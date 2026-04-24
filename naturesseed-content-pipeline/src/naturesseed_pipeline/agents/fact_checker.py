"""Fact checker agent — verifies cited claims against sources.

Runs AFTER writer. Extracts factual claims, fetches cited URLs,
checks if the source supports the claim. Flags unsupported claims.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Draft

log = structlog.get_logger()


def _fetch_source_text(url: str) -> str | None:
    """Fetch and extract text from a citation URL."""
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded, include_comments=False)
    except Exception as e:
        log.warning("source_fetch_failed", url=url, error=str(e))
    return None


def _extract_citations_from_markdown(content: str) -> list[dict[str, str]]:
    """Extract footnote citations from markdown content."""
    citations: list[dict[str, str]] = []
    # Match [^N]: Title. [URL](URL). Accessed date.
    pattern = re.compile(
        r"\[\^(\d+)\]:\s+(.+?)\.\s+\[(.+?)\]\(.+?\)\.\s+Accessed\s+(.+?)\."
    )
    for m in pattern.finditer(content):
        citations.append({
            "id": m.group(1),
            "title": m.group(2),
            "url": m.group(3),
            "accessed": m.group(4),
        })
    return citations


def _extract_claims(content: str) -> list[dict[str, Any]]:
    """Extract lines with citation markers and their claims."""
    claims: list[dict[str, Any]] = []
    pattern = re.compile(r"(.+?)\s*\[\^(\d+)\]")
    for m in pattern.finditer(content):
        claim_text = m.group(1).strip().lstrip("- ")
        cite_id = m.group(2)
        claims.append({
            "text": claim_text,
            "citation_id": cite_id,
        })
    return claims


def _verify_claim(claim_text: str, source_text: str) -> dict[str, Any]:
    """Check if a claim is supported by the source text.

    Simple heuristic: check if key words from the claim appear in the source.
    Returns verification result.
    """
    if not source_text:
        return {"supported": False, "reason": "Source could not be fetched"}

    # Extract significant words from claim (>3 chars, not common words)
    stop_words = {"the", "and", "for", "with", "that", "this", "from", "your", "have"}
    claim_words = [
        w.lower() for w in re.findall(r"\b\w+\b", claim_text)
        if len(w) > 3 and w.lower() not in stop_words
    ]

    if not claim_words:
        return {"supported": True, "reason": "No verifiable terms"}

    source_lower = source_text.lower()
    matched = sum(1 for w in claim_words if w in source_lower)
    ratio = matched / len(claim_words) if claim_words else 0

    if ratio >= 0.5:
        return {"supported": True, "reason": f"Matched {matched}/{len(claim_words)} key terms"}
    elif ratio >= 0.25:
        return {"supported": True, "reason": f"Partial match ({matched}/{len(claim_words)} terms)", "warning": True}
    else:
        return {"supported": False, "reason": f"Only {matched}/{len(claim_words)} key terms found in source"}


def check_facts(
    session: Session,
    draft_id: int,
    fetch_sources: bool = True,
) -> dict[str, Any]:
    """Run fact-checking on a draft.

    Returns a summary dict. Updates draft.fact_check_notes and potentially
    sets status=needs_revision if critical claims are unsupported.
    """
    draft = session.get(Draft, draft_id)
    if not draft or not draft.content_markdown:
        return {"error": "Draft not found or empty"}

    content = draft.content_markdown
    claims = _extract_claims(content)
    citations = _extract_citations_from_markdown(content)

    # Build citation map
    cite_map: dict[str, dict[str, str]] = {}
    for c in citations:
        cite_map[c["id"]] = c

    results: list[dict[str, Any]] = []
    unsupported_count = 0
    placeholder_count = 0

    for claim in claims:
        cite_id = claim["citation_id"]
        citation = cite_map.get(cite_id)

        if not citation:
            results.append({
                "claim": claim["text"],
                "citation_id": cite_id,
                "status": "missing_citation",
                "reason": "No matching citation found",
            })
            unsupported_count += 1
            continue

        url = citation.get("url", "")

        # Check for placeholder citations
        if "example.com" in url or "citation-needed" in url:
            results.append({
                "claim": claim["text"],
                "citation_id": cite_id,
                "url": url,
                "status": "placeholder",
                "reason": "Citation URL is a placeholder — needs real source",
            })
            placeholder_count += 1
            continue

        if fetch_sources:
            source_text = _fetch_source_text(url)
            verification = _verify_claim(claim["text"], source_text or "")
            results.append({
                "claim": claim["text"],
                "citation_id": cite_id,
                "url": url,
                "status": "supported" if verification["supported"] else "unsupported",
                "reason": verification["reason"],
            })
            if not verification["supported"]:
                unsupported_count += 1
        else:
            results.append({
                "claim": claim["text"],
                "citation_id": cite_id,
                "url": url,
                "status": "unchecked",
                "reason": "Source fetch disabled",
            })

    # Build summary
    summary = {
        "total_claims": len(claims),
        "total_citations": len(citations),
        "supported": sum(1 for r in results if r["status"] == "supported"),
        "unsupported": unsupported_count,
        "placeholders": placeholder_count,
        "unchecked": sum(1 for r in results if r["status"] == "unchecked"),
        "details": results,
    }

    # Update draft
    draft.fact_check_notes = summary

    if unsupported_count > 0:
        draft.status = "needs_revision"
        log.warning("fact_check_failed", draft_id=draft_id, unsupported=unsupported_count)
    else:
        log.info("fact_check_passed", draft_id=draft_id, claims=len(claims))

    session.commit()
    return summary
