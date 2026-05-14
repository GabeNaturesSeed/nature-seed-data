# New Product Channel Listings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a single script that adds 3 new products (9 size variants) to Google Merchant Center (via Sheets API), Walmart Marketplace (MP_ITEM feed), and Amazon draft CSV.

**Architecture:** Single script `Amazonimprovement/add_new_listings.py` with three independent channel functions driven by argparse flags. Product data lives as hardcoded constants (no external fetch needed — all data confirmed). External API calls are isolated in push functions so unit tests can mock them cleanly.

**Tech Stack:** Python 3.9, Google Sheets API v4 (urllib), `walmart_client.py` (existing), `amazon_missing_products.csv` (existing CSV append). No new dependencies.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `Amazonimprovement/add_new_listings.py` | Create | All three channel functions + CLI |
| `Amazonimprovement/tests/test_add_new_listings.py` | Create | Unit tests for builders + push functions |

---

## Reference Data

### Product constants (used in every task)

```python
# Sheets API
SHEET_ID = "12u2Uj0gHNImAQKDA1qnDUxlw4czL4DNuHbuUFqULbuU"
SHEET_RANGE = "Sheet1"

# Column order matching existing sheet (33 columns)
GMC_COLS = [
    "id","title","description","availability","condition","price","link",
    "image_link","brand","google_product_category","fb_product_category",
    "quantity_to_sell_on_facebook","sale_price","sale_price_effective_date",
    "item_group_id","gender","color","size","age_group","material","pattern",
    "shipping","shipping_weight","gtin","video[0].url","video[0].tag[0]",
    "product_tags[0]","product_tags[1]","style[0]","mpn",
    "custom_label_0","custom_label_1","custom_label_2",
]

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
            "Yellow Sweet Clover fix nitrogen and support native pollinators including native bees "
            "and monarch butterflies. Seeding rate: 10-15 lbs pure live seed per acre. Dormant "
            "seeding in fall or late spring after soil temperatures reach 60°F. Drill at 1/4 to "
            "1/2 inch depth. Expect slow first-year establishment — full expression by year two."
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
```

---

### Task 1: Scaffold script + product data constants

**Files:**
- Create: `Amazonimprovement/add_new_listings.py`
- Create: `Amazonimprovement/tests/test_add_new_listings.py`

- [ ] **Step 1: Create the script file with product constants**

Create `Amazonimprovement/add_new_listings.py`:

```python
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
```

- [ ] **Step 2: Create the test file scaffold**

Create `Amazonimprovement/tests/test_add_new_listings.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import patch, MagicMock
import add_new_listings as m
```

- [ ] **Step 3: Commit scaffold**

```bash
cd "$(git rev-parse --show-toplevel)"
git add Amazonimprovement/add_new_listings.py Amazonimprovement/tests/test_add_new_listings.py
git commit -m "feat: scaffold add_new_listings script with product constants"
```

---

### Task 2: GMC row builder

**Files:**
- Modify: `Amazonimprovement/add_new_listings.py` — add `build_gmc_rows()`
- Modify: `Amazonimprovement/tests/test_add_new_listings.py` — add GMC row tests

- [ ] **Step 1: Write failing tests for GMC row builder**

Add to `Amazonimprovement/tests/test_add_new_listings.py`:

