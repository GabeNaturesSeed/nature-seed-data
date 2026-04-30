# Walmart STAGE Item Re-submission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-submit all Walmart STAGE items using the correct MP_ITEM feed format (Orderable + Visible sections) so they get published.

**Architecture:** Single script `resubmit_stage_items.py` with four pure testable functions (`find_seo_content`, `build_product_identifiers`, `build_orderable`, `build_visible`) and a `run_resubmit()` orchestrator. Data comes from `data/stage_audit.json` (STAGE SKUs), `data/walmart_items.json` (price/UPC/GTIN/productType), and `data/seo_optimized.json` (content). Reuses `_parse_net_content` and `_normalize_light_needs` from `seo_optimize.py` and `get_base_sku` from `sku_matching.py`.

**Tech Stack:** Python 3, stdlib only. Existing `walmart_client.py` handles feed submission and polling.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `marketplaces/walmart-optimization/resubmit_stage_items.py` | Create | Pure functions + `run_resubmit()` orchestrator |
| `marketplaces/walmart-optimization/tests/test_resubmit.py` | Create | Unit tests for the four pure functions |

## MP_ITEM Feed Structure (per item in MPItem array)

```json
{
  "Item": {
    "sku": "PG-BUCK-5-LB",
    "productIdentifiers": {"productIdType": "GTIN", "productId": "00021532968880"},
    "Orderable": {
      "startDate": "2020-01-01T00:00:00Z",
      "endDate": "2099-01-01T00:00:00Z",
      "fulfillmentLagTime": 2,
      "price": 49.99
    },
    "Visible": {
      "Grass Seeds": {
        "productName": "...",
        "brand": "Nature's Seed",
        "shortDescription": "...",
        "keyFeatures": ["...", "..."],
        "isProp65WarningRequired": "No",
        "condition": "New",
        "light_needs": "Full Sun",
        "plantCategory": ["Grasses"],
        "plant_name": ["Buckwheat"],
        "netContent": {"productNetContentMeasure": 5.0, "productNetContentUnit": "Pound"}
      }
    }
  }
}
```

`productIdentifiers` is a top-level `Item` field. `Orderable` and `Visible` are nested sections.

---

### Task 1: Pure functions + unit tests (TDD)

**Files:**
- Create: `marketplaces/walmart-optimization/tests/test_resubmit.py`
- Create: `marketplaces/walmart-optimization/resubmit_stage_items.py`

- [ ] **Step 1: Write the failing tests**

