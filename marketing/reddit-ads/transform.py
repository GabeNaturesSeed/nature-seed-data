"""Pure functions for transforming WC products into Reddit catalog rows.

No I/O, no env vars, no network calls live here. Everything is a function
of its inputs so the unit tests in tests/test_transform.py can exercise
every branch from JSON fixtures.
"""

import html
import re


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
    base = html.unescape(name or "")
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


ADDITIONAL_IMAGE_LIMIT = 9


def pick_image(parent, variation):
    """Return the variation's image URL if set, else the parent's first
    image, else None."""
    if variation:
        v_img = variation.get("image")
        if v_img and v_img.get("src"):
            return v_img["src"]
    images = (parent or {}).get("images") or []
    if images and images[0].get("src"):
        return images[0]["src"]
    return None


def additional_images(parent):
    """Return up to 9 extra image URLs (skipping the featured one) joined by ','."""
    images = (parent or {}).get("images") or []
    extras = [img.get("src", "") for img in images[1:1 + ADDITIONAL_IMAGE_LIMIT]]
    return ",".join(e for e in extras if e)


BRAND = "Nature's Seed"
GOOGLE_PRODUCT_CATEGORY = "5587"  # Home & Garden > Lawn & Garden > Gardening > Plants > Seeds


def _gtin_from_meta(meta_data):
    for entry in meta_data or []:
        if entry.get("key") == "_gtin":
            return str(entry.get("value") or "")
    return ""


def _product_type(product):
    cats = product.get("categories") or []
    return html.unescape(cats[0].get("name", "")) if cats else ""


def _description(product):
    text = product.get("short_description") or product.get("description") or ""
    return truncate_description(text)


def _sale_price(regular, sale, current_price):
    sale_fmt = format_price(sale)
    reg_fmt = format_price(regular)
    if not sale_fmt or not reg_fmt:
        return ""
    if float(sale) >= float(regular):
        return ""
    if current_price is not None:
        current_fmt = format_price(current_price)
        if current_fmt == sale_fmt:
            return ""
    return sale_fmt


def transform_simple_product(product):
    """Return one TSV row dict for a simple WC product."""
    pid = str(product["id"])
    return {
        "id": pid,
        "item_group_id": pid,
        "title": build_title(product.get("name"), []),
        "description": _description(product),
        "link": product.get("permalink", ""),
        "image_link": pick_image(product, None) or "",
        "additional_image_link": additional_images(product),
        "availability": "in stock",
        "price": format_price(product.get("price")) or "",
        "sale_price": _sale_price(product.get("regular_price"), product.get("sale_price"), product.get("price")),
        "brand": BRAND,
        "condition": "new",
        "gtin": _gtin_from_meta(product.get("meta_data")),
        "mpn": product.get("sku", "") or "",
        "product_type": _product_type(product),
        "google_product_category": GOOGLE_PRODUCT_CATEGORY,
    }


def transform_variable_product(parent, variations):
    """Return (rows, skipped) for a variable WC product.

    `variations` is the list returned by GET /products/{id}/variations.
    Variations that fail filters are recorded in `skipped` with their reason
    and excluded from `rows`. Each row uses the variation's id, but shares
    `item_group_id` with all siblings (the parent's id).
    """
    parent_id = str(parent["id"])
    rows = []
    skipped = []
    for v in variations:
        reason = should_skip_variation(v)
        if reason:
            skipped.append({"id": v["id"], "reason": reason})
            continue
        rows.append({
            "id": str(v["id"]),
            "item_group_id": parent_id,
            "title": build_title(parent.get("name"), v.get("attributes")),
            "description": _description(parent),
            "link": parent.get("permalink", ""),
            "image_link": pick_image(parent, v) or "",
            "additional_image_link": additional_images(parent),
            "availability": "in stock",
            "price": format_price(v.get("price")) or "",
            "sale_price": _sale_price(v.get("regular_price"), v.get("sale_price"), v.get("price")),
            "brand": BRAND,
            "condition": "new",
            "gtin": "",
            "mpn": v.get("sku", "") or parent.get("sku", "") or "",
            "product_type": _product_type(parent),
            "google_product_category": GOOGLE_PRODUCT_CATEGORY,
        })
    return rows, skipped


TSV_COLUMNS = [
    "id",
    "item_group_id",
    "title",
    "description",
    "link",
    "image_link",
    "additional_image_link",
    "availability",
    "price",
    "sale_price",
    "brand",
    "condition",
    "gtin",
    "mpn",
    "product_type",
    "google_product_category",
]


def _scrub_cell(value):
    """Replace tabs and newlines with single spaces — TSV cells cannot contain them."""
    s = "" if value is None else str(value)
    return s.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def write_tsv(file_like, rows):
    """Write header + rows to a text file-like object. Each row is a dict
    keyed by TSV_COLUMNS; missing keys become empty strings."""
    file_like.write("\t".join(TSV_COLUMNS) + "\n")
    for row in rows:
        cells = [_scrub_cell(row.get(col, "")) for col in TSV_COLUMNS]
        file_like.write("\t".join(cells) + "\n")