```python
def test_build_gmc_rows_count():
    rows = m.build_gmc_rows()
    assert len(rows) == 9  # 3 products × 3 variants

def test_build_gmc_rows_structure():
    rows = m.build_gmc_rows()
    first = rows[0]
    assert set(first.keys()) == set(m.GMC_COLS)

def test_build_gmc_row_cnir_5lb():
    rows = m.build_gmc_rows()
    cnir_5 = next(r for r in rows if r["mpn"] == "CV-CNIR-5-LB")
    assert cnir_5["id"] == "gla_470544"
    assert cnir_5["title"] == "California Native Ignition Resistant Seed Mix - 5 Lb - 5,000 Sq Ft"
    assert cnir_5["price"] == "311.87 USD"
    assert cnir_5["gtin"] == "840184629488"
    assert cnir_5["item_group_id"] == "NS_0103"
    assert cnir_5["custom_label_0"] == "specialty"
    assert cnir_5["custom_label_1"] == ">200"
    assert cnir_5["availability"] == "in stock"
    assert cnir_5["condition"] == "new"
    assert cnir_5["brand"] == "Nature's Seed"
    assert cnir_5["shipping"] == "US:Ground:9.99 USD"
    assert cnir_5["shipping_weight"] == "5 lb"
    assert "attribute_pa_size=5-lb" in cnir_5["link"]
    assert "/products/specialty-seed/california-native-ignition-resistant-seed-mix/" in cnir_5["link"]

def test_build_gmc_row_sols_50lb():
    rows = m.build_gmc_rows()
    sols_50 = next(r for r in rows if r["mpn"] == "PB-SOLS-50-LB")
    assert sols_50["id"] == "gla_470550"
    assert sols_50["title"] == "Southern Livestock Pasture Seed Mix - 50 Lb - 100,000 Sq Ft"
    assert sols_50["price"] == "242.21 USD"
    assert sols_50["shipping_weight"] == "50 lb"
    assert sols_50["item_group_id"] == "NS_0104"
    assert sols_50["custom_label_0"] == "pasture"

def test_build_gmc_row_plpr_10lb():
    rows = m.build_gmc_rows()
    plpr_10 = next(r for r in rows if r["mpn"] == "PB-PLPR-10-LB")
    assert plpr_10["id"] == "gla_470556"
    assert plpr_10["title"] == "Plains Prairie Native Seed Mix - 10 Lb - 29,000 Sq Ft"
    assert plpr_10["price"] == "157.99 USD"
    assert plpr_10["item_group_id"] == "NS_0105"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 -m pytest tests/test_add_new_listings.py -k "gmc" -v 2>&1 | head -30
```

Expected: `FAILED` — `AttributeError: module 'add_new_listings' has no attribute 'build_gmc_rows'`

- [ ] **Step 3: Implement `build_gmc_rows()`**

Add to `Amazonimprovement/add_new_listings.py` after the PRODUCTS constant:

```python
def _size_slug(lb):
    """Convert lb integer to WC attribute slug: 5 -> '5-lb'"""
    return f"{lb}-lb"

def _sqft_fmt(sqft):
    """Format sq ft with commas: 29000 -> '29,000'"""
    return f"{sqft:,}"

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 -m pytest tests/test_add_new_listings.py -k "gmc" -v
```

Expected: 5 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add Amazonimprovement/add_new_listings.py Amazonimprovement/tests/test_add_new_listings.py
git commit -m "feat: add build_gmc_rows() with 9 variant rows"
```

---

### Task 3: Sheets API push

**Files:**
- Modify: `Amazonimprovement/add_new_listings.py` — add `get_sheets_token()` and `push_gmc()`
- Modify: `Amazonimprovement/tests/test_add_new_listings.py` — add Sheets push tests

- [ ] **Step 1: Write failing tests for Sheets push**

Add to `Amazonimprovement/tests/test_add_new_listings.py`:

```python
def test_get_sheets_token_calls_oauth(monkeypatch):
    captured = {}
    def fake_urlopen(req, timeout=30):
        captured["url"] = req.full_url
        body = req.data.decode()
        captured["body"] = body
        resp = MagicMock()
        resp.read.return_value = b'{"access_token": "test_token_abc"}'
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    token = m.get_sheets_token()
    assert token == "test_token_abc"
    assert "oauth2.googleapis.com/token" in captured["url"]
    assert "refresh_token" in captured["body"]

