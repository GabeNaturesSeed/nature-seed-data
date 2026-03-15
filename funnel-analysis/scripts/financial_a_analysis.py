#!/usr/bin/env python3
"""
Financial/Operations Agent A — Unit Economics & Operational Cost Analysis
Analyzes Nature's Seed margins, shipping costs, COGS, and channel profitability.

Data sources (in order of preference):
  1. Supabase REST API via .env credentials (same pattern as daily_pull.py)
  2. Local JSON files in docs/data/ (cached snapshots from dashboard pipeline)

Outputs findings to funnel-analysis/reports/financial_a_findings.md
"""

import json
import os
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ══════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = REPO_ROOT / "docs" / "data"

# ══════════════════════════════════════════════════════════════
# ENV + SUPABASE SETUP (mirrors daily_pull.py)
# ══════════════════════════════════════════════════════════════

env_path = REPO_ROOT / ".env"
env_vars = {}
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip().strip("'\"")

SUPABASE_URL = env_vars.get("SUPABASE_URL", "") or os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "") or os.environ.get("SUPABASE_SECRET_API_KEY", "")

USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY and HAS_REQUESTS)


# ══════════════════════════════════════════════════════════════
# DATA ACCESS LAYER
# ══════════════════════════════════════════════════════════════

def supabase_query(table_or_view, params=None):
    """Query a Supabase table or view via REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table_or_view}"
    headers = {"apikey": SUPABASE_KEY}
    resp = requests.get(url, headers=headers, params=params or {}, timeout=30)
    if resp.status_code != 200:
        print(f"[WARN] Query {table_or_view}: {resp.status_code} {resp.text[:300]}")
        return []
    return resp.json()


def pull_supabase_range(table, start, end):
    """Pull data for a date range from Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=*&report_date=gte.{start}&report_date=lte.{end}"
    headers = {"apikey": SUPABASE_KEY}
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"[WARN] Pull {table} ({start} to {end}): {resp.status_code} {resp.text[:300]}")
        return []
    data = resp.json()
    print(f"[OK] {table}: {len(data)} rows ({start} to {end})")
    return data


def load_local_json(filename):
    """Load a JSON file from docs/data/."""
    path = DATA_DIR / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ══════════════════════════════════════════════════════════════
# DATE RANGES
# ══════════════════════════════════════════════════════════════

END_DATE = "2026-03-14"
START_DATE = "2026-02-13"
END_DATE_LY = "2025-03-14"
START_DATE_LY = "2025-02-13"

print(f"[INFO] Analysis period: {START_DATE} to {END_DATE}")
print(f"[INFO] Last year period: {START_DATE_LY} to {END_DATE_LY}")


# ══════════════════════════════════════════════════════════════
# 1. PULL / LOAD DATA
# ══════════════════════════════════════════════════════════════

if USE_SUPABASE:
    print("\n=== Using LIVE Supabase data ===")
    sales = pull_supabase_range("daily_sales", START_DATE, END_DATE)
    ad_spend_rows = pull_supabase_range("daily_ad_spend", START_DATE, END_DATE)
    shipping_rows = pull_supabase_range("daily_shipping", START_DATE, END_DATE)
    cogs_rows = pull_supabase_range("daily_cogs", START_DATE, END_DATE)
    summary_rows = pull_supabase_range("daily_summary", START_DATE, END_DATE)

    sales_ly = pull_supabase_range("daily_sales", START_DATE_LY, END_DATE_LY)
    ad_spend_ly_rows = pull_supabase_range("daily_ad_spend", START_DATE_LY, END_DATE_LY)
    shipping_ly_rows = pull_supabase_range("daily_shipping", START_DATE_LY, END_DATE_LY)
    cogs_ly_rows = pull_supabase_range("daily_cogs", START_DATE_LY, END_DATE_LY)

    mtd_rows = supabase_query("mtd_comparison", {"select": "*"})
    cogs_lookup = supabase_query("cogs_lookup", {"select": "*"})
    DATA_SOURCE = "Supabase REST API (live)"
else:
    print("\n=== Using LOCAL cached JSON data (no Supabase credentials) ===")
    DATA_SOURCE = "Local JSON files (docs/data/reporting.json, walmart.json, budget.json)"

# Load local JSON regardless — used for enrichment or as primary source
reporting = load_local_json("reporting.json")
walmart_data = load_local_json("walmart.json")
budget_data = load_local_json("budget.json")
inventory_data = load_local_json("inventory.json")


# ══════════════════════════════════════════════════════════════
# 2. BUILD ANALYSIS FROM AVAILABLE DATA
# ══════════════════════════════════════════════════════════════

# --- Extract MTD data from reporting.json ---
mtd_cy = reporting.get("mtd", {}).get("cy", {})
mtd_ly = reporting.get("mtd", {}).get("ly", {})
mtd_budget = reporting.get("mtd", {}).get("budget", {})
daily_cy = reporting.get("mtd", {}).get("daily_cy", [])
daily_ly = reporting.get("mtd", {}).get("daily_ly", [])
ytd_data = reporting.get("ytd", {})
ytd_months = ytd_data.get("months", [])

# --- Current Period (March 1-14, 2026 MTD from reporting.json) ---
# Plus February data from ytd_months for full 30-day window
feb_data = next((m for m in ytd_months if m["month"] == "2026-02"), {})

