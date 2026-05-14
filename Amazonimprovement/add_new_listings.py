#!/usr/bin/env python3
"""
Add new product listings to GMC Sheet, Walmart, and Amazon draft.

Usage:
  python3 add_new_listings.py            # all three channels
  python3 add_new_listings.py --gmc      # GMC Sheet only
  python3 add_new_listings.py --walmart  # Walmart only
  python3 add_new_listings.py --amazon   # Amazon CSV only
"""

import argparse
import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
ENV_PATH = PROJECT_DIR / ".env"
AMAZON_CSV = SCRIPT_DIR / "amazon_missing_products.csv"
WALMART_CLIENT_DIR = PROJECT_DIR / "marketplaces" / "walmart-optimization"
sys.path.insert(0, str(WALMART_CLIENT_DIR))

# ── Env ───────────────────────────────────────────────────────────────────────
def _load_env():
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env

ENV = _load_env()

# ── GMC Sheet ─────────────────────────────────────────────────────────────────
SHEET_ID = "12u2Uj0gHNImAQKDA1qnDUxlw4czL4DNuHbuUFqULbuU"
SHEET_RANGE = "Sheet1"

GMC_COLS = [
    "id", "title", "description", "availability", "condition", "price", "link",
    "image_link", "brand", "google_product_category", "fb_product_category",
    "quantity_to_sell_on_facebook", "sale_price", "sale_price_effective_date",
    "item_group_id", "gender", "color", "size", "age_group", "material", "pattern",
    "shipping", "shipping_weight", "gtin", "video[0].url", "video[0].tag[0]",
    "product_tags[0]", "product_tags[1]", "style[0]", "mpn",
    "custom_label_0", "custom_label_1", "custom_label_2",
]

# ── Walmart lazy import (module-level for monkeypatching in tests) ─────────────
try:
    from walmart_client import submit_maintenance_feed
except ImportError:
    submit_maintenance_feed = None

# ── Helper Functions ──────────────────────────────────────────────────────────
def _size_slug(lb):
    """Convert lb integer to WC attribute slug: 5 -> '5-lb'"""
    return f"{lb}-lb"

def _sqft_fmt(sqft):
    """Format sq ft with commas: 29000 -> '29,000'"""
    return f"{sqft:,}"

