#!/usr/bin/env python3
"""Build cross-purchase affinity matrix from WooCommerce order data.

This script creates reusable cross-purchase analysis datasets that can be
referenced by multiple future projects (email campaigns, product recommendations, etc.)

Output files:
  analysis/cross_purchase_matrix.csv  — Full category affinity matrix
  analysis/upsell_recommendations.csv — Top cross-sell/upsell per category
  analysis/customer_category_map.json — Raw customer→categories purchased data
"""

import json
import csv
import os
import re
from collections import defaultdict, Counter
from itertools import combinations

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
ANALYSIS_DIR = os.path.join(os.path.dirname(__file__), 'analysis')
os.makedirs(ANALYSIS_DIR, exist_ok=True)

# Category normalization map: old Magento/WC categories → current WC categories
# This handles the category structure changes from the platform migration
CATEGORY_NORMALIZE = {
    # Old → New mappings
    'grass seed': 'Lawn Seed',
    'grass-seed': 'Lawn Seed',
    'lawn grass seed': 'Lawn Seed',
    'lawn seed': 'Lawn Seed',
    'northern lawn': 'Northern Lawn',
    'southern lawn': 'Southern Lawn',
    'transitional lawn': 'Transitional Lawn',
    'water-wise lawn': 'TWCA - Water-Wise Lawn',
    'twca - water-wise lawn': 'TWCA - Water-Wise Lawn',
    'sports turf/high traffic': 'Sports Turf/High Traffic',
    'sports turf': 'Sports Turf/High Traffic',
    'lawn alternatives': 'Lawn Alternatives',

    'pasture seed': 'Pasture Seed',
    'pasture': 'Pasture Seed',
    'horse pasture': 'Horse Pasture',
    'horse pasture seed': 'Horse Pasture',
    'cattle pasture': 'Cattle Pasture',
    'cattle pasture seed': 'Cattle Pasture',
    'goat pasture': 'Goat Pasture',
    'goat pasture seed': 'Goat Pasture',
    'sheep pastures': 'Sheep Pastures',
    'sheep pasture': 'Sheep Pastures',
    'sheep pasture seed': 'Sheep Pastures',
    'individual pasture species': 'Individual Pasture Species',
    'northern us pasture': 'Northern US Pasture',
    'southern us pasture': 'Southern US Pasture',
    'transitional zone pasture': 'Transitional Zone Pasture',

    'wildflower seed': 'Native Wildflower Seed',
    'wildflower seeds': 'Native Wildflower Seed',
    'native wildflower seed': 'Native Wildflower Seed',
    'wildflowers': 'Native Wildflower Seed',

    'california collection': 'California Collection',
    'california native': 'California Collection',

    'clover seed': 'Clover Seed',
    'clover': 'Clover Seed',

    'specialty seed': 'Specialty Seed',
    'food plot seed': 'Food Plot Seed',
    'food plot': 'Food Plot Seed',
    'cover crop seed': 'Cover Crop Seed',
    'cover crop': 'Cover Crop Seed',

    'planting aids': 'Planting Aids',
    'planting aid': 'Planting Aids',

    'all seed': 'All Seed',  # generic parent, will be filtered out
    'uncategorized': 'Uncategorized',

    # Magento-era categories
    'conservation seed': 'Specialty Seed',
    'erosion control': 'Specialty Seed',
    'ground cover': 'Lawn Alternatives',
    'native grass seed': 'Specialty Seed',
    'buffalo grass': 'Lawn Seed',
    'bermuda grass': 'Southern Lawn',
    'fescue': 'Lawn Seed',
    'bluegrass': 'Lawn Seed',
    'ryegrass': 'Lawn Seed',
}

