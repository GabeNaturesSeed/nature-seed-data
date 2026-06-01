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
  7. Shippo+WC  — shipping.json  (shipping costs + carrier breakdown)
  8. docs/notes.md — notes.json  (operator notes)
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

# Shipping cost estimation from Shippo quotes (for open months without finance actuals).
# Formula: estimated_actual = shippo_quote × SHIPPO_RATE_MULTIPLIER + SHIPPO_WEIGHT_SURCHARGE × shipments
#   - ×0.783: UPS invoices at 78.3% of Shippo's quoted rate (Shippo quotes run ~21.7% high)
#   - +$2.00/shipment: UPS weight-corrects ~12.6% of packages after the fact; spread evenly ≈ $2/order
# Net effect vs UPS list rate: ~47.7% savings (negotiated Shippo discount).
SHIPPO_RATE_MULTIPLIER = 0.783
SHIPPO_WEIGHT_SURCHARGE = 2.00  # dollars per shipment

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
    """GET from Supabase REST API.
    Always sets a high limit to avoid PostgREST default truncation.
    """
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    p = dict(params or {})
    if "limit" not in p:
        p["limit"] = 10000
    resp = requests.get(url, headers=headers, params=p, timeout=30)
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


# _pull_google_ads_range() — REMOVED: replaced by Supabase v_marketing_12m view
# _pull_google_ads_daily() — REMOVED: replaced by Supabase v_daily_ad_spend_90d view


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
    Still used by generate_reporting() for MTD new customer counts.
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


# _load_cogs_cache() — REMOVED: replaced by Supabase v_monthly_cogs view
# _calculate_cogs_from_orders() — REMOVED: replaced by Supabase v_monthly_cogs view


# _pull_shippo_range() — REMOVED: replaced by Supabase v_monthly_shipping view


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


def _load_budget_csv_full():
    """Parse ALL line items from 2026 budget CSV for P&L view.
    Returns dict: { "2026-01": { "seed_revenue": ..., "freight_revenue": ..., ... } }
    """
    budget_path = ROOT / "research" / "2026-budget" / "Budget 2026 - Sheet1.csv"
    if not budget_path.exists():
        return {}

    months = [f"2026-{m:02d}" for m in range(1, 13)]

    # We need to handle duplicate labels (e.g. "Seed" appears under Revenue and COGS,
    # "Salaries & Wages" appears under S/M/A and G&A). Use section tracking.
    result = {m: {} for m in months}
    section = ""

    # Map (section, label) → output key
    key_map = {
        # Revenue
        ("revenue", "Seed"): "seed_revenue",
        ("revenue", "Other"): "other_revenue",
        ("revenue", "Freight"): "freight_revenue",
        ("revenue", "Discounts & Allowances"): "discounts",
        ("revenue", "Net Revenue"): "net_revenue",
        # COGS
        ("cogs", "Seed"): "cogs_seed",
        ("cogs", "Other"): "cogs_other",
        ("cogs", "Inventory Adjustment"): "cogs_inventory_adj",
        ("cogs", "Freight"): "cogs_freight",
        ("cogs", "Total Cost Of Goods"): "total_cogs",
        # Margin
        ("cogs", "Gross Margin"): "gross_margin",
        ("cogs", "Gross Margin %"): "gross_margin_pct",
        # Production/Warehouse
        ("prod", "Warehouse"): "warehouse",
        ("prod", "Farm"): "farm",
        ("prod", "Collections"): "collections",
        ("prod", "Total Production/Warehouse"): "total_production",
        # Sales/Marketing/Advertising
        ("sma", "Salaries & Wages"): "sma_salaries",
        ("sma", "Marketing"): "marketing",
        ("sma", "Advertising"): "advertising",
        ("sma", "Development"): "development",
        ("sma", "Total Sales/Marketing/Advertising"): "total_sma",
        # G&A
        ("ga", "Salaries & Wages"): "ga_salaries",
        ("ga", "Professional Fees"): "professional_fees",
        ("ga", "Insurance"): "insurance",
        ("ga", "T&E"): "travel_entertainment",
        ("ga", "Utilities & Supplies"): "utilities_supplies",
        ("ga", "Corporate Allocation"): "corporate_allocation",
        ("ga", "Other"): "ga_other",
        ("ga", "Total General & Admin"): "total_ga",
        # Bottom line
        ("bottom", "Total Operating Costs"): "total_opex",
        ("bottom", "OPEX %"): "opex_pct",
        ("bottom", "Management Fee"): "management_fee",
        ("bottom", "Other Income & Expense"): "other_income_expense",
        ("bottom", "Net Income"): "net_income",
        ("bottom", "EBITDA"): "ebitda",
        ("bottom", "EBITDA %"): "ebitda_pct",
        ("bottom", "Interest"): "interest",
        ("bottom", "Tax"): "tax",
        ("bottom", "Depreciation"): "depreciation",
        ("bottom", "Amortization"): "amortization",
    }

    with open(budget_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            label = row[0].strip()

            # Track sections by all-caps header rows
            if label == "REVENUE":
                section = "revenue"; continue
            elif label == "COST OF GOODS":
                section = "cogs"; continue
            elif label == "PRODUCTION/WAREHOUSE":
                section = "prod"; continue
            elif label == "SALES/MARKETING/ADVERTISING":
                section = "sma"; continue
            elif label == "GENERAL & ADMIN":
                section = "ga"; continue
            elif label == "Total Operating Costs":
                # This row belongs to bottom, but parse it first
                pass

            # Gross Margin sits between COGS and PROD sections
            if label in ("Gross Margin", "Gross Margin %"):
                section = "cogs"
            # Everything after Total Operating Costs is bottom
            if label in ("Total Operating Costs", "OPEX %", "Management Fee",
                         "Other Income & Expense", "Net Income", "Interest",
                         "Tax", "Depreciation", "Amortization", "EBITDA", "EBITDA %"):
                section = "bottom"

            key = key_map.get((section, label))
            if key:
                for i, month in enumerate(months):
                    val = row[i + 1] if i + 1 < len(row) else "0"
                    result[month][key] = _parse_dollar(val)

    return result


def _load_actuals_csv():
    """
    Parse any *Actuals*.csv files from 2026-budget/.
    Returns dict: { "2026-01": { "net_revenue": ..., "cogs": ..., "warehouse": ..., ... } }
    Captures ALL P&L line items so completed months use real numbers.
    """
    actuals = {}
    budget_dir = ROOT / "research" / "2026-budget"
    if not budget_dir.exists():
        return actuals

    month_names = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }

    for csv_path in sorted(budget_dir.glob("*Actuals*.csv")):
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = None
            scale = 1  # 1000 if CSV is in ($000s) format
            # Track which section we're in to disambiguate duplicate labels
            section = None
            for row in reader:
                if not row:
                    continue
                if header is None:
                    header = []
                    for cell in row:
                        cell_lower = cell.strip().lower()
                        if cell_lower in month_names:
                            header.append(f"2026-{month_names[cell_lower]}")
                        else:
                            header.append(None)
                    continue

                label = row[0].strip()

                # Detect thousands-format rows (e.g. "($000s)")
                if "000s" in label.lower():
                    scale = 1000
                    continue

                # Track sections for disambiguation
                if label == "REVENUE":
                    section = "revenue"
                    continue
                elif label == "COST OF GOODS":
                    section = "cogs"
                    continue
                elif label == "PRODUCTION/WAREHOUSE":
                    section = "production"
                    continue
                elif label == "SALES/MARKETING/ADVERTISING":
                    section = "sma"
                    continue
                elif label == "GENERAL & ADMIN":
                    section = "ga"
                    continue

                # Map label to key, handling duplicates by section
                key = None
                if label == "Net Revenue":
                    key = "net_revenue"
                elif label == "Seed" and section == "revenue":
                    key = "seed_revenue"
                elif label == "Other" and section == "revenue":
                    key = "other_revenue"
                elif label == "Discounts & Allowances":
                    key = "discounts"
                elif label == "Total Cost Of Goods":
                    key = "cogs"
                elif label == "Seed" and section == "cogs":
                    key = "seed_cogs"
                elif label == "Other" and section == "cogs":
                    key = "other_cogs"
                elif label == "Inventory Adjustment":
                    key = "inventory_adjustment"
                elif label == "Gross Margin":
                    key = "gross_margin"
                elif label == "Advertising":
                    key = "ad_spend"
                elif label == "Net Income":
                    key = "net_income"
                elif label == "Warehouse":
                    key = "warehouse"
                elif label == "Farm":
                    key = "farm"
                elif label == "Collections":
                    key = "collections"
                elif label == "Total Production/Warehouse":
                    key = "total_production"
                elif label == "Salaries & Wages" and section == "sma":
                    key = "sma_salaries"
                elif label == "Salaries & Wages" and section == "ga":
                    key = "ga_salaries"
                elif label == "Marketing":
                    key = "marketing"
                elif label == "Development":
                    key = "development"
                elif label == "Total Sales/Marketing/Advertising":
                    key = "total_sma"
                elif label == "Professional Fees":
                    key = "professional_fees"
                elif label == "Insurance":
                    key = "insurance"
                elif label in ("T&E", "Travel & Entertainment"):
                    key = "travel_entertainment"
                elif label == "Utilities & Supplies":
                    key = "utilities_supplies"
                elif label == "Corporate Allocation":
                    key = "corporate_allocation"
                elif label == "Other" and section == "ga":
                    key = "ga_other"
                elif label == "Total General & Admin":
                    key = "total_ga"
                elif label == "Total Operating Costs":
                    key = "total_opex"
                elif label == "Depreciation":
                    key = "depreciation"
                elif label == "Amortization":
                    key = "amortization"
                elif label == "Interest":
                    key = "interest"
                elif label == "Tax":
                    key = "tax"
                elif label == "EBITDA":
                    key = "ebitda"
                elif label == "Other Income & Expense":
                    key = "other_income"
                elif label == "Freight" and section == "cogs":
                    key = "cogs_freight"
                elif label == "Freight" and section == "revenue":
                    key = "freight_revenue"

                if key:
                    for i, month_key in enumerate(header):
                        if month_key is None or i >= len(row):
                            continue
                        if month_key not in actuals:
                            actuals[month_key] = {}
                        actuals[month_key][key] = _parse_dollar(row[i]) * scale

    return actuals


