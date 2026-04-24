"""HTTP status checker for outbound_links with 30-day result cache."""

from datetime import datetime, timedelta, timezone

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import OutboundLink

log = structlog.get_logger()


def needs_recheck(last_checked_at: datetime | None, cache_days: int) -> bool:
    if last_checked_at is None:
        return True
    if last_checked_at.tzinfo is None:
        last_checked_at = last_checked_at.replace(tzinfo=timezone.utc)
    return last_checked_at < datetime.now(timezone.utc) - timedelta(days=cache_days)


def _check_one(client: httpx.Client, href: str) -> int | None:
    try:
        resp = client.head(href, follow_redirects=True, timeout=10.0)
        if resp.status_code >= 400:
            resp = client.get(href, follow_redirects=True, timeout=10.0)
        return resp.status_code
    except httpx.RequestError as e:
        log.warning("link_check.error", href=href, error=str(e))
        return 0  # 0 signals unreachable


def check_links_http(
    session: Session,
    cache_days: int,
    concurrency: int,
    client: httpx.Client | None = None,
) -> int:
    """Check HTTP status for all outbound links that need rechecking.
    Returns the number of links updated.

    The concurrency arg is reserved for a future threading impl; current
    implementation is sequential to keep tests stable."""
    close_client = False
    if client is None:
        client = httpx.Client(); close_client = True

    try:
        links = session.execute(select(OutboundLink).where(
            OutboundLink.link_type != "anchor"
        )).scalars().all()

        to_check: dict[str, list[OutboundLink]] = {}
        for link in links:
            if needs_recheck(link.last_checked_at, cache_days):
                to_check.setdefault(link.href, []).append(link)

        now = datetime.now(timezone.utc)
        updated = 0
        for href, rows in to_check.items():
            status = _check_one(client, href)
            for row in rows:
                row.http_status = status
                row.last_checked_at = now
                updated += 1

        return updated
    finally:
        if close_client:
            client.close()
