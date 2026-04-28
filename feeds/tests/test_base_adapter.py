import pytest
from feeds.adapters.base_adapter import BaseAdapter, AdapterResult, CoverageResult, DriftResult, QualityResult


class ConcreteAdapter(BaseAdapter):
    channel = "test_channel"
    def fetch_channel_products(self):
        return [{"sku": "A-SKU", "price": "10.00", "stock_status": "instock"}]
    def get_required_fields(self):
        return ["sku", "price"]


def _master():
    return {
        "meta": {"product_count": 2, "variation_count": 0},
        "products": {
            "1": {"wc_id": 1, "sku": "A-SKU", "price": "10.00", "stock_status": "instock",
                  "status": "publish", "variations": [], "channel_skus": {"test_channel": "A-SKU"}},
            "2": {"wc_id": 2, "sku": "B-SKU", "price": "20.00", "stock_status": "instock",
                  "status": "publish", "variations": [], "channel_skus": {"test_channel": ""}},
        }
    }


def test_coverage_check_finds_missing():
    adapter = ConcreteAdapter({})
    result = adapter.coverage_check(_master())
    assert result.wc_total == 2
    assert result.channel_total == 1
    assert "B-SKU" in result.missing_skus


def test_drift_check_detects_price_drift():
    master = _master()
    master["products"]["1"]["price"] = "12.00"
    channel_products = [{"sku": "A-SKU", "price": "10.00", "stock_status": "instock"}]
    adapter = ConcreteAdapter({})
    result = adapter.drift_check(master, channel_products)
    assert len(result.drifted) == 1
    assert result.drifted[0]["sku"] == "A-SKU"


def test_quality_check_flags_missing_required_field():
    channel_products = [{"sku": "A-SKU"}]  # missing price
    adapter = ConcreteAdapter({})
    result = adapter.quality_check(channel_products)
    assert len(result.incomplete) == 1


def test_run_catches_errors():
    class BrokenAdapter(BaseAdapter):
        channel = "broken"
        def fetch_channel_products(self):
            raise RuntimeError("API down")
        def get_required_fields(self):
            return []
    adapter = BrokenAdapter({})
    result = adapter.run(_master())
    assert result.error != ""
    assert result.ok is False
