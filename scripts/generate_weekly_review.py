#!/usr/bin/env python3
"""Generate the Monday weekly Klaviyo review markdown file.

Usage:
    python3 scripts/generate_weekly_review.py                     # Upcoming Monday
    python3 scripts/generate_weekly_review.py 2026-04-20           # Specific Monday

Writes to: marketing/klaviyo-audit/reviews/weekly/<YYYY-MM-DD>-weekly-review.md
"""

import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

# Make framework package importable
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "marketing" / "klaviyo-audit"))

from framework.klaviyo_client import KlaviyoClient
from framework.review_generator import build_weekly_review_markdown
from framework.wc_revenue import get_wc_revenue_for_week


# ── env loading (manual — matches infrastructure/daily-report pattern) ──
env_path = REPO_ROOT / ".env"
if not env_path.exists():
    print(f"[ERROR] .env not found at {env_path}. Copy .env.example and fill in KLAVIYO_API.", file=sys.stderr)
    sys.exit(1)

env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

KLAVIYO_API_KEY = env_vars.get("KLAVIYO_API")
if not KLAVIYO_API_KEY:
    print("[ERROR] KLAVIYO_API not set in .env", file=sys.stderr)
    sys.exit(1)
SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_API_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")
CONVERSION_METRIC_ID = "VLbLXB"  # WooCommerce Placed Order

# Known flow IDs from spec / SKILL.md
FLOW_IDS = {
    "NnjZbq": "2025 - Welcome Series",
    "SxbaYQ": "Checkout Abandonment - GS",
    "Y7Qm8F": "Abandoned Cart Reminder",
    "Xz9k4a": "Browse Abandonment - Standard",
    "VvvqpW": "Winback Flow",
    "VZsFVy": "Upsell Flow",
    "UZf9UD": "Sunset Flow",
    "UhxNKt": "Shipment Flow - WooCommerce",
    "TFkMLx": "Yard Plan Welcome Flow",
}


def next_monday(from_date: date) -> date:
    """Return the next Monday on or after `from_date`."""
    days_ahead = (7 - from_date.weekday()) % 7
    return from_date + timedelta(days=days_ahead)


def _get_wc_revenue(start_date: str, end_date: str) -> float:
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        print("[WARN] SUPABASE_URL or SUPABASE_SECRET_API_KEY not set — WC revenue will show $0", file=sys.stderr)
        return 0.0
    try:
        return get_wc_revenue_for_week(start_date, end_date, SUPABASE_URL, SUPABASE_API_KEY)
    except Exception as e:
        print(f"[WARN] Supabase WC revenue query failed: {e}", file=sys.stderr)
        return 0.0


