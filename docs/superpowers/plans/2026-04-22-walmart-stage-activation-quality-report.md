# Walmart STAGE Activation + Product Quality Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Identify all Walmart STAGE items, activate those with Fishbowl stock > 0 via MP_ITEM feed, and generate a completeness + quality report for every STAGE item.

**Architecture:** Three standalone scripts in `marketplaces/walmart-optimization/` that reuse existing `fishbowl_client.py`, `walmart_client.py`, and `sku_matching.py`. Run in sequence: audit → activate → report. Each script writes output to `data/`. Pure logic functions are unit-tested; API calls are smoke-tested manually.

**Tech Stack:** Python 3, stdlib only (no new dependencies). Existing clients handle OAuth, pagination, and feed submission.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `marketplaces/walmart-optimization/stage_audit.py` | Create | Fetch STAGE items, cross-ref Fishbowl, write `data/stage_audit.json` |
| `marketplaces/walmart-optimization/activate_stage_items.py` | Create | Read audit, submit MP_ITEM feed for in-stock items, write `data/activation_results.json` |
| `marketplaces/walmart-optimization/product_quality_report.py` | Create | Score all STAGE items on completeness + quality, write `.md` + `.csv` |
| `marketplaces/walmart-optimization/tests/__init__.py` | Create | Makes tests/ a package |
| `marketplaces/walmart-optimization/tests/test_stage_audit.py` | Create | Unit tests for filter + audit row logic |
| `marketplaces/walmart-optimization/tests/test_activate.py` | Create | Unit tests for payload builder + result parser |
| `marketplaces/walmart-optimization/tests/test_quality_report.py` | Create | Unit tests for scoring functions |

---

### Task 1: Probe Walmart item detail structure

Confirm exact JSON field paths returned by `GET /v3/items/{sku}` before writing scoring logic. This is read-only and makes no changes.

**Files:** none created

- [ ] **Step 1: Run the probe**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"
python3 -c "
from walmart_client import get_all_items, get_item
import json

items = get_all_items()
stage = [i for i in items if i.get('publishedStatus') == 'STAGE']
if not stage:
    print('No STAGE items found — sample publishedStatus values:')
    for i in items[:5]:
        print(' ', i.get('sku'), i.get('publishedStatus'))
else:
    sku = stage[0]['sku']
    print(f'Probing SKU: {sku}')
    detail = get_item(sku)
    print(json.dumps(detail, indent=2))
" 2>&1 | head -120
```

- [ ] **Step 2: Record actual field paths**

From the probe output, verify and note the actual key names for:
- Product name → expected: `item["productName"]`
- Long description → expected: `item["productAttributes"]["longDescription"]`
- Short description → expected: `item["productAttributes"]["shortDescription"]`
- Brand → expected: `item["productAttributes"]["brand"]`
- Images list → expected: `item["images"]` (each has `imageType` and `url`)
- Key features/bullets → expected: `item["productAttributes"]["keyFeatures"]`
- Shipping weight → expected: `item["productAttributes"]["assembledProductWeight"]["value"]`
- Price → expected: `item["price"]["currentPrice"]["amount"]`
- Unpublished reasons → expected: `item["unpublishedReasons"]`

If any path differs, update the accessor functions in Task 4 (`_get_*` helpers) before writing `product_quality_report.py`.

---

### Task 2: `stage_audit.py` with unit tests

**Files:**
- Create: `marketplaces/walmart-optimization/tests/__init__.py`
- Create: `marketplaces/walmart-optimization/tests/test_stage_audit.py`
- Create: `marketplaces/walmart-optimization/stage_audit.py`

- [ ] **Step 1: Create tests directory**

```bash
mkdir -p "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization/tests"
touch "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization/tests/__init__.py"
```

- [ ] **Step 2: Write the failing tests**

Create `marketplaces/walmart-optimization/tests/test_stage_audit.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from stage_audit import filter_stage_items, build_audit_row


def test_filter_stage_items_keeps_only_stage():
    items = [
        {"sku": "A-1", "productName": "Alpha", "publishedStatus": "STAGE"},
        {"sku": "B-2", "productName": "Beta",  "publishedStatus": "PUBLISHED"},
        {"sku": "C-3", "productName": "Gamma", "publishedStatus": "STAGE"},
    ]
    result = filter_stage_items(items)
    assert len(result) == 2
    assert all(i["publishedStatus"] == "STAGE" for i in result)


