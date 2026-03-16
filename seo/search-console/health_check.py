"""
Google Search Console — Full Health Check for Nature's Seed
Pulls 90-day data across queries, pages, devices, countries,
and identifies opportunities and issues.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

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

# ── Date ranges ──
today = datetime.now().date()
# GSC data is typically 2-3 days behind
end_date = today - timedelta(days=3)
start_90 = end_date - timedelta(days=89)
start_30 = end_date - timedelta(days=29)
start_7 = end_date - timedelta(days=6)

# For comparison: previous 30 days
prev_30_end = start_30 - timedelta(days=1)
prev_30_start = prev_30_end - timedelta(days=29)

SITE = "sc-domain:naturesseed.com"

def query_sc(start, end, dimensions, row_limit=25000, dim_filter=None):
    body = {
        "startDate": str(start),
        "endDate": str(end),
        "dimensions": dimensions,
        "rowLimit": row_limit,
        "type": "web",
    }
    if dim_filter:
        body["dimensionFilterGroups"] = [{"filters": dim_filter}]
    return sc.searchanalytics().query(siteUrl=SITE, body=body).execute()

print("=" * 70)
print("  GOOGLE SEARCH CONSOLE — Health Check")
print(f"  Site: {SITE}")
print(f"  90-day range: {start_90} → {end_date}")
print(f"  30-day range: {start_30} → {end_date}")
print(f"  7-day range:  {start_7} → {end_date}")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════
# 1. OVERALL METRICS (30-day vs previous 30-day)
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ 1. OVERALL PERFORMANCE (30-day vs Previous 30-day) ━━━")

current = query_sc(start_30, end_date, ["date"])
previous = query_sc(prev_30_start, prev_30_end, ["date"])

def sum_metrics(rows):
    clicks = sum(r["clicks"] for r in rows)
    impressions = sum(r["impressions"] for r in rows)
    ctr = clicks / impressions if impressions else 0
    avg_pos = sum(r["position"] * r["impressions"] for r in rows) / impressions if impressions else 0
    return clicks, impressions, ctr, avg_pos

cur_rows = current.get("rows", [])
prev_rows = previous.get("rows", [])

cc, ci, cctr, cpos = sum_metrics(cur_rows)
pc, pi, pctr, ppos = sum_metrics(prev_rows)

def pct_change(new, old):
    if old == 0: return "N/A"
    change = ((new - old) / old) * 100
    arrow = "▲" if change > 0 else "▼" if change < 0 else "─"
    return f"{arrow} {abs(change):.1f}%"

print(f"\n  {'Metric':<20s} | {'Current 30d':>12s} | {'Previous 30d':>12s} | {'Change':>10s}")
print("  " + "-" * 62)
print(f"  {'Clicks':<20s} | {cc:>12,} | {pc:>12,} | {pct_change(cc, pc):>10s}")
print(f"  {'Impressions':<20s} | {ci:>12,} | {pi:>12,} | {pct_change(ci, pi):>10s}")
print(f"  {'CTR':<20s} | {cctr*100:>11.2f}% | {pctr*100:>11.2f}% | {pct_change(cctr, pctr):>10s}")
print(f"  {'Avg Position':<20s} | {cpos:>12.1f} | {ppos:>12.1f} | {pct_change(ppos, cpos):>10s}")

# ═══════════════════════════════════════════════════════════════
# 2. DAILY TREND (last 30 days)
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ 2. DAILY TREND (Last 30 Days) ━━━")
print(f"\n  {'Date':<12s} | {'Clicks':>7s} | {'Impressions':>11s} | {'CTR':>6s} | {'Pos':>5s}")
print("  " + "-" * 50)
for row in sorted(cur_rows, key=lambda r: r["keys"][0]):
    d = row["keys"][0]
    print(f"  {d:<12s} | {int(row['clicks']):>7,} | {int(row['impressions']):>11,} | {row['ctr']*100:>5.1f}% | {row['position']:>5.1f}")

# ═══════════════════════════════════════════════════════════════
# 3. TOP QUERIES (90 days, top 50)
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ 3. TOP 50 QUERIES (90 Days) ━━━")
q90 = query_sc(start_90, end_date, ["query"], 50)
q_rows = q90.get("rows", [])
print(f"\n  {'#':>3s}  {'Query':<55s} | {'Clicks':>7s} | {'Impr':>7s} | {'CTR':>6s} | {'Pos':>5s}")
print("  " + "-" * 90)
for i, row in enumerate(q_rows, 1):
    q = row["keys"][0][:55]
    print(f"  {i:>3d}  {q:<55s} | {int(row['clicks']):>7,} | {int(row['impressions']):>7,} | {row['ctr']*100:>5.1f}% | {row['position']:>5.1f}")

# ═══════════════════════════════════════════════════════════════
# 4. TOP PAGES (90 days, top 30)
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ 4. TOP 30 PAGES (90 Days) ━━━")
p90 = query_sc(start_90, end_date, ["page"], 30)
p_rows = p90.get("rows", [])
print(f"\n  {'#':>3s}  {'Page':<65s} | {'Clicks':>7s} | {'Impr':>7s} | {'CTR':>6s} | {'Pos':>5s}")
print("  " + "-" * 100)
for i, row in enumerate(p_rows, 1):
    page = row["keys"][0].replace("https://naturesseed.com", "")[:65]
    print(f"  {i:>3d}  {page:<65s} | {int(row['clicks']):>7,} | {int(row['impressions']):>7,} | {row['ctr']*100:>5.1f}% | {row['position']:>5.1f}")

# ═══════════════════════════════════════════════════════════════
# 5. DEVICE BREAKDOWN (30 days)
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ 5. DEVICE BREAKDOWN (30 Days) ━━━")
dev = query_sc(start_30, end_date, ["device"])
dev_rows = dev.get("rows", [])
total_clicks = sum(r["clicks"] for r in dev_rows)
print(f"\n  {'Device':<12s} | {'Clicks':>7s} | {'Share':>6s} | {'Impr':>9s} | {'CTR':>6s} | {'Pos':>5s}")
print("  " + "-" * 55)
for row in sorted(dev_rows, key=lambda r: -r["clicks"]):
    device = row["keys"][0].title()
    share = row["clicks"] / total_clicks * 100 if total_clicks else 0
    print(f"  {device:<12s} | {int(row['clicks']):>7,} | {share:>5.1f}% | {int(row['impressions']):>9,} | {row['ctr']*100:>5.1f}% | {row['position']:>5.1f}")

# ═══════════════════════════════════════════════════════════════
# 6. COUNTRY BREAKDOWN (30 days, top 10)
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ 6. TOP COUNTRIES (30 Days) ━━━")
countries = query_sc(start_30, end_date, ["country"], 10)
c_rows = countries.get("rows", [])
print(f"\n  {'Country':<8s} | {'Clicks':>7s} | {'Impr':>9s} | {'CTR':>6s} | {'Pos':>5s}")
print("  " + "-" * 42)
for row in c_rows:
    print(f"  {row['keys'][0]:<8s} | {int(row['clicks']):>7,} | {int(row['impressions']):>9,} | {row['ctr']*100:>5.1f}% | {row['position']:>5.1f}")

# ═══════════════════════════════════════════════════════════════
# 7. QUICK WINS — High impressions, low CTR, positions 4-20
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ 7. QUICK WINS — High Impressions, Low CTR (Pos 4-20) ━━━")
print("  (Queries with 50+ impressions/30d, CTR < 3%, position 4-20)")
qw = query_sc(start_30, end_date, ["query"], 5000)
qw_rows = qw.get("rows", [])
quick_wins = [
    r for r in qw_rows
    if r["impressions"] >= 50
    and r["ctr"] < 0.03
    and 4 <= r["position"] <= 20
]
quick_wins.sort(key=lambda r: -r["impressions"])
print(f"\n  {'#':>3s}  {'Query':<50s} | {'Clicks':>6s} | {'Impr':>6s} | {'CTR':>6s} | {'Pos':>5s}")
print("  " + "-" * 85)
for i, row in enumerate(quick_wins[:30], 1):
    q = row["keys"][0][:50]
    print(f"  {i:>3d}  {q:<50s} | {int(row['clicks']):>6,} | {int(row['impressions']):>6,} | {row['ctr']*100:>5.1f}% | {row['position']:>5.1f}")

# ═══════════════════════════════════════════════════════════════
# 8. STRIKING DISTANCE — Position 5-15, good impressions
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ 8. STRIKING DISTANCE — Almost Page 1 (Pos 5-15) ━━━")
print("  (Queries with 20+ impressions, position 5-15 — could reach top 3)")
striking = [
    r for r in qw_rows
    if r["impressions"] >= 20
    and 5 <= r["position"] <= 15
]
striking.sort(key=lambda r: -r["impressions"])
print(f"\n  {'#':>3s}  {'Query':<50s} | {'Clicks':>6s} | {'Impr':>6s} | {'CTR':>6s} | {'Pos':>5s}")
print("  " + "-" * 85)
for i, row in enumerate(striking[:30], 1):
    q = row["keys"][0][:50]
    print(f"  {i:>3d}  {q:<50s} | {int(row['clicks']):>6,} | {int(row['impressions']):>6,} | {row['ctr']*100:>5.1f}% | {row['position']:>5.1f}")

# ═══════════════════════════════════════════════════════════════
# 9. BRANDED vs NON-BRANDED
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ 9. BRANDED vs NON-BRANDED (30 Days) ━━━")
brand_terms = ["nature's seed", "natures seed", "naturesseed", "nature seed"]
branded_clicks = 0
branded_impr = 0
nonbranded_clicks = 0
nonbranded_impr = 0

for row in qw_rows:
    q = row["keys"][0].lower()
    if any(b in q for b in brand_terms):
        branded_clicks += row["clicks"]
        branded_impr += row["impressions"]
    else:
        nonbranded_clicks += row["clicks"]
        nonbranded_impr += row["impressions"]

total_c = branded_clicks + nonbranded_clicks
total_i = branded_impr + nonbranded_impr
print(f"\n  {'Type':<15s} | {'Clicks':>7s} | {'% Clicks':>8s} | {'Impressions':>11s} | {'CTR':>6s}")
print("  " + "-" * 55)
b_ctr = branded_clicks / branded_impr * 100 if branded_impr else 0
nb_ctr = nonbranded_clicks / nonbranded_impr * 100 if nonbranded_impr else 0
print(f"  {'Branded':<15s} | {branded_clicks:>7,} | {branded_clicks/total_c*100 if total_c else 0:>7.1f}% | {branded_impr:>11,} | {b_ctr:>5.1f}%")
print(f"  {'Non-Branded':<15s} | {nonbranded_clicks:>7,} | {nonbranded_clicks/total_c*100 if total_c else 0:>7.1f}% | {nonbranded_impr:>11,} | {nb_ctr:>5.1f}%")

# ═══════════════════════════════════════════════════════════════
# 10. LOW-HANGING FRUIT PAGES — High impr pages with low CTR
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ 10. PAGE OPPORTUNITIES — High Impressions, Low CTR ━━━")
p30 = query_sc(start_30, end_date, ["page"], 5000)
p30_rows = p30.get("rows", [])
page_opps = [
    r for r in p30_rows
    if r["impressions"] >= 100
    and r["ctr"] < 0.03
]
page_opps.sort(key=lambda r: -r["impressions"])
print(f"\n  {'#':>3s}  {'Page':<65s} | {'Clicks':>6s} | {'Impr':>6s} | {'CTR':>6s} | {'Pos':>5s}")
print("  " + "-" * 100)
for i, row in enumerate(page_opps[:20], 1):
    page = row["keys"][0].replace("https://naturesseed.com", "")[:65]
    print(f"  {i:>3d}  {page:<65s} | {int(row['clicks']):>6,} | {int(row['impressions']):>6,} | {row['ctr']*100:>5.1f}% | {row['position']:>5.1f}")

# ═══════════════════════════════════════════════════════════════
# 11. QUERY + PAGE COMBO — Find which pages rank for which queries
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ 11. QUERY CANNIBALIZATION CHECK ━━━")
print("  (Queries where 2+ pages compete — top 15 by impressions)")
qp = query_sc(start_30, end_date, ["query", "page"], 25000)
qp_rows = qp.get("rows", [])

query_pages = defaultdict(list)
for row in qp_rows:
    query_pages[row["keys"][0]].append({
        "page": row["keys"][1],
        "clicks": row["clicks"],
        "impressions": row["impressions"],
        "position": row["position"],
    })

cannibalized = {q: pages for q, pages in query_pages.items() if len(pages) >= 2}
# Sort by total impressions
cann_sorted = sorted(cannibalized.items(), key=lambda x: -sum(p["impressions"] for p in x[1]))

for q, pages in cann_sorted[:15]:
    total_impr = sum(p["impressions"] for p in pages)
    print(f"\n  Query: \"{q}\" ({total_impr:,} impressions, {len(pages)} pages)")
    for p in sorted(pages, key=lambda x: -x["impressions"])[:4]:
        page = p["page"].replace("https://naturesseed.com", "")[:70]
        print(f"    {page:<70s} | clicks: {int(p['clicks']):>4} | impr: {int(p['impressions']):>5} | pos: {p['position']:.1f}")

# ═══════════════════════════════════════════════════════════════
# SAVE RAW DATA
# ═══════════════════════════════════════════════════════════════
data_dir = Path(__file__).parent / "data"
data_dir.mkdir(exist_ok=True)

report = {
    "generated": datetime.now().isoformat(),
    "date_range_30d": {"start": str(start_30), "end": str(end_date)},
    "date_range_90d": {"start": str(start_90), "end": str(end_date)},
    "overall_current": {"clicks": cc, "impressions": ci, "ctr": cctr, "avg_position": cpos},
    "overall_previous": {"clicks": pc, "impressions": pi, "ctr": pctr, "avg_position": ppos},
    "quick_wins_count": len(quick_wins),
    "striking_distance_count": len(striking),
    "cannibalized_queries": len(cannibalized),
    "branded_pct": branded_clicks / total_c * 100 if total_c else 0,
}

with open(data_dir / "health_check.json", "w") as f:
    json.dump(report, f, indent=2)

print(f"\n\n  Report saved to {data_dir / 'health_check.json'}")
print("\n" + "=" * 70)
print("  HEALTH CHECK COMPLETE")
print("=" * 70)