def main(argv: list) -> int:
    if len(argv) > 1:
        target_monday = datetime.strptime(argv[1], "%Y-%m-%d").date()
    else:
        target_monday = next_monday(date.today())

    client = KlaviyoClient(api_key=KLAVIYO_API_KEY)

    # Pull per-flow reports
    flow_stats: dict = {}
    flow_revenue_total = 0.0
    for flow_id, flow_name in FLOW_IDS.items():
        try:
            attrs = client.get_flow_report(
                flow_id=flow_id,
                statistics=["recipients", "conversions", "conversion_value", "conversion_rate"],
                conversion_metric_id=CONVERSION_METRIC_ID,
                timeframe_key="last_7_days",
            )
            recipients = attrs.get("recipients", 0)
            revenue = attrs.get("conversion_value", 0.0)
            flow_stats[flow_id] = {
                "name": flow_name,
                "recipients": recipients,
                "revenue": revenue,
                "conversion_rate": attrs.get("conversion_rate", 0.0),
            }
            flow_revenue_total += revenue
            time.sleep(0.4)  # Klaviyo reporting API rate limit — 429 on rapid sequential POSTs
        except Exception as e:  # noqa: BLE001 — log and continue
            print(f"[WARN] flow {flow_id} ({flow_name}): {e}", file=sys.stderr)
            flow_stats[flow_id] = {
                "name": flow_name,
                "recipients": 0,
                "revenue": 0.0,
                "conversion_rate": 0.0,
            }

    # Campaign aggregate revenue (placeholder — refined in Plan 2 via campaign IDs)
    campaign_revenue_total = 0.0

    # Real deliverability metrics from Klaviyo metric aggregates
    total_sends_for_gates = sum(s["recipients"] for s in flow_stats.values())
    end_date_str = target_monday.isoformat()
    start_date_str = (target_monday - timedelta(days=30)).isoformat()
    try:
        deliverability_metrics = client.get_deliverability_metrics(
            start_date=start_date_str,
            end_date=end_date_str,
            total_sends=total_sends_for_gates,
        )
        time.sleep(0.4)
    except Exception as e:
        print(f"[WARN] deliverability metrics failed: {e}", file=sys.stderr)
        deliverability_metrics = {
            "net_list_growth_30d": 0,
            "spam_rate_30d": 0.0,
            "bounce_rate_30d": 0.0,
            "unsub_rate_per_send_30d": 0.0,
        }

    data = {
        "week_of": target_monday,
        "total_sends": sum(s["recipients"] for s in flow_stats.values()),
        "recipients": sum(s["recipients"] for s in flow_stats.values()),
        "opens_unique": 0,            # populated in Plan 2
        "clicks_unique": 0,           # populated in Plan 2
        "email_revenue": flow_revenue_total + campaign_revenue_total,
        "flow_revenue": flow_revenue_total,
        "campaign_revenue": campaign_revenue_total,
        "total_wc_revenue": _get_wc_revenue(start_date_str, end_date_str),
        "flow_stats": flow_stats,
        "campaigns_sent": [],
        "campaigns_proposed": _phase_0_and_phase_1_proposals(),
        "deliverability_metrics": deliverability_metrics,
        "prior_flow_share": 0.08,
        "prior_flow_revenue": 0.0,
        "medium_alerts": 0,
        "critical_alerts": 0,
        "anomalies": [
            "Winback flow `VvvqpW` had 0 conversions YTD on 774 sends — queued for "
            "Phase 0 fix (see winback-fix/ proposals in this file).",
            "Net list growth remains negative (-558 YTD as of 2026-03-10). Aggressive "
            "mode stays locked until rolling-30d growth turns positive.",
        ],
        "experiment_recommendation": (
            "Once Phase 0 Winback fix is approved + deployed, A/B test subject lines on "
            "Winback Email 3: 'We miss you — $15 off to come back' vs 'One last spring "
            "reminder from Nature's Seed'. Sample: 50/50 split on At Risk + Lapsed segments."
        ),
    }

    markdown = build_weekly_review_markdown(data)

    # Append Winback proposals section
    markdown += "\n\n---\n\n## Phase 0: Winback Fix — Awaiting Approval\n\n"
    markdown += ("The current Winback flow (`VvvqpW`) has 0 conversions on 774 sends YTD "
                 "(rated D). Per spec Phase 0, we propose rewriting Email 2 and adding "
                 "Emails 3–5 with real offers + urgency. Proposals are in "
                 "`marketing/klaviyo-audit/winback-fix/`. Approve each below:\n\n")
    for n in (2, 3, 4, 5):
        markdown += (f"### Winback Email {n} proposal\n\n"
                     f"→ Full copy at `marketing/klaviyo-audit/winback-fix/email_{n}_proposal.md`\n\n"
                     "- [ ] ✅ APPROVED — deploy to Klaviyo\n"
                     "- [ ] ❌ REJECTED — reason:\n"
                     "- [ ] 🔄 REVISE — change:\n\n")

    # Write file
    out_dir = REPO_ROOT / "marketing" / "klaviyo-audit" / "reviews" / "weekly"
    out_path = out_dir / f"{target_monday.isoformat()}-weekly-review.md"
    out_path.write_text(markdown)
    print(f"[OK] Wrote {out_path}")
    return 0


def _phase_0_and_phase_1_proposals() -> list:
    """Hard-coded first-week proposals (Phase 0 + Phase 1 kickoff). Plan 2 will
    generate these dynamically once campaign proposal generator exists."""
    return [
        {
            "name": "Phase 0: Winback Fix deployment (after copy approval)",
            "audience": "At Risk (RyASXF) + Lapsed (Sv5cSC)",
            "estimated_rpr": 0.50,
        },
        {
            "name": "Phase 1 Kickoff: Build Seasonal Reorder flow for Warm × Lawn Warm Season",
            "audience": "WdpJti Warm × Ra4637 Lawn Purchasers",
            "estimated_rpr": 0.85,
        },
    ]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
