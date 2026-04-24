"""WP media library indexing for image reuse.

Indexes images from WordPress media library into media_index table.
Uses title + alt + caption as searchable description text.
For semantic search, uses simple keyword overlap scoring (no vector DB dependency).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import MediaIndex
from naturesseed_pipeline.integrations.wordpress import WordPressClient, html_to_text

log = structlog.get_logger()


def index_media_library(session: Session, wp: WordPressClient | None = None) -> int:
    """Index all WP media into media_index table.

    Fetches media via WP REST API, builds description_text from
    title + alt + caption for text-based search.
    """
    if wp is None:
        wp = WordPressClient()
    close_wp = wp is None

    try:
        items = wp.list_media()
    except Exception as e:
        log.error("media_fetch_failed", error=str(e))
        return 0

    indexed = 0
    for item in items:
        wp_id = item.get("id")
        if not wp_id:
            continue

        existing = session.execute(
            select(MediaIndex).where(MediaIndex.wp_media_id == wp_id)
        ).scalar_one_or_none()

        url = item.get("source_url", "")
        title = html_to_text(item.get("title", {}).get("rendered", ""))
        alt = item.get("alt_text", "")
        caption = html_to_text(item.get("caption", {}).get("rendered", ""))
        filename = url.rsplit("/", 1)[-1] if url else ""

        details = item.get("media_details", {})
        width = details.get("width")
        height = details.get("height")
        mime = item.get("mime_type", "")

        # Build searchable description
        desc_parts = [p for p in [title, alt, caption, filename] if p]
        description_text = " ".join(desc_parts).lower()

        if existing:
            existing.url = url
            existing.filename = filename
            existing.title = title
            existing.alt_text = alt or None
            existing.caption = caption or None
            existing.width = width
            existing.height = height
            existing.mime_type = mime
            existing.description_text = description_text
        else:
            session.add(MediaIndex(
                wp_media_id=wp_id,
                url=url,
                filename=filename,
                title=title,
                alt_text=alt or None,
                caption=caption or None,
                width=width,
                height=height,
                mime_type=mime,
                description_text=description_text,
            ))
            indexed += 1

    session.commit()
    log.info("media_indexed", total=len(items), new=indexed)
    return indexed


def search_media(
    session: Session,
    query: str,
    limit: int = 5,
) -> list[tuple[MediaIndex, float]]:
    """Search media_index by keyword overlap scoring.

    Returns list of (MediaIndex, similarity_score) tuples, highest first.
    """
    query_words = set(query.lower().split())
    if not query_words:
        return []

    all_media = session.execute(select(MediaIndex)).scalars().all()

    scored: list[tuple[MediaIndex, float]] = []
    for m in all_media:
        if not m.description_text:
            continue
        desc_words = set(m.description_text.split())
        overlap = query_words & desc_words
        if not overlap:
            continue
        score = len(overlap) / max(len(query_words), 1)
        scored.append((m, round(score, 3)))

    scored.sort(key=lambda x: -x[1])
    return scored[:limit]
