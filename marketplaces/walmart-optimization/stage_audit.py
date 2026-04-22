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
