/**
 * Data source registry for DTC reporting tooltips.
 *
 * Every metric on the DTC (Reporting) pages has an entry here with:
 *   - description: what the number represents
 *   - formula: how it's derived
 *   - source: the Supabase table/view/column plus any critical filters
 *
 * CRITICAL RULE: all DTC reporting is WooCommerce-only. Amazon and Walmart
 * marketplace data lives in `daily_sales` / `daily_cogs` for reference but is
 * filtered out (`channel='woocommerce'`) or read from the `wc_revenue` column
 * of `daily_summary`. Marketplaces have their own pages.
 *
 * Backend: `infrastructure/dashboard/generate_data.py :: generate_reporting()`
 * Pipeline: GitHub Actions `dashboard_update.yml` writes `docs/reporting.json`.
 */

import type { ReactNode } from 'react';

export interface DataSource {
  description: string;
  formula?: string;
  source: string;
}

function render(s: DataSource): ReactNode {
  return (
    <div className="space-y-1.5">
      <div>{s.description}</div>
      {s.formula && (
        <div>
          <span className="font-semibold">Formula: </span>
          <span className="text-brand-neutral/80">{s.formula}</span>
        </div>
      )}
      <div>
        <span className="font-semibold">Source: </span>
        <span className="text-brand-neutral/80">{s.source}</span>
      </div>
    </div>
  );
}

// ── MTD KPIs ────────────────────────────────────────────────────────────
const mtdSources = {
  mtdRevenue: {
    description: 'Month-to-date WooCommerce (DTC) revenue — gross order total for completed + processing orders, 1st of current month through yesterday. Excludes Amazon and Walmart.',
    formula: 'Σ daily_summary.wc_revenue (fallback: total_revenue − amazon_revenue − walmart_revenue)',
    source: "Supabase view `daily_summary`, column `wc_revenue`, filter `report_date` in current MTD window",
  },
  mtdOrders: {
    description: 'Count of WooCommerce orders (status = completed or processing) placed in the current month through yesterday.',
    formula: 'Σ daily_sales.orders where channel=woocommerce',
    source: "Supabase table `daily_sales`, column `orders`, filter `channel='woocommerce'` AND `report_date` in MTD window",
  },
  mtdAdSpend: {
    description: 'Month-to-date Google Ads spend. Marketplace ad spend (Amazon/Walmart) has its own platforms and is not included.',
    formula: 'Σ daily_summary.total_ad_spend',
    source: 'Supabase view `daily_summary`, column `total_ad_spend` (Google Ads API via `daily_ad_spend` table)',
  },
  mtdMer: {
    description: 'Marketing Efficiency Ratio — WooCommerce revenue divided by total ad spend. Higher is better; > 4.0 is healthy for DTC seed.',
    formula: 'mtd_revenue ÷ mtd_ad_spend',
    source: 'Computed in `generate_data.py :: generate_reporting()` from WC-only revenue and Google Ads spend',
  },
  mtdAov: {
    description: 'Average Order Value — WooCommerce revenue divided by WC order count for the current MTD window.',
    formula: 'mtd_revenue ÷ mtd_orders',
    source: 'Computed from `daily_summary.wc_revenue` and `daily_sales.orders where channel=woocommerce`',
  },
  mtdCogs: {
    description: 'WooCommerce cost of goods sold — unit cost × qty for every line on WC orders in the current MTD window. Excludes marketplace COGS.',
    formula: 'Σ daily_cogs.total_cogs where channel=woocommerce',
    source: "Supabase table `daily_cogs`, column `total_cogs`, filter `channel='woocommerce'` (derived from `cogs_lookup` SKU→unit_cost × WC order line items)",
  },
  mtdGrossProfit: {
    description: 'Revenue minus COGS — money left after the product itself is paid for, before shipping / ads / fees.',
    formula: 'mtd_revenue − mtd_cogs (both WC-only)',
    source: 'Recomputed in `generate_reporting()` from WC-only revenue + WC-only cogs',
  },
  mtdGrossMarginPct: {
    description: 'Gross margin as a percentage of WooCommerce revenue.',
    formula: '(mtd_revenue − mtd_cogs) ÷ mtd_revenue × 100',
    source: 'Recomputed in `generate_reporting()` from WC-only revenue + cogs',
  },
  mtdShipping: {
    description: 'Shipping costs paid to carriers (Shippo) in the current MTD window. Assumed ~100% WooCommerce — marketplaces handle their own fulfillment.',
    formula: 'Σ daily_summary.shipping_cost',
    source: 'Supabase view `daily_summary`, column `shipping_cost` (from `daily_shipping` table, Shippo API)',
  },
  mtdPlatformFees: {
    description: 'Stripe processing fees on WooCommerce orders (no marketplace equivalent in this metric).',
    formula: 'Σ daily_summary.platform_fees',
    source: 'Supabase view `daily_summary`, column `platform_fees`',
  },
  mtdNetRevenue: {
    description: 'Revenue net of refunds and cancellations (pre-COGS, pre-shipping).',
    formula: 'Σ daily_summary.net_revenue',
    source: 'Supabase view `daily_summary`, column `net_revenue`',
  },
  mtdCm1: {
    description: 'Contribution Margin 1 — gross profit minus ad spend. How much each dollar of revenue contributes after product + marketing costs.',
    formula: 'gross_profit − ad_spend',
    source: 'Recomputed in `generate_reporting()` from WC-only inputs',
  },
  mtdCm2: {
    description: 'Contribution Margin 2 — CM1 minus shipping costs and Stripe fees. The true variable-cost-adjusted margin per dollar of DTC revenue.',
    formula: 'CM1 − shipping − platform_fees',
    source: 'Recomputed in `generate_reporting()` from WC-only inputs',
  },
  mtdCm2Pct: {
    description: 'CM2 as a percentage of WooCommerce revenue. ≥ 20% is healthy, 10–20% marginal, < 10% below target for DTC seed.',
    formula: 'CM2 ÷ mtd_revenue × 100',
    source: 'Recomputed in `generate_reporting()` from WC-only inputs',
  },
  mtdNewCustomerCac: {
    description: 'New-customer acquisition cost — total ad spend divided by customers with their first WooCommerce order in the window.',
    formula: 'mtd_ad_spend ÷ mtd_new_customers',
    source: 'Ad spend from `daily_summary.total_ad_spend`; new-customer count from WooCommerce `/orders` lookback (see `_new_customer_count_mtd()` in `generate_data.py`)',
  },
  mtdProjectedRevenue: {
    description: 'Linear-pace projection for month-end WooCommerce revenue based on current daily run rate.',
    formula: '(mtd_revenue ÷ days_elapsed) × days_in_month',
    source: 'Computed client-side by `linearProjection(mtd.daily_cy)` in `dashboard/src/lib/formatters.ts`',
  },
  mtdProjectedCm2: {
    description: 'Projected month-end CM2 dollars, assuming current CM2% rate holds for the rest of the month.',
    formula: 'projected_revenue × (cm2_pct ÷ 100)',
    source: 'Computed client-side on MTD page from projected revenue × actual MTD CM2%',
  },
} as const;

