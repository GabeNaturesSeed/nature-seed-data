#!/usr/bin/env python3
"""
Google Ads Diagnostic: Before vs After March 8, 2026
=====================================================
Compares search term, ad group, and keyword performance between:
  BEFORE: Feb 20 - Mar 7, 2026
  AFTER:  Mar 8 - Mar 15, 2026

Usage:
  python3 diagnose_mar8.py

Requires .env in project root with Google Ads credentials.
"""

import sys
from pathlib import Path
from collections import defaultdict

from google.ads.googleads.client import GoogleAdsClient

# ── Load .env ───────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]

def _load_env():
    env = {}
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        print(f"ERROR: .env not found at {env_file}")
        sys.exit(1)
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip().strip("'\"")
    return env

env = _load_env()

CUSTOMER_ID = env.get("GOOGLE_ADS_CUSTOMER_ID", "5992879586").replace("-", "")
LOGIN_CID = env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "8386194588").replace("-", "")

credentials = {
    "developer_token": env["GOOGLE_ADS_DEVELOPER_TOKEN"],
    "client_id": env["GOOGLE_ADS_CLIENT_ID"],
    "client_secret": env["GOOGLE_ADS_CLIENT_SECRET"],
    "refresh_token": env["GOOGLE_ADS_REFRESH_TOKEN"],
    "login_customer_id": LOGIN_CID,
    "use_proto_plus": True,
}
client = GoogleAdsClient.load_from_dict(credentials)
ga_service = client.get_service("GoogleAdsService")


def run_query(query):
    """Execute a GAQL query and return raw rows."""
    return list(ga_service.search(customer_id=CUSTOMER_ID, query=query))


def fmt_dollar(micros):
    return micros / 1_000_000


# ════════════════════════════════════════════════════════════════════════════
# QUERY A: Search terms BEFORE (Feb 20 - Mar 7)
# ════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("QUERY A: Search Terms BEFORE (Feb 20 - Mar 7, 2026)")
print("=" * 80)

query_before = """
    SELECT
        search_term_view.search_term,
        campaign.name,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value,
        metrics.clicks,
        metrics.impressions
    FROM search_term_view
    WHERE segments.date BETWEEN '2026-02-20' AND '2026-03-07'
      AND campaign.status != 'REMOVED'
      AND metrics.cost_micros > 0
    ORDER BY metrics.cost_micros DESC
    LIMIT 50
"""

rows_before = run_query(query_before)
before_terms = {}

print(f"\n{'Rank':>4} | {'Search Term':<50} | {'Campaign':<30} | {'Cost':>10} | {'Conv':>6} | {'Revenue':>10} | {'Clicks':>7} | {'Impr':>7} | {'ROAS':>6}")
print("-" * 145)

for i, row in enumerate(rows_before, 1):
    term = row.search_term_view.search_term
    cost = fmt_dollar(row.metrics.cost_micros)
    rev = row.metrics.conversions_value
    roas = rev / cost if cost > 0 else 0
    before_terms[term] = {
        "cost": cost,
        "conversions": row.metrics.conversions,
        "revenue": rev,
        "clicks": row.metrics.clicks,
        "impressions": row.metrics.impressions,
        "campaign": row.campaign.name,
    }
    print(f"{i:>4} | {term:<50} | {row.campaign.name:<30} | ${cost:>9.2f} | {row.metrics.conversions:>6.1f} | ${rev:>9.2f} | {row.metrics.clicks:>7} | {row.metrics.impressions:>7} | {roas:>5.1f}x")

print(f"\nTotal BEFORE terms returned: {len(rows_before)}")
total_before_cost = sum(v["cost"] for v in before_terms.values())
total_before_rev = sum(v["revenue"] for v in before_terms.values())
total_before_conv = sum(v["conversions"] for v in before_terms.values())
print(f"Total cost (top 50): ${total_before_cost:,.2f}")
print(f"Total revenue (top 50): ${total_before_rev:,.2f}")
print(f"Total conversions (top 50): {total_before_conv:.1f}")
print(f"Blended ROAS (top 50): {total_before_rev / total_before_cost:.2f}x" if total_before_cost > 0 else "")


# ════════════════════════════════════════════════════════════════════════════
# QUERY B: Search terms AFTER (Mar 8 - Mar 15)
# ════════════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 80)
print("QUERY B: Search Terms AFTER (Mar 8 - Mar 15, 2026)")
print("=" * 80)

