from unittest.mock import patch, MagicMock
from feeds.adapters.walmart import WalmartAdapter

ENV = {
    "WALMART_CLIENT_ID": "fake_id",
    "WALMART_CLIENT_SECRET": "fake_secret",
}

def test_walmart_required_fields():
    adapter = WalmartAdapter(ENV)
    fields = adapter.get_required_fields()
    assert "sku" in fields
    assert "price" in fields
    assert "main_image_url" in fields

def test_walmart_fetch_normalizes_sku():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ItemResponse": [{"sku": "LAWN-KY31-5LB", "price": {"amount": 24.99},
                          "availabilityInformation": {"quantity": 50},
                          "productName": "Test", "shortDescription": "desc",
                          "mainImageUrl": "http://img.jpg"}]
    }
    mock_token = MagicMock()
    mock_token.status_code = 200
    mock_token.json.return_value = {"access_token": "tok123", "expires_in": 900}

    with patch("requests.post", return_value=mock_token), \
         patch("requests.get", return_value=mock_resp):
        adapter = WalmartAdapter(ENV)
        products = adapter.fetch_channel_products()

    assert len(products) == 1
    assert products[0]["sku"] == "LAWN-KY31-5LB"
    assert products[0]["price"] == "24.99"
