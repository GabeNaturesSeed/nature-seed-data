-- ═══════════════════════════════════════════════════════════════
-- Nature's Seed — Daily Report Schema
-- Run this in Supabase SQL Editor to create all tables
-- ═══════════════════════════════════════════════════════════════

-- 1. Daily sales by channel (one row per date per channel)
CREATE TABLE daily_sales (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_date DATE NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('woocommerce', 'walmart', 'amazon')),
    revenue NUMERIC(12,2) NOT NULL DEFAULT 0,
    orders INTEGER NOT NULL DEFAULT 0,
    units INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (report_date, channel)
);

-- 2. Daily ad spend by channel
CREATE TABLE daily_ad_spend (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_date DATE NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('google_ads', 'meta_ads', 'amazon_ads')),
    spend NUMERIC(12,2) NOT NULL DEFAULT 0,
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    conversions NUMERIC(10,2) NOT NULL DEFAULT 0,
    conversions_value NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (report_date, channel)
);

-- 3. Daily shipping costs (from Shippo)
CREATE TABLE daily_shipping (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_date DATE NOT NULL UNIQUE,
    total_cost NUMERIC(12,2) NOT NULL DEFAULT 0,
    shipment_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. COGS lookup table (synced from Google Sheet)
CREATE TABLE cogs_lookup (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    unit_cost NUMERIC(10,2) NOT NULL DEFAULT 0,
    selling_price NUMERIC(10,2),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Daily COGS (calculated from orders × unit costs)
CREATE TABLE daily_cogs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_date DATE NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('woocommerce', 'walmart', 'amazon')),
    total_cogs NUMERIC(12,2) NOT NULL DEFAULT 0,
    matched_units INTEGER NOT NULL DEFAULT 0,
    unmatched_units INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (report_date, channel)
);

-- 6. Financial goals (monthly targets)
CREATE TABLE financial_goals (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    revenue_goal NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (year, month)
);

-- ═══════════════════════════════════════════════════════════════
-- INDEXES for fast dashboard queries
-- ═══════════════════════════════════════════════════════════════
CREATE INDEX idx_daily_sales_date ON daily_sales (report_date);
CREATE INDEX idx_daily_sales_channel_date ON daily_sales (channel, report_date);
CREATE INDEX idx_daily_ad_spend_date ON daily_ad_spend (report_date);
CREATE INDEX idx_daily_shipping_date ON daily_shipping (report_date);
CREATE INDEX idx_daily_cogs_date ON daily_cogs (report_date);
CREATE INDEX idx_cogs_lookup_sku ON cogs_lookup (sku);

-- ═══════════════════════════════════════════════════════════════
-- VIEW: daily_summary (aggregated KPIs for Retool)
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW daily_summary AS
SELECT
    s.report_date,
    -- Revenue
    SUM(s.revenue) AS total_revenue,
    SUM(s.orders) AS total_orders,
    SUM(s.units) AS total_units,
    -- By channel
    SUM(CASE WHEN s.channel = 'woocommerce' THEN s.revenue ELSE 0 END) AS wc_revenue,
    SUM(CASE WHEN s.channel = 'walmart' THEN s.revenue ELSE 0 END) AS walmart_revenue,
    SUM(CASE WHEN s.channel = 'amazon' THEN s.revenue ELSE 0 END) AS amazon_revenue,
    -- COGS
    COALESCE(cogs.total_cogs, 0) AS total_cogs,
    -- Shipping
    COALESCE(ship.total_cost, 0) AS shipping_cost,
    -- Net Revenue
    SUM(s.revenue) - COALESCE(cogs.total_cogs, 0) - COALESCE(ship.total_cost, 0) AS net_revenue,
    -- Ad Spend
    COALESCE(ads.total_spend, 0) AS total_ad_spend,
    -- MER (Marketing Efficiency Ratio = Revenue / Ad Spend)
    CASE WHEN COALESCE(ads.total_spend, 0) > 0
         THEN ROUND(SUM(s.revenue) / ads.total_spend, 2)
         ELSE NULL
    END AS mer
FROM daily_sales s
LEFT JOIN (
    SELECT report_date, SUM(total_cogs) AS total_cogs
    FROM daily_cogs GROUP BY report_date
) cogs ON cogs.report_date = s.report_date
LEFT JOIN daily_shipping ship ON ship.report_date = s.report_date
LEFT JOIN (
    SELECT report_date, SUM(spend) AS total_spend
    FROM daily_ad_spend GROUP BY report_date
) ads ON ads.report_date = s.report_date
GROUP BY s.report_date, cogs.total_cogs, ship.total_cost, ship.shipment_count, ads.total_spend;

-- ═══════════════════════════════════════════════════════════════
-- VIEW: mtd_comparison (MTD current year vs last year vs goal)
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW mtd_comparison AS
WITH current_month AS (
    SELECT
        EXTRACT(YEAR FROM report_date)::INT AS yr,
        EXTRACT(MONTH FROM report_date)::INT AS mo,
        SUM(revenue) AS mtd_revenue,
        SUM(orders) AS mtd_orders
    FROM daily_sales
    WHERE EXTRACT(YEAR FROM report_date) = EXTRACT(YEAR FROM CURRENT_DATE)
      AND EXTRACT(MONTH FROM report_date) = EXTRACT(MONTH FROM CURRENT_DATE)
    GROUP BY yr, mo
),
last_year_month AS (
    SELECT
        EXTRACT(YEAR FROM report_date)::INT AS yr,
        EXTRACT(MONTH FROM report_date)::INT AS mo,
        SUM(revenue) AS mtd_revenue,
        SUM(orders) AS mtd_orders
    FROM daily_sales
    WHERE EXTRACT(YEAR FROM report_date) = EXTRACT(YEAR FROM CURRENT_DATE) - 1
      AND EXTRACT(MONTH FROM report_date) = EXTRACT(MONTH FROM CURRENT_DATE)
      AND EXTRACT(DAY FROM report_date) <= EXTRACT(DAY FROM CURRENT_DATE)
    GROUP BY yr, mo
)
SELECT
    cm.yr AS current_year,
    cm.mo AS current_month,
    cm.mtd_revenue AS mtd_revenue_cy,
    cm.mtd_orders AS mtd_orders_cy,
    ly.mtd_revenue AS mtd_revenue_ly,
    ly.mtd_orders AS mtd_orders_ly,
    fg.revenue_goal AS month_goal,
    CASE WHEN ly.mtd_revenue > 0
         THEN ROUND(((cm.mtd_revenue - ly.mtd_revenue) / ly.mtd_revenue) * 100, 1)
         ELSE NULL
    END AS yoy_pct_change,
    CASE WHEN fg.revenue_goal > 0
         THEN ROUND((cm.mtd_revenue / fg.revenue_goal) * 100, 1)
         ELSE NULL
    END AS pct_to_goal
FROM current_month cm
LEFT JOIN last_year_month ly ON ly.mo = cm.mo
LEFT JOIN financial_goals fg ON fg.year = cm.yr AND fg.month = cm.mo;
