#!/usr/bin/env python3
"""
Analyze Shopping Products CSV to find:
1. High-ROAS underinvested products (hidden gems)
2. Star products (proven winners at scale)
3. Forage/animal-specific product performance
Output CSVs and a budget reallocation summary.
"""

import pandas as pd
import re
import os

# --- Configuration ---
INPUT_CSV = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/data/Shopping_Products.csv"
OUTPUT_DIR = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/implementation"

# --- Load Data ---
df = pd.read_csv(INPUT_CSV)

print(f"Loaded {len(df):,} rows")
print(f"Columns: {list(df.columns)}")
print(f"Unique Product Item IDs: {df['Product Item ID'].nunique()}")
print(f"Date range: {df['Year'].min()} Q{df['Quarter'].min()} to {df['Year'].max()} Q{df['Quarter'].max()}")

# Clean numeric columns - strip $ and % and convert
for col in ['Cost ($)', 'Avg CPC ($)', 'Conv. Value ($)', 'ROAS']:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace('$', '').str.replace(',', '').str.replace('%', ''), errors='coerce').fillna(0)

for col in ['Impressions', 'Clicks', 'Conversions']:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

df['CTR'] = pd.to_numeric(df['CTR'].astype(str).str.replace('%', ''), errors='coerce').fillna(0)

# --- Aggregate by Product Item ID + Product Title ---
# Since a product can have slightly different titles across quarters/campaigns,
# we group by Product Item ID and take the most common title
def most_common_title(titles):
    return titles.value_counts().index[0]

agg = df.groupby('Product Item ID').agg(
    product_title=('Product Title', most_common_title),
    product_type_l1=('Product Type (L1)', 'first'),
    product_type_l2=('Product Type (L2)', 'first'),
    total_impressions=('Impressions', 'sum'),
    total_clicks=('Clicks', 'sum'),
    total_cost=('Cost ($)', 'sum'),
    total_conversions=('Conversions', 'sum'),
    total_revenue=('Conv. Value ($)', 'sum'),
    num_quarters=('Quarter', 'nunique'),
    num_campaigns=('Campaign Name', 'nunique'),
).reset_index()

# Calculate aggregate metrics
agg['total_roas'] = (agg['total_revenue'] / agg['total_cost']).replace([float('inf')], 0).fillna(0)
agg['ctr'] = ((agg['total_clicks'] / agg['total_impressions']) * 100).replace([float('inf')], 0).fillna(0)
agg['avg_cpc'] = (agg['total_cost'] / agg['total_clicks']).replace([float('inf')], 0).fillna(0)
agg['conv_rate'] = ((agg['total_conversions'] / agg['total_clicks']) * 100).replace([float('inf')], 0).fillna(0)
agg['avg_order_value'] = (agg['total_revenue'] / agg['total_conversions']).replace([float('inf')], 0).fillna(0)

print(f"\nAggregated to {len(agg):,} unique products")
print(f"Total spend: ${agg['total_cost'].sum():,.2f}")
print(f"Total revenue: ${agg['total_revenue'].sum():,.2f}")
print(f"Overall ROAS: {agg['total_revenue'].sum() / agg['total_cost'].sum():.2f}x")

# --- 1. High-ROAS Underinvested Products (Hidden Gems) ---
hidden_gems = agg[
    (agg['total_roas'] > 5) &
    (agg['total_cost'] < 500) &
    (agg['total_conversions'] >= 1)
].sort_values('total_roas', ascending=False).copy()

hidden_gems_out = hidden_gems[[
    'Product Item ID', 'product_title', 'product_type_l1', 'product_type_l2',
    'total_impressions', 'total_clicks', 'total_cost', 'total_conversions',
    'total_revenue', 'total_roas', 'ctr', 'avg_cpc', 'conv_rate',
    'avg_order_value', 'num_quarters', 'num_campaigns'
]].copy()

