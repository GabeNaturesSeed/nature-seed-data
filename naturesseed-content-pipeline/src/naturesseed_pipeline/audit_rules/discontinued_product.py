"""Rule #1 — article mentions a product with WC status='draft'."""

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import OrphanReference


class DiscontinuedProductRule:
    name = "DiscontinuedProductRule"
    severity = "critical"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        rows = ctx.session.execute(
            select(OrphanReference).where(
                OrphanReference.content_inventory_id == content.id,
                OrphanReference.reference_type == "inactive_product",
                OrphanReference.status == "flagged",
            )
        ).scalars().all()
        return [
            Finding(
                rule_name=self.name, severity=self.severity,
                snippet=r.snippet or "",
                suggested_action=(
                    f"Replace mention of '{r.reference_value}' with a "
                    f"currently-sold product or remove section"
                ),
            )
            for r in rows
        ]
