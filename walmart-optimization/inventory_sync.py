#!/usr/bin/env python3
"""
Fishbowl → Walmart Inventory Sync.

Cross-references Fishbowl stock with Walmart listings and pushes
accurate inventory quantities to Walmart Marketplace.

Usage:
  python3 inventory_sync.py              # Dry run (default)
  python3 inventory_sync.py --dry-run    # Preview without updating
  python3 inventory_sync.py --push       # Actually push to Walmart
"""

import json
import csv
import sys
import os
from datetime import datetime
from pathlib import Path

from fishbowl_client import get_all_inventory
from sku_matching import match_sku
from walmart_client import get_all_items, submit_inventory_feed, wait_for_feed

DATA_DIR = Path(__file__).parent / "data"


def load_walmart_items():
    """Load cached Walmart items or pull fresh."""
    cache = DATA_DIR / "walmart_items.json"
    if cache.exists():
        with open(cache) as f:
            items = json.load(f)
        print(f"  Loaded {len(items)} Walmart items from cache")
        return items

    print("  Pulling fresh Walmart items...")
    items = get_all_items()
    with open(cache, "w") as f:
        json.dump(items, f, indent=2)
    return items


def run_sync(push=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode = "PUSH" if push else "DRY RUN"

    print(f"[{mode}] Fishbowl → Walmart Inventory Sync")
    print(f"Started: {timestamp}")
    print("=" * 60)

    # Step 1: Pull Fishbowl inventory
    print("\n[1/3] Pulling Fishbowl inventory...")
    fb_inventory = get_all_inventory()
    in_stock_count = sum(1 for q in fb_inventory.values() if q > 0)
    print(f"  {len(fb_inventory)} total parts, {in_stock_count} in stock")

    # Step 2: Pull Walmart items
    print("\n[2/3] Loading Walmart items...")
    wm_items = load_walmart_items()
    wm_skus = [it["sku"] for it in wm_items]
    print(f"  {len(wm_skus)} Walmart SKUs")

    # Deduplicate Walmart items by SKU (API returns dupes per variant group)
    seen_skus = set()
    unique_items = []
    for item in wm_items:
        if item["sku"] not in seen_skus:
            seen_skus.add(item["sku"])
            unique_items.append(item)
    print(f"  {len(wm_items)} total items, {len(unique_items)} unique SKUs")
    wm_items = unique_items

    # Step 3: Cross-reference
    print("\n[3/3] Cross-referencing...")
    results = []
    in_stock = []
    out_of_stock = []
    no_match = []

    for item in wm_items:
        sku = item["sku"]
        name = item.get("productName", "")
        current_avail = item.get("availability", "")
        published = item.get("publishedStatus", "")

        qty, match_type, matched_sku = match_sku(sku, fb_inventory)

        row = {
            "sku": sku,
            "product_name": name,
            "published_status": published,
            "current_availability": current_avail,
            "fishbowl_qty": qty,
            "match_type": match_type,
            "matched_sku": matched_sku or "",
            "new_qty": qty,
        }
        results.append(row)

        if match_type == "no_match":
            row["new_qty"] = 0
            no_match.append(row)
        elif qty > 0:
            in_stock.append(row)
        else:
            out_of_stock.append(row)

    print(f"\n  Match results:")
    print(f"    In stock:     {len(in_stock)} items")
    print(f"    Out of stock: {len(out_of_stock)} items (matched but qty=0)")
    print(f"    No match:     {len(no_match)} items (will set qty=0)")

    # Match type breakdown
    match_types = {}
    for r in results:
        t = r["match_type"]
        match_types[t] = match_types.get(t, 0) + 1
    print(f"\n  Match type breakdown:")
    for t, c in sorted(match_types.items()):
        print(f"    {t:15s}: {c}")

    # Availability changes
    becoming_oos = [r for r in results if r["current_availability"] == "In_stock" and r["new_qty"] == 0]
    becoming_is = [r for r in results if r["current_availability"] != "In_stock" and r["new_qty"] > 0]
    print(f"\n  Availability changes:")
    print(f"    In_stock → out of stock: {len(becoming_oos)} items")
    print(f"    Out of stock → in stock: {len(becoming_is)} items")

    # Save report
    report_path = DATA_DIR / "inventory_sync_report.csv"
    with open(report_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda x: x["sku"]))
    print(f"\n  Report saved: {report_path}")

    if not push:
        print(f"\n{'='*60}")
        print("[DRY RUN] No changes pushed to Walmart.")

        if becoming_oos:
            print(f"\n  Items that WOULD become out of stock ({len(becoming_oos)}):")
            for r in sorted(becoming_oos, key=lambda x: x["sku"]):
                print(f"    {r['sku']:35s} {r['product_name'][:45]}")

        if becoming_is:
            print(f"\n  Items that WOULD become in stock ({len(becoming_is)}):")
            for r in sorted(becoming_is, key=lambda x: x["sku"]):
                print(f"    {r['sku']:35s} qty={r['new_qty']}")

        print("\n  Run with --push to apply changes.")
        return results

    # Push to Walmart
    print(f"\n{'='*60}")
    print("[PUSH] Submitting inventory feed to Walmart...")

    inventory_items = []
    for r in results:
        inventory_items.append({
            "sku": r["sku"],
            "quantity": {
                "unit": "EACH",
                "amount": r["new_qty"],
            },
        })

    feed_id = submit_inventory_feed(inventory_items)
    print(f"\n  Feed ID: {feed_id}")
    print("  Polling for completion...")

    status = wait_for_feed(feed_id, max_wait=300, poll_interval=20)
    feed_status = status.get("feedStatus", "UNKNOWN")
    print(f"\n  Feed status: {feed_status}")

    if "itemsReceived" in status:
        print(f"  Items received: {status['itemsReceived']}")
    if "itemsSucceeded" in status:
        print(f"  Items succeeded: {status['itemsSucceeded']}")
    if "itemsFailed" in status:
        print(f"  Items failed: {status['itemsFailed']}")

    # Save feed response
    feed_result_path = DATA_DIR / "inventory_feed_result.json"
    with open(feed_result_path, "w") as f:
        json.dump(status, f, indent=2)
    print(f"\n  Feed result saved: {feed_result_path}")

    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return results


if __name__ == "__main__":
    push = "--push" in sys.argv
    run_sync(push=push)
