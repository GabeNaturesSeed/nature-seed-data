# Nature's Seed — Session Handoff (March 16, 2026)

> Read this at the start of any new session to pick up where we left off.

---

## Project Status Overview

| # | Project | Directory | Status |
|---|---------|-----------|--------|
| 1 | Daily Report Pipeline | `infrastructure/daily-report/` | Running (daily + nightly cron) |
| 2 | Nightly Sales Review | `infrastructure/daily-report/nightly_review.py` | Running (10 PM MST Telegram) |
| 3 | Google Ads Drip | `marketing/google-ads-audit/drip/` | ⏸️ Cron disabled — manual desktop only |
| 4 | Walmart Optimization | `marketplaces/walmart-optimization/` | Spreadsheet regenerated, needs upload |
| 5 | WC ↔ Walmart Sync | — | Not built yet |
| 6 | Shopper Approved → GMC | — | Research done, needs dashboard check |
| 7 | Amazon Channel | — | API access obtained, ready to build |
| 8 | Retool Dashboard | Retool (external) | Pending — connect to Supabase |
| 9 | Crawl Budget Cleanup | `seo/search-console/` | Theme code + GSC submissions pending |
| 10 | Google Ads Audit | `marketing/google-ads-audit/` | Done — Tier 2-4 items remain |
| 11 | Keyword Expansion | `seo/is-increase/` | Phase 1-3 done, manual SEO tasks remain |

**Fully Completed (archived):** Google API Connections, Texas Collection Feed, Spring 2026 Recovery, Klaviyo 55 Campaign Drafts, Shopping Bottom-20 Fixes, Browse Abandonment Flow, Algolia Optimization, Marketplace Bot (cron disabled)

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

### Amazon Channel
- API access now available in `.env`
- Ready to add as a channel in `daily_pull.py` and build order/sales sync

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
