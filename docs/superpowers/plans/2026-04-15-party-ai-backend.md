# PARTY AI Backend + Agent Provisioning — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Claude Agent SDK as the AI backend for PARTY, then provision six production agents (Google Ads, Klaviyo, Amazon, Walmart, WooCommerce, Shippo) with full credentials, skills, and domain knowledge.

**Architecture:** Python bridge sidecar (`agent_bridge.py`) wraps the Claude Agent SDK, communicating with PARTY's Rust TUI via stdin/stdout JSON lines. Each agent has its own AGENT.md system prompt, skills, and persistent session ID. All agents work inside the ClaudeDataAgent repo with full `.env` credentials.

**Tech Stack:** Rust (existing PARTY TUI), Python 3.9+ (`claude-agent-sdk`), Tokio async (subprocess management), serde_json (JSON line protocol).

**Spec:** `docs/superpowers/specs/2026-04-15-party-ai-backend-design.md`

**PARTY repo:** `~/Desktop/party/`
**ClaudeDataAgent repo:** `~/Desktop/ClaudeDataAgent -/`

---

## File Structure

```
~/Desktop/party/                           (PARTY repo)
  src/
    agent_runner.rs     — NEW: bridge subprocess manager
    env_loader.rs       — NEW: .env file parser
    app.rs              — MODIFY: add bridge, poll events, wire send_message
    models.rs           — MODIFY: add PartyConfig, session_id, cost
    store.rs            — MODIFY: add config load/save, bridge install
    main.rs             — MODIFY: load config, env vars, pass to App
    ui/messages.rs      — MODIFY: render tool_use/tool_result as system messages
    theme.rs            — MODIFY: add processing style
    lib.rs              — MODIFY: add new modules
  bridge/
    agent_bridge.py     — NEW: Python sidecar (Claude Agent SDK wrapper)
    requirements.txt    — NEW: claude-agent-sdk
  tests/
    env_loader_test.rs  — NEW: .env parser tests

~/.party/                                  (runtime data)
  config.json           — NEW: env_file + working_dir paths
  agents/
    google-ads/
      instructions/AGENT.md   — NEW: system prompt
      skills/*.md              — NEW: copied skill files
      memory/*.md              — NEW: empty stubs
    klaviyo-email/...
    amazon/...
    walmart/...
    woocommerce/...
    shippo/...
```

---

## Task 1: Python Bridge — `agent_bridge.py`

**Files:**
- Create: `~/Desktop/party/bridge/agent_bridge.py`
- Create: `~/Desktop/party/bridge/requirements.txt`

This is the heart of the AI backend. A single Python process that multiplexes all agent conversations through the Claude Agent SDK.

- [ ] **Step 1: Create bridge directory and requirements**

```bash
cd ~/Desktop/party && mkdir -p bridge
```

Create `bridge/requirements.txt`:

```
claude-agent-sdk
```

- [ ] **Step 2: Install the SDK**

```bash
cd ~/Desktop/party/bridge && pip install -r requirements.txt
```

- [ ] **Step 3: Write agent_bridge.py**

Create `bridge/agent_bridge.py`:

