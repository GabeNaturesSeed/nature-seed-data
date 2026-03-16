#!/usr/bin/env python3
"""
Inject product card HTML into resource/blog articles.

For each resource article that has related products (from the ACF mapping),
this script:
1. Fetches the resource post content via WP REST API
2. Fetches product data (title, permalink, image, price) via WC REST API
3. Builds a styled product card section
4. Appends it to the article content
5. PUTs the updated content back

Usage:
    python inject_product_cards.py --dry-run   # Preview without updating
    python inject_product_cards.py --push       # Actually update posts
"""

import argparse
import json
import os
import sys
import time
import requests
from pathlib import Path
from urllib.parse import urlparse

# ── Config ──────────────────────────────────────────────────────────────
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
DATA_DIR = Path(__file__).resolve().parent / "data"
RATE_LIMIT = 0.4  # seconds between API calls

# ── Load .env ───────────────────────────────────────────────────────────
env_vars = {}
with open(ENV_PATH) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

WC_CK = env_vars["WC_CK"]
WC_CS = env_vars["WC_CS"]
WP_USER = env_vars["WP_USERNAME"]
WP_PASS = env_vars["WP_APP_PASSWORD"]
WC_BASE = "https://naturesseed.com/wp-json/wc/v3"
WP_BASE = "https://naturesseed.com/wp-json/wp/v2"

# ── Slug Aliases: mapping slug → actual WC slug ─────────────────────────
SLUG_ALIASES = {
    "alpaca-llama-pasture-forage-mix": "products-pasture-seed-alpaca-llama-pasture-forage-mix",
    "alsike-clover-seed": "alsike-clover",
    "bermudagrass": "triblade-elite-bermudagrass-lawn-mix-2",
    "cattle-dairy-cow-pasture-mix-cold-warm-season": None,  # not in catalog
    "cattle-dairy-cow-pasture-mix-for-warm-season": None,  # not in catalog
    "clover-lawn-alternative-mix": "lawn-alternative-clover-mix",
    "crimsom-clover-crop-seed": "crimson-clover",
    "first-year-and-perennial-foundation-wildflower-kit": "first-year-color-perennial-foundation-wildflower-kit",
    "goat-pasture-forage-mix-transitional": None,  # not in catalog
    "high-traffic-hardy-lawn": "hardy-grass-seed-mix-for-high-traffic-lawns",
    "horse-pastures-seed": None,  # ambiguous search result
    "native-cabin-grass-mix": "products-pasture-seed-native-cabin-grass-mix",
    "overseed-and-repair-lawn-kit": "overseed-repair-lawn-kit",
    "red-clover-seed": "red-clover",
    "rice-hull": "rice-hulls-improve-seed-contact-germination-hold-moisture-25-lb-bag",
    "rice-hulls-improve-seed-contact-germination-hold-moisture": "rice-hulls-improve-seed-contact-germination-hold-moisture-25-lb-bag",
    "sundancer-buffalograss-seed": "sundancer-buffalograss-lawn-seed",
    "switchgrass-seed": "products-pasture-seed-switchgrass-seed",
    "thin-pasture-kit": "thin-pasture-fix-kit",
    "thingrass": "seashore-bentgrass-2",
    "triblade-elite-fescue-lawn-mix": "triblade-elite-fescue-lawn-mix-twca-certified",
}

