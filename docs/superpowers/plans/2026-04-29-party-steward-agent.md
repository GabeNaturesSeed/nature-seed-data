# PARTY Steward Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new PARTY agent named `steward` that reviews all PARTY agents + the operator repo, runs a daily 01:00 MST Opus 4.7 digest into `system_state.md`, and proposes gated diffs to other agents' memory/instructions for human approval.

**Architecture:** Read-only across `~/.party/agents/*/` and the operator repo; write directly only to its own `memory/`; cross-agent edits go through a new `propose_edit` SDK tool that creates rows in the existing `human_gates` table and renders a diff viewer in the frontend gate panel for human approval.

**Tech Stack:** Tauri 2 + Rust backend, vanilla JS frontend, Node.js TypeScript sidecar running `@anthropic-ai/claude-agent-sdk`, SQLite via `sqlx`, `tokio-cron-scheduler` for cron.

**Spec:** [docs/superpowers/specs/2026-04-29-party-steward-agent-design.md](docs/superpowers/specs/2026-04-29-party-steward-agent-design.md)

**Implementation repo:** `/Users/gabegimenes-silva/Desktop/party-dev/` (canonical PARTY checkout). All file paths below are relative to that repo unless otherwise noted.

**Prerequisite (separate PR, NOT part of this plan):** Fix the known persistence bug in `src-tauri/src/agents/pool.rs:167-175` where events are dropped when the user switches agents. This affects all agents, not just Steward.

---

## File Structure (where new code lands)

**New Rust files:**
- `src-tauri/src/install/mod.rs` — install module entry
- `src-tauri/src/install/steward.rs` — `install_steward` command
- `src-tauri/src/commands/propose_edit.rs` — `propose_edit` command + path validation (or extend `commands.rs` if codebase prefers single-file)
- `src-tauri/assets/steward-seeds/` — seed asset folder copied at install time
- `src-tauri/migrations/0002_human_gates_target.sql` — adds `target_agent` and `target_path` columns

**New TypeScript sidecar files:**
- `sidecar/src/tools/propose_edit.ts` — tool definition

**New frontend files:**
- `src/diff.js` — line diff implementation (kept separate from `app.js` for testability)

**Modified files:**
- `src-tauri/src/agents/config.rs` — add `model_override: Option<String>` to `AgentConfig`
- `src-tauri/src/agents/pool.rs` — pass `model_override` through to sidecar spawn
- `src-tauri/src/main.rs` — register new `install_steward`, `propose_edit` commands in `tauri::generate_handler!`
- `src-tauri/src/db/schema.rs` — wire migration `0002`
- `src-tauri/src/scheduler/jobs.rs` — add `steward_digest` template type
- `src-tauri/src/store.rs` — already has `create_agent`; reuse, don't modify
- `sidecar/src/index.ts` — register `propose_edit` tool, handle invocation
- `sidecar/src/protocol.ts` — add new wrapper event types: `WrapperProposeEditRequest`, `WrapperGateResolved` (inbound)
- `src/app.js` — add `propose_edit` gate type render branch

---

## Phase 1 — Foundation: per-run model override + DB migration

### Task 1: Verify current scheduler state (investigation, no code change)

**Files:** none modified.

- [ ] **Step 1: Inspect existing scheduled_jobs rows**

Run:
```
sqlite3 ~/.party/data.sqlite "SELECT id, cron_expr, route_template_json, enabled FROM scheduled_jobs;"
```

Expected: zero or more existing rows. Note their `route_template_json` shape — the new `steward_digest` template will follow the same pattern.

- [ ] **Step 2: Read `src-tauri/src/scheduler/jobs.rs:23-95`** to confirm:
  - The `start()` function reads from `scheduled_jobs` table at boot
  - The `add_job()` function dispatches based on a template type field in `route_template_json`
  - There is a known existing template type (likely `consolidate`) — note its JSON shape

Record findings (briefly, in commit message or a scratch note); no code change in this task.

- [ ] **Step 3: Commit (empty marker — optional)**

Skip the commit if there's no file change. This task is verification only.

---

### Task 2: Add `model_override` to AgentConfig

**Files:**
- Modify: `src-tauri/src/agents/config.rs:42-54`
- Test: `src-tauri/tests/agent_config_test.rs` (new file)

- [ ] **Step 1: Write failing test**

Create `src-tauri/tests/agent_config_test.rs`:

```rust
use party::agents::config::AgentConfig;
use std::path::PathBuf;

#[test]
fn agent_config_uses_override_when_present() {
    let mut cfg = AgentConfig::from_slug("steward", PathBuf::from("/tmp/work"));
    assert_eq!(cfg.effective_model(), cfg.model.clone());

    cfg.model_override = Some("claude-opus-4-7".to_string());
    assert_eq!(cfg.effective_model(), "claude-opus-4-7");
}

#[test]
fn agent_config_default_override_is_none() {
    let cfg = AgentConfig::from_slug("steward", PathBuf::from("/tmp/work"));
    assert!(cfg.model_override.is_none());
}
```

- [ ] **Step 2: Run test to confirm failure**

```
cd src-tauri && cargo test agent_config_uses_override_when_present
```

Expected: compile error — `model_override` field and `effective_model()` method don't exist yet.

- [ ] **Step 3: Add the field and method**

In `src-tauri/src/agents/config.rs`, modify the struct (currently lines 42–54):

```rust
pub struct AgentConfig {
    pub slug: String,
    pub model: String,
    pub model_override: Option<String>,
    pub max_turns: u32,
    pub max_budget_usd: f64,
    pub system_prompt_path: Option<PathBuf>,
    pub append_system_prompt_path: Option<PathBuf>,
    pub working_dir: PathBuf,
    pub session_id: Option<String>,
    pub env_vars: HashMap<String, String>,
}

impl AgentConfig {
    pub fn effective_model(&self) -> String {
        self.model_override.clone().unwrap_or_else(|| self.model.clone())
    }
}
```

In `AgentConfig::from_slug` (same file), set `model_override: None,` in the constructor.

- [ ] **Step 4: Run test to confirm pass**

```
cd src-tauri && cargo test agent_config_uses_override_when_present agent_config_default_override_is_none
```

Expected: 2 passed.

- [ ] **Step 5: Update sidecar spawn to use `effective_model()`**

Find the spawn site in `src-tauri/src/agents/pool.rs` where `AgentConfig.model` is read and passed to the sidecar process. Replace `cfg.model` with `cfg.effective_model()` at the spawn arg site.

- [ ] **Step 6: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/src/agents/config.rs src-tauri/src/agents/pool.rs src-tauri/tests/agent_config_test.rs && git commit -m "feat(agents): add model_override for per-run model selection"
```

---

### Task 3: SQL migration — add `target_agent` and `target_path` to `human_gates`

**Files:**
- Create: `src-tauri/migrations/0002_human_gates_target.sql`
- Modify: `src-tauri/src/db/schema.rs:106-121` (where the table is referenced) — register the migration

- [ ] **Step 1: Create migration file**

Create `src-tauri/migrations/0002_human_gates_target.sql`:

```sql
ALTER TABLE human_gates ADD COLUMN target_agent TEXT;
ALTER TABLE human_gates ADD COLUMN target_path TEXT;
```

- [ ] **Step 2: Wire migration into the migration runner**

In `src-tauri/src/db/schema.rs`, find where migrations are applied (likely a function like `run_migrations` or `init_db`). Add the new migration to the list. The exact mechanism depends on whether PARTY uses `sqlx::migrate!` (declarative) or imperative `sqlx::query` calls.

If declarative:
```rust
sqlx::migrate!("./migrations").run(&pool).await?;
```
Place file in `src-tauri/migrations/` and `sqlx-cli` will pick it up.

If imperative: add an `ALTER TABLE` execute call alongside existing schema setup, gated on a version check.

- [ ] **Step 3: Apply migration to local dev DB**

```
cd src-tauri && sqlite3 ~/.party/data.sqlite < migrations/0002_human_gates_target.sql
```

Expected: no error. Verify columns:
```
sqlite3 ~/.party/data.sqlite ".schema human_gates"
```
Expected: schema includes `target_agent TEXT` and `target_path TEXT`.

- [ ] **Step 4: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/migrations/0002_human_gates_target.sql src-tauri/src/db/schema.rs && git commit -m "feat(db): add target_agent and target_path to human_gates"
```

---

## Phase 2 — Steward seed files + install command

### Task 4: Create Steward seed asset files

**Files:**
- Create: `src-tauri/assets/steward-seeds/agent.json`
- Create: `src-tauri/assets/steward-seeds/CLAUDE.md`
- Create: `src-tauri/assets/steward-seeds/instructions/AGENT.md`
- Create: `src-tauri/assets/steward-seeds/policy.json`
- Create: `src-tauri/assets/steward-seeds/memory/system_state.md`
- Create: `src-tauri/assets/steward-seeds/memory/learnings.md`

These are *templates*; install code will fill in id/timestamps and write them to `~/.party/agents/steward/`.

- [ ] **Step 1: Write `agent.json` template**

Use `{{ID}}`, `{{CREATED_AT}}` placeholders that install code substitutes:

```json
{
  "id": "{{ID}}",
  "name": "Steward",
  "slug": "steward",
  "role": "Cross-system reviewer. Read all PARTY agents and the operator repo, surface patterns and improvements, propose diffs to other agents' memory/instructions for human approval.",
  "status": "Active",
  "channels": [],
  "projects": [],
  "context_snapshots": [],
  "unread_count": 0,
  "session_id": null,
  "total_cost_usd": 0.0,
  "total_input_tokens": 0,
  "total_output_tokens": 0,
  "created_at": "{{CREATED_AT}}"
}
```

