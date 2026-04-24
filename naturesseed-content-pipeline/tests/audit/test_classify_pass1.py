"""Pass 1 of classify — assigns each article a top-level topic deterministically."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentTopic, Topic,
)
from naturesseed_pipeline.pipelines.audit.classify import (
    seed_topics_from_wc_categories, run_classify_pass1,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_pass1_product_gets_category_topic():
    s = _session()
    seed_topics_from_wc_categories(s, [
        {"id": 10, "slug": "grass-seed", "name": "Grass Seed"},
    ]); s.commit()
    s.add(ContentInventory(wp_post_id=1, url="https://x/p/1/", title="Fescue Mix",
                          slug="fescue-mix", post_type="product",
                          categories=[10], status="publish"))
    s.commit()

    count = run_classify_pass1(s, wp_cat_id_to_slug={10: "grass-seed"})
    s.commit()

    assignments = s.execute(select(ContentTopic)).scalars().all()
    assert len(assignments) == 1
    grass = s.execute(select(Topic).where(Topic.slug == "grass-seed")).scalar_one()
    assert assignments[0].topic_id == grass.id


def test_pass1_post_falls_to_unclassified_without_category():
    s = _session()
    seed_topics_from_wc_categories(s, [
        {"id": 10, "slug": "grass-seed", "name": "Grass Seed"},
    ]); s.commit()
    s.add(ContentInventory(wp_post_id=2, url="https://x/a/", title="A", slug="a",
                          post_type="post", categories=[], status="publish"))
    s.commit()

    run_classify_pass1(s, wp_cat_id_to_slug={10: "grass-seed"})
    s.commit()

    assignments = s.execute(select(ContentTopic)).scalars().all()
    unclassified = s.execute(select(Topic).where(Topic.slug == "unclassified")).scalar_one()
    assert assignments[0].topic_id == unclassified.id


def test_pass1_idempotent():
    s = _session()
    seed_topics_from_wc_categories(s, [
        {"id": 10, "slug": "grass-seed", "name": "Grass Seed"},
    ]); s.commit()
    s.add(ContentInventory(wp_post_id=1, url="https://x/p/1/", title="X", slug="x",
                          post_type="post", categories=[10], status="publish"))
    s.commit()

    run_classify_pass1(s, wp_cat_id_to_slug={10: "grass-seed"}); s.commit()
    run_classify_pass1(s, wp_cat_id_to_slug={10: "grass-seed"}); s.commit()

    assignments = s.execute(select(ContentTopic)).scalars().all()
    assert len(assignments) == 1
