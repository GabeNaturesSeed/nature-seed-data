#!/usr/bin/env python3
"""
Two-task WooCommerce update script:
  Task A: Update price_discount_2 meta from "10% Bulk Discount" -> "10% Off - MOST PICKED"
  Task B: Set upsell_ids on all products based on SKU-prefix cross-sell map
"""

import requests
import base64
import time
import html
import os
import sys

# ── Parse .env ──────────────────────────────────────────────────────────────
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
env = {}
with open(ENV_PATH) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        env[key] = val

# WooCommerce credentials — support both naming conventions
WC_CK = env.get("WC_CONSUMER_KEY") or env.get("WC_CK", "")
WC_CS = env.get("WC_CONSUMER_SECRET") or env.get("WC_CS", "")
WC_BASE = (env.get("WC_STORE_URL") or env.get("WC_BASE_URL", "https://naturesseed.com")).rstrip("/")
# Strip /wp-json/wc/v3 suffix if already present in env
if WC_BASE.endswith("/wp-json/wc/v3"):
    WC_BASE = WC_BASE[: -len("/wp-json/wc/v3")]

CF_WORKER_URL = env.get("CF_WORKER_URL", "").strip()
CF_WORKER_SECRET = env.get("CF_WORKER_SECRET", "").strip()

# For local execution, always use direct WC API — residential IPs don't trigger
# Bot Fight Mode. CF Worker proxy is only needed from datacenter IPs (GitHub Actions).
# Also, the CF Worker is read-only (GET only), so writes must always be direct.
CF_WORKER_URL = ""  # force direct for local dev

print(f"WC base: {WC_BASE}")
print(f"CF Worker: disabled (local dev — direct API calls)")
print()


