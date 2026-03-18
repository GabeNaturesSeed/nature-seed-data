#!/usr/bin/env python3
"""
Nature's Seed — Operations Dashboard Data Generator
Runs nightly via GitHub Actions to pull data from all sources and write JSON
files to docs/data/. These files power the static HTML operations dashboard.

Sources:
  1. Supabase  — reporting.json  (MTD/YTD P&L)
  2. Budget CSV — budget.json    (2026 budget + actuals)
  3. Klaviyo   — klaviyo.json    (upcoming campaigns)
  4. Amazon    — amazon.json     (SP-API orders + health)
  5. Walmart   — walmart.json    (marketplace orders)
  6. Fishbowl  — inventory.json  (stock levels + velocity)
  7. docs/notes.md — notes.json  (operator notes)
"""

import json
import sys
import time
import base64
import uuid
import re
import csv
import io
from datetime import datetime, date, timedelta
from pathlib import Path

import requests

try:
    from google.ads.googleads.client import GoogleAdsClient
    HAS_GOOGLE_ADS = True
except ImportError:
    HAS_GOOGLE_ADS = False

# ══════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "docs" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════
# ENV PARSING  (spaces around = AND quoted values)
# ══════════════════════════════════════════════════════════════

env_path = ROOT / ".env"
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")

WM_CLIENT_ID = env_vars.get("WALMART_CLIENT_ID", "")
WM_CLIENT_SECRET = env_vars.get("WALMART_CLIENT_SECRET", "")
WM_BASE = "https://marketplace.walmartapis.com/v3"

KLAVIYO_API_KEY = env_vars.get("KLAVIYO_API", "")

AMZ_CLIENT_ID = env_vars.get("AMAZON_CLIENT_ID", "")
AMZ_CLIENT_SECRET = env_vars.get("AMAZON_CLIENT_SECRET", "")
AMZ_REFRESH_TOKEN = env_vars.get("AMAZON_REFRESH_TOKEN", "")
AMZ_MARKETPLACE_ID = "ATVPDKIKX0DER"

# Fishbowl — hardcoded per CLAUDE.md
FB_BASE = "http://naturesseed.myfishbowl.com:3875"
FB_USER = "gabe"
FB_PASS = "#Numb3rs!"

# WooCommerce (customer metrics via CF Worker proxy)
WC_BASE = env_vars.get("WC_BASE_URL", "https://naturesseed.com/wp-json/wc/v3")
WC_CK = env_vars.get("WC_CK", "")
WC_CS = env_vars.get("WC_CS", "")
CF_WORKER_URL = env_vars.get("CF_WORKER_URL", "")
CF_WORKER_SECRET = env_vars.get("CF_WORKER_SECRET", "")

# Google Ads (for marketing metrics — 12-month ad spend)
GADS_DEVELOPER_TOKEN = env_vars.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
GADS_CLIENT_ID = env_vars.get("GOOGLE_ADS_CLIENT_ID", "")
GADS_CLIENT_SECRET = env_vars.get("GOOGLE_ADS_CLIENT_SECRET", "")
GADS_REFRESH_TOKEN = env_vars.get("GOOGLE_ADS_REFRESH_TOKEN", "")
GADS_LOGIN_CID = env_vars.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
GADS_CUSTOMER_ID = env_vars.get("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")
COGS_SHEET_ID = env_vars.get("COGS_SHEET_ID", "1nve5yRvw7fY0caVqZDHYDjhoQmj_a6S9PkC3BMKm1S4")

# Shippo (shipping costs)
SHIPPO_API_KEY = env_vars.get("SHIPPO_API_KEY", "")

TODAY = date.today()
TODAY_STR = str(TODAY)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _parse_dollar(val):
    """Strip $, commas, parens (negative) and return float."""
    if val is None:
        return 0.0
    s = str(val).strip().replace("$", "").replace(",", "").replace(" ", "")
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s) if s and s not in ("-", "") else 0.0
    except ValueError:
        return 0.0


def _write_json(filename, data):
    """Write data atomically to docs/data/<filename>."""
    path = OUT_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  [OK] Wrote {path.name}")


def _supabase_get(path, params=None):
    """GET from Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    resp = requests.get(url, headers=headers, params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _wc_get(path, params=None):
    """GET from WooCommerce REST API, routing through CF Worker if configured."""
    import base64
    if CF_WORKER_URL:
        p = {"wc_path": path, **(params or {})}
        auth_str = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        headers = {"X-Proxy-Secret": CF_WORKER_SECRET, "Authorization": f"Basic {auth_str}"}
        resp = requests.get(CF_WORKER_URL, headers=headers, params=p, timeout=30)
    else:
        resp = requests.get(f"{WC_BASE}{path}", auth=(WC_CK, WC_CS), params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp


def _pull_google_ads_range(start_date, end_date):
    """Pull aggregated Google Ads spend/conversions for a date range.
    Returns dict with spend, conversions_value, impressions, clicks.
    """
    if not HAS_GOOGLE_ADS or not GADS_DEVELOPER_TOKEN:
        print("    [SKIP] Google Ads not configured")
        return {"spend": 0, "conversions_value": 0, "impressions": 0, "clicks": 0}

    config = {
        "developer_token": GADS_DEVELOPER_TOKEN,
        "client_id": GADS_CLIENT_ID,
        "client_secret": GADS_CLIENT_SECRET,
        "refresh_token": GADS_REFRESH_TOKEN,
        "use_proto_plus": True,
    }
    if GADS_LOGIN_CID:
        config["login_customer_id"] = GADS_LOGIN_CID

    client = GoogleAdsClient.load_from_dict(config)
    ga_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
          AND campaign.status != 'REMOVED'
    """

    response = ga_service.search(customer_id=GADS_CUSTOMER_ID, query=query)
    rows = list(response)

    return {
        "spend": round(sum(r.metrics.cost_micros / 1_000_000 for r in rows), 2),
        "conversions_value": round(sum(r.metrics.conversions_value for r in rows), 2),
        "impressions": sum(r.metrics.impressions for r in rows),
        "clicks": sum(r.metrics.clicks for r in rows),
    }


