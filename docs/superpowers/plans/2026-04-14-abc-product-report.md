# ABC Product Report — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a seasonal multi-factor ABC product classification report accessible on the dashboard under Operations > ABC Product Report.

**Architecture:** Python batch script pulls WC orders per season, scores SKUs across 8 weighted factors (revenue, margin, units, frequency, basket size, velocity trend, backorders, cancellations), generates JSON. Next.js dashboard page reads the JSON with season selector, KPI cards, and filterable/sortable table.

**Tech Stack:** Python 3.9+ (requests, numpy for regression), Next.js 14 (app router), Recharts, HeroUI, Supabase (COGS lookup)

---

### Task 1: Python batch script — data pulling + caching

**Files:**
- Create: `research/abc-analysis/abc_seasonal_report.py`

- [ ] **Step 1: Create the script with season definitions, env loading, and WC order puller**

```python
#!/usr/bin/env python3
"""
Seasonal ABC Product Classification — Multi-Factor Weighted Scoring
Nature's Seed | WooCommerce orders → 8-factor SKU-level ranking

Usage:
  python3 abc_seasonal_report.py                    # All 3 seasons
  python3 abc_seasonal_report.py spring_2026        # Single season
  python3 abc_seasonal_report.py --refresh          # Force re-pull
"""

import requests, time, json, os, sys, base64, math
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# ── Env ──────────────────────────────────────────────────────────────────────
def _load_env():
    env = {}
    for p in [Path(__file__).parent / ".env", Path(__file__).resolve().parent.parent.parent / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
            break
    for key in list(env.keys()):
        ov = os.environ.get(key)
        if ov is not None:
            env[key] = ov
    return env

ENV = _load_env()
WC_CK = ENV.get("WC_CK", "")
WC_CS = ENV.get("WC_CS", "")
CF_URL = ENV.get("CF_WORKER_URL", "")
CF_SEC = ENV.get("CF_WORKER_SECRET", "")
SB_URL = ENV.get("SUPABASE_URL", "")
SB_KEY = ENV.get("SUPABASE_SECRET_API_KEY", "")

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
OUT_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "data"

# ── Seasons ──────────────────────────────────────────────────────────────────
now = datetime.now(timezone.utc)

SEASONS = {
    "spring_2026": ("Spring 2026", "2026-02-01", "2026-04-30"),
    "fall_2025":   ("Fall 2025",   "2025-08-01", "2025-09-30"),
    "spring_2025": ("Spring 2025", "2025-02-01", "2025-04-30"),
}

def _season_end(end_str):
    """Cap season end at today if in the future."""
    end = datetime.strptime(end_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return min(end, now).strftime("%Y-%m-%d")

# ── WC API ───────────────────────────────────────────────────────────────────
def wc_get(path, params=None):
    params = dict(params or {})
    if CF_URL and CF_SEC:
        params["wc_path"] = path
        auth_str = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        headers = {"X-Proxy-Secret": CF_SEC, "Authorization": f"Basic {auth_str}"}
        r = requests.get(CF_URL, headers=headers, params=params, timeout=30)
    else:
        r = requests.get(f"https://naturesseed.com/wp-json/wc/v3{path}",
                         auth=(WC_CK, WC_CS), params=params, timeout=30)
    r.raise_for_status()
    return r.json(), r.headers

def pull_orders(after, before, statuses=("completed", "processing")):
    """Pull all orders in date range with given statuses."""
    all_orders = []
    for status in statuses:
        page = 1
        while True:
            params = {"status": status, "after": f"{after}T00:00:00",
                      "before": f"{before}T23:59:59", "per_page": 100, "page": page}
            data, hdrs = wc_get("/orders", params)
            if not data:
                break
            all_orders.extend(data)
            total_pages = int(hdrs.get("X-WP-TotalPages", 1))
            print(f"    [{status}] page {page}/{total_pages} ({len(data)} orders)", flush=True)
            if page >= total_pages:
                break
            page += 1
            time.sleep(0.3)
    return all_orders

def pull_cancelled(after, before):
    """Pull cancelled orders for the same period."""
    return pull_orders(after, before, statuses=("cancelled",))

def get_cached_or_pull(season_key, after, before, refresh=False):
    """Use cache for completed seasons, always refresh current."""
    cache_file = CACHE_DIR / f"{season_key}_orders.json"
    cache_cancelled = CACHE_DIR / f"{season_key}_cancelled.json"
    end_date = datetime.strptime(before, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    season_complete = now > end_date

    if cache_file.exists() and not refresh and season_complete:
        print(f"  Using cached orders for {season_key}", flush=True)
        orders = json.loads(cache_file.read_text())
        cancelled = json.loads(cache_cancelled.read_text()) if cache_cancelled.exists() else []
        return orders, cancelled

    print(f"  Pulling orders for {season_key} ({after} → {before})...", flush=True)
    orders = pull_orders(after, before)
    cancelled = pull_cancelled(after, before)

    cache_file.write_text(json.dumps(orders))
    cache_cancelled.write_text(json.dumps(cancelled))
    print(f"  Cached {len(orders)} orders + {len(cancelled)} cancelled", flush=True)
    return orders, cancelled

# ── COGS lookup ──────────────────────────────────────────────────────────────
def load_cogs():
    """Load SKU → unit_cost from Supabase cogs_lookup table."""
    if not SB_URL or not SB_KEY:
        print("  [WARN] No Supabase credentials — using default 65% margin", flush=True)
        return {}
    headers = {"apikey": SB_KEY}
    url = f"{SB_URL}/rest/v1/cogs_lookup?select=sku,unit_cost"
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        print(f"  [WARN] COGS fetch failed: {resp.status_code}", flush=True)
        return {}
    return {r["sku"]: float(r["unit_cost"]) for r in resp.json()}
```