Create `marketplaces/walmart-optimization/tests/test_resubmit.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from resubmit_stage_items import (
    find_seo_content,
    build_product_identifiers,
    build_orderable,
    build_visible,
)

SEO_ITEMS = [
    {
        "sku": "PG-BUCK-50-LB-KIT",
        "title": "Nature's Seed Buckwheat Seed - 50 Lb",
        "description": "<p>Great cover crop.</p>",
        "key_features": ["Fast germinating", "Drought tolerant"],
        "attributes": {
            "brand": "Nature's Seed",
            "light_needs": "Full Sun",
            "plantCategory": "Grasses",
            "plantName": "Buckwheat",
            "netContent": "50 lb",
            "isProp65WarningRequired": "No",
            "condition": "New",
        },
        "product_type": "Grass Seeds",
    },
]

WM_ITEM = {
    "sku": "PG-BUCK-5-LB",
    "gtin": "00021532968880",
    "upc": "021532968880",
    "price": {"currency": "USD", "amount": 49.99},
    "productType": "Grass Seeds",
    "publishedStatus": "STAGE",
}


# --- find_seo_content ---

def test_find_seo_content_base_match():
    # PG-BUCK-5-LB and PG-BUCK-50-LB-KIT share base PG-BUCK
    result = find_seo_content("PG-BUCK-5-LB", SEO_ITEMS)
    assert result is not None
    assert result["title"] == "Nature's Seed Buckwheat Seed - 50 Lb"


def test_find_seo_content_kit_variant_matches():
    result = find_seo_content("PG-BUCK-25-LB-KIT", SEO_ITEMS)
    assert result is not None


def test_find_seo_content_no_match_returns_none():
    result = find_seo_content("PB-CHM-5-LB", SEO_ITEMS)
    assert result is None


# --- build_product_identifiers ---

def test_build_product_identifiers_prefers_gtin():
    result = build_product_identifiers(WM_ITEM)
    assert result["productIdType"] == "GTIN"
    assert result["productId"] == "00021532968880"


def test_build_product_identifiers_falls_back_to_upc():
    item = dict(WM_ITEM)
    item["gtin"] = ""
    result = build_product_identifiers(item)
    assert result["productIdType"] == "UPC"
    assert result["productId"] == "021532968880"


def test_build_product_identifiers_returns_none_when_neither():
    item = dict(WM_ITEM)
    item["gtin"] = ""
    item["upc"] = ""
    result = build_product_identifiers(item)
    assert result is None


# --- build_orderable ---

def test_build_orderable_contains_required_fields():
    result = build_orderable(WM_ITEM)
    assert result["price"] == 49.99
    assert result["fulfillmentLagTime"] == 2
    assert "startDate" in result
    assert "endDate" in result


def test_build_orderable_no_price_when_missing():
    item = dict(WM_ITEM)
    item["price"] = {}
    result = build_orderable(item)
    assert "price" not in result


# --- build_visible ---

def test_build_visible_with_seo_content():
    result = build_visible(SEO_ITEMS[0], "Grass Seeds")
    section = result["Grass Seeds"]
    assert section["productName"] == "Nature's Seed Buckwheat Seed - 50 Lb"
    assert section["brand"] == "Nature's Seed"
    assert section["keyFeatures"] == ["Fast germinating", "Drought tolerant"]
    assert section["plantCategory"] == ["Grasses"]
    assert section["plant_name"] == ["Buckwheat"]
    assert section["netContent"]["productNetContentMeasure"] == 50.0
    assert section["netContent"]["productNetContentUnit"] == "Pound"
    assert section["light_needs"] == "Full Sun"


def test_build_visible_fallback_no_seo():
    result = build_visible(None, "Grass Seeds")
    section = result["Grass Seeds"]
    assert section["brand"] == "Nature's Seed"
    assert section["isProp65WarningRequired"] == "No"
    assert section["condition"] == "New"
    assert "productName" not in section
    assert "keyFeatures" not in section


def test_build_visible_product_type_is_outer_key():
    result = build_visible(SEO_ITEMS[0], "Plant Seeds")
    assert "Plant Seeds" in result
    assert "Grass Seeds" not in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"
python3 -m pytest tests/test_resubmit.py -v
```

Expected: `ModuleNotFoundError: No module named 'resubmit_stage_items'`

- [ ] **Step 3: Write `resubmit_stage_items.py`**

Create `marketplaces/walmart-optimization/resubmit_stage_items.py`:

```python
#!/usr/bin/env python3
"""
Re-submits all Walmart STAGE items with correct MP_ITEM feed format.
Builds Orderable + Visible sections from seo_optimized.json content
and walmart_items.json pricing/identifiers.

Usage:
  python3 resubmit_stage_items.py
"""

import json
from datetime import datetime
from pathlib import Path

from sku_matching import get_base_sku
from seo_optimize import _parse_net_content, _normalize_light_needs
from walmart_client import submit_maintenance_feed, wait_for_feed

DATA_DIR = Path(__file__).parent / "data"


# ============================================================
# PURE FUNCTIONS
# ============================================================

def find_seo_content(sku, seo_items):
    """
    Match a STAGE SKU to seo_optimized content via base-SKU lookup.
    Returns the matching seo item dict, or None if no match.
    """
    lookup = {get_base_sku(item["sku"]): item for item in seo_items}
    return lookup.get(get_base_sku(sku))


def build_product_identifiers(wm_item):
    """
    Return productIdentifiers dict for the Item level, or None if no UPC/GTIN.
    Prefers GTIN over UPC.
    """
    gtin = wm_item.get("gtin", "")
    upc = wm_item.get("upc", "")
    if gtin:
        return {"productIdType": "GTIN", "productId": gtin}
    if upc:
        return {"productIdType": "UPC", "productId": upc}
    return None


def build_orderable(wm_item):
    """
    Build the Orderable section from a walmart_items.json entry.
    Returns dict with startDate, endDate, fulfillmentLagTime, and price if present.
    """
    orderable = {
        "startDate": "2020-01-01T00:00:00Z",
        "endDate": "2099-01-01T00:00:00Z",
        "fulfillmentLagTime": 2,
    }
    price_amount = wm_item.get("price", {}).get("amount")
    if price_amount:
        orderable["price"] = price_amount
    return orderable


def build_visible(seo_item, product_type):
    """
    Build the Visible section.
    seo_item: dict from seo_optimized.json, or None for fallback.
    product_type: Walmart productType string (e.g. "Grass Seeds").
    Returns {"<product_type>": {...}}.
    """
    if seo_item is None:
        return {
            product_type: {
                "brand": "Nature's Seed",
                "isProp65WarningRequired": "No",
                "condition": "New",
            }
        }

    attrs = seo_item.get("attributes", {})
    section = {
        "productName": seo_item.get("title", ""),
        "brand": attrs.get("brand", "Nature's Seed"),
        "shortDescription": seo_item.get("description", ""),
        "keyFeatures": seo_item.get("key_features", []),
        "isProp65WarningRequired": attrs.get("isProp65WarningRequired", "No"),
        "condition": attrs.get("condition", "New"),
    }

    light = attrs.get("light_needs", "")
    if light:
        section["light_needs"] = _normalize_light_needs(light)

    plant_cat = attrs.get("plantCategory", "")
    if plant_cat:
        section["plantCategory"] = [plant_cat]

    plant_name = attrs.get("plantName", "")
    if plant_name:
        section["plant_name"] = [plant_name]

    net_content = attrs.get("netContent", "")
    if net_content:
        section["netContent"] = _parse_net_content(net_content)

    return {product_type: section}


# ============================================================
# ORCHESTRATOR
# ============================================================

def run_resubmit():
    print("Walmart STAGE Item Re-submission")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    DATA_DIR.mkdir(exist_ok=True)

    audit_path = DATA_DIR / "stage_audit.json"
    if not audit_path.exists():
        print("ERROR: data/stage_audit.json not found. Run stage_audit.py first.")
        return

    stage_items = json.loads(audit_path.read_text())
    print(f"  {len(stage_items)} STAGE items from audit")

    wm_by_sku = {
        item["sku"]: item
        for item in json.loads((DATA_DIR / "walmart_items.json").read_text())
    }
    print(f"  {len(wm_by_sku)} Walmart items loaded")

    seo_items = json.loads((DATA_DIR / "seo_optimized.json").read_text())
    print(f"  {len(seo_items)} SEO items loaded")

    # Build payloads
    print("\n  Building payloads...")
    mp_items = []
    skipped = []

    for i, row in enumerate(stage_items, 1):
        sku = row["sku"]
        wm_item = wm_by_sku.get(sku)
        if not wm_item:
            print(f"    WARNING: {sku} not in walmart_items.json — skipping")
            skipped.append(sku)
            continue

        seo_content = find_seo_content(sku, seo_items)
        product_type = wm_item.get("productType", "Grass Seeds")
        identifiers = build_product_identifiers(wm_item)

        item = {
            "sku": sku,
            "Orderable": build_orderable(wm_item),
            "Visible": build_visible(seo_content, product_type),
        }
        if identifiers:
            item["productIdentifiers"] = identifiers

        mp_items.append({"Item": item})
        match_label = "seo" if seo_content else "fallback"
        print(f"    [{len(mp_items)}/{len(stage_items)}] {sku} ({match_label})")

    print(f"\n  Built {len(mp_items)} payloads, {len(skipped)} skipped")

    if not mp_items:
        print("  Nothing to submit.")
        return

    # Submit feed
    print(f"\n  Submitting MP_ITEM feed ({len(mp_items)} items)...")
    feed_id = submit_maintenance_feed(mp_items, feed_type="MP_ITEM")
    print(f"  Polling feed {feed_id}...")
    feed_status = wait_for_feed(feed_id, max_wait=600, poll_interval=30)

    overall = feed_status.get("feedStatus", "UNKNOWN")
    item_results = []
    for detail in feed_status.get("itemDetails", {}).get("itemIngestionStatus", []):
        errors = [
            err.get("description", str(err))
            for err in (detail.get("ingestionErrors") or {}).get("ingestionError", [])
        ]
        item_results.append({
            "sku": detail.get("sku", ""),
            "ingestion_status": detail.get("ingestionStatus", "UNKNOWN"),
            "errors": errors,
        })

    success = sum(1 for r in item_results if r["ingestion_status"] == "SUCCESS")
    errors_count = sum(1 for r in item_results if r["ingestion_status"] not in ("SUCCESS", "UNKNOWN"))

    print(f"\nFeed status: {overall}")
    print(f"  Submitted: {len(mp_items)}")
    print(f"  SUCCESS:   {success}")
    print(f"  ERRORS:    {errors_count}  → see data/resubmit_results.json")

    result_path = DATA_DIR / "resubmit_results.json"
    result_path.write_text(json.dumps({
        "feed_id": feed_id,
        "feed_status": overall,
        "submitted": len(mp_items),
        "skipped": skipped,
        "items": item_results,
    }, indent=2))
    print(f"  Results saved: {result_path}")


if __name__ == "__main__":
    run_resubmit()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"
python3 -m pytest tests/test_resubmit.py -v
```