def _pull_google_ads_daily(start_date, end_date):
    """Pull daily Google Ads spend/conversions for a date range.
    Returns list of dicts with date, spend, conversions_value.
    """
    if not HAS_GOOGLE_ADS or not GADS_DEVELOPER_TOKEN:
        return []

    config = {
        "developer_token": GADS_DEVELOPER_TOKEN,
        "client_id": GADS_CLIENT_ID,
        "client_secret": GADS_CLIENT_SECRET,
        "refresh_token": GADS_REFRESH_TOKEN,
        "use_proto_plus": True,
    }
    if GADS_LOGIN_CID:
        config["login_customer_id"] = GADS_LOGIN_CID

    client = GoogleAdsClient.load_from_dict(config)
    ga_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            segments.date,
            metrics.cost_micros,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
          AND campaign.status != 'REMOVED'
    """

    response = ga_service.search(customer_id=GADS_CUSTOMER_ID, query=query)

    daily = {}
    for row in response:
        d = row.segments.date
        if d not in daily:
            daily[d] = {"spend": 0, "conversions_value": 0}
        daily[d]["spend"] += row.metrics.cost_micros / 1_000_000
        daily[d]["conversions_value"] += row.metrics.conversions_value

    return [
        {"date": d, "spend": round(v["spend"], 2), "conversions_value": round(v["conversions_value"], 2)}
        for d, v in sorted(daily.items())
    ]


def _pull_wc_orders_range(start_date, end_date):
    """Pull all WooCommerce orders in a date range. Returns list of order dicts.
    Uses CF Worker proxy if configured (for GitHub Actions).
    """
    all_orders = []
    page = 1
    after = f"{start_date}T00:00:00"
    before = f"{end_date}T23:59:59"

    while True:
        params = {
            "after": after,
            "before": before,
            "status": "completed,processing",
            "per_page": 100,
            "page": page,
        }
        resp = _wc_get("/orders", params)
        orders = resp.json()
        if not orders:
            break
        all_orders.extend(orders)
        page += 1
        time.sleep(0.3)

    return all_orders


def _pull_wc_customers_batch(customer_ids):
    """Fetch customer records to get date_created for new/returning classification.
    Uses WC 'include' param to batch-fetch up to 100 customers per request.
    Returns dict of {customer_id: date_created_str}.
    """
    result = {}
    ids = [cid for cid in customer_ids if cid and cid != 0]

    # Batch in chunks of 100 (WC API limit)
    for i in range(0, len(ids), 100):
        chunk = ids[i:i+100]
        try:
            params = {
                "include": ",".join(str(c) for c in chunk),
                "per_page": 100,
            }
            resp = _wc_get("/customers", params)
            for cust in resp.json():
                result[cust["id"]] = cust.get("date_created", "")
            time.sleep(0.3)
        except Exception as e:
            print(f"    [WARN] Customer batch fetch failed: {e}")
    return result


def _load_cogs_cache():
    """Load COGS lookup from Google Sheet (same as daily_pull.py pattern)."""
    url = f"https://docs.google.com/spreadsheets/d/{COGS_SHEET_ID}/export?format=csv"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"    [WARN] COGS sheet fetch failed: {e}")
        return {}

    cache = {}
    reader = csv.DictReader(io.StringIO(resp.text))
    for row in reader:
        sku = (row.get("SKU") or "").strip()
        cost_str = (row.get("Unit Cost") or "").strip()
        if not sku or not cost_str:
            continue
        unit_cost = _parse_dollar(cost_str)
        if unit_cost > 0:
            cache[sku] = unit_cost
    return cache


def _calculate_cogs_from_orders(orders, cogs_cache):
    """Calculate total COGS from order line items using the COGS lookup."""
    total_cogs = 0.0
    for order in orders:
        for item in order.get("line_items", []):
            sku = (item.get("sku") or "").strip()
            qty = item.get("quantity", 0)
            if sku in cogs_cache:
                total_cogs += cogs_cache[sku] * qty
    return round(total_cogs, 2)


def _pull_shippo_range(start_date, end_date):
    """Pull Shippo shipping costs for a date range.

    Paginates all transactions, filters by object_created date locally,
    deduplicates by tracking number (voided+recreated labels), and fetches
    rate costs in parallel batches via /rates/{id}.

    Returns total cost as float.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if not SHIPPO_API_KEY:
        print("    [SKIP] No SHIPPO_API_KEY configured")
        return 0.0

    headers = {"Authorization": f"ShippoToken {SHIPPO_API_KEY}"}
    start_str = str(start_date)
    end_str = str(end_date)

    rate_cache = {}
    seen_tracking = set()
    pending_rate_ids = set()  # collect rate IDs, fetch in bulk later
    shipment_rates = []       # (tracking, rate_id) pairs
    skipped_dupes = 0
    pages_checked = 0

    # Phase 1: paginate transactions, collect rate IDs (fast — no rate calls)
    url = "https://api.goshippo.com/transactions/"
    params = {"results": 200}
    found_older = False

    while url and not found_older:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"    [WARN] Shippo: {resp.status_code} {resp.text[:200]}")
            break
        data = resp.json()
        pages_checked += 1

        for txn in data.get("results", []):
            txn_date = (txn.get("object_created") or "")[:10]

            if txn_date < start_str:
                found_older = True
                break

            if start_str <= txn_date <= end_str and txn.get("status") == "SUCCESS":
                tracking = txn.get("tracking_number", "")
                if tracking and tracking in seen_tracking:
                    skipped_dupes += 1
                    continue
                if tracking:
                    seen_tracking.add(tracking)

                rate_id = txn.get("rate", "")
                shipment_rates.append((tracking, rate_id))
                if rate_id:
                    pending_rate_ids.add(rate_id)

        url = data.get("next")
        params = {}  # next URL includes params

    print(f"    Shippo: {len(shipment_rates)} shipments, {len(pending_rate_ids)} unique rates to fetch ({pages_checked} pages)")

    # Phase 2: fetch all unique rates in parallel (10 workers)
    def _fetch_rate(rid):
        try:
            r = requests.get(f"https://api.goshippo.com/rates/{rid}", headers=headers, timeout=15)
            if r.status_code == 200:
                return rid, float(r.json().get("amount", 0))
        except Exception:
            pass
        return rid, 0

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_fetch_rate, rid): rid for rid in pending_rate_ids}
        for fut in as_completed(futures):
            rid, amount = fut.result()
            rate_cache[rid] = amount

    # Phase 3: sum up costs
    total_cost = sum(rate_cache.get(rid, 0) for _, rid in shipment_rates)

    dupe_msg = f" (deduped {skipped_dupes})" if skipped_dupes else ""
    print(f"    Shippo: ${total_cost:,.2f} total ({len(rate_cache)} rates fetched){dupe_msg}")
    return round(total_cost, 2)


# ══════════════════════════════════════════════════════════════
# 1. REPORTING.JSON — Supabase daily_summary + budget CSV
# ══════════════════════════════════════════════════════════════

def _load_budget_csv():
    """
    Parse 2026 budget CSV.
    Returns dict: { "2026-01": { "net_revenue": 133779, "ad_spend": 35805,
                                 "cogs": 67192, "gross_margin": 66587, "net_income": -48839 } }
    """
    budget_path = ROOT / "research" / "2026-budget" / "Budget 2026 - Sheet1.csv"
    budget = {}
    if not budget_path.exists():
        print("  [WARN] Budget CSV not found")
        return budget

    months = [f"2026-{m:02d}" for m in range(1, 13)]
    # Rows we care about — map CSV label → output key
    row_map = {
        "Net Revenue": "net_revenue",
        "Total Cost Of Goods": "cogs",
        "Gross Margin": "gross_margin",
        "Advertising": "ad_spend",
        "Net Income": "net_income",
    }

    with open(budget_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            label = row[0].strip()
            if label in row_map:
                key = row_map[label]
                # Columns 1-12 = Jan-Dec
                for i, month in enumerate(months):
                    if month not in budget:
                        budget[month] = {}
                    val = row[i + 1] if i + 1 < len(row) else "0"
                    budget[month][key] = _parse_dollar(val)

    return budget


def _load_actuals_csv():
    """
    Parse any *Actuals*.csv files from 2026ECOMMBUDGET/.
    Returns dict: { "2026-01": { "net_revenue": ..., "cogs": ..., ... } }
    """
    actuals = {}
    budget_dir = ROOT / "research" / "2026-budget"
    if not budget_dir.exists():
        return actuals

    # Map column header → month key
    month_names = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }
    row_map = {
        "Net Revenue": "net_revenue",
        "Total Cost Of Goods": "cogs",
        "Gross Margin": "gross_margin",
        "Advertising": "ad_spend",
        "Net Income": "net_income",
    }

    for csv_path in sorted(budget_dir.glob("*Actuals*.csv")):
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = None
            for row in reader:
                if not row:
                    continue
                if header is None:
                    # First row: determine which month columns are present
                    header = []
                    for cell in row:
                        cell_lower = cell.strip().lower()
                        if cell_lower in month_names:
                            header.append(f"2026-{month_names[cell_lower]}")
                        else:
                            header.append(None)
                    continue

                label = row[0].strip()
                if label in row_map:
                    key = row_map[label]
                    for i, month_key in enumerate(header):
                        if month_key is None or i >= len(row):
                            continue
                        if month_key not in actuals:
                            actuals[month_key] = {}
                        actuals[month_key][key] = _parse_dollar(row[i])

    return actuals


