# Feed Benchmark Scoring Infrastructure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a multi-dimensional, seasonality-normalized feed health scoring system that appends a Feed Scorecard section to the daily digest and persists weekly snapshots to `feeds/benchmark/benchmark.json`.

**Architecture:** `run_audit.py` emits structured `latest_results.json` alongside its markdown digest. A new `feeds/benchmark/score.py` reads that JSON + `docs/data/seasonality.json`, computes three scores per channel (Coverage, Quality, Drift), appends a snapshot to `benchmark.json`, and injects a scorecard table into the day's digest. One new GH Actions step wires it into the daily workflow.

**Tech Stack:** Python 3.11, pytest, existing `feeds/` package, `docs/data/seasonality.json` (read-only), `.github/workflows/feed-audit.yml`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `feeds/digest/run_audit.py` | Modify | Add `latest_results.json` output after markdown write |
| `feeds/benchmark/__init__.py` | Create | Package marker |
| `feeds/benchmark/score.py` | Create | Scoring logic + benchmark persistence + scorecard generation |
| `feeds/benchmark/benchmark.json` | Create | Initial seed with schema version + channel baselines |
| `feeds/tests/test_score.py` | Create | Unit tests for all scoring functions |
| `.github/workflows/feed-audit.yml` | Modify | Add `score` step + include `benchmark.json` in commit |

---

### Task 1: Emit `latest_results.json` from `run_audit.py`

`score.py` needs structured adapter results without re-running all 8 adapters. `run_audit.py` already holds them in memory — we just serialize them.

**Files:**
- Modify: `feeds/digest/run_audit.py`
- Test: `feeds/tests/test_run_audit_json.py`

- [ ] **Step 1: Write the failing test**

```python
# feeds/tests/test_run_audit_json.py
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from feeds.digest.run_audit import run_audit

def test_run_audit_writes_latest_results_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Minimal feed_master
    master = {"meta": {"product_count": 1, "generated_at": "2026-01-01"}, "products": {}}
    master_path = tmp_path / "feeds" / "feed_master.json"
    master_path.parent.mkdir(parents=True)
    master_path.write_text(json.dumps(master))

    digest_dir = tmp_path / "feeds" / "digest"
    digest_dir.mkdir()

    with patch("feeds.digest.run_audit.MASTER_PATH", master_path), \
         patch("feeds.digest.run_audit.DIGEST_DIR", digest_dir), \
         patch("feeds.digest.run_audit.WalmartAdapter") as wa, \
         patch("feeds.digest.run_audit.AmazonAdapter") as aa, \
         patch("feeds.digest.run_audit.GoogleMerchantAdapter") as ga, \
         patch("feeds.digest.run_audit.KlaviyoAdapter") as ka, \
         patch("feeds.digest.run_audit.ShopperApprovedAdapter") as sa, \
         patch("feeds.digest.run_audit.RedditAdapter") as ra, \
         patch("feeds.digest.run_audit.FacebookAdapter") as fa, \
         patch("feeds.digest.run_audit.PinterestAdapter") as pa:

        from feeds.adapters.base_adapter import AdapterResult, CoverageResult, DriftResult, QualityResult
        mock_result = AdapterResult(
            channel="walmart",
            coverage=CoverageResult(wc_total=10, channel_total=8, missing_skus=["A", "B"]),
            drift=DriftResult(drifted=[]),
            quality=QualityResult(incomplete=[]),
        )
        for adapter_cls in [wa, aa, ga, ka, sa, ra, fa, pa]:
            instance = MagicMock()
            instance.channel = "walmart"
            instance.run.return_value = mock_result
            adapter_cls.return_value = instance

        run_audit()

    results_path = digest_dir / "latest_results.json"
    assert results_path.exists(), "latest_results.json not written"
    data = json.loads(results_path.read_text())
    assert isinstance(data, list)
    assert data[0]["channel"] == "walmart"
    assert data[0]["coverage"]["wc_total"] == 10
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
python -m pytest feeds/tests/test_run_audit_json.py -v
```

