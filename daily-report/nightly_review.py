#!/usr/bin/env python3
"""
Nature's Seed — Nightly Sales Review (Telegram)
Sent every night at 10 PM MST via GitHub Actions.

Pulls TODAY's live data from WooCommerce + Google Ads,
combines with Supabase MTD data (through yesterday),
and sends a formatted summary to Telegram.

Includes:
  - Today's revenue, orders, ad spend, MER
  - Best sellers (top 5 products by revenue)
  - Sales by state (top 5)
  - MTD vs last year comparison
  - Quick commentary

Usage:
  python3 nightly_review.py           # Today's review
  python3 nightly_review.py 2026-03-09  # Specific date
"""

import json
import sys
import time
import os
import html
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict

import requests
from google.ads.googleads.client import GoogleAdsClient

# ══════════════════════════════════════════════════════════════
# ENV SETUP (reuse from daily_pull.py)
# ══════════════════════════════════════════════════════════════

env_path = Path(__file__).resolve().parent.parent / ".env"
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

# Supabase
SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")

# WooCommerce
WC_BASE = env_vars.get("WC_BASE_URL", "https://naturesseed.com/wp-json/wc/v3")
WC_CK = env_vars["WC_CK"]
WC_CS = env_vars["WC_CS"]
WC_AUTH = (WC_CK, WC_CS)

# Cloudflare Worker proxy (bypasses Bot Fight Mode for datacenter IPs)
CF_WORKER_URL = env_vars.get("CF_WORKER_URL", "")
CF_WORKER_SECRET = env_vars.get("CF_WORKER_SECRET", "")
if CF_WORKER_URL:
    print(f"[CONFIG] CF Worker proxy enabled: {CF_WORKER_URL[:40]}...")
else:
    print("[CONFIG] CF Worker proxy NOT configured — using direct WC API calls")

# Google Ads
GOOGLE_ADS_CONFIG = {
    "developer_token": env_vars["GOOGLE_ADS_DEVELOPER_TOKEN"],
    "client_id": env_vars["GOOGLE_ADS_CLIENT_ID"],
    "client_secret": env_vars["GOOGLE_ADS_CLIENT_SECRET"],
    "refresh_token": env_vars["GOOGLE_ADS_REFRESH_TOKEN"],
    "use_proto_plus": True,
}
login_cid = env_vars.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
if login_cid:
    GOOGLE_ADS_CONFIG["login_customer_id"] = login_cid
GOOGLE_ADS_CUSTOMER_ID = env_vars["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")

# Telegram
TELEGRAM_TOKEN = env_vars.get("TELEGRAM_BOT_TOKEN") or env_vars.get("TELEGRAM_BOT_API", "")
TELEGRAM_CHAT_ID = env_vars.get("TELEGRAM_CHAT_ID", "")


# ══════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════

def send_telegram(text, parse_mode="HTML"):
    """Send a message to Telegram, auto-splitting if needed."""
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
        time.sleep(0.1)


# ══════════════════════════════════════════════════════════════
# DATA PULLS
# ══════════════════════════════════════════════════════════════

WC_HEADERS = {"User-Agent": "NaturesSeed-NightlyReview/1.0"}


def _wc_request_with_retry(url, params, max_retries=3):
    """Make a WC API request with retry logic for transient errors.

    If CF_WORKER_URL is set, routes through the Cloudflare Worker proxy
    to bypass Bot Fight Mode (which blocks datacenter IPs like GitHub Actions).
    Falls back to direct WC API calls for local use.
    """
    import base64

    for attempt in range(max_retries):
        if CF_WORKER_URL and CF_WORKER_SECRET:
            # Route through Cloudflare Worker proxy
            wc_path = url.replace(WC_BASE, "")
            proxy_params = dict(params)
            proxy_params["wc_path"] = wc_path
            auth_str = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
            headers = {
                "X-Proxy-Secret": CF_WORKER_SECRET,
                "Authorization": f"Basic {auth_str}",
                "User-Agent": "NaturesSeed-NightlyReview/1.0",
            }
            resp = requests.get(CF_WORKER_URL, params=proxy_params, headers=headers, timeout=60)
        else:
            # Direct WC API call (local dev)
            resp = requests.get(url, auth=WC_AUTH, params=params, headers=WC_HEADERS, timeout=60)

        if resp.status_code == 200:
            return resp
        if resp.status_code in (403, 429, 500, 502, 503):
            print(f"  [DEBUG] Status: {resp.status_code}")
            print(f"  [DEBUG] Server: {resp.headers.get('server', 'unknown')}")
            print(f"  [DEBUG] CF-Mitigated: {resp.headers.get('cf-mitigated', 'none')}")
            if attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  [RETRY] Waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
        resp.raise_for_status()
    return resp


