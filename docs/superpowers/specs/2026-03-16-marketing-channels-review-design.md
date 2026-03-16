# Marketing Channels Review Tab — Design Spec

**Date**: 2026-03-16
**Status**: Approved
**Scope**: New dashboard tab for marketing channel performance analysis

---

## Overview

Add a "Marketing" tab to the GitHub Pages dashboard (`docs/index.html`) that displays customer economics (LTV, CAC, contribution margin) and per-channel marketing performance. Data is computed in `generate_data.py` and written to `docs/data/marketing.json`.

## Data Sources

### WooCommerce Orders (new pull — 12 months)
- **Endpoint**: `GET /wp-json/wc/v3/orders`
- **Filter**: Last 12 months, `status` IN ('completed', 'processing')
- **Extracted**: Customer email/ID, order total, order date, line items
- **Purpose**: Calculate unique customers, new vs returning segmentation, LTV
- **Performance**: Could be 50-100+ paginated requests at 0.3s rate limit ≈ 30-60s (acceptable for daily cron)
- **Routing**: Through CF Worker proxy when `CF_WORKER_URL` is set (GitHub Actions)

### WooCommerce Customers (for new vs returning classification)
- **Endpoint**: `GET /wp-json/wc/v3/customers/{id}`
- **Purpose**: Get `date_created` to determine if customer is new (account created within 12-month window)
- **Optimization**: Batch-fetch only unique customer IDs from orders, cache results

### Supabase (existing data)
- `daily_ad_spend` — Google Ads spend, conversions_value (90 days — ad spend data available since early March 2026)
- `daily_summary` — WC revenue, COGS, shipping (available since early March 2026)

### Cold-Start: Limited Supabase History
Supabase has only been collecting data since early March 2026 (~2 weeks). For the 12-month metrics:
- **Revenue + LTV**: Calculated directly from WooCommerce order totals (full 12-month history available)
- **Ad spend (12-month)**: Pull from Google Ads API directly for the full 12-month period (same client library already used in `daily_pull.py`)
- **COGS**: Calculate from WC order line items matched against `cogs_lookup` table (same logic as `daily_pull.py`)
- **Shipping**: Use Supabase data where available; for months without data, omit from contribution margin denominator or note as partial
- **90-day daily table**: Uses Supabase `daily_summary` + `daily_ad_spend` — will only have rows for dates since pipeline started. Display available data, empty rows show "—"

## Metric Definitions

| Metric | Formula | Description |
|--------|---------|-------------|
| 12-Month LTV | `total_wc_revenue / unique_customers` | Average lifetime value over trailing 12 months |
| Contribution Margin | `(revenue - COGS - shipping) / revenue` | Percentage of revenue retained after variable costs |
| CAC | `total_ad_spend / unique_customers` | Cost to acquire any customer |
| nCAC | `total_ad_spend / new_customers` | Cost to acquire a NEW customer only |
| Max CAC (break-even) | `LTV × contribution_margin` | Maximum affordable CAC at zero profit |
| Max CAC (20% profit) | `LTV × contribution_margin × 0.8` | Maximum affordable CAC at 20% profit margin |
| Payback Time | `CAC / (LTV / 12)` | Months to recover acquisition cost |
| LTV:CAC | `LTV / CAC` | Return multiple on acquisition investment |
| ROAS | `conversions_value / ad_spend` | Google Ads return on ad spend |
| Revenue Contribution | `channel_conversions_value / total_wc_revenue × 100` | Channel's attributed revenue as % of total |
| MER | `wc_revenue / ad_spend` | Marketing efficiency ratio (blended) |

### New vs Returning Customer Logic (Chosen Approach)
1. Pull all WooCommerce orders for the 12-month window
2. Extract unique customer IDs from orders
3. For each unique customer, use their WC `date_created` field (available on order objects as `customer_id` → customer record)
4. **New customer**: WC account `date_created` falls within the 12-month window
5. **Returning customer**: WC account `date_created` is before the 12-month window start
6. Guest orders (customer_id = 0): Group by billing email; treat as "new" if their only orders are within the window

