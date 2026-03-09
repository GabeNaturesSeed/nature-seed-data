#!/usr/bin/env python3
"""
Add contextual tags + no-catalog redirect rules to Algolia.

1. Parses WC product meta (detail_5_uses, detail_5_water, detail_5_sunshade,
   detail_5_native, supported_species, categories) into normalized contextual
   tags per product. Pushes as `contextual_tags` array on each Algolia record.

2. Creates Algolia Rules for searches where we don't carry the product,
   redirecting to the closest category with a custom message via userData.

Usage:
  python3 add_contextual_tags.py --dry-run    # Preview tags + rules
  python3 add_contextual_tags.py --push       # Apply to Algolia
"""

import json
import os
import re
import argparse
import time
from datetime import datetime
from pathlib import Path

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

WC_PRODUCTS_PATH = Path("/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/spring-2026-recovery/data/products_active.json")
DATA_DIR = Path(__file__).resolve().parent / "data"


def get_meta(product, key, default=""):
    """Get meta_data value by key."""
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


def get_meta_list(product, key):
    """Get meta_data value as a list (for supported_species etc.)."""
    for m in product.get("meta_data", []):
        if m.get("key") == key:
            val = m.get("value")
            if isinstance(val, list):
                return [str(v).strip() for v in val if v]
            if isinstance(val, str) and val.strip():
                return [val.strip()]
    return []


# ─── Tag Mapping Rules ────────────────────────────────────────────────
# Each rule: (tag_label, check_function)
# tag_label is what shows as a pill in search results

def _uses_contains(product, *keywords):
    """Check if detail_5_uses contains any of the keywords (case-insensitive)."""
    uses = get_meta(product, "detail_5_uses").lower()
    return any(kw.lower() in uses for kw in keywords)


def _water_is_low(product):
    """Check if detail_5_water indicates drought tolerance."""
    water = get_meta(product, "detail_5_water").lower()
    if not water:
        return False
    low_indicators = ["low", "drought", "minimal", "very low", "xeric"]
    high_indicators = ["high", "frequent", "moist", "wet"]
    return any(w in water for w in low_indicators) and not any(w in water for w in high_indicators)


def _sun_full(product):
    sun = get_meta(product, "sun_requirements").lower() or get_meta(product, "detail_5_sunshade").lower()
    return "full sun" in sun and "shade" not in sun


def _sun_shade_tolerant(product):
    sun = get_meta(product, "sun_requirements").lower() or get_meta(product, "detail_5_sunshade").lower()
    uses = get_meta(product, "detail_5_uses").lower()
    return "shade" in sun or "shade" in uses


def _is_native(product):
    native = get_meta(product, "detail_5_native").lower()
    return "native" in native and "introduced" not in native


def _is_california_native(product):
    native = get_meta(product, "detail_5_native").lower()
    cats = [c["name"].lower() for c in product.get("categories", [])]
    return "california" in native or "california collection" in cats


def _has_category(product, *cat_names):
    cats = [c["name"].lower() for c in product.get("categories", [])]
    return any(cn.lower() in cats for cn in cat_names)


def _has_species(product, species_name):
    species = get_meta_list(product, "supported_species")
    return species_name in species


