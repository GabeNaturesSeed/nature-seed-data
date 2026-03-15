#!/usr/bin/env python3
"""
Nature's Seed — Walmart Marketplace Funnel Analysis

Analyzes the Walmart channel for revenue leaks:
  1. Listing health (publish status, lifecycle, missing content)
  2. Inventory gaps (out-of-stock, low-stock items)
  3. Order performance (last 30 days)
  4. Price discrepancies vs WooCommerce
  5. Estimated lost revenue from issues

Usage:
  python3 marketplace_walmart.py
"""

import json
import os
import sys
import time
import base64
import uuid
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict

# ══════════════════════════════════════════════════════════════
# ENV SETUP (same pattern as daily_pull.py)
# ══════════════════════════════════════════════════════════════

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
env_vars = {}
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip().strip("'\"")
else:
    # Fall back to environment variables
    print(f"[WARN] .env not found at {env_path}, using environment variables")

def get_env(key, default=""):
    return env_vars.get(key, os.environ.get(key, default))

WM_CLIENT_ID = get_env("WALMART_CLIENT_ID")
WM_CLIENT_SECRET = get_env("WALMART_CLIENT_SECRET")
WM_BASE = "https://marketplace.walmartapis.com/v3"

# Determine if we can use live API or must fall back to cached data
LIVE_API = bool(WM_CLIENT_ID and WM_CLIENT_SECRET)
if not LIVE_API:
    print("[INFO] No Walmart credentials — will use cached inventory sync report + WC Store API")
    print("       Set WALMART_CLIENT_ID and WALMART_CLIENT_SECRET in .env for live API mode")

# Path to cached inventory sync report from walmart-optimization
CACHED_REPORT = Path(__file__).resolve().parent.parent.parent / "walmart-optimization" / "data" / "inventory_sync_report.csv"


# ══════════════════════════════════════════════════════════════
# WALMART AUTH (token caching with 15-min expiry)
# ══════════════════════════════════════════════════════════════

_wm_token_cache = {"token": None, "expires_at": None}


def wm_get_token():
    """Get/refresh Walmart OAuth token (expires in 15 min)."""
    now = datetime.utcnow()
    if _wm_token_cache["token"] and _wm_token_cache["expires_at"] and now < _wm_token_cache["expires_at"]:
        return _wm_token_cache["token"]

    creds = base64.b64encode(f"{WM_CLIENT_ID}:{WM_CLIENT_SECRET}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(f"{WM_BASE}/token", data=body, method="POST")
    req.add_header("Authorization", f"Basic {creds}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/json")
    req.add_header("WM_SVC.NAME", "Nature's Seed")
    req.add_header("WM_QOS.CORRELATION_ID", str(uuid.uuid4()))

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())

    _wm_token_cache["token"] = data["access_token"]
    _wm_token_cache["expires_at"] = now + timedelta(seconds=int(data.get("expires_in", 900)) - 60)
    print(f"[AUTH] Walmart token acquired (expires in {data.get('expires_in', 900)}s)")
    return _wm_token_cache["token"]


def wm_headers():
    return {
        "WM_SEC.ACCESS_TOKEN": wm_get_token(),
        "WM_SVC.NAME": "Nature's Seed",
        "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def wm_api_get(path, params=None):
    """Make a GET request to Walmart API with auto token refresh."""
    url = f"{WM_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, method="GET")
    for k, v in wm_headers().items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  [API ERROR] {e.code} on {path}: {body[:300]}")
        return None


# ══════════════════════════════════════════════════════════════
# 1. PULL ALL ITEMS/LISTINGS
# ══════════════════════════════════════════════════════════════

def pull_all_items():
    """Fetch all Walmart items with pagination."""
    print("\n" + "=" * 60)
    print("  STEP 1: Pulling all Walmart listings")
    print("=" * 60)

    all_items = []
    offset = 0
    limit = 50
    total = None

    while True:
        data = wm_api_get("/items", {"limit": limit, "offset": offset})
        if not data:
            break

        total_items = data.get("totalItems", 0)
        if total is None:
            total = total_items
            print(f"  Walmart reports {total} total items")

        items = data.get("ItemResponse", [])
        if not items:
            break

        all_items.extend(items)
        print(f"  Fetched {len(all_items)}/{total} items...")

        if len(all_items) >= total or len(items) < limit:
            break

        offset += limit
        time.sleep(0.5)

    print(f"  Total items retrieved: {len(all_items)}")
    return all_items


# ══════════════════════════════════════════════════════════════
# 2. PULL ORDERS (LAST 30 DAYS)
# ══════════════════════════════════════════════════════════════

def pull_orders_30d():
    """Fetch all Walmart orders from the last 30 days."""
    print("\n" + "=" * 60)
    print("  STEP 2: Pulling Walmart orders (last 30 days)")
    print("=" * 60)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    start_str = start_date.strftime("%Y-%m-%dT00:00:00.000Z")
    end_str = end_date.strftime("%Y-%m-%dT23:59:59.999Z")

    print(f"  Date range: {start_str[:10]} to {end_str[:10]}")

    all_orders = []
    next_cursor = None

    while True:
        params = {
            "createdStartDate": start_str,
            "createdEndDate": end_str,
            "limit": 200,
        }
        if next_cursor:
            params["nextCursor"] = next_cursor

        data = wm_api_get("/orders", params)
        if not data:
            break

        elements = data.get("list", {}).get("elements", {}).get("order", [])
        if not elements:
            break

        all_orders.extend(elements)
        print(f"  Fetched {len(all_orders)} orders so far...")

        meta = data.get("list", {}).get("meta", {})
        next_cursor = meta.get("nextCursor")
        if not next_cursor:
            break
        time.sleep(0.5)

    print(f"  Total orders retrieved: {len(all_orders)}")
    return all_orders


# ══════════════════════════════════════════════════════════════
# 3. PULL INVENTORY FOR EACH ITEM
# ══════════════════════════════════════════════════════════════

def pull_inventory_for_items(items):
    """Check inventory levels for all items."""
    print("\n" + "=" * 60)
    print("  STEP 3: Checking inventory levels")
    print("=" * 60)

    inventory_data = {}
    total = len(items)

    for i, item in enumerate(items):
        sku = item.get("sku", "")
        if not sku:
            continue

        data = wm_api_get("/inventory", {"sku": sku})
        if data:
            qty = data.get("quantity", {}).get("amount", 0)
            inventory_data[sku] = {
                "quantity": int(qty) if qty else 0,
                "product_name": item.get("productName", "Unknown"),
                "price": item.get("price", {}).get("amount", 0),
                "published_status": item.get("publishedStatus", "UNKNOWN"),
                "lifecycle_status": item.get("lifecycleStatus", "UNKNOWN"),
            }

        if (i + 1) % 20 == 0:
            print(f"  Checked {i + 1}/{total} SKUs...")
        time.sleep(0.3)  # Rate limit

    print(f"  Inventory checked for {len(inventory_data)} SKUs")
    return inventory_data


# ══════════════════════════════════════════════════════════════
# 4. PULL WOOCOMMERCE PRICES (Store API — no auth needed)
# ══════════════════════════════════════════════════════════════

def _wc_store_get(path, timeout=30):
    """Make a GET request to WC Store API (public, no auth)."""
    url = f"https://naturesseed.com/wp-json/wc/store/v1{path}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "NaturesSeed-MarketplaceAnalysis/1.0")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  [WC API ERROR] {e.code} on {path}")
        return None
    except Exception as e:
        print(f"  [WC ERROR] {e}")
        return None


