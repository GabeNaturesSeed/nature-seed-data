# Feed Platform Guides + Agent Directive — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Research best practices for all 8 feed channels using Opus 4.7, write per-platform AI-agent directive guides, and create the master monthly `FEED_AGENT_DIRECTIVE.md` that the feed agent reads to execute improvements autonomously.

**Architecture:** Each platform guide lives in `docs/feeds/guides/{channel}.md` and follows a standard template (success criteria → required fields → failure modes → seasonal behavior → improvement checklist → how to measure). The master directive `docs/feeds/FEED_AGENT_DIRECTIVE.md` synthesizes all guides into a monthly operating playbook. All guides are living docs — the agent updates them as results come in.

**Tech Stack:** Opus 4.7 subagents for deep research, current feed data from `feeds/digest/latest_results.json` + `feeds/benchmark/benchmark.json`, existing adapter SCHEMA.md files.

**Important:** Tasks 1–8 (the platform guides) are fully independent and can be executed in parallel. Task 9 (master directive) depends on all guides existing.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `docs/feeds/guides/walmart.md` | Create | Walmart Marketplace feed success guide |
| `docs/feeds/guides/amazon.md` | Create | Amazon SP-API catalog feed success guide |
| `docs/feeds/guides/google_merchant.md` | Create | Google Merchant Center feed success guide |
| `docs/feeds/guides/klaviyo.md` | Create | Klaviyo catalog sync success guide |
| `docs/feeds/guides/shopper_approved.md` | Create | Shopper Approved review feed guide |
| `docs/feeds/guides/reddit.md` | Create | Reddit Dynamic Product Ads feed guide |
| `docs/feeds/guides/facebook.md` | Create | Meta/Facebook catalog feed success guide |
| `docs/feeds/guides/pinterest.md` | Create | Pinterest catalog feed success guide |
| `docs/feeds/FEED_AGENT_DIRECTIVE.md` | Create | Master monthly agent operating directive |

---

### Task 1: Walmart Marketplace Feed Guide

**Files:**
- Create: `docs/feeds/guides/walmart.md`

Current state from audit: 200/478 coverage (41.8% — seasonality-explained), 192 stock drift items, 55 quality issues (missing short_description fields), 0 price drift.

- [ ] **Step 1: Research Walmart feed best practices via Opus 4.7**

Dispatch an Opus 4.7 agent with this prompt:

```
Research Walmart Marketplace seller product feed best practices for 2025-2026. Cover:
1. What makes a listing rank well in Walmart search (title optimization, keyword placement, attribute completeness)
2. Required vs recommended fields in the MP_MAINTENANCE feed — what triggers suppression vs just quality score reduction
3. Listing Quality Score (LQS) — how it's calculated, what the main levers are
4. Buy Box factors for a small brand seller (no FBA equivalent, but Nature's Seed uses standard fulfillment)
5. How Walmart's search algorithm responds to seasonal demand spikes (seed/garden category, spring = high season weeks 8-18)
6. Common feed failure modes: what causes items to go STAGE vs PUBLISHED vs UNPUBLISHED
7. Image requirements: minimum resolution, background, aspect ratio
8. Short description best practices: character limits, keyword density, format

Scope: Nature's Seed sells grass seed, wildflower mixes, pasture seed, cover crops. SKUs are variation products (1 lb, 5 lb, 25 lb bags). ~478 WC SKUs, 200 currently listed on Walmart.

Return: structured findings organized by the research questions above. Be specific about character counts, field names, score thresholds where known.
```

- [ ] **Step 2: Write `docs/feeds/guides/walmart.md`**

Using the Opus 4.7 research output, write the guide file:

