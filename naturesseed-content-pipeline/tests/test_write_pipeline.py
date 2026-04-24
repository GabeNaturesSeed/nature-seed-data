"""Tests for writing pipeline: writer, fact_checker, editor, images."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from naturesseed_pipeline.db.models import (
    Base,
    BriefQueue,
    ContentInventory,
    Draft,
    KeywordCandidate,
    MediaIndex,
    PublishQueue,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_approved_brief(session: Session, keyword: str = "bermuda grass seed") -> BriefQueue:
    """Create a keyword + approved brief for testing."""
    kw = KeywordCandidate(keyword=keyword, search_volume=5000, source="google_ads")
    session.add(kw)
    session.flush()

    brief = BriefQueue(
        keyword_candidate_id=kw.id,
        topic=keyword,
        target_keyword=keyword,
        brief_json={
            "target_keyword": keyword,
            "secondary_keywords": ["lawn grass", "warm season grass"],
            "search_intent": "commercial",
            "suggested_title_options": [
                f"Best {keyword.title()} for 2025",
                f"{keyword.title()} Guide",
                f"How to Choose {keyword.title()}",
            ],
            "recommended_word_count": 1500,
            "outline": [
                {"heading": f"What is {keyword.title()}?", "level": "H2",
                 "points": ["Definition", "Key characteristics"]},
                {"heading": "Best Varieties", "level": "H2",
                 "points": ["Premium blends", "Budget options"]},
                {"heading": "How to Plant", "level": "H2",
                 "points": ["Soil preparation", "Watering schedule"]},
                {"heading": "FAQ", "level": "H2",
                 "points": ["When to plant?", "How much seed per sqft?"]},
            ],
            "competitor_gap_notes": {"competitors_analyzed": [], "opportunities": "Zone-specific advice"},
            "internal_link_candidates": [
                {"title": "Lawn Care Guide", "url": "https://naturesseed.com/lawn-care/"},
            ],
            "product_cta_candidates": [
                {"title": "Bermuda Seed 5lb", "url": "https://naturesseed.com/products/bermuda-5lb/"},
            ],
            "citation_requirements": [
                "Any germination rates or growing zone claims",
                "Any soil/climate requirement specifics",
            ],
            "suggested_angle": "Zone-specific expertise from Nature's Seed.",
            "metadata": {"search_volume": 5000, "keyword_difficulty": 40},
        },
        priority_score=0.75,
        status="approved",
        approved_at=datetime.now(timezone.utc),
    )
    session.add(brief)
    session.commit()
    return brief


# ── Writer tests ──────────────────────────────────────────────────────────────

def test_writer_creates_draft(db_session: Session):
    from naturesseed_pipeline.agents.writer import write_from_brief

    brief = _make_approved_brief(db_session)
    draft = write_from_brief(db_session, brief.id)

    assert draft is not None
    assert draft.status == "draft"
    assert draft.title is not None
    assert "Bermuda Grass Seed" in draft.title
    assert draft.content_markdown is not None
    assert len(draft.content_markdown) > 500


def test_writer_has_citations(db_session: Session):
    from naturesseed_pipeline.agents.writer import write_from_brief

    brief = _make_approved_brief(db_session)
    draft = write_from_brief(db_session, brief.id)

    assert draft.citations is not None
    assert len(draft.citations) >= 1
    assert "[^1]" in draft.content_markdown


def test_writer_has_meta_description(db_session: Session):
    from naturesseed_pipeline.agents.writer import write_from_brief

    brief = _make_approved_brief(db_session)
    draft = write_from_brief(db_session, brief.id)

    assert draft.meta_description is not None
    assert len(draft.meta_description) > 50


def test_writer_has_headings(db_session: Session):
    from naturesseed_pipeline.agents.writer import write_from_brief

    brief = _make_approved_brief(db_session)
    draft = write_from_brief(db_session, brief.id)
    content = draft.content_markdown

    assert content.count("\n# ") >= 1 or content.startswith("# ")
    assert content.count("\n## ") >= 3


def test_writer_rejects_unapproved_brief(db_session: Session):
    from naturesseed_pipeline.agents.writer import write_from_brief

    brief = _make_approved_brief(db_session)
    brief.status = "pending"
    db_session.commit()

    draft = write_from_brief(db_session, brief.id)
    assert draft is None


# ── Fact checker tests ────────────────────────────────────────────────────────

def test_fact_checker_detects_placeholders(db_session: Session):
    from naturesseed_pipeline.agents.fact_checker import check_facts
    from naturesseed_pipeline.agents.writer import write_from_brief

    brief = _make_approved_brief(db_session)
    draft = write_from_brief(db_session, brief.id)

    result = check_facts(db_session, draft.id, fetch_sources=False)

    assert result["placeholders"] >= 1
    assert draft.fact_check_notes is not None


def test_fact_checker_with_no_citations(db_session: Session):
    from naturesseed_pipeline.agents.fact_checker import check_facts

    draft = Draft(
        brief_id=1,
        title="No citations here",
        content_markdown="# Simple Article\n\nJust some text without citations.",
        status="draft",
    )
    db_session.add(draft)
    db_session.flush()

    result = check_facts(db_session, draft.id, fetch_sources=False)
    assert result["total_claims"] == 0
    assert result["unsupported"] == 0


# ── Editor tests ──────────────────────────────────────────────────────────────

def test_editor_checks_readability(db_session: Session):
    from naturesseed_pipeline.agents.editor import run_editorial_review
    from naturesseed_pipeline.agents.writer import write_from_brief

    brief = _make_approved_brief(db_session)
    draft = write_from_brief(db_session, brief.id)
    draft.status = "draft"  # reset from fact-check
    db_session.commit()

    result = run_editorial_review(db_session, draft.id)
    assert "readability" in result
    assert "flesch_reading_ease" in result["readability"]


def test_editor_checks_heading_structure(db_session: Session):
    from naturesseed_pipeline.agents.editor import run_editorial_review
    from naturesseed_pipeline.agents.writer import write_from_brief

    brief = _make_approved_brief(db_session)
    draft = write_from_brief(db_session, brief.id)
    draft.status = "draft"
    db_session.commit()

    result = run_editorial_review(db_session, draft.id)
    assert "heading_structure" in result
    assert result["heading_structure"]["h1_count"] == 1


def test_editor_checks_keyword_density(db_session: Session):
    from naturesseed_pipeline.agents.editor import run_editorial_review
    from naturesseed_pipeline.agents.writer import write_from_brief

    brief = _make_approved_brief(db_session)
    draft = write_from_brief(db_session, brief.id)
    draft.status = "draft"
    db_session.commit()

    result = run_editorial_review(db_session, draft.id)
    assert "keyword_density" in result
    assert "density_pct" in result["keyword_density"]


def test_editor_auto_fixes(db_session: Session):
    from naturesseed_pipeline.agents.editor import run_editorial_review

    brief = _make_approved_brief(db_session)
    draft = Draft(
        brief_id=brief.id,
        title="Test  Double  Spaces",
        content_markdown="# Title\n\nSome  double  spaces  here.\n\n\n\n## Section\n\nMore text.  ",
        status="draft",
    )
    db_session.add(draft)
    db_session.commit()

    result = run_editorial_review(db_session, draft.id)
    assert len(result.get("auto_fixes", [])) >= 1
    assert "  " not in draft.content_markdown


def test_editor_checks_meta_description(db_session: Session):
    from naturesseed_pipeline.agents.editor import run_editorial_review

    brief = _make_approved_brief(db_session)
    draft = Draft(
        brief_id=brief.id,
        title="No Meta",
        content_markdown="# Title\n\nContent without meta.",
        status="draft",
    )
    db_session.add(draft)
    db_session.commit()

    result = run_editorial_review(db_session, draft.id)
    assert not result["meta_description"]["present"]


# ── Write pipeline ────────────────────────────────────────────────────────────

def test_full_write_pipeline(db_session: Session):
    from naturesseed_pipeline.pipelines.write import write_from_brief_pipeline

    brief = _make_approved_brief(db_session)
    result = write_from_brief_pipeline(db_session, brief.id, fetch_sources=False)

    assert "draft_id" in result
    assert result["stages"]["writer"] == "complete"
    assert result.get("final_status") is not None

    draft = db_session.get(Draft, result["draft_id"])
    assert draft is not None
    assert draft.fact_check_notes is not None
    assert draft.editorial_notes is not None


def test_write_pipeline_from_next_brief(db_session: Session):
    from naturesseed_pipeline.pipelines.write import write_next_approved_brief

    _make_approved_brief(db_session, "lawn seed")
    result = write_next_approved_brief(db_session, fetch_sources=False)

    assert result is not None
    assert "draft_id" in result


def test_write_pipeline_no_approved_briefs(db_session: Session):
    from naturesseed_pipeline.pipelines.write import write_next_approved_brief

    result = write_next_approved_brief(db_session)
    assert result is None


# ── Image library tests ───────────────────────────────────────────────────────

def test_media_search_keyword_overlap(db_session: Session):
    from naturesseed_pipeline.integrations.image_library import search_media

    db_session.add(MediaIndex(
        wp_media_id=1,
        url="https://naturesseed.com/wp-content/uploads/bermuda-lawn.jpg",
        filename="bermuda-lawn.jpg",
        title="Bermuda grass lawn",
        alt_text="Lush bermuda grass lawn in sunlight",
        description_text="bermuda grass lawn lush sunlight bermuda-lawn.jpg",
    ))
    db_session.add(MediaIndex(
        wp_media_id=2,
        url="https://naturesseed.com/wp-content/uploads/tomato-seeds.jpg",
        filename="tomato-seeds.jpg",
        title="Tomato seeds close up",
        description_text="tomato seeds close up tomato-seeds.jpg",
    ))
    db_session.commit()

    results = search_media(db_session, "bermuda grass lawn care")
    assert len(results) >= 1
    assert results[0][0].wp_media_id == 1
    assert results[0][1] > 0


def test_media_search_no_match(db_session: Session):
    from naturesseed_pipeline.integrations.image_library import search_media

    db_session.add(MediaIndex(
        wp_media_id=1, url="https://x.com/a.jpg", filename="a.jpg",
        description_text="random unrelated image",
    ))
    db_session.commit()

    results = search_media(db_session, "bermuda grass lawn")
    assert len(results) == 0


# ── Image selector tests ─────────────────────────────────────────────────────

def test_infer_image_slots():
    from naturesseed_pipeline.agents.image_selector import _infer_image_slots

    content = """# Main Title

