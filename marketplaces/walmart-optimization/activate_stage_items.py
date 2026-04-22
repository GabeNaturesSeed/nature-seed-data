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
    # Wraps the GET /v3/items/{sku} response as-is into an MPItem feed entry.
    # Assumption: MP_ITEM feed accepts the same body shape as MP_MAINTENANCE.
    # If Walmart rejects read-only fields (publishedStatus, etc.), errors will
    # appear in activation_results.json with DATA_ERROR + field-level details.
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
    DATA_DIR.mkdir(exist_ok=True)
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
    try:
        for i, row in enumerate(to_activate, 1):
            sku = row["sku"]
            print(f"\n  [{i}/{len(to_activate)}] {sku}")

            try:
                item_detail = get_item(sku)
            except Exception as exc:
                print(f"    WARNING: get_item failed: {exc}")
                results.append({
                    "sku": sku, "feed_id": None, "status": "ERROR",
                    "ingestion_status": "ERROR", "errors": [str(exc)],
                })
                continue

            if not item_detail:
                print(f"    WARNING: Could not fetch item detail")
                results.append({
                    "sku": sku, "feed_id": None, "status": "SKIPPED",
                    "ingestion_status": "SKIPPED", "errors": ["Could not fetch item detail from Walmart API"],
                })
                continue

            mp_item = build_mp_item_payload(item_detail)
            try:
                feed_id = submit_maintenance_feed([mp_item], feed_type="MP_ITEM")
                print(f"    Polling feed {feed_id}...")
                feed_status = wait_for_feed(feed_id, max_wait=600, poll_interval=30)
            except Exception as exc:
                print(f"    WARNING: feed submission/polling failed: {exc}")
                results.append({
                    "sku": sku, "feed_id": None, "status": "ERROR",
                    "ingestion_status": "ERROR", "errors": [str(exc)],
                })
                continue

            result = parse_feed_item_result(sku, feed_id, feed_status)
            results.append(result)

            if result["errors"]:
                print(f"    Status: {result['ingestion_status']}")
                for err in result["errors"]:
                    print(f"      ERROR: {err}")
            else:
                print(f"    Status: {result['ingestion_status']}")

            if i < len(to_activate):
                time.sleep(2)  # brief rate-limit buffer between submissions
    finally:
        out = DATA_DIR / "activation_results.json"
        with open(out, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n  Results saved: {out}")

    success = sum(1 for r in results if r["ingestion_status"] == "SUCCESS")
    errors = sum(1 for r in results if r["ingestion_status"] not in ("SUCCESS", "SKIPPED", "UNKNOWN"))
    timeouts = sum(1 for r in results if r["ingestion_status"] == "UNKNOWN")

    print(f"\nActivation results: {len(results)} submitted")
    print(f"  SUCCESS: {success}")
    print(f"  ERRORS:  {errors}  → see data/activation_results.json")
    print(f"  TIMEOUT: {timeouts}  (check activation_results.json)")

    return results


if __name__ == "__main__":
    run_activation()
