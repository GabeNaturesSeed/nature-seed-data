#!/usr/bin/env python3
"""
Fishbowl Inventory API client for Nature's Seed.
Ported from sync_delivery_time.py.

Usage:
  from fishbowl_client import get_all_inventory
  inventory = get_all_inventory()  # {SKU: qty, ...}
"""

import urllib.request
import json
import os
from pathlib import Path

# Load .env
ENV_PATHS = [
    Path(__file__).resolve().parent.parent / ".env",
    Path("/Users/gabegimenes-silva/Desktop/ClaudeDataAgent - /.env"),
]

def _load_env():
    for p in ENV_PATHS:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    os.environ.setdefault(key, val)
            return

_load_env()

# ============================================================
# CONFIGURATION
# ============================================================

FB_URL = "http://naturesseed.myfishbowl.com:3875"
FB_USERNAME = "gabe"
FB_PASSWORD = "#Numb3rs!"
FB_APP_NAME = "Postman Testing"
FB_APP_ID = 101


# ============================================================
# API FUNCTIONS
# ============================================================

def fb_login():
    """Login to Fishbowl and return auth token."""
    payload = json.dumps({
        "appName": FB_APP_NAME,
        "appId": FB_APP_ID,
        "username": FB_USERNAME,
        "password": FB_PASSWORD,
    }).encode()

    req = urllib.request.Request(f"{FB_URL}/api/login", data=payload, method="POST")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        return data["token"]


def fb_query(token, sql):
    """Run a SQL query against Fishbowl, return list of row dicts."""
    req = urllib.request.Request(
        f"{FB_URL}/api/data-query",
        data=sql.encode(),
        method="GET",
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "text/plain")

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fb_logout(token):
    """Logout from Fishbowl."""
    try:
        req = urllib.request.Request(f"{FB_URL}/api/logout", method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


# ============================================================
# HIGH-LEVEL FUNCTIONS
# ============================================================

def get_all_inventory():
    """
    Query Fishbowl for ALL parts with their stock quantities.
    Returns dict: {SKU_UPPER: qty, ...} (includes 0-stock items).
    """
    token = fb_login()
    print("  Fishbowl: logged in")

    sql = (
        "SELECT p.num AS SKU, COALESCE(SUM(qoh.qty), 0) AS TotalQty "
        "FROM part p "
        "LEFT JOIN qtyonhand qoh ON qoh.partid = p.id "
        "GROUP BY p.num "
        "ORDER BY p.num;"
    )

    rows = fb_query(token, sql)
    fb_logout(token)
    print(f"  Fishbowl: {len(rows)} parts returned")

    inventory = {}
    for row in rows:
        sku = row.get("SKU", "")
        qty = row.get("TotalQty", 0)
        if sku:
            inventory[sku.upper()] = max(0, int(qty)) if qty else 0

    in_stock = sum(1 for q in inventory.values() if q > 0)
    print(f"  Fishbowl: {in_stock} in stock, {len(inventory) - in_stock} at zero")

    return inventory


def get_in_stock_skus():
    """Return set of uppercase SKUs that have stock > 0."""
    inventory = get_all_inventory()
    return {sku for sku, qty in inventory.items() if qty > 0}


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    print("Testing Fishbowl connection...")
    inventory = get_all_inventory()
    print(f"\nTotal parts: {len(inventory)}")

    in_stock = {k: v for k, v in inventory.items() if v > 0}
    print(f"In stock: {len(in_stock)}")

    # Show first 10
    print("\nSample (first 10 in-stock):")
    for sku in sorted(in_stock.keys())[:10]:
        print(f"  {sku}: {in_stock[sku]}")
