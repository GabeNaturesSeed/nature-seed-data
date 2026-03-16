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
| Cloudflare Worker (WC Proxy) | `wc-api-proxy.skylar-d51.workers.dev` | `infrastructure/cloudflare-worker/wc-proxy.js` |
| Klaviyo | MCP Server (20+ tools) | `.claude/skills/klaviyo-api/` |
| Walmart Marketplace | OAuth 2.0 REST API | `.claude/skills/walmart-api/` |
| Fishbowl Inventory | HTTP API | `.claude/skills/fishbowl-inventory/` |
| Gmail | MCP Server | `.claude/skills/gmail-communications/` |
| Supabase | PostgREST API | `infrastructure/daily-report/` |
| Google Ads | Python client library | `infrastructure/daily-report/daily_pull.py` |
| Google Analytics (GA4) | REST API | Property ID `294622924` |
| Google Merchant Center | Content API | Merchant ID `138935850` |
| Google Search Console | REST API | `sc-domain:naturesseed.com` |
| Shippo | REST API | `infrastructure/daily-report/daily_pull.py` |
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
| `woocommerce-product-creation` | **Use when creating product pages via API** — full order of operations, ACF fields, variation gotchas |

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
13. **Cloudflare Bot Fight Mode** — Blocks all datacenter IPs (GitHub Actions, AWS, etc.) from calling WC API. Cannot be bypassed with WAF rules on free plan. Solution: route WC API calls through Cloudflare Worker proxy (`infrastructure/cloudflare-worker/wc-proxy.js`). Set `CF_WORKER_URL` and `CF_WORKER_SECRET` env vars to enable proxy mode. CFO does NOT allow disabling Bot Fight Mode.
14. **GitHub Actions secrets** — Must be added as **Repository secrets** (not Environment secrets). Verify they appear under Settings → Secrets and variables → Actions → Repository secrets.
15. **WooCommerce variant ordering** — Always list Size attribute options smallest-to-largest in the parent product's `attributes[].options` array. Set `default_attributes` to the smallest variant. This controls frontend dropdown order AND is required for bulk discount labels to work correctly.
16. **Klaviyo segments — starred only** — Only use **starred** segments for campaign targeting. These are documented in `.claude/skills/klaviyo-api/SKILL.md` under "Active Segments (Starred — Use These)". Never create campaigns targeting non-starred segments.
17. **Klaviyo API revision `2024-07-15`** — Use this revision for campaign creation. It uses hyphenated/snake_case (`campaign-messages`, `send_strategy`, `options_static`). Template assignment only works via MCP tool `klaviyo_assign_template_to_campaign_message`.
18. **Google Ads `shopping_performance_view` with `segments.date`** — Must include `campaign.id` in SELECT clause when filtering by `campaign.id` in WHERE. API errors otherwise.
19. **WC order attribution metadata** — GCLID and campaign ID are in `_wc_order_attribution_session_entry` URL query params. Parse with `urllib.parse`. PMax sub-campaign IDs in click URLs won't match API campaign list — group with parent PMax campaigns.
20. **`.env` has spaces around `=` AND quotes around values** — Cannot `source .env`. Parse manually: `line.split('=', 1)` then `.strip().strip("'\"")` on both key and value. Skipping the quote-strip causes 401 API errors.
21. **Klaviyo flow messages — no API editing** — Cannot update flow message subject lines, content, or assign templates to flow messages via REST API or MCP. Campaign messages support template assignment via MCP tool; flow messages do not. Flow changes require the UI at `klaviyo.com/flow/{id}/edit`.
22. **WC variation IDs return `parent_id` only** — `/products/{variation_id}` returns `type: "variation"` with a `parent_id` field and minimal data. Must call `/products/{parent_id}` to get `description`, `short_description`, ACF `meta_data`, categories, and attributes.
23. **ACF `price_discount_2`** — Controls the discount badge on the mid-tier variation in the PDP variation selector. Standard value: `"10% Off - MOST PICKED"`. Uses GET-then-PUT meta pattern (must include existing meta ID). Bulk-updated on all 99 products in March 2026.
24. **WooCommerce `upsell_ids`** — Set via `{"upsell_ids": [id1, id2, id3]}` on parent product PUT. Cross-sell map by prefix: TURF-→S-MICRO+S-DUTCH+SUSTANE; PB-→S-INNOC; WB-→companion wildflower species; clover-→S-INNOC. See `store/product-updates/update_acf_bulk_and_upsells.py` for full implementation.
25. **Permalink Manager — NEVER use `/product-category/` URLs** — Site uses Permalink Manager plugin. All category URLs are under `/products/`, NOT `/product-category/`. Using default WC paths causes Google Ads DESTINATION_NOT_WORKING disapprovals. Always verify URLs against the sitemap (`product_cat-sitemap.xml`) or `requests.head(url, allow_redirects=True)`. Key mappings: Lawn→`/products/grass-seed/`, Pasture→`/products/pasture-seed/`, Wildflower→`/products/wildflower-seed/`, California→`/products/california-seeds/`, Texas→`/products/texas-collection/`, Clover→`/products/clover-seed/`, Food Plot→`/products/food-plot-seed/`, Cover Crop→`/products/cover-crop-seed/`, Drought→`/products/drought-tolerant-pasture-seed/`, Horse→`/products/pasture-seed/horse-pastures-seed/`.

## Repository Structure

