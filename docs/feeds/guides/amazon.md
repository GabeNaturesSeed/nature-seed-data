# Amazon SP-API — Feed Success Guide
_Last updated: 2026-04-30_

## What Success Looks Like

- **Coverage:** 100% of active WC SKUs listed on Amazon (~478 listings live, 0 in `INCOMPLETE` status). Baseline target in `benchmark.json` meta = 90% (accepts buffer for SKUs intentionally excluded from FBM, e.g. heavy bulk pasture mixes >40 lb).
- **Quality score:** ≥0.85. Listings have title (≤200 chars), 5 bullets, ≥4 images (1 main white-bg + 3 supporting), product description ≥1000 chars, A+ Content for top 20 revenue SKUs.
- **Suppressed listing count:** 0. Any `status: SUPPRESSED` or `INACTIVE (Search Suppressed)` in Listings API breaks discoverability — these don't appear in search even when in stock.
- **Buy Box win rate (FBM seed seller):** ≥85% — Nature's Seed brand is the only seller on its own ASINs, so loss-of-buy-box almost always = pricing error or suppression, not competition.
- **Reviews:** Top 50 SKUs target ≥10 reviews at ≥4.0 stars (review velocity matters more than absolute count for A9 ranking).
- **Current state:** ERROR — adapter returns 400 from SP-API. `AMAZON_SELLER_ID` was added to GH secrets 2026-04-29, may need one audit cycle to verify. All quality/coverage scores are `null` in `benchmark.json` until auth resolves.

## Required Fields & Why They Matter

