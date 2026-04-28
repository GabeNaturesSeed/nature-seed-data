# Reddit Ads Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a Google-Shopping-spec TSV of every in-stock published WooCommerce product (one row per variation) and serve it via GitHub Pages so Reddit Ads Manager can ingest it daily as a Catalog.

**Architecture:** Pure-function transform layer + thin WC client + main entry script + GitHub Action cron. The transform layer is the testable core; everything else is I/O. Output files committed to `main` so `git log` is the catalog audit trail. GitHub Pages serves the static TSV.

**Tech Stack:** Python 3.11, `requests`, `pytest`, GitHub Actions, GitHub Pages. WooCommerce REST API routed through existing CF Worker proxy (`wc-api-proxy.skylar-d51.workers.dev`).

**Spec:** [docs/superpowers/specs/2026-04-28-reddit-ads-catalog-design.md](../specs/2026-04-28-reddit-ads-catalog-design.md)

---

## File Structure

```
marketing/reddit-ads/
├── __init__.py                       # empty, makes package importable
├── transform.py                      # pure functions: filter, format, build rows
├── wc_client.py                      # WC API I/O (paginated fetch, retry)
├── build_reddit_catalog.py           # main entry: orchestrates fetch → transform → write
├── requirements.txt                  # requests, pytest
├── README.md                         # one-time Reddit Ads Manager + GH Pages setup
├── output/
│   ├── .gitkeep                      # placeholder so empty dir is committed
│   ├── reddit_catalog.tsv            # generated, committed each run
│   └── reddit_catalog_summary.json   # generated, committed each run
└── tests/
    ├── __init__.py
    ├── fixtures/
    │   ├── simple_product.json       # one simple product, all fields valid
    │   ├── variable_product.json     # one variable product with 3 variations
    │   └── edge_cases.json           # list of products that should each be skipped
    └── test_transform.py             # unit tests for every pure function

.github/workflows/reddit-catalog.yml  # daily cron + commit + push
```

**Responsibilities:**
- `transform.py` — Pure functions only. No I/O, no env vars, no network. Every function is unit-testable from a JSON dict.
- `wc_client.py` — Wraps the CF Worker proxy. `fetch_products()` and `fetch_variations(product_id)`. Handles retry, pagination, rate-limit sleep.
- `build_reddit_catalog.py` — Glue. Loads `.env`, calls `wc_client`, feeds results to `transform`, writes TSV + JSON, applies regression guard.

---

## Task 1: Scaffold the project structure

**Files:**
- Create: `marketing/reddit-ads/__init__.py`
- Create: `marketing/reddit-ads/tests/__init__.py`
- Create: `marketing/reddit-ads/tests/fixtures/.gitkeep`
- Create: `marketing/reddit-ads/output/.gitkeep`
- Create: `marketing/reddit-ads/requirements.txt`

- [ ] **Step 1: Create empty package files and dirs**

```bash
mkdir -p "marketing/reddit-ads/tests/fixtures"
mkdir -p "marketing/reddit-ads/output"
touch "marketing/reddit-ads/__init__.py"
touch "marketing/reddit-ads/tests/__init__.py"
touch "marketing/reddit-ads/tests/fixtures/.gitkeep"
touch "marketing/reddit-ads/output/.gitkeep"
```

- [ ] **Step 2: Write requirements.txt**

Create `marketing/reddit-ads/requirements.txt`:
```
requests>=2.31
pytest>=7.4
```

- [ ] **Step 3: Verify pip install works**

Run: `pip install -r marketing/reddit-ads/requirements.txt`
Expected: Successfully installed (or "already satisfied").

- [ ] **Step 4: Commit**

```bash
git add marketing/reddit-ads/
git commit -m "scaffold: marketing/reddit-ads package structure"
```

---

## Task 2: TDD `format_price()` — currency formatting

**Files:**
- Create: `marketing/reddit-ads/tests/test_transform.py`
- Create: `marketing/reddit-ads/transform.py`

- [ ] **Step 1: Write the failing test**

Create `marketing/reddit-ads/tests/test_transform.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from transform import format_price


def test_format_price_normal():
    assert format_price("19.99") == "19.99 USD"


def test_format_price_integer_string():
    assert format_price("20") == "20.00 USD"


def test_format_price_float():
    assert format_price(19.99) == "19.99 USD"


def test_format_price_none_returns_none():
    assert format_price(None) is None


def test_format_price_empty_string_returns_none():
    assert format_price("") is None


def test_format_price_zero_returns_none():
    assert format_price("0") is None
    assert format_price(0) is None
    assert format_price("0.00") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v`
Expected: ImportError or "cannot import name 'format_price'".

- [ ] **Step 3: Write minimal implementation**

Create `marketing/reddit-ads/transform.py`:
```python
"""Pure functions for transforming WC products into Reddit catalog rows.

No I/O, no env vars, no network calls live here. Everything is a function
of its inputs so the unit tests in tests/test_transform.py can exercise
every branch from JSON fixtures.
"""


def format_price(value):
    """Format a price as '<float> USD' for the Reddit/Google Shopping spec.

    Returns None if the value is missing or zero — caller treats that as
    a skip signal.
    """
    if value is None or value == "":
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    return f"{amount:.2f} USD"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add marketing/reddit-ads/tests/test_transform.py marketing/reddit-ads/transform.py
git commit -m "feat(reddit-ads): format_price() — currency formatting per Reddit spec"
```

---

## Task 3: TDD `strip_html()` and `truncate_description()`

**Files:**
- Modify: `marketing/reddit-ads/tests/test_transform.py`
- Modify: `marketing/reddit-ads/transform.py`

- [ ] **Step 1: Append failing tests**

