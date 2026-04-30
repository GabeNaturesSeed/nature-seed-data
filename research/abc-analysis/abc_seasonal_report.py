#!/usr/bin/env python3
"""
Nature's Seed — ABC Seasonal Report Generator

Pulls WooCommerce orders for up to 3 seasons, aggregates per-SKU metrics,
scores with an 8-factor weighted model, classifies A/B/C, and outputs
docs/data/abc_report.json for the dashboard.

Usage:
  python3 abc_seasonal_report.py                    # All 3 seasons
  python3 abc_seasonal_report.py spring_2026        # Single season
  python3 abc_seasonal_report.py --refresh          # Force re-pull all
"""

import json
import sys
import time
import os
import base64
import math
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict

import requests

# Use numpy if available, fallback to pure Python
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = Path(__file__).resolve().parent / "cache"
OUTPUT_PATH = REPO_ROOT / "docs" / "data" / "abc_report.json"

SEASONS = {
    "spring_2026": ("Spring 2026", "2026-02-01", "2026-04-30"),
    "fall_2025":   ("Fall 2025",   "2025-08-01", "2025-09-30"),
    "spring_2025": ("Spring 2025", "2025-02-01", "2025-04-30"),
}

# 8-factor weights (revenue_velocity = revenue/active_days, normalizes for late-added products)
WEIGHTS = {
    "revenue_velocity":  0.30,
    "margin":            0.15,
    "units":             0.15,
    "orders":            0.10,
    "avg_basket":        0.10,
    "velocity_trend":    0.08,
    "backorder_rate":    0.07,  # inverted
    "cancellation_rate": 0.05,  # inverted
}

DEFAULT_MARGIN_PCT = 0.65  # fallback if no COGS match


def _linregress_slope(x, y):
    """Simple linear regression slope (pure Python)."""
    n = len(x)
    if n < 2:
        return 0.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    ss_xx = sum((xi - mean_x) ** 2 for xi in x)
    return ss_xy / ss_xx if ss_xx != 0 else 0.0


def _median(values):
    """Pure Python median."""
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]


def _mean(values):
    """Pure Python mean."""
    return sum(values) / len(values) if values else 0.0

# ══════════════════════════════════════════════════════════════
# ENV PARSING
# ══════════════════════════════════════════════════════════════

env_path = REPO_ROOT / ".env"
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

WC_BASE = env_vars.get("WC_BASE_URL", "https://naturesseed.com/wp-json/wc/v3")
WC_CK = env_vars["WC_CK"]
WC_CS = env_vars["WC_CS"]
WC_AUTH = (WC_CK, WC_CS)

CF_WORKER_URL = env_vars.get("CF_WORKER_URL", "")
CF_WORKER_SECRET = env_vars.get("CF_WORKER_SECRET", "")

SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")


# ══════════════════════════════════════════════════════════════
# WC API HELPERS
# ══════════════════════════════════════════════════════════════

def wc_get(endpoint, params, max_retries=3):
    """WC API GET with CF Worker proxy support and retry logic."""
    url = f"{WC_BASE}{endpoint}"
    for attempt in range(max_retries):
        if CF_WORKER_URL and CF_WORKER_SECRET:
            proxy_params = dict(params)
            proxy_params["wc_path"] = endpoint
            auth_str = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
            headers = {
                "X-Proxy-Secret": CF_WORKER_SECRET,
                "Authorization": f"Basic {auth_str}",
                "User-Agent": "NaturesSeed-ABCReport/1.0",
            }
            resp = requests.get(CF_WORKER_URL, params=proxy_params, headers=headers, timeout=60)
        else:
            headers = {"User-Agent": "NaturesSeed-ABCReport/1.0"}
            resp = requests.get(url, auth=WC_AUTH, params=params, headers=headers, timeout=60)

        if resp.status_code == 200:
            return resp
        if resp.status_code in (403, 429, 500, 502, 503) and attempt < max_retries - 1:
            wait = 5 * (attempt + 1)
            print(f"    [RETRY] {resp.status_code}, waiting {wait}s (attempt {attempt+1}/{max_retries})")
            time.sleep(wait)
            continue
        resp.raise_for_status()
    return resp


