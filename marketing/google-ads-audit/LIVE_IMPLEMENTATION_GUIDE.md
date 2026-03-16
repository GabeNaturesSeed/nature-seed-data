# Google Ads Implementation Guide — LIVE STATE
## Nature's Seed | naturesseed.com
### Based on: LIVE_STATE_AUDIT.md (March 5, 2026)
### Scope: ONLY the 6 enabled campaigns currently serving traffic

---

**This guide contains ONLY actions that apply to currently running campaigns, ads, and keywords. Every recommendation has been verified against the live account state and the live merchant feed (280 products). Nothing references paused, removed, or historical-only items.**

---

## Quick Reference: Current Live Account

| Campaign | Type | Daily Budget | 3M ROAS | Status |
|---|---|---|---|---|
| Shopping \| Catch All. | Shopping | $1,100 | 2.45-3.11 | Stable |
| PMAX \| Catch all | PMax | $760 | 2.52-4.97 | Declining |
| Search \| Animal Seed (Broad) \| ROAS | Search | $260 | **0.84** | **CRITICAL** |
| Search \| Brand \| ROAS | Search | $220 | 8.38-12.55 | Strong |
| PMAX - Search | PMax | $210 | 1.74-5.44 | Improving |
| Search \| Pasture \| Exact | Search | $78 | 1.89-4.08 | Improving |

**Total daily budget: $2,628/day (~$79K/month)**

---

## TIER 1: STOP THE BLEEDING (Do This Week)

### 1.1 Fix 16 Live Ad URLs

**Script:** `scripts/09_fix_live_ad_urls.js`
**Impact:** 16 enabled ads point to old URL paths or use www. subdomain
**All-time spend on these ads:** ~$12,900
**Verified:** All 10 destination URLs return HTTP 200 (confirmed March 5, 2026)

**What to do:**
1. Open Google Ads → Tools → Scripts
2. Paste the contents of `09_fix_live_ad_urls.js`
3. Run with `DRY_RUN = true` — review logs
4. Set `DRY_RUN = false` — run again to apply
5. Verify in the Ads interface that URLs updated

**Specific fixes:**

| Ad ID | Campaign | Current URL | New URL |
|---|---|---|---|
| 272079888904 | Brand | `www.naturesseed.com/` | `naturesseed.com/` |
| 272079888901 | Brand | `www.naturesseed.com/` | `naturesseed.com/` |
| 272079888907 | Brand | `www.naturesseed.com/` | `naturesseed.com/` |
| 771352317042 | Pasture Exact | `/product/cattle-dairy-cow-pasture-mix...` | `/products/pasture-seed/cattle-dairy-cow-pasture-mix...` |
| 771352317054 | Pasture Exact | `/product/sheep-pasture-forage-mix...` | `/products/pasture-seed/sheep-pasture-forage-mix...` |
| 771352317048 | Pasture Exact | `/product/alpaca-llama-pasture-forage-mix/` | `/products/pasture-seed/alpaca-llama-pasture-forage-mix/` |
| 773132599438 | Animal Broad | `/pasture-seed/cattle-pastures/beef-cattle-forage/` | `/products/pasture-seed/cattle-pasture-seed/` |
| 773132599351 | Animal Broad | `/pasture-seed/horse-pastures/` | `/products/pasture-seed/horse-pastures-seed/` |
| 773132599198 | Animal Broad | `/pasture-seed/sheep-pastures/` | `/products/pasture-seed/sheep-pastures-seed/` |
| 773132599345 | Animal Broad | `/pasture-seed/alpaca-llama-pastures/` | `/products/pasture-seed/alpaca-llama-pasture-forage-mix/` |
| 773132599426 | Animal Broad | `/product/pig-pasture-forage-mix/` | `/products/pasture-seed/pig-pasture-forage-mix/` |
| 773132599366 | Animal Broad | `/product/alpaca-llama-pasture-forage-mix/` | `/products/pasture-seed/alpaca-llama-pasture-forage-mix/` |
| 773132599387 | Animal Broad | `/pasture-seed/goat-pastures/` | `/products/pasture-seed/goat-pastures-seed/` |
| 773132599390 | Animal Broad | `/pasture-seed/goat-pastures/` | `/products/pasture-seed/goat-pastures-seed/` |
| 773132599570 | Animal Broad | `/product/big-game-food-plot-forage-mix/` | `/products/pasture-seed/big-game-food-plot-forage-mix/` |

