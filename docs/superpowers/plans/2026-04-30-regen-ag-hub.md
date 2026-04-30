# Regenerative Agriculture Hub — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `/products/regenerative-agriculture/` editorial hub page that educates homesteaders on regen ag by outcome, surfaces curated products per section, and hosts 12 blog article cards as the SEO play.

**Architecture:** Custom PHP page template (`page-regenerative-agriculture.php`) following the same pattern as `page-shipping-and-returns-policy.php`. Products are fetched by SKU via `wc_get_product_id_by_sku()`. A background WC category tree (`regenerative-ag` + 5 subcategories) handles product assignment and SEO. Filter tab interactivity is inline JS (~25 lines) in the template — no separate JS file needed. SCSS is a new `_regenerative-agriculture.scss` page file compiled via existing Vite 6 build.

**Tech Stack:** PHP 8, WooCommerce `wc_get_product()` / `wc_get_product_id_by_sku()`, BEM SCSS, Vite 6, Python 3 + requests (WC REST API for category setup), Permalink Manager plugin (manual WP Admin step)

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| CREATE | `store/product-updates/setup_regen_ag_categories.py` | API script: create WC categories + assign products |
| CREATE | `/Users/gabegimenes-silva/Local Sites/natures-seed/app/public/wp-content/themes/GSNature V1.03a/page-regenerative-agriculture.php` | Page template — full hub layout |
| CREATE | `/Users/gabegimenes-silva/Local Sites/natures-seed/app/public/wp-content/themes/GSNature V1.03a/assets/scss/pages/_regenerative-agriculture.scss` | All BEM styles for this page |
| MODIFY | `/Users/gabegimenes-silva/Local Sites/natures-seed/app/public/wp-content/themes/GSNature V1.03a/assets/scss/main.scss` | Add `@use 'pages/regenerative-agriculture';` after line 50 |

**Confirmed from Task 1 inspection:**
- Theme path: `/Users/gabegimenes-silva/Local Sites/natures-seed/app/public/wp-content/themes/GSNature V1.03a/`
- Product card template uses `global $product` — set global before calling `gsnature_template_part()`
- SCSS import syntax: `@use 'pages/regenerative-agriculture';`
- Vite build: run from theme root with `npx vite build`

---

## Task 1: Inspect Product Card Template

Before writing the hub template, confirm what variables the shared product card expects.

**Files:**
- Read: `app/public/wp-content/themes/GSNature/template-parts/components/product-card.php`

- [ ] **Step 1: Read the product card template**

```bash
cat app/public/wp-content/themes/GSNature/template-parts/components/product-card.php
```

Look for which variables are expected at the top (e.g., `$product`, `$args`, `$atts`). Note the variable name used — you will pass it this way in Task 3.

- [ ] **Step 2: Find the SCSS entry file**

```bash
find app/public/wp-content/themes/GSNature/assets/scss -name "main.scss" -o -name "style.scss" -o -name "app.scss" | head -5
```

Open whichever file exists and find the line that imports `_shipping-policy.scss` or the pages directory. Note the exact import syntax used — you will mirror it in Task 5.

- [ ] **Step 3: Note findings**

Record:
- Product card variable name (e.g., `$product`)
- SCSS entry file path
- SCSS import syntax used for existing page files

No commit needed — this is a read-only task.

---

## Task 2: Create WC Categories + Assign Products via API

**Files:**
- Create: `store/product-updates/setup_regen_ag_categories.py`

- [ ] **Step 1: Write the category setup script**

