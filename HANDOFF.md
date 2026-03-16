# Nature's Seed — Session Handoff (March 10, 2026)

> **Purpose**: This document captures the full context, history, and state of all work completed across multiple CLI sessions. Read this at the start of any new session to pick up where we left off.

---

## Active Projects & Status

### 0. Daily Report Pipeline ✅ BUILT + CF PROXY DEPLOYED (March 10, 2026)
**Directory**: `infrastructure/daily-report/`
**GitHub Repo**: `GabeNaturesSeed/nature-seed-data`

**What was done**:
- Built complete daily P&L data pipeline pulling from 5 sources (WooCommerce, Walmart, Google Ads, Shippo, Google Sheets COGS)
- Created Supabase schema with 6 tables + 2 views (`daily_summary`, `mtd_comparison`)
- Backfilled all 365 days of 2025 data (sales + ad spend only, no COGS/Shippo for historical)
- Set up GitHub Actions cron job (midnight MST / 7 AM UTC)
- Pushed to GitHub, 16 secrets configured (including CF_WORKER_URL, CF_WORKER_SECRET)
- **Cloudflare Worker proxy deployed** to bypass Bot Fight Mode blocking WC API calls from GitHub Actions datacenter IPs

**Cloudflare Worker Proxy** (March 10, 2026):
- **Problem**: Cloudflare Bot Fight Mode serves JS challenges to datacenter IPs (GitHub Actions, AWS, etc.). Cannot be disabled (CFO policy). Cannot be bypassed with WAF custom rules on free plan.
- **Solution**: Cloudflare Worker at `wc-api-proxy.skylar-d51.workers.dev` — runs inside CF's network, bypasses Bot Fight Mode. Validates `PROXY_SECRET` header, forwards to WC REST API with Basic Auth.
- **Code**: `infrastructure/cloudflare-worker/wc-proxy.js`
- **Env vars**: `CF_WORKER_URL` + `CF_WORKER_SECRET` — when set, both `daily_pull.py` and `nightly_review.py` route WC calls through the Worker. When unset, falls back to direct WC API calls (local dev).
- **GitHub secrets**: Must be **Repository secrets** (not Environment secrets) — this distinction caused initial deployment failure.

**Key Files**:
| File | Purpose |
|------|---------|
| `infrastructure/daily-report/daily_pull.py` | Main orchestrator — pulls all 5 sources, writes to Supabase |
| `infrastructure/daily-report/nightly_review.py` | Nightly Telegram summary (10 PM MST) |
| `infrastructure/daily-report/backfill_2025.py` | Lightweight backfill (sales + ads only) |
| `infrastructure/daily-report/supabase_schema.sql` | All table DDL + views |
| `infrastructure/daily-report/requirements.txt` | Python deps (requests, google-ads, google-auth) |
| `infrastructure/cloudflare-worker/wc-proxy.js` | CF Worker proxy for WC API (bypasses Bot Fight Mode) |
| `.github/workflows/daily_report.yml` | GitHub Actions cron — midnight MST |
| `.github/workflows/nightly_review.yml` | GitHub Actions cron — 10 PM MST |

**Remaining**:
- Connect Retool to Supabase (PostgreSQL: `db.zoeuacgxthkiemzyunsd.supabase.co`, port 6543, db `postgres`, user `postgres`)
- Build Retool dashboard with MTD/YTD comparison queries
- Add financial goals to `financial_goals` table
- Future: Add Amazon channel when API access is obtained

### 0b. Google API Connections Verified (March 9, 2026)
**What was done**:
- Verified Google Ads API connection (Python client library)
- Verified Google Analytics GA4 (Property ID `294622924`)
- Verified Google Merchant Center (ID `138935850`) — required enabling Content API in Cloud Console
- Verified Google Search Console (`sc-domain:naturesseed.com` + `https://naturesseed.com/`)
- Generated new 4-scope OAuth refresh token covering all Google APIs

---

### 1. Google Ads 4-Year Audit ✅ COMPLETE + ORDER ATTRIBUTION + SHOPPING BENCHMARKING
**Directory**: `marketing/google-ads-audit/`

