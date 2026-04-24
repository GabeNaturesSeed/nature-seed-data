"""Scan-links stage: extract outbound links per article, HTTP-check them."""

from urllib.parse import urlparse

import httpx
import structlog
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import ContentInventory, OutboundLink
from naturesseed_pipeline.pipelines.audit.link_check import check_links_http
from naturesseed_pipeline.pipelines.audit.link_extract import extract_links

log = structlog.get_logger()


def _build_url_to_content_id(session: Session) -> dict[str, int]:
    """Map canonical internal URLs to content_inventory IDs for target resolution."""
    rows = session.execute(select(ContentInventory.id, ContentInventory.url)).all()
    mapping: dict[str, int] = {}
    for cid, url in rows:
        if not url:
            continue
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        mapping[path] = cid
    return mapping


def _resolve_target(href: str, url_to_id: dict[str, int]) -> int | None:
    parsed = urlparse(href)
    path = (parsed.path or "").rstrip("/") or "/"
    return url_to_id.get(path)


def run_scan_links(
    session: Session,
    site_host: str,
    cache_days: int,
    client: httpx.Client | None = None,
    skip_http: bool = False,
) -> dict[str, int]:
    """Extract + classify + store + HTTP-check outbound links for every article."""
    url_to_id = _build_url_to_content_id(session)
    rows = session.execute(select(ContentInventory)).scalars().all()

    counts = {"articles": 0, "links_upserted": 0, "http_updated": 0}

    for row in rows:
        extracted = extract_links(row.content_html or "", site_host)
        counts["articles"] += 1

        # Clear prior rows then insert fresh — guarantees idempotency
        session.execute(
            delete(OutboundLink).where(OutboundLink.content_inventory_id == row.id)
        )
        for link in extracted:
            target_id = (_resolve_target(link.href, url_to_id)
                         if link.link_type.startswith("internal_") else None)
            session.add(OutboundLink(
                content_inventory_id=row.id,
                href=link.href,
                anchor_text=link.anchor_text,
                link_type=link.link_type,
                target_content_id=target_id,
            ))
            counts["links_upserted"] += 1
        session.flush()

    if not skip_http:
        counts["http_updated"] = check_links_http(
            session, cache_days=cache_days,
            concurrency=1, client=client,
        )
    log.info("audit.scan_links.done", **counts)
    return counts