# ── Product Data ──────────────────────────────────────────────────────────────
PRODUCTS = [
    {
        "parent_sku": "CV-CNIR",
        "name": "California Native Ignition Resistant Seed Mix",
        "wc_id": 470543,
        "gtin": "840184629488",
        "item_group_id": "NS_0103",
        "custom_label_0": "specialty",
        "slug": "california-native-ignition-resistant-seed-mix",
        "category_path": "specialty-seed",
        "image": "https://naturesseed.com/wp-content/uploads/2026/05/California-Native-Ignition-Resistant-Seed-Mix-.png",
        "description": (
            "The California Native Ignition Resistant Seed Mix is a seven-species blend designed to "
            "establish a fire-resistant, low-fuel ground cover in California's wildland-urban interface "
            "and foothill landscapes. Purple Needlegrass anchors the mix at 30%, providing the state "
            "grass of California in a naturally fine-textured, low-growing form that accumulates less "
            "dry biomass than non-native annual grasses. Blue Wildrye and Sandberg Bluegrass fill "
            "structural roles as perennial bunchgrasses that retain basal moisture between rains, "
            "reducing ignition potential. Small Fescue adds low-growing coverage that competes "
            "effectively against fire-prone annual grasses like wild oats and bromes. Deerweed and "
            "Miniature Lupine are nitrogen-fixing forbs that improve soil fertility while providing "
            "pollinator habitat. Great Valley Gumweed serves as a late-season bloomer that maintains "
            "ground cover into the fall fire season. Seeding rate: 1 lb per 1,000 sq ft. Plant in "
            "fall before winter rains or in early spring. Full sun preferred."
        ),
        "bullets": [
            "CALIFORNIA NATIVE FIRE-RESISTANT BLEND: Seven-species bunchgrass-and-forb mix — Purple Needlegrass, Blue Wildrye, Sandberg Bluegrass, Small Fescue, Deerweed, Miniature Lupine, and Great Valley Gumweed — forms a low-fuel, fine-textured stand that reduces surface fire intensity compared to non-native annual grasses.",
            "SPECIES SELECTED FOR FIRE RESISTANCE: Purple Needlegrass (30%) and Small Fescue (15%) are naturally fine-textured and low-growing, reducing fuel load. Deerweed and Great Valley Gumweed add nitrogen-fixing ground cover that retains moisture and slows fire spread during the dry season.",
            "CALIFORNIA NATIVE AND DROUGHT TOLERANT: All seven species are native to California's foothills and valleys — established stands survive dry summers with minimal irrigation and no synthetic fertilizers once root systems are established.",
            "SEEDING RATE 1 LB PER 1,000 SQ FT: Plant in fall or early spring at surface to 1/4 inch depth in full sun. Germination strongest after first winter rains on lightly scarified or raked soil with good seed-to-soil contact.",
            "SUPPORTS NATIVE POLLINATORS AND BIRDS: Miniature Lupine and Great Valley Gumweed provide nectar for native bees throughout the growing season. Purple Needlegrass is a documented host for native butterflies and provides cover for ground-nesting birds.",
        ],
        "search_terms": "california native grass seed, fire resistant seed mix, ignition resistant landscaping, native grass california, wildland urban interface seed",
        "variants": [
            {"sku": "CV-CNIR-5-LB",  "wc_id": 470544, "lb": 5,  "sqft": 5000,  "price": 311.87},
            {"sku": "CV-CNIR-10-LB", "wc_id": 470545, "lb": 10, "sqft": 10000, "price": 561.37},
            {"sku": "CV-CNIR-25-LB", "wc_id": 470546, "lb": 25, "sqft": 25000, "price": 1325.44},
        ],
    },
    {
        "parent_sku": "PB-SOLS",
        "name": "Southern Livestock Pasture Seed Mix",
        "wc_id": 470547,
        "gtin": "840184629426",
        "item_group_id": "NS_0104",
        "custom_label_0": "pasture",
        "slug": "southern-livestock-pasture-seed-mix",
        "category_path": "pasture-seed",
        "image": "https://naturesseed.com/wp-content/uploads/2026/05/SouthernPasture.png",
        "description": (
            "The Southern Livestock Pasture Seed Mix is a nine-species forage blend engineered for "
            "full-season grazing in the Southern United States, covering the Gulf Coast, mid-South, "
            "and Transition Zone. The mix pairs cool-season forages — Tall Fescue, Perennial Ryegrass, "
            "and Orchardgrass — with Sahara II Bermudagrass for summer production. Alfalfa and Ladino "
            "White Clover contribute high-protein legume forage and biological nitrogen fixation. "
            "The defining differentiators are Cicer Milkvetch and Puna Chicory. Milkvetch is a "
            "non-bloating legume that delivers protein comparable to alfalfa without the bloat risk "
            "associated with pure-legume stands. Puna Chicory contains sesquiterpene lactones shown "
            "to reduce internal parasite egg counts in sheep and goats, providing passive parasite "
            "management between anthelmintic treatments. Birdsfoot Trefoil adds a third non-bloating "
            "legume for drought-bridge nutrition. Seeding rate: 25-30 lbs per acre for new stand; "
            "35-40 lbs per acre for overseeding."
        ),
        "bullets": [
            "NINE-SPECIES SOUTHERN LIVESTOCK MIX: Tall Fescue (22%), Bermudagrass (18%), Alfalfa (15%), Ryegrass (12%), Ladino Clover (10%), Orchardgrass (9%), Cicer Milkvetch (7%), Puna Chicory (4%), and Birdsfoot Trefoil (3%) — engineered for cattle, horses, sheep, and goats in Southern livestock operations.",
            "BLOAT-SAFE LEGUME SELECTION: Cicer Milkvetch is a non-bloating legume that delivers protein comparable to alfalfa without the bloat risk associated with pure-legume stands — a meaningful safety advantage for cattle and small ruminants in high-legume pasture systems.",
            "PARASITE REDUCTION WITH CHICORY: Puna Chicory contains sesquiterpene lactones that reduce internal parasite burdens in sheep and goats — a practical, non-chemical tool for small ruminant operations managing barber pole worm pressure between anthelmintic treatments.",
            "SEASON-LONG COVERAGE: Cool-season grasses (Tall Fescue, Ryegrass, Orchardgrass) provide spring and fall production. Bermudagrass extends summer grazing. Legumes fix nitrogen and maintain forage quality through the growing season without synthetic fertilizer.",
            "SEEDING RATE 25-30 LBS PER ACRE: Establish by drilling or broadcasting on a prepared seedbed. Delay grazing until plants reach 6-8 inches. Suitable for Gulf Coast, Transition Zone, and mid-South climates across USDA Zones 6-9.",
        ],
        "search_terms": "southern pasture seed mix, livestock forage seed, bloat safe clover pasture, chicory parasite reduction, nine species pasture blend",
        "variants": [
            {"sku": "PB-SOLS-10-LB", "wc_id": 470548, "lb": 10, "sqft": 20000,  "price": 56.99},
            {"sku": "PB-SOLS-20-LB", "wc_id": 470549, "lb": 20, "sqft": 40000,  "price": 102.58},
            {"sku": "PB-SOLS-50-LB", "wc_id": 470550, "lb": 50, "sqft": 100000, "price": 242.21},
        ],
    },
    {
        "parent_sku": "PB-PLPR",
        "name": "Plains Prairie Native Seed Mix",
        "wc_id": 470555,
        "gtin": "840184629389",
        "item_group_id": "NS_0105",
        "custom_label_0": "pasture",
        "slug": "plains-prairie-native-seed-mix",
        "category_path": "pasture-seed",
        "image": "https://naturesseed.com/wp-content/uploads/2026/05/plainsprairie.webp",
        "description": (
            "The Plains Prairie Native Seed Mix is a twelve-species native grass and forb blend "
            "formulated to restore mixed-grass prairie ecology across the Great Plains. Big Bluestem "
            "anchors the mix as the iconic tallgrass prairie dominant — its root system can reach "
            "10 feet, anchoring topsoil and sequestering carbon across decades. Indiangrass "
            "complements it with seed heads that provide winter forage for birds and nesting "
            "structure. Canada Wildrye and Virginia Wildrye are early-establishing cool-season "
            "grasses that serve as nurse crops, germinating quickly to protect newly seeded soil "
            "while slower warm-season species develop. Buffalograss and Blue Grama fill the "
            "understory, reducing bare soil between taller bunchgrasses. Purple Prairie Clover and "
            "Yellow Sweet Clover fix nitrogen and support native pollinators. Seeding rate: "
            "10-15 lbs pure live seed per acre. Dormant seeding in fall or late spring after soil "
            "temperatures reach 60°F. Drill at 1/4 to 1/2 inch depth."
        ),
        "bullets": [
            "TWELVE-SPECIES PLAINS PRAIRIE NATIVE: Big Bluestem, Indiangrass, Western Wheatgrass, Sideoats Grama, Switchgrass, Canada Wildrye, Virginia Wildrye, Buffalograss, Blue Grama, Prairie Dropseed, Purple Prairie Clover, and Yellow Sweet Clover — rebuilding the mixed-grass prairie of the Great Plains.",
            "ECOLOGICAL ROLE BY SPECIES: Big Bluestem and Indiangrass are warm-season tallgrasses providing late-season structure and bird nesting habitat. Canada and Virginia Wildrye are nurse grasses that germinate quickly, stabilize soil, and allow slower natives to establish without weed competition in year one.",
            "NITROGEN FIXATION AND SOIL BUILDING: Purple Prairie Clover and Yellow Sweet Clover are native legumes that fix atmospheric nitrogen, improve soil organic matter, and provide early-season pollinator forage — reducing the need for supplemental fertilization during the multi-year establishment window.",
            "SEEDING RATE 10-15 LBS PLS PER ACRE: Plant in fall (dormant seeding) or late spring after soil reaches 60°F. Drill at 1/4 to 1/2 inch. Expect sparse first-year growth — root development precedes visible top growth. Do not mow below 8 inches in year one.",
            "GREAT PLAINS PROVENANCE, ZONES 4-7: Species sourced for performance across Kansas, Nebraska, Oklahoma, South Dakota, Colorado, Wyoming, and adjacent states. Covers approximately 29,000 sq ft per 10 lbs at 15 lbs PLS/acre.",
        ],
        "search_terms": "plains prairie native seed mix, native grass restoration, big bluestem seed, mixed grass prairie restoration, great plains native seed",
        "variants": [
            {"sku": "PB-PLPR-10-LB", "wc_id": 470556, "lb": 10, "sqft": 29000,  "price": 157.99},
            {"sku": "PB-PLPR-20-LB", "wc_id": 470557, "lb": 20, "sqft": 58000,  "price": 284.38},
            {"sku": "PB-PLPR-50-LB", "wc_id": 470558, "lb": 50, "sqft": 145000, "price": 671.46},
        ],
    },
]

