"""Pure functions for transforming WC products into Reddit catalog rows.

No I/O, no env vars, no network calls live here. Everything is a function
of its inputs so the unit tests in tests/test_transform.py can exercise
every branch from JSON fixtures.
"""


def format_price(value):
    """Format a price as '<float> USD' for the Reddit/Google Shopping spec.

    Returns None if the value is missing or zero — caller treats that as
    a skip signal.
    """
    if value is None or value == "":
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    return f"{amount:.2f} USD"


import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text):
    """Remove HTML tags and decode entities. Collapses whitespace to single spaces."""
    if not text:
        return ""
    no_tags = _TAG_RE.sub(" ", text)
    decoded = html.unescape(no_tags)
    return _WS_RE.sub(" ", decoded).strip()


def truncate_description(text, limit=1000):
    """Strip HTML, then cap at `limit` characters. Safe for UTF-8 (str slicing
    operates on code points, not bytes)."""
    cleaned = strip_html(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit]


TITLE_LIMIT = 150


def build_title(name, attributes):
    """Build the Reddit catalog title for one row.

    `attributes` is the variation's `attributes` list from the WC API:
    a list of {"name": ..., "option": ...} dicts. For simple products
    pass an empty list.
    """
    base = name or ""
    options = [a.get("option", "") for a in (attributes or []) if a.get("option")]
    if options:
        title = f"{base} — {' / '.join(options)}"
    else:
        title = base
    if len(title) > TITLE_LIMIT:
        title = title[:TITLE_LIMIT]
    return title


def should_skip_product(product):
    """Decide whether a parent WC product should be skipped before fetching
    variations. Returns a reason string (for logging) or None to keep.

    Variable parents are kept even if their stock/price look empty —
    those fields are populated on the variation level.
    """
    if product.get("status") != "publish":
        return "not_published"
    if not product.get("images"):
        return "no_image"
    if product.get("type") == "variable":
        return None
    if product.get("stock_status") != "instock":
        return "out_of_stock"
    if format_price(product.get("price")) is None:
        return "zero_price"
    return None


def should_skip_variation(variation):
    """Decide whether a single variation should be skipped. Image is checked
    elsewhere (variation can fall back to parent image)."""
    if variation.get("stock_status") != "instock":
        return "out_of_stock"
    if format_price(variation.get("price")) is None:
        return "zero_price"
    return None