```python
#!/usr/bin/env python3
"""
PARTY Agent Bridge — Claude Agent SDK wrapper.

Reads JSON commands from stdin, routes to per-agent SDK sessions,
streams structured events to stdout as JSON lines.

Protocol:
  stdin  → {"cmd":"message","agent":"slug","content":"...","session_id":"..."}
  stdin  → {"cmd":"kill","agent":"slug"}
  stdin  → {"cmd":"shutdown"}
  stdout ← {"agent":"slug","type":"assistant","content":"..."}
  stdout ← {"agent":"slug","type":"tool_use","tool":"Bash","input":"..."}
  stdout ← {"agent":"slug","type":"tool_result","output":"..."}
  stdout ← {"agent":"slug","type":"result","session_id":"...","cost_usd":0.05}
  stdout ← {"agent":"slug","type":"error","message":"..."}
  stdout ← {"agent":"slug","type":"status","status":"thinking"}
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    UserMessage,
)


PARTY_DIR = Path(os.environ.get("PARTY_DIR", Path.home() / ".party"))


def emit(event: dict):
    """Write a JSON line to stdout and flush immediately."""
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def load_system_prompt(agent_slug: str) -> str:
    """Load AGENT.md + all skill files as the system prompt."""
    agent_dir = PARTY_DIR / "agents" / agent_slug
    parts = []

    # Main instructions
    agent_md = agent_dir / "instructions" / "AGENT.md"
    if agent_md.exists():
        parts.append(agent_md.read_text())

    # Skill files
    skills_dir = agent_dir / "skills"
    if skills_dir.exists():
        for skill_file in sorted(skills_dir.glob("*.md")):
            parts.append(f"\n\n---\n\n# Skill: {skill_file.stem}\n\n{skill_file.read_text()}")

    return "\n\n".join(parts) if parts else "You are a helpful assistant."


async def handle_message(agent_slug: str, content: str, session_id: str | None):
    """Send a message to an agent and stream events back."""
    system_prompt = load_system_prompt(agent_slug)

    working_dir = os.environ.get(
        "PARTY_WORKING_DIR",
        str(Path.home() / "Desktop" / "ClaudeDataAgent -")
    )

    emit({"agent": agent_slug, "type": "status", "status": "thinking"})

    try:
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            cwd=working_dir,
            allowed_tools=["Bash", "Read", "Write", "Edit", "Grep", "Glob"],
            permission_mode="acceptEdits",
            max_turns=30,
        )
        if session_id:
            options.resume = session_id

        captured_session_id = session_id

        async for message in query(prompt=content, options=options):
            if isinstance(message, SystemMessage):
                if message.subtype == "init" and "session_id" in message.data:
                    captured_session_id = message.data["session_id"]

            elif isinstance(message, AssistantMessage):
                # Extract text from content blocks
                for block in message.content:
                    if hasattr(block, "text") and block.text:
                        emit({
                            "agent": agent_slug,
                            "type": "assistant",
                            "content": block.text,
                        })
                    elif hasattr(block, "name"):
                        # ToolUseBlock
                        input_str = json.dumps(block.input) if isinstance(block.input, dict) else str(block.input)
                        emit({
                            "agent": agent_slug,
                            "type": "tool_use",
                            "tool": block.name,
                            "input": input_str[:500],  # truncate for display
                        })

            elif isinstance(message, UserMessage):
                # Tool results fed back to Claude
                content_str = str(message.content) if message.content else ""
                if content_str:
                    emit({
                        "agent": agent_slug,
                        "type": "tool_result",
                        "output": content_str[:500],  # truncate for display
                    })

            elif isinstance(message, ResultMessage):
                emit({
                    "agent": agent_slug,
                    "type": "result",
                    "session_id": message.session_id or captured_session_id or "",
                    "cost_usd": message.total_cost_usd or 0.0,
                    "input_tokens": (message.usage or {}).get("input_tokens", 0),
                    "output_tokens": (message.usage or {}).get("output_tokens", 0),
                })

    except Exception as e:
        emit({"agent": agent_slug, "type": "error", "message": str(e)})


async def main():
    """Main event loop — read stdin commands, dispatch to agents."""
    loop = asyncio.get_event_loop()
    active_tasks: dict[str, asyncio.Task] = {}

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break  # stdin closed

        line = line.decode().strip()
        if not line:
            continue

        try:
            cmd = json.loads(line)
        except json.JSONDecodeError:
            emit({"agent": "", "type": "error", "message": f"Invalid JSON: {line}"})
            continue

        command = cmd.get("cmd", "")

        if command == "message":
            agent = cmd.get("agent", "")
            content = cmd.get("content", "")
            session_id = cmd.get("session_id")

            # Cancel any active task for this agent
            if agent in active_tasks and not active_tasks[agent].done():
                active_tasks[agent].cancel()

            # Dispatch new query
            task = asyncio.create_task(handle_message(agent, content, session_id))
            active_tasks[agent] = task

        elif command == "kill":
            agent = cmd.get("agent", "")
            if agent in active_tasks and not active_tasks[agent].done():
                active_tasks[agent].cancel()
                emit({"agent": agent, "type": "status", "status": "killed"})

        elif command == "shutdown":
            for agent, task in active_tasks.items():
                if not task.done():
                    task.cancel()
            break

    # Wait for cancellations
    for task in active_tasks.values():
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Test the bridge manually**

```bash
cd ~/Desktop/party
echo '{"cmd":"shutdown"}' | PARTY_DIR=~/.party python3 bridge/agent_bridge.py
```

Expected: Clean exit, no errors.

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/party
git add bridge/
git commit -m "feat: add Python bridge for Claude Agent SDK"
```

---

## Task 2: Env Loader — `.env` Parser

**Files:**
- Create: `~/Desktop/party/src/env_loader.rs`
- Create: `~/Desktop/party/tests/env_loader_test.rs`
- Modify: `~/Desktop/party/src/lib.rs`

- [ ] **Step 1: Write env loader tests**

Create `tests/env_loader_test.rs`:

```rust
use party::env_loader::load_env;
use std::io::Write;
use tempfile::NamedTempFile;

#[test]
fn test_parse_standard_env() {
    let mut f = NamedTempFile::new().unwrap();
    writeln!(f, "KEY = 'value'").unwrap();
    writeln!(f, "OTHER = \"quoted\"").unwrap();
    let vars = load_env(f.path()).unwrap();
    assert_eq!(vars.get("KEY").unwrap(), "value");
    assert_eq!(vars.get("OTHER").unwrap(), "quoted");
}

#[test]
fn test_parse_no_spaces() {
    let mut f = NamedTempFile::new().unwrap();
    writeln!(f, "KEY=value").unwrap();
    let vars = load_env(f.path()).unwrap();
    assert_eq!(vars.get("KEY").unwrap(), "value");
}

#[test]
fn test_skip_comments_and_blanks() {
    let mut f = NamedTempFile::new().unwrap();
    writeln!(f, "# comment").unwrap();
    writeln!(f, "").unwrap();
    writeln!(f, "KEY = 'val'").unwrap();
    let vars = load_env(f.path()).unwrap();
    assert_eq!(vars.len(), 1);
    assert_eq!(vars.get("KEY").unwrap(), "val");
}

#[test]
fn test_value_with_equals() {
    let mut f = NamedTempFile::new().unwrap();
    writeln!(f, "URL = 'https://example.com?a=1&b=2'").unwrap();
    let vars = load_env(f.path()).unwrap();
    assert_eq!(vars.get("URL").unwrap(), "https://example.com?a=1&b=2");
}

#[test]
fn test_empty_file() {
    let f = NamedTempFile::new().unwrap();
    let vars = load_env(f.path()).unwrap();
    assert!(vars.is_empty());
}
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd ~/Desktop/party && cargo test --test env_loader_test
```

