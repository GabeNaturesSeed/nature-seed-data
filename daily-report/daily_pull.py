#!/usr/bin/env python3
"""
Nature's Seed — Daily Report Data Pull
Runs at midnight, pulls yesterday's data from all sources, writes to Supabase.

Sources:
  1. WooCommerce — orders & revenue
  2. Walmart — orders & revenue
  3. Google Ads — ad spend
  4. Shippo — shipping costs
  5. Google Sheets — COGS lookup (synced periodically)

Usage:
  python3 daily_pull.py              # Pull yesterday's data
  python3 daily_pull.py 2026-03-01   # Pull specific date
  python3 daily_pull.py backfill 2025-01-01 2026-03-08  # Backfill range
"""

import json
import sys
import time
import os
import base64
import uuid
import urllib.request
import urllib.parse
import csv
import io
from datetime import datetime, date, timedelta
from pathlib import Path

import requests
from google.oauth2.credentials import Credentials
from google.ads.googleads.client import GoogleAdsClient

# ══════════════════════════════════════════════════════════════
# ENV + SUPABASE SETUP
# ══════════════════════════════════════════════════════════════

env_path = Path(__file__).resolve().parent.parent / ".env"
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")

# WooCommerce
WC_BASE = env_vars.get("WC_BASE_URL", "https://naturesseed.com/wp-json/wc/v3")
WC_CK = env_vars["WC_CK"]
WC_CS = env_vars["WC_CS"]
WC_AUTH = (WC_CK, WC_CS)

# Walmart
WM_CLIENT_ID = env_vars["WALMART_CLIENT_ID"]
WM_CLIENT_SECRET = env_vars["WALMART_CLIENT_SECRET"]
WM_BASE = "https://marketplace.walmartapis.com/v3"

# Google Ads
GOOGLE_ADS_CONFIG = {
    "developer_token": env_vars["GOOGLE_ADS_DEVELOPER_TOKEN"],
    "client_id": env_vars["GOOGLE_ADS_CLIENT_ID"],
    "client_secret": env_vars["GOOGLE_ADS_CLIENT_SECRET"],
    "refresh_token": env_vars["GOOGLE_ADS_REFRESH_TOKEN"],
    "use_proto_plus": True,
}
login_cid = env_vars.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
if login_cid:
    GOOGLE_ADS_CONFIG["login_customer_id"] = login_cid
GOOGLE_ADS_CUSTOMER_ID = env_vars["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")

# Shippo
SHIPPO_API_KEY = env_vars.get("SHIPPO_API_KEY", "")

# Google Sheets COGS
COGS_SHEET_ID = "1nve5yRvw7fY0caVqZDHYDjhoQmj_a6S9PkC3BMKm1S4"


# ══════════════════════════════════════════════════════════════
# SUPABASE HELPERS
# ══════════════════════════════════════════════════════════════

# Unique constraint columns for each table (used for upsert)
_UPSERT_KEYS = {
    "daily_sales": "report_date,channel",
    "daily_ad_spend": "report_date,channel",
    "daily_shipping": "report_date",
    "daily_cogs": "report_date,channel",
    "cogs_lookup": "sku",
    "financial_goals": "year,month",
}


def supabase_upsert(table, rows):
    """Upsert rows into a Supabase table via REST API.
    Uses PostgREST on_conflict query param to specify unique columns,
    combined with Prefer: resolution=merge-duplicates to update on conflict.
    """
    if not rows:
        return
    on_conflict = _UPSERT_KEYS.get(table, "")
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if on_conflict:
        url += f"?on_conflict={on_conflict}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    # Strip auto-generated columns
    clean_rows = [{k: v for k, v in row.items() if k not in ("id", "created_at", "updated_at")} for row in rows]
    resp = requests.post(url, headers=headers, json=clean_rows, timeout=30)
    if resp.status_code not in (200, 201, 204):
        print(f"    [WARN] Supabase upsert {table}: {resp.status_code} {resp.text[:200]}")
    else:
        print(f"    [OK] Upserted {len(clean_rows)} rows into {table}")


