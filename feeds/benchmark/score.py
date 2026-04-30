import json
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_PATH = _REPO_ROOT / "feeds/digest/latest_results.json"
SEASONALITY_PATH = _REPO_ROOT / "docs/data/seasonality.json"
BENCHMARK_PATH = _REPO_ROOT / "feeds/benchmark/benchmark.json"

CHANNEL_BASELINES = {
    "walmart": 0.42,
    "amazon": 0.90,
    "google_merchant": 0.67,
    "klaviyo": 0.95,
    "shopper_approved": 0.99,
    "reddit": 1.0,
    "facebook": 0.59,
    "pinterest": 1.0,
}

DISCOVERY_CHANNELS = {"reddit", "facebook", "pinterest", "shopper_approved"}

QUALITY_THRESHOLDS = {"green": 95, "amber": 80}
COVERAGE_THRESHOLDS = {"green": 90, "amber": 70}
DRIFT_THRESHOLDS = {"green": 90, "amber": 75}

CHANNEL_ORDER = ["walmart", "amazon", "google_merchant", "klaviyo",
                 "shopper_approved", "reddit", "facebook", "pinterest"]


def score_coverage(channel_total, wc_total, baseline_ratio, seasonality_index):
    if wc_total == 0:
        return None
    raw_ratio = channel_total / wc_total
    expected_ratio = baseline_ratio * seasonality_index
    if expected_ratio == 0:
        return None
    return min(100, round((raw_ratio / expected_ratio) * 100))


def score_quality(incomplete_count, channel_total):
    if channel_total == 0:
        return None
    return round((1 - incomplete_count / channel_total) * 100)


def score_drift(drift_price, drift_stock, channel_total, is_discovery):
    if is_discovery:
        return 100
    if channel_total == 0:
        return None
    weighted = (drift_price * 2.0 + drift_stock * 1.5) / channel_total * 100
    return min(100, max(0, round(100 - weighted)))


def rag(score, thresholds):
    if score is None:
        return "ERROR"
    if score >= thresholds["green"]:
        return "🟢"
    if score >= thresholds["amber"]:
        return "🟡"
    return "🔴"


def compute_composite(coverage, quality, drift):
    weights = {"coverage": (coverage, 0.4), "quality": (quality, 0.35), "drift": (drift, 0.25)}
    total_weight = sum(w for _, (v, w) in weights.items() if v is not None)
    if total_weight == 0:
        return None
    weighted_sum = sum(v * w for _, (v, w) in weights.items() if v is not None)
    return round(weighted_sum / total_weight)


def compute_trend(channel, snapshots, current_composite):
    if len(snapshots) < 4:
        return "NEW"
    recent = [s.get("channels", {}).get(channel, {}).get("composite") for s in snapshots[-4:]]
    recent = [r for r in recent if r is not None]
    if not recent or current_composite is None:
        return "→"
    avg = sum(recent) / len(recent)
    if current_composite > avg + 3:
        return "↑"
    if current_composite < avg - 3:
        return "↓"
    return "→"


def load_seasonality_index():
    with open(SEASONALITY_PATH) as f:
        idx = json.load(f)
    iso_week = str(date.today().isocalendar()[1])
    baselines = idx["weekly_baselines"]
    max_revenue = max(float(b["revenue_mean"]) for b in baselines.values())
    if iso_week not in baselines:
        raise ValueError(f"Week {iso_week} not in seasonality data — check docs/data/seasonality.json")
    current = float(baselines[iso_week]["revenue_mean"])
    return {
        "index": current / max_revenue,
        "label": idx["index"]["label"],
        "iso_week": int(iso_week),
    }


def load_benchmark():
    if not BENCHMARK_PATH.exists():
        return {
            "meta": {"schema_version": 1, "channel_baselines": CHANNEL_BASELINES},
            "snapshots": [],
        }
    with open(BENCHMARK_PATH) as f:
        return json.load(f)


def save_benchmark(data):
    BENCHMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BENCHMARK_PATH, "w") as f:
        json.dump(data, f, indent=2)


