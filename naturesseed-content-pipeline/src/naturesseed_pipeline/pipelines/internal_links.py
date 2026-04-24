"""Internal linking pass — insert contextual links into draft content.

Scans approved draft content for phrases matching existing content_inventory
titles. Inserts up to max_links (default 5) contextual internal links.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import ContentInventory

log = structlog.get_logger()


def find_link_opportunities(
    session: Session,
    content: str,
    exclude_urls: list[str] | None = None,
    max_links: int = 5,
) -> list[dict[str, Any]]:
    """Find phrases in content that match content_inventory titles.

    Returns list of {title, url, anchor, position} for insertion.
    """
    exclude = set(exclude_urls or [])

    # Get published posts/pages (not products — those go in CTAs)
    inventory = session.execute(
        select(ContentInventory)
        .where(
            ContentInventory.status == "publish",
            ContentInventory.post_type.in_(["post", "page"]),
        )
    ).scalars().all()

    opportunities: list[dict[str, Any]] = []
    content_lower = content.lower()

    for item in inventory:
        if item.url in exclude:
            continue

        # Try matching title words in content
        title_words = [w for w in item.title.lower().split() if len(w) > 3]
        if not title_words:
            continue

        # Require at least 2 significant words to match (or 1 if title is short)
        min_match = min(2, len(title_words))
        matched_words = [w for w in title_words if w in content_lower]

        if len(matched_words) >= min_match:
            # Find a good anchor position — look for the matched phrase
            anchor = " ".join(matched_words[:4])
            pos = content_lower.find(matched_words[0])
            if pos >= 0:
                opportunities.append({
                    "title": item.title,
                    "url": item.url,
                    "anchor": anchor,
                    "position": pos,
                    "match_strength": len(matched_words) / len(title_words),
                })

    # Sort by match strength, take top N
    opportunities.sort(key=lambda x: -x["match_strength"])
    return opportunities[:max_links]


def insert_internal_links(
    content_html: str,
    links: list[dict[str, Any]],
) -> str:
    """Insert internal links into HTML content.

    Replaces first occurrence of anchor text with a hyperlink.
    Avoids linking inside existing <a> tags or headings.
    """
    result = content_html

    for link in links:
        anchor = link["anchor"]
        url = link["url"]

        # Find first occurrence not inside a tag
        pattern = re.compile(
            r"(?<![<\"/])(" + re.escape(anchor) + r")(?![^<]*>)",
            re.IGNORECASE,
        )

        replacement = f'<a href="{url}" title="{link["title"]}">{anchor}</a>'

        # Only replace first occurrence
        result, count = pattern.subn(replacement, result, count=1)
        if count > 0:
            log.debug("internal_link_inserted", anchor=anchor, url=url)

    return result


def add_internal_links(
    session: Session,
    content_html: str,
    draft_url: str | None = None,
    max_links: int = 5,
) -> tuple[str, list[dict[str, Any]]]:
    """Full internal linking: find opportunities and insert links.

    Returns (updated_html, links_inserted).
    """
    exclude = [draft_url] if draft_url else []
    opportunities = find_link_opportunities(session, content_html, exclude, max_links)
    updated = insert_internal_links(content_html, opportunities)
    log.info("internal_links_added", count=len(opportunities))
    return updated, opportunities