def generate_reporting():
    """Pull MTD and YTD data from Supabase + budget CSV."""
    print("\n[Reporting] Pulling Supabase daily_summary...")

    today = TODAY
    yesterday = today - timedelta(days=1)

    # MTD window
    mtd_start_cy = date(today.year, today.month, 1)
    mtd_start_ly = date(today.year - 1, today.month, 1)
    # When today is the 1st, yesterday is in the prior month — clamp to avoid
    # "day out of range" when yesterday.day > days in today.month (e.g. June 1 after May 31).
    if today.day > 1:
        mtd_end_cy = yesterday
        mtd_end_ly = date(today.year - 1, today.month, yesterday.day)
    else:
        mtd_end_cy = mtd_start_cy
        mtd_end_ly = date(today.year - 1, today.month, 1)

    # Last month window (full calendar month)
    import calendar as _calendar
    lm_year = today.year if today.month > 1 else today.year - 1
    lm_month = today.month - 1 if today.month > 1 else 12
    lm_days = _calendar.monthrange(lm_year, lm_month)[1]
    lm_start_cy = date(lm_year, lm_month, 1)
    lm_end_cy = date(lm_year, lm_month, lm_days)
    lm_start_ly = date(lm_year - 1, lm_month, 1)
    lm_end_ly = date(lm_year - 1, lm_month, lm_days)

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
    lm_cy_rows = fetch_date_range(lm_start_cy, lm_end_cy)
    lm_ly_rows = fetch_date_range(lm_start_ly, lm_end_ly)
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
        # CRITICAL REPORTING RULE: Revenue is WC-only (DTC). Exclude Amazon + Walmart.
        # COGS note: daily_summary.total_cogs is all-channel; for precision MTD
        # should pull daily_cogs where channel='woocommerce', but since
        # Amazon/Walmart COGS is typically ~$0, total_cogs ≈ wc_cogs in practice.
        rev = round(sum(float(r.get("wc_revenue") or 0) for r in rows), 2)
        total_rev_all = round(sum(float(_col(r, "total_revenue", "revenue") or 0) for r in rows), 2)
        amz_rev = round(sum(float(r.get("amazon_revenue") or 0) for r in rows), 2)
        wmt_rev = round(sum(float(r.get("walmart_revenue") or 0) for r in rows), 2)
        cogs = round(sum(float(_col(r, "total_cogs", "cogs") or 0) for r in rows), 2)
        ad_spend = round(sum(float(_col(r, "total_ad_spend", "ad_spend") or 0) for r in rows), 2)
        shipping = round(sum(float(_col(r, "total_shipping", "shipping_cost") or 0) for r in rows), 2)
        platform_fees = round(sum(float(r.get("platform_fees") or 0) for r in rows), 2)
        # If wc_revenue not populated (backfill gap), fall back gracefully
        if rev == 0 and total_rev_all > 0:
            rev = round(total_rev_all - amz_rev - wmt_rev, 2)
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
            "wc_revenue": rev,
            "amazon_revenue": amz_rev,
            "walmart_revenue": wmt_rev,
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

    # ── WC-only overrides for MTD metrics ────────────────────────
    # daily_summary.total_orders/total_cogs are all-channel. Replace with
    # WC-channel rollups so the DTC reporting section is WooCommerce-only.
    def _sum_channel(table, start, end, channel, value_col):
        try:
            url = f"{SUPABASE_URL}/rest/v1/{table}"
            params = [
                ("report_date", f"gte.{start}"),
                ("report_date", f"lte.{end}"),
                ("channel", f"eq.{channel}"),
                ("select", f"report_date,{value_col}"),
            ]
            resp = requests.get(url, headers={"apikey": SUPABASE_KEY}, params=params, timeout=30)
            resp.raise_for_status()
            return sum(float(r.get(value_col) or 0) for r in resp.json())
        except Exception as e:
            print(f"    [WARN] WC-only {table}.{value_col} pull failed: {e}")
            return None

    wc_orders_mtd = _sum_channel("daily_sales", mtd_start_cy, mtd_end_cy, "woocommerce", "orders")
    wc_cogs_mtd = _sum_channel("daily_cogs", mtd_start_cy, mtd_end_cy, "woocommerce", "total_cogs")
    wc_orders_ly = _sum_channel("daily_sales", mtd_start_ly, mtd_end_ly, "woocommerce", "orders")
    wc_cogs_ly = _sum_channel("daily_cogs", mtd_start_ly, mtd_end_ly, "woocommerce", "total_cogs")

    if wc_orders_mtd is not None:
        cy_totals["orders"] = int(wc_orders_mtd)
    if wc_cogs_mtd is not None:
        cy_totals["cogs"] = round(wc_cogs_mtd, 2)
    if wc_orders_ly is not None:
        ly_totals["orders"] = int(wc_orders_ly)
    if wc_cogs_ly is not None:
        ly_totals["cogs"] = round(wc_cogs_ly, 2)

    # Recompute DTC-only gross profit / CM1 / CM2 from WC-only revenue + cogs
    for tot in (cy_totals, ly_totals):
        tot["gross_profit"] = round(tot["revenue"] - tot["cogs"], 2)
        tot["gross_margin_pct"] = round(tot["gross_profit"] / tot["revenue"] * 100, 1) if tot["revenue"] else None
        tot["cm1"] = round(tot["gross_profit"] - tot["ad_spend"], 2)
        tot["cm2"] = round(tot["cm1"] - tot["shipping"] - tot["platform_fees"], 2)
        tot["cm2_pct"] = round(tot["cm2"] / tot["revenue"] * 100, 1) if tot["revenue"] else None

    # ── Last-month totals ─────────────────────────────────────
    lm_cy_totals = sum_rows(lm_cy_rows)
    lm_ly_totals = sum_rows(lm_ly_rows)
    lm_cy_totals["mer"] = round(lm_cy_totals["revenue"] / lm_cy_totals["ad_spend"], 2) if lm_cy_totals["ad_spend"] else 0

    wc_orders_lm = _sum_channel("daily_sales", lm_start_cy, lm_end_cy, "woocommerce", "orders")
    wc_cogs_lm = _sum_channel("daily_cogs", lm_start_cy, lm_end_cy, "woocommerce", "total_cogs")
    wc_orders_lm_ly = _sum_channel("daily_sales", lm_start_ly, lm_end_ly, "woocommerce", "orders")
    wc_cogs_lm_ly = _sum_channel("daily_cogs", lm_start_ly, lm_end_ly, "woocommerce", "total_cogs")

    if wc_orders_lm is not None:
        lm_cy_totals["orders"] = int(wc_orders_lm)
    if wc_cogs_lm is not None:
        lm_cy_totals["cogs"] = round(wc_cogs_lm, 2)
    if wc_orders_lm_ly is not None:
        lm_ly_totals["orders"] = int(wc_orders_lm_ly)
    if wc_cogs_lm_ly is not None:
        lm_ly_totals["cogs"] = round(wc_cogs_lm_ly, 2)

    for tot in (lm_cy_totals, lm_ly_totals):
        tot["gross_profit"] = round(tot["revenue"] - tot["cogs"], 2)
        tot["gross_margin_pct"] = round(tot["gross_profit"] / tot["revenue"] * 100, 1) if tot["revenue"] else None
        tot["cm1"] = round(tot["gross_profit"] - tot["ad_spend"], 2)
        tot["cm2"] = round(tot["cm1"] - tot["shipping"] - tot["platform_fees"], 2)
        tot["cm2_pct"] = round(tot["cm2"] / tot["revenue"] * 100, 1) if tot["revenue"] else None

    budget = _load_budget_csv()
    cur_month_key = f"{today.year}-{today.month:02d}"
    budget_month = budget.get(cur_month_key, {})
    mtd_budget = {
        "revenue": budget_month.get("net_revenue", 0),
        "ad_spend": budget_month.get("ad_spend", 0),
    }

    lm_month_key = f"{lm_year}-{lm_month:02d}"
    lm_budget_month = budget.get(lm_month_key, {})
    lm_budget = {
        "revenue": lm_budget_month.get("net_revenue", 0),
        "ad_spend": lm_budget_month.get("ad_spend", 0),
    }

    # Daily chart series — WC-only (fall back to total_revenue if wc_revenue missing)
    def _wc_rev(row):
        wc = row.get("wc_revenue")
        if wc is not None:
            return float(wc)
        # Back-compat: derive from total - marketplaces
        total = float(row.get("total_revenue") or 0)
        amz = float(row.get("amazon_revenue") or 0)
        wmt = float(row.get("walmart_revenue") or 0)
        return max(0, total - amz - wmt)

    daily_cy = [
        {"date": r["report_date"], "revenue": _wc_rev(r)}
        for r in cy_rows
    ]
    daily_ly = [
        {
            # Shift last-year date forward 1 year for chart alignment
            "date": str(date.fromisoformat(r["report_date"]) + timedelta(days=365)),
            "revenue": _wc_rev(r),
        }
        for r in ly_rows
    ]

    lm_daily_cy = [
        {"date": r["report_date"], "revenue": _wc_rev(r)}
        for r in lm_cy_rows
    ]
    lm_daily_ly = [
        {
            "date": str(date.fromisoformat(r["report_date"]) + timedelta(days=365)),
            "revenue": _wc_rev(r),
        }
        for r in lm_ly_rows
    ]

    # YTD — aggregate by month
    # CRITICAL REPORTING RULE: Use WooCommerce (DTC) data ONLY. Exclude
    # Amazon and Walmart marketplace revenue/orders from all P&L and reporting.
    # Marketplaces are tracked separately on their own pages.
    from collections import defaultdict
    cy_by_month = defaultdict(lambda: {"revenue": 0, "orders": 0, "ad_spend": 0, "cogs": 0, "shipping": 0, "platform_fees": 0, "net_revenue": 0})
    ly_by_month = defaultdict(lambda: {"revenue": 0, "ad_spend": 0})

    for r in ytd_cy_rows:
        m = r["report_date"][:7]  # YYYY-MM
        # revenue = WC only (excludes Amazon + Walmart). Fall back to total_revenue if wc_revenue column missing.
        wc_rev = r.get("wc_revenue")
        rev = float(wc_rev) if wc_rev is not None else float(_col(r, "total_revenue", "revenue") or 0)
        cy_by_month[m]["revenue"] += rev
        cy_by_month[m]["orders"] += int(_col(r, "total_orders", "orders") or 0)
        cy_by_month[m]["ad_spend"] += float(_col(r, "total_ad_spend", "ad_spend") or 0)
        cy_by_month[m]["cogs"] += float(_col(r, "total_cogs", "cogs") or 0)
        cy_by_month[m]["shipping"] += float(_col(r, "total_shipping", "shipping_cost") or 0)
        cy_by_month[m]["platform_fees"] += float(r.get("platform_fees") or 0)
        cy_by_month[m]["net_revenue"] += float(_col(r, "net_revenue") or 0)

    # Pull WC-only COGS directly from daily_cogs (daily_summary.total_cogs is all-channel)
    wc_cogs_by_month = defaultdict(float)
    try:
        url_cogs = f"{SUPABASE_URL}/rest/v1/daily_cogs"
        headers_cogs = {"apikey": SUPABASE_KEY}
        params_cogs = [
            ("report_date", f"gte.{ytd_start_cy}"),
            ("report_date", f"lte.{yesterday}"),
            ("channel", "eq.woocommerce"),
            ("select", "report_date,total_cogs"),
        ]
        resp_cogs = requests.get(url_cogs, headers=headers_cogs, params=params_cogs, timeout=30)
        resp_cogs.raise_for_status()
        for r in resp_cogs.json():
            wc_cogs_by_month[r["report_date"][:7]] += float(r.get("total_cogs") or 0)
    except Exception as e:
        print(f"    [WARN] Could not pull WC-only daily_cogs: {e}. Falling back to total_cogs.")
        for m, v in cy_by_month.items():
            wc_cogs_by_month[m] = v["cogs"]

    # Overwrite cogs with WC-only values
    for m in list(cy_by_month.keys()):
        cy_by_month[m]["cogs"] = round(wc_cogs_by_month.get(m, cy_by_month[m]["cogs"]), 2)

    for r in ytd_ly_rows:
        # Map last-year month to this-year equivalent
        m_ly = r["report_date"][:7]
        year_ly, mon_ly = m_ly.split("-")
        m_cy = f"{int(year_ly)+1}-{mon_ly}"
        # LY revenue also WC-only for fair YoY compare
        wc_rev = r.get("wc_revenue")
        rev = float(wc_rev) if wc_rev is not None else float(_col(r, "total_revenue", "revenue") or 0)
        ly_by_month[m_cy]["revenue"] += rev
        ly_by_month[m_cy]["ad_spend"] += float(_col(r, "total_ad_spend", "ad_spend") or 0)

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
        ly_ad = ly_by_month.get(m, {}).get("ad_spend", 0)
        bud_ad = budget.get(m, {}).get("ad_spend", 0)
        ly_rev = ly_by_month.get(m, {}).get("revenue", 0)
        ly_mer = round(ly_rev / ly_ad, 2) if ly_ad else None
        bud_rev = budget.get(m, {}).get("net_revenue", 0)
        bud_mer = round(bud_rev / bud_ad, 2) if bud_ad else None
        ytd_months.append({
            "month": m,
            "revenue": round(rev, 2),
            "ly_revenue": round(ly_rev, 2),
            "budget_revenue": bud_rev,
            "orders": cy.get("orders", 0),
            "ad_spend": round(ad, 2),
            "ly_ad_spend": round(ly_ad, 2),
            "budget_ad_spend": bud_ad,
            "mer": mer,
            "ly_mer": ly_mer,
            "budget_mer": bud_mer,
            "cogs": round(cogs_m, 2),
            "shipping": round(ship_m, 2),
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
    _ytd_ly_rev = round(sum(m["ly_revenue"] for m in ytd_months), 2)
    _ytd_ly_ad = round(sum(m["ly_ad_spend"] for m in ytd_months), 2)
    _ytd_bud_rev = round(sum(m["budget_revenue"] for m in ytd_months), 2)
    _ytd_bud_ad = round(sum(m["budget_ad_spend"] for m in ytd_months), 2)
    ytd_totals_ly = {
        "revenue": _ytd_ly_rev,
        "ad_spend": _ytd_ly_ad,
        "mer": round(_ytd_ly_rev / _ytd_ly_ad, 2) if _ytd_ly_ad else None,
    }
    ytd_totals_budget = {
        "revenue": _ytd_bud_rev,
        "ad_spend": _ytd_bud_ad,
        "mer": round(_ytd_bud_rev / _ytd_bud_ad, 2) if _ytd_bud_ad else None,
    }

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
        # Sum shipping collected from WC orders for current month P&L
        mtd_shipping_collected = round(sum(float(o.get("shipping_total") or 0) for o in mtd_orders), 2)
        print(f"    MTD WC shipping collected: ${mtd_shipping_collected:,.2f}")
    except Exception as e:
        print(f"    [WARN] MTD new customer count failed: {e}")
        new_customers_mtd = None
        mtd_shipping_collected = 0

    aov = round(cy_totals["revenue"] / cy_totals["orders"], 2) if cy_totals["orders"] else 0
    new_cac = round(cy_totals["ad_spend"] / new_customers_mtd, 2) if new_customers_mtd else None

    # Pull last-month WC orders for new customer count
    print("  Pulling last-month WC orders for new customer count...")
    try:
        lm_orders = _pull_wc_orders_range(str(lm_start_cy), str(lm_end_cy))
        lm_cids = {}
        lm_guest_emails = {}
        for o in lm_orders:
            cid = o.get("customer_id", 0)
            if cid and cid != 0:
                lm_cids.setdefault(cid, True)
            else:
                email = (o.get("billing", {}).get("email") or "").lower().strip()
                if email:
                    lm_guest_emails.setdefault(email, True)
        lm_cust_dates = _pull_wc_customers_batch(list(lm_cids.keys()))
        lm_start_str = str(lm_start_cy)
        new_customers_lm = sum(1 for cid in lm_cids if (lm_cust_dates.get(cid, "")[:10] >= lm_start_str))
        new_customers_lm += len(lm_guest_emails)
        print(f"    LM customers: {len(lm_cids) + len(lm_guest_emails)} unique ({new_customers_lm} new)")
    except Exception as e:
        print(f"    [WARN] Last-month new customer count failed: {e}")
        new_customers_lm = None

    lm_aov = round(lm_cy_totals["revenue"] / lm_cy_totals["orders"], 2) if lm_cy_totals["orders"] else 0
    lm_new_cac = round(lm_cy_totals["ad_spend"] / new_customers_lm, 2) if new_customers_lm else None

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
        "lm": {
            "cy": {
                "revenue": lm_cy_totals["revenue"],
                "orders": lm_cy_totals["orders"],
                "ad_spend": lm_cy_totals["ad_spend"],
                "mer": lm_cy_totals["mer"],
                "cogs": lm_cy_totals["cogs"],
                "shipping": lm_cy_totals["shipping"],
                "net_revenue": lm_cy_totals["net_revenue"],
                "wc_revenue": lm_cy_totals["wc_revenue"],
                "amazon_revenue": lm_cy_totals["amazon_revenue"],
                "walmart_revenue": lm_cy_totals["walmart_revenue"],
                "platform_fees": lm_cy_totals["platform_fees"],
                "gross_profit": lm_cy_totals["gross_profit"],
                "gross_margin_pct": lm_cy_totals["gross_margin_pct"],
                "cm1": lm_cy_totals["cm1"],
                "cm2": lm_cy_totals["cm2"],
                "cm2_pct": lm_cy_totals["cm2_pct"],
                "aov": lm_aov,
                "new_customers": new_customers_lm,
                "new_customer_cac": lm_new_cac,
            },
            "ly": {
                "revenue": lm_ly_totals["revenue"],
                "orders": lm_ly_totals["orders"],
                "ad_spend": lm_ly_totals["ad_spend"],
            },
            "budget": lm_budget,
            "daily_cy": lm_daily_cy,
            "daily_ly": lm_daily_ly,
        },
        "ytd": {
            "months": ytd_months,
            "totals_cy": ytd_totals_cy,
            "totals_ly": ytd_totals_ly,
            "totals_budget": ytd_totals_budget,
        },
    }
    # ── P&L: merge actuals with budget fixed costs ────────
    # For months with finance actuals CSV → use real fixed costs
    # For months without actuals → use budget estimates
    print("  Building P&L from actuals + budget fixed costs...")
    budget_full = _load_budget_csv_full()
    actuals_csv = _load_actuals_csv()

    # ── Freight revenue for open closed months ───────────
    # Current month uses mtd_shipping_collected. Past months with actuals use CSV.
    # Past months WITHOUT actuals (e.g. March before finance closes Jan/Feb) need
    # WC orders pulled to recover customer-paid shipping.
    open_closed_shipping = {}  # {month_key: shipping_collected}
    open_closed_months = [
        m["month"] for m in ytd_months
        if m["month"] != cur_month_key and m["month"] not in actuals_csv
    ]
    for mk_open in open_closed_months:
        y_o, mo_o = mk_open.split("-")
        m_start = f"{y_o}-{mo_o}-01"
        import calendar as _cal
        m_end = f"{y_o}-{mo_o}-{_cal.monthrange(int(y_o), int(mo_o))[1]:02d}"
        print(f"  Pulling WC orders for open month {mk_open} shipping_total...")
        try:
            m_orders = _pull_wc_orders_range(m_start, m_end)
            open_closed_shipping[mk_open] = round(
                sum(float(o.get("shipping_total") or 0) for o in m_orders), 2
            )
            print(f"    {mk_open} WC shipping collected: ${open_closed_shipping[mk_open]:,.2f}")
        except Exception as e:
            print(f"    [WARN] {mk_open} WC shipping pull failed: {e}")
            open_closed_shipping[mk_open] = None

    # ── Freight COGS estimate formula ──────────────────────
    # estimated_actual = shippo_quote × 0.783 + $2.00 × shipments
    print(f"  Freight estimate: Shippo quote × {SHIPPO_RATE_MULTIPLIER} + ${SHIPPO_WEIGHT_SURCHARGE:.2f}/shipment")

    pnl_months = []
    for m_data in ytd_months:
        mk = m_data["month"]  # e.g. "2026-01"
        bud = budget_full.get(mk, {})
        act = actuals_csv.get(mk, {})  # Finance actuals for completed months
        has_actuals = bool(act)

        if has_actuals:
            print(f"    {mk}: Using FINANCE ACTUALS for fixed costs")
        else:
            print(f"    {mk}: Using BUDGET ESTIMATES for fixed costs")

        # ── Revenue + COGS sourcing hierarchy ──────────────────
        # 1) If finance actuals CSV present → use CSV (authoritative)
        # 2) Else if Supabase has data for this month → use WC-only Supabase
        # 3) Else → fall back to budget CSV (prorated yearly)
        #
        # NOTE: m_data.revenue is already WC-only (set above to wc_revenue).
        #       m_data.cogs is already WC-only (set above to daily_cogs WC).
        #       m_data.shipping is Shippo freight cost (all channels, but WC is ~100%).
        act_ad_spend = m_data.get("ad_spend", 0)
        act_shipping = m_data.get("shipping", 0) if m_data.get("shipping") else 0

        if has_actuals:
            # Finance CSV is authoritative for closed months
            seed_revenue = act.get("seed_revenue", 0)
            other_revenue = act.get("other_revenue", 0)
            discounts = act.get("discounts", 0)  # stored as negative number
            revenue_freight = act.get("freight_revenue", 0)
            # Net Revenue from CSV already = seed + other + freight + discounts
            act_revenue = act.get("net_revenue", seed_revenue + other_revenue + revenue_freight + discounts)

            seed_cogs = act.get("seed_cogs", 0)
            other_cogs = act.get("other_cogs", 0)
            inventory_adjustment = act.get("inventory_adjustment", 0)
            cogs_freight = act.get("cogs_freight", 0)
            # Total COGS from CSV already = seed + other + inv_adj + freight
            act_cogs = act.get("cogs", seed_cogs + other_cogs + inventory_adjustment + cogs_freight)
            source_tag = "actuals"
            revenue_freight_source = "Finance Actuals CSV"
            cogs_freight_source = "Finance Actuals CSV"
        else:
            # Supabase WC-only for current/future months without finance upload
            seed_revenue = m_data.get("revenue", 0)  # = wc_revenue after above changes
            other_revenue = 0
            discounts = 0  # WC order totals are already post-discount
            # Freight revenue sourcing hierarchy for non-actuals months:
            #   1) Current month → live WC shipping_total MTD
            #   2) Open closed month → backfilled WC shipping_total (pulled above)
            #   3) Fallback → yearly budget prorate
            if mk == cur_month_key:
                revenue_freight = mtd_shipping_collected
                revenue_freight_source = "WooCommerce shipping_total (MTD live)"
            elif open_closed_shipping.get(mk) is not None:
                revenue_freight = open_closed_shipping[mk]
                revenue_freight_source = "WooCommerce shipping_total (backfill)"
            else:
                revenue_freight = bud.get("freight_revenue", 0)
                revenue_freight_source = "Yearly Budget Breakdown"
            act_revenue = seed_revenue + other_revenue + revenue_freight + discounts

            seed_cogs = m_data.get("cogs", 0)  # = WC-only daily_cogs after above changes
            other_cogs = 0
            inventory_adjustment = 0
            # Freight COGS: Shippo transactions are the base cost. When we have a
            # discount ratio (avg of finance-booked cogs_freight ÷ Shippo quote
            # across closed months), apply it to bridge Shippo records to how
            # finance will book the month.
            if act_shipping:
                month_shipments = m_data.get("orders", 0)
                cogs_freight = round(act_shipping * SHIPPO_RATE_MULTIPLIER + SHIPPO_WEIGHT_SURCHARGE * month_shipments, 2)
                cogs_freight_source = f"Estimated: Shippo quote × {SHIPPO_RATE_MULTIPLIER} + ${SHIPPO_WEIGHT_SURCHARGE:.2f} × {month_shipments} shipments"
            else:
                cogs_freight = 0
                cogs_freight_source = "Shippo API (no data)"
            act_cogs = seed_cogs + other_cogs + inventory_adjustment + cogs_freight
            source_tag = "supabase_wc" if mk == cur_month_key or m_data.get("revenue") else "budget"

        # ── Gross Profit: Revenue (incl freight, net of discounts) − COGS (incl freight) ──
        act_gross_profit = act_revenue - act_cogs

        # Fixed costs: actuals if available, budget otherwise
        # Helper: use actuals value if present, else budget value
        def pick(key, default=0):
            return act.get(key, bud.get(key, default))

        warehouse = pick("warehouse")
        farm = pick("farm")
        collections = pick("collections")
        total_production = pick("total_production", warehouse + farm + collections)
        sma_salaries = pick("sma_salaries")
        marketing = pick("marketing")
        development = pick("development")
        ga_salaries = pick("ga_salaries")
        professional_fees = pick("professional_fees")
        insurance = pick("insurance")
        travel_entertainment = pick("travel_entertainment")
        utilities_supplies = pick("utilities_supplies")
        corporate_allocation = pick("corporate_allocation")
        ga_other = pick("ga_other")
        total_ga = pick("total_ga", ga_salaries + professional_fees + insurance + travel_entertainment + utilities_supplies + corporate_allocation + ga_other)

        # Computed P&L
        total_sma = sma_salaries + marketing + act_ad_spend + development
        total_opex = total_production + total_sma + total_ga
        net_income = act_gross_profit - total_opex

        # Budget comparisons
        bud_revenue = bud.get("net_revenue", 0)
        bud_gross = bud.get("gross_margin", 0)
        bud_opex = bud.get("total_opex", 0)
        bud_net_income = bud.get("net_income", 0)
        bud_ebitda = bud.get("ebitda", 0)
        bud_advertising = bud.get("ad_spend", bud.get("advertising", 0))

        depreciation = pick("depreciation")
        amortization = pick("amortization")
        interest = pick("interest")
        tax = pick("tax")
        other_income = pick("other_income")
        ebitda = net_income + depreciation + amortization + interest + tax

        pnl_months.append({
            "month": mk,
            "source": source_tag,  # "actuals" | "supabase_wc" | "budget"
            # Revenue (granular line items for new P&L design)
            "seed_revenue": round(seed_revenue, 2),
            "other_revenue": round(other_revenue, 2),
            "revenue_freight": round(revenue_freight, 2),
            "discounts": round(discounts, 2),
            "revenue": round(act_revenue, 2),  # Net Revenue (seed + other + freight + discounts)
            "budget_revenue": round(bud_revenue, 2),
            # COGS (granular)
            "seed_cogs": round(seed_cogs, 2),
            "other_cogs": round(other_cogs, 2),
            "inventory_adjustment": round(inventory_adjustment, 2),
            "cogs_freight": round(cogs_freight, 2),
            "cogs": round(act_cogs, 2),  # Total COGS (seed + other + inv_adj + freight)
            "budget_cogs": round(bud.get("total_cogs", 0), 2),
            "shippo_freight": round(act_shipping, 2),
            # Data-source provenance per category (for tooltips)
            "source_revenue": "Finance Actuals CSV" if has_actuals else ("WooCommerce API (via Supabase)" if mk == cur_month_key else "Supabase daily_summary (WC only)"),
            "source_cogs": "Finance Actuals CSV" if has_actuals else "Supabase daily_cogs (WC channel)",
            "source_freight_cogs": cogs_freight_source,
            "source_freight_revenue": revenue_freight_source,
            "freight_cogs_ratio": SHIPPO_RATE_MULTIPLIER if not has_actuals else None,
            # Gross Profit
            "gross_profit": round(act_gross_profit, 2),
            "budget_gross_profit": round(bud_gross, 2),
            "gross_margin_pct": round(act_gross_profit / act_revenue * 100, 1) if act_revenue else 0,
            # Operating Expenses
            "production_warehouse": round(total_production, 2),
            "warehouse": round(warehouse, 2),
            "advertising": round(act_ad_spend, 2),
            "budget_advertising": round(bud_advertising, 2),
            "marketing": round(marketing, 2),
            "sma_salaries": round(sma_salaries, 2),
            "development": round(development, 2),
            "total_sma": round(total_sma, 2),
            "ga_salaries": round(ga_salaries, 2),
            "professional_fees": round(professional_fees, 2),
            "insurance": round(insurance, 2),
            "travel_entertainment": round(travel_entertainment, 2),
            "utilities_supplies": round(utilities_supplies, 2),
            "corporate_allocation": round(corporate_allocation, 2),
            "ga_other": round(ga_other, 2),
            "total_ga": round(total_ga, 2),
            "total_opex": round(total_opex, 2),
            "budget_opex": round(bud_opex, 2),
            # Net Income
            "net_income": round(net_income, 2),
            "budget_net_income": round(bud_net_income, 2),
            # EBITDA
            "depreciation": round(depreciation, 2),
            "ebitda": round(ebitda, 2),
            "budget_ebitda": round(bud_ebitda, 2),
        })

    # YTD totals for P&L
    def _pnl_sum(key):
        return round(sum(m.get(key, 0) for m in pnl_months), 2)

    pnl_ytd = {k: _pnl_sum(k) for k in [
        "revenue", "budget_revenue", "revenue_freight", "cogs", "budget_cogs", "cogs_freight",
        "seed_revenue", "other_revenue", "discounts",
        "seed_cogs", "other_cogs", "inventory_adjustment",
        "gross_profit", "budget_gross_profit",
        "production_warehouse", "warehouse", "advertising", "budget_advertising",
        "marketing", "sma_salaries", "development", "total_sma",
        "ga_salaries", "professional_fees", "insurance", "travel_entertainment",
        "utilities_supplies", "corporate_allocation", "ga_other", "total_ga",
        "total_opex", "budget_opex", "net_income", "budget_net_income",
        "depreciation", "ebitda", "budget_ebitda",
    ]}
    pnl_ytd["gross_margin_pct"] = round(pnl_ytd["gross_profit"] / pnl_ytd["revenue"] * 100, 1) if pnl_ytd["revenue"] else 0

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
        "lm": {
            "cy": {
                "revenue": lm_cy_totals["revenue"],
                "orders": lm_cy_totals["orders"],
                "ad_spend": lm_cy_totals["ad_spend"],
                "mer": lm_cy_totals["mer"],
                "cogs": lm_cy_totals["cogs"],
                "shipping": lm_cy_totals["shipping"],
                "net_revenue": lm_cy_totals["net_revenue"],
                "wc_revenue": lm_cy_totals["wc_revenue"],
                "amazon_revenue": lm_cy_totals["amazon_revenue"],
                "walmart_revenue": lm_cy_totals["walmart_revenue"],
                "platform_fees": lm_cy_totals["platform_fees"],
                "gross_profit": lm_cy_totals["gross_profit"],
                "gross_margin_pct": lm_cy_totals["gross_margin_pct"],
                "cm1": lm_cy_totals["cm1"],
                "cm2": lm_cy_totals["cm2"],
                "cm2_pct": lm_cy_totals["cm2_pct"],
                "aov": lm_aov,
                "new_customers": new_customers_lm,
                "new_customer_cac": lm_new_cac,
            },
            "ly": {
                "revenue": lm_ly_totals["revenue"],
                "orders": lm_ly_totals["orders"],
                "ad_spend": lm_ly_totals["ad_spend"],
            },
            "budget": lm_budget,
            "daily_cy": lm_daily_cy,
            "daily_ly": lm_daily_ly,
        },
        "ytd": {
            "months": ytd_months,
            "totals_cy": ytd_totals_cy,
            "totals_ly": ytd_totals_ly,
            "totals_budget": ytd_totals_budget,
        },
        "pnl": {
            "months": pnl_months,
            "ytd": pnl_ytd,
        },
    }
    _write_json("reporting.json", result)
    print(f"  MTD CY revenue: ${cy_totals['revenue']:,.2f} | orders: {cy_totals['orders']}")
    print(f"  P&L months: {len(pnl_months)} | YTD Net Income: ${pnl_ytd.get('net_income', 0):,.2f}")
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
    """Pull Amazon 30d data from Supabase v_amazon_30d view."""
    print("\n[Amazon] Querying Supabase v_amazon_30d...")

    try:
        rows = _supabase_get("v_amazon_30d", {"select": "*", "order": "report_date.asc"})
    except Exception as e:
        print(f"  [WARN] Supabase v_amazon_30d failed: {e}")
        rows = []

    if not rows:
        print("  [SKIP] No Amazon data in Supabase")
        _write_json("amazon.json", {
            "as_of": TODAY_STR,
            "last_30d": {"revenue": 0, "orders": 0, "aov": 0},
            "daily": [],
            "account_health": {"defect_rate": 0, "cancellation_rate": 0, "late_shipment_rate": 0, "status": "Good"},
            "active_count": None,
            "top_products": [],
            "issues": ["No Amazon data in Supabase"],
        })
        return False

    total_revenue = sum(float(r.get("revenue") or 0) for r in rows)
    total_orders = sum(int(r.get("orders") or 0) for r in rows)
    aov = round(total_revenue / total_orders, 2) if total_orders else 0

    daily = [
        {
            "date": r["report_date"],
            "revenue": round(float(r.get("revenue") or 0), 2),
            "orders": int(r.get("orders") or 0),
        }
        for r in rows
    ]

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
        "top_products": [],  # Not available from Supabase — skipped
        "issues": [],
    }
    _write_json("amazon.json", result)
    print(f"  Orders: {total_orders} | Revenue: ${total_revenue:,.2f} (from Supabase)")
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
    """Pull Walmart 30d data from Supabase v_walmart_30d view."""
    print("\n[Walmart] Querying Supabase v_walmart_30d...")

    try:
        rows = _supabase_get("v_walmart_30d", {"select": "*", "order": "report_date.asc"})
    except Exception as e:
        print(f"  [WARN] Supabase v_walmart_30d failed: {e}")
        rows = []

    if not rows:
        print("  [SKIP] No Walmart data in Supabase")
        _write_json("walmart.json", {
            "as_of": TODAY_STR,
            "last_30d": {"revenue": 0, "orders": 0, "aov": 0},
            "daily": [],
            "active_count": None,
            "top_products": [],
            "issues": ["No Walmart data in Supabase"],
        })
        return False

    total_revenue = sum(float(r.get("revenue") or 0) for r in rows)
    total_orders = sum(int(r.get("orders") or 0) for r in rows)
    aov = round(total_revenue / total_orders, 2) if total_orders else 0

    daily = [
        {
            "date": r["report_date"],
            "revenue": round(float(r.get("revenue") or 0), 2),
            "orders": int(r.get("orders") or 0),
        }
        for r in rows
    ]

    # Active item count — still pull from Walmart API (fast, single call)
    active_count = None
    if WM_CLIENT_ID and WM_CLIENT_SECRET:
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
        "top_products": [],  # Not available from Supabase — skipped
        "issues": [],
    }
    _write_json("walmart.json", result)
    print(f"  Orders: {total_orders} | Revenue: ${total_revenue:,.2f} | Active items: {active_count} (from Supabase)")
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