def pull_wc_orders(report_date):
    """Pull WooCommerce orders with full detail for today."""
    start = f"{report_date}T00:00:00"
    end = f"{report_date}T23:59:59"

    all_orders = []
    for status in ["completed", "processing"]:
        page = 1
        while True:
            params = {
                "after": start, "before": end,
                "status": status, "per_page": 100, "page": page,
            }
            resp = _wc_request_with_retry(f"{WC_BASE}/orders", params)
            orders = resp.json()
            if not orders:
                break
            all_orders.extend(orders)
            total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
            if page >= total_pages:
                break
            page += 1
            time.sleep(0.3)

    return all_orders


def pull_google_ads_today(report_date):
    """Pull Google Ads metrics for today."""
    client = GoogleAdsClient.load_from_dict(GOOGLE_ADS_CONFIG)
    ga_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date = '{report_date}'
          AND campaign.status != 'REMOVED'
    """
    try:
        response = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query)
        rows = list(response)
    except Exception as e:
        print(f"[WARN] Google Ads error: {e}")
        rows = []

    return {
        "spend": sum(r.metrics.cost_micros / 1_000_000 for r in rows),
        "clicks": sum(r.metrics.clicks for r in rows),
        "conversions": sum(r.metrics.conversions for r in rows),
        "conv_value": sum(r.metrics.conversions_value for r in rows),
    }


def query_supabase_mtd(report_date):
    """
    Query Supabase for MTD data through yesterday.
    Also pulls same period last year for comparison.
    """
    today = datetime.strptime(str(report_date), "%Y-%m-%d")
    month_start = today.replace(day=1).strftime("%Y-%m-%d")
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # Current year MTD (through yesterday — today's data isn't in Supabase yet)
    url = f"{SUPABASE_URL}/rest/v1/daily_summary"
    headers = {"apikey": SUPABASE_KEY}

    # MTD current year
    params = {
        "select": "report_date,total_revenue,total_orders,total_ad_spend,shipping_cost",
        "report_date": f"gte.{month_start}",
        "and": f"(report_date.lte.{yesterday})",
    }
    resp = requests.get(url, headers=headers, params=params, timeout=30)

    mtd_cy = {"revenue": 0, "orders": 0, "ad_spend": 0, "shipping": 0}
    if resp.status_code == 200:
        for row in resp.json():
            mtd_cy["revenue"] += float(row.get("total_revenue") or 0)
            mtd_cy["orders"] += int(row.get("total_orders") or 0)
            mtd_cy["ad_spend"] += float(row.get("total_ad_spend") or 0)
            mtd_cy["shipping"] += float(row.get("shipping_cost") or 0)

    # Last year same period
    ly_start = (today.replace(year=today.year - 1, day=1)).strftime("%Y-%m-%d")
    ly_end = (today.replace(year=today.year - 1)).strftime("%Y-%m-%d")

    params_ly = {
        "select": "report_date,total_revenue,total_orders,total_ad_spend",
        "report_date": f"gte.{ly_start}",
        "and": f"(report_date.lte.{ly_end})",
    }
    resp_ly = requests.get(url, headers=headers, params=params_ly, timeout=30)

    mtd_ly = {"revenue": 0, "orders": 0, "ad_spend": 0}
    if resp_ly.status_code == 200:
        for row in resp_ly.json():
            mtd_ly["revenue"] += float(row.get("total_revenue") or 0)
            mtd_ly["orders"] += int(row.get("total_orders") or 0)
            mtd_ly["ad_spend"] += float(row.get("total_ad_spend") or 0)

    # Same day last year
    ly_same_day = today.replace(year=today.year - 1).strftime("%Y-%m-%d")
    params_day_ly = {
        "select": "report_date,total_revenue,total_orders,total_ad_spend",
        "report_date": f"eq.{ly_same_day}",
    }
    resp_day_ly = requests.get(url, headers=headers, params=params_day_ly, timeout=30)

    day_ly = {"revenue": 0, "orders": 0, "ad_spend": 0}
    if resp_day_ly.status_code == 200:
        for row in resp_day_ly.json():
            day_ly["revenue"] += float(row.get("total_revenue") or 0)
            day_ly["orders"] += int(row.get("total_orders") or 0)
            day_ly["ad_spend"] += float(row.get("total_ad_spend") or 0)

    return mtd_cy, mtd_ly, day_ly


# ══════════════════════════════════════════════════════════════
# ANALYSIS
# ══════════════════════════════════════════════════════════════

def analyze_orders(orders):
    """Extract best sellers and per-state breakdown from WooCommerce orders."""

    # Best sellers by revenue
    product_rev = defaultdict(lambda: {"revenue": 0, "qty": 0})
    for order in orders:
        for item in order.get("line_items", []):
            name = html.unescape(item.get("name", "Unknown"))
            revenue = float(item.get("total", 0))
            qty = item.get("quantity", 0)
            product_rev[name]["revenue"] += revenue
            product_rev[name]["qty"] += qty

    best_sellers = sorted(product_rev.items(), key=lambda x: -x[1]["revenue"])[:5]

    # Per-state breakdown
    state_rev = defaultdict(lambda: {"revenue": 0, "orders": 0})
    for order in orders:
        state = order.get("billing", {}).get("state", "") or order.get("shipping", {}).get("state", "")
        if not state:
            state = "Unknown"
        revenue = float(order.get("total", 0))
        state_rev[state]["revenue"] += revenue
        state_rev[state]["orders"] += 1

    top_states = sorted(state_rev.items(), key=lambda x: -x[1]["revenue"])[:5]

    return best_sellers, top_states


def generate_commentary(today_rev, today_orders, mtd_cy, mtd_ly, ads):
    """Generate a quick natural language commentary."""
    lines = []

    # Today vs average
    if mtd_cy["orders"] > 0 and mtd_cy["revenue"] > 0:
        days_so_far = max(1, mtd_cy["orders"] // max(1, today_orders) if today_orders > 0 else 1)

    # YoY comparison
    if mtd_ly["revenue"] > 0:
        # MTD including today vs LY
        total_mtd = mtd_cy["revenue"] + today_rev
        yoy = ((total_mtd - mtd_ly["revenue"]) / mtd_ly["revenue"]) * 100
        if yoy > 10:
            lines.append(f"MTD revenue is up {yoy:.0f}% vs last year — strong momentum.")
        elif yoy > 0:
            lines.append(f"MTD revenue is up {yoy:.0f}% vs last year — steady growth.")
        elif yoy > -10:
            lines.append(f"MTD revenue is down {abs(yoy):.0f}% vs last year — close to pacing.")
        else:
            lines.append(f"MTD revenue is down {abs(yoy):.0f}% vs last year — needs attention.")

    # MER commentary
    total_spend = mtd_cy["ad_spend"] + ads["spend"]
    total_rev = mtd_cy["revenue"] + today_rev
    if total_spend > 0:
        mer = total_rev / total_spend
        if mer > 5:
            lines.append(f"MTD MER is {mer:.1f}x — excellent efficiency.")
        elif mer > 3:
            lines.append(f"MTD MER is {mer:.1f}x — healthy.")
        else:
            lines.append(f"MTD MER is {mer:.1f}x — watch spend efficiency.")

    # Today's specific note
    if today_rev > 3000:
        lines.append("Great sales day!")
    elif today_rev < 500 and today_orders < 5:
        lines.append("Slow day — likely timing or day-of-week effect.")

    return " ".join(lines) if lines else "Steady day."


# ══════════════════════════════════════════════════════════════
# FORMAT MESSAGE
# ══════════════════════════════════════════════════════════════

# US state abbreviation to full name (for readability)
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "Washington DC",
}


def format_review(report_date, orders, ads, mtd_cy, mtd_ly, day_ly, best_sellers, top_states):
    """Format the nightly review as a Telegram HTML message."""
    today_rev = sum(float(o.get("total", 0)) for o in orders)
    today_orders = len(orders)
    today_units = sum(
        item.get("quantity", 0)
        for o in orders
        for item in o.get("line_items", [])
    )

    today_mer = round(today_rev / ads["spend"], 1) if ads["spend"] > 0 else 0
    day_name = datetime.strptime(str(report_date), "%Y-%m-%d").strftime("%A")

    commentary = generate_commentary(today_rev, today_orders, mtd_cy, mtd_ly, ads)

    lines = []
    lines.append(f"📊 <b>Daily Sales Review — {day_name}, {report_date}</b>")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━\n")

    # Today's numbers
    lines.append("<b>Today</b>")
    lines.append(f"  💰 Revenue: <b>${today_rev:,.0f}</b>  ({today_orders} orders, {today_units} units)")
    lines.append(f"  📈 Ad Spend: ${ads['spend']:,.0f}  |  MER: {today_mer}x")
    lines.append(f"  🖱 Clicks: {ads['clicks']:,}  |  Conversions: {ads['conversions']:.0f}")

    # Today vs last year same day
    if day_ly["revenue"] > 0:
        day_yoy = ((today_rev - day_ly["revenue"]) / day_ly["revenue"]) * 100
        arrow = "📈" if day_yoy >= 0 else "📉"
        lines.append(f"  {arrow} vs Last Year: {day_yoy:+.0f}%  (LY: ${day_ly['revenue']:,.0f}, {day_ly['orders']} orders)")
    elif day_ly["revenue"] == 0 and day_ly["orders"] == 0:
        lines.append(f"  ℹ️ No data for this day last year")
    lines.append("")

    # Best sellers
    if best_sellers:
        lines.append("<b>Best Sellers</b>")
        for i, (name, data) in enumerate(best_sellers, 1):
            safe_name = html.escape(name)
            # Truncate long names
            if len(safe_name) > 35:
                safe_name = safe_name[:32] + "..."
            lines.append(f"  {i}. {safe_name} — ${data['revenue']:,.0f} ({data['qty']}x)")
        lines.append("")

    # Top states
    if top_states:
        lines.append("<b>Top States</b>")
        for state_code, data in top_states:
            state_name = STATE_NAMES.get(state_code, state_code)
            lines.append(f"  📍 {state_name}: ${data['revenue']:,.0f} ({data['orders']} orders)")
        lines.append("")

    # MTD comparison
    mtd_rev_total = mtd_cy["revenue"] + today_rev
    mtd_orders_total = mtd_cy["orders"] + today_orders
    mtd_spend_total = mtd_cy["ad_spend"] + ads["spend"]
    mtd_mer = round(mtd_rev_total / mtd_spend_total, 1) if mtd_spend_total > 0 else 0

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    month_name = datetime.strptime(str(report_date), "%Y-%m-%d").strftime("%B")
    lines.append(f"<b>{month_name} MTD</b>")
    lines.append(f"  💰 Revenue: <b>${mtd_rev_total:,.0f}</b>  ({mtd_orders_total} orders)")
    lines.append(f"  📈 Ad Spend: ${mtd_spend_total:,.0f}  |  MER: {mtd_mer}x")

    if mtd_ly["revenue"] > 0:
        yoy_pct = ((mtd_rev_total - mtd_ly["revenue"]) / mtd_ly["revenue"]) * 100
        arrow = "📈" if yoy_pct >= 0 else "📉"
        lines.append(f"  {arrow} vs Last Year: {yoy_pct:+.0f}% (LY: ${mtd_ly['revenue']:,.0f})")
    lines.append("")

    # Commentary
    lines.append(f"<i>{html.escape(commentary)}</i>")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) > 1:
        report_date = sys.argv[1]
    else:
        report_date = date.today().strftime("%Y-%m-%d")

    print(f"Nightly Sales Review for {report_date}")
    print("=" * 50)

    errors = []

    # Pull live data — each source is non-fatal
    print("Pulling WooCommerce orders...")
    try:
        orders = pull_wc_orders(report_date)
        print(f"  Found {len(orders)} orders")
    except Exception as e:
        print(f"  [ERR] WooCommerce failed: {e}")
        errors.append("WooCommerce")
        orders = []

    print("Pulling Google Ads metrics...")
    try:
        ads = pull_google_ads_today(report_date)
        print(f"  Spend: ${ads['spend']:,.2f}")
    except Exception as e:
        print(f"  [ERR] Google Ads failed: {e}")
        errors.append("Google Ads")
        ads = {"spend": 0, "clicks": 0, "conversions": 0, "conv_value": 0}

    print("Querying Supabase for MTD + last year...")
    try:
        mtd_cy, mtd_ly, day_ly = query_supabase_mtd(report_date)
        print(f"  MTD CY (thru yesterday): ${mtd_cy['revenue']:,.0f}")
        print(f"  MTD LY: ${mtd_ly['revenue']:,.0f}")
        print(f"  Same day LY: ${day_ly['revenue']:,.0f} ({day_ly['orders']} orders)")
    except Exception as e:
        print(f"  [ERR] Supabase failed: {e}")
        errors.append("Supabase")
        mtd_cy = {"revenue": 0, "orders": 0, "ad_spend": 0, "shipping": 0}
        mtd_ly = {"revenue": 0, "orders": 0, "ad_spend": 0}
        day_ly = {"revenue": 0, "orders": 0, "ad_spend": 0}

    # Analyze
    best_sellers, top_states = analyze_orders(orders)

    # Format
    message = format_review(report_date, orders, ads, mtd_cy, mtd_ly, day_ly, best_sellers, top_states)

    if errors:
        message += f"\n\n⚠️ <i>Data sources unavailable: {', '.join(errors)}</i>"

    # Print to console
    print("\n" + "=" * 50)
    print(message)
    print("=" * 50)

    # Send to Telegram
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        print("\nSending to Telegram...")
        send_telegram(message)
        print("Sent!")
    else:
        print("\n[SKIP] No Telegram credentials — printed only")


if __name__ == "__main__":
    main()