def test_push_gmc_calls_sheets_append(monkeypatch):
    call_log = []
    def fake_urlopen(req, timeout=30):
        call_log.append({"url": req.full_url, "method": req.get_method()})
        resp = MagicMock()
        resp.read.return_value = b'{"updates": {"updatedRows": 9}}'
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("add_new_listings.get_sheets_token", lambda: "fake_token")
    rows = m.build_gmc_rows()
    result = m.push_gmc(rows)
    assert result == 9
    assert any(m.SHEET_ID in c["url"] for c in call_log)
    assert any("append" in c["url"] for c in call_log)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 -m pytest tests/test_add_new_listings.py -k "sheets or push_gmc" -v 2>&1 | head -20
```

Expected: `FAILED` — `AttributeError: module has no attribute 'get_sheets_token'`

- [ ] **Step 3: Implement `get_sheets_token()` and `push_gmc()`**

Add to `Amazonimprovement/add_new_listings.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 -m pytest tests/test_add_new_listings.py -k "sheets or push_gmc or get_sheets" -v
```

Expected: all related tests `PASSED`

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add Amazonimprovement/add_new_listings.py Amazonimprovement/tests/test_add_new_listings.py
git commit -m "feat: add get_sheets_token() and push_gmc() for Sheets API append"
```

---

### Task 4: Walmart item builder + feed push

**Files:**
- Modify: `Amazonimprovement/add_new_listings.py` — add `build_walmart_items()` and `push_walmart()`
- Modify: `Amazonimprovement/tests/test_add_new_listings.py` — add Walmart tests

- [ ] **Step 1: Write failing tests for Walmart builder**

Add to `Amazonimprovement/tests/test_add_new_listings.py`:

```python
def test_build_walmart_items_count():
    items = m.build_walmart_items()
    assert len(items) == 9

def test_build_walmart_item_cnir_5lb():
    items = m.build_walmart_items()
    cnir_5 = next(i for i in items if i["Orderable"]["sku"] == "CV-CNIR-5-LB-KIT")
    assert cnir_5["Orderable"]["productIdentifiers"]["productIdType"] == "GTIN"
    assert cnir_5["Orderable"]["productIdentifiers"]["productId"] == "840184629488"
    assert cnir_5["Orderable"]["price"] == 311.87
    assert cnir_5["Orderable"]["variantGroupId"] == "CVCNIR"
    assert cnir_5["Orderable"]["variantGroupInfo"]["groupingAttributes"][0]["value"] == "5"
    visible = cnir_5["Visible"]["Grass Seeds"]
    assert "California Native Ignition Resistant" in visible["productName"]
    assert "5 lb" in visible["productName"]
    assert visible["brand"] == "Nature's Seed"
    assert len(visible["keyFeatures"]) == 5
    assert visible["condition"] == "New"

def test_build_walmart_items_primary_variant():
    items = m.build_walmart_items()
    # First variant of each product is primary
    cnir_primary = next(i for i in items if i["Orderable"]["sku"] == "CV-CNIR-5-LB-KIT")
    cnir_secondary = next(i for i in items if i["Orderable"]["sku"] == "CV-CNIR-10-LB-KIT")
    assert cnir_primary["Orderable"]["variantGroupInfo"]["isPrimary"] is True
    assert cnir_secondary["Orderable"]["variantGroupInfo"]["isPrimary"] is False

def test_push_walmart_calls_submit_feed(monkeypatch):
    call_log = []
    def fake_submit(mp_items, feed_type="MP_MAINTENANCE"):
        call_log.append({"items": mp_items, "feed_type": feed_type})
        return "feed_abc123"
    monkeypatch.setattr("add_new_listings.submit_maintenance_feed", fake_submit)
    items = m.build_walmart_items()
    feed_id = m.push_walmart(items)
    assert feed_id == "feed_abc123"
    assert call_log[0]["feed_type"] == "MP_ITEM"
    assert len(call_log[0]["items"]) == 9
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 -m pytest tests/test_add_new_listings.py -k "walmart" -v 2>&1 | head -20
```

