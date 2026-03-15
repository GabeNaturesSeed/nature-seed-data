#!/usr/bin/env python3
"""
WooCommerce Order Attribution Diagnosis — Post March 8, 2026
=============================================================
Pulls WC orders with meta_data to trace revenue back to Google Ads campaigns.

WooCommerce 8.5+ stores attribution data in order meta:
  - _wc_order_attribution_source_type (organic, referral, utm, typein, admin)
  - _wc_order_attribution_utm_source (google, bing, etc.)
  - _wc_order_attribution_utm_medium (cpc, organic, etc.)
  - _wc_order_attribution_utm_campaign (campaign name)
  - _wc_order_attribution_utm_content
  - _wc_order_attribution_utm_term (search keyword)
  - _wc_order_attribution_session_entry (landing page URL)
  - _wc_order_attribution_session_pages (pages viewed)
  - _wc_order_attribution_referrer (referrer URL)
  - _wc_order_attribution_device_type (mobile, desktop, tablet)

Run locally: python google-ads-audit/diagnose_wc_attribution.py
"""

import json
import sys
import time
import base64
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

import requests

# ── Load .env ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
env_path = PROJECT_ROOT / ".env"
env_vars = {}
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")
else:
    print(f"ERROR: .env not found at {env_path}")
    sys.exit(1)

WC_BASE = env_vars.get("WC_BASE_URL", "https://naturesseed.com/wp-json/wc/v3")
WC_CK = env_vars["WC_CK"]
WC_CS = env_vars["WC_CS"]
WC_AUTH = (WC_CK, WC_CS)

CF_WORKER_URL = env_vars.get("CF_WORKER_URL", "")
CF_WORKER_SECRET = env_vars.get("CF_WORKER_SECRET", "")


def wc_get(endpoint, params):
    """WC API request with CF Worker proxy support."""
    if CF_WORKER_URL and CF_WORKER_SECRET:
        wc_path = endpoint
        proxy_params = dict(params)
        proxy_params["wc_path"] = wc_path
        auth_str = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        headers = {
            "X-Proxy-Secret": CF_WORKER_SECRET,
            "Authorization": f"Basic {auth_str}",
            "User-Agent": "NaturesSeed-Diagnosis/1.0",
        }
        resp = requests.get(CF_WORKER_URL, params=proxy_params, headers=headers, timeout=60)
    else:
        resp = requests.get(f"{WC_BASE}{endpoint}", auth=WC_AUTH, params=params,
                          headers={"User-Agent": "NaturesSeed-Diagnosis/1.0"}, timeout=60)
    resp.raise_for_status()
    return resp


def pull_orders_for_date(report_date):
    """Pull all completed/processing orders for a date with full meta_data."""
    start = f"{report_date}T00:00:00"
    end = f"{report_date}T23:59:59"
    all_orders = []
    for status in ["completed", "processing"]:
        page = 1
        while True:
            params = {
                "after": start, "before": end,
                "status": status, "per_page": 100, "page": page,
            }
            resp = wc_get("/orders", params)
            orders = resp.json()
            if not orders:
                break
            all_orders.extend(orders)
            total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
            if page >= total_pages:
                break
            page += 1
            time.sleep(0.3)
    return all_orders


def extract_attribution(order):
    """Extract WC order attribution meta fields."""
    meta = {}
    for m in order.get("meta_data", []):
        key = m.get("key", "")
        if key.startswith("_wc_order_attribution_"):
            short_key = key.replace("_wc_order_attribution_", "")
            meta[short_key] = m.get("value", "")
    return meta


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

BEFORE_START = "2026-02-26"  # 10 days before
BEFORE_END = "2026-03-07"
AFTER_START = "2026-03-08"
AFTER_END = "2026-03-15"

# Attribution meta keys we care about
ATTRIBUTION_KEYS = [
    "source_type", "utm_source", "utm_medium", "utm_campaign",
    "utm_content", "utm_term", "session_entry", "referrer", "device_type",
]


