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
SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")
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
    if mean == 0.0:
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
    norm_is_rank = normalize(is_rank, baseline["is_rank_mean"]) if is_rank is not None and baseline.get("is_rank_mean") else None
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


# ════════════════════════════════════════════════════════════
# API PULL FUNCTIONS
# ════════════════════════════════════════════════════════════

def _sb_get(path, params=None):
    """GET from Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    p = dict(params or {})
    if "limit" not in p:
        p["limit"] = 50000
    resp = requests.get(url, headers=headers, params=p, timeout=60)
    resp.raise_for_status()
    return resp.json()


def pull_wc_history() -> dict:
    """Pull WC daily revenue and orders from Supabase daily_sales table.
    Returns {date_str: {revenue: float, orders: int}}.
    Uses Supabase instead of paginated WC API — much faster for historical pulls.
    """
    print("  Pulling WooCommerce history from Supabase daily_sales...")
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("    [WARN] Supabase credentials not configured")
        return {}

    history_start = date(TODAY.year - YEARS_BACK, 1, 1).isoformat()
    try:
        rows = _sb_get("daily_sales", {
            "select": "report_date,revenue,orders",
            "report_date": f"gte.{history_start}",
            "channel": "eq.woocommerce",
            "order": "report_date.asc",
        })
    except Exception as e:
        print(f"    [WARN] Supabase daily_sales failed: {e}")
        return {}

    result: dict = {}
    for r in rows:
        d = r.get("report_date", "")
        if d:
            result[d] = {
                "revenue": float(r.get("revenue") or 0),
                "orders": int(r.get("orders") or 0),
            }

    print(f"    Supabase: {len(result)} days pulled")
    return result


def pull_gads_history() -> dict:
    """Pull Google Ads daily metrics (cost, IS rank, IS budget lost) for all history.
    Returns {date_str: {cost: float, is_rank: float|None, is_budget_lost: float|None}}.
    """
    print("  Pulling Google Ads history...")
    if not HAS_GOOGLE_ADS:
        print("    [WARN] google-ads package not installed")
        return {}
    if not all([GADS_DEVELOPER_TOKEN, GADS_CLIENT_ID, GADS_CLIENT_SECRET, GADS_REFRESH_TOKEN, GADS_CUSTOMER_ID, GADS_LOGIN_CID]):
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
    try:
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
    except Exception as e:
        print(f"    [WARN] Google Ads stream error after {len(raw)} days: {e}")

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
    """Build 52-entry weekly history array for current year + historical averages.
    Returns list of {week, seasonality_avg, demand_avg, performance_avg, current_year}.
    """
    cy_wc = _aggregate_wc_by_week(wc_daily, TODAY.year)
    cy_gads = _aggregate_gads_by_week(gads_daily, TODAY.year)
    current_iso_week = TODAY.isocalendar()[1]

    history = []
    for week_num in range(1, 53):
        baseline = baselines.get(str(week_num))
        if not baseline:
            avg_entry = {"week": week_num, "seasonality_avg": None, "demand_avg": None, "performance_avg": None}
        else:
            avg_entry = {"week": week_num, "seasonality_avg": 1.0, "demand_avg": 1.0, "performance_avg": 1.0}

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

    baselines = existing.get("weekly_baselines") if existing.get("weekly_baselines") else None

    if baselines:
        print("  Baselines found — pulling current year Google Ads only")
        wc_daily = {}
        gads_daily = pull_gads_history()
        # Rebuild WC weekly aggregates from stored baselines context (not re-pulled)
        # For history chart we use prior computed current_year values and extend
        wc_daily_for_history = {}
        gads_daily_for_history = gads_daily
    else:
        print("  No baselines found — running full historical pull")
        wc_daily = pull_wc_history()
        gads_daily = pull_gads_history()
        baselines = compute_weekly_baselines(wc_daily, gads_daily)
        wc_daily_for_history = wc_daily
        gads_daily_for_history = gads_daily
        print(f"  Baselines computed for {len(baselines)} weeks")

    # ── Step 2: Current week aggregates ─────────────────────
    current_week_num = TODAY.isocalendar()[1]
    cy_wc = _aggregate_wc_by_week(wc_daily, TODAY.year)
    cy_gads = _aggregate_gads_by_week(gads_daily, TODAY.year)
    wc_cw = cy_wc.get(current_week_num, {})
    gads_cw = cy_gads.get(current_week_num, {})

    # ── Step 3: Compute current week index ──────────────────
    indexes = compute_index_for_week(current_week_num, wc_cw, gads_cw, baselines)
    baseline_cw = baselines.get(str(current_week_num), {}) if baselines else {}

    mer_cw = (wc_cw.get("revenue", 0) / gads_cw["cost"]
              if gads_cw.get("cost", 0) > 0 else None)

    # ── Step 4: Build 52-week chart history ──────────────────
    weekly_history = build_weekly_history(wc_daily_for_history, gads_daily_for_history, baselines or {})

    # ── Step 5: Write output ─────────────────────────────────
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
            "wc_revenue": round(wc_cw.get("revenue", 0), 2),
            "wc_revenue_avg": baseline_cw.get("revenue_mean"),
            "orders": wc_cw.get("orders", 0),
            "orders_avg": baseline_cw.get("orders_mean"),
            "blended_mer": round(mer_cw, 4) if mer_cw else None,
            "blended_mer_avg": baseline_cw.get("mer_mean"),
            "is_rank": gads_cw.get("is_rank"),
            "is_rank_avg": baseline_cw.get("is_rank_mean"),
            "is_budget_lost": gads_cw.get("is_budget_lost"),
            "is_budget_lost_avg": baseline_cw.get("is_budget_lost_mean"),
            "ad_spend": gads_cw.get("cost", 0),
            "ad_spend_avg": baseline_cw.get("ad_spend_mean"),
        },
        "weekly_baselines": baselines or {},
        "weekly_history": weekly_history,
    }

    _write_json("seasonality.json", output)
    print(f"  Seasonality Index: {indexes['seasonality']} ({indexes['label']})")


if __name__ == "__main__":
    main()
