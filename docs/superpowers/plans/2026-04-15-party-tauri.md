# PARTY Tauri Desktop App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace PARTY's terminal TUI with a Tauri v2 desktop application, keeping all Rust backend code and adding a vanilla HTML/CSS/JS frontend.

**Architecture:** Tauri v2 wraps the existing Rust backend (models, store, agent_runner, env_loader) in a native window. The TUI layer (ratatui, crossterm, ui/*.rs, app.rs, tui.rs, theme.rs) is removed and replaced by Tauri IPC commands + a single-page web frontend. The Python bridge stays unchanged.

**Tech Stack:** Tauri 2, Rust 2021, vanilla HTML/CSS/JS (no framework, no bundler), existing tokio/serde/chrono/uuid deps.

**Spec:** `docs/superpowers/specs/2026-04-15-party-tauri-design.md`
**Repo:** `~/Desktop/party/`

---

## File Structure (After Migration)

```
party/
  src-tauri/
    src/
      main.rs             — Tauri entry point, command registration
      commands.rs          — IPC command handlers
      state.rs             — AppState (shared state for commands)
      models.rs            — MOVED from src/models.rs (unchanged)
      store.rs             — MOVED from src/store.rs (unchanged)
      agent_runner.rs      — MOVED from src/agent_runner.rs (unchanged)
      env_loader.rs        — MOVED from src/env_loader.rs (unchanged)
      lib.rs               — Module declarations
    Cargo.toml            — Tauri deps (replaces ratatui/crossterm)
    tauri.conf.json       — Window config
    build.rs              — Tauri build script
  src/
    index.html            — Single page app
    style.css             — Light gray theme
    app.js                — All frontend logic
  bridge/
    agent_bridge.py       — KEPT (unchanged)
    requirements.txt      — KEPT
  tests/
    env_loader_test.rs    — MOVED (unchanged)
    models_test.rs        — MOVED (unchanged)
    store_test.rs         — MOVED (unchanged)
    blocks_test.rs        — REMOVED (TUI block parser gone)
```

---

## Task 1: Restructure to Tauri Project Layout

**Files:**
- Move: `src/*.rs` → `src-tauri/src/`
- Move: `Cargo.toml` → `src-tauri/Cargo.toml`
- Move: `tests/` → `src-tauri/tests/` (except blocks_test.rs)
- Create: `src-tauri/tauri.conf.json`
- Create: `src-tauri/build.rs`
- Create: `src/index.html` (placeholder)
- Remove: TUI files (app.rs, tui.rs, theme.rs, src/ui/)

- [ ] **Step 1: Create the Tauri directory structure**

```bash
cd ~/Desktop/party
mkdir -p src-tauri/src
mkdir -p src
```

- [ ] **Step 2: Move Rust backend files to src-tauri/src/**

```bash
cd ~/Desktop/party
# Move backend files (keep these)
cp src/models.rs src-tauri/src/
cp src/store.rs src-tauri/src/
cp src/agent_runner.rs src-tauri/src/
cp src/env_loader.rs src-tauri/src/

# Move tests (except blocks_test which depends on TUI)
mkdir -p src-tauri/tests
cp tests/models_test.rs src-tauri/tests/
cp tests/store_test.rs src-tauri/tests/
cp tests/env_loader_test.rs src-tauri/tests/
```

- [ ] **Step 3: Write src-tauri/Cargo.toml**

```toml
[package]
name = "party"
version = "0.2.0"
edition = "2021"
description = "AI Agent Management Desktop App"

[lib]
name = "party_lib"
crate-type = ["staticlib", "cdylib", "rlib"]

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-shell = "2"
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
chrono = { version = "0.4", features = ["serde"] }
uuid = { version = "1", features = ["v4", "serde"] }
dirs = "5"
anyhow = "1"

[dev-dependencies]
tempfile = "3"

[profile.release]
opt-level = 3
lto = true
strip = true
```

- [ ] **Step 4: Write src-tauri/build.rs**

```rust
fn main() {
    tauri_build::build()
}
```

- [ ] **Step 5: Write src-tauri/tauri.conf.json**

```json
{
  "productName": "PARTY",
  "version": "0.2.0",
  "identifier": "com.naturesseed.party",
  "build": {
    "frontendDist": "../src"
  },
  "app": {
    "windows": [
      {
        "title": "PARTY — AI Agent Management",
        "width": 1200,
        "height": 800,
        "minWidth": 600,
        "minHeight": 400,
        "resizable": true
      }
    ],
    "security": {
      "csp": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    }
  }
}
```

- [ ] **Step 6: Write placeholder src/index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PARTY</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div id="app">
    <h1>PARTY — Loading...</h1>
  </div>
  <script src="app.js"></script>
</body>
</html>
```

Create empty `src/style.css` and `src/app.js`:

```bash
touch src/style.css src/app.js
```

- [ ] **Step 7: Write src-tauri/src/lib.rs**

```rust
pub mod models;
pub mod store;
pub mod agent_runner;
pub mod env_loader;
pub mod commands;
pub mod state;
```

- [ ] **Step 8: Write stub src-tauri/src/state.rs**

```rust
use crate::agent_runner::Bridge;
use crate::models::PartyConfig;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Mutex;

pub struct AppState {
    pub party_dir: PathBuf,
    pub config: PartyConfig,
    pub env_vars: HashMap<String, String>,
    pub bridge: Mutex<Option<Bridge>>,
}
```

- [ ] **Step 9: Write stub src-tauri/src/commands.rs**

```rust
use tauri::State;
use crate::state::AppState;
use crate::models::Agent;

#[tauri::command]
pub fn list_agents(state: State<'_, AppState>) -> Result<Vec<Agent>, String> {
    crate::store::list_agents(&state.party_dir).map_err(|e| e.to_string())
}
```

- [ ] **Step 10: Write src-tauri/src/main.rs**

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod models;
mod store;
mod agent_runner;
mod env_loader;
mod commands;
mod state;

use state::AppState;
use std::collections::HashMap;

fn main() {
    let party_dir = store::default_party_dir();
    store::init_party_dir(&party_dir).expect("Failed to init party dir");

    let config = store::load_config(&party_dir).expect("Failed to load config");
    let env_vars = env_loader::load_env(&config.env_file).unwrap_or_default();

    let app_state = AppState {
        party_dir,
        config,
        env_vars,
        bridge: std::sync::Mutex::new(None),
    };

    tauri::Builder::default()
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            commands::list_agents,
        ])
        .run(tauri::generate_context!())
        .expect("error running PARTY");
}
```

- [ ] **Step 11: Remove old files**

```bash
cd ~/Desktop/party
rm -rf src/ui src/app.rs src/tui.rs src/theme.rs src/main.rs src/lib.rs src/models.rs src/store.rs src/agent_runner.rs src/env_loader.rs
rm -f tests/blocks_test.rs tests/models_test.rs tests/store_test.rs tests/env_loader_test.rs
rm -f Cargo.toml Cargo.lock
```

- [ ] **Step 12: Verify it compiles**

```bash
cd ~/Desktop/party && cargo tauri build --debug 2>&1 | tail -10
```

Or just compile the Rust:

```bash
cd ~/Desktop/party/src-tauri && cargo build
```

- [ ] **Step 13: Commit**

```bash
cd ~/Desktop/party
git add -A
git commit -m "refactor: migrate from TUI to Tauri desktop app structure"
```

---

## Task 2: Full IPC Commands

**Files:**
- Modify: `src-tauri/src/commands.rs`
- Modify: `src-tauri/src/state.rs`
- Modify: `src-tauri/src/main.rs`

- [ ] **Step 1: Expand state.rs with thread tracking**

Replace `src-tauri/src/state.rs`:

```rust
use crate::agent_runner::{AgentEvent, Bridge};
use crate::models::{PartyConfig, Thread};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Mutex;

pub struct AppState {
    pub party_dir: PathBuf,
    pub config: PartyConfig,
    pub env_vars: HashMap<String, String>,
    pub bridge: Mutex<Option<Bridge>>,
    pub active_threads: Mutex<HashMap<String, Vec<Thread>>>,  // slug → threads
    pub pending_events: Mutex<Vec<AgentEvent>>,  // events waiting to be polled
    pub thinking: Mutex<HashMap<String, bool>>,  // slug → is_thinking
}
```

- [ ] **Step 2: Write complete commands.rs**

Replace `src-tauri/src/commands.rs`:

```rust
use chrono::Utc;
use tauri::State;
use uuid::Uuid;

use crate::agent_runner::{AgentEvent, Bridge};
use crate::models::*;
use crate::state::AppState;
use crate::store;

// ── Agent CRUD ──────────────────────────────────────────────────────────────

#[tauri::command]
pub fn list_agents(state: State<'_, AppState>) -> Result<Vec<Agent>, String> {
    store::list_agents(&state.party_dir).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_agent(state: State<'_, AppState>, name: String, role: String) -> Result<Agent, String> {
    let agent = Agent {
        id: Uuid::new_v4(),
        name: name.clone(),
        slug: slugify(&name),
        role,
        status: AgentStatus::Idle,
        channels: vec![],
        projects: vec![],
        context_snapshots: vec![],
        unread_count: 0,
        session_id: None,
        total_cost_usd: 0.0,
        created_at: Utc::now(),
    };
    store::create_agent(&state.party_dir, &agent).map_err(|e| e.to_string())?;
    Ok(agent)
}

#[tauri::command]
pub fn delete_agent(state: State<'_, AppState>, slug: String) -> Result<(), String> {
    store::delete_agent(&state.party_dir, &slug).map_err(|e| e.to_string())
}

// ── Chat ────────────────────────────────────────────────────────────────────

#[tauri::command]
pub fn load_threads(state: State<'_, AppState>, slug: String) -> Result<Vec<Thread>, String> {
    let threads = store::load_threads(&state.party_dir, &slug).map_err(|e| e.to_string())?;
    let mut active = state.active_threads.lock().unwrap();
    active.insert(slug, threads.clone());
    Ok(threads)
}

#[tauri::command]
pub async fn send_message(
    state: State<'_, AppState>,
    slug: String,
    thread_id: String,
    content: String,
) -> Result<(), String> {
    // Create and persist user message
    let msg = Message {
        id: Uuid::new_v4(),
        role: Role::You,
        content: content.clone(),
        timestamp: Utc::now(),
    };

    // Find thread and append message
    {
        let mut active = state.active_threads.lock().unwrap();
        if let Some(threads) = active.get_mut(&slug) {
            if let Some(thread) = threads.iter_mut().find(|t| t.id.to_string() == thread_id) {
                thread.messages.push(msg);
                store::save_thread(&state.party_dir, &slug, thread).map_err(|e| e.to_string())?;
            }
        }
    }

    // Get session_id for this agent
    let session_id = {
        let agents = store::list_agents(&state.party_dir).map_err(|e| e.to_string())?;
        agents.iter().find(|a| a.slug == slug).and_then(|a| a.session_id.clone())
    };

    // Ensure bridge is running
    {
        let mut bridge_lock = state.bridge.lock().unwrap();
        if bridge_lock.is_none() {
            let script = store::bridge_script_path(&state.party_dir);
            let bridge = Bridge::spawn(
                &script,
                &state.party_dir,
                &state.config.working_dir,
                &state.env_vars,
            ).await.map_err(|e| e.to_string())?;
            *bridge_lock = Some(bridge);
        }
    }

    // Send to bridge
    {
        let mut bridge_lock = state.bridge.lock().unwrap();
        if let Some(ref mut bridge) = *bridge_lock {
            bridge.send_message(&slug, &content, session_id.as_deref())
                .await
                .map_err(|e| e.to_string())?;
        }
    }

    // Mark as thinking
    {
        let mut thinking = state.thinking.lock().unwrap();
        thinking.insert(slug, true);
    }

    Ok(())
}

#[tauri::command]
pub fn poll_events(state: State<'_, AppState>) -> Result<Vec<AgentEvent>, String> {
    // Drain events from bridge
    {
        let mut bridge_lock = state.bridge.lock().unwrap();
        if let Some(ref mut bridge) = *bridge_lock {
            while let Some(event) = bridge.try_recv() {
                let mut pending = state.pending_events.lock().unwrap();

                // Handle result events: save session_id, update cost
                if event.event_type == "result" {
                    if let (Some(sid), Some(agent_slug)) = (&event.session_id, Some(&event.agent)) {
                        if !sid.is_empty() {
                            if let Ok(mut agent) = store::load_agent(&state.party_dir, agent_slug) {
                                agent.session_id = Some(sid.clone());
                                if let Some(cost) = event.cost_usd {
                                    agent.total_cost_usd += cost;
                                }
                                let _ = store::save_agent(&state.party_dir, &agent);
                            }
                        }
                    }
                    let mut thinking = state.thinking.lock().unwrap();
                    thinking.remove(&event.agent);
                }

                if event.event_type == "error" {
                    let mut thinking = state.thinking.lock().unwrap();
                    thinking.remove(&event.agent);
                }

                pending.push(event);
            }
        }
    }

    // Return and clear pending events
    let mut pending = state.pending_events.lock().unwrap();
    let events: Vec<AgentEvent> = pending.drain(..).collect();
    Ok(events)
}

// ── Sidebar ─────────────────────────────────────────────────────────────────

#[tauri::command]
pub fn get_file_tree(state: State<'_, AppState>, slug: String) -> Result<FileNode, String> {
    store::build_file_tree(&state.party_dir, &slug).map_err(|e| e.to_string())
}

// ── Threads ─────────────────────────────────────────────────────────────────

#[tauri::command]
pub fn fork_thread(
    state: State<'_, AppState>,
    slug: String,
    source_thread_id: String,
) -> Result<Thread, String> {
    let source_id: Uuid = source_thread_id.parse().map_err(|e: uuid::Error| e.to_string())?;

    let msg_count = {
        let active = state.active_threads.lock().unwrap();
        active.get(&slug)
            .and_then(|threads| threads.iter().find(|t| t.id == source_id))
            .map(|t| t.messages.len())
            .unwrap_or(0)
    };

    let thread_count = {
        let active = state.active_threads.lock().unwrap();
        active.get(&slug).map(|t| t.len()).unwrap_or(0)
    };

    let new_thread = Thread {
        id: Uuid::new_v4(),
        label: format!("Fork {}", thread_count),
        messages: vec![],
        forked_from: Some((source_id, msg_count)),
        created_at: Utc::now(),
    };

    store::save_thread(&state.party_dir, &slug, &new_thread).map_err(|e| e.to_string())?;

    {
        let mut active = state.active_threads.lock().unwrap();
        if let Some(threads) = active.get_mut(&slug) {
            threads.push(new_thread.clone());
        }
    }

    Ok(new_thread)
}

// ── Config ──────────────────────────────────────────────────────────────────

#[tauri::command]
pub fn get_config(state: State<'_, AppState>) -> Result<PartyConfig, String> {
    Ok(state.config.clone())
}

#[tauri::command]
pub fn is_thinking(state: State<'_, AppState>, slug: String) -> Result<bool, String> {
    let thinking = state.thinking.lock().unwrap();
    Ok(thinking.get(&slug).copied().unwrap_or(false))
}
```

- [ ] **Step 3: Register all commands in main.rs**

Replace `src-tauri/src/main.rs`:

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod agent_runner;
mod commands;
mod env_loader;
mod models;
mod state;
mod store;

use state::AppState;
use std::collections::HashMap;
use std::sync::Mutex;

fn main() {
    let party_dir = store::default_party_dir();
    store::init_party_dir(&party_dir).expect("Failed to init party dir");

    let config = store::load_config(&party_dir).expect("Failed to load config");
    let env_vars = env_loader::load_env(&config.env_file).unwrap_or_default();

    let app_state = AppState {
        party_dir,
        config,
        env_vars,
        bridge: Mutex::new(None),
        active_threads: Mutex::new(HashMap::new()),
        pending_events: Mutex::new(Vec::new()),
        thinking: Mutex::new(HashMap::new()),
    };

    tauri::Builder::default()
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            commands::list_agents,
            commands::create_agent,
            commands::delete_agent,
            commands::load_threads,
            commands::send_message,
            commands::poll_events,
            commands::get_file_tree,
            commands::fork_thread,
            commands::get_config,
            commands::is_thinking,
        ])
        .run(tauri::generate_context!())
        .expect("error running PARTY");
}
```

- [ ] **Step 4: Verify it compiles**

```bash
cd ~/Desktop/party/src-tauri && cargo build
```

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/party
git add -A
git commit -m "feat: add Tauri IPC commands for all operations"
```

---

## Task 3: Frontend — HTML Structure + CSS Theme

**Files:**
- Create: `src/index.html`
- Create: `src/style.css`

- [ ] **Step 1: Write index.html**

Replace `src/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PARTY</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div id="app">

    <!-- Agent Sidebar -->
    <aside id="sidebar">
      <div class="sidebar-header">AGENTS</div>
      <div id="agent-list"></div>
      <button id="new-agent-btn" onclick="showCreateModal()">+ New Agent</button>
    </aside>

    <!-- Chat Area -->
    <main id="chat">
      <div id="empty-state">
        <h2>PARTY</h2>
        <p>AI Agent Management</p>
        <p class="dim">Select an agent to start chatting</p>
      </div>

      <div id="chat-content" class="hidden">
        <!-- Header -->
        <header id="chat-header">
          <div class="agent-info">
            <span id="agent-name"></span>
            <span id="agent-status"></span>
            <span id="agent-role" class="dim"></span>
          </div>
          <div class="tab-buttons">
            <button class="tab-btn" onclick="openPanel('threads')">Threads</button>
            <button class="tab-btn" onclick="openPanel('files')">Files</button>
          </div>
        </header>

        <!-- Thread indicator -->
        <div id="thread-bar" class="hidden">
          <span id="thread-label"></span>
        </div>

        <!-- Messages -->
        <div id="messages"></div>

        <!-- Thinking indicator -->
        <div id="thinking" class="hidden">
          <span class="role role-agent">agent</span>
          <span class="thinking-dots">thinking...</span>
        </div>

        <!-- Input -->
        <footer id="input-area">
          <input type="text" id="message-input" placeholder="Type a message..."
                 onkeydown="if(event.key==='Enter')sendMessage()" />
          <button id="send-btn" onclick="sendMessage()">Send</button>
        </footer>
      </div>
    </main>

    <!-- Slide Panel (Threads / Files) -->
    <aside id="slide-panel" class="hidden">
      <div class="panel-header">
        <span id="panel-title"></span>
        <button class="panel-close" onclick="closePanel()">✕</button>
      </div>
      <div id="panel-content"></div>
    </aside>

    <!-- Create Agent Modal -->
    <div id="create-modal" class="hidden">
      <div class="modal-content">
        <h3>New Agent</h3>
        <input type="text" id="new-agent-name" placeholder="Agent name" />
        <input type="text" id="new-agent-role" placeholder="Role description" />
        <div class="modal-actions">
          <button onclick="hideCreateModal()">Cancel</button>
          <button class="primary" onclick="createAgent()">Create</button>
        </div>
      </div>
    </div>

  </div>

  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write style.css**

Create `src/style.css`:

```css
/* ── Reset + Variables ──────────────────────────────────────────────────── */

:root {
  --bg: #e8e8e8;
  --surface: #dedede;
  --border: #cccccc;
  --active: #aaaaaa;
  --text: #2a2a2a;
  --dim: #888888;
  --accent: #4a7a9a;
  --alert: #9a4a4a;
  --success: #4a8a4a;
  --warning: #8a7a4a;
  --radius: 6px;
  --font: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
  --mono: 'SF Mono', 'Menlo', 'Consolas', monospace;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  height: 100vh;
  overflow: hidden;
}

.hidden { display: none !important; }
.dim { color: var(--dim); }

/* ── App Layout ─────────────────────────────────────────────────────────── */

#app {
  display: flex;
  height: 100vh;
}