```markdown
# Walmart Marketplace — Feed Success Guide
_Last updated: 2026-04-29_

## What Success Looks Like

[Fill from research: coverage %, LQS target score, publish rate target, buy box win rate target.
For Nature's Seed specifically: all 478 WC SKUs listed, LQS ≥ 75 across catalog, 0 UNPUBLISHED items,
stock status in sync within 24h of WC change.]

## Required Fields & Why They Matter

| Field | Required | What breaks without it |
|-------|----------|----------------------|
| sku | Yes | Item cannot be created |
| name/productName | Yes | Listing suppressed |
| shortDescription | Yes | LQS -25 pts; ranking drops significantly |
| price | Yes | Listing suppressed |
| main_image_url | Yes | Listing suppressed |
| stock_status | Yes | Buy box ineligible if wrong |
| brand | Yes | Category filtering breaks |
| GTIN/UPC | Recommended | LQS -15 pts without it |
| keyFeatures (3-5 bullets) | Recommended | LQS -10 pts; conversion drops |
| longDescription | Recommended | LQS -10 pts |
| shelfName (4-level category) | Recommended | LQS -15 pts |

[Expand each row with exact character limits and format requirements from research.]

## Known Failure Modes

### Items stuck in STAGE
**Symptom:** publishedStatus == "STAGE" in GET /v3/items  
**Cause:** Item submitted but not yet activated. Walmart requires explicit activation via MP_ITEM feed after creation.  
**Fix:** Run `marketplaces/walmart-optimization/activate_stage_items.py` — reads stage_audit.json, submits activation feed for items with Fishbowl stock.

### Stock drift (192 items)
**Symptom:** WC stock_status != Walmart stock_status  
**Cause:** Price sync script (sync_prices.py) does not sync stock. Manual trigger only.  
**Fix:** Run `feeds/sync/sync_prices.py --push` — pushes both price and inventory from feed_master.json.

### JSONDecodeError on token endpoint
**Symptom:** `json.JSONDecodeError` when fetching token  
**Cause:** Missing `Accept: application/json` header — Walmart returns XML by default.  
**Fix:** Ensure `_get_token()` in `feeds/adapters/walmart.py` includes `"Accept": "application/json"` header. Already fixed as of 2026-04-29.

[Add additional failure modes from Opus research.]

## Seasonal Behavior

[Fill from research: how Walmart's algorithm behaves during spring planting season (weeks 8-18).
Expected: higher search volume for grass seed / wildflower categories, buy box competition increases,
LQS becomes more important for ranking. Note weeks 8-18 are peak for Nature's Seed (index > 0.85).]

## Improvement Checklist (ordered by impact)

- [ ] Fix 192 stock drift items — run sync_prices.py --push (immediate, no content work)
- [ ] Populate shortDescription on all 478 SKUs — biggest LQS lever (-25 pts when missing)
- [ ] Add 3-5 keyFeatures bullets to every SKU — second biggest LQS lever
- [ ] Add GTIN/UPC to all SKUs that have it in WC meta_data
- [ ] Expand to full 478 SKU coverage — submit missing 278 SKUs via MP_ITEM feed
- [ ] Set 4-level shelfName taxonomy for all items
- [ ] Audit UNPUBLISHED items and resolve suppression reasons via GET /v3/items?lifecycleStatus=UNPUBLISHED

## How to Measure Progress

- **Primary:** `benchmark.json` — walmart coverage_score, quality_score, drift_score week-over-week
- **Secondary:** Walmart Seller Center → Growth → Listing Quality Score dashboard
- **Drift resolution:** drift_score should move from ~68 → 95+ after one sync_prices run
- **Quality improvement:** quality_score moves as shortDescription fields are populated
- **Seasonality note:** Coverage score is relaxed off-season (index < 0.5). At peak (weeks 8-18), coverage_score target is 95+.
```

- [ ] **Step 3: Commit**

```bash
git add docs/feeds/guides/walmart.md
git commit -m "docs(feeds): Walmart feed success guide"
```

---

### Task 2: Amazon SP-API Catalog Guide

**Files:**
- Create: `docs/feeds/guides/amazon.md`

Current state: adapter erroring (auth issue — AMAZON_SELLER_ID in GH secrets, pending verification). No audit data yet.

- [ ] **Step 1: Research Amazon feed best practices via Opus 4.7**

```
Research Amazon Selling Partner (SP-API) product catalog feed best practices for 2025-2026, specifically for:
1. What fields are required to avoid listing suppression in the Seeds & Plants category
2. How Amazon's A9/A10 algorithm weights product listing completeness (title, bullets, description, images, A+ content)
3. ASIN matching vs new listing creation — when does Amazon create a new ASIN vs match to existing?
4. FBA vs FBM listing quality differences (Nature's Seed is FBM — ships direct)
5. How to check for suppressed listings via SP-API
6. Seasonal visibility in the Seeds/Garden category — does Amazon algorithmically boost listings during spring?
7. Image requirements: main image (pure white background required), additional images, lifestyle images
8. Common SP-API catalog submission errors and how to diagnose them from the response

Return: structured findings. Be specific about the SP-API endpoints involved and field names.
```

- [ ] **Step 2: Write `docs/feeds/guides/amazon.md`** using the template:

```markdown
# Amazon SP-API — Feed Success Guide
_Last updated: 2026-04-29_

## What Success Looks Like
[Fill: coverage %, suppressed listing count = 0, Buy Box % target for FBM seller in seed category,
review velocity target.]

## Required Fields & Why They Matter
[Fill from research: item_name, brand, product_description, bullet_points (5), main_image, category node,
UPC/EAN, manufacturer. Note which cause suppression vs just hurt ranking.]

## Known Failure Modes

### Auth error (current)
**Symptom:** `400 Client Error` or empty sellerId in SP-API requests  
**Cause:** `AMAZON_SELLER_ID` env var not set in GH Actions secrets (added 2026-04-29 — verify next run).  
**Fix:** Confirm secret `AMAZON_SELLER_ID` exists in repo secrets (not environment secrets).

### ASIN mismatch
[Fill from research.]

[Additional failure modes from research.]

## Seasonal Behavior
[Fill from research.]

## Improvement Checklist (ordered by impact)
- [ ] Verify AMAZON_SELLER_ID secret is working — check next audit run for error resolution
- [ ] Audit suppressed listings via GET /catalog/2022-04-01/items with includedData=summaries
- [ ] Ensure all SKUs have 5 bullet points (keyFeatures equivalent for Amazon)
- [ ] Add A+ content to top 20 SKUs by revenue
- [ ] Map all SKUs to correct Amazon browse node (Seeds > Grass Seed etc.)

## How to Measure Progress
- **Primary:** benchmark.json — amazon coverage_score, quality_score week-over-week once auth is resolved
- **Secondary:** Amazon Seller Central → Inventory → Fix stranded inventory report
```

