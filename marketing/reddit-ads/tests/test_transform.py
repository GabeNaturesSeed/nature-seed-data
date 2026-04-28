import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from transform import format_price


def test_format_price_normal():
    assert format_price("19.99") == "19.99 USD"


def test_format_price_integer_string():
    assert format_price("20") == "20.00 USD"


def test_format_price_float():
    assert format_price(19.99) == "19.99 USD"


def test_format_price_none_returns_none():
    assert format_price(None) is None


def test_format_price_empty_string_returns_none():
    assert format_price("") is None


def test_format_price_zero_returns_none():
    assert format_price("0") is None
    assert format_price(0) is None
    assert format_price("0.00") is None
