import csv
import io
import requests
from feeds.adapters.base_adapter import BaseAdapter

SHEET_ID = "12u2Uj0gHNImAQKDA1qnDUxlw4czL4DNuHbuUFqULbuU"
SHEET_GID = "0"
CATALOG_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"


class FacebookAdapter(BaseAdapter):
    channel = "facebook"

    def fetch_channel_products(self) -> list:
        resp = requests.get(CATALOG_URL, timeout=30)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        products = []
        for row in reader:
            price = row.get("price", "").replace(" USD", "").strip()
            sale_price = row.get("sale_price", "").replace(" USD", "").strip()
            availability = row.get("availability", "").strip().lower()
            products.append({
                "sku": row.get("mpn", "").strip(),
                "name": row.get("title", "").strip(),
                "price": price,
                "sale_price": sale_price,
                "stock_status": "instock" if availability == "in stock" else "outofstock",
                "main_image_url": row.get("image_link", "").strip(),
                "description": row.get("description", "").strip(),
                "url": row.get("link", "").strip(),
                "gtin": row.get("gtin", "").strip(),
                "brand": row.get("brand", "").strip(),
                "fb_id": row.get("id", "").strip(),
                "item_group_id": row.get("item_group_id", "").strip(),
            })
        return products

    def get_required_fields(self) -> list:
        return ["sku", "name", "price", "main_image_url", "url", "gtin", "brand"]