/* ── Sidebar ────────────────────────────────────────────────────────────── */

#sidebar {
  width: 220px;
  min-width: 220px;
  background: #e0e0e0;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.sidebar-header {
  padding: 16px;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--dim);
  font-weight: 600;
}

#agent-list {
  flex: 1;
  padding: 0 8px;
}

.agent-card {
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: var(--radius);
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: background 0.15s;
}

.agent-card:hover {
  background: var(--surface);
}

.agent-card.active {
  background: #d4d4d4;
  border-left-color: var(--accent);
}

.agent-card .name {
  font-weight: 600;
  font-size: 13px;
}

.agent-card .role {
  font-size: 11px;
  color: var(--dim);
  margin-top: 2px;
}

.agent-card .status {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  font-size: 10px;
}

.agent-card .status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-active { color: var(--success); }
.status-active .status-dot { background: var(--success); }
.status-idle { color: var(--dim); }
.status-idle .status-dot { background: var(--dim); }
.status-error { color: var(--alert); }
.status-error .status-dot { background: var(--alert); }

#new-agent-btn {
  margin: 8px;
  padding: 10px;
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  background: none;
  color: var(--dim);
  cursor: pointer;
  font-family: var(--font);
  font-size: 13px;
  transition: border-color 0.15s;
}

