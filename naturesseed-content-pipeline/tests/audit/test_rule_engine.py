"""Rule engine — Protocol, AuditContext, discovery mechanism."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules import discover_rules
from naturesseed_pipeline.audit_rules.base import (
    AuditContext, Finding, DecayRule,
)
from naturesseed_pipeline.db.models import Base, ContentInventory


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_finding_fields():
    f = Finding(rule_name="X", severity="critical", snippet="...",
                suggested_action="do this")
    assert f.rule_name == "X" and f.severity == "critical"


def test_audit_context_exposes_session():
    s = _session()
    ctx = AuditContext(session=s, current_shipping="free over $99")
    assert ctx.session is s
    assert ctx.current_shipping == "free over $99"


def test_discover_rules_returns_list():
    """Discovery should collect every DecayRule-conforming class from audit_rules/.
    Tasks 16-23 will add 12 rules; for now the list can be empty (just verify
    the call works and returns a list)."""
    rules = discover_rules()
    assert isinstance(rules, list)


class _DummyRule:
    name = "dummy"
    severity = "info"

    def check(self, content, ctx):
        if "stale" in (content.content_text or ""):
            return [Finding(rule_name=self.name, severity=self.severity,
                           snippet="stale found", suggested_action="refresh")]
        return []


def test_rule_protocol_contract():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="this is stale data")
    s.add(c); s.flush()
    ctx = AuditContext(session=s, current_shipping="")
    findings = _DummyRule().check(c, ctx)
    assert len(findings) == 1
    assert findings[0].snippet == "stale found"
