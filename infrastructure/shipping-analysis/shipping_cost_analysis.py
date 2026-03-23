#!/usr/bin/env python3
"""
Nature's Seed — Shipping Cost Analysis (Shippo)

Pulls all GROUND shipments from the last 60 days, deduplicates by tracking
number, and produces weekly cost trends with carrier breakdown.

Key Shippo API notes:
  - No date filtering — must paginate all transactions and filter locally
  - Rate details (cost, weight, zone) require separate /rates/{id} calls
  - Deduplicate by tracking number to handle voided/recreated labels
"""

import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date, timedelta
from pathlib import Path

import requests

# Force unbuffered output
def log(msg):
    print(msg, flush=True)

# ══════════════════════════════════════════════════════════════
# ENV SETUP
# ══════════════════════════════════════════════════════════════

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

SHIPPO_API_KEY = env_vars.get("SHIPPO_API_KEY", "")
if not SHIPPO_API_KEY:
    raise SystemExit("ERROR: SHIPPO_API_KEY not found in .env")

HEADERS = {"Authorization": f"ShippoToken {SHIPPO_API_KEY}"}
LOOKBACK_DAYS = 60
CUTOFF_DATE = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()

# Ground service keywords (case-insensitive matching)
GROUND_KEYWORDS = [
    "ground", "parcel select", "ups surepost", "smartpost",
    "fedex home", "ups ground", "usps parcel", "retail ground",
    "ground advantage", "priority mail"  # USPS Ground Advantage replaced retail ground
]

OUTPUT_DIR = Path(__file__).resolve().parent


def is_ground_service(service_name: str) -> bool:
    """Check if a service level name is a ground service."""
    svc = (service_name or "").lower()
    return any(kw in svc for kw in GROUND_KEYWORDS)


def iso_to_week(date_str: str) -> str:
    """Convert YYYY-MM-DD to ISO week label like '2026-W08'."""
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def pull_all_transactions():
    """Paginate all Shippo transactions back to CUTOFF_DATE."""
    log(f"Pulling Shippo transactions since {CUTOFF_DATE} ...")

    all_txns = []
    url = "https://api.goshippo.com/transactions/"
    params = {"results": 200}
    pages = 0
    done = False

    while url and not done:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code != 200:
            log(f"  [WARN] Shippo returned {resp.status_code}: {resp.text[:200]}")
            break

        data = resp.json()
        pages += 1

        for txn in data.get("results", []):
            txn_date = (txn.get("object_created") or "")[:10]

            if txn_date < CUTOFF_DATE:
                done = True
                break

            if txn.get("status") == "SUCCESS":
                all_txns.append(txn)

        if pages % 5 == 0:
            log(f"  ... page {pages}, {len(all_txns)} SUCCESS txns so far")

        url = data.get("next")
        params = {}  # next URL has params embedded
        time.sleep(0.3)

    log(f"  Done: {pages} pages, {len(all_txns)} SUCCESS transactions")
    return all_txns


def deduplicate(txns):
    """Keep only the latest transaction per tracking number."""
    by_tracking = {}
    no_tracking = []

    for txn in txns:
        tracking = txn.get("tracking_number", "")
        if not tracking:
            no_tracking.append(txn)
            continue

        existing = by_tracking.get(tracking)
        if existing is None:
            by_tracking[tracking] = txn
        else:
            if (txn.get("object_created") or "") > (existing.get("object_created") or ""):
                by_tracking[tracking] = txn

    deduped = list(by_tracking.values()) + no_tracking
    removed = len(txns) - len(deduped)
    if removed:
        log(f"  Deduplicated: removed {removed} voided/duplicate labels")
    return deduped


def _fetch_single_rate(rate_id):
    """Fetch a single rate from Shippo API. Returns (rate_id, rate_dict or None)."""
    try:
        resp = requests.get(
            f"https://api.goshippo.com/rates/{rate_id}",
            headers=HEADERS, timeout=15
        )
        if resp.status_code == 200:
            return (rate_id, resp.json())
        else:
            return (rate_id, None)
    except Exception:
        return (rate_id, None)


