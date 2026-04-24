"""Image pipeline — attach images to drafts.

Runs image selector, handles library search + generation fallback,
optimizes images, writes image_assignments JSON into draft record.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.orm import Session

from naturesseed_pipeline.agents.image_selector import select_images_for_draft
from naturesseed_pipeline.db.models import Draft
from naturesseed_pipeline.integrations.image_library import index_media_library

log = structlog.get_logger()


def attach_images_to_draft(
    session: Session,
    draft_id: int,
) -> dict[str, Any]:
    """Run image selection pipeline for a draft.

    Searches library, generates fallbacks, optimizes, and writes
    image_assignments JSON to the draft record.
    """
    draft = session.get(Draft, draft_id)
    if not draft:
        return {"error": "Draft not found"}

    assignments = select_images_for_draft(session, draft_id)

    # Store in draft
    draft.image_assignments = [
        {k: v for k, v in a.items() if k != "candidates"}
        for a in assignments
    ]
    session.commit()

    # Summary
    library_count = sum(1 for a in assignments if a["source"] == "library")
    generated_count = sum(1 for a in assignments if a["source"] == "generated")
    none_count = sum(1 for a in assignments if a["source"] == "none")
    has_alt = sum(1 for a in assignments if a.get("alt_text"))

    summary = {
        "draft_id": draft_id,
        "total_slots": len(assignments),
        "from_library": library_count,
        "generated": generated_count,
        "unresolved": none_count,
        "with_alt_text": has_alt,
        "assignments": assignments,
    }

    log.info("images_attached", **{k: v for k, v in summary.items() if k != "assignments"})
    return summary


def preview_image_assignments(
    session: Session,
    draft_id: int,
) -> list[dict[str, Any]] | None:
    """Get image assignments for display."""
    draft = session.get(Draft, draft_id)
    if not draft:
        return None
    return draft.image_assignments