| Field | Required? | What breaks without it |
|-------|-----------|------------------------|
| item_name (title) | Yes | Listing rejected at submission. Max 200 chars (Seeds & Plants category enforces 200; some categories cap at 80). Recommended formula: `[Brand] + [Product Type] + [Key Attribute (Coverage/Weight)] + [Use Case]` — e.g. "Nature's Seed Bermuda Grass Seed, 5 lb Bag, Covers 2,500 sq ft, Drought-Tolerant Lawn Mix". A9 indexes the title heavily. |
| brand | Yes | Without a registered Brand Registry entry, Amazon may auto-assign "Generic" — disqualifies you from A+ Content, Sponsored Brands, Vine, and brand-gated reporting. Brand must match exactly across all SKUs (Nature's Seed, not "Natures Seed" or "Nature Seed"). |
| bullet_points (5) | Yes | Listings with <5 bullets show empty whitespace and rank lower in Mobile App carousel. Each bullet ≤500 chars (recommended ≤250 for mobile). Lead each bullet with a CAPS HOOK (e.g. "DROUGHT-TOLERANT:" then benefit). |
| product_description | Recommended | Plain-text description (max 2000 chars) is replaced by A+ Content for Brand Registry sellers. Without either, mobile users see only bullets. Keyword indexing is weak vs. title/bullets but still a ranking input. |
| main_image | Yes | Listing is suppressed and not searchable until a compliant main image is uploaded. Must be ≥1600px on longest side (zoom requires this), pure white background (RGB 255,255,255), product fills ≥85% of frame, no text/watermarks/logos overlaid. |
| UPC/EAN | Required for ASIN matching | Without GTIN, you cannot create a new ASIN unless you have GTIN exemption. With UPC, Amazon matches your offer to an existing ASIN automatically — this is how duplicate listings get created if your title/brand differ from the existing ASIN. |
| browse_node (category) | Yes | Wrong browse node = listing buried in low-traffic category. Seeds & Plants → Lawn & Garden → Plants, Seeds & Bulbs → Seeds (browse node `3744191`) is correct for grass/wildflower/cover crop. Pasture/agricultural seed may route to `2972638011`. |
| manufacturer | Recommended | Required for Brand Registry verification. Match brand for own-brand SKUs. |
| product_dimensions / item_weight | Recommended | Required for FBA, optional for FBM but used by Amazon for shipping calculation and "frequently bought together" matching. |
| keywords (search terms) | Recommended | Backend search terms field — max 250 bytes total, no commas, no repeated words from title. Highest A9 keyword indexing weight after title. |

**Amazon-specific limits:**
- Title: 200 chars max (Seeds category), 80 recommended for desktop preview
- Bullets: 500 chars each, 5 bullets total = 2,500 chars
- Description: 2,000 chars (plain text) — superseded by A+ Content modules (up to 7 modules, 1,000 chars each)
- Backend keywords: 250 bytes total (~250 ASCII chars)
- Main image: ≥1600px longest side, JPEG/PNG, sRGB, ≤10MB
- Additional images: up to 8 more (9 total slots), 500–1600px

## Known Failure Modes

### Auth error (current — active)
**Symptom:** 400 Client Error from SP-API
**Cause:** `AMAZON_SELLER_ID` environment variable missing or incorrect in GH Actions secrets
**Fix:** Verify `AMAZON_SELLER_ID` is set as a Repository secret (not Environment secret) in GitHub. Check next audit run output. Also confirm `LWA_APP_ID`, `LWA_CLIENT_SECRET`, `SP_API_REFRESH_TOKEN`, and `SP_API_ROLE_ARN` are present and that the IAM role policy includes `execute-api:Invoke` on the SP-API endpoint. A 400 with body `{"errors":[{"code":"InvalidInput","message":"Invalid sellerId"}]}` means the seller ID is malformed (must be the 13–14 char merchant token like `A1B2C3...`, not the storefront name).

### ASIN mismatch / duplicate listing
**Symptom:** Two ASINs exist for the same physical product; one has reviews and ranks, the other is empty.
**Cause:** Amazon ASIN-matches by GTIN (UPC/EAN) **first**, then by brand+title fingerprint. If you submit a UPC that's already attached to an ASIN, Amazon merges your offer onto that ASIN regardless of your title — meaning you inherit a competitor's (or your old) title/images. If you submit *no* UPC and request GTIN exemption, Amazon creates a brand-new ASIN even if the product already exists, leading to duplicates.
**Fix:**
1. Run Catalog Items API `GET /catalog/2022-04-01/items?keywords=<SKU>&marketplaceIds=ATVPDKIKX0DER&sellerId=<your_id>` to find all ASINs tied to your seller account.
2. For duplicates: use Listings API to delete the empty/wrong ASIN (`DELETE /listings/2021-08-01/items/{sellerId}/{sku}`) and consolidate inventory on the canonical ASIN.
3. Always submit UPC when available. For private label without UPC, apply for GTIN exemption *before* listing.

### Suppressed listings
**Symptom:** Listing exists in inventory but doesn't appear in customer search; Seller Central flags "Search Suppressed" or "Quality Alert".
**Detection via SP-API:**
- `GET /listings/2021-08-01/items/{sellerId}/{sku}?marketplaceIds=ATVPDKIKX0DER&includedData=summaries,issues` — check `issues[]` array for severity `ERROR` or `WARNING`.
- Common issue codes: `90000100` (missing main image), `90000200` (title too long), `90000400` (missing required attribute), `99001` (restricted product / pesticide claim).
- Status field `summaries[0].status` containing `INCOMPLETE` or `SEARCH_SUPPRESSED` confirms suppression.
**Fix:** Resolve each listed issue, then PATCH the listing via Listings API. Suppression lifts within 15–60 minutes once issues clear.

### Stranded inventory (FBA only — informational for FBM seller)
**Symptom:** FBA inventory units exist but listing is inactive; units accrue long-term storage fees.
**Detection:** Reports API `GET_FBA_STRANDED_INVENTORY_DATA` report.
**Fix:** Either re-enable the listing or submit a removal order. Not currently relevant since Nature's Seed is FBM, but worth tracking if any test FBA units remain.

### Restricted-claim violation (HIGH RISK for seed category)
**Symptom:** Listing rejected or suppressed with code `99001` or "Restricted Products Policy Violation".
**Cause:** Amazon's pesticide/herbicide/seed policy prohibits unverified claims. Specifically banned phrases in title/bullets/description for seeds:
- "Roundup Ready", "GMO" (positive or negative claim without USDA cert)
- "Pesticide-free" or "Organic" without USDA Organic certification number on file
- "Cures", "treats", "prevents [disease]" (medical/agricultural claims)
- "EPA approved", "FIFRA registered" unless you have the registration number
- Coated seed claims (neonicotinoid, fungicide treatment) require explicit SDS upload
**Fix:** Audit copy for banned terms. For Nature's Seed, common pitfall is wildflower mix bullets claiming "attracts pollinators / bee-safe" — acceptable, but "neonic-free" requires lab certification on file. Use neutral phrasing: "untreated seed", "no chemical coating".

### Pricing error / Buy Box loss
**Symptom:** Buy Box drops to "no Buy Box winner" or competitor; sales tank overnight.
**Cause:** Listing price violates Amazon's "Fair Pricing Policy" — typically triggered when Amazon's bot finds the same product cheaper on naturesseed.com or another marketplace. Also: stockout (qty=0) auto-suppresses the offer.
**Fix:** Maintain price parity (Amazon ≥ DTC) or use Amazon-specific bundles/sizes that don't price-match. Listings API `PATCH` updates price within minutes; Buy Box re-evaluation takes 15–60 min.

## Seasonal Behavior

Amazon's A9/A10 algorithm does **not** apply explicit seasonal boosts to the Seeds & Plants category — there's no equivalent to Google Shopping's seasonality bidding hint. Instead, seasonality emerges organically through three signals:

1. **Sales velocity weighting (the dominant signal).** A9 ranks by recent conversion rate weighted heavily on the last 14–30 days. During weeks 8–18 (Feb–early May, Nature's Seed peak), seed search volume spikes 4–8× baseline. Listings that convert in that window rocket up rank; listings out of stock or with poor CTR fall to page 3+ and don't recover until the next peak.
2. **BSR (Best Sellers Rank) compounding.** BSR updates hourly within category. A SKU that hits top 100 in "Lawn & Garden > Seeds" during peak earns the "Best Seller" badge, which itself drives ~15–25% CTR lift. Push for BSR during weeks 8–14 specifically.
3. **Sponsored Products bid inflation.** CPC for "grass seed", "wildflower seeds", "cover crop seed" rises 2–3× in spring (March bid floor often $1.20–2.00 vs. $0.50–0.80 in November). Plan ad budget accordingly. Sponsored Brands and Sponsored Display see less inflation because lower competition in the category.

**Tactical implications for weeks 8–18:**
- Verify all top 50 revenue SKUs are NOT suppressed by week 6 (mid-Feb). A suppressed listing during peak loses the entire season.
- Pre-position FBM inventory so you can fulfill within Amazon's promised handling time (Amazon penalizes late shipments harder during peak — Late Shipment Rate >4% triggers account review).
- Add A+ Content to top 20 SKUs *before* week 8 — A+ Content takes 7 days for Amazon review.
- Run Vine enrollment on top 10 SKUs in November–January (off-peak) so reviews land before spring.
- BSR volatility is highest weeks 10–14 — monitor daily, not weekly.

**Off-peak (weeks 30–52):** Use this window for catalog cleanup, image refreshes, A+ Content rebuilds, and Brand Story enrollment. These changes need a "burn-in" period before A9 fully re-indexes; submit changes at least 30 days before the next peak.

## Improvement Checklist (ordered by impact)

- [ ] Verify AMAZON_SELLER_ID secret is working — check next audit run for error resolution
- [ ] Audit suppressed listings via SP-API Listings API `GET /listings/2021-08-01/items` with `includedData=issues` — fix every ERROR-severity issue before week 6
- [ ] Ensure all SKUs have 5 bullet points (equivalent to keyFeatures) — leading CAPS hook + 200–250 chars each
- [ ] Verify all SKUs have main_image on pure white background, ≥1600px longest side (enables zoom)
- [ ] Add ≥4 supporting images per top-50 SKU (lifestyle, dimensions, coverage map, infographic, application)
- [ ] Add A+ Content (Enhanced Brand Content) to top 20 SKUs by WC revenue — submit by week 6 for week 8 launch
- [ ] Map all SKUs to correct Amazon browse node (Seeds & Bulbs subcategory `3744191` for retail, `2972638011` for ag)
- [ ] Populate UPC/EAN for all SKUs (critical for ASIN matching) — request GTIN exemption only for SKUs without retail UPCs
- [ ] Audit titles for 200-char limit and Brand-First formula
- [ ] Populate backend keywords (search terms) field — 250 bytes, no title repetition, include common misspellings ("clover", "klover", "cluver")
- [ ] Audit bullets/description for restricted claims (organic, neonic-free, pesticide-free, GMO claims)
- [ ] Enroll top 50 SKUs in Brand Story (separate from A+ Content)
- [ ] Run Vine enrollment in Q4 for spring review velocity
- [ ] Set Sponsored Products bids 2–3× higher for weeks 8–18 vs. baseline

## How to Measure Progress

- **Primary:** `feeds/benchmark/benchmark.json` — `amazon.coverage_score`, `amazon.quality_score` (once auth resolved). Coverage = listed SKUs / WC active SKUs. Quality = weighted average of (title_present, bullet_count_5, main_image_compliant, description_or_aplus, browse_node_correct).
- **Secondary:** Seller Central → Inventory → "Manage All Inventory" → filter `Status: Inactive (Quality)`. Also: Account Health → Listing Quality Dashboard (lists every SKU with a quality issue and its severity).
- **Suppression check (programmatic):** Listings API `GET /listings/2021-08-01/items/{sellerId}/{sku}?marketplaceIds=ATVPDKIKX0DER&includedData=summaries,issues` — flag any SKU where `summaries[0].status` is not `BUYABLE` or where `issues[]` contains severity `ERROR`.
- **Stranded inventory (FBA, if any):** Reports API → request report type `GET_FBA_STRANDED_INVENTORY_DATA`.
- **Seasonality:** During peak (weeks 8–18), poll BSR daily for top seed categories via Catalog Items API (`includedData=salesRanks`). Track movement vs. prior year. Goal: 5 SKUs in top 100 of category, 1 in top 10 by week 12.
- **Buy Box:** Pricing API `GET /products/pricing/v0/items/{Asin}/offers` → `Summary.BuyBoxPrices` and `IsBuyBoxWinner` per offer. Should be `true` for our seller for ≥85% of own-brand ASINs.
- **Reviews:** No SP-API endpoint exposes review count directly (deprecated 2020); pull via Brand Analytics or scrape Seller Central report `GET_BRAND_ANALYTICS_REPEAT_PURCHASE_REPORT`. Target review velocity: ≥1 new review per top-50 SKU per month during peak.