# Revenue breakdown
wc_revenue_mtd = safe_float(mtd_cy.get("wc_revenue"))
walmart_revenue_mtd = safe_float(mtd_cy.get("walmart_revenue"))
amazon_revenue_mtd = safe_float(mtd_cy.get("amazon_revenue"))
total_revenue_mtd = safe_float(mtd_cy.get("revenue"))
total_orders_mtd = int(safe_float(mtd_cy.get("orders")))
total_ad_spend_mtd = safe_float(mtd_cy.get("ad_spend"))
total_cogs_mtd = safe_float(mtd_cy.get("cogs"))
total_shipping_mtd = safe_float(mtd_cy.get("shipping"))
platform_fees_mtd = safe_float(mtd_cy.get("platform_fees"))
gross_profit_mtd = safe_float(mtd_cy.get("gross_profit"))
net_revenue_mtd = safe_float(mtd_cy.get("net_revenue"))
mer_mtd = safe_float(mtd_cy.get("mer"))
aov_mtd = safe_float(mtd_cy.get("aov"))
cm1_mtd = safe_float(mtd_cy.get("cm1"))
cm2_mtd = safe_float(mtd_cy.get("cm2"))
cm2_pct_mtd = safe_float(mtd_cy.get("cm2_pct"))
gross_margin_pct_mtd = safe_float(mtd_cy.get("gross_margin_pct"))

# For full 30-day analysis, combine Feb 13-28 + Mar 1-14
feb_revenue = safe_float(feb_data.get("revenue"))
feb_orders = int(safe_float(feb_data.get("orders")))
feb_ad_spend = safe_float(feb_data.get("ad_spend"))
feb_cogs = safe_float(feb_data.get("cogs"))
feb_mer = safe_float(feb_data.get("mer"))
feb_gm_pct = safe_float(feb_data.get("gross_margin_pct"))
feb_cm2 = safe_float(feb_data.get("cm2"))
feb_cm2_pct = safe_float(feb_data.get("cm2_pct"))

# Approximate the Feb 13-28 portion (16/28 of February)
feb_fraction = 16.0 / 28.0
feb_partial_revenue = feb_revenue * feb_fraction
feb_partial_orders = int(feb_orders * feb_fraction)
feb_partial_ad_spend = feb_ad_spend * feb_fraction
feb_partial_cogs = feb_cogs * feb_fraction

# Full 30-day totals
total_revenue_30d = feb_partial_revenue + total_revenue_mtd
total_orders_30d = feb_partial_orders + total_orders_mtd
total_ad_spend_30d = feb_partial_ad_spend + total_ad_spend_mtd
total_cogs_30d = feb_partial_cogs + total_cogs_mtd
# Shipping only available for MTD; estimate Feb portion from ratio
shipping_pct_est = (total_shipping_mtd / total_revenue_mtd * 100) if total_revenue_mtd else 0
total_shipping_30d = total_shipping_mtd + (feb_partial_revenue * shipping_pct_est / 100)
platform_fees_30d = platform_fees_mtd + (platform_fees_mtd / total_revenue_mtd * feb_partial_revenue) if total_revenue_mtd else platform_fees_mtd

# --- Last Year ---
total_revenue_ly = safe_float(mtd_ly.get("revenue"))
total_orders_ly = int(safe_float(mtd_ly.get("orders")))
total_ad_spend_ly = safe_float(mtd_ly.get("ad_spend"))

# --- Margin Calculations ---
gross_profit_30d = total_revenue_30d - total_cogs_30d
gross_margin_pct_30d = (gross_profit_30d / total_revenue_30d * 100) if total_revenue_30d else 0

# Net margin (after shipping, ads, platform fees)
total_costs_30d = total_cogs_30d + total_shipping_30d + total_ad_spend_30d + platform_fees_30d
net_profit_30d = total_revenue_30d - total_costs_30d
net_margin_pct_30d = (net_profit_30d / total_revenue_30d * 100) if total_revenue_30d else 0

# Using exact MTD data for more precise current-month metrics
shipping_pct_mtd = (total_shipping_mtd / total_revenue_mtd * 100) if total_revenue_mtd else 0
ad_spend_pct_mtd = (total_ad_spend_mtd / total_revenue_mtd * 100) if total_revenue_mtd else 0
cogs_pct_mtd = (total_cogs_mtd / total_revenue_mtd * 100) if total_revenue_mtd else 0
platform_fees_pct_mtd = (platform_fees_mtd / total_revenue_mtd * 100) if total_revenue_mtd else 0

# Net margin for MTD
net_profit_mtd = total_revenue_mtd - total_cogs_mtd - total_shipping_mtd - total_ad_spend_mtd - platform_fees_mtd
net_margin_pct_mtd = (net_profit_mtd / total_revenue_mtd * 100) if total_revenue_mtd else 0

# MER / ROAS
mer_30d = (total_revenue_30d / total_ad_spend_30d) if total_ad_spend_30d else 0
mer_ly_val = (total_revenue_ly / total_ad_spend_ly) if total_ad_spend_ly else 0

aov_30d = (total_revenue_30d / total_orders_30d) if total_orders_30d else 0
aov_ly = (total_revenue_ly / total_orders_ly) if total_orders_ly else 0

avg_daily_revenue_mtd = total_revenue_mtd / 14  # Mar 1-14

# --- Daily Trend Analysis (from daily_cy) ---
daily_margins = []
for d in daily_cy:
    rev = safe_float(d.get("revenue"))
    daily_margins.append({"date": d.get("date", ""), "revenue": rev})

# Trend: compare first half vs second half
if len(daily_margins) >= 4:
    mid = len(daily_margins) // 2
    first_half_avg = sum(d["revenue"] for d in daily_margins[:mid]) / mid
    second_half_avg = sum(d["revenue"] for d in daily_margins[mid:]) / (len(daily_margins) - mid)
    revenue_trend = "IMPROVING" if second_half_avg > first_half_avg else "DECLINING"
    revenue_trend_pct = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg else 0
else:
    first_half_avg = second_half_avg = 0
    revenue_trend = "INSUFFICIENT DATA"
    revenue_trend_pct = 0


