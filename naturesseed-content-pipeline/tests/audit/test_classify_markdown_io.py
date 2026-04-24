"""Markdown export + import round-trip for subtopic approvals."""

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Base, Topic
from naturesseed_pipeline.pipelines.audit.classify import (
    export_pending_subtopics_to_markdown,
    import_subtopic_approvals_from_markdown,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    s = Session(eng)
    parent = Topic(name="Grass Seed", slug="grass-seed", source="wc_category", approved=1)
    s.add(parent); s.flush()
    s.add(Topic(name="Cool-Season", slug="cool-season", parent_topic_id=parent.id,
                source="llm_proposed", approved=0,
                keywords=["fescue", "rye"]))
    s.add(Topic(name="Warm-Season", slug="warm-season", parent_topic_id=parent.id,
                source="llm_proposed", approved=0,
                keywords=["bermuda", "zoysia"]))
    s.add(Topic(name="Shade", slug="shade", parent_topic_id=parent.id,
                source="llm_proposed", approved=0,
                keywords=["shade tolerant"]))
    s.commit()
    return s


def test_export_writes_file_with_all_pending(tmp_path: Path):
    s = _session()
    path = tmp_path / "proposals.md"
    count = export_pending_subtopics_to_markdown(s, path)
    assert count == 3
    text = path.read_text()
    assert "Cool-Season" in text
    assert "Warm-Season" in text
    assert "Shade" in text
    assert "parent: grass-seed" in text


def test_import_roundtrip_all_approved(tmp_path: Path):
    s = _session()
    path = tmp_path / "proposals.md"
    export_pending_subtopics_to_markdown(s, path)

    counts = import_subtopic_approvals_from_markdown(s, path)
    s.commit()
    assert counts["approved"] == 3
    assert counts["rejected"] == 0

    all_approved = s.execute(select(Topic).where(
        Topic.parent_topic_id.isnot(None), Topic.source == "llm_proposed"
    )).scalars().all()
    assert all(t.approved == 1 for t in all_approved)


def test_import_rejects_deleted_sections(tmp_path: Path):
    s = _session()
    path = tmp_path / "proposals.md"
    export_pending_subtopics_to_markdown(s, path)

    # Simulate user deleting the "Shade" section
    text = path.read_text()
    # Strip the Shade block (from its --- separator through the next --- or EOF)
    import re
    text = re.sub(r"---\s*\n## Shade \[parent:.*?(?=---|\Z)", "", text, flags=re.DOTALL)
    path.write_text(text)

    counts = import_subtopic_approvals_from_markdown(s, path)
    s.commit()
    assert counts["approved"] == 2
    assert counts["rejected"] == 1

    remaining = s.execute(select(Topic).where(
        Topic.parent_topic_id.isnot(None)
    )).scalars().all()
    slugs = {t.slug for t in remaining}
    assert "shade" not in slugs
    assert {"cool-season", "warm-season"} <= slugs


def test_import_applies_edited_name_and_keywords(tmp_path: Path):
    s = _session()
    path = tmp_path / "proposals.md"
    export_pending_subtopics_to_markdown(s, path)

    # User renames Cool-Season and adds a keyword
    text = path.read_text()
    text = text.replace("## Cool-Season [parent: grass-seed]",
                        "## Cool-Season Grasses [parent: grass-seed]")
    text = text.replace("  - fescue\n  - rye",
                        "  - fescue\n  - rye\n  - bluegrass")
    path.write_text(text)

    counts = import_subtopic_approvals_from_markdown(s, path)
    s.commit()
    assert counts["refined"] >= 1

    cool = s.execute(select(Topic).where(Topic.slug == "cool-season")).scalar_one()
    assert cool.name == "Cool-Season Grasses"
    assert "bluegrass" in (cool.keywords or [])
