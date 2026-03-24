-- ═══════════════════════════════════════════════════════════════
-- Nature's Seed — Supabase Dashboard Views
-- Run these in Supabase SQL Editor to create the views that
-- eliminate redundant API pulls from generate_data.py.
-- ═══════════════════════════════════════════════════════════════

-- ─── 1. Marketing 12-Month Aggregates ────────────────────────
-- Replaces: 365-day WC order pull + Google Ads pull + Shippo pull
-- Used by: generate_marketing() for LTV, CAC, nCAC, CM, payback
DROP VIEW IF EXISTS v_marketing_12m;
CREATE VIEW v_marketing_12m AS
SELECT
  -- Revenue & Orders (all channels)
  COALESCE(SUM(s.revenue), 0) AS total_revenue,
  COALESCE(SUM(s.orders), 0) AS total_orders,
  COALESCE(SUM(s.units), 0) AS total_units,
  -- WooCommerce only
  COALESCE(SUM(CASE WHEN s.channel = 'woocommerce' THEN s.revenue END), 0) AS wc_revenue,
  COALESCE(SUM(CASE WHEN s.channel = 'woocommerce' THEN s.orders END), 0) AS wc_orders,
  -- Ad Spend (all channels)
  COALESCE((SELECT SUM(a.spend) FROM daily_ad_spend a
    WHERE a.report_date >= CURRENT_DATE - INTERVAL '365 days'), 0) AS total_ad_spend,
  -- Google Ads conversions value
  COALESCE((SELECT SUM(a.conversions_value) FROM daily_ad_spend a
    WHERE a.report_date >= CURRENT_DATE - INTERVAL '365 days'
    AND a.channel = 'google_ads'), 0) AS total_conv_value,
  -- COGS
  COALESCE((SELECT SUM(c.total_cogs) FROM daily_cogs c
    WHERE c.report_date >= CURRENT_DATE - INTERVAL '365 days'), 0) AS total_cogs,
  -- Shipping
  COALESCE((SELECT SUM(sh.total_cost) FROM daily_shipping sh
    WHERE sh.report_date >= CURRENT_DATE - INTERVAL '365 days'), 0) AS total_shipping
FROM daily_sales s
WHERE s.report_date >= CURRENT_DATE - INTERVAL '365 days';


-- ─── 2. Monthly Channel Breakdown ───────────────────────────
-- Replaces: 12-month WC order aggregation in Python
-- Used by: generate_marketing() 12-month monthly table
DROP VIEW IF EXISTS v_monthly_channel;
CREATE VIEW v_monthly_channel AS
SELECT
  TO_CHAR(s.report_date, 'YYYY-MM') AS month,
  s.channel,
  SUM(s.revenue) AS revenue,
  SUM(s.orders) AS orders,
  SUM(s.units) AS units
FROM daily_sales s
WHERE s.report_date >= CURRENT_DATE - INTERVAL '365 days'
GROUP BY TO_CHAR(s.report_date, 'YYYY-MM'), s.channel
ORDER BY month, channel;


-- ─── 3. Monthly Ad Spend Breakdown ──────────────────────────
-- Replaces: _pull_google_ads_daily() 365-day pull
-- Used by: generate_marketing() monthly ad spend table
DROP VIEW IF EXISTS v_monthly_ad_spend;
CREATE VIEW v_monthly_ad_spend AS
SELECT
  TO_CHAR(a.report_date, 'YYYY-MM') AS month,
  a.channel,
  SUM(a.spend) AS spend,
  SUM(a.clicks) AS clicks,
  SUM(a.conversions) AS conversions,
  SUM(a.conversions_value) AS conversions_value
FROM daily_ad_spend a
WHERE a.report_date >= CURRENT_DATE - INTERVAL '365 days'
GROUP BY TO_CHAR(a.report_date, 'YYYY-MM'), a.channel
ORDER BY month, channel;


-- ─── 4. Daily Ad Spend (90 days) ────────────────────────────
-- Replaces: _pull_google_ads_daily() for the 90-day daily table
-- Used by: generate_marketing() daily table
DROP VIEW IF EXISTS v_daily_ad_spend_90d;
CREATE VIEW v_daily_ad_spend_90d AS
SELECT
  a.report_date,
  a.channel,
  a.spend,
  a.clicks,
  a.conversions,
  a.conversions_value
