#!/usr/bin/env python3
"""
Nature's Seed — Keyword Coverage Audit
Compares WooCommerce product catalog against Google Ads keywords
to find coverage gaps and suggest new ad groups.
"""

import json
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import requests
from google.ads.googleads.client import GoogleAdsClient

# ══════════════════════════════════════════════════════════════
# ENV
# ══════════════════════════════════════════════════════════════

def _load_env():
    env = {}
    p = Path(__file__).resolve().parent.parent / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip("'\"")
    return env

ENV = _load_env()

# WooCommerce
WC_BASE = ENV.get("WC_BASE_URL", "https://naturesseed.com/wp-json/wc/v3")
WC_AUTH = (ENV["WC_CK"], ENV["WC_CS"])

# Google Ads
customer_id = ENV["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
login_id = ENV.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
gads_config = {
    "developer_token": ENV["GOOGLE_ADS_DEVELOPER_TOKEN"],
    "client_id": ENV["GOOGLE_ADS_CLIENT_ID"],
    "client_secret": ENV["GOOGLE_ADS_CLIENT_SECRET"],
    "refresh_token": ENV["GOOGLE_ADS_REFRESH_TOKEN"],
    "use_proto_plus": True,
}
if login_id:
    gads_config["login_customer_id"] = login_id

# ══════════════════════════════════════════════════════════════
# 1. PULL ALL PUBLISHED WOOCOMMERCE PRODUCTS
# ══════════════════════════════════════════════════════════════

def pull_wc_products():
    """Paginate through all published WooCommerce products."""
    products = []
    page = 1
    while True:
        print(f"  WC products page {page}...")
        resp = requests.get(
            f"{WC_BASE}/products",
            auth=WC_AUTH,
            params={"per_page": 100, "page": page, "status": "publish"},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for p in batch:
            products.append({
                "id": p["id"],
                "name": p.get("name", ""),
                "slug": p.get("slug", ""),
                "sku": p.get("sku", ""),
                "categories": [c["name"] for c in p.get("categories", [])],
                "tags": [t["name"] for t in p.get("tags", [])],
                "short_description": p.get("short_description", ""),
                "description": p.get("description", ""),
            })
        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)
    return products

# ══════════════════════════════════════════════════════════════
# 2. PULL ALL ENABLED GOOGLE ADS KEYWORDS (LAST 30 DAYS)
# ══════════════════════════════════════════════════════════════

def pull_gads_keywords():
    """Pull all enabled keywords with performance metrics from Google Ads."""
    client = GoogleAdsClient.load_from_dict(gads_config)
    service = client.get_service("GoogleAdsService")

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    query = f"""
        SELECT
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            campaign.name,
            campaign.id,
            ad_group.name,
            ad_group_criterion.quality_info.quality_score,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM keyword_view
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            AND ad_group_criterion.status = 'ENABLED'
            AND campaign.status = 'ENABLED'
            AND ad_group.status = 'ENABLED'
    """

    keywords = []
    seen = set()
    response = service.search_stream(customer_id=customer_id, query=query)
    for batch in response:
        for row in batch.results:
            kw_text = row.ad_group_criterion.keyword.text
            match_type = row.ad_group_criterion.keyword.match_type.name
            campaign_name = row.campaign.name
            ad_group_name = row.ad_group.name

            key = (kw_text, match_type, campaign_name, ad_group_name)
            if key in seen:
                continue
            seen.add(key)

            qs = row.ad_group_criterion.quality_info.quality_score
            keywords.append({
                "keyword": kw_text,
                "match_type": match_type,
                "campaign": campaign_name,
                "ad_group": ad_group_name,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "spend": round(row.metrics.cost_micros / 1_000_000, 2),
                "conversions": round(row.metrics.conversions, 2),
                "conv_value": round(row.metrics.conversions_value, 2),
                "quality_score": qs if qs > 0 else None,
            })
    return keywords

# ══════════════════════════════════════════════════════════════
# 3. GENERATE SEARCH TERMS FROM PRODUCTS
# ══════════════════════════════════════════════════════════════

# Noise words to strip when building search terms
NOISE = {"and", "or", "the", "a", "an", "for", "with", "of", "in", "to", "by", "-", "&", "/"}

# Seed/grass domain terms that signal meaningful product keywords
DOMAIN_TERMS = {
    "seed", "seeds", "mix", "blend", "grass", "pasture", "lawn", "turf",
    "clover", "wildflower", "wildflowers", "fescue", "ryegrass", "bermuda",
    "bluegrass", "timothy", "alfalfa", "orchard", "brome", "wheatgrass",
    "buffalo", "zoysia", "bentgrass", "native", "drought", "shade",
    "sun", "cool", "warm", "season", "horse", "cattle", "deer", "goat",
    "sheep", "elk", "wildlife", "food", "plot", "cover", "crop",
    "erosion", "control", "reclamation", "restoration", "pollinator",
    "bee", "butterfly", "forage", "hay", "overseeding", "overseed",
    "bermudagrass", "perennial", "annual", "rye", "micro", "clover",
    "dutch", "white", "red", "crimson", "inoculant", "coating",
    "coated", "hulled", "unhulled", "organic", "non-gmo",
    "kentucky", "tall", "fine", "creeping", "hard", "chewings",
}


def _clean(text):
    """Lowercase, strip HTML, collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def extract_product_terms(product):
    """Generate candidate search terms from a product."""
    name = _clean(product["name"])
    terms = set()

    # Full product name as a search term
    terms.add(name)

    words = name.split()

    # Add "{name} seed" variant if 'seed' not already in name
    if "seed" not in words and "seeds" not in words:
        terms.add(name + " seed")

    # Sliding window 2-5 grams that contain at least one domain term
    for n in range(2, min(6, len(words) + 1)):
        for i in range(len(words) - n + 1):
            gram = words[i:i + n]
            gram_clean = [w for w in gram if w not in NOISE]
            if len(gram_clean) < 2:
                continue
            phrase = " ".join(gram_clean)
            if any(w in DOMAIN_TERMS for w in gram_clean):
                terms.add(phrase)
                # Also add with "seed" appended if missing
                if "seed" not in gram_clean and "seeds" not in gram_clean:
                    terms.add(phrase + " seed")

    # Category-based terms
    for cat in product["categories"]:
        cat_clean = _clean(cat)
        if cat_clean and cat_clean not in {"uncategorized"}:
            terms.add(cat_clean)
            if "seed" not in cat_clean:
                terms.add(cat_clean + " seed")

    return terms


def extract_category_terms(products):
    """Generate category-level search terms."""
    cat_terms = defaultdict(set)
    for p in products:
        for cat in p["categories"]:
            cat_clean = _clean(cat)
            if cat_clean and cat_clean not in {"uncategorized"}:
                cat_terms[cat_clean].add(cat_clean)
                if "seed" not in cat_clean:
                    cat_terms[cat_clean].add(cat_clean + " seed")
                # Add "{category} mix" variant
                cat_terms[cat_clean].add(cat_clean + " mix")
    return cat_terms

# ══════════════════════════════════════════════════════════════
# 4. COMPARE AND FIND GAPS
# ══════════════════════════════════════════════════════════════

def normalize_for_match(text):
    """Normalize a string for fuzzy matching."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", text.lower())).strip()


