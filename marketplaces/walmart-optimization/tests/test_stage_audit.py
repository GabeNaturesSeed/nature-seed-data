import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from stage_audit import filter_stage_items, build_audit_row


def test_filter_stage_items_keeps_only_stage():
    items = [
        {"sku": "A-1", "productName": "Alpha", "publishedStatus": "STAGE"},
        {"sku": "B-2", "productName": "Beta",  "publishedStatus": "PUBLISHED"},
        {"sku": "C-3", "productName": "Gamma", "publishedStatus": "STAGE"},
    ]
    result = filter_stage_items(items)
    assert len(result) == 2
    assert all(i["publishedStatus"] == "STAGE" for i in result)


def test_filter_stage_items_deduplicates_by_sku():
    items = [
        {"sku": "A-1", "productName": "Alpha", "publishedStatus": "STAGE"},
        {"sku": "A-1", "productName": "Alpha", "publishedStatus": "STAGE"},
    ]
    result = filter_stage_items(items)
    assert len(result) == 1


def test_filter_stage_items_empty():
    assert filter_stage_items([]) == []


def test_build_audit_row_with_stock():
    item = {"sku": "NS-BLUE-5-LB", "productName": "Bluegrass 5lb"}
    row = build_audit_row(item, fishbowl_qty=50, match_type="direct", matched_sku="NS-BLUE-5-LB")
    assert row["sku"] == "NS-BLUE-5-LB"
    assert row["fishbowl_qty"] == 50
    assert row["will_activate"] is True
    assert row["matched_fishbowl_sku"] == "NS-BLUE-5-LB"


def test_build_audit_row_no_stock():
    item = {"sku": "NS-BLUE-5-LB", "productName": "Bluegrass 5lb"}
    row = build_audit_row(item, fishbowl_qty=0, match_type="no_match", matched_sku=None)
    assert row["will_activate"] is False
    assert row["matched_fishbowl_sku"] is None
