# Klaviyo Catalog — Feed Success Guide
_Last updated: 2026-04-30_

## What Success Looks Like

Concrete targets for a healthy Klaviyo catalog feed:

- All 478 WC SKUs present in Klaviyo catalog (`coverage_score >= 95`)
- Zero items missing required fields: `external_id`, `title`, `price`, `image_full_url`, `url`, `published` (`quality_score = 100`)
- Klaviyo `price` and `inventory_quantity` match WC within 24 hours of any change (`drift_score >= 90`)
- Back-in-stock flow firing on `availability` transitions from `out of stock` to `in stock`
- Browse abandonment flow rendering correct prices and live stock status in email
- API revision pinned to `2024-07-15`; account `H627hn`

**Current state (2026-04-30 audit):**

| Score | Value | Status |
|-------|-------|--------|
| Coverage | 99 (474/478) | green |
| Quality | 100 (0 incomplete items) | green |
| Drift | 0 (401 drifted items) | red |

The drift score is the only red signal. Coverage and quality are solid; the catalog exists in Klaviyo and every item has the required fields, but **84% of items have stale price or stock data**. This is the bottleneck for revenue from browse abandonment, back-in-stock, and product recommendation blocks.

## How Klaviyo Uses the Catalog

The catalog feeds three revenue-critical surfaces. Each depends on a different subset of fields, so a single bad field can degrade one flow while leaving others working.