def pull_wc_orders(date_start, date_end, statuses=("completed", "processing")):
    """Pull all WC orders for a date range and statuses."""
    all_orders = []
    for status in statuses:
        page = 1
        while True:
            params = {
                "after": f"{date_start}T00:00:00",
                "before": f"{date_end}T23:59:59",
                "status": status,
                "per_page": 100,
                "page": page,
            }
            resp = wc_get("/orders", params)
            orders = resp.json()
            if not orders:
                break
            all_orders.extend(orders)
            total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
            print(f"    [{status}] page {page}/{total_pages} — {len(orders)} orders")
            if page >= total_pages:
                break
            page += 1
            time.sleep(0.3)
    return all_orders


def pull_cancelled_orders(date_start, date_end):
    """Pull cancelled orders for the date range."""
    return pull_wc_orders(date_start, date_end, statuses=("cancelled",))


# ══════════════════════════════════════════════════════════════
# SUPABASE — COGS
# ══════════════════════════════════════════════════════════════

def load_cogs_lookup():
    """Load SKU → unit_cost from Supabase cogs_lookup table."""
    url = f"{SUPABASE_URL}/rest/v1/cogs_lookup"
    headers = {"apikey": SUPABASE_KEY}
    params = {"select": "sku,unit_cost", "limit": 1000}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    lookup = {}
    for r in rows:
        if r.get("sku") and r.get("unit_cost") is not None:
            lookup[r["sku"]] = float(r["unit_cost"])
    print(f"  [COGS] Loaded {len(lookup)} SKU costs from Supabase")
    return lookup


# ══════════════════════════════════════════════════════════════
# CACHING
# ══════════════════════════════════════════════════════════════

def _cache_path(season_key, kind):
    return CACHE_DIR / f"{season_key}_{kind}.json"


def _season_is_complete(season_key):
    """A season is complete if its end date is in the past."""
    _, _, end_str = SEASONS[season_key]
    return date.fromisoformat(end_str) < date.today()


def load_or_pull_orders(season_key, force_refresh=False):
    """Load orders from cache or pull from WC API. Current seasons always re-pull."""
    label, start, end = SEASONS[season_key]
    # Clamp end date to today if season is ongoing
    effective_end = min(end, str(date.today()))

    completed_cache = _cache_path(season_key, "completed")
    cancelled_cache = _cache_path(season_key, "cancelled")

    use_cache = (
        not force_refresh
        and _season_is_complete(season_key)
        and completed_cache.exists()
        and cancelled_cache.exists()
    )

    if use_cache:
        print(f"\n[{label}] Loading from cache (season complete)")
        with open(completed_cache) as f:
            completed = json.load(f)
        with open(cancelled_cache) as f:
            cancelled = json.load(f)
    else:
        reason = "force refresh" if force_refresh else ("ongoing season" if not _season_is_complete(season_key) else "no cache")
        print(f"\n[{label}] Pulling from WC API ({reason})... {start} → {effective_end}")
        completed = pull_wc_orders(start, effective_end)
        cancelled = pull_cancelled_orders(start, effective_end)

        # Cache the results
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(completed_cache, "w") as f:
            json.dump(completed, f)
        with open(cancelled_cache, "w") as f:
            json.dump(cancelled, f)
        print(f"  Cached: {len(completed)} completed/processing, {len(cancelled)} cancelled")

    return completed, cancelled, effective_end


# ══════════════════════════════════════════════════════════════
# AGGREGATION
# ══════════════════════════════════════════════════════════════

def build_parent_map(product_ids):
    """Fetch parent product SKU/name for a set of product_ids via WC /products bulk call."""
    parent_map = {}
    ids_list = list(product_ids)
    for i in range(0, len(ids_list), 100):
        chunk = ids_list[i:i + 100]
        resp = wc_get("/products", {"include": ",".join(str(x) for x in chunk), "per_page": 100})
        for p in resp.json():
            parent_map[p["id"]] = {
                "sku": p.get("sku", ""),
                "name": p.get("name", ""),
                "date_created": (p.get("date_created") or "")[:10],
            }
        time.sleep(0.25)
    print(f"  [Parent Map] {len(parent_map)} parent products mapped")
    return parent_map


