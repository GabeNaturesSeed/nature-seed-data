// ── Reporting ──
export interface DailyDataPoint {
  date: string;
  revenue: number;
}

export interface MtdCY {
  revenue: number;
  orders: number;
  ad_spend: number;
  mer: number;
  cogs: number;
  shipping: number;
  net_revenue: number;
  wc_revenue: number;
  amazon_revenue: number;
  walmart_revenue: number;
  platform_fees: number;
  gross_profit: number;
  gross_margin_pct: number;
  cm1: number;
  cm2: number;
  cm2_pct: number;
  aov: number;
  new_customers: number;
  new_customer_cac: number;
}

export interface MtdComparison {
  revenue: number;
  orders?: number;
  ad_spend: number;
  mer?: number;
}

export interface MtdBudget {
  revenue: number;
  ad_spend: number;
}

export interface YtdMonth {
  month: string;
  revenue: number;
  ly_revenue: number;
  budget_revenue: number;
  orders: number;
  ad_spend: number;
  ly_ad_spend: number;
  budget_ad_spend: number;
  mer: number;
  ly_mer: number;
  budget_mer: number;
  cogs: number;
  shipping: number;
  net_revenue: number;
  gross_profit: number;
  gross_margin_pct: number;
  cm2: number;
  cm2_pct: number;
}

export interface YtdTotals {
  revenue: number;
  orders?: number;
  ad_spend: number;
  cogs?: number;
  net_revenue?: number;
  gross_profit?: number;
  gross_margin_pct?: number;
  cm2?: number;
  cm2_pct?: number;
  mer?: number;
}

export interface PnlMonth {
  month: string;
  source: string;
  seed_revenue?: number;
  other_revenue?: number;
  discounts?: number;
  revenue: number;
  budget_revenue: number;
  revenue_freight: number;
  seed_cogs?: number;
  other_cogs?: number;
  inventory_adjustment?: number;
  cogs: number;
  budget_cogs: number;
  cogs_freight: number;
  source_revenue?: string;
  source_cogs?: string;
  source_freight_cogs?: string;
  source_freight_revenue?: string;
  gross_profit: number;
  budget_gross_profit: number;
  gross_margin_pct: number;
  production_warehouse: number;
  warehouse: number;
  advertising: number;
  budget_advertising: number;
  marketing: number;
  sma_salaries: number;
  development: number;
  total_sma: number;
  ga_salaries: number;
  professional_fees: number;
  insurance: number;
  travel_entertainment: number;
  utilities_supplies: number;
  corporate_allocation: number;
  ga_other: number;
  total_ga: number;
  total_opex: number;
  budget_opex: number;
  net_income: number;
  budget_net_income: number;
  depreciation: number;
  ebitda: number;
  budget_ebitda: number;
}

export interface PnlYtd {
  revenue: number;
  budget_revenue: number;
  revenue_freight: number;
  cogs: number;
  budget_cogs: number;
  cogs_freight: number;
  gross_profit: number;
  budget_gross_profit: number;
  production_warehouse: number;
  warehouse: number;
  advertising: number;
  budget_advertising: number;
  marketing: number;
  sma_salaries: number;
  development: number;
  total_sma: number;
  ga_salaries: number;
  professional_fees: number;
  insurance: number;
  travel_entertainment: number;
  utilities_supplies: number;
  corporate_allocation: number;
  ga_other: number;
  total_ga: number;
  total_opex: number;
  budget_opex: number;
  net_income: number;
  budget_net_income: number;
  depreciation: number;
  ebitda: number;
  budget_ebitda: number;
  gross_margin_pct: number;
}

export interface ReportingData {
  as_of: string;
  mtd: {
    cy: MtdCY;
    ly: MtdComparison;
    budget: MtdBudget;
    daily_cy: DailyDataPoint[];
    daily_ly: DailyDataPoint[];
  };
  ytd: {
    months: YtdMonth[];
    totals_cy: YtdTotals;
    totals_ly: YtdTotals;
    totals_budget: YtdTotals;
  };
  pnl: {
    months: PnlMonth[];
    ytd: PnlYtd;
  };
}

// ── Budget ──
export interface BudgetMonth {
  net_revenue: number;
  cogs: number;
  gross_margin: number;
  ad_spend: number;
  net_income: number;
}

export interface BudgetData {
  as_of: string;
  monthly: Record<string, BudgetMonth>;
  actuals?: Record<string, Record<string, number>>;
}

// ── Amazon ──
export interface MarketplaceDailyPoint {
  date: string;
  revenue: number;
  orders: number;
}

export interface AmazonData {
  as_of: string;
  last_30d: { revenue: number; orders: number; aov: number };
  daily: MarketplaceDailyPoint[];
  account_health: {
    defect_rate: number;
    cancellation_rate: number;
    late_shipment_rate: number;
    status: string;
  };
  active_count: number | null;
  top_products: unknown[];
  issues: unknown[];
}

// ── Walmart ──
export interface WalmartData {
  as_of: string;
  last_30d: { revenue: number; orders: number; aov: number };
  daily: MarketplaceDailyPoint[];
  active_count: number | null;
  top_products: unknown[];
  issues: unknown[];
}

