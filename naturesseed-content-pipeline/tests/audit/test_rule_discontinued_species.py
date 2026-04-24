from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.discontinued_species import DiscontinuedSpeciesRule
from naturesseed_pipeline.db.models import (
    Base, ContentInventory, OrphanReference, WcCatalogSnapshot,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_fires_on_species_not_in_any_publish_product():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="m", name="M", status="publish",
                           species_list=["fescue"], permalink=""))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OrphanReference(content_inventory_id=c.id,
                         reference_type="species_mention",
                         reference_value="alfalfa",
                         match_confidence=1.0, snippet="...alfalfa...",
                         status="flagged"))
    s.commit()

    findings = DiscontinuedSpeciesRule().check(c, AuditContext(session=s, current_shipping=""))
    assert len(findings) == 1
    assert findings[0].severity == "critical"


def test_silent_when_species_exists_in_active():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="m", name="M", status="publish",
                           species_list=["fescue"], permalink=""))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OrphanReference(content_inventory_id=c.id,
                         reference_type="species_mention",
                         reference_value="fescue",
                         match_confidence=1.0, snippet="...fescue...",
                         status="flagged"))
    s.commit()
    assert DiscontinuedSpeciesRule().check(c, AuditContext(session=s, current_shipping="")) == []
