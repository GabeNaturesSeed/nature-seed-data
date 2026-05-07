import sqlite3
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup


def strip_html(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


def parse_post(raw: dict) -> dict:
    return {
        "post_id": raw["id"],
        "title": BeautifulSoup(raw["title"]["rendered"], "html.parser").get_text(),
        "url": raw["link"],
        "content_html": raw["content"]["rendered"],
    }


def fetch_all_posts(env: dict, db_path: Optional[Path] = None) -> list[dict]:
    """Load all post-type articles from content_inventory DB.

    WP REST API only exposes published posts (12 live). The DB already has
    content_html for all 312 posts including drafts, so we read from there.
    """
    if db_path is None:
        db_path = Path(env.get("DB_PATH", "")).expanduser()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id AS post_id, wp_post_id, url, title, content_html "
        "FROM content_inventory "
        "WHERE post_type = 'post' AND content_html IS NOT NULL AND content_html != '' "
        "ORDER BY id"
    ).fetchall()
    conn.close()
    return [
        {
            "post_id": r["wp_post_id"] or r["post_id"],
            "title": r["title"] or "",
            "url": r["url"] or "",
            "content_html": r["content_html"] or "",
        }
        for r in rows
    ]