- [ ] **Step 3: Commit**

```bash
git add docs/feeds/guides/amazon.md
git commit -m "docs(feeds): Amazon SP-API feed success guide"
```

---

### Task 3: Google Merchant Center Feed Guide

**Files:**
- Create: `docs/feeds/guides/google_merchant.md`

Current state: adapter returning `gla_*` offerIds (fixed to use mpn as of 2026-04-29 — verify in next run). 16 quality issues (missing GTINs). Expected coverage near 100% after mpn fix.

- [ ] **Step 1: Research GMC feed best practices via Opus 4.7**

```
Research Google Merchant Center product feed best practices for 2025-2026:
1. Feed spec compliance — what triggers product disapprovals vs just warnings
2. Required attributes for the Seeds/Plants category (google_product_category 1712 or similar)
3. How Google's Shopping algorithm uses feed quality for ranking (title optimization, description, product type)
4. GTIN requirements — what happens with missing GTINs, how to use identifier_exists=false as fallback
5. Supplemental feeds vs primary feeds — when to use each
6. How Shopping ads performance correlates with feed quality score in Merchant Center
7. Free Listings (organic Shopping) vs paid Shopping ads — do the same quality signals apply?
8. Image requirements for Shopping ads (main image, additional images, lifestyle)
9. How seasonal demand affects Shopping impression share (Google Ads IS metrics)

Context: Nature's Seed manages their GMC feed via a Google Sheet (supplemental feed approach).
The sheet uses gla_* as the id column and mpn = WC SKU (e.g. WB-RM-5-LB-KIT).

Return: structured findings with specific attribute names and disapproval trigger conditions.
```

- [ ] **Step 2: Write `docs/feeds/guides/google_merchant.md`** using the template:

```markdown
# Google Merchant Center — Feed Success Guide
_Last updated: 2026-04-29_

## What Success Looks Like
[Fill: 0 disapproved products, feed quality score ≥ 80%, all active SKUs listed,
GTIN populated on all items where available, IS rank target from seasonality.json baselines.]

## Required Fields & Why They Matter
[Fill: id (gla_* from sheet), title, description, link, image_link, availability, price,
google_product_category, brand, gtin (or identifier_exists=false), condition=new.
Note which cause disapproval vs just warning.]

## Known Failure Modes

### offerId vs mpn mismatch (fixed 2026-04-29)
**Symptom:** 0/478 WC SKUs matching in coverage check despite 320 GMC products  
**Cause:** GMC Content API returns `offerId` as `gla_*` IDs; WC SKUs live in `mpn` field.  
**Fix:** Adapter now uses `item.get("mpn", "") or item.get("offerId", "")`. Verify in next audit run.

### Missing GTINs (16 items)
**Symptom:** quality_score < 100 due to missing `gtin` field  
**Cause:** 16 products in the Google Sheet don't have GTIN populated.  
**Fix:** Either populate GTIN in the sheet for those 16 SKUs, or add `identifier_exists: false` attribute.

[Additional failure modes from research.]

## Seasonal Behavior
[Fill from research — how Google Shopping IS fluctuates with planting season.
Note: IS rank data is in seasonality.json weekly_baselines.is_rank_mean — use this as the baseline.]

## Improvement Checklist (ordered by impact)
- [ ] Verify mpn fix resolves coverage to ~100% in next audit run
- [ ] Populate GTIN for 16 missing items in Google Sheet OR add identifier_exists=false
- [ ] Optimize titles for top 50 SKUs (keyword-front-loaded, species name first)
- [ ] Add product_type (4-level taxonomy) to all items
- [ ] Audit disapproved products in Merchant Center dashboard

## How to Measure Progress
- **Primary:** benchmark.json — google_merchant coverage_score (should hit ~100 after mpn fix), quality_score
- **Secondary:** Merchant Center → Products → Diagnostics tab (disapprovals, warnings)
- **Performance:** IS rank from daily_report Supabase data vs weekly_baselines.is_rank_mean in seasonality.json
```

- [ ] **Step 3: Commit**

```bash
git add docs/feeds/guides/google_merchant.md
git commit -m "docs(feeds): Google Merchant Center feed success guide"
```

