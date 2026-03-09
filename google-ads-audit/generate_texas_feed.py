#!/usr/bin/env python3
"""
Generate Google Merchant Center Feed Rows for Texas Collection Products
=======================================================================

Produces 21 rows (7 products x 3 variants) in the exact 47-column format
used by Nature's Seed's live merchant feed.

All GTINs, COGS, and prices are production values (updated March 5, 2026).
Prices use the lowest available price (sale price where applicable, else regular).

Usage:
    python3 generate_texas_feed.py
    # Output: texas_collection_feed.csv (paste into live Google Sheet)
"""

import csv
import os
from urllib.parse import quote

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'texas_collection_feed.csv')

# ============================================================
# COLUMN HEADERS (exact order from live feed)
# ============================================================
HEADERS = [
    'id', 'mpn', 'Title', 'description', 'availability', 'availability date',
    'expiration date', 'link', 'mobile link', 'image link', 'price',
    'sale price', 'sale price effective date', 'identifier exists', 'gtin',
    'brand', 'product highlight', 'product detail', 'additional image link',
    'condition', 'adult', 'color', 'size', 'size type', 'size system',
    'gender', 'material', 'pattern', 'age group', 'multipack', 'is bundle',
    'shipping_weight', 'unit pricing measure', 'unit pricing base measure',
    'energy efficiency class', 'min energy efficiency class',
    'min energy efficiency class', 'item group id', 'sell on google quantity',
    'Custom label 0', 'Custom label 1', 'Custom label 2', 'Custom label 3',
    'Custom label 4', 'Google product category', 'Product Type',
    'cost_of_goods_sold'
]

GOOGLE_PRODUCT_CAT = 'Home & Garden > Plants > Seeds > Seeds & Seed Tape'
BRAND = "Nature's Seed"
BASE_URL = 'https://naturesseed.com'

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def price_bucket(price):
    """Determine Custom Label 2 price bucket."""
    if price < 50:
        return '<50'
    elif price < 100:
        return '50-100'
    elif price < 150:
        return '100-150'
    elif price < 200:
        return '150-200'
    else:
        return '>200'

def margin_tier(price, cogs):
    """Determine Custom Label 3 margin tier from price and COGS.
    High Margin: >50% margin
    Average Margin: 25-50% margin
    Low Margin: <25% margin (including negative)
    """
    if price <= 0:
        return 'Low Margin'
    margin_pct = (price - cogs) / price * 100
    if margin_pct > 50:
        return 'High Margin'
    elif margin_pct >= 25:
        return 'Average Margin'
    else:
        return 'Low Margin'

def format_coverage(sqft):
    """Format coverage with commas: 1000 -> 1,000"""
    return f'{sqft:,}'

def encode_size_attr(weight_str, coverage_sqft):
    """Build the URL attribute_size parameter.
    Format: '0.5 lb - Covers 1,000 Sq Ft' -> URL-encoded with + for spaces
    Matches existing feed style: 5+lb+-+Covers+1%2C000+Sq+Ft
    """
    size_label = f'{weight_str} lb - Covers {format_coverage(coverage_sqft)} Sq Ft'
    # Use + for spaces (matching existing feed), %2C for commas
    encoded = size_label.replace(' ', '+').replace(',', '%2C')
    return encoded

def build_link(category_slug, product_slug, variation_id, weight_str, coverage_sqft):
    """Build the full product URL with variation parameters."""
    encoded_size = encode_size_attr(weight_str, coverage_sqft)
    return (f'{BASE_URL}/products/{category_slug}/{product_slug}/'
            f'?variation_id={variation_id}&attribute_size={encoded_size}')

def build_mpn(sku_prefix, weight_str, is_kit):
    """Build MPN from SKU prefix and weight.
    Pattern: SKU-WEIGHT-LB or SKU-WEIGHT-LB-KIT
    """
    mpn = f'{sku_prefix}-{weight_str}-LB'
    if is_kit:
        mpn += '-KIT'
    return mpn