def fetch_rate_details(txns):
    """Fetch rate details using concurrent threads for speed."""
    log(f"Fetching rate details for {len(txns)} transactions ...")

    # Collect unique rate IDs
    rate_ids_needed = set()
    skipped_no_rate = 0
    for txn in txns:
        rate_id = txn.get("rate", "")
        if rate_id:
            rate_ids_needed.add(rate_id)
        else:
            skipped_no_rate += 1

    log(f"  Unique rate IDs to fetch: {len(rate_ids_needed)}")
    if skipped_no_rate:
        log(f"  Skipped {skipped_no_rate} txns with no rate ID")

    # Fetch rates concurrently (10 threads)
    rate_cache = {}
    fetched = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_single_rate, rid): rid for rid in rate_ids_needed}
        for future in as_completed(futures):
            rate_id, rate_data = future.result()
            rate_cache[rate_id] = rate_data
            fetched += 1
            if fetched % 100 == 0:
                log(f"  ... {fetched}/{len(rate_ids_needed)} rates fetched")

    log(f"  All {fetched} rates fetched")

    # Enrich transactions
    enriched = []
    for txn in txns:
        rate_id = txn.get("rate", "")
        if not rate_id:
            continue

        rate = rate_cache.get(rate_id)
        if rate is None:
            continue

        txn_date = (txn.get("object_created") or "")[:10]
        carrier = rate.get("provider", "") or txn.get("provider", "") or "Unknown"
        service = rate.get("servicelevel", {}).get("name", "") or ""
        cost = float(rate.get("amount", 0) or 0)
        zone = rate.get("zone", None)

        # Weight from rate's parcel (may be dict or string URL)
        weight = 0
        rate_parcel = rate.get("parcel")
        if isinstance(rate_parcel, dict):
            try:
                weight = float(rate_parcel.get("weight", 0) or 0)
            except (TypeError, ValueError):
                weight = 0

        enriched.append({
            "date": txn_date,
            "tracking_number": txn.get("tracking_number", ""),
            "carrier": carrier,
            "service": service,
            "cost": cost,
            "weight_lbs": weight,
            "zone": zone,
        })

    log(f"  Enriched {len(enriched)} transactions with rate data")
    return enriched


def filter_ground(enriched):
    """Filter to ground services only."""
    ground = [r for r in enriched if is_ground_service(r["service"])]
    log(f"  Ground shipments: {len(ground)} / {len(enriched)} total")

    # Show all service levels for debugging
    svc_counts = defaultdict(int)
    for r in enriched:
        svc_counts[r["service"]] += 1
    log("\n  All service levels found:")
    for svc, cnt in sorted(svc_counts.items(), key=lambda x: -x[1]):
        marker = " <-- GROUND" if is_ground_service(svc) else ""
        log(f"    {svc}: {cnt}{marker}")

    return ground


