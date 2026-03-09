#!/usr/bin/env python3
"""
Backfill 2025 data — sales (WC + Walmart) and ad spend (Google Ads) only.
No COGS or Shippo (not needed for YoY comparison).

Usage: python3 backfill_2025.py
"""

import sys
import time
from datetime import date, timedelta

# Import from daily_pull
sys.path.insert(0, str(__file__).rsplit("/", 1)[0])
from daily_pull import (
    pull_woocommerce,
    pull_walmart,
    pull_google_ads,
    supabase_upsert,
    SUPABASE_URL,
    SUPABASE_KEY,
)

START = date(2025, 1, 1)
END = date(2025, 12, 31)


def backfill_date(report_date):
    """Pull sales + ads for a single date (no COGS/Shippo)."""
    print(f"\n{'='*50}  {report_date}  {'='*10}")

    # WooCommerce
    wc = pull_woocommerce(report_date)

    # Walmart
    wm = pull_walmart(report_date)

    # Google Ads
    ads = pull_google_ads(report_date)

    total_rev = wc["sales"]["revenue"] + wm["sales"]["revenue"]
    print(f"  >> Total: ${total_rev:,.2f} rev | ${ads['spend']:,.2f} ad spend")

    # Write to Supabase
    if SUPABASE_URL and SUPABASE_KEY:
        supabase_upsert("daily_sales", [wc["sales"], wm["sales"]])
        supabase_upsert("daily_ad_spend", [ads])


def main():
    current = START
    day_count = 0
    total_rev = 0
    total_spend = 0

    while current <= END:
        try:
            backfill_date(current)
            day_count += 1
        except Exception as e:
            print(f"  [ERR] {current}: {e}")

        current += timedelta(days=1)
        time.sleep(0.5)  # gentle on APIs

        # Progress every 30 days
        if day_count % 30 == 0:
            print(f"\n  *** Progress: {day_count} days processed ***\n")

    print(f"\n\n{'='*60}")
    print(f"  BACKFILL COMPLETE: {START} → {END}")
    print(f"  Days processed: {day_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