def analyze_period(start_date, end_date, label):
    """Pull and analyze orders for a date range."""
    print(f"\n{'=' * 80}")
    print(f"PERIOD: {label} ({start_date} to {end_date})")
    print(f"{'=' * 80}")

    all_orders = []
    current = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        print(f"  Pulling {date_str}...", end=" ", flush=True)
        orders = pull_orders_for_date(date_str)
        print(f"{len(orders)} orders")
        for o in orders:
            o["_report_date"] = date_str
            o["_attribution"] = extract_attribution(o)
        all_orders.extend(orders)
        current += timedelta(days=1)
        time.sleep(0.3)

    print(f"\n  Total orders: {len(all_orders)}")
    total_rev = sum(float(o.get("total", 0)) for o in all_orders)
    print(f"  Total revenue: ${total_rev:,.2f}")

    # ── Check what attribution data is available ─────────────────
    has_attribution = sum(1 for o in all_orders if o["_attribution"])
    print(f"\n  Orders with attribution data: {has_attribution}/{len(all_orders)}")

    if has_attribution == 0:
        print("  ⚠️  No WC attribution meta found. Checking raw meta keys...")
        all_meta_keys = set()
        for o in all_orders:
            for m in o.get("meta_data", []):
                all_meta_keys.add(m.get("key", ""))
        print(f"  Found {len(all_meta_keys)} unique meta keys across all orders:")
        for k in sorted(all_meta_keys):
            if not k.startswith("_"):
                continue  # skip non-internal
            print(f"    {k}")
        return all_orders

    # ── First: dump a sample order's attribution for inspection ──
    sample = next((o for o in all_orders if o["_attribution"]), None)
    if sample:
        print(f"\n  Sample attribution (Order #{sample.get('number')}):")
        for k, v in sample["_attribution"].items():
            print(f"    {k}: {v}")

    # ── Source type breakdown ────────────────────────────────────
    print(f"\n  --- Revenue by Source Type ---")
    by_source_type = defaultdict(lambda: {"orders": 0, "revenue": 0.0})
    for o in all_orders:
        attr = o["_attribution"]
        src = attr.get("source_type", "unknown")
        by_source_type[src]["orders"] += 1
        by_source_type[src]["revenue"] += float(o.get("total", 0))

    print(f"  {'Source Type':<20} {'Orders':>8} {'Revenue':>12} {'% Rev':>8} {'AOV':>8}")
    print(f"  {'-' * 60}")
    for src in sorted(by_source_type, key=lambda x: by_source_type[x]["revenue"], reverse=True):
        d = by_source_type[src]
        pct = d["revenue"] / total_rev * 100 if total_rev else 0
        aov = d["revenue"] / d["orders"] if d["orders"] else 0
        print(f"  {src:<20} {d['orders']:>8} ${d['revenue']:>11,.2f} {pct:>7.1f}% ${aov:>7,.2f}")

    # ── UTM Source breakdown ────────────────────────────────────
    print(f"\n  --- Revenue by UTM Source ---")
    by_utm_source = defaultdict(lambda: {"orders": 0, "revenue": 0.0})
    for o in all_orders:
        attr = o["_attribution"]
        src = attr.get("utm_source", attr.get("source_type", "none"))
        by_utm_source[src]["orders"] += 1
        by_utm_source[src]["revenue"] += float(o.get("total", 0))

    print(f"  {'UTM Source':<25} {'Orders':>8} {'Revenue':>12} {'% Rev':>8}")
    print(f"  {'-' * 55}")
    for src in sorted(by_utm_source, key=lambda x: by_utm_source[x]["revenue"], reverse=True):
        d = by_utm_source[src]
        pct = d["revenue"] / total_rev * 100 if total_rev else 0
        print(f"  {src:<25} {d['orders']:>8} ${d['revenue']:>11,.2f} {pct:>7.1f}%")

    # ── UTM Campaign breakdown (GOOGLE ADS SPECIFIC) ────────────
    print(f"\n  --- Revenue by UTM Campaign (Google Ads) ---")
    by_campaign = defaultdict(lambda: {"orders": 0, "revenue": 0.0, "terms": defaultdict(int)})
    for o in all_orders:
        attr = o["_attribution"]
        if attr.get("utm_source", "").lower() == "google" and attr.get("utm_medium", "").lower() == "cpc":
            camp = attr.get("utm_campaign", "unknown")
            by_campaign[camp]["orders"] += 1
            by_campaign[camp]["revenue"] += float(o.get("total", 0))
            term = attr.get("utm_term", "")
            if term:
                by_campaign[camp]["terms"][term] += 1

    if by_campaign:
        print(f"  {'Campaign':<45} {'Orders':>8} {'Revenue':>12} {'Top Search Terms'}")
        print(f"  {'-' * 90}")
        for camp in sorted(by_campaign, key=lambda x: by_campaign[x]["revenue"], reverse=True):
            d = by_campaign[camp]
            top_terms = ", ".join(f"{t}({c})" for t, c in
                                sorted(d["terms"].items(), key=lambda x: -x[1])[:3])
            print(f"  {camp[:44]:<45} {d['orders']:>8} ${d['revenue']:>11,.2f} {top_terms}")
    else:
        print("  No Google Ads (cpc) orders found in this period.")

    # ── Daily breakdown by source ───────────────────────────────
    print(f"\n  --- Daily Google Ads Revenue ---")
    by_date = defaultdict(lambda: {"google_cpc": 0.0, "organic": 0.0, "direct": 0.0, "other": 0.0, "total": 0.0})
    for o in all_orders:
        attr = o["_attribution"]
        date = o["_report_date"]
        rev = float(o.get("total", 0))
        by_date[date]["total"] += rev
        if attr.get("utm_source", "").lower() == "google" and attr.get("utm_medium", "").lower() == "cpc":
            by_date[date]["google_cpc"] += rev
        elif attr.get("source_type") == "organic":
            by_date[date]["organic"] += rev
        elif attr.get("source_type") in ("typein", "admin"):
            by_date[date]["direct"] += rev
        else:
            by_date[date]["other"] += rev

    print(f"  {'Date':<12} {'Google CPC':>12} {'Organic':>12} {'Direct':>12} {'Other':>12} {'Total':>12} {'G.Ads%':>8}")
    print(f"  {'-' * 80}")
    for date in sorted(by_date):
        d = by_date[date]
        g_pct = d["google_cpc"] / d["total"] * 100 if d["total"] else 0
        print(f"  {date:<12} ${d['google_cpc']:>11,.2f} ${d['organic']:>11,.2f} ${d['direct']:>11,.2f} ${d['other']:>11,.2f} ${d['total']:>11,.2f} {g_pct:>7.1f}%")

    # ── UTM Term analysis (search terms driving orders) ─────────
    print(f"\n  --- Top Search Terms (utm_term) Driving Revenue ---")
    by_term = defaultdict(lambda: {"orders": 0, "revenue": 0.0})
    for o in all_orders:
        attr = o["_attribution"]
        term = attr.get("utm_term", "")
        if term and attr.get("utm_medium", "").lower() == "cpc":
            by_term[term]["orders"] += 1
            by_term[term]["revenue"] += float(o.get("total", 0))

    if by_term:
        print(f"  {'Search Term':<45} {'Orders':>8} {'Revenue':>12}")
        print(f"  {'-' * 68}")
        for term in sorted(by_term, key=lambda x: by_term[x]["revenue"], reverse=True)[:30]:
            d = by_term[term]
            print(f"  {term[:44]:<45} {d['orders']:>8} ${d['revenue']:>11,.2f}")
    else:
        print("  No utm_term data found.")

    # ── Device type breakdown ───────────────────────────────────
    print(f"\n  --- Device Type Breakdown ---")
    by_device = defaultdict(lambda: {"orders": 0, "revenue": 0.0})
    for o in all_orders:
        attr = o["_attribution"]
        device = attr.get("device_type", "unknown")
        by_device[device]["orders"] += 1
        by_device[device]["revenue"] += float(o.get("total", 0))

    print(f"  {'Device':<15} {'Orders':>8} {'Revenue':>12} {'AOV':>8}")
    print(f"  {'-' * 45}")
    for dev in sorted(by_device, key=lambda x: by_device[x]["revenue"], reverse=True):
        d = by_device[dev]
        aov = d["revenue"] / d["orders"] if d["orders"] else 0
        print(f"  {dev:<15} {d['orders']:>8} ${d['revenue']:>11,.2f} ${aov:>7,.2f}")

    return all_orders