def format_price(price):
    """Format price as 'XX.XX USD'."""
    return f'{price:.2f} USD'

def multipack_value(weight_str, base_unit_str):
    """Calculate multipack value (number of base units in the package).
    Returns empty string for single unit, or integer for multi-unit."""
    try:
        weight = float(weight_str)
        base = float(base_unit_str)
        count = int(weight / base)
        if count <= 1:
            return ''
        return str(count)
    except:
        return ''


# ============================================================
# PRODUCT DEFINITIONS
# ============================================================

PRODUCTS = [
    # -------------------------------------------------------
    # 1. Texas Bluebonnet Seeds (W-LUTE)
    # -------------------------------------------------------
    {
        'name': 'Texas Bluebonnet Seeds',
        'sku_prefix': 'W-LUTE',
        'subtitle': 'Native Texas Wildflower',
        'category_slug': 'wildflower-seed',
        'product_slug': 'texas-bluebonnet-seeds',
        'item_group_id': 'NS_0103',
        'gtin': '840184629518',
        'image_link': f'{BASE_URL}/wp-content/uploads/2026/02/TexasBluebonnet.webp',
        'additional_image_link': f'{BASE_URL}/wp-content/uploads/2025/07/WildflowerBag-2.png',
        'cl0': 'wildflower',
        'product_type': 'Wildflower Seeds > Single Species Wildflower',
        'base_unit': '0.25',
        'description': (
            "Bring the iconic Texas spring to your landscape with Texas Bluebonnet Seeds (Lupinus texensis) "
            "from Nature's Seed. The official Texas state flower, bluebonnets transform fields and roadsides "
            "into breathtaking blue-violet displays each spring.\n\n"
            "Why you'll love Texas Bluebonnets\n"
            "Authentic Texas heritage wildflower with deep blue-violet blooms tipped in white\n"
            "Easy fall planting produces stunning spring color from March through May\n"
            "Native legume fixes nitrogen and improves soil health naturally\n"
            "Drought-tolerant once established, thriving in lean, well-drained Texas soils\n"
            "Self-seeding perennial returns year after year with minimal effort\n"
            "Attracts pollinators including native bees, butterflies, and hummingbirds\n\n"
            "Perfect for meadows, roadside plantings, open fields, and native landscapes across USDA Zones 4-9. "
            "Plant in fall for best results. Scarify seeds before sowing for faster germination."
        ),
        'highlights': [
            "Iconic Texas state flower with stunning blue-violet spring blooms",
            "Native legume that fixes nitrogen and naturally improves soil health",
            "Drought-tolerant wildflower adapted to lean, well-drained Texas soils",
            "Self-seeding perennial returns reliably year after year with minimal care",
            "Fall planting produces vibrant spring color from March through May",
            "Attracts essential pollinators including bees, butterflies, and hummingbirds"
        ],
        'product_detail': ':Seed type:Single species,:Native species:Yes,:Region:Texas,:Sun requirement:Full sun',
        'variants': [
            {'var_id': 462924, 'weight': '0.25', 'price': 38.99,  'coverage': 500,   'cogs': 15.48},
            {'var_id': 462925, 'weight': '0.5',  'price': 70.19,  'coverage': 1000,  'cogs': 30.96},
            {'var_id': 462926, 'weight': '1',    'price': 131.74, 'coverage': 2000,  'cogs': 61.91},
        ]
    },

    # -------------------------------------------------------
    # 2. Texas Native Wildflower Mix (WB-TEXN)
    # -------------------------------------------------------
    {
        'name': 'Texas Native Wildflower Mix',
        'sku_prefix': 'WB-TEXN',
        'subtitle': '8-Species Native Blend',
        'category_slug': 'wildflower-seed',
        'product_slug': 'texas-native-wildflower-mix',
        'item_group_id': 'NS_0104',
        'gtin': '840184629495',
        'image_link': f'{BASE_URL}/wp-content/uploads/2026/02/Texas-Native-Wildflower-Mix.webp',
        'additional_image_link': f'{BASE_URL}/wp-content/uploads/2025/07/WildflowerBag-2.png',
        'cl0': 'wildflower',
        'product_type': 'Wildflower Seeds > Regional Wildflower Mixes > Texas Wildflower Mix',
        'base_unit': '0.5',
        'description': (
            "Create a vibrant Texas wildflower meadow with the Texas Native Wildflower Mix from Nature's Seed. "
            "This expertly blended 8-species mix features Texas Bluebonnet, Indian Paintbrush, and six additional "
            "native species selected for continuous color from March through October.\n\n"
            "Why you'll love this mix\n"
            "Authentic 8-species Texas native blend with Bluebonnet at 22% of the mix\n"
            "Season-long color from spring through fall with staggered bloom times\n"
            "Adapted to Texas soils and climate for reliable establishment\n"
            "Drought-tolerant native species require minimal irrigation once established\n"
            "Supports Texas pollinators including monarch butterflies and native bees\n"
            "Simple scatter-sow planting makes it easy to establish even on large areas\n\n"
            "Ideal for meadows, roadsides, ranch entries, and restoration projects across Texas. "
            "Plant in fall for best spring color. Thrives in full sun with well-drained soil."
        ),
        'highlights': [
            "8-species native Texas wildflower blend with Bluebonnet as the dominant species",
            "Season-long color from March through October with staggered bloom times",
            "Drought-tolerant native species adapted to Texas soils and climate",
            "Attracts and supports pollinators including monarch butterflies and bees",
            "Simple scatter-sow planting for easy establishment on any scale",
            "Ideal for meadows, ranch entries, roadsides, and restoration projects"
        ],
        'product_detail': ':Seed type:Seed mix,:Native species:Yes,:Region:Texas,:Sun requirement:Full sun',
        'variants': [
            {'var_id': 462885, 'weight': '0.5', 'price': 32.99,  'coverage': 1000,   'cogs': 12.95},
            {'var_id': 462886, 'weight': '1',   'price': 58.49,  'coverage': 2000,   'cogs': 25.89},
            {'var_id': 462887, 'weight': '5',   'price': 275.39, 'coverage': 10000,  'cogs': 129.45},
        ]
    },

    # -------------------------------------------------------
    # 3. Texas Pollinator Wildflower Mix (WB-TXPB)
    # -------------------------------------------------------
    {
        'name': 'Texas Pollinator Wildflower Mix',
        'sku_prefix': 'WB-TXPB',
        'subtitle': 'Bee & Butterfly Habitat Blend',
        'category_slug': 'wildflower-seed',
        'product_slug': 'texas-pollinator-wildflower-mix',
        'item_group_id': 'NS_0105',
        'gtin': '840184629501',
        'image_link': f'{BASE_URL}/wp-content/uploads/2026/02/Texas-Pollinator-Wildflower-Mix.webp',
        'additional_image_link': f'{BASE_URL}/wp-content/uploads/2025/07/WildflowerBag-2.png',
        'cl0': 'wildflower',
        'product_type': 'Wildflower Seeds > Regional Wildflower Mixes > Texas Wildflower Mix',
        'base_unit': '0.5',
        'description': (
            "Support Texas pollinators with the Texas Pollinator Wildflower Mix from Nature's Seed. "
            "This specially formulated blend combines native Texas wildflowers selected for maximum "
            "nectar and pollen production, providing critical food sources for bees, butterflies, and "
            "hummingbirds throughout the growing season.\n\n"
            "Why you'll love this mix\n"
            "Native Texas species selected specifically for pollinator support\n"
            "Extended bloom period provides nectar from early spring through fall\n"
            "Supports honeybees, native bees, monarch butterflies, and hummingbirds\n"
            "Drought-tolerant once established for low-maintenance pollinator habitat\n"
            "Adapted to Texas heat, alkaline soils, and low-rainfall conditions\n"
            "Scatter-sow planting method makes establishment simple\n\n"
            "Perfect for pollinator gardens, meadows, conservation areas, and property borders. "
            "Contributes to monarch butterfly corridor and native bee habitat restoration across Texas."
        ),
        'highlights': [
            "Native Texas wildflower blend formulated specifically for pollinator support",
            "Extended bloom period provides nectar from spring through fall",
            "Supports honeybees, native bees, monarch butterflies, and hummingbirds",
            "Drought-tolerant species adapted to Texas heat and alkaline soils",
            "Contributes to monarch butterfly corridor and native bee habitat restoration",
            "Easy scatter-sow planting for simple establishment at any scale"
        ],
        'product_detail': ':Seed type:Seed mix,:Native species:Yes,:Region:Texas,:Sun requirement:Full sun,:Use case:Pollinator habitat',
        'variants': [
            {'var_id': 462888, 'weight': '0.5', 'price': 33.99,  'coverage': 1000,   'cogs': 13.47},
            {'var_id': 462889, 'weight': '1',   'price': 61.19,  'coverage': 2000,   'cogs': 26.94},
            {'var_id': 462890, 'weight': '5',   'price': 286.44, 'coverage': 10000,  'cogs': 134.70},
        ]
    },

    # -------------------------------------------------------
    # 4. Texas Native Lawn Mix (TURF-TXN)
    # -------------------------------------------------------
    {
        'name': 'Texas Native Lawn Mix',
        'sku_prefix': 'TURF-TXN',
        'subtitle': 'Low-Water Native Turf Blend',
        'category_slug': 'grass-seed',
        'product_slug': 'texas-native-lawn-mix',
        'item_group_id': 'NS_0106',
        'gtin': '840184629525',
        'image_link': f'{BASE_URL}/wp-content/uploads/2026/02/Texas-Native-Lawn-Mix.webp',
        'additional_image_link': f'{BASE_URL}/wp-content/uploads/2025/07/LawnBag.png',
        'cl0': 'grass-seed',
        'product_type': 'Lawn / Turf Seeds > Home Lawn/Yard Grass Seed',
        'base_unit': '5',
        'description': (
            "Build a drought-proof Texas lawn with the Texas Native Lawn Mix from Nature's Seed. "
            "This 3-species native grass blend is dominated by Buffalograss at 70%, with Blue Grama at 20% "
            "and Curly Mesquite at 10%, specifically formulated for Central and West Texas alkaline soils.\n\n"
            "Why you'll love this lawn mix\n"
            "Uses 30-40% less water than Bermuda and other conventional turf grasses\n"
            "Native 3-species blend built for Texas alkaline soils and extreme heat\n"
            "Buffalograss-dominant for dense, low-growing turf with excellent wear tolerance\n"
            "No fertilizer needed once established for truly low-maintenance lawn care\n"
            "Deep root system survives Texas drought and heat stress naturally\n"
            "Mow just 2-3 times per season or leave as a natural shortgrass lawn\n\n"
            "Ideal for home lawns, commercial landscapes, and municipal turf in USDA Zones 5-9. "
            "Plant in late spring when soil temperatures reach 60F or above for best establishment."
        ),
        'highlights': [
            "3-species native grass blend with 70% Buffalograss for dense, durable turf",
            "Uses 30-40% less water than Bermuda and conventional turf grasses",
            "Formulated specifically for Central and West Texas alkaline soils",
            "No fertilizer required once established for truly low-maintenance care",
            "Deep root system withstands Texas drought and extreme summer heat",
            "Mow just 2-3 times per season or leave as natural shortgrass lawn"
        ],
        'product_detail': ':Grass type:Native blend,:Growth season:Warm season,:Sun requirement:Full sun,:Drought tolerant:Yes,:Native species:Yes',
        'variants': [
            {'var_id': 462891, 'weight': '5',  'price': 164.99, 'coverage': 1000,  'cogs': 65.80},
            {'var_id': 462892, 'weight': '10', 'price': 296.09, 'coverage': 2000,  'cogs': 131.60},
            {'var_id': 462893, 'weight': '25', 'price': 699.54, 'coverage': 5000,  'cogs': 329.00},
        ]
    },

    # -------------------------------------------------------
    # 5. Texas Native Prairie Mix (PB-TXPR)
    # -------------------------------------------------------
    {
        'name': 'Texas Native Prairie Mix',
        'sku_prefix': 'PB-TXPR',
        'subtitle': 'Rangeland & Conservation Blend',
        'category_slug': 'pasture-seed',
        'product_slug': 'texas-native-prairie-mix',
        'item_group_id': 'NS_0107',
        'gtin': '840184629532',
        'image_link': f'{BASE_URL}/wp-content/uploads/2026/02/Texas-Native-Prairie-Mix.webp',
        'additional_image_link': f'{BASE_URL}/wp-content/uploads/2025/05/NS-Pasture-Seed-Large-bag.jpg',
        'cl0': 'specialty',
        'product_type': 'Specialty Seeds > Regional Specialty Seed Mix > Texas Specialty Seed Mix',
        'base_unit': '10',
        'description': (
            "Restore native Texas prairie with the Texas Native Prairie Mix from Nature's Seed. "
            "This 8-species blend combines native grasses and forbs specifically selected for Texas "
            "rangeland improvement, prairie restoration, and conservation programs including CRP and EQIP.\n\n"
            "Why you'll love this prairie mix\n"
            "8 native Texas grass and forb species for diverse, resilient prairie establishment\n"
            "Formulated for Texas rangeland improvement and prairie restoration projects\n"
            "Deep-rooted native perennials provide excellent erosion control on slopes and disturbed sites\n"
            "Drought-tolerant species thrive in Texas heat with minimal supplemental irrigation\n"
            "Qualifies for USDA conservation programs including CRP and EQIP\n"
            "Supports native wildlife habitat and biodiversity restoration\n\n"
            "Ideal for rangeland restoration, conservation programs, highway rights-of-way, "
            "and large-scale native habitat projects. Plant at 10 PLS lb per acre. "
            "Best results with fall or late-winter dormant seeding."
        ),
        'highlights': [
            "8-species native Texas grass and forb blend for prairie restoration",
            "Formulated for rangeland improvement and USDA conservation programs (CRP/EQIP)",
            "Deep-rooted native perennials provide excellent erosion control",
            "Drought-tolerant species thrive in Texas heat with minimal irrigation",
            "Supports native wildlife habitat and biodiversity restoration",
            "Recommended seeding rate of 10 PLS lb per acre for full coverage"
        ],
        'product_detail': ':Seed type:Seed mix,:Native species:Yes,:Region:Texas,:Use case:Prairie restoration and conservation',
        'variants': [
            {'var_id': 462894, 'weight': '10', 'price': 214.99, 'coverage': 40000,  'cogs': 85.90},
            {'var_id': 462895, 'weight': '20', 'price': 386.99, 'coverage': 80000,  'cogs': 171.80},
            {'var_id': 462896, 'weight': '50', 'price': 912.89, 'coverage': 200000, 'cogs': 429.50},
        ]
    },

    # -------------------------------------------------------
    # 6. Mexican Primrose / Pinkladies (W-OESP)
    # -------------------------------------------------------
    {
        'name': 'Mexican Primrose (Pinkladies)',
        'sku_prefix': 'W-OESP',
        'subtitle': 'Native Texas Pink Wildflower',
        'category_slug': 'wildflower-seed',
        'product_slug': 'pink-evening-primrose-seeds',
        'item_group_id': 'NS_0108',
        'gtin': '840184626265',
        'image_link': f'{BASE_URL}/wp-content/uploads/2026/02/Mexican-Primrose-pinkladies.webp',
        'additional_image_link': f'{BASE_URL}/wp-content/uploads/2023/08/bag5_6.png',
        'cl0': 'wildflower',
        'product_type': 'Wildflower Seeds > Single Species Wildflower',
        'base_unit': '0.25',
        'description': (
            "Add iconic Texas pink roadside color to your landscape with Mexican Primrose (Oenothera speciosa) "
            "from Nature's Seed. Also known as Pinkladies, this native perennial creates spreading carpets of "
            "delicate pink blooms from April through October across Texas roadsides and meadows.\n\n"
            "Why you'll love Mexican Primrose\n"
            "Native Texas perennial that creates sweeping carpets of soft pink blooms\n"
            "Extended bloom period from April through October for months of color\n"
            "Extremely drought-tolerant once established, requiring no supplemental water\n"
            "Thrives in poor, sandy, and rocky Texas soils where other flowers struggle\n"
            "Spreads via rhizomes and self-seeding for reliable coverage expansion\n"
            "Attracts butterflies, bees, and other beneficial pollinators\n\n"
            "Perfect for meadows, xeriscapes, roadsides, and open natural areas. "
            "Surface sow seeds in fall for best spring establishment. "
            "Note: vigorous spreader best suited to open areas, not manicured garden beds."
        ),
        'highlights': [
            "Iconic Texas roadside wildflower with delicate pink blooms April through October",
            "Native perennial that spreads via rhizomes for expanding ground coverage",
            "Extremely drought-tolerant once established with zero supplemental water needed",
            "Thrives in poor, sandy, and rocky soils where other wildflowers struggle",
            "Simple surface-sow planting with no soil preparation required",
            "Attracts butterflies, bees, and beneficial pollinators to your landscape"
        ],
        'product_detail': ':Seed type:Single species,:Native species:Yes,:Region:Texas,:Sun requirement:Full sun,:Bloom period:April through October',
        'variants': [
            {'var_id': 462897, 'weight': '0.25', 'price': 13.99, 'coverage': 750,   'cogs': 5.43},
            {'var_id': 462898, 'weight': '0.5',  'price': 25.19, 'coverage': 1500,  'cogs': 10.85},
            {'var_id': 462899, 'weight': '1',    'price': 46.74, 'coverage': 3000,  'cogs': 21.70},
        ]
    },

    # -------------------------------------------------------
    # 7. Drummond Phlox Seeds (W-PHDR)
    # -------------------------------------------------------
    {
        'name': 'Drummond Phlox Seeds',
        'sku_prefix': 'W-PHDR',
        'subtitle': 'Texas-Native Annual Wildflower',
        'category_slug': 'wildflower-seed',
        'product_slug': 'drummond-phlox-seeds',
        'item_group_id': 'NS_0109',
        'gtin': '840184626838',
        'image_link': f'{BASE_URL}/wp-content/uploads/2026/02/Drummond-Phlox-Seeds.webp',
        'additional_image_link': f'{BASE_URL}/wp-content/uploads/2025/07/WildflowerBag-2.png',
        'cl0': 'wildflower',
        'product_type': 'Wildflower Seeds > Single Species Wildflower',
        'base_unit': '0.25',
        'description': (
            "Add multicolor spring beauty to your Texas landscape with Drummond Phlox Seeds (Phlox drummondii) "
            "from Nature's Seed. The only annual phlox species native to Texas, Drummond Phlox produces "
            "vibrant clusters of red, pink, purple, and white blooms from March through May.\n\n"
            "Why you'll love Drummond Phlox\n"
            "The only annual phlox native to Texas with multicolor blooms in red, pink, purple, and white\n"
            "Perfect bluebonnet companion plant with identical growing requirements\n"
            "Easy fall planting produces reliable spring color from March through May\n"
            "Thrives in full sun to partial shade with well-drained, slightly acidic soil\n"
            "Self-seeding annual returns each spring with minimal effort\n"
            "Compact 6-12 inch height ideal for borders, beds, and meadow plantings\n\n"
            "Ideal for wildflower meadows, borders, rock gardens, and companion planting with Texas Bluebonnets. "
            "Plant seeds in fall (September through December) at 0.25 lb per 1,000 sq ft. "
            "Cover lightly as seeds require darkness for germination."
        ),
        'highlights': [
            "Only annual phlox species native to Texas with stunning multicolor blooms",
            "Perfect companion plant for Texas Bluebonnets with identical growing needs",
            "Vibrant red, pink, purple, and white flower clusters from March through May",
            "Thrives in full sun to partial shade in well-drained Texas soils",
            "Self-seeding annual that returns reliably with minimal maintenance",
            "Compact 6-12 inch height perfect for borders, beds, and meadow plantings"
        ],
        'product_detail': ':Seed type:Single species,:Native species:Yes,:Region:Texas,:Sun requirement:Full sun to partial shade,:Bloom period:March through May',
        'variants': [
            {'var_id': 462900, 'weight': '0.25', 'price': 10.99, 'coverage': 1000,  'cogs': 4.16},
            {'var_id': 462901, 'weight': '0.5',  'price': 18.89, 'coverage': 2000,  'cogs': 8.32},
            {'var_id': 462902, 'weight': '1',    'price': 35.69, 'coverage': 4000,  'cogs': 16.63},
        ]
    },
]


