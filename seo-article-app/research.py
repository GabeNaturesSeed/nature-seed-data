"""
SEO Keyword Research Engine for Nature's Seed.

Pulls data from Google Search Console, analyzes WooCommerce product catalog,
and uses Claude to identify high-intent article opportunities.
"""

import os
import json
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Google OAuth (shared 4-scope token)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")

SITE_URL = "sc-domain:naturesseed.com"
SC_API = "https://www.googleapis.com/webmasters/v3"

# Nature's Seed product verticals for content mapping
CONTENT_VERTICALS = {
    "lawn": {
        "category_ids": [3881, 4618, 4621, 4623, 4622, 4614, 4617],
        "seed_keywords": [
            "lawn seed", "grass seed", "lawn care", "overseeding",
            "lawn renovation", "water-wise lawn", "sports turf",
            "northern lawn", "southern lawn", "transitional lawn",
        ],
    },
    "pasture": {
        "category_ids": [3897, 4613, 4616, 4615, 3915, 4706, 3910, 3927, 3916],
        "seed_keywords": [
            "pasture seed", "horse pasture", "cattle pasture",
            "goat pasture", "sheep pasture", "forage seed",
            "hay field", "grazing mix", "pasture renovation",
        ],
    },
    "wildflower": {
        "category_ids": [3896],
        "seed_keywords": [
            "wildflower seed", "wildflower mix", "native wildflower",
            "pollinator garden", "meadow seed", "wildflower planting",
        ],
    },
    "california": {
        "category_ids": [4035],
        "seed_keywords": [
            "california wildflower", "california native plants",
            "california poppy", "drought tolerant seed",
        ],
    },
    "clover": {
        "category_ids": [4688],
        "seed_keywords": [
            "clover seed", "white clover lawn", "clover lawn alternative",
            "micro clover", "crimson clover",
        ],
    },
    "food_plot": {
        "category_ids": [6000],
        "seed_keywords": [
            "food plot seed", "deer food plot", "wildlife food plot",
            "hunting food plot", "turkey food plot",
        ],
    },
    "cover_crop": {
        "category_ids": [6002],
        "seed_keywords": [
            "cover crop seed", "green manure", "winter cover crop",
            "nitrogen fixer", "soil improvement",
        ],
    },
}


def _get_google_credentials():
    """Build Google OAuth credentials from refresh token."""
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )
    creds.refresh(Request())
    return creds