# Top-level categories we care about for the affinity matrix
# (exclude "All Seed" which is too generic)
TOP_CATEGORIES = [
    'Lawn Seed',
    'Northern Lawn',
    'Southern Lawn',
    'Transitional Lawn',
    'TWCA - Water-Wise Lawn',
    'Sports Turf/High Traffic',
    'Lawn Alternatives',
    'Pasture Seed',
    'Horse Pasture',
    'Cattle Pasture',
    'Goat Pasture',
    'Sheep Pastures',
    'Northern US Pasture',
    'Southern US Pasture',
    'Transitional Zone Pasture',
    'Individual Pasture Species',
    'Native Wildflower Seed',
    'California Collection',
    'Clover Seed',
    'Specialty Seed',
    'Food Plot Seed',
    'Cover Crop Seed',
    'Planting Aids',
]

# Higher-level groupings for broader cross-sell analysis
CATEGORY_GROUPS = {
    'Lawn': ['Lawn Seed', 'Northern Lawn', 'Southern Lawn', 'Transitional Lawn',
             'TWCA - Water-Wise Lawn', 'Sports Turf/High Traffic', 'Lawn Alternatives'],
    'Pasture': ['Pasture Seed', 'Horse Pasture', 'Cattle Pasture', 'Goat Pasture',
                'Sheep Pastures', 'Northern US Pasture', 'Southern US Pasture',
                'Transitional Zone Pasture', 'Individual Pasture Species'],
    'Wildflower': ['Native Wildflower Seed'],
    'California': ['California Collection'],
    'Clover': ['Clover Seed'],
    'Specialty': ['Specialty Seed', 'Food Plot Seed', 'Cover Crop Seed'],
    'Planting Aids': ['Planting Aids'],
}

# Reverse lookup: sub-category → group
SUB_TO_GROUP = {}
for group, subs in CATEGORY_GROUPS.items():
    for sub in subs:
        SUB_TO_GROUP[sub] = group


def normalize_category(cat):
    """Normalize a category name to current WC taxonomy."""
    cat_lower = cat.lower().strip()
    return CATEGORY_NORMALIZE.get(cat_lower, cat.strip())


def infer_categories_from_name(product_name):
    """Infer product categories from product name when categories are missing."""
    name_lower = product_name.lower()
    cats = set()

    # Pasture keywords
    if 'pasture' in name_lower:
        cats.add('Pasture Seed')
        if 'horse' in name_lower:
            cats.add('Horse Pasture')
        if 'cattle' in name_lower or 'cow' in name_lower:
            cats.add('Cattle Pasture')
        if 'sheep' in name_lower:
            cats.add('Sheep Pastures')
        if 'goat' in name_lower:
            cats.add('Goat Pasture')
        if 'northern' in name_lower or 'cool season' in name_lower:
            cats.add('Northern US Pasture')
        if 'southern' in name_lower or 'warm season' in name_lower:
            cats.add('Southern US Pasture')

    # Lawn keywords
    if any(kw in name_lower for kw in ['lawn', 'turf', 'bermuda', 'bluegrass', 'fescue', 'ryegrass']):
        cats.add('Lawn Seed')
        if 'northern' in name_lower or 'cool season' in name_lower:
            cats.add('Northern Lawn')
        if 'southern' in name_lower or 'warm season' in name_lower:
            cats.add('Southern Lawn')

    # Wildflower keywords
    if 'wildflower' in name_lower:
        cats.add('Native Wildflower Seed')
        if 'california' in name_lower:
            cats.add('California Collection')

    # Clover
    if 'clover' in name_lower:
        cats.add('Clover Seed')

    # Food plot
    if 'food plot' in name_lower or 'deer plot' in name_lower:
        cats.add('Food Plot Seed')

    # Cover crop
    if 'cover crop' in name_lower:
        cats.add('Cover Crop Seed')

    # Planting aids
    if any(kw in name_lower for kw in ['tackifier', 'rice hull', 'mulch', 'planting aid']):
        cats.add('Planting Aids')

    # California
    if 'california' in name_lower:
        cats.add('California Collection')

    return cats if cats else {'Specialty Seed'}


