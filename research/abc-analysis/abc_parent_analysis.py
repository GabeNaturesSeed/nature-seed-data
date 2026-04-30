#!/usr/bin/env python3
"""
ABC Analysis — Parent Product Level with Size Variant Breakdown
Groups by product_id (parent), surfaces size preference trends per product + category.
"""

import requests, time, json, os, base64, re
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict

def _load_env():
    env = {}
    env_file = Path(__file__).parent.parent / ".env"
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

ENV    = _load_env()
WC_CK  = ENV.get("WC_CK", "")
WC_CS  = ENV.get("WC_CS", "")
CF_URL = ENV.get("CF_WORKER_URL", "")
CF_SEC = ENV.get("CF_WORKER_SECRET", "")
BASE   = "https://naturesseed.com/wp-json/wc/v3"

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

# ── Pull orders (last 14 days) ────────────────────────────────────────────────
now      = datetime.now(timezone.utc)
start_dt = now - timedelta(days=14)
after    = start_dt.strftime("%Y-%m-%dT00:00:00")

all_orders = []
for status in ("completed", "processing"):
    page = 1
    while True:
        data, hdrs = wc_get("/orders", {"status": status, "after": after,
                                         "per_page": 100, "page": page})
        if not data:
            break
        all_orders.extend(data)
        if page >= int(hdrs.get("X-WP-TotalPages", 1)):
            break
        page += 1
        time.sleep(0.3)

print(f"Orders: {len(all_orders)}")

# ── Fetch product date_created for active-days normalization ──────────────────
product_ids = {item.get("product_id") for order in all_orders for item in order.get("line_items", []) if item.get("product_id")}
product_dates = {}  # product_id → date_created str (YYYY-MM-DD)
ids_list = list(product_ids)
for i in range(0, len(ids_list), 100):
    chunk = ids_list[i:i + 100]
    data, _ = wc_get("/products", {"include": ",".join(str(x) for x in chunk), "per_page": 100})
    for p in data:
        product_dates[p["id"]] = (p.get("date_created") or "")[:10]
    time.sleep(0.25)
print(f"Product dates: {len(product_dates)} products")

# ── Helpers ───────────────────────────────────────────────────────────────────
SIZE_RE = re.compile(
    r'\b(\d+\.?\d*\s*(?:lb|lbs|oz|kg|g|pound|pounds|sqft|sq\s*ft)s?'
    r'|\d+[\.,]\d+\s*(?:lb|oz|kg)'
    r'|(?:small|medium|large|xl|xxl|starter|mini))\b',
    re.IGNORECASE
)

def extract_size(sku, name, meta):
    """Pull size label from SKU, product name, or order meta."""
    # 1. From SKU segments like -50-LB-, -5-LB, -25-LB-KIT
    m = re.search(r'-(\d+\.?\d*)-?(LB|OZ|KG|G)\b', sku, re.IGNORECASE)
    if m:
        return f"{m.group(1)} {m.group(2).upper()}"
    # 2. From product name
    m = SIZE_RE.search(name)
    if m:
        return m.group(0).strip()
    # 3. From line item meta (WC passes attribute values here)
    for item in meta:
        k = item.get("key", "").lower()
        v = str(item.get("value", "")).strip()
        if any(x in k for x in ("size", "weight", "lb", "quantity", "volume")) and v:
            return v
    return "Unknown"

def clean_name(name):
    """Strip HTML entities and size info from product name for parent grouping."""
    import html as html_mod
    name = html_mod.unescape(name)
    # Remove trailing size descriptors
    name = re.sub(r'\s*[-–]\s*\d+\.?\d*\s*(lb|lbs|oz|kg|g|sqft|sq\s*ft)s?\b.*$',
                  '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*[-–]\s*(small|medium|large|xl|starter)\b.*$', '', name, flags=re.IGNORECASE)
    return name.strip()

def infer_category(name, sku):
    """Rough category from product name / SKU prefix."""
    n = name.lower(); s = sku.upper()
    if s.startswith("PB-") or "pasture" in n or "forage" in n:
        return "Pasture & Forage"
    if s.startswith("TURF-") or "lawn" in n or "grass seed" in n or "fescue" in n or "bluegrass" in n or "ryegrass" in n:
        return "Lawn & Turf"
    if s.startswith("WB-") or "wildflower" in n:
        return "Wildflower"
    if s.startswith("CV-") or "erosion" in n or "revegetation" in n or "native" in n:
        return "Conservation"
    if s.startswith("PG-") or any(x in n for x in ("clover", "alfalfa", "orchardgrass", "timothy", "rye seed", "bermuda", "bahia", "buckwheat", "fescue grass")):
        return "Forage Grasses & Legumes"
    if s.startswith("S-") or any(x in n for x in ("rice hull", "inoculant", "fertilizer", "micro clover", "tackifier", "dutch clover", "sheep fescue", "thingrass")):
        return "Amendments & Specialty"
    if "food plot" in n or s.startswith("PB-GAME") or s.startswith("PB-GRSC") or s.startswith("PB-BIRD") or s.startswith("PB-KRMU"):
        return "Food Plot & Wildlife"
    if "cover crop" in n or "crimson clover" in n or "winter rye" in n or "mustard" in n:
        return "Cover Crop"
    return "Other"

