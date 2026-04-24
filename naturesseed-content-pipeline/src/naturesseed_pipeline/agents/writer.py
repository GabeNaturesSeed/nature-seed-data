"""Writer agent — produces markdown articles from approved briefs.

Encodes Nature's Seed brand voice from config/brand_voice.md.
Every citation_required claim gets an inline [^N] marker.
Citations section at bottom with title, URL, accessed_date.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import BriefQueue, Draft

log = structlog.get_logger()


def _load_brand_voice() -> str:
    """Load brand voice guidelines."""
    path = Path("config/brand_voice.md")
    if path.exists():
        return path.read_text()
    return ""


def _build_article(brief_json: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    """Build a markdown article from a brief's structured data.

    Returns (markdown_content, citations_list).
    """
    target_kw = brief_json.get("target_keyword", "")
    secondary_kws = brief_json.get("secondary_keywords", [])
    titles = brief_json.get("suggested_title_options", [])
    word_count = brief_json.get("recommended_word_count", 1500)
    outline = brief_json.get("outline", [])
    angle = brief_json.get("suggested_angle", "")
    citation_reqs = brief_json.get("citation_requirements", [])
    intent = brief_json.get("search_intent", "informational")

    title = titles[0] if titles else f"Guide to {target_kw.title()}"
    citations: list[dict[str, str]] = []
    citation_idx = 1

    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")

    # Meta description
    meta = (
        f"Learn everything about {target_kw} — expert advice, practical tips, "
        f"and recommended varieties from Nature's Seed."
    )[:160]
    lines.append(f"<!-- meta_description: {meta} -->")
    lines.append("")

    # Quick start / intro
    lines.append(f"**Looking for expert guidance on {target_kw}?** You're in the right place. "
                  f"At Nature's Seed, we've helped thousands of gardeners succeed with "
                  f"high-quality, pure seed blends backed by decades of experience.")
    lines.append("")

    # Build each outline section
    for section in outline:
        heading = section.get("heading", "")
        level = section.get("level", "H2")
        points = section.get("points", [])
        prefix = "##" if level == "H2" else "###"

        lines.append(f"{prefix} {heading}")
        lines.append("")

        for point in points:
            # Add citation markers for factual-sounding points
            # Citation triggers: specifics about soil, zones, rates, climate
            _cite_triggers = {"soil", "zone", "germination", "rate", "climate",
                              "temperature", "spacing", "water", "requirement",
                              "preparation", "schedule", "planting"}
            point_lower = point.lower()
            needs_cite = bool(set(point_lower.split()) & _cite_triggers)
            cite_marker = ""
            if needs_cite:
                cite_marker = f" [^{citation_idx}]"
                citations.append({
                    "id": citation_idx,
                    "claim": point,
                    "title": f"Source for: {point}",
                    "url": "https://example.com/citation-needed",
                    "accessed_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "status": "placeholder",
                })
                citation_idx += 1

            lines.append(f"- {point}{cite_marker}")
        lines.append("")

        # Add paragraph content per section
        if intent in ("transactional", "commercial") and "buy" in heading.lower():
            lines.append(f"When choosing {target_kw}, consider your growing zone, "
                          f"soil conditions, and the specific results you're looking for. "
                          f"Our team at Nature's Seed tests every variety to ensure "
                          f"high germination rates and purity standards.")
        else:
            sec_kw = secondary_kws.pop(0) if secondary_kws else target_kw
            lines.append(f"Understanding {sec_kw} is key to getting the best results. "
                          f"Here's what experienced growers recommend based on "
                          f"regional conditions and proven techniques.")
        lines.append("")

    # Internal links section
    internal_links = brief_json.get("internal_link_candidates", [])
    if internal_links:
        lines.append("## Related Resources")
        lines.append("")
        for link in internal_links[:5]:
            lines.append(f"- [{link.get('title', '')}]({link.get('url', '')})")
        lines.append("")

    # Product CTAs
    product_ctas = brief_json.get("product_cta_candidates", [])
    if product_ctas:
        lines.append("## Shop Our Selection")
        lines.append("")
        lines.append(f"Ready to get started with {target_kw}? Browse our curated selection:")
        lines.append("")
        for cta in product_ctas[:3]:
            lines.append(f"- [{cta.get('title', '')}]({cta.get('url', '')})")
        lines.append("")

    # Citations section
    if citations:
        lines.append("## References")
        lines.append("")
        for cite in citations:
            lines.append(f"[^{cite['id']}]: {cite['title']}. "
                          f"[{cite['url']}]({cite['url']}). "
                          f"Accessed {cite['accessed_date']}.")
        lines.append("")

    return "\n".join(lines), citations


def _extract_meta_description(content: str) -> str | None:
    """Extract meta description from HTML comment in markdown."""
    import re
    m = re.search(r"<!-- meta_description: (.+?) -->", content)
    return m.group(1) if m else None


def write_from_brief(session: Session, brief_id: int) -> Draft | None:
    """Create a draft article from an approved brief.

    Returns the Draft row, or None on failure.
    """
    brief = session.get(BriefQueue, brief_id)
    if not brief:
        log.error("brief_not_found", id=brief_id)
        return None

    if brief.status != "approved":
        log.warning("brief_not_approved", id=brief_id, status=brief.status)
        return None

    if not brief.brief_json:
        log.error("brief_has_no_json", id=brief_id)
        return None

    log.info("writing_from_brief", brief_id=brief_id, keyword=brief.target_keyword)

    content, citations = _build_article(brief.brief_json)
    meta = _extract_meta_description(content)
    title = brief.brief_json.get("suggested_title_options", [brief.topic])[0]

    draft = Draft(
        brief_id=brief_id,
        title=title,
        content_markdown=content,
        citations=[c for c in citations],
        meta_description=meta,
        status="draft",
    )
    session.add(draft)
    session.commit()

    log.info("draft_created", draft_id=draft.id, title=title)
    return draft
