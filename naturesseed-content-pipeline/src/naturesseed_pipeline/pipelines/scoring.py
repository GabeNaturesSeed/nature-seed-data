"""Keyword backlog scoring — bridge between research and writing.

Scores each KeywordCandidate on a weighted combination of:
- Search volume (log-scaled, 0-1)
- Intent fit (commercial/transactional > informational for a retailer)
- Keyword difficulty (inverted — easier = higher score)
- Gap score (higher = bigger opportunity)
- Seasonality boost (is now a peak month?)
- Media signal corroboration (trending topics in media_signals)

Weights are configurable via .env / config.py.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func as sqlfunc
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.config import settings
from naturesseed_pipeline.db.models import KeywordCandidate, MediaSignal

log = structlog.get_logger()

# Intent fitness for a seed retailer: transactional > commercial > informational
_INTENT_SCORES: dict[str, float] = {
    "transactional": 1.0,
    "commercial": 0.8,
    "navigational": 0.3,
    "informational": 0.4,
}

# Log-scale volume normalization: volumes above this are capped at 1.0
_VOLUME_CAP = 50_000


def _norm_volume(volume: int | None) -> float:
    """Log-scaled normalization of search volume to 0-1."""
    if not volume or volume <= 0:
        return 0.0
    return min(math.log1p(volume) / math.log1p(_VOLUME_CAP), 1.0)


def _norm_intent(intent: str | None) -> float:
    """Map intent label to fitness score."""
    return _INTENT_SCORES.get(intent or "informational", 0.4)


def _norm_difficulty(difficulty: float | None) -> float:
    """Invert difficulty so easier keywords score higher. 0-1."""
    if difficulty is None:
        return 0.5  # unknown = neutral
    return max(0.0, 1.0 - (difficulty / 100.0))


def _norm_gap(gap_score: float | None) -> float:
    """Gap score is already 0-1 (higher = bigger opportunity)."""
    return gap_score if gap_score is not None else 0.5


def _seasonality_boost(seasonality: dict | None) -> float:
    """Return 1.0 if current month is a peak month, else 0.0."""
    if not seasonality:
        return 0.0
    peak_months = seasonality.get("peak_months", [])
    current_month = datetime.now(timezone.utc).month
    return 1.0 if current_month in peak_months else 0.0


def _media_corroboration(keyword: str, session: Session) -> float:
    """Check if keyword topic is corroborated by recent media signals.

    Returns 1.0 if a recent high-relevance signal mentions the keyword,
    0.5 for moderate match, 0.0 for no match.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    # Search for signals where title contains the keyword (case-insensitive)
    kw_lower = keyword.lower()

    count = session.execute(
        select(sqlfunc.count())
        .select_from(MediaSignal)
        .where(
            MediaSignal.captured_at >= cutoff,
            MediaSignal.relevance_score >= 0.5,
            sqlfunc.lower(MediaSignal.title).contains(kw_lower),
        )
    ).scalar() or 0

    if count >= 3:
        return 1.0
    elif count >= 1:
        return 0.5
    return 0.0


def score_keyword(kw: KeywordCandidate, session: Session) -> float:
    """Compute a weighted priority score for a keyword candidate."""
    w = settings

    vol = _norm_volume(kw.search_volume) * w.score_weight_volume
    intent = _norm_intent(kw.intent) * w.score_weight_intent
    diff = _norm_difficulty(kw.keyword_difficulty) * w.score_weight_difficulty
    gap = _norm_gap(kw.gap_score) * w.score_weight_gap
    season = _seasonality_boost(kw.seasonality) * w.score_weight_seasonality
    media = _media_corroboration(kw.keyword, session) * w.score_weight_media

    total = vol + intent + diff + gap + season + media
    return round(total, 4)


def rank_backlog(session: Session, limit: int = 50) -> list[tuple[KeywordCandidate, float]]:
    """Score all keyword_candidates and return top N ranked by priority.

    Also persists the priority_score on each candidate.
    """
    candidates = session.execute(
        select(KeywordCandidate)
        .where(KeywordCandidate.status.in_(["new", "scored"]))
    ).scalars().all()

    scored: list[tuple[KeywordCandidate, float]] = []
    for kw in candidates:
        s = score_keyword(kw, session)
        kw.priority_score = s
        kw.status = "scored"
        scored.append((kw, s))

    scored.sort(key=lambda x: -x[1])
    session.commit()

    log.info("backlog_ranked", total=len(scored), top_score=scored[0][1] if scored else 0)
    return scored[:limit]
