#!/usr/bin/env python3
"""
Nature's Seed — Uptime Checker
Runs every 30 minutes via GitHub Actions.
Checks key pages and writes results to Supabase website_health table.
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
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")

# ══════════════════════════════════════════════════════════════
# PAGES TO CHECK
# ══════════════════════════════════════════════════════════════

URLS = [
    "https://naturesseed.com/",
    "https://naturesseed.com/products/grass-seed/",
    "https://naturesseed.com/shop/",
    "https://naturesseed.com/product/bermuda-grass-seed/",
    "https://naturesseed.com/cart/",
    "https://naturesseed.com/checkout/",
    "https://naturesseed.com/my-account/",
]

# ══════════════════════════════════════════════════════════════
# CHECK LOGIC
# ══════════════════════════════════════════════════════════════

def check_url(url):
    """HEAD request with redirect follow, 10s timeout. Returns result dict."""
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
        resp = requests.head(url, allow_redirects=True, timeout=10)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        result["status_code"] = resp.status_code
        result["response_time_ms"] = elapsed_ms
        result["is_up"] = 200 <= resp.status_code <= 399
    except requests.exceptions.Timeout:
        result["error_message"] = "Timeout after 10s"
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
    resp.raise_for_status()
    print(f"  [OK] Inserted {len(results)} health check rows")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=== Nature's Seed Uptime Check ===")
    results = []
    for url in URLS:
        r = check_url(url)
        status = "UP" if r["is_up"] else "DOWN"
        ms = r["response_time_ms"] or "N/A"
        err = f" ({r['error_message']})" if r["error_message"] else ""
        print(f"  {status} {r['status_code'] or '---'} {ms}ms  {url}{err}")
        results.append(r)

    if SUPABASE_URL and SUPABASE_KEY:
        upsert_to_supabase(results)
    else:
        print("  [SKIP] No Supabase credentials — printing results only")
        print(json.dumps(results, indent=2))

    # Summary
    up_count = sum(1 for r in results if r["is_up"])
    print(f"\n  Result: {up_count}/{len(results)} pages UP")
    if up_count < len(results):
        down = [r["url"] for r in results if not r["is_up"]]
        print(f"  DOWN: {', '.join(down)}")
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