def test_filter_stage_items_deduplicates_by_sku():
    items = [
        {"sku": "A-1", "productName": "Alpha", "publishedStatus": "STAGE"},
        {"sku": "A-1", "productName": "Alpha", "publishedStatus": "STAGE"},
    ]
    result = filter_stage_items(items)
    assert len(result) == 1


def test_filter_stage_items_empty():
    assert filter_stage_items([]) == []


def test_build_audit_row_with_stock():
    item = {"sku": "NS-BLUE-5-LB", "productName": "Bluegrass 5lb"}
    row = build_audit_row(item, fishbowl_qty=50, match_type="direct", matched_sku="NS-BLUE-5-LB")
    assert row["sku"] == "NS-BLUE-5-LB"
    assert row["fishbowl_qty"] == 50
    assert row["will_activate"] is True
    assert row["matched_fishbowl_sku"] == "NS-BLUE-5-LB"


def test_build_audit_row_no_stock():
    item = {"sku": "NS-BLUE-5-LB", "productName": "Bluegrass 5lb"}
    row = build_audit_row(item, fishbowl_qty=0, match_type="no_match", matched_sku=None)
    assert row["will_activate"] is False
    assert row["matched_fishbowl_sku"] is None
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"
python3 -m pytest tests/test_stage_audit.py -v
```

Expected: `ModuleNotFoundError: No module named 'stage_audit'`

- [ ] **Step 4: Write `stage_audit.py`**

Create `marketplaces/walmart-optimization/stage_audit.py`:

```python
#!/usr/bin/env python3
"""
Audits all Walmart STAGE items against Fishbowl inventory.
Outputs data/stage_audit.json.

Usage:
  python3 stage_audit.py
"""

import json
from datetime import datetime
from pathlib import Path

from fishbowl_client import get_all_inventory
from sku_matching import match_sku
from walmart_client import get_all_items

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def filter_stage_items(items):
    """Return deduplicated list of items with publishedStatus == STAGE."""
    seen = set()
    result = []
    for item in items:
        sku = item.get("sku", "")
        if item.get("publishedStatus") == "STAGE" and sku not in seen:
            seen.add(sku)
            result.append(item)
    return result


def build_audit_row(item, fishbowl_qty, match_type, matched_sku):
    """Build a single audit result dict."""
    return {
        "sku": item["sku"],
        "productName": item.get("productName", ""),
        "fishbowl_qty": fishbowl_qty,
        "matched_fishbowl_sku": matched_sku,
        "match_type": match_type,
        "will_activate": fishbowl_qty > 0,
    }


def run_audit():
    print("Walmart STAGE Item Audit")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print("\n[1/2] Pulling Fishbowl inventory...")
    fb_inventory = get_all_inventory()

    print("\n[2/2] Pulling Walmart items...")
    all_items = get_all_items()
    stage_items = filter_stage_items(all_items)
    print(f"  {len(all_items)} total items, {len(stage_items)} STAGE items")

    results = []
    for item in stage_items:
        qty, match_type, matched_sku = match_sku(item["sku"], fb_inventory)
        row = build_audit_row(item, qty, match_type, matched_sku)
        results.append(row)

    will_activate = sum(1 for r in results if r["will_activate"])
    no_stock = len(results) - will_activate

    print(f"\nSTAGE items found: {len(results)}")
    print(f"  Will activate (stock > 0): {will_activate}")
    print(f"  No stock, skipping: {no_stock}")

    out = DATA_DIR / "stage_audit.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Audit saved: {out}")

    return results


if __name__ == "__main__":
    run_audit()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"
python3 -m pytest tests/test_stage_audit.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 6: Smoke test against live API**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"
python3 stage_audit.py
```

Expected: prints STAGE item count summary and writes `data/stage_audit.json`.

```bash
python3 -c "
import json
with open('data/stage_audit.json') as f:
    rows = json.load(f)
print(f'{len(rows)} rows')
for r in rows[:3]:
    print(r)
