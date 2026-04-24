"""Verify the 6 new audit tables can be created and related."""

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    Base, ContentInventory,
    Topic, ContentTopic, ContentProductMention,
    OutboundLink, DecayFinding, WcCatalogSnapshot,
)


def _make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_topic_self_reference_parent_child():
    s = _make_session()
    parent = Topic(name="Grass Seed", slug="grass-seed", wc_category_slug="grass-seed",
                   source="wc_category", approved=1)
    s.add(parent); s.flush()
    child = Topic(name="Cool-Season", slug="cool-season", source="llm_proposed",
                  approved=0, parent_topic_id=parent.id)
    s.add(child); s.commit()
    assert child.parent_topic_id == parent.id


def test_content_topic_unique():
    s = _make_session()
    content = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    topic = Topic(name="T", slug="t", source="user_created", approved=1)
    s.add_all([content, topic]); s.flush()
    s.add(ContentTopic(content_inventory_id=content.id, topic_id=topic.id,
                       assigned_by="auto", confidence=0.9))
    s.commit()
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        s.add(ContentTopic(content_inventory_id=content.id, topic_id=topic.id,
                           assigned_by="auto", confidence=0.5))
        s.commit()


def test_content_product_mention_unique():
    s = _make_session()
    content = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(content); s.flush()
    s.add(ContentProductMention(content_inventory_id=content.id, wp_product_id=42,
                                product_slug="x", product_name="X", match_type="exact",
                                confidence=0.95))
    s.commit()
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        s.add(ContentProductMention(content_inventory_id=content.id, wp_product_id=42,
                                    product_slug="x", product_name="X", match_type="fuzzy",
                                    confidence=0.85))
        s.commit()


def test_outbound_link_fields():
    s = _make_session()
    src = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    tgt = ContentInventory(url="https://x/b", title="B", slug="b", post_type="post")
    s.add_all([src, tgt]); s.flush()
    link = OutboundLink(content_inventory_id=src.id, href="https://x/b",
                        anchor_text="B", link_type="internal_content",
                        target_content_id=tgt.id, http_status=200,
                        last_checked_at=datetime.now(timezone.utc))
    s.add(link); s.commit()
    assert link.target_content_id == tgt.id


def test_decay_finding_status_default():
    s = _make_session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    f = DecayFinding(content_inventory_id=c.id, rule_name="ThinContentRule",
                    severity="info", snippet="...", suggested_action="expand")
    s.add(f); s.commit()
    assert f.status == "open"


def test_wc_catalog_snapshot_keys_by_product_id():
    s = _make_session()
    s.add(WcCatalogSnapshot(wp_product_id=99, slug="zzz", name="Zzz",
                            status="publish", species_list=["alfalfa"], price=9.99,
                            permalink="https://x/products/zzz/"))
    s.commit()
    row = s.get(WcCatalogSnapshot, 99)
    assert row.status == "publish"
    assert row.species_list == ["alfalfa"]
