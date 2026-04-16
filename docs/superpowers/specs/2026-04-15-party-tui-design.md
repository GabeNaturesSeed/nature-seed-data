# PARTY v1 — Design Specification

**Date:** 2026-04-15
**Status:** Approved
**Repo:** Standalone (new repository, separate from ClaudeDataAgent)

---

## Overview

PARTY is a native Rust TUI application for managing AI agents. A single operator manages multiple domain-specific agents (Google Ads, Email Marketing, SEO, etc.) through threaded conversations, each agent with its own persistent memory, instructions, skills, and project tracking. The terminal is mission control; the agents are the fleet.

v1 delivers the complete TUI shell — all screens, panes, persistence, and rendering — without an AI backend. Messages are journaled (no agent responses). The AI integration comes in a future version.

---

## Tech Stack

- **Language:** Rust (2021 edition), single binary
- **TUI:** Ratatui 0.29 + Crossterm 0.28
- **Async:** Tokio 1 (full features)
- **Serialization:** Serde + serde_json
- **Time:** Chrono 0.4 (serde)
- **IDs:** UUID v4 (serde)
- **Paths:** dirs 5
- **Errors:** anyhow 1

No database, no web server, no JavaScript. Compiles with `cargo build --release`.

---

## Architecture

### Approach: Modular UI

Single `App` state struct with unidirectional data flow (Elm/Redux pattern). UI rendering split into focused sub-modules to keep files under 300 lines.

### Module Structure

```
src/
  main.rs             — entry point: init terminal, run app, restore on exit
  app.rs              — App state struct + event loop + top-level input dispatch
  models.rs           — all data types
  store.rs            — disk I/O: load/save from ~/.party/
  tui.rs              — terminal setup/teardown (raw mode, alternate screen)
  theme.rs            — color palette constants, style helpers
  ui/
    mod.rs            — top-level render() dispatcher
    agent_list.rs     — agent list page
    chat.rs           — chat page layout (3-pane split, delegates to sub-modules)
    threads.rs        — thread list pane
    messages.rs       — message stream pane + scroll logic
    sidebar.rs        — sidebar container (tab switching)
    files.rs          — Tab 1: file tree renderer
    projects.rs       — Tab 2: project list with progress bars
    context.rs        — Tab 3: token usage + snapshots
    blocks.rs         — inline block renderers (metric, table, approval, code)
    input.rs          — input bar at bottom
    help.rs           — contextual help bar
    responsive.rs     — breakpoint logic, pane collapse decisions
```

### Data Flow

1. **State** lives in `App` (single struct in `app.rs`) — single source of truth
2. **Events** from Crossterm polling (50ms interval), dispatched by current screen/pane
3. **Rendering** is a pure function of state — `ui::render(frame, &app)` never mutates state
4. **Persistence** on state changes — async writes via Tokio `spawn_blocking`

---

## Data Models

All types implement `Serialize`/`Deserialize`.

### Agent

```
Agent
  ├── id: Uuid
  ├── name: String
  ├── slug: String              (derived from name, used as folder name)
  ├── role: String
  ├── status: AgentStatus       (Active | Idle | Error | Offline)
  ├── channels: Vec<String>     (credential key references)
  ├── projects: Vec<Project>
  ├── context_snapshots: Vec<ContextSnapshot>
  └── created_at: DateTime
```

### Thread

```
Thread
  ├── id: Uuid
  ├── label: String
  ├── messages: Vec<Message>
  ├── forked_from: Option<(Uuid, usize)>   (thread_id, message_index)
  └── created_at: DateTime
```

### Message

```
Message
  ├── id: Uuid
  ├── role: Role                (You | Agent | System)
  ├── content: String           (raw text, may contain inline syntax)
  ├── blocks: Vec<InlineBlock>  (parsed from content at render time, not persisted)
  └── timestamp: DateTime
```

### InlineBlock (enum)

```
InlineBlock
  ├── Metric { label: String, value: String, delta: Option<String> }
  ├── Table { headers: Vec<String>, rows: Vec<Vec<String>> }
  ├── Approval { action: String, status: ApprovalStatus }   (Pending | Approved | Rejected)
  └── Code { language: Option<String>, code: String }
```

### Supporting Types

```
Project
  ├── name: String
  ├── status: ProjectStatus     (Active | Paused | Done)
  └── progress: f32             (0.0 to 1.0)

ContextSnapshot
  ├── label: String
  ├── saved_at: DateTime
  └── token_count: u64

FileNode (runtime only, not persisted)
  ├── name: String
  ├── is_dir: bool
  ├── size: Option<u64>
  ├── children: Vec<FileNode>
  └── expanded: bool
```

### Inline Block Syntax

