#!/usr/bin/env python3
"""
Growth Gap Analysis — Nature's Seed
====================================
Analyzes every connected platform to find high-impact growth opportunities,
similar to the theme change that drove +70% revenue lift.

Data Sources:
  - GA4 channel data (from theme_attribution_data.json)
  - Google Search Console: top queries by impression (low CTR = quick wins)
  - Google Ads: campaign-level ROAS to find scaling opportunities
  - Klaviyo: flow + campaign revenue attribution
  - Supabase: revenue trends

Outputs:
  - reports/growth_gaps_report.html — Interactive prioritized report
  - reports/growth_gaps_data.json   — Raw data for further analysis

Usage:
    python3 reports/growth_gap_analysis.py
"""

import json
import logging
from datetime import date, timedelta
from pathlib import Path

import requests
from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric, FilterExpression,
    Filter
)
from googleapiclient.discovery import build
from google.ads.googleads.client import GoogleAdsClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("growth_gaps")

ROOT = Path(__file__).resolve().parents[1]

# ── Analysis Period ──────────────────────────────────────────────────────────
# Post-theme window (last 13 days)
POST_START = date(2026, 2, 28)
POST_END   = date(2026, 3, 12)
# Same window last year for seasonal baseline
YOY_START  = date(2025, 2, 28)
YOY_END    = date(2025, 3, 12)

GA4_PROPERTY = "294622924"
GSC_SITE     = "sc-domain:naturesseed.com"


# ── Env ──────────────────────────────────────────────────────────────────────

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