def load_wc_orders():
    """Load all WooCommerce order files and extract customer→product→category data."""
    customer_purchases = defaultdict(lambda: defaultdict(set))  # email → {product_name: {categories}}
    customer_product_values = defaultdict(lambda: defaultdict(float))  # email → {product_name: total_value}

    # Load active products for category lookup
    active_products = {}
    try:
        with open(os.path.join(DATA_DIR, 'products_active.json')) as f:
            for p in json.load(f):
                active_products[p['sku']] = {
                    'name': p['name'],
                    'categories': [c['name'] for c in p.get('categories', [])],
                }
    except FileNotFoundError:
        pass

    # Load inactive products too
    try:
        with open(os.path.join(DATA_DIR, 'products_inactive.json')) as f:
            for p in json.load(f):
                if p['sku']:
                    active_products[p['sku']] = {
                        'name': p['name'],
                        'categories': [c['name'] for c in p.get('categories', [])],
                    }
    except FileNotFoundError:
        pass

    order_files = [
        'orders_2024_q3q4.json',
        'orders_q1_2025.json',
        'orders_q2_2025.json',
        'orders_2025_q3.json',
        'orders_2025_q4.json',
        'orders_2026_q1.json',
    ]

    total_orders = 0
    total_items = 0

    for fname in order_files:
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  Skipping {fname} (not found)")
            continue

        with open(fpath) as f:
            orders = json.load(f)

        print(f"  Processing {fname}: {len(orders)} orders")
        total_orders += len(orders)

        for order in orders:
            email = order.get('customer_email', '').lower().strip()
            if not email:
                continue

            for li in order.get('line_items', []):
                sku = li.get('sku', '')
                name = li.get('name', '')
                value = float(li.get('total', 0) or 0)
                total_items += 1

                # Try to get categories from product database
                categories = set()
                if sku and sku in active_products:
                    for cat in active_products[sku].get('categories', []):
                        normalized = normalize_category(cat)
                        if normalized in TOP_CATEGORIES:
                            categories.add(normalized)

                # If no categories found, infer from product name
                if not categories and name:
                    categories = infer_categories_from_name(name)

                # Filter to only relevant categories
                categories = {c for c in categories if c in TOP_CATEGORIES}

                if categories:
                    customer_purchases[email][name] |= categories
                    customer_product_values[email][name] += value

    print(f"\n  Total: {total_orders} orders, {total_items} line items")
    print(f"  Unique customers with categorized purchases: {len(customer_purchases)}")

    return customer_purchases, customer_product_values


def build_affinity_matrix(customer_purchases):
    """Build category co-purchase affinity matrix.

    For each pair of categories (A, B), calculate:
    - co_purchase_count: number of customers who bought from both A and B
    - a_total: total customers who bought from A
    - b_total: total customers who bought from B
    - a_to_b_rate: % of A customers who also bought B
    - b_to_a_rate: % of B customers who also bought A
    """
    # Build customer → set of categories
    customer_categories = {}
    for email, products in customer_purchases.items():
        cats = set()
        for product_name, product_cats in products.items():
            cats |= product_cats
        if cats:
            customer_categories[email] = cats

    # Also build customer → set of category GROUPS
    customer_groups = {}
    for email, cats in customer_categories.items():
        groups = set()
        for cat in cats:
            if cat in SUB_TO_GROUP:
                groups.add(SUB_TO_GROUP[cat])
        customer_groups[email] = groups

    # Count customers per category
    cat_counts = Counter()
    for cats in customer_categories.values():
        for cat in cats:
            cat_counts[cat] += 1

    group_counts = Counter()
    for groups in customer_groups.values():
        for g in groups:
            group_counts[g] += 1

    # Count co-purchases (detailed categories)
    cat_co_purchase = defaultdict(int)
    for cats in customer_categories.values():
        for a, b in combinations(sorted(cats), 2):
            cat_co_purchase[(a, b)] += 1

    # Count co-purchases (groups)
    group_co_purchase = defaultdict(int)
    for groups in customer_groups.values():
        for a, b in combinations(sorted(groups), 2):
            group_co_purchase[(a, b)] += 1

    # Build detailed affinity rows
    detail_rows = []
    for (a, b), count in sorted(cat_co_purchase.items(), key=lambda x: -x[1]):
        a_total = cat_counts[a]
        b_total = cat_counts[b]
        if a_total > 0 and b_total > 0:
            detail_rows.append({
                'category_a': a,
                'category_b': b,
                'co_purchase_customers': count,
                'category_a_total_customers': a_total,
                'category_b_total_customers': b_total,
                'a_to_b_rate': round(count / a_total * 100, 1),
                'b_to_a_rate': round(count / b_total * 100, 1),
                'level': 'subcategory',
            })

    # Build group-level affinity rows
    group_rows = []
    for (a, b), count in sorted(group_co_purchase.items(), key=lambda x: -x[1]):
        a_total = group_counts[a]
        b_total = group_counts[b]
        if a_total > 0 and b_total > 0:
            group_rows.append({
                'category_a': a,
                'category_b': b,
                'co_purchase_customers': count,
                'category_a_total_customers': a_total,
                'category_b_total_customers': b_total,
                'a_to_b_rate': round(count / a_total * 100, 1),
                'b_to_a_rate': round(count / b_total * 100, 1),
                'level': 'group',
            })

    return detail_rows + group_rows, cat_counts, group_counts


