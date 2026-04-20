"""Tests for framework.kpi_calculator."""

import pytest

from framework.kpi_calculator import (
    flow_revenue_share,
    acquisition_flow_rpr,
    email_revenue_share_of_wc,
    agent_grade,
)


def test_flow_revenue_share_returns_ratio():
    """C-metric: flow_revenue / (flow_revenue + campaign_revenue)."""
    result = flow_revenue_share(flow_revenue=34361.0, campaign_revenue=50499.0)
    assert round(result, 3) == 0.405  # 40.5% (example scenario)


def test_flow_revenue_share_zero_total_returns_zero():
    """Safe when no revenue at all."""
    assert flow_revenue_share(flow_revenue=0, campaign_revenue=0) == 0.0


def test_acquisition_flow_rpr_averages_across_three_flows():
    """Average of RPR for Cart, Browse, Checkout recovery flows."""
    flow_stats = {
        "Y7Qm8F": {"recipients": 311, "revenue": 2074.0},       # Cart Abandonment
        "Xz9k4a": {"recipients": 392, "revenue": 1277.0},       # Browse Abandonment
        "SxbaYQ": {"recipients": 3208, "revenue": 29314.0},     # Checkout Abandonment
    }
    result = acquisition_flow_rpr(flow_stats)
    # Individual RPRs: 6.67, 3.26, 9.14 → mean 6.36
    assert 6.3 <= result <= 6.5


def test_acquisition_flow_rpr_skips_zero_recipient_flows():
    """Zero-recipient flow doesn't pollute average with NaN."""
    flow_stats = {
        "Y7Qm8F": {"recipients": 0, "revenue": 0},
        "Xz9k4a": {"recipients": 392, "revenue": 1277.0},
    }
    result = acquisition_flow_rpr(flow_stats)
    assert round(result, 2) == 3.26


def test_email_revenue_share_of_wc():
    """A-metric: (flow + campaign) / total_wc."""
    result = email_revenue_share_of_wc(
        flow_revenue=34361.0,
        campaign_revenue=50499.0,
        total_wc_revenue=393207.0,
    )
    assert round(result, 3) == 0.216  # 21.6%


def test_agent_grade_a_when_primary_grows_and_gates_pass():
    assert agent_grade(
        flow_share_pct_change=6.5,
        gates_all_passing=True,
        critical_alerts=0,
        medium_alerts=0,
        flow_revenue_pct_change=5.0,
    ) == "A"


def test_agent_grade_d_when_critical_alert():
    assert agent_grade(
        flow_share_pct_change=10,
        gates_all_passing=True,
        critical_alerts=1,
        medium_alerts=0,
        flow_revenue_pct_change=5.0,
    ) == "D"


def test_agent_grade_c_when_primary_metric_shrinks():
    assert agent_grade(
        flow_share_pct_change=-2.0,
        gates_all_passing=True,
        critical_alerts=0,
        medium_alerts=0,
        flow_revenue_pct_change=-3.0,
    ) == "C"


def test_agent_grade_b_when_flat_and_healthy():
    assert agent_grade(
        flow_share_pct_change=2.0,
        gates_all_passing=True,
        critical_alerts=0,
        medium_alerts=0,
        flow_revenue_pct_change=1.0,
    ) == "B"
