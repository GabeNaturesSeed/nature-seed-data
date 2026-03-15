#!/usr/bin/env python3
"""
Acquisition Agent B — Google Search Console + Supabase Analysis
Pulls organic search data and revenue metrics to assess SEO funnel health.
"""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

# ══════════════════════════════════════════════════════════════
# ENV LOADING (same pattern as daily_pull.py)
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

# Also check OS environment as fallback
def _env(key, default=""):
    return env_vars.get(key, os.environ.get(key, default))

GOOGLE_CLIENT_ID = _env("GOOGLE_ADS_CLIENT_ID")
GOOGLE_CLIENT_SECRET = _env("GOOGLE_ADS_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = _env("GOOGLE_ADS_REFRESH_TOKEN")

SUPABASE_URL = _env("SUPABASE_URL")
SUPABASE_KEY = _env("SUPABASE_SECRET_API_KEY")

# Check if credentials are available
HAS_GOOGLE_CREDS = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REFRESH_TOKEN)
HAS_SUPABASE_CREDS = bool(SUPABASE_URL and SUPABASE_KEY)

if not HAS_GOOGLE_CREDS:
    print("[WARN] Google OAuth credentials not found — GSC queries will be skipped")
if not HAS_SUPABASE_CREDS:
    print("[WARN] Supabase credentials not found — revenue queries will be skipped")

SITE_URL = "sc-domain:naturesseed.com"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GSC_API_BASE = "https://searchconsole.googleapis.com/v1"

START_DATE = "2026-02-13"
END_DATE = "2026-03-14"


# ══════════════════════════════════════════════════════════════
# OAUTH TOKEN
# ══════════════════════════════════════════════════════════════

def get_access_token():
    """Exchange refresh token for access token."""
    resp = requests.post(TOKEN_ENDPOINT, data={
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }, timeout=15)
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print(f"[OK] Got access token ({token[:12]}...)")
    return token


# ══════════════════════════════════════════════════════════════
# GSC QUERY HELPER
# ══════════════════════════════════════════════════════════════

def gsc_query(access_token, dimensions, row_limit=100, dim_filters=None):
    """Run a Search Analytics query against GSC API."""
    url = f"{GSC_API_BASE}/sites/{requests.utils.quote(SITE_URL, safe='')}/searchAnalytics/query"
    body = {
        "startDate": START_DATE,
        "endDate": END_DATE,
        "dimensions": dimensions,
        "rowLimit": row_limit,
        "dataState": "final",
    }
    if dim_filters:
        body["dimensionFilterGroups"] = [{"filters": dim_filters}]

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    if resp.status_code != 200:
        print(f"[ERROR] GSC query failed ({resp.status_code}): {resp.text[:300]}")
        resp.raise_for_status()
    data = resp.json()
    return data.get("rows", [])


# ══════════════════════════════════════════════════════════════
# SUPABASE QUERY
# ══════════════════════════════════════════════════════════════