// ── Shipping ──
export interface CarrierData {
  carrier: string;
  total_paid: number;
  shipment_count: number;
  pct_of_shipments: number;
  avg_cost_per_shipment: number;
}

export interface ShippingData {
  as_of: string;
  mtd: {
    shipping_collected: number;
    shipping_paid: number;
    shipping_net: number;
    shipment_count: number;
    avg_cost_per_order: number;
    wc_order_count: number;
  };
  ytd: {
    shipping_collected: number;
    shipping_paid: number;
    shipping_net: number;
    shipment_count: number;
    avg_cost_per_order: number;
    wc_order_count: number;
  };
  carriers: CarrierData[];
  weekly_cost_per_lb: Record<string, { weeks: string[]; values: number[] }>;
}

// ── Inventory ──
export interface InventoryItem {
  sku: string;
  name: string;
  qty: number;
  daily_velocity: number;
  days_remaining: number;
  q1_need: number;
  q2_need: number;
  surplus_gap: number;
  status: string;
}

export interface InventoryData {
  as_of: string;
  items: InventoryItem[];
  fba_items?: InventoryItem[];
  summary?: { total_skus: number; red_count: number; yellow_count: number; green_count: number };
  fba_summary?: { total_skus: number; red_count: number; yellow_count: number; green_count: number };
  warning?: string;
  order_tracking?: {
    total_orders: number;
    fulfilled: number;
    backorders: number;
    unfulfilled_by_age: Record<string, number>;
    total_30d?: number;
    unfulfilled_lt_1d?: number;
    unfulfilled_lt_5d?: number;
    unfulfilled_5_to_10d?: number;
    unfulfilled_gt_10d?: number;
  };
}

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

// ── Klaviyo ──
export interface KlaviyoCampaign {
  id: string;
  name: string;
  send_time: string;
  status: string;
  subject: string;
  segment_name: string;
}

export interface KlaviyoData {
  as_of: string;
  campaigns: KlaviyoCampaign[];
}

// ── Marketing ──
export interface MarketingWidgets {
  ltv_12m: number;
  contribution_margin: number;
  cac: number;
  max_cac_breakeven: number;
  max_cac_20pct: number;
  ncac: number;
  payback_months: number;
  ltv_cac_ratio: number;
}

export interface MarketingDailyPoint {
  date: string;
  ad_spend: number;
  ad_spend_google: number;
  ad_spend_ctv: number;
  channel_revenue: number;
  wc_revenue: number;
  mer: number | null;
}

export interface MarketingMonthlyPoint {
  month: string;
  ad_spend: number;
  ad_spend_google: number;
  ad_spend_ctv: number;
  channel_revenue: number;
  wc_revenue: number;
  mer: number;
  customers: number | null;
  new_customers: number | null;
  cac: number | null;
  ncac: number | null;
}

export interface MarketingChannel {
  name: string;
  cac: number;
  ltv: number;
  ncac: number;
  payback_months: number;
  revenue_contribution_pct: number;
  roas: number;
}

export interface MarketingData {
  generated_at: string;
  period_start: string;
  period_end: string;
  total_customers: number;
  new_customers: number;
  returning_customers: number;
  total_revenue: number;
  total_ad_spend: number;
  total_cogs: number;
  total_shipping: number;
  widgets: MarketingWidgets;
  channels: MarketingChannel[];
  daily_90d: MarketingDailyPoint[];
  monthly_12m: MarketingMonthlyPoint[];
}

// ── Customers ──
export interface CustomersData {
  as_of: string;
  orders_by_state: { state: string; state_name: string; orders: number; revenue: number }[];
  orders_by_hour: { hour: number; label: string; orders: number; revenue: number }[];
  attribution: {
    by_source_type: { source: string; orders: number; revenue: number; pct: number }[];
    by_utm_source: { source: string; orders: number; revenue: number; pct: number }[];
  };
  sessions_before_buying: { bucket: string; orders: number; pct: number }[];
  new_vs_returning: {
    monthly: { month: string; new: number; returning: number; new_revenue: number; returning_revenue: number }[];
    ytd_new: number;
    ytd_returning: number;
    ytd_new_pct: number;
  };
  cohorts: { cohort: string; total: number; reordered: number; reorder_rate: number }[];
}

// ── Notes ──
export interface NotesData {
  as_of: string;
  html: string;
}

// ── Website Health ──
export interface UptimeStatus {
  url: string;
  is_up: boolean;
  response_time_ms: number;
  last_checked: string;
}

export interface UptimeIncident {
  url: string;
  timestamp: string;
  status_code: number;
  duration_min: number;
}

export interface HourlyOrder {
  hour: number;
  today: number;
  last_week: number;
}

export interface SearchQuery {
  query: string;
  count: number;
}

export interface HealthData {
  as_of: string;
  uptime: {
    current_status: UptimeStatus[];
    uptime_24h: number | null;
    uptime_7d: number | null;
    incidents: UptimeIncident[];
    note?: string;
  };
  order_velocity: {
    today_label: string;
    hourly: HourlyOrder[];
    today_total: number;
    last_week_total: number;
  };
  search_health: {
    total_searches_24h: number;
    no_result_rate: number;
    no_result_searches: number;
    top_searches: SearchQuery[];
    top_no_results: SearchQuery[];
  };
  server: Record<string, unknown>;
}
