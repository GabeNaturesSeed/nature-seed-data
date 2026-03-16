#!/usr/bin/env python3
"""
Generate actionable URL fix lists from health check results.
Outputs:
  1. FINAL_url_redirect_fixes.csv
  2. FINAL_url_404_fixes.csv
  3. FINAL_merchant_feed_url_fixes.csv
  4. FINAL_url_health_summary.md
"""

import csv
import os
from collections import defaultdict

BASE_DIR = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/implementation"
DATA_DIR = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/data"

HEALTH_CHECK_FILE = os.path.join(BASE_DIR, "url_health_check.csv")
PROBLEMS_FILE = os.path.join(BASE_DIR, "url_problems.csv")
AD_COPY_FILE = os.path.join(DATA_DIR, "Ad_Copy_Perf.csv")

# ── Step 1: Load Ad Copy data to map URLs → ad details ──────────────────
print("Loading ad copy performance data...")
ad_copy_rows = []
with open(AD_COPY_FILE, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        ad_copy_rows.append(row)

print(f"  Loaded {len(ad_copy_rows)} ad copy rows")

# Build lookup: final_url → list of ad records
url_to_ads = defaultdict(list)
for row in ad_copy_rows:
    url = row.get("Final URL", "").strip()
    if url:
        url_to_ads[url].append(row)

# ── Step 2: Load full health check data ──────────────────────────────────
print("Loading URL health check data...")
health_rows = []
with open(HEALTH_CHECK_FILE, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        health_rows.append(row)

print(f"  Loaded {len(health_rows)} health check rows")

# ── Step 3: Load problems data (has spend/clicks/campaigns pre-joined) ──
print("Loading URL problems data...")
problem_rows = []
with open(PROBLEMS_FILE, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        problem_rows.append(row)

print(f"  Loaded {len(problem_rows)} problem rows")

# ── Helper: parse spend ──────────────────────────────────────────────────
def parse_spend(val):
    if not val or val.strip() == "":
        return 0.0
    try:
        return float(val.replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return 0.0

def parse_clicks(val):
    if not val or val.strip() == "":
        return 0
    try:
        return int(float(val.replace(",", "").strip()))
    except (ValueError, TypeError):
        return 0

# ── Helper: infer correct URL for 404s ───────────────────────────────────
# The pattern is: www.naturesseed.com/{product-slug} → 404
# Correct URL should be naturesseed.com/products/{category}/{product-slug}/
# We also have the final_url from the redirect which shows 301 → naturesseed.com/{slug}/
# which then 404s.

# Known category mappings from working URLs
CATEGORY_KEYWORDS = {
    "grass-seed": [
        "fescue", "bluegrass", "ryegrass", "bermuda", "bahia", "zoysia", "buffalo",
        "kentucky", "lawn", "turf", "sod", "tall-fescue", "fine-fescue", "chewings",
        "centipede", "grass-seed", "grass", "bent", "orchard", "timothy",
        "northeast", "southeast", "midwest", "northwest", "southwest",
        "shade", "sun", "drought", "pet", "kid", "triblade", "blue-ribbon",
        "melic", "brome", "big-bluegrass", "canada-bluegrass", "creeping-red",
        "hard-fescue", "sheep-fescue", "idaho-fescue", "arizona-fescue",
        "blue-wildrye", "bottlebrush", "squirreltail", "alkali-sacaton",
        "alkali-barley", "barley", "wheatgrass", "switchgrass", "indian-grass",
        "sideoats-grama", "blue-grama", "bluestem", "sand-dropseed", "california-melic",
        "coast-range-melic", "california-brome", "california-barley",
        "blando-brome", "common-bermuda"
    ],
    "pasture-seed": [
        "pasture", "forage", "horse", "cattle", "goat", "sheep", "poultry",
        "chicken", "pig", "alpaca", "llama", "deer", "elk", "food-plot",
        "big-game", "dairy", "cow", "beef", "tortoise", "rabbit",
        "cattle-spinach", "cereal-rye", "cicer-milkvetch", "birdsfoot-trefoil"
    ],
    "clover-seed": [
        "clover", "microclover", "dutch-clover", "crimson-clover", "alsike",
        "white-clover", "red-clover", "creek-clover"
    ],
    "wildflower-seed": [
        "wildflower", "poppy", "daisy", "lupine", "sunflower", "columbine",
        "coneflower", "black-eyed-susan", "blanket-flower", "milkweed",
        "butterfly", "bee", "pollinator", "baby-blue", "baby-s-breath",
        "bachelor-button", "snapdragon", "bluebell", "buckwheat", "sage",
        "sagebrush", "goldfields", "gilia", "balsamroot", "penstemon",
        "globe", "tarweed", "gumweed", "goldenbush", "verbena", "vervain",
        "goldenrod", "chinese-houses", "phacelia", "yucca", "flax",
        "chaparral", "habitat", "coastal", "erosion-control", "bioswale",
        "native", "annual", "perennial-wildflower"
    ],
    "cover-crop": [
        "cover-crop", "buckwheat-cover", "rye-cover"
    ],
    "planting-aids": [
        "fertilizer", "mycorrhizal", "inoculant", "mulch"
    ]
}

def infer_replacement_url(broken_url):
    """Try to infer what the correct URL should be for a 404."""
    # Extract the slug from the URL
    slug = broken_url.rstrip("/").split("/")[-1]

    # Remove query params
    if "?" in slug:
        slug = slug.split("?")[0]

    # Special cases: catalogsearch URLs
    if "catalogsearch" in broken_url:
        return "MANUAL REVIEW NEEDED - search URL no longer valid"

    # Check for category keyword matches
    slug_lower = slug.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in slug_lower:
                return f"https://naturesseed.com/products/{category}/{slug}/"

    # Wildflower mix patterns
    if "wildflower-mix" in slug_lower or "mix" in slug_lower and any(w in slug_lower for w in ["pollinator", "butterfly", "bee", "native"]):
        return f"https://naturesseed.com/products/wildflower-seed/{slug}/"

    # Default: can't determine
    return "MANUAL REVIEW NEEDED"


# ══════════════════════════════════════════════════════════════════════════
# OUTPUT 1: FINAL_url_redirect_fixes.csv
# ══════════════════════════════════════════════════════════════════════════
print("\n--- Generating FINAL_url_redirect_fixes.csv ---")

redirect_fixes = []

for row in problem_rows:
    is_redirect = row.get("is_redirect", "").strip().lower() == "true"
    is_error = row.get("is_error", "").strip().lower() == "true"
    source = row.get("source", "").strip()

    # Only ad_copy redirects (not merchant feed -- those go in file 3)
    if not is_redirect or is_error:
        continue
    if source != "ad_copy":
        continue

    spend = parse_spend(row.get("total_historical_spend", ""))
    if spend <= 10:
        continue

    current_url = row.get("url", "")
    final_url = row.get("final_url", "")
    campaigns = row.get("associated_campaigns", "")
    clicks = parse_clicks(row.get("total_historical_clicks", ""))

    # Find associated ad IDs from ad copy data
    ad_ids = []
    for ad in url_to_ads.get(current_url, []):
        ad_ids.append(ad.get("Ad ID", ""))
    ad_id_str = "; ".join(ad_ids) if ad_ids else "Check in Google Ads"

    redirect_fixes.append({
        "current_ad_url": current_url,
        "redirects_to": final_url,
        "campaign_name": campaigns,
        "ad_id": ad_id_str,
        "historical_spend": f"{spend:.2f}",
        "historical_clicks": clicks,
        "action_needed": f"Update ad final URL to: {final_url}"
    })

# Sort by spend descending
redirect_fixes.sort(key=lambda x: float(x["historical_spend"]), reverse=True)

redirect_file = os.path.join(BASE_DIR, "FINAL_url_redirect_fixes.csv")
with open(redirect_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "current_ad_url", "redirects_to", "campaign_name", "ad_id",
        "historical_spend", "historical_clicks", "action_needed"
    ])
    writer.writeheader()
    writer.writerows(redirect_fixes)

print(f"  Wrote {len(redirect_fixes)} redirect fixes")
total_redirect_spend = sum(float(r["historical_spend"]) for r in redirect_fixes)
print(f"  Total spend on redirecting URLs: ${total_redirect_spend:,.2f}")


# ══════════════════════════════════════════════════════════════════════════
# OUTPUT 2: FINAL_url_404_fixes.csv
# ══════════════════════════════════════════════════════════════════════════
print("\n--- Generating FINAL_url_404_fixes.csv ---")

error_404_fixes = []

for row in problem_rows:
    is_error = row.get("is_error", "").strip().lower() == "true"
    http_status = row.get("http_status", "").strip()
    source = row.get("source", "").strip()

    if source != "ad_copy":
        continue

    # Include 404s and connection errors
    if http_status not in ("404", "CONN_ERROR", "TIMEOUT"):
        continue

    current_url = row.get("url", "")
    campaigns = row.get("associated_campaigns", "")
    spend = parse_spend(row.get("total_historical_spend", ""))
    clicks = parse_clicks(row.get("total_historical_clicks", ""))

    # Find ad status and ad IDs
    ad_ids = []
    ad_statuses = set()
    for ad in url_to_ads.get(current_url, []):
        ad_ids.append(ad.get("Ad ID", ""))
        ad_statuses.add(ad.get("Ad Status", "UNKNOWN"))

    ad_id_str = "; ".join(ad_ids) if ad_ids else "Check in Google Ads"
    ad_status_str = "; ".join(ad_statuses) if ad_statuses else "UNKNOWN"

    suggested = infer_replacement_url(current_url)

    error_404_fixes.append({
        "broken_url": current_url,
        "campaign_name": campaigns,
        "ad_id": ad_id_str,
        "ad_status": ad_status_str,
        "historical_spend": f"{spend:.2f}",
        "historical_clicks": clicks,
        "suggested_replacement": suggested
    })

# Sort by spend descending
error_404_fixes.sort(key=lambda x: float(x["historical_spend"]), reverse=True)

error_file = os.path.join(BASE_DIR, "FINAL_url_404_fixes.csv")
with open(error_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "broken_url", "campaign_name", "ad_id", "ad_status",
        "historical_spend", "historical_clicks", "suggested_replacement"
    ])
    writer.writeheader()
    writer.writerows(error_404_fixes)

print(f"  Wrote {len(error_404_fixes)} 404/error fixes")
total_404_spend = sum(float(r["historical_spend"]) for r in error_404_fixes)
total_404_with_spend = len([r for r in error_404_fixes if float(r["historical_spend"]) > 0])
print(f"  Total spend on 404 URLs: ${total_404_spend:,.2f}")
print(f"  URLs with >$0 spend: {total_404_with_spend}")


# ══════════════════════════════════════════════════════════════════════════
# OUTPUT 3: FINAL_merchant_feed_url_fixes.csv
# ══════════════════════════════════════════════════════════════════════════
print("\n--- Generating FINAL_merchant_feed_url_fixes.csv ---")

merchant_fixes = []

for row in problem_rows:
    source = row.get("source", "").strip()
    if source != "merchant_feed":
        continue

    current_url = row.get("url", "")
    is_redirect = row.get("is_redirect", "").strip().lower() == "true"
    is_error = row.get("is_error", "").strip().lower() == "true"
    http_status = row.get("http_status", "").strip()
    final_url = row.get("final_url", "")
    notes = row.get("notes", "")

    # Determine issue type
    if is_error:
        issue = f"Error: {http_status} - {notes}"
    elif is_redirect:
        issue = f"Redirects ({row.get('redirect_type', '301')})"
    else:
        continue  # Skip if neither error nor redirect

    # Extract product_id from URL (variation_id param or slug)
    product_id = ""
    if "variation_id=" in current_url:
        import re
        vid_match = re.search(r'variation_id=(\d+)', current_url)
        if vid_match:
            product_id = f"variation_{vid_match.group(1)}"
    else:
        # Use the slug
        slug = current_url.rstrip("/").split("/")[-1]
        if "?" in slug:
            slug = slug.split("?")[0]
        product_id = slug

    # Suggested fix
    if is_redirect and final_url:
        suggested_fix = f"Update feed URL to: {final_url}"
    elif is_error:
        suggested_fix = "Investigate server error; may need to remove from feed or fix server timeout"
    else:
        suggested_fix = "MANUAL REVIEW NEEDED"

    merchant_fixes.append({
        "product_id": product_id,
        "current_url": current_url,
        "issue": issue,
        "redirects_to": final_url if is_redirect else "",
        "suggested_fix": suggested_fix
    })

merchant_file = os.path.join(BASE_DIR, "FINAL_merchant_feed_url_fixes.csv")
with open(merchant_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "product_id", "current_url", "issue", "redirects_to", "suggested_fix"
    ])
    writer.writeheader()
    writer.writerows(merchant_fixes)

print(f"  Wrote {len(merchant_fixes)} merchant feed fixes")


# ══════════════════════════════════════════════════════════════════════════
# OUTPUT 4: FINAL_url_health_summary.md
# ══════════════════════════════════════════════════════════════════════════
print("\n--- Generating FINAL_url_health_summary.md ---")

# Compute stats from full health check
total_urls = len(health_rows)
ok_count = 0
redirect_count = 0
error_count = 0
error_404_count = 0
error_conn_count = 0
error_timeout_count = 0

# Source breakdown
ad_copy_total = 0
ad_copy_redirects = 0
ad_copy_errors = 0
merchant_total = 0
merchant_redirects = 0
merchant_errors = 0
base_url_total = 0
base_url_redirects = 0
base_url_errors = 0

for row in health_rows:
    source = row.get("source", "").strip()
    is_redirect = row.get("is_redirect", "").strip().lower() == "true"
    is_error = row.get("is_error", "").strip().lower() == "true"
    http_status = row.get("http_status", "").strip()

    if source == "ad_copy":
        ad_copy_total += 1
        if is_redirect and not is_error:
            ad_copy_redirects += 1
        if is_error:
            ad_copy_errors += 1
    elif source == "merchant_feed":
        merchant_total += 1
        if is_redirect and not is_error:
            merchant_redirects += 1
        if is_error:
            merchant_errors += 1
    elif source == "base_url_check":
        base_url_total += 1
        if is_redirect and not is_error:
            base_url_redirects += 1
        if is_error:
            base_url_errors += 1

    if is_error:
        error_count += 1
        if http_status == "404":
            error_404_count += 1
        elif http_status == "CONN_ERROR":
            error_conn_count += 1
        elif http_status == "TIMEOUT":
            error_timeout_count += 1
    elif is_redirect:
        redirect_count += 1
    else:
        ok_count += 1

# Gather redirect patterns from ad_copy problems
redirect_patterns = defaultdict(int)
for row in problem_rows:
    source = row.get("source", "").strip()
    is_redirect = row.get("is_redirect", "").strip().lower() == "true"
    is_error = row.get("is_error", "").strip().lower() == "true"
    if source == "ad_copy" and is_redirect and not is_error:
        url = row.get("url", "")
        final = row.get("final_url", "")
        # Identify pattern
        if "/product/" in url and "/products/" in final:
            redirect_patterns["/product/{slug} --> /products/{category}/{slug}/"] += 1
        elif url.startswith("https://www.naturesseed.com") and "naturesseed.com" in final:
            if "404" not in row.get("http_status", ""):
                redirect_patterns["www.naturesseed.com/{slug} --> naturesseed.com/{slug}/ (www redirect)"] += 1
        elif "/grass-seed/" in url and "/products/grass-seed/" in final:
            redirect_patterns["/grass-seed/{path} --> /products/grass-seed/{slug}/"] += 1
        elif "/pasture-seed/" in url and "/products/pasture-seed/" in final:
            redirect_patterns["/pasture-seed/{path} --> /products/pasture-seed/{slug}/"] += 1
        elif "/wildflower-seed/" in url and "/products/wildflower-seed/" in final:
            redirect_patterns["/wildflower-seed/ --> /products/wildflower-seed/"] += 1
        elif "/products/grass-seed" in url and "/products/grass-seed/" in final:
            redirect_patterns["Missing trailing slash: /products/grass-seed --> /products/grass-seed/"] += 1
        elif "/sale/" in url:
            redirect_patterns["/sale/ --> / (302 temporary redirect, sale page gone)"] += 1
        else:
            redirect_patterns["Other redirect"] += 1

# Campaign impact analysis
campaign_spend_impact = defaultdict(lambda: {"redirect_spend": 0, "error_spend": 0, "redirect_count": 0, "error_count": 0})
for row in problem_rows:
    source = row.get("source", "").strip()
    if source != "ad_copy":
        continue
    campaigns_str = row.get("associated_campaigns", "")
    spend = parse_spend(row.get("total_historical_spend", ""))
    is_error = row.get("is_error", "").strip().lower() == "true"
    is_redirect = row.get("is_redirect", "").strip().lower() == "true"

    if campaigns_str:
        for camp in campaigns_str.split("; "):
            camp = camp.strip()
            if is_error:
                campaign_spend_impact[camp]["error_spend"] += spend
                campaign_spend_impact[camp]["error_count"] += 1
            elif is_redirect:
                campaign_spend_impact[camp]["redirect_spend"] += spend
                campaign_spend_impact[camp]["redirect_count"] += 1

# Sort campaigns by total impact
campaign_impact_list = []
for camp, data in campaign_spend_impact.items():
    total = data["redirect_spend"] + data["error_spend"]
    campaign_impact_list.append((camp, data, total))
campaign_impact_list.sort(key=lambda x: x[2], reverse=True)

# Top redirect fixes (for summary)
top_redirects = redirect_fixes[:15]
top_404s = [r for r in error_404_fixes if float(r["historical_spend"]) > 0][:15]

# ── Write summary ────────────────────────────────────────────────────────
summary_file = os.path.join(BASE_DIR, "FINAL_url_health_summary.md")
with open(summary_file, "w", encoding="utf-8") as f:
    f.write("# URL Health Check Summary -- Nature's Seed Google Ads\n\n")
    f.write(f"**Date:** 2026-03-05\n\n")

    # ── Overall stats ────────────────────────────────────────────────────
    f.write("## Overall Health Stats\n\n")
    f.write(f"| Metric | Count | % of Total |\n")
    f.write(f"|--------|------:|----------:|\n")
    f.write(f"| Total URLs Checked | {total_urls} | 100% |\n")
    f.write(f"| OK (200, no redirect) | {ok_count} | {ok_count/total_urls*100:.1f}% |\n")
    f.write(f"| Redirects (301/302) | {redirect_count} | {redirect_count/total_urls*100:.1f}% |\n")
    f.write(f"| Errors (404/timeout/conn) | {error_count} | {error_count/total_urls*100:.1f}% |\n")
    f.write(f"\n")

    f.write("### Error Breakdown\n\n")
    f.write(f"| Error Type | Count |\n")
    f.write(f"|-----------|------:|\n")
    f.write(f"| HTTP 404 (Not Found) | {error_404_count} |\n")
    f.write(f"| Connection Error | {error_conn_count} |\n")
    f.write(f"| Timeout | {error_timeout_count} |\n")
    f.write(f"\n")

    f.write("### By Source\n\n")
    f.write(f"| Source | Total | OK | Redirects | Errors |\n")
    f.write(f"|--------|------:|---:|----------:|-------:|\n")
    ad_ok = ad_copy_total - ad_copy_redirects - ad_copy_errors
    merch_ok = merchant_total - merchant_redirects - merchant_errors
    base_ok = base_url_total - base_url_redirects - base_url_errors
    f.write(f"| Ad Copy URLs | {ad_copy_total} | {ad_ok} | {ad_copy_redirects} | {ad_copy_errors} |\n")
    f.write(f"| Merchant Feed URLs | {merchant_total} | {merch_ok} | {merchant_redirects} | {merchant_errors} |\n")
    f.write(f"| Base URL Checks | {base_url_total} | {base_ok} | {base_url_redirects} | {base_url_errors} |\n")
    f.write(f"\n")

    # ── Financial impact ─────────────────────────────────────────────────
    f.write("## Financial Impact\n\n")
    f.write(f"| Issue | URLs Affected | Historical Spend |\n")
    f.write(f"|-------|-------------:|-----------------:|\n")
    f.write(f"| Redirecting ad URLs (>$10 spend) | {len(redirect_fixes)} | ${total_redirect_spend:,.2f} |\n")
    f.write(f"| Broken/404 ad URLs (any spend) | {total_404_with_spend} | ${total_404_spend:,.2f} |\n")
    f.write(f"| Broken/404 ad URLs (all) | {len(error_404_fixes)} | ${total_404_spend:,.2f} |\n")
    f.write(f"| Merchant feed issues | {len(merchant_fixes)} | N/A (feed) |\n")
    f.write(f"| **Total wasted/degraded spend** | **{len(redirect_fixes) + total_404_with_spend}** | **${total_redirect_spend + total_404_spend:,.2f}** |\n")
    f.write(f"\n")

    f.write("### Why This Matters\n\n")
    f.write("- **301 redirects** add latency (200-500ms per hop), hurt Quality Score, and waste crawl budget. ")
    f.write("Google Ads charges for the click before the redirect completes -- if users bounce due to slow loads, that spend is wasted.\n")
    f.write("- **404 errors** mean ads are sending paid traffic to dead pages. Any active ads pointing to 404s are burning budget with zero conversion potential.\n")
    f.write("- **Merchant feed redirects** cause Google Shopping disapprovals and reduced visibility.\n\n")

    # ── Priority fixes by $ impact ───────────────────────────────────────
    f.write("## Priority Fixes by Dollar Impact\n\n")
    f.write("### Top 15 Redirect Fixes (by historical spend)\n\n")
    f.write("| # | Current URL | Redirects To | Spend | Clicks |\n")
    f.write("|---|-----------|-------------|------:|-------:|\n")
    for i, r in enumerate(top_redirects, 1):
        curr = r["current_ad_url"]
        dest = r["redirects_to"]
        # Truncate for readability
        if len(curr) > 60:
            curr_display = curr[:57] + "..."
        else:
            curr_display = curr
        if len(dest) > 60:
            dest_display = dest[:57] + "..."
        else:
            dest_display = dest
        f.write(f"| {i} | `{curr_display}` | `{dest_display}` | ${float(r['historical_spend']):,.2f} | {r['historical_clicks']} |\n")
    f.write(f"\n")

    f.write("### Top 15 Broken URL Fixes (404s with spend)\n\n")
    f.write("| # | Broken URL | Campaign | Spend | Clicks |\n")
    f.write("|---|----------|---------|------:|-------:|\n")
    for i, r in enumerate(top_404s, 1):
        url_display = r["broken_url"]
        if len(url_display) > 50:
            url_display = url_display[:47] + "..."
        camp = r["campaign_name"]
        if len(camp) > 30:
            camp = camp[:27] + "..."
        f.write(f"| {i} | `{url_display}` | {camp} | ${float(r['historical_spend']):,.2f} | {r['historical_clicks']} |\n")
    f.write(f"\n")

    # ── Redirect mapping table ───────────────────────────────────────────
    f.write("## Redirect Pattern Mapping\n\n")
    f.write("These are the systematic URL structure changes that caused redirects across the site:\n\n")
    f.write("| Pattern | Count |\n")
    f.write("|---------|------:|\n")
    for pattern, count in sorted(redirect_patterns.items(), key=lambda x: x[1], reverse=True):
        f.write(f"| {pattern} | {count} |\n")
    f.write(f"\n")

    f.write("### Key Structural Changes\n\n")
    f.write("The site underwent a major URL restructuring:\n\n")
    f.write("1. **`/product/{slug}` changed to `/products/{category}/{slug}/`** -- Old WooCommerce default product URLs now use category-based paths.\n")
    f.write("2. **`/grass-seed/{subcategory}/{slug}` changed to `/products/grass-seed/{slug}/`** -- Flattened subcategory structure.\n")
    f.write("3. **`/pasture-seed/{animal}/` changed to `/products/pasture-seed/{animal}-seed/`** -- Added `-seed` suffix and moved under `/products/`.\n")
    f.write("4. **`/wildflower-seed/` changed to `/products/wildflower-seed/`** -- Added `/products/` prefix.\n")
    f.write("5. **`www.naturesseed.com` redirects to `naturesseed.com`** -- www subdomain redirect (minor, but adds latency).\n")
    f.write("6. **`/products/grass-seeds/` changed to `/products/grass-seed/`** -- Pluralization fix (seeds to seed).\n")
    f.write("7. **`/products/pasture-seeds/` changed to `/products/pasture-seed/`** -- Same pluralization fix.\n")
    f.write("8. **`/sale/` redirects to `/`** -- Sale page removed, 302 temp redirect to homepage.\n\n")

    f.write("### 404 URL Pattern (US | Search | Product Ads campaign)\n\n")
    f.write("The vast majority of 404s come from the **US | Search | Product Ads** campaign which uses the URL pattern:\n")
    f.write("`www.naturesseed.com/{product-slug}` (e.g., `www.naturesseed.com/big-bluestem`)\n\n")
    f.write("These URLs redirect `www` to non-www, but then land on `naturesseed.com/{slug}/` which returns 404.\n")
    f.write("The correct URLs should be `naturesseed.com/products/{category}/{slug}/`.\n\n")
    f.write("**Recommended action:** Pause or rebuild the US | Search | Product Ads campaign with corrected URLs. ")
    f.write("Most of these ads have $0 or minimal spend, suggesting they may already be paused or have low impressions.\n\n")

    # ── Campaigns needing attention ──────────────────────────────────────
    f.write("## Campaigns Needing Attention\n\n")
    f.write("| Campaign | Redirect Spend | Redirect URLs | Error Spend | Error URLs | Total Impact |\n")
    f.write("|----------|---------------:|--------------:|------------:|-----------:|-------------:|\n")
    for camp, data, total in campaign_impact_list[:20]:
        if total < 1:
            continue
        f.write(f"| {camp} | ${data['redirect_spend']:,.2f} | {data['redirect_count']} | ${data['error_spend']:,.2f} | {data['error_count']} | ${total:,.2f} |\n")
    f.write(f"\n")

    # ── Action plan ──────────────────────────────────────────────────────
    f.write("## Recommended Action Plan\n\n")
    f.write("### Immediate (This Week)\n\n")
    f.write("1. **Update top 5 redirecting ad URLs** -- These represent the highest spend and are easy fixes. ")
    f.write("Just update the Final URL in each ad to the destination URL (see `FINAL_url_redirect_fixes.csv`).\n")
    f.write("2. **Pause any active ads pointing to 404 URLs** -- Check `FINAL_url_404_fixes.csv` for ads with recent spend.\n")
    f.write("3. **Fix merchant feed URLs** -- Update product URLs in feed to use the new `/products/{category}/{slug}/` structure.\n\n")

    f.write("### Short-Term (This Month)\n\n")
    f.write("4. **Update ALL redirecting ad URLs** -- Work through the full `FINAL_url_redirect_fixes.csv` list.\n")
    f.write("5. **Rebuild US | Search | Product Ads campaign** -- The old `www.naturesseed.com/{slug}` URL pattern is completely broken. ")
    f.write("Rebuild with the correct `/products/{category}/{slug}/` URLs.\n")
    f.write("6. **Update `www.` prefixed URLs** -- All ads using `www.naturesseed.com` should use `naturesseed.com` instead.\n\n")

    f.write("### Ongoing\n\n")
    f.write("7. **Set up URL monitoring** -- Run this health check monthly to catch new redirects before they accumulate.\n")
    f.write("8. **Update ad templates** -- Ensure all new ads use the current URL structure.\n")
    f.write("9. **Merchant feed automation** -- Ensure the WooCommerce-to-Google feed uses canonical URLs.\n\n")

    # ── File reference ───────────────────────────────────────────────────
    f.write("## Output File Reference\n\n")
    f.write("| File | Description | Records |\n")
    f.write("|------|------------|--------:|\n")
    f.write(f"| `FINAL_url_redirect_fixes.csv` | Ad URLs that 301-redirect, sorted by spend | {len(redirect_fixes)} |\n")
    f.write(f"| `FINAL_url_404_fixes.csv` | Ad URLs returning 404, with suggested replacements | {len(error_404_fixes)} |\n")
    f.write(f"| `FINAL_merchant_feed_url_fixes.csv` | Merchant feed URLs with issues | {len(merchant_fixes)} |\n")
    f.write(f"| `FINAL_url_health_summary.md` | This summary document | -- |\n")

print(f"  Wrote summary to {summary_file}")
print("\n=== DONE ===")
print(f"All files written to: {BASE_DIR}")
