# Nature's Seed — Data Orchestrator Agent

This is the central data hub for all Nature's Seed ecommerce operations. Any agent working on Nature's Seed projects should reference this folder for API connections, data schemas, and operational knowledge.

## Purpose

1. **Teach agents** — Skills in `.claude/skills/` provide instant context for every API and database connection
2. **Source of data** — Single place to query any Nature's Seed data across all platforms
3. **Save tokens** — Pre-documented schemas, IDs, and patterns eliminate discovery overhead

## Connected Systems

| System | Connection | Skill |
|--------|-----------|-------|
| WooCommerce (naturesseed.com) | REST API v3 + Store API v1 | `.claude/skills/woocommerce-api/` |
| Klaviyo | MCP Server (20+ tools) | `.claude/skills/klaviyo-api/` |
| Walmart Marketplace | OAuth 2.0 REST API | `.claude/skills/walmart-api/` |
| Fishbowl Inventory | HTTP API | `.claude/skills/fishbowl-inventory/` |
| Gmail | MCP Server | `.claude/skills/gmail-communications/` |
| Postman | MCP Server | Available via MCP tools |
| Chrome Browser | MCP Server | Available via MCP tools |
| Stripe | Via WooCommerce plugin | Documented in WC skill |

## Credentials

All API credentials are in `.env` in this directory. Never hardcode or expose them.

## Skills Directory

| Skill | When to Invoke |
|-------|---------------|
| `data-orchestrator` | **Start here.** Routes you to the right system for any data need |
| `woocommerce-api` | Product, order, customer, shipping, coupon operations |
| `klaviyo-api` | Email marketing, flows, segments, campaigns, customer profiles |
| `walmart-api` | Marketplace listings, orders, inventory, pricing |
| `fishbowl-inventory` | Warehouse stock levels, SKU mapping, delivery times |
| `gmail-communications` | Email search, reading, drafting |
| `natures-seed-brand` | **Required before ANY customer-facing content** — brand voice, colors, copy patterns |

## Rules

1. **Always invoke `natures-seed-brand` skill before writing any customer-facing content** — emails, product descriptions, marketing copy, social posts
2. **Use MCP tools when available** instead of raw API calls (Klaviyo, Postman, Gmail, Chrome)
3. **Rate limit WooCommerce calls** — 0.3s between bulk operations
4. **Walmart tokens expire in 15 minutes** — cache and refresh
5. **Fishbowl is the inventory source of truth** — WooCommerce stock data may lag
6. **Use `VLbLXB` as the conversion metric ID** in Klaviyo — it's the WooCommerce "Placed Order" metric
7. **Always pass `model: "claude"` in Klaviyo MCP tool calls**

## Session Handoff

**Read `HANDOFF.md` at the start of any new session.** It captures the full history, completed work, active state, and priority queue from prior sessions.

## Active Work (as of March 5, 2026)

| Project | Directory | Status |
|---------|-----------|--------|
| Google Ads 4-Year Audit | `google-ads-audit/` | ✅ Complete — scripts 09-13b built, LIVE audit done |
| Texas Collection Feed | `google-ads-audit/texas_collection_feed.csv` | ✅ Complete — 21 rows ready to paste |
| Spring 2026 Recovery | `spring-2026-recovery/` | Sent — follow-up in 2 weeks |
| Walmart Optimization | `walmart-optimization/` | Sync done — SEO spreadsheet needs upload |
| Algolia Optimization | `algolia-optimization/` | Config done — clickAnalytics pending |

## Related Projects

| Project | Path |
|---------|------|
| Next.js Headless Storefront | `~/Desktop/woodmart2:16-ClaudeWork/` |
| Data Integration Scripts | `~/Desktop/ClaudeProjectsLocal/` |
| Email Audit & Templates | `~/Desktop/ClaudeProjectsLocal/natures-seed-email-audit/` |
| Inventory Forecasting | `~/Desktop/CascadeProjects/Naturesseed inventory helper/` |

## Workflow Orchestration

### 1. Plan mode default
- Enter plan mode for ANY non-trivial task (3_step or architectural descisions)
- If something goes sidewasys, STOP and re-plan immediately, don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailsd specs upfront for reduce ambiguity

### 2. Subagent strategy
- Use subagents liberally to keep main context window clean
- Offload research , exploration, and parallel analysis to subagents
- For complex problems, throw more comute at it via subagents
- One track per subagent for focused execution

### 3. Self-improvement Loop
- After ANY correction from the user, update 'task/lessons.md' with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthless iterate on these lessons until mistake rates drops
-Review lessons at session start for relevant project

#### 4. Verification before Done
- Never mark a task complete without proving it works 
- Diff behavior between main and tour changes when relevant
- ASk yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrante correctness

### 5. Demand Elagance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegnt way?"
- If a fix feels hacky: "Knowing everything i know now, implement the elgang solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous bug fizing
- When given a bug report: just fix it. Don't ask for hand-holding
- point at logs, errors, failing tests -then resolve them
- Zero context switching required from the user
- Go fix failin CI tests without being told how

### Task Management

1. **Plan first**: Weite plan to:'tasks/todo.md' with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track progress**: Mark items complete as you go
4. **Explain changes**: High level-summary at each step
5. **Document Results**: Add review section to 'tasks/todo.md'
6. **Capture Lessons**: Update 'tasks/lessons.md' after corrections

### Core Principles

- **Simplicity First**: Make every change as simple as possible, Impcat minimal code.
- **No Laziness**: Find root cause, No temporary fixes, Senior developer Standards. 
- **Minimal Impact**: Changes should only touch what is necessary, avoid introducing bugs.