```python
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

def wc_get(path, params={}):
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

# ── Category definitions ──────────────────────────────────────────────────────
PARENT_CAT = {"name": "Regenerative Agriculture", "slug": "regenerative-ag",
              "description": "Seeds, soil tools, and knowledge for regenerative land management."}

SUBCATEGORIES = [
    {"name": "Build Soil",           "slug": "regen-build-soil"},
    {"name": "Reduce Inputs",        "slug": "regen-reduce-inputs"},
    {"name": "Feed Livestock Better","slug": "regen-feed-livestock"},
    {"name": "Support Pollinators",  "slug": "regen-support-pollinators"},
    {"name": "Sequester Carbon",     "slug": "regen-sequester-carbon"},
]

# ── Product → subcategory mapping ────────────────────────────────────────────
# Format: SKU → [subcategory slugs]
PRODUCT_CATEGORIES = {
    # Build Soil
    "S-INNOC":    ["regen-build-soil"],
    "BDL-SBC":    ["regen-build-soil"],
    "PG-TRIN":    ["regen-build-soil", "regen-support-pollinators"],
    "S-DUTCH":    ["regen-build-soil", "regen-support-pollinators"],
    "PB-MUST":    ["regen-build-soil"],
    "PG-BUCK":    ["regen-build-soil"],
    "PG-SECE":    ["regen-build-soil"],
    "SUSTANE-4-6-4": ["regen-build-soil"],
    "PG-TRRE":    ["regen-build-soil", "regen-support-pollinators"],
    # Reduce Inputs
    "BDL-WSC":    ["regen-reduce-inputs"],
    "S-MICRO":    ["regen-reduce-inputs"],
    "SUSTANE-18-1-8+FE": ["regen-reduce-inputs"],
    "PG-BUDA":    ["regen-reduce-inputs", "regen-sequester-carbon"],
    "PG-BOGR":    ["regen-reduce-inputs", "regen-sequester-carbon"],
    "PG-PAVI":    ["regen-reduce-inputs", "regen-sequester-carbon"],
    "TURF-CLV":   ["regen-reduce-inputs"],
    # Feed Livestock Better
    "BDL-TPF":    ["regen-feed-livestock"],
    "PG-MESA":    ["regen-feed-livestock", "regen-sequester-carbon"],
    "PG-TRPR":    ["regen-feed-livestock"],
    "PB-COW-NTR": ["regen-feed-livestock"],
    "PB-COW-SO":  ["regen-feed-livestock"],
    "PB-HRSE-N":  ["regen-feed-livestock"],
    "PB-HRSE-SO": ["regen-feed-livestock"],
    "PB-HRSE-TR": ["regen-feed-livestock"],
    "PB-SHEP-N":  ["regen-feed-livestock"],
    "PB-SHEP-SO": ["regen-feed-livestock"],
    "PB-SHEP-TR": ["regen-feed-livestock"],
    "PB-GOAT-TR": ["regen-feed-livestock"],
    "PG-DAGL":    ["regen-feed-livestock"],
    # Support Pollinators
    "PB-HONEY":   ["regen-support-pollinators"],
    "BDL-POL":    ["regen-support-pollinators"],
    "WB-AN":      ["regen-support-pollinators"],
    "WB-RM":      ["regen-support-pollinators"],
    "WB-SD":      ["regen-support-pollinators"],
    # Sequester Carbon
    "PB-SGPR":    ["regen-sequester-carbon"],
    "CV-BGEC":    ["regen-sequester-carbon"],
    "PB-PLPR":    ["regen-sequester-carbon"],
    "PB-TXPR":    ["regen-sequester-carbon"],
}

# ── Step 1: Get or create parent category ────────────────────────────────────
print("Fetching existing categories...")
existing = wc_get("/products/categories", {"per_page": 100, "hide_empty": False})
existing_by_slug = {c["slug"]: c for c in existing}

if "regenerative-ag" in existing_by_slug:
    parent_id = existing_by_slug["regenerative-ag"]["id"]
    print(f"  Parent exists: ID {parent_id}")
else:
    resp = wc_post("/products/categories", PARENT_CAT)
    parent_id = resp.json()["id"]
    print(f"  Created parent: ID {parent_id}")
time.sleep(0.3)

# ── Step 2: Get or create subcategories ──────────────────────────────────────
subcat_slug_to_id = {}
for subcat in SUBCATEGORIES:
    if subcat["slug"] in existing_by_slug:
        subcat_slug_to_id[subcat["slug"]] = existing_by_slug[subcat["slug"]]["id"]
        print(f"  Subcat exists: {subcat['slug']} → ID {subcat_slug_to_id[subcat['slug']]}")
    else:
        payload = {**subcat, "parent": parent_id}
        resp = wc_post("/products/categories", payload)
        subcat_slug_to_id[subcat["slug"]] = resp.json()["id"]
        print(f"  Created subcat: {subcat['slug']} → ID {subcat_slug_to_id[subcat['slug']]}")
    time.sleep(0.3)

# ── Step 3: Assign products to categories ────────────────────────────────────
print("\nAssigning products to categories...")
results = {"success": [], "not_found": [], "error": []}

for sku, cat_slugs in PRODUCT_CATEGORIES.items():
    product_id = None
    # Find product by SKU
    search = wc_get("/products", {"sku": sku, "per_page": 1})
    if not search:
        # Try partial match
        search = wc_get("/products", {"search": sku, "per_page": 5})
        search = [p for p in search if p.get("sku", "").startswith(sku.split("-")[0])]

    if not search:
        print(f"  NOT FOUND: {sku}")
        results["not_found"].append(sku)
        time.sleep(0.3)
        continue

    product = search[0]
    product_id = product["id"]

    # Build target category list: existing cats + new regen cats (no duplicates)
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

# Save summary
with open(Path(__file__).parent / "regen_ag_category_setup.json", "w") as f:
    json.dump({"parent_id": parent_id, "subcategories": subcat_slug_to_id, "results": results}, f, indent=2)
print("Summary saved to regen_ag_category_setup.json")
```

