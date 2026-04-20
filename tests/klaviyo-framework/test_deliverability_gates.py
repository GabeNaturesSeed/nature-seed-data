"""Tests for framework.deliverability_gates."""

import pytest

from framework.deliverability_gates import (
    check_all_gates,
    GateStatus,
)


def test_all_gates_pass_unlocks_aggressive_mode():
    """All four gates green → aggressive mode allowed."""
    metrics = {
        "net_list_growth_30d": 120,      # >=0 ✅
        "spam_rate_30d": 0.0002,         # <0.1% ✅
        "bounce_rate_30d": 0.005,        # <1% ✅
        "unsub_rate_per_send_30d": 0.0022,  # <0.3% ✅
    }
    result = check_all_gates(metrics)
    assert result.all_pass is True
    assert result.mode_unlocked is True
    assert all(g.passing for g in result.gates)


def test_one_failing_gate_blocks_aggressive_mode():
    """Any gate red → conservative mode only."""
    metrics = {
        "net_list_growth_30d": -558,     # NEGATIVE — fails
        "spam_rate_30d": 0.0002,
        "bounce_rate_30d": 0.005,
        "unsub_rate_per_send_30d": 0.0022,
    }
    result = check_all_gates(metrics)
    assert result.all_pass is False
    assert result.mode_unlocked is False
    list_growth_gate = next(g for g in result.gates if g.name == "net_list_growth")
    assert list_growth_gate.passing is False


def test_each_gate_has_name_threshold_and_current():
    """Gate status includes name, threshold, actual value, and pass/fail."""
    metrics = {
        "net_list_growth_30d": 0,
        "spam_rate_30d": 0.0005,
        "bounce_rate_30d": 0.0099,
        "unsub_rate_per_send_30d": 0.0029,
    }
    result = check_all_gates(metrics)
    names = {g.name for g in result.gates}
    assert names == {"net_list_growth", "spam_rate", "bounce_rate", "unsub_rate"}
    for gate in result.gates:
        assert gate.threshold is not None
        assert gate.current is not None
        assert gate.passing is True  # boundary pass


def test_result_renders_checkmark_summary():
    """GateStatus.summary returns ✅/❌ block for review doc inclusion."""
    metrics = {
        "net_list_growth_30d": -558,
        "spam_rate_30d": 0.0002,
        "bounce_rate_30d": 0.005,
        "unsub_rate_per_send_30d": 0.0022,
    }
    result = check_all_gates(metrics)
    summary = result.summary_markdown()
    assert "❌" in summary
    assert "✅" in summary
    assert "net_list_growth" in summary
