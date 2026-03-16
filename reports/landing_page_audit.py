#!/usr/bin/env python3
"""
Landing Page Audit for Google Ads — Nature's Seed
===================================================
Pulls keyword-level Quality Score breakdowns + landing page URLs + GA4 page
performance to identify exactly what's causing impression share loss to rank.

Quality Score components:
  1. Landing Page Experience (BELOW/AVERAGE/ABOVE AVERAGE)
  2. Ad Relevance (BELOW/AVERAGE/ABOVE AVERAGE)
  3. Expected CTR (BELOW/AVERAGE/ABOVE AVERAGE)

Outputs:
  - reports/landing_page_audit.json — Raw data
  - reports/landing_page_audit.html — Interactive report

Usage:
    python3 reports/landing_page_audit.py
"""

import json
import logging
from datetime import date
from pathlib import Path
from collections import defaultdict

from google.ads.googleads.client import GoogleAdsClient
from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("lp_audit")

ROOT = Path(__file__).resolve().parents[1]

POST_START = date(2026, 2, 28)
POST_END   = date(2026, 3, 12)
GA4_PROPERTY = "294622924"


def _load_env() -> dict:
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip().strip("'\"")
    return env

ENV = _load_env()


def _gads_client():
    customer_id = ENV["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
    login_id = ENV.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
    config = {
        "developer_token": ENV["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": ENV["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": ENV["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": ENV["GOOGLE_ADS_REFRESH_TOKEN"],
        "use_proto_plus": True,
    }
    if login_id:
        config["login_customer_id"] = login_id
    return GoogleAdsClient.load_from_dict(config), customer_id


def _google_creds():
    return Credentials(
        token=None,
        refresh_token=ENV["GOOGLE_ADS_REFRESH_TOKEN"],
        client_id=ENV["GOOGLE_ADS_CLIENT_ID"],
        client_secret=ENV["GOOGLE_ADS_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )


# ── 1. Keyword Quality Score Breakdown ───────────────────────────────────────

def pull_keyword_quality_scores(service, customer_id: str) -> list:
    """Pull keyword-level quality score components for enabled keywords."""
    query = """
        SELECT
            campaign.id,
            campaign.name,
            ad_group.id,
            ad_group.name,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.quality_info.quality_score,
            ad_group_criterion.quality_info.creative_quality_score,
            ad_group_criterion.quality_info.search_predicted_ctr,
            ad_group_criterion.quality_info.post_click_quality_score,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM keyword_view
        WHERE campaign.status = 'ENABLED'
          AND ad_group.status = 'ENABLED'
          AND ad_group_criterion.status = 'ENABLED'
          AND metrics.impressions > 0
          AND segments.date DURING LAST_30_DAYS
    """
    response = service.search(customer_id=customer_id, query=query)

    keywords = {}
    for row in response:
        kw_text = row.ad_group_criterion.keyword.text
        key = f"{row.campaign.id}_{row.ad_group.id}_{kw_text}"

        if key not in keywords:
            qi = row.ad_group_criterion.quality_info
            keywords[key] = {
                "campaign_id": str(row.campaign.id),
                "campaign": row.campaign.name,
                "ad_group_id": str(row.ad_group.id),
                "ad_group": row.ad_group.name,
                "keyword": kw_text,
                "match_type": str(row.ad_group_criterion.keyword.match_type).replace("KeywordMatchType.", ""),
                "quality_score": qi.quality_score if qi.quality_score else 0,
                "ad_relevance": str(qi.creative_quality_score).replace("QualityScoreBucket.", ""),
                "expected_ctr": str(qi.search_predicted_ctr).replace("QualityScoreBucket.", ""),
                "landing_page_exp": str(qi.post_click_quality_score).replace("QualityScoreBucket.", ""),
                "impressions": 0, "clicks": 0, "spend": 0,
                "conversions": 0, "conv_value": 0,
            }
        kw = keywords[key]
        kw["impressions"] += row.metrics.impressions
        kw["clicks"]      += row.metrics.clicks
        kw["spend"]       += row.metrics.cost_micros / 1_000_000
        kw["conversions"] += row.metrics.conversions
        kw["conv_value"]  += row.metrics.conversions_value

    result = []
    for kw in keywords.values():
        kw["spend"]      = round(kw["spend"], 2)
        kw["conversions"] = round(kw["conversions"], 1)
        kw["conv_value"] = round(kw["conv_value"], 2)
        kw["cpc"]        = round(kw["spend"] / kw["clicks"], 2) if kw["clicks"] else 0
        kw["ctr"]        = round(kw["clicks"] / kw["impressions"] * 100, 2) if kw["impressions"] else 0
        kw["roas"]       = round(kw["conv_value"] / kw["spend"], 2) if kw["spend"] > 0 else 0
        result.append(kw)

    return sorted(result, key=lambda x: x["spend"], reverse=True)


# ── 2. Ad Group Landing Page URLs ────────────────────────────────────────────

def pull_ad_landing_pages(service, customer_id: str) -> dict:
    """Pull final URLs from expanded text ads and responsive search ads."""
    query = """
        SELECT
            campaign.id,
            campaign.name,
            ad_group.id,
            ad_group.name,
            ad_group_ad.ad.final_urls,
            ad_group_ad.ad.type,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value,
            metrics.cost_micros
        FROM ad_group_ad
        WHERE campaign.status = 'ENABLED'
          AND ad_group.status = 'ENABLED'
          AND ad_group_ad.status = 'ENABLED'
          AND metrics.impressions > 0
          AND segments.date DURING LAST_30_DAYS
    """
    response = service.search(customer_id=customer_id, query=query)

    ads = {}
    for row in response:
        urls = list(row.ad_group_ad.ad.final_urls) if row.ad_group_ad.ad.final_urls else []
        url = urls[0] if urls else "(no URL)"
        key = f"{row.ad_group.id}_{url}"

        if key not in ads:
            ads[key] = {
                "campaign_id": str(row.campaign.id),
                "campaign": row.campaign.name,
                "ad_group_id": str(row.ad_group.id),
                "ad_group": row.ad_group.name,
                "landing_page": url,
                "ad_type": str(row.ad_group_ad.ad.type).replace("AdType.", ""),
                "impressions": 0, "clicks": 0, "spend": 0,
                "conversions": 0, "conv_value": 0,
            }
        a = ads[key]
        a["impressions"] += row.metrics.impressions
        a["clicks"]      += row.metrics.clicks
        a["spend"]       += row.metrics.cost_micros / 1_000_000
        a["conversions"] += row.metrics.conversions
        a["conv_value"]  += row.metrics.conversions_value

    result = []
    for a in ads.values():
        a["spend"]      = round(a["spend"], 2)
        a["conversions"] = round(a["conversions"], 1)
        a["conv_value"] = round(a["conv_value"], 2)
        result.append(a)

    return sorted(result, key=lambda x: x["spend"], reverse=True)


# ── 3. GA4 Landing Page On-Site Metrics ──────────────────────────────────────

def pull_ga4_landing_page_metrics(ga_client) -> list:
    """Pull landing page metrics from GA4 for cross-reference with ad pages."""
    metric_names = [
        "sessions", "ecommercePurchases", "purchaseRevenue",
        "sessionConversionRate", "bounceRate", "averageSessionDuration",
        "engagedSessions",
    ]
    resp = ga_client.run_report(RunReportRequest(
        property=f"properties/{GA4_PROPERTY}",
        date_ranges=[DateRange(start_date=str(POST_START), end_date=str(POST_END))],
        dimensions=[Dimension(name="landingPagePlusQueryString")],
        metrics=[Metric(name=m) for m in metric_names],
        limit=500,
        order_bys=[{"metric": {"metric_name": "sessions"}, "desc": True}],
    ))

    pages = {}
    for row in resp.rows:
        page = row.dimension_values[0].value
        vals = {metric_names[i]: row.metric_values[i].value for i in range(len(metric_names))}
        pages[page] = {
            "sessions": int(vals["sessions"]),
            "purchases": int(vals["ecommercePurchases"]),
            "revenue": round(float(vals["purchaseRevenue"]), 2),
            "cr": round(float(vals["sessionConversionRate"]) * 100, 2),
            "bounce_rate": round(float(vals["bounceRate"]) * 100, 1),
            "avg_duration": round(float(vals["averageSessionDuration"]), 1),
            "engaged_sessions": int(vals["engagedSessions"]),
            "engagement_rate": round(int(vals["engagedSessions"]) / int(vals["sessions"]) * 100, 1) if int(vals["sessions"]) > 0 else 0,
        }
    return pages


# ── 4. Analysis ──────────────────────────────────────────────────────────────

def analyze_quality_issues(keywords: list) -> dict:
    """Aggregate quality score issues by campaign and component."""

    # Per-campaign summary
    campaign_summary = defaultdict(lambda: {
        "keywords": 0, "total_spend": 0, "total_impressions": 0,
        "qs_sum": 0, "qs_count": 0,
        "lp_below": 0, "lp_average": 0, "lp_above": 0,
        "ad_rel_below": 0, "ad_rel_average": 0, "ad_rel_above": 0,
        "ctr_below": 0, "ctr_average": 0, "ctr_above": 0,
        "worst_keywords": [],
    })

    for kw in keywords:
        camp = kw["campaign"]
        cs = campaign_summary[camp]
        cs["keywords"] += 1
        cs["total_spend"] += kw["spend"]
        cs["total_impressions"] += kw["impressions"]
        if kw["quality_score"] > 0:
            cs["qs_sum"] += kw["quality_score"]
            cs["qs_count"] += 1

        # Count component ratings
        for component, prefix in [("landing_page_exp", "lp_"), ("ad_relevance", "ad_rel_"), ("expected_ctr", "ctr_")]:
            val = kw[component].upper()
            if "BELOW" in val:
                cs[f"{prefix}below"] += 1
            elif "ABOVE" in val:
                cs[f"{prefix}above"] += 1
            elif "AVERAGE" in val:
                cs[f"{prefix}average"] += 1

        # Track worst keywords (QS <= 5 with significant spend)
        if kw["quality_score"] > 0 and kw["quality_score"] <= 5 and kw["spend"] > 10:
            cs["worst_keywords"].append(kw)

    # Calculate averages and sort worst keywords
    result = {}
    for camp, cs in campaign_summary.items():
        cs["total_spend"] = round(cs["total_spend"], 2)
        cs["avg_qs"] = round(cs["qs_sum"] / cs["qs_count"], 1) if cs["qs_count"] else 0
        cs["worst_keywords"] = sorted(cs["worst_keywords"], key=lambda x: x["quality_score"])[:10]
        result[camp] = cs

    return result


def cross_reference_landing_pages(ads: list, ga4_pages: dict) -> list:
    """Cross-reference ad landing pages with GA4 on-site metrics."""
    results = []
    for ad in ads:
        url = ad["landing_page"]
        # Normalize URL to match GA4 path format
        path = url.replace("https://naturesseed.com", "").replace("https://www.naturesseed.com", "")
        if not path:
            path = "/"

        # Find matching GA4 data (try exact, then without trailing slash)
        ga4 = ga4_pages.get(path, ga4_pages.get(path.rstrip("/"), ga4_pages.get(path + "/", {})))

        results.append({
            "campaign": ad["campaign"],
            "ad_group": ad["ad_group"],
            "landing_page": url,
            "path": path,
            "ad_spend": ad["spend"],
            "ad_clicks": ad["clicks"],
            "ad_conversions": ad["conversions"],
            "ad_conv_value": ad["conv_value"],
            # GA4 metrics (if found)
            "ga4_sessions": ga4.get("sessions", 0),
            "ga4_cr": ga4.get("cr", 0),
            "ga4_bounce_rate": ga4.get("bounce_rate", 0),
            "ga4_avg_duration": ga4.get("avg_duration", 0),
            "ga4_engagement_rate": ga4.get("engagement_rate", 0),
            "ga4_revenue": ga4.get("revenue", 0),
            # Issues
            "issues": [],
        })

        r = results[-1]
        if ga4:
            if ga4["bounce_rate"] > 40:
                r["issues"].append(f"High bounce rate ({ga4['bounce_rate']}%)")
            if ga4["avg_duration"] < 30:
                r["issues"].append(f"Very short session ({ga4['avg_duration']}s)")
            if ga4["cr"] < 1.0 and ga4["sessions"] > 50:
                r["issues"].append(f"Low conversion rate ({ga4['cr']}%)")
            if ga4["engagement_rate"] < 60:
                r["issues"].append(f"Low engagement ({ga4['engagement_rate']}%)")
        else:
            r["issues"].append("No GA4 data found — check URL tracking")

    return sorted(results, key=lambda x: x["ad_spend"], reverse=True)


# ── 5. HTML Report ───────────────────────────────────────────────────────────

def generate_html(data: dict) -> str:
    campaign_qs = data["campaign_quality"]
    lp_cross = data["landing_page_cross_ref"]
    keywords = data["keywords"]

    # Count total issues
    total_lp_below = sum(c["lp_below"] for c in campaign_qs.values())
    total_ad_below = sum(c["ad_rel_below"] for c in campaign_qs.values())
    total_ctr_below = sum(c["ctr_below"] for c in campaign_qs.values())
    total_keywords = sum(c["keywords"] for c in campaign_qs.values())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Landing Page Audit — Nature's Seed Google Ads</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8f9fa; color: #333; padding: 20px; }}
  .container {{ max-width: 1400px; margin: 0 auto; }}
  h1 {{ color: #2d5016; margin-bottom: 5px; }}
  .subtitle {{ color: #666; margin-bottom: 25px; }}
  .hero {{ background: linear-gradient(135deg, #8b2500, #c0392b); color: white; padding: 30px; border-radius: 12px; margin-bottom: 25px; }}
  .hero h2 {{ font-size: 1.8em; margin-bottom: 10px; }}
  .hero-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 15px; }}
  .hero-stat {{ text-align: center; }}
  .hero-stat .val {{ font-size: 2.2em; font-weight: bold; }}
  .hero-stat .lbl {{ opacity: 0.85; font-size: 0.9em; }}
  .section {{ margin-bottom: 30px; }}
  .section h2 {{ color: #2d5016; border-bottom: 2px solid #4a7c28; padding-bottom: 8px; margin-bottom: 15px; }}
  .section h3 {{ color: #555; margin: 15px 0 10px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85em; margin: 10px 0; }}
  th {{ background: #f0f4e8; text-align: left; padding: 10px 6px; border-bottom: 2px solid #ddd; white-space: nowrap; }}
  td {{ padding: 8px 6px; border-bottom: 1px solid #eee; }}
  tr:hover {{ background: #f9fdf5; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; font-weight: 600; margin: 1px; }}
  .below {{ background: #f8d7da; color: #721c24; }}
  .average {{ background: #fff3cd; color: #856404; }}
  .above {{ background: #d4edda; color: #155724; }}
  .card {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .issue-list {{ list-style: none; padding: 0; }}
  .issue-list li {{ padding: 4px 0; color: #c0392b; font-size: 0.9em; }}
  .issue-list li::before {{ content: "⚠ "; }}
  .fix-box {{ background: #e8f5e9; border: 1px solid #a5d6a7; border-radius: 8px; padding: 15px; margin: 10px 0; }}
  .fix-box h4 {{ color: #2d5016; margin-bottom: 8px; }}
  .fix-box ul {{ margin-left: 20px; }}
  .fix-box li {{ margin: 4px 0; }}
  .qs-bar {{ display: inline-block; height: 12px; border-radius: 6px; }}
  .qs-1 {{ background: #e74c3c; }} .qs-2 {{ background: #e74c3c; }} .qs-3 {{ background: #e67e22; }}
  .qs-4 {{ background: #f39c12; }} .qs-5 {{ background: #f1c40f; }} .qs-6 {{ background: #d4ac0d; }}
  .qs-7 {{ background: #27ae60; }} .qs-8 {{ background: #27ae60; }} .qs-9 {{ background: #1e8449; }}
  .qs-10 {{ background: #1e8449; }}
  .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }}
  .metric {{ text-align: center; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); }}
  .metric .val {{ font-size: 1.6em; font-weight: bold; }}
  .metric .lbl {{ font-size: 0.85em; color: #666; }}
  .bad {{ color: #e74c3c; }}
  .ok {{ color: #f39c12; }}
  .good {{ color: #27ae60; }}
</style>
</head>
<body>
<div class="container">
  <h1>Landing Page & Quality Score Audit</h1>
  <p class="subtitle">Nature's Seed Google Ads — {POST_START.strftime('%b %d')} to {POST_END.strftime('%b %d, %Y')}</p>

  <div class="hero">
    <h2>Impression Share Loss to Rank — Root Cause Analysis</h2>
    <p>Quality Score has 3 components. Here's where your keywords fall across all campaigns:</p>
    <div class="hero-grid">
      <div class="hero-stat">
        <div class="val">{total_lp_below}</div>
        <div class="lbl">Keywords with BELOW AVG<br>Landing Page Experience</div>
      </div>
      <div class="hero-stat">
        <div class="val">{total_ad_below}</div>
        <div class="lbl">Keywords with BELOW AVG<br>Ad Relevance</div>
      </div>
      <div class="hero-stat">
        <div class="val">{total_ctr_below}</div>
        <div class="lbl">Keywords with BELOW AVG<br>Expected CTR</div>
      </div>
    </div>
  </div>
"""

    # Per-campaign Quality Score breakdown
    html += '  <div class="section">\n    <h2>Quality Score by Campaign</h2>\n'

    for camp_name in sorted(campaign_qs.keys(), key=lambda c: campaign_qs[c]["total_spend"], reverse=True):
        cs = campaign_qs[camp_name]
        avg_qs = cs["avg_qs"]
        qs_class = f"qs-{min(max(int(avg_qs), 1), 10)}"

        html += f"""
    <div class="card">
      <h3>{camp_name} <span class="tag {'below' if avg_qs < 5 else 'average' if avg_qs < 7 else 'above'}">Avg QS: {avg_qs}/10</span></h3>
      <p style="color:#666; margin-bottom:10px;">{cs['keywords']} keywords | ${cs['total_spend']:,.0f} spend | {cs['total_impressions']:,} impressions</p>

      <div class="grid-3">
        <div class="metric">
          <div class="val {'bad' if cs['lp_below'] > 0 else 'good'}">{cs['lp_below']}</div>
          <div class="lbl">LP Below Avg</div>
          <div style="font-size:0.8em; color:#888">{cs['lp_average']} avg / {cs['lp_above']} above</div>
        </div>
        <div class="metric">
          <div class="val {'bad' if cs['ad_rel_below'] > 0 else 'good'}">{cs['ad_rel_below']}</div>
          <div class="lbl">Ad Rel Below Avg</div>
          <div style="font-size:0.8em; color:#888">{cs['ad_rel_average']} avg / {cs['ad_rel_above']} above</div>
        </div>
        <div class="metric">
          <div class="val {'bad' if cs['ctr_below'] > 0 else 'good'}">{cs['ctr_below']}</div>
          <div class="lbl">CTR Below Avg</div>
          <div style="font-size:0.8em; color:#888">{cs['ctr_average']} avg / {cs['ctr_above']} above</div>
        </div>
      </div>
"""

        # Show worst keywords for this campaign
        if cs["worst_keywords"]:
            html += """
      <h4 style="margin-top:15px; color:#c0392b;">Keywords Needing Attention (QS ≤ 5)</h4>
      <table>
        <tr><th>Keyword</th><th>Match</th><th>QS</th><th>LP Exp</th><th>Ad Rel</th><th>Exp CTR</th><th>Spend</th><th>ROAS</th><th>Impr</th></tr>
"""
            for kw in cs["worst_keywords"]:
                lp_class = "below" if "BELOW" in kw["landing_page_exp"].upper() else "average" if "AVERAGE" in kw["landing_page_exp"].upper() and "ABOVE" not in kw["landing_page_exp"].upper() else "above"
                ar_class = "below" if "BELOW" in kw["ad_relevance"].upper() else "average" if "AVERAGE" in kw["ad_relevance"].upper() and "ABOVE" not in kw["ad_relevance"].upper() else "above"
                ctr_class = "below" if "BELOW" in kw["expected_ctr"].upper() else "average" if "AVERAGE" in kw["expected_ctr"].upper() and "ABOVE" not in kw["expected_ctr"].upper() else "above"

                lp_short = kw["landing_page_exp"].replace("QUALITY_SCORE_BUCKET_", "").replace("_", " ").title()
                ar_short = kw["ad_relevance"].replace("QUALITY_SCORE_BUCKET_", "").replace("_", " ").title()
                ctr_short = kw["expected_ctr"].replace("QUALITY_SCORE_BUCKET_", "").replace("_", " ").title()

                html += f"""
        <tr>
          <td><strong>{kw['keyword'][:35]}</strong></td>
          <td>{kw['match_type']}</td>
          <td><span class="qs-bar qs-{kw['quality_score']}" style="width:{kw['quality_score']*10}px"></span> {kw['quality_score']}</td>
          <td><span class="tag {lp_class}">{lp_short}</span></td>
          <td><span class="tag {ar_class}">{ar_short}</span></td>
          <td><span class="tag {ctr_class}">{ctr_short}</span></td>
          <td>${kw['spend']:,.0f}</td>
          <td>{kw['roas']}x</td>
          <td>{kw['impressions']:,}</td>
        </tr>
"""
            html += "      </table>\n"

        html += "    </div>\n"

    html += "  </div>\n"

    # Landing Page Cross-Reference with GA4
    html += """
  <div class="section">
    <h2>Landing Pages — Ad Performance vs On-Site Behavior</h2>
    <p style="color:#666; margin-bottom:10px;">Ad landing page URLs cross-referenced with GA4 on-site metrics. Red flags indicate pages that may be hurting Quality Score.</p>
    <table>
      <tr>
        <th>Campaign</th>
        <th>Landing Page</th>
        <th>Ad Spend</th>
        <th>Ad Clicks</th>
        <th>GA4 Sessions</th>
        <th>GA4 CR%</th>
        <th>Bounce%</th>
        <th>Avg Duration</th>
        <th>Engage%</th>
        <th>Issues</th>
      </tr>
"""
    for lp in lp_cross[:40]:
        path_short = lp["path"][:50] if len(lp["path"]) > 50 else lp["path"]
        issues_html = ", ".join(f'<span class="tag below">{i}</span>' for i in lp["issues"]) if lp["issues"] else '<span class="tag above">OK</span>'
        bounce_class = ' class="bad"' if lp["ga4_bounce_rate"] > 40 else ""
        cr_class = ' class="bad"' if lp["ga4_cr"] < 1.0 and lp["ga4_sessions"] > 50 else ""

        html += f"""
      <tr>
        <td>{lp['campaign'][:25]}</td>
        <td title="{lp['landing_page']}">{path_short}</td>
        <td>${lp['ad_spend']:,.0f}</td>
        <td>{lp['ad_clicks']:,}</td>
        <td>{lp['ga4_sessions']:,}</td>
        <td{cr_class}>{lp['ga4_cr']}%</td>
        <td{bounce_class}>{lp['ga4_bounce_rate']}%</td>
        <td>{lp['ga4_avg_duration']:.0f}s</td>
        <td>{lp['ga4_engagement_rate']}%</td>
        <td>{issues_html}</td>
      </tr>
"""
    html += "    </table>\n  </div>\n"

    # Actionable Fix Guide
    html += """
  <div class="section">
    <h2>How to Fix Impression Share Loss to Rank</h2>

    <div class="fix-box">
      <h4>1. Landing Page Experience (affects QS most heavily)</h4>
      <ul>
        <li><strong>Page speed:</strong> Run PageSpeed Insights on every landing page. Target 90+ mobile score. Compress images, defer JS, use next-gen formats</li>
        <li><strong>Mobile experience:</strong> Google evaluates mobile-first. Ensure tap targets, readable text, no horizontal scroll</li>
        <li><strong>Content relevance:</strong> Landing page content must match the keyword intent. "grass seed" should land on a grass seed category page, not homepage</li>
        <li><strong>Above-the-fold CTA:</strong> Clear product/category presentation with visible add-to-cart or shop-now without scrolling</li>
        <li><strong>HTTPS + no interstitials:</strong> Ensure all pages are secure with no popup blockers on entry</li>
        <li><strong>Unique, useful content:</strong> Google rewards pages with original descriptions, reviews, guides — not just product grids</li>
      </ul>
    </div>

    <div class="fix-box">
      <h4>2. Ad Relevance (keyword ↔ ad copy alignment)</h4>
      <ul>
        <li><strong>Include keyword in headlines:</strong> RSA should have at least 2 headlines containing the exact keyword or close variant</li>
        <li><strong>Tighter ad groups:</strong> If one ad group covers "grass seed" AND "wildflower seed", split them — each needs its own ad copy</li>
        <li><strong>Use keyword insertion:</strong> {Keyword:Default Text} in headlines for broad match ad groups</li>
        <li><strong>Pin relevant headlines:</strong> Pin keyword-matching headlines to positions 1-2 so they always show</li>
      </ul>
    </div>

    <div class="fix-box">
      <h4>3. Expected CTR (ad attractiveness in SERP)</h4>
      <ul>
        <li><strong>Compelling headlines:</strong> Use numbers, urgency, differentiators ("Free Shipping", "Since 1998", "USDA Certified")</li>
        <li><strong>Sitelinks + callouts:</strong> Ad extensions improve CTR significantly. Ensure all campaigns have 4+ sitelinks and callout extensions</li>
        <li><strong>Structured snippets:</strong> Add "Types:", "Brands:", "Services:" snippets</li>
        <li><strong>Price extensions:</strong> Show product prices directly in the ad for shopping intent keywords</li>
        <li><strong>Review / seller ratings:</strong> If Shopper Approved reviews are connected, these boost CTR</li>
      </ul>
    </div>

    <div class="fix-box">
      <h4>4. PMax-Specific Fixes (no keyword QS, but feed quality matters)</h4>
      <ul>
        <li><strong>Product feed titles:</strong> Include top search terms in product titles (e.g., "Premium Kentucky Bluegrass Seed" not just "KBG Mix")</li>
        <li><strong>High-quality images:</strong> Lifestyle images outperform white-background product shots in PMax</li>
        <li><strong>Product descriptions:</strong> Match common search queries in descriptions — Google uses these for relevance matching</li>
        <li><strong>Asset groups:</strong> Create separate asset groups for different product categories with tailored headlines/images</li>
        <li><strong>Audience signals:</strong> Add purchase intent audiences and competitor URL signals</li>
      </ul>
    </div>
  </div>
"""

    html += """
  <div style="text-align:center; color:#999; margin-top:30px; padding:15px;">
    Generated by Nature's Seed Data Orchestrator | Landing Page Audit v1.0
  </div>
</div>
</body>
</html>"""

    return html


# ── Main ─────────────────────────────────────────────────────────────────────

def run():
    client, customer_id = _gads_client()
    service = client.get_service("GoogleAdsService")

    # 1. Keyword quality scores
    log.info("Pulling keyword quality scores...")
    keywords = pull_keyword_quality_scores(service, customer_id)
    log.info(f"  Got {len(keywords)} keywords with QS data")

    # 2. Ad landing page URLs
    log.info("Pulling ad landing pages...")
    ads = pull_ad_landing_pages(service, customer_id)
    log.info(f"  Got {len(ads)} ad/landing page combos")

    # 3. GA4 landing page metrics
    log.info("Pulling GA4 landing page metrics...")
    creds = _google_creds()
    ga_client = BetaAnalyticsDataClient(credentials=creds)
    ga4_pages = pull_ga4_landing_page_metrics(ga_client)
    log.info(f"  Got {len(ga4_pages)} GA4 landing pages")

    # 4. Analysis
    log.info("Analyzing quality score issues...")
    campaign_qs = analyze_quality_issues(keywords)

    log.info("Cross-referencing landing pages...")
    lp_cross = cross_reference_landing_pages(ads, ga4_pages)

    data = {
        "keywords": keywords,
        "ads": ads,
        "campaign_quality": campaign_qs,
        "landing_page_cross_ref": lp_cross,
    }

    # Save JSON
    json_path = ROOT / "reports" / "landing_page_audit.json"
    json_path.write_text(json.dumps(data, indent=2, default=str))
    log.info(f"Saved JSON: {json_path}")

    # Generate HTML
    html = generate_html(data)
    html_path = ROOT / "reports" / "landing_page_audit.html"
    html_path.write_text(html)
    log.info(f"Saved HTML: {html_path}")

    # Print summary
    print("\n" + "=" * 80)
    print("LANDING PAGE AUDIT SUMMARY")
    print("=" * 80)
    for camp, cs in sorted(campaign_qs.items(), key=lambda x: x[1]["total_spend"], reverse=True):
        print(f"\n{camp}")
        print(f"  Avg QS: {cs['avg_qs']}/10 | {cs['keywords']} keywords | ${cs['total_spend']:,.0f} spend")
        print(f"  Landing Page:  {cs['lp_below']} below / {cs['lp_average']} avg / {cs['lp_above']} above")
        print(f"  Ad Relevance:  {cs['ad_rel_below']} below / {cs['ad_rel_average']} avg / {cs['ad_rel_above']} above")
        print(f"  Expected CTR:  {cs['ctr_below']} below / {cs['ctr_average']} avg / {cs['ctr_above']} above")
        if cs["worst_keywords"]:
            print(f"  Worst keywords:")
            for kw in cs["worst_keywords"][:5]:
                print(f"    QS {kw['quality_score']}: '{kw['keyword']}' — LP:{kw['landing_page_exp']} Ad:{kw['ad_relevance']} CTR:{kw['expected_ctr']} (${kw['spend']:.0f} spend)")


if __name__ == "__main__":
    run()
