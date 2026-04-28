import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from transform import format_price


def test_format_price_normal():
    assert format_price("19.99") == "19.99 USD"


def test_format_price_integer_string():
    assert format_price("20") == "20.00 USD"


def test_format_price_float():
    assert format_price(19.99) == "19.99 USD"


def test_format_price_none_returns_none():
    assert format_price(None) is None


def test_format_price_empty_string_returns_none():
    assert format_price("") is None


def test_format_price_zero_returns_none():
    assert format_price("0") is None
    assert format_price(0) is None
    assert format_price("0.00") is None


from transform import strip_html, truncate_description


def test_strip_html_removes_tags():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_decodes_entities():
    assert strip_html("Tom &amp; Jerry &lt;3") == "Tom & Jerry <3"


def test_strip_html_collapses_whitespace():
    assert strip_html("<p>Line one</p>\n\n<p>Line two</p>") == "Line one Line two"


def test_strip_html_handles_empty():
    assert strip_html("") == ""
    assert strip_html(None) == ""


def test_truncate_description_short_passthrough():
    assert truncate_description("Short text", limit=1000) == "Short text"


def test_truncate_description_caps_at_limit():
    long = "a" * 2000
    out = truncate_description(long, limit=1000)
    assert len(out) == 1000


def test_truncate_description_strips_html_first():
    out = truncate_description("<p>Hi <b>there</b></p>", limit=1000)
    assert out == "Hi there"


def test_truncate_description_preserves_utf8():
    out = truncate_description("héllo " * 500, limit=100)
    assert isinstance(out, str)
    assert len(out) <= 100
    out.encode("utf-8")


from transform import build_title


def test_build_title_no_attributes():
    assert build_title("Kentucky Bluegrass Seed", []) == "Kentucky Bluegrass Seed"


def test_build_title_single_attribute():
    attrs = [{"name": "Size", "option": "5 lb"}]
    assert build_title("Kentucky Bluegrass Seed", attrs) == "Kentucky Bluegrass Seed — 5 lb"


def test_build_title_multiple_attributes_joined():
    attrs = [
        {"name": "Size", "option": "5 lb"},
        {"name": "Type", "option": "Coated"},
    ]
    assert build_title("Clover Mix", attrs) == "Clover Mix — 5 lb / Coated"


def test_build_title_truncates_at_150():
    long_name = "A" * 200
    out = build_title(long_name, [])
    assert len(out) == 150


def test_build_title_truncates_with_attributes():
    long_name = "A" * 145
    attrs = [{"name": "Size", "option": "Extra Large 50 Pound Bag"}]
    out = build_title(long_name, attrs)
    assert len(out) == 150


from transform import should_skip_product, should_skip_variation


def _valid_simple_product():
    return {
        "id": 1,
        "status": "publish",
        "stock_status": "instock",
        "price": "19.99",
        "type": "simple",
        "images": [{"src": "https://example.com/a.jpg"}],
    }


def test_skip_product_unpublished():
    p = _valid_simple_product()
    p["status"] = "draft"
    assert should_skip_product(p) == "not_published"


def test_skip_product_no_images():
    p = _valid_simple_product()
    p["images"] = []
    assert should_skip_product(p) == "no_image"


def test_skip_simple_out_of_stock():
    p = _valid_simple_product()
    p["stock_status"] = "outofstock"
    assert should_skip_product(p) == "out_of_stock"


def test_skip_simple_zero_price():
    p = _valid_simple_product()
    p["price"] = "0"
    assert should_skip_product(p) == "zero_price"


def test_keep_valid_simple_product():
    assert should_skip_product(_valid_simple_product()) is None


def test_variable_parent_not_skipped_for_stock_or_price():
    p = _valid_simple_product()
    p["type"] = "variable"
    p["stock_status"] = "outofstock"
    p["price"] = ""
    assert should_skip_product(p) is None


def test_skip_variation_out_of_stock():
    v = {"id": 10, "stock_status": "outofstock", "price": "19.99"}
    assert should_skip_variation(v) == "out_of_stock"


def test_skip_variation_zero_price():
    v = {"id": 10, "stock_status": "instock", "price": "0"}
    assert should_skip_variation(v) == "zero_price"


def test_keep_valid_variation():
    v = {"id": 10, "stock_status": "instock", "price": "19.99"}
    assert should_skip_variation(v) is None


from transform import pick_image, additional_images


def test_pick_image_variation_override():
    parent = {"images": [{"src": "https://example.com/parent.jpg"}]}
    variation = {"image": {"src": "https://example.com/var.jpg"}}
    assert pick_image(parent, variation) == "https://example.com/var.jpg"


def test_pick_image_falls_back_to_parent():
    parent = {"images": [{"src": "https://example.com/parent.jpg"}]}
    variation = {"image": None}
    assert pick_image(parent, variation) == "https://example.com/parent.jpg"


def test_pick_image_simple_product_no_variation():
    parent = {"images": [{"src": "https://example.com/parent.jpg"}]}
    assert pick_image(parent, None) == "https://example.com/parent.jpg"


def test_pick_image_returns_none_when_nothing_available():
    assert pick_image({"images": []}, None) is None


def test_additional_images_skips_first():
    parent = {"images": [
        {"src": "a.jpg"}, {"src": "b.jpg"}, {"src": "c.jpg"}
    ]}
    assert additional_images(parent) == "b.jpg,c.jpg"


def test_additional_images_caps_at_nine():
    parent = {"images": [{"src": f"{i}.jpg"} for i in range(15)]}
    out = additional_images(parent).split(",")
    assert len(out) == 9


