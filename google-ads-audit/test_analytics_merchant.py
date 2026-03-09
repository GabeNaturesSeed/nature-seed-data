"""
Quick test: Google Analytics + Merchant Center API connections
Pulls sample daily-report data from both.
"""
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric
)
from googleapiclient.discovery import build

# ── Load .env ──
env_path = Path(__file__).resolve().parent.parent / ".env"
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

creds = Credentials(
    token=None,
    refresh_token=env_vars["GOOGLE_ADS_REFRESH_TOKEN"],
    client_id=env_vars["GOOGLE_ADS_CLIENT_ID"],
    client_secret=env_vars["GOOGLE_ADS_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token",
)

GA_PROPERTY = env_vars["GOOGLE_ANALYTICS_PROPERTY_ID"]
MC_ID = env_vars["GOOGLE_MERCHANT_CENTER_ID"]


# ═══════════════════════════════════════════════════════════════
# GOOGLE ANALYTICS 4
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("  GOOGLE ANALYTICS 4 — Test Pull")
print("=" * 60)

try:
    ga_client = BetaAnalyticsDataClient(credentials=creds)

    # 1. Last 7 days: sessions, users, conversions, revenue
    print("\n  --- Last 7 Days Summary ---")
    response = ga_client.run_report(RunReportRequest(
        property=f"properties/{GA_PROPERTY}",
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="ecommercePurchases"),
            Metric(name="purchaseRevenue"),
            Metric(name="averagePurchaseRevenuePerUser"),
            Metric(name="sessionConversionRate"),
        ],
    ))
    for row in response.rows:
        vals = [v.value for v in row.metric_values]
        print(f"    Sessions:          {int(float(vals[0])):,}")
        print(f"    Total Users:       {int(float(vals[1])):,}")
        print(f"    New Users:         {int(float(vals[2])):,}")
        print(f"    Purchases:         {int(float(vals[3])):,}")
        print(f"    Revenue:           ${float(vals[4]):,.2f}")
        print(f"    Rev/User:          ${float(vals[5]):,.2f}")
        print(f"    Conv Rate:         {float(vals[6])*100:.2f}%")

    # 2. Daily breakdown last 7 days
    print("\n  --- Daily Breakdown (Last 7 Days) ---")
    response2 = ga_client.run_report(RunReportRequest(
        property=f"properties/{GA_PROPERTY}",
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        dimensions=[Dimension(name="date")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="ecommercePurchases"),
            Metric(name="purchaseRevenue"),
        ],
    ))
    print(f"    {'Date':<12s} | {'Sessions':>8s} | {'Users':>6s} | {'Orders':>6s} | {'Revenue':>10s}")
    print("    " + "-" * 52)
    for row in sorted(response2.rows, key=lambda r: r.dimension_values[0].value):
        date = row.dimension_values[0].value
        date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        vals = [v.value for v in row.metric_values]
        print(f"    {date_fmt:<12s} | {int(float(vals[0])):>8,} | {int(float(vals[1])):>6,} | {int(float(vals[2])):>6,} | ${float(vals[3]):>9,.2f}")

    # 3. Top traffic sources
    print("\n  --- Top Traffic Sources (Last 7 Days) ---")
    response3 = ga_client.run_report(RunReportRequest(
        property=f"properties/{GA_PROPERTY}",
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="ecommercePurchases"),
            Metric(name="purchaseRevenue"),
        ],
    ))
    print(f"    {'Channel':<30s} | {'Sessions':>8s} | {'Orders':>6s} | {'Revenue':>10s}")
    print("    " + "-" * 62)
    for row in sorted(response3.rows, key=lambda r: -float(r.metric_values[0].value)):
        channel = row.dimension_values[0].value
        vals = [v.value for v in row.metric_values]
        print(f"    {channel:<30s} | {int(float(vals[0])):>8,} | {int(float(vals[1])):>6,} | ${float(vals[2]):>9,.2f}")

    # 4. Top landing pages
    print("\n  --- Top Landing Pages (Last 7 Days, Top 15) ---")
    response4 = ga_client.run_report(RunReportRequest(
        property=f"properties/{GA_PROPERTY}",
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        dimensions=[Dimension(name="landingPagePlusQueryString")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="ecommercePurchases"),
            Metric(name="purchaseRevenue"),
        ],
        limit=15,
    ))
    print(f"    {'Landing Page':<55s} | {'Sess':>5s} | {'Ord':>4s} | {'Revenue':>10s}")
    print("    " + "-" * 82)
    for row in sorted(response4.rows, key=lambda r: -float(r.metric_values[0].value)):
        page = row.dimension_values[0].value[:55]
        vals = [v.value for v in row.metric_values]
        print(f"    {page:<55s} | {int(float(vals[0])):>5,} | {int(float(vals[1])):>4,} | ${float(vals[2]):>9,.2f}")

    print("\n  [OK] Google Analytics 4 connected successfully")

except Exception as e:
    print(f"\n  [ERR] Analytics failed: {e}")


# ═══════════════════════════════════════════════════════════════
# GOOGLE MERCHANT CENTER
# ═══════════════════════════════════════════════════════════════
print("\n\n" + "=" * 60)
print("  GOOGLE MERCHANT CENTER — Test Pull")
print("=" * 60)

try:
    mc_service = build("content", "v2.1", credentials=creds)

    # 1. Account info
    account = mc_service.accounts().get(merchantId=MC_ID, accountId=MC_ID).execute()
    print(f"\n  Account: {account.get('name', 'N/A')}")
    print(f"  ID: {MC_ID}")

    # 2. Product status counts
    print("\n  --- Product Status Summary ---")
    statuses = mc_service.productstatuses().list(merchantId=MC_ID, maxResults=250).execute()
    products = statuses.get("resources", [])
    total = len(products)
    approved = 0
    disapproved = 0
    pending = 0
    expiring = 0

    for p in products:
        dest_statuses = p.get("destinationStatuses", [])
        for ds in dest_statuses:
            if ds.get("destination") == "SurfacesAcrossGoogle" or ds.get("destination") == "Shopping":
                status = ds.get("status", "").lower()
                if status == "approved":
                    approved += 1
                elif status == "disapproved":
                    disapproved += 1
                elif status == "pending":
                    pending += 1
                break

    print(f"    Total products:    {total}")
    print(f"    Approved:          {approved}")
    print(f"    Disapproved:       {disapproved}")
    print(f"    Pending:           {pending}")

    # Check if there are more pages
    next_token = statuses.get("nextPageToken")
    if next_token:
        print(f"    (more products exist — showing first 250)")

    # 3. Show some disapproved products if any
    if disapproved > 0:
        print(f"\n  --- Disapproved Products (up to 10) ---")
        count = 0
        for p in products:
            dest_statuses = p.get("destinationStatuses", [])
            issues = p.get("itemLevelIssues", [])
            for ds in dest_statuses:
                if ds.get("status", "").lower() == "disapproved":
                    title = p.get("title", "Unknown")[:50]
                    issue_list = [i.get("description", "") for i in issues[:2]]
                    print(f"    {title}")
                    for iss in issue_list:
                        print(f"      Issue: {iss[:80]}")
                    count += 1
                    break
            if count >= 10:
                break

    # 4. Products with issues
    issue_products = [p for p in products if p.get("itemLevelIssues")]
    print(f"\n  Products with issues: {len(issue_products)} of {total}")

    print("\n  [OK] Google Merchant Center connected successfully")

except Exception as e:
    print(f"\n  [ERR] Merchant Center failed: {e}")


print("\n\n" + "=" * 60)
print("  ALL TESTS COMPLETE")
print("=" * 60)
