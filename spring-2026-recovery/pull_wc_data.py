#!/usr/bin/env python3
"""Pull all WooCommerce products (active + inactive) and Q1/Q2 2025 orders."""

import requests
import json
import time
import os

WC_BASE = 'https://naturesseed.com/wp-json/wc/v3'
WC_AUTH = (
    'ck_9629579f1379f272169de8628edddb00b24737f9',
    'cs_bf6dcf206d6ed26b83e55e8af62c16de26339815'
)
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def wc_get_all(endpoint, params=None):
    """Paginate through all WC API results."""
    params = params or {}
    params['per_page'] = 100
    page = 1
    all_items = []
    while True:
        params['page'] = page
        print(f"  Fetching {endpoint} page {page}...")
        r = requests.get(f"{WC_BASE}/{endpoint}", auth=WC_AUTH, params=params)
        r.raise_for_status()
        items = r.json()
        if not items:
            break
        all_items.extend(items)
        print(f"    Got {len(items)} items (total: {len(all_items)})")
        page += 1
        time.sleep(0.3)
    return all_items

def extract_product_fields(product):
    """Extract relevant fields from a WC product."""
    return {
        'id': product.get('id'),
        'sku': product.get('sku', ''),
        'name': product.get('name', ''),
        'slug': product.get('slug', ''),
        'status': product.get('status', ''),
        'type': product.get('type', ''),
        'permalink': product.get('permalink', ''),
        'price': product.get('price', ''),
        'regular_price': product.get('regular_price', ''),
        'sale_price': product.get('sale_price', ''),
        'description': product.get('description', ''),
        'short_description': product.get('short_description', ''),
        'categories': [{'id': c['id'], 'name': c['name'], 'slug': c['slug']} for c in product.get('categories', [])],
        'tags': [{'id': t['id'], 'name': t['name']} for t in product.get('tags', [])],
        'images': [{'id': img['id'], 'src': img['src'], 'alt': img.get('alt', '')} for img in product.get('images', [])],
        'attributes': product.get('attributes', []),
        'variations': product.get('variations', []),
        'meta_data': product.get('meta_data', []),
        'manage_stock': product.get('manage_stock'),
        'stock_quantity': product.get('stock_quantity'),
        'weight': product.get('weight', ''),
        'date_created': product.get('date_created', ''),
        'date_modified': product.get('date_modified', ''),
    }

def extract_order_fields(order):
    """Extract relevant fields from a WC order."""
    billing = order.get('billing', {})
    return {
        'id': order.get('id'),
        'number': order.get('number'),
        'status': order.get('status'),
        'date_created': order.get('date_created'),
        'total': order.get('total'),
        'customer_id': order.get('customer_id'),
        'customer_email': billing.get('email', ''),
        'customer_first_name': billing.get('first_name', ''),
        'customer_last_name': billing.get('last_name', ''),
        'line_items': [{
            'product_id': li.get('product_id'),
            'variation_id': li.get('variation_id'),
            'name': li.get('name', ''),
            'sku': li.get('sku', ''),
            'quantity': li.get('quantity'),
            'subtotal': li.get('subtotal', ''),
            'total': li.get('total', ''),
            'price': li.get('price'),
        } for li in order.get('line_items', [])],
    }

def main():
    # --- PRODUCTS ---
    print("=" * 60)
    print("PULLING ACTIVE PRODUCTS (status=publish)")
    print("=" * 60)
    active_raw = wc_get_all('products', {'status': 'publish'})
    active = [extract_product_fields(p) for p in active_raw]
    with open(os.path.join(DATA_DIR, 'products_active.json'), 'w') as f:
        json.dump(active, f, indent=2)
    print(f"\nSaved {len(active)} active products\n")

    print("=" * 60)
    print("PULLING DRAFT PRODUCTS")
    print("=" * 60)
    draft_raw = wc_get_all('products', {'status': 'draft'})

    print("\n" + "=" * 60)
    print("PULLING PRIVATE PRODUCTS")
    print("=" * 60)
    private_raw = wc_get_all('products', {'status': 'private'})

    print("\n" + "=" * 60)
    print("PULLING PENDING PRODUCTS")
    print("=" * 60)
    pending_raw = wc_get_all('products', {'status': 'pending'})

    inactive_raw = draft_raw + private_raw + pending_raw
    inactive = [extract_product_fields(p) for p in inactive_raw]
    with open(os.path.join(DATA_DIR, 'products_inactive.json'), 'w') as f:
        json.dump(inactive, f, indent=2)
    print(f"\nSaved {len(inactive)} inactive products (draft={len(draft_raw)}, private={len(private_raw)}, pending={len(pending_raw)})\n")

    # --- CATEGORIES ---
    print("=" * 60)
    print("PULLING CATEGORIES")
    print("=" * 60)
    cats = wc_get_all('products/categories')
    with open(os.path.join(DATA_DIR, 'categories.json'), 'w') as f:
        json.dump(cats, f, indent=2)
    print(f"\nSaved {len(cats)} categories\n")

    # --- Q1 2025 ORDERS ---
    print("=" * 60)
    print("PULLING Q1 2025 ORDERS (Jan-Mar, completed)")
    print("=" * 60)
    q1_raw = wc_get_all('orders', {
        'after': '2025-01-01T00:00:00',
        'before': '2025-03-31T23:59:59',
        'status': 'completed',
    })
    q1 = [extract_order_fields(o) for o in q1_raw]
    with open(os.path.join(DATA_DIR, 'orders_q1_2025.json'), 'w') as f:
        json.dump(q1, f, indent=2)
    print(f"\nSaved {len(q1)} Q1 2025 orders\n")

    # --- Q2 2025 ORDERS ---
    print("=" * 60)
    print("PULLING Q2 2025 ORDERS (Apr-Jun, completed)")
    print("=" * 60)
    q2_raw = wc_get_all('orders', {
        'after': '2025-04-01T00:00:00',
        'before': '2025-06-30T23:59:59',
        'status': 'completed',
    })
    q2 = [extract_order_fields(o) for o in q2_raw]
    with open(os.path.join(DATA_DIR, 'orders_q2_2025.json'), 'w') as f:
        json.dump(q2, f, indent=2)
    print(f"\nSaved {len(q2)} Q2 2025 orders\n")

    # --- SUMMARY ---
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Active products:   {len(active)}")
    print(f"Inactive products: {len(inactive)}")
    print(f"Categories:        {len(cats)}")
    print(f"Q1 2025 orders:    {len(q1)}")
    print(f"Q2 2025 orders:    {len(q2)}")

    # Quick stats
    q1_skus = set()
    q2_skus = set()
    for o in q1:
        for li in o['line_items']:
            if li['sku']:
                q1_skus.add(li['sku'])
    for o in q2:
        for li in o['line_items']:
            if li['sku']:
                q2_skus.add(li['sku'])
    active_skus = set(p['sku'] for p in active if p['sku'])

    print(f"\nUnique SKUs in Q1 orders: {len(q1_skus)}")
    print(f"Unique SKUs in Q2 orders: {len(q2_skus)}")
    print(f"Active product SKUs:      {len(active_skus)}")
    print(f"Q1 SKUs still active:     {len(q1_skus & active_skus)}")
    print(f"Q1 SKUs phased out:       {len(q1_skus - active_skus)}")
    print(f"Q2 SKUs still active:     {len(q2_skus & active_skus)}")
    print(f"Q2 SKUs phased out:       {len(q2_skus - active_skus)}")

if __name__ == '__main__':
    main()