def test_additional_images_empty_when_only_one():
    parent = {"images": [{"src": "a.jpg"}]}
    assert additional_images(parent) == ""


import json
from transform import transform_simple_product

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name):
    with open(os.path.join(FIXTURE_DIR, name)) as f:
        return json.load(f)


def test_transform_simple_product_full_row():
    product = _load_fixture("simple_product.json")
    row = transform_simple_product(product)
    assert row == {
        "id": "1001",
        "item_group_id": "1001",
        "title": "Annual Ryegrass Seed",
        "description": "Fast germinating cover crop.",
        "link": "https://naturesseed.com/products/annual-ryegrass/",
        "image_link": "https://naturesseed.com/img/ar-1.jpg",
        "additional_image_link": "https://naturesseed.com/img/ar-2.jpg",
        "availability": "in stock",
        "price": "24.99 USD",
        "sale_price": "",
        "brand": "Nature's Seed",
        "condition": "new",
        "gtin": "",
        "mpn": "NS-AR-5LB",
        "product_type": "Cover Crops",
        "google_product_category": "5587",
    }


from transform import transform_variable_product


def test_transform_variable_product_emits_one_row_per_valid_variation():
    parent = _load_fixture("variable_product.json")
    variations = _load_fixture("variations_for_variable.json")
    rows, skipped = transform_variable_product(parent, variations)
    assert [r["id"] for r in rows] == ["3001", "3002"]
    assert all(r["item_group_id"] == "2001" for r in rows)
    assert skipped == [{"id": 3003, "reason": "out_of_stock"}]


def test_transform_variable_variation_image_fallback_to_parent():
    parent = _load_fixture("variable_product.json")
    variations = _load_fixture("variations_for_variable.json")
    rows, _ = transform_variable_product(parent, variations)
    row_3002 = next(r for r in rows if r["id"] == "3002")
    assert row_3002["image_link"] == "https://naturesseed.com/img/sheep-parent.jpg"


def test_transform_variable_title_includes_attributes():
    parent = _load_fixture("variable_product.json")
    variations = _load_fixture("variations_for_variable.json")
    rows, _ = transform_variable_product(parent, variations)
    row_3001 = next(r for r in rows if r["id"] == "3001")
    assert row_3001["title"] == "Sheep Pasture Mix — 5 lb"


def test_transform_variable_sale_price_blank_when_current_price_equals_sale():
    # Fixture 3002: regular=119.99, sale=99.99, price=99.99 (current price IS the sale)
    # sale_price should be blank because the active price already reflects the discount
    parent = _load_fixture("variable_product.json")
    variations = _load_fixture("variations_for_variable.json")
    rows, _ = transform_variable_product(parent, variations)
    row_3002 = next(r for r in rows if r["id"] == "3002")
    assert row_3002["price"] == "99.99 USD"
    assert row_3002["sale_price"] == ""


import io
from transform import write_tsv, TSV_COLUMNS


def test_write_tsv_header_first():
    rows = [{c: "" for c in TSV_COLUMNS}]
    rows[0]["id"] = "1"
    buf = io.StringIO()
    write_tsv(buf, rows)
    lines = buf.getvalue().splitlines()
    assert lines[0] == "\t".join(TSV_COLUMNS)


def test_write_tsv_escapes_tabs_and_newlines():
    row = {c: "" for c in TSV_COLUMNS}
    row["id"] = "1"
    row["title"] = "Has\ttab and\nnewline"
    buf = io.StringIO()
    write_tsv(buf, [row])
    body = buf.getvalue().splitlines()[1]
    cells = body.split("\t")
    title_idx = TSV_COLUMNS.index("title")
    assert cells[title_idx] == "Has tab and newline"


def test_write_tsv_row_count_matches():
    rows = [{c: "" for c in TSV_COLUMNS} for _ in range(5)]
    for i, r in enumerate(rows):
        r["id"] = str(i)
    buf = io.StringIO()
    write_tsv(buf, rows)
    assert len(buf.getvalue().splitlines()) == 6


from transform import _sale_price, _product_type


def test_sale_price_blank_when_equal_to_current_price():
    # Variation on sale: regular=119.99, sale=99.99, current price=99.99
    # Should NOT emit sale_price since price already reflects the sale
    assert _sale_price("119.99", "99.99", "99.99") == ""


def test_sale_price_set_when_lower_than_current_price():
    # Edge case where current price differs from sale price (rare but possible)
    assert _sale_price("119.99", "89.99", "99.99") == "89.99 USD"


def test_sale_price_blank_when_no_current_price_passed_and_equal_to_regular():
    # Backwards: when called without current_price, original behavior holds
    # (sale==regular is also "no real sale")
    assert _sale_price("99.99", "99.99", None) == ""


def test_product_type_decodes_html_entities():
    p = {"categories": [{"name": "Native Wildflower Seed &amp; Seed Mixes"}]}
    assert _product_type(p) == "Native Wildflower Seed & Seed Mixes"


def test_product_type_handles_no_entities():
    p = {"categories": [{"name": "Cover Crops"}]}
    assert _product_type(p) == "Cover Crops"


def test_product_type_empty_when_no_categories():
    assert _product_type({"categories": []}) == ""
    assert _product_type({}) == ""


def test_build_title_decodes_html_entities():
    assert build_title("Honey Bee Cover Crop &amp; Pasture Mix", []) == "Honey Bee Cover Crop & Pasture Mix"
