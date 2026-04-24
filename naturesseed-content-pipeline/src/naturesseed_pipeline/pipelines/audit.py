"""Audit pipeline — content inventory sync + orphan product reference detection."""

import re
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import ContentInventory, OrphanReference
from naturesseed_pipeline.integrations.wordpress import (
    WooCommerceClient,
    WordPressClient,
    html_to_text,
)
from naturesseed_pipeline.pipelines.orphans import (
    ProductIndex,
    build_product_index,
    scan_content,
)

log = structlog.get_logger()


def _infer_target_keyword(title: str, html: str | None) -> str | None:
    """Heuristic: use first H1 if present, otherwise title."""
    if html:
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        if m:
            return html_to_text(m.group(1)).strip()[:300]
    return title.strip()[:300] if title else None


def _parse_wp_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_categories(item: dict[str, Any]) -> list[int]:
    """Extract category IDs from a WP REST API item."""
    cats = item.get("categories", [])
    if isinstance(cats, list):
        return cats
    return []


def _extract_tags(item: dict[str, Any]) -> list[int]:
    tags = item.get("tags", [])
    if isinstance(tags, list):
        return tags
    return []


def upsert_content(session: Session, item: dict[str, Any], post_type: str) -> ContentInventory:
    """Insert or update a content_inventory row by wp_post_id."""
    wp_id = item["id"]
    row = session.execute(
        select(ContentInventory).where(ContentInventory.wp_post_id == wp_id)
    ).scalar_one_or_none()

    raw_html = item.get("content", {}).get("rendered", "")
    plain_text = html_to_text(raw_html)
    title = html_to_text(item.get("title", {}).get("rendered", ""))
    excerpt_html = item.get("excerpt", {}).get("rendered", "")

    now = datetime.now(timezone.utc)

    if row is None:
        row = ContentInventory(wp_post_id=wp_id)
        session.add(row)

    row.url = item.get("link", "")
    row.title = title
    row.slug = item.get("slug", "")
    row.content_html = raw_html
    row.content_text = plain_text
    row.excerpt = html_to_text(excerpt_html) if excerpt_html else None
    row.post_type = post_type
    row.status = item.get("status", "publish")
    row.categories = _extract_categories(item)
    row.tags = _extract_tags(item)
    row.word_count = len(plain_text.split()) if plain_text else 0
    row.published_at = _parse_wp_datetime(item.get("date_gmt"))
    row.modified_at = _parse_wp_datetime(item.get("modified_gmt"))
    row.target_keyword = _infer_target_keyword(title, raw_html)
    row.last_audited_at = now

    return row


def upsert_product(session: Session, item: dict[str, Any]) -> ContentInventory:
    """Upsert a WC product into content_inventory."""
    wp_id = item["id"]
    row = session.execute(
        select(ContentInventory).where(ContentInventory.wp_post_id == wp_id)
    ).scalar_one_or_none()

    raw_html = item.get("description", "")
    plain_text = html_to_text(raw_html)
    title = item.get("name", "")
    now = datetime.now(timezone.utc)

    if row is None:
        row = ContentInventory(wp_post_id=wp_id)
        session.add(row)

    row.url = item.get("permalink", "")
    row.title = title
    row.slug = item.get("slug", "")
    row.content_html = raw_html
    row.content_text = plain_text
    row.excerpt = html_to_text(item.get("short_description", ""))
    row.post_type = "product"
    row.status = item.get("status", "publish")
    row.categories = [c["id"] for c in item.get("categories", []) if "id" in c]
    row.tags = [t["id"] for t in item.get("tags", []) if "id" in t]
    row.word_count = len(plain_text.split()) if plain_text else 0
    row.published_at = _parse_wp_datetime(item.get("date_created_gmt"))
    row.modified_at = _parse_wp_datetime(item.get("date_modified_gmt"))
    row.target_keyword = _infer_target_keyword(title, raw_html)
    row.last_audited_at = now

    return row


def run_content_sync(
    session: Session,
    wp: WordPressClient,
    wc: WooCommerceClient,
    since: str | None = None,
) -> dict[str, int]:
    """Pull posts, pages, products into content_inventory. Returns counts."""
    counts = {"posts": 0, "pages": 0, "products": 0}

    log.info("syncing posts", since=since)
    posts = wp.list_posts(since=since)
    for item in posts:
        upsert_content(session, item, "post")
        counts["posts"] += 1
    session.flush()

    log.info("syncing pages", since=since)
    pages = wp.list_pages(since=since)
    for item in pages:
        upsert_content(session, item, "page")
        counts["pages"] += 1
    session.flush()

    log.info("syncing products")
    products = wc.list_all_products()
    for item in products:
        upsert_product(session, item)
        counts["products"] += 1
    session.flush()

    log.info("content sync complete", **counts)
    return counts


