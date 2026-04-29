import time
import requests
from feeds.adapters.base_adapter import BaseAdapter

KLAVIYO_BASE = "https://a.klaviyo.com/api"
REVISION = "2024-07-15"


class KlaviyoAdapter(BaseAdapter):
    channel = "klaviyo"

    def _headers(self):
        return {
            "Authorization": f"Klaviyo-API-Key {self.env['KLAVIYO_API']}",
            "revision": REVISION,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def fetch_channel_products(self) -> list:
        headers = self._headers()
        products = []
        cursor = None
        while True:
            # Build URL manually — requests percent-encodes brackets which Klaviyo rejects
            url = f"{KLAVIYO_BASE}/catalog-items?page[size]=100"
            if cursor:
                url += f"&page[cursor]={cursor}"
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                products.append({
                    "sku": attrs.get("external_id", ""),
                    "name": attrs.get("title", ""),
                    "price": str(attrs.get("price", "")),
                    "stock_status": "instock" if attrs.get("published") else "outofstock",
                    "main_image_url": attrs.get("image_full_url", ""),
                    "description": attrs.get("description", ""),
                    "url": attrs.get("url", ""),
                })
            cursor = data.get("links", {}).get("next")
            if not cursor:
                break
            time.sleep(0.3)
        return products

    def get_required_fields(self) -> list:
        return ["sku", "name", "price", "main_image_url", "url"]
