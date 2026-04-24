"""Seed top-level topics from WooCommerce categories."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Base, Topic
from naturesseed_pipeline.pipelines.audit.classify import seed_topics_from_wc_categories


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_seed_inserts_top_level_topics():
    s = _session()
    wc_categories = [
        {"id": 10, "slug": "grass-seed", "name": "Grass Seed"},
        {"id": 11, "slug": "pasture-seed", "name": "Pasture Seed"},
        {"id": 12, "slug": "wildflower-seed", "name": "Wildflower Seed"},
    ]
    count = seed_topics_from_wc_categories(s, wc_categories)
    s.commit()
    # 3 WC categories + 1 Unclassified bucket = 4
    assert count == 4
    topics = s.execute(select(Topic).order_by(Topic.slug)).scalars().all()
    assert all(t.parent_topic_id is None for t in topics)
    assert all(t.approved == 1 for t in topics)
    # 3 should have source='wc_category', 1 Unclassified has source='user_created'
    sources = {t.slug: t.source for t in topics}
    assert sources["grass-seed"] == "wc_category"
    assert sources["unclassified"] == "user_created"


def test_seed_is_idempotent():
    s = _session()
    wc_categories = [{"id": 10, "slug": "grass-seed", "name": "Grass Seed"}]
    seed_topics_from_wc_categories(s, wc_categories); s.commit()
    added = seed_topics_from_wc_categories(s, wc_categories); s.commit()
    assert added == 0
    # 1 WC + 1 Unclassified = 2 rows total, both from first call
    assert len(s.execute(select(Topic)).scalars().all()) == 2


def test_seed_creates_unclassified_bucket():
    s = _session()
    seed_topics_from_wc_categories(s, []); s.commit()
    topics = s.execute(select(Topic)).scalars().all()
    assert any(t.slug == "unclassified" for t in topics)
