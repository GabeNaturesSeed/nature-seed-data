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

from naturesseed_pipeline.db.models import ContentInventory, ContentTopic, Topic

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


def _find_top_level_topic_slug(
    row: ContentInventory,
    wp_cat_id_to_slug: dict[int, str],
    topic_slugs: set[str],
) -> str:
    """Return slug of top-level topic this article should map to."""
    for cat_id in row.categories or []:
        if not isinstance(cat_id, int):
            continue
        slug = wp_cat_id_to_slug.get(cat_id)
        if slug and slug in topic_slugs:
            return slug
    return "unclassified"


def run_classify_pass1(
    session: Session, wp_cat_id_to_slug: dict[int, str],
) -> int:
    """Assign every article to a top-level topic based on its WP/WC categories.
    Returns the count of new assignments."""
    topics = {t.slug: t for t in session.execute(select(Topic)).scalars().all()
              if t.parent_topic_id is None}
    topic_slugs = set(topics.keys())

    existing_pairs = {
        (a.content_inventory_id, a.topic_id)
        for a in session.execute(select(ContentTopic)).scalars().all()
    }

    rows = session.execute(select(ContentInventory)).scalars().all()
    assigned = 0
    for row in rows:
        slug = _find_top_level_topic_slug(row, wp_cat_id_to_slug, topic_slugs)
        topic = topics.get(slug) or topics["unclassified"]
        key = (row.id, topic.id)
        if key in existing_pairs:
            continue
        session.add(ContentTopic(
            content_inventory_id=row.id, topic_id=topic.id,
            confidence=1.0, assigned_by="auto",
        ))
        existing_pairs.add(key); assigned += 1
    return assigned
