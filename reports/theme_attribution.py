#!/usr/bin/env python3
"""
Theme Attribution Analysis — Nature's Seed
===========================================
Compares pre vs post theme deploy across every data source to determine
whether the sales increase is due to:
  1. The new theme (site experience / search improvements)
  2. Seasonality (March = peak planting season)
  3. Strategy changes (Google Ads drip, Klaviyo campaigns, etc.)

Data Sources:
  - GA4: sessions, conversion rate, bounce rate, engagement — by channel
  - Google Search Console: organic clicks, impressions, CTR, position
  - Google Ads: spend, clicks, conversions, ROAS
  - Supabase: historical daily revenue for YoY comparison

Key Dates:
  - Theme deploy: Friday, February 27, 2026
  - Post period:  Feb 28 – Mar 12, 2026 (13 days)
  - Pre period:   Feb 14 – Feb 27, 2026 (14 days)
  - YoY post:     Feb 28 – Mar 12, 2025 (seasonality control)
  - YoY pre:      Feb 14 – Feb 27, 2025

Usage:
    python3 reports/theme_attribution.py
"""

import json
import html as html_mod
import logging
from datetime import date, timedelta
from pathlib import Path

import requests
from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric
)
from googleapiclient.discovery import build
from google.ads.googleads.client import GoogleAdsClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("theme_attribution")

ROOT = Path(__file__).resolve().parents[1]

# ── Key Dates ─────────────────────────────────────────────────────────────────

THEME_DEPLOY = date(2026, 2, 27)

POST_START = date(2026, 2, 28)
POST_END   = date(2026, 3, 12)

PRE_START  = date(2026, 2, 14)
PRE_END    = date(2026, 2, 27)

# Year-over-Year (same calendar window 2025)
YOY_POST_START = date(2025, 2, 28)
YOY_POST_END   = date(2025, 3, 12)

YOY_PRE_START  = date(2025, 2, 14)
YOY_PRE_END    = date(2025, 2, 27)


# ── Env ───────────────────────────────────────────────────────────────────────

def _load_env() -> dict:
    env = {}
    for p in [ROOT / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env[key.strip()] = val.strip().strip("'\"")
    return env

ENV = _load_env()


# ── Google OAuth ──────────────────────────────────────────────────────────────

def _google_creds() -> Credentials:
    return Credentials(
        token=None,
        refresh_token=ENV["GOOGLE_ADS_REFRESH_TOKEN"],
        client_id=ENV["GOOGLE_ADS_CLIENT_ID"],
        client_secret=ENV["GOOGLE_ADS_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )


# ── GA4 ───────────────────────────────────────────────────────────────────────

def pull_ga4_period(ga_client, property_id: str, start: date, end: date,
                    dimensions: list = None) -> list:
    """
    Pull GA4 data for a date range. Returns list of row dicts.
    Metrics: sessions, totalUsers, newUsers, ecommercePurchases,
             purchaseRevenue, sessionConversionRate, bounceRate,
             averageSessionDuration, engagedSessions
    """
    dim_objs = [Dimension(name=d) for d in (dimensions or [])]
    metric_names = [
        "sessions", "totalUsers", "newUsers",
        "ecommercePurchases", "purchaseRevenue",
        "sessionConversionRate", "bounceRate",
        "averageSessionDuration", "engagedSessions",
    ]

    resp = ga_client.run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=str(start), end_date=str(end))],
        dimensions=dim_objs,
        metrics=[Metric(name=m) for m in metric_names],
    ))

    rows = []
    for row in resp.rows:
        dims = {d: row.dimension_values[i].value for i, d in enumerate(dimensions or [])}
        vals = {metric_names[i]: row.metric_values[i].value for i in range(len(metric_names))}
        rows.append({**dims, **vals})

    return rows


def pull_ga4_daily(ga_client, property_id: str, start: date, end: date) -> list:
    """Pull daily GA4 data. Returns list of {date, sessions, revenue, ...}."""
    return pull_ga4_period(ga_client, property_id, start, end, dimensions=["date"])


def pull_ga4_by_channel(ga_client, property_id: str, start: date, end: date) -> list:
    """Pull GA4 data grouped by channel. Returns list of {channel, ...}."""
    return pull_ga4_period(
        ga_client, property_id, start, end,
        dimensions=["sessionDefaultChannelGroup"]
    )


def pull_ga4_summary(ga_client, property_id: str, start: date, end: date) -> dict:
    """Pull aggregate GA4 metrics for a period. Returns single dict."""
    rows = pull_ga4_period(ga_client, property_id, start, end)
    if rows:
        return rows[0]
    return {}


# ── Google Search Console ─────────────────────────────────────────────────────

def pull_gsc_period(sc_client, site: str, start: date, end: date,
                    dimensions: list = None) -> list:
    """Pull GSC data for a period. Returns list of row dicts."""
    dims = dimensions or ["date"]
    body = {
        "startDate": str(start),
        "endDate": str(end),
        "dimensions": dims,
        "rowLimit": 25000,
        "type": "web",
    }
    result = sc_client.searchanalytics().query(siteUrl=site, body=body).execute()
    rows = []
    for r in result.get("rows", []):
        row = {
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"] * 100, 2),
            "position": round(r["position"], 1),
        }
        for i, d in enumerate(dims):
            row[d] = r["keys"][i]
        rows.append(row)
    return rows


def pull_gsc_summary(sc_client, site: str, start: date, end: date) -> dict:
    """Pull aggregate GSC metrics."""
    rows = pull_gsc_period(sc_client, site, start, end, dimensions=["date"])
    if not rows:
        return {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}
    total_clicks = sum(r["clicks"] for r in rows)
    total_impr   = sum(r["impressions"] for r in rows)
    avg_ctr      = round(total_clicks / total_impr * 100, 2) if total_impr else 0
    avg_pos      = round(sum(r["position"] for r in rows) / len(rows), 1)
    return {
        "clicks": total_clicks,
        "impressions": total_impr,
        "ctr": avg_ctr,
        "position": avg_pos,
        "days": len(rows),
    }


