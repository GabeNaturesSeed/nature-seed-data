import hashlib
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import (
    Base, ContentInventory, DecayFinding, RefreshQueue,
)
from naturesseed_pipeline.pipelines.audit.scan_decay import run_scan_decay


class AlwaysFiresRule:
    name = "AlwaysFires"
    severity = "warning"

    def check(self, content, ctx):
        return [Finding(rule_name=self.name, severity=self.severity,
                        snippet="fires", suggested_action="fix it")]


class NeverFiresRule:
    name = "NeverFires"
    severity = "info"

    def check(self, content, ctx): return []


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_scan_decay_creates_findings_and_refresh_row():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.commit()

    counts = run_scan_decay(s, rules=[AlwaysFiresRule()], current_shipping="",
                            llm_client=None)
    s.commit()

    findings = s.execute(select(DecayFinding)).scalars().all()
    assert len(findings) == 1 and findings[0].status == "open"
    refresh = s.execute(select(RefreshQueue)).scalars().all()
    assert len(refresh) == 1 and "AlwaysFires" in refresh[0].reason


def test_scan_decay_reconciles_stale_to_resolved():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.commit()

    # First run: AlwaysFires fires
    run_scan_decay(s, rules=[AlwaysFiresRule()], current_shipping="", llm_client=None)
    s.commit()
    # Second run: only NeverFires runs → prior finding becomes stale → resolved
    run_scan_decay(s, rules=[NeverFiresRule()], current_shipping="", llm_client=None)
    s.commit()

    findings = s.execute(select(DecayFinding)).scalars().all()
    assert len(findings) == 1
    assert findings[0].status == "resolved"
    assert findings[0].resolved_at is not None

    refresh = s.execute(select(RefreshQueue)).scalars().all()
    assert len(refresh) == 0


def test_scan_decay_idempotent_same_rule_same_run():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.commit()
    run_scan_decay(s, rules=[AlwaysFiresRule()], current_shipping="", llm_client=None); s.commit()
    run_scan_decay(s, rules=[AlwaysFiresRule()], current_shipping="", llm_client=None); s.commit()
    findings = s.execute(select(DecayFinding)).scalars().all()
    assert len(findings) == 1  # deduped on (content, rule, snippet_hash)
