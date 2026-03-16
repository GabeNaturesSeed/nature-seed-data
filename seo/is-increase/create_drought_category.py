#!/usr/bin/env python3
"""
Create Drought-Tolerant Pasture Seed category on WooCommerce
=============================================================
1. Pull all pasture products
2. Identify drought-tolerant species/products
3. Create the category with RankMath SEO
4. Assign products to it

Usage:
    python3 IS-Increase/create_drought_category.py
"""

import json
import logging
import time
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("drought_cat")

ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> dict:
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip().strip("'\"")
    return env

ENV = _load_env()

WC_BASE = "https://naturesseed.com/wp-json/wc/v3"
WC_AUTH = (ENV.get("WC_CK", ""), ENV.get("WC_CS", ""))


def wc_get(endpoint, params=None):
    r = requests.get(f"{WC_BASE}/{endpoint}", auth=WC_AUTH, params=params, timeout=30)
    r.raise_for_status()
    return r.json(), r.headers


def wc_get_all(endpoint, params=None):
    params = params or {}
    params["per_page"] = 100
    page = 1
    all_items = []
    while True:
        params["page"] = page
        items, headers = wc_get(endpoint, params)
        if not items:
            break
        all_items.extend(items)
        total_pages = int(headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)
    return all_items


def wc_post(endpoint, data):
    r = requests.post(f"{WC_BASE}/{endpoint}", auth=WC_AUTH, json=data, timeout=30)
    r.raise_for_status()
    return r.json()


def wc_put(endpoint, data):
    r = requests.put(f"{WC_BASE}/{endpoint}", auth=WC_AUTH, json=data, timeout=30)
    r.raise_for_status()
    return r.json()


# ── Drought-tolerant species identifiers ─────────────────────────────────────
# These are grass/forage species known for drought tolerance

DROUGHT_SPECIES = [
    "bermuda", "buffalograss", "buffalo grass",
    "blue grama", "sideoats grama", "grama",
    "tall fescue", "hard fescue",
    "crested wheatgrass", "western wheatgrass", "wheatgrass",
    "switchgrass",
    "big bluestem", "little bluestem", "bluestem",
    "indiangrass", "indian grass",
    "sand lovegrass", "lovegrass",
    "green needlegrass", "needlegrass",
    "prairie sandreed",
    "drought", "dryland", "dry land", "arid",
    "water-wise", "water wise", "low water",
    "native range", "rangeland",
    "southern", "transitional",  # southern/transitional pastures tend toward drought tolerance
]

# Species that are NOT drought tolerant (to exclude false positives)
WET_SPECIES = [
    "orchardgrass only",  # orchardgrass alone is moderate, not drought
    "ryegrass only",
    "timothy only",
]


def is_drought_tolerant(product: dict) -> tuple:
    """Check if a product is drought-tolerant based on name, description, and species."""
    name = (product.get("name") or "").lower()
    desc = (product.get("description") or "").lower()
    short_desc = (product.get("short_description") or "").lower()
    all_text = f"{name} {desc} {short_desc}"

    # Check categories — Southern US Pasture and Transitional Zone products
    # are generally more drought-adapted
    cat_names = [c.get("name", "").lower() for c in product.get("categories", [])]

    reasons = []

    # Direct drought keyword matches
    for species in DROUGHT_SPECIES:
        if species in all_text:
            reasons.append(species)

    # Category signals
    if "southern us pasture" in " ".join(cat_names):
        reasons.append("Southern US category")
    if "transitional zone pasture" in " ".join(cat_names):
        reasons.append("Transitional zone category")

    # Check attributes for grass species
    for attr in product.get("attributes", []):
        attr_text = " ".join(attr.get("options", [])).lower()
        for species in DROUGHT_SPECIES:
            if species in attr_text:
                reasons.append(f"attribute: {species}")

    # Deduplicate reasons
    reasons = list(dict.fromkeys(reasons))

    return len(reasons) > 0, reasons