**Note on old Script 10 (10_pause_404_ads.js):** That script is NO LONGER NEEDED. All 568 broken 404 URLs were in the paused "US | Search | Product Ads" campaign which is not running. No live ads have 404 URLs.

---

### 1.2 Tighten or Pause Search | Animal Seed (Broad)

**The problem:** This campaign's ROAS collapsed from 3.76 (Jan) to 1.54 (Feb) to **0.84 (Mar)**. It is actively losing money — spending $1 to make $0.84.

**Budget at risk:** $260/day = $7,800/month losing money at current trajectory

**Root cause:** 23 broad-match keywords are matching too many irrelevant or low-intent queries. Top offenders:

| Keyword | 3M Spend | 3M Revenue | ROAS | Action |
|---|---|---|---|---|
| horse pasture seed mix | $949 | $615 | 0.65 | **Pause or switch to Phrase** |
| sheep forage seed mix | $338 | $67 | 0.20 | **Pause** |
| best perennial wildflower seed mix | $189 | $174 | 0.92 | **Pause** |
| chicken pasture seed | $124 | $69 | 0.56 | **Pause** |
| forage seed mix for chickens | $95 | $20 | 0.21 | **Pause** |
| alpaca pasture seed | $87 | $18 | 0.21 | **Pause** |

**What to do:**

**Option A (Conservative):** Pause the 6 worst keywords above ($1,782 spend, $963 revenue = 0.54x ROAS). Keep the campaign running with remaining keywords.

**Option B (Aggressive):** Reduce campaign budget from $260 to $100/day while the above keywords are paused. Let Google's algorithm re-optimize with fewer, better keywords.

**Option C (Nuclear):** Pause the entire campaign for 2 weeks, redirect the $260/day to Brand or Shopping. Re-evaluate after.

**Recommended: Option A + B** — Pause the 6 worst keywords AND reduce budget to $130/day.

---

### 1.3 Pause 24 Money-Losing Keywords

The following keywords have ROAS below 1.0x in the last 3 months (spending more than they earn). All are in enabled campaigns.

**Action: Pause these keywords in Google Ads.**

**High-spend losers (>$100 each):**

| Keyword | Campaign | Match | 3M Cost | 3M ROAS |
|---|---|---|---|---|
| horse pasture seed mix | Animal Broad | BROAD | $949 | 0.65 |
| sheep forage seed mix | Animal Broad | BROAD | $338 | 0.20 |
| best perennial wildflower seed mix | Animal Broad | BROAD | $189 | 0.92 |
| pasture grass for sheep | Pasture Exact | EXACT | $134 | 0.01 |
| chicken pasture seed | Animal Broad | BROAD | $124 | 0.56 |
| wildflower seeds | Pasture Exact | PHRASE | $121 | 0.00 |
| pasture grass seed mix | Pasture Exact | PHRASE | $112 | 0.44 |

**Medium-spend losers ($20-$100 each):**

| Keyword | Campaign | Match | 3M Cost | 3M ROAS |
|---|---|---|---|---|
| forage seed mix for chickens | Animal Broad | BROAD | $95 | 0.21 |
| alpaca pasture seed | Animal Broad | BROAD | $87 | 0.21 |
| arizona wildflower seed mix | Animal Broad | BROAD | $32 | 0.00 |
| bulk micro clover seed | Animal Broad | BROAD | $31 | 0.00 |
| chicken safe grass seed | Pasture Exact | PHRASE | $27 | 0.00 |
| pig pasture seed | Animal Broad | BROAD | $25 | 0.00 |
| alpaca grass seed | Pasture Exact | PHRASE | $25 | 0.00 |
| white clover grass seed | Animal Broad | BROAD | $24 | 0.00 |
| pasture grass seed for horses | Pasture Exact | PHRASE | $24 | 0.00 |
| white clover lawn | Animal Broad | BROAD | $22 | 0.00 |
| timothy grass seed | Pasture Exact | PHRASE | $21 | 0.00 |
| white clover grass | Animal Broad | BROAD | $21 | 0.00 |
| pasture seed for horses | Pasture Exact | PHRASE | $19 | 0.00 |
| pasture grass for sheep | Pasture Exact | PHRASE | $41 | 0.00 |
| sheep forage seed mix | Pasture Exact | EXACT | $37 | 0.00 |
| california wildflower seeds | Pasture Exact | PHRASE | $14 | 0.00 |
| california native wildflower seeds | Pasture Exact | PHRASE | $11 | 0.00 |

