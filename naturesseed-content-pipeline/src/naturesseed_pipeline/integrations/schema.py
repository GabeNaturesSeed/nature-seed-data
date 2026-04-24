"""Schema markup (JSON-LD) injector for SEO.

Auto-detects article type and generates appropriate structured data:
- Article (default)
- HowTo (if step-by-step patterns detected)
- FAQPage (if FAQ section detected)
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any


def detect_schema_type(html_content: str) -> str:
    """Auto-detect article type from content patterns."""
    lower = html_content.lower()

    # FAQ detection: look for FAQ heading + question patterns
    if re.search(r"<h[23][^>]*>\s*(?:faq|frequently asked)", lower):
        return "FAQPage"

    # HowTo detection: look for numbered steps or "step N" patterns
    step_count = len(re.findall(r"(?:step\s+\d|<li>|<ol>)", lower))
    if step_count >= 3 and re.search(r"(?:how to|guide|tutorial|instructions)", lower):
        return "HowTo"

    return "Article"


def _extract_faq_items(html_content: str) -> list[dict[str, str]]:
    """Extract Q&A pairs from FAQ sections."""
    items: list[dict[str, str]] = []
    # Match patterns like <h3>Question?</h3> followed by <p>Answer</p>
    pattern = re.compile(
        r"<h[34][^>]*>(.*?)</h[34]>\s*<p>(.*?)</p>",
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(html_content):
        q = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        a = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if q and a:
            items.append({"question": q, "answer": a})
    return items[:10]


def _extract_howto_steps(html_content: str) -> list[dict[str, str]]:
    """Extract how-to steps from ordered lists or step patterns."""
    steps: list[dict[str, str]] = []
    # Look for <li> items after a "how to" or "steps" heading
    li_pattern = re.compile(r"<li>(.*?)</li>", re.DOTALL | re.IGNORECASE)
    for m in li_pattern.finditer(html_content):
        text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if text and len(text) > 10:
            steps.append({"text": text})
    return steps[:20]


def generate_schema(
    html_content: str,
    title: str,
    description: str = "",
    url: str = "",
    author: str = "Nature's Seed",
    publisher: str = "Nature's Seed",
    published_date: str | None = None,
    modified_date: str | None = None,
    image_url: str | None = None,
) -> str:
    """Generate JSON-LD schema markup based on content type.

    Returns a <script type="application/ld+json"> block ready to inject.
    """
    schema_type = detect_schema_type(html_content)
    now_iso = datetime.now(timezone.utc).isoformat()

    if schema_type == "FAQPage":
        faq_items = _extract_faq_items(html_content)
        schema: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": item["answer"],
                    },
                }
                for item in faq_items
            ],
        }

    elif schema_type == "HowTo":
        steps = _extract_howto_steps(html_content)
        schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": title,
            "description": description,
            "step": [
                {
                    "@type": "HowToStep",
                    "text": step["text"],
                    "position": i + 1,
                }
                for i, step in enumerate(steps)
            ],
        }
        if image_url:
            schema["image"] = image_url

    else:  # Article
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": description,
            "author": {"@type": "Organization", "name": author},
            "publisher": {
                "@type": "Organization",
                "name": publisher,
                "url": "https://www.naturesseed.com",
            },
            "datePublished": published_date or now_iso,
            "dateModified": modified_date or now_iso,
        }
        if url:
            schema["url"] = url
        if image_url:
            schema["image"] = image_url

    json_str = json.dumps(schema, indent=2, ensure_ascii=False)
    return f'\n<script type="application/ld+json">\n{json_str}\n</script>'


def inject_schema(html_content: str, schema_block: str) -> str:
    """Inject schema block at the end of HTML content."""
    return html_content + schema_block
