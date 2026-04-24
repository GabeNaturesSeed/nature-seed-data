"""Media listener agent — classifies raw signals for relevance and trend potential.

For each captured signal:
- Relevance: is this about seeds/gardening/plants? (0-1)
- Trend: is this an emerging topic or stale/evergreen? (0-1)
- Topic extraction: what's the core topic?

Uses keyword heuristics (no LLM call needed for classification at this scale).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta

from naturesseed_pipeline.integrations.media_sources import RawSignal

# Gardening/seed relevance keywords — weighted by specificity
_RELEVANCE_KEYWORDS: list[tuple[str, float]] = [
    # High relevance (0.3 each)
    (r"\bseed\s?start", 0.3),
    (r"\bgermination\b", 0.3),
    (r"\bseed\s?saving\b", 0.3),
    (r"\bcover\s?crop\b", 0.3),
    (r"\bpollinator\b", 0.3),
    (r"\bnative\s+plants?\b", 0.3),
    (r"\bwildflower\b", 0.3),
    (r"\bgrass\s+seed\b", 0.3),
    (r"\blawn\s+seed\b", 0.3),
    (r"\bseed\s+mix\b", 0.3),
    (r"\bplanting\s+zone\b", 0.3),
    # Medium relevance (0.2 each)
    (r"\bseed(?:s|ing)?\b", 0.2),
    (r"\bgarden(?:ing)?\b", 0.2),
    (r"\bvegetable\s+garden\b", 0.2),
    (r"\braised\s+bed\b", 0.2),
    (r"\bcompost(?:ing)?\b", 0.2),
    (r"\bsoil\s+amendment\b", 0.2),
    (r"\bpermaculture\b", 0.2),
    (r"\borganic\s+(?:garden|farm|grow)", 0.2),
    (r"\bheirloom\b", 0.2),
    (r"\bno.till\b", 0.2),
    # Low relevance (0.1 each)
    (r"\bplant(?:s|ing)?\b", 0.1),
    (r"\bgrow(?:ing)?\b", 0.1),
    (r"\bharvest\b", 0.1),
    (r"\bfertiliz", 0.1),
    (r"\birrigat", 0.1),
    (r"\bmulch\b", 0.1),
    (r"\bdrought", 0.1),
]

# Trend signals — indicators of emerging/timely content
_TREND_KEYWORDS: list[tuple[str, float]] = [
    (r"\b202[5-9]\b", 0.2),
    (r"\bnew\b", 0.15),
    (r"\btrend(?:s|ing)?\b", 0.3),
    (r"\bviral\b", 0.25),
    (r"\bgame.changer\b", 0.2),
    (r"\bjust\s+released\b", 0.25),
    (r"\bbreakthrough\b", 0.2),
    (r"\bfirst\s+time\b", 0.15),
    (r"\bsurpris", 0.15),
    (r"\bunexpected\b", 0.15),
]


def _score_text(text: str, patterns: list[tuple[str, float]], cap: float = 1.0) -> float:
    """Score text against weighted regex patterns, capped at cap."""
    text_lower = text.lower()
    score = 0.0
    for pattern, weight in patterns:
        if re.search(pattern, text_lower):
            score += weight
    return min(score, cap)


def classify_signal(signal: RawSignal) -> dict[str, float | str]:
    """Classify a raw signal for relevance, trend potential, and topic.

    Returns:
        dict with keys: relevance_score, trending_score, topic
    """
    combined_text = f"{signal.title} {signal.text}"

    relevance = _score_text(combined_text, _RELEVANCE_KEYWORDS)
    trending = _score_text(combined_text, _TREND_KEYWORDS)

    # Boost trending score for recent content
    if signal.published_at:
        age_days = (datetime.now(timezone.utc) - signal.published_at).days
        if age_days <= 1:
            trending = min(trending + 0.2, 1.0)
        elif age_days <= 3:
            trending = min(trending + 0.1, 1.0)
        elif age_days > 30:
            trending = max(trending - 0.2, 0.0)

    # Boost relevance for signals from gardening-specific sources
    if signal.source_type == "reddit" and any(
        s in signal.source_name.lower()
        for s in ["garden", "seed", "permaculture"]
    ):
        relevance = min(relevance + 0.2, 1.0)

    # Extract primary topic from title
    topic = _extract_topic(signal.title)

    return {
        "relevance_score": round(relevance, 2),
        "trending_score": round(trending, 2),
        "topic": topic,
    }


def _extract_topic(title: str) -> str:
    """Extract the core topic from a title. Simple heuristic."""
    # Remove common prefixes/noise
    cleaned = re.sub(
        r"^(how\s+to|why|what|when|the\s+best|top\s+\d+|my|i)\s+",
        "",
        title.lower().strip(),
        flags=re.IGNORECASE,
    )
    # Trim to first clause
    for sep in ["—", "-", "|", ":", "?"]:
        if sep in cleaned:
            cleaned = cleaned.split(sep)[0].strip()
    # Cap length
    words = cleaned.split()[:8]
    return " ".join(words).strip()
