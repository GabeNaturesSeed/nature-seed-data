"""Tests for framework.klaviyo_client."""

import pytest
import responses
from unittest.mock import MagicMock, patch, call

from framework.klaviyo_client import KlaviyoClient


@responses.activate
def test_get_campaign_report_returns_parsed_attributes(sample_campaign_report):
    """Client should call the Klaviyo reports endpoint and return attributes dict."""
    responses.add(
        responses.POST,
        "https://a.klaviyo.com/api/campaign-values-reports",
        json=sample_campaign_report,
        status=200,
    )
    client = KlaviyoClient(api_key="pk_test_fake")
    result = client.get_campaign_report(
        campaign_id="abc123",
        statistics=["recipients", "opens_unique"],
        conversion_metric_id="VLbLXB",
    )
    assert result["recipients"] == 6636
    assert result["opens_unique"] == 4497


@responses.activate
def test_client_sends_correct_headers():
    """Requests must include Klaviyo-API-Key auth and revision 2024-07-15."""
    responses.add(
        responses.POST,
        "https://a.klaviyo.com/api/campaign-values-reports",
        json={"data": {"attributes": {"recipients": 0}}},
        status=200,
    )
    client = KlaviyoClient(api_key="pk_test_fake")
    client.get_campaign_report(campaign_id="x", statistics=[], conversion_metric_id="VLbLXB")
    assert responses.calls[0].request.headers["Authorization"] == "Klaviyo-API-Key pk_test_fake"
    assert responses.calls[0].request.headers["revision"] == "2024-07-15"


def test_get_deliverability_metrics_computes_rates():
    """Verify counts are fetched and rates computed correctly."""
    client = KlaviyoClient(api_key="test-key")

    # Ordered: subscribed, unsubscribed, bounced, spam
    side_effects = [
        {"results": [{"measurements": {"count": [120, 80]}}]},   # subscribed = 200
        {"results": [{"measurements": {"count": [30, 20]}}]},    # unsubscribed = 50
        {"results": [{"measurements": {"count": [10]}}]},         # bounced = 10
        {"results": [{"measurements": {"count": [2]}}]},          # spam = 2
    ]

    with patch.object(client, "query_metric_aggregates", side_effect=side_effects) as mock_qma:
        result = client.get_deliverability_metrics(
            start_date="2026-03-22",
            end_date="2026-04-22",
            total_sends=1000,
        )

    assert result["net_list_growth_30d"] == 150      # 200 - 50
    assert result["spam_rate_30d"] == pytest.approx(0.002)    # 2 / 1000
    assert result["bounce_rate_30d"] == pytest.approx(0.01)   # 10 / 1000
    assert result["unsub_rate_per_send_30d"] == pytest.approx(0.05)  # 50 / 1000

    # Verify called with correct metric IDs in order
    calls = mock_qma.call_args_list
    assert calls[0].kwargs["metric_id"] == "RDUMLh"   # subscribed
    assert calls[1].kwargs["metric_id"] == "UwnyvV"   # unsubscribed
    assert calls[2].kwargs["metric_id"] == "MTYddd"   # bounced
    assert calls[3].kwargs["metric_id"] == "NwZfPQ"   # spam


def test_get_deliverability_metrics_handles_zero_sends():
    """total_sends=0 should not raise ZeroDivisionError."""
    client = KlaviyoClient(api_key="test-key")
    empty = {"results": [{"measurements": {"count": []}}]}

    with patch.object(client, "query_metric_aggregates", return_value=empty):
        result = client.get_deliverability_metrics("2026-03-22", "2026-04-22", total_sends=0)

    assert result["spam_rate_30d"] == 0.0
    assert result["bounce_rate_30d"] == 0.0
    assert result["unsub_rate_per_send_30d"] == 0.0
    assert result["net_list_growth_30d"] == 0
