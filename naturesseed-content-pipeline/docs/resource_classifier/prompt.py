import json
from bs4 import BeautifulSoup


def _truncate(html: str, max_chars: int = 4000) -> str:
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)
    return text[:max_chars]


def build_prompt(batch: list[dict]) -> str:
    articles = [
        {
            "post_id": a["post_id"],
            "title": a["title"],
            "url": a["url"],
            "body": _truncate(a["content_html"]),
        }
        for a in batch
    ]
    articles_json = json.dumps(articles, indent=2)

    return f"""You are classifying Nature's Seed blog/resource articles for a content taxonomy.

Return a JSON array — one object per article. Each object must have exactly these keys:

{{
  "post_id": <integer>,
  "topics": [
    {{"category": "<string>", "subcategory": "<string>"}}
  ],
  "species_mentioned": ["<common or Latin name>"],
  "products_mentioned": [
    {{"name": "<product name>", "slug_if_known": "<slug or null>", "has_link": <true|false>}}
  ]
}}

Rules:
- Assign UNLIMITED topics per article — be generous. If an article covers 3 topics, list 3.
- category = broad topic (e.g. "Lawn Care", "Wildflowers", "Pasture Management", "Water Conservation")
- subcategory = specific angle (e.g. "Overseeding", "Native Species Selection", "Drought Tolerance")
- species_mentioned = any seed species by common OR Latin name. Empty array if none.
- products_mentioned = any specific product or seed mix mentioned. has_link = true if it appears inside an <a> tag in the original HTML. Empty array if none.
- Return ONLY the JSON array. No explanation, no markdown fences.

<articles>
{articles_json}
</articles>"""
