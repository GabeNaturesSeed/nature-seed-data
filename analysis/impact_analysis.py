#!/usr/bin/env python3
"""
Nature's Seed — Impact Analysis: Before vs After Changes (~Feb 26)

Compares 2-week windows across all data sources to attribute impact
of: new theme, Algolia search fix, Amazon launch, and other changes.

Sends formatted results to Telegram.

Usage:
  python3 impact_analysis.py                          # Default Feb 26 cutoff
  python3 impact_analysis.py 2026-02-26               # Custom cutoff date
  python3 impact_analysis.py 2026-02-26 --no-telegram # Print only
"""

import json
import sys
import time
import os
import html
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict

import requests
from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric, OrderBy
)
from googleapiclient.discovery import build


# ══════════════════════════════════════════════════════════════
# ENV SETUP
# ══════════════════════════════════════════════════════════════

env_path = Path(__file__).resolve().parent.parent / ".env"
env_vars = {}
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip().strip("'\"")

# Fall back to OS env vars (for GitHub Actions)
def env(key, default=""):
    return env_vars.get(key) or os.environ.get(key, default)

SUPABASE_URL = env("SUPABASE_URL")
SUPABASE_KEY = env("SUPABASE_SECRET_API_KEY")
GA_PROPERTY = env("GOOGLE_ANALYTICS_PROPERTY_ID", "294622924")
TELEGRAM_TOKEN = env("TELEGRAM_BOT_TOKEN") or env("TELEGRAM_BOT_API")
TELEGRAM_CHAT_ID = env("TELEGRAM_CHAT_ID")

google_creds = Credentials(
    token=None,
    refresh_token=env("GOOGLE_ADS_REFRESH_TOKEN"),
    client_id=env("GOOGLE_ADS_CLIENT_ID"),
    client_secret=env("GOOGLE_ADS_CLIENT_SECRET"),
    token_uri="https://oauth2.googleapis.com/token",
)


# ══════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════

def send_telegram(text, parse_mode="HTML"):
    MAX_LEN = 4096
    chunks = []
    if len(text) <= MAX_LEN:
        chunks = [text]
    else:
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > MAX_LEN:
                if current:
                    chunks.append(current)
                current = line
            else:
                current = current + "\n" + line if current else line
        if current:
            chunks.append(current)

    for chunk in chunks:
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req) as resp:
                resp.read()
        except urllib.error.HTTPError as e:
            print(f"[WARN] Telegram send failed: {e.code} {e.read().decode()[:200]}")
        time.sleep(0.3)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def pct_change(before, after):
    if before == 0:
        return float("inf") if after > 0 else 0.0
    return ((after - before) / before) * 100

def fmt_pct(val):
    if val == float("inf"):
        return "NEW"
    return f"{val:+.0f}%"

def fmt_money(val):
    return f"${val:,.0f}"


# ══════════════════════════════════════════════════════════════
# 1. SUPABASE — Daily P&L
# ══════════════════════════════════════════════════════════════

