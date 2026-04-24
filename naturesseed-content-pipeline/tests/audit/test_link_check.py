"""Tests for HTTP status checker — uses httpx MockTransport."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Base, ContentInventory, OutboundLink
from naturesseed_pipeline.pipelines.audit.link_check import (
    check_links_http, needs_recheck,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_needs_recheck_never_checked():
    assert needs_recheck(None, cache_days=30) is True


def test_needs_recheck_recent_false():
    recent = datetime.now(timezone.utc) - timedelta(days=1)
    assert needs_recheck(recent, cache_days=30) is False


def test_needs_recheck_old_true():
    old = datetime.now(timezone.utc) - timedelta(days=45)
    assert needs_recheck(old, cache_days=30) is True


def test_check_links_updates_http_status(monkeypatch):
    s = _session()
    content = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(content); s.flush()
    s.add(OutboundLink(content_inventory_id=content.id, href="https://ok.com",
                       anchor_text="", link_type="external"))
    s.add(OutboundLink(content_inventory_id=content.id, href="https://notfound.com",
                       anchor_text="", link_type="external"))
    s.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        if "notfound" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    updated = check_links_http(s, cache_days=30, concurrency=2,
                                client=httpx.Client(transport=transport))
    s.commit()

    links = s.execute(select(OutboundLink).order_by(OutboundLink.href)).scalars().all()
    statuses = {l.href: l.http_status for l in links}
    assert statuses["https://ok.com"] == 200
    assert statuses["https://notfound.com"] == 404
    assert updated == 2


def test_check_links_skips_cached(monkeypatch):
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OutboundLink(content_inventory_id=c.id, href="https://ok.com",
                       anchor_text="", link_type="external",
                       http_status=200,
                       last_checked_at=datetime.now(timezone.utc) - timedelta(days=2)))
    s.commit()

    def handler(_):
        raise AssertionError("should not be called when cached")

    updated = check_links_http(s, cache_days=30, concurrency=1,
                                client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert updated == 0
