#!/usr/bin/env python3
"""
Algolia Auto-Synonym Review
============================
Pulls no-result queries from Algolia analytics, finds intelligent mappings,
and pushes new synonyms automatically. Sends a summary to Telegram.

Runs daily via GitHub Actions or local cron.

Strategy:
1. Pull no-result queries from last 7 days
2. Skip queries that already have synonyms or < 2 searches
3. For each unhandled query:
   a. Try a relaxed search (typoTolerance=max, removeWordsIfNoResults=allOptional)
   b. If good matches found → create oneWaySynonym to those product categories
   c. If no matches → classify as "not carried" and map to nearest category
4. Push new synonyms
5. Send Telegram summary

Usage:
    python3 auto_synonym_review.py              # Dry run
    python3 auto_synonym_review.py --push       # Push + notify
    python3 auto_synonym_review.py --push --no-telegram  # Push without notification
"""

import json
import os
import re
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    os.system("pip3 install requests")
    import requests

# ─── Config ───────────────────────────────────────────────────────────

# Load from env or fallback to defaults
APP_ID = os.environ.get("ALGOLIA_APP_ID", "CR7906DEBT")
ADMIN_KEY = os.environ.get("ALGOLIA_ADMIN_API_KEY", "48fa3067eaffd3b69093b3311a30b357")
SEARCH_KEY = os.environ.get("ALGOLIA_SEARCH_API_KEY", "e873ad4081aaea5a24e840ff99a13e51")
INDEX_NAME = "wp_prod_posts_product"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_API", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

BASE_URL = f"https://{APP_ID}-dsn.algolia.net"
ANALYTICS_URL = "https://analytics.us.algolia.com"

HEADERS_ADMIN = {
    "X-Algolia-API-Key": ADMIN_KEY,
    "X-Algolia-Application-Id": APP_ID,
    "Content-Type": "application/json",
}
HEADERS_SEARCH = {
    "X-Algolia-API-Key": SEARCH_KEY,
    "X-Algolia-Application-Id": APP_ID,
    "Content-Type": "application/json",
}

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Minimum searches before we act on a no-result query
MIN_SEARCHES = 2

# Category keywords for intelligent mapping
CATEGORY_MAP = {
    "lawn": ["lawn", "turf", "yard", "grass seed", "sod"],
    "pasture": ["pasture", "forage", "grazing", "hay", "livestock"],
    "wildflower": ["wildflower", "flower", "bloom", "native wildflower"],
    "clover": ["clover", "legume", "nitrogen"],
    "cover crop": ["cover crop", "green manure"],
    "food plot": ["food plot", "deer", "hunting", "game"],
    "planting aid": ["fertilizer", "tackifier", "rice hulls", "soil"],
    "native grass": ["native grass", "prairie", "restoration"],
    "erosion": ["erosion", "slope", "hillside", "stabiliz"],
    "pollinator": ["pollinator", "bee", "butterfly", "monarch"],
    "shade": ["shade", "shady", "low light"],
    "drought": ["drought", "dry", "xeriscape", "water wise"],
}

# Known non-seed terms that we should always redirect
NOT_SEED_TERMS = {
    "mushroom", "tomato", "vegetable", "herb", "cannabis", "marijuana",
    "weed killer", "roundup", "fertilizer spreader", "mower", "tractor",
    "soil test", "gypsum", "lime", "peat moss", "coconut coir",
    "compost", "mulch bag", "landscape fabric", "edging",
}


def log(msg):
    print(f"  {msg}")


# ─── Algolia API helpers ──────────────────────────────────────────────