Expected: Compilation error — module not found.

- [ ] **Step 3: Write env_loader.rs**

Create `src/env_loader.rs`:

```rust
use anyhow::Result;
use std::collections::HashMap;
use std::path::Path;

/// Parse a .env file that may have spaces around `=` and quotes around values.
/// Format: `KEY = 'value'` or `KEY="value"` or `KEY=value`
pub fn load_env(path: &Path) -> Result<HashMap<String, String>> {
    let content = std::fs::read_to_string(path)?;
    let mut vars = HashMap::new();

    for line in content.lines() {
        let trimmed = line.trim();

        // Skip empty lines and comments
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }

        // Split on first '='
        if let Some((key, value)) = trimmed.split_once('=') {
            let key = key.trim().to_string();
            let mut value = value.trim().to_string();

            // Strip surrounding quotes
            if (value.starts_with('\'') && value.ends_with('\''))
                || (value.starts_with('"') && value.ends_with('"'))
            {
                value = value[1..value.len() - 1].to_string();
            }

            if !key.is_empty() {
                vars.insert(key, value);
            }
        }
    }

    Ok(vars)
}
```

- [ ] **Step 4: Add to lib.rs**

Add to `src/lib.rs`:

```rust
pub mod env_loader;
```

- [ ] **Step 5: Run tests — all 5 pass**

```bash
cd ~/Desktop/party && cargo test --test env_loader_test
```

- [ ] **Step 6: Commit**

```bash
cd ~/Desktop/party
git add src/env_loader.rs src/lib.rs tests/env_loader_test.rs
git commit -m "feat: add .env file parser"
```

---

## Task 3: Agent Runner — Bridge Process Manager

**Files:**
- Create: `~/Desktop/party/src/agent_runner.rs`
- Modify: `~/Desktop/party/src/lib.rs`

- [ ] **Step 1: Write agent_runner.rs**

Create `src/agent_runner.rs`:

```rust
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, ChildStdin};
use tokio::sync::mpsc;

/// Event received from the Python bridge.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentEvent {
    pub agent: String,
    #[serde(rename = "type")]
    pub event_type: String,
    #[serde(default)]
    pub content: Option<String>,
    #[serde(default)]
    pub tool: Option<String>,
    #[serde(default)]
    pub input: Option<String>,
    #[serde(default)]
    pub output: Option<String>,
    #[serde(default)]
    pub session_id: Option<String>,
    #[serde(default)]
    pub cost_usd: Option<f64>,
    #[serde(default)]
    pub input_tokens: Option<u64>,
    #[serde(default)]
    pub output_tokens: Option<u64>,
    #[serde(default)]
    pub message: Option<String>,
    #[serde(default)]
    pub status: Option<String>,
}

/// Command sent to the Python bridge.
#[derive(Debug, Serialize)]
struct BridgeCommand {
    cmd: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    agent: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    content: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    session_id: Option<String>,
}

/// Manages the single Python bridge subprocess.
pub struct Bridge {
    child: Child,
    stdin: ChildStdin,
    pub event_rx: mpsc::Receiver<AgentEvent>,
}

impl Bridge {
    /// Spawn the bridge process.
    pub fn spawn(
        bridge_script: &Path,
        party_dir: &Path,
        working_dir: &Path,
        env_vars: &HashMap<String, String>,
    ) -> Result<Self> {
        let mut cmd = tokio::process::Command::new("python3");
        cmd.arg(bridge_script)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .env("PARTY_DIR", party_dir.as_os_str())
            .env("PARTY_WORKING_DIR", working_dir.as_os_str());

        // Inject all .env vars
        for (k, v) in env_vars {
            cmd.env(k, v);
        }

        let mut child = cmd.spawn().context("Failed to spawn bridge process")?;

        let stdin = child.stdin.take().expect("bridge stdin");
        let stdout = child.stdout.take().expect("bridge stdout");

        // Background task: read stdout lines and send through channel
        let (tx, rx) = mpsc::channel::<AgentEvent>(256);
        tokio::spawn(async move {
            let reader = BufReader::new(stdout);
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                if let Ok(event) = serde_json::from_str::<AgentEvent>(&line) {
                    if tx.send(event).await.is_err() {
                        break; // receiver dropped
                    }
                }
            }
        });

        Ok(Bridge {
            child,
            stdin,
            event_rx: rx,
        })
    }

    /// Send a message to an agent.
    pub async fn send_message(
        &mut self,
        agent: &str,
        content: &str,
        session_id: Option<&str>,
    ) -> Result<()> {
        let cmd = BridgeCommand {
            cmd: "message".to_string(),
            agent: Some(agent.to_string()),
            content: Some(content.to_string()),
            session_id: session_id.map(|s| s.to_string()),
        };
        let line = serde_json::to_string(&cmd)? + "\n";
        self.stdin.write_all(line.as_bytes()).await?;
        self.stdin.flush().await?;
        Ok(())
    }

    /// Kill an agent's active query.
    pub async fn kill_agent(&mut self, agent: &str) -> Result<()> {
        let cmd = BridgeCommand {
            cmd: "kill".to_string(),
            agent: Some(agent.to_string()),
            content: None,
            session_id: None,
        };
        let line = serde_json::to_string(&cmd)? + "\n";
        self.stdin.write_all(line.as_bytes()).await?;
        self.stdin.flush().await?;
        Ok(())
    }

    /// Shutdown the bridge gracefully.
    pub async fn shutdown(&mut self) -> Result<()> {
        let cmd = BridgeCommand {
            cmd: "shutdown".to_string(),
            agent: None,
            content: None,
            session_id: None,
        };
        let line = serde_json::to_string(&cmd)? + "\n";
        let _ = self.stdin.write_all(line.as_bytes()).await;
        let _ = self.stdin.flush().await;
        let _ = self.child.wait().await;
        Ok(())
    }

    /// Try to receive an event (non-blocking).
    pub fn try_recv(&mut self) -> Option<AgentEvent> {
        self.event_rx.try_recv().ok()
    }
}
```