**Total waste from these 24 keywords: ~$2,300 in the last 3 months (~$770/month).**

**Full list with performance data:** `implementation/LIVE_top_keywords.csv` — filter for "MONEY LOSER" status.

---

### 1.4 Add Negative Keywords for Top Wasted Search Terms

**637 search terms** with $5+ spend and zero conversions in Q1 2026 = **$8,038 wasted**.

**Add these as negative keywords at the ACCOUNT level (campaign-level for Shopping):**

**Competitor/brand terms (add as exact match negatives across all campaigns):**
- "johnny seed" ($44)
- "granite seed" ($41)
- "sustane 18 1 8" ($28)

**Products not carried or low-relevance (add as phrase match negatives):**
- "st augustine grass seed" ($32) — if not a core product
- "bahia grass seed" ($38) — if not a core product
- "zoysia grass seed" ($35) — if not a core product
- "mycorrhizae" ($34) — accessory, low purchase intent
- "fine fescue seed" ($37) — evaluate if in live catalog

**Informational / non-purchase intent (add as exact match negatives):**
- "nature's seed phone number" ($25)
- "naturesseed com" ($44) — this is a navigation query that should be caught by Brand, not Shopping

**Generic terms bleeding budget in Shopping (add to Shopping campaign negatives):**
- "kentucky bluegrass" ($38) — too broad for Shopping
- "pasture grass" ($40) — too generic
- "native california grass seed" ($139) — high spend, zero conversions

**Ready-to-paste negative keyword lists:**
See `implementation/negative_keywords_paste_list.txt` (from the original audit — these terms are still valid since they come from live campaign search term data).

**Full wasted search term list:** `implementation/LIVE_wasted_search_terms.csv`

---

## TIER 2: QUICK WINS (Next 2 Weeks)

### 2.1 Fix "Search | Pasture | Exact" Bidding Strategy

**The problem:** This campaign uses "Maximize Conversions" instead of "Maximize Conversion Value" like the other Search campaigns. This means Google optimizes for conversion COUNT, not revenue. It'll happily drive 10 $20 conversions instead of 2 $200 conversions.

**What to do:**
1. Go to Campaign Settings → Bidding
2. Change from "Maximize Conversions" to "Maximize Conversion Value"
3. Optionally set a target ROAS of 300% (3.0x) as a floor

**Why this matters:** This campaign's ROAS (1.89 → 3.37 → 4.08) is improving but still below Animal Broad's historical peak. Switching to value-based bidding should lift ROAS by prioritizing higher-revenue clicks.

---

### 2.2 Add Missing High-Value Keywords

Historical data shows these keywords drove significant revenue but are NOT in any current campaign:

| Keyword | Suggested Match | Historical Revenue | Historical ROAS | Add to Campaign |
|---|---|---|---|---|
| pasture seed | PHRASE | $24,102 | 3.15 | Pasture Exact |
| pasture seed | EXACT | $15,331 | 3.65 | Pasture Exact |
| hay seed mix | BROAD | $11,127 | 10.75 | Pasture Exact (new Hay Seed ad group) |
| lawn seed | PHRASE | $7,354 | 3.61 | Pasture Exact (new Lawn ad group) |
| pasture grass mix | PHRASE | $7,576 | 3.44 | Pasture Exact |
| horse pasture seed | PHRASE | $9,695 | 3.75 | Pasture Exact (Horse) |
| sheep pasture mix | PHRASE | $5,514 | 9.51 | Pasture Exact (Sheep) |
| best cattle pasture mix | PHRASE | $5,391 | 12.78 | Pasture Exact (Cattle) |
| cattle pasture seed | EXACT | $5,165 | 11.18 | Pasture Exact (Cattle) |

**Priority 1:** "pasture seed" (phrase + exact) — this family alone drove $39K+ in historical revenue.

**Priority 2:** "hay seed mix" — 10.75x ROAS is exceptional and this term has zero current coverage.

**Priority 3:** "lawn seed" — $7.3K revenue at 3.61x, currently zero coverage in any Search campaign.

**What to do:**
1. Navigate to Search | Pasture | Exact campaign
2. Add "pasture seed" as PHRASE and EXACT match keywords to the "All Pasture" ad group
3. Create a new ad group called "Hay Seed" with keyword "hay seed mix" (BROAD) + a new RSA ad pointing to the timothy/hay seed product page
4. Create a new ad group called "Lawn Seed" with keyword "lawn seed" (PHRASE) + a new RSA pointing to `/products/grass-seed/`

