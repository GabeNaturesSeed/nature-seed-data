#!/usr/bin/env python3
"""
Update ACF article support fields (slots 2 & 3) on WooCommerce products.
Reads product catalog from local JSON, maps slugs to article URLs,
and PUTs meta_data updates via WC REST API v3.

Slot 1 is reserved for planting instructions — never touched.
"""

import json
import os
import sys
import time
import requests
from dotenv import load_dotenv

# ── Config ──────────────────────────────────────────────────────────────
ENV_PATH = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/.env"
PRODUCTS_JSON = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/search-console/data/wc_products.json"
RATE_LIMIT = 0.35  # seconds between API calls

load_dotenv(ENV_PATH)
WC_CK = os.getenv("WC_CK")
WC_CS = os.getenv("WC_CS")
BASE_URL = "https://naturesseed.com/wp-json/wc/v3"

# ── Article Mapping ─────────────────────────────────────────────────────
# slug → { slot2_title, slot2_link, slot3_title, slot3_link }
ARTICLE_MAP = {
    # ── Grass Seed ──
    "bermudagrass-seed-blend": {
        "slot2_title": "How to Fertilize Your Bermudagrass Lawn",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/",
        "slot3_title": "Best Lawn Seed for Sunny Yards",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/bermuda-grass-seed-best-lawn-seed-for-sunny-yards/",
    },
    "triblade-elite-fescue-lawn-mix": {
        "slot2_title": "Fescue Grass Seed for Shady Areas",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/fescue-grass-seed-for-shady-areas/",
        "slot3_title": "How to Fertilize Your Fescue Lawn",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-fescue-grass-seed-lawn/",
    },
    "fine-fescue-grass-seed-mix": {
        "slot2_title": "Fescue Grass Seed for Shady Areas",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/fescue-grass-seed-for-shady-areas/",
        "slot3_title": "Growing Tall Fescue in the Shade",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-grow-tall-fescue-grass-in-the-shade/",
    },
    "sheep-fescue-grass": {
        "slot2_title": "Sheep Fescue as an Alternative Lawn",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/sheep-fescue-as-an-alternative-lawn-grass/",
        "slot3_title": "What is a Low Maintenance Lawn?",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/what-exactly-is-a-low-maintenance-lawn/",
    },
    "perennial-ryegrass-seed-blend": {
        "slot2_title": "How to Plant & Grow Perennial Ryegrass",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/how-to-plant-and-grow-perennial-ryegrass/",
        "slot3_title": "How to Re-Seed Your Ryegrass Lawn",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/",
    },
    "water-wise-bluegrass-blend": {
        "slot2_title": "How to Fertilize Your Bluegrass Lawn",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bluegrass-seed-lawn/",
        "slot3_title": "Sun or Shade for Bluegrass?",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-much-sun-or-shade-does-a-bluegrass-seed-lawn-require/",
    },
    "kentucky-bluegrass-seed-blue-ribbon-mix": {
        "slot2_title": "How to Plant & Grow Kentucky Bluegrass",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/how-to-plant-and-grow/",
        "slot3_title": "How to Fertilize Your Bluegrass Lawn",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bluegrass-seed-lawn/",
    },
    "jimmys-blue-ribbon-premium-grass-seed-mix": {
        "slot2_title": "How to Choose the Right Grass Seed",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/how-to-choose-the-right-grass-seed/",
        "slot3_title": "How to Prepare Soil for Grass Seed",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/",
    },
    "high-traffic-hardy-lawn": {
        "slot2_title": "Best Grass Seed for Athletic Fields",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/best-grass-seed-choices-for-athletic-fields/",
        "slot3_title": "How to Grow Grass With Dogs",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-grow-grass-with-dogs/",
    },
    "twca-water-wise-sun-shade-mix": {
        "slot2_title": "Best Grass Seed for Shade & Poor Soil",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/",
        "slot3_title": "How Often to Water New Grass Seed",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-often-should-you-water-new-grass-seed/",
    },
    "twca-water-wise-shade-mix": {
        "slot2_title": "Best Grass Seed for Shade & Poor Soil",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/",
        "slot3_title": "Fescue Grass Seed for Shady Areas",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/fescue-grass-seed-for-shady-areas/",
    },
    "sundancer-buffalograss-seed": {
        "slot2_title": "An Introduction to Buffalograss",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/an-introduction-to-buffalograss/",
        "slot3_title": "Planting a Buffalograss Lawn",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/planting-a-buffalograss-lawn/",
    },
    "clover-lawn-alternative-mix": {
        "slot2_title": "Classy Clover: Best Addition to Your Lawn",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/",
        "slot3_title": "Teeny Tiny Clover Trend",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/teeny-tiny-clover-trend/",
    },
    "meadow-lawn-blend": {
        "slot2_title": "What is a Low Maintenance Lawn?",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/what-exactly-is-a-low-maintenance-lawn/",
        "slot3_title": "Advantages of Grass Seed Over Sod",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/advantages-of-grass-seed-over-laying-sod/",
    },
    "california-native-lawn-alternative-mix": {
        "slot2_title": "California Native Grass Series",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
        "slot3_title": "Introducing the California Collection",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
    },
    "california-habitat-mix": {
        "slot2_title": "California Native Grass Series",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
        "slot3_title": "Introducing the California Collection",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
    },
    "thingrass": {
        "slot2_title": "California Native Grass Series",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
        "slot3_title": "What is a Low Maintenance Lawn?",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/what-exactly-is-a-low-maintenance-lawn/",
    },
    "texas-native-lawn-mix": {
        "slot2_title": "Best Grass Seed for Texas",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/texas/",
        "slot3_title": "How to Choose the Right Grass Seed",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-choose-the-right-grass-seed/",
    },
    "overseed-and-repair-lawn-kit": {
        "slot2_title": "Common Mistakes When Establishing a Lawn",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/common-mistakes-made-when-establishing-a-lawn-from-seed/",
        "slot3_title": "How to Prepare Soil for Grass Seed",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/",
    },
    # ── Clover Seed ──
    "white-dutch-clover": {
        "slot2_title": "Classy Clover: Best Addition to Your Lawn",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/",
        "slot3_title": "Teeny Tiny Clover Trend",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/teeny-tiny-clover-trend/",
    },
    "white-clover": {
        "slot2_title": "Classy Clover: Best Addition to Your Lawn",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/",
        "slot3_title": "More Than Luck: Add Clover to Your Lawn",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/more-than-luck-why-you-should-add-clover-to-your-lawn-grass/",
    },
    "microclover": {
        "slot2_title": "Teeny Tiny Clover Trend",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/teeny-tiny-clover-trend/",
        "slot3_title": "Classy Clover: Best Addition to Your Lawn",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/",
    },
    "red-clover-seed": {
        "slot2_title": "The Importance of Legumes in Pastures",
        "slot2_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "slot3_title": "Classy Clover: Best Addition to Your Lawn",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/",
    },
    "crimsom-clover-crop-seed": {
        "slot2_title": "The Importance of Legumes in Pastures",
        "slot2_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "slot3_title": "Best Cover Crops for the Midwest",
        "slot3_link": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
    },
    "alsike-clover-seed": {
        "slot2_title": "The Importance of Legumes in Pastures",
        "slot2_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "slot3_title": "Which Pasture Plants Make the Best Hay?",
        "slot3_link": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    # ── Pasture Seed ──
    "tall-fescue": {
        "slot2_title": "Fescue Grass Seed for Shady Areas",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/fescue-grass-seed-for-shady-areas/",
        "slot3_title": "Endophyte Toxicity in Tall Fescue",
        "slot3_link": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
    },
    "perennial-ryegrass": {
        "slot2_title": "How to Plant & Grow Perennial Ryegrass",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/how-to-plant-and-grow-perennial-ryegrass/",
        "slot3_title": "How to Re-Seed Your Ryegrass Lawn",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/",
    },
    "kentucky-bluegrass": {
        "slot2_title": "How to Plant & Grow Kentucky Bluegrass",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/how-to-plant-and-grow/",
        "slot3_title": "How to Fertilize Your Bluegrass Lawn",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bluegrass-seed-lawn/",
    },
    "buffalograss": {
        "slot2_title": "An Introduction to Buffalograss",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/an-introduction-to-buffalograss/",
        "slot3_title": "Planting a Buffalograss Lawn",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/planting-a-buffalograss-lawn/",
    },
    "bermudagrass": {
        "slot2_title": "How to Fertilize Your Bermudagrass Lawn",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/",
        "slot3_title": "Bermuda Grass: Best Lawn Seed for Sunny Yards",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/bermuda-grass-seed-best-lawn-seed-for-sunny-yards/",
    },
    "alfalfa": {
        "slot2_title": "Converting Old Alfalfa to Productive Pasture",
        "slot2_link": "https://naturesseed.com/resources/agriculture/converting-your-old-alfalfa-field-into-a-productive-pasture/",
        "slot3_title": "Which Pasture Plants Make the Best Hay?",
        "slot3_link": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "orchardgrass": {
        "slot2_title": "Which Pasture Plants Make the Best Hay?",
        "slot2_link": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
        "slot3_title": "Pasture Establishment: Seeding Methods",
        "slot3_link": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
    },
    "timothy": {
        "slot2_title": "Which Pasture Plants Make the Best Hay?",
        "slot2_link": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
        "slot3_title": "Pasture Establishment: Seeding Methods",
        "slot3_link": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
    },
    "switchgrass-seed": {
        "slot2_title": "Switchgrass: A Grass of Many Uses",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/switchgrass-a-grass-of-many-uses/",
        "slot3_title": "Attract Gobblers with Turkey Food Plots",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
    },
    "cereal-rye": {
        "slot2_title": "Best Cover Crops for the Midwest",
        "slot2_link": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
        "slot3_title": "Which Pasture Plants Make the Best Hay?",
        "slot3_link": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "common-buckwheat": {
        "slot2_title": "Best Cover Crops for the Midwest",
        "slot2_link": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
        "slot3_title": "Attract Gobblers with Turkey Food Plots",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
    },
    "bahia-grass": {
        "slot2_title": "Best Grass Seed for Florida",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/florida/",
        "slot3_title": "How to Choose the Right Grass Seed",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-choose-the-right-grass-seed/",
    },
    "blue-grama": {
        "slot2_title": "Native Grass Series: Great Plains",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
        "slot3_title": "Erosion Control in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "goat-pasture-forage-mix-transitional": {
        "slot2_title": "The Importance of Legumes in Pastures",
        "slot2_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "slot3_title": "Pasture Establishment: Seeding Methods",
        "slot3_link": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
    },
    "horse-pastures-seed": {
        "slot2_title": "Endophyte Toxicity in Tall Fescue",
        "slot2_link": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
        "slot3_title": "Erosion Control in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "horse-pasture-mix-cold-season": {
        "slot2_title": "Endophyte Toxicity in Tall Fescue",
        "slot2_link": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
        "slot3_title": "Which Pasture Plants Make the Best Hay?",
        "slot3_link": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "horse-pasture-mix-warm-season": {
        "slot2_title": "Erosion Control in Pastures",
        "slot2_link": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
        "slot3_title": "Which Pasture Plants Make the Best Hay?",
        "slot3_link": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "horse-pasture-mix-transitional": {
        "slot2_title": "Endophyte Toxicity in Tall Fescue",
        "slot2_link": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
        "slot3_title": "Erosion Control in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "pig-pasture-forage-mix": {
        "slot2_title": "Pasture Pig Forage Mixes",
        "slot2_link": "https://naturesseed.com/resources/agriculture/pasture-pig-forage-mixes/",
        "slot3_title": "The Importance of Legumes in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
    },
    "poultry-forage-mix": {
        "slot2_title": "Pastured Poultry: What Forages for Chickens?",
        "slot2_link": "https://naturesseed.com/resources/agriculture/pastured-poultry-what-kind-of-forages-should-your-chickens-be-grazing-on/",
        "slot3_title": "The Importance of Legumes in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
    },
    "cattle-dairy-cow-pasture-mix-cold-warm-season": {
        "slot2_title": "Which Pasture Plants Make the Best Hay?",
        "slot2_link": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
        "slot3_title": "Endophyte Toxicity in Tall Fescue",
        "slot3_link": "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/",
    },
    "cattle-dairy-cow-pasture-mix-for-warm-season": {
        "slot2_title": "Which Pasture Plants Make the Best Hay?",
        "slot2_link": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
        "slot3_title": "Erosion Control in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "sheep-pasture-forage-mix-cold-season": {
        "slot2_title": "The Importance of Legumes in Pastures",
        "slot2_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "slot3_title": "Which Pasture Plants Make the Best Hay?",
        "slot3_link": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "sheep-pasture-forage-mix-warm-season": {
        "slot2_title": "The Importance of Legumes in Pastures",
        "slot2_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "slot3_title": "Erosion Control in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "sheep-pasture-forage-mix-transitional": {
        "slot2_title": "The Importance of Legumes in Pastures",
        "slot2_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "slot3_title": "Which Pasture Plants Make the Best Hay?",
        "slot3_link": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "alpaca-llama-pasture-forage-mix": {
        "slot2_title": "The Importance of Legumes in Pastures",
        "slot2_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
        "slot3_title": "Pasture Establishment: Seeding Methods",
        "slot3_link": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
    },
    "shade-mix-food-plot": {
        "slot2_title": "Attract Gobblers with Turkey Food Plots",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "slot3_title": "Best Grass Seed for Shade & Poor Soil",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/",
    },
    "big-game-food-plot-forage-mix": {
        "slot2_title": "Attract Gobblers with Turkey Food Plots",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "slot3_title": "Native Grass Series: Great Plains",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
    },
    "full-potential-food-plot": {
        "slot2_title": "Attract Gobblers with Turkey Food Plots",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "slot3_title": "The Importance of Legumes in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
    },
    "green-screen-food-plot-screen": {
        "slot2_title": "Attract Gobblers with Turkey Food Plots",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "slot3_title": "Switchgrass: A Grass of Many Uses",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/switchgrass-a-grass-of-many-uses/",
    },
    "krunch-and-munch-food-plot": {
        "slot2_title": "Attract Gobblers with Turkey Food Plots",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "slot3_title": "The Importance of Legumes in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
    },
    "upland-game-mix": {
        "slot2_title": "Attract Gobblers with Turkey Food Plots",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "slot3_title": "Switchgrass: A Grass of Many Uses",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/switchgrass-a-grass-of-many-uses/",
    },
    "pasture-clover-mix-for-duck-quail-food-plot": {
        "slot2_title": "Attract Gobblers with Turkey Food Plots",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/",
        "slot3_title": "The Importance of Legumes in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
    },
    "honey-bee-cover-crop-pasture-mix": {
        "slot2_title": "Best Cover Crops for the Midwest",
        "slot2_link": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
        "slot3_title": "Pollinator Conservation",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "weed-smother-cover-crop-kit": {
        "slot2_title": "Best Cover Crops for the Midwest",
        "slot2_link": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
        "slot3_title": "Mustard Biofumigant Cover Crops",
        "slot3_link": "https://naturesseed.com/resources/agriculture/mustard-cover-crops-for-soil-fumigation/",
    },
    "soil-builder-cover-crop-kit": {
        "slot2_title": "Best Cover Crops for the Midwest",
        "slot2_link": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
        "slot3_title": "Organic Soil Conditions for Grass Seed",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/organic-matter-achieving-the-best-possible-soil-conditions-for-grass-seed/",
    },
    "mustard-biofumigant-blend-cover-crop-seed-mix": {
        "slot2_title": "Mustard Cover Crops for Soil Fumigation",
        "slot2_link": "https://naturesseed.com/resources/agriculture/mustard-cover-crops-for-soil-fumigation/",
        "slot3_title": "Best Cover Crops for the Midwest",
        "slot3_link": "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/",
    },
    "thin-pasture-kit": {
        "slot2_title": "Pasture Establishment: Seeding Methods",
        "slot2_link": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
        "slot3_title": "Which Pasture Plants Make the Best Hay?",
        "slot3_link": "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/",
    },
    "dryland-pasture-mix": {
        "slot2_title": "Erosion Control in Pastures",
        "slot2_link": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
        "slot3_title": "Native Grass Series: Great Plains",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
    },
    "premium-irrigated-pasture-mix": {
        "slot2_title": "Pasture Establishment: Seeding Methods",
        "slot2_link": "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/",
        "slot3_title": "The Importance of Legumes in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/",
    },
    "native-cabin-grass-mix": {
        "slot2_title": "What is a Low Maintenance Lawn?",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/what-exactly-is-a-low-maintenance-lawn/",
        "slot3_title": "Native Grass Series: Great Plains",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
    },
    "shortgrass-prairie-mix": {
        "slot2_title": "Native Grass Series: Great Plains",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
        "slot3_title": "Erosion Control in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "sandhills-prairie-mix": {
        "slot2_title": "Native Grass Series: Great Plains",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
        "slot3_title": "Erosion Control in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "plains-prairie-mix": {
        "slot2_title": "Native Grass Series: Great Plains",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
        "slot3_title": "Erosion Control in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    "texas-native-prairie-mix": {
        "slot2_title": "Best Grass Seed for Texas",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/texas/",
        "slot3_title": "Native Grass Series: Great Plains",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/",
    },
    # ── Wildflower Seed ──
    "deer-resistant-wildflower-mix": {
        "slot2_title": "Keeping Deer From Eating Wildflowers",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
        "slot3_title": "Wildflower Buffer Strips for Water Quality",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "annual-wildflower-mix": {
        "slot2_title": "Wildflower Buffer Strips for Water Quality",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
        "slot3_title": "Keeping Deer From Eating Wildflowers",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
    },
    "rocky-mountain-wildflower-mix": {
        "slot2_title": "Keeping Deer From Eating Wildflowers",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
        "slot3_title": "Wildflower Buffer Strips for Water Quality",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "california-native-wildflower-mix": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "california-coastal-native-wildflower-mix": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "california-poppy": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "brittlebush": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "california-bush-sunflower": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "white-sage": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "purple-needlegrass": {
        "slot2_title": "California Native Grass Series",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
        "slot3_title": "Introducing the California Collection",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
    },
    "arroyo-lupine": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "golden-yarrow": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "western-yarrow": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "yellow-lupine": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "miniature-lupine": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "blue-eyed-grass": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "bush-monkeyflower": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "chaparral-sage-scrub-mix": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "coastal-sage-scrub-mix": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "California Native Grass Series",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/",
    },
    "central-valley-pollinator-mix-xerces-society": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "Wildflower Buffer Strips for Water Quality",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "narrowleaf-milkweed": {
        "slot2_title": "Introducing the California Collection",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/",
        "slot3_title": "Wildflower Buffer Strips for Water Quality",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "texas-bluebonnet-seeds": {
        "slot2_title": "Best Grass Seed for Texas",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/texas/",
        "slot3_title": "Wildflower Buffer Strips for Water Quality",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "texas-native-wildflower-mix": {
        "slot2_title": "Best Grass Seed for Texas",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/texas/",
        "slot3_title": "Wildflower Buffer Strips for Water Quality",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "texas-pollinator-wildflower-mix": {
        "slot2_title": "Best Grass Seed for Texas",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/texas/",
        "slot3_title": "Wildflower Buffer Strips for Water Quality",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "pink-evening-primrose-seeds": {
        "slot2_title": "Best Grass Seed for Texas",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/texas/",
        "slot3_title": "Wildflower Buffer Strips for Water Quality",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "drummond-phlox-seeds": {
        "slot2_title": "Best Grass Seed for Texas",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/texas/",
        "slot3_title": "Wildflower Buffer Strips for Water Quality",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
    },
    "pollinator-corridor-kit": {
        "slot2_title": "Wildflower Buffer Strips for Water Quality",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
        "slot3_title": "Keeping Deer From Eating Wildflowers",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
    },
    "first-year-and-perennial-foundation-wildflower-kit": {
        "slot2_title": "Wildflower Buffer Strips for Water Quality",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
        "slot3_title": "Keeping Deer From Eating Wildflowers",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
    },
    "jimmys-perennial-wildflower-mix": {
        "slot2_title": "Wildflower Buffer Strips for Water Quality",
        "slot2_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/",
        "slot3_title": "Keeping Deer From Eating Wildflowers",
        "slot3_link": "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/",
    },
    # ── Planting Aids ──
    "rice-hull": {
        "slot2_title": "Guide to Grass Seed Germination",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/a-guide-to-grass-seed-germination/",
        "slot3_title": "How to Prepare Soil for Grass Seed",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/",
    },
    "rice-hulls-improve-seed-contact-germination-hold-moisture": {
        "slot2_title": "Guide to Grass Seed Germination",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/a-guide-to-grass-seed-germination/",
        "slot3_title": "How to Prepare Soil for Grass Seed",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/",
    },
    "organic-seed-starter-fertilizer-4-6-4": {
        "slot2_title": "Understanding Fertilizer Components",
        "slot2_link": "https://naturesseed.com/resources/news-and-misc/understanding-fertilizer-components/",
        "slot3_title": "Fertilizing New Grass Seeds",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/",
    },
    "m-binder-tackifier-soil-stabilizer": {
        "slot2_title": "How to Prepare Soil for Grass Seed",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/",
        "slot3_title": "Erosion Control in Pastures",
        "slot3_link": "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/",
    },
    # ── Bundles ──
    "pet-kid-friendly-fescue-lawn-bundle": {
        "slot2_title": "Fescue Grass Seed for Shady Areas",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/fescue-grass-seed-for-shady-areas/",
        "slot3_title": "How to Grow Grass With Dogs",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-grow-grass-with-dogs/",
    },
    "premium-pet-kid-friendly-bluegrass-bundle": {
        "slot2_title": "How to Plant & Grow Kentucky Bluegrass",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/how-to-plant-and-grow/",
        "slot3_title": "How to Grow Grass With Dogs",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/how-to-grow-grass-with-dogs/",
    },
    "white-dutch-clover-soil-grass-health-boost-5lb-for-10000-sq-ft": {
        "slot2_title": "Classy Clover: Best Addition to Your Lawn",
        "slot2_link": "https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/",
        "slot3_title": "Organic Soil Conditions",
        "slot3_link": "https://naturesseed.com/resources/lawn-turf/organic-matter-achieving-the-best-possible-soil-conditions-for-grass-seed/",
    },
}


def get_meta_value(meta_list, key):
    """Extract a meta value by key from WC meta_data list."""
    for m in meta_list:
        if m.get("key") == key:
            return m.get("value", "")
    return ""


def update_product(product_id, slug, articles, session):
    """Check current fields and update slots 2 & 3 if empty."""
    # GET current product meta
    url = f"{BASE_URL}/products/{product_id}"
    resp = session.get(url)
    if resp.status_code != 200:
        return "ERROR", f"GET failed ({resp.status_code})"

    meta = resp.json().get("meta_data", [])

    # Check if slots 2 & 3 already have content
    s2_title = get_meta_value(meta, "custom_article_support_title2")
    s2_link = get_meta_value(meta, "custom_article_support_link2")
    s3_title = get_meta_value(meta, "custom_article_support_title3")
    s3_link = get_meta_value(meta, "custom_article_support_link3")

    # Build update payload — only update empty slots
    updates = []
    slot2_filled = bool(s2_title and s2_link)
    slot3_filled = bool(s3_title and s3_link)

    if slot2_filled and slot3_filled:
        return "SKIPPED", "Both slots already filled"

    if not slot2_filled:
        updates.append({"key": "custom_article_support_title2", "value": articles["slot2_title"]})
        updates.append({"key": "custom_article_support_link2", "value": articles["slot2_link"]})
        updates.append({"key": "custom_article_support_image2", "value": ""})

    if not slot3_filled:
        updates.append({"key": "custom_article_support_title3", "value": articles["slot3_title"]})
        updates.append({"key": "custom_article_support_link3", "value": articles["slot3_link"]})
        updates.append({"key": "custom_article_support_image3", "value": ""})

    # PUT update
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
    # Load product catalog
    with open(PRODUCTS_JSON, "r") as f:
        products = json.load(f)

    # Build slug → id map (published only)
    slug_to_id = {}
    for p in products:
        if p.get("status") == "publish":
            slug_to_id[p["slug"]] = p["id"]

    # Session with auth
    session = requests.Session()
    session.auth = (WC_CK, WC_CS)

    # Stats
    updated = 0
    skipped = 0
    errors = 0
    not_found = 0

    print(f"{'='*70}")
    print(f"WooCommerce Article Support Updater")
    print(f"Products in mapping: {len(ARTICLE_MAP)}")
    print(f"Published products in catalog: {len(slug_to_id)}")
    print(f"{'='*70}\n")

    for slug, articles in ARTICLE_MAP.items():
        product_id = slug_to_id.get(slug)
        if not product_id:
            print(f"  NOT FOUND  | {slug}")
            not_found += 1
            continue

        time.sleep(RATE_LIMIT)
        status, detail = update_product(product_id, slug, articles, session)

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
    print(f"  Updated:   {updated}")
    print(f"  Skipped:   {skipped}")
    print(f"  Not found: {not_found}")
    print(f"  Errors:    {errors}")
    print(f"  Total:     {updated + skipped + not_found + errors}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
