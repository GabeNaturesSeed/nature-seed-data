#!/usr/bin/env python3
"""
Push ACF content to WooCommerce Planting Aid products.

Reads content JSON files from content/ directory and pushes meta_data
updates to WooCommerce via REST API. After pushing, optionally triggers
Algolia enrichment.

Usage:
  python3 push_acf_content.py --dry-run          # Show what would change
  python3 push_acf_content.py --push             # Apply updates
  python3 push_acf_content.py --push --product 445123   # Single product
  python3 push_acf_content.py --push --verify    # Push + verify
"""

import json
import os
import sys
import argparse
import time
import glob
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    os.system("pip3 install requests")
    import requests

# ─── Config ───────────────────────────────────────────────────────────
WC_BASE = "https://naturesseed.com/wp-json/wc/v3"
WC_AUTH = (
    "ck_9629579f1379f272169de8628edddb00b24737f9",
    "cs_bf6dcf206d6ed26b83e55e8af62c16de26339815",
)

CONTENT_DIR = Path(__file__).resolve().parent / "content"
ALGOLIA_ENRICH = Path(__file__).resolve().parent.parent / "algolia-optimization" / "enrich_records.py"

# Fields that should NOT be overwritten if already populated
# (set --force to override)
SKIP_IF_FILLED = True


def load_content_files(product_id=None):
    """Load content JSON files from content/ directory."""
    files = sorted(CONTENT_DIR.glob("*.json"))
    contents = []
    for f in files:
        with open(f) as fh:
            data = json.load(fh)
        if product_id and data.get("product_id") != product_id:
            continue
        contents.append(data)
    return contents


def get_existing_meta(product_id):
    """GET current product meta_data from WooCommerce."""
    r = requests.get(
        f"{WC_BASE}/products/{product_id}",
        auth=WC_AUTH,
        params={"_fields": "id,name,meta_data"},
    )
    r.raise_for_status()
    product = r.json()
    # Build dict of key -> value
    meta = {}
    for m in product.get("meta_data", []):
        meta[m["key"]] = m["value"]
    return meta, product.get("name", "")


def build_update_payload(content_data, existing_meta, force=False):
    """Build the meta_data array for WC API PUT."""
    meta_updates = []
    skipped = []
    new_fields = []

    for key, value in content_data.get("meta_data", {}).items():
        existing_val = existing_meta.get(key, "")
        has_value = existing_val and str(existing_val).strip() and str(existing_val).strip() not in ("", "0")

        if has_value and not force:
            skipped.append(key)
            continue

        meta_updates.append({"key": key, "value": value})
        new_fields.append(key)

    return meta_updates, new_fields, skipped