def supabase_query(table, params=None):
    """Query a Supabase table."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
    }
    resp = requests.get(url, headers=headers, params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ══════════════════════════════════════════════════════════════
# 1. WOOCOMMERCE ORDERS
# ══════════════════════════════════════════════════════════════

def pull_woocommerce(report_date):
    """Pull WooCommerce completed/processing orders for a single date."""
    print(f"\n  [WooCommerce] Pulling orders for {report_date}...")

    start = f"{report_date}T00:00:00"
    end = f"{report_date}T23:59:59"

    all_orders = []
    for status in ["completed", "processing"]:
        page = 1
        while True:
            params = {
                "after": start,
                "before": end,
                "status": status,
                "per_page": 100,
                "page": page,
            }
            resp = requests.get(f"{WC_BASE}/orders", auth=WC_AUTH, params=params, timeout=60)
            resp.raise_for_status()
            orders = resp.json()
            if not orders:
                break
            all_orders.extend(orders)
            total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
            if page >= total_pages:
                break
            page += 1
            time.sleep(0.3)

    # Aggregate
    revenue = sum(float(o.get("total", 0)) for o in all_orders)
    order_count = len(all_orders)
    units = sum(
        item.get("quantity", 0)
        for o in all_orders
        for item in o.get("line_items", [])
    )

    # Calculate COGS from line items
    cogs = calculate_cogs_for_orders(all_orders)

    print(f"    Orders: {order_count} | Revenue: ${revenue:,.2f} | Units: {units} | COGS: ${cogs:,.2f}")

    return {
        "sales": {
            "report_date": str(report_date),
            "channel": "woocommerce",
            "revenue": round(revenue, 2),
            "orders": order_count,
            "units": units,
        },
        "cogs": {
            "report_date": str(report_date),
            "channel": "woocommerce",
            "total_cogs": round(cogs, 2),
            "matched_units": units,  # will refine below
            "unmatched_units": 0,
        },
        "raw_orders": all_orders,
    }


# ══════════════════════════════════════════════════════════════
# 2. WALMART ORDERS
# ══════════════════════════════════════════════════════════════

_wm_token_cache = {"token": None, "expires_at": None}

def _wm_get_token():
    """Get/refresh Walmart OAuth token."""
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
    return _wm_token_cache["token"]


def _wm_headers():
    return {
        "WM_SEC.ACCESS_TOKEN": _wm_get_token(),
        "WM_SVC.NAME": "Nature's Seed",
        "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def pull_walmart(report_date):
    """Pull Walmart orders for a single date."""
    print(f"\n  [Walmart] Pulling orders for {report_date}...")

    start = f"{report_date}T00:00:00.000Z"
    end = f"{report_date}T23:59:59.999Z"

    all_orders = []
    next_cursor = None

    while True:
        params = {
            "createdStartDate": start,
            "createdEndDate": end,
            "limit": 200,
        }
        if next_cursor:
            params["nextCursor"] = next_cursor

        url = f"{WM_BASE}/orders?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, method="GET")
        for k, v in _wm_headers().items():
            req.add_header(k, v)

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # No orders for this date
                break
            raise

        elements = data.get("list", {}).get("elements", {}).get("order", [])
        if not elements:
            break

        all_orders.extend(elements)

        meta = data.get("list", {}).get("meta", {})
        next_cursor = meta.get("nextCursor")
        if not next_cursor:
            break
        time.sleep(0.5)

    # Aggregate — Walmart order totals
    revenue = 0
    units = 0
    for order in all_orders:
        for line in order.get("orderLines", {}).get("orderLine", []):
            charges = line.get("charges", {}).get("charge", [])
            for charge in charges:
                if charge.get("chargeType") == "PRODUCT":
                    amount = charge.get("chargeAmount", {})
                    revenue += float(amount.get("amount", 0))
            qty = int(line.get("orderLineQuantity", {}).get("amount", 0))
            units += qty

    order_count = len(all_orders)
    print(f"    Orders: {order_count} | Revenue: ${revenue:,.2f} | Units: {units}")

    return {
        "sales": {
            "report_date": str(report_date),
            "channel": "walmart",
            "revenue": round(revenue, 2),
            "orders": order_count,
            "units": units,
        },
        "cogs": {
            "report_date": str(report_date),
            "channel": "walmart",
            "total_cogs": 0,  # TODO: match Walmart SKUs to COGS
            "matched_units": 0,
            "unmatched_units": units,
        },
    }


# ══════════════════════════════════════════════════════════════
# 3. GOOGLE ADS SPEND
# ══════════════════════════════════════════════════════════════

def pull_google_ads(report_date):
    """Pull Google Ads spend for a single date."""
    print(f"\n  [Google Ads] Pulling spend for {report_date}...")

    client = GoogleAdsClient.load_from_dict(GOOGLE_ADS_CONFIG)
    ga_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date = '{report_date}'
          AND campaign.status != 'REMOVED'
    """

    try:
        response = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query)
        rows = list(response)
    except Exception as e:
        print(f"    [ERR] {e}")
        rows = []

    spend = sum(r.metrics.cost_micros / 1_000_000 for r in rows)
    impressions = sum(r.metrics.impressions for r in rows)
    clicks = sum(r.metrics.clicks for r in rows)
    conversions = sum(r.metrics.conversions for r in rows)
    conv_value = sum(r.metrics.conversions_value for r in rows)

    print(f"    Spend: ${spend:,.2f} | Clicks: {clicks:,} | Conv: {conversions:.1f} | Conv Value: ${conv_value:,.2f}")

    return {
        "report_date": str(report_date),
        "channel": "google_ads",
        "spend": round(spend, 2),
        "impressions": impressions,
        "clicks": clicks,
        "conversions": round(conversions, 2),
        "conversions_value": round(conv_value, 2),
    }


