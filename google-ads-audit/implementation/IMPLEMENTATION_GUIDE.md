# Nature's Seed Google Ads -- Implementation Guide

**Generated:** March 5, 2026
**Audit Period:** March 2022 -- March 2026
**Current ROAS:** 3.21x (down from 10.58x in 2022)
**Target ROAS after implementation:** 4.0--4.5x
**Estimated impact:** $150--300K additional revenue on less spend

This guide walks through every recommendation from the full audit, in priority order, with exact navigation paths, file references, and verification steps. Follow it top to bottom.

---

## WEEK 1: Critical Fixes (Tier 1)

These three actions have the highest ROI per minute of effort. Do them before anything else.

---

### Step 1: Remove "Begin Checkout" from Conversion Tracking

**Time:** 5 minutes
**Priority:** CRITICAL -- do this first

#### WHY

The "Begin checkout" conversion action is currently **included in the Conversions column** and is inflating reported conversions by 30--54%. In Q1 2026 alone, it added ~3,753 fake conversions. This corrupts Smart Bidding: the algorithm sees artificially high conversion rates, bids too aggressively, and wastes budget on low-quality traffic that merely reaches checkout but never purchases.

#### WHAT

Exclude "Begin checkout" from the primary Conversions column so Smart Bidding only optimizes toward actual purchases.

#### WHERE (Navigation)