#new-agent-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* ── Chat Area ──────────────────────────────────────────────────────────── */

#chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

#empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

#empty-state h2 {
  color: var(--accent);
  font-size: 24px;
  font-weight: 600;
}

#chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ── Chat Header ────────────────────────────────────────────────────────── */

#chat-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.agent-info {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

#agent-name {
  font-weight: 600;
  font-size: 15px;
}

#agent-status {
  font-size: 11px;
}

#agent-role {
  font-size: 12px;
}

.tab-buttons {
  display: flex;
  gap: 6px;
}

.tab-btn {
  background: var(--surface);
  border: none;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--dim);
  cursor: pointer;
  font-family: var(--font);
}

.tab-btn:hover {
  background: var(--border);
}

/* ── Thread Bar ─────────────────────────────────────────────────────────── */

#thread-bar {
  padding: 6px 16px;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  color: var(--dim);
  background: var(--surface);
}

/* ── Messages ───────────────────────────────────────────────────────────── */

#messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.message {
  margin-bottom: 16px;
}

.message-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}

.role {
  font-weight: 600;
  font-size: 13px;
}

.role-you { color: var(--accent); }
.role-agent { color: var(--success); }
.role-sys { color: var(--warning); }

.timestamp {
  color: var(--dim);
  font-size: 11px;
}

