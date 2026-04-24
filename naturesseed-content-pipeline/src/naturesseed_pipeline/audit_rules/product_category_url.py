"""Rule #12 — /product-category/ URLs should be /products/."""

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import OutboundLink


class ProductCategoryUrlRule:
    name = "ProductCategoryUrlRule"
    severity = "critical"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        rows = ctx.session.execute(
            select(OutboundLink).where(
                OutboundLink.content_inventory_id == content.id,
                OutboundLink.href.like("%/product-category/%"),
            )
        ).scalars().all()
        return [
            Finding(
                rule_name=self.name, severity=self.severity,
                snippet=r.href,
                suggested_action=(
                    f"Rewrite URL from /product-category/... to /products/... "
                    f"(Permalink Manager mapping). Source: {r.href}"
                ),
            )
            for r in rows
        ]
