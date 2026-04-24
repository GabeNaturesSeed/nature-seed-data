"""Google Ads Keyword Planner provider.

Uses the official google-ads Python library with Application Default Credentials (ADC).
Naturesseed's $40k/mo spend unlocks precise (non-ranged) search volumes.

Auth: gcloud CLI login sets up ADC; we read GOOGLE_ADS_DEVELOPER_TOKEN from .env.
"""

from __future__ import annotations

from typing import Any

import structlog

from naturesseed_pipeline.config import settings
from naturesseed_pipeline.integrations.keyword_research.base import (
    CompetitorDomainRecord,
    DifficultyRecord,
    KeywordIdea,
    RelatedQuery,
    SeasonalityRecord,
    SerpResult,
    VolumeRecord,
)

log = structlog.get_logger()

# Month name mapping for historical metrics
_MONTH_NAMES = {
    1: "JANUARY", 2: "FEBRUARY", 3: "MARCH", 4: "APRIL",
    5: "MAY", 6: "JUNE", 7: "JULY", 8: "AUGUST",
    9: "SEPTEMBER", 10: "OCTOBER", 11: "NOVEMBER", 12: "DECEMBER",
}
_MONTH_NUMBERS = {v: k for k, v in _MONTH_NAMES.items()}


def _get_ads_client():
    """Create a GoogleAdsClient using ADC + developer token."""
    from google.ads.googleads.client import GoogleAdsClient

    config = {
        "developer_token": settings.google_ads_developer_token,
        "use_proto_plus": True,
    }
    if settings.google_ads_login_customer_id:
        config["login_customer_id"] = settings.google_ads_login_customer_id

    return GoogleAdsClient.load_from_dict(config)


