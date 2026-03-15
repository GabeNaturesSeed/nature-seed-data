#!/usr/bin/env python3
"""
Conversion Agent A — WooCommerce Funnel Analysis
Pulls order, product, and customer data to identify conversion leaks.

Analyzes:
  1. Order health (statuses, refunds, failures, payment methods)
  2. Product performance (top sellers, category mix, items/order)
  3. Customer behavior (new vs returning, geography)
  4. YoY comparison via Supabase historical data

Usage:
  python3 conversion_a_woocommerce.py
"""

import json
import time
import os
import base64
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import Counter, defaultdict

import requests

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
    # Fall back to os.environ
    print(f"[WARN] .env not found at {env_path}, using os.environ")
    env_vars = dict(os.environ)

# WooCommerce
WC_BASE = env_vars.get("WC_BASE_URL", "https://naturesseed.com/wp-json/wc/v3")
WC_CK = env_vars.get("WC_CK", "")
WC_CS = env_vars.get("WC_CS", "")
WC_AUTH = (WC_CK, WC_CS)

# Cloudflare Worker proxy
CF_WORKER_URL = env_vars.get("CF_WORKER_URL", "")
CF_WORKER_SECRET = env_vars.get("CF_WORKER_SECRET", "")

# Supabase
SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")

WC_HEADERS = {"User-Agent": "NaturesSeed-ConversionAgent/1.0"}

# Date range: last 30 days
END_DATE = date(2026, 3, 14)
START_DATE = date(2026, 2, 13)
# YoY comparison
YOY_END = date(2025, 3, 14)
YOY_START = date(2025, 2, 13)

# ══════════════════════════════════════════════════════════════
# WC API HELPERS
# ══════════════════════════════════════════════════════════════

def wc_request(endpoint, params=None, max_retries=3):
    """Make a WC API request with retry and optional CF Worker proxy."""
    url = f"{WC_BASE}{endpoint}"
    params = params or {}

    for attempt in range(max_retries):
        try:
            if CF_WORKER_URL and CF_WORKER_SECRET:
                proxy_params = dict(params)
                proxy_params["wc_path"] = endpoint
                auth_str = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
                headers = {
                    "X-Proxy-Secret": CF_WORKER_SECRET,
                    "Authorization": f"Basic {auth_str}",
                    "User-Agent": "NaturesSeed-ConversionAgent/1.0",
                }
                resp = requests.get(CF_WORKER_URL, params=proxy_params,
                                    headers=headers, timeout=60)
            else:
                resp = requests.get(url, auth=WC_AUTH, params=params,
                                    headers=WC_HEADERS, timeout=60)

            if resp.status_code == 200:
                return resp
            if resp.status_code in (403, 429, 500, 502, 503) and attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  [RETRY] {resp.status_code} on {endpoint}, wait {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  [RETRY] {e}, wait {wait}s")
                time.sleep(wait)
            else:
                raise
    return resp


def wc_paginate(endpoint, params=None):
    """Paginate through a WC endpoint, returning all results."""
    params = params or {}
    params["per_page"] = 100
    all_results = []
    page = 1

    while True:
        params["page"] = page
        resp = wc_request(endpoint, params)
        data = resp.json()
        if not data:
            break
        all_results.extend(data)
        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        print(f"    Page {page}/{total_pages} — {len(data)} items")
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)

    return all_results


# ══════════════════════════════════════════════════════════════
# 1. ORDER ANALYSIS
# ══════════════════════════════════════════════════════════════

def pull_all_orders():
    """Pull ALL orders (all statuses) for the analysis period."""
    print("\n═══ PULLING ORDERS ═══")
    start_iso = f"{START_DATE}T00:00:00"
    end_iso = f"{END_DATE}T23:59:59"

    statuses = ["completed", "processing", "cancelled", "refunded", "failed",
                "pending", "on-hold"]
    all_orders = []

    for status in statuses:
        print(f"\n  Status: {status}")
        params = {
            "after": start_iso,
            "before": end_iso,
            "status": status,
        }
        orders = wc_paginate("/orders", params)
        print(f"    → {len(orders)} {status} orders")
        all_orders.extend(orders)
        time.sleep(0.3)

    print(f"\n  TOTAL ORDERS: {len(all_orders)}")
    return all_orders


