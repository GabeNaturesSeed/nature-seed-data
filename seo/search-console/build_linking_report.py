#!/usr/bin/env python3
"""
Build a comprehensive internal linking & cannibalization report
from WooCommerce product data, Search Console deep analysis, and health check data.

Output: INTERNAL_LINKING_REPORT.md
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse, unquote

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(filename):
    with open(os.path.join(DATA_DIR, filename)) as f:
        return json.load(f)


def fmt_num(n):
    """Format number with commas."""
    if isinstance(n, float):
        return f"{n:,.2f}"
    return f"{n:,}"


def fmt_pct(n):
    """Format as percentage."""
    return f"{n * 100:.2f}%"


def base_url(url):
    """Strip fragment and query string to get the canonical base URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def url_has_fragment(url):
    return "#" in url


def url_has_variation(url):
    return "variation_id" in url or "attribute" in url


def classify_page(url):
    """Classify a URL into page type."""
    path = urlparse(url).path.rstrip("/")
    if "/products/" in path:
        return "product"
    elif "/resources/" in path:
        return "resource"
    elif path.endswith(("/grass-seed", "/pasture-seed", "/wildflower-seed",
                        "/clover-seed", "/california-seeds")):
        return "category"
    elif "/grass-seed/" in path and path.count("/") <= 3:
        # e.g. /grass-seed/florida/
        return "state-landing"
    elif path in ("", "/"):
        return "homepage"
    else:
        return "other"


def normalize_query(q):
    """Lowercase, strip extra whitespace."""
    return re.sub(r"\s+", " ", q.strip().lower())


def build_product_keywords(products):
    """
    Build a lookup of keyword tokens -> list of product dicts.
    Also return a list of (name_lower, product) for fuzzy matching.
    """
    token_map = defaultdict(list)
    name_list = []
    for p in products:
        name_lower = p["name"].lower()
        name_list.append((name_lower, p))
        # Tokenize product name
        tokens = re.findall(r"[a-z]+", name_lower)
        for t in tokens:
            if len(t) > 2:  # skip very short tokens
                token_map[t].append(p)
        # Also add category tokens
        for cat in p.get("categories", []):
            cat_clean = cat.replace("&amp;", "&").lower()
            for t in re.findall(r"[a-z]+", cat_clean):
                if len(t) > 2:
                    token_map[t].append(p)
    return token_map, name_list