def supabase_get(table, params):
    """Query Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {"apikey": SUPABASE_KEY}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ══════════════════════════════════════════════════════════════
# MAIN DATA PULLS
# ══════════════════════════════════════════════════════════════

def main():
    print(f"═══ Acquisition Agent B — Search Console Analysis ═══")
    print(f"Date range: {START_DATE} to {END_DATE}\n")

    top_queries = []
    top_pages = []
    device_data = []
    easy_wins = []
    low_ctr_pages = []

    if HAS_GOOGLE_CREDS:
        token = get_access_token()

        # 1. Top 100 queries by clicks
        print("[1/5] Pulling top 100 queries by clicks...")
        top_queries = gsc_query(token, ["query"], row_limit=100)
        print(f"      Got {len(top_queries)} queries")

        # 2. Top 50 pages by clicks
        print("[2/5] Pulling top 50 pages by clicks...")
        top_pages = gsc_query(token, ["page"], row_limit=50)
        print(f"      Got {len(top_pages)} pages")

        # 3. Device breakdown
        print("[3/5] Pulling device breakdown...")
        device_data = gsc_query(token, ["device"], row_limit=10)
        print(f"      Got {len(device_data)} device types")

        # 4. Easy-win queries (position 4-20)
        print("[4/5] Pulling easy-win queries (position 4–20)...")
        all_queries_broad = gsc_query(token, ["query"], row_limit=500)
        easy_wins = [
            r for r in all_queries_broad
            if 4.0 <= r.get("position", 0) <= 20.0
        ]
        easy_wins.sort(key=lambda r: r.get("impressions", 0), reverse=True)
        easy_wins = easy_wins[:50]
        print(f"      Got {len(easy_wins)} easy-win queries")
    else:
        print("[SKIP] GSC queries — no Google OAuth credentials available")

    # 5. High impressions, low CTR pages
    if HAS_GOOGLE_CREDS:
        print("[5/5] Pulling high-impression/low-CTR pages...")
        all_pages_broad = gsc_query(token, ["page"], row_limit=200)
        if all_pages_broad:
            imp_values = sorted([r["impressions"] for r in all_pages_broad])
            median_imp = imp_values[len(imp_values) // 2]
            low_ctr_pages = [
                r for r in all_pages_broad
                if r.get("impressions", 0) >= median_imp and r.get("ctr", 1) < 0.03
            ]
            low_ctr_pages.sort(key=lambda r: r.get("impressions", 0), reverse=True)
            low_ctr_pages = low_ctr_pages[:25]
        print(f"      Got {len(low_ctr_pages)} pages with high impressions but low CTR")

    # ── Supabase: Revenue & Ad Spend ──
    sales_rows = []
    ad_rows = []
    if HAS_SUPABASE_CREDS:
        print("\n[Supabase] Pulling revenue and ad spend data...")
        sales_rows = supabase_get("daily_sales", {
            "select": "report_date,channel,revenue,orders",
            "report_date": f"gte.{START_DATE}",
            "and": f"(report_date.lte.{END_DATE})",
        })
        print(f"      Got {len(sales_rows)} sales rows")

        ad_rows = supabase_get("daily_ad_spend", {
            "select": "report_date,channel,spend",
            "report_date": f"gte.{START_DATE}",
            "and": f"(report_date.lte.{END_DATE})",
        })
        print(f"      Got {len(ad_rows)} ad spend rows")
    else:
        print("\n[SKIP] Supabase queries — no credentials available")

    # Compute totals
    wc_revenue = sum(float(r.get("revenue", 0) or 0) for r in sales_rows if r.get("channel") == "woocommerce")
    walmart_revenue = sum(float(r.get("revenue", 0) or 0) for r in sales_rows if r.get("channel") == "walmart")
    total_revenue = wc_revenue + walmart_revenue
    wc_orders = sum(int(r.get("orders", 0) or 0) for r in sales_rows if r.get("channel") == "woocommerce")
    walmart_orders = sum(int(r.get("orders", 0) or 0) for r in sales_rows if r.get("channel") == "walmart")
    total_orders = wc_orders + walmart_orders

    total_ad_spend = sum(float(r.get("spend", 0) or 0) for r in ad_rows)

    print(f"\n═══ Revenue & Spend Summary ═══")
    print(f"  WC Revenue:      ${wc_revenue:,.2f} ({wc_orders} orders)")
    print(f"  Walmart Revenue: ${walmart_revenue:,.2f} ({walmart_orders} orders)")
    print(f"  Total Revenue:   ${total_revenue:,.2f} ({total_orders} orders)")
    print(f"  Total Ad Spend:  ${total_ad_spend:,.2f}")

    # ══════════════════════════════════════════════════════════════
    # BUILD REPORT
    # ══════════════════════════════════════════════════════════════

    report = generate_report(
        top_queries, top_pages, device_data, easy_wins, low_ctr_pages,
        wc_revenue, walmart_revenue, total_revenue, total_orders,
        wc_orders, walmart_orders, total_ad_spend
    )

    report_path = Path(__file__).resolve().parent.parent / "reports" / "acquisition_b_findings.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    print(f"\n[OK] Report saved to {report_path}")


def generate_report(
    top_queries, top_pages, device_data, easy_wins, low_ctr_pages,
    wc_revenue, walmart_revenue, total_revenue, total_orders,
    wc_orders, walmart_orders, total_ad_spend
):
    """Generate the markdown findings report."""

    # Aggregate totals from GSC
    total_clicks = sum(r.get("clicks", 0) for r in top_queries)
    total_impressions = sum(r.get("impressions", 0) for r in top_queries)
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0
    avg_position = (
        sum(r.get("position", 0) * r.get("impressions", 0) for r in top_queries)
        / total_impressions if total_impressions else 0
    )

    # Device breakdown
    device_lines = []
    for d in device_data:
        device_lines.append(
            f"| {d['keys'][0].capitalize()} | {d.get('clicks',0):,} | "
            f"{d.get('impressions',0):,} | {d.get('ctr',0)*100:.1f}% | "
            f"{d.get('position',0):.1f} |"
        )

    # Top queries table
    query_lines = []
    for i, r in enumerate(top_queries[:30], 1):
        q = r["keys"][0]
        query_lines.append(
            f"| {i} | {q[:55]} | {r.get('clicks',0):,} | "
            f"{r.get('impressions',0):,} | {r.get('ctr',0)*100:.1f}% | "
            f"{r.get('position',0):.1f} |"
        )

    # Top pages table
    page_lines = []
    for i, r in enumerate(top_pages[:20], 1):
        p = r["keys"][0].replace("https://naturesseed.com", "")
        page_lines.append(
            f"| {i} | {p[:60]} | {r.get('clicks',0):,} | "
            f"{r.get('impressions',0):,} | {r.get('ctr',0)*100:.1f}% | "
            f"{r.get('position',0):.1f} |"
        )

    # Easy wins table
    easy_win_lines = []
    for i, r in enumerate(easy_wins[:25], 1):
        q = r["keys"][0]
        # Estimate: moving to position 2.5 would ~3x CTR
        current_clicks = r.get("clicks", 0)
        current_imp = r.get("impressions", 0)
        # Top 3 avg CTR ~ 8-12%, estimate conservatively at 8%
        est_new_clicks = current_imp * 0.08
        incremental = max(0, est_new_clicks - current_clicks)
        easy_win_lines.append(
            f"| {i} | {q[:50]} | {r.get('position',0):.1f} | "
            f"{current_imp:,} | {current_clicks:,} | "
            f"{r.get('ctr',0)*100:.1f}% | +{int(incremental):,} |"
        )

    # Low CTR pages table
    low_ctr_lines = []
    for i, r in enumerate(low_ctr_pages[:15], 1):
        p = r["keys"][0].replace("https://naturesseed.com", "")
        low_ctr_lines.append(
            f"| {i} | {p[:55]} | {r.get('impressions',0):,} | "
            f"{r.get('clicks',0):,} | {r.get('ctr',0)*100:.1f}% | "
            f"{r.get('position',0):.1f} |"
        )

    # Revenue attribution estimates
    # Rough model: organic drives traffic that converts without ad click
    # MER (Marketing Efficiency Ratio) = Revenue / Ad Spend
    mer = total_revenue / total_ad_spend if total_ad_spend else 0
    # Conservative estimate: if ads drive ~40% of WC revenue, organic drives ~60%
    # We'll note this is estimated since we don't have exact attribution
    organic_pct_estimate = max(0, 100 - (total_ad_spend / total_revenue * 100)) if total_revenue else 0
    est_organic_revenue = total_revenue * (organic_pct_estimate / 100)

    # Estimated revenue from easy wins
    total_incremental_clicks = sum(
        max(0, r.get("impressions", 0) * 0.08 - r.get("clicks", 0))
        for r in easy_wins[:25]
    )
    # Avg revenue per organic session (rough: total_revenue * organic_pct / total organic clicks)
    rev_per_click = est_organic_revenue / total_clicks if total_clicks else 0
    easy_win_revenue = total_incremental_clicks * rev_per_click

    report = f"""# Acquisition Agent B — Organic Search & SEO Funnel Analysis

