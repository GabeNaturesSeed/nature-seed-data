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
