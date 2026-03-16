"""
Weekly GCLID Attribution Report — Nature's Seed
================================================
Cross-references WooCommerce order attribution (GCLID/campaign ID)
with Google Ads campaign spend data to produce a weekly performance
report with budget recommendations (30% guardrails).

Runs weekly (Sundays) via GitHub Actions, sends report to Telegram.

Usage:
    python weekly_attribution_report.py          # Generate + send to Telegram
    python weekly_attribution_report.py --local  # Generate only, print to stdout
"""

import json
import logging
import os
import sys
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from collections import defaultdict

from google.ads.googleads.client import GoogleAdsClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("weekly_attribution")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DRIP_DIR = Path(__file__).resolve().parent
REPORTS_DIR = DRIP_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ── Known PMax sub-campaign → parent mapping ─────────────────────────────────
# PMax generates invisible sub-campaign IDs in click URLs.
# These don't appear in the Google Ads API campaign list.
PMAX_PARENT_MAP = {
    # PMAX | Catch all (parent: 22944456167)
    "22944456167": "22944456167",
    # PMAX - Search (parent: 23453477009)
    "23453477009": "23453477009",
}
# Known campaign names for display
CAMPAIGN_NAMES = {
    "22908379664": "Shopping | Catch All",
    "22944456167": "PMAX | Catch All",
    "23453477009": "PMAX - Search",
    "22906429547": "Search | Brand",
    "22914283571": "Search | Animal Seed",
    "22914283568": "Search | Pasture Exact",
    "22914283574": "Search | Pasture Broad",
}


def _load_env():
    """Load .env from project root. OS env vars override file values."""
    env = {}
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        raise FileNotFoundError(f".env not found at {env_file}")
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip().strip("'\"")
    # OS env vars override file values (allows local overrides like CF_WORKER_URL="")
    for key in list(env.keys()):
        os_val = os.environ.get(key)
        if os_val is not None:
            env[key] = os_val
    return env


def _wc_get(env, endpoint, params=None):
    """GET from WooCommerce REST API (with CF Worker proxy support)."""
    cf_url = env.get("CF_WORKER_URL", "").strip()

    if cf_url:
        # Route through Cloudflare Worker proxy
        # Worker expects full WC API path after the worker URL
        url = f"{cf_url}/{endpoint}"
        headers = {"X-Proxy-Secret": env.get("CF_WORKER_SECRET", "")}
        r = requests.get(url, params=params, headers=headers, timeout=30)
    else:
        # Direct WC API call (local dev — residential IP bypasses Bot Fight Mode)
        url = f"{env['WC_BASE_URL']}/{endpoint}"
        auth = (env["WC_CK"], env["WC_CS"])
        r = requests.get(url, auth=auth, params=params, timeout=30)

    r.raise_for_status()
    return r.json(), r.headers


