# Nature's Seed — Session Handoff (April 17, 2026)

> Read this at the start of any new session to pick up where we left off.

---

## 🔥 ACTIVE IN-FLIGHT — Klaviyo Strategy Framework Rollout (Plan 1 Execution)

**Session goal:** Execute Plan 1 of the Klaviyo Strategy & Measurement Framework — ships the operational scaffolding (Python helpers) + first Monday review file + Phase 0 Winback flow fix proposals for Gabe's approval.

### What already shipped (this session, 2026-04-17)

| Deliverable | Path | Commit |
|---|---|---|
| Strategy design spec | `docs/superpowers/specs/2026-04-17-klaviyo-strategy-design.md` | `d9a74eb` |
| Plan 1 implementation plan | `docs/superpowers/plans/2026-04-17-klaviyo-framework-foundation.md` | `c165a5b` |
| Roadmap memory (4-plan decomposition) | `~/.claude/projects/.../memory/project_klaviyo_strategy_roadmap.md` | N/A |
| Seasonal-cadence rule memory | `~/.claude/projects/.../memory/feedback_klaviyo_seasonal_cadence.md` | N/A |
| Seasonality-calendar future-project memory | `~/.claude/projects/.../memory/project_seasonality_calendar.md` | N/A |

### Strategic decisions locked in the spec (do NOT re-decide in execution)

- Primary goal = **Retention / LTV** — Replant Moment (Warm RFM `WdpJti`) is #1 cohort
- Quick win before main lever = **Fix Winback flow `VvvqpW`** (0.13% conversion → D grade)
- Ops model = **Hybrid D** — autonomous on flows, approval-gated on broadcasts
- Cadence = **RFM-tiered × seasonal mode**; Spring 2026 starts conservative, aggressive mode gated by 4 deliverability gates (net list growth ≥0, spam <0.1%, bounce <1%, unsub <0.3%)
- Offer philosophy = **Targeted + seasonal-dynamic, 15% max discount cap**, `$` off preferred over `%`
- North Star (agent steering) = **Flow revenue % of email revenue** (current 8% → 20-25% target)
- Secondary (acquisition flows) = Email-attributed RPR for Cart/Browse/Checkout recovery
- Review cadence = **Weekly file drops + monthly strategic review** (no Telegram — files in `marketing/klaviyo-audit/reviews/`)

### What Plan 1 will produce (when executed)

- 4 Python modules at `marketing/klaviyo-audit/framework/`: `klaviyo_client.py`, `deliverability_gates.py`, `kpi_calculator.py`, `review_generator.py`
- 19 passing unit tests at `tests/klaviyo-framework/`
- CLI at `scripts/generate_weekly_review.py`
- First Monday review file at `marketing/klaviyo-audit/reviews/weekly/2026-04-20-weekly-review.md`
- 4 Winback email proposals (Email 2 rewrite + Emails 3, 4, 5 new) at `marketing/klaviyo-audit/winback-fix/`
- Suppression rules doc with per-flow manual-UI checklist at `marketing/klaviyo-audit/suppression-rules.md`

### Manual Gabe-only steps deferred to AFTER Plan 1 execution

1. **Review + approve Winback email proposals** in the generated 2026-04-20 weekly review file
2. **Update flow filter rules in Klaviyo UI** per `suppression-rules.md` checklist (flow-filter edits are NOT supported via REST API — per CLAUDE.md rule 21)
3. Approve the agenda for Phase 1 work (Seasonal Reorder flow build)

### Plan 2 (scoped for next cycle, after Plan 1 approval + deployment)

- Seasonal Reorder flow build (category × season)
- Welcome Series activation (`WQBF89` draft)
- Cadence cap checker module
- Campaign proposal generator (6-step decision tree)
- Alert-file writer
- Monthly review generator
- Supabase integration for `total_wc_revenue` in reviews
- Metric aggregates for real deliverability gate values

### Critical context for the executing session