hidden_gems_out.columns = [
    'Product Item ID', 'Product Title', 'Product Type L1', 'Product Type L2',
    'Total Impressions', 'Total Clicks', 'Total Cost ($)', 'Total Conversions',
    'Total Revenue ($)', 'Total ROAS', 'CTR (%)', 'Avg CPC ($)', 'Conv Rate (%)',
    'Avg Order Value ($)', 'Quarters Active', 'Campaigns'
]

hidden_gems_out.to_csv(os.path.join(OUTPUT_DIR, 'high_roas_underinvested.csv'), index=False, float_format='%.2f')
print(f"\n--- HIGH-ROAS UNDERINVESTED (Hidden Gems) ---")
print(f"Found {len(hidden_gems_out)} products with ROAS > 5x, spend < $500, conversions >= 1")
print(f"Combined spend: ${hidden_gems['total_cost'].sum():,.2f}")
print(f"Combined revenue: ${hidden_gems['total_revenue'].sum():,.2f}")
print(f"Combined ROAS: {hidden_gems['total_revenue'].sum() / hidden_gems['total_cost'].sum():.2f}x")
print("\nTop 15:")
for _, row in hidden_gems_out.head(15).iterrows():
    print(f"  {row['Product Item ID']:20s} | ROAS: {row['Total ROAS']:8.2f}x | Spend: ${row['Total Cost ($)']:8.2f} | Rev: ${row['Total Revenue ($)']:10.2f} | Conv: {row['Total Conversions']:6.1f} | {row['Product Title'][:60]}")


# --- 2. Star Products (Proven Winners at Scale) ---
stars = agg[
    (agg['total_roas'] > 4) &
    (agg['total_revenue'] > 5000)
].sort_values('total_revenue', ascending=False).copy()

stars_out = stars[[
    'Product Item ID', 'product_title', 'product_type_l1', 'product_type_l2',
    'total_impressions', 'total_clicks', 'total_cost', 'total_conversions',
    'total_revenue', 'total_roas', 'ctr', 'avg_cpc', 'conv_rate',
    'avg_order_value', 'num_quarters', 'num_campaigns'
]].copy()

stars_out.columns = [
    'Product Item ID', 'Product Title', 'Product Type L1', 'Product Type L2',
    'Total Impressions', 'Total Clicks', 'Total Cost ($)', 'Total Conversions',
    'Total Revenue ($)', 'Total ROAS', 'CTR (%)', 'Avg CPC ($)', 'Conv Rate (%)',
    'Avg Order Value ($)', 'Quarters Active', 'Campaigns'
]

stars_out.to_csv(os.path.join(OUTPUT_DIR, 'star_products.csv'), index=False, float_format='%.2f')
print(f"\n--- STAR PRODUCTS (Proven Winners) ---")
print(f"Found {len(stars_out)} products with ROAS > 4x and revenue > $5,000")
print(f"Combined spend: ${stars['total_cost'].sum():,.2f}")
print(f"Combined revenue: ${stars['total_revenue'].sum():,.2f}")
print(f"Combined ROAS: {stars['total_revenue'].sum() / stars['total_cost'].sum():.2f}x")
print("\nAll star products:")
for _, row in stars_out.iterrows():
    print(f"  {row['Product Item ID']:20s} | ROAS: {row['Total ROAS']:6.2f}x | Spend: ${row['Total Cost ($)']:10.2f} | Rev: ${row['Total Revenue ($)']:12.2f} | Conv: {row['Total Conversions']:8.1f} | {row['Product Title'][:60]}")


# --- 3. Forage / Animal-Specific Products ---
forage_keywords = ['sheep', 'goat', 'horse', 'cattle', 'poultry', 'forage', 'livestock']
pattern = '|'.join(forage_keywords)

forage = agg[agg['product_title'].str.contains(pattern, case=False, na=False)].sort_values('total_roas', ascending=False).copy()

forage_out = forage[[
    'Product Item ID', 'product_title', 'product_type_l1', 'product_type_l2',
    'total_impressions', 'total_clicks', 'total_cost', 'total_conversions',
    'total_revenue', 'total_roas', 'ctr', 'avg_cpc', 'conv_rate',
    'avg_order_value', 'num_quarters', 'num_campaigns'
]].copy()