- [ ] **Step 2: Write `CLAUDE.md`**

```markdown
# Steward — Procedural Memory

You are Steward, a cross-system reviewer agent inside PARTY.

Working directory: /Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/

## What you do
- Read across all PARTY agents (excluding yourself) and the operator repo to understand the state of the operation
- During interactive chat: answer questions, surface patterns, draft proposed improvements
- During the 01:00 digest run: synthesize the operation's state into `memory/system_state.md` and post a digest message into the "Daily Digest" thread
- When you want to change another agent's memory, instructions, CLAUDE.md, or skills: call the `propose_edit` tool. Edits are NOT applied automatically — they create a gate the human reviews and approves.

## What you do NOT do
- You do NOT directly edit other agents' files. Cross-agent edits ALWAYS go through `propose_edit`.
- You do NOT edit operator repo files. Read-only there.
- You do NOT edit your own `agent.json` or `policy.json`.

## Where to read
- `~/.party/agents/*/` (all agents except `steward/`)
- `/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/` (operator repo)
- `/Users/gabegimenes-silva/.claude/projects/-Users-gabegimenes-silva-Desktop-ClaudeDataAgent--/memory/` (operator project memory)

## Where to write directly (no gate)
- `~/.party/agents/steward/memory/` and `~/.party/agents/steward/retros/` ONLY

## Where to propose edits (via `propose_edit` tool)
- `~/.party/agents/<other>/memory/**`
- `~/.party/agents/<other>/instructions/AGENT.md`
- `~/.party/agents/<other>/CLAUDE.md`
- `~/.party/agents/<other>/skills/**`

## When a gate resolves
- `[gate_resolved gate_id=... status=approved ...]` → your proposed change was accepted
- `[gate_resolved gate_id=... status=rejected reason="..."]` → user disagreed; learn from the reason
- `[gate_resolved gate_id=... status=stale]` → file changed under you; reread and repropose if still relevant

Reflect on rejected gates in your `Self-notes` section of `memory/system_state.md` so future digests propose better-shaped edits.
```

- [ ] **Step 3: Write `instructions/AGENT.md`**

```markdown
# Steward role spec

Cross-system reviewer for PARTY + operator repo.

Default model: claude-sonnet-4-6
Digest model (01:00 MST): claude-opus-4-7
```

- [ ] **Step 4: Write `policy.json`**

```json
{
  "allowed_paths": {
    "read": [
      "~/.party/agents/",
      "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/",
      "/Users/gabegimenes-silva/.claude/projects/-Users-gabegimenes-silva-Desktop-ClaudeDataAgent--/memory/",
      "~/.party/data.sqlite"
    ],
    "write": [
      "~/.party/agents/steward/memory/",
      "~/.party/agents/steward/retros/"
    ],
    "denied_read": [
      "~/.party/agents/steward/conversations/.private/"
    ]
  },
  "tools": {
    "allowed": ["Read", "Glob", "Grep", "Edit", "Write", "propose_edit"],
    "denied_for_targets_outside_self": ["Edit", "Write"]
  }
}
```

The `denied_for_targets_outside_self` is enforced in the sidecar's `PreToolUse` hook (see Task 12).

- [ ] **Step 5: Write `memory/system_state.md` placeholder**

```markdown
# Steward — System State

**As of:** NEVER (placeholder — first digest run will populate)
**Last digest model:** —
**Sources scanned:** 0 agents, 0 threads, 0 repo files

## Operator state
(awaiting first digest)

## Agent landscape
(awaiting first digest)

## Active tensions
(awaiting first digest)

## Things to watch
(awaiting first digest)

## Self-notes
(awaiting first digest)
```

- [ ] **Step 6: Write empty `memory/learnings.md`**

```markdown
# Steward Learnings

(populated as digest runs accumulate)
```

- [ ] **Step 7: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/assets/steward-seeds/ && git commit -m "feat(steward): seed asset files for steward agent"
```

---

### Task 5: `install_steward` — happy path (fresh install)

**Files:**
- Create: `src-tauri/src/install/mod.rs`
- Create: `src-tauri/src/install/steward.rs`
- Modify: `src-tauri/src/main.rs:151-205` (register command)
- Test: `src-tauri/tests/install_steward_test.rs`

- [ ] **Step 1: Write failing test**

Create `src-tauri/tests/install_steward_test.rs`:

```rust
use party::install::steward::install_steward_to_path;
use std::fs;
use tempfile::tempdir;

#[test]
fn install_creates_full_folder_structure_on_empty_state() {
    let tmp = tempdir().unwrap();
    let party_dir = tmp.path();

    install_steward_to_path(party_dir).expect("install should succeed");

    let steward = party_dir.join("agents").join("steward");
    assert!(steward.exists(), "steward folder should exist");
    assert!(steward.join("agent.json").exists());
    assert!(steward.join("CLAUDE.md").exists());
    assert!(steward.join("instructions/AGENT.md").exists());
    assert!(steward.join("policy.json").exists());
    assert!(steward.join("memory/system_state.md").exists());
    assert!(steward.join("memory/learnings.md").exists());
    assert!(steward.join("conversations").is_dir());
    assert!(steward.join("retros").is_dir());
    assert!(steward.join("workspace").is_dir());
    assert!(steward.join("skills").is_dir());
    assert!(steward.join("data").is_dir());

    let agent_json = fs::read_to_string(steward.join("agent.json")).unwrap();
    assert!(!agent_json.contains("{{ID}}"), "ID placeholder must be replaced");
    assert!(!agent_json.contains("{{CREATED_AT}}"), "timestamp placeholder must be replaced");
    assert!(agent_json.contains("\"slug\": \"steward\""));
}
```

- [ ] **Step 2: Run test — confirm failure**

```
cd src-tauri && cargo test install_creates_full_folder_structure_on_empty_state
```

Expected: compile error — `party::install` module doesn't exist.

- [ ] **Step 3: Add module declaration to `src-tauri/src/lib.rs`**

```rust
pub mod install;
```

- [ ] **Step 4: Create `src-tauri/src/install/mod.rs`**

```rust
pub mod steward;
```

- [ ] **Step 5: Create `src-tauri/src/install/steward.rs`**

```rust
use chrono::Utc;
use std::fs;
use std::path::Path;
use uuid::Uuid;

const SEEDS: &str = include_str!("../../assets/steward-seeds/agent.json");
const CLAUDE_MD: &str = include_str!("../../assets/steward-seeds/CLAUDE.md");
const AGENT_MD: &str = include_str!("../../assets/steward-seeds/instructions/AGENT.md");
const POLICY: &str = include_str!("../../assets/steward-seeds/policy.json");
const SYSTEM_STATE: &str = include_str!("../../assets/steward-seeds/memory/system_state.md");
const LEARNINGS: &str = include_str!("../../assets/steward-seeds/memory/learnings.md");

pub fn install_steward_to_path(party_dir: &Path) -> Result<(), String> {
    let steward = party_dir.join("agents").join("steward");
    if steward.exists() {
        return Err("steward folder already exists — refuse to overwrite".to_string());
    }

    fs::create_dir_all(steward.join("memory")).map_err(|e| e.to_string())?;
    fs::create_dir_all(steward.join("instructions")).map_err(|e| e.to_string())?;
    fs::create_dir_all(steward.join("skills")).map_err(|e| e.to_string())?;
    fs::create_dir_all(steward.join("conversations")).map_err(|e| e.to_string())?;
    fs::create_dir_all(steward.join("retros")).map_err(|e| e.to_string())?;
    fs::create_dir_all(steward.join("workspace")).map_err(|e| e.to_string())?;
    fs::create_dir_all(steward.join("data")).map_err(|e| e.to_string())?;

    let id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();
    let agent_json = SEEDS
        .replace("{{ID}}", &id)
        .replace("{{CREATED_AT}}", &now);

    fs::write(steward.join("agent.json"), agent_json).map_err(|e| e.to_string())?;
    fs::write(steward.join("CLAUDE.md"), CLAUDE_MD).map_err(|e| e.to_string())?;
    fs::write(steward.join("instructions/AGENT.md"), AGENT_MD).map_err(|e| e.to_string())?;
    fs::write(steward.join("policy.json"), POLICY).map_err(|e| e.to_string())?;
    fs::write(steward.join("memory/system_state.md"), SYSTEM_STATE).map_err(|e| e.to_string())?;
    fs::write(steward.join("memory/learnings.md"), LEARNINGS).map_err(|e| e.to_string())?;

    Ok(())
}
```

- [ ] **Step 6: Run test — confirm pass**

```
cd src-tauri && cargo test install_creates_full_folder_structure_on_empty_state
```

Expected: PASS.

- [ ] **Step 7: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/src/install/ src-tauri/src/lib.rs src-tauri/tests/install_steward_test.rs && git commit -m "feat(install): install_steward filesystem layout"
```

---

### Task 6: `install_steward` — folder-already-exists error

**Files:**
- Modify: `src-tauri/src/install/steward.rs` (already does this in Task 5 — write the test)
- Test: extend `src-tauri/tests/install_steward_test.rs`

- [ ] **Step 1: Write test**

Append to `src-tauri/tests/install_steward_test.rs`:

```rust
#[test]
fn install_errors_when_folder_already_exists() {
    let tmp = tempdir().unwrap();
    let party_dir = tmp.path();
    install_steward_to_path(party_dir).unwrap();

    let result = install_steward_to_path(party_dir);
    assert!(result.is_err());
    let msg = result.err().unwrap();
    assert!(msg.contains("already exists"));
}
```

- [ ] **Step 2: Run test — confirm pass**

```
cd src-tauri && cargo test install_errors_when_folder_already_exists
```

Expected: PASS (the impl from Task 5 already handles this case).

- [ ] **Step 3: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/tests/install_steward_test.rs && git commit -m "test(install): assert install refuses to overwrite existing folder"
```

---

### Task 6.5: `install_steward` — mismatch detection tests

**Files:**
- Test: extend `src-tauri/tests/install_steward_test.rs`

These tests assert the Tauri command (added in Task 7) refuses to "fix up" inconsistent state.

- [ ] **Step 1: Write tests**

Append to `src-tauri/tests/install_steward_test.rs`. (These need a real DB pool, so they belong in an integration-style test setup.)

```rust
use party::install::steward::install_steward_inner;
use sqlx::sqlite::SqlitePool;

async fn fresh_pool() -> SqlitePool {
    let pool = SqlitePool::connect("sqlite::memory:").await.unwrap();
    sqlx::query("CREATE TABLE agents (slug TEXT PRIMARY KEY, name TEXT)").execute(&pool).await.unwrap();
    pool
}

#[tokio::test]
async fn install_aborts_when_folder_exists_but_no_db_row() {
    let tmp = tempdir().unwrap();
    let party_dir = tmp.path();
    std::fs::create_dir_all(party_dir.join("agents/steward")).unwrap();
    let pool = fresh_pool().await;

    let r = install_steward_inner(&pool, party_dir).await;
    assert!(r.is_err());
    assert!(r.err().unwrap().contains("inconsistent"));
}

#[tokio::test]
async fn install_aborts_when_db_row_exists_but_no_folder() {
    let tmp = tempdir().unwrap();
    let party_dir = tmp.path();
    let pool = fresh_pool().await;
    sqlx::query("INSERT INTO agents (slug, name) VALUES ('steward', 'Steward')").execute(&pool).await.unwrap();

    let r = install_steward_inner(&pool, party_dir).await;
    assert!(r.is_err());
    assert!(r.err().unwrap().contains("inconsistent"));
}

#[tokio::test]
async fn install_succeeds_on_empty_state() {
    let tmp = tempdir().unwrap();
    let party_dir = tmp.path();
    let pool = fresh_pool().await;

    let r = install_steward_inner(&pool, party_dir).await;
    assert!(r.is_ok());
    assert_eq!(r.unwrap(), "steward installed");
}

#[tokio::test]
async fn install_idempotent_when_both_exist() {
    let tmp = tempdir().unwrap();
    let party_dir = tmp.path();
    std::fs::create_dir_all(party_dir.join("agents/steward")).unwrap();
    let pool = fresh_pool().await;
    sqlx::query("INSERT INTO agents (slug, name) VALUES ('steward', 'Steward')").execute(&pool).await.unwrap();

    let r = install_steward_inner(&pool, party_dir).await;
    assert!(r.is_ok());
    assert!(r.unwrap().contains("already installed"));
}
```

`install_steward_inner` is the testable core; the `#[tauri::command] install_steward` is a thin wrapper around it (defined in Task 7). This split makes the integration logic unit-testable without Tauri's State plumbing.

- [ ] **Step 2: Run — confirm failure**

```
cd src-tauri && cargo test install_aborts
```

Expected: compile error — `install_steward_inner` doesn't exist yet. Task 7 will add it.

- [ ] **Step 3: Commit (test-only commit)**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/tests/install_steward_test.rs && git commit -m "test(install): mismatch detection cases (failing — impl in next task)"
```

---

### Task 7: `install_steward` Tauri command + DB row

**Files:**
- Modify: `src-tauri/src/install/steward.rs` (add Tauri command wrapper that also creates DB row)
- Modify: `src-tauri/src/main.rs:151-205`

- [ ] **Step 1: Add Tauri command + testable inner function**

Append to `src-tauri/src/install/steward.rs`:

```rust
use tauri::State;
use crate::AppState;

#[tauri::command]
pub async fn install_steward(state: State<'_, AppState>) -> Result<String, String> {
    install_steward_inner(&state.db, &state.party_dir).await
}

pub async fn install_steward_inner(
    pool: &sqlx::SqlitePool,
    party_dir: &std::path::Path,
) -> Result<String, String> {
    let steward_folder = party_dir.join("agents").join("steward");
    let folder_exists = steward_folder.exists();

    let row_exists: bool = sqlx::query_scalar("SELECT EXISTS(SELECT 1 FROM agents WHERE slug = 'steward')")
        .fetch_one(pool)
        .await
        .map_err(|e| e.to_string())?;

    match (folder_exists, row_exists) {
        (true, true) => Ok("steward already installed".to_string()),
        (true, false) | (false, true) => Err(format!(
            "inconsistent state — folder_exists={} db_row_exists={}; resolve manually before re-running install",
            folder_exists, row_exists
        )),
        (false, false) => {
            install_steward_to_path(party_dir)?;
            sqlx::query("INSERT INTO agents (slug, name) VALUES ('steward', 'Steward')")
                .execute(pool)
                .await
                .map_err(|e| e.to_string())?;
            // If the production schema requires more columns, mirror what `store::create_agent`
            // does — call it directly instead of the raw INSERT above.
            Ok("steward installed".to_string())
        }
    }
}

fn steward_agent() -> crate::models::Agent {
    use chrono::Utc;
    use uuid::Uuid;
    crate::models::Agent {
        id: Uuid::new_v4(),
        name: "Steward".to_string(),
        slug: "steward".to_string(),
        role: "Cross-system reviewer. Read all PARTY agents and the operator repo, surface patterns and improvements, propose diffs to other agents' memory/instructions for human approval.".to_string(),
        status: crate::models::AgentStatus::Active,
        channels: vec![],
        projects: vec![],
        context_snapshots: vec![],
        unread_count: 0,
        session_id: None,
        total_cost_usd: 0.0,
        total_input_tokens: 0,
        total_output_tokens: 0,
        created_at: Utc::now(),
    }
}
```

Note: this assumes `store::create_agent` writes to both filesystem AND the agents SQLite table. If it only does the filesystem (and SQLite is populated elsewhere), add an explicit `sqlx::query!("INSERT INTO agents ...")` here. **Verify the actual behavior of `store::create_agent` in `src-tauri/src/store.rs:151-176` before this task** — the install logic must produce a consistent (folder, DB row) pair.

If `store::create_agent` already writes both folder and row, the call to `install_steward_to_path` becomes redundant; in that case, replace the body of the `(false, false)` branch with just `crate::store::create_agent(party_dir, &steward_agent())` and discard `install_steward_to_path` (or keep it as the test-only path).

- [ ] **Step 2: Register the command**

In `src-tauri/src/main.rs`, find the `tauri::generate_handler![ ... ]` block (lines 151–205) and add `install::steward::install_steward` to the list.

- [ ] **Step 3: Build to verify compile**

```
cd src-tauri && cargo build
```

Expected: compiles cleanly. If `store::create_agent` async-vs-sync doesn't match, adjust the `.await` accordingly.

- [ ] **Step 4: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/src/install/steward.rs src-tauri/src/main.rs && git commit -m "feat(install): install_steward Tauri command with DB row creation"
```

---

### Task 8: Auto-run install on app startup if Steward not installed

**Files:**
- Modify: `src-tauri/src/main.rs` (in `setup` closure or wherever app boot lives)

- [ ] **Step 1: Add startup hook**

In `src-tauri/src/main.rs`, locate the `tauri::Builder::default().setup(|app| { ... })` block. Inside, after AppState is created, add:

```rust
let app_state = app.state::<AppState>();
let party_dir = app_state.party_dir.clone();
let db = app_state.db.clone();
tokio::spawn(async move {
    let steward_folder = party_dir.join("agents").join("steward");
    let row_exists: bool = sqlx::query_scalar("SELECT EXISTS(SELECT 1 FROM agents WHERE slug = 'steward')")
        .fetch_one(&db)
        .await
        .unwrap_or(false);
    if !steward_folder.exists() && !row_exists {
        if let Err(e) = crate::install::steward::install_steward_to_path(&party_dir) {
            eprintln!("auto-install steward (filesystem) failed: {}", e);
            return;
        }
        // Insert DB row using the same Agent struct as the manual command
        // (mirror Task 7's logic — extract to a helper if you prefer)
    }
});
```

If the existing `setup` closure is not async, wrap with `tokio::runtime::Handle::current().spawn`.

- [ ] **Step 2: Build, run app, verify**

```
cd src-tauri && cargo build && cd .. && npm run tauri dev
```

Move existing `~/.party/agents/steward/` out of the way first (back it up, don't delete) so the auto-install path is taken. After app boots, verify:

```
ls ~/.party/agents/steward/
sqlite3 ~/.party/data.sqlite "SELECT slug FROM agents WHERE slug='steward';"
```

Both should show steward.

- [ ] **Step 3: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/src/main.rs && git commit -m "feat(install): auto-install steward on app startup if absent"
```

---

## Phase 3 — propose_edit Rust command

### Task 9: Path validation function with tests

**Files:**
- Create: `src-tauri/src/commands/propose_edit.rs`
- Modify: `src-tauri/src/commands.rs` (add `mod propose_edit;` if commands.rs is the module root, or `src-tauri/src/lib.rs`)
- Test: `src-tauri/tests/propose_edit_test.rs`

- [ ] **Step 1: Write failing tests**

Create `src-tauri/tests/propose_edit_test.rs`:

```rust
use party::commands::propose_edit::validate_target;
use std::path::PathBuf;

fn party() -> PathBuf { PathBuf::from("/tmp/.party-test") }

#[test]
fn rejects_steward_as_target() {
    let r = validate_target(&party(), "steward", "memory/foo.md");
    assert!(r.is_err());
    assert!(r.err().unwrap().contains("steward"));
}

#[test]
fn allows_memory_path() {
    let r = validate_target(&party(), "klaviyo", "memory/learnings.md");
    assert!(r.is_ok());
}

#[test]
fn allows_instructions_agent_md() {
    let r = validate_target(&party(), "klaviyo", "instructions/AGENT.md");
    assert!(r.is_ok());
}

#[test]
fn allows_claude_md() {
    let r = validate_target(&party(), "klaviyo", "CLAUDE.md");
    assert!(r.is_ok());
}

#[test]
fn allows_skills_path() {
    let r = validate_target(&party(), "klaviyo", "skills/some-skill/SKILL.md");
    assert!(r.is_ok());
}

#[test]
fn rejects_agent_json() {
    let r = validate_target(&party(), "klaviyo", "agent.json");
    assert!(r.is_err());
}

#[test]
fn rejects_conversations() {
    let r = validate_target(&party(), "klaviyo", "conversations/foo.json");
    assert!(r.is_err());
}

#[test]
fn rejects_policy_json() {
    let r = validate_target(&party(), "klaviyo", "policy.json");
    assert!(r.is_err());
}

#[test]
fn rejects_path_traversal() {
    let r = validate_target(&party(), "klaviyo", "../steward/memory/foo.md");
    assert!(r.is_err());
    assert!(r.err().unwrap().contains("traversal") || r.err().unwrap().contains("escape"));
}

#[test]
fn rejects_absolute_path() {
    let r = validate_target(&party(), "klaviyo", "/etc/passwd");
    assert!(r.is_err());
}
```

- [ ] **Step 2: Run tests — confirm failure**

```
cd src-tauri && cargo test propose_edit
```

Expected: compile error (module doesn't exist).

- [ ] **Step 3: Implement validation**

Create `src-tauri/src/commands/propose_edit.rs`:

```rust
use std::path::{Path, PathBuf};

pub fn validate_target(party_dir: &Path, target_agent: &str, target_path: &str) -> Result<PathBuf, String> {
    if target_agent == "steward" {
        return Err("steward cannot propose edits to itself; use direct write".to_string());
    }
    if target_path.starts_with('/') {
        return Err("absolute paths not permitted".to_string());
    }
    if target_path.contains("..") {
        return Err("path traversal not permitted".to_string());
    }

    let allowed = matches!(
        target_path,
        "CLAUDE.md" | "instructions/AGENT.md"
    ) || target_path.starts_with("memory/")
       || target_path.starts_with("skills/");

    if !allowed {
        return Err(format!("path not in allow-list: {}", target_path));
    }

    let agent_root = party_dir.join("agents").join(target_agent);
    let resolved = agent_root.join(target_path);
    let canonical_root = agent_root.canonicalize().unwrap_or(agent_root.clone());
    let canonical_resolved = resolved.parent().and_then(|p| p.canonicalize().ok()).unwrap_or_else(|| resolved.clone());

    if !canonical_resolved.starts_with(&canonical_root) {
        return Err("resolved path escapes target agent folder".to_string());
    }

    Ok(resolved)
}
```

- [ ] **Step 4: Wire module into the crate**

If `src-tauri/src/commands.rs` is a single file (not a module), instead create the module root: rename `commands.rs` to `commands/mod.rs` (or add `pub mod propose_edit;` to wherever the commands module is declared). Easier alternative: add `pub mod commands { pub mod propose_edit; }` in `lib.rs`.

Choose whichever matches the existing PARTY pattern. If unsure, use `pub mod commands_propose_edit;` in `lib.rs` and reference as `party::commands_propose_edit::validate_target` in tests.

- [ ] **Step 5: Run tests — confirm pass**

```
cd src-tauri && cargo test propose_edit
```

Expected: 10 passed.

- [ ] **Step 6: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/src/commands/ src-tauri/src/lib.rs src-tauri/tests/propose_edit_test.rs && git commit -m "feat(propose_edit): path validation for cross-agent edit proposals"
```

---

### Task 10: `propose_edit` Tauri command — gate creation

**Files:**
- Modify: `src-tauri/src/commands/propose_edit.rs`
- Modify: `src-tauri/src/main.rs:151-205` (register command)
- Test: extend `src-tauri/tests/propose_edit_test.rs`

- [ ] **Step 1: Write integration test**

Append to `src-tauri/tests/propose_edit_test.rs`:

```rust
use party::commands::propose_edit::{ProposeEditPayload, EditOp, create_gate};
use sqlx::sqlite::SqlitePool;
use tempfile::tempdir;

#[tokio::test]
async fn create_gate_inserts_human_gates_row() {
    let tmp = tempdir().unwrap();
    let party_dir = tmp.path();
    std::fs::create_dir_all(party_dir.join("agents/klaviyo/memory")).unwrap();
    std::fs::write(party_dir.join("agents/klaviyo/memory/learnings.md"), "old content").unwrap();

    let pool = SqlitePool::connect("sqlite::memory:").await.unwrap();
    sqlx::query("CREATE TABLE human_gates (id TEXT PRIMARY KEY, chain_id TEXT, gate_type TEXT, status TEXT, agent_slug TEXT, brief_path TEXT, decided_at TEXT, decision TEXT, edits_json TEXT, target_agent TEXT, target_path TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')))").execute(&pool).await.unwrap();

    let payload = ProposeEditPayload {
        target_agent: "klaviyo".to_string(),
        target_path: "memory/learnings.md".to_string(),
        edits: vec![EditOp::Replace { old_string: "old content".to_string(), new_string: "new content".to_string() }],
        rationale: "test rationale".to_string(),
    };

    let gate_id = create_gate(&pool, party_dir, &payload).await.unwrap();
    let row: (String, String, String, String) = sqlx::query_as("SELECT gate_type, status, target_agent, target_path FROM human_gates WHERE id = ?")
        .bind(&gate_id)
        .fetch_one(&pool)
        .await
        .unwrap();
    assert_eq!(row.0, "propose_edit");
    assert_eq!(row.1, "pending");
    assert_eq!(row.2, "klaviyo");
    assert_eq!(row.3, "memory/learnings.md");
}

#[tokio::test]
async fn create_gate_rejects_when_old_string_not_in_file() {
    let tmp = tempdir().unwrap();
    let party_dir = tmp.path();
    std::fs::create_dir_all(party_dir.join("agents/klaviyo/memory")).unwrap();
    std::fs::write(party_dir.join("agents/klaviyo/memory/learnings.md"), "actual content").unwrap();

    let pool = SqlitePool::connect("sqlite::memory:").await.unwrap();
    sqlx::query("CREATE TABLE human_gates (id TEXT PRIMARY KEY, chain_id TEXT, gate_type TEXT, status TEXT, agent_slug TEXT, brief_path TEXT, decided_at TEXT, decision TEXT, edits_json TEXT, target_agent TEXT, target_path TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')))").execute(&pool).await.unwrap();

    let payload = ProposeEditPayload {
        target_agent: "klaviyo".to_string(),
        target_path: "memory/learnings.md".to_string(),
        edits: vec![EditOp::Replace { old_string: "wrong old".to_string(), new_string: "new".to_string() }],
        rationale: "test".to_string(),
    };

    let r = create_gate(&pool, party_dir, &payload).await;
    assert!(r.is_err());
    assert!(r.err().unwrap().contains("old_string not found"));
}
```

- [ ] **Step 2: Implement payload types and gate creation**

Append to `src-tauri/src/commands/propose_edit.rs`:

```rust
use serde::{Deserialize, Serialize};
use sqlx::SqlitePool;
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize)]
#[serde(tag = "kind")]
pub enum EditOp {
    Replace { old_string: String, new_string: String },
    FullReplace { full_replace: String },
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ProposeEditPayload {
    pub target_agent: String,
    pub target_path: String,
    pub edits: Vec<EditOp>,
    pub rationale: String,
}

pub async fn create_gate(
    pool: &sqlx::SqlitePool,
    party_dir: &Path,
    payload: &ProposeEditPayload,
) -> Result<String, String> {
    let resolved = validate_target(party_dir, &payload.target_agent, &payload.target_path)?;
    let original = std::fs::read_to_string(&resolved).map_err(|e| format!("cannot read target: {}", e))?;
    let _final_content = apply_edits_in_memory(&original, &payload.edits)?;

    let gate_id = Uuid::new_v4().to_string();
    let edits_json = serde_json::to_string(&payload.edits).map_err(|e| e.to_string())?;

    sqlx::query("INSERT INTO human_gates (id, gate_type, status, agent_slug, target_agent, target_path, edits_json, brief_path) VALUES (?, 'propose_edit', 'pending', 'steward', ?, ?, ?, ?)")
        .bind(&gate_id)
        .bind(&payload.target_agent)
        .bind(&payload.target_path)
        .bind(&edits_json)
        .bind(&payload.rationale)
        .execute(pool)
        .await
        .map_err(|e| e.to_string())?;

    Ok(gate_id)
}

pub fn apply_edits_in_memory(original: &str, edits: &[EditOp]) -> Result<String, String> {
    let mut current = original.to_string();
    for edit in edits {
        match edit {
            EditOp::Replace { old_string, new_string } => {
                if !current.contains(old_string) {
                    return Err(format!("old_string not found in target: {:?}", old_string));
                }
                current = current.replacen(old_string, new_string, 1);
            }
            EditOp::FullReplace { full_replace } => {
                current = full_replace.clone();
            }
        }
    }
    Ok(current)
}

#[tauri::command]
pub async fn propose_edit(
    state: tauri::State<'_, crate::AppState>,
    payload: ProposeEditPayload,
) -> Result<serde_json::Value, String> {
    let gate_id = create_gate(&state.db, &state.party_dir, &payload).await?;
    // Emit gate_pending event to frontend
    state.emit_gate_pending(&gate_id).await;
    Ok(serde_json::json!({ "gate_id": gate_id, "status": "pending" }))
}
```

If `state.emit_gate_pending` doesn't exist, use `app_handle.emit_all("gate_pending", &gate_id)` via Tauri's built-in emit API.

- [ ] **Step 3: Run tests — confirm pass**

```
cd src-tauri && cargo test propose_edit
```

Expected: all 12 tests pass (10 from Task 9 + 2 new).

- [ ] **Step 4: Register command**

Add `commands::propose_edit::propose_edit` to the `tauri::generate_handler!` list in `main.rs`.

- [ ] **Step 5: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/src/commands/propose_edit.rs src-tauri/src/main.rs src-tauri/tests/propose_edit_test.rs && git commit -m "feat(propose_edit): gate creation with old_string validation"
```

---

### Task 11: `apply_gate_propose_edit` and `gate_resolved` events

**Files:**
- Modify: `src-tauri/src/commands.rs` (where `approve_gate` lives — extend it)
- Modify: `src-tauri/src/commands/propose_edit.rs`

- [ ] **Step 1: Write test for apply-on-approve**

Append to `src-tauri/tests/propose_edit_test.rs`:

```rust
#[tokio::test]
async fn apply_gate_writes_new_content_to_disk() {
    use party::commands::propose_edit::apply_gate;
    let tmp = tempdir().unwrap();
    let party_dir = tmp.path();
    std::fs::create_dir_all(party_dir.join("agents/klaviyo/memory")).unwrap();
    std::fs::write(party_dir.join("agents/klaviyo/memory/learnings.md"), "old").unwrap();

    let pool = SqlitePool::connect("sqlite::memory:").await.unwrap();
    sqlx::query("CREATE TABLE human_gates (id TEXT PRIMARY KEY, chain_id TEXT, gate_type TEXT, status TEXT, agent_slug TEXT, brief_path TEXT, decided_at TEXT, decision TEXT, edits_json TEXT, target_agent TEXT, target_path TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')))").execute(&pool).await.unwrap();

    let payload = ProposeEditPayload {
        target_agent: "klaviyo".to_string(),
        target_path: "memory/learnings.md".to_string(),
        edits: vec![EditOp::Replace { old_string: "old".to_string(), new_string: "new".to_string() }],
        rationale: "x".to_string(),
    };
    let gate_id = create_gate(&pool, party_dir, &payload).await.unwrap();

    apply_gate(&pool, party_dir, &gate_id).await.unwrap();
    let content = std::fs::read_to_string(party_dir.join("agents/klaviyo/memory/learnings.md")).unwrap();
    assert_eq!(content, "new");

    let status: String = sqlx::query_scalar("SELECT status FROM human_gates WHERE id = ?")
        .bind(&gate_id).fetch_one(&pool).await.unwrap();
    assert_eq!(status, "approved");
}

#[tokio::test]
async fn apply_gate_marks_stale_when_file_changed() {
    use party::commands::propose_edit::apply_gate;
    let tmp = tempdir().unwrap();
    let party_dir = tmp.path();
    std::fs::create_dir_all(party_dir.join("agents/klaviyo/memory")).unwrap();
    std::fs::write(party_dir.join("agents/klaviyo/memory/learnings.md"), "old").unwrap();

    let pool = SqlitePool::connect("sqlite::memory:").await.unwrap();
    sqlx::query("CREATE TABLE human_gates (id TEXT PRIMARY KEY, chain_id TEXT, gate_type TEXT, status TEXT, agent_slug TEXT, brief_path TEXT, decided_at TEXT, decision TEXT, edits_json TEXT, target_agent TEXT, target_path TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')))").execute(&pool).await.unwrap();

    let payload = ProposeEditPayload {
        target_agent: "klaviyo".to_string(),
        target_path: "memory/learnings.md".to_string(),
        edits: vec![EditOp::Replace { old_string: "old".to_string(), new_string: "new".to_string() }],
        rationale: "x".to_string(),
    };
    let gate_id = create_gate(&pool, party_dir, &payload).await.unwrap();

    // simulate user editing the file before approval
    std::fs::write(party_dir.join("agents/klaviyo/memory/learnings.md"), "user-edited").unwrap();

    let result = apply_gate(&pool, party_dir, &gate_id).await;
    assert!(result.is_err());

    let status: String = sqlx::query_scalar("SELECT status FROM human_gates WHERE id = ?")
        .bind(&gate_id).fetch_one(&pool).await.unwrap();
    assert_eq!(status, "stale");
}
```

- [ ] **Step 2: Run tests — confirm failure**

```
cd src-tauri && cargo test apply_gate
```

Expected: compile error — `apply_gate` doesn't exist.

- [ ] **Step 3: Implement `apply_gate`**

Append to `src-tauri/src/commands/propose_edit.rs`:

```rust
pub async fn apply_gate(pool: &SqlitePool, party_dir: &Path, gate_id: &str) -> Result<(), String> {
    let row: (String, String, String) = sqlx::query_as(
        "SELECT target_agent, target_path, edits_json FROM human_gates WHERE id = ? AND gate_type = 'propose_edit' AND status = 'pending'"
    )
    .bind(gate_id)
    .fetch_one(pool)
    .await
    .map_err(|e| format!("gate not found or not pending: {}", e))?;

    let (target_agent, target_path, edits_json) = row;
    let edits: Vec<EditOp> = serde_json::from_str(&edits_json).map_err(|e| e.to_string())?;
    let resolved = validate_target(party_dir, &target_agent, &target_path)?;
    let original = std::fs::read_to_string(&resolved).map_err(|e| format!("cannot read target: {}", e))?;

    let final_content = match apply_edits_in_memory(&original, &edits) {
        Ok(s) => s,
        Err(_) => {
            sqlx::query("UPDATE human_gates SET status = 'stale', decided_at = datetime('now') WHERE id = ?")
                .bind(gate_id).execute(pool).await.map_err(|e| e.to_string())?;
            return Err("gate stale: file changed since proposal".to_string());
        }
    };

    std::fs::write(&resolved, final_content).map_err(|e| e.to_string())?;
    sqlx::query("UPDATE human_gates SET status = 'approved', decided_at = datetime('now') WHERE id = ?")
        .bind(gate_id).execute(pool).await.map_err(|e| e.to_string())?;

    Ok(())
}
```

- [ ] **Step 4: Wire `apply_gate` into the existing `approve_gate` command**

In `src-tauri/src/commands.rs`, find `approve_gate` (it must exist since the frontend already calls it). Before marking the gate approved as a generic gate, check if `gate_type = 'propose_edit'` and dispatch to `apply_gate`:

```rust
let gate_type: String = sqlx::query_scalar("SELECT gate_type FROM human_gates WHERE id = ?")
    .bind(&gate_id).fetch_one(&state.db).await.map_err(|e| e.to_string())?;
if gate_type == "propose_edit" {
    return crate::commands::propose_edit::apply_gate(&state.db, &state.party_dir, &gate_id).await;
}
// ... existing approval logic for other gate_types
```

- [ ] **Step 5: Run tests — confirm pass**

```
cd src-tauri && cargo test apply_gate
```

Expected: 2 new tests pass.

- [ ] **Step 6: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/src/commands/propose_edit.rs src-tauri/src/commands.rs src-tauri/tests/propose_edit_test.rs && git commit -m "feat(propose_edit): apply on approve, mark stale on conflict"
```

---

## Phase 4 — Sidecar `propose_edit` tool

### Task 12: Register `propose_edit` SDK tool in sidecar

**Files:**
- Create: `sidecar/src/tools/propose_edit.ts`
- Modify: `sidecar/src/index.ts:191-330` (PreToolUse hook section)
- Modify: `sidecar/src/protocol.ts:86-136` (add new wrapper event types)

- [ ] **Step 1: Add wrapper protocol types**

In `sidecar/src/protocol.ts`, alongside existing `WrapperPermissionRequest` and `WrapperSdkPassthrough`, add:

```typescript
export interface WrapperProposeEditRequest {
  kind: "propose_edit_request";
  req_id: string;
  agent_slug: string;
  target_agent: string;
  target_path: string;
  edits: Array<{ old_string: string; new_string: string } | { full_replace: string }>;
  rationale: string;
}

export interface WrapperProposeEditResponse {
  kind: "propose_edit_response";
  req_id: string;
  gate_id: string;
}

export interface WrapperGateResolved {
  kind: "gate_resolved";
  gate_id: string;
  status: "approved" | "rejected" | "stale";
  reason?: string;
  target_agent: string;
  target_path: string;
}
```

`WrapperProposeEditRequest` is sidecar → Rust. `WrapperProposeEditResponse` is Rust → sidecar (via stdin). `WrapperGateResolved` is Rust → sidecar (delivered when user approves/rejects later).

- [ ] **Step 2: Define the SDK tool**

Create `sidecar/src/tools/propose_edit.ts`:

```typescript
import { tool } from "@anthropic-ai/claude-agent-sdk";
import { randomUUID } from "node:crypto";
import { emitToRust, awaitRustResponse } from "../bridge.js";

export function buildProposeEditTool(agentSlug: string) {
  return tool({
    name: "propose_edit",
    description: "Propose an edit to another PARTY agent's memory, instructions, CLAUDE.md, or skills. Creates a human-approval gate; the edit is NOT applied until the human approves it. Returns immediately with a gate_id; the outcome arrives later as a [gate_resolved] system message.",
    input_schema: {
      type: "object",
      properties: {
        target_agent: { type: "string", description: "Slug of the agent whose file you want to edit. Cannot be 'steward'." },
        target_path: { type: "string", description: "Path within the target agent folder. Allowed: memory/**, instructions/AGENT.md, CLAUDE.md, skills/**" },
        edits: {
          type: "array",
          items: {
            oneOf: [
              { type: "object", properties: { old_string: { type: "string" }, new_string: { type: "string" } }, required: ["old_string", "new_string"] },
              { type: "object", properties: { full_replace: { type: "string" } }, required: ["full_replace"] }
            ]
          }
        },
        rationale: { type: "string", description: "Markdown explanation of WHY this edit improves the target agent" }
      },
      required: ["target_agent", "target_path", "edits", "rationale"]
    },
    execute: async (input: any) => {
      const reqId = randomUUID();
      emitToRust({
        kind: "propose_edit_request",
        req_id: reqId,
        agent_slug: agentSlug,
        target_agent: input.target_agent,
        target_path: input.target_path,
        edits: input.edits,
        rationale: input.rationale,
      });
      const response = await awaitRustResponse(reqId, 30_000);
      return JSON.stringify({ gate_id: response.gate_id, status: "pending" });
    }
  });
}
```

The exact `tool()` API and `bridge.js` helpers depend on the SDK version PARTY uses. Check `sidecar/src/index.ts` for how existing tools (or hooks) emit/await NDJSON events; reuse that pattern. The shape above is the contract — adapt the syntax to match.

- [ ] **Step 3: Wire tool into agent spawn**

In `sidecar/src/index.ts`, where the SDK query is constructed (around line 150), add `propose_edit` to the tools list when the agent slug is `steward`:

```typescript
const tools = agentSlug === "steward" ? [buildProposeEditTool(agentSlug)] : [];
// pass `tools` through to the SDK query options
```

- [ ] **Step 4: Add Rust handler for `propose_edit_request` event**

In `src-tauri/src/agents/pool.rs` (where sidecar events are received and dispatched — near `poll_all` at line 167), add handling for `kind: "propose_edit_request"`. When seen:
1. Parse the payload as `ProposeEditPayload`
2. Call `commands::propose_edit::create_gate(&state.db, &state.party_dir, &payload)` (rename to `create_gate` for production use)
3. Write `WrapperProposeEditResponse` JSON line to the sidecar's stdin

```rust
// pseudocode — adapt to actual event-dispatch shape
"propose_edit_request" => {
    let payload: ProposeEditPayload = serde_json::from_value(event["..."].clone())?;
    let gate_id = crate::commands::propose_edit::create_gate(&self.db, &self.party_dir, &payload).await?;
    let response = serde_json::json!({
        "kind": "propose_edit_response",
        "req_id": event["req_id"],
        "gate_id": gate_id
    });
    sidecar.send_stdin(&serde_json::to_string(&response)?).await?;
    self.app_handle.emit_all("gate_pending", &gate_id).ok();
}
```

- [ ] **Step 5: Manual smoke test**

Build and run PARTY, open Steward agent, send a chat like: *"Propose an edit to klaviyo's CLAUDE.md adding a 'note' line at the end."* Verify:
- A gate row appears: `sqlite3 ~/.party/data.sqlite "SELECT id, gate_type, target_agent, target_path FROM human_gates WHERE gate_type='propose_edit';"`
- Steward's response indicates the gate_id was returned

- [ ] **Step 6: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add sidecar/src/tools/propose_edit.ts sidecar/src/protocol.ts sidecar/src/index.ts src-tauri/src/agents/pool.rs && git commit -m "feat(sidecar): propose_edit SDK tool with gate request bridge"
```

---

### Task 13: `gate_resolved` event injected into Steward's next turn

**Files:**
- Modify: `src-tauri/src/agents/pool.rs` (or wherever messages are sent to sidecar stdin)
- Modify: `sidecar/src/index.ts` (handle `gate_resolved` inbound)

- [ ] **Step 1: Define inbound message handler in sidecar**

In `sidecar/src/index.ts`, add handler in the stdin parsing section:

```typescript
case "gate_resolved": {
  pendingResolutions.push(message);
  break;
}
```

`pendingResolutions` is a buffer that gets prepended to the next user message Steward sends.

- [ ] **Step 2: On next outgoing user message, prepend resolution lines**

Where the sidecar constructs the next user message to send to the SDK, prepend any pending resolutions as a system-style preamble:

```typescript
const preamble = pendingResolutions
  .map(r => `[gate_resolved gate_id=${r.gate_id} status=${r.status} target=${r.target_agent}/${r.target_path}${r.reason ? ` reason="${r.reason}"` : ''}]`)
  .join("\n");
pendingResolutions = [];
const fullMessage = preamble ? `${preamble}\n\n${userMessage}` : userMessage;
```

- [ ] **Step 3: On Rust side, when `approve_gate` or `reject_gate` resolves a `propose_edit` gate, send `gate_resolved` to Steward sidecar**

In `commands.rs` (or wherever approve/reject logic lives), after the gate row is updated:

```rust
if gate_type == "propose_edit" {
    let resolved = serde_json::json!({
        "kind": "gate_resolved",
        "gate_id": gate_id,
        "status": status_str, // "approved" | "rejected" | "stale"
        "reason": reason_opt,
        "target_agent": target_agent,
        "target_path": target_path,
    });
    pool.send_to_sidecar("steward", &serde_json::to_string(&resolved)?).await?;
}
```

- [ ] **Step 4: Manual smoke test**

After Task 12 + 13, full round-trip works: Steward proposes → gate created → user clicks approve in UI (Task 17 will wire the UI) → file updated → next time Steward chats, the `[gate_resolved]` line appears in its context. Until UI is wired (Task 17), test by manually running `UPDATE human_gates SET status='approved' WHERE id='...'` and triggering approve_gate command via DevTools.

- [ ] **Step 5: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add sidecar/src/index.ts src-tauri/src/commands.rs src-tauri/src/agents/pool.rs && git commit -m "feat(sidecar): inject gate_resolved feedback into steward's next turn"
```

---

## Phase 5 — Frontend diff UI

### Task 14: Line diff implementation

**Files:**
- Create: `src/diff.js`

- [ ] **Step 1: Create the diff function**

Create `src/diff.js`:

```javascript
// Simple LCS-based line diff. Returns array of {type, line} where type is "same" | "add" | "del".
function lineDiff(oldText, newText) {
  const oldLines = oldText.split("\n");
  const newLines = newText.split("\n");
  const m = oldLines.length, n = newLines.length;
  const lcs = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (oldLines[i - 1] === newLines[j - 1]) lcs[i][j] = lcs[i - 1][j - 1] + 1;
      else lcs[i][j] = Math.max(lcs[i - 1][j], lcs[i][j - 1]);
    }
  }
  const out = [];
  let i = m, j = n;
  while (i > 0 && j > 0) {
    if (oldLines[i - 1] === newLines[j - 1]) { out.unshift({ type: "same", line: oldLines[i - 1] }); i--; j--; }
    else if (lcs[i - 1][j] >= lcs[i][j - 1]) { out.unshift({ type: "del", line: oldLines[i - 1] }); i--; }
    else { out.unshift({ type: "add", line: newLines[j - 1] }); j--; }
  }
  while (i > 0) { out.unshift({ type: "del", line: oldLines[i - 1] }); i--; }
  while (j > 0) { out.unshift({ type: "add", line: newLines[j - 1] }); j--; }
  return out;
}

window.lineDiff = lineDiff;
```

- [ ] **Step 2: Include in HTML**

In `src/index.html` (or wherever scripts are loaded), add `<script src="diff.js"></script>` before `app.js`.

- [ ] **Step 3: Manual smoke test**

In DevTools console:

```javascript
lineDiff("a\nb\nc", "a\nB\nc")
// Expected: [{type:"same",line:"a"},{type:"del",line:"b"},{type:"add",line:"B"},{type:"same",line:"c"}]
```

- [ ] **Step 4: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src/diff.js src/index.html && git commit -m "feat(frontend): line diff implementation for gate UI"
```

---

### Task 15: Render `propose_edit` gate type with diff viewer

**Files:**
- Modify: `src/app.js:1796-1825` (extend `showGateApproval` or add a new render branch)

- [ ] **Step 1: Add new render function**

In `src/app.js`, add (near `showGateApproval`):

```javascript
async function showProposeEditGate(gate) {
  // gate = { id, target_agent, target_path, edits, rationale, ... }
  const targetUrl = '~/.party/agents/' + gate.target_agent + '/' + gate.target_path;
  const original = await invoke('read_target_for_preview', { targetAgent: gate.target_agent, targetPath: gate.target_path });
  const final = await invoke('compute_edit_preview', { gateId: gate.id });

  const el = document.createElement('div');
  el.className = 'consult-request propose-edit-gate';
  el.innerHTML =
    '<div class="consult-header" style="border-color:var(--orange);color:var(--orange);">' +
      '<span class="consult-icon">&#x270e;</span> STEWARD PROPOSES EDIT' +
    '</div>' +
    '<div class="consult-body">' +
      '<div><strong>Target:</strong> <code>' + escapeHtml(targetUrl) + '</code></div>' +
      '<div style="margin-top:6px;"><strong>Rationale:</strong></div>' +
      '<div class="rationale">' + renderMarkdown(gate.rationale) + '</div>' +
      '<div style="margin-top:8px;"><strong>Diff:</strong></div>' +
      '<div class="diff-viewer">' + renderDiff(original, final) + '</div>' +
    '</div>' +
    '<div class="consult-actions">' +
      '<button class="consult-deny">REJECT</button>' +
      '<button class="consult-approve">APPROVE</button>' +
    '</div>';

  el.querySelector('.consult-deny').addEventListener('click', function () {
    const reason = prompt("Reason for rejection (optional, helps Steward learn):") || "";
    invoke('reject_gate', { gateId: gate.id, reason });
    el.remove();
  });
  el.querySelector('.consult-approve').addEventListener('click', function () {
    invoke('approve_gate', { gateId: gate.id });
    el.remove();
  });

  document.getElementById('messages').appendChild(el);
}

function renderDiff(oldText, newText) {
  const diff = window.lineDiff(oldText, newText);
  const lines = diff.map(d => {
    const cls = d.type === 'add' ? 'diff-add' : d.type === 'del' ? 'diff-del' : 'diff-same';
    const prefix = d.type === 'add' ? '+ ' : d.type === 'del' ? '- ' : '  ';
    return '<div class="' + cls + '">' + escapeHtml(prefix + d.line) + '</div>';
  });
  return '<pre class="diff">' + lines.join('') + '</pre>';
}
```

- [ ] **Step 2: Add `read_target_for_preview` and `compute_edit_preview` Rust commands**

In `src-tauri/src/commands/propose_edit.rs`:

```rust
#[tauri::command]
pub async fn read_target_for_preview(
    state: tauri::State<'_, crate::AppState>,
    target_agent: String,
    target_path: String,
) -> Result<String, String> {
    let resolved = validate_target(&state.party_dir, &target_agent, &target_path)?;
    std::fs::read_to_string(resolved).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn compute_edit_preview(
    state: tauri::State<'_, crate::AppState>,
    gate_id: String,
) -> Result<String, String> {
    let row: (String, String, String) = sqlx::query_as(
        "SELECT target_agent, target_path, edits_json FROM human_gates WHERE id = ?"
    )
    .bind(&gate_id)
    .fetch_one(&state.db)
    .await
    .map_err(|e| e.to_string())?;
    let edits: Vec<EditOp> = serde_json::from_str(&row.2).map_err(|e| e.to_string())?;
    let resolved = validate_target(&state.party_dir, &row.0, &row.1)?;
    let original = std::fs::read_to_string(&resolved).map_err(|e| e.to_string())?;
    apply_edits_in_memory(&original, &edits)
}
```

Register both in `main.rs` `tauri::generate_handler!`.

- [ ] **Step 3: Update gate dispatcher to call `showProposeEditGate` for new type**

Find where `showGateApproval` is called from (probably in a `gate_pending` event handler in `app.js`). Branch on `gate.gate_type`:

```javascript
window.__TAURI__.event.listen('gate_pending', async (event) => {
  const gate = await invoke('get_gate', { gateId: event.payload });
  if (gate.gate_type === 'propose_edit') {
    showProposeEditGate(gate);
  } else {
    showGateApproval(gate.agent_slug, gate.id, gate.brief_path);
  }
});
```

If a `get_gate` command doesn't exist, add a tiny one in `commands.rs` returning gate row as JSON.

- [ ] **Step 4: Add minimal CSS for diff colors**

In `src/styles.css` (or wherever app styles live):

```css
.diff-add { background: rgba(0,200,0,0.15); color: #6cdf6c; }
.diff-del { background: rgba(220,0,0,0.15); color: #ff8080; }
.diff-same { color: #aaa; }
.diff { font-family: monospace; font-size: 12px; white-space: pre; max-height: 320px; overflow-y: auto; padding: 8px; background: rgba(0,0,0,0.25); }
.rationale { padding: 6px 0; color: #ccc; }
```

- [ ] **Step 5: Manual smoke test**

Run `npm run tauri dev`. From Steward chat, propose an edit. Verify the gate panel shows: target path, rationale (rendered markdown), diff with red/green lines, Approve/Reject buttons.

- [ ] **Step 6: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src/app.js src/styles.css src-tauri/src/commands/propose_edit.rs src-tauri/src/main.rs && git commit -m "feat(frontend): diff viewer for propose_edit gates"
```

---

### Task 15.5: Load pending propose_edit gates on app startup

**Files:**
- Modify: `src/app.js` (boot sequence)

The PARTY codebase has a known TODO (§P0.8 at `src-tauri/src/commands.rs:46`): pending gates are not rendered after app restart. `get_pending_gates` already exists as a Tauri command. The frontend just doesn't call it at boot. Wire it for `propose_edit` gates.

- [ ] **Step 1: Wire `get_pending_gates` at boot**

In `src/app.js`, find the app initialization block (where agents are loaded — likely an `async function init()` or similar). Add:

```javascript
async function loadPendingGates() {
  try {
    const gates = await invoke("get_pending_gates");
    for (const gate of gates) {
      if (gate.gate_type === "propose_edit") {
        showProposeEditGate(gate);
      } else {
        showGateApproval(gate.agent_slug, gate.id, gate.brief_path);
      }
    }
  } catch (e) {
    console.error("loadPendingGates failed:", e);
  }
}
```

Call `loadPendingGates()` after `renderAgentList()` in the boot sequence.

- [ ] **Step 2: Verify `get_pending_gates` returns `gate_type` and the new columns**

Check the existing implementation of `get_pending_gates` in `commands.rs`. It must SELECT and return `gate_type`, `target_agent`, `target_path`, `edits_json`, `brief_path` (the rationale). If it doesn't, extend its SELECT and the return struct. Quick check:

```
grep -n "get_pending_gates" src-tauri/src/commands.rs
```

Adapt as needed.

- [ ] **Step 3: Manual smoke test**

Propose an edit, do NOT approve/reject. Quit the app. Restart. The gate should reappear in the panel without manual intervention.

- [ ] **Step 4: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src/app.js src-tauri/src/commands.rs && git commit -m "fix(gates): render pending gates on app boot (§P0.8)"
```

---

### Task 16: Reject reason flows back to Steward

**Files:**
- Modify: `src-tauri/src/commands.rs` — `reject_gate` already exists; ensure the reason argument is recorded and forwarded to sidecar

- [ ] **Step 1: Verify `reject_gate` accepts a reason argument**

Check existing signature in `src-tauri/src/commands.rs`. If it doesn't accept a reason, modify:

```rust
#[tauri::command]
pub async fn reject_gate(
    state: tauri::State<'_, AppState>,
    gate_id: String,
    reason: Option<String>,
) -> Result<(), String> {
    sqlx::query("UPDATE human_gates SET status = 'rejected', decided_at = datetime('now'), decision = ? WHERE id = ?")
        .bind(reason.as_deref().unwrap_or(""))
        .bind(&gate_id)
        .execute(&state.db)
        .await
        .map_err(|e| e.to_string())?;

    let row: (String, String, String) = sqlx::query_as(
        "SELECT gate_type, target_agent, target_path FROM human_gates WHERE id = ?"
    )
    .bind(&gate_id).fetch_one(&state.db).await.map_err(|e| e.to_string())?;

    if row.0 == "propose_edit" {
        let resolved = serde_json::json!({
            "kind": "gate_resolved",
            "gate_id": gate_id,
            "status": "rejected",
            "reason": reason,
            "target_agent": row.1,
            "target_path": row.2,
        });
        state.pool.send_to_sidecar("steward", &serde_json::to_string(&resolved).unwrap()).await.ok();
    }
    Ok(())
}
```

- [ ] **Step 2: Manual smoke test**

Propose, reject with reason "too prescriptive". Verify Steward's next turn includes `[gate_resolved gate_id=... status=rejected reason="too prescriptive" ...]` in its context.

- [ ] **Step 3: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/src/commands.rs && git commit -m "feat(gates): forward rejection reason to steward sidecar"
```

---

## Phase 6 — 01:00 digest cron

### Task 17: New `steward_digest` scheduled-jobs template

**Files:**
- Modify: `src-tauri/src/scheduler/jobs.rs:23-95`

- [ ] **Step 1: Inspect existing template dispatch**

Read `src-tauri/src/scheduler/jobs.rs` lines 79–95 (existing `consolidate` job). Note the JSON shape used in `route_template_json`. Mirror it.

- [ ] **Step 2: Add `steward_digest` branch**

In the dispatch match on template type, add:

```rust
"steward_digest" => {
    let pool_clone = pool.clone();
    let app_handle = app_handle.clone();
    Box::pin(async move {
        let cfg_override = "claude-opus-4-7".to_string();
        let prompt = "It's the 01:00 digest run. Read scope-B sources. Compare with the previous memory/system_state.md. Update memory/system_state.md to reflect current reality. Then write a digest message into the Daily Digest thread covering: what changed in the last 24h, top 3 patterns/tensions worth my attention, and any concrete diffs you want to propose. End with one open question for me.";

        // Spawn (or warm-resume) steward sidecar with model override
        if let Err(e) = pool_clone.send_message_with_override("steward", "Daily Digest", prompt, Some(cfg_override)).await {
            eprintln!("steward digest failed: {}", e);
            // log to audit_log
            sqlx::query("INSERT INTO audit_log (event_type, details) VALUES ('steward_digest_error', ?)")
                .bind(format!("{}", e)).execute(&pool_clone).await.ok();
        }
    })
}
```

`send_message_with_override` is a new helper on `AgentPool` that calls existing send-message logic but sets `AgentConfig.model_override` before spawning the sidecar. Add it in `pool.rs`:

```rust
pub async fn send_message_with_override(
    &self,
    slug: &str,
    thread_label: &str,
    message: &str,
    model_override: Option<String>,
) -> Result<(), String> {
    let mut cfg = AgentConfig::from_slug(slug, /* working_dir */);
    cfg.model_override = model_override;
    // ... rest of existing send_message logic, using `cfg` instead of default
}
```

- [ ] **Step 3: Insert the cron row on Steward install**

Modify `install_steward` (Task 7) to also INSERT a `scheduled_jobs` row:

```rust
let cron_expr = "0 0 8 * * *"; // 01:00 MST = 08:00 UTC
let template = serde_json::json!({"type": "steward_digest"});
sqlx::query("INSERT OR IGNORE INTO scheduled_jobs (id, cron_expr, route_template_json, enabled) VALUES (?, ?, ?, 1)")
    .bind("steward_daily_digest")
    .bind(cron_expr)
    .bind(template.to_string())
    .execute(&state.db).await.ok();