# ── Google Ads ────────────────────────────────────────────────────────────────

def pull_gads_period(ga_service, customer_id: str, start: date, end: date) -> dict:
    """Pull aggregate Google Ads metrics for a period."""
    query = f"""
        SELECT
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date >= '{start}'
          AND segments.date <= '{end}'
          AND campaign.status != 'REMOVED'
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    rows = list(response)

    spend       = sum(r.metrics.cost_micros / 1_000_000 for r in rows)
    impressions = sum(r.metrics.impressions for r in rows)
    clicks      = sum(r.metrics.clicks for r in rows)
    conversions = sum(r.metrics.conversions for r in rows)
    conv_value  = sum(r.metrics.conversions_value for r in rows)
    roas        = round(conv_value / spend, 2) if spend > 0 else 0

    return {
        "spend":       round(spend, 2),
        "impressions": impressions,
        "clicks":      clicks,
        "conversions": round(conversions, 1),
        "conv_value":  round(conv_value, 2),
        "roas":        roas,
        "cpc":         round(spend / clicks, 2) if clicks else 0,
        "ctr":         round(clicks / impressions * 100, 2) if impressions else 0,
    }


def pull_gads_daily(ga_service, customer_id: str, start: date, end: date) -> list:
    """Pull daily Google Ads metrics."""
    query = f"""
        SELECT
            segments.date,
            metrics.cost_micros,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date >= '{start}'
          AND segments.date <= '{end}'
          AND campaign.status != 'REMOVED'
    """
    response = ga_service.search(customer_id=customer_id, query=query)

    daily = {}
    for r in response:
        d = str(r.segments.date)
        if d not in daily:
            daily[d] = {"date": d, "spend": 0, "clicks": 0, "conversions": 0, "conv_value": 0}
        daily[d]["spend"]       += r.metrics.cost_micros / 1_000_000
        daily[d]["clicks"]      += r.metrics.clicks
        daily[d]["conversions"] += r.metrics.conversions
        daily[d]["conv_value"]  += r.metrics.conversions_value

    return sorted(daily.values(), key=lambda x: x["date"])


# ── Supabase Historical Revenue ──────────────────────────────────────────────

def pull_supabase_revenue(start: date, end: date) -> list:
    """Pull daily revenue from Supabase daily_sales table."""
    url = f"{ENV.get('SUPABASE_URL', '')}/rest/v1/daily_sales"
    headers = {"apikey": ENV.get("SUPABASE_SECRET_API_KEY", "")}
    params = {
        "select": "report_date,channel,revenue,orders",
        "report_date": f"gte.{start}",
        "order": "report_date.asc",
    }
    # Add upper bound filter
    resp = requests.get(
        url, headers=headers,
        params={**params, "report_date": f"gte.{start}", "and": f"(report_date.lte.{end})"},
        timeout=30
    )
    if resp.status_code != 200:
        # Try alternate filter syntax
        resp = requests.get(
            f"{url}?report_date=gte.{start}&report_date=lte.{end}&select=report_date,channel,revenue,orders&order=report_date.asc",
            headers=headers, timeout=30
        )
    if resp.status_code == 200:
        return resp.json()
    log.warning(f"Supabase query failed: {resp.status_code} {resp.text[:200]}")
    return []


def aggregate_supabase(rows: list) -> dict:
    """Aggregate Supabase daily_sales rows."""
    total_rev    = sum(float(r.get("revenue", 0) or 0) for r in rows)
    total_orders = sum(int(r.get("orders", 0) or 0) for r in rows)
    wc_rev       = sum(float(r.get("revenue", 0) or 0) for r in rows if r.get("channel") == "woocommerce")
    wm_rev       = sum(float(r.get("revenue", 0) or 0) for r in rows if r.get("channel") == "walmart")
    days         = len(set(r.get("report_date", "") for r in rows))
    return {
        "total_revenue": round(total_rev, 2),
        "total_orders":  total_orders,
        "wc_revenue":    round(wc_rev, 2),
        "wm_revenue":    round(wm_rev, 2),
        "days":          days,
        "daily_avg":     round(total_rev / days, 2) if days else 0,
    }


# ── Percentage Change Helper ─────────────────────────────────────────────────

def pct_change(before, after) -> str:
    """Return formatted percentage change string."""
    if not before or float(before) == 0:
        return "N/A"
    change = ((float(after) - float(before)) / float(before)) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.1f}%"


def pct_val(before, after) -> float:
    """Return raw percentage change."""
    if not before or float(before) == 0:
        return 0
    return ((float(after) - float(before)) / float(before)) * 100


def color_class(val: float) -> str:
    """Return CSS class based on positive/negative change."""
    if val > 5:
        return "positive"
    elif val < -5:
        return "negative"
    return "neutral"


# ── HTML Report Generator ────────────────────────────────────────────────────

def generate_html_report(data: dict) -> str:
    """Generate the full attribution HTML report."""

    ga4_pre       = data["ga4_pre"]
    ga4_post      = data["ga4_post"]
    ga4_yoy_post  = data.get("ga4_yoy_post", {})
    ga4_channels_pre  = data.get("ga4_channels_pre", [])
    ga4_channels_post = data.get("ga4_channels_post", [])
    gsc_pre       = data["gsc_pre"]
    gsc_post      = data["gsc_post"]
    gsc_yoy_post  = data.get("gsc_yoy_post", {})
    gads_pre      = data["gads_pre"]
    gads_post     = data["gads_post"]
    gads_yoy_post = data.get("gads_yoy_post", {})
    rev_pre       = data["rev_pre"]
    rev_post      = data["rev_post"]
    rev_yoy_post  = data.get("rev_yoy_post", {})
    rev_yoy_pre   = data.get("rev_yoy_pre", {})
    ga4_daily_pre  = data.get("ga4_daily_pre", [])
    ga4_daily_post = data.get("ga4_daily_post", [])
    verdict       = data.get("verdict", {})

    def safe_float(d, key, default=0):
        try:
            return float(d.get(key, default) or default)
        except (ValueError, TypeError):
            return default

    # Channel comparison table rows
    channel_map_pre  = {r.get("sessionDefaultChannelGroup", ""): r for r in ga4_channels_pre}
    channel_map_post = {r.get("sessionDefaultChannelGroup", ""): r for r in ga4_channels_post}
    all_channels     = sorted(set(list(channel_map_pre.keys()) + list(channel_map_post.keys())))

    channel_rows = ""
    for ch in all_channels:
        pre  = channel_map_pre.get(ch, {})
        post = channel_map_post.get(ch, {})
        sess_pre  = safe_float(pre, "sessions")
        sess_post = safe_float(post, "sessions")
        rev_pre_  = safe_float(pre, "purchaseRevenue")
        rev_post_ = safe_float(post, "purchaseRevenue")
        cr_pre    = safe_float(pre, "sessionConversionRate") * 100
        cr_post   = safe_float(post, "sessionConversionRate") * 100

        sess_chg = pct_val(sess_pre, sess_post)
        rev_chg  = pct_val(rev_pre_, rev_post_)
        cr_chg   = cr_post - cr_pre

        channel_rows += f"""
        <tr>
            <td><b>{html_mod.escape(ch or 'Unknown')}</b></td>
            <td>{sess_pre:,.0f}</td>
            <td>{sess_post:,.0f}</td>
            <td class="{color_class(sess_chg)}">{pct_change(sess_pre, sess_post)}</td>
            <td>${rev_pre_:,.0f}</td>
            <td>${rev_post_:,.0f}</td>
            <td class="{color_class(rev_chg)}">{pct_change(rev_pre_, rev_post_)}</td>
            <td>{cr_pre:.2f}%</td>
            <td>{cr_post:.2f}%</td>
            <td class="{color_class(cr_chg * 10)}">{cr_chg:+.2f}pp</td>
        </tr>"""

    # Revenue daily chart data (for inline JS sparkline)
    daily_rev_pre  = []
    daily_rev_post = []
    for r in ga4_daily_pre:
        d = r.get("date", "")
        if len(d) == 8:
            d = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        daily_rev_pre.append({"date": d, "revenue": safe_float(r, "purchaseRevenue")})
    for r in ga4_daily_post:
        d = r.get("date", "")
        if len(d) == 8:
            d = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        daily_rev_post.append({"date": d, "revenue": safe_float(r, "purchaseRevenue")})

    daily_data_json = json.dumps(daily_rev_pre + daily_rev_post)

    # Verdict section
    verdict_signals = verdict.get("signals", [])
    verdict_text    = verdict.get("conclusion", "")
    signals_html    = ""
    for s in verdict_signals:
        icon = "✅" if s.get("supports") == "theme" else ("📅" if s.get("supports") == "seasonality" else "⚙️")
        signals_html += f'<div class="signal"><span class="signal-icon">{icon}</span> {html_mod.escape(s.get("text", ""))}</div>\n'

    # Overall metrics
    sessions_pre  = safe_float(ga4_pre, "sessions")
    sessions_post = safe_float(ga4_post, "sessions")
    cr_pre_val    = safe_float(ga4_pre, "sessionConversionRate") * 100
    cr_post_val   = safe_float(ga4_post, "sessionConversionRate") * 100
    bounce_pre    = safe_float(ga4_pre, "bounceRate") * 100
    bounce_post   = safe_float(ga4_post, "bounceRate") * 100
    rev_total_pre = rev_pre.get("total_revenue", 0)
    rev_total_post = rev_post.get("total_revenue", 0)
    rev_total_yoy = rev_yoy_post.get("total_revenue", 0)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Theme Attribution Analysis — Nature's Seed</title>
<style>
  :root {{
    --green: #16a34a; --red: #dc2626; --blue: #2563eb; --amber: #d97706;
    --bg: #f8fafc; --card: #fff; --border: #e2e8f0; --text: #1e293b;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
         background: var(--bg); color: var(--text); padding: 24px; max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 1.8rem; margin-bottom: 4px; }}
  h2 {{ font-size: 1.3rem; margin: 28px 0 12px; border-bottom: 2px solid var(--border); padding-bottom: 6px; }}
  h3 {{ font-size: 1.05rem; margin: 16px 0 8px; }}
  .subtitle {{ color: #64748b; margin-bottom: 20px; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
           padding: 16px; margin-bottom: 16px; }}
  .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 16px 0; }}
  .metric {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
             padding: 14px; text-align: center; }}
  .metric .label {{ font-size: 0.8rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }}
  .metric .value {{ font-size: 1.6rem; font-weight: 700; margin: 4px 0; }}
  .metric .change {{ font-size: 0.9rem; font-weight: 600; }}
  .positive {{ color: var(--green); }}
  .negative {{ color: var(--red); }}
  .neutral {{ color: #64748b; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th {{ background: #f1f5f9; padding: 8px 10px; text-align: left; font-weight: 600; border-bottom: 2px solid var(--border); }}
  td {{ padding: 8px 10px; border-bottom: 1px solid var(--border); }}
  tr:hover td {{ background: #f8fafc; }}
  .verdict-box {{ background: #eff6ff; border: 2px solid var(--blue); border-radius: 8px;
                  padding: 20px; margin: 20px 0; }}
  .verdict-box h2 {{ border: none; margin: 0 0 12px; color: var(--blue); }}
  .verdict-text {{ font-size: 1.1rem; line-height: 1.6; margin: 12px 0; }}
  .signal {{ padding: 6px 0; font-size: 0.9rem; }}
  .signal-icon {{ margin-right: 6px; }}
  .period-label {{ display: inline-block; background: #e2e8f0; border-radius: 4px;
                   padding: 2px 8px; font-size: 0.75rem; font-weight: 600; margin-right: 6px; }}
  .period-pre {{ background: #fee2e2; color: var(--red); }}
  .period-post {{ background: #dcfce7; color: var(--green); }}
  .period-yoy {{ background: #fef3c7; color: var(--amber); }}
  .chart-container {{ position: relative; height: 200px; margin: 16px 0; }}
  canvas {{ width: 100% !important; height: 100% !important; }}
  .footnote {{ font-size: 0.8rem; color: #94a3b8; margin-top: 24px; border-top: 1px solid var(--border); padding-top: 12px; }}
</style>
</head>
<body>

<h1>Theme Attribution Analysis</h1>
<p class="subtitle">
  New theme deployed <b>Friday, Feb 27, 2026</b> &mdash;
  comparing <span class="period-label period-pre">PRE</span> Feb 14–27 vs
  <span class="period-label period-post">POST</span> Feb 28 – Mar 12 vs
  <span class="period-label period-yoy">YoY 2025</span>
</p>

<!-- ════════ VERDICT ════════ -->
<div class="verdict-box">
  <h2>Attribution Verdict</h2>
  <div class="verdict-text">{html_mod.escape(verdict_text)}</div>
  <h3>Evidence Signals</h3>
  {signals_html}
</div>

<!-- ════════ HEADLINE METRICS ════════ -->
<h2>Headline Metrics (Pre → Post)</h2>
<div class="metrics-grid">
  <div class="metric">
    <div class="label">Total Revenue</div>
    <div class="value">${rev_total_post:,.0f}</div>
    <div class="change {color_class(pct_val(rev_total_pre, rev_total_post))}">{pct_change(rev_total_pre, rev_total_post)} vs pre</div>
    <div class="change {color_class(pct_val(rev_total_yoy, rev_total_post))}" style="font-size:0.8rem">{pct_change(rev_total_yoy, rev_total_post)} vs YoY</div>
  </div>
  <div class="metric">
    <div class="label">Sessions</div>
    <div class="value">{sessions_post:,.0f}</div>
    <div class="change {color_class(pct_val(sessions_pre, sessions_post))}">{pct_change(sessions_pre, sessions_post)} vs pre</div>
  </div>
  <div class="metric">
    <div class="label">Conversion Rate</div>
    <div class="value">{cr_post_val:.2f}%</div>
    <div class="change {color_class((cr_post_val - cr_pre_val) * 10)}">{cr_post_val - cr_pre_val:+.2f}pp vs pre</div>
  </div>
  <div class="metric">
    <div class="label">Bounce Rate</div>
    <div class="value">{bounce_post:.1f}%</div>
    <div class="change {color_class((bounce_pre - bounce_post) * 10)}">{bounce_post - bounce_pre:+.1f}pp vs pre</div>
  </div>
  <div class="metric">
    <div class="label">Daily Avg Revenue</div>
    <div class="value">${rev_post.get('daily_avg', 0):,.0f}</div>
    <div class="change {color_class(pct_val(rev_pre.get('daily_avg', 0), rev_post.get('daily_avg', 0)))}">{pct_change(rev_pre.get('daily_avg', 0), rev_post.get('daily_avg', 0))} vs pre</div>
  </div>
  <div class="metric">
    <div class="label">Orders (Total)</div>
    <div class="value">{rev_post.get('total_orders', 0):,}</div>
    <div class="change {color_class(pct_val(rev_pre.get('total_orders', 0), rev_post.get('total_orders', 0)))}">{pct_change(rev_pre.get('total_orders', 0), rev_post.get('total_orders', 0))} vs pre</div>
  </div>
</div>

<!-- ════════ GA4 BY CHANNEL ════════ -->
<h2>GA4 — Traffic &amp; Revenue by Channel</h2>
<div class="card">
<p style="font-size:0.85rem; color:#64748b; margin-bottom:10px;">
  This is the <b>key isolation test</b> — if Organic and Direct channels improved more than Paid,
  the theme is likely driving it (not just more ad spend).
</p>
<table>
  <tr>
    <th>Channel</th>
    <th colspan="3">Sessions</th>
    <th colspan="3">Revenue</th>
    <th colspan="3">Conv. Rate</th>
  </tr>
  <tr>
    <th></th>
    <th>Pre</th><th>Post</th><th>Δ</th>
    <th>Pre</th><th>Post</th><th>Δ</th>
    <th>Pre</th><th>Post</th><th>Δ</th>
  </tr>
  {channel_rows}
</table>
</div>

<!-- ════════ GOOGLE SEARCH CONSOLE ════════ -->
<h2>Google Search Console — Organic Performance</h2>
<div class="card">
<p style="font-size:0.85rem; color:#64748b; margin-bottom:10px;">
  GSC data lags 2-3 days. Organic improvements = theme/content effect. Flat = seasonality.
</p>
<div class="metrics-grid">
  <div class="metric">
    <div class="label">Organic Clicks</div>
    <div class="value">{gsc_post.get('clicks', 0):,}</div>
    <div class="change {color_class(pct_val(gsc_pre.get('clicks', 0), gsc_post.get('clicks', 0)))}">{pct_change(gsc_pre.get('clicks', 0), gsc_post.get('clicks', 0))} vs pre</div>
    <div class="change {color_class(pct_val(gsc_yoy_post.get('clicks', 0), gsc_post.get('clicks', 0)))}" style="font-size:0.8rem">{pct_change(gsc_yoy_post.get('clicks', 0), gsc_post.get('clicks', 0))} vs YoY</div>
  </div>
  <div class="metric">
    <div class="label">Impressions</div>
    <div class="value">{gsc_post.get('impressions', 0):,}</div>
    <div class="change {color_class(pct_val(gsc_pre.get('impressions', 0), gsc_post.get('impressions', 0)))}">{pct_change(gsc_pre.get('impressions', 0), gsc_post.get('impressions', 0))} vs pre</div>
  </div>
  <div class="metric">
    <div class="label">CTR</div>
    <div class="value">{gsc_post.get('ctr', 0):.1f}%</div>
    <div class="change">{gsc_post.get('ctr', 0) - gsc_pre.get('ctr', 0):+.1f}pp vs pre</div>
  </div>
  <div class="metric">
    <div class="label">Avg Position</div>
    <div class="value">{gsc_post.get('position', 0):.1f}</div>
    <div class="change">{gsc_post.get('position', 0) - gsc_pre.get('position', 0):+.1f} vs pre</div>
  </div>
</div>
</div>

<!-- ════════ GOOGLE ADS ════════ -->
<h2>Google Ads — Paid Performance</h2>
<div class="card">
<p style="font-size:0.85rem; color:#64748b; margin-bottom:10px;">
  If paid conversion rate improved at same spend → theme is converting better.
  If spend increased → can't attribute to theme alone.
</p>
<div class="metrics-grid">
  <div class="metric">
    <div class="label">Ad Spend</div>
    <div class="value">${gads_post.get('spend', 0):,.0f}</div>
    <div class="change {color_class(pct_val(gads_pre.get('spend', 0), gads_post.get('spend', 0)))}">{pct_change(gads_pre.get('spend', 0), gads_post.get('spend', 0))} vs pre</div>
  </div>
  <div class="metric">
    <div class="label">ROAS</div>
    <div class="value">{gads_post.get('roas', 0):.1f}x</div>
    <div class="change {color_class(pct_val(gads_pre.get('roas', 0), gads_post.get('roas', 0)))}">{pct_change(gads_pre.get('roas', 0), gads_post.get('roas', 0))} vs pre</div>
  </div>
  <div class="metric">
    <div class="label">Conversions</div>
    <div class="value">{gads_post.get('conversions', 0):,.0f}</div>
    <div class="change {color_class(pct_val(gads_pre.get('conversions', 0), gads_post.get('conversions', 0)))}">{pct_change(gads_pre.get('conversions', 0), gads_post.get('conversions', 0))} vs pre</div>
  </div>
  <div class="metric">
    <div class="label">Conv. Value</div>
    <div class="value">${gads_post.get('conv_value', 0):,.0f}</div>
    <div class="change {color_class(pct_val(gads_pre.get('conv_value', 0), gads_post.get('conv_value', 0)))}">{pct_change(gads_pre.get('conv_value', 0), gads_post.get('conv_value', 0))} vs pre</div>
  </div>
  <div class="metric">
    <div class="label">Clicks</div>
    <div class="value">{gads_post.get('clicks', 0):,}</div>
    <div class="change {color_class(pct_val(gads_pre.get('clicks', 0), gads_post.get('clicks', 0)))}">{pct_change(gads_pre.get('clicks', 0), gads_post.get('clicks', 0))} vs pre</div>
  </div>
  <div class="metric">
    <div class="label">CPC</div>
    <div class="value">${gads_post.get('cpc', 0):.2f}</div>
    <div class="change {color_class(pct_val(gads_pre.get('cpc', 0), gads_post.get('cpc', 0)) * -1)}">{pct_change(gads_pre.get('cpc', 0), gads_post.get('cpc', 0))} vs pre</div>
  </div>
</div>
</div>

<!-- ════════ REVENUE YoY ════════ -->
<h2>Revenue — Year-over-Year Seasonality Check</h2>
<div class="card">
<p style="font-size:0.85rem; color:#64748b; margin-bottom:10px;">
  Compare 2026 vs 2025 same calendar period. If 2025 showed similar growth → seasonality.
  If 2026 outpaces → theme + strategy changes are additive.
</p>
<table>
  <tr>
    <th>Period</th>
    <th>Revenue</th>
    <th>Orders</th>
    <th>Daily Avg</th>
    <th>WC Rev</th>
    <th>Walmart Rev</th>
  </tr>
  <tr>
    <td><span class="period-label period-pre">2026 PRE</span> Feb 14–27</td>
    <td>${rev_pre.get('total_revenue', 0):,.0f}</td>
    <td>{rev_pre.get('total_orders', 0)}</td>
    <td>${rev_pre.get('daily_avg', 0):,.0f}</td>
    <td>${rev_pre.get('wc_revenue', 0):,.0f}</td>
    <td>${rev_pre.get('wm_revenue', 0):,.0f}</td>
  </tr>
  <tr>
    <td><span class="period-label period-post">2026 POST</span> Feb 28 – Mar 12</td>
    <td><b>${rev_post.get('total_revenue', 0):,.0f}</b></td>
    <td><b>{rev_post.get('total_orders', 0)}</b></td>
    <td><b>${rev_post.get('daily_avg', 0):,.0f}</b></td>
    <td><b>${rev_post.get('wc_revenue', 0):,.0f}</b></td>
    <td><b>${rev_post.get('wm_revenue', 0):,.0f}</b></td>
  </tr>
  <tr>
    <td><span class="period-label period-yoy">2025 PRE</span> Feb 14–27</td>
    <td>${rev_yoy_pre.get('total_revenue', 0):,.0f}</td>
    <td>{rev_yoy_pre.get('total_orders', 0)}</td>
    <td>${rev_yoy_pre.get('daily_avg', 0):,.0f}</td>
    <td>${rev_yoy_pre.get('wc_revenue', 0):,.0f}</td>
    <td>${rev_yoy_pre.get('wm_revenue', 0):,.0f}</td>
  </tr>
  <tr>
    <td><span class="period-label period-yoy">2025 POST</span> Feb 28 – Mar 12</td>
    <td>${rev_yoy_post.get('total_revenue', 0):,.0f}</td>
    <td>{rev_yoy_post.get('total_orders', 0)}</td>
    <td>${rev_yoy_post.get('daily_avg', 0):,.0f}</td>
    <td>${rev_yoy_post.get('wc_revenue', 0):,.0f}</td>
    <td>${rev_yoy_post.get('wm_revenue', 0):,.0f}</td>
  </tr>
  <tr style="background:#f8fafc; font-weight:600;">
    <td>2026 Post vs 2025 Post (YoY)</td>
    <td class="{color_class(pct_val(rev_yoy_post.get('total_revenue', 0), rev_post.get('total_revenue', 0)))}">{pct_change(rev_yoy_post.get('total_revenue', 0), rev_post.get('total_revenue', 0))}</td>
    <td class="{color_class(pct_val(rev_yoy_post.get('total_orders', 0), rev_post.get('total_orders', 0)))}">{pct_change(rev_yoy_post.get('total_orders', 0), rev_post.get('total_orders', 0))}</td>
    <td colspan="3"></td>
  </tr>
  <tr style="background:#f8fafc; font-weight:600;">
    <td>2025 Pre → Post (seasonal lift last year)</td>
    <td>{pct_change(rev_yoy_pre.get('total_revenue', 0), rev_yoy_post.get('total_revenue', 0))}</td>
    <td>{pct_change(rev_yoy_pre.get('total_orders', 0), rev_yoy_post.get('total_orders', 0))}</td>
    <td colspan="3"></td>
  </tr>
  <tr style="background:#f8fafc; font-weight:600;">
    <td>2026 Pre → Post (this year's lift)</td>
    <td class="{color_class(pct_val(rev_pre.get('total_revenue', 0), rev_post.get('total_revenue', 0)))}">{pct_change(rev_pre.get('total_revenue', 0), rev_post.get('total_revenue', 0))}</td>
    <td class="{color_class(pct_val(rev_pre.get('total_orders', 0), rev_post.get('total_orders', 0)))}">{pct_change(rev_pre.get('total_orders', 0), rev_post.get('total_orders', 0))}</td>
    <td colspan="3"></td>
  </tr>
</table>
</div>

<div class="footnote">
  Generated {date.today().isoformat()} by theme_attribution.py &mdash;
  Data sources: GA4, Google Search Console, Google Ads, Supabase (daily_sales)
</div>

</body>
</html>"""