def push_product(product_id, meta_updates):
    """Push meta_data updates to WooCommerce."""
    r = requests.put(
        f"{WC_BASE}/products/{product_id}",
        auth=WC_AUTH,
        json={"meta_data": meta_updates},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def verify_product(product_id, expected_meta):
    """Verify pushed fields match expected values."""
    meta, name = get_existing_meta(product_id)
    mismatches = []
    verified = 0

    for key, expected_value in expected_meta.items():
        actual = meta.get(key, "")
        if str(actual).strip() == str(expected_value).strip():
            verified += 1
        else:
            mismatches.append({
                "key": key,
                "expected": str(expected_value)[:80],
                "actual": str(actual)[:80],
            })

    return verified, mismatches


def dry_run(product_id=None, force=False):
    """Preview what would be updated."""
    print("=" * 60)
    print("[DRY RUN] Planting Aid ACF Content Push")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    contents = load_content_files(product_id)
    if not contents:
        print("\n  No content files found!")
        return

    total_updates = 0
    total_skipped = 0

    for content in contents:
        pid = content["product_id"]
        print(f"\n  {'─' * 56}")
        print(f"  {content['product_name']} (ID: {pid}, SKU: {content['product_sku']})")

        existing_meta, _ = get_existing_meta(pid)
        meta_updates, new_fields, skipped = build_update_payload(content, existing_meta, force)

        print(f"  Fields to update: {len(new_fields)}")
        print(f"  Fields skipped (already filled): {len(skipped)}")

        if new_fields:
            print(f"\n  Updates:")
            for key in sorted(new_fields):
                val = content["meta_data"][key]
                preview = str(val)[:60].replace("\n", " ")
                print(f"    + {key}: {preview}...")

        if skipped:
            print(f"\n  Skipped (use --force to override):")
            for key in sorted(skipped):
                print(f"    ~ {key}")

        total_updates += len(new_fields)
        total_skipped += len(skipped)

        time.sleep(0.3)

    print(f"\n{'=' * 60}")
    print(f"  Total: {total_updates} fields to update, {total_skipped} skipped")
    print(f"  Products: {len(contents)}")
    print("=" * 60)


def push(product_id=None, force=False, verify=False):
    """Push content updates to WooCommerce."""
    print("=" * 60)
    print("[PUSH] Planting Aid ACF Content")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    contents = load_content_files(product_id)
    if not contents:
        print("\n  No content files found!")
        return

    results = []

    for content in contents:
        pid = content["product_id"]
        name = content["product_name"]
        sku = content["product_sku"]

        print(f"\n  {'─' * 56}")
        print(f"  {name} (ID: {pid}, SKU: {sku})")

        # Get existing meta
        existing_meta, _ = get_existing_meta(pid)
        meta_updates, new_fields, skipped = build_update_payload(content, existing_meta, force)

        if not meta_updates:
            print(f"  ⏭  No updates needed (all fields filled)")
            results.append({"id": pid, "name": name, "updated": 0, "skipped": len(skipped)})
            continue

        print(f"  Pushing {len(meta_updates)} field updates...")

        try:
            push_product(pid, meta_updates)
            print(f"  ✓  Pushed {len(meta_updates)} fields")
            results.append({"id": pid, "name": name, "updated": len(new_fields), "skipped": len(skipped)})
        except Exception as e:
            print(f"  ✗  ERROR: {e}")
            results.append({"id": pid, "name": name, "updated": 0, "error": str(e)})

        if verify:
            print(f"  Verifying...")
            time.sleep(1)
            verified, mismatches = verify_product(pid, content["meta_data"])
            if mismatches:
                print(f"  ⚠  {len(mismatches)} mismatches:")
                for m in mismatches[:5]:
                    print(f"    {m['key']}: expected '{m['expected']}' got '{m['actual']}'")
            else:
                print(f"  ✓  All {verified} fields verified")

        time.sleep(0.5)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  SUMMARY")
    print(f"  {'─' * 56}")
    total_updated = sum(r.get("updated", 0) for r in results)
    total_skipped = sum(r.get("skipped", 0) for r in results)
    for r in results:
        status = f"{r.get('updated', 0)} updated, {r.get('skipped', 0)} skipped"
        if r.get("error"):
            status = f"ERROR: {r['error']}"
        print(f"  {r['name']}: {status}")
    print(f"\n  Total: {total_updated} fields updated, {total_skipped} skipped")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Trigger Algolia enrichment
    if total_updated > 0 and ALGOLIA_ENRICH.exists():
        print(f"\n  Triggering Algolia enrichment...")
        os.system(f"python3 {ALGOLIA_ENRICH} --push")


def main():
    parser = argparse.ArgumentParser(description="Push ACF content to WooCommerce")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Preview changes")
    group.add_argument("--push", action="store_true", help="Apply changes")
    parser.add_argument("--product", type=int, help="Update single product by ID")
    parser.add_argument("--force", action="store_true", help="Overwrite existing values")
    parser.add_argument("--verify", action="store_true", help="Verify after pushing")
    args = parser.parse_args()

    if args.dry_run:
        dry_run(args.product, args.force)
    elif args.push:
        push(args.product, args.force, args.verify)


if __name__ == "__main__":
    main()
