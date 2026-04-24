"""Tests for keyword scoring and brief generation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from naturesseed_pipeline.db.models import (
    Base,
    BriefQueue,
    ContentInventory,
    KeywordCandidate,
    MediaSignal,
)
from naturesseed_pipeline.pipelines.scoring import (
    _norm_difficulty,
    _norm_intent,
    _norm_volume,
    _seasonality_boost,
    rank_backlog,
    score_keyword,
)
from naturesseed_pipeline.agents.brief_generator import (
    _build_outline,
    _generate_titles,
    _identify_citation_requirements,
    format_brief_markdown,
    generate_brief,
    generate_top_briefs,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_keyword(
    session: Session,
    keyword: str = "bermuda grass seed",
    volume: int = 5000,
    difficulty: float = 40.0,
    intent: str = "commercial",
    gap: float = 0.6,
    seasonality: dict | None = None,
) -> KeywordCandidate:
    kw = KeywordCandidate(
        keyword=keyword,
        search_volume=volume,
        keyword_difficulty=difficulty,
        difficulty_source="ads_competition",
        intent=intent,
        gap_score=gap,
        seasonality=seasonality or {"peak_months": [3, 4, 5, 9, 10]},
        source="google_ads",
        competition_index=40.0,
        status="new",
    )
    session.add(kw)
    session.flush()
    return kw


# ── Normalization functions ───────────────────────────────────────────────────

def test_norm_volume_zero():
    assert _norm_volume(0) == 0.0
    assert _norm_volume(None) == 0.0


def test_norm_volume_scales():
    low = _norm_volume(100)
    high = _norm_volume(10000)
    assert 0 < low < high <= 1.0


def test_norm_volume_caps():
    assert _norm_volume(1_000_000) == 1.0


def test_norm_intent():
    assert _norm_intent("transactional") == 1.0
    assert _norm_intent("commercial") == 0.8
    assert _norm_intent("informational") == 0.4
    assert _norm_intent(None) == 0.4


def test_norm_difficulty():
    assert _norm_difficulty(0) == 1.0  # easiest
    assert _norm_difficulty(100) == 0.0  # hardest
    assert _norm_difficulty(50) == 0.5
    assert _norm_difficulty(None) == 0.5  # unknown = neutral


def test_seasonality_boost_in_peak():
    now = datetime.now(timezone.utc).month
    data = {"peak_months": [now]}
    assert _seasonality_boost(data) == 1.0


def test_seasonality_boost_off_peak():
    now = datetime.now(timezone.utc).month
    other_months = [m for m in range(1, 13) if m != now]
    data = {"peak_months": other_months[:2]}
    assert _seasonality_boost(data) == 0.0


def test_seasonality_boost_none():
    assert _seasonality_boost(None) == 0.0


# ── Keyword scoring ──────────────────────────────────────────────────────────

def test_score_keyword_returns_positive(db_session: Session):
    kw = _make_keyword(db_session)
    score = score_keyword(kw, db_session)
    assert 0 < score <= 1.0


def test_score_keyword_higher_volume_higher_score(db_session: Session):
    kw_low = _make_keyword(db_session, keyword="low vol", volume=100)
    kw_high = _make_keyword(db_session, keyword="high vol", volume=20000)
    s_low = score_keyword(kw_low, db_session)
    s_high = score_keyword(kw_high, db_session)
    assert s_high > s_low


def test_score_keyword_transactional_beats_informational(db_session: Session):
    kw_info = _make_keyword(db_session, keyword="how to garden", intent="informational")
    kw_trans = _make_keyword(db_session, keyword="buy garden seed", intent="transactional")
    s_info = score_keyword(kw_info, db_session)
    s_trans = score_keyword(kw_trans, db_session)
    assert s_trans > s_info


def test_score_keyword_media_corroboration(db_session: Session):
    """Keywords with recent media signals should score higher."""
    kw = _make_keyword(db_session, keyword="cover crop")
    # No media signals
    s_without = score_keyword(kw, db_session)

    # Add corroborating media signal
    now = datetime.now(timezone.utc)
    db_session.add(MediaSignal(
        source_type="reddit", title="Cover Crop revolution in 2025",
        url="https://r.com/1", relevance_score=0.8, captured_at=now,
    ))
    db_session.flush()

    s_with = score_keyword(kw, db_session)
    assert s_with > s_without


# ── Rank backlog ──────────────────────────────────────────────────────────────

def test_rank_backlog_returns_sorted(db_session: Session):
    _make_keyword(db_session, keyword="low priority", volume=50, gap=0.1, intent="informational")
    _make_keyword(db_session, keyword="high priority", volume=10000, gap=0.9, intent="transactional")
    _make_keyword(db_session, keyword="mid priority", volume=2000, gap=0.5)

    ranked = rank_backlog(db_session, limit=10)
    assert len(ranked) == 3
    # Highest score first
    assert ranked[0][1] >= ranked[1][1] >= ranked[2][1]
    assert ranked[0][0].keyword == "high priority"


def test_rank_backlog_persists_scores(db_session: Session):
    kw = _make_keyword(db_session)
    rank_backlog(db_session, limit=10)

    refreshed = db_session.get(KeywordCandidate, kw.id)
    assert refreshed.priority_score is not None
    assert refreshed.priority_score > 0
    assert refreshed.status == "scored"


def test_rank_backlog_respects_limit(db_session: Session):
    for i in range(10):
        _make_keyword(db_session, keyword=f"kw-{i}", volume=1000 + i * 100)

    ranked = rank_backlog(db_session, limit=3)
    assert len(ranked) == 3


# ── Brief generation ─────────────────────────────────────────────────────────

def test_generate_brief_creates_entry(db_session: Session):
    kw = _make_keyword(db_session)
    db_session.commit()

    brief = generate_brief(db_session, kw.id, scrape_competitors=False)

    assert brief is not None
    assert brief.topic == "bermuda grass seed"
    assert brief.target_keyword == "bermuda grass seed"
    assert brief.status == "pending"
    assert brief.keyword_candidate_id == kw.id


def test_brief_has_all_required_fields(db_session: Session):
    kw = _make_keyword(db_session)
    db_session.commit()

    brief = generate_brief(db_session, kw.id, scrape_competitors=False)
    b = brief.brief_json

    assert "target_keyword" in b
    assert "secondary_keywords" in b
    assert "suggested_title_options" in b
    assert len(b["suggested_title_options"]) == 3
    assert "search_intent" in b
    assert "recommended_word_count" in b
    assert isinstance(b["recommended_word_count"], int)
    assert b["recommended_word_count"] >= 800
    assert "outline" in b
    assert len(b["outline"]) >= 3
    assert "competitor_gap_notes" in b
    assert "internal_link_candidates" in b
    assert "product_cta_candidates" in b
    assert "citation_requirements" in b
    assert len(b["citation_requirements"]) >= 1
    assert "suggested_angle" in b
    assert len(b["suggested_angle"]) > 20
    assert "metadata" in b


def test_brief_outline_structure(db_session: Session):
    kw = _make_keyword(db_session, intent="informational")
    db_session.commit()

    brief = generate_brief(db_session, kw.id, scrape_competitors=False)
    outline = brief.brief_json["outline"]

    for section in outline:
        assert "heading" in section
        assert "level" in section
        assert section["level"] in ("H2", "H3")
        assert "points" in section
        assert isinstance(section["points"], list)


def test_brief_idempotent(db_session: Session):
    """Generating a brief twice for the same keyword returns the existing one."""
    kw = _make_keyword(db_session)
    db_session.commit()

    brief1 = generate_brief(db_session, kw.id, scrape_competitors=False)
    brief2 = generate_brief(db_session, kw.id, scrape_competitors=False)

    assert brief1.id == brief2.id

    # Only one brief in DB
    count = len(db_session.execute(select(BriefQueue)).scalars().all())
    assert count == 1


def test_brief_updates_keyword_status(db_session: Session):
    kw = _make_keyword(db_session)
    db_session.commit()

    generate_brief(db_session, kw.id, scrape_competitors=False)

    refreshed = db_session.get(KeywordCandidate, kw.id)
    assert refreshed.status == "briefed"


def test_brief_internal_links(db_session: Session):
    """Brief should find relevant internal content for linking."""
    db_session.add(ContentInventory(
        wp_post_id=1, url="https://naturesseed.com/bermuda/",
        title="Complete Bermuda Grass Guide", slug="bermuda-guide",
        post_type="post", status="publish",
    ))
    kw = _make_keyword(db_session, keyword="bermuda grass seed")
    db_session.commit()

    brief = generate_brief(db_session, kw.id, scrape_competitors=False)
    links = brief.brief_json.get("internal_link_candidates", [])
    assert len(links) >= 1
    assert any("bermuda" in l["title"].lower() for l in links)


def test_brief_product_ctas(db_session: Session):
    """Brief should find matching products for CTAs."""
    db_session.add(ContentInventory(
        wp_post_id=100, url="https://naturesseed.com/products/bermuda-seed/",
        title="Bermuda Grass Seed - 5lb Bag", slug="bermuda-seed",
        post_type="product", status="publish",
    ))
    kw = _make_keyword(db_session, keyword="bermuda grass seed")
    db_session.commit()

    brief = generate_brief(db_session, kw.id, scrape_competitors=False)
    ctas = brief.brief_json.get("product_cta_candidates", [])
    assert len(ctas) >= 1
    assert any("bermuda" in c["title"].lower() for c in ctas)


# ── Generate top briefs ──────────────────────────────────────────────────────

def test_generate_top_briefs(db_session: Session):
    _make_keyword(db_session, keyword="tomato seed", volume=8000)
    _make_keyword(db_session, keyword="pepper seed", volume=5000)
    _make_keyword(db_session, keyword="herb seed", volume=3000)
    db_session.commit()

    briefs = generate_top_briefs(db_session, count=3, scrape=False)
    assert len(briefs) == 3
    assert all(b.brief_json is not None for b in briefs)

    # All keywords should be marked as briefed
    all_kws = db_session.execute(select(KeywordCandidate)).scalars().all()
    assert all(kw.status == "briefed" for kw in all_kws)


def test_generate_top_skips_already_briefed(db_session: Session):
    kw1 = _make_keyword(db_session, keyword="seed a", volume=5000)
    kw2 = _make_keyword(db_session, keyword="seed b", volume=4000)
    db_session.commit()

    # Generate brief for kw1
    generate_brief(db_session, kw1.id, scrape_competitors=False)

    # generate_top should only create 1 more
    briefs = generate_top_briefs(db_session, count=5, scrape=False)
    assert len(briefs) == 1
    assert briefs[0].topic == "seed b"


# ── Brief formatting ─────────────────────────────────────────────────────────

def test_format_brief_markdown(db_session: Session):
    kw = _make_keyword(db_session)
    db_session.commit()

    brief = generate_brief(db_session, kw.id, scrape_competitors=False)
    md = format_brief_markdown(brief)

    assert "# Brief: bermuda grass seed" in md
    assert "## Suggested Titles" in md
    assert "## Outline" in md
    assert "## Citation Requirements" in md
    assert "## Suggested Angle" in md


# ── Title generation ──────────────────────────────────────────────────────────

def test_generate_titles_commercial():
    titles = _generate_titles("grass seed", "commercial")
    assert len(titles) == 3
    assert all("Grass Seed" in t for t in titles)
    assert any("Buying" in t or "Compared" in t for t in titles)


def test_generate_titles_informational():
    titles = _generate_titles("grass seed", "informational")
    assert len(titles) == 3
    assert any("Guide" in t for t in titles)


# ── Outline generation ────────────────────────────────────────────────────────

def test_build_outline_informational():
    outline = _build_outline("tomato seeds", "informational", [])
    assert len(outline) >= 4
    headings = [s["heading"] for s in outline]
    assert any("What is" in h for h in headings)
    assert any("FAQ" in h or "Frequently" in h for h in headings)


def test_build_outline_commercial():
    outline = _build_outline("lawn seed", "commercial", [])
    assert len(outline) >= 4
    headings = [s["heading"] for s in outline]
    assert any("Best" in h for h in headings)
    assert any("Buy" in h or "Look" in h for h in headings)


# ── Citation requirements ─────────────────────────────────────────────────────

def test_citation_requirements_always_include_basics():
    outline = [{"heading": "Test", "points": ["Some fact"]}]
    cites = _identify_citation_requirements(outline)
    assert any("germination" in c.lower() for c in cites)
    assert any("zone" in c.lower() for c in cites)