Append to `marketing/reddit-ads/tests/test_transform.py`:
```python
from transform import strip_html, truncate_description


def test_strip_html_removes_tags():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_decodes_entities():
    assert strip_html("Tom &amp; Jerry &lt;3") == "Tom & Jerry <3"


def test_strip_html_collapses_whitespace():
    assert strip_html("<p>Line one</p>\n\n<p>Line two</p>") == "Line one Line two"


def test_strip_html_handles_empty():
    assert strip_html("") == ""
    assert strip_html(None) == ""


def test_truncate_description_short_passthrough():
    assert truncate_description("Short text", limit=1000) == "Short text"


def test_truncate_description_caps_at_limit():
    long = "a" * 2000
    out = truncate_description(long, limit=1000)
    assert len(out) == 1000


def test_truncate_description_strips_html_first():
    out = truncate_description("<p>Hi <b>there</b></p>", limit=1000)
    assert out == "Hi there"


def test_truncate_description_preserves_utf8():
    # Cap inside a multi-byte character must not produce invalid UTF-8
    out = truncate_description("héllo " * 500, limit=100)
    assert isinstance(out, str)
    assert len(out) <= 100
    out.encode("utf-8")  # would raise if broken
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v -k "strip_html or truncate"`
Expected: ImportError on `strip_html` / `truncate_description`.

- [ ] **Step 3: Add implementations**

Append to `marketing/reddit-ads/transform.py`:
```python
import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text):
    """Remove HTML tags and decode entities. Collapses whitespace to single spaces."""
    if not text:
        return ""
    no_tags = _TAG_RE.sub(" ", text)
    decoded = html.unescape(no_tags)
    return _WS_RE.sub(" ", decoded).strip()


def truncate_description(text, limit=1000):
    """Strip HTML, then cap at `limit` characters. Safe for UTF-8 (str slicing
    operates on code points, not bytes)."""
    cleaned = strip_html(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v`
Expected: 14 passed (6 from Task 2 + 8 new).

- [ ] **Step 5: Commit**

```bash
git add marketing/reddit-ads/tests/test_transform.py marketing/reddit-ads/transform.py
git commit -m "feat(reddit-ads): strip_html + truncate_description"
```

---

## Task 4: TDD `build_title()` — variation attributes appended

**Files:**
- Modify: `marketing/reddit-ads/tests/test_transform.py`
- Modify: `marketing/reddit-ads/transform.py`

- [ ] **Step 1: Append failing tests**

Append to `marketing/reddit-ads/tests/test_transform.py`:
```python
from transform import build_title


def test_build_title_no_attributes():
    assert build_title("Kentucky Bluegrass Seed", []) == "Kentucky Bluegrass Seed"


def test_build_title_single_attribute():
    attrs = [{"name": "Size", "option": "5 lb"}]
    assert build_title("Kentucky Bluegrass Seed", attrs) == "Kentucky Bluegrass Seed — 5 lb"


def test_build_title_multiple_attributes_joined():
    attrs = [
        {"name": "Size", "option": "5 lb"},
        {"name": "Type", "option": "Coated"},
    ]
    assert build_title("Clover Mix", attrs) == "Clover Mix — 5 lb / Coated"


def test_build_title_truncates_at_150():
    long_name = "A" * 200
    out = build_title(long_name, [])
    assert len(out) == 150


def test_build_title_truncates_with_attributes():
    long_name = "A" * 145
    attrs = [{"name": "Size", "option": "Extra Large 50 Pound Bag"}]
    out = build_title(long_name, attrs)
    assert len(out) == 150
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v -k "build_title"`
Expected: ImportError on `build_title`.

- [ ] **Step 3: Add implementation**

Append to `marketing/reddit-ads/transform.py`:
```python
TITLE_LIMIT = 150


def build_title(name, attributes):
    """Build the Reddit catalog title for one row.

    `attributes` is the variation's `attributes` list from the WC API:
    a list of {"name": ..., "option": ...} dicts. For simple products
    pass an empty list.
    """
    base = name or ""
    options = [a.get("option", "") for a in (attributes or []) if a.get("option")]
    if options:
        title = f"{base} — {' / '.join(options)}"
    else:
        title = base
    if len(title) > TITLE_LIMIT:
        title = title[:TITLE_LIMIT]
    return title
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v`
Expected: 19 passed.

- [ ] **Step 5: Commit**

```bash
git add marketing/reddit-ads/tests/test_transform.py marketing/reddit-ads/transform.py
git commit -m "feat(reddit-ads): build_title with variation attribute suffix"
```

---

## Task 5: TDD `should_skip_product()` and `should_skip_variation()`

**Files:**
- Modify: `marketing/reddit-ads/tests/test_transform.py`
- Modify: `marketing/reddit-ads/transform.py`

- [ ] **Step 1: Append failing tests**

Append to `marketing/reddit-ads/tests/test_transform.py`:
```python
from transform import should_skip_product, should_skip_variation


def _valid_simple_product():
    return {
        "id": 1,
        "status": "publish",
        "stock_status": "instock",
        "price": "19.99",
        "type": "simple",
        "images": [{"src": "https://example.com/a.jpg"}],
    }


def test_skip_product_unpublished():
    p = _valid_simple_product()
    p["status"] = "draft"
    assert should_skip_product(p) == "not_published"


def test_skip_product_no_images():
    p = _valid_simple_product()
    p["images"] = []
    assert should_skip_product(p) == "no_image"


def test_skip_simple_out_of_stock():
    p = _valid_simple_product()
    p["stock_status"] = "outofstock"
    assert should_skip_product(p) == "out_of_stock"


def test_skip_simple_zero_price():
    p = _valid_simple_product()
    p["price"] = "0"
    assert should_skip_product(p) == "zero_price"


def test_keep_valid_simple_product():
    assert should_skip_product(_valid_simple_product()) is None


def test_variable_parent_not_skipped_for_stock_or_price():
    # Variable parent's stock/price come from variations — only filter on
    # publish status and presence of any image at the parent level.
    p = _valid_simple_product()
    p["type"] = "variable"
    p["stock_status"] = "outofstock"
    p["price"] = ""
    assert should_skip_product(p) is None


def test_skip_variation_out_of_stock():
    v = {"id": 10, "stock_status": "outofstock", "price": "19.99"}
    assert should_skip_variation(v) == "out_of_stock"


def test_skip_variation_zero_price():
    v = {"id": 10, "stock_status": "instock", "price": "0"}
    assert should_skip_variation(v) == "zero_price"


def test_keep_valid_variation():
    v = {"id": 10, "stock_status": "instock", "price": "19.99"}
    assert should_skip_variation(v) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v -k "skip"`