.message-content {
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* ── Tool Blocks ────────────────────────────────────────────────────────── */

.tool-block {
  margin-top: 6px;
}

.tool-header {
  background: var(--surface);
  border-radius: 4px;
  padding: 6px 10px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--dim);
}

.tool-header .tool-name {
  color: var(--accent);
  font-weight: 600;
}

.tool-output {
  background: #d8d8d8;
  border-radius: 4px;
  padding: 6px 10px;
  margin-top: 2px;
  font-family: var(--mono);
  font-size: 11px;
  color: #666;
  max-height: 200px;
  overflow-y: auto;
}

/* ── Inline Blocks ──────────────────────────────────────────────────────── */

.metric-block {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 10px 14px;
  margin-top: 8px;
  font-family: var(--mono);
  font-size: 12px;
}

.metric-block .label { color: var(--dim); font-size: 11px; }
.metric-block .value { font-weight: 600; }
.metric-block .delta-positive { color: var(--success); }
.metric-block .delta-negative { color: var(--alert); }

.code-block {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 10px 14px;
  margin-top: 8px;
  font-family: var(--mono);
  font-size: 12px;
  white-space: pre;
  overflow-x: auto;
}

.code-block .lang { color: var(--dim); font-size: 10px; margin-bottom: 4px; }

