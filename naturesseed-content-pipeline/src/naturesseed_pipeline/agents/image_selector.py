"""Image selector agent — matches image slots to library or generates new.

For each slot in a draft, generates a descriptive query, searches the
media library, and falls back to AI generation if no good match.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from sqlalchemy.orm import Session

from naturesseed_pipeline.config import settings
from naturesseed_pipeline.db.models import Draft
from naturesseed_pipeline.integrations.image_generation import (
    generate_alt_text,
    generate_image,
    optimize_image,
)
from naturesseed_pipeline.integrations.image_library import search_media

log = structlog.get_logger()


def _infer_image_slots(content: str) -> list[dict[str, str]]:
    """Infer image slots from draft content based on H2 headings.

    Returns a list of slots: hero + one per H2 section.
    """
    slots: list[dict[str, str]] = [
        {"name": "hero", "context": content[:200]},
    ]

    h2_pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    for i, m in enumerate(h2_pattern.finditer(content)):
        heading = m.group(1).strip()
        # Get text after this heading until next heading or end
        start = m.end()
        next_h = h2_pattern.search(content, start)
        end = next_h.start() if next_h else len(content)
        section_text = content[start:end][:300]

        slots.append({
            "name": f"section_{i + 1}",
            "context": f"{heading}. {section_text}",
            "heading": heading,
        })

    return slots


def _generate_search_query(slot: dict[str, str], keyword: str | None) -> str:
    """Generate a descriptive search query for an image slot."""
    context = slot.get("context", "")
    heading = slot.get("heading", "")
    name = slot.get("name", "")

    if name == "hero":
        return f"{keyword or 'gardening'} outdoor garden seeds planting"

    # Extract key nouns from context
    words = re.findall(r"\b[a-z]{4,}\b", context.lower())
    # Pick top unique words
    seed_words = list(dict.fromkeys(words))[:6]
    return " ".join([heading.lower()] + seed_words[:4])


def select_images_for_draft(
    session: Session,
    draft_id: int,
) -> list[dict[str, Any]]:
    """Select images for each slot in a draft.

    Searches media library first, falls back to generation if below threshold.
    Generates alt text for every image.
    """
    draft = session.get(Draft, draft_id)
    if not draft or not draft.content_markdown:
        return []

    brief = draft.brief
    keyword = None
    if brief and brief.brief_json:
        keyword = brief.brief_json.get("target_keyword")

    slug = re.sub(r"[^a-z0-9]+", "-", draft.title.lower())[:50]
    slots = _infer_image_slots(draft.content_markdown)
    threshold = settings.image_similarity_threshold

    assignments: list[dict[str, Any]] = []

    for slot in slots:
        query = _generate_search_query(slot, keyword)
        log.info("searching_image", slot=slot["name"], query=query)

        # Search library
        results = search_media(session, query, limit=3)

        assignment: dict[str, Any] = {
            "slot": slot["name"],
            "query": query,
            "source": None,
            "url": None,
            "local_path": None,
            "alt_text": None,
            "similarity": None,
            "candidates": [],
        }

        # Record top candidates
        for media, score in results:
            assignment["candidates"].append({
                "media_id": media.id,
                "url": media.url,
                "title": media.title,
                "score": score,
            })

        # Check if best match is above threshold
        if results and results[0][1] >= threshold:
            best_media, best_score = results[0]
            assignment["source"] = "library"
            assignment["url"] = best_media.url
            assignment["similarity"] = best_score
            assignment["alt_text"] = best_media.alt_text or generate_alt_text(
                "", slot.get("context", "")
            )
            log.info("library_match", slot=slot["name"], score=best_score)
        else:
            # Fallback to generation
            log.info("generating_image", slot=slot["name"])
            gen_result = generate_image(query, slug, slot["name"])
            if gen_result:
                # Optimize
                optimized = optimize_image(gen_result["local_path"])
                assignment["source"] = "generated"
                assignment["local_path"] = optimized
                assignment["alt_text"] = generate_alt_text(
                    optimized, slot.get("context", "")
                )
            else:
                assignment["source"] = "none"
                assignment["alt_text"] = generate_alt_text(
                    "", slot.get("context", "")
                )

        assignments.append(assignment)

    return assignments