Expected: FAIL — `latest_results.json` not written.

- [ ] **Step 3: Add JSON output to `run_audit.py`**

Add `import dataclasses` at the top, then after the existing `out_path` write block inside `run_audit()`:

```python
import dataclasses  # add to top of file

# Inside run_audit(), after the existing markdown write:
results_json_path = DIGEST_DIR / "latest_results.json"
with open(results_json_path, "w") as f:
    json.dump([dataclasses.asdict(r) for r in results], f, indent=2)
print(f"[DONE] Results JSON written to {results_json_path}")
```

Full updated `run_audit()` tail (after the existing `print(f"[DONE] Digest written...")`):

```python
    results_json_path = DIGEST_DIR / "latest_results.json"
    with open(results_json_path, "w") as f:
        json.dump([dataclasses.asdict(r) for r in results], f, indent=2)
    print(f"[DONE] Results JSON written to {results_json_path}")
    return results
```

Also add `import dataclasses` and `import json` (json is already imported via other means — verify it's at the top).

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest feeds/tests/test_run_audit_json.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add feeds/digest/run_audit.py feeds/tests/test_run_audit_json.py
git commit -m "feat(feeds): run_audit emits latest_results.json for score.py"
```

---

### Task 2: Create `feeds/benchmark/` package and seed `benchmark.json`

**Files:**
- Create: `feeds/benchmark/__init__.py`
- Create: `feeds/benchmark/benchmark.json`

- [ ] **Step 1: Create package init**

```bash
mkdir -p "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/feeds/benchmark"
touch "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/feeds/benchmark/__init__.py"
```

- [ ] **Step 2: Write the seed `benchmark.json`**

```json
{
  "meta": {
    "schema_version": 1,
    "channel_baselines": {
      "walmart": 0.42,
      "amazon": 0.90,
      "google_merchant": 0.67,
      "klaviyo": 0.95,
      "shopper_approved": 0.99,
      "reddit": 1.0,
      "facebook": 0.59,
      "pinterest": 1.0
    }
  },
  "snapshots": []
}
```

Save to `feeds/benchmark/benchmark.json`.

- [ ] **Step 3: Commit**

```bash
git add feeds/benchmark/__init__.py feeds/benchmark/benchmark.json
git commit -m "feat(feeds): seed benchmark package and initial benchmark.json"
```

---

### Task 3: Implement scoring functions in `score.py`

**Files:**
- Create: `feeds/benchmark/score.py`
- Create: `feeds/tests/test_score.py`

- [ ] **Step 1: Write failing tests for all scoring functions**

```python
# feeds/tests/test_score.py
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
    # 42% actual vs 90% baseline at index 1.0 → expected = 0.9 → score = 0.42/0.9*100 = 46
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest feeds/tests/test_score.py -v
```

Expected: FAIL — `feeds.benchmark.score` module not found.

- [ ] **Step 3: Implement `score.py` with all scoring functions**

Create `feeds/benchmark/score.py`:

```python
import json
from datetime import date
from pathlib import Path

RESULTS_PATH = Path("feeds/digest/latest_results.json")
SEASONALITY_PATH = Path("docs/data/seasonality.json")
BENCHMARK_PATH = Path("feeds/benchmark/benchmark.json")

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
    return max(0, round(100 - weighted))


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
            print(f"  {channel}: ERROR — {ch['error'][:60]}")
        elif ch:
            print(f"  {channel}: cov={ch.get('coverage_score')} qual={ch.get('quality_score')} drift={ch.get('drift_score')} composite={ch.get('composite')}")
    return snapshot


if __name__ == "__main__":
    import sys
    digest = sys.argv[1] if len(sys.argv) > 1 else None
    run_scoring(digest)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest feeds/tests/test_score.py -v
```

Expected: All tests PASS. Fix any off-by-one issues in `score_coverage` test assertions by running and reading actual vs expected.

- [ ] **Step 5: Commit**

```bash
git add feeds/benchmark/score.py feeds/tests/test_score.py
git commit -m "feat(feeds): score.py — coverage/quality/drift scoring with seasonality normalization"
```

---

### Task 4: Integration test — full snapshot from mock results

**Files:**
- Modify: `feeds/tests/test_score.py`

- [ ] **Step 1: Add integration test**

Append to `feeds/tests/test_score.py`:

```python
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
    assert walmart["coverage_score"] is not None
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
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest feeds/tests/test_score.py -v
```

Expected: All PASS (including new integration tests).

- [ ] **Step 3: Commit**

```bash
git add feeds/tests/test_score.py
git commit -m "test(feeds): integration tests for build_snapshot"
```

---

### Task 5: Wire `score.py` into GH Actions workflow

**Files:**
- Modify: `.github/workflows/feed-audit.yml`

- [ ] **Step 1: Read current workflow**

```bash
cat "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/.github/workflows/feed-audit.yml"
```

- [ ] **Step 2: Add score step and update commit step**

After the `Run channel audits` step and before `Commit feed master + digest`, add:

```yaml
      - name: Score feeds
        run: |
          DIGEST_DATE=$(date -u +%Y-%m-%d)
          python -m feeds.benchmark.score feeds/digest/${DIGEST_DATE}-feed-health.md
```

Update the `Commit feed master + digest` step to include `benchmark.json`:

```yaml
      - name: Commit feed master + digest + benchmark
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add feeds/feed_master.json feeds/digest/ feeds/benchmark/benchmark.json
          git diff --staged --quiet || git commit -m "chore(feeds): daily feed snapshot + audit + benchmark $(date -u +%Y-%m-%d)"
          git push
```

- [ ] **Step 3: Ensure `benchmark.json` is not gitignored**

```bash
grep "benchmark" "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/.gitignore"
```

If it matches a `*.json` rule, add an exception:

```bash
echo "!feeds/benchmark/benchmark.json" >> "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/.gitignore"
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/feed-audit.yml .gitignore
git commit -m "feat(feeds): add score step to feed-audit workflow"
```

---

### Task 6: Smoke test full pipeline locally

- [ ] **Step 1: Run the full pipeline from feed_master**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
python -m feeds.digest.run_audit
```

Expected output includes: `[DONE] Results JSON written to feeds/digest/latest_results.json`

- [ ] **Step 2: Confirm `latest_results.json` exists and is valid**

```bash
python -c "
import json
data = json.load(open('feeds/digest/latest_results.json'))
print(f'{len(data)} channel results')
for r in data:
    print(f'  {r[\"channel\"]}: error={bool(r.get(\"error\"))}')
"
```

- [ ] **Step 3: Run score.py against the live digest**

```bash
TODAY=$(date +%Y-%m-%d)
python -m feeds.benchmark.score "feeds/digest/${TODAY}-feed-health.md"
```

Expected: Score output per channel printed, scorecard appended to digest, `benchmark.json` updated.

- [ ] **Step 4: Verify scorecard in digest**

```bash
grep -A 20 "Feed Scorecard" "feeds/digest/$(date +%Y-%m-%d)-feed-health.md"
```

Expected: Markdown table with channel rows, RAG emoji, trend arrows.

- [ ] **Step 5: Verify benchmark.json has one snapshot**

```bash
python -c "
import json
b = json.load(open('feeds/benchmark/benchmark.json'))
print(f'{len(b[\"snapshots\"])} snapshots')
print(json.dumps(b['snapshots'][-1], indent=2)[:500])
"
```

- [ ] **Step 6: Run full test suite**

```bash
python -m pytest feeds/tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit and push**

```bash
git add feeds/benchmark/benchmark.json feeds/digest/
git commit -m "chore(feeds): first scored benchmark snapshot"
git push
```

---

## Post-Implementation Verification

After the next GH Actions run (tomorrow 7:05 AM UTC):

1. Check that `feeds/benchmark/benchmark.json` in the commit has 2 snapshots
2. Check that the digest `.md` file ends with `## Feed Scorecard`
3. Check that no adapter errors caused `score.py` to crash (it must be error-tolerant)
