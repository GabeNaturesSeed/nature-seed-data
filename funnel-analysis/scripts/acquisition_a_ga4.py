#!/usr/bin/env python3
"""
Acquisition Agent A — GA4 Deep-Dive
Pulls 30-day traffic, landing page, device, and funnel data from GA4.

Uses Google Analytics Data API (REST) with OAuth credentials from .env.
GA4 Property ID: 294622924

Usage:
    python3 acquisition_a_ga4.py
"""

import json
import sys
import os
from datetime import date, timedelta
from pathlib import Path

import requests

# ══════════════════════════════════════════════════════════════
# ENV SETUP
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
    for k in [
        "GOOGLE_ADS_CLIENT_ID", "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
    ]:
        if os.environ.get(k):
            env_vars[k] = os.environ[k]

GA4_PROPERTY_ID = "294622924"
TOKEN_URL = "https://oauth2.googleapis.com/token"
GA4_API_BASE = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY_ID}"

# OAuth credentials (shared with Google Ads)
CLIENT_ID = env_vars.get("GOOGLE_ADS_CLIENT_ID", "")
CLIENT_SECRET = env_vars.get("GOOGLE_ADS_CLIENT_SECRET", "")
REFRESH_TOKEN = env_vars.get("GOOGLE_ADS_REFRESH_TOKEN", "")

# Date range
END_DATE = date(2026, 3, 14)
START_DATE = date(2026, 2, 13)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_access_token = None


def get_access_token():
    """Exchange refresh token for an access token."""
    global _access_token
    if _access_token:
        return _access_token

    resp = requests.post(TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }, timeout=15)
    resp.raise_for_status()
    _access_token = resp.json()["access_token"]
    return _access_token


def ga4_run_report(dimensions, metrics, dimension_filter=None, order_bys=None, limit=None):
    """Run a GA4 Data API report."""
    token = get_access_token()
    url = f"{GA4_API_BASE}:runReport"

    body = {
        "dateRanges": [{"startDate": str(START_DATE), "endDate": str(END_DATE)}],
        "dimensions": [{"name": d} for d in dimensions],
        "metrics": [{"name": m} for m in metrics],
    }
    if dimension_filter:
        body["dimensionFilter"] = dimension_filter
    if order_bys:
        body["orderBys"] = order_bys
    if limit:
        body["limit"] = str(limit)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    resp = requests.post(url, headers=headers, json=body, timeout=30)
    if resp.status_code != 200:
        print(f"    [ERR] GA4 API: {resp.status_code} {resp.text[:300]}")
        resp.raise_for_status()

    return resp.json()


def parse_report(response, dimensions, metrics):
    """Parse a GA4 report response into a list of dicts."""
    rows = []
    for row in response.get("rows", []):
        entry = {}
        for i, d in enumerate(dimensions):
            entry[d] = row["dimensionValues"][i]["value"]
        for i, m in enumerate(metrics):
            val = row["metricValues"][i]["value"]
            # Try to convert to number
            try:
                if "." in val:
                    entry[m] = float(val)
                else:
                    entry[m] = int(val)
            except ValueError:
                entry[m] = val
        rows.append(entry)
    return rows


def validate_credentials():
    """Check that all required credentials are present."""
    missing = []
    if not CLIENT_ID:
        missing.append("GOOGLE_ADS_CLIENT_ID")
    if not CLIENT_SECRET:
        missing.append("GOOGLE_ADS_CLIENT_SECRET")
    if not REFRESH_TOKEN:
        missing.append("GOOGLE_ADS_REFRESH_TOKEN")
    if missing:
        print(f"[ERROR] Missing credentials: {missing}")
        return False
    return True


# ══════════════════════════════════════════════════════════════
# DATA PULLS
# ══════════════════════════════════════════════════════════════

def pull_traffic_by_source():
    """Traffic by source/medium."""
    print("\n[1/5] Pulling traffic by source/medium...")

    dims = ["sessionSource", "sessionMedium"]
    mets = ["sessions", "totalUsers", "bounceRate", "averageSessionDuration",
            "conversions", "ecommercePurchases"]

    resp = ga4_run_report(
        dims, mets,
        order_bys=[{"metric": {"metricName": "sessions"}, "desc": True}],
        limit=30,
    )
    results = parse_report(resp, dims, mets)

    total_sessions = sum(r["sessions"] for r in results)
    print(f"    {len(results)} sources | {total_sessions:,} total sessions")
    return results