1. Go to [ads.google.com](https://ads.google.com)
2. Click **Goals** in the left sidebar
3. Click **Conversions** > **Summary**
4. Find the conversion action named **"Begin checkout"**
5. Click on it to open the detail view
6. Click **Edit settings**
7. Under **"Include in 'Conversions'"**, change the toggle to **No**
8. Click **Save**

#### EXPECTED IMPACT

- Smart Bidding will see real conversion rates (not inflated ones), leading to more conservative, efficient bidding
- Estimated 15--20% reduction in wasted spend ($45--70K/year) as the algorithm stops overbidding on checkout-but-no-purchase traffic
- ROAS reporting will become accurate, giving you real performance data to make decisions

#### FILES REFERENCED

- `FULL_AUDIT_REPORT.md` -- Section 7: Conversion Tracking, Issue #1

#### VERIFICATION

1. Wait 24 hours after making the change
2. Go to **Goals** > **Conversions** > **Summary**
3. Confirm "Begin checkout" now shows "Secondary" under the "Include in Conversions" column (not "Yes")
4. Check campaign-level reporting: the Conversions column should drop noticeably (this is correct -- it was previously inflated)
5. **Do NOT panic** when conversion numbers drop. The old numbers were fake. Allow 2 weeks for Smart Bidding to recalibrate.

---

### Step 2: Add Negative Keywords Across All Campaigns

**Time:** 30 minutes
**Priority:** CRITICAL

#### WHY

The account is currently spending ~$8,000/year on competitor brand terms (Nature's Finest, Created By Nature, American Meadows, Ernst Seeds, etc.) and irrelevant queries (chicken feed, home depot, tractor supply, amazon). These searches have near-zero ROAS. The 483 negative keywords in the paste list cover:

- **Competitor brands** (153 terms): Nature's Finest ($3,472 wasted), Created By Nature ($1,636 wasted), American Meadows, Barenbrug, Baker Creek, Hancock Seed, Ernst Seeds, etc.
- **Retail/marketplace terms** (45+ terms): amazon, home depot, tractor supply, walmart, costco, lowes
- **Off-topic queries** (200+ terms): chicken feed (not seed), fertilizer, sod, turf rolls, lawn mower, weed killer, soil, mulch
- **DIY/informational intent** (80+ terms): how to, what is, youtube, reddit, near me

#### WHAT

Create a shared negative keyword list and apply it to all active campaigns.

#### WHERE (Navigation)

1. Go to [ads.google.com](https://ads.google.com)
2. Click **Tools** (wrench icon, top right)
3. Under **Shared library**, click **Negative keyword lists**
4. Click the **blue + button** to create a new list
5. Name it: **"Competitor Brands & Irrelevant Terms - Audit 2026"**
6. Open the file `negative_keywords_paste_list.txt` from the implementation folder
7. **Select all 483 keywords** and copy them
8. Paste into the keyword text box (one keyword per line is already formatted)
9. Click **Save**
10. After saving, select the list you just created
11. Click **Apply to campaigns**
12. Select **ALL active campaigns** (currently 6 enabled: Shopping Catch All, PMAX Catch All, Search Animal Seed, Search Brand ROAS, PMAX Search, Search Pasture Exact)
13. Click **Apply**

#### EXPECTED IMPACT

- Immediate savings of ~$8,000/year in pure waste (competitor terms)
- Additional ~$3--5K/year saved on off-topic terms (chicken feed, retail, informational)
- Total estimated savings: **$11--13K/year**
- ROAS improvement across all campaigns as budget stops leaking to non-converting queries

#### FILES REFERENCED

- `negative_keywords_paste_list.txt` -- 483 keywords, one per line, ready to paste
- `negative_keywords_competitors.csv` -- Detailed breakdown with spend, conversions, and ROAS for each competitor term (for your records)
- `negative_keywords_irrelevant.csv` -- Detailed breakdown of off-topic terms with spend data

#### VERIFICATION

1. After applying, go to each active campaign > **Keywords** > **Negative keywords**
2. Confirm the shared list appears under "Using lists"
3. Wait 7 days, then run a **Search terms report** (Campaigns > Insights & reports > Search terms)
4. Confirm that none of the blocked terms appear in new search term data
5. Compare week-over-week CPA -- it should decrease

---

### Step 3: Audit All Hidden Conversion Actions

**Time:** 1 hour
**Priority:** HIGH

#### WHY

Over 4 years, the account has accumulated **45 total conversion actions**, of which **20 are purchase-type**. In Q1 2024, seven purchase-related actions fired simultaneously. Even if they are marked as "secondary," their existence creates noise. More critically, there may be other actions (like "Begin checkout") that are silently included in the primary Conversions column and corrupting Smart Bidding.

The dominant purchase tracking has changed 5 times:
- 2022: Universal Analytics "Transactions"
- 2023: Profit Metrics "PM Revenue - Browser"
- 2024: Mix of PM + GA4 + WooCommerce
- 2025--2026: "Purchase" (Data-Driven)

Each transition created learning-period disruptions.

#### WHAT

Review every conversion action. Ensure only ONE legitimate purchase action is "Included in Conversions." Mark everything else as secondary or remove it.

#### WHERE (Navigation)

1. Go to [ads.google.com](https://ads.google.com)
2. Click **Goals** > **Conversions** > **Summary**
3. You will see all conversion actions listed
4. For EACH action, check:
   - **Is "Include in Conversions" set to Yes?** If so, is this the one legitimate purchase action you want Smart Bidding to optimize toward?
   - **Is it still firing?** Check the "Status" column. If it says "No recent conversions" or "Inactive," it is stale.
   - **Is it a duplicate?** Multiple purchase actions from different tracking systems (GA4, Profit Metrics, WooCommerce plugin) should NOT all be included.

5. The ONLY action that should have "Include in Conversions = Yes" for purchase tracking is: **"Purchase" (the current Data-Driven attribution one)**
6. For all others:
   - Click the action name
   - Click **Edit settings**
   - Set "Include in 'Conversions'" to **No**
   - Click **Save**

#### What to Look For Specifically

| Action Type | Expected Status | If Wrong |
|---|---|---|
| Purchase (Data-Driven) | Include = Yes | Keep as-is |
| Begin checkout | Include = No | You fixed this in Step 1 |
| PM Revenue - Browser | Include = No | Set to No if still Yes |
| GA4 Transactions | Include = No | Set to No if still Yes |
| WooCommerce Purchase | Include = No | Set to No if still Yes |
| Page view actions | Include = No | Set to No if still Yes |
| Add to cart actions | Include = No | Set to No if still Yes |

#### EXPECTED IMPACT

- Clean bidding signals: Smart Bidding will optimize on exactly one conversion event
- Eliminates double/triple counting that inflates reported performance
- More predictable CPA trends going forward

#### FILES REFERENCED

- `FULL_AUDIT_REPORT.md` -- Section 7: Conversion Tracking Issues #2 and #3

#### VERIFICATION

1. After cleanup, go to **Goals** > **Conversions** > **Summary**
2. Count how many actions show "Yes" in the "Include in Conversions" column
3. There should be exactly **ONE** purchase action with Include = Yes
4. Monitor conversion volume over the next 2 weeks -- it should stabilize and reflect real purchase behavior

---

## WEEK 2: Structural Improvements (Tier 2)

These require more setup but unlock significant budget savings and revenue opportunities.

---

### Step 4: Clean the Product Feed (Exclude Zero-Conversion Products)

**Time:** 2--4 hours
**Priority:** HIGH

#### WHY

**2,825 products received ad spend but generated zero conversions.** That is $33,004 in pure waste. These are mostly low-demand individual species, obscure variants, and variant-level SKUs that dilute budget away from proven winners. Every dollar spent on a zero-conversion product is a dollar that could have gone to White Dutch Clover (8.81x ROAS) or a forage mix (16--29x ROAS).

Additionally, there are **513 products with sub-1x ROAS** -- products that technically converted but cost more to advertise than they generated in revenue.

#### WHAT

Exclude the worst-performing products from your Shopping and PMax campaigns using either Google Merchant Center feed rules or campaign-level product exclusions.

#### WHERE (Navigation) -- Option A: Google Merchant Center Feed Rules

1. Go to [merchants.google.com](https://merchants.google.com)
2. Click **Products** > **Feeds** > select your primary feed
3. Click **Feed rules**
4. Create a new rule:
   - **Condition:** Product ID is in list
   - **Action:** Set `excluded_destination` to `Shopping_ads, Free_listings`
5. Upload the IDs from `product_exclusion_ids.txt` (2,825 IDs)

#### WHERE (Navigation) -- Option B: Campaign-Level Product Groups (Faster)

1. Go to [ads.google.com](https://ads.google.com)
2. Open **Shopping | Catch All** campaign
3. Click **Product groups**
4. Subdivide by **Item ID**
5. Manually exclude IDs, or create a supplemental feed in Merchant Center that sets `custom_label_0 = "exclude"` for the 2,825 products, then exclude by custom label in the campaign

#### Option C: Supplemental Feed (Most Scalable)

1. Create a CSV with two columns: `id` and `custom_label_0`
2. Set `custom_label_0 = "zero_conv_exclude"` for all 2,825 product IDs
3. Upload as a supplemental feed in Merchant Center
4. In Google Ads campaigns, subdivide product groups by `custom_label_0`
5. Set bid to $0.01 or exclude the "zero_conv_exclude" group entirely

#### EXPECTED IMPACT

- **$33,004/year saved** in wasted spend on zero-conversion products
- Remaining budget is redistributed to products that actually convert
- ROAS should improve 0.3--0.5x across Shopping/PMax campaigns

#### FILES REFERENCED

- `zero_conversion_products.csv` -- Full list of 2,825 products with spend data (columns: Item ID, Title, Type L1, Type L2, Spend, Clicks, Conversions, Revenue, ROAS)
- `product_exclusion_ids.txt` -- 2,825 product IDs only, one per line, ready to paste or upload
- `sub_1x_roas_products.csv` -- 513 additional products with sub-1x ROAS (consider these for a second-wave exclusion)

#### VERIFICATION

1. After implementing, wait 7 days
2. Go to **Shopping | Catch All** > **Product groups**
3. Confirm excluded products show $0.00 spend for the past 7 days
4. Check campaign-level ROAS -- it should be trending up
5. Run a products report (Reports > Predefined > Shopping > Products) and confirm no excluded IDs are getting impressions

---

### Step 5: Create Dedicated Forage Mix Campaigns

**Time:** 4 hours
**Priority:** HIGH -- this is the biggest revenue opportunity

#### WHY

Forage mixes for specific animals (sheep, goat, horse, cattle, poultry, alpaca) are generating **16--29x ROAS** on minimal spend. They are buried inside the "catch-all" campaigns where Google's algorithm has no incentive to prioritize them over higher-volume (but lower-ROAS) products. Creating dedicated campaigns gives you direct budget control over these winners.

Top performers being starved of budget:

| Product | Current Spend | Revenue | ROAS |
|---|---|---|---|
| SW Desert Goat Forage | $122 | $3,515 | **28.9x** |
| PNW Sheep Forage | $173 | $4,451 | **25.7x** |
| GL/NE Sheep Forage | $510 | $9,627 | **18.9x** |
| Southern Sheep Forage | $312 | $5,186 | **16.7x** |
| GL/NE Goat Forage | $178 | $2,883 | **16.2x** |
| S-AT Horse Forage | $645 | $7,942 | **12.3x** |

#### WHAT

Create 2--3 new campaigns specifically for forage/animal products:

**Campaign 1: Shopping | Forage Mixes (High ROAS)**
- Budget: $150--200/day (reallocated from catch-all)
- Bidding: Target ROAS at 8x (conservative, lets the algorithm find the best products)
- Products: All forage mixes (sheep, goat, horse, cattle, poultry, alpaca, dairy cow)
- Use `forage_animal_products.csv` to identify the 1,130 forage products

**Campaign 2: Search | Animal Forage (Exact + Phrase)**
- Budget: $100--150/day
- Bidding: Max Conversion Value
- Keywords from `exact_match_candidates.txt`: "goat pasture seed mix", "sheep forage seed mix", "cattle pasture seed", "horse grass seed", "alpaca pasture seed", etc.
- Use exact match for the top 30 proven converters, phrase match for the rest

#### WHERE (Navigation) -- Creating a Shopping Campaign

1. Go to [ads.google.com](https://ads.google.com)
2. Click **+ New campaign**
3. Select **Sales** as the goal
4. Select **Shopping** as the campaign type
5. Name it: **"Shopping | Forage Mixes (High ROAS)"**
6. Set daily budget: **$175**
7. Bidding: **Target ROAS** at **800%** (8x)
8. In product groups, subdivide by **Product Type Level 2**
9. Include only groups containing: horse, sheep, goat, cattle, poultry, alpaca, llama, dairy cow, beef, forage, tortoise
10. Exclude everything else

#### WHERE (Navigation) -- Creating a Search Campaign

1. Click **+ New campaign**
2. Select **Sales** > **Search**
3. Name it: **"Search | Animal Forage (Exact)"**
4. Set daily budget: **$125**
5. Bidding: **Maximize conversion value**
6. Create ad groups by animal type:
   - **Ad Group: Goat Forage** -- keywords: [goat pasture seed mix], [goat forage seed mix], [best seed for goat pasture], [best pasture grass for goats]
   - **Ad Group: Sheep Forage** -- keywords: [sheep pasture seed mix], [sheep forage seed mix], [pasture mix for sheep], [best pasture for sheep]
   - **Ad Group: Horse Forage** -- keywords: [best pasture seed for horses], [horse grass seed], [best grass seed for horse pastures], [winter pasture grass for horses]
   - **Ad Group: Cattle Forage** -- keywords: [cattle pasture seed], [pasture seed for cattle], [grass seed for cattle], [beef pasture seed mix]
   - **Ad Group: Poultry/Chicken** -- keywords: [chicken pasture seed], [poultry pasture seed], [forage for chickens], [grass seed mix for chickens]
7. Add the shared negative keyword list from Step 2

#### Budget Reallocation

Reduce the catch-all campaigns to free up budget:

| Campaign | Current Budget | New Budget | Freed |
|---|---|---|---|
| Shopping Catch All | $1,100/day | $850/day | $250/day |
| PMAX Catch All | $760/day | $660/day | $100/day |
| **New: Shopping Forage** | $0 | **$175/day** | -- |
| **New: Search Forage** | $0 | **$125/day** | -- |
| **Net change** | | | **$50/day saved** |

#### EXPECTED IMPACT

- If forage mixes maintain even half their historical ROAS (8--15x) at 5--10x current spend, that is **$50--100K in additional revenue**
- Minimum estimated incremental revenue: $50K/year
- Improved account-level ROAS by 0.3--0.5x

#### FILES REFERENCED

- `forage_animal_products.csv` -- 1,130 forage/animal products with full performance data
- `high_roas_underinvested.csv` -- 542 high-ROAS products getting minimal spend
- `star_products.csv` -- 29 proven winners at scale (>$5K revenue, >4x ROAS)
- `exact_match_candidates.txt` -- 259 keyword candidates for Search campaigns
- `budget_reallocation_summary.txt` -- Full budget reallocation analysis with Section 3 on forage products

#### VERIFICATION

1. After 14 days, compare the new forage campaigns' ROAS to the catch-all campaigns
2. Check that forage product spend has increased (compare to `forage_animal_products.csv` baseline)
3. Monitor the catch-all campaigns for any ROAS changes (should improve as low-ROAS products get less budget)
4. Run a products performance report filtered to forage mix products

---

### Step 6: Apply Mobile Bid Adjustments

**Time:** 30 minutes
**Priority:** MEDIUM-HIGH

#### WHY

Mobile devices consume **63% of total ad spend** but deliver **18% lower ROAS** than desktop (3.50x vs 4.28x). In 2026, tablet ROAS has dropped to 1.92x. The account is over-allocated to mobile at the expense of more efficient desktop traffic. A -15% to -20% mobile bid adjustment would save an estimated **$50--70K/year** in lost efficiency.

| Device | % of Spend | ROAS | Action |
|---|---|---|---|
| Mobile | 63% | 3.50x | Reduce bids -15% to -20% |
| Desktop | 38% | 4.28x | No change (or slight increase) |
| Tablet | 2% | 1.92x (2026) | Reduce bids -30% to -40% |

#### WHAT

Apply device-level bid adjustments to all Search and Shopping campaigns. (PMax campaigns do not support device bid adjustments -- Google controls that automatically.)

#### WHERE (Navigation)

For **each** Search and Shopping campaign:

1. Go to [ads.google.com](https://ads.google.com)
2. Open the campaign (e.g., **Shopping | Catch All**)
3. Click **Devices** in the left sidebar (under "Content")
4. You will see three rows: Computers, Mobile phones, Tablets
5. Click the **Bid adj.** column next to **Mobile phones**
6. Select **Decrease** and enter **18%**
7. Click the **Bid adj.** column next to **Tablets**
8. Select **Decrease** and enter **35%**
9. Click **Save**

Repeat for:
- Shopping | Catch All
- Search | Animal Seed (Broad)
- Search | Brand | ROAS
- Search | Pasture | Exact
- Any new campaigns you create

**Note:** PMax campaigns (PMAX Catch All, PMAX Search) do NOT support device bid adjustments. Google controls device allocation in PMax.

#### EXPECTED IMPACT

- Shifts ~$50--70K/year of spend from mobile to desktop where conversion rates are higher
- Conservative ROAS improvement of 0.2--0.3x across adjusted campaigns
- Desktop should capture more impression share and budget

#### FILES REFERENCED

- `FULL_AUDIT_REPORT.md` -- Section 6: Device & Geo Performance

#### VERIFICATION

1. After 14 days, go to each campaign > **Devices**
2. Confirm the bid adjustments show -18% for Mobile and -35% for Tablet
3. Compare device-level ROAS before and after (use the date comparison feature)
4. Desktop share of spend should increase from ~38% toward 45--50%

---

### Step 7: Consolidate Pasture Seed Landing Pages

**Time:** 1 hour (may require web dev)
**Priority:** MEDIUM

#### WHY

Two URLs are splitting traffic for pasture seed:
- `/products/pasture-seed/` (WooCommerce shop category)
- `/pasture-seed/` (standalone page)

This splits conversion signals across two destinations, making it harder for Google to learn which one converts better. It also fragments your data in Google Analytics.

Additionally, `get.naturesseed.com` (a subdomain) received 17,220 clicks at only 2.83x ROAS. If this is a landing page builder (Unbounce, etc.), it may be underperforming vs the main domain.

#### WHAT

1. Pick ONE canonical URL for pasture seed traffic (recommendation: `/products/pasture-seed/` since it is the WooCommerce category page with full product listings)
2. Set up a 301 redirect from `/pasture-seed/` to `/products/pasture-seed/`
3. Update all ad final URLs that point to `/pasture-seed/` to use `/products/pasture-seed/`
4. Evaluate whether `get.naturesseed.com` should continue receiving ad traffic, or if those ads should point to the main domain

#### WHERE (Navigation) -- Updating Ad URLs

1. In Google Ads, go to **Campaigns** > select a campaign
2. Click **Ads** in the left sidebar
3. For each ad using `/pasture-seed/` as the final URL:
   - Click the ad to edit
   - Change Final URL to `https://www.naturesseed.com/products/pasture-seed/`
   - Save

#### WHERE (Navigation) -- Setting Up 301 Redirect

This needs to be done on the WooCommerce/WordPress side:
1. Install or use an existing redirect plugin (e.g., Redirection, Yoast SEO Premium)
2. Create a 301 redirect: `/pasture-seed/` --> `/products/pasture-seed/`

#### EXPECTED IMPACT

- Consolidates conversion data, helping Smart Bidding optimize faster
- Should improve pasture seed campaign ROAS by 0.1--0.3x
- Cleaner analytics and reporting

#### FILES REFERENCED

- `FULL_AUDIT_REPORT.md` -- Section 5: Landing Page Issues

#### VERIFICATION

1. Visit `naturesseed.com/pasture-seed/` in a browser -- it should redirect to `/products/pasture-seed/`
2. In Google Ads, search for ads with the old URL -- none should remain
3. Check Google Search Console for any crawl errors on the old URL

---

### Step 8: Pause the Heartland Collection

**Time:** 15 minutes
**Priority:** MEDIUM

#### WHY

The Heartland Collection products have a combined **0.29x ROAS** -- spending $2,732 to generate only $791 in revenue. This is a direct loss. The top Heartland product (Hybrid Forage Brassica, `gla_355806`) spent $817 for $236 in revenue.

#### WHAT

Exclude all Heartland Collection products from Shopping and PMax campaigns.

#### WHERE (Navigation)

1. Go to [ads.google.com](https://ads.google.com)
2. Open **Shopping | Catch All**
3. Click **Product groups**
4. Subdivide by **Product Type L1** (or Brand if available)
5. Find the **"heartland collection"** group
6. Set its bid to **Excluded** (click the bid and select "Exclude")
7. Repeat for **PMAX | Catch All** (in Asset Groups > Listing Groups)

If Heartland products do not appear as a separate product type subdivision:
1. Use Merchant Center to add `custom_label_1 = "heartland_exclude"` to all Heartland products
2. Then exclude that custom label group in your campaigns

#### EXPECTED IMPACT

- Saves ~$2,700/year in pure waste
- Prevents these products from consuming impression share that should go to winners

#### FILES REFERENCED

- `sub_1x_roas_products.csv` -- Heartland products appear near the top of this list
- `zero_conversion_products.csv` -- Several Heartland items are here too

#### VERIFICATION

1. After 7 days, filter the Products report by "heartland"
2. Confirm $0 spend on all Heartland items
3. Check that overall campaign ROAS ticked up

---

## MONTH 2: Strategic Shifts (Tier 3)

These are larger structural changes that require more planning and monitoring.

---

### Step 9: Build Regional Campaigns

**Time:** 8 hours
**Priority:** MEDIUM

#### WHY

Regional products massively outperform national averages, but they receive almost no dedicated budget:

| Region | ROAS | Current Spend | Gap |
|---|---|---|---|
| Southwest Desert | **15.11x** | $297 | Almost zero budget |
| Great Lakes/NE | **12.03x** | $533 | Almost zero budget |
| Pacific Northwest | **11.66x** | $2,021 | Underinvested |
| National (catch-all) | **4.30x** | $301,021 | Where all the money goes |

The historical account tried hyper-regional campaigns ($10--17/day budgets) which were too fragmented. The sweet spot is 3--4 regional campaigns with meaningful budgets.

#### WHAT

Create regional Shopping or PMax campaigns that target the three highest-ROAS regions:

**Campaign 1: Shopping | Pacific Northwest**
- Budget: $75--100/day
- Products: Filter by product title or type containing "Pacific Northwest", "PNW"
- Geo targeting: WA, OR, ID, MT (layer on top of product filter)

**Campaign 2: Shopping | Great Lakes & Northeast**
- Budget: $50--75/day
- Products: Filter by "Great Lakes", "New England", "GL/NE", "Northeast"
- Geo targeting: MI, WI, MN, OH, PA, NY, VT, NH, ME, MA, CT, RI

**Campaign 3: Shopping | Southwest Desert**
- Budget: $30--50/day
- Products: Filter by "Southwest Desert", "SW Desert"
- Geo targeting: AZ, NM, NV, UT (southern), West TX

**Important:** When creating these campaigns, exclude these products from the catch-all campaigns to avoid internal competition. Use product-type or custom-label subdivisions.

#### WHERE (Navigation)

1. In Google Ads, click **+ New campaign** > **Sales** > **Shopping**
2. Name it per the above
3. Set daily budget and bidding (Target ROAS at 600--800%)
4. Under **Settings** > **Locations**, set the geo targets
5. In **Product groups**, filter to only regional products
6. In the catch-all Shopping campaign, exclude these same products

#### EXPECTED IMPACT

- If these regions maintain even 6--8x ROAS at 5--10x current spend: **$50K+ additional revenue**
- Minimum estimated: $30K incremental at conservative scaling

#### FILES REFERENCED

- `high_roas_underinvested.csv` -- Many PNW, GL/NE, and SW Desert products appear here
- `forage_animal_products.csv` -- Regional forage mixes sorted by region
- `star_products.csv` -- PNW and GL/NE products dominate the star list
- `budget_reallocation_summary.txt` -- Section 1 (Hidden Gems) and Section 2 (Stars) show regional breakdowns

#### VERIFICATION

1. After 21 days, compare regional campaign ROAS to the catch-all
2. Check that regional products are getting more impressions and clicks than before
3. Monitor the catch-all campaign to ensure its ROAS improves as well (since low-performing products were removed)

---

### Step 10: Implement Seasonal Budget Pacing

**Time:** Ongoing (set up quarterly calendar)
**Priority:** MEDIUM

#### WHY

The account currently ramps spend aggressively in Q1 (spring planting season) when ROAS is at its worst (2.6--3.4x), while pulling back in Q3 when ROAS peaks (3.5--4.0x). This is backwards. Every dollar spent in Q3 generates 30% more revenue than the same dollar spent in Q1.

| Quarter | Current Pattern | Better Pattern |
|---|---|---|
| Q1 (Jan-Mar) | PEAK spend, WORST ROAS | Moderate spend, focus on exact match + brand |
| Q2 (Apr-May) | High spend | Maintain -- decent efficiency |
| Q3 (Jul-Sep) | Reduced spend, BEST ROAS | INCREASE spend -- best efficiency window |
| Q4 (Oct-Dec) | Low spend | Low spend -- correct |

#### WHAT

1. Set a quarterly budget calendar
2. Q1: Cap budgets at 85% of current peak levels. Focus on exact match and brand campaigns. Limit broad match expansion.
3. Q3: Increase budgets by 20--30% above current Q3 levels. This is when the audience is most responsive and competition is lower.
4. Use Google Ads **Seasonality adjustments** for peak periods.

#### WHERE (Navigation) -- Setting Seasonality Adjustments

1. Go to [ads.google.com](https://ads.google.com)
2. Click **Tools** > **Bidding** > **Seasonality adjustments**
3. Click **+ New seasonality adjustment**
4. Set the date range for expected high-performance periods (e.g., July 15 -- September 30)
5. Set expected conversion rate change to **+15%**
6. Apply to all campaigns

#### EXPECTED IMPACT

- Shifting 10--15% of Q1 budget to Q3 could improve annual ROAS by 0.2--0.4x
- Estimated additional revenue: $20--40K/year from better seasonal allocation

#### FILES REFERENCED

- `FULL_AUDIT_REPORT.md` -- Section 2: Seasonality Pattern table

#### VERIFICATION

1. Compare quarter-over-quarter ROAS to the previous year
2. Q3 ROAS should exceed previous Q3 due to higher budget in the efficient period
3. Q1 ROAS should improve (or hold) due to tighter budget discipline

---

### Step 11: Move from Catch-All to Segmented PMax

**Time:** 4--6 hours
**Priority:** MEDIUM

#### WHY

The two catch-all campaigns (Shopping Catch All + PMAX Catch All) consume **71% of total budget** with no product/category segmentation. This makes it impossible to:
- Know which product categories are profitable vs unprofitable
- Control budget allocation between pasture, lawn, wildflower, specialty
- Set different ROAS targets for different categories (forage mixes deserve a higher budget; lawn seed deserves a lower one)

#### WHAT

Replace the catch-all PMax with 3--4 segmented PMax campaigns:

**PMax | Pasture & Forage (excl. dedicated forage campaign)**
- Budget: $400/day
- Asset groups with pasture-focused creative and headlines
- Exclude products already in the dedicated Forage campaign (Step 5)

**PMax | Lawn & Turf**
- Budget: $150/day
- Asset groups focused on lawn, turf, grass seed
- Star products: White Dutch Clover, Microclover, Fine Fescue, Buffalograss

**PMax | Wildflower & Specialty**
- Budget: $100/day
- Wildflower mixes, erosion control, specialty blends
- Note: Wildflower search ads historically underperform (sub-1x ROAS), but Shopping/PMax may do better

**PMax | Brand Defense**
- Budget: $50/day
- Brand terms only
- This protects your brand ROAS (19.8x) from being diluted by non-brand traffic in PMax

#### WHERE (Navigation)

1. For each new PMax campaign:
   - Click **+ New campaign** > **Sales** > **Performance Max**
   - Set daily budget per above
   - Bidding: **Maximize conversion value** with optional Target ROAS
   - Create relevant asset groups (headlines, descriptions, images relevant to the category)
   - In **Listing Groups**, filter products to the relevant category using Product Type subdivisions

2. After creating all segmented campaigns, **pause** the old PMAX Catch All campaign

#### EXPECTED IMPACT

- Visibility into category-level performance (you can see exactly what lawn vs pasture vs wildflower is doing)
- Ability to reallocate budget away from underperformers (e.g., reduce wildflower budget if ROAS stays low)
- Estimated ROAS improvement: 0.3--0.5x from targeted budget allocation

#### FILES REFERENCED

- `budget_reallocation_summary.txt` -- Full product breakdown by performance tier
- `star_products.csv` -- Which products to prioritize in each campaign
- `high_roas_underinvested.csv` -- Products that need more spend (assign to the right campaign)

#### VERIFICATION

1. After 21 days, compare total account ROAS to pre-segmentation baseline
2. Each campaign should have distinct ROAS that you can compare
3. Confirm that star products are getting MORE spend (not less) after segmentation
4. Verify no products are falling through the cracks (appearing in no campaign)

---

### Step 12: Add Exact Match Keywords for Proven Search Terms

**Time:** 2 hours
**Priority:** MEDIUM

#### WHY

Exact match keywords deliver **13.08x ROAS** vs 2.49x for phrase and 2.12x for broad. The account currently spends 76% of keyword budget on phrase + broad match but gets only 39% of conversion value from them. Adding exact match keywords for proven high-converting search terms lets you bid more aggressively on queries you know work.

Top non-brand search terms that deserve exact match keywords:

| Search Term | Revenue | ROAS |
|---|---|---|
| cattle pasture seed | $4,648 | **23.4x** |
| organic pasture seed | $3,837 | **13.6x** |
| goat pasture seed mix | $8,149 | **9.6x** |
| sheep pasture seed mix | $4,041 | **5.7x** |
| pasture grass seed | $10,986 | **4.4x** |

#### WHAT

1. Add exact match keywords from `exact_match_candidates.txt` to your Search campaigns
2. Prioritize the top 50 by proven conversion data
3. Create a new ad group in each relevant campaign for exact match terms

#### WHERE (Navigation)

1. Open **Search | Animal Seed (Broad)** campaign
2. Click **Keywords** > **Search keywords** > **+ button**
3. Create a new ad group: **"Animal Forage - Exact Match"**
4. Open `exact_match_candidates.txt`
5. Copy the top 50--100 keywords
6. When pasting, wrap each in square brackets: `[goat pasture seed mix]`, `[cattle pasture seed]`, etc.
7. Alternatively, add them to the new Search | Animal Forage campaign from Step 5

Also create an exact match ad group in **Search | Pasture | Exact**:
1. Add pasture-specific exact match terms: `[pasture seed]`, `[pasture grass seed]`, `[pasture seed for cattle]`, etc.

#### EXPECTED IMPACT

- Exact match captures the highest-intent traffic at the best ROAS
- Estimated incremental revenue: $15--25K/year from better keyword targeting
- Reduces reliance on broad match for proven terms

#### FILES REFERENCED

- `exact_match_candidates.txt` -- 259 keyword candidates extracted from top-converting search terms, one per line, ready to copy

#### VERIFICATION

1. After 14 days, go to **Keywords** > sort by match type
2. Compare exact match ROAS to broad/phrase ROAS within the same campaign
3. Exact match should be 3--5x more efficient
4. Check the Search Terms report to confirm exact match keywords are triggering for the intended queries

---

## ONGOING: Tier 4 -- Continuous Optimization

These are not one-time tasks but recurring processes that prevent the account from degrading again.

---

### Monthly: Search Term Review Process

**Frequency:** First Monday of each month
**Time:** 1--2 hours

#### Process

1. Go to **Campaigns** > **Insights & reports** > **Search terms**
2. Set date range to the past 30 days
3. Sort by **Cost** (highest first)
4. Review the top 100 search terms
5. For each term, ask:
   - Is this relevant to Nature's Seed? (If not --> add as negative)
   - Is this a competitor name? (If yes --> add as negative)
   - Is this a retail/marketplace query? (amazon, home depot, etc. --> add as negative)
   - Does it have >$20 spend and 0 conversions? (Consider adding as negative)
   - Does it have high ROAS? (Consider adding as exact match keyword)
6. Add new negatives to the shared negative keyword list from Step 2
7. Add new winners as exact match keywords

#### Key Metrics to Track Monthly

| Metric | Target | Red Flag |
|---|---|---|
| Account ROAS | >4.0x | Below 3.0x |
| Cost/Conversion | <$30 | Above $45 |
| % Brand Conversions | <50% | Above 65% (too brand-dependent) |
| Zero-conv product spend | <$500/month | Above $2,000/month |
| Mobile ROAS gap vs Desktop | <15% | Above 25% |

---

### Quarterly: Conversion Tracking Audit

**Frequency:** First week of each quarter
**Time:** 1 hour

#### Process

1. Go to **Goals** > **Conversions** > **Summary**
2. Review every conversion action:
   - Is "Include in Conversions" still correctly set? (Only ONE purchase action should be Yes)
   - Are any new conversion actions auto-created by tags/integrations? (Common with WooCommerce plugin updates)
   - Is the "Status" column showing "Recording" for your primary action? If not, tracking may be broken.
3. Check the **Conversions (by time)** report:
   - Is the primary purchase action accounting for 90%+ of conversion value?
   - Are any zombie actions showing unexpected volume?
4. Compare Google Ads reported conversions to WooCommerce actual orders for the same period. They should be within 10% of each other. If Google Ads shows 50%+ more conversions, a secondary action is leaking into the primary count.

---

### Quarterly: Product Feed Health Check

**Frequency:** Every quarter
**Time:** 2 hours

#### Process

1. Run a Products performance report in Google Ads (Reports > Predefined > Shopping > Products)
2. Export to CSV
3. Filter for products with:
   - **$50+ spend and 0 conversions** (new candidates for exclusion)
   - **Sub-1x ROAS with $100+ spend** (consider pausing)
   - **10x+ ROAS with <$50 spend** (new hidden gems to invest in)
4. Update the supplemental feed or exclusion lists
5. Cross-reference with WooCommerce: are there new products that should be in the feed? Are there discontinued products still getting spend?

---

### Quarterly: Competitive Landscape Check

**Frequency:** Every quarter
**Time:** 30 minutes

#### Process

1. Go to **Campaigns** > **Insights & reports** > **Auction insights**
2. Check who is competing for your top keywords
3. Note any new competitors entering the space
4. Check if your impression share is declining on key terms
5. Adjust bids or budgets if a new competitor is pushing you off the page for high-ROAS terms

---

## SUMMARY: Implementation Timeline

| Week | Step | Time | Est. Annual Impact |
|---|---|---|---|
| **Week 1** | Step 1: Fix Begin Checkout | 5 min | $45--70K saved (bidding fix) |
| **Week 1** | Step 2: Add 483 Negative Keywords | 30 min | $11--13K saved |
| **Week 1** | Step 3: Audit All Conversions | 1 hr | Prevents future corruption |
| **Week 2** | Step 4: Clean Product Feed (2,825 products) | 2--4 hrs | $33K saved |
| **Week 2** | Step 5: Create Forage Mix Campaigns | 4 hrs | $50--100K new revenue |
| **Week 2** | Step 6: Mobile Bid Adjustments | 30 min | $50--70K efficiency gain |
| **Week 2** | Step 7: Consolidate Landing Pages | 1 hr | Improves conversion rate |
| **Week 2** | Step 8: Pause Heartland Collection | 15 min | $2.7K saved |
| **Month 2** | Step 9: Regional Campaigns | 8 hrs | $30--50K new revenue |
| **Month 2** | Step 10: Seasonal Budget Pacing | Ongoing | $20--40K efficiency gain |
| **Month 2** | Step 11: Segmented PMax | 4--6 hrs | $30--50K efficiency gain |
| **Month 2** | Step 12: Exact Match Keywords | 2 hrs | $15--25K new revenue |
| **Ongoing** | Monthly search term reviews | 1--2 hrs/mo | Prevents decay |
| **Ongoing** | Quarterly audits | 3--4 hrs/qtr | Prevents decay |

**Total estimated annual impact: $150--300K in additional revenue and/or saved waste**

---

## FILES IN THIS DIRECTORY -- Quick Reference

| File | Contents | Used In |
|---|---|---|
| `negative_keywords_paste_list.txt` | 483 negative keywords, one per line, ready to paste | Step 2 |
| `negative_keywords_competitors.csv` | Competitor search terms with spend/ROAS data | Step 2 (reference) |
| `negative_keywords_irrelevant.csv` | Off-topic search terms with spend/ROAS data | Step 2 (reference) |
| `zero_conversion_products.csv` | 2,825 products with spend but zero conversions | Step 4 |
| `product_exclusion_ids.txt` | 2,825 product IDs only, one per line | Step 4 |
| `sub_1x_roas_products.csv` | 513 products with sub-1x ROAS | Step 4, Step 8 |
| `forage_animal_products.csv` | 1,130 forage/animal products with performance data | Step 5, Step 9 |
| `high_roas_underinvested.csv` | 542 high-ROAS products getting minimal spend | Step 5, Step 9 |
| `star_products.csv` | 29 proven winners (>$5K revenue, >4x ROAS) | Step 5, Step 11 |
| `exact_match_candidates.txt` | 259 keyword candidates from top-converting searches | Step 5, Step 12 |
| `budget_reallocation_summary.txt` | Full budget analysis: hidden gems, stars, forage, underperformers | Step 5, Step 9, Step 11 |
| `analyze_shopping_products.py` | Script used to generate product performance data | Reference only |
| `extract_negatives.py` | Script used to extract negative keywords | Reference only |
| `extract_product_performance.py` | Script used to extract product performance | Reference only |

---

## IMPORTANT NOTES

1. **Allow Smart Bidding time to adjust.** After Steps 1 and 3 (conversion tracking fixes), Smart Bidding will need 2--3 weeks to recalibrate. ROAS may dip temporarily before improving. Do not make additional bidding changes during this period.

2. **Do not implement all 12 steps at once.** Follow the weekly sequence. Making too many changes simultaneously makes it impossible to attribute which change caused which result.

3. **Document every change.** Use Google Ads Change History (Tools > Change History) to track what was changed and when. This is critical for diagnosing future issues.

4. **The 2.67x ROAS in Q1 2026 is partially fake.** Because "Begin checkout" was inflating conversions, the real Q1 2026 ROAS might be closer to 1.5--2.0x. After fixing tracking, the numbers will look worse before they look better -- this is the true baseline.

5. **Brand vs Non-Brand balance.** 62% of conversions come from brand searches. This is healthy but means the account is somewhat dependent on existing brand awareness. The non-brand optimization in Steps 5, 9, and 12 is designed to grow the non-brand share profitably.
