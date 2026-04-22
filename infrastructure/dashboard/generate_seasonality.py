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


if __name__ == "__main__":
    print("generate_seasonality.py: pipeline not yet implemented")