def pull_wc_prices(walmart_skus=None):
    """Pull WooCommerce product prices via Store API (public, no auth).

    Fetches all products, then fetches variation-level SKUs/prices for
    variable products whose base SKU matches any Walmart base SKU pattern.
    """
    print("\n" + "=" * 60)
    print("  STEP 4: Pulling WooCommerce prices for comparison")
    print("=" * 60)

    all_products = []
    page = 1

    while True:
        products = _wc_store_get(f"/products?per_page=100&page={page}")
        if not products:
            break

        all_products.extend(products)
        print(f"  Fetched {len(all_products)} WC products (page {page})...")

        if len(products) < 100:
            break

        page += 1
        time.sleep(0.3)

    # Build set of Walmart base SKUs for matching
    wm_base_skus = set()
    if walmart_skus:
        import re
        for sku in walmart_skus:
            s = sku.upper().strip()
            s = re.sub(r"-KIT$", "", s)
            s = re.sub(r"-[\d.]+-(?:LB|OZ|LBS)$", "", s)
            wm_base_skus.add(s)

    # Build SKU -> price map
    wc_prices = {}

    # First pass: simple products + base SKUs of variable products
    variable_products = []
    for p in all_products:
        sku = p.get("sku", "")
        if not sku:
            continue

        price_str = p.get("prices", {}).get("price", "0")
        try:
            price = float(price_str) / 100
        except (ValueError, TypeError):
            price = 0

        wc_prices[sku] = {
            "price": price,
            "name": p.get("name", ""),
            "stock_status": p.get("is_in_stock", None),
        }

        # Track variable products that match Walmart base SKUs
        if p.get("has_options") and p.get("variations"):
            base = sku.upper().strip()
            if not wm_base_skus or base in wm_base_skus:
                variable_products.append(p)

    print(f"  Base products with SKUs: {len(wc_prices)}")
    print(f"  Variable products to expand: {len(variable_products)}")

    # Second pass: fetch variation-level prices for matching products
    variation_count = 0
    for product in variable_products:
        variations = product.get("variations", [])
        for v in variations:
            vid = v.get("id")
            if not vid:
                continue

            vdata = _wc_store_get(f"/products/{vid}", timeout=15)
            if vdata:
                vsku = vdata.get("sku", "")
                if vsku:
                    vprice_str = vdata.get("prices", {}).get("price", "0")
                    try:
                        vprice = float(vprice_str) / 100
                    except (ValueError, TypeError):
                        vprice = 0
                    wc_prices[vsku] = {
                        "price": vprice,
                        "name": vdata.get("name", product.get("name", "")),
                        "stock_status": vdata.get("is_in_stock", None),
                    }
                    variation_count += 1

            time.sleep(0.15)  # Rate limit

        if variation_count % 30 == 0 and variation_count > 0:
            print(f"  Fetched {variation_count} variations...")

    print(f"  Total WC SKUs (incl. variations): {len(wc_prices)} ({variation_count} variations expanded)")
    return wc_prices


# ══════════════════════════════════════════════════════════════
# 5. PULL RETURNS DATA
# ══════════════════════════════════════════════════════════════

def pull_returns():
    """Fetch recent Walmart returns."""
    print("\n" + "=" * 60)
    print("  STEP 5: Pulling returns data")
    print("=" * 60)

    data = wm_api_get("/returns", {"limit": 200})
    if not data:
        print("  No returns data available (or endpoint returned error)")
        return []

    returns = data.get("returnOrders", [])
    if not returns:
        returns = data.get("returns", [])

    print(f"  Returns retrieved: {len(returns)}")
    return returns


