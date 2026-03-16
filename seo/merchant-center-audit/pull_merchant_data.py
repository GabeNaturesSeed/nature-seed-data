#!/usr/bin/env python3
"""
Nature's Seed — Google Merchant Center Account Health Audit
============================================================
Pulls all product data, statuses, and diagnostics from the Content API.
Outputs comprehensive JSON for analysis.

Usage:
    python3 pull_merchant_data.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── Load credentials ──
PROJECT_ROOT = Path(__file__).resolve().parents[1]
env_path = PROJECT_ROOT / ".env"

env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

MC_ID = env_vars["GOOGLE_MERCHANT_CENTER_ID"]
CLIENT_ID = env_vars["GOOGLE_ADS_CLIENT_ID"]
CLIENT_SECRET = env_vars["GOOGLE_ADS_CLIENT_SECRET"]
REFRESH_TOKEN = env_vars["GOOGLE_ADS_REFRESH_TOKEN"]

creds = Credentials(
    token=None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/content"],
)

mc = build("content", "v2.1", credentials=creds)

OUT_DIR = Path(__file__).resolve().parent / "data"
OUT_DIR.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════
# 1. ACCOUNT INFO
# ══════════════════════════════════════════════════════════════

def pull_account_info():
    """Get account-level details."""
    print("Pulling account info...")
    try:
        account = mc.accounts().get(merchantId=MC_ID, accountId=MC_ID).execute()
        print(f"  Account: {account.get('name', 'Unknown')}")
        print(f"  Website: {account.get('websiteUrl', 'N/A')}")
        return account
    except Exception as e:
        print(f"  [ERR] {e}")
        return {}


# ══════════════════════════════════════════════════════════════
# 2. ALL PRODUCTS (full feed data)
# ══════════════════════════════════════════════════════════════

def pull_all_products():
    """Pull all products from the feed."""
    print("Pulling all products...")
    products = []
    page_token = None

    while True:
        resp = mc.products().list(
            merchantId=MC_ID,
            maxResults=250,
            pageToken=page_token,
        ).execute()

        batch = resp.get("resources", [])
        products.extend(batch)
        print(f"  Fetched {len(products)} products...")

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"  Total products: {len(products)}")
    return products


# ══════════════════════════════════════════════════════════════
# 3. PRODUCT STATUSES (approval, issues, destinations)
# ══════════════════════════════════════════════════════════════

def pull_product_statuses():
    """Pull product statuses — approved, disapproved, pending, issues."""
    print("Pulling product statuses...")
    statuses = []
    page_token = None

    while True:
        resp = mc.productstatuses().list(
            merchantId=MC_ID,
            maxResults=250,
            pageToken=page_token,
        ).execute()

        batch = resp.get("resources", [])
        statuses.extend(batch)
        print(f"  Fetched {len(statuses)} statuses...")

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"  Total statuses: {len(statuses)}")
    return statuses


# ══════════════════════════════════════════════════════════════
# 4. ACCOUNT-LEVEL DIAGNOSTICS
# ══════════════════════════════════════════════════════════════

def pull_account_statuses():
    """Pull account-level status and diagnostics."""
    print("Pulling account statuses...")
    try:
        resp = mc.accountstatuses().get(
            merchantId=MC_ID,
            accountId=MC_ID,
        ).execute()
        return resp
    except Exception as e:
        print(f"  [ERR] {e}")
        return {}


# ══════════════════════════════════════════════════════════════
# 5. ANALYZE
# ══════════════════════════════════════════════════════════════

def analyze(products, statuses, account_status):
    """Build comprehensive analysis from raw data."""

    analysis = {
        "pull_date": datetime.now().isoformat(),
        "total_products": len(products),
        "total_statuses": len(statuses),
    }

    # ── Product approval breakdown ──
    approval_counts = defaultdict(int)
    issues_by_type = defaultdict(int)
    issues_by_severity = defaultdict(int)
    products_with_issues = []
    disapproved_products = []

    for status in statuses:
        product_id = status.get("productId", "")
        title = status.get("title", "Unknown")

        # Destination statuses
        dest_statuses = status.get("destinationStatuses", [])
        for dest in dest_statuses:
            dest_name = dest.get("destination", "unknown")
            approval = dest.get("approvedCountry") or dest.get("status", "unknown")
            # Check if approved for US
            approved_countries = dest.get("approvedCountries", [])
            pending_countries = dest.get("pendingCountries", [])
            disapproved_countries = dest.get("disapprovedCountries", [])

            if "US" in approved_countries:
                approval_counts["approved"] += 1
            elif "US" in disapproved_countries:
                approval_counts["disapproved"] += 1
                disapproved_products.append({
                    "id": product_id,
                    "title": title,
                    "destination": dest_name,
                })
            elif "US" in pending_countries:
                approval_counts["pending"] += 1
            else:
                approval_counts["other"] += 1

        # Item-level issues
        item_issues = status.get("itemLevelIssues", [])
        if item_issues:
            product_issue_summary = {
                "id": product_id,
                "title": title,
                "issues": [],
            }
            for issue in item_issues:
                issue_type = issue.get("code", "unknown")
                severity = issue.get("servability", issue.get("severity", "unknown"))
                description = issue.get("description", "")
                detail = issue.get("detail", "")
                resolution = issue.get("resolution", "")
                applicable = issue.get("applicableCountries", [])

                issues_by_type[issue_type] += 1
                issues_by_severity[severity] += 1

                product_issue_summary["issues"].append({
                    "code": issue_type,
                    "severity": severity,
                    "description": description,
                    "detail": detail,
                    "resolution": resolution,
                    "countries": applicable,
                })

            products_with_issues.append(product_issue_summary)

    analysis["approval_breakdown"] = dict(approval_counts)
    analysis["issues_by_type"] = dict(sorted(issues_by_type.items(), key=lambda x: -x[1]))
    analysis["issues_by_severity"] = dict(issues_by_severity)
    analysis["disapproved_count"] = len(disapproved_products)
    analysis["disapproved_products"] = disapproved_products
    analysis["products_with_issues_count"] = len(products_with_issues)

    # ── Product data analysis ──
    product_types = defaultdict(int)
    brands = defaultdict(int)
    price_ranges = {"under_10": 0, "10_25": 0, "25_50": 0, "50_100": 0, "100_200": 0, "over_200": 0}
    missing_fields = defaultdict(int)
    custom_labels = defaultdict(lambda: defaultdict(int))
    has_gtin = 0
    no_gtin = 0
    has_sale_price = 0
    has_cost_of_goods = 0
    has_shipping_weight = 0
    has_product_highlights = 0
    item_group_ids = defaultdict(int)
    google_categories = defaultdict(int)

    for product in products:
        # Product type
        pt = product.get("productTypes", ["(none)"])
        for t in pt:
            product_types[t] += 1

        # Brand
        brand = product.get("brand", "(missing)")
        brands[brand] += 1

        # Price
        price_obj = product.get("price", {})
        price_val = float(price_obj.get("value", 0)) if price_obj.get("value") else 0
        if price_val < 10:
            price_ranges["under_10"] += 1
        elif price_val < 25:
            price_ranges["10_25"] += 1
        elif price_val < 50:
            price_ranges["25_50"] += 1
        elif price_val < 100:
            price_ranges["50_100"] += 1
        elif price_val < 200:
            price_ranges["100_200"] += 1
        else:
            price_ranges["over_200"] += 1

        # Missing fields
        if not product.get("gtin"):
            no_gtin += 1
            missing_fields["gtin"] += 1
        else:
            has_gtin += 1

        if not product.get("description"):
            missing_fields["description"] += 1
        if not product.get("imageLink"):
            missing_fields["imageLink"] += 1
        if not product.get("brand"):
            missing_fields["brand"] += 1
        if not product.get("mpn"):
            missing_fields["mpn"] += 1
        if not product.get("googleProductCategory"):
            missing_fields["googleProductCategory"] += 1
        if not product.get("link"):
            missing_fields["link"] += 1

        if product.get("salePrice"):
            has_sale_price += 1
        if product.get("costOfGoodsSold"):
            has_cost_of_goods += 1
        if product.get("shippingWeight"):
            has_shipping_weight += 1
        if product.get("productHighlights"):
            has_product_highlights += 1

        # Custom labels
        for i in range(5):
            label_key = f"customLabel{i}"
            label_val = product.get(label_key, "")
            if label_val:
                custom_labels[f"custom_label_{i}"][label_val] += 1

        # Item group
        ig = product.get("itemGroupId", "(none)")
        item_group_ids[ig] += 1

        # Google category
        gc = product.get("googleProductCategory", "(none)")
        google_categories[gc] += 1

    analysis["product_types"] = dict(sorted(product_types.items(), key=lambda x: -x[1]))
    analysis["brands"] = dict(brands)
    analysis["price_ranges"] = price_ranges
    analysis["missing_fields"] = dict(sorted(missing_fields.items(), key=lambda x: -x[1]))
    analysis["gtin_coverage"] = {"has_gtin": has_gtin, "no_gtin": no_gtin}
    analysis["optional_fields"] = {
        "has_sale_price": has_sale_price,
        "has_cost_of_goods_sold": has_cost_of_goods,
        "has_shipping_weight": has_shipping_weight,
        "has_product_highlights": has_product_highlights,
    }
    analysis["custom_labels"] = {k: dict(v) for k, v in custom_labels.items()}
    analysis["item_groups"] = len([k for k in item_group_ids if k != "(none)"])
    analysis["google_categories"] = dict(sorted(google_categories.items(), key=lambda x: -x[1]))
    analysis["products_with_issues_detail"] = products_with_issues

    # ── Account-level issues ──
    account_issues = []
    for issue in account_status.get("accountLevelIssues", []):
        account_issues.append({
            "title": issue.get("title", ""),
            "severity": issue.get("severity", ""),
            "detail": issue.get("detail", ""),
            "documentation": issue.get("documentation", ""),
            "country": issue.get("country", ""),
            "destination": issue.get("destination", ""),
        })
    analysis["account_level_issues"] = account_issues

    return analysis


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("GOOGLE MERCHANT CENTER — ACCOUNT HEALTH AUDIT")
    print(f"Merchant ID: {MC_ID}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Pull data
    account = pull_account_info()
    products = pull_all_products()
    statuses = pull_product_statuses()
    account_status = pull_account_statuses()

    # Save raw data
    with open(OUT_DIR / "raw_products.json", "w") as f:
        json.dump(products, f, indent=2, default=str)
    print(f"\nSaved raw products to {OUT_DIR / 'raw_products.json'}")

    with open(OUT_DIR / "raw_statuses.json", "w") as f:
        json.dump(statuses, f, indent=2, default=str)
    print(f"Saved raw statuses to {OUT_DIR / 'raw_statuses.json'}")

    with open(OUT_DIR / "raw_account_status.json", "w") as f:
        json.dump(account_status, f, indent=2, default=str)
    print(f"Saved account status to {OUT_DIR / 'raw_account_status.json'}")

    # Analyze
    print("\nAnalyzing...")
    analysis = analyze(products, statuses, account_status)

    with open(OUT_DIR / "analysis.json", "w") as f:
        json.dump(analysis, f, indent=2, default=str)
    print(f"Saved analysis to {OUT_DIR / 'analysis.json'}")

    # Print summary
    print("\n" + "=" * 60)
    print("QUICK SUMMARY")
    print("=" * 60)
    print(f"  Total products: {analysis['total_products']}")
    print(f"  Approval: {json.dumps(analysis['approval_breakdown'])}")
    print(f"  Disapproved: {analysis['disapproved_count']}")
    print(f"  Products with issues: {analysis['products_with_issues_count']}")
    print(f"  GTIN coverage: {analysis['gtin_coverage']}")
    print(f"  Missing fields: {json.dumps(analysis['missing_fields'])}")
    print(f"  Item groups: {analysis['item_groups']}")
    print(f"  Account-level issues: {len(analysis['account_level_issues'])}")

    if analysis['account_level_issues']:
        print("\n  Account Issues:")
        for issue in analysis['account_level_issues']:
            print(f"    [{issue['severity']}] {issue['title']}: {issue['detail'][:100]}")

    print(f"\n  Top issue types:")
    for issue_type, count in list(analysis['issues_by_type'].items())[:10]:
        print(f"    {issue_type}: {count}")


if __name__ == "__main__":
    main()