- [ ] **Step 2: Add to lib.rs**

Add to `src/lib.rs`:

```rust
pub mod agent_runner;
```

- [ ] **Step 3: Verify it compiles**

```bash
cd ~/Desktop/party && cargo build
```

- [ ] **Step 4: Commit**

```bash
cd ~/Desktop/party
git add src/agent_runner.rs src/lib.rs
git commit -m "feat: add bridge process manager"
```

---

## Task 4: Model + Store Updates — Config, Session, Cost

**Files:**
- Modify: `~/Desktop/party/src/models.rs`
- Modify: `~/Desktop/party/src/store.rs`

- [ ] **Step 1: Add PartyConfig and Agent fields to models.rs**

Add to `src/models.rs` after the existing `FileNode` struct:

```rust
// ── Config ──────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartyConfig {
    pub env_file: std::path::PathBuf,
    pub working_dir: std::path::PathBuf,
}

impl Default for PartyConfig {
    fn default() -> Self {
        let home = dirs::home_dir().unwrap_or_default();
        Self {
            env_file: home.join("Desktop/ClaudeDataAgent -/.env"),
            working_dir: home.join("Desktop/ClaudeDataAgent -"),
        }
    }
}
```

Add two fields to the `Agent` struct (after `unread_count`):

```rust
    #[serde(default)]
    pub session_id: Option<String>,
    #[serde(default)]
    pub total_cost_usd: f64,
```

- [ ] **Step 2: Add config functions to store.rs**

Add to `src/store.rs`:

```rust
use crate::models::PartyConfig;

/// Load config from ~/.party/config.json (creates default if missing).
pub fn load_config(base: &Path) -> Result<PartyConfig> {
    let config_path = base.join("config.json");
    if config_path.exists() {
        let json = std::fs::read_to_string(&config_path)?;
        let config: PartyConfig = serde_json::from_str(&json)?;
        Ok(config)
    } else {
        let config = PartyConfig::default();
        save_config(base, &config)?;
        Ok(config)
    }
}

/// Save config to ~/.party/config.json.
pub fn save_config(base: &Path, config: &PartyConfig) -> Result<()> {
    let json = serde_json::to_string_pretty(config)?;
    std::fs::write(base.join("config.json"), json)?;
    Ok(())
}

/// Get the path to the bridge script (ships with PARTY).
pub fn bridge_script_path() -> PathBuf {
    // Look for bridge relative to the binary, or fall back to known location
    let exe = std::env::current_exe().unwrap_or_default();
    let dir = exe.parent().unwrap_or(Path::new("."));

    // Check next to binary first
    let next_to_binary = dir.join("agent_bridge.py");
    if next_to_binary.exists() {
        return next_to_binary;
    }

    // Check in repo bridge/ dir (dev mode)
    let repo_bridge = dir.join("../../bridge/agent_bridge.py");
    if repo_bridge.exists() {
        return repo_bridge.canonicalize().unwrap_or(repo_bridge);
    }

    // Fallback: ~/.party/agent_bridge.py
    dirs::home_dir()
        .unwrap_or_default()
        .join(".party/agent_bridge.py")
}
```

- [ ] **Step 3: Update test files to include new Agent fields**

In `tests/models_test.rs` and `tests/store_test.rs`, add `session_id: None, total_cost_usd: 0.0,` to all `Agent` struct literals (after `unread_count: 0`).

- [ ] **Step 4: Verify all tests pass**

```bash
cd ~/Desktop/party && cargo test --tests
```

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/party
git add src/models.rs src/store.rs tests/
git commit -m "feat: add PartyConfig, session_id, cost tracking"
```

---

## Task 5: App Integration — Wire Bridge to Event Loop

**Files:**
- Modify: `~/Desktop/party/src/app.rs`
- Modify: `~/Desktop/party/src/main.rs`

This is the critical integration task. The App gets a bridge, send_message pipes to it, and the event loop polls for agent responses.

- [ ] **Step 1: Update App struct and new()**

In `src/app.rs`, add these imports at the top:

```rust
use std::collections::HashMap;
use crate::agent_runner::{AgentEvent, Bridge};
use crate::env_loader;
use crate::models::PartyConfig;
```

Add new fields to the `App` struct:

```rust
    pub config: PartyConfig,
    pub env_vars: HashMap<String, String>,
    pub bridge: Option<Bridge>,
    pub agent_thinking: HashMap<String, bool>, // tracks which agents are processing
