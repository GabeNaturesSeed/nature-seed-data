#!/usr/bin/env python3
"""
SKU matching logic for cross-referencing Walmart SKUs against Fishbowl inventory.
Ported from sync_delivery_time.py with additions for Walmart weight-variant patterns.

Matching rules (in order):
  1. Direct match (exact SKU)
  2. Prefix match: Walmart "PB-ALPACA-10-LB" → Fishbowl "PB-ALPACA-10-LB"
  3. Weight-variant: Walmart "PB-ALPACA-10-LB-KIT" → Fishbowl "PB-ALPACA-10-LB"
  4. Base prefix: Walmart "PB-ALPACA-10-LB-KIT" → any Fishbowl "PB-ALPACA-*"
  5. KIT base: "PG-CYDA-25-LB-KIT" → strip KIT+weight → check "PG-CYDA-*"
"""

import re


def match_sku(walmart_sku, fb_inventory):
    """
    Match a single Walmart SKU to Fishbowl inventory.

    Args:
        walmart_sku: The Walmart SKU string
        fb_inventory: dict {SKU_UPPER: qty} from fishbowl_client

    Returns:
        (qty, match_type, matched_sku)
        - qty: stock quantity (0 if no match)
        - match_type: "direct", "prefix", "kit", "no_match"
        - matched_sku: the Fishbowl SKU that matched (or None)
    """
    wm = walmart_sku.upper().strip()

    # 1. Direct match
    if wm in fb_inventory:
        return fb_inventory[wm], "direct", wm

    # 2. Strip -KIT suffix and try direct
    if wm.endswith("-KIT"):
        without_kit = wm[:-4]
        if without_kit in fb_inventory:
            return fb_inventory[without_kit], "kit_direct", without_kit

    # 3. Prefix match: look for FB SKUs that start with this Walmart SKU
    for fb_sku, qty in fb_inventory.items():
        if fb_sku.startswith(wm + "-"):
            return qty, "prefix", fb_sku

    # 4. KIT base match: strip -KIT and weight, check base
    if wm.endswith("-KIT"):
        base = re.sub(r"-KIT$", "", wm)
        base = re.sub(r"-[\d.]+-(?:LB|OZ)$", "", base)
        best_qty = 0
        best_sku = None
        for fb_sku, qty in fb_inventory.items():
            if fb_sku.startswith(base + "-") and not fb_sku.endswith("-KIT"):
                if qty > best_qty:
                    best_qty = qty
                    best_sku = fb_sku
        if best_sku:
            return best_qty, "kit_base", best_sku

    # 5. Broader base match (strip weight from non-KIT SKUs too)
    base = re.sub(r"-[\d.]+-(?:LB|OZ)(?:-KIT)?$", "", wm)
    if base != wm:
        best_qty = 0
        best_sku = None
        for fb_sku, qty in fb_inventory.items():
            if fb_sku.startswith(base + "-") and not fb_sku.endswith("-KIT"):
                if qty > best_qty:
                    best_qty = qty
                    best_sku = fb_sku
        if best_sku:
            return best_qty, "base_prefix", best_sku

    return 0, "no_match", None


def match_all(walmart_skus, fb_inventory):
    """
    Match a list of Walmart SKUs against Fishbowl inventory.

    Args:
        walmart_skus: list of SKU strings
        fb_inventory: dict {SKU_UPPER: qty}

    Returns:
        list of dicts: [{sku, qty, match_type, matched_sku}, ...]
    """
    results = []
    for sku in walmart_skus:
        qty, match_type, matched_sku = match_sku(sku, fb_inventory)
        results.append({
            "sku": sku,
            "qty": qty,
            "match_type": match_type,
            "matched_sku": matched_sku,
        })
    return results


def get_base_sku(sku):
    """
    Extract base SKU from a weight-variant SKU.
    e.g., "PB-ALPACA-10-LB-KIT" → "PB-ALPACA"
          "PB-ALPACA-10-LB"     → "PB-ALPACA"
          "WB-RM-0.5-LB"       → "WB-RM"
    """
    s = sku.upper().strip()
    s = re.sub(r"-KIT$", "", s)
    s = re.sub(r"-[\d.]+-(?:LB|OZ)$", "", s)
    return s


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    # Test with some known patterns
    test_inventory = {
        "PB-ALPACA-10-LB": 50,
        "PB-ALPACA-25-LB": 30,
        "PG-CYDA-10-LB": 20,
        "S-DUTCH-5-LB": 100,
        "WB-RM-0.5-LB": 15,
    }

    test_skus = [
        "PB-ALPACA-10-LB-KIT",    # should match via kit_direct
        "PB-ALPACA-25-LB-KIT",    # should match via kit_direct
        "PG-CYDA-25-LB-KIT",      # should match via kit_base
        "S-DUTCH-5-LB",           # direct match
        "WB-RM-0.5-LB",          # direct match
        "NONEXISTENT-SKU",        # no match
    ]

    print("SKU matching test:")
    for sku in test_skus:
        qty, mtype, matched = match_sku(sku, test_inventory)
        print(f"  {sku:30s} → qty={qty:4d}  type={mtype:12s}  matched={matched}")

    print(f"\nBase SKU extraction:")
    for sku in test_skus:
        print(f"  {sku:30s} → {get_base_sku(sku)}")
