#!/usr/bin/env python3
"""
Financial/Operations Agent A — Unit Economics & Operational Cost Analysis
Analyzes Nature's Seed margins, shipping costs, COGS, and channel profitability.

Reads from Supabase via REST API (same .env pattern as daily_pull.py).
Outputs findings to funnel-analysis/reports/financial_a_findings.md
"""

import json
import os
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict

import requests

# ══════════════════════════════════════════════════════════════
# ENV + SUPABASE SETUP (mirrors daily_pull.py)
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

# Also check os.environ as fallback (e.g. GitHub Actions)
SUPABASE_URL = env_vars.get("SUPABASE_URL", "") or os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "") or os.environ.get("SUPABASE_SECRET_API_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] SUPABASE_URL or SUPABASE_SECRET_API_KEY not found in .env or environment")
    print("[INFO]  Create a .env file at the repo root with these keys, or export them as env vars")
    sys.exit(1)

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════
# SUPABASE QUERY HELPER
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


def safe_float(val, default=0.0):
    """Safely convert a value to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ══════════════════════════════════════════════════════════════
# DATE RANGES
# ══════════════════════════════════════════════════════════════

# Last 30 days
END_DATE = "2026-03-14"
START_DATE = "2026-02-13"

# Same period last year
END_DATE_LY = "2025-03-14"
START_DATE_LY = "2025-02-13"

print(f"[INFO] Analysis period: {START_DATE} to {END_DATE}")
print(f"[INFO] Last year period: {START_DATE_LY} to {END_DATE_LY}")


# ══════════════════════════════════════════════════════════════
# 1. PULL DATA FROM SUPABASE
# ══════════════════════════════════════════════════════════════

def pull_date_range(table, start, end, extra_params=None):
    """Pull data for a date range from a Supabase table."""
    params = {
        "select": "*",
        "report_date": f"gte.{start}",
    }
    # PostgREST needs separate key for second filter on same column
    # Use 'and' filter syntax
    params = {
        "select": "*",
    }
    if extra_params:
        params.update(extra_params)
    # Use PostgREST filtering
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=*&report_date=gte.{start}&report_date=lte.{end}"
    headers = {"apikey": SUPABASE_KEY}
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"[WARN] Pull {table} ({start} to {end}): {resp.status_code} {resp.text[:300]}")
        return []
    data = resp.json()
    print(f"[OK] {table}: {len(data)} rows ({start} to {end})")
    return data


print("\n=== Pulling current period data ===")
sales = pull_date_range("daily_sales", START_DATE, END_DATE)
ad_spend = pull_date_range("daily_ad_spend", START_DATE, END_DATE)
shipping = pull_date_range("daily_shipping", START_DATE, END_DATE)
cogs = pull_date_range("daily_cogs", START_DATE, END_DATE)
summary = pull_date_range("daily_summary", START_DATE, END_DATE)

print("\n=== Pulling last year data ===")
sales_ly = pull_date_range("daily_sales", START_DATE_LY, END_DATE_LY)
ad_spend_ly = pull_date_range("daily_ad_spend", START_DATE_LY, END_DATE_LY)
shipping_ly = pull_date_range("daily_shipping", START_DATE_LY, END_DATE_LY)
cogs_ly = pull_date_range("daily_cogs", START_DATE_LY, END_DATE_LY)

print("\n=== Pulling MTD comparison ===")
mtd = supabase_query("mtd_comparison", {"select": "*"})
print(f"[OK] mtd_comparison: {len(mtd)} rows")

print("\n=== Pulling COGS lookup ===")
cogs_lookup = supabase_query("cogs_lookup", {"select": "*"})
print(f"[OK] cogs_lookup: {len(cogs_lookup)} rows")


# ══════════════════════════════════════════════════════════════
# 2. AGGREGATE & CALCULATE
# ══════════════════════════════════════════════════════════════

def aggregate_by_channel(rows, revenue_key="revenue", orders_key="orders"):
    """Aggregate revenue and orders by channel."""
    channels = defaultdict(lambda: {"revenue": 0.0, "orders": 0, "days": 0})
    for row in rows:
        ch = row.get("channel", "unknown")
        channels[ch]["revenue"] += safe_float(row.get(revenue_key))
        channels[ch]["orders"] += int(safe_float(row.get(orders_key)))
        channels[ch]["days"] += 1
    return dict(channels)


def sum_field(rows, field):
    """Sum a single field across all rows."""
    return sum(safe_float(row.get(field)) for row in rows)


# --- Current Period Aggregations ---
total_revenue = sum_field(sales, "revenue")
total_orders = int(sum_field(sales, "orders"))
channel_sales = aggregate_by_channel(sales)

total_ad_spend_val = sum_field(ad_spend, "spend")
total_shipping_cost = sum_field(shipping, "total_cost")
total_cogs_val = sum_field(cogs, "total_cogs")

# Channel-level COGS
cogs_by_channel = defaultdict(float)
for row in cogs:
    cogs_by_channel[row.get("channel", "unknown")] += safe_float(row.get("total_cogs"))

# Channel-level ad spend
ad_by_channel = defaultdict(float)
for row in ad_spend:
    ad_by_channel[row.get("channel", "unknown")] += safe_float(row.get("spend"))

# --- Last Year Aggregations ---
total_revenue_ly = sum_field(sales_ly, "revenue")
total_orders_ly = int(sum_field(sales_ly, "orders"))
total_ad_spend_ly = sum_field(ad_spend_ly, "spend")
total_shipping_ly = sum_field(shipping_ly, "total_cost")
total_cogs_ly = sum_field(cogs_ly, "total_cogs")

# --- Margin Calculations ---
gross_profit = total_revenue - total_cogs_val
gross_margin_pct = (gross_profit / total_revenue * 100) if total_revenue else 0

net_profit = total_revenue - total_cogs_val - total_shipping_cost - total_ad_spend_val
net_margin_pct = (net_profit / total_revenue * 100) if total_revenue else 0

# MER and ROAS
mer = (total_revenue / total_ad_spend_val) if total_ad_spend_val else 0
roas = mer  # Same calculation, different framing

shipping_pct = (total_shipping_cost / total_revenue * 100) if total_revenue else 0
aov = (total_revenue / total_orders) if total_orders else 0

# Last year margins
gross_profit_ly = total_revenue_ly - total_cogs_ly
gross_margin_ly = (gross_profit_ly / total_revenue_ly * 100) if total_revenue_ly else 0
net_profit_ly = total_revenue_ly - total_cogs_ly - total_shipping_ly - total_ad_spend_ly
net_margin_ly = (net_profit_ly / total_revenue_ly * 100) if total_revenue_ly else 0
mer_ly = (total_revenue_ly / total_ad_spend_ly) if total_ad_spend_ly else 0
shipping_pct_ly = (total_shipping_ly / total_revenue_ly * 100) if total_revenue_ly else 0
aov_ly = (total_revenue_ly / total_orders_ly) if total_orders_ly else 0


# --- Daily Trend Analysis ---
daily_data = defaultdict(lambda: {"revenue": 0.0, "orders": 0, "cogs": 0.0, "shipping": 0.0, "ad_spend": 0.0})

for row in sales:
    d = row.get("report_date", "")
    daily_data[d]["revenue"] += safe_float(row.get("revenue"))
    daily_data[d]["orders"] += int(safe_float(row.get("orders")))

for row in cogs:
    d = row.get("report_date", "")
    daily_data[d]["cogs"] += safe_float(row.get("total_cogs"))

for row in shipping:
    d = row.get("report_date", "")
    daily_data[d]["shipping"] += safe_float(row.get("total_cost"))

for row in ad_spend:
    d = row.get("report_date", "")
    daily_data[d]["ad_spend"] += safe_float(row.get("spend"))

# Sort by date
sorted_dates = sorted(daily_data.keys())

# Calculate daily margins
daily_margins = []
for d in sorted_dates:
    dd = daily_data[d]
    rev = dd["revenue"]
    gm = ((rev - dd["cogs"]) / rev * 100) if rev else 0
    nm = ((rev - dd["cogs"] - dd["shipping"] - dd["ad_spend"]) / rev * 100) if rev else 0
    daily_margins.append({
        "date": d,
        "revenue": rev,
        "orders": dd["orders"],
        "gross_margin": gm,
        "net_margin": nm,
    })

# Trend: compare first half vs second half
if len(daily_margins) >= 2:
    mid = len(daily_margins) // 2
    first_half_gm = sum(d["gross_margin"] for d in daily_margins[:mid]) / mid if mid else 0
    second_half_gm = sum(d["gross_margin"] for d in daily_margins[mid:]) / (len(daily_margins) - mid) if (len(daily_margins) - mid) else 0
    first_half_nm = sum(d["net_margin"] for d in daily_margins[:mid]) / mid if mid else 0
    second_half_nm = sum(d["net_margin"] for d in daily_margins[mid:]) / (len(daily_margins) - mid) if (len(daily_margins) - mid) else 0
    gm_trend = "IMPROVING" if second_half_gm > first_half_gm else "DECLINING" if second_half_gm < first_half_gm else "FLAT"
    nm_trend = "IMPROVING" if second_half_nm > first_half_nm else "DECLINING" if second_half_nm < first_half_nm else "FLAT"
else:
    first_half_gm = second_half_gm = first_half_nm = second_half_nm = 0
    gm_trend = nm_trend = "INSUFFICIENT DATA"


# --- Channel Profitability ---
channel_profit = {}
for ch, data in channel_sales.items():
    ch_rev = data["revenue"]
    ch_cogs = cogs_by_channel.get(ch, 0)
    ch_ads = ad_by_channel.get(ch, 0)
    # Allocate shipping proportionally by revenue
    ch_shipping = (ch_rev / total_revenue * total_shipping_cost) if total_revenue else 0
    ch_gross = ch_rev - ch_cogs
    ch_net = ch_rev - ch_cogs - ch_shipping - ch_ads
    ch_gm = (ch_gross / ch_rev * 100) if ch_rev else 0
    ch_nm = (ch_net / ch_rev * 100) if ch_rev else 0
    channel_profit[ch] = {
        "revenue": ch_rev,
        "orders": data["orders"],
        "cogs": ch_cogs,
        "shipping": ch_shipping,
        "ad_spend": ch_ads,
        "gross_profit": ch_gross,
        "net_profit": ch_net,
        "gross_margin": ch_gm,
        "net_margin": ch_nm,
        "aov": (ch_rev / data["orders"]) if data["orders"] else 0,
    }


# --- Break-Even Analysis ---
# Fixed daily costs: ad spend average
avg_daily_ad = total_ad_spend_val / 30 if total_ad_spend_val else 0
avg_daily_shipping = total_shipping_cost / 30 if total_shipping_cost else 0
avg_daily_fixed = avg_daily_ad + avg_daily_shipping

# Variable cost ratio (COGS as % of revenue)
cogs_pct = (total_cogs_val / total_revenue * 100) if total_revenue else 0
contribution_margin_pct = 100 - cogs_pct  # Revenue after COGS

# Break-even daily revenue = fixed costs / contribution margin ratio
breakeven_daily = (avg_daily_fixed / (contribution_margin_pct / 100)) if contribution_margin_pct else 0
avg_daily_revenue = total_revenue / 30 if total_revenue else 0

# Days below break-even
days_below_breakeven = sum(1 for d in daily_margins if d["revenue"] < breakeven_daily)


# --- COGS Lookup Analysis ---
margin_tiers = {"negative": [], "0-20%": [], "20-40%": [], "40-60%": [], "60%+": [], "no_price": []}
for item in cogs_lookup:
    sku = item.get("sku", "?")
    unit_cost = safe_float(item.get("unit_cost"))
    selling_price = safe_float(item.get("selling_price"))
    product_name = item.get("product_name", item.get("name", sku))

    if selling_price <= 0:
        margin_tiers["no_price"].append({"sku": sku, "name": product_name, "cost": unit_cost, "price": selling_price})
        continue

    margin = ((selling_price - unit_cost) / selling_price) * 100
    entry = {"sku": sku, "name": product_name, "cost": unit_cost, "price": selling_price, "margin": margin}

    if margin < 0:
        margin_tiers["negative"].append(entry)
    elif margin < 20:
        margin_tiers["0-20%"].append(entry)
    elif margin < 40:
        margin_tiers["20-40%"].append(entry)
    elif margin < 60:
        margin_tiers["40-60%"].append(entry)
    else:
        margin_tiers["60%+"].append(entry)

# Sort negative margin items by margin (worst first)
margin_tiers["negative"].sort(key=lambda x: x["margin"])
margin_tiers["0-20%"].sort(key=lambda x: x["margin"])


# --- COGS Coverage Check ---
# Check how many SKUs have COGS data
cogs_skus = {item.get("sku", "") for item in cogs_lookup if item.get("sku")}
# Check for unmatched COGS in daily data
unmatched_units_total = sum(safe_float(row.get("unmatched_units", 0)) for row in cogs)
total_units = sum(safe_float(row.get("total_units", 0)) for row in cogs)
cogs_coverage = ((total_units - unmatched_units_total) / total_units * 100) if total_units else 0


# ══════════════════════════════════════════════════════════════
# 3. FORMAT MTD COMPARISON
# ══════════════════════════════════════════════════════════════

mtd_text = ""
if mtd:
    mtd_text = "\n### MTD Comparison (from view)\n\n"
    mtd_text += "| Metric | Value |\n|--------|-------|\n"
    for row in mtd:
        for k, v in row.items():
            if v is not None:
                mtd_text += f"| {k} | {v} |\n"


# ══════════════════════════════════════════════════════════════
# 4. GENERATE REPORT
# ══════════════════════════════════════════════════════════════

def fmt(val, prefix="$", decimals=2):
    """Format a number with optional prefix."""
    if prefix == "$":
        return f"${val:,.{decimals}f}"
    elif prefix == "%":
        return f"{val:.{decimals}f}%"
    else:
        return f"{val:,.{decimals}f}"


def yoy_change(current, prior):
    """Calculate YoY % change."""
    if prior == 0:
        return "N/A (no prior data)"
    change = ((current - prior) / abs(prior)) * 100
    direction = "+" if change >= 0 else ""
    return f"{direction}{change:.1f}%"


report_lines = []
r = report_lines.append

r("# Financial Analysis: Unit Economics & Operational Costs")
r(f"\n**Agent**: Financial/Operations Agent A")
r(f"**Period**: {START_DATE} to {END_DATE} (30 days)")
r(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
r(f"**Data Source**: Supabase (daily_sales, daily_ad_spend, daily_shipping, daily_cogs, cogs_lookup)")

# --- P&L Summary ---
r("\n---\n")
r("## 1. P&L Summary (Last 30 Days)\n")
r("| Line Item | Amount | % of Revenue |")
r("|-----------|--------|-------------|")
r(f"| **Revenue** | {fmt(total_revenue)} | 100.0% |")
r(f"| COGS | ({fmt(total_cogs_val)}) | {fmt(cogs_pct, '%', 1)} |")
r(f"| **Gross Profit** | {fmt(gross_profit)} | {fmt(gross_margin_pct, '%', 1)} |")
r(f"| Shipping | ({fmt(total_shipping_cost)}) | {fmt(shipping_pct, '%', 1)} |")
r(f"| Ad Spend | ({fmt(total_ad_spend_val)}) | {fmt((total_ad_spend_val/total_revenue*100) if total_revenue else 0, '%', 1)} |")
r(f"| **Net Profit** | {fmt(net_profit)} | {fmt(net_margin_pct, '%', 1)} |")
r(f"\n- **Total Orders**: {total_orders:,}")
r(f"- **AOV**: {fmt(aov)}")
r(f"- **Avg Daily Revenue**: {fmt(avg_daily_revenue)}")

# --- Margin Health ---
r("\n---\n")
r("## 2. Margin Health\n")
r("| Metric | Current (30d) | Last Year | YoY Change |")
r("|--------|--------------|-----------|------------|")
r(f"| Gross Margin % | {fmt(gross_margin_pct, '%', 1)} | {fmt(gross_margin_ly, '%', 1)} | {yoy_change(gross_margin_pct, gross_margin_ly)} |")
r(f"| Net Margin % | {fmt(net_margin_pct, '%', 1)} | {fmt(net_margin_ly, '%', 1)} | {yoy_change(net_margin_pct, net_margin_ly)} |")
r(f"| Shipping % of Rev | {fmt(shipping_pct, '%', 1)} | {fmt(shipping_pct_ly, '%', 1)} | {yoy_change(shipping_pct, shipping_pct_ly)} |")
r(f"| AOV | {fmt(aov)} | {fmt(aov_ly)} | {yoy_change(aov, aov_ly)} |")
r(f"| MER | {fmt(mer, '', 2)}x | {fmt(mer_ly, '', 2)}x | {yoy_change(mer, mer_ly)} |")

r(f"\n**Gross Margin Trend**: {gm_trend} (first half avg: {first_half_gm:.1f}% -> second half avg: {second_half_gm:.1f}%)")
r(f"**Net Margin Trend**: {nm_trend} (first half avg: {first_half_nm:.1f}% -> second half avg: {second_half_nm:.1f}%)")

# --- Negative Margin Products ---
r("\n---\n")
r("## 3. Top Money-Losing Products (Negative Margins)\n")
if margin_tiers["negative"]:
    r(f"**{len(margin_tiers['negative'])} SKUs selling below cost:**\n")
    r("| SKU | Product | Unit Cost | Selling Price | Margin % |")
    r("|-----|---------|-----------|--------------|----------|")
    for item in margin_tiers["negative"][:20]:
        r(f"| {item['sku']} | {item['name'][:50]} | {fmt(item['cost'])} | {fmt(item['price'])} | {fmt(item['margin'], '%', 1)} |")
else:
    r("No SKUs currently have negative margins.")

r(f"\n### Margin Tier Distribution ({len(cogs_lookup)} total SKUs)\n")
r("| Tier | Count | % of Catalog |")
r("|------|-------|-------------|")
for tier_name in ["negative", "0-20%", "20-40%", "40-60%", "60%+"]:
    count = len(margin_tiers[tier_name])
    pct = (count / len(cogs_lookup) * 100) if cogs_lookup else 0
    r(f"| {tier_name} | {count} | {pct:.1f}% |")
r(f"| No price data | {len(margin_tiers['no_price'])} | {(len(margin_tiers['no_price']) / len(cogs_lookup) * 100) if cogs_lookup else 0:.1f}% |")

r(f"\n### COGS Coverage")
r(f"- **SKUs in cogs_lookup**: {len(cogs_lookup)}")
r(f"- **Unmatched units (30d)**: {int(unmatched_units_total)}")
r(f"- **Total units sold (30d)**: {int(total_units)}")
r(f"- **COGS coverage rate**: {cogs_coverage:.1f}%")
if unmatched_units_total > 0:
    r(f"- **WARNING**: {int(unmatched_units_total)} units sold without COGS data — actual margins may be LOWER than reported")

# --- Shipping Cost Analysis ---
r("\n---\n")
r("## 4. Shipping Cost Analysis\n")
r(f"- **Total shipping cost (30d)**: {fmt(total_shipping_cost)}")
r(f"- **Shipping as % of revenue**: {fmt(shipping_pct, '%', 1)}")
r(f"- **Avg shipping cost per order**: {fmt(total_shipping_cost / total_orders if total_orders else 0)}")
r(f"- **Avg daily shipping cost**: {fmt(avg_daily_shipping)}")

if total_revenue_ly:
    r(f"\n**YoY Comparison**:")
    r(f"- Last year shipping %: {fmt(shipping_pct_ly, '%', 1)}")
    r(f"- Change: {yoy_change(shipping_pct, shipping_pct_ly)}")
    if shipping_pct > shipping_pct_ly:
        delta_dollars = total_revenue * (shipping_pct - shipping_pct_ly) / 100
        r(f"- **Shipping cost creep is costing ~{fmt(delta_dollars)} extra per 30-day period**")

# --- Ad Spend Efficiency ---
r("\n---\n")
r("## 5. Ad Spend Efficiency\n")
r(f"- **Total ad spend (30d)**: {fmt(total_ad_spend_val)}")
r(f"- **Ad spend as % of revenue**: {fmt((total_ad_spend_val/total_revenue*100) if total_revenue else 0, '%', 1)}")
r(f"- **MER (Revenue / Ad Spend)**: {fmt(mer, '', 2)}x")
r(f"- **ROAS**: {fmt(roas, '', 2)}x")

if total_ad_spend_ly:
    r(f"\n**YoY Comparison**:")
    r(f"- Last year MER: {fmt(mer_ly, '', 2)}x")
    r(f"- MER change: {yoy_change(mer, mer_ly)}")

# Ad spend by channel
if ad_by_channel:
    r(f"\n**Ad Spend by Channel**:\n")
    r("| Channel | Spend | % of Total |")
    r("|---------|-------|-----------|")
    for ch, spend in sorted(ad_by_channel.items(), key=lambda x: -x[1]):
        pct = (spend / total_ad_spend_val * 100) if total_ad_spend_val else 0
        r(f"| {ch} | {fmt(spend)} | {pct:.1f}% |")

# --- Channel Comparison ---
r("\n---\n")
r("## 6. Channel Comparison (WC vs Walmart)\n")
if channel_profit:
    r("| Metric | " + " | ".join(channel_profit.keys()) + " |")
    r("|--------|" + "|".join(["-------"] * len(channel_profit)) + "|")

    metrics = [
        ("Revenue", "revenue", "$"),
        ("Orders", "orders", ""),
        ("AOV", "aov", "$"),
        ("COGS", "cogs", "$"),
        ("Shipping (allocated)", "shipping", "$"),
        ("Ad Spend", "ad_spend", "$"),
        ("Gross Profit", "gross_profit", "$"),
        ("Net Profit", "net_profit", "$"),
        ("Gross Margin %", "gross_margin", "%"),
        ("Net Margin %", "net_margin", "%"),
    ]
    for label, key, sym in metrics:
        vals = []
        for ch in channel_profit:
            v = channel_profit[ch][key]
            if sym == "$":
                vals.append(fmt(v))
            elif sym == "%":
                vals.append(fmt(v, "%", 1))
            else:
                vals.append(f"{v:,}" if isinstance(v, int) else f"{v:,.0f}")
        r(f"| {label} | " + " | ".join(vals) + " |")

    # Flag unprofitable channels
    for ch, data in channel_profit.items():
        if data["net_profit"] < 0:
            r(f"\n**WARNING: {ch} is unprofitable** — losing {fmt(abs(data['net_profit']))} over 30 days (net margin: {data['net_margin']:.1f}%)")

# --- YoY Financial Health ---
r("\n---\n")
r("## 7. YoY Financial Health Comparison\n")
r("| Metric | Current 30d | Last Year 30d | YoY Change |")
r("|--------|------------|--------------|------------|")
r(f"| Revenue | {fmt(total_revenue)} | {fmt(total_revenue_ly)} | {yoy_change(total_revenue, total_revenue_ly)} |")
r(f"| Orders | {total_orders:,} | {total_orders_ly:,} | {yoy_change(total_orders, total_orders_ly)} |")
r(f"| COGS | {fmt(total_cogs_val)} | {fmt(total_cogs_ly)} | {yoy_change(total_cogs_val, total_cogs_ly)} |")
r(f"| Gross Profit | {fmt(gross_profit)} | {fmt(gross_profit_ly)} | {yoy_change(gross_profit, gross_profit_ly)} |")
r(f"| Shipping | {fmt(total_shipping_cost)} | {fmt(total_shipping_ly)} | {yoy_change(total_shipping_cost, total_shipping_ly)} |")
r(f"| Ad Spend | {fmt(total_ad_spend_val)} | {fmt(total_ad_spend_ly)} | {yoy_change(total_ad_spend_val, total_ad_spend_ly)} |")
r(f"| Net Profit | {fmt(net_profit)} | {fmt(net_profit_ly)} | {yoy_change(net_profit, net_profit_ly)} |")

# --- Top 5 Optimization Opportunities ---
r("\n---\n")
r("## 8. Top 5 Financial Optimization Opportunities\n")

opportunities = []

# 1. Negative margin products
if margin_tiers["negative"]:
    # Estimate impact: if we fix pricing on negative-margin items
    neg_loss = sum(abs(i["price"] - i["cost"]) for i in margin_tiers["negative"])
    opportunities.append({
        "title": "Fix negative-margin SKUs",
        "detail": f"{len(margin_tiers['negative'])} SKUs selling below cost. Raise prices or discontinue.",
        "impact": neg_loss * 12,  # rough annualized
        "priority": "CRITICAL",
    })

# 2. COGS coverage gaps
if unmatched_units_total > 0 and total_units > 0:
    # If unmatched units have same avg COGS, we're understating costs
    avg_cogs_per_unit = total_cogs_val / (total_units - unmatched_units_total) if (total_units - unmatched_units_total) else 0
    hidden_cogs = unmatched_units_total * avg_cogs_per_unit
    opportunities.append({
        "title": "Close COGS coverage gaps",
        "detail": f"{int(unmatched_units_total)} units/30d without COGS data. Estimated hidden cost: {fmt(hidden_cogs)}/month.",
        "impact": hidden_cogs * 12,
        "priority": "HIGH",
    })

# 3. Shipping cost optimization
if shipping_pct > 10:
    potential_save = total_revenue * 0.02  # target 2% reduction
    opportunities.append({
        "title": "Reduce shipping costs",
        "detail": f"Shipping at {shipping_pct:.1f}% of revenue. Negotiate rates, optimize packaging, or adjust free-shipping threshold.",
        "impact": potential_save * 12,
        "priority": "HIGH",
    })

# 4. Ad spend efficiency
if mer < 5:
    target_mer = 5.0
    target_spend = total_revenue / target_mer
    savings = total_ad_spend_val - target_spend
    if savings > 0:
        opportunities.append({
            "title": "Improve MER to 5.0x",
            "detail": f"Current MER: {mer:.2f}x. Reduce inefficient spend or increase conversion rates.",
            "impact": savings * 12,
            "priority": "MEDIUM",
        })

# 5. Low-margin product mix
low_margin_count = len(margin_tiers["0-20%"])
if low_margin_count:
    opportunities.append({
        "title": "Improve low-margin product mix",
        "detail": f"{low_margin_count} SKUs in 0-20% margin tier. Bundle with higher-margin items or raise prices.",
        "impact": 0,  # hard to estimate
        "priority": "MEDIUM",
    })

# 6. Channel optimization
for ch, data in channel_profit.items():
    if data["net_margin"] < 0:
        opportunities.append({
            "title": f"Fix {ch} channel profitability",
            "detail": f"{ch} losing {fmt(abs(data['net_profit']))}/30d at {data['net_margin']:.1f}% net margin.",
            "impact": abs(data["net_profit"]) * 12,
            "priority": "HIGH",
        })

# Sort by impact (descending), take top 5
opportunities.sort(key=lambda x: -x["impact"])
for i, opp in enumerate(opportunities[:5], 1):
    impact_str = fmt(opp["impact"]) if opp["impact"] > 0 else "TBD"
    r(f"### {i}. [{opp['priority']}] {opp['title']}")
    r(f"- {opp['detail']}")
    r(f"- **Estimated annual impact**: {impact_str}")
    r("")

if not opportunities:
    r("Insufficient data to identify specific opportunities. Ensure all tables have data for the analysis period.")

# --- Break-Even Analysis ---
r("\n---\n")
r("## 9. Break-Even Analysis & Risk Assessment\n")
r(f"- **Average daily fixed costs** (ads + shipping): {fmt(avg_daily_fixed)}")
r(f"- **COGS as % of revenue**: {fmt(cogs_pct, '%', 1)}")
r(f"- **Contribution margin ratio**: {fmt(contribution_margin_pct, '%', 1)}")
r(f"- **Break-even daily revenue**: {fmt(breakeven_daily)}")
r(f"- **Actual avg daily revenue**: {fmt(avg_daily_revenue)}")
r(f"- **Buffer above break-even**: {fmt(avg_daily_revenue - breakeven_daily)} ({((avg_daily_revenue - breakeven_daily) / breakeven_daily * 100) if breakeven_daily else 0:.1f}%)")
r(f"- **Days below break-even (last 30d)**: {days_below_breakeven} of {len(daily_margins)}")

if days_below_breakeven > 10:
    r(f"\n**RISK: HIGH** — {days_below_breakeven} days below break-even in the last 30 days. Business is frequently unprofitable on a daily basis.")
elif days_below_breakeven > 5:
    r(f"\n**RISK: MODERATE** — {days_below_breakeven} days below break-even. Some volatility but generally profitable.")
elif days_below_breakeven > 0:
    r(f"\n**RISK: LOW** — Only {days_below_breakeven} days below break-even. Generally healthy daily performance.")
else:
    r(f"\n**RISK: MINIMAL** — No days below break-even. Strong daily performance.")

# --- Daily Trend Table (last 10 days) ---
r("\n### Daily Trend (Last 10 Days)\n")
r("| Date | Revenue | Orders | Gross Margin | Net Margin |")
r("|------|---------|--------|-------------|------------|")
for dm in daily_margins[-10:]:
    r(f"| {dm['date']} | {fmt(dm['revenue'])} | {dm['orders']} | {fmt(dm['gross_margin'], '%', 1)} | {fmt(dm['net_margin'], '%', 1)} |")

# MTD section
if mtd_text:
    r("\n---\n")
    r("## 10. MTD Comparison\n")
    r(mtd_text)

# --- Appendix: Summary View Data ---
if summary:
    r("\n---\n")
    r("## Appendix: Daily Summary View (Raw)\n")
    r("First 5 rows from daily_summary view:\n")
    for row in summary[:5]:
        r(f"```json\n{json.dumps(row, indent=2, default=str)}\n```\n")

# Write report
report_path = REPORT_DIR / "financial_a_findings.md"
report_content = "\n".join(report_lines)
report_path.write_text(report_content)
print(f"\n[DONE] Report written to: {report_path}")
print(f"[DONE] Report size: {len(report_content):,} characters, {len(report_lines)} lines")