def get_no_result_queries(days=7):
    """Pull no-result queries from analytics."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    r = requests.get(
        f"{ANALYTICS_URL}/2/searches/noResults",
        headers=HEADERS_ADMIN,
        params={
            "index": INDEX_NAME,
            "startDate": start_date,
            "endDate": end_date,
            "limit": 100,
        },
    )
    r.raise_for_status()
    return r.json().get("searches", [])


def get_existing_synonyms():
    """Get all existing synonym inputs/terms to avoid duplicates."""
    existing = set()
    page = 0
    while True:
        r = requests.post(
            f"{BASE_URL}/1/indexes/{INDEX_NAME}/synonyms/search",
            headers=HEADERS_ADMIN,
            json={"query": "", "hitsPerPage": 100, "page": page},
        )
        r.raise_for_status()
        data = r.json()
        hits = data.get("hits", [])
        if not hits:
            break

        for syn in hits:
            # Track all terms covered by existing synonyms
            if syn.get("type") == "synonym":
                for s in syn.get("synonyms", []):
                    existing.add(s.lower().strip())
            elif syn.get("type") == "oneWaySynonym":
                existing.add(syn.get("input", "").lower().strip())
            existing.add(syn.get("objectID", "").lower())

        page += 1
        if page * 100 >= data.get("nbHits", 0):
            break

    # Also load existing rules — queries handled by rules still show in
    # no-result analytics because the rule rewrites the query
    r = requests.post(
        f"{BASE_URL}/1/indexes/{INDEX_NAME}/rules/search",
        headers=HEADERS_ADMIN,
        json={"query": "", "hitsPerPage": 100},
    )
    r.raise_for_status()
    for rule in r.json().get("hits", []):
        pattern = rule.get("condition", {}).get("pattern", "").lower().strip()
        if pattern:
            existing.add(pattern)

    return existing


def relaxed_search(query):
    """Search with maximum typo tolerance and word removal to find potential matches."""
    r = requests.post(
        f"{BASE_URL}/1/indexes/{INDEX_NAME}/query",
        headers=HEADERS_SEARCH,
        json={
            "query": query,
            "hitsPerPage": 5,
            "typoTolerance": "min",
            "removeWordsIfNoResults": "allOptional",
            "attributesToRetrieve": [
                "post_title", "taxonomies.product_cat",
                "taxonomies.product_uses", "contextual_tags",
            ],
        },
    )
    r.raise_for_status()
    return r.json()


def classify_query(query):
    """Try to classify a query into a product category based on keywords."""
    q = query.lower()

    # Check if it's a known non-seed term
    for term in NOT_SEED_TERMS:
        if term in q:
            return "not_relevant"

    # Check against category map
    for category, keywords in CATEGORY_MAP.items():
        for kw in keywords:
            if kw in q:
                return category

    # Check for regional terms
    regions_cool = ["michigan", "minnesota", "wisconsin", "maine", "vermont",
                    "new hampshire", "alaska", "montana", "north dakota", "iowa"]
    regions_warm = ["florida", "georgia", "alabama", "mississippi", "louisiana",
                    "south carolina", "hawaii"]
    regions_transition = ["oklahoma", "tennessee", "arkansas", "missouri",
                          "north carolina", "virginia", "kentucky"]
    regions_arid = ["nevada", "arizona", "new mexico", "utah"]

    for r in regions_cool:
        if r in q:
            return "cool_season"
    for r in regions_warm:
        if r in q:
            return "warm_season"
    for r in regions_transition:
        if r in q:
            return "transitional"
    for r in regions_arid:
        if r in q:
            return "drought"

    return "unknown"


def build_synonym_for_query(query, relaxed_results, classification):
    """Build a oneWaySynonym mapping for a no-result query."""
    q_clean = query.strip().lower()
    obj_id = f"syn-auto-{re.sub(r'[^a-z0-9]+', '-', q_clean).strip('-')}"

    # Strategy 1: Use relaxed search results to find matching categories
    if relaxed_results.get("nbHits", 0) > 0:
        hits = relaxed_results.get("hits", [])
        # Extract categories from top hits
        categories = set()
        for hit in hits[:3]:
            cats = hit.get("taxonomies", {}).get("product_cat", [])
            for cat in cats:
                cat_lower = cat.lower()
                if "lawn" in cat_lower:
                    categories.add("lawn seed")
                elif "pasture" in cat_lower:
                    categories.add("pasture seed")
                elif "wildflower" in cat_lower:
                    categories.add("wildflower")
                elif "clover" in cat_lower:
                    categories.add("clover")
                elif "cover crop" in cat_lower:
                    categories.add("cover crop")
                elif "food plot" in cat_lower:
                    categories.add("food plot")
                elif "planting" in cat_lower or "aid" in cat_lower:
                    categories.add("planting aid")

        if categories:
            return {
                "objectID": obj_id,
                "type": "oneWaySynonym",
                "input": q_clean,
                "synonyms": list(categories)[:3],
            }

        # Fallback: use the top hit's title words
        top_title = hits[0].get("post_title", "").lower()
        # Extract meaningful words
        words = [w for w in top_title.split() if len(w) > 3 and w not in
                 {"seed", "seeds", "nature", "natures", "mix"}]
        if words:
            return {
                "objectID": obj_id,
                "type": "oneWaySynonym",
                "input": q_clean,
                "synonyms": words[:2],
            }

    # Strategy 2: Use classification
    category_synonyms = {
        "lawn": ["lawn seed", "grass seed"],
        "pasture": ["pasture seed", "forage"],
        "wildflower": ["wildflower", "native wildflower"],
        "clover": ["clover", "lawn alternative"],
        "cover crop": ["cover crop"],
        "food plot": ["food plot"],
        "planting aid": ["fertilizer", "planting aid"],
        "native grass": ["native grass", "prairie"],
        "erosion": ["erosion control", "slope"],
        "pollinator": ["pollinator wildflower"],
        "shade": ["shade tolerant", "shade"],
        "drought": ["drought tolerant", "dryland"],
        "cool_season": ["cool season lawn", "cool season pasture"],
        "warm_season": ["warm season lawn", "bermuda"],
        "transitional": ["transitional zone lawn", "transitional zone pasture"],
        "not_relevant": ["grass seed"],  # Generic fallback
    }

    synonyms = category_synonyms.get(classification)
    if synonyms:
        return {
            "objectID": obj_id,
            "type": "oneWaySynonym",
            "input": q_clean,
            "synonyms": synonyms,
        }

    return None


def push_synonyms(new_synonyms):
    """Push new synonyms to Algolia without replacing existing ones."""
    if not new_synonyms:
        return

    r = requests.post(
        f"{BASE_URL}/1/indexes/{INDEX_NAME}/synonyms/batch?replaceExistingSynonyms=false",
        headers=HEADERS_ADMIN,
        json=new_synonyms,
    )
    r.raise_for_status()
    result = r.json()

    task_id = result.get("taskID")
    if task_id:
        for _ in range(30):
            status = requests.get(
                f"{BASE_URL}/1/indexes/{INDEX_NAME}/task/{task_id}",
                headers=HEADERS_ADMIN,
            ).json()
            if status.get("status") == "published":
                return True
            time.sleep(1)

    return True


def send_telegram(message):
    """Send summary to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("Telegram not configured, skipping notification")
        return

    try:
        import html as html_mod
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        r.raise_for_status()
        log("Telegram notification sent")
    except Exception as e:
        log(f"Telegram error: {e}")