query_after = """
    SELECT
        search_term_view.search_term,
        campaign.name,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value,
        metrics.clicks,
        metrics.impressions
    FROM search_term_view
    WHERE segments.date BETWEEN '2026-03-08' AND '2026-03-15'
      AND campaign.status != 'REMOVED'
      AND metrics.cost_micros > 0
    ORDER BY metrics.cost_micros DESC
    LIMIT 50
"""

rows_after = run_query(query_after)
after_terms = {}

print(f"\n{'Rank':>4} | {'Search Term':<50} | {'Campaign':<30} | {'Cost':>10} | {'Conv':>6} | {'Revenue':>10} | {'Clicks':>7} | {'Impr':>7} | {'ROAS':>6}")
print("-" * 145)

for i, row in enumerate(rows_after, 1):
    term = row.search_term_view.search_term
    cost = fmt_dollar(row.metrics.cost_micros)
    rev = row.metrics.conversions_value
    roas = rev / cost if cost > 0 else 0
    after_terms[term] = {
        "cost": cost,
        "conversions": row.metrics.conversions,
        "revenue": rev,
        "clicks": row.metrics.clicks,
        "impressions": row.metrics.impressions,
        "campaign": row.campaign.name,
    }
    print(f"{i:>4} | {term:<50} | {row.campaign.name:<30} | ${cost:>9.2f} | {row.metrics.conversions:>6.1f} | ${rev:>9.2f} | {row.metrics.clicks:>7} | {row.metrics.impressions:>7} | {roas:>5.1f}x")

print(f"\nTotal AFTER terms returned: {len(rows_after)}")
total_after_cost = sum(v["cost"] for v in after_terms.values())
total_after_rev = sum(v["revenue"] for v in after_terms.values())
total_after_conv = sum(v["conversions"] for v in after_terms.values())
print(f"Total cost (top 50): ${total_after_cost:,.2f}")
print(f"Total revenue (top 50): ${total_after_rev:,.2f}")
print(f"Total conversions (top 50): {total_after_conv:.1f}")
print(f"Blended ROAS (top 50): {total_after_rev / total_after_cost:.2f}x" if total_after_cost > 0 else "")


# ════════════════════════════════════════════════════════════════════════════
# COMPARISON: Before vs After
# ════════════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 80)
print("COMPARISON: Search Term Changes (Before vs After Mar 8)")
print("=" * 80)

# New terms (appeared after Mar 8 but not before)
new_terms = set(after_terms.keys()) - set(before_terms.keys())
disappeared_terms = set(before_terms.keys()) - set(after_terms.keys())
common_terms = set(before_terms.keys()) & set(after_terms.keys())

print(f"\n--- NEW Search Terms (appeared AFTER Mar 8, not in BEFORE top 50) ---")
print(f"Count: {len(new_terms)}")
if new_terms:
    new_sorted = sorted(new_terms, key=lambda t: after_terms[t]["cost"], reverse=True)
    print(f"\n{'Search Term':<50} | {'Campaign':<30} | {'Cost':>10} | {'Conv':>6} | {'Revenue':>10} | {'ROAS':>6}")
    print("-" * 125)
    for term in new_sorted:
        d = after_terms[term]
        roas = d["revenue"] / d["cost"] if d["cost"] > 0 else 0
        print(f"{term:<50} | {d['campaign']:<30} | ${d['cost']:>9.2f} | {d['conversions']:>6.1f} | ${d['revenue']:>9.2f} | {roas:>5.1f}x")

print(f"\n--- DISAPPEARED Search Terms (in BEFORE top 50, gone from AFTER top 50) ---")
print(f"Count: {len(disappeared_terms)}")
if disappeared_terms:
    dis_sorted = sorted(disappeared_terms, key=lambda t: before_terms[t]["cost"], reverse=True)
    print(f"\n{'Search Term':<50} | {'Campaign':<30} | {'Cost':>10} | {'Conv':>6} | {'Revenue':>10} | {'ROAS':>6}")
    print("-" * 125)
    for term in dis_sorted:
        d = before_terms[term]
        roas = d["revenue"] / d["cost"] if d["cost"] > 0 else 0
        print(f"{term:<50} | {d['campaign']:<30} | ${d['cost']:>9.2f} | {d['conversions']:>6.1f} | ${d['revenue']:>9.2f} | {roas:>5.1f}x")

