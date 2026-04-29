import requests
from feeds.adapters.base_adapter import BaseAdapter

GMC_BASE = "https://shoppingcontent.googleapis.com/content/v2.1"


class GoogleMerchantAdapter(BaseAdapter):
    channel = "google_merchant"

    def _get_access_token(self):
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": self.env["GOOGLE_ADS_CLIENT_ID"],
            "client_secret": self.env["GOOGLE_ADS_CLIENT_SECRET"],
            "refresh_token": self.env["GOOGLE_ADS_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def fetch_channel_products(self) -> list:
        token = self._get_access_token()
        merchant_id = self.env.get("GOOGLE_MERCHANT_CENTER_ID", "138935850")
        headers = {"Authorization": f"Bearer {token}"}
        products = []
        page_token = None
        while True:
            params = {"maxResults": 250}
            if page_token:
                params["pageToken"] = page_token
            resp = requests.get(
                f"{GMC_BASE}/{merchant_id}/products",
                headers=headers, params=params, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("resources", []):
                price_info = item.get("price", {})
                products.append({
                    "sku": item.get("offerId", ""),
                    "name": item.get("title", ""),
                    "price": price_info.get("value", ""),
                    "stock_status": "instock" if item.get("availability") == "in stock" else "outofstock",
                    "gtin": item.get("gtin", ""),
                    "brand": item.get("brand", ""),
                    "main_image_url": item.get("imageLink", ""),
                    "description": item.get("description", ""),
                    "product_type": (item.get("productTypes") or [""])[0],
                })
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return products

    def get_required_fields(self) -> list:
        return ["sku", "name", "price", "gtin", "brand", "main_image_url", "description"]
