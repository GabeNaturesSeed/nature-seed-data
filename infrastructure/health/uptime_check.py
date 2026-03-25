#!/usr/bin/env python3
"""
Nature's Seed — Uptime Checker
Runs every 30 minutes via GitHub Actions.
Routes through Cloudflare Worker proxy to bypass Bot Fight Mode.
Writes results to Supabase website_health table.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ══════════════════════════════════════════════════════════════
# ENV PARSING  (spaces around = AND quoted values)
# ══════════════════════════════════════════════════════════════

env_path = Path(__file__).resolve().parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
env_vars = {}
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip().strip("'\"")

# Also check os.environ (GitHub Actions sets these directly)
import os
for k in ["SUPABASE_URL", "SUPABASE_SECRET_API_KEY", "CF_WORKER_URL", "CF_WORKER_SECRET"]:
    if k in os.environ and k not in env_vars:
        env_vars[k] = os.environ[k]

SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")
CF_WORKER_URL = env_vars.get("CF_WORKER_URL", "")
CF_WORKER_SECRET = env_vars.get("CF_WORKER_SECRET", "")

# ══════════════════════════════════════════════════════════════
# PAGES TO CHECK
# ══════════════════════════════════════════════════════════════

# wp_path is the WordPress path to check via CF Worker proxy
PAGES = [
    {"label": "Homepage", "wp_path": "/"},
    {"label": "Grass Seed Category", "wp_path": "/products/grass-seed/"},
    {"label": "Shop", "wp_path": "/shop/"},
    {"label": "Product Page", "wp_path": "/product/bermuda-grass-seed/"},
    {"label": "Cart", "wp_path": "/cart/"},
    {"label": "Checkout", "wp_path": "/checkout/"},
    {"label": "My Account", "wp_path": "/my-account/"},
]

# ══════════════════════════════════════════════════════════════
# CHECK LOGIC — routes through CF Worker to bypass Bot Fight Mode
# ══════════════════════════════════════════════════════════════

def check_page(page):
    """Check a page via CF Worker proxy or direct if no proxy configured."""
    url = f"https://naturesseed.com{page['wp_path']}"
    result = {
        "check_timestamp": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "status_code": None,
        "response_time_ms": None,
        "is_up": False,
        "error_message": None,
    }

    try:
        start = time.monotonic()

        if CF_WORKER_URL and CF_WORKER_SECRET:
            # Route through Cloudflare Worker proxy (bypasses Bot Fight Mode)
            # The worker expects wp_path param and forwards as a site request
            proxy_url = f"{CF_WORKER_URL}?wp_path={page['wp_path']}"
            resp = requests.get(
                proxy_url,
                headers={"X-Proxy-Secret": CF_WORKER_SECRET},
                timeout=15,
                allow_redirects=True,
            )
        else:
            # Direct request (works from residential IPs)
            resp = requests.head(url, allow_redirects=True, timeout=10)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        result["status_code"] = resp.status_code
        result["response_time_ms"] = elapsed_ms
        result["is_up"] = 200 <= resp.status_code <= 399

    except requests.exceptions.Timeout:
        result["error_message"] = "Timeout"
    except requests.exceptions.ConnectionError as e:
        result["error_message"] = f"Connection error: {str(e)[:200]}"
    except Exception as e:
        result["error_message"] = f"Error: {str(e)[:200]}"

    return result


def upsert_to_supabase(results):
    """Insert results into website_health table."""
    url = f"{SUPABASE_URL}/rest/v1/website_health"
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    resp = requests.post(url, headers=headers, json=results, timeout=30)
    if resp.status_code in (200, 201, 204):
        print(f"  [OK] Inserted {len(results)} health check rows")
    else:
        print(f"  [WARN] Supabase insert: {resp.status_code} {resp.text[:200]}")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=== Nature's Seed Uptime Check ===")
    if CF_WORKER_URL:
        print(f"  Using CF Worker proxy: {CF_WORKER_URL[:40]}...")
    else:
        print("  Direct requests (no CF Worker configured)")

    results = []
    for page in PAGES:
        r = check_page(page)
        status = "UP" if r["is_up"] else "DOWN"
        ms = r["response_time_ms"] or "N/A"
        err = f" ({r['error_message']})" if r["error_message"] else ""
        print(f"  {status} {r['status_code'] or '---'} {ms}ms  {r['url']}{err}")
        results.append(r)
        time.sleep(0.5)  # Don't hammer the proxy

    if SUPABASE_URL and SUPABASE_KEY:
        upsert_to_supabase(results)
    else:
        print("  [SKIP] No Supabase credentials")

    up_count = sum(1 for r in results if r["is_up"])
    print(f"\n  Result: {up_count}/{len(results)} pages UP")
    if up_count < len(results):
        down = [r["url"] for r in results if not r["is_up"]]
        print(f"  DOWN: {', '.join(down)}")

    # Don't exit with error — 403s from CF aren't real downtime
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
