# Pinterest Catalog — Feed Success Guide
_Last updated: 2026-04-30_

## Current Status: STUB (not yet integrated)

The Pinterest adapter is a stub — it returns an empty product list with no API connection.
This guide documents the integration path and success criteria for when Pinterest is prioritized.

`feeds/adapters/pinterest.py` currently:
- Returns `[]` from `fetch_channel_products()`
- Returns an `AdapterResult` with `error="not connected — Pinterest Catalog API not yet configured"`
- Shows up as **STUB** in the daily digest scorecard with no coverage / quality / drift data

## Build Recommendation

**Verdict: YES — build it, but in Q3 2026 (post-spring-peak), not now.**

Pinterest is the single best demographic-and-intent fit out of all the unbuilt channels for a seed company. Specifically:

- **Audience size & fit:** Pinterest has ~498M MAUs globally (~92M US). Home & Garden is a top-three vertical on the platform — gardening searches alone run ~9B/year, and "garden ideas," "raised bed," "wildflower garden," "front yard landscaping" are perennial top-100 queries. The platform skews ~76% female and 35–54 — that maps almost exactly onto the Nature's Seed Klaviyo profile (homeowner, household decision-maker, suburban/rural, aspirational planning behavior).
- **CPM / CPC vs alternatives:** Pinterest Shopping ad CPMs run **~$5–$15** in Home & Garden vs **$15–$35** on Meta and **$8–$20** on Reddit for comparable interest targeting. CPCs in seed/garden categories typically settle **$0.30–$0.80** — cheaper than Google Shopping for the same buyer at top-of-funnel intent. Conversion rate is lower than Google Shopping (intent is "planning" not "buying right now"), but the assisted-conversion contribution is the value, not last-click.
- **Organic upside (the reason this matters):** Pinterest is the only ad platform where a Product Pin can keep generating impressions for **6–12 months** after publishing — the search graph re-surfaces evergreen content seasonally without paid amplification. A "Wildflower Mix for Full Sun" pin published in April 2026 will be re-shown to next year's spring-planting cohort automatically. Meta and Reddit have effectively zero evergreen organic compounding.
- **Visual fit:** Seeds-in-bag are a weak Pinterest creative; **the planted result** (wildflower meadow, restored pasture, repaired front lawn, food plot, deer plot, pollinator strip) is exactly the aspirational lifestyle imagery that the algorithm rewards. Nature's Seed already has this imagery in the WC media library — it just isn't surfaced in product feeds yet.
- **Competition:** Lower than Meta. American Meadows, Outsidepride, and Eden Brothers have small Pinterest presences; Home Depot / Lowe's dominate generic queries but lose the niche "regional native mix / pollinator / restoration" segment that's Nature's Seed strongest territory.

**Why "Q3 2026, not now":** spring is the worst time to launch a Pinterest catalog — peak planting traffic (weeks 8–18) is mostly already over by April 30, and a brand-new account has no engagement history, so the algorithm gates impressions for ~6–8 weeks while it learns. Launch in **June–August 2026**, build organic boards through the slow season, then arrive at fall overseeding (week 32+) with a warm account, and at spring 2027 with 6 months of audience data.

**What it costs to build:** ~2 days dev for the adapter + OAuth + catalog upload, ~1 week of design time to crop top-50 SKU images to 2:3 vertical, ~$300–$500/mo test ad budget for the first 90 days. Low-risk, high-asymmetric-upside.

## What Success Looks Like (when integrated)

