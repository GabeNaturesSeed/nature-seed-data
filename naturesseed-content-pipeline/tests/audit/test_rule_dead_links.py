from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.dead_external_link import DeadExternalLinkRule
from naturesseed_pipeline.audit_rules.dead_internal_link import DeadInternalLinkRule
from naturesseed_pipeline.audit_rules.product_category_url import ProductCategoryUrlRule
from naturesseed_pipeline.db.models import Base, ContentInventory, OutboundLink


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_dead_external_fires_on_404():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OutboundLink(content_inventory_id=c.id, href="https://dead.com",
                      link_type="external", http_status=404))
    s.commit()
    findings = DeadExternalLinkRule().check(c, AuditContext(session=s, current_shipping=""))
    assert len(findings) == 1


def test_dead_external_silent_on_200():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OutboundLink(content_inventory_id=c.id, href="https://ok.com",
                      link_type="external", http_status=200))
    s.commit()
    assert DeadExternalLinkRule().check(c, AuditContext(session=s, current_shipping="")) == []


def test_dead_internal_fires_when_target_missing():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OutboundLink(content_inventory_id=c.id,
                      href="https://naturesseed.com/gone/",
                      link_type="internal_content", target_content_id=None))
    s.commit()
    assert len(DeadInternalLinkRule().check(c, AuditContext(session=s, current_shipping=""))) == 1


def test_dead_internal_fires_when_target_is_draft():
    s = _session()
    tgt = ContentInventory(url="https://x/b", title="B", slug="b", post_type="post",
                          status="draft")
    src = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add_all([src, tgt]); s.flush()
    s.add(OutboundLink(content_inventory_id=src.id,
                      href="https://naturesseed.com/b/",
                      link_type="internal_content", target_content_id=tgt.id))
    s.commit()
    assert len(DeadInternalLinkRule().check(src, AuditContext(session=s, current_shipping=""))) == 1


def test_product_category_url_rule():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OutboundLink(content_inventory_id=c.id,
                      href="https://naturesseed.com/product-category/grass-seed/",
                      link_type="internal_content"))
    s.commit()
    findings = ProductCategoryUrlRule().check(c, AuditContext(session=s, current_shipping=""))
    assert len(findings) == 1
    assert findings[0].severity == "critical"
