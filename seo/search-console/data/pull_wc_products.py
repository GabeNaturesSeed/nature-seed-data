#!/usr/bin/env python3
"""Pull full WooCommerce product catalog and save to JSON."""

import json
import time
import requests
from collections import Counter

BASE_URL = "https://naturesseed.com/wp-json/wc/v3"
CK = "ck_9629579f1379f272169de8628edddb00b24737f9"
CS = "cs_bf6dcf206d6ed26b83e55e8af62c16de26339815"
OUTPUT = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/search-console/data/wc_products.json"

def fetch_all_products():
    products = []
    page = 1
    per_page = 100

    while True:
        print(f"Fetching page {page}...")
        resp = requests.get(
            f"{BASE_URL}/products",
            auth=(CK, CS),
            params={"per_page": per_page, "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        products.extend(batch)
        print(f"  Got {len(batch)} products (total so far: {len(products)})")
        if len(batch) < per_page:
            break
        page += 1
        time.sleep(0.3)

    return products


def extract_fields(product):
    return {
        "id": product["id"],
        "name": product["name"],
        "slug": product["slug"],
        "permalink": product["permalink"],
        "status": product["status"],
        "type": product["type"],
        "categories": [c["name"] for c in product.get("categories", [])],
        "tags": [t["name"] for t in product.get("tags", [])],
        "sku": product.get("sku", ""),
        "stock_status": product.get("stock_status", ""),
    }


def main():
    raw = fetch_all_products()
    cleaned = [extract_fields(p) for p in raw]

    with open(OUTPUT, "w") as f:
        json.dump(cleaned, f, indent=2)
    print(f"\nSaved {len(cleaned)} products to {OUTPUT}")

    # Summary
    status_counts = Counter(p["status"] for p in cleaned)
    type_counts = Counter(p["type"] for p in cleaned)
    cat_counts = Counter()
    for p in cleaned:
        for c in p["categories"]:
            cat_counts[c] += 1

    print(f"\n{'='*50}")
    print(f"TOTAL PRODUCTS: {len(cleaned)}")
    print(f"\n--- Status Breakdown ---")
    for s, n in status_counts.most_common():
        print(f"  {s}: {n}")
    print(f"\n--- Type Breakdown ---")
    for t, n in type_counts.most_common():
        print(f"  {t}: {n}")
    print(f"\n--- Category Breakdown (top 20) ---")
    for c, n in cat_counts.most_common(20):
        print(f"  {c}: {n}")


if __name__ == "__main__":
    main()
