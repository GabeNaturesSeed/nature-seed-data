import requests
from feeds.adapters.base_adapter import BaseAdapter


class ShopperApprovedAdapter(BaseAdapter):
    channel = "shopper_approved"

    def fetch_channel_products(self) -> list:
        site_id = self.env["SA_SITE_ID"]
        token = self.env["SA_API_TOKEN"]
        resp = requests.get(
            f"https://api.shopperapproved.com/products/{site_id}",
            params={"token": token, "limit": 500},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        products = []
        items = data if isinstance(data, list) else data.get("products", [])
        for item in items:
            products.append({
                "sku": str(item.get("product_id", "")),
                "name": item.get("name", ""),
                "price": str(item.get("price", "")),
                "stock_status": "instock",
                "url": item.get("url", ""),
                "review_count": item.get("review_count", 0),
            })
        return products

    def get_required_fields(self) -> list:
        return ["sku", "name", "url"]
