from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.missing_product_card import MissingProductCardRule
from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentProductMention, OutboundLink, WcCatalogSnapshot,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_fires_when_product_mentioned_but_not_linked():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="foo", name="Foo",
                           status="publish",
                           permalink="https://naturesseed.com/products/foo/"))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(ContentProductMention(content_inventory_id=c.id, wp_product_id=1,
                               product_slug="foo", product_name="Foo",
                               match_type="exact", confidence=0.9))
    s.commit()
    ctx = AuditContext(session=s, current_shipping="")
    assert len(MissingProductCardRule().check(c, ctx)) == 1


def test_silent_when_product_is_linked():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="foo", name="Foo",
                           status="publish",
                           permalink="https://naturesseed.com/products/foo/"))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(ContentProductMention(content_inventory_id=c.id, wp_product_id=1,
                               product_slug="foo", product_name="Foo",
                               match_type="exact", confidence=0.9))
    s.add(OutboundLink(content_inventory_id=c.id,
                      href="https://naturesseed.com/products/foo/",
                      link_type="internal_product"))
    s.commit()
    ctx = AuditContext(session=s, current_shipping="")
    assert MissingProductCardRule().check(c, ctx) == []
