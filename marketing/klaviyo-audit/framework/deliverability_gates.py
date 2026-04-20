"""Deliverability gate checker (spec §2.2).

Four gates that must all pass (rolling 30d) before aggressive-mode
cadence is unlocked:
    1. Net list growth >= 0
    2. Spam complaint rate < 0.1%
    3. Hard bounce rate < 1%
    4. Unsubscribe rate < 0.3% per send
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Gate:
    name: str
    threshold: float
    current: float
    passing: bool
    comparator: str  # "gte" or "lt" — human-readable


@dataclass
class GateStatus:
    gates: List[Gate]

    @property
    def all_pass(self) -> bool:
        return all(g.passing for g in self.gates)

    @property
    def mode_unlocked(self) -> bool:
        return self.all_pass

    def summary_markdown(self) -> str:
        lines = ["| Gate | Threshold | Current | Status |", "|---|---|---|---|"]
        for g in self.gates:
            icon = "✅" if g.passing else "❌"
            op = "≥" if g.comparator == "gte" else "<"
            lines.append(
                f"| {g.name} | {op} {g.threshold} | {g.current} | {icon} |"
            )
        return "\n".join(lines)


GATE_SPECS = [
    ("net_list_growth", "net_list_growth_30d", 0.0, "gte"),
    ("spam_rate", "spam_rate_30d", 0.001, "lt"),       # 0.1%
    ("bounce_rate", "bounce_rate_30d", 0.01, "lt"),     # 1%
    ("unsub_rate", "unsub_rate_per_send_30d", 0.003, "lt"),  # 0.3%
]


def check_all_gates(metrics: Dict[str, float]) -> GateStatus:
    """Evaluate all four gates from a metrics dict."""
    gates: List[Gate] = []
    for name, metric_key, threshold, comparator in GATE_SPECS:
        current = metrics.get(metric_key, 0.0)
        if comparator == "gte":
            passing = current >= threshold
        else:  # "lt"
            passing = current < threshold
        gates.append(Gate(
            name=name,
            threshold=threshold,
            current=current,
            passing=passing,
            comparator=comparator,
        ))
    return GateStatus(gates=gates)
