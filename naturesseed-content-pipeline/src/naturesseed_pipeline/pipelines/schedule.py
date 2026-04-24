"""Editorial calendar — assign publish slots based on configurable rules.

Config from config/schedule.yaml: publish_days, publish_time, max_per_week, min_gap_hours.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import PublishQueue

log = structlog.get_logger()

_DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def load_schedule_config(path: str = "config/schedule.yaml") -> dict[str, Any]:
    """Load editorial calendar config."""
    p = Path(path)
    if not p.exists():
        return {
            "publish_days": ["Tuesday", "Thursday"],
            "publish_time": "09:00",
            "timezone": "America/Denver",
            "max_per_week": 3,
            "min_gap_hours": 24,
        }
    with open(p) as f:
        return yaml.safe_load(f) or {}


def _get_publish_weekdays(config: dict[str, Any]) -> list[int]:
    """Convert day names to weekday numbers (0=Monday)."""
    days = config.get("publish_days", ["Tuesday", "Thursday"])
    return sorted(_DAY_MAP.get(d.lower(), 1) for d in days)


def _get_publish_hour_minute(config: dict[str, Any]) -> tuple[int, int]:
    """Parse publish_time string to (hour, minute)."""
    time_str = config.get("publish_time", "09:00")
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


def get_scheduled_slots(session: Session) -> list[datetime]:
    """Get all currently scheduled publish slots."""
    items = session.execute(
        select(PublishQueue.scheduled_for)
        .where(
            PublishQueue.scheduled_for.isnot(None),
            PublishQueue.publish_status.in_(["scheduled_pending", "queued"]),
        )
    ).scalars().all()
    # Normalize to UTC-aware
    result = []
    for s in items:
        if s is None:
            continue
        if s.tzinfo is None:
            s = s.replace(tzinfo=timezone.utc)
        result.append(s)
    return result


def assign_next_slot(
    session: Session,
    config: dict[str, Any] | None = None,
    after: datetime | None = None,
) -> datetime:
    """Find the next available publish slot based on calendar rules."""
    if config is None:
        config = load_schedule_config()

    weekdays = _get_publish_weekdays(config)
    hour, minute = _get_publish_hour_minute(config)
    min_gap = timedelta(hours=config.get("min_gap_hours", 24))
    max_per_week = config.get("max_per_week", 3)

    existing = get_scheduled_slots(session)
    existing_set = {s.date() for s in existing if s}

    # Start from tomorrow or after
    if after is None:
        after = datetime.now(timezone.utc)
    candidate = after + timedelta(days=1)
    candidate = candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # Search up to 60 days ahead
    for _ in range(60):
        if candidate.weekday() in weekdays:
            # Check min gap
            too_close = any(
                abs((candidate - s).total_seconds()) < min_gap.total_seconds()
                for s in existing
            )
            if not too_close:
                # Check weekly cap
                week_start = candidate - timedelta(days=candidate.weekday())
                week_end = week_start + timedelta(days=7)
                week_count = sum(
                    1 for s in existing
                    if week_start <= s < week_end
                )
                if week_count < max_per_week:
                    return candidate

        candidate += timedelta(days=1)

    # Fallback: next valid weekday regardless of caps
    candidate = after + timedelta(days=1)
    for _ in range(30):
        if candidate.weekday() in weekdays:
            return candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
        candidate += timedelta(days=1)

    return candidate


def schedule_draft(
    session: Session,
    draft_id: int,
    slot: datetime | None = None,
) -> PublishQueue | None:
    """Schedule a draft for publishing. Auto-assigns slot if None."""
    from naturesseed_pipeline.db.models import Draft

    draft = session.get(Draft, draft_id)
    if not draft:
        return None

    if slot is None:
        slot = assign_next_slot(session)

    # Check if already in publish queue
    existing = session.execute(
        select(PublishQueue).where(PublishQueue.draft_id == draft_id)
    ).scalar_one_or_none()

    if existing:
        existing.scheduled_for = slot
        existing.publish_status = "scheduled_pending"
    else:
        existing = PublishQueue(
            draft_id=draft_id,
            scheduled_for=slot,
            publish_status="scheduled_pending",
        )
        session.add(existing)

    session.commit()
    log.info("draft_scheduled", draft_id=draft_id, slot=slot.isoformat())
    return existing


def get_calendar(session: Session, days: int = 30) -> list[dict[str, Any]]:
    """Get upcoming publish calendar for the next N days."""
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days)

    items = session.execute(
        select(PublishQueue)
        .where(
            PublishQueue.scheduled_for.isnot(None),
            PublishQueue.scheduled_for <= cutoff,
        )
        .order_by(PublishQueue.scheduled_for)
    ).scalars().all()

    calendar: list[dict[str, Any]] = []
    for item in items:
        from naturesseed_pipeline.db.models import Draft
        draft = session.get(Draft, item.draft_id)
        calendar.append({
            "publish_queue_id": item.id,
            "draft_id": item.draft_id,
            "title": draft.title if draft else "?",
            "scheduled_for": item.scheduled_for,
            "status": item.publish_status,
        })

    return calendar