def generate_upsell_recommendations(customer_purchases, customer_product_values, cat_counts):
    """Generate top cross-sell/upsell recommendations per category.

    For each category, identify:
    1. Top 3 cross-sell categories (highest affinity rate with min threshold)
    2. Top products within those cross-sell categories
    3. Upsell opportunities (larger sizes of same products)
    """
    # Build customer → category set
    customer_categories = {}
    for email, products in customer_purchases.items():
        cats = set()
        for pname, pcats in products.items():
            cats |= pcats
        customer_categories[email] = cats

    # Build category → co-purchase rates
    co_rates = defaultdict(lambda: defaultdict(float))
    for email, cats in customer_categories.items():
        for a in cats:
            for b in cats:
                if a != b:
                    co_rates[a][b] += 1

    # Normalize to percentages
    for cat_a in co_rates:
        total_a = cat_counts.get(cat_a, 1)
        for cat_b in co_rates[cat_a]:
            co_rates[cat_a][cat_b] = round(co_rates[cat_a][cat_b] / total_a * 100, 1)

    # Build category → top products purchased
    cat_product_revenue = defaultdict(lambda: defaultdict(float))
    cat_product_count = defaultdict(lambda: defaultdict(int))
    for email, products in customer_purchases.items():
        for pname, pcats in products.items():
            value = customer_product_values[email].get(pname, 0)
            for cat in pcats:
                cat_product_revenue[cat][pname] += value
                cat_product_count[cat][pname] += 1

    # Generate recommendations
    recommendations = []
    for source_cat in TOP_CATEGORIES:
        if source_cat not in co_rates or cat_counts.get(source_cat, 0) < 5:
            continue

        # Top 3 cross-sell categories (min 5% rate, min 10 co-purchase customers)
        cross_sells = sorted(
            [(target, rate) for target, rate in co_rates[source_cat].items()
             if target in TOP_CATEGORIES and rate >= 3.0],
            key=lambda x: -x[1]
        )[:5]

        for rank, (target_cat, rate) in enumerate(cross_sells, 1):
            # Get top products in target category
            top_products = sorted(
                cat_product_revenue[target_cat].items(),
                key=lambda x: -x[1]
            )[:3]

            for prod_name, prod_rev in top_products:
                prod_count = cat_product_count[target_cat].get(prod_name, 0)
                recommendations.append({
                    'source_category': source_cat,
                    'source_category_group': SUB_TO_GROUP.get(source_cat, source_cat),
                    'source_category_customers': cat_counts.get(source_cat, 0),
                    'cross_sell_rank': rank,
                    'target_category': target_cat,
                    'target_category_group': SUB_TO_GROUP.get(target_cat, target_cat),
                    'cross_sell_rate_pct': rate,
                    'recommended_product': prod_name,
                    'product_purchases': prod_count,
                    'product_revenue': round(prod_rev, 2),
                    'recommendation_type': 'cross_sell',
                })

    return recommendations


