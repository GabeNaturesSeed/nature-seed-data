import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate_seasonality import (
    normalize,
    invert_normalize,
    compute_demand_index,
    compute_performance_index,
    compute_seasonality_index,
    label_for_index,
    iso_week,
    compute_index_for_week,
)


# ── normalize ──────────────────────────────────────────────

def test_normalize_above_mean():
    assert normalize(120.0, 100.0) == 1.2

def test_normalize_below_mean():
    assert normalize(80.0, 100.0) == 0.8

def test_normalize_at_mean():
    assert normalize(100.0, 100.0) == 1.0

def test_normalize_zero_mean_returns_none():
    assert normalize(100.0, 0.0) is None

def test_normalize_caps_at_2():
    assert normalize(300.0, 100.0) == 2.0


# ── invert_normalize ───────────────────────────────────────

def test_invert_normalize_lower_is_better():
    # budget lost 0.08 vs avg 0.15 → better performance
    result = invert_normalize(0.08, 0.15)
    assert result is not None
    assert result > 1.0  # better than average

def test_invert_normalize_higher_is_worse():
    # budget lost 0.25 vs avg 0.15 → worse performance
    result = invert_normalize(0.25, 0.15)
    assert result is not None
    assert result < 1.0

def test_invert_normalize_at_mean():
    result = invert_normalize(0.15, 0.15)
    assert result is not None
    assert abs(result - 1.0) < 0.001


# ── compute_demand_index ───────────────────────────────────

def test_demand_index_both_signals():
    result = compute_demand_index(1.2, 1.4)
    assert abs(result - 1.3) < 0.001

def test_demand_index_one_signal_none():
    result = compute_demand_index(1.2, None)
    assert abs(result - 1.2) < 0.001

def test_demand_index_both_none():
    assert compute_demand_index(None, None) is None


# ── compute_performance_index ──────────────────────────────

def test_performance_index_all_signals():
    result = compute_performance_index(1.1, 1.3, 0.9)
    assert abs(result - round((1.1 + 1.3 + 0.9) / 3, 4)) < 0.001

def test_performance_index_partial_signals():
    result = compute_performance_index(1.2, None, None)
    assert abs(result - 1.2) < 0.001

def test_performance_index_all_none():
    assert compute_performance_index(None, None, None) is None


# ── compute_seasonality_index ──────────────────────────────

def test_seasonality_index_average_of_both():
    result = compute_seasonality_index(1.4, 1.2)
    assert abs(result - 1.3) < 0.001

def test_seasonality_index_clamped_to_zero():
    result = compute_seasonality_index(0.0, 0.0)
    assert result == 0.0

def test_seasonality_index_clamped_to_two():
    result = compute_seasonality_index(2.0, 2.0)
    assert result == 2.0

def test_seasonality_index_one_none():
    result = compute_seasonality_index(1.4, None)
    assert abs(result - 1.4) < 0.001


# ── label_for_index ────────────────────────────────────────

def test_label_deep_off_season():
    assert label_for_index(0.3) == "Deep Off-Season"

def test_label_slow_period():
    assert label_for_index(0.65) == "Slow Period"

def test_label_average():
    assert label_for_index(1.0) == "Average"

def test_label_approaching_peak():
    assert label_for_index(1.4) == "Approaching Peak"

def test_label_peak_season():
    assert label_for_index(1.8) == "Peak Season"

def test_label_none():
    assert label_for_index(None) == "Insufficient Data"


# ── iso_week ───────────────────────────────────────────────

def test_iso_week_jan_1():
    # 2024-01-01 is week 1
    assert iso_week("2024-01-01") == 1

def test_iso_week_mid_year():
    # 2024-07-01 is week 27
    assert iso_week("2024-07-01") == 27


# ── compute_index_for_week ─────────────────────────────────

def test_compute_index_for_week_above_average():
    baselines = {
        "17": {
            "revenue_mean": 40000.0,
            "orders_mean": 260.0,
            "ad_spend_mean": 13000.0,
            "mer_mean": 3.0,
            "is_rank_mean": 0.62,
            "is_budget_lost_mean": 0.14,
        }
    }
    wc_week = {"revenue": 48000.0, "orders": 312.0}
    gads_week = {"cost": 15000.0, "is_rank": 0.68, "is_budget_lost": 0.10}
    result = compute_index_for_week(17, wc_week, gads_week, baselines)
    assert result["seasonality"] is not None
    assert result["seasonality"] > 1.0
    assert result["demand"] > 1.0
    assert result["performance"] > 1.0
    assert result["label"] in ("Approaching Peak", "Peak Season", "Average")

def test_compute_index_for_week_missing_baseline():
    result = compute_index_for_week(17, {}, {}, {})
    assert result["seasonality"] is None
    assert result["label"] == "Insufficient Data"
