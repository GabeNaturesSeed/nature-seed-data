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
