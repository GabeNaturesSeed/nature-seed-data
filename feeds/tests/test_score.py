import pytest
from feeds.benchmark.score import (
    score_coverage,
    score_quality,
    score_drift,
    compute_composite,
    compute_trend,
    rag,
    COVERAGE_THRESHOLDS,
    QUALITY_THRESHOLDS,
    DRIFT_THRESHOLDS,
)


# --- score_coverage ---

def test_coverage_full_at_peak():
    # 100% coverage at peak (index 1.0), baseline 0.9 → score = min(100, 1.0/0.9*100) = 100
    assert score_coverage(channel_total=90, wc_total=100, baseline_ratio=0.9, seasonality_index=1.0) == 100

def test_coverage_relaxed_at_offseason():
    # 42% actual vs 42% baseline at 0.537 index → expected = 0.42*0.537 = 0.226 → score = min(100, 0.42/0.226*100) = 100
    score = score_coverage(channel_total=200, wc_total=478, baseline_ratio=0.42, seasonality_index=0.537)
    assert score == 100

def test_coverage_low_at_peak():
    # 42% actual vs 90% baseline at index 1.0 → expected = 0.9 → score = round(0.42/0.9*100) = round(46.67) = 47
    score = score_coverage(channel_total=42, wc_total=100, baseline_ratio=0.9, seasonality_index=1.0)
    assert score == 47  # min(100, round(42/90*100))

def test_coverage_zero_wc_total():
    assert score_coverage(channel_total=0, wc_total=0, baseline_ratio=0.9, seasonality_index=1.0) is None


# --- score_quality ---

def test_quality_perfect():
    assert score_quality(incomplete_count=0, channel_total=100) == 100

def test_quality_partial():
    assert score_quality(incomplete_count=10, channel_total=100) == 90

def test_quality_zero_channel():
    assert score_quality(incomplete_count=0, channel_total=0) is None


# --- score_drift ---

def test_drift_perfect():
    assert score_drift(drift_price=0, drift_stock=0, channel_total=100, is_discovery=False) == 100

def test_drift_stock_penalty():
    # 10 stock drifts out of 100 → weighted = 10*1.5/100*100 = 15 → score = 85
    assert score_drift(drift_price=0, drift_stock=10, channel_total=100, is_discovery=False) == 85

def test_drift_price_penalty():
    # 10 price drifts out of 100 → weighted = 10*2.0/100*100 = 20 → score = 80
    assert score_drift(drift_price=10, drift_stock=0, channel_total=100, is_discovery=False) == 80

def test_drift_discovery_always_100():
    assert score_drift(drift_price=50, drift_stock=50, channel_total=100, is_discovery=True) == 100

def test_drift_zero_channel():
    assert score_drift(drift_price=0, drift_stock=0, channel_total=0, is_discovery=False) is None


# --- compute_composite ---

def test_composite_all_present():
    # 80*0.4 + 90*0.35 + 70*0.25 = 32+31.5+17.5 = 81
    result = compute_composite(coverage=80, quality=90, drift=70)
    assert result == 81

def test_composite_missing_drift():
    # coverage 0.4, quality 0.35, drift None → renormalize to 0.4+0.35=0.75
    result = compute_composite(coverage=80, quality=90, drift=None)
    assert result == round((80*0.4 + 90*0.35) / (0.4+0.35))

def test_composite_all_none():
    assert compute_composite(coverage=None, quality=None, drift=None) is None


# --- compute_trend ---

def test_trend_new_with_few_snapshots():
    assert compute_trend("walmart", [], 80) == "NEW"
    assert compute_trend("walmart", [{}]*3, 80) == "NEW"

def test_trend_improving():
    snapshots = [{"channels": {"walmart": {"composite": 60}}} for _ in range(4)]
    assert compute_trend("walmart", snapshots, 70) == "↑"

def test_trend_declining():
    snapshots = [{"channels": {"walmart": {"composite": 80}}} for _ in range(4)]
    assert compute_trend("walmart", snapshots, 70) == "↓"

def test_trend_stable():
    snapshots = [{"channels": {"walmart": {"composite": 75}}} for _ in range(4)]
    assert compute_trend("walmart", snapshots, 75) == "→"


# --- rag ---

def test_rag_green():
    assert rag(95, QUALITY_THRESHOLDS) == "🟢"

def test_rag_amber():
    assert rag(85, QUALITY_THRESHOLDS) == "🟡"

def test_rag_red():
    assert rag(70, QUALITY_THRESHOLDS) == "🔴"

def test_rag_none():
    assert rag(None, QUALITY_THRESHOLDS) == "ERROR"


# --- build_snapshot integration ---

from feeds.benchmark.score import build_snapshot, CHANNEL_BASELINES

MOCK_RESULTS = [
    {
        "channel": "walmart",
        "error": "",
        "coverage": {"wc_total": 478, "channel_total": 200, "missing_skus": []},
        "drift": {"drifted": [
            {"sku": "A", "field": "stock_status", "wc": "instock", "channel": "outofstock"},
            {"sku": "B", "field": "price", "wc": "10.00", "channel": "12.00"},
        ]},
        "quality": {"incomplete": [{"sku": "X", "missing_fields": ["gtin"]}] * 55},
    },
    {
        "channel": "shopper_approved",
        "error": "",
        "coverage": {"wc_total": 478, "channel_total": 474, "missing_skus": []},
        "drift": {"drifted": []},
        "quality": {"incomplete": []},
    },
    {
        "channel": "amazon",
        "error": "401 Unauthorized",
        "coverage": None,
        "drift": None,
        "quality": None,
    },
]

MOCK_SEASONALITY = {"index": 0.537, "label": "Deep Off-Season", "iso_week": 18}


def test_build_snapshot_walmart_scores():
    snapshot = build_snapshot(MOCK_RESULTS, MOCK_SEASONALITY, CHANNEL_BASELINES)
    walmart = snapshot["channels"]["walmart"]
    assert walmart["coverage_score"] == 100
    assert walmart["quality_score"] == round((1 - 55/200) * 100)
    # drift: 1 price (weight 2.0) + 1 stock (weight 1.5) out of 200
    # weighted = (1*2.0 + 1*1.5)/200*100 = 1.75 → score = 98
    assert walmart["drift_score"] == 98
    assert walmart["composite"] is not None


def test_build_snapshot_discovery_drift_is_100():
    snapshot = build_snapshot(MOCK_RESULTS, MOCK_SEASONALITY, CHANNEL_BASELINES)
    assert snapshot["channels"]["shopper_approved"]["drift_score"] == 100


def test_build_snapshot_error_channel():
    snapshot = build_snapshot(MOCK_RESULTS, MOCK_SEASONALITY, CHANNEL_BASELINES)
    assert "error" in snapshot["channels"]["amazon"]


def test_build_snapshot_metadata():
    snapshot = build_snapshot(MOCK_RESULTS, MOCK_SEASONALITY, CHANNEL_BASELINES)
    assert snapshot["iso_week"] == 18
    assert snapshot["season_label"] == "Deep Off-Season"
    assert snapshot["seasonality_index"] == 0.537