def analyze_orders(orders):
    """Analyze orders for conversion health metrics."""
    print("\n═══ ORDER ANALYSIS ═══")

    if not orders:
        print("  No orders found!")
        return {}

    # --- Basic metrics ---
    total_orders = len(orders)
    total_revenue = sum(float(o.get("total", 0)) for o in orders)
    aov = total_revenue / total_orders if total_orders else 0

    # --- Status breakdown ---
    status_counts = Counter(o.get("status", "unknown") for o in orders)
    status_revenue = defaultdict(float)
    for o in orders:
        status_revenue[o.get("status", "unknown")] += float(o.get("total", 0))

    # --- Good orders (completed + processing) ---
    good_statuses = {"completed", "processing"}
    good_orders = [o for o in orders if o.get("status") in good_statuses]
    good_count = len(good_orders)
    good_revenue = sum(float(o.get("total", 0)) for o in good_orders)
    good_aov = good_revenue / good_count if good_count else 0

    # --- Refunds ---
    refunded = [o for o in orders if o.get("status") == "refunded"]
    refund_count = len(refunded)
    refund_amount = sum(float(o.get("total", 0)) for o in refunded)
    refund_rate = refund_count / total_orders * 100 if total_orders else 0

    # Also check for partial refunds in completed/processing orders
    partial_refund_total = 0
    partial_refund_count = 0
    for o in good_orders:
        refund_lines = o.get("refunds", [])
        if refund_lines:
            partial_refund_count += 1
            partial_refund_total += sum(abs(float(r.get("total", 0))) for r in refund_lines)

    # --- Failed / Cancelled ---
    failed = [o for o in orders if o.get("status") == "failed"]
    cancelled = [o for o in orders if o.get("status") == "cancelled"]
    failed_count = len(failed)
    cancelled_count = len(cancelled)
    lost_revenue_failed = sum(float(o.get("total", 0)) for o in failed)
    lost_revenue_cancelled = sum(float(o.get("total", 0)) for o in cancelled)

    # --- Payment methods ---
    payment_methods = Counter()
    for o in orders:
        if o.get("status") in good_statuses:
            pm = o.get("payment_method_title", o.get("payment_method", "unknown"))
            payment_methods[pm] += 1

    # --- Coupon usage ---
    coupon_orders = 0
    total_discount = 0.0
    coupon_codes = Counter()
    for o in orders:
        if o.get("status") in good_statuses:
            coupons = o.get("coupon_lines", [])
            if coupons:
                coupon_orders += 1
                total_discount += float(o.get("discount_total", 0))
                for c in coupons:
                    coupon_codes[c.get("code", "unknown")] += 1
    coupon_rate = coupon_orders / good_count * 100 if good_count else 0

    # --- Shipping methods ---
    shipping_methods = Counter()
    shipping_costs = defaultdict(float)
    for o in good_orders:
        for sl in o.get("shipping_lines", []):
            method = sl.get("method_title", "Unknown")
            shipping_methods[method] += 1
            shipping_costs[method] += float(sl.get("total", 0))

    # --- Orders by state/region (top 10) ---
    state_orders = Counter()
    state_revenue = defaultdict(float)
    for o in good_orders:
        billing = o.get("billing", {})
        state = billing.get("state", "")
        country = billing.get("country", "US")
        if state:
            region = f"{state}, {country}" if country != "US" else state
            state_orders[region] += 1
            state_revenue[region] += float(o.get("total", 0))

    results = {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "aov": aov,
        "good_count": good_count,
        "good_revenue": good_revenue,
        "good_aov": good_aov,
        "status_counts": dict(status_counts),
        "status_revenue": dict(status_revenue),
        "refund_count": refund_count,
        "refund_amount": refund_amount,
        "refund_rate": refund_rate,
        "partial_refund_count": partial_refund_count,
        "partial_refund_total": partial_refund_total,
        "failed_count": failed_count,
        "cancelled_count": cancelled_count,
        "lost_revenue_failed": lost_revenue_failed,
        "lost_revenue_cancelled": lost_revenue_cancelled,
        "payment_methods": dict(payment_methods),
        "coupon_orders": coupon_orders,
        "coupon_rate": coupon_rate,
        "total_discount": total_discount,
        "top_coupons": dict(coupon_codes.most_common(10)),
        "shipping_methods": dict(shipping_methods),
        "shipping_costs": dict(shipping_costs),
        "top_states": dict(state_orders.most_common(10)),
        "top_state_revenue": {k: state_revenue[k] for k, _ in state_orders.most_common(10)},
    }

    # Print summary
    print(f"\n  Total Orders: {total_orders}")
    print(f"  Total Revenue: ${total_revenue:,.2f}")
    print(f"  AOV (all): ${aov:,.2f}")
    print(f"  Good Orders (completed+processing): {good_count} (${good_revenue:,.2f})")
    print(f"  Good AOV: ${good_aov:,.2f}")
    print(f"\n  Status Breakdown:")
    for s, c in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f"    {s}: {c} orders (${status_revenue[s]:,.2f})")
    print(f"\n  Refund Rate: {refund_rate:.1f}% ({refund_count} orders, ${refund_amount:,.2f})")
    print(f"  Partial Refunds: {partial_refund_count} orders, ${partial_refund_total:,.2f}")
    print(f"  Failed: {failed_count} (${lost_revenue_failed:,.2f} lost)")
    print(f"  Cancelled: {cancelled_count} (${lost_revenue_cancelled:,.2f} lost)")
    print(f"\n  Coupon Usage: {coupon_rate:.1f}% ({coupon_orders}/{good_count})")
    print(f"  Total Discounts: ${total_discount:,.2f}")
    print(f"\n  Payment Methods:")
    for pm, c in payment_methods.most_common():
        print(f"    {pm}: {c}")
    print(f"\n  Shipping Methods:")
    for sm, c in shipping_methods.most_common():
        print(f"    {sm}: {c} (${shipping_costs[sm]:,.2f})")
    print(f"\n  Top 10 States:")
    for st, c in state_orders.most_common(10):
        print(f"    {st}: {c} orders (${state_revenue[st]:,.2f})")

    return results


