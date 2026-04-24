"""Tests for publish, schedule, schema, internal links, refresh, and orchestrator."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from naturesseed_pipeline.db.models import (
    Base,
    BriefQueue,
    ContentInventory,
    Draft,
    GscQueryPerformance,
    KeywordCandidate,
    PublishQueue,
    RefreshQueue,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_draft(session: Session, title: str = "Test Draft", status: str = "approved") -> Draft:
    kw = KeywordCandidate(keyword=title.lower(), search_volume=1000, source="test")
    session.add(kw)
    session.flush()
    brief = BriefQueue(
        keyword_candidate_id=kw.id, topic=title, target_keyword=title.lower(),
        brief_json={"target_keyword": title.lower(), "search_intent": "informational"},
        status="approved", approved_at=datetime.now(timezone.utc),
    )
    session.add(brief)
    session.flush()
    draft = Draft(
        brief_id=brief.id, title=title, status=status,
        content_markdown=f"# {title}\n\nIntro text about {title.lower()}.\n\n## Getting Started\n\nStep by step guide.\n\n## FAQ\n\n### When to plant?\n\nSpring is best.\n\n### How much water?\n\nRegular watering.",
        meta_description=f"Learn about {title.lower()} from Nature's Seed.",
    )
    session.add(draft)
    session.commit()
    return draft


# ── Markdown to HTML ──────────────────────────────────────────────────────────

def test_markdown_to_html():
    from naturesseed_pipeline.integrations.wordpress import markdown_to_html

    html = markdown_to_html("# Hello\n\nParagraph with **bold**.")
    assert "<h1>" in html
    assert "<strong>bold</strong>" in html


def test_markdown_footnotes():
    from naturesseed_pipeline.integrations.wordpress import markdown_to_html

    md = "Claim [^1].\n\n[^1]: Source URL."
    html = markdown_to_html(md)
    assert "footnote" in html.lower() or "sup" in html.lower() or "[^1]" not in html


# ── Schema markup ─────────────────────────────────────────────────────────────

def test_schema_detect_article():
    from naturesseed_pipeline.integrations.schema import detect_schema_type

    html = "<h1>Guide to Grass Seed</h1><p>Content here.</p>"
    assert detect_schema_type(html) == "Article"


def test_schema_detect_faq():
    from naturesseed_pipeline.integrations.schema import detect_schema_type

    html = "<h2>Frequently Asked Questions</h2><h3>When?</h3><p>Spring.</p>"
    assert detect_schema_type(html) == "FAQPage"


def test_schema_detect_howto():
    from naturesseed_pipeline.integrations.schema import detect_schema_type

    html = "<h1>How to Plant Seeds</h1><ol><li>Step 1</li><li>Step 2</li><li>Step 3</li></ol>"
    assert detect_schema_type(html) == "HowTo"


def test_schema_generates_json_ld():
    from naturesseed_pipeline.integrations.schema import generate_schema

    html = "<h1>Test</h1><p>Content</p>"
    schema = generate_schema(html, title="Test Article", description="A test.")
    assert 'application/ld+json' in schema
    assert '"Article"' in schema
    assert '"Test Article"' in schema


def test_schema_faq_extracts_questions():
    from naturesseed_pipeline.integrations.schema import generate_schema

    html = '<h2>FAQ</h2><h3>When to plant?</h3><p>In spring.</p><h3>How deep?</h3><p>Half inch.</p>'
    schema = generate_schema(html, title="FAQ Test")
    assert "When to plant?" in schema
    assert "In spring." in schema


def test_schema_injection():
    from naturesseed_pipeline.integrations.schema import generate_schema, inject_schema

    html = "<h1>Test</h1><p>Content</p>"
    schema = generate_schema(html, title="Test")
    result = inject_schema(html, schema)
    assert result.startswith("<h1>")
    assert result.endswith("</script>")


# ── Internal links ────────────────────────────────────────────────────────────

def test_find_link_opportunities(db_session: Session):
    from naturesseed_pipeline.pipelines.internal_links import find_link_opportunities

    db_session.add(ContentInventory(
        wp_post_id=1, url="https://naturesseed.com/lawn-care-guide/",
        title="Complete Lawn Care Guide", slug="lawn-care-guide",
        post_type="post", status="publish",
    ))
    db_session.commit()

    content = "This article covers lawn care tips and how to maintain your lawn properly."
    links = find_link_opportunities(db_session, content)
    assert len(links) >= 1
    assert links[0]["url"] == "https://naturesseed.com/lawn-care-guide/"


def test_insert_internal_links():
    from naturesseed_pipeline.pipelines.internal_links import insert_internal_links

    html = "<p>Learn about lawn care and how to grow grass.</p>"
    links = [{"anchor": "lawn care", "url": "https://naturesseed.com/lawn/", "title": "Lawn Guide"}]
    result = insert_internal_links(html, links)
    assert '<a href="https://naturesseed.com/lawn/"' in result


def test_max_links_respected(db_session: Session):
    from naturesseed_pipeline.pipelines.internal_links import find_link_opportunities

    for i in range(10):
        db_session.add(ContentInventory(
            wp_post_id=i + 1, url=f"https://naturesseed.com/post-{i}/",
            title=f"Garden Post About Topic {i}", slug=f"post-{i}",
            post_type="post", status="publish",
        ))
    db_session.commit()

    content = "This covers garden topic 1 and garden topic 2 and garden topic 3 and more garden topics."
    links = find_link_opportunities(db_session, content, max_links=3)
    assert len(links) <= 3


# ── Schedule ──────────────────────────────────────────────────────────────────

def test_assign_next_slot(db_session: Session):
    from naturesseed_pipeline.pipelines.schedule import assign_next_slot

    config = {
        "publish_days": ["Tuesday", "Thursday"],
        "publish_time": "09:00",
        "max_per_week": 3,
        "min_gap_hours": 24,
    }
    slot = assign_next_slot(db_session, config=config)
    assert slot.weekday() in (1, 3)  # Tuesday or Thursday
    assert slot.hour == 9


def test_schedule_draft(db_session: Session):
    from naturesseed_pipeline.pipelines.schedule import schedule_draft

    draft = _make_draft(db_session)
    pq = schedule_draft(db_session, draft.id)
    assert pq is not None
    assert pq.scheduled_for is not None
    assert pq.publish_status == "scheduled_pending"


def test_schedule_respects_gap(db_session: Session):
    from naturesseed_pipeline.pipelines.schedule import assign_next_slot

    config = {"publish_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
              "publish_time": "09:00", "max_per_week": 10, "min_gap_hours": 48}

    draft = _make_draft(db_session)
    slot1 = assign_next_slot(db_session, config=config)
    db_session.add(PublishQueue(draft_id=draft.id, scheduled_for=slot1, publish_status="scheduled_pending"))
    db_session.commit()

    slot2 = assign_next_slot(db_session, config=config)
    gap = abs((slot2 - slot1).total_seconds()) / 3600
    assert gap >= 48


def test_get_calendar(db_session: Session):
    from naturesseed_pipeline.pipelines.schedule import get_calendar, schedule_draft

    draft = _make_draft(db_session)
    schedule_draft(db_session, draft.id)

    cal = get_calendar(db_session, days=60)
    assert len(cal) >= 1
    assert cal[0]["title"] == draft.title


# ── Publish pipeline ─────────────────────────────────────────────────────────

def test_publish_dry_run(db_session: Session):
    from naturesseed_pipeline.pipelines.publish import publish_draft

    draft = _make_draft(db_session)
    result = publish_draft(db_session, draft.id, dry_run=True)

    assert result["mode"] == "dry_run"
    assert result["title"] == draft.title
    assert result["html_length"] > 0
    assert "schema_type" in result


def test_publish_generates_schema(db_session: Session):
    from naturesseed_pipeline.pipelines.publish import publish_draft

    draft = _make_draft(db_session, title="How to Plant Seeds")
    result = publish_draft(db_session, draft.id, dry_run=True)
    # The HTML should contain JSON-LD
    assert "application/ld+json" in result.get("html_preview", "")


# ── Refresh pipeline ─────────────────────────────────────────────────────────

def test_find_refresh_candidates_stale(db_session: Session):
    from naturesseed_pipeline.pipelines.refresh import find_refresh_candidates

    old_date = datetime.now(timezone.utc) - timedelta(days=400)
    db_session.add(ContentInventory(
        wp_post_id=1, url="https://naturesseed.com/old-post/",
        title="Old Stale Post", slug="old-post",
        post_type="post", status="publish",
        modified_at=old_date,
    ))
    db_session.commit()

    candidates = find_refresh_candidates(db_session)
    assert len(candidates) >= 1
    assert any("months old" in c["reasons"][0] for c in candidates)


def test_find_refresh_candidates_no_fresh(db_session: Session):
    from naturesseed_pipeline.pipelines.refresh import find_refresh_candidates

    recent = datetime.now(timezone.utc) - timedelta(days=30)
    db_session.add(ContentInventory(
        wp_post_id=1, url="https://naturesseed.com/fresh/",
        title="Fresh Post", slug="fresh",
        post_type="post", status="publish",
        modified_at=recent,
    ))
    db_session.commit()

    candidates = find_refresh_candidates(db_session)
    assert len(candidates) == 0


def test_scan_and_queue(db_session: Session):
    from naturesseed_pipeline.pipelines.refresh import scan_and_queue

    old_date = datetime.now(timezone.utc) - timedelta(days=400)
    db_session.add(ContentInventory(
        wp_post_id=1, url="https://naturesseed.com/old/",
        title="Old Post", slug="old", post_type="post", status="publish",
        modified_at=old_date,
    ))
    db_session.commit()

    added = scan_and_queue(db_session)
    assert added >= 1

    items = db_session.execute(select(RefreshQueue)).scalars().all()
    assert len(items) >= 1


def test_scan_no_duplicates(db_session: Session):
    from naturesseed_pipeline.pipelines.refresh import scan_and_queue

    old_date = datetime.now(timezone.utc) - timedelta(days=400)
    db_session.add(ContentInventory(
        wp_post_id=1, url="https://naturesseed.com/old/",
        title="Old Post", slug="old", post_type="post", status="publish",
        modified_at=old_date,
    ))
    db_session.commit()

    scan_and_queue(db_session)
    scan_and_queue(db_session)

    items = db_session.execute(select(RefreshQueue)).scalars().all()
    assert len(items) == 1


# ── Refresh planner ───────────────────────────────────────────────────────────

def test_refresh_planner(db_session: Session):
    from naturesseed_pipeline.agents.refresh_planner import plan_refresh

    old_date = datetime.now(timezone.utc) - timedelta(days=400)
    content = ContentInventory(
        wp_post_id=42, url="https://naturesseed.com/old-guide/",
        title="Old Gardening Guide", slug="old-guide",
        post_type="post", status="publish",
        target_keyword="gardening guide",
        modified_at=old_date, word_count=800,
    )
    db_session.add(content)
    db_session.flush()

    rq = RefreshQueue(
        content_inventory_id=content.id,
        reason="Content is 13 months old",
        status="pending",
    )
    db_session.add(rq)
    db_session.commit()

    brief = plan_refresh(db_session, rq.id)
    assert brief is not None
    assert brief.is_refresh == 1
    assert brief.original_wp_post_id == 42
    assert "[REFRESH]" in brief.topic
    assert brief.brief_json is not None
    assert brief.brief_json.get("is_refresh") is True
    assert len(brief.brief_json.get("sections_to_update", [])) >= 1

    # Refresh queue should be marked planned
    refreshed_rq = db_session.get(RefreshQueue, rq.id)
    assert refreshed_rq.status == "planned"


# ── Orchestrator ──────────────────────────────────────────────────────────────

def test_orchestrator_daily_runs_without_crash(db_session: Session):
    """Daily orchestrator should run all steps without crashing."""
    from unittest.mock import patch

    # Mock external calls
    with patch("naturesseed_pipeline.pipelines.audit_legacy.run_full_audit", return_value={"posts": 0, "pages": 0, "products": 0, "orphan_flags": 0}), \
         patch("naturesseed_pipeline.pipelines.research_keywords.run_gsc_sync", return_value={"rows": 0}), \
         patch("naturesseed_pipeline.pipelines.research_media.run_listener_sweep", return_value={"new_signals": 0, "by_source": {}, "total_fetched": 0}):
        from naturesseed_pipeline.pipelines.orchestrator import run_daily
        results = run_daily(db_session)

    assert "audit" in results
    assert "gsc_sync" in results
    assert "media" in results


def test_orchestrator_weekly_runs_without_crash(db_session: Session):
    """Weekly orchestrator should run without crashing (even with empty data)."""
    from unittest.mock import patch

    with patch("naturesseed_pipeline.pipelines.research_keywords.run_inventory_expansion", return_value={"candidates": 0}), \
         patch("naturesseed_pipeline.pipelines.research_media.promote_signals_to_keywords", return_value={"promoted": 0, "eligible": 0}):
        from naturesseed_pipeline.pipelines.orchestrator import run_weekly
        results = run_weekly(db_session, brief_count=3)

    assert "keyword_expansion" in results
    assert "scoring" in results


def test_orchestrator_refresh_runs_without_crash(db_session: Session):
    from naturesseed_pipeline.pipelines.orchestrator import run_refresh

    results = run_refresh(db_session)
    assert "scan" in results