# ══════════════════════════════════════════════════════════════
# CACHED DATA LOADING (when API credentials unavailable)
# ══════════════════════════════════════════════════════════════

def load_items_from_cache():
    """Load item data from cached inventory_sync_report.csv."""
    print("\n" + "=" * 60)
    print("  LOADING CACHED DATA (inventory_sync_report.csv)")
    print("=" * 60)

    if not CACHED_REPORT.exists():
        print(f"  [ERROR] Cached report not found: {CACHED_REPORT}")
        return []

    import csv
    items = []
    with open(CACHED_REPORT) as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append({
                "sku": row["sku"],
                "productName": row["product_name"],
                "publishedStatus": row["published_status"],
                "lifecycleStatus": "ACTIVE",  # Assume active if in the report
                "price": {"amount": 0},  # Will be enriched from WC prices
                "shortDescription": "",
                # Inventory data from cache
                "_fishbowl_qty": int(row["fishbowl_qty"]),
                "_match_type": row["match_type"],
                "_current_availability": row["current_availability"],
            })

    print(f"  Loaded {len(items)} items from cached report")
    return items


def build_inventory_from_cache(items):
    """Build inventory data dict from cached items."""
    inventory = {}
    for item in items:
        sku = item.get("sku", "")
        if not sku:
            continue
        inventory[sku] = {
            "quantity": item.get("_fishbowl_qty", 0),
            "product_name": item.get("productName", "Unknown"),
            "price": float(item.get("price", {}).get("amount", 0) or 0),
            "published_status": item.get("publishedStatus", "UNKNOWN"),
            "lifecycle_status": item.get("lifecycleStatus", "UNKNOWN"),
        }
    return inventory


# ══════════════════════════════════════════════════════════════
# ANALYSIS ENGINE
# ══════════════════════════════════════════════════════════════

def analyze_listings(items):
    """Analyze listing health."""
    results = {
        "total_items": len(items),
        "published": 0,
        "unpublished": 0,
        "retired": 0,
        "active": 0,
        "stage": 0,
        "missing_content": [],
        "lifecycle_breakdown": defaultdict(int),
        "publish_breakdown": defaultdict(int),
    }

    for item in items:
        pub = item.get("publishedStatus", "UNKNOWN")
        lifecycle = item.get("lifecycleStatus", "UNKNOWN")

        results["publish_breakdown"][pub] += 1
        results["lifecycle_breakdown"][lifecycle] += 1

        if pub == "PUBLISHED":
            results["published"] += 1
        else:
            results["unpublished"] += 1

        if lifecycle == "ACTIVE":
            results["active"] += 1
        elif lifecycle == "RETIRED":
            results["retired"] += 1

        # Check for missing content (only flag issues we can actually detect)
        name = item.get("productName", "")
        sku = item.get("sku", "")
        price = item.get("price", {}).get("amount", 0)

        issues = []
        if not name or len(name) < 10:
            issues.append("short/missing title")
        if not price or float(price) <= 0:
            issues.append("missing/zero price")
        # Only check shortDescription if the field was actually populated from API
        # (cached data won't have this field, so skip to avoid false positives)
        if "shortDescription" in item and item.get("shortDescription", "") == "":
            issues.append("missing short description")

        # Flag SYSTEM_PROBLEM items
        if pub == "SYSTEM_PROBLEM":
            issues.append("SYSTEM_PROBLEM status (Walmart flagged)")

        if issues:
            results["missing_content"].append({
                "sku": sku,
                "name": name[:60],
                "issues": issues,
            })

    return results


def analyze_orders(orders):
    """Analyze order performance over 30 days."""
    results = {
        "total_orders": len(orders),
        "total_revenue": 0,
        "total_units": 0,
        "cancelled_orders": 0,
        "shipped_orders": 0,
        "daily_revenue": defaultdict(float),
        "daily_orders": defaultdict(int),
        "top_skus": defaultdict(lambda: {"units": 0, "revenue": 0, "name": ""}),
        "status_breakdown": defaultdict(int),
    }

    for order in orders:
        order_status = order.get("orderStatus", "UNKNOWN")
        results["status_breakdown"][order_status] += 1

        if order_status == "Cancelled":
            results["cancelled_orders"] += 1

        if order_status == "Shipped":
            results["shipped_orders"] += 1

        # Extract date from orderDate
        order_date_str = order.get("orderDate", "")
        if order_date_str:
            try:
                order_date = order_date_str[:10]
            except Exception:
                order_date = "unknown"
        else:
            order_date = "unknown"

        for line in order.get("orderLines", {}).get("orderLine", []):
            sku = line.get("item", {}).get("sku", "unknown")
            name = line.get("item", {}).get("productName", "")
            qty = int(line.get("orderLineQuantity", {}).get("amount", 0))

            charges = line.get("charges", {}).get("charge", [])
            line_revenue = 0
            for charge in charges:
                if charge.get("chargeType") == "PRODUCT":
                    amount = charge.get("chargeAmount", {})
                    line_revenue += float(amount.get("amount", 0))

            results["total_revenue"] += line_revenue
            results["total_units"] += qty
            results["daily_revenue"][order_date] += line_revenue
            results["daily_orders"][order_date] += 1

            results["top_skus"][sku]["units"] += qty
            results["top_skus"][sku]["revenue"] += line_revenue
            if name:
                results["top_skus"][sku]["name"] = name[:60]

    # Calculate averages
    if results["total_orders"] > 0:
        results["avg_order_value"] = results["total_revenue"] / results["total_orders"]
    else:
        results["avg_order_value"] = 0

    # Sort top SKUs by revenue
    results["top_skus_sorted"] = sorted(
        results["top_skus"].items(),
        key=lambda x: x[1]["revenue"],
        reverse=True,
    )

    return results


