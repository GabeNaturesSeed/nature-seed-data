"""Weekly review markdown builder (spec §5.2).

Input is a dict of precomputed metrics + proposals; output is the full
markdown document that gets written to
`marketing/klaviyo-audit/reviews/weekly/YYYY-MM-DD-weekly-review.md`.
"""

from datetime import date
from typing import Any, Dict, List

from framework.deliverability_gates import check_all_gates
from framework.kpi_calculator import (
    flow_revenue_share,
    email_revenue_share_of_wc,
    agent_grade,
)


def build_weekly_review_markdown(data: Dict[str, Any]) -> str:
    """Render the full weekly review markdown from a data dict."""
    week_of: date = data["week_of"]
    flow_rev = data["flow_revenue"]
    camp_rev = data["campaign_revenue"]
    total_wc = data["total_wc_revenue"]

    # Compute metrics
    current_share = flow_revenue_share(flow_rev, camp_rev)
    prior_share = data.get("prior_flow_share", 0.0)
    share_pct_change = (current_share - prior_share) * 100

    prior_flow_rev = data.get("prior_flow_revenue", 0.0)
    if prior_flow_rev > 0:
        flow_rev_pct_change = ((flow_rev - prior_flow_rev) / prior_flow_rev) * 100
    else:
        flow_rev_pct_change = 0.0

    gates = check_all_gates(data["deliverability_metrics"])
    email_share_wc = email_revenue_share_of_wc(flow_rev, camp_rev, total_wc)
    grade = agent_grade(
        flow_share_pct_change=share_pct_change,
        gates_all_passing=gates.all_pass,
        gates_failing=sum(1 for g in gates.gates if not g.passing),
        critical_alerts=data.get("critical_alerts", 0),
        medium_alerts=data.get("medium_alerts", 0),
        flow_revenue_pct_change=flow_rev_pct_change,
    )

    # Build sections
    sections: List[str] = []
    sections.append(f"# Weekly Klaviyo Review — Week of {week_of.isoformat()}")
    sections.append("")
    sections.append("## Week at a glance")
    sections.append("")
    sections.append(f"- Total sends: {data['total_sends']}")
    sections.append(f"- Recipients: {data['recipients']:,}")
    sections.append(f"- Opens (unique): {data['opens_unique']:,}")
    sections.append(f"- Clicks (unique): {data['clicks_unique']:,}")
    sections.append(f"- Email revenue: ${data['email_revenue']:,.2f}")
    sections.append(f"  - Flow: ${flow_rev:,.2f}")
    sections.append(f"  - Campaign: ${camp_rev:,.2f}")
    sections.append(f"- **Flow revenue share (primary C-metric): {current_share*100:.1f}%** "
                    f"(WoW change: {share_pct_change:+.1f}pp)")
    sections.append(f"- Email share of WC revenue (board metric): {email_share_wc*100:.1f}%")
    sections.append("")

    # Flow scorecard
    sections.append("## Flow scorecard")
    sections.append("")
    sections.append("| Flow | Recipients | Revenue | Conv % |")
    sections.append("|---|---|---|---|")
    for flow_id, stats in data["flow_stats"].items():
        sections.append(
            f"| {stats.get('name', flow_id)} | {stats.get('recipients', 0):,} "
            f"| ${stats.get('revenue', 0):,.2f} "
            f"| {stats.get('conversion_rate', 0)*100:.2f}% |"
        )
    sections.append("")

    # Campaign scorecard
    sections.append("## Campaign scorecard")
    sections.append("")
    if data["campaigns_sent"]:
        sections.append("| Campaign | Recipients | Revenue | RPR |")
        sections.append("|---|---|---|---|")
        for c in data["campaigns_sent"]:
            sections.append(
                f"| {c['name']} | {c['recipients']:,} | ${c['revenue']:,.2f} | ${c['rpr']:.2f} |"
            )
    else:
        sections.append("_No campaigns sent this week._")
    sections.append("")

    # Segment health
    sections.append("## Segment health check")
    sections.append("")
    sections.append(f"- Net list growth (30d): {int(data['deliverability_metrics']['net_list_growth_30d']):+d}")
    sections.append("- (RFM transition data will populate here in Plan 2 when we have snapshots)")
    sections.append("")

    # Gate snapshot
    sections.append("## Deliverability gate snapshot")
    sections.append("")
    sections.append(gates.summary_markdown())
    sections.append("")
    if gates.all_pass:
        sections.append("→ **All gates passing. Aggressive mode eligible at next monthly review.**")
    else:
        sections.append("→ **One or more gates failing. Cadence remains in conservative mode.**")
    sections.append("")

    # Self-grade
    sections.append("## Agent self-grade")
    sections.append("")
    sections.append(f"**{grade}** — Flow share change {share_pct_change:+.1f}pp, "
                    f"gates {'passing' if gates.all_pass else 'failing'}, "
                    f"{data.get('critical_alerts', 0)} critical alert(s), "
                    f"{data.get('medium_alerts', 0)} medium alert(s), "
                    f"flow revenue change {flow_rev_pct_change:+.1f}%.")
    sections.append("")

    # Anomalies
    sections.append("## Anomalies / wins")
    sections.append("")
    if data["anomalies"]:
        for a in data["anomalies"]:
            sections.append(f"- {a}")
    else:
        sections.append("_None flagged this week._")
    sections.append("")

    # Proposed calendar
    sections.append("## Proposed next-week calendar")
    sections.append("")
    for i, prop in enumerate(data["campaigns_proposed"], start=1):
        sections.append(f"### Proposal {i}: {prop['name']}")
        sections.append(f"- Audience: {prop['audience']}")
        sections.append(f"- Estimated RPR: ${prop['estimated_rpr']:.2f}")
        sections.append("")
        sections.append("**Your decision:**")
        sections.append("- [ ] ✅ APPROVED")
        sections.append("- [ ] ❌ REJECTED — reason:")
        sections.append("- [ ] 🔄 REVISE — change:")
        sections.append("")

    # Experiment recommendation
    sections.append("## Experiment recommendation")
    sections.append("")
    sections.append(data.get("experiment_recommendation") or "_None this week._")
    sections.append("")

    # Approvals footer
    sections.append("## Approvals")
    sections.append("")
    sections.append("_Add inline comments above in the proposal boxes. This section is for "
                    "overall direction notes or escalations._")
    sections.append("")
    sections.append("**Status:** ⬜ Awaiting review")

    return "\n".join(sections)
