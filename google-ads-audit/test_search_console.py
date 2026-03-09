"""
Quick test: Google Search Console API connection
Pulls top queries and pages for the last 7 days.
"""
from pathlib import Path
from google.oauth2.credentials import Credentials
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

# ═══════════════════════════════════════════════════════════════
# STEP 1: List verified sites to find the right property
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("  GOOGLE SEARCH CONSOLE — Test Pull")
print("=" * 60)

try:
    sc_service = build("searchconsole", "v1", credentials=creds)

    # List all sites the account has access to
    print("\n  --- Verified Sites ---")
    sites = sc_service.sites().list().execute()
    site_list = sites.get("siteEntry", [])

    if not site_list:
        print("  No verified sites found.")
    else:
        for s in site_list:
            print(f"    {s['siteUrl']}  (permission: {s.get('permissionLevel', 'N/A')})")

        # Use the first site (or naturesseed.com if found)
        site_url = site_list[0]["siteUrl"]
        for s in site_list:
            if "naturesseed" in s["siteUrl"]:
                site_url = s["siteUrl"]
                break

        print(f"\n  Using site: {site_url}")

        # STEP 2: Top queries (last 7 days)
        print("\n  --- Top 20 Search Queries (Last 7 Days) ---")
        query_response = sc_service.searchanalytics().query(
            siteUrl=site_url,
            body={
                "startDate": "2026-03-02",
                "endDate": "2026-03-08",
                "dimensions": ["query"],
                "rowLimit": 20,
                "type": "web",
            },
        ).execute()

        rows = query_response.get("rows", [])
        print(f"    {'Query':<50s} | {'Clicks':>6s} | {'Impr':>7s} | {'CTR':>6s} | {'Pos':>5s}")
        print("    " + "-" * 82)
        for row in rows:
            query = row["keys"][0][:50]
            clicks = int(row["clicks"])
            impressions = int(row["impressions"])
            ctr = row["ctr"] * 100
            position = row["position"]
            print(f"    {query:<50s} | {clicks:>6,} | {impressions:>7,} | {ctr:>5.1f}% | {position:>5.1f}")

        # STEP 3: Top pages (last 7 days)
        print("\n  --- Top 15 Pages (Last 7 Days) ---")
        page_response = sc_service.searchanalytics().query(
            siteUrl=site_url,
            body={
                "startDate": "2026-03-02",
                "endDate": "2026-03-08",
                "dimensions": ["page"],
                "rowLimit": 15,
                "type": "web",
            },
        ).execute()

        page_rows = page_response.get("rows", [])
        print(f"    {'Page':<60s} | {'Clicks':>6s} | {'Impr':>7s} | {'CTR':>6s} | {'Pos':>5s}")
        print("    " + "-" * 92)
        for row in page_rows:
            page = row["keys"][0].replace("https://naturesseed.com", "")[:60]
            clicks = int(row["clicks"])
            impressions = int(row["impressions"])
            ctr = row["ctr"] * 100
            position = row["position"]
            print(f"    {page:<60s} | {clicks:>6,} | {impressions:>7,} | {ctr:>5.1f}% | {position:>5.1f}")

        # STEP 4: Daily totals
        print("\n  --- Daily Totals (Last 7 Days) ---")
        daily_response = sc_service.searchanalytics().query(
            siteUrl=site_url,
            body={
                "startDate": "2026-03-02",
                "endDate": "2026-03-08",
                "dimensions": ["date"],
                "type": "web",
            },
        ).execute()

        daily_rows = daily_response.get("rows", [])
        print(f"    {'Date':<12s} | {'Clicks':>7s} | {'Impressions':>11s} | {'CTR':>6s} | {'Avg Pos':>7s}")
        print("    " + "-" * 52)
        for row in sorted(daily_rows, key=lambda r: r["keys"][0]):
            date = row["keys"][0]
            clicks = int(row["clicks"])
            impressions = int(row["impressions"])
            ctr = row["ctr"] * 100
            position = row["position"]
            print(f"    {date:<12s} | {clicks:>7,} | {impressions:>11,} | {ctr:>5.1f}% | {position:>7.1f}")

    print("\n  [OK] Google Search Console connected successfully")

except Exception as e:
    print(f"\n  [ERR] Search Console failed: {e}")

print("\n" + "=" * 60)
print("  TEST COMPLETE")
print("=" * 60)
