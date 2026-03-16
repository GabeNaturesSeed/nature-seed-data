#!/usr/bin/env python3
"""Analyze SKU patterns and build replacement mapping."""

import json
import csv
import os
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
ANALYSIS_DIR = os.path.join(os.path.dirname(__file__), 'analysis')
os.makedirs(ANALYSIS_DIR, exist_ok=True)

class HTMLTextExtractor(HTMLParser):
    """Strip HTML tags and extract text."""
    def __init__(self):
        super().__init__()
        self.result = []
    def handle_data(self, d):
        self.result.append(d)
    def get_text(self):
        return ' '.join(self.result)

def strip_html(html):
    if not html:
        return ''
    extractor = HTMLTextExtractor()
    extractor.feed(html)
    return extractor.get_text().strip()

def load_json(filename):
    with open(os.path.join(DATA_DIR, filename)) as f:
        return json.load(f)

def get_product_content_2(product):
    """Extract the ACF 'Product Content 2' field from meta_data."""
    for m in product.get('meta_data', []):
        if m.get('key') in ('product_content_2', '_product_content_2', 'Product Content 2'):
            return m.get('value', '')
    return ''

def main():
    active = load_json('products_active.json')
    inactive = load_json('products_inactive.json')
    q1_orders = load_json('orders_q1_2025.json')
    q2_orders = load_json('orders_q2_2025.json')

    # --- Build product lookup maps ---
    active_by_sku = {}
    active_by_id = {}
    active_by_name_lower = {}
    for p in active:
        if p['sku']:
            active_by_sku[p['sku']] = p
        active_by_id[p['id']] = p
        active_by_name_lower[p['name'].lower().strip()] = p

    inactive_by_sku = {}
    inactive_by_id = {}
    for p in inactive:
        if p['sku']:
            inactive_by_sku[p['sku']] = p
        inactive_by_id[p['id']] = p

    all_products_by_id = {**active_by_id, **inactive_by_id}

    # --- Analyze order SKUs ---
    print("=" * 70)
    print("SKU ANALYSIS")
    print("=" * 70)

    # Collect all ordered SKUs with their product names and counts
    ordered_items = defaultdict(lambda: {'count': 0, 'revenue': 0.0, 'names': set(), 'product_ids': set(), 'emails': set()})

    for order in q1_orders + q2_orders:
        for li in order['line_items']:
            sku = li.get('sku', '') or ''
            name = li.get('name', '') or ''
            pid = li.get('product_id')
            email = order.get('customer_email', '')
            total = float(li.get('total', 0) or 0)

            key = sku if sku else f"ID:{pid}"
            ordered_items[key]['count'] += li.get('quantity', 1) or 1
            ordered_items[key]['revenue'] += total
            ordered_items[key]['names'].add(name)
            if pid:
                ordered_items[key]['product_ids'].add(pid)
            if email:
                ordered_items[key]['emails'].add(email)

    print(f"\nTotal unique SKUs/IDs ordered: {len(ordered_items)}")

    # Sample active SKUs
    print(f"\n--- ACTIVE PRODUCT SKU SAMPLES (first 20) ---")
    for sku in sorted(active_by_sku.keys())[:20]:
        p = active_by_sku[sku]
        print(f"  {sku:30s} -> {p['name'][:50]}")

    # Sample order SKUs (top by revenue)
    print(f"\n--- TOP 30 ORDERED SKUs BY REVENUE ---")
    top_ordered = sorted(ordered_items.items(), key=lambda x: x[1]['revenue'], reverse=True)[:30]
    for sku, info in top_ordered:
        names = list(info['names'])[:2]
        in_active = "ACTIVE" if sku in active_by_sku else "PHASED"
        print(f"  {sku:30s} | {info['count']:5d} units | ${info['revenue']:10.2f} | {in_active} | {names[0][:45]}")

    # --- Match by product_id instead of SKU ---
    print(f"\n--- MATCHING BY PRODUCT ID ---")
    matched_by_id = 0
    matched_by_name = 0
    for sku, info in ordered_items.items():
        for pid in info['product_ids']:
            if pid in active_by_id:
                matched_by_id += 1
                break
        for name in info['names']:
            if name.lower().strip() in active_by_name_lower:
                matched_by_name += 1
                break
    print(f"  Matched by product ID: {matched_by_id}")
    print(f"  Matched by exact name: {matched_by_name}")

    # --- Categorize all ordered items ---
    print(f"\n--- CATEGORIZATION ---")

    categories = {
        'ACTIVE': [],
        'PHASED_OUT': [],
        'UNKNOWN': [],
    }

    for sku, info in ordered_items.items():
        # Check if active by SKU
        if sku in active_by_sku:
            categories['ACTIVE'].append((sku, info, active_by_sku[sku]))
            continue

        # Check if active by product ID
        found_active = False
        for pid in info['product_ids']:
            if pid in active_by_id:
                categories['ACTIVE'].append((sku, info, active_by_id[pid]))
                found_active = True
                break
        if found_active:
            continue

        # Check if known inactive product
        found_inactive = False
        if sku in inactive_by_sku:
            found_inactive = True
        else:
            for pid in info['product_ids']:
                if pid in inactive_by_id:
                    found_inactive = True
                    break

        if found_inactive:
            categories['PHASED_OUT'].append((sku, info, None))
        else:
            # Could be from variation, or old product no longer in system
            categories['PHASED_OUT'].append((sku, info, None))

    print(f"  ACTIVE:     {len(categories['ACTIVE'])} items")
    print(f"  PHASED_OUT: {len(categories['PHASED_OUT'])} items")

    # --- Active SKUs detail ---
    print(f"\n--- ACTIVE PRODUCTS (still selling) ---")
    active_items = sorted(categories['ACTIVE'], key=lambda x: x[1]['revenue'], reverse=True)
    for sku, info, prod in active_items[:20]:
        print(f"  {sku:30s} | ${info['revenue']:8.2f} | {len(info['emails']):4d} customers | {prod['name'][:45]}")

    # --- Build replacement candidates ---
    print(f"\n\n{'='*70}")
    print("BUILDING REPLACEMENT MAP")
    print("="*70)

    # Group active products by category for matching
    active_by_category = defaultdict(list)
    for p in active:
        for cat in p.get('categories', []):
            active_by_category[cat['name'].lower()].append(p)

    # Extract species keywords from product names for matching
    def extract_keywords(name):
        """Extract meaningful keywords from a product name."""
        name = name.lower()
        # Remove common words
        stopwords = {'seed', 'mix', 'blend', 'lb', 'lbs', 'kit', 'pure', 'premium', 'certified', 'for', 'the', 'and', 'or', 'a', 'an', 'in', '-', 'to'}
        words = re.findall(r'[a-z]+', name)
        return set(w for w in words if w not in stopwords and len(w) > 2)

    def match_score(old_name, old_cats, new_product):
        """Score how well a new product matches an old one."""
        score = 0
        old_kw = extract_keywords(old_name)
        new_kw = extract_keywords(new_product['name'])
        new_cats_lower = set(c['name'].lower() for c in new_product.get('categories', []))

        # Keyword overlap
        overlap = old_kw & new_kw
        score += len(overlap) * 10

        # Category match
        old_cats_lower = set(c.lower() for c in old_cats)
        cat_overlap = old_cats_lower & new_cats_lower
        score += len(cat_overlap) * 20

        # Special matching patterns
        patterns = {
            'horse': ['horse', 'equine'],
            'cow': ['cattle', 'cow', 'bovine'],
            'goat': ['goat', 'caprine'],
            'sheep': ['sheep', 'ovine'],
            'pig': ['pig', 'swine', 'hog'],
            'chicken': ['chicken', 'poultry', 'chix'],
            'pasture': ['pasture', 'grazing', 'forage'],
            'lawn': ['lawn', 'turf', 'grass'],
            'wildflower': ['wildflower', 'flower', 'native'],
            'clover': ['clover', 'dutch', 'crimson'],
            'bermuda': ['bermuda', 'berm'],
            'fescue': ['fescue'],
            'ryegrass': ['ryegrass', 'rye'],
            'bluegrass': ['bluegrass', 'blue'],
            'buffalo': ['buffalo', 'buffalograss'],
            'timothy': ['timothy'],
            'orchard': ['orchard'],
            'deer': ['deer'],
            'shade': ['shade'],
            'drought': ['drought', 'dry', 'dryland'],
            'northern': ['northern', 'cool', 'north'],
            'southern': ['southern', 'warm', 'south'],
            'california': ['california', 'cal'],
            'conservation': ['conservation', 'cover', 'erosion'],
            'food plot': ['food plot', 'game', 'wildlife'],
            'tackifier': ['tackifier', 'tack'],
            'inoculant': ['inoculant', 'innoculant'],
        }

        for concept, terms in patterns.items():
            old_has = any(t in old_name.lower() for t in terms)
            new_has = any(t in new_product['name'].lower() for t in terms)
            if old_has and new_has:
                score += 30

        return score

    # For each phased out item, find best replacement
    replacement_map = []
    no_replacement = []

    phased_items = sorted(categories['PHASED_OUT'], key=lambda x: x[1]['revenue'], reverse=True)

    for sku, info, _ in phased_items:
        names = list(info['names'])
        old_name = names[0] if names else sku

        # Get old product categories
        old_cats = []
        old_product = None
        if sku in inactive_by_sku:
            old_product = inactive_by_sku[sku]
            old_cats = [c['name'] for c in old_product.get('categories', [])]
        else:
            for pid in info['product_ids']:
                if pid in all_products_by_id:
                    old_product = all_products_by_id[pid]
                    old_cats = [c['name'] for c in old_product.get('categories', [])]
                    break

        # Score all active products
        scores = []
        for p in active:
            s = match_score(old_name, old_cats, p)
            if s > 0:
                scores.append((s, p))

        scores.sort(key=lambda x: x[0], reverse=True)

        if scores and scores[0][0] >= 20:
            best = scores[0][1]
            replacement_map.append({
                'old_sku': sku,
                'old_name': old_name,
                'old_categories': ', '.join(old_cats),
                'old_revenue_q1q2': round(info['revenue'], 2),
                'old_customer_count': len(info['emails']),
                'old_units_sold': info['count'],
                'new_sku': best['sku'],
                'new_name': best['name'],
                'new_categories': ', '.join(c['name'] for c in best.get('categories', [])),
                'new_permalink': best.get('permalink', ''),
                'new_price': best.get('price', ''),
                'new_image': best['images'][0]['src'] if best.get('images') else '',
                'match_score': scores[0][0],
                'replacement_notes': '',
            })
        else:
            no_replacement.append({
                'old_sku': sku,
                'old_name': old_name,
                'old_categories': ', '.join(old_cats),
                'old_revenue_q1q2': round(info['revenue'], 2),
                'old_customer_count': len(info['emails']),
                'old_units_sold': info['count'],
            })

    # --- Write CSVs ---
    # SKU comparison
    sku_rows = []
    for sku, info, prod in categories['ACTIVE']:
        sku_rows.append({
            'sku': sku,
            'name': list(info['names'])[0] if info['names'] else '',
            'status': 'ACTIVE',
            'revenue_q1q2': round(info['revenue'], 2),
            'customer_count': len(info['emails']),
            'units_sold': info['count'],
        })
    for sku, info, _ in categories['PHASED_OUT']:
        names = list(info['names'])
        sku_rows.append({
            'sku': sku,
            'name': names[0] if names else '',
            'status': 'PHASED_OUT',
            'revenue_q1q2': round(info['revenue'], 2),
            'customer_count': len(info['emails']),
            'units_sold': info['count'],
        })

    sku_rows.sort(key=lambda x: x['revenue_q1q2'], reverse=True)

    with open(os.path.join(ANALYSIS_DIR, 'sku_comparison.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['sku', 'name', 'status', 'revenue_q1q2', 'customer_count', 'units_sold'])
        w.writeheader()
        w.writerows(sku_rows)

    # Replacement map
    replacement_map.sort(key=lambda x: x['old_revenue_q1q2'], reverse=True)
    with open(os.path.join(ANALYSIS_DIR, 'replacement_map.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(replacement_map[0].keys()) if replacement_map else [])
        w.writeheader()
        w.writerows(replacement_map)

    # No replacement
    no_replacement.sort(key=lambda x: x['old_revenue_q1q2'], reverse=True)
    with open(os.path.join(ANALYSIS_DIR, 'no_replacement.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(no_replacement[0].keys()) if no_replacement else [])
        w.writeheader()
        w.writerows(no_replacement)

    # --- Summary ---
    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print("="*70)
    print(f"Total unique ordered items:      {len(ordered_items)}")
    print(f"  Still ACTIVE:                  {len(categories['ACTIVE'])}")
    print(f"  PHASED OUT with replacement:   {len(replacement_map)}")
    print(f"  PHASED OUT no replacement:     {len(no_replacement)}")

    active_rev = sum(info['revenue'] for _, info, _ in categories['ACTIVE'])
    replaced_rev = sum(r['old_revenue_q1q2'] for r in replacement_map)
    no_rep_rev = sum(r['old_revenue_q1q2'] for r in no_replacement)

    print(f"\n  Active revenue (Q1+Q2):        ${active_rev:,.2f}")
    print(f"  Replaced revenue (Q1+Q2):      ${replaced_rev:,.2f}")
    print(f"  No-replacement revenue (Q1+Q2): ${no_rep_rev:,.2f}")

    active_emails = set()
    for _, info, _ in categories['ACTIVE']:
        active_emails |= info['emails']
    replaced_emails = set()
    for r in replacement_map:
        sku = r['old_sku']
        replaced_emails |= ordered_items[sku]['emails']
    no_rep_emails = set()
    for r in no_replacement:
        sku = r['old_sku']
        no_rep_emails |= ordered_items[sku]['emails']

    print(f"\n  Unique customers (ACTIVE):      {len(active_emails)}")
    print(f"  Unique customers (REPLACED):    {len(replaced_emails)}")
    print(f"  Unique customers (NO REPLACE):  {len(no_rep_emails)}")
    print(f"  Total unique customers:         {len(active_emails | replaced_emails | no_rep_emails)}")

    # Top 15 replacements by revenue
    print(f"\n--- TOP 15 REPLACEMENTS (by old revenue) ---")
    for r in replacement_map[:15]:
        print(f"  [{r['match_score']:3d}] {r['old_name'][:40]:42s} -> {r['new_name'][:40]:42s} | ${r['old_revenue_q1q2']:8.2f} | {r['old_customer_count']} customers")

    # Top 15 no-replacement by revenue
    print(f"\n--- TOP 15 NO REPLACEMENT (by old revenue) ---")
    for r in no_replacement[:15]:
        print(f"  {r['old_name'][:55]:57s} | ${r['old_revenue_q1q2']:8.2f} | {r['old_customer_count']} customers")

    # Files saved
    print(f"\n--- FILES SAVED ---")
    print(f"  {ANALYSIS_DIR}/sku_comparison.csv    ({len(sku_rows)} rows)")
    print(f"  {ANALYSIS_DIR}/replacement_map.csv   ({len(replacement_map)} rows)")
    print(f"  {ANALYSIS_DIR}/no_replacement.csv    ({len(no_replacement)} rows)")

if __name__ == '__main__':
    main()