// ── MTD Charts ──────────────────────────────────────────────────────────
const mtdChartSources = {
  dailyRevenueChart: {
    description: 'Daily WooCommerce revenue for the current month vs the same calendar days last year. Each point is one day of DTC orders.',
    formula: 'daily_summary.wc_revenue grouped by report_date; LY points aligned by day-of-month',
    source: 'Supabase view `daily_summary`, column `wc_revenue` (fallback: `total_revenue − amazon_revenue − walmart_revenue`)',
  },
  cumulativeRevenueChart: {
    description: 'Running total of MTD WooCommerce revenue vs LY and vs budget pace. Budget pace = monthly budget ÷ days in month × day-of-month.',
    formula: 'CY/LY: cumulative sum of daily wc_revenue. Budget pace: (budget.net_revenue ÷ days_in_month) × day_index',
    source: 'CY/LY from `daily_summary.wc_revenue`; budget from `infrastructure/dashboard/budget_2026.csv`',
  },
  dailyCmChart: {
    description: 'Estimated daily contribution margin (CM2). Uses current MTD CM2% rate applied to each day\'s revenue — an approximation when per-day shipping / fees / cogs breakouts aren\'t available.',
    formula: 'daily_wc_revenue × (mtd_cm2_pct ÷ 100)',
    source: 'Computed client-side on MTD page from daily WC revenue × MTD CM2 rate',
  },
  cumulativeCmChart: {
    description: 'Running total of estimated daily CM2 for CY and LY. LY uses the same CY rate as an approximation (LY per-day CM2% not available).',
    formula: 'Σ (daily_revenue × cm2_pct_rate) for CY and LY',
    source: 'Computed client-side on MTD page',
  },
};

