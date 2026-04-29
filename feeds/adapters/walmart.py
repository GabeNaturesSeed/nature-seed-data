import time
import requests
from feeds.adapters.base_adapter import BaseAdapter

WM_BASE = "https://marketplace.walmartapis.com/v3"


class WalmartAdapter(BaseAdapter):
    channel = "walmart"

    def _get_token(self):
        resp = requests.post(
            "https://marketplace.walmartapis.com/v3/token",
            auth=(self.env["WALMART_CLIENT_ID"], self.env["WALMART_CLIENT_SECRET"]),
            data={"grant_type": "client_credentials"},
            headers={"WM_SVC.NAME": "Walmart Marketplace", "WM_QOS.CORRELATION_ID": "feed-audit", "Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _wm_headers(self, token):
        return {
            "WM_SEC.ACCESS_TOKEN": token,
            "WM_SVC.NAME": "Walmart Marketplace",
            "WM_QOS.CORRELATION_ID": "feed-audit",
            "Accept": "application/json",
        }

    def fetch_channel_products(self) -> list:
        token = self._get_token()
        headers = self._wm_headers(token)
        products = []
        next_cursor = None
        while True:
            params = {"limit": 200}
            if next_cursor:
                params["nextCursor"] = next_cursor
            resp = requests.get(f"{WM_BASE}/items", headers=headers, params=params, timeout=30)
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("ItemResponse", []):
                price_info = item.get("price", {})
                qty = item.get("availabilityInformation", {}).get("quantity", 0)
                products.append({
                    "sku": item.get("sku", ""),
                    "price": str(price_info.get("amount", "")),
                    "stock_status": "instock" if qty > 0 else "outofstock",
                    "name": item.get("productName", ""),
                    "short_description": item.get("shortDescription", ""),
                    "main_image_url": item.get("mainImageUrl", ""),
                })
            next_cursor = data.get("nextCursor")
            if not next_cursor:
                break
            time.sleep(0.5)
        return products

    def get_required_fields(self) -> list:
        return ["sku", "price", "name", "short_description", "main_image_url", "stock_status"]