**What was done**:
- Built 8 data extraction scripts (01–08) that pull from the Google Ads UI console → output to Google Sheets
- Normalized all historical data via `normalize_google_ads.py`
- Produced `FULL_AUDIT_REPORT.md` (historical analysis) then pivoted to **LIVE-FIRST** framework
- Produced `LIVE_STATE_AUDIT.md` — the corrected audit grounded only in currently ENABLED campaigns
- Produced `LIVE_IMPLEMENTATION_GUIDE.md` — 4-tier action plan

**Order Attribution Analysis (March 10, 2026)**:
- Pulled 2,506 WC orders with full attribution metadata (GCLID, campaign ID, UTM, device)
- Cross-referenced to Google Ads campaigns for new customer acquisition cost (nCAC)
- Discovered PMax sub-campaign IDs not visible in API — grouped with parent PMax campaigns
- 95% of Google Ads orders are guest checkouts → strong new customer signal
- **Key files**: `order_attribution_90d.json`, `campaign_spend_90d.json`

**Shopping Product Benchmarking (March 10, 2026)**:
- Daily-normalized bottom 20 worst-performing products in Shopping | Catch All (campaign `22908379664`)
- Waste score = 50% daily spend + 50% inverse ROAS, normalized per day on days with actual spend
- **Top findings**:
  - White Dutch Clover: $26/day spend, 2.11x ROAS (highest waste)
  - Clover line collectively: $1,532 spent, ROAS 1.31-1.90x
  - 4 products with zero conversions (Fire-Wise, Bluebonnet, Pasture 50lb, Milkweed)
  - Dryland Pasture & Rocky Mountains Wildflower: worst CPAs ($75, $88)
- **Key file**: `shopping_bottom20_daily.json`

**Google Ads Scripts Created (ready to run in Google Ads UI)**:
| Script | Purpose | Status |
|--------|---------|--------|
| `09_fix_live_ad_urls.js` | Fix 16 enabled ads with redirect/broken URLs | Ready to run |
| `11_pause_money_losing_keywords.js` | Pause 24 keywords with ROAS <1.0x across 2 campaigns | **RAN** |
| `12_add_negative_keywords.js` | Add 21 negative keywords (account-wide, shopping-only, search-only) | **RAN** |
| `13_add_high_value_keywords.js` | Add 9 proven keywords to Search Pasture Exact | **RAN** (5 added, 1 skipped) |
| `13b_add_remaining_keywords.js` | Fix for Script 13 — fetches ALL ad groups regardless of status | Ready to run |
| `10_pause_404_ads.js` | ~~Pause 404 ads~~ **NO LONGER NEEDED** — all 404s were in paused campaigns | Deprecated |

**Key insight**: The user corrected the approach — only ENABLED campaigns matter. The old "US | Search | Product Ads" campaign has been off forever. Script 10 was scrapped entirely.

**Remaining Google Ads work (from LIVE_IMPLEMENTATION_GUIDE.md)**:
- Tier 1: Run Script 09 (URL fixes), Run Script 13b (remaining keywords)
- Tier 2: Fix Pasture Exact bidding strategy, audit conversion tracking, exclude zero-revenue Shopping products
- Tier 2 NEW: Act on Shopping bottom 20 — pause/exclude zero-conversion products, review Clover line ROAS
- Tier 3: Budget reallocation, California asset group, DSA campaign
- Tier 4: Mobile bid adjustments, search term mining, merchant feed cleanup

**Data sheets**:
- Scripts 1–4 data: `https://docs.google.com/spreadsheets/d/1pxIpjA8NGI7bM1JkANXtkJ1anpCOQ-Cs7-eQVnAit5k/edit`
- Scripts 5–8 data: `https://docs.google.com/spreadsheets/d/1eoGfHV6DmacNSM0TUA3RnjlZOiaRepzdCmeLR7o-DXU/edit`

---

### 2. Texas Collection — Google Merchant Center Feed ✅ COMPLETE
**Files**: `marketing/google-ads-audit/generate_texas_feed.py` → `marketing/google-ads-audit/texas_collection_feed.csv`

