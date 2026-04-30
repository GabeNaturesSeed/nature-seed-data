# Seasonality Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 0–2 dual-track seasonality index (Demand + Performance) powered by historical Google Ads and WooCommerce data, surfaced on a new Operations page and as a 6th KPI card on the DTC MTD dashboard.

**Architecture:** A new Python script (`generate_seasonality.py`) pulls full API history once to compute per-week baselines, then runs nightly to update current-week index values and writes `docs/data/seasonality.json`. The Next.js dashboard reads this file to render a dedicated Seasonality page at `/inventory/seasonality` and a compact index card on `/reporting`.

**Tech Stack:** Python 3.11, `google-ads`, `requests`, Next.js 15, TypeScript, Recharts, HeroUI, Tailwind CSS 4

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `infrastructure/dashboard/generate_seasonality.py` | Create | Full pipeline: API pulls, baseline math, JSON output |
| `infrastructure/dashboard/tests/test_seasonality_math.py` | Create | Pytest unit tests for pure math functions |
| `.github/workflows/dashboard_update.yml` | Modify | Add `seasonality-data` parallel job + download in commit step |
| `docs/data/seasonality.json` | Generated | Output data file |
| `dashboard/src/lib/types.ts` | Modify | Add `SeasonalityData` interface |
| `dashboard/src/components/kpi/KpiGrid.tsx` | Modify | Add `columns={6}` support |
| `dashboard/src/components/seasonality/SeasonalityIndexCard.tsx` | Create | Reusable index card (compact + full modes) |
| `dashboard/src/app/reporting/page.tsx` | Modify | Add SeasonalityIndexCard as 6th KPI |
| `dashboard/src/app/inventory/seasonality/page.tsx` | Create | Full Seasonality page |
| `dashboard/src/components/layout/Sidebar.tsx` | Modify | Add Seasonality nav item under Operations |

---

## Task 1: Python — Core Math Functions + Tests (TDD)

**Files:**
- Create: `infrastructure/dashboard/tests/__init__.py`
- Create: `infrastructure/dashboard/tests/test_seasonality_math.py`
- Create: `infrastructure/dashboard/generate_seasonality.py` (math functions only, stubs for the rest)

### Step 1.1 — Write failing tests

Create `infrastructure/dashboard/tests/__init__.py` (empty file), then create `infrastructure/dashboard/tests/test_seasonality_math.py`:

```python
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
```

- [ ] **Step 1.2 — Run tests to confirm they all fail**

```bash
cd "infrastructure/dashboard"
python -m pytest tests/test_seasonality_math.py -v 2>&1 | head -30
```