Expected: 11/11 PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add marketplaces/walmart-optimization/resubmit_stage_items.py marketplaces/walmart-optimization/tests/test_resubmit.py
git commit -m "feat: resubmit_stage_items.py — correct MP_ITEM feed with Orderable + Visible sections"
```

---

### Task 2: Live run + inspect results

**Files:**
- Run: `resubmit_stage_items.py` against live Walmart API
- Output: `data/resubmit_results.json`

- [ ] **Step 1: Run against live API**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"
python3 resubmit_stage_items.py
```

Expected output structure:
```
Walmart STAGE Item Re-submission
Started: 2026-04-22 ...
============================================================
  19 STAGE items from audit
  257 Walmart items loaded
  182 SEO items loaded

  Building payloads...
    [1/19] W-ACLA-0.5-LB-KIT (seo)
    ...
  Built 19 payloads, 0 skipped

  Submitting MP_ITEM feed (19 items)...
  Polling feed ...
Feed status: PROCESSED
  Submitted: 19
  SUCCESS:   17
  ERRORS:    2
```

- [ ] **Step 2: Inspect results**

```bash
python3 -c "
import json
r = json.loads(open('/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization/data/resubmit_results.json').read())
print(f'Feed: {r[\"feed_id\"]}  Status: {r[\"feed_status\"]}')
print(f'Submitted: {r[\"submitted\"]}  Skipped: {r[\"skipped\"]}')
print()
for item in r['items']:
    status = item['ingestion_status']
    errors = ' | '.join(item['errors']) if item['errors'] else ''
    print(f'  {item[\"sku\"]:40s} {status}  {errors}')
"
```

- [ ] **Step 3: If any ERRORS — read Walmart's messages**

Walmart error messages will name the exact missing or invalid field. Common issues and fixes:

| Error | Fix |
|---|---|
| `price required in Orderable` | Item has no price in `walmart_items.json` — set price in Seller Center first |
| `productIdentifiers required` | No UPC/GTIN in `walmart_items.json` — add in Seller Center |
| `productName required` | Fallback item has no productName — add `productName` to fallback in `build_visible` |
| `shortDescription invalid HTML` | Description from seo_optimized has unsupported tags — strip to plain text |

- [ ] **Step 4: Commit output**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add marketplaces/walmart-optimization/data/resubmit_results.json
git commit -m "data: MP_ITEM re-submission results for STAGE items"
```