print(f"\n--- SPEND SHIFT for Common Terms ---")
print(f"Terms in both periods: {len(common_terms)}")
if common_terms:
    # Normalize: BEFORE is 16 days, AFTER is 8 days
    before_days = 16
    after_days = 8
    shifts = []
    for term in common_terms:
        b = before_terms[term]
        a = after_terms[term]
        daily_before = b["cost"] / before_days
        daily_after = a["cost"] / after_days
        shift_pct = ((daily_after - daily_before) / daily_before * 100) if daily_before > 0 else 999
        roas_before = b["revenue"] / b["cost"] if b["cost"] > 0 else 0
        roas_after = a["revenue"] / a["cost"] if a["cost"] > 0 else 0
        shifts.append({
            "term": term,
            "daily_before": daily_before,
            "daily_after": daily_after,
            "shift_pct": shift_pct,
            "roas_before": roas_before,
            "roas_after": roas_after,
            "cost_before": b["cost"],
            "cost_after": a["cost"],
        })

    shifts.sort(key=lambda x: abs(x["shift_pct"]), reverse=True)
    print(f"\n{'Search Term':<45} | {'Daily Before':>12} | {'Daily After':>12} | {'Shift %':>8} | {'ROAS Bef':>9} | {'ROAS Aft':>9}")
    print("-" * 110)
    for s in shifts[:30]:
        print(f"{s['term']:<45} | ${s['daily_before']:>10.2f} | ${s['daily_after']:>10.2f} | {s['shift_pct']:>+7.0f}% | {s['roas_before']:>8.1f}x | {s['roas_after']:>8.1f}x")


# ════════════════════════════════════════════════════════════════════════════
# QUERY C: Ad Group Daily Performance (Mar 1 - Mar 15)
# ════════════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 80)
print("QUERY C: Ad Group Daily Performance (Mar 1 - Mar 15, 2026)")
print("=" * 80)

query_adgroup = """
    SELECT
        segments.date,
        campaign.name,
        ad_group.name,
        ad_group.status,
        metrics.cost_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.conversions,
        metrics.conversions_value
    FROM ad_group
    WHERE segments.date BETWEEN '2026-03-01' AND '2026-03-15'
      AND campaign.status != 'REMOVED'
      AND ad_group.status != 'REMOVED'
    ORDER BY segments.date, metrics.cost_micros DESC
"""

rows_adgroup = run_query(query_adgroup)

print(f"\nTotal rows: {len(rows_adgroup)}")
print(f"\n{'Date':<12} | {'Campaign':<30} | {'Ad Group':<35} | {'Status':<10} | {'Cost':>10} | {'Impr':>7} | {'Clicks':>7} | {'Conv':>6} | {'Revenue':>10}")
print("-" * 170)

# Aggregate by date for summary
daily_totals = defaultdict(lambda: {"cost": 0, "impressions": 0, "clicks": 0, "conversions": 0, "revenue": 0})

for row in rows_adgroup:
    dt = row.segments.date
    cost = fmt_dollar(row.metrics.cost_micros)
    rev = row.metrics.conversions_value
    status = row.ad_group.status.name if hasattr(row.ad_group.status, 'name') else str(row.ad_group.status)

    daily_totals[dt]["cost"] += cost
    daily_totals[dt]["impressions"] += row.metrics.impressions
    daily_totals[dt]["clicks"] += row.metrics.clicks
    daily_totals[dt]["conversions"] += row.metrics.conversions
    daily_totals[dt]["revenue"] += rev

    # Print individual rows only if they had spend
    if cost > 0:
        print(f"{dt:<12} | {row.campaign.name:<30} | {row.ad_group.name:<35} | {status:<10} | ${cost:>9.2f} | {row.metrics.impressions:>7} | {row.metrics.clicks:>7} | {row.metrics.conversions:>6.1f} | ${rev:>9.2f}")

print(f"\n--- Daily Totals ---")
print(f"{'Date':<12} | {'Cost':>10} | {'Impr':>7} | {'Clicks':>7} | {'Conv':>6} | {'Revenue':>10} | {'ROAS':>6}")
print("-" * 75)
for dt in sorted(daily_totals.keys()):
    d = daily_totals[dt]
    roas = d["revenue"] / d["cost"] if d["cost"] > 0 else 0
    marker = " <<<" if dt >= "2026-03-08" else ""
    print(f"{dt:<12} | ${d['cost']:>9.2f} | {d['impressions']:>7} | {d['clicks']:>7} | {d['conversions']:>6.1f} | ${d['revenue']:>9.2f} | {roas:>5.1f}x{marker}")

# Before vs After summary
before_agg = {"cost": 0, "impressions": 0, "clicks": 0, "conversions": 0, "revenue": 0}
after_agg = {"cost": 0, "impressions": 0, "clicks": 0, "conversions": 0, "revenue": 0}
for dt, d in daily_totals.items():
    target = after_agg if dt >= "2026-03-08" else before_agg
    for k in target:
        target[k] += d[k]

