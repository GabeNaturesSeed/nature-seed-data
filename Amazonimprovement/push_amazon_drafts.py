import os, csv, json, time, re, requests
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
ENV_PATH = PROJECT_DIR / ".env"
MISSING_CSV = SCRIPT_DIR / "amazon_missing_products.csv"
STATUS_CSV = SCRIPT_DIR / "amazon_expansion_status.csv"
TODO_MD = SCRIPT_DIR / "content_manager_todo.md"

# ── Env ───────────────────────────────────────────────────────────────────────
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

# ── SP-API helpers ─────────────────────────────────────────────────────────────
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

# ── Seller ID ──────────────────────────────────────────────────────────────────
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

# ── Completeness check ─────────────────────────────────────────────────────────
def check_completeness(row):
    """Return {'ready': bool, 'missing': [field_names]}.

    CSV columns: product_name, parent_sku, bullet_1..bullet_5,
    description_plain, image_1..image_5, price, search_terms, wc_url
    """
    missing = []
    if not str(row.get('product_name', '')).strip():
        missing.append('title')
    bullets = [str(row.get(f'bullet_{i}', '')).strip() for i in range(1, 6)]
    if len([b for b in bullets if b]) < 5:
        missing.append('bullets')
    desc = str(row.get('description_plain', '')).strip()
    if len(desc) < 50:
        missing.append('description')
    if not str(row.get('image_1', '')).strip():
        missing.append('images')
    try:
        price = float(str(row.get('price', '0')).replace('$', '').strip())
    except (ValueError, TypeError):
        price = 0
    if price <= 0:
        missing.append('price')
    return {'ready': len(missing) == 0, 'missing': missing}
