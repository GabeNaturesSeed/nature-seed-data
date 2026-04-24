"""Parse HTML and extract classified outbound links."""

from dataclasses import dataclass
from urllib.parse import urlparse

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ExtractedLink:
    href: str
    anchor_text: str
    link_type: str  # 'internal_content' | 'internal_product' | 'external' | 'anchor'


def classify_href(href: str, site_host: str) -> str:
    if not href:
        return "external"
    if href.startswith("#"):
        return "anchor"
    parsed = urlparse(href)
    path = parsed.path or ""
    host = parsed.netloc.lower()
    site_host = site_host.lower().lstrip("www.")

    is_internal = (host == "" or host == site_host or host == f"www.{site_host}")
    if not is_internal:
        return "external"
    if path.startswith("/products/") or path.startswith("/product/"):
        return "internal_product"
    return "internal_content"


def extract_links(html: str, site_host: str) -> list[ExtractedLink]:
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    seen: dict[str, ExtractedLink] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href in seen:
            continue
        anchor = a.get_text(separator=" ", strip=True)[:500]
        seen[href] = ExtractedLink(
            href=href,
            anchor_text=anchor,
            link_type=classify_href(href, site_host),
        )
    return list(seen.values())
