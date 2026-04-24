"""Rule #8 — shipping claims that don't match current policy.

Two-stage: regex filter → LLM judge vs current_shipping from config.
"""

import json
import re

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding

_FILTER_PATTERN = re.compile(
    r"(free shipping|ships? in \d+\s*(?:day|business)|"
    r"\$\d{1,3}\s+(?:shipping|threshold|minimum)|"
    r"\b(?:UPS|FedEx|USPS)\b)",
    re.IGNORECASE,
)


class OutdatedShippingRule:
    name = "OutdatedShippingRule"
    severity = "warning"

    def _extract_candidates(self, text: str, ctx_chars: int = 150) -> list[str]:
        out: list[str] = []
        for m in _FILTER_PATTERN.finditer(text):
            lo = max(0, m.start() - ctx_chars); hi = min(len(text), m.end() + ctx_chars)
            out.append(text[lo:hi])
        return out

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        text = content.content_text or ""
        candidates = self._extract_candidates(text)
        if not candidates or ctx.llm_client is None:
            return []

        prompt = (
            f"Current Nature's Seed shipping policy: {ctx.current_shipping}\n\n"
            "For each snippet, determine whether the shipping claim matches "
            "the current policy. Return JSON array with keys: snippet, is_outdated, reason.\n\n"
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
                    f"Update shipping claim to match current policy. "
                    f"Reason: {item.get('reason', '')}"
                ),
            ))
        return findings