def main():
    print("=" * 70)
    print("CROSS-PURCHASE AFFINITY ANALYSIS")
    print("Building reusable cross-sell/upsell datasets")
    print("=" * 70)

    # Step 1: Load all WC order data
    print("\n--- Loading WooCommerce Orders ---")
    customer_purchases, customer_product_values = load_wc_orders()

    # Step 2: Build affinity matrix
    print("\n--- Building Category Affinity Matrix ---")
    affinity_rows, cat_counts, group_counts = build_affinity_matrix(customer_purchases)

    # Save affinity matrix
    if affinity_rows:
        with open(os.path.join(ANALYSIS_DIR, 'cross_purchase_matrix.csv'), 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(affinity_rows[0].keys()))
            w.writeheader()
            w.writerows(affinity_rows)
        print(f"  Saved {len(affinity_rows)} affinity pairs to cross_purchase_matrix.csv")

    # Step 3: Generate upsell recommendations
    print("\n--- Generating Cross-Sell Recommendations ---")
    recommendations = generate_upsell_recommendations(
        customer_purchases, customer_product_values, cat_counts
    )

    if recommendations:
        with open(os.path.join(ANALYSIS_DIR, 'upsell_recommendations.csv'), 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(recommendations[0].keys()))
            w.writeheader()
            w.writerows(recommendations)
        print(f"  Saved {len(recommendations)} recommendations to upsell_recommendations.csv")

    # Step 4: Save raw customer→category map (for reuse)
    customer_cat_map = {}
    for email, products in customer_purchases.items():
        cats = set()
        for pname, pcats in products.items():
            cats |= pcats
        groups = set()
        for cat in cats:
            if cat in SUB_TO_GROUP:
                groups.add(SUB_TO_GROUP[cat])
        customer_cat_map[email] = {
            'categories': sorted(cats),
            'groups': sorted(groups),
            'product_count': len(products),
            'total_value': round(sum(customer_product_values[email].values()), 2),
        }

    with open(os.path.join(ANALYSIS_DIR, 'customer_category_map.json'), 'w') as f:
        json.dump(customer_cat_map, f, indent=2)
    print(f"\n  Saved customer→category map for {len(customer_cat_map)} customers")

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"\nCategory Customer Counts:")
    for cat in TOP_CATEGORIES:
        count = cat_counts.get(cat, 0)
        if count > 0:
            print(f"  {cat:40s} {count:>6,} customers")

    print(f"\nGroup-Level Customer Counts:")
    for group in sorted(group_counts, key=group_counts.get, reverse=True):
        print(f"  {group:20s} {group_counts[group]:>6,} customers")

    # Top cross-sell pairs
    print(f"\nTop 20 Cross-Sell Pairs (group level):")
    group_pairs = [r for r in affinity_rows if r['level'] == 'group']
    for r in sorted(group_pairs, key=lambda x: -x['co_purchase_customers'])[:20]:
        print(f"  {r['category_a']:20s} <-> {r['category_b']:20s} | "
              f"{r['co_purchase_customers']:>5,} customers | "
              f"{r['a_to_b_rate']:>5.1f}% / {r['b_to_a_rate']:>5.1f}%")

    print(f"\nTop 20 Cross-Sell Pairs (subcategory level):")
    sub_pairs = [r for r in affinity_rows if r['level'] == 'subcategory']
    for r in sorted(sub_pairs, key=lambda x: -x['co_purchase_customers'])[:20]:
        print(f"  {r['category_a']:40s} <-> {r['category_b']:40s} | "
              f"{r['co_purchase_customers']:>5,} | "
              f"{r['a_to_b_rate']:>5.1f}% / {r['b_to_a_rate']:>5.1f}%")

    print(f"\n{'=' * 70}")
    print("OUTPUT FILES (all reusable across projects):")
    print(f"  analysis/cross_purchase_matrix.csv       — {len(affinity_rows)} affinity pairs")
    print(f"  analysis/upsell_recommendations.csv      — {len(recommendations)} recommendations")
    print(f"  analysis/customer_category_map.json      — {len(customer_cat_map)} customer profiles")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
