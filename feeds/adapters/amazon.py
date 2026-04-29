import time
import requests
from feeds.adapters.base_adapter import BaseAdapter

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
SP_BASE = "https://sellingpartnerapi-na.amazon.com"


class AmazonAdapter(BaseAdapter):
    channel = "amazon"

    def _get_access_token(self):
        resp = requests.post(LWA_TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": self.env["AMAZON_REFRESH_TOKEN"],
            "client_id": self.env["AMAZON_CLIENT_ID"],
            "client_secret": self.env["AMAZON_CLIENT_SECRET"],
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def fetch_channel_products(self) -> list:
        token = self._get_access_token()
        seller_id = self.env["AMAZON_MERCHANT_TOKEN"]
        headers = {
            "x-amz-access-token": token,
            "Accept": "application/json",
        }
        products = []
        next_token = None
        while True:
            params = {"sellerId": seller_id, "includedData": "summaries,attributes,offers"}
            if next_token:
                params["pageToken"] = next_token
            resp = requests.get(
                f"{SP_BASE}/catalog/2022-04-01/items",
                headers=headers, params=params, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("items", []):
                summaries = item.get("summaries", [{}])[0] if item.get("summaries") else {}
                offers = item.get("offers", [{}])[0] if item.get("offers") else {}
                seller_sku = offers.get("sellerSku", "") or summaries.get("asin", "")
                qty = 0
                fa = offers.get("fulfillmentAvailability", [])
                if fa:
                    qty = fa[0].get("quantity", 0)
                products.append({
                    "sku": seller_sku,
                    "asin": summaries.get("asin", ""),
                    "name": summaries.get("itemName", ""),
                    "price": str(offers.get("buyingPrice", {}).get("listingPrice", {}).get("amount", "")),
                    "stock_status": "instock" if qty > 0 else "outofstock",
                    "bullet_points": item.get("attributes", {}).get("bullet_point", []),
                    "main_image_url": summaries.get("mainImage", {}).get("link", ""),
                    "brand": summaries.get("brand", ""),
                })
            next_token = data.get("nextToken")
            if not next_token:
                break
            time.sleep(0.5)
        return products

    def get_required_fields(self) -> list:
        return ["sku", "name", "price", "main_image_url", "brand"]