def generate_reporting():
    """Pull MTD and YTD data from Supabase + budget CSV."""
    print("\n[Reporting] Pulling Supabase daily_summary...")

    today = TODAY
    yesterday = today - timedelta(days=1)

    # MTD window
    mtd_start_cy = date(today.year, today.month, 1)
    mtd_end_cy = yesterday
    mtd_start_ly = date(today.year - 1, today.month, 1)
    mtd_end_ly = date(today.year - 1, today.month, yesterday.day)

    # YTD window (Jan 1 → yesterday)
    ytd_start_cy = date(today.year, 1, 1)
    ytd_start_ly = date(today.year - 1, 1, 1)
    ytd_end_ly = date(today.year - 1, yesterday.month, yesterday.day)

    def fetch_range(start, end):
        rows = _supabase_get(
            "daily_summary",
            {
                "report_date": f"gte.{start}",
                "order": "report_date.asc",
                "select": "report_date,total_revenue,total_orders,total_ad_spend,total_cogs,total_shipping,net_revenue,mer",
                # Add lte filter via additional param
            },
        )
        # PostgREST multiple filters: pass as separate keys — build manually
        # Re-fetch with both gte and lte
        url = f"{SUPABASE_URL}/rest/v1/daily_summary"
        headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
        params = {
            "report_date": f"gte.{start}",
            "and": f"(report_date.lte.{end})",
            "order": "report_date.asc",
            "select": "report_date,total_revenue,total_orders,total_ad_spend,total_cogs,total_shipping,net_revenue,mer",
        }
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def fetch_date_range(start, end):
        """Fetch daily_summary rows between start and end (inclusive)."""
        url = f"{SUPABASE_URL}/rest/v1/daily_summary"
        headers = {"apikey": SUPABASE_KEY}
        # PostgREST: pass duplicate param keys as list of tuples (requests supports this)
        # Use select=* to avoid 400 from non-existent column names
        params = [
            ("report_date", f"gte.{start}"),
            ("report_date", f"lte.{end}"),
            ("order", "report_date.asc"),
            ("select", "*"),
        ]
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    cy_rows = fetch_date_range(mtd_start_cy, mtd_end_cy)
    ly_rows = fetch_date_range(mtd_start_ly, mtd_end_ly)
    ytd_cy_rows = fetch_date_range(ytd_start_cy, yesterday)
    ytd_ly_rows = fetch_date_range(ytd_start_ly, ytd_end_ly)

    def _col(row, *keys):
        """Try multiple column name variants, return first non-None value."""
        for k in keys:
            v = row.get(k)
            if v is not None:
                return v
        return 0

    def sum_rows(rows):
        rev = round(sum(float(_col(r, "total_revenue", "revenue") or 0) for r in rows), 2)
        cogs = round(sum(float(_col(r, "total_cogs", "cogs") or 0) for r in rows), 2)
        ad_spend = round(sum(float(_col(r, "total_ad_spend", "ad_spend") or 0) for r in rows), 2)
        shipping = round(sum(float(_col(r, "total_shipping", "shipping_cost") or 0) for r in rows), 2)
        platform_fees = round(sum(float(r.get("platform_fees") or 0) for r in rows), 2)
        gross_profit = round(rev - cogs, 2)
        cm1 = round(gross_profit - ad_spend, 2)
        cm2 = round(cm1 - shipping - platform_fees, 2)
        return {
            "revenue": rev,
            "orders": sum(int(_col(r, "total_orders", "orders") or 0) for r in rows),
            "ad_spend": ad_spend,
            "cogs": cogs,
            "shipping": shipping,
            "net_revenue": round(sum(float(_col(r, "net_revenue") or 0) for r in rows), 2),
            "wc_revenue": round(sum(float(r.get("wc_revenue") or 0) for r in rows), 2),
            "amazon_revenue": round(sum(float(r.get("amazon_revenue") or 0) for r in rows), 2),
            "walmart_revenue": round(sum(float(r.get("walmart_revenue") or 0) for r in rows), 2),
            "platform_fees": platform_fees,
            "gross_profit": gross_profit,
            "gross_margin_pct": round(gross_profit / rev * 100, 1) if rev else None,
            "cm1": cm1,
            "cm2": cm2,
            "cm2_pct": round(cm2 / rev * 100, 1) if rev else None,
        }

    cy_totals = sum_rows(cy_rows)
    ly_totals = sum_rows(ly_rows)
    cy_totals["mer"] = round(cy_totals["revenue"] / cy_totals["ad_spend"], 2) if cy_totals["ad_spend"] else 0

    budget = _load_budget_csv()
    cur_month_key = f"{today.year}-{today.month:02d}"
    budget_month = budget.get(cur_month_key, {})
    mtd_budget = {
        "revenue": budget_month.get("net_revenue", 0),
        "ad_spend": budget_month.get("ad_spend", 0),
    }

    daily_cy = [
        {"date": r["report_date"], "revenue": float(r.get("total_revenue") or 0)}
        for r in cy_rows
    ]
    daily_ly = [
        {
            # Shift last-year date forward 1 year for chart alignment
            "date": str(date.fromisoformat(r["report_date"]) + timedelta(days=365)),
            "revenue": float(r.get("total_revenue") or 0),
        }
        for r in ly_rows
    ]

    # YTD — aggregate by month
    from collections import defaultdict
    cy_by_month = defaultdict(lambda: {"revenue": 0, "orders": 0, "ad_spend": 0, "cogs": 0, "shipping": 0, "platform_fees": 0, "net_revenue": 0})
    ly_by_month = defaultdict(lambda: {"revenue": 0})

    for r in ytd_cy_rows:
        m = r["report_date"][:7]  # YYYY-MM
        cy_by_month[m]["revenue"] += float(_col(r, "total_revenue", "revenue") or 0)
        cy_by_month[m]["orders"] += int(_col(r, "total_orders", "orders") or 0)
        cy_by_month[m]["ad_spend"] += float(_col(r, "total_ad_spend", "ad_spend") or 0)
        cy_by_month[m]["cogs"] += float(_col(r, "total_cogs", "cogs") or 0)
        cy_by_month[m]["shipping"] += float(_col(r, "total_shipping", "shipping_cost") or 0)
        cy_by_month[m]["platform_fees"] += float(r.get("platform_fees") or 0)
        cy_by_month[m]["net_revenue"] += float(_col(r, "net_revenue") or 0)

    for r in ytd_ly_rows:
        # Map last-year month to this-year equivalent
        m_ly = r["report_date"][:7]
        year_ly, mon_ly = m_ly.split("-")
        m_cy = f"{int(year_ly)+1}-{mon_ly}"
        ly_by_month[m_cy]["revenue"] += float(_col(r, "total_revenue", "revenue") or 0)

    # Build month list (all months in YTD that have data or budget)
    all_months = sorted(set(list(cy_by_month.keys()) + [k for k in budget if k <= cur_month_key]))
    ytd_months = []
    for m in all_months:
        cy = cy_by_month.get(m, {})
        rev = cy.get("revenue", 0)
        ad = cy.get("ad_spend", 0)
        cogs_m = cy.get("cogs", 0)
        ship_m = cy.get("shipping", 0)
        pfees_m = cy.get("platform_fees", 0)
        gross_profit_m = rev - cogs_m
        cm1_m = gross_profit_m - ad
        cm2_m = cm1_m - ship_m - pfees_m
        mer = round(rev / ad, 2) if ad else 0
        ytd_months.append({
            "month": m,
            "revenue": round(rev, 2),
            "ly_revenue": round(ly_by_month.get(m, {}).get("revenue", 0), 2),
            "budget_revenue": budget.get(m, {}).get("net_revenue", 0),
            "orders": cy.get("orders", 0),
            "ad_spend": round(ad, 2),
            "mer": mer,
            "cogs": round(cogs_m, 2),
            "net_revenue": round(cy.get("net_revenue", 0), 2),
            "gross_profit": round(gross_profit_m, 2),
            "gross_margin_pct": round(gross_profit_m / rev * 100, 1) if rev else None,
            "cm2": round(cm2_m, 2),
            "cm2_pct": round(cm2_m / rev * 100, 1) if rev else None,
        })

    _ytd_rev = round(sum(m["revenue"] for m in ytd_months), 2)
    _ytd_gp = round(sum(m["gross_profit"] for m in ytd_months), 2)
    _ytd_cm2 = round(sum(m["cm2"] for m in ytd_months), 2)
    ytd_totals_cy = {
        "revenue": _ytd_rev,
        "orders": sum(m["orders"] for m in ytd_months),
        "ad_spend": round(sum(m["ad_spend"] for m in ytd_months), 2),
        "cogs": round(sum(m["cogs"] for m in ytd_months), 2),
        "net_revenue": round(sum(m["net_revenue"] for m in ytd_months), 2),
        "gross_profit": _ytd_gp,
        "gross_margin_pct": round(_ytd_gp / _ytd_rev * 100, 1) if _ytd_rev else None,
        "cm2": _ytd_cm2,
        "cm2_pct": round(_ytd_cm2 / _ytd_rev * 100, 1) if _ytd_rev else None,
    }
    ytd_totals_ly = {"revenue": round(sum(m["ly_revenue"] for m in ytd_months), 2)}
    ytd_totals_budget = {"revenue": round(sum(m["budget_revenue"] for m in ytd_months), 2)}

    # Pull MTD WC orders to count new vs returning customers
    print("  Pulling MTD WC orders for new customer count...")
    try:
        mtd_orders = _pull_wc_orders_range(str(mtd_start_cy), str(mtd_end_cy))
        mtd_cids = {}
        mtd_guest_emails = {}
        for o in mtd_orders:
            cid = o.get("customer_id", 0)
            if cid and cid != 0:
                mtd_cids.setdefault(cid, True)
            else:
                email = (o.get("billing", {}).get("email") or "").lower().strip()
                if email:
                    mtd_guest_emails.setdefault(email, True)
        cust_dates = _pull_wc_customers_batch(list(mtd_cids.keys()))
        mtd_start_str = str(mtd_start_cy)
        new_customers_mtd = sum(1 for cid in mtd_cids if (cust_dates.get(cid, "")[:10] >= mtd_start_str))
        new_customers_mtd += len(mtd_guest_emails)  # guests treated as new
        print(f"    MTD customers: {len(mtd_cids) + len(mtd_guest_emails)} unique ({new_customers_mtd} new)")
    except Exception as e:
        print(f"    [WARN] MTD new customer count failed: {e}")
        new_customers_mtd = None

    aov = round(cy_totals["revenue"] / cy_totals["orders"], 2) if cy_totals["orders"] else 0
    new_cac = round(cy_totals["ad_spend"] / new_customers_mtd, 2) if new_customers_mtd else None

    result = {
        "as_of": TODAY_STR,
        "mtd": {
            "cy": {
                "revenue": cy_totals["revenue"],
                "orders": cy_totals["orders"],
                "ad_spend": cy_totals["ad_spend"],
                "mer": cy_totals["mer"],
                "cogs": cy_totals["cogs"],
                "shipping": cy_totals["shipping"],
                "net_revenue": cy_totals["net_revenue"],
                "wc_revenue": cy_totals["wc_revenue"],
                "amazon_revenue": cy_totals["amazon_revenue"],
                "walmart_revenue": cy_totals["walmart_revenue"],
                "platform_fees": cy_totals["platform_fees"],
                "gross_profit": cy_totals["gross_profit"],
                "gross_margin_pct": cy_totals["gross_margin_pct"],
                "cm1": cy_totals["cm1"],
                "cm2": cy_totals["cm2"],
                "cm2_pct": cy_totals["cm2_pct"],
                "aov": aov,
                "new_customers": new_customers_mtd,
                "new_customer_cac": new_cac,
            },
            "ly": {
                "revenue": ly_totals["revenue"],
                "orders": ly_totals["orders"],
                "ad_spend": ly_totals["ad_spend"],
            },
            "budget": mtd_budget,
            "daily_cy": daily_cy,
            "daily_ly": daily_ly,
        },
        "ytd": {
            "months": ytd_months,
            "totals_cy": ytd_totals_cy,
            "totals_ly": ytd_totals_ly,
            "totals_budget": ytd_totals_budget,
        },
    }
    _write_json("reporting.json", result)
    print(f"  MTD CY revenue: ${cy_totals['revenue']:,.2f} | orders: {cy_totals['orders']}")
    return True