def build_contextual_tags(product):
    """Build normalized contextual_tags array for a product."""
    tags = []

    # ── Use-case tags (from detail_5_uses) ──
    if _uses_contains(product, "drought", "water-conscious", "xeriscape", "xeriscap") or _water_is_low(product):
        tags.append("Drought Tolerant")

    if _uses_contains(product, "pollinator", "bee ", "honey bee", "butterfly"):
        tags.append("Attracts Pollinators")

    if _uses_contains(product, "erosion"):
        tags.append("Erosion Control")

    if _uses_contains(product, "pet", "dog"):
        tags.append("Pet Friendly")

    if _sun_shade_tolerant(product):
        tags.append("Shade Tolerant")

    if _sun_full(product):
        tags.append("Full Sun")

    if _is_native(product):
        tags.append("Native Species")

    if _is_california_native(product):
        tags.append("California Native")

    if _uses_contains(product, "wildlife", "habitat restoration", "ecological restoration"):
        tags.append("Wildlife Habitat")

    if _uses_contains(product, "nitrogen fix", "green manure"):
        tags.append("Nitrogen Fixing")

    if _uses_contains(product, "lawn alternative"):
        tags.append("Lawn Alternative")

    if _uses_contains(product, "sports turf", "high traffic", "high-traffic"):
        tags.append("Sports Turf")

    if _uses_contains(product, "hay", "haymaking"):
        tags.append("Hay Production")

    if _uses_contains(product, "forage", "grazing"):
        tags.append("Forage & Grazing")

    if _uses_contains(product, "food plot", "wildlife food"):
        tags.append("Food Plot")

    if _uses_contains(product, "cover crop", "cover cropping"):
        tags.append("Cover Crop")

    if _uses_contains(product, "ornamental"):
        tags.append("Ornamental")

    if _uses_contains(product, "meadow"):
        tags.append("Meadow")

    if _uses_contains(product, "slope"):
        tags.append("Slopes & Hillsides")

    if _uses_contains(product, "low-maintenance", "low maintenance"):
        tags.append("Low Maintenance")

    # ── Water level tags ──
    water = get_meta(product, "detail_5_water").lower()
    if water:
        if any(w in water for w in ["moderate to high", "high"]) and "low" not in water:
            tags.append("Regular Water")
        elif "moderate" in water and "low" not in water:
            tags.append("Moderate Water")
        elif any(w in water for w in ["low to moderate"]):
            tags.append("Low to Moderate Water")

    # ── Life form tags ──
    life = get_meta(product, "detail_5_life_form").lower()
    if "perennial" in life and "annual" not in life:
        tags.append("Perennial")
    elif "annual" in life and "perennial" not in life:
        tags.append("Annual")

    # ── Category-based tags ──
    if _has_category(product, "Lawn Seed", "Northern Lawn", "Southern Lawn", "Transitional Lawn"):
        tags.append("Lawn Seed")

    if _has_category(product, "TWCA - Water-Wise Lawn"):
        tags.append("Water-Wise")

    if _has_category(product, "Cover Crop Seed"):
        if "Cover Crop" not in tags:
            tags.append("Cover Crop")

    if _has_category(product, "Food Plot Seed"):
        if "Food Plot" not in tags:
            tags.append("Food Plot")

    if _has_category(product, "Clover Seed"):
        tags.append("Clover")

    if _has_category(product, "Sports Turf/High Traffic"):
        if "Sports Turf" not in tags:
            tags.append("Sports Turf")

    if _has_category(product, "Lawn Alternatives"):
        if "Lawn Alternative" not in tags:
            tags.append("Lawn Alternative")

    # ── Animal species tags ──
    for species in ["Cattle", "Sheep", "Goats", "Horse", "Bison",
                    "Alpaca/Llama", "Poultry", "Pig", "Tortoise", "Honey Bee"]:
        if _has_species(product, species):
            label = {
                "Alpaca/Llama": "Alpaca & Llama",
                "Goats": "Goat",
                "Horse": "Horse",
            }.get(species, species)
            tags.append(f"{label} Forage")

    return tags


# ─── No-Catalog Redirect Rules ───────────────────────────────────────
# For products customers search for but we don't carry
# Each: (query_pattern, replacement_query, redirect_category, message)