// ── YTD KPIs ────────────────────────────────────────────────────────────
const ytdSources = {
  ytdRevenue: {
    description: 'Year-to-date WooCommerce (DTC) revenue, Jan 1 through yesterday. Excludes Amazon and Walmart.',
    formula: 'Σ daily_summary.wc_revenue over YTD window, grouped by month',
    source: "Supabase view `daily_summary`, column `wc_revenue`, filter `report_date` ≥ Jan 1 of current year",
  },
  ytdOrders: {
    description: 'Year-to-date count of WooCommerce orders (completed + processing). Excludes marketplaces.',
    formula: 'Σ daily_summary.total_orders per month',
    source: 'Supabase view `daily_summary`, column `total_orders`. (Note: this uses all-channel order totals; for strict WC-only, see `daily_sales` filter)',
  },
  ytdAdSpend: {
    description: 'Year-to-date Google Ads spend. Marketplaces run on their own ad platforms and are not included here.',
    formula: 'Σ daily_summary.total_ad_spend over YTD',
    source: 'Supabase view `daily_summary`, column `total_ad_spend`',
  },
  ytdMer: {
    description: 'Year-to-date Marketing Efficiency Ratio — DTC revenue divided by Google Ads spend.',
    formula: 'ytd_revenue ÷ ytd_ad_spend',
    source: 'Computed in `generate_reporting()` from YTD totals',
  },
  ytdGrossMarginPct: {
    description: 'Year-to-date gross margin percentage — aggregated across all months, WC-only.',
    formula: '(ytd_revenue − ytd_cogs) ÷ ytd_revenue × 100',
    source: 'Computed in `generate_reporting()` from YTD WC-only revenue + cogs',
  },
  ytdCm2: {
    description: 'Year-to-date CM2 dollars — revenue minus cogs, ad spend, shipping, and platform fees, summed across months.',
    formula: 'Σ monthly CM2',
    source: 'Computed in `generate_reporting()` by rolling up per-month CM2 values',
  },
  ytdCm2Pct: {
    description: 'Year-to-date CM2 as a percent of WC revenue. ≥ 20% healthy, 10–20% marginal, < 10% below target.',
    formula: 'ytd_cm2 ÷ ytd_revenue × 100',
    source: 'Computed in `generate_reporting()` from YTD totals',
  },
};

// ── YTD Chart ───────────────────────────────────────────────────────────
const ytdChartSources = {
  cumulativeYtdRevenueChart: {
    description: 'Running total of YTD WooCommerce revenue by month vs LY revenue, budget, and cumulative CM2. Future months show budget only (dotted line) as forward guidance.',
    formula: 'CY/LY/Budget/CM2: cumulative sum over month-series',
    source: 'Monthly aggregates from `daily_summary` (WC-only) + `budget_2026.csv`',
  },
};

// ── CM Waterfall ────────────────────────────────────────────────────────
const cmSources = {
  cmWaterfall: {
    description: 'Monthly contribution margin waterfall: Revenue → CM1 (after seed COGS) → CM2 (after freight + marketing) → Net Income (after G&A only). Built from the full P&L, filtered to WC DTC.',
    formula: 'Revenue = seed_revenue + revenue_freight + discounts. CM1 = Revenue − seed_cogs. CM2 = CM1 − freight − (advertising + development). Net = CM2 − total_ga',
    source: 'Supabase view `daily_summary` + Finance Actuals CSV, rolled up in `generate_reporting() → pnl.months`. Buttons above the chart select which month to render.',
  },
};

// ── P&L Page ────────────────────────────────────────────────────────────
const pnlSources = {
  pnlStatement: {
    description: 'Full monthly P&L including seed revenue, freight, COGS, SMA (advertising + salaries + development), and G&A (salaries, professional fees, insurance, T&E, utilities, corporate allocation). Per-cell tooltips show the specific data source for each line.',
    formula: 'Per-line aggregation — see individual cell tooltips',
    source: 'Finance Actuals CSV (source of truth for closed months) + `daily_summary` / WooCommerce API for the in-progress current month. Assembled in `generate_reporting() → pnl` in `generate_data.py`.',
  },
};

// ── Export — each entry pre-rendered as a ReactNode ─────────────────────
const all = {
  ...mtdSources,
  ...mtdChartSources,
  ...ytdSources,
  ...ytdChartSources,
  ...cmSources,
  ...pnlSources,
};

type SourceKey = keyof typeof all;

export const sources: Record<SourceKey, ReactNode> = Object.fromEntries(
  Object.entries(all).map(([k, v]) => [k, render(v as DataSource)])
) as Record<SourceKey, ReactNode>;

// Raw source definitions exported for anyone who needs the strings (e.g. tests)
export const sourceDefs = all;
