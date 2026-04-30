# Walmart Marketplace — Feed Success Guide
_Last updated: 2026-04-30_

## What Success Looks Like

Concrete targets for a small FBM seed brand on Walmart Marketplace:

- **Listing Quality Score (LQS):** target ≥ 80 ("Best") on every published SKU; minimum acceptable is ≥ 60 ("Good"). Walmart suppresses or deprioritizes anything below 60 in search.
- **Coverage:** at peak (weeks 8-18, seasonality index ≥ 0.85) target **95% of WC catalog published on Walmart** (≈ 454 of 478 SKUs). Off-season (index < 0.5) the live audit relaxes this — current 200/478 (41.8%) at index 0.462 is acceptable.
- **Publish rate:** ≥ 98% of submitted items reach `lifecycleStatus=ACTIVE` + `publishedStatus=PUBLISHED` within 48h of feed submission. Anything stuck in `STAGE` for > 72h must be triaged.
- **Stock sync cadence:** push inventory **every 6 hours** during peak season, **every 12 hours** off-season. Walmart's buy-box algorithm penalizes stale inventory feeds older than 24 hours.
- **Price sync cadence:** push price changes within **2 hours** of any WC price change. Walmart's repricer compares against site-wide retail; drift > 24h triggers price-parity flags.
- **Drift score:** ≥ 95 on `feeds/benchmark/benchmark.json`. Allowed: ≤ 5% of SKUs in transient drift between sync runs.
- **Quality score:** ≥ 90 on the benchmark (i.e., ≥ 90% of SKUs have all six required fields populated).

## Required Fields & Why They Matter

| Field | Required? | What breaks without it |
|-------|-----------|------------------------|
| productName (title) | Yes | Item rejected at feed ingest. 50–200 char limit; Walmart's enforced format is `Brand + Distinguishing Detail + Product Type + Pack Count/Weight`. Titles > 200 chars are truncated in search. |
| shortDescription | Yes | LQS drops by ~20 points; item still publishes but is heavily deprioritized in search and cannot win the Buy Box. 500–4000 char limit, plain text or limited HTML, must contain the primary search term in first 150 chars. |
| mainImageUrl | Yes | Item enters `STAGE` (unpublished) at feed ingest. Walmart will not promote a listing without a primary image. Min 1000×1000px (2000×2000 recommended), pure white background (RGB 255,255,255), product fills ≥ 85% of frame, JPG/PNG, public HTTPS URL, < 5MB. |
| price | Yes | Item rejected at feed ingest. Must be ≤ Walmart's "Comparison Price Rule" (typically the lowest price on naturesseed.com or any other public channel) or the listing is unpublished as "Price Leadership Violation." |
| stock_status / inventory | Yes | Items with `quantity=0` are auto-set to `outofstock` and lose Buy Box eligibility within 1 hour. Inventory must be a non-negative integer with `unit=EACH`. |
| brand | Yes | Item rejected at feed ingest. Must match a brand registered on Walmart's brand registry; mismatched brand = "BRAND_MISMATCH" suppression. |
| GTIN/UPC | Recommended (effectively required for new items) | Without a valid 12–14 digit GTIN, items fall back to `MP_ITEM_MATCH` flow which has a much higher rejection rate. Required if Walmart already has a catalog match — without GTIN you cannot share that match and lose the established LQS. |
| keyFeatures (3–5 bullets) | Recommended | Each missing bullet costs ~3 LQS points. Format: 3–10 bullets, 80 char max each, no all-caps, no marketing claims like "Best" or "#1." Ranks 2nd highest content lever after shortDescription. |
| longDescription | Recommended | Missing = ~5 LQS points lost. 1000–4000 chars recommended, basic HTML allowed (`<p>`, `<br>`, `<ul>`, `<li>`, `<b>`). First 200 chars surface in some grid views — front-load the value prop. |
| shelfName (4-level category) | Recommended | Wrong/missing shelf = item buried in Walmart search and excluded from category browse. Must be all 4 levels: e.g., `Home > Patio & Garden > Lawn Care > Grass Seed`. Mis-shelved items cannot appear in seasonal "Spring Lawn" merchandising slots. |

### Field-level format notes

- **productName:** Walmart's tokenizer indexes the first 75 chars heavily — put species/mix name and weight there.
- **shortDescription / longDescription:** strip emojis, em-dashes inside HTML attrs, and curly quotes — they cause feed validation warnings.
- **Image URLs:** must return `Content-Type: image/jpeg` or `image/png`. Walmart's CDN crawler does not follow 301 redirects on image URLs > 1 hop.
- **keyFeatures:** Walmart parses the first 5 bullets into the "Highlights" panel; bullets 6–10 only appear in the full description.
- **GTIN:** must validate against the Mod-10 checksum. If a SKU has no real GTIN, do NOT fabricate one — apply for a Walmart GTIN exemption per brand.