Expected: ImportError on the two new functions.

- [ ] **Step 3: Add implementations**

Append to `marketing/reddit-ads/transform.py`:
```python
def should_skip_product(product):
    """Decide whether a parent WC product should be skipped before fetching
    variations. Returns a reason string (for logging) or None to keep.

    Variable parents are kept even if their stock/price look empty —
    those fields are populated on the variation level.
    """
    if product.get("status") != "publish":
        return "not_published"
    if not product.get("images"):
        return "no_image"
    if product.get("type") == "variable":
        return None
    if product.get("stock_status") != "instock":
        return "out_of_stock"
    if format_price(product.get("price")) is None:
        return "zero_price"
    return None


def should_skip_variation(variation):
    """Decide whether a single variation should be skipped. Image is checked
    elsewhere (variation can fall back to parent image)."""
    if variation.get("stock_status") != "instock":
        return "out_of_stock"
    if format_price(variation.get("price")) is None:
        return "zero_price"
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v`
Expected: 28 passed.

- [ ] **Step 5: Commit**

```bash
git add marketing/reddit-ads/tests/test_transform.py marketing/reddit-ads/transform.py
git commit -m "feat(reddit-ads): should_skip_product + should_skip_variation filters"
```

---

## Task 6: TDD `pick_image()` — variation overrides parent

**Files:**
- Modify: `marketing/reddit-ads/tests/test_transform.py`
- Modify: `marketing/reddit-ads/transform.py`

- [ ] **Step 1: Append failing tests**

Append to `marketing/reddit-ads/tests/test_transform.py`:
```python
from transform import pick_image, additional_images


def test_pick_image_variation_override():
    parent = {"images": [{"src": "https://example.com/parent.jpg"}]}
    variation = {"image": {"src": "https://example.com/var.jpg"}}
    assert pick_image(parent, variation) == "https://example.com/var.jpg"


def test_pick_image_falls_back_to_parent():
    parent = {"images": [{"src": "https://example.com/parent.jpg"}]}
    variation = {"image": None}
    assert pick_image(parent, variation) == "https://example.com/parent.jpg"


def test_pick_image_simple_product_no_variation():
    parent = {"images": [{"src": "https://example.com/parent.jpg"}]}
    assert pick_image(parent, None) == "https://example.com/parent.jpg"


def test_pick_image_returns_none_when_nothing_available():
    assert pick_image({"images": []}, None) is None


def test_additional_images_skips_first():
    parent = {"images": [
        {"src": "a.jpg"}, {"src": "b.jpg"}, {"src": "c.jpg"}
    ]}
    assert additional_images(parent) == "b.jpg,c.jpg"


def test_additional_images_caps_at_nine():
    parent = {"images": [{"src": f"{i}.jpg"} for i in range(15)]}
    out = additional_images(parent).split(",")
    assert len(out) == 9


def test_additional_images_empty_when_only_one():
    parent = {"images": [{"src": "a.jpg"}]}
    assert additional_images(parent) == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v -k "image"`
Expected: ImportError.

- [ ] **Step 3: Add implementations**

Append to `marketing/reddit-ads/transform.py`:
```python
ADDITIONAL_IMAGE_LIMIT = 9


def pick_image(parent, variation):
    """Return the variation's image URL if set, else the parent's first
    image, else None."""
    if variation:
        v_img = variation.get("image")
        if v_img and v_img.get("src"):
            return v_img["src"]
    images = (parent or {}).get("images") or []
    if images and images[0].get("src"):
        return images[0]["src"]
    return None


def additional_images(parent):
    """Return up to 9 extra image URLs (skipping the featured one) joined by ','."""
    images = (parent or {}).get("images") or []
    extras = [img.get("src", "") for img in images[1:1 + ADDITIONAL_IMAGE_LIMIT]]
    return ",".join(e for e in extras if e)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v`
Expected: 35 passed.

- [ ] **Step 5: Commit**

```bash
git add marketing/reddit-ads/tests/test_transform.py marketing/reddit-ads/transform.py
git commit -m "feat(reddit-ads): pick_image with variation override + additional_images"
```

---

## Task 7: Add fixture JSON files

**Files:**
- Create: `marketing/reddit-ads/tests/fixtures/simple_product.json`
- Create: `marketing/reddit-ads/tests/fixtures/variable_product.json`
- Create: `marketing/reddit-ads/tests/fixtures/variations_for_variable.json`

- [ ] **Step 1: Create simple product fixture**

Create `marketing/reddit-ads/tests/fixtures/simple_product.json`:
```json
{
  "id": 1001,
  "name": "Annual Ryegrass Seed",
  "type": "simple",
  "status": "publish",
  "stock_status": "instock",
  "permalink": "https://naturesseed.com/products/annual-ryegrass/",
  "short_description": "<p>Fast germinating <b>cover crop</b>.</p>",
  "description": "<p>Long version.</p>",
  "price": "24.99",
  "regular_price": "24.99",
  "sale_price": "",
  "sku": "NS-AR-5LB",
  "images": [
    {"src": "https://naturesseed.com/img/ar-1.jpg"},
    {"src": "https://naturesseed.com/img/ar-2.jpg"}
  ],
  "categories": [{"name": "Cover Crops"}],
  "meta_data": []
}
```

