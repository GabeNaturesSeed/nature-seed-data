#!/usr/bin/env python3
"""
Google Ads Performance Diagnosis — Post March 8, 2026
=====================================================
Deep dive into what changed after the Cycle 1 drip changes on March 9.

Run locally with: python google-ads-audit/diagnose_post_march8.py

Outputs:
  1. Account-level daily totals (Feb 20 - Mar 15)
  2. Campaign-level daily breakdown
  3. Change history / audit log from Google Ads API
  4. Search term comparison (before vs after Mar 8)
  5. Keyword-level daily performance
  6. Shopping product performance comparison
  7. Supabase daily_ad_spend data correlation
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ── Load .env ────────────────────────────────────────────────────────────────
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

CUSTOMER_ID = env.get("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")
LOGIN_CID = env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")

GOOGLE_ADS_CONFIG = {
    "developer_token": env.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
    "client_id": env.get("GOOGLE_ADS_CLIENT_ID"),
    "client_secret": env.get("GOOGLE_ADS_CLIENT_SECRET"),
    "refresh_token": env.get("GOOGLE_ADS_REFRESH_TOKEN"),
    "use_proto_plus": True,
}
if LOGIN_CID:
    GOOGLE_ADS_CONFIG["login_customer_id"] = LOGIN_CID

from google.ads.googleads.client import GoogleAdsClient

client = GoogleAdsClient.load_from_dict(GOOGLE_ADS_CONFIG)
ga_service = client.get_service("GoogleAdsService")

# ── Date ranges ──────────────────────────────────────────────────────────────
BEFORE_START = "2026-02-20"
BEFORE_END = "2026-03-07"
AFTER_START = "2026-03-08"
AFTER_END = "2026-03-15"
FULL_START = BEFORE_START
FULL_END = AFTER_END

def micros_to_dollars(micros):
    return round(micros / 1_000_000, 2)

def safe_roas(revenue, cost):
    return round(revenue / cost, 2) if cost > 0 else 0.0

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: Account-Level Daily Totals
# ══════════════════════════════════════════════════════════════════════════════
def section_1_account_daily():
    print("\n" + "=" * 80)
    print("SECTION 1: ACCOUNT-LEVEL DAILY PERFORMANCE")
    print("=" * 80)

    query = f"""
        SELECT
            segments.date,
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value
        FROM customer
        WHERE segments.date BETWEEN '{FULL_START}' AND '{FULL_END}'
        ORDER BY segments.date
    """
    response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
    rows = list(response)

    before_totals = {"spend": 0, "imp": 0, "clicks": 0, "conv": 0, "rev": 0, "days": 0}
    after_totals = {"spend": 0, "imp": 0, "clicks": 0, "conv": 0, "rev": 0, "days": 0}

    print(f"\n{'Date':<12} {'Spend':>10} {'Impr':>10} {'Clicks':>8} {'Conv':>8} {'Revenue':>12} {'ROAS':>8} {'CPC':>8} {'CTR':>7}")
    print("-" * 95)

    for row in rows:
        date = row.segments.date
        spend = micros_to_dollars(row.metrics.cost_micros)
        imp = row.metrics.impressions
        clicks = row.metrics.clicks
        conv = round(row.metrics.conversions, 1)
        rev = round(row.metrics.conversions_value, 2)
        roas = safe_roas(rev, spend)
        cpc = round(spend / clicks, 2) if clicks > 0 else 0
        ctr = round(clicks / imp * 100, 2) if imp > 0 else 0

        marker = " ◄ CYCLE 1" if date == "2026-03-09" else ""
        marker = " ◄ CUTOFF" if date == "2026-03-08" else marker

        print(f"{date:<12} ${spend:>9,.2f} {imp:>10,} {clicks:>8,} {conv:>8} ${rev:>11,.2f} {roas:>7}x ${cpc:>7} {ctr:>6}%{marker}")

        bucket = after_totals if date >= "2026-03-08" else before_totals
        bucket["spend"] += spend
        bucket["imp"] += imp
        bucket["clicks"] += clicks
        bucket["conv"] += conv
        bucket["rev"] += rev
        bucket["days"] += 1

    print("\n--- PERIOD COMPARISON ---")
    for label, t in [("BEFORE (Feb 20 - Mar 7)", before_totals), ("AFTER  (Mar 8 - Mar 15)", after_totals)]:
        days = t["days"] or 1
        avg_spend = t["spend"] / days
        avg_rev = t["rev"] / days
        roas = safe_roas(t["rev"], t["spend"])
        print(f"\n{label}:")
        print(f"  Days: {days}")
        print(f"  Total spend: ${t['spend']:,.2f}  |  Avg/day: ${avg_spend:,.2f}")
        print(f"  Total revenue: ${t['rev']:,.2f}  |  Avg/day: ${avg_rev:,.2f}")
        print(f"  Total conversions: {t['conv']}")
        print(f"  ROAS: {roas}x")
        print(f"  Avg CPC: ${t['spend'] / t['clicks']:.2f}" if t["clicks"] else "  Avg CPC: N/A")

    if before_totals["days"] and after_totals["days"]:
        b_avg = before_totals["spend"] / before_totals["days"]
        a_avg = after_totals["spend"] / after_totals["days"]
        spend_chg = ((a_avg - b_avg) / b_avg) * 100 if b_avg else 0
        b_roas = safe_roas(before_totals["rev"], before_totals["spend"])
        a_roas = safe_roas(after_totals["rev"], after_totals["spend"])
        roas_chg = ((a_roas - b_roas) / b_roas) * 100 if b_roas else 0
        print(f"\n  >>> Daily spend change: {spend_chg:+.1f}%")
        print(f"  >>> ROAS change: {roas_chg:+.1f}% ({b_roas}x → {a_roas}x)")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: Campaign-Level Daily Breakdown
# ══════════════════════════════════════════════════════════════════════════════
def section_2_campaign_daily():
    print("\n" + "=" * 80)
    print("SECTION 2: CAMPAIGN-LEVEL DAILY PERFORMANCE")
    print("=" * 80)

    query = f"""
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
            metrics.search_impression_share
        FROM campaign
        WHERE segments.date BETWEEN '{FULL_START}' AND '{FULL_END}'
          AND campaign.status != 'REMOVED'
        ORDER BY segments.date, metrics.cost_micros DESC
    """
    response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
    rows = list(response)

    # Group by campaign for before/after comparison
    campaign_periods = defaultdict(lambda: {
        "before": {"spend": 0, "rev": 0, "conv": 0, "imp": 0, "clicks": 0, "days": set()},
        "after": {"spend": 0, "rev": 0, "conv": 0, "imp": 0, "clicks": 0, "days": set()}
    })

    current_date = None
    for row in rows:
        date = row.segments.date
        if date != current_date:
            current_date = date
            print(f"\n--- {date} ---")
            print(f"  {'Campaign':<40} {'Spend':>10} {'Impr':>8} {'Clicks':>7} {'Conv':>6} {'Revenue':>10} {'ROAS':>7} {'IS%':>6} {'Budget':>10}")

        name = row.campaign.name[:40]
        spend = micros_to_dollars(row.metrics.cost_micros)
        imp = row.metrics.impressions
        clicks = row.metrics.clicks
        conv = round(row.metrics.conversions, 1)
        rev = round(row.metrics.conversions_value, 2)
        roas = safe_roas(rev, spend)
        is_pct = round(row.metrics.search_impression_share * 100, 1) if row.metrics.search_impression_share else 0
        budget = micros_to_dollars(row.campaign_budget.amount_micros) if row.campaign_budget.amount_micros else 0

        if spend > 0:
            print(f"  {name:<40} ${spend:>9,.2f} {imp:>8,} {clicks:>7,} {conv:>6} ${rev:>9,.2f} {roas:>6}x {is_pct:>5}% ${budget:>9,.2f}")

        period = "after" if date >= "2026-03-08" else "before"
        cp = campaign_periods[row.campaign.name][period]
        cp["spend"] += spend
        cp["rev"] += rev
        cp["conv"] += conv
        cp["imp"] += imp
        cp["clicks"] += clicks
        cp["days"].add(date)

    # Summary comparison by campaign
    print("\n\n" + "=" * 80)
    print("CAMPAIGN BEFORE vs AFTER COMPARISON")
    print("=" * 80)
    print(f"\n{'Campaign':<40} {'Period':<8} {'Days':>4} {'Avg$/d':>10} {'Avg Rev/d':>12} {'ROAS':>7} {'Avg Conv/d':>10}")
    print("-" * 100)

    for cname in sorted(campaign_periods.keys()):
        for period_label, period_key in [("BEFORE", "before"), ("AFTER", "after")]:
            p = campaign_periods[cname][period_key]
            days = len(p["days"]) or 1
            avg_spend = p["spend"] / days
            avg_rev = p["rev"] / days
            avg_conv = p["conv"] / days
            roas = safe_roas(p["rev"], p["spend"])
            if p["spend"] > 0:
                print(f"  {cname[:38]:<40} {period_label:<8} {days:>4} ${avg_spend:>9,.2f} ${avg_rev:>11,.2f} {roas:>6}x {avg_conv:>10.1f}")
        print()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Change History / Audit Log
# ══════════════════════════════════════════════════════════════════════════════
def section_3_change_history():
    print("\n" + "=" * 80)
    print("SECTION 3: GOOGLE ADS CHANGE HISTORY (March 1-15)")
    print("=" * 80)

    query = f"""
        SELECT
            change_event.change_date_time,
            change_event.change_resource_type,
            change_event.client_type,
            change_event.user_email,
            change_event.resource_change_operation,
            change_event.changed_fields
        FROM change_event
        WHERE change_event.change_date_time >= '2026-03-01 00:00:00'
          AND change_event.change_date_time <= '2026-03-15 23:59:59'
        ORDER BY change_event.change_date_time DESC
        LIMIT 500
    """
    try:
        response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
        rows = list(response)
        print(f"\nFound {len(rows)} change events:\n")
        print(f"{'Timestamp':<25} {'Resource Type':<25} {'Operation':<12} {'Client':<20} {'User':<30} {'Changed Fields'}")
        print("-" * 150)
        for row in rows:
            ts = str(row.change_event.change_date_time)[:24]
            res_type = str(row.change_event.change_resource_type).replace("ChangeClientType.", "").replace("ResourceChangeOperation.", "")
            operation = str(row.change_event.resource_change_operation)
            client = str(row.change_event.client_type)
            user = str(row.change_event.user_email) if row.change_event.user_email else "—"
            fields = str(row.change_event.changed_fields)[:60] if row.change_event.changed_fields else "—"
            print(f"{ts:<25} {res_type:<25} {operation:<12} {client:<20} {user:<30} {fields}")
    except Exception as e:
        print(f"\n⚠️  change_event query failed: {e}")
        print("Trying change_status instead...\n")
        try:
            query2 = f"""
                SELECT
                    change_status.last_change_date_time,
                    change_status.resource_type,
                    change_status.resource_status,
                    change_status.campaign,
                    change_status.ad_group
                FROM change_status
                WHERE change_status.last_change_date_time >= '2026-03-01'
                  AND change_status.last_change_date_time <= '2026-03-16'
                ORDER BY change_status.last_change_date_time DESC
                LIMIT 300
            """
            response2 = ga_service.search(customer_id=CUSTOMER_ID, query=query2)
            rows2 = list(response2)
            print(f"Found {len(rows2)} change_status entries:\n")
            for row in rows2:
                print(f"  {row.change_status.last_change_date_time} | "
                      f"Type: {row.change_status.resource_type} | "
                      f"Status: {row.change_status.resource_status} | "
                      f"Campaign: {row.change_status.campaign} | "
                      f"AdGroup: {row.change_status.ad_group}")
        except Exception as e2:
            print(f"⚠️  change_status also failed: {e2}")
            print("Change history not available via API. Check Google Ads UI → Change History.")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: Search Term Comparison
# ══════════════════════════════════════════════════════════════════════════════
def section_4_search_terms():
    print("\n" + "=" * 80)
    print("SECTION 4: SEARCH TERM COMPARISON (Before vs After Mar 8)")
    print("=" * 80)

    for label, start, end in [("BEFORE (Feb 20 - Mar 7)", BEFORE_START, BEFORE_END),
                               ("AFTER  (Mar 8 - Mar 15)", AFTER_START, AFTER_END)]:
        print(f"\n--- {label} ---")
        query = f"""
            SELECT
                search_term_view.search_term,
                campaign.name,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.clicks,
                metrics.impressions
            FROM search_term_view
            WHERE segments.date BETWEEN '{start}' AND '{end}'
              AND campaign.status != 'REMOVED'
              AND metrics.cost_micros > 0
            ORDER BY metrics.cost_micros DESC
            LIMIT 40
        """
        response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
        rows = list(response)
        print(f"\n  {'Search Term':<45} {'Campaign':<30} {'Spend':>8} {'Clicks':>6} {'Conv':>6} {'Revenue':>10} {'ROAS':>7}")
        print("  " + "-" * 120)
        for row in rows:
            term = row.search_term_view.search_term[:44]
            camp = row.campaign.name[:29]
            spend = micros_to_dollars(row.metrics.cost_micros)
            clicks = row.metrics.clicks
            conv = round(row.metrics.conversions, 1)
            rev = round(row.metrics.conversions_value, 2)
            roas = safe_roas(rev, spend)
            print(f"  {term:<45} {camp:<30} ${spend:>7,.2f} {clicks:>6} {conv:>6} ${rev:>9,.2f} {roas:>6}x")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: Keyword-Level Daily Performance
# ══════════════════════════════════════════════════════════════════════════════
def section_5_keywords():
    print("\n" + "=" * 80)
    print("SECTION 5: KEYWORD PERFORMANCE (Before vs After)")
    print("=" * 80)

    for label, start, end in [("BEFORE (Feb 20 - Mar 7)", BEFORE_START, BEFORE_END),
                               ("AFTER  (Mar 8 - Mar 15)", AFTER_START, AFTER_END)]:
        print(f"\n--- {label} ---")
        query = f"""
            SELECT
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                campaign.name,
                ad_group.name,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.conversions_value
            FROM keyword_view
            WHERE segments.date BETWEEN '{start}' AND '{end}'
              AND campaign.status != 'REMOVED'
              AND metrics.cost_micros > 0
            ORDER BY metrics.cost_micros DESC
            LIMIT 40
        """
        response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
        rows = list(response)
        print(f"\n  {'Keyword':<35} {'Match':<8} {'Status':<8} {'Campaign':<25} {'Spend':>8} {'Conv':>6} {'Revenue':>10} {'ROAS':>7}")
        print("  " + "-" * 115)
        for row in rows:
            kw = row.ad_group_criterion.keyword.text[:34]
            match = str(row.ad_group_criterion.keyword.match_type).split(".")[-1][:7]
            status = str(row.ad_group_criterion.status).split(".")[-1][:7]
            camp = row.campaign.name[:24]
            spend = micros_to_dollars(row.metrics.cost_micros)
            conv = round(row.metrics.conversions, 1)
            rev = round(row.metrics.conversions_value, 2)
            roas = safe_roas(rev, spend)
            print(f"  {kw:<35} {match:<8} {status:<8} {camp:<25} ${spend:>7,.2f} {conv:>6} ${rev:>9,.2f} {roas:>6}x")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6: Shopping Product Performance
# ══════════════════════════════════════════════════════════════════════════════
def section_6_shopping():
    print("\n" + "=" * 80)
    print("SECTION 6: SHOPPING PRODUCT PERFORMANCE (Before vs After)")
    print("=" * 80)

    for label, start, end in [("BEFORE (Feb 20 - Mar 7)", BEFORE_START, BEFORE_END),
                               ("AFTER  (Mar 8 - Mar 15)", AFTER_START, AFTER_END)]:
        print(f"\n--- {label} ---")
        query = f"""
            SELECT
                segments.product_item_id,
                segments.product_title,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.clicks,
                metrics.impressions
            FROM shopping_performance_view
            WHERE segments.date BETWEEN '{start}' AND '{end}'
              AND metrics.cost_micros > 0
            ORDER BY metrics.cost_micros DESC
            LIMIT 30
        """
        response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
        rows = list(response)
        print(f"\n  {'Product':<55} {'Spend':>8} {'Clicks':>6} {'Conv':>6} {'Revenue':>10} {'ROAS':>7}")
        print("  " + "-" * 100)
        for row in rows:
            title = row.segments.product_title[:54]
            spend = micros_to_dollars(row.metrics.cost_micros)
            clicks = row.metrics.clicks
            conv = round(row.metrics.conversions, 1)
            rev = round(row.metrics.conversions_value, 2)
            roas = safe_roas(rev, spend)
            print(f"  {title:<55} ${spend:>7,.2f} {clicks:>6} {conv:>6} ${rev:>9,.2f} {roas:>6}x")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7: Supabase Daily Data (if available)
# ══════════════════════════════════════════════════════════════════════════════
def section_7_supabase():
    print("\n" + "=" * 80)
    print("SECTION 7: SUPABASE DAILY DATA CORRELATION")
    print("=" * 80)

    import requests
    sb_url = env.get("SUPABASE_URL", "")
    sb_key = env.get("SUPABASE_SECRET_API_KEY", "") or env.get("SUPABASE_ANON_KEY", "")

    if not sb_url or not sb_key:
        print("\n⚠️  Supabase credentials not found in .env. Skipping.")
        return

    headers = {"apikey": sb_key, "Content-Type": "application/json"}
    base = f"{sb_url}/rest/v1"

    for table in ["daily_ad_spend", "daily_sales", "daily_summary"]:
        print(f"\n--- {table} (Feb 20 - Mar 15) ---")
        url = f"{base}/{table}?select=*&report_date=gte.2026-02-20&report_date=lte.2026-03-15&order=report_date"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    print(f"  {len(data)} rows returned")
                    for row in data:
                        print(f"  {json.dumps(row)}")
                else:
                    print("  No data returned")
            else:
                print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8: Conversion Action Audit
# ══════════════════════════════════════════════════════════════════════════════
def section_8_conversions():
    print("\n" + "=" * 80)
    print("SECTION 8: CONVERSION ACTION AUDIT")
    print("=" * 80)

    query = """
        SELECT
            conversion_action.id,
            conversion_action.name,
            conversion_action.category,
            conversion_action.type,
            conversion_action.status,
            conversion_action.include_in_conversions_metric,
            conversion_action.counting_type
        FROM conversion_action
        WHERE conversion_action.status = 'ENABLED'
        ORDER BY conversion_action.name
    """
    try:
        response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
        rows = list(response)
        print(f"\n{'Name':<40} {'Category':<20} {'Type':<15} {'Primary?':<10} {'Counting':<15}")
        print("-" * 105)
        for row in rows:
            name = str(row.conversion_action.name)[:39]
            cat = str(row.conversion_action.category).split(".")[-1][:19]
            typ = str(row.conversion_action.type).split(".")[-1][:14]
            primary = "YES" if row.conversion_action.include_in_conversions_metric else "no"
            counting = str(row.conversion_action.counting_type).split(".")[-1][:14]
            print(f"{name:<40} {cat:<20} {typ:<15} {primary:<10} {counting:<15}")
    except Exception as e:
        print(f"⚠️  Conversion audit failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9: Ad Group Level Daily (most granular)
# ══════════════════════════════════════════════════════════════════════════════
def section_9_adgroup_daily():
    print("\n" + "=" * 80)
    print("SECTION 9: AD GROUP DAILY PERFORMANCE (Mar 1-15)")
    print("=" * 80)

    query = f"""
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
          AND metrics.cost_micros > 0
        ORDER BY segments.date, metrics.cost_micros DESC
    """
    response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
    rows = list(response)

    current_date = None
    for row in rows:
        date = row.segments.date
        if date != current_date:
            current_date = date
            marker = " ◄◄ CYCLE 1" if date == "2026-03-09" else ""
            print(f"\n--- {date}{marker} ---")
            print(f"  {'Campaign':<30} {'Ad Group':<30} {'Spend':>8} {'Impr':>7} {'Clicks':>6} {'Conv':>6} {'Revenue':>10} {'ROAS':>7}")
            print("  " + "-" * 110)

        camp = row.campaign.name[:29]
        ag = row.ad_group.name[:29]
        spend = micros_to_dollars(row.metrics.cost_micros)
        imp = row.metrics.impressions
        clicks = row.metrics.clicks
        conv = round(row.metrics.conversions, 1)
        rev = round(row.metrics.conversions_value, 2)
        roas = safe_roas(rev, spend)
        if spend >= 1:  # Skip <$1 noise
            print(f"  {camp:<30} {ag:<30} ${spend:>7,.2f} {imp:>7,} {clicks:>6} {conv:>6} ${rev:>9,.2f} {roas:>6}x")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 80)
    print("GOOGLE ADS PERFORMANCE DIAGNOSIS — POST MARCH 8, 2026")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Account: {CUSTOMER_ID}")
    print(f"Analysis: {FULL_START} to {FULL_END}")
    print("=" * 80)

    sections = [
        ("1", section_1_account_daily),
        ("2", section_2_campaign_daily),
        ("3", section_3_change_history),
        ("4", section_4_search_terms),
        ("5", section_5_keywords),
        ("6", section_6_shopping),
        ("7", section_7_supabase),
        ("8", section_8_conversions),
        ("9", section_9_adgroup_daily),
    ]

    # Allow running specific sections: python diagnose_post_march8.py 1 3 5
    requested = sys.argv[1:] if len(sys.argv) > 1 else [s[0] for s in sections]

    for num, func in sections:
        if num in requested:
            try:
                func()
            except Exception as e:
                print(f"\n⚠️  Section {num} failed: {e}")
                import traceback
                traceback.print_exc()

    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)
    print("\nTo save output: python diagnose_post_march8.py > diagnosis_report.txt 2>&1")
    print("To run specific sections: python diagnose_post_march8.py 1 3 5")