Parsed at render time from `Message.content`. Raw syntax is the source of truth. Block syntax must appear on its own line (not inline within a sentence) to avoid false matches with natural `|` usage in text.

| Type | Syntax |
|------|--------|
| Metric | `[metric: Label \| 98.7% \| +1.2%]` |
| Table | `[table: H1, H2, H3 \| val1, val2, val3 \| val4, val5, val6]` |
| Approval | `[approval: Deploy new bid strategy \| pending]` |
| Code | `[code: rust] fn main() {}` or triple-backtick fenced blocks |

The parser scans each line independently. A line starting with `[metric:`, `[table:`, `[approval:`, or `[code:` triggers block parsing. Lines not matching these patterns render as plain text.

---

## Disk Persistence

### Directory Structure

```
~/.party/
  config.json                    — future: global settings
  agents/
    {slug}/                      — one folder per agent
      agent.json                 — metadata (name, role, status, projects, snapshots)
      conversations/
        main.json                — default thread (auto-created)
        {label}.json             — additional threads
      memory/                    — empty on init, user-populated
      instructions/              — empty on init, user-populated
      skills/                    — empty on init, user-populated
      data/                      — empty on init, user-populated
```

### Design Decisions

- **Separate files for metadata vs conversations.** `agent.json` is small (no messages). Each thread is its own JSON file. Sending a message only rewrites one thread file.
- **Slug as folder name.** Derived from agent name ("Google Ads" → `google-ads`). Stored in `agent.json` so renames don't break paths.
- **Lazy loading.** Startup reads all `agent.json` files (lightweight). Thread messages load only when entering an agent's chat.
- **Write-on-change.** Messages flush to disk immediately on send. Metadata saves on state changes. Async via `spawn_blocking`.
- **Empty subdirs on init.** `memory/`, `instructions/`, `skills/`, `data/` created when agent is born. User populates them with AGENT.md, skill files, etc.
- **First run.** If `~/.party/` doesn't exist, create the full structure. No seeded agents — blank slate.

---

## Screens

### Page 1: Agent List

Full terminal width, horizontally centered with 15% margins. Thin header, help bar at bottom, agent table in between.

**Per row (double-height):**
- Selection cursor `▸`
- Agent name (bold)
- Status badge (ACTIVE/IDLE/ERROR/OFFLINE) — color-coded
- Channel count
- Project count
- Unread count (only if > 0, alert color)

**Selected row:** Subtle surface-color background highlight.

**Keys:** `j/k` or arrows to navigate, `Enter` to open chat, `n` to create agent, `d` to delete agent, `q` to quit.

### Page 2: Chat (3-Pane Cockpit)

```
┌─────────────────────────────────────────────────────────────────┐
│  ◂  Agent Name   STATUS  ·  Role description                    │  header
├────────────┬────────────────────────────────────┬───────────────┤
│  threads   │  messages                          │  sidebar      │
│            │                                    │  (1/2/3 tabs) │
├────────────┴────────────────────────────────────┴───────────────┤
│  input bar                                                       │
├─────────────────────────────────────────────────────────────────┤
│  help bar                                                        │
└─────────────────────────────────────────────────────────────────┘
```

**Pane proportions (wide):** Threads 22col fixed, Sidebar 34col fixed, Messages fluid.

#### Threads Pane
- Lists all threads for the current agent
- Each agent starts with one "Main" thread (auto-created)
- Shows: label, fork marker `⑂` (if forked), message count
- `f` to fork a new thread from current thread's last message

#### Messages Pane
- Chronological message stream with role labels and timestamps
- Role colors: `you` in accent, `agent` in success, `sys` in warning
- Format: `role  HH:MM` then indented content on next lines
- Inline blocks rendered below message text using box-drawing characters
- `j/k` scrolls, scroll indicator in top-right

#### Sidebar (3 Tabs)
- **Tab 1 — Files:** Read-only navigable file tree of `~/.party/agents/{slug}/`. Folders expand/collapse with Enter. `▾`/`▸` for folders, `◇` for files.
- **Tab 2 — Projects:** List with name, status badge, percentage, horizontal progress bar (`━` filled, `─` empty).
- **Tab 3 — Context:** Token usage fraction + progress bar, list of saved context snapshots with label/date/token count.

#### Input Mode
- `i` to enter (vim-style), accent-colored border on input bar
- Type message, `Enter` to send, `Esc` to cancel
- Message appended to current thread, persisted to disk immediately

#### Pane Focus
- `Tab` cycles forward: Threads → Messages → Sidebar
- `Shift+Tab` cycles backward
- Focused pane gets brighter (active-color) border
- Navigation keys apply to focused pane

---

## Agent CRUD