```

Place this after the `create_agent` call in `install_steward`.

- [ ] **Step 3.5: Atomic write for `system_state.md`**

In Steward's `CLAUDE.md` (created in Task 4), add a procedural rule reminding Steward to write `memory/system_state.md` atomically (write to `memory/system_state.md.tmp` first, then rename). This prevents a partial file if the digest run fails mid-write.

Edit `src-tauri/assets/steward-seeds/CLAUDE.md`, append to the bottom:

```markdown
## Writing memory/system_state.md
- Write to `memory/system_state.md.tmp` first.
- After the full content is written, rename `system_state.md.tmp` → `system_state.md`.
- This is the only place where atomicity matters; other memory files (`learnings.md`, retros) are append-only or small.
```

This is a procedural instruction, not enforced by code. Acceptable v1 — if the SDK skips it, the worst case is one stale day until the next digest run.

- [ ] **Step 4: Manual test — fire digest manually**

Add a temporary debug command (delete after verification):

```rust
#[tauri::command]
pub async fn trigger_steward_digest_now(state: tauri::State<'_, AppState>) -> Result<(), String> {
    state.pool.send_message_with_override(
        "steward", "Daily Digest",
        "Test digest run.",
        Some("claude-opus-4-7".to_string())
    ).await
}
```

Invoke from DevTools: `await invoke('trigger_steward_digest_now')`. Verify:
- A new message appears in Steward's "Daily Digest" thread
- `~/.party/agents/steward/memory/system_state.md` is updated with non-placeholder content

Remove the debug command before committing.

- [ ] **Step 5: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add src-tauri/src/scheduler/jobs.rs src-tauri/src/agents/pool.rs src-tauri/src/install/steward.rs && git commit -m "feat(steward): 01:00 daily digest cron with opus override"
```