- [ ] **Step 2: Run the script to verify env loading and WC connection**

Run: `cd research/abc-analysis && python3 -c "exec(open('abc_seasonal_report.py').read().split('# ── Seasons')[0]); print('ENV loaded:', bool(WC_CK))"`
Expected: `ENV loaded: True`

- [ ] **Step 3: Commit**

```bash
git add research/abc-analysis/abc_seasonal_report.py
git commit -m "feat: abc seasonal report — data pulling + caching scaffold"
```

---

### Task 2: Multi-factor scoring engine

**Files:**
- Modify: `research/abc-analysis/abc_seasonal_report.py`

- [ ] **Step 1: Add the aggregation and scoring functions**

Append to the script after the COGS section:

```python
# ── Aggregate by SKU ─────────────────────────────────────────────────────────
def aggregate_skus(orders, cancelled_orders, cogs_map):
    """Build per-SKU metrics from order line items."""
    skus = defaultdict(lambda: {
        "sku": "", "name": "", "revenue": 0.0, "units": 0, "orders": 0,
        "order_totals": [],  # for basket size calc
        "weekly_revenue": defaultdict(float),  # for velocity trend
        "backordered_qty": 0, "cancelled_orders": 0,
        "product_id": 0,
    })

    # Process completed/processing orders
    for order in orders:
        order_total = float(order.get("total", 0))
        order_date = order.get("date_created", "")[:10]
        # ISO week number for weekly binning
        try:
            week = datetime.strptime(order_date, "%Y-%m-%d").isocalendar()[1]
            week_key = f"{order_date[:4]}-W{week:02d}"
        except (ValueError, IndexError):
            week_key = "unknown"

        order_skus_seen = set()
        for item in order.get("line_items", []):
            sku = item.get("sku") or str(item.get("product_id", "unknown"))
            if not sku or sku == "unknown":
                continue
            name = item.get("name", "Unknown")
            qty = int(item.get("quantity", 0))
            rev = float(item.get("total", 0))
            backordered = int(item.get("backordered", 0))

            s = skus[sku]
            s["sku"] = sku
            s["name"] = name
            s["revenue"] += rev
            s["units"] += qty
            s["backordered_qty"] += backordered
            s["product_id"] = item.get("product_id", 0)
            s["weekly_revenue"][week_key] += rev

            if sku not in order_skus_seen:
                s["orders"] += 1
                s["order_totals"].append(order_total)
                order_skus_seen.add(sku)

    # Process cancelled orders
    cancelled_sku_counts = defaultdict(int)
    for order in cancelled_orders:
        for item in order.get("line_items", []):
            sku = item.get("sku") or str(item.get("product_id", "unknown"))
            if sku and sku != "unknown":
                cancelled_sku_counts[sku] += 1

    # Finalize metrics
    results = []
    for sku, s in skus.items():
        if s["units"] == 0:
            continue
        unit_cost = cogs_map.get(sku, None)
        if unit_cost is not None:
            margin = s["revenue"] - (unit_cost * s["units"])
        else:
            margin = s["revenue"] * 0.65  # default 65% margin

        margin_pct = (margin / s["revenue"] * 100) if s["revenue"] > 0 else 0
        avg_basket = sum(s["order_totals"]) / len(s["order_totals"]) if s["order_totals"] else 0
        backorder_rate = s["backordered_qty"] / s["units"] if s["units"] > 0 else 0
        total_orders_for_sku = s["orders"] + cancelled_sku_counts.get(sku, 0)
        cancellation_rate = cancelled_sku_counts.get(sku, 0) / total_orders_for_sku if total_orders_for_sku > 0 else 0

        # Velocity trend — linear regression slope on weekly revenue
        weeks = sorted(s["weekly_revenue"].keys())
        if len(weeks) >= 2:
            x = list(range(len(weeks)))
            y = [s["weekly_revenue"][w] for w in weeks]
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(xi * yi for xi, yi in zip(x, y))
            sum_x2 = sum(xi * xi for xi in x)
            denom = n * sum_x2 - sum_x * sum_x
            slope = (n * sum_xy - sum_x * sum_y) / denom if denom != 0 else 0
        else:
            slope = 0

        # Daily velocity
        season_days = max(len(weeks) * 7, 14)  # approximate
        daily_velocity = s["units"] / season_days

        results.append({
            "sku": sku,
            "name": s["name"],
            "revenue": round(s["revenue"], 2),
            "margin": round(margin, 2),
            "margin_pct": round(margin_pct, 1),
            "units": s["units"],
            "orders": s["orders"],
            "avg_basket": round(avg_basket, 2),
            "daily_velocity": round(daily_velocity, 2),
            "velocity_trend": round(slope, 2),
            "backorder_rate": round(backorder_rate, 4),
            "cancellation_rate": round(cancellation_rate, 4),
            "product_id": s["product_id"],
        })

    return results

# ── Percentile scoring ───────────────────────────────────────────────────────
def percentile_rank(values):
    """Return percentile ranks (0–100) for a list of values."""
    n = len(values)
    if n == 0:
        return []
    sorted_vals = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * n
    for rank_pos, (orig_idx, _) in enumerate(sorted_vals):
        ranks[orig_idx] = rank_pos / max(n - 1, 1) * 100
    return ranks

WEIGHTS = {
    "revenue": 0.30,
    "margin": 0.15,
    "units": 0.15,
    "orders": 0.10,
    "avg_basket": 0.10,
    "velocity_trend": 0.08,
    "backorder_rate": 0.07,   # inverted
    "cancellation_rate": 0.05,  # inverted
}

def score_and_classify(items):
    """Score each SKU with weighted percentiles and assign A/B/C."""
    if not items:
        return items

    # Compute percentile ranks for each factor
    factors = {}
    for key in WEIGHTS:
        values = [item[key] for item in items]
        ranks = percentile_rank(values)
        # Invert negative factors (lower = better)
        if key in ("backorder_rate", "cancellation_rate"):
            ranks = [100 - r for r in ranks]
        factors[key] = ranks

    # Composite score
    for i, item in enumerate(items):
        score = sum(WEIGHTS[k] * factors[k][i] for k in WEIGHTS)
        item["composite_score"] = round(score, 1)

    # Sort by composite score descending
    items.sort(key=lambda x: x["composite_score"], reverse=True)

    # ABC classification by cumulative score
    total_score = sum(item["composite_score"] for item in items)
    cumulative = 0.0
    for item in items:
        cumulative += item["composite_score"]
        pct = cumulative / total_score * 100 if total_score > 0 else 100
        if pct <= 80:
            item["class"] = "A"
        elif pct <= 95:
            item["class"] = "B"
        else:
            item["class"] = "C"

    return items

# ── Reason generator ─────────────────────────────────────────────────────────
def generate_reasons(items, total_revenue):
    """Generate plain-English explanation for each SKU's classification."""
    for item in items:
        cls = item["class"]
        rev = item["revenue"]
        rev_pct = rev / total_revenue * 100 if total_revenue > 0 else 0
        parts = []

        if cls == "A":
            parts.append(f"Top performer — ${rev:,.0f} revenue ({rev_pct:.1f}% of season), {item['units']} units across {item['orders']} orders.")
            if item["margin_pct"] > 60:
                parts.append(f"Strong margin at {item['margin_pct']:.0f}%.")
            if item["velocity_trend"] > 50:
                parts.append("Accelerating demand.")
            if item["avg_basket"] > 150:
                parts.append(f"Drives large orders (${item['avg_basket']:,.0f} avg basket).")
            if item["backorder_rate"] > 0.05:
                parts.append(f"Watch: {item['backorder_rate']*100:.1f}% backorder rate — supply constraint risk.")

        elif cls == "B":
            parts.append(f"Moderate performer — ${rev:,.0f} revenue, {item['units']} units.")
            if item["orders"] > 30:
                parts.append(f"Consistent demand across {item['orders']} orders.")
            if item["margin_pct"] > 60:
                parts.append(f"Good margin at {item['margin_pct']:.0f}%.")
            elif item["margin_pct"] < 30:
                parts.append(f"Low margin at {item['margin_pct']:.0f}% — review pricing.")
            if item["backorder_rate"] > 0.05:
                parts.append(f"Backorder rate {item['backorder_rate']*100:.1f}% signals supply difficulty.")
            if item["velocity_trend"] < -50:
                parts.append("Declining trend — monitor.")

        else:  # C
            parts.append(f"Low volume — {item['units']} units, ${rev:,.0f} revenue.")
            if item["velocity_trend"] < -20:
                parts.append("Declining demand.")
            if item["backorder_rate"] > 0.10:
                parts.append(f"High backorder rate ({item['backorder_rate']*100:.0f}%) — hard to source.")
            if item["cancellation_rate"] > 0.05:
                parts.append(f"Elevated cancellations ({item['cancellation_rate']*100:.1f}%).")
            if item["margin_pct"] < 20:
                parts.append("Weak margin — consider discontinuing or bundling.")
            if not any("Declin" in p or "backorder" in p.lower() or "cancel" in p.lower() or "margin" in p.lower() for p in parts[1:]):
                parts.append("Niche product — low demand but stable.")

        item["reason"] = " ".join(parts)

# ── Build season report ──────────────────────────────────────────────────────
def build_season(season_key, refresh=False):
    label, start, end = SEASONS[season_key]
    actual_end = _season_end(end)
    period_str = f"{start} → {actual_end}"
    print(f"\n{'='*60}")
    print(f"  {label} ({period_str})")
    print(f"{'='*60}", flush=True)

    orders, cancelled = get_cached_or_pull(season_key, start, actual_end, refresh)
    cogs = load_cogs()

    items = aggregate_skus(orders, cancelled, cogs)
    items = score_and_classify(items)

    total_revenue = sum(i["revenue"] for i in items)
    total_orders = len(set(o.get("id") for o in orders))
    generate_reasons(items, total_revenue)

    # Summary counts
    a_items = [i for i in items if i["class"] == "A"]
    b_items = [i for i in items if i["class"] == "B"]
    c_items = [i for i in items if i["class"] == "C"]

    # Clean up internal fields before output
    for item in items:
        for key in ("product_id",):
            item.pop(key, None)

    return {
        "label": label,
        "period": period_str,
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "total_skus": len(items),
        "summary": {
            "a_count": len(a_items), "a_revenue": round(sum(i["revenue"] for i in a_items), 2),
            "a_pct": round(sum(i["revenue"] for i in a_items) / total_revenue * 100, 1) if total_revenue else 0,
            "b_count": len(b_items), "b_revenue": round(sum(i["revenue"] for i in b_items), 2),
            "b_pct": round(sum(i["revenue"] for i in b_items) / total_revenue * 100, 1) if total_revenue else 0,
            "c_count": len(c_items), "c_revenue": round(sum(i["revenue"] for i in c_items), 2),
            "c_pct": round(sum(i["revenue"] for i in c_items) / total_revenue * 100, 1) if total_revenue else 0,
        },
        "items": items,
    }

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    refresh = "--refresh" in sys.argv
    requested = [a for a in sys.argv[1:] if not a.startswith("-")]

    if requested:
        season_keys = [k for k in requested if k in SEASONS]
    else:
        season_keys = list(SEASONS.keys())

    report = {"generated": now.isoformat(), "seasons": {}}
    for key in season_keys:
        report["seasons"][key] = build_season(key, refresh)

    # Print summary
    print(f"\n{'='*60}")
    print("  REPORT SUMMARY")
    print(f"{'='*60}")
    for key, season in report["seasons"].items():
        s = season["summary"]
        print(f"  {season['label']}: {season['total_skus']} SKUs, ${season['total_revenue']:,.0f} revenue")
        print(f"    A: {s['a_count']} SKUs ({s['a_pct']:.0f}%)  B: {s['b_count']} SKUs ({s['b_pct']:.0f}%)  C: {s['c_count']} SKUs ({s['c_pct']:.0f}%)")

    out = OUT_DIR / "abc_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\n  Saved → {out}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script for Spring 2026 only (test)**

Run: `cd research/abc-analysis && python3 abc_seasonal_report.py spring_2026`
Expected: Pulls ~5,850 orders, outputs JSON with scored/classified SKUs

- [ ] **Step 3: Run all 3 seasons**

Run: `cd research/abc-analysis && python3 abc_seasonal_report.py`
Expected: All 3 seasons processed, `docs/data/abc_report.json` written

- [ ] **Step 4: Commit**

```bash
git add research/abc-analysis/abc_seasonal_report.py docs/data/abc_report.json
git commit -m "feat: seasonal ABC product report with 8-factor scoring"
```

---

### Task 3: TypeScript types + sidebar update

**Files:**
- Modify: `dashboard/src/lib/types.ts`
- Modify: `dashboard/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Add ABC types to types.ts**

