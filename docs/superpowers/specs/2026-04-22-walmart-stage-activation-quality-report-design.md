# Walmart STAGE Activation + Product Quality Report

**Date:** 2026-04-22  
**Status:** Approved

## Goal

1. Identify all Walmart items with `publishedStatus = STAGE`
2. Check Fishbowl inventory for each; activate those with stock > 0
3. Score every STAGE item on content completeness and quality
4. Output a report usable for ongoing product optimization

## Pipeline

Three scripts in `marketplaces/walmart-optimization/`, run in sequence:

```
stage_audit.py            →  data/stage_audit.json
activate_stage_items.py   →  data/activation_results.json
product_quality_report.py →  data/product_quality_report.md
                             data/product_quality_report.csv
```

All three reuse existing `fishbowl_client.py`, `walmart_client.py`, `sku_matching.py`.

---

## Script 1: `stage_audit.py`

**Inputs:** Walmart API (live), Fishbowl API (live)  
**Output:** `data/stage_audit.json`

**Steps:**
1. Fetch all Walmart items (paginated `GET /v3/items`), filter `publishedStatus == "STAGE"`
2. Pull Fishbowl inventory for all SKUs via existing `fishbowl_client.py`
3. Cross-reference each STAGE SKU using `sku_matching.py` (5-tier hierarchy)
4. Set `will_activate: true` if matched Fishbowl qty > 0

**Output schema per item:**
```json
{
  "sku": "NS-BLUEGRASS-5-LB",
  "productName": "Kentucky Bluegrass Seed 5 lb",
  "fishbowl_qty": 142,
  "matched_fishbowl_sku": "NS-BLUEGRASS-5-LB",
  "match_type": "direct",
  "will_activate": true
}
```

**Terminal summary:**
```
STAGE items found: 18
  Will activate (stock > 0): 12
  No stock, skipping: 6
```

---

## Script 2: `activate_stage_items.py`

**Inputs:** `data/stage_audit.json`, Walmart API (live writes)  
**Output:** `data/activation_results.json`

**Steps:**
1. Read audit, filter `will_activate: true`
2. For each item, fetch full detail via `GET /v3/items/{sku}`
3. Re-submit via `POST /v3/feeds?feedType=MP_ITEM` (triggers Walmart re-evaluation)
4. Poll feed status every 30s, timeout at 10 minutes
5. Write result per SKU including any Walmart error messages

**Output schema per item:**
```json
{
  "sku": "NS-BLUEGRASS-5-LB",
  "feed_id": "abc123",
  "status": "PROCESSED",
  "ingestion_status": "SUCCESS",
  "errors": []
}
```

**Terminal summary:**
```
Activation results: 12 submitted
  SUCCESS: 10
  ERRORS:  2  → see data/activation_results.json
```

**Note:** Items that fail activation will include Walmart's error message in `errors[]`. These errors feed into the quality report as known content gaps.

---

## Script 3: `product_quality_report.py`

**Inputs:** All STAGE items (fresh `GET /v3/items/{sku}` for full detail), `data/activation_results.json`  
**Output:** `data/product_quality_report.md`, `data/product_quality_report.csv`

**Covers all STAGE items** — regardless of stock or activation outcome.

### Completeness Check (pass/fail per field)

| Field | Required |
|---|---|
| Title | yes |
| Short description | yes |
| Long description | yes |
| Brand | yes |
| Main image | yes |
| Additional images (2+) | yes |
| Key features / bullets (3+) | yes |
| Shipping weight | yes |
| Price | yes |

### Quality Score (0–100)

| Signal | Points |
|---|---|
| Title 50–150 chars | 15 |
| Title contains species name | 10 |
| Long description > 150 words | 20 |
| 4+ images | 15 |
| 5+ bullet points | 15 |
| Bullets avg > 10 words each | 10 |
| Shipping weight present | 10 |
| Activation succeeded | 5 |

### Report Structure

**Markdown (`product_quality_report.md`):**
- Summary: total STAGE items, activated count, avg quality score
- Per-product table: SKU | Name | Stock | Activated | Completeness gaps | Quality score
- Top issues section: most common missing fields across all items

**CSV (`product_quality_report.csv`):**
- One row per SKU
- All completeness flags + quality score breakdown
- Importable to spreadsheet for sorting/filtering

---

## Constraints

- Activation is automatic — no manual review gate
- Items with `will_activate: false` (no stock) are reported on but not submitted
- Fishbowl is source of truth for inventory
- Walmart auth uses `WM_SEC.ACCESS_TOKEN` header (not `Authorization: Bearer`)
- Tokens expire in 15 min — `walmart_client.py` handles refresh
