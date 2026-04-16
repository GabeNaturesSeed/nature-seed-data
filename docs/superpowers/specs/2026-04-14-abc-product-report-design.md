# ABC Product Report — Seasonal Classification

## Overview

A multi-factor ABC product classification system that runs per-season and displays on the dashboard under Operations > ABC Product Report. Shows current season + last 2 seasons for trend comparison.

## Seasons

| Season | Window | Peak |
|---|---|---|
| Spring | Feb 1 – Apr 30 | Feb–Apr |
| Fall | Aug 1 – Sep 30 | Aug–Sep |

Dashboard shows: current season + previous 2 seasons (e.g., Spring 2026, Fall 2025, Spring 2025).

## Data Sources

| Source | Data | Access |
|---|---|---|
| WooCommerce Orders API | Line items (SKU, qty, total, backordered), order totals, order status | Via CF Worker proxy, paginated at 100/page |
| Supabase `cogs_lookup` | SKU → unit cost | REST API |
| WooCommerce cancelled orders | Cancelled order line items | Same API, status=cancelled |

## Classification Model

8-factor weighted composite score per SKU:

| Factor | Weight | Calculation | Direction |
|---|---|---|---|
| **Revenue** | 30% | Sum of line item totals for SKU | Higher = better |
| **Net margin** | 15% | Revenue - (unit_cost × qty). If no COGS match, use revenue × 0.65 (65% default margin) | Higher = better |
| **Units sold** | 15% | Sum of line item quantities | Higher = better |
| **Order frequency** | 10% | Count of distinct orders containing SKU | Higher = better |
| **Avg basket size** | 10% | Mean order total for orders containing this SKU | Higher = better |
| **Velocity trend** | 8% | Linear regression slope of weekly revenue (positive = growing) | Higher = better |
| **Backorder rate** | 7% | Backordered qty / total qty ordered. Penalizes supply difficulty | Lower = better (inverted) |
| **Cancellation rate** | 5% | Cancelled orders with SKU / total orders with SKU | Lower = better (inverted) |

### Scoring

1. For each factor, rank all SKUs by percentile (0–100)
2. Backorder rate and cancellation rate are inverted (100 - percentile) since lower is better
3. Weighted composite: `score = Σ(weight × percentile)` per SKU
4. Sort descending by composite score
5. Classify:
   - **A** = top SKUs comprising 80% of cumulative composite score
   - **B** = next 15% (80–95%)
   - **C** = bottom 5% (95–100%)

### Auto-Generated Reason

Each SKU gets a 1-2 sentence plain-English explanation of its classification. Template:

- **A**: `"Top [revenue/margin/velocity] driver — $X revenue, Y units across Z orders. [Additional notable factor]."`
- **B**: `"Moderate performer — $X revenue. [Strength]. [Weakness or watch item if any]."`
- **C**: `"Low volume — Y units, $X revenue. [Key issue: declining trend / supply constraints / low margin]."`

Include notable signals: high backorder rate, strong velocity trend, exceptional basket lift, margin outlier.

## Output Format

File: `docs/data/abc_report.json`

```json
{
  "generated": "2026-04-14T12:00:00Z",
  "seasons": {
    "spring_2026": {
      "label": "Spring 2026",
      "period": "Feb 1 – Apr 14, 2026",
      "total_revenue": 513441.35,
      "total_orders": 5850,
      "total_skus": 180,
      "summary": {
        "a_count": 25, "a_revenue": 410000, "a_pct": 79.8,
        "b_count": 40, "b_revenue": 77000, "b_pct": 15.0,
        "c_count": 115, "c_revenue": 26441, "c_pct": 5.2
      },
      "items": [
        {
          "sku": "TURF-CLV-25-LB-KIT",
          "name": "Clover Lawn Alternative Mix - 25 lb",
          "class": "A",
          "composite_score": 92.4,
          "revenue": 18500.00,
          "margin": 12025.00,
          "margin_pct": 65.0,
          "units": 206,
          "orders": 158,
          "avg_basket": 142.50,
          "daily_velocity": 2.8,
          "velocity_trend": 0.15,
          "backorder_rate": 0.0,
          "cancellation_rate": 0.0,
          "reason": "Top revenue driver — $18.5K revenue, 206 units across 158 orders. Strong margin at 65% and growing velocity trend."
        }
      ]
    },
    "fall_2025": { ... },
    "spring_2025": { ... }
  }
}
```

## Script

File: `research/abc-analysis/abc_seasonal_report.py`

### Usage
```bash
python3 abc_seasonal_report.py                    # All 3 seasons
python3 abc_seasonal_report.py spring_2026        # Single season
python3 abc_seasonal_report.py --refresh          # Force re-pull (skip cache)
```

### Caching
- Each season's raw order data cached to `research/abc-analysis/cache/spring_2026_orders.json`
- Cache valid for 24 hours (or until `--refresh`)
- Historical seasons (Spring 2025, Fall 2025) cached indefinitely (data doesn't change)

### Performance
- ~5,850 orders for Spring 2026 = 59 pages × 0.3s = ~18 seconds
- Run as part of `dashboard_update.yml` workflow (new job: `abc-report`)

## Dashboard Page

Route: `/inventory/abc`

### Sidebar
Add to Operations menu (Sidebar.tsx) after Shipping Insights:
```
Operations
├── Current Stock
├── Forecasting
├── FBA Inventory
├── Shipping Insights
└── ABC Product Report   ← NEW
```

### Layout

1. **Season selector** — dropdown at top right: "Spring 2026", "Fall 2025", "Spring 2025"

2. **KPI row** (4 cards):
   - A Products (count + revenue %)
   - B Products (count + revenue %)
   - C Products (count + revenue %)
   - Total Season Revenue

3. **Revenue distribution bar** — horizontal stacked bar showing A/B/C revenue split

4. **Data table** — searchable, sortable:
   | Column | Sortable | Default Sort |
   |---|---|---|
   | Class (A/B/C badge) | Yes | — |
   | SKU | Yes | — |
   | Product | Yes | — |
   | Revenue | Yes | desc (default) |
   | Margin | Yes | — |
   | Margin % | Yes | — |
   | Units | Yes | — |
   | Orders | Yes | — |
   | Avg Basket | Yes | — |
   | Velocity | Yes | — |
   | Trend | Yes | — |
   | Backorder % | Yes | — |
   | Reason | No | — |

   - Class column: colored chip (A=green, B=yellow, C=red)
   - Filter tabs above table: All | A Only | B Only | C Only
   - Reason column uses smaller text, wraps

5. **Season comparison** (below table): If previous season data exists, show a small summary:
   - "vs Fall 2025: X products moved A→B, Y moved B→A, Z new products"

## Types

Add to `dashboard/src/lib/types.ts`:

```typescript
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
