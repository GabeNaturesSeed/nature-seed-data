from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.stale_date import StaleDateRule
from naturesseed_pipeline.audit_rules.thin_content import ThinContentRule
from naturesseed_pipeline.audit_rules.schema_gap import SchemaGapRule
from naturesseed_pipeline.db.models import Base, ContentInventory


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_stale_date_fires_on_old_year():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="In 2019, the market was different.")
    s.add(c); s.commit()
    assert len(StaleDateRule().check(c, AuditContext(session=s, current_shipping=""))) >= 1


def test_stale_date_silent_on_recent_year():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="Updated in 2026 per latest USDA guidance.")
    s.add(c); s.commit()
    assert StaleDateRule().check(c, AuditContext(session=s, current_shipping="")) == []


def test_thin_content_fires_below_threshold():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        word_count=50)
    s.add(c); s.commit()
    ctx = AuditContext(session=s, current_shipping="")
    ctx._cache["thin_word_count"] = 300
    assert len(ThinContentRule().check(c, ctx)) == 1


def test_thin_content_silent_above():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        word_count=1000)
    s.add(c); s.commit()
    ctx = AuditContext(session=s, current_shipping="")
    ctx._cache["thin_word_count"] = 300
    assert ThinContentRule().check(c, ctx) == []


def test_schema_gap_fires_when_h1_missing():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_html="<div>no h1</div>", target_keyword=None)
    s.add(c); s.commit()
    findings = SchemaGapRule().check(c, AuditContext(session=s, current_shipping=""))
    assert len(findings) >= 2  # missing h1 + missing target keyword