def pull_wc_orders(env, days=7):
    """Pull WooCommerce orders from last N days with attribution metadata."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    after = start_date.strftime("%Y-%m-%dT00:00:00")

    all_orders = []
    for status in ["completed", "processing"]:
        page = 1
        while True:
            params = {
                "status": status,
                "after": after,
                "per_page": 100,
                "page": page,
                "orderby": "date",
                "order": "desc",
            }
            orders, headers = _wc_get(env, "orders", params)
            if not orders:
                break
            all_orders.extend(orders)
            total_pages = int(headers.get("X-WP-TotalPages", 1))
            if page >= total_pages:
                break
            page += 1
            time.sleep(0.3)

    log.info(f"Pulled {len(all_orders)} WC orders from last {days} days")
    return all_orders


def extract_attribution(order):
    """Extract Google Ads attribution from WC order metadata."""
    meta = {m["key"]: m["value"] for m in order.get("meta_data", [])}

    result = {
        "order_id": order["id"],
        "date": order["date_created"][:10],
        "total": float(order.get("total", 0)),
        "billing_email": order.get("billing", {}).get("email", ""),
        "customer_id": order.get("customer_id", 0),
        "utm_source": meta.get("_wc_order_attribution_utm_source", ""),
        "utm_medium": meta.get("_wc_order_attribution_utm_medium", ""),
        "utm_campaign": meta.get("_wc_order_attribution_utm_campaign", ""),
        "source_type": meta.get("_wc_order_attribution_source_type", ""),
        "device": meta.get("_wc_order_attribution_device_type", ""),
        "gclid": None,
        "gad_campaignid": None,
    }

    # Parse GCLID and campaign ID from session entry URL
    session_entry = meta.get("_wc_order_attribution_session_entry", "")
    if session_entry:
        try:
            parsed = urlparse(session_entry)
            qs = parse_qs(parsed.query)
            result["gclid"] = qs.get("gclid", [None])[0]
            result["gad_campaignid"] = qs.get("gad_campaignid", [None])[0]
        except Exception:
            pass

    return result


def resolve_campaign_id(gad_campaignid, known_campaigns):
    """Resolve a gad_campaignid to a known campaign, handling PMax sub-campaigns."""
    if not gad_campaignid:
        return None

    # Direct match
    if gad_campaignid in known_campaigns:
        return gad_campaignid

    # Check PMax parent mapping
    if gad_campaignid in PMAX_PARENT_MAP:
        return PMAX_PARENT_MAP[gad_campaignid]

    # Unknown sub-campaign → try to match to a PMax parent
    # PMax sub-campaigns are the most common unknowns
    return f"pmax_unknown_{gad_campaignid}"


def pull_google_ads_spend(env, days=7):
    """Pull Google Ads spend by campaign for the last N days."""
    credentials = {
        "developer_token": env["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": env["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": env["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": env["GOOGLE_ADS_REFRESH_TOKEN"],
        "login_customer_id": env["GOOGLE_ADS_LOGIN_CUSTOMER_ID"].replace("-", ""),
        "use_proto_plus": True,
    }
    client = GoogleAdsClient.load_from_dict(credentials)
    customer_id = env["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
    ga_service = client.get_service("GoogleAdsService")

    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.advertising_channel_type,
            campaign_budget.amount_micros,
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
          AND campaign.status = 'ENABLED'
          AND metrics.cost_micros > 0
    """

    campaigns = {}
    for row in ga_service.search(customer_id=customer_id, query=query):
        cid = str(row.campaign.id)
        if cid not in campaigns:
            campaigns[cid] = {
                "campaign_id": cid,
                "campaign_name": row.campaign.name,
                "channel_type": row.campaign.advertising_channel_type.name,
                "budget_daily": row.campaign_budget.amount_micros / 1_000_000,
                "spend": 0,
                "impressions": 0,
                "clicks": 0,
                "conversions": 0,
                "conv_value": 0,
            }
        c = campaigns[cid]
        c["spend"] += row.metrics.cost_micros / 1_000_000
        c["impressions"] += row.metrics.impressions
        c["clicks"] += row.metrics.clicks
        c["conversions"] += row.metrics.conversions
        c["conv_value"] += row.metrics.conversions_value

    log.info(f"Pulled spend for {len(campaigns)} campaigns ({start_date} to {end_date})")
    return campaigns


