# SEO Content Audit & Topic Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a six-stage idempotent audit pipeline inside `naturesseed-content-pipeline/` that inventories editorial content, classifies topic/subtopic against WC categories, tags products (active + discontinued), extracts outbound links, and runs a pluggable decay-rule engine — producing DB state + committed markdown/CSV reports.

**Architecture:** Extend the existing `naturesseed_pipeline` package. Add six new SQLAlchemy models + one Alembic migration. Split existing `pipelines/audit.py` into a `pipelines/audit/` package of discrete stages. Add a new `audit_rules/` directory of pluggable rule classes discovered at runtime. All stages are idempotent and share the existing SQLite DB.

**Tech Stack:** Python 3.11, SQLAlchemy 2.x (existing), Alembic (existing), Typer (existing CLI), pytest (existing test harness), BeautifulSoup (existing), httpx (existing), rapidfuzz (existing), anthropic SDK (existing).

**Spec reference:** `docs/superpowers/specs/2026-04-24-seo-content-audit-design.md`

**Working directory for all bash commands:** `/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/naturesseed-content-pipeline/`

---

## File Structure

**New files:**
- `alembic/versions/<hash>_add_audit_tables.py` — migration
- `src/naturesseed_pipeline/pipelines/audit/__init__.py` — package marker
- `src/naturesseed_pipeline/pipelines/audit/sync.py` — Stage 1
- `src/naturesseed_pipeline/pipelines/audit/classify.py` — Stage 2
- `src/naturesseed_pipeline/pipelines/audit/tag_products.py` — Stage 3
- `src/naturesseed_pipeline/pipelines/audit/scan_links.py` — Stage 4
- `src/naturesseed_pipeline/pipelines/audit/scan_decay.py` — Stage 5
- `src/naturesseed_pipeline/pipelines/audit/report.py` — Stage 6
- `src/naturesseed_pipeline/audit_rules/__init__.py` — registry + discovery
- `src/naturesseed_pipeline/audit_rules/base.py` — `DecayRule` protocol + `AuditContext`
- `src/naturesseed_pipeline/audit_rules/<rule_name>.py` — one per rule (12 files)
- `tests/audit/` — one test module per stage + `test_<rule_name>.py` per rule

**Files to modify:**
- `src/naturesseed_pipeline/db/models.py` — add 6 models
- `src/naturesseed_pipeline/config.py` — add audit-scoped settings
- `src/naturesseed_pipeline/cli.py` — wire 6 new `audit` subcommands, retire old `audit run`/`audit report`

**Files preserved as-is (reused):**
- `src/naturesseed_pipeline/pipelines/orphans.py` — `ProductIndex`, `build_product_index`, `scan_content` stay; `tag-products` stage calls into them.
- `src/naturesseed_pipeline/integrations/wordpress.py` — no changes needed.
- `src/naturesseed_pipeline/pipelines/refresh.py` — `scan_and_queue` keeps working; `scan-decay` populates `refresh_queue` directly from `decay_findings`.

---

## Task 1: DB Models — Add Six New Tables

**Files:**
- Modify: `src/naturesseed_pipeline/db/models.py`
- Test: `tests/audit/test_models.py` (create)

- [ ] **Step 1: Create `tests/audit/__init__.py`**

```bash
mkdir -p tests/audit && touch tests/audit/__init__.py
```

- [ ] **Step 2: Write failing test for new models**

Create `tests/audit/test_models.py`:

```python
"""Verify the 6 new audit tables can be created and related."""

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    Base, ContentInventory,
    Topic, ContentTopic, ContentProductMention,
    OutboundLink, DecayFinding, WcCatalogSnapshot,
)


def _make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_topic_self_reference_parent_child():
    s = _make_session()
    parent = Topic(name="Grass Seed", slug="grass-seed", wc_category_slug="grass-seed",
                   source="wc_category", approved=1)
    s.add(parent); s.flush()
    child = Topic(name="Cool-Season", slug="cool-season", source="llm_proposed",
                  approved=0, parent_topic_id=parent.id)
    s.add(child); s.commit()
    assert child.parent_topic_id == parent.id


def test_content_topic_unique():
    s = _make_session()
    content = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    topic = Topic(name="T", slug="t", source="user_created", approved=1)
    s.add_all([content, topic]); s.flush()
    s.add(ContentTopic(content_inventory_id=content.id, topic_id=topic.id,
                       assigned_by="auto", confidence=0.9))
    s.commit()
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        s.add(ContentTopic(content_inventory_id=content.id, topic_id=topic.id,
                           assigned_by="auto", confidence=0.5))
        s.commit()


def test_content_product_mention_unique():
    s = _make_session()
    content = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(content); s.flush()
    s.add(ContentProductMention(content_inventory_id=content.id, wp_product_id=42,
                                product_slug="x", product_name="X", match_type="exact",
                                confidence=0.95))
    s.commit()
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        s.add(ContentProductMention(content_inventory_id=content.id, wp_product_id=42,
                                    product_slug="x", product_name="X", match_type="fuzzy",
                                    confidence=0.85))
        s.commit()


def test_outbound_link_fields():
    s = _make_session()
    src = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    tgt = ContentInventory(url="https://x/b", title="B", slug="b", post_type="post")
    s.add_all([src, tgt]); s.flush()
    link = OutboundLink(content_inventory_id=src.id, href="https://x/b",
                        anchor_text="B", link_type="internal_content",
                        target_content_id=tgt.id, http_status=200,
                        last_checked_at=datetime.now(timezone.utc))
    s.add(link); s.commit()
    assert link.target_content_id == tgt.id


def test_decay_finding_status_default():
    s = _make_session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    f = DecayFinding(content_inventory_id=c.id, rule_name="ThinContentRule",
                    severity="info", snippet="...", suggested_action="expand")
    s.add(f); s.commit()
    assert f.status == "open"


def test_wc_catalog_snapshot_keys_by_product_id():
    s = _make_session()
    s.add(WcCatalogSnapshot(wp_product_id=99, slug="zzz", name="Zzz",
                            status="publish", species_list=["alfalfa"], price=9.99,
                            permalink="https://x/products/zzz/"))
    s.commit()
    row = s.get(WcCatalogSnapshot, 99)
    assert row.status == "publish"
    assert row.species_list == ["alfalfa"]
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/audit/test_models.py -v
```

Expected: `ImportError: cannot import name 'Topic'` (or similar) — all six new models don't exist yet.

- [ ] **Step 4: Add the six models to `src/naturesseed_pipeline/db/models.py`**

Append to the end of the file, before any module-level trailing whitespace:

```python
class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    wc_category_slug: Mapped[str | None] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    approved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ContentTopic(Base):
    __tablename__ = "content_topics"
    __table_args__ = (
        UniqueConstraint("content_inventory_id", "topic_id", name="uq_content_topic"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_inventory_id: Mapped[int] = mapped_column(
        ForeignKey("content_inventory.id"), nullable=False
    )
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    assigned_by: Mapped[str] = mapped_column(String(20), nullable=False)


class ContentProductMention(Base):
    __tablename__ = "content_product_mentions"
    __table_args__ = (
        UniqueConstraint("content_inventory_id", "wp_product_id",
                         name="uq_content_product_mention"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_inventory_id: Mapped[int] = mapped_column(
        ForeignKey("content_inventory.id"), nullable=False
    )
    wp_product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_slug: Mapped[str] = mapped_column(String(300), nullable=False)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_snippet: Mapped[str | None] = mapped_column(Text)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class OutboundLink(Base):
    __tablename__ = "outbound_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_inventory_id: Mapped[int] = mapped_column(
        ForeignKey("content_inventory.id"), nullable=False, index=True
    )
    href: Mapped[str] = mapped_column(String(2000), nullable=False)
    anchor_text: Mapped[str | None] = mapped_column(String(500))
    link_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_content_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_inventory.id"), index=True
    )
    http_status: Mapped[int | None] = mapped_column(Integer)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)


class DecayFinding(Base):
    __tablename__ = "decay_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_inventory_id: Mapped[int] = mapped_column(
        ForeignKey("content_inventory.id"), nullable=False, index=True
    )
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    snippet: Mapped[str | None] = mapped_column(Text)
    suggested_action: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)


class WcCatalogSnapshot(Base):
    __tablename__ = "wc_catalog_snapshot"

    wp_product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    species_list: Mapped[list | None] = mapped_column(JSON)
    price: Mapped[float | None] = mapped_column(Float)
    permalink: Mapped[str | None] = mapped_column(String(500))
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 5: Run test to verify pass**

```bash
pytest tests/audit/test_models.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/db/models.py \
        naturesseed-content-pipeline/tests/audit/__init__.py \
        naturesseed-content-pipeline/tests/audit/test_models.py
git commit -m "feat(audit): add 6 new models for content audit pipeline"
```

---

## Task 2: Alembic Migration for New Tables

**Files:**
- Create: `alembic/versions/<auto_hash>_add_audit_tables.py`

- [ ] **Step 1: Generate migration**

```bash
cd naturesseed-content-pipeline && uv run alembic revision --autogenerate -m "add audit tables"
```

Expected: new file in `alembic/versions/`.

- [ ] **Step 2: Inspect the generated migration**

Read the file. Confirm it contains `op.create_table('topics', ...)`, `op.create_table('content_topics', ...)`, `op.create_table('content_product_mentions', ...)`, `op.create_table('outbound_links', ...)`, `op.create_table('decay_findings', ...)`, `op.create_table('wc_catalog_snapshot', ...)` and no other changes (no `drop_table`, no `alter_column` on existing tables). If extraneous operations were generated, hand-edit the file to remove them.

- [ ] **Step 3: Apply migration against a throwaway DB**

```bash
cd naturesseed-content-pipeline && DATABASE_URL="sqlite:///test_migration.db" uv run alembic upgrade head
```

Expected: migration runs without error.

- [ ] **Step 4: Verify tables exist**

```bash
cd naturesseed-content-pipeline && sqlite3 test_migration.db ".tables" | tr ' ' '\n' | sort | grep -E 'topic|outbound|decay|wc_catalog|product_mention' | wc -l
```

Expected: `6`

- [ ] **Step 5: Clean up and commit**

```bash
rm naturesseed-content-pipeline/test_migration.db
git add naturesseed-content-pipeline/alembic/versions/
git commit -m "feat(audit): alembic migration for audit tables"
```

---

## Task 3: Config Additions

**Files:**
- Modify: `src/naturesseed_pipeline/config.py`
- Test: `tests/audit/test_config.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_config.py`:

```python
"""Verify audit-scoped config settings are readable and have sensible defaults."""

from naturesseed_pipeline.config import Settings


def test_audit_defaults_present():
    s = Settings()
    assert s.audit_llm_model == "claude-sonnet-4-6"
    assert s.audit_http_check_concurrency == 5
    assert s.audit_http_check_cache_days == 30
    assert 0.0 < s.audit_fuzzy_match_threshold <= 1.0
    assert s.audit_thin_word_count == 300
    assert isinstance(s.audit_current_shipping, str)


def test_audit_shipping_overridable_via_env(monkeypatch):
    monkeypatch.setenv("AUDIT_CURRENT_SHIPPING", "Free shipping over $99")
    s = Settings()
    assert "Free shipping over $99" in s.audit_current_shipping
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_config.py -v
```

Expected: `AttributeError: 'Settings' object has no attribute 'audit_llm_model'`.

- [ ] **Step 3: Add settings to `src/naturesseed_pipeline/config.py`**

Insert after the existing `anthropic_api_key: str = ""` line:

```python
    # Audit pipeline settings
    audit_llm_model: str = "claude-sonnet-4-6"
    audit_http_check_concurrency: int = 5
    audit_http_check_cache_days: int = 30
    audit_fuzzy_match_threshold: float = 0.85
    audit_thin_word_count: int = 300
    audit_current_shipping: str = "Free shipping on orders over $99 (lower 48 US states)"
    audit_llm_max_tokens_per_rule: int = 50_000
```

- [ ] **Step 4: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_config.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/config.py \
        naturesseed-content-pipeline/tests/audit/test_config.py
git commit -m "feat(audit): add audit-scoped config settings"
```

---

## Task 4: WC Catalog Snapshot Writer

**Files:**
- Create: `src/naturesseed_pipeline/pipelines/audit/__init__.py`
- Create: `src/naturesseed_pipeline/pipelines/audit/sync.py`
- Test: `tests/audit/test_sync.py` (create)

- [ ] **Step 1: Create package marker**

```bash
mkdir -p naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit
touch naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/__init__.py
```

- [ ] **Step 2: Write failing test**

Create `tests/audit/test_sync.py`:

```python
"""Sync stage tests — content_inventory upsert + wc_catalog_snapshot population."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Base, ContentInventory, WcCatalogSnapshot
from naturesseed_pipeline.pipelines.audit.sync import (
    upsert_wc_snapshot,
    extract_species_from_product,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_extract_species_from_meta_data_acf():
    product = {
        "meta_data": [
            {"key": "species_list", "value": ["alfalfa", "clover"]}
        ]
    }
    assert extract_species_from_product(product) == ["alfalfa", "clover"]


def test_extract_species_from_attribute_fallback():
    product = {
        "attributes": [
            {"name": "Species", "options": ["fescue", "ryegrass"]}
        ]
    }
    assert extract_species_from_product(product) == ["fescue", "ryegrass"]


def test_extract_species_none_when_absent():
    assert extract_species_from_product({"id": 1}) == []


def test_upsert_wc_snapshot_insert_then_update():
    s = _session()
    product = {
        "id": 42, "slug": "test-mix", "name": "Test Mix",
        "status": "publish", "permalink": "https://x/products/test-mix/",
        "price": "19.99",
        "meta_data": [{"key": "species_list", "value": ["alfalfa"]}],
    }
    upsert_wc_snapshot(s, product)
    s.flush()
    row = s.get(WcCatalogSnapshot, 42)
    assert row.status == "publish"
    assert row.price == 19.99

    product["status"] = "draft"
    product["price"] = "24.50"
    upsert_wc_snapshot(s, product)
    s.flush()
    row = s.get(WcCatalogSnapshot, 42)
    assert row.status == "draft"
    assert row.price == 24.50


def test_upsert_wc_snapshot_handles_empty_price():
    s = _session()
    upsert_wc_snapshot(s, {"id": 1, "slug": "x", "name": "X", "status": "publish",
                           "permalink": "", "price": ""})
    s.flush()
    assert s.get(WcCatalogSnapshot, 1).price is None
```

- [ ] **Step 3: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_sync.py -v
```

Expected: `ImportError: cannot import name 'upsert_wc_snapshot'`.

- [ ] **Step 4: Implement `sync.py` with snapshot helpers**

Create `src/naturesseed_pipeline/pipelines/audit/sync.py`:

```python
"""Audit sync stage — pulls content from WP + WC into content_inventory
and wc_catalog_snapshot. Idempotent on wp_post_id and wp_product_id."""

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import ContentInventory, WcCatalogSnapshot
from naturesseed_pipeline.integrations.wordpress import (
    WooCommerceClient, WordPressClient, html_to_text,
)

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


def upsert_wc_snapshot(session: Session, product: dict[str, Any]) -> WcCatalogSnapshot:
    pid = int(product["id"])
    row = session.get(WcCatalogSnapshot, pid)
    if row is None:
        row = WcCatalogSnapshot(wp_product_id=pid)
        session.add(row)
    row.slug = product.get("slug", "")
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
    from naturesseed_pipeline.pipelines.audit._shared import upsert_content, upsert_product

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
```

- [ ] **Step 5: Extract `upsert_content` / `upsert_product` into shared module**

Create `src/naturesseed_pipeline/pipelines/audit/_shared.py`:

```python
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
```

- [ ] **Step 6: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_sync.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/ \
        naturesseed-content-pipeline/tests/audit/test_sync.py
git commit -m "feat(audit): sync stage with wc_catalog_snapshot writer"
```