def _fb_query(fb_token, sql):
    """Execute a SQL query against Fishbowl and return the JSON array."""
    import urllib.request as _urllib_req
    req = _urllib_req.Request(
        f"{FB_BASE}/api/data-query",
        data=sql.encode("utf-8"),
        method="GET",
    )
    req.add_header("Authorization", f"Bearer {fb_token}")
    req.add_header("Content-Type", "text/plain")
    with _urllib_req.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result if isinstance(result, list) else []


def _compute_runway(raw_rows, velocity_map, days_remaining_q1, q2_days):
    """Given raw Fishbowl rows and a velocity map, compute runway items + summary."""
    items = []
    red_count = yellow_count = green_count = 0

    for row in raw_rows:
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

    summary = {
        "total_skus": len(items),
        "red_count": red_count,
        "yellow_count": yellow_count,
        "green_count": green_count,
    }
    return items, summary


def _load_amazon_velocity():
    """Compute Amazon daily velocity from amazon.json daily data (last 14 days)."""
    amz_path = OUT_DIR / "amazon.json"
    if not amz_path.exists():
        return {}

    try:
        with open(amz_path) as f:
            data = json.load(f)
        daily = data.get("daily", [])
        if len(daily) < 2:
            return {}

        # Use last 14 days of data for velocity
        recent = daily[-14:]
        total_orders = sum(d.get("orders", 0) for d in recent)
        num_days = len(recent)
        if num_days == 0:
            return {}

        # Amazon velocity is order-level (not SKU-level) since we don't have
        # per-SKU daily data. Return as a single aggregate.
        return {
            "daily_orders": round(total_orders / num_days, 1),
            "daily_revenue": round(sum(d.get("revenue", 0) for d in recent) / num_days, 2),
            "period_days": num_days,
        }
    except Exception:
        return {}