# ══════════════════════════════════════════════════════════════
# 2. PRODUCT ANALYSIS
# ══════════════════════════════════════════════════════════════

def analyze_products(orders):
    """Analyze product performance from order line items."""
    print("\n═══ PRODUCT ANALYSIS ═══")

    good_statuses = {"completed", "processing"}
    good_orders = [o for o in orders if o.get("status") in good_statuses]

    if not good_orders:
        print("  No good orders to analyze!")
        return {}

    # --- Product revenue and units ---
    product_revenue = defaultdict(float)
    product_units = defaultdict(int)
    product_names = {}
    product_skus = {}
    category_revenue = defaultdict(float)
    category_units = defaultdict(int)

    total_items = 0
    for o in good_orders:
        items = o.get("line_items", [])
        total_items += len(items)
        for item in items:
            pid = item.get("product_id", 0)
            name = item.get("name", "Unknown")
            sku = item.get("sku", "")
            qty = item.get("quantity", 0)
            rev = float(item.get("total", 0))

            product_revenue[pid] += rev
            product_units[pid] += qty
            product_names[pid] = name
            product_skus[pid] = sku

            # Try to extract category from meta or product data
            meta = item.get("meta_data", [])
            for m in meta:
                if m.get("key") == "_category":
                    cat = m.get("value", "Uncategorized")
                    category_revenue[cat] += rev
                    category_units[cat] += qty

    avg_items_per_order = total_items / len(good_orders) if good_orders else 0
    single_item_orders = sum(1 for o in good_orders if len(o.get("line_items", [])) == 1)
    single_item_rate = single_item_orders / len(good_orders) * 100 if good_orders else 0

    # Top 20 by revenue
    top_products = sorted(product_revenue.items(), key=lambda x: -x[1])[:20]
    top_products_data = []
    for pid, rev in top_products:
        top_products_data.append({
            "product_id": pid,
            "name": product_names.get(pid, "Unknown"),
            "sku": product_skus.get(pid, ""),
            "revenue": rev,
            "units": product_units.get(pid, 0),
        })

    # If categories weren't in meta, try to fetch them from products endpoint
    if not category_revenue:
        print("  Category data not in line items, pulling product categories...")
        unique_pids = list(set(pid for pid, _ in top_products[:20]))
        for pid in unique_pids:
            try:
                resp = wc_request(f"/products/{pid}")
                prod = resp.json()
                cats = prod.get("categories", [])
                if cats:
                    cat_name = cats[0].get("name", "Uncategorized")
                    category_revenue[cat_name] += product_revenue[pid]
                    category_units[cat_name] += product_units[pid]
                time.sleep(0.3)
            except Exception as e:
                print(f"    [WARN] Could not fetch product {pid}: {e}")

    results = {
        "avg_items_per_order": avg_items_per_order,
        "single_item_orders": single_item_orders,
        "single_item_rate": single_item_rate,
        "total_good_orders": len(good_orders),
        "top_products": top_products_data,
        "category_revenue": dict(category_revenue),
        "category_units": dict(category_units),
    }

    print(f"\n  Avg Items/Order: {avg_items_per_order:.2f}")
    print(f"  Single-Item Orders: {single_item_orders}/{len(good_orders)} ({single_item_rate:.1f}%)")
    print(f"\n  Top 20 Products by Revenue:")
    for i, p in enumerate(top_products_data, 1):
        print(f"    {i:2d}. {p['name'][:50]:50s} ${p['revenue']:>10,.2f}  ({p['units']} units)")
    if category_revenue:
        print(f"\n  Category Distribution:")
        for cat, rev in sorted(category_revenue.items(), key=lambda x: -x[1])[:10]:
            print(f"    {cat}: ${rev:,.2f} ({category_units[cat]} units)")

    return results


# ══════════════════════════════════════════════════════════════
# 3. CUSTOMER ANALYSIS
# ══════════════════════════════════════════════════════════════

