"""Rule #10 — word_count below configurable threshold."""

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding


class ThinContentRule:
    name = "ThinContentRule"
    severity = "info"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        threshold = ctx._cache.get("thin_word_count", 300)
        wc = content.word_count or 0
        if wc >= threshold:
            return []
        return [Finding(
            rule_name=self.name, severity=self.severity,
            snippet=f"word_count={wc}",
            suggested_action=f"Expand content above {threshold} words for SEO depth",
        )]
