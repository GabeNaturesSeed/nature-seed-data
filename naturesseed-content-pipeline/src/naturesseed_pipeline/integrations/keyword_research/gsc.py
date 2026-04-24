"""Google Search Console provider.

Uses google-api-python-client with ADC for authentication.
Provides own-site ranking data, gap discovery, and page 2 quick wins.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import structlog
from google.auth import default as google_auth_default
from googleapiclient.discovery import build

from naturesseed_pipeline.config import settings

log = structlog.get_logger()

_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def _get_gsc_service():
    """Build a Search Console API service using ADC."""
    credentials, _ = google_auth_default(scopes=_SCOPES)
    return build("searchconsole", "v1", credentials=credentials)


class GscProvider:
    """Google Search Console — own-site query performance and gap discovery."""

    def __init__(self) -> None:
        self._service = None
        self._property_url = settings.gsc_property_url

    def is_available(self) -> bool:
        return settings.gsc_available

    def _svc(self):
        if self._service is None:
            self._service = _get_gsc_service()
        return self._service

    def get_site_queries(
        self,
        start: str | None = None,
        end: str | None = None,
        dimensions: list[str] | None = None,
        row_limit: int = 25000,
    ) -> list[dict[str, Any]]:
        """Fetch GSC search analytics with pagination.

        Args:
            start: YYYY-MM-DD (default: 90 days ago)
            end: YYYY-MM-DD (default: yesterday)
            dimensions: e.g. ["query", "page", "device", "country"]
            row_limit: max rows to fetch (paginated in batches of 25000)
        """
        if not start:
            start = (date.today() - timedelta(days=90)).isoformat()
        if not end:
            end = (date.today() - timedelta(days=1)).isoformat()
        if not dimensions:
            dimensions = ["query", "page", "device", "country"]

        all_rows: list[dict[str, Any]] = []
        start_row = 0
        batch_size = min(row_limit, 25000)

        while True:
            request = {
                "startDate": start,
                "endDate": end,
                "dimensions": dimensions,
                "rowLimit": batch_size,
                "startRow": start_row,
            }

            try:
                response = (
                    self._svc()
                    .searchanalytics()
                    .query(siteUrl=self._property_url, body=request)
                    .execute()
                )
            except Exception as e:
                log.error("gsc_query_failed", error=str(e), start_row=start_row)
                break

            rows = response.get("rows", [])
            if not rows:
                break

            for row in rows:
                keys = row.get("keys", [])
                entry: dict[str, Any] = {}
                for i, dim in enumerate(dimensions):
                    entry[dim] = keys[i] if i < len(keys) else ""
                entry["impressions"] = row.get("impressions", 0)
                entry["clicks"] = row.get("clicks", 0)
                entry["ctr"] = row.get("ctr", 0.0)
                entry["position"] = row.get("position", 0.0)
                all_rows.append(entry)

            start_row += len(rows)
            if len(rows) < batch_size or start_row >= row_limit:
                break

        log.info("gsc_query_complete", rows=len(all_rows), start=start, end=end)
        return all_rows

    def get_ranked_keywords(self) -> list[dict[str, Any]]:
        """Get all keywords naturesseed currently shows impressions for.

        Returns rows with query, page, impressions, clicks, ctr, position
        aggregated over the last 90 days.
        """
        return self.get_site_queries(
            dimensions=["query", "page"],
            row_limit=25000,
        )

    def find_page2_opportunities(
        self,
        min_impressions: int = 50,
        max_position: float = 30.0,
        min_position: float = 11.0,
    ) -> list[dict[str, Any]]:
        """Find keywords where naturesseed ranks on pages 2-5 — quick wins.

        These are near-miss keywords (position 11-30) with significant impressions.
        The writer pipeline can prioritize refreshing pages that rank for these.
        """
        rows = self.get_ranked_keywords()
        opportunities = [
            r for r in rows
            if min_position <= r["position"] <= max_position
            and r["impressions"] >= min_impressions
        ]
        # Sort by impressions descending — highest-potential first
        opportunities.sort(key=lambda x: -x["impressions"])
        log.info("gsc_page2_opportunities", count=len(opportunities))
        return opportunities
