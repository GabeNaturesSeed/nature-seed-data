# PARTY Tauri Desktop App — Design Specification

**Date:** 2026-04-15
**Status:** Approved
**Repo:** `~/Desktop/party/`

---

## Overview

Replace PARTY's terminal TUI with a Tauri desktop application. The Rust backend (models, store, agent_runner, env_loader, bridge) stays identical. The TUI rendering layer (ratatui, crossterm, ui/*.rs) is replaced by a Tauri shell + vanilla HTML/CSS/JS frontend. The result is a native macOS app with the same light gray aesthetic.

---

## Architecture

```
party/
  src-tauri/                    ← Rust backend (Tauri app)
    src/
      main.rs                   ← Tauri entry, plugin setup, command registration
      commands.rs               ← IPC handlers (list_agents, send_message, etc.)
      models.rs                 ← KEPT: Agent, Thread, Message, InlineBlock, etc.
      store.rs                  ← KEPT: disk I/O
      agent_runner.rs           ← KEPT: Bridge subprocess manager
      env_loader.rs             ← KEPT: .env parser
    Cargo.toml                  ← Tauri deps replace ratatui/crossterm
    tauri.conf.json             ← Window config (title, size, decorations)
  src/                          ← Web frontend (no framework, no build)
    index.html                  ← Single page
    style.css                   ← Light gray theme
    app.js                      ← All frontend logic
  bridge/
    agent_bridge.py             ← KEPT: Claude Agent SDK wrapper
    requirements.txt
```

### What Stays (zero changes)
- `models.rs` — all data types
- `store.rs` — disk persistence
- `agent_runner.rs` — Bridge subprocess management
- `env_loader.rs` — .env parser
- `bridge/agent_bridge.py` — Python sidecar

### What Gets Removed
- `tui.rs` — terminal setup/teardown
- `theme.rs` — Ratatui color constants
- `src/ui/` — all 12 TUI rendering files
- `app.rs` — App struct + event loop (replaced by commands.rs + Tauri)
- Dependencies: `ratatui`, `crossterm`

### What's New
- `commands.rs` — Tauri IPC command handlers
- `main.rs` — Tauri app bootstrap (replaces TUI event loop)
- `Cargo.toml` — Tauri dependencies
- `tauri.conf.json` — window configuration
- `src/index.html` — single-page frontend
- `src/style.css` — CSS theme
- `src/app.js` — frontend logic

---

## Tauri IPC Commands (`commands.rs`)

All functions are `#[tauri::command]` handlers that the frontend calls via `invoke()`.

### Agent CRUD
```rust
fn list_agents() -> Result<Vec<Agent>, String>
fn create_agent(name: String, role: String) -> Result<Agent, String>
fn delete_agent(slug: String) -> Result<(), String>
```

### Chat
```rust
fn load_threads(slug: String) -> Result<Vec<Thread>, String>
fn send_message(slug: String, thread_id: String, content: String) -> Result<(), String>
fn poll_events() -> Result<Vec<AgentEvent>, String>
```

`send_message` persists the user message to disk and pipes it to the bridge. Returns immediately. The frontend polls `poll_events()` on a 100ms interval to receive agent responses.

### Sidebar Data
```rust
fn get_file_tree(slug: String) -> Result<FileNode, String>
```

### Thread Management
```rust
fn fork_thread(slug: String, source_thread_id: String) -> Result<Thread, String>
```

### Config
```rust
fn get_config() -> Result<PartyConfig, String>
```

---

## Frontend

### index.html

Single page, two-panel layout:

```html
<body>
  <div id="app">
    <aside id="sidebar">
      <div class="sidebar-header">AGENTS</div>
      <div id="agent-list"></div>
      <button id="new-agent-btn">+ New Agent</button>
    </aside>
    <main id="chat">
      <header id="chat-header">
        <div class="agent-info"><!-- name, status, role --></div>
        <div class="tab-buttons"><!-- Threads, Files --></div>
      </header>
      <div id="messages"></div>
      <footer id="input-area">
        <input type="text" id="message-input" placeholder="Type a message..." />
        <button id="send-btn">Send</button>
      </footer>
    </main>
    <aside id="slide-panel" class="hidden">
      <!-- Threads / Files / Projects content -->
    </aside>
  </div>
</body>
```

### style.css

Light gray theme (same palette as TUI spec):

```css
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
}
```

Font stack: `-apple-system, BlinkMacSystemFont, 'Inter', sans-serif`
Code font: `'SF Mono', 'Menlo', monospace`

Layout: CSS Grid — sidebar 220px fixed, chat fluid. Messages area `overflow-y: auto` with `flex: 1`. Input bar fixed at bottom.

### app.js

~300 lines, no framework. Key functions:

- `init()` — load agents, select first, start polling
- `loadAgents()` → `invoke('list_agents')`, render sidebar
- `selectAgent(slug)` → `invoke('load_threads', {slug})`, render chat
- `sendMessage()` → `invoke('send_message', {...})`, append user message, show thinking
- `pollLoop()` — `setInterval` at 100ms, calls `invoke('poll_events')`, appends messages
- `renderMessage(msg)` — HTML for role-styled message with timestamp
- `renderToolUse(event)` — collapsible code block for tool calls
- `renderInlineBlock(block)` — metric/table/approval/code blocks as HTML
- `openSlidePanel(tab)` — threads/files slide-in from right
- `createAgent()` — prompt modal, calls `invoke('create_agent', {...})`
- `deleteAgent(slug)` — confirm, calls `invoke('delete_agent', {slug})`

### Message Rendering

Messages auto-scroll to bottom. Each message is a div:

```html
<div class="message">
  <div class="message-header">
    <span class="role role-agent">agent</span>
    <span class="timestamp">08:00</span>
  </div>
  <div class="message-content">Response text here...</div>
</div>
```

Tool use blocks render as collapsible:
```html
<div class="tool-block">
  <div class="tool-header">⚡ Bash <span class="tool-input">python3 daily_pull.py</span></div>
  <div class="tool-output">→ Revenue: $4,231</div>
</div>
```

Inline blocks (metric, table, approval, code) render as styled HTML elements matching the TUI box-drawing aesthetic but with proper CSS.

### Thinking Indicator

While waiting for agent response, show pulsing dots:
```html
<div class="thinking">
  <span class="role role-agent">agent</span>
  <span class="thinking-dots">thinking...</span>
</div>
```

---

## Tauri Configuration

### tauri.conf.json

```json
{
  "app": {
    "windows": [{
      "title": "PARTY — AI Agent Management",
      "width": 1200,
      "height": 800,
      "minWidth": 600,
      "minHeight": 400,
      "decorations": true,
      "resizable": true
    }]
  }
}
```

### Cargo.toml changes

Remove: `ratatui`, `crossterm`
Add: `tauri`, `tauri-build`, `serde` (already present)
Keep: `tokio`, `serde`, `serde_json`, `chrono`, `uuid`, `dirs`, `anyhow`

---

## State Management

The frontend has minimal state:

```javascript
const state = {
  agents: [],           // from list_agents()
  activeSlug: null,     // currently selected agent
  threads: [],          // from load_threads()
  activeThreadId: null, // selected thread
  pollInterval: null,   // setInterval ID
  thinking: {},         // {slug: true/false}
};
```

The Rust backend remains the source of truth. The frontend re-fetches on actions (create/delete agent refreshes the list, sending a message refreshes via polling).

---

## What This Spec Does NOT Include

- Dark mode toggle (future — light gray only for v1)
- Drag-and-drop file upload
- Notification badges / system tray
- Auto-update mechanism
- Multiple windows