def fetch_search_console_queries(days=90, row_limit=500):
    """Pull top queries from Google Search Console."""
    creds = _get_google_credentials()
    url = f"{SC_API}/sites/{SITE_URL}/searchAnalytics/query"
    headers = {"Authorization": f"Bearer {creds.token}"}

    from datetime import datetime, timedelta
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query"],
        "rowLimit": row_limit,
        "dimensionFilterGroups": [],
    }

    r = requests.post(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    data = r.json()

    queries = []
    for row in data.get("rows", []):
        queries.append({
            "query": row["keys"][0],
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": round(row.get("ctr", 0) * 100, 2),
            "position": round(row.get("position", 0), 1),
        })

    return queries


def fetch_page_performance(days=90, row_limit=200):
    """Pull top pages from Google Search Console."""
    creds = _get_google_credentials()
    url = f"{SC_API}/sites/{SITE_URL}/searchAnalytics/query"
    headers = {"Authorization": f"Bearer {creds.token}"}

    from datetime import datetime, timedelta
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["page"],
        "rowLimit": row_limit,
    }

    r = requests.post(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    data = r.json()

    pages = []
    for row in data.get("rows", []):
        pages.append({
            "page": row["keys"][0],
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": round(row.get("ctr", 0) * 100, 2),
            "position": round(row.get("position", 0), 1),
        })
    return pages


def classify_query_intent(query):
    """Classify a search query by purchase intent."""
    high_intent = ["buy", "price", "cost", "order", "shop", "sale", "discount",
                   "best", "near me", "delivery", "ship", "lb", "pound",
                   "how much", "where to buy", "for sale"]
    medium_intent = ["seed", "mix", "blend", "variety", "type", "vs",
                     "review", "compare", "recommend"]
    low_intent = ["what is", "how to", "when to", "can i", "does", "will",
                  "why", "guide", "tips", "ideas"]

    q = query.lower()
    if any(kw in q for kw in high_intent):
        return "high"
    if any(kw in q for kw in medium_intent):
        return "medium"
    if any(kw in q for kw in low_intent):
        return "informational"
    return "medium"


def score_keyword_opportunity(query_data):
    """Score a keyword for article opportunity (0-100)."""
    score = 0
    q = query_data

    # High impressions but low clicks = content gap opportunity
    if q["impressions"] > 100 and q["ctr"] < 3:
        score += 30
    elif q["impressions"] > 50:
        score += 15

    # Position 5-20 = striking distance (can improve with content)
    if 5 <= q["position"] <= 20:
        score += 25
    elif 3 <= q["position"] < 5:
        score += 15

    # Intent scoring
    intent = classify_query_intent(q["query"])
    if intent == "high":
        score += 30
    elif intent == "medium":
        score += 20
    elif intent == "informational":
        score += 10

    # Longer queries tend to be more specific/easier to rank
    word_count = len(q["query"].split())
    if word_count >= 4:
        score += 10
    elif word_count >= 3:
        score += 5

    return min(score, 100)


def find_content_gaps(queries, existing_pages):
    """Find queries with high impressions that don't have dedicated content."""
    existing_slugs = set()
    for page in existing_pages:
        slug = page["page"].rstrip("/").split("/")[-1]
        existing_slugs.add(slug.lower())

    gaps = []
    for q in queries:
        query_words = set(q["query"].lower().split())
        # Check if any existing page targets this query
        has_content = any(
            word in slug for slug in existing_slugs
            for word in query_words if len(word) > 3
        )
        if not has_content:
            q["opportunity_score"] = score_keyword_opportunity(q)
            q["intent"] = classify_query_intent(q["query"])
            gaps.append(q)

    return sorted(gaps, key=lambda x: x["opportunity_score"], reverse=True)


def map_query_to_vertical(query):
    """Map a search query to a Nature's Seed product vertical."""
    q = query.lower()
    for vertical, config in CONTENT_VERTICALS.items():
        if any(kw in q for kw in config["seed_keywords"]):
            return vertical
    return "general"


def generate_topic_suggestions(queries, pages, limit=20):
    """Generate article topic suggestions from Search Console data."""
    gaps = find_content_gaps(queries, pages)

    suggestions = []
    for gap in gaps[:limit]:
        vertical = map_query_to_vertical(gap["query"])
        suggestions.append({
            "topic": gap["query"],
            "vertical": vertical,
            "category_ids": CONTENT_VERTICALS.get(vertical, {}).get("category_ids", []),
            "opportunity_score": gap["opportunity_score"],
            "intent": gap["intent"],
            "current_position": gap["position"],
            "impressions": gap["impressions"],
            "clicks": gap["clicks"],
            "ctr": gap["ctr"],
        })

    return suggestions


def run_full_research():
    """Run complete keyword research pipeline."""
    try:
        queries = fetch_search_console_queries(days=90, row_limit=500)
        pages = fetch_page_performance(days=90, row_limit=200)
        suggestions = generate_topic_suggestions(queries, pages, limit=30)
        return {
            "total_queries_analyzed": len(queries),
            "total_pages": len(pages),
            "suggestions": suggestions,
        }
    except Exception as e:
        # If Search Console is unavailable, fall back to seed keywords
        return _fallback_research(str(e))


def _fallback_research(error_msg):
    """Generate suggestions from seed keywords when API is unavailable."""
    suggestions = []
    priority_topics = [
        {"topic": "best grass seed for shade", "vertical": "lawn", "intent": "high", "opportunity_score": 85},
        {"topic": "when to plant pasture seed", "vertical": "pasture", "intent": "informational", "opportunity_score": 80},
        {"topic": "how to plant wildflower seeds", "vertical": "wildflower", "intent": "informational", "opportunity_score": 78},
        {"topic": "clover lawn pros and cons", "vertical": "clover", "intent": "medium", "opportunity_score": 82},
        {"topic": "best food plot seed for deer", "vertical": "food_plot", "intent": "high", "opportunity_score": 88},
        {"topic": "horse pasture seed mix guide", "vertical": "pasture", "intent": "high", "opportunity_score": 86},
        {"topic": "california native wildflower planting guide", "vertical": "california", "intent": "medium", "opportunity_score": 75},
        {"topic": "cover crop benefits for gardens", "vertical": "cover_crop", "intent": "informational", "opportunity_score": 70},
        {"topic": "how to overseed a lawn", "vertical": "lawn", "intent": "informational", "opportunity_score": 77},
        {"topic": "drought tolerant grass seed", "vertical": "lawn", "intent": "high", "opportunity_score": 84},
        {"topic": "best pasture grass for cattle", "vertical": "pasture", "intent": "high", "opportunity_score": 83},
        {"topic": "wildflower meadow establishment guide", "vertical": "wildflower", "intent": "informational", "opportunity_score": 72},
        {"topic": "pollinator garden seed mix", "vertical": "wildflower", "intent": "high", "opportunity_score": 79},
        {"topic": "winter cover crop seed selection", "vertical": "cover_crop", "intent": "medium", "opportunity_score": 74},
        {"topic": "lawn alternatives that save water", "vertical": "lawn", "intent": "medium", "opportunity_score": 81},
    ]

    for topic in priority_topics:
        vertical = topic["vertical"]
        topic["category_ids"] = CONTENT_VERTICALS.get(vertical, {}).get("category_ids", [])
        topic["current_position"] = None
        topic["impressions"] = None
        topic["clicks"] = None
        topic["ctr"] = None
        suggestions.append(topic)

    return {
        "total_queries_analyzed": 0,
        "total_pages": 0,
        "suggestions": suggestions,
        "note": f"Using seed keyword suggestions (Search Console unavailable: {error_msg})",
    }
