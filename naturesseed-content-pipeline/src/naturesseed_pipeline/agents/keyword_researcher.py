"""Keyword researcher agent.

Orchestrates multi-source keyword research:
1. Expand seeds via Google Ads (precise volumes)
2. Pull competitor domains from Ads auction data
3. Cross-reference with GSC for gap scoring
4. Classify search intent
5. Seasonality from Ads historical metrics + Trends
6. Optional DataForSEO enrichment for SERP + true difficulty
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    CompetitorDomain,
    GscQueryPerformance,
    KeywordCandidate,
)
from naturesseed_pipeline.integrations.keyword_research.base import (
    KeywordIdea,
    ResearchRouter,
    SeasonalityRecord,
)

log = structlog.get_logger()

# Intent classification heuristics (avoids API calls for this)
_INTENT_PATTERNS: list[tuple[str, str]] = [
    (r"\b(buy|purchase|order|price|cheap|discount|deal|shop|sale)\b", "transactional"),
    (r"\b(best|top|review|vs|compare|comparison)\b", "commercial"),
    (r"\b(how|what|why|when|where|guide|tutorial|tips|learn)\b", "informational"),
    (r"\b(near me|store|location|directions|hours)\b", "navigational"),
]


def classify_intent(keyword: str) -> str:
    """Classify search intent from keyword text using heuristics."""
    kw_lower = keyword.lower()
    for pattern, intent in _INTENT_PATTERNS:
        if re.search(pattern, kw_lower):
            return intent
    return "informational"  # default


def _compute_gap_score(
    keyword: str,
    gsc_data: dict[str, dict[str, Any]],
) -> tuple[float, str | None, float | None]:
    """Compute gap score: 0 = top 3, 1 = not ranking at all.

    Returns (gap_score, best_url, best_position).
    """
    kw_lower = keyword.lower()
    entry = gsc_data.get(kw_lower)
    if not entry:
        return 1.0, None, None

    position = entry.get("position", 100)
    if position <= 3:
        return 0.0, entry.get("page"), position
    elif position <= 10:
        return 0.2, entry.get("page"), position
    elif position <= 20:
        return 0.5, entry.get("page"), position
    elif position <= 50:
        return 0.7, entry.get("page"), position
    return 0.9, entry.get("page"), position


def research_seeds(
    session: Session,
    router: ResearchRouter,
    seeds: list[str],
    gsc_data: dict[str, dict[str, Any]] | None = None,
) -> list[KeywordCandidate]:
    """Run seed expansion and populate keyword_candidates.

    Steps:
    1. expand_keywords via Google Ads
    2. Cross-reference with GSC data for gap_score
    3. Classify intent
    4. Get seasonality
    5. Upsert into keyword_candidates
    """
    if gsc_data is None:
        gsc_data = {}

    log.info("expanding_seeds", seeds=seeds)
    ideas = router.expand_keywords(seeds)
    log.info("ideas_generated", count=len(ideas))

    candidates: list[KeywordCandidate] = []
    for idea in ideas:
        # Check if already exists
        existing = session.execute(
            select(KeywordCandidate).where(KeywordCandidate.keyword == idea.keyword)
        ).scalar_one_or_none()

        if existing:
            # Update volume/competition if newer data
            existing.search_volume = idea.search_volume
            existing.competition_index = idea.competition_index
            candidates.append(existing)
            continue

        gap_score, best_url, best_pos = _compute_gap_score(idea.keyword, gsc_data)
        intent = classify_intent(idea.keyword)

        # Get seasonality
        seasonality_data = None
        season = router.get_seasonality(idea.keyword)
        if season:
            seasonality_data = {
                "monthly": season.monthly_data,
                "peak_months": season.peak_months,
                "source": season.source,
            }

        candidate = KeywordCandidate(
            keyword=idea.keyword,
            search_volume=idea.search_volume,
            competition_index=idea.competition_index,
            keyword_difficulty=idea.competition_index,  # Ads competition as initial proxy
            difficulty_source="ads_competition",
            intent=intent,
            seasonality=seasonality_data,
            source=idea.source,
            gap_score=gap_score,
            best_ranking_url=best_url,
            best_ranking_position=best_pos,
            status="new",
        )
        session.add(candidate)
        candidates.append(candidate)

    session.flush()
    log.info("candidates_upserted", count=len(candidates))
    return candidates


def enrich_with_dataforseo(
    session: Session,
    router: ResearchRouter,
    top_n: int = 100,
) -> int:
    """Enrich existing candidates with DataForSEO SERP + true difficulty.

    Only runs if DataForSEO provider is active. Enriches the top N candidates
    by search volume that haven't been enriched yet.
    """
    providers = router.get_active_providers()
    if not providers.get("dataforseo"):
        log.warning("dataforseo_not_available", msg="Skipping enrichment")
        return 0

    candidates = session.execute(
        select(KeywordCandidate)
        .where(KeywordCandidate.enriched_at.is_(None))
        .order_by(KeywordCandidate.search_volume.desc())
        .limit(top_n)
    ).scalars().all()

    if not candidates:
        return 0

    # Batch difficulty lookup
    keywords = [c.keyword for c in candidates]
    difficulties = router.get_keyword_difficulty(keywords)
    diff_map = {d.keyword: d for d in difficulties}

    enriched = 0
    now = datetime.now(timezone.utc)
    for c in candidates:
        diff = diff_map.get(c.keyword)
        if diff and diff.source == "seo_difficulty":
            c.keyword_difficulty = diff.difficulty
            c.difficulty_source = "seo_difficulty"

        # Get SERP data
        serp = router.get_serp(c.keyword)
        if serp and serp.organic_results:
            c.serp_features = {
                "organic_count": len(serp.organic_results),
                "has_featured_snippet": serp.featured_snippet is not None,
                "paa_count": len(serp.people_also_ask),
                "top3_domains": [r.get("domain", "") for r in serp.organic_results[:3]],
            }

        c.enriched_at = now
        enriched += 1

    session.flush()
    log.info("dataforseo_enriched", count=enriched)
    return enriched


def update_competitor_domains(
    session: Session,
    competitor_records: list[Any],
) -> int:
    """Upsert competitor domains from Ads auction data."""
    now = datetime.now(timezone.utc)
    count = 0
    for rec in competitor_records:
        existing = session.execute(
            select(CompetitorDomain).where(CompetitorDomain.domain == rec.domain)
        ).scalar_one_or_none()

        if existing:
            existing.keyword_overlap_count = rec.keyword_overlap_count
            existing.last_seen_at = now
        else:
            session.add(CompetitorDomain(
                domain=rec.domain,
                source=rec.source,
                keyword_overlap_count=rec.keyword_overlap_count,
                last_seen_at=now,
            ))
            count += 1

    session.flush()
    return count
