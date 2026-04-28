from feeds.adapters.base_adapter import BaseAdapter, AdapterResult


class FacebookAdapter(BaseAdapter):
    channel = "facebook"

    def fetch_channel_products(self) -> list:
        return []

    def get_required_fields(self) -> list:
        return ["id", "title", "description", "availability", "condition", "price",
                "link", "image_link", "brand", "google_product_category"]

    def run(self, master: dict) -> AdapterResult:
        return AdapterResult(channel=self.channel, error="not connected — Facebook Catalog API not yet configured")