**What was done**:
- Analyzed full 280-product merchant feed (47 columns, all patterns documented)
- Found 7 Texas products on live site, scraped all variant data from WooCommerce Store API
- Built Python generator that produces 21 feed rows (7 products × 3 variants) in exact feed format
- User provided GTINs and COGS — all filled in, margin tiers auto-calculated
- CSV is **ready to paste** into the live Google Merchant Center feed sheet

**The 7 Texas Products**:
| Product | SKU | Item Group | Margin Status |
|---------|-----|-----------|---------------|
| Texas Bluebonnet Seeds | W-LUTE | NS_0103 | ⚠️ ALL negative (-3% to -21%) |
| Texas Native Wildflower Mix | WB-TEXN | NS_0104 | ⚠️ ALL negative (-8% to -29%) |
| Texas Pollinator Wildflower Mix | WB-TXPB | NS_0105 | ⚠️ 1 of 3 negative |
| Texas Native Lawn Mix | TURF-TXN | NS_0106 | ⚠️ ALL negative (-32% to -55%) |
| Texas Native Prairie Mix | PB-TXPR | NS_0107 | ⚠️ 1 of 3 negative |
| Mexican Primrose (Pinkladies) | W-OESP | NS_0108 | ✅ High Margin (56-64%) |
| Drummond Phlox Seeds | W-PHDR | NS_0109 | ✅ High/Average (50-58%) |

**⚠️ PRICING ALERT**: 11 of 21 variants have COGS exceeding the selling price. This was flagged to the user. The CSV was generated as-is — pricing review may be needed.

**Feed conventions established**:
- Custom label 1 = `Texas` (new regional tag, alongside existing `California`)
- Product Types: `Texas Wildflower Mix` and `Texas Specialty Seed Mix` (new subcategories)
- Item group IDs: NS_0103 through NS_0109 (continuing from highest existing NS_0102)

---

### 3. Spring 2026 Recovery Campaign (Previous Sessions)
**Directory**: `marketing/spring-2026-recovery/`

- Dynamic email template: Klaviyo ID `XGwd4G`
- Push script: `spring-2026-recovery/scripts/push_replacement_properties.py`
- Profile properties: `ns_p1_*` convention
- 4 category campaigns created (Lawn, Pasture, Wildflower, Clover)
- **Known issue**: ~1,029 profiles incorrectly in replacement pipeline (product still exists, variant changed). Fix planned for follow-up campaign 2 weeks after initial send.

---

### 4. Walmart Optimization (Previous Sessions)
**Directory**: `marketplaces/walmart-optimization/`

- Inventory sync: `inventory_sync.py` (182/182 items synced)
- SEO optimization: `seo_content_generator.py` + `generate_spreadsheet.py` (182 items)
- **Remaining**: Spreadsheet upload via Seller Center needed

---

### 5. Algolia Search Optimization (Previous Sessions)
**Directory**: `seo/algolia-optimization/`

- `optimize_search.py` — 57 synonyms, 7 rules, 11 searchable attributes configured
- App ID: `CR7906DEBT`, main index: `wp_prod_posts_product`
- **Remaining**: Enable clickAnalytics in theme JS, fix WC → Algolia content sync (empty descriptions)

---

## Key Technical Patterns

### Google Ads Scripts
- All scripts use `DRY_RUN = true` by default (log-only). Set `false` to apply changes.
- Scripts run in Google Ads UI: Ads account → Tools → Scripts → paste & run
- Use `AdsApp` API and GAQL queries. GAQL is preferred for complex filtering.
- **Bug learned**: `campaign.adGroups().withCondition('Status = ENABLED')` excludes PAUSED ad groups. Use GAQL without status filter to find all ad groups.

### Google Merchant Center Feed
- 47 columns, CSV format with multi-line descriptions
- ID format: `gla_` + WooCommerce variation ID
- MPN format: `SKU-WEIGHT-LB` (base) or `SKU-WEIGHT-LB-KIT` (multi-bag)
- URL format: `naturesseed.com/products/{category}/{slug}/?variation_id=XXXXX&attribute_size=...`
- Custom labels: CL0=category, CL1=region, CL2=price bucket, CL3=margin tier, CL4=unused
- Price format: `XX.XX USD`
- All products share GTIN within item group, differ in id/mpn/title/price/weight

