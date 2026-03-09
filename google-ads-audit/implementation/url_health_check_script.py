#!/usr/bin/env python3
"""
Comprehensive URL Health Check for Nature's Seed Google Ads & Merchant Feed URLs.
Checks all unique URLs from Ad Copy and Merchant Feed for HTTP status, redirects, errors.
"""

import csv
import time
import ssl
import sys
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from collections import defaultdict, Counter
from datetime import datetime

# Try to use requests library, fall back to urllib
try:
    import requests
    USE_REQUESTS = True
    print("Using 'requests' library for HTTP checks.")
except ImportError:
    USE_REQUESTS = False
    print("Using 'urllib' for HTTP checks (requests not available).")

# ─── Configuration ───────────────────────────────────────────────────────────
AD_COPY_CSV = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/data/Ad_Copy_Perf.csv"
MERCHANT_FEED_CSV = "/Users/gabegimenes-silva/Downloads/Google Merchant Center Feed - Sheet1 (11).csv"
OUTPUT_DIR = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/implementation"

TIMEOUT = 10  # seconds
DELAY = 0.5   # seconds between requests
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ─── Step 1: Extract URLs from both sources ──────────────────────────────────
print("\n" + "="*80)
print("STEP 1: Extracting URLs from data sources")
print("="*80)

ad_copy_urls = {}       # url -> list of {campaign, spend, clicks}
merchant_feed_urls = set()

