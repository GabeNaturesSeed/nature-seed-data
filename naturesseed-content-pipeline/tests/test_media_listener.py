"""Tests for media listener: sources, classification, pipeline, dedup, promotion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from naturesseed_pipeline.agents.media_listener import classify_signal, _extract_topic
from naturesseed_pipeline.db.models import Base, KeywordCandidate, MediaSignal
from naturesseed_pipeline.integrations.media_sources import (
    RawSignal,
    fetch_rss,
    fetch_trends,
    load_media_config,
)
from naturesseed_pipeline.pipelines.research_media import (
    get_top_signals,
    promote_signals_to_keywords,
    run_listener_sweep,
    list_sources,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_signal(
    title: str = "How to Start Seeds Indoors",
    text: str = "A beginner's guide to seed starting in 2025",
    source_type: str = "youtube",
    source_name: str = "Epic Gardening",
    url: str = "https://youtube.com/watch?v=abc123",
    published_at: datetime | None = None,
) -> RawSignal:
    return RawSignal(
        source_type=source_type,
        source_name=source_name,
        title=title,
        url=url,
        text=text,
        published_at=published_at or datetime.now(timezone.utc),
    )


# ── Classification tests ─────────────────────────────────────────────────────

def test_classify_high_relevance_gardening_signal():
    """Gardening seed-starting content should score high relevance."""
    signal = _make_signal(
        title="Seed Starting Guide 2025 — Best Heirloom Tomato Seeds",
        text="Complete guide to germination, planting zones, and organic seed saving."
    )
    result = classify_signal(signal)
    assert result["relevance_score"] >= 0.7
    assert isinstance(result["topic"], str)
    assert len(result["topic"]) > 0


def test_classify_low_relevance_unrelated():
    """Unrelated content should score low relevance."""
    signal = _make_signal(
        title="Best Budget Smartphones of 2025",
        text="Samsung vs iPhone comparison review."
    )
    result = classify_signal(signal)
    assert result["relevance_score"] < 0.3


def test_classify_trending_signal():
    """Recent content with trend keywords should score high trending."""
    signal = _make_signal(
        title="Trending: Viral New Gardening Method Takes 2025 by Storm",
        text="This game-changer technique just released and everyone is surprised.",
        published_at=datetime.now(timezone.utc) - timedelta(hours=12),
    )
    result = classify_signal(signal)
    assert result["trending_score"] >= 0.5


def test_classify_stale_signal():
    """Old content should have lower trending score."""
    signal = _make_signal(
        title="How to Grow Tomatoes",
        text="Basic tomato growing tips.",
        published_at=datetime.now(timezone.utc) - timedelta(days=60),
    )
    result = classify_signal(signal)
    assert result["trending_score"] < 0.5


def test_classify_reddit_gardening_boost():
    """Signals from gardening subreddits get a relevance boost."""
    signal = _make_signal(
        source_type="reddit",
        source_name="r/gardening",
        title="My first garden this year",
        text="I planted some stuff",
    )
    result = classify_signal(signal)
    # Should get boosted above a generic source with same text
    generic = _make_signal(
        source_type="rss",
        source_name="Random Blog",
        title="My first garden this year",
        text="I planted some stuff",
    )
    generic_result = classify_signal(generic)
    assert result["relevance_score"] >= generic_result["relevance_score"]


# ── Topic extraction ──────────────────────────────────────────────────────────

def test_extract_topic_strips_prefix():
    assert _extract_topic("How to Start Seeds Indoors") == "start seeds indoors"
    assert _extract_topic("The Best Cover Crops for 2025") == "cover crops for 2025"


def test_extract_topic_trims_at_separator():
    assert _extract_topic("Seed Starting — A Complete Guide") == "seed starting"
    assert _extract_topic("Garden Tips: Spring Edition") == "garden tips"


def test_extract_topic_caps_length():
    long_title = " ".join(["word"] * 20)
    topic = _extract_topic(long_title)
    assert len(topic.split()) <= 8


# ── Pipeline: listener sweep ─────────────────────────────────────────────────

def test_listener_sweep_stores_signals(db_session: Session):
    """Listener sweep should classify and store signals."""
    signals = [
        _make_signal(
            title="Seed Starting Guide",
            text="Complete guide to germination",
            url="https://example.com/1",
        ),
        _make_signal(
            title="Best Lawn Seed Review",
            text="Comparing grass seed mixes",
            url="https://example.com/2",
            source_type="rss",
            source_name="Garden Blog",
        ),
    ]

    result = run_listener_sweep(db_session, signals=signals)
    assert result["new_signals"] == 2

    all_signals = db_session.execute(select(MediaSignal)).scalars().all()
    assert len(all_signals) == 2
    assert all(s.relevance_score is not None for s in all_signals)
    assert all(s.trending_score is not None for s in all_signals)


def test_listener_sweep_dedup_by_url(db_session: Session):
    """Same URL should not be stored twice."""
    signals = [
        _make_signal(url="https://example.com/same"),
        _make_signal(title="Different Title", url="https://example.com/same"),
    ]

    result = run_listener_sweep(db_session, signals=signals)
    assert result["new_signals"] == 1

    # Run again with same URL
    result2 = run_listener_sweep(db_session, signals=signals)
    assert result2["new_signals"] == 0

    total = len(db_session.execute(select(MediaSignal)).scalars().all())
    assert total == 1


def test_listener_sweep_counts_by_source(db_session: Session):
    """Counts should be grouped by source type."""
    signals = [
        _make_signal(source_type="youtube", url="https://yt.com/1"),
        _make_signal(source_type="youtube", url="https://yt.com/2"),
        _make_signal(source_type="reddit", url="https://reddit.com/1"),
        _make_signal(source_type="rss", url="https://blog.com/1"),
    ]

    result = run_listener_sweep(db_session, signals=signals)
    assert result["by_source"]["youtube"] == 2
    assert result["by_source"]["reddit"] == 1
    assert result["by_source"]["rss"] == 1


# ── Top signals ───────────────────────────────────────────────────────────────

def test_get_top_signals(db_session: Session):
    """Top signals should be sorted by combined score."""
    now = datetime.now(timezone.utc)
    db_session.add(MediaSignal(
        source_type="youtube", title="High Signal",
        url="https://a.com", relevance_score=0.9, trending_score=0.8,
        captured_at=now,
    ))
    db_session.add(MediaSignal(
        source_type="rss", title="Low Signal",
        url="https://b.com", relevance_score=0.2, trending_score=0.1,
        captured_at=now,
    ))
    db_session.commit()

    signals = get_top_signals(db_session, since_days=7)
    assert len(signals) == 2
    assert signals[0].title == "High Signal"


def test_get_top_signals_filters_old(db_session: Session):
    """Old signals should be filtered out."""
    old = datetime.now(timezone.utc) - timedelta(days=30)
    db_session.add(MediaSignal(
        source_type="youtube", title="Old",
        url="https://old.com", relevance_score=0.9, trending_score=0.9,
        captured_at=old,
    ))
    db_session.commit()

    signals = get_top_signals(db_session, since_days=7)
    assert len(signals) == 0


# ── Promotion to keywords ────────────────────────────────────────────────────

def test_promote_signals_to_keywords(db_session: Session):
    """High-scoring signals should promote topics to keyword_candidates."""
    now = datetime.now(timezone.utc)
    db_session.add(MediaSignal(
        source_type="youtube",
        title="Wildflower Seed Starting Revolution",
        url="https://yt.com/1",
        captured_text="New method for wildflower seed germination",
        relevance_score=0.9,
        trending_score=0.8,
        captured_at=now,
        status="new",
    ))
    db_session.add(MediaSignal(
        source_type="reddit",
        title="Best Smartphone Deals",
        url="https://reddit.com/2",
        captured_text="Phones on sale",
        relevance_score=0.1,
        trending_score=0.1,
        captured_at=now,
        status="new",
    ))
    db_session.commit()

    result = promote_signals_to_keywords(db_session, min_relevance=0.7, min_trend=0.6)
    assert result["promoted"] >= 1
    assert result["eligible"] == 1

    candidates = db_session.execute(select(KeywordCandidate)).scalars().all()
    assert len(candidates) >= 1
    assert any("media_" in (c.source or "") for c in candidates)

    # Signal should be marked promoted
    promoted_signal = db_session.execute(
        select(MediaSignal).where(MediaSignal.url == "https://yt.com/1")
    ).scalar_one()
    assert promoted_signal.status == "promoted"


def test_promote_no_duplicate_keywords(db_session: Session):
    """Promotion should not create duplicate keyword_candidates."""
    now = datetime.now(timezone.utc)
    # Pre-populate keyword
    db_session.add(KeywordCandidate(keyword="seed starting", source="google_ads"))
    db_session.add(MediaSignal(
        source_type="youtube",
        title="Seed Starting Tips",
        url="https://yt.com/1",
        captured_text="seed starting guide",
        relevance_score=0.9,
        trending_score=0.8,
        captured_at=now,
        status="new",
    ))
    db_session.commit()

    result = promote_signals_to_keywords(db_session)

    # Should not create a second "seed starting" candidate
    candidates = db_session.execute(
        select(KeywordCandidate).where(KeywordCandidate.keyword == "seed starting")
    ).scalars().all()
    assert len(candidates) == 1


# ── Config loading ────────────────────────────────────────────────────────────

def test_load_media_config():
    """Config should load from YAML."""
    config = load_media_config("config/media_sources.yaml")
    assert "youtube" in config
    assert "reddit" in config
    assert "rss" in config
    assert "trends" in config
    assert len(config["youtube"]["channels"]) >= 1
    assert len(config["reddit"]["subreddits"]) >= 3


def test_list_sources():
    """list_sources should return all source types."""
    sources = list_sources("config/media_sources.yaml")
    assert "youtube" in sources
    assert "reddit" in sources
    assert "rss" in sources
    assert "trends" in sources


# ── RSS fetch (no external call — uses feedparser on any valid XML) ──────────

def test_rss_fetch_handles_empty_config():
    """RSS fetch with empty config should return empty list."""
    signals = fetch_rss(config={"rss": {"feeds": []}})
    assert signals == []


# ── Trends fetch (non-fatal failure) ─────────────────────────────────────────

def test_trends_fetch_handles_failure():
    """Trends fetch should return empty on failure, not crash."""
    # Pass a config that would trigger a trends query — may fail due to no API
    # but should not raise
    signals = fetch_trends(config={"trends": {"category": 11, "geo": "US"}})
    assert isinstance(signals, list)  # may be empty, but shouldn't crash
