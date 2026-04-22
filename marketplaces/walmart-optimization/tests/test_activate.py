import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from activate_stage_items import build_mp_item_payload, parse_feed_item_result


def test_build_mp_item_payload_wraps_item():
    item_detail = {
        "sku": "NS-BLUE-5-LB",
        "productName": "Bluegrass 5lb",
        "price": {"currentPrice": {"amount": 29.99, "currency": "USD"}},
    }
    payload = build_mp_item_payload(item_detail)
    assert "Item" in payload
    assert payload["Item"]["sku"] == "NS-BLUE-5-LB"


def test_parse_feed_item_result_success():
    feed_status = {
        "feedStatus": "PROCESSED",
        "itemDetails": {
            "itemIngestionStatus": [
                {"ingestionStatus": "SUCCESS", "ingestionErrors": None}
            ]
        },
    }
    result = parse_feed_item_result("NS-BLUE-5-LB", "feed123", feed_status)
    assert result["sku"] == "NS-BLUE-5-LB"
    assert result["feed_id"] == "feed123"
    assert result["status"] == "PROCESSED"
    assert result["ingestion_status"] == "SUCCESS"
    assert result["errors"] == []


def test_parse_feed_item_result_data_error():
    feed_status = {
        "feedStatus": "PROCESSED",
        "itemDetails": {
            "itemIngestionStatus": [
                {
                    "ingestionStatus": "DATA_ERROR",
                    "ingestionErrors": {
                        "ingestionError": [
                            {"type": "DATA_ERROR", "description": "Missing required field: brand"}
                        ]
                    },
                }
            ]
        },
    }
    result = parse_feed_item_result("NS-BLUE-5-LB", "feed123", feed_status)
    assert result["ingestion_status"] == "DATA_ERROR"
    assert len(result["errors"]) == 1
    assert "brand" in result["errors"][0]


def test_parse_feed_item_result_timeout():
    feed_status = {"feedStatus": "UNKNOWN"}
    result = parse_feed_item_result("NS-BLUE-5-LB", "feed123", feed_status)
    assert result["status"] == "UNKNOWN"
    assert result["ingestion_status"] == "UNKNOWN"
    assert result["errors"] == []