"
```

- [ ] **Step 7: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add marketplaces/walmart-optimization/stage_audit.py marketplaces/walmart-optimization/tests/
git commit -m "feat: stage_audit.py — cross-reference Walmart STAGE items with Fishbowl inventory"
```

---

### Task 3: `activate_stage_items.py` with unit tests

**Files:**
- Create: `marketplaces/walmart-optimization/tests/test_activate.py`
- Create: `marketplaces/walmart-optimization/activate_stage_items.py`

- [ ] **Step 1: Write the failing tests**

Create `marketplaces/walmart-optimization/tests/test_activate.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from activate_stage_items import build_mp_item_payload, parse_feed_item_result


def test_build_mp_item_payload_wraps_item():
    item_detail = {
        "sku": "NS-BLUE-5-LB",
        "productName": "Bluegrass 5lb",
        "price": {"currentPrice": {"amount": 29.99, "currency": "USD"}},
    }
    payload = build_mp_item_payload(item_detail)
    assert "Item" in payload
    assert payload["Item"]["sku"] == "NS-BLUE-5-LB"


def test_parse_feed_item_result_success():
    feed_status = {
        "feedStatus": "PROCESSED",
        "itemDetails": {
            "itemIngestionStatus": [
                {"ingestionStatus": "SUCCESS", "ingestionErrors": None}
            ]
        },
    }
    result = parse_feed_item_result("NS-BLUE-5-LB", "feed123", feed_status)
    assert result["sku"] == "NS-BLUE-5-LB"
    assert result["feed_id"] == "feed123"
    assert result["status"] == "PROCESSED"
    assert result["ingestion_status"] == "SUCCESS"
    assert result["errors"] == []


def test_parse_feed_item_result_data_error():
    feed_status = {
        "feedStatus": "PROCESSED",
        "itemDetails": {
            "itemIngestionStatus": [
                {
                    "ingestionStatus": "DATA_ERROR",
                    "ingestionErrors": {
                        "ingestionError": [
                            {"type": "DATA_ERROR", "description": "Missing required field: brand"}
                        ]
                    },
                }
            ]
        },
    }
    result = parse_feed_item_result("NS-BLUE-5-LB", "feed123", feed_status)
    assert result["ingestion_status"] == "DATA_ERROR"
    assert len(result["errors"]) == 1
    assert "brand" in result["errors"][0]


def test_parse_feed_item_result_timeout():
    feed_status = {"feedStatus": "UNKNOWN"}
    result = parse_feed_item_result("NS-BLUE-5-LB", "feed123", feed_status)
    assert result["status"] == "UNKNOWN"
    assert result["ingestion_status"] == "UNKNOWN"
    assert result["errors"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"
python3 -m pytest tests/test_activate.py -v
```

Expected: `ModuleNotFoundError: No module named 'activate_stage_items'`

- [ ] **Step 3: Write `activate_stage_items.py`**

Create `marketplaces/walmart-optimization/activate_stage_items.py`:

```python
#!/usr/bin/env python3
"""
Activates Walmart STAGE items that have Fishbowl stock > 0.
Reads data/stage_audit.json, submits one MP_ITEM feed per item,
polls for result, writes data/activation_results.json.

Usage:
  python3 activate_stage_items.py
"""

import json
import time
from datetime import datetime
from pathlib import Path

from walmart_client import get_item, submit_maintenance_feed, wait_for_feed

DATA_DIR = Path(__file__).parent / "data"


def build_mp_item_payload(item_detail):
    """
    Wrap a Walmart GET /v3/items/{sku} response into an MPItem feed entry.
    Re-submitting via MP_ITEM triggers Walmart to re-evaluate a STAGE item.
    """
    return {"Item": item_detail}


def parse_feed_item_result(sku, feed_id, feed_status):
    """
    Extract per-item ingestion result from a Walmart feed status response.
    Returns dict with sku, feed_id, status, ingestion_status, errors.
    """
    overall = feed_status.get("feedStatus", "UNKNOWN")
    ingestion_status = "UNKNOWN"
    errors = []

    item_details = feed_status.get("itemDetails", {})
    ingestion_list = item_details.get("itemIngestionStatus", [])
    if ingestion_list:
        first = ingestion_list[0]
        ingestion_status = first.get("ingestionStatus", "UNKNOWN")
        raw_errors = first.get("ingestionErrors") or {}
        for err in raw_errors.get("ingestionError", []):
            errors.append(err.get("description", str(err)))

    return {
        "sku": sku,
        "feed_id": feed_id,
        "status": overall,
        "ingestion_status": ingestion_status,
        "errors": errors,
    }


def run_activation():
    print("Walmart STAGE Item Activation")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    audit_path = DATA_DIR / "stage_audit.json"
    if not audit_path.exists():
        print("ERROR: data/stage_audit.json not found. Run stage_audit.py first.")
        return []

    with open(audit_path) as f:
        audit = json.load(f)

    to_activate = [r for r in audit if r["will_activate"]]
    print(f"\n  {len(audit)} STAGE items in audit, {len(to_activate)} to activate")

    if not to_activate:
        print("  Nothing to activate.")
        return []

    results = []
    for i, row in enumerate(to_activate, 1):
        sku = row["sku"]
        print(f"\n  [{i}/{len(to_activate)}] {sku}")

        item_detail = get_item(sku)
        if not item_detail:
            print(f"    WARNING: Could not fetch item detail")
            results.append({
                "sku": sku,
                "feed_id": None,
                "status": "SKIPPED",
                "ingestion_status": "SKIPPED",
                "errors": ["Could not fetch item detail from Walmart API"],
            })
            continue

        mp_item = build_mp_item_payload(item_detail)
        feed_id = submit_maintenance_feed([mp_item], feed_type="MP_ITEM")
        print(f"    Feed submitted: {feed_id}")

        feed_status = wait_for_feed(feed_id, max_wait=600, poll_interval=30)
        result = parse_feed_item_result(sku, feed_id, feed_status)
        results.append(result)

        if result["errors"]:
            print(f"    Status: {result['ingestion_status']}")
            for err in result["errors"]:
                print(f"      ERROR: {err}")
        else:
            print(f"    Status: {result['ingestion_status']}")

        if i < len(to_activate):
            time.sleep(2)

    success = sum(1 for r in results if r["ingestion_status"] == "SUCCESS")
    errors = sum(1 for r in results if r["ingestion_status"] not in ("SUCCESS", "SKIPPED", "UNKNOWN"))

    print(f"\nActivation results: {len(results)} submitted")
    print(f"  SUCCESS: {success}")
    print(f"  ERRORS:  {errors}  → see data/activation_results.json")

    out = DATA_DIR / "activation_results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: {out}")

    return results


if __name__ == "__main__":
    run_activation()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"
python3 -m pytest tests/test_activate.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add marketplaces/walmart-optimization/activate_stage_items.py marketplaces/walmart-optimization/tests/test_activate.py
git commit -m "feat: activate_stage_items.py — submit MP_ITEM feed for in-stock STAGE items"
```

---

### Task 4: `product_quality_report.py` with unit tests

**Note:** If the Task 1 probe showed different field paths than the expected ones, update the `_get_*` accessor functions in this script before running tests.

**Files:**
- Create: `marketplaces/walmart-optimization/tests/test_quality_report.py`
- Create: `marketplaces/walmart-optimization/product_quality_report.py`

- [ ] **Step 1: Write the failing tests**