def _pull_wc_order_tracking():
    """Pull WooCommerce order fulfillment metrics for last 30 days."""
    print("\n[WC Orders] Pulling fulfillment tracking...")
    if not WC_CK or not WC_CS:
        print("  [SKIP] WC credentials not configured")
        return None

    now = datetime.utcnow()
    after = (now - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00")

    all_orders = []
    for status in ("completed", "processing", "on-hold"):
        page = 1
        while True:
            try:
                resp = _wc_get("/orders", {
                    "status": status,
                    "after": after,
                    "per_page": 100,
                    "page": page,
                })
                data = resp.json()
                if not data:
                    break
                all_orders.extend(data)
                total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
                if page >= total_pages:
                    break
                page += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"  [WARN] WC order pull failed (status={status}, page={page}): {e}")
                break

    total = len(all_orders)
    fulfilled = 0
    backorders = 0
    unfulfilled_lt_1d = 0
    unfulfilled_lt_5d = 0
    unfulfilled_gt_10d = 0
    unfulfilled_5_to_10d = 0

    for order in all_orders:
        status = order.get("status", "")
        if status == "completed":
            fulfilled += 1
        else:
            # Check if any line item is backordered
            is_backorder = False
            for item in order.get("line_items", []):
                if item.get("backordered", False):
                    is_backorder = True
                    break

            if is_backorder:
                backorders += 1
                continue

            # Calculate business days since order was placed
            date_created = order.get("date_created", "")
            if date_created:
                try:
                    order_dt = datetime.fromisoformat(date_created.replace("Z", "+00:00"))
                    delta = now - order_dt.replace(tzinfo=None)
                    days = delta.days
                    # Rough business day conversion (5/7)
                    biz_days = int(days * 5 / 7)
                    if biz_days < 1:
                        unfulfilled_lt_1d += 1
                    elif biz_days < 5:
                        unfulfilled_lt_5d += 1
                    elif biz_days > 10:
                        unfulfilled_gt_10d += 1
                    else:
                        unfulfilled_5_to_10d += 1
                except Exception:
                    unfulfilled_lt_5d += 1  # Default bucket

    result = {
        "total_30d": total,
        "fulfilled": fulfilled,
        "backorders": backorders,
        "unfulfilled_lt_1d": unfulfilled_lt_1d,
        "unfulfilled_lt_5d": unfulfilled_lt_5d,
        "unfulfilled_5_to_10d": unfulfilled_5_to_10d,
        "unfulfilled_gt_10d": unfulfilled_gt_10d,
    }
    print(f"  Total: {total} | Fulfilled: {fulfilled} | Backorders: {backorders} | Unfulfilled <1d: {unfulfilled_lt_1d} | <5d: {unfulfilled_lt_5d} | >10d: {unfulfilled_gt_10d}")
    return result


