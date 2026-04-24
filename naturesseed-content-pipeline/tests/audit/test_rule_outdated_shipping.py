from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.outdated_shipping import OutdatedShippingRule
from naturesseed_pipeline.db.models import Base, ContentInventory


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_fires_when_filter_hits_and_llm_confirms():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="Free shipping on orders over $49!")
    s.add(c); s.commit()
    mock = MagicMock()
    mock.messages.create.return_value = MagicMock(
        content=[MagicMock(text='[{"snippet": "Free shipping on orders over $49",'
                                '"is_outdated": true, "reason": "current threshold is $99"}]')]
    )
    ctx = AuditContext(session=s, current_shipping="Free shipping over $99",
                       llm_client=mock)
    assert len(OutdatedShippingRule().check(c, ctx)) == 1


def test_silent_when_no_filter_hit():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="Pure content, no shipping.")
    s.add(c); s.commit()
    ctx = AuditContext(session=s, current_shipping="Free shipping over $99",
                       llm_client=MagicMock())
    assert OutdatedShippingRule().check(c, ctx) == []