- `.env` at repo root has `KLAVIYO_API` (private key, prefix `pk_3e5ea...`). Parse with `line.split("=", 1)` then `.strip().strip("'\"")` — NOT `source .env` (CLAUDE.md rule 20).
- Klaviyo REST API revision = `2024-07-15` (CLAUDE.md rule 17)
- Conversion metric ID = `VLbLXB` (WooCommerce Placed Order)
- **Do NOT use MCP tools for the Python scripts** — MCP is Claude-Code-only; Plan 1 scripts must run in CI/cron eventually so use REST API directly
- Winback template UPLOAD to Klaviyo is NOT in Plan 1 — proposals stay as markdown pending Gabe's approval

### How to resume (first prompt for the next conversation below)

See the "First Prompt for New Conversation" block at the very end of this file.

---

## 📦 PREVIOUS IN-FLIGHT — DTC Section Overhaul

**Session goal (three parts, user prompt verbatim):**
> 1. Add tooltips on the whole reporting section to all pages that explain what the numbers are, how we're doing the math, and where we're pulling each number from.
> 2. Change the name of the section from "Reporting" to "DTC".
> 3. Go through all pages in the section to make sure we are not pulling anything from marketplaces (Amazon/Walmart), only WooCommerce. Mark the WC-Only project as done if confirmed.

### Progress snapshot

