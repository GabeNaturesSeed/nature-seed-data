from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.usda_zone_map import UsdaZoneMapRule
from naturesseed_pipeline.db.models import Base, ContentInventory


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_fires_when_regex_matches_and_llm_confirms():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="Use the 2012 USDA plant hardiness zone map to decide.")
    s.add(c); s.commit()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='[{"snippet": "2012 USDA plant hardiness zone map",'
                                '"is_outdated": true, "reason": "references old map"}]')]
    )
    ctx = AuditContext(session=s, current_shipping="", llm_client=mock_client)
    findings = UsdaZoneMapRule().check(c, ctx)
    assert len(findings) == 1


def test_silent_when_no_regex_match():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="Nothing related here.")
    s.add(c); s.commit()
    ctx = AuditContext(session=s, current_shipping="", llm_client=MagicMock())
    assert UsdaZoneMapRule().check(c, ctx) == []


def test_silent_when_regex_matches_but_llm_says_current():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="See the USDA plant hardiness zone map (2023 update).")
    s.add(c); s.commit()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='[{"snippet": "USDA plant hardiness zone map (2023 update)",'
                                '"is_outdated": false}]')]
    )
    ctx = AuditContext(session=s, current_shipping="", llm_client=mock_client)
    assert UsdaZoneMapRule().check(c, ctx) == []
