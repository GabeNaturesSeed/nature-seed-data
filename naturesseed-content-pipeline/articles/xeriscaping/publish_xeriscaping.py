"""Publish all 12 xeriscaping articles to WordPress."""

import sys
import os
import time
import tempfile
import urllib.request
from pathlib import Path

import yaml

# Ensure the src package is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from naturesseed_pipeline.integrations.wordpress import WordPressClient, markdown_to_html
from naturesseed_pipeline.config import Settings

ARTICLES_DIR = Path(__file__).parent / "md"
HERO_URL = "https://naturesseed.com/wp-content/uploads/2025/07/buffalograssfield.png"
HERO_ALT = "Drought-tolerant buffalograss lawn in dry summer landscape"
CATEGORY_NAME = "Xeriscaping"
CATEGORY_SLUG = "xeriscaping"
TAG_NAME = "xeriscape"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (meta, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.index("---", 3)
    raw_yaml = text[3:end].strip()
    body = text[end + 3:].lstrip("\n")
    meta = yaml.safe_load(raw_yaml)
    return meta, body


def get_or_create_category(wp: WordPressClient, name: str, slug: str) -> int:
    resp = wp._request("GET", "categories", params={"search": name})
    results = resp.json()
    for cat in results:
        if cat.get("slug") == slug or cat.get("name", "").lower() == name.lower():
            print(f"  Found existing category '{name}' (id={cat['id']})")
            return cat["id"]
    resp = wp._request("POST", "categories", json={"name": name, "slug": slug})
    cat = resp.json()
    print(f"  Created category '{name}' (id={cat['id']})")
    return cat["id"]


def get_or_create_tag(wp: WordPressClient, name: str) -> int:
    resp = wp._request("GET", "tags", params={"search": name})
    results = resp.json()
    for tag in results:
        if tag.get("name", "").lower() == name.lower():
            print(f"  Found existing tag '{name}' (id={tag['id']})")
            return tag["id"]
    resp = wp._request("POST", "tags", json={"name": name})
    tag = resp.json()
    print(f"  Created tag '{name}' (id={tag['id']})")
    return tag["id"]


def download_hero(url: str, dest: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0.0"})
    with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
        f.write(r.read())


def main() -> None:
    cfg = Settings()
    # cfg.wp_api_base is broken when wc_base_url already contains /wp-json/wc/v3.
    # Derive the correct WP REST base from the domain portion only.
    import re as _re
    m = _re.match(r"(https?://[^/]+)", cfg.wc_base_url)
    domain = m.group(1) if m else cfg.wc_base_url
    wp_api_base = f"{domain}/wp-json/wp/v2"
    wp = WordPressClient(wp_api_base, cfg.wp_username, cfg.wp_app_password)

    print("=== Xeriscaping Publisher ===\n")

    # 1. Category
    print("Step 1: Get/create category...")
    category_id = get_or_create_category(wp, CATEGORY_NAME, CATEGORY_SLUG)

    # 2. Tag
    print("Step 2: Get/create tag...")
    tag_id = get_or_create_tag(wp, TAG_NAME)

    # 3. Hero image
    print("Step 3: Downloading and uploading hero image...")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        download_hero(HERO_URL, tmp_path)
        media = wp.upload_media(tmp_path, title="Buffalograss Field Hero", alt_text=HERO_ALT)
        media_id = media["id"]
        print(f"  Uploaded hero image (media_id={media_id})")
    finally:
        os.unlink(tmp_path)

    # 4. Publish articles
    md_files = sorted(ARTICLES_DIR.glob("*.md"))
    print(f"\nStep 4: Publishing {len(md_files)} articles...\n")

    results = []
    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        title = meta.get("title", md_file.stem)
        slug = meta.get("slug", md_file.stem)
        description = meta.get("description", "")
        html = markdown_to_html(body)

        try:
            post = wp.create_post(
                title=title,
                content_html=html,
                slug=slug,
                excerpt=description,
                featured_media_id=media_id,
                categories=[category_id],
                tags=[tag_id],
                status="publish",
            )
            url = post.get("link", "")
            post_id = post.get("id", "")
            print(f"  PUBLISHED  {slug}  ->  {url}")
            results.append({"slug": slug, "status": "published", "url": url, "id": post_id})

        except Exception as exc:
            exc_str = str(exc)
            # Check for duplicate slug (WP returns 400 with rest_post_invalid_slug)
            if "rest_post_invalid_slug" in exc_str or "400" in exc_str:
                # Try to get more detail from the response
                err_code = "duplicate_slug"
                if hasattr(exc, "response") and exc.response is not None:
                    try:
                        err_body = exc.response.json()
                        if err_body.get("code") == "rest_post_invalid_slug":
                            err_code = "duplicate_slug"
                        else:
                            err_code = err_body.get("code", "http_400")
                    except Exception:
                        pass
                print(f"  SKIPPED    {slug}  (reason: {err_code})")
                results.append({"slug": slug, "status": "skipped", "reason": err_code})
            else:
                print(f"  ERROR      {slug}  ({exc_str[:120]})")
                results.append({"slug": slug, "status": "error", "reason": exc_str[:120]})

        time.sleep(0.4)

    # 5. Delivery table
    published = [r for r in results if r["status"] == "published"]
    skipped = [r for r in results if r["status"] == "skipped"]
    errors = [r for r in results if r["status"] == "error"]

    print("\n" + "=" * 70)
    print("DELIVERY TABLE")
    print("=" * 70)
    for r in results:
        if r["status"] == "published":
            print(f"  [OK]      {r['slug']}")
            print(f"            {r['url']}")
        elif r["status"] == "skipped":
            print(f"  [SKIP]    {r['slug']}  ({r['reason']})")
        else:
            print(f"  [ERROR]   {r['slug']}  ({r['reason']})")

    print("=" * 70)
    print(f"Total: {len(published)} of {len(md_files)} published successfully")
    if skipped:
        print(f"Skipped (duplicate slug): {len(skipped)}")
    if errors:
        print(f"Errors: {len(errors)}")
    print("=" * 70)

    wp.close()


if __name__ == "__main__":
    main()
