#!/usr/bin/env python3
"""
Backfill WooCommerce daily sales history into Supabase daily_sales table.

Pulls WC orders month-by-month for the specified date range, aggregates to
daily {revenue, orders, units}, and upserts into daily_sales (channel=woocommerce).

Run once to seed historical data. Safe to re-run — upsert is idempotent.

Usage:
    python infrastructure/dashboard/backfill_wc_history.py
    python infrastructure/dashboard/backfill_wc_history.py --start 2022-01-01 --end 2024-12-31
    python infrastructure/dashboard/backfill_wc_history.py --start 2023-01-01  # one year only
"""

import argparse
import base64
import json
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent.parent

env_vars = {}
with open(ROOT / ".env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip("'\"")

SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")
WC_CK = env_vars.get("WC_CK", "")
WC_CS = env_vars.get("WC_CS", "")
WC_BASE = env_vars.get("WC_BASE_URL", "https://naturesseed.com/wp-json/wc/v3")
CF_WORKER_URL = env_vars.get("CF_WORKER_URL", "")
CF_WORKER_SECRET = env_vars.get("CF_WORKER_SECRET", "")


def _wc_get(path, params=None):
    if CF_WORKER_URL:
        p = {"wc_path": path, **(params or {})}
        auth = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        headers = {"X-Proxy-Secret": CF_WORKER_SECRET, "Authorization": f"Basic {auth}"}
        resp = requests.get(CF_WORKER_URL, headers=headers, params=p, timeout=60)
    else:
        resp = requests.get(f"{WC_BASE}{path}", auth=(WC_CK, WC_CS), params=params or {}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def pull_month(year: int, month: int) -> dict:
    """Pull all completed/processing WC orders for one calendar month.
    Returns {date_str: {revenue, orders, units}}.
    """
    # Last day of month
    if month == 12:
        last_day = date(year, 12, 31)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    start = date(year, month, 1)
    end = last_day

    daily = defaultdict(lambda: {"revenue": 0.0, "orders": 0, "units": 0})
    page = 1
    total_orders = 0

    while True:
        params = {
            "after": f"{start}T00:00:00",
            "before": f"{end}T23:59:59",
            "status": "completed,processing,on-hold",
            "per_page": 100,
            "page": page,
        }
        try:
            orders = _wc_get("/orders", params)
        except Exception as e:
            print(f"    [WARN] page {page} failed: {e}")
            break

        if not orders:
            break

        for order in orders:
            d = order.get("date_created", "")[:10]
            if d:
                daily[d]["revenue"] += float(order.get("total", 0))
                daily[d]["orders"] += 1
                daily[d]["units"] += sum(int(i.get("quantity", 0)) for i in order.get("line_items", []))
        total_orders += len(orders)
        page += 1
        time.sleep(0.25)  # stay under WC rate limit

    print(f"    {year}-{month:02d}: {total_orders} orders → {len(daily)} days")
    return dict(daily)


def supabase_upsert(rows: list) -> None:
    url = f"{SUPABASE_URL}/rest/v1/daily_sales?on_conflict=report_date,channel"
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    resp = requests.post(url, headers=headers, json=rows, timeout=30)
    if resp.status_code not in (200, 201, 204):
        print(f"    [ERR] Upsert failed: {resp.status_code} {resp.text[:200]}")
    else:
        print(f"    [OK] Upserted {len(rows)} rows")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2022-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2024-12-31", help="End date YYYY-MM-DD (inclusive)")
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    print(f"Backfilling WC daily sales: {start} → {end}")
    print(f"Supabase: {SUPABASE_URL}")

    # Walk month by month
    cursor = date(start.year, start.month, 1)
    total_rows = 0

    while cursor <= end:
        year, month = cursor.year, cursor.month
        print(f"\n  Pulling {year}-{month:02d}...")

        daily = pull_month(year, month)

        if daily:
            rows = [
                {
                    "report_date": d,
                    "channel": "woocommerce",
                    "revenue": round(v["revenue"], 2),
                    "orders": v["orders"],
                    "units": v["units"],
                }
                for d, v in sorted(daily.items())
            ]
            supabase_upsert(rows)
            total_rows += len(rows)

        # Advance to next month
        if month == 12:
            cursor = date(year + 1, 1, 1)
        else:
            cursor = date(year, month + 1, 1)

    print(f"\nDone. {total_rows} daily rows upserted into daily_sales.")


if __name__ == "__main__":
    main()