Create `marketplaces/walmart-optimization/tests/test_quality_report.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from product_quality_report import check_completeness, calc_quality_score, score_item

FULL_ITEM = {
    "sku": "NS-BLUE-5-LB",
    "productName": "Nature's Seed Kentucky Bluegrass Grass Seed Mixture 5 lb Bag",
    "price": {"currentPrice": {"amount": 29.99, "currency": "USD"}},
    "images": [
        {"url": "https://example.com/img1.jpg", "imageType": "PRIMARY"},
        {"url": "https://example.com/img2.jpg", "imageType": "SECONDARY"},
        {"url": "https://example.com/img3.jpg", "imageType": "SECONDARY"},
        {"url": "https://example.com/img4.jpg", "imageType": "SECONDARY"},
    ],
    "productAttributes": {
        "shortDescription": "Fast-germinating Kentucky Bluegrass",
        "longDescription": "A " + "word " * 160,
        "brand": "Nature's Seed",
        "keyFeatures": [
            "Fast germination in 7-14 days with proper watering",
            "Ideal for cool-season lawns throughout the midwest",
            "Drought tolerant once fully established after 6 weeks",
            "Works well in full sun and light shade conditions",
            "Covers up to 2500 sq ft per bag when properly applied",
        ],
        "assembledProductWeight": {"value": 5.0, "unit": "lb"},
    },
}

EMPTY_ITEM = {
    "sku": "NS-BLUE-5-LB",
    "productName": "",
    "productAttributes": {},
}


def test_check_completeness_full_item():
    result = check_completeness(FULL_ITEM)
    assert result["title"] is True
    assert result["long_description"] is True
    assert result["brand"] is True
    assert result["main_image"] is True
    assert result["additional_images"] is True
    assert result["key_features"] is True
    assert result["shipping_weight"] is True
    assert result["price"] is True


def test_check_completeness_empty_item():
    result = check_completeness(EMPTY_ITEM)
    assert result["title"] is False
    assert result["long_description"] is False
    assert result["brand"] is False
    assert result["main_image"] is False
    assert result["additional_images"] is False
    assert result["key_features"] is False
    assert result["shipping_weight"] is False
    assert result["price"] is False


def test_calc_quality_score_full_item():
    completeness = check_completeness(FULL_ITEM)
    score = calc_quality_score(FULL_ITEM, completeness)
    assert score >= 90


def test_calc_quality_score_empty_item():
    completeness = check_completeness(EMPTY_ITEM)
    score = calc_quality_score(EMPTY_ITEM, completeness)
    assert score == 0


def test_score_item_returns_required_keys():
    result = score_item(FULL_ITEM)
    assert "completeness" in result
    assert "quality_score" in result
    assert "gaps" in result
    assert isinstance(result["quality_score"], int)
    assert 0 <= result["quality_score"] <= 100


def test_title_length_boosts_score():
    short_item = dict(FULL_ITEM)
    short_item["productName"] = "Seed"
    completeness_short = check_completeness(short_item)
    score_short = calc_quality_score(short_item, completeness_short)

    completeness_full = check_completeness(FULL_ITEM)
    score_full = calc_quality_score(FULL_ITEM, completeness_full)

    assert score_full > score_short
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"
python3 -m pytest tests/test_quality_report.py -v
```

Expected: `ModuleNotFoundError: No module named 'product_quality_report'`

- [ ] **Step 3: Write `product_quality_report.py`**

Create `marketplaces/walmart-optimization/product_quality_report.py`:

```python
#!/usr/bin/env python3
"""
Scores all Walmart STAGE items on content completeness and quality.
Outputs data/product_quality_report.md and data/product_quality_report.csv.

Usage:
  python3 product_quality_report.py
"""

import csv
import json
from datetime import datetime
from pathlib import Path

from walmart_client import get_all_items, get_item
from stage_audit import filter_stage_items

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


# ============================================================
# FIELD ACCESSORS
# Update paths here if Task 1 probe showed different key names.
# ============================================================

def _get_title(item):
    return item.get("productName", "")

def _get_long_description(item):
    attrs = item.get("productAttributes", {})
    return attrs.get("longDescription", "") or attrs.get("description", "")

def _get_short_description(item):
    attrs = item.get("productAttributes", {})
    return attrs.get("shortDescription", "")

def _get_brand(item):
    attrs = item.get("productAttributes", {})
    return attrs.get("brand", "")

def _get_images(item):
    return item.get("images", [])

def _get_key_features(item):
    attrs = item.get("productAttributes", {})
    features = attrs.get("keyFeatures", [])
    if isinstance(features, str):
        return [features]
    return features or []

def _get_shipping_weight(item):
    attrs = item.get("productAttributes", {})
    weight = attrs.get("assembledProductWeight", {})
    return weight.get("value") if weight else None

def _get_price(item):
    price = item.get("price", {})
    current = price.get("currentPrice", {})
    return current.get("amount")


# ============================================================
# SCORING
# ============================================================

def check_completeness(item):
    """Return dict of required field name → bool (True = present)."""
    images = _get_images(item)
    primary = [i for i in images if i.get("imageType") == "PRIMARY"]
    secondary = [i for i in images if i.get("imageType") != "PRIMARY"]
    features = _get_key_features(item)

    return {
        "title": bool(_get_title(item)),
        "short_description": bool(_get_short_description(item)),
        "long_description": bool(_get_long_description(item)),
        "brand": bool(_get_brand(item)),
        "main_image": len(primary) >= 1,
        "additional_images": len(secondary) >= 2,
        "key_features": len(features) >= 3,
        "shipping_weight": _get_shipping_weight(item) is not None,
        "price": _get_price(item) is not None,
    }


def calc_quality_score(item, completeness):
    """
    Score 0-100 based on content quality signals.

    Rubric:
      Title 50-150 chars           15 pts
      Title contains species name  10 pts
      Long description > 150 words 20 pts
      4+ images (any type)         15 pts
      5+ bullet points             15 pts
      Bullets avg > 10 words each  10 pts
      Shipping weight present      10 pts
      Price present                 5 pts
    """
    SPECIES_SIGNALS = [
        "bluegrass", "fescue", "ryegrass", "bermuda", "zoysia", "kentucky",
        "perennial", "annual", "tall", "fine", "creeping", "centipede",
        "buffalo", "bahia", "clover", "wildflower", "bentgrass", "wheatgrass",
        "bromegrass", "orchardgrass", "timothy", "alpaca", "wildflower",
    ]

    score = 0
    title = _get_title(item)
    long_desc = _get_long_description(item)
    images = _get_images(item)
    features = _get_key_features(item)

    if 50 <= len(title) <= 150:
        score += 15

    if any(s in title.lower() for s in SPECIES_SIGNALS):
        score += 10

    if long_desc and len(long_desc.split()) > 150:
        score += 20

    if len(images) >= 4:
        score += 15

    if len(features) >= 5:
        score += 15

    if features:
        avg_words = sum(len(f.split()) for f in features) / len(features)
        if avg_words >= 10:
            score += 10

    if _get_shipping_weight(item) is not None:
        score += 10

    if _get_price(item) is not None:
        score += 5

    return score


def score_item(item):
    """Return completeness dict, quality_score int, and gaps list for one item."""
    completeness = check_completeness(item)
    quality_score = calc_quality_score(item, completeness)
    gaps = [field for field, ok in completeness.items() if not ok]
    return {
        "completeness": completeness,
        "quality_score": quality_score,
        "gaps": gaps,
    }


# ============================================================
# REPORT GENERATION
# ============================================================

def generate_markdown(scored_items):
    total = len(scored_items)
    avg_score = sum(i["quality_score"] for i in scored_items) / total if total else 0
    activated = sum(1 for i in scored_items if i.get("activation_status") == "SUCCESS")

    gap_counts = {}
    for item in scored_items:
        for gap in item["gaps"]:
            gap_counts[gap] = gap_counts.get(gap, 0) + 1
    top_gaps = sorted(gap_counts.items(), key=lambda x: x[1], reverse=True)

    lines = [
        "# Walmart STAGE Items — Product Quality Report",
        f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n## Summary",
        f"- STAGE items audited: **{total}**",
        f"- Successfully activated: **{activated}**",
        f"- Average quality score: **{avg_score:.1f} / 100**",
        "",
        "## Most Common Content Gaps",
        "",
    ]

    if top_gaps:
        for field, count in top_gaps:
            pct = round(count / total * 100) if total else 0
            lines.append(f"- `{field}`: missing from {count}/{total} items ({pct}%)")
    else:
        lines.append("- No gaps found across all items")

    lines += [
        "",
        "## Per-Product Scores",
        "",
        "| SKU | Product Name | Stock | Activated | Score | Gaps |",
        "|-----|-------------|-------|-----------|-------|------|",
    ]

    for item in sorted(scored_items, key=lambda x: x["quality_score"]):
        name = item["productName"][:40]
        activated_label = "YES" if item.get("activation_status") == "SUCCESS" else "no"
        gaps = ", ".join(item["gaps"]) if item["gaps"] else "none"
        lines.append(
            f"| {item['sku']} | {name} | {item.get('fishbowl_qty', 0)} "
            f"| {activated_label} | {item['quality_score']}/100 | {gaps} |"
        )

    lines += ["", "---", "*Generated by product_quality_report.py*"]
    return "\n".join(lines)


def run_report():
    print("Walmart STAGE Product Quality Report")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    activation_map = {}
    activation_path = DATA_DIR / "activation_results.json"
    if activation_path.exists():
        with open(activation_path) as f:
            for r in json.load(f):
                activation_map[r["sku"]] = r.get("ingestion_status", "UNKNOWN")
        print(f"  Loaded activation results for {len(activation_map)} items")

    audit_map = {}
    audit_path = DATA_DIR / "stage_audit.json"
    if audit_path.exists():
        with open(audit_path) as f:
            for r in json.load(f):
                audit_map[r["sku"]] = r

    print("\n  Fetching STAGE items from Walmart...")
    all_items = get_all_items()
    stage_items = filter_stage_items(all_items)
    print(f"  {len(stage_items)} STAGE items to score")

    scored = []
    for i, item in enumerate(stage_items, 1):
        sku = item["sku"]
        print(f"  [{i}/{len(stage_items)}] Scoring {sku}...")

        detail = get_item(sku) or item
        result = score_item(detail)
        audit_row = audit_map.get(sku, {})

        scored.append({
            "sku": sku,
            "productName": item.get("productName", ""),
            "fishbowl_qty": audit_row.get("fishbowl_qty", 0),
            "will_activate": audit_row.get("will_activate", False),
            "activation_status": activation_map.get(sku, "NOT_ATTEMPTED"),
            "quality_score": result["quality_score"],
            "gaps": result["gaps"],
            **result["completeness"],
        })

    md_path = DATA_DIR / "product_quality_report.md"
    with open(md_path, "w") as f:
        f.write(generate_markdown(scored))
    print(f"\n  Markdown saved: {md_path}")

    csv_path = DATA_DIR / "product_quality_report.csv"
    if scored:
        fieldnames = [
            "sku", "productName", "fishbowl_qty", "will_activate",
            "activation_status", "quality_score", "gaps",
            "title", "short_description", "long_description", "brand",
            "main_image", "additional_images", "key_features",
            "shipping_weight", "price",
        ]
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in sorted(scored, key=lambda x: x["sku"]):
                row = dict(row)
                row["gaps"] = "; ".join(row["gaps"])
                writer.writerow(row)
    print(f"  CSV saved: {csv_path}")

    avg_score = sum(i["quality_score"] for i in scored) / len(scored) if scored else 0
    print(f"\nAverage quality score: {avg_score:.1f}/100")

    return scored


if __name__ == "__main__":
    run_report()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"
python3 -m pytest tests/test_quality_report.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add marketplaces/walmart-optimization/product_quality_report.py marketplaces/walmart-optimization/tests/test_quality_report.py
git commit -m "feat: product_quality_report.py — completeness + quality scoring for all STAGE items"
```