### 1. Browse Abandonment Flow
**Trigger:** `Viewed Product` event (fired from Klaviyo's onsite tracking snippet on naturesseed.com)
**Catalog fields used:** `title`, `price`, `image_full_url`, `url`, `published`, `description`
**Behavior:** When a profile views a product page and doesn't purchase within ~30 minutes, Klaviyo fires the flow. The email's product block looks up the catalog item by `external_id` (= WC SKU) and renders a card with the cataloged price/image/title — **not** the price that was on-site at view time. If the catalog price is stale, the email shows the stale price.

### 2. Back-in-Stock Flow
**Trigger:** Profile clicks "Notify me when available" → `Subscribed to Back in Stock` event. Flow then waits for an `availability` transition on the matching catalog item from out-of-stock to in-stock.
**Catalog fields used:** `external_id`, `inventory_quantity`, `availability` (or the `published` toggle as proxy in some integrations), `title`, `image_full_url`, `url`
**Behavior:** The `availability` field on the catalog item is the **only** signal Klaviyo watches for restock. If the WC stock changes but the catalog item is not re-pushed, the flow never fires. This is the single largest drift-cost surface for a seasonal seed business.

### 3. Campaign Product Blocks (Product Feed / Recommendations)
**Catalog fields used:** `title`, `price`, `image_full_url`, `url`, `description`, `categories`, `published`, plus engagement signals (Viewed Product / Placed Order events tied to `external_id`)
**Behavior:** Klaviyo's recommendation engine blends catalog metadata with profile-level event history (Viewed Product, Placed Order, Started Checkout) to pick items per recipient. Items where `published = false` are excluded from recommendations entirely; items missing `image_full_url` are skipped silently in the rendered block.

## Required Fields & Why They Matter

| Field | Required? | What breaks without it |
|-------|-----------|------------------------|
| `external_id` (= WC SKU) | Yes | Klaviyo cannot dedupe on update → duplicate items; Viewed Product / Placed Order events cannot match a catalog item, so browse abandonment and recommendations will not render the product. |
| `title` | Yes | Empty product name in email; many ESP clients render the row blank, others show "Untitled" — both kill CTR. |
| `price` | Yes | Klaviyo rejects the create call (422). Even a `0` price is technically accepted, but `0` triggers Klaviyo's "free product" filtering in some flow conditions. |
| `image_full_url` | Yes | Product block renders as a text-only row. In recommendation blocks, the entire row is silently dropped, so a 4-up grid becomes 3-up with no warning. |
| `url` | Yes | "Shop now" / image links resolve to your Klaviyo account default redirect or 404. Conversion tracking is broken because the click hits no real URL. |
| `published` | Yes | Defaults to `true`. Set `false` to hide an item from all flows and recommendations without deleting it (use this for seasonally retired SKUs). |
| `description` | Recommended | Used by the recommendation engine to compute item similarity and shown in some default email templates. Missing description weakens cross-sell relevance. |
| `categories` | Recommended | Required to use category-scoped product blocks and "recommend from same category" logic. |
| `inventory_quantity` / `availability` | Required for back-in-stock | Without these, back-in-stock flow has nothing to watch. |

**Format requirements:**
- `image_full_url` — must be HTTPS, publicly fetchable, ideally **600×600 minimum** (Klaviyo will not upscale; small images render blurry on retina). PNG or JPG; avoid WEBP — some email clients still don't render it.
- `url` — must be HTTPS, must resolve directly to a product page (NOT `/product-category/`; Nature's Seed uses `/products/<slug>` via Permalink Manager). Append UTM tags so click-through revenue is attributable.
- `price` — decimal string (e.g., `"24.99"`), no currency symbol, no thousands separator. Currency is set per-feed at the catalog level.
- `external_id` — string, must be globally unique per catalog. WC SKU is the canonical choice; never reuse.

## Catalog Variants vs Catalog Items

Klaviyo supports two shapes:

- **Catalog Item** = a top-level product (e.g., "Pollinator Wildflower Mix")
- **Catalog Variant** = a child of a parent item (e.g., 1lb / 5lb / 25lb of that mix)

**Why variants exist:** Browse abandonment, back-in-stock, and recommendations roll up at the parent item level. With variants, a customer who viewed the 5lb bag can be re-targeted with a card that links to the parent product page and shows "from $X" pricing, while back-in-stock alerts can fire on any single variant returning. Without variants, each pack size is a separate product card — three near-duplicate items competing in recommendation blocks.

**Nature's Seed today:** Each WC SKU is pushed as a separate top-level catalog item. With ~478 SKUs and many products having 2–4 size variants, this means recommendation blocks routinely show two pack sizes of the same blend side-by-side, and back-in-stock alerts fire per-pack-size instead of per-product.

**Recommended migration (post-drift fix):**
- Keep current single-item shape until drift is resolved (don't restructure a stale catalog).
- Then group by WC parent product ID: parent → catalog item, each WC variation SKU → catalog variant.
- Use the variant's `external_id` = WC SKU; parent's `external_id` = WC parent product ID prefixed (e.g., `parent-12345`) to avoid colliding with SKU namespace.
- Net effect: ~150–180 catalog items + ~478 variants instead of 478 items. Cleaner recommendations, single back-in-stock event per blend.

## Known Failure Modes

### Bracket encoding error (fixed b9e8114)
**Symptom:** `400 Bad Request for url: .../catalog-items?page%5Bsize%5D=100`
**Cause:** Python `requests` library percent-encodes `page[size]` → `page%5Bsize%5D`, which Klaviyo rejects.
**Fix:** Build URL string manually: `url = f"{KLAVIYO_BASE}/catalog-items?page[size]=100"`. Fixed in b9e8114.

### 401 drifted catalog items (drift_score = 0, red — current)
**Symptom:** `benchmark.json` shows 401/474 items have price or stock mismatch between WC and Klaviyo.
**Cause:** Klaviyo catalog is not automatically synced when WC prices or stock change. The native Klaviyo–WooCommerce integration syncs on a polling interval (typically 6–24h depending on plan tier and account size) and silently skips items where it cannot reconcile SKU mappings. Manual price/stock changes in WC admin do not push immediately.
**Impact:**
- **Browse abandonment emails show stale prices.** A customer who viewed a product at the new $29.99 sale price gets an email rendering the old $34.99 catalog price. CTR on incorrect-price emails drops 30–50% (industry benchmark) and on the click-through they see a different price than the email — measurable bounce.
- **Out-of-stock items keep selling in email.** Items WC has flipped to OOS still render `availability: in stock` in Klaviyo; product blocks send paying clicks to OOS PDPs. Conversion lost outright.
- **Back-in-stock flow misfires or no-fires.** If WC restocks a SKU but Klaviyo still shows it as in-stock (because the original OOS push never landed), the flow never sees a transition, and subscribers don't get notified — the entire BIS flow's opt-in list silently expires.
- **Recommendation engine bias.** Stale items with stale prices keep getting recommended, including items that may be retired. Revenue attribution gets noisy.
- **Estimated revenue cost:** at 84% drift on a catalog tied to 3 active flows (browse abandonment, BIS, weekly campaign with product block), expect 15–25% degradation on flow-attributed revenue vs. a clean catalog.

**Fix:**
1. **Short-term (this week):** Run a one-shot full re-push of all 478 SKUs via the catalog-items bulk update endpoint. Pull current WC product list with prices + stock, transform to Klaviyo catalog payload, PATCH each item by `external_id`. Use the bulk-job endpoint (`/catalog-item-bulk-update-jobs`) to avoid per-item rate limits.
2. **Medium-term:** Add a nightly GitHub Actions job that diffs WC vs Klaviyo and patches only changed items. Bound it to drift_score > 80 as a guardrail.
3. **Long-term:** Move to webhook-driven sync — fire a Klaviyo PATCH on WC `product.update` and `product.stock.change` webhooks via the CF Worker. Eliminates polling lag entirely.

### Soft 422 on missing `image_full_url`
**Symptom:** Catalog item create returns 200 but item shows up "Incomplete" in Klaviyo UI; never appears in product blocks.
**Cause:** Klaviyo accepts items with empty/null `image_full_url` but flags them internally as unrenderable. They count toward catalog total but are silently dropped from emails.
**Fix:** Treat missing `image_full_url` as a hard validation error in the adapter — refuse to push the item until WC has a featured image. Log to `feeds/benchmark/quality_issues.json` so they show up in the audit.

### `published: false` items still appearing in flows
**Symptom:** A retired SKU keeps showing up in "Recently Viewed" product blocks even after `published` is set to false.
**Cause:** `published: false` blocks recommendation/feed selection, but does NOT retroactively scrub the item from already-rendered Viewed Product event history. If a profile viewed the item before retirement, it can still appear in personalized blocks for ~30 days until events age out.
**Fix:** For SKUs being permanently retired, also DELETE the catalog item via API (not just unpublish), and add a flow filter `Viewed Product within last 30 days = false for {SKU}` if the item is part of a critical recovery flow.

## Seasonal Behavior

Nature's Seed catalog accuracy matters more during peak weeks because that's when emails do the heaviest lifting.

- **Weeks 8–18 (late Feb through early May, spring planting):** Highest browse abandonment volume of the year. A stale price on the 10 best-selling grass blends costs more in lost revenue here than in the entire low season. Catalog should be re-synced **at least every 24 hours**, ideally every 6 hours during weeks 10–14.
- **Weeks 32–38 (Aug–Sept fall planting + restock cycle):** Back-in-stock flow becomes the dominant catalog-driven flow. Many spring SKUs that went OOS in April come back. Every restock missed in the catalog = a cohort of opted-in subscribers who never get notified. Verify `availability` transitions are pushing during this window.
- **Weeks 45–52 (Nov–Dec):** Cover crop and food plot restocks. Lower volume but high AOV — back-in-stock alerts on premium mixes are revenue-significant per subscriber.
- **Low season (weeks 25–31, 39–44):** Daily sync is sufficient. Use the off-peak window to do structural work (e.g., variant migration) without risking peak-season disruption.

**Practical rule:** during peak weeks, treat drift_score < 80 as a P1 incident — it directly throttles the highest-revenue flows of the quarter.

## Improvement Checklist (ordered by impact)

- [ ] **Resolve 401 price/stock drift items** — run full re-push via `/catalog-item-bulk-update-jobs` against current WC prices + stock. Target drift_score >= 90 within 48 hours.
- [ ] Verify bracket encoding fix (b9e8114) is holding in latest audit run; confirm `coverage_score = 99` is stable.
- [ ] Confirm the 4 missing SKUs (478 - 474) are intentional — likely OOS-retired or staff-only; document in `feeds/benchmark/known_exclusions.json`.
- [ ] Set up back-in-stock flow for top 20 currently OOS SKUs; verify the `availability` transition fires test events end-to-end.
- [ ] Add UTM parameters to all catalog `url` values (`?utm_source=klaviyo&utm_medium=email&utm_campaign={{flow_name}}`) so flow revenue is attributable in GA4.
- [ ] Add nightly drift check to GitHub Actions; alert if drift_score drops below 80.
- [ ] Migrate to catalog variants for size-variable products (1lb / 5lb / 25lb) — execute during low season (weeks 25–31).
- [ ] Move sync to webhook-driven via CF Worker on WC `product.update` / `product.stock.change` events.

## How to Measure Progress

- **Primary:** `feeds/benchmark/benchmark.json` — `klaviyo.drift_score` (currently 0 → target 90+ within 7 days, 95+ steady-state)
- **Secondary:** Klaviyo UI → Catalog → Items tab. Check item count (target 474+), "Last synced" timestamp (target < 24h), and the "Incomplete" filter (target 0).
- **Revenue signal:** Klaviyo → Analytics → Flows → Browse Abandonment / Back in Stock. Watch flow-attributed Placed Order (metric `VLbLXB`) revenue trend after drift fix; expect lift of 15–25% within two cycles.
- **Back-in-stock health:** Count of "Subscribed to Back in Stock" → "Placed Order" conversions per week. Should rise sharply after drift fix during weeks 32–38.
- **Catalog freshness audit:** weekly diff of WC product list vs Klaviyo catalog items; log count of price/stock mismatches to `feeds/benchmark/klaviyo_drift_history.json`.