- [ ] **Step 2: Create variable product fixture**

Create `marketing/reddit-ads/tests/fixtures/variable_product.json`:
```json
{
  "id": 2001,
  "name": "Sheep Pasture Mix",
  "type": "variable",
  "status": "publish",
  "stock_status": "instock",
  "permalink": "https://naturesseed.com/products/sheep-pasture-mix/",
  "short_description": "<p>Premium sheep grazing blend.</p>",
  "description": "",
  "price": "",
  "regular_price": "",
  "sale_price": "",
  "sku": "",
  "images": [
    {"src": "https://naturesseed.com/img/sheep-parent.jpg"}
  ],
  "categories": [{"name": "Pasture & Forage"}],
  "meta_data": [],
  "variations": [3001, 3002, 3003]
}
```

- [ ] **Step 3: Create variations fixture**

Create `marketing/reddit-ads/tests/fixtures/variations_for_variable.json`:
```json
[
  {
    "id": 3001,
    "stock_status": "instock",
    "price": "29.99",
    "regular_price": "29.99",
    "sale_price": "",
    "sku": "NS-SHEEP-5LB",
    "image": {"src": "https://naturesseed.com/img/sheep-5lb.jpg"},
    "attributes": [{"name": "Size", "option": "5 lb"}]
  },
  {
    "id": 3002,
    "stock_status": "instock",
    "price": "99.99",
    "regular_price": "119.99",
    "sale_price": "99.99",
    "sku": "NS-SHEEP-25LB",
    "image": null,
    "attributes": [{"name": "Size", "option": "25 lb"}]
  },
  {
    "id": 3003,
    "stock_status": "outofstock",
    "price": "199.99",
    "regular_price": "199.99",
    "sale_price": "",
    "sku": "NS-SHEEP-50LB",
    "image": {"src": "https://naturesseed.com/img/sheep-50lb.jpg"},
    "attributes": [{"name": "Size", "option": "50 lb"}]
  }
]
```

- [ ] **Step 4: Commit**

```bash
git add marketing/reddit-ads/tests/fixtures/
git commit -m "test(reddit-ads): add WC product fixtures (simple, variable, variations)"
```

---

## Task 8: TDD `transform_simple_product()` — single-row builder

**Files:**
- Modify: `marketing/reddit-ads/tests/test_transform.py`
- Modify: `marketing/reddit-ads/transform.py`

- [ ] **Step 1: Append failing test**

Append to `marketing/reddit-ads/tests/test_transform.py`:
```python
import json
from transform import transform_simple_product

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name):
    with open(os.path.join(FIXTURE_DIR, name)) as f:
        return json.load(f)


def test_transform_simple_product_full_row():
    product = _load_fixture("simple_product.json")
    row = transform_simple_product(product)
    assert row == {
        "id": "1001",
        "item_group_id": "1001",
        "title": "Annual Ryegrass Seed",
        "description": "Fast germinating cover crop.",
        "link": "https://naturesseed.com/products/annual-ryegrass/",
        "image_link": "https://naturesseed.com/img/ar-1.jpg",
        "additional_image_link": "https://naturesseed.com/img/ar-2.jpg",
        "availability": "in stock",
        "price": "24.99 USD",
        "sale_price": "",
        "brand": "Nature's Seed",
        "condition": "new",
        "gtin": "",
        "mpn": "NS-AR-5LB",
        "product_type": "Cover Crops",
        "google_product_category": "5587",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v -k "transform_simple"`
Expected: ImportError on `transform_simple_product`.

- [ ] **Step 3: Add implementation**

Append to `marketing/reddit-ads/transform.py`:
```python
BRAND = "Nature's Seed"
GOOGLE_PRODUCT_CATEGORY = "5587"  # Home & Garden > Lawn & Garden > Gardening > Plants > Seeds


def _gtin_from_meta(meta_data):
    for entry in meta_data or []:
        if entry.get("key") == "_gtin":
            return str(entry.get("value") or "")
    return ""


def _product_type(product):
    cats = product.get("categories") or []
    return cats[0].get("name", "") if cats else ""


def _description(product):
    text = product.get("short_description") or product.get("description") or ""
    return truncate_description(text)


def _sale_price(regular, sale):
    sale_fmt = format_price(sale)
    reg_fmt = format_price(regular)
    if not sale_fmt or not reg_fmt:
        return ""
    if float(sale) >= float(regular):
        return ""
    return sale_fmt


def transform_simple_product(product):
    """Return one TSV row dict for a simple WC product."""
    pid = str(product["id"])
    return {
        "id": pid,
        "item_group_id": pid,
        "title": build_title(product.get("name"), []),
        "description": _description(product),
        "link": product.get("permalink", ""),
        "image_link": pick_image(product, None) or "",
        "additional_image_link": additional_images(product),
        "availability": "in stock",
        "price": format_price(product.get("price")) or "",
        "sale_price": _sale_price(product.get("regular_price"), product.get("sale_price")),
        "brand": BRAND,
        "condition": "new",
        "gtin": _gtin_from_meta(product.get("meta_data")),
        "mpn": product.get("sku", "") or "",
        "product_type": _product_type(product),
        "google_product_category": GOOGLE_PRODUCT_CATEGORY,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v`
Expected: 36 passed.

- [ ] **Step 5: Commit**

```bash
git add marketing/reddit-ads/tests/test_transform.py marketing/reddit-ads/transform.py
git commit -m "feat(reddit-ads): transform_simple_product builds full TSV row"
```

---

## Task 9: TDD `transform_variable_product()` — multi-row, with skip