forage_out.columns = [
    'Product Item ID', 'Product Title', 'Product Type L1', 'Product Type L2',
    'Total Impressions', 'Total Clicks', 'Total Cost ($)', 'Total Conversions',
    'Total Revenue ($)', 'Total ROAS', 'CTR (%)', 'Avg CPC ($)', 'Conv Rate (%)',
    'Avg Order Value ($)', 'Quarters Active', 'Campaigns'
]

forage_out.to_csv(os.path.join(OUTPUT_DIR, 'forage_animal_products.csv'), index=False, float_format='%.2f')
print(f"\n--- FORAGE / ANIMAL-SPECIFIC PRODUCTS ---")
print(f"Found {len(forage_out)} products matching keywords: {forage_keywords}")
print(f"Combined spend: ${forage['total_cost'].sum():,.2f}")
print(f"Combined revenue: ${forage['total_revenue'].sum():,.2f}")
if forage['total_cost'].sum() > 0:
    print(f"Combined ROAS: {forage['total_revenue'].sum() / forage['total_cost'].sum():.2f}x")
print("\nAll forage/animal products:")
for _, row in forage_out.iterrows():
    print(f"  {row['Product Item ID']:20s} | ROAS: {row['Total ROAS']:8.2f}x | Spend: ${row['Total Cost ($)']:8.2f} | Rev: ${row['Total Revenue ($)']:10.2f} | Conv: {row['Total Conversions']:6.1f} | {row['Product Title'][:70]}")

# --- Keyword breakdown for forage ---
print("\nKeyword breakdown:")
for kw in forage_keywords:
    subset = forage[forage['product_title'].str.contains(kw, case=False, na=False)]
    if len(subset) > 0:
        print(f"  '{kw}': {len(subset)} products | Spend: ${subset['total_cost'].sum():,.2f} | Rev: ${subset['total_revenue'].sum():,.2f} | ROAS: {subset['total_revenue'].sum() / max(subset['total_cost'].sum(), 0.01):.2f}x")


# --- 4. Budget Reallocation Summary ---
total_spend = agg['total_cost'].sum()
total_rev = agg['total_revenue'].sum()

# Identify wasted spend: products with spend > $100 but ROAS < 1
wasted = agg[(agg['total_cost'] > 100) & (agg['total_roas'] < 1)]
low_roas = agg[(agg['total_cost'] > 100) & (agg['total_roas'] >= 1) & (agg['total_roas'] < 2)]

summary_lines = []
summary_lines.append("=" * 80)
summary_lines.append("NATURE'S SEED - GOOGLE ADS SHOPPING BUDGET REALLOCATION SUMMARY")
summary_lines.append("=" * 80)
summary_lines.append(f"Data: All quarters and campaigns aggregated")
summary_lines.append(f"Total unique products analyzed: {len(agg):,}")
summary_lines.append(f"Total spend: ${total_spend:,.2f}")
summary_lines.append(f"Total revenue: ${total_rev:,.2f}")
summary_lines.append(f"Overall ROAS: {total_rev / total_spend:.2f}x")
summary_lines.append("")

summary_lines.append("-" * 80)
summary_lines.append("SECTION 1: HIDDEN GEMS (High ROAS, Underinvested)")
summary_lines.append(f"Criteria: ROAS > 5x, Spend < $500, Conversions >= 1")
summary_lines.append("-" * 80)
summary_lines.append(f"Products found: {len(hidden_gems)}")
summary_lines.append(f"Current combined spend: ${hidden_gems['total_cost'].sum():,.2f}")
summary_lines.append(f"Current combined revenue: ${hidden_gems['total_revenue'].sum():,.2f}")
summary_lines.append(f"Combined ROAS: {hidden_gems['total_revenue'].sum() / max(hidden_gems['total_cost'].sum(), 0.01):.2f}x")
summary_lines.append("")
summary_lines.append("RECOMMENDATION: Increase budgets on these products. They have proven")
summary_lines.append("conversion ability with excellent ROAS but have been starved of spend.")
summary_lines.append("Suggested action: Increase bids/budgets by 50-100% and monitor weekly.")
summary_lines.append("")
summary_lines.append("Top 10 hidden gems to prioritize:")
for i, (_, row) in enumerate(hidden_gems.head(10).iterrows(), 1):
    summary_lines.append(f"  {i:2d}. {row['Product Item ID']:20s} | ROAS: {row['total_roas']:7.2f}x | Spend: ${row['total_cost']:7.2f} | Rev: ${row['total_revenue']:9.2f}")
    summary_lines.append(f"      Title: {row['product_title'][:75]}")
