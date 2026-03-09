#!/usr/bin/env python3
"""
Build comprehensive SKU migration map between old Google Ads product IDs
and new Google Merchant Center product IDs for Nature's Seed.

Matching methods (in priority order):
1. Exact MPN match in merchant feed
2. Base SKU match (strip size suffixes from old ID, match to new MPN base)
3. Replacement map lookup (old variant SKUs → new SKU → merchant feed)
4. Title similarity matching (normalized product names)

Output:
- sku_migration_map.csv: Full mapping with match details
- sku_migration_summary.txt: Coverage statistics
"""

import csv
import re
import os
from collections import defaultdict
from difflib import SequenceMatcher

# --- Paths ---
BASE = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/data"
SHOPPING_CSV = os.path.join(BASE, "Shopping_Products.csv")
MERCHANT_CSV = os.path.join(BASE, "merchant_feed_summary.csv")
REPLACEMENT_CSV = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/spring-2026-recovery/analysis/replacement_map_final.csv"
OUTPUT_MAP = os.path.join(BASE, "sku_migration_map.csv")
OUTPUT_SUMMARY = os.path.join(BASE, "sku_migration_summary.txt")

# --- User-confirmed mappings ---
CONFIRMED_MAPPINGS = {
    "s-trre": ["gla_447280", "gla_447281", "gla_447282"],
    "s-micro": ["gla_451060", "gla_451061", "gla_451062"],
}

# =====================================================================
# Step 1: Load merchant feed — build lookup structures
# =====================================================================
def load_merchant_feed(path):
    """Load merchant feed and build multiple lookup indices."""
    items = []
    by_id = {}          # gla_XXXX → item
    by_mpn = {}         # MPN (lowercase) → [items]
    by_mpn_base = {}    # base MPN (no size suffix) → [items]

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gla_id = row["id"].strip().replace("\n", "")
            mpn = row["mpn"].strip()
            title = row["Title"].strip()

            if not gla_id or not mpn:
                continue

            item = {
                "id": gla_id,
                "mpn": mpn,
                "title": title,
                "price": row.get("price", ""),
                "product_type": row.get("Product_Type", ""),
            }
            items.append(item)
            by_id[gla_id] = item

            mpn_lower = mpn.lower()
            by_mpn.setdefault(mpn_lower, []).append(item)

            base = extract_base_sku(mpn_lower)
            by_mpn_base.setdefault(base, []).append(item)

    return items, by_id, by_mpn, by_mpn_base


def extract_base_sku(sku):
    """Extract base SKU by stripping size/variant suffixes.

    Examples:
        PB-ALPACA-10-LB → pb-alpaca
        PG-FEAR2-50-LB-KIT → pg-fear2
        S-FEOV-25-LB-OLD → s-feov
        TURF-FF-5000-F → turf-ff
        WB-AN-500-F-OLD → wb-an
        S-DUTCH-5-LB-ADDON → s-dutch
        CV-BGEC-10-LB → cv-bgec
        TURF-BUDA-1000-F → turf-buda
        TURF-W-BLUE-5-LB-OLD → turf-w-blue
        PB-COW-NTR-10-LB → pb-cow-ntr
    """
    s = sku.lower().strip()
    # Remove -OLD suffix
    s = re.sub(r'-old$', '', s)
    # Remove -ADDON suffix
    s = re.sub(r'-addon$', '', s)
    # Remove -KIT suffix
    s = re.sub(r'-kit$', '', s)
    # Remove size patterns: -NN-LB, -NN.N-LB
    s = re.sub(r'-\d+\.?\d*-lb$', '', s)
    # Remove area patterns: -NNNN-F (e.g., -5000-F, -500-F)
    s = re.sub(r'-\d+-f$', '', s)
    # Remove acreage patterns: -N.N-A, -N-A (e.g., -2.5-A, -0.5-A, -1-A)
    s = re.sub(r'-\d+\.?\d*-a$', '', s)
    # Remove -0.25-A patterns
    s = re.sub(r'-\d+\.\d+-a$', '', s)
    # Remove trailing -NN-LBS patterns (e.g., PB-PLPR-16-LBS)
    s = re.sub(r'-\d+-lbs$', '', s)
    # Remove trailing -N.N-LB-KIT patterns already handled, but double-check
    s = re.sub(r'-\d+\.?\d*-lb-kit$', '', s)
    # Remove trailing size like -0.5-LB
    s = re.sub(r'-\d+\.?\d*-lb$', '', s)

    return s


