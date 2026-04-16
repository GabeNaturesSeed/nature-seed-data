# PARTY AI Backend + Agent Provisioning — Design Specification

**Date:** 2026-04-15
**Status:** Approved
**Repo:** `~/Desktop/party/` (standalone PARTY repo)
**Data Repo:** `~/Desktop/ClaudeDataAgent -/` (Nature's Seed data hub)

---

## Overview

Wire the Claude Agent SDK (Python) as the AI backend for PARTY. Each agent runs through a Python bridge process that wraps the SDK, providing session persistence, system prompts, tool access, and streaming structured events. Agents work inside the ClaudeDataAgent repo where all scripts, `.env` credentials, and infrastructure already exist.

This spec covers three sub-projects delivered as one implementation:
1. Agent SDK bridge (Python sidecar + Rust integration)
2. Agent provisioning (config, AGENT.md generation)
3. Six production agents (Google Ads, Klaviyo, Amazon, Walmart, WooCommerce, Shippo)

---

## Architecture

### Why Agent SDK (Not CLI)

The Claude Code CLI is interactive-only — no subprocess/streaming JSON mode. The **Claude Agent SDK** (`claude-agent-sdk` Python package) is purpose-built for programmatic use and provides:
- Structured message objects (not terminal ANSI)
- Session persistence via `resume=session_id`
- System prompt injection via `system_prompt` option
- Tool restrictions via `allowed_tools` / `permission_mode`
- Cost limits via `max_budget_usd`
- Turn limits via `max_turns`
- All Claude Code tools: Read, Write, Edit, Bash, Grep, Glob

### Bridge Architecture

```
PARTY (Rust TUI)
  │
  ├─ Spawns: python3 ~/.party/agent_bridge.py
  │          (single long-lived process, multiplexes all agents)
  │
  ├─ Sends via stdin (JSON lines):
  │    {"cmd":"message","agent":"google-ads","content":"What's our ROAS this week?"}
  │    {"cmd":"resume","agent":"google-ads"}
  │    {"cmd":"kill","agent":"google-ads"}
  │
  ├─ Receives via stdout (JSON lines):
  │    {"agent":"google-ads","type":"assistant","content":"Let me check..."}
  │    {"agent":"google-ads","type":"tool_use","tool":"Bash","input":"python3 daily_pull.py ..."}
  │    {"agent":"google-ads","type":"tool_result","output":"ROAS: 4.2x"}
  │    {"agent":"google-ads","type":"result","session_id":"abc123","cost_usd":0.05}
  │    {"agent":"google-ads","type":"error","message":"Rate limited"}
  │
  └─ Python bridge internals:
       - One asyncio event loop
       - Per-agent: query() call with system_prompt from AGENT.md
       - resume=session_id for session persistence
       - allowed_tools per agent config
       - permission_mode="acceptEdits" (auto-approve file ops)
       - Streams messages back as JSON lines tagged with agent slug
```

### Data Flow

```
User types message in PARTY
  → Message saved to thread JSON (existing persistence)
  → JSON command sent to bridge stdin: {"cmd":"message","agent":"...","content":"..."}
  → Bridge calls Agent SDK query() with system_prompt + resume
  → SDK processes, agent may use tools (Bash, Read, Write, etc.)
  → Bridge serializes each message to JSON line on stdout
  → Rust reads stdout lines, parses, routes to correct agent
  → Events become Agent/System messages in the thread
  → Messages rendered in real-time in the messages pane
  → Agent messages saved to disk as they arrive
```

### Process Lifecycle

1. **Bridge start** — PARTY spawns the bridge process on first agent message. Single process handles all agents.
2. **Send message** — JSON line written to bridge stdin. Bridge routes to the right agent's SDK session.
3. **Receive events** — Bridge streams JSON lines on stdout. Each line tagged with agent slug.
4. **Session persistence** — Bridge captures `session_id` from ResultMessage, saves to agent's config. Next message uses `resume=session_id`.
5. **Agent concurrency** — Bridge uses asyncio to handle multiple agents. Only one active query per agent (messages queue if agent is busy).
6. **Kill** — On PARTY quit: send `{"cmd":"shutdown"}`, bridge gracefully stops all queries. On agent delete: `{"cmd":"kill","agent":"slug"}`.
7. **Resume on restart** — PARTY restarts → spawns bridge → first message to an agent includes saved session_id → SDK resumes conversation.

---

## New Files

### `~/.party/agent_bridge.py` — Python Sidecar

Single Python script, installed alongside PARTY. Requires `pip install claude-agent-sdk`.

**Responsibilities:**
- Read JSON commands from stdin (one per line)
- Maintain per-agent SDK sessions (system_prompt, session_id, tools)
- Stream structured events to stdout as JSON lines
- Handle concurrent agents via asyncio
- Persist session IDs to agent config files

**Commands (stdin):**

| Command | Fields | Effect |
|---------|--------|--------|
| `message` | `agent`, `content`, `session_id?` | Send message to agent, stream response |
| `kill` | `agent` | Cancel agent's active query |
| `shutdown` | — | Gracefully stop all agents, exit |

**Events (stdout):**

| Event | Fields | Meaning |
|-------|--------|---------|
| `assistant` | `agent`, `content` | Agent's text response (may arrive in chunks) |
| `tool_use` | `agent`, `tool`, `input` | Agent is calling a tool |
| `tool_result` | `agent`, `output` | Tool returned a result |
| `result` | `agent`, `session_id`, `cost_usd`, `input_tokens`, `output_tokens` | Query complete |
| `error` | `agent`, `message` | Something went wrong |
| `status` | `agent`, `status` | Agent status change (thinking, tool_calling, done) |

**Agent configuration loaded from:**
```
~/.party/agents/{slug}/agent.json    → session_id, allowed_tools
~/.party/agents/{slug}/instructions/AGENT.md → system_prompt (read as string)
~/.party/agents/{slug}/skills/*.md   → appended to system_prompt
```

### `src/agent_runner.rs` — Rust Bridge Manager

Manages the single bridge subprocess and routes events.

```rust
pub struct BridgeProcess {
    child: tokio::process::Child,
    stdin: tokio::process::ChildStdin,
    event_rx: tokio::sync::mpsc::Receiver<AgentEvent>,
}

pub struct AgentEvent {
    pub agent: String,           // slug
    pub event_type: EventType,
}

pub enum EventType {
    AssistantText(String),
    ToolUse { tool: String, input: String },
    ToolResult { output: String },
    Result { session_id: String, cost_usd: f64 },
    Error(String),
    Status(String),
}
```

**Public API:**

```rust
pub fn spawn_bridge(bridge_path: &Path, env_vars: &HashMap<String, String>) -> Result<BridgeProcess>
pub fn send_message(bridge: &mut BridgeProcess, agent: &str, content: &str, session_id: Option<&str>) -> Result<()>
pub fn try_recv(bridge: &mut BridgeProcess) -> Option<AgentEvent>
pub fn kill_agent(bridge: &mut BridgeProcess, agent: &str) -> Result<()>
pub fn shutdown(bridge: &mut BridgeProcess) -> Result<()>
```

### `src/env_loader.rs` — .env Parser

Parses ClaudeDataAgent's `.env` file (spaces around `=`, quotes around values).

```rust
pub fn load_env(path: &Path) -> Result<HashMap<String, String>>
// Per line: skip comments (#) and blanks
// Split on first '='
// Strip whitespace from key and value
// Strip surrounding quotes (' or ") from value
```

---

## Modified Existing Modules

### `src/models.rs`

Add:

```rust
pub struct PartyConfig {
    pub env_file: PathBuf,
    pub working_dir: PathBuf,
    pub bridge_script: PathBuf,  // path to agent_bridge.py
}
```

Add to Agent:

```rust
    #[serde(default)]
    pub session_id: Option<String>,   // saved Agent SDK session ID
    #[serde(default)]
    pub total_cost_usd: f64,          // cumulative API cost
```

### `src/store.rs`

Add:

```rust
pub fn load_config(base: &Path) -> Result<PartyConfig>
pub fn save_config(base: &Path, config: &PartyConfig) -> Result<()>
pub fn install_bridge(base: &Path) -> Result<PathBuf>  // writes agent_bridge.py to ~/.party/
```

### `src/app.rs`

Changes:
- Add field: `pub bridge: Option<BridgeProcess>`
- Add field: `pub config: PartyConfig`
- Add field: `pub env_vars: HashMap<String, String>`
- Modify `send_message()`: after persisting to disk, also send JSON command to bridge. If bridge not running, spawn it first (lazy start).
- Modify `handle_event()`: after polling crossterm, also poll bridge via `try_recv()`. Route incoming events by agent slug → append as Agent/System messages to active thread.
- Modify `delete_selected_agent()`: send kill command before deleting files.
- Add method: `fn poll_bridge_events(&mut self) -> Result<()>`
- On quit: send shutdown command to bridge.

### `src/main.rs`

Changes:
- Load `PartyConfig` from `~/.party/config.json` on startup
- Load env vars via `env_loader::load_env()`
- Pass config + env_vars to `App::new()`
- First run: create default config.json, install bridge script, prompt for env_file path if not found

### `src/ui/messages.rs`

Changes:
- `ToolUse` events render as System messages: `"sys  HH:MM\n    [tool: {name}] {input}"`
- `ToolResult` events append below: `"    → {output}"`
- `AssistantText` events render as Agent messages (Role::Agent)
- While waiting for result (between message send and Result event), show "thinking..." in dim italic
- `Result` events update agent's cost counter (not rendered as a message)

### `src/theme.rs`

Add:
- `pub fn processing() -> Style` — dim italic, for "thinking..." indicator

---

## Credential System

### `~/.party/config.json`

```json
{
  "env_file": "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/.env",
  "working_dir": "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
}
```

### Flow

1. PARTY reads `config.json` on startup
2. Loads all env vars from `env_file` path via `env_loader`
3. When spawning bridge process, ALL env vars are injected into subprocess environment
4. Bridge process inherits all env vars — SDK queries run with full credential access
5. Each agent's AGENT.md documents which credentials are "theirs" (documentation, not enforcement)

---

## The Six Agents

### Agent 1: Google Ads (`google-ads`)

**Mission:** Manage paid acquisition — campaign performance, bid optimization, budget allocation, ROAS tracking.

**Systems:** Google Ads API, GA4, Google Merchant Center, Google Search Console

**Credentials documented:** `GOOGLE_ADS_*`, `GOOGLE_ANALYTICS_PROPERTY_ID`, `GOOGLE_MERCHANT_CENTER_ID`

**Key IDs:** Customer ID `599-287-9586`, Login CID `838-619-4588`, GA4 Property `294622924`, Merchant ID `138935850`

**Skills copied:**
- `data-orchestrator` (routing)
- Relevant sections from `woocommerce-api` (product data for Shopping campaigns)

**AGENT.md includes:**
- Google Ads API patterns (from `daily_pull.py`'s `pull_google_ads()`)
- GA4 reporting API patterns
- Merchant Center Content API patterns
- Search Console API patterns
- Shopping campaign optimization rules (from `marketing/google-ads-audit/`)
- ROAS/MER calculation formulas (from Supabase `daily_summary` view)
- `shopping_performance_view` + `segments.date` requires `campaign.id` in SELECT
- PMax sub-campaign ID grouping rules
- WC order attribution (GCLID parsing from `_wc_order_attribution_session_entry`)
- 4-year audit findings (from `marketing/google-ads-audit/`)
- Reference to existing scripts: `daily_pull.py`, `drip/`, `campaign_performance_curves.py`

**Allowed tools:** `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`

---

### Agent 2: Klaviyo Email (`klaviyo-email`)

**Mission:** Email marketing — campaigns, flows, segments, templates, deliverability.

**Systems:** Klaviyo API + MCP tools

**Credentials documented:** `KLAVIYO_API`

**Key IDs:** Account `H627hn`, Placed Order metric `VLbLXB`, Opened Email metric `LBjRM6`

**Skills copied:**
- `klaviyo-api` (full — MCP tools, campaign creation, flows, segments)
- `klaviyo-email-design` (template HTML patterns)
- `natures-seed-brand` (required for all copy)

**AGENT.md includes:**
- MCP tools listing (20+ tools, always pass `model: "claude"`)
- API revision `2024-07-15` for campaigns (hyphenated/snake_case)
- Template assignment ONLY via MCP tool (not REST API)
- Flow messages cannot be edited via API — UI only
- Active segments (starred only) for campaign targeting
- 10 active flows with performance benchmarks
- 55 campaign drafts (Mar-May 2026) status
- Browse abandonment flow `Xz9k4a` status
- Email design standards (CTA #C96A2E, Inter + Noto Serif Display)
- Reference to existing scripts: `marketing/klaviyo-audit/create_campaigns.py`

**Allowed tools:** `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`

---

### Agent 3: Amazon (`amazon`)

**Mission:** Amazon Selling Partner marketplace — listings, orders, inventory sync.

**Systems:** Amazon SP-API

**Credentials documented:** `AMAZON_*`

**Skills copied:**
- `data-orchestrator` (routing)

**AGENT.md includes:**
- SP-API authentication pattern (from `daily_pull.py`'s `_amz_get_token()`)
- Order pull pattern (from `pull_amazon()`)
- Refresh token flow
- Current status: API access ready, recently integrated into daily pipeline
- SKU system shared with WooCommerce
- Reference to `daily_pull.py` for integration patterns

**Allowed tools:** `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`

---

### Agent 4: Walmart (`walmart`)

**Mission:** Walmart Marketplace — listings, orders, inventory sync, pricing.

**Systems:** Walmart Marketplace API

**Credentials documented:** `WALMART_*`

**Key IDs:** 257 active items

**Skills copied:**
- `walmart-api` (full — OAuth, endpoints, Python client)
- `data-orchestrator` (routing)

**AGENT.md includes:**
- OAuth 2.0 pattern (15-min token expiry, cache required)
- CRITICAL: `WM_SEC.ACCESS_TOKEN` header, NOT `Authorization: Bearer`
- 6 endpoint groups (Items, Inventory, Prices, Orders, Feeds, Reports)
- SKU mapping (same as WooCommerce)
- Walmart 404 = no orders (not an error)
- Current status: 257 items, inventory/price sync built, SEO spreadsheet pending
- Reference to `marketplaces/walmart-optimization/` and `daily_pull.py`

**Allowed tools:** `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`

---

### Agent 5: WooCommerce (`woocommerce`)

**Mission:** Storefront operations — products, orders, customers, SEO, search, content.

**Systems:** WooCommerce REST API, WordPress, Algolia, Cloudflare Worker

**Credentials documented:** `WC_*`, `WP_*`, `CF_WORKER_*`, `ALGOLIA_*`

**Skills copied:**
- `woocommerce-api` (full — 35+ endpoints, product structure, shipping rules)
- `woocommerce-product-creation` (18-step creation checklist)
- `algolia-search` (search config, synonyms)
- `natures-seed-brand` (required for product descriptions)

**AGENT.md includes:**
- CF Worker proxy: route through `CF_WORKER_URL` when set, direct when not
- Bot Fight Mode bypass explanation
- 0.3s rate limit between bulk operations
- Product structure with ACF fields
- Permalink Manager: NEVER use `/product-category/` URLs, always `/products/`
- Variant ordering: smallest-to-largest, default to smallest
- Upsell cross-sell mapping by prefix
- Category tree (9 root + 20 sub, 87 products)
- Shipping rules (free <100lb, $80/25lb 100-300lb, flat $640 >300lb)
- Reference to `store/product-updates/`, `seo/`, `infrastructure/cloudflare-worker/`

**Allowed tools:** `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`

---

### Agent 6: Shippo Shipping (`shippo`)

**Mission:** Shipping operations — label creation, rate comparison, cost tracking, carrier management.

**Systems:** Shippo API, Fishbowl Inventory (read-only for stock context)

**Credentials documented:** `SHIPPO_API_KEY`

**Skills copied:**
- `fishbowl-inventory` (stock levels, delivery times)
- `data-orchestrator` (routing)

**AGENT.md includes:**
- Shippo API has NO date filtering — must paginate all and filter by `object_created`
- Rate cost requires separate `/rates/{id}` call
- Always deduplicate by tracking number (voided/recreated labels)
- Fishbowl HTTP API pattern (login → token → SQL query)
- Delivery time sync pattern (`sync_delivery_time.py`)
- Weight-based shipping validation
- Shipping cost tracking via Supabase `daily_shipping` table
- Reference to `daily_pull.py`'s `pull_shippo()` and `marketplaces/fishbowl/`

**Allowed tools:** `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`

---

## Agent Directory Structure (per agent)

```
~/.party/agents/{slug}/
  agent.json                    — metadata + session_id + cost
  conversations/                — thread storage
  instructions/
    AGENT.md                    — system prompt (THE key file)
  skills/
    {skill-name}.md             — extracted from ClaudeDataAgent/.claude/skills/
  memory/
    conversation_log.md         — agent maintains across sessions
    decisions.md                — standing decisions
    learnings.md                — mistakes and patterns
  data/                         — agent-specific data files
```

Skills are copied as single `.md` files extracted from skill directories — agents have their own copy.

---

## Dependencies

### Python (bridge)
```bash
pip install claude-agent-sdk
```

### Rust (new crates)
- `tokio::process` — already available (tokio full features)
- `serde_json` — already available

No new Rust crate dependencies needed.

---

## What This Spec Does NOT Include

- MCP server integration (agents use Bash to call APIs instead)
- Agent-to-agent communication
- Approval workflow for destructive actions (future)
- Streaming character-by-character rendering (messages arrive as complete chunks)
- Web UI (terminal only)
