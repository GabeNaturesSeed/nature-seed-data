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
