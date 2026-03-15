#!/usr/bin/env python3
"""
Google Ads — Campaign-Level Daily Performance Diagnosis
========================================================
Pulls daily campaign-level and account-level metrics from Feb 20 to Mar 15, 2026
to diagnose what happened after March 8.

Usage:
    python3 campaign_daily_diagnosis.py
"""

import os
import sys
from pathlib import Path
from google.ads.googleads.client import GoogleAdsClient

# ── Load .env ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
env_path = PROJECT_ROOT / ".env"

if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip("'\""))

# ── Google Ads client setup ──────────────────────────────────────────────────
CUSTOMER_ID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
LOGIN_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")

config = {
    "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
    "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
    "use_proto_plus": True,
}
if LOGIN_CUSTOMER_ID:
    config["login_customer_id"] = LOGIN_CUSTOMER_ID

client = GoogleAdsClient.load_from_dict(config)
ga_service = client.get_service("GoogleAdsService")


def micros(val):
    return val / 1_000_000


# ══════════════════════════════════════════════════════════════════════════════
# QUERY 1: Campaign-level daily performance
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 120)
print("QUERY 1: CAMPAIGN-LEVEL DAILY PERFORMANCE  (Feb 20 – Mar 15, 2026)")
print("=" * 120)

query1 = """
    SELECT
        segments.date,
        campaign.id,
        campaign.name,
        campaign.status,
        campaign.advertising_channel_type,
        campaign_budget.amount_micros,
        metrics.cost_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.conversions,
        metrics.conversions_value,
        metrics.search_impression_share,
        metrics.ctr,
        metrics.average_cpc
    FROM campaign
    WHERE segments.date BETWEEN '2026-02-20' AND '2026-03-15'
      AND campaign.status != 'REMOVED'
    ORDER BY segments.date, metrics.cost_micros DESC
"""

response1 = ga_service.search(customer_id=CUSTOMER_ID, query=query1)

rows = []
for row in response1:
    rows.append({
        "date": row.segments.date,
        "id": row.campaign.id,
        "name": row.campaign.name,
        "status": row.campaign.status.name,
        "type": row.campaign.advertising_channel_type.name,
        "budget": micros(row.campaign_budget.amount_micros),
        "cost": micros(row.metrics.cost_micros),
        "impr": row.metrics.impressions,
        "clicks": row.metrics.clicks,
        "conv": row.metrics.conversions,
        "rev": row.metrics.conversions_value,
        "is_pct": row.metrics.search_impression_share if row.metrics.search_impression_share else 0,
        "ctr": row.metrics.ctr if row.metrics.ctr else 0,
        "avg_cpc": micros(row.metrics.average_cpc) if row.metrics.average_cpc else 0,
    })

print(f"\nTotal rows returned: {len(rows)}\n")

# Print header
hdr = f"{'Date':<12} {'Campaign':<45} {'Status':<10} {'Type':<12} {'Budget':>8} {'Cost':>10} {'Impr':>8} {'Clicks':>7} {'Conv':>6} {'Revenue':>10} {'ROAS':>6} {'IS%':>6} {'CTR%':>6} {'AvgCPC':>7}"
print(hdr)
print("-" * len(hdr))

current_date = None
daily_cost = 0
daily_rev = 0

for r in rows:
    # Date separator
    if r["date"] != current_date:
        if current_date is not None:
            roas_str = f"{daily_rev/daily_cost:.1f}x" if daily_cost > 0 else "N/A"
            print(f"{'':>12} {'>>> DAY TOTAL':<45} {'':10} {'':12} {'':>8} {daily_cost:>10.2f} {'':>8} {'':>7} {'':>6} {daily_rev:>10.2f} {roas_str:>6}")
            print()
        current_date = r["date"]
        daily_cost = 0
        daily_rev = 0

    daily_cost += r["cost"]
    daily_rev += r["rev"]

    roas = f"{r['rev']/r['cost']:.1f}x" if r["cost"] > 0 else "N/A"
    is_str = f"{r['is_pct']:.1%}" if r["is_pct"] > 0 else "N/A"
    ctr_str = f"{r['ctr']:.2%}" if r["ctr"] > 0 else "N/A"

    name_trunc = r["name"][:43] if len(r["name"]) > 43 else r["name"]
    print(f"{r['date']:<12} {name_trunc:<45} {r['status']:<10} {r['type']:<12} {r['budget']:>8.2f} {r['cost']:>10.2f} {r['impr']:>8} {r['clicks']:>7} {r['conv']:>6.1f} {r['rev']:>10.2f} {roas:>6} {is_str:>6} {ctr_str:>6} {r['avg_cpc']:>7.2f}")

# Final day total
if current_date is not None:
    roas_str = f"{daily_rev/daily_cost:.1f}x" if daily_cost > 0 else "N/A"
    print(f"{'':>12} {'>>> DAY TOTAL':<45} {'':10} {'':12} {'':>8} {daily_cost:>10.2f} {'':>8} {'':>7} {'':>6} {daily_rev:>10.2f} {roas_str:>6}")


# ══════════════════════════════════════════════════════════════════════════════
# QUERY 2: Account-level daily totals
# ══════════════════════════════════════════════════════════════════════════════

print("\n\n")
print("=" * 100)
print("QUERY 2: ACCOUNT-LEVEL DAILY TOTALS  (Feb 20 – Mar 15, 2026)")
print("=" * 100)