# ============================================================
# GENERATE ROWS
# ============================================================

def generate_rows():
    """Generate all 21 feed rows."""
    rows = []

    for product in PRODUCTS:
        for i, variant in enumerate(product['variants']):
            is_first = (i == 0)
            is_kit = not is_first  # First variant = base, others = KIT

            weight = variant['weight']
            price = variant['price']
            coverage = variant['coverage']

            # Build title: "Product Name - Key Feature - Weight, Covers X sq ft | Nature's Seed"
            title = (f"{product['name']} - {product['subtitle']} - "
                     f"{weight} lb, Covers {format_coverage(coverage)} sq ft | Nature's Seed")

            # Build URL
            link = build_link(
                product['category_slug'],
                product['product_slug'],
                variant['var_id'],
                weight,
                coverage
            )

            # Build MPN
            mpn = build_mpn(product['sku_prefix'], weight, is_kit)

            # Multipack
            mp = multipack_value(weight, product['base_unit'])

            # Highlights (formatted as comma-separated double-quoted strings)
            # Variant-specific: update coverage in first highlight if applicable
            highlights_formatted = ','.join(f'"{h}"' for h in product['highlights'])

            # Product detail with coverage
            detail = product['product_detail'] + f',:Coverage area:{coverage} sq ft'

            # Build the row dict
            row = {
                'id': f'gla_{variant["var_id"]}',
                'mpn': mpn,
                'Title': title,
                'description': product['description'],
                'availability': 'in_stock',
                'availability date': '',
                'expiration date': '',
                'link': link,
                'mobile link': '',
                'image link': product['image_link'],
                'price': format_price(price),
                'sale price': '',
                'sale price effective date': '',
                'identifier exists': 'yes',
                'gtin': product['gtin'],
                'brand': BRAND,
                'product highlight': highlights_formatted,
                'product detail': detail,
                'additional image link': product['additional_image_link'],
                'condition': 'new',
                'adult': 'no',
                'color': '',
                'size': '',
                'size type': '',
                'size system': '',
                'gender': '',
                'material': '',
                'pattern': '',
                'age group': '',
                'multipack': mp,
                'is bundle': 'no',
                'shipping_weight': f'{weight} lb',
                'unit pricing measure': f'{product["base_unit"]} lb',
                'unit pricing base measure': '1 lb',
                'energy efficiency class': '',
                'min energy efficiency class': '',  # First one
                'item group id': product['item_group_id'],
                'sell on google quantity': '100',
                'Custom label 0': product['cl0'],
                'Custom label 1': 'Texas',
                'Custom label 2': price_bucket(price),
                'Custom label 3': margin_tier(price, variant['cogs']),
                'Custom label 4': '',
                'Google product category': GOOGLE_PRODUCT_CAT,
                'Product Type': product['product_type'],
                'cost_of_goods_sold': format_price(variant['cogs']),
            }

            rows.append(row)

    return rows


