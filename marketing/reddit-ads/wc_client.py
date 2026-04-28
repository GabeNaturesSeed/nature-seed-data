"""WooCommerce REST client for the Reddit catalog builder.

Routes through the CF Worker proxy when CF_WORKER_URL is set in the env
dict (required in CI to bypass Bot Fight Mode). Falls back to direct
WC API calls when not set (works from residential IPs).
"""
import base64
import time
import requests

PER_PAGE = 100
SLEEP_BETWEEN_CALLS = 0.3
MAX_RETRIES = 3
TIMEOUT = 30


def _auth_header(env):
    ck = env.get("WP_WOO_CONSUMER_KEY") or env["WC_CK"]
    cs = env.get("WP_WOO_CONSUMER_SECRET") or env["WC_CS"]
    token = base64.b64encode(f"{ck}:{cs}".encode()).decode()
    return f"Basic {token}"


def _request(env, wc_path, params):
    """Make one paginated request through the proxy if configured, else direct."""
    headers = {"Authorization": _auth_header(env)}
    if env.get("CF_WORKER_URL"):
        url = env["CF_WORKER_URL"]
        headers["X-Proxy-Secret"] = env["CF_WORKER_SECRET"]
        full_params = {"wc_path": wc_path, **params}
    else:
        url = env["WC_BASE_URL"].rstrip("/") + wc_path
        full_params = params

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, params=full_params, timeout=TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = 4 ** attempt  # 1, 4, 16
                print(f"  HTTP {resp.status_code} — retry in {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except (requests.ConnectionError, requests.Timeout) as e:
            wait = 4 ** attempt
            print(f"  Network error ({e!r}) — retry in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"WC request failed after {MAX_RETRIES} retries: {wc_path} {params}")


def fetch_products(env):
    """Yield every published product, paginated. Includes both simple and variable.

    We do NOT filter by stock_status here — the parent of a variable product
    can show 'outofstock' while a specific variation is in stock. The
    transform layer applies per-variation filtering.
    """
    page = 1
    while True:
        print(f"  Fetching products page {page}...")
        batch = _request(env, "/products", {
            "status": "publish",
            "per_page": PER_PAGE,
            "page": page,
        })
        if not batch:
            return
        for product in batch:
            yield product
        if len(batch) < PER_PAGE:
            return
        page += 1
        time.sleep(SLEEP_BETWEEN_CALLS)


def fetch_variations(env, product_id):
    """Return the full list of variations for one variable product."""
    variations = []
    page = 1
    while True:
        batch = _request(env, f"/products/{product_id}/variations", {
            "per_page": PER_PAGE,
            "page": page,
        })
        if not batch:
            break
        variations.extend(batch)
        if len(batch) < PER_PAGE:
            break
        page += 1
        time.sleep(SLEEP_BETWEEN_CALLS)
    return variations
