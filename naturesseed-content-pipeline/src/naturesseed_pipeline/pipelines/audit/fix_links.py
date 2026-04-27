"""Apply a reviewed link-remapping plan to live WordPress content.

The plan is a markdown file produced by the audit pipeline (see
`docs/content-audit/link-remapping-plan.md`). For each section the user
marked `APPROVE` or `MAP TO <slug>` or `DELETE`, this module:

  1. Looks up every article whose `content_html` still contains the old href
  2. Performs a careful string replace (or anchor unwrap, for DELETE)
  3. POSTs the updated HTML back to WordPress via WordPressClient.update_post

`--dry-run` prints the plan and a sample of diffs without touching WP.
`--apply` makes the changes for real.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import ContentInventory, WcCatalogSnapshot
from naturesseed_pipeline.integrations.wordpress import WordPressClient

log = structlog.get_logger()


@dataclass
class RemapEntry:
    href: str
    decision: str  # APPROVE | SKIP | MAP TO <slug> | DELETE | REVIEW
    suggested_slug: str | None
    suggested_permalink: str | None
    explicit_slug: str | None  # set when decision starts with "MAP TO"


def parse_plan(text: str) -> list[RemapEntry]:
    """Parse the markdown plan. Returns one RemapEntry per `## ` section."""
    entries: list[RemapEntry] = []
    current: dict | None = None
    href_re = re.compile(r"^##\s+`([^`]+)`")
    field_re = re.compile(r"^-\s+\*\*([a-z ]+)\*\*:\s*(.+?)\s*$")
    slug_in_text = re.compile(r"`([a-z0-9][a-z0-9\-]*)`")

    for line in text.splitlines():
        m = href_re.match(line)
        if m:
            if current and current.get("href"):
                entries.append(_to_entry(current))
            current = {"href": m.group(1)}
            continue
        if not current:
            continue
        fm = field_re.match(line)
        if not fm:
            continue
        key = fm.group(1).strip().lower()
        val = fm.group(2).strip()
        if key == "decision":
            current["decision"] = val
        elif key == "suggested target slug":
            sm = slug_in_text.search(val)
            if sm:
                current["suggested_slug"] = sm.group(1)
        elif key == "target permalink":
            current["suggested_permalink"] = val
    if current and current.get("href"):
        entries.append(_to_entry(current))
    return entries


def _to_entry(d: dict) -> RemapEntry:
    decision = (d.get("decision") or "").strip()
    explicit_slug = None
    upper = decision.upper()
    if upper.startswith("MAP TO"):
        rest = decision[len("MAP TO"):].strip().strip("`").strip()
        explicit_slug = rest if rest else None
        decision = "MAP TO"
    elif upper in ("APPROVE", "SKIP", "DELETE", "REVIEW"):
        decision = upper
    else:
        decision = "SKIP"
    return RemapEntry(
        href=d["href"],
        decision=decision,
        suggested_slug=d.get("suggested_slug"),
        suggested_permalink=d.get("suggested_permalink"),
        explicit_slug=explicit_slug,
    )


def resolve_target(entry: RemapEntry, session: Session) -> tuple[str | None, str | None]:
    """Return (slug, permalink) of the target product for this entry,
    or (None, None) if entry should be skipped."""
    if entry.decision == "APPROVE":
        return entry.suggested_slug, entry.suggested_permalink
    if entry.decision == "MAP TO" and entry.explicit_slug:
        snap = session.execute(
            select(WcCatalogSnapshot).where(WcCatalogSnapshot.slug == entry.explicit_slug)
        ).scalar_one_or_none()
        if snap:
            return snap.slug, snap.permalink
    return None, None


def apply_one_article(
    content_id: int, session: Session,
    href_to_target: dict[str, str],
    delete_hrefs: set[str],
) -> tuple[str, list[str]]:
    """Rewrite one article's content_html. Returns (new_html, diffs).
    `diffs` is a list of human-readable change descriptions for logs/preview."""
    row = session.get(ContentInventory, content_id)
    if not row or not row.content_html:
        return "", []
    html = row.content_html
    diffs: list[str] = []

    # 1. Direct href replacements: any `<a href="<old>"` → `<a href="<new>"`
    for old_href, new_href in href_to_target.items():
        # Try the literal href first (most common)
        if old_href in html:
            count = html.count(old_href)
            html = html.replace(old_href, new_href)
            diffs.append(f"replaced {count}× `{old_href}` → `{new_href}`")

    # 2. DELETE: unwrap <a href="..."> ... </a> when href matches
    for href in delete_hrefs:
        # Match <a [attrs] href="<href>"[attrs]>TEXT</a> with the literal href
        # We escape the href and allow attrs around it.
        pattern = re.compile(
            r'<a\s+[^>]*href=["\']' + re.escape(href) + r'["\'][^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        def _unwrap(m): return m.group(1)
        new_html, n = pattern.subn(_unwrap, html)
        if n:
            diffs.append(f"unwrapped {n}× <a href=\"{href}\">…</a>")
            html = new_html

    return html, diffs


def find_articles_using(session: Session, hrefs: set[str]) -> set[int]:
    """Return the set of content_inventory IDs whose content_html mentions
    any of the given hrefs. Avoids loading entire HTML into Python by
    using SQLite LIKE."""
    if not hrefs:
        return set()
    matched: set[int] = set()
    for href in hrefs:
        rows = session.execute(
            select(ContentInventory.id).where(
                ContentInventory.content_html.like(f"%{href}%")
            )
        ).scalars().all()
        matched.update(rows)
    return matched


def run_fix_links(
    session: Session,
    plan_path: Path,
    apply: bool,
    wp: WordPressClient | None = None,
) -> dict:
    """Read the plan, build the remap dictionary, find affected articles,
    apply changes (dry-run by default).
    Returns counts dict: {entries, hrefs_to_remap, hrefs_to_delete, articles, edits, posted}."""
    text = plan_path.read_text()
    entries = parse_plan(text)

    href_to_target: dict[str, str] = {}
    delete_hrefs: set[str] = set()
    for e in entries:
        if e.decision == "DELETE":
            delete_hrefs.add(e.href)
        elif e.decision in ("APPROVE", "MAP TO"):
            slug, permalink = resolve_target(e, session)
            if permalink:
                href_to_target[e.href] = permalink

    affected = find_articles_using(session, set(href_to_target.keys()) | delete_hrefs)
    log.info("audit.fix_links.scope",
             entries=len(entries),
             hrefs_to_remap=len(href_to_target),
             hrefs_to_delete=len(delete_hrefs),
             affected_articles=len(affected))

    counts = {
        "entries": len(entries),
        "hrefs_to_remap": len(href_to_target),
        "hrefs_to_delete": len(delete_hrefs),
        "articles": len(affected),
        "edits": 0, "posted": 0,
    }

    created_wp = False
    if apply and wp is None:
        wp = WordPressClient()
        created_wp = True
    try:
        preview_count = 0
        for cid in sorted(affected):
            new_html, diffs = apply_one_article(cid, session, href_to_target, delete_hrefs)
            if not diffs:
                continue
            counts["edits"] += sum(1 for _ in diffs)
            row = session.get(ContentInventory, cid)
            if preview_count < 3 or apply:
                log.info("audit.fix_links.article",
                         id=cid, title=row.title[:60] if row else "?",
                         changes=len(diffs))
            preview_count += 1

            if apply and row and row.wp_post_id:
                try:
                    if row.post_type == "product":
                        # WC products use a different update endpoint — skip for now
                        log.warning("audit.fix_links.skip_product",
                                    id=cid, reason="WC product update not yet supported")
                        continue
                    wp.update_post(row.wp_post_id, content_html=new_html)
                    row.content_html = new_html
                    counts["posted"] += 1
                    log.info("audit.fix_links.posted", wp_post_id=row.wp_post_id)
                except Exception as e:
                    log.error("audit.fix_links.post_failed",
                              id=cid, wp_post_id=row.wp_post_id, error=str(e))
        if apply:
            session.commit()
    finally:
        if created_wp:
            wp.close()

    return counts
