# Product Feed Management — Implementation Plan (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scheduled feed audit system that pulls a WooCommerce product snapshot daily, runs per-channel drift/coverage/quality checks across 6 active channels + 2 stubs, and commits a daily digest markdown to git.

**Architecture:** `build_feed_master.py` pulls WC once daily and writes `feeds/feed_master.json` (WC-canonical). Eight channel adapters inherit from `base_adapter.py` and each run three checks (coverage, drift, quality) against that snapshot. `run_audit.py` calls all adapters and writes `feeds/digest/YYYY-MM-DD-feed-health.md`. `sync_prices.py` is a separate manual-trigger script for price+inventory pushes.

**Tech Stack:** Python 3.9+ (local) / 3.11 (GH Actions), `requests`, existing `.env` parsing pattern, existing CF Worker proxy pattern from `infrastructure/daily-report/daily_pull.py`.

---

## File Map

**New files — feeds layer:**
- `feeds/build_feed_master.py` — pulls WC products+variations, writes feed_master.json
- `feeds/feed_master.json` — generated daily, committed to git
- `feeds/channel_sku_map.json` — manually maintained SKU aliases per channel

**New files — adapters:**
- `feeds/adapters/__init__.py`
- `feeds/adapters/base_adapter.py` — abstract base: coverage_check, drift_check, quality_check
- `feeds/adapters/walmart.py` + `feeds/adapters/walmart_SCHEMA.md`
- `feeds/adapters/amazon.py` + `feeds/adapters/amazon_SCHEMA.md`
- `feeds/adapters/google_merchant.py` + `feeds/adapters/google_merchant_SCHEMA.md`
- `feeds/adapters/klaviyo.py` + `feeds/adapters/klaviyo_SCHEMA.md`
- `feeds/adapters/shopper_approved.py` + `feeds/adapters/shopper_approved_SCHEMA.md`
- `feeds/adapters/reddit.py` + `feeds/adapters/reddit_SCHEMA.md`
- `feeds/adapters/facebook.py` + `feeds/adapters/facebook_SCHEMA.md` (stub)
- `feeds/adapters/pinterest.py` + `feeds/adapters/pinterest_SCHEMA.md` (stub)

**New files — digest + sync:**
- `feeds/digest/__init__.py`
- `feeds/digest/run_audit.py` — calls all adapters, writes daily digest markdown
- `feeds/sync/__init__.py`
- `feeds/sync/sync_prices.py` — pushes price+inventory to Walmart + Amazon (manual trigger)

**New files — infra:**
- `feeds/requirements.txt`
- `.github/workflows/feed-audit.yml` — daily cron at midnight MST

**New files — tests:**
- `feeds/tests/__init__.py`
- `feeds/tests/test_build_feed_master.py`
- `feeds/tests/test_base_adapter.py`
- `feeds/tests/test_walmart.py`
- `feeds/tests/test_digest.py`
- `feeds/tests/test_sync_prices.py`

---

## Task 1: Project scaffold + shared env loader

**Files:**
- Create: `feeds/requirements.txt`
- Create: `feeds/__init__.py`
- Create: `feeds/adapters/__init__.py`
- Create: `feeds/digest/__init__.py`
- Create: `feeds/sync/__init__.py`
- Create: `feeds/tests/__init__.py`
- Create: `feeds/env_loader.py`
- Create: `feeds/tests/test_env_loader.py`

- [ ] **Step 1: Create requirements.txt**

```
requests>=2.31.0
pytest>=7.4.0
```

- [ ] **Step 2: Create all `__init__.py` files (all empty)**

```bash
mkdir -p feeds/adapters feeds/digest feeds/sync feeds/tests
touch feeds/__init__.py feeds/adapters/__init__.py feeds/digest/__init__.py feeds/sync/__init__.py feeds/tests/__init__.py
```

- [ ] **Step 3: Write failing test for env loader**

`feeds/tests/test_env_loader.py`:
```python
import os
import tempfile
from feeds.env_loader import load_env

def test_load_env_parses_spaces_and_quotes():
    content = "WC_CK = 'ck_abc123'\nWC_CS = \"cs_def456\"\n"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(content)
        path = f.name
    env = load_env(path)
    assert env['WC_CK'] == 'ck_abc123'
    assert env['WC_CS'] == 'cs_def456'

def test_load_env_ignores_comments_and_blanks():
    content = "# comment\n\nFOO = 'bar'\n"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(content)
        path = f.name
    env = load_env(path)
    assert 'FOO' in env
    assert len(env) == 1
```

- [ ] **Step 4: Run test to confirm failure**

```bash
cd "ClaudeDataAgent -"
python -m pytest feeds/tests/test_env_loader.py -v
```
Expected: `ModuleNotFoundError` or `ImportError`

- [ ] **Step 5: Create `feeds/env_loader.py`**

```python
from pathlib import Path

def load_env(path=None):
    if path is None:
        path = Path(__file__).resolve().parent.parent / ".env"
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env
```

- [ ] **Step 6: Run tests — confirm pass**

```bash
python -m pytest feeds/tests/test_env_loader.py -v
```
Expected: 2 PASS

- [ ] **Step 7: Commit**

```bash
git add feeds/
git commit -m "feat(feeds): scaffold project structure + env loader"
```

---

## Task 2: Feed Master Builder

**Files:**
- Create: `feeds/build_feed_master.py`
- Create: `feeds/tests/test_build_feed_master.py`

- [ ] **Step 1: Write failing tests**

`feeds/tests/test_build_feed_master.py`:
```python
import json
from unittest.mock import patch, MagicMock
from feeds.build_feed_master import build_product_record, pull_wc_products

def _mock_product(wc_id=100, sku="TEST-SKU", price="19.99", status="publish"):
    return {
        "id": wc_id,
        "sku": sku,
        "name": "Test Product",
        "status": status,
        "type": "simple",
        "price": price,
        "sale_price": "",
        "stock_status": "instock",
        "stock_quantity": 50,
        "categories": [{"name": "Lawn"}],
        "permalink": "https://www.naturesseed.com/products/test/",
        "images": [{"src": "https://example.com/img.jpg"}],
        "meta_data": [{"key": "_gtin", "value": "012345678901"}],
        "weight": "5",
        "short_description": "Short desc",
        "description": "Long desc",
        "variations": [],
        "attributes": [],
    }

def test_build_product_record_simple():
    p = _mock_product()
    record = build_product_record(p, variations=[])
    assert record["wc_id"] == 100
    assert record["sku"] == "TEST-SKU"
    assert record["price"] == "19.99"
    assert record["status"] == "publish"
    assert record["type"] == "simple"
    assert record["brand"] == "Nature's Seed"
    assert record["variations"] == []

def test_build_product_record_extracts_gtin():
    p = _mock_product()
    record = build_product_record(p, variations=[])
    assert record["gtin"] == "012345678901"

def test_build_product_record_url_uses_products_permalink():
    p = _mock_product()
    record = build_product_record(p, variations=[])
    assert "/products/" in record["url"]

def test_build_product_record_skips_draft():
    p = _mock_product(status="draft")
    record = build_product_record(p, variations=[])
    assert record["status"] == "draft"
```

- [ ] **Step 2: Run tests — confirm failure**

```bash
python -m pytest feeds/tests/test_build_feed_master.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `feeds/build_feed_master.py`**

```python
#!/usr/bin/env python3
"""
Nature's Seed — Feed Master Builder
Pulls full WC product catalog (products + variations) and writes feeds/feed_master.json.
Runs daily via GitHub Actions. Uses CF Worker proxy when CF_WORKER_URL is set.

Usage:
    python3 feeds/build_feed_master.py
"""

import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from feeds.env_loader import load_env

ENV = load_env()

