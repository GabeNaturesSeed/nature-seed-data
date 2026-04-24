"""Rule #9 — article mentions a price for a product that drifts >5% from current."""

import re

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import ContentProductMention, WcCatalogSnapshot

_PRICE_PATTERN = re.compile(r"\$\s?(\d{1,5}(?:\.\d{2})?)")


class OutdatedPricingRule:
    name = "OutdatedPricingRule"
    severity = "info"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        text = content.content_text or ""
        if "$" not in text:
            return []
        mentions = ctx.session.execute(
            select(ContentProductMention).where(
                ContentProductMention.content_inventory_id == content.id
            )
        ).scalars().all()
        if not mentions:
            return []

        prices_in_text = [float(m.group(1)) for m in _PRICE_PATTERN.finditer(text)]
        if not prices_in_text:
            return []

        findings: list[Finding] = []
        for m in mentions:
            snap = ctx.session.get(WcCatalogSnapshot, m.wp_product_id)
            if not snap or not snap.price:
                continue
            current = snap.price
            drift = [
                p for p in prices_in_text
                if abs(p - current) / current > 0.05
            ]
            if drift:
                findings.append(Finding(
                    rule_name=self.name, severity=self.severity,
                    snippet=f"text prices {drift} vs current {current}",
                    suggested_action=(
                        f"Verify/update price for {m.product_name} "
                        f"(current: ${current:.2f})"
                    ),
                ))
        return findings