Expected: `FAILED` — `AttributeError: module has no attribute 'build_walmart_items'`

- [ ] **Step 3: Implement `build_walmart_items()` and `push_walmart()`**

Add to `Amazonimprovement/add_new_listings.py`:

```python
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
    from walmart_client import submit_maintenance_feed
    feed_id = submit_maintenance_feed(items, feed_type="MP_ITEM")
    print(f"  Walmart: feed submitted — {feed_id}")
    return feed_id
```

Note: `submit_maintenance_feed` is imported inside the function so the test can monkeypatch `add_new_listings.submit_maintenance_feed` at module level. Add this import at the top of the test patch target by also adding a module-level alias after the `sys.path.insert` in `add_new_listings.py`:

```python
# Lazy import — resolved at call time; allows monkeypatching in tests
try:
    from walmart_client import submit_maintenance_feed
except ImportError:
    submit_maintenance_feed = None
```

Move the `from walmart_client import submit_maintenance_feed` line to module level (outside the function), replacing the in-function import.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 -m pytest tests/test_add_new_listings.py -k "walmart" -v
```

Expected: 4 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add Amazonimprovement/add_new_listings.py Amazonimprovement/tests/test_add_new_listings.py
git commit -m "feat: add build_walmart_items() and push_walmart() for MP_ITEM feed"
```

---

### Task 5: Amazon CSV row builder + append

**Files:**
- Modify: `Amazonimprovement/add_new_listings.py` — add `build_amazon_rows()` and `push_amazon()`
- Modify: `Amazonimprovement/tests/test_add_new_listings.py` — add Amazon tests

- [ ] **Step 1: Write failing tests for Amazon builder**

Add to `Amazonimprovement/tests/test_add_new_listings.py`:

```python
import io
import csv as csv_module

def test_build_amazon_rows_count():
    rows = m.build_amazon_rows()
    assert len(rows) == 3  # one parent row per product

def test_build_amazon_row_cnir():
    rows = m.build_amazon_rows()
    cnir = next(r for r in rows if r["parent_sku"] == "CV-CNIR")
    assert cnir["wc_id"] == 470543
    assert cnir["product_name"] == "California Native Ignition Resistant Seed Mix"
    assert cnir["bullet_1"] != ""
    assert cnir["bullet_5"] != ""
    assert len(cnir["description_plain"]) > 100
    assert "CV-CNIR-5-LB" in cnir["variation_skus"]
    assert "CV-CNIR-10-LB" in cnir["variation_skus"]
    assert "CV-CNIR-25-LB" in cnir["variation_skus"]
    assert "311.87" in cnir["variation_prices"]
    assert "5 lb" in cnir["size_options"]
    assert cnir["image_1"] != ""

def test_build_amazon_row_sols():
    rows = m.build_amazon_rows()
    sols = next(r for r in rows if r["parent_sku"] == "PB-SOLS")
    assert "PB-SOLS-10-LB" in sols["variation_skus"]
    assert "56.99" in sols["variation_prices"]
    assert "10 lb" in sols["size_options"]

def test_push_amazon_appends_to_csv(tmp_path, monkeypatch):
    monkeypatch.setattr("add_new_listings.AMAZON_CSV", tmp_path / "amazon_missing_products.csv")
    # Pre-populate with header + one existing row
    existing_cols = list(m.AMAZON_CSV_COLS)
    with open(tmp_path / "amazon_missing_products.csv", "w", newline="") as f:
        writer = csv_module.DictWriter(f, fieldnames=existing_cols)
        writer.writeheader()
        writer.writerow({c: "existing" for c in existing_cols})
    rows = m.build_amazon_rows()
    m.push_amazon(rows)
    with open(tmp_path / "amazon_missing_products.csv") as f:
        all_rows = list(csv_module.DictReader(f))
    assert len(all_rows) == 4  # 1 existing + 3 new
    skus = [r["parent_sku"] for r in all_rows]
    assert "CV-CNIR" in skus
    assert "PB-SOLS" in skus
    assert "PB-PLPR" in skus
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 -m pytest tests/test_add_new_listings.py -k "amazon" -v 2>&1 | head -20
```

