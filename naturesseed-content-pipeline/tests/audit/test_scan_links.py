"""Integration test for scan-links stage — DB round-trip with mocked HTTP."""

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Base, ContentInventory, OutboundLink
from naturesseed_pipeline.pipelines.audit.scan_links import run_scan_links


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_run_scan_links_extracts_classifies_and_targets():
    s = _session()
    src = ContentInventory(url="https://naturesseed.com/resources/a/",
                           title="A", slug="a", post_type="post",
                           content_html='<a href="/resources/b/">B</a> '
                                        '<a href="/products/foo/">Foo</a> '
                                        '<a href="https://ext.com">Ext</a>')
    tgt = ContentInventory(url="https://naturesseed.com/resources/b/",
                           title="B", slug="b", post_type="post",
                           content_html="")
    s.add_all([src, tgt]); s.commit()

    def handler(_): return httpx.Response(200)
    client = httpx.Client(transport=httpx.MockTransport(handler))

    run_scan_links(s, site_host="naturesseed.com", cache_days=30, client=client,
                   skip_http=False)
    s.commit()

    links = s.execute(select(OutboundLink).order_by(OutboundLink.href)).scalars().all()
    by_type = {l.href: l.link_type for l in links}
    assert by_type["https://ext.com"] == "external"
    assert by_type["/products/foo/"] == "internal_product"

    internal = [l for l in links if l.href == "/resources/b/"]
    assert internal and internal[0].target_content_id == tgt.id


def test_run_scan_links_skip_http_leaves_status_null():
    s = _session()
    src = ContentInventory(url="https://naturesseed.com/a/", title="A", slug="a",
                           post_type="post",
                           content_html='<a href="https://ext.com">Ext</a>')
    s.add(src); s.commit()

    run_scan_links(s, site_host="naturesseed.com", cache_days=30,
                   client=None, skip_http=True)
    s.commit()

    link = s.execute(select(OutboundLink)).scalar_one()
    assert link.http_status is None


def test_run_scan_links_idempotent():
    s = _session()
    src = ContentInventory(url="https://naturesseed.com/a/", title="A", slug="a",
                           post_type="post",
                           content_html='<a href="https://ext.com">Ext</a>')
    s.add(src); s.commit()

    run_scan_links(s, site_host="naturesseed.com", cache_days=30,
                   client=None, skip_http=True)
    s.commit()
    run_scan_links(s, site_host="naturesseed.com", cache_days=30,
                   client=None, skip_http=True)
    s.commit()

    links = s.execute(select(OutboundLink)).scalars().all()
    assert len(links) == 1