def analyze_customers(orders):
    """Analyze new vs returning customers and geography."""
    print("\n═══ CUSTOMER ANALYSIS ═══")

    good_statuses = {"completed", "processing"}
    good_orders = [o for o in orders if o.get("status") in good_statuses]

    if not good_orders:
        return {}

    # New vs returning (customer_id=0 means guest/new)
    new_orders = 0
    returning_orders = 0
    customer_ids = set()
    new_revenue = 0.0
    returning_revenue = 0.0

    for o in good_orders:
        cid = o.get("customer_id", 0)
        rev = float(o.get("total", 0))
        if cid == 0:
            new_orders += 1
            new_revenue += rev
        else:
            if cid in customer_ids:
                returning_orders += 1
                returning_revenue += rev
            else:
                # First order from this customer in the period
                customer_ids.add(cid)
                # Could be new or returning from before the period
                # WC doesn't expose "first order date" easily, treat as "unique"
                new_orders += 1
                new_revenue += rev

    # Geographic distribution
    country_orders = Counter()
    country_revenue = defaultdict(float)
    for o in good_orders:
        billing = o.get("billing", {})
        country = billing.get("country", "Unknown")
        country_orders[country] += 1
        country_revenue[country] += float(o.get("total", 0))

    results = {
        "new_orders": new_orders,
        "returning_orders": returning_orders,
        "new_revenue": new_revenue,
        "returning_revenue": returning_revenue,
        "unique_customers": len(customer_ids),
        "guest_orders": sum(1 for o in good_orders if o.get("customer_id", 0) == 0),
        "country_orders": dict(country_orders.most_common(10)),
        "country_revenue": {k: country_revenue[k] for k, _ in country_orders.most_common(10)},
    }

    print(f"\n  New/Guest Orders: {new_orders} (${new_revenue:,.2f})")
    print(f"  Returning Orders: {returning_orders} (${returning_revenue:,.2f})")
    print(f"  Unique Customer IDs: {len(customer_ids)}")
    print(f"  Guest Checkout Orders: {results['guest_orders']}")
    print(f"\n  Country Distribution:")
    for c, cnt in country_orders.most_common(10):
        print(f"    {c}: {cnt} orders (${country_revenue[c]:,.2f})")

    return results


# ══════════════════════════════════════════════════════════════
# 4. SUPABASE YoY COMPARISON
# ══════════════════════════════════════════════════════════════

def pull_supabase_yoy():
    """Pull last year's data from Supabase for YoY comparison."""
    print("\n═══ SUPABASE YoY COMPARISON ═══")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("  [SKIP] Supabase credentials not configured")
        return {}

    headers = {"apikey": SUPABASE_KEY}

    # Last year same period
    params = {
        "select": "*",
        "report_date": f"gte.{YOY_START}",
        "channel": "eq.woocommerce",
    }
    # Need two date filters — use AND via query string
    url = (f"{SUPABASE_URL}/rest/v1/daily_sales"
           f"?select=*"
           f"&report_date=gte.{YOY_START}"
           f"&report_date=lte.{YOY_END}"
           f"&channel=eq.woocommerce")

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        yoy_data = resp.json()
    except Exception as e:
        print(f"  [ERROR] Supabase query failed: {e}")
        return {}

    if not yoy_data:
        print("  No YoY data found in Supabase")
        return {}

    yoy_revenue = sum(float(r.get("revenue", 0)) for r in yoy_data)
    yoy_orders = sum(int(r.get("orders", 0)) for r in yoy_data)
    yoy_aov = yoy_revenue / yoy_orders if yoy_orders else 0
    yoy_units = sum(int(r.get("units", 0)) for r in yoy_data)

    # Also pull current period from Supabase for consistency
    url_current = (f"{SUPABASE_URL}/rest/v1/daily_sales"
                   f"?select=*"
                   f"&report_date=gte.{START_DATE}"
                   f"&report_date=lte.{END_DATE}"
                   f"&channel=eq.woocommerce")

    try:
        resp2 = requests.get(url_current, headers=headers, timeout=30)
        resp2.raise_for_status()
        current_data = resp2.json()
    except Exception as e:
        print(f"  [WARN] Current period Supabase query failed: {e}")
        current_data = []

    current_revenue = sum(float(r.get("revenue", 0)) for r in current_data)
    current_orders = sum(int(r.get("orders", 0)) for r in current_data)
    current_aov = current_revenue / current_orders if current_orders else 0

    results = {
        "yoy_revenue": yoy_revenue,
        "yoy_orders": yoy_orders,
        "yoy_aov": yoy_aov,
        "yoy_units": yoy_units,
        "current_revenue_supabase": current_revenue,
        "current_orders_supabase": current_orders,
        "current_aov_supabase": current_aov,
        "revenue_change_pct": ((current_revenue - yoy_revenue) / yoy_revenue * 100) if yoy_revenue else 0,
        "orders_change_pct": ((current_orders - yoy_orders) / yoy_orders * 100) if yoy_orders else 0,
        "aov_change_pct": ((current_aov - yoy_aov) / yoy_aov * 100) if yoy_aov else 0,
    }

    print(f"\n  Last Year ({YOY_START} to {YOY_END}):")
    print(f"    Revenue: ${yoy_revenue:,.2f}")
    print(f"    Orders: {yoy_orders}")
    print(f"    AOV: ${yoy_aov:,.2f}")
    print(f"\n  This Year (Supabase data):")
    print(f"    Revenue: ${current_revenue:,.2f}")
    print(f"    Orders: {current_orders}")
    print(f"    AOV: ${current_aov:,.2f}")
    print(f"\n  YoY Changes:")
    print(f"    Revenue: {results['revenue_change_pct']:+.1f}%")
    print(f"    Orders: {results['orders_change_pct']:+.1f}%")
    print(f"    AOV: {results['aov_change_pct']:+.1f}%")

    return results


