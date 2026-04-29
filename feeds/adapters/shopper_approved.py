import requests
from feeds.adapters.base_adapter import BaseAdapter


class ShopperApprovedAdapter(BaseAdapter):
    channel = "shopper_approved"

    def fetch_channel_products(self) -> list:
        site_id = self.env["SA_SITE_ID"]
        token = self.env["SA_API_TOKEN"]
        seen = {}
        page = 0
        while True:
            resp = requests.get(
                f"https://api.shopperapproved.com/products/reviews/{site_id}",
                params={"token": token, "limit": 100, "page": page, "from": "2010-01-01", "xml": "false"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            for review in data.values():
                if not isinstance(review, dict):
                    continue
                pid = str(review.get("product_id", "") or review.get("product", ""))
                if pid and pid not in seen:
                    seen[pid] = {
                        "sku": pid,
                        "name": review.get("product", pid),
                        "price": "",
                        "stock_status": "instock",
                        "url": review.get("product_url", ""),
                        "review_count": 1,
                    }
                elif pid:
                    seen[pid]["review_count"] += 1
            if len(data) < 100:
                break
            page += 1
        return list(seen.values())

    def get_required_fields(self) -> list:
        return ["sku", "name"]