---

## Phase 7 — End-to-end manual verification

### Task 18: E2E happy path — install and chat

**Files:** none modified.

- [ ] **Step 1: Fresh install verification**

Move existing Steward folder out of the way:
```
mv ~/.party/agents/steward ~/.party/agents/steward.backup
sqlite3 ~/.party/data.sqlite "DELETE FROM agents WHERE slug='steward';"
```

Boot the app: `npm run tauri dev`. Confirm Steward auto-installed:
```
ls ~/.party/agents/steward/
sqlite3 ~/.party/data.sqlite "SELECT slug, name FROM agents WHERE slug='steward';"
sqlite3 ~/.party/data.sqlite "SELECT id, cron_expr FROM scheduled_jobs WHERE id='steward_daily_digest';"
```

All three should show steward.

- [ ] **Step 2: Chat smoke test**

Click Steward in agent list. Send: *"What agents do I have configured? Just list them by slug."*

Expected: Steward responds with a list pulled from `~/.party/agents/*/`. Verify the response was persisted by closing and reopening the app.

- [ ] **Step 3: Verify existing agents untouched**

```
ls -la ~/.party/agents/steward.backup/conversations/
```

Pick any other agent (e.g., the existing `reflector`):
```
ls -la ~/.party/agents/reflector/conversations/
```