### WooCommerce Store API
- Public endpoint (no auth): `naturesseed.com/wp-json/wc/store/v1/products?search=...`
- Returns product IDs, variation IDs, SKUs, prices, images
- Variation details need individual product page scraping (Store API variation endpoint returns 404)

---

## Connected Systems Quick Reference

| System | Key ID | Notes |
|--------|--------|-------|
| Klaviyo | Account `H627hn` | MCP server connected, use `model: "claude"` |
| Klaviyo Placed Order metric | `VLbLXB` | Use as conversionMetricId |
| Klaviyo Newsletter list | `NLT2S2` | — |
| Klaviyo Customers list | `Sy6vRV` | — |
| Algolia | App `CR7906DEBT` | Main index: `wp_prod_posts_product` |
| WooCommerce | REST API v3 | Rate limit: 0.3s between bulk ops |
| Walmart | OAuth 2.0 | Tokens expire in 15 minutes |
| Fishbowl | HTTP API | Inventory source of truth |
| Gmail | customercare@naturesseed.com | MCP server connected |
| Supabase | `zoeuacgxthkiemzyunsd.supabase.co` | Daily report database, `sb_secret_*` API key |
| Google Ads | Customer `599-287-9586` | Login CID `838-619-4588`, Python client |
| GA4 | Property `294622924` | Shared OAuth token |
| Merchant Center | ID `138935850` | Shared OAuth token |
| Search Console | `sc-domain:naturesseed.com` | Shared OAuth token |
| Shippo | REST API | Live key, deduplicate by tracking number |
| Retool | API key available | Dashboard frontend (pending setup) |
| Cloudflare Worker | `wc-api-proxy.skylar-d51.workers.dev` | WC API proxy, bypasses Bot Fight Mode |
| GitHub Actions | `nature-seed-data` repo | Daily cron at midnight MST, nightly at 10 PM MST |

---

### 6. Google Ads Drip Automation ✅ BUILT (March 9, 2026)
**Directory**: `marketing/google-ads-audit/drip/`

**What was built**:
- Complete drip optimization system: plan generation → Telegram approval → execution → tracking
- Python mutator library (`google_ads_mutator.py`) with all Google Ads API v23 write operations
- Telegram bot (`telegram_bot.py`) for plan delivery, double-confirmation flow, and interactive keyword placement
- Cycle orchestrator (`cycle_orchestrator.py`) — full autonomous cycle with peak season guardrails
- GitHub Actions workflow (`.github/workflows/google_ads_drip.yml`) — cron Mon/Thu at 8 AM MST
- Interactive keyword placement: user replies with `keyword, campaign > ad_group, match_type` format

**Key Files**:
| File | Purpose |
|------|---------|
| `marketing/google-ads-audit/drip/google_ads_mutator.py` | All Google Ads API write ops (budgets, negatives, pauses, keyword adds) |
| `marketing/google-ads-audit/drip/telegram_bot.py` | Telegram bot with HTML rendering, polling, keyword parsing |
| `marketing/google-ads-audit/drip/cycle_orchestrator.py` | Plan generation, execution, tracker/approval log updates |
| `marketing/google-ads-audit/drip/IMPLEMENTATION_TRACKER.md` | Optimization roadmap + change history |
| `marketing/google-ads-audit/drip/APPROVAL_LOG.md` | Full audit trail of all approvals |
| `marketing/google-ads-audit/drip/run_keyword_review.py` | One-off keyword review runner (retry logic, HTML-safe reports) |
| `.github/workflows/google_ads_drip.yml` | GitHub Actions cron + manual dispatch |

**Cycles Completed**:
- **Cycle 1** (March 9): Brand budget $30→$39/day, 4 negatives added, 3 keywords paused, keyword opps deferred
- **Cycle 1 Keyword Review** (March 9): 6/7 keywords added (3 brand, 3 search). `goat pasture seed mix` failed with persistent Google 500 error on Goats ad group — retry next cycle.