def aggregate_by_parent(completed_orders, cancelled_orders, cogs_lookup, date_start, date_end, parent_map):
    """Aggregate metrics grouped by product_id (parent product), tracking variants."""
    parent_data = defaultdict(lambda: {
        "sku": "", "name": "", "date_created": "",
        "revenue": 0.0, "units": 0, "orders": set(), "order_totals": [],
        "weekly_revenue": defaultdict(float),
        "backordered_qty": 0,
        "variants": defaultdict(lambda: {"sku": "", "name": "", "revenue": 0.0, "units": 0, "orders": 0}),
    })

    start_date = date.fromisoformat(date_start)

    for order in completed_orders:
        order_id = order.get("id")
        order_total = float(order.get("total", 0))
        order_date_str = order.get("date_created", "")[:10]
        try:
            order_date = date.fromisoformat(order_date_str)
        except (ValueError, TypeError):
            continue
        week_num = (order_date - start_date).days // 7

        for item in order.get("line_items", []):
            pid = item.get("product_id", 0)
            sku = (item.get("sku") or "").strip()
            name = item.get("name", "")
            qty = item.get("quantity", 0)
            line_total = float(item.get("total", 0))

            info = parent_map.get(pid, {})
            parent_sku = info.get("sku") or str(pid)
            parent_name = info.get("name") or name

            d = parent_data[pid]
            d["sku"] = parent_sku
            d["name"] = parent_name
            d["date_created"] = info.get("date_created", "")
            d["revenue"] += line_total
            d["units"] += qty
            d["orders"].add(order_id)
            d["order_totals"].append(order_total)
            d["weekly_revenue"][week_num] += line_total

            if sku:
                d["variants"][sku]["sku"] = sku
                d["variants"][sku]["name"] = name
                d["variants"][sku]["revenue"] += line_total
                d["variants"][sku]["units"] += qty
                d["variants"][sku]["orders"] += 1

            for meta in item.get("meta_data", []):
                if meta.get("key") == "_backordered" and meta.get("value"):
                    try:
                        d["backordered_qty"] += int(meta["value"])
                    except (ValueError, TypeError):
                        pass

    # Cancelled order counts by product_id
    cancelled_pids = defaultdict(int)
    for order in cancelled_orders:
        pids_seen = set()
        for item in order.get("line_items", []):
            pid = item.get("product_id", 0)
            if pid and pid not in pids_seen:
                cancelled_pids[pid] += 1
                pids_seen.add(pid)

    end_date = date.fromisoformat(date_end)
    days_in_period = max((end_date - start_date).days, 1)

    results = []
    for pid, d in parent_data.items():
        order_count = len(d["orders"])
        revenue = d["revenue"]
        units = d["units"]

        # Active days: how many days in this window the product actually existed
        created_str = d.get("date_created", "")
        try:
            created_date = date.fromisoformat(created_str) if created_str else None
        except ValueError:
            created_date = None
        if created_date and created_date > start_date:
            active_days = max(1, (end_date - created_date).days)
        else:
            active_days = days_in_period

        # Margin: sum COGS per variant SKU, fall back to default margin pct
        total_cogs = 0.0
        has_cogs = False
        for vsku, vdata in d["variants"].items():
            unit_cost = cogs_lookup.get(vsku)
            if unit_cost is not None:
                total_cogs += unit_cost * vdata["units"]
                has_cogs = True
        margin = (revenue - total_cogs) if has_cogs else (revenue * DEFAULT_MARGIN_PCT)
        margin_pct = (margin / revenue * 100) if revenue > 0 else 0

        avg_basket = _mean(d["order_totals"]) if d["order_totals"] else 0
        daily_velocity = round(units / active_days, 2)
        revenue_velocity = round(revenue / active_days, 2)

        weekly = d["weekly_revenue"]
        if len(weekly) >= 2:
            weeks = sorted(weekly.keys())
            velocity_trend = round(_linregress_slope([float(w) for w in weeks], [weekly[w] for w in weeks]), 4)
        else:
            velocity_trend = 0.0

        backorder_rate = d["backordered_qty"] / units if units > 0 else 0.0

        total_appearances = order_count + cancelled_pids.get(pid, 0)
        cancellation_rate = cancelled_pids.get(pid, 0) / total_appearances if total_appearances > 0 else 0.0

        variants = sorted(
            [{"sku": v["sku"], "name": v["name"], "revenue": round(v["revenue"], 2),
              "units": v["units"], "orders": v["orders"]}
             for v in d["variants"].values()],
            key=lambda x: x["revenue"], reverse=True,
        )

        results.append({
            "sku": d["sku"],
            "name": d["name"],
            "product_id": pid,
            "revenue": round(revenue, 2),
            "margin": round(margin, 2),
            "margin_pct": round(margin_pct, 1),
            "units": units,
            "orders": order_count,
            "avg_basket": round(float(avg_basket), 2),
            "active_days": active_days,
            "daily_velocity": daily_velocity,
            "revenue_velocity": revenue_velocity,
            "velocity_trend": velocity_trend,
            "backorder_rate": round(backorder_rate, 4),
            "cancellation_rate": round(cancellation_rate, 4),
            "variants": variants,
        })

    return results


