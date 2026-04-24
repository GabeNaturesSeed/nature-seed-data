"""Shared helpers used across audit stages — content/product upsert."""

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import ContentInventory
from naturesseed_pipeline.integrations.wordpress import html_to_text


def _infer_target_keyword(title: str, html: str | None) -> str | None:
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


def upsert_content(session: Session, item: dict[str, Any], post_type: str) -> ContentInventory:
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
        row = ContentInventory(wp_post_id=wp_id); session.add(row)

    row.url = item.get("link", "")
    row.title = title
    row.slug = item.get("slug", "")
    row.content_html = raw_html
    row.content_text = plain_text
    row.excerpt = html_to_text(excerpt_html) if excerpt_html else None
    row.post_type = post_type
    row.status = item.get("status", "publish")
    cats = item.get("categories", [])
    row.categories = cats if isinstance(cats, list) else []
    tags = item.get("tags", [])
    row.tags = tags if isinstance(tags, list) else []
    row.word_count = len(plain_text.split()) if plain_text else 0
    row.published_at = _parse_wp_datetime(item.get("date_gmt"))
    row.modified_at = _parse_wp_datetime(item.get("modified_gmt"))
    row.target_keyword = _infer_target_keyword(title, raw_html)
    row.last_audited_at = now
    return row


def upsert_product(session: Session, item: dict[str, Any]) -> ContentInventory:
    wp_id = item["id"]
    row = session.execute(
        select(ContentInventory).where(ContentInventory.wp_post_id == wp_id)
    ).scalar_one_or_none()

    raw_html = item.get("description", "")
    plain_text = html_to_text(raw_html)
    title = item.get("name", "")
    now = datetime.now(timezone.utc)

    if row is None:
        row = ContentInventory(wp_post_id=wp_id); session.add(row)

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
