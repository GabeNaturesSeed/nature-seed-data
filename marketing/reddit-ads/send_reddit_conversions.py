#!/usr/bin/env python3
"""Send WooCommerce Purchase events to the Reddit Conversions API (CAPI).

Server-side companion to the browser Reddit Pixel. Pulls recent WooCommerce
orders (via the Cloudflare Worker proxy, same as the rest of the data hub),
builds Reddit "Purchase" conversion events, and POSTs them to Reddit.

Dedup: each event sets event_metadata.conversion_id = <WC order id> (Reddit
rejects a top-level event_id — verified 2026-07-23). Set the GTM/browser pixel's
Purchase `conversion_id` to the same WC order id so Reddit dedupes the browser
event against this server event. (See pixel-validation-checklist.md.)

Match signals sent per order (best-effort, more = better attribution):
  - email        SHA-256 of the lowercased/trimmed billing email (always)
  - click_id     Reddit rdt_cid, recovered from WC order attribution landing URL
  - ip_address   WC customer_ip_address
  - user_agent   WC customer_user_agent

SAFETY: defaults to test_mode=True. Test events appear in Reddit Events
Manager under "Test Events" and do NOT affect reporting/optimization.
Pass --live to send real events.

Usage:
    # dry run — print payloads, send nothing
    python marketing/reddit-ads/send_reddit_conversions.py --dry-run

    # send last 2h of orders as TEST events (safe; check Events Manager)
    python marketing/reddit-ads/send_reddit_conversions.py --hours 2

    # send one specific order as a TEST event
    python marketing/reddit-ads/send_reddit_conversions.py --order-id 471501

    # go live (real conversion events)
    python marketing/reddit-ads/send_reddit_conversions.py --hours 2 --live
"""
import argparse
import base64
import hashlib
import html
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))

REDDIT_CAPI_BASE = "https://ads-api.reddit.com/api/v2.0/conversions/events"
WC_STATUSES = ["completed", "processing"]
BATCH_SIZE = 100
RATE_SLEEP = 0.3


# ── config ───────────────────────────────────────────────────────────────
def load_env():
    env = {}
    with open(os.path.join(PROJECT_DIR, ".env")) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip().strip("'\"")
    return env


def pixel_id(env):
    """Reddit CAPI path segment = the PIXEL id (Events Manager, 'a2_' format),
    NOT the ad-account id. Posting to the account id ('t2_') returns 403
    (verified 2026-07-23). The pixel id is not in the token, so set it
    explicitly as REDDIT_PIXEL_ID; fall back to the token aid only if unset."""
    if env.get("REDDIT_PIXEL_ID"):
        return env["REDDIT_PIXEL_ID"]
    token = env["REDDIT_EVENTS_TOKEN"]
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)  # pad base64
        claims = json.loads(base64.urlsafe_b64decode(payload))
        aid = claims.get("aid") or claims.get("account_id")
        if not aid:
            raise ValueError("no aid claim in token")
        return aid
    except Exception as e:
        sys.exit(f"Could not resolve pixel id: {e}. Set REDDIT_PIXEL_ID in .env.")


# ── woocommerce ──────────────────────────────────────────────────────────
def wc_headers(env):
    ck, cs = env["WP_WOO_CONSUMER_KEY"], env["WP_WOO_CONSUMER_SECRET"]
    token = base64.b64encode(f"{ck}:{cs}".encode()).decode()
    return {"X-Proxy-Secret": env["CF_WORKER_SECRET"],
            "Authorization": f"Basic {token}"}


def fetch_orders(env, after_iso, before_iso, order_id=None):
    """Pull WC orders via the CF Worker proxy (paginated)."""
    url, headers, out = env["CF_WORKER_URL"], wc_headers(env), []
    if order_id:
        params = {"wc_path": f"/orders/{order_id}"}
        r = requests.get(url, headers=headers, params=params, timeout=60)
        r.raise_for_status()
        return [r.json()]
    for status in WC_STATUSES:
        page = 1
        while True:
            params = {"wc_path": "/orders", "status": status,
                      "after": after_iso, "before": before_iso,
                      "per_page": 100, "page": page}
            r = requests.get(url, headers=headers, params=params, timeout=60)
            if r.status_code != 200:
                print(f"  WC error {r.status_code}: {r.text[:200]}")
                break
            data = r.json()
            if not data:
                break
            out.extend(data)
            if len(data) < 100:
                break
            page += 1
            time.sleep(RATE_SLEEP)
        time.sleep(RATE_SLEEP)
    return out


# ── event building ───────────────────────────────────────────────────────
def sha256_email(email):
    if not email:
        return None
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