# ══════════════════════════════════════════════════════════════
# SCORING & CLASSIFICATION
# ══════════════════════════════════════════════════════════════

def percentile_rank(values):
    """Return percentile ranks (0-100) for a list of values (pure Python)."""
    n = len(values)
    if n == 0:
        return []
    # Create (value, original_index) pairs, sort by value
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * n
    i = 0
    while i < n:
        # Find all ties
        j = i
        while j < n and indexed[j][1] == indexed[i][1]:
            j += 1
        # Average rank for ties (0-based)
        avg_rank = (i + j - 1) / 2
        for k in range(i, j):
            orig_idx = indexed[k][0]
            ranks[orig_idx] = (avg_rank / max(n - 1, 1)) * 100
        i = j
    return ranks


def score_and_classify(items):
    """Score SKUs using weighted percentiles, classify A/B/C."""
    if not items:
        return []

    factors = ["revenue_velocity", "margin", "units", "orders", "avg_basket", "velocity_trend", "backorder_rate", "cancellation_rate"]
    inverted = {"backorder_rate", "cancellation_rate"}

    # Compute percentile ranks per factor
    pct_ranks = {}
    for f in factors:
        values = [item[f] for item in items]
        ranks = percentile_rank(values)
        if f in inverted:
            ranks = [100 - r for r in ranks]
        pct_ranks[f] = ranks

    # Weighted composite score
    for i, item in enumerate(items):
        score = sum(pct_ranks[f][i] * WEIGHTS[f] for f in factors)
        item["composite_score"] = round(score, 2)

    # Sort by composite score descending
    items.sort(key=lambda x: x["composite_score"], reverse=True)

    # Classify using revenue_velocity (revenue/active_days) for cumulative cuts.
    # This normalizes for products created after the season start so they aren't
    # penalized by having fewer active days than established products.
    # A = top 80% cumulative velocity, B = next 15%, C = bottom 5%
    total_velocity = sum(i["revenue_velocity"] for i in items)
    if total_velocity == 0:
        for item in items:
            item["class"] = "C"
        return items

    cumulative = 0.0
    for item in items:
        cumulative += item["revenue_velocity"]
        pct = cumulative / total_velocity
        if pct <= 0.80:
            item["class"] = "A"
        elif pct <= 0.95:
            item["class"] = "B"
        else:
            item["class"] = "C"

    return items


# ══════════════════════════════════════════════════════════════
# REASON GENERATION
# ══════════════════════════════════════════════════════════════