def analyze_and_report(records):
    """Compute aggregates and print a clear report."""
    if not records:
        log("\nNo ground shipments found in the last 60 days.")
        return

    # ── Overall Averages ──
    total_cost = sum(r["cost"] for r in records)
    total_weight = sum(r["weight_lbs"] for r in records)
    total_orders = len(records)
    avg_cost = total_cost / total_orders
    avg_cost_per_lb = total_cost / total_weight if total_weight > 0 else 0

    log("\n" + "=" * 70)
    log("  SHIPPING COST ANALYSIS -- GROUND SHIPMENTS (Last 60 Days)")
    log("=" * 70)
    log(f"\n  Total shipments:     {total_orders}")
    log(f"  Total shipping cost: ${total_cost:,.2f}")
    log(f"  Total weight:        {total_weight:,.1f} lbs")
    log(f"\n  Avg cost / order:    ${avg_cost:,.2f}")
    log(f"  Avg cost / lb:       ${avg_cost_per_lb:,.2f}")

    # ── Zone breakdown (cost per mile proxy) ──
    zone_data = defaultdict(lambda: {"cost": 0, "count": 0, "weight": 0})
    has_zones = False
    for r in records:
        z = r.get("zone")
        if z:
            has_zones = True
            zone_data[z]["cost"] += r["cost"]
            zone_data[z]["count"] += 1
            zone_data[z]["weight"] += r["weight_lbs"]

    if has_zones:
        log(f"\n  ZONE BREAKDOWN (proxy for distance)")
        log(f"  {'Zone':<8} {'Orders':<8} {'Avg Cost':<12} {'Avg $/lb':<12} {'Total Cost':<12}")
        log("  " + "-" * 52)
        for z in sorted(zone_data.keys()):
            d = zone_data[z]
            zc = d["cost"] / d["count"] if d["count"] else 0
            zw = d["cost"] / d["weight"] if d["weight"] else 0
            log(f"  {z:<8} {d['count']:<8} ${zc:<10,.2f} ${zw:<10,.2f} ${d['cost']:<10,.2f}")
    else:
        log("\n  (No zone data available -- cost per mile cannot be computed)")

    # ── Carrier Breakdown ──
    carrier_data = defaultdict(lambda: {"cost": 0, "count": 0, "weight": 0})
    for r in records:
        c = r["carrier"]
        carrier_data[c]["cost"] += r["cost"]
        carrier_data[c]["count"] += 1
        carrier_data[c]["weight"] += r["weight_lbs"]

    log(f"\n  CARRIER BREAKDOWN")
    log(f"  {'Carrier':<20} {'Orders':<8} {'Avg Cost':<12} {'Avg $/lb':<12} {'Total Cost':<12}")
    log("  " + "-" * 64)
    for c in sorted(carrier_data.keys(), key=lambda x: -carrier_data[x]["cost"]):
        d = carrier_data[c]
        cc = d["cost"] / d["count"] if d["count"] else 0
        cw = d["cost"] / d["weight"] if d["weight"] else 0
        log(f"  {c:<20} {d['count']:<8} ${cc:<10,.2f} ${cw:<10,.2f} ${d['cost']:<10,.2f}")

    # ── Weekly Trends ──
    weekly = defaultdict(lambda: {"cost": 0, "count": 0, "weight": 0})
    for r in records:
        wk = iso_to_week(r["date"])
        weekly[wk]["cost"] += r["cost"]
        weekly[wk]["count"] += 1
        weekly[wk]["weight"] += r["weight_lbs"]

    weeks_sorted = sorted(weekly.keys())
    log(f"\n  WEEKLY TRENDS")
    log(f"  {'Week':<12} {'Orders':<8} {'Total Cost':<14} {'Avg/Order':<12} {'Avg/lb':<12}")
    log("  " + "-" * 58)

    avg_per_order_list = []
    for wk in weeks_sorted:
        d = weekly[wk]
        wo = d["cost"] / d["count"] if d["count"] else 0
        ww = d["cost"] / d["weight"] if d["weight"] else 0
        avg_per_order_list.append((wk, wo, d["count"]))
        log(f"  {wk:<12} {d['count']:<8} ${d['cost']:<12,.2f} ${wo:<10,.2f} ${ww:<10,.2f}")

    # ── Detect inflection points ──
    log(f"\n  INFLECTION ANALYSIS")
    if len(avg_per_order_list) >= 3:
        changes = []
        for i in range(1, len(avg_per_order_list)):
            prev_wk, prev_avg, prev_cnt = avg_per_order_list[i - 1]
            curr_wk, curr_avg, curr_cnt = avg_per_order_list[i]
            if prev_avg > 0 and prev_cnt >= 3 and curr_cnt >= 3:
                pct_change = ((curr_avg - prev_avg) / prev_avg) * 100
                changes.append((curr_wk, pct_change, prev_avg, curr_avg))

        significant = [c for c in changes if abs(c[1]) > 10]
        if significant:
            log("  Weeks with >10% avg cost/order change vs prior week:")
            for wk, pct, prev, curr in significant:
                direction = "UP" if pct > 0 else "DOWN"
                log(f"    {wk}: {direction} {abs(pct):.1f}% (${prev:.2f} -> ${curr:.2f})")
        else:
            log("  No single week showed >10% jump in avg cost/order vs prior week.")

        # Overall trend: first half vs second half
        first_half = avg_per_order_list[:len(avg_per_order_list) // 2]
        second_half = avg_per_order_list[len(avg_per_order_list) // 2:]
        first_valid = [a for _, a, c in first_half if c >= 2]
        second_valid = [a for _, a, c in second_half if c >= 2]
        first_avg = sum(first_valid) / len(first_valid) if first_valid else 0
        second_avg = sum(second_valid) / len(second_valid) if second_valid else 0
        if first_avg > 0:
            overall_pct = ((second_avg - first_avg) / first_avg) * 100
            log(f"\n  Overall trend (first half vs second half):")
            log(f"    First half avg/order:  ${first_avg:.2f}")
            log(f"    Second half avg/order: ${second_avg:.2f}")
            log(f"    Change: {overall_pct:+.1f}%")
    else:
        log("  Not enough weeks for trend analysis.")

    # ── Weekly by Carrier ──
    weekly_carrier = defaultdict(lambda: defaultdict(lambda: {"cost": 0, "count": 0}))
    for r in records:
        wk = iso_to_week(r["date"])
        c = r["carrier"]
        weekly_carrier[wk][c]["cost"] += r["cost"]
        weekly_carrier[wk][c]["count"] += 1

    all_carriers = sorted(set(r["carrier"] for r in records))
    if len(all_carriers) > 1:
        log(f"\n  WEEKLY AVG COST/ORDER BY CARRIER")
        hdr = f"  {'Week':<12}" + "".join(f"{c:<18}" for c in all_carriers)
        log(hdr)
        log("  " + "-" * (10 + 18 * len(all_carriers)))
        for wk in weeks_sorted:
            row = f"  {wk:<12}"
            for c in all_carriers:
                d = weekly_carrier[wk].get(c, {"cost": 0, "count": 0})
                if d["count"]:
                    row += f"${d['cost']/d['count']:<16,.2f}"
                else:
                    row += f"{'--':<18}"
            log(row)

    log("\n" + "=" * 70)


def save_to_json(records):
    """Save raw enriched data + summary to JSON for dashboard."""
    output = {
        "generated_at": datetime.now().isoformat(),
        "lookback_days": LOOKBACK_DAYS,
        "cutoff_date": CUTOFF_DATE,
        "total_records": len(records),
        "records": records,
    }

    outpath = OUTPUT_DIR / "shipping_ground_analysis.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=str)
    log(f"\nRaw data saved to {outpath}")


def main():
    # 1. Pull all transactions
    txns = pull_all_transactions()

    # 2. Deduplicate
    txns = deduplicate(txns)

    # 3. Fetch rate details concurrently
    enriched = fetch_rate_details(txns)

    # 4. Filter to ground only
    ground = filter_ground(enriched)

    # 5. Analyze and report
    analyze_and_report(ground)

    # 6. Save raw data
    save_to_json(ground)


if __name__ == "__main__":
    main()
