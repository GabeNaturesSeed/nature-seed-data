"""Pipeline orchestrator — daily, weekly, and quarterly run commands.

Composes the individual pipelines into scheduled batches:
- daily:   audit sync + GSC sync + media listener sweep
- weekly:  keyword expansion + scoring + generate top 5 briefs
- refresh: quarterly refresh scan
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.orm import Session

log = structlog.get_logger()


def run_daily(session: Session) -> dict[str, Any]:
    """Daily pipeline: audit sync + analytics sync + media listener sweep."""
    results: dict[str, Any] = {}

    # 1. Audit sync (content inventory)
    log.info("daily_step", step="audit_sync")
    try:
        from naturesseed_pipeline.pipelines.audit_legacy import run_full_audit
        results["audit"] = run_full_audit(session)
    except Exception as e:
        log.error("daily_audit_failed", error=str(e))
        results["audit"] = {"error": str(e)}

    # 2. GSC sync (search performance data)
    log.info("daily_step", step="gsc_sync")
    try:
        from naturesseed_pipeline.pipelines.research_keywords import run_gsc_sync
        results["gsc_sync"] = run_gsc_sync(session)
    except Exception as e:
        log.error("daily_gsc_failed", error=str(e))
        results["gsc_sync"] = {"error": str(e)}

    # 3. Media listener sweep
    log.info("daily_step", step="media_sweep")
    try:
        from naturesseed_pipeline.pipelines.research_media import run_listener_sweep
        results["media"] = run_listener_sweep(session)
    except Exception as e:
        log.error("daily_media_failed", error=str(e))
        results["media"] = {"error": str(e)}

    log.info("daily_complete", results={k: "ok" if "error" not in v else "error" for k, v in results.items()})
    return results


def run_weekly(session: Session, brief_count: int = 5) -> dict[str, Any]:
    """Weekly pipeline: keyword expansion + scoring + generate top N briefs."""
    results: dict[str, Any] = {}

    # 1. Inventory expansion (find new keywords from existing content)
    log.info("weekly_step", step="keyword_expansion")
    try:
        from naturesseed_pipeline.pipelines.research_keywords import run_inventory_expansion
        results["keyword_expansion"] = run_inventory_expansion(session)
    except Exception as e:
        log.error("weekly_expansion_failed", error=str(e))
        results["keyword_expansion"] = {"error": str(e)}

    # 2. Promote media signals to keywords
    log.info("weekly_step", step="signal_promotion")
    try:
        from naturesseed_pipeline.pipelines.research_media import promote_signals_to_keywords
        results["signal_promotion"] = promote_signals_to_keywords(session)
    except Exception as e:
        log.error("weekly_promotion_failed", error=str(e))
        results["signal_promotion"] = {"error": str(e)}

    # 3. Score backlog
    log.info("weekly_step", step="scoring")
    try:
        from naturesseed_pipeline.pipelines.scoring import rank_backlog
        ranked = rank_backlog(session, limit=brief_count * 2)
        results["scoring"] = {"ranked": len(ranked)}
    except Exception as e:
        log.error("weekly_scoring_failed", error=str(e))
        results["scoring"] = {"error": str(e)}

    # 4. Generate top briefs
    log.info("weekly_step", step="brief_generation")
    try:
        from naturesseed_pipeline.agents.brief_generator import generate_top_briefs
        briefs = generate_top_briefs(session, count=brief_count, scrape=False)
        results["briefs"] = {"generated": len(briefs)}
    except Exception as e:
        log.error("weekly_briefs_failed", error=str(e))
        results["briefs"] = {"error": str(e)}

    log.info("weekly_complete", results={k: "ok" if "error" not in v else "error" for k, v in results.items()})
    return results


def run_refresh(session: Session) -> dict[str, Any]:
    """Quarterly refresh: scan for decaying content."""
    results: dict[str, Any] = {}

    log.info("refresh_step", step="scan")
    try:
        from naturesseed_pipeline.pipelines.refresh import scan_and_queue
        added = scan_and_queue(session)
        results["scan"] = {"queued": added}
    except Exception as e:
        log.error("refresh_scan_failed", error=str(e))
        results["scan"] = {"error": str(e)}

    log.info("refresh_complete", results=results)
    return results