---

### Task 4: Klaviyo Catalog Guide

**Files:**
- Create: `docs/feeds/guides/klaviyo.md`

Current state: adapter erroring (400 on `page%5Bsize%5D=100` — bracket encoding bug fixed in b9e8114, but the 2026-04-29 digest still shows the old error because the workflow ran before the fix was pushed). Should clear on next run.

- [ ] **Step 1: Research Klaviyo catalog best practices via Opus 4.7**

```
Research Klaviyo product catalog (catalog items API) best practices for 2025-2026:
1. How Klaviyo uses the product catalog for email personalization — browse abandonment, back-in-stock, 
   product recommendation blocks in campaigns
2. Required fields for a catalog item to be usable in flows (external_id, title, price, image_full_url, url)
3. How catalog sync health affects email revenue — what breaks if items are missing or have stale prices
4. Best practices for catalog item URLs in emails (UTM parameters, direct product page vs category page)
5. How to use catalog items in Klaviyo's product recommendation algorithm (collaborative filtering)
6. Klaviyo's "published" field — what does it control in email templates?
7. Catalog variants vs catalog items — when to use each for a variable product like grass seed (1lb vs 5lb vs 25lb)
8. Back-in-stock flow setup — how catalog item availability field triggers the flow

Context: Nature's Seed has ~478 WC SKUs, each with multiple size variations. Klaviyo is used for
email marketing — browse abandonment, post-purchase, seasonal campaigns.
Revision: 2024-07-15

Return: structured findings with specific API field names.
```

- [ ] **Step 2: Write `docs/feeds/guides/klaviyo.md`** using the template:

```markdown
# Klaviyo Catalog — Feed Success Guide
_Last updated: 2026-04-29_

## What Success Looks Like
[Fill: all active WC SKUs synced to Klaviyo catalog, 0 items with missing image_full_url or url,
price matches WC within 24h, back-in-stock flow triggering on availability changes.]

## Required Fields & Why They Matter
[Fill from research: external_id (= WC SKU), title, price, image_full_url, url, published.
Note what breaks in email templates when each is missing.]

## Known Failure Modes

### Bracket encoding error (fixed b9e8114)
**Symptom:** `400 Bad Request for url: .../catalog-items?page%5Bsize%5D=100`  
**Cause:** `requests` library percent-encodes `page[size]` → `page%5Bsize%5D` which Klaviyo rejects.  
**Fix:** Build URL string manually: `url = f"{KLAVIYO_BASE}/catalog-items?page[size]=100"`. Fixed in b9e8114.

[Additional failure modes from research.]

## Seasonal Behavior
[Fill: how Klaviyo email performance correlates with planting season.
During peak (weeks 8-18), browse abandonment flows fire more frequently.
Back-in-stock triggers during fall restock (weeks 32-38).
Catalog must stay fresh during high-volume email periods.]

## Improvement Checklist (ordered by impact)
- [ ] Verify bracket encoding fix resolves auth error in next audit run
- [ ] Confirm all 478 SKUs have populated image_full_url and url in Klaviyo catalog
- [ ] Set up back-in-stock flow for top 20 out-of-stock SKUs
- [ ] Validate URL UTM parameters are correctly set on all catalog item links
- [ ] Audit catalog items vs WC for price drift > $1.00

## How to Measure Progress
- **Primary:** benchmark.json — klaviyo coverage_score, quality_score once error resolves
- **Secondary:** Klaviyo → Catalog → Items tab (item count, last synced timestamp)
- **Revenue signal:** Browse abandonment flow revenue in Klaviyo flow reports
```

- [ ] **Step 3: Commit**

```bash
git add docs/feeds/guides/klaviyo.md
git commit -m "docs(feeds): Klaviyo catalog feed success guide"
```

---

### Task 5: Shopper Approved Guide

**Files:**
- Create: `docs/feeds/guides/shopper_approved.md`

Current state: 474/478 coverage (99.2%), 20 stock drift items (SA always returns instock), quality issues fixed (dropped url from required fields). TURF-JBR has 0 reviews due to SA integration disconnect.

- [ ] **Step 1: Research Shopper Approved best practices via Opus 4.7**

```
Research Shopper Approved (shopperapproved.com) product reviews integration best practices:
1. How the SA review widget affects on-site conversion (trust signals, star ratings in search results)
2. How SA product reviews feed into Google Shopping rich snippets (seller ratings)
3. Review request email timing best practices — when after purchase to send for highest response rate
4. How to maximize review collection rate (email sequence, incentives, timing)
5. SA API: what the /products/reviews/{site_id} endpoint returns — specifically what product_id represents
   (is it the merchant's own SKU, a SA-internal ID, or the product URL?)
6. How SA integrates with WooCommerce — does it automatically match reviews to products by SKU?
7. What "product_url" in the SA API response represents — is it the WC product permalink?

Context: Nature's Seed uses SA for product reviews. Site ID 33157. SA→Klaviyo review request
integration was disconnected in August 2025. TURF-JBR (Jimmy Blue Ribbon) shows 0 reviews despite
being a top seller since July 2025.

Return: structured findings. Focus especially on question 5 (product_id field meaning) and
question 6 (WC integration).
```

