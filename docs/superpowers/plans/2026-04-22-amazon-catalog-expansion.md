# Amazon Catalog Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pull all WooCommerce products missing from Amazon, push complete ones as inactive SP-API drafts, and generate a structured content manager to-do for incomplete listings.

**Architecture:** Three existing scripts build the data foundation (Amazon catalog, WC catalog, cross-reference CSV). A new `push_amazon_drafts.py` script reads the cross-ref output, checks completeness, pushes ready listings to SP-API as INACTIVE, writes a status CSV + Supabase upsert, and generates `content_manager_todo.md` for flagged products.

**Tech Stack:** Python 3, requests, SP-API Listings Items v2021-08-01, Supabase REST API, csv, json

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `Amazonimprovement/pull_amazon_catalog.py` | Run as-is | Produces `amazon_catalog.json` |
| `Amazonimprovement/pull_wc_catalog.py` | Run as-is | Produces `wc_catalog.json` |
| `Amazonimprovement/amazon_wc_crossref.py` | Run as-is | Produces `amazon_missing_products.csv` |
| `Amazonimprovement/push_amazon_drafts.py` | **Create** | Main new script — completeness check, SP-API push, status output, todo generator |
| `Amazonimprovement/tests/test_push_amazon_drafts.py` | **Create** | Unit tests for pure functions |
| `Amazonimprovement/amazon_expansion_status.csv` | Generated output | Per-SKU status tracking |
| `Amazonimprovement/content_manager_todo.md` | Generated output | Content manager briefing doc |

---

## Task 1: Create Supabase Table

**Files:**
- No code file — run SQL directly via Supabase dashboard

- [ ] **Step 1: Open Supabase SQL editor**

Log into Supabase → SQL Editor → New Query. Run:

```sql
create table if not exists amazon_listing_queue (
  sku text primary key,
  title text,
  status text,
  missing_fields text,
  image_count int,
  asin text,
  pushed_at timestamptz,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

- [ ] **Step 2: Verify table exists**

In Supabase Table Editor, confirm `amazon_listing_queue` appears with the correct columns.

---

## Task 2: Run Data Pull Scripts

**Files:**
- Run: `Amazonimprovement/pull_amazon_catalog.py`
- Run: `Amazonimprovement/pull_wc_catalog.py`
- Run: `Amazonimprovement/amazon_wc_crossref.py`

- [ ] **Step 1: Pull Amazon catalog**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/Amazonimprovement"
python pull_amazon_catalog.py
```

Expected: `amazon_catalog.json` created in the working directory. Output should show "Token acquired" and a count of listings fetched.

- [ ] **Step 2: Pull WooCommerce catalog**

```bash
python pull_wc_catalog.py
```

Expected: `wc_catalog.json` created. Output shows product count.

- [ ] **Step 3: Run cross-reference**

```bash
python amazon_wc_crossref.py
```

Expected: `amazon_missing_products.csv`, `amazon_content_audit.csv`, `amazon_content_enrichment.csv` created. Note the count printed for "missing products".

- [ ] **Step 4: Inspect missing products CSV**

```bash
python -c "
import csv
with open('amazon_missing_products.csv') as f:
    rows = list(csv.DictReader(f))
print(f'Missing from Amazon: {len(rows)} products')
print('Columns:', list(rows[0].keys()) if rows else 'none')
if rows:
    print('First row keys/values:')
    for k, v in list(rows[0].items())[:8]:
        print(f'  {k}: {str(v)[:80]}')
"
```

Record the column names — you'll need them in Task 3.

- [ ] **Step 5: Commit data artifacts note**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add Amazonimprovement/amazon_missing_products.csv Amazonimprovement/amazon_catalog.json Amazonimprovement/wc_catalog.json
git commit -m "data: pull amazon and wc catalogs for expansion analysis"
```

---

## Task 3: Scaffold push_amazon_drafts.py — Env, Auth, SP-API Wrappers

**Files:**
- Create: `Amazonimprovement/push_amazon_drafts.py`
- Create: `Amazonimprovement/tests/test_push_amazon_drafts.py`

- [ ] **Step 1: Write failing test for env loading**

Create `Amazonimprovement/tests/test_push_amazon_drafts.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_check_completeness_ready():
    from push_amazon_drafts import check_completeness
    row = {
        'name': 'Kentucky Bluegrass Seed',
        'sku': 'NS-KBG-5LB',
        'bullets': 'Fast germination\nDense coverage\nDrought tolerant\nFine texture\nPersistent stand',
        'description': 'Premium Kentucky Bluegrass for home lawns and athletic fields.',
        'images': 'https://example.com/img1.jpg',
        'price': '29.99',
    }
    result = check_completeness(row)
    assert result['ready'] is True
    assert result['missing'] == []