Expected: `FAILED` — `AttributeError: module has no attribute 'build_amazon_rows'`

- [ ] **Step 3: Implement `build_amazon_rows()` and `push_amazon()`**

Add to `Amazonimprovement/add_new_listings.py`:

```python
# Amazon CSV column order (matches existing amazon_missing_products.csv header)
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 -m pytest tests/test_add_new_listings.py -k "amazon" -v
```

Expected: 4 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add Amazonimprovement/add_new_listings.py Amazonimprovement/tests/test_add_new_listings.py
git commit -m "feat: add build_amazon_rows() and push_amazon() for CSV append"
```

---

### Task 6: CLI wiring + full test run

**Files:**
- Modify: `Amazonimprovement/add_new_listings.py` — add `main()` with argparse

- [ ] **Step 1: Write failing test for CLI**

Add to `Amazonimprovement/tests/test_add_new_listings.py`:

```python
def test_main_runs_all_channels_by_default(monkeypatch):
    called = []
    monkeypatch.setattr("add_new_listings.push_gmc", lambda rows: called.append("gmc") or 9)
    monkeypatch.setattr("add_new_listings.push_walmart", lambda items: called.append("walmart") or "feed_id")
    monkeypatch.setattr("add_new_listings.push_amazon", lambda rows: called.append("amazon"))
    m.main([])
    assert "gmc" in called
    assert "walmart" in called
    assert "amazon" in called