def run():
    # Step 1: Pull all pasture products
    log.info("Pulling all pasture products...")
    # Pasture Seed category ID: 3897
    pasture_products = wc_get_all("products", {"category": "3897", "status": "publish"})
    log.info(f"  Got {len(pasture_products)} pasture products")

    # Also pull individual pasture species (3916) and specialty/cover crop
    log.info("Pulling individual pasture species...")
    species_products = wc_get_all("products", {"category": "3916", "status": "publish"})
    log.info(f"  Got {len(species_products)} individual species products")

    # Also pull lawn products that might be drought-tolerant
    log.info("Pulling lawn products...")
    lawn_products = wc_get_all("products", {"category": "3881", "status": "publish"})
    log.info(f"  Got {len(lawn_products)} lawn products")

    # Merge and deduplicate
    all_products = {}
    for p in pasture_products + species_products + lawn_products:
        all_products[p["id"]] = p
    log.info(f"  {len(all_products)} unique products total")

    # Step 2: Identify drought-tolerant products
    log.info("\nAnalyzing drought tolerance...")
    drought_products = []
    non_drought = []

    for pid, product in all_products.items():
        is_dt, reasons = is_drought_tolerant(product)
        if is_dt:
            drought_products.append({
                "id": pid,
                "name": product["name"],
                "slug": product["slug"],
                "sku": product.get("sku", ""),
                "price": product.get("price", ""),
                "categories": [c["name"] for c in product.get("categories", [])],
                "reasons": reasons,
            })
        else:
            non_drought.append({"id": pid, "name": product["name"]})

    log.info(f"\n  DROUGHT-TOLERANT: {len(drought_products)} products")
    for dp in sorted(drought_products, key=lambda x: x["name"]):
        log.info(f"    ✓ {dp['name']} — {', '.join(dp['reasons'][:3])}")

    log.info(f"\n  NOT drought-tolerant: {len(non_drought)} products")
    for nd in sorted(non_drought, key=lambda x: x["name"]):
        log.info(f"    ✗ {nd['name']}")

    # Save analysis for review
    analysis_path = ROOT / "IS-Increase" / "drought_analysis.json"
    analysis_path.write_text(json.dumps({
        "drought_tolerant": drought_products,
        "not_drought_tolerant": non_drought,
    }, indent=2))
    log.info(f"\nSaved analysis: {analysis_path}")

    if not drought_products:
        log.warning("No drought-tolerant products found!")
        return

    # Step 3: Create the category
    log.info("\nCreating 'Drought-Tolerant Pasture Seed' category...")

    category_data = {
        "name": "Drought-Tolerant Pasture Seed",
        "slug": "drought-tolerant-pasture-seed",
        "parent": 3897,  # Under Pasture Seed
        "description": (
            "<p>Our drought-tolerant pasture seed mixes are specifically formulated for "
            "dry climates, arid conditions, and regions with limited rainfall. These deep-rooting "
            "grass and forage species thrive with minimal water while providing excellent grazing "
            "nutrition for horses, cattle, sheep, and other livestock.</p>"
            "<p>Each blend features proven drought-resistant species like Bermudagrass, Blue Grama, "
            "Buffalograss, Tall Fescue, Wheatgrass, and native warm-season grasses that establish "
            "strong root systems and maintain productivity even during extended dry periods.</p>"
            "<p>Whether you're establishing a new pasture in the Western US, renovating rangeland "
            "in Texas, or looking for water-wise forage options, our USDA-tested drought-tolerant "
            "seed blends deliver reliable performance with lower water requirements.</p>"
        ),
    }

    try:
        new_cat = wc_post("products/categories", category_data)
        cat_id = new_cat["id"]
        log.info(f"  Created category ID: {cat_id}")
        log.info(f"  URL: https://naturesseed.com/product-category/{new_cat['slug']}/")
    except requests.HTTPError as e:
        if "term_exists" in str(e.response.text):
            log.info("  Category already exists — finding it...")
            cats, _ = wc_get("products/categories", {"slug": "drought-tolerant-pasture-seed"})
            if cats:
                cat_id = cats[0]["id"]
                log.info(f"  Found existing category ID: {cat_id}")
            else:
                log.error("  Cannot find or create category")
                return
        else:
            raise

    # Step 4: Add RankMath SEO via product category meta
    # RankMath SEO is set via WordPress REST API, not WC API
    # We'll use the WP REST API to update the category's meta
    log.info("\nSetting RankMath SEO metadata...")

    seo_title = "Drought-Tolerant Pasture Seed | Water-Wise Forage Mixes | Nature's Seed"
    seo_desc = (
        "Shop drought-tolerant pasture grass seed mixes for dry climates & arid conditions. "
        "Deep-rooting varieties like Bermuda, Blue Grama & Tall Fescue. "
        "USDA-tested, free shipping. Perfect for Western, Texas & low-rainfall pastures."
    )

    # Try updating via WP REST API for RankMath
    wp_base = "https://naturesseed.com/wp-json/wp/v2"
    try:
        # RankMath stores SEO in term meta — try the rankmath endpoint
        rm_resp = requests.post(
            f"{wp_base}/product_cat/{cat_id}",
            auth=WC_AUTH,
            json={
                "meta": {
                    "rank_math_title": seo_title,
                    "rank_math_description": seo_desc,
                    "rank_math_focus_keyword": "drought tolerant pasture seed",
                }
            },
            timeout=30,
        )
        if rm_resp.status_code == 200:
            log.info(f"  RankMath SEO set successfully")
        else:
            log.warning(f"  RankMath update returned {rm_resp.status_code}: {rm_resp.text[:200]}")
            log.info(f"  SEO Title: {seo_title}")
            log.info(f"  SEO Desc: {seo_desc}")
            log.info("  → Set these manually in WordPress → Products → Categories → Drought-Tolerant → Edit → RankMath SEO")
    except Exception as e:
        log.warning(f"  RankMath API failed: {e}")
        log.info(f"  SEO Title: {seo_title}")
        log.info(f"  SEO Desc: {seo_desc}")
        log.info("  → Set manually in WordPress admin")

    # Step 5: Assign products to the new category
    log.info(f"\nAssigning {len(drought_products)} products to category {cat_id}...")

    assigned = 0
    failed = 0
    for dp in drought_products:
        pid = dp["id"]
        # Get current categories for this product
        try:
            product, _ = wc_get(f"products/{pid}")
            current_cats = [{"id": c["id"]} for c in product.get("categories", [])]

            # Add new category if not already there
            if not any(c["id"] == cat_id for c in current_cats):
                current_cats.append({"id": cat_id})
                wc_put(f"products/{pid}", {"categories": current_cats})
                log.info(f"  ✓ Added '{dp['name']}' to drought category")
                assigned += 1
            else:
                log.info(f"  ○ '{dp['name']}' already in category")
            time.sleep(0.3)
        except Exception as e:
            log.error(f"  ✗ Failed '{dp['name']}': {e}")
            failed += 1

    log.info(f"\n{'='*60}")
    log.info("DROUGHT CATEGORY CREATION COMPLETE")
    log.info(f"{'='*60}")
    log.info(f"  Category ID: {cat_id}")
    log.info(f"  URL: https://naturesseed.com/product-category/pasture-seed/drought-tolerant-pasture-seed/")
    log.info(f"  Products assigned: {assigned}")
    log.info(f"  Already in category: {len(drought_products) - assigned - failed}")
    log.info(f"  Failed: {failed}")
    log.info(f"\n  SEO Title: {seo_title}")
    log.info(f"  SEO Description: {seo_desc}")
    log.info(f"  Focus Keyword: drought tolerant pasture seed")

    # Save results
    results_path = ROOT / "IS-Increase" / "drought_category_results.json"
    results_path.write_text(json.dumps({
        "category_id": cat_id,
        "category_url": f"https://naturesseed.com/product-category/pasture-seed/drought-tolerant-pasture-seed/",
        "seo_title": seo_title,
        "seo_description": seo_desc,
        "products_assigned": [dp["name"] for dp in drought_products],
        "products_count": len(drought_products),
    }, indent=2))


if __name__ == "__main__":
    run()
