import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from resubmit_stage_items import (
    find_seo_content,
    build_product_identifiers,
    build_orderable,
    build_visible,
)

SEO_ITEMS = [
    {
        "sku": "PG-BUCK-50-LB-KIT",
        "title": "Nature's Seed Buckwheat Seed - 50 Lb",
        "description": "<p>Great cover crop.</p>",
        "key_features": ["Fast germinating", "Drought tolerant"],
        "attributes": {
            "brand": "Nature's Seed",
            "light_needs": "Full Sun",
            "plantCategory": "Grasses",
            "plantName": "Buckwheat",
            "netContent": "50 lb",
            "isProp65WarningRequired": "No",
            "condition": "New",
        },
        "product_type": "Grass Seeds",
    },
]

WM_ITEM = {
    "sku": "PG-BUCK-5-LB",
    "gtin": "00021532968880",
    "upc": "021532968880",
    "price": {"currency": "USD", "amount": 49.99},
    "productType": "Grass Seeds",
    "publishedStatus": "STAGE",
}


# --- find_seo_content ---

def test_find_seo_content_base_match():
    # PG-BUCK-5-LB and PG-BUCK-50-LB-KIT share base PG-BUCK
    result = find_seo_content("PG-BUCK-5-LB", SEO_ITEMS)
    assert result is not None
    assert result["title"] == "Nature's Seed Buckwheat Seed - 50 Lb"


def test_find_seo_content_kit_variant_matches():
    result = find_seo_content("PG-BUCK-25-LB-KIT", SEO_ITEMS)
    assert result is not None


def test_find_seo_content_no_match_returns_none():
    result = find_seo_content("PB-CHM-5-LB", SEO_ITEMS)
    assert result is None


# --- build_product_identifiers ---

def test_build_product_identifiers_prefers_gtin():
    result = build_product_identifiers(WM_ITEM)
    assert result["productIdType"] == "GTIN"
    assert result["productId"] == "00021532968880"


def test_build_product_identifiers_falls_back_to_upc():
    item = dict(WM_ITEM)
    item["gtin"] = ""
    result = build_product_identifiers(item)
    assert result["productIdType"] == "UPC"
    assert result["productId"] == "021532968880"


def test_build_product_identifiers_returns_none_when_neither():
    item = dict(WM_ITEM)
    item["gtin"] = ""
    item["upc"] = ""
    result = build_product_identifiers(item)
    assert result is None


# --- build_orderable ---

def test_build_orderable_contains_required_fields():
    result = build_orderable(WM_ITEM)
    assert result["price"] == 49.99
    assert result["fulfillmentLagTime"] == 2
    assert "startDate" in result
    assert "endDate" in result


def test_build_orderable_no_price_when_missing():
    item = dict(WM_ITEM)
    item["price"] = {}
    result = build_orderable(item)
    assert "price" not in result


# --- build_visible ---

def test_build_visible_with_seo_content():
    result = build_visible(SEO_ITEMS[0], "Grass Seeds")
    section = result["Grass Seeds"]
    assert section["productName"] == "Nature's Seed Buckwheat Seed - 50 Lb"
    assert section["brand"] == "Nature's Seed"
    assert section["keyFeatures"] == ["Fast germinating", "Drought tolerant"]
    assert section["plantCategory"] == ["Grasses"]
    assert section["plant_name"] == ["Buckwheat"]
    assert section["netContent"]["productNetContentMeasure"] == 50.0
    assert section["netContent"]["productNetContentUnit"] == "Pound"
    assert section["light_needs"] == "Full Sun"


def test_build_visible_fallback_no_seo():
    result = build_visible(None, "Grass Seeds")
    section = result["Grass Seeds"]
    assert section["brand"] == "Nature's Seed"
    assert section["isProp65WarningRequired"] == "No"
    assert section["condition"] == "New"
    assert "productName" not in section
    assert "keyFeatures" not in section


def test_build_visible_product_type_is_outer_key():
    result = build_visible(SEO_ITEMS[0], "Plant Seeds")
    assert "Plant Seeds" in result
    assert "Grass Seeds" not in result
