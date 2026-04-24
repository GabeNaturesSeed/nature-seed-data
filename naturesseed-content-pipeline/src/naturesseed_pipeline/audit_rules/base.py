"""Decay rule protocol + shared context.

A DecayRule reads a ContentInventory row + AuditContext and returns Findings.
Findings become decay_findings rows.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class Finding:
    rule_name: str
    severity: str  # 'critical' | 'warning' | 'info'
    snippet: str
    suggested_action: str


@dataclass
class AuditContext:
    session: Session
    current_shipping: str
    llm_client: object | None = None  # anthropic.Anthropic, lazy
    llm_model: str = "claude-sonnet-4-6"
    llm_token_budget_remaining: int = 50_000
    _cache: dict = field(default_factory=dict)

    def cached(self, key: str, factory):
        if key not in self._cache:
            self._cache[key] = factory()
        return self._cache[key]


@runtime_checkable
class DecayRule(Protocol):
    name: str
    severity: str

    def check(self, content, ctx: AuditContext) -> list[Finding]: ...
