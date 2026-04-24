"""Tests for the content audit pipeline: API clients, upsert, orphan detection."""

import httpx
import pytest
import respx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from naturesseed_pipeline.db.models import (
    Base,
    ContentInventory,
)
from naturesseed_pipeline.integrations.wordpress import (
    WordPressClient,
    html_to_text,
)
from naturesseed_pipeline.pipelines.audit._shared import upsert_content
from naturesseed_pipeline.pipelines.orphans import (
    build_product_index,
    scan_content,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def db_session():
    """In-memory SQLite session for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_wp_post(
    post_id: int = 1,
    title: str = "Test Post",
    slug: str = "test-post",
    content: str = "<p>Hello world</p>",
    status: str = "publish",
    post_type: str = "post",
) -> dict:
    return {
        "id": post_id,
        "title": {"rendered": title},
        "slug": slug,
        "content": {"rendered": content},
        "excerpt": {"rendered": "<p>Excerpt</p>"},
        "link": f"https://naturesseed.com/{slug}/",
        "status": status,
        "date_gmt": "2025-01-15T10:00:00",
        "modified_gmt": "2025-03-01T12:00:00",
        "categories": [5, 10],
        "tags": [3],
    }


def _make_wc_product(
    pid: int = 100,
    name: str = "Kentucky Bluegrass Seed",
    slug: str = "kentucky-bluegrass-seed",
    sku: str = "KBG-5LB",
    status: str = "publish",
    description: str = "<p>Premium KBG blend</p>",
) -> dict:
    return {
        "id": pid,
        "name": name,
        "slug": slug,
        "sku": sku,
        "status": status,
        "description": description,
        "short_description": "<p>Short desc</p>",
        "permalink": f"https://naturesseed.com/products/{slug}/",
        "date_created_gmt": "2024-06-01T08:00:00",
        "date_modified_gmt": "2025-02-15T14:00:00",
        "categories": [{"id": 20}],
        "tags": [{"id": 30}],
    }


# ── HTML to text ──────────────────────────────────────────────────────────────

def test_html_to_text():
    assert html_to_text("<p>Hello <b>world</b></p>") == "Hello world"
    assert html_to_text("") == ""
    assert html_to_text("<h1>Title</h1><p>Body</p>") == "Title Body"


# ── Client pagination ─────────────────────────────────────────────────────────

@respx.mock
def test_wp_client_pagination():
    """Test pagination via X-WP-TotalPages header."""
    base = "https://example.com/wp-json/wp/v2"
    page1 = [_make_wp_post(1, "Post 1"), _make_wp_post(2, "Post 2")]
    page2 = [_make_wp_post(3, "Post 3")]

    respx.get(f"{base}/posts").mock(side_effect=[
        httpx.Response(
            200,
            json=page1,
            headers={"X-WP-TotalPages": "2"},
        ),
        httpx.Response(
            200,
            json=page2,
            headers={"X-WP-TotalPages": "2"},
        ),
    ])

    client = WordPressClient(base_url=base, username="u", app_password="p")
    posts = client.list_posts()
    assert len(posts) == 3
    assert posts[0]["id"] == 1
    assert posts[2]["id"] == 3
    client.close()


# ── Rate limit retry ─────────────────────────────────────────────────────────

@respx.mock
def test_wp_client_retry_on_429():
    """Client should retry on 429 and eventually succeed."""
    base = "https://example.com/wp-json/wp/v2"
    respx.get(f"{base}/posts").mock(side_effect=[
        httpx.Response(429),
        httpx.Response(200, json=[_make_wp_post(1)], headers={"X-WP-TotalPages": "1"}),
    ])

    client = WordPressClient(base_url=base, username="u", app_password="p")
    posts = client.list_posts()
    assert len(posts) == 1
    client.close()


@respx.mock
def test_wp_client_retry_on_500():
    """Client should retry on 500."""
    base = "https://example.com/wp-json/wp/v2"
    respx.get(f"{base}/posts").mock(side_effect=[
        httpx.Response(500),
        httpx.Response(200, json=[_make_wp_post(1)], headers={"X-WP-TotalPages": "1"}),
    ])

    client = WordPressClient(base_url=base, username="u", app_password="p")
    posts = client.list_posts()
    assert len(posts) == 1
    client.close()


# ── Upsert idempotency ───────────────────────────────────────────────────────

def test_upsert_creates_then_updates(db_session: Session):
    """Upserting same wp_post_id twice should not create duplicates."""
    item = _make_wp_post(42, "Original Title")
    upsert_content(db_session, item, "post")
    db_session.flush()

    count = db_session.execute(
        select(ContentInventory).where(ContentInventory.wp_post_id == 42)
    ).scalars().all()
    assert len(count) == 1
    assert count[0].title == "Original Title"

    # Update
    item["title"]["rendered"] = "Updated Title"
    upsert_content(db_session, item, "post")
    db_session.flush()

    count = db_session.execute(
        select(ContentInventory).where(ContentInventory.wp_post_id == 42)
    ).scalars().all()
    assert len(count) == 1
    assert count[0].title == "Updated Title"


# ── Product index ─────────────────────────────────────────────────────────────

def test_build_product_index():
    products = [
        _make_wc_product(100, "Kentucky Bluegrass Seed", "kbg-seed", "KBG-5LB"),
        _make_wc_product(200, "Bermuda Grass Seed", "bermuda-seed", "BER-10LB"),
    ]
    idx = build_product_index(products)
    assert 100 in idx.by_id
    assert "kbg-seed" in idx.by_slug
    assert "KBG-5LB" in idx.by_sku
    assert "kentucky bluegrass seed" in idx.by_name_lower


# ── Orphan detection: URL ─────────────────────────────────────────────────────

def test_orphan_url_detection():
    active = build_product_index([
        _make_wc_product(100, "Active Product", "active-prod"),
    ])
    inactive = build_product_index([
        _make_wc_product(200, "Discontinued Mix", "old-mix", status="draft"),
    ])
    html = '<a href="/products/old-mix/">Buy Old Mix</a> and <a href="/products/active-prod/">Active</a>'
    text = "Check /products/old-mix/ and /products/active-prod/"

    hits = scan_content(text, html, active, inactive)
    url_hits = [h for h in hits if h.reference_type == "url"]
    # old-mix should be flagged (appears in both html and text)
    assert any(h.reference_value.strip("/").endswith("old-mix") for h in url_hits)
    # active-prod should NOT be flagged
    assert not any("active-prod" in h.reference_value for h in url_hits)


# ── Orphan detection: shortcode ───────────────────────────────────────────────

def test_orphan_shortcode_detection():
    active = build_product_index([_make_wc_product(100)])
    inactive = build_product_index([_make_wc_product(200, status="draft")])

    html = '[product id="200"] and [products ids="100,200"] and [add_to_cart id="999"]'
    hits = scan_content("", html, active, inactive)
    sc_hits = [h for h in hits if h.reference_type == "shortcode"]
    # ID 200 appears twice (product and products shortcodes), ID 999 once
    flagged_ids = set()
    for h in sc_hits:
        if "200" in h.reference_value:
            flagged_ids.add(200)
        if "999" in h.reference_value:
            flagged_ids.add(999)
    assert 200 in flagged_ids
    assert 999 in flagged_ids


# ── Orphan detection: SKU ─────────────────────────────────────────────────────

def test_orphan_sku_detection():
    active = build_product_index([])
    inactive = build_product_index([
        _make_wc_product(200, sku="DISC-MIX-5LB", status="trash"),
    ])

    text = "The product DISC-MIX-5LB is no longer available."
    hits = scan_content(text, "", active, inactive)
    sku_hits = [h for h in hits if h.reference_type == "sku"]
    assert len(sku_hits) == 1
    assert sku_hits[0].matched_product_id == 200


def test_sku_no_false_positive_on_short():
    """SKUs shorter than 3 chars should be skipped."""
    inactive = build_product_index([
        _make_wc_product(200, sku="AB", status="draft"),
    ])
    text = "AB testing is important"
    hits = scan_content(text, "", build_product_index([]), inactive)
    assert len([h for h in hits if h.reference_type == "sku"]) == 0


# ── Orphan detection: fuzzy name ──────────────────────────────────────────────

def test_orphan_fuzzy_name_detection():
    inactive = build_product_index([
        _make_wc_product(300, name="Bermuda Grass Seed Premium Blend", status="draft"),
    ])
    active = build_product_index([])

    text = "We used to carry the Bermuda Grass Seed Premium Blend but it is discontinued."
    hits = scan_content(text, "", active, inactive)
    name_hits = [h for h in hits if h.reference_type == "name"]
    assert len(name_hits) >= 1
    assert name_hits[0].matched_product_id == 300
    assert name_hits[0].confidence >= 0.9


def test_fuzzy_no_match_below_threshold():
    """Unrelated text should not fuzzy-match product names."""
    inactive = build_product_index([
        _make_wc_product(300, name="Kentucky Bluegrass Premium Blend", status="draft"),
    ])
    text = "The weather forecast calls for rain tomorrow in Kentucky."
    hits = scan_content(text, "", build_product_index([]), inactive)
    name_hits = [h for h in hits if h.reference_type == "name"]
    assert len(name_hits) == 0


def test_fuzzy_skips_stopword_only_names():
    """Names consisting only of stopwords should be skipped."""
    inactive = build_product_index([
        _make_wc_product(400, name="Seed Mix", status="draft"),
    ])
    text = "Our seed mix is the best available anywhere."
    hits = scan_content(text, "", build_product_index([]), inactive)
    name_hits = [h for h in hits if h.reference_type == "name"]
    assert len(name_hits) == 0


def test_fuzzy_skips_short_names():
    """Names shorter than 4 chars should be skipped."""
    inactive = build_product_index([
        _make_wc_product(500, name="Rye", status="draft"),
    ])
    text = "Rye is commonly used in winter overseeding."
    hits = scan_content(text, "", build_product_index([]), inactive)
    name_hits = [h for h in hits if h.reference_type == "name"]
    assert len(name_hits) == 0


