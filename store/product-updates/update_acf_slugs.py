#!/usr/bin/env python3
"""Search WooCommerce products by name and update ACF fields for 15 products."""

import requests
import time
import json

WC_CK = "ck_9629579f1379f272169de8628edddb00b24737f9"
WC_CS = "cs_bf6dcf206d6ed26b83e55e8af62c16de26339815"
BASE = "https://naturesseed.com/wp-json/wc/v3"
AUTH = (WC_CK, WC_CS)

# Search terms and their ACF mapping keys
SEARCHES = [
    ("bermuda", "bermuda"),
    ("switchgrass", "switchgrass"),
    ("horse pasture", "horse pasture"),
    ("cattle cool season pasture", "cattle cool"),
    ("cattle warm season pasture", "cattle warm"),
    ("alpaca llama pasture", "alpaca"),
    ("goat pasture", "goat"),
    ("thin pasture", "thin pasture"),
    ("cabin grass", "cabin"),
    ("first year wildflower", "first year"),
    ("rice hull", "rice hull"),
    ("red clover", "red clover"),
    ("crimson clover", "crimson clover"),
    ("alsike clover", "alsike"),
]

MAPPING = {
    "bermuda": {
        "title2": "How to Fertilize Your Bermudagrass Lawn",
        "link2": "https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/",
        "title3": "Bermuda Grass: Best Lawn Seed for Sunny Yards",
        "link3": "https://naturesseed.com/resources/lawn-turf/bermuda-grass-seed-best-lawn-seed-for-sunny-yards/",
    },
    "switchgrass": {
        "title2": "Switchgrass: A Grass of Many Uses",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/switchgrass-a-grass-of-many-uses/",
        "title3": "Attract Gobblers with Turkey Food Plots",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
    },
    "horse pasture": {
        "title2": "Endophyte Toxicity in Tall Fescue",
        "link2": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "cattle cool": {
        "title2": "Which Pasture Plants Make the Best Hay?",
        "link2": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
        "title3": "Endophyte Toxicity in Tall Fescue",
        "link3": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
    },
    "cattle warm": {
        "title2": "Which Pasture Plants Make the Best Hay?",
        "link2": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "alpaca": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Pasture Establishment: Seeding Methods",
        "link3": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
    },
    "goat": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Pasture Establishment: Seeding Methods",
        "link3": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
    },
    "thin pasture": {
        "title2": "Pasture Establishment: Seeding Methods",
        "link2": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
        "title3": "Which Pasture Plants Make the Best Hay?",
        "link3": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "cabin": {
        "title2": "What is a Low Maintenance Lawn?",
        "link2": "https://naturesseed.com/resources/lawn-turf/what-exactly-is-a-low-maintenance-lawn/",
        "title3": "Native Grass Series: Great Plains",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
    },
    "first year": {
        "title2": "Wildflower Buffer Strips for Water Quality",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
        "title3": "Keeping Deer From Eating Wildflowers",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
    },
    "rice hull": {
        "title2": "Guide to Grass Seed Germination",
        "link2": "https://naturesseed.com/resources/lawn-turf/a-guide-to-grass-seed-germination/",
        "title3": "How to Prepare Soil for Grass Seed",
        "link3": "https://naturesseed.com/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/",
    },
    "red clover": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Classy Clover: Best Addition to Your Lawn",
        "link3": "https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/",
    },
    "crimson clover": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Best Cover Crops for the Midwest",
        "link3": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
    },
    "alsike": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Which Pasture Plants Make the Best Hay?",
        "link3": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
}

def search_products(term):
    """Search WC products by term."""
    url = f"{BASE}/products"
    params = {"search": term, "per_page": 10}
    r = requests.get(url, auth=AUTH, params=params)
    r.raise_for_status()
    return r.json()

def update_product_acf(product_id, acf_data):
    """Update ACF fields on a product."""
    url = f"{BASE}/products/{product_id}"
    payload = {"meta_data": [{"key": k, "value": v} for k, v in acf_data.items()]}
    r = requests.put(url, auth=AUTH, json=payload)
    r.raise_for_status()
    return r.json()

def filter_results(products, search_term, mapping_key):
    """Filter search results to relevant products based on the mapping key."""
    filtered = []
    term_lower = search_term.lower()

    for p in products:
        name_lower = p["name"].lower()

        # For horse pasture, we want the hub page — skip specific cold/warm/transitional mixes
        if mapping_key == "horse pasture":
            if "horse" in name_lower and "pasture" in name_lower:
                # Skip ones that are clearly specific mixes (cold, warm, transitional)
                if any(x in name_lower for x in ["cold", "warm", "transitional", "cool"]):
                    continue
                filtered.append(p)
            continue

        # For cattle cool — need cattle + (cold or cool)
        if mapping_key == "cattle cool":
            if "cattle" in name_lower and ("cold" in name_lower or "cool" in name_lower):
                filtered.append(p)
            continue

        # For cattle warm — need cattle + warm, but NOT cold/cool
        if mapping_key == "cattle warm":
            if "cattle" in name_lower and "warm" in name_lower:
                filtered.append(p)
            continue

        # For generic searches, just include all results that seem relevant
        # The WC search API already does relevance matching
        filtered.append(p)

    return filtered


found_products = []
updated_products = []
not_found = []

for search_term, mapping_key in SEARCHES:
    print(f"\n{'='*60}")
    print(f"Searching for: '{search_term}' (mapping: '{mapping_key}')")
    print(f"{'='*60}")

    try:
        results = search_products(search_term)
        time.sleep(0.5)
    except Exception as e:
        print(f"  ERROR searching: {e}")
        not_found.append((search_term, mapping_key, str(e)))
        continue

    if not results:
        print(f"  No results found!")
        not_found.append((search_term, mapping_key, "no results"))
        continue

    # Filter to relevant products
    relevant = filter_results(results, search_term, mapping_key)

    if not relevant:
        print(f"  No relevant products after filtering. Raw results:")
        for p in results[:5]:
            print(f"    - ID={p['id']}, name='{p['name']}', slug='{p['slug']}', status={p['status']}")
        not_found.append((search_term, mapping_key, "no relevant products after filtering"))
        continue

    for p in relevant:
        print(f"  Found: ID={p['id']}, name='{p['name']}', slug='{p['slug']}', status={p['status']}")
        found_products.append({"id": p["id"], "name": p["name"], "slug": p["slug"], "status": p["status"], "mapping": mapping_key})

        if p["status"] == "publish":
            acf_data = MAPPING[mapping_key]
            print(f"    Updating ACF fields...")
            try:
                update_product_acf(p["id"], acf_data)
                time.sleep(0.5)
                print(f"    Updated successfully!")
                updated_products.append({"id": p["id"], "name": p["name"], "mapping": mapping_key})
            except Exception as e:
                print(f"    ERROR updating: {e}")
        else:
            print(f"    Skipping (status={p['status']})")

# Summary
print(f"\n\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
print(f"\nFound {len(found_products)} products:")
for p in found_products:
    print(f"  ID={p['id']}: {p['name']} (slug={p['slug']}, status={p['status']}, mapping={p['mapping']})")

print(f"\nUpdated {len(updated_products)} products:")
for p in updated_products:
    print(f"  ID={p['id']}: {p['name']} (mapping={p['mapping']})")

if not_found:
    print(f"\nNot found ({len(not_found)}):")
    for term, key, reason in not_found:
        print(f"  '{term}' (mapping={key}): {reason}")
else:
    print(f"\nAll products found and processed!")