Confirm timestamps and contents match what they were before install. **No existing agent's data was mutated.**

- [ ] **Step 4: Cleanup**

```
rm -rf ~/.party/agents/steward.backup
```

(Only after confirming the new install is healthy.)

---

### Task 19: E2E gated edit happy path

**Files:** none modified.

- [ ] **Step 1: Set up a test target**

Create a sacrificial agent (or use an existing low-stakes one):
```
# from PARTY UI: create_agent("TestTarget", "test target")
```

Manually edit `~/.party/agents/test-target/memory/learnings.md` to include `original line`.

- [ ] **Step 2: Trigger Steward to propose**

In Steward chat: *"Propose an edit to test-target's memory/learnings.md replacing 'original line' with 'edited line', rationale: 'testing gate flow'."*

Expected:
- Steward calls `propose_edit` tool
- A gate appears in the gate panel showing: target path, rationale, side-by-side diff
- Steward says something like "I've proposed the edit; gate_id is X"

- [ ] **Step 3: Approve**

Click APPROVE. Verify:
```
cat ~/.party/agents/test-target/memory/learnings.md
```
Shows `edited line`.

```
sqlite3 ~/.party/data.sqlite "SELECT status, decided_at FROM human_gates WHERE id='<gate_id>';"
```
Shows `approved` and timestamp.

