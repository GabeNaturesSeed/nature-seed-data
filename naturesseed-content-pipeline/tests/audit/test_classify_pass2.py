"""Pass 2 — LLM subtopic proposal (mocked LLM)."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentTopic, Topic,
)
from naturesseed_pipeline.pipelines.audit.classify import (
    run_classify_pass2, SubtopicProposer,
)


class FakeProposer:
    def propose(self, topic_name, samples):
        return [
            {"name": "Cool-Season", "slug": "cool-season",
             "keywords": ["fescue", "rye", "kentucky bluegrass"]},
            {"name": "Warm-Season", "slug": "warm-season",
             "keywords": ["bermuda", "zoysia", "st augustine"]},
        ]


def _setup(s: Session):
    topic = Topic(name="Grass Seed", slug="grass-seed",
                  wc_category_slug="grass-seed", source="wc_category", approved=1)
    s.add(topic); s.flush()
    for i in range(3):
        c = ContentInventory(wp_post_id=i + 1, url=f"https://x/{i}", title=f"A{i}",
                            slug=f"a{i}", post_type="post", content_text="fescue info")
        s.add(c); s.flush()
        s.add(ContentTopic(content_inventory_id=c.id, topic_id=topic.id,
                          confidence=1.0, assigned_by="auto"))
    s.commit()
    return topic


def test_pass2_proposes_subtopics_with_approved_zero():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    s = Session(eng)
    topic = _setup(s)

    proposed = run_classify_pass2(s, proposer=FakeProposer())
    s.commit()
    assert proposed == 2

    subs = s.execute(select(Topic).where(Topic.parent_topic_id == topic.id)).scalars().all()
    assert len(subs) == 2
    assert all(t.source == "llm_proposed" and t.approved == 0 for t in subs)
    slugs = {t.slug for t in subs}
    assert slugs == {"cool-season", "warm-season"}
    # keywords must be persisted
    cool = next(t for t in subs if t.slug == "cool-season")
    assert cool.keywords == ["fescue", "rye", "kentucky bluegrass"]


def test_pass2_skips_topics_with_existing_approved_subtopics():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    s = Session(eng)
    topic = _setup(s)

    # Pre-existing approved subtopic
    s.add(Topic(name="Existing", slug="existing", parent_topic_id=topic.id,
               source="user_created", approved=1))
    s.commit()

    proposed = run_classify_pass2(s, proposer=FakeProposer())
    s.commit()
    assert proposed == 0
