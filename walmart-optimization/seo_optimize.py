#!/usr/bin/env python3
"""
Walmart SEO Optimization Pipeline for Nature's Seed.

Audits current listings, generates optimized content, and pushes
updates via MP_MAINTENANCE feed.

Usage:
  python3 seo_optimize.py --audit         # Audit current listings
  python3 seo_optimize.py --dry-run       # Generate + preview (default)
  python3 seo_optimize.py --push          # Generate + push to Walmart
"""

import json
import csv
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from walmart_client import (
    get_all_items,
    submit_maintenance_feed,
    get_feed_status,
    wait_for_feed,
)
from seo_content_generator import (
    load_wc_products,
    generate_all,
    get_base_sku,
    get_product_type,
    get_usda_zones,
    get_weight_from_sku,
    clean_product_name,
)

DATA_DIR = Path(__file__).parent / "data"


def load_walmart_items():
    """Load cached or fresh Walmart items, deduplicated."""
    cache = DATA_DIR / "walmart_items.json"
    if cache.exists():
        with open(cache) as f:
            items = json.load(f)
    else:
        items = get_all_items()
        with open(cache, "w") as f:
            json.dump(items, f, indent=2)

    # Deduplicate
    seen = set()
    unique = []
    for it in items:
        if it["sku"] not in seen:
            seen.add(it["sku"])
            unique.append(it)

    print(f"  {len(items)} total items, {len(unique)} unique SKUs")
    return unique


# ============================================================
# AUDIT MODE
# ============================================================

def run_audit():
    """Audit current Walmart listings for SEO completeness."""
    print("=" * 60)
    print("WALMART SEO AUDIT")
    print("=" * 60)

    print("\nLoading Walmart items...")
    items = load_walmart_items()

    print("\nLoading WC products...")
    wc_index = load_wc_products()

    # Audit metrics
    status_counts = {}
    type_counts = {}
    short_titles = []
    no_wc_match = []

    for item in items:
        sku = item["sku"]
        status = item.get("publishedStatus", "UNKNOWN")
        ptype = item.get("productType", "Unknown")
        name = item.get("productName", "")

        status_counts[status] = status_counts.get(status, 0) + 1
        type_counts[ptype] = type_counts.get(ptype, 0) + 1

        if len(name) < 40:
            short_titles.append({"sku": sku, "title": name, "length": len(name)})

        # Check WC match
        base = get_base_sku(sku)
        if base not in wc_index and sku.upper() not in wc_index:
            no_wc_match.append(sku)

    print(f"\n  Published status:")
    for s, c in sorted(status_counts.items()):
        print(f"    {s:20s}: {c}")

    print(f"\n  Product types:")
    for t, c in sorted(type_counts.items()):
        print(f"    {t:20s}: {c}")

    print(f"\n  Titles < 40 chars: {len(short_titles)}")
    for t in short_titles[:5]:
        print(f"    {t['sku']:35s} ({t['length']} chars) {t['title']}")

    print(f"\n  No WC match (will use fallback content): {len(no_wc_match)}")
    for sku in sorted(no_wc_match):
        print(f"    {sku}")

    # SEO fields that GET /items doesn't return
    print(f"\n  NOTE: GET /items does not return description, keyFeatures, or attributes.")
    print(f"  All {len(items)} items will receive new SEO content regardless.")

    # Generate preview of what we'll push
    print("\n\nGenerating optimized content preview...")
    results = generate_all(items, wc_index)

    wc_matched = sum(1 for r in results if r["wc_matched"])
    title_lens = [len(r["title"]) for r in results]

    print(f"\n  Content generation results:")
    print(f"    WC matched: {wc_matched}/{len(results)}")
    print(f"    Title lengths: min={min(title_lens)}, max={max(title_lens)}, avg={sum(title_lens)/len(title_lens):.0f}")

    # Save audit report
    audit_path = DATA_DIR / "seo_audit.json"
    with open(audit_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_items": len(items),
            "unique_skus": len(items),
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "short_titles": len(short_titles),
            "no_wc_match": no_wc_match,
            "wc_matched": wc_matched,
        }, f, indent=2)
    print(f"\n  Audit saved: {audit_path}")