---

## Task 5: Link Extractor

**Files:**
- Create: `src/naturesseed_pipeline/pipelines/audit/link_extract.py`
- Test: `tests/audit/test_link_extract.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_link_extract.py`:

```python
"""Unit tests for link extraction and URL classification."""

from naturesseed_pipeline.pipelines.audit.link_extract import (
    classify_href, extract_links, ExtractedLink,
)


def test_classify_anchor():
    assert classify_href("#section-1", "naturesseed.com") == "anchor"


def test_classify_internal_product():
    assert classify_href("https://naturesseed.com/products/fescue/", "naturesseed.com") == "internal_product"
    assert classify_href("https://naturesseed.com/product/bundle/foo/", "naturesseed.com") == "internal_product"


def test_classify_internal_content():
    assert classify_href("https://naturesseed.com/resources/guide/", "naturesseed.com") == "internal_content"
    assert classify_href("/resources/guide/", "naturesseed.com") == "internal_content"


def test_classify_external():
    assert classify_href("https://example.com/page", "naturesseed.com") == "external"


def test_extract_links_returns_href_and_anchor():
    html = '<p><a href="/a/">A text</a> <a href="https://ext.com">Ext</a></p>'
    links = extract_links(html, "naturesseed.com")
    assert len(links) == 2
    assert links[0] == ExtractedLink(href="/a/", anchor_text="A text", link_type="internal_content")
    assert links[1].link_type == "external"


def test_extract_links_dedupes_same_href_in_same_doc():
    html = '<a href="/x/">first</a> <a href="/x/">second</a>'
    links = extract_links(html, "naturesseed.com")
    assert len(links) == 1
    assert links[0].anchor_text == "first"


def test_extract_links_handles_relative_urls():
    html = '<a href="/products/foo/">Foo</a>'
    links = extract_links(html, "naturesseed.com")
    assert links[0].link_type == "internal_product"
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_link_extract.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `link_extract.py`**

Create `src/naturesseed_pipeline/pipelines/audit/link_extract.py`:

```python
"""Parse HTML and extract classified outbound links."""

from dataclasses import dataclass
from urllib.parse import urlparse

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ExtractedLink:
    href: str
    anchor_text: str
    link_type: str  # 'internal_content' | 'internal_product' | 'external' | 'anchor'


def classify_href(href: str, site_host: str) -> str:
    if not href:
        return "external"
    if href.startswith("#"):
        return "anchor"
    parsed = urlparse(href)
    path = parsed.path or ""
    host = parsed.netloc.lower()
    site_host = site_host.lower().lstrip("www.")

    is_internal = (host == "" or host == site_host or host == f"www.{site_host}")
    if not is_internal:
        return "external"
    if path.startswith("/products/") or path.startswith("/product/"):
        return "internal_product"
    return "internal_content"


def extract_links(html: str, site_host: str) -> list[ExtractedLink]:
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    seen: dict[str, ExtractedLink] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href in seen:
            continue
        anchor = a.get_text(separator=" ", strip=True)[:500]
        seen[href] = ExtractedLink(
            href=href,
            anchor_text=anchor,
            link_type=classify_href(href, site_host),
        )
    return list(seen.values())
```

- [ ] **Step 4: Run tests (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_link_extract.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/link_extract.py \
        naturesseed-content-pipeline/tests/audit/test_link_extract.py
git commit -m "feat(audit): HTML link extractor with URL classification"
```

---

## Task 6: Link HTTP Checker

**Files:**
- Create: `src/naturesseed_pipeline/pipelines/audit/link_check.py`
- Test: `tests/audit/test_link_check.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_link_check.py`:

```python
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
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_link_check.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `link_check.py`**

Create `src/naturesseed_pipeline/pipelines/audit/link_check.py`:

```python
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
    Returns the number of links updated."""
    close_client = False
    if client is None:
        client = httpx.Client(); close_client = True

    try:
        # Gather unique hrefs needing check (one check per unique URL, applied to all rows)
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
```

Note: concurrency arg is retained for future threading; initial implementation is sequential to keep the test stable. An implementer can swap in `concurrent.futures.ThreadPoolExecutor` later without changing the signature.

- [ ] **Step 4: Run tests (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_link_check.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/link_check.py \
        naturesseed-content-pipeline/tests/audit/test_link_check.py
git commit -m "feat(audit): HTTP status checker with 30-day cache"
```

---

## Task 7: `scan-links` Stage Orchestrator

**Files:**
- Create: `src/naturesseed_pipeline/pipelines/audit/scan_links.py`
- Test: `tests/audit/test_scan_links.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_scan_links.py`:

```python
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
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_scan_links.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `scan_links.py`**

Create `src/naturesseed_pipeline/pipelines/audit/scan_links.py`:

```python
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
```

- [ ] **Step 4: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_scan_links.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/scan_links.py \
        naturesseed-content-pipeline/tests/audit/test_scan_links.py
git commit -m "feat(audit): scan-links stage orchestrator"
```

---

## Task 8: Product Matcher Built From `wc_catalog_snapshot`

**Files:**
- Create: `src/naturesseed_pipeline/pipelines/audit/product_match.py`
- Test: `tests/audit/test_product_match.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_product_match.py`:

```python
"""Product matcher built from wc_catalog_snapshot rows."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Base, WcCatalogSnapshot
from naturesseed_pipeline.pipelines.audit.product_match import (
    build_matcher, ProductMatch, find_product_mentions,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def _seed(s):
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="fine-fescue-grass-seed-mix",
                            name="Fine Fescue Grass Seed Mix", status="publish",
                            permalink="https://naturesseed.com/products/fine-fescue-grass-seed-mix/",
                            species_list=["fine fescue"]))
    s.add(WcCatalogSnapshot(wp_product_id=2, slug="old-pasture-mix",
                            name="Old Pasture Mix", status="draft",
                            permalink="https://naturesseed.com/products/old-pasture-mix/",
                            species_list=["alfalfa", "clover"]))
    s.commit()


def test_build_matcher_indexes_all():
    s = _session(); _seed(s)
    m = build_matcher(s)
    assert "fine-fescue-grass-seed-mix" in m.by_slug
    assert "old-pasture-mix" in m.by_slug
    assert m.by_slug["old-pasture-mix"].status == "draft"


def test_find_mentions_url_match():
    s = _session(); _seed(s)
    m = build_matcher(s)
    html = 'Check <a href="https://naturesseed.com/products/fine-fescue-grass-seed-mix/">this</a>.'
    matches = find_product_mentions("", html, m, fuzzy_threshold=0.85)
    assert len(matches) == 1
    assert matches[0].wp_product_id == 1
    assert matches[0].match_type == "url"
    assert matches[0].is_active is True


def test_find_mentions_exact_name():
    s = _session(); _seed(s)
    m = build_matcher(s)
    text = "We love our Old Pasture Mix for clients."
    matches = find_product_mentions(text, "", m, fuzzy_threshold=0.85)
    assert len(matches) == 1
    assert matches[0].wp_product_id == 2
    assert matches[0].match_type == "exact"
    assert matches[0].is_active is False


def test_find_mentions_fuzzy():
    s = _session(); _seed(s)
    m = build_matcher(s)
    text = "Our fine fescue grass-seed mix is great."
    matches = find_product_mentions(text, "", m, fuzzy_threshold=0.85)
    assert any(x.wp_product_id == 1 for x in matches)


def test_find_mentions_dedupes_url_beats_exact():
    s = _session(); _seed(s)
    m = build_matcher(s)
    html = '<a href="/products/fine-fescue-grass-seed-mix/">Fine Fescue Grass Seed Mix</a>'
    text = "Fine Fescue Grass Seed Mix"
    matches = find_product_mentions(text, html, m, fuzzy_threshold=0.85)
    by_id = {p.wp_product_id: p for p in matches}
    assert by_id[1].match_type == "url"  # url wins over exact
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_product_match.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `product_match.py`**

Create `src/naturesseed_pipeline/pipelines/audit/product_match.py`:

```python
"""Product matcher built from wc_catalog_snapshot.

Three-tier matching per article:
  1. URL exact  — href contains a product permalink or /products/<slug>/
  2. Name exact — product name appears as substring in text (case-insensitive)
  3. Name fuzzy — rapidfuzz.token_set_ratio above threshold
"""

import re
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import WcCatalogSnapshot


@dataclass
class ProductRecord:
    wp_product_id: int
    slug: str
    name: str
    status: str
    permalink: str
    species_list: list[str]


@dataclass
class ProductMatcher:
    by_slug: dict[str, ProductRecord]
    by_name_lower: dict[str, ProductRecord]
    all_records: list[ProductRecord]


@dataclass
class ProductMatch:
    wp_product_id: int
    product_slug: str
    product_name: str
    is_active: bool
    match_type: str  # 'url' | 'exact' | 'fuzzy'
    confidence: float
    snippet: str


def build_matcher(session: Session) -> ProductMatcher:
    rows = session.execute(select(WcCatalogSnapshot)).scalars().all()
    records = [
        ProductRecord(
            wp_product_id=r.wp_product_id, slug=r.slug, name=r.name,
            status=r.status, permalink=r.permalink or "",
            species_list=r.species_list or [],
        )
        for r in rows
    ]
    return ProductMatcher(
        by_slug={r.slug: r for r in records},
        by_name_lower={r.name.lower(): r for r in records if r.name},
        all_records=records,
    )


_URL_PATTERN = re.compile(r"/products?/([a-z0-9][a-z0-9\-/]*)/?", re.IGNORECASE)


def _snippet(text: str, start: int, end: int, ctx: int = 60) -> str:
    lo = max(0, start - ctx); hi = min(len(text), end + ctx)
    return ("..." if lo > 0 else "") + text[lo:hi] + ("..." if hi < len(text) else "")


def find_product_mentions(
    text: str,
    html: str,
    matcher: ProductMatcher,
    fuzzy_threshold: float,
) -> list[ProductMatch]:
    matches: dict[int, ProductMatch] = {}

    # 1. URL-based
    for source in (html, text):
        for m in _URL_PATTERN.finditer(source or ""):
            slug = m.group(1).split("/")[-1].lower()
            rec = matcher.by_slug.get(slug)
            if rec and rec.wp_product_id not in matches:
                matches[rec.wp_product_id] = ProductMatch(
                    wp_product_id=rec.wp_product_id,
                    product_slug=rec.slug, product_name=rec.name,
                    is_active=(rec.status == "publish"),
                    match_type="url", confidence=1.0,
                    snippet=_snippet(source, m.start(), m.end()),
                )

    # 2. Exact name
    text_lower = (text or "").lower()
    for name_lower, rec in matcher.by_name_lower.items():
        if rec.wp_product_id in matches:
            continue
        if len(name_lower) < 4:
            continue
        pos = text_lower.find(name_lower)
        if pos >= 0:
            matches[rec.wp_product_id] = ProductMatch(
                wp_product_id=rec.wp_product_id,
                product_slug=rec.slug, product_name=rec.name,
                is_active=(rec.status == "publish"),
                match_type="exact", confidence=0.9,
                snippet=_snippet(text, pos, pos + len(name_lower)),
            )

    # 3. Fuzzy name (token_set_ratio over sliding window; skip already-matched)
    if text_lower:
        tokens = text_lower.split()
        for name_lower, rec in matcher.by_name_lower.items():
            if rec.wp_product_id in matches:
                continue
            if len(name_lower) < 6:
                continue
            name_words = name_lower.split()
            window = max(len(name_words), 2)
            for i in range(0, max(len(tokens) - window + 1, 0)):
                chunk = " ".join(tokens[i:i + window])
                score = fuzz.token_set_ratio(name_lower, chunk) / 100.0
                if score >= fuzzy_threshold:
                    matches[rec.wp_product_id] = ProductMatch(
                        wp_product_id=rec.wp_product_id,
                        product_slug=rec.slug, product_name=rec.name,
                        is_active=(rec.status == "publish"),
                        match_type="fuzzy", confidence=score,
                        snippet=chunk,
                    )
                    break

    return list(matches.values())
```

- [ ] **Step 4: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_product_match.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/product_match.py \
        naturesseed-content-pipeline/tests/audit/test_product_match.py
git commit -m "feat(audit): product matcher with url/exact/fuzzy tiers"
```

---

## Task 9: `tag-products` Stage + Species Extraction

**Files:**
- Create: `src/naturesseed_pipeline/pipelines/audit/tag_products.py`
- Test: `tests/audit/test_tag_products.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_tag_products.py`:

```python
"""Integration test for tag-products stage."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentProductMention,
    OrphanReference, WcCatalogSnapshot,
)
from naturesseed_pipeline.pipelines.audit.tag_products import run_tag_products


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def _seed_catalog(s):
    s.add_all([
        WcCatalogSnapshot(wp_product_id=1, slug="active-mix", name="Active Mix",
                         status="publish", permalink="https://x/products/active-mix/",
                         species_list=["fescue", "rye"]),
        WcCatalogSnapshot(wp_product_id=2, slug="old-mix", name="Old Mix",
                         status="draft", permalink="https://x/products/old-mix/",
                         species_list=["orchard grass"]),
    ]); s.commit()


def test_active_product_goes_to_mentions_not_orphan():
    s = _session(); _seed_catalog(s)
    s.add(ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                          content_html='<a href="/products/active-mix/">x</a>',
                          content_text="Active Mix is great"))
    s.commit()

    run_tag_products(s, fuzzy_threshold=0.85)
    s.commit()

    mentions = s.execute(select(ContentProductMention)).scalars().all()
    orphans = s.execute(select(OrphanReference)).scalars().all()
    assert len(mentions) == 1 and mentions[0].wp_product_id == 1
    # species in active product → not an orphan
    assert not any(o.reference_type == "species_mention" and o.reference_value == "fescue"
                   for o in orphans)


def test_discontinued_product_goes_to_orphan_not_mentions():
    s = _session(); _seed_catalog(s)
    s.add(ContentInventory(url="https://x/b", title="B", slug="b", post_type="post",
                          content_html='', content_text="Old Mix worked well."))
    s.commit()

    run_tag_products(s, fuzzy_threshold=0.85)
    s.commit()

    assert s.execute(select(ContentProductMention)).scalars().all() == []
    orphans = s.execute(select(OrphanReference)).scalars().all()
    assert any(o.reference_type == "inactive_product" for o in orphans)


def test_unmatched_species_flagged_as_species_mention():
    s = _session(); _seed_catalog(s)
    s.add(ContentInventory(url="https://x/c", title="C", slug="c", post_type="post",
                          content_html='', content_text="Plant clover or orchard grass here."))
    s.commit()

    run_tag_products(s, fuzzy_threshold=0.85)
    s.commit()

    orphans = s.execute(select(OrphanReference)).scalars().all()
    values = {o.reference_value for o in orphans
              if o.reference_type == "species_mention"}
    assert "clover" in values  # not in any snapshot species_list


def test_rerun_clears_prior_rows_and_re_inserts():
    s = _session(); _seed_catalog(s)
    s.add(ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                          content_html='<a href="/products/active-mix/">x</a>',
                          content_text=""))
    s.commit()

    run_tag_products(s, fuzzy_threshold=0.85); s.commit()
    run_tag_products(s, fuzzy_threshold=0.85); s.commit()

    mentions = s.execute(select(ContentProductMention)).scalars().all()
    assert len(mentions) == 1
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_tag_products.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `tag_products.py`**

Create `src/naturesseed_pipeline/pipelines/audit/tag_products.py`:

```python
"""Tag articles with product and species mentions.

