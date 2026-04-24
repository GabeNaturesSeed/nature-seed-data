"""Brief generator agent — produces structured content briefs from scored keywords.

Input: keyword_candidate_id
Output: structured brief_json in brief_queue with all required fields.

Pulls SERP data, competitor content (via trafilatura), related keywords,
relevant media signals, and internal content for linking opportunities.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    BriefQueue,
    ContentInventory,
    KeywordCandidate,
    MediaSignal,
)

log = structlog.get_logger()


def _scrape_url(url: str) -> str | None:
    """Scrape a URL for main text content using trafilatura."""
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded, include_comments=False)
    except Exception as e:
        log.warning("scrape_failed", url=url, error=str(e))
    return None


def _estimate_word_count(texts: list[str | None]) -> int:
    """Estimate recommended word count from competitor content lengths."""
    counts = [len(t.split()) for t in texts if t]
    if not counts:
        return 1500  # sensible default for seed/garden content
    avg = sum(counts) // len(counts)
    # Aim for 10-20% longer than competitor average
    return max(800, min(int(avg * 1.15), 5000))


def _find_internal_link_candidates(
    session: Session, keyword: str, limit: int = 5
) -> list[dict[str, str]]:
    """Find content_inventory rows that could serve as internal links.

    Simple approach: search for rows where the keyword appears in title or content_text.
    """
    kw_lower = keyword.lower()
    # Split keyword into meaningful words (skip stopwords)
    words = [w for w in kw_lower.split() if len(w) > 3]
    if not words:
        words = kw_lower.split()[:2]

    candidates: list[dict[str, str]] = []
    for word in words[:3]:
        rows = session.execute(
            select(ContentInventory)
            .where(
                ContentInventory.status == "publish",
                ContentInventory.title.ilike(f"%{word}%"),
            )
            .limit(limit)
        ).scalars().all()
        for r in rows:
            if r.url and not any(c["url"] == r.url for c in candidates):
                candidates.append({"title": r.title, "url": r.url})

    return candidates[:limit]


def _find_product_ctas(
    session: Session, keyword: str, limit: int = 5
) -> list[dict[str, str]]:
    """Find WC products in content_inventory that match the topic for CTAs."""
    kw_lower = keyword.lower()
    words = [w for w in kw_lower.split() if len(w) > 3]
    if not words:
        words = kw_lower.split()[:2]

    products: list[dict[str, str]] = []
    for word in words[:3]:
        rows = session.execute(
            select(ContentInventory)
            .where(
                ContentInventory.post_type == "product",
                ContentInventory.status == "publish",
                ContentInventory.title.ilike(f"%{word}%"),
            )
            .limit(limit)
        ).scalars().all()
        for r in rows:
            if r.url and not any(p["url"] == r.url for p in products):
                products.append({"title": r.title, "url": r.url})

    return products[:limit]


def _get_media_context(session: Session, keyword: str, limit: int = 3) -> list[dict[str, str]]:
    """Find recent media signals relevant to this keyword."""
    kw_lower = keyword.lower()
    words = [w for w in kw_lower.split() if len(w) > 3]
    if not words:
        return []

    signals: list[dict[str, str]] = []
    from sqlalchemy import func as sqlfunc

    for word in words[:2]:
        rows = session.execute(
            select(MediaSignal)
            .where(
                MediaSignal.relevance_score >= 0.5,
                sqlfunc.lower(MediaSignal.title).contains(word),
            )
            .order_by(MediaSignal.trending_score.desc())
            .limit(limit)
        ).scalars().all()
        for s in rows:
            if not any(x["url"] == s.url for x in signals):
                signals.append({
                    "title": s.title or "",
                    "url": s.url or "",
                    "source": f"{s.source_type}/{s.source_name or ''}",
                })

    return signals[:limit]


def _build_outline(keyword: str, intent: str | None, competitor_texts: list[str | None]) -> list[dict[str, Any]]:
    """Generate an H2/H3 outline structure based on keyword and intent.

    Uses simple heuristics + headings extracted from competitor content.
    """
    sections: list[dict[str, Any]] = []

    # Extract H2-like patterns from competitor text
    competitor_headings: list[str] = []
    for text in competitor_texts:
        if not text:
            continue
        # Look for lines that look like headings (short, capitalized)
        for line in text.split("\n"):
            line = line.strip()
            if 5 < len(line) < 80 and not line.endswith(".") and line[0].isupper():
                competitor_headings.append(line)

    # Standard article structure
    if intent in ("informational", None):
        sections = [
            {"heading": f"What is {keyword.title()}?", "level": "H2",
             "points": ["Definition", "Why it matters for gardeners"]},
            {"heading": f"How to Choose the Right {keyword.title()}", "level": "H2",
             "points": ["Key factors", "Common mistakes"]},
            {"heading": "Step-by-Step Guide", "level": "H2",
             "points": ["Preparation", "Planting", "Care and maintenance"]},
            {"heading": "Tips from Expert Growers", "level": "H2",
             "points": ["Pro tips", "Seasonal considerations"]},
            {"heading": "Frequently Asked Questions", "level": "H2",
             "points": ["Top 3-5 PAA questions"]},
        ]
    elif intent in ("commercial", "transactional"):
        sections = [
            {"heading": f"Best {keyword.title()} Options for 2025", "level": "H2",
             "points": ["Top picks", "Comparison table"]},
            {"heading": "What to Look for When Buying", "level": "H2",
             "points": ["Quality indicators", "Price vs value"]},
            {"heading": f"Our {keyword.title()} Collection", "level": "H2",
             "points": ["Product highlights", "What sets us apart"]},
            {"heading": "Customer Results", "level": "H2",
             "points": ["Success stories", "Before/after"]},
            {"heading": "Growing Guide", "level": "H2",
             "points": ["Quick-start instructions"]},
        ]

    # Append competitor-inspired sections (deduped)
    existing_headings = {s["heading"].lower() for s in sections}
    for h in competitor_headings[:3]:
        if h.lower() not in existing_headings:
            sections.append({
                "heading": h,
                "level": "H2",
                "points": ["(Competitor covers this — analyze their approach)"],
            })

    return sections


def _identify_citation_requirements(outline: list[dict[str, Any]]) -> list[str]:
    """Identify which claims in the outline need citations.

    Returns a list of specific claims that MUST be sourced.
    """
    citation_triggers = [
        "percent", "study", "research", "according", "statistics",
        "USDA", "university", "data shows", "expert",
    ]
    citations: list[str] = []

    for section in outline:
        for point in section.get("points", []):
            for trigger in citation_triggers:
                if trigger.lower() in point.lower():
                    citations.append(f"[{section['heading']}] {point}")
                    break

    # Always require citations for factual claims
    citations.append("Any germination rates or growing zone claims")
    citations.append("Any soil/climate requirement specifics")
    citations.append("Any pricing comparisons with competitors")

    return citations


def generate_brief(
    session: Session,
    keyword_id: int,
    scrape_competitors: bool = True,
) -> BriefQueue | None:
    """Generate a structured content brief for a keyword candidate.

    Returns the created BriefQueue row, or None if keyword not found.
    """
    kw = session.get(KeywordCandidate, keyword_id)
    if not kw:
        log.error("keyword_not_found", id=keyword_id)
        return None

    # Check if brief already exists for this keyword
    existing = session.execute(
        select(BriefQueue).where(BriefQueue.keyword_candidate_id == keyword_id)
    ).scalar_one_or_none()
    if existing:
        log.info("brief_already_exists", keyword=kw.keyword, brief_id=existing.id)
        return existing

    log.info("generating_brief", keyword=kw.keyword, id=keyword_id)

    # Gather SERP competitor URLs
    competitor_urls: list[str] = []
    if kw.serp_features and isinstance(kw.serp_features, dict):
        top3 = kw.serp_features.get("top3_domains", [])
        for result in (kw.serp_features.get("organic_results", []) or [])[:3]:
            if isinstance(result, dict) and result.get("url"):
                competitor_urls.append(result["url"])

    # Scrape competitor content
    competitor_texts: list[str | None] = []
    competitor_analysis: list[dict[str, str]] = []
    if scrape_competitors and competitor_urls:
        for url in competitor_urls[:3]:
            text = _scrape_url(url)
            competitor_texts.append(text)
            if text:
                word_count = len(text.split())
                competitor_analysis.append({
                    "url": url,
                    "word_count": word_count,
                    "summary": text[:300] + "..." if len(text) > 300 else text,
                })

    # Related keywords
    secondary_keywords: list[str] = []
    if kw.related_keywords and isinstance(kw.related_keywords, list):
        secondary_keywords = kw.related_keywords[:10]
    elif kw.related_keywords and isinstance(kw.related_keywords, dict):
        secondary_keywords = kw.related_keywords.get("related", [])[:10]

    # Build outline
    outline = _build_outline(kw.keyword, kw.intent, competitor_texts)

    # Suggested titles
    titles = _generate_titles(kw.keyword, kw.intent)

    # Internal links and product CTAs
    internal_links = _find_internal_link_candidates(session, kw.keyword)
    product_ctas = _find_product_ctas(session, kw.keyword)

    # Media context
    media_context = _get_media_context(session, kw.keyword)

    # Citation requirements
    citations = _identify_citation_requirements(outline)

    # Recommended word count
    word_count = _estimate_word_count(competitor_texts)

    # Build the brief JSON
    brief_data: dict[str, Any] = {
        "target_keyword": kw.keyword,
        "secondary_keywords": secondary_keywords,
        "search_intent": kw.intent or "informational",
        "suggested_title_options": titles,
        "recommended_word_count": word_count,
        "outline": outline,
        "competitor_gap_notes": {
            "competitors_analyzed": competitor_analysis,
            "what_they_cover": [s["heading"] for s in outline if "(Competitor" in str(s.get("points", []))],
            "opportunities": "Focus on Nature's Seed specific expertise, product quality, and growing-zone-specific advice.",
        },
        "internal_link_candidates": internal_links,
        "product_cta_candidates": product_ctas,
        "citation_requirements": citations,
        "media_signals": media_context,
        "suggested_angle": _suggest_angle(kw.keyword, kw.intent),
        "metadata": {
            "keyword_candidate_id": keyword_id,
            "search_volume": kw.search_volume,
            "keyword_difficulty": kw.keyword_difficulty,
            "gap_score": kw.gap_score,
            "priority_score": kw.priority_score,
        },
    }

    # Create brief queue entry
    brief = BriefQueue(
        keyword_candidate_id=keyword_id,
        topic=kw.keyword,
        target_keyword=kw.keyword,
        brief_json=brief_data,
        priority_score=kw.priority_score,
        status="pending",
    )
    session.add(brief)

    # Update keyword status
    kw.status = "briefed"
    session.commit()

    log.info("brief_generated", keyword=kw.keyword, brief_id=brief.id)
    return brief


def _generate_titles(keyword: str, intent: str | None) -> list[str]:
    """Generate 3 title options based on keyword and intent."""
    kw_title = keyword.title()
    if intent in ("transactional", "commercial"):
        return [
            f"Best {kw_title} for 2025: Expert Picks & Growing Guide",
            f"{kw_title}: Complete Buying Guide for Home Gardeners",
            f"Top {kw_title} Varieties Compared — Which is Right for You?",
        ]
    return [
        f"{kw_title}: The Complete Guide for Home Gardeners",
        f"How to Grow {kw_title} — Expert Tips & Step-by-Step Guide",
        f"Everything You Need to Know About {kw_title} in 2025",
    ]


def _suggest_angle(keyword: str, intent: str | None) -> str:
    """Suggest what makes Nature's Seed's take distinct."""
    if intent in ("transactional", "commercial"):
        return (
            f"Position as the seed-quality expert. Emphasize Nature's Seed's "
            f"direct-from-grower supply chain, purity testing, and growing-zone-specific "
            f"recommendations. Include real planting calendar data for {keyword}."
        )
    return (
        f"Lead with practical, zone-specific growing advice from Nature's Seed's "
        f"horticulture team. Focus on actionable steps that readers can apply "
        f"immediately. Differentiate from generic gardening blogs by including "
        f"specific variety recommendations from our catalog."
    )


def generate_top_briefs(
    session: Session,
    count: int = 5,
    scrape: bool = True,
) -> list[BriefQueue]:
    """Generate briefs for the top N scored keywords."""
    from naturesseed_pipeline.pipelines.scoring import rank_backlog

    ranked = rank_backlog(session, limit=count * 2)  # overfetch for already-briefed

    briefs: list[BriefQueue] = []
    for kw, score in ranked:
        if len(briefs) >= count:
            break
        # Skip if already briefed
        existing = session.execute(
            select(BriefQueue).where(BriefQueue.keyword_candidate_id == kw.id)
        ).scalar_one_or_none()
        if existing:
            continue

        brief = generate_brief(session, kw.id, scrape_competitors=scrape)
        if brief:
            briefs.append(brief)

    return briefs


def format_brief_markdown(brief: BriefQueue) -> str:
    """Pretty-print a brief as markdown."""
    b = brief.brief_json or {}
    lines: list[str] = []

    lines.append(f"# Brief: {b.get('target_keyword', brief.topic)}")
    lines.append(f"**ID:** {brief.id}  |  **Status:** {brief.status}  |  **Priority:** {brief.priority_score or '-'}")
    lines.append("")

    lines.append(f"**Search Intent:** {b.get('search_intent', '-')}")
    lines.append(f"**Recommended Word Count:** {b.get('recommended_word_count', '-')}")
    lines.append("")

    meta = b.get("metadata", {})
    if meta:
        lines.append(f"**Volume:** {meta.get('search_volume', '-')}  |  "
                      f"**Difficulty:** {meta.get('keyword_difficulty', '-')}  |  "
                      f"**Gap:** {meta.get('gap_score', '-')}")
        lines.append("")

    # Titles
    lines.append("## Suggested Titles")
    for i, t in enumerate(b.get("suggested_title_options", []), 1):
        lines.append(f"{i}. {t}")
    lines.append("")

    # Secondary keywords
    secs = b.get("secondary_keywords", [])
    if secs:
        lines.append(f"## Secondary Keywords")
        lines.append(", ".join(secs))
        lines.append("")

    # Outline
    outline = b.get("outline", [])
    if outline:
        lines.append("## Outline")
        for section in outline:
            level = section.get("level", "H2")
            prefix = "##" if level == "H2" else "###"
            lines.append(f"{prefix} {section.get('heading', '')}")
            for point in section.get("points", []):
                lines.append(f"- {point}")
            lines.append("")

    # Competitor gap notes
    gap = b.get("competitor_gap_notes", {})
    if gap:
        lines.append("## Competitor Analysis")
        for comp in gap.get("competitors_analyzed", []):
            lines.append(f"- [{comp.get('url', '')}] ({comp.get('word_count', '?')} words)")
        if gap.get("opportunities"):
            lines.append(f"\n**Opportunity:** {gap['opportunities']}")
        lines.append("")

    # Internal links
    links = b.get("internal_link_candidates", [])
    if links:
        lines.append("## Internal Link Candidates")
        for link in links:
            lines.append(f"- [{link.get('title', '')}]({link.get('url', '')})")
        lines.append("")

    # Product CTAs
    ctas = b.get("product_cta_candidates", [])
    if ctas:
        lines.append("## Product CTA Candidates")
        for cta in ctas:
            lines.append(f"- [{cta.get('title', '')}]({cta.get('url', '')})")
        lines.append("")

    # Citations
    cites = b.get("citation_requirements", [])
    if cites:
        lines.append("## Citation Requirements")
        for c in cites:
            lines.append(f"- {c}")
        lines.append("")

    # Suggested angle
    angle = b.get("suggested_angle", "")
    if angle:
        lines.append("## Suggested Angle")
        lines.append(angle)
        lines.append("")

    return "\n".join(lines)
