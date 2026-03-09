#!/usr/bin/env python3
"""
push_replacement_properties.py — Nature's Seed Spring 2026 Recovery

COMPREHENSIVE PIPELINE:
1. Loads all order data (Q1/Q2 2025 WC orders + optional Klaviyo event history)
2. Cross-references products against WooCommerce active product list
3. Identifies discontinued products each customer purchased
4. Matches discontinued products to replacements via replacement_map_final.json
5. Pushes profile properties to Klaviyo using the ns_p1_* convention

Profile properties pushed:
    ns_p1_name                  - The discontinued product they bought
    ns_p1_sku                   - SKU of the discontinued product
    ns_p1_status                - "discontinued"
    ns_p1_replacement_name      - The recommended replacement product
    ns_p1_replacement_sku       - Replacement product SKU
    ns_p1_replacement_url       - Replacement product permalink
    ns_p1_replacement_price     - Replacement product price
    ns_p1_replacement_image     - Replacement product image URL
    ns_p1_replacement_bullets   - Key selling points (pipe-separated)
    ns_draft_hit                - true (flag for Klaviyo segment/flow use)
    primary_seed_category       - Customer's primary product category

Email templates then reference these via:
    {{ person|lookup:'ns_p1_replacement_name'|default:'a premium seed product' }}
    {{ person|lookup:'ns_p1_replacement_url' }}
    etc.

Usage:
    python push_replacement_properties.py --dry-run         # Preview (no API calls)
    python push_replacement_properties.py                   # Full push
    python push_replacement_properties.py --limit 50        # First 50 customers
    python push_replacement_properties.py --category Lawn   # Only Lawn category
    python push_replacement_properties.py --fetch-events    # Also query Klaviyo events for 3yr history
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
from typing import Optional, Any, Dict, List, Tuple, Set

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library is required. Install with: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


# ---------------------------------------------------------------------------
# Constants & Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent          # spring-2026-recovery/
ANALYSIS_DIR = BASE_DIR / "analysis"
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = BASE_DIR / "scripts"

REPLACEMENT_MAP_PATH = ANALYSIS_DIR / "replacement_map_final.json"
CUSTOMER_CATEGORY_MAP_PATH = ANALYSIS_DIR / "customer_category_map.json"
PRODUCTS_ACTIVE_PATH = DATA_DIR / "products_active.json"
PRODUCTS_INACTIVE_PATH = DATA_DIR / "products_inactive.json"
ORDERS_Q1_PATH = DATA_DIR / "orders_q1_2025.json"
ORDERS_Q2_PATH = DATA_DIR / "orders_q2_2025.json"
REPORT_PATH = ANALYSIS_DIR / "replacement_push_report.csv"
UNMATCHED_PATH = ANALYSIS_DIR / "unmatched_discontinued_products.csv"

KLAVIYO_API_BASE = "https://a.klaviyo.com/api"
KLAVIYO_REVISION = "2024-10-15"

# Klaviyo metric IDs
METRIC_WC_ORDERED_PRODUCT = "WpcPAe"     # WooCommerce Ordered Product (Sept 2024+)
METRIC_MAGENTO_ORDERED_PRODUCT = "X3UByC" # Magento Ordered Product (pre-Sept 2024)

# Category priority (first match wins when assigning primary category)
CATEGORY_PRIORITY = ["Lawn", "Pasture", "Wildflower", "Clover", "Cover Crop", "Food Plot", "Specialty"]

# Rate limiting
REQUEST_DELAY = 0.15  # seconds between API calls


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Any:
    """Load a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_active_products() -> Dict[str, dict]:
    """
    Load active WooCommerce products and return lookups.
    Returns: { 'sku_upper': product_dict, ... }
    """
    products = load_json(PRODUCTS_ACTIVE_PATH)
    sku_lookup = {}
    name_lookup = {}

    for p in products:
        sku = (p.get("sku") or "").strip().upper()
        name = (p.get("name") or "").strip().lower()
        if sku:
            sku_lookup[sku] = p
        if name:
            name_lookup[name] = p

    return sku_lookup, name_lookup


