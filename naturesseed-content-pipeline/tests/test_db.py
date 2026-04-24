"""Test database models and table creation."""

import os
import tempfile

from sqlalchemy import create_engine, inspect

from naturesseed_pipeline.db.models import Base


def test_all_tables_created() -> None:
    """Verify all tables are created from the ORM models."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        tables = sorted(inspector.get_table_names())

        expected = sorted([
            "content_inventory",
            "keyword_candidates",
            "media_signals",
            "brief_queue",
            "drafts",
            "publish_queue",
            "performance_metrics",
            "orphan_references",
            "refresh_queue",
            "redirects",
            "gsc_query_performance",
            "competitor_domains",
            "media_index",
            "refresh_history",
            "topics",
            "content_topics",
            "content_product_mentions",
            "outbound_links",
            "decay_findings",
            "wc_catalog_snapshot",
        ])
        assert tables == expected


def test_content_inventory_columns() -> None:
    """Spot-check content_inventory has the right columns."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("content_inventory")}
        assert "wp_post_id" in cols
        assert "target_keyword" in cols
        assert "performance_metrics" in cols
        assert "last_audited_at" in cols