---

### 2.3 Review Conversion Tracking

**Concern:** The data shows fractional conversion numbers (e.g., 93.4, 7.2, 4.0) which indicates either:
- A "Begin Checkout" conversion action is enabled alongside Purchase (counting cart adds)
- Attribution model is splitting credit across touchpoints (expected with data-driven)

**What to check:**
1. Go to Tools → Conversions → see which conversion actions are active
2. If "Begin Checkout" is set to "Primary", change it to "Secondary" (observation only)
3. Only "Purchase" / "Placed Order" should be a Primary conversion action
4. This directly affects Smart Bidding — the algorithm is optimizing toward whatever conversion actions are set as Primary

**Why it matters:** If Begin Checkout inflates conversion counts by 30-50%, your bidding algorithm is over-valuing low-intent signals and spending on clicks that start checkout but don't complete purchase.

---

### 2.4 Exclude Zero-Revenue Shopping Products

**101 products** in Shopping | Catch All had spend but zero revenue in Q1 2026.

**Top offenders to exclude or monitor:**

| Product | Q1 Spend | Action |
|---|---|---|
| Cool-Season Pasture 10 Lb | $118 | Exclude from Shopping |
| Rocky Mountains Wildflower 1 Lb | $102 | Exclude from Shopping |
| Wildflower 0.5 Lb | $100 | Exclude from Shopping |
| White Sage Seed | $94 | Exclude from Shopping |
| Native Cabin Grass Seed Mix 25 lb | $90 | Exclude from Shopping |
| Kentucky Bluegrass Pasture Seed | $88 | Exclude from Shopping |
| Upland Game Bird Food Plot Seed | $85 | Exclude from Shopping |

**Total waste from all 101 zero-revenue products:** ~$3,200 in Q1

**How to exclude:**
- In Merchant Center, you can use `custom_label_4` (currently unused in the feed) to tag low-performers
- In Google Ads Shopping campaign, create a product group that excludes items tagged with this label
- Alternatively, use campaign-level product exclusions in Google Ads for the top offenders

---

## TIER 3: STRATEGIC GROWTH (Next 30 Days)

### 3.1 Budget Reallocation

**Current allocation vs. recommended:**

| Campaign | Current Budget | Current ROAS | Recommended | Rationale |
|---|---|---|---|---|
| Shopping Catch All | $1,100 (42%) | 2.31-3.11 | $1,000 | Trim $100; mediocre ROAS |
| PMAX Catch all | $760 (29%) | 2.52-4.97 | $760 | Hold; volatile but high-volume |
| Animal Seed Broad | $260 (10%) | **0.84** | **$130** | Cut 50%; losing money |
| Brand Search | $220 (8%) | 8.38-12.55 | **$300** | Increase; highest ROAS |
| PMAX Search | $210 (8%) | 1.74-5.44 | $210 | Hold; improving trend |
| Pasture Exact | $78 (3%) | 1.89-4.08 | **$148** | Double; add new keywords |
| **Total** | **$2,628** | | **$2,548** | **Saves $80/day** |

**Net effect:** Shift $80/day away from money-losing Animal Broad, increase Brand ($80) and Pasture Exact ($70). This should improve blended account ROAS from ~2.8x toward 3.5x+.

---

### 3.2 Evaluate California / Regional Campaign

**Historical context:** The paused "California | PMax | ROAS" campaign generated $174,363 in revenue at 3.17x ROAS. That's significant revenue with no current replacement.

**The live merchant feed already has California infrastructure:**
- `custom_label_1` tags products as "California" (or blank)
- California Wildflower Seed Blend is the #1 product by revenue in Q1 ($4,372, 10.27x ROAS)
- California Poppy, Miniature Lupine, and other CA products are in the feed

**Options:**
1. **Add a California asset group in PMAX Catch All** — lowest effort, uses existing campaign
2. **Reactivate the paused California PMax** — if still in the account, simply re-enable
3. **Create new California Search campaign** — keywords like "california wildflower seed", "california native grass seed"

**Recommended: Option 1** — Add a California-focused asset group in the existing PMAX Catch All. Use custom_label_1 = "California" as the product group filter.

---

### 3.3 Consider DSA (Dynamic Search Ads)

**Historical evidence:** Two paused DSA campaigns generated $35K+ in revenue:
- "Pacific Northwest | DSA" — $875 spend, $11,637 revenue (13.30x ROAS)
- "US | DSA | Pasture Seed" — $2,712 spend, $23,801 revenue (8.77x ROAS)