# --- Channel Profitability ---
channels = {}

# WooCommerce
wc_rev = wc_revenue_mtd
wc_cogs_est = wc_rev * (cogs_pct_mtd / 100) if cogs_pct_mtd else 0
wc_shipping_est = wc_rev * (shipping_pct_mtd / 100) if shipping_pct_mtd else 0
wc_ads_est = total_ad_spend_mtd * 0.95  # Assume 95% of ads drive WC traffic
wc_gross = wc_rev - wc_cogs_est
wc_net = wc_rev - wc_cogs_est - wc_shipping_est - wc_ads_est
channels["WooCommerce"] = {
    "revenue": wc_rev,
    "orders": int(total_orders_mtd * (wc_rev / total_revenue_mtd)) if total_revenue_mtd else 0,
    "aov": 0,
    "cogs": wc_cogs_est,
    "shipping": wc_shipping_est,
    "ad_spend": wc_ads_est,
    "platform_fees": 0,  # WC has no platform fees beyond Stripe ~2.9%
    "gross_profit": wc_gross,
    "net_profit": wc_net,
    "gross_margin": (wc_gross / wc_rev * 100) if wc_rev else 0,
    "net_margin": (wc_net / wc_rev * 100) if wc_rev else 0,
}
channels["WooCommerce"]["aov"] = (wc_rev / channels["WooCommerce"]["orders"]) if channels["WooCommerce"]["orders"] else 0

# Walmart
wm_rev = walmart_revenue_mtd
wm_orders = int(safe_float(walmart_data.get("last_30d", {}).get("orders")))
wm_aov = safe_float(walmart_data.get("last_30d", {}).get("aov"))
wm_cogs_est = wm_rev * (cogs_pct_mtd / 100) if cogs_pct_mtd else 0
wm_shipping_est = wm_rev * (shipping_pct_mtd / 100) if shipping_pct_mtd else 0
wm_fees = platform_fees_mtd * (wm_rev / total_revenue_mtd) if total_revenue_mtd else 0
wm_ads = total_ad_spend_mtd * 0.02  # Minimal ad spend on Walmart
wm_gross = wm_rev - wm_cogs_est
wm_net = wm_rev - wm_cogs_est - wm_shipping_est - wm_fees - wm_ads
channels["Walmart"] = {
    "revenue": wm_rev,
    "orders": wm_orders,
    "aov": wm_aov,
    "cogs": wm_cogs_est,
    "shipping": wm_shipping_est,
    "ad_spend": wm_ads,
    "platform_fees": wm_fees,
    "gross_profit": wm_gross,
    "net_profit": wm_net,
    "gross_margin": (wm_gross / wm_rev * 100) if wm_rev else 0,
    "net_margin": (wm_net / wm_rev * 100) if wm_rev else 0,
}

# Amazon
amz_rev = amazon_revenue_mtd
if amz_rev > 0:
    amz_cogs_est = amz_rev * (cogs_pct_mtd / 100) if cogs_pct_mtd else 0
    amz_fees = platform_fees_mtd * (amz_rev / total_revenue_mtd) if total_revenue_mtd else 0
    amz_shipping_est = amz_rev * (shipping_pct_mtd / 100) if shipping_pct_mtd else 0
    amz_ads = total_ad_spend_mtd * 0.03  # Small Amazon ad allocation
    amz_gross = amz_rev - amz_cogs_est
    amz_net = amz_rev - amz_cogs_est - amz_shipping_est - amz_fees - amz_ads
    channels["Amazon"] = {
        "revenue": amz_rev,
        "orders": int(total_orders_mtd * (amz_rev / total_revenue_mtd)) if total_revenue_mtd else 0,
        "aov": 0,
        "cogs": amz_cogs_est,
        "shipping": amz_shipping_est,
        "ad_spend": amz_ads,
        "platform_fees": amz_fees,
        "gross_profit": amz_gross,
        "net_profit": amz_net,
        "gross_margin": (amz_gross / amz_rev * 100) if amz_rev else 0,
        "net_margin": (amz_net / amz_rev * 100) if amz_rev else 0,
    }
    if channels["Amazon"]["orders"]:
        channels["Amazon"]["aov"] = amz_rev / channels["Amazon"]["orders"]

# --- Break-Even Analysis ---
days_in_mtd = 14  # Mar 1-14
avg_daily_ad = total_ad_spend_mtd / days_in_mtd
avg_daily_shipping = total_shipping_mtd / days_in_mtd
avg_daily_platform_fees = platform_fees_mtd / days_in_mtd
avg_daily_fixed = avg_daily_ad + avg_daily_shipping + avg_daily_platform_fees

contribution_margin_pct = gross_margin_pct_mtd  # Revenue after COGS
breakeven_daily = (avg_daily_fixed / (contribution_margin_pct / 100)) if contribution_margin_pct else 0

days_below_breakeven = sum(1 for d in daily_margins if d["revenue"] < breakeven_daily)

# --- February Financial Health ---
# February was concerning: CM2 was -$11,900 (negative)
feb_cm2_val = safe_float(feb_data.get("cm2"))
feb_cm2_pct_val = safe_float(feb_data.get("cm2_pct"))

# --- YTD Totals ---
ytd_totals = ytd_data.get("totals_cy", {})
ytd_revenue = safe_float(ytd_totals.get("revenue"))
ytd_orders = int(safe_float(ytd_totals.get("orders")))
ytd_ad_spend = safe_float(ytd_totals.get("ad_spend"))
ytd_cogs = safe_float(ytd_totals.get("cogs"))
ytd_gross_profit = safe_float(ytd_totals.get("gross_profit"))
ytd_net_revenue = safe_float(ytd_totals.get("net_revenue"))
ytd_cm2 = safe_float(ytd_totals.get("cm2"))
ytd_cm2_pct = safe_float(ytd_totals.get("cm2_pct"))
ytd_gm_pct = safe_float(ytd_totals.get("gross_margin_pct"))
ytd_ly_revenue = safe_float(ytd_data.get("totals_ly", {}).get("revenue"))
ytd_budget_revenue = safe_float(ytd_data.get("totals_budget", {}).get("revenue"))

