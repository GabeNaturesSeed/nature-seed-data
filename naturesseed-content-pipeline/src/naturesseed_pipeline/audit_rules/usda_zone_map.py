"""Rule #7 — references to pre-2023 USDA hardiness zone map.

Two-stage: regex filter → LLM judge.
"""

import json
import re

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding

_FILTER_PATTERN = re.compile(
    r"(hardiness zone map|USDA\s+(?:plant\s+)?map|USDA.*(?:2012|pre.?2023))",
    re.IGNORECASE,
)


class UsdaZoneMapRule:
    name = "UsdaZoneMapRule"
    severity = "warning"

    def _extract_candidates(self, text: str, ctx_chars: int = 200) -> list[str]:
        out: list[str] = []
        for m in _FILTER_PATTERN.finditer(text):
            lo = max(0, m.start() - ctx_chars); hi = min(len(text), m.end() + ctx_chars)
            out.append(text[lo:hi])
        return out

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        text = content.content_text or ""
        candidates = self._extract_candidates(text)
        if not candidates:
            return []
        if ctx.llm_client is None or ctx.llm_token_budget_remaining <= 0:
            return []

        prompt = (
            "For each snippet below, determine whether it references the "
            "pre-2023 USDA plant hardiness zone map (outdated) or the 2023-updated "
            "version (current). Return a JSON array with keys: snippet, is_outdated, reason.\n\n"
            + "\n---\n".join(f"[{i}] {c}" for i, c in enumerate(candidates))
        )
        resp = ctx.llm_client.messages.create(
            model=ctx.llm_model, max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            if raw.endswith("```"):
                raw = raw[:-3]
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []

        findings: list[Finding] = []
        for item in parsed:
            if not item.get("is_outdated"):
                continue
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet=item.get("snippet", "")[:300],
                suggested_action=(
                    "Update USDA zone map reference to the 2023 version. "
                    f"Reason: {item.get('reason', '')}"
                ),
            ))
        return findings
