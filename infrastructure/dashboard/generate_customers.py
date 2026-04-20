#!/usr/bin/env python3
"""
Nature's Seed — Customer Dashboard Data Generator
Generates docs/data/customers.json with demographics, attribution, and cohort data.

Sources:
  A. WooCommerce (via CF Worker proxy) — YTD orders for state, hour, attribution
  B. Supabase — customer table for new vs returning classification

Usage:
  python3 infrastructure/dashboard/generate_customers.py
"""

import json
import time
import base64
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from collections import defaultdict

import requests

# ══════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "docs" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════
# ENV PARSING  (spaces around = AND quoted values)
# ══════════════════════════════════════════════════════════════

env_path = ROOT / ".env"
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")

WC_BASE = env_vars.get("WC_BASE_URL", "https://naturesseed.com/wp-json/wc/v3")
WC_CK = env_vars.get("WC_CK", "")
WC_CS = env_vars.get("WC_CS", "")
CF_WORKER_URL = env_vars.get("CF_WORKER_URL", "")
CF_WORKER_SECRET = env_vars.get("CF_WORKER_SECRET", "")

TODAY = date.today()
TODAY_STR = str(TODAY)
YEAR = TODAY.year
YTD_START = f"{YEAR}-01-01"

# ══════════════════════════════════════════════════════════════
# US STATE NAMES
# ══════════════════════════════════════════════════════════════

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

HOUR_LABELS = [
    "12 AM", "1 AM", "2 AM", "3 AM", "4 AM", "5 AM",
    "6 AM", "7 AM", "8 AM", "9 AM", "10 AM", "11 AM",
    "12 PM", "1 PM", "2 PM", "3 PM", "4 PM", "5 PM",
    "6 PM", "7 PM", "8 PM", "9 PM", "10 PM", "11 PM",
]

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _write_json(filename, data):
    path = OUT_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  [OK] Wrote {path.name}")


def _wc_get(path, params=None, retries=3):
    """GET from WooCommerce REST API, routing through CF Worker if configured.
    Includes retry logic for timeout-prone bulk pulls.
    """
    for attempt in range(1, retries + 1):
        try:
            if CF_WORKER_URL:
                p = {"wc_path": path, **(params or {})}
                auth_str = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
                headers = {"X-Proxy-Secret": CF_WORKER_SECRET, "Authorization": f"Basic {auth_str}"}
                resp = requests.get(CF_WORKER_URL, headers=headers, params=p, timeout=60)
            else:
                resp = requests.get(f"{WC_BASE}{path}", auth=(WC_CK, WC_CS), params=params or {}, timeout=60)
            resp.raise_for_status()
            return resp
        except (
            requests.exceptions.ReadTimeout,
            requests.exceptions.HTTPError,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ConnectionError,
        ) as e:
            is_retryable = (
                isinstance(e, (
                    requests.exceptions.ReadTimeout,
                    requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ConnectionError,
                ))
                or (
                    isinstance(e, requests.exceptions.HTTPError)
                    and hasattr(e, 'response')
                    and e.response is not None
                    and e.response.status_code in (502, 503, 504)
                )
            )
            if is_retryable and attempt < retries:
                wait = attempt * 10
                page_info = (params or {}).get('page', '?')
                print(f"    [RETRY] {type(e).__name__} on {path} page {page_info}, retrying in {wait}s ({attempt}/{retries})...")
                time.sleep(wait)
            else:
                raise