- Active product mentions → content_product_mentions
- Inactive (status='draft') product mentions → orphan_references (inactive_product)
- Species names not in any publish-status product's species_list → orphan_references (species_mention)
"""

import re

import structlog
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    ContentInventory, ContentProductMention, OrphanReference, WcCatalogSnapshot,
)
from naturesseed_pipeline.pipelines.audit.product_match import (
    ProductMatcher, build_matcher, find_product_mentions,
)

log = structlog.get_logger()


def _collect_species(matcher: ProductMatcher) -> set[str]:
    species: set[str] = set()
    for rec in matcher.all_records:
        for s in rec.species_list or []:
            if s:
                species.add(s.strip().lower())
    return species


def _find_species_mentions(text: str, all_species: set[str]) -> list[tuple[str, str]]:
    """Return (species, snippet) tuples for every species string found in text."""
    if not text:
        return []
    text_lower = text.lower()
    hits: list[tuple[str, str]] = []
    for sp in all_species:
        if len(sp) < 4:
            continue
        pattern = r"\b" + re.escape(sp) + r"\b"
        m = re.search(pattern, text_lower)
        if m:
            lo = max(0, m.start() - 40); hi = min(len(text), m.end() + 40)
            hits.append((sp, text[lo:hi]))
    return hits


def run_tag_products(session: Session, fuzzy_threshold: float) -> dict[str, int]:
    matcher = build_matcher(session)
    all_species = _collect_species(matcher)

    content_rows = session.execute(select(ContentInventory)).scalars().all()

    counts = {"articles": 0, "product_mentions": 0, "inactive_orphans": 0,
              "species_orphans": 0}

    for row in content_rows:
        counts["articles"] += 1

        # Wipe prior auto-populated rows for this content (keep user-decided)
        session.execute(
            delete(ContentProductMention)
            .where(ContentProductMention.content_inventory_id == row.id)
        )
        session.execute(
            delete(OrphanReference).where(
                OrphanReference.content_inventory_id == row.id,
                OrphanReference.reference_type.in_(["inactive_product", "species_mention"]),
                OrphanReference.user_decision_at.is_(None),
            )
        )
        session.flush()

        matches = find_product_mentions(
            row.content_text or "", row.content_html or "",
            matcher, fuzzy_threshold,
        )
        for m in matches:
            if m.is_active:
                session.add(ContentProductMention(
                    content_inventory_id=row.id, wp_product_id=m.wp_product_id,
                    product_slug=m.product_slug, product_name=m.product_name,
                    mention_count=1, first_snippet=m.snippet,
                    match_type=m.match_type, confidence=m.confidence,
                ))
                counts["product_mentions"] += 1
            else:
                session.add(OrphanReference(
                    content_inventory_id=row.id,
                    reference_type="inactive_product",
                    reference_value=m.product_slug,
                    matched_inactive_product_id=m.wp_product_id,
                    match_confidence=m.confidence,
                    snippet=m.snippet,
                    status="flagged",
                ))
                counts["inactive_orphans"] += 1

        # Species mentions: only flag if species not already covered by an active match
        covered_species = {
            sp.strip().lower()
            for match in matches if match.is_active
            for sp in (matcher.by_slug.get(match.product_slug).species_list or [])
        }
        for species, snippet in _find_species_mentions(row.content_text or "", all_species):
            if species in covered_species:
                continue
            session.add(OrphanReference(
                content_inventory_id=row.id,
                reference_type="species_mention",
                reference_value=species,
                match_confidence=1.0,
                snippet=snippet,
                status="flagged",
            ))
            counts["species_orphans"] += 1

        session.flush()

    log.info("audit.tag_products.done", **counts)
    return counts
```

- [ ] **Step 4: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_tag_products.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/tag_products.py \
        naturesseed-content-pipeline/tests/audit/test_tag_products.py
git commit -m "feat(audit): tag-products stage — mentions, inactives, species"
```

---

## Task 10: Topic Taxonomy Seed from WC Categories

**Files:**
- Create: `src/naturesseed_pipeline/pipelines/audit/classify.py`
- Test: `tests/audit/test_classify_seed.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_classify_seed.py`:

```python
"""Seed top-level topics from WooCommerce categories."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Base, Topic
from naturesseed_pipeline.pipelines.audit.classify import seed_topics_from_wc_categories


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_seed_inserts_top_level_topics():
    s = _session()
    wc_categories = [
        {"id": 10, "slug": "grass-seed", "name": "Grass Seed"},
        {"id": 11, "slug": "pasture-seed", "name": "Pasture Seed"},
        {"id": 12, "slug": "wildflower-seed", "name": "Wildflower Seed"},
    ]
    count = seed_topics_from_wc_categories(s, wc_categories)
    s.commit()
    assert count == 3
    topics = s.execute(select(Topic).order_by(Topic.slug)).scalars().all()
    assert all(t.parent_topic_id is None for t in topics)
    assert all(t.approved == 1 for t in topics)
    assert all(t.source == "wc_category" for t in topics)


def test_seed_is_idempotent():
    s = _session()
    wc_categories = [{"id": 10, "slug": "grass-seed", "name": "Grass Seed"}]
    seed_topics_from_wc_categories(s, wc_categories); s.commit()
    added = seed_topics_from_wc_categories(s, wc_categories); s.commit()
    assert added == 0
    assert len(s.execute(select(Topic)).scalars().all()) == 1


def test_seed_creates_unclassified_bucket():
    s = _session()
    seed_topics_from_wc_categories(s, []); s.commit()
    topics = s.execute(select(Topic)).scalars().all()
    assert any(t.slug == "unclassified" for t in topics)
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_classify_seed.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement the seed function**

Create `src/naturesseed_pipeline/pipelines/audit/classify.py`:

```python
"""Classify stage — assigns each article to a topic + subtopic.

Four-pass workflow:
  Pass 1: seed top-level Topics from WC categories + deterministic article → topic
  Pass 2: propose subtopics via LLM (one shot per topic; proposals start approved=0)
  Pass 3: user approval gate (CLI flips approved=1)
  Pass 4: deterministic subtopic matching using approved subtopic keyword phrases
"""

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    ContentInventory, ContentTopic, Topic, WcCatalogSnapshot,
)

log = structlog.get_logger()


def seed_topics_from_wc_categories(
    session: Session, wc_categories: list[dict[str, Any]],
) -> int:
    """Insert missing top-level topics for each WC category + an Unclassified bucket."""
    existing = {t.slug for t in session.execute(select(Topic)).scalars().all()
                if t.parent_topic_id is None}
    added = 0
    for cat in wc_categories:
        slug = cat.get("slug") or ""
        if not slug or slug in existing:
            continue
        session.add(Topic(
            name=cat.get("name") or slug, slug=slug,
            wc_category_slug=slug, source="wc_category", approved=1,
        ))
        existing.add(slug); added += 1
    if "unclassified" not in existing:
        session.add(Topic(name="Unclassified", slug="unclassified",
                          source="user_created", approved=1))
        added += 1
    return added
```

- [ ] **Step 4: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_classify_seed.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/classify.py \
        naturesseed-content-pipeline/tests/audit/test_classify_seed.py
git commit -m "feat(audit): seed top-level topics from WC categories"
```

---

## Task 11: Classify Pass 1 — Deterministic Top-Level Assignment

**Files:**
- Modify: `src/naturesseed_pipeline/pipelines/audit/classify.py`
- Test: `tests/audit/test_classify_pass1.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_classify_pass1.py`:

```python
"""Pass 1 of classify — assigns each article a top-level topic deterministically."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentTopic, Topic, WcCatalogSnapshot,
)
from naturesseed_pipeline.pipelines.audit.classify import (
    seed_topics_from_wc_categories, run_classify_pass1,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_pass1_product_gets_category_topic():
    s = _session()
    seed_topics_from_wc_categories(s, [
        {"id": 10, "slug": "grass-seed", "name": "Grass Seed"},
    ]); s.commit()
    # WC category id 10 maps to slug "grass-seed" via wp_cat_id_to_slug
    s.add(ContentInventory(wp_post_id=1, url="https://x/p/1/", title="Fescue Mix",
                          slug="fescue-mix", post_type="product",
                          categories=[10], status="publish"))
    s.commit()

    count = run_classify_pass1(s, wp_cat_id_to_slug={10: "grass-seed"})
    s.commit()

    assignments = s.execute(select(ContentTopic)).scalars().all()
    assert len(assignments) == 1
    grass = s.execute(select(Topic).where(Topic.slug == "grass-seed")).scalar_one()
    assert assignments[0].topic_id == grass.id


def test_pass1_post_falls_to_unclassified_without_category():
    s = _session()
    seed_topics_from_wc_categories(s, [
        {"id": 10, "slug": "grass-seed", "name": "Grass Seed"},
    ]); s.commit()
    s.add(ContentInventory(wp_post_id=2, url="https://x/a/", title="A", slug="a",
                          post_type="post", categories=[], status="publish"))
    s.commit()

    run_classify_pass1(s, wp_cat_id_to_slug={10: "grass-seed"})
    s.commit()

    assignments = s.execute(select(ContentTopic)).scalars().all()
    unclassified = s.execute(select(Topic).where(Topic.slug == "unclassified")).scalar_one()
    assert assignments[0].topic_id == unclassified.id


def test_pass1_idempotent():
    s = _session()
    seed_topics_from_wc_categories(s, [
        {"id": 10, "slug": "grass-seed", "name": "Grass Seed"},
    ]); s.commit()
    s.add(ContentInventory(wp_post_id=1, url="https://x/p/1/", title="X", slug="x",
                          post_type="post", categories=[10], status="publish"))
    s.commit()

    run_classify_pass1(s, wp_cat_id_to_slug={10: "grass-seed"}); s.commit()
    run_classify_pass1(s, wp_cat_id_to_slug={10: "grass-seed"}); s.commit()

    assignments = s.execute(select(ContentTopic)).scalars().all()
    assert len(assignments) == 1
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_classify_pass1.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Append `run_classify_pass1` to `classify.py`**

Append to `src/naturesseed_pipeline/pipelines/audit/classify.py`:

```python
def _find_top_level_topic_slug(
    row: ContentInventory,
    wp_cat_id_to_slug: dict[int, str],
    topic_slugs: set[str],
) -> str:
    """Return slug of top-level topic this article should map to."""
    for cat_id in row.categories or []:
        if not isinstance(cat_id, int):
            continue
        slug = wp_cat_id_to_slug.get(cat_id)
        if slug and slug in topic_slugs:
            return slug
    return "unclassified"


def run_classify_pass1(
    session: Session, wp_cat_id_to_slug: dict[int, str],
) -> int:
    """Assign every article to a top-level topic based on its WP/WC categories."""
    topics = {t.slug: t for t in session.execute(select(Topic)).scalars().all()
              if t.parent_topic_id is None}
    topic_slugs = set(topics.keys())

    existing_pairs = {
        (a.content_inventory_id, a.topic_id)
        for a in session.execute(select(ContentTopic)).scalars().all()
    }

    rows = session.execute(select(ContentInventory)).scalars().all()
    assigned = 0
    for row in rows:
        slug = _find_top_level_topic_slug(row, wp_cat_id_to_slug, topic_slugs)
        topic = topics.get(slug) or topics["unclassified"]
        key = (row.id, topic.id)
        if key in existing_pairs:
            continue
        session.add(ContentTopic(
            content_inventory_id=row.id, topic_id=topic.id,
            confidence=1.0, assigned_by="auto",
        ))
        existing_pairs.add(key); assigned += 1
    return assigned
```

- [ ] **Step 4: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_classify_pass1.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/classify.py \
        naturesseed-content-pipeline/tests/audit/test_classify_pass1.py
git commit -m "feat(audit): classify pass 1 — deterministic top-level assignment"
```

---

## Task 12: Classify Pass 2 — LLM Subtopic Proposal

**Files:**
- Modify: `src/naturesseed_pipeline/pipelines/audit/classify.py`
- Test: `tests/audit/test_classify_pass2.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_classify_pass2.py`:

```python
"""Pass 2 — LLM subtopic proposal (mocked LLM)."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentTopic, Topic,
)
from naturesseed_pipeline.pipelines.audit.classify import (
    run_classify_pass2, SubtopicProposer,
)


class FakeProposer(SubtopicProposer):
    def propose(self, topic_name, samples):
        return [
            {"name": "Cool-Season", "slug": "cool-season",
             "keywords": ["fescue", "rye", "kentucky bluegrass"]},
            {"name": "Warm-Season", "slug": "warm-season",
             "keywords": ["bermuda", "zoysia", "st augustine"]},
        ]


def _setup(s: Session):
    topic = Topic(name="Grass Seed", slug="grass-seed",
                  wc_category_slug="grass-seed", source="wc_category", approved=1)
    s.add(topic); s.flush()
    for i in range(3):
        c = ContentInventory(wp_post_id=i + 1, url=f"https://x/{i}", title=f"A{i}",
                            slug=f"a{i}", post_type="post", content_text="fescue info")
        s.add(c); s.flush()
        s.add(ContentTopic(content_inventory_id=c.id, topic_id=topic.id,
                          confidence=1.0, assigned_by="auto"))
    s.commit()
    return topic


def test_pass2_proposes_subtopics_with_approved_zero():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    s = Session(eng)
    topic = _setup(s)

    proposed = run_classify_pass2(s, proposer=FakeProposer())
    s.commit()
    assert proposed == 2

    subs = s.execute(select(Topic).where(Topic.parent_topic_id == topic.id)).scalars().all()
    assert len(subs) == 2
    assert all(t.source == "llm_proposed" and t.approved == 0 for t in subs)
    slugs = {t.slug for t in subs}
    assert slugs == {"cool-season", "warm-season"}


def test_pass2_skips_topics_with_existing_approved_subtopics():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    s = Session(eng)
    topic = _setup(s)

    # Pre-existing approved subtopic
    s.add(Topic(name="Existing", slug="existing", parent_topic_id=topic.id,
               source="user_created", approved=1))
    s.commit()

    proposed = run_classify_pass2(s, proposer=FakeProposer())
    s.commit()
    assert proposed == 0
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_classify_pass2.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Append `SubtopicProposer` + `run_classify_pass2`**

Append to `src/naturesseed_pipeline/pipelines/audit/classify.py`:

```python
import json
from typing import Protocol


class SubtopicProposer(Protocol):
    """Contract for LLM-backed subtopic proposal. Real impl uses Anthropic."""
    def propose(self, topic_name: str, samples: list[dict[str, str]]) -> list[dict]: ...


class AnthropicSubtopicProposer:
    """Real LLM impl — reads Anthropic client from settings."""

    def __init__(self, model: str | None = None) -> None:
        from naturesseed_pipeline.config import settings
        import anthropic
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = model or settings.audit_llm_model

    def propose(self, topic_name: str, samples: list[dict[str, str]]) -> list[dict]:
        sample_text = "\n\n".join(
            f"- Title: {s['title']}\n  Excerpt: {s.get('excerpt', '')[:400]}"
            for s in samples[:40]
        )
        prompt = f"""You are organizing a content library for Nature's Seed.
Top-level topic: "{topic_name}".

Here are {len(samples)} article titles + excerpts in this topic:

{sample_text}

Propose 3-7 subtopics that best organize this content. Each subtopic MUST have:
- A short name (2-4 words, title case)
- A URL-safe slug (lowercase, hyphens)
- 5-15 keyword phrases that, when matched against article text, would reliably identify articles as belonging to that subtopic

Return ONLY a JSON array of objects with keys: name, slug, keywords. No prose.
"""
        resp = self.client.messages.create(
            model=self.model, max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        # Trim markdown fences if present
        if text.startswith("```"):
            text = text.strip("`")
            text = text.split("\n", 1)[1] if "\n" in text else text
            if text.endswith("```"):
                text = text[:-3]
        return json.loads(text)


