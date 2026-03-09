#!/usr/bin/env python3
"""
Update WooCommerce Prices for Texas Collection Products
========================================================

Sets both regular_price and sale_price for all 21 Texas product variants
to match the correct pricing table (March 5, 2026).

Uses WooCommerce REST API v3 with Basic Auth.
Rate-limited at 0.3s between calls per CLAUDE.md rules.

Usage:
    python3 update_texas_prices_wc.py          # DRY RUN (default)
    python3 update_texas_prices_wc.py --live    # ACTUALLY UPDATE PRICES
"""

import requests
import time
import sys

# ============================================================
# CONFIG
# ============================================================
WC_BASE_URL = 'https://naturesseed.com/wp-json/wc/v3'
WC_CK = 'ck_9629579f1379f272169de8628edddb00b24737f9'
WC_CS = 'cs_bf6dcf206d6ed26b83e55e8af62c16de26339815'

DRY_RUN = '--live' not in sys.argv

# ============================================================
# PRICING TABLE
# From user's corrected pricing (March 5, 2026)
# regular_price = always set
# sale_price = set only for KIT variants (empty string to clear)
# ============================================================
UPDATES = [
    # --- Texas Bluebonnet Seeds (W-LUTE) — Product ID 462219 ---
    {'product_id': 462219, 'variation_id': 462924, 'sku': 'W-LUTE-0.25-LB',     'regular_price': '38.99',   'sale_price': ''},
    {'product_id': 462219, 'variation_id': 462925, 'sku': 'W-LUTE-0.5-LB-KIT',  'regular_price': '77.99',   'sale_price': '70.19'},
    {'product_id': 462219, 'variation_id': 462926, 'sku': 'W-LUTE-1-LB-KIT',    'regular_price': '154.99',  'sale_price': '131.74'},

    # --- Texas Native Wildflower Mix (WB-TEXN) — Product ID 462220 ---
    {'product_id': 462220, 'variation_id': 462885, 'sku': 'WB-TEXN-0.5-LB',     'regular_price': '32.99',   'sale_price': ''},
    {'product_id': 462220, 'variation_id': 462886, 'sku': 'WB-TEXN-1-LB-KIT',   'regular_price': '64.99',   'sale_price': '58.49'},
    {'product_id': 462220, 'variation_id': 462887, 'sku': 'WB-TEXN-5-LB-KIT',   'regular_price': '323.99',  'sale_price': '275.39'},

    # --- Texas Pollinator Wildflower Mix (WB-TXPB) — Product ID 462221 ---
    {'product_id': 462221, 'variation_id': 462888, 'sku': 'WB-TXPB-0.5-LB',     'regular_price': '33.99',   'sale_price': ''},
    {'product_id': 462221, 'variation_id': 462889, 'sku': 'WB-TXPB-1-LB-KIT',   'regular_price': '67.99',   'sale_price': '61.19'},
    {'product_id': 462221, 'variation_id': 462890, 'sku': 'WB-TXPB-5-LB-KIT',   'regular_price': '336.99',  'sale_price': '286.44'},

    # --- Texas Native Lawn Mix (TURF-TXN) — Product ID 462222 ---
    {'product_id': 462222, 'variation_id': 462891, 'sku': 'TURF-TXN-5-LB',      'regular_price': '164.99',  'sale_price': ''},
    {'product_id': 462222, 'variation_id': 462892, 'sku': 'TURF-TXN-10-LB-KIT', 'regular_price': '328.99',  'sale_price': '296.09'},
    {'product_id': 462222, 'variation_id': 462893, 'sku': 'TURF-TXN-25-LB-KIT', 'regular_price': '822.99',  'sale_price': '699.54'},

    # --- Texas Native Prairie Mix (PB-TXPR) — Product ID 462223 ---
    {'product_id': 462223, 'variation_id': 462894, 'sku': 'PB-TXPR-10-LB',      'regular_price': '214.99',  'sale_price': ''},
    {'product_id': 462223, 'variation_id': 462895, 'sku': 'PB-TXPR-20-LB-KIT',  'regular_price': '429.99',  'sale_price': '386.99'},
    {'product_id': 462223, 'variation_id': 462896, 'sku': 'PB-TXPR-50-LB-KIT',  'regular_price': '1073.99', 'sale_price': '912.89'},

    # --- Mexican Primrose / Pinkladies (W-OESP) — Product ID 462260 ---
    {'product_id': 462260, 'variation_id': 462897, 'sku': 'W-OESP-0.25-LB',     'regular_price': '13.99',   'sale_price': ''},
    {'product_id': 462260, 'variation_id': 462898, 'sku': 'W-OESP-0.5-LB-KIT',  'regular_price': '27.99',   'sale_price': '25.19'},
    {'product_id': 462260, 'variation_id': 462899, 'sku': 'W-OESP-1-LB-KIT',    'regular_price': '54.99',   'sale_price': '46.74'},

    # --- Drummond Phlox Seeds (W-PHDR) — Product ID 462264 ---
    {'product_id': 462264, 'variation_id': 462900, 'sku': 'W-PHDR-0.25-LB',     'regular_price': '10.99',   'sale_price': ''},
    {'product_id': 462264, 'variation_id': 462901, 'sku': 'W-PHDR-0.5-LB-KIT',  'regular_price': '20.99',   'sale_price': '18.89'},
    {'product_id': 462264, 'variation_id': 462902, 'sku': 'W-PHDR-1-LB-KIT',    'regular_price': '41.99',   'sale_price': '35.69'},
]