def generate_report(env, days=7):
    """Generate the weekly attribution report."""
    log.info(f"Generating {days}-day attribution report...")

    # Pull data
    orders = pull_wc_orders(env, days=days)
    ad_spend = pull_google_ads_spend(env, days=days)

    # Extract attribution from each order
    attributed_orders = [extract_attribution(o) for o in orders]

    # Known campaign IDs from Google Ads
    known_campaigns = set(ad_spend.keys())

    # Group orders by campaign
    campaign_orders = defaultdict(list)
    unattributed = []
    organic_direct = []

    for order in attributed_orders:
        if order["gad_campaignid"]:
            resolved = resolve_campaign_id(order["gad_campaignid"], known_campaigns)
            campaign_orders[resolved].append(order)
        elif order["utm_source"] in ("google", "google-ads") and order["utm_medium"] in ("cpc", "ppc"):
            # Has UTM but no GCLID campaign ID — attribute to "Google Ads (UTM only)"
            campaign_orders["google_ads_utm_only"].append(order)
        else:
            if order["source_type"] in ("organic", "direct", "referral", ""):
                organic_direct.append(order)
            else:
                unattributed.append(order)

    # Track new vs returning customers
    email_first_seen = {}
    for order in sorted(attributed_orders, key=lambda o: o["date"]):
        email = order["billing_email"].lower()
        if email and email not in email_first_seen:
            email_first_seen[email] = order["date"]

    # Build per-campaign report
    campaign_reports = []
    pmax_unknown_orders = []

    for campaign_id, orders_list in campaign_orders.items():
        if campaign_id.startswith("pmax_unknown_"):
            pmax_unknown_orders.extend(orders_list)
            continue

        spend_data = ad_spend.get(campaign_id, {})
        total_revenue = sum(o["total"] for o in orders_list)
        total_orders = len(orders_list)

        # New customer detection
        new_customers = 0
        for o in orders_list:
            email = o["billing_email"].lower()
            if email and email_first_seen.get(email) == o["date"]:
                # First order from this email in the window
                new_customers += 1
            elif o["customer_id"] == 0:
                # Guest checkout = likely new
                new_customers += 1

        ad_spend_amount = spend_data.get("spend", 0)
        ncac = ad_spend_amount / new_customers if new_customers > 0 else float("inf")
        roas_wc = total_revenue / ad_spend_amount if ad_spend_amount > 0 else float("inf")

        campaign_reports.append({
            "campaign_id": campaign_id,
            "campaign_name": spend_data.get("campaign_name") or CAMPAIGN_NAMES.get(campaign_id, f"Unknown ({campaign_id})"),
            "budget_daily": spend_data.get("budget_daily", 0),
            "spend": ad_spend_amount,
            "wc_revenue": total_revenue,
            "wc_orders": total_orders,
            "new_customers": new_customers,
            "returning_customers": total_orders - new_customers,
            "new_pct": new_customers / total_orders * 100 if total_orders > 0 else 0,
            "ncac": ncac,
            "roas_wc": roas_wc,
            "roas_google": spend_data.get("conv_value", 0) / ad_spend_amount if ad_spend_amount > 0 else 0,
            "clicks": spend_data.get("clicks", 0),
            "conv_rate": total_orders / spend_data.get("clicks", 1) * 100 if spend_data.get("clicks", 0) > 0 else 0,
        })

    # Merge PMax unknown into PMax Catch All
    if pmax_unknown_orders:
        for cr in campaign_reports:
            if cr["campaign_id"] == "22944456167":
                cr["wc_revenue"] += sum(o["total"] for o in pmax_unknown_orders)
                cr["wc_orders"] += len(pmax_unknown_orders)
                cr["new_customers"] += sum(1 for o in pmax_unknown_orders if o["customer_id"] == 0)
                cr["roas_wc"] = cr["wc_revenue"] / cr["spend"] if cr["spend"] > 0 else 0
                cr["ncac"] = cr["spend"] / cr["new_customers"] if cr["new_customers"] > 0 else float("inf")
                break

    # Sort by spend descending
    campaign_reports.sort(key=lambda c: c["spend"], reverse=True)

    # Generate budget recommendations with 30% guardrails
    recommendations = generate_budget_recommendations(campaign_reports)

    report = {
        "period": f"Last {days} days",
        "start_date": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
        "end_date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_orders": len(attributed_orders),
            "google_ads_orders": sum(cr["wc_orders"] for cr in campaign_reports),
            "organic_direct_orders": len(organic_direct),
            "unattributed_orders": len(unattributed),
            "total_ad_spend": sum(cr["spend"] for cr in campaign_reports),
            "total_wc_revenue_from_ads": sum(cr["wc_revenue"] for cr in campaign_reports),
            "blended_roas": (
                sum(cr["wc_revenue"] for cr in campaign_reports)
                / sum(cr["spend"] for cr in campaign_reports)
                if sum(cr["spend"] for cr in campaign_reports) > 0
                else 0
            ),
        },
        "campaigns": campaign_reports,
        "recommendations": recommendations,
    }

    # Save report
    report_file = REPORTS_DIR / f"attribution_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    log.info(f"Report saved to {report_file}")

    return report