/* ── Thinking ───────────────────────────────────────────────────────────── */

#thinking {
  padding: 8px 16px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.thinking-dots {
  color: var(--dim);
  font-style: italic;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

/* ── Input ──────────────────────────────────────────────────────────────── */

#input-area {
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

#message-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: #f0f0f0;
  font-size: 13px;
  font-family: var(--font);
  outline: none;
  transition: border-color 0.15s;
}

#message-input:focus {
  border-color: var(--accent);
}

#send-btn {
  padding: 10px 20px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius);
  font-size: 13px;
  font-family: var(--font);
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

#send-btn:hover {
  background: #3d6a87;
}

/* ── Slide Panel ────────────────────────────────────────────────────────── */

#slide-panel {
  width: 280px;
  min-width: 280px;
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.panel-close {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: var(--dim);
}

#panel-content {
  flex: 1;
  padding: 12px;
}

/* ── File Tree ──────────────────────────────────────────────────────────── */

.file-node {
  padding: 3px 0;
  cursor: pointer;
  font-size: 12px;
}

.file-node:hover { color: var(--accent); }
.file-node .icon { color: var(--dim); margin-right: 4px; }
.file-node.dir { font-weight: 600; }

/* ── Thread List ────────────────────────────────────────────────────────── */

.thread-item {
  padding: 8px 10px;
  border-radius: var(--radius);
  cursor: pointer;
  margin-bottom: 4px;
}

