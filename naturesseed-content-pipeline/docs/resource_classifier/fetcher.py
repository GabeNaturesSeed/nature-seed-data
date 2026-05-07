import httpx
from bs4 import BeautifulSoup


WP_POSTS_ENDPOINT = "https://naturesseed.com/wp-json/wp/v2/posts"


def strip_html(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


def parse_post(raw: dict) -> dict:
    return {
        "post_id": raw["id"],
        "title": BeautifulSoup(raw["title"]["rendered"], "html.parser").get_text(),
        "url": raw["link"],
        "content_html": raw["content"]["rendered"],
    }


def _get_page(page: int, env: dict) -> list[dict]:
    params = {"status": "publish", "per_page": 100, "page": page}
    url = WP_POSTS_ENDPOINT

    cf_url = env.get("CF_WORKER_URL", "").strip()
    cf_secret = env.get("CF_WORKER_SECRET", "").strip()
    ck = env.get("WC_CK", "").strip()
    cs = env.get("WC_CS", "").strip()

    if cf_url:
        # Build the full target URL with query params
        req = httpx.Request("GET", url, params=params)
        target_url = str(req.url)
        headers = {"X-Worker-Secret": cf_secret} if cf_secret else {}
        payload = {
            "url": target_url,
            "method": "GET",
            "auth": "basic",
            "username": ck,
            "password": cs,
        }
        resp = httpx.post(cf_url, json=payload, headers=headers, timeout=30)
    else:
        resp = httpx.get(url, params=params, auth=(ck, cs), timeout=30)

    resp.raise_for_status()
    return resp.json()


def fetch_all_posts(env: dict) -> list[dict]:
    """Fetch all published WP posts. Returns list of parsed post dicts."""
    posts = []
    page = 1
    while True:
        raw_posts = _get_page(page, env)
        if not raw_posts:
            break
        posts.extend(parse_post(p) for p in raw_posts)
        if len(raw_posts) < 100:
            break
        page += 1
    return posts
