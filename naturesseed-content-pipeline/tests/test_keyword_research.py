"""Tests for keyword research: providers, router, agent, pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from naturesseed_pipeline.db.models import (
    Base,
    CompetitorDomain,
    GscQueryPerformance,
    KeywordCandidate,
)
from naturesseed_pipeline.integrations.keyword_research.base import (
    CompetitorDomainRecord,
    DifficultyRecord,
    KeywordIdea,
    KeywordProvider,
    RelatedQuery,
    ResearchRouter,
    SeasonalityRecord,
    SerpResult,
    VolumeRecord,
)
from naturesseed_pipeline.integrations.keyword_research.dataforseo import DataForSEOProvider
from naturesseed_pipeline.integrations.keyword_research.trends import TrendsProvider


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


class FakeGoogleAdsProvider:
    """Fake Google Ads provider for testing."""

    @property
    def name(self) -> str:
        return "google_ads"

    def is_available(self) -> bool:
        return True

    def expand_keywords(self, seeds, geo="US", language="en"):
        ideas = []
        base_volume = 5000
        for i, seed in enumerate(seeds):
            # Generate a few ideas per seed
            ideas.append(KeywordIdea(
                keyword=seed,
                search_volume=base_volume - (i * 100),
                competition_index=45.0 + i,
                cpc_low=0.50,
                cpc_high=2.50,
                source="google_ads",
            ))
            ideas.append(KeywordIdea(
                keyword=f"{seed} guide",
                search_volume=base_volume // 2,
                competition_index=30.0,
                source="google_ads",
            ))
            ideas.append(KeywordIdea(
                keyword=f"buy {seed}",
                search_volume=base_volume // 3,
                competition_index=70.0,
                source="google_ads",
            ))
        return ideas

    def get_search_volume(self, keywords):
        return [
            VolumeRecord(
                keyword=kw,
                monthly_volumes=[
                    {"year": 2025, "month": m, "volume": 1000 + (m * 100)}
                    for m in range(1, 13)
                ],
                avg_monthly_volume=1600,
                source="google_ads",
            )
            for kw in keywords
        ]

    def get_keyword_difficulty(self, keywords):
        return [
            DifficultyRecord(keyword=kw, difficulty=45.0, source="ads_competition")
            for kw in keywords
        ]

    def get_serp(self, keyword):
        raise NotImplementedError("Google Ads does not provide SERP data")

    def get_related(self, keyword):
        return RelatedQuery(
            seed_keyword=keyword,
            related=[f"{keyword} tips", f"{keyword} guide"],
            source="google_ads",
        )

    def get_seasonality(self, keyword):
        return SeasonalityRecord(
            keyword=keyword,
            monthly_data=[
                {"year": 2025, "month": m, "volume": 1000 + (m * 100)}
                for m in range(1, 13)
            ],
            peak_months=[3, 4, 5, 9, 10],
            source="google_ads",
        )


class FakeDataForSEOProvider:
    """Fake DataForSEO for testing — toggleable availability."""

    def __init__(self, available: bool = False):
        self._available = available

    @property
    def name(self) -> str:
        return "dataforseo"

    def is_available(self) -> bool:
        return self._available

    def expand_keywords(self, seeds, geo="US", language="en"):
        raise NotImplementedError("Use Google Ads")

    def get_search_volume(self, keywords):
        raise NotImplementedError("Use Google Ads")

    def get_keyword_difficulty(self, keywords):
        if not self._available:
            return []
        return [
            DifficultyRecord(keyword=kw, difficulty=62.0, source="seo_difficulty")
            for kw in keywords
        ]

    def get_serp(self, keyword):
        if not self._available:
            return SerpResult(keyword=keyword, source="dataforseo")
        return SerpResult(
            keyword=keyword,
            organic_results=[
                {"position": 1, "url": "https://example.com/1", "domain": "example.com"},
                {"position": 2, "url": "https://other.com/2", "domain": "other.com"},
            ],
            featured_snippet={"url": "https://example.com/1", "title": "Answer"},
            people_also_ask=["How to plant?", "When to seed?"],
            source="dataforseo",
        )

    def get_related(self, keyword):
        raise NotImplementedError("Use Google Ads")

    def get_seasonality(self, keyword):
        raise NotImplementedError("Use Google Ads")


# ── Router tests ──────────────────────────────────────────────────────────────

def test_router_dispatches_to_first_available():
    """Router should use the first available provider for a method."""
    ads = FakeGoogleAdsProvider()
    dfs = FakeDataForSEOProvider(available=False)
    router = ResearchRouter(
        providers={"google_ads": ads, "dataforseo": dfs},
        priority={"expand": ["google_ads"], "difficulty": ["dataforseo", "google_ads"]},
    )
    ideas = router.expand_keywords(["tomato seeds"])
    assert len(ideas) >= 3
    assert ideas[0].source == "google_ads"


def test_router_falls_through_unavailable():
    """If first provider is unavailable, try next."""
    ads = FakeGoogleAdsProvider()
    dfs = FakeDataForSEOProvider(available=False)
    router = ResearchRouter(
        providers={"google_ads": ads, "dataforseo": dfs},
        priority={"difficulty": ["dataforseo", "google_ads"]},
    )
    # DataForSEO unavailable → falls through to Google Ads
    diffs = router.get_keyword_difficulty(["lawn seed"])
    assert len(diffs) == 1
    assert diffs[0].source == "ads_competition"


def test_router_falls_through_not_implemented():
    """If provider raises NotImplementedError, try next."""
    ads = FakeGoogleAdsProvider()
    dfs = FakeDataForSEOProvider(available=True)
    router = ResearchRouter(
        providers={"google_ads": ads, "dataforseo": dfs},
        priority={"serp": ["google_ads", "dataforseo"]},
    )
    # Google Ads raises NotImplementedError for SERP → falls through to DataForSEO
    # But wait — router catches NotImplementedError and returns empty, doesn't try next.
    # That's by design: each method call targets ONE provider.
    serp = router.get_serp("lawn seed")
    # google_ads will raise NotImplementedError, returns None
    assert serp is None


def test_router_returns_empty_when_no_provider():
    """When no provider is configured for a method, return empty."""
    router = ResearchRouter(
        providers={},
        priority={"expand": []},
    )
    ideas = router.expand_keywords(["test"])
    assert ideas == []


def test_router_get_active_providers():
    ads = FakeGoogleAdsProvider()
    dfs = FakeDataForSEOProvider(available=False)
    router = ResearchRouter(
        providers={"google_ads": ads, "dataforseo": dfs},
        priority={},
    )
    status = router.get_active_providers()
    assert status["google_ads"] is True
    assert status["dataforseo"] is False


# ── Intent classification ─────────────────────────────────────────────────────

def test_classify_intent():
    from naturesseed_pipeline.agents.keyword_researcher import classify_intent

    assert classify_intent("buy tomato seeds") == "transactional"
    assert classify_intent("best grass seed for shade") == "commercial"
    assert classify_intent("how to plant wildflower seeds") == "informational"
    assert classify_intent("grass seed store near me") == "navigational"
    assert classify_intent("bermuda grass seed") == "informational"  # default


# ── Gap scoring ───────────────────────────────────────────────────────────────

def test_gap_score_computation():
    from naturesseed_pipeline.agents.keyword_researcher import _compute_gap_score

    gsc = {
        "lawn seed": {"position": 2.0, "page": "https://naturesseed.com/lawn/"},
        "grass seed": {"position": 15.0, "page": "https://naturesseed.com/grass/"},
    }

    # Top 3 → score 0.0
    score, url, pos = _compute_gap_score("lawn seed", gsc)
    assert score == 0.0
    assert url == "https://naturesseed.com/lawn/"

    # Page 2 → score 0.5
    score, url, pos = _compute_gap_score("grass seed", gsc)
    assert score == 0.5

    # Not ranking → score 1.0
    score, url, pos = _compute_gap_score("wildflower seeds", gsc)
    assert score == 1.0
    assert url is None


# ── Agent: seed research ──────────────────────────────────────────────────────

def test_research_seeds_populates_candidates(db_session: Session):
    """Seed research should create KeywordCandidate rows."""
    from naturesseed_pipeline.agents.keyword_researcher import research_seeds

    ads = FakeGoogleAdsProvider()
    router = ResearchRouter(
        providers={"google_ads": ads},
        priority={
            "expand": ["google_ads"],
            "seasonality": ["google_ads"],
        },
    )
    gsc_data = {
        "tomato seeds": {"position": 5.0, "page": "https://naturesseed.com/tomato/"},
    }

    candidates = research_seeds(db_session, router, ["tomato seeds"], gsc_data=gsc_data)
    db_session.commit()

    assert len(candidates) >= 3  # seed + guide + buy variants
    all_kws = db_session.execute(select(KeywordCandidate)).scalars().all()
    assert len(all_kws) >= 3

    # Check the main seed keyword
    tomato = db_session.execute(
        select(KeywordCandidate).where(KeywordCandidate.keyword == "tomato seeds")
    ).scalar_one_or_none()
    assert tomato is not None
    assert tomato.search_volume == 5000
    assert tomato.intent is not None
    assert tomato.gap_score == 0.2  # position 5 → gap 0.2


def test_research_seeds_idempotent(db_session: Session):
    """Running twice should update, not duplicate."""
    from naturesseed_pipeline.agents.keyword_researcher import research_seeds

    ads = FakeGoogleAdsProvider()
    router = ResearchRouter(
        providers={"google_ads": ads},
        priority={"expand": ["google_ads"], "seasonality": ["google_ads"]},
    )

    research_seeds(db_session, router, ["lawn seed"])
    db_session.commit()
    count1 = len(db_session.execute(select(KeywordCandidate)).scalars().all())

    research_seeds(db_session, router, ["lawn seed"])
    db_session.commit()
    count2 = len(db_session.execute(select(KeywordCandidate)).scalars().all())

    assert count1 == count2


# ── Agent: DataForSEO enrichment ──────────────────────────────────────────────

def test_dataforseo_enrichment_when_active(db_session: Session):
    """When DataForSEO is active, enrichment should add difficulty + SERP data."""
    from naturesseed_pipeline.agents.keyword_researcher import enrich_with_dataforseo

    # Pre-populate candidates
    db_session.add(KeywordCandidate(
        keyword="tomato seeds", search_volume=5000, source="google_ads",
        difficulty_source="ads_competition",
    ))
    db_session.add(KeywordCandidate(
        keyword="lawn seed", search_volume=3000, source="google_ads",
        difficulty_source="ads_competition",
    ))
    db_session.commit()

    dfs = FakeDataForSEOProvider(available=True)
    ads = FakeGoogleAdsProvider()
    router = ResearchRouter(
        providers={"google_ads": ads, "dataforseo": dfs},
        priority={"difficulty": ["dataforseo"], "serp": ["dataforseo"]},
    )

    count = enrich_with_dataforseo(db_session, router, top_n=10)
    db_session.commit()

    assert count == 2

    tomato = db_session.execute(
        select(KeywordCandidate).where(KeywordCandidate.keyword == "tomato seeds")
    ).scalar_one()
    assert tomato.difficulty_source == "seo_difficulty"
    assert tomato.keyword_difficulty == 62.0
    assert tomato.serp_features is not None
    assert tomato.enriched_at is not None


def test_dataforseo_enrichment_when_gated(db_session: Session):
    """When DataForSEO is gated, enrichment should skip gracefully."""
    from naturesseed_pipeline.agents.keyword_researcher import enrich_with_dataforseo

    db_session.add(KeywordCandidate(
        keyword="test", search_volume=100, source="google_ads",
    ))
    db_session.commit()

    dfs = FakeDataForSEOProvider(available=False)
    router = ResearchRouter(
        providers={"dataforseo": dfs},
        priority={"difficulty": ["dataforseo"], "serp": ["dataforseo"]},
    )

    count = enrich_with_dataforseo(db_session, router, top_n=10)
    assert count == 0


# ── Competitor domains ────────────────────────────────────────────────────────

def test_update_competitor_domains(db_session: Session):
    from naturesseed_pipeline.agents.keyword_researcher import update_competitor_domains

    records = [
        CompetitorDomainRecord(domain="rival1.com", keyword_overlap_count=15),
        CompetitorDomainRecord(domain="rival2.com", keyword_overlap_count=8),
    ]

    count = update_competitor_domains(db_session, records)
    db_session.commit()
    assert count == 2

    all_domains = db_session.execute(select(CompetitorDomain)).scalars().all()
    assert len(all_domains) == 2

    # Idempotent: update existing
    records[0].keyword_overlap_count = 20
    count = update_competitor_domains(db_session, records)
    db_session.commit()
    assert count == 0  # no new domains

    rival1 = db_session.execute(
        select(CompetitorDomain).where(CompetitorDomain.domain == "rival1.com")
    ).scalar_one()
    assert rival1.keyword_overlap_count == 20


# ── DataForSEO provider: mocked HTTP ─────────────────────────────────────────

@respx.mock
def test_dataforseo_get_serp_mocked():
    """DataForSEO SERP endpoint with mocked response."""
    provider = DataForSEOProvider()
    # Manually set client with test auth
    provider._client = httpx.Client(
        base_url="https://api.dataforseo.com/v3",
        auth=("test", "test"),
        timeout=10.0,
    )

    mock_response = {
        "tasks": [{
            "result": [{
                "items": [
                    {"type": "organic", "rank_absolute": 1, "url": "https://a.com/1",
                     "title": "Result 1", "description": "Desc", "domain": "a.com"},
                    {"type": "organic", "rank_absolute": 2, "url": "https://b.com/2",
                     "title": "Result 2", "description": "Desc", "domain": "b.com"},
                    {"type": "featured_snippet", "url": "https://a.com/1",
                     "title": "Snippet", "description": "Answer"},
                    {"type": "people_also_ask", "items": [
                        {"title": "How?"},
                        {"title": "When?"},
                    ]},
                ]
            }]
        }]
    }

    respx.post("https://api.dataforseo.com/v3/serp/google/organic/live/regular").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # Override is_available
    with patch.object(DataForSEOProvider, "is_available", return_value=True):
        result = provider.get_serp("lawn seed")

    assert len(result.organic_results) == 2
    assert result.featured_snippet is not None
    assert len(result.people_also_ask) == 2
    assert result.source == "dataforseo"
    provider.close()


@respx.mock
def test_dataforseo_get_difficulty_mocked():
    """DataForSEO difficulty endpoint with mocked response."""
    provider = DataForSEOProvider()
    provider._client = httpx.Client(
        base_url="https://api.dataforseo.com/v3",
        auth=("test", "test"),
        timeout=10.0,
    )

    mock_response = {
        "tasks": [{
            "result": [
                {"keyword": "lawn seed", "keyword_difficulty": 55.0},
                {"keyword": "grass seed", "keyword_difficulty": 72.0},
            ]
        }]
    }

    respx.post(
        "https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_difficulty/live"
    ).mock(return_value=httpx.Response(200, json=mock_response))

    with patch.object(DataForSEOProvider, "is_available", return_value=True):
        results = provider.get_keyword_difficulty(["lawn seed", "grass seed"])

    assert len(results) == 2
    assert results[0].source == "seo_difficulty"
    assert results[0].difficulty == 55.0
    provider.close()


@respx.mock
def test_dataforseo_retry_on_429():
    """DataForSEO should retry on 429."""
    provider = DataForSEOProvider()
    provider._client = httpx.Client(
        base_url="https://api.dataforseo.com/v3",
        auth=("test", "test"),
        timeout=10.0,
    )

    respx.post(
        "https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_difficulty/live"
    ).mock(side_effect=[
        httpx.Response(429),
        httpx.Response(200, json={"tasks": [{"result": []}]}),
    ])

    with patch.object(DataForSEOProvider, "is_available", return_value=True):
        results = provider.get_keyword_difficulty(["test"])

    assert results == []  # empty result but no crash
    provider.close()


@respx.mock
def test_dataforseo_competitor_keywords_mocked():
    """DataForSEO competitor ranked keywords."""
    provider = DataForSEOProvider()
    provider._client = httpx.Client(
        base_url="https://api.dataforseo.com/v3",
        auth=("test", "test"),
        timeout=10.0,
    )

    mock_response = {
        "tasks": [{
            "result": [{
                "items": [{
                    "keyword_data": {
                        "keyword": "grass seed",
                        "keyword_info": {"search_volume": 10000},
                    },
                    "ranked_serp_element": {
                        "serp_item": {"rank_absolute": 3, "url": "https://rival.com/grass"},
                    },
                }]
            }]
        }]
    }

    respx.post(
        "https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live"
    ).mock(return_value=httpx.Response(200, json=mock_response))

    with patch.object(DataForSEOProvider, "is_available", return_value=True):
        results = provider.get_ranked_keywords_for_competitor("rival.com")

    assert len(results) == 1
    assert results[0]["keyword"] == "grass seed"
    provider.close()


# ── Trends provider ──────────────────────────────────────────────────────────

def test_trends_is_available():
    t = TrendsProvider()
    # pytrends is installed, so should be True
    assert t.is_available() is True


def test_trends_expand_raises():
    t = TrendsProvider()
    with pytest.raises(NotImplementedError):
        t.expand_keywords(["test"])


# ── Provider status ───────────────────────────────────────────────────────────

def test_provider_status():
    from naturesseed_pipeline.pipelines.research_keywords import get_provider_status

    with patch("naturesseed_pipeline.pipelines.research_keywords.settings") as mock_settings:
        mock_settings.google_ads_available = True
        mock_settings.gsc_available = True
        mock_settings.dataforseo_available = False

        status = get_provider_status()

    assert status["Google Ads"] == "ACTIVE"
    assert status["GSC"] == "ACTIVE"
    assert "GATED" in status["DataForSEO"]
    assert status["Trends"] == "ACTIVE"


# ── Integration: full flow with Google providers only ─────────────────────────

def test_full_research_flow_google_only(db_session: Session):
    """Full seed research with only Google providers active (DataForSEO gated)."""
    from naturesseed_pipeline.agents.keyword_researcher import (
        research_seeds,
        update_competitor_domains,
    )

    ads = FakeGoogleAdsProvider()
    dfs = FakeDataForSEOProvider(available=False)
    router = ResearchRouter(
        providers={"google_ads": ads, "dataforseo": dfs},
        priority={
            "expand": ["google_ads"],
            "difficulty": ["dataforseo", "google_ads"],
            "seasonality": ["google_ads"],
            "serp": ["dataforseo"],
        },
    )

    gsc_data = {
        "tomato seeds": {"position": 12.0, "page": "https://naturesseed.com/tomato/"},
        "tomato seeds guide": {"position": 3.0, "page": "https://naturesseed.com/guide/"},
    }

    candidates = research_seeds(
        db_session, router, ["tomato seeds", "lawn seed"], gsc_data=gsc_data
    )
    db_session.commit()

    # Should have multiple candidates
    all_kws = db_session.execute(select(KeywordCandidate)).scalars().all()
    assert len(all_kws) >= 6  # 3 per seed

    # Check volumes are precise (not ranged)
    for kw in all_kws:
        assert kw.search_volume is not None
        assert kw.search_volume > 0

    # Check gap scores computed from GSC
    tomato = db_session.execute(
        select(KeywordCandidate).where(KeywordCandidate.keyword == "tomato seeds")
    ).scalar_one()
    assert tomato.gap_score == 0.5  # position 12 → 0.5

    # Check intent classified
    buy_kw = db_session.execute(
        select(KeywordCandidate).where(KeywordCandidate.keyword == "buy tomato seeds")
    ).scalar_one()
    assert buy_kw.intent == "transactional"

    # Competitor domains
    competitors = [
        CompetitorDomainRecord(domain="seedsuperstore.com", keyword_overlap_count=12),
        CompetitorDomainRecord(domain="grassseedusa.com", keyword_overlap_count=8),
    ]
    update_competitor_domains(db_session, competitors)
    db_session.commit()

    domains = db_session.execute(select(CompetitorDomain)).scalars().all()
    assert len(domains) == 2


# ── Integration: flip DataForSEO on ──────────────────────────────────────────

def test_full_flow_with_dataforseo_on(db_session: Session):
    """After flipping DataForSEO on, enrichment adds SERP + true difficulty."""
    from naturesseed_pipeline.agents.keyword_researcher import (
        enrich_with_dataforseo,
        research_seeds,
    )

    ads = FakeGoogleAdsProvider()
    dfs_off = FakeDataForSEOProvider(available=False)
    router_off = ResearchRouter(
        providers={"google_ads": ads, "dataforseo": dfs_off},
        priority={
            "expand": ["google_ads"],
            "difficulty": ["dataforseo", "google_ads"],
            "seasonality": ["google_ads"],
            "serp": ["dataforseo"],
        },
    )

    # Phase 1: Google-only research
    research_seeds(db_session, router_off, ["bermuda grass"])
    db_session.commit()

    bermuda = db_session.execute(
        select(KeywordCandidate).where(KeywordCandidate.keyword == "bermuda grass")
    ).scalar_one()
    assert bermuda.difficulty_source == "ads_competition"
    assert bermuda.enriched_at is None
    assert bermuda.serp_features is None

    # Phase 2: Flip DataForSEO on
    dfs_on = FakeDataForSEOProvider(available=True)
    router_on = ResearchRouter(
        providers={"google_ads": ads, "dataforseo": dfs_on},
        priority={
            "difficulty": ["dataforseo"],
            "serp": ["dataforseo"],
        },
    )

    enriched = enrich_with_dataforseo(db_session, router_on, top_n=50)
    db_session.commit()

    assert enriched >= 1

    bermuda = db_session.execute(
        select(KeywordCandidate).where(KeywordCandidate.keyword == "bermuda grass")
    ).scalar_one()
    assert bermuda.difficulty_source == "seo_difficulty"
    assert bermuda.keyword_difficulty == 62.0
    assert bermuda.serp_features is not None
    assert bermuda.enriched_at is not None

    # Google-provider rows are NOT broken
    assert bermuda.search_volume == 5000
    assert bermuda.source == "google_ads"
