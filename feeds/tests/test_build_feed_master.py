import json
from unittest.mock import patch, MagicMock
from feeds.build_feed_master import build_product_record, pull_wc_products

def _mock_product(wc_id=100, sku="TEST-SKU", price="19.99", status="publish"):
    return {
        "id": wc_id,
        "sku": sku,
        "name": "Test Product",
        "status": status,
        "type": "simple",
        "price": price,
        "sale_price": "",
        "stock_status": "instock",
        "stock_quantity": 50,
        "categories": [{"name": "Lawn"}],
        "permalink": "https://www.naturesseed.com/products/test/",
        "images": [{"src": "https://example.com/img.jpg"}],
        "meta_data": [{"key": "_gtin", "value": "012345678901"}],
        "weight": "5",
        "short_description": "Short desc",
        "description": "Long desc",
        "variations": [],
        "attributes": [],
    }

def test_build_product_record_simple():
    p = _mock_product()
    record = build_product_record(p, variations=[])
    assert record["wc_id"] == 100
    assert record["sku"] == "TEST-SKU"
    assert record["price"] == "19.99"
    assert record["status"] == "publish"
    assert record["type"] == "simple"
    assert record["brand"] == "Nature's Seed"
    assert record["variations"] == []

def test_build_product_record_extracts_gtin():
    p = _mock_product()
    record = build_product_record(p, variations=[])
    assert record["gtin"] == "012345678901"

def test_build_product_record_url_uses_products_permalink():
    p = _mock_product()
    record = build_product_record(p, variations=[])
    assert "/products/" in record["url"]

def test_build_product_record_skips_draft():
    p = _mock_product(status="draft")
    record = build_product_record(p, variations=[])
    assert record["status"] == "draft"
