# PARTY Steward Agent — Design

**Date:** 2026-04-29
**Status:** Spec — pending implementation plan
**Repo target:** `/Users/gabegimenes-silva/Desktop/party/` (canonical PARTY checkout)

## Problem

The user wants a "meta agent" inside PARTY they can chat with — one that reviews all PARTY agent conversations, memory, and operator repo state, surfaces patterns and improvements, and proposes concrete edits to other agents' memory and instructions for human approval. This capability does not exist today.

PARTY's existing `reflector` agent is a narrow per-run retro writer (Haiku, single-bullet output to its own agent's `instructions/AGENT.md`). It does not read across agents and does not propose diffs.

PARTY's `ROADMAP.md` describes a deferred "Steward layer" with system-level oversight responsibilities. This work brings that layer forward, scoped to the user's actual needs.

## Goals

1. A new PARTY agent named `steward` that the user chats with through PARTY's existing chat UI.
2. Steward reads broadly across PARTY agents and the operator repo (read-only).
3. Steward proposes concrete file diffs for cross-agent improvements; every diff requires human approval before being applied.
4. Steward runs a daily 01:00 MST digest powered by Opus 4.7 that synthesizes the operation's state into a memory file and posts a digest message into a "Daily Digest" thread.
5. No existing PARTY agent data (conversations, memory, instructions, skills) is deleted, overwritten, or destructively migrated by installing Steward.

## Non-goals

- Replacing or modifying the existing `reflector` agent. Steward is additive; reflector keeps writing per-run retros.
- Steward writing to operator repo files (read-only for v1; revisit later).
- Auto-applying changes without per-edit approval. All cross-agent edits are gated.
- Fixing the known PARTY persistence bug (events dropped on agent switch). Out of scope for this work; fix separately first.
- Calendar/task awareness, Slack/email gate forwarding, retry on failed digests, cross-day archive of memory file. All deferred.

## Architecture

### Identity

| Field | Value |
|---|---|
| Slug | `steward` |
| Folder | `~/.party/agents/steward/` |
| Working dir | `/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/` |
| Default model | `claude-sonnet-4-6` (1M context) |
| Digest model | `claude-opus-4-7` (1M context, override per scheduled run) |
| Status on install | `Active` |

Working dir matches the convention used by the existing `reflector` agent.

### Read scope (enforced via `policy.json` allowed_paths)

1. `~/.party/agents/*/` — every PARTY agent's `agent.json`, `CLAUDE.md`, `instructions/`, `memory/`, `conversations/`, `retros/`. Excludes `~/.party/agents/steward/` itself (avoids self-loop confusion during synthesis).
2. `/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/` — full operator repo, including `tasks/lessons.md`, `HANDOFF.md`, `apps/`, `docs/`, code.
3. `/Users/gabegimenes-silva/.claude/projects/-Users-gabegimenes-silva-Desktop-ClaudeDataAgent--/memory/` — operator project memory (Claude Code auto-memory).
4. `~/.party/data.sqlite` — read-only, for cross-agent run/chain history.

### Write scope

- **Direct write (no gate):** `~/.party/agents/steward/memory/*` and `~/.party/agents/steward/retros/*` only.
- **Gated write (human approval required):** files under `~/.party/agents/<other>/` matching one of: `memory/**`, `instructions/AGENT.md`, `CLAUDE.md`, `skills/**`.
- **Forbidden:** other agents' `agent.json`, `conversations/`, `policy.json`. All operator repo files. Path traversal attempts.

The write boundary is mechanically enforced in the Rust `propose_edit` command before any gate row is created. Steward has no direct file-write capability into other agents' folders, so the data-preservation requirement is satisfied by construction.

### Models

- **Interactive chat:** Sonnet 4.6 — strong reasoning, low cost, plenty of context for ad-hoc questions.
- **01:00 digest:** Opus 4.7 — paid for once per day, produces durable artifacts that cheapen all subsequent same-day chat.

**Implementation note:** PARTY today has per-agent model selection (`AgentConfig` per-slug), but per-*run* model override is not confirmed present. The implementation plan must either (a) verify and use existing per-run override, (b) add a small extension to pass `model_override` from the scheduler into `runQuery`, or (c) accept always-Opus for Steward at cost. Option (b) is recommended; (a) is a verification step at start of implementation.

User's stated reason for 01:00 timing: less contention with daytime API quota, fresh digest waiting in the morning.

## Data flow

### Daily digest (01:00 MST / 08:00 UTC)