# ── Reverse Map: article URL → product slugs ────────────────────────────
REVERSE_MAP = {
    "https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/": [
        "california-native-lawn-alternative-mix", "california-habitat-mix",
        "california-native-wildflower-mix", "california-coastal-native-wildflower-mix",
        "california-poppy", "brittlebush", "california-bush-sunflower", "white-sage",
        "purple-needlegrass", "arroyo-lupine", "golden-yarrow", "western-yarrow",
        "yellow-lupine", "miniature-lupine", "blue-eyed-grass", "bush-monkeyflower",
        "chaparral-sage-scrub-mix", "coastal-sage-scrub-mix",
        "central-valley-pollinator-mix-xerces-society", "narrowleaf-milkweed",
    ],
    "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/": [
        "california-native-lawn-alternative-mix", "california-habitat-mix", "thingrass",
        "california-native-wildflower-mix", "california-coastal-native-wildflower-mix",
        "california-poppy", "brittlebush", "california-bush-sunflower", "white-sage",
        "purple-needlegrass", "arroyo-lupine", "golden-yarrow", "western-yarrow",
        "yellow-lupine", "miniature-lupine", "blue-eyed-grass", "bush-monkeyflower",
        "chaparral-sage-scrub-mix", "coastal-sage-scrub-mix",
    ],
    "https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/": [
        "red-clover-seed", "crimsom-clover-crop-seed", "alsike-clover-seed",
        "goat-pasture-forage-mix-transitional", "pig-pasture-forage-mix",
        "poultry-forage-mix", "sheep-pasture-forage-mix-cold-season",
        "sheep-pasture-forage-mix-warm-season", "sheep-pasture-forage-mix-transitional",
        "alpaca-llama-pasture-forage-mix", "full-potential-food-plot",
        "krunch-and-munch-food-plot", "pasture-clover-mix-for-duck-quail-food-plot",
        "premium-irrigated-pasture-mix",
    ],
    "https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/": [
        "honey-bee-cover-crop-pasture-mix", "deer-resistant-wildflower-mix",
        "annual-wildflower-mix", "rocky-mountain-wildflower-mix",
        "central-valley-pollinator-mix-xerces-society", "narrowleaf-milkweed",
        "texas-bluebonnet-seeds", "texas-native-wildflower-mix",
        "texas-pollinator-wildflower-mix", "pink-evening-primrose-seeds",
        "drummond-phlox-seeds", "pollinator-corridor-kit",
        "first-year-and-perennial-foundation-wildflower-kit",
        "jimmys-perennial-wildflower-mix",
    ],
    "https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/": [
        "alsike-clover-seed", "alfalfa", "orchardgrass", "timothy", "cereal-rye",
        "horse-pasture-mix-cold-season", "horse-pasture-mix-warm-season",
        "cattle-dairy-cow-pasture-mix-cold-warm-season",
        "cattle-dairy-cow-pasture-mix-for-warm-season",
        "sheep-pasture-forage-mix-cold-season", "sheep-pasture-forage-mix-transitional",
        "thin-pasture-kit",
    ],
    "https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/": [
        "blue-grama", "horse-pastures-seed", "horse-pasture-mix-warm-season",
        "horse-pasture-mix-transitional", "cattle-dairy-cow-pasture-mix-for-warm-season",
        "sheep-pasture-forage-mix-warm-season", "dryland-pasture-mix",
        "shortgrass-prairie-mix", "sandhills-prairie-mix", "plains-prairie-mix",
        "m-binder-tackifier-soil-stabilizer",
    ],
    "https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/": [
        "switchgrass-seed", "common-buckwheat", "shade-mix-food-plot",
        "big-game-food-plot-forage-mix", "full-potential-food-plot",
        "green-screen-food-plot-screen", "krunch-and-munch-food-plot",
        "upland-game-mix", "pasture-clover-mix-for-duck-quail-food-plot",
    ],
    "https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-the-great-plains/": [
        "blue-grama", "big-game-food-plot-forage-mix", "dryland-pasture-mix",
        "native-cabin-grass-mix", "shortgrass-prairie-mix", "sandhills-prairie-mix",
        "plains-prairie-mix", "texas-native-prairie-mix",
    ],
    "https://naturesseed.com/resources/agriculture/best-cover-crops-for-the-midwest/": [
        "crimsom-clover-crop-seed", "cereal-rye", "common-buckwheat",
        "honey-bee-cover-crop-pasture-mix", "weed-smother-cover-crop-kit",
        "soil-builder-cover-crop-kit", "mustard-biofumigant-blend-cover-crop-seed-mix",
    ],
    "https://naturesseed.com/resources/lawn-turf/texas/": [
        "texas-native-lawn-mix", "texas-native-prairie-mix", "texas-bluebonnet-seeds",
        "texas-native-wildflower-mix", "texas-pollinator-wildflower-mix",
        "pink-evening-primrose-seeds", "drummond-phlox-seeds",
    ],
    "https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/": [
        "orchardgrass", "timothy", "goat-pasture-forage-mix-transitional",
        "alpaca-llama-pasture-forage-mix", "thin-pasture-kit",
        "premium-irrigated-pasture-mix",
    ],
    "https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/": [
        "clover-lawn-alternative-mix", "white-dutch-clover", "white-clover",
        "microclover", "red-clover-seed",
        "white-dutch-clover-soil-grass-health-boost-5lb-for-10000-sq-ft",
    ],
    "https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/": [
        "deer-resistant-wildflower-mix", "annual-wildflower-mix",
        "rocky-mountain-wildflower-mix", "pollinator-corridor-kit",
        "first-year-and-perennial-foundation-wildflower-kit",
        "jimmys-perennial-wildflower-mix",
    ],
    "https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/": [
        "tall-fescue", "horse-pastures-seed", "horse-pasture-mix-cold-season",
        "horse-pasture-mix-transitional", "cattle-dairy-cow-pasture-mix-cold-warm-season",
    ],
    "https://naturesseed.com/resources/lawn-turf/fescue-grass-seed-for-shady-areas/": [
        "triblade-elite-fescue-lawn-mix", "fine-fescue-grass-seed-mix",
        "twca-water-wise-shade-mix", "tall-fescue", "pet-kid-friendly-fescue-lawn-bundle",
    ],
    "https://naturesseed.com/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/": [
        "jimmys-blue-ribbon-premium-grass-seed-mix", "overseed-and-repair-lawn-kit",
        "rice-hull", "rice-hulls-improve-seed-contact-germination-hold-moisture",
        "m-binder-tackifier-soil-stabilizer",
    ],
    "https://naturesseed.com/resources/lawn-turf/what-exactly-is-a-low-maintenance-lawn/": [
        "sheep-fescue-grass", "meadow-lawn-blend", "thingrass", "native-cabin-grass-mix",
    ],
    "https://naturesseed.com/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/": [
        "twca-water-wise-sun-shade-mix", "twca-water-wise-shade-mix", "shade-mix-food-plot",
    ],
    "https://naturesseed.com/resources/lawn-turf/how-to-choose-the-right-grass-seed/": [
        "jimmys-blue-ribbon-premium-grass-seed-mix", "texas-native-lawn-mix", "bahia-grass",
    ],
    "https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bluegrass-seed-lawn/": [
        "water-wise-bluegrass-blend", "kentucky-bluegrass-seed-blue-ribbon-mix",
        "kentucky-bluegrass",
    ],
    "https://naturesseed.com/resources/lawn-turf/how-to-grow-grass-with-dogs/": [
        "high-traffic-hardy-lawn", "pet-kid-friendly-fescue-lawn-bundle",
        "premium-pet-kid-friendly-bluegrass-bundle",
    ],
    "https://naturesseed.com/resources/lawn-turf/how-to-plant-and-grow/": [
        "kentucky-bluegrass-seed-blue-ribbon-mix", "kentucky-bluegrass",
        "premium-pet-kid-friendly-bluegrass-bundle",
    ],
    "https://naturesseed.com/resources/lawn-turf/teeny-tiny-clover-trend/": [
        "clover-lawn-alternative-mix", "white-dutch-clover", "microclover",
    ],
    "https://naturesseed.com/resources/wildlife-habitat-sustainability/switchgrass-a-grass-of-many-uses/": [
        "switchgrass-seed", "green-screen-food-plot-screen", "upland-game-mix",
    ],
    "https://naturesseed.com/resources/agriculture/mustard-cover-crops-for-soil-fumigation/": [
        "weed-smother-cover-crop-kit", "mustard-biofumigant-blend-cover-crop-seed-mix",
    ],
    "https://naturesseed.com/resources/lawn-turf/a-guide-to-grass-seed-germination/": [
        "rice-hull", "rice-hulls-improve-seed-contact-germination-hold-moisture",
    ],
    "https://naturesseed.com/resources/lawn-turf/an-introduction-to-buffalograss/": [
        "sundancer-buffalograss-seed", "buffalograss",
    ],
    "https://naturesseed.com/resources/lawn-turf/bermuda-grass-seed-best-lawn-seed-for-sunny-yards/": [
        "bermudagrass-seed-blend", "bermudagrass",
    ],
    "https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/": [
        "bermudagrass-seed-blend", "bermudagrass",
    ],
    "https://naturesseed.com/resources/lawn-turf/how-to-plant-and-grow-perennial-ryegrass/": [
        "perennial-ryegrass-seed-blend", "perennial-ryegrass",
    ],
    "https://naturesseed.com/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/": [
        "perennial-ryegrass-seed-blend", "perennial-ryegrass",
    ],
    "https://naturesseed.com/resources/lawn-turf/organic-matter-achieving-the-best-possible-soil-conditions-for-grass-seed/": [
        "soil-builder-cover-crop-kit",
        "white-dutch-clover-soil-grass-health-boost-5lb-for-10000-sq-ft",
    ],
    "https://naturesseed.com/resources/lawn-turf/planting-a-buffalograss-lawn/": [
        "sundancer-buffalograss-seed", "buffalograss",
    ],
    "https://naturesseed.com/resources/agriculture/converting-your-old-alfalfa-field-into-a-productive-pasture/": ["alfalfa"],
    "https://naturesseed.com/resources/agriculture/pasture-pig-forage-mixes/": ["pig-pasture-forage-mix"],
    "https://naturesseed.com/resources/agriculture/pastured-poultry-what-kind-of-forages-should-your-chickens-be-grazing-on/": ["poultry-forage-mix"],
    "https://naturesseed.com/resources/lawn-turf/advantages-of-grass-seed-over-laying-sod/": ["meadow-lawn-blend"],
    "https://naturesseed.com/resources/lawn-turf/best-grass-seed-choices-for-athletic-fields/": ["high-traffic-hardy-lawn"],
    "https://naturesseed.com/resources/lawn-turf/common-mistakes-made-when-establishing-a-lawn-from-seed/": ["overseed-and-repair-lawn-kit"],
    "https://naturesseed.com/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/": ["organic-seed-starter-fertilizer-4-6-4"],
    "https://naturesseed.com/resources/lawn-turf/florida/": ["bahia-grass"],
    "https://naturesseed.com/resources/lawn-turf/how-much-sun-or-shade-does-a-bluegrass-seed-lawn-require/": ["water-wise-bluegrass-blend"],
    "https://naturesseed.com/resources/lawn-turf/how-often-should-you-water-new-grass-seed/": ["twca-water-wise-sun-shade-mix"],
    "https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-fescue-grass-seed-lawn/": ["triblade-elite-fescue-lawn-mix"],
    "https://naturesseed.com/resources/lawn-turf/how-to-grow-tall-fescue-grass-in-the-shade/": ["fine-fescue-grass-seed-mix"],
    "https://naturesseed.com/resources/lawn-turf/more-than-luck-why-you-should-add-clover-to-your-lawn-grass/": ["white-clover"],
    "https://naturesseed.com/resources/lawn-turf/sheep-fescue-as-an-alternative-lawn-grass/": ["sheep-fescue-grass"],
    "https://naturesseed.com/resources/news-and-misc/understanding-fertilizer-components/": ["organic-seed-starter-fertilizer-4-6-4"],
}