**Date Range:** {START_DATE} to {END_DATE}
**Site:** naturesseed.com
**Generated:** {date.today().isoformat()}

---

## 1. Organic Traffic Health Assessment

| Metric | Value |
|--------|-------|
| Total Clicks (top 100 queries) | {total_clicks:,} |
| Total Impressions (top 100 queries) | {total_impressions:,} |
| Weighted Avg CTR | {avg_ctr:.1f}% |
| Weighted Avg Position | {avg_position:.1f} |
| Queries with Position 4-20 (easy wins) | {len(easy_wins)} |
| High-impression/Low-CTR pages | {len(low_ctr_pages)} |

## 2. Top Organic Revenue-Driving Queries (Top 30 by Clicks)

| # | Query | Clicks | Impressions | CTR | Avg Pos |
|---|-------|--------|-------------|-----|---------|
{chr(10).join(query_lines)}

## 3. Top Organic Pages (Top 20 by Clicks)

| # | Page | Clicks | Impressions | CTR | Avg Pos |
|---|------|--------|-------------|-----|---------|
{chr(10).join(page_lines)}

## 4. Mobile vs Desktop Organic Performance

| Device | Clicks | Impressions | CTR | Avg Pos |
|--------|--------|-------------|-----|---------|
{chr(10).join(device_lines)}