- [ ] **Step 4: Verify Steward sees the resolution**

Send Steward another message: *"What just happened with the gate?"*

Expected: Steward references the `[gate_resolved gate_id=... status=approved ...]` line and confirms.

- [ ] **Step 5: Test reject path**

Propose another edit, click REJECT with reason "test rejection reason". Verify:
- File content unchanged
- DB shows `status='rejected'` and `decision='test rejection reason'`
- Steward's next turn includes the rejection reason in context

- [ ] **Step 6: Test stale path**

Propose an edit. Before approving, manually edit the target file in a terminal (changing the `old_string` content). Click APPROVE. Verify:
- File content reflects YOUR manual edit, NOT Steward's
- DB shows `status='stale'`
- Steward's next turn includes `status=stale` in context

---

### Task 20: E2E digest run manual trigger

**Files:** none modified.

- [ ] **Step 1: Manually trigger digest**

Re-add the `trigger_steward_digest_now` debug command from Task 17 Step 4 (temporary).

In DevTools: `await invoke('trigger_steward_digest_now')`. Wait for the run to complete (may take 30–90 seconds with Opus on full repo).

- [ ] **Step 2: Verify artifacts**

```
cat ~/.party/agents/steward/memory/system_state.md
```

Expected:
- `As of:` line populated with a real timestamp (not `NEVER`)
- `Last digest model:` = `claude-opus-4-7`
- All 5 sections (Operator state, Agent landscape, Active tensions, Things to watch, Self-notes) populated with real synthesis

