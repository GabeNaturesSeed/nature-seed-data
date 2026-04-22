"""Tests for Supabase WC revenue query."""
import pytest
from unittest.mock import patch, MagicMock
from framework.wc_revenue import get_wc_revenue_for_week


def test_get_wc_revenue_sums_rows():
    """Correctly sums revenue from multiple daily rows."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"revenue": "1250.50"},
        {"revenue": "875.00"},
        {"revenue": "2100.25"},
    ]
    mock_response.raise_for_status = MagicMock()

    with patch("framework.wc_revenue.requests.get", return_value=mock_response) as mock_get:
        total = get_wc_revenue_for_week(
            start_date="2026-04-14",
            end_date="2026-04-20",
            supabase_url="https://abc.supabase.co",
            api_key="test-key",
        )

    assert total == pytest.approx(4225.75)

    call_args = mock_get.call_args
    assert "daily_sales" in call_args.args[0]
    params_list = call_args.kwargs["params"]
    params_map: dict = {}
    for k, v in params_list:
        params_map.setdefault(k, []).append(v)
    assert params_map["channel"] == ["eq.woocommerce"]
    assert any("gte.2026-04-14" in v for v in params_map.get("report_date", []))


def test_get_wc_revenue_returns_zero_on_empty():
    """Returns 0.0 when no rows found."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()

    with patch("framework.wc_revenue.requests.get", return_value=mock_response):
        total = get_wc_revenue_for_week(
            start_date="2020-01-01",
            end_date="2020-01-07",
            supabase_url="https://abc.supabase.co",
            api_key="test-key",
        )

    assert total == 0.0


def test_get_wc_revenue_correct_headers():
    """Sends correct Supabase auth headers."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()

    with patch("framework.wc_revenue.requests.get", return_value=mock_response) as mock_get:
        get_wc_revenue_for_week("2026-04-14", "2026-04-20", "https://abc.supabase.co", "sk-test")

    headers = mock_get.call_args.kwargs["headers"]
    assert headers["apikey"] == "sk-test"
    assert headers["Authorization"] == "Bearer sk-test"