NO_CATALOG_REDIRECTS = [
    {
        "objectID": "no-catalog-zoysia",
        "condition": {"pattern": "zoysia", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "warm season lawn",
                "filters": "taxonomies.product_cat:'Lawn Seed'"
            },
            "userData": {
                "message": "We don't carry Zoysia grass seed this season. Here are other warm-season lawn grasses that might interest you:",
                "originalQuery": "zoysia"
            }
        },
        "description": "Redirect zoysia → warm season lawn alternatives"
    },
    {
        "objectID": "no-catalog-sorghum",
        "condition": {"pattern": "sorghum", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "cover crop forage"
            },
            "userData": {
                "message": "We don't carry Sorghum seed this season. Here are other cover crop and forage options that might interest you:",
                "originalQuery": "sorghum"
            }
        },
        "description": "Redirect sorghum → cover crop/forage alternatives"
    },
    {
        "objectID": "no-catalog-centipede",
        "condition": {"pattern": "centipede", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "warm season lawn",
                "filters": "taxonomies.product_cat:'Lawn Seed'"
            },
            "userData": {
                "message": "We don't carry Centipede grass seed this season. Here are other warm-season lawn grasses that might interest you:",
                "originalQuery": "centipede"
            }
        },
        "description": "Redirect centipede → warm season lawn alternatives"
    },
    {
        "objectID": "no-catalog-creeping-thyme",
        "condition": {"pattern": "creeping thyme", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "lawn alternative ground cover"
            },
            "userData": {
                "message": "We don't carry Creeping Thyme seed this season. Here are other lawn alternative ground covers that might interest you:",
                "originalQuery": "creeping thyme"
            }
        },
        "description": "Redirect creeping thyme → lawn alternative ground covers"
    },
    {
        "objectID": "no-catalog-thyme",
        "condition": {"pattern": "thyme", "anchoring": "is"},
        "consequence": {
            "params": {
                "query": "lawn alternative ground cover"
            },
            "userData": {
                "message": "We don't carry Thyme seed this season. Here are other lawn alternative ground covers that might interest you:",
                "originalQuery": "thyme"
            }
        },
        "description": "Redirect thyme → lawn alternative ground covers"
    },
    {
        "objectID": "no-catalog-dandelion",
        "condition": {"pattern": "dandelion", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "wildflower pollinator"
            },
            "userData": {
                "message": "We don't carry Dandelion seed this season. Here are other wildflower and pollinator options that might interest you:",
                "originalQuery": "dandelion"
            }
        },
        "description": "Redirect dandelion → wildflower/pollinator alternatives"
    },
    {
        "objectID": "no-catalog-cosmos",
        "condition": {"pattern": "cosmos", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "wildflower"
            },
            "userData": {
                "message": "We don't carry Cosmos seed this season. Here are other wildflower options that might interest you:",
                "originalQuery": "cosmos"
            }
        },
        "description": "Redirect cosmos → wildflower alternatives"
    },
    {
        "objectID": "no-catalog-zinnia",
        "condition": {"pattern": "zinnia", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "wildflower"
            },
            "userData": {
                "message": "We don't carry Zinnia seed this season. Here are other wildflower options that might interest you:",
                "originalQuery": "zinnia"
            }
        },
        "description": "Redirect zinnia → wildflower alternatives"
    },
    {
        "objectID": "no-catalog-dichondra",
        "condition": {"pattern": "dichondra", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "lawn alternative ground cover"
            },
            "userData": {
                "message": "We don't carry Dichondra seed this season. Here are other lawn alternative ground covers that might interest you:",
                "originalQuery": "dichondra"
            }
        },
        "description": "Redirect dichondra → lawn alternative ground covers"
    },
    {
        "objectID": "no-catalog-hibiscus",
        "condition": {"pattern": "hibiscus", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "wildflower"
            },
            "userData": {
                "message": "We don't carry Hibiscus seed this season. Here are other wildflower options that might interest you:",
                "originalQuery": "hibiscus"
            }
        },
        "description": "Redirect hibiscus → wildflower alternatives"
    },
    {
        "objectID": "no-catalog-marigold",
        "condition": {"pattern": "marigold", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "wildflower"
            },
            "userData": {
                "message": "We don't carry Marigold seed this season. Here are other wildflower options that might interest you:",
                "originalQuery": "marigold"
            }
        },
        "description": "Redirect marigold → wildflower alternatives"
    },
    {
        "objectID": "no-catalog-nasturtium",
        "condition": {"pattern": "nasturtium", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "wildflower pollinator"
            },
            "userData": {
                "message": "We don't carry Nasturtium seed this season. Here are other wildflower and pollinator options that might interest you:",
                "originalQuery": "nasturtium"
            }
        },
        "description": "Redirect nasturtium → wildflower/pollinator alternatives"
    },
    {
        "objectID": "no-catalog-crabgrass",
        "condition": {"pattern": "crabgrass", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "warm season lawn",
                "filters": "taxonomies.product_cat:'Lawn Seed'"
            },
            "userData": {
                "message": "We don't carry Crabgrass seed this season. Here are other warm-season lawn grasses that might interest you:",
                "originalQuery": "crabgrass"
            }
        },
        "description": "Redirect crabgrass → warm season lawn alternatives"
    },
    {
        "objectID": "no-catalog-cat-grass",
        "condition": {"pattern": "cat grass", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "forage"
            },
            "userData": {
                "message": "We don't carry Cat Grass seed this season. Here are other forage grass options that might interest you:",
                "originalQuery": "cat grass"
            }
        },
        "description": "Redirect cat grass → forage alternatives"
    },
    {
        "objectID": "no-catalog-tobacco",
        "condition": {"pattern": "tobacco", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "cover crop"
            },
            "userData": {
                "message": "We don't carry Tobacco seed. Here are other seed options that might interest you:",
                "originalQuery": "tobacco"
            }
        },
        "description": "Redirect tobacco → general alternatives"
    },
    {
        "objectID": "no-catalog-kurapia",
        "condition": {"pattern": "kurapia", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "lawn alternative ground cover"
            },
            "userData": {
                "message": "We don't carry Kurapia this season. Here are other lawn alternative ground covers that might interest you:",
                "originalQuery": "kurapia"
            }
        },
        "description": "Redirect kurapia → lawn alternative ground covers"
    },
    {
        "objectID": "no-catalog-comfrey",
        "condition": {"pattern": "comfrey", "anchoring": "contains"},
        "consequence": {
            "params": {
                "query": "cover crop nitrogen"
            },
            "userData": {
                "message": "We don't carry Comfrey seed this season. Here are other cover crop options that might interest you:",
                "originalQuery": "comfrey"
            }
        },
        "description": "Redirect comfrey → cover crop alternatives"
    },
]


