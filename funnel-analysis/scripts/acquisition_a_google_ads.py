#!/usr/bin/env python3
"""
Acquisition Agent A — Google Ads Deep-Dive
Pulls 30-day campaign, keyword, and search term data to identify waste.

Usage:
    python3 acquisition_a_google_ads.py
"""

import json
import sys
import os
from datetime import date, timedelta
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient

# ══════════════════════════════════════════════════════════════
# ENV SETUP (same pattern as daily_pull.py)
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
else:
    print(f"[WARN] .env not found at {env_path}")
    print("       Will try OS environment variables as fallback.")
    # Fallback to OS env
    for k in [
        "GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID", "GOOGLE_ADS_CUSTOMER_ID",
    ]:
        if os.environ.get(k):
            env_vars[k] = os.environ[k]

# Google Ads config
GOOGLE_ADS_CONFIG = {
    "developer_token": env_vars.get("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
    "client_id": env_vars.get("GOOGLE_ADS_CLIENT_ID", ""),
    "client_secret": env_vars.get("GOOGLE_ADS_CLIENT_SECRET", ""),
    "refresh_token": env_vars.get("GOOGLE_ADS_REFRESH_TOKEN", ""),
    "use_proto_plus": True,
}
login_cid = env_vars.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
if login_cid:
    GOOGLE_ADS_CONFIG["login_customer_id"] = login_cid
GOOGLE_ADS_CUSTOMER_ID = env_vars.get("GOOGLE_ADS_CUSTOMER_ID", "5992879586").replace("-", "")

# Date range
END_DATE = date(2026, 3, 14)
START_DATE = date(2026, 2, 13)
SEARCH_TERM_START = END_DATE - timedelta(days=13)  # 14 days for search terms

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def validate_credentials():
    """Check that all required credentials are present."""
    required = ["developer_token", "client_id", "client_secret", "refresh_token"]
    missing = [k for k in required if not GOOGLE_ADS_CONFIG.get(k)]
    if missing:
        print(f"[ERROR] Missing Google Ads credentials: {missing}")
        print("        Ensure .env file exists with GOOGLE_ADS_* variables.")
        return False
    return True


# ══════════════════════════════════════════════════════════════
# QUERIES
# ══════════════════════════════════════════════════════════════

def pull_campaign_performance(ga_service):
    """Campaign-level metrics for the last 30 days."""
    print("\n[1/4] Pulling campaign performance (30 days)...")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            metrics.cost_micros,
            metrics.clicks,
            metrics.impressions,
            metrics.conversions,
            metrics.conversions_value,
            metrics.all_conversions,
            metrics.all_conversions_value
        FROM campaign
        WHERE segments.date BETWEEN '{START_DATE}' AND '{END_DATE}'
          AND campaign.status != 'REMOVED'
    """

    response = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query)

    # Aggregate by campaign
    campaigns = {}
    for row in response:
        cid = row.campaign.id
        if cid not in campaigns:
            campaigns[cid] = {
                "id": cid,
                "name": row.campaign.name,
                "status": row.campaign.status.name,
                "channel_type": row.campaign.advertising_channel_type.name,
                "spend": 0, "clicks": 0, "impressions": 0,
                "conversions": 0, "conv_value": 0,
            }
        c = campaigns[cid]
        c["spend"] += row.metrics.cost_micros / 1_000_000
        c["clicks"] += row.metrics.clicks
        c["impressions"] += row.metrics.impressions
        c["conversions"] += row.metrics.conversions
        c["conv_value"] += row.metrics.conversions_value

    # Calculate derived metrics
    results = []
    for c in campaigns.values():
        c["ctr"] = (c["clicks"] / c["impressions"] * 100) if c["impressions"] > 0 else 0
        c["cpc"] = (c["spend"] / c["clicks"]) if c["clicks"] > 0 else 0
        c["roas"] = (c["conv_value"] / c["spend"]) if c["spend"] > 0 else 0
        c["conv_rate"] = (c["conversions"] / c["clicks"] * 100) if c["clicks"] > 0 else 0
        c["profit"] = c["conv_value"] - c["spend"]
        results.append(c)

    results.sort(key=lambda x: x["spend"], reverse=True)

    print(f"    Found {len(results)} campaigns")
    total_spend = sum(c["spend"] for c in results)
    total_conv_value = sum(c["conv_value"] for c in results)
    print(f"    Total spend: ${total_spend:,.2f} | Total conv value: ${total_conv_value:,.2f} | Overall ROAS: {total_conv_value/total_spend:.2f}x" if total_spend > 0 else "    No spend")

    return results


def pull_keyword_performance(ga_service):
    """Top 50 keywords by spend with ROAS."""
    print("\n[2/4] Pulling keyword performance (top 50 by spend)...")

    query = f"""
        SELECT
            campaign.name,
            ad_group.name,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            metrics.cost_micros,
            metrics.clicks,
            metrics.impressions,
            metrics.conversions,
            metrics.conversions_value
        FROM keyword_view
        WHERE segments.date BETWEEN '{START_DATE}' AND '{END_DATE}'
          AND campaign.status != 'REMOVED'
          AND ad_group.status != 'REMOVED'
        ORDER BY metrics.cost_micros DESC
        LIMIT 200
    """

    response = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query)

    # Aggregate by keyword text (may appear across ad groups)
    keywords = {}
    for row in response:
        kw_text = row.ad_group_criterion.keyword.text
        key = f"{kw_text}|{row.campaign.name}"
        if key not in keywords:
            keywords[key] = {
                "keyword": kw_text,
                "match_type": row.ad_group_criterion.keyword.match_type.name,
                "campaign": row.campaign.name,
                "ad_group": row.ad_group.name,
                "spend": 0, "clicks": 0, "impressions": 0,
                "conversions": 0, "conv_value": 0,
            }
        k = keywords[key]
        k["spend"] += row.metrics.cost_micros / 1_000_000
        k["clicks"] += row.metrics.clicks
        k["impressions"] += row.metrics.impressions
        k["conversions"] += row.metrics.conversions
        k["conv_value"] += row.metrics.conversions_value

    results = []
    for k in keywords.values():
        k["roas"] = (k["conv_value"] / k["spend"]) if k["spend"] > 0 else 0
        k["cpc"] = (k["spend"] / k["clicks"]) if k["clicks"] > 0 else 0
        k["conv_rate"] = (k["conversions"] / k["clicks"] * 100) if k["clicks"] > 0 else 0
        results.append(k)

    results.sort(key=lambda x: x["spend"], reverse=True)
    results = results[:50]

    wasted = [k for k in results if k["conversions"] == 0 and k["spend"] > 0]
    wasted_spend = sum(k["spend"] for k in wasted)
    print(f"    Top 50 keywords: ${sum(k['spend'] for k in results):,.2f} total spend")
    print(f"    Zero-conversion keywords: {len(wasted)} | Wasted: ${wasted_spend:,.2f}")

    return results


def pull_search_terms(ga_service):
    """Search term report for the last 14 days."""
    print("\n[3/4] Pulling search term report (14 days)...")

    query = f"""
        SELECT
            campaign.name,
            search_term_view.search_term,
            search_term_view.status,
            metrics.cost_micros,
            metrics.clicks,
            metrics.impressions,
            metrics.conversions,
            metrics.conversions_value
        FROM search_term_view
        WHERE segments.date BETWEEN '{SEARCH_TERM_START}' AND '{END_DATE}'
          AND campaign.status != 'REMOVED'
        ORDER BY metrics.cost_micros DESC
        LIMIT 500
    """

    response = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query)

    results = []
    for row in response:
        spend = row.metrics.cost_micros / 1_000_000
        results.append({
            "search_term": row.search_term_view.search_term,
            "campaign": row.campaign.name,
            "status": row.search_term_view.status.name,
            "spend": spend,
            "clicks": row.metrics.clicks,
            "impressions": row.metrics.impressions,
            "conversions": row.metrics.conversions,
            "conv_value": row.metrics.conversions_value,
            "roas": (row.metrics.conversions_value / spend) if spend > 0 else 0,
        })

    wasted = [s for s in results if s["conversions"] == 0 and s["spend"] > 0]
    wasted_spend = sum(s["spend"] for s in wasted)
    print(f"    Search terms: {len(results)} | Zero-conv terms: {len(wasted)} | Wasted: ${wasted_spend:,.2f}")

    return results


def pull_daily_trends(ga_service):
    """Daily spend/CPC/conversion trends for the 30-day window."""
    print("\n[4/4] Pulling daily trends (30 days)...")

    query = f"""
        SELECT
            segments.date,
            metrics.cost_micros,
            metrics.clicks,
            metrics.impressions,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date BETWEEN '{START_DATE}' AND '{END_DATE}'
          AND campaign.status != 'REMOVED'
    """

    response = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query)

    days = {}
    for row in response:
        d = row.segments.date
        if d not in days:
            days[d] = {"date": d, "spend": 0, "clicks": 0, "impressions": 0, "conversions": 0, "conv_value": 0}
        days[d]["spend"] += row.metrics.cost_micros / 1_000_000
        days[d]["clicks"] += row.metrics.clicks
        days[d]["impressions"] += row.metrics.impressions
        days[d]["conversions"] += row.metrics.conversions
        days[d]["conv_value"] += row.metrics.conversions_value

    results = []
    for d in sorted(days.values(), key=lambda x: x["date"]):
        d["cpc"] = (d["spend"] / d["clicks"]) if d["clicks"] > 0 else 0
        d["roas"] = (d["conv_value"] / d["spend"]) if d["spend"] > 0 else 0
        d["conv_rate"] = (d["conversions"] / d["clicks"] * 100) if d["clicks"] > 0 else 0
        results.append(d)

    if results:
        avg_cpc = sum(d["cpc"] for d in results) / len(results)
        avg_roas = sum(d["roas"] for d in results) / len(results)
        print(f"    {len(results)} days | Avg CPC: ${avg_cpc:.2f} | Avg ROAS: {avg_roas:.2f}x")

    return results


# ══════════════════════════════════════════════════════════════
# REPORT GENERATION
# ══════════════════════════════════════════════════════════════

def generate_report(campaigns, keywords, search_terms, daily_trends):
    """Generate markdown report from collected data."""

    total_spend = sum(c["spend"] for c in campaigns)
    total_conv_value = sum(c["conv_value"] for c in campaigns)
    total_conversions = sum(c["conversions"] for c in campaigns)
    total_clicks = sum(c["clicks"] for c in campaigns)
    total_impressions = sum(c["impressions"] for c in campaigns)
    overall_roas = total_conv_value / total_spend if total_spend > 0 else 0
    overall_cpc = total_spend / total_clicks if total_clicks > 0 else 0
    overall_ctr = total_clicks / total_impressions * 100 if total_impressions > 0 else 0
    overall_conv_rate = total_conversions / total_clicks * 100 if total_clicks > 0 else 0

    # Identify money-losing campaigns
    losing_campaigns = [c for c in campaigns if c["profit"] < 0]
    losing_spend = sum(c["spend"] for c in losing_campaigns)
    losing_loss = sum(abs(c["profit"]) for c in losing_campaigns)

    # Wasted keyword spend (keywords with spend but 0 conversions)
    wasted_keywords = [k for k in keywords if k["conversions"] == 0 and k["spend"] > 0]
    wasted_kw_spend = sum(k["spend"] for k in wasted_keywords)

    # Wasted search term spend
    wasted_terms = [s for s in search_terms if s["conversions"] == 0 and s["spend"] > 0]
    wasted_term_spend = sum(s["spend"] for s in wasted_terms)

    # CPC trend
    if len(daily_trends) >= 7:
        first_week_cpc = sum(d["cpc"] for d in daily_trends[:7]) / 7
        last_week_cpc = sum(d["cpc"] for d in daily_trends[-7:]) / 7
        cpc_trend = ((last_week_cpc - first_week_cpc) / first_week_cpc * 100) if first_week_cpc > 0 else 0
    else:
        first_week_cpc = last_week_cpc = cpc_trend = 0

    lines = []
    lines.append("# Google Ads Acquisition Analysis")
    lines.append(f"**Period**: {START_DATE} to {END_DATE} (30 days)")
    lines.append(f"**Generated**: {date.today()}")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Total Spend**: ${total_spend:,.2f}")
    lines.append(f"- **Total Conversion Value**: ${total_conv_value:,.2f}")
    lines.append(f"- **Overall ROAS**: {overall_roas:.2f}x")
    lines.append(f"- **Total Conversions**: {total_conversions:.1f}")
    lines.append(f"- **Total Clicks**: {total_clicks:,}")
    lines.append(f"- **Total Impressions**: {total_impressions:,}")
    lines.append(f"- **Average CPC**: ${overall_cpc:.2f}")
    lines.append(f"- **Overall CTR**: {overall_ctr:.2f}%")
    lines.append(f"- **Overall Conversion Rate**: {overall_conv_rate:.2f}%")
    lines.append("")

    # Waste Summary
    lines.append("## Waste Identified")
    lines.append("")
    total_waste = wasted_kw_spend + wasted_term_spend
    lines.append(f"| Category | Amount |")
    lines.append(f"|----------|--------|")
    lines.append(f"| Money-losing campaigns (ROAS < 1x) | ${losing_spend:,.2f} spent, ${losing_loss:,.2f} net loss |")
    lines.append(f"| Zero-conversion keywords (top 50) | ${wasted_kw_spend:,.2f} |")
    lines.append(f"| Zero-conversion search terms (14d) | ${wasted_term_spend:,.2f} |")
    lines.append("")

    # Campaign Performance
    lines.append("## Campaign Performance (Ranked by Spend)")
    lines.append("")
    lines.append("| Campaign | Spend | Conv Value | ROAS | Conversions | CPC | CTR | Conv Rate | Profit/Loss |")
    lines.append("|----------|-------|-----------|------|-------------|-----|-----|-----------|-------------|")
    for c in campaigns:
        flag = " !!!" if c["profit"] < 0 else ""
        lines.append(
            f"| {c['name'][:40]} | ${c['spend']:,.2f} | ${c['conv_value']:,.2f} | "
            f"{c['roas']:.2f}x | {c['conversions']:.1f} | ${c['cpc']:.2f} | "
            f"{c['ctr']:.2f}% | {c['conv_rate']:.2f}% | "
            f"{'${:,.2f}'.format(c['profit'])}{flag} |"
        )
    lines.append("")

    # Money-Losing Campaigns Detail
    if losing_campaigns:
        lines.append("### Money-Losing Campaigns (ROAS < 1x)")
        lines.append("")
        for c in sorted(losing_campaigns, key=lambda x: x["profit"]):
            lines.append(f"- **{c['name']}**: Spent ${c['spend']:,.2f}, returned ${c['conv_value']:,.2f} "
                        f"(ROAS {c['roas']:.2f}x) — **${abs(c['profit']):,.2f} net loss**")
        lines.append("")

    # Top Keywords
    lines.append("## Top 50 Keywords by Spend")
    lines.append("")
    lines.append("| Keyword | Match | Campaign | Spend | Conv | ROAS | CPC | Conv Rate |")
    lines.append("|---------|-------|----------|-------|------|------|-----|-----------|")
    for k in keywords[:50]:
        flag = " [WASTE]" if k["conversions"] == 0 else ""
        lines.append(
            f"| {k['keyword'][:35]} | {k['match_type']} | {k['campaign'][:25]} | "
            f"${k['spend']:,.2f} | {k['conversions']:.1f} | {k['roas']:.2f}x | "
            f"${k['cpc']:.2f} | {k['conv_rate']:.1f}%{flag} |"
        )
    lines.append("")

    # Wasted Keywords
    if wasted_keywords:
        lines.append("### Zero-Conversion Keywords (Wasted Spend)")
        lines.append("")
        lines.append(f"**Total wasted on zero-conversion keywords**: ${wasted_kw_spend:,.2f}")
        lines.append("")
        for k in sorted(wasted_keywords, key=lambda x: x["spend"], reverse=True)[:20]:
            lines.append(f"- `{k['keyword']}` ({k['match_type']}) in *{k['campaign']}*: "
                        f"${k['spend']:,.2f} spent, {k['clicks']} clicks, 0 conversions")
        lines.append("")

    # Search Terms
    lines.append("## Search Term Analysis (14 Days)")
    lines.append("")

    # Top converting search terms
    converting_terms = [s for s in search_terms if s["conversions"] > 0]
    converting_terms.sort(key=lambda x: x["conv_value"], reverse=True)

    if converting_terms:
        lines.append("### Top Converting Search Terms")
        lines.append("")
        lines.append("| Search Term | Campaign | Spend | Conv Value | ROAS | Conversions |")
        lines.append("|-------------|----------|-------|-----------|------|-------------|")
        for s in converting_terms[:20]:
            lines.append(
                f"| {s['search_term'][:40]} | {s['campaign'][:25]} | "
                f"${s['spend']:,.2f} | ${s['conv_value']:,.2f} | "
                f"{s['roas']:.2f}x | {s['conversions']:.1f} |"
            )
        lines.append("")

    # Top wasted search terms
    wasted_terms.sort(key=lambda x: x["spend"], reverse=True)
    if wasted_terms:
        lines.append("### Top Wasted Search Terms (Spend with 0 Conversions)")
        lines.append("")
        lines.append(f"**Total wasted**: ${wasted_term_spend:,.2f} across {len(wasted_terms)} terms")
        lines.append("")
        lines.append("| Search Term | Campaign | Spend | Clicks |")
        lines.append("|-------------|----------|-------|--------|")
        for s in wasted_terms[:30]:
            lines.append(
                f"| {s['search_term'][:45]} | {s['campaign'][:25]} | "
                f"${s['spend']:,.2f} | {s['clicks']} |"
            )
        lines.append("")

    # CPC Trends
    lines.append("## CPC & ROAS Trends (Daily)")
    lines.append("")
    if cpc_trend:
        direction = "increasing" if cpc_trend > 0 else "decreasing"
        lines.append(f"CPC trend: **{direction}** — first week avg ${first_week_cpc:.2f} vs last week ${last_week_cpc:.2f} ({cpc_trend:+.1f}%)")
        lines.append("")

    lines.append("| Date | Spend | Clicks | CPC | ROAS | Conv Rate |")
    lines.append("|------|-------|--------|-----|------|-----------|")
    for d in daily_trends:
        lines.append(
            f"| {d['date']} | ${d['spend']:,.2f} | {d['clicks']:,} | "
            f"${d['cpc']:.2f} | {d['roas']:.2f}x | {d['conv_rate']:.1f}% |"
        )
    lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  ACQUISITION AGENT A — Google Ads Analysis")
    print(f"  Period: {START_DATE} to {END_DATE}")
    print("=" * 60)

    if not validate_credentials():
        sys.exit(1)

    client = GoogleAdsClient.load_from_dict(GOOGLE_ADS_CONFIG)
    ga_service = client.get_service("GoogleAdsService")

    # Pull all data
    campaigns = pull_campaign_performance(ga_service)
    keywords = pull_keyword_performance(ga_service)
    search_terms = pull_search_terms(ga_service)
    daily_trends = pull_daily_trends(ga_service)

    # Generate report
    report = generate_report(campaigns, keywords, search_terms, daily_trends)

    # Save report section
    output_file = OUTPUT_DIR / "google_ads_data.md"
    with open(output_file, "w") as f:
        f.write(report)
    print(f"\n[OK] Report saved to {output_file}")

    # Also save raw JSON for downstream use
    raw_data = {
        "campaigns": campaigns,
        "keywords": keywords,
        "search_terms": search_terms[:100],  # Limit for file size
        "daily_trends": daily_trends,
        "summary": {
            "total_spend": sum(c["spend"] for c in campaigns),
            "total_conv_value": sum(c["conv_value"] for c in campaigns),
            "total_conversions": sum(c["conversions"] for c in campaigns),
            "overall_roas": sum(c["conv_value"] for c in campaigns) / max(sum(c["spend"] for c in campaigns), 0.01),
            "wasted_keyword_spend": sum(k["spend"] for k in keywords if k["conversions"] == 0),
            "wasted_search_term_spend": sum(s["spend"] for s in search_terms if s["conversions"] == 0),
        },
    }
    json_file = OUTPUT_DIR / "google_ads_raw.json"
    with open(json_file, "w") as f:
        json.dump(raw_data, f, indent=2, default=str)
    print(f"[OK] Raw data saved to {json_file}")

    # Print summary to stdout for capture
    print("\n" + "=" * 60)
    print("  GOOGLE ADS SUMMARY")
    print("=" * 60)
    s = raw_data["summary"]
    print(f"  Total Spend:          ${s['total_spend']:,.2f}")
    print(f"  Total Conv Value:     ${s['total_conv_value']:,.2f}")
    print(f"  Overall ROAS:         {s['overall_roas']:.2f}x")
    print(f"  Wasted KW Spend:      ${s['wasted_keyword_spend']:,.2f}")
    print(f"  Wasted Search Terms:  ${s['wasted_search_term_spend']:,.2f}")

    return raw_data


if __name__ == "__main__":
    main()
