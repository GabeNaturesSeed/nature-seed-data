"""Orphan product reference detector.

Scans content_inventory rows for references to inactive/deleted WooCommerce products.
Detects: internal URLs, WC shortcodes, SKU mentions, fuzzy product name matches.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from rapidfuzz import fuzz

# Generic seed/plant words that appear in many product names — skip fuzzy matching on these
STOPWORDS = frozenset({
    "seed", "seeds", "mix", "blend", "grass", "lawn", "wildflower", "clover",
    "pasture", "hay", "cover", "crop", "annual", "perennial", "native",
    "tall", "short", "fine", "coated", "hulled", "organic",
})


@dataclass
class ProductIndex:
    """Lookup structure for active/inactive products."""

    by_id: dict[int, dict[str, Any]] = field(default_factory=dict)
    by_slug: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_sku: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_name_lower: dict[str, dict[str, Any]] = field(default_factory=dict)


def build_product_index(products: list[dict[str, Any]]) -> ProductIndex:
    """Build lookup indexes from a list of WC product dicts."""
    idx = ProductIndex()
    for p in products:
        pid = p.get("id")
        if pid:
            idx.by_id[int(pid)] = p
        slug = p.get("slug", "")
        if slug:
            idx.by_slug[slug] = p
        sku = p.get("sku", "")
        if sku:
            idx.by_sku[sku.upper()] = p
        name = p.get("name", "")
        if name:
            idx.by_name_lower[name.lower()] = p
    return idx


@dataclass
class OrphanHit:
    """A detected orphan reference."""

    reference_type: str  # url, shortcode, sku, name
    reference_value: str
    matched_product_id: int | None
    confidence: float  # 0.0-1.0
    snippet: str


def _extract_snippet(text: str, match_start: int, match_end: int, context: int = 50) -> str:
    """Extract ±context chars around a match position."""
    start = max(0, match_start - context)
    end = min(len(text), match_end + context)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def _find_url_orphans(
    text: str,
    html: str,
    active: ProductIndex,
    inactive: ProductIndex,
) -> list[OrphanHit]:
    """Find internal /product/<slug> URLs pointing to inactive products."""
    hits: list[OrphanHit] = []
    # Match /product/<slug> or /products/<slug> patterns
    pattern = re.compile(r"/products?/([\w-]+)/?", re.IGNORECASE)
    for source in [html, text]:
        if not source:
            continue
        for m in pattern.finditer(source):
            slug = m.group(1).lower()
            if slug in active.by_slug:
                continue  # active product, fine
            product = inactive.by_slug.get(slug)
            hits.append(OrphanHit(
                reference_type="url",
                reference_value=m.group(0),
                matched_product_id=product["id"] if product else None,
                confidence=1.0,
                snippet=_extract_snippet(source, m.start(), m.end()),
            ))
    return hits


def _find_shortcode_orphans(
    html: str,
    active: ProductIndex,
    inactive: ProductIndex,
) -> list[OrphanHit]:
    """Find WC shortcodes referencing inactive product IDs."""
    hits: list[OrphanHit] = []
    if not html:
        return hits
    # [product id="123"], [products ids="1,2,3"], [add_to_cart id="123"]
    pattern = re.compile(
        r'\[(?:product|products|add_to_cart)\s+[^]]*?ids?=["\']?([\d,\s]+)["\']?',
        re.IGNORECASE,
    )
    for m in pattern.finditer(html):
        id_str = m.group(1)
        ids = [int(x.strip()) for x in id_str.split(",") if x.strip().isdigit()]
        for pid in ids:
            if pid in active.by_id:
                continue
            product = inactive.by_id.get(pid)
            hits.append(OrphanHit(
                reference_type="shortcode",
                reference_value=m.group(0),
                matched_product_id=product["id"] if product else None,
                confidence=1.0,
                snippet=_extract_snippet(html, m.start(), m.end()),
            ))
    return hits


def _find_sku_orphans(
    text: str,
    inactive: ProductIndex,
) -> list[OrphanHit]:
    """Find word-boundary SKU matches against inactive products."""
    hits: list[OrphanHit] = []
    if not text:
        return hits
    for sku, product in inactive.by_sku.items():
        if len(sku) < 3:
            continue  # too short to reliably match
        pattern = re.compile(r"\b" + re.escape(sku) + r"\b", re.IGNORECASE)
        for m in pattern.finditer(text):
            hits.append(OrphanHit(
                reference_type="sku",
                reference_value=sku,
                matched_product_id=product["id"],
                confidence=1.0,
                snippet=_extract_snippet(text, m.start(), m.end()),
            ))
    return hits


def _find_fuzzy_name_orphans(
    text: str,
    inactive: ProductIndex,
) -> list[OrphanHit]:
    """Fuzzy-match inactive product names in content text.

    Only matches against INACTIVE products to avoid false positives.
    Threshold: token_set_ratio >= 90, min name length 4 chars, word boundary check.
    """
    hits: list[OrphanHit] = []
    if not text:
        return hits
    text_lower = text.lower()

    for name_lower, product in inactive.by_name_lower.items():
        if len(name_lower) < 4:
            continue
        # Skip names that are just stopwords
        name_words = set(name_lower.split())
        if name_words.issubset(STOPWORDS):
            continue

        # Quick substring pre-filter: at least one non-stopword from the name must appear
        non_stop_words = name_words - STOPWORDS
        if non_stop_words and not any(w in text_lower for w in non_stop_words):
            continue

        # Sliding window: check chunks roughly the size of the product name
        name_word_count = len(name_lower.split())
        text_words = text_lower.split()
        window_size = max(name_word_count, 2)

        for i in range(len(text_words) - window_size + 1):
            chunk = " ".join(text_words[i : i + window_size])
            score = fuzz.token_set_ratio(name_lower, chunk)
            if score >= 90:
                # Find position in original text for snippet
                chunk_start = text_lower.find(chunk)
                if chunk_start == -1:
                    chunk_start = 0
                hits.append(OrphanHit(
                    reference_type="name",
                    reference_value=name_lower,
                    matched_product_id=product["id"],
                    confidence=score / 100.0,
                    snippet=_extract_snippet(text, chunk_start, chunk_start + len(chunk)),
                ))
                break  # one match per product per content item is enough

    return hits


def scan_content(
    content_text: str | None,
    content_html: str | None,
    active: ProductIndex,
    inactive: ProductIndex,
) -> list[OrphanHit]:
    """Run all orphan detectors on a single content item."""
    text = content_text or ""
    html = content_html or ""
    hits: list[OrphanHit] = []
    hits.extend(_find_url_orphans(text, html, active, inactive))
    hits.extend(_find_shortcode_orphans(html, active, inactive))
    hits.extend(_find_sku_orphans(text, inactive))
    hits.extend(_find_fuzzy_name_orphans(text, inactive))
    return hits