def run_classify_pass2(session: Session, proposer: SubtopicProposer) -> int:
    """Ask LLM to propose subtopics for each top-level topic with no existing approved subtopics."""
    top_level = [t for t in session.execute(select(Topic)).scalars().all()
                 if t.parent_topic_id is None and t.slug != "unclassified"]
    proposed_count = 0

    for topic in top_level:
        existing_subs = session.execute(
            select(Topic).where(Topic.parent_topic_id == topic.id, Topic.approved == 1)
        ).scalars().all()
        if existing_subs:
            continue

        # Collect article samples in this topic
        sample_rows = session.execute(
            select(ContentInventory)
            .join(ContentTopic, ContentTopic.content_inventory_id == ContentInventory.id)
            .where(ContentTopic.topic_id == topic.id)
            .limit(40)
        ).scalars().all()
        if not sample_rows:
            continue

        samples = [{"title": r.title, "excerpt": r.excerpt or r.content_text[:500] or ""}
                   for r in sample_rows]

        proposals = proposer.propose(topic.name, samples)
        for p in proposals:
            slug = p.get("slug") or ""
            if not slug:
                continue
            existing = session.execute(
                select(Topic).where(Topic.slug == slug)
            ).scalar_one_or_none()
            if existing:
                continue
            t = Topic(
                name=p.get("name") or slug, slug=slug,
                parent_topic_id=topic.id, source="llm_proposed", approved=0,
            )
            # Keywords stored inside the name field is ugly — use a separate
            # mechanism: serialize into wc_category_slug? Better: persist as JSON
            # in topic — but schema doesn't have a field. Compromise for the plan:
            # store keyword list as pipe-delimited string in name (ugly) — OR
            # extend schema. For TDD here we store keywords in a side dict via
            # a helper table? Keep simple: pack into existing field. To keep the
            # test passing we only need the row to exist.
            session.add(t); proposed_count += 1

    return proposed_count
```

Note: subtopic keyword phrases need persistence for Pass 4. The schema as specified doesn't have a `keywords` field on `topics`. **Before Step 4, add a `keywords` JSON column to the `Topic` model.**

- [ ] **Step 4: Add `keywords` column to `Topic` + follow-up migration**

In `src/naturesseed_pipeline/db/models.py`, add to `Topic`:

```python
    keywords: Mapped[list | None] = mapped_column(JSON)
```

Generate migration:

```bash
cd naturesseed-content-pipeline && uv run alembic revision --autogenerate -m "add keywords to topics"
cd naturesseed-content-pipeline && uv run alembic upgrade head
```

Update the proposer to write keywords:

```python
            t = Topic(
                name=p.get("name") or slug, slug=slug,
                parent_topic_id=topic.id, source="llm_proposed", approved=0,
                keywords=p.get("keywords") or [],
            )
```

- [ ] **Step 5: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_classify_pass2.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/classify.py \
        naturesseed-content-pipeline/src/naturesseed_pipeline/db/models.py \
        naturesseed-content-pipeline/alembic/versions/ \
        naturesseed-content-pipeline/tests/audit/test_classify_pass2.py
git commit -m "feat(audit): classify pass 2 — LLM subtopic proposal"
```

---

## Task 13: Classify Pass 3 — Approval Gate CLI

**Files:**
- Modify: `src/naturesseed_pipeline/pipelines/audit/classify.py`
- Test: `tests/audit/test_classify_approve.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_classify_approve.py`:

```python
"""Approval helpers for pass 3 — the CLI piggybacks on these."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Base, Topic
from naturesseed_pipeline.pipelines.audit.classify import (
    list_pending_subtopics, approve_subtopic, approve_all_subtopics,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    s = Session(eng)
    parent = Topic(name="Grass Seed", slug="grass-seed", source="wc_category", approved=1)
    s.add(parent); s.flush()
    s.add(Topic(name="Cool", slug="cool", parent_topic_id=parent.id,
               source="llm_proposed", approved=0, keywords=["fescue"]))
    s.add(Topic(name="Warm", slug="warm", parent_topic_id=parent.id,
               source="llm_proposed", approved=0, keywords=["bermuda"]))
    s.commit()
    return s


def test_list_pending_returns_only_unapproved():
    s = _session()
    pending = list_pending_subtopics(s)
    assert len(pending) == 2
    assert all(t.approved == 0 for t in pending)


def test_approve_subtopic_flips_flag():
    s = _session()
    approved = approve_subtopic(s, "cool"); s.commit()
    assert approved is True
    cool = s.execute(select(Topic).where(Topic.slug == "cool")).scalar_one()
    assert cool.approved == 1


def test_approve_all_approves_every_pending():
    s = _session()
    n = approve_all_subtopics(s); s.commit()
    assert n == 2
    assert not list_pending_subtopics(s)
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_classify_approve.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Append approval helpers**

Append to `src/naturesseed_pipeline/pipelines/audit/classify.py`:

```python
def list_pending_subtopics(session: Session) -> list[Topic]:
    return session.execute(
        select(Topic).where(
            Topic.parent_topic_id.isnot(None),
            Topic.source == "llm_proposed",
            Topic.approved == 0,
        ).order_by(Topic.id)
    ).scalars().all()


def approve_subtopic(session: Session, slug: str) -> bool:
    t = session.execute(select(Topic).where(Topic.slug == slug)).scalar_one_or_none()
    if t is None or t.approved == 1:
        return False
    t.approved = 1
    return True


def approve_all_subtopics(session: Session) -> int:
    pending = list_pending_subtopics(session)
    for t in pending:
        t.approved = 1
    return len(pending)
```

- [ ] **Step 4: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_classify_approve.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/classify.py \
        naturesseed-content-pipeline/tests/audit/test_classify_approve.py
git commit -m "feat(audit): classify pass 3 — approval helpers"
```

---

## Task 14: Classify Pass 4 — Deterministic Subtopic Assignment

**Files:**
- Modify: `src/naturesseed_pipeline/pipelines/audit/classify.py`
- Test: `tests/audit/test_classify_pass4.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_classify_pass4.py`:

```python
"""Pass 4 — match articles to approved subtopics via keyword presence."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentTopic, Topic,
)
from naturesseed_pipeline.pipelines.audit.classify import run_classify_pass4


def _setup() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    s = Session(eng)
    parent = Topic(name="Grass Seed", slug="grass-seed", source="wc_category", approved=1)
    s.add(parent); s.flush()
    cool = Topic(name="Cool-Season", slug="cool-season", parent_topic_id=parent.id,
                source="llm_proposed", approved=1,
                keywords=["fescue", "rye", "kentucky bluegrass"])
    warm = Topic(name="Warm-Season", slug="warm-season", parent_topic_id=parent.id,
                source="llm_proposed", approved=1,
                keywords=["bermuda", "zoysia"])
    s.add_all([cool, warm]); s.flush()

    # Article matches cool
    a1 = ContentInventory(wp_post_id=1, url="https://x/1", title="Fescue Guide",
                         slug="fescue-guide", post_type="post",
                         content_text="Fescue and rye are great cool-season grasses.")
    # Article matches warm
    a2 = ContentInventory(wp_post_id=2, url="https://x/2", title="Bermuda Guide",
                         slug="bermuda-guide", post_type="post",
                         content_text="Bermuda grows in warm climates.")
    # Article matches neither
    a3 = ContentInventory(wp_post_id=3, url="https://x/3", title="Misc",
                         slug="misc", post_type="post",
                         content_text="Something unrelated.")
    s.add_all([a1, a2, a3]); s.flush()
    for a in (a1, a2, a3):
        s.add(ContentTopic(content_inventory_id=a.id, topic_id=parent.id,
                          confidence=1.0, assigned_by="auto"))
    s.commit()
    return s


def test_pass4_assigns_matching_subtopic():
    s = _setup()
    count = run_classify_pass4(s); s.commit()
    assert count == 2  # a1 + a2

    assignments = s.execute(select(ContentTopic)).scalars().all()
    # 3 (top-level from setup) + 2 (subtopic from pass4) = 5
    assert len(assignments) == 5


def test_pass4_picks_best_match_when_multiple_keywords_hit():
    s = _setup()
    # Add a more strongly cool-matching article
    a = ContentInventory(wp_post_id=99, url="https://x/99", title="Fescue Rye",
                        slug="fr", post_type="post",
                        content_text="fescue rye fescue kentucky bluegrass")
    s.add(a); s.flush()
    parent = s.execute(select(Topic).where(Topic.slug == "grass-seed")).scalar_one()
    s.add(ContentTopic(content_inventory_id=a.id, topic_id=parent.id,
                      confidence=1.0, assigned_by="auto"))
    s.commit()

    run_classify_pass4(s); s.commit()

    cool = s.execute(select(Topic).where(Topic.slug == "cool-season")).scalar_one()
    assignments = s.execute(
        select(ContentTopic).where(ContentTopic.content_inventory_id == a.id)
    ).scalars().all()
    assert any(x.topic_id == cool.id for x in assignments)
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_classify_pass4.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Append `run_classify_pass4`**

Append to `src/naturesseed_pipeline/pipelines/audit/classify.py`:

```python
def _score_article_against_subtopic(text: str, keywords: list[str]) -> int:
    """Hit count of keyword phrases in article text (case-insensitive)."""
    if not text or not keywords:
        return 0
    text_lower = text.lower()
    return sum(text_lower.count(kw.lower()) for kw in keywords if kw)


def run_classify_pass4(session: Session) -> int:
    """Assign subtopic to each article using best-match keyword hit count."""
    # Group approved subtopics by parent
    top_levels = {t.id: t for t in session.execute(
        select(Topic).where(Topic.parent_topic_id.is_(None))
    ).scalars().all()}
    subtopics_by_parent: dict[int, list[Topic]] = {}
    for t in session.execute(
        select(Topic).where(Topic.parent_topic_id.isnot(None), Topic.approved == 1)
    ).scalars().all():
        subtopics_by_parent.setdefault(t.parent_topic_id, []).append(t)

    # Existing content-topic pairs
    existing = {(a.content_inventory_id, a.topic_id) for a in
                session.execute(select(ContentTopic)).scalars().all()}

    assigned = 0
    content_topic_rows = session.execute(select(ContentTopic)).scalars().all()
    # Build: content_id -> list of top-level topic_ids currently assigned
    by_content: dict[int, list[int]] = {}
    for ct in content_topic_rows:
        by_content.setdefault(ct.content_inventory_id, []).append(ct.topic_id)

    content_rows = session.execute(select(ContentInventory)).scalars().all()
    for row in content_rows:
        assigned_topic_ids = by_content.get(row.id, [])
        # Find the top-level topic this article was assigned to
        tl_id = next((tid for tid in assigned_topic_ids if tid in top_levels), None)
        if tl_id is None:
            continue
        subs = subtopics_by_parent.get(tl_id, [])
        if not subs:
            continue

        scored = sorted(
            ((sub, _score_article_against_subtopic(row.content_text or "", sub.keywords or []))
             for sub in subs),
            key=lambda x: x[1], reverse=True,
        )
        best_sub, best_score = scored[0]
        if best_score == 0:
            continue
        if (row.id, best_sub.id) in existing:
            continue

        total_hits = sum(score for _, score in scored) or 1
        session.add(ContentTopic(
            content_inventory_id=row.id, topic_id=best_sub.id,
            confidence=best_score / total_hits, assigned_by="auto",
        ))
        existing.add((row.id, best_sub.id))
        assigned += 1

    return assigned
```

- [ ] **Step 4: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_classify_pass4.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/classify.py \
        naturesseed-content-pipeline/tests/audit/test_classify_pass4.py
git commit -m "feat(audit): classify pass 4 — deterministic subtopic assignment"
```

---

## Task 15: Rule Engine Scaffolding

**Files:**
- Create: `src/naturesseed_pipeline/audit_rules/__init__.py`
- Create: `src/naturesseed_pipeline/audit_rules/base.py`
- Test: `tests/audit/test_rule_engine.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_rule_engine.py`:

```python
"""Rule engine — Protocol, AuditContext, discovery mechanism."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules import discover_rules
from naturesseed_pipeline.audit_rules.base import (
    AuditContext, Finding, DecayRule,
)
from naturesseed_pipeline.db.models import Base, ContentInventory


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_finding_fields():
    f = Finding(rule_name="X", severity="critical", snippet="...",
                suggested_action="do this")
    assert f.rule_name == "X" and f.severity == "critical"


def test_audit_context_exposes_session():
    s = _session()
    ctx = AuditContext(session=s, current_shipping="free over $99")
    assert ctx.session is s
    assert ctx.current_shipping == "free over $99"


def test_discover_rules_finds_rule_classes():
    """Discovery should collect every DecayRule subclass from audit_rules/."""
    rules = discover_rules()
    # At minimum the base module must be skipped; real rules added in later tasks
    # will make this non-empty. For now, the call must not raise.
    assert isinstance(rules, list)


class _DummyRule:
    name = "dummy"
    severity = "info"

    def check(self, content, ctx):
        if "stale" in (content.content_text or ""):
            return [Finding(rule_name=self.name, severity=self.severity,
                           snippet="stale found", suggested_action="refresh")]
        return []


def test_rule_protocol_contract():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="this is stale data")
    s.add(c); s.flush()
    ctx = AuditContext(session=s, current_shipping="")
    findings = _DummyRule().check(c, ctx)
    assert len(findings) == 1
    assert findings[0].snippet == "stale found"
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_rule_engine.py -v
```

Expected: `ImportError` on `audit_rules`.

- [ ] **Step 3: Implement base + discovery**

Create `src/naturesseed_pipeline/audit_rules/base.py`:

```python
"""Decay rule protocol + shared context.

A DecayRule reads a ContentInventory row + AuditContext and returns Findings.
Findings become decay_findings rows.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class Finding:
    rule_name: str
    severity: str  # 'critical' | 'warning' | 'info'
    snippet: str
    suggested_action: str


@dataclass
class AuditContext:
    session: Session
    current_shipping: str
    llm_client: object | None = None  # anthropic.Anthropic, lazy
    llm_model: str = "claude-sonnet-4-6"
    llm_token_budget_remaining: int = 50_000
    _cache: dict = field(default_factory=dict)

    def cached(self, key: str, factory):
        if key not in self._cache:
            self._cache[key] = factory()
        return self._cache[key]


@runtime_checkable
class DecayRule(Protocol):
    name: str
    severity: str

    def check(self, content, ctx: AuditContext) -> list[Finding]: ...
```

Create `src/naturesseed_pipeline/audit_rules/__init__.py`:

```python
"""Registry + directory discovery for decay rules."""

import importlib
import inspect
import pkgutil
from typing import Any

from naturesseed_pipeline.audit_rules.base import DecayRule


def discover_rules() -> list[DecayRule]:
    """Instantiate every DecayRule subclass found in this package."""
    pkg = importlib.import_module("naturesseed_pipeline.audit_rules")
    rules: list[DecayRule] = []
    for info in pkgutil.iter_modules(pkg.__path__):
        if info.name in ("base", "__init__"):
            continue
        module = importlib.import_module(f"naturesseed_pipeline.audit_rules.{info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj is DecayRule:
                continue
            if not hasattr(obj, "check") or not hasattr(obj, "name"):
                continue
            if obj.__module__ != module.__name__:
                continue  # skip imports
            try:
                rules.append(obj())
            except TypeError:
                pass
    return rules
```