- **Coverage 95%+** — all 478 active WC SKUs submitted to Pinterest Catalog and accepted (rejection rate < 5%)
- **Image pass rate 100% on Pinterest spec** — every SKU has a 2:3 vertical image at ≥ 1000×1500 px (this is the single largest blocker; see Image Strategy below)
- **Quality score 90+** — all required fields populated, descriptions ≥ 100 chars (Pinterest weights description heavily for Shopping match), `google_product_category` set to `Home & Garden > Lawn & Garden > Gardening > Plants > Seeds & Bulbs`
- **Shopping ad eligibility on 95%+ of submitted items** — items pass Pinterest's automated review for Promoted Pins / Shopping campaigns (separate from catalog acceptance — items can be in catalog but not ad-eligible)
- **Drift 90+** — price/availability parity between WC and Pinterest within 24 hours
- **Organic engagement targets (post-90-day warmup):** ≥ 0.6% save rate on Product Pins (saves ÷ impressions), ≥ 0.4% outbound click rate, ≥ 5K monthly impressions per top-20 SKU
- **Paid Shopping ad ROAS** ≥ 2.0x by month 4 (warmup is real — first 60 days are cost discovery, not performance)

## Pinterest's Gardening Audience

**Demographics:** ~76% female, peak age 35–54, ~45% household income > $75K, heavy suburban + exurban skew. This is the highest-overlap audience profile of any platform vs Nature's Seed Klaviyo file (suburban homeowners, female purchase decision-maker for yard/garden, planning-driven not impulse).

**Seasonal behavior — this is the load-bearing insight for a seed company:**

Pinterest gardening engagement peaks **4–8 weeks BEFORE physical planting**, because the platform is used for *planning*, not buying. The user pins ideas in February, then buys seed in April.

| Nature's Seed Peak | WC Order Volume | Pinterest Garden Search Peak |
|--------------------|-----------------|------------------------------|
| Weeks 8–18 (mid-Feb–early May) — spring planting | Peak | **Weeks 1–10 (Jan–early March)** — planning peak, ~6 weeks earlier |
| Weeks 32–38 (Aug–mid-Sep) — fall overseeding | Secondary peak | **Weeks 26–32 (Jul–early Aug)** — planning peak |

**Implication for content cadence:**
- **December–February:** Pinterest's "what should I plant this year" search peak. **This is when product pins need to already be live and ranking.** Pinning in March is too late — users have already saved their inspiration boards and moved into purchase mode on Google/Amazon.
- **June–July:** Fall planning peak for overseeding, food plots, cover crops. Same lead-time dynamic.
- **Off-peak (Oct–Nov, May):** Slow growth months — cheap impressions, good for retargeting and brand-building.

**Practical takeaway:** Pinterest is a **lead-indicator channel**. Spending optimization should be front-loaded into the planning windows, not the buying windows. This is the opposite of Google Shopping (where you bid up *during* the buying window).

## Required Fields for Product Pins

| Field | Required? | Notes |
|-------|-----------|-------|
| `id` | Yes | Stable per-SKU identifier, max 127 chars, ASCII. Use the WC SKU. Changing it resets all engagement history on the pin. |
| `title` | Yes | Max **100 chars** (Pinterest displays first ~50 in feed). Front-load species + form factor. No promotional language ("SALE", "BEST", "FREE"), no all-caps. |
| `description` | Yes | Max **10000 chars** but Pinterest's algorithm weights the **first 500 chars** for Shopping match. Keyword-rich, full sentences. Plain text — no HTML, no emoji spam. Pinterest gives this more ranking weight than Google does. |
| `link` | Yes | Canonical product URL with `https://`. Must be `/products/<slug>` (Permalink Manager) — never `/product-category/`. Redirects and 4xx = rejection. |
| `image_link` | Yes | **Vertical 2:3 strongly preferred (1000×1500 px).** Min 600×900. Square (1:1) and horizontal images are accepted but get ~3–4x lower impression supply because they don't fit the home feed grid cleanly. **This is the single largest gating factor.** |
| `price` | Yes | Format `19.99 USD` — currency required. Must match landing page within tolerance (~2%) or item gets paused. |
| `availability` | Yes | Allowed values: `in stock`, `out of stock`, `preorder`, `backorder`. Mismatch with landing page = item paused, not just disapproved. |
| `google_product_category` | Recommended | Use `Home & Garden > Lawn & Garden > Gardening > Plants > Seeds & Bulbs` (Google taxonomy ID `2802` — Pinterest accepts the same taxonomy as GMC). Strongly affects Shopping eligibility and category-browse surfacing. |
| `additional_image_link` | Recommended | Up to 10 additional images. **Use the lifestyle / planted-result imagery here** — wildflower meadows, restored lawn beauty shots, food-plot deer photography. These don't show in feed but appear on the pin detail page and lift save rate ~2x. |
| `product_type` | Recommended | Internal taxonomy, e.g. `Grass Seed > Cool Season > Tall Fescue`. Used by Pinterest for product-group ad targeting. Up to 750 chars, ` > ` separated. |
| `brand` | Recommended | `Nature's Seed`. Helps Shopping eligibility and brand-targeting in ad campaigns. |
| `condition` | Recommended | `new` for all SKUs. |
| `gtin` / `mpn` | Recommended | If WC has them, send them. Pinterest doesn't disapprove on missing GTIN like GMC does, but it does help match products into Shopping carousels. |
| `shipping` | Optional | Account-level shipping config preferred. |
| `tax` | Optional | Account-level tax config preferred. |
| `custom_label_0` … `custom_label_4` | Optional | Use for season tags (`spring`, `fall`), region (`zone-5`), category bucket — drives campaign segmentation in Pinterest Ads Manager. |