# --- Ad Copy ---
with open(AD_COPY_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        url = row.get("Final URL", "").strip()
        if not url:
            continue
        campaign = row.get("Campaign Name", "")
        try:
            spend = float(row.get("Cost ($)", "0").replace(",", ""))
        except (ValueError, TypeError):
            spend = 0.0
        try:
            clicks = int(float(row.get("Clicks", "0").replace(",", "")))
        except (ValueError, TypeError):
            clicks = 0

        if url not in ad_copy_urls:
            ad_copy_urls[url] = []
        ad_copy_urls[url].append({
            "campaign": campaign,
            "spend": spend,
            "clicks": clicks
        })

print(f"  Ad Copy: {len(ad_copy_urls)} unique Final URLs extracted")

# --- Merchant Feed ---
with open(MERCHANT_FEED_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        url = row.get("link", "").strip()
        if url:
            merchant_feed_urls.add(url)

print(f"  Merchant Feed: {len(merchant_feed_urls)} unique link URLs extracted")

# ─── Step 2: Deduplicate and categorize ──────────────────────────────────────
print("\n" + "="*80)
print("STEP 2: Deduplicating URLs and identifying base URLs")
print("="*80)

all_urls = {}  # url -> source ("ad_copy", "merchant_feed", "both")

for url in ad_copy_urls:
    if url in merchant_feed_urls:
        all_urls[url] = "both"
    else:
        all_urls[url] = "ad_copy"

for url in merchant_feed_urls:
    if url not in all_urls:
        all_urls[url] = "merchant_feed"

# Also extract base URLs (without query params) for URLs that have them
base_urls_to_check = set()
for url in all_urls:
    parsed = urlparse(url)
    if parsed.query or parsed.fragment:
        base_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
        if base_url and base_url not in all_urls:
            base_urls_to_check.add(base_url)

# Add base URLs with source "base_url_check"
for base_url in base_urls_to_check:
    all_urls[base_url] = "base_url_check"

total_urls = len(all_urls)
print(f"  Total unique URLs to check: {total_urls}")
print(f"    - Ad Copy only: {sum(1 for v in all_urls.values() if v == 'ad_copy')}")
print(f"    - Merchant Feed only: {sum(1 for v in all_urls.values() if v == 'merchant_feed')}")
print(f"    - Both sources: {sum(1 for v in all_urls.values() if v == 'both')}")
print(f"    - Base URL checks: {sum(1 for v in all_urls.values() if v == 'base_url_check')}")

# ─── Step 3: Check each URL ─────────────────────────────────────────────────
print("\n" + "="*80)
print("STEP 3: Checking URLs (this will take a while...)")
print("="*80)

results = []
status_counter = Counter()
error_types = Counter()

def check_url_requests(url):
    """Check URL using requests library."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
            allow_redirects=True
        )

        # Build redirect chain
        redirect_chain = []
        if resp.history:
            for r in resp.history:
                redirect_chain.append({
                    "url": r.url,
                    "status": r.status_code
                })

        final_url = resp.url
        status_code = resp.status_code
        is_redirect = len(resp.history) > 0
        redirect_type = ""
        if is_redirect and resp.history:
            redirect_type = str(resp.history[0].status_code)

        is_error = status_code >= 400
        notes = ""
        if is_redirect:
            chain_str = " -> ".join([f"{r['status']}:{r['url']}" for r in redirect_chain])
            notes = f"Redirect chain: {chain_str} -> {status_code}:{final_url}"
        if is_error:
            notes = f"HTTP {status_code} error"

        return {
            "status_code": status_code,
            "final_url": final_url,
            "is_redirect": is_redirect,
            "redirect_type": redirect_type,
            "is_error": is_error,
            "notes": notes,
            "redirect_chain": redirect_chain
        }

    except requests.exceptions.SSLError as e:
        return {
            "status_code": "SSL_ERROR",
            "final_url": "",
            "is_redirect": False,
            "redirect_type": "",
            "is_error": True,
            "notes": f"SSL Error: {str(e)[:200]}",
            "redirect_chain": []
        }
    except requests.exceptions.Timeout:
        return {
            "status_code": "TIMEOUT",
            "final_url": "",
            "is_redirect": False,
            "redirect_type": "",
            "is_error": True,
            "notes": f"Timeout after {TIMEOUT}s",
            "redirect_chain": []
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "status_code": "CONN_ERROR",
            "final_url": "",
            "is_redirect": False,
            "redirect_type": "",
            "is_error": True,
            "notes": f"Connection Error: {str(e)[:200]}",
            "redirect_chain": []
        }
    except Exception as e:
        return {
            "status_code": "ERROR",
            "final_url": "",
            "is_redirect": False,
            "redirect_type": "",
            "is_error": True,
            "notes": f"Error: {str(e)[:200]}",
            "redirect_chain": []
        }


def check_url_urllib(url):
    """Check URL using urllib (fallback)."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        ctx = ssl.create_default_context()

        resp = urlopen(req, timeout=TIMEOUT, context=ctx)
        status_code = resp.getcode()
        final_url = resp.geturl()
        is_redirect = final_url != url
        redirect_type = "301/302" if is_redirect else ""
        is_error = status_code >= 400
        notes = ""
        if is_redirect:
            notes = f"Redirected to: {final_url}"

        return {
            "status_code": status_code,
            "final_url": final_url,
            "is_redirect": is_redirect,
            "redirect_type": redirect_type,
            "is_error": is_error,
            "notes": notes,
            "redirect_chain": []
        }

    except HTTPError as e:
        return {
            "status_code": e.code,
            "final_url": url,
            "is_redirect": False,
            "redirect_type": "",
            "is_error": True,
            "notes": f"HTTP {e.code}: {e.reason}",
            "redirect_chain": []
        }
    except ssl.SSLError as e:
        return {
            "status_code": "SSL_ERROR",
            "final_url": "",
            "is_redirect": False,
            "redirect_type": "",
            "is_error": True,
            "notes": f"SSL Error: {str(e)[:200]}",
            "redirect_chain": []
        }
    except TimeoutError:
        return {
            "status_code": "TIMEOUT",
            "final_url": "",
            "is_redirect": False,
            "redirect_type": "",
            "is_error": True,
            "notes": f"Timeout after {TIMEOUT}s",
            "redirect_chain": []
        }
    except URLError as e:
        if "timed out" in str(e):
            return {
                "status_code": "TIMEOUT",
                "final_url": "",
                "is_redirect": False,
                "redirect_type": "",
                "is_error": True,
                "notes": f"Timeout after {TIMEOUT}s",
                "redirect_chain": []
            }
        return {
            "status_code": "CONN_ERROR",
            "final_url": "",
            "is_redirect": False,
            "redirect_type": "",
            "is_error": True,
            "notes": f"URL Error: {str(e)[:200]}",
            "redirect_chain": []
        }
    except Exception as e:
        return {
            "status_code": "ERROR",
            "final_url": "",
            "is_redirect": False,
            "redirect_type": "",
            "is_error": True,
            "notes": f"Error: {str(e)[:200]}",
            "redirect_chain": []
        }


check_url = check_url_requests if USE_REQUESTS else check_url_urllib

sorted_urls = sorted(all_urls.keys())
start_time = time.time()

for i, url in enumerate(sorted_urls):
    source = all_urls[url]

    # Progress reporting
    if (i + 1) % 25 == 0 or i == 0:
        elapsed = time.time() - start_time
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        remaining = (total_urls - i - 1) / rate if rate > 0 else 0
        print(f"  [{i+1}/{total_urls}] Checking... ({rate:.1f} URLs/sec, ~{remaining:.0f}s remaining)")

    result = check_url(url)

    results.append({
        "url": url,
        "source": source,
        "http_status": result["status_code"],
        "final_url": result["final_url"],
        "is_redirect": result["is_redirect"],
        "redirect_type": result["redirect_type"],
        "is_error": result["is_error"],
        "notes": result["notes"],
        "redirect_chain": result["redirect_chain"]
    })

    # Track stats
    sc = str(result["status_code"])
    status_counter[sc] += 1
    if result["is_error"]:
        error_types[sc] += 1

    # Delay between requests
    time.sleep(DELAY)

elapsed_total = time.time() - start_time
print(f"\n  Done! Checked {total_urls} URLs in {elapsed_total:.1f}s")

# ─── Step 4: Write output files ─────────────────────────────────────────────
print("\n" + "="*80)
print("STEP 4: Writing output files")
print("="*80)

# --- File 1: url_health_check.csv (all URLs) ---
output1 = f"{OUTPUT_DIR}/url_health_check.csv"
with open(output1, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["url", "source", "http_status", "final_url", "is_redirect", "redirect_type", "is_error", "notes"])
    for r in results:
        writer.writerow([
            r["url"],
            r["source"],
            r["http_status"],
            r["final_url"],
            r["is_redirect"],
            r["redirect_type"],
            r["is_error"],
            r["notes"]
        ])
print(f"  Written: {output1} ({len(results)} rows)")

# --- File 2: url_problems.csv (only URLs with issues) ---
output2 = f"{OUTPUT_DIR}/url_problems.csv"
problem_results = []
for r in results:
    sc = str(r["http_status"])
    # A problem is: error status, redirect, timeout, SSL error, connection error
    is_problem = (
        r["is_error"] or
        r["is_redirect"] or
        sc in ("TIMEOUT", "SSL_ERROR", "CONN_ERROR", "ERROR")
    )
    if is_problem:
        # Aggregate campaign data for this URL
        campaigns = []
        total_spend = 0.0
        total_clicks = 0
        if r["url"] in ad_copy_urls:
            for entry in ad_copy_urls[r["url"]]:
                if entry["campaign"] not in campaigns:
                    campaigns.append(entry["campaign"])
                total_spend += entry["spend"]
                total_clicks += entry["clicks"]

        problem_results.append({
            **r,
            "associated_campaigns": "; ".join(campaigns) if campaigns else "",
            "total_historical_spend": f"{total_spend:.2f}" if total_spend > 0 else "",
            "total_historical_clicks": total_clicks if total_clicks > 0 else ""
        })

with open(output2, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "url", "source", "http_status", "final_url", "is_redirect", "redirect_type",
        "is_error", "notes", "associated_campaigns", "total_historical_spend", "total_historical_clicks"
    ])
    for r in problem_results:
        writer.writerow([
            r["url"],
            r["source"],
            r["http_status"],
            r["final_url"],
            r["is_redirect"],
            r["redirect_type"],
            r["is_error"],
            r["notes"],
            r["associated_campaigns"],
            r["total_historical_spend"],
            r["total_historical_clicks"]
        ])
print(f"  Written: {output2} ({len(problem_results)} problem URLs)")

# --- File 3: url_health_summary.txt ---
output3 = f"{OUTPUT_DIR}/url_health_summary.txt"

# Categorize results
status_200 = [r for r in results if str(r["http_status"]) == "200" and not r["is_redirect"]]
status_301 = [r for r in results if r["redirect_type"] == "301"]
status_302 = [r for r in results if r["redirect_type"] == "302"]
status_other_redirect = [r for r in results if r["is_redirect"] and r["redirect_type"] not in ("301", "302", "")]
status_404 = [r for r in results if str(r["http_status"]) == "404"]
status_500 = [r for r in results if str(r["http_status"]).startswith("5")]
status_timeout = [r for r in results if str(r["http_status"]) == "TIMEOUT"]
status_ssl = [r for r in results if str(r["http_status"]) == "SSL_ERROR"]
status_conn = [r for r in results if str(r["http_status"]) == "CONN_ERROR"]
status_other_error = [r for r in results if r["is_error"] and str(r["http_status"]) not in ("404", "TIMEOUT", "SSL_ERROR", "CONN_ERROR", "ERROR") and not str(r["http_status"]).startswith("5")]
redirects_all = [r for r in results if r["is_redirect"]]

# Calculate wasted spend on broken URLs
total_wasted_spend_404 = 0
total_wasted_clicks_404 = 0
for r in status_404:
    if r["url"] in ad_copy_urls:
        for entry in ad_copy_urls[r["url"]]:
            total_wasted_spend_404 += entry["spend"]
            total_wasted_clicks_404 += entry["clicks"]

total_redirect_spend = 0
total_redirect_clicks = 0
for r in redirects_all:
    if r["url"] in ad_copy_urls:
        for entry in ad_copy_urls[r["url"]]:
            total_redirect_spend += entry["spend"]
            total_redirect_clicks += entry["clicks"]

with open(output3, "w", encoding="utf-8") as f:
    f.write("=" * 80 + "\n")
    f.write("URL HEALTH CHECK SUMMARY — Nature's Seed Google Ads & Merchant Feed\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 80 + "\n\n")

    f.write("DATA SOURCES\n")
    f.write("-" * 40 + "\n")
    f.write(f"  Ad Copy Final URLs (unique):    {len(ad_copy_urls)}\n")
    f.write(f"  Merchant Feed link URLs (unique):{len(merchant_feed_urls)}\n")
    f.write(f"  Base URL extras checked:         {len(base_urls_to_check)}\n")
    f.write(f"  Total unique URLs checked:       {total_urls}\n")
    f.write(f"  Time elapsed:                    {elapsed_total:.1f}s\n\n")

    f.write("STATUS BREAKDOWN\n")
    f.write("-" * 40 + "\n")
    f.write(f"  200 OK (clean):                  {len(status_200)}\n")
    f.write(f"  301 Permanent Redirect:          {len(status_301)}\n")
    f.write(f"  302 Temporary Redirect:          {len(status_302)}\n")
    f.write(f"  Other Redirects:                 {len(status_other_redirect)}\n")
    f.write(f"  404 Not Found:                   {len(status_404)}\n")
    f.write(f"  5xx Server Error:                {len(status_500)}\n")
    f.write(f"  Timeout:                         {len(status_timeout)}\n")
    f.write(f"  SSL Error:                       {len(status_ssl)}\n")
    f.write(f"  Connection Error:                {len(status_conn)}\n")
    f.write(f"  Other Errors:                    {len(status_other_error)}\n\n")

    f.write("RAW STATUS CODE COUNTS\n")
    f.write("-" * 40 + "\n")
    for code, count in sorted(status_counter.items(), key=lambda x: -x[1]):
        f.write(f"  {code}: {count}\n")
    f.write("\n")

    f.write("FINANCIAL IMPACT\n")
    f.write("-" * 40 + "\n")
    f.write(f"  Wasted spend on 404 URLs:        ${total_wasted_spend_404:,.2f}\n")
    f.write(f"  Wasted clicks on 404 URLs:       {total_wasted_clicks_404:,}\n")
    f.write(f"  Spend on redirecting URLs:        ${total_redirect_spend:,.2f}\n")
    f.write(f"  Clicks on redirecting URLs:       {total_redirect_clicks:,}\n\n")

    # --- Detail sections ---

    if status_404:
        f.write("=" * 80 + "\n")
        f.write("404 NOT FOUND — CRITICAL (these URLs are broken)\n")
        f.write("=" * 80 + "\n")
        for r in sorted(status_404, key=lambda x: x["url"]):
            f.write(f"\n  URL: {r['url']}\n")
            f.write(f"  Source: {r['source']}\n")
            if r["url"] in ad_copy_urls:
                total_s = sum(e["spend"] for e in ad_copy_urls[r["url"]])
                total_c = sum(e["clicks"] for e in ad_copy_urls[r["url"]])
                campaigns = list(set(e["campaign"] for e in ad_copy_urls[r["url"]]))
                f.write(f"  Campaigns: {'; '.join(campaigns)}\n")
                f.write(f"  Total Spend: ${total_s:,.2f} | Total Clicks: {total_c:,}\n")
        f.write("\n")

    if status_500:
        f.write("=" * 80 + "\n")
        f.write("5xx SERVER ERRORS\n")
        f.write("=" * 80 + "\n")
        for r in sorted(status_500, key=lambda x: x["url"]):
            f.write(f"\n  URL: {r['url']}\n")
            f.write(f"  Status: {r['http_status']}\n")
            f.write(f"  Source: {r['source']}\n")
        f.write("\n")

    if status_timeout:
        f.write("=" * 80 + "\n")
        f.write("TIMEOUTS\n")
        f.write("=" * 80 + "\n")
        for r in sorted(status_timeout, key=lambda x: x["url"]):
            f.write(f"\n  URL: {r['url']}\n")
            f.write(f"  Source: {r['source']}\n")
        f.write("\n")

    if status_ssl:
        f.write("=" * 80 + "\n")
        f.write("SSL ERRORS\n")
        f.write("=" * 80 + "\n")
        for r in sorted(status_ssl, key=lambda x: x["url"]):
            f.write(f"\n  URL: {r['url']}\n")
            f.write(f"  Source: {r['source']}\n")
            f.write(f"  Error: {r['notes']}\n")
        f.write("\n")

    if status_conn:
        f.write("=" * 80 + "\n")
        f.write("CONNECTION ERRORS\n")
        f.write("=" * 80 + "\n")
        for r in sorted(status_conn, key=lambda x: x["url"]):
            f.write(f"\n  URL: {r['url']}\n")
            f.write(f"  Source: {r['source']}\n")
            f.write(f"  Error: {r['notes']}\n")
        f.write("\n")

    # Top redirects by spend
    redirect_with_spend = []
    for r in redirects_all:
        if r["url"] in ad_copy_urls:
            total_s = sum(e["spend"] for e in ad_copy_urls[r["url"]])
            redirect_with_spend.append((r, total_s))
    redirect_with_spend.sort(key=lambda x: -x[1])

    if redirect_with_spend:
        f.write("=" * 80 + "\n")
        f.write("TOP REDIRECTING URLs BY AD SPEND (update ad URLs to final destination)\n")
        f.write("=" * 80 + "\n")
        for r, spend in redirect_with_spend[:30]:
            total_c = sum(e["clicks"] for e in ad_copy_urls[r["url"]])
            campaigns = list(set(e["campaign"] for e in ad_copy_urls[r["url"]]))
            f.write(f"\n  URL: {r['url']}\n")
            f.write(f"  -> Redirects to: {r['final_url']}\n")
            f.write(f"  Redirect type: {r['redirect_type']}\n")
            f.write(f"  Ad Spend: ${spend:,.2f} | Clicks: {total_c:,}\n")
            f.write(f"  Campaigns: {'; '.join(campaigns)}\n")
        f.write("\n")

    # Merchant feed problems
    merchant_problems = [r for r in results if r["source"] in ("merchant_feed", "both") and (r["is_error"] or r["is_redirect"])]
    if merchant_problems:
        f.write("=" * 80 + "\n")
        f.write("MERCHANT FEED URL PROBLEMS (may cause disapprovals)\n")
        f.write("=" * 80 + "\n")
        for r in sorted(merchant_problems, key=lambda x: x["url"]):
            f.write(f"\n  URL: {r['url']}\n")
            f.write(f"  Status: {r['http_status']}\n")
            if r["is_redirect"]:
                f.write(f"  -> Redirects to: {r['final_url']}\n")
            if r["notes"]:
                f.write(f"  Notes: {r['notes']}\n")
        f.write("\n")

    f.write("=" * 80 + "\n")
    f.write("END OF REPORT\n")
    f.write("=" * 80 + "\n")

print(f"  Written: {output3}")

# ─── Final summary to console ────────────────────────────────────────────────
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"  Total URLs checked:    {total_urls}")
print(f"  200 OK (clean):        {len(status_200)}")
print(f"  Redirects:             {len(redirects_all)} (301: {len(status_301)}, 302: {len(status_302)})")
print(f"  404 Not Found:         {len(status_404)}")
print(f"  5xx Errors:            {len(status_500)}")
print(f"  Timeouts:              {len(status_timeout)}")
print(f"  SSL Errors:            {len(status_ssl)}")
print(f"  Connection Errors:     {len(status_conn)}")
print(f"  Problem URLs total:    {len(problem_results)}")
print(f"\n  Wasted spend (404s):   ${total_wasted_spend_404:,.2f}")
print(f"  Redirect spend:        ${total_redirect_spend:,.2f}")
print(f"\n  Output files:")
print(f"    {output1}")
print(f"    {output2}")
print(f"    {output3}")
print("="*80)
