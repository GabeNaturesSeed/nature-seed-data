# Meta/Facebook Catalog — Feed Success Guide
_Last updated: 2026-04-30_

## What Success Looks Like

Concrete targets:
- 0 rejected items in Meta Commerce Manager → Catalog → Diagnostics
- All 280+ products approved and eligible for Advantage+ Shopping / DPA
- `quality_score ≥ 95` in `feeds/benchmark/benchmark.json` (currently 88, amber)
- `coverage_score ≥ 90` (currently 91, green)
- `custom_label_0/1/2` populated for 100% of items so ad sets can slice on category, season, and price tier
- Active Dynamic Product Ads (DPA) retargeting + prospecting campaign running off the catalog
- Catalog connected to Meta Pixel + Conversions API with `content_id` matching `mpn` (WC SKU)

Current state: coverage 91 (green), quality 88 (amber — ~34 products incomplete), drift 100 (green — discovery channel, no historical drift tracked).

## Feed Architecture

Nature's Seed manages the Meta catalog via a public Google Sheet:
- Sheet ID: `12u2Uj0gHNImAQKDA1qnDUxlw4czL4DNuHbuUFqULbuU`
- Adapter fetches via CSV export URL (no Meta API auth needed)
- `mpn` column = WC SKU; `id` column = `gla_*` format offerId
- Same sheet powers Google Merchant — Meta accepts the Google Shopping spec, so a single sheet can feed both with minor field aliasing
- Meta refreshes scheduled feeds at most once per hour; daily refresh is sufficient for seasonal seed catalog

## Required Fields & Why They Matter

Meta accepts the Google Shopping feed spec, but field semantics differ slightly. Required fields cause **item rejection**; recommended fields don't reject but **suppress ad eligibility** (item won't serve in DPA / Advantage+).

