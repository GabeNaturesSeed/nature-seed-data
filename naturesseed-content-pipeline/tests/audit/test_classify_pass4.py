"""Pass 4 — match articles to approved subtopics via keyword presence."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentTopic, Topic,
)
from naturesseed_pipeline.pipelines.audit.classify import run_classify_pass4


def _setup() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    s = Session(eng)
    parent = Topic(name="Grass Seed", slug="grass-seed", source="wc_category", approved=1)
    s.add(parent); s.flush()
    cool = Topic(name="Cool-Season", slug="cool-season", parent_topic_id=parent.id,
                source="llm_proposed", approved=1,
                keywords=["fescue", "rye", "kentucky bluegrass"])
    warm = Topic(name="Warm-Season", slug="warm-season", parent_topic_id=parent.id,
                source="llm_proposed", approved=1,
                keywords=["bermuda", "zoysia"])
    s.add_all([cool, warm]); s.flush()

    # Article matches cool
    a1 = ContentInventory(wp_post_id=1, url="https://x/1", title="Fescue Guide",
                         slug="fescue-guide", post_type="post",
                         content_text="Fescue and rye are great cool-season grasses.")
    # Article matches warm
    a2 = ContentInventory(wp_post_id=2, url="https://x/2", title="Bermuda Guide",
                         slug="bermuda-guide", post_type="post",
                         content_text="Bermuda grows in warm climates.")
    # Article matches neither
    a3 = ContentInventory(wp_post_id=3, url="https://x/3", title="Misc",
                         slug="misc", post_type="post",
                         content_text="Something unrelated.")
    s.add_all([a1, a2, a3]); s.flush()
    for a in (a1, a2, a3):
        s.add(ContentTopic(content_inventory_id=a.id, topic_id=parent.id,
                          confidence=1.0, assigned_by="auto"))
    s.commit()
    return s


def test_pass4_assigns_matching_subtopic():
    s = _setup()
    count = run_classify_pass4(s); s.commit()
    assert count == 2  # a1 + a2

    assignments = s.execute(select(ContentTopic)).scalars().all()
    # 3 (top-level from setup) + 2 (subtopic from pass4) = 5
    assert len(assignments) == 5


def test_pass4_picks_best_match_when_multiple_keywords_hit():
    s = _setup()
    # Add a more strongly cool-matching article
    a = ContentInventory(wp_post_id=99, url="https://x/99", title="Fescue Rye",
                        slug="fr", post_type="post",
                        content_text="fescue rye fescue kentucky bluegrass")
    s.add(a); s.flush()
    parent = s.execute(select(Topic).where(Topic.slug == "grass-seed")).scalar_one()
    s.add(ContentTopic(content_inventory_id=a.id, topic_id=parent.id,
                      confidence=1.0, assigned_by="auto"))
    s.commit()

    run_classify_pass4(s); s.commit()

    cool = s.execute(select(Topic).where(Topic.slug == "cool-season")).scalar_one()
    assignments = s.execute(
        select(ContentTopic).where(ContentTopic.content_inventory_id == a.id)
    ).scalars().all()
    assert any(x.topic_id == cool.id for x in assignments)