Add after the InventoryData interface:

```typescript
// ── ABC Product Report ──
export interface AbcItem {
  sku: string;
  name: string;
  class: 'A' | 'B' | 'C';
  composite_score: number;
  revenue: number;
  margin: number;
  margin_pct: number;
  units: number;
  orders: number;
  avg_basket: number;
  daily_velocity: number;
  velocity_trend: number;
  backorder_rate: number;
  cancellation_rate: number;
  reason: string;
}

export interface AbcSeason {
  label: string;
  period: string;
  total_revenue: number;
  total_orders: number;
  total_skus: number;
  summary: {
    a_count: number; a_revenue: number; a_pct: number;
    b_count: number; b_revenue: number; b_pct: number;
    c_count: number; c_revenue: number; c_pct: number;
  };
  items: AbcItem[];
}

export interface AbcReportData {
  generated: string;
  seasons: Record<string, AbcSeason>;
}
```

- [ ] **Step 2: Add ABC page to sidebar**

In `Sidebar.tsx`, add after the Shipping Insights entry in the Operations (formerly Inventory) children array. Import `ClipboardList` from lucide-react at the top:

```typescript
{ label: 'ABC Product Report', href: '/inventory/abc', icon: ClipboardList },
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/lib/types.ts dashboard/src/components/layout/Sidebar.tsx
git commit -m "feat: ABC report types + sidebar link"
```