def generate_reasons(items):
    """Generate plain-English reason for each SKU's classification."""
    if not items:
        return items

    # Compute medians for comparison
    revenues = [i["revenue_velocity"] for i in items]
    margins = [i["margin_pct"] for i in items]
    med_revenue = _median(revenues)
    med_margin = _median(margins)

    for item in items:
        parts = []
        cls = item["class"]
        max_days = max(i["active_days"] for i in items)
        new_flag = f" ({item['active_days']}d active)" if item["active_days"] < max_days else ""

        if cls == "A":
            parts.append("Top performer")
            if item["revenue_velocity"] > med_revenue * 2:
                parts.append(f"${item['revenue_velocity']:,.0f}/day is {item['revenue_velocity']/med_revenue:.1f}x the median velocity{new_flag}")
            if item["margin_pct"] > 70:
                parts.append(f"strong {item['margin_pct']:.0f}% margin")
            if item["velocity_trend"] > 0.5:
                parts.append("accelerating sales trend")
            if item["avg_basket"] > 150:
                parts.append(f"drives ${item['avg_basket']:,.0f} avg basket")
        elif cls == "B":
            parts.append("Mid-tier SKU")
            if item["margin_pct"] > med_margin:
                parts.append(f"above-median {item['margin_pct']:.0f}% margin")
            else:
                parts.append(f"{item['margin_pct']:.0f}% margin")
            if item["velocity_trend"] > 0:
                parts.append("positive trend")
            elif item["velocity_trend"] < -0.5:
                parts.append("declining velocity")
        else:  # C
            parts.append("Low volume")
            if item["units"] <= 5:
                parts.append(f"only {item['units']} units sold")
            if item["cancellation_rate"] > 0.1:
                parts.append(f"{item['cancellation_rate']*100:.0f}% cancellation rate")
            if item["velocity_trend"] < -0.5:
                parts.append("declining trend")

        # Universal signals
        if item["backorder_rate"] > 0.05:
            parts.append(f"{item['backorder_rate']*100:.1f}% backorder rate — stock risk")
        if item["cancellation_rate"] > 0.15 and cls != "C":
            parts.append(f"watch {item['cancellation_rate']*100:.0f}% cancellation rate")

        item["reason"] = " — ".join(parts[:3]) + "."

    return items


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def process_season(season_key, cogs_lookup, force_refresh=False):
    """Process a single season: pull data, aggregate, score, classify."""
    label, start, end = SEASONS[season_key]

    completed, cancelled, effective_end = load_or_pull_orders(season_key, force_refresh)
    print(f"  Orders: {len(completed)} completed/processing, {len(cancelled)} cancelled")

    # Build parent product map from all product_ids in completed orders
    product_ids = {item.get("product_id") for order in completed for item in order.get("line_items", []) if item.get("product_id")}
    parent_map = build_parent_map(product_ids)

    items = aggregate_by_parent(completed, cancelled, cogs_lookup, start, effective_end, parent_map)
    print(f"  Parent products: {len(items)}")

    items = score_and_classify(items)
    items = generate_reasons(items)

    # Summary
    a_items = [i for i in items if i["class"] == "A"]
    b_items = [i for i in items if i["class"] == "B"]
    c_items = [i for i in items if i["class"] == "C"]

    total_revenue = sum(i["revenue"] for i in items)
    a_revenue = sum(i["revenue"] for i in a_items)
    b_revenue = sum(i["revenue"] for i in b_items)
    c_revenue = sum(i["revenue"] for i in c_items)

    summary = {
        "a_count": len(a_items),
        "a_revenue": round(a_revenue, 2),
        "a_pct": round(a_revenue / total_revenue * 100, 1) if total_revenue else 0,
        "b_count": len(b_items),
        "b_revenue": round(b_revenue, 2),
        "b_pct": round(b_revenue / total_revenue * 100, 1) if total_revenue else 0,
        "c_count": len(c_items),
        "c_revenue": round(c_revenue, 2),
        "c_pct": round(c_revenue / total_revenue * 100, 1) if total_revenue else 0,
    }

    print(f"  Classification: A={summary['a_count']} ({summary['a_pct']}%), "
          f"B={summary['b_count']} ({summary['b_pct']}%), "
          f"C={summary['c_count']} ({summary['c_pct']}%)")

    return {
        "label": label,
        "period": f"{start} → {effective_end}",
        "total_revenue": round(total_revenue, 2),
        "total_orders": sum(i["orders"] for i in items),
        "total_skus": len(items),
        "summary": summary,
        "items": items,
    }


def main():
    args = sys.argv[1:]
    force_refresh = "--refresh" in args
    season_keys = [a for a in args if a != "--refresh"]

    if not season_keys:
        season_keys = list(SEASONS.keys())
    else:
        for k in season_keys:
            if k not in SEASONS:
                print(f"Unknown season: {k}. Valid: {', '.join(SEASONS.keys())}")
                sys.exit(1)

    print("=" * 60)
    print("Nature's Seed — ABC Seasonal Report")
    print(f"Generated: {datetime.now().isoformat()}")
    print(f"Seasons: {', '.join(season_keys)}")
    if force_refresh:
        print("Mode: FORCE REFRESH (ignoring cache)")
    print("=" * 60)

    # Load COGS
    cogs_lookup = load_cogs_lookup()

    # Process each season
    report = {
        "generated": datetime.now().isoformat(),
        "seasons": {},
    }

    for key in season_keys:
        report["seasons"][key] = process_season(key, cogs_lookup, force_refresh)

    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"Report written to: {OUTPUT_PATH}")
    print(f"Seasons: {len(report['seasons'])}")
    for k, v in report["seasons"].items():
        print(f"  {v['label']}: {v['total_skus']} SKUs, ${v['total_revenue']:,.2f} revenue")
    print("=" * 60)


if __name__ == "__main__":
    main()