# ── API helper ───────────────────────────────────────────────────────────────
# NOTE: The CF Worker only supports GET requests (bypasses Bot Fight Mode for
# datacenter IPs like GitHub Actions). Local dev uses direct WC API calls since
# residential IPs don't trigger Bot Fight Mode. Write operations (PUT/POST/DELETE)
# always go direct regardless, since the Worker is read-only.
def api(method, path, body=None, params_extra=None, retries=3):
    params = {"_": int(time.time())}
    if params_extra:
        params.update(params_extra)

    # Use CF Worker proxy only for GET requests when proxy is configured
    use_proxy = CF_WORKER_URL and method.lower() == "get"

    if use_proxy:
        url = CF_WORKER_URL
        params["wc_path"] = f"/wp-json/wc/v3/{path}"
        creds = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        headers = {
            "Authorization": f"Basic {creds}",
            "X-Proxy-Secret": CF_WORKER_SECRET,
            "Content-Type": "application/json",
        }
    else:
        url = f"{WC_BASE}/wp-json/wc/v3/{path}"
        params["consumer_key"] = WC_CK
        params["consumer_secret"] = WC_CS
        headers = {"Content-Type": "application/json"}

    for attempt in range(1, retries + 1):
        try:
            resp = getattr(requests, method)(
                url, json=body, params=params, headers=headers, timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if attempt == retries:
                raise
            print(f"    [retry {attempt}/{retries}] HTTP {e.response.status_code}: {e}")
            time.sleep(2)
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                raise
            print(f"    [retry {attempt}/{retries}] Request error: {e}")
            time.sleep(2)


# ── Fetch all published products (paginated) ─────────────────────────────────
def fetch_all_products():
    all_products = []
    page = 1
    while True:
        print(f"  Fetching products page {page}...", end="", flush=True)
        batch = api("get", "products", params_extra={
            "per_page": "100",
            "status": "publish",
            "page": str(page),
        })
        if not batch:
            print(" (empty, done)")
            break
        print(f" {len(batch)} products")
        all_products.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        time.sleep(0.3)
    return all_products


# ── SKU lookup: fetch a product by SKU ──────────────────────────────────────
def fetch_product_by_sku(sku):
    results = api("get", "products", params_extra={"sku": sku, "per_page": "5"})
    if results:
        return results[0]
    return None


# ════════════════════════════════════════════════════════════════════════════
# TASK A — Update price_discount_2
# ════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("TASK A — Update price_discount_2")
print("=" * 70)

OLD_VALUE_FRAGMENTS = ["10% bulk discount", "10% bulk"]  # case-insensitive match
NEW_VALUE = "10% Off - MOST PICKED"

print("\nFetching all published products...")
all_products = fetch_all_products()
print(f"\nTotal products fetched: {len(all_products)}")

task_a_updated = []
task_a_errors = []

for product in all_products:
    pid = product["id"]
    pname = html.unescape(product.get("name", ""))
    meta_data = product.get("meta_data", [])

    # Find price_discount_2 in meta_data
    for meta in meta_data:
        if meta.get("key") == "price_discount_2":
            current_val = str(meta.get("value", "")).strip()
            if any(frag in current_val.lower() for frag in OLD_VALUE_FRAGMENTS):
                print(f"  [{pid}] {pname}")
                print(f"         price_discount_2: '{current_val}' -> '{NEW_VALUE}'")
                try:
                    api("put", f"products/{pid}", {
                        "meta_data": [
                            {"id": meta["id"], "key": "price_discount_2", "value": NEW_VALUE}
                        ]
                    })
                    task_a_updated.append({"id": pid, "name": pname, "old": current_val})
                    print(f"         -> UPDATED")
                except Exception as e:
                    print(f"         -> ERROR: {e}")
                    task_a_errors.append({"id": pid, "name": pname, "error": str(e)})
                time.sleep(0.3)
            break

print(f"\nTask A complete: {len(task_a_updated)} updated, {len(task_a_errors)} errors")


# ════════════════════════════════════════════════════════════════════════════
# TASK B — Upsell Products Audit and Update
# ════════════════════════════════════════════════════════════════════════════
print("\n")
print("=" * 70)
print("TASK B — Upsell Products Audit and Update")
print("=" * 70)

# ── Step 1: Print a sample of 20 products showing current upsell state ──────
print("\n--- Sample audit: first 20 products upsell state ---")
for product in all_products[:20]:
    pid = product["id"]
    pname = html.unescape(product.get("name", ""))
    sku = product.get("sku", "")
    upsell_ids = product.get("upsell_ids", [])
    upsell_meta = [
        f"{m['key']}={m['value']}"
        for m in product.get("meta_data", [])
        if "upsell" in m.get("key", "").lower()
    ]
    print(f"  [{pid}] SKU={sku:<25} upsell_ids={upsell_ids}  meta_upsell={upsell_meta}")

# ── Step 2: Define cross-sell map (SKU prefix -> companion SKUs) ─────────────
# Rules are evaluated in order; first matching prefix wins.
CROSS_SELL_RULES = [
    # More-specific rules first
    ("TURF-CLV",   ["S-INNOC-5-LB", "S-MICRO-1-LB"]),
    ("PB-HRSE-",   ["PB-CHSS-1-LB-KIT"]),
    ("PB-CLV",     ["S-INNOC-5-LB"]),
    ("PB-",        ["S-INNOC-5-LB"]),
    ("TURF-",      ["S-MICRO-1-LB", "S-DUTCH-5-LB", "SUSTANE-4-6-4"]),
    ("WB-",        ["WB-AN-0.5-LB", "W-LUBI-0.25-LB", "W-LUMI-0.25-LB"]),
    ("W-",         ["WB-AN-0.5-LB", "WB-DR-0.5-LB"]),
    ("CV-",        ["S-INNOC-5-LB"]),
    ("S-DUTCH",    ["S-INNOC-5-LB", "TURF-CLV-5-LB"]),
    ("S-MICRO",    ["S-INNOC-5-LB", "TURF-CLV-5-LB"]),
    ("S-INNOC",    ["S-DUTCH-5-LB", "S-MICRO-1-LB", "PB-CLV-10-LB"]),
    ("SUSTANE-",   ["TURF-W-TALL-5-LB", "TURF-W-BLUE-5-LB"]),
    ("S-RICE",     ["S-TACKI-50-LB", "TURF-W-TALL-5-LB"]),
    ("PG-",        ["S-INNOC-5-LB", "WB-AN-0.5-LB"]),
]

def get_upsell_skus_for_sku(sku):
    """Return list of companion SKUs for a product SKU, or None if no rule matches."""
    sku_upper = sku.upper()
    for prefix, companions in CROSS_SELL_RULES:
        if sku_upper.startswith(prefix.upper()):
            return companions
    return None

# ── Step 3: Build SKU -> product_id lookup for all companion SKUs ────────────
all_companion_skus = set()
for _, companions in CROSS_SELL_RULES:
    for sku in companions:
        all_companion_skus.add(sku)

print(f"\n--- Building companion SKU lookup ({len(all_companion_skus)} unique SKUs) ---")
sku_to_id = {}

# First check if any are already in our product list (saves API calls)
for product in all_products:
    psku = product.get("sku", "").upper()
    if psku in {s.upper() for s in all_companion_skus}:
        # Find the original-case SKU
        for companion_sku in all_companion_skus:
            if companion_sku.upper() == psku:
                sku_to_id[companion_sku] = product["id"]
                break

# Fetch any remaining companion SKUs not already found
missing_companions = [s for s in all_companion_skus if s not in sku_to_id]
if missing_companions:
    print(f"  Need to fetch {len(missing_companions)} companion SKUs from API...")
    for companion_sku in missing_companions:
        try:
            p = fetch_product_by_sku(companion_sku)
            if p:
                sku_to_id[companion_sku] = p["id"]
                print(f"  Found: {companion_sku} -> ID {p['id']} ({html.unescape(p.get('name',''))})")
            else:
                print(f"  NOT FOUND: {companion_sku}")
            time.sleep(0.3)
        except Exception as e:
            print(f"  ERROR fetching {companion_sku}: {e}")

print(f"\n  Companion SKU lookup complete: {len(sku_to_id)}/{len(all_companion_skus)} found")
print(f"  Missing companions: {[s for s in all_companion_skus if s not in sku_to_id]}")

# ── Step 4: Apply upsell_ids to all products ─────────────────────────────────
print("\n--- Applying upsell_ids ---")

task_b_updated = []
task_b_skipped_no_match = []
task_b_skipped_no_companions = []
task_b_errors = []

for product in all_products:
    pid = product["id"]
    pname = html.unescape(product.get("name", ""))
    sku = product.get("sku", "").strip()

    if not sku:
        task_b_skipped_no_match.append({"id": pid, "name": pname, "reason": "no SKU"})
        continue

    companion_skus = get_upsell_skus_for_sku(sku)
    if companion_skus is None:
        task_b_skipped_no_match.append({"id": pid, "name": pname, "sku": sku, "reason": "no prefix match"})
        continue

    # Resolve companion SKUs to IDs (skip any not found)
    companion_ids = []
    missing = []
    for csku in companion_skus:
        if csku in sku_to_id:
            cid = sku_to_id[csku]
            if cid != pid:  # don't upsell to self
                companion_ids.append(cid)
        else:
            missing.append(csku)

    if not companion_ids:
        task_b_skipped_no_companions.append({
            "id": pid, "name": pname, "sku": sku,
            "wanted": companion_skus, "missing": missing
        })
        continue

    # Check if already set correctly
    current_upsells = sorted(product.get("upsell_ids", []))
    desired_upsells = sorted(companion_ids)

    if current_upsells == desired_upsells:
        print(f"  [{pid}] {sku} — already correct {desired_upsells}, skipping")
        continue

    print(f"  [{pid}] {sku:<30} upsell_ids: {current_upsells} -> {desired_upsells}")
    if missing:
        print(f"         (companion SKUs not found, skipped: {missing})")

    try:
        api("put", f"products/{pid}", {"upsell_ids": companion_ids})
        task_b_updated.append({
            "id": pid, "name": pname, "sku": sku,
            "upsell_ids": companion_ids, "companion_skus": companion_skus
        })
        print(f"         -> UPDATED")
    except Exception as e:
        print(f"         -> ERROR: {e}")
        task_b_errors.append({"id": pid, "name": pname, "sku": sku, "error": str(e)})
    time.sleep(0.3)


# ════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════════════════════════
print("\n")
print("=" * 70)
print("FINAL SUMMARY")
print("=" * 70)

print(f"\n[TASK A] price_discount_2 Updates")
print(f"  Updated:  {len(task_a_updated)}")
for p in task_a_updated:
    print(f"    [{p['id']}] {p['name']} | '{p['old']}' -> '{NEW_VALUE}'")
if task_a_errors:
    print(f"  Errors:   {len(task_a_errors)}")
    for p in task_a_errors:
        print(f"    [{p['id']}] {p['name']} | {p['error']}")

print(f"\n[TASK B] Upsell IDs Updates")
print(f"  Updated:               {len(task_b_updated)}")
print(f"  Skipped (no SKU match):{len(task_b_skipped_no_match)}")
print(f"  Skipped (no companion IDs found): {len(task_b_skipped_no_companions)}")
print(f"  Errors:                {len(task_b_errors)}")

if task_b_updated:
    print(f"\n  Products updated:")
    for p in task_b_updated:
        print(f"    [{p['id']}] {p['sku']:<30} {p['name']}")
        print(f"           companions: {p['companion_skus']}")

if task_b_skipped_no_companions:
    print(f"\n  Skipped — companion SKUs not in catalog:")
    for p in task_b_skipped_no_companions:
        print(f"    [{p['id']}] {p['sku']:<30} wanted={p['wanted']} missing={p['missing']}")

if task_b_errors:
    print(f"\n  Errors:")
    for p in task_b_errors:
        print(f"    [{p['id']}] {p['sku']:<30} {p['error']}")

print(f"\nDone.")