- [ ] **Step 2: Write `docs/feeds/guides/shopper_approved.md`** using the template:

```markdown
# Shopper Approved — Feed Success Guide
_Last updated: 2026-04-29_

## What Success Looks Like
[Fill: review collection rate, star rating targets, rich snippet eligibility requirements (minimum 50 reviews
for Google seller ratings). For Nature's Seed: SA→Klaviyo review request flow active, TURF-JBR
collecting reviews, all top-50 SKUs have ≥5 reviews.]

## Required Fields & Why They Matter
SA is a reviews source, not a product catalog. Required fields are minimal:
- `sku` (from product_id in SA API) — identifies the product
- `name` (from product field in SA API) — display name in reports

Note: price, GTIN, description are NOT available from SA review API responses.
Quality score only checks sku + name.

## Known Failure Modes

### product_id field meaning
[Fill from Opus research: is product_id the merchant SKU, a SA internal ID, or something else?
Current adapter uses `review.get("product_id", "") or review.get("product", "")` — if product_id
is not the WC SKU, the coverage check may be matching on wrong identifiers.]

### SA→Klaviyo review request disconnect (August 2025)
**Symptom:** New products launched after August 2025 (e.g. TURF-JBR) have 0 reviews  
**Cause:** SA→Klaviyo integration disconnected. Review request emails not being sent post-purchase.  
**Fix:** Reconnect SA→Klaviyo integration in SA admin dashboard → Integrations → Klaviyo.

### Stock drift (20 items)
**Symptom:** SA always returns stock_status = "instock" regardless of actual WC status  
**Cause:** SA review API doesn't carry real-time inventory data — it reflects status at time of review.  
**Fix:** Drift items here are informational only. No action needed on SA side; these are data source limitations.

## Seasonal Behavior
Review velocity naturally spikes during and after peak season (weeks 8-20 = spring planting,
customers receive product and submit reviews 2-4 weeks later). Off-season review collection is slow
but the backlog of reviews from peak is valuable social proof for the following season.

## Improvement Checklist (ordered by impact)
- [ ] Reconnect SA→Klaviyo integration to resume automated review request emails
- [ ] Manually request reviews from TURF-JBR purchasers (since July 2025) via SA admin
- [ ] Verify product_id in SA API maps to WC SKU (see Known Failure Modes above)
- [ ] Target 50+ reviews on top-10 SKUs for Google seller ratings rich snippet eligibility

## How to Measure Progress
- **Primary:** benchmark.json — shopper_approved coverage_score, quality_score
- **Proxy:** Total review count per SKU in SA admin → Products tab
- **Rich snippets:** Google Search Console → Rich Results Test on product pages
```

- [ ] **Step 3: Commit**

```bash
git add docs/feeds/guides/shopper_approved.md
git commit -m "docs(feeds): Shopper Approved feed success guide"
```

---

### Task 6: Reddit Dynamic Product Ads Guide

**Files:**
- Create: `docs/feeds/guides/reddit.md`

Current state: adapter erroring (catalog file at `docs/reddit-catalog/reddit_catalog.tsv` not yet generated — external reddit-ads agent dependency).

- [ ] **Step 1: Research Reddit DPA feed best practices via Opus 4.7**

```
Research Reddit Dynamic Product Ads (DPA) product catalog feed best practices for 2025-2026:
1. Reddit catalog feed spec — required vs recommended fields (id, title, description, link, image_link,
   price, availability, condition, mpn, google_product_category)
2. How Reddit's DPA algorithm uses the catalog for retargeting and prospecting
3. Image requirements for Reddit ads (aspect ratios, minimum dimensions, text overlay rules)
4. Title and description optimization for Reddit's audience (more casual/authentic tone vs Google Shopping)
5. How Reddit's catalog approval process works — what triggers rejection
6. How seasonal demand for seeds/gardening content correlates with Reddit engagement
   (r/gardening, r/lawncare subreddits — when are they most active?)
7. Reddit pixel events that feed the DPA catalog — AddToCart, ViewContent, Purchase
8. TSV format specifics — any fields that differ from standard Google Shopping feed format

Context: Nature's Seed has a TSV catalog at docs/reddit-catalog/reddit_catalog.tsv (generated by
external reddit-ads agent). The TSV uses `mpn` as the WC SKU field and `price` in "X.XX USD" format.

Return: structured findings with specific field names and Reddit-specific requirements.
```

- [ ] **Step 2: Write `docs/feeds/guides/reddit.md`** using the template:

```markdown
# Reddit Dynamic Product Ads — Feed Success Guide
_Last updated: 2026-04-29_

## What Success Looks Like
[Fill: catalog approved, 0 rejected items, all active SKUs in feed, image pass rate 100%,
DPA campaigns active during peak season weeks 8-18.]

## Required Fields & Why They Matter
[Fill from research: id (gla_* or WC SKU), title, description, link, image_link, price, availability.
Note Reddit-specific format requirements vs standard Shopping feed.]

## Known Failure Modes

### Catalog file not generated yet
**Symptom:** `FileNotFoundError: docs/reddit-catalog/reddit_catalog.tsv`  
**Cause:** reddit-ads agent has not run yet to generate the TSV catalog.  
**Fix:** Run the reddit-ads agent to generate the catalog before the feed audit runs.

[Additional failure modes from research.]

## Seasonal Behavior
[Fill from Opus research: Reddit gardening/lawncare subreddits peak activity timing.
Cross-reference with Nature's Seed seasonality.json peaks (weeks 8-18 spring, 32-38 fall).]

## Improvement Checklist (ordered by impact)
- [ ] Unblock: run reddit-ads agent to generate catalog TSV
- [ ] Verify all required fields populated after first successful run
- [ ] Confirm image URLs are accessible and meet Reddit dimensions
- [ ] Set up Reddit pixel events on WC for DPA retargeting

## How to Measure Progress
- **Primary:** benchmark.json — reddit coverage_score, quality_score (once catalog file exists)
- **Secondary:** Reddit Ads Manager → Catalogs → Items tab (approval rate, rejected items)
```

- [ ] **Step 3: Commit**

```bash
git add docs/feeds/guides/reddit.md
git commit -m "docs(feeds): Reddit DPA feed success guide"
```

---

### Task 7: Facebook/Meta Catalog Guide

**Files:**
- Create: `docs/feeds/guides/facebook.md`

Current state: 280 products via public Google Sheet CSV. All required fields populated. Adapter live as of 2026-04-29.

- [ ] **Step 1: Research Meta catalog best practices via Opus 4.7**

```
Research Meta (Facebook/Instagram) product catalog feed best practices for 2025-2026:
1. Required vs recommended fields in the Meta catalog spec — what causes items to be rejected
2. How Meta's dynamic product ads (DPA) use catalog data for targeting and creative generation
3. Image requirements: main image (square preferred, min 500x500), lifestyle images, video
4. Title and description optimization for Meta ads (character limits, tone)
5. How Meta's catalog ranking algorithm works — what makes products more likely to show in DPA
6. google_product_category vs fb_product_category — which matters more for Meta catalog?
7. sale_price and sale_price_effective_date — how Meta handles sale pricing in ads
8. How seasonal demand for seeds/garden products translates to Meta ad performance
   (interest targeting, lookalike audiences)
9. Custom labels (custom_label_0 through custom_label_4) — best practices for organizing catalog
   for ad set targeting
10. Meta catalog approval process and common disapproval reasons

Context: Nature's Seed manages catalog via Google Sheet (spreadsheet ID 12u2Uj0gHNImAQKDA1qnDUxlw4czL4DNuHbuUFqULbuU).
280 products loaded. Fields include: id (gla_*), mpn (WC SKU), title, description, availability,
condition, price, link, image_link, brand, gtin, sale_price, custom_label_0/1/2.

Return: structured findings. Focus especially on custom_label strategy for targeting.
```

- [ ] **Step 2: Write `docs/feeds/guides/facebook.md`** using the template:

```markdown
# Meta/Facebook Catalog — Feed Success Guide
_Last updated: 2026-04-29_

## What Success Looks Like
[Fill: 0 rejected items, all 280+ products approved, DPA campaigns active,
custom labels set for seasonal targeting, sale_price populated during promotions.]

## Required Fields & Why They Matter
[Fill from research: id, title, description, availability, condition, price, link, image_link, brand.
Note which trigger rejection vs just reduce ad eligibility.]

## Known Failure Modes
[Fill from research: common disapprovals, image issues, pricing inconsistencies.]

## Custom Label Strategy
[Fill from research: recommended custom label structure for Nature's Seed.
Example: custom_label_0 = category (wildflower/grass/pasture), custom_label_1 = season (spring/fall/year-round),
custom_label_2 = price tier (under-50/50-100/100-plus).]

## Seasonal Behavior
[Fill from research: Meta DPA performance timing for garden/seed category.
Note: sale_price_effective_date in sheet currently set to 2025-08-01/2026-08-01 — verify still valid.]

## Improvement Checklist (ordered by impact)
- [ ] Verify catalog approved in Meta Business Manager (no disapprovals)
- [ ] Populate sale_price on all SKUs that have WC sale_price set
- [ ] Set custom_label_0/1/2 consistently across all 280 products in the sheet
- [ ] Add lifestyle images for top 20 SKUs (custom_label for image testing)
- [ ] Set up DPA retargeting campaign using catalog

## How to Measure Progress
- **Primary:** benchmark.json — facebook coverage_score, quality_score
- **Secondary:** Meta Business Manager → Catalogs → Data quality tab
```

