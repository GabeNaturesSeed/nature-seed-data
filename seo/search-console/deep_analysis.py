"""
Deep Analysis: Google Search Console data for naturesseed.com
Pulls query+page combos and computes cannibalization, CTR gaps, etc.
"""
import json
from collections import defaultdict
from datetime import date, timedelta
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

sc = build("searchconsole", "v1", credentials=creds)
SITE = "sc-domain:naturesseed.com"

# Date range: last 30 days, ending 3 days ago for GSC lag
end_date = date.today() - timedelta(days=3)
start_date = end_date - timedelta(days=29)
START = start_date.isoformat()
END = end_date.isoformat()

print("=" * 70)
print("  GSC DEEP ANALYSIS — naturesseed.com")
print(f"  Date range: {START} → {END}")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════
# 1. Pull ALL query+page combos
# ═══════════════════════════════════════════════════════════════
print("\n  [1/2] Pulling query+page combos (rowLimit=25000)...")
qp_response = sc.searchanalytics().query(
    siteUrl=SITE,
    body={
        "startDate": START,
        "endDate": END,
        "dimensions": ["query", "page"],
        "rowLimit": 25000,
        "type": "web",
    },
).execute()
qp_rows = qp_response.get("rows", [])
print(f"         Got {len(qp_rows):,} query+page rows")

# ═══════════════════════════════════════════════════════════════
# 2. Pull ALL pages
# ═══════════════════════════════════════════════════════════════
print("  [2/2] Pulling all pages (rowLimit=25000)...")
page_response = sc.searchanalytics().query(
    siteUrl=SITE,
    body={
        "startDate": START,
        "endDate": END,
        "dimensions": ["page"],
        "rowLimit": 25000,
        "type": "web",
    },
).execute()
page_rows = page_response.get("rows", [])
print(f"         Got {len(page_rows):,} page rows")

# ═══════════════════════════════════════════════════════════════
# 3. Compute derived datasets
# ═══════════════════════════════════════════════════════════════
print("\n  Computing derived data...")

# For each page: all queries it ranks for
page_to_queries = defaultdict(list)
# For each query: all pages that rank for it
query_to_pages = defaultdict(list)

for row in qp_rows:
    query = row["keys"][0]
    page = row["keys"][1]
    entry = {
        "query": query,
        "page": page,
        "clicks": row["clicks"],
        "impressions": row["impressions"],
        "ctr": round(row["ctr"], 4),
        "position": round(row["position"], 1),
    }
    page_to_queries[page].append({
        "query": query,
        "clicks": entry["clicks"],
        "impressions": entry["impressions"],
        "ctr": entry["ctr"],
        "position": entry["position"],
    })
    query_to_pages[query].append({
        "page": page,
        "clicks": entry["clicks"],
        "impressions": entry["impressions"],
        "ctr": entry["ctr"],
        "position": entry["position"],
    })

# Cannibalization: queries where 2+ pages rank
cannibalized = []
for query, pages in query_to_pages.items():
    if len(pages) >= 2:
        total_impressions = sum(p["impressions"] for p in pages)
        total_clicks = sum(p["clicks"] for p in pages)
        cannibalized.append({
            "query": query,
            "num_pages": len(pages),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "pages": sorted(pages, key=lambda p: p["impressions"], reverse=True),
        })

cannibalized.sort(key=lambda x: x["total_impressions"], reverse=True)

# Pages with highest impressions but lowest CTR
page_stats = []
for row in page_rows:
    page = row["keys"][0]
    page_stats.append({
        "page": page,
        "clicks": row["clicks"],
        "impressions": row["impressions"],
        "ctr": round(row["ctr"], 4),
        "position": round(row["position"], 1),
    })

# Sort by impressions desc for the "high impressions, low CTR" view
pages_by_impressions = sorted(page_stats, key=lambda p: p["impressions"], reverse=True)

# ═══════════════════════════════════════════════════════════════
# 4. Print summaries
# ═══════════════════════════════════════════════════════════════
unique_queries = set(row["keys"][0] for row in qp_rows)
unique_pages = set(row["keys"][1] for row in qp_rows)