def pull_supabase(before_start, before_end, after_start, after_end):
    """Pull daily_summary and daily_sales for before/after comparison."""
    print("Pulling Supabase daily_summary...")
    headers = {"apikey": SUPABASE_KEY}

    # Daily summary (aggregated P&L)
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/daily_summary",
        headers=headers,
        params={"report_date": f"gte.{before_start}", "order": "report_date.asc", "limit": 100},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  [ERR] daily_summary: {resp.status_code}")
        return None, None

    before = {"revenue": 0, "orders": 0, "units": 0, "ad_spend": 0, "cogs": 0, "shipping": 0, "days": 0}
    after = {"revenue": 0, "orders": 0, "units": 0, "ad_spend": 0, "cogs": 0, "shipping": 0, "days": 0}

    for row in resp.json():
        d = row.get("report_date", "")
        if d < before_start or d > after_end:
            continue
        bucket = before if d <= before_end else after
        bucket["revenue"] += float(row.get("total_revenue", 0) or 0)
        bucket["orders"] += int(row.get("total_orders", 0) or 0)
        bucket["units"] += int(row.get("total_units", 0) or 0)
        bucket["ad_spend"] += float(row.get("total_ad_spend", 0) or 0)
        bucket["cogs"] += float(row.get("total_cogs", 0) or 0)
        bucket["shipping"] += float(row.get("shipping_cost", 0) or 0)
        bucket["days"] += 1

    print(f"  Before: {before['days']} days, After: {after['days']} days")

    # Channel breakdown
    resp2 = requests.get(
        f"{SUPABASE_URL}/rest/v1/daily_sales",
        headers=headers,
        params={"report_date": f"gte.{before_start}", "order": "report_date.asc", "limit": 300},
        timeout=30,
    )
    channels = defaultdict(lambda: {"before": {"revenue": 0, "orders": 0}, "after": {"revenue": 0, "orders": 0}})
    if resp2.status_code == 200:
        for row in resp2.json():
            d = row.get("report_date", "")
            ch = row.get("channel", "unknown")
            if d < before_start or d > after_end:
                continue
            period = "before" if d <= before_end else "after"
            channels[ch][period]["revenue"] += float(row.get("revenue", 0) or 0)
            channels[ch][period]["orders"] += int(row.get("orders", 0) or 0)

    return {"before": before, "after": after}, dict(channels)


# ══════════════════════════════════════════════════════════════
# 2. GOOGLE ANALYTICS 4
# ══════════════════════════════════════════════════════════════

def pull_ga4(before_start, before_end, after_start, after_end):
    """Pull GA4 metrics for before/after comparison."""
    print("Pulling Google Analytics 4...")
    ga_client = BetaAnalyticsDataClient(credentials=google_creds)
    prop = f"properties/{GA_PROPERTY}"

    results = {}

    # Overall metrics
    for period, start, end in [("before", before_start, before_end), ("after", after_start, after_end)]:
        r = ga_client.run_report(RunReportRequest(
            property=prop,
            date_ranges=[DateRange(start_date=start, end_date=end)],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="newUsers"),
                Metric(name="ecommercePurchases"),
                Metric(name="purchaseRevenue"),
                Metric(name="bounceRate"),
                Metric(name="screenPageViews"),
                Metric(name="userEngagementDuration"),
            ],
        ))
        vals = [float(v.value) for v in r.rows[0].metric_values] if r.rows else [0]*8
        results[period] = {
            "sessions": vals[0], "users": vals[1], "new_users": vals[2],
            "purchases": vals[3], "revenue": vals[4], "bounce_rate": vals[5],
            "pageviews": vals[6], "engagement_sec": vals[7],
        }

    # Traffic sources
    traffic = defaultdict(lambda: {"before": {"sessions": 0, "purchases": 0, "revenue": 0},
                                    "after": {"sessions": 0, "purchases": 0, "revenue": 0}})
    for period, start, end in [("before", before_start, before_end), ("after", after_start, after_end)]:
        r = ga_client.run_report(RunReportRequest(
            property=prop,
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[Dimension(name="sessionDefaultChannelGroup")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="ecommercePurchases"),
                Metric(name="purchaseRevenue"),
            ],
        ))
        for row in r.rows:
            ch = row.dimension_values[0].value
            vals = [float(v.value) for v in row.metric_values]
            traffic[ch][period] = {"sessions": vals[0], "purchases": vals[1], "revenue": vals[2]}

    # Site search usage (key for Algolia fix attribution)
    search = {"before": {"used": {}, "not_used": {}}, "after": {"used": {}, "not_used": {}}}
    for period, start, end in [("before", before_start, before_end), ("after", after_start, after_end)]:
        r = ga_client.run_report(RunReportRequest(
            property=prop,
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[Dimension(name="searchUsed")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="ecommercePurchases"),
                Metric(name="purchaseRevenue"),
            ],
        ))
        for row in r.rows:
            used = "used" if row.dimension_values[0].value == "true" else "not_used"
            vals = [float(v.value) for v in row.metric_values]
            search[period][used] = {"sessions": vals[0], "purchases": vals[1], "revenue": vals[2]}

    print(f"  GA4 OK — Before: {results['before']['sessions']:.0f} sessions, After: {results['after']['sessions']:.0f}")
    return results, dict(traffic), search


