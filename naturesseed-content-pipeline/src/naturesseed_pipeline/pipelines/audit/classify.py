"""Classify stage — assigns each article to a topic + subtopic.

Four-pass workflow:
  Pass 1: seed top-level Topics from WC categories + deterministic article → topic
  Pass 2: propose subtopics via LLM (one shot per topic; proposals start approved=0)
  Pass 3: user approval gate (CLI flips approved=1)
  Pass 4: deterministic subtopic matching using approved subtopic keyword phrases
"""

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Topic

log = structlog.get_logger()


def seed_topics_from_wc_categories(
    session: Session, wc_categories: list[dict[str, Any]],
) -> int:
    """Insert missing top-level topics for each WC category + an Unclassified bucket.
    Returns the number of rows added this call."""
    existing = {t.slug for t in session.execute(select(Topic)).scalars().all()
                if t.parent_topic_id is None}
    added = 0
    for cat in wc_categories:
        slug = cat.get("slug") or ""
        if not slug or slug in existing:
            continue
        session.add(Topic(
            name=cat.get("name") or slug, slug=slug,
            wc_category_slug=slug, source="wc_category", approved=1,
        ))
        existing.add(slug); added += 1
    if "unclassified" not in existing:
        session.add(Topic(name="Unclassified", slug="unclassified",
                          source="user_created", approved=1))
        added += 1
    return added
