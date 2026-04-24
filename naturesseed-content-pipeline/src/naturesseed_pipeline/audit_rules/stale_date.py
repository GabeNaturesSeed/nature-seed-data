"""Rule #6 — article mentions pre-2023 calendar years.

Flags standalone year tokens \\b(19\\d{2}|20[0-1]\\d|202[0-2])\\b.
"""

import re

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding

_YEAR_PATTERN = re.compile(r"\b(19\d{2}|20[0-1]\d|202[0-2])\b")


class StaleDateRule:
    name = "StaleDateRule"
    severity = "warning"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        text = content.content_text or ""
        findings: list[Finding] = []
        seen_years: set[str] = set()
        for m in _YEAR_PATTERN.finditer(text):
            year = m.group(1)
            if year in seen_years:
                continue
            seen_years.add(year)
            lo = max(0, m.start() - 60); hi = min(len(text), m.end() + 60)
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet=text[lo:hi],
                suggested_action=f"Reference to {year} may be stale — verify and update",
            ))
        return findings
