#!/usr/bin/env python3
"""
ABC Product Classification — Last 14 Days
Nature's Seed | WooCommerce orders → parent-SKU revenue ranking
Variants are grouped under their parent product.
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
        r = requests.get(CF_URL, headers=headers, params=params, timeout=60)
    else:
        r = requests.get(f"{BASE}{path}", auth=(WC_CK, WC_CS), params=params, timeout=60)
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

# ── Build parent product map (product_id → {sku, name}) ──────────────────────
print("\nBuilding parent product map...")
product_ids = set()
for order in all_orders:
    for item in order.get("line_items", []):
        pid = item.get("product_id")
        if pid:
            product_ids.add(pid)

parent_map = {}  # product_id → {sku, name, date_created}
ids_list = list(product_ids)
for i in range(0, len(ids_list), 100):
    chunk = ids_list[i:i + 100]
    data, _ = wc_get("/products", {"include": ",".join(str(x) for x in chunk), "per_page": 100})
    for p in data:
        parent_map[p["id"]] = {
            "sku": p.get("sku", ""),
            "name": p.get("name", ""),
            "date_created": (p.get("date_created") or "")[:10],
        }
    time.sleep(0.25)
print(f"  Mapped {len(parent_map)} parent products")

# ── Aggregate by parent product_id, tracking variants ────────────────────────
parent_data = defaultdict(lambda: {
    "parent_sku": "", "name": "", "product_id": 0,
    "qty": 0, "revenue": 0.0, "orders": 0,
    "date_created": "",
    "variants": defaultdict(lambda: {"sku": "", "name": "", "qty": 0, "revenue": 0.0, "orders": 0}),
})

for order in all_orders:
    for item in order.get("line_items", []):
        pid  = item.get("product_id", 0)
        sku  = (item.get("sku") or "").strip()
        name = item.get("name", "Unknown")
        qty  = int(item.get("quantity", 0))
        rev  = float(item.get("total", 0))

        info = parent_map.get(pid, {})
        parent_data[pid]["parent_sku"]    = info.get("sku") or str(pid)
        parent_data[pid]["name"]          = info.get("name") or name
        parent_data[pid]["date_created"]  = info.get("date_created", "")
        parent_data[pid]["product_id"]  = pid
        parent_data[pid]["qty"]         += qty
        parent_data[pid]["revenue"]     += rev
        parent_data[pid]["orders"]      += 1

        if sku:
            parent_data[pid]["variants"][sku]["sku"]     = sku
            parent_data[pid]["variants"][sku]["name"]    = name
            parent_data[pid]["variants"][sku]["qty"]     += qty
            parent_data[pid]["variants"][sku]["revenue"] += rev
            parent_data[pid]["variants"][sku]["orders"]  += 1

# ── Build rows ────────────────────────────────────────────────────────────────
from datetime import date as _date

rows = []
for pid, d in parent_data.items():
    # Determine how many days this product was actually active in the window
    created_str = d.get("date_created", "")
    try:
        created_date = _date.fromisoformat(created_str) if created_str else None
    except ValueError:
        created_date = None

    if created_date and created_date > start_dt.date():
        active_days = max(1, (now.date() - created_date).days)
    else:
        active_days = 14

    revenue = round(d["revenue"], 2)
    velocity = round(revenue / active_days, 2)

    variants = sorted(
        [{"sku": v["sku"], "name": v["name"], "qty": v["qty"],
          "revenue": round(v["revenue"], 2), "orders": v["orders"]}
         for v in d["variants"].values()],
        key=lambda x: x["revenue"], reverse=True,
    )
    rows.append({
        "sku":         d["parent_sku"],
        "name":        d["name"],
        "product_id":  d["product_id"],
        "qty":         d["qty"],
        "revenue":     revenue,
        "orders":      d["orders"],
        "active_days": active_days,
        "velocity":    velocity,
        "variants":    variants,
    })

# ── Sort by velocity (revenue/active_days) and apply ABC classification ───────
# Velocity normalizes for products created after the window start, so a new
# product with strong per-day sales isn't penalized by having fewer active days.
rows.sort(key=lambda x: x["velocity"], reverse=True)
total_rev = sum(r["revenue"] for r in rows)
total_qty = sum(r["qty"] for r in rows)

cumulative = 0.0
for r in rows:
    cumulative += r["revenue"]
    pct = cumulative / total_rev * 100
    r["class"]     = "A" if pct <= 80 else ("B" if pct <= 95 else "C")
    r["rev_pct"]   = round(r["revenue"] / total_rev * 100, 2)
    r["daily_qty"] = round(r["qty"] / r["active_days"], 1)

# ── Print report ──────────────────────────────────────────────────────────────
def section(cls, label):
    subset = [r for r in rows if r["class"] == cls]
    cls_rev = sum(r["revenue"] for r in subset)
    cls_qty = sum(r["qty"] for r in subset)
    print(f"\n{'='*95}")
    print(f"  CLASS {cls} — {label}")
    print(f"  {len(subset)} products | ${cls_rev:,.2f} revenue ({cls_rev/total_rev*100:.1f}%) | {cls_qty} units")
    print(f"{'='*95}")
    print(f"  {'SKU':<25} {'Product':<38} {'ActDays':>7} {'Qty':>6} {'Revenue':>10} {'$/day':>8} {'Variants':>8}")
    print(f"  {'-'*25} {'-'*38} {'-'*7} {'-'*6} {'-'*10} {'-'*8} {'-'*8}")
    for r in subset:
        new_flag = " *" if r["active_days"] < 14 else ""
        print(f"  {str(r['sku'])[:24]:<25} {r['name'][:37]:<38} {r['active_days']:>5}{new_flag:>2} {r['qty']:>6} ${r['revenue']:>9,.2f} ${r['velocity']:>7,.2f} {len(r['variants']):>8}")
        for v in r["variants"]:
            print(f"    {'↳ ' + v['sku'][:28]:<30} {v['name'][:37]:<38} {v['qty']:>6} ${v['revenue']:>9,.2f}")

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
new_products = [r for r in rows if r["active_days"] < 14]
print(f"  Period          : {start_dt.strftime('%b %d')} – {now.strftime('%b %d, %Y')} (14 days)")
print(f"  New Products    : {len(new_products)} products with < 14 active days (marked with * — ranked by $/day velocity)")
print(f"  Total Products  : {len(rows)}")
print(f"  Total Revenue   : ${total_rev:,.2f}  (${total_rev/14:,.2f}/day avg)")
print(f"  Total Units     : {total_qty}  ({total_qty/14:.1f} units/day)")
print(f"  Class A         : {len(a)} products ({len(a)/len(rows)*100:.1f}%) → {sum(r['revenue'] for r in a)/total_rev*100:.1f}% of revenue")
print(f"  Class B         : {len(b)} products ({len(b)/len(rows)*100:.1f}%) → {sum(r['revenue'] for r in b)/total_rev*100:.1f}% of revenue")
print(f"  Class C         : {len(c)} products ({len(c)/len(rows)*100:.1f}%) → {sum(r['revenue'] for r in c)/total_rev*100:.1f}% of revenue")

# ── Save JSON ─────────────────────────────────────────────────────────────────
out = Path(__file__).parent / "abc_analysis_results.json"
with open(out, "w") as f:
    json.dump({
        "generated":     now.isoformat(),
        "period_days":   14,
        "total_revenue": total_rev,
        "total_units":   total_qty,
        "ranked_by":     "velocity (revenue/active_days)",
        "skus":          rows,
    }, f, indent=2)
print(f"\n  JSON saved → {out.name}")
