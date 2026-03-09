#!/usr/bin/env python3
"""
Extract zero-conversion and sub-1x ROAS products from Google Ads Shopping Products data.
Aggregates across all time periods/campaigns by Product Item ID.
"""

import pandas as pd
import os

# Paths
DATA_DIR = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/data"
OUTPUT_DIR = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/implementation"

# Read CSV
df = pd.read_csv(os.path.join(DATA_DIR, "Shopping_Products.csv"))

print(f"Total rows: {len(df)}")
print(f"Columns: {list(df.columns)}")
print(f"Unique Product Item IDs: {df['Product Item ID'].nunique()}")

# Clean numeric columns - strip % from CTR, ensure numeric types
numeric_cols = ['Impressions', 'Clicks', 'Cost ($)', 'Avg CPC ($)', 'Conversions', 'Conv. Value ($)', 'ROAS']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# For Product Title, Product Type L1, Product Type L2 - take the most recent (last) non-null value per product
# First, sort by Year and Quarter to ensure chronological order
df = df.sort_values(['Year', 'Quarter'])

# Aggregate by Product Item ID
# For titles and types, take the last (most recent) non-empty value
def last_non_empty(series):
    """Return the last non-null, non-empty value from a series."""
    valid = series.dropna()
    valid = valid[valid.astype(str).str.strip() != '']
    if len(valid) > 0:
        return valid.iloc[-1]
    return ''

agg = df.groupby('Product Item ID').agg(
    product_title=('Product Title', last_non_empty),
    product_type_l1=('Product Type (L1)', last_non_empty),
    product_type_l2=('Product Type (L2)', last_non_empty),
    total_spend=('Cost ($)', 'sum'),
    total_clicks=('Clicks', 'sum'),
    total_conversions=('Conversions', 'sum'),
    total_conv_value=('Conv. Value ($)', 'sum'),
).reset_index()

# Calculate ROAS at the aggregated level
agg['roas'] = agg.apply(
    lambda row: round(row['total_conv_value'] / row['total_spend'], 2) if row['total_spend'] > 0 else 0,
    axis=1
)

# Round numeric columns
agg['total_spend'] = agg['total_spend'].round(2)
agg['total_clicks'] = agg['total_clicks'].astype(int)
agg['total_conversions'] = agg['total_conversions'].round(2)
agg['total_conv_value'] = agg['total_conv_value'].round(2)

print(f"\nAggregated products: {len(agg)}")
print(f"Products with spend > 0: {len(agg[agg['total_spend'] > 0])}")
print(f"Products with conversions == 0 AND spend > 0: {len(agg[(agg['total_spend'] > 0) & (agg['total_conversions'] == 0)])}")
print(f"Products with conversions > 0 AND ROAS < 1: {len(agg[(agg['total_conversions'] > 0) & (agg['roas'] < 1) & (agg['total_spend'] > 0)])}")

# --- Zero Conversion Products ---
# Products that received spend (Cost > 0) but had 0 conversions across ALL time periods
zero_conv = agg[(agg['total_spend'] > 0) & (agg['total_conversions'] == 0)].copy()
zero_conv = zero_conv.sort_values('total_spend', ascending=False)

# Rename columns for output
output_cols = {
    'Product Item ID': 'Product Item ID',
    'product_title': 'Product Title',
    'product_type_l1': 'Product Type L1',
    'product_type_l2': 'Product Type L2',
    'total_spend': 'Total Spend ($)',
    'total_clicks': 'Total Clicks',
    'total_conversions': 'Total Conversions',
    'total_conv_value': 'Total Conv Value ($)',
    'roas': 'ROAS'
}
zero_conv = zero_conv.rename(columns=output_cols)

zero_conv_path = os.path.join(OUTPUT_DIR, "zero_conversion_products.csv")
zero_conv.to_csv(zero_conv_path, index=False)
print(f"\nZero-conversion products: {len(zero_conv)}")
print(f"Total wasted spend: ${zero_conv['Total Spend ($)'].sum():,.2f}")
print(f"Saved to: {zero_conv_path}")

# Top 10 zero-conversion by spend
print("\nTop 10 zero-conversion products by spend:")
for i, row in zero_conv.head(10).iterrows():
    print(f"  {row['Product Item ID']:30s} | ${row['Total Spend ($)']:>10,.2f} | {row['Total Clicks']:>6d} clicks | {row['Product Title'][:60]}")

# --- Sub-1x ROAS Products ---
# Products that had conversions > 0 but overall ROAS < 1.0
sub_1x = agg[(agg['total_conversions'] > 0) & (agg['roas'] < 1) & (agg['total_spend'] > 0)].copy()
sub_1x = sub_1x.sort_values('total_spend', ascending=False)
sub_1x = sub_1x.rename(columns=output_cols)

sub_1x_path = os.path.join(OUTPUT_DIR, "sub_1x_roas_products.csv")
sub_1x.to_csv(sub_1x_path, index=False)
print(f"\nSub-1x ROAS products: {len(sub_1x)}")
print(f"Total spend on sub-1x ROAS: ${sub_1x['Total Spend ($)'].sum():,.2f}")
print(f"Total conv value on sub-1x ROAS: ${sub_1x['Total Conv Value ($)'].sum():,.2f}")
print(f"Net loss: ${sub_1x['Total Spend ($)'].sum() - sub_1x['Total Conv Value ($)'].sum():,.2f}")
print(f"Saved to: {sub_1x_path}")

# Top 10 sub-1x ROAS by spend
print("\nTop 10 sub-1x ROAS products by spend:")
for i, row in sub_1x.head(10).iterrows():
    print(f"  {row['Product Item ID']:30s} | ${row['Total Spend ($)']:>10,.2f} | ROAS: {row['ROAS']:.2f} | {row['Product Title'][:50]}")

# --- Product Exclusion IDs (zero-conversion only) ---
exclusion_path = os.path.join(OUTPUT_DIR, "product_exclusion_ids.txt")
with open(exclusion_path, 'w') as f:
    for pid in zero_conv['Product Item ID']:
        f.write(f"{pid}\n")
print(f"\nProduct exclusion IDs: {len(zero_conv)} IDs")
print(f"Saved to: {exclusion_path}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total unique products in data: {len(agg)}")
print(f"Products with any spend: {len(agg[agg['total_spend'] > 0])}")
print(f"Zero-conversion products (spend > 0, conv = 0): {len(zero_conv)}")
print(f"  -> Wasted spend: ${zero_conv['Total Spend ($)'].sum():,.2f}")
print(f"Sub-1x ROAS products (conv > 0, ROAS < 1.0): {len(sub_1x)}")
print(f"  -> Net loss: ${sub_1x['Total Spend ($)'].sum() - sub_1x['Total Conv Value ($)'].sum():,.2f}")
print(f"Combined problematic spend: ${zero_conv['Total Spend ($)'].sum() + sub_1x['Total Spend ($)'].sum():,.2f}")
