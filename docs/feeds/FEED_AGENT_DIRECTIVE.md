# Feed Agent Directive — Nature's Seed
_Version: 1.0 | Created: 2026-04-30 | Next review: 2026-05-31_

---

## Mission

Maintain feed health across all 8 distribution channels for Nature's Seed (~478 WC SKUs). Execute the monthly housekeeping run autonomously, prioritize actions by revenue impact, and deliver a scannable summary to Gabe after each run. Do not block on ambiguity — log it and move on.

---

## Platform Guide Paths

Read the relevant guide before taking any action on that channel. These are authoritative on field specs, failure modes, and seasonal behavior.

```
docs/feeds/guides/walmart.md
docs/feeds/guides/amazon.md
docs/feeds/guides/google_merchant.md
docs/feeds/guides/klaviyo.md
docs/feeds/guides/shopper_approved.md
docs/feeds/guides/reddit.md
docs/feeds/guides/facebook.md
docs/feeds/guides/pinterest.md
```

---

## Monthly Workflow

Execute in this exact order every monthly run:

### Step 1 — Read Benchmark

Load `feeds/benchmark/benchmark.json`. Extract the latest snapshot. Record:
- `date`, `iso_week`, `seasonality_index`, `season_label`
- Per-channel: `coverage_score`, `quality_score`, `drift_score`, `composite`, and `raw` counts
- Any channels in `error` state

### Step 2 — Classify Signals

Apply the thresholds below to identify which channels need action this cycle.

| Score | Red | Amber | Green |
|-------|-----|-------|-------|
| Coverage | < 70 | 70–89 | ≥ 90 |
| Quality | < 80 | 80–94 | ≥ 95 |
| Drift | < 70 | 70–89 | ≥ 90 |

Special rules:
- Coverage gaps **below the seasonality-adjusted threshold** (see Seasonality Rules table): log only, do not alert Gabe.
- Coverage gaps **above the seasonality-adjusted threshold**: treat same as amber/red quality.
- Any channel in `error` state for 3 consecutive days: alert Gabe immediately, regardless of season.
- Quality red or amber: **always act**, regardless of season or coverage state.
- Drift red: act if within a revenue-generating season window (see Seasonality Rules). Off-season drift: log, schedule for next cycle.

### Step 3 — Execute Priority Actions

Work through the Prioritized Action List below (updated each cycle based on current benchmark). Complete each action fully before moving to the next. Commit a dry-run log before any price or inventory push. See Standing Rules.

### Step 4 — Commit and Log

After each completed action:
- Commit a brief git commit describing what changed and the score delta (before → after)
- Append an entry to the Pivot Log at the bottom of this file

### Step 5 — Write Report

Write the Monthly Run Report (see Reporting Template) as a Markdown file at:
`docs/feeds/reports/YYYY-MM-DD-monthly-run.md`

Do NOT commit this to git — it is an ephemeral working artifact. Surface it to Gabe directly.

---

## Seasonality Rules

Nature's Seed operates on two seasonal peaks aligned with spring and fall planting windows. Adjust coverage targets and drift urgency accordingly.

| Season | Weeks | Index Range | Coverage Target | Drift Urgency | Notes |
|--------|-------|-------------|-----------------|---------------|-------|
| Spring Peak | 8–18 | ≥ 0.85 | ≥ 95% all channels | P1 — act same day | Highest revenue window of year. Any suppressed SKU = permanent lost revenue. |
| Spring Shoulder | 6–7, 19–20 | 0.65–0.84 | ≥ 85% | P2 — act within 3 days | Ramp up / ramp down window. Catalog must be clean before week 8. |
| Fall Peak | 32–38 | ≥ 0.75 | ≥ 90% | P1 — act same day | Second revenue peak. Food plots, overseeding, cover crops. |
| Fall Shoulder | 30–31, 39–40 | 0.55–0.74 | ≥ 80% | P2 — act within 3 days | |
| Slow Period | 21–29, 41–52 | < 0.55 | ≥ 42% (current acceptable floor) | P3 — log, next cycle | Off-season. Focus on content quality and catalog expansion. |
| Recovery Window | 1–5 | 0.35–0.55 | ≥ 60% | P2 | Pre-peak content fix window. All content work must land before week 6. |

