from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.discontinued_product import DiscontinuedProductRule
from naturesseed_pipeline.db.models import (
    Base, ContentInventory, OrphanReference,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_fires_on_inactive_product_orphan_ref():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OrphanReference(
        content_inventory_id=c.id,
        reference_type="inactive_product",
        reference_value="old-mix",
        match_confidence=0.95, snippet="...Old Mix...", status="flagged",
    ))
    s.commit()

    ctx = AuditContext(session=s, current_shipping="")
    findings = DiscontinuedProductRule().check(c, ctx)
    assert len(findings) == 1
    assert findings[0].rule_name == "DiscontinuedProductRule"
    assert findings[0].severity == "critical"
    assert "old-mix" in findings[0].suggested_action


def test_silent_when_no_orphan_refs():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.commit()
    ctx = AuditContext(session=s, current_shipping="")
    assert DiscontinuedProductRule().check(c, ctx) == []
