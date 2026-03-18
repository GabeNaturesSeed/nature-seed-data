#!/usr/bin/env python3
"""
ABC Product Classification — Last 14 Days
Nature's Seed | WooCommerce orders → SKU-level revenue ranking
A = top 80% of revenue  B = next 15%  C = bottom 5%
"""

import requests, time, json, os, base64
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# ── Credentials ───────────────────────────────────────────────────────────────
def _load_env():
    env = {}
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip().strip("'\"")] = v.strip().strip("'\"")
    for key in list(env.keys()):
        ov = os.environ.get(key)
        if ov is not None:
            env[key] = ov
    return env

ENV      = _load_env()
WC_CK    = ENV.get("WC_CK", "")
WC_CS    = ENV.get("WC_CS", "")
CF_URL   = ENV.get("CF_WORKER_URL", "")
CF_SEC   = ENV.get("CF_WORKER_SECRET", "")
BASE     = "https://naturesseed.com/wp-json/wc/v3"

def wc_get(path, params=None):
    params = dict(params or {})
    if CF_URL and CF_SEC:
        params["wc_path"] = path
        auth_str = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        headers = {"X-Proxy-Secret": CF_SEC, "Authorization": f"Basic {auth_str}"}
        r = requests.get(CF_URL, headers=headers, params=params, timeout=30)
    else:
        r = requests.get(f"{BASE}{path}", auth=(WC_CK, WC_CS), params=params, timeout=30)
    r.raise_for_status()
    return r.json(), r.headers

# ── Date range ────────────────────────────────────────────────────────────────
now       = datetime.now(timezone.utc)
start_dt  = now - timedelta(days=14)
after_str = start_dt.strftime("%Y-%m-%dT00:00:00")
print(f"Pulling orders from {start_dt.strftime('%Y-%m-%d')} → {now.strftime('%Y-%m-%d')}")
print("=" * 60)

# ── Pull all orders ───────────────────────────────────────────────────────────
all_orders = []
for status in ("completed", "processing"):
    page = 1
    while True:
        params = {
            "status": status,
            "after": after_str,
            "per_page": 100,
            "page": page,
            "orderby": "date",
            "order": "desc",
        }
        data, headers = wc_get("/orders", params)
        if not data:
            break
        all_orders.extend(data)
        total_pages = int(headers.get("X-WP-TotalPages", 1))
        print(f"  [{status}] page {page}/{total_pages} — {len(data)} orders")
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)

print(f"\nTotal orders pulled: {len(all_orders)}")

# ── Aggregate by SKU ──────────────────────────────────────────────────────────
sku_data = defaultdict(lambda: {
    "name": "", "sku": "", "qty": 0, "revenue": 0.0, "orders": 0, "product_id": 0
})

for order in all_orders:
    for item in order.get("line_items", []):
        sku  = item.get("sku") or item.get("variation_id") or str(item.get("product_id", "unknown"))
        name = item.get("name", "Unknown")
        qty  = int(item.get("quantity", 0))
        rev  = float(item.get("total", 0))
        pid  = item.get("product_id", 0)

        sku_data[sku]["name"]       = name
        sku_data[sku]["sku"]        = sku
        sku_data[sku]["qty"]        += qty
        sku_data[sku]["revenue"]    += rev
        sku_data[sku]["orders"]     += 1
        sku_data[sku]["product_id"] = pid

# ── Sort by revenue ───────────────────────────────────────────────────────────
rows = sorted(sku_data.values(), key=lambda x: x["revenue"], reverse=True)
total_rev = sum(r["revenue"] for r in rows)
total_qty = sum(r["qty"] for r in rows)

# ── Apply ABC classification ──────────────────────────────────────────────────
cumulative = 0.0
for r in rows:
    cumulative += r["revenue"]
    pct = cumulative / total_rev * 100
    if pct <= 80:
        r["class"] = "A"
    elif pct <= 95:
        r["class"] = "B"
    else:
        r["class"] = "C"
    r["rev_pct"]  = r["revenue"] / total_rev * 100
    r["daily_qty"] = round(r["qty"] / 14, 1)
    r["daily_rev"] = round(r["revenue"] / 14, 2)

# ── Print report ──────────────────────────────────────────────────────────────
def section(cls, label):
    subset = [r for r in rows if r["class"] == cls]
    cls_rev = sum(r["revenue"] for r in subset)
    cls_qty = sum(r["qty"] for r in subset)
    print(f"\n{'='*80}")
    print(f"  CLASS {cls} — {label}")
    print(f"  {len(subset)} SKUs | ${cls_rev:,.2f} revenue ({cls_rev/total_rev*100:.1f}%) | {cls_qty} units")
    print(f"{'='*80}")
    print(f"  {'SKU':<30} {'Product':<42} {'14d Qty':>7} {'14d Rev':>10} {'$/day':>8} {'u/day':>6}")
    print(f"  {'-'*30} {'-'*42} {'-'*7} {'-'*10} {'-'*8} {'-'*6}")
    for r in subset:
        name_trunc = r["name"][:41]
        sku_trunc  = str(r["sku"])[:29]
        print(f"  {sku_trunc:<30} {name_trunc:<42} {r['qty']:>7} ${r['revenue']:>9,.2f} ${r['daily_rev']:>7,.2f} {r['daily_qty']:>6.1f}")

section("A", "HIGH VALUE  — top 80% of revenue")
section("B", "MID VALUE   — next 15% of revenue")
section("C", "LONG TAIL   — bottom 5% of revenue")

# ── Summary stats ─────────────────────────────────────────────────────────────
a = [r for r in rows if r["class"] == "A"]
b = [r for r in rows if r["class"] == "B"]
c = [r for r in rows if r["class"] == "C"]

print(f"\n{'='*80}")
print("  SUMMARY")
print(f"{'='*80}")
print(f"  Period        : {start_dt.strftime('%b %d')} – {now.strftime('%b %d, %Y')} (14 days)")
print(f"  Total SKUs    : {len(rows)}")
print(f"  Total Revenue : ${total_rev:,.2f}  (${total_rev/14:,.2f}/day avg)")
print(f"  Total Units   : {total_qty}  ({total_qty/14:.1f} units/day)")
print(f"  Class A       : {len(a)} SKUs ({len(a)/len(rows)*100:.1f}% of catalog) → {sum(r['revenue'] for r in a)/total_rev*100:.1f}% of revenue")
print(f"  Class B       : {len(b)} SKUs ({len(b)/len(rows)*100:.1f}% of catalog) → {sum(r['revenue'] for r in b)/total_rev*100:.1f}% of revenue")
print(f"  Class C       : {len(c)} SKUs ({len(c)/len(rows)*100:.1f}% of catalog) → {sum(r['revenue'] for r in c)/total_rev*100:.1f}% of revenue")

# ── Save JSON ─────────────────────────────────────────────────────────────────
out = Path(__file__).parent / "abc_analysis_results.json"
with open(out, "w") as f:
    json.dump({
        "generated": now.isoformat(),
        "period_days": 14,
        "total_revenue": total_rev,
        "total_units": total_qty,
        "skus": rows
    }, f, indent=2)
print(f"\n  JSON saved → {out.name}")