**Current state (week 18, index 0.537, Slow Period transitioning out of Spring Peak):** Any unfixed quality or drift that survived peak season must be resolved NOW before the account-quality damage compounds into off-season ranking debt.

---

## Prioritized Action List (Current Cycle — 2026-04-30)

Ordered by revenue impact. Work top to bottom. Do not skip items without logging a reason.

---

### Priority 1 — Walmart Drift (191 stock items)
**Why #1:** 191 SKUs are invisible in Walmart search and Buy Box-ineligible right now. Each OOS-misrepresented item converts at 0%. This is direct, immediate revenue loss at the tail end of peak season.

**Action:**
1. Read `docs/feeds/guides/walmart.md` — stock drift fix section.
2. Run `feeds/sync/sync_prices.py --dry-run` first. Commit the dry-run log to `feeds/logs/YYYY-MM-DD-walmart-dry-run.log`.
3. Confirm policy decision for `onbackorder` items: during week 18 (end of peak), push as `available` with `fulfillmentLagTime=7` via `walmart_lagtime_update.py`. Off-season, push as `outofstock`.
4. Run `feeds/sync/sync_prices.py --push`.
5. Wait 60 minutes. Verify `drift_score` in next audit run moves from 0 to ≥ 90.
6. Log: drift_score 0 → target 90+.

**Acceptance criterion:** `walmart.drift_score ≥ 90` in next benchmark snapshot.

---

### Priority 2 — Klaviyo Catalog Drift (267 price + 134 stock drifted items)
**Why #2:** 84% of Klaviyo catalog items carry stale price or stock data. This directly degrades browse abandonment emails (wrong prices shown), back-in-stock flow accuracy, and recommendation engine quality. The Klaviyo guide estimates 15–25% degradation on flow-attributed revenue vs. a clean catalog. Email is the highest-margin channel — this is a revenue multiplier, not a vanity metric.

**Action:**
1. Read `docs/feeds/guides/klaviyo.md` — drift fix section.
2. Pull current WC product list (prices + stock) via WC REST API. Use CF Worker if `CF_WORKER_URL` is set. Parse `.env` with `line.split('=', 1)` + `.strip().strip("'\"")`.
3. Transform to Klaviyo catalog payload. Use API revision `2024-07-15`. Account `H627hn`.
4. Submit full re-push via `/api/catalog-item-bulk-update-jobs` (batch endpoint, not per-item).
5. Build URL manually — do NOT let `requests` encode `page[size]`: `url = f"{KLAVIYO_BASE}/catalog-items?page[size]=100"`.
6. Confirm `drift_score` in next audit moves from 0 to ≥ 90.
7. Log: drift_score 0 → target 90+.

**Acceptance criterion:** `klaviyo.drift_score ≥ 90` in next benchmark snapshot.

---

### Priority 3 — Walmart Quality (200 SKUs missing shortDescription + mainImageUrl)
**Why #3:** quality_score = 0 means every live Walmart listing has LQS near 40, well below the 60-point threshold for search relevance or Buy Box eligibility. This is not just a slow-bleed — it is a persistent suppression affecting all 200 live SKUs. Even a mid-peak fix lifts LQS within ~7 days. Off-season is the ideal window to catch up, and that window is now opening.

**Action:**
1. Read `docs/feeds/guides/walmart.md` — quality fix section and image CDN failure mode.
2. Pull `short_description` and `images[0].src` for all 200 Walmart SKUs from WC via API.
3. Check image URLs: run `curl -A "WalmartImageBot" -I {url}` on a sample. If Cloudflare Bot Fight Mode blocks Walmart's crawler, image must be hosted at a CF-excluded path (e.g., `cdn.naturesseed.com/marketplace/`) before submission. Do not submit image URLs that return non-200 to Walmart's crawler — they will be silently rejected.
4. Build `MP_MAINTENANCE` feed payload. Submit in batches of 1000 via `POST /v3/feeds?feedType=MP_MAINTENANCE`.
5. Read `feeds/adapters/walmart.py` before all Walmart API calls — verify token management (`WM_SEC.ACCESS_TOKEN` header, 15-min expiry) and batch patterns.
6. Poll `/v3/feeds/{feedId}` until `feedStatus=PROCESSED`. Log any per-item errors.
7. Log: quality_score 0 → target 60+ (partial) or 90+ (full).

