"""Rule #11 — missing H1, target keyword, or JSON-LD schema markup."""

import re

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding

_H1_PATTERN = re.compile(r"<h1[^>]*>", re.IGNORECASE)
_JSONLD_PATTERN = re.compile(r'<script[^>]+type="application/ld\+json"', re.IGNORECASE)


class SchemaGapRule:
    name = "SchemaGapRule"
    severity = "info"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        findings: list[Finding] = []
        html = content.content_html or ""
        if not _H1_PATTERN.search(html):
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet="No <h1> tag found",
                suggested_action="Add an H1 heading that includes the target keyword",
            ))
        if not (content.target_keyword or "").strip():
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet="target_keyword is empty",
                suggested_action="Set a target keyword for this article",
            ))
        if not _JSONLD_PATTERN.search(html):
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet="No JSON-LD structured data",
                suggested_action="Add Article or HowTo JSON-LD schema markup",
            ))
        return findings