## Known Failure Modes

### All 200 products missing shortDescription and mainImageUrl (current — quality score 0)
**Symptom:** quality_score = 0 in benchmark.json, 200/200 products flagged as incomplete  
**Cause:** The `shortDescription` and `main_image_url` fields are required by `get_required_fields()` in the Walmart adapter, and the live Walmart API is returning empty strings for both fields on all 200 products.  
**Impact:** With both fields missing, every listing's LQS is capped near 40 — well below the 60-point "Good" threshold. Walmart deprioritizes these items in search ranking, blocks them from Buy Box wins against any other seller, excludes them from "Sponsored Products" auctions, and at peak-season the algorithm will quietly de-list low-LQS Lawn & Garden items in favor of richer competitor listings. Items remain `PUBLISHED` but are effectively invisible.  
**Fix:** Populate shortDescription and mainImageUrl via MP_MAINTENANCE feed for all 200 SKUs. Use the existing WC `short_description` and `images[0].src` per SKU as the source of truth. Submit in batches of 1000 via `POST /v3/feeds?feedType=MP_MAINTENANCE` and poll `/v3/feeds/{feedId}` until `feedStatus=PROCESSED`.

### 191 stock drift items (WC: onbackorder → Walmart: outofstock)
**Symptom:** drift_score = 0, 191/200 products show stock_status mismatch  
**Cause:** WooCommerce uses `onbackorder` for items with backorder enabled; Walmart adapter maps anything that isn't `instock` to `outofstock`. The drift checker compares WC `onbackorder` vs Walmart `outofstock`.  
**Impact:** Walmart treats `outofstock` items as Buy Box-ineligible, removes them from search relevance scoring for ~24 hours, and blocks them from any "Available to ship" filter — which is the default sort in the Lawn & Garden category. For seed customers, "out of stock" also kills the impulse purchase entirely; an `available with delay` listing converts at ~30% of an in-stock listing, but `outofstock` converts at 0%. At peak season, 191 misrepresented SKUs is a measurable revenue leak.  
**Fix:** Run `feeds/sync/sync_prices.py --push` to sync current inventory. For `onbackorder` items, decide policy: either push as `available` with a fulfillment delay note (`fulfillmentLagTime` 5–10 days, set via `walmart_lagtime_update.py`), or as `outofstock`. Recommended for seed: push backorders as `available` with `fulfillmentLagTime=7` during peak (weeks 8-18), `outofstock` off-season.

### JSONDecodeError on Walmart token endpoint (historical)
**Symptom:** JSONDecodeError when fetching auth token  
**Cause:** Missing `Accept: application/json` header — Walmart returns XML by default  
**Fix:** Fixed in walmart.py — `_get_token()` includes `"Accept": "application/json"` header.

### Items stuck in STAGE (lifecycleStatus=ACTIVE, publishedStatus=STAGE)
**Symptom:** Items submitted via feed never reach `PUBLISHED`; appear in `GET /v3/items?lifecycleStatus=UNPUBLISHED` with reason codes.  
**Cause:** Most common reasons in order of frequency: (1) `IMAGE_QUALITY_FAILURE` — image < 1000px on long edge, non-white background, or watermark; (2) `MISSING_REQUIRED_ATTRIBUTE` — shelf-specific required attribute (e.g., `seedType`, `coverageArea` for Grass Seed shelf) missing; (3) `PRICE_LEADERSHIP_VIOLATION` — Walmart price > naturesseed.com price; (4) `BRAND_MISMATCH` — brand string doesn't match Walmart's brand registry; (5) `TRUST_AND_SAFETY_REVIEW` — flagged for manual review (most often hits agricultural/chemical adjacent items).  
**Fix:** Pull `GET /v3/items?lifecycleStatus=UNPUBLISHED` and inspect `unpublishedReasons` array per SKU. Resolve top-3 reasons via MP_MAINTENANCE feed. Re-submission auto-clears STAGE within ~6 hours of next ingest.

### Image rejected silently with no STAGE flag
**Symptom:** `mainImageUrl` populated in feed, but `GET /v3/items/{sku}` returns empty `mainImageUrl`. No unpublishedReason given.  
**Cause:** Walmart's image CDN crawler couldn't fetch the URL: 4xx response, > 5MB file, redirected > 1 hop, or non-public (Cloudflare bot challenge). Cloudflare Bot Fight Mode on `naturesseed.com/wp-content/uploads/...` blocks Walmart's crawler the same way it blocks our WC API calls.  
**Fix:** Host marketplace images at a CF-cacheable subpath excluded from Bot Fight (e.g., `cdn.naturesseed.com/marketplace/`) or push to a dedicated CDN bucket. Verify with `curl -A "WalmartImageBot" -I {url}` returning 200.