def load_product_cache():
    """Load cached product data to avoid redundant API calls."""
    cache_path = DATA_DIR / "product_cache.json"
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)
    return {}


def save_product_cache(cache):
    cache_path = DATA_DIR / "product_cache.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)


def fetch_product(slug, cache):
    """Fetch product data from WC API by slug, using cache and aliases."""
    if slug in cache:
        return cache[slug]

    # Resolve alias
    actual_slug = SLUG_ALIASES.get(slug, slug)
    if actual_slug is None:
        cache[slug] = None
        return None

    resp = requests.get(
        f"{WC_BASE}/products",
        auth=(WC_CK, WC_CS),
        params={"slug": actual_slug, "per_page": 1},
        timeout=15,
    )
    resp.raise_for_status()
    products = resp.json()
    time.sleep(RATE_LIMIT)

    if not products:
        print(f"    [SKIP] Product not found: {slug}")
        cache[slug] = None
        return None

    p = products[0]

    # Construct clean permalink from slug (API returns ugly ?post_type=product&p=ID)
    product_slug = p["slug"]
    clean_permalink = f"https://naturesseed.com/products/{product_slug}/"

    # Get price — variable products may have empty price, use price_html
    price = p.get("price", "")
    if not price and p.get("type") == "variable":
        # Try to extract from variations or just skip price display
        price = ""

    data = {
        "id": p["id"],
        "name": p["name"],
        "slug": product_slug,
        "permalink": clean_permalink,
        "price": price,
        "status": p.get("status", "publish"),
        "image_url": "",
        "image_alt": p["name"],
        "categories": [c["name"] for c in p.get("categories", [])],
    }

    # Get first image
    images = p.get("images", [])
    if images:
        data["image_url"] = images[0].get("src", "")
        data["image_alt"] = images[0].get("alt", "") or p["name"]

    cache[slug] = data
    return data