# ══════════════════════════════════════════════════════════════
# 4. SHIPPO SHIPPING COSTS
# ══════════════════════════════════════════════════════════════

def pull_shippo(report_date):
    """Pull Shippo transaction costs for a single date.

    Shippo doesn't support date filtering params reliably, so we paginate
    through all transactions and filter by object_created date locally.
    The rate cost is on a separate /rates/{id} endpoint.
    """
    print(f"\n  [Shippo] Pulling shipping costs for {report_date}...")

    if not SHIPPO_API_KEY:
        print("    [SKIP] No SHIPPO_API_KEY configured")
        return {"report_date": str(report_date), "total_cost": 0, "shipment_count": 0}

    headers = {
        "Authorization": f"ShippoToken {SHIPPO_API_KEY}",
    }

    target_date = str(report_date)
    total_cost = 0
    shipment_count = 0
    rate_cache = {}
    seen_tracking = set()  # Deduplicate by tracking number (voided + recreated labels)

    url = "https://api.goshippo.com/transactions/"
    params = {"results": 200}
    pages_checked = 0
    found_older = False
    skipped_dupes = 0

    while url and not found_older:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"    [WARN] Shippo: {resp.status_code} {resp.text[:200]}")
            break
        data = resp.json()
        pages_checked += 1

        for txn in data.get("results", []):
            txn_date = (txn.get("object_created") or "")[:10]

            if txn_date < target_date:
                found_older = True
                break

            if txn_date == target_date and txn.get("status") == "SUCCESS":
                # Deduplicate by tracking number — if a label was voided and
                # recreated, both SUCCESS transactions may exist. Only count once.
                tracking = txn.get("tracking_number", "")
                if tracking and tracking in seen_tracking:
                    skipped_dupes += 1
                    continue
                if tracking:
                    seen_tracking.add(tracking)

                # Look up rate cost
                rate_id = txn.get("rate", "")
                if rate_id and rate_id not in rate_cache:
                    try:
                        rate_resp = requests.get(
                            f"https://api.goshippo.com/rates/{rate_id}",
                            headers=headers, timeout=15
                        )
                        if rate_resp.status_code == 200:
                            rate_cache[rate_id] = float(rate_resp.json().get("amount", 0))
                        else:
                            rate_cache[rate_id] = 0
                    except Exception:
                        rate_cache[rate_id] = 0
                    time.sleep(0.1)

                cost = rate_cache.get(rate_id, 0)
                total_cost += cost
                shipment_count += 1

        url = data.get("next")
        params = {}  # next URL includes params
        time.sleep(0.3)

    dupe_msg = f" (deduped {skipped_dupes})" if skipped_dupes else ""
    print(f"    Shipments: {shipment_count} | Cost: ${total_cost:,.2f} (checked {pages_checked} pages){dupe_msg}")

    return {
        "report_date": str(report_date),
        "total_cost": round(total_cost, 2),
        "shipment_count": shipment_count,
    }


# ══════════════════════════════════════════════════════════════
# 5. COGS LOOKUP (Google Sheets sync)
# ══════════════════════════════════════════════════════════════

_cogs_cache = {}

def sync_cogs_from_sheet():
    """Download COGS data from Google Sheet and cache/upload to Supabase."""
    global _cogs_cache
    print("\n  [COGS] Syncing from Google Sheet...")

    url = f"https://docs.google.com/spreadsheets/d/{COGS_SHEET_ID}/export?format=csv"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = []
    for row in reader:
        sku = (row.get("SKU") or "").strip()
        if not sku:
            continue
        # Clean price formatting
        unit_cost_str = (row.get("Unit Cost") or "0").replace("$", "").replace(",", "").strip()
        selling_price_str = (row.get("Selling Price") or "0").replace("$", "").replace(",", "").strip()

        try:
            unit_cost = float(unit_cost_str) if unit_cost_str else 0
        except ValueError:
            unit_cost = 0
        try:
            selling_price = float(selling_price_str) if selling_price_str else None
        except ValueError:
            selling_price = None

        _cogs_cache[sku] = unit_cost
        rows.append({
            "sku": sku,
            "unit_cost": unit_cost,
            "selling_price": selling_price,
        })

    print(f"    Loaded {len(rows)} SKUs from sheet")

    # Upload to Supabase
    if SUPABASE_URL and SUPABASE_KEY and rows:
        supabase_upsert("cogs_lookup", rows)

    return rows