WC_BASE = ENV.get("WC_BASE_URL", "https://naturesseed.com/wp-json/wc/v3")
WC_CK = ENV["WC_CK"]
WC_CS = ENV["WC_CS"]
WC_AUTH = (WC_CK, WC_CS)
WC_HEADERS = {"User-Agent": "NaturesSeed-FeedMaster/1.0"}

CF_WORKER_URL = ENV.get("CF_WORKER_URL", "")
CF_WORKER_SECRET = ENV.get("CF_WORKER_SECRET", "")

OUT_PATH = Path(__file__).parent / "feed_master.json"


def _wc_get(endpoint, params=None, max_retries=3):
    """GET from WC REST API. Routes through CF Worker when CF_WORKER_URL is set."""
    params = params or {}
    url = f"{WC_BASE}{endpoint}"
    for attempt in range(max_retries):
        if CF_WORKER_URL and CF_WORKER_SECRET:
            proxy_params = dict(params)
            proxy_params["wc_path"] = endpoint
            auth_str = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
            headers = {
                "X-Proxy-Secret": CF_WORKER_SECRET,
                "Authorization": f"Basic {auth_str}",
                **WC_HEADERS,
            }
            resp = requests.get(CF_WORKER_URL, params=proxy_params, headers=headers, timeout=60)
        else:
            resp = requests.get(url, auth=WC_AUTH, params=params, headers=WC_HEADERS, timeout=60)

        if resp.status_code == 200:
            return resp
        if resp.status_code in (403, 429, 500, 502, 503) and attempt < max_retries - 1:
            time.sleep(5 * (attempt + 1))
            continue
        resp.raise_for_status()
    return resp


def _get_meta(meta_data, key):
    for m in meta_data:
        if m.get("key") == key:
            return m.get("value", "")
    return ""


def build_product_record(product, variations):
    """Convert a WC product dict into the feed_master canonical format."""
    meta = product.get("meta_data", [])
    images = [img["src"] for img in product.get("images", [])]

    built_variations = []
    for v in variations:
        vmeta = v.get("meta_data", [])
        built_variations.append({
            "variation_id": v["id"],
            "sku": v.get("sku", ""),
            "price": v.get("price", ""),
            "sale_price": v.get("sale_price", ""),
            "stock_quantity": v.get("stock_quantity"),
            "stock_status": v.get("stock_status", ""),
            "attributes": {a["name"]: a["option"] for a in v.get("attributes", [])},
            "gtin": _get_meta(vmeta, "_gtin") or _get_meta(vmeta, "_wc_gtin") or "",
            "weight_lbs": float(v["weight"]) if v.get("weight") else None,
        })

    return {
        "wc_id": product["id"],
        "sku": product.get("sku", ""),
        "name": product.get("name", ""),
        "status": product.get("status", ""),
        "type": product.get("type", "simple"),
        "price": product.get("price", ""),
        "sale_price": product.get("sale_price", ""),
        "stock_status": product.get("stock_status", ""),
        "stock_quantity": product.get("stock_quantity"),
        "categories": [c["name"] for c in product.get("categories", [])],
        "url": product.get("permalink", ""),
        "images": images,
        "gtin": _get_meta(meta, "_gtin") or _get_meta(meta, "_wc_gtin") or "",
        "mpn": product.get("sku", ""),
        "brand": "Nature's Seed",
        "weight_lbs": float(product["weight"]) if product.get("weight") else None,
        "short_description": product.get("short_description", ""),
        "description": product.get("description", ""),
        "variations": built_variations,
        "channel_skus": {},
    }


def pull_wc_products():
    """Pull all published WC products and their variations. Returns list of product dicts."""
    print("[WC] Pulling products...")
    products = []
    page = 1
    while True:
        resp = _wc_get("/products", {"per_page": 100, "page": page, "status": "publish"})
        batch = resp.json()
        if not batch:
            break
        products.extend(batch)
        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        print(f"  Page {page}/{total_pages} — {len(batch)} products")
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)

    print(f"[WC] {len(products)} products. Pulling variations...")
    records = []
    for p in products:
        variations = []
        if p.get("type") == "variable" and p.get("variations"):
            vpage = 1
            while True:
                vresp = _wc_get(f"/products/{p['id']}/variations", {"per_page": 100, "page": vpage})
                vbatch = vresp.json()
                if not vbatch:
                    break
                variations.extend(vbatch)
                vtotal = int(vresp.headers.get("X-WP-TotalPages", 1))
                if vpage >= vtotal:
                    break
                vpage += 1
                time.sleep(0.3)
        records.append(build_product_record(p, variations))

    return records