def _google_creds() -> Credentials:
    return Credentials(
        token=None,
        refresh_token=ENV["GOOGLE_ADS_REFRESH_TOKEN"],
        client_id=ENV["GOOGLE_ADS_CLIENT_ID"],
        client_secret=ENV["GOOGLE_ADS_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )


# ── 1. GSC Top Queries (high impression, low CTR = quick wins) ───────────────

def pull_gsc_top_queries(sc_client, start: date, end: date, limit=200) -> list:
    """Pull top queries by impressions to find CTR optimization opportunities."""
    body = {
        "startDate": str(start),
        "endDate": str(end),
        "dimensions": ["query"],
        "rowLimit": limit,
        "type": "web",
    }
    result = sc_client.searchanalytics().query(siteUrl=GSC_SITE, body=body).execute()
    rows = []
    for r in result.get("rows", []):
        rows.append({
            "query": r["keys"][0],
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"] * 100, 2),
            "position": round(r["position"], 1),
        })
    return rows


def pull_gsc_top_pages(sc_client, start: date, end: date, limit=100) -> list:
    """Pull top pages by impressions to find page-level CTR opportunities."""
    body = {
        "startDate": str(start),
        "endDate": str(end),
        "dimensions": ["page"],
        "rowLimit": limit,
        "type": "web",
    }
    result = sc_client.searchanalytics().query(siteUrl=GSC_SITE, body=body).execute()
    rows = []
    for r in result.get("rows", []):
        rows.append({
            "page": r["keys"][0],
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"] * 100, 2),
            "position": round(r["position"], 1),
        })
    return rows


# ── 2. Google Ads Campaign-Level ROAS ────────────────────────────────────────

def pull_gads_campaigns(start: date, end: date) -> list:
    """Pull campaign-level performance for the post-theme period."""
    customer_id = ENV["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
    login_id    = ENV.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")

    config = {
        "developer_token": ENV["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": ENV["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": ENV["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": ENV["GOOGLE_ADS_REFRESH_TOKEN"],
        "use_proto_plus": True,
    }
    if login_id:
        config["login_customer_id"] = login_id

    client = GoogleAdsClient.load_from_dict(config)
    service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.advertising_channel_type,
            campaign.bidding_strategy_type,
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date >= '{start}'
          AND segments.date <= '{end}'
          AND campaign.status = 'ENABLED'
          AND metrics.impressions > 0
    """
    response = service.search(customer_id=customer_id, query=query)

    campaigns = {}
    for row in response:
        cid = str(row.campaign.id)
        if cid not in campaigns:
            campaigns[cid] = {
                "id": cid,
                "name": row.campaign.name,
                "type": str(row.campaign.advertising_channel_type).replace("AdvertisingChannelType.", ""),
                "bidding": str(row.campaign.bidding_strategy_type).replace("BiddingStrategyType.", ""),
                "spend": 0, "impressions": 0, "clicks": 0,
                "conversions": 0, "conv_value": 0,
            }
        c = campaigns[cid]
        c["spend"]       += row.metrics.cost_micros / 1_000_000
        c["impressions"] += row.metrics.impressions
        c["clicks"]      += row.metrics.clicks
        c["conversions"] += row.metrics.conversions
        c["conv_value"]  += row.metrics.conversions_value

    result = []
    for c in campaigns.values():
        c["spend"]      = round(c["spend"], 2)
        c["conversions"] = round(c["conversions"], 1)
        c["conv_value"] = round(c["conv_value"], 2)
        c["roas"]       = round(c["conv_value"] / c["spend"], 2) if c["spend"] > 0 else 0
        c["cpc"]        = round(c["spend"] / c["clicks"], 2) if c["clicks"] else 0
        c["ctr"]        = round(c["clicks"] / c["impressions"] * 100, 2) if c["impressions"] else 0
        c["cr"]         = round(c["conversions"] / c["clicks"] * 100, 2) if c["clicks"] else 0
        result.append(c)

    return sorted(result, key=lambda x: x["conv_value"], reverse=True)


# ── 3. Google Ads Shopping Product Performance ───────────────────────────────

def pull_shopping_products(start: date, end: date, limit=50) -> list:
    """Pull shopping product performance to find underperformers."""
    customer_id = ENV["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
    login_id    = ENV.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")

    config = {
        "developer_token": ENV["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": ENV["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": ENV["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": ENV["GOOGLE_ADS_REFRESH_TOKEN"],
        "use_proto_plus": True,
    }
    if login_id:
        config["login_customer_id"] = login_id

    client = GoogleAdsClient.load_from_dict(config)
    service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            campaign.id,
            segments.product_title,
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value
        FROM shopping_performance_view
        WHERE segments.date >= '{start}'
          AND segments.date <= '{end}'
    """
    response = service.search(customer_id=customer_id, query=query)

    products = {}
    for row in response:
        title = row.segments.product_title or "(unknown)"
        if title not in products:
            products[title] = {
                "title": title,
                "spend": 0, "impressions": 0, "clicks": 0,
                "conversions": 0, "conv_value": 0,
            }
        p = products[title]
        p["spend"]       += row.metrics.cost_micros / 1_000_000
        p["impressions"] += row.metrics.impressions
        p["clicks"]      += row.metrics.clicks
        p["conversions"] += row.metrics.conversions
        p["conv_value"]  += row.metrics.conversions_value

    result = []
    for p in products.values():
        p["spend"]      = round(p["spend"], 2)
        p["conversions"] = round(p["conversions"], 1)
        p["conv_value"] = round(p["conv_value"], 2)
        p["roas"]       = round(p["conv_value"] / p["spend"], 2) if p["spend"] > 0 else 0
        result.append(p)

    # Return top spenders (most opportunity for optimization)
    return sorted(result, key=lambda x: x["spend"], reverse=True)[:limit]


# ── 4. GA4 Landing Page Performance ─────────────────────────────────────────

def pull_ga4_landing_pages(ga_client, start: date, end: date, limit=50) -> list:
    """Pull landing page performance to find high-traffic/low-converting pages."""
    metric_names = [
        "sessions", "ecommercePurchases", "purchaseRevenue",
        "sessionConversionRate", "bounceRate",
    ]
    resp = ga_client.run_report(RunReportRequest(
        property=f"properties/{GA4_PROPERTY}",
        date_ranges=[DateRange(start_date=str(start), end_date=str(end))],
        dimensions=[Dimension(name="landingPagePlusQueryString")],
        metrics=[Metric(name=m) for m in metric_names],
        limit=limit,
        order_bys=[{
            "metric": {"metric_name": "sessions"},
            "desc": True,
        }],
    ))

    rows = []
    for row in resp.rows:
        page = row.dimension_values[0].value
        vals = {metric_names[i]: row.metric_values[i].value for i in range(len(metric_names))}
        rows.append({
            "page": page,
            "sessions": int(vals["sessions"]),
            "purchases": int(vals["ecommercePurchases"]),
            "revenue": round(float(vals["purchaseRevenue"]), 2),
            "cr": round(float(vals["sessionConversionRate"]) * 100, 2),
            "bounce_rate": round(float(vals["bounceRate"]) * 100, 1),
        })
    return rows


# ── 5. GA4 Device Category Performance ──────────────────────────────────────

def pull_ga4_devices(ga_client, start: date, end: date) -> list:
    """Pull device-level performance to find mobile/desktop gaps."""
    metric_names = [
        "sessions", "ecommercePurchases", "purchaseRevenue",
        "sessionConversionRate", "bounceRate", "averageSessionDuration",
    ]
    resp = ga_client.run_report(RunReportRequest(
        property=f"properties/{GA4_PROPERTY}",
        date_ranges=[DateRange(start_date=str(start), end_date=str(end))],
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[Metric(name=m) for m in metric_names],
    ))

    rows = []
    for row in resp.rows:
        device = row.dimension_values[0].value
        vals = {metric_names[i]: row.metric_values[i].value for i in range(len(metric_names))}
        rows.append({
            "device": device,
            "sessions": int(vals["sessions"]),
            "purchases": int(vals["ecommercePurchases"]),
            "revenue": round(float(vals["purchaseRevenue"]), 2),
            "cr": round(float(vals["sessionConversionRate"]) * 100, 2),
            "bounce_rate": round(float(vals["bounceRate"]) * 100, 1),
            "avg_duration": round(float(vals["averageSessionDuration"]), 1),
        })
    return sorted(rows, key=lambda x: x["sessions"], reverse=True)


# ── 6. Klaviyo Flow + Campaign Revenue (via MCP fallback to REST) ────────────

def pull_klaviyo_flows() -> list:
    """Pull Klaviyo flow performance via REST API."""
    api_key = ENV.get("KLAVIYO_API_KEY", "")
    if not api_key:
        log.warning("No KLAVIYO_API_KEY — skipping Klaviyo flows")
        return []

    headers = {
        "Authorization": f"Klaviyo-API-Key {api_key}",
        "revision": "2024-07-15",
        "Accept": "application/json",
    }

    resp = requests.get(
        "https://a.klaviyo.com/api/flows",
        headers=headers,
        params={"fields[flow]": "name,status,created,updated"},
        timeout=30,
    )
    if resp.status_code != 200:
        log.warning(f"Klaviyo flows API returned {resp.status_code}")
        return []

    flows = []
    for f in resp.json().get("data", []):
        attrs = f.get("attributes", {})
        flows.append({
            "id": f["id"],
            "name": attrs.get("name", ""),
            "status": attrs.get("status", ""),
        })
    return flows


# ── Analysis Engine ──────────────────────────────────────────────────────────

def analyze_channel_gaps(attr_data: dict) -> list:
    """Analyze channel data from theme attribution to find gaps."""
    gaps = []
    pre = {c["sessionDefaultChannelGroup"]: c for c in attr_data.get("ga4_channels_pre", [])}
    post = {c["sessionDefaultChannelGroup"]: c for c in attr_data.get("ga4_channels_post", [])}

    for channel, p in post.items():
        sessions = int(p["sessions"])
        revenue = float(p["purchaseRevenue"])
        cr = float(p["sessionConversionRate"]) * 100
        bounce = float(p["bounceRate"]) * 100
        purchases = int(p["ecommercePurchases"])

        pre_data = pre.get(channel, {})
        pre_sessions = int(pre_data.get("sessions", 0))
        pre_revenue = float(pre_data.get("purchaseRevenue", 0))
        pre_cr = float(pre_data.get("sessionConversionRate", 0)) * 100

        rev_per_session = revenue / sessions if sessions > 0 else 0

        gap = {
            "channel": channel,
            "sessions": sessions,
            "revenue": revenue,
            "cr": round(cr, 2),
            "bounce": round(bounce, 1),
            "purchases": purchases,
            "rev_per_session": round(rev_per_session, 2),
            "pre_sessions": pre_sessions,
            "pre_revenue": round(pre_revenue, 2),
            "pre_cr": round(pre_cr, 2),
            "session_change_pct": round((sessions - pre_sessions) / pre_sessions * 100, 1) if pre_sessions else 0,
            "revenue_change_pct": round((revenue - pre_revenue) / pre_revenue * 100, 1) if pre_revenue else 0,
            "cr_change_pp": round(cr - pre_cr, 2),
            "issues": [],
            "opportunities": [],
        }

        # Flag issues and opportunities
        if cr > 4 and sessions < 3000:
            gap["opportunities"].append(f"HIGH CR ({cr:.1f}%) but low traffic ({sessions} sessions) — scale this channel")
        if cr < 1 and revenue < 1000 and sessions > 500:
            gap["issues"].append(f"LOW CR ({cr:.1f}%) with {sessions} sessions — fix targeting or landing page")
        if bounce > 50:
            gap["issues"].append(f"HIGH BOUNCE ({bounce:.0f}%) — traffic quality issue or tracking problem")
        if rev_per_session > 8 and sessions < 5000:
            gap["opportunities"].append(f"High rev/session (${rev_per_session:.2f}) — profitable to scale")
        if pre_cr > 0 and cr > pre_cr * 1.5:
            gap["opportunities"].append(f"CR improved {pre_cr:.1f}% → {cr:.1f}% post-theme — theme is working for this channel")

        gaps.append(gap)

    return sorted(gaps, key=lambda x: len(x["opportunities"]) + len(x["issues"]), reverse=True)


def find_gsc_quick_wins(queries: list) -> list:
    """Find queries with high impressions but low CTR (positions 4-20)."""
    wins = []
    for q in queries:
        # High impression queries in striking distance (pos 4-20) with low CTR
        if q["impressions"] > 100 and q["position"] <= 20 and q["ctr"] < 3:
            potential_clicks = int(q["impressions"] * 0.05)  # 5% CTR target
            additional_clicks = potential_clicks - q["clicks"]
            if additional_clicks > 10:
                wins.append({
                    **q,
                    "potential_clicks": potential_clicks,
                    "additional_clicks": additional_clicks,
                    "priority": "high" if q["position"] <= 10 and q["impressions"] > 500 else "medium",
                })
    return sorted(wins, key=lambda x: x["additional_clicks"], reverse=True)[:30]


def find_campaign_scaling_ops(campaigns: list) -> list:
    """Find campaigns with high ROAS that could handle more budget."""
    ops = []
    for c in campaigns:
        if c["roas"] >= 3.0 and c["conversions"] >= 5:
            # High ROAS campaigns that could scale
            ops.append({
                **c,
                "action": "SCALE",
                "reason": f"ROAS {c['roas']}x with {c['conversions']} conversions — increase budget",
            })
        elif c["spend"] > 500 and c["roas"] < 1.5 and c["conversions"] < 5:
            ops.append({
                **c,
                "action": "FIX_OR_PAUSE",
                "reason": f"Spent ${c['spend']:.0f} with only {c['roas']}x ROAS — review targeting",
            })
        elif c["roas"] >= 2.0 and c["cr"] < 1.5 and c["clicks"] > 200:
            ops.append({
                **c,
                "action": "OPTIMIZE_CR",
                "reason": f"Good ROAS ({c['roas']}x) but low CR ({c['cr']}%) — landing page opportunity",
            })
    return ops


def find_landing_page_gaps(pages: list) -> list:
    """Find high-traffic pages with low conversion rates."""
    gaps = []
    for p in pages:
        if p["sessions"] > 200 and p["cr"] < 1.0:
            gaps.append({
                **p,
                "action": "OPTIMIZE",
                "reason": f"{p['sessions']} sessions, {p['cr']}% CR — needs CTA/UX improvement",
            })
        elif p["sessions"] > 100 and p["bounce_rate"] > 50:
            gaps.append({
                **p,
                "action": "FIX_BOUNCE",
                "reason": f"{p['bounce_rate']}% bounce rate on {p['sessions']} sessions — content or speed issue",
            })
    return sorted(gaps, key=lambda x: x["sessions"], reverse=True)[:20]


def find_device_gaps(devices: list) -> list:
    """Find mobile vs desktop conversion gaps."""
    gaps = []
    desktop_cr = 0
    for d in devices:
        if d["device"] == "desktop":
            desktop_cr = d["cr"]
            break

    for d in devices:
        if d["device"] != "desktop" and desktop_cr > 0:
            cr_gap = desktop_cr - d["cr"]
            if cr_gap > 0.5 and d["sessions"] > 1000:
                lost_rev = d["sessions"] * (cr_gap / 100) * (d["revenue"] / d["purchases"]) if d["purchases"] > 0 else 0
                gaps.append({
                    **d,
                    "cr_gap_vs_desktop": round(cr_gap, 2),
                    "estimated_lost_revenue": round(lost_rev, 0),
                    "action": f"{d['device']} CR is {cr_gap:.1f}pp below desktop — optimize mobile experience",
                })
    return gaps


# ── Prioritized Opportunities Builder ────────────────────────────────────────

def build_opportunities(data: dict) -> list:
    """Build a prioritized list of growth opportunities with estimated impact."""
    ops = []

    # 1. Channel gaps from GA4
    channel_gaps = data.get("channel_gaps", [])
    for g in channel_gaps:
        for opp in g["opportunities"]:
            # Estimate impact based on channel size and CR
            if "scale" in opp.lower():
                # If we doubled sessions at current CR
                est_rev = g["rev_per_session"] * g["sessions"]
                ops.append({
                    "category": "Channel Scaling",
                    "channel": g["channel"],
                    "opportunity": opp,
                    "est_monthly_revenue": round(est_rev * 2, 0),  # 2x sessions
                    "effort": "medium",
                    "priority_score": g["cr"] * g["rev_per_session"],
                })

    # 2. Paid Search scaling (the #1 gap from the data)
    ps = next((g for g in channel_gaps if g["channel"] == "Paid Search"), None)
    if ps and ps["cr"] > 4:
        ops.append({
            "category": "Paid Search Scaling",
            "channel": "Paid Search",
            "opportunity": f"Paid Search has {ps['cr']}% CR (highest channel) but only {ps['sessions']} sessions. "
                          f"Doubling budget could add ~${ps['revenue']:.0f}/mo in revenue.",
            "est_monthly_revenue": round(ps["revenue"] * 2, 0),
            "effort": "low",
            "priority_score": 100,
        })

    # 3. Email channel
    em = next((g for g in channel_gaps if g["channel"] == "Email"), None)
    if em and em["cr"] > 3:
        ops.append({
            "category": "Email Marketing",
            "channel": "Email",
            "opportunity": f"Email has {em['cr']}% CR but only {em['sessions']} sessions. "
                          f"More campaigns + flows could 3x email revenue from ${em['revenue']:.0f}.",
            "est_monthly_revenue": round(em["revenue"] * 3, 0),
            "effort": "medium",
            "priority_score": 90,
        })

    # 4. Paid Social fix
    social = next((g for g in channel_gaps if g["channel"] == "Paid Social"), None)
    if social and social["cr"] < 1:
        ops.append({
            "category": "Paid Social Fix",
            "channel": "Paid Social",
            "opportunity": f"Paid Social CR is only {social['cr']}% with {social['sessions']} sessions. "
                          f"Either fix targeting/creative or reallocate budget to Paid Search.",
            "est_monthly_revenue": round(social["sessions"] * 5, 0),  # At reasonable $5 rev/session
            "effort": "medium",
            "priority_score": 70,
        })

    # 5. GSC quick wins
    gsc_wins = data.get("gsc_quick_wins", [])
    total_additional = sum(w["additional_clicks"] for w in gsc_wins)
    if total_additional > 0:
        # Assume 2% conversion on organic, $150 AOV
        est_rev = total_additional * 0.02 * 150
        ops.append({
            "category": "SEO Quick Wins",
            "channel": "Organic Search",
            "opportunity": f"{len(gsc_wins)} queries with high impressions but low CTR. "
                          f"Optimizing titles/meta could add ~{total_additional} clicks/period.",
            "est_monthly_revenue": round(est_rev, 0),
            "effort": "medium",
            "priority_score": 60,
        })

    # 6. Campaign scaling opportunities
    scale_ops = [c for c in data.get("campaign_ops", []) if c["action"] == "SCALE"]
    if scale_ops:
        total_scalable_rev = sum(c["conv_value"] for c in scale_ops)
        ops.append({
            "category": "Google Ads Scaling",
            "channel": "Google Ads",
            "opportunity": f"{len(scale_ops)} campaigns with ROAS > 3x are budget-constrained. "
                          f"Current value: ${total_scalable_rev:,.0f}. Increasing budgets 50% could add "
                          f"~${total_scalable_rev * 0.3:,.0f}.",
            "est_monthly_revenue": round(total_scalable_rev * 0.3, 0),
            "effort": "low",
            "priority_score": 85,
        })

    # 7. Fix/pause underperformers
    fix_ops = [c for c in data.get("campaign_ops", []) if c["action"] == "FIX_OR_PAUSE"]
    if fix_ops:
        wasted = sum(c["spend"] - c["conv_value"] for c in fix_ops if c["conv_value"] < c["spend"])
        ops.append({
            "category": "Google Ads Waste Reduction",
            "channel": "Google Ads",
            "opportunity": f"{len(fix_ops)} campaigns spending with ROAS < 1.5x. "
                          f"~${wasted:,.0f} in wasted spend could be reallocated to high-ROAS campaigns.",
            "est_monthly_revenue": round(wasted * 2, 0),  # reallocated at 2x ROAS
            "effort": "low",
            "priority_score": 75,
        })

    # 8. Device gaps
    device_gaps = data.get("device_gaps", [])
    for dg in device_gaps:
        ops.append({
            "category": "Mobile Optimization",
            "channel": dg["device"],
            "opportunity": dg["action"],
            "est_monthly_revenue": dg["estimated_lost_revenue"],
            "effort": "high",
            "priority_score": 55,
        })

    # 9. Landing page optimization
    lp_gaps = data.get("landing_page_gaps", [])
    if lp_gaps:
        total_sessions = sum(p["sessions"] for p in lp_gaps)
        ops.append({
            "category": "Landing Page Optimization",
            "channel": "All",
            "opportunity": f"{len(lp_gaps)} high-traffic pages with <1% CR or >50% bounce. "
                          f"Combined {total_sessions} sessions/period — CRO could recover significant revenue.",
            "est_monthly_revenue": round(total_sessions * 2, 0),  # conservative $2/session uplift
            "effort": "high",
            "priority_score": 50,
        })

    # 10. Walmart marketplace acceleration
    rev_data = data.get("attribution", {})
    rev_post = rev_data.get("rev_post", {})
    wm_rev = rev_post.get("wm_revenue", 0)
    if wm_rev > 0:
        ops.append({
            "category": "Walmart Marketplace",
            "channel": "Walmart",
            "opportunity": f"Walmart revenue grew to ${wm_rev:,.0f}/period but is only "
                          f"{wm_rev / rev_post.get('total_revenue', 1) * 100:.1f}% of total. "
                          f"Buy box optimization + listing quality could 3-5x this.",
            "est_monthly_revenue": round(wm_rev * 4, 0),
            "effort": "medium",
            "priority_score": 45,
        })

    # Sort by priority score
    return sorted(ops, key=lambda x: x["priority_score"], reverse=True)


# ── HTML Report Generator ────────────────────────────────────────────────────

def generate_html_report(data: dict) -> str:
    """Generate an interactive HTML report."""
    opportunities = data.get("opportunities", [])
    channel_gaps = data.get("channel_gaps", [])
    gsc_wins = data.get("gsc_quick_wins", [])
    campaign_ops = data.get("campaign_ops", [])
    campaigns = data.get("campaigns", [])
    devices = data.get("devices", [])
    landing_pages = data.get("landing_pages", [])
    device_gaps = data.get("device_gaps", [])

    total_est_revenue = sum(o.get("est_monthly_revenue", 0) for o in opportunities)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Growth Gap Analysis — Nature's Seed</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8f9fa; color: #333; padding: 20px; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ color: #2d5016; margin-bottom: 5px; font-size: 1.8em; }}
  .subtitle {{ color: #666; margin-bottom: 20px; }}
  .hero {{ background: linear-gradient(135deg, #2d5016, #4a7c28); color: white; padding: 30px; border-radius: 12px; margin-bottom: 25px; }}
  .hero h2 {{ font-size: 2.5em; margin-bottom: 5px; }}
  .hero .big-number {{ font-size: 3em; font-weight: bold; }}
  .hero .context {{ opacity: 0.85; margin-top: 8px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-bottom: 25px; }}
  .card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .card h3 {{ color: #2d5016; margin-bottom: 10px; font-size: 1.1em; }}
  .priority-high {{ border-left: 4px solid #e74c3c; }}
  .priority-medium {{ border-left: 4px solid #f39c12; }}
  .priority-low {{ border-left: 4px solid #27ae60; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.9em; }}
  th {{ background: #f0f4e8; text-align: left; padding: 10px 8px; border-bottom: 2px solid #ddd; }}
  td {{ padding: 8px; border-bottom: 1px solid #eee; }}
  tr:hover {{ background: #f9fdf5; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; font-weight: 600; }}
  .tag-scale {{ background: #d4edda; color: #155724; }}
  .tag-fix {{ background: #f8d7da; color: #721c24; }}
  .tag-optimize {{ background: #fff3cd; color: #856404; }}
  .section {{ margin-bottom: 30px; }}
  .section h2 {{ color: #2d5016; border-bottom: 2px solid #4a7c28; padding-bottom: 8px; margin-bottom: 15px; }}
  .metric {{ text-align: center; }}
  .metric .value {{ font-size: 1.8em; font-weight: bold; color: #2d5016; }}
  .metric .label {{ font-size: 0.85em; color: #666; }}
  .up {{ color: #27ae60; }}
  .down {{ color: #e74c3c; }}
  .opp-card {{ background: white; border-radius: 10px; padding: 18px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); display: flex; align-items: flex-start; gap: 15px; }}
  .opp-rank {{ font-size: 1.5em; font-weight: bold; color: #4a7c28; min-width: 35px; }}
  .opp-body {{ flex: 1; }}
  .opp-category {{ font-weight: 600; color: #2d5016; }}
  .opp-desc {{ margin: 5px 0; color: #555; }}
  .opp-meta {{ font-size: 0.85em; color: #888; }}
  .effort-low {{ color: #27ae60; }}
  .effort-medium {{ color: #f39c12; }}
  .effort-high {{ color: #e74c3c; }}
</style>
</head>
<body>
<div class="container">
  <h1>Growth Gap Analysis</h1>
  <p class="subtitle">Nature's Seed — {POST_START.strftime('%b %d')} to {POST_END.strftime('%b %d, %Y')} | Generated {date.today().strftime('%b %d, %Y')}</p>

  <div class="hero">
    <h2>Estimated Opportunity</h2>
    <div class="big-number">${total_est_revenue:,.0f}</div>
    <div class="context">Total estimated additional monthly revenue across {len(opportunities)} identified growth gaps</div>
  </div>

  <!-- Top Priorities -->
  <div class="section">
    <h2>Prioritized Growth Opportunities</h2>
"""

    for i, opp in enumerate(opportunities[:12], 1):
        effort_class = f"effort-{opp['effort']}"
        html += f"""
    <div class="opp-card">
      <div class="opp-rank">#{i}</div>
      <div class="opp-body">
        <div class="opp-category">{opp['category']} <span class="tag tag-{'scale' if 'scal' in opp['category'].lower() else 'fix' if 'fix' in opp['category'].lower() or 'waste' in opp['category'].lower() else 'optimize'}">{opp['channel']}</span></div>
        <div class="opp-desc">{opp['opportunity']}</div>
        <div class="opp-meta">Est. value: <strong>${opp['est_monthly_revenue']:,.0f}</strong> | Effort: <span class="{effort_class}">{opp['effort'].upper()}</span></div>
      </div>
    </div>
"""

    # Channel Performance Grid
    html += """
  </div>

  <div class="section">
    <h2>Channel Performance (Post-Theme Deploy)</h2>
    <table>
      <tr>
        <th>Channel</th>
        <th>Sessions</th>
        <th>Revenue</th>
        <th>CR%</th>
        <th>Rev/Session</th>
        <th>Bounce%</th>
        <th>CR Change</th>
        <th>Rev Change</th>
      </tr>
"""
    for g in sorted(channel_gaps, key=lambda x: x["revenue"], reverse=True):
        cr_class = "up" if g["cr_change_pp"] > 0 else "down"
        rev_class = "up" if g["revenue_change_pct"] > 0 else "down"
        html += f"""
      <tr>
        <td><strong>{g['channel']}</strong></td>
        <td>{g['sessions']:,}</td>
        <td>${g['revenue']:,.0f}</td>
        <td>{g['cr']}%</td>
        <td>${g['rev_per_session']:.2f}</td>
        <td>{g['bounce']}%</td>
        <td class="{cr_class}">{'+' if g['cr_change_pp'] > 0 else ''}{g['cr_change_pp']:.2f}pp</td>
        <td class="{rev_class}">{'+' if g['revenue_change_pct'] > 0 else ''}{g['revenue_change_pct']:.0f}%</td>
      </tr>
"""
    html += """
    </table>
  </div>
"""

    # Device performance
    if devices:
        html += """
  <div class="section">
    <h2>Device Performance</h2>
    <table>
      <tr><th>Device</th><th>Sessions</th><th>Revenue</th><th>CR%</th><th>Bounce%</th><th>Avg Duration</th></tr>
"""
        for d in devices:
            html += f"""
      <tr>
        <td><strong>{d['device'].title()}</strong></td>
        <td>{d['sessions']:,}</td>
        <td>${d['revenue']:,.0f}</td>
        <td>{d['cr']}%</td>
        <td>{d['bounce_rate']}%</td>
        <td>{d['avg_duration']:.0f}s</td>
      </tr>
"""
        html += "    </table>\n"
        if device_gaps:
            for dg in device_gaps:
                html += f'    <p style="color:#e74c3c; margin-top:8px;"><strong>Gap:</strong> {dg["action"]} (est. ${dg["estimated_lost_revenue"]:,.0f} lost revenue)</p>\n'
        html += "  </div>\n"

    # Google Ads Campaign Table
    if campaigns:
        html += """
  <div class="section">
    <h2>Google Ads Campaigns (by Revenue)</h2>
    <table>
      <tr><th>Campaign</th><th>Type</th><th>Spend</th><th>Revenue</th><th>ROAS</th><th>Conv</th><th>CR%</th><th>Action</th></tr>
"""
        for c in campaigns[:20]:
            action_tag = ""
            for op in campaign_ops:
                if op["id"] == c["id"]:
                    tag_class = "tag-scale" if op["action"] == "SCALE" else "tag-fix" if op["action"] == "FIX_OR_PAUSE" else "tag-optimize"
                    action_tag = f'<span class="tag {tag_class}">{op["action"]}</span>'
                    break

            html += f"""
      <tr>
        <td>{c['name'][:45]}</td>
        <td>{c['type']}</td>
        <td>${c['spend']:,.0f}</td>
        <td>${c['conv_value']:,.0f}</td>
        <td><strong>{c['roas']}x</strong></td>
        <td>{c['conversions']}</td>
        <td>{c['cr']}%</td>
        <td>{action_tag}</td>
      </tr>
"""
        html += "    </table>\n  </div>\n"

    # GSC Quick Wins
    if gsc_wins:
        html += """
  <div class="section">
    <h2>SEO Quick Wins — High Impression, Low CTR Queries</h2>
    <p style="color:#666; margin-bottom:10px;">These queries have visibility but aren't getting clicks. Optimizing title tags and meta descriptions for these could capture significant traffic.</p>
    <table>
      <tr><th>Query</th><th>Impressions</th><th>Clicks</th><th>CTR%</th><th>Position</th><th>Potential Clicks</th><th>Priority</th></tr>
"""
        for w in gsc_wins[:20]:
            pri_class = "tag-fix" if w["priority"] == "high" else "tag-optimize"
            html += f"""
      <tr>
        <td>{w['query'][:50]}</td>
        <td>{w['impressions']:,}</td>
        <td>{w['clicks']}</td>
        <td>{w['ctr']}%</td>
        <td>{w['position']}</td>
        <td>+{w['additional_clicks']}</td>
        <td><span class="tag {pri_class}">{w['priority'].upper()}</span></td>
      </tr>
"""
        html += "    </table>\n  </div>\n"

    # Landing Page Gaps
    if landing_pages:
        html += """
  <div class="section">
    <h2>Top Landing Pages — Conversion & Bounce Analysis</h2>
    <table>
      <tr><th>Page</th><th>Sessions</th><th>Revenue</th><th>CR%</th><th>Bounce%</th></tr>
"""
        for p in landing_pages[:20]:
            cr_style = ' style="color:#e74c3c"' if p["cr"] < 1.0 and p["sessions"] > 200 else ""
            bounce_style = ' style="color:#e74c3c"' if p["bounce_rate"] > 50 else ""
            page_short = p["page"].replace("https://naturesseed.com", "").replace("https://www.naturesseed.com", "")[:60]
            html += f"""
      <tr>
        <td>{page_short or '/'}</td>
        <td>{p['sessions']:,}</td>
        <td>${p['revenue']:,.0f}</td>
        <td{cr_style}>{p['cr']}%</td>
        <td{bounce_style}>{p['bounce_rate']}%</td>
      </tr>
"""
        html += "    </table>\n  </div>\n"

    html += """
  <div style="text-align:center; color:#999; margin-top:30px; padding:15px;">
    Generated by Nature's Seed Data Orchestrator | Growth Gap Analysis v1.0
  </div>
</div>
</body>
</html>"""

    return html


# ── Main ─────────────────────────────────────────────────────────────────────

def run():
    """Run the full growth gap analysis."""
    # Load existing attribution data for channel analysis
    attr_path = ROOT / "reports" / "theme_attribution_data.json"
    if attr_path.exists():
        attr_data = json.loads(attr_path.read_text())
        log.info("Loaded theme attribution data")
    else:
        log.error("theme_attribution_data.json not found — run theme_attribution.py first")
        return

    data = {"attribution": attr_data}

    # 1. Analyze channel gaps from existing data
    log.info("Analyzing channel gaps...")
    data["channel_gaps"] = analyze_channel_gaps(attr_data)

    # 2. GSC top queries
    log.info("Pulling GSC top queries...")
    creds = _google_creds()
    sc_client = build("searchconsole", "v1", credentials=creds)
    gsc_queries = pull_gsc_top_queries(sc_client, POST_START, POST_END)
    data["gsc_queries"] = gsc_queries
    data["gsc_quick_wins"] = find_gsc_quick_wins(gsc_queries)
    log.info(f"  Found {len(data['gsc_quick_wins'])} GSC quick wins from {len(gsc_queries)} queries")

    # 3. GSC top pages
    log.info("Pulling GSC top pages...")
    data["gsc_pages"] = pull_gsc_top_pages(sc_client, POST_START, POST_END)

    # 4. Google Ads campaign-level performance
    log.info("Pulling Google Ads campaigns...")
    data["campaigns"] = pull_gads_campaigns(POST_START, POST_END)
    data["campaign_ops"] = find_campaign_scaling_ops(data["campaigns"])
    log.info(f"  Found {len(data['campaign_ops'])} campaign actions from {len(data['campaigns'])} campaigns")

    # 5. Shopping product performance
    log.info("Pulling shopping product performance...")
    try:
        data["shopping_products"] = pull_shopping_products(POST_START, POST_END)
        log.info(f"  Got {len(data['shopping_products'])} product rows")
    except Exception as e:
        log.warning(f"  Shopping products failed: {e}")
        data["shopping_products"] = []

    # 6. GA4 landing pages
    log.info("Pulling GA4 landing pages...")
    ga_client = BetaAnalyticsDataClient(credentials=creds)
    data["landing_pages"] = pull_ga4_landing_pages(ga_client, POST_START, POST_END)
    data["landing_page_gaps"] = find_landing_page_gaps(data["landing_pages"])
    log.info(f"  Found {len(data['landing_page_gaps'])} landing page gaps")

    # 7. GA4 device performance
    log.info("Pulling GA4 device data...")
    data["devices"] = pull_ga4_devices(ga_client, POST_START, POST_END)
    data["device_gaps"] = find_device_gaps(data["devices"])
    log.info(f"  Device gaps: {len(data['device_gaps'])}")

    # 8. Klaviyo flows
    log.info("Pulling Klaviyo flows...")
    data["klaviyo_flows"] = pull_klaviyo_flows()
    log.info(f"  Got {len(data['klaviyo_flows'])} flows")

    # 9. Build prioritized opportunities
    log.info("Building prioritized opportunities...")
    data["opportunities"] = build_opportunities(data)
    log.info(f"  {len(data['opportunities'])} opportunities identified")

    # 10. Generate outputs
    # JSON (exclude large raw data)
    json_data = {k: v for k, v in data.items() if k != "attribution"}
    json_path = ROOT / "reports" / "growth_gaps_data.json"
    json_path.write_text(json.dumps(json_data, indent=2, default=str))
    log.info(f"Saved JSON: {json_path}")

    # HTML report
    html = generate_html_report(data)
    html_path = ROOT / "reports" / "growth_gaps_report.html"
    html_path.write_text(html)
    log.info(f"Saved HTML: {html_path}")

    # Summary
    total_est = sum(o.get("est_monthly_revenue", 0) for o in data["opportunities"])
    log.info(f"\n{'='*60}")
    log.info(f"GROWTH GAP ANALYSIS COMPLETE")
    log.info(f"  Opportunities: {len(data['opportunities'])}")
    log.info(f"  Est. total monthly opportunity: ${total_est:,.0f}")
    log.info(f"  Top 3:")
    for i, o in enumerate(data["opportunities"][:3], 1):
        log.info(f"    {i}. {o['category']} ({o['channel']}) — ${o['est_monthly_revenue']:,.0f}")
    log.info(f"{'='*60}")


if __name__ == "__main__":
    run()