def generate_budget_recommendations(campaign_reports):
    """Generate budget recommendations with 30% guardrails."""
    recs = []

    for cr in campaign_reports:
        budget = cr["budget_daily"]
        if budget <= 0:
            continue

        roas = cr["roas_wc"]
        ncac = cr["ncac"]
        spend = cr["spend"]
        name = cr["campaign_name"]

        # Skip campaigns with too little data
        if cr["wc_orders"] < 2:
            continue

        # Recommendation logic:
        # ROAS > 5x and nCAC < $40 → strong increase (up to +30%)
        # ROAS 3-5x and nCAC < $60 → moderate increase (+15-20%)
        # ROAS 2-3x → hold (healthy)
        # ROAS 1-2x → watch / slight decrease (-10-15%)
        # ROAS < 1x → decrease (-20-30%)

        if roas > 5.0 and ncac < 40:
            new_budget = min(budget * 1.30, budget + 50)  # +30% or +$50 cap
            recs.append({
                "campaign": name,
                "campaign_id": cr["campaign_id"],
                "action": "INCREASE",
                "current_budget": budget,
                "proposed_budget": round(new_budget, 0),
                "change_pct": round((new_budget - budget) / budget * 100, 1),
                "rationale": f"Strong performer: {roas:.1f}x ROAS, ${ncac:.0f} nCAC, {cr['new_customers']} new customers",
                "confidence": "HIGH",
            })
        elif roas > 3.0 and ncac < 60:
            new_budget = min(budget * 1.15, budget + 30)
            change_pct = (new_budget - budget) / budget * 100
            if change_pct > 5:  # Only recommend if meaningful
                recs.append({
                    "campaign": name,
                    "campaign_id": cr["campaign_id"],
                    "action": "INCREASE",
                    "current_budget": budget,
                    "proposed_budget": round(new_budget, 0),
                    "change_pct": round(change_pct, 1),
                    "rationale": f"Good performer: {roas:.1f}x ROAS, ${ncac:.0f} nCAC",
                    "confidence": "MEDIUM",
                })
        elif roas >= 2.0:
            recs.append({
                "campaign": name,
                "campaign_id": cr["campaign_id"],
                "action": "HOLD",
                "current_budget": budget,
                "proposed_budget": budget,
                "change_pct": 0,
                "rationale": f"Healthy: {roas:.1f}x ROAS, ${ncac:.0f} nCAC — maintain current budget",
                "confidence": "HIGH",
            })
        elif roas >= 1.0:
            new_budget = max(budget * 0.85, budget - 20)
            recs.append({
                "campaign": name,
                "campaign_id": cr["campaign_id"],
                "action": "WATCH",
                "current_budget": budget,
                "proposed_budget": round(new_budget, 0),
                "change_pct": round((new_budget - budget) / budget * 100, 1),
                "rationale": f"Break-even: {roas:.1f}x ROAS, ${ncac:.0f} nCAC — consider decreasing if trend continues",
                "confidence": "MEDIUM",
            })
        else:
            new_budget = max(budget * 0.70, 10)  # -30% or $10 floor
            recs.append({
                "campaign": name,
                "campaign_id": cr["campaign_id"],
                "action": "DECREASE",
                "current_budget": budget,
                "proposed_budget": round(new_budget, 0),
                "change_pct": round((new_budget - budget) / budget * 100, 1),
                "rationale": f"Underperforming: {roas:.1f}x ROAS, ${ncac:.0f} nCAC — losing money",
                "confidence": "HIGH",
            })

    return recs