**Files:**
- Modify: `marketing/reddit-ads/tests/test_transform.py`
- Modify: `marketing/reddit-ads/transform.py`

- [ ] **Step 1: Append failing tests**

Append to `marketing/reddit-ads/tests/test_transform.py`:
```python
from transform import transform_variable_product


def test_transform_variable_product_emits_one_row_per_valid_variation():
    parent = _load_fixture("variable_product.json")
    variations = _load_fixture("variations_for_variable.json")
    rows, skipped = transform_variable_product(parent, variations)
    # 3001 keeps, 3002 keeps (image falls back to parent), 3003 skipped (oos)
    assert [r["id"] for r in rows] == ["3001", "3002"]
    assert all(r["item_group_id"] == "2001" for r in rows)
    assert skipped == [{"id": 3003, "reason": "out_of_stock"}]


def test_transform_variable_variation_image_fallback_to_parent():
    parent = _load_fixture("variable_product.json")
    variations = _load_fixture("variations_for_variable.json")
    rows, _ = transform_variable_product(parent, variations)
    row_3002 = next(r for r in rows if r["id"] == "3002")
    assert row_3002["image_link"] == "https://naturesseed.com/img/sheep-parent.jpg"


def test_transform_variable_title_includes_attributes():
    parent = _load_fixture("variable_product.json")
    variations = _load_fixture("variations_for_variable.json")
    rows, _ = transform_variable_product(parent, variations)
    row_3001 = next(r for r in rows if r["id"] == "3001")
    assert row_3001["title"] == "Sheep Pasture Mix — 5 lb"


def test_transform_variable_sale_price_when_lower():
    parent = _load_fixture("variable_product.json")
    variations = _load_fixture("variations_for_variable.json")
    rows, _ = transform_variable_product(parent, variations)
    row_3002 = next(r for r in rows if r["id"] == "3002")
    assert row_3002["price"] == "99.99 USD"
    assert row_3002["sale_price"] == "99.99 USD"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v -k "transform_variable"`
Expected: ImportError on `transform_variable_product`.

- [ ] **Step 3: Add implementation**

Append to `marketing/reddit-ads/transform.py`:
```python
def transform_variable_product(parent, variations):
    """Return (rows, skipped) for a variable WC product.

    `variations` is the list returned by GET /products/{id}/variations.
    Variations that fail filters are recorded in `skipped` with their reason
    and excluded from `rows`. Each row uses the variation's id, but shares
    `item_group_id` with all siblings (the parent's id).
    """
    parent_id = str(parent["id"])
    rows = []
    skipped = []
    for v in variations:
        reason = should_skip_variation(v)
        if reason:
            skipped.append({"id": v["id"], "reason": reason})
            continue
        rows.append({
            "id": str(v["id"]),
            "item_group_id": parent_id,
            "title": build_title(parent.get("name"), v.get("attributes")),
            "description": _description(parent),
            "link": parent.get("permalink", ""),
            "image_link": pick_image(parent, v) or "",
            "additional_image_link": additional_images(parent),
            "availability": "in stock",
            "price": format_price(v.get("price")) or "",
            "sale_price": _sale_price(v.get("regular_price"), v.get("sale_price")),
            "brand": BRAND,
            "condition": "new",
            "gtin": "",
            "mpn": v.get("sku", "") or parent.get("sku", "") or "",
            "product_type": _product_type(parent),
            "google_product_category": GOOGLE_PRODUCT_CATEGORY,
        })
    return rows, skipped
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v`
Expected: 40 passed.

- [ ] **Step 5: Commit**

```bash
git add marketing/reddit-ads/tests/test_transform.py marketing/reddit-ads/transform.py
git commit -m "feat(reddit-ads): transform_variable_product with per-variation skip"
```

---

## Task 10: TDD `write_tsv()` — escaping + header row

**Files:**
- Modify: `marketing/reddit-ads/tests/test_transform.py`
- Modify: `marketing/reddit-ads/transform.py`

- [ ] **Step 1: Append failing tests**

Append to `marketing/reddit-ads/tests/test_transform.py`:
```python
import io
from transform import write_tsv, TSV_COLUMNS


def test_write_tsv_header_first():
    rows = [{c: "" for c in TSV_COLUMNS}]
    rows[0]["id"] = "1"
    buf = io.StringIO()
    write_tsv(buf, rows)
    lines = buf.getvalue().splitlines()
    assert lines[0] == "\t".join(TSV_COLUMNS)


def test_write_tsv_escapes_tabs_and_newlines():
    row = {c: "" for c in TSV_COLUMNS}
    row["id"] = "1"
    row["title"] = "Has\ttab and\nnewline"
    buf = io.StringIO()
    write_tsv(buf, [row])
    body = buf.getvalue().splitlines()[1]
    cells = body.split("\t")
    title_idx = TSV_COLUMNS.index("title")
    assert cells[title_idx] == "Has tab and newline"


def test_write_tsv_row_count_matches():
    rows = [{c: "" for c in TSV_COLUMNS} for _ in range(5)]
    for i, r in enumerate(rows):
        r["id"] = str(i)
    buf = io.StringIO()
    write_tsv(buf, rows)
    assert len(buf.getvalue().splitlines()) == 6  # header + 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v -k "write_tsv"`
Expected: ImportError on `write_tsv` / `TSV_COLUMNS`.

- [ ] **Step 3: Add implementation**