| Field | Required? | What breaks without it |
|-------|-----------|------------------------|
| id | Yes | Item rejected. Must be unique, stable, ≤100 chars. Used as `content_id` for Pixel matching. |
| title | Yes | Item rejected. Max 150 chars (Meta truncates harder than Google's 150). First 65 chars are what render in mobile feed. |
| description | Yes | Item rejected. Max 9999 chars but Meta only displays ~30 chars in feed; first sentence carries all the weight. |
| availability | Yes | Item rejected. Accepted: `in stock`, `out of stock`, `available for order`, `discontinued`. Out-of-stock items are auto-paused in DPA, not rejected. |
| condition | Yes | Item rejected. Use `new` for all seed product (Meta has no "agricultural goods" condition). |
| price | Yes | Item rejected. Format `19.99 USD` (currency required). Must match landing page within 3% or Meta disapproves on policy. |
| link | Yes | Item rejected. Must resolve 200 OK, https, no redirects, must contain Pixel + match `id` via `content_ids`. NEVER use `/product-category/` URLs (use `/products/` per Permalink Manager). |
| image_link | Yes | Item rejected. Min 500x500, max 8MB, JPG/PNG. Square (1:1) preferred over Google's portrait preference. Lifestyle > pack-shot for Meta CTR. |
| brand | Yes | Item rejected. Use "Nature's Seed" verbatim — must match registered Brand in Meta Business Manager for Advantage+ Catalog Ads. |
| gtin | Recommended | Item still serves but ineligible for some Advantage+ placements; lower match rate to Meta's product graph; cannot join lookalike audiences across catalogs. Seed mixes typically have no GTIN — this is OK, leave blank rather than fake. |
| mpn | Recommended | Recommended only when no `gtin`. Adapter populates with WC SKU — good. |
| sale_price | Optional | Without it, no strikethrough pricing in ads → 10–20% lower CTR during sale periods. |
| sale_price_effective_date | Optional | Without it, sale_price applies indefinitely. Format: `YYYY-MM-DDTHH:MMZ/YYYY-MM-DDTHH:MMZ` (ISO 8601 interval). |
| custom_label_0/1/2 | Optional | Without these, ad sets cannot filter the catalog → every campaign targets all 280 SKUs equally, killing ROAS on seasonal/price-tier strategies. |
| google_product_category | Recommended | Helps Meta auto-classify; falls back to scraped landing page if absent. Use `Home & Garden > Plants > Seeds`. |
| fb_product_category | Optional | Meta's own taxonomy, only required for Facebook/Instagram **Shop** (on-platform checkout), NOT for catalog ads. Nature's Seed runs ads only → ignore. |
| additional_image_link | Recommended | Up to 20 extra images. Critical for carousel DPA ads — without it, Meta only has 1 creative angle per SKU. |

**Character limits:** title max 150 chars (aim 65 for mobile), description max 9999 chars (first ~30 chars render in feed, write punchy lead).

## Why Quality Score is 88 (Amber)

The adapter's `required_fields = ["sku","name","price","main_image_url","description","brand"]` map to sheet columns as:

| Adapter field | Sheet column | Likely cause of empty |
|---------------|--------------|-----------------------|
| sku | mpn | None — every WC product has a SKU. ✅ |
| name | title | None — title generated upstream. ✅ |
| price | price | None — pulled from WC. ✅ |
| main_image_url | **image_link** | **Most likely culprit.** Newer products without a featured image set in WC produce empty `image_link`. |
| description | **description** | Second most likely. Some WC products use only short_description; if sheet builder pulls only `description` field, empty for ~10% of catalog. |
| brand | brand | Possible — older products or imported SKUs may have empty brand attribute in WC. |

With 280 products and 88% quality, ~34 products are failing one or more required-field checks. Run a sheet audit:

```python
# Quick triage — count empties per required field
import pandas as pd
df = pd.read_csv("https://docs.google.com/spreadsheets/d/12u2Uj0gHNImAQKDA1qnDUxlw4czL4DNuHbuUFqULbuU/export?format=csv")
for col in ["image_link", "description", "brand", "title", "price", "mpn"]:
    print(col, df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum())
```

Highest-leverage fix: backfill the ~34 empty `image_link` rows by pulling featured images from WC via the API (or set a default category-level image as fallback). Single highest impact action — one query gets quality from 88 → 95+.

## Custom Label Strategy

Custom labels are free-form strings Meta uses for ad set filtering. They don't appear in ads — they're internal slicing keys. For a seasonal seed company with 478 SKUs and a price range from ~$8 to $300+, the optimal split is:

### `custom_label_0` — Product Category (taxonomy)
Use for category-level campaigns and audience segmentation. Recommended values:
- `grass-seed` — turf, pasture-grass single species
- `wildflower` — wildflower mixes
- `pasture` — pasture & forage blends
- `cover-crop` — cover crops, soil builders
- `food-plot` — wildlife food plots
- `native` — native restoration, regenerative-ag
- `accessory` — soil amendments, equipment, non-seed

This enables ad sets like "Wildflower Spring Push" to filter `custom_label_0 = wildflower` and only retarget viewers of that category.

### `custom_label_1` — Seasonal Window (when to advertise)
Use to gate DPA ad set delivery to relevant planting season. Recommended values:
- `spring` — cool-season, plant Mar–May
- `fall` — cool-season fall planting, Aug–Oct
- `summer` — warm-season grasses, plant May–Jul
- `year-round` — accessories, indoor, evergreen demand
- `dormant-seeded` — Nov–Feb dormant seeding window

Pair with Meta ad set scheduling (e.g., active Feb 1 – May 15 with `custom_label_1 IN (spring, year-round)`) to stop wasting impressions on out-of-season SKUs.

### `custom_label_2` — Price Tier (bid strategy + audience)
Use for ROAS-targeted bidding and lookalike seeds. Recommended buckets:
- `under-25` — impulse / first-purchase / cold prospecting
- `25-75` — standard residential
- `75-200` — acreage / serious gardener
- `200-plus` — pro/farm/commercial — needs higher LTV target ROAS

Higher tiers warrant separate campaigns with longer attribution windows (7-day click vs 1-day default) and lookalikes built from `Purchase` events with value > $200.

### Optional `custom_label_3` & `custom_label_4`
If extra slicing needed later: `custom_label_3` = best-seller flag (`top-20`, `top-50`, `tail`); `custom_label_4` = margin tier (`high-margin`, `standard`, `loss-leader`).

## Known Failure Modes

### Quality score 88 — ~34 products missing required fields
**Symptom:** quality_score = 88 (amber) — approximately 34 products incomplete  
**Cause:** Some products in the Google Sheet have empty `image_link`, `description`, or `brand` columns  
**Fix:** Audit the Google Sheet for empty required fields and populate missing values. Start with `image_link` (highest impact — Meta rejects items entirely without an image, while empty description/brand only suppress ad eligibility).

### sale_price_effective_date may be stale
**Symptom:** sale_price shows in Meta ads outside the intended sale period  
**Cause:** Sheet currently has `sale_price_effective_date: 2025-08-01/2026-08-01`  
**Fix:** Update date range in Google Sheet to match actual sale periods. Use ISO 8601 with timezone: `2026-08-01T00:00-0700/2027-08-01T00:00-0700`.

### Image policy disapproval — "promotional overlay"
**Symptom:** Items rejected with reason "Image contains promotional content / overlay text"  
**Cause:** Meta automatically rejects images with text overlays >20% of image area, badges ("SALE", "NEW"), watermarks, or borders. Common with seed-pack hero shots that have brand banners.  
**Fix:** Use clean lifestyle or product-only photography for `image_link`. Push branded/promo creatives into `additional_image_link` slots 2-20 — those are not policy-checked the same way for DPA. Or use Meta's Catalog Ads "image enhancements" (available 2025) to auto-strip overlays.

### Landing page mismatch — price or availability
**Symptom:** Items go from "Active" to "Rejected" with "Mismatched information" after a WC price change  
**Cause:** Meta crawls the landing page within 24h of feed update; if catalog `price` differs from landing page Schema.org `price` by more than 3%, item is rejected. Common during sale rollouts when WC sale price activates before sheet refresh.  
**Fix:** When toggling WC sale prices, re-run the sheet sync within 1 hour. Verify `<meta property="product:price:amount">` in page source matches feed price. Use `availability: in stock` only when WC stock_status = `instock` AND quantity > 0.

### Restricted goods false-positive — "agricultural / regulated"
**Symptom:** Wildflower or pasture mixes flagged "Restricted Goods — Plants & Seeds"  
**Cause:** Meta's policy has carve-outs for some plant species (cannabis, kratom, ephedra) and occasionally over-flags wildflower mixes containing species like poppy or hemp-adjacent natives.  
**Fix:** File a manual review in Commerce Manager → Account Quality → Appeal. Include link to USDA species list and a description that explicitly says "non-GMO grass and wildflower seeds for residential and agricultural planting" — avoid words like "potent," "high," or species names overlapping restricted lists.

### Currency / tax inclusion errors
**Symptom:** "Price not formatted correctly" for international viewers  
**Cause:** Meta requires currency suffix (`19.99 USD`, not `19.99` or `$19.99`).  
**Fix:** Confirm sheet `price` column always emits `<amount> USD`.

## Seasonal Behavior

Garden/seed demand on Meta is more peaked than on Google Shopping because Meta is push (interest-based) vs Google's pull (search-based). Pattern:

- **Weeks 6–18 (Feb 8 – May 4):** Spring interest surge. CPMs rise 30–50% as gardening interest goes mainstream. CTR on grass/wildflower spikes 2x baseline. Highest ROAS window of the year — go aggressive.
- **Weeks 19–31 (May–early Aug):** Summer plateau. Warm-season grasses still active; cool-season demand collapses. Pivot custom_label_1 ad sets from `spring` to `summer`.
- **Weeks 32–43 (Aug 8 – Oct 26):** Fall planting surge. Second-largest window — fall lawn renovation, food plots for hunters. Hunters/food-plot audience converts hardest weeks 36–40.
- **Weeks 44–5 (Nov–early Feb):** Off-season. Pause prospecting, keep retargeting active for accessories + dormant-seeding push (Dec–Feb in southern zones).

**Lookalike audience strategy:**
- Build 1% LAL from `Purchase` events Mar–May 2025 → activate Feb 1 2026 (12-month-prior seasonal twins convert 40% better than recency-only LALs for seasonal categories).
- Separate LAL per `custom_label_0` (wildflower buyers ≠ pasture buyers) — avoid blending seed types in one source audience.
- Build value-based LAL filtered to Purchase value > $100 for the `200-plus` and `75-200` price tiers.

**DPA retargeting windows:**
- 14-day view, 30-day click for cold viewers (long consideration cycle for $100+ seed orders)
- 7-day click for warm cart-abandoners (run aggressive — average gardener decides within a week of researching)

**Creative rotation by season:** Use `custom_label_1` to gate ad sets on/off via Meta's automated rules; pre-build all 4 seasonal ad sets in January, schedule activation, walk away.

## Improvement Checklist (ordered by impact)

- [ ] Fix quality to 95+: audit Google Sheet for empty required fields (image_link, description, brand) in the ~34 incomplete products
- [ ] Verify catalog approved in Meta Business Manager — no disapprovals, no policy holds
- [ ] Populate custom_label_0 (category), custom_label_1 (season), custom_label_2 (price tier) for all 280 products
- [ ] Update sale_price_effective_date to ISO 8601 format with current 2026–2027 date range before next sale
- [ ] Add lifestyle / additional_image_link (up to 20 per SKU) for top 20 best-sellers — biggest DPA CTR lift
- [ ] Confirm `link` column uses `/products/` not `/product-category/` (Permalink Manager rule)
- [ ] Set up DPA retargeting campaign (14d view / 30d click) keyed off `custom_label_1` season filters
- [ ] Build seasonal-twin lookalike audiences (1% LAL from Mar–May 2025 purchasers)
- [ ] Connect Meta Pixel + Conversions API; verify `content_id` parameter matches feed `id` (gla_*) on all PDPs
- [ ] Add `google_product_category: Home & Garden > Plants > Seeds` to all rows for taxonomy match
- [ ] Expand to all 478 WC SKUs (currently 280 in sheet)
- [ ] Backfill `gtin` where available (UPC on accessories/equipment); leave blank for seed mixes (no fake GTINs)

## How to Measure Progress

- **Primary:** `feeds/benchmark/benchmark.json` — facebook quality_score (target 95+), coverage_score (target 90+)
- **Catalog health:** Meta Business Manager → Commerce Manager → Catalog → Diagnostics tab (approval rate, # rejected items, # warnings)
- **Match rate:** Events Manager → Pixel → Match Quality (target ≥ 8.0/10 — confirms `content_id` ↔ feed `id` join)
- **Campaign performance:** Meta Ads Manager → DPA campaign ROAS (target ≥ 4.0x), CTR (target ≥ 1.5% in-season), CPP
- **Custom label leverage:** Ads Manager Breakdown → "Custom Label 1 (Season)" — confirm spring SKUs spending 80%+ of budget in spring window