This avoids extra API calls in most cases — the customer `date_created` is deterministic and doesn't require cross-referencing historical orders.

### Channel Attribution Disclaimer
With only Google Ads as a tracked paid channel and no multi-touch attribution model, **all channel-level metrics (CAC, LTV, nCAC) are blended across all customers**, not attributed to specific channels. The channel table currently mirrors the top-level widgets. When additional channels are added (Meta, Amazon Ads), per-channel attribution will require order-level source tracking (UTM params, GCLID matching, etc.).

## Output: `docs/data/marketing.json`

```json
{
  "generated_at": "2026-03-16T07:00:00Z",
  "period_start": "2025-03-16",
  "period_end": "2026-03-16",
  "widgets": {
    "ltv_12m": 85.50,
    "contribution_margin": 0.42,
    "cac": 22.30,
    "max_cac_breakeven": 35.91,
    "max_cac_20pct": 28.73,
    "ncac": 31.10,
    "payback_months": 3.1,
    "ltv_cac_ratio": 3.83
  },
  "channels": [
    {
      "name": "Google Ads",
      "cac": 22.30,
      "ltv": 85.50,
      "ncac": 31.10,
      "payback_months": 3.1,
      "revenue_contribution_pct": 100.0,
      "roas": 4.2
    }
  ],
  "daily_90d": [
    {
      "date": "2026-03-16",
      "ad_spend": 120.50,
      "ad_spend_google": 120.50,
      "channel_revenue": 502.30,
      "wc_revenue": 1250.00,
      "mer": 10.37
    }
  ]
}
```

## Dashboard UI

### Tab Structure
- New 5th main tab: **"Marketing"** (after Inventory)
- No sub-tabs initially — single panel

### Layout (top to bottom)

**1. KPI Widget Row** (6 cards, same style as existing MTD cards)
| Card | Value | Subtitle/Context |
|------|-------|-------------------|
| 12-Month LTV | `$85.50` | "Avg customer value" |
| Contribution Margin | `42%` | "After COGS + shipping" |
| Current CAC | `$22.30` | "Break-even: $35.91 · 20% profit: $28.73" |
| Payback Time | `3.1 mo` | "Months to recover CAC" |
| LTV:CAC | `3.83x` | Color: green >3, yellow 2-3, red <2 |
| nCAC | `$31.10` | "New customers only" |

**2. Channel Performance Table**
| Channel | CAC | LTV | nCAC | Payback | Rev Contribution | ROAS |
|---------|-----|-----|------|---------|-----------------|------|
| Google Ads | $22.30 | $85.50 | $31.10 | 3.1 mo | 100% | 4.2x |

**3. 90-Day Daily Table** (scrollable, newest first)
| Date | Ad Spend | Google Ads | Channel Rev | WC Revenue | MER |
|------|----------|------------|-------------|------------|-----|
| 2026-03-16 | $120.50 | $120.50 | $502.30 | $1,250.00 | 10.4x |

## Files Modified

| File | Change |
|------|--------|
| `infrastructure/dashboard/generate_data.py` | Add `generate_marketing()` function + call it from `main()` |
| `docs/index.html` | Add Marketing tab, rendering logic, KPI cards, tables |
| `docs/data/marketing.json` | New output file (generated) |
| `.github/workflows/dashboard_update.yml` | No change needed (generate_data.py already runs fully) |

## Edge Cases

- **Zero ad spend days**: MER = null, display "—"
- **Zero customers**: All customer metrics = null, display "—"
- **Missing COGS/shipping data**: Contribution margin calculated with available data, note if incomplete
- **CF Worker proxy**: Must route WC API calls through proxy in GitHub Actions (same pattern as existing WC pulls)
