"""Tests for the Klaviyo catalog price/availability sync.

The Klaviyo catalog items are keyed by WC SKU (external_id), one item per
size/variation. Price comes from the variation's `price` field (NOT
regular_price, which WC leaves blank); url and image come from the PARENT
product because a variation has no page of its own. Availability maps from
stock_status, with onbackorder treated as sellable (documented house rule).
"""
from feeds.sync.sync_klaviyo_catalog import (
    item_id_for,
    build_sku_attrs,
    build_catalog_item_update,
    build_bulk_update_payload,
    compute_changes,
)


def _master():
    return {"products": {
        "464558": {
            "wc_id": 464558, "sku": "W-TRDA", "name": "Eastern Gamagrass Seed",
            "status": "publish", "type": "variable", "price": "16.99", "sale_price": "",
            "stock_status": "instock",
            "url": "https://naturesseed.com/products/pasture-seed/fakahatchee/",
            "images": ["https://naturesseed.com/img/a.webp",
                       "https://naturesseed.com/img/b.webp"],
            "variations": [
                {"variation_id": 464561, "sku": "W-TRDA-1-LB-KIT", "price": "55.24",
                 "sale_price": "55.24", "stock_status": "instock", "attributes": {"Size": "1 lb"}},
                {"variation_id": 464562, "sku": "W-TRDA-5-LB-KIT", "price": "220.00",
                 "sale_price": "", "stock_status": "onbackorder", "attributes": {"Size": "5 lb"}},
                {"variation_id": 464563, "sku": "W-TRDA-OOS", "price": "9.99",
                 "sale_price": "", "stock_status": "outofstock", "attributes": {"Size": "x"}},
                {"variation_id": 464564, "sku": "", "price": "1.00",
                 "sale_price": "", "stock_status": "instock", "attributes": {"Size": "no-sku"}},
            ],
        },
        "461690": {
            "wc_id": 461690, "sku": "BDL-POL", "name": "Pollinator Corridor Kit",
            "status": "publish", "type": "simple", "price": "339.99", "sale_price": "",
            "stock_status": "instock",
            "url": "https://naturesseed.com/products/wildflower-seed/pollinator-corridor-kit/",
            "images": ["https://naturesseed.com/img/pol.png"], "variations": [],
        },
        "999999": {  # draft -> must be excluded from the sync
            "wc_id": 999999, "sku": "DRAFT-1", "status": "draft", "type": "simple",
            "price": "10.00", "sale_price": "", "stock_status": "instock",
            "url": "https://naturesseed.com/products/x/draft/", "images": [], "variations": [],
        },
    }}


def test_item_id_for_builds_compound_id():
    assert item_id_for("PG-BOGR-5-LB") == "$custom:::$default:::PG-BOGR-5-LB"


def test_variation_uses_own_price_and_parent_url_and_image():
    attrs = build_sku_attrs(_master())
    a = attrs["W-TRDA-1-LB-KIT"]
    assert a["price"] == 55.24                        # from the variation
    assert isinstance(a["price"], float)              # numeric, not "55.24"
    assert a["url"] == "https://naturesseed.com/products/pasture-seed/fakahatchee/"  # parent
    assert a["image_full_url"] == "https://naturesseed.com/img/a.webp"               # parent[0]
    assert a["published"] is True


def test_simple_product_uses_own_fields():
    a = build_sku_attrs(_master())["BDL-POL"]
    assert a["price"] == 339.99
    assert a["url"].endswith("/pollinator-corridor-kit/")
    assert a["published"] is True


def test_published_reflects_stock_status():
    attrs = build_sku_attrs(_master())
    assert attrs["W-TRDA-5-LB-KIT"]["published"] is True    # onbackorder = sellable
    assert attrs["W-TRDA-OOS"]["published"] is False        # outofstock = hidden


def test_draft_products_and_skuless_variations_excluded():
    attrs = build_sku_attrs(_master())
    assert "DRAFT-1" not in attrs
    assert "" not in attrs
    assert set(attrs) == {"W-TRDA-1-LB-KIT", "W-TRDA-5-LB-KIT", "W-TRDA-OOS", "BDL-POL"}


def test_build_catalog_item_update_shape():
    obj = build_catalog_item_update(
        "$custom:::$default:::X",
        {"price": 42.0, "published": True, "url": "u", "image_full_url": "i"},
    )
    assert obj["type"] == "catalog-item"
    assert obj["id"] == "$custom:::$default:::X"
    assert obj["attributes"]["price"] == 42.0
    assert obj["attributes"]["published"] is True
    assert obj["attributes"]["url"] == "u"
    assert obj["attributes"]["image_full_url"] == "i"


def test_bulk_payload_envelope_and_type():
    items = [build_catalog_item_update("$custom:::$default:::X",
                                       {"price": 1.0, "published": True})]
    payload = build_bulk_update_payload(items)
    assert payload["data"]["type"] == "catalog-item-bulk-update-job"
    assert payload["data"]["attributes"]["items"]["data"] == items


def test_compute_changes_updates_existing_only_and_reports_gaps():
    targets = {
        "IN-CAT": {"price": 5.0, "url": "https://naturesseed.com/products/a/", "published": True},
        "NOT-IN-CAT": {"price": 9.0, "url": "https://naturesseed.com/products/b/", "published": True},
    }
    existing = {
        "IN-CAT": {"id": item_id_for("IN-CAT"), "price": None,
                   "url": "https://naturesseed.com/product/IN-CAT", "published": True},
        "ORPHAN": {"id": item_id_for("ORPHAN"), "price": 1.0, "url": "x", "published": True},
    }
    updates, report = compute_changes(targets, existing)
    assert [u["id"] for u in updates] == [item_id_for("IN-CAT")]   # existing target only
    assert report["missing_from_catalog"] == ["NOT-IN-CAT"]         # cannot create here
    assert report["orphans_in_catalog"] == ["ORPHAN"]
    assert report["price_fixes"] == 1                              # null -> 5.0
    assert report["url_fixes"] == 1                                # /product/ -> /products/