FROM daily_ad_spend a
WHERE a.report_date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY a.report_date, a.channel;


-- ─── 5. Amazon 30-Day Summary ───────────────────────────────
-- Replaces: generate_amazon() SP-API 30-day pull
-- Used by: generate_amazon() dashboard widget
DROP VIEW IF EXISTS v_amazon_30d;
CREATE VIEW v_amazon_30d AS
SELECT
  s.report_date,
  s.revenue,
  s.orders,
  s.units
FROM daily_sales s
WHERE s.channel = 'amazon'
  AND s.report_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY s.report_date;


-- ─── 6. Walmart 30-Day Summary ──────────────────────────────
-- Replaces: generate_walmart() API 30-day pull
-- Used by: generate_walmart() dashboard widget
DROP VIEW IF EXISTS v_walmart_30d;
CREATE VIEW v_walmart_30d AS
SELECT
  s.report_date,
  s.revenue,
  s.orders,
  s.units
FROM daily_sales s
WHERE s.channel = 'walmart'
  AND s.report_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY s.report_date;


-- ─── 7. Monthly Shipping Costs ──────────────────────────────
-- Replaces: _pull_shippo_range() 365-day pagination
-- Used by: generate_marketing() total shipping cost
DROP VIEW IF EXISTS v_monthly_shipping;
CREATE VIEW v_monthly_shipping AS
SELECT
  TO_CHAR(sh.report_date, 'YYYY-MM') AS month,
  SUM(sh.total_cost) AS total_cost,
  SUM(sh.shipment_count) AS shipment_count
FROM daily_shipping sh
WHERE sh.report_date >= CURRENT_DATE - INTERVAL '365 days'
GROUP BY TO_CHAR(sh.report_date, 'YYYY-MM')
ORDER BY month;


-- ─── 8. Monthly COGS ───────────────────────────────────────
-- Used by: generate_marketing() contribution margin calc
DROP VIEW IF EXISTS v_monthly_cogs;
CREATE VIEW v_monthly_cogs AS
SELECT
  TO_CHAR(c.report_date, 'YYYY-MM') AS month,
  c.channel,
  SUM(c.total_cogs) AS total_cogs
FROM daily_cogs c
WHERE c.report_date >= CURRENT_DATE - INTERVAL '365 days'
GROUP BY TO_CHAR(c.report_date, 'YYYY-MM'), c.channel
ORDER BY month, channel;


-- ─── 9. Customers Table ─────────────────────────────────────
-- Stores WC customer data for new/returning classification.
-- Eliminates the 365-day WC order pull + customer batch lookup.
CREATE TABLE IF NOT EXISTS customers (
  customer_id BIGINT PRIMARY KEY,
  email TEXT,
  date_created TEXT,       -- ISO date string from WC
  first_order_date TEXT,   -- earliest order date we've seen
  total_orders INT DEFAULT 0,
  total_revenue NUMERIC(12,2) DEFAULT 0,
  last_order_date TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for new/returning classification
CREATE INDEX IF NOT EXISTS idx_customers_date_created
  ON customers(date_created);


-- ─── 10. Customer Summary View ──────────────────────────────
-- Pre-computed new/returning counts for the last 12 months
DROP VIEW IF EXISTS v_customer_summary_12m;
CREATE VIEW v_customer_summary_12m AS
SELECT
  COUNT(*) AS unique_customers,
  COUNT(*) FILTER (WHERE date_created >= TO_CHAR(CURRENT_DATE - INTERVAL '365 days', 'YYYY-MM-DD')) AS new_customers,
  COUNT(*) FILTER (WHERE date_created < TO_CHAR(CURRENT_DATE - INTERVAL '365 days', 'YYYY-MM-DD')) AS returning_customers,
  COALESCE(SUM(total_revenue), 0) AS total_customer_revenue,
  CASE WHEN COUNT(*) > 0 THEN ROUND(SUM(total_revenue) / COUNT(*), 2) ELSE 0 END AS avg_ltv
FROM customers
WHERE last_order_date >= TO_CHAR(CURRENT_DATE - INTERVAL '365 days', 'YYYY-MM-DD');
