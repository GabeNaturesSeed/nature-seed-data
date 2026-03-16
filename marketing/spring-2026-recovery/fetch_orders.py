#!/usr/bin/env python3
"""
Fetch WooCommerce completed orders for multiple periods and save to JSON.
Periods:
  - 2024 Q3/Q4 (Sept-Dec 2024)
  - 2025 Q3 (Jul-Sep 2025)
  - 2025 Q4 (Oct-Dec 2025)
  - 2026 Q1 (Jan-Feb 2026)
"""

import json
import time
import requests
from datetime import datetime

BASE_URL = "https://naturesseed.com/wp-json/wc/v3"
CK = "ck_9629579f1379f272169de8628edddb00b24737f9"
CS = "cs_bf6dcf206d6ed26b83e55e8af62c16de26339815"
AUTH = (CK, CS)

DATA_DIR = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/spring-2026-recovery/data"

PERIODS = [
    {
        "label": "2024 Q3/Q4 (Sep-Dec 2024)",
        "after": "2024-09-01T00:00:00",
        "before": "2024-12-31T23:59:59",
        "filename": "orders_2024_q3q4.json",
    },
    {
        "label": "2025 Q3 (Jul-Sep 2025)",
        "after": "2025-07-01T00:00:00",
        "before": "2025-09-30T23:59:59",
        "filename": "orders_2025_q3.json",
    },
    {
        "label": "2025 Q4 (Oct-Dec 2025)",
        "after": "2025-10-01T00:00:00",
        "before": "2025-12-31T23:59:59",
        "filename": "orders_2025_q4.json",
    },
    {
        "label": "2026 Q1 (Jan-Feb 2026)",
        "after": "2026-01-01T00:00:00",
        "before": "2026-02-28T23:59:59",
        "filename": "orders_2026_q1.json",
    },
]


def extract_order(order):
    """Extract relevant fields from a raw WooCommerce order."""
    billing = order.get("billing", {})
    line_items = []
    for item in order.get("line_items", []):
        line_items.append({
            "product_id": item.get("product_id"),
            "variation_id": item.get("variation_id"),
            "name": item.get("name"),
            "sku": item.get("sku"),
            "quantity": item.get("quantity"),
            "subtotal": item.get("subtotal"),
            "total": item.get("total"),
            "price": item.get("price"),
        })
    return {
        "id": order.get("id"),
        "number": order.get("number"),
        "status": order.get("status"),
        "date_created": order.get("date_created"),
        "total": order.get("total"),
        "customer_email": billing.get("email"),
        "billing_first_name": billing.get("first_name"),
        "billing_last_name": billing.get("last_name"),
        "line_items": line_items,
    }


def fetch_orders_for_period(after, before, label):
    """Paginate through all completed orders for a given date range."""
    all_orders = []
    page = 1
    while True:
        params = {
            "after": after,
            "before": before,
            "status": "completed",
            "per_page": 100,
            "page": page,
            "orderby": "date",
            "order": "asc",
        }
        print(f"  Fetching page {page} ...", end=" ", flush=True)
        resp = requests.get(f"{BASE_URL}/orders", auth=AUTH, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        count = len(data)
        print(f"got {count} orders")

        if count == 0:
            break

        for raw in data:
            all_orders.append(extract_order(raw))

        # Check WooCommerce pagination headers
        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break

        page += 1
        time.sleep(0.3)  # rate limiting

    return all_orders


def main():
    results = {}  # label -> list of orders
    all_emails = set()

    for period in PERIODS:
        label = period["label"]
        print(f"\n{'='*60}")
        print(f"Fetching: {label}")
        print(f"  Range: {period['after']} to {period['before']}")
        print(f"{'='*60}")

        orders = fetch_orders_for_period(period["after"], period["before"], label)
        results[label] = orders

        # Collect emails
        for o in orders:
            email = o.get("customer_email")
            if email:
                all_emails.add(email.lower().strip())

        # Save to file
        filepath = f"{DATA_DIR}/{period['filename']}"
        with open(filepath, "w") as f:
            json.dump(orders, f, indent=2)
        print(f"  Saved {len(orders)} orders to {filepath}")

        time.sleep(0.3)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    total_orders = 0
    for label, orders in results.items():
        count = len(orders)
        total_orders += count
        # Calculate revenue
        revenue = sum(float(o.get("total", 0) or 0) for o in orders)
        print(f"  {label}: {count} orders, ${revenue:,.2f} revenue")
    print(f"  {'─'*50}")
    print(f"  Total orders across all periods: {total_orders}")
    print(f"  Total unique customer emails:    {len(all_emails)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