### Inventory feed accepted but quantity not reflected
**Symptom:** Feed status = `PROCESSED`, no errors, but `GET /v3/inventory?sku=X` still shows old quantity.  
**Cause:** Walmart's inventory pipeline has a 30–60 minute eventual-consistency window. Also, if `fulfillmentLagTime` is changed in the same feed without including ALL required inventory fields (sku, quantity.amount, quantity.unit, lagTime), Walmart silently keeps the old value.  
**Fix:** Always include the full inventory payload on every push, even when only changing one field. Wait 60 minutes before re-checking. Don't retry on the assumption it failed — duplicate pushes within the consistency window can cause oscillation.

## Seasonal Behavior

Walmart's Lawn & Garden category is one of the most aggressively re-ranked verticals on the platform between February and June. The algorithm surfaces seed/lawn listings based on a combination of LQS, conversion rate, and inventory depth — and the weighting shifts seasonally.

**Peak (weeks 8–18, late Feb through early May, seasonality index > 0.85):**

- LQS becomes a hard gate. Items below LQS 60 are dropped from "Spring Lawn Care" merchandised modules entirely. Items at LQS 80+ are eligible for the "Featured" carousel.
- Buy Box competition intensifies — Walmart adds 3–5 new sellers per popular seed SKU during this window. Without rich content (shortDescription, 5 keyFeatures, longDescription) a small FBM seller cannot win the Buy Box even at the lowest price.
- Search query volume on terms like `grass seed`, `wildflower seed mix`, `cover crop seed` increases ~6× over the off-season baseline. Items with `coverageArea`, `seedType`, and `usdaZone` shelf-specific attributes populated rank materially higher because Walmart's filter sidebar drives a significant share of category traffic.
- Inventory depth signal weights up: Walmart prefers listings with `quantity ≥ 50` for the Buy Box during peak. Items oscillating between `instock` and `outofstock` get penalty-scored.
- **Implication for Nature's Seed:** the current quality_score=0 state is most damaging now. Every week of the Feb–May window with empty content fields is permanently lost peak-season revenue.

**Off-season (weeks 19–7, May–February, seasonality index < 0.5):**

- Coverage matters less; Walmart de-emphasizes Lawn & Garden category entirely. Coverage_score targets relax (current 41.8% acceptable at index 0.462).
- LQS still matters because it carries forward — listings with high LQS off-season get a "tenure boost" when the algorithm re-weights for spring. **Off-season is the right window to fix content.** Catching up on shortDescription/keyFeatures in November–January is when you bank LQS for the February surge.
- Stock drift is less penalized but still erodes long-term seller rating.

**Practical cadence for Nature's Seed:**

- Now (week 18, end of peak): emergency sprint to populate shortDescription + mainImageUrl on the 200 live SKUs. Even mid-peak content fixes lift LQS within ~7 days.
- Weeks 19–35 (off-season): expand coverage from 200 → 478 SKUs, build the full keyFeatures + longDescription + shelfName matrix, audit and resolve all UNPUBLISHED items.
- Weeks 36–7: ramp inventory pushes to 6h cadence, validate price parity with WC site, rehearse the spring playbook.
- Weeks 8–18 next year: pure execution — coverage ≥ 95%, LQS ≥ 80, drift ≤ 5%.

## Improvement Checklist (ordered by impact)

- [ ] Fix 191 stock drift — run `feeds/sync/sync_prices.py --push` (immediate, no content work)
- [ ] Populate shortDescription for all 200 SKUs — biggest LQS lever, required for ranking
- [ ] Add mainImageUrl for all 200 SKUs — required field, listing can be suppressed without it
- [ ] Add 3-5 keyFeatures bullets per SKU — second biggest LQS lever
- [ ] Add GTIN/UPC to all SKUs that have it in WC meta_data
- [ ] Expand to full 478 SKU coverage — submit missing 278 SKUs via MP_ITEM feed
- [ ] Set 4-level shelfName taxonomy for all items
- [ ] Audit UNPUBLISHED items via GET /v3/items?lifecycleStatus=UNPUBLISHED and resolve suppression reasons

## How to Measure Progress

- **Primary:** `feeds/benchmark/benchmark.json` — walmart coverage_score, quality_score, drift_score week-over-week
- **Drift resolution:** drift_score 0 → 95+ after one `sync_prices.py --push` run
- **Quality baseline:** quality_score moves from 0 as shortDescription/mainImageUrl populated
- **Secondary:** Walmart Seller Center → Growth → Listing Quality Score dashboard
- **Seasonality:** Coverage score expectation is relaxed off-season (index < 0.5). At peak (weeks 8-18), target coverage_score ≥ 95.