**Title formula for seed products:** `<Species/Mix Name> – <Pack Size> Seed for <Use Case>` — example: `Northeast Wildflower Mix – 1 lb Seed for Pollinator Gardens`. Pinterest's first-50-char window is tighter than Google's first-70 — be ruthless.

## Image Strategy

**This is the make-or-break section.** Pinterest is a visual platform first, a commerce platform second. ~80% of catalog underperformance on Pinterest traces back to image format, not price or copy.

**Why 2:3 vertical (1000×1500 px) is critical:**
- Pinterest's home feed is a vertical-grid layout. 2:3 images take up 50% more pixel real estate than 1:1 squares and ~3x more than 16:9 horizontals.
- The algorithm explicitly downranks non-2:3 images in the home feed (Pinterest has stated this in their creator docs since 2022).
- Standard idea pin spec: 1000×1500. Acceptable: 600×900 minimum, 2000×3000 maximum.
- Pins taller than 2:3 (e.g. 2:5 long-form infographics) get cropped in-feed and link-clicked-out at lower rates.

**The Nature's Seed problem:** WC product images are typically 1:1 square (bag-on-white). Submitting these directly to Pinterest = ~70% of catalog underperforming.

**Three-tier image strategy when integrated:**

1. **Bag-on-white (square)** — keep for `additional_image_link`, never use as `image_link`. WC default works here.
2. **Vertical 2:3 product hero** — bag photo composited onto a vertical 1000×1500 background with seasonal/contextual styling (e.g. seed bag laid on garden soil, with planted wildflowers in the upper third). Top 50 SKUs minimum. Estimated 8–10 hr of design work for top-50.
3. **Vertical 2:3 lifestyle** — full meadow / restored lawn / food plot / pollinator garden photography, with a small product callout in the corner. Use for top-20 hero SKUs. Often performs better than (2) once the user lands on the pin detail page.

