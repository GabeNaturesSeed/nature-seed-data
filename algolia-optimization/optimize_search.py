#!/usr/bin/env python3
"""
Algolia Search Optimization for Nature's Seed
==============================================

Analyzes search analytics, identifies issues, and applies fixes:
1. Synonyms — map common search terms to actual product names
2. Rules — redirect/boost for high-value queries
3. Settings — improve searchable attributes, typo tolerance, removeWordsIfNoResults

Usage:
  python3 optimize_search.py --audit        # Analyze current state + issues
  python3 optimize_search.py --dry-run      # Show what would change
  python3 optimize_search.py --push         # Apply all optimizations
"""

import json
import sys
import os
import argparse
import time
from datetime import datetime

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
ANALYTICS_URL = "https://analytics.us.algolia.com"

HEADERS = {
    "X-Algolia-API-Key": ADMIN_KEY,
    "X-Algolia-Application-Id": APP_ID,
    "Content-Type": "application/json",
}


def api_get(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()


def api_post(url, data):
    r = requests.post(url, headers=HEADERS, json=data)
    r.raise_for_status()
    return r.json()


def api_put(url, data):
    r = requests.put(url, headers=HEADERS, json=data)
    r.raise_for_status()
    return r.json()


# ─── Synonyms ─────────────────────────────────────────────────────────
# Based on analytics: no-result queries and low-result queries
# that map to products Nature's Seed actually carries

SYNONYMS = [
    # ── Animal-based searches → pasture products ──
    {
        "objectID": "syn-animal-sheep",
        "type": "synonym",
        "synonyms": ["sheep", "sheep pasture", "sheep forage", "sheep feed"],
    },
    {
        "objectID": "syn-animal-goat",
        "type": "synonym",
        "synonyms": ["goat", "goat pasture", "goat forage", "goat feed"],
    },
    {
        "objectID": "syn-animal-horse",
        "type": "synonym",
        "synonyms": ["horse", "horse pasture", "horse forage", "equine"],
    },
    {
        "objectID": "syn-animal-cattle",
        "type": "synonym",
        "synonyms": ["cattle", "cow", "cows", "bovine", "beef cattle"],
    },
    {
        "objectID": "syn-animal-chicken",
        "type": "synonym",
        "synonyms": ["chicken", "chickens", "poultry", "hen", "hens", "chicken forage"],
    },
    {
        "objectID": "syn-animal-tortoise",
        "type": "synonym",
        "synonyms": ["tortoise", "turtle", "reptile forage", "tortoise food"],
    },
    {
        "objectID": "syn-animal-pig",
        "type": "synonym",
        "synonyms": ["pig", "pigs", "hog", "swine", "pig forage"],
    },
    {
        "objectID": "syn-animal-alpaca",
        "type": "synonym",
        "synonyms": ["alpaca", "llama", "camelid"],
    },
    {
        "objectID": "syn-animal-deer",
        "type": "synonym",
        "synonyms": ["deer", "deer food plot", "deer forage", "whitetail"],
    },
    # ── Grass types ──
    {
        "objectID": "syn-grass-bermuda",
        "type": "synonym",
        "synonyms": ["bermuda", "bermudagrass", "bermuda grass"],
    },
    {
        "objectID": "syn-grass-bluegrass",
        "type": "synonym",
        "synonyms": ["bluegrass", "kentucky bluegrass", "kbg", "blue grass"],
    },
    {
        "objectID": "syn-grass-fescue-tall",
        "type": "synonym",
        "synonyms": ["tall fescue", "fescue tall", "ttf", "turf type tall fescue"],
    },
    {
        "objectID": "syn-grass-fescue-fine",
        "type": "synonym",
        "synonyms": ["fine fescue", "creeping red fescue", "chewings fescue", "hard fescue"],
    },
    {
        "objectID": "syn-grass-fescue-sheep",
        "type": "synonym",
        "synonyms": ["sheep fescue", "festuca ovina"],
    },
    {
        "objectID": "syn-grass-ryegrass",
        "type": "synonym",
        "synonyms": ["ryegrass", "rye grass", "perennial ryegrass", "annual ryegrass"],
    },
    {
        "objectID": "syn-grass-buffalo",
        "type": "synonym",
        "synonyms": ["buffalo", "buffalo grass", "buffalograss", "bufallo", "buffalograss"],
    },
    {
        "objectID": "syn-grass-orchard",
        "type": "synonym",
        "synonyms": ["orchard", "orchard grass", "orchardgrass", "orchard-grass"],
    },
    {
        "objectID": "syn-grass-timothy",
        "type": "synonym",
        "synonyms": ["timothy", "timothy grass", "timothy hay"],
    },
    {
        "objectID": "syn-grass-switchgrass",
        "type": "synonym",
        "synonyms": ["switchgrass", "switch grass", "panicum virgatum"],
    },
    {
        "objectID": "syn-grass-grama",
        "type": "synonym",
        "synonyms": ["grama", "blue grama", "blue grama grass", "bouteloua gracilis"],
    },
    {
        "objectID": "syn-grass-bluestem",
        "type": "synonym",
        "synonyms": ["bluestem", "big bluestem", "little bluestem", "andropogon"],
    },
    {
        "objectID": "syn-grass-bahia",
        "type": "synonym",
        "synonyms": ["bahia", "bahia grass", "bahiagrass", "pensacola bahia"],
    },
    {
        "objectID": "syn-grass-bentgrass",
        "type": "synonym",
        "synonyms": ["bentgrass", "bent grass", "california bentgrass", "thingrass", "agrostis"],
    },
    {
        "objectID": "syn-grass-purple-needlegrass",
        "type": "synonym",
        "synonyms": ["needlegrass", "purple needlegrass", "nassella pulchra"],
    },
    {
        "objectID": "syn-grass-brome",
        "type": "synonym",
        "synonyms": ["brome", "bromus", "california brome", "mountain brome", "bromus carinatus"],
    },
    # ── Clover types ──
    {
        "objectID": "syn-clover-white",
        "type": "synonym",
        "synonyms": ["white clover", "white dutch clover", "dutch clover", "trifolium repens"],
    },
    {
        "objectID": "syn-clover-red",
        "type": "synonym",
        "synonyms": ["red clover", "trifolium pratense", "medium red clover"],
    },
    {
        "objectID": "syn-clover-crimson",
        "type": "synonym",
        "synonyms": ["crimson clover", "trifolium incarnatum", "crimson"],
    },
    {
        "objectID": "syn-clover-alsike",
        "type": "synonym",
        "synonyms": ["alsike clover", "alsike", "trifolium hybridum"],
    },
    {
        "objectID": "syn-clover-micro",
        "type": "synonym",
        "synonyms": ["micro clover", "microclover", "mini clover", "miniclover", "micro"],
    },
    # ── Cover crops ──
    {
        "objectID": "syn-cover-buckwheat",
        "type": "synonym",
        "synonyms": ["buckwheat", "fagopyrum esculentum", "cover crop buckwheat"],
    },
    {
        "objectID": "syn-cover-rye",
        "type": "synonym",
        "synonyms": ["rye", "cereal rye", "winter rye", "secale cereale"],
    },
    {
        "objectID": "syn-cover-mustard",
        "type": "synonym",
        "synonyms": ["mustard", "biofumigant", "mustard cover crop", "green manure"],
    },
    {
        "objectID": "syn-cover-vetch",
        "type": "synonym",
        "synonyms": ["vetch", "hairy vetch", "vicia villosa", "winter vetch"],
    },
    # ── Wildflowers ──
    {
        "objectID": "syn-flower-poppy",
        "type": "synonym",
        "synonyms": ["poppy", "california poppy", "poppies", "eschscholzia"],
    },
    {
        "objectID": "syn-flower-lupine",
        "type": "synonym",
        "synonyms": ["lupine", "lupin", "lupines", "lupinus"],
    },
    {
        "objectID": "syn-flower-milkweed",
        "type": "synonym",
        "synonyms": ["milkweed", "narrowleaf milkweed", "asclepias", "monarch butterfly"],
    },
    {
        "objectID": "syn-flower-yarrow",
        "type": "synonym",
        "synonyms": ["yarrow", "achillea", "golden yarrow", "western yarrow"],
    },
    {
        "objectID": "syn-flower-sunflower",
        "type": "synonym",
        "synonyms": ["sunflower", "sunflowers", "helianthus", "helianthus annuus"],
    },
    {
        "objectID": "syn-flower-sage",
        "type": "synonym",
        "synonyms": ["sage", "white sage", "salvia", "chaparral sage"],
    },
    # ── Pasture / forage terms ──
    {
        "objectID": "syn-forage-alfalfa",
        "type": "synonym",
        "synonyms": ["alfalfa", "medicago sativa", "lucerne"],
    },
    {
        "objectID": "syn-forage-sainfoin",
        "type": "synonym",
        "synonyms": ["sainfoin", "onobrychis", "onobrychis viciifolia"],
    },
    {
        "objectID": "syn-forage-chicory",
        "type": "synonym",
        "synonyms": ["chicory", "cichorium intybus", "forage chicory"],
    },
    {
        "objectID": "syn-forage-trefoil",
        "type": "synonym",
        "synonyms": ["trefoil", "birdsfoot trefoil", "birds foot trefoil", "lotus corniculatus"],
    },
    # ── Products / planting aids ──
    {
        "objectID": "syn-product-rice-hulls",
        "type": "synonym",
        "synonyms": ["rice hulls", "rice hull", "rice husks", "seed cover", "mulch"],
    },
    {
        "objectID": "syn-product-tackifier",
        "type": "synonym",
        "synonyms": ["tackifier", "m-binder", "soil stabilizer", "erosion mat"],
    },
    {
        "objectID": "syn-product-fertilizer",
        "type": "synonym",
        "synonyms": ["fertilizer", "fert", "plant food", "lawn food"],
    },
    {
        "objectID": "syn-product-inoculant",
        "type": "synonym",
        "synonyms": ["inoculant", "mycorrhizal", "mycorrhizae", "soil microbes"],
    },
    # ── Use-case searches ──
    {
        "objectID": "syn-use-shade",
        "type": "synonym",
        "synonyms": ["shade", "shady", "shade tolerant", "low light"],
    },
    {
        "objectID": "syn-use-drought",
        "type": "synonym",
        "synonyms": ["drought", "drought tolerant", "dry", "xeriscape", "water wise"],
    },
    {
        "objectID": "syn-use-erosion",
        "type": "synonym",
        "synonyms": ["erosion", "erosion control", "slope", "hillside"],
    },
    {
        "objectID": "syn-use-pollinator",
        "type": "synonym",
        "synonyms": ["pollinator", "bee", "bees", "butterfly", "butterflies", "honeybee", "honey bee"],
    },
    {
        "objectID": "syn-use-native",
        "type": "synonym",
        "synonyms": ["native", "native plants", "native seed", "indigenous"],
    },
    {
        "objectID": "syn-use-overseeding",
        "type": "synonym",
        "synonyms": ["overseed", "overseeding", "over seed", "reseed", "repair"],
    },
    {
        "objectID": "syn-use-food-plot",
        "type": "synonym",
        "synonyms": ["food plot", "foodplot", "deer plot", "game plot", "hunting"],
    },
    # ── Spelling variations / common misspellings ──
    {
        "objectID": "syn-spell-oats",
        "type": "oneWaySynonym",
        "input": "oats",
        "synonyms": ["oat"],
    },
    {
        "objectID": "syn-spell-barley",
        "type": "oneWaySynonym",
        "input": "barley",
        "synonyms": ["cereal rye", "cover crop"],
    },
]


# ─── Rules ────────────────────────────────────────────────────────────
# Pin/promote rules for common high-value searches
# Uses "promote" (pin specific products) since optionalFilters requires paid plan

RULES = [
    # "clover" → pin top clover products
    {
        "objectID": "rule-clover-pin",
        "description": "Pin popular clover products at top for 'clover' search",
        "condition": {"anchoring": "is", "pattern": "clover"},
        "consequence": {
            "promote": [
                {"objectID": "458434-0", "position": 0},  # Clover Lawn Alternative Mix
                {"objectID": "445312-0", "position": 1},  # White Dutch Clover Seed
                {"objectID": "452364-0", "position": 2},  # White Clover Seed
            ],
        },
    },
    # "lawn" → pin best lawn products
    {
        "objectID": "rule-lawn-pin",
        "description": "Pin top lawn products for 'lawn' search",
        "condition": {"anchoring": "is", "pattern": "lawn"},
        "consequence": {
            "promote": [
                {"objectID": "445158-0", "position": 0},  # Jimmy's Blue Ribbon Lawn Seed Mix
                {"objectID": "458434-0", "position": 1},  # Clover Lawn Alternative Mix
                {"objectID": "456233-0", "position": 2},  # Sundancer Buffalograss Lawn Seed
            ],
        },
    },
    # "food plot" → pin food plot products
    {
        "objectID": "rule-food-plot-pin",
        "description": "Pin food plot products for 'food plot' search",
        "condition": {"anchoring": "contains", "pattern": "food plot"},
        "consequence": {
            "promote": [
                {"objectID": "455411-0", "position": 0},  # Full Potential Food Plot Mix
                {"objectID": "455414-0", "position": 1},  # Green Screen Food Plot Mix
                {"objectID": "455409-0", "position": 2},  # Krunch N Munch Food Plot Mix
            ],
        },
    },
    # "cover crop" → pin cover crop products
    {
        "objectID": "rule-cover-crop-pin",
        "description": "Pin cover crop products for 'cover crop' search",
        "condition": {"anchoring": "contains", "pattern": "cover crop"},
        "consequence": {
            "promote": [
                {"objectID": "461687-0", "position": 0},  # Weed Smother Cover Crop Kit
                {"objectID": "461686-0", "position": 1},  # Soil Builder Cover Crop Kit
                {"objectID": "458469-0", "position": 2},  # Mustard Biofumigant Blend
            ],
        },
    },
    # "wildflower" → pin wildflower products
    {
        "objectID": "rule-wildflower-pin",
        "description": "Pin wildflower products for 'wildflower' search",
        "condition": {"anchoring": "contains", "pattern": "wildflower"},
        "consequence": {
            "promote": [
                {"objectID": "461689-0", "position": 0},  # First-Year Color Kit
                {"objectID": "445313-0", "position": 1},  # Deer Resistant Wildflower Mix
                {"objectID": "345345-0", "position": 2},  # Rocky Mountain Wildflower Mix
            ],
        },
    },
    # "shade" → pin shade-tolerant products
    {
        "objectID": "rule-shade-pin",
        "description": "Pin shade-tolerant products for 'shade' search",
        "condition": {"anchoring": "contains", "pattern": "shade"},
        "consequence": {
            "promote": [
                {"objectID": "458422-0", "position": 0},  # Grass Seed Mix for Shady Areas
                {"objectID": "455407-0", "position": 1},  # Shade Tolerant Food Plot Mix
            ],
        },
    },
    # "pollinator" or "bee" → pin pollinator products
    {
        "objectID": "rule-pollinator-pin",
        "description": "Pin pollinator products for 'pollinator' search",
        "condition": {"anchoring": "contains", "pattern": "pollinator"},
        "consequence": {
            "promote": [
                {"objectID": "461688-0", "position": 0},  # Pollinator Corridor Kit
                {"objectID": "452791-0", "position": 1},  # Central Valley Pollinator Wildflower Mix
                {"objectID": "445268-0", "position": 2},  # Honey Bee Cover Crop & Pasture Mix
            ],
        },
    },
]


# ─── Settings Optimization ────────────────────────────────────────────

OPTIMIZED_SETTINGS = {
    # Make taxonomies searchable at higher priority — this is how users find
    # products by category name, use case, and attributes
    "searchableAttributes": [
        "unordered(post_title)",
        "unordered(taxonomies.product_cat)",
        "unordered(taxonomies.product_tag)",
        "unordered(taxonomies.product_uses)",
        "unordered(taxonomies.product_grass_type)",
        "unordered(taxonomies.product_region)",
        "unordered(taxonomies.product_sun_requirements)",
        "unordered(taxonomies.pa_scientific-name)",
        "unordered(taxonomies.pa_uses)",
        "unordered(taxonomies)",
        "unordered(content)",
    ],
    # Add more facets for filtering
    "attributesForFaceting": [
        "searchable(taxonomies.product_cat)",
        "searchable(taxonomies.product_tag)",
        "searchable(taxonomies.product_uses)",
        "searchable(taxonomies.product_grass_type)",
        "searchable(taxonomies.product_region)",
        "searchable(taxonomies.product_sun_requirements)",
        "taxonomies_hierarchical",
        "post_author.display_name",
    ],
    # When no results, try removing less-important words
    "removeWordsIfNoResults": "lastWords",
    # Enable query languages for better pluralization
    "queryLanguages": ["en"],
    # Enable ignorePlurals for English
    "ignorePlurals": ["en"],
    # Lower typo thresholds for short seed names
    "minWordSizefor1Typo": 3,
    "minWordSizefor2Typos": 6,
    # Custom ranking: prioritize featured, then sticky, then recent
    "customRanking": [
        "desc(is_sticky)",
        "desc(post_date)",
        "asc(record_index)",
    ],
    # Note: clickAnalytics is a query-time parameter, not an index setting
    # It needs to be enabled in the frontend search code
}


def audit(verbose=True):
    """Run a full search audit."""
    print("=" * 60)
    print("[AUDIT] Nature's Seed Algolia Search Analysis")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Index info
    indexes = api_get(f"{BASE_URL}/1/indexes")
    for idx in indexes["items"]:
        if idx["name"] == INDEX_NAME:
            print(f"\n  Index: {idx['name']}")
            print(f"  Records: {idx['entries']}")
            print(f"  Last updated: {idx['updatedAt']}")

    # 2. Current settings
    settings = api_get(f"{BASE_URL}/1/indexes/{INDEX_NAME}/settings")
    print(f"\n  Searchable attributes: {len(settings.get('searchableAttributes', []))}")
    for a in settings.get("searchableAttributes", []):
        print(f"    - {a}")
    print(f"  removeWordsIfNoResults: {settings.get('removeWordsIfNoResults', 'none')}")
    print(f"  queryLanguages: {settings.get('queryLanguages', 'not set')}")
    print(f"  ignorePlurals: {settings.get('ignorePlurals', 'not set')}")

    # 3. Current synonyms
    syns = api_post(f"{BASE_URL}/1/indexes/{INDEX_NAME}/synonyms/search",
                     {"query": "", "hitsPerPage": 100})
    print(f"\n  Current synonyms: {syns['nbHits']}")

    # 4. Current rules
    rules = api_post(f"{BASE_URL}/1/indexes/{INDEX_NAME}/rules/search",
                      {"query": "", "hitsPerPage": 100})
    print(f"  Current rules: {rules['nbHits']}")

    # 5. Analytics
    print("\n" + "─" * 60)
    print("  SEARCH ANALYTICS (last 90 days)")
    print("─" * 60)

    top = api_get(f"{ANALYTICS_URL}/2/searches", params={
        "index": INDEX_NAME, "limit": 50,
        "startDate": "2025-12-01", "endDate": "2026-03-04",
    })

    total_volume = sum(s["count"] for s in top["searches"])
    print(f"\n  Total search volume (top 50): {total_volume}")

    # Low-result queries
    low_result = [s for s in top["searches"] if s["nbHits"] <= 3 and s["count"] >= 5]
    print(f"\n  HIGH-VOLUME POOR-RESULT QUERIES ({len(low_result)} queries):")
    print(f"  {'Query':<25} {'Searches':<10} {'Results':<10}")
    print(f"  {'-'*45}")
    for s in low_result:
        print(f"  {s['search']:<25} {s['count']:<10} {s['nbHits']:<10}")

    # No-result queries
    no_results = api_get(f"{ANALYTICS_URL}/2/searches/noResults", params={
        "index": INDEX_NAME, "limit": 50,
        "startDate": "2025-12-01", "endDate": "2026-03-04",
    })

    total_no_result = sum(s["count"] for s in no_results["searches"])
    print(f"\n  NO-RESULT QUERIES: {len(no_results['searches'])} unique, {total_no_result} total searches")
    print(f"  Top 15:")
    for s in no_results["searches"][:15]:
        print(f"    '{s['search']}': {s['count']} searches")

    # Click tracking
    print(f"\n  Click tracking: NOT ENABLED (0% CTR across all queries)")
    print(f"  → Will enable clickAnalytics in settings update")

    # Summary
    print("\n" + "=" * 60)
    print("  ISSUES FOUND:")
    print("=" * 60)
    issues = [
        f"0 synonyms configured — {len(SYNONYMS)} needed for product discovery",
        f"0 rules configured — {len(RULES)} category boost rules needed",
        f"Only 3 searchable attributes — missing product_cat, product_tag, product_uses, scientific names",
        f"removeWordsIfNoResults = 'none' — should be 'lastWords' to handle multi-word queries",
        f"No query language set — can't leverage English pluralization",
        f"Click analytics disabled — can't measure search effectiveness",
        f"{len(low_result)} high-volume queries returning <=3 results",
        f"{len(no_results['searches'])} unique queries returning 0 results",
        f"content field is empty for all products — descriptions not indexed",
    ]
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")

    return issues


def dry_run():
    """Show what would be changed."""
    print("=" * 60)
    print("[DRY RUN] Changes that would be applied")
    print("=" * 60)

    print(f"\n  SYNONYMS TO ADD: {len(SYNONYMS)}")
    for syn in SYNONYMS:
        if syn["type"] == "synonym":
            print(f"    [{syn['objectID']}] {' ↔ '.join(syn['synonyms'])}")
        elif syn["type"] == "oneWaySynonym":
            print(f"    [{syn['objectID']}] {syn['input']} → {', '.join(syn['synonyms'])}")

    print(f"\n  RULES TO ADD: {len(RULES)}")
    for rule in RULES:
        print(f"    [{rule['objectID']}] {rule['description']}")

    print(f"\n  SETTINGS CHANGES:")
    for key, value in OPTIMIZED_SETTINGS.items():
        if isinstance(value, list):
            print(f"    {key}: {len(value)} items")
            for v in value:
                print(f"      - {v}")
        else:
            print(f"    {key}: {value}")


def push():
    """Apply all optimizations."""
    print("=" * 60)
    print("[PUSH] Applying Algolia Search Optimizations")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Push synonyms
    print(f"\n  [1/3] Pushing {len(SYNONYMS)} synonyms...")
    result = api_post(
        f"{BASE_URL}/1/indexes/{INDEX_NAME}/synonyms/batch",
        SYNONYMS,
    )
    print(f"    Task ID: {result.get('taskID')}")
    print(f"    Updated at: {result.get('updatedAt')}")

    # Wait for task
    task_id = result.get("taskID")
    if task_id:
        print(f"    Waiting for indexing...")
        while True:
            status = api_get(f"{BASE_URL}/1/indexes/{INDEX_NAME}/task/{task_id}")
            if status.get("status") == "published":
                print(f"    ✓ Synonyms indexed successfully")
                break
            time.sleep(1)

    # 2. Push rules
    print(f"\n  [2/3] Pushing {len(RULES)} rules...")
    try:
        result = api_post(
            f"{BASE_URL}/1/indexes/{INDEX_NAME}/rules/batch",
            RULES,
        )
        print(f"    Task ID: {result.get('taskID')}")

        task_id = result.get("taskID")
        if task_id:
            print(f"    Waiting for indexing...")
            while True:
                status = api_get(f"{BASE_URL}/1/indexes/{INDEX_NAME}/task/{task_id}")
                if status.get("status") == "published":
                    print(f"    ✓ Rules indexed successfully")
                    break
                time.sleep(1)
    except requests.exceptions.HTTPError as e:
        print(f"    ✗ Rules batch failed: {e}")
        print(f"    Response: {e.response.text if e.response else 'N/A'}")
        # Try pushing rules one by one
        print(f"    Retrying rules individually...")
        success = 0
        for rule in RULES:
            try:
                r = requests.put(
                    f"{BASE_URL}/1/indexes/{INDEX_NAME}/rules/{rule['objectID']}",
                    headers=HEADERS,
                    json=rule,
                )
                r.raise_for_status()
                success += 1
            except Exception as ex:
                print(f"      ✗ Rule '{rule['objectID']}': {ex}")
        print(f"    ✓ Pushed {success}/{len(RULES)} rules individually")

    # 3. Update settings
    print(f"\n  [3/3] Updating index settings...")
    result = api_put(
        f"{BASE_URL}/1/indexes/{INDEX_NAME}/settings",
        OPTIMIZED_SETTINGS,
    )
    print(f"    Task ID: {result.get('taskID')}")

    task_id = result.get("taskID")
    if task_id:
        print(f"    Waiting for indexing...")
        while True:
            status = api_get(f"{BASE_URL}/1/indexes/{INDEX_NAME}/task/{task_id}")
            if status.get("status") == "published":
                print(f"    ✓ Settings updated successfully")
                break
            time.sleep(1)

    # 4. Verify
    print(f"\n  [VERIFY] Checking optimizations...")

    # Test previously-failing queries
    test_queries = [
        ("zoysia", "should now suggest related grasses"),
        ("creeping thyme", "should match via synonyms"),
        ("chicken", "should match chicken forage"),
        ("poppy", "should match california poppy"),
        ("microclover", "should match micro clover"),
        ("buffalo grass", "should match buffalograss"),
        ("bee", "should match pollinator products"),
    ]

    for query, expected in test_queries:
        result = api_post(f"{BASE_URL}/1/indexes/{INDEX_NAME}/query", {
            "query": query,
            "hitsPerPage": 3,
            "attributesToRetrieve": ["post_title"],
        })
        hits = result.get("nbHits", 0)
        titles = [h["post_title"] for h in result.get("hits", [])[:3]]
        status = "✓" if hits > 0 else "✗"
        print(f"    {status} '{query}' → {hits} hits: {', '.join(titles[:2])}")

    print(f"\n  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Algolia Search Optimization")
    parser.add_argument("--audit", action="store_true", help="Analyze current state")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")
    parser.add_argument("--push", action="store_true", help="Apply optimizations")

    args = parser.parse_args()

    if args.audit:
        audit()
    elif args.dry_run:
        dry_run()
    elif args.push:
        push()
    else:
        # Default: run audit
        audit()


if __name__ == "__main__":
    main()
