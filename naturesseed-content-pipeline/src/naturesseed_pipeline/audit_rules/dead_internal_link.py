"""Rule #5 — outbound internal links whose target is missing or not publish."""

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import ContentInventory, OutboundLink


class DeadInternalLinkRule:
    name = "DeadInternalLinkRule"
    severity = "critical"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        rows = ctx.session.execute(
            select(OutboundLink).where(
                OutboundLink.content_inventory_id == content.id,
                OutboundLink.link_type.in_(["internal_content", "internal_product"]),
            )
        ).scalars().all()
        findings: list[Finding] = []
        for r in rows:
            broken = False
            if r.target_content_id is None:
                broken = True
            else:
                tgt = ctx.session.get(ContentInventory, r.target_content_id)
                if tgt is None or tgt.status != "publish":
                    broken = True
            if broken:
                findings.append(Finding(
                    rule_name=self.name, severity=self.severity,
                    snippet=r.href,
                    suggested_action=f"Fix or remove broken internal link to {r.href}",
                ))
        return findings
