"""
WordPress REST API client for Nature's Seed.

Handles both WooCommerce API (products) and WordPress core API (posts, media).
Routes through Cloudflare Worker proxy when CF_WORKER_URL is set.
"""

import os
import time
import base64
import requests
from urllib.parse import urlencode

WP_BASE = "https://naturesseed.com/wp-json"
WC_V3 = f"{WP_BASE}/wc/v3"
WP_V2 = f"{WP_BASE}/wp/v2"

# Auth
WC_CK = os.getenv("WC_CK", "")
WC_CS = os.getenv("WC_CS", "")
WP_USER = os.getenv("WP_APP_USER", "")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")

# Cloudflare Worker proxy (for GET requests that hit Bot Fight Mode)
CF_WORKER_URL = os.getenv("CF_WORKER_URL", "")
CF_WORKER_SECRET = os.getenv("CF_WORKER_SECRET", "")


def _wc_auth_header():
    token = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _wp_auth_header():
    token = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _use_proxy():
    return bool(CF_WORKER_URL and CF_WORKER_SECRET)


# ── WooCommerce reads (products, categories) ──────────────────────────

def wc_get(endpoint, params=None):
    """GET from WooCommerce REST API v3. Uses CF Worker proxy if available."""
    if _use_proxy():
        proxy_params = {"wc_path": f"/{endpoint}"}
        if params:
            proxy_params.update(params)
        url = f"https://{CF_WORKER_URL}?{urlencode(proxy_params)}"
        headers = {
            "X-Proxy-Secret": CF_WORKER_SECRET,
            **_wc_auth_header(),
        }
        r = requests.get(url, headers=headers, timeout=30)
    else:
        url = f"{WC_V3}/{endpoint}"
        r = requests.get(url, auth=(WC_CK, WC_CS), params=params, timeout=30)
    r.raise_for_status()
    return r.json(), r.headers


def wc_get_all(endpoint, params=None):
    """Paginate through all WooCommerce results."""
    params = params or {}
    params["per_page"] = 100
    page = 1
    all_items = []
    while True:
        params["page"] = page
        items, headers = wc_get(endpoint, params)
        if not items:
            break
        all_items.extend(items)
        total_pages = int(headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)
    return all_items


# ── WordPress core reads (media, posts) ───────────────────────────────

def wp_get(endpoint, params=None):
    """GET from WordPress REST API v2."""
    url = f"{WP_V2}/{endpoint}"
    headers = _wp_auth_header() if WP_USER else {}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json(), r.headers


def wp_post(endpoint, data=None, json_data=None, files=None):
    """POST to WordPress REST API v2 (create posts, upload media)."""
    url = f"{WP_V2}/{endpoint}"
    headers = _wp_auth_header()
    if files:
        r = requests.post(url, headers=headers, data=data, files=files, timeout=60)
    else:
        headers["Content-Type"] = "application/json"
        r = requests.post(url, headers=headers, json=json_data, timeout=30)
    r.raise_for_status()
    return r.json()


def wp_put(endpoint, json_data):
    """PUT to WordPress REST API v2 (update posts)."""
    url = f"{WP_V2}/{endpoint}"
    headers = {**_wp_auth_header(), "Content-Type": "application/json"}
    r = requests.put(url, headers=headers, json=json_data, timeout=30)
    r.raise_for_status()
    return r.json()


# ── Media search ──────────────────────────────────────────────────────

def search_media(search_term, per_page=20):
    """Search WordPress media library by filename/title/alt text."""
    params = {
        "search": search_term,
        "per_page": per_page,
        "media_type": "image",
    }
    items, _ = wp_get("media", params)
    results = []
    for item in items:
        results.append({
            "id": item["id"],
            "title": item.get("title", {}).get("rendered", ""),
            "alt_text": item.get("alt_text", ""),
            "url": item.get("source_url", ""),
            "thumbnail": item.get("media_details", {}).get("sizes", {}).get("thumbnail", {}).get("source_url", ""),
            "medium": item.get("media_details", {}).get("sizes", {}).get("medium", {}).get("source_url", ""),
            "width": item.get("media_details", {}).get("width", 0),
            "height": item.get("media_details", {}).get("height", 0),
        })
    return results


# ── Product helpers ───────────────────────────────────────────────────

def get_products(category_id=None, per_page=100):
    """Get published products, optionally filtered by category."""
    params = {"status": "publish", "per_page": per_page}
    if category_id:
        params["category"] = category_id
    return wc_get("products", params)[0]


def get_categories():
    """Get all product categories."""
    return wc_get_all("products/categories")


def get_product_by_slug(slug):
    """Find a product by its slug."""
    items, _ = wc_get("products", {"slug": slug})
    return items[0] if items else None


# ── Post publishing ───────────────────────────────────────────────────

def create_post(title, content, status="draft", categories=None, tags=None,
                featured_media=None, meta=None):
    """Create a WordPress post."""
    data = {
        "title": title,
        "content": content,
        "status": status,
    }
    if categories:
        data["categories"] = categories
    if tags:
        data["tags"] = tags
    if featured_media:
        data["featured_media"] = featured_media
    if meta:
        data["meta"] = meta
    return wp_post("posts", json_data=data)


def update_post(post_id, **kwargs):
    """Update an existing WordPress post."""
    return wp_put(f"posts/{post_id}", json_data=kwargs)


def get_posts(per_page=20, status="any", search=None):
    """List WordPress posts."""
    params = {"per_page": per_page, "status": status}
    if search:
        params["search"] = search
    items, _ = wp_get("posts", params)
    return items
