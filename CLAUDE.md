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
| Supabase | PostgREST API | `daily-report/` |
| Google Ads | Python client library | `daily-report/daily_pull.py` |
| Google Analytics (GA4) | REST API | Property ID `294622924` |
| Google Merchant Center | Content API | Merchant ID `138935850` |
| Google Search Console | REST API | `sc-domain:naturesseed.com` |
| Shippo | REST API | `daily-report/daily_pull.py` |
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
| `algolia-search` | Product search optimization, synonyms, rules |
| `klaviyo-email-design` | Email template HTML/design for Klaviyo |

## Rules

1. **Always invoke `natures-seed-brand` skill before writing any customer-facing content** — emails, product descriptions, marketing copy, social posts
2. **Use MCP tools when available** instead of raw API calls (Klaviyo, Postman, Gmail, Chrome)
3. **Rate limit WooCommerce calls** — 0.3s between bulk operations
4. **Walmart tokens expire in 15 minutes** — cache and refresh
5. **Fishbowl is the inventory source of truth** — WooCommerce stock data may lag
6. **Use `VLbLXB` as the conversion metric ID** in Klaviyo — it's the WooCommerce "Placed Order" metric
7. **Always pass `model: "claude"` in Klaviyo MCP tool calls**
8. **Supabase new API keys** — `sb_secret_*` keys are opaque tokens, NOT JWTs. Use only `apikey` header, never `Authorization: Bearer`
9. **Supabase upsert** — Requires `on_conflict` query param + `Prefer: resolution=merge-duplicates` header. See `_UPSERT_KEYS` in `daily_pull.py`
10. **Google OAuth multi-scope** — Single refresh token covers Ads, Analytics, Merchant Center, and Search Console. Don't create separate tokens per API
11. **Shippo date filtering** — API doesn't support reliable date params. Must paginate all transactions and filter by `object_created` locally. Rate cost is on separate `/rates/{id}` endpoint
12. **Shippo deduplication** — Always deduplicate by tracking number to handle voided/recreated labels

## Session Handoff

**Read `HANDOFF.md` at the start of any new session.** It captures the full history, completed work, active state, and priority queue from prior sessions.

## Active Work (as of March 9, 2026)

| Project | Directory | Status |
|---------|-----------|--------|
| Daily Report Pipeline | `daily-report/` | ✅ Pipeline built, 2025 backfilled, GitHub Actions scheduled |
| Retool Dashboard | Retool (external) | Pending — connect to Supabase, build MTD/YTD queries |
| Google Ads 4-Year Audit | `google-ads-audit/` | ✅ Complete — scripts 09-13b built, LIVE audit done |
| Texas Collection Feed | `google-ads-audit/texas_collection_feed.csv` | ✅ Complete — 21 rows ready to paste |
| Spring 2026 Recovery | `spring-2026-recovery/` | Sent — follow-up in 2 weeks |
| Walmart Optimization | `walmart-optimization/` | Sync done — SEO spreadsheet needs upload |
| Algolia Optimization | `algolia-optimization/` | Config done — clickAnalytics pending |

## Daily Report System

**GitHub Repo**: `GabeNaturesSeed/nature-seed-data`
**Database**: Supabase (`zoeuacgxthkiemzyunsd.supabase.co`)
**Frontend**: Retool (free tier)
**Schedule**: GitHub Actions cron at midnight MST (7 AM UTC)

### Tables (in Supabase)
| Table | Purpose |
|-------|---------|
| `daily_sales` | Revenue/orders by channel (WC, Walmart) — PK: `report_date, channel` |
| `daily_ad_spend` | Ad spend by channel (Google Ads) — PK: `report_date, channel` |
| `daily_shipping` | Shippo costs — PK: `report_date` |
| `daily_cogs` | Cost of goods by channel — PK: `report_date, channel` |
| `cogs_lookup` | SKU → unit cost from Google Sheet — PK: `sku` |
| `financial_goals` | Monthly revenue targets — PK: `year, month` |

### Views
- `daily_summary` — Aggregated daily P&L with MER
- `mtd_comparison` — Current month vs last year vs goal with YoY % change

### Data Sources
| Source | What | Script |
|--------|------|--------|
| WooCommerce | Orders (completed + processing) | `pull_woocommerce()` |
| Walmart | Marketplace orders | `pull_walmart()` |
| Google Ads | Ad spend, clicks, conversions | `pull_google_ads()` |
| Shippo | Shipping costs (deduplicated) | `pull_shippo()` |
| Google Sheets | COGS lookup table (276 SKUs) | `sync_cogs_from_sheet()` |

### Key IDs
| System | ID |
|--------|----|
| Google Ads Customer | `599-287-9586` (login: `838-619-4588`) |
| GA4 Property | `294622924` |
| Google Merchant Center | `138935850` |
| COGS Google Sheet | `1nve5yRvw7fY0caVqZDHYDjhoQmj_a6S9PkC3BMKm1S4` |

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