```

Update `App::new()` to accept config and env_vars:

```rust
    pub fn new(party_dir: PathBuf, config: PartyConfig, env_vars: HashMap<String, String>) -> Result<Self> {
        store::init_party_dir(&party_dir)?;
        let agents = store::list_agents(&party_dir)?;
        Ok(Self {
            running: true,
            party_dir,
            screen: Screen::AgentList,
            agents,
            selected_agent: 0,
            active_agent: None,
            focus: Pane::Messages,
            sidebar_tab: SidebarTab::Files,
            threads: vec![],
            selected_thread: 0,
            selected_file: 0,
            selected_project: 0,
            scroll_offset: 0,
            input_mode: false,
            input_target: InputTarget::Chat,
            input_buffer: String::new(),
            file_tree: None,
            terminal_size: (80, 24),
            pending_agent_name: None,
            config,
            env_vars,
            bridge: None,
            agent_thinking: HashMap::new(),
        })
    }
```

- [ ] **Step 2: Add bridge spawn and message piping**

Add method to App:

```rust
    /// Ensure the bridge is running, spawning if needed.
    fn ensure_bridge(&mut self) -> Result<()> {
        if self.bridge.is_none() {
            let script = store::bridge_script_path();
            let bridge = Bridge::spawn(
                &script,
                &self.party_dir,
                &self.config.working_dir,
                &self.env_vars,
            )?;
            self.bridge = Some(bridge);
        }
        Ok(())
    }
```

Modify the existing `send_message()` method — after persisting to disk, also send to bridge:

```rust
    fn send_message(&mut self, content: String) -> Result<()> {
        if self.threads.is_empty() {
            return Ok(());
        }
        let msg = Message {
            id: Uuid::new_v4(),
            role: Role::You,
            content: content.clone(),
            timestamp: Utc::now(),
        };
        self.threads[self.selected_thread].messages.push(msg);

        // Persist to disk
        if let Some(idx) = self.active_agent {
            let slug = self.agents[idx].slug.clone();
            store::save_thread(&self.party_dir, &slug, &self.threads[self.selected_thread])?;

            // Send to bridge (async — fire and forget, bridge runs in background)
            if let Err(e) = self.ensure_bridge() {
                // Bridge failed to start — add error message
                self.add_system_message(format!("Bridge error: {}", e));
                return Ok(());
            }
            if let Some(ref mut bridge) = self.bridge {
                let session_id = self.agents[idx].session_id.clone();
                let rt = tokio::runtime::Handle::try_current();
                if let Ok(handle) = rt {
                    let _ = handle.block_on(bridge.send_message(
                        &slug,
                        &content,
                        session_id.as_deref(),
                    ));
                    self.agent_thinking.insert(slug, true);
                }
            }
        }
        Ok(())
    }

    /// Add a system message to the current thread.
    fn add_system_message(&mut self, content: String) {
        if self.threads.is_empty() {
            return;
        }
        let msg = Message {
            id: Uuid::new_v4(),
            role: Role::System,
            content,
            timestamp: Utc::now(),
        };
        self.threads[self.selected_thread].messages.push(msg);
    }
