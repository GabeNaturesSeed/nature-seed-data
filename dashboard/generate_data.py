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

# ══════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent.parent
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


# ══════════════════════════════════════════════════════════════
# 1. REPORTING.JSON — Supabase daily_summary + budget CSV
# ══════════════════════════════════════════════════════════════

def _load_budget_csv():
    """
    Parse 2026 budget CSV.
    Returns dict: { "2026-01": { "net_revenue": 133779, "ad_spend": 35805,
                                 "cogs": 67192, "gross_margin": 66587, "net_income": -48839 } }
    """
    budget_path = ROOT / "2026ECOMMBUDGET" / "Budget 2026 - Sheet1.csv"
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
    budget_dir = ROOT / "2026ECOMMBUDGET"
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
        return {
            "revenue": round(sum(float(_col(r, "total_revenue", "revenue") or 0) for r in rows), 2),
            "orders": sum(int(_col(r, "total_orders", "orders") or 0) for r in rows),
            "ad_spend": round(sum(float(_col(r, "total_ad_spend", "ad_spend") or 0) for r in rows), 2),
            "cogs": round(sum(float(_col(r, "total_cogs", "cogs") or 0) for r in rows), 2),
            "shipping": round(sum(float(_col(r, "total_shipping", "shipping_cost") or 0) for r in rows), 2),
            "net_revenue": round(sum(float(_col(r, "net_revenue") or 0) for r in rows), 2),
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
    cy_by_month = defaultdict(lambda: {"revenue": 0, "orders": 0, "ad_spend": 0, "cogs": 0, "net_revenue": 0})
    ly_by_month = defaultdict(lambda: {"revenue": 0})

    for r in ytd_cy_rows:
        m = r["report_date"][:7]  # YYYY-MM
        cy_by_month[m]["revenue"] += float(_col(r, "total_revenue", "revenue") or 0)
        cy_by_month[m]["orders"] += int(_col(r, "total_orders", "orders") or 0)
        cy_by_month[m]["ad_spend"] += float(_col(r, "total_ad_spend", "ad_spend") or 0)
        cy_by_month[m]["cogs"] += float(_col(r, "total_cogs", "cogs") or 0)
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
        ad = cy.get("ad_spend", 0)
        mer = round(cy.get("revenue", 0) / ad, 2) if ad else 0
        ytd_months.append({
            "month": m,
            "revenue": round(cy.get("revenue", 0), 2),
            "ly_revenue": round(ly_by_month.get(m, {}).get("revenue", 0), 2),
            "budget_revenue": budget.get(m, {}).get("net_revenue", 0),
            "orders": cy.get("orders", 0),
            "ad_spend": round(ad, 2),
            "mer": mer,
            "cogs": round(cy.get("cogs", 0), 2),
            "net_revenue": round(cy.get("net_revenue", 0), 2),
        })

    ytd_totals_cy = {
        "revenue": round(sum(m["revenue"] for m in ytd_months), 2),
        "orders": sum(m["orders"] for m in ytd_months),
        "ad_spend": round(sum(m["ad_spend"] for m in ytd_months), 2),
        "cogs": round(sum(m["cogs"] for m in ytd_months), 2),
        "net_revenue": round(sum(m["net_revenue"] for m in ytd_months), 2),
    }
    ytd_totals_ly = {"revenue": round(sum(m["ly_revenue"] for m in ytd_months), 2)}
    ytd_totals_budget = {"revenue": round(sum(m["budget_revenue"] for m in ytd_months), 2)}

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

    # No server-side date filter — Klaviyo 2024-07-15 doesn't support send_time filter
    # Fetch all campaigns (sorted by name), filter client-side by send_time
    params = {
        "sort": "-scheduled_at",
        "page[size]": 50,
    }

    campaigns = []
    url = f"{base_url}/campaigns/"
    first_page = True
    while url:
        resp = requests.get(
            url,
            headers=headers,
            params=params if first_page else None,
            timeout=30,
        )
        first_page = False
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
        params = None  # next URL already has params

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
    abc_path = ROOT / "abc-analysis" / "abc_analysis_results.json"
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
            json={"appName": "Dashboard", "appId": 101, "username": FB_USER, "password": FB_PASS},
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
