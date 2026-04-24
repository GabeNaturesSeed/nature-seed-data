"""Keyword research pipeline orchestration.

Coordinates Google Ads, GSC, Trends, and DataForSEO providers through the
ResearchRouter. Manages seed expansion, inventory expansion, gap discovery,
competitor discovery, and GSC sync.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.config import settings
from naturesseed_pipeline.db.models import (
    CompetitorDomain,
    ContentInventory,
    GscQueryPerformance,
    KeywordCandidate,
)
from naturesseed_pipeline.integrations.keyword_research.base import ResearchRouter
from naturesseed_pipeline.integrations.keyword_research.dataforseo import DataForSEOProvider
from naturesseed_pipeline.integrations.keyword_research.google_ads import GoogleAdsProvider
from naturesseed_pipeline.integrations.keyword_research.gsc import GscProvider
from naturesseed_pipeline.integrations.keyword_research.trends import TrendsProvider

log = structlog.get_logger()


def _build_router() -> ResearchRouter:
    """Build the research router with all available providers."""
    providers: dict[str, Any] = {
        "google_ads": GoogleAdsProvider(),
        "trends": TrendsProvider(),
        "dataforseo": DataForSEOProvider(),
    }
    return ResearchRouter(
        providers=providers,
        priority=settings.research_provider_priority,
    )


def _build_gsc_lookup(gsc: GscProvider) -> dict[str, dict[str, Any]]:
    """Build a keyword→best-ranking lookup from GSC data."""
    if not gsc.is_available():
        return {}
    rows = gsc.get_ranked_keywords()
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        query = row["query"].lower()
        # Keep the best-ranking page per query
        if query not in lookup or row["position"] < lookup[query]["position"]:
            lookup[query] = row
    return lookup


def run_seed_research(session: Session, seeds: list[str]) -> dict[str, Any]:
    """Expand seed keywords → keyword_candidates + competitor_domains.

    Steps:
    1. Build GSC lookup for gap scoring
    2. Expand via Google Ads
    3. Pull competitor domains
    4. Upsert all results
    """
    from naturesseed_pipeline.agents.keyword_researcher import (
        research_seeds,
        update_competitor_domains,
    )

    router = _build_router()
    gsc = GscProvider()
    gsc_lookup = _build_gsc_lookup(gsc)

    # Expand and score
    candidates = research_seeds(session, router, seeds, gsc_data=gsc_lookup)

    # Competitor domains
    ads_provider = GoogleAdsProvider()
    competitor_count = 0
    if ads_provider.is_available():
        competitors = ads_provider.get_competitor_domains(seeds)
        competitor_count = update_competitor_domains(session, competitors)

    session.commit()
    return {
        "candidates": len(candidates),
        "competitors_new": competitor_count,
    }


def run_inventory_expansion(session: Session) -> dict[str, Any]:
    """Find adjacent keywords from existing content target_keywords.

    Takes all target_keyword values from content_inventory and expands them
    to find related keywords not yet in keyword_candidates.
    """
    from naturesseed_pipeline.agents.keyword_researcher import research_seeds

    # Get existing target keywords
    target_kws = session.execute(
        select(ContentInventory.target_keyword)
        .where(ContentInventory.target_keyword.isnot(None))
        .distinct()
    ).scalars().all()

    seeds = [kw for kw in target_kws if kw and len(kw) > 3][:50]  # cap at 50 seeds
    if not seeds:
        return {"candidates": 0, "message": "No target keywords in content_inventory"}

    router = _build_router()
    gsc = GscProvider()
    gsc_lookup = _build_gsc_lookup(gsc)

    candidates = research_seeds(session, router, seeds, gsc_data=gsc_lookup)
    session.commit()

    return {"candidates": len(candidates), "seeds_used": len(seeds)}


def run_gsc_gap_discovery(session: Session) -> list[dict[str, Any]]:
    """Surface page 2-5 keywords as quick-win opportunities."""
    gsc = GscProvider()
    if not gsc.is_available():
        log.warning("gsc_not_available")
        return []

    opportunities = gsc.find_page2_opportunities()

    # Also upsert into keyword_candidates if not already there
    for opp in opportunities:
        query = opp["query"]
        existing = session.execute(
            select(KeywordCandidate).where(KeywordCandidate.keyword == query)
        ).scalar_one_or_none()

        if not existing:
            session.add(KeywordCandidate(
                keyword=query,
                source="gsc_gap",
                gap_score=0.5,
                best_ranking_url=opp.get("page"),
                best_ranking_position=opp.get("position"),
                status="new",
            ))

    session.commit()
    return opportunities


def run_competitor_discovery(session: Session) -> dict[str, Any]:
    """Pull competitor domains from Google Ads auction data."""
    from naturesseed_pipeline.agents.keyword_researcher import update_competitor_domains

    ads = GoogleAdsProvider()
    if not ads.is_available():
        return {"competitors_new": 0, "message": "Google Ads not configured"}

    # Use top keywords from keyword_candidates as the seed
    top_kws = session.execute(
        select(KeywordCandidate.keyword)
        .order_by(KeywordCandidate.search_volume.desc())
        .limit(20)
    ).scalars().all()

    if not top_kws:
        return {"competitors_new": 0, "message": "No keywords to query"}

    competitors = ads.get_competitor_domains(list(top_kws))
    count = update_competitor_domains(session, competitors)
    session.commit()

    return {"competitors_new": count, "total_queried": len(top_kws)}


def run_gsc_sync(session: Session) -> dict[str, Any]:
    """Daily refresh of GSC performance data.

    Upserts into gsc_query_performance table AND updates
    content_inventory.performance_metrics JSON.
    """
    gsc = GscProvider()
    if not gsc.is_available():
        return {"rows": 0, "message": "GSC not configured"}

    rows = gsc.get_site_queries(
        dimensions=["query", "page", "device", "country"],
        row_limit=25000,
    )

    upserted = 0
    for row in rows:
        # Upsert into gsc_query_performance
        existing = session.execute(
            select(GscQueryPerformance).where(
                GscQueryPerformance.query == row.get("query", ""),
                GscQueryPerformance.page == row.get("page", ""),
                GscQueryPerformance.date == row.get("date", ""),
                GscQueryPerformance.device == row.get("device", "DESKTOP"),
                GscQueryPerformance.country == row.get("country", "USA"),
            )
        ).scalar_one_or_none()

        if existing:
            existing.impressions = row.get("impressions", 0)
            existing.clicks = row.get("clicks", 0)
            existing.ctr = row.get("ctr", 0.0)
            existing.position = row.get("position", 0.0)
        else:
            session.add(GscQueryPerformance(
                query=row.get("query", ""),
                page=row.get("page", ""),
                date=row.get("date", ""),
                device=row.get("device", "DESKTOP"),
                country=row.get("country", "USA"),
                impressions=row.get("impressions", 0),
                clicks=row.get("clicks", 0),
                ctr=row.get("ctr", 0.0),
                position=row.get("position", 0.0),
            ))
            upserted += 1

    session.commit()
    log.info("gsc_sync_complete", rows=len(rows), new=upserted)
    return {"rows": len(rows), "new": upserted}


def run_dataforseo_enrichment(session: Session, top_n: int = 100) -> dict[str, Any]:
    """Explicit enrichment of existing candidates with DataForSEO data."""
    from naturesseed_pipeline.agents.keyword_researcher import enrich_with_dataforseo

    router = _build_router()
    count = enrich_with_dataforseo(session, router, top_n=top_n)
    session.commit()
    return {"enriched": count}


def get_provider_status() -> dict[str, str]:
    """Return provider availability for display."""
    return {
        "Google Ads": "ACTIVE" if settings.google_ads_available else "INACTIVE (env vars missing)",
        "GSC": "ACTIVE" if settings.gsc_available else "INACTIVE (env vars missing)",
        "Trends": "ACTIVE",
        "DataForSEO": "ACTIVE" if settings.dataforseo_available else "GATED (env vars missing)",
    }