def generate_inventory():
    """Query Fishbowl inventory by location group and compute velocity/runway.

    Separates local warehouse (Main) from Amazon FBA inventory.
    Local velocity comes from WooCommerce ABC analysis.
    FBA velocity comes from Amazon SP-API daily order data.
    """
    print("\n[Fishbowl] Querying inventory by location group...")

    # Step 1: Login to Fishbowl
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
            "items": [], "fba_items": [],
            "summary": {"total_skus": 0, "red_count": 0, "yellow_count": 0, "green_count": 0},
            "fba_summary": {"total_skus": 0, "red_count": 0, "yellow_count": 0, "green_count": 0},
            "order_tracking": None,
            "warning": f"Fishbowl login failed: {e}",
        })
        return False

    # Step 2: Query inventory with location group breakdown
    raw_local = []
    raw_fba = []
    try:
        # Single query with location group info
        sql = (
            "SELECT p.num AS sku, p.description AS name, "
            "qoh.qty AS qty, lg.name AS location_group "
            "FROM qtyonhand qoh "
            "JOIN part p ON p.id = qoh.partid "
            "JOIN locationgroup lg ON lg.id = qoh.locationgroupid "
            "WHERE qoh.qty > 0 AND p.activeFlag = 1 "
            "ORDER BY p.num;"
        )
        raw_inventory = _fb_query(fb_token, sql)
        print(f"  Fishbowl returned {len(raw_inventory)} rows")

        # Split by location group
        for row in raw_inventory:
            lg = str(row.get("location_group") or row.get("LOCATION_GROUP") or "").strip()
            if lg == "Amazon FBA":
                raw_fba.append(row)
            else:
                raw_local.append(row)

        print(f"  Local: {len(raw_local)} rows | Amazon FBA: {len(raw_fba)} rows")
    except Exception as e:
        print(f"  [WARN] Fishbowl query failed: {e}")
        _write_json("inventory.json", {
            "as_of": TODAY_STR,
            "items": [], "fba_items": [],
            "summary": {"total_skus": 0, "red_count": 0, "yellow_count": 0, "green_count": 0},
            "fba_summary": {"total_skus": 0, "red_count": 0, "yellow_count": 0, "green_count": 0},
            "order_tracking": None,
            "warning": f"Fishbowl query failed: {e}",
        })
    finally:
        if fb_token:
            try:
                requests.post(f"{FB_BASE}/api/logout",
                    headers={"Authorization": f"Bearer {fb_token}"}, timeout=10)
            except Exception:
                pass
        if not raw_local and not raw_fba:
            return False

    # Step 3: Load velocity — WC velocity for local, Amazon velocity for FBA
    wc_velocity_map = _load_abc_velocity()
    amz_velocity = _load_amazon_velocity()

    # For FBA, distribute aggregate Amazon velocity proportionally by stock
    # (We don't have per-SKU Amazon velocity, so use aggregate orders/day)
    fba_velocity_map = {}
    if amz_velocity and amz_velocity.get("daily_orders", 0) > 0:
        # Calculate total FBA stock to distribute velocity proportionally
        total_fba_qty = 0
        for row in raw_fba:
            try:
                total_fba_qty += float(row.get("qty") or row.get("QTY") or 0)
            except (TypeError, ValueError):
                pass
        if total_fba_qty > 0:
            daily_orders = amz_velocity["daily_orders"]
            for row in raw_fba:
                sku = str(row.get("sku") or row.get("SKU") or "").strip()
                try:
                    qty = float(row.get("qty") or row.get("QTY") or 0)
                except (TypeError, ValueError):
                    qty = 0
                # Proportional velocity: this SKU's share of total FBA stock × daily orders
                fba_velocity_map[sku] = round((qty / total_fba_qty) * daily_orders, 2)

    # Step 4: Compute Q1/Q2 runway
    today = TODAY
    q1_end = date(today.year, 3, 31)
    days_remaining_q1 = max(0, (q1_end - today).days) if today <= q1_end else 0
    q2_days = 91

    local_items, local_summary = _compute_runway(raw_local, wc_velocity_map, days_remaining_q1, q2_days)
    fba_items, fba_summary = _compute_runway(raw_fba, fba_velocity_map, days_remaining_q1, q2_days)

    # Step 5: Pull WC order tracking
    order_tracking = _pull_wc_order_tracking()

    result = {
        "as_of": TODAY_STR,
        "items": local_items,
        "fba_items": fba_items,
        "summary": local_summary,
        "fba_summary": fba_summary,
        "fba_velocity": amz_velocity,
        "order_tracking": order_tracking,
    }
    _write_json("inventory.json", result)
    print(f"  Local — SKUs: {local_summary['total_skus']} | Red: {local_summary['red_count']} | Yellow: {local_summary['yellow_count']} | Green: {local_summary['green_count']}")
    print(f"  FBA   — SKUs: {fba_summary['total_skus']} | Red: {fba_summary['red_count']} | Yellow: {fba_summary['yellow_count']} | Green: {fba_summary['green_count']}")
    return True


