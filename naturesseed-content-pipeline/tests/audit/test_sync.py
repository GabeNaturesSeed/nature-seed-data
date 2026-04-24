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