def _supabase_get(path, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    p = dict(params or {})
    if "limit" not in p:
        p["limit"] = 10000
    resp = requests.get(url, headers=headers, params=p, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _pull_wc_orders_range(start_date, end_date):
    """Pull all WooCommerce orders in a date range. Returns list of order dicts."""
    all_orders = []
    page = 1
    after = f"{start_date}T00:00:00"
    before = f"{end_date}T23:59:59"

    while True:
        params = {
            "after": after,
            "before": before,
            "status": "completed,processing",
            "per_page": 100,
            "page": page,
        }
        resp = _wc_get("/orders", params)
        orders = resp.json()
        if not orders:
            break
        all_orders.extend(orders)
        page += 1
        time.sleep(0.3)

    return all_orders


def _order_total(order):
    """Extract float total from order, defaulting to 0."""
    try:
        return float(order.get("total", 0))
    except (ValueError, TypeError):
        return 0.0


def _get_meta(order, key):
    """Extract a value from order meta_data by key."""
    for m in order.get("meta_data", []):
        if m.get("key") == key:
            return m.get("value", "")
    return ""


# ══════════════════════════════════════════════════════════════
# SECTION 1: Demographics & Behavior
# ══════════════════════════════════════════════════════════════

def build_orders_by_state(orders):
    """Aggregate orders and revenue by billing state."""
    print("  [1A] Orders by state...")
    state_data = defaultdict(lambda: {"orders": 0, "revenue": 0.0})

    for o in orders:
        state = (o.get("billing", {}).get("state") or "").strip().upper()
        if not state:
            continue
        state_data[state]["orders"] += 1
        state_data[state]["revenue"] += _order_total(o)

    result = []
    for st, d in state_data.items():
        result.append({
            "state": st,
            "state_name": STATE_NAMES.get(st, st),
            "orders": d["orders"],
            "revenue": round(d["revenue"], 2),
        })

    result.sort(key=lambda x: x["orders"], reverse=True)
    print(f"    {len(result)} states, {sum(r['orders'] for r in result)} orders")
    return result


def build_orders_by_hour(orders):
    """Bucket orders into 24 hours based on date_created."""
    print("  [1B] Orders by hour...")
    hour_data = defaultdict(lambda: {"orders": 0, "revenue": 0.0})

    for o in orders:
        dc = o.get("date_created", "")
        if not dc:
            continue
        try:
            # WC returns ISO format: 2026-01-15T14:30:00
            dt = datetime.fromisoformat(dc.replace("Z", "+00:00"))
            h = dt.hour
        except (ValueError, AttributeError):
            continue
        hour_data[h]["orders"] += 1
        hour_data[h]["revenue"] += _order_total(o)

    result = []
    for h in range(24):
        d = hour_data[h]
        result.append({
            "hour": h,
            "label": HOUR_LABELS[h],
            "orders": d["orders"],
            "revenue": round(d["revenue"], 2),
        })

    return result


def build_attribution(orders):
    """Aggregate last-touch attribution from WC order meta."""
    print("  [1C] Attribution...")
    by_source_type = defaultdict(lambda: {"orders": 0, "revenue": 0.0})
    by_utm_source = defaultdict(lambda: {"orders": 0, "revenue": 0.0})

    for o in orders:
        source_type = _get_meta(o, "_wc_order_attribution_source_type") or "unknown"
        utm_source = _get_meta(o, "_wc_order_attribution_utm_source") or "direct"
        rev = _order_total(o)

        by_source_type[source_type]["orders"] += 1
        by_source_type[source_type]["revenue"] += rev
        by_utm_source[utm_source]["orders"] += 1
        by_utm_source[utm_source]["revenue"] += rev

    total_orders = len(orders) or 1

    source_type_list = []
    for src, d in by_source_type.items():
        source_type_list.append({
            "source": src,
            "orders": d["orders"],
            "revenue": round(d["revenue"], 2),
            "pct": round(d["orders"] / total_orders * 100, 1),
        })
    source_type_list.sort(key=lambda x: x["orders"], reverse=True)

    utm_source_list = []
    for src, d in by_utm_source.items():
        utm_source_list.append({
            "source": src,
            "orders": d["orders"],
            "revenue": round(d["revenue"], 2),
            "pct": round(d["orders"] / total_orders * 100, 1),
        })
    utm_source_list.sort(key=lambda x: x["orders"], reverse=True)

    print(f"    {len(source_type_list)} source types, {len(utm_source_list)} utm sources")
    return {
        "by_source_type": source_type_list,
        "by_utm_source": utm_source_list,
    }


def build_sessions_before_buying(orders):
    """Bucket session_count into meaningful ranges."""
    print("  [1D] Sessions before buying...")
    buckets = {"1": 0, "2": 0, "3-5": 0, "6-10": 0, "11+": 0}

    for o in orders:
        raw = _get_meta(o, "_wc_order_attribution_session_count")
        try:
            n = int(raw)
        except (ValueError, TypeError):
            continue

        if n <= 1:
            buckets["1"] += 1
        elif n == 2:
            buckets["2"] += 1
        elif n <= 5:
            buckets["3-5"] += 1
        elif n <= 10:
            buckets["6-10"] += 1
        else:
            buckets["11+"] += 1

    total = sum(buckets.values()) or 1
    result = []
    for bucket, count in buckets.items():
        result.append({
            "bucket": bucket,
            "orders": count,
            "pct": round(count / total * 100, 1),
        })

    return result


# ══════════════════════════════════════════════════════════════
# SECTION 2: New vs Returning + Cohorts
# ══════════════════════════════════════════════════════════════

def build_new_vs_returning(orders):
    """Classify each order as new or returning customer.

    Strategy: collect all customer_id values from YTD orders, then pull
    their prior-year orders to determine who is truly new. Guests
    (customer_id=0) are always counted as new.
    """
    print("  [2A] New vs returning...")

    # Group orders by month
    monthly = defaultdict(lambda: {"new": 0, "returning": 0, "new_revenue": 0.0, "returning_revenue": 0.0})

    # Build a map of customer_id -> earliest order date in our dataset
    # Then also try to pull historical orders from prior year
    cust_first_order = {}  # customer_id -> earliest date_created we know of

    # First pass: collect all customer_ids and their earliest order in YTD
    for o in orders:
        cid = o.get("customer_id", 0)
        if cid == 0:
            continue
        dc = o.get("date_created", "")
        if dc and (cid not in cust_first_order or dc < cust_first_order[cid]):
            cust_first_order[cid] = dc

    # Pull prior year orders in quarterly chunks to avoid CF Worker timeouts
    prior_customer_ids = set()
    prior_orders = []
    py = YEAR - 1
    quarters = [
        (f"{py}-01-01", f"{py}-03-31"),
        (f"{py}-04-01", f"{py}-06-30"),
        (f"{py}-07-01", f"{py}-09-30"),
        (f"{py}-10-01", f"{py}-12-31"),
    ]
    print(f"    Pulling {py} orders (4 quarters) for returning customer detection...")
    for q_start, q_end in quarters:
        print(f"      Quarter {q_start} to {q_end}...")
        q_orders = _pull_wc_orders_range(q_start, q_end)
        prior_orders.extend(q_orders)
        print(f"        {len(q_orders)} orders")
    for o in prior_orders:
        cid = o.get("customer_id", 0)
        if cid > 0:
            prior_customer_ids.add(cid)
    print(f"    {len(prior_orders)} prior-year orders, {len(prior_customer_ids)} unique customers")

    # Also track which customers appeared earlier within YTD
    # Sort orders chronologically to detect intra-year returning
    sorted_orders = sorted(orders, key=lambda o: o.get("date_created", ""))
    seen_ytd = set()

    for o in sorted_orders:
        cid = o.get("customer_id", 0)
        dc = o.get("date_created", "")
        rev = _order_total(o)
        month = dc[:7] if dc else ""
        if not month:
            continue

        if cid == 0:
            # Guest = always new
            monthly[month]["new"] += 1
            monthly[month]["new_revenue"] += rev
        elif cid in prior_customer_ids or cid in seen_ytd:
            # Returning: ordered last year OR already ordered earlier this year
            monthly[month]["returning"] += 1
            monthly[month]["returning_revenue"] += rev
        else:
            monthly[month]["new"] += 1
            monthly[month]["new_revenue"] += rev

        if cid > 0:
            seen_ytd.add(cid)

    # Build sorted monthly list
    months_sorted = sorted(monthly.keys())
    monthly_list = []
    ytd_new = 0
    ytd_returning = 0
    for m in months_sorted:
        d = monthly[m]
        monthly_list.append({
            "month": m,
            "new": d["new"],
            "returning": d["returning"],
            "new_revenue": round(d["new_revenue"], 2),
            "returning_revenue": round(d["returning_revenue"], 2),
        })
        ytd_new += d["new"]
        ytd_returning += d["returning"]

    ytd_total = ytd_new + ytd_returning or 1
    result = {
        "monthly": monthly_list,
        "ytd_new": ytd_new,
        "ytd_returning": ytd_returning,
        "ytd_new_pct": round(ytd_new / ytd_total * 100, 1),
    }
    print(f"    YTD: {ytd_new} new, {ytd_returning} returning ({result['ytd_new_pct']}% new)")
    return result, prior_orders


def build_cohorts(ytd_orders, prior_orders):
    """Group customers by first-purchase month, show reorder rates.

    Uses both prior-year and YTD orders to build cohorts spanning
    the last 12+ months.
    """
    print("  [2B] Cohort summary...")
    all_orders = prior_orders + ytd_orders

    # customer_id -> list of order months
    cust_months = defaultdict(list)
    for o in all_orders:
        cid = o.get("customer_id", 0)
        if cid == 0:
            continue
        dc = o.get("date_created", "")
        if dc:
            cust_months[cid].append(dc[:7])

    # For each customer, determine first-purchase cohort month
    cohort_data = defaultdict(lambda: {"total": 0, "reordered": 0})
    for cid, months in cust_months.items():
        months_sorted = sorted(set(months))
        first_month = months_sorted[0]
        cohort_data[first_month]["total"] += 1
        # Reordered = purchased in more than one distinct month
        if len(months_sorted) > 1:
            cohort_data[first_month]["reordered"] += 1

    result = []
    for cohort in sorted(cohort_data.keys()):
        d = cohort_data[cohort]
        total = d["total"] or 1
        result.append({
            "cohort": cohort,
            "total": d["total"],
            "reordered": d["reordered"],
            "reorder_rate": round(d["reordered"] / total * 100, 1),
        })

    print(f"    {len(result)} cohorts built")
    return result


# ══════════════════════════════════════════════════════════════
# MAIN GENERATOR
# ══════════════════════════════════════════════════════════════

def generate_customers():
    """Generate customers.json with all customer analytics sections."""
    print("\n" + "=" * 60)
    print("  Customers Dashboard Data Generator")
    print(f"  Date: {TODAY_STR}  |  YTD from {YTD_START}")
    print("=" * 60)

    if not WC_CK or not WC_CS:
        print("  [SKIP] No WooCommerce credentials")
        return False

    # ── Pull YTD orders ─────────────────────────────────────
    print(f"\n  Pulling YTD orders ({YTD_START} to {TODAY_STR})...")
    ytd_orders = _pull_wc_orders_range(YTD_START, TODAY_STR)
    print(f"  {len(ytd_orders)} YTD orders fetched\n")

    if not ytd_orders:
        print("  [SKIP] No orders found for YTD period")
        return False

    # ── Section 1: Demographics & Behavior ──────────────────
    orders_by_state = build_orders_by_state(ytd_orders)
    orders_by_hour = build_orders_by_hour(ytd_orders)
    attribution = build_attribution(ytd_orders)
    sessions = build_sessions_before_buying(ytd_orders)

    # ── Section 2: New vs Returning + Cohorts ───────────────
    new_vs_returning, prior_orders = build_new_vs_returning(ytd_orders)
    cohorts = build_cohorts(ytd_orders, prior_orders)

    # ── Write JSON ──────────────────────────────────────────
    output = {
        "as_of": TODAY_STR,
        "orders_by_state": orders_by_state,
        "orders_by_hour": orders_by_hour,
        "attribution": attribution,
        "sessions_before_buying": sessions,
        "new_vs_returning": new_vs_returning,
        "cohorts": cohorts,
    }

    _write_json("customers.json", output)
    print(f"\n  [DONE] customers.json — {len(ytd_orders)} YTD + {len(prior_orders)} prior-year orders processed")
    return True


if __name__ == "__main__":
    import sys
    import os
    # --direct flag bypasses CF Worker proxy for local dev
    if "--direct" in sys.argv:
        CF_WORKER_URL = ""
        os.environ.pop("CF_WORKER_URL", None)
        print("  [INFO] --direct mode: bypassing CF Worker proxy")
    ok = generate_customers()
    if not ok:
        sys.exit(1)