### Create (`n` on agent list)
1. Inline prompt at bottom: "Agent name:" — type name, Enter
2. Second prompt: "Role:" — type role description, Enter
3. Agent created: status Idle, one "Main" thread, four empty subdirs on disk
4. Drops into agent's chat

### Delete (`d` on agent list)
1. Confirmation prompt: "Delete {name}? y/n"
2. On `y`: removes `~/.party/agents/{slug}/` directory entirely

---

## State Machine

```
┌─────────────┐     Enter      ┌─────────────┐
│  AgentList  │ ──────────────▸ │    Chat     │
│             │ ◂────────────── │             │
└─────────────┘   Esc          └─────────────┘
```

### App State

```
App
  ├── screen: Screen                (AgentList | Chat)
  ├── agents: Vec<Agent>
  ├── selected_agent: usize
  ├── active_agent: Option<usize>
  ├── focus: Pane                   (Threads | Messages | Sidebar)
  ├── sidebar_tab: SidebarTab       (Files | Projects | Context)
  ├── selected_thread: usize
  ├── selected_file: usize
  ├── selected_project: usize
  ├── scroll_offset: usize
  ├── input_mode: bool
  ├── input_buffer: String
  ├── file_tree: Option<FileNode>
  └── terminal_size: (u16, u16)
```

### Input Dispatch

```
if input_mode:
    Enter     → send message, persist, exit input mode
    Esc       → cancel, clear buffer, exit input mode
    chars     → append to buffer
    Backspace → delete from buffer

else match screen:
    AgentList:
        j/↓   → cursor down
        k/↑   → cursor up
        Enter  → open agent chat
        n      → create new agent
        d      → delete selected agent
        q      → quit

    Chat:
        i      → enter input mode
        Tab    → focus forward
        S-Tab  → focus backward
        Esc    → back to agent list
        1/2/3  → switch sidebar tab

        Threads focused:  j/k navigate, Enter select, f fork
        Messages focused: j/k scroll
        Files focused:    j/k navigate, Enter expand/collapse
        Projects focused: j/k navigate
        Context focused:  j/k navigate
```

---

## Responsive Layout

Managed by `ui/responsive.rs`. Three breakpoints based on terminal width:

### Wide (120+ columns)
Full 3-pane layout. Threads 22col, Sidebar 34col, Messages fluid.

### Medium (80–119 columns)
Sidebar hidden. Threads + Messages only. Press `1/2/3` to toggle sidebar as overlay (replaces messages pane temporarily).

### Narrow (< 80 columns)
Single-pane mode. Only the focused pane is visible full-width. Tab cycles between Threads → Messages → Sidebar.

Agent list page needs no responsive logic — centered list works at any width.

---

## Color Palette (Light Gray Theme)

True color only (RGB values). No 256-color fallback.

| Role       | Hex       | RGB             | Usage                                        |
|------------|-----------|-----------------|----------------------------------------------|
| Background | `#e8e8e8` | `(232, 232, 232)` | Primary background                          |
| Surface    | `#dedede` | `(222, 222, 222)` | Selected/hovered row highlight              |
| Border     | `#cccccc` | `(204, 204, 204)` | Pane dividers, separator lines              |
| Active     | `#aaaaaa` | `(170, 170, 170)` | Focused pane border                         |
| Text       | `#2a2a2a` | `(42, 42, 42)`    | Primary readable text                       |
| Dim        | `#888888` | `(136, 136, 136)` | Secondary text, labels, metadata            |
| Accent     | `#4a7a9a` | `(74, 122, 154)`  | The ONE color — cursors, links, active items |
| Alert      | `#9a4a4a` | `(154, 74, 74)`   | Unread badges, errors                       |
| Success    | `#4a8a4a` | `(74, 138, 74)`   | Active status, positive deltas              |
| Warning    | `#8a7a4a` | `(138, 122, 74)`  | Paused status, system messages              |

**Rule:** Accent (`#4a7a9a`, muted steel blue) is the only "color." Everything else is grayscale. Alert, success, and warning are desaturated and semantic only. The UI should feel monochrome at a glance.

### Visual Language

- `▸` selected items, `▾`/`▸` expanded/collapsed folders
- `⑂` forked threads, `◇` file items
- `━` filled progress, `─` empty progress
- `┌` `│` `└` inline block structure
- Double-height agent list rows, generous whitespace throughout
- Bold for agent names, folder names, token counts
- Uppercase + letter-spacing for section headers

---

## What v1 Does NOT Include

- AI backend / agent responses (messages are journaled only)
- Credentials/access control screen
- File editing from the sidebar (read-only tree)
- Settings/config screen
- Notification system
- Any external API calls