def find_gaps(products, keywords):
    """Compare product-derived terms against Google Ads keywords."""

    # Build set of normalized existing keyword texts
    kw_set = set()
    for kw in keywords:
        kw_set.add(normalize_for_match(kw["keyword"]))

    # Per-product analysis
    product_gaps = []
    products_with_zero_coverage = []

    for p in products:
        p_terms = extract_product_terms(p)
        matched = set()
        unmatched = set()
        for t in p_terms:
            t_norm = normalize_for_match(t)
            # Check if any existing keyword contains this term or vice versa
            found = False
            for kw in kw_set:
                if t_norm in kw or kw in t_norm:
                    found = True
                    break
            if found:
                matched.add(t)
            else:
                unmatched.add(t)

        if unmatched:
            product_gaps.append({
                "product_id": p["id"],
                "product_name": p["name"],
                "categories": p["categories"],
                "matched_terms": len(matched),
                "gap_terms": sorted(unmatched),
            })
        if not matched:
            products_with_zero_coverage.append({
                "product_id": p["id"],
                "product_name": p["name"],
                "categories": p["categories"],
                "all_terms": sorted(p_terms),
            })

    # Category-level analysis
    cat_terms = extract_category_terms(products)
    category_gaps = {}
    for cat, terms in cat_terms.items():
        cat_matched = 0
        cat_unmatched = []
        for t in terms:
            t_norm = normalize_for_match(t)
            found = any(t_norm in kw or kw in t_norm for kw in kw_set)
            if found:
                cat_matched += 1
            else:
                cat_unmatched.append(t)
        if cat_unmatched and cat_matched == 0:
            category_gaps[cat] = sorted(cat_unmatched)

    return product_gaps, products_with_zero_coverage, category_gaps


