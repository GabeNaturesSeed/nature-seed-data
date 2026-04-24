"""Provider abstraction for keyword research.

Defines the KeywordProvider protocol, shared data models, and the ResearchRouter
that dispatches method calls to providers based on a configurable priority list.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

import structlog
from pydantic import BaseModel

log = structlog.get_logger()


# ── Data models ───────────────────────────────────────────────────────────────

class KeywordIdea(BaseModel):
    keyword: str
    search_volume: int | None = None
    competition_index: float | None = None  # 0-100, from Ads auction
    cpc_low: float | None = None
    cpc_high: float | None = None
    source: str = "unknown"


class VolumeRecord(BaseModel):
    keyword: str
    monthly_volumes: list[dict[str, Any]]  # [{year, month, volume}, ...]
    avg_monthly_volume: int | None = None
    source: str = "unknown"


class DifficultyRecord(BaseModel):
    keyword: str
    difficulty: float  # 0-100
    source: str = "unknown"  # "ads_competition" or "seo_difficulty"


class SerpResult(BaseModel):
    keyword: str
    organic_results: list[dict[str, Any]] = []
    featured_snippet: dict[str, Any] | None = None
    people_also_ask: list[str] = []
    source: str = "unknown"


class RelatedQuery(BaseModel):
    seed_keyword: str
    related: list[str] = []
    source: str = "unknown"


class SeasonalityRecord(BaseModel):
    keyword: str
    monthly_data: list[dict[str, Any]]  # [{year, month, volume_or_interest}, ...]
    peak_months: list[int] = []
    source: str = "unknown"


class CompetitorDomainRecord(BaseModel):
    domain: str
    keyword_overlap_count: int = 0
    source: str = "ads_auction"


# ── Provider protocol ─────────────────────────────────────────────────────────

@runtime_checkable
class KeywordProvider(Protocol):
    """Protocol for keyword research data providers."""

    @property
    def name(self) -> str: ...

    def is_available(self) -> bool: ...

    def expand_keywords(
        self, seeds: list[str], geo: str = "US", language: str = "en"
    ) -> list[KeywordIdea]: ...

    def get_search_volume(self, keywords: list[str]) -> list[VolumeRecord]: ...

    def get_keyword_difficulty(self, keywords: list[str]) -> list[DifficultyRecord]: ...

    def get_serp(self, keyword: str) -> SerpResult: ...

    def get_related(self, keyword: str) -> RelatedQuery: ...

    def get_seasonality(self, keyword: str) -> SeasonalityRecord: ...


# ── Router ────────────────────────────────────────────────────────────────────

class ResearchRouter:
    """Dispatches keyword research calls to providers based on priority config.

    Priority is a dict like:
        {"volume": ["google_ads", "dataforseo"], "serp": ["dataforseo"]}

    For each method call, the router tries providers in priority order.
    If a provider is unavailable or raises NotImplementedError, it falls through
    to the next. If all fail, returns empty/default.
    """

    def __init__(
        self,
        providers: dict[str, KeywordProvider],
        priority: dict[str, list[str]],
    ) -> None:
        self._providers = providers
        self._priority = priority

    def _get_provider(self, method: str) -> KeywordProvider | None:
        """Return the first available provider for a method."""
        for name in self._priority.get(method, []):
            provider = self._providers.get(name)
            if provider and provider.is_available():
                return provider
            if provider and not provider.is_available():
                log.debug("provider_unavailable", provider=name, method=method)
        log.warning("no_provider_available", method=method)
        return None

    def expand_keywords(
        self, seeds: list[str], geo: str = "US", language: str = "en"
    ) -> list[KeywordIdea]:
        provider = self._get_provider("expand")
        if not provider:
            return []
        try:
            return provider.expand_keywords(seeds, geo, language)
        except NotImplementedError:
            log.warning("not_implemented", provider=provider.name, method="expand_keywords")
            return []

    def get_search_volume(self, keywords: list[str]) -> list[VolumeRecord]:
        provider = self._get_provider("volume")
        if not provider:
            return []
        try:
            return provider.get_search_volume(keywords)
        except NotImplementedError:
            log.warning("not_implemented", provider=provider.name, method="get_search_volume")
            return []

    def get_keyword_difficulty(self, keywords: list[str]) -> list[DifficultyRecord]:
        provider = self._get_provider("difficulty")
        if not provider:
            return []
        try:
            return provider.get_keyword_difficulty(keywords)
        except NotImplementedError:
            log.warning("not_implemented", provider=provider.name, method="get_keyword_difficulty")
            return []

    def get_serp(self, keyword: str) -> SerpResult | None:
        provider = self._get_provider("serp")
        if not provider:
            return None
        try:
            return provider.get_serp(keyword)
        except NotImplementedError:
            log.warning("not_implemented", provider=provider.name, method="get_serp")
            return None

    def get_related(self, keyword: str) -> RelatedQuery | None:
        provider = self._get_provider("related")
        if not provider:
            return None
        try:
            return provider.get_related(keyword)
        except NotImplementedError:
            log.warning("not_implemented", provider=provider.name, method="get_related")
            return None

    def get_seasonality(self, keyword: str) -> SeasonalityRecord | None:
        provider = self._get_provider("seasonality")
        if not provider:
            return None
        try:
            return provider.get_seasonality(keyword)
        except NotImplementedError:
            log.warning("not_implemented", provider=provider.name, method="get_seasonality")
            return None

    def get_active_providers(self) -> dict[str, bool]:
        """Return availability status of all registered providers."""
        return {name: p.is_available() for name, p in self._providers.items()}
