import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from product_quality_report import check_fields, calc_quality_score, score_item


FULL_ITEM = {
    "sku": "NS-BLUE-5-LB",
    "productName": "Nature's Seed Kentucky Bluegrass Grass Seed Mixture 5 lb Bag for Lawns",
    "price": {"currency": "USD", "amount": 29.99},
    "shelf": "Home Page/Patio & Garden/Garden Center/Lawn Care/Grass Seed & Sod/Full Sun Grass Seeds",
    "productType": "Grass Seeds",
    "upc": "021532968881",
    "gtin": "00021532968881",
    "unpublishedReasons": {"reason": []},
}

EMPTY_ITEM = {
    "sku": "NS-BLUE-5-LB",
    "productName": "",
}


def test_check_fields_full_item():
    result = check_fields(FULL_ITEM)
    assert result["title"] is True
    assert result["price"] is True
    assert result["upc"] is True
    assert result["shelf_category"] is True
    # content fields not available via API — always None
    assert result["images"] is None
    assert result["description"] is None
    assert result["brand"] is None
    assert result["bullets"] is None


def test_check_fields_empty_item():
    result = check_fields(EMPTY_ITEM)
    assert result["title"] is False
    assert result["price"] is False
    assert result["upc"] is False
    assert result["shelf_category"] is False


def test_calc_quality_score_full_item():
    fields = check_fields(FULL_ITEM)
    score = calc_quality_score(FULL_ITEM, fields)
    assert score >= 60  # full available fields should score high


def test_calc_quality_score_empty_item():
    fields = check_fields(EMPTY_ITEM)
    score = calc_quality_score(EMPTY_ITEM, fields)
    assert score == 0


def test_score_item_returns_required_keys():
    result = score_item(FULL_ITEM)
    assert "fields" in result
    assert "quality_score" in result
    assert "gaps" in result
    assert "api_limitations" in result
    assert isinstance(result["quality_score"], int)
    assert 0 <= result["quality_score"] <= 100


def test_title_length_boosts_score():
    short_item = dict(FULL_ITEM)
    short_item["productName"] = "Seed"
    score_short = calc_quality_score(short_item, check_fields(short_item))
    score_full = calc_quality_score(FULL_ITEM, check_fields(FULL_ITEM))
    assert score_full > score_short


def test_walmart_unpublished_reasons_captured():
    item = dict(FULL_ITEM)
    item["unpublishedReasons"] = {"reason": ["Missing required attribute: shortDescription"]}
    result = score_item(item)
    assert len(result["unpublished_reasons"]) == 1
    assert "shortDescription" in result["unpublished_reasons"][0]