.thread-item:hover { background: var(--surface); }
.thread-item.active { background: #d4d4d4; border-left: 3px solid var(--accent); }
.thread-item .label { font-weight: 600; }
.thread-item .count { color: var(--dim); font-size: 11px; }
.thread-item .fork-marker { color: var(--dim); font-size: 11px; }

/* ── Modal ──────────────────────────────────────────────────────────────── */

#create-modal {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 24px;
  width: 360px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
}

.modal-content h3 { margin-bottom: 16px; }

.modal-content input {
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-family: var(--font);
  font-size: 13px;
  background: #f0f0f0;
  outline: none;
}

.modal-content input:focus { border-color: var(--accent); }

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

.modal-actions button {
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: none;
  cursor: pointer;
  font-family: var(--font);
  font-size: 13px;
}

.modal-actions button.primary {
  background: var(--accent);
  color: white;
  border: none;
}
```

- [ ] **Step 3: Verify the HTML loads**

```bash
cd ~/Desktop/party && cargo tauri dev 2>&1 | tail -5
```

Expected: Window opens with the layout visible.

- [ ] **Step 4: Commit**

```bash
cd ~/Desktop/party
git add src/
git commit -m "feat: add HTML structure and CSS theme for desktop app"
```

---

## Task 4: Frontend — JavaScript Application Logic

**Files:**
- Create: `src/app.js`

- [ ] **Step 1: Write app.js**

Create `src/app.js`:

```javascript
// ── State ──────────────────────────────────────────────────────────────────

const { invoke } = window.__TAURI__.core;

const state = {
  agents: [],
  activeSlug: null,
  threads: [],
  activeThreadId: null,
  pollInterval: null,
};

// ── Init ───────────────────────────────────────────────────────────────────

async function init() {
  await loadAgents();
  startPolling();
}

// ── Agents ─────────────────────────────────────────────────────────────────

async function loadAgents() {
  state.agents = await invoke('list_agents');
  renderAgentList();
}

function renderAgentList() {
  const list = document.getElementById('agent-list');
  list.innerHTML = state.agents.map(agent => `
    <div class="agent-card ${agent.slug === state.activeSlug ? 'active' : ''}"
         onclick="selectAgent('${agent.slug}')"
         oncontextmenu="event.preventDefault(); confirmDelete('${agent.slug}', '${agent.name}')">
      <div class="name">${agent.name}</div>
      <div class="role">${agent.role}</div>
      <div class="status status-${agent.status.toLowerCase()}">
        <div class="status-dot"></div>
        ${agent.status}
      </div>
    </div>
  `).join('');
}

async function selectAgent(slug) {
  state.activeSlug = slug;
  const agent = state.agents.find(a => a.slug === slug);

  // Update sidebar
  renderAgentList();

  // Show chat
  document.getElementById('empty-state').classList.add('hidden');
  document.getElementById('chat-content').classList.remove('hidden');

  // Update header
  document.getElementById('agent-name').textContent = agent.name;
  document.getElementById('agent-status').textContent = '● ' + agent.status;
  document.getElementById('agent-status').className = 'status-' + agent.status.toLowerCase();
  document.getElementById('agent-role').textContent = '·  ' + agent.role;

  // Load threads
  state.threads = await invoke('load_threads', { slug });
  if (state.threads.length > 0) {
    state.activeThreadId = state.threads[0].id;
    renderMessages(state.threads[0].messages);
    updateThreadBar();
  }

  // Focus input
  document.getElementById('message-input').focus();
}

