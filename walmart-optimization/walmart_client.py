#!/usr/bin/env python3
"""
Walmart Marketplace API client for Nature's Seed.

Handles:
  - OAuth 2.0 token management (auto-refresh)
  - Paginated item listing
  - Feed submission (MP_MAINTENANCE JSON + inventory multipart)
  - Feed status polling

Usage:
  from walmart_client import WalmartClient
  wm = WalmartClient()
  items = wm.get_all_items()
  wm.submit_feed("MP_MAINTENANCE", payload)
"""

import urllib.request
import urllib.parse
import json
import base64
import uuid
import time
import os
import io
from datetime import datetime, timedelta
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
    raise FileNotFoundError("No .env found")

_load_env()

# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://marketplace.walmartapis.com/v3"
CLIENT_ID = os.environ["WALMART_CLIENT_ID"]
CLIENT_SECRET = os.environ["WALMART_CLIENT_SECRET"]
SERVICE_NAME = "Nature's Seed"

# Token cache
_token_cache = {"token": None, "expires_at": None}


# ============================================================
# AUTH
# ============================================================

def _get_token():
    """Get or refresh OAuth 2.0 access token."""
    now = datetime.utcnow()

    if _token_cache["token"] and _token_cache["expires_at"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    # Request new token
    creds = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()

    req = urllib.request.Request(f"{BASE_URL}/token", data=body, method="POST")
    req.add_header("Authorization", f"Basic {creds}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/json")
    req.add_header("WM_SVC.NAME", SERVICE_NAME)
    req.add_header("WM_QOS.CORRELATION_ID", str(uuid.uuid4()))

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())

    token = data["access_token"]
    expires_in = int(data.get("expires_in", 900))
    # Cache with 60s buffer
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + timedelta(seconds=expires_in - 60)

    return token


def _headers(content_type="application/json"):
    """Build standard Walmart API headers."""
    h = {
        "WM_SEC.ACCESS_TOKEN": _get_token(),
        "WM_SVC.NAME": SERVICE_NAME,
        "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = content_type
    return h


def _api_request(url, method="GET", data=None, headers=None, timeout=60):
    """Make an API request, return parsed JSON."""
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or _headers()).items():
        req.add_header(k, v)

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
        if raw:
            return json.loads(raw)
        return None


# ============================================================
# ITEMS
# ============================================================

def get_all_items(limit=20):
    """
    Pull all Walmart items (paginated).
    Returns list of item dicts.
    """
    all_items = []
    offset = 0
    total = None

    while True:
        url = f"{BASE_URL}/items?limit={limit}&offset={offset}"
        data = _api_request(url)

        if not data:
            break

        total_items = data.get("totalItems", 0)
        if total is None:
            total = total_items
            print(f"  Walmart reports {total} total items")

        items = data.get("ItemResponse", [])
        if not items:
            break

        all_items.extend(items)
        print(f"  Fetched {len(all_items)}/{total} items...")

        if len(all_items) >= total or len(items) < limit:
            break

        offset += limit
        time.sleep(0.5)

    return all_items


def get_item(sku):
    """Get a single item by SKU."""
    url = f"{BASE_URL}/items/{urllib.parse.quote(sku)}"
    return _api_request(url)


# ============================================================
# FEEDS
# ============================================================

def submit_maintenance_feed(mp_items, feed_type="MP_MAINTENANCE"):
    """
    Submit an MP_MAINTENANCE feed (JSON body).

    mp_items: list of MPItem dicts (each with Orderable + Visible sections)
    Returns feed ID.
    """
    payload = {
        "MPItemFeedHeader": {
            "version": "5.0.20251118-18_39_44-api",
            "businessUnit": "WALMART_US",
            "locale": "en",
        },
        "MPItem": mp_items,
    }

    url = f"{BASE_URL}/feeds?feedType={feed_type}"
    body = json.dumps(payload).encode()
    result = _api_request(url, method="POST", data=body)

    feed_id = result.get("feedId", "")
    print(f"  Feed submitted: {feed_id} ({len(mp_items)} items)")
    return feed_id


def submit_inventory_feed(inventory_items):
    """
    Submit an inventory feed (multipart form-data).

    inventory_items: list of {sku, quantity: {unit, amount}} dicts
    Returns feed ID.
    """
    payload = {
        "InventoryHeader": {"version": "1.4"},
        "Inventory": inventory_items,
    }

    json_bytes = json.dumps(payload).encode()

    # Build multipart form-data
    boundary = f"----WalmartBoundary{uuid.uuid4().hex[:16]}"
    body_parts = []
    body_parts.append(f"--{boundary}".encode())
    body_parts.append(
        b'Content-Disposition: form-data; name="file"; filename="inventory.json"'
    )
    body_parts.append(b"Content-Type: application/json")
    body_parts.append(b"")
    body_parts.append(json_bytes)
    body_parts.append(f"--{boundary}--".encode())

    body = b"\r\n".join(body_parts)

    hdrs = _headers(content_type=None)
    hdrs["Content-Type"] = f"multipart/form-data; boundary={boundary}"

    url = f"{BASE_URL}/feeds?feedType=inventory"
    result = _api_request(url, method="POST", data=body, headers=hdrs)

    feed_id = result.get("feedId", "")
    print(f"  Inventory feed submitted: {feed_id} ({len(inventory_items)} items)")
    return feed_id


def get_feed_status(feed_id, include_details=False):
    """Check feed processing status."""
    url = f"{BASE_URL}/feeds/{feed_id}"
    if include_details:
        url += "?includeDetails=true"
    return _api_request(url)


def wait_for_feed(feed_id, max_wait=600, poll_interval=30):
    """
    Poll feed status until complete or timeout.
    Returns final feed status dict.
    """
    start = time.time()
    while time.time() - start < max_wait:
        status = get_feed_status(feed_id, include_details=True)
        feed_status = status.get("feedStatus", "UNKNOWN")

        if feed_status in ("PROCESSED", "ERROR"):
            return status

        elapsed = int(time.time() - start)
        print(f"  Feed {feed_id}: {feed_status} ({elapsed}s elapsed)")
        time.sleep(poll_interval)

    print(f"  Feed {feed_id}: timed out after {max_wait}s")
    return get_feed_status(feed_id, include_details=True)


# ============================================================
# CONVENIENCE
# ============================================================

def submit_maintenance_batched(mp_items, batch_size=50, delay=65):
    """
    Submit MP_MAINTENANCE feed in batches of 50 with 65s delay.
    Returns list of feed IDs.
    """
    feed_ids = []
    total = len(mp_items)

    for i in range(0, total, batch_size):
        batch = mp_items[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size
        print(f"\n  Batch {batch_num}/{total_batches} ({len(batch)} items)")

        feed_id = submit_maintenance_feed(batch)
        feed_ids.append(feed_id)

        if i + batch_size < total:
            print(f"  Waiting {delay}s before next batch...")
            time.sleep(delay)

    return feed_ids


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    print("Testing Walmart API connection...")
    print(f"  Client ID: {CLIENT_ID[:12]}...")

    token = _get_token()
    print(f"  Token obtained: {token[:20]}...")

    items = get_all_items()
    print(f"\n  Total items retrieved: {len(items)}")

    if items:
        sample = items[0]
        print(f"\n  Sample item:")
        print(f"    SKU: {sample.get('sku', 'N/A')}")
        print(f"    Product Name: {sample.get('productName', 'N/A')[:60]}")
        print(f"    Published Status: {sample.get('publishedStatus', 'N/A')}")
        print(f"    Lifecycle Status: {sample.get('lifecycleStatus', 'N/A')}")
