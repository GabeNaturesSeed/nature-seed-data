#!/usr/bin/env python3
"""
Nature's Seed — Website Health Dashboard Data Generator
Generates docs/data/health.json with uptime, order velocity, search health,
and server metrics.

Sources:
  A. Supabase website_health table — uptime data
  B. WooCommerce (via CF Worker proxy) — order velocity
  C. Algolia Analytics API — search health
  D. WP Engine API — server health

Usage:
  python3 infrastructure/dashboard/generate_health.py
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

ALGOLIA_APP_ID = env_vars.get("ALGOLIA_APP_ID", "")
ALGOLIA_ADMIN_KEY = env_vars.get("ALGOLIA_ADMIN_API_KEY", "")

WPENGINE_USER = env_vars.get("WPENGINE_API_USER", "")
WPENGINE_PASS = env_vars.get("WPENGINE_API_PASS", "")

TODAY = date.today()
TODAY_STR = str(TODAY)
NOW_UTC = datetime.now(timezone.utc)

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _write_json(filename, data):
    path = OUT_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  [OK] Wrote {path.name}")


def _supabase_get(path, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    p = dict(params or {})
    if "limit" not in p:
        p["limit"] = 10000
    resp = requests.get(url, headers=headers, params=p, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _wc_get(path, params=None):
    """GET from WooCommerce REST API, routing through CF Worker if configured."""
    if CF_WORKER_URL:
        p = {"wc_path": path, **(params or {})}
        auth_str = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        headers = {"X-Proxy-Secret": CF_WORKER_SECRET, "Authorization": f"Basic {auth_str}"}
        resp = requests.get(CF_WORKER_URL, headers=headers, params=p, timeout=30)
    else:
        resp = requests.get(f"{WC_BASE}{path}", auth=(WC_CK, WC_CS), params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp


# ══════════════════════════════════════════════════════════════
# SECTION A: UPTIME (from Supabase website_health)
# ══════════════════════════════════════════════════════════════

def pull_uptime():
    """Pull uptime data from Supabase website_health table."""
    print("\n[A] Uptime data...")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("  [SKIP] No Supabase credentials")
        return {
            "current_status": [],
            "uptime_24h": None,
            "uptime_7d": None,
            "incidents": [],
        }

    ts_24h = (NOW_UTC - timedelta(hours=24)).isoformat()
    ts_7d = (NOW_UTC - timedelta(days=7)).isoformat()

    # Pull last 7 days of data
    try:
        rows = _supabase_get("website_health", {
            "check_timestamp": f"gte.{ts_7d}",
            "order": "check_timestamp.desc",
            "limit": 10000,
        })
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print("  [WARN] website_health table not found — run website_health.sql first")
        else:
            print(f"  [WARN] Supabase error: {e}")
        return {
            "current_status": [],
            "uptime_24h": None,
            "uptime_7d": None,
            "incidents": [],
            "note": "Table not yet created. Run infrastructure/pipeline/website_health.sql in Supabase.",
        }
    print(f"  Fetched {len(rows)} health check rows (7d)")

    if not rows:
        return {
            "current_status": [],
            "uptime_24h": None,
            "uptime_7d": None,
            "incidents": [],
        }

    # Current status: latest check per URL
    latest_by_url = {}
    for r in rows:
        url = r["url"]
        if url not in latest_by_url:
            latest_by_url[url] = {
                "url": url,
                "is_up": r["is_up"],
                "status_code": r["status_code"],
                "response_time_ms": r["response_time_ms"],
                "last_checked": r["check_timestamp"],
                "error_message": r.get("error_message"),
            }
    current_status = list(latest_by_url.values())

    # Uptime percentages
    rows_24h = [r for r in rows if r["check_timestamp"] >= ts_24h]
    up_24h = sum(1 for r in rows_24h if r["is_up"])
    uptime_24h = round(up_24h / len(rows_24h) * 100, 1) if rows_24h else None

    up_7d = sum(1 for r in rows if r["is_up"])
    uptime_7d = round(up_7d / len(rows) * 100, 1) if rows else None

    print(f"  24h uptime: {uptime_24h}% ({up_24h}/{len(rows_24h)} checks)")
    print(f"  7d uptime:  {uptime_7d}% ({up_7d}/{len(rows)} checks)")

    # Incidents: downtime events in last 7 days
    incidents = []
    down_rows = [r for r in rows if not r["is_up"]]
    # Group consecutive down checks by URL to estimate duration
    down_by_url = defaultdict(list)
    for r in down_rows:
        down_by_url[r["url"]].append(r)

    for url, dr_list in down_by_url.items():
        # Sort by timestamp ascending
        dr_list.sort(key=lambda x: x["check_timestamp"])
        for dr in dr_list:
            incidents.append({
                "url": url,
                "timestamp": dr["check_timestamp"],
                "status_code": dr["status_code"],
                "error_message": dr.get("error_message"),
                "duration_min": 30,  # Each check is 30 min apart, so min duration
            })

    if incidents:
        print(f"  {len(incidents)} downtime incidents found")
    else:
        print("  No downtime incidents")

    return {
        "current_status": current_status,
        "uptime_24h": uptime_24h,
        "uptime_7d": uptime_7d,
        "incidents": incidents[:50],  # Cap at 50 incidents
    }


# ══════════════════════════════════════════════════════════════
# SECTION B: ORDER VELOCITY (from WooCommerce)
# ══════════════════════════════════════════════════════════════

def pull_order_velocity():
    """Pull today's orders and same-day-last-week, bucket by hour."""
    print("\n[B] Order velocity...")

    if not WC_CK or not WC_CS:
        print("  [SKIP] No WooCommerce credentials")
        return {
            "today_label": TODAY.strftime("%A"),
            "hourly": [],
            "today_total": 0,
            "last_week_total": 0,
        }

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_label = day_names[TODAY.weekday()]
    last_week_date = TODAY - timedelta(days=7)

    def fetch_orders_for_date(d):
        """Fetch all orders for a specific date."""
        all_orders = []
        page = 1
        after = f"{d}T00:00:00"
        before = f"{d}T23:59:59"
        while True:
            params = {
                "after": after,
                "before": before,
                "status": "completed,processing",
                "per_page": 100,
                "page": page,
            }
            try:
                resp = _wc_get("/orders", params)
                orders = resp.json()
            except Exception as e:
                print(f"  [WARN] WC API error page {page}: {e}")
                break
            if not orders:
                break
            all_orders.extend(orders)
            page += 1
            time.sleep(0.3)
        return all_orders

    # Today's orders
    print(f"  Fetching today's orders ({TODAY_STR})...")
    today_orders = fetch_orders_for_date(TODAY)
    print(f"  Got {len(today_orders)} orders today")

    # Last week same day
    print(f"  Fetching last week orders ({last_week_date})...")
    lw_orders = fetch_orders_for_date(last_week_date)
    print(f"  Got {len(lw_orders)} orders last week same day")

    # Bucket by hour
    def bucket_by_hour(orders):
        buckets = defaultdict(int)
        for o in orders:
            # date_created is in site timezone
            dc = o.get("date_created", "")
            if dc and "T" in dc:
                try:
                    hour = int(dc.split("T")[1].split(":")[0])
                    buckets[hour] += 1
                except (ValueError, IndexError):
                    pass
        return buckets

    today_buckets = bucket_by_hour(today_orders)
    lw_buckets = bucket_by_hour(lw_orders)

    hourly = []
    for h in range(24):
        hourly.append({
            "hour": h,
            "today": today_buckets.get(h, 0),
            "last_week": lw_buckets.get(h, 0),
        })

    return {
        "today_label": today_label,
        "hourly": hourly,
        "today_total": len(today_orders),
        "last_week_total": len(lw_orders),
    }


