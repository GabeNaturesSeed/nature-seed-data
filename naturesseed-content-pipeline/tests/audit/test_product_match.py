"""Product matcher built from wc_catalog_snapshot rows."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Base, WcCatalogSnapshot
from naturesseed_pipeline.pipelines.audit.product_match import (
    build_matcher, ProductMatch, find_product_mentions,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def _seed(s):
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="fine-fescue-grass-seed-mix",
                            name="Fine Fescue Grass Seed Mix", status="publish",
                            permalink="https://naturesseed.com/products/fine-fescue-grass-seed-mix/",
                            species_list=["fine fescue"]))
    s.add(WcCatalogSnapshot(wp_product_id=2, slug="old-pasture-mix",
                            name="Old Pasture Mix", status="draft",
                            permalink="https://naturesseed.com/products/old-pasture-mix/",
                            species_list=["alfalfa", "clover"]))
    s.commit()


def test_build_matcher_indexes_all():
    s = _session(); _seed(s)
    m = build_matcher(s)
    assert "fine-fescue-grass-seed-mix" in m.by_slug
    assert "old-pasture-mix" in m.by_slug
    assert m.by_slug["old-pasture-mix"].status == "draft"


def test_find_mentions_url_match():
    s = _session(); _seed(s)
    m = build_matcher(s)
    html = 'Check <a href="https://naturesseed.com/products/fine-fescue-grass-seed-mix/">this</a>.'
    matches = find_product_mentions("", html, m, fuzzy_threshold=0.85)
    assert len(matches) == 1
    assert matches[0].wp_product_id == 1
    assert matches[0].match_type == "url"
    assert matches[0].is_active is True


def test_find_mentions_exact_name():
    s = _session(); _seed(s)
    m = build_matcher(s)
    text = "We love our Old Pasture Mix for clients."
    matches = find_product_mentions(text, "", m, fuzzy_threshold=0.85)
    assert len(matches) == 1
    assert matches[0].wp_product_id == 2
    assert matches[0].match_type == "exact"
    assert matches[0].is_active is False


def test_find_mentions_fuzzy():
    s = _session(); _seed(s)
    m = build_matcher(s)
    text = "Our fine fescue grass-seed mix is great."
    matches = find_product_mentions(text, "", m, fuzzy_threshold=0.85)
    assert any(x.wp_product_id == 1 for x in matches)


def test_find_mentions_dedupes_url_beats_exact():
    s = _session(); _seed(s)
    m = build_matcher(s)
    html = '<a href="/products/fine-fescue-grass-seed-mix/">Fine Fescue Grass Seed Mix</a>'
    text = "Fine Fescue Grass Seed Mix"
    matches = find_product_mentions(text, html, m, fuzzy_threshold=0.85)
    by_id = {p.wp_product_id: p for p in matches}
    assert by_id[1].match_type == "url"  # url wins over exact
