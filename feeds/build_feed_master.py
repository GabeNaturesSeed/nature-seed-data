#!/usr/bin/env python3
"""
Nature's Seed — Feed Master Builder
Pulls full WC product catalog (products + variations) and writes feeds/feed_master.json.
Runs daily via GitHub Actions. Uses CF Worker proxy when CF_WORKER_URL is set.

Usage:
    python3 -m feeds.build_feed_master
"""

import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from feeds.env_loader import load_env

WC_HEADERS = {"User-Agent": "NaturesSeed-FeedMaster/1.0"}

OUT_PATH = Path(__file__).parent / "feed_master.json"


def _get_env():
    """Load env lazily so module import works without a .env file (e.g. in tests)."""
    env = load_env()
    wc_base = env.get("WC_BASE_URL", "https://naturesseed.com/wp-json/wc/v3")
    wc_ck = env["WC_CK"]
    wc_cs = env["WC_CS"]
    cf_worker_url = env.get("CF_WORKER_URL", "")
    cf_worker_secret = env.get("CF_WORKER_SECRET", "")
    return wc_base, wc_ck, wc_cs, cf_worker_url, cf_worker_secret


def _wc_get(endpoint, params=None, max_retries=3):
    """GET from WC REST API. Routes through CF Worker when CF_WORKER_URL is set."""
    params = params or {}
    wc_base, wc_ck, wc_cs, cf_worker_url, cf_worker_secret = _get_env()
    url = f"{wc_base}{endpoint}"
    for attempt in range(max_retries):
        if cf_worker_url and cf_worker_secret:
            proxy_params = dict(params)
            proxy_params["wc_path"] = endpoint
            auth_str = base64.b64encode(f"{wc_ck}:{wc_cs}".encode()).decode()
            headers = {
                "X-Proxy-Secret": cf_worker_secret,
                "Authorization": f"Basic {auth_str}",
                **WC_HEADERS,
            }
            resp = requests.get(cf_worker_url, params=proxy_params, headers=headers, timeout=60)
        else:
            resp = requests.get(url, auth=(wc_ck, wc_cs), params=params, headers=WC_HEADERS, timeout=60)

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
