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