def test_main_runs_only_gmc_with_flag(monkeypatch):
    called = []
    monkeypatch.setattr("add_new_listings.push_gmc", lambda rows: called.append("gmc") or 9)
    monkeypatch.setattr("add_new_listings.push_walmart", lambda items: called.append("walmart") or "feed_id")
    monkeypatch.setattr("add_new_listings.push_amazon", lambda rows: called.append("amazon"))
    m.main(["--gmc"])
    assert called == ["gmc"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 -m pytest tests/test_add_new_listings.py -k "main" -v 2>&1 | head -20
```

Expected: `FAILED` — `AttributeError: module has no attribute 'main'`

- [ ] **Step 3: Implement `main()`**

Add to `Amazonimprovement/add_new_listings.py`:

```python
def main(argv=None):
    parser = argparse.ArgumentParser(description="Push new product listings to GMC, Walmart, Amazon")
    parser.add_argument("--gmc",     action="store_true", help="Push to GMC Sheet only")
    parser.add_argument("--walmart", action="store_true", help="Push to Walmart only")
    parser.add_argument("--amazon",  action="store_true", help="Push to Amazon CSV only")
    args = parser.parse_args(argv)
    run_all = not (args.gmc or args.walmart or args.amazon)

    if run_all or args.gmc:
        print("\n── Google Merchant Center ────────────────────────────────")
        rows = build_gmc_rows()
        push_gmc(rows)

    if run_all or args.walmart:
        print("\n── Walmart ───────────────────────────────────────────────")
        items = build_walmart_items()
        push_walmart(items)

    if run_all or args.amazon:
        print("\n── Amazon ────────────────────────────────────────────────")
        rows = build_amazon_rows()
        push_amazon(rows)

    print("\nDone.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the full test suite**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 -m pytest tests/test_add_new_listings.py -v
```

Expected: all tests `PASSED`, 0 failures.

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add Amazonimprovement/add_new_listings.py Amazonimprovement/tests/test_add_new_listings.py
git commit -m "feat: add CLI main() with --gmc/--walmart/--amazon flags"
```

---

### Task 7: Live run + verification

- [ ] **Step 1: Dry-run Amazon channel (safe, file only)**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 add_new_listings.py --amazon
```

Expected output:
```
── Amazon ────────────────────────────────────────────────
  Amazon: appended 3 rows to amazon_missing_products.csv

Done.
```

Verify the 3 rows are present:
```bash
python3 -c "
import csv
with open('amazon_missing_products.csv') as f:
    rows = list(csv.DictReader(f))
new = [r for r in rows if r['parent_sku'] in ('CV-CNIR','PB-SOLS','PB-PLPR')]
for r in new: print(r['parent_sku'], r['product_name'][:50])
"
```

Expected: 3 lines — `CV-CNIR California Native Ignition...`, `PB-SOLS Southern Livestock...`, `PB-PLPR Plains Prairie...`

- [ ] **Step 2: Run GMC channel**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 add_new_listings.py --gmc
```

Expected output:
```
── Google Merchant Center ────────────────────────────────
  GMC: appended 9 rows to sheet

Done.
```

Verify in the sheet by reading the last 10 rows:
```bash
python3 -c "
import csv, io, requests
SHEET_ID = '12u2Uj0gHNImAQKDA1qnDUxlw4czL4DNuHbuUFqULbuU'
r = requests.get(f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv', timeout=30)
rows = list(csv.DictReader(io.StringIO(r.text)))
for row in rows[-9:]:
    print(row['mpn'], '|', row['title'][:55])
"
```

Expected: 9 new rows with `CV-CNIR-*`, `PB-SOLS-*`, `PB-PLPR-*` MPNs.

- [ ] **Step 3: Run Walmart channel**

```bash
cd "$(git rev-parse --show-toplevel)/Amazonimprovement"
python3 add_new_listings.py --walmart
```

Expected output:
```
── Walmart ───────────────────────────────────────────────
  Feed submitted: <feed_id> (9 items)
  Walmart: feed submitted — <feed_id>

Done.
```

Note the feed ID. Check feed status after ~2 minutes:
```bash
python3 -c "
import sys; sys.path.insert(0, '../marketplaces/walmart-optimization')
from walmart_client import get_feed_status
status = get_feed_status('<feed_id>', include_details=True)
print('Feed status:', status.get('feedStatus'))
print('Items processed:', status.get('itemsProcessed', 0))
print('Items succeeded:', status.get('itemsSucceeded', 0))
print('Items failed:', status.get('itemsFailed', 0))
" 
```

Replace `<feed_id>` with the actual ID from the output above.

Expected: `feedStatus: PROCESSED`, `itemsSucceeded: 9`, `itemsFailed: 0`

- [ ] **Step 4: Final commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add Amazonimprovement/amazon_missing_products.csv
git commit -m "data: add CV-CNIR, PB-SOLS, PB-PLPR to amazon_missing_products.csv"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** GMC (9 rows via Sheets API) ✓, Walmart (9 MP_ITEM entries) ✓, Amazon (3 parent CSV rows) ✓, auth via `GOOGLE_SHEETS_REFRESH_TOKEN` ✓, `--gmc/--walmart/--amazon` flags ✓
- [x] **Placeholders:** None. All code blocks are complete and runnable.
- [x] **Type consistency:** `build_gmc_rows()` returns `list[dict]` keyed by `GMC_COLS` — used correctly in `push_gmc()`. `build_walmart_items()` returns `list[dict]` with `Orderable`/`Visible` keys — passed directly to `submit_maintenance_feed()`. `build_amazon_rows()` returns `list[dict]` keyed by `AMAZON_CSV_COLS` — used correctly in `push_amazon()`. `AMAZON_CSV` path monkeypatched in test via module attribute — import alias must be at module level (not inside function) for this to work.
- [x] **`submit_maintenance_feed` import:** Must be at module level for the test monkeypatch `add_new_listings.submit_maintenance_feed` to work. Task 4 Step 3 specifies this explicitly.