// ── Messages ───────────────────────────────────────────────────────────────

function renderMessages(messages) {
  const container = document.getElementById('messages');
  container.innerHTML = messages.map(msg => renderMessage(msg)).join('');
  container.scrollTop = container.scrollHeight;
}

function renderMessage(msg) {
  const roleClass = msg.role === 'You' ? 'role-you' : msg.role === 'Agent' ? 'role-agent' : 'role-sys';
  const roleLabel = msg.role === 'You' ? 'you' : msg.role === 'Agent' ? 'agent' : 'sys';
  const time = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // Check for tool blocks in system messages
  if (msg.role === 'System' && msg.content.startsWith('[code:')) {
    const match = msg.content.match(/^\[code:\s*(\w+)\]\s*(.*)$/);
    if (match) {
      return `<div class="message"><div class="tool-block">
        <div class="tool-header"><span class="tool-name">⚡ ${match[1]}</span> ${escapeHtml(match[2])}</div>
      </div></div>`;
    }
  }

  if (msg.role === 'System' && msg.content.startsWith('→ ')) {
    return `<div class="message"><div class="tool-block">
      <div class="tool-output">${escapeHtml(msg.content)}</div>
    </div></div>`;
  }

  return `<div class="message">
    <div class="message-header">
      <span class="role ${roleClass}">${roleLabel}</span>
      <span class="timestamp">${time}</span>
    </div>
    <div class="message-content">${escapeHtml(msg.content)}</div>
  </div>`;
}

function appendMessage(msg) {
  const container = document.getElementById('messages');
  container.innerHTML += renderMessage(msg);
  container.scrollTop = container.scrollHeight;
}

// ── Send Message ───────────────────────────────────────────────────────────

async function sendMessage() {
  const input = document.getElementById('message-input');
  const content = input.value.trim();
  if (!content || !state.activeSlug || !state.activeThreadId) return;

  input.value = '';

  // Append user message immediately
  const msg = { role: 'You', content, timestamp: new Date().toISOString() };
  appendMessage(msg);

  // Show thinking
  document.getElementById('thinking').classList.remove('hidden');

  // Send to backend
  await invoke('send_message', {
    slug: state.activeSlug,
    threadId: state.activeThreadId,
    content,
  });
}

// ── Polling ────────────────────────────────────────────────────────────────

function startPolling() {
  state.pollInterval = setInterval(pollEvents, 100);
}

async function pollEvents() {
  const events = await invoke('poll_events');
  for (const event of events) {
    handleEvent(event);
  }
}