def format_telegram_report(report):
    """Format the report for Telegram (HTML)."""
    import html as html_mod

    lines = [
        "📊 <b>Weekly GCLID Attribution Report</b>",
        f"📅 {report['start_date']} → {report['end_date']}",
        "━━━━━━━━━━━━━━━━━━━━━━━━\n",
    ]

    # Summary
    s = report["summary"]
    lines.append("<b>Summary</b>")
    lines.append(f"  • Total orders: {s['total_orders']}")
    lines.append(f"  • Google Ads orders: {s['google_ads_orders']}")
    lines.append(f"  • Organic/Direct: {s['organic_direct_orders']}")
    lines.append(f"  • Total ad spend: ${s['total_ad_spend']:,.0f}")
    lines.append(f"  • WC revenue (from ads): ${s['total_wc_revenue_from_ads']:,.0f}")
    lines.append(f"  • Blended ROAS (WC): {s['blended_roas']:.2f}x")
    lines.append("")

    # Per-campaign breakdown
    lines.append("<b>Campaign Attribution</b>")
    lines.append("<pre>")
    lines.append(f"{'Campaign':<28} {'Spend':>8} {'Rev':>8} {'ROAS':>5} {'New':>4} {'nCAC':>7}")
    lines.append(f"{'─' * 28} {'─' * 8} {'─' * 8} {'─' * 5} {'─' * 4} {'─' * 7}")

    for c in report["campaigns"]:
        name = c["campaign_name"][:27]
        ncac_str = f"${c['ncac']:,.0f}" if c["ncac"] != float("inf") else "N/A"
        lines.append(
            f"{name:<28} ${c['spend']:>7,.0f} ${c['wc_revenue']:>7,.0f} "
            f"{c['roas_wc']:>4.1f}x {c['new_customers']:>3} {ncac_str:>7}"
        )
    lines.append("</pre>")
    lines.append("")

    # Budget recommendations
    recs = report["recommendations"]
    if recs:
        lines.append("<b>Budget Recommendations</b> (30% guardrails)")
        lines.append("")

        for r in recs:
            action = r["action"]
            emoji = {"INCREASE": "📈", "DECREASE": "📉", "HOLD": "➡️", "WATCH": "👀"}.get(action, "❓")
            name = html_mod.escape(r["campaign"])

            if action in ("INCREASE", "DECREASE"):
                lines.append(
                    f"{emoji} <b>{name}</b>: ${r['current_budget']:.0f} → "
                    f"${r['proposed_budget']:.0f}/day ({r['change_pct']:+.0f}%)"
                )
            elif action == "HOLD":
                lines.append(f"{emoji} <b>{name}</b>: ${r['current_budget']:.0f}/day — hold")
            elif action == "WATCH":
                lines.append(
                    f"{emoji} <b>{name}</b>: ${r['current_budget']:.0f}/day — watch "
                    f"(consider ${r['proposed_budget']:.0f})"
                )
            lines.append(f"   <i>{html_mod.escape(r['rationale'])}</i>")
            lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📋 <i>Budget changes require approval via drip cycle (Mon/Thu)</i>")

    return "\n".join(lines)


def main():
    env = _load_env()
    local_only = "--local" in sys.argv

    report = generate_report(env, days=7)

    # Print summary to stdout
    s = report["summary"]
    print(f"\n{'=' * 60}")
    print(f"WEEKLY ATTRIBUTION REPORT ({report['start_date']} → {report['end_date']})")
    print(f"{'=' * 60}")
    print(f"Total orders: {s['total_orders']}")
    print(f"Google Ads orders: {s['google_ads_orders']}")
    print(f"Organic/Direct: {s['organic_direct_orders']}")
    print(f"Ad spend: ${s['total_ad_spend']:,.0f}")
    print(f"WC revenue from ads: ${s['total_wc_revenue_from_ads']:,.0f}")
    print(f"Blended ROAS: {s['blended_roas']:.2f}x")
    print()

    for c in report["campaigns"]:
        ncac_str = f"${c['ncac']:.0f}" if c["ncac"] != float("inf") else "N/A"
        print(
            f"  {c['campaign_name']:<35} ${c['spend']:>8,.0f}  "
            f"Rev ${c['wc_revenue']:>8,.0f}  ROAS {c['roas_wc']:>5.1f}x  "
            f"New {c['new_customers']:>3}  nCAC {ncac_str:>7}"
        )
    print()

    for r in report["recommendations"]:
        action = r["action"]
        if action in ("INCREASE", "DECREASE"):
            print(f"  {action}: {r['campaign']}: ${r['current_budget']:.0f} → ${r['proposed_budget']:.0f}/day ({r['change_pct']:+.0f}%)")
        else:
            print(f"  {action}: {r['campaign']}: ${r['current_budget']:.0f}/day")
        print(f"    → {r['rationale']}")
    print()

    if not local_only:
        from telegram_bot import TelegramBot
        bot = TelegramBot()
        telegram_msg = format_telegram_report(report)
        bot.send_message(telegram_msg)
        log.info("Report sent to Telegram")


if __name__ == "__main__":
    main()
