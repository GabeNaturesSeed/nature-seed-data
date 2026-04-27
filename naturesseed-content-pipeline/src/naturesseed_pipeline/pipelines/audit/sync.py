"""Audit sync stage — pulls content from WP + WC into content_inventory
and wc_catalog_snapshot. Idempotent on wp_post_id and wp_product_id."""

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import WcCatalogSnapshot
from naturesseed_pipeline.integrations.wordpress import (
    WooCommerceClient, WordPressClient,
)
from naturesseed_pipeline.pipelines.audit._shared import upsert_content, upsert_product

log = structlog.get_logger()


def extract_species_from_product(product: dict[str, Any]) -> list[str]:
    """Species list from ACF meta_data.species_list, else from Species attribute."""
    for m in product.get("meta_data") or []:
        if m.get("key") == "species_list" and isinstance(m.get("value"), list):
            return [str(v) for v in m["value"]]
    for attr in product.get("attributes") or []:
        if str(attr.get("name", "")).strip().lower() == "species":
            opts = attr.get("options") or []
            if isinstance(opts, list):
                return [str(o) for o in opts]
    return []


def _parse_price(raw: Any) -> float | None:
    if raw in (None, "", 0, "0"):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def upsert_wc_snapshot(session: Session, product: dict[str, Any]) -> WcCatalogSnapshot | None:
    pid = int(product["id"])
    slug = product.get("slug") or ""
    if not slug:
        # WP returns drafts/auto-drafts without a slug; the slug column is UNIQUE
        # so we'd collide on empty-string. Fall back to a synthetic slug keyed
        # on the product ID so each row is still unique.
        slug = f"_draft-{pid}"
    row = session.get(WcCatalogSnapshot, pid)
    if row is None:
        row = WcCatalogSnapshot(wp_product_id=pid)
        session.add(row)
    row.slug = slug
    row.name = product.get("name", "")
    row.status = product.get("status", "publish")
    row.species_list = extract_species_from_product(product)
    row.price = _parse_price(product.get("price"))
    row.permalink = product.get("permalink", "")
    row.last_synced_at = datetime.now(timezone.utc)
    return row


def run_sync(
    session: Session,
    wp: WordPressClient | None = None,
    wc: WooCommerceClient | None = None,
    since: str | None = None,
) -> dict[str, int]:
    """Pull posts + pages + products. Populates content_inventory and
    wc_catalog_snapshot. Idempotent. Returns counts."""
    created_clients = False
    if wp is None:
        wp = WordPressClient(); created_clients = True
    if wc is None:
        wc = WooCommerceClient()

    counts = {"posts": 0, "pages": 0, "products": 0, "snapshots": 0}
    try:
        log.info("audit.sync.posts")
        for item in wp.list_posts(since=since):
            upsert_content(session, item, "post")
            counts["posts"] += 1
        session.flush()

        log.info("audit.sync.pages")
        for item in wp.list_pages(since=since):
            upsert_content(session, item, "page")
            counts["pages"] += 1
        session.flush()

        log.info("audit.sync.products")
        for item in wc.list_all_products():
            upsert_product(session, item)
            upsert_wc_snapshot(session, item)
            counts["products"] += 1
            counts["snapshots"] += 1
        session.flush()
    finally:
        if created_clients:
            wp.close(); wc.close()

    log.info("audit.sync.done", **counts)
    return counts
