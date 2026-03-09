# Nature's Seed — Session Handoff (March 5, 2026)

> **Purpose**: This document captures the full context, history, and state of all work completed across multiple CLI sessions. Read this at the start of any new session to pick up where we left off.

---

## Active Projects & Status

### 1. Google Ads 4-Year Audit ✅ COMPLETE
**Directory**: `google-ads-audit/`

**What was done**:
- Built 8 data extraction scripts (01–08) that pull from the Google Ads UI console → output to Google Sheets
- Normalized all historical data via `normalize_google_ads.py`
- Produced `FULL_AUDIT_REPORT.md` (historical analysis) then pivoted to **LIVE-FIRST** framework
- Produced `LIVE_STATE_AUDIT.md` — the corrected audit grounded only in currently ENABLED campaigns
- Produced `LIVE_IMPLEMENTATION_GUIDE.md` — 4-tier action plan

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
- Tier 3: Budget reallocation, California asset group, DSA campaign
- Tier 4: Mobile bid adjustments, search term mining, merchant feed cleanup

**Data sheets**:
- Scripts 1–4 data: `https://docs.google.com/spreadsheets/d/1pxIpjA8NGI7bM1JkANXtkJ1anpCOQ-Cs7-eQVnAit5k/edit`
- Scripts 5–8 data: `https://docs.google.com/spreadsheets/d/1eoGfHV6DmacNSM0TUA3RnjlZOiaRepzdCmeLR7o-DXU/edit`

---

### 2. Texas Collection — Google Merchant Center Feed ✅ COMPLETE
**Files**: `google-ads-audit/generate_texas_feed.py` → `google-ads-audit/texas_collection_feed.csv`

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
**Directory**: `spring-2026-recovery/`

- Dynamic email template: Klaviyo ID `XGwd4G`
- Push script: `spring-2026-recovery/scripts/push_replacement_properties.py`
- Profile properties: `ns_p1_*` convention
- 4 category campaigns created (Lawn, Pasture, Wildflower, Clover)
- **Known issue**: ~1,029 profiles incorrectly in replacement pipeline (product still exists, variant changed). Fix planned for follow-up campaign 2 weeks after initial send.

---

### 4. Walmart Optimization (Previous Sessions)
**Directory**: `walmart-optimization/`

- Inventory sync: `inventory_sync.py` (182/182 items synced)
- SEO optimization: `seo_content_generator.py` + `generate_spreadsheet.py` (182 items)
- **Remaining**: Spreadsheet upload via Seller Center needed

---

### 5. Algolia Search Optimization (Previous Sessions)
**Directory**: `algolia-optimization/`

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

---

## Automation Gaps (Priority Queue)

1. **WC → Walmart price sync** (HIGH)
2. **Walmart orders → WC/Fishbowl** (MEDIUM)
3. **Winback flow email 2** — 0% click rate (CRITICAL marketing fix)
4. **Algolia clickAnalytics** — enable in theme JS (MEDIUM)
5. **Algolia content sync** — WC descriptions empty in index (MEDIUM)
6. **Google Ads Tier 2-4 items** — see `LIVE_IMPLEMENTATION_GUIDE.md`
7. **Texas collection pricing review** — 11 of 21 variants below cost
8. **Spring recovery follow-up** — reclassify 1,029 "product still exists" profiles

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
