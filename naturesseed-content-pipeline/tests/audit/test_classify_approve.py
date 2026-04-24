"""Approval helpers for pass 3 — the CLI piggybacks on these."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Base, Topic
from naturesseed_pipeline.pipelines.audit.classify import (
    list_pending_subtopics, approve_subtopic, approve_all_subtopics,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    s = Session(eng)
    parent = Topic(name="Grass Seed", slug="grass-seed", source="wc_category", approved=1)
    s.add(parent); s.flush()
    s.add(Topic(name="Cool", slug="cool", parent_topic_id=parent.id,
               source="llm_proposed", approved=0, keywords=["fescue"]))
    s.add(Topic(name="Warm", slug="warm", parent_topic_id=parent.id,
               source="llm_proposed", approved=0, keywords=["bermuda"]))
    s.commit()
    return s


def test_list_pending_returns_only_unapproved():
    s = _session()
    pending = list_pending_subtopics(s)
    assert len(pending) == 2
    assert all(t.approved == 0 for t in pending)


def test_approve_subtopic_flips_flag():
    s = _session()
    approved = approve_subtopic(s, "cool"); s.commit()
    assert approved is True
    cool = s.execute(select(Topic).where(Topic.slug == "cool")).scalar_one()
    assert cool.approved == 1


def test_approve_all_approves_every_pending():
    s = _session()
    n = approve_all_subtopics(s); s.commit()
    assert n == 2
    assert not list_pending_subtopics(s)