---

### Task 4: Dashboard ABC page

**Files:**
- Create: `dashboard/src/app/inventory/abc/page.tsx`

- [ ] **Step 1: Create the ABC report page**

```tsx
'use client';

import { useState, useMemo } from 'react';
import { useJsonData } from '@/hooks/useJsonData';
import { AbcReportData, AbcItem } from '@/lib/types';
import { fmt, fmtInt, pctPlain } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import { Skeleton, Chip } from '@heroui/react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

type SortKey = 'class' | 'sku' | 'name' | 'revenue' | 'margin' | 'margin_pct' | 'units' | 'orders' | 'avg_basket' | 'daily_velocity' | 'velocity_trend' | 'backorder_rate';
type SortDir = 'asc' | 'desc';
type ClassFilter = 'all' | 'A' | 'B' | 'C';

const CLASS_COLORS = { A: '#2d6a4f', B: '#d4a373', C: '#c96a2e' };

export default function AbcReportPage() {
  const { data, loading } = useJsonData<AbcReportData>('abc_report');
  const [seasonKey, setSeasonKey] = useState<string>('');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('revenue');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [classFilter, setClassFilter] = useState<ClassFilter>('all');

  // Pick season keys
  const seasonKeys = useMemo(() => data ? Object.keys(data.seasons) : [], [data]);
  const activeKey = seasonKey || seasonKeys[0] || '';
  const season = data?.seasons[activeKey];

  const items = useMemo(() => {
    if (!season) return [];
    let filtered = season.items;
    if (classFilter !== 'all') {
      filtered = filtered.filter(i => i.class === classFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      filtered = filtered.filter(i => i.sku.toLowerCase().includes(q) || i.name.toLowerCase().includes(q));
    }
    return [...filtered].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return sortDir === 'asc' ? (Number(aVal) - Number(bVal)) : (Number(bVal) - Number(aVal));
    });
  }, [season, classFilter, search, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };
  const sortInd = (key: SortKey) => sortKey !== key ? '' : sortDir === 'asc' ? ' ↑' : ' ↓';

  if (loading) return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-64 rounded-xl" />
      <div className="grid grid-cols-4 gap-4">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}</div>
    </div>
  );

  if (!data || !season) return <p className="text-brand-neutral/50">ABC report data unavailable</p>;

  const s = season.summary;
  const chartData = [
    { name: `A (${s.a_count})`, value: s.a_revenue, color: CLASS_COLORS.A },
    { name: `B (${s.b_count})`, value: s.b_revenue, color: CLASS_COLORS.B },
    { name: `C (${s.c_count})`, value: s.c_revenue, color: CLASS_COLORS.C },
  ];

  return (
    <div>
      {/* Header + Season Selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-baseline justify-between mb-6 md:mb-8 gap-3">
        <h1 className="font-display text-xl md:text-2xl font-bold text-brand-neutral">ABC Product Report</h1>
        <div className="flex items-center gap-3">
          <select
            value={activeKey}
            onChange={e => setSeasonKey(e.target.value)}
            className="px-3 py-1.5 text-sm bg-surface-lowest rounded-lg shadow-ambient outline-none focus:ring-2 focus:ring-brand-primary/20 text-brand-neutral"
          >
            {seasonKeys.map(k => (
              <option key={k} value={k}>{data.seasons[k].label}</option>
            ))}
          </select>
          <span className="text-[10px] md:text-xs text-brand-neutral/50">{season.period}</span>
        </div>
      </div>

      {/* KPI Cards */}
      <KpiGrid columns={4}>
        <KpiCard label="A Products" value={fmtInt(s.a_count)} subValue={`${fmt(s.a_revenue)} (${s.a_pct}%)`} badges={[{ label: 'Top performers', color: 'success' }]} />
        <KpiCard label="B Products" value={fmtInt(s.b_count)} subValue={`${fmt(s.b_revenue)} (${s.b_pct}%)`} badges={[{ label: 'Moderate', color: 'warning' }]} />
        <KpiCard label="C Products" value={fmtInt(s.c_count)} subValue={`${fmt(s.c_revenue)} (${s.c_pct}%)`} badges={[{ label: 'Long tail', color: 'danger' }]} />
        <KpiCard label="Season Revenue" value={fmt(season.total_revenue)} subValue={`${fmtInt(season.total_orders)} orders • ${fmtInt(season.total_skus)} SKUs`} />
      </KpiGrid>

      {/* Revenue Distribution Chart */}
      <div className="bg-surface-lowest rounded-xl shadow-ambient p-6 mb-8">
        <h2 className="font-display text-sm font-semibold text-brand-neutral/60 uppercase tracking-wider mb-4">Revenue Distribution by Class</h2>
        <div className="h-16">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={[{ A: s.a_pct, B: s.b_pct, C: s.c_pct }]} layout="vertical" barSize={32}>
              <XAxis type="number" domain={[0, 100]} hide />
              <YAxis type="category" dataKey="name" hide />
              <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
              <Bar dataKey="A" stackId="stack" fill={CLASS_COLORS.A} radius={[4, 0, 0, 4]} />
              <Bar dataKey="B" stackId="stack" fill={CLASS_COLORS.B} />
              <Bar dataKey="C" stackId="stack" fill={CLASS_COLORS.C} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="flex gap-6 mt-3">
          {chartData.map(d => (
            <div key={d.name} className="flex items-center gap-2 text-xs text-brand-neutral/60">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: d.color }} />
              {d.name}: {fmt(d.value)}
            </div>
          ))}
        </div>
      </div>

      {/* Filter tabs + search */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-5">
        <div className="flex gap-1 bg-surface-low rounded-lg p-1">
          {(['all', 'A', 'B', 'C'] as ClassFilter[]).map(f => (
            <button key={f} onClick={() => setClassFilter(f)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${classFilter === f ? 'bg-surface-lowest shadow-sm text-brand-neutral' : 'text-brand-neutral/50 hover:text-brand-neutral/80'}`}>
              {f === 'all' ? `All (${season.total_skus})` : `${f} (${s[`${f.toLowerCase()}_count` as keyof typeof s]})`}
            </button>
          ))}
        </div>
        <input type="text" placeholder="Search SKU or product..." value={search} onChange={e => setSearch(e.target.value)}
          className="px-4 py-2 text-sm bg-surface-lowest rounded-xl shadow-ambient outline-none focus:ring-2 focus:ring-brand-primary/20 text-brand-neutral placeholder:text-brand-neutral/40 w-full sm:w-64" />
      </div>

      {/* Data Table */}
      <div className="bg-surface-lowest rounded-xl shadow-ambient overflow-x-auto">
        <table className="w-full text-sm border-collapse min-w-[1200px]">
          <thead>
            <tr className="bg-surface-low">
              {([
                { key: 'class' as SortKey, label: 'Class', align: 'left' },
                { key: 'sku' as SortKey, label: 'SKU', align: 'left' },
                { key: 'name' as SortKey, label: 'Product', align: 'left' },
                { key: 'revenue' as SortKey, label: 'Revenue', align: 'right' },
                { key: 'margin' as SortKey, label: 'Margin', align: 'right' },
                { key: 'margin_pct' as SortKey, label: 'Margin %', align: 'right' },
                { key: 'units' as SortKey, label: 'Units', align: 'right' },
                { key: 'orders' as SortKey, label: 'Orders', align: 'right' },
                { key: 'avg_basket' as SortKey, label: 'Avg Basket', align: 'right' },
                { key: 'daily_velocity' as SortKey, label: 'Velocity', align: 'right' },
                { key: 'backorder_rate' as SortKey, label: 'BO %', align: 'right' },
              ]).map(col => (
                <th key={col.key} onClick={() => handleSort(col.key)}
                  className={`px-4 py-3 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold cursor-pointer hover:bg-brand-primary/5 select-none transition-colors ${col.align === 'right' ? 'text-right' : 'text-left'}`}>
                  {col.label}{sortInd(col.key)}
                </th>
              ))}
              <th className="px-4 py-3 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold text-left">Reason</th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => (
              <tr key={item.sku} className="hover:bg-surface-low transition-colors border-t border-brand-outline/10">
                <td className="px-4 py-2.5">
                  <Chip size="sm" variant="solid"
                    style={{ backgroundColor: CLASS_COLORS[item.class], color: item.class === 'B' ? '#1a1a1a' : '#fff' }}>
                    {item.class}
                  </Chip>
                </td>
                <td className="px-4 py-2.5 font-mono text-xs">{item.sku}</td>
                <td className="px-4 py-2.5 max-w-[200px] truncate">{item.name}</td>
                <td className="px-4 py-2.5 text-right">{fmt(item.revenue)}</td>
                <td className="px-4 py-2.5 text-right">{fmt(item.margin)}</td>
                <td className="px-4 py-2.5 text-right">{item.margin_pct.toFixed(0)}%</td>
                <td className="px-4 py-2.5 text-right">{fmtInt(item.units)}</td>
                <td className="px-4 py-2.5 text-right">{fmtInt(item.orders)}</td>
                <td className="px-4 py-2.5 text-right">{fmt(item.avg_basket)}</td>
                <td className="px-4 py-2.5 text-right">{item.daily_velocity.toFixed(1)}/d</td>
                <td className="px-4 py-2.5 text-right">{item.backorder_rate > 0 ? `${(item.backorder_rate * 100).toFixed(1)}%` : '—'}</td>
                <td className="px-4 py-2.5 text-xs text-brand-neutral/60 max-w-[300px]">{item.reason}</td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={12} className="px-5 py-8 text-center text-brand-neutral/50">No matching products</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify the page renders locally**

Run: `cd dashboard && npm run dev` then visit `http://localhost:3000/inventory/abc`
Expected: Page loads with season selector, KPI cards, chart, and table

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/app/inventory/abc/page.tsx
git commit -m "feat: ABC Product Report dashboard page with season selector + filterable table"
```

---

### Task 5: Add to GitHub Actions workflow

**Files:**
- Modify: `.github/workflows/dashboard_update.yml`

- [ ] **Step 1: Add abc-report job**

Add a new parallel job after the `algolia-enrich` job:

```yaml
  abc-report:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install requests
      - name: Create .env
        run: echo "$ENV_CONTENT" > .env
      - name: Generate ABC seasonal report
        run: python research/abc-analysis/abc_seasonal_report.py
      - uses: actions/upload-artifact@v4
        with:
          name: abc-report
          path: docs/data/abc_report.json
          retention-days: 1
```

- [ ] **Step 2: Add download + commit in commit-and-push job**

Add `abc-report` to the `needs` array and add a download step:

```yaml
    needs: [abc-analysis, dashboard-data, customer-data, review-feed, algolia-enrich, abc-report]
```

```yaml
      - name: Download ABC report
        uses: actions/download-artifact@v4
        with:
          name: abc-report
          path: docs/data/
        continue-on-error: true
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/dashboard_update.yml
git commit -m "ci: add seasonal ABC report to dashboard workflow"
```

---

### Task 6: Run full report + verify end-to-end

- [ ] **Step 1: Generate all 3 seasons locally**

Run: `cd research/abc-analysis && python3 abc_seasonal_report.py`

- [ ] **Step 2: Verify abc_report.json structure**

Run: `python3 -c "import json; d=json.load(open('docs/data/abc_report.json')); [print(f'{k}: {d[\"seasons\"][k][\"total_skus\"]} SKUs, \${d[\"seasons\"][k][\"total_revenue\"]:,.0f}') for k in d['seasons']]"`

- [ ] **Step 3: Test dashboard page with real data**

Run: `cd dashboard && npm run dev` → visit `/inventory/abc`
Verify: season dropdown works, class filters work, sorting works, reasons display

- [ ] **Step 4: Final commit with generated data**

```bash
git add docs/data/abc_report.json research/abc-analysis/cache/
git commit -m "data: seasonal ABC report for Spring 2025, Fall 2025, Spring 2026"
```