def analyze_inventory(inventory_data):
    """Analyze inventory gaps."""
    results = {
        "total_checked": len(inventory_data),
        "out_of_stock": [],
        "low_stock": [],
        "healthy_stock": [],
    }

    for sku, info in inventory_data.items():
        qty = info["quantity"]
        entry = {
            "sku": sku,
            "quantity": qty,
            "name": info["product_name"][:60],
            "price": float(info.get("price", 0) or 0),
            "published": info.get("published_status", ""),
        }

        if qty == 0:
            results["out_of_stock"].append(entry)
        elif qty < 5:
            results["low_stock"].append(entry)
        else:
            results["healthy_stock"].append(entry)

    # Sort OOS by price (highest value items = most lost revenue)
    results["out_of_stock"].sort(key=lambda x: x["price"], reverse=True)
    results["low_stock"].sort(key=lambda x: x["quantity"])

    return results


def analyze_price_discrepancies(inventory_data, wc_prices, has_walmart_prices=True):
    """Compare Walmart vs WooCommerce prices.

    When has_walmart_prices=False (cached mode), Walmart prices were enriched from WC
    so there's no meaningful comparison. Instead, report the WC price coverage.
    """
    discrepancies = []
    matched = 0
    unmatched_wm = 0
    wc_only_prices = []

    for sku, wm_info in inventory_data.items():
        wm_price = float(wm_info.get("price", 0) or 0)
        if sku in wc_prices:
            wc_price = wc_prices[sku]["price"]
            matched += 1

            if has_walmart_prices and wm_price > 0 and wc_price > 0:
                diff = wm_price - wc_price
                pct_diff = (diff / wc_price) * 100 if wc_price > 0 else 0

                if abs(pct_diff) > 1:  # More than 1% difference
                    discrepancies.append({
                        "sku": sku,
                        "name": wm_info["product_name"][:50],
                        "walmart_price": wm_price,
                        "wc_price": wc_price,
                        "difference": round(diff, 2),
                        "pct_diff": round(pct_diff, 1),
                    })

            # In cached mode, track WC prices for reference
            if not has_walmart_prices and wc_price > 0:
                wc_only_prices.append({
                    "sku": sku,
                    "name": wm_info["product_name"][:50],
                    "wc_price": wc_price,
                })
        else:
            unmatched_wm += 1

    # Sort by absolute difference
    discrepancies.sort(key=lambda x: abs(x["difference"]), reverse=True)

    return {
        "matched_skus": matched,
        "unmatched_walmart_skus": unmatched_wm,
        "discrepancies": discrepancies,
        "total_wc_products": len(wc_prices),
        "has_walmart_prices": has_walmart_prices,
        "wc_only_prices": wc_only_prices,
    }


def estimate_lost_revenue(order_analysis, inventory_analysis):
    """Estimate revenue lost from OOS items based on order velocity or price estimates.

    When order data is available, uses actual sales velocity.
    When only price data is available (cached mode), estimates based on
    conservative sell-through assumptions:
    - Published items with price > $100: 0.15 units/day
    - Published items with price $50-$100: 0.2 units/day
    - Published items with price < $50: 0.3 units/day
    """
    total_days = 30
    has_order_data = order_analysis["total_orders"] > 0

    # Build velocity map from orders if available
    sku_velocity = {}
    if has_order_data:
        for sku, info in order_analysis["top_skus"].items():
            daily_units = info["units"] / total_days
            daily_rev = info["revenue"] / total_days
            sku_velocity[sku] = {"daily_units": daily_units, "daily_revenue": daily_rev}

    oos_with_history = []
    total_daily_loss = 0

    for oos_item in inventory_analysis["out_of_stock"]:
        sku = oos_item["sku"]
        price = oos_item["price"]

        if sku in sku_velocity:
            # Use actual velocity
            daily_loss = sku_velocity[sku]["daily_revenue"]
            total_daily_loss += daily_loss
            oos_with_history.append({
                "sku": sku,
                "name": oos_item["name"],
                "price": price,
                "est_daily_loss": round(daily_loss, 2),
                "est_monthly_loss": round(daily_loss * 30, 2),
            })
        elif oos_item.get("published") == "PUBLISHED" and price > 0:
            # Estimate from price with conservative velocity assumptions
            if price >= 100:
                daily_units = 0.15
            elif price >= 50:
                daily_units = 0.2
            else:
                daily_units = 0.3

            est_daily = price * daily_units
            total_daily_loss += est_daily
            oos_with_history.append({
                "sku": sku,
                "name": oos_item["name"],
                "price": price,
                "est_daily_loss": round(est_daily, 2),
                "est_monthly_loss": round(est_daily * 30, 2),
                "note": f"estimated ({daily_units} units/day assumption)",
            })

    oos_with_history.sort(key=lambda x: x["est_monthly_loss"], reverse=True)

    return {
        "estimated_daily_loss": round(total_daily_loss, 2),
        "estimated_monthly_loss": round(total_daily_loss * 30, 2),
        "oos_items": oos_with_history,
        "estimation_method": "order velocity" if has_order_data else "price-based estimate (no order data)",
    }


