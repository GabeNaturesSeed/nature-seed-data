#!/usr/bin/env python3
"""
Google Product Reviews feed: fetch from WordPress (source of truth), validate,
guard against shrinkage, and write docs/reviews/product_reviews.xml for GitHub Pages.

Replaces shopper-approved/generate_review_feed.py (Shopper Approved retired).
The site generates the XML itself: GET {REVIEW_FEED_URL}
  default https://naturesseed.com/wp-json/gsnature/v1/reviews-feed

Guards (any failure leaves the previous feed untouched and exits 1):
  - HTTP 200 and well-formed XML with <feed><version>2.4</version> and <reviews>
  - every <review> has review_id, content, ratings/overall, products/product/product_url
  - every product_url is on the production host (staging/local feeds are refused)
  - shrinkage: new review count must be >= SHRINK_FLOOR (default 0.8) x previous count
    (set FORCE_FEED=1 to override deliberately)

Usage: python3 reviews/fetch_review_feed.py [--dry-run]
"""
import os, sys, requests
import xml.etree.ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUT_PATH = os.path.join(PROJECT_DIR, 'docs', 'reviews', 'product_reviews.xml')
FEED_URL = os.environ.get('REVIEW_FEED_URL', 'https://naturesseed.com/wp-json/gsnature/v1/reviews-feed')
SHRINK_FLOOR = float(os.environ.get('SHRINK_FLOOR', '0.8'))
EXPECTED_HOST = os.environ.get('REVIEW_FEED_HOST', 'https://naturesseed.com/')  # never publish staging/local URLs
FORCE = os.environ.get('FORCE_FEED', '') == '1'
DRY_RUN = '--dry-run' in sys.argv


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def count_reviews(xml_bytes):
    root = ET.fromstring(xml_bytes)
    if root.tag != 'feed':
        fail(f"root element is <{root.tag}>, expected <feed>")
    version = root.findtext('version')
    if version != '2.4':
        fail(f"feed version is {version!r}, expected '2.4'")
    reviews = root.findall('./reviews/review')
    for i, r in enumerate(reviews):
        for path in ('review_id', 'content', 'ratings/overall', 'products/product/product_url'):
            if r.find(path) is None or not (r.find(path).text or '').strip():
                fail(f"review #{i} missing <{path}>")
        url = r.findtext('products/product/product_url') or ''
        if not url.startswith(EXPECTED_HOST):
            fail(f"review #{i} product_url is not on {EXPECTED_HOST}: {url[:80]} (staging/local feed?)")
    return len(reviews)


def main():
    print(f"Fetching {FEED_URL}")
    resp = requests.get(FEED_URL, headers={'User-Agent': 'GSNature/1.0', 'Accept': 'application/xml'}, timeout=120)
    if resp.status_code != 200:
        fail(f"HTTP {resp.status_code}")
    ctype = resp.headers.get('Content-Type', '')
    if 'xml' not in ctype:
        fail(f"unexpected Content-Type {ctype!r}")
    new_count = count_reviews(resp.content)
    print(f"  fetched {len(resp.content):,} bytes, {new_count} reviews, well-formed, required fields present")

    old_count = 0
    if os.path.exists(OUT_PATH):
        try:
            old_count = len(ET.parse(OUT_PATH).getroot().findall('./reviews/review'))
        except ET.ParseError:
            old_count = 0
    print(f"  previous feed: {old_count} reviews")
    if old_count and new_count < SHRINK_FLOOR * old_count and not FORCE:
        fail(f"shrinkage guard: {new_count} < {SHRINK_FLOOR:.0%} of {old_count} (set FORCE_FEED=1 to override)")

    if DRY_RUN:
        print("  dry-run: not writing")
        return
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'wb') as f:
        f.write(resp.content)
    print(f"  wrote {OUT_PATH} ({new_count} reviews)")


if __name__ == '__main__':
    main()
