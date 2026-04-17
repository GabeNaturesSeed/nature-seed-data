"""Tests for framework.klaviyo_client."""

import pytest
import responses

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