# ============================================================
# EXECUTION
# ============================================================

def get_current_price(product_id, variation_id):
    """Fetch current variation prices from WooCommerce."""
    url = f'{WC_BASE_URL}/products/{product_id}/variations/{variation_id}'
    resp = requests.get(url, auth=(WC_CK, WC_CS), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return {
        'regular_price': data.get('regular_price', ''),
        'sale_price': data.get('sale_price', ''),
        'price': data.get('price', ''),
        'sku': data.get('sku', ''),
    }


def update_variation_price(product_id, variation_id, regular_price, sale_price):
    """Update a single variation's prices."""
    url = f'{WC_BASE_URL}/products/{product_id}/variations/{variation_id}'
    payload = {
        'regular_price': regular_price,
        'sale_price': sale_price,
    }
    resp = requests.put(url, json=payload, auth=(WC_CK, WC_CS), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return {
        'regular_price': data.get('regular_price', ''),
        'sale_price': data.get('sale_price', ''),
        'price': data.get('price', ''),
    }


def main():
    mode = 'DRY RUN' if DRY_RUN else '🔴 LIVE UPDATE'
    print(f'\n{"="*70}')
    print(f'Texas Collection WooCommerce Price Update — {mode}')
    print(f'{"="*70}\n')

    if not DRY_RUN:
        print('⚠️  LIVE MODE — prices will be changed on production WooCommerce!')
        print('    Press Ctrl+C within 3 seconds to abort...')
        time.sleep(3)
        print('    Proceeding with live updates.\n')

    print(f'{"SKU":<25} {"Current":>12} {"→ Regular":>12} {"→ Sale":>12} {"→ Effective":>12} {"Status":<10}')
    print('-' * 90)

    success = 0
    errors = 0

    for item in UPDATES:
        sku = item['sku']
        pid = item['product_id']
        vid = item['variation_id']
        new_regular = item['regular_price']
        new_sale = item['sale_price']
        effective = new_sale if new_sale else new_regular

        try:
            # Fetch current price
            current = get_current_price(pid, vid)
            current_price = current['price']

            # Verify SKU matches
            if current['sku'] and current['sku'] != sku:
                print(f'{sku:<25} {"SKU MISMATCH: " + current["sku"]:>50} {"ERROR":<10}')
                errors += 1
                time.sleep(0.3)
                continue

            if DRY_RUN:
                status = 'DRY RUN'
                sale_display = new_sale if new_sale else '(none)'
                print(f'{sku:<25} ${current_price:>10} → ${new_regular:>10}  ${sale_display:>10}  ${effective:>10} {status:<10}')
            else:
                # Actually update
                result = update_variation_price(pid, vid, new_regular, new_sale)
                sale_display = new_sale if new_sale else '(none)'
                print(f'{sku:<25} ${current_price:>10} → ${new_regular:>10}  ${sale_display:>10}  ${effective:>10} {"✅ DONE":<10}')
                success += 1

            time.sleep(0.3)  # Rate limit

        except requests.exceptions.HTTPError as e:
            print(f'{sku:<25} {"HTTP " + str(e.response.status_code):>50} {"❌ ERROR":<10}')
            errors += 1
            time.sleep(0.3)
        except Exception as e:
            print(f'{sku:<25} {str(e)[:50]:>50} {"❌ ERROR":<10}')
            errors += 1
            time.sleep(0.3)

    print(f'\n{"="*70}')
    if DRY_RUN:
        print(f'DRY RUN COMPLETE — no changes made')
        print(f'Run with --live to apply these {len(UPDATES)} price updates')
    else:
        print(f'LIVE UPDATE COMPLETE: {success} updated, {errors} errors')
    print(f'{"="*70}\n')


if __name__ == '__main__':
    main()