```
tokio-cron-scheduler fires
   ↓
spawn steward sidecar with model_override=claude-opus-4-7
   ↓
send digest prompt (see below)
   ↓
sidecar reads scope-B sources via Read/Glob/Grep tools
   ↓
sidecar writes:
   - ~/.party/agents/steward/memory/system_state.md  (overwrite)
   - new message in "Daily Digest" thread
   - any propose_edit calls → pending gates
   ↓
sidecar exits (or warm-resumes session)
```

### Digest prompt (sent as user-style message)

> *"It's the 01:00 digest run. Read scope-B sources. Compare with the previous `memory/system_state.md`. Update `memory/system_state.md` to reflect current reality. Then write a digest message into the `Daily Digest` thread covering: what changed in the last 24h, top 3 patterns/tensions worth my attention, and any concrete diffs you want to propose. End with one open question for me."*

### Failure handling

- Digest run failure (rate limit, sidecar crash, model error) → `audit_log` entry, previous `system_state.md` untouched, no digest message that day.
- Next morning chat detects stale `as_of` timestamp and falls back to fresh Reads to fill gaps.
- No retry logic in v1.

### `system_state.md` schema

Plain markdown, fully overwritten each digest. Fixed section order:

```markdown
# Steward — System State

**As of:** <ISO 8601 UTC>
**Last digest model:** claude-opus-4-7
**Sources scanned:** N agents, M threads, K repo files

## Operator state
[1–2 paragraphs: what Gabe is currently working on, key projects, recent decisions]

## Agent landscape
[One short paragraph per active PARTY agent]

## Active tensions
[Cross-agent contradictions, gaps, mismatches with operator goals]

## Things to watch
[Observed patterns, drift signals, weak signals]

## Self-notes
[Steward's own meta-learning about being useful]
```

Continuity across days lives in the `Daily Digest` thread (timestamped messages), not in this file.

## Diff proposal flow (Tier 2)

PARTY's `human_gates` table already has an `edits_json` column today (`db/schema.rs:115`) that is never populated and never rendered. This work fills in that path end-to-end.

### `propose_edit` — new SDK tool

Exposed to the Steward sidecar via the Claude Agent SDK tool registry.

```typescript
propose_edit({
  target_agent: string,        // not "steward"
  target_path: string,         // relative to target agent folder
  edits: Array<{old_string, new_string}> | {full_replace: string},
  rationale: string            // markdown
})
→ { gate_id: string, status: "pending" }
```

Non-blocking. Steward keeps reasoning. The outcome lands in its next turn as a `gate_resolved` event.

### Rust `propose_edit` command (path validation = the safety boundary)

In `src-tauri/src/commands.rs`. Validates in this order:

1. `target_agent != "steward"` (Steward must use direct write for itself)
2. `target_path` matches one of: `memory/**`, `instructions/AGENT.md`, `CLAUDE.md`, `skills/**`
3. Resolved absolute path is inside the target agent's folder (path traversal check)
4. Apply edits in-memory; fail if any `old_string` not found
5. Insert `human_gates` row: `kind="propose_edit"`, `agent_slug="steward"` (proposer), `target_agent`, `target_path`, `edits_json`, `preview_json` (rendered before/after for fast UI render), `rationale`, `status="pending"`
6. Emit `gate_pending` event to frontend

### Approval UI (vanilla JS in `src/app.js`)

New render branch in the right-pane gate area when `gate.kind === "propose_edit"`:

- Header: *"Steward proposes edit to `<target_agent>/<target_path>`"*
- Rationale block (rendered markdown)
- Side-by-side diff viewer (line-numbered, red-bg old / green-bg new). Computed via small line-diff implementation; library only if needed.
- Buttons: **Approve** | **Reject** (with optional reason textarea)
- Pending gates reload on app startup (also fixes the `§P0.8` TODO at `commands.rs:46` for proposed-edit gates)

`Modify-then-approve` deferred to v1.1. For v1, modifications go via Reject + reason; Steward redrafts.

### Outcome events (back to Steward)

```
[gate_resolved gate_id=<id> status=approved target=<agent>/<path>]
[gate_resolved gate_id=<id> status=rejected reason="<text>"]
[gate_resolved gate_id=<id> status=stale]   // file changed under us
```

These resolution events feed into Steward's next-turn context so it learns from both approval and rejection patterns. Cumulative learning lands in the `Self-notes` section of `system_state.md` over time.

### Edge cases

- **Concurrent edits:** if a target file changes between gate creation and approval, the `old_string` match fails → gate marked `stale`, Steward notified, must repropose.
- **Steward proposes edit to nonexistent file:** rejected at validation, error returned to Steward.
- **Multiple pending gates on same file:** allowed; applied in approval order; later gates may go stale.
- **Steward target_agent = "steward":** rejected at validation. Self-edits use direct write.

## Bootstrap / install