Append to `marketing/reddit-ads/transform.py`:
```python
TSV_COLUMNS = [
    "id",
    "item_group_id",
    "title",
    "description",
    "link",
    "image_link",
    "additional_image_link",
    "availability",
    "price",
    "sale_price",
    "brand",
    "condition",
    "gtin",
    "mpn",
    "product_type",
    "google_product_category",
]


def _scrub_cell(value):
    """Replace tabs and newlines with single spaces — TSV cells cannot contain them."""
    s = "" if value is None else str(value)
    return s.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def write_tsv(file_like, rows):
    """Write header + rows to a text file-like object. Each row is a dict
    keyed by TSV_COLUMNS; missing keys become empty strings."""
    file_like.write("\t".join(TSV_COLUMNS) + "\n")
    for row in rows:
        cells = [_scrub_cell(row.get(col, "")) for col in TSV_COLUMNS]
        file_like.write("\t".join(cells) + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest marketing/reddit-ads/tests/test_transform.py -v`
Expected: 43 passed.

- [ ] **Step 5: Commit**

```bash
git add marketing/reddit-ads/tests/test_transform.py marketing/reddit-ads/transform.py
git commit -m "feat(reddit-ads): write_tsv with header + tab/newline escaping"
```

---

## Task 11: WC client — paginated fetch with retry

**Files:**
- Create: `marketing/reddit-ads/wc_client.py`

This task has no unit tests — it's pure I/O against a live API, exercised end-to-end in Task 13.

- [ ] **Step 1: Write the WC client module**

Create `marketing/reddit-ads/wc_client.py`:
```python
"""WooCommerce REST client for the Reddit catalog builder.

Routes through the CF Worker proxy when CF_WORKER_URL is set in the env
dict (required in CI to bypass Bot Fight Mode). Falls back to direct
WC API calls when not set (works from residential IPs).
"""
import base64
import time
import requests

PER_PAGE = 100
SLEEP_BETWEEN_CALLS = 0.3
MAX_RETRIES = 3
TIMEOUT = 30


def _auth_header(env):
    ck = env.get("WP_WOO_CONSUMER_KEY") or env["WC_CK"]
    cs = env.get("WP_WOO_CONSUMER_SECRET") or env["WC_CS"]
    token = base64.b64encode(f"{ck}:{cs}".encode()).decode()
    return f"Basic {token}"


def _request(env, wc_path, params):
    """Make one paginated request through the proxy if configured, else direct."""
    headers = {"Authorization": _auth_header(env)}
    if env.get("CF_WORKER_URL"):
        url = env["CF_WORKER_URL"]
        headers["X-Proxy-Secret"] = env["CF_WORKER_SECRET"]
        full_params = {"wc_path": wc_path, **params}
    else:
        url = env["WC_BASE_URL"].rstrip("/") + wc_path
        full_params = params

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, params=full_params, timeout=TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = 4 ** attempt  # 1, 4, 16
                print(f"  HTTP {resp.status_code} — retry in {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except (requests.ConnectionError, requests.Timeout) as e:
            wait = 4 ** attempt
            print(f"  Network error ({e!r}) — retry in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"WC request failed after {MAX_RETRIES} retries: {wc_path} {params}")


def fetch_products(env):
    """Yield every published product, paginated. Includes both simple and variable.

    We do NOT filter by stock_status here — the parent of a variable product
    can show 'outofstock' while a specific variation is in stock. The
    transform layer applies per-variation filtering.
    """
    page = 1
    while True:
        print(f"  Fetching products page {page}...")
        batch = _request(env, "/products", {
            "status": "publish",
            "per_page": PER_PAGE,
            "page": page,
        })
        if not batch:
            return
        for product in batch:
            yield product
        if len(batch) < PER_PAGE:
            return
        page += 1
        time.sleep(SLEEP_BETWEEN_CALLS)


def fetch_variations(env, product_id):
    """Return the full list of variations for one variable product."""
    variations = []
    page = 1
    while True:
        batch = _request(env, f"/products/{product_id}/variations", {
            "per_page": PER_PAGE,
            "page": page,
        })
        if not batch:
            break
        variations.extend(batch)
        if len(batch) < PER_PAGE:
            break
        page += 1
        time.sleep(SLEEP_BETWEEN_CALLS)
    return variations
```

- [ ] **Step 2: Smoke test the client locally**

Run from project root (uses local `.env`, hits live WC):
```bash
python -c "
import sys
sys.path.insert(0, 'marketing/reddit-ads')
from wc_client import fetch_products
env = {}
with open('.env') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip(\"'\\\"\")
n = 0
for p in fetch_products(env):
    n += 1
    if n >= 5: break
print('OK,', n, 'products fetched')
"
```
Expected: `OK, 5 products fetched` printed within ~10s. If you see auth errors, check that `WP_WOO_CONSUMER_KEY/SECRET` are present in `.env` (preferred over the older `WC_CK/WC_CS`).

- [ ] **Step 3: Commit**

```bash
git add marketing/reddit-ads/wc_client.py
git commit -m "feat(reddit-ads): WC client with CF Worker proxy + retry"
```

---

## Task 12: Main entry script — orchestration + regression guard

**Files:**
- Create: `marketing/reddit-ads/build_reddit_catalog.py`

- [ ] **Step 1: Write the main script**

