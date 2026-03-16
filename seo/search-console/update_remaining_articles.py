#!/usr/bin/env python3
"""
Update ACF article support fields (slots 2 & 3) on remaining WooCommerce products.
Queries products directly from the WC REST API by slug (no local JSON needed).

Slot 1 is reserved for planting instructions — never touched.
"""

import os
import time
import requests
from dotenv import load_dotenv

# ── Config ──────────────────────────────────────────────────────────────
ENV_PATH = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/.env"
RATE_LIMIT = 0.5  # seconds between API calls

load_dotenv(ENV_PATH)
WC_CK = os.getenv("WC_CK")
WC_CS = os.getenv("WC_CS")
BASE_URL = "https://naturesseed.com/wp-json/wc/v3"

# ── Remaining Article Mapping ────────────────────────────────────────────
REMAINING = {
    "bermudagrass": {
        "title2": "How to Fertilize Your Bermudagrass Lawn",
        "link2": "https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/",
        "title3": "Bermuda Grass: Best Lawn Seed for Sunny Yards",
        "link3": "https://naturesseed.com/resources/lawn-turf/bermuda-grass-seed-best-lawn-seed-for-sunny-yards/",
    },
    "perennial-ryegrass": {
        "title2": "How to Plant & Grow Perennial Ryegrass",
        "link2": "https://naturesseed.com/resources/lawn-turf/how-to-plant-and-grow-perennial-ryegrass/",
        "title3": "How to Re-Seed Your Ryegrass Lawn",
        "link3": "https://naturesseed.com/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/",
    },
    "kentucky-bluegrass": {
        "title2": "How to Plant & Grow Kentucky Bluegrass",
        "link2": "https://naturesseed.com/resources/lawn-turf/how-to-plant-and-grow/",
        "title3": "How to Fertilize Your Bluegrass Lawn",
        "link3": "https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bluegrass-seed-lawn/",
    },
    "buffalograss": {
        "title2": "An Introduction to Buffalograss",
        "link2": "https://naturesseed.com/resources/lawn-turf/an-introduction-to-buffalograss/",
        "title3": "Planting a Buffalograss Lawn",
        "link3": "https://naturesseed.com/resources/lawn-turf/planting-a-buffalograss-lawn/",
    },
    "tall-fescue": {
        "title2": "Fescue Grass Seed for Shady Areas",
        "link2": "https://naturesseed.com/resources/lawn-turf/fescue-grass-seed-for-shady-areas/",
        "title3": "Endophyte Toxicity in Tall Fescue",
        "link3": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
    },
    "alfalfa": {
        "title2": "Converting Old Alfalfa to Productive Pasture",
        "link2": "https://naturesseed.com/resources/agriculture/converting-your-old-alfalfa-field-into-a-productive-pasture/",
        "title3": "Which Pasture Plants Make the Best Hay?",
        "link3": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "orchardgrass": {
        "title2": "Which Pasture Plants Make the Best Hay?",
        "link2": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
        "title3": "Pasture Establishment: Seeding Methods",
        "link3": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
    },
    "timothy": {
        "title2": "Which Pasture Plants Make the Best Hay?",
        "link2": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
        "title3": "Pasture Establishment: Seeding Methods",
        "link3": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
    },
    "switchgrass-seed": {
        "title2": "Switchgrass: A Grass of Many Uses",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/switchgrass-a-grass-of-many-uses/",
        "title3": "Attract Gobblers with Turkey Food Plots",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
    },
    "cereal-rye": {
        "title2": "Best Cover Crops for the Midwest",
        "link2": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
        "title3": "Which Pasture Plants Make the Best Hay?",
        "link3": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "common-buckwheat": {
        "title2": "Best Cover Crops for the Midwest",
        "link2": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
        "title3": "Attract Gobblers with Turkey Food Plots",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
    },
    "bahia-grass": {
        "title2": "Best Grass Seed for Florida",
        "link2": "https://naturesseed.com/resources/lawn-turf/florida/",
        "title3": "How to Choose the Right Grass Seed",
        "link3": "https://naturesseed.com/resources/lawn-turf/how-to-choose-the-right-grass-seed/",
    },
    "blue-grama": {
        "title2": "Native Grass Series: Great Plains",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "horse-pastures-seed": {
        "title2": "Endophyte Toxicity in Tall Fescue",
        "link2": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "horse-pasture-mix-cold-season": {
        "title2": "Endophyte Toxicity in Tall Fescue",
        "link2": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
        "title3": "Which Pasture Plants Make the Best Hay?",
        "link3": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "horse-pasture-mix-warm-season": {
        "title2": "Erosion Control in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
        "title3": "Which Pasture Plants Make the Best Hay?",
        "link3": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "horse-pasture-mix-transitional": {
        "title2": "Endophyte Toxicity in Tall Fescue",
        "link2": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "cattle-dairy-cow-pasture-mix-cold-warm-season": {
        "title2": "Which Pasture Plants Make the Best Hay?",
        "link2": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
        "title3": "Endophyte Toxicity in Tall Fescue",
        "link3": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
    },
    "cattle-dairy-cow-pasture-mix-for-warm-season": {
        "title2": "Which Pasture Plants Make the Best Hay?",
        "link2": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "sheep-pasture-forage-mix-cold-season": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Which Pasture Plants Make the Best Hay?",
        "link3": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "sheep-pasture-forage-mix-warm-season": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "sheep-pasture-forage-mix-transitional": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Which Pasture Plants Make the Best Hay?",
        "link3": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "alpaca-llama-pasture-forage-mix": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Pasture Establishment: Seeding Methods",
        "link3": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
    },
    "goat-pasture-forage-mix-transitional": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Pasture Establishment: Seeding Methods",
        "link3": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
    },
    "pig-pasture-forage-mix": {
        "title2": "Pasture Pig Forage Mixes",
        "link2": "https://naturesseed.com/resources/agriculture/pasture-pig-forage-mixes/",
        "title3": "The Importance of Legumes in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
    },
    "poultry-forage-mix": {
        "title2": "Pastured Poultry: What Forages for Chickens?",
        "link2": "https://naturesseed.com/resources/agriculture/pastured-poultry-what-kind-of-forages-should-your-chickens-be-grazing-on/",
        "title3": "The Importance of Legumes in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
    },
    "shade-mix-food-plot": {
        "title2": "Attract Gobblers with Turkey Food Plots",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "title3": "Best Grass Seed for Shade & Poor Soil",
        "link3": "https://naturesseed.com/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/",
    },
    "full-potential-food-plot": {
        "title2": "Attract Gobblers with Turkey Food Plots",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "title3": "The Importance of Legumes in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
    },
    "green-screen-food-plot-screen": {
        "title2": "Attract Gobblers with Turkey Food Plots",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "title3": "Switchgrass: A Grass of Many Uses",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/switchgrass-a-grass-of-many-uses/",
    },
    "krunch-and-munch-food-plot": {
        "title2": "Attract Gobblers with Turkey Food Plots",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "title3": "The Importance of Legumes in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
    },
    "upland-game-mix": {
        "title2": "Attract Gobblers with Turkey Food Plots",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "title3": "Switchgrass: A Grass of Many Uses",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/switchgrass-a-grass-of-many-uses/",
    },
    "pasture-clover-mix-for-duck-quail-food-plot": {
        "title2": "Attract Gobblers with Turkey Food Plots",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "title3": "The Importance of Legumes in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
    },
    "weed-smother-cover-crop-kit": {
        "title2": "Best Cover Crops for the Midwest",
        "link2": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
        "title3": "Mustard Cover Crops for Soil Fumigation",
        "link3": "https://naturesseed.com/resources/agriculture/mustard-cover-crops-for-soil-fumigation/",
    },
    "soil-builder-cover-crop-kit": {
        "title2": "Best Cover Crops for the Midwest",
        "link2": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
        "title3": "Organic Soil Conditions for Grass Seed",
        "link3": "https://naturesseed.com/resources/lawn-turf/organic-matter-achieving-the-best-possible-soil-conditions-for-grass-seed/",
    },
    "mustard-biofumigant-blend-cover-crop-seed-mix": {
        "title2": "Mustard Cover Crops for Soil Fumigation",
        "link2": "https://naturesseed.com/resources/agriculture/mustard-cover-crops-for-soil-fumigation/",
        "title3": "Best Cover Crops for the Midwest",
        "link3": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
    },
    "thin-pasture-kit": {
        "title2": "Pasture Establishment: Seeding Methods",
        "link2": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
        "title3": "Which Pasture Plants Make the Best Hay?",
        "link3": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "dryland-pasture-mix": {
        "title2": "Erosion Control in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
        "title3": "Native Grass Series: Great Plains",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
    },
    "premium-irrigated-pasture-mix": {
        "title2": "Pasture Establishment: Seeding Methods",
        "link2": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
        "title3": "The Importance of Legumes in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
    },
    "native-cabin-grass-mix": {
        "title2": "What is a Low Maintenance Lawn?",
        "link2": "https://naturesseed.com/resources/lawn-turf/what-exactly-is-a-low-maintenance-lawn/",
        "title3": "Native Grass Series: Great Plains",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
    },
    "shortgrass-prairie-mix": {
        "title2": "Native Grass Series: Great Plains",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "sandhills-prairie-mix": {
        "title2": "Native Grass Series: Great Plains",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "plains-prairie-mix": {
        "title2": "Native Grass Series: Great Plains",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "deer-resistant-wildflower-mix": {
        "title2": "Keeping Deer From Eating Wildflowers",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
        "title3": "Wildflower Buffer Strips for Water Quality",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "annual-wildflower-mix": {
        "title2": "Wildflower Buffer Strips for Water Quality",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
        "title3": "Keeping Deer From Eating Wildflowers",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
    },
    "rocky-mountain-wildflower-mix": {
        "title2": "Keeping Deer From Eating Wildflowers",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
        "title3": "Wildflower Buffer Strips for Water Quality",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "pollinator-corridor-kit": {
        "title2": "Wildflower Buffer Strips for Water Quality",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
        "title3": "Keeping Deer From Eating Wildflowers",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
    },
    "first-year-and-perennial-foundation-wildflower-kit": {
        "title2": "Wildflower Buffer Strips for Water Quality",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
        "title3": "Keeping Deer From Eating Wildflowers",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
    },
    "jimmys-perennial-wildflower-mix": {
        "title2": "Wildflower Buffer Strips for Water Quality",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
        "title3": "Keeping Deer From Eating Wildflowers",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
    },
    "rice-hulls-improve-seed-contact-germination-hold-moisture": {
        "title2": "Guide to Grass Seed Germination",
        "link2": "https://naturesseed.com/resources/lawn-turf/a-guide-to-grass-seed-germination/",
        "title3": "How to Prepare Soil for Grass Seed",
        "link3": "https://naturesseed.com/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/",
    },
    "rice-hull": {
        "title2": "Guide to Grass Seed Germination",
        "link2": "https://naturesseed.com/resources/lawn-turf/a-guide-to-grass-seed-germination/",
        "title3": "How to Prepare Soil for Grass Seed",
        "link3": "https://naturesseed.com/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/",
    },
    "organic-seed-starter-fertilizer-4-6-4": {
        "title2": "Understanding Fertilizer Components",
        "link2": "https://naturesseed.com/resources/news-and-misc/understanding-fertilizer-components/",
        "title3": "Fertilizing New Grass Seeds",
        "link3": "https://naturesseed.com/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/",
    },
    "m-binder-tackifier-soil-stabilizer": {
        "title2": "How to Prepare Soil for Grass Seed",
        "link2": "https://naturesseed.com/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/",
        "title3": "Erosion Control in Pastures",
        "link3": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "pet-kid-friendly-fescue-lawn-bundle": {
        "title2": "Fescue Grass Seed for Shady Areas",
        "link2": "https://naturesseed.com/resources/lawn-turf/fescue-grass-seed-for-shady-areas/",
        "title3": "How to Grow Grass With Dogs",
        "link3": "https://naturesseed.com/resources/lawn-turf/how-to-grow-grass-with-dogs/",
    },
    "premium-pet-kid-friendly-bluegrass-bundle": {
        "title2": "How to Plant & Grow Kentucky Bluegrass",
        "link2": "https://naturesseed.com/resources/lawn-turf/how-to-plant-and-grow/",
        "title3": "How to Grow Grass With Dogs",
        "link3": "https://naturesseed.com/resources/lawn-turf/how-to-grow-grass-with-dogs/",
    },
    "white-dutch-clover-soil-grass-health-boost-5lb-for-10000-sq-ft": {
        "title2": "Classy Clover: Best Addition to Your Lawn",
        "link2": "https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/",
        "title3": "Organic Soil Conditions",
        "link3": "https://naturesseed.com/resources/lawn-turf/organic-matter-achieving-the-best-possible-soil-conditions-for-grass-seed/",
    },
    "red-clover-seed": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Classy Clover: Best Addition to Your Lawn",
        "link3": "https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/",
    },
    "crimsom-clover-crop-seed": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Best Cover Crops for the Midwest",
        "link3": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
    },
    "alsike-clover-seed": {
        "title2": "The Importance of Legumes in Pastures",
        "link2": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "title3": "Which Pasture Plants Make the Best Hay?",
        "link3": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "honey-bee-cover-crop-pasture-mix": {
        "title2": "Best Cover Crops for the Midwest",
        "link2": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
        "title3": "Pollinator Conservation",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "big-game-food-plot-forage-mix": {
        "title2": "Attract Gobblers with Turkey Food Plots",
        "link2": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "title3": "Native Grass Series: Great Plains",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
    },
    "texas-native-prairie-mix": {
        "title2": "Best Grass Seed for Texas",
        "link2": "https://naturesseed.com/resources/lawn-turf/texas/",
        "title3": "Native Grass Series: Great Plains",
        "link3": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
    },
}


def get_meta_value(meta_list, key):
    """Extract a meta value by key from WC meta_data list."""
    for m in meta_list:
        if m.get("key") == key:
            return m.get("value", "")
    return ""


def find_product_by_slug(slug, session):
    """Query WC API for a product by slug. Returns (product_id, meta_data) or (None, None)."""
    url = f"{BASE_URL}/products"
    resp = session.get(url, params={"slug": slug})
    if resp.status_code != 200:
        return None, None, f"API error {resp.status_code}"
    data = resp.json()
    if not data:
        return None, None, "No product found"
    product = data[0]
    return product["id"], product.get("meta_data", []), None


def update_product(product_id, articles, meta, session):
    """Check current fields and update slots 2 & 3 if empty."""
    s2_title = get_meta_value(meta, "custom_article_support_title2")
    s2_link = get_meta_value(meta, "custom_article_support_link2")
    s3_title = get_meta_value(meta, "custom_article_support_title3")
    s3_link = get_meta_value(meta, "custom_article_support_link3")

    slot2_filled = bool(s2_title and s2_link)
    slot3_filled = bool(s3_title and s3_link)

    if slot2_filled and slot3_filled:
        return "SKIPPED", "Both slots already filled"

    updates = []
    if not slot2_filled:
        updates.append({"key": "custom_article_support_title2", "value": articles["title2"]})
        updates.append({"key": "custom_article_support_link2", "value": articles["link2"]})
        updates.append({"key": "custom_article_support_image2", "value": ""})

    if not slot3_filled:
        updates.append({"key": "custom_article_support_title3", "value": articles["title3"]})
        updates.append({"key": "custom_article_support_link3", "value": articles["link3"]})
        updates.append({"key": "custom_article_support_image3", "value": ""})

    url = f"{BASE_URL}/products/{product_id}"
    put_resp = session.put(url, json={"meta_data": updates})
    if put_resp.status_code != 200:
        return "ERROR", f"PUT failed ({put_resp.status_code}): {put_resp.text[:200]}"

    filled = []
    if not slot2_filled:
        filled.append("slot2")
    if not slot3_filled:
        filled.append("slot3")
    return "UPDATED", f"Set {' + '.join(filled)}"


def main():
    session = requests.Session()
    session.auth = (WC_CK, WC_CS)

    updated = 0
    skipped = 0
    errors = 0
    not_found = 0
    found = 0

    print(f"{'='*70}")
    print(f"WooCommerce Article Support Updater — Remaining Products")
    print(f"Products in mapping: {len(REMAINING)}")
    print(f"Querying WC API directly by slug...")
    print(f"{'='*70}\n")

    for slug, articles in REMAINING.items():
        time.sleep(RATE_LIMIT)

        product_id, meta, err = find_product_by_slug(slug, session)

        if product_id is None:
            print(f"  NOT FOUND  | {slug} — {err}")
            not_found += 1
            continue

        found += 1
        time.sleep(RATE_LIMIT)

        status, detail = update_product(product_id, articles, meta, session)

        if status == "UPDATED":
            print(f"  UPDATED    | {slug} (ID {product_id}) — {detail}")
            updated += 1
        elif status == "SKIPPED":
            print(f"  SKIPPED    | {slug} (ID {product_id}) — {detail}")
            skipped += 1
        else:
            print(f"  ERROR      | {slug} (ID {product_id}) — {detail}")
            errors += 1

    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"  Found:     {found}")
    print(f"  Updated:   {updated}")
    print(f"  Skipped:   {skipped}")
    print(f"  Not found: {not_found}")
    print(f"  Errors:    {errors}")
    print(f"  Total:     {len(REMAINING)}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
