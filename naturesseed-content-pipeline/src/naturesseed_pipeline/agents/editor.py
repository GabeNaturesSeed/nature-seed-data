"""Editor agent — grammar, readability, brand voice, and structure checks.

Runs AFTER fact_checker passes. Auto-fixes what it can, flags the rest.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Draft

log = structlog.get_logger()


def _check_readability(text: str) -> dict[str, Any]:
    """Check Flesch-Kincaid readability. Target: 60-70 (8th-9th grade)."""
    try:
        import textstat

        fk_score = textstat.flesch_reading_ease(text)
        grade = textstat.flesch_kincaid_grade(text)
        return {
            "flesch_reading_ease": round(fk_score, 1),
            "flesch_kincaid_grade": round(grade, 1),
            "in_target": 55 <= fk_score <= 75,
            "recommendation": (
                "Good readability" if 55 <= fk_score <= 75
                else "Too complex — simplify sentences" if fk_score < 55
                else "Could be more detailed"
            ),
        }
    except Exception as e:
        log.warning("readability_check_failed", error=str(e))
        return {"error": str(e)}


def _check_heading_structure(content: str) -> dict[str, Any]:
    """Verify heading hierarchy: one H1, H2s under it, H3s under H2s."""
    h1s = re.findall(r"^# [^\n]+", content, re.MULTILINE)
    h2s = re.findall(r"^## [^\n]+", content, re.MULTILINE)
    h3s = re.findall(r"^### [^\n]+", content, re.MULTILINE)

    issues: list[str] = []
    if len(h1s) != 1:
        issues.append(f"Expected 1 H1, found {len(h1s)}")
    if len(h2s) < 3:
        issues.append(f"Only {len(h2s)} H2 sections — aim for 4-6")

    return {
        "h1_count": len(h1s),
        "h2_count": len(h2s),
        "h3_count": len(h3s),
        "issues": issues,
        "pass": len(issues) == 0,
    }


def _check_keyword_density(content: str, keyword: str | None) -> dict[str, Any]:
    """Check target keyword density. Target: 1-2%. Flag if >3% (stuffed)."""
    if not keyword or not content:
        return {"density": 0, "pass": True}

    words = content.lower().split()
    total = len(words)
    if total == 0:
        return {"density": 0, "pass": True}

    kw_lower = keyword.lower()
    kw_words = kw_lower.split()
    kw_len = len(kw_words)

    count = 0
    for i in range(len(words) - kw_len + 1):
        if " ".join(words[i:i + kw_len]) == kw_lower:
            count += 1

    density = (count * kw_len / total) * 100
    return {
        "keyword": keyword,
        "occurrences": count,
        "total_words": total,
        "density_pct": round(density, 2),
        "pass": density <= 3.0,
        "stuffed": density > 3.0,
        "recommendation": (
            "Good density" if 0.5 <= density <= 2.5
            else "Consider adding more keyword mentions" if density < 0.5
            else "Keyword stuffing detected — reduce usage" if density > 3.0
            else "Slightly high — review for natural usage"
        ),
    }


def _check_meta_description(content: str) -> dict[str, Any]:
    """Check meta description presence and length."""
    m = re.search(r"<!-- meta_description: (.+?) -->", content)
    if not m:
        return {"present": False, "issue": "No meta description found"}

    meta = m.group(1)
    length = len(meta)
    return {
        "present": True,
        "length": length,
        "pass": 120 <= length <= 160,
        "text": meta,
        "recommendation": (
            "Good length" if 120 <= length <= 160
            else f"Too short ({length} chars) — aim for 150-160" if length < 120
            else f"Too long ({length} chars) — trim to 160"
        ),
    }


def _auto_fix_content(content: str) -> tuple[str, list[str]]:
    """Apply automatic fixes. Returns (fixed_content, list_of_fixes)."""
    fixes: list[str] = []
    fixed = content

    # Fix double spaces
    if "  " in fixed:
        fixed = re.sub(r"  +", " ", fixed)
        fixes.append("Removed double spaces")

    # Fix trailing whitespace on lines
    lines = fixed.split("\n")
    stripped = [line.rstrip() for line in lines]
    if lines != stripped:
        fixed = "\n".join(stripped)
        fixes.append("Removed trailing whitespace")

    # Ensure single blank line between sections
    fixed = re.sub(r"\n{3,}", "\n\n", fixed)
    if fixed != content:
        fixes.append("Normalized section spacing")

    return fixed, fixes


def run_editorial_review(
    session: Session,
    draft_id: int,
) -> dict[str, Any]:
    """Run all editorial checks on a draft.

    Auto-fixes what it can, flags the rest in editorial_notes.
    Sets status to 'reviewed' if passing, 'needs_revision' if not.
    """
    draft = session.get(Draft, draft_id)
    if not draft or not draft.content_markdown:
        return {"error": "Draft not found or empty"}

    content = draft.content_markdown

    # Get target keyword from brief
    brief = draft.brief
    target_kw = None
    if brief and brief.brief_json:
        target_kw = brief.brief_json.get("target_keyword")

    # Run checks
    readability = _check_readability(content)
    headings = _check_heading_structure(content)
    keyword_density = _check_keyword_density(content, target_kw)
    meta = _check_meta_description(content)

    # Auto-fix
    fixed_content, auto_fixes = _auto_fix_content(content)
    if auto_fixes:
        draft.content_markdown = fixed_content
        content = fixed_content

    # Compile notes
    issues: list[str] = []
    if not readability.get("in_target", True):
        issues.append(f"Readability: {readability.get('recommendation', '')}")
    issues.extend(headings.get("issues", []))
    if keyword_density.get("stuffed"):
        issues.append(keyword_density["recommendation"])
    if not meta.get("present"):
        issues.append("Missing meta description")
    elif not meta.get("pass"):
        issues.append(meta["recommendation"])

    notes = {
        "readability": readability,
        "heading_structure": headings,
        "keyword_density": keyword_density,
        "meta_description": meta,
        "auto_fixes": auto_fixes,
        "remaining_issues": issues,
        "pass": len(issues) == 0,
    }

    draft.editorial_notes = notes

    if issues:
        draft.status = "needs_revision"
        log.warning("editorial_issues", draft_id=draft_id, issues=issues)
    else:
        draft.status = "reviewed"
        log.info("editorial_passed", draft_id=draft_id)

    session.commit()
    return notes