- [ ] **Step 2: Run the script**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
python3 store/product-updates/setup_regen_ag_categories.py 2>&1 | grep -v NotOpenSSLWarning | grep -v "warnings.warn"
```

Expected output ends with: `Done. Success: 35+ | Not found: 0 | Errors: 0`
If any SKUs are not found, check the SKU spelling against the live catalog.

- [ ] **Step 3: Verify in WC Admin**

Hit the WC categories endpoint to confirm all 6 categories exist:
```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
python3 - <<'EOF'
import requests, base64
from pathlib import Path
env_vars = {}
with open(".env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip("'\"")
CF = env_vars.get("CF_WORKER_URL",""); CS = env_vars.get("CF_WORKER_SECRET","")
CK = env_vars["WC_CK"]; CC = env_vars["WC_CS"]
auth = base64.b64encode(f"{CK}:{CC}".encode()).decode()
resp = requests.get(CF, params={"wc_path": "/products/categories", "per_page": 100, "hide_empty": False},
    headers={"X-Proxy-Secret": CS, "Authorization": f"Basic {auth}"}, timeout=30)
for c in resp.json():
    if "regen" in c["slug"]:
        print(f"  [{c['id']}] {c['name']} — slug: {c['slug']} parent: {c['parent']} count: {c['count']}")
EOF
```

Expected: 6 lines (1 parent + 5 subcategories).

- [ ] **Step 4: Manual — Set Permalink Manager URL**

In WP Admin → Permalink Manager → find category "Regenerative Agriculture" → set custom URI to `/products/regenerative-agriculture/`. Save.

Verify: `curl -I https://naturesseed.com/products/regenerative-agriculture/` returns 200 (or will once the WP page exists — do after Task 3 Step 1).

- [ ] **Step 5: Commit**

```bash
git add store/product-updates/setup_regen_ag_categories.py store/product-updates/regen_ag_category_setup.json
git commit -m "feat: create regenerative-ag WC category tree and assign products"
```

---

## Task 3: Create WordPress Page

The PHP template is only served when a WordPress page with the matching slug exists in the database.

- [ ] **Step 1: Create page in WP Admin**

WP Admin → Pages → Add New:
- Title: `Regenerative Agriculture`
- Slug: `regenerative-agriculture`
- Status: Draft (not published yet)
- Template: leave as Default (the `page-regenerative-agriculture.php` template will be detected by its filename)
- Body content: leave empty

Save Draft.

- [ ] **Step 2: Set Permalink Manager custom URI**

WP Admin → Permalink Manager → Custom Permalinks → find the new page → set URI to `/products/regenerative-agriculture/`. Save.

No commit — this is a database/admin action.

---

## Task 4: Build PHP Page Template

**Files:**
- Create: `app/public/wp-content/themes/GSNature/page-regenerative-agriculture.php`
- Reference: `app/public/wp-content/themes/GSNature/template-parts/components/product-card.php` (read variable name from Task 1)

Before writing, confirm the variable name the product card template expects from Task 1 Step 1. The plan assumes `$product` — substitute if different.

- [ ] **Step 1: Write the template file**

```php
<?php
/**
 * Template Name: Regenerative Agriculture Hub
 *
 * @package GSNature
 */

defined('ABSPATH') || exit;

// ── Product helper ────────────────────────────────────────────────────────────
function regen_get_products( array $skus ): array {
    $products = [];
    foreach ( $skus as $sku ) {
        $id = wc_get_product_id_by_sku( $sku );
        if ( $id ) {
            $p = wc_get_product( $id );
            if ( $p && $p->is_visible() ) {
                $products[] = $p;
            }
        }
    }
    return $products;
}

// ── Outcome definitions ────────────────────────────────────────────────────────
$outcomes = [
    'build-soil' => [
        'slug'     => 'build-soil',
        'headline' => 'Build Soil',
        'icon'     => '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="32" height="32"><path d="M12 22V12M12 12C12 7 7 4 3 6M12 12C12 7 17 4 21 6"/><path d="M3 18c2-3 5-4 9-4s7 1 9 4"/></svg>',
        'explainer'=> 'Compacted, depleted soil is the root cause of most pasture and crop problems. Cover crops, nitrogen-fixing legumes, and mycorrhizal inoculants restore what decades of conventional management removed — without tillage.',
        'featured' => ['S-INNOC', 'BDL-SBC', 'PG-TRIN'],
    ],
    'reduce-inputs' => [
        'slug'     => 'reduce-inputs',
        'headline' => 'Reduce Inputs',
        'icon'     => '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="32" height="32"><circle cx="12" cy="12" r="9"/><path d="M9 12h6M12 9v6"/></svg>',
        'explainer'=> 'Every bag of synthetic fertilizer, every herbicide pass, every irrigation cycle is a cost you can reduce. The right plants — clovers, deep-rooted grasses, weed-smothering cover crops — do the work for free once established.',
        'featured' => ['BDL-WSC', 'S-MICRO', 'SUSTANE-18-1-8+FE'],
    ],
    'feed-livestock' => [
        'slug'     => 'feed-livestock',
        'headline' => 'Feed Livestock Better',
        'icon'     => '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="32" height="32"><path d="M3 9l4-5h10l4 5"/><path d="M3 9h18v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/><path d="M9 22V12h6v10"/></svg>',
        'explainer'=> 'A diverse pasture — grasses, legumes, forbs — produces more nutrition per acre than a monoculture stand and reduces supplemental feed costs. Rotation keeps it productive instead of overgrazed.',
        'featured' => ['BDL-TPF', 'PG-MESA', 'PG-TRPR'],
    ],
    'support-pollinators' => [
        'slug'     => 'support-pollinators',
        'headline' => 'Support Pollinators',
        'icon'     => '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="32" height="32"><path d="M12 2a4 4 0 014 4c0 1.5-.5 3-2 4l2 4H8l2-4c-1.5-1-2-2.5-2-4a4 4 0 014-4z"/><path d="M8 14l-3 5M16 14l3 5M12 14v5"/></svg>',
        'explainer'=> 'Healthy pollinator populations signal a functioning ecosystem — and benefit every neighboring farm. Clover and diverse forage mixes are the lowest-effort, highest-impact starting point.',
        'featured' => ['PB-HONEY', 'BDL-POL', 'S-DUTCH'],
    ],
    'sequester-carbon' => [
        'slug'     => 'sequester-carbon',
        'headline' => 'Sequester Carbon',
        'icon'     => '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="32" height="32"><path d="M12 22V6M12 6L7 11M12 6l5 5"/><path d="M5 19h14"/></svg>',
        'explainer'=> 'Deep-rooted perennial grasses are among the most effective carbon sinks on land. Restoring native prairie species builds soil organic matter that compounds over years — and increasingly qualifies for carbon credit programs.',
        'featured' => ['PG-PAVI', 'PB-SGPR', 'CV-BGEC'],
    ],
];

// ── All products for the full grid ────────────────────────────────────────────
$all_skus_map = [
    'build-soil'          => ['S-INNOC','BDL-SBC','PG-TRIN','S-DUTCH','PB-MUST','PG-BUCK','PG-SECE','SUSTANE-4-6-4','PG-TRRE'],
    'reduce-inputs'       => ['BDL-WSC','S-MICRO','SUSTANE-18-1-8+FE','PG-BUDA','PG-BOGR','PG-PAVI','TURF-CLV'],
    'feed-livestock'      => ['BDL-TPF','PG-MESA','PG-TRPR','PB-COW-NTR','PB-COW-SO','PB-HRSE-N','PB-HRSE-SO','PB-HRSE-TR','PB-SHEP-N','PB-SHEP-SO','PB-SHEP-TR','PB-GOAT-TR','PG-DAGL'],
    'support-pollinators' => ['PB-HONEY','BDL-POL','S-DUTCH','PG-TRIN','WB-AN','WB-RM','WB-SD','PG-TRRE'],
    'sequester-carbon'    => ['PG-PAVI','PB-SGPR','CV-BGEC','PG-BUDA','PG-BOGR','PB-PLPR','PG-MESA','PB-TXPR'],
];

// Build unique product list with outcome membership
$grid_products = []; // sku => ['product' => WC_Product, 'outcomes' => []]
foreach ( $all_skus_map as $outcome_slug => $skus ) {
    foreach ( $skus as $sku ) {
        if ( ! isset( $grid_products[$sku] ) ) {
            $id = wc_get_product_id_by_sku( $sku );
            if ( $id ) {
                $p = wc_get_product( $id );
                if ( $p && $p->is_visible() ) {
                    $grid_products[$sku] = ['product' => $p, 'outcomes' => []];
                }
            }
        }
        if ( isset( $grid_products[$sku] ) ) {
            $grid_products[$sku]['outcomes'][] = $outcome_slug;
        }
    }
}

// ── Blog articles ─────────────────────────────────────────────────────────────
$pillars = [
    [
        'label'   => 'Foundations',
        'slug'    => 'foundations',
        'articles' => [
            ['title' => 'What Is Regenerative Agriculture? A Plain-English Guide',      'teaser' => 'Cut through the buzzwords — here\'s what it actually means for a small operation.', 'read_time' => '6 min', 'url' => '#'],
            ['title' => 'The 5 Principles of Soil Health',                              'teaser' => 'Gabe Brown\'s framework, explained for ranchers who are short on time and long on skepticism.', 'read_time' => '7 min', 'url' => '#'],
            ['title' => 'What Your Soil Test Actually Tells You',                       'teaser' => 'Most farmers run the test. Few know which numbers actually matter.', 'read_time' => '5 min', 'url' => '#'],
            ['title' => 'Cover Crops 101: How to Pick Your First Mix',                 'teaser' => 'Species selection, seeding rates, and termination — without the agronomy degree.', 'read_time' => '8 min', 'url' => '#'],
        ],
    ],
    [
        'label'   => 'Practical How-To',
        'slug'    => 'how-to',
        'articles' => [
            ['title' => 'Frost Seeding Clover Into an Existing Pasture',               'teaser' => 'The lowest-cost pasture improvement you can make, explained step by step.', 'read_time' => '5 min', 'url' => '#'],
            ['title' => 'Renovating a Tired Hobby Farm Pasture in One Season',         'teaser' => 'Overseeding vs. full renovation — how to decide, and what to plant.', 'read_time' => '9 min', 'url' => '#'],
            ['title' => 'Stockpile Grazing: How to Save on Hay',                       'teaser' => 'Fescue and timing are the whole game. Here\'s how smaller operations pull it off.', 'read_time' => '6 min', 'url' => '#'],
            ['title' => 'Why Mycorrhizae Matter for Pasture Establishment',            'teaser' => 'The soil biology shortcut that most seeding guides leave out.', 'read_time' => '5 min', 'url' => '#'],
        ],
    ],
    [
        'label'   => 'Niche Deep Dives',
        'slug'    => 'deep-dives',
        'articles' => [
            ['title' => 'Silvopasture: Forage Under Trees Without Killing Either',     'teaser' => 'Species selection and spacing for integrated tree-and-livestock systems.', 'read_time' => '10 min', 'url' => '#'],
            ['title' => 'Pollinator Forage for Beekeepers With Acreage',               'teaser' => 'Beyond clover — building a season-long forage calendar for honeybees.', 'read_time' => '7 min', 'url' => '#'],
            ['title' => 'Carbon Capture on a Small Farm: What\'s Real, What\'s Hype', 'teaser' => 'Soil carbon programs explained for operations under 500 acres.', 'read_time' => '8 min', 'url' => '#'],
            ['title' => 'Multi-Species Cover Crop Mixes Explained',                   'teaser' => 'Why single-species cover crops are leaving yield on the table.', 'read_time' => '7 min', 'url' => '#'],
        ],
    ],
];

get_header();
?>

<main class="regen-hub" id="main">

    <?php /* ── HERO ────────────────────────────────────────────────────── */ ?>
    <section class="regen-hub__hero">
        <div class="regen-hub__hero-inner">
            <h1 class="regen-hub__hero-headline">Farming With Nature, Not Against It</h1>
            <p class="regen-hub__hero-subhead">Practical seeds and soil tools for smaller-scale ranchers and farmers building healthier land — one season at a time.</p>
            <p class="regen-hub__hero-body">Regenerative agriculture isn't a certification or a philosophy seminar. It's a set of practices that improve your land, reduce your input costs, and build something worth passing on.</p>
            <a href="#challenge-selector" class="regen-hub__hero-cta btn btn--primary">Find your starting point &rarr;</a>
        </div>
    </section>

    <?php /* ── CHALLENGE SELECTOR ──────────────────────────────────────── */ ?>
    <section class="regen-hub__challenge-selector" id="challenge-selector">
        <p class="regen-hub__challenge-label">What's your biggest challenge right now?</p>
        <div class="regen-hub__challenge-pills">
            <a href="#build-soil"          class="regen-hub__challenge-pill">My soil is tired and compacted</a>
            <a href="#reduce-inputs"       class="regen-hub__challenge-pill">I'm spending too much on inputs</a>
            <a href="#feed-livestock"      class="regen-hub__challenge-pill">My pastures aren't feeding my animals</a>
            <a href="#support-pollinators" class="regen-hub__challenge-pill">I want to support pollinators</a>
            <a href="#sequester-carbon"    class="regen-hub__challenge-pill">I want to capture carbon</a>
        </div>
    </section>

    <?php /* ── OUTCOME SECTIONS ──────────────────────────────────────────── */ ?>
    <?php foreach ( $outcomes as $outcome ) :
        $featured_products = regen_get_products( $outcome['featured'] );
    ?>
    <section class="regen-hub__outcome regen-hub__outcome--<?php echo esc_attr( $outcome['slug'] ); ?>" id="<?php echo esc_attr( $outcome['slug'] ); ?>">
        <div class="regen-hub__outcome-inner">
            <div class="regen-hub__outcome-header">
                <span class="regen-hub__outcome-icon"><?php echo $outcome['icon']; ?></span>
                <h2 class="regen-hub__outcome-headline"><?php echo esc_html( $outcome['headline'] ); ?></h2>
            </div>
            <p class="regen-hub__outcome-explainer"><?php echo esc_html( $outcome['explainer'] ); ?></p>

            <?php if ( $featured_products ) : ?>
            <ul class="regen-hub__outcome-products">
                <?php foreach ( $featured_products as $product ) : ?>
                <li class="regen-hub__outcome-product-item">
                    <?php
                    // Product card reads from global $product (confirmed Task 1).
                    $GLOBALS['product'] = $product;
                    gsnature_template_part( 'components/product-card' );
                    ?>
                </li>
                <?php endforeach; ?>
            </ul>
            <?php endif; ?>

            <a href="#all-products" class="regen-hub__outcome-see-all">See all <?php echo esc_html( strtolower( $outcome['headline'] ) ); ?> products &rarr;</a>
        </div>
    </section>
    <?php endforeach; ?>

    <?php /* ── FULL PRODUCT GRID ──────────────────────────────────────────── */ ?>
    <section class="regen-hub__grid-section" id="all-products">
        <div class="regen-hub__grid-inner">
            <h2 class="regen-hub__grid-title">All Regenerative Agriculture Products</h2>

            <div class="regen-hub__filter-tabs" role="tablist">
                <button class="regen-hub__filter-tab is-active" data-outcome="all" role="tab">All</button>
                <button class="regen-hub__filter-tab" data-outcome="build-soil" role="tab">Build Soil</button>
                <button class="regen-hub__filter-tab" data-outcome="reduce-inputs" role="tab">Reduce Inputs</button>
                <button class="regen-hub__filter-tab" data-outcome="feed-livestock" role="tab">Feed Livestock</button>
                <button class="regen-hub__filter-tab" data-outcome="support-pollinators" role="tab">Support Pollinators</button>
                <button class="regen-hub__filter-tab" data-outcome="sequester-carbon" role="tab">Sequester Carbon</button>
            </div>

            <ul class="regen-hub__grid woocommerce">
                <?php foreach ( $grid_products as $sku => $entry ) :
                    $product = $entry['product'];
                    $outcome_list = implode( ' ', $entry['outcomes'] );
                ?>
                <li class="regen-hub__grid-item" data-outcomes="<?php echo esc_attr( $outcome_list ); ?>">
                    <?php
                    set_query_var( 'product', $product );
                    gsnature_template_part( 'components/product-card' );
                    ?>
                </li>
                <?php endforeach; ?>
            </ul>
        </div>
    </section>

    <?php /* ── BLOG CARDS ────────────────────────────────────────────────── */ ?>
    <section class="regen-hub__learn" id="learn-more">
        <div class="regen-hub__learn-inner">
            <h2 class="regen-hub__learn-title">Learn More</h2>
            <p class="regen-hub__learn-subtitle">Practical guides written for operations under 500 acres — no certification required.</p>

            <?php foreach ( $pillars as $pillar ) : ?>
            <div class="regen-hub__pillar regen-hub__pillar--<?php echo esc_attr( $pillar['slug'] ); ?>">
                <span class="regen-hub__pillar-badge"><?php echo esc_html( $pillar['label'] ); ?></span>
                <div class="regen-hub__article-grid">
                    <?php foreach ( $pillar['articles'] as $article ) : ?>
                    <article class="regen-hub__article-card">
                        <span class="regen-hub__article-badge regen-hub__article-badge--<?php echo esc_attr( $pillar['slug'] ); ?>"><?php echo esc_html( $pillar['label'] ); ?></span>
                        <h3 class="regen-hub__article-title"><?php echo esc_html( $article['title'] ); ?></h3>
                        <p class="regen-hub__article-teaser"><?php echo esc_html( $article['teaser'] ); ?></p>
                        <div class="regen-hub__article-footer">
                            <span class="regen-hub__article-read-time"><?php echo esc_html( $article['read_time'] ); ?> read</span>
                            <a href="<?php echo esc_url( $article['url'] ); ?>" class="regen-hub__article-link">Read article &rarr;</a>
                        </div>
                    </article>
                    <?php endforeach; ?>
                </div>
            </div>
            <?php endforeach; ?>
        </div>
    </section>

    <?php /* ── FOOTER CTA ───────────────────────────────────────────────── */ ?>
    <section class="regen-hub__footer-cta">
        <div class="regen-hub__footer-cta-inner">
            <h2 class="regen-hub__footer-cta-headline">Not sure where to start?</h2>
            <p class="regen-hub__footer-cta-body">Most small operations see the biggest return from improving soil biology first. A cover crop mix and a mycorrhizal inoculant — two products, one season, measurable difference.</p>
            <a href="#build-soil" class="regen-hub__footer-cta-btn btn btn--primary">Shop Cover Crops &amp; Soil Builders &rarr;</a>
        </div>
    </section>

</main>

<script>
(function () {
    var tabs = document.querySelectorAll('.regen-hub__filter-tab');
    var items = document.querySelectorAll('.regen-hub__grid-item');

    tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            var outcome = this.dataset.outcome;
            tabs.forEach(function (t) { t.classList.remove('is-active'); });
            this.classList.add('is-active');
            items.forEach(function (item) {
                var outcomes = item.dataset.outcomes ? item.dataset.outcomes.split(' ') : [];
                item.style.display = (outcome === 'all' || outcomes.indexOf(outcome) !== -1) ? '' : 'none';
            });
        });
    });
})();
</script>

<?php get_footer(); ?>
```

- [ ] **Step 2: Verify template is detected by WordPress**

After saving the file, go to WP Admin → Pages → find the "Regenerative Agriculture" page created in Task 3 → Edit → Page Attributes → Template dropdown. Confirm "Regenerative Agriculture Hub" appears as an option. Select it and Save.

If it doesn't appear, check the `Template Name:` comment at the top of the file matches exactly.

No commit yet — SCSS and build come first.

---

## Task 5: Build SCSS

**Files:**
- Create: `app/public/wp-content/themes/GSNature/assets/scss/pages/_regenerative-agriculture.scss`
- Modify: SCSS entry file found in Task 1 Step 2

- [ ] **Step 1: Write the SCSS file**

```scss
// _regenerative-agriculture.scss
// Regenerative Agriculture Hub page styles

// ── Variables ─────────────────────────────────────────────────────────────────
$regen-green:         #2D5A27;
$regen-green-light:   #4a7c42;
$regen-brown:         #8B6914;
$regen-slate:         #3D5A73;
$regen-cream:         #f7f4ef;
$regen-border:        #e2ddd5;
$regen-text:          #2c2c2c;

// Pillar badge colors
$pillar-foundations:  #8B6914;
$pillar-how-to:       #2D5A27;
$pillar-deep-dives:   #3D5A73;

.regen-hub {

    // ── Hero ─────────────────────────────────────────────────────────────────
    &__hero {
        background: $regen-green;
        color: #fff;
        padding: 80px 24px;
        text-align: center;
    }

    &__hero-inner {
        max-width: 720px;
        margin: 0 auto;
    }

    &__hero-headline {
        font-size: clamp(2rem, 4vw, 3rem);
        font-weight: 700;
        margin: 0 0 16px;
        line-height: 1.15;
    }

    &__hero-subhead {
        font-size: 1.2rem;
        opacity: 0.9;
        margin: 0 0 16px;
    }

    &__hero-body {
        font-size: 1rem;
        opacity: 0.8;
        max-width: 560px;
        margin: 0 auto 32px;
    }

    &__hero-cta {
        display: inline-block;
        background: #fff;
        color: $regen-green;
        font-weight: 600;
        padding: 14px 28px;
        border-radius: 4px;
        text-decoration: none;
        transition: background 0.2s, color 0.2s;

        &:hover {
            background: $regen-cream;
        }
    }

    // ── Challenge selector ───────────────────────────────────────────────────
    &__challenge-selector {
        background: $regen-cream;
        padding: 40px 24px;
        text-align: center;
    }

    &__challenge-label {
        font-size: 1rem;
        font-weight: 600;
        color: $regen-text;
        margin: 0 0 20px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    &__challenge-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        justify-content: center;
        max-width: 900px;
        margin: 0 auto;
    }

    &__challenge-pill {
        display: inline-block;
        padding: 10px 20px;
        border: 2px solid $regen-green;
        border-radius: 100px;
        color: $regen-green;
        font-weight: 500;
        font-size: 0.9rem;
        text-decoration: none;
        transition: background 0.2s, color 0.2s;

        &:hover {
            background: $regen-green;
            color: #fff;
        }
    }

    // ── Outcome sections ─────────────────────────────────────────────────────
    &__outcome {
        padding: 64px 24px;
        border-bottom: 1px solid $regen-border;

        &:nth-child(even) {
            background: $regen-cream;
        }
    }

    &__outcome-inner {
        max-width: 1100px;
        margin: 0 auto;
    }

    &__outcome-header {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 16px;
    }

    &__outcome-icon {
        color: $regen-green;
        flex-shrink: 0;
    }

    &__outcome-headline {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
        color: $regen-text;
    }

    &__outcome-explainer {
        font-size: 1.05rem;
        line-height: 1.65;
        color: #555;
        max-width: 720px;
        margin: 0 0 32px;
    }

    &__outcome-products {
        list-style: none;
        padding: 0;
        margin: 0 0 24px;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 24px;

        @media (max-width: 768px) {
            grid-template-columns: 1fr 1fr;
        }

        @media (max-width: 480px) {
            grid-template-columns: 1fr;
        }
    }

    &__outcome-see-all {
        display: inline-block;
        color: $regen-green;
        font-weight: 600;
        text-decoration: underline;
        font-size: 0.95rem;

        &:hover {
            color: $regen-green-light;
        }
    }

    // ── Full product grid ────────────────────────────────────────────────────
    &__grid-section {
        padding: 64px 24px;
        background: #fff;
    }

    &__grid-inner {
        max-width: 1200px;
        margin: 0 auto;
    }

    &__grid-title {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0 0 24px;
        color: $regen-text;
    }

    &__filter-tabs {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 32px;
    }

    &__filter-tab {
        padding: 8px 18px;
        border: 2px solid $regen-border;
        background: #fff;
        border-radius: 100px;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        color: $regen-text;
        transition: border-color 0.2s, background 0.2s, color 0.2s;

        &:hover {
            border-color: $regen-green;
            color: $regen-green;
        }

        &.is-active {
            background: $regen-green;
            border-color: $regen-green;
            color: #fff;
        }
    }

    &__grid {
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 24px;

        @media (max-width: 1024px) { grid-template-columns: repeat(3, 1fr); }
        @media (max-width: 768px)  { grid-template-columns: repeat(2, 1fr); }
        @media (max-width: 480px)  { grid-template-columns: 1fr; }
    }

    &__grid-item {
        // inherits product card styles from product-card.php
    }

    // ── Learn More / Blog cards ──────────────────────────────────────────────
    &__learn {
        padding: 64px 24px;
        background: $regen-cream;
    }

    &__learn-inner {
        max-width: 1200px;
        margin: 0 auto;
    }

    &__learn-title {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0 0 8px;
        color: $regen-text;
    }

    &__learn-subtitle {
        font-size: 1rem;
        color: #666;
        margin: 0 0 48px;
    }

    &__pillar {
        margin-bottom: 48px;

        &:last-child { margin-bottom: 0; }
    }

    &__pillar-badge {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        padding: 4px 10px;
        border-radius: 100px;
        margin-bottom: 20px;
        color: #fff;

        .regen-hub__pillar--foundations & { background: $pillar-foundations; }
        .regen-hub__pillar--how-to &      { background: $pillar-how-to; }
        .regen-hub__pillar--deep-dives &  { background: $pillar-deep-dives; }
    }

    &__article-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;

        @media (max-width: 1024px) { grid-template-columns: repeat(2, 1fr); }
        @media (max-width: 480px)  { grid-template-columns: 1fr; }
    }

    &__article-card {
        background: #fff;
        border-radius: 6px;
        padding: 24px;
        border: 1px solid $regen-border;
        display: flex;
        flex-direction: column;
        transition: box-shadow 0.2s;

        &:hover {
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        }
    }

    &__article-badge {
        display: inline-block;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 3px 8px;
        border-radius: 100px;
        margin-bottom: 14px;
        color: #fff;
        align-self: flex-start;

        &--foundations { background: $pillar-foundations; }
        &--how-to      { background: $pillar-how-to; }
        &--deep-dives  { background: $pillar-deep-dives; }
    }

    &__article-title {
        font-size: 0.95rem;
        font-weight: 700;
        line-height: 1.4;
        color: $regen-text;
        margin: 0 0 10px;
        flex-grow: 1;
    }

    &__article-teaser {
        font-size: 0.85rem;
        color: #666;
        line-height: 1.55;
        margin: 0 0 16px;
    }

    &__article-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: auto;
    }

    &__article-read-time {
        font-size: 0.75rem;
        color: #999;
    }

    &__article-link {
        font-size: 0.8rem;
        font-weight: 600;
        color: $regen-green;
        text-decoration: none;

        &:hover { text-decoration: underline; }
    }

    // ── Footer CTA ───────────────────────────────────────────────────────────
    &__footer-cta {
        background: $regen-green;
        color: #fff;
        padding: 64px 24px;
        text-align: center;
    }

    &__footer-cta-inner {
        max-width: 600px;
        margin: 0 auto;
    }

    &__footer-cta-headline {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0 0 16px;
    }

    &__footer-cta-body {
        font-size: 1rem;
        opacity: 0.9;
        line-height: 1.65;
        margin: 0 0 32px;
    }

    &__footer-cta-btn {
        display: inline-block;
        background: #fff;
        color: $regen-green;
        font-weight: 600;
        padding: 14px 28px;
        border-radius: 4px;
        text-decoration: none;
        transition: background 0.2s;

        &:hover { background: $regen-cream; }
    }
}

// ── Smooth scroll ─────────────────────────────────────────────────────────────
html:has(.regen-hub) {
    scroll-behavior: smooth;
}
```

- [ ] **Step 2: Add import to SCSS entry file**

Open the SCSS entry file found in Task 1 Step 2. Find the line that imports `_shipping-policy.scss` (or whichever adjacent page file exists). Add the new import directly after it, using the same syntax:

```scss
// If the existing syntax is @use:
@use 'pages/regenerative-agriculture';

// If the existing syntax is @import:
@import 'pages/regenerative-agriculture';
```

- [ ] **Step 3: Run the Vite build**

```bash
cd app/public/wp-content/themes/GSNature
npx vite build
```

Expected: build completes with no errors. SCSS compile warnings are acceptable; errors are not.

- [ ] **Step 4: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add app/public/wp-content/themes/GSNature/page-regenerative-agriculture.php
git add app/public/wp-content/themes/GSNature/assets/scss/pages/_regenerative-agriculture.scss
git add app/public/wp-content/themes/GSNature/assets/scss/main.scss  # or whichever entry file
git add app/public/wp-content/themes/GSNature/dist/
git commit -m "feat: add regenerative agriculture hub page template and styles"
```

---

## Task 6: QA Checklist

Open `https://naturesseed.com/products/regenerative-agriculture/` (or the local dev URL) with the WordPress page set to Published.

- [ ] **Hero:** Headline, subhead, and CTA button visible. CTA scrolls to challenge selector.
- [ ] **Challenge selector:** All 5 pills visible. Each pill scrolls to its correct outcome section (check `#build-soil`, `#sequester-carbon`).
- [ ] **Outcome sections:** All 5 render. Each shows 3 product cards. "See all" link scrolls to `#all-products`.
- [ ] **Product cards:** Images, names, prices, and Add to Cart buttons load. No missing products (check console for 404s).
- [ ] **Full grid:** All products visible under "All" tab. Each filter tab correctly shows/hides products. A product in multiple outcomes (e.g., S-DUTCH) appears under both relevant tabs.
- [ ] **Blog cards:** All 12 article cards render with title, teaser, read time, and badge. Links are `#` placeholders — confirm no broken redirects.
- [ ] **Footer CTA:** "Shop Cover Crops & Soil Builders" button scrolls to `#build-soil`.
- [ ] **Mobile (375px):** Challenge pills wrap cleanly. Outcome product grid drops to 1-col. Article grid drops to 1-col. No horizontal overflow.
- [ ] **Page not in nav:** Confirm the hub does not appear in the main navigation.

- [ ] **Final commit if any fixes were needed**

```bash
git add -p
git commit -m "fix: regen ag hub QA adjustments"
```

---

## Notes for Sub-project 2 & 3

- **Sub-project 2** (new products/bundles): When new SKUs are added, update `$all_skus_map` and `$outcomes[*]['featured']` arrays in `page-regenerative-agriculture.php` and re-run `setup_regen_ag_categories.py` with the new SKUs.
- **Sub-project 3** (blog articles): When articles are written and published, replace `'url' => '#'` in the `$pillars` array with the actual article URLs. No other changes needed.