# ─── Main Logic ───────────────────────────────────────────────────────

def run(push=False, notify=True):
    print("=" * 60)
    print("ALGOLIA AUTO-SYNONYM REVIEW")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mode: {'PUSH' if push else 'DRY RUN'}")
    print("=" * 60)

    # 1. Pull no-result queries
    log("Pulling no-result queries (last 7 days)...")
    no_results = get_no_result_queries(days=7)
    log(f"Found {len(no_results)} unique no-result queries")

    # Filter by minimum searches
    actionable = [q for q in no_results if q["count"] >= MIN_SEARCHES]
    log(f"Actionable (>= {MIN_SEARCHES} searches): {len(actionable)}")

    # 2. Get existing synonyms
    log("Loading existing synonyms...")
    existing = get_existing_synonyms()
    log(f"Existing synonym terms: {len(existing)}")

    # 3. Find unhandled queries
    unhandled = []
    already_covered = []
    for item in actionable:
        query = item["search"].strip().lower()
        count = item["count"]

        # Skip very short queries (typos, single chars)
        if len(query) <= 2:
            continue

        # Skip if already covered by a synonym
        if query in existing or f"syn-auto-{re.sub(r'[^a-z0-9]+', '-', query).strip('-')}" in existing:
            already_covered.append((query, count))
            continue

        # Skip SKU-like queries
        if re.match(r'^[a-z]{1,4}-[a-z0-9]+', query) or re.match(r'^[0-9]+$', query):
            continue

        unhandled.append((query, count))

    log(f"Already covered by synonyms: {len(already_covered)}")
    log(f"Unhandled queries to process: {len(unhandled)}")

    if not unhandled:
        log("No new queries to handle. All good!")
        if push and notify:
            send_telegram(
                "<b>🔍 Algolia Auto-Review</b>\n\n"
                "No new no-result queries to fix today. "
                f"All {len(already_covered)} active queries are covered."
            )
        return

    # 4. Process each unhandled query
    new_synonyms = []
    skipped = []

    for query, count in unhandled:
        # Try relaxed search
        relaxed = relaxed_search(query)
        classification = classify_query(query)

        synonym = build_synonym_for_query(query, relaxed, classification)
        if synonym:
            new_synonyms.append(synonym)
            log(f"  + '{query}' ({count}x) → {synonym['synonyms']} [{classification}]")
        else:
            skipped.append((query, count, classification))
            log(f"  ? '{query}' ({count}x) — could not map [{classification}]")

    print()
    log(f"New synonyms to add: {len(new_synonyms)}")
    log(f"Skipped (unmappable): {len(skipped)}")

    # 5. Push if requested
    if push and new_synonyms:
        log("Pushing new synonyms...")
        push_synonyms(new_synonyms)
        log(f"✓ {len(new_synonyms)} synonyms pushed to Algolia")

        # Verify
        time.sleep(2)
        fixed = 0
        for syn in new_synonyms:
            result = requests.post(
                f"{BASE_URL}/1/indexes/{INDEX_NAME}/query",
                headers=HEADERS_SEARCH,
                json={"query": syn["input"], "hitsPerPage": 0},
            )
            if result.json().get("nbHits", 0) > 0:
                fixed += 1
        log(f"Verified: {fixed}/{len(new_synonyms)} queries now return results")

    # 6. Save report
    report = {
        "date": datetime.now().isoformat(),
        "total_no_result_queries": len(no_results),
        "actionable": len(actionable),
        "already_covered": len(already_covered),
        "new_synonyms_added": len(new_synonyms) if push else 0,
        "new_synonyms": [
            {"input": s["input"], "synonyms": s["synonyms"]}
            for s in new_synonyms
        ],
        "skipped": [
            {"query": q, "count": c, "classification": cl}
            for q, c, cl in skipped
        ],
    }

    report_path = DATA_DIR / f"auto_review_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    log(f"Report saved: {report_path}")

    # 7. Telegram notification
    if push and notify and new_synonyms:
        import html as html_mod

        lines = [f"<b>🔍 Algolia Auto-Review — {datetime.now().strftime('%b %d')}</b>\n"]
        lines.append(f"Added <b>{len(new_synonyms)}</b> new synonyms:\n")

        for syn in new_synonyms[:15]:  # Limit to 15 to fit Telegram
            inp = html_mod.escape(syn["input"])
            targets = ", ".join(syn["synonyms"])
            lines.append(f"• <code>{inp}</code> → {html_mod.escape(targets)}")

        if len(new_synonyms) > 15:
            lines.append(f"\n...and {len(new_synonyms) - 15} more")

        if skipped:
            lines.append(f"\n⚠️ {len(skipped)} queries couldn't be auto-mapped")

        lines.append(f"\nTotal synonyms: ~{len(existing) + len(new_synonyms)}")

        send_telegram("\n".join(lines))

    print()
    print("=" * 60)
    print(f"  Done — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Algolia Auto-Synonym Review")
    parser.add_argument("--push", action="store_true", help="Push synonyms + notify")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram notification")
    args = parser.parse_args()

    run(push=args.push, notify=not args.no_telegram)


if __name__ == "__main__":
    main()