function handleEvent(event) {
  // Only render events for the active agent
  if (event.agent !== state.activeSlug) return;

  switch (event.event_type) {
    case 'assistant':
      if (event.content) {
        appendMessage({ role: 'Agent', content: event.content, timestamp: new Date().toISOString() });
      }
      break;

    case 'tool_use':
      appendMessage({
        role: 'System',
        content: `[code: ${event.tool || 'tool'}] ${event.input || ''}`,
        timestamp: new Date().toISOString(),
      });
      break;

    case 'tool_result':
      if (event.output) {
        appendMessage({
          role: 'System',
          content: `→ ${event.output}`,
          timestamp: new Date().toISOString(),
        });
      }
      break;

    case 'result':
      document.getElementById('thinking').classList.add('hidden');
      // Refresh agent list to update status/cost
      loadAgents();
      break;

    case 'error':
      document.getElementById('thinking').classList.add('hidden');
      appendMessage({
        role: 'System',
        content: `⚠ Error: ${event.message || 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      });
      break;

    case 'status':
      if (event.status === 'thinking') {
        document.getElementById('thinking').classList.remove('hidden');
      }
      break;
  }
}

// ── Agent CRUD ─────────────────────────────────────────────────────────────

function showCreateModal() {
  document.getElementById('create-modal').classList.remove('hidden');
  document.getElementById('new-agent-name').focus();
}

function hideCreateModal() {
  document.getElementById('create-modal').classList.add('hidden');
  document.getElementById('new-agent-name').value = '';
  document.getElementById('new-agent-role').value = '';
}

async function createAgent() {
  const name = document.getElementById('new-agent-name').value.trim();
  const role = document.getElementById('new-agent-role').value.trim();
  if (!name) return;

  await invoke('create_agent', { name, role: role || 'General assistant' });
  hideCreateModal();
  await loadAgents();
}

async function confirmDelete(slug, name) {
  if (confirm(`Delete agent "${name}"? This removes all conversations and data.`)) {
    await invoke('delete_agent', { slug });
    if (state.activeSlug === slug) {
      state.activeSlug = null;
      document.getElementById('empty-state').classList.remove('hidden');
      document.getElementById('chat-content').classList.add('hidden');
    }
    await loadAgents();
  }
}

// ── Slide Panel ────────────────────────────────────────────────────────────

async function openPanel(tab) {
  const panel = document.getElementById('slide-panel');
  const title = document.getElementById('panel-title');
  const content = document.getElementById('panel-content');

  panel.classList.remove('hidden');

  if (tab === 'threads') {
    title.textContent = 'Threads';
    content.innerHTML = state.threads.map(t => `
      <div class="thread-item ${t.id === state.activeThreadId ? 'active' : ''}"
           onclick="selectThread('${t.id}')">
        ${t.forked_from ? '<span class="fork-marker">⑂ </span>' : ''}
        <span class="label">${t.label}</span>
        <span class="count">(${t.messages.length})</span>
      </div>
    `).join('') + `
      <button class="tab-btn" style="margin-top:8px;width:100%" onclick="forkThread()">Fork Thread</button>
    `;
  } else if (tab === 'files') {
    title.textContent = 'Files';
    if (state.activeSlug) {
      const tree = await invoke('get_file_tree', { slug: state.activeSlug });
      content.innerHTML = renderFileTree(tree, 0);
    }
  }
}

function closePanel() {
  document.getElementById('slide-panel').classList.add('hidden');
}

function selectThread(threadId) {
  state.activeThreadId = threadId;
  const thread = state.threads.find(t => t.id === threadId);
  if (thread) {
    renderMessages(thread.messages);
    updateThreadBar();
  }
  closePanel();
}

async function forkThread() {
  if (!state.activeSlug || !state.activeThreadId) return;
  const newThread = await invoke('fork_thread', {
    slug: state.activeSlug,
    sourceThreadId: state.activeThreadId,
  });
  state.threads.push(newThread);
  selectThread(newThread.id);
}

function updateThreadBar() {
  const bar = document.getElementById('thread-bar');
  const label = document.getElementById('thread-label');
  if (state.threads.length > 1) {
    const thread = state.threads.find(t => t.id === state.activeThreadId);
    label.textContent = '─── ' + (thread ? thread.label : 'Main') + ' ───';
    bar.classList.remove('hidden');
  } else {
    bar.classList.add('hidden');
  }
}

// ── File Tree ──────────────────────────────────────────────────────────────

function renderFileTree(node, depth) {
  const indent = 'padding-left:' + (depth * 16) + 'px';
  const icon = node.is_dir ? (node.expanded ? '▾' : '▸') : '◇';
  const cls = node.is_dir ? 'dir' : '';
  let html = `<div class="file-node ${cls}" style="${indent}">
    <span class="icon">${icon}</span>${node.name}
  </div>`;
  if (node.is_dir && node.children) {
    for (const child of node.children) {
      html += renderFileTree(child, depth + 1);
    }
  }
  return html;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ── Start ──────────────────────────────────────────────────────────────────

window.addEventListener('DOMContentLoaded', init);
```

- [ ] **Step 2: Verify the full app works**

```bash
cd ~/Desktop/party && cargo tauri dev
```

Expected: Window opens. Agent list shows 6 agents. Click one → chat loads. Type a message → sends to bridge → agent responds.

- [ ] **Step 3: Commit**

```bash
cd ~/Desktop/party
git add src/app.js
git commit -m "feat: add frontend JavaScript — agents, chat, polling, panels"
```

---

## Task 5: Build + Polish

**Files:**
- Modify: `src-tauri/tauri.conf.json` (if needed)
- Modify: Various files for fixes found during testing

- [ ] **Step 1: Build release**

```bash
cd ~/Desktop/party && cargo tauri build
```

Expected: Produces a `.app` bundle in `src-tauri/target/release/bundle/macos/`.

- [ ] **Step 2: Test the built app**

Open the `.app` from Finder. Verify:
1. Agent list loads with all 6 agents
2. Click agent → chat opens
3. Send message → thinking indicator → agent responds
4. Tool use shows as collapsible blocks
5. Threads panel works (open, fork, switch)
6. Files panel shows agent directory tree
7. Create new agent works
8. Right-click delete agent works
9. Resize window — layout responds correctly

- [ ] **Step 3: Fix any issues found during testing**

- [ ] **Step 4: Final commit**

```bash
cd ~/Desktop/party
git add -A
git commit -m "feat: PARTY v0.2.0 — Tauri desktop app"
```

---

## Execution Summary

| Task | What it delivers | Key files |
|------|-----------------|-----------|
| 1 | Tauri project structure, move Rust backend | `src-tauri/` setup |
| 2 | All IPC commands (CRUD, chat, polling) | `commands.rs`, `state.rs`, `main.rs` |
| 3 | HTML structure + complete CSS theme | `index.html`, `style.css` |
| 4 | Frontend JS — full chat app | `app.js` (~250 lines) |
| 5 | Release build + polish | `.app` bundle |

Total: **5 tasks**. The Rust backend is a move-not-rewrite. The frontend is 3 files. The bridge is untouched.