# ── Aggregate ─────────────────────────────────────────────────────────────────
# parent_id → { name, category, total_rev, total_qty, total_orders, variants: {size → {rev, qty}} }
parents = defaultdict(lambda: {
    "name": "", "sku_base": "", "category": "", "date_created": "",
    "rev": 0.0, "qty": 0, "orders": 0,
    "variants": defaultdict(lambda: {"rev": 0.0, "qty": 0, "sku": ""})
})

for order in all_orders:
    for item in order.get("line_items", []):
        pid  = item.get("product_id", 0)
        sku  = item.get("sku", "") or ""
        name = item.get("name", "") or ""
        qty  = int(item.get("quantity", 0))
        rev  = float(item.get("total", 0))
        meta = item.get("meta_data", [])

        size = extract_size(sku, name, meta)
        cname = clean_name(name)
        cat   = infer_category(cname, sku)

        p = parents[pid]
        if not p["name"] or len(cname) < len(p["name"]):
            p["name"] = cname
        if not p["sku_base"]:
            p["sku_base"] = re.sub(r'-\d+[\.\d]*-?(LB|OZ|KG|KIT).*$', '', sku, flags=re.IGNORECASE)
        p["category"] = cat
        p["date_created"] = product_dates.get(pid, "")
        p["rev"]    += rev
        p["qty"]    += qty
        p["orders"] += 1
        p["variants"][size]["rev"] += rev
        p["variants"][size]["qty"] += qty
        p["variants"][size]["sku"]  = sku

# ── Compute active_days and velocity per product ──────────────────────────────
from datetime import date as _date

for pid, r in parents.items():
    created_str = r.get("date_created", "")
    try:
        created_date = _date.fromisoformat(created_str) if created_str else None
    except ValueError:
        created_date = None
    if created_date and created_date > start_dt.date():
        r["active_days"] = max(1, (now.date() - created_date).days)
    else:
        r["active_days"] = 14
    r["velocity"] = round(r["rev"] / r["active_days"], 2)

# ── Sort by velocity, apply ABC classification ────────────────────────────────
rows = sorted(parents.items(), key=lambda x: x[1]["velocity"], reverse=True)
total_rev = sum(r["rev"] for _, r in rows)

cumulative = 0.0
for pid, r in rows:
    cumulative += r["rev"]
    pct = cumulative / total_rev * 100
    r["class"]    = "A" if pct <= 80 else ("B" if pct <= 95 else "C")
    r["rev_pct"]  = r["rev"] / total_rev * 100
    r["daily_rev"] = round(r["rev"] / r["active_days"], 2)
    r["daily_qty"] = round(r["qty"] / r["active_days"], 1)
    r["pid"]       = pid
    # Sort variants by revenue
    r["variants"] = dict(sorted(r["variants"].items(), key=lambda x: x[1]["rev"], reverse=True))

# ── Category size trends ──────────────────────────────────────────────────────
cat_sizes = defaultdict(lambda: defaultdict(float))
for pid, r in rows:
    for size, sv in r["variants"].items():
        cat_sizes[r["category"]][size] += sv["rev"]

# ── Output JSON ───────────────────────────────────────────────────────────────
out_data = {
    "generated": now.isoformat(),
    "period": "2026-02-25 to 2026-03-11",
    "period_days": 14,
    "ranked_by": "velocity (rev/active_days)",
    "total_revenue": total_rev,
    "total_units": sum(r["qty"] for _, r in rows),
    "total_parent_skus": len(rows),
    "products": [
        {
            "pid": pid,
            "name": r["name"],
            "sku_base": r["sku_base"],
            "category": r["category"],
            "class": r["class"],
            "rev": round(r["rev"], 2),
            "qty": r["qty"],
            "orders": r["orders"],
            "active_days": r["active_days"],
            "rev_pct": round(r["rev_pct"], 3),
            "daily_rev": r["daily_rev"],
            "daily_qty": r["daily_qty"],
            "variants": {
                size: {"rev": round(sv["rev"], 2), "qty": sv["qty"], "sku": sv["sku"]}
                for size, sv in r["variants"].items()
            }
        }
        for pid, r in rows
    ],
    "category_size_trends": {
        cat: dict(sorted(sizes.items(), key=lambda x: x[1], reverse=True))
        for cat, sizes in cat_sizes.items()
    }
}

out_path = Path(__file__).parent / "abc_parent_results.json"
with open(out_path, "w") as f:
    json.dump(out_data, f, indent=2)

# ── Print summary ─────────────────────────────────────────────────────────────
print(f"\nPeriod: {out_data['period']}")
print(f"Total Revenue: ${total_rev:,.2f}  |  ${total_rev/14:,.2f}/day")
print(f"Total Parents: {len(rows)}  |  Total Units: {out_data['total_units']}")

for cls in ("A","B","C"):
    sub = [(pid,r) for pid,r in rows if r["class"]==cls]
    cr  = sum(r["rev"] for _,r in sub)
    print(f"Class {cls}: {len(sub)} products  ${cr:,.0f}  ({cr/total_rev*100:.1f}%)")

print(f"\nTop 10 Parents:")
for i,(pid,r) in enumerate(rows[:10]):
    print(f"  {i+1:2}. [{r['class']}] {r['name'][:50]:<50}  ${r['rev']:>9,.2f}  ${r['daily_rev']:>7,.2f}/day")

print(f"\nJSON → {out_path.name}")
