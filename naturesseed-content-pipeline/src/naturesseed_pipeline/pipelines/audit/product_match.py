"""Product matcher built from wc_catalog_snapshot.

Three-tier matching per article:
  1. URL exact  — href contains a product permalink or /products/<slug>/
  2. Name exact — product name appears as substring in text (case-insensitive)
  3. Name fuzzy — rapidfuzz.token_set_ratio above threshold
"""

import re
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import WcCatalogSnapshot


@dataclass
class ProductRecord:
    wp_product_id: int
    slug: str
    name: str
    status: str
    permalink: str
    species_list: list[str]


@dataclass
class ProductMatcher:
    by_slug: dict[str, ProductRecord]
    by_name_lower: dict[str, ProductRecord]
    all_records: list[ProductRecord]


@dataclass
class ProductMatch:
    wp_product_id: int
    product_slug: str
    product_name: str
    is_active: bool
    match_type: str  # 'url' | 'exact' | 'fuzzy'
    confidence: float
    snippet: str


def build_matcher(session: Session) -> ProductMatcher:
    rows = session.execute(select(WcCatalogSnapshot)).scalars().all()
    records = [
        ProductRecord(
            wp_product_id=r.wp_product_id, slug=r.slug, name=r.name,
            status=r.status, permalink=r.permalink or "",
            species_list=r.species_list or [],
        )
        for r in rows
    ]
    return ProductMatcher(
        by_slug={r.slug: r for r in records},
        by_name_lower={r.name.lower(): r for r in records if r.name},
        all_records=records,
    )


_URL_PATTERN = re.compile(r"/products?/([a-z0-9][a-z0-9\-/]*)/?", re.IGNORECASE)


def _snippet(text: str, start: int, end: int, ctx: int = 60) -> str:
    lo = max(0, start - ctx); hi = min(len(text), end + ctx)
    return ("..." if lo > 0 else "") + text[lo:hi] + ("..." if hi < len(text) else "")


def find_product_mentions(
    text: str,
    html: str,
    matcher: ProductMatcher,
    fuzzy_threshold: float,
) -> list[ProductMatch]:
    matches: dict[int, ProductMatch] = {}

    # 1. URL-based
    for source in (html, text):
        for m in _URL_PATTERN.finditer(source or ""):
            slug = m.group(1).rstrip("/").split("/")[-1].lower()
            rec = matcher.by_slug.get(slug)
            if rec and rec.wp_product_id not in matches:
                matches[rec.wp_product_id] = ProductMatch(
                    wp_product_id=rec.wp_product_id,
                    product_slug=rec.slug, product_name=rec.name,
                    is_active=(rec.status == "publish"),
                    match_type="url", confidence=1.0,
                    snippet=_snippet(source, m.start(), m.end()),
                )

    # 2. Exact name
    text_lower = (text or "").lower()
    for name_lower, rec in matcher.by_name_lower.items():
        if rec.wp_product_id in matches:
            continue
        if len(name_lower) < 4:
            continue
        pos = text_lower.find(name_lower)
        if pos >= 0:
            matches[rec.wp_product_id] = ProductMatch(
                wp_product_id=rec.wp_product_id,
                product_slug=rec.slug, product_name=rec.name,
                is_active=(rec.status == "publish"),
                match_type="exact", confidence=0.9,
                snippet=_snippet(text, pos, pos + len(name_lower)),
            )

    # 3. Fuzzy name (token_set_ratio over sliding window; skip already-matched)
    if text_lower:
        tokens = text_lower.split()
        for name_lower, rec in matcher.by_name_lower.items():
            if rec.wp_product_id in matches:
                continue
            if len(name_lower) < 6:
                continue
            name_words = name_lower.split()
            window = max(len(name_words), 2)
            for i in range(0, max(len(tokens) - window + 1, 0)):
                chunk = " ".join(tokens[i:i + window])
                score = fuzz.token_set_ratio(name_lower, chunk) / 100.0
                if score >= fuzzy_threshold:
                    matches[rec.wp_product_id] = ProductMatch(
                        wp_product_id=rec.wp_product_id,
                        product_slug=rec.slug, product_name=rec.name,
                        is_active=(rec.status == "publish"),
                        match_type="fuzzy", confidence=score,
                        snippet=chunk,
                    )
                    break

    return list(matches.values())