---

### Task 5: End-to-end pipeline run

- [ ] **Step 1: Run all three scripts in sequence**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"

echo "=== Step 1: Audit ==="
python3 stage_audit.py

echo ""
echo "=== Step 2: Activate ==="
python3 activate_stage_items.py

echo ""
echo "=== Step 3: Report ==="
python3 product_quality_report.py
```

- [ ] **Step 2: Inspect outputs**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketplaces/walmart-optimization"

echo "--- Audit ---"
python3 -c "
import json
with open('data/stage_audit.json') as f:
    rows = json.load(f)
print(f'{len(rows)} STAGE items')
for r in rows:
    print(f'  {r[\"sku\"]:35s} qty={r[\"fishbowl_qty\"]:4d}  activate={r[\"will_activate\"]}')
"

echo ""
echo "--- Activation results ---"
python3 -c "
import json
with open('data/activation_results.json') as f:
    rows = json.load(f)
for r in rows:
    print(f'  {r[\"sku\"]:35s} {r[\"ingestion_status\"]}', end='')
    if r['errors']:
        print(f'  ERRORS: {r[\"errors\"]}')
    else:
        print()
"

echo ""
echo "--- Quality report ---"
cat data/product_quality_report.md
```

- [ ] **Step 3: If any activation errors — read the error messages**

Walmart error messages in `activation_results.json` will describe exactly what field is missing or wrong for each item. These match 1:1 with gaps in `product_quality_report.md`. No further action needed — the report documents them.

- [ ] **Step 4: Final commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add marketplaces/walmart-optimization/data/
git commit -m "data: initial STAGE audit, activation results, and quality report"
```