**Acceptance criterion:** `walmart.quality_score ≥ 60` within 7 days of submission.

---

### Priority 4 — Google Merchant Drift (133 stock + 2 price items)
**Why #4:** drift_score = 37 on GMC means 135 items carry stale price or availability data. Price mismatch > ~2% triggers item-level "Mismatched value (price)" disapprovals; ≥ 5 disapprovals within 7 days escalates to account-level warning. An account-level Misrepresentation flag is the worst possible GMC outcome — it caps the entire feed. This is not yet at that threshold, but it is close.

**Action:**
1. Read `docs/feeds/guides/google_merchant.md` — drift and supplemental feed sections.
2. Pull current WC prices and stock_status for all SKUs.
3. Update the Google Sheet (Sheet ID: `12u2Uj0gHNImAQKDA1qnDUxlw4czL4DNuHbuUFqULbuU`) with current prices and `availability` values.
4. Verify Merchant Center sheet fetch schedule is set to daily (Merchant Center → Feeds → fetch schedule).
5. For the 2 price-drift items specifically: confirm the WC price and sheet price now agree. Price drift > 3% is the disapproval trigger.
6. Log: drift_score 37 → target 90+.

**Acceptance criterion:** `google_merchant.drift_score ≥ 80` within 48 hours of sheet update (GMC re-crawl latency).

---

### Priority 5 — Amazon Auth Verification
**Why #5:** Amazon is completely dark — all scores are ERROR. Amazon is Nature's Seed's second-largest marketplace channel. Every day the adapter is broken is a day with no catalog visibility or health tracking.

**Action:**
1. Read `docs/feeds/guides/amazon.md` — auth error section.
2. Verify `AMAZON_SELLER_ID` is set as a **Repository secret** (not Environment secret) in GitHub. The seller ID format is the 13–14 char merchant token (e.g. `A1B2C3...`), not the storefront name.
3. Confirm `LWA_APP_ID`, `LWA_CLIENT_SECRET`, `SP_API_REFRESH_TOKEN`, and `SP_API_ROLE_ARN` are all present.
4. Confirm IAM role policy includes `execute-api:Invoke` on the SP-API endpoint.
5. Trigger a manual audit run. If the 400 error persists after `AMAZON_SELLER_ID` was added 2026-04-29, inspect the response body — `"InvalidInput"/"Invalid sellerId"` means the token is malformed; a different error means auth credentials issue.
6. Log: error → working or error → escalate to Gabe.

**Acceptance criterion:** `amazon` channel returns numeric scores (not ERROR) in next benchmark snapshot.

---

### Priority 6 — Google Merchant Quality (20 incomplete items)
**Why #6:** quality_score = 94, which is amber (below 95 target). 20 items are incomplete — most likely missing GTIN without `identifier_exists: false`, causing silent ranking penalty. This is not urgent but actionable off-season.

**Action:**
1. Read `docs/feeds/guides/google_merchant.md` — GTIN and quality sections.
2. Identify the 20 incomplete items in the Google Sheet — check for missing `gtin` column.
3. For items with a real GTIN: populate it in the sheet.
4. For private-label seed mixes with no GTIN: add `identifier_exists: false` to the sheet row. Do NOT set `identifier_exists: false` for items that genuinely have a GTIN.
5. Log: quality_score 94 → target 95+.

**Acceptance criterion:** `google_merchant.quality_score ≥ 95` in next benchmark snapshot.

---

### Priority 7 — Facebook Quality (9 incomplete items)
**Why #7:** quality_score = 97, composite = 99. Nine items are incomplete — most likely missing `image_link` in the Google Sheet. Low urgency but cleanable this cycle.

**Action:**
1. Read `docs/feeds/guides/facebook.md` — quality score section.
2. Run sheet triage:
   ```python
   import pandas as pd
   df = pd.read_csv("https://docs.google.com/spreadsheets/d/12u2Uj0gHNImAQKDA1qnDUxlw4czL4DNuHbuUFqULbuU/export?format=csv")
   for col in ["image_link", "description", "brand", "title", "price", "mpn"]:
       print(col, df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum())
   ```
