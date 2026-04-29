import csv
from pathlib import Path
from feeds.adapters.base_adapter import BaseAdapter


class RedditAdapter(BaseAdapter):
    channel = "reddit"
    CATALOG_PATH = Path("docs/reddit-catalog/reddit_catalog.csv")

    def fetch_channel_products(self) -> list:
        if not self.CATALOG_PATH.exists():
            raise FileNotFoundError(
                f"Reddit catalog not found at {self.CATALOG_PATH}. Run the reddit-ads agent first."
            )
        products = []
        with open(self.CATALOG_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                products.append({
                    "sku": row.get("id", ""),
                    "name": row.get("title", ""),
                    "price": row.get("price", "").replace("USD ", ""),
                    "stock_status": "instock" if row.get("availability") == "in stock" else "outofstock",
                    "main_image_url": row.get("image_link", ""),
                    "description": row.get("description", ""),
                })
        return products

    def get_required_fields(self) -> list:
        return ["sku", "name", "price", "main_image_url"]
