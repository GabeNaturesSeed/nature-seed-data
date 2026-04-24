"""Rule #4 — outbound external links returning 4xx/5xx."""

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import OutboundLink


class DeadExternalLinkRule:
    name = "DeadExternalLinkRule"
    severity = "warning"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        rows = ctx.session.execute(
            select(OutboundLink).where(
                OutboundLink.content_inventory_id == content.id,
                OutboundLink.link_type == "external",
                OutboundLink.http_status.isnot(None),
            )
        ).scalars().all()
        findings: list[Finding] = []
        for r in rows:
            if r.http_status in (200, 301, 302, 303, 304, 307, 308) or r.http_status is None:
                continue
            if r.http_status >= 400 or r.http_status == 0:
                findings.append(Finding(
                    rule_name=self.name, severity=self.severity,
                    snippet=f"{r.href} → HTTP {r.http_status}",
                    suggested_action=f"Remove or replace dead link to {r.href}",
                ))
        return findings
