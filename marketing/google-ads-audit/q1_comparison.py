"""
Google Ads Q1 Performance Comparison — 2024 vs 2025 vs 2026
Pulls search terms, products (Shopping), and budget data for Jan 1 - Mar 9 each year.
"""
import json
from pathlib import Path
from google.ads.googleads.client import GoogleAdsClient

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

# Strip dashes from customer IDs
customer_id = env_vars["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
login_customer_id = env_vars.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")

# Configure client
config = {
    "developer_token": env_vars["GOOGLE_ADS_DEVELOPER_TOKEN"],
    "client_id": env_vars["GOOGLE_ADS_CLIENT_ID"],
    "client_secret": env_vars["GOOGLE_ADS_CLIENT_SECRET"],
    "refresh_token": env_vars["GOOGLE_ADS_REFRESH_TOKEN"],
    "use_proto_plus": True,
}
if login_customer_id:
    config["login_customer_id"] = login_customer_id

print("Connecting to Google Ads API...")
client = GoogleAdsClient.load_from_dict(config)
ga_service = client.get_service("GoogleAdsService")

# Date ranges: Q1 each year (Jan 1 - Mar 9 to match current date)
YEARS = [2024, 2025, 2026]
DATE_RANGES = {
    year: (f"{year}-01-01", f"{year}-03-09")
    for year in YEARS
}


def run_query(query, year):
    """Run a GAQL query for a specific date range."""
    start, end = DATE_RANGES[year]
    q = query.replace("{START}", start).replace("{END}", end)
    try:
        response = ga_service.search(customer_id=customer_id, query=q)
        return list(response)
    except Exception as e:
        print(f"  [ERR] {year}: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# QUERY 1: Campaign-level performance (budget overview)
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  QUERY 1: CAMPAIGN PERFORMANCE (Q1 each year)")
print("=" * 70)

CAMPAIGN_QUERY = """
    SELECT
        campaign.name,
        campaign.advertising_channel_type,
        campaign.status,
        metrics.cost_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.conversions,
        metrics.conversions_value,
        metrics.ctr,
        metrics.average_cpc,
        metrics.cost_per_conversion
    FROM campaign
    WHERE segments.date BETWEEN '{START}' AND '{END}'
        AND campaign.status != 'REMOVED'
    ORDER BY metrics.cost_micros DESC
"""

campaign_data = {}
for year in YEARS:
    print(f"\n  --- {year} (Jan 1 - Mar 9) ---")
    rows = run_query(CAMPAIGN_QUERY, year)
    year_data = []
    total_cost = 0
    total_clicks = 0
    total_impressions = 0
    total_conversions = 0
    total_conv_value = 0

    for row in rows:
        c = row.campaign
        m = row.metrics
        cost = m.cost_micros / 1_000_000
        total_cost += cost
        total_clicks += m.clicks
        total_impressions += m.impressions
        total_conversions += m.conversions
        total_conv_value += m.conversions_value

        year_data.append({
            "name": c.name,
            "type": str(c.advertising_channel_type).split(".")[-1],
            "status": str(c.status).split(".")[-1],
            "cost": round(cost, 2),
            "impressions": m.impressions,
            "clicks": m.clicks,
            "ctr": round(m.ctr * 100, 2) if m.ctr else 0,
            "avg_cpc": round(m.average_cpc / 1_000_000, 2) if m.average_cpc else 0,
            "conversions": round(m.conversions, 1),
            "conv_value": round(m.conversions_value, 2),
            "roas": round(m.conversions_value / cost, 2) if cost > 0 else 0,
        })

    for d in year_data:
        print(f"    {d['name'][:40]:<40s} | ${d['cost']:>8.2f} | {d['clicks']:>5d} clicks | {d['conversions']:>5.1f} conv | ${d['conv_value']:>9.2f} rev | {d['roas']:>5.2f}x ROAS")

    print(f"\n    TOTALS: ${total_cost:,.2f} spent | {total_clicks:,} clicks | {total_conversions:.1f} conv | ${total_conv_value:,.2f} revenue | {total_conv_value/total_cost:.2f}x ROAS" if total_cost > 0 else "    TOTALS: No data")
    campaign_data[year] = {
        "campaigns": year_data,
        "total_cost": round(total_cost, 2),
        "total_clicks": total_clicks,
        "total_impressions": total_impressions,
        "total_conversions": round(total_conversions, 1),
        "total_conv_value": round(total_conv_value, 2),
    }


# ═══════════════════════════════════════════════════════════════
# QUERY 2: Top search terms
# ═══════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("  QUERY 2: TOP SEARCH TERMS (Q1 each year, top 30 by spend)")
print("=" * 70)

SEARCH_TERM_QUERY = """
    SELECT
        search_term_view.search_term,
        campaign.name,
        metrics.cost_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.conversions,
        metrics.conversions_value,
        metrics.ctr
    FROM search_term_view
    WHERE segments.date BETWEEN '{START}' AND '{END}'
        AND metrics.impressions > 0
    ORDER BY metrics.cost_micros DESC
    LIMIT 30
"""

search_data = {}
for year in YEARS:
    print(f"\n  --- {year} (Jan 1 - Mar 9) ---")
    rows = run_query(SEARCH_TERM_QUERY, year)
    year_terms = []
    for row in rows:
        cost = row.metrics.cost_micros / 1_000_000
        term = row.search_term_view.search_term
        conv = row.metrics.conversions
        conv_val = row.metrics.conversions_value
        roas = conv_val / cost if cost > 0 else 0
        year_terms.append({
            "term": term,
            "campaign": row.campaign.name,
            "cost": round(cost, 2),
            "clicks": row.metrics.clicks,
            "impressions": row.metrics.impressions,
            "ctr": round(row.metrics.ctr * 100, 2) if row.metrics.ctr else 0,
            "conversions": round(conv, 1),
            "conv_value": round(conv_val, 2),
            "roas": round(roas, 2),
        })
        print(f"    {term[:45]:<45s} | ${cost:>7.2f} | {row.metrics.clicks:>4d} cl | {conv:>4.1f} cv | ${conv_val:>8.2f} | {roas:>5.2f}x")

    search_data[year] = year_terms
    if not year_terms:
        print("    (no data)")


# ═══════════════════════════════════════════════════════════════
# QUERY 3: Shopping/product performance
# ═══════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("  QUERY 3: SHOPPING PRODUCT PERFORMANCE (Q1 each year, top 25)")
print("=" * 70)

SHOPPING_QUERY = """
    SELECT
        segments.product_title,
        segments.product_type_l1,
        campaign.name,
        metrics.cost_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.conversions,
        metrics.conversions_value,
        metrics.ctr
    FROM shopping_performance_view
    WHERE segments.date BETWEEN '{START}' AND '{END}'
        AND metrics.impressions > 0
    ORDER BY metrics.conversions_value DESC
    LIMIT 25
"""

shopping_data = {}
for year in YEARS:
    print(f"\n  --- {year} (Jan 1 - Mar 9) ---")
    rows = run_query(SHOPPING_QUERY, year)
    year_products = []
    for row in rows:
        cost = row.metrics.cost_micros / 1_000_000
        conv_val = row.metrics.conversions_value
        roas = conv_val / cost if cost > 0 else 0
        title = row.segments.product_title or "(untitled)"
        year_products.append({
            "title": title,
            "product_type": row.segments.product_type_l1 or "",
            "campaign": row.campaign.name,
            "cost": round(cost, 2),
            "clicks": row.metrics.clicks,
            "conversions": round(row.metrics.conversions, 1),
            "conv_value": round(conv_val, 2),
            "roas": round(roas, 2),
        })
        print(f"    {title[:45]:<45s} | ${cost:>7.2f} | {row.metrics.clicks:>4d} cl | ${conv_val:>8.2f} rev | {roas:>5.2f}x")

    shopping_data[year] = year_products
    if not year_products:
        print("    (no data)")


# ═══════════════════════════════════════════════════════════════
# SAVE RAW DATA
# ═══════════════════════════════════════════════════════════════
output = {
    "date_ranges": {str(k): v for k, v in DATE_RANGES.items()},
    "campaigns": {str(k): v for k, v in campaign_data.items()},
    "search_terms": {str(k): v for k, v in search_data.items()},
    "shopping": {str(k): v for k, v in shopping_data.items()},
}

output_path = Path(__file__).resolve().parent / "q1_comparison_data.json"
with open(output_path, "w") as f:
    json.dump(output, f, indent=2, default=str)
print(f"\n\nRaw data saved to: {output_path}")


# ═══════════════════════════════════════════════════════════════
# YOY COMPARISON SUMMARY
# ═══════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("  YEAR-OVER-YEAR Q1 COMPARISON SUMMARY")
print("=" * 70)

def pct_change(new, old):
    if old == 0:
        return "N/A"
    return f"{((new - old) / old) * 100:+.1f}%"

headers = ["Metric", "Q1 2024", "Q1 2025", "Q1 2026", "YoY 24→25", "YoY 25→26"]
print(f"\n  {'Metric':<20s} | {'Q1 2024':>12s} | {'Q1 2025':>12s} | {'Q1 2026':>12s} | {'24→25':>10s} | {'25→26':>10s}")
print("  " + "-" * 90)

for label, key, fmt in [
    ("Spend", "total_cost", "${:,.2f}"),
    ("Clicks", "total_clicks", "{:,}"),
    ("Impressions", "total_impressions", "{:,}"),
    ("Conversions", "total_conversions", "{:.1f}"),
    ("Revenue", "total_conv_value", "${:,.2f}"),
]:
    vals = [campaign_data.get(y, {}).get(key, 0) for y in YEARS]
    formatted = [fmt.format(v) for v in vals]
    chg1 = pct_change(vals[1], vals[0])
    chg2 = pct_change(vals[2], vals[1])
    print(f"  {label:<20s} | {formatted[0]:>12s} | {formatted[1]:>12s} | {formatted[2]:>12s} | {chg1:>10s} | {chg2:>10s}")

# ROAS
for year in YEARS:
    cd = campaign_data.get(year, {})
    if cd.get("total_cost", 0) > 0:
        cd["roas"] = round(cd["total_conv_value"] / cd["total_cost"], 2)
    else:
        cd["roas"] = 0

roas_vals = [campaign_data.get(y, {}).get("roas", 0) for y in YEARS]
print(f"  {'ROAS':<20s} | {roas_vals[0]:>11.2f}x | {roas_vals[1]:>11.2f}x | {roas_vals[2]:>11.2f}x | {pct_change(roas_vals[1], roas_vals[0]):>10s} | {pct_change(roas_vals[2], roas_vals[1]):>10s}")

# CPC
for year in YEARS:
    cd = campaign_data.get(year, {})
    if cd.get("total_clicks", 0) > 0:
        cd["avg_cpc"] = round(cd["total_cost"] / cd["total_clicks"], 2)
    else:
        cd["avg_cpc"] = 0

cpc_vals = [campaign_data.get(y, {}).get("avg_cpc", 0) for y in YEARS]
print(f"  {'Avg CPC':<20s} | ${cpc_vals[0]:>11.2f} | ${cpc_vals[1]:>11.2f} | ${cpc_vals[2]:>11.2f} | {pct_change(cpc_vals[1], cpc_vals[0]):>10s} | {pct_change(cpc_vals[2], cpc_vals[1]):>10s}")

# Conv Rate
for year in YEARS:
    cd = campaign_data.get(year, {})
    if cd.get("total_clicks", 0) > 0:
        cd["conv_rate"] = round(cd["total_conversions"] / cd["total_clicks"] * 100, 2)
    else:
        cd["conv_rate"] = 0

cr_vals = [campaign_data.get(y, {}).get("conv_rate", 0) for y in YEARS]
print(f"  {'Conv Rate':<20s} | {cr_vals[0]:>11.2f}% | {cr_vals[1]:>11.2f}% | {cr_vals[2]:>11.2f}% | {pct_change(cr_vals[1], cr_vals[0]):>10s} | {pct_change(cr_vals[2], cr_vals[1]):>10s}")

print("\n\nDone. See q1_comparison_data.json for full raw data.")