Create `marketing/reddit-ads/build_reddit_catalog.py`:
```python
#!/usr/bin/env python3
"""Build the Reddit Ads catalog TSV from WooCommerce.

Run from project root:
    python marketing/reddit-ads/build_reddit_catalog.py

Outputs:
    marketing/reddit-ads/output/reddit_catalog.tsv
    marketing/reddit-ads/output/reddit_catalog_summary.json
"""
import json
import os
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, SCRIPT_DIR)

from transform import (
    should_skip_product,
    transform_simple_product,
    transform_variable_product,
    write_tsv,
)
from wc_client import fetch_products, fetch_variations

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
TSV_PATH = os.path.join(OUTPUT_DIR, "reddit_catalog.tsv")
SUMMARY_PATH = os.path.join(OUTPUT_DIR, "reddit_catalog_summary.json")
REGRESSION_THRESHOLD = 0.5  # new run must have at least 50% of previous row count


def load_env():
    env = {}
    with open(os.path.join(PROJECT_DIR, ".env")) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip().strip("'\"")
    return env


def previous_row_count():
    if not os.path.exists(SUMMARY_PATH):
        return None
    try:
        with open(SUMMARY_PATH) as f:
            return json.load(f).get("row_count")
    except (OSError, json.JSONDecodeError):
        return None


def main():
    env = load_env()
    rows = []
    skipped = []
    products_seen = 0
    variations_seen = 0

    for product in fetch_products(env):
        products_seen += 1
        reason = should_skip_product(product)
        if reason:
            skipped.append({"id": product["id"], "reason": reason})
            continue

        if product.get("type") == "variable":
            variations = fetch_variations(env, product["id"])
            variations_seen += len(variations)
            sub_rows, sub_skipped = transform_variable_product(product, variations)
            rows.extend(sub_rows)
            skipped.extend(sub_skipped)
        else:
            rows.append(transform_simple_product(product))

    prev = previous_row_count()
    if prev is not None and len(rows) < prev * REGRESSION_THRESHOLD:
        print(
            f"FAIL: row count regression. New={len(rows)} Previous={prev} "
            f"(threshold {int(REGRESSION_THRESHOLD * 100)}%). Not writing output."
        )
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(TSV_PATH, "w", encoding="utf-8") as f:
        write_tsv(f, rows)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "row_count": len(rows),
        "products_seen": products_seen,
        "variations_seen": variations_seen,
        "skipped": skipped,
        "previous_row_count": prev,
    }
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"OK: wrote {len(rows)} rows ({products_seen} products, {variations_seen} variations)")
    print(f"     skipped: {len(skipped)}")
    print(f"     {TSV_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run end-to-end against live WC**

Run: `python "marketing/reddit-ads/build_reddit_catalog.py"`
Expected: prints `OK: wrote N rows ...` where N is in the 100s–1000s. Two new files exist in `marketing/reddit-ads/output/`.

- [ ] **Step 3: Sanity-check the TSV by hand**

Run: `head -3 "marketing/reddit-ads/output/reddit_catalog.tsv" | cut -f1-5`
Expected: header row + 2 product rows showing `id`, `item_group_id`, `title`, `description`, `link`. Title has variation suffix where applicable. No empty `id` or `link` cells.

- [ ] **Step 4: Inspect the summary**

Run: `cat "marketing/reddit-ads/output/reddit_catalog_summary.json"`
Expected: JSON with `row_count`, `products_seen`, `variations_seen`, `skipped` array, `previous_row_count: null` (first run).

- [ ] **Step 5: Commit script + first baseline output**

```bash
git add marketing/reddit-ads/build_reddit_catalog.py marketing/reddit-ads/output/reddit_catalog.tsv marketing/reddit-ads/output/reddit_catalog_summary.json
git commit -m "feat(reddit-ads): main entry + first live catalog baseline"
```

---

## Task 13: Verify regression guard works

**Files:** No new files — manual verification.

- [ ] **Step 1: Temporarily lower the regression threshold to 0.99**

Edit `marketing/reddit-ads/build_reddit_catalog.py` line `REGRESSION_THRESHOLD = 0.5` to `REGRESSION_THRESHOLD = 0.99`.

- [ ] **Step 2: Re-run the build and confirm it still passes (or skips by ≤1%)**

Run: `python "marketing/reddit-ads/build_reddit_catalog.py"`
Expected: either `OK:` (if row count is identical to previous) or `FAIL: row count regression` (if catalog naturally fluctuated by even 1 row). Either outcome confirms the guard fires correctly when given a strict threshold.

- [ ] **Step 3: Restore threshold and re-run**

Edit back to `REGRESSION_THRESHOLD = 0.5`. Run: `python "marketing/reddit-ads/build_reddit_catalog.py"`. Expected: `OK:`.

- [ ] **Step 4: Discard any output changes from this verification**

```bash
git checkout marketing/reddit-ads/build_reddit_catalog.py marketing/reddit-ads/output/
```

(No commit — this task is a behavioral check only.)

---

## Task 14: GitHub Action workflow

**Files:**
- Create: `.github/workflows/reddit-catalog.yml`

- [ ] **Step 1: Write the workflow file**

Create `.github/workflows/reddit-catalog.yml`:
```yaml
name: Reddit Ads Catalog

on:
  schedule:
    - cron: '0 6 * * *'   # 6 AM UTC daily
  workflow_dispatch:

permissions:
  contents: write   # needed to commit the regenerated TSV back to main

jobs:
  build-catalog:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - uses: actions/checkout@v5

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r marketing/reddit-ads/requirements.txt

      - name: Create .env from secrets
        run: |
          cat > .env << 'ENVEOF'
          WC_BASE_URL=${{ secrets.WC_BASE_URL }}
          WC_CK=${{ secrets.WC_CK }}
          WC_CS=${{ secrets.WC_CS }}
          WP_WOO_CONSUMER_KEY=${{ secrets.WP_WOO_CONSUMER_KEY }}
          WP_WOO_CONSUMER_SECRET=${{ secrets.WP_WOO_CONSUMER_SECRET }}
          CF_WORKER_URL=${{ secrets.CF_WORKER_URL }}
          CF_WORKER_SECRET=${{ secrets.CF_WORKER_SECRET }}
          ENVEOF

      - name: Run unit tests
        run: pytest marketing/reddit-ads/tests/ -v

      - name: Build catalog
        run: python marketing/reddit-ads/build_reddit_catalog.py

      - name: Commit and push regenerated catalog
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add marketing/reddit-ads/output/reddit_catalog.tsv marketing/reddit-ads/output/reddit_catalog_summary.json
          if git diff --cached --quiet; then
            echo "No catalog changes."
          else
            git commit -m "chore(reddit-ads): daily catalog rebuild $(date -u +%Y-%m-%d)"
            git push
          fi