- [ ] **Step 4: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_rule_engine.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/ \
        naturesseed-content-pipeline/tests/audit/test_rule_engine.py
git commit -m "feat(audit): rule engine protocol + directory discovery"
```

---

## Task 16: DiscontinuedProductRule

**Files:**
- Create: `src/naturesseed_pipeline/audit_rules/discontinued_product.py`
- Test: `tests/audit/test_rule_discontinued_product.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_rule_discontinued_product.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.discontinued_product import DiscontinuedProductRule
from naturesseed_pipeline.db.models import (
    Base, ContentInventory, OrphanReference,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_fires_on_inactive_product_orphan_ref():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OrphanReference(
        content_inventory_id=c.id,
        reference_type="inactive_product",
        reference_value="old-mix",
        match_confidence=0.95, snippet="...Old Mix...", status="flagged",
    ))
    s.commit()

    ctx = AuditContext(session=s, current_shipping="")
    findings = DiscontinuedProductRule().check(c, ctx)
    assert len(findings) == 1
    assert findings[0].rule_name == "DiscontinuedProductRule"
    assert findings[0].severity == "critical"
    assert "old-mix" in findings[0].suggested_action


def test_silent_when_no_orphan_refs():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.commit()
    ctx = AuditContext(session=s, current_shipping="")
    assert DiscontinuedProductRule().check(c, ctx) == []
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_rule_discontinued_product.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement rule**

Create `src/naturesseed_pipeline/audit_rules/discontinued_product.py`:

```python
"""Rule #1 — article mentions a product with WC status='draft'."""

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import OrphanReference


class DiscontinuedProductRule:
    name = "DiscontinuedProductRule"
    severity = "critical"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        rows = ctx.session.execute(
            select(OrphanReference).where(
                OrphanReference.content_inventory_id == content.id,
                OrphanReference.reference_type == "inactive_product",
                OrphanReference.status == "flagged",
            )
        ).scalars().all()
        return [
            Finding(
                rule_name=self.name, severity=self.severity,
                snippet=r.snippet or "",
                suggested_action=(
                    f"Replace mention of '{r.reference_value}' with a "
                    f"currently-sold product or remove section"
                ),
            )
            for r in rows
        ]
```

- [ ] **Step 4: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_rule_discontinued_product.py -v
```

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/discontinued_product.py \
        naturesseed-content-pipeline/tests/audit/test_rule_discontinued_product.py
git commit -m "feat(audit): DiscontinuedProductRule"
```

---

## Task 17: DiscontinuedSpeciesRule

**Files:**
- Create: `src/naturesseed_pipeline/audit_rules/discontinued_species.py`
- Test: `tests/audit/test_rule_discontinued_species.py` (create)

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_rule_discontinued_species.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.discontinued_species import DiscontinuedSpeciesRule
from naturesseed_pipeline.db.models import (
    Base, ContentInventory, OrphanReference, WcCatalogSnapshot,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_fires_on_species_not_in_any_publish_product():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="m", name="M", status="publish",
                           species_list=["fescue"], permalink=""))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OrphanReference(content_inventory_id=c.id,
                         reference_type="species_mention",
                         reference_value="alfalfa",
                         match_confidence=1.0, snippet="...alfalfa...",
                         status="flagged"))
    s.commit()

    findings = DiscontinuedSpeciesRule().check(c, AuditContext(session=s, current_shipping=""))
    assert len(findings) == 1
    assert findings[0].severity == "critical"


def test_silent_when_species_exists_in_active():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="m", name="M", status="publish",
                           species_list=["fescue"], permalink=""))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OrphanReference(content_inventory_id=c.id,
                         reference_type="species_mention",
                         reference_value="fescue",
                         match_confidence=1.0, snippet="...fescue...",
                         status="flagged"))
    s.commit()
    assert DiscontinuedSpeciesRule().check(c, AuditContext(session=s, current_shipping="")) == []
```

- [ ] **Step 2: Run test (expect fail) → Implement → Pass → Commit**

Create `src/naturesseed_pipeline/audit_rules/discontinued_species.py`:

```python
"""Rule #2 — species mentioned but not in any publish-status product."""

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import OrphanReference, WcCatalogSnapshot


class DiscontinuedSpeciesRule:
    name = "DiscontinuedSpeciesRule"
    severity = "critical"

    def _active_species(self, ctx: AuditContext) -> set[str]:
        def build():
            active = ctx.session.execute(
                select(WcCatalogSnapshot).where(WcCatalogSnapshot.status == "publish")
            ).scalars().all()
            out: set[str] = set()
            for p in active:
                for sp in p.species_list or []:
                    out.add(sp.strip().lower())
            return out
        return ctx.cached("active_species", build)

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        active = self._active_species(ctx)
        rows = ctx.session.execute(
            select(OrphanReference).where(
                OrphanReference.content_inventory_id == content.id,
                OrphanReference.reference_type == "species_mention",
                OrphanReference.status == "flagged",
            )
        ).scalars().all()
        findings: list[Finding] = []
        for r in rows:
            if r.reference_value.strip().lower() in active:
                continue
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet=r.snippet or "",
                suggested_action=(
                    f"Species '{r.reference_value}' is not sold in any active product — "
                    f"remove mention or update to a currently-carried species"
                ),
            ))
        return findings
```

Run tests, commit:

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_rule_discontinued_species.py -v
git add naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/discontinued_species.py \
        naturesseed-content-pipeline/tests/audit/test_rule_discontinued_species.py
git commit -m "feat(audit): DiscontinuedSpeciesRule"
```

---

## Task 18: MissingProductCardRule

**Files:**
- Create: `src/naturesseed_pipeline/audit_rules/missing_product_card.py`
- Test: `tests/audit/test_rule_missing_product_card.py`

- [ ] **Step 1: Write failing test**

```python
# tests/audit/test_rule_missing_product_card.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.missing_product_card import MissingProductCardRule
from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentProductMention, OutboundLink, WcCatalogSnapshot,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_fires_when_product_mentioned_but_not_linked():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="foo", name="Foo",
                           status="publish",
                           permalink="https://naturesseed.com/products/foo/"))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(ContentProductMention(content_inventory_id=c.id, wp_product_id=1,
                               product_slug="foo", product_name="Foo",
                               match_type="exact", confidence=0.9))
    s.commit()
    ctx = AuditContext(session=s, current_shipping="")
    assert len(MissingProductCardRule().check(c, ctx)) == 1


def test_silent_when_product_is_linked():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="foo", name="Foo",
                           status="publish",
                           permalink="https://naturesseed.com/products/foo/"))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(ContentProductMention(content_inventory_id=c.id, wp_product_id=1,
                               product_slug="foo", product_name="Foo",
                               match_type="exact", confidence=0.9))
    s.add(OutboundLink(content_inventory_id=c.id,
                      href="https://naturesseed.com/products/foo/",
                      link_type="internal_product"))
    s.commit()
    ctx = AuditContext(session=s, current_shipping="")
    assert MissingProductCardRule().check(c, ctx) == []
```

- [ ] **Step 2-5: Run fail → Implement → Pass → Commit**

```python
# src/naturesseed_pipeline/audit_rules/missing_product_card.py
"""Rule #3 — article mentions an active product but has no link to it."""

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import (
    ContentProductMention, OutboundLink, WcCatalogSnapshot,
)


class MissingProductCardRule:
    name = "MissingProductCardRule"
    severity = "warning"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        mentions = ctx.session.execute(
            select(ContentProductMention).where(
                ContentProductMention.content_inventory_id == content.id
            )
        ).scalars().all()
        if not mentions:
            return []

        links = ctx.session.execute(
            select(OutboundLink).where(
                OutboundLink.content_inventory_id == content.id,
                OutboundLink.link_type == "internal_product",
            )
        ).scalars().all()
        linked_slugs = set()
        for link in links:
            # /products/<slug>/ path extraction
            parts = [p for p in (link.href or "").split("/") if p]
            if parts:
                linked_slugs.add(parts[-1].lower())

        findings: list[Finding] = []
        for m in mentions:
            if m.product_slug.lower() in linked_slugs:
                continue
            snap = ctx.session.get(WcCatalogSnapshot, m.wp_product_id)
            permalink = snap.permalink if snap else f"/products/{m.product_slug}/"
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet=m.first_snippet or "",
                suggested_action=f"Add a product card or CTA linking to {permalink}",
            ))
        return findings
```

Run + commit:

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_rule_missing_product_card.py -v
git add naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/missing_product_card.py \
        naturesseed-content-pipeline/tests/audit/test_rule_missing_product_card.py
git commit -m "feat(audit): MissingProductCardRule"
```

---

## Task 19: Dead Link Rules (External + Internal + Product Category)

**Files:**
- Create: `src/naturesseed_pipeline/audit_rules/dead_external_link.py`
- Create: `src/naturesseed_pipeline/audit_rules/dead_internal_link.py`
- Create: `src/naturesseed_pipeline/audit_rules/product_category_url.py`
- Test: `tests/audit/test_rule_dead_links.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/audit/test_rule_dead_links.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.dead_external_link import DeadExternalLinkRule
from naturesseed_pipeline.audit_rules.dead_internal_link import DeadInternalLinkRule
from naturesseed_pipeline.audit_rules.product_category_url import ProductCategoryUrlRule
from naturesseed_pipeline.db.models import Base, ContentInventory, OutboundLink


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_dead_external_fires_on_404():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OutboundLink(content_inventory_id=c.id, href="https://dead.com",
                      link_type="external", http_status=404))
    s.commit()
    findings = DeadExternalLinkRule().check(c, AuditContext(session=s, current_shipping=""))
    assert len(findings) == 1


def test_dead_external_silent_on_200():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OutboundLink(content_inventory_id=c.id, href="https://ok.com",
                      link_type="external", http_status=200))
    s.commit()
    assert DeadExternalLinkRule().check(c, AuditContext(session=s, current_shipping="")) == []


def test_dead_internal_fires_when_target_missing():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OutboundLink(content_inventory_id=c.id,
                      href="https://naturesseed.com/gone/",
                      link_type="internal_content", target_content_id=None))
    s.commit()
    assert len(DeadInternalLinkRule().check(c, AuditContext(session=s, current_shipping=""))) == 1


def test_dead_internal_fires_when_target_is_draft():
    s = _session()
    tgt = ContentInventory(url="https://x/b", title="B", slug="b", post_type="post",
                          status="draft")
    src = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add_all([src, tgt]); s.flush()
    s.add(OutboundLink(content_inventory_id=src.id,
                      href="https://naturesseed.com/b/",
                      link_type="internal_content", target_content_id=tgt.id))
    s.commit()
    assert len(DeadInternalLinkRule().check(src, AuditContext(session=s, current_shipping=""))) == 1


def test_product_category_url_rule():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.flush()
    s.add(OutboundLink(content_inventory_id=c.id,
                      href="https://naturesseed.com/product-category/grass-seed/",
                      link_type="internal_content"))
    s.commit()
    findings = ProductCategoryUrlRule().check(c, AuditContext(session=s, current_shipping=""))
    assert len(findings) == 1
    assert findings[0].severity == "critical"
```

- [ ] **Step 2: Implementation**

```python
# src/naturesseed_pipeline/audit_rules/dead_external_link.py
"""Rule #4 — outbound external links returning 4xx/5xx."""

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import OutboundLink


class DeadExternalLinkRule:
    name = "DeadExternalLinkRule"
    severity = "warning"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        rows = ctx.session.execute(
            select(OutboundLink).where(
                OutboundLink.content_inventory_id == content.id,
                OutboundLink.link_type == "external",
                OutboundLink.http_status.isnot(None),
            )
        ).scalars().all()
        findings: list[Finding] = []
        for r in rows:
            if r.http_status in (200, 301, 302, 303, 304, 307, 308) or r.http_status is None:
                continue
            if r.http_status >= 400 or r.http_status == 0:
                findings.append(Finding(
                    rule_name=self.name, severity=self.severity,
                    snippet=f"{r.href} → HTTP {r.http_status}",
                    suggested_action=f"Remove or replace dead link to {r.href}",
                ))
        return findings
```

```python
# src/naturesseed_pipeline/audit_rules/dead_internal_link.py
"""Rule #5 — outbound internal links whose target is missing or not publish."""

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import ContentInventory, OutboundLink


class DeadInternalLinkRule:
    name = "DeadInternalLinkRule"
    severity = "critical"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        rows = ctx.session.execute(
            select(OutboundLink).where(
                OutboundLink.content_inventory_id == content.id,
                OutboundLink.link_type.in_(["internal_content", "internal_product"]),
            )
        ).scalars().all()
        findings: list[Finding] = []
        for r in rows:
            broken = False
            if r.target_content_id is None:
                broken = True
            else:
                tgt = ctx.session.get(ContentInventory, r.target_content_id)
                if tgt is None or tgt.status != "publish":
                    broken = True
            if broken:
                findings.append(Finding(
                    rule_name=self.name, severity=self.severity,
                    snippet=r.href,
                    suggested_action=f"Fix or remove broken internal link to {r.href}",
                ))
        return findings
```

```python
# src/naturesseed_pipeline/audit_rules/product_category_url.py
"""Rule #12 — /product-category/ URLs should be /products/."""

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import OutboundLink


class ProductCategoryUrlRule:
    name = "ProductCategoryUrlRule"
    severity = "critical"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        rows = ctx.session.execute(
            select(OutboundLink).where(
                OutboundLink.content_inventory_id == content.id,
                OutboundLink.href.like("%/product-category/%"),
            )
        ).scalars().all()
        return [
            Finding(
                rule_name=self.name, severity=self.severity,
                snippet=r.href,
                suggested_action=(
                    f"Rewrite URL from /product-category/... to /products/... "
                    f"(Permalink Manager mapping). Source: {r.href}"
                ),
            )
            for r in rows
        ]
```

- [ ] **Step 3: Run + commit**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_rule_dead_links.py -v
git add naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/dead_external_link.py \
        naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/dead_internal_link.py \
        naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/product_category_url.py \
        naturesseed-content-pipeline/tests/audit/test_rule_dead_links.py
git commit -m "feat(audit): dead link + product-category URL rules"
```

---

## Task 20: Content-Text Rules (StaleDate, ThinContent, SchemaGap)

**Files:**
- Create: `src/naturesseed_pipeline/audit_rules/stale_date.py`
- Create: `src/naturesseed_pipeline/audit_rules/thin_content.py`
- Create: `src/naturesseed_pipeline/audit_rules/schema_gap.py`
- Test: `tests/audit/test_rule_content_text.py`

- [ ] **Step 1: Write failing test**

```python
# tests/audit/test_rule_content_text.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.stale_date import StaleDateRule
from naturesseed_pipeline.audit_rules.thin_content import ThinContentRule
from naturesseed_pipeline.audit_rules.schema_gap import SchemaGapRule
from naturesseed_pipeline.db.models import Base, ContentInventory


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_stale_date_fires_on_old_year():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="In 2019, the market was different.")
    s.add(c); s.commit()
    assert len(StaleDateRule().check(c, AuditContext(session=s, current_shipping=""))) >= 1


def test_stale_date_silent_on_recent_year():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="Updated in 2026 per latest USDA guidance.")
    s.add(c); s.commit()
    assert StaleDateRule().check(c, AuditContext(session=s, current_shipping="")) == []


def test_thin_content_fires_below_threshold():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        word_count=50)
    s.add(c); s.commit()
    ctx = AuditContext(session=s, current_shipping="")
    ctx._cache["thin_word_count"] = 300
    assert len(ThinContentRule().check(c, ctx)) == 1


def test_thin_content_silent_above():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        word_count=1000)
    s.add(c); s.commit()
    ctx = AuditContext(session=s, current_shipping="")
    ctx._cache["thin_word_count"] = 300
    assert ThinContentRule().check(c, ctx) == []


def test_schema_gap_fires_when_h1_missing():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_html="<div>no h1</div>", target_keyword=None)
    s.add(c); s.commit()
    findings = SchemaGapRule().check(c, AuditContext(session=s, current_shipping=""))
    assert len(findings) >= 2  # missing h1 + missing target keyword
```