3. For empty `image_link` rows: pull `images[0].src` from WC via API and backfill. Square bag-on-white is acceptable for Meta (unlike Pinterest).
4. Log: quality_score 97 → target 100.

**Acceptance criterion:** `facebook.quality_score ≥ 98` in next benchmark snapshot.

---

### Priority 8 — Shopper Approved: SA→Klaviyo Reconnect (Ongoing)
**Why #8:** SA→Klaviyo has been disconnected since August 2025. TURF-JBR, the top seller since July 2025, has 0 reviews after ~9 months of orders. Google Seller Ratings eligibility requires 150 reviews/12 months — the clock is running. This action cannot be automated by the feed agent alone but must be flagged to Gabe each cycle until resolved.

**Action:**
1. Check if SA→Klaviyo integration is reconnected (query SA Admin or check the `shopper_approved` guide).
2. If still disconnected: flag to Gabe in the monthly report. Do not attempt to reconnect autonomously — requires Klaviyo API key validation and SA Admin UI access.
3. If reconnected: verify that TURF-JBR has received a batch review request for the Aug 2025 → reconnect window. Confirm via SA Admin → Products → TURF-JBR review count.
4. Log: reconnected Y/N, TURF-JBR review count.

---

### Priority 9 — Reddit: Awaiting TSV (Blocked)
**Why #9:** Reddit is blocked on an external agent dependency (reddit-ads agent must generate `docs/reddit-catalog/reddit_catalog.tsv`). The feed agent cannot unblock this directly.

**Action:**
1. Check if `docs/reddit-catalog/reddit_catalog.tsv` exists.
2. If it exists: run the adapter and verify coverage and quality scores populate.
3. If it does not exist: log "Reddit blocked — TSV not generated" in report. Do not alert Gabe unless this has been missing for > 30 days.

---

### Priority 10 — Pinterest (STUB — Do Not Touch)
Pinterest is intentionally STUB. Do not attempt to build the adapter or run any Pinterest actions. Target build window is Q3 2026 (July–August). Until then, the STUB status is expected and correct.

---

## Standing Rules

These rules apply in every run, every month, without exception.

1. **Never auto-push price changes without a dry-run log first.** Always run `sync_prices.py --dry-run` and commit the output to `feeds/logs/YYYY-MM-DD-<channel>-dry-run.log` before running `--push`. No exceptions.

2. **Quality is always acted on, regardless of season.** Coverage and drift can wait for the right season window. Quality gaps (missing required fields, broken images, wrong field formats) degrade accounts silently and compound — act immediately.

3. **Adapter errors 3 days in a row: alert Gabe immediately.** If any channel shows `error` in `benchmark.json` for 3 consecutive daily runs, include an explicit "ACTION REQUIRED" line in the daily digest and the monthly report, with the exact error message and the fix steps from the guide.

4. **Do not overwrite channel-specific copy with WC source copy.** Each channel has field constraints and audience tone distinct from the WC product description. When pushing content (shortDescription, bullets, title), pull from WC as the source of truth but apply channel-specific formatting and truncation. Never paste WC HTML into Walmart's plain-text fields.

5. **Before any Walmart operation, read `feeds/adapters/walmart.py`.** Verify token management (`WM_SEC.ACCESS_TOKEN` header, 15-min token expiry refresh), batch size limits, and rate-limit spacing. Do not assume the adapter is unchanged between cycles.

6. **Pinterest STUB is intentional.** Do not attempt to build, configure, or test the Pinterest adapter until Q3 2026 is explicitly approved by Gabe. The STUB scorecard entry is correct behavior.

7. **Reddit ERROR is expected.** Until the reddit-ads agent delivers `docs/reddit-catalog/reddit_catalog.tsv`, Reddit will show ERROR. This is a known external dependency — do not attempt to generate the TSV manually or fabricate catalog data.

8. **Content changes are intentional per channel.** Walmart content is different from GMC content which is different from Klaviyo catalog fields. Do not normalize or flatten copy across channels. Each channel's adapter owns its transformation.

9. **Parse `.env` correctly.** The `.env` file uses spaces around `=` and quotes around values. Always parse with: `key, val = line.split('=', 1); val = val.strip().strip("'\"")`  — never use `source .env` or Python's `os.environ.get()` without a proper parser.