# ══════════════════════════════════════════════════════════════
# 3. GOOGLE SEARCH CONSOLE
# ══════════════════════════════════════════════════════════════

def pull_gsc(before_start, before_end, after_start, after_end):
    """Pull Search Console data for organic visibility comparison."""
    print("Pulling Google Search Console...")
    sc = build("searchconsole", "v1", credentials=google_creds)
    site_url = "sc-domain:naturesseed.com"

    results = {}
    for period, start, end in [("before", before_start, before_end), ("after", after_start, after_end)]:
        r = sc.searchanalytics().query(
            siteUrl=site_url,
            body={"startDate": start, "endDate": end, "type": "web"},
        ).execute()
        rows = r.get("rows", [{}])
        if rows:
            row = rows[0]
            results[period] = {
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": row.get("ctr", 0),
                "position": row.get("position", 0),
            }
        else:
            results[period] = {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}

    # Top queries (after period)
    top_q = sc.searchanalytics().query(
        siteUrl=site_url,
        body={"startDate": after_start, "endDate": after_end,
              "dimensions": ["query"], "rowLimit": 15, "type": "web"},
    ).execute()

    print(f"  GSC OK — Before: {results['before']['clicks']} clicks, After: {results['after']['clicks']} clicks")
    return results, top_q.get("rows", [])


# ══════════════════════════════════════════════════════════════
# FORMAT TELEGRAM MESSAGE
# ══════════════════════════════════════════════════════════════

