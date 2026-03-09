#!/usr/bin/env python3
"""
Google Ads 4-Year Data Normalization Pipeline

Reads exported Google Ads Script CSVs, normalizes product/campaign data
against current SKUs and historical replacement mappings, assigns categories,
and outputs a unified dataset for analysis.

Usage:
    python normalize_google_ads.py [--data-dir ./data] [--dry-run]

Input files (in data/ directory):
    - Campaigns_Structure.csv
    - Monthly_Campaign_Perf.csv
    - AdGroups_Keywords.csv
    - Search_Terms.csv
    - Shopping_Products.csv
    - Ad_Copy_Perf.csv
    - Geo_State_Perf.csv
    - Device_Perf.csv
    - Conversions_Setup.csv
    - Conversions_Volume_Summary.csv

Reference files (auto-discovered):
    - ../spring-2026-recovery/analysis/replacement_map_final.csv
    - ../spring-2026-recovery/data/products_active.json

Outputs (in data/ directory):
    - unified_4yr_performance.csv
    - sku_normalization_report.csv
    - unmatched_products.csv
    - category_performance_summary.csv
    - campaign_category_map.csv
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = SCRIPT_DIR / "data"

REPLACEMENT_MAP = PROJECT_ROOT / "spring-2026-recovery" / "analysis" / "replacement_map_final.csv"
PRODUCTS_ACTIVE = PROJECT_ROOT / "spring-2026-recovery" / "data" / "products_active.json"


# ── SKU Helpers (adapted from walmart-optimization/sku_matching.py) ─────────

def get_base_sku(sku):
    """
    Extract base SKU from a weight-variant SKU.
    e.g., "PB-ALPACA-10-LB-KIT" → "PB-ALPACA"
          "PB-ALPACA-10-LB"     → "PB-ALPACA"
          "WB-RM-0.5-LB"       → "WB-RM"
    """
    s = sku.upper().strip()
    # Remove ADDON suffix
    s = re.sub(r"-ADDON$", "", s)
    # Remove KIT suffix
    s = re.sub(r"-KIT$", "", s)
    # Remove weight pattern
    s = re.sub(r"-[\d.]+-(?:LB|OZ)$", "", s)
    return s


def normalize_product_title(title):
    """Normalize product title for fuzzy matching."""
    if not title:
        return ""
    t = title.lower().strip()
    # Remove size/weight suffixes
    t = re.sub(r"\s*[-–]\s*\d+[\d,.]*\s*(?:lb|oz|sq\s*ft|ft²|acre|acres?).*$", "", t, flags=re.IGNORECASE)
    # Remove parenthetical content
    t = re.sub(r"\s*\(.*?\)", "", t)
    # Remove trailing "seeds" / "seed" variations
    t = re.sub(r"\s+seeds?\s*$", "", t, flags=re.IGNORECASE)
    # Normalize whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


def title_similarity(t1, t2):
    """Simple word-overlap similarity between two titles (Jaccard)."""
    if not t1 or not t2:
        return 0.0
    words1 = set(t1.lower().split())
    words2 = set(t2.lower().split())
    # Remove very common words
    stopwords = {"seed", "seeds", "mix", "blend", "the", "a", "an", "for", "-", "&", "and"}
    words1 -= stopwords
    words2 -= stopwords
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


# ── Category Assignment (from business rules in MEMORY.md) ─────────────────

# Keywords that indicate category from campaign/product names
CATEGORY_KEYWORDS = {
    "Cover Crop": [
        "cover crop", "covercrop", "cover-crop", "cc-", "cc_"
    ],
    "Food Plot": [
        "food plot", "foodplot", "food-plot", "fp-", "fp_", "deer", "hunting",
        "wildlife", "game"
    ],
    "Clover": [
        "clover", "clov-", "dutch", "crimson clover", "white clover", "red clover"
    ],
    "Lawn Seed": [
        "lawn", "turf", "grass seed", "bermuda", "fescue", "bluegrass",
        "ryegrass", "zoysia", "buffalo", "bentgrass", "dichondra", "st. augustine",
        "centipede"
    ],
    "Wildflowers": [
        "wildflower", "wild flower", "poppy", "lupine", "sunflower",
        "flower mix", "pollinator", "butterfly", "hummingbird"
    ],
    "Pasture Seed": [
        "pasture", "forage", "hay", "rangeland", "erosion", "reclamation",
        "dryland", "irrigated pasture"
    ],
    "Planting Aid": [
        "tackifier", "m-binder", "rice hull", "spreader", "fertilizer",
        "sustane", "planting aid"
    ]
}


def assign_category(name, sku="", product_type=""):
    """
    Assign primary category based on business rules.
    Subcategories (Cover Crop, Food Plot, Clover) override Pasture Seed.
    """
    combined = f"{name} {sku} {product_type}".lower()

    # Check subcategories first (they override Pasture Seed)
    for cat in ["Cover Crop", "Food Plot", "Clover"]:
        for keyword in CATEGORY_KEYWORDS[cat]:
            if keyword in combined:
                return cat

    # Then check main categories
    for cat in ["Lawn Seed", "Wildflowers", "Pasture Seed", "Planting Aid"]:
        for keyword in CATEGORY_KEYWORDS[cat]:
            if keyword in combined:
                return cat

    return "Uncategorized"


def assign_campaign_category(campaign_name):
    """Assign category to a campaign based on its name."""
    return assign_category(campaign_name)


# ── Data Loading ───────────────────────────────────────────────────────────────

def load_csv(filepath):
    """Load a CSV file and return list of dicts."""
    if not filepath.exists():
        print(f"  [SKIP] {filepath.name} not found")
        return []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"  [OK] {filepath.name}: {len(rows)} rows")
    return rows


def load_active_products(filepath):
    """Load active products JSON and build lookup indexes."""
    if not filepath.exists():
        print(f"  [WARN] {filepath.name} not found — SKU matching will be limited")
        return {}, {}, {}

    with open(filepath, "r") as f:
        products = json.load(f)

    by_sku = {}
    by_name = {}
    by_id = {}

    for p in products:
        sku = p.get("sku", "").upper().strip()
        name = p.get("name", "")
        pid = str(p.get("id", ""))
        categories = [c.get("name", "") for c in p.get("categories", [])]

        entry = {
            "sku": sku,
            "name": name,
            "id": pid,
            "categories": categories,
            "permalink": p.get("permalink", ""),
            "price": p.get("price", ""),
            "status": p.get("status", "")
        }

        # Skip ADDON products
        if "-ADDON" in sku:
            continue

        if sku:
            by_sku[sku] = entry
            base = get_base_sku(sku)
            if base != sku:
                by_sku[base] = entry

        if name:
            normalized = normalize_product_title(name)
            by_name[normalized] = entry

        if pid:
            by_id[pid] = entry

    print(f"  [OK] Active products: {len(by_sku)} SKUs, {len(by_name)} names, {len(by_id)} IDs")
    return by_sku, by_name, by_id


def load_replacement_map(filepath):
    """Load the old→new SKU replacement map."""
    if not filepath.exists():
        print(f"  [WARN] {filepath.name} not found — historical SKU mapping unavailable")
        return {}

    mapping = {}
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            old_skus = row.get("old_variant_skus", "")
            new_sku = row.get("new_sku", "").upper().strip()
            old_name = row.get("old_base_name", "").strip()

            if not new_sku:
                continue

            # Map each old variant SKU to the new SKU
            for old_sku in old_skus.split(";"):
                old_sku = old_sku.strip().upper()
                if old_sku:
                    mapping[old_sku] = {
                        "new_sku": new_sku,
                        "old_name": old_name,
                        "new_name": row.get("new_name", ""),
                        "new_categories": row.get("new_categories", "")
                    }

            # Also map by old product name (normalized)
            if old_name:
                norm_name = normalize_product_title(old_name)
                mapping["NAME:" + norm_name] = {
                    "new_sku": new_sku,
                    "old_name": old_name,
                    "new_name": row.get("new_name", ""),
                    "new_categories": row.get("new_categories", "")
                }

    print(f"  [OK] Replacement map: {len(mapping)} old→new mappings")
    return mapping


# ── Shopping Product Normalization ─────────────────────────────────────────────

def normalize_shopping_products(shopping_rows, active_by_sku, active_by_name,
                                 active_by_id, replacement_map):
    """
    Match Shopping product data to current SKUs.
    Returns: (normalized_rows, normalization_report, unmatched)
    """
    report = []
    unmatched = []
    normalized = []

    for row in shopping_rows:
        item_id = (row.get("Product Item ID") or "").strip()
        title = (row.get("Product Title") or "").strip()
        product_type = (row.get("Product Type (L1)") or "").strip()

        match_method = "none"
        matched_sku = ""
        matched_name = ""
        matched_category = ""
        confidence = 0.0

        # 1. Direct SKU match on item_id
        item_upper = item_id.upper()
        if item_upper in active_by_sku:
            match_method = "direct_sku"
            matched_sku = active_by_sku[item_upper]["sku"]
            matched_name = active_by_sku[item_upper]["name"]
            matched_category = ", ".join(active_by_sku[item_upper]["categories"])
            confidence = 1.0

        # 2. Base SKU match
        if not matched_sku and item_id:
            base = get_base_sku(item_upper)
            if base in active_by_sku:
                match_method = "base_sku"
                matched_sku = active_by_sku[base]["sku"]
                matched_name = active_by_sku[base]["name"]
                matched_category = ", ".join(active_by_sku[base]["categories"])
                confidence = 0.9

        # 3. Replacement map by SKU
        if not matched_sku and item_upper in replacement_map:
            repl = replacement_map[item_upper]
            match_method = "replacement_map_sku"
            matched_sku = repl["new_sku"]
            matched_name = repl["new_name"]
            matched_category = repl.get("new_categories", "")
            confidence = 0.85

        # 4. Replacement map by base SKU
        if not matched_sku and item_id:
            base = get_base_sku(item_upper)
            if base in replacement_map:
                repl = replacement_map[base]
                match_method = "replacement_map_base"
                matched_sku = repl["new_sku"]
                matched_name = repl["new_name"]
                matched_category = repl.get("new_categories", "")
                confidence = 0.8

        # 5. Title-based match against active products
        if not matched_sku and title:
            norm_title = normalize_product_title(title)
            if norm_title in active_by_name:
                match_method = "title_exact"
                matched_sku = active_by_name[norm_title]["sku"]
                matched_name = active_by_name[norm_title]["name"]
                matched_category = ", ".join(active_by_name[norm_title]["categories"])
                confidence = 0.85

        # 6. Title-based fuzzy match
        if not matched_sku and title:
            norm_title = normalize_product_title(title)
            best_sim = 0.0
            best_entry = None
            for active_title, entry in active_by_name.items():
                sim = title_similarity(norm_title, active_title)
                if sim > best_sim and sim >= 0.5:
                    best_sim = sim
                    best_entry = entry
            if best_entry:
                match_method = f"title_fuzzy({best_sim:.2f})"
                matched_sku = best_entry["sku"]
                matched_name = best_entry["name"]
                matched_category = ", ".join(best_entry["categories"])
                confidence = best_sim * 0.8

        # 7. Replacement map by title
        if not matched_sku and title:
            norm_title = normalize_product_title(title)
            name_key = "NAME:" + norm_title
            if name_key in replacement_map:
                repl = replacement_map[name_key]
                match_method = "replacement_map_title"
                matched_sku = repl["new_sku"]
                matched_name = repl["new_name"]
                matched_category = repl.get("new_categories", "")
                confidence = 0.7

        # 8. Category from keywords if nothing else matched
        if not matched_category:
            matched_category = assign_category(title, item_id, product_type)

        # Build normalized row
        norm_row = dict(row)
        norm_row["Normalized SKU"] = matched_sku
        norm_row["Normalized Name"] = matched_name
        norm_row["Primary Category"] = matched_category or assign_category(title, item_id, product_type)
        norm_row["Match Method"] = match_method
        norm_row["Match Confidence"] = f"{confidence:.2f}"
        normalized.append(norm_row)

        # Report
        report.append({
            "Original Item ID": item_id,
            "Original Title": title,
            "Normalized SKU": matched_sku,
            "Normalized Name": matched_name,
            "Primary Category": norm_row["Primary Category"],
            "Match Method": match_method,
            "Confidence": f"{confidence:.2f}"
        })

        if not matched_sku:
            unmatched.append({
                "Original Item ID": item_id,
                "Original Title": title,
                "Product Type": product_type,
                "Campaign": row.get("Campaign Name", ""),
                "Total Cost": row.get("Cost ($)", "0"),
                "Total Conversions": row.get("Conversions", "0")
            })

    return normalized, report, unmatched


# ── Campaign Category Tagging ──────────────────────────────────────────────────

def tag_campaigns_with_categories(campaign_rows):
    """Assign category to each campaign based on name keywords."""
    tagged = []
    for row in campaign_rows:
        name = row.get("Campaign Name", "")
        category = assign_campaign_category(name)
        tagged_row = dict(row)
        tagged_row["Inferred Category"] = category
        tagged.append(tagged_row)
    return tagged


# ── Category Performance Summary ───────────────────────────────────────────────

def build_category_performance(monthly_perf_rows):
    """
    Aggregate monthly campaign performance by inferred category.
    Returns list of dicts with Year, Month, Category, and summed metrics.
    """
    agg = defaultdict(lambda: {
        "impressions": 0, "clicks": 0, "cost": 0.0,
        "conversions": 0.0, "conv_value": 0.0
    })

    for row in monthly_perf_rows:
        year = row.get("Year", "")
        month = row.get("Month", "")
        campaign_name = row.get("Campaign Name", "")
        category = assign_campaign_category(campaign_name)

        key = (year, month, category)

        agg[key]["impressions"] += int(row.get("Impressions", "0") or "0")
        agg[key]["clicks"] += int(row.get("Clicks", "0") or "0")

        cost_str = (row.get("Cost ($)", "0") or "0").replace(",", "")
        agg[key]["cost"] += float(cost_str)

        conv_str = (row.get("Conversions", "0") or "0").replace(",", "")
        agg[key]["conversions"] += float(conv_str)

        val_str = (row.get("Conv. Value ($)", "0") or "0").replace(",", "")
        agg[key]["conv_value"] += float(val_str)

    summary = []
    for (year, month, category), metrics in sorted(agg.items()):
        cost = metrics["cost"]
        conv_value = metrics["conv_value"]
        clicks = metrics["clicks"]
        impressions = metrics["impressions"]

        summary.append({
            "Year": year,
            "Month": month,
            "Category": category,
            "Impressions": impressions,
            "Clicks": clicks,
            "CTR": f"{(clicks / impressions * 100):.2f}%" if impressions > 0 else "0.00%",
            "Cost ($)": f"{cost:.2f}",
            "Conversions": f"{metrics['conversions']:.2f}",
            "Conv. Value ($)": f"{conv_value:.2f}",
            "ROAS": f"{(conv_value / cost):.2f}" if cost > 0 else "0.00",
            "Cost/Conv ($)": f"{(cost / metrics['conversions']):.2f}" if metrics["conversions"] > 0 else "N/A"
        })

    return summary


# ── Output Helpers ─────────────────────────────────────────────────────────────

def write_csv(filepath, rows, fieldnames=None):
    """Write list of dicts to CSV."""
    if not rows:
        print(f"  [SKIP] {filepath.name} — no data")
        return

    if not fieldnames:
        fieldnames = list(rows[0].keys())

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"  [OK] {filepath.name}: {len(rows)} rows written")


# ── Main Pipeline ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Normalize Google Ads 4-year data export")
    parser.add_argument("--data-dir", type=str, default=str(DATA_DIR),
                        help="Directory containing exported CSVs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Load and analyze without writing output files")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}")
        print("Export your Google Sheets tabs as CSVs into this directory first.")
        sys.exit(1)

    print("=" * 70)
    print("Google Ads 4-Year Data Normalization Pipeline")
    print("=" * 70)

    # ── Step 1: Load reference data ────────────────────────────────────────────
    print("\n[1/5] Loading reference data...")
    active_by_sku, active_by_name, active_by_id = load_active_products(PRODUCTS_ACTIVE)
    replacement_map = load_replacement_map(REPLACEMENT_MAP)

    # ── Step 2: Load exported CSVs ─────────────────────────────────────────────
    print("\n[2/5] Loading Google Ads export CSVs...")
    campaigns = load_csv(data_dir / "Campaigns_Structure.csv")
    monthly_perf = load_csv(data_dir / "Monthly_Campaign_Perf.csv")
    keywords = load_csv(data_dir / "AdGroups_Keywords.csv")
    search_terms = load_csv(data_dir / "Search_Terms.csv")
    shopping = load_csv(data_dir / "Shopping_Products.csv")
    ad_copy = load_csv(data_dir / "Ad_Copy_Perf.csv")
    geo = load_csv(data_dir / "Geo_State_Perf.csv")
    device = load_csv(data_dir / "Device_Perf.csv")
    conversions = load_csv(data_dir / "Conversions_Setup.csv")
    conv_volume = load_csv(data_dir / "Conversions_Volume_Summary.csv")

    # ── Step 3: Normalize Shopping Products ────────────────────────────────────
    print("\n[3/5] Normalizing Shopping product data...")
    if shopping:
        normalized_shopping, norm_report, unmatched = normalize_shopping_products(
            shopping, active_by_sku, active_by_name, active_by_id, replacement_map
        )

        matched = sum(1 for r in norm_report if r["Match Method"] != "none")
        total = len(norm_report)
        print(f"  Matched: {matched}/{total} ({matched/total*100:.1f}%)")

        # Show match method distribution
        method_counts = defaultdict(int)
        for r in norm_report:
            method_counts[r["Match Method"]] += 1
        for method, count in sorted(method_counts.items(), key=lambda x: -x[1]):
            print(f"    {method}: {count}")
    else:
        normalized_shopping, norm_report, unmatched = [], [], []
        print("  No Shopping data to normalize.")

    # ── Step 4: Tag campaigns with categories ──────────────────────────────────
    print("\n[4/5] Tagging campaigns with categories...")
    if campaigns:
        tagged_campaigns = tag_campaigns_with_categories(campaigns)
        cat_counts = defaultdict(int)
        for tc in tagged_campaigns:
            cat_counts[tc["Inferred Category"]] += 1
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            print(f"    {cat}: {count} campaigns")
    else:
        tagged_campaigns = []
        print("  No campaign data to tag.")

    # Build category performance summary
    if monthly_perf:
        cat_summary = build_category_performance(monthly_perf)
    else:
        cat_summary = []

    # ── Step 5: Write output files ─────────────────────────────────────────────
    print("\n[5/5] Writing output files...")

    if args.dry_run:
        print("  [DRY RUN] — skipping file writes")
    else:
        # Unified performance: normalized shopping data
        if normalized_shopping:
            write_csv(data_dir / "unified_4yr_performance.csv", normalized_shopping)

        # SKU normalization report
        if norm_report:
            write_csv(data_dir / "sku_normalization_report.csv", norm_report)

        # Unmatched products for manual review
        if unmatched:
            # Deduplicate unmatched by item ID
            seen = set()
            unique_unmatched = []
            for u in unmatched:
                key = u["Original Item ID"] + "|" + u["Original Title"]
                if key not in seen:
                    seen.add(key)
                    unique_unmatched.append(u)
            write_csv(data_dir / "unmatched_products.csv", unique_unmatched)
        else:
            print("  [OK] No unmatched products!")

        # Category performance summary
        if cat_summary:
            write_csv(data_dir / "category_performance_summary.csv", cat_summary)

        # Campaign category map
        if tagged_campaigns:
            campaign_cat_fields = ["Campaign ID", "Campaign Name", "Status",
                                    "Channel Type", "Inferred Category"]
            write_csv(data_dir / "campaign_category_map.csv", tagged_campaigns,
                      fieldnames=campaign_cat_fields)

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Campaigns loaded:        {len(campaigns)}")
    print(f"  Monthly perf rows:       {len(monthly_perf)}")
    print(f"  Keywords:                {len(keywords)}")
    print(f"  Search terms:            {len(search_terms)}")
    print(f"  Shopping products:       {len(shopping)}")
    print(f"  Ad copies:               {len(ad_copy)}")
    print(f"  Geo rows:                {len(geo)}")
    print(f"  Device rows:             {len(device)}")
    print(f"  Conversion actions:      {len(conversions)}")
    if shopping:
        matched = sum(1 for r in norm_report if r["Match Method"] != "none")
        print(f"  Shopping SKU match rate:  {matched}/{len(norm_report)} ({matched/len(norm_report)*100:.1f}%)")
        print(f"  Unmatched (need review):  {len(set(u['Original Item ID'] + '|' + u['Original Title'] for u in unmatched))}")
    print("=" * 70)

    if not args.dry_run:
        print("\nOutput files written to:", data_dir)
        print("Next steps:")
        print("  1. Review unmatched_products.csv for manual SKU mapping")
        print("  2. Review campaign_category_map.csv for category accuracy")
        print("  3. Use unified_4yr_performance.csv + category_performance_summary.csv for analysis")


if __name__ == "__main__":
    main()
