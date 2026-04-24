from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.outdated_pricing import OutdatedPricingRule
from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentProductMention, WcCatalogSnapshot,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_fires_when_price_differs_over_5_percent():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="x", name="X", status="publish",
                           price=50.00, permalink=""))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="Our product X is only $35.99 today!")
    s.add(c); s.flush()
    s.add(ContentProductMention(content_inventory_id=c.id, wp_product_id=1,
                               product_slug="x", product_name="X",
                               match_type="exact", confidence=0.9))
    s.commit()
    findings = OutdatedPricingRule().check(c, AuditContext(session=s, current_shipping=""))
    assert len(findings) >= 1


def test_silent_when_price_within_5_percent():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="x", name="X", status="publish",
                           price=50.00, permalink=""))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="X is only $49.99 today!")
    s.add(c); s.flush()
    s.add(ContentProductMention(content_inventory_id=c.id, wp_product_id=1,
                               product_slug="x", product_name="X",
                               match_type="exact", confidence=0.9))
    s.commit()
    assert OutdatedPricingRule().check(c, AuditContext(session=s, current_shipping="")) == []


def test_silent_when_no_dollar_amount():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="x", name="X", status="publish",
                           price=50.00, permalink=""))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="X is a great product.")
    s.add(c); s.flush()
    s.add(ContentProductMention(content_inventory_id=c.id, wp_product_id=1,
                               product_slug="x", product_name="X",
                               match_type="exact", confidence=0.9))
    s.commit()
    assert OutdatedPricingRule().check(c, AuditContext(session=s, current_shipping="")) == []
