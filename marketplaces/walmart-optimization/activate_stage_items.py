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
