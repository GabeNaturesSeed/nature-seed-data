-- Website Health Monitoring table
-- Stores uptime check results from GitHub Actions (every 30 min)

CREATE TABLE IF NOT EXISTS website_health (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    check_timestamp TIMESTAMPTZ NOT NULL,
    url TEXT NOT NULL,
    status_code INT,
    response_time_ms INT,
    is_up BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wh_timestamp ON website_health(check_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_wh_url ON website_health(url);