# ── Article Slug Aliases: URL slug → actual WP slug ─────────────────────
ARTICLE_SLUG_ALIASES = {
    "texas": "the-best-grass-seed-for-texas",
    "how-to-plant-and-grow": "how-to-plant-and-grow-kentucky-bluegrass",
    "advantages-of-grass-seed-over-laying-sod": "sod-vs-seed-whats-the-best-choice-for-your-lawn",
    "florida": "the-best-grass-seed-for-florida",
}


def slug_from_article_url(url):
    """Extract slug from article URL for WP API lookup, with alias support."""
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1]
    return ARTICLE_SLUG_ALIASES.get(slug, slug)


def fetch_resource_post(article_url):
    """Fetch resource post by slug from WP REST API."""
    slug = slug_from_article_url(article_url)
    resp = requests.get(
        f"{WP_BASE}/resource",
        auth=(WP_USER, WP_PASS),
        params={"slug": slug, "per_page": 1, "_fields": "id,title,slug,link,content"},
        timeout=15,
    )
    resp.raise_for_status()
    posts = resp.json()
    time.sleep(RATE_LIMIT)

    if not posts:
        return None
    return posts[0]


def build_product_card_html(products_data):
    """Build the product card section HTML matching the site's inline style."""
    if not products_data:
        return ""

    # Cap at 6 products to avoid overwhelming the article
    products_data = products_data[:6]

    cards_html = []
    for p in products_data:
        img_html = ""
        if p["image_url"]:
            img_html = (
                f'<img src="{p["image_url"]}" alt="{p["image_alt"]}" '
                f'style="width:100%;height:180px;object-fit:contain;'
                f'border-radius:8px 8px 0 0;" loading="lazy" />'
            )

        price_html = ""
        if p["price"]:
            price_html = (
                f'<p style="font-size:15px;color:#2d5a27;font-weight:700;'
                f'margin:0 0 12px 0;">From ${p["price"]}</p>'
            )

        card = f"""<div style="flex:1 1 260px;max-width:300px;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);text-align:center;">
  <div style="background:#f5f2eb;padding:16px 16px 0;">
    {img_html}
  </div>
  <div style="padding:16px 20px 20px;">
    <h4 style="font-size:16px;font-weight:700;color:#2d5a27;margin:0 0 8px 0;line-height:1.3;">{p["name"]}</h4>
    {price_html}
    <a href="{p["permalink"]}" style="display:inline-block;background-color:#f1b434;color:#fff;font-weight:600;font-size:14px;padding:10px 24px;border-radius:6px;text-decoration:none;transition:background 0.2s;">Shop Now</a>
  </div>
</div>"""
        cards_html.append(card)

    section_html = f"""
<!-- ns-product-cards -->
<section style="margin:48px 0;padding:36px 24px;background:#f9f7f2;border-radius:12px;">
  <h3 style="text-align:center;font-size:22px;color:#2d5a27;margin:0 0 8px 0;font-weight:700;">Shop Related Products</h3>
  <p style="text-align:center;color:#666;font-size:15px;margin:0 0 28px 0;">Premium seed mixes for your project</p>
  <div style="display:flex;flex-wrap:wrap;gap:20px;justify-content:center;">
    {"".join(cards_html)}
  </div>
</section>
<!-- /ns-product-cards -->
"""
    return section_html