def suggest_ad_groups(product_gaps, products):
    """Suggest new ad groups based on product category groupings."""
    # Group gap terms by category
    cat_gap_terms = defaultdict(set)
    cat_products = defaultdict(list)

    for gap in product_gaps:
        cats = gap["categories"] or ["Uncategorized"]
        for cat in cats:
            cat_clean = _clean(cat)
            if cat_clean == "uncategorized":
                continue
            for term in gap["gap_terms"]:
                cat_gap_terms[cat_clean].add(term)
            cat_products[cat_clean].append(gap["product_name"])

    suggestions = []
    for cat, terms in sorted(cat_gap_terms.items(), key=lambda x: -len(x[1])):
        if not terms:
            continue
        suggestions.append({
            "suggested_ad_group": cat.title().replace(" Seed", " Seeds"),
            "keywords": sorted(terms)[:20],  # top 20 per group
            "total_keyword_count": len(terms),
            "products_covered": sorted(set(cat_products[cat]))[:10],
        })

    return suggestions

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("KEYWORD COVERAGE AUDIT — Nature's Seed")
    print("=" * 60)

    # 1. Pull WC products
    print("\n[1/4] Pulling WooCommerce products...")
    products = pull_wc_products()
    print(f"  -> {len(products)} published products")

    # 2. Pull Google Ads keywords
    print("\n[2/4] Pulling Google Ads keywords (last 30 days)...")
    keywords = pull_gads_keywords()
    print(f"  -> {len(keywords)} enabled keywords with data")

    # 3. Find gaps
    print("\n[3/4] Analyzing keyword coverage gaps...")
    product_gaps, zero_coverage, category_gaps = find_gaps(products, keywords)

    # 4. Suggest ad groups
    print("\n[4/4] Generating ad group suggestions...")
    suggestions = suggest_ad_groups(product_gaps, products)

    # ── Save raw data ────────────────────────────────────────
    output_dir = Path(__file__).resolve().parent
    output_path = output_dir / "keyword_audit_data.json"
    audit_data = {
        "generated_at": datetime.now().isoformat(),
        "total_products": len(products),
        "total_keywords": len(keywords),
        "products": products,
        "keywords": keywords,
        "product_gaps": product_gaps,
        "products_with_zero_coverage": zero_coverage,
        "category_gaps": category_gaps,
        "suggested_ad_groups": suggestions,
    }
    output_path.write_text(json.dumps(audit_data, indent=2, default=str))
    print(f"\n  Raw data saved to {output_path}")

    # ── Print summary ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("KEYWORD COVERAGE AUDIT SUMMARY")
    print("=" * 60)

    print(f"\nTotal published products:   {len(products)}")
    print(f"Total active keywords:      {len(keywords)}")
    print(f"Products with gaps:         {len(product_gaps)}")
    print(f"Products with ZERO coverage:{len(zero_coverage)}")
    print(f"Categories with NO coverage:{len(category_gaps)}")

    # Top keyword stats
    if keywords:
        total_spend = sum(k["spend"] for k in keywords)
        total_clicks = sum(k["clicks"] for k in keywords)
        total_conv = sum(k["conversions"] for k in keywords)
        total_value = sum(k["conv_value"] for k in keywords)
        print(f"\n--- Google Ads Keyword Stats (30 days) ---")
        print(f"Total spend:      ${total_spend:,.2f}")
        print(f"Total clicks:     {total_clicks:,}")
        print(f"Total conversions:{total_conv:,.1f}")
        print(f"Total conv value: ${total_value:,.2f}")

    # Products with zero coverage
    if zero_coverage:
        print(f"\n--- Products with ZERO Keyword Coverage ({len(zero_coverage)}) ---")
        for p in zero_coverage[:30]:
            cats = ", ".join(p["categories"]) if p["categories"] else "No category"
            print(f"  [{p['product_id']}] {p['product_name']}  ({cats})")
        if len(zero_coverage) > 30:
            print(f"  ... and {len(zero_coverage) - 30} more")

    # Category gaps
    if category_gaps:
        print(f"\n--- Categories with NO Keyword Coverage ({len(category_gaps)}) ---")
        for cat, terms in sorted(category_gaps.items()):
            print(f"  {cat}")
            for t in terms[:5]:
                print(f"    -> {t}")

    # Keyword gaps (top 30 products by gap count)
    if product_gaps:
        top_gaps = sorted(product_gaps, key=lambda x: -len(x["gap_terms"]))[:30]
        print(f"\n--- Top Keyword Gaps (by product, showing top 30) ---")
        for g in top_gaps:
            print(f"\n  {g['product_name']} ({g['matched_terms']} matched, {len(g['gap_terms'])} gaps)")
            for t in g["gap_terms"][:8]:
                print(f"    MISSING: {t}")
            if len(g["gap_terms"]) > 8:
                print(f"    ... +{len(g['gap_terms']) - 8} more")

    # Suggested ad groups
    if suggestions:
        print(f"\n--- Suggested New Ad Groups ({len(suggestions)}) ---")
        for s in suggestions[:15]:
            print(f"\n  Ad Group: \"{s['suggested_ad_group']}\" ({s['total_keyword_count']} keywords)")
            print(f"  Products: {', '.join(s['products_covered'][:5])}")
            for kw in s["keywords"][:6]:
                print(f"    + {kw}")
            if len(s["keywords"]) > 6:
                print(f"    ... +{len(s['keywords']) - 6} more")
        if len(suggestions) > 15:
            print(f"\n  ... and {len(suggestions) - 15} more ad groups")

    print("\n" + "=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
