"""Klaviyo REST API wrapper.

Uses revision 2024-07-15 (per project convention — see CLAUDE.md rule 17).
All responses are unwrapped to the `attributes` dict for ergonomics.
"""

from typing import Any, Dict, List, Optional

import requests

API_BASE = "https://a.klaviyo.com/api"
API_REVISION = "2024-07-15"
DEFAULT_TIMEOUT = 30


class KlaviyoClient:
    """Thin wrapper over the Klaviyo REST API."""

    def __init__(self, api_key: str, timeout: int = DEFAULT_TIMEOUT):
        if not api_key:
            raise ValueError("Klaviyo API key is required")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Klaviyo-API-Key {self.api_key}",
            "revision": API_REVISION,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(
            f"{API_BASE}{path}",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_campaign_report(
        self,
        campaign_id: str,
        statistics: List[str],
        conversion_metric_id: str,
        timeframe_key: str = "last_30_days",
    ) -> Dict[str, Any]:
        """Return the `attributes` dict from a campaign performance report."""
        payload = {
            "data": {
                "type": "campaign-values-report",
                "attributes": {
                    "statistics": statistics,
                    "timeframe": {"key": timeframe_key},
                    "conversion_metric_id": conversion_metric_id,
                    "filter": f"equals(campaign_id,\"{campaign_id}\")",
                },
            }
        }
        body = self._post("/campaign-values-reports", payload)
        return body["data"]["attributes"]

    def get_flow_report(
        self,
        flow_id: str,
        statistics: List[str],
        conversion_metric_id: str,
        timeframe_key: str = "last_30_days",
    ) -> Dict[str, Any]:
        """Return the `attributes` dict from a flow performance report."""
        payload = {
            "data": {
                "type": "flow-values-report",
                "attributes": {
                    "statistics": statistics,
                    "timeframe": {"key": timeframe_key},
                    "conversion_metric_id": conversion_metric_id,
                    "filter": f"equals(flow_id,\"{flow_id}\")",
                },
            }
        }
        body = self._post("/flow-values-reports", payload)
        return body["data"]["attributes"]

    def query_metric_aggregates(
        self,
        metric_id: str,
        measurements: List[str],
        start_date: str,
        end_date: str,
        interval: str = "day",
    ) -> Dict[str, Any]:
        """Aggregate events over a time range. Used for list-growth + engagement rate math."""
        payload = {
            "data": {
                "type": "metric-aggregate",
                "attributes": {
                    "metric_id": metric_id,
                    "measurements": measurements,
                    "interval": interval,
                    "filter": [
                        f"greater-or-equal(datetime,{start_date})",
                        f"less-than(datetime,{end_date})",
                    ],
                },
            }
        }
        body = self._post("/metric-aggregates", payload)
        return body["data"]["attributes"]

    # Metric IDs for deliverability signals
    _DELIVERABILITY_METRIC_IDS = {
        "subscribed": "RDUMLh",
        "unsubscribed": "UwnyvV",
        "bounced": "MTYddd",
        "spam": "NwZfPQ",
    }

    def get_deliverability_metrics(
        self,
        start_date: str,
        end_date: str,
        total_sends: int,
    ) -> Dict[str, Any]:
        """Return a dict ready for check_all_gates().

        Fetches 4 metric aggregate counts (subscribed, unsubscribed, bounced, spam)
        and computes rates against total_sends.
        """
        def _count(metric_id: str) -> int:
            attrs = self.query_metric_aggregates(
                metric_id=metric_id,
                measurements=["count"],
                start_date=start_date,
                end_date=end_date,
                interval="month",
            )
            total = 0
            for result in attrs.get("results", []):
                values = result.get("measurements", {}).get("count") or []
                total += sum(v for v in values if isinstance(v, (int, float)))
            return total

        subscribed = _count(self._DELIVERABILITY_METRIC_IDS["subscribed"])
        unsubscribed = _count(self._DELIVERABILITY_METRIC_IDS["unsubscribed"])
        bounced = _count(self._DELIVERABILITY_METRIC_IDS["bounced"])
        spam = _count(self._DELIVERABILITY_METRIC_IDS["spam"])

        safe_sends = max(total_sends, 1)
        return {
            "net_list_growth_30d": subscribed - unsubscribed,
            "spam_rate_30d": spam / safe_sends,
            "bounce_rate_30d": bounced / safe_sends,
            "unsub_rate_per_send_30d": unsubscribed / safe_sends,
        }