print(f"\n--- Period Summary (from daily totals) ---")
before_days_c = len([d for d in daily_totals if d < "2026-03-08"])
after_days_c = len([d for d in daily_totals if d >= "2026-03-08"])
print(f"BEFORE (Mar 1-7, {before_days_c} days): Cost=${before_agg['cost']:,.2f}, Rev=${before_agg['revenue']:,.2f}, Conv={before_agg['conversions']:.1f}, ROAS={before_agg['revenue']/before_agg['cost']:.2f}x" if before_agg['cost'] > 0 else "BEFORE: no spend")
print(f"AFTER  (Mar 8-15, {after_days_c} days): Cost=${after_agg['cost']:,.2f}, Rev=${after_agg['revenue']:,.2f}, Conv={after_agg['conversions']:.1f}, ROAS={after_agg['revenue']/after_agg['cost']:.2f}x" if after_agg['cost'] > 0 else "AFTER: no spend")

if before_agg["cost"] > 0 and after_agg["cost"] > 0 and before_days_c > 0 and after_days_c > 0:
    daily_cost_before = before_agg["cost"] / before_days_c
    daily_cost_after = after_agg["cost"] / after_days_c
    daily_rev_before = before_agg["revenue"] / before_days_c
    daily_rev_after = after_agg["revenue"] / after_days_c
    print(f"\nDaily avg cost:  BEFORE=${daily_cost_before:.2f} -> AFTER=${daily_cost_after:.2f} ({(daily_cost_after-daily_cost_before)/daily_cost_before*100:+.1f}%)")
    print(f"Daily avg rev:   BEFORE=${daily_rev_before:.2f} -> AFTER=${daily_rev_after:.2f} ({(daily_rev_after-daily_rev_before)/daily_rev_before*100:+.1f}%)")


# ════════════════════════════════════════════════════════════════════════════
# QUERY D: Keyword-Level Performance (Mar 1 - Mar 15)
# ════════════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 80)
print("QUERY D: Keyword-Level Performance (Mar 1 - Mar 15, 2026)")
print("=" * 80)

query_keywords = """
    SELECT
        segments.date,
        campaign.name,
        ad_group.name,
        ad_group_criterion.keyword.text,
        ad_group_criterion.keyword.match_type,
        ad_group_criterion.status,
        ad_group_criterion.quality_info.quality_score,
        metrics.cost_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.conversions,
        metrics.conversions_value,
        metrics.average_cpc,
        metrics.search_impression_share
    FROM keyword_view
    WHERE segments.date BETWEEN '2026-03-01' AND '2026-03-15'
      AND campaign.status != 'REMOVED'
      AND metrics.cost_micros > 0
    ORDER BY segments.date, metrics.cost_micros DESC
    LIMIT 500
"""

rows_kw = run_query(query_keywords)

print(f"\nTotal keyword rows: {len(rows_kw)}")
print(f"\n{'Date':<12} | {'Campaign':<25} | {'Ad Group':<25} | {'Keyword':<30} | {'Match':>7} | {'QS':>3} | {'Cost':>10} | {'Impr':>7} | {'Clicks':>6} | {'Conv':>5} | {'Rev':>10} | {'Avg CPC':>8} | {'IS':>6}")
print("-" * 195)

# Aggregate keyword data for before/after comparison
kw_before = defaultdict(lambda: {"cost": 0, "clicks": 0, "impressions": 0, "conversions": 0, "revenue": 0, "days": set()})
kw_after = defaultdict(lambda: {"cost": 0, "clicks": 0, "impressions": 0, "conversions": 0, "revenue": 0, "days": set()})

for row in rows_kw:
    dt = row.segments.date
    cost = fmt_dollar(row.metrics.cost_micros)
    rev = row.metrics.conversions_value
    avg_cpc = fmt_dollar(row.metrics.average_cpc)
    match_type = row.ad_group_criterion.keyword.match_type.name if hasattr(row.ad_group_criterion.keyword.match_type, 'name') else str(row.ad_group_criterion.keyword.match_type)
    status = row.ad_group_criterion.status.name if hasattr(row.ad_group_criterion.status, 'name') else str(row.ad_group_criterion.status)
    qs = row.ad_group_criterion.quality_info.quality_score if row.ad_group_criterion.quality_info.quality_score else 0
    imp_share = row.metrics.search_impression_share if row.metrics.search_impression_share else 0

    kw_key = (row.ad_group_criterion.keyword.text, row.campaign.name, match_type)
    target = kw_after if dt >= "2026-03-08" else kw_before
    target[kw_key]["cost"] += cost
    target[kw_key]["clicks"] += row.metrics.clicks
    target[kw_key]["impressions"] += row.metrics.impressions
    target[kw_key]["conversions"] += row.metrics.conversions
    target[kw_key]["revenue"] += rev
    target[kw_key]["days"].add(dt)

    print(f"{dt:<12} | {row.campaign.name:<25} | {row.ad_group.name:<25} | {row.ad_group_criterion.keyword.text:<30} | {match_type:>7} | {qs:>3} | ${cost:>9.2f} | {row.metrics.impressions:>7} | {row.metrics.clicks:>6} | {row.metrics.conversions:>5.1f} | ${rev:>9.2f} | ${avg_cpc:>7.2f} | {imp_share:>5.1%}")