def query_matches_product(query, token_map, name_list, min_token_overlap=2):
    """
    Check if a query matches any product. Returns list of matching products
    scored by relevance.
    """
    q_tokens = set(re.findall(r"[a-z]+", query.lower()))
    # Remove very common / non-discriminating words
    stop = {"the", "for", "and", "how", "what", "best", "buy", "near", "does",
            "can", "with", "from", "that", "this", "where", "when", "why",
            "are", "you", "your", "seed", "seeds", "grass", "mix", "much"}
    q_meaningful = q_tokens - stop

    scored = []
    seen_ids = set()
    for name_lower, p in name_list:
        if p["id"] in seen_ids:
            continue
        name_tokens = set(re.findall(r"[a-z]+", name_lower)) - stop
        overlap = q_meaningful & name_tokens
        if len(overlap) >= min_token_overlap or (
            len(q_meaningful) == 1 and q_meaningful & name_tokens
        ):
            scored.append((len(overlap), p))
            seen_ids.add(p["id"])

    # Also try substring match on product name
    for name_lower, p in name_list:
        if p["id"] in seen_ids:
            continue
        # If query is contained in the product name or vice versa
        if query.lower() in name_lower or name_lower in query.lower():
            scored.append((5, p))
            seen_ids.add(p["id"])

    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Load data
    products_raw = load_json("wc_products.json")
    deep = load_json("deep_analysis.json")
    health = load_json("health_check.json")

    # Published products only
    products = [p for p in products_raw if p["status"] == "publish"]
    token_map, name_list = build_product_keywords(products)

    meta = deep["meta"]
    query_page_raw = deep["query_page_raw"]
    pages_data = deep["pages"]
    cannibalization = deep["cannibalization"]

    # Sort cannibalization by total impressions
    cannibalization.sort(key=lambda x: x["total_impressions"], reverse=True)

    # -----------------------------------------------------------------------
    # Build aggregated query-level data (sum across all pages)
    # -----------------------------------------------------------------------
    query_agg = defaultdict(lambda: {"impressions": 0, "clicks": 0, "pages": []})
    for row in query_page_raw:
        q = row["query"]
        query_agg[q]["impressions"] += row["impressions"]
        query_agg[q]["clicks"] += row["clicks"]
        query_agg[q]["pages"].append(row)

    top_queries_by_imp = sorted(query_agg.items(),
                                key=lambda x: x[1]["impressions"], reverse=True)

    # -----------------------------------------------------------------------
    # Fragment URL analysis
    # -----------------------------------------------------------------------
    fragment_pages = [p for p in pages_data if url_has_fragment(p["page"])]
    fragment_pages.sort(key=lambda x: x["impressions"], reverse=True)

    # Group fragments by base URL
    fragment_groups = defaultdict(list)
    for p in fragment_pages:
        fragment_groups[base_url(p["page"])].append(p)

    # Variation URL analysis
    variation_pages = [p for p in pages_data if url_has_variation(p["page"])]
    variation_pages.sort(key=lambda x: x["impressions"], reverse=True)

    # -----------------------------------------------------------------------
    # Section 2: Product catalog vs search demand
    # -----------------------------------------------------------------------
    top100_queries = top_queries_by_imp[:100]
    carry_queries = []     # (query, agg_data, matching_products)
    not_carry_queries = []  # (query, agg_data)
    branded_queries = []    # skip branded

    branded_patterns = re.compile(
        r"nature.?s?\s*seed|naturesseed|natureseed", re.IGNORECASE
    )

    for query, agg in top100_queries:
        if branded_patterns.search(query):
            branded_queries.append((query, agg))
            continue
        matches = query_matches_product(query, token_map, name_list)
        if matches:
            carry_queries.append((query, agg, matches))
        else:
            not_carry_queries.append((query, agg))

    # -----------------------------------------------------------------------
    # Section 5: Internal linking opportunities
    # -----------------------------------------------------------------------
    # Identify resource pages with high impressions
    resource_pages = [p for p in pages_data
                      if "/resources/" in p["page"] and "#" not in p["page"]
                      and "?" not in p["page"]]
    resource_pages.sort(key=lambda x: x["impressions"], reverse=True)

    # Product pages in search console
    product_pages_sc = [p for p in pages_data
                        if "/products/" in p["page"] and "#" not in p["page"]
                        and "?" not in p["page"]]
    product_pages_sc.sort(key=lambda x: x["impressions"], reverse=True)

    # Category pages
    category_pages = []
    for p in pages_data:
        ptype = classify_page(p["page"])
        if ptype in ("category", "state-landing"):
            if "#" not in p["page"] and "?" not in p["page"]:
                category_pages.append(p)
    category_pages.sort(key=lambda x: x["impressions"], reverse=True)

    # -----------------------------------------------------------------------
    # Determine product categories for hub-spoke mapping
    # -----------------------------------------------------------------------
    cat_to_products = defaultdict(list)
    for p in products:
        for c in p.get("categories", []):
            cat_clean = c.replace("&amp;", "&")
            cat_to_products[cat_clean].append(p)

    # -----------------------------------------------------------------------
    # Build the report
    # -----------------------------------------------------------------------
    lines = []
    W = lines.append

    W("# Nature's Seed — Internal Linking & Cannibalization Report")
    W(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    W(f"*Data period: {meta['start_date']} to {meta['end_date']} (30 days)*")
    W("")

    # ===== SECTION 1: EXECUTIVE SUMMARY =====
    W("---")
    W("## 1. Executive Summary")
    W("")
    W("### 30-Day Organic Traffic Overview")
    W("")
    curr = health["overall_current"]
    prev = health["overall_previous"]
    W(f"| Metric | Current 30d | Previous 30d | Change |")
    W(f"|--------|------------|-------------|--------|")
    click_chg = ((curr["clicks"] - prev["clicks"]) / prev["clicks"] * 100) if prev["clicks"] else 0
    imp_chg = ((curr["impressions"] - prev["impressions"]) / prev["impressions"] * 100) if prev["impressions"] else 0
    W(f"| Clicks | {fmt_num(curr['clicks'])} | {fmt_num(prev['clicks'])} | {click_chg:+.1f}% |")
    W(f"| Impressions | {fmt_num(curr['impressions'])} | {fmt_num(prev['impressions'])} | {imp_chg:+.1f}% |")
    W(f"| CTR | {fmt_pct(curr['ctr'])} | {fmt_pct(prev['ctr'])} | — |")
    W(f"| Avg Position | {curr['avg_position']:.1f} | {prev['avg_position']:.1f} | {curr['avg_position'] - prev['avg_position']:+.1f} |")
    W("")
    W("### Key Findings")
    W("")
    W(f"- **{fmt_num(meta['cannibalized_query_count'])} cannibalized queries** — multiple pages competing for the same keyword")
    W(f"- **{fmt_num(meta['unique_pages'])} unique pages** indexed across {fmt_num(meta['unique_queries'])} unique queries")
    W(f"- **{len(fragment_pages)} fragment URLs** (anchor links like `#section`) being indexed as separate pages — this is a major crawl-budget and cannibalization issue")
    W(f"- **{len(variation_pages)} variation/parameter URLs** (product variations with `?variation_id=`) indexed separately")
    W(f"- **{health['quick_wins_count']} quick-win opportunities** (positions 5-15, high impressions)")
    W(f"- **{health['striking_distance_count']} striking-distance queries** (positions 8-20)")
    W(f"- **{health['branded_pct']:.1f}% branded traffic** — the rest is non-branded organic")
    W("")
    total_fragment_impressions = sum(p["impressions"] for p in fragment_pages)
    W(f"> **Estimated wasted impressions on fragment URLs: {fmt_num(total_fragment_impressions)}** — these should all be consolidated to base URLs via canonical tags.")
    W("")

    # ===== SECTION 2: PRODUCT CATALOG VS SEARCH DEMAND =====
    W("---")
    W("## 2. Product Catalog vs. Search Demand Mismatch")
    W("")
    W(f"Analyzed the top 100 queries by impressions against the {len(products)} published WooCommerce products.")
    W("")

    # --- We carry this — optimize ---
    W("### 2a. \"We Carry This — Optimize\" (Query matches a product we sell)")
    W("")
    W(f"**{len(carry_queries)} queries** match products in the catalog.")
    W("")
    W("| # | Query | Impressions | Clicks | CTR | Best Matching Product | Product URL |")
    W("|---|-------|------------|--------|-----|----------------------|-------------|")
    for i, (query, agg, matches) in enumerate(carry_queries[:50], 1):
        best = matches[0]
        imp = agg["impressions"]
        clk = agg["clicks"]
        ctr = clk / imp if imp else 0
        name = best["name"].replace("&amp;", "&")
        url = best["permalink"]
        W(f"| {i} | {query} | {fmt_num(imp)} | {fmt_num(clk)} | {fmt_pct(ctr)} | {name} | {url} |")
    W("")

    # --- We don't carry this — deprioritize/redirect ---
    W("### 2b. \"We Don't Carry This — Deprioritize or Redirect\" (No matching product)")
    W("")
    W(f"**{len(not_carry_queries)} queries** from the top 100 have NO matching product in the catalog. These drive impressions but may attract the wrong audience.")
    W("")
    W("| # | Query | Impressions | Clicks | Top Ranking Page | Recommendation |")
    W("|---|-------|------------|--------|-----------------|----------------|")
    for i, (query, agg) in enumerate(not_carry_queries[:50], 1):
        imp = agg["impressions"]
        clk = agg["clicks"]
        # Find the top page for this query
        top_page = max(agg["pages"], key=lambda x: x["impressions"])
        page_short = top_page["page"].replace("https://naturesseed.com", "")
        # Generate recommendation
        rec = "Resource page — OK for SEO authority"
        q_lower = query.lower()
        if any(kw in q_lower for kw in ["st augustine", "zoysia", "centipede",
                                         "bahia", "carpet grass", "dichondra"]):
            rec = "We don't sell this species — consider adding or redirecting"
        elif "paper" in q_lower or "diy" in q_lower or "make" in q_lower:
            rec = "DIY/informational — drives traffic, not sales. OK to keep"
        elif any(kw in q_lower for kw in ["how to", "when to", "what is", "guide"]):
            rec = "Informational intent — add CTAs to relevant product pages"
        elif "best" in q_lower and any(state in q_lower for state in [
            "virginia", "florida", "georgia", "texas", "indiana", "illinois",
            "wisconsin", "washington", "ohio", "michigan", "minnesota",
            "tennessee", "north carolina", "maryland", "oregon", "colorado",
            "pennsylvania", "new york", "kentucky", "missouri", "oklahoma"
        ]):
            rec = "State guide — add internal links to relevant product pages"
        W(f"| {i} | {query} | {fmt_num(imp)} | {fmt_num(clk)} | `{page_short}` | {rec} |")
    W("")

    W(f"### 2c. Branded Queries ({len(branded_queries)} queries)")
    W("")
    W("These are navigational — users searching for Nature's Seed by name. No action needed.")
    W("")

    # ===== SECTION 3: CANNIBALIZATION DEEP DIVE =====
    W("---")
    W("## 3. Cannibalization Analysis — Top 40 Queries")
    W("")
    W("These queries have **multiple pages competing** for the same keyword, diluting click-through and confusing Google about which page to rank.")
    W("")

    for idx, c in enumerate(cannibalization[:40], 1):
        query = c["query"]
        W(f"### 3.{idx}. \"{query}\"")
        W(f"**Total impressions:** {fmt_num(c['total_impressions'])} | **Total clicks:** {fmt_num(c['total_clicks'])} | **Pages competing:** {c['num_pages']}")
        W("")
        W("| Page | Type | Clicks | Impressions | CTR | Avg Pos |")
        W("|------|------|--------|------------|-----|---------|")

        # Show top pages (limit to top 10 by impressions to keep readable)
        sorted_pages = sorted(c["pages"], key=lambda x: x["impressions"], reverse=True)
        for p in sorted_pages[:10]:
            page_url = p["page"].replace("https://naturesseed.com", "")
            ptype = classify_page(p["page"])
            has_frag = " (FRAGMENT)" if "#" in p["page"] else ""
            has_var = " (VARIATION)" if "?" in p["page"] else ""
            ctr = fmt_pct(p["ctr"]) if p["impressions"] > 0 else "—"
            W(f"| `{page_url}`{has_frag}{has_var} | {ptype} | {p['clicks']} | {fmt_num(p['impressions'])} | {ctr} | {p['position']:.1f} |")

        if len(sorted_pages) > 10:
            remaining_imp = sum(p["impressions"] for p in sorted_pages[10:])
            W(f"| *... +{len(sorted_pages) - 10} more pages* | — | — | {fmt_num(remaining_imp)} | — | — |")

        W("")
        # Recommendation: which page should be canonical
        top_page = sorted_pages[0]
        top_type = classify_page(top_page["page"])

        # Find if there's a product page in the mix
        product_candidates = [p for p in sorted_pages if classify_page(p["page"]) == "product" and "#" not in p["page"] and "?" not in p["page"]]
        category_candidates = [p for p in sorted_pages if classify_page(p["page"]) == "category" and "#" not in p["page"]]

        if product_candidates:
            best_prod = max(product_candidates, key=lambda x: x["impressions"])
            W(f"**Recommended canonical:** `{best_prod['page'].replace('https://naturesseed.com', '')}`")
            W(f"**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.")
        elif category_candidates:
            best_cat = max(category_candidates, key=lambda x: x["impressions"])
            W(f"**Recommended canonical:** `{best_cat['page'].replace('https://naturesseed.com', '')}`")
            W(f"**Reason:** Category page is the broadest match for this query. Individual product/resource pages should link up to the category.")
        else:
            W(f"**Recommended canonical:** `{top_page['page'].replace('https://naturesseed.com', '')}`")
            if top_type == "resource":
                W(f"**Reason:** This resource page has the most impressions. If a product page exists, consider creating one and shifting authority there.")
            else:
                W(f"**Reason:** Highest impression page — consolidate others via canonical tags or 301 redirects.")

        # Flag fragment URLs
        frag_count = sum(1 for p in sorted_pages if "#" in p["page"])
        var_count = sum(1 for p in sorted_pages if "?" in p["page"])
        if frag_count:
            W(f"**Warning:** {frag_count} fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.")
        if var_count:
            W(f"**Warning:** {var_count} variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.")
        W("")

    # ===== SECTION 4: FRAGMENT URL PROBLEM =====
    W("---")
    W("## 4. Fragment URL Problem")
    W("")
    W(f"**{len(fragment_pages)} fragment URLs** are being indexed by Google as separate pages.")
    W(f"These are anchor links (e.g., `/page/#section`) that Google is treating as distinct URLs.")
    W("")
    W(f"**Total wasted impressions across fragment URLs: {fmt_num(total_fragment_impressions)}**")
    W(f"**Total wasted clicks: {sum(p['clicks'] for p in fragment_pages)}**")
    W("")
    W("### Impact by Base URL")
    W("")
    W("| Base URL | # Fragments | Total Fragment Impressions | Total Fragment Clicks |")
    W("|----------|------------|---------------------------|----------------------|")
    fragment_group_sorted = sorted(fragment_groups.items(),
                                   key=lambda x: sum(p["impressions"] for p in x[1]),
                                   reverse=True)
    for base, frags in fragment_group_sorted[:30]:
        base_short = base.replace("https://naturesseed.com", "")
        total_imp = sum(p["impressions"] for p in frags)
        total_clk = sum(p["clicks"] for p in frags)
        W(f"| `{base_short}` | {len(frags)} | {fmt_num(total_imp)} | {total_clk} |")
    W("")

    W("### Worst Offenders — Individual Fragment URLs by Impressions")
    W("")
    W("| Fragment URL | Impressions | Clicks | Avg Pos |")
    W("|-------------|------------|--------|---------|")
    for p in fragment_pages[:40]:
        short = p["page"].replace("https://naturesseed.com", "")
        W(f"| `{short}` | {fmt_num(p['impressions'])} | {p['clicks']} | {p['position']:.1f} |")
    W("")

    W("### Fix")
    W("")
    W("1. **Add `<link rel=\"canonical\" href=\"BASE_URL\">` to every page** — this tells Google that `page/#section` is the same as `page/`")
    W("2. **Check for JavaScript-generated anchor links** that Google is crawling as separate URLs")
    W("3. **Verify in Google Search Console** that fragment URLs stop appearing after canonical tags are added")
    W("4. **Consider using `scrollTo` JavaScript** instead of anchor `#id` links for in-page navigation")
    W("")

    # Also mention variation URLs
    W("### Variation/Parameter URLs")
    W("")
    W(f"**{len(variation_pages)} variation URLs** (with `?variation_id=...`) are indexed.")
    W("")
    total_var_imp = sum(p["impressions"] for p in variation_pages)
    W(f"Total impressions on variation URLs: {fmt_num(total_var_imp)}")
    W("")
    W("**Top variation URLs by impressions:**")
    W("")
    W("| URL | Impressions | Clicks |")
    W("|-----|------------|--------|")
    for p in variation_pages[:15]:
        short = unquote(p["page"]).replace("https://naturesseed.com", "")
        if len(short) > 100:
            short = short[:97] + "..."
        W(f"| `{short}` | {fmt_num(p['impressions'])} | {p['clicks']} |")
    W("")
    W("**Fix:** Add `<link rel=\"canonical\">` pointing to the base product URL (without query params). Optionally add `<meta name=\"robots\" content=\"noindex\">` on variation pages or block `?variation_id` in robots.txt.")
    W("")

    # ===== SECTION 5: INTERNAL LINKING ACTION PLAN =====
    W("---")
    W("## 5. Internal Linking Action Plan")
    W("")

    W("### 5a. High-Impression Resource Pages That Should Link to Product Pages")
    W("")
    W("These resource/blog pages get significant organic traffic but may not link to the relevant product pages, missing conversion opportunities.")
    W("")
    W("| Resource Page | Impressions | Clicks | Suggested Product Link(s) |")
    W("|--------------|------------|--------|--------------------------|")
    for rp in resource_pages[:30]:
        page_short = rp["page"].replace("https://naturesseed.com", "")
        # Try to match resource page topic to products
        # Extract topic keywords from URL
        path_parts = urlparse(rp["page"]).path.strip("/").split("/")
        topic = path_parts[-1] if path_parts else ""
        topic_words = set(re.findall(r"[a-z]+", topic.lower()))
        topic_words -= {"how", "to", "the", "and", "for", "of", "in", "a", "an",
                        "is", "are", "your", "from", "with", "about", "resources",
                        "lawn", "turf", "seed", "seeds"}

        matching_prods = []
        for name_lower, p in name_list:
            name_words = set(re.findall(r"[a-z]+", name_lower))
            overlap = topic_words & name_words
            if len(overlap) >= 1 and any(w not in {"grass", "mix", "best", "plant"} for w in overlap):
                matching_prods.append(p)

        if matching_prods:
            prod_links = "; ".join(
                f"[{p['name'].replace('&amp;', '&')}]({p['permalink']})"
                for p in matching_prods[:3]
            )
        else:
            prod_links = "*Review manually — no obvious product match*"

        W(f"| `{page_short}` | {fmt_num(rp['impressions'])} | {rp['clicks']} | {prod_links} |")
    W("")

    W("### 5b. Product Pages That Should Link to Resource Guides")
    W("")
    W("| Product Page | Impressions | Clicks | Suggested Resource Link(s) |")
    W("|-------------|------------|--------|---------------------------|")
    for pp in product_pages_sc[:25]:
        page_short = pp["page"].replace("https://naturesseed.com", "")
        # Match product page to resource pages by topic
        path_parts = urlparse(pp["page"]).path.strip("/").split("/")
        topic = path_parts[-1] if path_parts else ""
        topic_words = set(re.findall(r"[a-z]+", topic.lower()))
        topic_words -= {"products", "seed", "seeds", "mix", "blend"}

        matching_resources = []
        for rp in resource_pages:
            rp_words = set(re.findall(r"[a-z]+", urlparse(rp["page"]).path.lower()))
            rp_words -= {"resources", "lawn", "turf", "how", "to", "the", "and",
                         "for", "of", "seed", "seeds"}
            overlap = topic_words & rp_words
            if len(overlap) >= 1 and any(w not in {"grass", "best", "plant", "grow"} for w in overlap):
                matching_resources.append(rp)

        if matching_resources:
            res_links = "; ".join(
                f"[{urlparse(r['page']).path.split('/')[-2] if urlparse(r['page']).path.endswith('/') else urlparse(r['page']).path.split('/')[-1]}]({r['page']})"
                for r in matching_resources[:3]
            )
        else:
            res_links = "*No matching resource found — consider creating a guide*"

        W(f"| `{page_short}` | {fmt_num(pp['impressions'])} | {pp['clicks']} | {res_links} |")
    W("")

    W("### 5c. Hub-and-Spoke: Category Pages and Their Products")
    W("")
    W("Each category page should link prominently to all its child product pages (hub → spoke). Product pages should link back to the category and cross-link to related products.")
    W("")

    # Map URL path segments to category pages in search console
    cat_page_map = {
        "grass-seed": "/products/grass-seed/",
        "pasture-seed": "/products/pasture-seed/",
        "wildflower-seed": "/products/wildflower-seed/",
        "clover-seed": "/products/clover-seed/",
        "california-seeds": "/products/california-seeds/",
    }

    for slug, cat_path in cat_page_map.items():
        # Find category page in SC data
        cat_url = f"https://naturesseed.com{cat_path}"
        cat_sc = next((p for p in pages_data if p["page"] == cat_url), None)
        cat_imp = cat_sc["impressions"] if cat_sc else 0
        cat_clicks = cat_sc["clicks"] if cat_sc else 0

        # Find products under this category
        child_products = [p for p in products if f"/{slug}/" in p["permalink"]]

        W(f"#### {slug.replace('-', ' ').title()} (Category)")
        W(f"**Category URL:** `{cat_path}` — {fmt_num(cat_imp)} impressions, {cat_clicks} clicks")
        W(f"**Products ({len(child_products)}):**")
        W("")
        if child_products:
            for p in child_products:
                prod_path = p["permalink"].replace("https://naturesseed.com", "")
                # Find SC data for this product
                prod_sc = next((pg for pg in pages_data if pg["page"] == p["permalink"]), None)
                prod_imp = prod_sc["impressions"] if prod_sc else 0
                W(f"- `{prod_path}` — {p['name'].replace('&amp;', '&')} ({fmt_num(prod_imp)} imp)")
        else:
            W("- *No published products found under this category slug*")
        W("")

    W("### 5d. Cross-Category Linking Opportunities")
    W("")
    W("These are thematic connections across categories that could benefit from cross-linking:")
    W("")
    W("| From Category | To Category | Linking Theme |")
    W("|--------------|------------|---------------|")
    W("| Grass Seed (lawn mixes) | Resources/Lawn Turf (state guides) | State-specific recommendations → product links |")
    W("| Pasture Seed (horse/goat/cattle) | Resources/Agriculture | Animal-specific guides → pasture product links |")
    W("| Wildflower Seed | Resources/Wildlife Habitat | Pollinator/habitat guides → wildflower product links |")
    W("| Clover Seed | Resources/Lawn Turf | Lawn alternative guides → clover product links |")
    W("| California Seeds | Resources/Lawn Turf (state guides) | California-specific guides → CA product links |")
    W("| Cover Crop Seed | Resources/Agriculture | Soil health guides → cover crop product links |")
    W("")

    W("### 5e. Potentially Orphaned Pages (High Impressions, Likely Few Internal Links)")
    W("")
    W("These pages get significant impressions but are likely not well-linked internally. Verify in the site and add links from relevant pages.")
    W("")
    W("| Page | Type | Impressions | Clicks | Suggested Internal Link Source |")
    W("|------|------|------------|--------|-------------------------------|")

    # Pages with high impressions but not product/category/homepage
    other_high_imp = [p for p in pages_data
                      if p["impressions"] > 500
                      and "#" not in p["page"]
                      and "?" not in p["page"]
                      and classify_page(p["page"]) not in ("homepage",)]
    other_high_imp.sort(key=lambda x: x["impressions"], reverse=True)

    for p in other_high_imp[:30]:
        ptype = classify_page(p["page"])
        page_short = p["page"].replace("https://naturesseed.com", "")
        # Suggest where links could come from
        if ptype == "resource":
            suggestion = "Add links from category pages & product pages in same topic"
        elif ptype == "product":
            suggestion = "Ensure category page links here; add to related resource articles"
        elif ptype == "state-landing":
            suggestion = "Link from main grass-seed category; link from state resource page"
        else:
            suggestion = "Review — may need links from homepage or navigation"
        W(f"| `{page_short}` | {ptype} | {fmt_num(p['impressions'])} | {p['clicks']} | {suggestion} |")
    W("")

    # ===== SECTION 6: CANONICAL URL STRUCTURE =====
    W("---")
    W("## 6. Canonical URL Structure Recommendations")
    W("")

    W("### 6a. Pages That Need Canonical Tags")
    W("")
    W("Every page with fragment or parameter variations should have a `<link rel=\"canonical\">` pointing to the clean base URL.")
    W("")
    W(f"- **{len(fragment_pages)} fragment URLs** need canonical → base URL")
    W(f"- **{len(variation_pages)} variation URLs** need canonical → base product URL")
    W("")

    W("### 6b. Fragment URL Cleanup Priority")
    W("")
    W("Ordered by total fragment impressions per base URL:")
    W("")
    for i, (base, frags) in enumerate(fragment_group_sorted[:15], 1):
        base_short = base.replace("https://naturesseed.com", "")
        total_imp = sum(p["impressions"] for p in frags)
        frag_list = ", ".join(f"`#{urlparse(p['page']).fragment}`" for p in frags[:5])
        extra = f" +{len(frags)-5} more" if len(frags) > 5 else ""
        W(f"{i}. **`{base_short}`** — {len(frags)} fragments, {fmt_num(total_imp)} impressions")
        W(f"   Fragments: {frag_list}{extra}")
        W(f"   Fix: Add `<link rel=\"canonical\" href=\"{base}\">` to this page")
        W("")

    W("### 6c. Duplicate Content / URL Inconsistencies")
    W("")
    # Check for near-duplicate paths
    path_groups = defaultdict(list)
    for p in pages_data:
        if "#" not in p["page"] and "?" not in p["page"]:
            # Normalize: strip trailing slash, lowercase
            norm = urlparse(p["page"]).path.rstrip("/").lower()
            path_groups[norm].append(p)

    # Find paths that differ only slightly
    W("| Issue | URLs | Combined Impressions | Recommendation |")
    W("|-------|------|---------------------|----------------|")

    # Check for /grass-seed/ vs /products/grass-seed/ patterns
    seen_dupes = set()
    all_paths = sorted(path_groups.keys())
    for i, path1 in enumerate(all_paths):
        parts1 = [s for s in path1.split("/") if s]
        slug1 = parts1[-1] if parts1 else ""
        for path2 in all_paths[i+1:]:
            parts2 = [s for s in path2.split("/") if s]
            slug2 = parts2[-1] if parts2 else ""
            if slug1 == slug2 and slug1 and len(slug1) > 3 and path1 != path2:
                key = tuple(sorted([path1, path2]))
                if key not in seen_dupes:
                    seen_dupes.add(key)
                    pages1 = path_groups[path1]
                    pages2 = path_groups[path2]
                    imp1 = sum(p["impressions"] for p in pages1)
                    imp2 = sum(p["impressions"] for p in pages2)
                    if imp1 + imp2 > 50:  # Only show meaningful ones
                        W(f"| Duplicate slug `{slug1}` | `{path1}` vs `{path2}` | {fmt_num(imp1 + imp2)} | 301 redirect lower-imp version → higher-imp version |")

    W("")
    W("### 6d. WWW vs Non-WWW / HTTP vs HTTPS")
    W("")
    # Check if any non-https or www URLs appear
    non_standard = [p for p in pages_data if "http://" in p["page"] or "www." in p["page"]]
    if non_standard:
        W(f"**{len(non_standard)} non-standard URLs found:**")
        for p in non_standard[:10]:
            W(f"- `{p['page']}` ({fmt_num(p['impressions'])} impressions)")
    else:
        W("All indexed URLs use `https://naturesseed.com` (no www). No HTTP or WWW inconsistencies detected.")
    W("")

    # ===== SECTION 7: PRIORITY ACTION ITEMS =====
    W("---")
    W("## 7. Priority Action Items")
    W("")
    W("Ordered by **impact** (impressions affected x ease of fix).")
    W("")

    W("### Priority 1: Quick Wins (Fix This Week)")
    W("")
    W(f"1. **Add canonical tags to ALL pages** — This single fix addresses {len(fragment_pages)} fragment URLs and {len(variation_pages)} variation URLs ({fmt_num(total_fragment_impressions + total_var_imp)} combined impressions)")
    W("   - Implementation: Add `<link rel=\"canonical\" href=\"{{base_url}}\">` in the `<head>` of every page")
    W("   - For WooCommerce: Install/configure Yoast SEO or RankMath to auto-set canonicals")
    W("   - For fragment URLs: Canonical should point to the URL without `#fragment`")
    W("   - For variation URLs: Canonical should point to the URL without `?variation_id=...`")
    W("")
    W(f"2. **Block variation URLs in robots.txt** — Add: `Disallow: /*?variation_id`")
    W("")

    # Find the highest-impact canonical fixes
    top_fragment_bases = fragment_group_sorted[:5]
    W("3. **Highest-priority canonical fixes (by impressions):**")
    for base, frags in top_fragment_bases:
        total_imp = sum(p["impressions"] for p in frags)
        W(f"   - `{base.replace('https://naturesseed.com', '')}` — {len(frags)} fragments, {fmt_num(total_imp)} impressions")
    W("")

    W("### Priority 2: High-Impact Internal Links (This Month)")
    W("")
    W("Add internal links from high-traffic resource pages to relevant product pages:")
    W("")
    link_actions = []
    for rp in resource_pages[:15]:
        if rp["impressions"] < 500:
            continue
        page_short = rp["page"].replace("https://naturesseed.com", "")
        path_parts = urlparse(rp["page"]).path.strip("/").split("/")
        topic = path_parts[-1] if path_parts else ""
        topic_words = set(re.findall(r"[a-z]+", topic.lower()))
        topic_words -= {"how", "to", "the", "and", "for", "of", "in", "a", "resources",
                        "lawn", "turf", "seed", "seeds"}

        matching_prods = []
        for name_lower, p in name_list:
            name_words = set(re.findall(r"[a-z]+", name_lower))
            overlap = topic_words & name_words
            if len(overlap) >= 1 and any(w not in {"grass", "mix", "best", "plant"} for w in overlap):
                matching_prods.append(p)

        if matching_prods:
            for mp in matching_prods[:2]:
                link_actions.append((rp["impressions"], page_short, mp["name"].replace("&amp;", "&"), mp["permalink"]))

    link_actions.sort(key=lambda x: -x[0])
    for i, (imp, from_page, to_name, to_url) in enumerate(link_actions[:15], 1):
        to_short = to_url.replace("https://naturesseed.com", "")
        W(f"{i}. **`{from_page}`** ({fmt_num(imp)} imp) → link to [{to_name}]({to_url})")
    W("")

    W("### Priority 3: Pages to Consolidate or Redirect (This Month)")
    W("")
    W("These are the most cannibalized queries where consolidation would have the biggest impact:")
    W("")
    for i, c in enumerate(cannibalization[:10], 1):
        # Find pages that should be redirected
        sorted_p = sorted(c["pages"], key=lambda x: x["impressions"], reverse=True)
        primary = sorted_p[0]
        primary_short = primary["page"].replace("https://naturesseed.com", "")
        redirect_candidates = [p for p in sorted_p[1:] if p["impressions"] > 10
                               and "#" not in p["page"] and "?" not in p["page"]
                               and classify_page(p["page"]) == classify_page(primary["page"])]
        if redirect_candidates:
            W(f"{i}. **\"{c['query']}\"** ({fmt_num(c['total_impressions'])} imp, {c['num_pages']} pages)")
            W(f"   - Keep: `{primary_short}`")
            for rc in redirect_candidates[:3]:
                rc_short = rc["page"].replace("https://naturesseed.com", "")
                W(f"   - Consolidate: `{rc_short}` ({fmt_num(rc['impressions'])} imp) → 301 or canonical to primary")
        else:
            W(f"{i}. **\"{c['query']}\"** ({fmt_num(c['total_impressions'])} imp, {c['num_pages']} pages)")
            W(f"   - Primary: `{primary_short}` — add canonical; ensure other pages link here instead of competing")
    W("")

    W("### Priority 4: Content Gaps to Fill (Next Quarter)")
    W("")
    W("High-impression queries where we carry the product but have weak or no dedicated landing pages:")
    W("")
    for i, (query, agg, matches) in enumerate(carry_queries[:10], 1):
        # Check if the top-ranking page IS the product page
        top_page = max(agg["pages"], key=lambda x: x["impressions"])
        is_product_page = "/products/" in top_page["page"]
        if not is_product_page:
            W(f"{i}. **\"{query}\"** ({fmt_num(agg['impressions'])} imp)")
            W(f"   - Product: [{matches[0]['name'].replace('&amp;', '&')}]({matches[0]['permalink']})")
            W(f"   - Currently ranking: `{top_page['page'].replace('https://naturesseed.com', '')}` (a {classify_page(top_page['page'])} page)")
            W(f"   - Action: Optimize the product page for this query; add internal links from the ranking resource page to the product page")
    W("")

    W("---")
    W("*End of report. All data sourced from Google Search Console (30-day window) and WooCommerce product catalog.*")

    # Write the report
    report_path = os.path.join(SCRIPT_DIR, "INTERNAL_LINKING_REPORT.md")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Report written to: {report_path}")
    print(f"Total lines: {len(lines)}")


if __name__ == "__main__":
    main()
