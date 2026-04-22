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
        q_month_end = {1: 3, 2: 3, 3: 3, 4: 6, 5: 6, 6: 6, 7: 9, 8: 9, 9: 9, 10: 12, 11: 12, 12: 12}
        end_month = q_month_end[chunk.month]
        end_day = {3: 31, 6: 30, 9: 30, 12: 31}[end_month]
        chunk_end = min(date(chunk.year, end_month, end_day), YESTERDAY)

        print(f"    WC: {chunk} → {chunk_end}")
        combined.update(_pull_wc_quarter(chunk, chunk_end))

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


if __name__ == "__main__":
    print("generate_seasonality.py: pipeline not yet implemented")
