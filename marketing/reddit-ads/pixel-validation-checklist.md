# Reddit Pixel — Validation Checklist (~15 min, run in a browser)

The pixel loader is on naturesseed.com via GTM `GTM-K8CP73`. What I **cannot** verify from the server is whether each event actually fires with the right data. This is that check. Do it before spending, and again after the CAPI sender goes live.

Tools:
- **Reddit Pixel Helper** — Chrome extension (install from the Chrome Web Store).
- **Events Manager** — Reddit Ads Manager → Events Manager (server-side view of what Reddit receives).

---

## 1. Pixel identity
- [ ] Open naturesseed.com with Pixel Helper active. Confirm exactly **one** Reddit pixel loads (two = double-counting).
- [ ] Note the Pixel ID shown. In Ads Manager → Events Manager, confirm it's the **same** pixel attached to account `t2_2d9xohhgkr`. A pixel from a different account = zero usable data.

## 2. Walk the funnel — confirm each event + its data
Visit these pages in order and watch Pixel Helper:

| Step | Page | Event | Must include |
|---|---|---|---|
| a | Home / category | `PageVisit` | — |
| b | Any product page | `ViewContent` | `itemCount`, `value`, `currency`, product `id` |
| c | Add a product to cart | `AddToCart` | `value`, `currency`, product `id` |
| d | Complete a test order | `Purchase` | `conversion_id`, `value` = order total, `currency`, `itemCount`, product `id`(s) |

- [ ] `ViewContent` fires on product pages with a **value** and **currency** (not empty).
- [ ] `AddToCart` fires on add-to-cart with value + currency.
- [ ] `Purchase` fires on the order-received page with **value = order total** and **currency**. ← most important; if value is missing you cannot optimize for or measure ROAS.

## 3. IDs must match the catalog (required for Dynamic Product Ads)
- [ ] The product `id` in `ViewContent` / `AddToCart` / `Purchase` matches the `id` column in the catalog feed — which is the **WC variation id**, not the product id.
  - Feed: https://gabenaturesseed.github.io/nature-seed-data/reddit-catalog/reddit_catalog.tsv
  - Mismatch → DPA shows wrong/no products and retargeting can't match.

## 4. Deduplication (REQUIRED before going live: the browser pixel fires Purchase too)
The CAPI sender sends `event_metadata.conversion_id = <WC order id>`. The browser Reddit Purchase tag ALSO fires, but today its Conversion ID is a randomly-generated value (a GTM custom-JS variable, `Math.random()`-based, macro 24), so it will NEVER match the server event and Reddit will DOUBLE-COUNT every sale.

Fix (GTM UI, then publish):
- [ ] Open the Reddit Pixel tag (Pixel ID `a2_ix4acqaqmq42`, GTM tag_id 129).
- [ ] Change its **Conversion ID** field from the current random-id variable to the order-id Data Layer Variable that reads `eventModel.transaction_id`. That is the SAME variable your Google Ads Purchase conversion tag uses in its **Order ID / Transaction ID** field, so the quickest way to find it is to open that Google tag and copy the variable it uses there.
- [ ] Publish the container.

Verify:
- [ ] On a test order, confirm `eventModel.transaction_id` equals the raw WC order id (e.g. `473523`), NOT a formatted order number. If it is the order number, either change the sender to use `order["number"]` or align both sides to the same value.
- [ ] After CAPI goes live, in Events Manager confirm Purchase count is about the real order count (not ~2x), and events show a Browser + Server / Deduplicated status.

## 5. Server-side confirmation
- [ ] In Events Manager, the events from steps 2–4 appear within a few minutes.
- [ ] Run the CAPI sender in test mode: `python marketing/reddit-ads/send_reddit_conversions.py --order-id <recent order> ` → the event shows under **Test Events**. Then re-run with `--live` for real.

---

## Common failures to rule out
- Purchase fires **without value** → can't optimize ROAS. Fix the GTM Purchase tag's value mapping from the dataLayer.
- content `id`s are **product ids, not variation ids** → DPA mismatch.
- Pixel fires **twice** (e.g. hardcoded + GTM) → inflated conversions.
- Pixel belongs to a **different Reddit account** → data goes nowhere useful.
- Purchase fires on page refresh of order-received → double-count; gate on first view.