summary_lines.append("")

summary_lines.append("-" * 80)
summary_lines.append("SECTION 2: STAR PRODUCTS (Proven Winners at Scale)")
summary_lines.append(f"Criteria: ROAS > 4x, Revenue > $5,000")
summary_lines.append("-" * 80)
summary_lines.append(f"Products found: {len(stars)}")
summary_lines.append(f"Current combined spend: ${stars['total_cost'].sum():,.2f}")
summary_lines.append(f"Current combined revenue: ${stars['total_revenue'].sum():,.2f}")
summary_lines.append(f"Combined ROAS: {stars['total_revenue'].sum() / max(stars['total_cost'].sum(), 0.01):.2f}x")
summary_lines.append(f"Share of total spend: {stars['total_cost'].sum() / total_spend * 100:.1f}%")
summary_lines.append(f"Share of total revenue: {stars['total_revenue'].sum() / total_rev * 100:.1f}%")
summary_lines.append("")
summary_lines.append("RECOMMENDATION: These are your workhorses. Maintain or moderately increase")
summary_lines.append("budgets. Ensure they never hit daily budget caps. Consider creating")
summary_lines.append("dedicated campaigns for top stars for granular bid control.")
summary_lines.append("")
summary_lines.append("All star products:")
for i, (_, row) in enumerate(stars.iterrows(), 1):
    summary_lines.append(f"  {i:2d}. {row['Product Item ID']:20s} | ROAS: {row['total_roas']:6.2f}x | Spend: ${row['total_cost']:10.2f} | Rev: ${row['total_revenue']:12.2f}")
    summary_lines.append(f"      Title: {row['product_title'][:75]}")
summary_lines.append("")

summary_lines.append("-" * 80)
summary_lines.append("SECTION 3: FORAGE / ANIMAL-SPECIFIC PRODUCTS")
summary_lines.append(f"Keywords: {', '.join(forage_keywords)}")
summary_lines.append("-" * 80)
summary_lines.append(f"Products found: {len(forage)}")
summary_lines.append(f"Current combined spend: ${forage['total_cost'].sum():,.2f}")
summary_lines.append(f"Current combined revenue: ${forage['total_revenue'].sum():,.2f}")
if forage['total_cost'].sum() > 0:
    summary_lines.append(f"Combined ROAS: {forage['total_revenue'].sum() / forage['total_cost'].sum():.2f}x")
summary_lines.append("")

# Split forage into performers and underperformers
forage_good = forage[forage['total_roas'] > 3]
forage_bad = forage[(forage['total_roas'] < 2) & (forage['total_cost'] > 20)]
summary_lines.append(f"Strong performers (ROAS > 3x): {len(forage_good)} products")
for _, row in forage_good.iterrows():
    summary_lines.append(f"  + {row['Product Item ID']:20s} | ROAS: {row['total_roas']:7.2f}x | Spend: ${row['total_cost']:7.2f} | Rev: ${row['total_revenue']:9.2f}")
summary_lines.append("")
if len(forage_bad) > 0:
    summary_lines.append(f"Underperformers (ROAS < 2x, Spend > $20): {len(forage_bad)} products")
    for _, row in forage_bad.iterrows():
        summary_lines.append(f"  - {row['Product Item ID']:20s} | ROAS: {row['total_roas']:7.2f}x | Spend: ${row['total_cost']:7.2f} | Rev: ${row['total_revenue']:9.2f}")
    summary_lines.append("")