def load_inactive_products() -> Dict[str, dict]:
    """Load inactive/draft WooCommerce products."""
    products = load_json(PRODUCTS_INACTIVE_PATH)
    sku_lookup = {}
    for p in products:
        sku = (p.get("sku") or "").strip().upper()
        if sku:
            sku_lookup[sku] = p
    return sku_lookup


# ---------------------------------------------------------------------------
# SKU & Name Normalization
# ---------------------------------------------------------------------------

def normalize_name(text: str) -> str:
    """Lowercase, strip, remove variant suffixes, collapse whitespace."""
    text = text.lower().strip()
    # Remove common variant suffixes like "- 5 lb", "- 1000 ft²", etc.
    text = re.sub(r'\s*-\s*[\d,.]+\s*(lb|lbs|ft²|ft2|sq\s*ft|pack|oz|acre|acres)\.?$', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def strip_old_suffix(sku: str) -> str:
    """Remove -OLD suffix from SKU for matching."""
    return re.sub(r'-OLD$', '', sku.upper().strip())


def extract_base_sku(sku: str) -> str:
    """
    Extract the base product SKU from a variant SKU.
    E.g., PB-HRSE-N-5-LB -> PB-HRSE-N
          S-TRRE-0.25-A -> S-TRRE
          TURF-JBR-5-LB -> TURF-JBR
    """
    sku = sku.upper().strip()
    # Remove -OLD suffix first
    sku = strip_old_suffix(sku)
    # Remove common size suffixes: -5-LB, -0.25-A, -1000-F, -500-F, -10-LB, etc.
    sku = re.sub(r'-[\d.]+-(LB|A|F|OZ|ACRE|PACK|SQ)$', '', sku)
    # Remove just weight suffixes: -5-LB, -25-LB
    sku = re.sub(r'-[\d.]+-LB$', '', sku)
    return sku


# ---------------------------------------------------------------------------
# Replacement Map Indexes
# ---------------------------------------------------------------------------

def build_replacement_indexes(replacement_map: list) -> Tuple[dict, dict, list]:
    """
    Build multiple indexes for matching products to replacements.

    Returns:
        sku_exact_index: { 'SKU': entry } - exact SKU match (includes -OLD variants)
        sku_base_index:  { 'BASE_SKU': entry } - base SKU after stripping -OLD and size
        name_index:      [ (normalized_name, entry) ] - for name-based matching
    """
    sku_exact_index = {}
    sku_base_index = {}
    name_index = []

    for entry in replacement_map:
        # Index by old variant SKUs
        for sku in entry.get("old_variant_skus", []):
            sku_clean = sku.strip().upper()
            if sku_clean and sku_clean != "ID:0" and sku_clean != "-OLD":
                # Exact match (including -OLD suffix)
                sku_exact_index[sku_clean] = entry
                # Also index the stripped version (without -OLD)
                base = strip_old_suffix(sku_clean)
                if base and base != sku_clean:
                    sku_exact_index[base] = entry
                # Also index the base SKU (without size suffix)
                base_sku = extract_base_sku(sku_clean)
                if base_sku:
                    sku_base_index[base_sku] = entry

        # Index by old product name
        norm_name = normalize_name(entry.get("old_base_name", ""))
        if norm_name:
            name_index.append((norm_name, entry))

    return sku_exact_index, sku_base_index, name_index


def match_product_to_replacement(
    sku: str,
    name: str,
    sku_exact_index: dict,
    sku_base_index: dict,
    name_index: list,
) -> Optional[dict]:
    """
    Multi-level matching to find a replacement for a product.
    Priority: exact SKU > SKU without -OLD > base SKU > exact name > substring name > token overlap.
    """
    sku_upper = (sku or "").strip().upper()
    name_norm = normalize_name(name or "")

    # Level 1: Exact SKU match
    if sku_upper and sku_upper in sku_exact_index:
        return sku_exact_index[sku_upper]

    # Level 2: SKU with -OLD appended (in case the map stores -OLD versions)
    if sku_upper and f"{sku_upper}-OLD" in sku_exact_index:
        return sku_exact_index[f"{sku_upper}-OLD"]

    # Level 3: Base SKU match (strip size suffixes)
    if sku_upper:
        base = extract_base_sku(sku_upper)
        if base and base in sku_base_index:
            return sku_base_index[base]

    # Level 4: Exact normalized name match
    if name_norm:
        for norm_name, entry in name_index:
            if name_norm == norm_name:
                return entry

    # Level 5: Substring name match (old name contained in order name or vice versa)
    if name_norm and len(name_norm) > 5:
        for norm_name, entry in name_index:
            if len(norm_name) > 5:
                if norm_name in name_norm or name_norm in norm_name:
                    return entry

    # Level 6: Token overlap (>= 70% of old name tokens present in order item name)
    if name_norm:
        item_tokens = set(name_norm.split())
        for norm_name, entry in name_index:
            name_tokens = set(norm_name.split())
            if len(name_tokens) >= 2 and len(item_tokens) >= 2:
                overlap = len(item_tokens & name_tokens) / len(name_tokens)
                if overlap >= 0.7:
                    return entry

    return None


# ---------------------------------------------------------------------------
# Product Status Check
# ---------------------------------------------------------------------------

def is_product_active(sku: str, name: str, active_sku_lookup: dict, active_name_lookup: dict) -> bool:
    """Check if a product is currently active on WooCommerce."""
    sku_upper = (sku or "").strip().upper()
    name_lower = (name or "").strip().lower()

    if sku_upper and sku_upper in active_sku_lookup:
        return True
    if name_lower and name_lower in active_name_lookup:
        return True
    return False


# ---------------------------------------------------------------------------
# Customer -> Discontinued Product -> Replacement Pipeline
# ---------------------------------------------------------------------------

def process_orders(
    orders: list,
    active_sku_lookup: dict,
    active_name_lookup: dict,
    sku_exact_index: dict,
    sku_base_index: dict,
    name_index: list,
) -> Tuple[dict, dict]:
    """
    Process all orders to build:
    1. customer_discontinued: { email: [(sku, name, revenue, replacement_entry), ...] }
    2. unmatched_products: { (sku, name): count } - discontinued products with no replacement

    Returns: (customer_discontinued, unmatched_products)
    """
    customer_discontinued = defaultdict(list)
    unmatched_products = defaultdict(int)

    for order in orders:
        email = (order.get("customer_email") or "").strip().lower()
        if not email:
            continue

        for item in order.get("line_items", []):
            sku = (item.get("sku") or "").strip()
            name = (item.get("name") or "").strip()
            revenue = float(item.get("total", 0) or item.get("subtotal", 0) or 0)

            # Skip if product is still active
            if is_product_active(sku, name, active_sku_lookup, active_name_lookup):
                continue

            # Product is discontinued — try to find a replacement
            replacement = match_product_to_replacement(
                sku, name, sku_exact_index, sku_base_index, name_index
            )

            if replacement:
                customer_discontinued[email].append((sku, name, revenue, replacement))
            else:
                unmatched_products[(sku, name)] += 1
                # Still track the customer with a None replacement
                customer_discontinued[email].append((sku, name, revenue, None))

    return customer_discontinued, unmatched_products


def pick_best_replacement(items: list) -> Tuple[Optional[dict], str, str]:
    """
    From a list of (sku, name, revenue, replacement_entry) for one customer,
    pick the BEST replacement to feature.

    Priority:
    1. Items that HAVE a replacement (non-None)
    2. Highest match_score
    3. Highest revenue from that line item
    4. Highest total_revenue in the replacement map entry

    Returns: (best_replacement_entry, original_product_name, original_sku)
    """
    # Filter to items with replacements
    with_replacement = [(s, n, r, e) for s, n, r, e in items if e is not None]

    if not with_replacement:
        # No replacement found — return the highest-revenue discontinued product
        items_sorted = sorted(items, key=lambda x: x[2], reverse=True)
        best = items_sorted[0]
        return None, best[1], best[0]

    # Sort by: match_score desc, line_revenue desc, total_revenue desc
    with_replacement.sort(
        key=lambda x: (
            x[3].get("match_score", 0),
            x[2],
            x[3].get("total_revenue", 0),
        ),
        reverse=True,
    )

    best = with_replacement[0]
    return best[3], best[1], best[0]


# ---------------------------------------------------------------------------
# Klaviyo Events (optional 3-year enhancement)
# ---------------------------------------------------------------------------

def fetch_klaviyo_events(api_key: str, metric_id: str, since_date: str, max_pages: int = 200) -> list:
    """
    Paginate through Klaviyo events for a given metric.
    Returns list of simplified event dicts: { profile_email, product_name, product_sku, revenue }
    """
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Klaviyo-API-Key {api_key}",
        "revision": KLAVIYO_REVISION,
        "Accept": "application/json",
    })

    url = f"{KLAVIYO_API_BASE}/events/"
    params = {
        "filter": f'greater-or-equal(datetime,{since_date}),equals(metric_id,"{metric_id}")',
        "include": "profile",
        "fields[event]": "event_properties,datetime",
        "fields[profile]": "email",
        "page[size]": 50,
        "sort": "-datetime",
    }

    all_events = []
    page = 0

    while url and page < max_pages:
        page += 1
        if page > 1:
            params = None  # Cursor-based pagination uses next URL

        try:
            resp = session.get(url, params=params)
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 10))
                print(f"    Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            if resp.status_code != 200:
                print(f"    Error {resp.status_code}: {resp.text[:200]}")
                break

            data = resp.json()
            events = data.get("data", [])
            included = {item["id"]: item for item in data.get("included", [])}

            for event in events:
                props = event.get("attributes", {}).get("event_properties", {})
                # Get profile email from included data
                profile_rel = event.get("relationships", {}).get("profile", {}).get("data", {})
                profile_id = profile_rel.get("id", "")
                profile_email = ""
                if profile_id and profile_id in included:
                    profile_email = included[profile_id].get("attributes", {}).get("email", "")

                if profile_email:
                    all_events.append({
                        "profile_email": profile_email.lower().strip(),
                        "product_name": props.get("ProductName", props.get("product_name", "")),
                        "product_sku": props.get("SKU", props.get("sku", "")),
                        "revenue": float(props.get("$value", props.get("value", 0)) or 0),
                    })

            # Get next page URL
            next_url = data.get("links", {}).get("next")
            if next_url and events:
                url = next_url
                time.sleep(0.3)
            else:
                break

            if page % 10 == 0:
                print(f"    Page {page}: {len(all_events)} events so far...")

        except Exception as e:
            print(f"    Error on page {page}: {e}")
            break

    return all_events


def process_klaviyo_events(
    events: list,
    active_sku_lookup: dict,
    active_name_lookup: dict,
    sku_exact_index: dict,
    sku_base_index: dict,
    name_index: list,
    existing_customers: set,
) -> dict:
    """Process Klaviyo events and add NEW customers not already in order data."""
    new_customer_discontinued = defaultdict(list)

    for evt in events:
        email = evt["profile_email"]
        if email in existing_customers:
            continue  # Already processed from order files

        sku = evt.get("product_sku", "")
        name = evt.get("product_name", "")
        revenue = evt.get("revenue", 0)

        # Skip active products
        if is_product_active(sku, name, active_sku_lookup, active_name_lookup):
            continue

        replacement = match_product_to_replacement(
            sku, name, sku_exact_index, sku_base_index, name_index
        )

        new_customer_discontinued[email].append((sku, name, revenue, replacement))

    return new_customer_discontinued


# ---------------------------------------------------------------------------
# Klaviyo Profile Push
# ---------------------------------------------------------------------------

class KlaviyoClient:
    """Minimal Klaviyo API client for profile upsert operations."""

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
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        max_retries = 5
        for attempt in range(max_retries):
            self._throttle()
            try:
                resp = self.session.request(method, url, **kwargs)
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", 5))
                    print(f"  Rate limited. Waiting {retry_after}s (attempt {attempt+1})")
                    time.sleep(retry_after)
                    continue
                if resp.status_code >= 500:
                    wait = 2 ** attempt
                    print(f"  Server error {resp.status_code}. Retrying in {wait}s")
                    time.sleep(wait)
                    continue
                return resp
            except requests.exceptions.ConnectionError as e:
                wait = 2 ** attempt
                print(f"  Connection error. Retrying in {wait}s")
                time.sleep(wait)
        self._throttle()
        return self.session.request(method, url, **kwargs)

    def upsert_profile(self, email: str, properties: dict) -> bool:
        """Upsert a profile by email with the given custom properties."""
        if self.dry_run:
            return True

        url = f"{KLAVIYO_API_BASE}/profile-import/"
        payload = {
            "data": {
                "type": "profile",
                "attributes": {
                    "email": email,
                    "properties": properties,
                },
            }
        }
        resp = self._request_with_retry("POST", url, json=payload)
        if resp.status_code in (200, 201, 204):
            return True
        else:
            print(f"  FAILED for {email}: {resp.status_code} — {resp.text[:200]}")
            return False


# ---------------------------------------------------------------------------
# Property Builder
# ---------------------------------------------------------------------------

def build_profile_properties(
    replacement_entry: Optional[dict],
    original_name: str,
    original_sku: str,
    primary_category: str,
) -> dict:
    """
    Build the ns_p1_* profile properties dict for one customer.
    """
    props = {
        # The discontinued product they bought
        "ns_p1_name": original_name,
        "ns_p1_sku": original_sku,
        "ns_p1_status": "discontinued",
        "ns_draft_hit": True,
        "primary_seed_category": primary_category,
    }

    if replacement_entry:
        new_product = replacement_entry.get("new_product", {})
        bullets = replacement_entry.get("bullets", [])

        props.update({
            "ns_p1_replacement_name": new_product.get("name", ""),
            "ns_p1_replacement_sku": new_product.get("sku", ""),
            "ns_p1_replacement_url": new_product.get("permalink", ""),
            "ns_p1_replacement_price": str(new_product.get("price", "")),
            "ns_p1_replacement_image": new_product.get("image", ""),
            "ns_p1_replacement_bullets": " | ".join(bullets[:4]) if bullets else "",
            "ns_p1_replacement_description": (new_product.get("description_text", "") or "")[:500],
            # Also store highlights if available
            "ns_p1_replacement_highlights": " | ".join(
                new_product.get("highlights", [])[:6]
            ) if new_product.get("highlights") else "",
        })
    else:
        # No replacement — clear any stale data
        props.update({
            "ns_p1_replacement_name": "",
            "ns_p1_replacement_sku": "",
            "ns_p1_replacement_url": "",
            "ns_p1_replacement_price": "",
            "ns_p1_replacement_image": "",
            "ns_p1_replacement_bullets": "",
            "ns_p1_replacement_description": "",
            "ns_p1_replacement_highlights": "",
        })

    return props


# ---------------------------------------------------------------------------
# Category Assignment
# ---------------------------------------------------------------------------

def assign_primary_category(email: str, category_map: dict) -> str:
    """Assign a primary seed category for a customer based on purchase history."""
    info = category_map.get(email, category_map.get(email.lower()))
    if not info:
        return "Unknown"
    groups = info.get("groups", [])
    for priority_cat in CATEGORY_PRIORITY:
        if priority_cat in groups:
            return priority_cat
    return groups[0] if groups else "Unknown"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Push replacement product properties to Klaviyo profiles (ns_p1_* convention)."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without making API calls.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only first N customers (0 = all).")
    parser.add_argument("--category", type=str, default="",
                        help="Only process customers in given primary category.")
    parser.add_argument("--fetch-events", action="store_true",
                        help="Also query Klaviyo events API for 3-year purchase history.")
    parser.add_argument("--max-event-pages", type=int, default=200,
                        help="Max pages to fetch per metric when using --fetch-events.")
    args = parser.parse_args()

    # -------------------------------------------------------------------
    # Load API key
    # -------------------------------------------------------------------
    env_paths = [
        Path.home() / "Desktop" / "ClaudeDataAgent - " / ".env",  # Note: space before dash
        Path.home() / "Desktop" / "ClaudeDataAgent -" / ".env",
        BASE_DIR / ".env",
        Path.cwd() / ".env",
    ]
    if load_dotenv:
        for p in env_paths:
            if p.exists():
                load_dotenv(p)
                print(f"  Loaded .env from: {p}")
                break

    api_key = os.environ.get("KLAVIYO_API", os.environ.get("KLAVIYO_PRIVATE_KEY", ""))
    if not api_key and not args.dry_run:
        print("ERROR: KLAVIYO_PRIVATE_KEY not found.")
        print("  Set via: export KLAVIYO_PRIVATE_KEY=pk_xxx")
        print(f"  Or create .env at: {[str(p) for p in env_paths]}")
        sys.exit(1)

    # -------------------------------------------------------------------
    # Step 1: Load all data files
    # -------------------------------------------------------------------
    print("=" * 70)
    print("STEP 1: Loading data files")
    print("=" * 70)

    active_sku_lookup, active_name_lookup = load_active_products()
    print(f"  Active products: {len(active_sku_lookup)} SKUs, {len(active_name_lookup)} names")

    inactive_sku_lookup = load_inactive_products()
    print(f"  Inactive products: {len(inactive_sku_lookup)} SKUs")

    replacement_map = load_json(REPLACEMENT_MAP_PATH)
    print(f"  Replacement map: {len(replacement_map)} entries")

    category_map = load_json(CUSTOMER_CATEGORY_MAP_PATH)
    print(f"  Customer category map: {len(category_map)} customers")

    orders_q1 = load_json(ORDERS_Q1_PATH)
    orders_q2 = load_json(ORDERS_Q2_PATH)
    all_orders = orders_q1 + orders_q2
    print(f"  Orders: {len(orders_q1)} (Q1) + {len(orders_q2)} (Q2) = {len(all_orders)} total")

    # -------------------------------------------------------------------
    # Step 2: Build replacement matching indexes
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("STEP 2: Building replacement matching indexes")
    print("=" * 70)

    sku_exact_index, sku_base_index, name_index = build_replacement_indexes(replacement_map)
    print(f"  SKU exact index: {len(sku_exact_index)} entries")
    print(f"  SKU base index: {len(sku_base_index)} entries")
    print(f"  Name index: {len(name_index)} entries")

    # -------------------------------------------------------------------
    # Step 3: Process Q1/Q2 orders
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("STEP 3: Processing Q1/Q2 2025 orders")
    print("=" * 70)

    customer_discontinued, unmatched_products = process_orders(
        all_orders, active_sku_lookup, active_name_lookup,
        sku_exact_index, sku_base_index, name_index,
    )

    print(f"  Customers with discontinued products: {len(customer_discontinued)}")
    with_replacement = sum(
        1 for items in customer_discontinued.values()
        if any(entry is not None for _, _, _, entry in items)
    )
    print(f"  Customers with at least one replacement match: {with_replacement}")
    print(f"  Unique unmatched discontinued products: {len(unmatched_products)}")

    # -------------------------------------------------------------------
    # Step 3b: Optional Klaviyo events enhancement
    # -------------------------------------------------------------------
    if args.fetch_events and api_key:
        print("\n" + "=" * 70)
        print("STEP 3b: Fetching Klaviyo events (3-year history)")
        print("=" * 70)

        existing_emails = set(customer_discontinued.keys())

        # Fetch WooCommerce Ordered Product events (Sept 2024+)
        print(f"\n  Fetching WC Ordered Product events (metric {METRIC_WC_ORDERED_PRODUCT})...")
        wc_events = fetch_klaviyo_events(
            api_key, METRIC_WC_ORDERED_PRODUCT,
            "2023-03-01T00:00:00Z",
            max_pages=args.max_event_pages,
        )
        print(f"    Retrieved {len(wc_events)} WC events")

        # Fetch Magento Ordered Product events (pre-Sept 2024)
        print(f"\n  Fetching Magento Ordered Product events (metric {METRIC_MAGENTO_ORDERED_PRODUCT})...")
        mag_events = fetch_klaviyo_events(
            api_key, METRIC_MAGENTO_ORDERED_PRODUCT,
            "2023-03-01T00:00:00Z",
            max_pages=args.max_event_pages,
        )
        print(f"    Retrieved {len(mag_events)} Magento events")

        # Process new customers from events
        all_events = wc_events + mag_events
        new_customers = process_klaviyo_events(
            all_events, active_sku_lookup, active_name_lookup,
            sku_exact_index, sku_base_index, name_index,
            existing_emails,
        )
        print(f"\n  NEW customers from Klaviyo events: {len(new_customers)}")

        # Merge into main dict
        for email, items in new_customers.items():
            customer_discontinued[email].extend(items)

        print(f"  Total customers after merge: {len(customer_discontinued)}")

    # -------------------------------------------------------------------
    # Step 4: Pick best replacement per customer + build properties
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("STEP 4: Building profile properties")
    print("=" * 70)

    profiles_to_push = []  # list of (email, properties_dict)
    no_replacement_customers = []

    for email, items in sorted(customer_discontinued.items()):
        primary_cat = assign_primary_category(email, category_map)

        # Filter by category if requested
        if args.category and primary_cat.lower() != args.category.lower():
            continue

        # Pick the best replacement
        best_entry, original_name, original_sku = pick_best_replacement(items)

        props = build_profile_properties(best_entry, original_name, original_sku, primary_cat)
        profiles_to_push.append((email, props))

        if best_entry is None:
            no_replacement_customers.append((email, original_name, original_sku, primary_cat))

    # Apply --limit
    if args.limit > 0:
        profiles_to_push = profiles_to_push[:args.limit]

    matched_count = sum(1 for _, p in profiles_to_push if p.get("ns_p1_replacement_name"))
    no_match_count = len(profiles_to_push) - matched_count

    print(f"  Total profiles to push: {len(profiles_to_push)}")
    print(f"    With replacement product: {matched_count}")
    print(f"    No replacement available: {no_match_count}")

    # Category breakdown
    cat_counts = defaultdict(lambda: {"total": 0, "with_replacement": 0})
    for _, props in profiles_to_push:
        cat = props.get("primary_seed_category", "Unknown")
        cat_counts[cat]["total"] += 1
        if props.get("ns_p1_replacement_name"):
            cat_counts[cat]["with_replacement"] += 1

    print("\n  Category breakdown:")
    print(f"  {'Category':<20} {'Total':>8} {'w/ Replacement':>15} {'No Replacement':>15}")
    print(f"  {'-'*60}")
    for cat in CATEGORY_PRIORITY + ["Unknown"]:
        if cat in cat_counts:
            t = cat_counts[cat]["total"]
            w = cat_counts[cat]["with_replacement"]
            print(f"  {cat:<20} {t:>8} {w:>15} {t-w:>15}")

    # -------------------------------------------------------------------
    # Step 5: Push to Klaviyo (or dry-run preview)
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    if args.dry_run:
        print("STEP 5: DRY RUN PREVIEW (no API calls)")
    else:
        print("STEP 5: Pushing to Klaviyo")
    print("=" * 70)

    if args.dry_run:
        # Show first 15 examples
        for i, (email, props) in enumerate(profiles_to_push[:15]):
            has_rep = "YES" if props.get("ns_p1_replacement_name") else "NO"
            print(f"\n  [{i+1}] {email} (replacement: {has_rep})")
            for k, v in sorted(props.items()):
                display_val = str(v)[:80]
                print(f"      {k}: {display_val}")
        if len(profiles_to_push) > 15:
            print(f"\n  ... and {len(profiles_to_push) - 15} more profiles.")
        print(f"\n  ** DRY RUN — No data was pushed to Klaviyo. **")
    else:
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

            ok = client.upsert_profile(email, props)
            if ok:
                success_count += 1
            else:
                fail_count += 1

        elapsed_total = time.time() - start_time
        print(f"\n  Done in {elapsed_total:.1f}s")
        print(f"  Success: {success_count}")
        print(f"  Failed:  {fail_count}")

    # -------------------------------------------------------------------
    # Step 6: Save reports
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("STEP 6: Saving reports")
    print("=" * 70)

    # Main report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "email", "primary_seed_category",
            "ns_p1_name", "ns_p1_sku",
            "ns_p1_replacement_name", "ns_p1_replacement_sku",
            "ns_p1_replacement_price", "ns_p1_replacement_url",
            "ns_p1_replacement_image", "has_replacement",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for email, props in profiles_to_push:
            writer.writerow({
                "email": email,
                "primary_seed_category": props.get("primary_seed_category", ""),
                "ns_p1_name": props.get("ns_p1_name", ""),
                "ns_p1_sku": props.get("ns_p1_sku", ""),
                "ns_p1_replacement_name": props.get("ns_p1_replacement_name", ""),
                "ns_p1_replacement_sku": props.get("ns_p1_replacement_sku", ""),
                "ns_p1_replacement_price": props.get("ns_p1_replacement_price", ""),
                "ns_p1_replacement_url": props.get("ns_p1_replacement_url", ""),
                "ns_p1_replacement_image": props.get("ns_p1_replacement_image", ""),
                "has_replacement": "yes" if props.get("ns_p1_replacement_name") else "no",
            })

    print(f"  Main report: {REPORT_PATH} ({len(profiles_to_push)} rows)")

    # Unmatched products report
    with open(UNMATCHED_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["sku", "product_name", "order_count"])
        for (sku, name), count in sorted(unmatched_products.items(), key=lambda x: -x[1]):
            writer.writerow([sku, name, count])

    print(f"  Unmatched products: {UNMATCHED_PATH} ({len(unmatched_products)} products)")

    # -------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total profiles processed:           {len(profiles_to_push)}")
    print(f"  With replacement product:           {matched_count}")
    print(f"  Without replacement:                {no_match_count}")
    print(f"  Match rate:                         {matched_count*100/max(len(profiles_to_push),1):.1f}%")
    print()
    print("  Profile properties pushed (ns_p1_* convention):")
    print("    ns_p1_name                   — Discontinued product name")
    print("    ns_p1_sku                    — Discontinued product SKU")
    print("    ns_p1_status                 — 'discontinued'")
    print("    ns_p1_replacement_name       — Replacement product name")
    print("    ns_p1_replacement_sku        — Replacement product SKU")
    print("    ns_p1_replacement_url        — Replacement product permalink")
    print("    ns_p1_replacement_price      — Replacement product price")
    print("    ns_p1_replacement_image      — Replacement product image URL")
    print("    ns_p1_replacement_bullets    — Key selling points")
    print("    ns_p1_replacement_highlights — Product highlights")
    print("    ns_draft_hit                 — true (segment/flow flag)")
    print("    primary_seed_category        — Customer's primary category")
    print()
    print("  Email template usage:")
    print("    {{ person|lookup:'ns_p1_replacement_name'|default:'a premium seed product' }}")
    print("    {{ person|lookup:'ns_p1_replacement_url' }}")
    print("    {{ person|lookup:'ns_p1_replacement_price' }}")
    print("    {{ person|lookup:'ns_p1_replacement_image' }}")
    print()

    if args.dry_run:
        print("  ** DRY RUN — No data was pushed. Run without --dry-run to push. **")


if __name__ == "__main__":
    main()
