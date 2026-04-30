# Google Merchant Center — Feed Success Guide
_Last updated: 2026-04-30_

## What Success Looks Like

- **0 disapproved products** in Merchant Center → Products → Diagnostics
- **All 320+ active SKUs listed** in GMC, with coverage expected to reach **~100%** after the `mpn` field fix (2026-04-30) — coverage_score in `benchmark.json` should jump from 0 to ~100 on the next audit run
- **Quality score 95+** — all required attributes (id, title, description, link, image_link, availability, price, brand, condition) populated; `gtin` populated where available, `identifier_exists: false` set for the rest
- **Drift score 90+** (currently 37, red) — price/stock parity between WooCommerce and the GMC supplemental sheet within 24 hours
- **Shopping IS ≥ 35%** during peak (weeks 8–18) and ≥ 20% off-peak — IS is the downstream metric that confirms feed quality is paying off
- **All product clicks active in Free Listings** (organic Shopping tab) — proves products clear policy and feed-spec checks even without ad spend

## Feed Architecture Note

Nature's Seed manages GMC via a Google Sheet (supplemental feed approach). The sheet uses:
- `id` column = `gla_*` format (Google Listings & Ads offerId)
- `mpn` column = WC SKU (e.g., `WB-RM-5-LB-KIT`)
- The GMC adapter fetches products via Content API and maps `item.get("mpn")` as the WC SKU identifier

The `gla_*` prefix is the **Google Listings & Ads** WooCommerce plugin convention — when GL&A syncs WC products to GMC it generates offerIds in the format `gla_<wc_post_id>` (e.g., `gla_12345`). Because that ID is opaque from a merchant's standpoint, GL&A also writes the merchant SKU into `mpn`. Any external auditor, supplemental sheet, or BI tool that wants to join GMC → WC must key on `mpn`, not `offerId`. This is why our coverage check showed 0% until the adapter was patched.

**Primary vs supplemental:** GL&A acts as the **primary feed** (live WC product data via Content API). The Google Sheet is a **supplemental feed** that overrides specific attributes (price, GTIN, custom titles, product_type) on a per-`id` basis. Pros: easy manual overrides, no plugin code changes, copy editors can work directly in Sheets. Cons: drift risk — if WC price changes and the sheet is not refreshed, GMC ends up with a stale price (this is exactly the source of our 135-product drift). Mitigation: scheduled fetch on the Sheet (Merchant Center → Feeds → fetch schedule, daily) plus a WC → Sheet sync script if drift becomes chronic.

## Required Fields & Why They Matter