def calculate_health_score(listing_analysis, order_analysis, inventory_analysis, price_analysis, live_api=True):
    """Calculate a 0-100 Walmart channel health score.

    When live_api=False, excludes order-based scoring (since we don't have order data)
    and adjusts the weight distribution accordingly.
    """
    score = 100
    reasons = []

    # Listing health (30 points max)
    if listing_analysis["total_items"] > 0:
        publish_rate = listing_analysis["published"] / listing_analysis["total_items"]
        listing_score = publish_rate * 30
        score_deduction = 30 - listing_score
        if score_deduction > 0:
            score -= score_deduction
            reasons.append(f"-{score_deduction:.0f} pts: {listing_analysis['unpublished']} unpublished listings ({listing_analysis['unpublished']} of {listing_analysis['total_items']} not visible to shoppers)")
    else:
        score -= 30
        reasons.append("-30 pts: no items found")

    # Content quality (10 points)
    if listing_analysis["missing_content"]:
        content_penalty = min(10, len(listing_analysis["missing_content"]) * 0.5)
        score -= content_penalty
        reasons.append(f"-{content_penalty:.0f} pts: {len(listing_analysis['missing_content'])} items with content issues")

    # Inventory health (30 points if no order data, 25 otherwise -- re-weighted)
    inv_max = 30 if not live_api else 25
    if inventory_analysis["total_checked"] > 0:
        oos_rate = len(inventory_analysis["out_of_stock"]) / inventory_analysis["total_checked"]
        inv_penalty = min(inv_max, oos_rate * 100)
        if inv_penalty > 0:
            score -= inv_penalty
            reasons.append(f"-{inv_penalty:.0f} pts: {len(inventory_analysis['out_of_stock'])} out-of-stock items ({oos_rate*100:.0f}% of catalog)")

    # Low stock warning (5 points)
    if inventory_analysis["low_stock"]:
        low_penalty = min(5, len(inventory_analysis["low_stock"]) * 0.5)
        score -= low_penalty
        reasons.append(f"-{low_penalty:.0f} pts: {len(inventory_analysis['low_stock'])} low-stock items (<5 units)")

    # Price consistency (15 points)
    if price_analysis["discrepancies"]:
        price_penalty = min(15, len(price_analysis["discrepancies"]) * 0.5)
        score -= price_penalty
        reasons.append(f"-{price_penalty:.0f} pts: {len(price_analysis['discrepancies'])} price discrepancies vs WooCommerce")

    # Order volume health (15 points — only scored with live API data)
    if live_api:
        if order_analysis["total_orders"] == 0:
            score -= 15
            reasons.append("-15 pts: zero orders in 30 days")
        elif order_analysis["total_orders"] < 10:
            score -= 10
            reasons.append(f"-10 pts: only {order_analysis['total_orders']} orders in 30 days")
    else:
        reasons.append("(order volume not scored — no API access)")

    return max(0, min(100, round(score))), reasons


# ══════════════════════════════════════════════════════════════
# REPORT GENERATION
# ══════════════════════════════════════════════════════════════