# =====================================================================
# Step 2: Load old shopping products — aggregate by product item ID
# =====================================================================
def load_shopping_products(path):
    """Load shopping products CSV and aggregate by Product Item ID."""
    agg = {}

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["Product Item ID"].strip().lower()
            title = row["Product Title"].strip()

            if not pid:
                continue

            try:
                cost = float(row["Cost ($)"].replace(",", ""))
            except (ValueError, KeyError):
                cost = 0.0
            try:
                revenue = float(row["Conv. Value ($)"].replace(",", ""))
            except (ValueError, KeyError):
                revenue = 0.0
            try:
                impressions = int(row["Impressions"].replace(",", ""))
            except (ValueError, KeyError):
                impressions = 0
            try:
                clicks = int(row["Clicks"].replace(",", ""))
            except (ValueError, KeyError):
                clicks = 0

            if pid not in agg:
                agg[pid] = {
                    "product_id": pid,
                    "title": title,   # keep first title seen
                    "total_spend": 0.0,
                    "total_revenue": 0.0,
                    "total_impressions": 0,
                    "total_clicks": 0,
                    "titles_seen": set(),
                }

            agg[pid]["total_spend"] += cost
            agg[pid]["total_revenue"] += revenue
            agg[pid]["total_impressions"] += impressions
            agg[pid]["total_clicks"] += clicks
            agg[pid]["titles_seen"].add(title)

    # Sort by revenue descending
    products = sorted(agg.values(), key=lambda x: x["total_revenue"], reverse=True)
    return products


# =====================================================================
# Step 3: Load replacement map — build old_sku → new_sku lookup
# =====================================================================
def load_replacement_map(path):
    """Load replacement map and build old variant SKU → new SKU lookup."""
    old_to_new = {}         # old_variant_sku (lower) → new_sku
    old_name_to_new = {}    # old_base_name (lower) → new_sku
    new_sku_to_name = {}    # new_sku (lower) → new_name

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            old_name = row.get("old_base_name", "").strip()
            old_variants = row.get("old_variant_skus", "").strip()
            new_sku = row.get("new_sku", "").strip()
            new_name = row.get("new_name", "").strip()

            if not new_sku:
                continue

            new_sku_to_name[new_sku.lower()] = new_name

            if old_name:
                old_name_to_new[old_name.lower()] = new_sku

            if old_variants:
                for variant in old_variants.split(";"):
                    variant = variant.strip()
                    if variant and variant != "-OLD":
                        # Store both with and without -OLD
                        v_lower = variant.lower()
                        old_to_new[v_lower] = new_sku
                        # Also store stripped version
                        v_stripped = re.sub(r'-old$', '', v_lower)
                        old_to_new[v_stripped] = new_sku
                        # Also store just the base
                        v_base = extract_base_sku(v_lower)
                        if v_base not in old_to_new:
                            old_to_new[v_base] = new_sku

    return old_to_new, old_name_to_new, new_sku_to_name


