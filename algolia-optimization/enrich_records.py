#!/usr/bin/env python3
"""
Enrich Algolia product records with WooCommerce descriptions and metadata.

The WP Algolia plugin indexes products but leaves the `content` field empty.
This script pulls rich product data from WooCommerce and pushes it to Algolia
via partial updates, enriching each record with:
  - description text (stripped HTML)
  - short_description
  - product highlights
  - scientific names
  - uses/applications
  - growing info (sun, soil, seeding rate, etc.)
  - rank_math SEO keywords

Usage:
  python3 enrich_records.py --dry-run    # Show what would change
  python3 enrich_records.py --push       # Apply enrichments
"""

import json
import os
import re
import sys
import argparse
import time
from datetime import datetime
from pathlib import Path
from html import unescape

try:
    import requests
except ImportError:
    os.system("pip3 install requests")
    import requests

# ─── Config ───────────────────────────────────────────────────────────
APP_ID = "CR7906DEBT"
ADMIN_KEY = "48fa3067eaffd3b69093b3311a30b357"
INDEX_NAME = "wp_prod_posts_product"

BASE_URL = f"https://{APP_ID}-dsn.algolia.net"
HEADERS = {
    "X-Algolia-API-Key": ADMIN_KEY,
    "X-Algolia-Application-Id": APP_ID,
    "Content-Type": "application/json",
}

# WC product data
WC_PRODUCTS_PATH = Path("/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/spring-2026-recovery/data/products_active.json")
DATA_DIR = Path(__file__).resolve().parent / "data"

# Order data for popularity scoring
ORDER_FILES = [
    Path("/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/spring-2026-recovery/data/orders_2025_q3.json"),
    Path("/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/spring-2026-recovery/data/orders_2025_q4.json"),
    Path("/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/spring-2026-recovery/data/orders_2026_q1.json"),
]

# Seasonal boost config — categories to boost per quarter
# Current season: Spring (March 2026)
SEASONAL_BOOSTS = {
    "spring": {
        "boost_categories": [
            "Lawn Seed", "Clover Seed", "Cover Crop Seed",
            "Native Wildflower Seed & Seed Mixes", "Lawn Alternatives",
            "Northern Lawn", "Southern Lawn", "Transitional Lawn",
        ],
        "boost_value": 20,
    },
    "summer": {
        "boost_categories": [
            "Lawn Seed", "Southern Lawn", "Sports Turf/High Traffic",
            "TWCA - Water-Wise Lawn",
        ],
        "boost_value": 20,
    },
    "fall": {
        "boost_categories": [
            "Cover Crop Seed", "Northern Lawn", "Lawn Seed",
            "Pasture Seed",
        ],
        "boost_value": 20,
    },
    "winter": {
        "boost_categories": [],
        "boost_value": 0,
    },
}


def get_current_season():
    """Get current season based on month."""
    month = datetime.now().month
    if month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    elif month in (9, 10, 11):
        return "fall"
    return "winter"


def strip_html(html_str):
    """Remove HTML tags and decode entities."""
    if not html_str:
        return ""
    text = re.sub(r'<[^>]+>', ' ', html_str)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def get_meta(product, key, default=""):
    """Get meta_data value by key, always returns a string."""
    for m in product.get("meta_data", []):
        if m.get("key") == key:
            val = m.get("value", default)
            if isinstance(val, str):
                return val.strip()
            if isinstance(val, list):
                return " ".join(str(v) for v in val if v)
            if val is None:
                return default
            return str(val)
    return default


def build_searchable_content(product):
    """Build rich searchable content string from WC product data."""
    parts = []

    # Description (HTML stripped)
    desc = strip_html(product.get("description", ""))
    if desc:
        parts.append(desc)

    # Short description
    short_desc = strip_html(product.get("short_description", ""))
    if short_desc:
        parts.append(short_desc)

    # Product highlights
    for i in range(1, 7):
        hl = get_meta(product, f"product_highlight_{i}")
        if hl:
            parts.append(hl)

    # Product card headers/content (marketing copy) — display set 1
    for i in range(1, 6):
        header = get_meta(product, f"product_card_header_{i}")
        content = get_meta(product, f"product_card_content_{i}")
        if header:
            parts.append(header)
        if content:
            parts.append(strip_html(content))

    # Product card headers/content — display set 2 (installation/maintenance)
    for i in range(1, 5):
        header = get_meta(product, f"product_card_2_header_{i}")
        content = get_meta(product, f"product_card_2_content_{i}")
        if header:
            parts.append(header)
        if content:
            parts.append(strip_html(content))

    # Product content sections (including section 1)
    for i in range(1, 7):
        content = get_meta(product, f"product_content_{i}")
        if content:
            parts.append(strip_html(content))

    # Detail 5 fields (growing info)
    for field in ["detail_5_uses", "detail_5_color", "detail_5_life_form",
                  "detail_5_native", "detail_5_sunshade", "detail_5_water"]:
        val = get_meta(product, field)
        if val:
            parts.append(val)

    # Scientific name
    sci_name = get_meta(product, "scientific_name")
    if sci_name:
        parts.append(sci_name)

    # Growing info
    for field in ["sun_requirements", "soil_preference", "soil_ph",
                  "seeding_rate", "days_to_maturity", "height_when_mature"]:
        val = get_meta(product, field)
        if val:
            parts.append(val)

    # Rank Math SEO
    seo_kw = get_meta(product, "rank_math_focus_keyword")
    if seo_kw:
        parts.append(seo_kw)

    seo_desc = get_meta(product, "rank_math_description")
    if seo_desc:
        parts.append(seo_desc)

    # Q&A headers AND answers (complete FAQ content)
    for i in range(1, 7):
        q = get_meta(product, f"question_header_{i}")
        if q:
            parts.append(q)
        a = get_meta(product, f"answer_content_{i}")
        if a:
            parts.append(strip_html(a))

    # Supported species (for animal pasture products)
    species = get_meta(product, "supported_species")
    if species:
        parts.append(species)

    # Mix contents / composition
    mix = get_meta(product, "detail_5_mix_contents")
    if mix:
        parts.append(strip_html(mix))

    return " ".join(parts)