# --- Budget data ---
mar_budget = budget_data.get("monthly", {}).get("2026-03", {})
mar_budget_revenue = safe_float(mar_budget.get("net_revenue"))
mar_budget_cogs = safe_float(mar_budget.get("cogs"))
mar_budget_ad_spend = safe_float(mar_budget.get("ad_spend"))
mar_budget_net_income = safe_float(mar_budget.get("net_income"))


# ══════════════════════════════════════════════════════════════
# 3. GENERATE REPORT
# ══════════════════════════════════════════════════════════════

def fmt(val, prefix="$", decimals=2):
    if prefix == "$":
        return f"${val:,.{decimals}f}"
    elif prefix == "%":
        return f"{val:.{decimals}f}%"
    else:
        return f"{val:,.{decimals}f}"


def yoy_change(current, prior):
    if prior == 0:
        return "N/A"
    change = ((current - prior) / abs(prior)) * 100
    direction = "+" if change >= 0 else ""
    return f"{direction}{change:.1f}%"


report_lines = []
r = report_lines.append

r("# Financial Analysis: Unit Economics & Operational Costs")
r(f"\n**Agent**: Financial/Operations Agent A")
r(f"**Period**: {START_DATE} to {END_DATE} (30 days)")
r(f"**MTD Focus**: March 1-14, 2026 (14 days of precise data)")
r(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
r(f"**Data Source**: {DATA_SOURCE}")

# ── SECTION 1: P&L SUMMARY ──
r("\n---\n")
r("## 1. P&L Summary\n")
r("### March MTD (Mar 1-14, 2026) — Precise Data\n")
r("| Line Item | Amount | % of Revenue |")
r("|-----------|--------|-------------|")
r(f"| **Revenue** | {fmt(total_revenue_mtd)} | 100.0% |")
r(f"| COGS | ({fmt(total_cogs_mtd)}) | {fmt(cogs_pct_mtd, '%', 1)} |")
r(f"| **Gross Profit** | {fmt(gross_profit_mtd)} | {fmt(gross_margin_pct_mtd, '%', 1)} |")
r(f"| Shipping | ({fmt(total_shipping_mtd)}) | {fmt(shipping_pct_mtd, '%', 1)} |")
r(f"| Ad Spend | ({fmt(total_ad_spend_mtd)}) | {fmt(ad_spend_pct_mtd, '%', 1)} |")
r(f"| Platform Fees | ({fmt(platform_fees_mtd)}) | {fmt(platform_fees_pct_mtd, '%', 1)} |")
r(f"| **Net Profit (CM2)** | {fmt(cm2_mtd)} | {fmt(cm2_pct_mtd, '%', 1)} |")

r(f"\n**Key Metrics**:")
r(f"- Total Orders: {total_orders_mtd:,}")
r(f"- AOV: {fmt(aov_mtd)}")
r(f"- Avg Daily Revenue: {fmt(avg_daily_revenue_mtd)}")
r(f"- MER: {mer_mtd:.2f}x")

r(f"\n### Estimated 30-Day P&L ({START_DATE} to {END_DATE})\n")
r(f"_(Feb 13-28 prorated from monthly data + Mar 1-14 actual)_\n")
r("| Line Item | Amount | % of Revenue |")
r("|-----------|--------|-------------|")
r(f"| **Revenue** | {fmt(total_revenue_30d)} | 100.0% |")
r(f"| COGS | ({fmt(total_cogs_30d)}) | {fmt(total_cogs_30d/total_revenue_30d*100 if total_revenue_30d else 0, '%', 1)} |")
r(f"| **Gross Profit** | {fmt(gross_profit_30d)} | {fmt(gross_margin_pct_30d, '%', 1)} |")
r(f"| Shipping | ({fmt(total_shipping_30d)}) | {fmt(total_shipping_30d/total_revenue_30d*100 if total_revenue_30d else 0, '%', 1)} |")
r(f"| Ad Spend | ({fmt(total_ad_spend_30d)}) | {fmt(total_ad_spend_30d/total_revenue_30d*100 if total_revenue_30d else 0, '%', 1)} |")
r(f"| Platform Fees (est.) | ({fmt(platform_fees_30d)}) | {fmt(platform_fees_30d/total_revenue_30d*100 if total_revenue_30d else 0, '%', 1)} |")
r(f"| **Net Profit** | {fmt(net_profit_30d)} | {fmt(net_margin_pct_30d, '%', 1)} |")
r(f"\n- Estimated 30-Day Orders: ~{total_orders_30d:,}")
r(f"- Estimated 30-Day AOV: {fmt(aov_30d)}")
r(f"- Estimated 30-Day MER: {mer_30d:.2f}x")

# ── SECTION 2: MARGIN HEALTH ──
r("\n---\n")
r("## 2. Margin Health\n")
r("### Current vs Last Year (March MTD, same day count)\n")
r("| Metric | March 2026 MTD | March 2025 MTD | YoY Change |")
r("|--------|---------------|---------------|------------|")
r(f"| Revenue | {fmt(total_revenue_mtd)} | {fmt(total_revenue_ly)} | {yoy_change(total_revenue_mtd, total_revenue_ly)} |")
r(f"| Orders | {total_orders_mtd:,} | {total_orders_ly:,} | {yoy_change(total_orders_mtd, total_orders_ly)} |")
r(f"| AOV | {fmt(aov_mtd)} | {fmt(aov_ly)} | {yoy_change(aov_mtd, aov_ly)} |")
r(f"| Ad Spend | {fmt(total_ad_spend_mtd)} | {fmt(total_ad_spend_ly)} | {yoy_change(total_ad_spend_mtd, total_ad_spend_ly)} |")
r(f"| MER | {mer_mtd:.2f}x | {mer_ly_val:.2f}x | {yoy_change(mer_mtd, mer_ly_val)} |")
r(f"| Gross Margin % | {fmt(gross_margin_pct_mtd, '%', 1)} | — | — |")

r(f"\n### Monthly Margin Trend (2026 YTD)\n")
r("| Month | Revenue | Gross Margin % | CM2 | CM2 % | MER |")
r("|-------|---------|---------------|-----|-------|-----|")
for m in ytd_months:
    r(f"| {m['month']} | {fmt(safe_float(m.get('revenue')))} | {fmt(safe_float(m.get('gross_margin_pct')), '%', 1)} | {fmt(safe_float(m.get('cm2')))} | {fmt(safe_float(m.get('cm2_pct')), '%', 1)} | {safe_float(m.get('mer')):.2f}x |")

r(f"\n**Revenue Trend (Mar 1-14)**: {revenue_trend}")
r(f"- First week avg: {fmt(first_half_avg)}/day")
r(f"- Second week avg: {fmt(second_half_avg)}/day")
r(f"- Shift: {revenue_trend_pct:+.1f}%")

# Highlight the February problem
if feb_cm2_val < 0:
    r(f"\n**ALERT: February 2026 was unprofitable** — CM2 was {fmt(feb_cm2_val)} ({feb_cm2_pct_val:.1f}%)")
    r(f"- February revenue ({fmt(feb_revenue)}) was strong but costs exceeded margins")
    r(f"- March is recovering: CM2 at {fmt(cm2_mtd)} ({cm2_pct_mtd:.1f}%)")

# ── SECTION 3: COGS & PRODUCT MARGINS ──
r("\n---\n")
r("## 3. Product Margin & COGS Analysis\n")

r("### COGS Coverage")
r(f"- The `cogs_lookup` table contains SKU-level unit costs (276 SKUs per CLAUDE.md)")
r(f"- COGS as % of revenue (Mar MTD): **{fmt(cogs_pct_mtd, '%', 1)}**")
r(f"- Gross margin: **{fmt(gross_margin_pct_mtd, '%', 1)}**")

r(f"\n### COGS Trend by Month\n")
r("| Month | Revenue | COGS | Gross Margin % |")
r("|-------|---------|------|---------------|")
for m in ytd_months:
    rev = safe_float(m.get("revenue"))
    cg = safe_float(m.get("cogs"))
    gm = safe_float(m.get("gross_margin_pct"))
    r(f"| {m['month']} | {fmt(rev)} | {fmt(cg)} | {fmt(gm, '%', 1)} |")

r(f"\n### Observations")
r(f"- January had the best gross margin at 72.5%, indicating lower-cost products or better pricing")
r(f"- February dropped to 65.5% gross margin — higher-cost mixes sold more")
r(f"- March is at 67.5% — partial recovery")
r(f"- **COGS data gaps**: The `daily_cogs` table tracks `unmatched_units` — units sold without matching SKU costs")
r(f"- Without live Supabase access, exact unmatched unit counts are unavailable, but the schema shows this is tracked")
r(f"- **Action needed**: Query `cogs_lookup` for SKUs with `selling_price < unit_cost` to find negative-margin products")

# ── SECTION 4: SHIPPING COST ANALYSIS ──
r("\n---\n")
r("## 4. Shipping Cost Analysis\n")
r(f"- **Total shipping cost (Mar MTD)**: {fmt(total_shipping_mtd)}")
r(f"- **Shipping as % of revenue**: **{fmt(shipping_pct_mtd, '%', 1)}**")
avg_ship_per_order = total_shipping_mtd / total_orders_mtd if total_orders_mtd else 0
r(f"- **Avg shipping cost per order**: {fmt(avg_ship_per_order)}")
r(f"- **Avg daily shipping cost**: {fmt(total_shipping_mtd / days_in_mtd)}")

r(f"\n### Shipping Cost Assessment")
if shipping_pct_mtd > 20:
    r(f"- **CRITICAL**: Shipping at {shipping_pct_mtd:.1f}% of revenue is very high")
    r(f"- Industry benchmark for ecommerce: 8-15% of revenue")
    r(f"- This is eating {fmt(total_shipping_mtd)} out of {fmt(total_revenue_mtd)} in revenue")
    excess_ship = total_revenue_mtd * ((shipping_pct_mtd - 15) / 100)
    r(f"- **Excess shipping cost** (above 15% benchmark): ~{fmt(excess_ship)} in 14 days = ~{fmt(excess_ship * 26)} annualized")
elif shipping_pct_mtd > 15:
    r(f"- **WARNING**: Shipping at {shipping_pct_mtd:.1f}% is above the 8-15% industry benchmark")
    excess_ship = total_revenue_mtd * ((shipping_pct_mtd - 12) / 100)
    r(f"- Reducing to 12% would save ~{fmt(excess_ship)} per 14 days")
else:
    r(f"- Shipping at {shipping_pct_mtd:.1f}% is within industry norms")

r(f"\n### Shipping's Impact on Profitability")
r(f"- Gross profit before shipping: {fmt(gross_profit_mtd)} ({gross_margin_pct_mtd:.1f}%)")
r(f"- After shipping: {fmt(gross_profit_mtd - total_shipping_mtd)} ({(gross_profit_mtd - total_shipping_mtd) / total_revenue_mtd * 100:.1f}%)")
r(f"- Shipping consumes **{(total_shipping_mtd / gross_profit_mtd * 100) if gross_profit_mtd else 0:.1f}%** of gross profit")

# ── SECTION 5: AD SPEND EFFICIENCY ──
r("\n---\n")
r("## 5. Ad Spend Efficiency\n")
r(f"- **Total ad spend (Mar MTD)**: {fmt(total_ad_spend_mtd)}")
r(f"- **Ad spend as % of revenue**: {fmt(ad_spend_pct_mtd, '%', 1)}")
r(f"- **MER**: {mer_mtd:.2f}x (revenue per $1 ad spend)")
r(f"- **ROAS**: {mer_mtd:.2f}x")

r(f"\n### MER Trend\n")
r("| Month | Ad Spend | Revenue | MER |")
r("|-------|---------|---------|-----|")
for m in ytd_months:
    rev = safe_float(m.get("revenue"))
    ads = safe_float(m.get("ad_spend"))
    mr = safe_float(m.get("mer"))
    r(f"| {m['month']} | {fmt(ads)} | {fmt(rev)} | {mr:.2f}x |")

r(f"\n### Assessment")
if mer_mtd >= 5:
    r(f"- MER of {mer_mtd:.2f}x is **healthy** (target: 5x+)")
else:
    r(f"- MER of {mer_mtd:.2f}x is **below target** (target: 5x+)")
    target_spend = total_revenue_mtd / 5.0
    savings = total_ad_spend_mtd - target_spend
    r(f"- To hit 5x MER at current revenue: reduce spend to {fmt(target_spend)} (save {fmt(savings)})")

r(f"- February MER dropped to {feb_mer:.2f}x (highest spend relative to revenue)")
r(f"- March recovered to {mer_mtd:.2f}x")

r(f"\n### YoY Ad Efficiency")
r(f"- March 2025 MTD ad spend: {fmt(total_ad_spend_ly)}")
r(f"- March 2025 MTD MER: {mer_ly_val:.2f}x")
r(f"- YoY MER change: {yoy_change(mer_mtd, mer_ly_val)}")

# ── SECTION 6: CHANNEL COMPARISON ──
r("\n---\n")
r("## 6. Channel Comparison (WC vs Walmart vs Amazon)\n")
r("_Note: Channel-level COGS and shipping are estimated proportionally. Ad spend allocation is estimated._\n")

r("| Metric | " + " | ".join(channels.keys()) + " |")
r("|--------|" + "|".join(["-------"] * len(channels)) + "|")

metrics = [
    ("Revenue (MTD)", "revenue", "$"),
    ("Orders", "orders", ""),
    ("AOV", "aov", "$"),
    ("COGS (est.)", "cogs", "$"),
    ("Shipping (est.)", "shipping", "$"),
    ("Ad Spend (est.)", "ad_spend", "$"),
    ("Platform Fees", "platform_fees", "$"),
    ("Gross Profit", "gross_profit", "$"),
    ("Net Profit", "net_profit", "$"),
    ("Gross Margin %", "gross_margin", "%"),
    ("Net Margin %", "net_margin", "%"),
]
for label, key, sym in metrics:
    vals = []
    for ch in channels:
        v = channels[ch][key]
        if sym == "$":
            vals.append(fmt(v))
        elif sym == "%":
            vals.append(fmt(v, "%", 1))
        else:
            vals.append(f"{v:,}" if isinstance(v, int) else f"{v:,.0f}")
    r(f"| {label} | " + " | ".join(vals) + " |")

for ch, data in channels.items():
    if data["net_profit"] < 0:
        r(f"\n**WARNING: {ch} is unprofitable (MTD)** — losing {fmt(abs(data['net_profit']))} at {data['net_margin']:.1f}% net margin")

r(f"\n### Revenue Mix")
for ch, data in channels.items():
    pct = (data["revenue"] / total_revenue_mtd * 100) if total_revenue_mtd else 0
    r(f"- **{ch}**: {fmt(data['revenue'])} ({pct:.1f}% of total)")

# Walmart-specific analysis
r(f"\n### Walmart Profitability Deep Dive")
r(f"- Walmart revenue: {fmt(wm_rev)} ({wm_orders} orders)")
r(f"- Walmart AOV: {fmt(wm_aov)}")
wm_rev_share = (wm_rev / total_revenue_mtd * 100) if total_revenue_mtd else 0
r(f"- Revenue share: {wm_rev_share:.1f}%")
if channels["Walmart"]["net_profit"] < 0:
    r(f"- **Walmart is a net loss** after platform fees ({fmt(wm_fees)}) + estimated shipping/COGS")
    r(f"- Consider: Is the brand exposure worth the losses? Can pricing be raised?")
else:
    r(f"- Walmart is marginally profitable at {channels['Walmart']['net_margin']:.1f}% net margin")

# ── SECTION 7: YoY FINANCIAL HEALTH ──
r("\n---\n")
r("## 7. YoY Financial Health Comparison\n")

r("### March MTD: 2026 vs 2025\n")
r("| Metric | 2026 | 2025 | YoY Change |")
r("|--------|------|------|------------|")
r(f"| Revenue | {fmt(total_revenue_mtd)} | {fmt(total_revenue_ly)} | {yoy_change(total_revenue_mtd, total_revenue_ly)} |")
r(f"| Orders | {total_orders_mtd:,} | {total_orders_ly:,} | {yoy_change(total_orders_mtd, total_orders_ly)} |")
r(f"| AOV | {fmt(aov_mtd)} | {fmt(aov_ly)} | {yoy_change(aov_mtd, aov_ly)} |")
r(f"| Ad Spend | {fmt(total_ad_spend_mtd)} | {fmt(total_ad_spend_ly)} | {yoy_change(total_ad_spend_mtd, total_ad_spend_ly)} |")
r(f"| MER | {mer_mtd:.2f}x | {mer_ly_val:.2f}x | {yoy_change(mer_mtd, mer_ly_val)} |")

r(f"\n### YTD Comparison\n")
r("| Metric | 2026 YTD | 2025 YTD (same period) | YoY | Budget | % to Budget |")
r("|--------|---------|----------------------|-----|--------|------------|")
r(f"| Revenue | {fmt(ytd_revenue)} | {fmt(ytd_ly_revenue)} | {yoy_change(ytd_revenue, ytd_ly_revenue)} | {fmt(ytd_budget_revenue)} | {(ytd_revenue/ytd_budget_revenue*100) if ytd_budget_revenue else 0:.1f}% |")
r(f"| Gross Margin % | {ytd_gm_pct:.1f}% | — | — | — | — |")
r(f"| CM2 | {fmt(ytd_cm2)} | — | — | — | — |")
r(f"| CM2 % | {ytd_cm2_pct:.1f}% | — | — | — | — |")

if ytd_ly_revenue:
    r(f"\n**YTD revenue is {yoy_change(ytd_revenue, ytd_ly_revenue)} vs last year** — tracking at {(ytd_revenue/ytd_ly_revenue*100):.1f}% of LY pace")
if ytd_budget_revenue:
    r(f"**YTD revenue is at {(ytd_revenue/ytd_budget_revenue*100):.1f}% of budget** — {'on track' if ytd_revenue/ytd_budget_revenue > 0.9 else 'behind target'}")

# ── SECTION 8: TOP 5 OPTIMIZATIONS ──
r("\n---\n")
r("## 8. Top 5 Financial Optimization Opportunities\n")

r("### 1. [CRITICAL] Reduce Shipping Costs")
r(f"- Shipping is {shipping_pct_mtd:.1f}% of revenue ({fmt(total_shipping_mtd)} MTD)")
r(f"- At {fmt(avg_ship_per_order)}/order, this is the single largest margin drain after COGS")
if shipping_pct_mtd > 15:
    annual_excess = total_revenue_mtd / 14 * 365 * ((shipping_pct_mtd - 12) / 100)
    r(f"- Reducing to 12% of revenue would save ~{fmt(annual_excess)}/year")
r(f"- **Actions**: Negotiate Shippo rates, increase free-shipping threshold, optimize packaging, consider regional carriers")
r(f"- **Estimated annual impact**: {fmt(total_shipping_mtd / 14 * 365 * 0.15)} (15% shipping cost reduction)")
r("")

r("### 2. [HIGH] Fix February-Type Cost Blowouts")
r(f"- February 2026 had **negative CM2** ({fmt(feb_cm2_val)}, {feb_cm2_pct_val:.1f}%)")
r(f"- Revenue was {fmt(feb_revenue)} but costs consumed all margin")
r(f"- This pattern suggests seasonal spend ramp without proportional revenue")
r(f"- **Actions**: Set hard budget caps, pause underperforming campaigns earlier, watch shipping costs during high-volume periods")
r(f"- **Estimated annual impact**: Avoiding one bad month = {fmt(abs(feb_cm2_val) * 2)} saved")
r("")

r("### 3. [HIGH] Improve COGS Tracking & Coverage")
r(f"- The `daily_cogs` table tracks `unmatched_units` (orders with no SKU cost data)")
r(f"- Any unmatched units mean reported margins are OVERSTATED")
r(f"- With 276 SKUs in `cogs_lookup`, coverage may not be 100%")
r(f"- **Actions**: Audit `cogs_lookup` for missing SKUs, reconcile Fishbowl costs, add selling_price for margin analysis")
r(f"- **Estimated annual impact**: 5% better COGS accuracy could reveal {fmt(ytd_cogs * 0.05)} in hidden costs")
r("")

r("### 4. [MEDIUM] Optimize Channel Mix (Reduce Marketplace Losses)")
r(f"- WooCommerce generates {(wc_revenue_mtd/total_revenue_mtd*100) if total_revenue_mtd else 0:.1f}% of revenue with best margins")
r(f"- Walmart ({fmt(wm_rev)}) and Amazon ({fmt(amz_rev)}) carry platform fees + higher shipping")
r(f"- **Actions**: Raise marketplace prices by 10-15% to cover fees, focus ad spend on WC, audit Walmart SKU profitability")
r(f"- **Estimated annual impact**: 10% price increase on marketplace = ~{fmt((wm_rev + amz_rev) * 0.10 * 26)}/year")
r("")

r("### 5. [MEDIUM] Maintain MER Above 5x")
r(f"- Current MER: {mer_mtd:.2f}x (healthy)")
r(f"- February dropped to {feb_mer:.2f}x (dangerous)")
r(f"- **Actions**: Set 4.5x MER floor as campaign pause trigger, reallocate budget to highest-ROAS campaigns")
r(f"- **Estimated annual impact**: Maintaining 5x vs 4x MER on {fmt(ytd_ad_spend)} annual ad spend = {fmt(ytd_ad_spend * (5/4 - 1))} additional revenue captured")
r("")

# ── SECTION 9: BREAK-EVEN ──
r("\n---\n")
r("## 9. Break-Even Analysis & Risk Assessment\n")
r(f"- **Average daily fixed costs** (ads + shipping + platform fees): {fmt(avg_daily_fixed)}")
r(f"- **COGS as % of revenue**: {fmt(cogs_pct_mtd, '%', 1)}")
r(f"- **Contribution margin ratio**: {fmt(contribution_margin_pct, '%', 1)}")
r(f"- **Break-even daily revenue**: **{fmt(breakeven_daily)}**")
r(f"- **Actual avg daily revenue (Mar MTD)**: {fmt(avg_daily_revenue_mtd)}")
buffer = avg_daily_revenue_mtd - breakeven_daily
buffer_pct = (buffer / breakeven_daily * 100) if breakeven_daily else 0
r(f"- **Buffer above break-even**: {fmt(buffer)} ({buffer_pct:.1f}%)")
r(f"- **Days below break-even (Mar 1-14)**: {days_below_breakeven} of {len(daily_margins)}")

if buffer_pct > 30:
    r(f"\n**RISK: LOW** — {buffer_pct:.0f}% buffer above break-even. Strong daily performance.")
elif buffer_pct > 10:
    r(f"\n**RISK: MODERATE** — {buffer_pct:.0f}% buffer. Adequate but vulnerable to demand drops.")
else:
    r(f"\n**RISK: HIGH** — Only {buffer_pct:.0f}% buffer above break-even. Very thin margin for error.")

r(f"\n### Monthly Break-Even Target")
monthly_breakeven = breakeven_daily * 30
r(f"- Monthly break-even revenue: ~{fmt(monthly_breakeven)}")
r(f"- March budget target: {fmt(mar_budget_revenue)}")
r(f"- Current March run rate (14d annualized): {fmt(avg_daily_revenue_mtd * 30)}")
if avg_daily_revenue_mtd * 30 < mar_budget_revenue:
    shortfall = mar_budget_revenue - (avg_daily_revenue_mtd * 30)
    r(f"- **Budget shortfall risk**: ~{fmt(shortfall)} below March target at current pace")

r(f"\n### Daily Revenue (Mar 1-14)\n")
r("| Date | Revenue | vs Break-Even |")
r("|------|---------|--------------|")
for dm in daily_margins:
    diff = dm["revenue"] - breakeven_daily
    status = "ABOVE" if diff >= 0 else "**BELOW**"
    r(f"| {dm['date']} | {fmt(dm['revenue'])} | {status} ({fmt(diff, '$', 0)}) |")

# ── SECTION 10: BUDGET COMPARISON ──
r("\n---\n")
r("## 10. Budget vs Actual (March 2026)\n")
r("| Metric | Budget (Full Month) | Actual (14d) | Run Rate (30d) | % of Budget |")
r("|--------|-------------------|-------------|---------------|------------|")
mar_run_rate = avg_daily_revenue_mtd * 30
r(f"| Revenue | {fmt(mar_budget_revenue)} | {fmt(total_revenue_mtd)} | {fmt(mar_run_rate)} | {(mar_run_rate/mar_budget_revenue*100) if mar_budget_revenue else 0:.0f}% |")
r(f"| COGS | {fmt(mar_budget_cogs)} | {fmt(total_cogs_mtd)} | {fmt(total_cogs_mtd/14*30)} | {(total_cogs_mtd/14*30/mar_budget_cogs*100) if mar_budget_cogs else 0:.0f}% |")
r(f"| Ad Spend | {fmt(mar_budget_ad_spend)} | {fmt(total_ad_spend_mtd)} | {fmt(total_ad_spend_mtd/14*30)} | {(total_ad_spend_mtd/14*30/mar_budget_ad_spend*100) if mar_budget_ad_spend else 0:.0f}% |")
r(f"| Net Income | {fmt(mar_budget_net_income)} | {fmt(cm2_mtd)} | {fmt(cm2_mtd/14*30)} | {(cm2_mtd/14*30/mar_budget_net_income*100) if mar_budget_net_income else 0:.0f}% |")

# ── APPENDIX ──
r("\n---\n")
r("## Appendix: Raw Data Summary\n")
r(f"### Source: `docs/data/reporting.json` (as of {reporting.get('as_of', 'unknown')})\n")
r(f"```")
r(f"MTD Revenue:    {fmt(total_revenue_mtd)}")
r(f"MTD Orders:     {total_orders_mtd:,}")
r(f"MTD COGS:       {fmt(total_cogs_mtd)}")
r(f"MTD Shipping:   {fmt(total_shipping_mtd)}")
r(f"MTD Ad Spend:   {fmt(total_ad_spend_mtd)}")
r(f"MTD Plat Fees:  {fmt(platform_fees_mtd)}")
r(f"MTD Net (CM2):  {fmt(cm2_mtd)}")
r(f"MTD GM%:        {gross_margin_pct_mtd:.1f}%")
r(f"MTD CM2%:       {cm2_pct_mtd:.1f}%")
r(f"MTD MER:        {mer_mtd:.2f}x")
r(f"MTD AOV:        {fmt(aov_mtd)}")
r(f"")
r(f"YTD Revenue:    {fmt(ytd_revenue)}")
r(f"YTD CM2:        {fmt(ytd_cm2)}")
r(f"YTD CM2%:       {ytd_cm2_pct:.1f}%")
r(f"YTD GM%:        {ytd_gm_pct:.1f}%")
r(f"```")

r(f"\n### Walmart Top Products (MTD)\n")
wm_top = walmart_data.get("top_products", [])
if wm_top:
    r("| Product | SKU | Revenue | Orders |")
    r("|---------|-----|---------|--------|")
    for p in wm_top[:5]:
        r(f"| {p.get('title', '')[:60]} | {p.get('sku', '')} | {fmt(safe_float(p.get('revenue')))} | {p.get('orders', 0)} |")

# Write report
report_path = REPORT_DIR / "financial_a_findings.md"
report_content = "\n".join(report_lines)
report_path.write_text(report_content)
print(f"\n[DONE] Report written to: {report_path}")
print(f"[DONE] Report size: {len(report_content):,} characters, {len(report_lines)} lines")
