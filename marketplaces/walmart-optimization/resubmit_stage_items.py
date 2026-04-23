#!/usr/bin/env python3
"""
Re-submits all Walmart STAGE items with correct MP_ITEM feed format.
Builds Orderable + Visible sections from seo_optimized.json content
and walmart_items.json pricing/identifiers.

Usage:
  python3 resubmit_stage_items.py
"""

import json
from datetime import datetime
from pathlib import Path

from sku_matching import get_base_sku
from seo_optimize import _parse_net_content, _normalize_light_needs

try:
    from walmart_client import submit_maintenance_feed, wait_for_feed
except Exception:
    submit_maintenance_feed = None
    wait_for_feed = None

DATA_DIR = Path(__file__).parent / "data"


# ============================================================
# PURE FUNCTIONS
# ============================================================

def find_seo_content(sku, seo_items):
    """
    Match a STAGE SKU to seo_optimized content via base-SKU lookup.
    Returns the matching seo item dict, or None if no match.
    """
    lookup = {get_base_sku(item["sku"]): item for item in seo_items}
    return lookup.get(get_base_sku(sku))



def build_product_identifiers(wm_item):
    """
    Return productIdentifiers dict (for inside Orderable), or None if no UPC/GTIN.
    Prefers GTIN over UPC.
    """
    gtin = wm_item.get("gtin", "")
    upc = wm_item.get("upc", "")
    if gtin:
        return {"productIdType": "GTIN", "productId": gtin}
    if upc:
        return {"productIdType": "UPC", "productId": upc}
    return None


def build_orderable(sku, wm_item):
    """
    Build the Orderable section from a walmart_items.json entry.
    Returns dict with sku, productIdentifiers, startDate, endDate, fulfillmentLagTime, and price.
    """
    orderable = {"sku": sku}
    identifiers = build_product_identifiers(wm_item)
    if identifiers:
        orderable["productIdentifiers"] = identifiers
    price_amount = wm_item.get("price", {}).get("amount")
    if price_amount:
        orderable["price"] = price_amount
    return orderable


def build_visible(seo_item, product_type):
    """
    Build the Visible section.
    seo_item: dict from seo_optimized.json, or None for fallback.
    product_type: Walmart productType string (e.g. "Grass Seeds").
    Returns {"<product_type>": {...}}.
    """
    if seo_item is None:
        return {
            product_type: {
                "brand": "Nature's Seed",
                "isProp65WarningRequired": "No",
                "condition": "New",
            }
        }

    attrs = seo_item.get("attributes", {})
    section = {
        "productName": seo_item.get("title", ""),
        "brand": attrs.get("brand", "Nature's Seed"),
        "shortDescription": seo_item.get("description", ""),
        "keyFeatures": seo_item.get("key_features", []),
        "isProp65WarningRequired": attrs.get("isProp65WarningRequired", "No"),
        "condition": attrs.get("condition", "New"),
    }

    if product_type in ("Grass Seeds", "Plant Seeds"):
        light = attrs.get("light_needs", "")
        if light:
            section["light_needs"] = _normalize_light_needs(light)

        plant_cat = attrs.get("plantCategory", "")
        if plant_cat:
            section["plantCategory"] = [plant_cat]

        plant_name_val = attrs.get("plantName", "")
        if plant_name_val:
            section["plant_name"] = [plant_name_val]

        net_content = attrs.get("netContent", "")
        if net_content:
            section["netContent"] = _parse_net_content(net_content)

    return {product_type: section}


# ============================================================
# ORCHESTRATOR
# ============================================================

def run_resubmit():
    print("Walmart STAGE Item Re-submission")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    DATA_DIR.mkdir(exist_ok=True)

    if submit_maintenance_feed is None or wait_for_feed is None:
        print("ERROR: walmart_client not available. Check that WALMART_CLIENT_ID and WALMART_CLIENT_SECRET env vars are set.")
        return

    audit_path = DATA_DIR / "stage_audit.json"
    if not audit_path.exists():
        print("ERROR: data/stage_audit.json not found. Run stage_audit.py first.")
        return

    stage_items = json.loads(audit_path.read_text())
    print(f"  {len(stage_items)} STAGE items from audit")

    wm_by_sku = {
        item["sku"]: item
        for item in json.loads((DATA_DIR / "walmart_items.json").read_text())
    }
    print(f"  {len(wm_by_sku)} Walmart items loaded")

    seo_items = json.loads((DATA_DIR / "seo_optimized.json").read_text())
    print(f"  {len(seo_items)} SEO items loaded")

    # Build payloads
    print("\n  Building payloads...")
    mp_items = []
    skipped = []

    for i, row in enumerate(stage_items, 1):
        sku = row["sku"]
        wm_item = wm_by_sku.get(sku)
        if not wm_item:
            print(f"    WARNING: {sku} not in walmart_items.json — skipping")
            skipped.append(sku)
            continue

        seo_content = find_seo_content(sku, seo_items)
        product_type = wm_item.get("productType", "Grass Seeds")

        item = {
            "Orderable": build_orderable(sku, wm_item),
            "Visible": build_visible(seo_content, product_type),
        }

        mp_items.append(item)
        match_label = "seo" if seo_content else "fallback"
        print(f"    [{len(mp_items)}/{len(stage_items)}] {sku} ({match_label})")

    print(f"\n  Built {len(mp_items)} payloads, {len(skipped)} skipped")

    if not mp_items:
        print("  Nothing to submit.")
        return

    # Submit feed
    print(f"\n  Submitting MP_MAINTENANCE feed ({len(mp_items)} items)...")
    feed_id = submit_maintenance_feed(mp_items, feed_type="MP_MAINTENANCE")
    print(f"  Polling feed {feed_id}...")
    feed_status = wait_for_feed(feed_id, max_wait=600, poll_interval=30)

    overall = feed_status.get("feedStatus", "UNKNOWN")
    item_results = []
    for detail in feed_status.get("itemDetails", {}).get("itemIngestionStatus", []):
        errors = [
            err.get("description", str(err))
            for err in (detail.get("ingestionErrors") or {}).get("ingestionError", [])
        ]
        item_results.append({
            "sku": detail.get("sku", ""),
            "ingestion_status": detail.get("ingestionStatus", "UNKNOWN"),
            "errors": errors,
        })

    success = sum(1 for r in item_results if r["ingestion_status"] == "SUCCESS")
    errors_count = sum(1 for r in item_results if r["ingestion_status"] not in ("SUCCESS", "UNKNOWN"))

    print(f"\nFeed status: {overall}")
    print(f"  Submitted: {len(mp_items)}")
    print(f"  SUCCESS:   {success}")
    print(f"  ERRORS:    {errors_count}  → see data/resubmit_results.json")

    result_path = DATA_DIR / "resubmit_results.json"
    result_path.write_text(json.dumps({
        "feed_id": feed_id,
        "feed_status": overall,
        "submitted": len(mp_items),
        "skipped": skipped,
        "items": item_results,
    }, indent=2))
    print(f"  Results saved: {result_path}")


if __name__ == "__main__":
    run_resubmit()