def run_orphan_scan(
    session: Session,
    wc: WooCommerceClient,
) -> int:
    """Scan all content for orphan product references. Returns flag count."""
    log.info("building product indexes")
    active_products = wc.list_products(status="publish")
    all_products = wc.list_all_products()
    inactive_products = [
        p for p in all_products if p.get("status") != "publish"
    ]

    active_idx = build_product_index(active_products)
    inactive_idx = build_product_index(inactive_products)

    # Get all content rows
    rows = session.execute(select(ContentInventory)).scalars().all()
    log.info("scanning content for orphan refs", content_count=len(rows))

    # Load existing flagged refs to avoid re-flagging decided ones
    existing = session.execute(select(OrphanReference)).scalars().all()
    decided_keys: set[tuple[int, str, str]] = set()
    existing_keys: set[tuple[int, str, str]] = set()
    for ref in existing:
        key = (ref.content_inventory_id, ref.reference_type, ref.reference_value)
        existing_keys.add(key)
        if ref.user_decision_at is not None:
            decided_keys.add(key)

    new_flags = 0
    for row in rows:
        hits = scan_content(row.content_text, row.content_html, active_idx, inactive_idx)
        for hit in hits:
            key = (row.id, hit.reference_type, hit.reference_value)
            if key in decided_keys or key in existing_keys:
                continue
            orphan = OrphanReference(
                content_inventory_id=row.id,
                reference_type=hit.reference_type,
                reference_value=hit.reference_value,
                matched_inactive_product_id=hit.matched_product_id,
                match_confidence=hit.confidence,
                snippet=hit.snippet,
                status="flagged",
            )
            session.add(orphan)
            existing_keys.add(key)
            new_flags += 1

    session.flush()
    log.info("orphan scan complete", new_flags=new_flags)
    return new_flags


def run_full_audit(
    session: Session,
    since: str | None = None,
) -> dict[str, Any]:
    """Full audit: content sync + orphan scan."""
    wp = WordPressClient()
    wc = WooCommerceClient()
    try:
        counts = run_content_sync(session, wp, wc, since=since)
        orphan_count = run_orphan_scan(session, wc)
        session.commit()
        return {**counts, "orphan_flags": orphan_count}
    finally:
        wp.close()
        wc.close()


def get_audit_report(session: Session) -> dict[str, Any]:
    """Generate audit summary stats."""
    from sqlalchemy import func as sqlfunc

    total_posts = session.execute(
        select(sqlfunc.count()).where(ContentInventory.post_type == "post")
    ).scalar() or 0
    total_pages = session.execute(
        select(sqlfunc.count()).where(ContentInventory.post_type == "page")
    ).scalar() or 0
    total_products = session.execute(
        select(sqlfunc.count()).where(ContentInventory.post_type == "product")
    ).scalar() or 0
    avg_words = session.execute(
        select(sqlfunc.avg(ContentInventory.word_count))
    ).scalar() or 0
    missing_keyword = session.execute(
        select(sqlfunc.count()).where(
            ContentInventory.target_keyword.is_(None),
            ContentInventory.post_type != "product",
        )
    ).scalar() or 0

    # Duplicate slugs
    from sqlalchemy import literal_column
    dup_slugs = session.execute(
        select(ContentInventory.slug, sqlfunc.count().label("cnt"))
        .group_by(ContentInventory.slug)
        .having(literal_column("cnt") > 1)
    ).all()

    # Orphan stats
    total_orphans = session.execute(
        select(sqlfunc.count()).select_from(OrphanReference)
        .where(OrphanReference.status == "flagged")
    ).scalar() or 0

    orphan_by_type = dict(
        session.execute(
            select(OrphanReference.reference_type, sqlfunc.count())
            .where(OrphanReference.status == "flagged")
            .group_by(OrphanReference.reference_type)
        ).all()
    )

    # Category clusters
    category_counts = session.execute(
        select(ContentInventory.categories, sqlfunc.count())
        .where(ContentInventory.post_type == "post")
        .group_by(ContentInventory.categories)
    ).all()

    return {
        "total_posts": total_posts,
        "total_pages": total_pages,
        "total_products": total_products,
        "avg_word_count": round(float(avg_words), 1),
        "missing_target_keyword": missing_keyword,
        "duplicate_slugs": [(s, c) for s, c in dup_slugs],
        "orphan_flags_total": total_orphans,
        "orphan_flags_by_type": orphan_by_type,
        "category_clusters": len(category_counts),
    }
