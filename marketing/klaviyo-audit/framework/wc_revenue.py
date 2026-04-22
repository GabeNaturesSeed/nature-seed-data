"""Supabase WooCommerce revenue query.

Reads from daily_sales table (channel='woocommerce') via PostgREST REST API.
Schema: daily_sales(report_date DATE, channel TEXT, revenue NUMERIC(12,2))
"""
import requests


def get_wc_revenue_for_week(
    start_date: str,
    end_date: str,
    supabase_url: str,
    api_key: str,
    timeout: int = 20,
) -> float:
    """Sum WooCommerce revenue from daily_sales for a date range (inclusive).

    Returns 0.0 if no rows found.
    """
    url = f"{supabase_url.rstrip('/')}/rest/v1/daily_sales"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # requests encodes list-of-tuples as repeated query params — required for
    # PostgREST range filters on the same column
    params = [
        ("select", "revenue"),
        ("channel", "eq.woocommerce"),
        ("report_date", f"gte.{start_date}"),
        ("report_date", f"lte.{end_date}"),
    ]
    response = requests.get(url, headers=headers, params=params, timeout=timeout)
    response.raise_for_status()
    rows = response.json()
    return sum((float(row["revenue"]) for row in rows), 0.0)