| Step | Status | Notes |
|------|--------|-------|
| 1. Sidebar rename Reporting → DTC | ✅ Done | `dashboard/src/components/layout/Sidebar.tsx` — label on parent item |
| 2. Backend WC-only audit in `generate_data.py` | ✅ Done | Added `_sum_channel()` helper; MTD orders/cogs now come from `daily_sales` / `daily_cogs` filtered `channel='woocommerce'`. `daily_cy`/`daily_ly` chart rows now use `wc_revenue` (fall-back derives from total − amazon − walmart). Gross profit / CM1 / CM2 recomputed from WC-only revenue + cogs. |
| 3. Remove "Channel Breakdown" section from `/reporting` (MTD page) | ⬜ **Not done** | MTD page still renders `WooCommerce / Amazon / Walmart Revenue` KPIs at bottom. User wants DTC pages to show zero marketplace numbers. File: `dashboard/src/app/reporting/page.tsx` lines ~277–295. |
| 4. Build `InfoTooltip` component | ✅ Done | `dashboard/src/components/InfoTooltip.tsx` — uses Heroui `Tooltip` + Lucide `Info` icon. |
| 5. Extend `KpiCard` with `tooltip?: ReactNode` prop | ✅ Done | Renders a small info "i" next to the KPI label. |
| 6. Extend `ChartCard` with `tooltip?: ReactNode` prop | ⬜ **Not done** | Edit attempted but failed (file wasn't re-read after another edit). Need to apply the same pattern used in KpiCard. |
| 7. Wire tooltips on every KPI and chart in MTD/YTD/P&L/CM/Notes | ⬜ **Not done** | No page has had tooltip props added yet. Each KpiCard and ChartCard needs a `tooltip={...}` prop explaining the number, the math, and the source. |
| 8. Mark "MTD/YTD/P&L — WooCommerce Only" project as Done in the Party projects file | ⬜ **Not done** | File: `/Users/gabegimenes-silva/.party/agents/github-pages/data/projects.json`. Project id `c3d4e5f6-7890-12cd-efab-34567890abcd`. Status should flip from "Active" to "Done" once step 3 above ships and CI run succeeds with the WC-only backend code. |
| 9. Build + commit + push | ⬜ **Not done** | Nothing is staged yet for this session's work. |

### Files modified (uncommitted)

```
M  dashboard/src/components/layout/Sidebar.tsx           (Reporting → DTC)
M  dashboard/src/components/kpi/KpiCard.tsx              (tooltip prop)
?? dashboard/src/components/InfoTooltip.tsx              (new)
M  infrastructure/dashboard/generate_data.py             (WC-only overrides + daily_cy/ly)
```

### Critical context for next session

**1. How the WC-only backend fix works (what's already live in the file):**

Inside `generate_reporting()` after `cy_totals = sum_rows(cy_rows)`:
- New helper `_sum_channel(table, start, end, channel, value_col)` queries Supabase with `channel=eq.woocommerce` and returns the sum of a numeric column.
- Four calls: MTD orders, MTD cogs, LY orders, LY cogs — all `channel='woocommerce'`.
- Results overwrite `cy_totals["orders"] / ["cogs"]` and `ly_totals` equivalents.
- `gross_profit`, `gross_margin_pct`, `cm1`, `cm2`, `cm2_pct` are **recomputed from WC-only revenue + cogs** for both `cy_totals` and `ly_totals`.
- `daily_cy` / `daily_ly` list comprehensions now call a new local `_wc_rev(row)` that prefers `wc_revenue`, falling back to `total_revenue − amazon_revenue − walmart_revenue`.

**Assumptions documented in the code:**
- `shipping_cost` (daily_summary) = Shippo = ~100% WC (marketplaces handle their own shipping).
- `total_ad_spend` = Google Ads = WC (marketplaces have their own ad platforms).
- `platform_fees` = Stripe processing on WC orders.
- `daily_shipping` table has no channel column.

**2. Tooltip content plan — what each page needs:**

Every number should answer three questions in the tooltip:
- **What it is** — one short sentence definition.
- **How it's calculated** — the formula, if derived.
- **Where it comes from** — the specific Supabase view/table or file, with the critical filters (e.g., `daily_sales.orders where channel='woocommerce'`).

Example (MTD Revenue KPI):
> Month-to-date WooCommerce revenue. Sum of `daily_summary.wc_revenue` from the 1st of the current month through yesterday. DTC only — excludes Amazon and Walmart.

A **data source registry** module would be cleaner than inline strings. Suggested layout: `dashboard/src/lib/sources.ts` exporting `{ mtdRevenue, mtdCogs, mtdCM2, ... }` objects with `{ description, formula, source }` so tooltips stay consistent across pages.

**3. Pages still to instrument (file paths):**
- `dashboard/src/app/reporting/page.tsx` — MTD (KpiCards × ~15 + ChartCards × 4). Also remove Channel Breakdown section here.
- `dashboard/src/app/reporting/ytd/page.tsx` — YTD Summary (KpiCards × 7 + 1 ChartCard + inline table headers).
- `dashboard/src/app/reporting/pnl/page.tsx` — P&L page shell (table already has native-title tooltips from the prior session; consider upgrading headers).
- `dashboard/src/app/reporting/cm/page.tsx` — CM Waterfall (table + chart).
- `dashboard/src/app/reporting/notes/page.tsx` — mostly static content, probably no tooltips needed.

**Pattern reminder (already in `PnlTable.tsx`):** Table cells use native HTML `title` attribute for source strings — that pattern is fine to keep for dense tables. For KPI cards and chart titles, use the new `tooltip` prop (Heroui Tooltip).

### The "stop before marking WC-Only project done"

Don't flip the project to "Done" in `projects.json` until:
1. Channel Breakdown section is removed from `/reporting`.
2. A fresh CI run completes successfully (current workflow failures are `customer-data` + `abc-report` — unrelated to DTC code path — but verify `dashboard-data` job is green after pushing the backend change).
3. User eyeballs the live DTC pages and confirms no Amazon/Walmart number appears anywhere.

---

## Project Status Overview

| # | Project | Directory | Status |
|---|---------|-----------|--------|
| 1 | Daily Report Pipeline | `infrastructure/daily-report/` | Running (daily + nightly cron) |
| 2 | Nightly Sales Review | `infrastructure/daily-report/nightly_review.py` | Running (10 PM MST Telegram) |
| 3 | Google Ads Drip | `marketing/google-ads-audit/drip/` | ⏸️ Cron disabled — manual desktop only |
| 4 | Walmart Optimization | `marketplaces/walmart-optimization/` | Spreadsheet regenerated, needs upload |
| 5 | WC ↔ Walmart Sync | — | Not built yet |
| 6 | Shopper Approved → Klaviyo | — | ⚠️ SA→Klaviyo integration disconnected since Aug 2025. Gabe reconnecting in SA dashboard. |
| 7 | **Amazon Store Launch** | `Amazonimprovement/` | 🔥 **TOP PRIORITY** — full catalog expansion + listing optimization + ads + data pipeline |
| 7a | **Amazon Ads Review & Optimization** | `Amazonimprovement/ads/` | 🔥 **URGENT** — audit existing PPC, optimize ACoS, expand campaigns (needs Ads API access) |
| 16 | **Influencer Media Kit Page** | `marketing/influencer-media-kit/` | 🆕 Content hub to attract influencer partnerships (product collabs + content sponsorships) |
| 17 | **Reddit Ads Catalog** | `marketing/reddit-ads/` | 🆕 Daily Google-Shopping-spec TSV of in-stock WC products (variation-level), served via GitHub Pages for Reddit Ads Manager catalog ingestion. See [marketing/reddit-ads/README.md](marketing/reddit-ads/README.md). |
| 8 | Dashboard (Next.js) | `dashboard/` | Live — menu renamed Inventory→Operations. Fishbowl API blocked from GH Actions (see below) |
| 9 | Crawl Budget Cleanup | `seo/search-console/` | Theme code + GSC submissions pending |
| 10 | Google Ads Audit | `marketing/google-ads-audit/` | Done — Tier 2-4 items remain |
| 11 | Keyword Expansion | `seo/is-increase/` | Phase 1-3 done, manual SEO tasks remain |
| 12 | Menards Wholesale | `Amazonimprovement/` | ✅ 77-SKU catalog with validated delivered pricing ready to submit |
| 13 | Shipment Tracking Flow | `infrastructure/cloudflare-worker/wc-proxy.js` | ✅ Fixed: tracking URLs now auto-generated, shipping address added to event |
| 14 | Review Request System | Klaviyo | ✅ Templates created (`WDeFiX` verified, `Tdpr6T` generic). Campaign draft ready. Flow needs UI setup. |
| 15 | Dashboard Commentary | `docs/notes.md` | ✅ Updated March 30 — simplified attribution, Zeck-ready format |

**Fully Completed (archived):** Google API Connections, Texas Collection Feed, Spring 2026 Recovery, Klaviyo 55 Campaign Drafts, Shopping Bottom-20 Fixes, Browse Abandonment Flow, Algolia Optimization, Marketplace Bot (cron disabled)

---

## Session Work (March 30, 2026)

### Menards Wholesale Catalog
- Menards buyer reached out for product submission (Grass Seed, Wildflower, Fertilizer categories)
- Built 77-SKU wholesale catalog with real Shippo freight quotes (UPS Ground, Lehi UT → Eau Claire WI)
- **All 50-lb items removed** — UPS Additional Handling surcharge ($77.41/unit) makes them unprofitable via parcel. Only viable with LTL pallet freight.
- Files: `Amazonimprovement/menards_catalog_FINAL.csv` (external), `menards_internal_v3.csv` (with margins)
- Script: `Amazonimprovement/build_menards_catalog_v3.py`
- **Next:** Gabe to sign Defect Agreement + Terms Checklist, submit catalog with email response

### Shipment Tracking Flow (CF Worker Fix)
- **Problem 1:** `TrackingLink` was empty on 100% of "Order Shipped" events — `custom_tracking_link` field only populated for manual entries, not standard carriers
- **Fix:** Added `buildTrackingUrl()` function that maps carrier name → tracking URL (UPS, USPS, FedEx, DHL + Google fallback)
- **Problem 2:** Email showed billing address instead of shipping address — event only sent `CustomerFirstName` from billing
- **Fix:** Added full `Shipping*` fields to event properties (FirstName, LastName, Address1, Address2, City, State, Postcode, Country)
- **Next:** Deploy updated `wc-proxy.js` to Cloudflare. Update Klaviyo email template in UI to use `{{ event.ShippingCity }}` etc. and `{{ event.TrackingLink }}` for button URL

### Review Request System (Klaviyo + Shopper Approved)
- **Finding:** SA→Klaviyo integration stopped sending events in August 2025. Last "Eligible for Shopper Approved Review" event: Aug 20, 2025.
- **Finding:** Each SA event includes `survey_link` — a unique HMAC-authenticated URL per customer/order for verified product reviews
- **Created:** Template `WDeFiX` — verified purchase review request using `{{ event.survey_link }}` and `{{ event.products }}`. Correct logo.
- **Created:** Template `Tdpr6T` — generic review request (for backfill campaign, no verified link)
- **Created:** Campaign `01KMZXHRTAMZ9B9BRRHT6AH2KT` — backfill for Active Customer This Season segment, Smart Send April 1
- **Next:** Gabe reconnecting SA→Klaviyo in SA dashboard. Build Klaviyo flow: trigger on "Eligible for SA Review" metric (`VcUYec`), email using template `WDeFiX`. Contact SA support to bulk-trigger eligibility for 2026 orders.

### Dashboard Updates
- Renamed sidebar "Inventory" → "Operations" in `Sidebar.tsx`
- Updated `docs/notes.md` — simplified attribution analysis, restructured as Zeck board commentary
- **Bug found:** Inventory data shows 0s on GitHub Pages because Fishbowl API (`naturesseed.myfishbowl.com:3875`) returns 400 from GitHub Actions IPs. Same datacenter IP blocking pattern as WooCommerce Bot Fight Mode.
- **Fix needed:** Either route Fishbowl through CF Worker proxy, or upload local `inventory.json` manually, or whitelist GH Actions IPs in Fishbowl

### Klaviyo Email Skill Update
- Updated logo URL in `.claude/skills/klaviyo-email-design/SKILL.md` — old `52272625` → correct `be2fed9c`

---

## Active Infrastructure

### Daily Report Pipeline
- **Cron**: GitHub Actions at midnight MST (7 AM UTC)
- **Sources**: WooCommerce, Walmart, Google Ads, Shippo, COGS Google Sheet
- **Database**: Supabase (`zoeuacgxthkiemzyunsd.supabase.co`) — 6 tables + 2 views
- **WC Proxy**: Cloudflare Worker at `wc-api-proxy.skylar-d51.workers.dev` (bypasses Bot Fight Mode)
- **Key files**: `daily_pull.py`, `nightly_review.py`, `supabase_schema.sql`

**Remaining**:
- Connect Retool to Supabase (host: `db.zoeuacgxthkiemzyunsd.supabase.co`, port 6543)
- Build Retool dashboard with MTD/YTD comparison queries
- Populate `financial_goals` table
- Add Amazon channel (API access now available)

---

## Pending Work

### Influencer Media Kit Page — 🆕
**Directory**: `marketing/influencer-media-kit/` (to be created)
**Goal**: Build a content-rich landing page that attracts influencers to partner with Nature's Seed.

**Partnership Models**:
1. **Product Collabs** (like Jimmy Lewis partnership) — co-branded/signature product lines, rev share or royalty
2. **Content Sponsorships** — supply free product in exchange for content (video, social, reviews)
3. **Affiliate / Ambassador** — ongoing commission-based partnership with custom discount codes

**Page Sections to Build**:
- Brand story + mission (use `natures-seed-brand` skill for voice)
- Audience & reach stats (SEO traffic, email list size, social followers)
- Featured partnership case study (Jimmy Lewis — pull into narrative)
- Product catalog samples — what we can supply (hunting, homesteading, landscaping, wildflower categories)
- Partnership tiers/options (product collab vs content vs ambassador)
- Application form → routes to Klaviyo list or dedicated inbox
- Contact + turnaround expectations

**Target Influencer Segments**:
- Hunting/outdoor YouTubers (food plots, deer habitat)
- Homesteading creators (pasture mixes, cover crops, chickens)
- Landscaping/lawn care (turf seed, drought-tolerant)
- Wildflower/pollinator garden creators
- Ranch/livestock creators (horse, cattle, sheep pasture)

**Tech**:
- Likely lives on `naturesseed.com` as WordPress page or custom headless route
- Could also build in Next.js dashboard under new `/partners` route
- Needs a dedicated application form (Klaviyo form, Typeform, or custom)
- Requires media kit PDF download (brand assets, stats one-pager)

**Next**: Brainstorm page structure + copy (invoke `superpowers:brainstorming` skill) before building.

---

### Walmart Optimization
**Directory**: `marketplaces/walmart-optimization/`
- Inventory sync: 182/182 items synced from Fishbowl
- SEO spreadsheet: **Regenerated March 16** — 180 items (2 Rice Hull SKUs excluded, need separate template upload)
- **Next**: Upload `data/walmart_seo_upload.xlsx` to Seller Center

### WC ↔ Walmart Sync (Not Built Yet)
- **Price sync**: WC prices → Walmart (ongoing automated)
- **Stock sync**: Fishbowl → WC `delivery_time` ACF field for extended lead times; keep Walmart listings active
- Goal: prevent canceled orders from stock mismatches

### Shopper Approved → Google Merchant Center
- **Finding**: Shopper Approved is an official Google Product Reviews Partner with built-in syndication
- **Action**: Check SA dashboard → Google Shopping settings → verify syndication is active
- Needs 50+ product reviews for stars to appear (4-6 week initial syndication)
- **Fallback**: SA has a REST API (`api.shopperapproved.com/products/reviews/{siteId}?token={token}`) — can build custom XML feed if built-in syndication isn't working

### Amazon Store Launch — 🔥 TOP PRIORITY
**Directory**: `Amazonimprovement/`
**Goal**: Grow Amazon from $25K/mo → $50K/mo (6 months) → $80-100K/mo (12 months)

**Current State (as of March 2026)**:
- 28 ASINs live, 91 WooCommerce products NOT on Amazon (23.5% catalog coverage)
- March projected: ~$25K revenue, 284 orders, $51 AOV
- FBM fulfillment, account health green (0% defect/late/cancel)
- No Amazon Advertising running yet
- SP-API access configured in `.env`
- Growth playbook: `Amazonimprovement/amazon-growth-playbook.md`
- State of Amazon report: `Amazonimprovement/stateofamazon-MAR2026.md`

**Launch Workstreams**:
1. **Catalog Expansion** — List remaining 91 products via SP-API (cross-ref WC catalog)
2. **Listing Optimization** — Titles, bullets, descriptions, A+ Content for top 28 ASINs
3. **Pricing Audit** — Kill/reprice negative-margin ASINs (PB-CHIX, PB-ALPACA losing money)
4. **Amazon Advertising** — Launch Sponsored Products on top 30 ASINs (target 25% ACoS)
5. **Data Pipeline** — Add `pull_amazon()` to `daily_pull.py`, Amazon channel in Supabase `daily_sales`
6. **Inventory Sync** — Fishbowl stock → Amazon inventory levels via SP-API

**Existing Scripts**:
- `pull_amazon_catalog.py` — Pulls current Amazon catalog
- `pull_amazon_report.py` — Pulls Amazon sales reports
- `amazon_wc_crossref.py` — Cross-references WC ↔ Amazon catalogs
- `amazon_content_enrichment.csv` — Content improvement opportunities
- `amazon_missing_products.csv` — Products not yet on Amazon

### Amazon Ads Review & Optimization — 🔥 URGENT
**Directory**: `Amazonimprovement/ads/` (to be created)
**Goal**: Audit current ad spend, improve targeting, expand to top 30 ASINs at <25% ACoS

**API Access Status**:
- ✅ **SP-API** (Selling Partner API) — we have credentials for Orders, Catalog, Listings, Inventory, Pricing
- ❌ **Advertising API** — NOT yet configured. Separate app registration + refresh token required
- **Scopes needed**: `advertising::campaign_management`, `advertising::account_management`
- **Required IDs**: Amazon Ads `profile_id` (different from Seller Central merchant ID)

**Ads API Capabilities (once configured)**:
- Create/pause/update Sponsored Products, Sponsored Brands, Sponsored Display campaigns
- Manage ad groups, keywords, targeting (auto/manual/product/category)
- Pull performance reports (clicks, spend, ACoS, ROAS, attributed sales)
- Bid management (manual + automated bidding strategies)
- Negative keyword management
- Budget allocation across campaigns
- Search term reports (for keyword harvesting)

**Launch Steps**:
1. Register Amazon Ads API app at `advertising.amazon.com/API` → get new LWA client + advertising refresh token
2. Pull existing campaigns (if any) via `GET /v2/sp/campaigns`
3. Audit current performance — identify wasteful spend, low-ACoS winners
4. Build Python client in `Amazonimprovement/ads/` (add to `pull_amazon_report.py` pattern)
5. Launch/optimize auto campaigns on top 28 ASINs
6. Harvest converting keywords → manual exact-match campaigns
7. Weekly reporting into Supabase `daily_ad_spend` table (new channel: `amazon_ads`)

### Crawl Budget Cleanup (March 16, 2026)
**Directory**: `seo/search-console/`
- 301 redirect CSV verified — 54/55 already redirect server-side (CSV was redundant)
- 4 broken redirect chains: chicken-forage, chicken-pasture, big-four-erosion, poultry-forage → land on 404
- **Remaining**:
  - 3 PHP functions (noindex, clean canonical, strip tracking) → send to theme editor
  - ~50 fragment URL prefix removals in GSC UI (manual — no API for this)
  - robots.txt: Do NOT add Disallow rules (conflicts with noindex approach)

### Google Ads — Remaining Tier 2-4 Work
From `marketing/google-ads-audit/LIVE_IMPLEMENTATION_GUIDE.md`:
- Tier 1: Run Script 09 (URL fixes), Run Script 13b (remaining keywords)
- Tier 2: Pasture Exact bidding strategy, conversion tracking audit
- Tier 3: Budget reallocation, California asset group, DSA campaign
- Tier 4: Mobile bid adjustments, search term mining, merchant feed cleanup

### Keyword Expansion — Phase 3 Done, Manual SEO Remains
**Phase 3 implemented March 16** — 4 new ad groups in "Search | Animal Seed (Broad) | ROAS":
| Ad Group | Keywords | Landing Page |
|----------|----------|--------------|
| Sheep Pasture Seed | 5 BROAD | `/products/pasture-seed/sheep-pastures-seed/` |
| Cattle Pasture Seed | 5 BROAD | `/products/pasture-seed/cattle-pasture-seed/` |
| Goat Pasture Seed | 5 BROAD | `/products/pasture-seed/goat-pasture-seed/` |
| Deer & Wildlife Habitat | 5 BROAD | `/products/food-plot-seed/` |

**Manual SEO remaining**:
- RankMath SEO for drought category page (WP admin)
- Horse pasture page UX improvements
- Page speed optimization on landing pages

### Financial Goals
- Populate `financial_goals` Supabase table for goal tracking in dashboard

### Klaviyo Campaign Templates
- 55 drafts created — verify all templates linked correctly

---

## Completed Projects (Condensed)

### Google Ads 4-Year Audit (March 9-10)
Full audit with LIVE-FIRST framework. 8 extraction scripts, order attribution analysis (2,506 orders), Shopping bottom-20 benchmarking. Scripts 11-13 ran (negatives, pauses, keywords). `LIVE_STATE_AUDIT.md` and `LIVE_IMPLEMENTATION_GUIDE.md` are the reference docs.

### Google Ads Drip Automation (March 9)
Built complete system: `cycle_orchestrator.py` → Telegram approval → `google_ads_mutator.py`. Completed 1 cycle + keyword review. **Cron disabled March 16** — user manages from desktop for more nuanced control. Manual trigger via `workflow_dispatch`.

### Texas Collection Feed (March 10)
21 feed rows (7 products x 3 variants) in `texas_collection_feed.csv`. Ready to paste into GMC feed sheet.

### Shopping Bottom-20 Fixes (March 11)
15 of 17 products updated with descriptions, short_descriptions, ACF fields. All 20 variations restocked to qty 40.

### Klaviyo Campaign Drafts (March 10)
55 campaigns created for Mar-May 2026 via `create_campaigns.py`. API revision `2024-07-15`. Template assignment via MCP tool only.

### Browse Abandonment Flow (March 11-16)
3 templates created (XAQtiJ, UmGdL4, Rt4ZAW). **Updated in Klaviyo UI March 16** — templates assigned, subject lines updated, filters reviewed.

### Algolia Search Optimization (March 4-9)
136 synonyms, 7 merchandising rules, 11 searchable attributes, content enrichment pipeline, contextual tags on all products, 17 "we don't carry this" redirect rules, auto-synonym review automation. **Complete** — all frontend work specs in `FRONTEND_INSTRUCTIONS.md`.

### IS Increase — Impression Share Recovery (March 12)
Created drought-tolerant WC category (ID: 6029), wildflower ad group, 9 RSAs, 16 sitelinks + 16 callouts. Updated keyword final URLs for drought/horse/texas.

### Keyword Coverage Expansion — Phase 1-3 (March 12-16)
Phase 1: Lawn, Food Plot, Clover, Cover Crop. Phase 2: CA Wildflower, Lawn Alt, Sports Turf, Buffalograss. Phase 3: Sheep, Cattle, Goat, Deer/Wildlife. Keywords went from 67 → ~150 covering ~95% of catalog.

### Spring 2026 Recovery
4 category campaigns sent. 1,029 profile reclassification follow-up completed.

### Repo Reorganization (March 16)
Restructured flat folder into domain-based: `infrastructure/`, `seo/`, `marketing/`, `store/`, `marketplaces/`, `research/`. All workflow paths updated.

---

## Connected Systems Quick Reference

| System | Key ID | Notes |
|--------|--------|-------|
| Klaviyo | Account `H627hn` | MCP server, use `model: "claude"`, metric `VLbLXB` |
| Algolia | App `CR7906DEBT` | Index: `wp_prod_posts_product` |
| WooCommerce | REST API v3 | 0.3s rate limit, CF Worker proxy for datacenter IPs |
| Walmart | OAuth 2.0 | Tokens expire 15 min |
| Amazon | SP-API | API access in `.env` (new) |
| Fishbowl | HTTP API | Inventory source of truth |
| Supabase | `zoeuacgxthkiemzyunsd.supabase.co` | `sb_secret_*` API key, `apikey` header only |
| Google Ads | `599-287-9586` | Login CID `838-619-4588` |
| GA4 | Property `294622924` | Shared OAuth token |
| Merchant Center | ID `138935850` | Shared OAuth token |
| Search Console | `sc-domain:naturesseed.com` | Shared OAuth token |
| Shippo | REST API | Deduplicate by tracking number |
| CF Worker | `wc-api-proxy.skylar-d51.workers.dev` | WC API proxy |
| GitHub Actions | `nature-seed-data` repo | Daily midnight MST, nightly 10 PM MST |

## Key Technical Patterns

- **`.env` parsing**: Spaces around `=` + quotes around values. Use `line.split('=', 1)` then `.strip().strip("'\"")`
- **Google Ads Scripts**: `DRY_RUN = true` default. Run in Ads UI → Tools → Scripts
- **Klaviyo API**: Revision `2024-07-15` = snake_case. Template assignment only via MCP tool
- **GMC Feed**: 47 cols, ID=`gla_`+variation_id, MPN=`SKU-WEIGHT-LB`, CL0-4 labels
- **Permalink Manager**: All URLs use `/products/`, NEVER `/product-category/`

## Business Rules

- `-ADDON` SKUs: Never recommend as replacement products
- "Product Still Exists" rule: Active product under new SKU → re-purchase segment, not replacement
- Main categories: Pasture, Lawn, Wildflowers. Subcategories (primary): Cover Crop, Food Plot, Clover
- Regional labels (California, Texas) are behavioral tags, not product categories

---

## First Prompt for New Conversation

Copy the block below into a new Claude Code session to resume Klaviyo Plan 1 execution:

```
Resume the Klaviyo Strategy Framework rollout — execute Plan 1.

Read in this order before doing anything:
1. HANDOFF.md (this file) — "🔥 ACTIVE IN-FLIGHT — Klaviyo Strategy Framework Rollout (Plan 1 Execution)" section at the top
2. docs/superpowers/specs/2026-04-17-klaviyo-strategy-design.md — the strategy spec (locked decisions, do NOT re-decide)
3. docs/superpowers/plans/2026-04-17-klaviyo-framework-foundation.md — Plan 1, 9 sections, ~30 bite-sized tasks

Execution mode: subagent-driven-development (per the Plan's handoff section).
Dispatch one fresh subagent per Task, review between tasks, commit after each
Section's tasks are all green.

Critical constraints (do not violate):
- Klaviyo REST API revision 2024-07-15 (CLAUDE.md rule 17)
- .env manual parse: line.split("=", 1) + .strip().strip("'\"") (CLAUDE.md rule 20)
- Klaviyo private key env var: KLAVIYO_API
- Conversion metric ID: VLbLXB (WooCommerce Placed Order)
- NO MCP tools in Python scripts — use REST API directly so scripts work in GitHub Actions
- Winback template UPLOAD is NOT in Plan 1 — only draft proposal markdown; Gabe approves first
- Flow filter edits are NOT possible via REST API — suppression-rules.md documents the manual UI steps (CLAUDE.md rule 21)

Stop before executing anything and summarize:
- What Plan 1 will produce
- The 9 sections in order
- Any questions before we start dispatching subagents
```