# ══════════════════════════════════════════════════════════════
# SECTION C: SEARCH HEALTH (from Algolia Analytics)
# ══════════════════════════════════════════════════════════════

def pull_search_health():
    """Pull search analytics from Algolia."""
    print("\n[C] Search health...")

    if not ALGOLIA_APP_ID or not ALGOLIA_ADMIN_KEY:
        print("  [SKIP] No Algolia credentials")
        return {
            "total_searches_24h": None,
            "no_result_rate": None,
            "no_result_searches": None,
            "top_searches": [],
            "top_no_results": [],
        }

    base_url = "https://analytics.us.algolia.com/2"
    headers = {
        "X-Algolia-API-Key": ALGOLIA_ADMIN_KEY,
        "X-Algolia-Application-Id": ALGOLIA_APP_ID,
    }
    index = "wp_prod_posts_product"
    end_date = TODAY_STR
    start_date = str(TODAY - timedelta(days=1))

    result = {
        "total_searches_24h": 0,
        "no_result_rate": 0,
        "no_result_searches": 0,
        "top_searches": [],
        "top_no_results": [],
    }

    # Total searches
    try:
        resp = requests.get(
            f"{base_url}/searches",
            headers=headers,
            params={
                "index": index,
                "startDate": start_date,
                "endDate": end_date,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        searches = data.get("searches", [])
        total = sum(s.get("count", 0) for s in searches) if searches else data.get("count", 0)
        result["total_searches_24h"] = total
        print(f"  Total searches (24h): {total}")
    except Exception as e:
        print(f"  [WARN] Algolia searches error: {e}")

    # Top searches
    try:
        resp = requests.get(
            f"{base_url}/searches",
            headers=headers,
            params={
                "index": index,
                "startDate": start_date,
                "endDate": end_date,
                "limit": 10,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        top = []
        for s in data.get("searches", [])[:10]:
            top.append({"query": s.get("search", ""), "count": s.get("count", 0)})
        # Sort by count descending
        top.sort(key=lambda x: x["count"], reverse=True)
        result["top_searches"] = top
        print(f"  Top searches: {len(top)} queries")
    except Exception as e:
        print(f"  [WARN] Algolia top searches error: {e}")

    # No-result searches
    try:
        resp = requests.get(
            f"{base_url}/searches/noResults",
            headers=headers,
            params={
                "index": index,
                "startDate": start_date,
                "endDate": end_date,
                "limit": 10,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        no_results = []
        for s in data.get("searches", [])[:10]:
            no_results.append({"query": s.get("search", ""), "count": s.get("count", 0)})
        no_result_count = sum(s.get("count", 0) for s in data.get("searches", []))
        result["top_no_results"] = no_results
        result["no_result_searches"] = no_result_count
        if result["total_searches_24h"] and result["total_searches_24h"] > 0:
            result["no_result_rate"] = round(no_result_count / result["total_searches_24h"] * 100, 1)
        print(f"  No-result searches: {no_result_count} ({result['no_result_rate']}%)")
    except Exception as e:
        print(f"  [WARN] Algolia no-results error: {e}")

    return result


# ══════════════════════════════════════════════════════════════
# SECTION D: WP ENGINE SERVER HEALTH
# ══════════════════════════════════════════════════════════════

def pull_server_health():
    """Pull server info from WP Engine API."""
    print("\n[D] Server health...")

    if not WPENGINE_USER or not WPENGINE_PASS:
        print("  [SKIP] No WP Engine credentials")
        return {
            "install_name": "naturesseed",
            "php_version": None,
            "wp_version": None,
            "status": "unknown",
            "note": "No WP Engine API credentials configured",
        }

    headers = {"Content-Type": "application/json"}
    auth = (WPENGINE_USER, WPENGINE_PASS)

    result = {
        "install_name": "naturesseed",
        "php_version": None,
        "wp_version": None,
        "status": "unknown",
    }

    # Get installs list
    try:
        resp = requests.get(
            "https://api.wpengineapi.com/v1/installs",
            auth=auth,
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        installs = data.get("results", data) if isinstance(data, dict) else data
        if isinstance(installs, list):
            # Find our install
            our_install = None
            for inst in installs:
                name = inst.get("name", "").lower()
                if "naturesseed" in name or "natures" in name:
                    our_install = inst
                    break
            if not our_install and installs:
                our_install = installs[0]  # Take first if only one

            if our_install:
                result["install_name"] = our_install.get("name", "naturesseed")
                result["php_version"] = our_install.get("php_version")
                result["wp_version"] = our_install.get("coreVersion") or our_install.get("wp_version")
                result["status"] = our_install.get("status", "active")
                result["environment"] = our_install.get("environment", "production")
                install_id = our_install.get("id")

                # Try to get stats if install_id is available
                if install_id:
                    try:
                        stats_resp = requests.get(
                            f"https://api.wpengineapi.com/v1/installs/{install_id}",
                            auth=auth,
                            headers=headers,
                            timeout=15,
                        )
                        if stats_resp.ok:
                            stats = stats_resp.json()
                            if stats.get("php_version"):
                                result["php_version"] = stats["php_version"]
                            if stats.get("coreVersion"):
                                result["wp_version"] = stats["coreVersion"]
                    except Exception:
                        pass

                print(f"  Install: {result['install_name']}")
                print(f"  PHP: {result['php_version']}, WP: {result['wp_version']}")
                print(f"  Status: {result['status']}")
            else:
                print("  [WARN] No matching install found")
        else:
            print(f"  [WARN] Unexpected API response format")
    except requests.exceptions.HTTPError as e:
        print(f"  [WARN] WP Engine API HTTP error: {e.response.status_code}")
        result["note"] = f"API returned {e.response.status_code}"
    except Exception as e:
        print(f"  [WARN] WP Engine API error: {e}")
        result["note"] = str(e)[:200]

    return result


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print(f"Nature's Seed — Health Dashboard Generator ({TODAY_STR})")
    print("=" * 60)

    health = {"as_of": TODAY_STR}

    health["uptime"] = pull_uptime()
    health["order_velocity"] = pull_order_velocity()
    health["search_health"] = pull_search_health()
    health["server"] = pull_server_health()

    _write_json("health.json", health)
    print(f"\n{'=' * 60}")
    print("Done. Output: docs/data/health.json")


if __name__ == "__main__":
    main()