def reddit_click_id(order):
    """Recover the Reddit click id (rdt_cid) from the WC order-attribution
    landing URL — same mechanism used for gclid elsewhere in the repo."""
    meta = {m["key"]: m["value"] for m in order.get("meta_data", [])}
    entry = meta.get("_wc_order_attribution_session_entry", "")
    if not entry:
        return None
    try:
        qs = parse_qs(urlparse(entry).query)
        return qs.get("rdt_cid", [None])[0]
    except Exception:
        return None


def event_time(order):
    """RFC3339 UTC from the order's paid/created GMT timestamp."""
    ts = order.get("date_paid_gmt") or order.get("date_created_gmt")
    if not ts:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return ts if ts.endswith("Z") else ts + "Z"


def build_products(order):
    """content_ids must match the catalog `id` column (= WC variation id;
    falls back to product id for simple products)."""
    products = []
    for it in order.get("line_items", []):
        pid = it.get("variation_id") or it.get("product_id")
        if not pid:
            continue
        products.append({
            "id": str(pid),
            "name": html.unescape(it.get("name", "")),
            "category": "",  # optional; catalog google_product_category if desired
        })
    return products


def build_event(order):
    email_hash = sha256_email(order.get("billing", {}).get("email", ""))
    click_id = reddit_click_id(order)
    user = {}
    if email_hash:
        user["email"] = email_hash
    if click_id:
        user["click_id"] = click_id
    if order.get("customer_ip_address"):
        user["ip_address"] = order["customer_ip_address"]
    if order.get("customer_user_agent"):
        user["user_agent"] = order["customer_user_agent"]

    if not user:
        return None  # no attribution signal → Reddit would reject it

    line_items = order.get("line_items", [])
    return {
        "event_at": event_time(order),
        "event_type": {"tracking_type": "Purchase"},
        "user": user,
        "event_metadata": {
            "conversion_id": str(order["id"]),  # dedup key — mirror on the pixel
            "currency": order.get("currency", "USD"),
            "value_decimal": round(float(order.get("total", 0)), 2),
            "item_count": sum(int(i.get("quantity", 0)) for i in line_items),
            "products": build_products(order),
        },
    }


# ── send ─────────────────────────────────────────────────────────────────
def send_batch(env, account_id, events, test_mode):
    url = f"{REDDIT_CAPI_BASE}/{account_id}"
    headers = {"Authorization": f"Bearer {env['REDDIT_EVENTS_TOKEN']}",
               "Content-Type": "application/json"}
    body = {"test_mode": test_mode, "events": events}
    r = requests.post(url, headers=headers, json=body, timeout=60)
    ok = r.status_code in (200, 202)
    print(f"  Reddit {r.status_code} ({'TEST' if test_mode else 'LIVE'}) "
          f"{len(events)} event(s): {r.text[:300]}")
    return ok


def chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def main():
    ap = argparse.ArgumentParser(description="Send WC purchases to Reddit CAPI")
    ap.add_argument("--hours", type=float, default=2,
                    help="lookback window in hours (default 2)")
    ap.add_argument("--order-id", type=int, help="send a single order by id")
    ap.add_argument("--live", action="store_true",
                    help="send REAL events (default is test_mode)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print payloads, send nothing")
    args = ap.parse_args()

    env = load_env()
    account_id = pixel_id(env)
    test_mode = not args.live

    now = datetime.now(timezone.utc)
    after_iso = (now - timedelta(hours=args.hours)).strftime("%Y-%m-%dT%H:%M:%S")
    before_iso = now.strftime("%Y-%m-%dT%H:%M:%S")

    print(f"Reddit pixel: {account_id}  mode: "
          f"{'DRY-RUN' if args.dry_run else ('TEST' if test_mode else 'LIVE')}")
    orders = fetch_orders(env, after_iso, before_iso, order_id=args.order_id)
    print(f"Fetched {len(orders)} order(s)")

    events, skipped = [], 0
    for o in orders:
        ev = build_event(o)
        if ev is None:
            skipped += 1
            continue
        events.append(ev)

    if skipped:
        print(f"Skipped {skipped} order(s) with no usable attribution signal")
    if not events:
        print("No sendable events.")
        return

    if args.dry_run:
        print(json.dumps({"test_mode": test_mode, "events": events}, indent=2))
        return

    sent = 0
    for batch in chunk(events, BATCH_SIZE):
        if send_batch(env, account_id, batch, test_mode):
            sent += len(batch)
        time.sleep(RATE_SLEEP)
    print(f"Done. Sent {sent}/{len(events)} event(s).")


if __name__ == "__main__":
    main()
