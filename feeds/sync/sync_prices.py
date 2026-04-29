#!/usr/bin/env python3
"""
Nature's Seed — Price + Inventory Sync (manual trigger)
Reads feed_master.json and pushes price + stock to Walmart and Amazon.
Content (titles, bullets, descriptions) is NEVER touched by this script.

Usage:
    python3 -m feeds.sync.sync_prices [--dry-run]
"""

import json
import sys
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

from feeds.env_loader import load_env

MASTER_PATH = Path(__file__).parent.parent / "feed_master.json"
LOG_PATH = Path(__file__).parent / f"{datetime.now(timezone.utc).date().isoformat()}-sync-log.json"

WM_BASE = "https://marketplace.walmartapis.com/v3"
LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
SP_BASE = "https://sellingpartnerapi-na.amazon.com"


def _get_walmart_token(env):
    resp = requests.post(
        "https://marketplace.walmartapis.com/v3/token",
        auth=(env["WALMART_CLIENT_ID"], env["WALMART_CLIENT_SECRET"]),
        data={"grant_type": "client_credentials"},
        headers={"WM_SVC.NAME": "Walmart Marketplace", "WM_QOS.CORRELATION_ID": "price-sync"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _get_amazon_token(env):
    resp = requests.post(LWA_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": env["AMAZON_REFRESH_TOKEN"],
        "client_id": env["AMAZON_CLIENT_ID"],
        "client_secret": env["AMAZON_CLIENT_SECRET"],
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def build_walmart_price_update(variation: dict) -> dict:
    return {
        "sku": variation["sku"],
        "pricing": {
            "currentPriceType": "BASE",
            "currentPrice": {"currency": "USD", "amount": float(variation["price"])},
        },
    }


def build_amazon_price_update(variation: dict, seller_id: str) -> dict:
    return {
        "sku": variation["sku"],
        "price": variation["price"],
        "currency": "USD",
    }


def push_walmart_prices(variations, env, dry_run=False):
    token = _get_walmart_token(env)
    headers = {
        "WM_SEC.ACCESS_TOKEN": token,
        "WM_SVC.NAME": "Walmart Marketplace",
        "WM_QOS.CORRELATION_ID": "price-sync",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    results = []
    for v in variations:
        if not v["sku"] or not v["price"]:
            continue
        payload = build_walmart_price_update(v)
        if dry_run:
            print(f"  [DRY] Walmart: {v['sku']} → ${v['price']}")
            results.append({"sku": v["sku"], "channel": "walmart", "status": "dry_run"})
            continue
        try:
            resp = requests.put(f"{WM_BASE}/price", headers=headers, json=payload, timeout=30)
            results.append({"sku": v["sku"], "channel": "walmart", "status": resp.status_code})
            print(f"  Walmart: {v['sku']} → ${v['price']} [{resp.status_code}]")
        except Exception as e:
            results.append({"sku": v["sku"], "channel": "walmart", "status": "error", "error": str(e)})
        time.sleep(0.5)
    return results


def push_amazon_prices(variations, env, dry_run=False):
    token = _get_amazon_token(env)
    seller_id = env["AMAZON_MERCHANT_TOKEN"]
    headers = {"x-amz-access-token": token, "Content-Type": "application/json"}
    results = []
    for v in variations:
        if not v["sku"] or not v["price"]:
            continue
        if dry_run:
            print(f"  [DRY] Amazon: {v['sku']} → ${v['price']}")
            results.append({"sku": v["sku"], "channel": "amazon", "status": "dry_run"})
            continue
        try:
            resp = requests.patch(
                f"{SP_BASE}/listings/2021-08-01/items/{seller_id}/{v['sku']}",
                headers=headers,
                json={"productType": "LAWN_AND_GARDEN", "patches": [
                    {"op": "replace", "path": "/attributes/purchasable_offer",
                     "value": [{"marketplace_id": "ATVPDKIKX0DER",
                                "our_price": [{"schedule": [{"value_with_tax": float(v["price"])}]}]}]}
                ]},
                timeout=30,
            )
            results.append({"sku": v["sku"], "channel": "amazon", "status": resp.status_code})
            print(f"  Amazon: {v['sku']} → ${v['price']} [{resp.status_code}]")
        except Exception as e:
            results.append({"sku": v["sku"], "channel": "amazon", "status": "error", "error": str(e)})
        time.sleep(0.5)
    return results


def sync_prices(dry_run=False):
    env = load_env()
    with open(MASTER_PATH) as f:
        master = json.load(f)

    # Collect all variation-level SKUs (variations carry the per-size price)
    all_variations = []
    for p in master["products"].values():
        if p["status"] != "publish":
            continue
        if p["variations"]:
            all_variations.extend(p["variations"])
        else:
            all_variations.append({"sku": p["sku"], "price": p["price"],
                                   "stock_quantity": p["stock_quantity"],
                                   "stock_status": p["stock_status"]})

    print(f"[SYNC] {len(all_variations)} SKUs to sync")
    results = []
    results.extend(push_walmart_prices(all_variations, env, dry_run))
    results.extend(push_amazon_prices(all_variations, env, dry_run))

    with open(LOG_PATH, "w") as f:
        json.dump({"synced_at": datetime.now(timezone.utc).isoformat(), "results": results}, f, indent=2)
    print(f"\n[DONE] Log: {LOG_PATH}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    sync_prices(dry_run=dry_run)