```

- [ ] **Step 3: Add bridge event polling**

Add method to poll bridge events and convert to messages:

```rust
    /// Poll the bridge for agent events and convert to messages.
    pub fn poll_bridge_events(&mut self) -> Result<()> {
        let bridge = match self.bridge.as_mut() {
            Some(b) => b,
            None => return Ok(()),
        };

        while let Some(event) = bridge.try_recv() {
            self.handle_agent_event(event)?;
        }
        Ok(())
    }

    fn handle_agent_event(&mut self, event: AgentEvent) -> Result<()> {
        // Find the agent index by slug
        let agent_idx = match self.agents.iter().position(|a| a.slug == event.agent) {
            Some(idx) => idx,
            None => return Ok(()), // unknown agent, ignore
        };

        // Only append to messages if this agent's chat is open
        let is_active = self.active_agent == Some(agent_idx);

        match event.event_type.as_str() {
            "assistant" => {
                if let Some(content) = event.content {
                    if is_active && !self.threads.is_empty() {
                        let msg = Message {
                            id: Uuid::new_v4(),
                            role: Role::Agent,
                            content,
                            timestamp: Utc::now(),
                        };
                        self.threads[self.selected_thread].messages.push(msg);
                    }
                }
            }
            "tool_use" => {
                if is_active && !self.threads.is_empty() {
                    let tool = event.tool.unwrap_or_default();
                    let input = event.input.unwrap_or_default();
                    let content = format!("[code: {}] {}", tool, input);
                    let msg = Message {
                        id: Uuid::new_v4(),
                        role: Role::System,
                        content,
                        timestamp: Utc::now(),
                    };
                    self.threads[self.selected_thread].messages.push(msg);
                }
            }
            "tool_result" => {
                if is_active && !self.threads.is_empty() {
                    if let Some(output) = event.output {
                        let msg = Message {
                            id: Uuid::new_v4(),
                            role: Role::System,
                            content: format!("→ {}", output),
                            timestamp: Utc::now(),
                        };
                        self.threads[self.selected_thread].messages.push(msg);
                    }
                }
            }
            "result" => {
                // Update session_id and cost on the agent
                if let Some(sid) = event.session_id {
                    if !sid.is_empty() {
                        self.agents[agent_idx].session_id = Some(sid);
                    }
                }
                if let Some(cost) = event.cost_usd {
                    self.agents[agent_idx].total_cost_usd += cost;
                }
                // Save agent metadata
                let _ = store::save_agent(&self.party_dir, &self.agents[agent_idx]);

                // Mark agent as done thinking
                self.agent_thinking.remove(&event.agent);

                // Update agent status
                self.agents[agent_idx].status = AgentStatus::Active;

                // Save thread
                if is_active && !self.threads.is_empty() {
                    let slug = &self.agents[agent_idx].slug;
                    let _ = store::save_thread(
                        &self.party_dir,
                        slug,
                        &self.threads[self.selected_thread],
                    );
                }
            }
            "error" => {
                if is_active && !self.threads.is_empty() {
                    let msg_text = event.message.unwrap_or_else(|| "Unknown error".to_string());
                    let msg = Message {
                        id: Uuid::new_v4(),
                        role: Role::System,
                        content: format!("⚠ Error: {}", msg_text),
                        timestamp: Utc::now(),
                    };
                    self.threads[self.selected_thread].messages.push(msg);
                }
                self.agent_thinking.remove(&event.agent);
                self.agents[agent_idx].status = AgentStatus::Error;
            }
            "status" => {
                // Update thinking state
                if let Some(status) = event.status {
                    match status.as_str() {
                        "thinking" => {
                            self.agent_thinking.insert(event.agent.clone(), true);
                        }
                        "killed" | "done" => {
                            self.agent_thinking.remove(&event.agent);
                        }
                        _ => {}
                    }
                }
            }
            _ => {}
        }

        Ok(())
    }
```

- [ ] **Step 4: Update main.rs to use async runtime and load config**

Replace `src/main.rs`:

```rust
mod app;
mod agent_runner;
mod env_loader;
mod models;
mod store;
mod theme;
mod tui;
mod ui;

use app::App;
use models::PartyConfig;
use store::default_party_dir;
use std::collections::HashMap;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Panic hook to restore terminal
    let original_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |panic_info| {
        let _ = crossterm::execute!(
            std::io::stderr(),
            crossterm::terminal::LeaveAlternateScreen
        );
        let _ = crossterm::terminal::disable_raw_mode();
        original_hook(panic_info);
    }));

    let party_dir = default_party_dir();

    // Load config (creates default on first run)
    let config = store::load_config(&party_dir)?;

    // Load env vars
    let env_vars = if config.env_file.exists() {
        env_loader::load_env(&config.env_file)?
    } else {
        HashMap::new()
    };

    let mut terminal = tui::init_terminal()?;
    let mut app = App::new(party_dir, config, env_vars)?;

    let size = terminal.size()?;
    app.terminal_size = (size.width, size.height);

    while app.running {
        // Poll bridge events
        let _ = app.poll_bridge_events();

        terminal.draw(|frame| {
            app.terminal_size = (frame.area().width, frame.area().height);
            ui::render(frame, &app);
        })?;
        app.handle_event()?;
    }

    // Shutdown bridge
    if let Some(ref mut bridge) = app.bridge {
        let rt = tokio::runtime::Handle::current();
        let _ = rt.block_on(bridge.shutdown());
    }

    tui::restore_terminal(&mut terminal)?;
    Ok(())
}
```

- [ ] **Step 5: Verify it compiles**

```bash
cd ~/Desktop/party && cargo build
```

- [ ] **Step 6: Commit**

```bash
cd ~/Desktop/party
git add src/app.rs src/main.rs
git commit -m "feat: wire bridge to event loop and message dispatch"
```

---

## Task 6: UI Updates — Thinking Indicator + Tool Messages

**Files:**
- Modify: `~/Desktop/party/src/theme.rs`
- Modify: `~/Desktop/party/src/ui/messages.rs`

- [ ] **Step 1: Add processing style to theme.rs**

Add to `src/theme.rs`:

```rust
/// Processing/thinking indicator style (dim italic)
pub fn processing() -> Style {
    Style::default()
        .fg(DIM)
        .bg(BACKGROUND)
        .add_modifier(Modifier::ITALIC)
}
```

- [ ] **Step 2: Update messages.rs to show thinking indicator**

In `src/ui/messages.rs`, add an import for the app's agent_thinking field and show a "thinking..." line when the active agent is processing. At the end of the message rendering (after all messages, before scroll logic), add:

```rust
    // Show thinking indicator if agent is processing
    if let Some(agent) = app.active_agent_ref() {
        if app.agent_thinking.get(&agent.slug).copied().unwrap_or(false) {
            lines.push(Line::from(""));
            lines.push(Line::from(vec![
                Span::styled("  ", theme::text()),
                Span::styled("agent", theme::role_style("agent")),
                Span::styled("  ", theme::text()),
                Span::styled("thinking...", theme::processing()),
            ]));
        }
    }