summary_lines.append("RECOMMENDATION: The forage/livestock niche is underserved in paid search.")
summary_lines.append("Products with proven ROAS should get dedicated campaign segments.")
summary_lines.append("Consider a dedicated 'Forage & Livestock' PMax campaign to better")
summary_lines.append("target agricultural buyers with tailored messaging.")
summary_lines.append("")

summary_lines.append("-" * 80)
summary_lines.append("SECTION 4: BUDGET REALLOCATION OPPORTUNITIES")
summary_lines.append("-" * 80)
summary_lines.append("")

summary_lines.append(f"WASTE: {len(wasted)} products with spend > $100 and ROAS < 1x")
summary_lines.append(f"  Total wasted spend: ${wasted['total_cost'].sum():,.2f}")
summary_lines.append(f"  Total revenue from wasted: ${wasted['total_revenue'].sum():,.2f}")
summary_lines.append(f"  Net loss: ${wasted['total_cost'].sum() - wasted['total_revenue'].sum():,.2f}")
summary_lines.append("")

if len(wasted) > 0:
    summary_lines.append("  Top wasters (by spend with ROAS < 1x):")
    for _, row in wasted.sort_values('total_cost', ascending=False).head(10).iterrows():
        summary_lines.append(f"    {row['Product Item ID']:20s} | ROAS: {row['total_roas']:.2f}x | Spend: ${row['total_cost']:8.2f} | Rev: ${row['total_revenue']:8.2f} | {row['product_title'][:50]}")
    summary_lines.append("")

summary_lines.append(f"LOW ROAS: {len(low_roas)} products with spend > $100 and ROAS between 1-2x")
summary_lines.append(f"  Total spend: ${low_roas['total_cost'].sum():,.2f}")
summary_lines.append(f"  Total revenue: ${low_roas['total_revenue'].sum():,.2f}")
summary_lines.append("")

# Calculate potential impact
potential_reallocate = wasted['total_cost'].sum() * 0.5 + low_roas['total_cost'].sum() * 0.25
hidden_gem_roas = hidden_gems['total_revenue'].sum() / max(hidden_gems['total_cost'].sum(), 0.01)
potential_additional_rev = potential_reallocate * hidden_gem_roas

summary_lines.append("PROPOSED REALLOCATION:")
summary_lines.append(f"  1. Cut 50% of spend on ROAS < 1x products:     ${wasted['total_cost'].sum() * 0.5:>10,.2f} freed")
summary_lines.append(f"  2. Cut 25% of spend on ROAS 1-2x products:     ${low_roas['total_cost'].sum() * 0.25:>10,.2f} freed")
summary_lines.append(f"  TOTAL available to reallocate:                  ${potential_reallocate:>10,.2f}")
summary_lines.append("")
summary_lines.append(f"  If reallocated to hidden gems (current ROAS {hidden_gem_roas:.1f}x):")
summary_lines.append(f"  Potential additional revenue:                   ${potential_additional_rev:>10,.2f}")
summary_lines.append("")
summary_lines.append("  Suggested split of reallocated budget:")
summary_lines.append(f"    60% to hidden gems (scale proven winners):    ${potential_reallocate * 0.6:>10,.2f}")
summary_lines.append(f"    25% to star product bid increases:            ${potential_reallocate * 0.25:>10,.2f}")
summary_lines.append(f"    15% to forage/livestock test campaigns:       ${potential_reallocate * 0.15:>10,.2f}")

summary_lines.append("")
summary_lines.append("=" * 80)
summary_lines.append("END OF SUMMARY")
summary_lines.append("=" * 80)

summary_text = "\n".join(summary_lines)
with open(os.path.join(OUTPUT_DIR, 'budget_reallocation_summary.txt'), 'w') as f:
    f.write(summary_text)

print("\n" + summary_text)

print(f"\n\nFiles written to: {OUTPUT_DIR}")
print(f"  - high_roas_underinvested.csv ({len(hidden_gems_out)} products)")
print(f"  - star_products.csv ({len(stars_out)} products)")
print(f"  - forage_animal_products.csv ({len(forage_out)} products)")
print(f"  - budget_reallocation_summary.txt")