def format_message(cutoff, before_start, before_end, after_start, after_end,
                   supabase, channels, ga4, traffic, search, gsc, gsc_queries):
    """Format complete analysis as Telegram HTML message."""
    lines = []
    lines.append("📊 <b>Impact Analysis — Before vs After Changes</b>")
    lines.append(f"Cutoff: {cutoff} (theme + search fix + Amazon)")
    lines.append(f"Before: {before_start} → {before_end}")
    lines.append(f"After:  {after_start} → {after_end}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━\n")

    # ── Section 1: Revenue & Orders ──
    b = supabase["before"]
    a = supabase["after"]
    b_days = max(b["days"], 1)
    a_days = max(a["days"], 1)

    lines.append("<b>💰 Revenue &amp; Orders</b>")
    lines.append(f"  Revenue:   {fmt_money(b['revenue'])} → <b>{fmt_money(a['revenue'])}</b>  ({fmt_pct(pct_change(b['revenue'], a['revenue']))})")
    lines.append(f"  Daily Avg: {fmt_money(b['revenue']/b_days)} → <b>{fmt_money(a['revenue']/a_days)}</b>  ({fmt_pct(pct_change(b['revenue']/b_days, a['revenue']/a_days))})")
    lines.append(f"  Orders:    {b['orders']} → <b>{a['orders']}</b>  ({fmt_pct(pct_change(b['orders'], a['orders']))})")
    lines.append(f"  Units:     {b['units']} → <b>{a['units']}</b>  ({fmt_pct(pct_change(b['units'], a['units']))})")

    b_aov = b["revenue"] / max(b["orders"], 1)
    a_aov = a["revenue"] / max(a["orders"], 1)
    lines.append(f"  AOV:       {fmt_money(b_aov)} → <b>{fmt_money(a_aov)}</b>  ({fmt_pct(pct_change(b_aov, a_aov))})")

    if b["ad_spend"] > 0 or a["ad_spend"] > 0:
        b_mer = b["revenue"] / max(b["ad_spend"], 1)
        a_mer = a["revenue"] / max(a["ad_spend"], 1)
        lines.append(f"  Ad Spend:  {fmt_money(b['ad_spend'])} → {fmt_money(a['ad_spend'])}  ({fmt_pct(pct_change(b['ad_spend'], a['ad_spend']))})")
        lines.append(f"  MER:       {b_mer:.1f}x → <b>{a_mer:.1f}x</b>")

    b_margin = b["revenue"] - b["cogs"] - b["shipping"] - b["ad_spend"]
    a_margin = a["revenue"] - a["cogs"] - a["shipping"] - a["ad_spend"]
    lines.append(f"  Margin:    {fmt_money(b_margin)} → <b>{fmt_money(a_margin)}</b>  ({fmt_pct(pct_change(b_margin, a_margin))})")
    lines.append("")

    # ── Section 2: Channel Breakdown ──
    if channels:
        lines.append("<b>🏪 Channel Breakdown</b>")
        for ch in sorted(channels.keys()):
            cb = channels[ch]["before"]
            ca = channels[ch]["after"]
            lines.append(f"  {ch}: {fmt_money(cb['revenue'])} → <b>{fmt_money(ca['revenue'])}</b>  ({fmt_pct(pct_change(cb['revenue'], ca['revenue']))})  |  {cb['orders']} → {ca['orders']} orders")
        lines.append("")

    # ── Section 3: Website Traffic (GA4) — Theme Impact ──
    if ga4:
        gb = ga4["before"]
        ga = ga4["after"]
        b_conv = (gb["purchases"] / max(gb["sessions"], 1)) * 100
        a_conv = (ga["purchases"] / max(ga["sessions"], 1)) * 100

        lines.append("<b>🌐 Website Traffic (Theme Impact)</b>")
        lines.append(f"  Sessions:    {gb['sessions']:,.0f} → <b>{ga['sessions']:,.0f}</b>  ({fmt_pct(pct_change(gb['sessions'], ga['sessions']))})")
        lines.append(f"  Users:       {gb['users']:,.0f} → <b>{ga['users']:,.0f}</b>  ({fmt_pct(pct_change(gb['users'], ga['users']))})")
        lines.append(f"  Page Views:  {gb['pageviews']:,.0f} → <b>{ga['pageviews']:,.0f}</b>  ({fmt_pct(pct_change(gb['pageviews'], ga['pageviews']))})")
        lines.append(f"  Bounce Rate: {gb['bounce_rate']*100:.1f}% → <b>{ga['bounce_rate']*100:.1f}%</b>  ({(ga['bounce_rate']-gb['bounce_rate'])*100:+.1f}pp)")
        lines.append(f"  <b>Conv Rate: {b_conv:.2f}% → {a_conv:.2f}%  ({a_conv-b_conv:+.2f}pp)</b>")
        lines.append(f"  GA4 Revenue: {fmt_money(gb['revenue'])} → <b>{fmt_money(ga['revenue'])}</b>")

        # Engagement per session
        b_eng = gb["engagement_sec"] / max(gb["sessions"], 1)
        a_eng = ga["engagement_sec"] / max(ga["sessions"], 1)
        lines.append(f"  Eng/Session: {b_eng:.0f}s → <b>{a_eng:.0f}s</b>  ({fmt_pct(pct_change(b_eng, a_eng))})")
        lines.append("")

    # ── Section 4: Traffic Sources ──
    if traffic:
        lines.append("<b>📡 Traffic Sources</b>")
        for ch in sorted(traffic.keys(), key=lambda c: -traffic[c]["after"]["sessions"]):
            tb = traffic[ch]["before"]
            ta = traffic[ch]["after"]
            b_cr = (tb["purchases"] / max(tb["sessions"], 1)) * 100
            a_cr = (ta["purchases"] / max(ta["sessions"], 1)) * 100
            lines.append(f"  {ch}:")
            lines.append(f"    Sess: {tb['sessions']:,.0f}→{ta['sessions']:,.0f} ({fmt_pct(pct_change(tb['sessions'], ta['sessions']))})  Conv: {b_cr:.1f}%→{a_cr:.1f}%  Rev: {fmt_money(tb['revenue'])}→{fmt_money(ta['revenue'])}")
        lines.append("")

    # ── Section 5: Site Search (Algolia Fix Attribution) ──
    if search:
        lines.append("<b>🔍 Site Search (Algolia Fix Impact)</b>")
        for period_name, period in [("Before", "before"), ("After", "after")]:
            used = search[period].get("used", {})
            not_used = search[period].get("not_used", {})
            u_sess = used.get("sessions", 0)
            u_purch = used.get("purchases", 0)
            u_rev = used.get("revenue", 0)
            u_conv = (u_purch / max(u_sess, 1)) * 100
            total_sess = u_sess + not_used.get("sessions", 0)
            search_rate = (u_sess / max(total_sess, 1)) * 100
            lines.append(f"  {period_name}: Search used by {search_rate:.1f}% of sessions ({u_sess:,.0f})")
            lines.append(f"    → {u_purch:.0f} orders, {fmt_money(u_rev)} rev, {u_conv:.1f}% conv rate")
        lines.append("")

    # ── Section 6: Organic Search (GSC) ──
    if gsc:
        gb = gsc["before"]
        ga = gsc["after"]
        lines.append("<b>🔎 Organic Search (Google Search Console)</b>")
        lines.append(f"  Clicks:      {gb['clicks']:,} → <b>{ga['clicks']:,}</b>  ({fmt_pct(pct_change(gb['clicks'], ga['clicks']))})")
        lines.append(f"  Impressions: {gb['impressions']:,} → <b>{ga['impressions']:,}</b>  ({fmt_pct(pct_change(gb['impressions'], ga['impressions']))})")
        lines.append(f"  CTR:         {gb['ctr']*100:.2f}% → <b>{ga['ctr']*100:.2f}%</b>  ({(ga['ctr']-gb['ctr'])*100:+.2f}pp)")
        lines.append(f"  Avg Pos:     {gb['position']:.1f} → <b>{ga['position']:.1f}</b>  ({ga['position']-gb['position']:+.1f})")
        if gsc_queries:
            lines.append("  Top Queries (After):")
            for q in gsc_queries[:8]:
                lines.append(f"    {q['keys'][0][:35]}: {int(q['clicks'])} clicks, pos {q['position']:.1f}")
        lines.append("")

    # ── Section 7: Attribution Summary ──
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("<b>🎯 Attribution Summary</b>\n")

    # Theme attribution: conv rate + bounce rate + engagement
    if ga4:
        gb = ga4["before"]
        ga = ga4["after"]
        b_conv = (gb["purchases"] / max(gb["sessions"], 1)) * 100
        a_conv = (ga["purchases"] / max(ga["sessions"], 1)) * 100
        conv_delta = a_conv - b_conv

        if conv_delta > 0.3:
            lines.append(f"✅ <b>New Theme</b>: Conv rate up {conv_delta:+.2f}pp — likely significant impact")
        elif conv_delta > 0:
            lines.append(f"🔶 <b>New Theme</b>: Conv rate up {conv_delta:+.2f}pp — modest improvement")
        else:
            lines.append(f"⚠️ <b>New Theme</b>: Conv rate {conv_delta:+.2f}pp — may need attention")

        bounce_delta = (ga["bounce_rate"] - gb["bounce_rate"]) * 100
        if bounce_delta < -2:
            lines.append(f"  ↳ Bounce rate improved {bounce_delta:+.1f}pp — visitors staying longer")
        elif bounce_delta > 2:
            lines.append(f"  ↳ Bounce rate worsened {bounce_delta:+.1f}pp — check mobile/page speed")

    # Search attribution
    if search:
        b_used = search["before"].get("used", {})
        a_used = search["after"].get("used", {})
        b_search_rev = b_used.get("revenue", 0)
        a_search_rev = a_used.get("revenue", 0)
        b_search_sess = b_used.get("sessions", 0)
        a_search_sess = a_used.get("sessions", 0)

        if a_search_sess > b_search_sess * 1.2:
            lines.append(f"\n✅ <b>Search Fix (Algolia)</b>: Search sessions up {fmt_pct(pct_change(b_search_sess, a_search_sess))}")
        elif a_search_sess > b_search_sess:
            lines.append(f"\n🔶 <b>Search Fix (Algolia)</b>: Search sessions up {fmt_pct(pct_change(b_search_sess, a_search_sess))}")
        else:
            lines.append(f"\n⚠️ <b>Search Fix (Algolia)</b>: Search sessions {fmt_pct(pct_change(b_search_sess, a_search_sess))}")

        lines.append(f"  ↳ Search revenue: {fmt_money(b_search_rev)} → {fmt_money(a_search_rev)}")

    # Amazon attribution
    lines.append(f"\nℹ️ <b>Amazon Launch</b>: Not yet tracked in Supabase")
    lines.append("  ↳ Revenue is additive — check Seller Central for numbers")
    lines.append("  ↳ Look for 'amazon.com' referral traffic in GA4 traffic sources above")

    # Organic attribution
    if gsc:
        gb = gsc["before"]
        ga = gsc["after"]
        click_chg = pct_change(gb["clicks"], ga["clicks"])
        if click_chg > 10:
            lines.append(f"\n✅ <b>Organic SEO</b>: Clicks up {fmt_pct(click_chg)} — content/product cards paying off")
        elif click_chg > 0:
            lines.append(f"\n🔶 <b>Organic SEO</b>: Clicks up {fmt_pct(click_chg)} — steady growth")
        else:
            lines.append(f"\n⚠️ <b>Organic SEO</b>: Clicks {fmt_pct(click_chg)} — may be seasonal")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    cutoff = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "2026-02-26"
    no_telegram = "--no-telegram" in sys.argv

    # 14-day windows
    cutoff_date = datetime.strptime(cutoff, "%Y-%m-%d")
    before_start = (cutoff_date - timedelta(days=14)).strftime("%Y-%m-%d")
    before_end = (cutoff_date - timedelta(days=1)).strftime("%Y-%m-%d")
    after_start = cutoff
    after_end = (cutoff_date + timedelta(days=13)).strftime("%Y-%m-%d")

    print("=" * 60)
    print(f"  IMPACT ANALYSIS")
    print(f"  Before: {before_start} → {before_end}")
    print(f"  After:  {after_start} → {after_end}")
    print("=" * 60)

    errors = []

    # 1. Supabase
    try:
        supabase, channels = pull_supabase(before_start, before_end, after_start, after_end)
    except Exception as e:
        print(f"  [ERR] Supabase: {e}")
        errors.append("Supabase")
        supabase = {"before": {"revenue":0,"orders":0,"units":0,"ad_spend":0,"cogs":0,"shipping":0,"days":0},
                     "after": {"revenue":0,"orders":0,"units":0,"ad_spend":0,"cogs":0,"shipping":0,"days":0}}
        channels = {}

    # 2. GA4
    ga4 = traffic = search = None
    try:
        ga4, traffic, search = pull_ga4(before_start, before_end, after_start, after_end)
    except Exception as e:
        print(f"  [ERR] GA4: {e}")
        errors.append("GA4")

    # 3. GSC
    gsc = gsc_queries = None
    try:
        gsc, gsc_queries = pull_gsc(before_start, before_end, after_start, after_end)
    except Exception as e:
        print(f"  [ERR] GSC: {e}")
        errors.append("GSC")

    # Format
    message = format_message(
        cutoff, before_start, before_end, after_start, after_end,
        supabase, channels, ga4, traffic, search, gsc, gsc_queries,
    )

    if errors:
        message += f"\n\n⚠️ <i>Data sources unavailable: {', '.join(errors)}</i>"

    # Print to console
    print("\n" + message)

    # Send to Telegram
    if not no_telegram and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        print("\nSending to Telegram...")
        send_telegram(message)
        print("Sent!")
    else:
        print("\n[SKIP] Telegram send skipped")


if __name__ == "__main__":
    main()