| Attribute | Required? | Disapproval trigger or impact |
|-----------|-----------|-------------------------------|
| `id` | Yes | Hard disapproval if missing or duplicate. Must be stable per-SKU; changing it resets product history (impressions, conversions, learning). Max 50 chars, ASCII only. |
| `title` | Yes | Hard disapproval if missing. Max **150 chars** (only first **~70 chars** show in most Shopping placements). Title is the single largest ranking signal — front-load species name + form factor + weight. Disapproval if it contains promotional text ("SALE", "Free Shipping", "BEST"), all-caps words >1, or foreign language vs target country. |
| `description` | Yes | Hard disapproval if missing. Max **5000 chars**. Promotional text, ALL CAPS, emoji spam, or HTML markup beyond plain line breaks all trigger disapproval. First 160–500 chars are the ones the algorithm weights for matching. |
| `link` | Yes | Hard disapproval if missing, broken (4xx/5xx), or redirected to a different domain. Must use `https://`, must be the canonical product URL — for Nature's Seed that means `/products/<slug>` (Permalink Manager), **never** `/product-category/`. |
| `image_link` | Yes | Hard disapproval if missing, returns 4xx/5xx, or violates image policy (overlays, watermarks, promotional text on image, placeholder/coming-soon). Min **100×100 px** for non-apparel; **strongly recommended ≥ 800×800 px** for Shopping ads to qualify for all surfaces. White or transparent background preferred but not required. |
| `additional_image_link` | Optional | Up to 10 extra images. No disapproval impact, but lifestyle/in-context shots correlate with higher CTR on the Shopping carousel. |
| `availability` | Yes | Hard disapproval if missing or invalid. Allowed values: `in_stock`, `out_of_stock`, `preorder`, `backorder`. Mismatch with landing page availability = **policy violation** ("Inaccurate availability") which suspends the entire account in repeated cases. |
| `price` | Yes | Hard disapproval if missing, ≤ 0, or **mismatched with landing page price** beyond a small tolerance — this is the #1 cause of "price mismatch" disapprovals. Must include currency (`19.99 USD`). Sale price uses `sale_price` + `sale_price_effective_date`. |
| `google_product_category` | Strongly recommended | Not strictly required, but missing/wrong category dramatically reduces impressions because Google can't bucket the SKU correctly. For seeds: **`Home & Garden > Lawn & Garden > Gardening > Plants > Seeds & Bulbs` (ID `2802`)**. Flowers vs grass vs cover crop are all under this node. |
| `brand` | Yes for branded items | Hard disapproval if missing **and** `gtin`/`mpn` are also missing. For Nature's Seed, brand = `Nature's Seed`. Max 70 chars. |
| `gtin` | Required when available | If the product **has** a manufacturer-assigned GTIN and the field is omitted, ranking is suppressed (sometimes silent disapproval on competitive queries). If product genuinely has no GTIN (custom blends, private-label seed mixes), set `identifier_exists: false` to avoid the suppression. Submitting a wrong/invalid GTIN = hard disapproval ("Incorrect identifier"). |
| `mpn` | Required when no GTIN | Manufacturer Part Number. For Nature's Seed this is the WC SKU. Required-with-brand if no GTIN exists. |
| `identifier_exists` | Conditional | Set to `false` for handmade/custom/private-label items with no GTIN/MPN. Without this, GMC assumes you forgot the GTIN and downranks. **Do not set `false` when the product actually has a GTIN** — that's a misrepresentation and accumulates account-quality penalties. |
| `condition` | Yes | Allowed: `new`, `refurbished`, `used`. Missing = warning, wrong value = disapproval. All Nature's Seed seed packs are `new`. |
| `product_type` | Recommended | Your internal taxonomy (e.g., `Grass Seed > Cool Season > Bluegrass`). Up to 750 chars, separated by ` > `. Strong ranking signal — Google uses it together with `google_product_category` to disambiguate. Not displayed to shoppers. |
| `shipping` | Conditional | Required if shipping isn't configured account-level. Mismatch with checkout shipping = disapproval ("Inaccurate shipping cost"). |
| `tax` | Conditional (US) | Required for US accounts unless tax is set in account settings. |

**Title formula for seed products:** `<Species/Mix Name> <Cultivar/Variety> – <Pack Size/Weight> <Form Factor> Seed | Nature's Seed` — example: `Kentucky 31 Tall Fescue – 5 lb Grass Seed | Nature's Seed`. Keep first 70 chars information-dense; brand can live in the tail.

## Known Failure Modes

### offerId vs mpn mismatch (fixed 2026-04-30)
**Symptom:** 0/478 WC SKUs matching in coverage despite 320 GMC products
**Cause:** GMC Content API returns `offerId` as `gla_*` IDs; WC SKUs live in `mpn` field
**Fix:** Adapter now uses `item.get("mpn", "") or item.get("offerId", "")`. Verify coverage in next audit run.

### 135 products with price/stock drift (drift_score = 37, red)
**Symptom:** benchmark.json shows high drift between WC and GMC
**Cause:** Prices in the Google Sheet get stale when WC prices are updated
**Impact:** Price drift > ~2% on the landing page triggers **"Mismatched value (price)"** disapprovals item-by-item; ≥ 5 disapprovals of this type within 7 days escalates to **account-level warning**, and persistent inaccuracy can suspend the account under the Misrepresentation policy. Stock drift causes **"Mismatched value (availability)"** disapprovals — same escalation path. Even before disapproval, the auto-detected mismatch downranks the SKU on Shopping until Google re-crawls and confirms parity (typically 24–72 hr).
**Fix:** Update the Google Sheet when WC prices change. Set Merchant Center sheet refresh to daily, or build a WC → Sheet sync (cron) so the supplemental feed never lags WC by more than 24 hours.

### 16 products missing GTIN
**Symptom:** quality_score < 100 due to missing `gtin` field
**Cause:** 16 products don't have GTIN populated in the Google Sheet
**Options:** (a) Add GTIN to the sheet for those SKUs, or (b) add `identifier_exists: false` as a feed attribute
**Impact:** Without `gtin` **and** without `identifier_exists: false`, Google assumes the field was forgotten and applies a silent ranking penalty — items still serve, but at lower bid efficiency and reduced impression share on competitive queries. Setting `identifier_exists: false` removes the penalty for genuinely brand-only SKUs (Nature's Seed custom mixes qualify because they're a private-label blend, not a UPC-coded retail product). Submitting an **invalid** GTIN is worse than missing — that's a hard disapproval ("Incorrect identifier") and trips account-quality flags.

### Image policy disapprovals
**Symptom:** Item-level disapproval "Promotional overlay on image" or "Image too small"
**Cause:** Product images contain "SALE %" badges, watermarks, "Bestseller" stickers, multi-product collages, or fall below the 100×100 minimum (250×250 for apparel). Sometimes triggered by images that come back as 4xx during Google's crawl (CDN throttling counts).
**Impact:** Item drops out of Shopping ads and Free Listings entirely until a clean image is submitted and re-crawled (24–72 hr). Repeated violations escalate to account warnings.
**Fix:** Use clean white-or-transparent backgrounds, ≥ 800×800 px, single product, no overlays. Lifestyle/garden-bed shots go in `additional_image_link`, never `image_link`.

### Landing-page text/policy mismatch
**Symptom:** "Inaccurate availability" or "Insufficient information" disapproval
**Cause:** GMC crawler hits the `link` URL and either (a) can't find a price/availability on the page, (b) sees a "Sold out" badge while feed says `in_stock`, or (c) the page redirects to a category/home page (the `/product-category/` mistake). Cloudflare bot blocking can also cause "page not crawlable" disapprovals — Google's crawler must be allowlisted.
**Impact:** Item-level disapproval. If a large share of the catalog hits this, the whole account can be flagged for Misrepresentation review.
**Fix:** Confirm `link` resolves to `/products/<slug>`, page renders price + add-to-cart server-side (not behind JS that the bot can't run), and Cloudflare Bot Fight Mode does not block the GMC crawler user-agent.

## Seasonal Behavior

Nature's Seed Shopping IS follows a strong seasonal arc tied to the spring planting window:

- **Weeks 1–7 (Jan–mid-Feb):** Low intent, low competition. IS often runs 40–55%. Cheap clicks; good window to test title and image changes.
- **Weeks 8–18 (mid-Feb–early May):** **Peak planting season.** Search volume on grass/wildflower/pasture queries explodes. Competing seed retailers (Outsidepride, American Meadows, Eden Brothers, Hancock) and big-box feed-overlap (Home Depot, Lowe's, Tractor Supply via GMC) all bid up. **IS index peaks around weeks 11–12** and feed quality directly determines whether you get displaced — Google preferentially serves merchants with clean feeds (no disapprovals, fresh pricing, complete attributes) when impression supply is constrained. A drift_score of 37 going into peak is a major risk; expect 10–20% IS loss vs cleaner competitors.
- **Weeks 19–30 (May–July):** IS recovers as planting demand tapers. Cover crop and pasture-mix queries hold up.
- **Weeks 31–42 (Aug–mid-Oct):** Secondary peak — fall overseeding, food plots (deer/wildlife mixes), winter cover crops. Smaller than spring peak but same dynamic: feed quality determines who survives the bid-up.
- **Weeks 43–52 (Nov–Dec):** Off-season. Use the lull to clean disapprovals, refresh GTINs, restructure titles, and rebuild the Sheet sync.

**Practical implication:** any feed cleanup work has to be done **before week 8**. Trying to fix drift or repopulate GTINs mid-peak loses 24–72 hr of re-crawl latency at the worst possible time.

## Improvement Checklist (ordered by impact)

- [ ] Verify mpn fix brings coverage to ~100% in next audit run (2026-04-30+)
- [ ] Fix 135 price/stock drift items — update Google Sheet prices to match current WC prices
- [ ] Populate GTIN for 16 missing items in Google Sheet OR add `identifier_exists: false`
- [ ] Optimize titles for top 50 SKUs (keyword-front-loaded: species name + weight + "Seed")
- [ ] Add `product_type` (4-level taxonomy) to all items in sheet
- [ ] Audit disapproved products in Merchant Center → Products → Diagnostics
- [ ] Add `lifestyle_image_link` for top 20 SKUs
- [ ] Confirm `google_product_category` = `2802` (Seeds & Bulbs) on every SKU
- [ ] Set Sheet auto-fetch to daily and add a WC→Sheet drift-sync script
- [ ] Verify GMC crawler user-agent is allowlisted past Cloudflare Bot Fight Mode

## How to Measure Progress

- **Primary:** `feeds/benchmark/benchmark.json` — google_merchant coverage_score (target ~100 after mpn fix), quality_score (target 95+), drift_score (currently 37 → target 90+)
- **Secondary:** Merchant Center → Products → Diagnostics tab (disapprovals, warnings)
- **Shopping performance:** Impression Share from Google Ads → Campaigns → Competitive metrics
- **Free Listings:** Merchant Center → Performance → Free listings tab — confirms the same SKUs are clearing organic Shopping (same feed-quality signals as paid; if Free Listings clicks drop, paid IS will follow within ~7 days)
- **Account health:** Merchant Center → Account issues — any account-level warning here is a higher priority than per-item disapprovals because it caps the entire feed
