#!/usr/bin/env python3
"""
Google Ads Audit — FINAL Implementation File Builder
=====================================================
Uses the SKU migration map to aggregate historical performance onto
live merchant-feed products, then produces 6 output files.

Input files:
  1. sku_migration_map.csv  — old_product_id -> new_product_id with spend/revenue
  2. merchant_feed_summary.csv — 280 live products with categories/labels
  3. Shopping_Products.csv — raw historical data (used only as reference; migration map already has aggregates)

Output files (written to ./):
  1. FINAL_star_products.csv
  2. FINAL_hidden_gems.csv
  3. FINAL_forage_products.csv
  4. FINAL_zero_conv_live.csv
  5. FINAL_product_exclusion_ids.txt
  6. FINAL_budget_reallocation.txt
"""

import csv
import os
from collections import defaultdict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUT_DIR = os.path.dirname(__file__)  # write next to this script

MIGRATION_MAP = os.path.join(DATA_DIR, "sku_migration_map.csv")
MERCHANT_FEED = os.path.join(DATA_DIR, "merchant_feed_summary.csv")

# ---------------------------------------------------------------------------
# 1. Load merchant feed  (keyed by id)
# ---------------------------------------------------------------------------
feed = {}  # id -> row dict
with open(MERCHANT_FEED, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        pid = row["id"].strip()
        feed[pid] = {
            "id": pid,
            "title": row["Title"].strip(),
            "price": row["price"].strip(),
            "product_type": row["Product_Type"].strip(),
            "custom_label_0": row["Custom_label_0"].strip(),
            "custom_label_1": row["Custom_label_1"].strip(),
            "custom_label_2": row["Custom_label_2"].strip(),
            "custom_label_3": row["Custom_label_3"].strip(),
            "custom_label_4": row["Custom_label_4"].strip(),
        }

print(f"Loaded {len(feed)} live merchant-feed products.")

# ---------------------------------------------------------------------------
# 2. Load migration map and aggregate by new_product_id
#    IMPORTANT: An old product with spend $X maps to N new products.
#    The old spend/revenue should be counted ONCE per old product, then
#    split equally among the N new products it maps to (variant-level split).
# ---------------------------------------------------------------------------

# First pass: figure out how many new products each old product maps to
old_to_new_count = defaultdict(int)
with open(MIGRATION_MAP, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        old_id = row["old_product_id"].strip()
        new_id = row["new_product_id"].strip()
        if new_id and new_id in feed:
            old_to_new_count[old_id] += 1

# Second pass: aggregate spend/revenue per new_product_id,
# splitting each old product's totals evenly across its N new mappings.
# Also track which old products map to each new product.
agg = defaultdict(lambda: {"spend": 0.0, "revenue": 0.0, "old_ids": set()})

with open(MIGRATION_MAP, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        old_id = row["old_product_id"].strip()
        new_id = row["new_product_id"].strip()
        if not new_id or new_id not in feed:
            continue

        n = old_to_new_count[old_id]
        if n == 0:
            continue

        spend = float(row["old_total_spend"].strip())
        revenue = float(row["old_total_revenue"].strip())

        agg[new_id]["spend"] += spend / n
        agg[new_id]["revenue"] += revenue / n
        agg[new_id]["old_ids"].add(old_id)

print(f"Aggregated historical data for {len(agg)} live products (from migration map).")

# ---------------------------------------------------------------------------
# Helper: compute ROAS safely
# ---------------------------------------------------------------------------
def roas(revenue, spend):
    if spend <= 0:
        return float("inf") if revenue > 0 else 0.0
    return revenue / spend


# ---------------------------------------------------------------------------
# 3. Build enriched rows (merge agg + feed)
# ---------------------------------------------------------------------------
enriched = []
for pid, info in feed.items():
    a = agg.get(pid, {"spend": 0.0, "revenue": 0.0, "old_ids": set()})
    r = roas(a["revenue"], a["spend"])
    enriched.append({
        "new_product_id": pid,
        "current_title": info["title"],
        "product_type": info["product_type"],
        "custom_label_0": info["custom_label_0"],
        "custom_label_1": info["custom_label_1"],
        "custom_label_2": info["custom_label_2"],
        "custom_label_3": info["custom_label_3"],
        "custom_label_4": info["custom_label_4"],
        "price": info["price"],
        "total_historical_spend": round(a["spend"], 2),
        "total_historical_revenue": round(a["revenue"], 2),
        "aggregated_roas": round(r, 2) if r != float("inf") else 999.99,
        "old_product_ids_mapped": ", ".join(sorted(a["old_ids"])) if a["old_ids"] else "",
    })

# ===================================================================
# FILE 1: FINAL_star_products.csv
#   ROAS > 4x AND revenue > $3,000
# ===================================================================
stars = [
    r for r in enriched
    if r["aggregated_roas"] > 4 and r["total_historical_revenue"] > 3000
]
stars.sort(key=lambda r: r["total_historical_revenue"], reverse=True)

star_cols = [
    "new_product_id", "current_title", "product_type", "custom_label_0",
    "price", "total_historical_spend", "total_historical_revenue",
    "aggregated_roas", "old_product_ids_mapped",
]
with open(os.path.join(OUT_DIR, "FINAL_star_products.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=star_cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(stars)

print(f"[1] FINAL_star_products.csv — {len(stars)} products")

# ===================================================================
# FILE 2: FINAL_hidden_gems.csv
#   ROAS > 5x AND spend < $1,000 AND revenue > 0
# ===================================================================
gems = [
    r for r in enriched
    if r["aggregated_roas"] > 5
    and r["total_historical_spend"] < 1000
    and r["total_historical_spend"] > 0
    and r["total_historical_revenue"] > 0
]
gems.sort(key=lambda r: r["aggregated_roas"], reverse=True)

with open(os.path.join(OUT_DIR, "FINAL_hidden_gems.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=star_cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(gems)

print(f"[2] FINAL_hidden_gems.csv — {len(gems)} products")

# ===================================================================
# FILE 3: FINAL_forage_products.csv
#   Product Type contains any forage/animal/food plot keyword
# ===================================================================
FORAGE_KEYWORDS = [
    "horse forage", "sheep forage", "cow forage", "goat forage",
    "pig forage", "tortoise forage", "poultry", "alpaca", "llama",
    "food plot",
]

def is_forage(product_type):
    pt_lower = product_type.lower()
    return any(kw in pt_lower for kw in FORAGE_KEYWORDS)

forage = [r for r in enriched if is_forage(r["product_type"])]
forage.sort(key=lambda r: r["total_historical_revenue"], reverse=True)

forage_cols = [
    "new_product_id", "current_title", "product_type", "custom_label_0",
    "price", "total_historical_spend", "total_historical_revenue",
    "aggregated_roas", "old_product_ids_mapped",
]
with open(os.path.join(OUT_DIR, "FINAL_forage_products.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=forage_cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(forage)

print(f"[3] FINAL_forage_products.csv — {len(forage)} products")

# ===================================================================
# FILE 4: FINAL_zero_conv_live.csv
#   Spend > 0 AND revenue == 0 (or near-zero, < $1)
# ===================================================================
zero_conv = [
    r for r in enriched
    if r["total_historical_spend"] > 0 and r["total_historical_revenue"] < 1.0
]
zero_conv.sort(key=lambda r: r["total_historical_spend"], reverse=True)

zero_cols = [
    "new_product_id", "current_title", "product_type", "custom_label_0",
    "price", "total_historical_spend", "total_historical_revenue",
    "aggregated_roas", "old_product_ids_mapped",
]
with open(os.path.join(OUT_DIR, "FINAL_zero_conv_live.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=zero_cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(zero_conv)

print(f"[4] FINAL_zero_conv_live.csv — {len(zero_conv)} products")

# ===================================================================
# FILE 5: FINAL_product_exclusion_ids.txt
#   IDs from File 4, one per line
# ===================================================================
with open(os.path.join(OUT_DIR, "FINAL_product_exclusion_ids.txt"), "w", encoding="utf-8") as f:
    for r in zero_conv:
        f.write(r["new_product_id"] + "\n")

print(f"[5] FINAL_product_exclusion_ids.txt — {len(zero_conv)} IDs")

# ===================================================================
# FILE 6: FINAL_budget_reallocation.txt
#   Human-readable strategy report
# ===================================================================
lines = []
lines.append("=" * 78)
lines.append("NATURE'S SEED — GOOGLE ADS BUDGET REALLOCATION STRATEGY")
lines.append("Generated from SKU Migration Map + Live Merchant Feed")
lines.append("=" * 78)
lines.append("")

# --- Section 1: Star Products ---
total_star_rev = sum(r["total_historical_revenue"] for r in stars)
total_star_spend = sum(r["total_historical_spend"] for r in stars)
star_roas_agg = roas(total_star_rev, total_star_spend)

lines.append("-" * 78)
lines.append("SECTION 1: STAR PRODUCTS  (ROAS > 4x, Revenue > $3,000)")
lines.append("-" * 78)
lines.append(f"  Count:           {len(stars)} live products")
lines.append(f"  Total Revenue:   ${total_star_rev:,.2f}")
lines.append(f"  Total Spend:     ${total_star_spend:,.2f}")
lines.append(f"  Blended ROAS:    {star_roas_agg:.2f}x")
lines.append("")
lines.append("  RECOMMENDATION:")
lines.append("  These are your proven winners. Allocate 50-60% of Shopping budget here.")
lines.append("  Create a dedicated high-priority campaign with aggressive bids for these")
lines.append("  products. Use Target ROAS bidding with a floor of 4x. Consider raising")
lines.append("  bids by 20-30% during peak season (March-June, September-October).")
lines.append("")
lines.append("  Top 10 Star Products by Revenue:")
for i, r in enumerate(stars[:10], 1):
    lines.append(f"    {i:>2}. {r['current_title'][:70]}")
    lines.append(f"        Revenue: ${r['total_historical_revenue']:,.2f}  |  ROAS: {r['aggregated_roas']:.1f}x  |  Spend: ${r['total_historical_spend']:,.2f}")
lines.append("")

# --- Section 2: Hidden Gems ---
total_gem_rev = sum(r["total_historical_revenue"] for r in gems)
total_gem_spend = sum(r["total_historical_spend"] for r in gems)
gem_roas_agg = roas(total_gem_rev, total_gem_spend)

lines.append("-" * 78)
lines.append("SECTION 2: HIDDEN GEMS  (ROAS > 5x, Spend < $1,000)")
lines.append("-" * 78)
lines.append(f"  Count:           {len(gems)} live products")
lines.append(f"  Total Revenue:   ${total_gem_rev:,.2f}")
lines.append(f"  Total Spend:     ${total_gem_spend:,.2f}")
lines.append(f"  Blended ROAS:    {gem_roas_agg:.2f}x")
lines.append("")
lines.append("  RECOMMENDATION:")
lines.append("  These products convert extremely well but have been under-invested.")
lines.append("  Gradually increase spend by 50-100% while monitoring ROAS. Create a")
lines.append("  'Scale Test' campaign with manual CPC bids to control spend ramp.")
lines.append("  If ROAS holds above 5x after doubling spend, move to Star tier.")
lines.append("")
lines.append("  Top 10 Hidden Gems by ROAS:")
for i, r in enumerate(gems[:10], 1):
    lines.append(f"    {i:>2}. {r['current_title'][:70]}")
    lines.append(f"        ROAS: {r['aggregated_roas']:.1f}x  |  Revenue: ${r['total_historical_revenue']:,.2f}  |  Spend: ${r['total_historical_spend']:,.2f}")
lines.append("")

# --- Section 3: Forage / Animal Products ---
# Breakdown by animal type
animal_buckets = defaultdict(lambda: {"count": 0, "spend": 0.0, "revenue": 0.0, "products": []})
for r in forage:
    pt = r["product_type"].lower()
    if "horse" in pt:
        bucket = "Horse Forage"
    elif "sheep" in pt or "goat" in pt:
        bucket = "Sheep & Goat Forage"
    elif "cow" in pt or "cattle" in pt or "beef" in pt:
        bucket = "Cattle Forage"
    elif "pig" in pt:
        bucket = "Pig Forage"
    elif "tortoise" in pt:
        bucket = "Tortoise Forage"
    elif "poultry" in pt or "chicken" in pt:
        bucket = "Poultry Forage"
    elif "alpaca" in pt or "llama" in pt:
        bucket = "Alpaca & Llama Forage"
    elif "food plot" in pt:
        bucket = "Food Plot / Wildlife"
    else:
        bucket = "Other Forage"
    animal_buckets[bucket]["count"] += 1
    animal_buckets[bucket]["spend"] += r["total_historical_spend"]
    animal_buckets[bucket]["revenue"] += r["total_historical_revenue"]

total_forage_rev = sum(r["total_historical_revenue"] for r in forage)
total_forage_spend = sum(r["total_historical_spend"] for r in forage)

lines.append("-" * 78)
lines.append("SECTION 3: FORAGE & ANIMAL PRODUCTS")
lines.append("-" * 78)
lines.append(f"  Total Products:  {len(forage)} live forage/animal products in feed")
lines.append(f"  Total Revenue:   ${total_forage_rev:,.2f}")
lines.append(f"  Total Spend:     ${total_forage_spend:,.2f}")
lines.append(f"  Blended ROAS:    {roas(total_forage_rev, total_forage_spend):.2f}x")
lines.append("")
lines.append("  Breakdown by Animal Type:")
for bucket_name in sorted(animal_buckets.keys()):
    b = animal_buckets[bucket_name]
    b_roas = roas(b["revenue"], b["spend"])
    lines.append(f"    {bucket_name:<25} {b['count']:>3} products  |  Revenue: ${b['revenue']:>10,.2f}  |  Spend: ${b['spend']:>9,.2f}  |  ROAS: {b_roas:>6.2f}x")
lines.append("")
lines.append("  RECOMMENDATION:")
lines.append("  Forage products are a high-value niche. Create a dedicated 'Animal Forage'")
lines.append("  campaign grouping products by animal type for custom ad copy.")
lines.append("  Horse forage historically has the strongest revenue. Tortoise forage")
lines.append("  often has very high ROAS with low competition. Food Plot products should")
lines.append("  be separated into a seasonal campaign (fall hunting season).")
lines.append("")

# --- Section 4: Zero-Conversion Exclusions ---
total_waste = sum(r["total_historical_spend"] for r in zero_conv)

lines.append("-" * 78)
lines.append("SECTION 4: ZERO-CONVERSION EXCLUSIONS")
lines.append("-" * 78)
lines.append(f"  Count:           {len(zero_conv)} live products with spend but no conversions")
lines.append(f"  Total Wasted:    ${total_waste:,.2f}")
lines.append("")
lines.append("  RECOMMENDATION:")
lines.append("  Immediately add these product IDs to campaign-level exclusion lists.")
lines.append("  Use the FINAL_product_exclusion_ids.txt file to bulk-upload exclusions.")
lines.append("  This reclaims ${:,.2f} in wasted spend that can be redirected to Star".format(total_waste))
lines.append("  and Hidden Gem products. Review quarterly — if products are reformulated")
lines.append("  or re-priced, they can be re-tested with a small budget.")
lines.append("")
if zero_conv:
    lines.append("  Top wasters:")
    for i, r in enumerate(zero_conv[:10], 1):
        lines.append(f"    {i:>2}. {r['current_title'][:65]}  — ${r['total_historical_spend']:,.2f} wasted")
    lines.append("")

# --- Section 5: Performance by Custom Label 0 (Category) ---
cat_buckets = defaultdict(lambda: {"count": 0, "spend": 0.0, "revenue": 0.0})
for r in enriched:
    cl0 = r["custom_label_0"].strip().lower() if r["custom_label_0"] else "(none)"
    cat_buckets[cl0]["count"] += 1
    cat_buckets[cl0]["spend"] += r["total_historical_spend"]
    cat_buckets[cl0]["revenue"] += r["total_historical_revenue"]

lines.append("-" * 78)
lines.append("SECTION 5: PERFORMANCE BY CUSTOM LABEL 0 (Product Category)")
lines.append("-" * 78)
lines.append(f"  {'Category':<20} {'Products':>8} {'Revenue':>14} {'Spend':>12} {'ROAS':>8}")
lines.append(f"  {'-'*20} {'-'*8} {'-'*14} {'-'*12} {'-'*8}")
for cat in sorted(cat_buckets.keys(), key=lambda c: cat_buckets[c]["revenue"], reverse=True):
    b = cat_buckets[cat]
    r_val = roas(b["revenue"], b["spend"])
    roas_str = f"{r_val:.2f}x" if b["spend"] > 0 else "N/A"
    lines.append(f"  {cat:<20} {b['count']:>8} ${b['revenue']:>12,.2f} ${b['spend']:>10,.2f} {roas_str:>8}")
lines.append("")
lines.append("  RECOMMENDATION:")
lines.append("  Structure Shopping campaigns by Custom Label 0 for bid segmentation.")
lines.append("  Categories with ROAS > 5x deserve aggressive bidding. Categories with")
lines.append("  low ROAS (< 2x) need creative refresh, landing page optimization, or")
lines.append("  reduced bids. The 'clover' category is a known strong performer — ensure")
lines.append("  it has dedicated budget allocation.")
lines.append("")

# --- Section 6: Performance by Margin Tier (Custom Label 3) ---
margin_buckets = defaultdict(lambda: {"count": 0, "spend": 0.0, "revenue": 0.0})
for r in enriched:
    cl3 = r["custom_label_3"].strip() if r["custom_label_3"] else "(none)"
    margin_buckets[cl3]["count"] += 1
    margin_buckets[cl3]["spend"] += r["total_historical_spend"]
    margin_buckets[cl3]["revenue"] += r["total_historical_revenue"]

lines.append("-" * 78)
lines.append("SECTION 6: PERFORMANCE BY MARGIN TIER (Custom Label 3)")
lines.append("-" * 78)
lines.append(f"  {'Margin Tier':<20} {'Products':>8} {'Revenue':>14} {'Spend':>12} {'ROAS':>8}")
lines.append(f"  {'-'*20} {'-'*8} {'-'*14} {'-'*12} {'-'*8}")
for tier in ["High Margin", "Average Margin", "Low Margin", "(none)"]:
    if tier in margin_buckets:
        b = margin_buckets[tier]
        r_val = roas(b["revenue"], b["spend"])
        roas_str = f"{r_val:.2f}x" if b["spend"] > 0 else "N/A"
        lines.append(f"  {tier:<20} {b['count']:>8} ${b['revenue']:>12,.2f} ${b['spend']:>10,.2f} {roas_str:>8}")
# Catch any other tiers
for tier in sorted(margin_buckets.keys()):
    if tier not in ["High Margin", "Average Margin", "Low Margin", "(none)"]:
        b = margin_buckets[tier]
        r_val = roas(b["revenue"], b["spend"])
        roas_str = f"{r_val:.2f}x" if b["spend"] > 0 else "N/A"
        lines.append(f"  {tier:<20} {b['count']:>8} ${b['revenue']:>12,.2f} ${b['spend']:>10,.2f} {roas_str:>8}")
lines.append("")
lines.append("  RECOMMENDATION:")
lines.append("  High Margin products should be bid most aggressively — every dollar of")
lines.append("  revenue here returns the most profit. Use Target ROAS bidding with lower")
lines.append("  ROAS floors for High Margin (3x may be profitable) vs Low Margin (need 6x+).")
lines.append("  Consider creating separate campaigns by margin tier to control bids:")
lines.append("    - High Margin campaign: Target ROAS 3-4x, aggressive budget")
lines.append("    - Average Margin campaign: Target ROAS 4-5x, moderate budget")
lines.append("    - Low Margin campaign: Target ROAS 6x+, conservative budget")
lines.append("")

# --- Summary ---
all_spend = sum(r["total_historical_spend"] for r in enriched)
all_rev = sum(r["total_historical_revenue"] for r in enriched)
lines.append("=" * 78)
lines.append("OVERALL SUMMARY")
lines.append("=" * 78)
lines.append(f"  Total live products in feed:        {len(feed)}")
lines.append(f"  Products with historical data:      {sum(1 for r in enriched if r['total_historical_spend'] > 0)}")
lines.append(f"  Products with NO historical data:   {sum(1 for r in enriched if r['total_historical_spend'] == 0)}")
lines.append(f"  Total historical spend (mapped):    ${all_spend:,.2f}")
lines.append(f"  Total historical revenue (mapped):  ${all_rev:,.2f}")
lines.append(f"  Overall mapped ROAS:                {roas(all_rev, all_spend):.2f}x")
lines.append("")
lines.append("  ACTION ITEMS:")
lines.append(f"  1. Exclude {len(zero_conv)} zero-conversion products (save ${total_waste:,.2f})")
lines.append(f"  2. Boost {len(stars)} star products (${total_star_rev:,.2f} proven revenue)")
lines.append(f"  3. Scale-test {len(gems)} hidden gems ({gem_roas_agg:.1f}x avg ROAS)")
lines.append(f"  4. Create dedicated forage campaign ({len(forage)} products)")
lines.append(f"  5. Segment campaigns by margin tier for profit-optimized bidding")
lines.append(f"  6. {sum(1 for r in enriched if r['total_historical_spend'] == 0)} live products have NO historical data — start small test budgets")
lines.append("")

report = "\n".join(lines)
with open(os.path.join(OUT_DIR, "FINAL_budget_reallocation.txt"), "w", encoding="utf-8") as f:
    f.write(report)

print(f"[6] FINAL_budget_reallocation.txt — written ({len(lines)} lines)")
print("\nDone. All 6 files written to:", OUT_DIR)