# ============================================================
# BUILD FEED PAYLOAD
# ============================================================

def _parse_net_content(weight_str):
    """Parse weight string like '25 lb' into Walmart netContent object."""
    if not weight_str:
        return {"productNetContentMeasure": 1, "productNetContentUnit": "Pound"}

    m = re.match(r"([\d.]+)\s*(\w+)", weight_str)
    if not m:
        return {"productNetContentMeasure": 1, "productNetContentUnit": "Pound"}

    measure = float(m.group(1))
    unit_str = m.group(2).lower()
    unit_map = {
        "lb": "Pound", "lbs": "Pound", "pound": "Pound",
        "oz": "Ounce", "ounce": "Ounce",
        "kg": "Kilogram", "g": "Gram",
    }
    unit = unit_map.get(unit_str, "Pound")
    return {"productNetContentMeasure": measure, "productNetContentUnit": unit}


def _encode_html(html_str):
    """Encode HTML tags for Walmart (they require character-encoded HTML)."""
    # Walmart requires HTML to be character-encoded
    return html_str


def _normalize_light_needs(value):
    """Map light needs to valid Walmart enum values."""
    valid = ["Full Sun", "Filtered Sun", "Full Shade", "Partial Shade",
             "Partial Sun", "Indirect Sunlight", "Shade"]
    if value in valid:
        return value
    v = value.lower()
    if "full sun" in v and ("shade" in v or "partial" in v):
        return "Partial Sun"
    if "full sun" in v:
        return "Full Sun"
    if "partial shade" in v or "part shade" in v:
        return "Partial Shade"
    if "partial sun" in v or "part sun" in v:
        return "Partial Sun"
    if "shade" in v:
        return "Shade"
    return "Full Sun"


def build_mp_item(seo_result, wm_item=None):
    """
    Build a single MPItem dict for the MP_MAINTENANCE feed.
    Follows Walmart v5 spec format matching EcommEngineGGS feed-formatters.ts.
    """
    sku = seo_result["sku"]
    attrs = seo_result["attributes"]

    # Use item's actual productType as the Visible section key (not hardcoded)
    section_key = "Grass Seeds"
    if wm_item:
        pt = wm_item.get("productType", "Grass Seeds")
        if pt and pt != "default":
            section_key = pt

    # Build visible section matching v5 format
    product_section = {
        "productName": seo_result["title"],
        "brand": attrs.get("brand", "Nature's Seed"),
        "shortDescription": seo_result["description"],
        "keyFeatures": seo_result["key_features"],
        "isProp65WarningRequired": attrs.get("isProp65WarningRequired", "No"),
        "condition": attrs.get("condition", "New"),
    }

    # Only include seed-specific attributes for seed product types
    if section_key in ("Grass Seeds", "Plant Seeds"):
        product_section["light_needs"] = _normalize_light_needs(
            attrs.get("light_needs", "Full Sun")
        )
        # plantCategory as array
        plant_cat = attrs.get("plantCategory", "Grasses")
        product_section["plantCategory"] = [plant_cat]
        # plant_name as array
        plant_name = attrs.get("plantName", seo_result["title"])
        product_section["plant_name"] = [plant_name]

    # netContent as object (required format)
    net_content_str = attrs.get("netContent", "")
    if net_content_str:
        product_section["netContent"] = _parse_net_content(net_content_str)

    # Build Orderable
    orderable = {"sku": sku}

    if wm_item:
        # productIdentifiers required
        gtin = wm_item.get("gtin", "")
        upc = wm_item.get("upc", "")
        if gtin:
            orderable["productIdentifiers"] = {
                "productIdType": "GTIN",
                "productId": gtin,
            }
        elif upc:
            orderable["productIdentifiers"] = {
                "productIdType": "UPC",
                "productId": upc,
            }

        # Price is REQUIRED in maintenance feed
        price_data = wm_item.get("price", {})
        price_amount = price_data.get("amount")
        if price_amount:
            orderable["price"] = price_amount

    mp_item = {
        "Orderable": orderable,
        "Visible": {
            section_key: product_section,
        },
    }

    return mp_item