- [ ] **Step 3: Commit**

```bash
git add docs/feeds/guides/facebook.md
git commit -m "docs(feeds): Meta/Facebook catalog feed success guide"
```

---

### Task 8: Pinterest Catalog Guide

**Files:**
- Create: `docs/feeds/guides/pinterest.md`

Current state: stub adapter only. Pinterest integration not yet built.

- [ ] **Step 1: Research Pinterest catalog best practices via Opus 4.7**

```
Research Pinterest product catalog feed best practices for 2025-2026:
1. Pinterest catalog spec — required fields for Product Pins (id, title, description, link, image_link,
   price, availability, google_product_category)
2. How Pinterest's Shopping algorithm works — what makes products eligible for Shopping ads and
   organic product discovery
3. Rich Pins vs Product Pins — difference and which to use
4. Image requirements for Pinterest: vertical images preferred (2:3 ratio), minimum dimensions,
   text overlay rules
5. How Pinterest's audience for seeds/gardening correlates with Nature's Seed's planting season
   (is Pinterest a spring-heavy platform for gardening content?)
6. Pinterest API v5 catalog endpoints — how to submit and update a catalog
7. Board organization and product groups — how they affect Shopping ad targeting
8. What happens without a Pinterest catalog (organic pins vs Shopping ads)

Context: Nature's Seed currently has a stub Pinterest adapter with no API connection.
This guide should inform when and how to build out the integration.

Return: structured findings. Include a clear recommendation on whether Pinterest is worth integrating
for a seed company (ROI estimate, audience size, competition level).
```

- [ ] **Step 2: Write `docs/feeds/guides/pinterest.md`** using the template:

```markdown
# Pinterest Catalog — Feed Success Guide
_Last updated: 2026-04-29_

## What Success Looks Like
[Fill from research + Opus recommendation on whether Pinterest is worth integrating for Nature's Seed.
If yes: coverage %, image pass rate, Shopping ad eligibility.]

## Build Recommendation
[Fill from Opus research: is Pinterest a viable channel for Nature's Seed?
Estimated audience size for seeds/gardening, competition, CPM vs other channels.]

## Required Fields & Why They Matter
[Fill from research.]

## Integration Path (when ready to build)
1. Apply for Pinterest API access at developers.pinterest.com
2. Create a catalog in Pinterest Business Hub
3. Replace stub adapter with real Pinterest Catalog API adapter
   (similar pattern to google_merchant.py — OAuth + paginated product fetch)
4. Map WC fields: id=SKU, title=name, description=short_description, link=url,
   image_link=main_image_url, price=price, availability based on stock_status

## Improvement Checklist
- [ ] Evaluate ROI: review Opus recommendation and decide if Pinterest integration is a Q3 priority
- [ ] If yes: apply for Pinterest API access
- [ ] Build adapter following google_merchant.py pattern
- [ ] Ensure all images are 2:3 vertical ratio for Pinterest optimization

## How to Measure Progress
- **Current:** N/A (stub — STUB shown in digest scorecard)
- **After integration:** benchmark.json pinterest coverage_score, quality_score
```

- [ ] **Step 3: Commit**

```bash
git add docs/feeds/guides/pinterest.md
git commit -m "docs(feeds): Pinterest catalog feed success guide"
```

---

### Task 9: Master Agent Directive

**Files:**
- Create: `docs/feeds/FEED_AGENT_DIRECTIVE.md`

This file synthesizes all platform guides into the monthly operating playbook. It depends on all 8 guides existing (Tasks 1–8).

- [ ] **Step 1: Pull current benchmark state**

```bash
python -c "
import json
b = json.load(open('feeds/benchmark/benchmark.json'))
if b['snapshots']:
    s = b['snapshots'][-1]
    print(f'Latest snapshot: {s[\"date\"]} (Week {s[\"iso_week\"]}, {s[\"season_label\"]})')
    for ch, data in s['channels'].items():
        if 'error' in data:
            print(f'  {ch}: ERROR')
        else:
            print(f'  {ch}: cov={data.get(\"coverage_score\")} qual={data.get(\"quality_score\")} drift={data.get(\"drift_score\")}')
else:
    print('No snapshots yet')
"
```

- [ ] **Step 2: Write `docs/feeds/FEED_AGENT_DIRECTIVE.md`**

