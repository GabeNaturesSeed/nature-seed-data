"""Content refresh pipeline — find decaying content and push it back through.

Identifies articles with declining traffic, worsening positions, or stale content.
Creates refresh_queue entries that flow into the brief → write → publish cycle.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    BriefQueue,
    ContentInventory,
    GscQueryPerformance,
    KeywordCandidate,
    RefreshQueue,
)

log = structlog.get_logger()


def _calculate_traffic_change(
    session: Session,
    page_url: str,
) -> float | None:
    """Calculate traffic change: last 90d vs previous 90d. Returns % change."""
    now = datetime.now(timezone.utc)
    d90 = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    d180 = (now - timedelta(days=180)).strftime("%Y-%m-%d")
    d_now = now.strftime("%Y-%m-%d")

    recent_clicks = session.execute(
        select(sqlfunc.sum(GscQueryPerformance.clicks))
        .where(
            GscQueryPerformance.page == page_url,
            GscQueryPerformance.date >= d90,
            GscQueryPerformance.date <= d_now,
        )
    ).scalar() or 0

    previous_clicks = session.execute(
        select(sqlfunc.sum(GscQueryPerformance.clicks))
        .where(
            GscQueryPerformance.page == page_url,
            GscQueryPerformance.date >= d180,
            GscQueryPerformance.date < d90,
        )
    ).scalar() or 0

    if previous_clicks == 0:
        return None
    return ((recent_clicks - previous_clicks) / previous_clicks) * 100


def find_refresh_candidates(
    session: Session,
    max_age_months: int = 12,
    traffic_decline_threshold: float = -20.0,
) -> list[dict[str, Any]]:
    """Find content_inventory rows that need refreshing.

    Criteria (any of):
    - Last modified > max_age_months ago
    - Traffic decline > threshold over last 90d vs previous 90d
    - Avg position worse than 10 for target keyword
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_months * 30)

    # Get all published posts/pages
    items = session.execute(
        select(ContentInventory)
        .where(
            ContentInventory.status == "publish",
            ContentInventory.post_type.in_(["post", "page"]),
        )
    ).scalars().all()

    candidates: list[dict[str, Any]] = []

    for item in items:
        reasons: list[str] = []
        priority = 0.0

        # Check age
        is_stale = False
        mod_at = item.modified_at
        if mod_at and mod_at.tzinfo is None:
            mod_at = mod_at.replace(tzinfo=timezone.utc)
        if mod_at and mod_at < cutoff:
            age_months = (datetime.now(timezone.utc) - mod_at).days // 30
            reasons.append(f"Content is {age_months} months old (threshold: {max_age_months})")
            priority += 0.3
            is_stale = True

        # Check traffic decline
        traffic_change = _calculate_traffic_change(session, item.url)
        if traffic_change is not None and traffic_change < traffic_decline_threshold:
            reasons.append(f"Traffic declined {traffic_change:.0f}% over last 90 days")
            priority += abs(traffic_change) / 100  # bigger drop = higher priority
        elif traffic_change is not None and traffic_change < 0:
            priority += 0.1  # minor decline

        # Check position for target keyword
        if item.target_keyword:
            best_pos = session.execute(
                select(sqlfunc.min(GscQueryPerformance.position))
                .where(
                    GscQueryPerformance.query == item.target_keyword.lower(),
                    GscQueryPerformance.page == item.url,
                )
            ).scalar()
            if best_pos and best_pos > 10:
                reasons.append(f"Position {best_pos:.1f} for '{item.target_keyword}' (outside top 10)")
                priority += 0.2

        if reasons:
            # Check if already in refresh queue
            existing = session.execute(
                select(RefreshQueue)
                .where(
                    RefreshQueue.content_inventory_id == item.id,
                    RefreshQueue.status.in_(["pending", "in_progress"]),
                )
            ).scalar_one_or_none()
            if existing:
                continue

            candidates.append({
                "content_id": item.id,
                "wp_post_id": item.wp_post_id,
                "title": item.title,
                "url": item.url,
                "reasons": reasons,
                "priority": round(min(priority, 1.0), 3),
                "traffic_change": traffic_change,
                "modified_at": item.modified_at,
            })

    candidates.sort(key=lambda x: -x["priority"])
    log.info("refresh_candidates_found", count=len(candidates))
    return candidates


def scan_and_queue(
    session: Session,
    limit: int = 20,
) -> int:
    """Find refresh candidates and add to refresh_queue."""
    candidates = find_refresh_candidates(session)

    added = 0
    for c in candidates[:limit]:
        session.add(RefreshQueue(
            content_inventory_id=c["content_id"],
            reason="; ".join(c["reasons"]),
            status="pending",
        ))
        added += 1

    session.commit()
    log.info("refresh_queued", added=added)
    return added


def get_refresh_queue(session: Session) -> list[dict[str, Any]]:
    """Get pending refresh queue with content details."""
    items = session.execute(
        select(RefreshQueue)
        .where(RefreshQueue.status == "pending")
        .order_by(RefreshQueue.created_at.desc())
    ).scalars().all()

    result: list[dict[str, Any]] = []
    for item in items:
        content = session.get(ContentInventory, item.content_inventory_id)
        result.append({
            "refresh_id": item.id,
            "content_id": item.content_inventory_id,
            "title": content.title if content else "?",
            "url": content.url if content else "?",
            "reason": item.reason,
            "status": item.status,
            "created_at": item.created_at,
        })

    return result
