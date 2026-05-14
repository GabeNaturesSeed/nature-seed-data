import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import patch, MagicMock
import add_new_listings as m


def test_build_gmc_rows_count():
    rows = m.build_gmc_rows()
    assert len(rows) == 9  # 3 products × 3 variants

def test_build_gmc_rows_structure():
    rows = m.build_gmc_rows()
    first = rows[0]
    assert set(first.keys()) == set(m.GMC_COLS)

def test_build_gmc_row_cnir_5lb():
    rows = m.build_gmc_rows()
    cnir_5 = next(r for r in rows if r["mpn"] == "CV-CNIR-5-LB")
    assert cnir_5["id"] == "gla_470544"
    assert cnir_5["title"] == "California Native Ignition Resistant Seed Mix - 5 Lb - 5,000 Sq Ft"
    assert cnir_5["price"] == "311.87 USD"
    assert cnir_5["gtin"] == "840184629488"
    assert cnir_5["item_group_id"] == "NS_0103"
    assert cnir_5["custom_label_0"] == "specialty"
    assert cnir_5["custom_label_1"] == ">200"
    assert cnir_5["availability"] == "in stock"
    assert cnir_5["condition"] == "new"
    assert cnir_5["brand"] == "Nature's Seed"
    assert cnir_5["shipping"] == "US:Ground:9.99 USD"
    assert cnir_5["shipping_weight"] == "5 lb"
    assert "attribute_pa_size=5-lb" in cnir_5["link"]
    assert "/products/specialty-seed/california-native-ignition-resistant-seed-mix/" in cnir_5["link"]

def test_build_gmc_row_sols_50lb():
    rows = m.build_gmc_rows()
    sols_50 = next(r for r in rows if r["mpn"] == "PB-SOLS-50-LB")
    assert sols_50["id"] == "gla_470550"
    assert sols_50["title"] == "Southern Livestock Pasture Seed Mix - 50 Lb - 100,000 Sq Ft"
    assert sols_50["price"] == "242.21 USD"
    assert sols_50["shipping_weight"] == "50 lb"
    assert sols_50["item_group_id"] == "NS_0104"
    assert sols_50["custom_label_0"] == "pasture"

def test_build_gmc_row_plpr_10lb():
    rows = m.build_gmc_rows()
    plpr_10 = next(r for r in rows if r["mpn"] == "PB-PLPR-10-LB")
    assert plpr_10["id"] == "gla_470556"
    assert plpr_10["title"] == "Plains Prairie Native Seed Mix - 10 Lb - 29,000 Sq Ft"
    assert plpr_10["price"] == "157.99 USD"
    assert plpr_10["item_group_id"] == "NS_0105"


def test_get_sheets_token_calls_oauth(monkeypatch):
    captured = {}
    def fake_urlopen(req, timeout=30):
        captured["url"] = req.full_url
        body = req.data.decode()
        captured["body"] = body
        resp = MagicMock()
        resp.read.return_value = b'{"access_token": "test_token_abc"}'
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    token = m.get_sheets_token()
    assert token == "test_token_abc"
    assert "oauth2.googleapis.com/token" in captured["url"]
    assert "refresh_token" in captured["body"]


def test_push_gmc_calls_sheets_append(monkeypatch):
    call_log = []
    def fake_urlopen(req, timeout=30):
        call_log.append({"url": req.full_url, "method": req.get_method()})
        resp = MagicMock()
        resp.read.return_value = b'{"updates": {"updatedRows": 9}}'
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("add_new_listings.get_sheets_token", lambda: "fake_token")
    rows = m.build_gmc_rows()
    result = m.push_gmc(rows)
    assert result == 9
    assert any(m.SHEET_ID in c["url"] for c in call_log)
    assert any("append" in c["url"] for c in call_log)


def test_build_walmart_items_count():
    items = m.build_walmart_items()
    assert len(items) == 9

def test_build_walmart_item_cnir_5lb():
    items = m.build_walmart_items()
    cnir_5 = next(i for i in items if i["Orderable"]["sku"] == "CV-CNIR-5-LB-KIT")
    assert cnir_5["Orderable"]["productIdentifiers"]["productIdType"] == "GTIN"
    assert cnir_5["Orderable"]["productIdentifiers"]["productId"] == "840184629488"
    assert cnir_5["Orderable"]["price"] == 311.87
    assert cnir_5["Orderable"]["variantGroupId"] == "CVCNIR"
    assert cnir_5["Orderable"]["variantGroupInfo"]["groupingAttributes"][0]["value"] == "5"
    visible = cnir_5["Visible"]["Grass Seeds"]
    assert "California Native Ignition Resistant" in visible["productName"]
    assert "5 lb" in visible["productName"]
    assert visible["brand"] == "Nature's Seed"
    assert len(visible["keyFeatures"]) == 5
    assert visible["condition"] == "New"

