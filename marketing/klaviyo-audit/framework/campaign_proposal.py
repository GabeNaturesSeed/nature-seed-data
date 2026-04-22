"""Campaign proposal evaluator — implements spec §4.1 six-check decision tree.

Every broadcast must pass all 6 checks. Failing any one = auto-rejected.
"""
from dataclasses import dataclass
from typing import Optional

# Segments explicitly starred in CLAUDE.md / spec §1.3 — only these are valid audience targets
STARRED_SEGMENTS = {
    # RFM lifecycle
    "VtKptn",  # Champions Active
    "RAQTca",  # Champions
    "RbGRqF",  # Active This Season
    "T93fB3",  # New
    "WdpJti",  # Warm
    "RyASXF",  # At Risk
    "Sv5cSC",  # Lapsed
    "WjzuUj",  # Dormant
    # Engagement tiers
    "VKVpf9",  # E30D
    "RbH7na",  # E60D
    "VduUfa",  # E90D
}

MAX_OFFER_PCT = 0.15          # spec §2.3
MIN_RPR_TARGETED = 0.50       # spec §4.1
MIN_RPR_BROAD = 0.15          # spec §4.1


@dataclass
class ProposalCheck:
    name: str
    goal: Optional[str]
    audience_segment_id: str
    sends_past_7d: int
    cadence_cap: int
    has_suppression_exclusions: bool
    offer_pct: Optional[float]
    expected_rpr: float
    target_type: str  # "targeted" | "broad"

    @property
    def goal_pass(self) -> bool:
        return bool(self.goal)

    @property
    def audience_pass(self) -> bool:
        return self.audience_segment_id in STARRED_SEGMENTS

    @property
    def cadence_pass(self) -> bool:
        return self.sends_past_7d < self.cadence_cap

    @property
    def suppression_pass(self) -> bool:
        return self.has_suppression_exclusions

    @property
    def offer_pass(self) -> bool:
        if self.offer_pct is None:
            return True
        return self.offer_pct <= MAX_OFFER_PCT

    @property
    def rpr_pass(self) -> bool:
        min_rpr = MIN_RPR_TARGETED if self.target_type == "targeted" else MIN_RPR_BROAD
        return self.expected_rpr >= min_rpr

    @property
    def all_pass(self) -> bool:
        return all([
            self.goal_pass,
            self.audience_pass,
            self.cadence_pass,
            self.suppression_pass,
            self.offer_pass,
            self.rpr_pass,
        ])

    def to_markdown(self) -> str:
        offer_detail = f"{self.offer_pct * 100:.0f}%" if self.offer_pct is not None else "none"
        min_rpr = MIN_RPR_TARGETED if self.target_type == "targeted" else MIN_RPR_BROAD
        checks = [
            ("1. Goal", self.goal_pass, self.goal or "None — no business goal defined"),
            ("2. Audience", self.audience_pass, f"`{self.audience_segment_id}` {'✓ starred' if self.audience_pass else '✗ not in starred segments'}"),
            ("3. Cadence", self.cadence_pass, f"{self.sends_past_7d} sends in last 7d vs cap of {self.cadence_cap}"),
            ("4. Suppression", self.suppression_pass, "exclusions applied" if self.suppression_pass else "MISSING — add bought-48hr, in-active-flow, NOT-E90 exclusions"),
            ("5. Offer", self.offer_pass, f"{offer_detail} vs {MAX_OFFER_PCT * 100:.0f}% cap"),
            ("6. RPR target", self.rpr_pass, f"${self.expected_rpr:.2f} vs ${min_rpr:.2f} min ({self.target_type})"),
        ]
        rows = "\n".join(
            f"| {name} | {'✅' if ok else '❌'} | {detail} |"
            for name, ok, detail in checks
        )
        verdict = "✅ APPROVED — ready to schedule" if self.all_pass else "❌ REJECTED — fix failing checks above"
        return (
            f"## Campaign Proposal: {self.name}\n\n"
            f"| Check | Status | Detail |\n"
            f"|---|---|---|\n"
            f"{rows}\n\n"
            f"**Verdict:** {verdict}\n"
        )


def evaluate_proposal(
    name: str,
    goal: Optional[str],
    audience_segment_id: str,
    sends_past_7d: int,
    cadence_cap: int,
    has_suppression_exclusions: bool,
    offer_pct: Optional[float],
    expected_rpr: float,
    target_type: str,
) -> ProposalCheck:
    """Run all 6 spec §4.1 checks and return a ProposalCheck."""
    return ProposalCheck(
        name=name,
        goal=goal,
        audience_segment_id=audience_segment_id,
        sends_past_7d=sends_past_7d,
        cadence_cap=cadence_cap,
        has_suppression_exclusions=has_suppression_exclusions,
        offer_pct=offer_pct,
        expected_rpr=expected_rpr,
        target_type=target_type,
    )
