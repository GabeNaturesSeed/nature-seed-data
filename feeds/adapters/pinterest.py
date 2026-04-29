from feeds.adapters.base_adapter import BaseAdapter, AdapterResult


class PinterestAdapter(BaseAdapter):
    channel = "pinterest"

    def fetch_channel_products(self) -> list:
        return []

    def get_required_fields(self) -> list:
        return ["id", "title", "description", "link", "image_link", "price", "availability"]

    def run(self, master: dict) -> AdapterResult:
        return AdapterResult(channel=self.channel, error="not connected — Pinterest Catalog API not yet configured")
