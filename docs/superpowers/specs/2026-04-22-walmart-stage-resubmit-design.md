# Walmart STAGE Item Re-submission Design

**Date:** 2026-04-22  
**Status:** Approved

## Goal

Re-submit all Walmart STAGE items with a correctly structured MP_ITEM feed so they are published. Previous attempt failed because we passed the raw GET response instead of the required `Orderable` + `Visible` feed schema.

## Approach

Option A — re-submit directly. No retire step needed. Walmart deduplicates by SKU, so a correctly structured MP_ITEM feed overwrites the existing STAGE item in place.

## Data Sources

| Source | Used for |
|---|---|
| `data/stage_audit.json` | List of 19 STAGE SKUs + stock info |
| `data/walmart_items.json` | Price, UPC/GTIN, productType (live Walmart data) |
| `data/seo_optimized.json` | Content: title, description, key_features, attributes |

## SKU Matching

`seo_optimized.json` uses different SKUs than the STAGE items (e.g. `PG-BUCK-50-LB-KIT` vs `PG-BUCK-5-LB`). Match by base SKU: strip `-KIT` and weight suffix, find any seo item sharing the same base prefix.

17 of 19 STAGE items have a base-SKU match. 2 items (`PB-CHM-5-LB`, `PB-CLV-10-LB`) have no seo content — use fallback Visible with `productName` only.

## Architecture

Single script: `marketplaces/walmart-optimization/resubmit_stage_items.py`

**Pure functions (unit-tested):**
- `get_base_sku(sku)` — strips weight + KIT suffix, returns base (reuse from `sku_matching.py`)
- `find_seo_content(sku, seo_items)` — matches STAGE SKU to seo content via base-SKU lookup; returns content dict or None
- `build_orderable(wm_item)` — constructs `Orderable` section from walmart_items.json entry
- `build_visible(seo_item, product_type)` — constructs `Visible` section; uses seo content when available, fallback when None

**Orchestrator:**
- `run_resubmit()` — loads data, builds all 19 payloads, submits one batch via `submit_maintenance_feed(items, feed_type="MP_ITEM")`, polls to completion, writes `data/resubmit_results.json`

## Payload Format

```json
{
  "Item": {
    "sku": "PG-BUCK-5-LB",
    "productIdentifiers": {
      "productIdType": "GTIN",
      "productId": "00021532968880"
    },
    "Orderable": {
      "price": 49.99,
      "startDate": "2020-01-01T00:00:00Z",
      "endDate": "2099-01-01T00:00:00Z",
      "fulfillmentLagTime": 2
    },
    "Visible": {
      "Grass Seeds": {
        "productName": "Nature's Seed Buckwheat Seed - 5 Lb",
        "brand": "Nature's Seed",
        "shortDescription": "<p>...</p>",
        "keyFeatures": ["Feature 1", "Feature 2", "Feature 3"],
        "isProp65WarningRequired": "No",
        "condition": "New",
        "light_needs": "Full Sun",
        "plantCategory": ["Grasses"],
        "plant_name": ["Buckwheat"],
        "netContent": {
          "productNetContentMeasure": 5.0,
          "productNetContentUnit": "Pound"
        }
      }
    }
  }
}
```

**Fallback Visible** (no seo match):
```json
{
  "Grass Seeds": {
    "productName": "...",
    "brand": "Nature's Seed",
    "isProp65WarningRequired": "No",
    "condition": "New"
  }
}
```

## Output

`data/resubmit_results.json`:
```json
{
  "feed_id": "...",
  "feed_status": "PROCESSED",
  "submitted": 19,
  "items": [
    {"sku": "PG-BUCK-5-LB", "ingestion_status": "SUCCESS", "errors": []}
  ]
}
```

Terminal summary:
```
Submitted: 19 items
  SUCCESS: 17
  ERRORS:  2  → see data/resubmit_results.json
```

## Constraints

- Reuses `submit_maintenance_feed`, `wait_for_feed` from `walmart_client.py`
- Reuses `get_base_sku` from `sku_matching.py`
- No retire step — direct re-submission only
- All 19 items in one feed (no batching needed at this volume)
- `fulfillmentLagTime: 2` hardcoded (standard for Nature's Seed)