def content_already_has_cards(content):
    """Check if product cards were already injected."""
    return "<!-- ns-product-cards -->" in content


def update_resource_post(post_id, new_content):
    """PUT updated content to resource post."""
    resp = requests.post(
        f"{WP_BASE}/resource/{post_id}",
        auth=(WP_USER, WP_PASS),
        json={"content": new_content},
        timeout=30,
    )
    resp.raise_for_status()
    time.sleep(RATE_LIMIT)
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Inject product cards into resource articles")
    parser.add_argument("--dry-run", action="store_true", help="Preview without updating")
    parser.add_argument("--push", action="store_true", help="Actually update posts")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of articles to process")
    args = parser.parse_args()

    if not args.dry_run and not args.push:
        print("  Specify --dry-run or --push")
        sys.exit(1)

    mode = "DRY RUN" if args.dry_run else "LIVE PUSH"
    print("=" * 60)
    print(f"  PRODUCT CARD INJECTION — {mode}")
    print("=" * 60)

    # Load product cache
    cache = load_product_cache()
    print(f"\n  Product cache: {len(cache)} entries")

    # Collect all unique product slugs needed
    all_slugs = set()
    for slugs in REVERSE_MAP.values():
        all_slugs.update(slugs)
    print(f"  Unique products to fetch: {len(all_slugs)}")

    # Pre-fetch all products
    print("\n  --- Fetching Product Data ---")
    fetched = 0
    for slug in sorted(all_slugs):
        if slug not in cache:
            fetch_product(slug, cache)
            fetched += 1
            if fetched % 10 == 0:
                print(f"    Fetched {fetched} products...")
                save_product_cache(cache)

    save_product_cache(cache)
    available = sum(1 for v in cache.values() if v is not None)
    print(f"  Products available: {available}/{len(all_slugs)}")

    # Process each article
    print("\n  --- Processing Articles ---")
    articles = list(REVERSE_MAP.items())
    if args.limit:
        articles = articles[:args.limit]

    updated = 0
    skipped_has_cards = 0
    skipped_not_found = 0
    skipped_no_products = 0
    errors = 0

    for i, (article_url, product_slugs) in enumerate(articles, 1):
        slug = slug_from_article_url(article_url)
        print(f"\n  [{i}/{len(articles)}] {slug}")

        # Fetch the resource post
        try:
            post = fetch_resource_post(article_url)
        except Exception as e:
            print(f"    [ERR] Failed to fetch post: {e}")
            errors += 1
            continue

        if not post:
            print(f"    [SKIP] Resource post not found")
            skipped_not_found += 1
            continue

        post_id = post["id"]
        content = post["content"]["rendered"]

        # Check if already injected
        if content_already_has_cards(content):
            print(f"    [SKIP] Already has product cards (ID: {post_id})")
            skipped_has_cards += 1
            continue

        # Gather product data
        products_data = []
        for ps in product_slugs:
            pd = cache.get(ps)
            if pd and pd.get("permalink"):
                products_data.append(pd)

        if not products_data:
            print(f"    [SKIP] No valid products found")
            skipped_no_products += 1
            continue

        # Build card HTML
        cards_html = build_product_card_html(products_data)
        new_content = content + cards_html

        card_count = min(len(products_data), 6)
        print(f"    Products: {card_count} cards (of {len(products_data)} matched) | Post ID: {post_id}")

        if args.push:
            try:
                update_resource_post(post_id, new_content)
                print(f"    [OK] Updated")
                updated += 1
            except Exception as e:
                print(f"    [ERR] Update failed: {e}")
                errors += 1
        else:
            print(f"    [DRY] Would inject {len(products_data)} product cards")
            updated += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"  SUMMARY ({mode})")
    print(f"    Updated:            {updated}")
    print(f"    Already had cards:  {skipped_has_cards}")
    print(f"    Post not found:     {skipped_not_found}")
    print(f"    No valid products:  {skipped_no_products}")
    print(f"    Errors:             {errors}")
    print("=" * 60)

    save_product_cache(cache)


if __name__ == "__main__":
    main()