**Technical lessons**:
- Google Ads API v23: `client.get_type("FieldMask")` doesn't work — use `operation.update_mask.paths.append()`
- v23 mutate methods don't accept `validate_only`/`partial_failure` kwargs — handle separately
- `CustomerNegativeCriterion` doesn't support `keyword` field — use campaign-level negatives
- Telegram HTML parse mode: must escape `<`, `>`, `&` before injecting `<b>` tags
- Curly apostrophe (`'`) is invalid in Google Ads keywords — use straight quote (`'`)
- Google API 500 errors on specific ad groups can be persistent — implement retry with backoff

**Remaining**:
- Retry `goat pasture seed mix` → Goats ad group next cycle
- `pasture seed` not placed (user skipped it) — offer again next cycle
- System runs autonomously on Mon/Thu cron schedule

---

### 9. Shopping Bottom-20 Product Improvements ✅ COMPLETE (March 11, 2026)
**Scripts**: `store/product-updates/audit_bottom20_products.py`, `store/product-updates/update_product_descriptions.py`
**Audit report**: `marketing/google-ads-audit/product_content_audit.json`

**What was done**:
- Audited all 17 parent products from the Shopping bottom-20 list for content gaps
- Updated 15 products with missing `short_description`, `description`, and/or ACF fields
- Added `product_content_2` ACF field for Dryland Pasture Mix and Sun & Shade Mix
- Added 6 FAQ answers to Grass Seed for Shady Areas (444217)
- Restocked all 20 variations to qty 40 (7 had negative stock)

**Content updates by product**:
| Product | Parent ID | Fixed |
|---------|-----------|-------|
| White Dutch Clover | 445312 | desc + short_desc |
| CA Fire-Resistant Mix | 445160 | desc + short_desc |
| Clover Lawn Alternative | 458434 | desc + short_desc |
| Green Screen Food Plot | 455414 | desc + short_desc |
| Sundancer Buffalograss | 456233 | desc + short_desc |
| Dryland Pasture Mix | 458472 | desc + product_content_2 |
| Texas Bluebonnet | 462219 | desc |
| Chicken Forage Mix | 445163 | desc + short_desc |
| California Poppy | 445350 | desc + short_desc |
| Goat Pasture & Forage | 445267 | short_desc |
| Narrowleaf Milkweed | 445347 | desc + short_desc |
| Triblade Tall Fescue | 445117 | desc |
| Sun and Shade Mix | 447115 | desc + product_content_2 |
| Coastal CA Wildflower | 445349 | desc + short_desc |
| Grass Seed Shady Areas | 444217 | 6 FAQ answers |

**Still complete**: Rocky Mountain Wildflower (445310), Switchgrass (445325)

**Remaining**: Shopper Approved → Google Merchant Center star ratings (see below)

---

### 10. Klaviyo Browse Abandonment Flow Improvement ✅ TEMPLATES CREATED (March 11, 2026)
**Flow**: Browse Abandonment - Standard (`Xz9k4a`) — LIVE
**Category-Aware Draft**: `V2q3uA` — still draft, needs UI work to activate

**Audit findings**:
- Only 4.4 entries/day (very low volume) — trigger filters may be too restrictive
- Email 1 generates 89.5% of all flow revenue ($1,142/$1,277)
- Subject lines are category-mismatched (everyone gets "pasture" first regardless of what they browsed)
- Flow has never been updated since Jan 30, 2026

**Templates created** (assign these to the 3 flow messages):
| Template | ID | Klaviyo URL |
|----------|-----|------------|
| Email 1 — Product Reminder | `XAQtiJ` | klaviyo.com/email-editor/XAQtiJ/edit |
| Email 2 — Social Proof | `UmGdL4` | klaviyo.com/email-editor/UmGdL4/edit |
| Email 3 — Urgency + Seasonal | `Rt4ZAW` | klaviyo.com/email-editor/Rt4ZAW/edit |