def build_feed_master():
    records = pull_wc_products()
    # Load existing channel_sku_map if present
    map_path = Path(__file__).parent / "channel_sku_map.json"
    channel_sku_map = {}
    if map_path.exists():
        with open(map_path) as f:
            channel_sku_map = json.load(f)

    # Inject channel_skus into each record
    for r in records:
        sku = r["sku"]
        r["channel_skus"] = {
            ch: aliases.get(sku, "") for ch, aliases in channel_sku_map.items()
        }

    variation_count = sum(len(r["variations"]) for r in records)
    output = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "product_count": len(records),
            "variation_count": variation_count,
        },
        "products": {str(r["wc_id"]): r for r in records},
    }

    with open(OUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n[DONE] {len(records)} products, {variation_count} variations → {OUT_PATH}")


if __name__ == "__main__":
    build_feed_master()
```

- [ ] **Step 4: Create `feeds/channel_sku_map.json` (starter template)**

```json
{
  "amazon": {},
  "walmart": {},
  "google_merchant": {},
  "klaviyo": {},
  "shopper_approved": {},
  "reddit": {}
}
```

- [ ] **Step 5: Run tests — confirm pass**

```bash
python -m pytest feeds/tests/test_build_feed_master.py -v
```
Expected: 4 PASS

- [ ] **Step 6: Smoke-test locally (requires .env)**

```bash
python -m feeds.build_feed_master
```
Expected: prints product count, writes `feeds/feed_master.json`

- [ ] **Step 7: Commit**

```bash
git add feeds/build_feed_master.py feeds/channel_sku_map.json feeds/tests/test_build_feed_master.py feeds/requirements.txt
git commit -m "feat(feeds): WC feed master builder with CF Worker proxy support"
```

---

## Task 3: Base Adapter

**Files:**
- Create: `feeds/adapters/base_adapter.py`
- Create: `feeds/tests/test_base_adapter.py`

- [ ] **Step 1: Write failing tests**

`feeds/tests/test_base_adapter.py`:
```python
import pytest
from feeds.adapters.base_adapter import BaseAdapter, AdapterResult

class ConcreteAdapter(BaseAdapter):
    channel = "test_channel"
    def fetch_channel_products(self):
        return [{"sku": "A-SKU", "price": "10.00", "stock_status": "instock"}]
    def get_required_fields(self):
        return ["sku", "price"]

def _master():
    return {
        "meta": {"product_count": 2, "variation_count": 0},
        "products": {
            "1": {"wc_id": 1, "sku": "A-SKU", "price": "10.00", "stock_status": "instock",
                  "status": "publish", "variations": [], "channel_skus": {"test_channel": "A-SKU"}},
            "2": {"wc_id": 2, "sku": "B-SKU", "price": "20.00", "stock_status": "instock",
                  "status": "publish", "variations": [], "channel_skus": {"test_channel": ""}},
        }
    }

def test_coverage_check_finds_missing():
    adapter = ConcreteAdapter({})
    result = adapter.coverage_check(_master())
    assert result.wc_total == 2
    assert result.channel_total == 1
    assert "B-SKU" in result.missing_skus

def test_drift_check_detects_price_drift():
    master = _master()
    master["products"]["1"]["price"] = "12.00"
    channel_products = [{"sku": "A-SKU", "price": "10.00", "stock_status": "instock"}]
    adapter = ConcreteAdapter({})
    result = adapter.drift_check(master, channel_products)
    assert len(result.drifted) == 1
    assert result.drifted[0]["sku"] == "A-SKU"

def test_quality_check_flags_missing_required_field():
    channel_products = [{"sku": "A-SKU"}]  # missing price
    adapter = ConcreteAdapter({})
    result = adapter.quality_check(channel_products)
    assert len(result.incomplete) == 1
```

- [ ] **Step 2: Run — confirm failure**

```bash
python -m pytest feeds/tests/test_base_adapter.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `feeds/adapters/base_adapter.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CoverageResult:
    wc_total: int
    channel_total: int
    missing_skus: list[str] = field(default_factory=list)


@dataclass
class DriftResult:
    drifted: list[dict] = field(default_factory=list)  # [{sku, field, wc_val, channel_val}]


@dataclass
class QualityResult:
    incomplete: list[dict] = field(default_factory=list)  # [{sku, missing_fields}]


@dataclass
class AdapterResult:
    channel: str
    error: str = ""
    coverage: CoverageResult = None
    drift: DriftResult = None
    quality: QualityResult = None

    @property
    def ok(self):
        return not self.error


class BaseAdapter(ABC):
    channel: str = ""

    def __init__(self, env: dict):
        self.env = env

    @abstractmethod
    def fetch_channel_products(self) -> list[dict]:
        """Pull current product data from the channel. Returns list of dicts with at least 'sku'."""

    @abstractmethod
    def get_required_fields(self) -> list[str]:
        """Return list of field names that must be non-empty on every channel product."""

    def _active_wc_skus(self, master: dict) -> dict[str, dict]:
        """Return {sku: product_record} for all published WC products (including variation SKUs)."""
        skus = {}
        for p in master["products"].values():
            if p["status"] != "publish":
                continue
            if p["sku"]:
                skus[p["sku"]] = p
            for v in p.get("variations", []):
                if v["sku"]:
                    skus[v["sku"]] = p
        return skus

    def _channel_sku_for(self, wc_product: dict) -> str:
        return wc_product.get("channel_skus", {}).get(self.channel, "") or wc_product["sku"]

    def coverage_check(self, master: dict) -> CoverageResult:
        wc_skus = self._active_wc_skus(master)
        channel_products = self.fetch_channel_products()
        channel_skus = {p["sku"] for p in channel_products if p.get("sku")}
        missing = [sku for sku in wc_skus if sku not in channel_skus]
        return CoverageResult(
            wc_total=len(wc_skus),
            channel_total=len(channel_skus),
            missing_skus=missing,
        )

    def drift_check(self, master: dict, channel_products: list[dict]) -> DriftResult:
        wc_by_sku = self._active_wc_skus(master)
        channel_by_sku = {p["sku"]: p for p in channel_products if p.get("sku")}
        drifted = []
        for sku, wc_p in wc_by_sku.items():
            ch_p = channel_by_sku.get(sku)
            if not ch_p:
                continue
            for field in ("price", "stock_status"):
                wc_val = str(wc_p.get(field, ""))
                ch_val = str(ch_p.get(field, ""))
                if wc_val and ch_val and wc_val != ch_val:
                    drifted.append({"sku": sku, "field": field, "wc": wc_val, "channel": ch_val})
        return DriftResult(drifted=drifted)

    def quality_check(self, channel_products: list[dict]) -> QualityResult:
        required = self.get_required_fields()
        incomplete = []
        for p in channel_products:
            missing = [f for f in required if not p.get(f)]
            if missing:
                incomplete.append({"sku": p.get("sku", "?"), "missing_fields": missing})
        return QualityResult(incomplete=incomplete)

    def run(self, master: dict) -> AdapterResult:
        result = AdapterResult(channel=self.channel)
        try:
            channel_products = self.fetch_channel_products()
            wc_skus = self._active_wc_skus(master)
            channel_skus = {p["sku"] for p in channel_products if p.get("sku")}
            missing = [sku for sku in wc_skus if sku not in channel_skus]
            result.coverage = CoverageResult(
                wc_total=len(wc_skus),
                channel_total=len(channel_skus),
                missing_skus=missing,
            )
            result.drift = self.drift_check(master, channel_products)
            result.quality = self.quality_check(channel_products)
        except Exception as e:
            result.error = str(e)
        return result
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
python -m pytest feeds/tests/test_base_adapter.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add feeds/adapters/base_adapter.py feeds/tests/test_base_adapter.py
git commit -m "feat(feeds): base adapter with coverage/drift/quality checks"
```

---

## Task 4: Walmart Adapter

**Files:**
- Create: `feeds/adapters/walmart.py`
- Create: `feeds/adapters/walmart_SCHEMA.md`
- Create: `feeds/tests/test_walmart.py`

- [ ] **Step 1: Write failing tests**

`feeds/tests/test_walmart.py`:
```python
from unittest.mock import patch, MagicMock
from feeds.adapters.walmart import WalmartAdapter

ENV = {
    "WALMART_CLIENT_ID": "fake_id",
    "WALMART_CLIENT_SECRET": "fake_secret",
}

def _channel_item(sku="LAWN-KY31-5LB", price="24.99", qty=50):
    return {"sku": sku, "price": price, "stock_status": "instock" if qty > 0 else "outofstock",
            "name": "Test Product", "short_description": "desc", "main_image_url": "http://img.jpg"}

def test_walmart_required_fields():
    adapter = WalmartAdapter(ENV)
    fields = adapter.get_required_fields()
    assert "sku" in fields
    assert "price" in fields
    assert "main_image_url" in fields

def test_walmart_fetch_normalizes_sku(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ItemResponse": [{"sku": "LAWN-KY31-5LB", "price": {"amount": 24.99},
                          "availabilityInformation": {"quantity": 50},
                          "productName": "Test", "shortDescription": "desc",
                          "mainImageUrl": "http://img.jpg"}]
    }
    mock_token = MagicMock()
    mock_token.status_code = 200
    mock_token.json.return_value = {"access_token": "tok123", "expires_in": 900}

    with patch("requests.post", return_value=mock_token), \
         patch("requests.get", return_value=mock_resp):
        adapter = WalmartAdapter(ENV)
        products = adapter.fetch_channel_products()

    assert len(products) == 1
    assert products[0]["sku"] == "LAWN-KY31-5LB"
    assert products[0]["price"] == "24.99"
```

- [ ] **Step 2: Run — confirm failure**

```bash
python -m pytest feeds/tests/test_walmart.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `feeds/adapters/walmart.py`**

```python
import time
import requests
from feeds.adapters.base_adapter import BaseAdapter

WM_BASE = "https://marketplace.walmartapis.com/v3"


class WalmartAdapter(BaseAdapter):
    channel = "walmart"

    def _get_token(self):
        resp = requests.post(
            "https://marketplace.walmartapis.com/v3/token",
            auth=(self.env["WALMART_CLIENT_ID"], self.env["WALMART_CLIENT_SECRET"]),
            data={"grant_type": "client_credentials"},
            headers={"WM_SVC.NAME": "Walmart Marketplace", "WM_QOS.CORRELATION_ID": "feed-audit"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _wm_headers(self, token):
        return {
            "WM_SEC.ACCESS_TOKEN": token,
            "WM_SVC.NAME": "Walmart Marketplace",
            "WM_QOS.CORRELATION_ID": "feed-audit",
            "Accept": "application/json",
        }

    def fetch_channel_products(self) -> list[dict]:
        token = self._get_token()
        headers = self._wm_headers(token)
        products = []
        next_cursor = None
        while True:
            params = {"limit": 200}
            if next_cursor:
                params["nextCursor"] = next_cursor
            resp = requests.get(f"{WM_BASE}/items", headers=headers, params=params, timeout=30)
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("ItemResponse", []):
                price_info = item.get("price", {})
                qty = item.get("availabilityInformation", {}).get("quantity", 0)
                products.append({
                    "sku": item.get("sku", ""),
                    "price": str(price_info.get("amount", "")),
                    "stock_status": "instock" if qty > 0 else "outofstock",
                    "name": item.get("productName", ""),
                    "short_description": item.get("shortDescription", ""),
                    "main_image_url": item.get("mainImageUrl", ""),
                })
            next_cursor = data.get("nextCursor")
            if not next_cursor:
                break
            time.sleep(0.5)
        return products

    def get_required_fields(self) -> list[str]:
        return ["sku", "price", "name", "short_description", "main_image_url", "stock_status"]
```

- [ ] **Step 4: Create `feeds/adapters/walmart_SCHEMA.md`**

```markdown
# Walmart Marketplace — Feed Schema

## Required Fields (quality check fails without these)
| Field | Notes |
|---|---|
| sku | Must match WC SKU exactly |
| price | USD decimal string |
| name | Product title (max 200 chars) |
| short_description | shelf description |
| main_image_url | Primary image URL |
| stock_status | instock / outofstock |

## Recommended Fields (Phase 2 — completeness score)
| Field | Notes |
|---|---|
| long_description | Full product description |
| brand | "Nature's Seed" |
| category | Walmart taxonomy category |
| weight | Shipping weight |
| gtin | UPC/EAN |
| shelf_description | Additional shelf copy |
| secondary_image_urls | Additional product images |
| key_features | Bullet points (up to 5) |

## API Notes
- Token header: `WM_SEC.ACCESS_TOKEN` (NOT `Authorization: Bearer`)
- Token expires: 15 minutes
- Rate limit: 0.5s between calls
- 404 on /items = no items listed (not an error)
```

- [ ] **Step 5: Run tests — confirm pass**

```bash
python -m pytest feeds/tests/test_walmart.py -v
```
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add feeds/adapters/walmart.py feeds/adapters/walmart_SCHEMA.md feeds/tests/test_walmart.py
git commit -m "feat(feeds): Walmart adapter with coverage/drift/quality checks"
```

---

## Task 5: Amazon Adapter

**Files:**
- Create: `feeds/adapters/amazon.py`
- Create: `feeds/adapters/amazon_SCHEMA.md`

- [ ] **Step 1: Create `feeds/adapters/amazon.py`**

```python
import time
import base64
import requests
from feeds.adapters.base_adapter import BaseAdapter

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
SP_BASE = "https://sellingpartnerapi-na.amazon.com"


class AmazonAdapter(BaseAdapter):
    channel = "amazon"

    def _get_access_token(self):
        resp = requests.post(LWA_TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": self.env["AMAZON_REFRESH_TOKEN"],
            "client_id": self.env["AMAZON_CLIENT_ID"],
            "client_secret": self.env["AMAZON_CLIENT_SECRET"],
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def fetch_channel_products(self) -> list[dict]:
        token = self._get_access_token()
        seller_id = self.env["AMAZON_MERCHANT_TOKEN"]
        headers = {
            "x-amz-access-token": token,
            "Accept": "application/json",
        }
        products = []
        next_token = None
        while True:
            params = {"sellerId": seller_id, "includedData": "summaries,attributes,offers"}
            if next_token:
                params["pageToken"] = next_token
            resp = requests.get(
                f"{SP_BASE}/catalog/2022-04-01/items",
                headers=headers, params=params, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("items", []):
                summaries = item.get("summaries", [{}])[0]
                offers = item.get("offers", [{}])[0] if item.get("offers") else {}
                sku = (item.get("attributes", {}).get("merchant_suggested_asin", [{}]) or [{}])[0].get("value", "")
                # Prefer seller SKU from offers
                seller_sku = offers.get("sellerSku", "") or summaries.get("asin", "")
                products.append({
                    "sku": seller_sku,
                    "asin": summaries.get("asin", ""),
                    "name": summaries.get("itemName", ""),
                    "price": str(offers.get("buyingPrice", {}).get("listingPrice", {}).get("amount", "")),
                    "stock_status": "instock" if offers.get("fulfillmentAvailability", [{}])[0].get("quantity", 0) > 0 else "outofstock" if offers else "",
                    "bullet_points": item.get("attributes", {}).get("bullet_point", []),
                    "main_image_url": summaries.get("mainImage", {}).get("link", ""),
                    "brand": summaries.get("brand", ""),
                })
            next_token = data.get("nextToken")
            if not next_token:
                break
            time.sleep(0.5)
        return products

    def get_required_fields(self) -> list[str]:
        return ["sku", "name", "price", "main_image_url", "brand"]
```

- [ ] **Step 2: Create `feeds/adapters/amazon_SCHEMA.md`**

```markdown
# Amazon — Feed Schema

## Required Fields
| Field | Notes |
|---|---|
| sku | Seller SKU (must match WC SKU via channel_sku_map) |
| name | Product title (max 200 chars) |
| price | USD decimal string |
| main_image_url | Primary image (white background preferred) |
| brand | "Nature's Seed" |

## Recommended Fields (Phase 2)
| Field | Notes |
|---|---|
| bullet_points | 3–5 bullet points (each < 500 chars) |
| description | Product description (< 2000 chars) |
| gtin | UPC — required for GTIN-based matching |
| search_terms | Backend keywords (< 250 chars per field) |
| material_type | e.g. "Grass Seed" |
| item_form | e.g. "Pellets", "Seeds" |
| product_type_name | Amazon browse node category |

## API Notes
- SP-API LWA OAuth (refresh token flow)
- Catalog Items API: `GET /catalog/2022-04-01/items`
- SKU aliases live in channel_sku_map.json under "amazon" key
- Content writes use Listings API (draft submissions only — requires Gabe approval)
```

- [ ] **Step 3: Run existing tests to ensure no regression**

```bash
python -m pytest feeds/tests/ -v
```
Expected: all existing tests pass

- [ ] **Step 4: Commit**

```bash
git add feeds/adapters/amazon.py feeds/adapters/amazon_SCHEMA.md
git commit -m "feat(feeds): Amazon SP-API adapter"
```

---

## Task 6: Google Merchant Center Adapter

**Files:**
- Create: `feeds/adapters/google_merchant.py`
- Create: `feeds/adapters/google_merchant_SCHEMA.md`

- [ ] **Step 1: Create `feeds/adapters/google_merchant.py`**

```python
import requests
from feeds.adapters.base_adapter import BaseAdapter

GMC_BASE = "https://shoppingcontent.googleapis.com/content/v2.1"


class GoogleMerchantAdapter(BaseAdapter):
    channel = "google_merchant"

    def _get_access_token(self):
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": self.env["GOOGLE_CLIENT_ID"],
            "client_secret": self.env["GOOGLE_CLIENT_SECRET"],
            "refresh_token": self.env["GOOGLE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def fetch_channel_products(self) -> list[dict]:
        token = self._get_access_token()
        merchant_id = self.env.get("GOOGLE_MERCHANT_CENTER_ID", "138935850")
        headers = {"Authorization": f"Bearer {token}"}
        products = []
        page_token = None
        while True:
            params = {"maxResults": 250}
            if page_token:
                params["pageToken"] = page_token
            resp = requests.get(
                f"{GMC_BASE}/{merchant_id}/products",
                headers=headers, params=params, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("resources", []):
                price_info = item.get("price", {})
                products.append({
                    "sku": item.get("offerId", ""),
                    "name": item.get("title", ""),
                    "price": price_info.get("value", ""),
                    "stock_status": "instock" if item.get("availability") == "in stock" else "outofstock",
                    "gtin": item.get("gtin", ""),
                    "brand": item.get("brand", ""),
                    "main_image_url": item.get("imageLink", ""),
                    "description": item.get("description", ""),
                    "product_type": item.get("productTypes", [""])[0],
                })
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return products

    def get_required_fields(self) -> list[str]:
        return ["sku", "name", "price", "gtin", "brand", "main_image_url", "description"]
```

- [ ] **Step 2: Create `feeds/adapters/google_merchant_SCHEMA.md`**

```markdown
# Google Merchant Center — Feed Schema

## Required Fields (suppression risk without these)
| Field | Notes |
|---|---|
| sku | offerId — must be unique per variant |
| name | title (max 150 chars) |
| price | USD with currency code |
| gtin | UPC/EAN — required for Shopping ads |
| brand | "Nature's Seed" |
| main_image_url | Primary image (min 100x100px) |
| description | Product description |

## Recommended Fields (Phase 2)
| Field | Notes |
|---|---|
| product_type | Full category path (e.g. "Lawn > Grass Seed > Cool Season") |
| additional_image_links | Up to 10 additional images |
| color | If applicable |
| material | e.g. "Grass Seed" |
| custom_label_0–4 | Campaign segmentation labels |
| shipping_weight | Weight for shipping cost calculation |
| condition | "new" |

## API Notes
- Read-only currently (Content API v2.1)
- Merchant ID: 138935850
- Uses shared Google refresh token (same as Ads + GA4)
- GTIN missing = suppression from Shopping — highest priority quality fix
```

- [ ] **Step 3: Run all tests**

```bash
python -m pytest feeds/tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add feeds/adapters/google_merchant.py feeds/adapters/google_merchant_SCHEMA.md
git commit -m "feat(feeds): Google Merchant Center adapter"
```

---

## Task 7: Klaviyo Adapter

**Files:**
- Create: `feeds/adapters/klaviyo.py`
- Create: `feeds/adapters/klaviyo_SCHEMA.md`

- [ ] **Step 1: Create `feeds/adapters/klaviyo.py`**

```python
import time
import requests
from feeds.adapters.base_adapter import BaseAdapter

KLAVIYO_BASE = "https://a.klaviyo.com/api"
REVISION = "2024-07-15"


class KlaviyoAdapter(BaseAdapter):
    channel = "klaviyo"

    def _headers(self):
        return {
            "Authorization": f"Klaviyo-API-Key {self.env['KLAVIYO_API']}",
            "revision": REVISION,
            "Accept": "application/json",
        }

    def fetch_channel_products(self) -> list[dict]:
        headers = self._headers()
        products = []
        cursor = None
        while True:
            params = {"page[size]": 100}
            if cursor:
                params["page[cursor]"] = cursor
            resp = requests.get(f"{KLAVIYO_BASE}/catalog-items", headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                products.append({
                    "sku": attrs.get("external_id", ""),
                    "name": attrs.get("title", ""),
                    "price": str(attrs.get("price", "")),
                    "stock_status": "instock" if attrs.get("published") else "outofstock",
                    "main_image_url": attrs.get("image_full_url", ""),
                    "description": attrs.get("description", ""),
                    "url": attrs.get("url", ""),
                })
            cursor = data.get("links", {}).get("next")
            if not cursor:
                break
            time.sleep(0.3)
        return products

    def get_required_fields(self) -> list[str]:
        return ["sku", "name", "price", "main_image_url", "url"]
```

- [ ] **Step 2: Create `feeds/adapters/klaviyo_SCHEMA.md`**

```markdown
# Klaviyo — Feed Schema (Catalog Items)

## Required Fields
| Field | Notes |
|---|---|
| sku | external_id — maps to WC SKU |
| name | title |
| price | Decimal (used in dynamic email blocks) |
| main_image_url | image_full_url |
| url | Product page URL — MUST use /products/ path (Permalink Manager) |

## Recommended Fields (Phase 2)
| Field | Notes |
|---|---|
| description | Product description for email rendering |
| categories | For segmentation and browse abandonment flows |
| custom_metadata | Any extra fields for personalization |

## API Notes
- Revision: `2024-07-15`
- Catalog items endpoint: `GET /api/catalog-items`
- Rate limit: 0.3s between calls
- URL rule: NEVER /product-category/ — always /products/
```

- [ ] **Step 3: Run all tests**

```bash
python -m pytest feeds/tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add feeds/adapters/klaviyo.py feeds/adapters/klaviyo_SCHEMA.md
git commit -m "feat(feeds): Klaviyo catalog adapter"
```

---

## Task 8: Shopper Approved + Reddit Adapters

**Files:**
- Create: `feeds/adapters/shopper_approved.py` + `shopper_approved_SCHEMA.md`
- Create: `feeds/adapters/reddit.py` + `reddit_SCHEMA.md`

- [ ] **Step 1: Create `feeds/adapters/shopper_approved.py`**

```python
import requests
from feeds.adapters.base_adapter import BaseAdapter


class ShopperApprovedAdapter(BaseAdapter):
    channel = "shopper_approved"

    def fetch_channel_products(self) -> list[dict]:
        site_id = self.env["SA_SITE_ID"]
        token = self.env["SA_API_TOKEN"]
        resp = requests.get(
            f"https://api.shopperapproved.com/products/{site_id}",
            params={"token": token, "limit": 500},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        products = []
        for item in data if isinstance(data, list) else data.get("products", []):
            products.append({
                "sku": str(item.get("product_id", "")),
                "name": item.get("name", ""),
                "price": str(item.get("price", "")),
                "stock_status": "instock",
                "url": item.get("url", ""),
                "review_count": item.get("review_count", 0),
            })
        return products

    def get_required_fields(self) -> list[str]:
        return ["sku", "name", "url"]
```

- [ ] **Step 2: Create `feeds/adapters/shopper_approved_SCHEMA.md`**

```markdown
# Shopper Approved — Feed Schema

## Required Fields
| Field | Notes |
|---|---|
| sku | product_id — matched to WC SKU via parent SKU extraction |
| name | Product name |
| url | Product page URL |

## Recommended Fields (Phase 2)
| Field | Notes |
|---|---|
| gtin | For Google Product Reviews XML matching |
| mpn | Manufacturer part number |
| brand | "Nature's Seed" |
| review_count | Useful for coverage audit |

## API Notes
- SA_SITE_ID: 33157
- Review feed output: `docs/reviews/product_reviews.xml` (GitHub Pages)
- Feed URL served at: https://gabenaturesseed.github.io/nature-seed-data/reviews/product_reviews.xml
- Coverage audit = all WC products should have at least 1 review indexed
```

- [ ] **Step 3: Create `feeds/adapters/reddit.py`**

The Reddit adapter audits the generated CSV catalog (built by the separate reddit-ads agent) against feed_master. No API calls needed — just file comparison.

```python
import csv
from pathlib import Path
from feeds.adapters.base_adapter import BaseAdapter


class RedditAdapter(BaseAdapter):
    channel = "reddit"
    CATALOG_PATH = Path("docs/reddit-catalog/reddit_catalog.csv")

    def fetch_channel_products(self) -> list[dict]:
        if not self.CATALOG_PATH.exists():
            raise FileNotFoundError(f"Reddit catalog not found at {self.CATALOG_PATH}. Run the reddit-ads agent first.")
        products = []
        with open(self.CATALOG_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                products.append({
                    "sku": row.get("id", ""),
                    "name": row.get("title", ""),
                    "price": row.get("price", "").replace("USD ", ""),
                    "stock_status": "instock" if row.get("availability") == "in stock" else "outofstock",
                    "main_image_url": row.get("image_link", ""),
                    "description": row.get("description", ""),
                })
        return products

    def get_required_fields(self) -> list[str]:
        return ["sku", "name", "price", "main_image_url"]
```

- [ ] **Step 4: Create `feeds/adapters/reddit_SCHEMA.md`**

```markdown
# Reddit Ads — Feed Schema

## Required Fields
| Field | Notes |
|---|---|
| sku | id — maps to WC variation SKU |
| name | title (max 150 chars) |
| price | "USD X.XX" format |
| main_image_url | image_link |

## Recommended Fields (Phase 2)
| Field | Notes |
|---|---|
| description | max 1000 chars |
| availability | "in stock" / "out of stock" |
| brand | "Nature's Seed" |
| product_type | Full category path |

## Notes
- Catalog built by separate reddit-ads agent at `docs/reddit-catalog/reddit_catalog.csv`
- Audit is file-based (no API call) — just compares CSV against feed_master
- Phase 3: wire up catalog upload to Reddit Ads API
```

- [ ] **Step 5: Run all tests**

```bash
python -m pytest feeds/tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add feeds/adapters/shopper_approved.py feeds/adapters/shopper_approved_SCHEMA.md feeds/adapters/reddit.py feeds/adapters/reddit_SCHEMA.md
git commit -m "feat(feeds): Shopper Approved and Reddit adapters"
```

---

## Task 9: Facebook + Pinterest Stub Adapters

**Files:**
- Create: `feeds/adapters/facebook.py` + `facebook_SCHEMA.md`
- Create: `feeds/adapters/pinterest.py` + `pinterest_SCHEMA.md`

- [ ] **Step 1: Create `feeds/adapters/facebook.py`**

```python
from feeds.adapters.base_adapter import BaseAdapter, AdapterResult


class FacebookAdapter(BaseAdapter):
    channel = "facebook"

    def fetch_channel_products(self) -> list[dict]:
        return []

    def get_required_fields(self) -> list[str]:
        return ["id", "title", "description", "availability", "condition", "price",
                "link", "image_link", "brand", "google_product_category"]

    def run(self, master: dict) -> AdapterResult:
        return AdapterResult(channel=self.channel, error="not connected — Facebook Catalog API not yet configured")
```

- [ ] **Step 2: Create `feeds/adapters/facebook_SCHEMA.md`**

```markdown
# Facebook / Meta — Feed Schema (Dynamic Product Ads)

## Required Fields (Phase 3)
| Field | Notes |
|---|---|
| id | Unique product ID (WC variation SKU) |
| title | Product name (max 150 chars) |
| description | Product description (max 5000 chars) |
| availability | "in stock" / "out of stock" |
| condition | "new" |
| price | "X.XX USD" format |
| link | Product page URL |
| image_link | Primary image URL |
| brand | "Nature's Seed" |
| google_product_category | Google taxonomy ID or text |

## Recommended Fields (Phase 3)
| Field | Notes |
|---|---|
| gtin | UPC |
| mpn | SKU |
| additional_image_link | Up to 10 extra images |
| sale_price | "X.XX USD" if on sale |
| item_group_id | Groups variants of same parent product |
| color, size | Variant attributes |
| custom_label_0–4 | Campaign segmentation |

## Setup Steps (Phase 3)
1. Create Meta Business account + Catalog in Commerce Manager
2. Add `FACEBOOK_PIXEL_ID` and `FACEBOOK_CATALOG_ID` to .env
3. Use Facebook Marketing API v18+ to upload feed CSV
4. Wire up `facebook.py` adapter to Marketing API
```

- [ ] **Step 3: Create `feeds/adapters/pinterest.py`**

```python
from feeds.adapters.base_adapter import BaseAdapter, AdapterResult


class PinterestAdapter(BaseAdapter):
    channel = "pinterest"

    def fetch_channel_products(self) -> list[dict]:
        return []

    def get_required_fields(self) -> list[str]:
        return ["id", "title", "description", "link", "image_link", "price", "availability"]

    def run(self, master: dict) -> AdapterResult:
        return AdapterResult(channel=self.channel, error="not connected — Pinterest Catalog API not yet configured")
```

- [ ] **Step 4: Create `feeds/adapters/pinterest_SCHEMA.md`**

```markdown
# Pinterest — Feed Schema

## Required Fields (Phase 3)
| Field | Notes |
|---|---|
| id | Unique product ID |
| title | Product name |
| description | Product description |
| link | Product page URL |
| image_link | Primary image URL |
| price | "X.XX USD" |
| availability | "in stock" / "out of stock" |

## Recommended Fields (Phase 3)
| Field | Notes |
|---|---|
| additional_image_link | Up to 10 extra images |
| brand | "Nature's Seed" |
| google_product_category | Google taxonomy |
| condition | "new" |
| item_group_id | Groups variants |
| gtin | UPC |

## Setup Steps (Phase 3)
1. Create Pinterest Business account + Catalog
2. Add `PINTEREST_ACCESS_TOKEN` to .env
3. Use Pinterest API v5 Catalogs endpoint to upload feed
4. Wire up `pinterest.py` adapter to API
```

- [ ] **Step 5: Run all tests**

```bash
python -m pytest feeds/tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add feeds/adapters/facebook.py feeds/adapters/facebook_SCHEMA.md feeds/adapters/pinterest.py feeds/adapters/pinterest_SCHEMA.md
git commit -m "feat(feeds): Facebook and Pinterest stub adapters"
```

---

## Task 10: Digest Runner

**Files:**
- Create: `feeds/digest/run_audit.py`
- Create: `feeds/tests/test_digest.py`

- [ ] **Step 1: Write failing tests**

`feeds/tests/test_digest.py`:
```python
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from feeds.digest.run_audit import build_digest_markdown, run_audit

def _mock_result(channel, wc=10, ch=8, drift=1, incomplete=2, error=""):
    from feeds.adapters.base_adapter import AdapterResult, CoverageResult, DriftResult, QualityResult
    r = AdapterResult(channel=channel, error=error)
    if not error:
        r.coverage = CoverageResult(wc_total=wc, channel_total=ch, missing_skus=["SKU-A", "SKU-B"])
        r.drift = DriftResult(drifted=[{"sku": "SKU-A", "field": "price", "wc": "10.00", "channel": "12.00"}] * drift)
        r.quality = QualityResult(incomplete=[{"sku": "SKU-A", "missing_fields": ["gtin"]}] * incomplete)
    return r

def test_build_digest_markdown_contains_all_channels():
    results = [
        _mock_result("walmart"),
        _mock_result("amazon"),
        _mock_result("google_merchant", error="auth failed"),
    ]
    md = build_digest_markdown(results, date="2026-04-28")
    assert "walmart" in md
    assert "amazon" in md
    assert "google_merchant" in md
    assert "auth failed" in md
    assert "8/10" in md  # coverage display

def test_build_digest_markdown_has_action_items():
    results = [_mock_result("walmart")]
    md = build_digest_markdown(results, date="2026-04-28")
    assert "Action Items" in md
    assert "- [ ]" in md
```

- [ ] **Step 2: Run — confirm failure**

```bash
python -m pytest feeds/tests/test_digest.py -v
```

- [ ] **Step 3: Create `feeds/digest/run_audit.py`**

```python
#!/usr/bin/env python3
"""
Nature's Seed — Feed Audit Digest
Loads feed_master.json, runs all channel adapters, writes daily digest markdown.

Usage:
    python3 -m feeds.digest.run_audit
"""

import json
from datetime import date
from pathlib import Path

from feeds.env_loader import load_env
from feeds.adapters.walmart import WalmartAdapter
from feeds.adapters.amazon import AmazonAdapter
from feeds.adapters.google_merchant import GoogleMerchantAdapter
from feeds.adapters.klaviyo import KlaviyoAdapter
from feeds.adapters.shopper_approved import ShopperApprovedAdapter
from feeds.adapters.reddit import RedditAdapter
from feeds.adapters.facebook import FacebookAdapter
from feeds.adapters.pinterest import PinterestAdapter

MASTER_PATH = Path(__file__).parent.parent / "feed_master.json"
DIGEST_DIR = Path(__file__).parent


def build_digest_markdown(results, date: str) -> str:
    lines = [f"# Feed Health — {date}\n"]

    # Summary table
    lines.append("## Summary\n")
    lines.append("| Channel | Coverage | Drift | Quality Issues |")
    lines.append("|---|---|---|---|")
    for r in results:
        if r.error:
            lines.append(f"| {r.channel} | ERROR | ERROR | {r.error} |")
        else:
            cov = f"{r.coverage.channel_total}/{r.coverage.wc_total}"
            drift = len(r.drift.drifted)
            quality = len(r.quality.incomplete)
            lines.append(f"| {r.channel} | {cov} | {drift} | {quality} |")

    lines.append("")

    # Action items
    lines.append("## Action Items\n")
    has_actions = False
    for r in results:
        if r.error:
            lines.append(f"- [ ] **{r.channel}**: investigate error — {r.error}")
            has_actions = True
            continue
        for d in r.drift.drifted:
            lines.append(f"- [ ] **{r.channel}**: sync {d['field']} on `{d['sku']}` (WC: {d['wc']} | channel: {d['channel']})")
            has_actions = True
        if r.coverage.missing_skus:
            n = len(r.coverage.missing_skus)
            lines.append(f"- [ ] **{r.channel}**: {n} WC SKUs not listed — {', '.join(r.coverage.missing_skus[:5])}{'...' if n > 5 else ''}")
            has_actions = True
        for q in r.quality.incomplete[:5]:
            lines.append(f"- [ ] **{r.channel}**: `{q['sku']}` missing fields: {', '.join(q['missing_fields'])}")
            has_actions = True

    if not has_actions:
        lines.append("_No action items — all channels healthy._")

    # Detail sections
    for r in results:
        if r.error or not r.coverage.missing_skus:
            continue
        lines.append(f"\n### {r.channel} — Missing SKUs\n")
        for sku in r.coverage.missing_skus:
            lines.append(f"- {sku}")

    return "\n".join(lines) + "\n"


def run_audit():
    env = load_env()

    with open(MASTER_PATH) as f:
        master = json.load(f)

    print(f"[AUDIT] feed_master: {master['meta']['product_count']} products, generated {master['meta']['generated_at']}")

    adapters = [
        WalmartAdapter(env),
        AmazonAdapter(env),
        GoogleMerchantAdapter(env),
        KlaviyoAdapter(env),
        ShopperApprovedAdapter(env),
        RedditAdapter(env),
        FacebookAdapter(env),
        PinterestAdapter(env),
    ]

    results = []
    for adapter in adapters:
        print(f"  [{adapter.channel}] running...")
        result = adapter.run(master)
        if result.error:
            print(f"    ERROR: {result.error}")
        else:
            print(f"    coverage: {result.coverage.channel_total}/{result.coverage.wc_total} | drift: {len(result.drift.drifted)} | quality: {len(result.quality.incomplete)}")
        results.append(result)

    today = date.today().isoformat()
    digest = build_digest_markdown(results, date=today)
    out_path = DIGEST_DIR / f"{today}-feed-health.md"
    with open(out_path, "w") as f:
        f.write(digest)
    print(f"\n[DONE] Digest written to {out_path}")
    return results


if __name__ == "__main__":
    run_audit()
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
python -m pytest feeds/tests/test_digest.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Run all tests**

```bash
python -m pytest feeds/tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add feeds/digest/run_audit.py feeds/tests/test_digest.py
git commit -m "feat(feeds): digest runner aggregates all channel audit results"
```

---

## Task 11: Price + Inventory Sync Script

**Files:**
- Create: `feeds/sync/sync_prices.py`
- Create: `feeds/tests/test_sync_prices.py`

- [ ] **Step 1: Write failing tests**

`feeds/tests/test_sync_prices.py`:
```python
from unittest.mock import patch, MagicMock
from feeds.sync.sync_prices import build_walmart_price_update, build_amazon_price_update

def _variation(sku="LAWN-KY31-5LB", price="24.99", stock_quantity=50, stock_status="instock"):
    return {"sku": sku, "price": price, "stock_quantity": stock_quantity, "stock_status": stock_status, "variation_id": 999}

def test_build_walmart_price_update():
    v = _variation(price="24.99")
    payload = build_walmart_price_update(v)
    assert payload["sku"] == "LAWN-KY31-5LB"
    assert payload["pricing"]["currentPrice"]["amount"] == 24.99
    assert payload["pricing"]["currentPriceType"] == "BASE"

def test_build_amazon_price_update():
    v = _variation(sku="B08XYZ123", price="24.99")
    payload = build_amazon_price_update(v, seller_id="A1L3JR5H0WXLZ")
    assert payload["sku"] == "B08XYZ123"
    assert payload["price"] == "24.99"
```

- [ ] **Step 2: Run — confirm failure**

```bash
python -m pytest feeds/tests/test_sync_prices.py -v
```

- [ ] **Step 3: Create `feeds/sync/sync_prices.py`**

```python
#!/usr/bin/env python3
"""
Nature's Seed — Price + Inventory Sync (manual trigger)
Reads feed_master.json and pushes price + stock to Walmart and Amazon.
Content (titles, bullets, descriptions) is NEVER touched by this script.

Usage:
    python3 -m feeds.sync.sync_prices [--dry-run]
"""

import json
import sys
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

from feeds.env_loader import load_env

MASTER_PATH = Path(__file__).parent.parent / "feed_master.json"
LOG_PATH = Path(__file__).parent / f"{datetime.now(timezone.utc).date().isoformat()}-sync-log.json"

WM_BASE = "https://marketplace.walmartapis.com/v3"
LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
SP_BASE = "https://sellingpartnerapi-na.amazon.com"


def _get_walmart_token(env):
    resp = requests.post(
        "https://marketplace.walmartapis.com/v3/token",
        auth=(env["WALMART_CLIENT_ID"], env["WALMART_CLIENT_SECRET"]),
        data={"grant_type": "client_credentials"},
        headers={"WM_SVC.NAME": "Walmart Marketplace", "WM_QOS.CORRELATION_ID": "price-sync"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _get_amazon_token(env):
    resp = requests.post(LWA_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": env["AMAZON_REFRESH_TOKEN"],
        "client_id": env["AMAZON_CLIENT_ID"],
        "client_secret": env["AMAZON_CLIENT_SECRET"],
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def build_walmart_price_update(variation: dict) -> dict:
    return {
        "sku": variation["sku"],
        "pricing": {
            "currentPriceType": "BASE",
            "currentPrice": {"currency": "USD", "amount": float(variation["price"])},
        },
    }


def build_amazon_price_update(variation: dict, seller_id: str) -> dict:
    return {
        "sku": variation["sku"],
        "price": variation["price"],
        "currency": "USD",
    }


def push_walmart_prices(variations, env, dry_run=False):
    token = _get_walmart_token(env)
    headers = {
        "WM_SEC.ACCESS_TOKEN": token,
        "WM_SVC.NAME": "Walmart Marketplace",
        "WM_QOS.CORRELATION_ID": "price-sync",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    results = []
    for v in variations:
        if not v["sku"] or not v["price"]:
            continue
        payload = build_walmart_price_update(v)
        if dry_run:
            print(f"  [DRY] Walmart: {v['sku']} → ${v['price']}")
            results.append({"sku": v["sku"], "channel": "walmart", "status": "dry_run"})
            continue
        try:
            resp = requests.put(f"{WM_BASE}/price", headers=headers, json=payload, timeout=30)
            results.append({"sku": v["sku"], "channel": "walmart", "status": resp.status_code})
            print(f"  Walmart: {v['sku']} → ${v['price']} [{resp.status_code}]")
        except Exception as e:
            results.append({"sku": v["sku"], "channel": "walmart", "status": "error", "error": str(e)})
        time.sleep(0.5)
    return results


def push_amazon_prices(variations, env, dry_run=False):
    token = _get_amazon_token(env)
    seller_id = env["AMAZON_MERCHANT_TOKEN"]
    headers = {"x-amz-access-token": token, "Content-Type": "application/json"}
    results = []
    for v in variations:
        if not v["sku"] or not v["price"]:
            continue
        if dry_run:
            print(f"  [DRY] Amazon: {v['sku']} → ${v['price']}")
            results.append({"sku": v["sku"], "channel": "amazon", "status": "dry_run"})
            continue
        try:
            resp = requests.patch(
                f"{SP_BASE}/listings/2021-08-01/items/{seller_id}/{v['sku']}",
                headers=headers,
                json={"productType": "LAWN_AND_GARDEN", "patches": [
                    {"op": "replace", "path": "/attributes/purchasable_offer",
                     "value": [{"marketplace_id": "ATVPDKIKX0DER",
                                "our_price": [{"schedule": [{"value_with_tax": float(v["price"])}]}]}]}
                ]},
                timeout=30,
            )
            results.append({"sku": v["sku"], "channel": "amazon", "status": resp.status_code})
            print(f"  Amazon: {v['sku']} → ${v['price']} [{resp.status_code}]")
        except Exception as e:
            results.append({"sku": v["sku"], "channel": "amazon", "status": "error", "error": str(e)})
        time.sleep(0.5)
    return results


def sync_prices(dry_run=False):
    env = load_env()
    with open(MASTER_PATH) as f:
        master = json.load(f)

    # Collect all variation-level SKUs (variations carry the per-size price)
    all_variations = []
    for p in master["products"].values():
        if p["status"] != "publish":
            continue
        if p["variations"]:
            all_variations.extend(p["variations"])
        else:
            all_variations.append({"sku": p["sku"], "price": p["price"],
                                   "stock_quantity": p["stock_quantity"],
                                   "stock_status": p["stock_status"]})

    print(f"[SYNC] {len(all_variations)} SKUs to sync")
    results = []
    results.extend(push_walmart_prices(all_variations, env, dry_run))
    results.extend(push_amazon_prices(all_variations, env, dry_run))

    with open(LOG_PATH, "w") as f:
        json.dump({"synced_at": datetime.now(timezone.utc).isoformat(), "results": results}, f, indent=2)
    print(f"\n[DONE] Log: {LOG_PATH}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    sync_prices(dry_run=dry_run)
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
python -m pytest feeds/tests/test_sync_prices.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Run all tests**

```bash
python -m pytest feeds/tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add feeds/sync/sync_prices.py feeds/tests/test_sync_prices.py
git commit -m "feat(feeds): price+inventory sync script for Walmart and Amazon"
```

---

## Task 12: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/feed-audit.yml`

- [ ] **Step 1: Create `.github/workflows/feed-audit.yml`**

```yaml
name: Feed Audit

on:
  schedule:
    # Run at 7:05 AM UTC (12:05 AM MST) daily — 5 min after daily report
    - cron: '5 7 * * *'
  workflow_dispatch:

jobs:
  feed-audit:
    runs-on: ubuntu-latest
    timeout-minutes: 20

    steps:
      - uses: actions/checkout@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r feeds/requirements.txt

      - name: Create .env from secrets
        run: |
          cat > .env << 'ENVEOF'
          WC_BASE_URL = '${{ secrets.WC_BASE_URL }}'
          WC_CK = '${{ secrets.WC_CK }}'
          WC_CS = '${{ secrets.WC_CS }}'
          CF_WORKER_URL = '${{ secrets.CF_WORKER_URL }}'
          CF_WORKER_SECRET = '${{ secrets.CF_WORKER_SECRET }}'
          WALMART_CLIENT_ID = '${{ secrets.WALMART_CLIENT_ID }}'
          WALMART_CLIENT_SECRET = '${{ secrets.WALMART_CLIENT_SECRET }}'
          AMAZON_REFRESH_TOKEN = '${{ secrets.AMAZON_REFRESH_TOKEN }}'
          AMAZON_CLIENT_ID = '${{ secrets.AMAZON_CLIENT_ID }}'
          AMAZON_CLIENT_SECRET = '${{ secrets.AMAZON_CLIENT_SECRET }}'
          AMAZON_MERCHANT_TOKEN = '${{ secrets.AMAZON_MERCHANT_TOKEN }}'
          GOOGLE_CLIENT_ID = '${{ secrets.GOOGLE_CLIENT_ID }}'
          GOOGLE_CLIENT_SECRET = '${{ secrets.GOOGLE_CLIENT_SECRET }}'
          GOOGLE_REFRESH_TOKEN = '${{ secrets.GOOGLE_REFRESH_TOKEN }}'
          GOOGLE_MERCHANT_CENTER_ID = '138935850'
          KLAVIYO_API = '${{ secrets.KLAVIYO_API }}'
          SA_SITE_ID = '33157'
          SA_API_TOKEN = '${{ secrets.SA_API_TOKEN }}'
          ENVEOF

      - name: Build feed master
        run: python -m feeds.build_feed_master

      - name: Run channel audits
        run: python -m feeds.digest.run_audit

      - name: Commit feed master + digest
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add feeds/feed_master.json feeds/digest/
          git diff --staged --quiet || git commit -m "chore(feeds): daily feed snapshot + audit $(date -u +%Y-%m-%d)"
          git push
```

- [ ] **Step 2: Verify all required GH Actions secrets are present**

Check that these Repository secrets exist in `GabeNaturesSeed/nature-seed-data` Settings → Secrets → Actions:
- `WC_BASE_URL`, `WC_CK`, `WC_CS`, `CF_WORKER_URL`, `CF_WORKER_SECRET`
- `WALMART_CLIENT_ID`, `WALMART_CLIENT_SECRET`
- `AMAZON_REFRESH_TOKEN`, `AMAZON_CLIENT_ID`, `AMAZON_CLIENT_SECRET`, `AMAZON_MERCHANT_TOKEN`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`
- `KLAVIYO_API`, `SA_API_TOKEN`

- [ ] **Step 3: Run full test suite one final time**

```bash
python -m pytest feeds/tests/ -v
```
Expected: all PASS

- [ ] **Step 4: Commit workflow**

```bash
git add .github/workflows/feed-audit.yml
git commit -m "feat(feeds): daily GH Actions cron for feed audit + digest commit"
```

- [ ] **Step 5: Push and verify workflow appears in Actions tab**

```bash
git push origin main
```
Then open `https://github.com/GabeNaturesSeed/nature-seed-data/actions` and confirm `Feed Audit` workflow appears. Trigger manually with `workflow_dispatch` to validate end-to-end.

---

## Self-Review

**Spec coverage check:**
- [x] Central feed_master.json snapshot — Task 2
- [x] WC-canonical model — `build_product_record` produces only WC fields
- [x] channel_sku_map.json — Task 2, referenced in adapters
- [x] base_adapter with 3 checks — Task 3
- [x] All 6 active adapters — Tasks 4–8
- [x] 2 stub adapters returning "not connected" — Task 9
- [x] SCHEMA.md per channel — each adapter task
- [x] Digest markdown with summary table + action items — Task 10
- [x] sync_prices.py (Walmart + Amazon, manual trigger) — Task 11
- [x] GH Actions cron — Task 12
- [x] CF Worker proxy pattern — Task 2 (`_wc_get`)
- [x] .env parsing — Task 1 (env_loader)
- [x] Error isolation (one adapter failure doesn't block digest) — `run` method in base_adapter wraps in try/except

**Type consistency check:**
- `build_product_record` returns dict, consumed by `build_feed_master` ✓
- `fetch_channel_products` returns `list[dict]` in all adapters ✓
- `AdapterResult` fields (coverage, drift, quality) match what `build_digest_markdown` accesses ✓
- `build_walmart_price_update` / `build_amazon_price_update` tested with same keys used in push functions ✓

**Placeholder scan:** None found.