# ============================================================
# DRY RUN MODE
# ============================================================

def run_dry_run():
    """Generate optimized content and preview without pushing."""
    print("=" * 60)
    print("[DRY RUN] WALMART SEO OPTIMIZATION")
    print("=" * 60)

    print("\nLoading Walmart items...")
    items = load_walmart_items()

    print("\nLoading WC products...")
    wc_index = load_wc_products()

    print("\nGenerating optimized content...")
    results = generate_all(items, wc_index)

    # Index walmart items by SKU for UPC/GTIN lookup
    wm_by_sku = {it["sku"]: it for it in items}

    # Save full output
    output_path = DATA_DIR / "seo_optimized.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Saved to: {output_path}")

    # Build feed items for validation
    mp_items = [build_mp_item(r, wm_by_sku.get(r["sku"])) for r in results]
    feed_path = DATA_DIR / "seo_feed_preview.json"
    with open(feed_path, "w") as f:
        json.dump(mp_items[:3], f, indent=2)
    print(f"  Sample feed payload (3 items): {feed_path}")

    # Stats
    wc_matched = sum(1 for r in results if r["wc_matched"])
    title_lens = [len(r["title"]) for r in results]

    print(f"\n  Summary:")
    print(f"    Total items: {len(results)}")
    print(f"    WC matched: {wc_matched}")
    print(f"    Title lengths: min={min(title_lens)}, max={max(title_lens)}, avg={sum(title_lens)/len(title_lens):.0f}")

    # Show 3 sample transformations
    for i, r in enumerate(results[:3]):
        print(f"\n  {'='*50}")
        print(f"  Sample {i+1}: {r['sku']}")
        print(f"    Before: {r['current_name']}")
        print(f"    After:  {r['title']} ({len(r['title'])} chars)")
        print(f"    WC:     {'matched' if r['wc_matched'] else 'no match'}")
        print(f"    Features: {len(r['key_features'])} bullets")
        for j, kf in enumerate(r["key_features"][:3]):
            print(f"      [{j+1}] {kf[:100]}...")
        print(f"    Attributes: {', '.join(f'{k}={v}' for k, v in list(r['attributes'].items())[:5])}")
        desc_preview = r["description"][:150].replace("\n", " ")
        print(f"    Description: {desc_preview}...")

    print(f"\n  {'='*50}")
    print(f"\n  [DRY RUN] No changes pushed. Run with --push to apply.")
    print(f"  Feed would send {len(results)} items in {(len(results) + 49) // 50} batches.")

    return results


# ============================================================
# PUSH MODE
# ============================================================