def generate_report(listing_analysis, order_analysis, inventory_analysis,
                    price_analysis, lost_revenue, health_score, health_reasons,
                    returns_data):
    """Generate the markdown findings report."""
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append(f"# Walmart Marketplace Analysis — Nature's Seed")
    lines.append(f"")
    lines.append(f"**Generated:** {report_date}")
    lines.append(f"**Analysis Period:** Last 30 days (orders)")
    lines.append(f"")

    # ── Health Score ──
    if health_score >= 80:
        grade = "A"
    elif health_score >= 60:
        grade = "B"
    elif health_score >= 40:
        grade = "C"
    elif health_score >= 20:
        grade = "D"
    else:
        grade = "F"

    lines.append(f"## Channel Health Score: {health_score}/100 (Grade: {grade})")
    lines.append(f"")
    for reason in health_reasons:
        lines.append(f"- {reason}")
    lines.append(f"")

    # ── Revenue Summary ──
    lines.append(f"## Revenue Summary (Last 30 Days)")
    lines.append(f"")
    if order_analysis['total_orders'] > 0:
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Orders | {order_analysis['total_orders']} |")
        lines.append(f"| Total Revenue | ${order_analysis['total_revenue']:,.2f} |")
        lines.append(f"| Total Units Sold | {order_analysis['total_units']} |")
        lines.append(f"| Avg Order Value | ${order_analysis['avg_order_value']:,.2f} |")
        lines.append(f"| Shipped Orders | {order_analysis['shipped_orders']} |")
        lines.append(f"| Cancelled Orders | {order_analysis['cancelled_orders']} |")
        cancel_rate = (order_analysis['cancelled_orders'] / order_analysis['total_orders']) * 100
        lines.append(f"| Cancellation Rate | {cancel_rate:.1f}% |")
    else:
        lines.append(f"*Order data not available. Run with Walmart API credentials (WALMART_CLIENT_ID, WALMART_CLIENT_SECRET) to pull live order data.*")
        lines.append(f"*Supabase `daily_sales` table contains historical Walmart order data if credentials are configured.*")
    lines.append(f"")

    # ── Order Status Breakdown ──
    if order_analysis["status_breakdown"]:
        lines.append(f"### Order Status Breakdown")
        lines.append(f"")
        lines.append(f"| Status | Count |")
        lines.append(f"|--------|-------|")
        for status, count in sorted(order_analysis["status_breakdown"].items(), key=lambda x: -x[1]):
            lines.append(f"| {status} | {count} |")
        lines.append(f"")

    # ── Top Selling Products ──
    if order_analysis["top_skus_sorted"]:
        lines.append(f"### Top 15 Products by Revenue")
        lines.append(f"")
        lines.append(f"| Rank | SKU | Product | Units | Revenue |")
        lines.append(f"|------|-----|---------|-------|---------|")
        for i, (sku, info) in enumerate(order_analysis["top_skus_sorted"][:15], 1):
            lines.append(f"| {i} | `{sku}` | {info['name'][:40]} | {info['units']} | ${info['revenue']:,.2f} |")
        lines.append(f"")

    # ── Revenue Lost from OOS ──
    lines.append(f"## Revenue Lost from Out-of-Stock Items")
    lines.append(f"")
    est_method = lost_revenue.get("estimation_method", "unknown")
    lines.append(f"*Estimation method: {est_method}*")
    lines.append(f"")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Estimated Daily Loss | ${lost_revenue['estimated_daily_loss']:,.2f} |")
    lines.append(f"| **Estimated Monthly Loss** | **${lost_revenue['estimated_monthly_loss']:,.2f}** |")
    lines.append(f"| OOS Items with Sales History | {len([x for x in lost_revenue['oos_items'] if 'note' not in x])} |")
    lines.append(f"| OOS Items (estimated) | {len([x for x in lost_revenue['oos_items'] if 'note' in x])} |")
    lines.append(f"")

    if lost_revenue["oos_items"]:
        lines.append(f"### Top OOS Items by Estimated Lost Revenue")
        lines.append(f"")
        lines.append(f"| SKU | Product | Price | Est. Monthly Loss | Notes |")
        lines.append(f"|-----|---------|-------|-------------------|-------|")
        for item in lost_revenue["oos_items"][:20]:
            note = item.get("note", "based on order history")
            lines.append(f"| `{item['sku']}` | {item['name'][:35]} | ${item['price']:,.2f} | ${item['est_monthly_loss']:,.2f} | {note} |")
        lines.append(f"")

    # ── Listing Quality ──
    lines.append(f"## Listing Quality Issues")
    lines.append(f"")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Listings | {listing_analysis['total_items']} |")
    lines.append(f"| Published | {listing_analysis['published']} |")
    lines.append(f"| Unpublished | {listing_analysis['unpublished']} |")
    lines.append(f"| Items with Content Issues | {len(listing_analysis['missing_content'])} |")
    lines.append(f"")

    # Lifecycle breakdown
    if listing_analysis["lifecycle_breakdown"]:
        lines.append(f"### Lifecycle Status Breakdown")
        lines.append(f"")
        lines.append(f"| Status | Count |")
        lines.append(f"|--------|-------|")
        for status, count in sorted(listing_analysis["lifecycle_breakdown"].items(), key=lambda x: -x[1]):
            lines.append(f"| {status} | {count} |")
        lines.append(f"")

    # Published status breakdown
    if listing_analysis["publish_breakdown"]:
        lines.append(f"### Publish Status Breakdown")
        lines.append(f"")
        lines.append(f"| Status | Count |")
        lines.append(f"|--------|-------|")
        for status, count in sorted(listing_analysis["publish_breakdown"].items(), key=lambda x: -x[1]):
            lines.append(f"| {status} | {count} |")
        lines.append(f"")

    if listing_analysis["missing_content"]:
        lines.append(f"### Items with Missing Content (first 20)")
        lines.append(f"")
        lines.append(f"| SKU | Product | Issues |")
        lines.append(f"|-----|---------|--------|")
        for item in listing_analysis["missing_content"][:20]:
            lines.append(f"| `{item['sku']}` | {item['name']} | {', '.join(item['issues'])} |")
        lines.append(f"")

    # ── Pricing Discrepancies ──
    lines.append(f"## Pricing Analysis (Walmart vs WooCommerce)")
    lines.append(f"")

    if price_analysis.get("has_walmart_prices"):
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| SKUs Matched Across Platforms | {price_analysis['matched_skus']} |")
        lines.append(f"| Walmart-Only SKUs (no WC match) | {price_analysis['unmatched_walmart_skus']} |")
        lines.append(f"| Price Discrepancies (>1%) | {len(price_analysis['discrepancies'])} |")
        lines.append(f"")

        if price_analysis["discrepancies"]:
            lines.append(f"### Price Differences (sorted by absolute difference)")
            lines.append(f"")
            lines.append(f"| SKU | Product | Walmart | WooCommerce | Diff | % Diff |")
            lines.append(f"|-----|---------|---------|-------------|------|--------|")
            for d in price_analysis["discrepancies"][:30]:
                direction = "higher" if d["difference"] > 0 else "lower"
                lines.append(f"| `{d['sku']}` | {d['name'][:30]} | ${d['walmart_price']:,.2f} | ${d['wc_price']:,.2f} | ${d['difference']:+,.2f} | {d['pct_diff']:+.1f}% ({direction}) |")
            lines.append(f"")
    else:
        lines.append(f"*Note: Walmart API prices not available in cached mode. Price discrepancy analysis requires live API credentials.*")
        lines.append(f"*Run with WALMART_CLIENT_ID and WALMART_CLIENT_SECRET to compare prices across channels.*")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Walmart SKUs matched to WC catalog | {price_analysis['matched_skus']} |")
        lines.append(f"| Walmart SKUs NOT in WC catalog | {price_analysis['unmatched_walmart_skus']} |")
        lines.append(f"| Total WC products | {price_analysis['total_wc_products']} |")
        lines.append(f"")

    # ── Inventory Management Gaps ──
    lines.append(f"## Inventory Management Gaps")
    lines.append(f"")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total SKUs Checked | {inventory_analysis['total_checked']} |")
    lines.append(f"| Out of Stock (0 units) | {len(inventory_analysis['out_of_stock'])} |")
    lines.append(f"| Low Stock (<5 units) | {len(inventory_analysis['low_stock'])} |")
    lines.append(f"| Healthy Stock (5+ units) | {len(inventory_analysis['healthy_stock'])} |")
    lines.append(f"")

    if inventory_analysis["out_of_stock"]:
        lines.append(f"### Out-of-Stock Items (sorted by price — highest value first)")
        lines.append(f"")
        lines.append(f"| SKU | Product | Price | Published |")
        lines.append(f"|-----|---------|-------|-----------|")
        for item in inventory_analysis["out_of_stock"][:25]:
            lines.append(f"| `{item['sku']}` | {item['name'][:40]} | ${item['price']:,.2f} | {item['published']} |")
        if len(inventory_analysis["out_of_stock"]) > 25:
            lines.append(f"| ... | *{len(inventory_analysis['out_of_stock']) - 25} more items* | | |")
        lines.append(f"")

    if inventory_analysis["low_stock"]:
        lines.append(f"### Low Stock Items (<5 units)")
        lines.append(f"")
        lines.append(f"| SKU | Product | Qty | Price |")
        lines.append(f"|-----|---------|-----|-------|")
        for item in inventory_analysis["low_stock"][:20]:
            lines.append(f"| `{item['sku']}` | {item['name'][:40]} | {item['quantity']} | ${item['price']:,.2f} |")
        lines.append(f"")

    # ── Optimization Opportunities ──
    lines.append(f"## Walmart-Specific Optimization Opportunities")
    lines.append(f"")

    opp_num = 1

    # Opportunity: Restock OOS
    if inventory_analysis["out_of_stock"]:
        oos_published = [x for x in inventory_analysis["out_of_stock"] if x["published"] == "PUBLISHED"]
        if oos_published:
            total_oos_value = sum(x["price"] for x in oos_published)
            lines.append(f"### {opp_num}. Restock {len(oos_published)} Published Out-of-Stock Items")
            lines.append(f"**Impact: HIGH** — These items are visible to shoppers but cannot be purchased.")
            lines.append(f"Combined catalog value of OOS published items: ${total_oos_value:,.2f}")
            lines.append(f"")
            opp_num += 1

    # Opportunity: Publish unpublished items
    if listing_analysis["unpublished"] > 0:
        lines.append(f"### {opp_num}. Publish {listing_analysis['unpublished']} Unpublished Listings")
        lines.append(f"**Impact: MEDIUM** — These items exist in your Walmart catalog but are not visible to shoppers.")
        lines.append(f"Review and publish items that are ready for sale.")
        lines.append(f"")
        opp_num += 1

    # Opportunity: Fix price discrepancies
    if price_analysis["discrepancies"]:
        walmart_higher = [d for d in price_analysis["discrepancies"] if d["difference"] > 0]
        walmart_lower = [d for d in price_analysis["discrepancies"] if d["difference"] < 0]
        lines.append(f"### {opp_num}. Resolve {len(price_analysis['discrepancies'])} Price Discrepancies")
        lines.append(f"**Impact: MEDIUM** — Inconsistent pricing across channels hurts customer trust and may violate MAP agreements.")
        if walmart_higher:
            lines.append(f"- {len(walmart_higher)} items priced HIGHER on Walmart (may reduce conversions)")
        if walmart_lower:
            lines.append(f"- {len(walmart_lower)} items priced LOWER on Walmart (margin leakage)")
        lines.append(f"")
        opp_num += 1

    # Opportunity: Automate inventory sync
    lines.append(f"### {opp_num}. Automate Inventory Sync (Fishbowl -> Walmart)")
    lines.append(f"**Impact: HIGH** — Currently manual. Automated sync would prevent stockouts and lost sales.")
    lines.append(f"Use the existing `walmart_client.py` to build a cron job that syncs Fishbowl inventory to Walmart via the `/v3/inventory` PUT endpoint or bulk feed.")
    lines.append(f"")
    opp_num += 1

    # Opportunity: Automate price sync
    lines.append(f"### {opp_num}. Automate Price Sync (WooCommerce -> Walmart)")
    lines.append(f"**Impact: MEDIUM** — Manual price updates lead to discrepancies. Use `/v3/prices` PUT endpoint for real-time sync.")
    lines.append(f"")
    opp_num += 1

    # Opportunity: Content optimization
    if listing_analysis["missing_content"]:
        lines.append(f"### {opp_num}. Fix Content Issues on {len(listing_analysis['missing_content'])} Listings")
        lines.append(f"**Impact: LOW-MEDIUM** — Missing descriptions reduce conversion rate and Walmart search ranking.")
        lines.append(f"")
        opp_num += 1

    # ── Estimated Revenue Opportunity ──
    lines.append(f"## Estimated Revenue Opportunity from Fixing Issues")
    lines.append(f"")

    monthly_oos_recovery = lost_revenue["estimated_monthly_loss"]
    # Estimate from publishing unpublished items (conservative: 10% of avg published item revenue)
    avg_monthly_rev_per_item = 0
    if listing_analysis["published"] > 0 and order_analysis["total_revenue"] > 0:
        avg_monthly_rev_per_item = order_analysis["total_revenue"] / listing_analysis["published"]
    unpublished_opportunity = listing_analysis["unpublished"] * avg_monthly_rev_per_item * 0.1

    # Price optimization (bringing Walmart-lower items up)
    price_margin_recovery = 0
    for d in price_analysis["discrepancies"]:
        if d["difference"] < 0:  # Walmart is lower
            price_margin_recovery += abs(d["difference"]) * 0.5  # Assume 50% sell-through

    total_monthly_opportunity = monthly_oos_recovery + unpublished_opportunity + price_margin_recovery

    lines.append(f"| Opportunity | Est. Monthly Revenue |")
    lines.append(f"|------------|---------------------|")
    lines.append(f"| Restock OOS items | ${monthly_oos_recovery:,.2f} |")
    lines.append(f"| Publish unpublished items | ${unpublished_opportunity:,.2f} |")
    lines.append(f"| Fix underpriced items (margin recovery) | ${price_margin_recovery:,.2f} |")
    lines.append(f"| **Total Monthly Opportunity** | **${total_monthly_opportunity:,.2f}** |")
    lines.append(f"| **Total Annual Opportunity** | **${total_monthly_opportunity * 12:,.2f}** |")
    lines.append(f"")

    # ── Daily Revenue Trend ──
    if order_analysis["daily_revenue"]:
        lines.append(f"## Daily Revenue Trend (Last 30 Days)")
        lines.append(f"")
        lines.append(f"| Date | Orders | Revenue |")
        lines.append(f"|------|--------|---------|")
        for d in sorted(order_analysis["daily_revenue"].keys()):
            rev = order_analysis["daily_revenue"][d]
            ords = order_analysis["daily_orders"][d]
            lines.append(f"| {d} | {ords} | ${rev:,.2f} |")
        lines.append(f"")

    # ── Returns Analysis ──
    if returns_data:
        lines.append(f"## Returns/Refunds")
        lines.append(f"")
        lines.append(f"Total returns found: {len(returns_data)}")
        if order_analysis["total_orders"] > 0:
            return_rate = (len(returns_data) / order_analysis["total_orders"]) * 100
            lines.append(f"Return rate: {return_rate:.1f}%")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"*Report generated by marketplace_walmart.py*")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  WALMART MARKETPLACE FUNNEL ANALYSIS")
    print("  Nature's Seed")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Mode: {'LIVE API' if LIVE_API else 'CACHED DATA + WC Store API'}")
    print("=" * 60)

    if LIVE_API:
        # Live API mode
        items = pull_all_items()
        orders = pull_orders_30d()
        inventory_data = pull_inventory_for_items(items)
        returns_data = pull_returns()
    else:
        # Cached data mode
        items = load_items_from_cache()
        orders = []  # No order data available without API
        inventory_data = build_inventory_from_cache(items)
        returns_data = []

    # Always try WooCommerce Store API (public, no auth)
    # Pass Walmart SKUs so we can expand matching variable products
    walmart_skus = [item.get("sku", "") for item in items if item.get("sku")]
    wc_prices = pull_wc_prices(walmart_skus=walmart_skus)

    # Enrich cached item prices from WC data where SKUs match
    if not LIVE_API and wc_prices:
        enriched = 0
        for item in items:
            sku = item.get("sku", "")
            if sku in wc_prices:
                item["price"] = {"amount": wc_prices[sku]["price"]}
                if sku in inventory_data:
                    inventory_data[sku]["price"] = wc_prices[sku]["price"]
                enriched += 1
        print(f"  Enriched {enriched} items with WC prices")

    # ── Run Analysis ──
    print("\n" + "=" * 60)
    print("  RUNNING ANALYSIS")
    print("=" * 60)

    listing_analysis = analyze_listings(items)
    print(f"  Listings: {listing_analysis['published']} published, {listing_analysis['unpublished']} unpublished")

    order_analysis = analyze_orders(orders)
    print(f"  Orders: {order_analysis['total_orders']} orders, ${order_analysis['total_revenue']:,.2f} revenue")

    inventory_analysis = analyze_inventory(inventory_data)
    print(f"  Inventory: {len(inventory_analysis['out_of_stock'])} OOS, {len(inventory_analysis['low_stock'])} low-stock")

    price_analysis = analyze_price_discrepancies(inventory_data, wc_prices, has_walmart_prices=LIVE_API)
    print(f"  Prices: {price_analysis['matched_skus']} SKUs matched to WC" + (f", {len(price_analysis['discrepancies'])} discrepancies" if LIVE_API else " (Walmart prices not available in cached mode)"))

    lost_revenue = estimate_lost_revenue(order_analysis, inventory_analysis)
    print(f"  Lost revenue (est): ${lost_revenue['estimated_monthly_loss']:,.2f}/month from OOS")

    health_score, health_reasons = calculate_health_score(
        listing_analysis, order_analysis, inventory_analysis, price_analysis, live_api=LIVE_API
    )
    print(f"\n  HEALTH SCORE: {health_score}/100")
    for r in health_reasons:
        print(f"    {r}")

    # ── Generate Report ──
    report = generate_report(
        listing_analysis, order_analysis, inventory_analysis,
        price_analysis, lost_revenue, health_score, health_reasons,
        returns_data
    )

    # Save report
    report_path = Path(__file__).resolve().parent.parent / "reports" / "marketplace_findings.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\n  Report saved to: {report_path}")
    print("=" * 60)
    print("  ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