if __name__ == "__main__":
    print("=" * 80)
    print("WOOCOMMERCE ORDER ATTRIBUTION DIAGNOSIS")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    before_orders = analyze_period(BEFORE_START, BEFORE_END, "BEFORE CHANGES")
    after_orders = analyze_period(AFTER_START, AFTER_END, "AFTER CHANGES")

    # ── COMPARISON SUMMARY ──────────────────────────────────────
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY: BEFORE vs AFTER")
    print("=" * 80)

    def summarize_google_ads(orders, label):
        google_orders = [o for o in orders if
                        o["_attribution"].get("utm_source", "").lower() == "google" and
                        o["_attribution"].get("utm_medium", "").lower() == "cpc"]
        total_rev = sum(float(o.get("total", 0)) for o in orders)
        google_rev = sum(float(o.get("total", 0)) for o in google_orders)
        days = len(set(o["_report_date"] for o in orders)) or 1
        g_pct = google_rev / total_rev * 100 if total_rev else 0
        print(f"\n  {label}:")
        print(f"    Total orders: {len(orders)} | Revenue: ${total_rev:,.2f} | Avg/day: ${total_rev/days:,.2f}")
        print(f"    Google Ads orders: {len(google_orders)} | Revenue: ${google_rev:,.2f} | Avg/day: ${google_rev/days:,.2f}")
        print(f"    Google Ads % of revenue: {g_pct:.1f}%")
        print(f"    Google Ads AOV: ${google_rev/len(google_orders):,.2f}" if google_orders else "    Google Ads AOV: N/A")

        # Campaign breakdown
        by_camp = defaultdict(float)
        for o in google_orders:
            camp = o["_attribution"].get("utm_campaign", "unknown")
            by_camp[camp] += float(o.get("total", 0))
        if by_camp:
            print(f"    Campaign revenue:")
            for c in sorted(by_camp, key=lambda x: by_camp[x], reverse=True):
                print(f"      {c}: ${by_camp[c]:,.2f}")
        return google_rev, len(google_orders), days

    b_rev, b_ord, b_days = summarize_google_ads(before_orders, "BEFORE (Feb 26 - Mar 7)")
    a_rev, a_ord, a_days = summarize_google_ads(after_orders, "AFTER  (Mar 8 - Mar 15)")

    if b_rev and b_days and a_days:
        b_daily = b_rev / b_days
        a_daily = a_rev / a_days
        chg = ((a_daily - b_daily) / b_daily) * 100
        print(f"\n  >>> Google Ads daily revenue change: ${b_daily:,.2f} → ${a_daily:,.2f} ({chg:+.1f}%)")

    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)
    print("\nTo save: python diagnose_wc_attribution.py > wc_attribution_report.txt 2>&1")
