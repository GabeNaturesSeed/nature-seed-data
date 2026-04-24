"""Rule #3 — article mentions an active product but has no link to it."""

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import (
    ContentProductMention, OutboundLink, WcCatalogSnapshot,
)


class MissingProductCardRule:
    name = "MissingProductCardRule"
    severity = "warning"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        mentions = ctx.session.execute(
            select(ContentProductMention).where(
                ContentProductMention.content_inventory_id == content.id
            )
        ).scalars().all()
        if not mentions:
            return []

        links = ctx.session.execute(
            select(OutboundLink).where(
                OutboundLink.content_inventory_id == content.id,
                OutboundLink.link_type == "internal_product",
            )
        ).scalars().all()
        linked_slugs = set()
        for link in links:
            parts = [p for p in (link.href or "").split("/") if p]
            if parts:
                linked_slugs.add(parts[-1].lower())

        findings: list[Finding] = []
        for m in mentions:
            if m.product_slug.lower() in linked_slugs:
                continue
            snap = ctx.session.get(WcCatalogSnapshot, m.wp_product_id)
            permalink = snap.permalink if snap else f"/products/{m.product_slug}/"
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet=m.first_snippet or "",
                suggested_action=f"Add a product card or CTA linking to {permalink}",
            ))
        return findings