# ─── Main Functions ───────────────────────────────────────────────────

def load_algolia_records():
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


def dry_run():
    print("=" * 70)
    print("[DRY RUN] Contextual Tags + No-Catalog Redirects")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    wc_products = load_wc_products()
    algolia_records = load_algolia_records()

    # ── Part 1: Contextual Tags ──
    print("\n─── CONTEXTUAL TAGS ───")

    tag_counts = {}
    product_tags = []
    for product in wc_products:
        wc_id = product["id"]
        if wc_id not in algolia_records:
            continue
        tags = build_contextual_tags(product)
        product_tags.append((product, algolia_records[wc_id], tags))
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    print(f"\n  Products with tags: {len(product_tags)}")
    print(f"  Unique tags: {len(tag_counts)}")

    # Sort tags by frequency
    print(f"\n  Tag distribution:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 40)
        print(f"    {tag:25s} {count:3d}  {bar}")

    # Sample products
    print(f"\n  Sample products:")
    for product, algolia, tags in product_tags[:5]:
        print(f"\n    {product['name']}")
        print(f"      Tags: {tags}")
        uses = get_meta(product, "detail_5_uses")
        water = get_meta(product, "detail_5_water")
        if uses:
            print(f"      Uses: {uses[:80]}")
        if water:
            print(f"      Water: {water}")

    # Products with 0 tags
    zero_tag = [p for p, a, t in product_tags if len(t) == 0]
    if zero_tag:
        print(f"\n  Products with 0 tags ({len(zero_tag)}):")
        for p in zero_tag:
            print(f"    - {p['name']}")

    # ── Part 2: No-Catalog Redirects ──
    print(f"\n─── NO-CATALOG REDIRECT RULES ───")
    print(f"  Total rules: {len(NO_CATALOG_REDIRECTS)}")
    for rule in NO_CATALOG_REDIRECTS:
        q = rule["condition"]["pattern"]
        msg = rule["consequence"]["userData"]["message"][:60]
        rq = rule["consequence"]["params"]["query"]
        print(f"    '{q}' → query='{rq}' | {msg}...")


def push():
    print("=" * 70)
    print("[PUSH] Contextual Tags + No-Catalog Redirects")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    wc_products = load_wc_products()
    algolia_records = load_algolia_records()

    # ── Part 1: Push contextual_tags ──
    print("\n─── PUSHING CONTEXTUAL TAGS ───")

    updates = []
    for product in wc_products:
        wc_id = product["id"]
        if wc_id not in algolia_records:
            continue
        tags = build_contextual_tags(product)
        updates.append({
            "objectID": algolia_records[wc_id]["objectID"],
            "contextual_tags": tags,
        })

    print(f"  Records to update: {len(updates)}")

    batch_requests = [
        {"action": "partialUpdateObject", "body": u} for u in updates
    ]

    batch_size = 50
    task_id = None
    for i in range(0, len(batch_requests), batch_size):
        batch = batch_requests[i:i + batch_size]
        result = requests.post(
            f"{BASE_URL}/1/indexes/{INDEX_NAME}/batch",
            headers=HEADERS,
            json={"requests": batch},
        )
        result.raise_for_status()
        task_id = result.json().get("taskID")
        print(f"    Batch {i // batch_size + 1}: {len(batch)} records (task {task_id})")

    if task_id:
        print("  Waiting for indexing...")
        while True:
            status = requests.get(
                f"{BASE_URL}/1/indexes/{INDEX_NAME}/task/{task_id}",
                headers=HEADERS,
            ).json()
            if status.get("status") == "published":
                print("  Tags indexed!")
                break
            time.sleep(1)

    # ── Part 2: Add contextual_tags to attributesForFaceting ──
    print("\n─── UPDATING SETTINGS ───")
    current_settings = requests.get(
        f"{BASE_URL}/1/indexes/{INDEX_NAME}/settings",
        headers=HEADERS,
    ).json()

    facets = current_settings.get("attributesForFaceting", [])
    if "contextual_tags" not in facets and "filterOnly(contextual_tags)" not in facets:
        facets.append("contextual_tags")
        result = requests.put(
            f"{BASE_URL}/1/indexes/{INDEX_NAME}/settings",
            headers=HEADERS,
            json={"attributesForFaceting": facets},
        )
        result.raise_for_status()
        print(f"  Added contextual_tags to facets: {facets}")
    else:
        print(f"  contextual_tags already in facets")

    # ── Part 3: Push no-catalog redirect rules ──
    print(f"\n─── PUSHING NO-CATALOG REDIRECT RULES ───")
    print(f"  Rules to push: {len(NO_CATALOG_REDIRECTS)}")

    # Push rules one at a time to handle errors gracefully
    pushed = 0
    failed = 0
    for rule in NO_CATALOG_REDIRECTS:
        try:
            result = requests.put(
                f"{BASE_URL}/1/indexes/{INDEX_NAME}/rules/{rule['objectID']}",
                headers=HEADERS,
                json=rule,
            )
            result.raise_for_status()
            pushed += 1
            print(f"    + {rule['objectID']}")
        except Exception as e:
            failed += 1
            print(f"    x {rule['objectID']}: {e}")

    print(f"\n  Rules pushed: {pushed}, failed: {failed}")

    # ── Verify ──
    print(f"\n─── VERIFICATION ───")

    # Check a product has contextual_tags
    result = requests.post(
        f"{BASE_URL}/1/indexes/{INDEX_NAME}/query",
        headers=HEADERS,
        json={
            "query": "clover lawn",
            "hitsPerPage": 1,
            "attributesToRetrieve": ["post_title", "contextual_tags"],
        },
    )
    data = result.json()
    if data.get("hits"):
        hit = data["hits"][0]
        print(f"  Tag check: {hit['post_title']}")
        print(f"    contextual_tags: {hit.get('contextual_tags', 'MISSING')}")

    # Check no-catalog redirect
    result = requests.post(
        f"{BASE_URL}/1/indexes/{INDEX_NAME}/query",
        headers=HEADERS,
        json={
            "query": "zoysia",
            "hitsPerPage": 3,
            "attributesToRetrieve": ["post_title"],
            "getRankingInfo": True,
        },
    )
    data = result.json()
    hits = data.get("nbHits", 0)
    ud = data.get("userData", [])
    titles = [h["post_title"] for h in data.get("hits", [])[:3]]
    print(f"\n  Redirect check: 'zoysia' → {hits} hits")
    print(f"    Results: {titles}")
    print(f"    userData: {ud}")

    print(f"\n  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Add contextual tags + no-catalog redirects")
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