# =====================================================================
# Step 4: Title normalization for fuzzy matching
# =====================================================================
def normalize_title(title):
    """Normalize a product title for comparison."""
    t = title.lower()
    # Remove "| Nature's Seed" suffix
    t = re.sub(r"\s*\|\s*nature'?s?\s*seed\s*$", "", t)
    # Remove size info like "5 lb", "10 lb", "50 lb", "25 lb"
    t = re.sub(r'\b\d+\.?\d*\s*(lb|lbs)\b', '', t)
    # Remove coverage info like "Covers 20,000 sq ft", "10,000 Sq Ft"
    t = re.sub(r'covers?\s+[\d,]+\s*sq\.?\s*ft\.?', '', t, flags=re.IGNORECASE)
    t = re.sub(r'[\d,]+\s*sq\.?\s*ft\.?', '', t, flags=re.IGNORECASE)
    # Remove "Bulk bags available"
    t = re.sub(r'bulk\s+bags?\s+available', '', t)
    # Remove "No added filler"
    t = re.sub(r'no\s+added\s+filler', '', t)
    # Remove size designators in parentheses
    t = re.sub(r'\(\d+\s*(lb|oz|ft)\)', '', t, flags=re.IGNORECASE)
    # Remove dashes that are used as separators with spaces
    t = re.sub(r'\s+-\s+', ' ', t)
    # Remove extra whitespace and punctuation
    t = re.sub(r'[,\-\(\)]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def title_similarity(t1, t2):
    """Compute similarity between two normalized titles."""
    n1 = normalize_title(t1)
    n2 = normalize_title(t2)

    # Check if one contains the other
    if n1 in n2 or n2 in n1:
        return 0.90

    # Use SequenceMatcher
    return SequenceMatcher(None, n1, n2).ratio()


def extract_core_product_name(title):
    """Extract core product name keywords for matching."""
    t = normalize_title(title)
    # Remove common generic words
    stop_words = {"seed", "seeds", "mix", "blend", "grass", "pasture", "forage",
                  "nature's", "natures", "premium", "organic", "native", "bulk",
                  "for", "the", "and", "a", "of", "in", "with", "&"}
    words = [w for w in t.split() if w not in stop_words and len(w) > 1]
    return " ".join(words)


# =====================================================================
# Step 5: Main matching logic
# =====================================================================
def find_matches(old_product, merchant_items, by_mpn, by_mpn_base,
                 old_to_new, old_name_to_new, new_sku_to_name,
                 by_id=None):
    """Find matching new product(s) for an old product. Returns list of matches."""

    pid = old_product["product_id"]
    old_title = old_product["title"]
    matches = []

    # --- Check user-confirmed mappings first ---
    if pid in CONFIRMED_MAPPINGS:
        for gla_id in CONFIRMED_MAPPINGS[pid]:
            # Find the item details
            for item in merchant_items:
                if item["id"] == gla_id:
                    matches.append({
                        "new_product_id": item["id"],
                        "new_title": item["title"],
                        "match_method": "user_confirmed",
                        "match_confidence": "high",
                    })
                    break
            else:
                matches.append({
                    "new_product_id": gla_id,
                    "new_title": "(ID from confirmed mapping)",
                    "match_method": "user_confirmed",
                    "match_confidence": "high",
                })
        if matches:
            return matches

    # --- Method 0: Direct gla_ ID match ---
    # If old product ID is a gla_ or gs1- ID, check if it exists in the current feed
    if by_id and (pid.startswith("gla_") or pid.startswith("gs1-")):
        if pid in by_id:
            item = by_id[pid]
            # Return this item plus all its size variants
            item_base = extract_base_sku(item["mpn"].lower())
            if item_base in by_mpn_base:
                for variant in by_mpn_base[item_base]:
                    if "-addon" in variant["mpn"].lower():
                        continue
                    matches.append({
                        "new_product_id": variant["id"],
                        "new_title": variant["title"],
                        "match_method": "direct_gla_id_match",
                        "match_confidence": "high",
                    })
            if not matches:
                matches.append({
                    "new_product_id": item["id"],
                    "new_title": item["title"],
                    "match_method": "direct_gla_id_match",
                    "match_confidence": "high",
                })
            return matches

    # --- Method 1: Exact MPN match ---
    # Check if the old product_id matches any MPN in the feed exactly
    if pid in by_mpn:
        for item in by_mpn[pid]:
            matches.append({
                "new_product_id": item["id"],
                "new_title": item["title"],
                "match_method": "exact_mpn_match",
                "match_confidence": "high",
            })
        return matches

    # --- Method 2: Base SKU match ---
    old_base = extract_base_sku(pid)
    if old_base in by_mpn_base:
        for item in by_mpn_base[old_base]:
            # Skip ADDON products
            if "-addon" in item["mpn"].lower():
                continue
            matches.append({
                "new_product_id": item["id"],
                "new_title": item["title"],
                "match_method": "base_sku_match",
                "match_confidence": "high",
            })
        if matches:
            return matches

    # --- Method 3: Replacement map lookup ---
    # Check if old pid or its base appears in replacement map
    new_sku = None

    # Direct variant lookup
    if pid in old_to_new:
        new_sku = old_to_new[pid]
    elif old_base in old_to_new:
        new_sku = old_to_new[old_base]

    # Also try with -OLD suffix patterns
    if not new_sku:
        pid_with_old = pid + "-old"
        if pid_with_old in old_to_new:
            new_sku = old_to_new[pid_with_old]

    if new_sku:
        # Find all merchant feed items matching this new_sku
        new_base = extract_base_sku(new_sku.lower())
        if new_base in by_mpn_base:
            for item in by_mpn_base[new_base]:
                if "-addon" in item["mpn"].lower():
                    continue
                matches.append({
                    "new_product_id": item["id"],
                    "new_title": item["title"],
                    "match_method": "replacement_map",
                    "match_confidence": "medium",
                })
            if matches:
                return matches

        # Try exact new_sku match
        if new_sku.lower() in by_mpn:
            for item in by_mpn[new_sku.lower()]:
                matches.append({
                    "new_product_id": item["id"],
                    "new_title": item["title"],
                    "match_method": "replacement_map",
                    "match_confidence": "medium",
                })
            if matches:
                return matches

    # --- Method 3b: Old name → replacement map name match ---
    for title_variant in old_product["titles_seen"]:
        clean = normalize_title(title_variant).strip()
        for old_name_key, r_new_sku in old_name_to_new.items():
            if SequenceMatcher(None, clean, old_name_key).ratio() > 0.75:
                r_base = extract_base_sku(r_new_sku.lower())
                if r_base in by_mpn_base:
                    for item in by_mpn_base[r_base]:
                        if "-addon" in item["mpn"].lower():
                            continue
                        matches.append({
                            "new_product_id": item["id"],
                            "new_title": item["title"],
                            "match_method": "replacement_map_title",
                            "match_confidence": "medium",
                        })
                    if matches:
                        return matches

    # --- Method 4: Title similarity matching ---
    best_score = 0
    best_items = []

    for item in merchant_items:
        if "-addon" in item["mpn"].lower():
            continue
        score = title_similarity(old_title, item["title"])
        if score > best_score:
            best_score = score
            best_items = [item]
        elif score == best_score and score > 0.5:
            best_items.append(item)

    if best_score >= 0.55:
        # Also find all size variants of the best match
        if best_items:
            best_base = extract_base_sku(best_items[0]["mpn"].lower())
            all_variants = by_mpn_base.get(best_base, [])
            for item in all_variants:
                if "-addon" in item["mpn"].lower():
                    continue
                confidence = "medium" if best_score >= 0.70 else "low"
                matches.append({
                    "new_product_id": item["id"],
                    "new_title": item["title"],
                    "match_method": f"title_similarity_{best_score:.2f}",
                    "match_confidence": confidence,
                })
        if matches:
            return matches

    # --- No match found ---
    return []


# =====================================================================
# Step 6: Main execution
# =====================================================================
def main():
    print("Loading merchant feed...")
    merchant_items, by_id, by_mpn, by_mpn_base = load_merchant_feed(MERCHANT_CSV)
    print(f"  → {len(merchant_items)} live products loaded")
    print(f"  → {len(by_mpn_base)} unique base SKUs")

    print("\nLoading shopping products...")
    old_products = load_shopping_products(SHOPPING_CSV)
    print(f"  → {len(old_products)} unique old product IDs")
    total_revenue = sum(p["total_revenue"] for p in old_products)
    print(f"  → ${total_revenue:,.2f} total historical revenue")

    print("\nLoading replacement map...")
    old_to_new, old_name_to_new, new_sku_to_name = load_replacement_map(REPLACEMENT_CSV)
    print(f"  → {len(old_to_new)} old→new SKU mappings")
    print(f"  → {len(old_name_to_new)} old name→new SKU mappings")

    print("\n" + "=" * 70)
    print("MATCHING OLD PRODUCTS TO NEW MERCHANT FEED")
    print("=" * 70)

    # Process all products
    results = []
    matched_count = 0
    unmatched_count = 0
    matched_revenue = 0.0
    unmatched_revenue = 0.0
    matched_spend = 0.0
    unmatched_spend = 0.0

    method_counts = defaultdict(int)
    confidence_counts = defaultdict(int)

    for i, prod in enumerate(old_products):
        pid = prod["product_id"]
        roas = (prod["total_revenue"] / prod["total_spend"]) if prod["total_spend"] > 0 else 0

        matches = find_matches(
            prod, merchant_items, by_mpn, by_mpn_base,
            old_to_new, old_name_to_new, new_sku_to_name,
            by_id=by_id
        )

        if matches:
            matched_count += 1
            matched_revenue += prod["total_revenue"]
            matched_spend += prod["total_spend"]
            for m in matches:
                base_method = m["match_method"].split("_similarity_")[0] if "_similarity_" in m["match_method"] else m["match_method"]
                method_counts[base_method] += 1
                confidence_counts[m["match_confidence"]] += 1
                results.append({
                    "old_product_id": pid,
                    "old_title": prod["title"],
                    "old_total_spend": f"{prod['total_spend']:.2f}",
                    "old_total_revenue": f"{prod['total_revenue']:.2f}",
                    "old_roas": f"{roas:.2f}",
                    "new_product_id": m["new_product_id"],
                    "new_title": m["new_title"],
                    "match_method": m["match_method"],
                    "match_confidence": m["match_confidence"],
                })
        else:
            unmatched_count += 1
            unmatched_revenue += prod["total_revenue"]
            unmatched_spend += prod["total_spend"]
            results.append({
                "old_product_id": pid,
                "old_title": prod["title"],
                "old_total_spend": f"{prod['total_spend']:.2f}",
                "old_total_revenue": f"{prod['total_revenue']:.2f}",
                "old_roas": f"{roas:.2f}",
                "new_product_id": "UNMATCHED",
                "new_title": "",
                "match_method": "none",
                "match_confidence": "none",
            })

        # Progress for top products
        if i < 10 or (i < 100 and i % 10 == 0):
            status = f"MATCHED ({matches[0]['match_method']})" if matches else "UNMATCHED"
            print(f"  [{i+1:3d}] {pid:40s} ${prod['total_revenue']:>10,.2f}  → {status}")

    # =====================================================================
    # Write CSV output
    # =====================================================================
    print(f"\nWriting {len(results)} rows to {OUTPUT_MAP}...")
    fieldnames = [
        "old_product_id", "old_title", "old_total_spend", "old_total_revenue",
        "old_roas", "new_product_id", "new_title", "match_method", "match_confidence"
    ]
    with open(OUTPUT_MAP, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # =====================================================================
    # Compute top-100 stats
    # =====================================================================
    top100 = old_products[:100]
    top100_total_rev = sum(p["total_revenue"] for p in top100)
    top100_matched_rev = 0.0
    top100_matched = 0
    for prod in top100:
        m = find_matches(prod, merchant_items, by_mpn, by_mpn_base,
                         old_to_new, old_name_to_new, new_sku_to_name,
                         by_id=by_id)
        if m:
            top100_matched += 1
            top100_matched_rev += prod["total_revenue"]

    # =====================================================================
    # Unmatched analysis
    # =====================================================================
    unmatched_prods = [p for p in old_products if not find_matches(
        p, merchant_items, by_mpn, by_mpn_base,
        old_to_new, old_name_to_new, new_sku_to_name,
        by_id=by_id
    )]
    unmatched_prods.sort(key=lambda x: x["total_revenue"], reverse=True)

    # =====================================================================
    # Write summary
    # =====================================================================
    summary_lines = []
    summary_lines.append("=" * 70)
    summary_lines.append("SKU MIGRATION MAP — SUMMARY REPORT")
    summary_lines.append(f"Nature's Seed — Google Ads → Merchant Center Mapping")
    summary_lines.append("=" * 70)
    summary_lines.append("")
    summary_lines.append("OVERALL STATISTICS")
    summary_lines.append("-" * 40)
    summary_lines.append(f"Total unique old products:     {len(old_products):>6d}")
    summary_lines.append(f"Matched to live products:      {matched_count:>6d}  ({matched_count/len(old_products)*100:.1f}%)")
    summary_lines.append(f"Unmatched (no live product):    {unmatched_count:>6d}  ({unmatched_count/len(old_products)*100:.1f}%)")
    summary_lines.append("")
    summary_lines.append("REVENUE COVERAGE")
    summary_lines.append("-" * 40)
    summary_lines.append(f"Total historical revenue:      ${total_revenue:>12,.2f}")
    summary_lines.append(f"Matched revenue:               ${matched_revenue:>12,.2f}  ({matched_revenue/total_revenue*100:.1f}%)")
    summary_lines.append(f"Unmatched revenue:             ${unmatched_revenue:>12,.2f}  ({unmatched_revenue/total_revenue*100:.1f}%)")
    summary_lines.append("")
    summary_lines.append("SPEND COVERAGE")
    summary_lines.append("-" * 40)
    total_spend = sum(p["total_spend"] for p in old_products)
    summary_lines.append(f"Total historical spend:        ${total_spend:>12,.2f}")
    summary_lines.append(f"Matched spend:                 ${matched_spend:>12,.2f}  ({matched_spend/total_spend*100:.1f}%)")
    summary_lines.append(f"Unmatched spend:               ${unmatched_spend:>12,.2f}  ({unmatched_spend/total_spend*100:.1f}%)")
    summary_lines.append("")
    summary_lines.append("TOP 100 PRODUCTS (BY REVENUE)")
    summary_lines.append("-" * 40)
    summary_lines.append(f"Top 100 total revenue:         ${top100_total_rev:>12,.2f}")
    summary_lines.append(f"Top 100 matched:               {top100_matched:>6d} / 100")
    summary_lines.append(f"Top 100 matched revenue:       ${top100_matched_rev:>12,.2f}  ({top100_matched_rev/top100_total_rev*100:.1f}%)")
    summary_lines.append("")
    summary_lines.append("MATCH METHOD BREAKDOWN")
    summary_lines.append("-" * 40)
    for method, count in sorted(method_counts.items(), key=lambda x: -x[1]):
        summary_lines.append(f"  {method:30s}  {count:>5d} rows")
    summary_lines.append("")
    summary_lines.append("MATCH CONFIDENCE BREAKDOWN")
    summary_lines.append("-" * 40)
    for conf, count in sorted(confidence_counts.items(), key=lambda x: -x[1]):
        summary_lines.append(f"  {conf:30s}  {count:>5d} rows")
    summary_lines.append("")
    summary_lines.append("TOP 20 UNMATCHED PRODUCTS (BY REVENUE)")
    summary_lines.append("-" * 70)
    summary_lines.append(f"{'Rank':>4s}  {'Product ID':30s}  {'Revenue':>12s}  {'Spend':>10s}  Title")
    summary_lines.append("-" * 70)
    for i, prod in enumerate(unmatched_prods[:20]):
        summary_lines.append(
            f"{i+1:>4d}  {prod['product_id']:30s}  "
            f"${prod['total_revenue']:>10,.2f}  "
            f"${prod['total_spend']:>8,.2f}  "
            f"{prod['title'][:60]}"
        )

    summary_lines.append("")
    summary_lines.append("=" * 70)
    summary_lines.append("TOP 30 MATCHED PRODUCTS (BY REVENUE)")
    summary_lines.append("-" * 70)
    summary_lines.append(f"{'Rank':>4s}  {'Old ID':25s}  {'Revenue':>12s}  {'Method':25s}  New Product")
    summary_lines.append("-" * 70)

    seen = set()
    rank = 0
    for prod in old_products:
        if rank >= 30:
            break
        matches = find_matches(prod, merchant_items, by_mpn, by_mpn_base,
                               old_to_new, old_name_to_new, new_sku_to_name,
                               by_id=by_id)
        if matches and prod["product_id"] not in seen:
            seen.add(prod["product_id"])
            rank += 1
            first_match = matches[0]
            summary_lines.append(
                f"{rank:>4d}  {prod['product_id']:25s}  "
                f"${prod['total_revenue']:>10,.2f}  "
                f"{first_match['match_method']:25s}  "
                f"{first_match['new_product_id']} ({first_match['new_title'][:40]})"
            )

    summary_text = "\n".join(summary_lines)

    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary_text)

    print("\n" + summary_text)
    print(f"\nOutput files:")
    print(f"  Map:     {OUTPUT_MAP}")
    print(f"  Summary: {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