# ══════════════════════════════════════════════════════════════
# 6b. SHIPPING.JSON — Shipping cost insights from Shippo + WC
# ══════════════════════════════════════════════════════════════

def _carrier_from_tracking(tracking):
    """Infer carrier from tracking number prefix (avoids Shippo rate API call)."""
    if not tracking:
        return "Unknown"
    t = tracking.strip()
    if t.startswith("1Z"):
        return "UPS"
    if t.startswith("94") or t.startswith("92") or t.startswith("93") or t.startswith("420"):
        return "USPS"
    if len(t) in (12, 15, 20, 22) and t.isdigit():
        return "FEDEX"
    # Check common FedEx patterns
    if len(t) >= 12 and t[:2].isdigit():
        return "FEDEX"
    return "UPS"  # Default — Nature's Seed uses UPS 98%+ of the time


def generate_shipping():
    """Pull shipping data from Supabase (daily totals) + Shippo (carrier breakdown).

    Uses Supabase daily_shipping for fast MTD/YTD totals, and Shippo transaction
    list (no rate API calls) for carrier breakdown by inferring carrier from
    tracking number prefixes. This avoids thousands of slow /rates/ API calls.

    Writes shipping.json with:
      - MTD/YTD KPI totals (collected, paid, net, avg cost per order)
      - Carrier breakdown (YTD totals, % of shipments)
      - Weekly avg cost per shipment by carrier (for Chart.js line charts)
    """
    print("\n[Shipping] Pulling shipping data (Supabase + Shippo carriers)...")

    today = TODAY
    ytd_start = date(today.year, 1, 1)
    mtd_start = date(today.year, today.month, 1)

    # ── Step 1: Get daily shipping totals from Supabase ────────
    sb_shipping_ytd = []
    try:
        url = f"{SUPABASE_URL}/rest/v1/daily_shipping"
        params = {
            "select": "report_date,total_cost,shipment_count",
            "report_date": f"gte.{ytd_start}",
            "order": "report_date.asc",
        }
        resp = requests.get(url, headers={
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json",
        }, params=params, timeout=15)
        if resp.status_code == 200:
            sb_shipping_ytd = resp.json()
            print(f"  Supabase: {len(sb_shipping_ytd)} daily_shipping rows (YTD)")
        else:
            print(f"  [WARN] Supabase daily_shipping: {resp.status_code}")
    except Exception as e:
        print(f"  [WARN] Supabase shipping pull failed: {e}")

    # Compute MTD/YTD Shippo totals from Supabase
    shippo_ytd_paid = 0
    ytd_shipments = 0
    shippo_mtd_paid = 0
    mtd_shipments = 0
    for row in sb_shipping_ytd:
        cost = float(row.get("total_cost") or 0)
        count = int(row.get("shipment_count") or 0)
        rd = row.get("report_date", "")
        shippo_ytd_paid += cost
        ytd_shipments += count
        if rd >= str(mtd_start):
            shippo_mtd_paid += cost
            mtd_shipments += count

    # Use finance actuals for completed months, Shippo for current month
    # Load actuals to get real freight costs
    actuals_csv = _load_actuals_csv()
    completed_months_paid = 0
    for mk, act_data in actuals_csv.items():
        if mk < str(mtd_start)[:7]:  # Only completed months (before current)
            completed_months_paid += act_data.get("cogs_freight", 0)

    # YTD paid = finance actuals for completed months + estimated cost for current month.
    # Formula: shippo_quote × 0.783 + $2.00 × shipments
    shippo_mtd_paid_est = round(shippo_mtd_paid * SHIPPO_RATE_MULTIPLIER + SHIPPO_WEIGHT_SURCHARGE * mtd_shipments, 2)
    ytd_paid = completed_months_paid + shippo_mtd_paid_est
    mtd_paid = shippo_mtd_paid_est  # Current month always uses Shippo (no actuals yet)
    print(f"  Paid: completed months (finance) ${completed_months_paid:,.2f} + MTD (Shippo×{SHIPPO_RATE_MULTIPLIER}+$2×{mtd_shipments}) ${shippo_mtd_paid_est:,.2f} = YTD ${ytd_paid:,.2f}")

    # ── Step 2: Pull WC shipping collected (MTD + YTD) ─────────
    # Use finance actuals revenue_freight for completed months + WC API for current month
    wc_shipping_mtd = 0.0
    wc_shipping_ytd = 0.0
    wc_orders_count_mtd = 0
    wc_orders_count_ytd = 0

    # Revenue freight from finance actuals (completed months)
    for mk, act_data in actuals_csv.items():
        wc_shipping_ytd += act_data.get("freight_revenue", 0)

    # Current month: pull from WC API
    try:
        mtd_orders = _pull_wc_orders_range(str(mtd_start), str(today))
        for order in mtd_orders:
            ship_total = float(order.get("shipping_total") or 0)
            wc_shipping_mtd += ship_total
            wc_orders_count_mtd += 1
        wc_shipping_ytd += wc_shipping_mtd
        wc_orders_count_ytd = wc_orders_count_mtd  # Only MTD orders pulled
        print(f"  WC shipping collected: MTD ${wc_shipping_mtd:,.2f} | YTD ${wc_shipping_ytd:,.2f}")
    except Exception as e:
        print(f"  [WARN] WC shipping pull failed: {e} — using finance actuals only")

    # ── Step 3: Pull Shippo transactions for carrier breakdown ─
    # Only need tracking numbers + dates + status (NO rate API calls)
    carrier_by_week = {}  # {carrier: {week: {"cost": x, "count": y}}}
    carrier_totals = {}
    from collections import defaultdict

    if SHIPPO_API_KEY:
        headers = {"Authorization": f"ShippoToken {SHIPPO_API_KEY}"}
        seen_tracking = set()
        url = "https://api.goshippo.com/transactions/"
        params = {"results": 200}
        pages_checked = 0
        all_carrier_txns = []

        while url:
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                if resp.status_code != 200:
                    print(f"  [WARN] Shippo: {resp.status_code}")
                    break
                data = resp.json()
                pages_checked += 1

                found_older = False
                for txn in data.get("results", []):
                    txn_date = (txn.get("object_created") or "")[:10]
                    if txn_date < str(ytd_start):
                        found_older = True
                        break
                    if txn.get("status") != "SUCCESS":
                        continue
                    tracking = txn.get("tracking_number", "")
                    if tracking and tracking in seen_tracking:
                        continue
                    if tracking:
                        seen_tracking.add(tracking)
                    carrier = _carrier_from_tracking(tracking)
                    all_carrier_txns.append({"date": txn_date, "carrier": carrier})

                if found_older:
                    break
                url = data.get("next")
                params = {}
                time.sleep(0.3)
            except Exception as e:
                print(f"  [WARN] Shippo pagination error: {e}")
                break

        print(f"  Shippo: {len(all_carrier_txns)} transactions for carrier breakdown ({pages_checked} pages)")

        # Build carrier totals and weekly breakdown
        # Distribute Supabase daily costs proportionally by carrier count per day
        daily_carrier_counts = defaultdict(lambda: defaultdict(int))  # {date: {carrier: count}}
        for txn in all_carrier_txns:
            daily_carrier_counts[txn["date"]][txn["carrier"]] += 1

        # Map Supabase daily costs to carriers proportionally
        sb_daily_map = {row["report_date"]: float(row.get("total_cost") or 0) for row in sb_shipping_ytd}

        carrier_totals = defaultdict(lambda: {"paid": 0, "count": 0})
        weekly_carrier = defaultdict(lambda: defaultdict(lambda: {"cost": 0, "count": 0}))

        for txn in all_carrier_txns:
            d = txn["date"]
            carrier = txn["carrier"]
            carrier_totals[carrier]["count"] += 1

            # Proportional cost from Supabase daily total
            day_total_cost = sb_daily_map.get(d, 0)
            day_total_txns = sum(daily_carrier_counts[d].values()) or 1
            proportional_cost = day_total_cost * (daily_carrier_counts[d][carrier] / day_total_txns) / daily_carrier_counts[d][carrier] if daily_carrier_counts[d][carrier] > 0 else 0
            carrier_totals[carrier]["paid"] += proportional_cost

            # Weekly bucket
            try:
                dt = datetime.strptime(d, "%Y-%m-%d").date()
                iso_year, iso_week, _ = dt.isocalendar()
                week_label = f"{iso_year}-W{iso_week:02d}"
            except ValueError:
                continue
            weekly_carrier[carrier][week_label]["cost"] += proportional_cost
            weekly_carrier[carrier][week_label]["count"] += 1

    # ── Step 4: Build KPIs ─────────────────────────────────────
    def _kpi(paid, shipments, collected, order_count):
        return {
            "shipping_collected": round(collected, 2),
            "shipping_paid": round(paid, 2),
            "shipping_net": round(collected - paid, 2),
            "shipment_count": shipments,
            "avg_cost_per_order": round(paid / shipments, 2) if shipments else 0,
            "wc_order_count": order_count,
        }

    mtd_kpi = _kpi(mtd_paid, mtd_shipments, wc_shipping_mtd, wc_orders_count_mtd)
    ytd_kpi = _kpi(ytd_paid, ytd_shipments, wc_shipping_ytd, wc_orders_count_ytd)

    # ── Step 5: Carrier list ───────────────────────────────────
    total_shipments_count = sum(c["count"] for c in carrier_totals.values()) or 1
    carriers = []
    for name, stats in sorted(carrier_totals.items(), key=lambda x: -x[1]["paid"]):
        carriers.append({
            "carrier": name,
            "total_paid": round(stats["paid"], 2),
            "shipment_count": stats["count"],
            "pct_of_shipments": round(stats["count"] / total_shipments_count * 100, 1),
            "avg_cost_per_shipment": round(stats["paid"] / stats["count"], 2) if stats["count"] else 0,
        })

    # ── Step 6: Weekly avg cost per shipment by carrier (charts) ─
    weekly_cost_per_shipment = {}
    for carrier, weeks in weekly_carrier.items():
        sorted_weeks = sorted(weeks.keys())
        weekly_cost_per_shipment[carrier] = {
            "weeks": sorted_weeks,
            "values": [
                round(weeks[w]["cost"] / weeks[w]["count"], 2) if weeks[w]["count"] > 0 else 0
                for w in sorted_weeks
            ],
        }

    # ── Write output ───────────────────────────────────────────
    output = {
        "as_of": TODAY_STR,
        "mtd": mtd_kpi,
        "ytd": ytd_kpi,
        "carriers": carriers,
        "weekly_cost_per_lb": weekly_cost_per_shipment,  # Keep key name for frontend compat
    }

    _write_json("shipping.json", output)
    print(f"  MTD paid: ${mtd_kpi['shipping_paid']:,.2f} ({mtd_kpi['shipment_count']} shipments)")
    print(f"  YTD paid: ${ytd_kpi['shipping_paid']:,.2f} ({ytd_kpi['shipment_count']} shipments)")
    print(f"  Carriers: {', '.join(c['carrier'] for c in carriers)}")
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
    """Generate marketing channel metrics from Supabase views.

    Reads from:
      - v_marketing_12m      — 12-month aggregate totals
      - v_customer_summary_12m — customer counts (unique, new, returning, LTV)
      - v_monthly_channel     — monthly revenue by channel
      - v_monthly_ad_spend    — monthly ad spend
      - v_daily_ad_spend_90d  — daily ad spend (last 90 days)
      - v_monthly_shipping    — monthly shipping costs
      - v_monthly_cogs        — monthly COGS
      - daily_sales (table)   — WC daily revenue for 90-day table
    """
    print("\n[Marketing] Querying Supabase views...")

    today = TODAY
    period_start = today - timedelta(days=365)
    period_90d_start = today - timedelta(days=90)
    yesterday = today - timedelta(days=1)

    # ── 1. Fetch all Supabase views in sequence ──────────────
    # v_marketing_12m — aggregate totals
    print("  Fetching v_marketing_12m...")
    try:
        mkt_rows = _supabase_get("v_marketing_12m", {"select": "*"})
        mkt = mkt_rows[0] if mkt_rows else {}
    except Exception as e:
        print(f"    [ERR] v_marketing_12m failed: {e}")
        mkt = {}

    if not mkt:
        print("    [SKIP] No marketing data — writing empty marketing.json")
        _write_json("marketing.json", {"generated_at": TODAY_STR, "error": "no_data"})
        return True

    total_revenue = float(mkt.get("total_revenue") or 0)
    total_orders = int(mkt.get("total_orders") or 0)
    wc_revenue = float(mkt.get("wc_revenue") or 0)
    total_ad_spend = float(mkt.get("total_ad_spend") or 0)
    total_conv_value = float(mkt.get("total_conv_value") or 0)
    total_cogs = float(mkt.get("total_cogs") or 0)
    total_shipping = float(mkt.get("total_shipping") or 0)

    print(f"    12m totals: revenue=${total_revenue:,.2f} orders={total_orders} ad_spend=${total_ad_spend:,.2f}")

    # v_customer_summary_12m — customer counts
    print("  Fetching v_customer_summary_12m...")
    try:
        cust_rows = _supabase_get("v_customer_summary_12m", {"select": "*"})
        cust = cust_rows[0] if cust_rows else {}
    except Exception as e:
        print(f"    [ERR] v_customer_summary_12m failed: {e}")
        cust = {}

    reg_unique = int(cust.get("unique_customers") or 0)
    reg_new = int(cust.get("new_customers") or 0)
    reg_returning = int(cust.get("returning_customers") or 0)

    # Registered customers miss guest orders (customer_id=0).
    # Use total_orders with industry-standard ratio: ~80% of orders are unique customers.
    # This matches Nature's Seed historical data (~9,400 unique from ~11,500 orders).
    unique_customers = reg_unique if reg_unique > 1000 else int(total_orders * 0.82)
    # Most seed customers are first-time buyers (~75-80% new).
    # Registered-only ratio skews low because repeat buyers register more.
    new_pct = 0.78 if reg_unique < 1000 else (reg_new / reg_unique)
    new_customers = int(unique_customers * new_pct)
    returning_customers = unique_customers - new_customers

    print(f"    Customers: {unique_customers} (new: {new_customers}, returning: {returning_customers})")

    # ── 2. Compute widget metrics ────────────────────────────
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

    # ── 3. Channel table (blended — single channel for now) ─
    channels = [{
        "name": "Google Ads",
        "cac": cac,
        "ltv": ltv,
        "ncac": ncac,
        "payback_months": payback,
        "revenue_contribution_pct": round(total_conv_value / total_revenue * 100, 1) if total_revenue else 0,
        "roas": roas,
    }]

    # ── 4. 90-day daily table ────────────────────────────────
    print("  Fetching v_daily_ad_spend_90d...")
    try:
        ads_daily_rows = _supabase_get("v_daily_ad_spend_90d", {"select": "*", "order": "report_date.asc"})
    except Exception as e:
        print(f"    [ERR] v_daily_ad_spend_90d failed: {e}")
        ads_daily_rows = []
    ads_by_date = {r.get("report_date", ""): r for r in ads_daily_rows}

    # Fetch CTV (vibe_co) daily spend from daily_ad_spend — may be empty until constraint fix
    print("  Fetching daily_ad_spend (vibe_co channel)...")
    ctv_by_date = {}
    try:
        url = f"{SUPABASE_URL}/rest/v1/daily_ad_spend"
        sb_headers = {"apikey": SUPABASE_KEY}
        sb_params = [
            ("report_date", f"gte.{period_90d_start}"),
            ("report_date", f"lte.{yesterday}"),
            ("channel", "eq.vibe_co"),
            ("select", "report_date,spend"),
        ]
        resp = requests.get(url, headers=sb_headers, params=sb_params, timeout=30)
        resp.raise_for_status()
        for r in resp.json():
            ctv_by_date[r["report_date"]] = float(r.get("spend", 0))
        if ctv_by_date:
            print(f"    Found {len(ctv_by_date)} days of CTV data")
        else:
            print("    No CTV data yet (constraint fix pending)")
    except Exception as e:
        print(f"    [WARN] CTV daily query failed: {e}")

    # WC daily revenue from Supabase daily_sales (90 days for daily table)
    try:
        url = f"{SUPABASE_URL}/rest/v1/daily_sales"
        sb_headers = {"apikey": SUPABASE_KEY}
        sb_params = [
            ("report_date", f"gte.{period_90d_start}"),
            ("report_date", f"lte.{yesterday}"),
            ("channel", "eq.woocommerce"),
            ("select", "report_date,revenue"),
        ]
        resp = requests.get(url, headers=sb_headers, params=sb_params, timeout=30)
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
        spend = float(ads.get("spend") or 0)
        conv_val = float(ads.get("conversions_value") or 0)
        wc_rev = wc_by_date.get(ds, 0)
        mer = round(wc_rev / spend, 2) if spend > 0 else None

        ctv_spend = ctv_by_date.get(ds, 0)
        total_spend = spend + ctv_spend

        daily_90d.append({
            "date": ds,
            "ad_spend": round(total_spend, 2),
            "ad_spend_google": round(spend, 2),
            "ad_spend_ctv": round(ctv_spend, 2),
            "channel_revenue": round(conv_val, 2),
            "wc_revenue": round(wc_rev, 2),
            "mer": round(wc_rev / total_spend, 2) if total_spend > 0 else None,
        })
        d += timedelta(days=1)

    # ── 5. 12-month monthly table ────────────────────────────
    print("  Fetching v_monthly_channel + v_monthly_ad_spend...")
    try:
        monthly_channel_rows = _supabase_get("v_monthly_channel", {"select": "*", "order": "month.asc"})
    except Exception as e:
        print(f"    [ERR] v_monthly_channel failed: {e}")
        monthly_channel_rows = []

    try:
        monthly_ad_rows = _supabase_get("v_monthly_ad_spend", {"select": "*", "order": "month.asc"})
    except Exception as e:
        print(f"    [ERR] v_monthly_ad_spend failed: {e}")
        monthly_ad_rows = []

    # Index monthly data by month key
    # Monthly WC revenue from v_monthly_channel (filter channel=woocommerce)
    monthly_wc_rev = {}
    for r in monthly_channel_rows:
        ch = (r.get("channel") or "").lower()
        month_key = (r.get("month") or "")[:7]
        if ch == "woocommerce" and month_key:
            monthly_wc_rev[month_key] = float(r.get("revenue") or 0)

    # Monthly ad spend from v_monthly_ad_spend (aggregate all channels — currently just google_ads)
    monthly_ads = {}
    for r in monthly_ad_rows:
        month_key = (r.get("month") or "")[:7]
        if not month_key:
            continue
        if month_key not in monthly_ads:
            monthly_ads[month_key] = {"spend": 0, "conversions_value": 0}
        monthly_ads[month_key]["spend"] += float(r.get("spend") or 0)
        monthly_ads[month_key]["conversions_value"] += float(r.get("conversions_value") or 0)

    # Monthly CTV spend — aggregate vibe_co from monthly_ad_rows
    monthly_ctv = {}
    for r in monthly_ad_rows:
        ch = (r.get("channel") or "").lower()
        month_key = (r.get("month") or "")[:7]
        if ch == "vibe_co" and month_key:
            monthly_ctv[month_key] = monthly_ctv.get(month_key, 0) + float(r.get("spend") or 0)

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

        # Customer counts per month not available from views — omit granular counts
        # (total counts come from v_customer_summary_12m at the top level)
        ctv_m = round(monthly_ctv.get(month_key, 0), 2)
        total_spend_m = round(spend + ctv_m, 2)
        mer = round(wc_rev / total_spend_m, 2) if total_spend_m > 0 else None

        monthly_12m.append({
            "month": month_key,
            "ad_spend": total_spend_m,
            "ad_spend_google": spend,
            "ad_spend_ctv": ctv_m,
            "channel_revenue": conv_val,
            "wc_revenue": wc_rev,
            "mer": mer,
            "customers": None,
            "new_customers": None,
            "cac": None,
            "ncac": None,
        })

        # Next month
        if d.month == 12:
            d = d.replace(year=d.year + 1, month=1)
        else:
            d = d.replace(month=d.month + 1)

    # ── 6. Write JSON ────────────────────────────────────────
    output = {
        "generated_at": TODAY_STR,
        "period_start": str(period_start),
        "period_end": str(yesterday),
        "total_customers": unique_customers,
        "new_customers": new_customers,
        "returning_customers": returning_customers,
        "total_revenue": round(total_revenue, 2),
        "total_ad_spend": round(total_ad_spend, 2),
        "total_cogs": round(total_cogs, 2),
        "total_shipping": round(total_shipping, 2),
        "widgets": widgets,
        "channels": channels,
        "daily_90d": daily_90d,
        "monthly_12m": monthly_12m,
    }

    _write_json("marketing.json", output)
    print(f"  [OK] marketing.json written (from Supabase views)")
    return True


# ══════════════════════════════════════════════════════════════
# CUSTOMERS (delegated to generate_customers.py)
# ══════════════════════════════════════════════════════════════

def _run_generate_customers():
    """Load and run generate_customers.py from the same directory."""
    import importlib.util
    script = Path(__file__).resolve().parent / "generate_customers.py"
    spec = importlib.util.spec_from_file_location("generate_customers", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.generate_customers()


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
        ("Amazon (Supabase)",     generate_amazon),
        ("Walmart (Supabase)",    generate_walmart),
        ("Inventory (Fishbowl)",  generate_inventory),
        ("Shipping (Shippo+WC)", generate_shipping),
        ("Notes (Markdown)",      generate_notes),
        ("Marketing (Supabase)",  generate_marketing),
        # Customers runs as separate CI job (generate_customers.py) — uncomment for local:
        # ("Customers (WC Orders)", _run_generate_customers),
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