Expected: `ImportError` or `ModuleNotFoundError` (generate_seasonality doesn't exist yet).

- [ ] **Step 1.3 — Create `generate_seasonality.py` with math functions only**

Create `infrastructure/dashboard/generate_seasonality.py`:

```python
#!/usr/bin/env python3
"""
Nature's Seed — Seasonality Index Generator
Computes a 0–2 dual-track (Demand + Performance) seasonality index
from historical WooCommerce and Google Ads data. Runs nightly via
GitHub Actions. First run computes weekly baselines from full history;
subsequent runs update only the current week.

Output: docs/data/seasonality.json
"""

import json
import time
import base64
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import requests

try:
    from google.ads.googleads.client import GoogleAdsClient
    HAS_GOOGLE_ADS = True
except ImportError:
    HAS_GOOGLE_ADS = False

# ── Paths ───────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.parent
OUT_DIR = ROOT / "docs" / "data"
ENV_FILE = ROOT / ".env"

# ── Env ─────────────────────────────────────────────────────
def _load_env() -> dict:
    env = {}
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env_vars = _load_env()

WC_BASE = env_vars.get("WC_BASE_URL", "")
WC_CK = env_vars.get("WC_CK", "")
WC_CS = env_vars.get("WC_CS", "")
CF_WORKER_URL = env_vars.get("CF_WORKER_URL", "")
CF_WORKER_SECRET = env_vars.get("CF_WORKER_SECRET", "")
GADS_DEVELOPER_TOKEN = env_vars.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
GADS_CLIENT_ID = env_vars.get("GOOGLE_ADS_CLIENT_ID", "")
GADS_CLIENT_SECRET = env_vars.get("GOOGLE_ADS_CLIENT_SECRET", "")
GADS_REFRESH_TOKEN = env_vars.get("GOOGLE_ADS_REFRESH_TOKEN", "")
GADS_LOGIN_CID = env_vars.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
GADS_CUSTOMER_ID = env_vars.get("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")

TODAY = date.today()
TODAY_STR = TODAY.isoformat()
YESTERDAY = TODAY - timedelta(days=1)
YEARS_BACK = 4


# ════════════════════════════════════════════════════════════
# PURE MATH FUNCTIONS (tested in tests/test_seasonality_math.py)
# ════════════════════════════════════════════════════════════

def iso_week(date_str: str) -> int:
    """Return ISO week number (1–52) for a YYYY-MM-DD string."""
    return date.fromisoformat(date_str).isocalendar()[1]


def normalize(value: float, mean: float):
    """Normalize value against its mean. Caps at 2.0. Returns None if mean is zero."""
    if not mean:
        return None
    return min(round(value / mean, 4), 2.0)


def invert_normalize(value: float, mean: float):
    """Normalize an inverted signal (lower is better, e.g. IS Budget Lost).
    Maps: (1 - value) / (1 - mean) so lower-than-average → score > 1.
    """
    return normalize(1.0 - value, 1.0 - mean)


def compute_demand_index(norm_revenue, norm_orders):
    """Mean of available normalized demand signals."""
    vals = [v for v in [norm_revenue, norm_orders] if v is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 4)


def compute_performance_index(norm_mer, norm_is_rank, norm_is_budget_inv):
    """Mean of available normalized performance signals."""
    vals = [v for v in [norm_mer, norm_is_rank, norm_is_budget_inv] if v is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 4)


def compute_seasonality_index(demand, performance):
    """Mean of demand + performance indexes, clamped to [0, 2]."""
    vals = [v for v in [demand, performance] if v is not None]
    if not vals:
        return None
    return round(max(0.0, min(2.0, sum(vals) / len(vals))), 4)


def label_for_index(score) -> str:
    if score is None:
        return "Insufficient Data"
    if score < 0.5:
        return "Deep Off-Season"
    if score < 0.8:
        return "Slow Period"
    if score < 1.2:
        return "Average"
    if score < 1.6:
        return "Approaching Peak"
    return "Peak Season"


def compute_index_for_week(week_num: int, wc_week: dict, gads_week: dict, baselines: dict) -> dict:
    """Compute Demand, Performance, and Seasonality indexes for one week."""
    baseline = baselines.get(str(week_num))
    if not baseline:
        return {"seasonality": None, "demand": None, "performance": None, "label": "Insufficient Data"}

    revenue = wc_week.get("revenue", 0.0)
    orders = float(wc_week.get("orders", 0))
    cost = gads_week.get("cost", 0.0)
    is_rank = gads_week.get("is_rank")
    is_budget_lost = gads_week.get("is_budget_lost")

    mer = revenue / cost if cost > 0 else 0.0

    norm_rev = normalize(revenue, baseline.get("revenue_mean", 0))
    norm_ord = normalize(orders, baseline.get("orders_mean", 0))
    norm_mer = normalize(mer, baseline.get("mer_mean", 0))
    norm_is_rank = normalize(is_rank, baseline["is_rank_mean"]) if is_rank and baseline.get("is_rank_mean") else None
    norm_is_budget_inv = (
        invert_normalize(is_budget_lost, baseline["is_budget_lost_mean"])
        if is_budget_lost is not None and baseline.get("is_budget_lost_mean")
        else None
    )

    demand = compute_demand_index(norm_rev, norm_ord)
    performance = compute_performance_index(norm_mer, norm_is_rank, norm_is_budget_inv)
    seasonality = compute_seasonality_index(demand, performance)

    return {
        "seasonality": seasonality,
        "demand": demand,
        "performance": performance,
        "label": label_for_index(seasonality),
    }
```

- [ ] **Step 1.4 — Run tests, confirm they pass**

```bash
cd "infrastructure/dashboard"
python -m pytest tests/test_seasonality_math.py -v
```

Expected output: all 24 tests PASSED.

- [ ] **Step 1.5 — Commit**

```bash
git add "infrastructure/dashboard/generate_seasonality.py" \
        "infrastructure/dashboard/tests/__init__.py" \
        "infrastructure/dashboard/tests/test_seasonality_math.py"
git commit -m "feat: add seasonality index math functions + tests"
```

---

## Task 2: Python — WooCommerce + Google Ads Historical Pulls

**Files:**
- Modify: `infrastructure/dashboard/generate_seasonality.py` (add API pull functions)

- [ ] **Step 2.1 — Add WC pull functions to generate_seasonality.py**

Append after the math functions section (after `compute_index_for_week`):

```python
# ════════════════════════════════════════════════════════════
# API PULL FUNCTIONS
# ════════════════════════════════════════════════════════════

def _wc_get(path: str, params: dict = None):
    """GET from WooCommerce REST API via CF Worker proxy if configured."""
    if CF_WORKER_URL:
        p = {"wc_path": path, **(params or {})}
        auth_str = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        headers = {
            "X-Proxy-Secret": CF_WORKER_SECRET,
            "Authorization": f"Basic {auth_str}",
        }
        resp = requests.get(CF_WORKER_URL, headers=headers, params=p, timeout=30)
    else:
        resp = requests.get(f"{WC_BASE}{path}", auth=(WC_CK, WC_CS), params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp


def _pull_wc_quarter(start: date, end: date) -> dict:
    """Pull WC orders for one date range. Returns {date_str: {revenue, orders}}."""
    daily: dict = defaultdict(lambda: {"revenue": 0.0, "orders": 0})
    page = 1
    while True:
        params = {
            "after": f"{start}T00:00:00",
            "before": f"{end}T23:59:59",
            "status": "completed,processing",
            "per_page": 100,
            "page": page,
        }
        try:
            orders = _wc_get("/orders", params).json()
        except Exception as e:
            print(f"    [WARN] WC page {page} failed: {e}")
            break
        if not orders:
            break
        for order in orders:
            d = order.get("date_created", "")[:10]
            if d:
                daily[d]["revenue"] += float(order.get("total", 0))
                daily[d]["orders"] += 1
        page += 1
        time.sleep(0.3)
    return dict(daily)


def pull_wc_history() -> dict:
    """Pull all WC order history chunked by quarter.
    Returns {date_str: {revenue: float, orders: int}}.
    """
    print("  Pulling WooCommerce history...")
    combined: dict = {}
    history_start = date(TODAY.year - YEARS_BACK, 1, 1)

    chunk = history_start
    while chunk <= YESTERDAY:
        # Advance to end of current quarter
        q_month_end = {1: 3, 2: 3, 3: 3, 4: 6, 5: 6, 6: 6, 7: 9, 8: 9, 9: 9, 10: 12, 11: 12, 12: 12}
        end_month = q_month_end[chunk.month]
        end_day = {3: 31, 6: 30, 9: 30, 12: 31}[end_month]
        chunk_end = min(date(chunk.year, end_month, end_day), YESTERDAY)

        print(f"    WC: {chunk} → {chunk_end}")
        combined.update(_pull_wc_quarter(chunk, chunk_end))

        # Advance to next quarter
        if end_month == 12:
            chunk = date(chunk.year + 1, 1, 1)
        else:
            chunk = date(chunk.year, end_month + 1, 1)

    print(f"    WC: {len(combined)} days pulled")
    return combined


def pull_gads_history() -> dict:
    """Pull Google Ads daily metrics (cost, IS rank, IS budget lost) for all history.
    Returns {date_str: {cost: float, is_rank: float|None, is_budget_lost: float|None}}.
    """
    print("  Pulling Google Ads history...")
    if not HAS_GOOGLE_ADS:
        print("    [WARN] google-ads package not installed")
        return {}
    if not all([GADS_DEVELOPER_TOKEN, GADS_CLIENT_ID, GADS_CLIENT_SECRET, GADS_REFRESH_TOKEN, GADS_CUSTOMER_ID]):
        print("    [WARN] Google Ads credentials not configured")
        return {}

    client = GoogleAdsClient.load_from_dict({
        "developer_token": GADS_DEVELOPER_TOKEN,
        "client_id": GADS_CLIENT_ID,
        "client_secret": GADS_CLIENT_SECRET,
        "refresh_token": GADS_REFRESH_TOKEN,
        "login_customer_id": GADS_LOGIN_CID,
        "use_proto_plus": True,
    })

    start_str = date(TODAY.year - YEARS_BACK, 1, 1).isoformat()
    end_str = YESTERDAY.isoformat()

    query = f"""
        SELECT
            segments.date,
            metrics.cost_micros,
            metrics.search_impression_share,
            metrics.search_budget_lost_impression_share
        FROM campaign
        WHERE
            segments.date >= '{start_str}'
            AND segments.date <= '{end_str}'
        ORDER BY segments.date ASC
    """

    service = client.get_service("GoogleAdsService")
    stream = service.search_stream(customer_id=GADS_CUSTOMER_ID, query=query)

    # Aggregate across all campaigns by date
    raw: dict = defaultdict(lambda: {
        "cost": 0.0, "is_rank_vals": [], "is_budget_vals": []
    })
    for batch in stream:
        for row in batch.results:
            d = row.segments.date
            raw[d]["cost"] += row.metrics.cost_micros / 1_000_000
            # IS metrics return 0.0 when data is unavailable ("--")
            if row.metrics.search_impression_share > 0:
                raw[d]["is_rank_vals"].append(row.metrics.search_impression_share)
            if row.metrics.search_budget_lost_impression_share > 0:
                raw[d]["is_budget_vals"].append(
                    row.metrics.search_budget_lost_impression_share
                )

    result: dict = {}
    for d, v in raw.items():
        result[d] = {
            "cost": round(v["cost"], 2),
            "is_rank": round(sum(v["is_rank_vals"]) / len(v["is_rank_vals"]), 4)
                       if v["is_rank_vals"] else None,
            "is_budget_lost": round(sum(v["is_budget_vals"]) / len(v["is_budget_vals"]), 4)
                              if v["is_budget_vals"] else None,
        }

    print(f"    Google Ads: {len(result)} days pulled")
    return result
```

- [ ] **Step 2.2 — Run existing tests to confirm nothing broke**

```bash
cd "infrastructure/dashboard"
python -m pytest tests/test_seasonality_math.py -v
```

Expected: all 24 tests still PASSED.

- [ ] **Step 2.3 — Commit**

```bash
git add "infrastructure/dashboard/generate_seasonality.py"
git commit -m "feat: add WooCommerce and Google Ads historical pull functions"
```

---

## Task 3: Python — Baseline Computation + Full Pipeline

**Files:**
- Modify: `infrastructure/dashboard/generate_seasonality.py` (add baseline + main pipeline)

- [ ] **Step 3.1 — Add baseline computation function**

Append to `generate_seasonality.py`:

```python
# ════════════════════════════════════════════════════════════
# BASELINE COMPUTATION
# ════════════════════════════════════════════════════════════

def compute_weekly_baselines(wc_daily: dict, gads_daily: dict) -> dict:
    """
    Group all historical data by ISO week number and compute multi-year means.
    Requires at least 2 years of data for a week to be included.
    Returns {str(1..52): {revenue_mean, orders_mean, ad_spend_mean, mer_mean,
                           is_rank_mean, is_budget_lost_mean}}.
    """
    # week_num → year → aggregated values for that (year, week) pair
    week_years: dict = defaultdict(lambda: defaultdict(lambda: {
        "revenue": 0.0, "orders": 0, "cost": 0.0,
        "is_ranks": [], "is_budgets": [],
    }))

    for date_str, v in wc_daily.items():
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            continue
        week = d.isocalendar()[1]
        year = d.year
        week_years[week][year]["revenue"] += v.get("revenue", 0.0)
        week_years[week][year]["orders"] += v.get("orders", 0)

    for date_str, v in gads_daily.items():
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            continue
        week = d.isocalendar()[1]
        year = d.year
        week_years[week][year]["cost"] += v.get("cost", 0.0)
        if v.get("is_rank") is not None:
            week_years[week][year]["is_ranks"].append(v["is_rank"])
        if v.get("is_budget_lost") is not None:
            week_years[week][year]["is_budgets"].append(v["is_budget_lost"])

    baselines: dict = {}
    for week_num in range(1, 53):
        years_data = week_years.get(week_num, {})
        if len(years_data) < 2:
            continue  # need at least 2 years to establish a baseline

        revenues = [y["revenue"] for y in years_data.values() if y["revenue"] > 0]
        orders_vals = [float(y["orders"]) for y in years_data.values() if y["orders"] > 0]
        costs = [y["cost"] for y in years_data.values() if y["cost"] > 0]
        all_is_ranks = [v for y in years_data.values() for v in y["is_ranks"]]
        all_is_budgets = [v for y in years_data.values() for v in y["is_budgets"]]

        if not revenues:
            continue

        rev_mean = sum(revenues) / len(revenues)
        ord_mean = sum(orders_vals) / len(orders_vals) if orders_vals else 0.0
        cost_mean = sum(costs) / len(costs) if costs else 0.0
        # MER: compute per-year then average
        mer_vals = []
        for y in years_data.values():
            if y["revenue"] > 0 and y["cost"] > 0:
                mer_vals.append(y["revenue"] / y["cost"])
        mer_mean = sum(mer_vals) / len(mer_vals) if mer_vals else 0.0

        baselines[str(week_num)] = {
            "revenue_mean": round(rev_mean, 2),
            "orders_mean": round(ord_mean, 2),
            "ad_spend_mean": round(cost_mean, 2),
            "mer_mean": round(mer_mean, 4),
            "is_rank_mean": round(sum(all_is_ranks) / len(all_is_ranks), 4) if all_is_ranks else None,
            "is_budget_lost_mean": round(sum(all_is_budgets) / len(all_is_budgets), 4) if all_is_budgets else None,
        }

    return baselines
```

- [ ] **Step 3.2 — Add `build_weekly_history` and `main` to generate_seasonality.py**

Append to `generate_seasonality.py`:

```python
def _aggregate_wc_by_week(wc_daily: dict, year: int) -> dict:
    """Aggregate WC daily data for a specific year into {week_num: {revenue, orders}}."""
    weeks: dict = defaultdict(lambda: {"revenue": 0.0, "orders": 0})
    for date_str, v in wc_daily.items():
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            continue
        if d.year == year:
            w = d.isocalendar()[1]
            weeks[w]["revenue"] += v.get("revenue", 0.0)
            weeks[w]["orders"] += v.get("orders", 0)
    return dict(weeks)


def _aggregate_gads_by_week(gads_daily: dict, year: int) -> dict:
    """Aggregate Google Ads daily data for a specific year into {week_num: {cost, is_rank, is_budget_lost}}."""
    weeks: dict = defaultdict(lambda: {"cost": 0.0, "is_ranks": [], "is_budgets": []})
    for date_str, v in gads_daily.items():
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            continue
        if d.year == year:
            w = d.isocalendar()[1]
            weeks[w]["cost"] += v.get("cost", 0.0)
            if v.get("is_rank") is not None:
                weeks[w]["is_ranks"].append(v["is_rank"])
            if v.get("is_budget_lost") is not None:
                weeks[w]["is_budgets"].append(v["is_budget_lost"])

    result: dict = {}
    for w, v in weeks.items():
        result[w] = {
            "cost": round(v["cost"], 2),
            "is_rank": round(sum(v["is_ranks"]) / len(v["is_ranks"]), 4) if v["is_ranks"] else None,
            "is_budget_lost": round(sum(v["is_budgets"]) / len(v["is_budgets"]), 4) if v["is_budgets"] else None,
        }
    return result


def build_weekly_history(wc_daily: dict, gads_daily: dict, baselines: dict) -> list:
    """Build 52-entry weekly history array for the current year + historical averages.
    Returns list of {week, seasonality_avg, demand_avg, performance_avg, current_year}.
    """
    cy_wc = _aggregate_wc_by_week(wc_daily, TODAY.year)
    cy_gads = _aggregate_gads_by_week(gads_daily, TODAY.year)
    current_iso_week = TODAY.isocalendar()[1]

    history = []
    for week_num in range(1, 53):
        baseline = baselines.get(str(week_num))
        # Historical average indexes (computed from baseline means = index of 1.0 by definition,
        # but we store null to signal "no data" vs "exactly average")
        avg_entry: dict = {"week": week_num, "seasonality_avg": 1.0, "demand_avg": 1.0, "performance_avg": 1.0}
        if not baseline:
            avg_entry = {"week": week_num, "seasonality_avg": None, "demand_avg": None, "performance_avg": None}

        # Current year actual (only for weeks already past)
        current_year_val = None
        if week_num < current_iso_week and baseline:
            wc_w = cy_wc.get(week_num, {})
            gads_w = cy_gads.get(week_num, {})
            idx = compute_index_for_week(week_num, wc_w, gads_w, baselines)
            current_year_val = idx["seasonality"]

        history.append({**avg_entry, "current_year": current_year_val})

    return history


def _write_json(filename: str, data: dict) -> None:
    path = OUT_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  [OK] Wrote {path.name}")


def _get_current_week_data(wc_daily: dict, gads_daily: dict) -> tuple[dict, dict]:
    """Aggregate WC and Ads data for the current ISO week."""
    current_week = TODAY.isocalendar()[1]
    wc_weeks = _aggregate_wc_by_week(wc_daily, TODAY.year)
    gads_weeks = _aggregate_gads_by_week(gads_daily, TODAY.year)
    return wc_weeks.get(current_week, {}), gads_weeks.get(current_week, {})


def main() -> None:
    print("=== Seasonality Index Generator ===")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = OUT_DIR / "seasonality.json"

    # ── Step 1: Load or compute baselines ───────────────────
    existing: dict = {}
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
        except json.JSONDecodeError:
            pass

    baselines = existing.get("weekly_baselines")

    if baselines:
        print("  Baselines found — skipping full historical pull")
        # Only pull current week (last 7 days) for nightly update
        current_week = TODAY.isocalendar()[1]
        week_start = TODAY - timedelta(days=TODAY.weekday())
        wc_daily = _pull_wc_quarter(week_start, YESTERDAY)
        gads_daily = {}  # Google Ads doesn't need re-pull for current week math
        # Re-pull full current year for gads to have IS rank for the chart
        # Only Google Ads current week data is needed
        gads_daily_full = pull_gads_history()
        wc_daily_full = existing.get("_raw_wc_weekly", {})
    else:
        print("  No baselines found — running full historical pull")
        wc_daily_full_raw = pull_wc_history()
        gads_daily_full = pull_gads_history()
        baselines = compute_weekly_baselines(wc_daily_full_raw, gads_daily_full)
        wc_daily_full = wc_daily_full_raw
        print(f"  Baselines computed for {len(baselines)} weeks")

    # ── Step 2: Current week index ───────────────────────────
    current_week_num = TODAY.isocalendar()[1]

    if baselines:
        wc_cw, gads_cw = _get_current_week_data(wc_daily_full, gads_daily_full)
        indexes = compute_index_for_week(current_week_num, wc_cw, gads_cw, baselines)
    else:
        indexes = {"seasonality": None, "demand": None, "performance": None, "label": "Insufficient Data"}

    baseline_cw = baselines.get(str(current_week_num), {}) if baselines else {}
    revenue_cw = wc_daily_full_raw.get(TODAY_STR, {}).get("revenue") if not existing.get("weekly_baselines") else None

    # Aggregate current week totals from WC for signals display
    wc_cw_agg = _aggregate_wc_by_week(wc_daily_full, TODAY.year).get(current_week_num, {}) if not existing.get("weekly_baselines") else {}
    gads_cw_agg = _aggregate_gads_by_week(gads_daily_full, TODAY.year).get(current_week_num, {})

    # ── Step 3: Build 52-week chart history ──────────────────
    wc_for_history = wc_daily_full if not existing.get("weekly_baselines") else {}
    weekly_history = build_weekly_history(wc_for_history, gads_daily_full, baselines or {})

    # ── Step 4: Write output ─────────────────────────────────
    mer_cw = (wc_cw_agg.get("revenue", 0) / gads_cw_agg["cost"]
              if gads_cw_agg.get("cost", 0) > 0 else None)

    output: dict = {
        "generated_at": TODAY_STR,
        "current_week": current_week_num,
        "index": {
            "seasonality": indexes["seasonality"],
            "demand": indexes["demand"],
            "performance": indexes["performance"],
            "label": indexes["label"],
        },
        "current_week_signals": {
            "wc_revenue": round(wc_cw_agg.get("revenue", 0), 2),
            "wc_revenue_avg": baseline_cw.get("revenue_mean"),
            "orders": wc_cw_agg.get("orders", 0),
            "orders_avg": baseline_cw.get("orders_mean"),
            "blended_mer": round(mer_cw, 4) if mer_cw else None,
            "blended_mer_avg": baseline_cw.get("mer_mean"),
            "is_rank": gads_cw_agg.get("is_rank"),
            "is_rank_avg": baseline_cw.get("is_rank_mean"),
            "is_budget_lost": gads_cw_agg.get("is_budget_lost"),
            "is_budget_lost_avg": baseline_cw.get("is_budget_lost_mean"),
            "ad_spend": gads_cw_agg.get("cost", 0),
            "ad_spend_avg": baseline_cw.get("ad_spend_mean"),
        },
        "weekly_baselines": baselines or {},
        "weekly_history": weekly_history,
    }

    _write_json("seasonality.json", output)
    print(f"  Seasonality Index: {indexes['seasonality']} ({indexes['label']})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3.3 — Run tests to confirm still passing**

```bash
cd "infrastructure/dashboard"
python -m pytest tests/test_seasonality_math.py -v
```

Expected: all 24 tests PASSED.

- [ ] **Step 3.4 — Smoke test the script locally (dry-run with no creds)**

```bash
cd "infrastructure/dashboard"
python generate_seasonality.py 2>&1 | head -20
```

Expected: warnings about missing credentials, then exit cleanly. No tracebacks.

- [ ] **Step 3.5 — Commit**

```bash
git add "infrastructure/dashboard/generate_seasonality.py"
git commit -m "feat: add seasonality baseline computation and pipeline main()"
```

---

## Task 4: GitHub Actions — Add Seasonality Job

**Files:**
- Modify: `.github/workflows/dashboard_update.yml`

- [ ] **Step 4.1 — Add parallel `seasonality-data` job**

In `.github/workflows/dashboard_update.yml`, add this job in the `# PARALLEL JOBS` section, after the `abc-report` job and before `commit-and-push`:

```yaml
  seasonality-data:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install requests google-ads google-auth
      - name: Create .env
        run: echo "$ENV_CONTENT" > .env
      - name: Generate seasonality index
        run: python infrastructure/dashboard/generate_seasonality.py
      - uses: actions/upload-artifact@v5
        with:
          name: seasonality-data
          path: docs/data/seasonality.json
          retention-days: 1
```

- [ ] **Step 4.2 — Add seasonality to `needs` in commit-and-push job**

Change the `needs` line in `commit-and-push`:

```yaml
    needs: [abc-analysis, dashboard-data, customer-data, review-feed, algolia-enrich, abc-report, seasonality-data]
```

- [ ] **Step 4.3 — Add download step in commit-and-push job**

Add after the `Download ABC report` step:

```yaml
      - name: Download seasonality data
        uses: actions/download-artifact@v5
        with:
          name: seasonality-data
          path: docs/data/
        continue-on-error: true
```

- [ ] **Step 4.4 — Commit**

```bash
git add ".github/workflows/dashboard_update.yml"
git commit -m "feat: add seasonality-data job to dashboard_update workflow"
```

---

## Task 5: TypeScript Types + KpiGrid 6-column Support

**Files:**
- Modify: `dashboard/src/lib/types.ts`
- Modify: `dashboard/src/components/kpi/KpiGrid.tsx`

- [ ] **Step 5.1 — Add SeasonalityData types to types.ts**

Open `dashboard/src/lib/types.ts` and append at the end of the file:

```typescript
// ── Seasonality ──
export interface SeasonalityIndex {
  seasonality: number | null;
  demand: number | null;
  performance: number | null;
  label: string;
}

export interface SeasonalityWeekSignals {
  wc_revenue: number;
  wc_revenue_avg: number | null;
  orders: number;
  orders_avg: number | null;
  blended_mer: number | null;
  blended_mer_avg: number | null;
  is_rank: number | null;
  is_rank_avg: number | null;
  is_budget_lost: number | null;
  is_budget_lost_avg: number | null;
  ad_spend: number;
  ad_spend_avg: number | null;
}

export interface SeasonalityWeekHistory {
  week: number;
  seasonality_avg: number | null;
  demand_avg: number | null;
  performance_avg: number | null;
  current_year: number | null;
}

export interface SeasonalityData {
  generated_at: string;
  current_week: number;
  index: SeasonalityIndex;
  current_week_signals: SeasonalityWeekSignals;
  weekly_baselines: Record<string, unknown>;
  weekly_history: SeasonalityWeekHistory[];
}
```

- [ ] **Step 5.2 — Add columns={6} support to KpiGrid.tsx**

Open `dashboard/src/components/kpi/KpiGrid.tsx`. Replace the `colClass` assignment:

```typescript
  const colClass = columns === 3
    ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'
    : columns === 5
    ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-5'
    : columns === 6
    ? 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-6'
    : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4';
```

- [ ] **Step 5.3 — Commit**

```bash
git add "dashboard/src/lib/types.ts" "dashboard/src/components/kpi/KpiGrid.tsx"
git commit -m "feat: add SeasonalityData types and KpiGrid 6-column support"
```

---

## Task 6: SeasonalityIndexCard Component

**Files:**
- Create: `dashboard/src/components/seasonality/SeasonalityIndexCard.tsx`

- [ ] **Step 6.1 — Create component**

Create `dashboard/src/components/seasonality/SeasonalityIndexCard.tsx`:

```typescript
'use client';

import Link from 'next/link';
import type { SeasonalityIndex } from '@/lib/types';

interface SeasonalityIndexCardProps {
  index: SeasonalityIndex;
  compact?: boolean;
}

function indexColor(score: number | null): string {
  if (score === null) return 'text-brand-neutral/50';
  if (score < 0.5) return 'text-red-500';
  if (score < 1.0) return 'text-yellow-500';
  if (score < 1.6) return 'text-orange-400';
  return 'text-green-500';
}

function barColor(score: number | null): string {
  if (score === null) return 'bg-brand-neutral/20';
  if (score < 0.5) return 'bg-red-500';
  if (score < 1.0) return 'bg-yellow-500';
  if (score < 1.6) return 'bg-orange-400';
  return 'bg-green-500';
}

export default function SeasonalityIndexCard({ index, compact = false }: SeasonalityIndexCardProps) {
  const fillPct = index.seasonality !== null ? Math.round((index.seasonality / 2) * 100) : 0;
  const color = indexColor(index.seasonality);
  const bar = barColor(index.seasonality);
  const scoreStr = index.seasonality !== null ? index.seasonality.toFixed(2) : '—';

  if (compact) {
    return (
      <Link href="/inventory/seasonality" className="block">
        <div className="bg-surface-lowest rounded-xl shadow-ambient p-4 md:p-5 hover:bg-surface-low transition-colors cursor-pointer">
          <p className="text-[10px] md:text-xs uppercase tracking-wider text-brand-neutral/50 mb-1.5 md:mb-2">
            Season Index
          </p>
          <p className={`text-2xl md:text-3xl font-semibold mb-2 md:mb-2.5 leading-none ${color}`}>
            {scoreStr}
          </p>
          <p className={`text-xs mb-2 ${color}`}>{index.label}</p>
          <div className="h-1.5 w-full bg-brand-neutral/10 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${bar}`}
              style={{ width: `${fillPct}%` }}
            />
          </div>
        </div>
      </Link>
    );
  }

  // Full mode — used on the Seasonality page header
  return (
    <div className="bg-surface-lowest rounded-xl shadow-ambient p-4 md:p-5">
      <p className="text-[10px] md:text-xs uppercase tracking-wider text-brand-neutral/50 mb-1.5 md:mb-2">
        Seasonality Index
      </p>
      <p className={`text-3xl md:text-4xl font-semibold mb-1 leading-none ${color}`}>
        {scoreStr}
      </p>
      <p className={`text-sm mb-3 ${color}`}>{index.label}</p>
      <div className="h-2 w-full bg-brand-neutral/10 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${bar}`}
          style={{ width: `${fillPct}%` }}
        />
      </div>
      <div className="mt-3 flex justify-between text-[10px] text-brand-neutral/40">
        <span>0 — Off-Season</span>
        <span>1 — Average</span>
        <span>2 — Peak</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 6.2 — Commit**

```bash
git add "dashboard/src/components/seasonality/SeasonalityIndexCard.tsx"
git commit -m "feat: add SeasonalityIndexCard component (compact + full modes)"
```

---

## Task 7: DTC MTD — Add Seasonality Widget

**Files:**
- Modify: `dashboard/src/app/reporting/page.tsx`

- [ ] **Step 7.1 — Add import to reporting/page.tsx**

At the top of `dashboard/src/app/reporting/page.tsx`, add after the existing imports:

```typescript
import { useJsonData } from '@/hooks/useJsonData';
import { SeasonalityData } from '@/lib/types';
import SeasonalityIndexCard from '@/components/seasonality/SeasonalityIndexCard';
```

Note: `useJsonData` is already imported — only add the two new lines (`SeasonalityData` and `SeasonalityIndexCard`).

- [ ] **Step 7.2 — Add seasonality data hook inside ReportingMtdPage**

Inside `ReportingMtdPage`, after the existing `const { data, loading } = useJsonData<ReportingData>('reporting');` line, add:

```typescript
  const { data: seasonalityData } = useJsonData<SeasonalityData>('seasonality');
```

- [ ] **Step 7.3 — Change KpiGrid to 6 columns**

In `reporting/page.tsx`, change:

```typescript
      <KpiGrid columns={5}>
```

to:

```typescript
      <KpiGrid columns={6}>
```

- [ ] **Step 7.4 — Add SeasonalityIndexCard as 6th KPI**

Inside the `<KpiGrid columns={6}>` block, add after the existing `<KpiCard label="AOV" ... />`:

```typescript
        {seasonalityData ? (
          <SeasonalityIndexCard index={seasonalityData.index} compact />
        ) : (
          <KpiCard label="Season Index" value="—" />
        )}
```

- [ ] **Step 7.5 — Commit**

```bash
git add "dashboard/src/app/reporting/page.tsx"
git commit -m "feat: add seasonality index widget to DTC MTD page"
```

---

## Task 8: Seasonality Page

**Files:**
- Create: `dashboard/src/app/inventory/seasonality/page.tsx`

- [ ] **Step 8.1 — Create the page**

Create `dashboard/src/app/inventory/seasonality/page.tsx`:

```typescript
'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { SeasonalityData } from '@/lib/types';
import { fmt, fmtInt } from '@/lib/formatters';
import KpiGrid from '@/components/kpi/KpiGrid';
import KpiCard from '@/components/kpi/KpiCard';
import ChartCard from '@/components/charts/ChartCard';
import SeasonalityIndexCard from '@/components/seasonality/SeasonalityIndexCard';
import { Skeleton } from '@heroui/react';
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';

function deltaPct(current: number | null, avg: number | null): string {
  if (!current || !avg || avg === 0) return '—';
  const pct = ((current - avg) / avg) * 100;
  return (pct >= 0 ? '+' : '') + pct.toFixed(1) + '%';
}

function deltaPts(current: number | null, avg: number | null): string {
  if (current === null || avg === null) return '—';
  const pts = ((current - avg) * 100);
  return (pts >= 0 ? '+' : '') + pts.toFixed(1) + 'pts';
}

function signalColor(current: number | null, avg: number | null, inverted = false): 'success' | 'danger' | 'default' {
  if (current === null || avg === null) return 'default';
  const better = inverted ? current < avg : current > avg;
  return better ? 'success' : 'danger';
}

export default function SeasonalityPage() {
  const { data, loading } = useJsonData<SeasonalityData>('seasonality');

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64 rounded-xl" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (!data) return <p className="text-brand-neutral/50">Seasonality data unavailable.</p>;

  const { index, current_week, current_week_signals: s, weekly_history } = data;

  // Chart data: 52 weeks
  const chartData = weekly_history.map(w => ({
    name: `Wk ${w.week}`,
    avg: w.seasonality_avg,
    current: w.current_year,
  }));

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">
          Seasonality Index
        </h1>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">
          Week {current_week} of 52 — {data.generated_at}
        </span>
      </div>

      {/* Three index KPIs */}
      <KpiGrid columns={3}>
        <SeasonalityIndexCard index={index} />
        <KpiCard
          label="Demand Index"
          value={index.demand !== null ? index.demand.toFixed(2) : '—'}
          note="Revenue + Orders"
        />
        <KpiCard
          label="Performance Index"
          value={index.performance !== null ? index.performance.toFixed(2) : '—'}
          note="MER + IS Rank + IS Budget"
        />
      </KpiGrid>

      {/* 52-week chart */}
      <ChartCard title="52-Week Seasonality Index — Historical Average vs Current Year">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 9, fill: '#212529' }}
              interval={3}
            />
            <YAxis
              domain={[0, 2]}
              ticks={[0, 0.5, 1.0, 1.5, 2.0]}
              tick={{ fontSize: 10, fill: '#212529' }}
            />
            <Tooltip formatter={(v: number) => v?.toFixed(2)} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <ReferenceLine y={1.0} stroke="rgba(191,201,193,0.4)" strokeDasharray="4 3" label={{ value: 'Avg', position: 'right', fontSize: 9, fill: '#64748b' }} />
            <ReferenceLine x={`Wk ${current_week}`} stroke="#f97316" strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="avg"
              name="Historical Avg"
              stroke="#52796F"
              strokeWidth={1.5}
              strokeDasharray="5 3"
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="current"
              name="Current Year"
              stroke="#2d6A4F"
              strokeWidth={2.5}
              dot={false}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Signal breakdown tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">

        {/* Demand signals */}
        <div className="bg-surface-lowest rounded-xl shadow-ambient p-4 md:p-5">
          <h3 className="text-xs uppercase tracking-wider text-brand-neutral/50 mb-4">
            Demand Signals — Week {current_week}
          </h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-brand-neutral/40 border-b border-brand-neutral/10">
                <th className="text-left pb-2">Signal</th>
                <th className="text-right pb-2">This Week</th>
                <th className="text-right pb-2">Historical Avg</th>
                <th className="text-right pb-2">Delta</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-neutral/5">
              <tr className="py-2">
                <td className="py-2.5 text-brand-neutral/70">WC Revenue</td>
                <td className="py-2.5 text-right font-medium text-brand-neutral">{fmt(s.wc_revenue)}</td>
                <td className="py-2.5 text-right text-brand-neutral/50">{s.wc_revenue_avg ? fmt(s.wc_revenue_avg) : '—'}</td>
                <td className={`py-2.5 text-right text-xs font-medium ${s.wc_revenue > (s.wc_revenue_avg ?? 0) ? 'text-green-500' : 'text-red-400'}`}>
                  {deltaPct(s.wc_revenue, s.wc_revenue_avg)}
                </td>
              </tr>
              <tr>
                <td className="py-2.5 text-brand-neutral/70">Orders</td>
                <td className="py-2.5 text-right font-medium text-brand-neutral">{fmtInt(s.orders)}</td>
                <td className="py-2.5 text-right text-brand-neutral/50">{s.orders_avg ? fmtInt(s.orders_avg) : '—'}</td>
                <td className={`py-2.5 text-right text-xs font-medium ${s.orders > (s.orders_avg ?? 0) ? 'text-green-500' : 'text-red-400'}`}>
                  {deltaPct(s.orders, s.orders_avg)}
                </td>
              </tr>
              <tr>
                <td className="py-2.5 text-brand-neutral/70">Blended MER</td>
                <td className="py-2.5 text-right font-medium text-brand-neutral">{s.blended_mer !== null ? s.blended_mer.toFixed(2) + 'x' : '—'}</td>
                <td className="py-2.5 text-right text-brand-neutral/50">{s.blended_mer_avg ? s.blended_mer_avg.toFixed(2) + 'x' : '—'}</td>
                <td className={`py-2.5 text-right text-xs font-medium ${(s.blended_mer ?? 0) > (s.blended_mer_avg ?? 0) ? 'text-green-500' : 'text-red-400'}`}>
                  {deltaPct(s.blended_mer, s.blended_mer_avg)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Performance signals */}
        <div className="bg-surface-lowest rounded-xl shadow-ambient p-4 md:p-5">
          <h3 className="text-xs uppercase tracking-wider text-brand-neutral/50 mb-4">
            Performance Signals — Week {current_week}
          </h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-brand-neutral/40 border-b border-brand-neutral/10">
                <th className="text-left pb-2">Signal</th>
                <th className="text-right pb-2">This Week</th>
                <th className="text-right pb-2">Historical Avg</th>
                <th className="text-right pb-2">Delta</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-neutral/5">
              <tr>
                <td className="py-2.5 text-brand-neutral/70">IS Rank</td>
                <td className="py-2.5 text-right font-medium text-brand-neutral">
                  {s.is_rank !== null ? (s.is_rank * 100).toFixed(1) + '%' : '—'}
                </td>
                <td className="py-2.5 text-right text-brand-neutral/50">
                  {s.is_rank_avg ? (s.is_rank_avg * 100).toFixed(1) + '%' : '—'}
                </td>
                <td className={`py-2.5 text-right text-xs font-medium ${(s.is_rank ?? 0) > (s.is_rank_avg ?? 0) ? 'text-green-500' : 'text-red-400'}`}>
                  {deltaPts(s.is_rank, s.is_rank_avg)}
                </td>
              </tr>
              <tr>
                <td className="py-2.5 text-brand-neutral/70">IS Budget Lost</td>
                <td className="py-2.5 text-right font-medium text-brand-neutral">
                  {s.is_budget_lost !== null ? (s.is_budget_lost * 100).toFixed(1) + '%' : '—'}
                </td>
                <td className="py-2.5 text-right text-brand-neutral/50">
                  {s.is_budget_lost_avg ? (s.is_budget_lost_avg * 100).toFixed(1) + '%' : '—'}
                </td>
                <td className={`py-2.5 text-right text-xs font-medium ${(s.is_budget_lost ?? 1) < (s.is_budget_lost_avg ?? 1) ? 'text-green-500' : 'text-red-400'}`}>
                  {deltaPts(s.is_budget_lost, s.is_budget_lost_avg)}
                </td>
              </tr>
              <tr>
                <td className="py-2.5 text-brand-neutral/70">Ad Spend</td>
                <td className="py-2.5 text-right font-medium text-brand-neutral">{fmt(s.ad_spend)}</td>
                <td className="py-2.5 text-right text-brand-neutral/50">{s.ad_spend_avg ? fmt(s.ad_spend_avg) : '—'}</td>
                <td className="py-2.5 text-right text-xs font-medium text-brand-neutral/50">
                  {deltaPct(s.ad_spend, s.ad_spend_avg)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 8.2 — Commit**

```bash
git add "dashboard/src/app/inventory/seasonality/page.tsx"
git commit -m "feat: add Seasonality page at /inventory/seasonality"
```

---

## Task 9: Sidebar — Add Seasonality Nav Item

**Files:**
- Modify: `dashboard/src/components/layout/Sidebar.tsx`

- [ ] **Step 9.1 — Add TrendingUp import (already imported, reuse it) + Seasonality nav item**

Open `dashboard/src/components/layout/Sidebar.tsx`. In the `navItems` array, find the `Operations` entry. Add `Seasonality` as the last child:

```typescript
  {
    label: 'Operations',
    href: '/inventory',
    icon: Package,
    children: [
      { label: 'Current Stock', href: '/inventory', icon: Boxes },
      { label: 'Forecasting', href: '/inventory/forecasting', icon: LineChart },
      { label: 'FBA Inventory', href: '/inventory/fba', icon: Warehouse },
      { label: 'Shipping Insights', href: '/inventory/shipping', icon: Truck },
      { label: 'ABC Product Report', href: '/inventory/abc', icon: ClipboardList },
      { label: 'Seasonality', href: '/inventory/seasonality', icon: TrendingUp },
    ],
  },
```

Note: `TrendingUp` is already imported at the top of the file.

- [ ] **Step 9.2 — Commit**

```bash
git add "dashboard/src/components/layout/Sidebar.tsx"
git commit -m "feat: add Seasonality nav item under Operations in sidebar"
```

---

## Task 10: Wire Seed Data + Verify Build

- [ ] **Step 10.1 — Create a minimal seed `seasonality.json` for local dev**

Create `docs/data/seasonality.json` with placeholder data so the dashboard builds without errors:

```json
{
  "generated_at": "2026-04-22",
  "current_week": 17,
  "index": {
    "seasonality": null,
    "demand": null,
    "performance": null,
    "label": "Insufficient Data"
  },
  "current_week_signals": {
    "wc_revenue": 0,
    "wc_revenue_avg": null,
    "orders": 0,
    "orders_avg": null,
    "blended_mer": null,
    "blended_mer_avg": null,
    "is_rank": null,
    "is_rank_avg": null,
    "is_budget_lost": null,
    "is_budget_lost_avg": null,
    "ad_spend": 0,
    "ad_spend_avg": null
  },
  "weekly_baselines": {},
  "weekly_history": []
}
```

- [ ] **Step 10.2 — Run the dashboard build locally**

```bash
cd "dashboard"
npm run build 2>&1 | tail -20
```

Expected: build succeeds, no TypeScript errors.

- [ ] **Step 10.3 — Run the dev server and verify both pages**

```bash
cd "dashboard"
npm run dev
```

- Open `http://localhost:3000/reporting` — confirm 6 KPI cards render, Season Index shows `—` with `Insufficient Data` label.
- Open `http://localhost:3000/inventory/seasonality` — confirm page renders with empty state (no crash).
- Confirm `Seasonality` appears in the sidebar under Operations.

- [ ] **Step 10.4 — Final commit**

```bash
git add "docs/data/seasonality.json"
git commit -m "feat: add seed seasonality.json for local dev + CI"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Dual-track index (Demand + Performance) — Tasks 1–3
- ✅ IS Rank + IS Budget Lost added to Google Ads pull — Task 2
- ✅ Weekly baselines from full API history — Tasks 2–3
- ✅ Raw data disposable (not stored in output) — Task 3 (baselines stored, not raw)
- ✅ Week-of-year granularity — Task 3
- ✅ 0–2 scale with labels — Tasks 1, 6
- ✅ Operations page at `/inventory/seasonality` — Tasks 8, 9
- ✅ DTC MTD 6th KPI card — Tasks 5, 7
- ✅ Daily update via GitHub Actions — Task 4
- ✅ 52-week chart — Task 8
- ✅ Signal breakdown tables — Task 8

**Placeholder scan:** None found. All code blocks are complete.

**Type consistency:** `SeasonalityData`, `SeasonalityIndex`, `SeasonalityWeekSignals`, `SeasonalityWeekHistory` defined in Task 5 and used consistently in Tasks 6, 7, 8.

**Edge cases handled:**
- Missing baselines → `"Insufficient Data"` label, null index values (won't crash)
- Zero mean in normalize → returns None, excluded from averages
- IS data unavailable (Google Ads returns 0.0) → filtered out
- First run (no existing JSON) → full historical pull triggered
- Subsequent runs → baselines reused, only current week pulled