def calculate_cogs_for_orders(orders):
    """Calculate total COGS from WooCommerce orders using the cached lookup."""
    if not _cogs_cache:
        sync_cogs_from_sheet()

    total_cogs = 0
    matched = 0
    unmatched = 0
    for order in orders:
        for item in order.get("line_items", []):
            sku = (item.get("sku") or "").strip()
            qty = item.get("quantity", 0)
            if sku in _cogs_cache:
                total_cogs += _cogs_cache[sku] * qty
                matched += qty
            else:
                unmatched += qty

    return total_cogs


# ══════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════

def pull_date(report_date):
    """Pull all data for a single date and write to Supabase."""
    print(f"\n{'='*60}")
    print(f"  DAILY PULL: {report_date}")
    print(f"{'='*60}")

    # Sync COGS first (needed for order COGS calculation)
    sync_cogs_from_sheet()

    # Pull all sources
    wc = pull_woocommerce(report_date)
    wm = pull_walmart(report_date)
    ads = pull_google_ads(report_date)
    shipping = pull_shippo(report_date)

    # Aggregate for console summary
    total_revenue = wc["sales"]["revenue"] + wm["sales"]["revenue"]
    total_orders = wc["sales"]["orders"] + wm["sales"]["orders"]
    total_cogs = wc["cogs"]["total_cogs"] + wm["cogs"]["total_cogs"]
    net_revenue = total_revenue - total_cogs - shipping["total_cost"]
    mer = round(total_revenue / ads["spend"], 2) if ads["spend"] > 0 else 0

    print(f"\n{'='*60}")
    print(f"  SUMMARY: {report_date}")
    print(f"{'='*60}")
    print(f"    WC Revenue:      ${wc['sales']['revenue']:>10,.2f}  ({wc['sales']['orders']} orders)")
    print(f"    Walmart Revenue: ${wm['sales']['revenue']:>10,.2f}  ({wm['sales']['orders']} orders)")
    print(f"    Total Revenue:   ${total_revenue:>10,.2f}  ({total_orders} orders)")
    print(f"    COGS:            ${total_cogs:>10,.2f}")
    print(f"    Shipping:        ${shipping['total_cost']:>10,.2f}  ({shipping['shipment_count']} shipments)")
    print(f"    Net Revenue:     ${net_revenue:>10,.2f}")
    print(f"    Ad Spend:        ${ads['spend']:>10,.2f}")
    print(f"    MER:             {mer:>10.2f}x")

    # Write to Supabase
    if SUPABASE_URL and SUPABASE_KEY:
        print(f"\n  Writing to Supabase...")
        supabase_upsert("daily_sales", [wc["sales"], wm["sales"]])
        supabase_upsert("daily_cogs", [wc["cogs"], wm["cogs"]])
        supabase_upsert("daily_ad_spend", [ads])
        supabase_upsert("daily_shipping", [shipping])
        print("  [OK] All data written to Supabase")
    else:
        print("\n  [SKIP] No Supabase credentials — data printed only")

    return {
        "date": str(report_date),
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_cogs": total_cogs,
        "shipping_cost": shipping["total_cost"],
        "net_revenue": net_revenue,
        "ad_spend": ads["spend"],
        "mer": mer,
    }


def main():
    args = sys.argv[1:]

    if len(args) == 0:
        # Default: pull yesterday
        target = date.today() - timedelta(days=1)
        pull_date(target)

    elif args[0] == "backfill" and len(args) == 3:
        # Backfill a date range
        start = date.fromisoformat(args[1])
        end = date.fromisoformat(args[2])
        current = start
        results = []
        while current <= end:
            result = pull_date(current)
            results.append(result)
            current += timedelta(days=1)
            time.sleep(1)  # Be gentle on APIs

        # Print backfill summary
        print(f"\n\n{'='*60}")
        print(f"  BACKFILL COMPLETE: {start} → {end}")
        print(f"{'='*60}")
        total_rev = sum(r["total_revenue"] for r in results)
        total_spend = sum(r["ad_spend"] for r in results)
        print(f"    Days: {len(results)}")
        print(f"    Total Revenue: ${total_rev:,.2f}")
        print(f"    Total Ad Spend: ${total_spend:,.2f}")
        print(f"    Period MER: {total_rev/total_spend:.2f}x" if total_spend > 0 else "    Period MER: N/A")

    elif len(args) == 1:
        # Pull specific date
        target = date.fromisoformat(args[0])
        pull_date(target)

    else:
        print("Usage:")
        print("  python3 daily_pull.py              # Yesterday")
        print("  python3 daily_pull.py 2026-03-08    # Specific date")
        print("  python3 daily_pull.py backfill 2025-01-01 2026-03-08  # Range")


if __name__ == "__main__":
    main()
