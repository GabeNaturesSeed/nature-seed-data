"""Integration test for tag-products stage."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentProductMention,
    OrphanReference, WcCatalogSnapshot,
)
from naturesseed_pipeline.pipelines.audit.tag_products import run_tag_products


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def _seed_catalog(s):
    s.add_all([
        WcCatalogSnapshot(wp_product_id=1, slug="active-mix", name="Active Mix",
                         status="publish", permalink="https://x/products/active-mix/",
                         species_list=["fescue", "rye"]),
        WcCatalogSnapshot(wp_product_id=2, slug="old-mix", name="Old Mix",
                         status="draft", permalink="https://x/products/old-mix/",
                         species_list=["orchard grass"]),
    ]); s.commit()


def test_active_product_goes_to_mentions_not_orphan():
    s = _session(); _seed_catalog(s)
    s.add(ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                          content_html='<a href="/products/active-mix/">x</a>',
                          content_text="Active Mix is great"))
    s.commit()

    run_tag_products(s, fuzzy_threshold=0.85)
    s.commit()

    mentions = s.execute(select(ContentProductMention)).scalars().all()
    orphans = s.execute(select(OrphanReference)).scalars().all()
    assert len(mentions) == 1 and mentions[0].wp_product_id == 1
    # species in active product → not an orphan
    assert not any(o.reference_type == "species_mention" and o.reference_value == "fescue"
                   for o in orphans)


def test_discontinued_product_goes_to_orphan_not_mentions():
    s = _session(); _seed_catalog(s)
    s.add(ContentInventory(url="https://x/b", title="B", slug="b", post_type="post",
                          content_html='', content_text="Old Mix worked well."))
    s.commit()

    run_tag_products(s, fuzzy_threshold=0.85)
    s.commit()

    assert s.execute(select(ContentProductMention)).scalars().all() == []
    orphans = s.execute(select(OrphanReference)).scalars().all()
    assert any(o.reference_type == "inactive_product" for o in orphans)


def test_unmatched_species_flagged_as_species_mention():
    s = _session(); _seed_catalog(s)
    s.add(ContentInventory(url="https://x/c", title="C", slug="c", post_type="post",
                          content_html='', content_text="Plant clover or orchard grass here."))
    s.commit()

    run_tag_products(s, fuzzy_threshold=0.85)
    s.commit()

    orphans = s.execute(select(OrphanReference)).scalars().all()
    values = {o.reference_value for o in orphans
              if o.reference_type == "species_mention"}
    assert "clover" in values  # not in any snapshot species_list


def test_rerun_clears_prior_rows_and_re_inserts():
    s = _session(); _seed_catalog(s)
    s.add(ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                          content_html='<a href="/products/active-mix/">x</a>',
                          content_text=""))
    s.commit()

    run_tag_products(s, fuzzy_threshold=0.85); s.commit()
    run_tag_products(s, fuzzy_threshold=0.85); s.commit()

    mentions = s.execute(select(ContentProductMention)).scalars().all()
    assert len(mentions) == 1