# ══════════════════════════════════════════════════════════════
# 5. GENERATE REPORT
# ══════════════════════════════════════════════════════════════

def calculate_health_score(order_data, product_data, customer_data):
    """Calculate a conversion health score 0-100."""
    score = 100
    penalties = []

    if not order_data:
        return 0, ["No order data available"]

    # Refund rate penalty (>3% = bad)
    rr = order_data.get("refund_rate", 0)
    if rr > 5:
        penalty = min(20, (rr - 3) * 5)
        score -= penalty
        penalties.append(f"High refund rate ({rr:.1f}%): -{penalty:.0f}")
    elif rr > 3:
        penalty = (rr - 3) * 3
        score -= penalty
        penalties.append(f"Elevated refund rate ({rr:.1f}%): -{penalty:.0f}")

    # Failed order penalty
    total = order_data.get("total_orders", 1)
    failed_rate = order_data.get("failed_count", 0) / total * 100
    if failed_rate > 2:
        penalty = min(15, failed_rate * 3)
        score -= penalty
        penalties.append(f"High failure rate ({failed_rate:.1f}%): -{penalty:.0f}")

    # Cancelled order penalty
    cancel_rate = order_data.get("cancelled_count", 0) / total * 100
    if cancel_rate > 5:
        penalty = min(15, (cancel_rate - 3) * 3)
        score -= penalty
        penalties.append(f"High cancel rate ({cancel_rate:.1f}%): -{penalty:.0f}")

    # Single-item order penalty (>70% = cross-sell problem)
    si_rate = product_data.get("single_item_rate", 0)
    if si_rate > 80:
        penalty = 15
        score -= penalty
        penalties.append(f"Very high single-item rate ({si_rate:.1f}%): -{penalty}")
    elif si_rate > 70:
        penalty = 10
        score -= penalty
        penalties.append(f"High single-item rate ({si_rate:.1f}%): -{penalty}")

    # Low AOV penalty (<$50 for seed company)
    aov = order_data.get("good_aov", 0)
    if aov < 30:
        penalty = 15
        score -= penalty
        penalties.append(f"Very low AOV (${aov:.2f}): -{penalty}")
    elif aov < 50:
        penalty = 8
        score -= penalty
        penalties.append(f"Low AOV (${aov:.2f}): -{penalty}")

    # Guest checkout too high (>60% = account creation issue)
    guest = customer_data.get("guest_orders", 0)
    good = order_data.get("good_count", 1)
    guest_rate = guest / good * 100 if good else 0
    if guest_rate > 80:
        penalty = 10
        score -= penalty
        penalties.append(f"Very high guest checkout ({guest_rate:.1f}%): -{penalty}")

    return max(0, min(100, score)), penalties


