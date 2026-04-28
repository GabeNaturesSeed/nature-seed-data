from unittest.mock import patch, MagicMock
from feeds.sync.sync_prices import build_walmart_price_update, build_amazon_price_update

def _variation(sku="LAWN-KY31-5LB", price="24.99", stock_quantity=50, stock_status="instock"):
    return {"sku": sku, "price": price, "stock_quantity": stock_quantity, "stock_status": stock_status, "variation_id": 999}

def test_build_walmart_price_update():
    v = _variation(price="24.99")
    payload = build_walmart_price_update(v)
    assert payload["sku"] == "LAWN-KY31-5LB"
    assert payload["pricing"]["currentPrice"]["amount"] == 24.99
    assert payload["pricing"]["currentPriceType"] == "BASE"

def test_build_amazon_price_update():
    v = _variation(sku="B08XYZ123", price="24.99")
    payload = build_amazon_price_update(v, seller_id="A1L3JR5H0WXLZ")
    assert payload["sku"] == "B08XYZ123"
    assert payload["price"] == "24.99"