def test_check_completeness_missing_bullets():
    from push_amazon_drafts import check_completeness
    row = {
        'name': 'Kentucky Bluegrass Seed',
        'sku': 'NS-KBG-5LB',
        'bullets': 'Fast germination\nDense coverage',
        'description': 'Premium Kentucky Bluegrass.',
        'images': 'https://example.com/img1.jpg',
        'price': '29.99',
    }
    result = check_completeness(row)
    assert result['ready'] is False
    assert 'bullets' in result['missing']

def test_check_completeness_missing_image():
    from push_amazon_drafts import check_completeness
    row = {
        'name': 'Kentucky Bluegrass Seed',
        'sku': 'NS-KBG-5LB',
        'bullets': 'b1\nb2\nb3\nb4\nb5',
        'description': 'Premium Kentucky Bluegrass.',
        'images': '',
        'price': '29.99',
    }
    result = check_completeness(row)
    assert result['ready'] is False
    assert 'images' in result['missing']

def test_check_completeness_missing_price():
    from push_amazon_drafts import check_completeness
    row = {
        'name': 'Kentucky Bluegrass Seed',
        'sku': 'NS-KBG-5LB',
        'bullets': 'b1\nb2\nb3\nb4\nb5',
        'description': 'Premium Kentucky Bluegrass.',
        'images': 'https://example.com/img1.jpg',
        'price': '0',
    }
    result = check_completeness(row)
    assert result['ready'] is False
    assert 'price' in result['missing']
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/Amazonimprovement"
python -m pytest tests/test_push_amazon_drafts.py -v 2>&1 | head -30
```

Expected: `ImportError` or `ModuleNotFoundError` — file doesn't exist yet.

- [ ] **Step 3: Create push_amazon_drafts.py with env loading and check_completeness**

Create `Amazonimprovement/push_amazon_drafts.py`:

```python
import os, csv, json, time, re, requests
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
ENV_PATH = PROJECT_DIR / ".env"
MISSING_CSV = SCRIPT_DIR / "amazon_missing_products.csv"
STATUS_CSV = SCRIPT_DIR / "amazon_expansion_status.csv"
TODO_MD = SCRIPT_DIR / "content_manager_todo.md"

# ── Env ──────────────────────────────────────────────────────────────────────
def _load_env():
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env

_ENV = _load_env()
AMZ_CLIENT_ID = _ENV["AMAZON_CLIENT_ID"]
AMZ_CLIENT_SECRET = _ENV["AMAZON_CLIENT_SECRET"]
AMZ_REFRESH_TOKEN = _ENV["AMAZON_REFRESH_TOKEN"]
AMZ_MARKETPLACE_ID = "ATVPDKIKX0DER"
SP_API_BASE = "https://sellingpartnerapi-na.amazon.com"
SUPABASE_URL = _ENV["SUPABASE_URL"]
SUPABASE_KEY = _ENV["SUPABASE_SECRET_API_KEY"]

# ── LWA Token ─────────────────────────────────────────────────────────────────
_token_cache = {"token": None, "expires_at": None}

