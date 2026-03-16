#!/usr/bin/env python3
"""Search WooCommerce products by name and update ACF fields — v2 with strict matching."""

import requests
import time

WC_CK = "ck_9629579f1379f272169de8628edddb00b24737f9"
WC_CS = "cs_bf6dcf206d6ed26b83e55e8af62c16de26339815"
BASE = "https://naturesseed.com/wp-json/wc/v3"
AUTH = (WC_CK, WC_CS)

# Each entry: (search_term, mapping_key, name_must_contain_all, name_must_not_contain)
# name_must_contain_all: ALL of these substrings must appear in the product name (case-insensitive)
# name_must_not_contain: NONE of these may appear
SEARCHES = [
    ("bermudagrass", "bermuda", ["bermuda"], ["pasture", "horse", "goat", "mix for lawns"]),
    ("bermuda grass seed mix for lawns", "bermuda", ["bermuda", "mix for lawns"], []),
    ("switchgrass", "switchgrass", ["switchgrass"], ["tallgrass"]),
    ("horse pasture seed", "horse pasture", ["horse", "pasture"], ["cold", "cool", "warm", "transitional"]),
    ("cattle cool season pasture", "cattle cool", ["cattle", "pasture"], []),
    ("cattle warm season pasture", "cattle warm", ["cattle", "warm"], []),
    ("alpaca llama pasture", "alpaca", ["alpaca", "pasture"], []),
    ("goat pasture forage mix", "goat", ["goat", "pasture"], []),
    ("thin pasture", "thin pasture", ["thin", "pasture"], []),
    ("native cabin grass", "cabin", ["cabin"], []),
    ("first year perennial foundation wildflower", "first year", ["first", "wildflower"], []),
    ("rice hull", "rice hull", ["rice hull"], []),
    ("red clover seed", "red clover", ["red clover"], []),
    ("crimson clover", "crimson clover", ["crimson", "clover"], []),
    ("alsike clover", "alsike", ["alsike", "clover"], []),
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


def search_products(term, per_page=10):
    url = f"{BASE}/products"
    params = {"search": term, "per_page": per_page}
    r = requests.get(url, auth=AUTH, params=params)
    r.raise_for_status()
    return r.json()


def update_product_acf(product_id, acf_data):
    url = f"{BASE}/products/{product_id}"
    payload = {"meta_data": [{"key": k, "value": v} for k, v in acf_data.items()]}
    r = requests.put(url, auth=AUTH, json=payload)
    r.raise_for_status()
    return r.json()


def matches_filter(product, must_contain, must_not_contain):
    """Check if product name matches the filter criteria."""
    import html
    name = html.unescape(product["name"]).lower()
    for term in must_contain:
        if term.lower() not in name:
            return False
    for term in must_not_contain:
        if term.lower() in name:
            return False
    return True


# Track unique product IDs we've already updated (to avoid duplicate updates)
already_updated = set()
found_products = []
updated_products = []
not_found_searches = []

for search_term, mapping_key, must_contain, must_not_contain in SEARCHES:
    print(f"\n{'='*60}")
    print(f"Search: '{search_term}' | mapping: '{mapping_key}'")
    print(f"  Must contain: {must_contain}")
    print(f"  Must NOT contain: {must_not_contain}")
    print(f"{'='*60}")

    try:
        results = search_products(search_term)
        time.sleep(0.5)
    except Exception as e:
        print(f"  ERROR: {e}")
        not_found_searches.append((search_term, mapping_key, str(e)))
        continue

    # Filter
    matched = [p for p in results if matches_filter(p, must_contain, must_not_contain)]

    if not matched:
        print(f"  No matching products. Raw results ({len(results)}):")
        for p in results[:5]:
            import html
            print(f"    ID={p['id']} | {html.unescape(p['name'])} | slug={p['slug']} | {p['status']}")
        not_found_searches.append((search_term, mapping_key, "no match after filter"))
        continue

    for p in matched:
        import html
        name = html.unescape(p["name"])
        print(f"  MATCH: ID={p['id']} | {name} | slug={p['slug']} | {p['status']}")
        found_products.append({"id": p["id"], "name": name, "slug": p["slug"],
                               "status": p["status"], "mapping": mapping_key})

        if p["status"] == "publish" and p["id"] not in already_updated:
            acf_data = MAPPING[mapping_key]
            try:
                update_product_acf(p["id"], acf_data)
                time.sleep(0.5)
                print(f"    -> UPDATED with {mapping_key} ACF fields")
                updated_products.append({"id": p["id"], "name": name, "mapping": mapping_key})
                already_updated.add(p["id"])
            except Exception as e:
                print(f"    -> ERROR updating: {e}")
        elif p["id"] in already_updated:
            print(f"    -> Already updated, skipping")
        else:
            print(f"    -> Skipped (status={p['status']})")


# ── SUMMARY ──
print(f"\n\n{'='*60}")
print("FINAL SUMMARY")
print(f"{'='*60}")

print(f"\nSuccessfully updated {len(updated_products)} products:")
for p in updated_products:
    print(f"  ID={p['id']}: {p['name']} (mapping={p['mapping']})")

if not_found_searches:
    print(f"\nSearches with no match ({len(not_found_searches)}):")
    for term, key, reason in not_found_searches:
        print(f"  '{term}' (mapping={key}): {reason}")

# Check which of the original 14 mapping keys were covered
covered_keys = set(p["mapping"] for p in updated_products)
all_keys = set(MAPPING.keys())
missing = all_keys - covered_keys
if missing:
    print(f"\nMapping keys with NO published product updated: {missing}")
else:
    print(f"\nAll 14 mapping keys covered!")