# ── Attribution Logic ─────────────────────────────────────────────────────────

def compute_verdict(data: dict) -> dict:
    """
    Analyze all data points and produce an attribution verdict.
    Returns: {conclusion: str, signals: [{text, supports}]}
    """
    signals = []

    ga4_pre  = data["ga4_pre"]
    ga4_post = data["ga4_post"]
    gsc_pre  = data["gsc_pre"]
    gsc_post = data["gsc_post"]
    gads_pre = data["gads_pre"]
    gads_post = data["gads_post"]
    rev_pre  = data["rev_pre"]
    rev_post = data["rev_post"]
    rev_yoy_pre  = data.get("rev_yoy_pre", {})
    rev_yoy_post = data.get("rev_yoy_post", {})
    ga4_channels_pre  = data.get("ga4_channels_pre", [])
    ga4_channels_post = data.get("ga4_channels_post", [])

    def sf(d, k, default=0):
        try: return float(d.get(k, default) or default)
        except: return default

    # 1. Revenue growth: this year vs last year (same period)
    rev_lift_2026 = pct_val(rev_pre.get("total_revenue", 0), rev_post.get("total_revenue", 0))
    rev_lift_2025 = pct_val(rev_yoy_pre.get("total_revenue", 0), rev_yoy_post.get("total_revenue", 0))

    if rev_lift_2025 > 0:
        excess_lift = rev_lift_2026 - rev_lift_2025
        if excess_lift > 15:
            signals.append({"text": f"2026 revenue lift ({rev_lift_2026:+.0f}%) exceeds 2025 seasonal lift ({rev_lift_2025:+.0f}%) by {excess_lift:.0f}pp — something beyond seasonality is driving growth.", "supports": "theme"})
        elif excess_lift > 0:
            signals.append({"text": f"2026 lift ({rev_lift_2026:+.0f}%) slightly above 2025 ({rev_lift_2025:+.0f}%) — mostly seasonal with marginal improvement.", "supports": "mixed"})
        else:
            signals.append({"text": f"2026 lift ({rev_lift_2026:+.0f}%) is at or below 2025 seasonal pattern ({rev_lift_2025:+.0f}%) — growth appears seasonal.", "supports": "seasonality"})

    # 2. Conversion rate change (GA4)
    cr_pre  = sf(ga4_pre, "sessionConversionRate") * 100
    cr_post = sf(ga4_post, "sessionConversionRate") * 100
    cr_delta = cr_post - cr_pre
    if cr_delta > 0.3:
        signals.append({"text": f"Conversion rate improved {cr_delta:+.2f}pp ({cr_pre:.2f}% → {cr_post:.2f}%). Better site experience converts more visitors — likely theme effect.", "supports": "theme"})
    elif cr_delta < -0.2:
        signals.append({"text": f"Conversion rate dropped {cr_delta:+.2f}pp. If traffic grew but CR fell, more top-of-funnel visitors (seasonal).", "supports": "seasonality"})
    else:
        signals.append({"text": f"Conversion rate flat ({cr_delta:+.2f}pp). Growth likely from more traffic, not better conversion.", "supports": "mixed"})

    # 3. Bounce rate change
    br_pre  = sf(ga4_pre, "bounceRate") * 100
    br_post = sf(ga4_post, "bounceRate") * 100
    br_delta = br_post - br_pre
    if br_delta < -3:
        signals.append({"text": f"Bounce rate dropped {br_delta:+.1f}pp ({br_pre:.1f}% → {br_post:.1f}%). Users are staying longer — theme UX improvement.", "supports": "theme"})
    elif br_delta > 3:
        signals.append({"text": f"Bounce rate increased {br_delta:+.1f}pp — possible theme issue or more casual traffic.", "supports": "strategy"})

    # 4. Organic search (GSC) — seasonality indicator
    gsc_click_chg = pct_val(gsc_pre.get("clicks", 0), gsc_post.get("clicks", 0))
    gsc_impr_chg  = pct_val(gsc_pre.get("impressions", 0), gsc_post.get("impressions", 0))
    if gsc_impr_chg > 20:
        signals.append({"text": f"Organic impressions up {gsc_impr_chg:+.0f}% — search demand is rising (seasonal planting interest).", "supports": "seasonality"})
    if gsc_click_chg > gsc_impr_chg + 10:
        signals.append({"text": f"Organic clicks ({gsc_click_chg:+.0f}%) growing faster than impressions ({gsc_impr_chg:+.0f}%) — improved CTR, likely better snippets/site.", "supports": "theme"})

    # 5. Paid ads performance
    spend_chg = pct_val(gads_pre.get("spend", 0), gads_post.get("spend", 0))
    roas_chg  = pct_val(gads_pre.get("roas", 0), gads_post.get("roas", 0))
    if abs(spend_chg) < 10 and roas_chg > 15:
        signals.append({"text": f"Ad spend roughly flat ({spend_chg:+.0f}%) but ROAS improved {roas_chg:+.0f}% — same traffic converting better (theme).", "supports": "theme"})
    elif spend_chg > 15:
        signals.append({"text": f"Ad spend increased {spend_chg:+.0f}% — part of revenue growth is from more ad investment (strategy).", "supports": "strategy"})

    # 6. Channel-level organic vs paid
    ch_pre  = {r.get("sessionDefaultChannelGroup", ""): r for r in ga4_channels_pre}
    ch_post = {r.get("sessionDefaultChannelGroup", ""): r for r in ga4_channels_post}

    org_rev_pre  = sf(ch_pre.get("Organic Search", {}), "purchaseRevenue")
    org_rev_post = sf(ch_post.get("Organic Search", {}), "purchaseRevenue")
    dir_rev_pre  = sf(ch_pre.get("Direct", {}), "purchaseRevenue")
    dir_rev_post = sf(ch_post.get("Direct", {}), "purchaseRevenue")
    paid_rev_pre = sf(ch_pre.get("Paid Search", {}), "purchaseRevenue")
    paid_rev_post = sf(ch_post.get("Paid Search", {}), "purchaseRevenue")

    org_chg  = pct_val(org_rev_pre, org_rev_post)
    dir_chg  = pct_val(dir_rev_pre, dir_rev_post)
    paid_chg = pct_val(paid_rev_pre, paid_rev_post)

    if org_chg > paid_chg + 10:
        signals.append({"text": f"Organic revenue ({org_chg:+.0f}%) outpacing Paid ({paid_chg:+.0f}%) — organic channel benefiting more, suggests theme/content effect.", "supports": "theme"})
    if dir_chg > 20:
        signals.append({"text": f"Direct traffic revenue up {dir_chg:+.0f}% — returning customers engaging more (brand + theme).", "supports": "theme"})

    # Build conclusion
    theme_count = sum(1 for s in signals if s["supports"] == "theme")
    season_count = sum(1 for s in signals if s["supports"] == "seasonality")
    strategy_count = sum(1 for s in signals if s["supports"] == "strategy")

    if theme_count >= 3 and theme_count > season_count:
        conclusion = (
            f"The evidence strongly suggests the new theme is a significant driver of the sales increase. "
            f"{theme_count} of {len(signals)} signals point to improved site experience (better conversion rate, "
            f"lower bounce rate, organic outperforming paid). Seasonality is a contributing factor but the theme "
            f"appears to be adding lift beyond what seasonal patterns alone would explain."
        )
    elif season_count >= theme_count and season_count >= 2:
        conclusion = (
            f"The sales increase appears to be primarily seasonal. {season_count} of {len(signals)} signals "
            f"align with typical late-Feb/March planting season demand patterns. The theme may be contributing "
            f"marginally but the dominant driver is market-wide search demand growth."
        )
    else:
        conclusion = (
            f"The sales increase is driven by a mix of factors: seasonality ({season_count} signals), "
            f"theme improvements ({theme_count} signals), and strategy changes ({strategy_count} signals). "
            f"No single factor dominates — the growth is likely compound: seasonal demand + better site experience "
            f"+ optimized ad strategy all contributing."
        )

    return {"conclusion": conclusion, "signals": signals}


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    log.info("=== Theme Attribution Analysis ===")
    creds = _google_creds()

    # Initialize clients
    log.info("Initializing API clients...")
    ga_client = BetaAnalyticsDataClient(credentials=creds)
    sc_client = build("searchconsole", "v1", credentials=creds)
    GA_PROPERTY = ENV.get("GOOGLE_ANALYTICS_PROPERTY_ID", "294622924")
    GSC_SITE    = "sc-domain:naturesseed.com"

    gads_config = {
        "developer_token": ENV["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id":       ENV["GOOGLE_ADS_CLIENT_ID"],
        "client_secret":   ENV["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token":   ENV["GOOGLE_ADS_REFRESH_TOKEN"],
        "use_proto_plus":  True,
    }
    login_cid = ENV.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
    if login_cid:
        gads_config["login_customer_id"] = login_cid
    gads_customer_id = ENV["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")

    gads_client  = GoogleAdsClient.load_from_dict(gads_config)
    gads_service = gads_client.get_service("GoogleAdsService")

    data = {}

    # ── GA4 ───────────────────────────────────────────
    log.info("Pulling GA4 data...")

    log.info("  GA4 summary: pre period")
    data["ga4_pre"] = pull_ga4_summary(ga_client, GA_PROPERTY, PRE_START, PRE_END)

    log.info("  GA4 summary: post period")
    data["ga4_post"] = pull_ga4_summary(ga_client, GA_PROPERTY, POST_START, POST_END)

    log.info("  GA4 summary: YoY post")
    try:
        data["ga4_yoy_post"] = pull_ga4_summary(ga_client, GA_PROPERTY, YOY_POST_START, YOY_POST_END)
    except Exception as e:
        log.warning(f"  GA4 YoY failed (data may not exist): {e}")
        data["ga4_yoy_post"] = {}

    log.info("  GA4 by channel: pre")
    data["ga4_channels_pre"] = pull_ga4_by_channel(ga_client, GA_PROPERTY, PRE_START, PRE_END)

    log.info("  GA4 by channel: post")
    data["ga4_channels_post"] = pull_ga4_by_channel(ga_client, GA_PROPERTY, POST_START, POST_END)

    log.info("  GA4 daily: pre + post")
    data["ga4_daily_pre"]  = pull_ga4_daily(ga_client, GA_PROPERTY, PRE_START, PRE_END)
    data["ga4_daily_post"] = pull_ga4_daily(ga_client, GA_PROPERTY, POST_START, POST_END)

    # ── GSC ───────────────────────────────────────────
    # GSC data lags 2-3 days — adjust end date
    gsc_end = min(POST_END, date.today() - timedelta(days=3))
    log.info(f"Pulling Search Console data (through {gsc_end})...")

    log.info("  GSC: pre period")
    data["gsc_pre"] = pull_gsc_summary(sc_client, GSC_SITE, PRE_START, PRE_END)

    log.info("  GSC: post period")
    data["gsc_post"] = pull_gsc_summary(sc_client, GSC_SITE, POST_START, gsc_end)

    log.info("  GSC: YoY post")
    try:
        data["gsc_yoy_post"] = pull_gsc_summary(sc_client, GSC_SITE, YOY_POST_START, YOY_POST_END)
    except Exception as e:
        log.warning(f"  GSC YoY failed: {e}")
        data["gsc_yoy_post"] = {}

    # ── Google Ads ────────────────────────────────────
    log.info("Pulling Google Ads data...")

    log.info("  Ads: pre period")
    data["gads_pre"] = pull_gads_period(gads_service, gads_customer_id, PRE_START, PRE_END)

    log.info("  Ads: post period")
    data["gads_post"] = pull_gads_period(gads_service, gads_customer_id, POST_START, POST_END)

    log.info("  Ads: YoY post")
    try:
        data["gads_yoy_post"] = pull_gads_period(gads_service, gads_customer_id, YOY_POST_START, YOY_POST_END)
    except Exception as e:
        log.warning(f"  Ads YoY failed: {e}")
        data["gads_yoy_post"] = {}

    # ── Supabase Revenue ──────────────────────────────
    log.info("Pulling Supabase historical revenue...")

    log.info("  Revenue: 2026 pre")
    data["rev_pre"] = aggregate_supabase(pull_supabase_revenue(PRE_START, PRE_END))

    log.info("  Revenue: 2026 post")
    data["rev_post"] = aggregate_supabase(pull_supabase_revenue(POST_START, POST_END))

    log.info("  Revenue: 2025 YoY pre")
    data["rev_yoy_pre"] = aggregate_supabase(pull_supabase_revenue(YOY_PRE_START, YOY_PRE_END))

    log.info("  Revenue: 2025 YoY post")
    data["rev_yoy_post"] = aggregate_supabase(pull_supabase_revenue(YOY_POST_START, YOY_POST_END))

    # ── Verdict ───────────────────────────────────────
    log.info("Computing attribution verdict...")
    data["verdict"] = compute_verdict(data)

    # ── Generate Report ───────────────────────────────
    log.info("Generating HTML report...")
    html = generate_html_report(data)

    out_path = ROOT / "reports" / "theme_attribution_report.html"
    out_path.write_text(html)
    log.info(f"Report written to: {out_path}")

    # Also dump raw data as JSON for future analysis
    json_path = ROOT / "reports" / "theme_attribution_data.json"

    def _serialize(obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return str(obj)

    json_path.write_text(json.dumps(data, indent=2, default=_serialize))
    log.info(f"Raw data written to: {json_path}")

    # Print summary to console
    v = data["verdict"]
    print("\n" + "=" * 60)
    print("  ATTRIBUTION VERDICT")
    print("=" * 60)
    print(f"\n{v['conclusion']}\n")
    for s in v["signals"]:
        icon = {"theme": "🎨", "seasonality": "📅", "strategy": "⚙️", "mixed": "🔀"}.get(s["supports"], "•")
        print(f"  {icon} {s['text']}")
    print(f"\n  Report: {out_path}")

    return data


if __name__ == "__main__":
    run()