print("\n" + "=" * 70)
print("  SUMMARY")
print("=" * 70)
print(f"  Total unique queries:        {len(unique_queries):,}")
print(f"  Total unique pages:          {len(unique_pages):,}")
print(f"  Cannibalized queries (2+ pg): {len(cannibalized):,}")

# Top 30 cannibalized queries
print("\n" + "-" * 70)
print("  TOP 30 CANNIBALIZED QUERIES (by impressions)")
print("-" * 70)
print(f"  {'Query':<45s} | {'#Pgs':>4s} | {'Impressions':>11s} | {'Clicks':>6s}")
print("  " + "-" * 72)
for item in cannibalized[:30]:
    q = item["query"][:45]
    print(f"  {q:<45s} | {item['num_pages']:>4} | {item['total_impressions']:>11,} | {item['total_clicks']:>6,}")
    # Show each page for this query
    for pg in item["pages"][:5]:
        short = pg["page"].replace("https://naturesseed.com", "")[:50]
        print(f"      {short:<50s}  pos={pg['position']:>5.1f}  impr={pg['impressions']:>6,}  clicks={pg['clicks']:>4,}")

# Top 20 pages by impressions with CTR
print("\n" + "-" * 70)
print("  TOP 20 PAGES BY IMPRESSIONS (with CTR)")
print("-" * 70)
print(f"  {'Page':<55s} | {'Impr':>7s} | {'Clicks':>6s} | {'CTR':>6s} | {'Pos':>5s}")
print("  " + "-" * 87)
for p in pages_by_impressions[:20]:
    short = p["page"].replace("https://naturesseed.com", "")[:55]
    ctr_pct = p["ctr"] * 100
    print(f"  {short:<55s} | {p['impressions']:>7,} | {p['clicks']:>6,} | {ctr_pct:>5.1f}% | {p['position']:>5.1f}")

# High-impression / low-CTR pages (potential quick wins)
print("\n" + "-" * 70)
print("  HIGH IMPRESSION / LOW CTR PAGES (CTR < 2%, Impr > 500)")
print("-" * 70)
low_ctr_pages = [p for p in pages_by_impressions if p["ctr"] < 0.02 and p["impressions"] > 500]
low_ctr_pages.sort(key=lambda p: p["impressions"], reverse=True)
print(f"  {'Page':<55s} | {'Impr':>7s} | {'Clicks':>6s} | {'CTR':>6s} | {'Pos':>5s}")
print("  " + "-" * 87)
for p in low_ctr_pages[:20]:
    short = p["page"].replace("https://naturesseed.com", "")[:55]
    ctr_pct = p["ctr"] * 100
    print(f"  {short:<55s} | {p['impressions']:>7,} | {p['clicks']:>6,} | {ctr_pct:>5.1f}% | {p['position']:>5.1f}")

# ═══════════════════════════════════════════════════════════════
# 5. Save to JSON
# ═══════════════════════════════════════════════════════════════
output_path = Path(__file__).resolve().parent / "data" / "deep_analysis.json"
output_path.parent.mkdir(parents=True, exist_ok=True)

output = {
    "meta": {
        "site": SITE,
        "start_date": START,
        "end_date": END,
        "total_query_page_rows": len(qp_rows),
        "total_page_rows": len(page_rows),
        "unique_queries": len(unique_queries),
        "unique_pages": len(unique_pages),
        "cannibalized_query_count": len(cannibalized),
    },
    "query_page_raw": [
        {
            "query": row["keys"][0],
            "page": row["keys"][1],
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": round(row["ctr"], 4),
            "position": round(row["position"], 1),
        }
        for row in qp_rows
    ],
    "pages": page_stats,
    "cannibalization": cannibalized,
}

with open(output_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n  [SAVED] {output_path}")
print(f"          JSON size: {output_path.stat().st_size / 1024:.0f} KB")
print("\n" + "=" * 70)
print("  DEEP ANALYSIS COMPLETE")
print("=" * 70)
