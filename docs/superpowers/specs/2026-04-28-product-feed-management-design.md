# Product Feed Management Agent — Design Spec
_2026-04-28_

## Overview

A unified product feed management system for Nature's Seed across 9 channels. WooCommerce is the source of truth. A daily snapshot drives per-channel audit adapters. Price + inventory sync is manual-trigger only. Content never auto-syncs — each channel maintains intentionally divergent, hand-tuned copy.

---

## Platform Inventory

| Platform | Status | Read | Write | Notes |
|---|---|---|---|---|
| WooCommerce | Active | Yes | Yes | Source of truth |
| Google Merchant Center | Active | Yes | No | Audit only; write access future |
| Amazon | Active | Yes | Partial | Drafts/content via SP-API |
| Walmart | Active | Yes | Yes | Full price, inventory, content |
| Klaviyo | Active | Yes | Yes | Campaigns, events, profiles |
| Shopper Approved | Active | Yes | Yes | XML review feed for GMC |
| Reddit | Partial | Yes | No | Transform layer; catalog upload in progress (separate agent) |
| Facebook | None | — | — | Stub — not yet integrated |
| Pinterest | None | — | — | Stub — not yet integrated |

---

## Architecture

```
WooCommerce (source of truth)
        │
        ▼
  feeds/build_feed_master.py       ← daily GH Actions cron (midnight MST)
        │
        ▼
  feeds/feed_master.json           ← WC-canonical snapshot, committed to git
        │
  ┌─────┴─────────────────────────────────────────────┐
  │  Channel Adapters (read-only audit — no writes)    │
  ├────────────────────────────────────────────────────┤
  │  adapters/google_merchant.py                       │
  │  adapters/amazon.py                                │
  │  adapters/walmart.py                               │
  │  adapters/klaviyo.py                               │
  │  adapters/shopper_approved.py                      │
  │  adapters/reddit.py                                │
  │  adapters/facebook.py        ← stub               │
  │  adapters/pinterest.py       ← stub               │
  └────────────────────────────────────────────────────┘
        │
        ▼
  feeds/digest/run_audit.py        ← calls all adapters, aggregates results
        │
        ▼
  feeds/digest/YYYY-MM-DD-feed-health.md   ← committed to git daily

        (manual trigger only)
        ▼
  feeds/sync/sync_prices.py        ← pushes price + inventory to channels
```

---

## Feed Master Data Model

`feeds/feed_master.json` — WC-canonical only. No channel-specific fields.

```json
{
  "meta": {
    "generated_at": "2026-04-28T07:00:00Z",
    "product_count": 312,
    "variation_count": 847
  },
  "products": {
    "12345": {
      "wc_id": 12345,
      "sku": "LAWN-KY31",
      "name": "Kentucky 31 Tall Fescue Grass Seed",
      "status": "publish",
      "type": "variable",
      "price": "24.99",
      "sale_price": "",
      "stock_status": "instock",
      "stock_quantity": 144,
      "categories": ["Lawn Grass Seed", "Cool Season"],
      "url": "https://www.naturesseed.com/products/kentucky-31-tall-fescue/",
      "images": ["https://...primary.jpg"],
      "gtin": "012345678901",
      "mpn": "LAWN-KY31",
      "brand": "Nature's Seed",
      "weight_lbs": 5.0,
      "short_description": "...",
      "description": "...",
      "variations": [
        {
          "variation_id": 12346,
          "sku": "LAWN-KY31-5LB",
          "price": "24.99",
          "sale_price": "",
          "stock_quantity": 72,
          "stock_status": "instock",
          "attributes": {"size": "5 lb"},
          "gtin": "012345678902",
          "weight_lbs": 5.0
        }
      ],
      "channel_skus": {
        "amazon": "B08XYZ",
        "walmart": "LAWN-KY31-5LB",
        "google_merchant": "LAWN-KY31-5LB"
      }
    }
  }
}
```

`feeds/channel_sku_map.json` — manually maintained SKU aliases per channel. Loaded by adapters to do apples-to-apples comparisons (Amazon ASINs, Walmart item IDs, etc.).

---

## Adapter Interface

All adapters inherit from `base_adapter.py` and implement three checks:

### 1. Coverage Check
Is every active WC product represented on this channel?
```
WC active SKUs: 312
Walmart listed: 257  →  55 missing (list of SKUs)
```

### 2. Price/Inventory Drift
Does the channel's price and stock match WC right now?
```
LAWN-KY31-5LB: WC $24.99 | Walmart $27.99  →  DRIFT
PAST-BLUEGRASS: WC instock | Amazon out-of-stock  →  DRIFT
```