query2 = """
    SELECT
        segments.date,
        metrics.cost_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.conversions,
        metrics.conversions_value
    FROM customer
    WHERE segments.date BETWEEN '2026-02-20' AND '2026-03-15'
    ORDER BY segments.date
"""

response2 = ga_service.search(customer_id=CUSTOMER_ID, query=query2)

totals = []
for row in response2:
    totals.append({
        "date": row.segments.date,
        "cost": micros(row.metrics.cost_micros),
        "impr": row.metrics.impressions,
        "clicks": row.metrics.clicks,
        "conv": row.metrics.conversions,
        "rev": row.metrics.conversions_value,
    })

print(f"\nTotal days returned: {len(totals)}\n")

hdr2 = f"{'Date':<12} {'Cost':>10} {'Impressions':>12} {'Clicks':>8} {'Conversions':>12} {'Revenue':>12} {'ROAS':>8} {'CPC':>8} {'CVR%':>8}"
print(hdr2)
print("-" * len(hdr2))

total_cost = 0
total_rev = 0
total_conv = 0

for t in totals:
    roas = f"{t['rev']/t['cost']:.2f}x" if t["cost"] > 0 else "N/A"
    cpc = f"${t['cost']/t['clicks']:.2f}" if t["clicks"] > 0 else "N/A"
    cvr = f"{t['conv']/t['clicks']:.2%}" if t["clicks"] > 0 else "N/A"

    total_cost += t["cost"]
    total_rev += t["rev"]
    total_conv += t["conv"]

    print(f"{t['date']:<12} ${t['cost']:>9.2f} {t['impr']:>12,} {t['clicks']:>8,} {t['conv']:>12.1f} ${t['rev']:>11.2f} {roas:>8} {cpc:>8} {cvr:>8}")

# Grand total
print("-" * len(hdr2))
grand_roas = f"{total_rev/total_cost:.2f}x" if total_cost > 0 else "N/A"
print(f"{'TOTAL':<12} ${total_cost:>9.2f} {'':>12} {'':>8} {total_conv:>12.1f} ${total_rev:>11.2f} {grand_roas:>8}")

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY: Pre vs Post March 8
# ══════════════════════════════════════════════════════════════════════════════

print("\n\n")
print("=" * 80)
print("SUMMARY: PRE vs POST March 8 Comparison")
print("=" * 80)

pre = [t for t in totals if t["date"] <= "2026-03-08"]
post = [t for t in totals if t["date"] > "2026-03-08"]

for label, group in [("Feb 20 – Mar 8 (BEFORE)", pre), ("Mar 9 – Mar 15 (AFTER)", post)]:
    days = len(group)
    if days == 0:
        continue
    g_cost = sum(t["cost"] for t in group)
    g_rev = sum(t["rev"] for t in group)
    g_conv = sum(t["conv"] for t in group)
    g_clicks = sum(t["clicks"] for t in group)
    g_impr = sum(t["impr"] for t in group)

    avg_cost = g_cost / days
    avg_rev = g_rev / days
    avg_conv = g_conv / days
    roas = g_rev / g_cost if g_cost > 0 else 0
    cpc = g_cost / g_clicks if g_clicks > 0 else 0
    cvr = g_conv / g_clicks if g_clicks > 0 else 0

    print(f"\n  {label} ({days} days)")
    print(f"    Total Spend:       ${g_cost:>10,.2f}   (avg ${avg_cost:>8,.2f}/day)")
    print(f"    Total Revenue:     ${g_rev:>10,.2f}   (avg ${avg_rev:>8,.2f}/day)")
    print(f"    Total Conversions: {g_conv:>10.1f}     (avg {avg_conv:>8.1f}/day)")
    print(f"    ROAS:              {roas:>10.2f}x")
    print(f"    Avg CPC:           ${cpc:>9.2f}")
    print(f"    CVR:               {cvr:>10.2%}")
    print(f"    Impressions:       {g_impr:>10,}     (avg {g_impr//days:>8,}/day)")

if pre and post:
    pre_avg_cost = sum(t["cost"] for t in pre) / len(pre)
    post_avg_cost = sum(t["cost"] for t in post) / len(post)
    pre_avg_rev = sum(t["rev"] for t in pre) / len(pre)
    post_avg_rev = sum(t["rev"] for t in post) / len(post)
    pre_roas = sum(t["rev"] for t in pre) / sum(t["cost"] for t in pre) if sum(t["cost"] for t in pre) > 0 else 0
    post_roas = sum(t["rev"] for t in post) / sum(t["cost"] for t in post) if sum(t["cost"] for t in post) > 0 else 0

    print(f"\n  CHANGE:")
    cost_chg = (post_avg_cost - pre_avg_cost) / pre_avg_cost * 100 if pre_avg_cost else 0
    rev_chg = (post_avg_rev - pre_avg_rev) / pre_avg_rev * 100 if pre_avg_rev else 0
    roas_chg = (post_roas - pre_roas) / pre_roas * 100 if pre_roas else 0
    print(f"    Avg Daily Spend:   {cost_chg:>+.1f}%")
    print(f"    Avg Daily Revenue: {rev_chg:>+.1f}%")
    print(f"    ROAS:              {roas_chg:>+.1f}%")

print("\n\nDone.")
