"""Classify stage — assigns each article to a topic + subtopic.

Four-pass workflow:
  Pass 1: seed top-level Topics from WC categories + deterministic article → topic
  Pass 2: propose subtopics via LLM (one shot per topic; proposals start approved=0)
  Pass 3: user approval gate (CLI flips approved=1)
  Pass 4: deterministic subtopic matching using approved subtopic keyword phrases
"""

import json
from typing import Any, Protocol

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


class SubtopicProposer(Protocol):
    """Contract for LLM-backed subtopic proposal. Real impl uses Anthropic."""
    def propose(self, topic_name: str, samples: list[dict[str, str]]) -> list[dict]: ...


class AnthropicSubtopicProposer:
    """Real LLM impl — reads Anthropic client from settings."""

    def __init__(self, model: str | None = None) -> None:
        from naturesseed_pipeline.config import settings
        import anthropic
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = model or settings.audit_llm_model

    def propose(self, topic_name: str, samples: list[dict[str, str]]) -> list[dict]:
        sample_text = "\n\n".join(
            f"- Title: {s['title']}\n  Excerpt: {s.get('excerpt', '')[:400]}"
            for s in samples[:40]
        )
        prompt = f"""You are organizing a content library for Nature's Seed.
Top-level topic: "{topic_name}".

Here are {len(samples)} article titles + excerpts in this topic:

{sample_text}

Propose 3-7 subtopics that best organize this content. Each subtopic MUST have:
- A short name (2-4 words, title case)
- A URL-safe slug (lowercase, hyphens)
- 5-15 keyword phrases that, when matched against article text, would reliably identify articles as belonging to that subtopic

Return ONLY a JSON array of objects with keys: name, slug, keywords. No prose.
"""
        resp = self.client.messages.create(
            model=self.model, max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        # Trim markdown fences if present
        if text.startswith("```"):
            text = text.strip("`")
            text = text.split("\n", 1)[1] if "\n" in text else text
            if text.endswith("```"):
                text = text[:-3]
        return json.loads(text)


def run_classify_pass2(session: Session, proposer: SubtopicProposer) -> int:
    """Ask LLM to propose subtopics for each top-level topic with no existing approved subtopics."""
    top_level = [t for t in session.execute(select(Topic)).scalars().all()
                 if t.parent_topic_id is None and t.slug != "unclassified"]
    proposed_count = 0

    for topic in top_level:
        existing_subs = session.execute(
            select(Topic).where(Topic.parent_topic_id == topic.id, Topic.approved == 1)
        ).scalars().all()
        if existing_subs:
            continue

        sample_rows = session.execute(
            select(ContentInventory)
            .join(ContentTopic, ContentTopic.content_inventory_id == ContentInventory.id)
            .where(ContentTopic.topic_id == topic.id)
            .limit(40)
        ).scalars().all()
        if not sample_rows:
            continue

        samples = [{"title": r.title, "excerpt": r.excerpt or r.content_text[:500] or ""}
                   for r in sample_rows]

        proposals = proposer.propose(topic.name, samples)
        for p in proposals:
            slug = p.get("slug") or ""
            if not slug:
                continue
            existing = session.execute(
                select(Topic).where(Topic.slug == slug)
            ).scalar_one_or_none()
            if existing:
                continue
            t = Topic(
                name=p.get("name") or slug, slug=slug,
                parent_topic_id=topic.id, source="llm_proposed", approved=0,
                keywords=p.get("keywords") or [],
            )
            session.add(t); proposed_count += 1

    return proposed_count