def generate_report(order_data, product_data, customer_data, yoy_data):
    """Generate the markdown findings report."""
    score, penalties = calculate_health_score(order_data, product_data, customer_data)

    # Score label
    if score >= 80:
        label = "HEALTHY"
    elif score >= 60:
        label = "NEEDS ATTENTION"
    elif score >= 40:
        label = "AT RISK"
    else:
        label = "CRITICAL"

    report = []
    report.append("# Conversion Agent A — WooCommerce Funnel Analysis")
    report.append(f"\n**Analysis Period:** {START_DATE} to {END_DATE} (30 days)")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"**Data Source:** WooCommerce REST API v3 + Supabase")

    # --- Health Score ---
    report.append(f"\n## Conversion Health Score: {score}/100 ({label})")
    if penalties:
        report.append("\n**Score Deductions:**")
        for p in penalties:
            report.append(f"- {p}")

    # --- Revenue Overview ---
    report.append("\n## 1. Revenue Overview")
    report.append(f"\n| Metric | Value |")
    report.append(f"|--------|-------|")
    report.append(f"| Total Orders (all statuses) | {order_data.get('total_orders', 0):,} |")
    report.append(f"| Successful Orders | {order_data.get('good_count', 0):,} |")
    report.append(f"| Gross Revenue (all) | ${order_data.get('total_revenue', 0):,.2f} |")
    report.append(f"| Net Revenue (completed+processing) | ${order_data.get('good_revenue', 0):,.2f} |")
    report.append(f"| AOV (successful orders) | ${order_data.get('good_aov', 0):,.2f} |")

    # --- Order Status Breakdown ---
    report.append("\n## 2. Order Status Breakdown")
    report.append(f"\n| Status | Orders | Revenue | % of Total |")
    report.append(f"|--------|--------|---------|------------|")
    total = order_data.get("total_orders", 1)
    sc = order_data.get("status_counts", {})
    sr = order_data.get("status_revenue", {})
    for status in ["completed", "processing", "on-hold", "pending", "cancelled", "refunded", "failed"]:
        cnt = sc.get(status, 0)
        rev = sr.get(status, 0)
        pct = cnt / total * 100 if total else 0
        if cnt > 0:
            report.append(f"| {status} | {cnt:,} | ${rev:,.2f} | {pct:.1f}% |")

    # --- Revenue Leaks ---
    report.append("\n## 3. Revenue Leaks")
    total_leaked = (order_data.get("refund_amount", 0) +
                    order_data.get("partial_refund_total", 0) +
                    order_data.get("lost_revenue_failed", 0) +
                    order_data.get("lost_revenue_cancelled", 0))

    report.append(f"\n**Total Revenue Leaked: ${total_leaked:,.2f}**\n")
    report.append(f"| Leak Type | Orders | Amount | Rate |")
    report.append(f"|-----------|--------|--------|------|")
    report.append(f"| Full Refunds | {order_data.get('refund_count', 0)} | ${order_data.get('refund_amount', 0):,.2f} | {order_data.get('refund_rate', 0):.1f}% |")
    report.append(f"| Partial Refunds | {order_data.get('partial_refund_count', 0)} | ${order_data.get('partial_refund_total', 0):,.2f} | — |")
    report.append(f"| Failed Payments | {order_data.get('failed_count', 0)} | ${order_data.get('lost_revenue_failed', 0):,.2f} | {order_data.get('failed_count', 0) / total * 100:.1f}% |")
    report.append(f"| Cancelled Orders | {order_data.get('cancelled_count', 0)} | ${order_data.get('lost_revenue_cancelled', 0):,.2f} | {order_data.get('cancelled_count', 0) / total * 100:.1f}% |")
    report.append(f"| Coupon Discounts | {order_data.get('coupon_orders', 0)} | ${order_data.get('total_discount', 0):,.2f} | {order_data.get('coupon_rate', 0):.1f}% usage |")

    # --- Payment Methods ---
    report.append("\n## 4. Payment Method Distribution")
    report.append(f"\n| Method | Orders | % |")
    report.append(f"|--------|--------|---|")
    pm = order_data.get("payment_methods", {})
    pm_total = sum(pm.values()) if pm else 1
    for method, cnt in sorted(pm.items(), key=lambda x: -x[1]):
        report.append(f"| {method} | {cnt:,} | {cnt / pm_total * 100:.1f}% |")

    # --- Shipping Methods ---
    report.append("\n## 5. Shipping Method Distribution")
    report.append(f"\n| Method | Orders | Total Shipping Rev |")
    report.append(f"|--------|--------|-------------------|")
    sm = order_data.get("shipping_methods", {})
    sc_ship = order_data.get("shipping_costs", {})
    for method, cnt in sorted(sm.items(), key=lambda x: -x[1]):
        report.append(f"| {method} | {cnt:,} | ${sc_ship.get(method, 0):,.2f} |")

    # --- Coupon Analysis ---
    report.append("\n## 6. Coupon Usage")
    report.append(f"\n- Coupon usage rate: {order_data.get('coupon_rate', 0):.1f}%")
    report.append(f"- Total discount given: ${order_data.get('total_discount', 0):,.2f}")
    top_coupons = order_data.get("top_coupons", {})
    if top_coupons:
        report.append(f"\n| Coupon Code | Times Used |")
        report.append(f"|-------------|------------|")
        for code, cnt in sorted(top_coupons.items(), key=lambda x: -x[1]):
            report.append(f"| {code} | {cnt} |")

    # --- Product Analysis ---
    report.append("\n## 7. Product Performance")
    report.append(f"\n- Average items per order: {product_data.get('avg_items_per_order', 0):.2f}")
    report.append(f"- Single-item orders: {product_data.get('single_item_orders', 0)}/{product_data.get('total_good_orders', 0)} ({product_data.get('single_item_rate', 0):.1f}%)")

    top_prods = product_data.get("top_products", [])
    if top_prods:
        report.append(f"\n### Top 20 Products by Revenue")
        report.append(f"\n| # | Product | SKU | Revenue | Units |")
        report.append(f"|---|---------|-----|---------|-------|")
        for i, p in enumerate(top_prods, 1):
            report.append(f"| {i} | {p['name'][:60]} | {p['sku']} | ${p['revenue']:,.2f} | {p['units']} |")

    cat_rev = product_data.get("category_revenue", {})
    if cat_rev:
        report.append(f"\n### Category Distribution")
        report.append(f"\n| Category | Revenue | Units |")
        report.append(f"|----------|---------|-------|")
        cat_units = product_data.get("category_units", {})
        for cat, rev in sorted(cat_rev.items(), key=lambda x: -x[1])[:15]:
            report.append(f"| {cat} | ${rev:,.2f} | {cat_units.get(cat, 0)} |")

    # --- Customer Analysis ---
    report.append("\n## 8. Customer Analysis")
    report.append(f"\n| Metric | Value |")
    report.append(f"|--------|-------|")
    report.append(f"| New/First-Time Orders | {customer_data.get('new_orders', 0):,} (${customer_data.get('new_revenue', 0):,.2f}) |")
    report.append(f"| Returning Orders | {customer_data.get('returning_orders', 0):,} (${customer_data.get('returning_revenue', 0):,.2f}) |")
    report.append(f"| Unique Registered Customers | {customer_data.get('unique_customers', 0):,} |")
    report.append(f"| Guest Checkout Orders | {customer_data.get('guest_orders', 0):,} |")

    country_orders = customer_data.get("country_orders", {})
    if country_orders:
        report.append(f"\n### Geographic Distribution")
        report.append(f"\n| Country | Orders | Revenue |")
        report.append(f"|---------|--------|---------|")
        country_rev = customer_data.get("country_revenue", {})
        for c, cnt in sorted(country_orders.items(), key=lambda x: -x[1]):
            report.append(f"| {c} | {cnt:,} | ${country_rev.get(c, 0):,.2f} |")

    # Top states
    top_states = order_data.get("top_states", {})
    if top_states:
        report.append(f"\n### Top 10 States/Regions")
        report.append(f"\n| State | Orders | Revenue |")
        report.append(f"|-------|--------|---------|")
        tsr = order_data.get("top_state_revenue", {})
        for st, cnt in sorted(top_states.items(), key=lambda x: -x[1]):
            report.append(f"| {st} | {cnt:,} | ${tsr.get(st, 0):,.2f} |")

    # --- YoY Comparison ---
    report.append("\n## 9. Year-over-Year Comparison")
    if yoy_data:
        report.append(f"\n| Metric | This Year | Last Year | Change |")
        report.append(f"|--------|-----------|-----------|--------|")
        report.append(f"| Revenue | ${yoy_data.get('current_revenue_supabase', 0):,.2f} | ${yoy_data.get('yoy_revenue', 0):,.2f} | {yoy_data.get('revenue_change_pct', 0):+.1f}% |")
        report.append(f"| Orders | {yoy_data.get('current_orders_supabase', 0):,} | {yoy_data.get('yoy_orders', 0):,} | {yoy_data.get('orders_change_pct', 0):+.1f}% |")
        report.append(f"| AOV | ${yoy_data.get('current_aov_supabase', 0):,.2f} | ${yoy_data.get('yoy_aov', 0):,.2f} | {yoy_data.get('aov_change_pct', 0):+.1f}% |")

        # Flag concerning patterns
        if yoy_data.get("revenue_change_pct", 0) < -10:
            report.append(f"\n> **WARNING:** Revenue is down {abs(yoy_data['revenue_change_pct']):.1f}% YoY — investigate root cause")
        if yoy_data.get("orders_change_pct", 0) < -10:
            report.append(f"\n> **WARNING:** Order volume is down {abs(yoy_data['orders_change_pct']):.1f}% YoY — traffic or conversion issue")
        if yoy_data.get("aov_change_pct", 0) < -10:
            report.append(f"\n> **WARNING:** AOV is down {abs(yoy_data['aov_change_pct']):.1f}% YoY — pricing or mix shift")
    else:
        report.append("\n*Supabase data not available for YoY comparison.*")

    # --- AOV Optimization ---
    report.append("\n## 10. AOV Optimization Opportunities")
    aov = order_data.get("good_aov", 0)
    si_rate = product_data.get("single_item_rate", 0)
    avg_items = product_data.get("avg_items_per_order", 0)

    if si_rate > 60:
        report.append(f"\n- **Cross-sell gap:** {si_rate:.0f}% of orders contain only 1 item. "
                      f"Adding bundle suggestions or 'frequently bought together' could lift AOV by 15-25%.")
    if avg_items < 2:
        report.append(f"\n- **Low basket depth:** Average {avg_items:.1f} items per order. "
                      f"Consider minimum-order free shipping threshold above AOV (e.g., ${aov * 1.3:.0f}) to encourage add-ons.")
    if aov < 60:
        report.append(f"\n- **AOV below $60:** Consider product bundles, quantity breaks, "
                      f"or tiered pricing to increase average spend.")

    coupon_rate = order_data.get("coupon_rate", 0)
    if coupon_rate > 30:
        report.append(f"\n- **Heavy coupon dependency:** {coupon_rate:.0f}% of orders use coupons "
                      f"(${order_data.get('total_discount', 0):,.2f} in discounts). "
                      f"Consider reducing coupon availability or switching to loyalty rewards.")

    # --- Top 5 Recommendations ---
    report.append("\n## 11. Top 5 Conversion Optimization Recommendations")
    recommendations = []

    # 1. Based on biggest leak
    total_leaked = (order_data.get("refund_amount", 0) +
                    order_data.get("lost_revenue_failed", 0) +
                    order_data.get("lost_revenue_cancelled", 0))
    if order_data.get("failed_count", 0) > 0:
        recommendations.append({
            "title": "Fix Payment Failures",
            "detail": (f"{order_data['failed_count']} failed orders = ${order_data['lost_revenue_failed']:,.2f} lost. "
                       f"Audit payment gateway logs, check for 3DS issues, add retry logic for declined cards, "
                       f"and consider adding alternative payment methods (PayPal, Apple Pay)."),
            "impact": f"Recover up to ${order_data['lost_revenue_failed']:,.2f}/month",
        })

    if order_data.get("cancelled_count", 0) > 3:
        recommendations.append({
            "title": "Reduce Order Cancellations",
            "detail": (f"{order_data['cancelled_count']} cancelled orders = ${order_data['lost_revenue_cancelled']:,.2f} lost. "
                       f"Add exit-intent offers, send abandoned-cart recovery emails faster (within 1 hour), "
                       f"and analyze cancellation reasons."),
            "impact": f"Recover up to ${order_data['lost_revenue_cancelled'] * 0.3:,.2f}/month (30% recovery rate)",
        })

    if si_rate > 50:
        lift = order_data.get("good_revenue", 0) * 0.15
        recommendations.append({
            "title": "Implement Cross-Sell / Bundle Strategy",
            "detail": (f"{si_rate:.0f}% single-item orders with only {avg_items:.1f} avg items. "
                       f"Add 'Complete Your Garden' product recommendations on cart page, "
                       f"create seed bundles by growing zone/season, offer quantity breaks."),
            "impact": f"Estimated +${lift:,.0f}/month (15% AOV lift)",
        })

    if order_data.get("refund_rate", 0) > 2:
        recommendations.append({
            "title": "Reduce Refund Rate",
            "detail": (f"Refund rate at {order_data['refund_rate']:.1f}% (${order_data['refund_amount']:,.2f}). "
                       f"Improve product descriptions with germination expectations, "
                       f"add planting zone guidance to PDPs, proactive shipping notifications."),
            "impact": f"Save up to ${order_data['refund_amount'] * 0.5:,.2f}/month (50% reduction target)",
        })

    guest_orders = customer_data.get("guest_orders", 0)
    good_count = order_data.get("good_count", 1)
    guest_rate = guest_orders / good_count * 100 if good_count else 0
    if guest_rate > 50:
        recommendations.append({
            "title": "Increase Account Creation Rate",
            "detail": (f"{guest_rate:.0f}% of orders are guest checkout. "
                       f"Offer account-only perks (order tracking, reorder, loyalty points). "
                       f"Post-purchase email to convert guests to accounts."),
            "impact": "Increase repeat purchase rate by 20-30%",
        })

    # Add free shipping threshold if not already there
    if aov > 0:
        recommendations.append({
            "title": "Optimize Free Shipping Threshold",
            "detail": (f"Set free shipping at ${aov * 1.25:.0f} (25% above current AOV of ${aov:.2f}). "
                       f"This encourages customers to add items to reach the threshold."),
            "impact": f"Estimated 10-15% AOV increase (${aov * 0.12:.2f} per order)",
        })

    # Take top 5
    recommendations = recommendations[:5]

    if not recommendations:
        report.append("\n*No recommendations generated — insufficient order data. "
                      "Ensure WC_CK, WC_CS are set in .env and re-run.*")
    else:
        for i, rec in enumerate(recommendations, 1):
            report.append(f"\n### {i}. {rec['title']}")
            report.append(f"\n{rec['detail']}")
            report.append(f"\n**Estimated Impact:** {rec['impact']}")

    # --- Raw Data Summary (JSON) ---
    report.append("\n---")
    report.append("\n*Report generated by Conversion Agent A — WooCommerce Funnel Analysis*")

    return "\n".join(report)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("CONVERSION AGENT A — WooCommerce Funnel Analysis")
    print(f"Period: {START_DATE} to {END_DATE}")
    print("=" * 60)

    # Check credentials
    if not WC_CK or not WC_CS:
        print("\n[ERROR] WC_CK and WC_CS not found in .env")
        print("Creating report with sample/empty data structure...")
        # Still generate the report structure for review
        order_data = {}
        product_data = {}
        customer_data = {}
        yoy_data = {}
    else:
        # Pull all orders
        all_orders = pull_all_orders()

        # Analyze
        order_data = analyze_orders(all_orders)
        product_data = analyze_products(all_orders)
        customer_data = analyze_customers(all_orders)
        yoy_data = pull_supabase_yoy()

    # Generate report
    report_text = generate_report(order_data, product_data, customer_data, yoy_data)

    # Save report
    report_path = Path(__file__).resolve().parent.parent / "reports" / "conversion_a_findings.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report_text)
    print(f"\n\n{'=' * 60}")
    print(f"Report saved to: {report_path}")
    print(f"{'=' * 60}")

    # Also save raw data as JSON for other agents
    data_path = report_path.parent / "conversion_a_raw_data.json"
    raw_data = {
        "period": {"start": str(START_DATE), "end": str(END_DATE)},
        "order_analysis": {k: v for k, v in order_data.items()
                          if not isinstance(v, (Counter, defaultdict))},
        "product_analysis": product_data,
        "customer_analysis": customer_data,
        "yoy_comparison": yoy_data,
    }
    with open(data_path, "w") as f:
        json.dump(raw_data, f, indent=2, default=str)
    print(f"Raw data saved to: {data_path}")


if __name__ == "__main__":
    main()