- [ ] **Step 2: Implementation**

```python
# src/naturesseed_pipeline/audit_rules/stale_date.py
"""Rule #6 — article mentions pre-2023 calendar years.

Flags standalone year tokens `\b(19\d{2}|20[0-1]\d|202[0-2])\b`.
"""

import re

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding

_YEAR_PATTERN = re.compile(r"\b(19\d{2}|20[0-1]\d|202[0-2])\b")


class StaleDateRule:
    name = "StaleDateRule"
    severity = "warning"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        text = content.content_text or ""
        findings: list[Finding] = []
        seen_years: set[str] = set()
        for m in _YEAR_PATTERN.finditer(text):
            year = m.group(1)
            if year in seen_years:
                continue
            seen_years.add(year)
            lo = max(0, m.start() - 60); hi = min(len(text), m.end() + 60)
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet=text[lo:hi],
                suggested_action=f"Reference to {year} may be stale — verify and update",
            ))
        return findings
```

```python
# src/naturesseed_pipeline/audit_rules/thin_content.py
"""Rule #10 — word_count below configurable threshold."""

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding


class ThinContentRule:
    name = "ThinContentRule"
    severity = "info"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        threshold = ctx._cache.get("thin_word_count", 300)
        wc = content.word_count or 0
        if wc >= threshold:
            return []
        return [Finding(
            rule_name=self.name, severity=self.severity,
            snippet=f"word_count={wc}",
            suggested_action=f"Expand content above {threshold} words for SEO depth",
        )]
```

```python
# src/naturesseed_pipeline/audit_rules/schema_gap.py
"""Rule #11 — missing H1, target keyword, or JSON-LD schema markup."""

import re

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding

_H1_PATTERN = re.compile(r"<h1[^>]*>", re.IGNORECASE)
_JSONLD_PATTERN = re.compile(r'<script[^>]+type="application/ld\+json"', re.IGNORECASE)


class SchemaGapRule:
    name = "SchemaGapRule"
    severity = "info"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        findings: list[Finding] = []
        html = content.content_html or ""
        if not _H1_PATTERN.search(html):
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet="No <h1> tag found",
                suggested_action="Add an H1 heading that includes the target keyword",
            ))
        if not (content.target_keyword or "").strip():
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet="target_keyword is empty",
                suggested_action="Set a target keyword for this article",
            ))
        if not _JSONLD_PATTERN.search(html):
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet="No JSON-LD structured data",
                suggested_action="Add Article or HowTo JSON-LD schema markup",
            ))
        return findings
```

- [ ] **Step 3: Run + commit**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_rule_content_text.py -v
git add naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/stale_date.py \
        naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/thin_content.py \
        naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/schema_gap.py \
        naturesseed-content-pipeline/tests/audit/test_rule_content_text.py
git commit -m "feat(audit): stale date + thin content + schema gap rules"
```

---

## Task 21: OutdatedPricingRule

**Files:**
- Create: `src/naturesseed_pipeline/audit_rules/outdated_pricing.py`
- Test: `tests/audit/test_rule_outdated_pricing.py`

- [ ] **Step 1: Write failing test**

```python
# tests/audit/test_rule_outdated_pricing.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.outdated_pricing import OutdatedPricingRule
from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentProductMention, WcCatalogSnapshot,
)


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_fires_when_price_differs_over_5_percent():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="x", name="X", status="publish",
                           price=50.00, permalink=""))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="Our product X is only $35.99 today!")
    s.add(c); s.flush()
    s.add(ContentProductMention(content_inventory_id=c.id, wp_product_id=1,
                               product_slug="x", product_name="X",
                               match_type="exact", confidence=0.9))
    s.commit()
    findings = OutdatedPricingRule().check(c, AuditContext(session=s, current_shipping=""))
    assert len(findings) >= 1


def test_silent_when_price_within_5_percent():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="x", name="X", status="publish",
                           price=50.00, permalink=""))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="X is only $49.99 today!")
    s.add(c); s.flush()
    s.add(ContentProductMention(content_inventory_id=c.id, wp_product_id=1,
                               product_slug="x", product_name="X",
                               match_type="exact", confidence=0.9))
    s.commit()
    assert OutdatedPricingRule().check(c, AuditContext(session=s, current_shipping="")) == []


def test_silent_when_no_dollar_amount():
    s = _session()
    s.add(WcCatalogSnapshot(wp_product_id=1, slug="x", name="X", status="publish",
                           price=50.00, permalink=""))
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="X is a great product.")
    s.add(c); s.flush()
    s.add(ContentProductMention(content_inventory_id=c.id, wp_product_id=1,
                               product_slug="x", product_name="X",
                               match_type="exact", confidence=0.9))
    s.commit()
    assert OutdatedPricingRule().check(c, AuditContext(session=s, current_shipping="")) == []
```

- [ ] **Step 2: Implementation**

```python
# src/naturesseed_pipeline/audit_rules/outdated_pricing.py
"""Rule #9 — article mentions a price for a product that drifts >5% from current."""

import re

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import ContentProductMention, WcCatalogSnapshot

_PRICE_PATTERN = re.compile(r"\$\s?(\d{1,5}(?:\.\d{2})?)")


class OutdatedPricingRule:
    name = "OutdatedPricingRule"
    severity = "info"

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        text = content.content_text or ""
        if "$" not in text:
            return []
        mentions = ctx.session.execute(
            select(ContentProductMention).where(
                ContentProductMention.content_inventory_id == content.id
            )
        ).scalars().all()
        if not mentions:
            return []

        prices_in_text = [float(m.group(1)) for m in _PRICE_PATTERN.finditer(text)]
        if not prices_in_text:
            return []

        findings: list[Finding] = []
        for m in mentions:
            snap = ctx.session.get(WcCatalogSnapshot, m.wp_product_id)
            if not snap or not snap.price:
                continue
            current = snap.price
            drift = [
                p for p in prices_in_text
                if abs(p - current) / current > 0.05
            ]
            if drift:
                findings.append(Finding(
                    rule_name=self.name, severity=self.severity,
                    snippet=f"text prices {drift} vs current {current}",
                    suggested_action=(
                        f"Verify/update price for {m.product_name} "
                        f"(current: ${current:.2f})"
                    ),
                ))
        return findings
```

- [ ] **Step 3: Run + commit**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_rule_outdated_pricing.py -v
git add naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/outdated_pricing.py \
        naturesseed-content-pipeline/tests/audit/test_rule_outdated_pricing.py
git commit -m "feat(audit): OutdatedPricingRule"
```

---

## Task 22: UsdaZoneMapRule (LLM-Assisted)

**Files:**
- Create: `src/naturesseed_pipeline/audit_rules/usda_zone_map.py`
- Test: `tests/audit/test_rule_usda_zone_map.py`

- [ ] **Step 1: Write failing test**

```python
# tests/audit/test_rule_usda_zone_map.py
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.usda_zone_map import UsdaZoneMapRule
from naturesseed_pipeline.db.models import Base, ContentInventory


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_fires_when_regex_matches_and_llm_confirms():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="Use the 2012 USDA plant hardiness zone map to decide.")
    s.add(c); s.commit()
    # Mock LLM to say "yes, pre-2023 reference"
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='[{"snippet": "2012 USDA plant hardiness zone map",'
                                '"is_outdated": true, "reason": "references old map"}]')]
    )
    ctx = AuditContext(session=s, current_shipping="", llm_client=mock_client)
    findings = UsdaZoneMapRule().check(c, ctx)
    assert len(findings) == 1


def test_silent_when_no_regex_match():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="Nothing related here.")
    s.add(c); s.commit()
    ctx = AuditContext(session=s, current_shipping="", llm_client=MagicMock())
    assert UsdaZoneMapRule().check(c, ctx) == []


def test_silent_when_regex_matches_but_llm_says_current():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="See the USDA plant hardiness zone map (2023 update).")
    s.add(c); s.commit()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='[{"snippet": "USDA plant hardiness zone map (2023 update)",'
                                '"is_outdated": false}]')]
    )
    ctx = AuditContext(session=s, current_shipping="", llm_client=mock_client)
    assert UsdaZoneMapRule().check(c, ctx) == []
```

- [ ] **Step 2: Implementation**

```python
# src/naturesseed_pipeline/audit_rules/usda_zone_map.py
"""Rule #7 — references to pre-2023 USDA hardiness zone map.

Two-stage: regex filter → LLM judge.
"""

import json
import re

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding

_FILTER_PATTERN = re.compile(
    r"(hardiness zone map|USDA\s+(?:plant\s+)?map|USDA.*(?:2012|pre.?2023))",
    re.IGNORECASE,
)


class UsdaZoneMapRule:
    name = "UsdaZoneMapRule"
    severity = "warning"

    def _extract_candidates(self, text: str, ctx_chars: int = 200) -> list[str]:
        out: list[str] = []
        for m in _FILTER_PATTERN.finditer(text):
            lo = max(0, m.start() - ctx_chars); hi = min(len(text), m.end() + ctx_chars)
            out.append(text[lo:hi])
        return out

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        text = content.content_text or ""
        candidates = self._extract_candidates(text)
        if not candidates:
            return []
        if ctx.llm_client is None or ctx.llm_token_budget_remaining <= 0:
            return []

        prompt = (
            "For each snippet below, determine whether it references the "
            "pre-2023 USDA plant hardiness zone map (outdated) or the 2023-updated "
            "version (current). Return a JSON array with keys: snippet, is_outdated, reason.\n\n"
            + "\n---\n".join(f"[{i}] {c}" for i, c in enumerate(candidates))
        )
        resp = ctx.llm_client.messages.create(
            model=ctx.llm_model, max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            if raw.endswith("```"):
                raw = raw[:-3]
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []

        findings: list[Finding] = []
        for item in parsed:
            if not item.get("is_outdated"):
                continue
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet=item.get("snippet", "")[:300],
                suggested_action=(
                    "Update USDA zone map reference to the 2023 version. "
                    f"Reason: {item.get('reason', '')}"
                ),
            ))
        return findings
```

- [ ] **Step 3: Run + commit**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_rule_usda_zone_map.py -v
git add naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/usda_zone_map.py \
        naturesseed-content-pipeline/tests/audit/test_rule_usda_zone_map.py
git commit -m "feat(audit): UsdaZoneMapRule (LLM-assisted)"
```

---

## Task 23: OutdatedShippingRule (LLM-Assisted)

**Files:**
- Create: `src/naturesseed_pipeline/audit_rules/outdated_shipping.py`
- Test: `tests/audit/test_rule_outdated_shipping.py`

- [ ] **Step 1: Write failing test**

```python
# tests/audit/test_rule_outdated_shipping.py
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext
from naturesseed_pipeline.audit_rules.outdated_shipping import OutdatedShippingRule
from naturesseed_pipeline.db.models import Base, ContentInventory


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_fires_when_filter_hits_and_llm_confirms():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="Free shipping on orders over $49!")
    s.add(c); s.commit()
    mock = MagicMock()
    mock.messages.create.return_value = MagicMock(
        content=[MagicMock(text='[{"snippet": "Free shipping on orders over $49",'
                                '"is_outdated": true, "reason": "current threshold is $99"}]')]
    )
    ctx = AuditContext(session=s, current_shipping="Free shipping over $99",
                       llm_client=mock)
    assert len(OutdatedShippingRule().check(c, ctx)) == 1


def test_silent_when_no_filter_hit():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post",
                        content_text="Pure content, no shipping.")
    s.add(c); s.commit()
    ctx = AuditContext(session=s, current_shipping="Free shipping over $99",
                       llm_client=MagicMock())
    assert OutdatedShippingRule().check(c, ctx) == []
```

- [ ] **Step 2: Implementation**

```python
# src/naturesseed_pipeline/audit_rules/outdated_shipping.py
"""Rule #8 — shipping claims that don't match current policy.

Two-stage: regex filter → LLM judge vs current_shipping from config.
"""

import json
import re

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding

_FILTER_PATTERN = re.compile(
    r"(free shipping|ships? in \d+\s*(?:day|business)|"
    r"\$\d{1,3}\s+(?:shipping|threshold|minimum)|"
    r"\b(?:UPS|FedEx|USPS)\b)",
    re.IGNORECASE,
)


class OutdatedShippingRule:
    name = "OutdatedShippingRule"
    severity = "warning"

    def _extract_candidates(self, text: str, ctx_chars: int = 150) -> list[str]:
        out: list[str] = []
        for m in _FILTER_PATTERN.finditer(text):
            lo = max(0, m.start() - ctx_chars); hi = min(len(text), m.end() + ctx_chars)
            out.append(text[lo:hi])
        return out

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        text = content.content_text or ""
        candidates = self._extract_candidates(text)
        if not candidates or ctx.llm_client is None:
            return []

        prompt = (
            f"Current Nature's Seed shipping policy: {ctx.current_shipping}\n\n"
            "For each snippet, determine whether the shipping claim matches "
            "the current policy. Return JSON array with keys: snippet, is_outdated, reason.\n\n"
            + "\n---\n".join(f"[{i}] {c}" for i, c in enumerate(candidates))
        )
        resp = ctx.llm_client.messages.create(
            model=ctx.llm_model, max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            if raw.endswith("```"):
                raw = raw[:-3]
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []

        findings: list[Finding] = []
        for item in parsed:
            if not item.get("is_outdated"):
                continue
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet=item.get("snippet", "")[:300],
                suggested_action=(
                    f"Update shipping claim to match current policy. "
                    f"Reason: {item.get('reason', '')}"
                ),
            ))
        return findings
```

- [ ] **Step 3: Run + commit**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_rule_outdated_shipping.py -v
git add naturesseed-content-pipeline/src/naturesseed_pipeline/audit_rules/outdated_shipping.py \
        naturesseed-content-pipeline/tests/audit/test_rule_outdated_shipping.py
git commit -m "feat(audit): OutdatedShippingRule (LLM-assisted)"
```

---

## Task 24: `scan-decay` Stage Orchestrator

Runs every rule, reconciles stale-vs-open findings, populates `refresh_queue` summary.

**Files:**
- Create: `src/naturesseed_pipeline/pipelines/audit/scan_decay.py`
- Test: `tests/audit/test_scan_decay.py`

- [ ] **Step 1: Write failing test**