10. **WC rate limit: 0.3s between calls.** Use CF Worker proxy (`CF_WORKER_URL` + `CF_WORKER_SECRET`) when set. Residential IPs can call WC directly; datacenter IPs (GitHub Actions) must route through the Worker.

11. **Never use `/product-category/` URLs in any feed.** Nature's Seed uses Permalink Manager — all product URLs are `/products/<slug>`. A `/product-category/` URL in any feed field (`link`, `url`) will cause broken landing pages and policy disapprovals.

12. **Walmart `onbackorder` policy requires a decision each cycle.** The mapping of WC `onbackorder` to Walmart is not automatic. During peak (weeks 8–18): push as `available` with `fulfillmentLagTime=7`. Off-season: push as `outofstock`. Confirm the current week before running the sync.

---

## Reporting Template

After each monthly run, write a report to `docs/feeds/reports/YYYY-MM-DD-monthly-run.md` using this structure. The goal is 2-minute readability for Gabe.

```markdown
# Feed Health — Monthly Run [YYYY-MM-DD]

**Week:** [N] | **Season:** [label] | **Seasonality Index:** [X.XXX]

---

## Actions Taken

| Channel | Dimension | Before | After | What Was Done |
|---------|-----------|--------|-------|---------------|
| walmart | drift | 0 | 92 | Ran sync_prices.py --push; 191 stock items synced |
| klaviyo | drift | 0 | 91 | Full catalog re-push via bulk-update-jobs endpoint |
| ... | ... | ... | ... | ... |

---

## Still Open (Blocked)

| Channel | Issue | Blocked On |
|---------|-------|-----------|
| reddit | ERROR — TSV missing | reddit-ads agent |
| shopper_approved | SA→Klaviyo disconnected | Gabe: manual reconnect in SA Admin |
| ... | ... | ... |

---

## Errors

| Channel | Error | Duration | Alert? |
|---------|-------|----------|--------|
| amazon | 400 SP-API auth | 2 days | No (< 3 days) |
| ... | ... | ... | ... |

---

## Score Summary

| Channel | Coverage | Quality | Drift | Composite | Delta |
|---------|----------|---------|-------|-----------|-------|
| walmart | 100 | 0→60 | 0→92 | 40→70 | +30 |
| amazon | ERROR | ERROR | ERROR | ERROR | — |
| google_merchant | 100 | 94→95 | 37→85 | 82→93 | +11 |
| klaviyo | 100 | 90 | 0→91 | 72→93 | +21 |
| shopper_approved | 100 | 97 | 100 | 99 | 0 |
| reddit | ERROR | ERROR | ERROR | ERROR | — |
| facebook | 100 | 97→100 | 100 | 99→100 | +1 |
| pinterest | STUB | STUB | STUB | STUB | — |

---

## Next Month Focus

1. [Channel + specific action + target score]
2. [Channel + specific action + target score]
3. [Channel + specific action + target score]
```

---

## Pivot Log

Record every significant change to channel state, directive updates, or structural decisions. The feed agent appends an entry after each monthly run.

| Date | Entry |
|------|-------|
| 2026-04-30 | Initial directive created. Benchmark snapshot v1 loaded. Top issues: Walmart quality=0 (200 SKUs missing shortDescription+mainImageUrl), Walmart drift=0 (191 stock items), Klaviyo drift=0 (267 price + 134 stock items), GMC drift=37 (133 stock + 2 price items), Amazon ERROR (auth). |

---

## Reference: Benchmark Score Interpretation

| Composite | Meaning |
|-----------|---------|
| 90–100 | Healthy — monitor only |
| 75–89 | Amber — act within this cycle |
| 50–74 | Red — act this week |
| < 50 | Critical — act today, flag to Gabe |

**Current composites (2026-04-30):**

| Channel | Composite | Status |
|---------|-----------|--------|
| walmart | 40 | Critical |
| amazon | ERROR | Blocked |
| google_merchant | 82 | Amber |
| klaviyo | 72 | Red |
| shopper_approved | 99 | Healthy |
| reddit | ERROR | Blocked (expected) |
| facebook | 99 | Healthy |
| pinterest | STUB | Intentional |

---

_End of directive. Update version header and append to Pivot Log after each monthly run._
