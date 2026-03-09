#!/usr/bin/env python3
"""
push_profile_properties.py — Nature's Seed Spring 2026 Recovery

Reads the replacement map and customer category map, matches customers to their
best replacement product based on order history, then pushes custom profile
properties to Klaviyo so email templates can reference them via:
    {{ person|lookup:'previous_product_name' }}
    {{ person|lookup:'replacement_product_name' }}
    etc.

Usage:
    python push_profile_properties.py                   # full push
    python push_profile_properties.py --dry-run         # preview only
    python push_profile_properties.py --limit 50        # first 50 customers
    python push_profile_properties.py --category Lawn   # only Lawn customers
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional, Any, Dict, List, Tuple

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library is required. Install with: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
    print("WARNING: python-dotenv not installed. Will rely on environment variable KLAVIYO_PRIVATE_KEY.")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent          # spring-2026-recovery/
ANALYSIS_DIR = BASE_DIR / "analysis"
DATA_DIR = BASE_DIR / "data"

REPLACEMENT_MAP_PATH = ANALYSIS_DIR / "replacement_map_final.json"
CUSTOMER_CATEGORY_MAP_PATH = ANALYSIS_DIR / "customer_category_map.json"
ORDERS_Q1_PATH = DATA_DIR / "orders_q1_2025.json"
ORDERS_Q2_PATH = DATA_DIR / "orders_q2_2025.json"
REPORT_PATH = ANALYSIS_DIR / "profile_properties_report.csv"

KLAVIYO_API_BASE = "https://a.klaviyo.com/api"
KLAVIYO_REVISION = "2024-10-15"

# Category priority (higher index = lower priority; first match wins)
CATEGORY_PRIORITY = ["Pasture", "Lawn", "Wildflower", "Clover", "Specialty", "California", "Planting Aids"]

# Rate limits
RATE_LIMIT_GET = 10     # requests/sec for GET (profile lookup)
RATE_LIMIT_PATCH = 75   # requests/sec for PATCH (profile update)
# We'll use a conservative combined delay
REQUEST_DELAY = 0.15    # seconds between API calls (~6-7 req/s, safe margin)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Any:
    """Load a JSON file and return its contents."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace, remove special size/variant suffixes."""
    text = text.lower().strip()
    # Remove common variant suffixes like "- 5 lb", "- 1000 ft²", "- 1 Pack", etc.
    text = re.sub(r'\s*-\s*[\d,.]+\s*(lb|lbs|ft²|ft2|sq\s*ft|pack|oz|acre|acres)\.?$', '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text


def build_sku_index(replacement_map: list) -> dict:
    """Build a dict from SKU -> replacement map entry for exact SKU matching."""
    index = {}
    for entry in replacement_map:
        for sku in entry.get("old_variant_skus", []):
            sku_clean = sku.strip().upper()
            if sku_clean and sku_clean != "ID:0":
                index[sku_clean] = entry
    return index


def build_name_index(replacement_map: list) -> list:
    """Build a list of (normalized_old_name, entry) for name-based matching."""
    pairs = []
    for entry in replacement_map:
        norm = normalize(entry["old_base_name"])
        pairs.append((norm, entry))
    return pairs


def match_line_item_to_replacement(item: dict, sku_index: dict, name_index: list):
    """
    Try to match an order line item to a replacement map entry.
    Returns the entry or None.
    Priority: exact SKU match > exact name match > partial name match.
    """
    # 1. Exact SKU match
    item_sku = (item.get("sku") or "").strip().upper()
    if item_sku and item_sku in sku_index:
        return sku_index[item_sku]

    # 2. Name-based matching
    item_name_norm = normalize(item.get("name", ""))
    if not item_name_norm:
        return None

    # Exact normalized name match
    for norm_name, entry in name_index:
        if item_name_norm == norm_name:
            return entry

    # Partial/substring match: old_base_name contained in item name or vice versa
    for norm_name, entry in name_index:
        if norm_name in item_name_norm or item_name_norm in norm_name:
            return entry

    # Token overlap match (at least 70% of old_base_name tokens present)
    item_tokens = set(item_name_norm.split())
    for norm_name, entry in name_index:
        name_tokens = set(norm_name.split())
        if len(name_tokens) >= 2:
            overlap = len(item_tokens & name_tokens) / len(name_tokens)
            if overlap >= 0.7:
                return entry

    return None


def assign_primary_category(email: str, category_map: dict) -> str:
    """
    Determine the primary seed category for a customer.
    Uses the category_map 'groups' field and picks the first match in priority order.
    """
    info = category_map.get(email)
    if not info:
        return "Unknown"
    groups = info.get("groups", [])
    for priority_cat in CATEGORY_PRIORITY:
        if priority_cat in groups:
            return priority_cat
    # If none matched, return the first group or Unknown
    return groups[0] if groups else "Unknown"


# ---------------------------------------------------------------------------
# Klaviyo API
# ---------------------------------------------------------------------------

class KlaviyoClient:
    """Minimal Klaviyo API client for profile operations."""

    def __init__(self, api_key: str, dry_run: bool = False):
        self.api_key = api_key
        self.dry_run = dry_run
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Klaviyo-API-Key {api_key}",
            "revision": KLAVIYO_REVISION,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self._last_request_time = 0

    def _throttle(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make an API request with retry on 429 and transient errors."""
        max_retries = 5
        for attempt in range(max_retries):
            self._throttle()
            try:
                resp = self.session.request(method, url, **kwargs)
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", 5))
                    print(f"  Rate limited. Waiting {retry_after}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_after)
                    continue
                if resp.status_code >= 500:
                    wait = 2 ** attempt
                    print(f"  Server error {resp.status_code}. Retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    continue
                return resp
            except requests.exceptions.ConnectionError as e:
                wait = 2 ** attempt
                print(f"  Connection error: {e}. Retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
        # Final attempt without catching
        self._throttle()
        return self.session.request(method, url, **kwargs)

    def get_profile_by_email(self, email: str) -> Optional[str]:
        """
        Look up a Klaviyo profile ID by email address.
        Returns the profile ID or None if not found.
        """
        url = f"{KLAVIYO_API_BASE}/profiles/"
        params = {"filter": f'equals(email,"{email}")'}
        resp = self._request_with_retry("GET", url, params=params)
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", [])
        if data:
            return data[0]["id"]
        return None

    def update_profile_properties(self, profile_id: str, properties: dict) -> bool:
        """
        Update custom properties on a Klaviyo profile.
        Uses PATCH /api/profiles/{id}.
        Returns True on success.
        """
        url = f"{KLAVIYO_API_BASE}/profiles/{profile_id}"
        payload = {
            "data": {
                "type": "profile",
                "id": profile_id,
                "attributes": {
                    "properties": properties
                }
            }
        }
        resp = self._request_with_retry("PATCH", url, json=payload)
        if resp.status_code in (200, 204):
            return True
        else:
            print(f"  PATCH failed for {profile_id}: {resp.status_code} — {resp.text[:200]}")
            return False

    def create_or_update_profile(self, email: str, properties: dict) -> bool:
        """
        Use the Profiles Create or Update endpoint (POST /api/profile-import/)
        to upsert a profile by email and set properties in one call.
        This avoids the need for a separate GET to find the profile ID.
        Returns True on success.
        """
        url = f"{KLAVIYO_API_BASE}/profile-import/"
        payload = {
            "data": {
                "type": "profile",
                "attributes": {
                    "email": email,
                    "properties": properties
                }
            }
        }
        resp = self._request_with_retry("POST", url, json=payload)
        if resp.status_code in (200, 201, 204):
            return True
        else:
            print(f"  Profile import failed for {email}: {resp.status_code} — {resp.text[:200]}")
            return False


# ---------------------------------------------------------------------------
# Main Logic
# ---------------------------------------------------------------------------

def build_customer_product_map(orders: list, sku_index: dict, name_index: list) -> dict:
    """
    For each customer email, collect all matched replacement entries
    along with the line item revenue and the original product name.

    Returns: { email: [ (entry, line_item_revenue, original_product_name), ... ] }
    """
    customer_matches = defaultdict(list)

    for order in orders:
        email = (order.get("customer_email") or "").strip().lower()
        if not email:
            continue
        for item in order.get("line_items", []):
            entry = match_line_item_to_replacement(item, sku_index, name_index)
            if entry:
                line_revenue = float(item.get("total", 0)) or float(item.get("subtotal", 0))
                original_name = item.get("name", "")
                customer_matches[email].append((entry, line_revenue, original_name))

    return customer_matches


def pick_best_replacement(matches: list) -> tuple:
    """
    Given a list of (entry, line_revenue, original_product_name) for a customer,
    pick the best replacement:
      1. Highest match_score
      2. If tie, highest line_revenue
      3. If still tie, highest total_revenue from the replacement map entry

    Returns: (entry, original_product_name) for the best match
    """
    if not matches:
        return None, None

    # Sort by: match_score desc, line_revenue desc, total_revenue desc
    matches_sorted = sorted(
        matches,
        key=lambda x: (
            x[0].get("match_score", 0),
            x[1],
            x[0].get("total_revenue", 0),
        ),
        reverse=True,
    )
    best = matches_sorted[0]
    return best[0], best[2]


def build_profile_properties(entry: dict, original_product_name: str, primary_category: str) -> dict:
    """Build the dictionary of Klaviyo profile properties for one customer."""
    new_product = entry.get("new_product", {})
    return {
        "previous_product_name": original_product_name,
        "replacement_product_name": new_product.get("name", ""),
        "replacement_product_price": new_product.get("price", ""),
        "replacement_product_url": new_product.get("permalink", ""),
        "replacement_product_image": new_product.get("image", ""),
        "primary_seed_category": primary_category,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Push replacement product profile properties to Klaviyo."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be pushed without making API calls.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only the first N customers (0 = all).",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="",
        help="Only process customers in the given primary category (e.g., Lawn, Pasture).",
    )
    args = parser.parse_args()

    # -----------------------------------------------------------------------
    # Load API key
    # -----------------------------------------------------------------------
    env_paths = [
        Path.home() / "Desktop" / "ClaudeDataAgent -" / ".env",
        BASE_DIR / ".env",
        Path.cwd() / ".env",
    ]
    if load_dotenv:
        for p in env_paths:
            if p.exists():
                load_dotenv(p)
                break

    api_key = os.environ.get("KLAVIYO_PRIVATE_KEY", "")
    if not api_key and not args.dry_run:
        print("ERROR: KLAVIYO_PRIVATE_KEY not found in environment or .env file.")
        print("  Set it via: export KLAVIYO_PRIVATE_KEY=pk_xxx")
        print(f"  Or create a .env file at one of: {[str(p) for p in env_paths]}")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Load data files
    # -----------------------------------------------------------------------
    print("Loading data files...")

    replacement_map = load_json(REPLACEMENT_MAP_PATH)
    print(f"  Replacement map: {len(replacement_map)} entries")

    category_map = load_json(CUSTOMER_CATEGORY_MAP_PATH)
    print(f"  Customer category map: {len(category_map)} customers")

    orders_q1 = load_json(ORDERS_Q1_PATH)
    orders_q2 = load_json(ORDERS_Q2_PATH)
    all_orders = orders_q1 + orders_q2
    print(f"  Orders: {len(orders_q1)} (Q1) + {len(orders_q2)} (Q2) = {len(all_orders)} total")

    # -----------------------------------------------------------------------
    # Step 1: Build matching indexes
    # -----------------------------------------------------------------------
    print("\nBuilding product matching indexes...")
    sku_index = build_sku_index(replacement_map)
    name_index = build_name_index(replacement_map)
    print(f"  SKU index: {len(sku_index)} SKUs")
    print(f"  Name index: {len(name_index)} product names")

    # -----------------------------------------------------------------------
    # Step 2: Match customers to replacement products
    # -----------------------------------------------------------------------
    print("\nMatching customers to replacement products...")
    customer_matches = build_customer_product_map(all_orders, sku_index, name_index)
    print(f"  Customers with at least one match: {len(customer_matches)}")

    # -----------------------------------------------------------------------
    # Step 3: Pick best replacement per customer + assign category
    # -----------------------------------------------------------------------
    print("\nAssigning best replacement and primary category...")

    # We process all emails from the category map (the full audience)
    # but only those with matches get replacement properties
    all_emails = sorted(set(
        list(customer_matches.keys()) + [e.lower().strip() for e in category_map.keys()]
    ))
    print(f"  Total unique emails to consider: {len(all_emails)}")

    # Build the final property sets
    profiles_to_push = []   # list of (email, properties_dict)
    unmatched_emails = []   # emails with no replacement

    for email in all_emails:
        primary_cat = assign_primary_category(email, category_map)

        # Filter by category if requested
        if args.category and primary_cat.lower() != args.category.lower():
            continue

        matches = customer_matches.get(email, [])
        if matches:
            best_entry, original_name = pick_best_replacement(matches)
            props = build_profile_properties(best_entry, original_name, primary_cat)
            profiles_to_push.append((email, props))
        else:
            # Customer has no discontinued product match — still assign category
            props = {
                "primary_seed_category": primary_cat,
            }
            profiles_to_push.append((email, props))
            unmatched_emails.append(email)

    # Apply --limit
    if args.limit > 0:
        profiles_to_push = profiles_to_push[:args.limit]

    matched_count = sum(1 for _, p in profiles_to_push if "replacement_product_name" in p)
    category_only_count = len(profiles_to_push) - matched_count

    print(f"\n  Profiles to push: {len(profiles_to_push)}")
    print(f"    With replacement product: {matched_count}")
    print(f"    Category only (no match): {category_only_count}")

    # -----------------------------------------------------------------------
    # Category breakdown
    # -----------------------------------------------------------------------
    category_counts = defaultdict(int)
    for _, props in profiles_to_push:
        cat = props.get("primary_seed_category", "Unknown")
        category_counts[cat] += 1

    print("\n  Category breakdown:")
    for cat in CATEGORY_PRIORITY + ["Unknown"]:
        if cat in category_counts:
            print(f"    {cat}: {category_counts[cat]}")

    # -----------------------------------------------------------------------
    # Step 4: Push to Klaviyo (or dry-run)
    # -----------------------------------------------------------------------
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN — No API calls will be made.")
        print("=" * 60)
        # Show first 10 examples
        for i, (email, props) in enumerate(profiles_to_push[:10]):
            print(f"\n  [{i+1}] {email}")
            for k, v in props.items():
                display_val = str(v)[:80]
                print(f"      {k}: {display_val}")
        if len(profiles_to_push) > 10:
            print(f"\n  ... and {len(profiles_to_push) - 10} more profiles.")
    else:
        print(f"\nPushing {len(profiles_to_push)} profiles to Klaviyo...")
        client = KlaviyoClient(api_key, dry_run=args.dry_run)

        success_count = 0
        fail_count = 0
        start_time = time.time()

        for i, (email, props) in enumerate(profiles_to_push):
            if (i + 1) % 100 == 0 or i == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                print(f"  Progress: {i+1}/{len(profiles_to_push)} "
                      f"({(i+1)*100//len(profiles_to_push)}%) "
                      f"— {rate:.1f} profiles/sec "
                      f"— OK: {success_count}, Fail: {fail_count}")

            ok = client.create_or_update_profile(email, props)
            if ok:
                success_count += 1
            else:
                fail_count += 1

        elapsed_total = time.time() - start_time
        print(f"\n  Done in {elapsed_total:.1f}s")
        print(f"  Success: {success_count}")
        print(f"  Failed:  {fail_count}")

    # -----------------------------------------------------------------------
    # Step 5: Save CSV report
    # -----------------------------------------------------------------------
    print(f"\nSaving report to {REPORT_PATH}...")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "email",
            "previous_product_name",
            "replacement_product_name",
            "replacement_product_price",
            "replacement_product_url",
            "replacement_product_image",
            "primary_seed_category",
            "has_replacement",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for email, props in profiles_to_push:
            row = {
                "email": email,
                "previous_product_name": props.get("previous_product_name", ""),
                "replacement_product_name": props.get("replacement_product_name", ""),
                "replacement_product_price": props.get("replacement_product_price", ""),
                "replacement_product_url": props.get("replacement_product_url", ""),
                "replacement_product_image": props.get("replacement_product_image", ""),
                "primary_seed_category": props.get("primary_seed_category", ""),
                "has_replacement": "yes" if "replacement_product_name" in props else "no",
            }
            writer.writerow(row)

    print(f"  Report saved: {len(profiles_to_push)} rows")

    # -----------------------------------------------------------------------
    # Final summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total customers processed:          {len(profiles_to_push)}")
    print(f"  Matched to a replacement product:   {matched_count}")
    print(f"  Category-only (no replacement):     {category_only_count}")
    print(f"  Unmatched emails (from full pool):  {len(unmatched_emails)}")
    print()
    print("  Category breakdown:")
    for cat in CATEGORY_PRIORITY + ["Unknown"]:
        if cat in category_counts:
            print(f"    {cat:20s} {category_counts[cat]:>6}")
    print()
    print(f"  Report: {REPORT_PATH}")
    if args.dry_run:
        print("\n  ** This was a DRY RUN. No data was pushed to Klaviyo. **")
    print()


if __name__ == "__main__":
    main()
