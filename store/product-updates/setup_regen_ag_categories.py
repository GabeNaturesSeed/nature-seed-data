#!/usr/bin/env python3
"""
Create Regenerative Agriculture WC category tree and assign products.
Run once. Safe to re-run — checks for existing categories before creating.
"""
import requests, base64, time, json
from pathlib import Path

env_vars = {}
with open(Path(__file__).resolve().parent.parent.parent / ".env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

WC_BASE = env_vars.get("WC_BASE_URL", "https://naturesseed.com/wp-json/wc/v3")
WC_CK = env_vars["WC_CK"]
WC_CS = env_vars["WC_CS"]
CF_WORKER_URL = env_vars.get("CF_WORKER_URL", "")
CF_WORKER_SECRET = env_vars.get("CF_WORKER_SECRET", "")

def wc_get(path, params=None):
    params = params or {}
    if CF_WORKER_URL and CF_WORKER_SECRET:
        p = dict(params); p["wc_path"] = path
        auth = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        resp = requests.get(CF_WORKER_URL, params=p,
            headers={"X-Proxy-Secret": CF_WORKER_SECRET, "Authorization": f"Basic {auth}"}, timeout=30)
    else:
        resp = requests.get(f"{WC_BASE}{path}", auth=(WC_CK, WC_CS), params=params, timeout=30)
    resp.raise_for_status(); return resp.json()

def wc_post(path, payload):
    if CF_WORKER_URL and CF_WORKER_SECRET:
        auth = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        resp = requests.post(CF_WORKER_URL, params={"wc_path": path, "wc_method": "POST"},
            headers={"X-Proxy-Secret": CF_WORKER_SECRET, "Authorization": f"Basic {auth}",
                     "Content-Type": "application/json"}, json=payload, timeout=30)
    else:
        resp = requests.post(f"{WC_BASE}{path}", auth=(WC_CK, WC_CS), json=payload, timeout=30)
    return resp

def wc_put(path, payload):
    if CF_WORKER_URL and CF_WORKER_SECRET:
        auth = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        resp = requests.post(CF_WORKER_URL, params={"wc_path": path, "wc_method": "PUT"},
            headers={"X-Proxy-Secret": CF_WORKER_SECRET, "Authorization": f"Basic {auth}",
                     "Content-Type": "application/json"}, json=payload, timeout=30)
    else:
        resp = requests.put(f"{WC_BASE}{path}", auth=(WC_CK, WC_CS), json=payload, timeout=30)
    return resp

PARENT_CAT = {"name": "Regenerative Agriculture", "slug": "regenerative-ag",
              "description": "Seeds, soil tools, and knowledge for regenerative land management."}

SUBCATEGORIES = [
    {"name": "Build Soil",            "slug": "regen-build-soil"},
    {"name": "Reduce Inputs",         "slug": "regen-reduce-inputs"},
    {"name": "Feed Livestock Better", "slug": "regen-feed-livestock"},
    {"name": "Support Pollinators",   "slug": "regen-support-pollinators"},
    {"name": "Sequester Carbon",      "slug": "regen-sequester-carbon"},
]

PRODUCT_CATEGORIES = {
    "S-INNOC":           ["regen-build-soil"],
    "BDL-SBC":           ["regen-build-soil"],
    "PG-TRIN":           ["regen-build-soil", "regen-support-pollinators"],
    "S-DUTCH":           ["regen-build-soil", "regen-support-pollinators"],
    "PB-MUST":           ["regen-build-soil"],
    "PG-BUCK":           ["regen-build-soil"],
    "PG-SECE":           ["regen-build-soil"],
    "SUSTANE-4-6-4":     ["regen-build-soil"],
    "PG-TRRE":           ["regen-build-soil", "regen-support-pollinators"],
    "BDL-WSC":           ["regen-reduce-inputs"],
    "S-MICRO":           ["regen-reduce-inputs"],
    "SUSTANE-18-1-8+FE": ["regen-reduce-inputs"],
    "PG-BUDA":           ["regen-reduce-inputs", "regen-sequester-carbon"],
    "PG-BOGR":           ["regen-reduce-inputs", "regen-sequester-carbon"],
    "PG-PAVI":           ["regen-reduce-inputs", "regen-sequester-carbon"],
    "TURF-CLV":          ["regen-reduce-inputs"],
    "BDL-TPF":           ["regen-feed-livestock"],
    "PG-MESA":           ["regen-feed-livestock", "regen-sequester-carbon"],
    "PG-TRPR":           ["regen-feed-livestock"],
    "PB-COW-NTR":        ["regen-feed-livestock"],
    "PB-COW-SO":         ["regen-feed-livestock"],
    "PB-HRSE-N":         ["regen-feed-livestock"],
    "PB-HRSE-SO":        ["regen-feed-livestock"],
    "PB-HRSE-TR":        ["regen-feed-livestock"],
    "PB-SHEP-N":         ["regen-feed-livestock"],
    "PB-SHEP-SO":        ["regen-feed-livestock"],
    "PB-SHEP-TR":        ["regen-feed-livestock"],
    "PB-GOAT-TR":        ["regen-feed-livestock"],
    "PG-DAGL":           ["regen-feed-livestock"],
    "PB-HONEY":          ["regen-support-pollinators"],
    "BDL-POL":           ["regen-support-pollinators"],
    "WB-AN":             ["regen-support-pollinators"],
    "WB-RM":             ["regen-support-pollinators"],
    "WB-SD":             ["regen-support-pollinators"],
    "PB-SGPR":           ["regen-sequester-carbon"],
    "CV-BGEC":           ["regen-sequester-carbon"],
    "PB-PLPR":           ["regen-sequester-carbon"],
    "PB-TXPR":           ["regen-sequester-carbon"],
}

print("Fetching existing categories...")
existing = []
page = 1
while True:
    batch = wc_get("/products/categories", {"per_page": 100, "page": page, "hide_empty": False})
    existing.extend(batch)
    if len(batch) < 100:
        break
    page += 1
    time.sleep(0.3)
existing_by_slug = {c["slug"]: c for c in existing}

if "regenerative-ag" in existing_by_slug:
    parent_id = existing_by_slug["regenerative-ag"]["id"]
    print(f"  Parent exists: ID {parent_id}")
else:
    resp = wc_post("/products/categories", PARENT_CAT)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create parent category: {resp.status_code} {resp.text[:200]}")
    parent_id = resp.json()["id"]
    print(f"  Created parent: ID {parent_id}")
time.sleep(0.3)

subcat_slug_to_id = {}
for subcat in SUBCATEGORIES:
    if subcat["slug"] in existing_by_slug:
        subcat_slug_to_id[subcat["slug"]] = existing_by_slug[subcat["slug"]]["id"]
        print(f"  Subcat exists: {subcat['slug']} → ID {subcat_slug_to_id[subcat['slug']]}")
    else:
        payload = {**subcat, "parent": parent_id}
        resp = wc_post("/products/categories", payload)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to create subcategory {subcat['slug']}: {resp.status_code} {resp.text[:200]}")
        subcat_slug_to_id[subcat["slug"]] = resp.json()["id"]
        print(f"  Created subcat: {subcat['slug']} → ID {subcat_slug_to_id[subcat['slug']]}")
    time.sleep(0.3)

print("\nAssigning products to categories...")
results = {"success": [], "not_found": [], "error": []}

for sku, cat_slugs in PRODUCT_CATEGORIES.items():
    search = wc_get("/products", {"sku": sku, "per_page": 1})
    if not search:
        print(f"  NOT FOUND: {sku}")
        results["not_found"].append(sku)
        time.sleep(0.3)
        continue

    product = search[0]
    product_id = product["id"]
    existing_cat_ids = [c["id"] for c in product.get("categories", [])]
    new_cat_ids = [parent_id] + [subcat_slug_to_id[s] for s in cat_slugs]
    merged = list(set(existing_cat_ids + new_cat_ids))
    cat_payload = [{"id": cid} for cid in merged]

    resp = wc_put(f"/products/{product_id}", {"categories": cat_payload})
    if resp.status_code in (200, 201):
        print(f"  OK: {sku} ({product_id}) → {cat_slugs}")
        results["success"].append(sku)
    else:
        print(f"  ERROR: {sku} — {resp.status_code} {resp.text[:100]}")
        results["error"].append(sku)
    time.sleep(0.3)

print(f"\nDone. Success: {len(results['success'])} | Not found: {len(results['not_found'])} | Errors: {len(results['error'])}")
if results["not_found"]:
    print(f"Not found SKUs: {results['not_found']}")
if results["error"]:
    print(f"Error SKUs: {results['error']}")

with open(Path(__file__).parent / "regen_ag_category_setup.json", "w") as f:
    json.dump({"parent_id": parent_id, "subcategories": subcat_slug_to_id, "results": results}, f, indent=2)
print("Summary saved to regen_ag_category_setup.json")
