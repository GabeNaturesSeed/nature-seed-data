"""KPI computations for the Klaviyo framework (spec §5.1).

Metrics:
    Primary (C): Flow revenue % of email revenue
    Secondary (A-for-acquisition): RPR on Cart/Browse/Checkout recovery flows
    Board-facing: Email-attributed % of total WooCommerce revenue
    Self-grading: A/B/C/D letter per spec §5.5
"""

from statistics import mean
from typing import Dict, Iterable

# Flow IDs for acquisition-adjacent flows (per spec — serve NEW customers)
ACQUISITION_FLOW_IDS: tuple = (
    "Y7Qm8F",   # Abandoned Cart Reminder
    "Xz9k4a",   # Browse Abandonment - Standard
    "SxbaYQ",   # Checkout Abandonment - GS
)


def flow_revenue_share(flow_revenue: float, campaign_revenue: float) -> float:
    """Primary C-metric: flow revenue / total email revenue (flow + campaign)."""
    total = flow_revenue + campaign_revenue
    if total == 0:
        return 0.0
    return flow_revenue / total


def acquisition_flow_rpr(flow_stats: Dict[str, Dict[str, float]]) -> float:
    """Secondary A-metric: average RPR across acquisition-adjacent flows.

    flow_stats maps flow_id -> {"recipients": int, "revenue": float}.
    Only flows matching ACQUISITION_FLOW_IDS with recipients > 0 are counted.
    """
    rprs = []
    for flow_id in ACQUISITION_FLOW_IDS:
        stats = flow_stats.get(flow_id)
        if not stats:
            continue
        recipients = stats.get("recipients", 0)
        if recipients == 0:
            continue
        rprs.append(stats.get("revenue", 0.0) / recipients)
    if not rprs:
        return 0.0
    return mean(rprs)


def email_revenue_share_of_wc(
    flow_revenue: float,
    campaign_revenue: float,
    total_wc_revenue: float,
) -> float:
    """Board-facing metric: email-attributed revenue / total WC revenue."""
    if total_wc_revenue == 0:
        return 0.0
    return (flow_revenue + campaign_revenue) / total_wc_revenue


def agent_grade(
    flow_share_pct_change: float,
    gates_all_passing: bool,
    gates_failing: int = 0,
    critical_alerts: int = 0,
    medium_alerts: int = 0,
    flow_revenue_pct_change: float = 0.0,
) -> str:
    """Self-grading logic per spec §5.5.

    A — primary (C) grew >=5% WoW, all 4 gates passing, no critical alerts
    B — primary flat or grew <5%, gates passing, no critical alerts
    C — primary shrank, OR 1 gate failing, OR 1+ medium alerts
    D — 2+ gates failing, OR any critical alert, OR flow revenue dropped >10%
    """
    # D conditions (worst — check first)
    if gates_failing >= 2:
        return "D"
    if critical_alerts >= 1:
        return "D"
    if flow_revenue_pct_change <= -10.0:
        return "D"
    # A conditions
    if (
        flow_share_pct_change >= 5.0
        and gates_all_passing
        and medium_alerts == 0
    ):
        return "A"
    # C conditions (degraded)
    if flow_share_pct_change < 0 or not gates_all_passing or medium_alerts >= 1:
        return "C"
    # B default
    return "B"