**Why DSA makes sense:** Nature's Seed has 280 products with well-structured URLs. DSA automatically generates ads from the website content, catching long-tail queries the keyword-based campaigns miss.

**Setup:**
1. Create new campaign: "DSA | All Products"
2. Target the entire naturesseed.com/products/ directory
3. Use Maximize Conversion Value bidding
4. Set daily budget: $50-100
5. Add the same negative keywords from Step 1.4

---

## TIER 4: ONGOING OPTIMIZATION

### 4.1 Mobile Landing Page Review

**Desktop ROAS is 20% higher than mobile** (3.21 vs 2.68). Mobile gets 79% of impressions but only 66% of conversions. This suggests mobile landing pages may be underperforming.

**Check:**
- Page load speed on mobile (should be < 3 seconds)
- Add-to-cart button placement (should be above the fold on mobile)
- Product image quality on small screens
- Checkout flow friction on mobile

---

### 4.2 Monthly Search Term Mining

**Ongoing process:**
1. Every 2 weeks, review search terms in all 3 Search campaigns
2. Add high-converting terms as exact/phrase keywords
3. Add irrelevant terms as negative keywords
4. The `LIVE_wasted_search_terms.csv` is a starting point; this needs to be refreshed regularly

---

### 4.3 Merchant Feed URL Cleanup

**10 products** in the Google Merchant Center feed have URL issues:

| Product | Feed URL | Issue |
|---|---|---|
| Bermudagrass Pasture Seed (3 variants) | `/pasture-seed/bermudagrass-pasture/` | Redirects to `/grass-seed/` category |
| Tortoise Forage Mix (3 variants) | Old product URL | May redirect to category page |
| Miniature Lupine (1) | `/wildflower-seed/miniature-lupins/` | Pluralization mismatch |
| 3 others | Various | Server timeout during check |

**Action:** Update these URLs in the Merchant Center feed to point to the correct `/products/` paths. The full list is in `implementation/FINAL_merchant_feed_wrong_urls.csv`.

---

## Summary Checklist

### This Week
- [ ] Run `09_fix_live_ad_urls.js` (DRY_RUN first, then live)
- [ ] Pause 6 worst keywords in Animal Seed (Broad) — see Section 1.2
- [ ] Pause remaining 18 money-losing keywords — see Section 1.3
- [ ] Add top negative keywords — see Section 1.4
- [ ] Reduce Animal Seed (Broad) budget from $260 to $130

### Next 2 Weeks
- [ ] Change Pasture Exact bidding to Maximize Conversion Value
- [ ] Add "pasture seed" (phrase + exact) keywords
- [ ] Add "hay seed mix" keyword + ad group
- [ ] Add "lawn seed" keyword + ad group
- [ ] Audit conversion actions — check for Begin Checkout inflation
- [ ] Exclude top zero-revenue Shopping products

### Next 30 Days
- [ ] Increase Brand budget to $300
- [ ] Increase Pasture Exact budget to $148
- [ ] Add California asset group to PMAX Catch All
- [ ] Evaluate DSA campaign ($50-100/day test)
- [ ] Review mobile landing page speed and UX

### Ongoing
- [ ] Bi-weekly search term review
- [ ] Monthly keyword performance review
- [ ] Update merchant feed URLs

---

## Supporting Files Reference

| File | What It Contains |
|---|---|
| `LIVE_STATE_AUDIT.md` | Full audit report (live campaigns only) |
| `scripts/09_fix_live_ad_urls.js` | Google Ads Script — fix 16 live ad URLs |
| `implementation/LIVE_enabled_ads_with_urls.csv` | All 39 enabled ads with URLs |
| `implementation/LIVE_enabled_keywords.csv` | All 66 enabled keywords with 3M performance |
| `implementation/LIVE_top_keywords.csv` | Keywords classified Winner/Loser/Neutral |
| `implementation/LIVE_url_issues.csv` | 16 ads with URL problems |
| `implementation/LIVE_wasted_search_terms.csv` | 637 zero-conversion search terms |
| `implementation/FINAL_merchant_feed_wrong_urls.csv` | 10 feed products with URL issues |
| `implementation/negative_keywords_paste_list.txt` | Ready-to-paste negative keywords |

---

*Generated by Nature's Seed Data Orchestrator | March 5, 2026*
*Based on LIVE_STATE_AUDIT.md — all recommendations verified against enabled campaigns only*
