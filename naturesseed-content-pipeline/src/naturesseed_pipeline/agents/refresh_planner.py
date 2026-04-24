"""Refresh planner agent — produces a refresh brief for decaying content.

Input: refresh_queue row
Output: brief in brief_queue with is_refresh=True + original_wp_post_id
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    BriefQueue,
    ContentInventory,
    KeywordCandidate,
    RefreshQueue,
)

log = structlog.get_logger()


def plan_refresh(
    session: Session,
    refresh_id: int,
) -> BriefQueue | None:
    """Generate a refresh brief for a refresh_queue item.

    Pulls current article content, compares with current keyword data,
    and produces a brief that specifies what to keep, update, add, remove.
    """
    rq = session.get(RefreshQueue, refresh_id)
    if not rq:
        log.error("refresh_item_not_found", id=refresh_id)
        return None

    content = session.get(ContentInventory, rq.content_inventory_id)
    if not content:
        log.error("content_not_found", id=rq.content_inventory_id)
        return None

    log.info("planning_refresh", title=content.title, url=content.url)

    # Get current keyword data if available
    keyword_data: dict[str, Any] = {}
    if content.target_keyword:
        kw = session.execute(
            select(KeywordCandidate)
            .where(KeywordCandidate.keyword == content.target_keyword)
        ).scalar_one_or_none()
        if kw:
            keyword_data = {
                "search_volume": kw.search_volume,
                "difficulty": kw.keyword_difficulty,
                "gap_score": kw.gap_score,
                "current_position": kw.best_ranking_position,
            }

    # Analyze what needs refreshing
    word_count = content.word_count or 0
    sections_to_update: list[str] = []
    sections_to_add: list[str] = []
    sections_to_keep: list[str] = []

    # Heuristic analysis of existing content
    if word_count < 1000:
        sections_to_add.append("Expand thin content — add at least 500 more words")
    if content.content_text:
        text = content.content_text.lower()
        if "2024" in text or "2023" in text:
            sections_to_update.append("Update year references to current year")
        if "link" not in text and "http" not in text:
            sections_to_add.append("Add internal links to related content")

    sections_to_add.append("Add or update FAQ section with current questions")
    sections_to_update.append("Verify all product recommendations are still available")
    sections_to_keep.append("Preserve existing URL structure and heading hierarchy")

    # Build refresh brief
    brief_data: dict[str, Any] = {
        "target_keyword": content.target_keyword or content.title,
        "secondary_keywords": [],
        "search_intent": "informational",
        "is_refresh": True,
        "original_url": content.url,
        "original_wp_post_id": content.wp_post_id,
        "original_word_count": word_count,
        "refresh_reason": rq.reason,
        "keyword_data": keyword_data,
        "sections_to_keep": sections_to_keep,
        "sections_to_update": sections_to_update,
        "sections_to_add": sections_to_add,
        "suggested_title_options": [
            content.title,
            f"{content.title} (Updated {datetime.now().year})",
            f"{content.target_keyword or content.title}: Complete Guide {datetime.now().year}",
        ],
        "recommended_word_count": max(word_count + 300, 1200),
        "outline": [],  # writer will use existing + modifications
        "competitor_gap_notes": {},
        "internal_link_candidates": [],
        "product_cta_candidates": [],
        "citation_requirements": [
            "Any updated statistics or data points",
            "Any new product availability claims",
        ],
        "suggested_angle": (
            f"Preserve the existing article's voice and structure. "
            f"Focus on updating: {'; '.join(sections_to_update[:3])}. "
            f"Add: {'; '.join(sections_to_add[:3])}."
        ),
        "metadata": {
            "refresh_id": refresh_id,
            "original_content_id": content.id,
            **keyword_data,
        },
    }

    # Create brief
    brief = BriefQueue(
        keyword_candidate_id=None,
        topic=f"[REFRESH] {content.title}",
        target_keyword=content.target_keyword,
        brief_json=brief_data,
        is_refresh=True,
        original_wp_post_id=content.wp_post_id,
        status="pending",
    )
    session.add(brief)

    # Update refresh queue status
    rq.status = "planned"
    session.commit()

    log.info("refresh_brief_created", brief_id=brief.id, title=content.title)
    return brief
