"""Tests for framework.review_generator."""

import pytest
from datetime import date

from framework.review_generator import build_weekly_review_markdown


def test_review_contains_required_sections():
    """Weekly review must include all 10 template sections from spec §5.2."""
    data = {
        "week_of": date(2026, 4, 20),
        "total_sends": 42,
        "recipients": 15400,
        "opens_unique": 6400,
        "clicks_unique": 520,
        "email_revenue": 18450.0,
        "flow_revenue": 6200.0,
        "campaign_revenue": 12250.0,
        "total_wc_revenue": 98000.0,
        "flow_stats": {
            "SxbaYQ": {"name": "Checkout Abandonment - GS", "recipients": 412, "revenue": 3180.0, "conversion_rate": 0.041},
            "VvvqpW": {"name": "Winback Flow", "recipients": 188, "revenue": 0.0, "conversion_rate": 0.0},
        },
        "campaigns_sent": [
            {"name": "Spring Replant Email 1", "recipients": 2100, "revenue": 1400.0, "rpr": 0.67},
        ],
        "campaigns_proposed": [
            {"name": "Replant Reminder — Lawn Cool Season", "audience": "WdpJti × Ra4637", "estimated_rpr": 0.85},
        ],
        "deliverability_metrics": {
            "net_list_growth_30d": -42,
            "spam_rate_30d": 0.0002,
            "bounce_rate_30d": 0.004,
            "unsub_rate_per_send_30d": 0.0025,
        },
        "prior_flow_share": 0.08,
        "prior_flow_revenue": 5900.0,
        "medium_alerts": 0,
        "critical_alerts": 0,
        "anomalies": ["Winback flow 0 conversions for 3rd consecutive week"],
        "experiment_recommendation": "A/B test subject line: 'Time to reorder?' vs 'Your seed is almost gone'",
    }
    md = build_weekly_review_markdown(data)

    # Required H2 sections
    required = [
        "## Week at a glance",
        "## Flow scorecard",
        "## Campaign scorecard",
        "## Segment health check",
        "## Deliverability gate snapshot",
        "## Agent self-grade",
        "## Anomalies / wins",
        "## Proposed next-week calendar",
        "## Experiment recommendation",
        "## Approvals",
    ]
    for section in required:
        assert section in md, f"Missing section: {section}"


def test_review_renders_approval_placeholders():
    """Every proposed campaign must have ✅/❌/🔄 placeholders for user."""
    data = _minimal_data_with_one_proposal()
    md = build_weekly_review_markdown(data)
    assert "✅ APPROVED" in md
    assert "❌ REJECTED" in md
    assert "🔄 REVISE" in md


def test_review_includes_gate_status_table():
    data = _minimal_data_with_one_proposal()
    md = build_weekly_review_markdown(data)
    assert "net_list_growth" in md
    assert "spam_rate" in md


def test_review_contains_self_grade_with_reasoning():
    data = _minimal_data_with_one_proposal()
    md = build_weekly_review_markdown(data)
    # Should contain an A/B/C/D letter grade
    assert any(f"**{g}**" in md for g in ["A", "B", "C", "D"])


def _minimal_data_with_one_proposal():
    return {
        "week_of": date(2026, 4, 20),
        "total_sends": 0,
        "recipients": 0,
        "opens_unique": 0,
        "clicks_unique": 0,
        "email_revenue": 0.0,
        "flow_revenue": 0.0,
        "campaign_revenue": 0.0,
        "total_wc_revenue": 0.0,
        "flow_stats": {},
        "campaigns_sent": [],
        "campaigns_proposed": [
            {"name": "Test Proposal", "audience": "Warm", "estimated_rpr": 0.50},
        ],
        "deliverability_metrics": {
            "net_list_growth_30d": 0,
            "spam_rate_30d": 0.0,
            "bounce_rate_30d": 0.0,
            "unsub_rate_per_send_30d": 0.0,
        },
        "prior_flow_share": 0.0,
        "prior_flow_revenue": 0.0,
        "medium_alerts": 0,
        "critical_alerts": 0,
        "anomalies": [],
        "experiment_recommendation": "",
    }