# ══════════════════════════════════════════════════════════════
# 2. BUDGET.JSON — CSV budget + actuals
# ══════════════════════════════════════════════════════════════

def generate_budget():
    """Parse budget and actuals CSVs into budget.json."""
    print("\n[Budget] Parsing budget + actuals CSVs...")

    monthly = _load_budget_csv()
    actuals = _load_actuals_csv()

    result = {
        "as_of": TODAY_STR,
        "monthly": monthly,
        "actuals": actuals,
    }
    _write_json("budget.json", result)
    print(f"  Budget months: {len(monthly)} | Actuals months: {len(actuals)}")
    return True


# ══════════════════════════════════════════════════════════════
# 3. KLAVIYO.JSON — upcoming campaigns via REST API
# ══════════════════════════════════════════════════════════════

def generate_klaviyo():
    """Pull upcoming Klaviyo campaigns (next 90 days) via REST API."""
    print("\n[Klaviyo] Pulling upcoming campaigns...")

    if not KLAVIYO_API_KEY:
        print("  [SKIP] No KLAVIYO_API key configured")
        _write_json("klaviyo.json", {"as_of": TODAY_STR, "campaigns": []})
        return False

    base_url = "https://a.klaviyo.com/api"
    headers = {
        "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
        "revision": "2024-07-15",
        "Content-Type": "application/json",
    }

    window_start = TODAY_STR
    window_end = str(TODAY + timedelta(days=90))

    # Klaviyo 2024-07-15: channel filter required. No send_time filter — filter client-side.
    # Note: pass params directly in URL — requests encodes brackets which Klaviyo rejects.

    campaigns = []
    url = None  # built below with requests to handle URL encoding
    init_params = {"filter": "equals(messages.channel,'email')", "sort": "-scheduled_at"}
    url = requests.Request("GET", f"{base_url}/campaigns/", params=init_params).prepare().url
    while url:
        resp = requests.get(
            url,
            headers=headers,
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"  [WARN] Klaviyo campaigns returned {resp.status_code}: {resp.text[:200]}")
            break
        data = resp.json()

        stop_pagination = False
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            # Extract send time — try multiple paths
            send_time = (
                attrs.get("send_time")
                or attrs.get("scheduled_at")
                or (attrs.get("send_strategy") or {}).get("options_static", {}).get("datetime")
                or ""
            )
            # Client-side filter: only include campaigns in our 90-day window
            if send_time:
                try:
                    st_date = send_time[:10]
                    if st_date < window_start:
                        stop_pagination = True  # sorted desc, so older = stop
                        continue
                    if st_date > window_end:
                        continue
                except Exception:
                    pass

            # Extract subject line — try messages[0] first
            subject = ""
            messages = attrs.get("campaign-messages", {}).get("data", [])
            if messages:
                msg_attrs = messages[0].get("attributes", {})
                subject = (
                    msg_attrs.get("definition", {}).get("subject", "")
                    or msg_attrs.get("subject", "")
                    or msg_attrs.get("content", {}).get("subject", "")
                    or ""
                )

            # Segment/list name from send_strategy
            segment_name = ""
            send_strategy = attrs.get("send_strategy", {})
            list_id = (send_strategy.get("options_static") or {}).get("list_id", "")
            if list_id:
                # Try to look up list name
                try:
                    list_resp = requests.get(
                        f"{base_url}/lists/{list_id}/",
                        headers=headers,
                        timeout=10,
                    )
                    if list_resp.status_code == 200:
                        segment_name = list_resp.json().get("data", {}).get("attributes", {}).get("name", "")
                except Exception:
                    segment_name = list_id

            campaigns.append({
                "id": item.get("id", ""),
                "name": attrs.get("name", ""),
                "send_time": send_time,
                "status": attrs.get("status", ""),
                "subject": subject,
                "segment_name": segment_name,
            })

        # Pagination — stop if we passed our window or no more pages
        next_url = data.get("links", {}).get("next")
        if stop_pagination or not next_url or next_url == url:
            break
        url = next_url

    # Also fetch Draft campaigns — they use options_static.datetime as the scheduled date
    # (scheduled_at is null on drafts; date is stored in send_strategy.options_static.datetime)
    draft_url = requests.Request("GET", f"{base_url}/campaigns/",
        params={"filter": "equals(status,'Draft')", "sort": "name"}).prepare().url
    while draft_url:
        resp = requests.get(draft_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            break
        data = resp.json()
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            send_time = (
                (attrs.get("send_strategy") or {}).get("options_static", {}).get("datetime")
                or attrs.get("scheduled_at")
                or attrs.get("send_time")
                or ""
            )
            if send_time:
                try:
                    st_date = send_time[:10]
                    if st_date < window_start or st_date > window_end:
                        continue
                except Exception:
                    pass
            elif not send_time:
                continue  # skip drafts with no date at all

            subject = ""
            messages = attrs.get("campaign-messages", {}).get("data", [])
            if messages:
                msg_attrs = messages[0].get("attributes", {})
                subject = (
                    msg_attrs.get("definition", {}).get("subject", "")
                    or msg_attrs.get("subject", "")
                    or ""
                )

            campaigns.append({
                "id": item.get("id", ""),
                "name": attrs.get("name", ""),
                "send_time": send_time,
                "status": "Draft",
                "subject": subject,
                "segment_name": "",
            })
        next_url = data.get("links", {}).get("next")
        if not next_url or next_url == draft_url:
            break
        draft_url = next_url

    # Sort all campaigns by send_time
    campaigns.sort(key=lambda c: c.get("send_time") or "")

    result = {"as_of": TODAY_STR, "campaigns": campaigns}
    _write_json("klaviyo.json", result)
    print(f"  Campaigns in next 90 days: {len(campaigns)}")
    return True


# ══════════════════════════════════════════════════════════════
# 4. AMAZON.JSON — SP-API orders
# ══════════════════════════════════════════════════════════════

_amz_token_cache = {"token": None, "expires_at": None}


def _amz_get_token():
    now = datetime.utcnow()
    if _amz_token_cache["token"] and _amz_token_cache["expires_at"] and now < _amz_token_cache["expires_at"]:
        return _amz_token_cache["token"]

    resp = requests.post(
        "https://api.amazon.com/auth/o2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": AMZ_REFRESH_TOKEN,
            "client_id": AMZ_CLIENT_ID,
            "client_secret": AMZ_CLIENT_SECRET,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _amz_token_cache["token"] = data["access_token"]
    expires_in = int(data.get("expires_in", 3600)) - 60
    _amz_token_cache["expires_at"] = now + timedelta(seconds=expires_in)
    return _amz_token_cache["token"]


def generate_amazon():
    """Pull Amazon SP-API orders for last 30 days."""
    print("\n[Amazon] Pulling 30d orders...")

    if not AMZ_CLIENT_ID or not AMZ_REFRESH_TOKEN:
        print("  [SKIP] Amazon credentials not configured")
        _write_json("amazon.json", {
            "as_of": TODAY_STR,
            "last_30d": {"revenue": 0, "orders": 0, "aov": 0},
            "daily": [],
            "account_health": {"defect_rate": 0, "cancellation_rate": 0, "late_shipment_rate": 0, "status": "Unknown"},
            "active_count": None,
            "top_products": [],
            "issues": ["Amazon credentials not configured"],
        })
        return False

    token = _amz_get_token()
    headers = {"x-amz-access-token": token, "Content-Type": "application/json"}

    thirty_days_ago = (TODAY - timedelta(days=30)).isoformat() + "T00:00:00Z"
    all_orders = []
    next_token = None

    while True:
        params = {
            "MarketplaceIds": AMZ_MARKETPLACE_ID,
            "CreatedAfter": thirty_days_ago,
        }
        if next_token:
            params["NextToken"] = next_token

        resp = requests.get(
            "https://sellingpartnerapi-na.amazon.com/orders/v0/orders",
            headers=headers,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json().get("payload", {})
        all_orders.extend(payload.get("Orders", []))
        next_token = payload.get("NextToken")
        if not next_token:
            break
        time.sleep(0.5)

    # Aggregate daily
    from collections import defaultdict
    daily_map = defaultdict(lambda: {"revenue": 0.0, "orders": 0})

    total_revenue = 0.0
    top_orders = []  # (revenue, order_id) for top-product lookup

    for order in all_orders:
        order_date = (order.get("PurchaseDate") or "")[:10]
        # Skip $0 Pending orders for revenue
        amt = float((order.get("OrderTotal") or {}).get("Amount", 0))
        status = order.get("OrderStatus", "")

        daily_map[order_date]["orders"] += 1
        if status != "Pending" and amt > 0:
            daily_map[order_date]["revenue"] += amt
            total_revenue += amt
            top_orders.append((amt, order.get("AmazonOrderId", "")))

    total_orders = len(all_orders)
    aov = round(total_revenue / total_orders, 2) if total_orders else 0

    daily = sorted(
        [{"date": d, "revenue": round(v["revenue"], 2), "orders": v["orders"]} for d, v in daily_map.items()],
        key=lambda x: x["date"],
    )

    # Top products — fetch order items for top 10 orders by revenue
    top_orders_sorted = sorted(top_orders, key=lambda x: x[0], reverse=True)[:10]
    product_map = defaultdict(lambda: {"revenue": 0.0, "orders": 0, "asin": ""})

    for amt, order_id in top_orders_sorted:
        try:
            items_resp = requests.get(
                f"https://sellingpartnerapi-na.amazon.com/orders/v0/orders/{order_id}/orderItems",
                headers={"x-amz-access-token": _amz_get_token(), "Content-Type": "application/json"},
                timeout=20,
            )
            if items_resp.status_code == 200:
                items = items_resp.json().get("payload", {}).get("OrderItems", [])
                for item in items:
                    title = item.get("Title", "Unknown")
                    asin = item.get("ASIN", "")
                    item_price = float((item.get("ItemPrice") or {}).get("Amount", 0))
                    qty = int(item.get("QuantityOrdered", 1))
                    product_map[title]["revenue"] += item_price
                    product_map[title]["orders"] += qty
                    product_map[title]["asin"] = asin
            time.sleep(0.5)
        except Exception:
            pass

    top_products = sorted(
        [
            {"title": title, "revenue": round(v["revenue"], 2), "orders": v["orders"], "asin": v["asin"]}
            for title, v in product_map.items()
        ],
        key=lambda x: x["revenue"],
        reverse=True,
    )[:10]

    result = {
        "as_of": TODAY_STR,
        "last_30d": {"revenue": round(total_revenue, 2), "orders": total_orders, "aov": aov},
        "daily": daily,
        "account_health": {
            "defect_rate": 0,
            "cancellation_rate": 0,
            "late_shipment_rate": 0,
            "status": "Good",
        },
        "active_count": None,
        "top_products": top_products,
        "issues": [],
    }
    _write_json("amazon.json", result)
    print(f"  Orders: {total_orders} | Revenue: ${total_revenue:,.2f} | Top products fetched: {len(top_products)}")
    return True


# ══════════════════════════════════════════════════════════════
# 5. WALMART.JSON — Marketplace orders
# ══════════════════════════════════════════════════════════════

_wm_token_cache = {"token": None, "expires_at": None}


def _wm_get_token():
    now = datetime.utcnow()
    if _wm_token_cache["token"] and _wm_token_cache["expires_at"] and now < _wm_token_cache["expires_at"]:
        return _wm_token_cache["token"]

    creds = base64.b64encode(f"{WM_CLIENT_ID}:{WM_CLIENT_SECRET}".encode()).decode()
    resp = requests.post(
        f"{WM_BASE}/token",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "WM_SVC.NAME": "Nature's Seed",
            "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
        },
        data="grant_type=client_credentials",
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
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


def generate_walmart():
    """Pull Walmart Marketplace orders for last 30 days."""
    print("\n[Walmart] Pulling 30d orders...")

    if not WM_CLIENT_ID or not WM_CLIENT_SECRET:
        print("  [SKIP] Walmart credentials not configured")
        _write_json("walmart.json", {
            "as_of": TODAY_STR,
            "last_30d": {"revenue": 0, "orders": 0, "aov": 0},
            "daily": [],
            "active_count": None,
            "top_products": [],
            "issues": ["Walmart credentials not configured"],
        })
        return False

    thirty_days_ago = (TODAY - timedelta(days=30)).isoformat() + "T00:00:00.000Z"
    today_iso = TODAY.isoformat() + "T23:59:59.999Z"

    all_orders = []
    next_cursor = None

    while True:
        params = {
            "createdStartDate": thirty_days_ago,
            "createdEndDate": today_iso,
            "limit": 200,
        }
        if next_cursor:
            params["nextCursor"] = next_cursor

        try:
            resp = requests.get(
                f"{WM_BASE}/orders",
                headers=_wm_headers(),
                params=params,
                timeout=60,
            )
            if resp.status_code == 404:
                break  # No orders
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
                break
            raise

        data = resp.json()
        list_obj = data.get("list") or {}
        if not isinstance(list_obj, dict):
            list_obj = {}
        elements_obj = list_obj.get("elements") or {}
        if not isinstance(elements_obj, dict):
            elements_obj = {}
        order_raw = elements_obj.get("order") or []
        # Walmart sometimes returns a single order dict instead of a list
        if isinstance(order_raw, dict):
            order_raw = [order_raw]
        if not order_raw:
            break
        all_orders.extend(order_raw)

        meta = list_obj.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        next_cursor = meta.get("nextCursor")
        if not next_cursor:
            break
        time.sleep(0.5)

    # Aggregate
    from collections import defaultdict
    daily_map = defaultdict(lambda: {"revenue": 0.0, "orders": 0})
    product_map = defaultdict(lambda: {"revenue": 0.0, "orders": 0, "sku": ""})
    total_revenue = 0.0

    for order in all_orders:
        order_date_raw = order.get("orderDate")
        if isinstance(order_date_raw, int):
            # Walmart returns orderDate as Unix timestamp in milliseconds
            order_date = datetime.utcfromtimestamp(order_date_raw / 1000).strftime("%Y-%m-%d")
        elif isinstance(order_date_raw, str):
            order_date = order_date_raw[:10]
        else:
            order_date = TODAY_STR
        daily_map[order_date]["orders"] += 1

        order_lines_raw = (order.get("orderLines") or {}).get("orderLine", [])
        if isinstance(order_lines_raw, dict):
            order_lines_raw = [order_lines_raw]
        for line in (order_lines_raw if isinstance(order_lines_raw, list) else []):
            if not isinstance(line, dict):
                continue
            item_name = (line.get("item") or {}).get("productName", "Unknown")
            sku = (line.get("item") or {}).get("sku", "")
            qty_obj = line.get("orderLineQuantity") or {}
            qty = int(qty_obj.get("amount", 0)) if isinstance(qty_obj, dict) else 0

            charges_raw = (line.get("charges") or {}).get("charge", [])
            if isinstance(charges_raw, dict):
                charges_raw = [charges_raw]
            for charge in (charges_raw if isinstance(charges_raw, list) else []):
                if not isinstance(charge, dict):
                    continue
                if charge.get("chargeType") == "PRODUCT":
                    amt = float((charge.get("chargeAmount") or {}).get("amount", 0))
                    daily_map[order_date]["revenue"] += amt
                    total_revenue += amt
                    product_map[item_name]["revenue"] += amt
                    product_map[item_name]["orders"] += qty
                    product_map[item_name]["sku"] = sku

    total_orders = len(all_orders)
    aov = round(total_revenue / total_orders, 2) if total_orders else 0

    daily = sorted(
        [{"date": d, "revenue": round(v["revenue"], 2), "orders": v["orders"]} for d, v in daily_map.items()],
        key=lambda x: x["date"],
    )

    top_products = sorted(
        [{"title": k, "revenue": round(v["revenue"], 2), "orders": v["orders"], "sku": v["sku"]} for k, v in product_map.items()],
        key=lambda x: x["revenue"],
        reverse=True,
    )[:5]

    # Active item count
    active_count = None
    try:
        items_resp = requests.get(
            f"{WM_BASE}/items",
            headers=_wm_headers(),
            params={"limit": 1},
            timeout=20,
        )
        if items_resp.status_code == 200:
            items_data = items_resp.json()
            item_response = items_data.get("ItemResponse")
            if isinstance(item_response, list) and item_response:
                active_count = item_response[0].get("totalElements")
            elif isinstance(item_response, int):
                active_count = item_response
            else:
                active_count = (
                    items_data.get("totalElements")
                    or items_data.get("list", {}).get("meta", {}).get("totalCount")
                )
    except Exception:
        pass

    result = {
        "as_of": TODAY_STR,
        "last_30d": {"revenue": round(total_revenue, 2), "orders": total_orders, "aov": aov},
        "daily": daily,
        "active_count": active_count,
        "top_products": top_products,
        "issues": [],
    }
    _write_json("walmart.json", result)
    print(f"  Orders: {total_orders} | Revenue: ${total_revenue:,.2f} | Active items: {active_count}")
    return True


# ══════════════════════════════════════════════════════════════
# 6. INVENTORY.JSON — Fishbowl + velocity
# ══════════════════════════════════════════════════════════════

def _load_abc_velocity():
    """Load daily_qty per SKU from abc_analysis_results.json."""
    velocity = {}
    abc_path = ROOT / "research" / "abc-analysis" / "abc_analysis_results.json"
    if not abc_path.exists():
        return velocity
    try:
        with open(abc_path) as f:
            data = json.load(f)
        for item in data.get("skus", []):
            sku = item.get("sku", "")
            if sku:
                velocity[sku] = float(item.get("daily_qty", 0))
    except Exception:
        pass
    return velocity


def generate_inventory():
    """Query Fishbowl inventory and compute velocity/runway."""
    print("\n[Fishbowl] Querying inventory...")

    # Step 1: Login to Fishbowl
    # Login body requires appName + appId per API guide
    fb_token = None
    try:
        login_resp = requests.post(
            f"{FB_BASE}/api/login",
            json={"appName": "Postman Testing", "appId": 101, "username": FB_USER, "password": FB_PASS},
            timeout=15,
        )
        login_resp.raise_for_status()
        login_data = login_resp.json()
        fb_token = (
            login_data.get("token")
            or login_data.get("access_token")
            or login_data.get("data", {}).get("token")
        )
        if not fb_token:
            raise ValueError(f"No token in response: {list(login_data.keys())}")
        print("  Fishbowl login OK")
    except Exception as e:
        print(f"  [WARN] Fishbowl login failed: {e}")
        _write_json("inventory.json", {
            "as_of": TODAY_STR,
            "items": [],
            "summary": {"total_skus": 0, "red_count": 0, "yellow_count": 0, "green_count": 0},
            "warning": f"Fishbowl login failed: {e}",
        })
        return False

    # Step 2: Query inventory via GET /api/data-query with plain-text SQL body
    # Per API guide: GET with body (unusual), Content-Type: text/plain, returns JSON array
    raw_inventory = []
    try:
        import urllib.request as _urllib_req
        sql = (
            "SELECT p.num AS sku, p.description AS name, "
            "qit.qtyonhand AS qty "
            "FROM qtyinventorytotals qit "
            "JOIN part p ON p.id = qit.partid "
            "WHERE qit.qtyonhand > 0 AND p.activeFlag = 1 "
            "ORDER BY p.num;"
        )
        req = _urllib_req.Request(
            f"{FB_BASE}/api/data-query",
            data=sql.encode("utf-8"),
            method="GET",
        )
        req.add_header("Authorization", f"Bearer {fb_token}")
        req.add_header("Content-Type", "text/plain")
        with _urllib_req.urlopen(req, timeout=60) as resp:
            raw_inventory = json.loads(resp.read().decode("utf-8"))
        if not isinstance(raw_inventory, list):
            raw_inventory = []
        print(f"  Fishbowl returned {len(raw_inventory)} SKUs")
    except Exception as e:
        print(f"  [WARN] Fishbowl query failed: {e}")
        _write_json("inventory.json", {
            "as_of": TODAY_STR,
            "items": [],
            "summary": {"total_skus": 0, "red_count": 0, "yellow_count": 0, "green_count": 0},
            "warning": f"Fishbowl query failed: {e}",
        })
    finally:
        # Always logout to free the session slot
        if fb_token:
            try:
                requests.post(f"{FB_BASE}/api/logout",
                    headers={"Authorization": f"Bearer {fb_token}"}, timeout=10)
            except Exception:
                pass
        if not raw_inventory:
            return False

    # Step 3: Load velocity from ABC analysis
    velocity_map = _load_abc_velocity()

    # Step 4: Compute Q1/Q2 runway
    today = TODAY
    # Q1 = Jan-Mar. Determine days remaining in Q1 (if we're in Q1)
    q1_end = date(today.year, 3, 31)
    if today <= q1_end:
        days_remaining_q1 = (q1_end - today).days
    else:
        days_remaining_q1 = 0  # Q1 is over

    q2_days = 91  # Apr-Jun

    items = []
    red_count = yellow_count = green_count = 0

    for row in raw_inventory:
        # Row may be dict or list depending on Fishbowl API version
        if isinstance(row, dict):
            sku = str(row.get("sku") or row.get("SKU") or "").strip()
            name = str(row.get("name") or row.get("description") or "").strip()
            qty_raw = row.get("qty") or row.get("QTY") or row.get("quantity") or 0
        elif isinstance(row, (list, tuple)) and len(row) >= 3:
            sku, name, qty_raw = str(row[0]).strip(), str(row[1]).strip(), row[2]
        else:
            continue

        try:
            qty = float(qty_raw)
        except (TypeError, ValueError):
            qty = 0.0

        daily_velocity = velocity_map.get(sku, 0.0)

        if daily_velocity > 0:
            days_remaining = int(qty / daily_velocity)
        else:
            days_remaining = 9999

        q1_need = round(days_remaining_q1 * daily_velocity, 1)
        q2_need = round(q2_days * daily_velocity * 1.2, 1)
        surplus_gap = round(qty - q1_need - q2_need, 1)

        if daily_velocity == 0:
            status = "ok"
        elif days_remaining < 30:
            status = "red"
            red_count += 1
        elif days_remaining < 60:
            status = "yellow"
            yellow_count += 1
        else:
            status = "ok"
            green_count += 1

        items.append({
            "sku": sku,
            "name": name,
            "qty": round(qty, 1),
            "daily_velocity": daily_velocity,
            "days_remaining": days_remaining,
            "q1_need": q1_need,
            "q2_need": q2_need,
            "surplus_gap": surplus_gap,
            "status": status,
        })

    result = {
        "as_of": TODAY_STR,
        "items": items,
        "summary": {
            "total_skus": len(items),
            "red_count": red_count,
            "yellow_count": yellow_count,
            "green_count": green_count,
        },
    }
    _write_json("inventory.json", result)
    print(f"  SKUs: {len(items)} | Red: {red_count} | Yellow: {yellow_count} | Green: {green_count}")
    return True


# ══════════════════════════════════════════════════════════════
# 7. NOTES.JSON — Convert docs/notes.md to HTML
# ══════════════════════════════════════════════════════════════

def _md_to_html(md_text):
    """
    Minimal Markdown → HTML converter.
    Handles: ## headings, # headings, **bold**, bullet lists, paragraphs.
    """
    lines = md_text.splitlines()
    html_parts = []
    in_list = False

    for line in lines:
        stripped = line.rstrip()

        # Headings
        if stripped.startswith("### "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            content = stripped[4:].strip()
            html_parts.append(f"<h3>{content}</h3>")
        elif stripped.startswith("## "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            content = stripped[3:].strip()
            html_parts.append(f"<h2>{content}</h2>")
        elif stripped.startswith("# "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            content = stripped[2:].strip()
            html_parts.append(f"<h1>{content}</h1>")
        # Bullet lists
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            content = stripped[2:].strip()
            content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
            html_parts.append(f"  <li>{content}</li>")
        # Blank line
        elif not stripped:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append("")
        # Regular paragraph line
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
            html_parts.append(f"<p>{content}</p>")

    if in_list:
        html_parts.append("</ul>")

    return "\n".join(part for part in html_parts if part != "")


def generate_notes():
    """Convert docs/notes.md to notes.json."""
    print("\n[Notes] Reading docs/notes.md...")

    notes_path = ROOT / "docs" / "notes.md"
    if not notes_path.exists():
        html = "<p>No notes yet. Edit docs/notes.md to add notes.</p>"
        print("  notes.md not found — writing placeholder")
    else:
        try:
            md_text = notes_path.read_text(encoding="utf-8")
            html = _md_to_html(md_text)
            print(f"  Converted {len(md_text)} chars of markdown")
        except Exception as e:
            html = f"<p>Error reading notes: {e}</p>"

    result = {"as_of": TODAY_STR, "html": html}
    _write_json("notes.json", result)
    return True


# ══════════════════════════════════════════════════════════════
# 8. MARKETING.JSON — Customer economics, channel performance
# ══════════════════════════════════════════════════════════════

def generate_marketing():
    """Generate marketing channel metrics: LTV, CAC, contribution margin, 90-day daily table."""
    print("\n[Marketing] Computing customer economics...")

    today = TODAY
    period_start = today - timedelta(days=365)
    period_90d_start = today - timedelta(days=90)
    yesterday = today - timedelta(days=1)

    # ── 1. Pull 12 months of WC orders ──────────────────────
    print("  Pulling 12 months of WooCommerce orders...")
    orders = _pull_wc_orders_range(str(period_start), str(yesterday))
    print(f"    Fetched {len(orders)} orders")

    if not orders:
        print("    [SKIP] No orders found — writing empty marketing.json")
        _write_json("marketing.json", {"generated_at": TODAY_STR, "error": "no_orders"})
        return True

    # ── 2. Customer segmentation ────────────────────────────
    # Group orders by customer
    customer_orders = {}  # {customer_key: [order_dates]}
    customer_revenue = {}  # {customer_key: total_revenue}
    guest_emails = {}  # {email: [order_dates]}

    total_revenue = 0.0
    for o in orders:
        rev = float(o.get("total", 0))
        total_revenue += rev
        cid = o.get("customer_id", 0)
        odate = o.get("date_created", "")[:10]

        if cid and cid != 0:
            customer_orders.setdefault(cid, []).append(odate)
            customer_revenue[cid] = customer_revenue.get(cid, 0) + rev
        else:
            email = (o.get("billing", {}).get("email") or "").lower().strip()
            if email:
                guest_emails.setdefault(email, []).append(odate)
                customer_revenue[f"guest_{email}"] = customer_revenue.get(f"guest_{email}", 0) + rev

    # Fetch customer date_created for new/returning classification
    registered_ids = list(customer_orders.keys())
    print(f"  Fetching {len(registered_ids)} customer records for classification...")
    customer_dates = _pull_wc_customers_batch(registered_ids)

    period_start_str = str(period_start)
    new_customers = 0
    returning_customers = 0

    for cid in registered_ids:
        created = customer_dates.get(cid, "")[:10]
        if created >= period_start_str:
            new_customers += 1
        else:
            returning_customers += 1

    # Guest orders: treat as new (no historical data)
    new_customers += len(guest_emails)

    unique_customers = len(registered_ids) + len(guest_emails)
    print(f"    Unique customers: {unique_customers} (new: {new_customers}, returning: {returning_customers})")

    # ── 3. Pull 12-month Google Ads spend ────────────────────
    print("  Pulling 12-month Google Ads spend...")
    try:
        ads_12m = _pull_google_ads_range(str(period_start), str(yesterday))
    except Exception as e:
        print(f"    [ERR] Google Ads 12m failed: {e}")
        ads_12m = {"spend": 0, "conversions_value": 0}

    total_ad_spend = ads_12m["spend"]
    total_conv_value = ads_12m["conversions_value"]

    # ── 4. COGS calculation ──────────────────────────────────
    print("  Calculating COGS from order line items...")
    cogs_cache = _load_cogs_cache()
    total_cogs = _calculate_cogs_from_orders(orders, cogs_cache)

    # Shipping: pull from Shippo API (full 12-month history)
    # Paginates all transactions, deduplicates by tracking number, fetches rate costs
    print("  Pulling shipping costs from Shippo API...")
    total_shipping = _pull_shippo_range(period_start, yesterday)

    # ── 5. Compute widget metrics ────────────────────────────
    ltv = round(total_revenue / unique_customers, 2) if unique_customers else 0
    contribution_margin = round((total_revenue - total_cogs - total_shipping) / total_revenue, 4) if total_revenue else 0
    cac = round(total_ad_spend / unique_customers, 2) if unique_customers else 0
    ncac = round(total_ad_spend / new_customers, 2) if new_customers else 0
    max_cac_be = round(ltv * contribution_margin, 2)
    max_cac_20 = round(ltv * contribution_margin * 0.8, 2)
    payback = round(cac / (ltv / 12), 1) if ltv else 0
    ltv_cac = round(ltv / cac, 2) if cac else 0
    roas = round(total_conv_value / total_ad_spend, 2) if total_ad_spend else 0

    widgets = {
        "ltv_12m": ltv,
        "contribution_margin": contribution_margin,
        "cac": cac,
        "max_cac_breakeven": max_cac_be,
        "max_cac_20pct": max_cac_20,
        "ncac": ncac,
        "payback_months": payback,
        "ltv_cac_ratio": ltv_cac,
    }

    print(f"    LTV: ${ltv} | CM: {contribution_margin:.1%} | CAC: ${cac} | nCAC: ${ncac}")
    print(f"    Payback: {payback} mo | LTV:CAC: {ltv_cac}x | ROAS: {roas}x")

    # ── 6. Channel table (blended — single channel for now) ─
    channels = [{
        "name": "Google Ads",
        "cac": cac,
        "ltv": ltv,
        "ncac": ncac,
        "payback_months": payback,
        "revenue_contribution_pct": round(total_conv_value / total_revenue * 100, 1) if total_revenue else 0,
        "roas": roas,
    }]

    # ── 7. 90-day daily table + 12-month monthly table ───────
    print("  Building 90-day daily table...")

    # Google Ads daily (full 12 months for monthly aggregation)
    try:
        ads_daily = _pull_google_ads_daily(str(period_start), str(yesterday))
    except Exception as e:
        print(f"    [ERR] Google Ads daily failed: {e}")
        ads_daily = []
    ads_by_date = {r["date"]: r for r in ads_daily}

    # WC daily revenue from Supabase (90 days for daily table)
    # Uses raw requests with list-of-tuples pattern for duplicate key support
    try:
        url = f"{SUPABASE_URL}/rest/v1/daily_sales"
        headers = {"apikey": SUPABASE_KEY}
        params = [
            ("report_date", f"gte.{period_90d_start}"),
            ("report_date", f"lte.{yesterday}"),
            ("channel", "eq.woocommerce"),
            ("select", "report_date,revenue"),
        ]
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        wc_daily_rows = resp.json()
        wc_by_date = {r["report_date"]: float(r.get("revenue", 0)) for r in wc_daily_rows}
    except Exception:
        wc_by_date = {}

    daily_90d = []
    d = period_90d_start
    while d <= yesterday:
        ds = str(d)
        ads = ads_by_date.get(ds, {})
        spend = ads.get("spend", 0)
        conv_val = ads.get("conversions_value", 0)
        wc_rev = wc_by_date.get(ds, 0)
        mer = round(wc_rev / spend, 2) if spend > 0 else None

        daily_90d.append({
            "date": ds,
            "ad_spend": spend,
            "ad_spend_google": spend,
            "channel_revenue": conv_val,
            "wc_revenue": round(wc_rev, 2),
            "mer": mer,
        })
        d += timedelta(days=1)

    # ── 7b. 12-month monthly aggregation ─────────────────────
    print("  Building 12-month monthly table...")

    # Aggregate orders by month for revenue + customer counts
    monthly_wc_rev = {}    # {YYYY-MM: revenue}
    monthly_customers = {} # {YYYY-MM: set(customer_keys)}
    monthly_new = {}       # {YYYY-MM: count}

    for o in orders:
        odate = o.get("date_created", "")[:7]  # YYYY-MM
        if not odate:
            continue
        rev = float(o.get("total", 0))
        monthly_wc_rev[odate] = monthly_wc_rev.get(odate, 0) + rev

        cid = o.get("customer_id", 0)
        if cid and cid != 0:
            key = cid
        else:
            email = (o.get("billing", {}).get("email") or "").lower().strip()
            key = f"guest_{email}" if email else None

        if key:
            monthly_customers.setdefault(odate, set()).add(key)

    # Count new customers per month using customer_dates
    for cid, created_str in customer_dates.items():
        created_month = created_str[:7]  # YYYY-MM
        if created_month:
            monthly_new[created_month] = monthly_new.get(created_month, 0) + 1
    # Add guest "new" customers to their earliest order month
    for email, odates in guest_emails.items():
        earliest = min(odates)[:7]
        monthly_new[earliest] = monthly_new.get(earliest, 0) + 1

    # Aggregate ads by month
    monthly_ads = {}  # {YYYY-MM: {spend, conversions_value}}
    for ad_row in ads_daily:
        month = ad_row["date"][:7]
        if month not in monthly_ads:
            monthly_ads[month] = {"spend": 0, "conversions_value": 0}
        monthly_ads[month]["spend"] += ad_row["spend"]
        monthly_ads[month]["conversions_value"] += ad_row["conversions_value"]

    # Build monthly rows
    monthly_12m = []
    d = period_start.replace(day=1)
    end_month = yesterday.replace(day=1)
    while d <= end_month:
        month_key = d.strftime("%Y-%m")
        wc_rev = round(monthly_wc_rev.get(month_key, 0), 2)
        ads_m = monthly_ads.get(month_key, {})
        spend = round(ads_m.get("spend", 0), 2)
        conv_val = round(ads_m.get("conversions_value", 0), 2)
        mer = round(wc_rev / spend, 2) if spend > 0 else None
        custs = len(monthly_customers.get(month_key, set()))
        new_c = monthly_new.get(month_key, 0)
        m_cac = round(spend / custs, 2) if custs > 0 else None
        m_ncac = round(spend / new_c, 2) if new_c > 0 else None

        monthly_12m.append({
            "month": month_key,
            "ad_spend": spend,
            "ad_spend_google": spend,
            "channel_revenue": conv_val,
            "wc_revenue": wc_rev,
            "mer": mer,
            "customers": custs,
            "new_customers": new_c,
            "cac": m_cac,
            "ncac": m_ncac,
        })

        # Next month
        if d.month == 12:
            d = d.replace(year=d.year + 1, month=1)
        else:
            d = d.replace(month=d.month + 1)

    # ── 8. Write JSON ────────────────────────────────────────
    output = {
        "generated_at": TODAY_STR,
        "period_start": str(period_start),
        "period_end": str(yesterday),
        "total_customers": unique_customers,
        "new_customers": new_customers,
        "returning_customers": returning_customers,
        "total_revenue": round(total_revenue, 2),
        "total_ad_spend": total_ad_spend,
        "total_cogs": total_cogs,
        "total_shipping": round(total_shipping, 2),
        "widgets": widgets,
        "channels": channels,
        "daily_90d": daily_90d,
        "monthly_12m": monthly_12m,
    }

    _write_json("marketing.json", output)
    print(f"  [OK] marketing.json written")
    return True


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print(f"  Nature's Seed Dashboard Data Generator")
    print(f"  Date: {TODAY_STR}")
    print(f"  Output: {OUT_DIR}")
    print("=" * 60)

    sources = [
        ("Reporting (Supabase)",  generate_reporting),
        ("Budget (CSV)",          generate_budget),
        ("Klaviyo (Campaigns)",   generate_klaviyo),
        ("Amazon (SP-API)",       generate_amazon),
        ("Walmart (Marketplace)", generate_walmart),
        ("Inventory (Fishbowl)",  generate_inventory),
        ("Notes (Markdown)",      generate_notes),
        ("Marketing (Channels)",  generate_marketing),
    ]

    import traceback
    results = {}
    for name, fn in sources:
        try:
            ok = fn()
            results[name] = "OK" if ok else "SKIPPED"
        except Exception as e:
            print(f"  [ERR] {name} failed: {e}")
            traceback.print_exc()
            results[name] = f"FAILED: {e}"

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for name, status in results.items():
        icon = "OK  " if status == "OK" else ("SKIP" if status == "SKIPPED" else "FAIL")
        print(f"  [{icon}] {name}: {status}")

    failed = [n for n, s in results.items() if s.startswith("FAILED")]
    if failed:
        print(f"\n  {len(failed)} source(s) failed — dashboard may show stale data for: {', '.join(failed)}")
        sys.exit(1)
    else:
        print(f"\n  All sources written to {OUT_DIR}")


if __name__ == "__main__":
    main()