# ── GMC Builder ───────────────────────────────────────────────────────────────
def build_gmc_rows():
    """
    Build 9 GMC sheet rows (one per variant across all products).
    Returns list of dicts keyed by GMC_COLS.
    """
    rows = []
    for product in PRODUCTS:
        for i, variant in enumerate(product["variants"]):
            lb = variant["lb"]
            sqft = variant["sqft"]
            sku = variant["sku"]
            wc_id = variant["wc_id"]
            price = variant["price"]
            link = (
                f"https://naturesseed.com/products/{product['category_path']}"
                f"/{product['slug']}/?attribute_pa_size={_size_slug(lb)}"
            )
            row = {col: "" for col in GMC_COLS}
            row.update({
                "id": f"gla_{wc_id}",
                "title": f"{product['name']} - {lb} Lb - {_sqft_fmt(sqft)} Sq Ft",
                "description": product["description"],
                "availability": "in stock",
                "condition": "new",
                "price": f"{price:.2f} USD",
                "link": link,
                "image_link": product["image"],
                "brand": "Nature's Seed",
                "google_product_category": "Home & Garden > Plants > Seeds",
                "fb_product_category": "patio & garden > plants, seeds & bulbs > seeds & bulbs",
                "quantity_to_sell_on_facebook": "75",
                "item_group_id": product["item_group_id"],
                "shipping": "US:Ground:9.99 USD",
                "shipping_weight": f"{lb} lb",
                "gtin": product["gtin"],
                "product_tags[0]": product["custom_label_0"],
                "product_tags[1]": ">200",
                "mpn": sku,
                "custom_label_0": product["custom_label_0"],
                "custom_label_1": ">200",
            })
            rows.append(row)
    return rows