def build_snapshot(results, seasonality, baselines):
    snapshot = {
        "date": date.today().isoformat(),
        "iso_week": seasonality["iso_week"],
        "seasonality_index": round(seasonality["index"], 3),
        "season_label": seasonality["label"],
        "channels": {},
    }
    for r in results:
        channel = r["channel"]
        is_discovery = channel in DISCOVERY_CHANNELS
        if r.get("error"):
            snapshot["channels"][channel] = {"error": r["error"]}
            continue
        coverage = r.get("coverage") or {}
        quality = r.get("quality") or {}
        drift_data = r.get("drift") or {}
        channel_total = coverage.get("channel_total", 0)
        wc_total = coverage.get("wc_total", 0)
        incomplete_count = len((quality.get("incomplete") or []))
        drift_items = drift_data.get("drifted") or []
        drift_price = sum(1 for d in drift_items if d["field"] == "price")
        drift_stock = sum(1 for d in drift_items if d["field"] == "stock_status")
        baseline = baselines.get(channel, 0.5)
        cov_score = score_coverage(channel_total, wc_total, baseline, seasonality["index"])
        qual_score = score_quality(incomplete_count, channel_total)
        drift_score = score_drift(drift_price, drift_stock, channel_total, is_discovery)
        composite = compute_composite(cov_score, qual_score, drift_score)
        snapshot["channels"][channel] = {
            "coverage_score": cov_score,
            "quality_score": qual_score,
            "drift_score": drift_score,
            "composite": composite,
            "raw": {
                "channel_total": channel_total,
                "wc_total": wc_total,
                "incomplete_count": incomplete_count,
                "drift_price": drift_price,
                "drift_stock": drift_stock,
            },
        }
    return snapshot


def build_scorecard_section(snapshot, prior_snapshots):
    idx = snapshot["seasonality_index"]
    label = snapshot["season_label"]
    week = snapshot["iso_week"]
    lines = [
        f"\n## Feed Scorecard — Week {week} ({label}, index {idx:.2f})\n",
        "| Channel | Coverage | Quality | Drift | Trend |",
        "|---------|----------|---------|-------|-------|",
    ]
    for channel in CHANNEL_ORDER:
        ch = snapshot["channels"].get(channel)
        if ch is None:
            lines.append(f"| {channel} | — | — | — | STUB |")
            continue
        if "error" in ch:
            lines.append(f"| {channel} | — | — | — | ERROR |")
            continue
        cov = ch.get("coverage_score")
        qual = ch.get("quality_score")
        drift = ch.get("drift_score")
        composite = ch.get("composite")
        trend = compute_trend(channel, prior_snapshots, composite)
        cov_str = f"{cov} {rag(cov, COVERAGE_THRESHOLDS)}" if cov is not None else "—"
        qual_str = f"{qual} {rag(qual, QUALITY_THRESHOLDS)}" if qual is not None else "—"
        drift_str = f"{drift} {rag(drift, DRIFT_THRESHOLDS)}" if drift is not None else "—"
        lines.append(f"| {channel} | {cov_str} | {qual_str} | {drift_str} | {trend} |")
    if idx < 0.5:
        lines.append(f"\n_Off-season ({label}): coverage expectations relaxed. Quality held to full standard._")
    elif idx > 0.85:
        lines.append(f"\n_Peak season ({label}): tighten sync cadence. All dimensions at full standard._")
    return "\n".join(lines) + "\n"


def run_scoring(digest_path=None):
    with open(RESULTS_PATH) as f:
        results = json.load(f)
    seasonality = load_seasonality_index()
    benchmark = load_benchmark()
    baselines = benchmark.get("meta", {}).get("channel_baselines", CHANNEL_BASELINES)
    prior_snapshots = benchmark.get("snapshots", [])
    snapshot = build_snapshot(results, seasonality, baselines)
    scorecard = build_scorecard_section(snapshot, prior_snapshots)
    benchmark["snapshots"].append(snapshot)
    save_benchmark(benchmark)
    if digest_path and Path(digest_path).exists():
        with open(digest_path, "a") as f:
            f.write(scorecard)
        print(f"[SCORE] Scorecard appended to {digest_path}")
    print(f"[SCORE] Week {snapshot['iso_week']}, {snapshot['season_label']} (index {snapshot['seasonality_index']})")
    for channel in CHANNEL_ORDER:
        ch = snapshot["channels"].get(channel, {})
        if "error" in ch:
            print(f"  {channel}: ERROR — {str(ch['error'])[:60]}")
        elif ch:
            print(f"  {channel}: cov={ch.get('coverage_score')} qual={ch.get('quality_score')} drift={ch.get('drift_score')} composite={ch.get('composite')}")
    return snapshot


if __name__ == "__main__":
    import sys
    digest = sys.argv[1] if len(sys.argv) > 1 else None
    run_scoring(digest)
