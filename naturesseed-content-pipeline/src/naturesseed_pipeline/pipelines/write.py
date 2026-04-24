"""Write pipeline — orchestrates writer → fact_checker → editor → supervisor.

The pipeline runs sequentially. If any stage fails (needs_revision), the
pipeline stops and the draft is queued for human review.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.agents.editor import run_editorial_review
from naturesseed_pipeline.agents.fact_checker import check_facts
from naturesseed_pipeline.agents.writer import write_from_brief
from naturesseed_pipeline.db.models import BriefQueue, Draft

log = structlog.get_logger()


def write_from_brief_pipeline(
    session: Session,
    brief_id: int,
    fetch_sources: bool = True,
) -> dict[str, Any]:
    """Full write pipeline: writer → fact_checker → editor → supervisor_pending.

    Returns a summary of what happened at each stage.
    """
    result: dict[str, Any] = {"brief_id": brief_id, "stages": {}}

    # Stage 1: Writer
    log.info("pipeline_stage", stage="writer", brief_id=brief_id)
    draft = write_from_brief(session, brief_id)
    if not draft:
        result["error"] = "Writer failed to produce draft"
        return result
    result["draft_id"] = draft.id
    result["stages"]["writer"] = "complete"

    # Stage 2: Fact checker
    log.info("pipeline_stage", stage="fact_checker", draft_id=draft.id)
    fact_notes = check_facts(session, draft.id, fetch_sources=fetch_sources)
    result["stages"]["fact_checker"] = fact_notes.get("unsupported", 0)

    if draft.status == "needs_revision":
        result["stages"]["status"] = "needs_revision_after_fact_check"
        result["final_status"] = "needs_revision"
        log.info("pipeline_stopped", reason="fact_check_failed", draft_id=draft.id)
        return result

    # Stage 3: Editor
    log.info("pipeline_stage", stage="editor", draft_id=draft.id)
    edit_notes = run_editorial_review(session, draft.id)
    result["stages"]["editor"] = edit_notes

    if draft.status == "needs_revision":
        result["stages"]["status"] = "needs_revision_after_edit"
        result["final_status"] = "needs_revision"
        log.info("pipeline_stopped", reason="editorial_issues", draft_id=draft.id)
        return result

    # Stage 4: Ready for supervisor review
    draft.status = "supervisor_pending"
    session.commit()
    result["stages"]["status"] = "supervisor_pending"
    result["final_status"] = "supervisor_pending"

    log.info("pipeline_complete", draft_id=draft.id, status="supervisor_pending")
    return result


def write_next_approved_brief(
    session: Session,
    fetch_sources: bool = True,
) -> dict[str, Any] | None:
    """Pick the next approved brief and run the full write pipeline."""
    brief = session.execute(
        select(BriefQueue)
        .where(BriefQueue.status == "approved")
        .order_by(BriefQueue.priority_score.desc())
        .limit(1)
    ).scalar_one_or_none()

    if not brief:
        log.info("no_approved_briefs")
        return None

    return write_from_brief_pipeline(session, brief.id, fetch_sources=fetch_sources)