```

- [ ] **Step 3: Verify it compiles**

```bash
cd ~/Desktop/party && cargo build
```

- [ ] **Step 4: Commit**

```bash
cd ~/Desktop/party
git add src/theme.rs src/ui/messages.rs
git commit -m "feat: add thinking indicator and tool message rendering"
```

---

## Task 7: Provision Agent — Google Ads

**Files:**
- Create: `~/.party/agents/google-ads/instructions/AGENT.md`
- Create: `~/.party/agents/google-ads/skills/data-orchestrator.md`
- Create: `~/.party/agents/google-ads/memory/conversation_log.md`
- Create: `~/.party/agents/google-ads/memory/decisions.md`
- Create: `~/.party/agents/google-ads/memory/learnings.md`

This task creates the Google Ads agent by: creating it via PARTY's store, then populating its instructions and skills.

- [ ] **Step 1: Write a provisioning script**

Create `~/Desktop/party/scripts/provision_agents.sh`:

```bash
#!/bin/bash
set -e

PARTY_DIR="$HOME/.party"
CDA_DIR="$HOME/Desktop/ClaudeDataAgent -"
SKILLS_DIR="$CDA_DIR/.claude/skills"

# Ensure base structure exists
mkdir -p "$PARTY_DIR/agents"

provision_agent() {
    local slug="$1"
    local name="$2"
    local role="$3"

    local agent_dir="$PARTY_DIR/agents/$slug"
    mkdir -p "$agent_dir/conversations"
    mkdir -p "$agent_dir/instructions"
    mkdir -p "$agent_dir/skills"
    mkdir -p "$agent_dir/memory"
    mkdir -p "$agent_dir/data"

    # Create agent.json
    cat > "$agent_dir/agent.json" << AGENTJSON
{
  "id": "$(python3 -c 'import uuid; print(uuid.uuid4())')",
  "name": "$name",
  "slug": "$slug",
  "role": "$role",
  "status": "Idle",
  "channels": [],
  "projects": [],
  "context_snapshots": [],
  "unread_count": 0,
  "session_id": null,
  "total_cost_usd": 0.0,
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
}
AGENTJSON

    # Create Main thread
    cat > "$agent_dir/conversations/$(python3 -c 'import uuid; print(uuid.uuid4())').json" << THREADJSON
{
  "id": "$(python3 -c 'import uuid; print(uuid.uuid4())')",
  "label": "Main",
  "messages": [],
  "forked_from": null,
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
}
THREADJSON

    # Create memory stubs
    echo "# Conversation Log" > "$agent_dir/memory/conversation_log.md"
    echo "# Decisions" > "$agent_dir/memory/decisions.md"
    echo "# Learnings" > "$agent_dir/memory/learnings.md"

    echo "  ✓ Provisioned $name ($slug)"
}

copy_skill() {
    local slug="$1"
    local skill_name="$2"
    local agent_dir="$PARTY_DIR/agents/$slug"

    if [ -f "$SKILLS_DIR/$skill_name/SKILL.md" ]; then
        cp "$SKILLS_DIR/$skill_name/SKILL.md" "$agent_dir/skills/$skill_name.md"
        echo "    + Copied skill: $skill_name"
    fi
}

echo "=== Provisioning PARTY Agents ==="
echo ""

# ── Google Ads ──
provision_agent "google-ads" "Google Ads" "Paid acquisition, bidding, ROAS, Shopping campaigns"
copy_skill "google-ads" "data-orchestrator"
echo ""

# ── Klaviyo Email ──
provision_agent "klaviyo-email" "Klaviyo Email" "Email marketing, campaigns, flows, segments, templates"
copy_skill "klaviyo-email" "klaviyo-api"
copy_skill "klaviyo-email" "klaviyo-email-design"
echo ""

# ── Amazon ──
provision_agent "amazon" "Amazon" "Amazon SP-API marketplace, listings, orders, inventory"
copy_skill "amazon" "data-orchestrator"
echo ""

# ── Walmart ──
provision_agent "walmart" "Walmart" "Walmart Marketplace listings, orders, inventory, pricing"
copy_skill "walmart" "walmart-api"
copy_skill "walmart" "data-orchestrator"
echo ""

# ── WooCommerce ──
provision_agent "woocommerce" "WooCommerce" "Products, orders, customers, SEO, search, content"
copy_skill "woocommerce" "woocommerce-api"
copy_skill "woocommerce" "woocommerce-product-creation"
echo ""

# ── Shippo ──
provision_agent "shippo" "Shippo Shipping" "Shipping labels, rates, tracking, cost analysis"
copy_skill "shippo" "fishbowl-inventory"
copy_skill "shippo" "data-orchestrator"
echo ""