def load_popularity_scores():
    """Compute popularity scores (0-100) from order data."""
    from collections import Counter
    product_sales = Counter()
    for path in ORDER_FILES:
        if not path.exists():
            continue
        with open(path) as f:
            orders = json.load(f)
        for order in orders:
            if order.get("status") not in ("completed", "processing"):
                continue
            for item in order.get("line_items", []):
                product_sales[item.get("product_id", 0)] += item.get("quantity", 0)

    if not product_sales:
        return {}

    max_sales = max(product_sales.values())
    scores = {}
    for pid, qty in product_sales.items():
        # Normalize to 0-100 scale
        scores[pid] = round((qty / max_sales) * 100)
    return scores


def get_seasonal_boost(product):
    """Get seasonal boost value for a product based on its categories."""
    season = get_current_season()
    config = SEASONAL_BOOSTS.get(season, {})
    boost_cats = set(config.get("boost_categories", []))
    boost_val = config.get("boost_value", 0)

    product_cats = {c["name"] for c in product.get("categories", [])}
    if product_cats & boost_cats:
        return boost_val
    return 0


def build_enrichment(product, popularity_scores=None):
    """Build the partial update payload for an Algolia record."""
    content = build_searchable_content(product)

    enrichment = {
        "content": content,
    }

    # Add SKU
    sku = product.get("sku", "")
    if sku:
        enrichment["sku"] = sku

    # Add scientific name as a separate searchable field
    sci = get_meta(product, "scientific_name")
    if sci:
        enrichment["scientific_name"] = sci

    # Add SEO keywords
    seo_kw = get_meta(product, "rank_math_focus_keyword")
    if seo_kw:
        enrichment["seo_keywords"] = seo_kw

    # Add popularity score (0-100)
    if popularity_scores:
        score = popularity_scores.get(product["id"], 0)
        enrichment["popularity_score"] = score

    # Add seasonal boost
    boost = get_seasonal_boost(product)
    enrichment["seasonal_boost"] = boost

    # Combined ranking signal: popularity + seasonal boost
    base = popularity_scores.get(product["id"], 0) if popularity_scores else 0
    enrichment["ranking_score"] = base + boost

    return enrichment


def load_algolia_records():
    """Get all current Algolia records with objectIDs."""
    result = requests.post(
        f"{BASE_URL}/1/indexes/{INDEX_NAME}/query",
        headers=HEADERS,
        json={
            "query": "",
            "hitsPerPage": 200,
            "attributesToRetrieve": ["objectID", "post_title", "post_id"],
        },
    )
    result.raise_for_status()
    data = result.json()
    records = {}
    for hit in data.get("hits", []):
        pid = hit.get("post_id")
        if pid:
            records[pid] = hit
    return records


def load_wc_products():
    """Load WooCommerce products, excluding ADDON SKUs."""
    with open(WC_PRODUCTS_PATH) as f:
        products = json.load(f)
    return [p for p in products if "ADDON" not in p.get("sku", "").upper()]


def match_wc_to_algolia(wc_products, algolia_records):
    """Match WC products to Algolia records by post_id (WC product ID)."""
    matches = []
    unmatched_wc = []
    unmatched_algolia = list(algolia_records.keys())

    for product in wc_products:
        wc_id = product["id"]
        if wc_id in algolia_records:
            matches.append((product, algolia_records[wc_id]))
            if wc_id in unmatched_algolia:
                unmatched_algolia.remove(wc_id)
        else:
            unmatched_wc.append(product)

    return matches, unmatched_wc, unmatched_algolia