```
ClaudeDataAgent/
├── infrastructure/          # Core data plumbing
│   ├── daily-report/        # Daily P&L pipeline (Supabase + GitHub Actions)
│   ├── cloudflare-worker/   # WC API proxy (bypasses Bot Fight Mode)
│   └── dashboard/           # Retool dashboard data generation
├── seo/                     # Search engine optimization
│   ├── search-console/      # GSC data, crawl budget cleanup, product cards
│   ├── is-increase/         # Impression share, category descriptions, FAQ schema
│   ├── algolia-optimization/# Search config, synonyms, rules
│   └── merchant-center-audit/# Google Merchant Center audit
├── marketing/               # Campaigns & advertising
│   ├── klaviyo-audit/       # 55 campaign drafts, templates, create_campaigns.py
│   ├── google-ads-audit/    # 4-year audit, drip automation, attribution
│   └── spring-2026-recovery/# Email recovery campaign
├── store/                   # WooCommerce & product operations
│   ├── product-updates/     # ACF bulk updates, descriptions, slugs, upsells
│   ├── woo-cogs/            # COGS tracking
│   ├── woo-theme-handoff/   # Theme editor handoff docs
│   ├── planting-aid-enrichment/
│   └── wildflower-catalog/
├── marketplaces/            # External sales channels
│   ├── marketplace-management/ # Walmart/Amazon bot (cron disabled)
│   ├── walmart-optimization/   # Inventory sync + SEO
│   └── fishbowl/            # Inventory source of truth
├── reports/                 # HTML reports + generator scripts
├── research/                # One-off research & analysis
│   ├── fava-bean-research/
│   ├── abc-analysis/
│   └── 2026-budget/
├── tasks/                   # Todo lists, lessons learned
├── docs/                    # Dashboard data JSONs
├── .claude/skills/          # Agent skills (API docs, brand guide)
└── .github/workflows/       # CI/CD (daily pull, nightly review, etc.)
```

## Session Handoff

**Read `HANDOFF.md` at the start of any new session.** It captures the full history, completed work, active state, and priority queue from prior sessions.

## Active Work (as of March 16, 2026)

| Project | Directory | Status |
|---------|-----------|--------|
| Daily Report Pipeline | `infrastructure/daily-report/` | ✅ Pipeline built, CF Worker proxy deployed, GitHub Actions working |
| Nightly Sales Review | `infrastructure/daily-report/nightly_review.py` | ✅ Telegram bot sends daily summary at 10 PM MST |
| Cloudflare Worker Proxy | `infrastructure/cloudflare-worker/` | ✅ Deployed — bypasses Bot Fight Mode for WC API |
| Google Ads Drip Automation | `marketing/google-ads-audit/drip/` | ⏸️ Cron disabled 2026-03-16 — manual trigger only |
| Weekly Attribution Report | `marketing/google-ads-audit/drip/weekly_attribution_report.py` | ✅ Built — every Sunday, GCLID cross-ref, budget recs |
| Product Card Injection | `seo/search-console/` | ✅ 38 of 48 articles updated with product cards |
| Retool Dashboard | Retool (external) | Pending — connect to Supabase, build MTD/YTD queries |
| Google Ads 4-Year Audit | `marketing/google-ads-audit/` | ✅ Complete — scripts 09-13b built, LIVE audit done |
| Shopping Bottom-20 Fix | `marketing/google-ads-audit/` | ✅ Content + stock updated for all 17 parent products |
| Klaviyo Campaign Drafts | `marketing/klaviyo-audit/` | ✅ Complete — 55 campaigns created for Mar–May 2026 |
| Browse Abandonment Flow | Klaviyo `Xz9k4a` | ✅ 3 new templates created — UI actions needed to assign |
| Shopper Approved → GMC | External dashboards | Pending — manual steps in SA + GMC dashboards |
| Fava Bean Market Research | `research/fava-bean-research/` | In progress — CFO PDF report |
| Texas Collection Feed | `marketing/google-ads-audit/texas_collection_feed.csv` | ✅ Complete — 21 rows ready to paste |
| Spring 2026 Recovery | `marketing/spring-2026-recovery/` | Sent — follow-up in 2 weeks |
| Walmart Optimization | `marketplaces/walmart-optimization/` | Sync done — SEO spreadsheet needs upload |
| Algolia Optimization | `seo/algolia-optimization/` | Config done — clickAnalytics pending |
| IS Increase (Impression Share) | `seo/is-increase/` | ✅ RSAs, extensions, drought category, keyword URLs done. Manual: RankMath SEO, permalink, horse UX |
| Keyword Coverage Expansion | `seo/is-increase/` | ✅ Phase 1+2 implemented (8 new ad groups). Phase 3 needs landing pages |
| Marketplace Bot | `marketplaces/marketplace-management/` | ⏸️ Cron disabled 2026-03-16 — manual trigger only |
| Crawl Budget Cleanup | `seo/search-console/` | ✅ Deliverables ready — theme code pending |

## Daily Report System

**GitHub Repo**: `GabeNaturesSeed/nature-seed-data`
**Database**: Supabase (`zoeuacgxthkiemzyunsd.supabase.co`)
**Frontend**: Retool (free tier)
**Schedule**: GitHub Actions cron at midnight MST (7 AM UTC)
**WC API Proxy**: Cloudflare Worker at `wc-api-proxy.skylar-d51.workers.dev` (bypasses Bot Fight Mode)

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

### 7. Skills-First Execution (MANDATORY)
- **Before starting ANY task**, ask: "Are there skills in `.claude/skills/` that can accomplish this?"
- If a skill exists that covers the task, **invoke it 100% of the time** — no exceptions
- Skills contain pre-documented patterns, schemas, IDs, and API details that eliminate discovery overhead
- Building on skills prevents repeated mistakes and ensures consistency across sessions
- **After completing a task that required new patterns/knowledge**, consider whether a new skill should be created or an existing skill should be updated
- The goal is continuous improvement: every session should leave skills better than it found them
- Skills are living documents — update them when APIs change, new patterns emerge, or better approaches are discovered
- Reference the Skills Directory table in this file to match tasks to skills

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