# Keyword-level before/after comparison
print(f"\n\n--- Keyword Before vs After Comparison ---")
print(f"(Normalized to daily averages: Before=Mar 1-7, After=Mar 8-15)")

all_kw_keys = set(kw_before.keys()) | set(kw_after.keys())
kw_comparison = []

for kw_key in all_kw_keys:
    b = kw_before.get(kw_key, {"cost": 0, "clicks": 0, "impressions": 0, "conversions": 0, "revenue": 0, "days": set()})
    a = kw_after.get(kw_key, {"cost": 0, "clicks": 0, "impressions": 0, "conversions": 0, "revenue": 0, "days": set()})

    b_days = max(len(b["days"]), 1)
    a_days = max(len(a["days"]), 1)

    daily_cost_b = b["cost"] / b_days if b["cost"] > 0 else 0
    daily_cost_a = a["cost"] / a_days if a["cost"] > 0 else 0

    cost_change = ((daily_cost_a - daily_cost_b) / daily_cost_b * 100) if daily_cost_b > 0 else (999 if daily_cost_a > 0 else 0)
    roas_b = b["revenue"] / b["cost"] if b["cost"] > 0 else 0
    roas_a = a["revenue"] / a["cost"] if a["cost"] > 0 else 0

    kw_comparison.append({
        "keyword": kw_key[0],
        "campaign": kw_key[1],
        "match": kw_key[2],
        "cost_before": b["cost"],
        "cost_after": a["cost"],
        "daily_cost_before": daily_cost_b,
        "daily_cost_after": daily_cost_a,
        "cost_change_pct": cost_change,
        "roas_before": roas_b,
        "roas_after": roas_a,
        "conv_before": b["conversions"],
        "conv_after": a["conversions"],
        "is_new": b["cost"] == 0 and a["cost"] > 0,
        "disappeared": b["cost"] > 0 and a["cost"] == 0,
    })

# Sort by absolute cost change
kw_comparison.sort(key=lambda x: abs(x["cost_change_pct"]) * max(x["cost_before"], x["cost_after"]), reverse=True)

print(f"\n{'Keyword':<30} | {'Campaign':<25} | {'Match':>7} | {'Cost Bef':>9} | {'Cost Aft':>9} | {'Chg %':>7} | {'ROAS B':>7} | {'ROAS A':>7} | {'Note':<10}")
print("-" * 155)
for kw in kw_comparison[:40]:
    note = ""
    if kw["is_new"]:
        note = "NEW"
    elif kw["disappeared"]:
        note = "GONE"
    elif kw["cost_change_pct"] > 50:
        note = "UP"
    elif kw["cost_change_pct"] < -50:
        note = "DOWN"
    print(f"{kw['keyword']:<30} | {kw['campaign']:<25} | {kw['match']:>7} | ${kw['cost_before']:>8.2f} | ${kw['cost_after']:>8.2f} | {kw['cost_change_pct']:>+6.0f}% | {kw['roas_before']:>6.1f}x | {kw['roas_after']:>6.1f}x | {note:<10}")

# Summary stats
new_kws = [k for k in kw_comparison if k["is_new"]]
gone_kws = [k for k in kw_comparison if k["disappeared"]]
print(f"\nKeywords NEW after Mar 8: {len(new_kws)}")
for kw in sorted(new_kws, key=lambda x: x["cost_after"], reverse=True)[:10]:
    print(f"  {kw['keyword']:<30} ({kw['campaign']}) - ${kw['cost_after']:.2f} spend, {kw['roas_after']:.1f}x ROAS")

print(f"\nKeywords DISAPPEARED after Mar 8: {len(gone_kws)}")
for kw in sorted(gone_kws, key=lambda x: x["cost_before"], reverse=True)[:10]:
    print(f"  {kw['keyword']:<30} ({kw['campaign']}) - was ${kw['cost_before']:.2f} spend, {kw['roas_before']:.1f}x ROAS")

print("\n\n" + "=" * 80)
print("DONE — Diagnostic complete.")
print("=" * 80)
