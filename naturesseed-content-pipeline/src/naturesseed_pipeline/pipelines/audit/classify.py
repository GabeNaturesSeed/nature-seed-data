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
        from naturesseed_pipeline.pipelines.audit.llm import CliClaudeClient
        self.client = CliClaudeClient()
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


def list_pending_subtopics(session: Session) -> list[Topic]:
    """Return all LLM-proposed subtopics still awaiting approval, oldest first."""
    return list(session.execute(
        select(Topic).where(
            Topic.parent_topic_id.isnot(None),
            Topic.source == "llm_proposed",
            Topic.approved == 0,
        ).order_by(Topic.id)
    ).scalars().all())


def approve_subtopic(session: Session, slug: str) -> bool:
    """Flip a single subtopic to approved. Returns True if a row was flipped."""
    t = session.execute(select(Topic).where(Topic.slug == slug)).scalar_one_or_none()
    if t is None or t.approved == 1:
        return False
    t.approved = 1
    return True


def approve_all_subtopics(session: Session) -> int:
    """Flip every pending proposal to approved. Returns the count flipped."""
    pending = list_pending_subtopics(session)
    for t in pending:
        t.approved = 1
    return len(pending)


def _score_article_against_subtopic(text: str, keywords: list[str]) -> int:
    """Hit count of keyword phrases in article text (case-insensitive)."""
    if not text or not keywords:
        return 0
    text_lower = text.lower()
    return sum(text_lower.count(kw.lower()) for kw in keywords if kw)


def run_classify_pass4(session: Session) -> int:
    """Assign subtopic to each article using best-match keyword hit count.
    Returns the count of new subtopic assignments."""
    # Group approved subtopics by parent
    top_levels = {t.id: t for t in session.execute(
        select(Topic).where(Topic.parent_topic_id.is_(None))
    ).scalars().all()}
    subtopics_by_parent: dict[int, list[Topic]] = {}
    for t in session.execute(
        select(Topic).where(Topic.parent_topic_id.isnot(None), Topic.approved == 1)
    ).scalars().all():
        subtopics_by_parent.setdefault(t.parent_topic_id, []).append(t)

    # Existing content-topic pairs
    existing = {(a.content_inventory_id, a.topic_id) for a in
                session.execute(select(ContentTopic)).scalars().all()}

    # Build: content_id -> list of top-level topic_ids currently assigned
    content_topic_rows = session.execute(select(ContentTopic)).scalars().all()
    by_content: dict[int, list[int]] = {}
    for ct in content_topic_rows:
        by_content.setdefault(ct.content_inventory_id, []).append(ct.topic_id)

    assigned = 0
    content_rows = session.execute(select(ContentInventory)).scalars().all()
    for row in content_rows:
        assigned_topic_ids = by_content.get(row.id, [])
        tl_id = next((tid for tid in assigned_topic_ids if tid in top_levels), None)
        if tl_id is None:
            continue
        subs = subtopics_by_parent.get(tl_id, [])
        if not subs:
            continue

        scored = sorted(
            ((sub, _score_article_against_subtopic(row.content_text or "", sub.keywords or []))
             for sub in subs),
            key=lambda x: x[1], reverse=True,
        )
        best_sub, best_score = scored[0]
        if best_score == 0:
            continue
        if (row.id, best_sub.id) in existing:
            continue

        total_hits = sum(score for _, score in scored) or 1
        session.add(ContentTopic(
            content_inventory_id=row.id, topic_id=best_sub.id,
            confidence=best_score / total_hits, assigned_by="auto",
        ))
        existing.add((row.id, best_sub.id))
        assigned += 1

    return assigned


from pathlib import Path


def export_pending_subtopics_to_markdown(session: Session, out_path: Path) -> int:
    """Dump all pending subtopic proposals to a markdown file for review.

    Format:
        # Subtopic Proposals — Pending Approval
        ... guidance ...
        ---
        ## <Subtopic Name> [parent: <parent-slug>]
        - slug: <slug>
        - keywords:
          - <kw1>
          - <kw2>
    """
    pending = list_pending_subtopics(session)
    parent_by_id = {
        t.id: t for t in session.execute(
            select(Topic).where(Topic.parent_topic_id.is_(None))
        ).scalars().all()
    }
    lines = [
        "# Subtopic Proposals — Pending Approval",
        "",
        "Review each section below:",
        "- **Approve**: leave it as-is.",
        "- **Reject**: delete the section (including its `##` heading).",
        "- **Refine**: edit the name, slug, or keywords. Re-imports re-read from disk.",
        "",
        "When done, run: `nspipe audit classify --import-approvals <this-file>`",
        "",
    ]
    for t in pending:
        parent = parent_by_id.get(t.parent_topic_id)
        parent_slug = parent.slug if parent else "?"
        lines.append("---")
        lines.append(f"## {t.name} [parent: {parent_slug}]")
        lines.append(f"- slug: {t.slug}")
        lines.append("- keywords:")
        for kw in (t.keywords or []):
            lines.append(f"  - {kw}")
        lines.append("")
    out_path.write_text("\n".join(lines))
    return len(pending)


def import_subtopic_approvals_from_markdown(session: Session, in_path: Path) -> dict[str, int]:
    """Parse the edited markdown file. Approve every surviving subtopic (update
    name/keywords if edited). Delete any pending subtopic whose slug is absent
    from the file — that represents a rejection.

    Returns counts: {approved, rejected, refined, unknown}.
    """
    import re

    text = in_path.read_text()
    # Split on `---` section separators, keep only non-empty blocks after the header
    blocks = [b.strip() for b in text.split("---") if b.strip()]
    if blocks and blocks[0].startswith("# Subtopic Proposals"):
        blocks = blocks[1:]  # drop the header block

    parsed: dict[str, dict] = {}  # slug -> {name, keywords, parent_slug}
    for block in blocks:
        # Header: "## <Name> [parent: <parent-slug>]"
        h = re.search(r"^##\s+(.+?)\s*\[parent:\s*([^\]]+)\]\s*$", block, re.MULTILINE)
        if not h:
            continue
        name = h.group(1).strip()
        parent_slug = h.group(2).strip()

        slug_m = re.search(r"^\s*-\s*slug:\s*(.+?)\s*$", block, re.MULTILINE)
        if not slug_m:
            continue
        slug = slug_m.group(1).strip()

        # keywords: list items after "- keywords:"
        kws: list[str] = []
        kw_section = re.search(r"-\s*keywords:\s*\n((?:\s+-\s+.+\n?)*)", block)
        if kw_section:
            for line in kw_section.group(1).splitlines():
                kw = line.strip().lstrip("-").strip()
                if kw:
                    kws.append(kw)

        parsed[slug] = {"name": name, "keywords": kws, "parent_slug": parent_slug}

    pending = list_pending_subtopics(session)
    pending_slugs = {t.slug for t in pending}

    counts = {"approved": 0, "rejected": 0, "refined": 0, "unknown": 0}

    for t in pending:
        if t.slug not in parsed:
            session.delete(t)
            counts["rejected"] += 1
            continue
        data = parsed[t.slug]
        if data["name"] != t.name or data["keywords"] != (t.keywords or []):
            t.name = data["name"]
            t.keywords = data["keywords"]
            counts["refined"] += 1
        t.approved = 1
        counts["approved"] += 1

    # Slugs in file but not in pending — probably user-added or already approved
    for slug in parsed.keys() - pending_slugs:
        counts["unknown"] += 1

    return counts