def dry_run():
    """Show what would be enriched."""
    print("=" * 60)
    print("[DRY RUN] Algolia Record Enrichment")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Season: {get_current_season()}")
    print("=" * 60)

    wc_products = load_wc_products()
    algolia_records = load_algolia_records()
    popularity = load_popularity_scores()

    print(f"\n  WC products: {len(wc_products)}")
    print(f"  Algolia records: {len(algolia_records)}")
    print(f"  Products with popularity data: {len(popularity)}")

    matches, unmatched_wc, unmatched_algolia = match_wc_to_algolia(
        wc_products, algolia_records
    )
    print(f"  Matched: {len(matches)}")
    print(f"  Unmatched WC: {len(unmatched_wc)}")
    print(f"  Unmatched Algolia: {len(unmatched_algolia)}")

    print(f"\n  Sample enrichments (first 3):")
    for product, algolia in matches[:3]:
        enrichment = build_enrichment(product, popularity)
        content_len = len(enrichment.get("content", ""))
        print(f"\n  {product['name']} (ID: {product['id']})")
        print(f"    objectID: {algolia['objectID']}")
        print(f"    Content length: {content_len} chars")
        print(f"    Content preview: {enrichment['content'][:200]}...")
        print(f"    popularity_score: {enrichment.get('popularity_score', 0)}")
        print(f"    seasonal_boost: {enrichment.get('seasonal_boost', 0)}")
        print(f"    ranking_score: {enrichment.get('ranking_score', 0)}")
        if enrichment.get("scientific_name"):
            print(f"    Scientific name: {enrichment['scientific_name']}")

    # Stats
    total_content = 0
    has_sci_name = 0
    has_seo = 0
    boosted = 0
    for product, algolia in matches:
        enrichment = build_enrichment(product, popularity)
        total_content += len(enrichment.get("content", ""))
        if enrichment.get("scientific_name"):
            has_sci_name += 1
        if enrichment.get("seo_keywords"):
            has_seo += 1
        if enrichment.get("seasonal_boost", 0) > 0:
            boosted += 1

    print(f"\n  Enrichment stats:")
    print(f"    Avg content length: {total_content // len(matches) if matches else 0} chars")
    print(f"    Products with scientific name: {has_sci_name}")
    print(f"    Products with SEO keywords: {has_seo}")
    print(f"    Products with seasonal boost: {boosted}")


def push():
    """Push enrichments to Algolia."""
    print("=" * 60)
    print("[PUSH] Enriching Algolia Records")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Season: {get_current_season()}")
    print("=" * 60)

    wc_products = load_wc_products()
    algolia_records = load_algolia_records()
    popularity = load_popularity_scores()

    matches, _, _ = match_wc_to_algolia(wc_products, algolia_records)
    print(f"\n  Matched {len(matches)} products for enrichment")
    print(f"  Products with popularity data: {len(popularity)}")

    # Build batch update
    updates = []
    for product, algolia in matches:
        enrichment = build_enrichment(product, popularity)
        enrichment["objectID"] = algolia["objectID"]
        updates.append(enrichment)

    # Push via batch partial update
    print(f"\n  Pushing {len(updates)} partial updates...")

    # Algolia batch API — use addObject with createIfNotExists=false
    batch_requests = []
    for update in updates:
        batch_requests.append({
            "action": "partialUpdateObject",
            "body": update,
        })

    # Batch in groups of 50
    batch_size = 50
    total_pushed = 0
    for i in range(0, len(batch_requests), batch_size):
        batch = batch_requests[i:i + batch_size]
        result = requests.post(
            f"{BASE_URL}/1/indexes/{INDEX_NAME}/batch",
            headers=HEADERS,
            json={"requests": batch},
        )
        result.raise_for_status()
        task_id = result.json().get("taskID")
        total_pushed += len(batch)
        print(f"    Batch {i // batch_size + 1}: {len(batch)} records (task {task_id})")

    # Wait for last task
    if task_id:
        print(f"\n  Waiting for indexing...")
        while True:
            status = requests.get(
                f"{BASE_URL}/1/indexes/{INDEX_NAME}/task/{task_id}",
                headers=HEADERS,
            ).json()
            if status.get("status") == "published":
                print(f"  Indexing complete!")
                break
            time.sleep(1)

    # Verify
    print(f"\n  [VERIFY] Checking enrichment...")
    test_queries = ["pollinator habitat", "bermuda drought tolerant", "soil ph 6.0"]
    for query in test_queries:
        result = requests.post(
            f"{BASE_URL}/1/indexes/{INDEX_NAME}/query",
            headers=HEADERS,
            json={"query": query, "hitsPerPage": 3, "attributesToRetrieve": ["post_title"]},
        )
        data = result.json()
        hits = data.get("nbHits", 0)
        titles = [h["post_title"] for h in data.get("hits", [])[:3]]
        status = "+" if hits > 0 else "="
        print(f"    {status} '{query}' → {hits} hits: {', '.join(titles[:2])}")

    print(f"\n  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Total records enriched: {total_pushed}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Enrich Algolia records with WC data")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    elif args.push:
        push()
    else:
        dry_run()


if __name__ == "__main__":
    main()