**Required UI actions for full improvement** (cannot do via API):
1. Go to [flow editor](https://www.klaviyo.com/flow/Xz9k4a/edit) → click each email message → swap template to new IDs above
2. Update subject lines to use dynamic tags:
   - Email 1: `Still thinking about {{ event.ProductName }}?`
   - Email 2: `{{ first_name|default:"Hey" }}, any questions about your seed?`
   - Email 3: `Your planting window is closing, {{ first_name|default:"friend" }}`
3. Review flow filters — remove overly restrictive conditions to increase entry volume (target: 30+/day)
4. Check Smart Sending setting — reduce or disable if suppressing too many entries

---

### 8. Klaviyo Campaign Drafts ✅ COMPLETE (March 10, 2026)
**File**: `marketing/klaviyo-audit/create_campaigns.py`
**Results**: `campaign_creation_results.json`

**What was done**:
- Created 55 campaign drafts in Klaviyo for March–May 2026 email schedule
- Each campaign: HTML template created via REST API → campaign created via REST API → template assigned via MCP tool
- All campaigns target only starred segments (RFM, engagement, category purchaser segments)
- Used API revision `2024-07-15` (hyphenated/snake_case field names)
- Template assignment only works via MCP tool `klaviyo_assign_template_to_campaign_message` — REST API doesn't support it in any revision

**Key learning**: Klaviyo API revision headers completely change the schema. `2024-10-15` = camelCase, `2024-07-15` = hyphenated/snake_case. The MCP tool abstracts this.

---

### 7. Nightly Sales Review (Telegram) ✅ WORKING (March 10, 2026)
**File**: `infrastructure/daily-report/nightly_review.py`
**Workflow**: `.github/workflows/nightly_review.yml`

**What it does** — Every night at 10 PM MST, sends a Telegram summary:
- Today's revenue, orders, units, ad spend, MER, clicks, conversions
- Top 5 best-selling products (by revenue)
- Top 5 states (by revenue)
- MTD revenue vs last year (YoY %)
- Auto-generated commentary on performance

**How it works**:
- Pulls TODAY's orders live from WooCommerce via Cloudflare Worker proxy
- Pulls TODAY's Google Ads metrics live
- Queries Supabase `daily_summary` view for MTD through yesterday
- Combines today + MTD for full picture

**Secrets needed** (in addition to existing daily report secrets):
- `TELEGRAM_BOT_API` — already set for drip automation
- `TELEGRAM_CHAT_ID` — already set for drip automation
- `CF_WORKER_URL` — Cloudflare Worker proxy URL
- `CF_WORKER_SECRET` — Proxy authentication secret

---

## Automation Gaps (Priority Queue)

1. **Shopping product exclusions** — Act on bottom 20 waste analysis: pause zero-conversion products, review Clover line ROAS (HIGH) — content fixes ✅ done, stock restocked ✅ done
2. **Retool dashboard setup** — Connect to Supabase, build MTD/YTD views (ACTIVE)
3. **Financial goals data entry** — Populate `financial_goals` table for goal tracking
4. **WC → Walmart price sync** (HIGH)
5. **Walmart orders → WC/Fishbowl** (MEDIUM)
6. **Winback flow email 2** — 0% click rate (CRITICAL marketing fix)
7. **Algolia clickAnalytics** — enable in theme JS (MEDIUM)
8. **Algolia content sync** — WC descriptions now populated for bottom-20 products (MEDIUM — re-sync Algolia)
14. **Browse Abandonment flow** — Templates created (XAQtiJ, UmGdL4, Rt4ZAW), need UI actions: assign templates, update subject lines, review filters to increase 4.4/day volume
15. **Shopper Approved → Merchant Center** — Product reviews not connecting; SA dashboard needs Google feed syndication enabled, GMC needs Product Ratings program opt-in
9. **Google Ads Tier 2-4 items** — see `LIVE_IMPLEMENTATION_GUIDE.md`
10. **Texas collection pricing review** — 11 of 21 variants below cost
11. **Spring recovery follow-up** — reclassify 1,029 "product still exists" profiles
12. **Klaviyo campaign template assignment** — 55 drafts created, verify all templates linked correctly
13. **Add Amazon channel** — when API access obtained

16. **Phase 3 keyword expansion** — Animal-specific ad groups (sheep, cattle, goat, deer/wildlife) need dedicated landing pages first. Build those, then create the ad groups.
17. **Permalink Manager custom URL** — Set drought-tolerant category to `products/drought-tolerant-seed` in WP admin → Permalink Manager. Then update Google Ads keyword final URLs.

---

### 11. IS Increase — Impression Share Recovery ✅ IMPLEMENTED (March 12, 2026)
**Directory**: `seo/is-increase/`

**What was done**:
- Full landing page audit identifying keyword-level Quality Score issues
- Created "Drought-Tolerant Pasture Seed" WooCommerce category (ID: 6029, 45 products assigned by species analysis)
- Created "Wildflower Seeds" ad group — moved 5 misplaced wildflower keywords from Pasture campaign
- Paused 4 misplaced wildflower keywords dragging down QS
- Created 9 intent-matched RSA ads (wildflower, horse, drought, regional)
- Added 16 sitelinks + 16 callout extensions across all campaigns
- Updated drought keyword final URLs to new category page
- Updated Texas Native Prairie Mix → "Texas Native Pasture Prairie Mix" + livestock suitability ACF field
- Updated horse/equine and texas keyword final URLs to matching landing pages

**Key Files**:
| File | Purpose |
|------|---------|
| `seo/is-increase/SITE_CHANGES.md` | Manual site-side instructions (RankMath SEO, permalink, UX improvements) |
| `seo/is-increase/create_drought_category.py` | WC category creation + product assignment |
| `seo/is-increase/update_drought_urls.py` | Google Ads keyword URL updates |
| `seo/is-increase/keyword_coverage_audit.py` | Full product vs keyword gap analysis |
| `seo/is-increase/keyword_expansion.py` | Phase 1+2 ad group creation |
| `seo/is-increase/keyword_audit_data.json` | Raw audit data (112 products, 67 keywords) |
| `reports/is_increase_rsas.py` | RSA ad creation (fixed character limits) |
| `reports/is_increase_actions.py` | Initial bulk actions (ad groups, keywords, extensions) |
| `reports/landing_page_audit.py` | Keyword-level QS breakdown report |
| `reports/campaign_constraints.py` | IS constraint analysis per campaign |

**Remaining**:
- RankMath SEO for drought category (manual — WP admin)
- Custom permalink via Permalink Manager (`products/drought-tolerant-seed`)
- Horse pasture page UX improvements
- Page speed optimization on landing pages
- Phase 3: Animal-specific ad groups (needs landing pages first)

### 12. Keyword Coverage Expansion — Phase 1+2 ✅ IMPLEMENTED (March 12, 2026)
**Directory**: `seo/is-increase/`

**What was done**:
- Full keyword coverage audit: 112 published products vs 67 active keywords
- Found 15 products with ZERO ad coverage, 21 categories with no keywords
- Phase 1 (4 ad groups): Lawn Seed, Food Plot Seed, Clover Seed, Cover Crop Seed
- Phase 2 (4 ad groups): California Wildflower, Lawn Alternatives, Sports Turf, Buffalograss
- Each ad group includes BROAD match keywords + intent-matched RSA ad
- Took keywords from 67 → ~130+ covering ~90% of catalog

**Remaining (Phase 3 — needs landing pages first)**:
- Sheep Pasture Seed ad group
- Cattle Pasture Seed ad group
- Goat Pasture Seed ad group
- Deer/Wildlife ad group
- Each needs a dedicated landing page before creating the ad group

---

## Business Rules (MUST FOLLOW)

### Product Category Taxonomy
- Main categories: Pasture Seed, Lawn Seed, Wildflowers
- Subcategories (treat as PRIMARY): Cover Crop, Food Plot, Clover
- Regional labels (California, Texas) are NOT product categories — they're behavioral tags

### SKU Rules
- `-ADDON` SKUs: Never recommend as replacement products
- "Product Still Exists" rule: If base product is active under new SKU, customer goes to re-purchase segment, not replacement segment

---

## User Preferences
- **LIVE-FIRST approach**: Always start with what's currently enabled/active, not historical data
- Token-saving skills that pre-document schemas
- Holistic ecommerce optimization across all channels
- Plan mode for non-trivial tasks
- Subagents for parallel research
- Verify before marking complete