```python
# tests/audit/test_scan_decay.py
import hashlib
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext, DecayRule, Finding
from naturesseed_pipeline.db.models import (
    Base, ContentInventory, DecayFinding, RefreshQueue,
)
from naturesseed_pipeline.pipelines.audit.scan_decay import run_scan_decay


class AlwaysFiresRule:
    name = "AlwaysFires"
    severity = "warning"

    def check(self, content, ctx):
        return [Finding(rule_name=self.name, severity=self.severity,
                        snippet="fires", suggested_action="fix it")]


class NeverFiresRule:
    name = "NeverFires"
    severity = "info"

    def check(self, content, ctx): return []


def _session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_scan_decay_creates_findings_and_refresh_row():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.commit()

    counts = run_scan_decay(s, rules=[AlwaysFiresRule()], current_shipping="",
                            llm_client=None)
    s.commit()

    findings = s.execute(select(DecayFinding)).scalars().all()
    assert len(findings) == 1 and findings[0].status == "open"
    refresh = s.execute(select(RefreshQueue)).scalars().all()
    assert len(refresh) == 1 and "AlwaysFires" in refresh[0].reason


def test_scan_decay_reconciles_stale_to_resolved():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.commit()

    # First run: AlwaysFires fires
    run_scan_decay(s, rules=[AlwaysFiresRule()], current_shipping="", llm_client=None)
    s.commit()
    # Second run: only NeverFires runs → prior finding becomes stale → resolved
    run_scan_decay(s, rules=[NeverFiresRule()], current_shipping="", llm_client=None)
    s.commit()

    findings = s.execute(select(DecayFinding)).scalars().all()
    assert len(findings) == 1
    assert findings[0].status == "resolved"
    assert findings[0].resolved_at is not None

    refresh = s.execute(select(RefreshQueue)).scalars().all()
    assert len(refresh) == 0


def test_scan_decay_idempotent_same_rule_same_run():
    s = _session()
    c = ContentInventory(url="https://x/a", title="A", slug="a", post_type="post")
    s.add(c); s.commit()
    run_scan_decay(s, rules=[AlwaysFiresRule()], current_shipping="", llm_client=None); s.commit()
    run_scan_decay(s, rules=[AlwaysFiresRule()], current_shipping="", llm_client=None); s.commit()
    findings = s.execute(select(DecayFinding)).scalars().all()
    assert len(findings) == 1  # deduped on (content, rule, snippet_hash)
```

- [ ] **Step 2: Implementation**

Create `src/naturesseed_pipeline/pipelines/audit/scan_decay.py`:

```python
"""Scan-decay stage — runs all rules, reconciles stale findings,
summarizes open findings into refresh_queue."""

import hashlib
from datetime import datetime, timezone
from typing import Sequence

import structlog
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext, DecayRule, Finding
from naturesseed_pipeline.db.models import ContentInventory, DecayFinding, RefreshQueue

log = structlog.get_logger()


def _snippet_hash(snippet: str) -> str:
    return hashlib.sha256(snippet.encode("utf-8")).hexdigest()[:16]


def run_scan_decay(
    session: Session,
    rules: Sequence[DecayRule],
    current_shipping: str,
    llm_client,
    llm_model: str = "claude-sonnet-4-6",
    llm_token_budget: int = 50_000,
    only_article_id: int | None = None,
    only_rule_name: str | None = None,
) -> dict[str, int]:
    """Run all decay rules. Mark prior open findings stale, rewrite or resolve them,
    then rebuild refresh_queue."""
    if only_rule_name:
        rules = [r for r in rules if r.name == only_rule_name]

    # Step 1: stale-out existing open findings
    session.execute(
        update(DecayFinding)
        .where(DecayFinding.status == "open")
        .values(status="stale")
    )
    session.flush()

    ctx = AuditContext(
        session=session, current_shipping=current_shipping,
        llm_client=llm_client, llm_model=llm_model,
        llm_token_budget_remaining=llm_token_budget,
    )
    # Share thin-content threshold through cache for ThinContentRule
    from naturesseed_pipeline.config import settings
    ctx._cache["thin_word_count"] = settings.audit_thin_word_count

    # Step 2: run rules
    content_q = select(ContentInventory)
    if only_article_id:
        content_q = content_q.where(ContentInventory.id == only_article_id)
    articles = session.execute(content_q).scalars().all()

    counts = {"findings_open": 0, "findings_reopened": 0, "findings_new": 0}

    for article in articles:
        for rule in rules:
            try:
                findings = rule.check(article, ctx)
            except Exception as e:
                log.error("rule.error", rule=rule.name, article=article.id, error=str(e))
                continue

            for f in findings:
                sh = _snippet_hash(f.snippet)
                existing = session.execute(
                    select(DecayFinding).where(
                        DecayFinding.content_inventory_id == article.id,
                        DecayFinding.rule_name == f.rule_name,
                    )
                ).scalars().all()
                match = next((e for e in existing
                              if _snippet_hash(e.snippet or "") == sh), None)
                if match is None:
                    session.add(DecayFinding(
                        content_inventory_id=article.id,
                        rule_name=f.rule_name, severity=f.severity,
                        snippet=f.snippet, suggested_action=f.suggested_action,
                        status="open",
                    ))
                    counts["findings_new"] += 1
                else:
                    match.status = "open"
                    match.suggested_action = f.suggested_action
                    match.detected_at = datetime.now(timezone.utc)
                    match.resolved_at = None
                    counts["findings_reopened"] += 1
        session.flush()

    # Step 3: stale → resolved
    now = datetime.now(timezone.utc)
    stale = session.execute(
        select(DecayFinding).where(DecayFinding.status == "stale")
    ).scalars().all()
    for f in stale:
        f.status = "resolved"
        f.resolved_at = now
    session.flush()

    # Step 4: rebuild refresh_queue from open findings
    session.execute(delete(RefreshQueue).where(RefreshQueue.status == "pending"))
    open_findings = session.execute(
        select(DecayFinding).where(DecayFinding.status == "open")
    ).scalars().all()
    by_content: dict[int, list[DecayFinding]] = {}
    for f in open_findings:
        by_content.setdefault(f.content_inventory_id, []).append(f)

    for cid, flist in by_content.items():
        rule_names = sorted({f.rule_name for f in flist})
        session.add(RefreshQueue(
            content_inventory_id=cid,
            reason=f"{len(flist)} decay findings: " + ", ".join(rule_names),
            status="pending",
        ))

    counts["findings_open"] = len(open_findings)
    log.info("audit.scan_decay.done", **counts)
    return counts
```

- [ ] **Step 3: Run + commit**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_scan_decay.py -v
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/scan_decay.py \
        naturesseed-content-pipeline/tests/audit/test_scan_decay.py
git commit -m "feat(audit): scan-decay orchestrator with stale reconciliation"
```

---

## Task 25: Report Builders — Topic Map + Per-Article

**Files:**
- Create: `src/naturesseed_pipeline/pipelines/audit/report.py`
- Test: `tests/audit/test_report.py`

- [ ] **Step 1: Write failing test**

```python
# tests/audit/test_report.py
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentTopic, ContentProductMention,
    DecayFinding, OutboundLink, Topic,
)
from naturesseed_pipeline.pipelines.audit.report import (
    generate_topic_map, generate_per_article, generate_internal_linking,
    generate_summary, run_report,
)


def _seeded_session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    s = Session(eng)
    top = Topic(name="Grass Seed", slug="grass-seed", source="wc_category", approved=1)
    s.add(top); s.flush()
    sub = Topic(name="Cool-Season", slug="cool-season", parent_topic_id=top.id,
               source="llm_proposed", approved=1)
    s.add(sub); s.flush()

    a1 = ContentInventory(wp_post_id=1, url="https://naturesseed.com/a/",
                         title="Article A", slug="a", post_type="post",
                         word_count=500, status="publish")
    a2 = ContentInventory(wp_post_id=2, url="https://naturesseed.com/b/",
                         title="Article B", slug="b", post_type="post",
                         word_count=200, status="publish")
    s.add_all([a1, a2]); s.flush()
    s.add_all([
        ContentTopic(content_inventory_id=a1.id, topic_id=top.id,
                    assigned_by="auto", confidence=1.0),
        ContentTopic(content_inventory_id=a1.id, topic_id=sub.id,
                    assigned_by="auto", confidence=0.8),
        ContentTopic(content_inventory_id=a2.id, topic_id=top.id,
                    assigned_by="auto", confidence=1.0),
    ])
    s.add(ContentProductMention(content_inventory_id=a1.id, wp_product_id=1,
                               product_slug="foo", product_name="Foo",
                               match_type="exact", confidence=0.9))
    s.add(DecayFinding(content_inventory_id=a2.id, rule_name="ThinContentRule",
                      severity="info", snippet="word_count=200",
                      suggested_action="expand", status="open"))
    s.add(OutboundLink(content_inventory_id=a1.id,
                      href="https://naturesseed.com/b/",
                      anchor_text="B", link_type="internal_content",
                      target_content_id=a2.id))
    s.commit()
    return s


def test_topic_map_contains_topics_and_articles():
    s = _seeded_session()
    md = generate_topic_map(s)
    assert "Grass Seed" in md
    assert "Cool-Season" in md
    assert "Article A" in md and "Article B" in md


def test_per_article_lists_findings_and_products():
    s = _seeded_session()
    md = generate_per_article(s)
    assert "Foo" in md
    assert "ThinContentRule" in md


def test_internal_linking_shows_edges():
    s = _seeded_session()
    md = generate_internal_linking(s)
    assert "Article A" in md and "Article B" in md


def test_summary_counts_present():
    s = _seeded_session()
    md = generate_summary(s)
    assert "Articles" in md or "articles" in md


def test_run_report_writes_all_files(tmp_path: Path):
    s = _seeded_session()
    out_dir = run_report(s, out_root=tmp_path, date_str="2026-04-24")
    dirlist = list(p.name for p in out_dir.iterdir())
    expected = {
        "topic-map.md", "topic-map.csv",
        "per-article.md", "per-article.csv",
        "decay-findings.csv", "internal-linking.md",
        "internal-linking.csv", "summary.md",
    }
    assert expected.issubset(set(dirlist))
```

- [ ] **Step 2: Implementation**

Create `src/naturesseed_pipeline/pipelines/audit/report.py`:

```python
"""Report stage — generates markdown + CSV files under docs/content-audit/YYYY-MM-DD/."""

import csv
from collections import defaultdict
from datetime import date
from io import StringIO
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    ContentInventory, ContentProductMention, ContentTopic,
    DecayFinding, OutboundLink, Topic,
)


def generate_topic_map(session: Session) -> str:
    topics = session.execute(select(Topic)).scalars().all()
    by_parent: dict[int | None, list[Topic]] = defaultdict(list)
    for t in topics:
        by_parent[t.parent_topic_id].append(t)

    topic_articles: dict[int, list[ContentInventory]] = defaultdict(list)
    for ct in session.execute(select(ContentTopic)).scalars().all():
        row = session.get(ContentInventory, ct.content_inventory_id)
        if row:
            topic_articles[ct.topic_id].append(row)

    mentions_by_content: dict[int, list[str]] = defaultdict(list)
    for m in session.execute(select(ContentProductMention)).scalars().all():
        mentions_by_content[m.content_inventory_id].append(m.product_name)

    lines = ["# Topic Map", ""]
    for top in sorted(by_parent[None], key=lambda x: x.name):
        lines.append(f"## {top.name} (`{top.slug}`)")
        subs = sorted(by_parent[top.id], key=lambda x: x.name)
        if subs:
            for sub in subs:
                lines.append(f"### {sub.name} (`{sub.slug}`)")
                for row in sorted(topic_articles[sub.id], key=lambda r: r.title):
                    prods = mentions_by_content.get(row.id, [])
                    prod_str = f" — _products: {', '.join(prods)}_" if prods else ""
                    lines.append(f"- [{row.title}]({row.url}){prod_str}")
        direct = [r for r in topic_articles[top.id]
                  if r.id not in {x.id for sub in subs for x in topic_articles[sub.id]}]
        if direct:
            if not subs:
                lines.append("")
            lines.append("**Articles without subtopic:**")
            for row in sorted(direct, key=lambda r: r.title):
                lines.append(f"- [{row.title}]({row.url})")
        lines.append("")
    return "\n".join(lines)


def _topic_map_csv(session: Session) -> str:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["content_id", "title", "url", "post_type",
                "topic_slug", "subtopic_slug", "product_slug"])

    top_level = {t.id: t for t in session.execute(select(Topic)).scalars().all()
                 if t.parent_topic_id is None}

    assignments = session.execute(select(ContentTopic)).scalars().all()
    by_content: dict[int, list[Topic]] = defaultdict(list)
    for ct in assignments:
        topic = session.get(Topic, ct.topic_id)
        if topic:
            by_content[ct.content_inventory_id].append(topic)

    mentions = session.execute(select(ContentProductMention)).scalars().all()
    prods_by_content: dict[int, list[str]] = defaultdict(list)
    for m in mentions:
        prods_by_content[m.content_inventory_id].append(m.product_slug)

    for row in session.execute(select(ContentInventory)).scalars().all():
        topics = by_content.get(row.id, [])
        tl = next((t for t in topics if t.id in top_level), None)
        sub = next((t for t in topics if t.parent_topic_id is not None), None)
        prods = prods_by_content.get(row.id) or [""]
        for p in prods:
            w.writerow([row.id, row.title, row.url, row.post_type,
                       tl.slug if tl else "",
                       sub.slug if sub else "", p])
    return buf.getvalue()


def generate_per_article(session: Session) -> str:
    findings = defaultdict(list)
    for f in session.execute(select(DecayFinding).where(
        DecayFinding.status == "open"
    )).scalars().all():
        findings[f.content_inventory_id].append(f)

    mentions = defaultdict(list)
    for m in session.execute(select(ContentProductMention)).scalars().all():
        mentions[m.content_inventory_id].append(m.product_name)

    lines = ["# Per-Article Audit", ""]
    for row in session.execute(select(ContentInventory).order_by(ContentInventory.title)).scalars().all():
        lines.append(f"## {row.title}")
        lines.append(f"- URL: {row.url}")
        lines.append(f"- Type: {row.post_type} | Words: {row.word_count or 0}")
        prods = mentions.get(row.id, [])
        if prods:
            lines.append(f"- Products: {', '.join(prods)}")
        flist = findings.get(row.id, [])
        if flist:
            lines.append("- Decay findings:")
            for f in flist:
                lines.append(f"  - **{f.rule_name}** ({f.severity}): {f.suggested_action}")
        lines.append("")
    return "\n".join(lines)


def _per_article_csv(session: Session) -> str:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["content_id", "title", "url", "post_type", "status",
                "word_count", "products_count", "open_findings", "critical_findings"])
    findings = defaultdict(list)
    for f in session.execute(select(DecayFinding).where(DecayFinding.status == "open")).scalars().all():
        findings[f.content_inventory_id].append(f)
    prod_counts = defaultdict(int)
    for m in session.execute(select(ContentProductMention)).scalars().all():
        prod_counts[m.content_inventory_id] += 1
    for row in session.execute(select(ContentInventory)).scalars().all():
        flist = findings.get(row.id, [])
        crit = sum(1 for f in flist if f.severity == "critical")
        w.writerow([row.id, row.title, row.url, row.post_type, row.status,
                   row.word_count or 0, prod_counts[row.id],
                   len(flist), crit])
    return buf.getvalue()


def _decay_findings_csv(session: Session) -> str:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["content_id", "title", "url", "rule_name", "severity",
                "snippet", "suggested_action"])
    for f in session.execute(select(DecayFinding).where(DecayFinding.status == "open")).scalars().all():
        row = session.get(ContentInventory, f.content_inventory_id)
        w.writerow([f.content_inventory_id, row.title if row else "",
                   row.url if row else "",
                   f.rule_name, f.severity,
                   (f.snippet or "")[:300], f.suggested_action or ""])
    return buf.getvalue()