**Text overlay rules:**
- Text overlays ARE allowed on Pinterest (unlike GMC's strict no-overlay rule). In fact, light text overlay correlates with higher save rates.
- Allowed: descriptive text ("Pollinator Wildflower Mix", "Plants in Zones 4–8"), contextual cues ("Spring Planting").
- Prohibited / heavily downranked: "SALE", "BUY NOW", "%OFF", phone numbers, URLs in image, watermarks covering >10% of image area.
- Recommended: text in upper or lower third, ≤ 30% of image area, high contrast against background, sans-serif font, ≥ 60pt at 1000px width for legibility on mobile.

**Seasonal imagery:** Cycle hero images quarterly. Spring = lush green, blooming wildflowers. Summer = full meadow / mature pasture. Fall = golden grass, deer / wildlife / harvest cues. Winter = soil prep, planning context. Pinterest's algorithm rewards seasonal freshness with a temporary impression boost on re-pin.

## Integration Path

When Pinterest is prioritized, build the adapter following `feeds/adapters/google_merchant.py` pattern:

1. **Apply for Pinterest API access** at developers.pinterest.com → create app → request "Catalogs" and "Ads" scopes. Approval typically 1–3 business days for legitimate ecommerce use cases.
2. **Set up Pinterest Business account + claimed naturesseed.com domain** (required for Rich Pins and product attribution). Verify the domain via DNS TXT record or HTML meta tag.
3. **Enable Rich Pins** by adding Open Graph product markup to WC product pages (most WC SEO plugins do this; verify the validator at `developers.pinterest.com/tools/url-debugger/`). Rich Pins automatically scrape WC pages and enrich any pinned URL with live price/availability — they're free and work even without a catalog feed. Rich Pins are not a substitute for the catalog (Shopping ads require the catalog), but they improve organic-pin performance.
4. **Create a catalog in Pinterest Business Hub** (Ads → Catalogs → Create catalog). Choose "API" as the data source (not "Feed file" — API is more current and avoids the 24-hr drift problem GMC has).
5. **Replace stub adapter `feeds/adapters/pinterest.py`** with real Pinterest Catalog API v5 adapter:
   - **Auth:** OAuth 2.0 with refresh token (similar to Google OAuth refresh-token pattern). Store `PINTEREST_REFRESH_TOKEN` + `PINTEREST_CLIENT_ID` + `PINTEREST_CLIENT_SECRET` in `.env`. Pinterest access tokens last 30 days; refresh tokens last 1 year and must be rotated.
   - **Catalog endpoints:**
     - `GET /v5/catalogs` — list catalogs
     - `POST /v5/catalogs/feeds` — register a catalog data source
     - `POST /v5/catalogs/items/batch` — upload up to 1000 product items per request (recommend batches of 500)
     - `GET /v5/catalogs/items` — paginated list of submitted items (use for coverage check)
     - `GET /v5/catalogs/processing_results` — diagnostic data on accepted / rejected items (use for quality_score)
   - **Map WC fields:** `id=SKU`, `title=name` (truncated to 100 chars), `description=short_description or first 500 chars of long_description`, `link=permalink`, `image_link=vertical_2x3_variant_url` (NOT main_image_url — see Image Strategy), `price=f"{price} USD"`, `availability=in_stock if stock_status=='instock' else 'out_of_stock'`, `google_product_category="Home & Garden > Lawn & Garden > Gardening > Plants > Seeds & Bulbs"`, `brand="Nature's Seed"`, `condition="new"`.
   - **Rate limit:** Pinterest API is 1000 requests/min per token. Comfortable. Add 0.1s spacing between batches.
6. **Test coverage and quality** via the existing benchmark system. First run will likely show ~60% acceptance until vertical images are produced for the rejected SKUs.
7. **Install Pinterest Tag** on naturesseed.com (analytics + retargeting). Single JS snippet, similar to Meta pixel. Required for conversion tracking on Shopping ads.

## Known Failure Modes (when integrated)

### Image aspect ratio rejection
**Symptom:** Items submitted but flagged "low quality" or quietly suppressed in feed (no impression supply)
**Cause:** WC product images are 1:1 square; Pinterest prefers 2:3 vertical. Pinterest does not technically *reject* a 1:1 image, but it caps impression supply ~70% lower.
**Fix:** Create vertical 1000×1500 variants of top SKU images via design pass, or auto-composite via Pillow/ImageMagick. Store the URL as `image_link`, keep the square bag shot as `additional_image_link[0]`.

### "Page not crawlable" / domain not claimed
**Symptom:** Catalog uploaded, items rejected with `validation: domain_not_claimed` or `link: not_crawlable`
**Cause:** naturesseed.com hasn't been claimed in Pinterest Business Hub, or Cloudflare Bot Fight Mode blocks Pinterest's crawler user-agent
**Fix:** Claim domain via DNS TXT record (preferred over HTML meta — survives theme changes). Allowlist Pinterest's crawler (`Pinterestbot/1.0`) past Cloudflare Bot Fight Mode same way GMC's crawler is allowlisted.

### Description too short / Shopping ineligibility
**Symptom:** Items in catalog but flagged "not eligible for Shopping ads" — they appear in organic browsing but can't be promoted
**Cause:** Pinterest requires description ≥ ~100 chars and weighted keyword density to qualify for Shopping campaigns. WC `short_description` is sometimes a one-liner ("5 lb bag of bluegrass seed").
**Fix:** Adapter falls back to `description` (long) when `short_description` is < 100 chars. Truncate at 500 chars at a sentence boundary.

### Price drift / availability mismatch
**Symptom:** Items paused (not disapproved — paused) with status `out_of_stock_landing_page` or `price_mismatch`
**Cause:** Catalog feed lags WC by > 24 hr after a price/stock change
**Fix:** Run the adapter daily (or sub-daily during peak). Pinterest's API-based catalog updates within ~1 hr of upload, much faster than GMC's sheet-based 24-hr cycle. This is actually one of Pinterest's advantages over GMC.

### Repeated promotional language → disapproval
**Symptom:** Items flagged "Misleading or sensational claims" with a spike of disapprovals on a single feed run
**Cause:** WC titles or descriptions contain "BEST", "FREE SHIPPING", "SALE", "%OFF", or excessive exclamation marks (often inherited from old Klaviyo product copy)
**Fix:** Title sanitizer in the adapter — strip promotional tokens before submission. Same logic GMC adapter should already use.

## Improvement Checklist

- [ ] Make build decision: confirm Q3 2026 launch window with current ad budget priorities (target build kickoff: July 2026)
- [ ] Apply for Pinterest API access at developers.pinterest.com (1–3 day approval)
- [ ] Create / claim Pinterest Business account, verify naturesseed.com domain via DNS TXT
- [ ] Enable Rich Pins (Open Graph product markup) — free organic lift even before catalog launches
- [ ] Create vertical 2:3 (1000×1500) image variants for top 50 SKUs (~8–10 hr design)
- [ ] Build adapter following `google_merchant.py` pattern, with Pinterest API v5 + OAuth refresh-token auth
- [ ] Install Pinterest Tag on naturesseed.com for conversion tracking + retargeting
- [ ] Set up seasonal organic boards (Spring Planting, Fall Lawn Restoration, Pollinator Gardens, Food Plots, Native Wildflowers) — pin 20 products per board to seed the algorithm
- [ ] Allowlist Pinterestbot user-agent past Cloudflare Bot Fight Mode
- [ ] Run first catalog sync; expect ~60–80% acceptance rate; iterate on rejected items
- [ ] Launch test Shopping campaign at $300–$500/mo for 90 days to gather conversion data
- [ ] Sync cadence: daily during peaks (Dec–Feb planning, Jun–Aug fall planning), 2x/week off-peak

## How to Measure Progress

- **Current:** N/A — shows STUB in digest scorecard
- **After integration:** `feeds/benchmark/benchmark.json` pinterest `coverage_score` (target 95+), `quality_score` (target 90+), `drift_score` (target 90+)
- **Catalog health:** Pinterest Business Hub → Catalogs → Diagnostics — accepted vs rejected vs paused counts
- **Organic reach:** Pinterest Analytics → Audience → Impressions, saves, outbound clicks per pin / per board. Lead indicator — saves precede clicks by ~2–4 weeks.
- **Shopping ads:** Pinterest Ads Manager → Shopping campaigns → ROAS, CPC, CPM. Expect 60-day warmup before stable performance.
- **Cross-channel attribution:** GA4 → Acquisition → Pinterest source/medium. Look for assisted conversions — Pinterest's last-click ROAS will *understate* true contribution because it's a planning-window channel.