def get_sheets_token():
    """Exchange GOOGLE_SHEETS_REFRESH_TOKEN for a short-lived access token."""
    data = urllib.parse.urlencode({
        "client_id": ENV["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": ENV["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": ENV["GOOGLE_SHEETS_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["access_token"]


def push_gmc(rows):
    """
    Append rows to the GMC supplemental Google Sheet.
    rows: list of dicts keyed by GMC_COLS.
    Returns number of rows appended.
    """
    token = get_sheets_token()
    values = [[row.get(col, "") for col in GMC_COLS] for row in rows]
    body = json.dumps({"values": values}).encode()
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
        f"/values/{SHEET_RANGE}!A1:AG1:append"
        f"?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
    )
    req = urllib.request.Request(
        url, data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    updated = result.get("updates", {}).get("updatedRows", 0)
    print(f"  GMC: appended {updated} rows to sheet")
    return updated


# ── Walmart Builder ───────────────────────────────────────────────────────────
def _walmart_variant_group_id(parent_sku):
    """Strip hyphens from parent SKU for Walmart variantGroupId."""
    return parent_sku.replace("-", "")


def build_walmart_items():
    """
    Build 9 MP_ITEM feed dicts (one per variant).
    Returns list of {"Orderable": {...}, "Visible": {"Grass Seeds": {...}}} dicts.
    """
    items = []
    for product in PRODUCTS:
        group_id = _walmart_variant_group_id(product["parent_sku"])
        for i, variant in enumerate(product["variants"]):
            lb = variant["lb"]
            sqft = variant["sqft"]
            sku_kit = f"{variant['sku']}-KIT"
            orderable = {
                "sku": sku_kit,
                "productIdentifiers": {
                    "productIdType": "GTIN",
                    "productId": product["gtin"],
                },
                "price": variant["price"],
                "variantGroupId": group_id,
                "variantGroupInfo": {
                    "isPrimary": i == 0,
                    "groupingAttributes": [
                        {"name": "assembled_product_weight", "value": str(lb)}
                    ],
                },
            }
            visible_section = {
                "productName": f"{product['name']} - {lb} lb - Covers {_sqft_fmt(sqft)} Sq Ft",
                "brand": "Nature's Seed",
                "shortDescription": product["description"][:4000],
                "keyFeatures": product["bullets"],
                "isProp65WarningRequired": "No",
                "condition": "New",
                "light_needs": "Full Sun",
                "plantCategory": ["Grasses"],
            }
            items.append({"Orderable": orderable, "Visible": {"Grass Seeds": visible_section}})
    return items


def push_walmart(items):
    """
    Submit items as MP_ITEM feed.
    Returns feed ID string.
    """
    feed_id = submit_maintenance_feed(items, feed_type="MP_ITEM")
    print(f"  Walmart: feed submitted — {feed_id}")
    return feed_id


# ── Amazon CSV ────────────────────────────────────────────────────────────────
AMAZON_CSV_COLS = [
    "wc_id", "parent_sku", "product_name", "product_type", "categories", "tags",
    "description_plain", "short_description_plain",
    "bullet_1", "bullet_2", "bullet_3", "bullet_4", "bullet_5",
    "search_terms", "price", "regular_price", "weight", "dimensions",
    "image_1", "image_2", "image_3", "image_4", "image_5",
    "size_options", "variation_skus", "variation_prices",
    "sun_requirements", "planting_depth", "delivery_time", "wc_url",
]


def build_amazon_rows():
    """
    Build 3 parent rows for amazon_missing_products.csv (one per product).
    Returns list of dicts keyed by AMAZON_CSV_COLS.
    """
    rows = []
    for product in PRODUCTS:
        variants = product["variants"]
        size_options = " | ".join(
            f"{v['lb']} lb - Covers {_sqft_fmt(v['sqft'])} Sq Ft" for v in variants
        )
        variation_skus = " | ".join(v["sku"] for v in variants)
        variation_prices = " | ".join(f"${v['price']:.2f}" for v in variants)
        min_price = min(v["price"] for v in variants)
        row = {col: "" for col in AMAZON_CSV_COLS}
        row.update({
            "wc_id": product["wc_id"],
            "parent_sku": product["parent_sku"],
            "product_name": product["name"],
            "product_type": "variable",
            "description_plain": product["description"],
            "bullet_1": product["bullets"][0],
            "bullet_2": product["bullets"][1],
            "bullet_3": product["bullets"][2],
            "bullet_4": product["bullets"][3],
            "bullet_5": product["bullets"][4],
            "search_terms": product["search_terms"],
            "price": f"{min_price:.2f}",
            "image_1": product["image"],
            "size_options": size_options,
            "variation_skus": variation_skus,
            "variation_prices": variation_prices,
            "sun_requirements": "Full Sun",
            "delivery_time": "7",
            "wc_url": (
                f"https://naturesseed.com/products/{product['category_path']}/{product['slug']}/"
            ),
        })
        rows.append(row)
    return rows


def push_amazon(rows):
    """
    Append rows to amazon_missing_products.csv.
    Creates file with header if it doesn't exist; otherwise appends without re-writing header.
    """
    write_header = not AMAZON_CSV.exists()
    with open(AMAZON_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=AMAZON_CSV_COLS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
    print(f"  Amazon: appended {len(rows)} rows to {AMAZON_CSV.name}")