def pull_landing_pages():
    """Landing page performance."""
    print("\n[2/5] Pulling landing page performance (top 30)...")

    dims = ["landingPage"]
    mets = ["sessions", "totalUsers", "bounceRate", "averageSessionDuration",
            "conversions", "ecommercePurchases", "purchaseRevenue"]

    resp = ga4_run_report(
        dims, mets,
        order_bys=[{"metric": {"metricName": "sessions"}, "desc": True}],
        limit=30,
    )
    results = parse_report(resp, dims, mets)

    # Calculate conversion rate
    for r in results:
        r["conv_rate"] = (r["ecommercePurchases"] / r["sessions"] * 100) if r["sessions"] > 0 else 0

    print(f"    {len(results)} landing pages")
    return results


def pull_device_breakdown():
    """Device category breakdown."""
    print("\n[3/5] Pulling device category breakdown...")

    dims = ["deviceCategory"]
    mets = ["sessions", "totalUsers", "bounceRate", "averageSessionDuration",
            "conversions", "ecommercePurchases", "purchaseRevenue"]

    resp = ga4_run_report(dims, mets)
    results = parse_report(resp, dims, mets)

    for r in results:
        r["conv_rate"] = (r["ecommercePurchases"] / r["sessions"] * 100) if r["sessions"] > 0 else 0

    for r in results:
        print(f"    {r['deviceCategory']}: {r['sessions']:,} sessions, {r['conv_rate']:.2f}% conv rate")

    return results


def pull_new_vs_returning():
    """New vs returning users."""
    print("\n[4/5] Pulling new vs returning users...")

    dims = ["newVsReturning"]
    mets = ["sessions", "totalUsers", "bounceRate", "averageSessionDuration",
            "conversions", "ecommercePurchases", "purchaseRevenue"]

    resp = ga4_run_report(dims, mets)
    results = parse_report(resp, dims, mets)

    for r in results:
        r["conv_rate"] = (r["ecommercePurchases"] / r["sessions"] * 100) if r["sessions"] > 0 else 0

    for r in results:
        print(f"    {r['newVsReturning']}: {r['sessions']:,} sessions, {r['conv_rate']:.2f}% conv rate")

    return results


def pull_ecommerce_funnel():
    """Ecommerce conversion funnel: sessions -> add_to_cart -> begin_checkout -> purchase."""
    print("\n[5/5] Pulling ecommerce funnel...")

    # Get total sessions
    resp_sessions = ga4_run_report([], ["sessions"])
    total_sessions = 0
    for row in resp_sessions.get("rows", []):
        total_sessions = int(row["metricValues"][0]["value"])

    # Get event counts for funnel steps
    funnel_events = ["add_to_cart", "begin_checkout", "purchase"]
    funnel_data = {"sessions": total_sessions}

    for event in funnel_events:
        dims = ["eventName"]
        mets = ["eventCount"]
        dimension_filter = {
            "filter": {
                "fieldName": "eventName",
                "stringFilter": {"matchType": "EXACT", "value": event},
            }
        }
        resp = ga4_run_report(dims, mets, dimension_filter=dimension_filter)
        rows = parse_report(resp, dims, mets)
        funnel_data[event] = rows[0]["eventCount"] if rows else 0

    # Calculate drop-off rates
    steps = ["sessions", "add_to_cart", "begin_checkout", "purchase"]
    funnel_data["dropoffs"] = {}
    for i in range(1, len(steps)):
        prev = funnel_data[steps[i - 1]]
        curr = funnel_data[steps[i]]
        if prev > 0:
            funnel_data["dropoffs"][f"{steps[i-1]}_to_{steps[i]}"] = {
                "from": prev,
                "to": curr,
                "drop_rate": round((1 - curr / prev) * 100, 1),
                "conversion_rate": round(curr / prev * 100, 1),
            }

    print(f"    Sessions: {funnel_data['sessions']:,}")
    print(f"    Add to Cart: {funnel_data['add_to_cart']:,}")
    print(f"    Begin Checkout: {funnel_data['begin_checkout']:,}")
    print(f"    Purchase: {funnel_data['purchase']:,}")
    if total_sessions > 0:
        print(f"    Overall Conversion Rate: {funnel_data['purchase']/total_sessions*100:.2f}%")

    return funnel_data