def get_token():
    now = datetime.utcnow()
    if _token_cache["token"] and _token_cache["expires_at"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]
    print("  Refreshing LWA access token...")
    resp = requests.post("https://api.amazon.com/auth/o2/token", data={
        "grant_type": "refresh_token",
        "refresh_token": AMZ_REFRESH_TOKEN,
        "client_id": AMZ_CLIENT_ID,
        "client_secret": AMZ_CLIENT_SECRET,
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    expires_in = int(data.get("expires_in", 3600)) - 60
    _token_cache["expires_at"] = now + timedelta(seconds=expires_in)
    print("  Token acquired.")
    return _token_cache["token"]

# ── SP-API helpers ────────────────────────────────────────────────────────────
def sp_get(path, params=None, retries=3):
    for attempt in range(retries):
        headers = {"x-amz-access-token": get_token(), "Content-Type": "application/json"}
        resp = requests.get(f"{SP_API_BASE}{path}", headers=headers,
                            params=params or {}, timeout=30)
        if resp.status_code == 429:
            wait = 2 ** attempt + 1
            print(f"    Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        return resp
    return resp

def sp_put(path, body, retries=3):
    for attempt in range(retries):
        headers = {"x-amz-access-token": get_token(), "Content-Type": "application/json"}
        resp = requests.put(f"{SP_API_BASE}{path}", headers=headers,
                            json=body, timeout=30)
        if resp.status_code == 429:
            wait = 2 ** attempt + 1
            print(f"    Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        return resp
    return resp

# ── Seller ID ─────────────────────────────────────────────────────────────────
_seller_id = None

def get_seller_id():
    global _seller_id
    if _seller_id:
        return _seller_id
    resp = sp_get("/sellers/v1/marketplaceParticipations")
    resp.raise_for_status()
    data = resp.json()
    participations = data.get("payload", [])
    for p in participations:
        if p.get("marketplace", {}).get("id") == AMZ_MARKETPLACE_ID:
            _seller_id = p["seller"]["sellerId"]
            print(f"  Seller ID: {_seller_id}")
            return _seller_id
    raise ValueError("Could not find seller ID for US marketplace")

# ── Completeness check ────────────────────────────────────────────────────────
def check_completeness(row):
    """Return {'ready': bool, 'missing': [field_names]}."""
    missing = []
    if not str(row.get('name', '')).strip():
        missing.append('title')
    bullets_raw = str(row.get('bullets', ''))
    bullet_lines = [b.strip() for b in bullets_raw.split('\n') if b.strip()]
    if len(bullet_lines) < 5:
        missing.append('bullets')
    desc = re.sub(r'<[^>]+>', '', str(row.get('description', ''))).strip()
    if len(desc) < 50:
        missing.append('description')
    images_raw = str(row.get('images', '')).strip()
    if not images_raw:
        missing.append('images')
    try:
        price = float(str(row.get('price', '0')).replace('$', '').strip())
    except (ValueError, TypeError):
        price = 0
    if price <= 0:
        missing.append('price')
    return {'ready': len(missing) == 0, 'missing': missing}
```

- [ ] **Step 4: Run tests — expect them to pass**

```bash
python -m pytest tests/test_push_amazon_drafts.py -v
```

Expected output:
```
test_check_completeness_ready PASSED
test_check_completeness_missing_bullets PASSED
test_check_completeness_missing_image PASSED
test_check_completeness_missing_price PASSED
4 passed
```

- [ ] **Step 5: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add Amazonimprovement/push_amazon_drafts.py Amazonimprovement/tests/test_push_amazon_drafts.py
git commit -m "feat: scaffold push_amazon_drafts with completeness checker and tests"
```

---

## Task 4: Build Listing Payload and SP-API Push

**Files:**
- Modify: `Amazonimprovement/push_amazon_drafts.py` (append functions)
- Modify: `Amazonimprovement/tests/test_push_amazon_drafts.py` (add tests)

- [ ] **Step 1: Write failing tests for payload builder**

Append to `Amazonimprovement/tests/test_push_amazon_drafts.py`:

```python
def test_build_listing_payload_structure():
    from push_amazon_drafts import build_listing_payload
    row = {
        'name': 'Kentucky Bluegrass Seed 5 lb',
        'sku': 'NS-KBG-5LB',
        'bullets': 'Fast germination\nDense coverage\nDrought tolerant\nFine texture\nPersistent stand',
        'description': 'Premium Kentucky Bluegrass seed for home lawns and athletic fields. Establishes a dense, fine-textured turf.',
        'images': 'https://example.com/img1.jpg|https://example.com/img2.jpg',
        'price': '29.99',
        'search_terms': 'grass seed lawn seed bluegrass',
    }
    payload = build_listing_payload(row)
    assert payload['productType'] == 'LAWN_AND_GARDEN'
    assert payload['attributes']['item_name'][0]['value'] == 'Kentucky Bluegrass Seed 5 lb'
    assert len(payload['attributes']['bullet_point']) == 5
    assert payload['attributes']['list_price'][0]['value'] == 29.99
    assert len(payload['attributes']['main_offer_image_locator']) >= 1
    assert payload['attributes']['fulfillment_availability'][0]['quantity'] == 0

def test_build_listing_payload_image_split():
    from push_amazon_drafts import build_listing_payload
    row = {
        'name': 'Test Seed',
        'sku': 'NS-TEST-1LB',
        'bullets': 'b1\nb2\nb3\nb4\nb5',
        'description': 'A' * 60,
        'images': 'https://a.com/1.jpg|https://a.com/2.jpg|https://a.com/3.jpg',
        'price': '9.99',
        'search_terms': '',
    }
    payload = build_listing_payload(row)
    # first image is main, rest are other_offer_image_locator
    assert len(payload['attributes']['main_offer_image_locator']) == 1
    assert len(payload['attributes']['other_offer_image_locator']) == 2
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/Amazonimprovement"
python -m pytest tests/test_push_amazon_drafts.py::test_build_listing_payload_structure tests/test_push_amazon_drafts.py::test_build_listing_payload_image_split -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'build_listing_payload'`

- [ ] **Step 3: Implement build_listing_payload and push_listing**

Append to the end of `Amazonimprovement/push_amazon_drafts.py` (before any `if __name__` block):

```python
# ── Payload builder ───────────────────────────────────────────────────────────
def build_listing_payload(row):
    """Build SP-API Listings Items PUT body for an INACTIVE draft."""
    bullets_raw = str(row.get('bullets', ''))
    bullet_lines = [b.strip() for b in bullets_raw.split('\n') if b.strip()][:5]
    bullet_points = [{"value": b, "marketplace_id": AMZ_MARKETPLACE_ID} for b in bullet_lines]

    images_raw = str(row.get('images', ''))
    image_urls = [u.strip() for u in images_raw.split('|') if u.strip()]
    main_image = [{"media_location": image_urls[0], "marketplace_id": AMZ_MARKETPLACE_ID}]
    other_images = [
        {"media_location": url, "marketplace_id": AMZ_MARKETPLACE_ID}
        for url in image_urls[1:]
    ]

    try:
        price_val = float(str(row.get('price', '0')).replace('$', '').strip())
    except (ValueError, TypeError):
        price_val = 0.0

    desc = re.sub(r'<[^>]+>', '', str(row.get('description', ''))).strip()

    search_terms_raw = str(row.get('search_terms', ''))
    search_terms = [t.strip() for t in search_terms_raw.replace(',', ' ').split() if t.strip()][:50]

    attributes = {
        "item_name": [{"value": str(row.get('name', '')).strip(), "marketplace_id": AMZ_MARKETPLACE_ID}],
        "bullet_point": bullet_points,
        "product_description": [{"value": desc, "marketplace_id": AMZ_MARKETPLACE_ID}],
        "list_price": [{"value": price_val, "currency": "USD", "marketplace_id": AMZ_MARKETPLACE_ID}],
        "main_offer_image_locator": main_image,
        "fulfillment_availability": [{"fulfillmentChannelCode": "DEFAULT", "quantity": 0}],
    }
    if other_images:
        attributes["other_offer_image_locator"] = other_images
    if search_terms:
        attributes["generic_keyword"] = [{"value": " ".join(search_terms), "marketplace_id": AMZ_MARKETPLACE_ID}]

    return {
        "productType": "LAWN_AND_GARDEN",
        "requirements": "LISTING",
        "attributes": attributes,
    }


# ── SP-API push ───────────────────────────────────────────────────────────────
def push_listing(seller_id, sku, payload):
    """PUT listing to SP-API. Returns (success: bool, asin_or_error: str)."""
    safe_sku = requests.utils.quote(sku, safe='')
    path = f"/listings/items/{seller_id}/{safe_sku}"
    params = {"marketplaceIds": AMZ_MARKETPLACE_ID}
    # SP-API requires params in query string for PUT
    url = f"{SP_API_BASE}{path}?marketplaceIds={AMZ_MARKETPLACE_ID}"
    headers = {"x-amz-access-token": get_token(), "Content-Type": "application/json"}
    resp = requests.put(url, headers=headers, json=payload, timeout=30)
    time.sleep(2)  # 0.5 req/s rate limit

    if resp.status_code in (200, 201):
        data = resp.json()
        asin = data.get("asin") or data.get("sku", "")
        return True, asin
    else:
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
```

- [ ] **Step 4: Run tests — expect them to pass**

```bash
python -m pytest tests/test_push_amazon_drafts.py -v
```

Expected: All 6 tests pass.

- [ ] **Step 5: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add Amazonimprovement/push_amazon_drafts.py Amazonimprovement/tests/test_push_amazon_drafts.py
git commit -m "feat: add listing payload builder and SP-API push function"
```

---

## Task 5: Status CSV and Supabase Upsert

**Files:**
- Modify: `Amazonimprovement/push_amazon_drafts.py` (append functions)

- [ ] **Step 1: Append write_status_csv and supabase_upsert_queue to push_amazon_drafts.py**

```python
# ── Status output ─────────────────────────────────────────────────────────────
STATUS_FIELDNAMES = ['sku', 'title', 'status', 'missing_fields', 'image_count', 'asin', 'pushed_at', 'notes']

def write_status_csv(rows):
    with open(STATUS_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=STATUS_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Status CSV written: {STATUS_CSV}")


# ── Supabase upsert ───────────────────────────────────────────────────────────
def supabase_upsert_queue(rows):
    if not rows:
        return
    url = f"{SUPABASE_URL}/rest/v1/amazon_listing_queue?on_conflict=sku"
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    clean = [{k: v for k, v in r.items() if k not in ('created_at', 'updated_at')} for r in rows]
    resp = requests.post(url, headers=headers, json=clean, timeout=30)
    if resp.status_code not in (200, 201, 204):
        print(f"  [WARN] Supabase upsert failed: {resp.status_code} {resp.text[:200]}")
    else:
        print(f"  [OK] Upserted {len(clean)} rows into amazon_listing_queue")
```

- [ ] **Step 2: Verify import works**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/Amazonimprovement"
python -c "from push_amazon_drafts import write_status_csv, supabase_upsert_queue; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add Amazonimprovement/push_amazon_drafts.py
git commit -m "feat: add status CSV writer and Supabase upsert for listing queue"
```

---

## Task 6: Content Manager To-Do Generator

**Files:**
- Modify: `Amazonimprovement/push_amazon_drafts.py` (append function)
- Modify: `Amazonimprovement/tests/test_push_amazon_drafts.py` (add test)

- [ ] **Step 1: Write failing test for todo generator**

Append to `Amazonimprovement/tests/test_push_amazon_drafts.py`:

```python
def test_generate_todo_section_contains_required_fields():
    from push_amazon_drafts import generate_todo_section
    row = {
        'name': 'Perennial Ryegrass Seed',
        'sku': 'NS-PRG-5LB',
        'wc_url': 'https://naturesseed.com/perennial-ryegrass',
        'missing_fields': 'images,bullets',
        'image_count': '0',
        'description': 'Hardy perennial ryegrass ideal for overseeding and permanent lawns.',
        'bullets': 'Quick germination',
        'search_terms': 'ryegrass seed lawn',
        'images': '',
    }
    section = generate_todo_section(row)
    assert 'NS-PRG-5LB' in section
    assert 'Perennial Ryegrass Seed' in section
    assert 'naturesseed.com' in section
    assert 'Missing:' in section
    assert 'Shot List' in section
    assert 'A+ Content' in section
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/Amazonimprovement"
python -m pytest tests/test_push_amazon_drafts.py::test_generate_todo_section_contains_required_fields -v 2>&1 | head -15
```

Expected: `ImportError: cannot import name 'generate_todo_section'`

- [ ] **Step 3: Implement generate_todo_section and generate_content_todo**

Append to `Amazonimprovement/push_amazon_drafts.py`:

```python
# ── Content manager to-do ─────────────────────────────────────────────────────
def generate_todo_section(row):
    """Build a Markdown section for one product needing content."""
    name = str(row.get('name', 'Unknown Product')).strip()
    sku = str(row.get('sku', '')).strip()
    wc_url = str(row.get('wc_url', '')).strip()
    missing = str(row.get('missing_fields', '')).strip()
    image_count = str(row.get('image_count', '0')).strip()
    desc = re.sub(r'<[^>]+>', '', str(row.get('description', ''))).strip()
    bullets_raw = str(row.get('bullets', ''))
    bullet_lines = [b.strip() for b in bullets_raw.split('\n') if b.strip()]
    search_terms = str(row.get('search_terms', '')).strip()
    existing_images = [u.strip() for u in str(row.get('images', '')).split('|') if u.strip()]

    bullets_section = '\n'.join(f"{i+1}. {b}" for i, b in enumerate(bullet_lines)) if bullet_lines else '_None available — needs copywriter_'
    images_section = '\n'.join(f"- {u}" for u in existing_images) if existing_images else '_No images available_'

    return f"""
---

## {name} — SKU: `{sku}`

**WC Link:** {wc_url if wc_url else '_not available_'}
**Missing:** {missing if missing else 'none'}
**Available Images:** {image_count} ({images_section})
**Recommended Total:** 7 images

### Copy Reference (from WooCommerce)
{desc if desc else '_No description available_'}

### Bullets (existing or suggested)
{bullets_section}

### Keywords to Feature
{search_terms if search_terms else '_Pull from Amazon top listings in seed category_'}

### A+ Content Guideline
- **Module type:** Brand Story + Comparison Chart + 4-image text block
- **Tone:** Straightforward, farmer-trusted, science-backed (see Nature's Seed brand guide)
- **Key messages:** seeding rate, coverage area, germination speed, regional suitability
- **Comparison chart:** compare this SKU vs competing weights/mixes in the Nature's Seed line

### Image Shot List
- [ ] Hero: product bag on clean white background, full label visible
- [ ] Lifestyle: seed being spread on lawn / field context
- [ ] Infographic: coverage area (sq ft per lb), seeding rate, germination days
- [ ] Detail: seed closeup (macro)
- [ ] Before/After: bare soil → established turf (use existing if available)
- [ ] Regional map: ideal grow zones highlighted
- [ ] A+ banner: brand story image with Nature's Seed logo and tagline

"""


def generate_content_todo(incomplete_rows):
    header = f"""# Amazon Expansion — Content Manager To-Do
**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
**Products needing content:** {len(incomplete_rows)}

For each product below, create the listed assets and upload to the shared drive folder `Amazon New Listings / [SKU]`.
Once assets are ready, notify the Amazon team so listings can be pushed live.

"""
    sections = [generate_todo_section(r) for r in incomplete_rows]
    with open(TODO_MD, 'w') as f:
        f.write(header + '\n'.join(sections))
    print(f"  Content manager to-do written: {TODO_MD} ({len(incomplete_rows)} products)")
```

- [ ] **Step 4: Run all tests**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/Amazonimprovement"
python -m pytest tests/test_push_amazon_drafts.py -v
```

Expected: All 7 tests pass.

- [ ] **Step 5: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add Amazonimprovement/push_amazon_drafts.py Amazonimprovement/tests/test_push_amazon_drafts.py
git commit -m "feat: add content manager todo generator with per-product shot lists and A+ guidelines"
```

---

## Task 7: Main Orchestration and End-to-End Run

**Files:**
- Modify: `Amazonimprovement/push_amazon_drafts.py` (append `main()` and `__main__` block)

- [ ] **Step 1: Append main() to push_amazon_drafts.py**

```python
# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n=== Amazon Catalog Expansion — Draft Listing Push ===\n")

    # 1. Load missing products
    if not MISSING_CSV.exists():
        raise FileNotFoundError(f"Run amazon_wc_crossref.py first — {MISSING_CSV} not found")
    with open(MISSING_CSV, newline='') as f:
        candidates = list(csv.DictReader(f))
    print(f"Candidates from cross-ref: {len(candidates)}")

    # 2. Get seller ID once
    seller_id = get_seller_id()

    # 3. Process each candidate
    status_rows = []
    incomplete_rows = []
    pushed = 0
    skipped = 0
    errors = 0

    for i, row in enumerate(candidates):
        sku = str(row.get('sku', '')).strip()
        name = str(row.get('name', '')).strip()
        print(f"\n[{i+1}/{len(candidates)}] {sku} — {name[:60]}")

        result = check_completeness(row)
        images_raw = str(row.get('images', ''))
        image_urls = [u.strip() for u in images_raw.split('|') if u.strip()]
        image_count = len(image_urls)

        if result['ready']:
            payload = build_listing_payload(row)
            success, asin_or_err = push_listing(seller_id, sku, payload)
            if success:
                print(f"  [PUSHED] ASIN: {asin_or_err}")
                status_rows.append({
                    'sku': sku, 'title': name, 'status': 'drafted',
                    'missing_fields': '', 'image_count': image_count,
                    'asin': asin_or_err,
                    'pushed_at': datetime.utcnow().isoformat(),
                    'notes': '',
                })
                pushed += 1
            else:
                print(f"  [ERROR] {asin_or_err}")
                status_rows.append({
                    'sku': sku, 'title': name, 'status': 'error',
                    'missing_fields': '', 'image_count': image_count,
                    'asin': '',
                    'pushed_at': datetime.utcnow().isoformat(),
                    'notes': asin_or_err,
                })
                errors += 1
        else:
            missing_str = ','.join(result['missing'])
            print(f"  [SKIP] Missing: {missing_str}")
            row['missing_fields'] = missing_str
            row['image_count'] = str(image_count)
            incomplete_rows.append(row)
            status_rows.append({
                'sku': sku, 'title': name, 'status': 'needs-content',
                'missing_fields': missing_str, 'image_count': image_count,
                'asin': '',
                'pushed_at': '',
                'notes': f"Needs: {missing_str}",
            })
            skipped += 1

    # 4. Write outputs
    print(f"\n--- Summary ---")
    print(f"  Drafted:       {pushed}")
    print(f"  Needs content: {skipped}")
    print(f"  Errors:        {errors}")

    write_status_csv(status_rows)
    supabase_upsert_queue(status_rows)

    if incomplete_rows:
        generate_content_todo(incomplete_rows)
    else:
        print("  All products had complete content — no content manager to-do needed.")

    print("\nDone.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify all tests still pass**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/Amazonimprovement"
python -m pytest tests/test_push_amazon_drafts.py -v
```

Expected: All 7 tests pass.

- [ ] **Step 3: Dry-run — syntax check only**

```bash
python -c "import push_amazon_drafts; print('Syntax OK')"
```

Expected: `Syntax OK` and `Token acquired.` (token fetch runs at import due to global `_load_env()` call — this is expected).

- [ ] **Step 4: Run the full pipeline**

```bash
python push_amazon_drafts.py
```

Expected output (example):
```
=== Amazon Catalog Expansion — Draft Listing Push ===

  Refreshing LWA access token...
  Token acquired.
  Seller ID: ABCDEF1234567

Candidates from cross-ref: 24

[1/24] NS-KBG-5LB — Kentucky Bluegrass Seed 5 lb
  [PUSHED] ASIN: B0XXXXXXXXX

[2/24] NS-PRG-5LB — Perennial Ryegrass Seed 5 lb
  [SKIP] Missing: images,bullets

...

--- Summary ---
  Drafted:       12
  Needs content: 10
  Errors:        2

  Status CSV written: .../amazon_expansion_status.csv
  [OK] Upserted 24 rows into amazon_listing_queue
  Content manager to-do written: .../content_manager_todo.md (10 products)

Done.
```

- [ ] **Step 5: Inspect outputs**

```bash
python -c "
import csv
with open('amazon_expansion_status.csv') as f:
    rows = list(csv.DictReader(f))
drafted = [r for r in rows if r['status'] == 'drafted']
needs = [r for r in rows if r['status'] == 'needs-content']
errors = [r for r in rows if r['status'] == 'error']
print(f'Drafted: {len(drafted)}, Needs content: {len(needs)}, Errors: {len(errors)}')
"
```

```bash
head -60 content_manager_todo.md
```

- [ ] **Step 6: Review errors (if any)**

For each row with `status=error`, check the `notes` column. Common issues:
- `HTTP 400: INVALID_INPUT` → product type mismatch — note SKU for manual review
- `HTTP 403: UNAUTHORIZED` → token scope issue — verify SP-API role has Listings permission

- [ ] **Step 7: Final commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add Amazonimprovement/push_amazon_drafts.py \
        Amazonimprovement/amazon_expansion_status.csv \
        Amazonimprovement/content_manager_todo.md
git commit -m "feat: amazon catalog expansion — draft listings pushed, content todo generated"
```

---

## Notes for SP-API 400 Errors

If listings come back `HTTP 400 INVALID_INPUT`, the most common cause is product type. The `LAWN_AND_GARDEN` product type may require additional required attributes (brand, manufacturer). If this occurs, update `build_listing_payload` to add:

```python
"brand": [{"value": "Nature's Seed", "marketplace_id": AMZ_MARKETPLACE_ID}],
"manufacturer": [{"value": "Nature's Seed", "marketplace_id": AMZ_MARKETPLACE_ID}],
```

If still failing, retrieve the product type definition:
```bash
python -c "
from push_amazon_drafts import sp_get
r = sp_get('/definitions/2020-09-01/productTypes/LAWN_AND_GARDEN', params={'marketplaceIds': 'ATVPDKIKX0DER'})
import json; print(json.dumps(r.json(), indent=2)[:3000])
"
```