def generate_internal_linking(session: Session) -> str:
    rows = session.execute(select(ContentInventory).order_by(ContentInventory.title)).scalars().all()
    id_to_row = {r.id: r for r in rows}

    outbound = defaultdict(list)
    for link in session.execute(select(OutboundLink).where(
        OutboundLink.link_type.in_(["internal_content", "internal_product"])
    )).scalars().all():
        outbound[link.content_inventory_id].append(link)

    inbound = defaultdict(list)
    for link in session.execute(select(OutboundLink).where(
        OutboundLink.target_content_id.isnot(None)
    )).scalars().all():
        inbound[link.target_content_id].append(link)

    lines = ["# Internal Linking Map", "", "## Outbound links per article", ""]
    for row in rows:
        lines.append(f"### {row.title}")
        for link in outbound.get(row.id, []):
            target = id_to_row.get(link.target_content_id)
            target_desc = target.title if target else link.href
            lines.append(f"- → {target_desc} ({link.href})")
        lines.append("")

    lines += ["", "## Inbound links (what links TO each article)", ""]
    for row in rows:
        incoming = inbound.get(row.id, [])
        if not incoming:
            continue
        lines.append(f"### {row.title}")
        for link in incoming:
            source = id_to_row.get(link.content_inventory_id)
            lines.append(f"- ← {source.title if source else '?'}")
        lines.append("")
    return "\n".join(lines)


def _internal_linking_csv(session: Session) -> str:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["source_content_id", "target_content_id", "anchor_text", "href"])
    for link in session.execute(select(OutboundLink).where(
        OutboundLink.link_type.in_(["internal_content", "internal_product"])
    )).scalars().all():
        w.writerow([link.content_inventory_id, link.target_content_id or "",
                   link.anchor_text or "", link.href])
    return buf.getvalue()


def generate_summary(session: Session) -> str:
    content_count = session.execute(
        select(ContentInventory.id)
    ).scalars().all()
    findings = session.execute(
        select(DecayFinding).where(DecayFinding.status == "open")
    ).scalars().all()
    by_rule: dict[str, int] = defaultdict(int)
    for f in findings:
        by_rule[f.rule_name] += 1

    lines = ["# Audit Summary", ""]
    lines.append(f"- Total articles: {len(content_count)}")
    lines.append(f"- Total open decay findings: {len(findings)}")
    lines.append("")
    lines.append("## Findings by rule")
    for name, count in sorted(by_rule.items(), key=lambda x: -x[1]):
        lines.append(f"- {name}: {count}")
    return "\n".join(lines)


def run_report(session: Session, out_root: Path, date_str: str | None = None) -> Path:
    date_str = date_str or date.today().isoformat()
    out_dir = Path(out_root) / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "topic-map.md").write_text(generate_topic_map(session))
    (out_dir / "topic-map.csv").write_text(_topic_map_csv(session))
    (out_dir / "per-article.md").write_text(generate_per_article(session))
    (out_dir / "per-article.csv").write_text(_per_article_csv(session))
    (out_dir / "decay-findings.csv").write_text(_decay_findings_csv(session))
    (out_dir / "internal-linking.md").write_text(generate_internal_linking(session))
    (out_dir / "internal-linking.csv").write_text(_internal_linking_csv(session))
    (out_dir / "summary.md").write_text(generate_summary(session))
    return out_dir
```

- [ ] **Step 3: Run + commit**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_report.py -v
git add naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit/report.py \
        naturesseed-content-pipeline/tests/audit/test_report.py
git commit -m "feat(audit): report stage — topic map + per-article + internal linking"
```

---

## Task 26: CLI Wiring — Six `audit` Subcommands

**Files:**
- Modify: `src/naturesseed_pipeline/cli.py`
- Test: `tests/audit/test_cli_audit.py`

- [ ] **Step 1: Write failing test**

Create `tests/audit/test_cli_audit.py`:

```python
"""Smoke tests for the new audit CLI subcommands via typer.testing."""

from typer.testing import CliRunner

from naturesseed_pipeline.cli import app

runner = CliRunner()


def test_audit_help_lists_new_subcommands():
    result = runner.invoke(app, ["audit", "--help"])
    assert result.exit_code == 0
    for cmd in ("sync", "classify", "tag-products", "scan-links",
                "scan-decay", "report"):
        assert cmd in result.stdout


def test_audit_classify_help_lists_approval_flags():
    result = runner.invoke(app, ["audit", "classify", "--help"])
    assert result.exit_code == 0
    assert "approve" in result.stdout.lower()
```

- [ ] **Step 2: Run test (expect fail)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_cli_audit.py -v
```

Expected: the new subcommands don't exist.

- [ ] **Step 3: Rewire `audit_app` in `src/naturesseed_pipeline/cli.py`**

Replace the existing `audit_run` and `audit_report` functions (lines 96-161) with:

```python
# ── Audit commands (6-stage pipeline) ─────────────────────────────────────────

@audit_app.command("sync")
def audit_sync_cmd(
    since: str = typer.Option(None, "--since", help="Incremental YYYY-MM-DD"),
) -> None:
    """Pull posts + pages + products into content_inventory and wc_catalog_snapshot."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.audit.sync import run_sync
    session = SessionLocal()
    try:
        counts = run_sync(session, since=since)
        session.commit()
        console.print(f"[bold]Sync complete[/bold] — {counts}")
    finally:
        session.close()


@audit_app.command("classify")
def audit_classify_cmd(
    approve_subtopics: bool = typer.Option(
        False, "--approve-subtopics", help="Interactively approve pending subtopic proposals"),
    approve_all: bool = typer.Option(
        False, "--approve-all", help="Non-interactive: approve every pending subtopic"),
    reclassify: bool = typer.Option(False, "--reclassify", help="Redo all classification"),
) -> None:
    """Four-pass classify: seed topics, assign top-level, propose subtopics, assign subtopics."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.integrations.wordpress import WooCommerceClient
    from naturesseed_pipeline.pipelines.audit.classify import (
        seed_topics_from_wc_categories, run_classify_pass1, run_classify_pass2,
        list_pending_subtopics, approve_subtopic, approve_all_subtopics,
        run_classify_pass4, AnthropicSubtopicProposer,
    )
    session = SessionLocal()
    try:
        if approve_subtopics:
            pending = list_pending_subtopics(session)
            if not pending:
                console.print("No pending subtopics.")
                return
            for t in pending:
                console.print(f"Topic: {t.name} (parent_id={t.parent_topic_id})")
                console.print(f"  Keywords: {t.keywords}")
                if input("Approve? [y/N] ").strip().lower() == "y":
                    approve_subtopic(session, t.slug)
            session.commit()
            return

        if approve_all:
            n = approve_all_subtopics(session); session.commit()
            console.print(f"Approved {n} subtopics.")
            return

        # Full classify
        wc = WooCommerceClient()
        try:
            cats = wc._paginate("products/categories") or []
        finally:
            wc.close()
        added = seed_topics_from_wc_categories(session, cats)

        cat_map = {int(c["id"]): c.get("slug", "") for c in cats if c.get("id")}
        assigned = run_classify_pass1(session, wp_cat_id_to_slug=cat_map)
        proposed = run_classify_pass2(session, proposer=AnthropicSubtopicProposer())
        sub_assigned = run_classify_pass4(session)
        session.commit()
        console.print(f"Added {added} topics, {assigned} top-level assignments, "
                      f"{proposed} proposed subtopics, {sub_assigned} subtopic assignments.")
        if proposed:
            console.print("Run [bold]nspipe audit classify --approve-subtopics[/bold] to review.")
    finally:
        session.close()


@audit_app.command("tag-products")
def audit_tag_products_cmd() -> None:
    """Tag articles with active + inactive product + species mentions."""
    from naturesseed_pipeline.config import settings
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.audit.tag_products import run_tag_products
    session = SessionLocal()
    try:
        counts = run_tag_products(session, fuzzy_threshold=settings.audit_fuzzy_match_threshold)
        session.commit()
        console.print(f"[bold]Tag products complete[/bold] — {counts}")
    finally:
        session.close()


@audit_app.command("scan-links")
def audit_scan_links_cmd(
    skip_http: bool = typer.Option(False, "--skip-http", help="Extract only, no HTTP checks"),
    recheck_all: bool = typer.Option(False, "--recheck-all", help="Ignore 30-day cache"),
) -> None:
    """Extract outbound links + HTTP-check them."""
    from urllib.parse import urlparse
    from naturesseed_pipeline.config import settings
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.audit.scan_links import run_scan_links
    session = SessionLocal()
    try:
        site_host = urlparse(settings.wc_base_url).netloc
        cache_days = 0 if recheck_all else settings.audit_http_check_cache_days
        counts = run_scan_links(session, site_host=site_host, cache_days=cache_days,
                                skip_http=skip_http)
        session.commit()
        console.print(f"[bold]Scan links complete[/bold] — {counts}")
    finally:
        session.close()


@audit_app.command("scan-decay")
def audit_scan_decay_cmd(
    rule: str = typer.Option(None, "--rule", help="Run only a single rule"),
    article: int = typer.Option(None, "--article", help="Run against a single article id"),
) -> None:
    """Run all decay rules, reconcile findings, rebuild refresh_queue."""
    from naturesseed_pipeline.audit_rules import discover_rules
    from naturesseed_pipeline.config import settings
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.audit.scan_decay import run_scan_decay
    session = SessionLocal()
    try:
        rules = discover_rules()
        llm_client = None
        if settings.anthropic_api_key:
            import anthropic
            llm_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        counts = run_scan_decay(
            session, rules=rules,
            current_shipping=settings.audit_current_shipping,
            llm_client=llm_client, llm_model=settings.audit_llm_model,
            llm_token_budget=settings.audit_llm_max_tokens_per_rule,
            only_article_id=article, only_rule_name=rule,
        )
        session.commit()
        console.print(f"[bold]Scan decay complete[/bold] — {counts}")
    finally:
        session.close()


@audit_app.command("report")
def audit_report_cmd(
    out_dir: str = typer.Option("docs/content-audit",
                                 "--out", help="Report output root"),
) -> None:
    """Generate markdown + CSV reports."""
    from pathlib import Path
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.audit.report import run_report
    session = SessionLocal()
    try:
        out = run_report(session, out_root=Path(out_dir))
        console.print(f"[bold]Reports written to {out}[/bold]")
    finally:
        session.close()
```

Also remove the old `audit_run` and `audit_report` functions that were at lines 96-161.

- [ ] **Step 4: Run test (expect pass)**

```bash
cd naturesseed-content-pipeline && uv run pytest tests/audit/test_cli_audit.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add naturesseed-content-pipeline/src/naturesseed_pipeline/cli.py \
        naturesseed-content-pipeline/tests/audit/test_cli_audit.py
git commit -m "feat(audit): wire 6 CLI subcommands under nspipe audit"
```

---

## Task 27: Full-Suite Regression + Docs Cleanup

**Files:**
- Verify: all tests pass
- Verify: existing `tests/test_audit.py` still passes (legacy path)

- [ ] **Step 1: Run the full test suite**

```bash
cd naturesseed-content-pipeline && uv run pytest -v
```

Expected: all tests PASS. If `tests/test_audit.py` (legacy) imports `run_full_audit` or `get_audit_report` from `pipelines.audit`, those were removed in the Task 4 refactor — that test needs its imports updated or the test file needs to be retired. Check:

```bash
cd naturesseed-content-pipeline && grep -n "run_full_audit\|get_audit_report" tests/test_audit.py
```

If hits: rename affected tests to use the new `pipelines.audit.sync.run_sync` function, or mark with `@pytest.mark.skip("replaced by tests/audit/*")`.

- [ ] **Step 2: Remove stale top-level helpers**

The original `pipelines/audit.py` file is now redundant (all logic moved into `pipelines/audit/` package). Decision: keep it as a one-line re-export for backwards compatibility, or delete. Check what imports reference it:

```bash
cd naturesseed-content-pipeline && grep -rn "from naturesseed_pipeline.pipelines.audit import" src/ tests/ | grep -v "pipelines.audit\."
```

If only the `cli.py` references it (and cli.py now uses `pipelines.audit.sync`), delete the legacy file:

```bash
git rm naturesseed-content-pipeline/src/naturesseed_pipeline/pipelines/audit.py
```

Otherwise, replace its contents with a shim that re-exports from the new package.

- [ ] **Step 3: Run full suite again**

```bash
cd naturesseed-content-pipeline && uv run pytest -v
```

- [ ] **Step 4: Commit**

```bash
git add naturesseed-content-pipeline/
git commit -m "chore(audit): retire legacy pipelines/audit.py, all tests green"
```

---

## Task 28: End-to-End Smoke Run

**Files:**
- None (integration verification)

- [ ] **Step 1: Ensure DB migrations are up-to-date**

```bash
cd naturesseed-content-pipeline && uv run alembic upgrade head
```

- [ ] **Step 2: Run each stage against real data**

Expected runtime: ~5-15 minutes depending on article count. Each stage writes to DB and emits counts.

```bash
cd naturesseed-content-pipeline && uv run nspipe audit sync
cd naturesseed-content-pipeline && uv run nspipe audit classify
# Review proposed subtopics:
cd naturesseed-content-pipeline && uv run nspipe audit classify --approve-subtopics
# (or for first smoke test, auto-approve:)
# cd naturesseed-content-pipeline && uv run nspipe audit classify --approve-all
cd naturesseed-content-pipeline && uv run nspipe audit classify   # pass 4 picks up newly approved
cd naturesseed-content-pipeline && uv run nspipe audit tag-products
cd naturesseed-content-pipeline && uv run nspipe audit scan-links --skip-http   # fast first run
cd naturesseed-content-pipeline && uv run nspipe audit scan-links                # HTTP checks
cd naturesseed-content-pipeline && uv run nspipe audit scan-decay
cd naturesseed-content-pipeline && uv run nspipe audit report
```

- [ ] **Step 3: Verify reports exist and have content**

```bash
ls -la naturesseed-content-pipeline/docs/content-audit/$(date +%Y-%m-%d)/
wc -l naturesseed-content-pipeline/docs/content-audit/$(date +%Y-%m-%d)/*
```

Expected: 8 files present, all non-empty.

- [ ] **Step 4: Spot-check DB state**

```bash
cd naturesseed-content-pipeline && sqlite3 content_pipeline.db "SELECT COUNT(*) FROM content_inventory;"
cd naturesseed-content-pipeline && sqlite3 content_pipeline.db "SELECT rule_name, COUNT(*) FROM decay_findings WHERE status='open' GROUP BY rule_name ORDER BY 2 DESC;"
cd naturesseed-content-pipeline && sqlite3 content_pipeline.db "SELECT COUNT(*) FROM refresh_queue WHERE status='pending';"
```

- [ ] **Step 5: Commit the first report**

```bash
git add naturesseed-content-pipeline/docs/content-audit/
git commit -m "chore(audit): first committed content audit run"
```

---

## Self-Review Notes

**Spec coverage check:** Each section of the spec is implemented in:
- Architecture / 6 stages → Tasks 4, 7, 9, 11-14, 24, 25
- 6 new tables → Task 1
- Alembic migration → Task 2
- Config → Task 3 (+ Task 12 adds `keywords` to `Topic`)
- 12 decay rules → Tasks 16-23
- Reports → Task 25
- CLI → Task 26
- End-to-end → Task 28

**Known deviations from spec resolved inline:**
- `Topic` schema gained a `keywords` JSON column in Task 12 (spec didn't spell this out but Pass 4 requires keywords to match against). Migration added in same task.
- Spec's "concurrent with a semaphore" HTTP check is initially implemented sequentially in Task 6 (keeps the mocked test stable); concurrency argument preserved so a future pass can swap implementations without breaking the contract.

**Placeholder scan:** no TBD/TODO/vague instructions remain.

**Type consistency:** `Finding`, `AuditContext`, `DecayRule`, `ProductMatch`, `ExtractedLink` names match across all tasks that reference them.

