# Shopper Approved — Feed Success Guide
_Last updated: 2026-04-30_

## What Success Looks Like

Concrete targets for Nature's Seed on Shopper Approved (review collection + Google seller ratings):

- **Site-wide seller rating:** maintain ≥ 4.5 stars (current store rating drives the orange star annotation in Google Ads + organic Shopping). Below 3.5 stars or below 100 reviews/yr disqualifies the account from Google Seller Ratings entirely.
- **Google Seller Ratings eligibility:** ≥ **150 verified merchant reviews collected in the trailing 12 months** (Google's published threshold) AND average ≥ 3.5 stars. SA syndicates merchant reviews to Google automatically once SA is whitelisted as a Google review partner — no merchant action required after the initial setup.
- **Google Shopping product rich snippets:** ≥ **50 product reviews** on a single GTIN within the last 36 months AND ≥ 3 reviews on the matched product before stars surface in Shopping search. SA pushes product reviews via the Google Product Reviews feed (the `shopper-approved/generate_review_feed.py` script in this repo).
- **Coverage (live audit):** 99 (474/478 products in SA). Hold ≥ 95 — drops below indicate adapter SKU-mapping regressions.
- **Quality:** 100 — the only required fields are `sku` (parsed from `product_id`) and `name` (from `product`). Holding 100 is trivial as long as SA returns non-empty values.
- **Review collection rate:** target ≥ **8% of orders** producing a review (SA platform average is 5–7% with default settings; >10% is achievable with SMS + 30-day delay). Currently unknown — needs measurement post-Klaviyo reconnect.
- **Active integrations:** SA → Klaviyo review request flow live; SA → Google Seller Ratings active; SA → Google Product Reviews feed (XML) updated daily via `generate_review_feed.py`.
- **Top-50 SKU coverage:** every SKU in the top-50 by revenue has ≥ 5 product reviews. TURF-JBR (Jimmy Blue Ribbon, top seller since July 2025) currently has **0 reviews** — remediate via the manual SA batch request after the Klaviyo flow is reconnected.

## What SA Measures (not a product catalog)

SA is a review collection and display platform, not a product content feed. The feed adapter
tracks which products have review data (coverage) and completeness of review records (quality).
Discovery channel — no price/stock drift tracked.

Required fields from the SA API: `sku` (from product_id) and `name` (from product field).

## product_id Field Clarification

In Shopper Approved's `/products/reviews/{site_id}` API, **`product_id` is the merchant-supplied
identifier that was passed to SA at the moment of review collection** — it is **not** an SA-internal
auto-incrementing ID, and it is **not** the product URL. SA records whatever string the merchant
sends in the `product` parameter on the review-request URL or post-purchase pixel.

For Nature's Seed historically, that value has been the **WooCommerce SKU** (parent or variation),
which is why `feeds/adapters/shopper_approved.py` uses `review.get("product_id", "")` as the
coverage key. However, three practical complications surface in the data:

1. **Mixed parent vs. variation SKUs.** Reviews collected before SKU consolidation use variation
   SKUs (e.g. `S-FEOV-10-LB`, `TURF-BR-2000-F`) while newer reviews use the parent SKU
   (`PG-FEOV`, `TURF-W-BR`). The `extract_parent_sku()` helper in
   `shopper-approved/generate_review_feed.py` strips suffixes like `-10-LB`, `-2000-F`, `-KIT`,
   `-N` to normalize back to the parent.
2. **Legacy / deprecated SKUs.** Old SKUs that no longer exist in WC (e.g. `PB-MWPB`, `TURF-NW`)
   are remapped via the hard-coded `ALIASES` dict in `generate_review_feed.py`. There are ~140
   alias entries — these reviews still count for coverage but point to the consolidated WC page.
3. **Site reviews use `SA-A`.** Merchant-level reviews (about the store, not a product) are
   tagged with `product_id="SA-A"`. The audit adapter currently treats this as just another
   product, which slightly inflates the SKU count by 1 — harmless but worth noting.

`product_url` in the SA response is whatever URL the merchant passed at collection time (or
left blank). It is **not** authoritative — when SA→WC matching runs, the canonical URL comes
from WC's `permalink` field, not from `product_url`.

**Implication for the audit adapter:** the current coverage check is correct *as long as* the
SA `product_id` value continues to match a WC SKU (parent or variation) or appears in the
ALIASES map. If the Klaviyo reconnect (or any new review-source integration) starts pushing
product IDs in a different format (e.g. WC numeric post IDs, slugs), coverage will silently
drop. Always sanity-check post-integration: pull 10 newest reviews from SA admin and confirm
the `product_id` column matches a WC SKU.

## Known Failure Modes

### SA→Klaviyo review request disconnect (August 2025 — active)
**Symptom:** Products launched after August 2025 have 0 reviews (TURF-JBR, others)  
**Cause:** SA→Klaviyo integration was disconnected. Post-purchase review request emails stopped going out.  
**Impact:** Zero new product reviews on any post-Aug-2025 SKU. TURF-JBR has been the top seller since July 2025 and has accumulated ~9 months of orders with no review collection — that's an estimated 400-800 missed reviews on a single SKU. Site-wide review velocity drops below the 150/12-mo threshold within ~14 months of the disconnect, at which point Google Seller Ratings eligibility will lapse and the orange-star annotation will disappear from paid Shopping ads (typical CTR lift of 10-17% lost). Product pages also lose social proof — TURF-JBR's PDP shows "no reviews yet," which conversion-rate testing across the seed industry suggests reduces add-to-cart by 8-15%.  
**Fix:** Reconnect in SA Admin → Integrations → Email → Klaviyo. Verify Klaviyo API key is still valid (rotate if it was changed in the Aug 2025 outage). After reconnecting, run a manual batch request from SA Admin → Reviews → Request Reviews → Bulk Upload, targeting all order emails from the disconnect window (Aug 2025 → reconnect date). Use a 30-day post-purchase target window so reviews arrive after seed germination.

### product_id mismatch risk
**Symptom:** Coverage may show false positives if product_id ≠ WC SKU  
**Cause:** Adapter uses `review.get("product_id", "")` — if this is an SA internal ID, not WC SKU, coverage matching is wrong  
**Fix:** Verify by pulling a sample directly: `curl "https://api.shopperapproved.com/products/reviews/33157?token=$SA_API_TOKEN&limit=10&from=2026-01-01&xml=false"` and inspect the `product_id` field on each review. Confirm each value either (a) matches a WC SKU (`/wp-json/wc/v3/products?sku=<id>`), (b) matches a known alias in `shopper-approved/generate_review_feed.py::ALIASES`, or (c) reduces to a known parent SKU via `extract_parent_sku()`. If any new format appears (numeric IDs, slugs, GTINs), patch the alias map or extend `extract_parent_sku` regex; do NOT silently let unmapped IDs accumulate.

### SA always returns instock
**Symptom:** 20 "drift" items in raw adapter data (stock_status mismatch)  
**Cause:** SA review API doesn't carry real-time inventory — reflects status at time of review collection  
**Note:** This is expected and informational. SA is a reviews source; drift is not penalized (discovery channel).

### SA → Google Seller Ratings sync gap (silent)
**Symptom:** Seller-rating star annotation disappears from Google Ads despite ≥150 reviews in SA admin  
**Cause:** SA syncs to Google Customer Reviews / Google Seller Ratings via a periodic XML push. If the SA merchant-account email or the Google Merchant Center business URL changes (or the Merchant Center "Customer reviews from third parties" partner relationship lapses), the sync silently breaks. SA does not surface a sync error.  
**Fix:** In Google Merchant Center → Growth → Manage programs → Customer reviews, confirm "Shopper Approved" is listed as an active partner with status "Connected." If disconnected, raise a ticket via SA support to rebuild the partnership; Google does not allow merchants to add review partners directly. Allow 4-6 weeks for the new star count to surface in Ads.

### Review request email landing in promotions / spam
**Symptom:** SA admin shows 30%+ of review requests as "delivered, not opened"  
**Cause:** Default SA-from-domain (`reviews.shopperapproved.com`) lacks Nature's Seed DKIM/SPF alignment. Gmail filters it to Promotions tab, reducing open rate from ~35% to ~12%.  
**Fix:** Switch to "Send from your Klaviyo domain" in SA → Klaviyo integration settings. Klaviyo's `naturesseed.com` sender already has aligned DKIM/SPF/DMARC, which lifts deliverability into the Primary tab and roughly doubles review-request open rate. This is the single highest-leverage change for review velocity.

## Seasonal Behavior

Review velocity naturally spikes during and after spring planting season (weeks 8-20) as customers
plant seed and submit reviews 2-4 weeks after purchase. Off-season review count is low but the
spring backlog provides social proof for the following year. Review request timing should account
for seed germination time (typically 14-21 days) — send review request 30-45 days after purchase,
not 7 days.

## Improvement Checklist (ordered by impact)

- [ ] Reconnect SA→Klaviyo integration to resume automated review request emails
- [ ] Manually request reviews from TURF-JBR purchasers (July 2025 – August 2025) via SA admin batch request
- [ ] Verify product_id in SA API maps to WC SKU (check SA admin for product_id format)
- [ ] Target 150+ total reviews for Google seller ratings eligibility (currently unknown count)
- [ ] Optimize review request email timing to 30-45 days post-purchase (vs default 7 days)
- [ ] Target 50+ reviews on top-10 SKUs for product-level rich snippets in Google
- [ ] Switch SA→Klaviyo sender to `naturesseed.com` domain (DKIM-aligned) to escape Gmail Promotions tab
- [ ] Confirm Google Merchant Center → Customer reviews partner shows "Shopper Approved — Connected"
- [ ] Add an SMS review-request follow-up in Klaviyo (sent 7 days after the email if no review submitted) — typically lifts collection rate by 2-3 percentage points

## How to Measure Progress

- **Primary:** `feeds/benchmark/benchmark.json` — shopper_approved coverage_score, quality_score
- **Review velocity:** SA Admin → Reviews → New reviews per week (track before/after reconnection)
- **Rich snippets:** Google Search Console → Rich Results Test on product pages
- **Google seller rating:** SA Admin → Reputation → Seller Rating score and eligibility status
- **TURF-JBR specifically:** SA Admin → Products → search "TURF-JBR" → review count should climb above 0 within 30 days of Klaviyo reconnect + batch request
- **Product reviews feed health:** check `docs/reviews/product_reviews.xml` GitHub Pages timestamp, then Merchant Center → Marketing → Product reviews → Feed status (no errors, < 5% unmatched URLs)