```markdown
# Feed Agent — Monthly Operating Directive
_Last updated: 2026-04-29 | Next review: 2026-05-29_

## Mission

Maintain feed health across all 8 channels. Execute improvement tasks autonomously each month.
Report results to Gabe (gabe@naturesseed.com). Update this directive when tactics produce
measurable results or fail after 2 cycles.

## Platform Guides

Read these before executing any channel-specific task:
- Walmart: `docs/feeds/guides/walmart.md`
- Amazon: `docs/feeds/guides/amazon.md`
- Google Merchant: `docs/feeds/guides/google_merchant.md`
- Klaviyo: `docs/feeds/guides/klaviyo.md`
- Shopper Approved: `docs/feeds/guides/shopper_approved.md`
- Reddit: `docs/feeds/guides/reddit.md`
- Facebook: `docs/feeds/guides/facebook.md`
- Pinterest: `docs/feeds/guides/pinterest.md`

## Monthly Workflow

1. Pull `feeds/benchmark/benchmark.json` — read last 4 snapshots per channel
2. Pull today's digest: `feeds/digest/YYYY-MM-DD-feed-health.md`
3. Read current ISO week from `docs/data/seasonality.json` → note season_label
4. For each channel with a Red score (any dimension): execute the top unchecked item
   from that channel's improvement checklist
5. For each channel with an Amber score: log it; execute if fewer than 2 Red items are active
6. Commit all changes with message: `chore(feeds): monthly feed improvements YYYY-MM-DD`
7. Report to Gabe: for each action taken, report [channel] [dimension] [score before → after] [what was done]
8. If a tactic produced no improvement after 2 monthly cycles: mark it with ~~strikethrough~~ and try the next item

## Seasonality Rules

| Season | Index | Coverage target | Quality target | Drift tolerance |
|--------|-------|----------------|---------------|-----------------|
| Peak (weeks 8–18) | > 0.85 | 95+ | 95+ | Tighten sync weekly |
| Spring shoulder (weeks 5–7, 19–22) | 0.6–0.85 | 85+ | 95+ | Sync bi-weekly |
| Off-season (weeks 23–31) | 0.4–0.6 | Relaxed per scoring model | 95+ | Monthly sync OK |
| Fall season (weeks 32–40) | 0.6–0.85 | 85+ | 95+ | Sync bi-weekly |
| Deep off-season (weeks 41–7) | < 0.5 | Relaxed | 95+ | Monthly sync OK |

**Rule:** Quality is never relaxed. Coverage and drift tolerance follow the seasonality index.

## Current Priority Order
_(Update as scores improve)_

1. **Walmart drift** — 192 stock drift items → run `feeds/sync/sync_prices.py --push` immediately
2. **Amazon auth** — resolve AMAZON_SELLER_ID secret, get adapter working
3. **Klaviyo auth** — verify bracket encoding fix resolved 400 error in latest run
4. **Walmart quality** — populate shortDescription on all SKUs (biggest LQS lever)
5. **GMC coverage** — verify mpn fix brought coverage to ~100%
6. **GMC quality** — resolve 16 missing GTINs
7. **Facebook quality** — verify all 280 products have no disapprovals in Meta Business Manager
8. **Shopper Approved** — reconnect SA→Klaviyo integration for review requests
9. **Reddit** — unblock by running reddit-ads agent to generate catalog TSV

## Standing Rules

- **Never auto-push price changes** without committing a dry-run log first
  (`feeds/sync/sync_prices.py --dry-run` → review → then `--push`)
- **Coverage gaps below seasonality-adjusted threshold**: log only, do not alert Gabe
- **Quality gaps**: always act, regardless of season
- **Adapter errors 3 days in a row**: alert Gabe immediately with the error message
- **Before touching Walmart**: read `marketplaces/walmart-optimization/walmart_client.py`
  to understand token management and batch submission patterns
- **Content changes**: hand-tuned copy is intentional per channel. Do not overwrite
  channel-specific content with WC source copy without a clear quality reason.

## Reporting Template

After each monthly run, send Gabe a report in this format:

```
Feed Health Report — [YYYY-MM-DD] (Week [N], [Season Label])

ACTIONS TAKEN:
- [channel] [dimension]: [score before] → [score after] — [what was done]

STILL OPEN (no change this cycle):
- [channel] [dimension]: score [N] — [why no action / blocked on]

ERRORS:
- [channel]: [error message] — [investigation status]

NEXT MONTH FOCUS:
- [top 2-3 priorities for next cycle]
```

## Pivot Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-04-29 | Initial directive created | First issue of feed benchmark system |
```

- [ ] **Step 3: Commit**

```bash
git add docs/feeds/FEED_AGENT_DIRECTIVE.md docs/feeds/guides/
git commit -m "docs(feeds): master agent directive + all platform guides"
git push
```

---

## Post-Implementation Verification

After all 9 tasks complete:

1. All 8 guide files exist in `docs/feeds/guides/`
2. `docs/feeds/FEED_AGENT_DIRECTIVE.md` exists and has current priority order
3. Each guide has the full template sections populated (no `[Fill from research]` placeholders remaining)
4. Git log shows one commit per guide
5. The priority order in FEED_AGENT_DIRECTIVE.md matches the latest benchmark.json scores