class GoogleAdsProvider:
    """Keyword Planner via Google Ads API — precise volumes for high-spend accounts."""

    @property
    def name(self) -> str:
        return "google_ads"

    def is_available(self) -> bool:
        return settings.google_ads_available

    def _customer_id(self) -> str:
        return settings.google_ads_customer_id.replace("-", "").replace(" ", "")

    def expand_keywords(
        self, seeds: list[str], geo: str = "US", language: str = "en"
    ) -> list[KeywordIdea]:
        """Generate keyword ideas from seed keywords via Keyword Planner.

        Returns ideas with precise monthly search volumes (unlocked by naturesseed's
        $40k/month ad spend — accounts with lower spend get ranged data).
        """
        client = _get_ads_client()
        service = client.get_service("KeywordPlanIdeaService")

        # Build geo/language resource names
        geo_target = client.get_service("GeoTargetConstantService")
        language_rn = f"languageConstants/1000"  # English
        geo_rn = f"geoTargetConstants/2840"  # United States

        request = client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = self._customer_id()
        request.language = language_rn
        request.geo_target_constants.append(geo_rn)
        request.keyword_plan_network = (
            client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        )
        request.keyword_seed.keywords.extend(seeds)

        ideas: list[KeywordIdea] = []
        try:
            response = service.generate_keyword_ideas(request=request)
            for result in response:
                metrics = result.keyword_idea_metrics
                ideas.append(KeywordIdea(
                    keyword=result.text,
                    search_volume=metrics.avg_monthly_searches or 0,
                    competition_index=metrics.competition_index or 0,
                    cpc_low=metrics.low_top_of_page_bid_micros / 1_000_000
                    if metrics.low_top_of_page_bid_micros else None,
                    cpc_high=metrics.high_top_of_page_bid_micros / 1_000_000
                    if metrics.high_top_of_page_bid_micros else None,
                    source="google_ads",
                ))
        except Exception as e:
            log.error("google_ads_expand_failed", error=str(e))

        log.info("google_ads_expand", seeds=seeds, results=len(ideas))
        return ideas

    def get_search_volume(self, keywords: list[str]) -> list[VolumeRecord]:
        """Get historical monthly search volumes via Keyword Planner.

        Returns 12 months of monthly breakdowns with precise volumes.
        """
        client = _get_ads_client()
        service = client.get_service("KeywordPlanIdeaService")

        request = client.get_type("GenerateKeywordHistoricalMetricsRequest")
        request.customer_id = self._customer_id()
        request.keywords.extend(keywords)
        request.keyword_plan_network = (
            client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        )

        records: list[VolumeRecord] = []
        try:
            response = service.generate_keyword_historical_metrics(request=request)
            for result in response.results:
                monthly = []
                for m in result.keyword_metrics.monthly_search_volumes:
                    month_num = _MONTH_NUMBERS.get(m.month.name, 0)
                    monthly.append({
                        "year": m.year,
                        "month": month_num,
                        "volume": m.monthly_searches,
                    })
                records.append(VolumeRecord(
                    keyword=result.text,
                    monthly_volumes=monthly,
                    avg_monthly_volume=result.keyword_metrics.avg_monthly_searches,
                    source="google_ads",
                ))
        except Exception as e:
            log.error("google_ads_volume_failed", error=str(e))

        return records

    def get_keyword_difficulty(self, keywords: list[str]) -> list[DifficultyRecord]:
        """Return competition_index from Ads as a difficulty proxy.

        NOTE: This is AD AUCTION competition (0-100), NOT SEO difficulty.
        Stored with source='ads_competition' so downstream scoring knows the difference.
        For true SEO difficulty, enable DataForSEO.
        """
        ideas = self.expand_keywords(keywords)
        return [
            DifficultyRecord(
                keyword=idea.keyword,
                difficulty=idea.competition_index or 0,
                source="ads_competition",
            )
            for idea in ideas
            if idea.keyword.lower() in {k.lower() for k in keywords}
        ]

    def get_serp(self, keyword: str) -> SerpResult:
        """Google Ads API does not return organic SERP data.

        Use DataForSEO provider for organic SERP results. Google Ads only provides
        ad auction metrics (competition_index, CPC estimates). For organic rankings,
        GSC provides own-site data, and DataForSEO provides full SERP snapshots.

        Raises:
            NotImplementedError: Always — this capability requires DataForSEO.
        """
        raise NotImplementedError(
            "Google Ads API does not provide organic SERP data. "
            "Enable DataForSEO for SERP snapshots."
        )

    def get_related(self, keyword: str) -> RelatedQuery:
        """Get related keywords from Keyword Planner expansion."""
        ideas = self.expand_keywords([keyword])
        return RelatedQuery(
            seed_keyword=keyword,
            related=[i.keyword for i in ideas if i.keyword.lower() != keyword.lower()][:20],
            source="google_ads",
        )

    def get_seasonality(self, keyword: str) -> SeasonalityRecord:
        """Get seasonality from historical monthly volumes.

        Ads historical metrics provide 12+ months of per-month data, which is
        the primary seasonality signal (more reliable than Google Trends).
        """
        volumes = self.get_search_volume([keyword])
        if not volumes:
            return SeasonalityRecord(keyword=keyword, monthly_data=[], source="google_ads")

        vol = volumes[0]
        peak_months = []
        if vol.monthly_volumes:
            avg = sum(m["volume"] for m in vol.monthly_volumes) / len(vol.monthly_volumes)
            peak_months = [
                m["month"] for m in vol.monthly_volumes
                if m["volume"] > avg * 1.3  # 30% above average = peak
            ]

        return SeasonalityRecord(
            keyword=keyword,
            monthly_data=vol.monthly_volumes,
            peak_months=sorted(set(peak_months)),
            source="google_ads",
        )

    def get_competitor_domains(self, keywords: list[str]) -> list[CompetitorDomainRecord]:
        """Pull competitor domains from Ads auction insights.

        This is valuable with naturesseed's spend — we see which domains bid on
        the same keywords. Writes to competitor_domains table.

        Uses search_terms_view to find domains appearing in auction insights
        for our top keywords.
        """
        client = _get_ads_client()
        ga_service = client.get_service("GoogleAdsService")
        customer_id = self._customer_id()

        domain_counts: dict[str, int] = {}
        try:
            # Query auction insights for the account
            query = """
                SELECT
                    auction_insights.display_domain,
                    metrics.impressions
                FROM auction_insights
                WHERE segments.date DURING LAST_90_DAYS
                ORDER BY metrics.impressions DESC
                LIMIT 100
            """
            response = ga_service.search(customer_id=customer_id, query=query)
            for row in response:
                domain = row.auction_insights.display_domain
                if domain and domain != "naturesseed.com":
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
        except Exception as e:
            log.error("google_ads_competitor_failed", error=str(e))

        return [
            CompetitorDomainRecord(
                domain=domain,
                keyword_overlap_count=count,
                source="ads_auction",
            )
            for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1])
        ]