def test_build_walmart_items_primary_variant():
    items = m.build_walmart_items()
    cnir_primary = next(i for i in items if i["Orderable"]["sku"] == "CV-CNIR-5-LB-KIT")
    cnir_secondary = next(i for i in items if i["Orderable"]["sku"] == "CV-CNIR-10-LB-KIT")
    assert cnir_primary["Orderable"]["variantGroupInfo"]["isPrimary"] is True
    assert cnir_secondary["Orderable"]["variantGroupInfo"]["isPrimary"] is False

def test_push_walmart_calls_submit_feed(monkeypatch):
    call_log = []
    def fake_submit(mp_items, feed_type="MP_MAINTENANCE"):
        call_log.append({"items": mp_items, "feed_type": feed_type})
        return "feed_abc123"
    monkeypatch.setattr("add_new_listings.submit_maintenance_feed", fake_submit)
    items = m.build_walmart_items()
    feed_id = m.push_walmart(items)
    assert feed_id == "feed_abc123"
    assert call_log[0]["feed_type"] == "MP_ITEM"
    assert len(call_log[0]["items"]) == 9


def test_build_amazon_rows_count():
    rows = m.build_amazon_rows()
    assert len(rows) == 3  # one parent row per product

def test_build_amazon_row_cnir():
    rows = m.build_amazon_rows()
    cnir = next(r for r in rows if r["parent_sku"] == "CV-CNIR")
    assert cnir["wc_id"] == 470543
    assert cnir["product_name"] == "California Native Ignition Resistant Seed Mix"
    assert cnir["bullet_1"] != ""
    assert cnir["bullet_5"] != ""
    assert len(cnir["description_plain"]) > 100
    assert "CV-CNIR-5-LB" in cnir["variation_skus"]
    assert "CV-CNIR-10-LB" in cnir["variation_skus"]
    assert "CV-CNIR-25-LB" in cnir["variation_skus"]
    assert "311.87" in cnir["variation_prices"]
    assert "5 lb" in cnir["size_options"]
    assert cnir["image_1"] != ""

def test_build_amazon_row_sols():
    rows = m.build_amazon_rows()
    sols = next(r for r in rows if r["parent_sku"] == "PB-SOLS")
    assert "PB-SOLS-10-LB" in sols["variation_skus"]
    assert "56.99" in sols["variation_prices"]
    assert "10 lb" in sols["size_options"]

def test_push_amazon_appends_to_csv(tmp_path, monkeypatch):
    import csv as csv_module
    monkeypatch.setattr("add_new_listings.AMAZON_CSV", tmp_path / "amazon_missing_products.csv")
    # Pre-populate with header + one existing row
    existing_cols = list(m.AMAZON_CSV_COLS)
    with open(tmp_path / "amazon_missing_products.csv", "w", newline="") as f:
        writer = csv_module.DictWriter(f, fieldnames=existing_cols)
        writer.writeheader()
        writer.writerow({c: "existing" for c in existing_cols})
    rows = m.build_amazon_rows()
    m.push_amazon(rows)
    with open(tmp_path / "amazon_missing_products.csv") as f:
        all_rows = list(csv_module.DictReader(f))
    assert len(all_rows) == 4  # 1 existing + 3 new
    skus = [r["parent_sku"] for r in all_rows]
    assert "CV-CNIR" in skus
    assert "PB-SOLS" in skus
    assert "PB-PLPR" in skus


def test_main_runs_all_channels_by_default(monkeypatch):
    called = []
    monkeypatch.setattr("add_new_listings.push_gmc", lambda rows: called.append("gmc") or 9)
    monkeypatch.setattr("add_new_listings.push_walmart", lambda items: called.append("walmart") or "feed_id")
    monkeypatch.setattr("add_new_listings.push_amazon", lambda rows: called.append("amazon"))
    m.main([])
    assert "gmc" in called
    assert "walmart" in called
    assert "amazon" in called

def test_main_runs_only_gmc_with_flag(monkeypatch):
    called = []
    monkeypatch.setattr("add_new_listings.push_gmc", lambda rows: called.append("gmc") or 9)
    monkeypatch.setattr("add_new_listings.push_walmart", lambda items: called.append("walmart") or "feed_id")
    monkeypatch.setattr("add_new_listings.push_amazon", lambda rows: called.append("amazon"))
    m.main(["--gmc"])
    assert called == ["gmc"]