echo "=== Done! ==="
echo "Now write AGENT.md for each agent."
```

```bash
chmod +x ~/Desktop/party/scripts/provision_agents.sh
```

- [ ] **Step 2: Run the provisioning script**

```bash
~/Desktop/party/scripts/provision_agents.sh
```

- [ ] **Step 3: Write Google Ads AGENT.md**

Create `~/.party/agents/google-ads/instructions/AGENT.md` — this is the agent's complete system prompt. Read the full content from the spec's Agent 1 section plus extract relevant patterns from the ClaudeDataAgent repo.

The AGENT.md should contain:
- Identity and mission
- Systems owned (Google Ads, GA4, Merchant Center, Search Console)
- Credential env vars to use
- Key IDs (customer IDs, property IDs)
- API patterns (extracted from daily_pull.py)
- Business rules from CLAUDE.md (rules 10, 18, 19)
- Reference to existing scripts
- Memory instructions
- Cross-agent boundaries

Write a complete AGENT.md (this will be a substantial file — 200+ lines of domain knowledge).

- [ ] **Step 4: Write Klaviyo Email AGENT.md**

Same pattern — extract from spec Agent 2 section + klaviyo-api skill + CLAUDE.md rules 6, 7, 16, 17, 21.

- [ ] **Step 5: Write Amazon AGENT.md**

Simpler — extract from spec Agent 3 + daily_pull.py Amazon patterns.

- [ ] **Step 6: Write Walmart AGENT.md**

Extract from spec Agent 4 + walmart-api skill + CLAUDE.md rule about Walmart 404.

- [ ] **Step 7: Write WooCommerce AGENT.md**

The biggest one — extract from spec Agent 5 + woocommerce-api + woocommerce-product-creation + CLAUDE.md rules 13, 15, 20, 22, 23, 24, 25.

- [ ] **Step 8: Write Shippo AGENT.md**

Extract from spec Agent 6 + fishbowl-inventory skill + CLAUDE.md rules 11, 12.

- [ ] **Step 9: Verify all agents show up in PARTY**

```bash
cd ~/Desktop/party && cargo run
```

Expected: Agent list shows all 6 agents. Can open each one, see the file tree with AGENT.md and skills.

- [ ] **Step 10: Commit provisioning script**

```bash
cd ~/Desktop/party
git add scripts/
git commit -m "feat: add agent provisioning script"
```

---

## Task 8: End-to-End Test — Talk to an Agent

**Files:** No new files. This is a verification task.

- [ ] **Step 1: Install claude-agent-sdk**

```bash
pip install claude-agent-sdk
```

- [ ] **Step 2: Verify bridge script path**

Make sure the bridge script is findable. For dev mode, symlink or copy:

```bash
cp ~/Desktop/party/bridge/agent_bridge.py ~/.party/agent_bridge.py
```

- [ ] **Step 3: Run PARTY and test**

```bash
cd ~/Desktop/party && cargo run
```

Test flow:
1. Open "Google Ads" agent
2. Type `i`, enter: "What's our Google Ads customer ID?"
3. Agent should respond (via bridge → SDK → Claude) with the customer ID from its AGENT.md
4. Try: "Check our daily revenue for today using the daily_pull.py script"
5. Agent should use Bash tool to run the script
6. Tool use should appear as system messages
7. Press Esc, reopen — conversation should persist
8. Quit and restart PARTY — session should resume via saved session_id

- [ ] **Step 4: Commit any fixes**

```bash
cd ~/Desktop/party
git add -A
git commit -m "fix: end-to-end agent communication fixes"
```

---

## Task 9: Install Bridge on First Run

**Files:**
- Modify: `~/Desktop/party/src/store.rs`
- Modify: `~/Desktop/party/src/main.rs`

- [ ] **Step 1: Add bridge install to store.rs**

Add function that copies `bridge/agent_bridge.py` to `~/.party/agent_bridge.py` on first run:

```rust
/// Install the bridge script to ~/.party/ if not already present.
pub fn install_bridge(base: &Path, source: &Path) -> Result<()> {
    let dest = base.join("agent_bridge.py");
    if !dest.exists() && source.exists() {
        std::fs::copy(source, &dest)?;
    }
    Ok(())
}
```

- [ ] **Step 2: Call from main.rs on startup**

In `main.rs`, after `init_party_dir`:

```rust
    // Install bridge script if needed
    let bridge_source = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.join("../../bridge/agent_bridge.py")))
        .unwrap_or_default();
    let _ = store::install_bridge(&party_dir, &bridge_source);
```

- [ ] **Step 3: Commit**

```bash
cd ~/Desktop/party
git add src/store.rs src/main.rs
git commit -m "feat: auto-install bridge script on first run"
```

---

## Execution Summary

| Task | What it delivers | Key files |
|------|-----------------|-----------|
| 1 | Python bridge (Agent SDK wrapper) | `bridge/agent_bridge.py` |
| 2 | .env parser with tests | `src/env_loader.rs`, 5 tests |
| 3 | Bridge process manager (Rust) | `src/agent_runner.rs` |
| 4 | Config + session + cost models | `src/models.rs`, `src/store.rs` |
| 5 | App integration (bridge ↔ event loop) | `src/app.rs`, `src/main.rs` |
| 6 | UI thinking indicator | `src/theme.rs`, `src/ui/messages.rs` |
| 7 | Six agents provisioned with AGENT.md + skills | `~/.party/agents/*/` |
| 8 | End-to-end verification | Manual test |
| 9 | First-run bridge install | `src/store.rs`, `src/main.rs` |

Total: **9 tasks**. Tasks 1-6 are code. Task 7 is agent content. Task 8 is E2E verification. Task 9 is polish.
