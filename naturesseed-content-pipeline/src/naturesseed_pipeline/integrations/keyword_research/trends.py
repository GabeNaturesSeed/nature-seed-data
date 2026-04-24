"""Google Trends provider — supplementary seasonality data.

Uses pytrends for Google Trends interest-over-time data. This is a FALLBACK
for seasonality when Google Ads historical metrics aren't available.

pytrends breaks periodically when Google changes markup. All calls are wrapped
in try/except — failure is non-fatal and the pipeline continues without Trends.
"""

from __future__ import annotations

import structlog

from naturesseed_pipeline.integrations.keyword_research.base import (
    DifficultyRecord,
    KeywordIdea,
    RelatedQuery,
    SeasonalityRecord,
    SerpResult,
    VolumeRecord,
)

log = structlog.get_logger()


class TrendsProvider:
    """Google Trends — supplementary seasonality via pytrends."""

    @property
    def name(self) -> str:
        return "trends"

    def is_available(self) -> bool:
        """Always available (no auth needed) but may fail at runtime."""
        try:
            import pytrends  # noqa: F401
            return True
        except ImportError:
            return False

    def expand_keywords(
        self, seeds: list[str], geo: str = "US", language: str = "en"
    ) -> list[KeywordIdea]:
        raise NotImplementedError("Use Google Ads for keyword expansion.")

    def get_search_volume(self, keywords: list[str]) -> list[VolumeRecord]:
        raise NotImplementedError("Use Google Ads for precise search volumes.")

    def get_keyword_difficulty(self, keywords: list[str]) -> list[DifficultyRecord]:
        raise NotImplementedError("Use DataForSEO for SEO difficulty.")

    def get_serp(self, keyword: str) -> SerpResult:
        raise NotImplementedError("Use DataForSEO for SERP data.")

    def get_related(self, keyword: str) -> RelatedQuery:
        """Get related queries from Google Trends."""
        try:
            from pytrends.request import TrendReq

            pytrends = TrendReq(hl="en-US", tz=360)
            pytrends.build_payload([keyword], cat=0, timeframe="today 12-m", geo="US")
            related_df = pytrends.related_queries()

            related = []
            kw_data = related_df.get(keyword, {})
            for key in ["top", "rising"]:
                df = kw_data.get(key)
                if df is not None and not df.empty:
                    related.extend(df["query"].tolist()[:10])

            return RelatedQuery(
                seed_keyword=keyword,
                related=list(dict.fromkeys(related))[:20],
                source="trends",
            )
        except Exception as e:
            log.warning("trends_related_failed", keyword=keyword, error=str(e))
            return RelatedQuery(seed_keyword=keyword, related=[], source="trends")

    def get_seasonality(self, keyword: str) -> SeasonalityRecord:
        """Get interest-over-time from Google Trends as seasonality signal.

        NOTE: This returns relative interest (0-100 scale), not absolute volumes.
        Google Ads historical metrics provide actual search volumes and should be
        preferred as the primary seasonality signal.
        """
        try:
            from pytrends.request import TrendReq

            pytrends = TrendReq(hl="en-US", tz=360)
            pytrends.build_payload([keyword], cat=0, timeframe="today 12-m", geo="US")
            df = pytrends.interest_over_time()

            if df.empty:
                return SeasonalityRecord(
                    keyword=keyword, monthly_data=[], source="trends"
                )

            monthly_data = []
            for idx, row in df.iterrows():
                monthly_data.append({
                    "year": idx.year,
                    "month": idx.month,
                    "interest": int(row[keyword]),
                })

            # Identify peak months (> 1.3x average)
            if monthly_data:
                avg = sum(m["interest"] for m in monthly_data) / len(monthly_data)
                peak_months = sorted(set(
                    m["month"] for m in monthly_data if m["interest"] > avg * 1.3
                ))
            else:
                peak_months = []

            return SeasonalityRecord(
                keyword=keyword,
                monthly_data=monthly_data,
                peak_months=peak_months,
                source="trends",
            )
        except Exception as e:
            log.warning("trends_seasonality_failed", keyword=keyword, error=str(e))
            return SeasonalityRecord(
                keyword=keyword, monthly_data=[], source="trends"
            )