## 5. SEO Gaps — High Impressions, Low CTR (< 3%)

These pages are getting seen but not clicked. Likely need title tag and meta description optimization.

| # | Page | Impressions | Clicks | CTR | Avg Pos |
|---|------|-------------|--------|-----|---------|
{chr(10).join(low_ctr_lines) if low_ctr_lines else "| — | No pages found matching criteria | — | — | — | — |"}

## 6. Easy-Win Opportunities — Queries at Position 4-20

These queries are close to page 1 / top 3. Improving content and on-page SEO could move them up significantly.

Estimated incremental clicks assume moving to ~8% CTR (top-3 average).

| # | Query | Pos | Impressions | Clicks | CTR | Est. +Clicks |
|---|-------|-----|-------------|--------|-----|-------------|
{chr(10).join(easy_win_lines)}

**Total estimated incremental clicks from easy wins:** +{int(total_incremental_clicks):,}
**Estimated revenue opportunity:** ${easy_win_revenue:,.0f} (at ${rev_per_click:.2f}/organic click)

## 7. Organic vs Paid Dependency Ratio

| Metric | Value |
|--------|-------|
| Total Revenue (30 days) | ${total_revenue:,.2f} |
| WooCommerce Revenue | ${wc_revenue:,.2f} ({wc_orders} orders) |
| Walmart Revenue | ${walmart_revenue:,.2f} ({walmart_orders} orders) |
| Total Ad Spend | ${total_ad_spend:,.2f} |
| MER (Revenue / Ad Spend) | {mer:.1f}x |
| Est. Organic Revenue Share | {organic_pct_estimate:.0f}% (~${est_organic_revenue:,.0f}) |
| Ad Spend as % of Revenue | {(total_ad_spend/total_revenue*100) if total_revenue else 0:.1f}% |

### Assessment

{"**Healthy organic dependency.** Ad spend is less than 15% of revenue, suggesting strong organic contribution. Focus on protecting and growing organic rankings." if total_revenue and (total_ad_spend/total_revenue) < 0.15 else "**Moderate ad dependency.** Ad spend is " + f"{(total_ad_spend/total_revenue*100):.0f}" + "% of revenue. " + ("Room to grow organic to reduce paid dependency." if total_revenue and (total_ad_spend/total_revenue) < 0.30 else "**High ad dependency.** Consider investing more in SEO to reduce reliance on paid acquisition.") if total_revenue else "No revenue data available."}

## 8. Key Recommendations

1. **Title/Meta Description Audit** — {len(low_ctr_pages)} pages have high impressions but CTR below 3%. Rewriting titles and meta descriptions for these pages is the highest-ROI quick win.

2. **Easy-Win Content Optimization** — {len(easy_wins)} queries rank between positions 4-20. Adding content depth, internal links, and schema markup could push these into top-3 positions, capturing an estimated +{int(total_incremental_clicks):,} clicks/month (~${easy_win_revenue:,.0f} revenue).

3. **Mobile Optimization** — {"Mobile CTR is lower than desktop, suggesting mobile UX or page speed issues need attention." if any(d["keys"][0] == "MOBILE" or d["keys"][0] == "mobile" for d in device_data if d.get("ctr", 0) < (next((x.get("ctr", 0) for x in device_data if x["keys"][0].lower() == "desktop"), 0))) else "Review device-specific performance data above for gaps."}

4. **Organic Revenue Growth** — With an estimated ${rev_per_click:.2f} per organic click, every 1,000 additional organic clicks = ~${rev_per_click * 1000:,.0f} in revenue.

---
*Report generated by Acquisition Agent B — Google Search Console + Supabase analysis*
"""
    return report


if __name__ == "__main__":
    main()
