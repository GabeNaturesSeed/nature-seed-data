# Seasonality Index — Design Spec
Date: 2026-04-22

## Overview

A live seasonality intelligence layer for the Nature's Seed dashboard. Produces a 0–2 composite index (updated daily) reflecting where the business currently sits in the seasonal cycle. Surfaces on a dedicated Operations page and as a widget on the DTC MTD dashboard.

---

## Index Model

### Dual-Track Architecture

**Demand Index** — how busy is the season?
- Signals: WC revenue, WC order count
- Weights: equal (50/50)

**Performance Index** — how well are we capturing it?
- Signals: blended MER (WC revenue ÷ total ad spend), IS Rank (Search Impression Share), IS Budget Lost (Search Budget Lost Impression Share)
- Weights: equal (33/33/33)
- IS Budget Lost is inverted before normalization (lower lost share = better performance)

**Seasonality Index** = mean(Demand Index, Performance Index), clamped to [0, 2]

### Normalization Method

1. Pull all available historical data from Google Ads API and WooCommerce API
2. Group by ISO week number (1–52)
3. For each week number, compute the multi-year mean across all available years
4. For any given week: `normalized_signal = signal_value ÷ historical_mean_for_that_week_number`
5. Sub-indexes and composite index are means of their normalized signals
6. Raw historical data is discarded after index math is computed — only computed output is stored

### Index Labels

| Range | Label |
|-------|-------|
| 0.0 – 0.5 | Deep Off-Season |
| 0.5 – 0.8 | Slow Period |
| 0.8 – 1.2 | Average |
| 1.2 – 1.6 | Approaching Peak |
| 1.6 – 2.0 | Peak Season |

---

## Data Pipeline

### New Script: `infrastructure/dashboard/generate_seasonality.py`

**Google Ads API pull** (all available history, account level):
- `metrics.cost_micros` → ad spend
- `metrics.search_impression_share` → IS Rank
- `metrics.search_budget_lost_impression_share` → IS Budget Lost

**WooCommerce API pull** (all historical orders):
- Aggregate to daily: revenue + order count
- Filter: `channel = 'woocommerce'` only

**Output:** `docs/data/seasonality.json`

```json
{
  "generated_at": "2026-04-22T07:00:00Z",
  "current_week": 17,
  "index": {
    "seasonality": 1.42,
    "demand": 1.61,
    "performance": 1.23,
    "label": "Approaching Peak"
  },
  "current_week_signals": {
    "wc_revenue": 48200,
    "wc_revenue_avg": 39500,
    "orders": 312,
    "orders_avg": 264,
    "blended_mer": 3.2,
    "blended_mer_avg": 3.33,
    "is_rank": 0.68,
    "is_rank_avg": 0.63,
    "is_budget_lost": 0.12,
    "is_budget_lost_avg": 0.10,
    "ad_spend": 15100,
    "ad_spend_avg": 13980
  },
  "weekly_history": [
    { "week": 1, "seasonality_avg": 0.72, "demand_avg": 0.68, "performance_avg": 0.76, "current_year": 0.71 },
    ...
  ]
}
```

### Pipeline Integration: `dashboard_update.yml`

Add a step after existing data generation to run `generate_seasonality.py`. Output file committed to `docs/data/` alongside other JSON files.

---

## Frontend

### New Page: `/inventory/seasonality`

Route: `src/app/inventory/seasonality/page.tsx`

**Layout (top to bottom):**

1. **Header row** — "Seasonality Overview" + current week badge (e.g. "Week 17 of 52")

2. **Three KPI cards** (full-width row):
   - Seasonality Index — large number, label, color-coded by range
   - Demand Index — revenue + orders sub-label
   - Performance Index — MER + IS sub-label

3. **52-Week Chart** (full width, Recharts `ComposedChart`):
   - X axis: week numbers 1–52
   - Historical average line (solid, muted)
   - Prior years as faint lines (if data available)
   - Current year as bold highlighted line
   - Current week marker (vertical reference line)
   - Reference lines at y=1.0 (average) and y=2.0 (peak)

4. **Signal breakdown** (two-column):
   - Left: Demand Signals table — WC Revenue, Orders, Blended MER vs historical avg
   - Right: Performance Signals table — IS Rank, IS Budget Lost, Ad Spend vs historical avg
   - Each row shows: signal name, current value, historical avg, delta (% or pts), color-coded

### Sidebar Update: `src/components/Sidebar.tsx`

Add "Seasonality" nav item under Operations section, route `/inventory/seasonality`.

---

### DTC MTD Widget — `/reporting`

**Widget:** 6th KPI card in the existing top row (`src/app/reporting/page.tsx`).

- Displays: Seasonality Index score, label, mini progress bar (score ÷ 2 = fill %)
- Color: orange below 1.0, green above 1.0, red below 0.5
- Clicking card navigates to `/inventory/seasonality`
- Extracted as reusable `SeasonalityIndexCard` component

### New Component: `src/components/SeasonalityIndexCard.tsx`

Shared between the DTC MTD widget (compact mode) and the Seasonality page header (full mode). Props: `{ index, demand, performance, label, compact?: boolean }`.

---

## Files Changed

| File | Change |
|------|--------|
| `infrastructure/dashboard/generate_seasonality.py` | New — full pipeline script |
| `.github/workflows/dashboard_update.yml` | Add seasonality generation step |
| `src/app/inventory/seasonality/page.tsx` | New — Seasonality page |
| `src/components/SeasonalityIndexCard.tsx` | New — shared index card component |
| `src/app/reporting/page.tsx` | Add SeasonalityIndexCard as 6th KPI card |
| `src/components/Sidebar.tsx` | Add Seasonality nav item under Operations |
| `docs/data/seasonality.json` | New — generated data file |

---

## Out of Scope

- Seasonality forecasting / projections (future)
- Per-SKU or per-category seasonality (ABC report handles this separately)
- Marketplace revenue in the index (WC-only by design)
- Configurable signal weights via UI
