#!/usr/bin/env python3
"""Fix remaining products: cattle warm override, horse pasture hub, red clover, crimson clover."""

import requests
import time
import html

WC_CK = "ck_9629579f1379f272169de8628edddb00b24737f9"
WC_CS = "cs_bf6dcf206d6ed26b83e55e8af62c16de26339815"
BASE = "https://naturesseed.com/wp-json/wc/v3"
AUTH = (WC_CK, WC_CS)

MAPPING = {
    "cattle warm": {
        "title2": "Which Pasture Plants Make the Best Hay?",
        "link2": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "horse pasture": {
        "title2": "Endophyte Toxicity in Tall Fescue",
        "link2": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
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
}


def search_products(term, per_page=20):
    url = f"{BASE}/products"
    params = {"search": term, "per_page": per_page}
    r = requests.get(url, auth=AUTH, params=params)
    r.raise_for_status()
    return r.json()


def get_product_by_slug(slug):
    url = f"{BASE}/products"
    params = {"slug": slug, "per_page": 1}
    r = requests.get(url, auth=AUTH, params=params)
    r.raise_for_status()
    return r.json()


def update_product_acf(product_id, acf_data):
    url = f"{BASE}/products/{product_id}"
    payload = {"meta_data": [{"key": k, "value": v} for k, v in acf_data.items()]}
    r = requests.put(url, auth=AUTH, json=payload)
    r.raise_for_status()
    return r.json()


updated = []

# ── 1. Fix Cattle Warm: ID 445164 got cattle cool mapping, needs cattle warm ──
print("=" * 60)
print("1. Fixing Warm Season Cattle Pasture (ID 445164) -> cattle warm mapping")
try:
    update_product_acf(445164, MAPPING["cattle warm"])
    time.sleep(0.5)
    print("   UPDATED successfully")
    updated.append(("445164", "Warm Season Cattle Pasture Seed Mix", "cattle warm"))
except Exception as e:
    print(f"   ERROR: {e}")

# ── 2. Horse Pasture hub page ──
print("\n" + "=" * 60)
print("2. Searching for Horse Pasture hub page...")
# Try various slug patterns
for slug in ["horse-pasture-seed", "horse-pastures-seed", "horse-pasture", "horse-pastures"]:
    results = get_product_by_slug(slug)
    time.sleep(0.5)
    if results:
        for p in results:
            name = html.unescape(p["name"])
            print(f"   Found by slug '{slug}': ID={p['id']} | {name} | status={p['status']}")
            if p["status"] == "publish":
                update_product_acf(p["id"], MAPPING["horse pasture"])
                time.sleep(0.5)
                print(f"   UPDATED successfully")
                updated.append((str(p["id"]), name, "horse pasture"))
        break
else:
    # Try broader search
    print("   No slug match. Trying broader search...")
    results = search_products("horse pasture", per_page=20)
    time.sleep(0.5)
    for p in results:
        name = html.unescape(p["name"])
        slug = p["slug"]
        print(f"   ID={p['id']} | {name} | slug={slug} | {p['status']}")
        # Look for a generic horse pasture product (hub page)
        name_l = name.lower()
        if "horse" in name_l and "pasture" in name_l:
            if not any(x in name_l for x in ["cold", "cool", "warm", "transitional"]):
                if p["status"] == "publish":
                    update_product_acf(p["id"], MAPPING["horse pasture"])
                    time.sleep(0.5)
                    print(f"   -> UPDATED as horse pasture hub")
                    updated.append((str(p["id"]), name, "horse pasture"))

# ── 3. Red Clover ──
print("\n" + "=" * 60)
print("3. Searching for Red Clover Seed...")
# Try slug first
for slug in ["red-clover-seed", "red-clover", "medium-red-clover"]:
    results = get_product_by_slug(slug)
    time.sleep(0.5)
    if results:
        for p in results:
            name = html.unescape(p["name"])
            print(f"   Found by slug '{slug}': ID={p['id']} | {name} | status={p['status']}")
            if p["status"] == "publish":
                update_product_acf(p["id"], MAPPING["red clover"])
                time.sleep(0.5)
                print(f"   UPDATED successfully")
                updated.append((str(p["id"]), name, "red clover"))
        break
else:
    # Broader search
    print("   No slug match. Trying search 'red clover'...")
    results = search_products("red clover", per_page=20)
    time.sleep(0.5)
    for p in results:
        name = html.unescape(p["name"])
        print(f"   ID={p['id']} | {name} | slug={p['slug']} | {p['status']}")
        if "red clover" in name.lower() and p["status"] == "publish":
            update_product_acf(p["id"], MAPPING["red clover"])
            time.sleep(0.5)
            print(f"   -> UPDATED")
            updated.append((str(p["id"]), name, "red clover"))

    # If still nothing, try searching just "clover"
    if not any(u[2] == "red clover" for u in updated):
        print("   Still not found. Searching 'clover seed'...")
        results = search_products("clover seed", per_page=30)
        time.sleep(0.5)
        for p in results:
            name = html.unescape(p["name"])
            if "red" in name.lower() and "clover" in name.lower():
                print(f"   ID={p['id']} | {name} | slug={p['slug']} | {p['status']}")
                if p["status"] == "publish":
                    update_product_acf(p["id"], MAPPING["red clover"])
                    time.sleep(0.5)
                    print(f"   -> UPDATED")
                    updated.append((str(p["id"]), name, "red clover"))

# ── 4. Crimson Clover ──
print("\n" + "=" * 60)
print("4. Searching for Crimson Clover...")
for slug in ["crimson-clover-crop-seed", "crimsom-clover-crop-seed", "crimson-clover-seed", "crimson-clover"]:
    results = get_product_by_slug(slug)
    time.sleep(0.5)
    if results:
        for p in results:
            name = html.unescape(p["name"])
            print(f"   Found by slug '{slug}': ID={p['id']} | {name} | status={p['status']}")
            if p["status"] == "publish":
                update_product_acf(p["id"], MAPPING["crimson clover"])
                time.sleep(0.5)
                print(f"   UPDATED successfully")
                updated.append((str(p["id"]), name, "crimson clover"))
        break
else:
    # Broader search
    print("   No slug match. Trying search 'crimson'...")
    results = search_products("crimson", per_page=20)
    time.sleep(0.5)
    for p in results:
        name = html.unescape(p["name"])
        print(f"   ID={p['id']} | {name} | slug={p['slug']} | {p['status']}")
        if "crimson" in name.lower() and p["status"] == "publish":
            update_product_acf(p["id"], MAPPING["crimson clover"])
            time.sleep(0.5)
            print(f"   -> UPDATED")
            updated.append((str(p["id"]), name, "crimson clover"))

    # Try 'crimsom' (typo variant from original slug)
    if not any(u[2] == "crimson clover" for u in updated):
        print("   Trying 'crimsom' (typo)...")
        results = search_products("crimsom", per_page=10)
        time.sleep(0.5)
        for p in results:
            name = html.unescape(p["name"])
            print(f"   ID={p['id']} | {name} | slug={p['slug']} | {p['status']}")

# ── SUMMARY ──
print("\n" + "=" * 60)
print("FIX SUMMARY")
print("=" * 60)
if updated:
    for pid, name, mapping in updated:
        print(f"  ID={pid}: {name} -> {mapping}")
else:
    print("  No products updated in this fix run.")

still_missing = {"horse pasture", "red clover", "crimson clover"} - {u[2] for u in updated}
if still_missing:
    print(f"\nStill missing: {still_missing}")