# ══════════════════════════════════════════════════════════════
# REPORT GENERATION
# ══════════════════════════════════════════════════════════════

def generate_report(traffic, landing_pages, devices, new_returning, funnel):
    """Generate GA4 section of the acquisition report."""
    lines = []
    lines.append("# GA4 Traffic & Conversion Analysis")
    lines.append(f"**Period**: {START_DATE} to {END_DATE} (30 days)")
    lines.append(f"**Property**: {GA4_PROPERTY_ID}")
    lines.append(f"**Generated**: {date.today()}")
    lines.append("")

    # Funnel summary
    lines.append("## Ecommerce Conversion Funnel")
    lines.append("")
    total_sessions = funnel["sessions"]
    lines.append(f"| Stage | Count | % of Sessions | Drop-off |")
    lines.append(f"|-------|-------|---------------|----------|")
    stages = [
        ("Sessions", funnel["sessions"]),
        ("Add to Cart", funnel["add_to_cart"]),
        ("Begin Checkout", funnel["begin_checkout"]),
        ("Purchase", funnel["purchase"]),
    ]
    prev = total_sessions
    for name, count in stages:
        pct = count / total_sessions * 100 if total_sessions > 0 else 0
        drop = f"{(1 - count/prev)*100:.1f}%" if prev > 0 and name != "Sessions" else "-"
        lines.append(f"| {name} | {count:,} | {pct:.1f}% | {drop} |")
        prev = count
    lines.append("")

    # Traffic by source
    lines.append("## Traffic by Source/Medium")
    lines.append("")
    lines.append("| Source | Medium | Sessions | Users | Bounce Rate | Avg Duration | Purchases | Conv Rate |")
    lines.append("|--------|--------|----------|-------|-------------|-------------|-----------|-----------|")
    for r in traffic:
        conv_rate = (r.get("ecommercePurchases", 0) / r["sessions"] * 100) if r["sessions"] > 0 else 0
        bounce = r.get("bounceRate", 0)
        if isinstance(bounce, (int, float)):
            bounce_str = f"{bounce*100:.1f}%" if bounce <= 1 else f"{bounce:.1f}%"
        else:
            bounce_str = str(bounce)
        duration = r.get("averageSessionDuration", 0)
        dur_str = f"{duration:.0f}s" if isinstance(duration, (int, float)) else str(duration)
        lines.append(
            f"| {r['sessionSource'][:20]} | {r['sessionMedium'][:15]} | "
            f"{r['sessions']:,} | {r['totalUsers']:,} | {bounce_str} | "
            f"{dur_str} | {r.get('ecommercePurchases', 0)} | {conv_rate:.2f}% |"
        )
    lines.append("")

    # Device breakdown
    lines.append("## Device Category Performance")
    lines.append("")
    lines.append("| Device | Sessions | Users | Bounce Rate | Purchases | Revenue | Conv Rate |")
    lines.append("|--------|----------|-------|-------------|-----------|---------|-----------|")
    for r in devices:
        bounce = r.get("bounceRate", 0)
        if isinstance(bounce, (int, float)):
            bounce_str = f"{bounce*100:.1f}%" if bounce <= 1 else f"{bounce:.1f}%"
        else:
            bounce_str = str(bounce)
        revenue = r.get("purchaseRevenue", 0)
        lines.append(
            f"| {r['deviceCategory']} | {r['sessions']:,} | {r['totalUsers']:,} | "
            f"{bounce_str} | {r.get('ecommercePurchases', 0)} | "
            f"${revenue:,.2f} | {r['conv_rate']:.2f}% |"
        )
    lines.append("")

    # Conversion rate gap analysis
    if len(devices) > 1:
        best = max(devices, key=lambda x: x["conv_rate"])
        worst = min(devices, key=lambda x: x["conv_rate"])
        gap = best["conv_rate"] - worst["conv_rate"]
        if gap > 0:
            lines.append(f"**Device conversion gap**: {best['deviceCategory']} ({best['conv_rate']:.2f}%) vs "
                        f"{worst['deviceCategory']} ({worst['conv_rate']:.2f}%) — {gap:.2f}pp gap")
            # Estimate lost revenue if worst matched best
            if worst["sessions"] > 0:
                potential_extra_purchases = worst["sessions"] * (best["conv_rate"] - worst["conv_rate"]) / 100
                lines.append(f"If {worst['deviceCategory']} matched {best['deviceCategory']} conv rate: "
                            f"~{potential_extra_purchases:.0f} additional purchases")
            lines.append("")

    # New vs Returning
    lines.append("## New vs Returning Users")
    lines.append("")
    lines.append("| Type | Sessions | Users | Bounce Rate | Purchases | Revenue | Conv Rate |")
    lines.append("|------|----------|-------|-------------|-----------|---------|-----------|")
    for r in new_returning:
        bounce = r.get("bounceRate", 0)
        if isinstance(bounce, (int, float)):
            bounce_str = f"{bounce*100:.1f}%" if bounce <= 1 else f"{bounce:.1f}%"
        else:
            bounce_str = str(bounce)
        revenue = r.get("purchaseRevenue", 0)
        lines.append(
            f"| {r['newVsReturning']} | {r['sessions']:,} | {r['totalUsers']:,} | "
            f"{bounce_str} | {r.get('ecommercePurchases', 0)} | "
            f"${revenue:,.2f} | {r['conv_rate']:.2f}% |"
        )
    lines.append("")

    # Landing Pages
    lines.append("## Top Landing Pages (by Sessions)")
    lines.append("")
    lines.append("| Landing Page | Sessions | Bounce Rate | Purchases | Revenue | Conv Rate |")
    lines.append("|-------------|----------|-------------|-----------|---------|-----------|")
    for r in landing_pages[:30]:
        bounce = r.get("bounceRate", 0)
        if isinstance(bounce, (int, float)):
            bounce_str = f"{bounce*100:.1f}%" if bounce <= 1 else f"{bounce:.1f}%"
        else:
            bounce_str = str(bounce)
        revenue = r.get("purchaseRevenue", 0)
        lines.append(
            f"| {r['landingPage'][:55]} | {r['sessions']:,} | "
            f"{bounce_str} | {r.get('ecommercePurchases', 0)} | "
            f"${revenue:,.2f} | {r['conv_rate']:.2f}% |"
        )
    lines.append("")

    # High-traffic, low-conversion landing pages
    high_traffic_low_conv = [p for p in landing_pages if p["sessions"] >= 50 and p["conv_rate"] < 0.5]
    if high_traffic_low_conv:
        lines.append("### High-Traffic, Low-Conversion Landing Pages (>50 sessions, <0.5% conv)")
        lines.append("")
        for p in sorted(high_traffic_low_conv, key=lambda x: x["sessions"], reverse=True):
            lines.append(f"- **{p['landingPage']}**: {p['sessions']:,} sessions, {p['conv_rate']:.2f}% conv rate")
        lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  ACQUISITION AGENT A — GA4 Analysis")
    print(f"  Period: {START_DATE} to {END_DATE}")
    print(f"  Property: {GA4_PROPERTY_ID}")
    print("=" * 60)

    if not validate_credentials():
        sys.exit(1)

    traffic = pull_traffic_by_source()
    landing_pages = pull_landing_pages()
    devices = pull_device_breakdown()
    new_returning = pull_new_vs_returning()
    funnel = pull_ecommerce_funnel()

    # Generate report
    report = generate_report(traffic, landing_pages, devices, new_returning, funnel)

    output_file = OUTPUT_DIR / "ga4_data.md"
    with open(output_file, "w") as f:
        f.write(report)
    print(f"\n[OK] Report saved to {output_file}")

    # Save raw JSON
    raw_data = {
        "traffic_by_source": traffic,
        "landing_pages": landing_pages,
        "devices": devices,
        "new_vs_returning": new_returning,
        "funnel": funnel,
    }
    json_file = OUTPUT_DIR / "ga4_raw.json"
    with open(json_file, "w") as f:
        json.dump(raw_data, f, indent=2, default=str)
    print(f"[OK] Raw data saved to {json_file}")

    return raw_data


if __name__ == "__main__":
    main()