A one-shot Rust command `install_steward` (or small CLI script). Idempotent.

1. **Pre-flight, both must agree:** `~/.party/agents/steward/` exists ⟺ `agents.steward` row exists. Mismatch → abort with explicit error message; user resolves manually.
2. **Already installed (both exist):** exit 0 with confirmation.
3. **Fresh install:**
   - Create `~/.party/agents/steward/` with subfolders: `memory/`, `instructions/`, `skills/`, `conversations/`, `retros/`, `workspace/`, `data/`
   - Write seed files: `agent.json`, `CLAUDE.md`, `instructions/AGENT.md`, `policy.json`, `memory/system_state.md` (placeholder, `as_of: NEVER`), `memory/learnings.md` (empty)
   - Insert SQLite row via existing `create_agent` flow
   - Schedule the 01:00 cron job
   - Print confirmation listing every file written

**Mechanically guaranteed:** install code touches only paths under `~/.party/agents/steward/` and the `agents` SQLite row for slug `steward`. No reads from other agents during install. No mutations to operator repo. Verifiable post-install via `find ~/.party -newer <pre-install-marker>` showing only steward paths.

## Defaults applied to open questions

- **Digest thread label:** `Daily Digest` (single fixed thread, timestamped messages).
- **Existing `reflector` agent included in Steward's read scope:** yes — its per-agent retros are exactly the kind of signal Steward should aggregate.
- **Unread badge on Steward agent in agent list when fresh digest waiting:** deferred (nice-to-have, ~30 LOC, not v1).

## Sequencing & dependencies

1. **Fix the known PARTY persistence bug first** (events dropped on agent switch — root cause `pool.rs:167-175` per exploration). Separate PR. Steward is affected by this bug like any other agent; fixing it cleanly first keeps the Steward PR focused.
2. **Then implement Steward** in `party/` (canonical checkout). `party-dev/` cleanups can be merged separately if desired.

## Implementation surface (rough sizing)

| Area | LOC estimate | Files |
|---|---|---|
| Rust: `propose_edit` command + path validation | ~250 | `src-tauri/src/commands.rs`, helpers |
| Rust: `install_steward` command | ~150 | new file `src-tauri/src/install/steward.rs` |
| Rust: cron job for digest | ~80 | `src-tauri/src/scheduler.rs` (existing) |
| TypeScript sidecar: `propose_edit` tool registration | ~50 | `sidecar/src/index.ts`, `sidecar/src/protocol.ts` |
| Frontend: diff viewer + new gate render branch | ~250 | `src/app.js` |
| Seed files for steward agent | ~150 | `src-tauri/assets/steward-seeds/` |
| Tests | ~200 | Rust unit tests in same files |
| **Total** | **~1130 LOC** | |

No DB schema migration required (`edits_json` column already exists).

## Tests

- **Rust unit:** path validation (path traversal, allow-list match, target_agent != steward), gate creation, gate apply, gate stale on file change, install idempotency, install pre-flight mismatch detection.
- **End-to-end happy path:** install Steward → send chat → manually trigger digest → assert `system_state.md` written + digest thread message present.
- **End-to-end gated edit:** Steward proposes edit to test agent's `learnings.md` → assert gate appears → approve → assert file updated → assert Steward sees `gate_approved` event next turn.
- **Frontend:** manual smoke test of diff viewer with hand-crafted gate row (PARTY has no automated frontend test infrastructure today; not adding it here).

## Risk register

| Risk | Mitigation |
|---|---|
| Steward proposes destructive or wrong edits | Every cross-agent edit gated; approval is the kill switch. Reject + reason teaches Steward. |
| `system_state.md` drifts during 24h gap | `as_of` timestamp visible; chat session falls back to fresh Reads when memory is stale. |
| Digest run fails silently | `audit_log` entry; user notices missing digest message in thread. (Not silent in practice.) |
| Persistence bug drops Steward events on agent switch | Out of scope here; fixed in prerequisite PR. |
| User commits `~/.party/` to git for cross-day memory archive | Acceptable side effect, not designed for. Don't rely on it. |
| Path traversal in `propose_edit` | Resolved absolute path check at step 3 of validation. |
| Concurrent file edits | Gate marked stale, Steward must repropose. Better than silent overwrite. |

## What this design does NOT solve

- The persistence bug (separate work).
- Editing operator-side knowledge (`tasks/lessons.md`, `HANDOFF.md`, project memory) — Steward reads it, can't edit it. Add later if useful.
- Auto-application of low-risk diffs (Tier 3, deliberately punted).
- Anything in the Phase 0 ROADMAP list (permissions enforcement, pool lifecycle, budget, etc.) — Steward inherits whatever foundation PARTY has at integration time.