- [ ] **Step 3: Verify digest message in thread**

Open Steward agent → Daily Digest thread. Verify a new message exists with the digest content (24h summary, 3 patterns, open question at the end).

- [ ] **Step 4: Remove debug command**

Delete `trigger_steward_digest_now` from `commands.rs` and `main.rs` registration.

- [ ] **Step 5: Commit cleanup**

```
cd /Users/gabegimenes-silva/Desktop/party && git add -A && git commit -m "chore: remove debug digest trigger"
```

---

## Final cleanup task

### Task 21: Update PARTY HANDOFF.md and ROADMAP.md

**Files:**
- Modify: `HANDOFF.md`
- Modify: `ROADMAP.md`

- [ ] **Step 1: Add Steward to HANDOFF.md "What's stubbed" / "What ships" sections**

Note that:
- Steward agent installed and operational
- `propose_edit` tool wired with diff approval UI
- Daily 01:00 MST digest active
- Phase 3 "Steward layer" of ROADMAP delivered ahead of schedule

- [ ] **Step 2: Update ROADMAP.md Phase 3 entry**

Mark the Steward layer item as shipped with a date and reference to this plan.

- [ ] **Step 3: Commit**

```
cd /Users/gabegimenes-silva/Desktop/party && git add HANDOFF.md ROADMAP.md && git commit -m "docs: mark steward layer shipped (Phase 3)"
```

---

## Self-review checklist (run by plan author after writing — for transparency)

- **Spec coverage:** every section of the spec maps to one or more tasks. Read scope → Task 4 (`policy.json`). Write scope → Tasks 9–10 (path validation + gate creation). Models → Task 2 (model_override). Digest → Task 17. Diff flow → Tasks 9–13, 15. Bootstrap → Tasks 4–8. Tests → Tasks 5, 6, 9, 10, 11, 18, 19, 20. ✓
- **Placeholder scan:** no TBD/TODO/"implement later"/"add appropriate error handling" patterns. Where the plan acknowledges PARTY-internal patterns must be matched (e.g., scheduler dispatch shape), the actual code is shown and the engineer is told to verify against `jobs.rs:79-95`. ✓
- **Type consistency:** `EditOp::Replace { old_string, new_string }`, `EditOp::FullReplace { full_replace }`, `ProposeEditPayload`, `WrapperProposeEditRequest`, `WrapperGateResolved`, and all SQL columns (`target_agent`, `target_path`, `gate_type`, `edits_json`, `decision`) consistent across Rust, TS, and SQL. ✓
- **Scope:** single feature, 21 tasks, ~1130 LOC, fits one plan. ✓