```

- [ ] **Step 2: Commit the workflow**

```bash
git add .github/workflows/reddit-catalog.yml
git commit -m "ci(reddit-ads): daily catalog build + commit workflow"
```

- [ ] **Step 3: Push to main and trigger a manual run**

```bash
git push origin main
```

Then in GitHub UI: Actions → "Reddit Ads Catalog" → "Run workflow" → Run.
Expected: green check within ~3 minutes. The workflow either commits a new TSV (if anything changed since the local run) or logs "No catalog changes."

If it fails on auth: confirm Repository secrets `WP_WOO_CONSUMER_KEY`, `WP_WOO_CONSUMER_SECRET`, `CF_WORKER_URL`, `CF_WORKER_SECRET` exist (Settings → Secrets and variables → Actions → Repository secrets, NOT Environment).

---

## Task 15: Enable GitHub Pages

**Files:** No code changes — manual GitHub UI step.

- [ ] **Step 1: Enable Pages on the repo**

In GitHub UI for `GabeNaturesSeed/nature-seed-data`:
- Settings → Pages
- Source: "Deploy from a branch"
- Branch: `main` / `/ (root)`
- Save

Wait ~1 minute for Pages to build.

- [ ] **Step 2: Verify the catalog is publicly fetchable**

Run from anywhere:
```bash
curl -sI "https://gabenaturesseed.github.io/nature-seed-data/marketing/reddit-ads/output/reddit_catalog.tsv" | head -5
```
Expected: `HTTP/2 200` + `content-type: text/tab-separated-values` (or `text/plain`).

If 404: wait another minute (Pages can be slow on first build), then try again. If still 404, confirm the file actually exists on `main` at that path with `git ls-tree main marketing/reddit-ads/output/`.

- [ ] **Step 3: Spot-check a few rows in a browser**

Open the URL in a browser. Expected: a TSV file downloads or renders as text. First line is the header row.

---

## Task 16: README — one-time Reddit Ads Manager setup

**Files:**
- Create: `marketing/reddit-ads/README.md`

- [ ] **Step 1: Write the README**

Create `marketing/reddit-ads/README.md`:
```markdown
# Reddit Ads Catalog

Daily-regenerated Google-Shopping-spec product feed for Reddit Ads Manager.

## What this does

A GitHub Action runs daily at 6 AM UTC, pulls every in-stock published
WooCommerce product (one row per variation), writes
`output/reddit_catalog.tsv`, and commits it to `main`. GitHub Pages
serves that file at:

`https://gabenaturesseed.github.io/nature-seed-data/marketing/reddit-ads/output/reddit_catalog.tsv`

Reddit Ads Manager fetches that URL on its own daily schedule.

## One-time setup in Reddit Ads Manager

1. Reddit Ads Manager → **Catalog** → **Create Catalog**
2. Source: **Scheduled feed**
3. Feed URL: paste the URL above
4. Refresh frequency: **Daily**
5. Currency: **USD**
6. Save. First validation pass takes ~30 minutes.

Once the catalog populates, link it to a Catalog Sales campaign objective.

## Local development

```bash
pip install -r requirements.txt
python build_reddit_catalog.py
```

Reads `.env` from project root. If `CF_WORKER_URL` is unset, hits the
WC API directly (works from residential IPs only).

## Tests

```bash
pytest tests/ -v
```

All transform logic is pure-function — tests run with no network.

## Files

- `build_reddit_catalog.py` — orchestrator
- `transform.py` — pure functions: filter, format, build rows, write TSV
- `wc_client.py` — paginated WC fetch with retry, routes through CF Worker
- `output/` — generated TSV + summary JSON, committed on every run
- `tests/` — unit tests + JSON fixtures
```

- [ ] **Step 2: Commit**

```bash
git add marketing/reddit-ads/README.md
git commit -m "docs(reddit-ads): README with one-time Reddit Ads Manager setup"
```

---

## Task 17: Update HANDOFF.md project map

**Files:**
- Modify: `HANDOFF.md`

- [ ] **Step 1: Add an entry under the project list**

Use Read to find the right section in `HANDOFF.md` (search for an existing `marketing/` entry, e.g. `klaviyo-audit/` or `google-ads-audit/`), then add a peer entry:

```markdown
- `marketing/reddit-ads/` — Daily Google-Shopping-spec TSV of in-stock WC products (variation-level), served via GitHub Pages for Reddit Ads Manager catalog ingestion. See [marketing/reddit-ads/README.md](marketing/reddit-ads/README.md).
```

Place it adjacent to the existing `marketing/*` entries to keep the section logically grouped.

- [ ] **Step 2: Commit**

```bash
git add HANDOFF.md
git commit -m "docs: add reddit-ads to HANDOFF project map"
```

- [ ] **Step 3: Push everything**

```bash
git push origin main
```

---

## Done criteria

- All 43 unit tests pass: `pytest marketing/reddit-ads/tests/ -v`
- Local run produces a non-empty TSV: `python marketing/reddit-ads/build_reddit_catalog.py` exits 0 with `OK: wrote N rows`
- GitHub Action manual run completes green
- `curl -I` against the GitHub Pages URL returns `200`
- The TSV opens cleanly in a spreadsheet (Excel/Numbers) with 16 columns
- Reddit Ads Manager catalog setup completed manually (Task 16's instructions)

## Out of scope (future work, do not implement here)

- Reddit Conversions API event push using `REDDIT_EVENTS_TOKEN`
- Catalog Sales campaign creative + audience setup
- Reusing the TSV for Meta / Pinterest / TikTok catalog ads
- Sweeping cleanup of legacy Telegram notifications (handle opportunistically)