### 3. Feed Quality / Completeness
Does each listed product meet this channel's required fields (per its SCHEMA.md)?
```
GMC: 18 products missing GTIN  →  SUPPRESSED
Amazon: 7 products bullet_points < 3  →  INCOMPLETE
Walmart: 3 products no shelf_description  →  INCOMPLETE
```

Each adapter ships with a `SCHEMA.md` that documents every required and recommended field for that channel. The quality check enforces it. Gabe does not need to memorize field specs — the adapter owns them.

---

## Daily Digest Format

`feeds/digest/YYYY-MM-DD-feed-health.md`

```markdown
# Feed Health — 2026-04-28

## Summary
| Channel          | Coverage | Drift | Quality Issues |
|------------------|----------|-------|----------------|
| Google Merchant  | 306/312  | —     | 18 GTIN gaps   |
| Amazon           | 241/312  | 3     | 7 incomplete   |
| Walmart          | 257/312  | 1     | 3 incomplete   |
| Reddit           | 312/312  | —     | —              |
| Klaviyo          | 312/312  | —     | —              |
| Shopper Approved | 298/312  | —     | —              |
| Facebook         | —        | —     | not connected  |
| Pinterest        | —        | —     | not connected  |

## Action Items
- [ ] Walmart: sync price on LAWN-KY31-5LB ($24.99 → $27.99)
- [ ] GMC: add GTIN to 18 products (list below)
- [ ] Amazon: expand bullet_points on 7 SKUs
```

Committed to git daily — git history serves as the feed changelog.

---

## Sync Layer

`feeds/sync/sync_prices.py` — manual trigger only.

- Reads `feed_master.json`
- For each active variation, pushes price + stock to:
  - Walmart (Items API)
  - Amazon (SP-API Listings)
  - GMC (Content API) — once write access is added
- Logs results to `feeds/sync/YYYY-MM-DD-sync-log.json`

Content (titles, descriptions, bullets, images) is **never** pushed by this script. Each channel's content is hand-tuned independently.

---

## Directory Structure

```
feeds/
  build_feed_master.py
  feed_master.json
  channel_sku_map.json

  adapters/
    base_adapter.py
    google_merchant.py
    google_merchant_SCHEMA.md
    amazon.py
    amazon_SCHEMA.md
    walmart.py
    walmart_SCHEMA.md
    klaviyo.py
    klaviyo_SCHEMA.md
    shopper_approved.py
    shopper_approved_SCHEMA.md
    reddit.py
    reddit_SCHEMA.md
    facebook.py               ← stub
    facebook_SCHEMA.md        ← stub
    pinterest.py              ← stub
    pinterest_SCHEMA.md       ← stub

  sync/
    sync_prices.py
    YYYY-MM-DD-sync-log.json

  digest/
    run_audit.py
    YYYY-MM-DD-feed-health.md
```

---

## Phased Rollout

### Phase 1 — Quality (build foundation)
- `build_feed_master.py` pulling full WC catalog
- All 6 active adapters with coverage + drift + quality checks
- Daily GH Actions cron + digest committed to git
- `channel_sku_map.json` populated for Amazon, Walmart, GMC
- `sync_prices.py` for Walmart + Amazon

### Phase 2 — Optimize (close quality gaps)
- Complete `SCHEMA.md` for every active channel (research full required field lists)
- Quality scores drive a content work queue per channel
- GMC write access added to sync layer when available

### Phase 3 — Expand (new channels)
- Facebook Catalog API wired up (stub → live)
- Pinterest Catalog API wired up (stub → live)
- Reddit catalog upload wired up (pending external agent feed delivery)

---

## Error Handling

- Adapter failures are caught and logged — a single channel failure does not block the digest
- Digest always generates, with `ERROR: <channel> — <reason>` in place of results for failed adapters
- Sync script logs per-SKU success/failure; does not halt on individual SKU errors

---

## Credentials Reference

All credentials in `.env` (spaces around `=`, quotes around values — parse with `line.split('=', 1)` then `.strip().strip("'\"")`).

| Channel | Env Vars |
|---|---|
| WooCommerce | `WC_CK`, `WC_CS`, `CF_WORKER_URL`, `CF_WORKER_SECRET` |
| Google Merchant | `GOOGLE_MERCHANT_CENTER_ID` + shared Google refresh token |
| Amazon | `AMAZON_REFRESH_TOKEN`, `AMAZON_CLIENT_ID`, `AMAZON_CLIENT_SECRET`, `AMAZON_MERCHANT_TOKEN` |
| Walmart | `WALMART_CLIENT_ID`, `WALMART_CLIENT_SECRET` |
| Klaviyo | `KLAVIYO_API` |
| Shopper Approved | `SA_SITE_ID`, `SA_API_TOKEN` |
| Reddit | `REDDIT_APP_ID`, `REDDIT_APP_SECRET`, `REDDIT_EVENTS_TOKEN` |
