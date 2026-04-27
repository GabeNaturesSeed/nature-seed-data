"""WordPress and WooCommerce REST API clients with pagination and retry."""

import time
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from naturesseed_pipeline.config import settings

log = structlog.get_logger()

MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0  # seconds


def _html_to_text(html: str) -> str:
    """Strip HTML tags, return plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


class _BaseClient:
    """Shared pagination + retry logic for WP/WC REST APIs."""

    def __init__(self, base_url: str, auth: tuple[str, str]) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = auth
        # Cloudflare Bot Fight Mode on naturesseed.com blocks the default
        # python-httpx / requests User-Agent. A curl-like UA passes through.
        self._client = httpx.Client(
            timeout=30.0,
            headers={"User-Agent": "curl/8.0.0", "Accept": "*/*"},
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self._base_url}/{path.lstrip('/')}"
        backoff = INITIAL_BACKOFF
        for attempt in range(MAX_RETRIES):
            resp = self._client.request(method, url, auth=self._auth, **kwargs)
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = backoff * (2**attempt)
                log.warning("retrying", url=url, status=resp.status_code, wait=wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        resp.raise_for_status()
        return resp  # unreachable but satisfies type checker

    def _paginate(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Fetch all pages using X-WP-TotalPages header."""
        params = dict(params or {})
        params.setdefault("per_page", 100)
        params["page"] = 1
        all_items: list[dict[str, Any]] = []

        while True:
            resp = self._request("GET", path, params=params)
            items = resp.json()
            if not isinstance(items, list):
                break
            all_items.extend(items)

            total_pages = int(resp.headers.get("X-WP-TotalPages", "1"))
            if params["page"] >= total_pages:
                break
            params["page"] += 1

        return all_items

    def close(self) -> None:
        self._client.close()


class WordPressClient(_BaseClient):
    """WP REST API — posts, pages, media."""

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        app_password: str | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url or settings.wp_api_base,
            auth=(username or settings.wp_username, app_password or settings.wp_app_password),
        )

    def list_posts(
        self, status: str = "any", since: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"status": status}
        if since:
            params["modified_after"] = f"{since}T00:00:00"
        return self._paginate("posts", params)

    def list_pages(
        self, status: str = "any", since: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"status": status}
        if since:
            params["modified_after"] = f"{since}T00:00:00"
        return self._paginate("pages", params)

    def list_media(self) -> list[dict[str, Any]]:
        return self._paginate("media")

    def update_post_status(self, post_id: int, status: str) -> dict[str, Any]:
        resp = self._request("POST", f"posts/{post_id}", json={"status": status})
        return resp.json()

    def create_post(
        self,
        title: str,
        content_html: str,
        slug: str,
        excerpt: str = "",
        meta_description: str = "",
        featured_media_id: int | None = None,
        categories: list[int] | None = None,
        tags: list[int] | None = None,
        status: str = "future",
        scheduled_for: str | None = None,
    ) -> dict[str, Any]:
        """Create a WP post. status='future' for scheduled publishing."""
        payload: dict[str, Any] = {
            "title": title,
            "content": content_html,
            "slug": slug,
            "excerpt": excerpt,
            "status": status,
        }
        if featured_media_id:
            payload["featured_media"] = featured_media_id
        if categories:
            payload["categories"] = categories
        if tags:
            payload["tags"] = tags
        if scheduled_for and status == "future":
            payload["date"] = scheduled_for

        resp = self._request("POST", "posts", json=payload)
        return resp.json()

    def update_post(
        self,
        post_id: int,
        title: str | None = None,
        content_html: str | None = None,
        excerpt: str | None = None,
        featured_media_id: int | None = None,
    ) -> dict[str, Any]:
        """Update an existing WP post (for refreshes)."""
        payload: dict[str, Any] = {}
        if title:
            payload["title"] = title
        if content_html:
            payload["content"] = content_html
        if excerpt:
            payload["excerpt"] = excerpt
        if featured_media_id:
            payload["featured_media"] = featured_media_id
        resp = self._request("POST", f"posts/{post_id}", json=payload)
        return resp.json()

    def upload_media(
        self,
        file_path: str,
        title: str = "",
        alt_text: str = "",
    ) -> dict[str, Any]:
        """Upload a file to WP media library. Returns media dict with id."""
        import mimetypes
        from pathlib import Path

        path = Path(file_path)
        mime_type = mimetypes.guess_type(str(path))[0] or "image/webp"

        with open(path, "rb") as f:
            resp = self._request(
                "POST",
                "media",
                content=f.read(),
                headers={
                    "Content-Disposition": f'attachment; filename="{path.name}"',
                    "Content-Type": mime_type,
                },
            )
        result = resp.json()

        # Set alt text if provided
        if alt_text and result.get("id"):
            self._request("POST", f"media/{result['id']}", json={
                "alt_text": alt_text,
                "title": title or path.stem,
            })

        return result


class WooCommerceClient(_BaseClient):
    """WC REST API v3 — products."""

    def __init__(
        self,
        base_url: str | None = None,
        consumer_key: str | None = None,
        consumer_secret: str | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url or settings.wc_api_base,
            auth=(consumer_key or settings.wc_ck, consumer_secret or settings.wc_cs),
        )

    def list_products(self, status: str = "publish") -> list[dict[str, Any]]:
        return self._paginate("products", {"status": status})

    def list_all_products(self) -> list[dict[str, Any]]:
        """All products regardless of status."""
        return self._paginate("products", {"status": "any"})


def html_to_text(html: str) -> str:
    """Public export of HTML stripper."""
    return _html_to_text(html)


def markdown_to_html(md_content: str) -> str:
    """Convert markdown to HTML using markdown-it-py with footnotes + GFM tables."""
    from markdown_it import MarkdownIt
    from mdit_py_plugins.footnote import footnote_plugin

    mdit = MarkdownIt("gfm-like", {"html": True})
    footnote_plugin(mdit)
    return mdit.render(md_content)