def run_push():
    """Generate and push optimized content to Walmart."""
    print("=" * 60)
    print("[PUSH] WALMART SEO OPTIMIZATION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print("\nLoading Walmart items...")
    items = load_walmart_items()

    print("\nLoading WC products...")
    wc_index = load_wc_products()

    print("\nGenerating optimized content...")
    results = generate_all(items, wc_index)

    # Index walmart items by SKU for UPC/GTIN lookup
    wm_by_sku = {it["sku"]: it for it in items}

    # Save before pushing
    output_path = DATA_DIR / "seo_optimized.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Build feed items
    mp_items = [build_mp_item(r, wm_by_sku.get(r["sku"])) for r in results]

    # Submit in batches of 50 with 65s delay
    batch_size = 50
    delay = 65
    total = len(mp_items)
    total_batches = (total + batch_size - 1) // batch_size
    feed_ids = []
    all_statuses = []

    print(f"\nSubmitting {total} items in {total_batches} batches...")

    # Phase 1: Submit all batches with required delay + 429 retry
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total)
        batch = mp_items[start_idx:end_idx]

        print(f"\n  Batch {batch_num + 1}/{total_batches} ({len(batch)} items, SKUs {start_idx+1}-{end_idx})")

        # Retry on 429 with exponential backoff
        for retry in range(5):
            try:
                feed_id = submit_maintenance_feed(batch)
                feed_ids.append(feed_id)
                break
            except Exception as e:
                if "429" in str(e):
                    wait = 120 * (retry + 1)
                    print(f"  Rate limited (429). Waiting {wait}s before retry {retry+2}/5...")
                    time.sleep(wait)
                else:
                    raise
        else:
            print(f"  FAILED batch {batch_num+1} after 5 retries")
            feed_ids.append(f"FAILED_BATCH_{batch_num+1}")

        # Delay between batches (except last)
        if batch_num + 1 < total_batches:
            print(f"  Waiting {delay}s before next batch...")
            time.sleep(delay)

    # Phase 2: Poll all feeds for completion
    print(f"\n  All {total_batches} batches submitted. Polling for completion...")
    print(f"  Feed IDs: {feed_ids}")

    for attempt in range(30):  # up to 15 minutes
        time.sleep(30)
        all_done = True
        for i, fid in enumerate(feed_ids):
            status = get_feed_status(fid, include_details=True)
            feed_status = status.get("feedStatus", "UNKNOWN")
            if feed_status == "INPROGRESS":
                all_done = False
            elif fid not in [s["feed_id"] for s in all_statuses]:
                items_succeeded = status.get("itemsSucceeded", 0)
                items_failed = status.get("itemsFailed", 0)
                all_statuses.append({
                    "batch": i + 1,
                    "feed_id": fid,
                    "status": feed_status,
                    "items_received": status.get("itemsReceived", 0),
                    "items_succeeded": items_succeeded,
                    "items_failed": items_failed,
                })
                print(f"  Batch {i+1}: {feed_status} — {items_succeeded} succeeded, {items_failed} failed")

                # Log failed items
                if items_failed > 0:
                    details = status.get("itemDetails", {}).get("itemIngestionStatus", [])
                    for d in details:
                        if d.get("ingestionStatus") != "SUCCESS":
                            err_sku = d.get("sku", "?")
                            errors = d.get("ingestionErrors", {}).get("ingestionError", [])
                            err_msgs = [e.get("description", "") for e in errors]
                            print(f"    FAILED: {err_sku} — {'; '.join(err_msgs[:2])}")

        completed = len(all_statuses)
        elapsed = (attempt + 1) * 30
        print(f"  Poll {attempt+1}: {completed}/{total_batches} complete ({elapsed}s elapsed)")

        if all_done or completed >= total_batches:
            break

    # Final summary
    total_succeeded = sum(s["items_succeeded"] for s in all_statuses)
    total_failed = sum(s["items_failed"] for s in all_statuses)

    print(f"\n{'='*60}")
    print(f"SEO OPTIMIZATION COMPLETE")
    print(f"  Total items: {total}")
    print(f"  Succeeded: {total_succeeded}")
    print(f"  Failed: {total_failed}")
    print(f"  Feed IDs: {len(feed_ids)}")

    # Save results
    result_path = DATA_DIR / "seo_push_result.json"
    with open(result_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_items": total,
            "total_succeeded": total_succeeded,
            "total_failed": total_failed,
            "batches": all_statuses,
            "feed_ids": feed_ids,
        }, f, indent=2)
    print(f"  Results saved: {result_path}")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    if "--audit" in sys.argv:
        run_audit()
    elif "--push" in sys.argv:
        run_push()
    else:
        run_dry_run()
