# Acquisition Agent A — Findings Report

**Agent**: Acquisition Agent A (Google Ads + GA4 Analysis)
**Date**: 2026-03-15
**Analysis Period**: 2026-02-13 to 2026-03-14 (30 days)
**Status**: BLOCKED — credentials unavailable in this environment

---

## Execution Summary

Two analysis scripts were written and validated:

1. **`acquisition_a_google_ads.py`** — Pulls campaign, keyword (top 50), search term (14d), and daily trend data from Google Ads API
2. **`acquisition_a_ga4.py`** — Pulls traffic sources, landing pages, device breakdown, new/returning users, and ecommerce funnel from GA4 Data API

Both scripts executed successfully through credential validation but could not pull live data because the `.env` file containing API credentials is not present in this sandboxed environment. The `.env` file exists on the production machine (referenced by `daily_pull.py` and documented in `CLAUDE.md`) but was excluded from the repository via `.gitignore`.

### To Run With Live Data

Place the `.env` file at `/home/user/nature-seed-data/.env` with these keys:
- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_CLIENT_ID`
- `GOOGLE_ADS_CLIENT_SECRET`
- `GOOGLE_ADS_REFRESH_TOKEN`
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID` (838-619-4588)
- `GOOGLE_ADS_CUSTOMER_ID` (599-287-9586)

Then run:
```bash
cd /home/user/nature-seed-data
python3 funnel-analysis/scripts/acquisition_a_google_ads.py
python3 funnel-analysis/scripts/acquisition_a_ga4.py
```

Output files will be generated at:
- `funnel-analysis/reports/google_ads_data.md` — formatted campaign/keyword/search term analysis
- `funnel-analysis/reports/google_ads_raw.json` — raw structured data for downstream agents
- `funnel-analysis/reports/ga4_data.md` — formatted traffic/funnel analysis
- `funnel-analysis/reports/ga4_raw.json` — raw structured data for downstream agents

---

## What Each Script Analyzes

### Google Ads Script (`acquisition_a_google_ads.py`)

| Analysis | Details |
|----------|---------|
| **Campaign Performance** | All active campaigns with spend, clicks, impressions, conversions, ROAS, CPC, CTR, conversion rate, profit/loss |
| **Keyword Performance** | Top 50 keywords by spend with ROAS, identifies zero-conversion keywords and wasted spend |
| **Search Term Report** | 14-day search query data showing what actual queries triggered ads, flags zero-conversion terms |
| **Daily Trends** | 30-day daily CPC, ROAS, and conversion rate trends with week-over-week comparison |
| **Waste Calculation** | Dollar amounts wasted on zero-conversion keywords and search terms |

### GA4 Script (`acquisition_a_ga4.py`)

| Analysis | Details |
|----------|---------|
| **Traffic by Source/Medium** | Top 30 sources with sessions, bounce rate, avg duration, purchases |
| **Landing Page Performance** | Top 30 pages with conversion rate, flags high-traffic/low-conversion pages |
| **Device Breakdown** | Mobile vs desktop vs tablet with conversion rate gap analysis |
| **New vs Returning** | Conversion rate comparison between new and returning visitors |
| **Ecommerce Funnel** | Sessions → Add to Cart → Begin Checkout → Purchase with drop-off rates at each stage |

---

## Analysis Framework (What to Look For When Data Is Available)

### Google Ads — Key Waste Indicators

1. **Campaigns with ROAS < 1x**: Spending more than they return. Candidates for pause or restructure.
2. **Zero-conversion keywords**: Keywords consuming budget with no returns. Add as negatives or pause.
3. **Irrelevant search terms**: Queries triggering ads that have no purchase intent. Add as negative keywords.
4. **CPC trend**: If CPC is rising without corresponding ROAS improvement, bid strategy needs adjustment.
5. **High-click, low-conversion campaigns**: Indicate landing page or audience targeting problems, not ad copy issues.

### GA4 — Key Conversion Gaps

1. **Mobile vs Desktop gap**: Seed/garden customers often research on mobile but buy on desktop. A large gap signals mobile UX issues.
2. **Funnel drop-off points**: Where are visitors abandoning? Cart abandonment vs checkout abandonment need different fixes.
3. **High-bounce landing pages**: Pages getting paid traffic but immediately losing visitors — page load speed, content mismatch, or poor mobile experience.
4. **Source quality**: Which paid channels bring users who actually convert vs just visit?
5. **New vs returning conversion**: If returning users convert much higher, the site needs better first-visit trust signals (reviews, guarantees, etc.).

---

## Known Context from Existing Data Pipeline

From the `daily_pull.py` system and `CLAUDE.md`:

- **Google Ads Customer ID**: 599-287-9586 (login: 838-619-4588)
- **GA4 Property**: 294622924
- **Conversion metric**: `VLbLXB` in Klaviyo = WooCommerce "Placed Order"
- **Daily pipeline** already pulls aggregate spend/clicks/conversions per day — these scripts go deeper into campaign/keyword/search term granularity
- **Google Ads 4-Year Audit** (`google-ads-audit/`) is complete — scripts 09-13b built
- **Google Ads Drip Automation** (`google-ads-audit/drip/`) is live — Mon/Thu cron with Telegram approval

---

## Recommendations (Pre-Data)

Based on the infrastructure and known account structure:

1. **Run these scripts on the production machine** where `.env` exists to get live data
2. **Cross-reference with the existing daily_pull data** in Supabase to validate trends
3. **Focus first on search term waste** — this is typically the largest source of wasted spend for seed/garden ecommerce
4. **Check mobile conversion rates** — seed shopping has high mobile research behavior
5. **Map top landing pages to Google Ads campaigns** — ensure paid traffic lands on high-converting pages, not informational blog posts

---

## Files Created

| File | Purpose |
|------|---------|
| `funnel-analysis/scripts/acquisition_a_google_ads.py` | Google Ads campaign/keyword/search term analysis |
| `funnel-analysis/scripts/acquisition_a_ga4.py` | GA4 traffic/funnel/device analysis |
| `funnel-analysis/reports/acquisition_a_findings.md` | This report |