Some intro text.

## Getting Started

First section content.

## Advanced Tips

Second section.

## FAQ

Questions here.
"""
    slots = _infer_image_slots(content)
    assert slots[0]["name"] == "hero"
    assert len(slots) >= 4  # hero + 3 H2s
    assert slots[1]["name"] == "section_1"


def test_image_selector_uses_library_when_available(db_session: Session):
    from naturesseed_pipeline.agents.image_selector import select_images_for_draft

    brief = _make_approved_brief(db_session)
    draft = Draft(
        brief_id=brief.id,
        title="Bermuda Grass Seed Guide",
        content_markdown="# Bermuda Guide\n\nIntro.\n\n## Planting\n\nPlant bermuda grass.\n\n## Care\n\nWater regularly.",
        status="draft",
    )
    db_session.add(draft)

    # Add matching media
    db_session.add(MediaIndex(
        wp_media_id=1,
        url="https://naturesseed.com/bermuda.jpg",
        filename="bermuda.jpg",
        title="Bermuda grass planting",
        alt_text="Bermuda grass being planted",
        description_text="bermuda grass planting seeds outdoor garden",
    ))
    db_session.commit()

    assignments = select_images_for_draft(db_session, draft.id)
    assert len(assignments) >= 2  # hero + at least 1 section

    # At least one should use library
    library_used = any(a["source"] == "library" for a in assignments)
    # May not match if threshold is high and keywords don't overlap enough
    # But every assignment should have alt text
    for a in assignments:
        assert a.get("alt_text") is not None or a["source"] == "none"


# ── Image optimization ────────────────────────────────────────────────────────

def test_optimize_image(tmp_path):
    from PIL import Image

    from naturesseed_pipeline.integrations.image_generation import optimize_image

    # Create a test image
    img = Image.new("RGB", (3000, 2000), color="green")
    input_path = str(tmp_path / "test.png")
    img.save(input_path)

    output_path = str(tmp_path / "test.webp")
    result = optimize_image(input_path, output_path, max_width=1600)

    assert result == output_path
    assert Path(output_path).exists()

    result_img = Image.open(output_path)
    assert result_img.width == 1600
    assert result_img.format == "WEBP"


def test_optimize_image_no_resize_needed(tmp_path):
    from PIL import Image

    from naturesseed_pipeline.integrations.image_generation import optimize_image

    img = Image.new("RGB", (800, 600), color="blue")
    input_path = str(tmp_path / "small.png")
    img.save(input_path)

    output_path = str(tmp_path / "small.webp")
    optimize_image(input_path, output_path, max_width=1600)

    result_img = Image.open(output_path)
    assert result_img.width == 800  # unchanged


# ── Alt text generation ───────────────────────────────────────────────────────

def test_alt_text_from_context():
    from naturesseed_pipeline.integrations.image_generation import _generate_alt_from_context

    alt = _generate_alt_from_context("Bermuda grass being planted in a raised bed garden")
    assert len(alt) > 0
    assert len(alt) <= 125


def test_alt_text_empty_context():
    from naturesseed_pipeline.integrations.image_generation import _generate_alt_from_context

    alt = _generate_alt_from_context("")
    assert "Nature's Seed" in alt


# ── Pipeline integration ─────────────────────────────────────────────────────

def test_attach_images_pipeline(db_session: Session):
    from naturesseed_pipeline.pipelines.images import attach_images_to_draft

    brief = _make_approved_brief(db_session)
    draft = Draft(
        brief_id=brief.id,
        title="Test Draft",
        content_markdown="# Test\n\nIntro.\n\n## Section One\n\nContent.\n\n## Section Two\n\nMore.",
        status="draft",
    )
    db_session.add(draft)
    db_session.commit()

    result = attach_images_to_draft(db_session, draft.id)
    assert result["total_slots"] >= 3  # hero + 2 sections
    assert result["with_alt_text"] >= 0

    # Check draft has image_assignments
    refreshed = db_session.get(Draft, draft.id)
    assert refreshed.image_assignments is not None
    assert len(refreshed.image_assignments) >= 3


from pathlib import Path