def main():
    rows = generate_rows()

    # Write CSV
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            # Handle the duplicate "min energy efficiency class" column
            # DictWriter will use the key once, but we need it twice
            # We'll write manually to handle this edge case
            pass

    # Actually, since there are duplicate column headers, let's use csv.writer instead
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(HEADERS)

        for row in rows:
            csv_row = [
                row['id'],
                row['mpn'],
                row['Title'],
                row['description'],
                row['availability'],
                row['availability date'],
                row['expiration date'],
                row['link'],
                row['mobile link'],
                row['image link'],
                row['price'],
                row['sale price'],
                row['sale price effective date'],
                row['identifier exists'],
                row['gtin'],
                row['brand'],
                row['product highlight'],
                row['product detail'],
                row['additional image link'],
                row['condition'],
                row['adult'],
                row['color'],
                row['size'],
                row['size type'],
                row['size system'],
                row['gender'],
                row['material'],
                row['pattern'],
                row['age group'],
                row['multipack'],
                row['is bundle'],
                row['shipping_weight'],
                row['unit pricing measure'],
                row['unit pricing base measure'],
                row['energy efficiency class'],
                row['min energy efficiency class'],  # First duplicate
                row['min energy efficiency class'],  # Second duplicate
                row['item group id'],
                row['sell on google quantity'],
                row['Custom label 0'],
                row['Custom label 1'],
                row['Custom label 2'],
                row['Custom label 3'],
                row['Custom label 4'],
                row['Google product category'],
                row['Product Type'],
                row['cost_of_goods_sold'],
            ]
            writer.writerow(csv_row)

    print(f'\n{"="*70}')
    print(f'Texas Collection Feed Generated: {OUTPUT_FILE}')
    print(f'{"="*70}')
    print(f'Total rows: {len(rows)} (7 products x 3 variants)')
    print()

    # Print summary table
    print(f'{"Product":<35} {"MPN":<25} {"Price":>10} {"COGS":>10} {"Margin":>8} {"Tier":<16}')
    print('-' * 110)
    negative_count = 0
    for row in rows:
        price_val = float(row["price"].replace(' USD', ''))
        cogs_val = float(row["cost_of_goods_sold"].replace(' USD', ''))
        margin_pct = (price_val - cogs_val) / price_val * 100 if price_val > 0 else 0
        flag = ' ⚠️' if margin_pct < 0 else ''
        if margin_pct < 0:
            negative_count += 1
        print(f'{row["Title"][:34]:<35} {row["mpn"]:<25} {row["price"]:>10} {row["cost_of_goods_sold"]:>10} '
              f'{margin_pct:>7.1f}% {row["Custom label 3"]:<16}{flag}')

    if negative_count > 0:
        print(f'\n⚠️  WARNING: {negative_count} of {len(rows)} variants have NEGATIVE margins (COGS > Price)')
        print('   These products are selling at a loss. You may want to review pricing.')

    print()
    print('READY TO PASTE:')
    print('  1. Open texas_collection_feed.csv')
    print('  2. Copy the 21 data rows (skip the header)')
    print('  3. Paste at the bottom of your live Google Merchant Center feed sheet')
    print()


if __name__ == '__main__':
    main()
