"""DataForSEO provider — SERP snapshots and true SEO difficulty.

STUBBED FOR NOW. Auto-gates on DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD env vars.
When both are set, the provider activates and enriches keyword candidates with:
- Organic SERP snapshots (Google Organic endpoint, Standard Queue)
- True SEO keyword difficulty (DataForSEO Labs API)
- Competitor ranked keywords for gap analysis

To enable:
    1. Add DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD to .env
    2. Fund account with $50 minimum deposit at https://dataforseo.com
    3. Restart the pipeline
    SERP + true keyword difficulty will automatically start enriching new candidates.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog

from naturesseed_pipeline.config import settings
from naturesseed_pipeline.integrations.keyword_research.base import (
    DifficultyRecord,
    KeywordIdea,
    RelatedQuery,
    SeasonalityRecord,
    SerpResult,
    VolumeRecord,
)

log = structlog.get_logger()

_BASE_URL = "https://api.dataforseo.com/v3"
_MAX_RETRIES = 3
_INITIAL_BACKOFF = 2.0


class DataForSEOProvider:
    """DataForSEO — SERP + true keyword difficulty. Feature-gated on env vars."""

    def __init__(self) -> None:
        self._client: httpx.Client | None = None

    @property
    def name(self) -> str:
        return "dataforseo"

    def is_available(self) -> bool:
        return settings.dataforseo_available

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=_BASE_URL,
                auth=(settings.dataforseo_login, settings.dataforseo_password),
                timeout=60.0,
            )
        return self._client

    def _request(
        self, method: str, path: str, json: Any = None
    ) -> dict[str, Any]:
        """Make a request with exponential backoff on 429/5xx."""
        client = self._get_client()
        backoff = _INITIAL_BACKOFF
        for attempt in range(_MAX_RETRIES):
            resp = client.request(method, path, json=json)
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = backoff * (2**attempt)
                log.warning(
                    "dataforseo_retry",
                    path=path, status=resp.status_code, wait=wait,
                )
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()
        return {}

    def expand_keywords(
        self, seeds: list[str], geo: str = "US", language: str = "en"
    ) -> list[KeywordIdea]:
        """Google Ads provider covers keyword expansion.

        DataForSEO's keyword_suggestions endpoint is available but Google Ads
        provides better data for accounts with high spend (precise volumes).

        Raises:
            NotImplementedError: Use Google Ads provider for keyword expansion.
        """
        raise NotImplementedError(
            "Google Ads provider covers keyword expansion with precise volumes. "
            "DataForSEO integration is optional for this method."
        )

    def get_search_volume(self, keywords: list[str]) -> list[VolumeRecord]:
        """Google Ads provider covers search volume with precise data.

        Raises:
            NotImplementedError: Use Google Ads provider.
        """
        raise NotImplementedError(
            "Google Ads provider covers search volume with precise monthly data. "
            "DataForSEO integration is optional for this method."
        )

    def get_keyword_difficulty(self, keywords: list[str]) -> list[DifficultyRecord]:
        """Get true SEO difficulty from DataForSEO Labs API.

        Unlike Google Ads competition_index (ad auction competition), this returns
        actual SEO difficulty based on backlink profiles and domain authority of
        currently ranking pages.
        """
        if not self.is_available():
            return []

        payload = [{
            "keywords": keywords,
            "language_code": "en",
            "location_code": 2840,  # United States
        }]

        try:
            data = self._request("POST", "/dataforseo_labs/google/keyword_difficulty/live", json=payload)
            results: list[DifficultyRecord] = []
            for task in data.get("tasks", []):
                for item in task.get("result", []) or []:
                    results.append(DifficultyRecord(
                        keyword=item.get("keyword", ""),
                        difficulty=item.get("keyword_difficulty", 0),
                        source="seo_difficulty",
                    ))
            return results
        except Exception as e:
            log.error("dataforseo_difficulty_failed", error=str(e))
            return []

    def get_serp(self, keyword: str) -> SerpResult:
        """Get organic SERP snapshot from DataForSEO.

        Hits Google Organic endpoint (Standard Queue). This is the primary
        capability that Google Ads API cannot provide — full organic SERP
        with rankings, snippets, featured snippets, and PAA boxes.
        """
        if not self.is_available():
            return SerpResult(keyword=keyword, source="dataforseo")

        payload = [{
            "keyword": keyword,
            "language_code": "en",
            "location_code": 2840,
            "device": "desktop",
            "os": "windows",
        }]

        try:
            data = self._request("POST", "/serp/google/organic/live/regular", json=payload)
            organic = []
            featured = None
            paa = []

            for task in data.get("tasks", []):
                for result in task.get("result", []) or []:
                    for item in result.get("items", []) or []:
                        item_type = item.get("type", "")
                        if item_type == "organic":
                            organic.append({
                                "position": item.get("rank_absolute"),
                                "url": item.get("url", ""),
                                "title": item.get("title", ""),
                                "description": item.get("description", ""),
                                "domain": item.get("domain", ""),
                            })
                        elif item_type == "featured_snippet":
                            featured = {
                                "url": item.get("url", ""),
                                "title": item.get("title", ""),
                                "description": item.get("description", ""),
                            }
                        elif item_type == "people_also_ask":
                            for q in item.get("items", []) or []:
                                paa.append(q.get("title", ""))

            return SerpResult(
                keyword=keyword,
                organic_results=organic[:10],
                featured_snippet=featured,
                people_also_ask=paa[:5],
                source="dataforseo",
            )
        except Exception as e:
            log.error("dataforseo_serp_failed", keyword=keyword, error=str(e))
            return SerpResult(keyword=keyword, source="dataforseo")

    def get_related(self, keyword: str) -> RelatedQuery:
        """Google Ads provider covers related keywords.

        Raises:
            NotImplementedError: Use Google Ads provider.
        """
        raise NotImplementedError(
            "Google Ads provider covers related keywords. "
            "DataForSEO integration is optional for this method."
        )

    def get_seasonality(self, keyword: str) -> SeasonalityRecord:
        """Google Ads historical metrics covers seasonality.

        Raises:
            NotImplementedError: Use Google Ads or Trends provider.
        """
        raise NotImplementedError(
            "Google Ads provider covers seasonality via historical metrics. "
            "DataForSEO integration is optional for this method."
        )

    def get_ranked_keywords_for_competitor(
        self, domain: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get keywords a competitor domain ranks for — gap analysis.

        Returns keywords the competitor ranks for that naturesseed may not,
        enabling "what do they rank for that we don't" discovery.
        """
        if not self.is_available():
            return []

        payload = [{
            "target": domain,
            "language_code": "en",
            "location_code": 2840,
            "limit": limit,
            "order_by": ["keyword_data.keyword_info.search_volume,desc"],
        }]

        try:
            data = self._request(
                "POST",
                "/dataforseo_labs/google/ranked_keywords/live",
                json=payload,
            )
            keywords = []
            for task in data.get("tasks", []):
                for item in task.get("result", []) or []:
                    for kw in item.get("items", []) or []:
                        kw_data = kw.get("keyword_data", {})
                        kw_info = kw_data.get("keyword_info", {})
                        keywords.append({
                            "keyword": kw_data.get("keyword", ""),
                            "search_volume": kw_info.get("search_volume"),
                            "position": kw.get("ranked_serp_element", {}).get(
                                "serp_item", {}
                            ).get("rank_absolute"),
                            "url": kw.get("ranked_serp_element", {}).get(
                                "serp_item", {}
                            ).get("url", ""),
                        })
            return keywords
        except Exception as e:
            log.error("dataforseo_competitor_kw_failed", domain=domain, error=str(e))
            return []

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
