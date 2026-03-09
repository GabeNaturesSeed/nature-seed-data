# Current Live State -- Google Ads Account
## Nature's Seed | naturesseed.com
### Audit Date: March 5, 2026
### Data Range: Last 3 months (Jan-Mar 2026) for performance; all-time for structure

---

**METHODOLOGY**: This audit examines ONLY what is currently ENABLED and serving traffic. Historical data is used solely for gap analysis (Section 10). Every metric in Sections 1-9 reflects the live, currently-running account state.

---

## 1. Live Campaign Inventory (What's On Right Now)

**6 enabled campaigns** with a combined daily budget of **$2,628/day ($78,840/month cap)**:

| Campaign Name | Type | Bidding Strategy | Daily Budget | Monthly Cap |
|---|---|---|---|---|
| **PMAX - Search** | Performance Max | Maximize Conv Value | $210 | $6,300 |
| **PMAX \| Catch all** | Performance Max | Maximize Conv Value | $760 | $22,800 |
| **Search \| Animal Seed (Broad) \| ROAS** | Search | Maximize Conv Value | $260 | $7,800 |
| **Search \| Brand \| ROAS** | Search | Maximize Conv Value | $220 | $6,600 |
| **Search \| Pasture \| Exact** | Search | Maximize Conversions | $78 | $2,340 |
| **Shopping \| Catch All.** | Shopping | Target ROAS | $1,100 | $33,000 |

**Structural observations:**
- 2 PMax campaigns (37% of budget) -- one general catch-all, one search-focused
- 3 Search campaigns (21% of budget) -- Brand, Animal/Pasture Broad, Pasture Exact
- 1 Shopping campaign (42% of budget) -- the single largest budget item at $1,100/day
- **No DSA campaigns active** (previously a major traffic source, all removed/paused)
- **No dedicated Grass Seed, Wildflower, or Lawn search campaigns** -- these categories rely entirely on PMax and Shopping
- **No dedicated California/Regional campaigns active** (previously significant)
- "Search | Pasture | Exact" uses Maximize Conversions (not Maximize Conv Value like the others) -- this means it optimizes for conversion count, not revenue. This may explain its lower ROAS vs. the others.

---

## 2. Live Ad Inventory (Every Enabled Ad with Its URL)

**39 unique enabled ads** across 6 campaigns. Full detail in `implementation/LIVE_enabled_ads_with_urls.csv`.

### By Campaign:

**Search | Brand | ROAS** (6 ads):
| Ad ID | Type | Final URL | Headline | All-Time Cost | ROAS |
|---|---|---|---|---|---|
| 578233647510 | RSA | https://naturesseed.com/ | Nature's Seed Quality Seed | $63,013 | 8.72 |
| 747838731525 | RSA | https://naturesseed.com/ | Save 40% on 500+ Seeds | $1,050 | 2.81 |
| 272079888904 | ETA | https://www.naturesseed.com/ | (expanded text) | $1,954 | 3.92 |
| 272079888901 | ETA | https://www.naturesseed.com/ | (expanded text) | $1,517 | 12.00 |
| 272079888907 | ETA | https://www.naturesseed.com/ | (expanded text) | $1,472 | 4.40 |

**Search | Pasture | Exact** (8 ads):
| Ad ID | Type | Final URL | Headline | All-Time Cost | ROAS |
|---|---|---|---|---|---|
| 771352317042 | RSA | /product/cattle-dairy-cow-pasture-mix-cold-warm-season | Cattle Pasture Seed | $4,584 | 2.60 |
| 771352317051 | RSA | /products/pasture-seed/poultry-forage-mix/ | Poultry Pasture Mix | $2,689 | 2.14 |
| 767882150044 | RSA | /products/pasture-seed/ | Buy Pasture Seed Online | $2,256 | 2.24 |
| 771352317045 | RSA | /products/pasture-seed/horse-pastures-seed/ | Horse Pasture Seeds | $1,418 | 3.10 |
| 771352317054 | RSA | /product/sheep-pasture-forage-mix-transitional | Sheep Pasture Seed | $823 | 2.87 |
| 771352317048 | RSA | /product/alpaca-llama-pasture-forage-mix/ | Alpaca Pasture Seed | $200 | 8.60 |
| 797303485619 | RSA | /products/wildflower-seed/ | Nature's Seed Wildflower Seed | $146 | 0.00 |
| 797195243664 | RSA | /products/grass-seed/twca-water-wise-sun-shade-mix/ | PNW Grass Seed Mixes | $66 | 3.95 |
| 797194961199 | RSA | /products/pasture-seed/timothy/ | Nature's Seed | $21 | 0.00 |
| 797304768224 | RSA | /products/clover-seed/ | Nature's Seed | $0 | -- |

**Search | Animal Seed (Broad) | ROAS** (19 ads):
Covers: Cattle (2), Horse (2), Wildflower (2), Poultry (2), Sheep (2), White Dutch Clover (2), Microclover (2), Pig (2), Alpaca (1), Llama (2), Goat (2), Bison (1), White Clover (1)

**Note:** The Llama, Goat, and Bison ad groups have 0 impressions/spend -- they appear set up but not receiving traffic.

**Search | Pasture | Exact** also has newer ad groups: Wildflowers, Regional/Lawn, Hay Seed, Clover -- all with minimal or zero spend so far.

---

## 3. Live Keyword Inventory (Every Enabled Keyword)

**39 unique enabled keywords** in the 3 Search campaigns. Full detail in `implementation/LIVE_enabled_keywords.csv`.

### Quality Score Distribution:
| QS | Count | % |
|---|---|---|
| 10 | 7 | 18% |
| 9 | 2 | 5% |
| 8 | 4 | 10% |
| 7 | 11 | 28% |
| 6 | 6 | 15% |
| 5 | 6 | 15% |
| No data | 3 | 8% |
| **Avg QS** | **7.0** | |

### Match Type Distribution:
- **BROAD**: 23 keywords (59%) -- all in Animal Seed (Broad) campaign
- **PHRASE**: 14 keywords (36%) -- across all Search campaigns
- **EXACT**: 2 keywords (5%) -- "natures seed" and a few others in Brand

### Top Spenders (Last 3 Months):

| # | Keyword | Match | 3M Cost | 3M Conv | 3M Revenue | 3M ROAS | QS |
|---|---|---|---|---|---|---|---|
| 1 | natures seed | EXACT | $1,047 | 93.4 | $21,576 | 20.61 | 10 |
| 2 | cattle forage seed | BROAD | $958 | 7.2 | $1,350 | 1.41 | 10 |
| 3 | horse pasture seed mix | BROAD | $949 | 4.0 | $615 | 0.65 | 7 |
| 4 | cattle grass seed | BROAD | $761 | 8.5 | $1,296 | 1.70 | 7 |
| 5 | wildflower seed | BROAD | $683 | 10.0 | $1,718 | 2.52 | 7 |

### Winners (ROAS > 5x, Spend > $5):

| Keyword | Match | Cost | Revenue | ROAS |
|---|---|---|---|---|
| natures seed | EXACT | $1,047 | $21,576 | 20.61 |
| dutch clover seed | BROAD | $204 | $2,104 | 10.29 |
| winter pasture seed mix for cattle | BROAD | $129 | $953 | 7.37 |
| naturesseed | EXACT | $86 | $493 | 5.74 |
| best pasture grass for pigs | BROAD | $19 | $179 | 9.22 |

### Money Losers (Spend > $10, ROAS < 1x) -- 24 keywords wasting money:

| Keyword | Match | Cost | Revenue | ROAS |
|---|---|---|---|---|
| horse pasture seed mix | BROAD | $949 | $615 | 0.65 |
| sheep forage seed mix | BROAD | $338 | $67 | 0.20 |
| best perennial wildflower seed mix | BROAD | $189 | $174 | 0.92 |
| pasture grass for sheep | EXACT | $134 | $1 | 0.01 |
| chicken pasture seed | BROAD | $124 | $69 | 0.56 |
| wildflower seeds | PHRASE | $121 | $0 | 0.00 |
| pasture grass seed mix | PHRASE | $112 | $49 | 0.44 |
| forage seed mix for chickens | BROAD | $95 | $20 | 0.21 |
| alpaca pasture seed | BROAD | $87 | $18 | 0.21 |

**Total wasted on money-loser keywords (last 3M): ~$2,300** on keywords returning less than $1 for every $1 spent.

---

## 4. Last 90 Days Performance by Campaign

### Monthly Breakdown (Jan-Mar 2026):

**PMAX - Search:**
| Month | Spend | Revenue | ROAS | Conv | CPA | Trend |
|---|---|---|---|---|---|---|
| Jan 2026 | $1,035 | $1,803 | 1.74 | 63.1 | $16.40 | |
| Feb 2026 | $4,275 | $10,016 | 2.34 | 43.0 | $99.50 | |
| Mar 2026* | $745 | $4,054 | 5.44 | 19.0 | $39.32 | IMPROVING |

**PMAX | Catch all:**
| Month | Spend | Revenue | ROAS | Conv | CPA | Trend |
|---|---|---|---|---|---|---|
| Jan 2026 | $1,730 | $8,592 | 4.97 | 40.0 | $43.27 | |
| Feb 2026 | $11,086 | $31,943 | 2.88 | 122.1 | $90.82 | |
| Mar 2026* | $2,643 | $6,668 | 2.52 | 49.6 | $53.22 | DECLINING |

**Search | Animal Seed (Broad) | ROAS:**
| Month | Spend | Revenue | ROAS | Conv | CPA | Trend |
|---|---|---|---|---|---|---|
| Jan 2026 | $1,453 | $5,464 | 3.76 | 27.5 | $52.85 | |
| Feb 2026 | $5,933 | $9,135 | 1.54 | 60.1 | $98.70 | |
| Mar 2026* | $554 | $465 | 0.84 | 6.1 | $91.00 | DECLINING -- CRITICAL |

**Search | Brand | ROAS:**
| Month | Spend | Revenue | ROAS | Conv | CPA | Trend |
|---|---|---|---|---|---|---|
| Jan 2026 | $1,034 | $5,979 | 5.78 | 24.8 | $41.66 | |
| Feb 2026 | $1,812 | $15,189 | 8.38 | 64.3 | $28.18 | |
| Mar 2026* | $236 | $2,959 | 12.55 | 15.6 | $15.10 | IMPROVING |

**Search | Pasture | Exact:**
| Month | Spend | Revenue | ROAS | Conv | CPA | Trend |
|---|---|---|---|---|---|---|
| Jan 2026 | $1,372 | $2,589 | 1.89 | 10.6 | $130.04 | |
| Feb 2026 | $1,520 | $5,127 | 3.37 | 32.2 | $47.13 | |
| Mar 2026* | $262 | $1,070 | 4.08 | 12.8 | $20.49 | IMPROVING |

**Shopping | Catch All.:**
| Month | Spend | Revenue | ROAS | Conv | CPA | Trend |
|---|---|---|---|---|---|---|
| Jan 2026 | $6,530 | $20,282 | 3.11 | 133.6 | $48.88 | |
| Feb 2026 | $19,234 | $44,358 | 2.31 | 321.4 | $59.84 | |
| Mar 2026* | $4,013 | $9,845 | 2.45 | 95.2 | $42.16 | IMPROVING |

*Mar 2026 is partial month (data through early March)

### Account Totals (Enabled Campaigns Only):

| Month | Total Spend | Total Revenue | Blended ROAS | Total Conv | CPA |
|---|---|---|---|---|---|
| Jan 2026 | $13,155 | $44,708 | 3.40 | 299.6 | $43.91 |
| Feb 2026 | $43,859 | $115,768 | 2.64 | 643.1 | $68.20 |
| Mar 2026* | $8,453 | $25,061 | 2.96 | 198.3 | $42.63 |

**Key observations:**
- February 2026 saw a major spend ramp (3.3x January) but ROAS dropped from 3.40 to 2.64
- Brand search is the most efficient campaign and keeps improving (5.78 -> 8.38 -> 12.55 ROAS)
- **Animal Seed (Broad) is in trouble**: ROAS dropped from 3.76 to 1.54 to 0.84 -- now below breakeven
- Shopping is the volume driver (~50% of spend) with steady but mediocre 2-3x ROAS
- PMAX Catch All declined from 4.97 to 2.52 ROAS -- may be cannibalizing Shopping

---

## 5. Last 90 Days Keyword Performance

### Summary Statistics:
- **Total live keywords**: 39
- **Keywords with spend**: 50 (some span multiple months/aggregations)
- **Total keyword spend (3M)**: ~$10,700
- **Winners (ROAS > 5x)**: 5 keywords driving $25,304 revenue on $1,486 spend
- **Money losers (ROAS < 1x)**: 24 keywords wasting ~$2,300 on $418 revenue

### Critical Issues:

**1. "horse pasture seed mix" (BROAD, $949 spend, 0.65 ROAS)**
This is the #3 keyword by spend but returns only $0.65 for every $1. The broad match is likely matching irrelevant queries. Consider pausing or switching to phrase/exact.

**2. "sheep forage seed mix" (BROAD, $338 spend, 0.20 ROAS)**
Only $67 in revenue on $338 spend. Terrible match quality.

**3. "pasture grass for sheep" has BOTH an EXACT ($134, 0.01 ROAS) and PHRASE ($41, 0.00 ROAS) variant -- both are money pits.**

**4. "wildflower seeds" (PHRASE, $121, 0.00 ROAS)**
Zero conversions. Too generic.

**5. 15 keywords with spend > $10 and ZERO conversions**
These include: arizona wildflower seed mix, bulk micro clover seed, chicken safe grass seed, pig pasture seed, alpaca grass seed, white clover grass seed, pasture grass seed for horses, white clover lawn, timothy grass seed, white clover grass, pasture seed for horses, california wildflower seeds, california native wildflower seeds.

Full detail in `implementation/LIVE_top_keywords.csv`.

---

## 6. Last 90 Days Search Term Analysis

**Quarter: Q1 2026 (Jan-Mar)**, enabled campaigns only.

### Top Wasted Search Terms (spend > $5, zero conversions): **637 terms, $8,038 wasted**

| # | Search Term | Cost | Clicks | Triggered By |
|---|---|---|---|---|
| 1 | horse pasture seed mix | $241 | 93 | Pasture Exact, Shopping, Animal Broad |
| 2 | native california grass seed | $139 | 9 | Brand, Shopping |
| 3 | white dutch clover | $102 | 101 | Shopping, Animal Broad |
| 4 | horse pasture grass seed | $69 | 17 | Pasture Exact, Shopping, Animal Broad |
| 5 | microclover seed | $64 | 27 | Shopping, Animal Broad |
| 6 | sheep pasture mix | $62 | 29 | Pasture Exact, Shopping, Animal Broad |
| 7 | pasture seed for cattle | $62 | 19 | Shopping, Animal Broad |
| 8 | bulk pasture seed | $56 | 15 | Shopping, Animal Broad |
| 9 | horse pasture mix | $53 | 14 | Pasture Exact, Shopping, Animal Broad |
| 10 | mini clover seed | $51 | 17 | Shopping, Animal Broad |

**Notable irrelevant search terms being matched:**
- "johnny seed" ($44) -- competitor/unrelated brand
- "granite seed" ($41) -- competitor brand
- "kentucky bluegrass" ($38) -- product they likely don't specialize in for Shopping
- "st augustine grass seed" ($32) -- warm season grass, may not be a core product
- "sustane 18 1 8" ($28) -- fertilizer brand
- "nature's seed phone number" ($25) -- info query, not purchase intent
- "bahia grass seed" ($38) -- may not be core
- "mycorrhizae" ($34) -- accessory product, low intent

Full list in `implementation/LIVE_wasted_search_terms.csv`.

### Top Converting Search Terms:

| Search Term | Cost | Conv | Revenue | ROAS |
|---|---|---|---|---|
| natures seed | $429 | 50.1 | $11,384 | 26.52 |
| nature's seed | $219 | 24.8 | $4,236 | 19.32 |
| nature seed | $246 | 10.6 | $3,279 | 13.34 |
| goat pasture seed mix | $103 | 4.2 | $2,891 | 28.02 |
| natureseed | $105 | 7.0 | $2,623 | 25.02 |
| native clover seeds | $0.62 | 1.0 | $1,922 | 3,100 |
| pasture seed | $162 | 5.1 | $955 | 5.92 |
| nature's seed company | $58 | 4.2 | $895 | 15.51 |
| kentucky bluegrass seed | $141 | 4.0 | $867 | 6.16 |
| pasture grass seed for horses | $84 | 1.0 | $869 | 10.38 |

**Brand terms dominate the top converters** (natures seed, nature's seed, natureseed, nature seed, nature's seed company = ~$22,200 combined revenue).

---

## 7. Live URL Issues (Only URLs That Are ACTUALLY Serving)

Full detail in `implementation/LIVE_url_issues.csv`.

### URLs Using www. Subdomain (Should Be naturesseed.com):

| URL | # Ads | All-Time Spend | Conversions |
|---|---|---|---|
| https://www.naturesseed.com/ | 3 (all ETAs in Brand) | $4,943 | 263.9 |

These 3 Expanded Text Ads use `www.naturesseed.com` instead of `naturesseed.com`. While redirects likely handle this, it is inconsistent and may cause tracking discrepancies.

### URLs Using Old Path Structure (no /products/ prefix):

These ads use legacy URL paths like `/product/slug` or `/pasture-seed/slug` instead of the current `/products/category/slug` pattern:

| URL | Campaign | All-Time Spend | Conversions | Issue |
|---|---|---|---|---|
| /product/cattle-dairy-cow-pasture-mix-cold-warm-season | Pasture Exact | $4,584 | 136.5 | /product/ not /products/ |
| /pasture-seed/cattle-pastures/beef-cattle-forage/ | Animal Broad | $1,808 | 20.9 | Old /pasture-seed/ path |
| /pasture-seed/horse-pastures/ | Animal Broad | $971 | 5.4 | Old /pasture-seed/ path |
| /product/sheep-pasture-forage-mix-transitional | Pasture Exact | $823 | 26.4 | /product/ not /products/ |
| /pasture-seed/sheep-pastures/ | Animal Broad | $683 | 14.4 | Old /pasture-seed/ path |
| /pasture-seed/alpaca-llama-pastures/ | Animal Broad | $262 | 4.6 | Old /pasture-seed/ path |
| /product/alpaca-llama-pasture-forage-mix/ | Pasture Exact + Animal Broad | $200 | 17.9 | /product/ not /products/ |
| /product/pig-pasture-forage-mix/ | Animal Broad | $151 | 8.0 | /product/ not /products/ |
| /product/big-game-food-plot-forage-mix/ | Animal Broad (Bison) | $0 | 0 | /product/ not /products/ |
| /pasture-seed/goat-pastures/ | Animal Broad (Goat) | $0 | 0 | Old /pasture-seed/ path |

**Total spend on old/mismatched URLs: ~$9,482 across 13 ads.**

These may still work via redirects, but should be verified and updated to canonical /products/ URLs to avoid redirect chains, ensure proper landing page tracking, and improve Quality Score.

---

## 8. Device Performance (Live Campaigns Only)

### Last 3 Months Aggregate:

| Device | Impressions | Clicks | Cost | Conv | Revenue | ROAS | CPA | CTR |
|---|---|---|---|---|---|---|---|---|
| **Mobile** | 3,088,641 | 40,466 | $39,750 | 751.7 | $106,351 | **2.68** | $52.88 | 1.31% |
| **Desktop** | 748,424 | 12,020 | $25,336 | 402.2 | $81,264 | **3.21** | $62.99 | 1.61% |
| **Tablet** | 62,886 | 779 | $895 | 14.0 | $1,787 | **2.00** | $63.87 | 1.24% |
| Connected TV | 405 | 0 | $3 | 0 | $0 | 0 | -- | 0% |

**Key findings:**
- **Mobile drives 61% of spend but only 57% of revenue** -- lower ROAS (2.68) vs Desktop (3.21)
- **Desktop has 20% higher ROAS than mobile** -- $3.21 vs $2.68
- **Tablet is underperforming** at 2.00 ROAS with high CPA ($63.87)
- Mobile gets 79% of impressions but only 66% of conversions -- potential landing page optimization opportunity

### Monthly Device Trends:
- Desktop ROAS declined: 3.11 (Jan) -> 3.38 (Feb) -> 2.58 (Mar)
- Mobile ROAS volatile: 3.65 (Jan) -> 2.25 (Feb) -> 3.48 (Mar)
- Tablet consistently weak: 1.89 -> 1.88 -> 2.90

---

## 9. Product Performance (Live Campaigns Only, Q1 2026)

603 product rows in Q1 2026 across enabled campaigns. Key findings:

### Top 10 Products by Revenue:

| Product | Cost | Revenue | ROAS |
|---|---|---|---|
| California Wildflower Seed Blend 5 Lb | $426 | $4,372 | 10.27 |
| White Dutch Clover Seed (large) | $1,843 | $4,091 | 2.22 |
| Transitional Pasture & Forage 50 Lb | $497 | $3,400 | 6.85 |
| Transitional Pasture & Forage 50 Lb (alt) | $330 | $2,864 | 8.68 |
| Buffalograss Lawn Seed | $445 | $1,961 | 4.40 |
| Shortgrass Prairie Seed Mix | $288 | $1,903 | 6.60 |
| Transitional Pasture & Forage 10 Lb | $447 | $1,903 | 4.26 |
| Full Shade Lawn Seed Mix | $519 | $1,809 | 3.49 |
| White Dutch Clover Seed (5 lb) | $525 | $1,672 | 2.71 |
| Chicken & Poultry Forage Seed Mix | $656 | $1,531 | 2.33 |

### Products with Spend but Zero Revenue: **101 products** wasting budget

Top offenders:
| Product | Cost | Issue |
|---|---|---|
| Cool-Season Pasture 10 Lb | $118 | $0 revenue |
| Rocky Mountains Wildflower 1 Lb | $102 | $0 revenue |
| Wildflower 0.5 Lb | $100 | $0 revenue |
| White Sage Seed | $94 | $0 revenue |
| Native Cabin Grass Seed Mix 25 lb | $90 | $0 revenue |
| Kentucky Bluegrass Pasture Seed | $88 | $0 revenue |
| Upland Game Bird Food Plot Seed | $85 | $0 revenue |

### Star Products (ROAS > 5x, Spend > $5): 31 products

Standouts include California Wildflower Blend (10.27x), Transitional Pasture large bags (6.85-8.68x), California Poppy 1 oz (11.66x), and Cool-Adapted Pasture 50 Lb (12.31x).

---

## 10. Gap Analysis: What Used to Work That We're NOT Doing Now

### Paused/Removed Campaigns That Had Strong ROAS:

| Campaign | Status | Type | Total Spend | Total Revenue | ROAS |
|---|---|---|---|---|---|
| Nat \| PMax \| Pasture Seed \| ROAS | PAUSED | PMax | $143,063 | $562,735 | 3.93 |
| Nat \| PMax \| Catch All (old) | REMOVED | PMax | $100,658 | $507,936 | 5.05 |
| Shopping \| grass \| ROAS | PAUSED | Shopping | $76,502 | $235,270 | 3.08 |
| Search \| Categories (Top) \| ROAS | PAUSED | Search | $59,656 | $183,257 | 3.07 |
| California \| PMax \| ROAS | PAUSED | PMax | $54,924 | $174,363 | 3.17 |
| Nat \| PMax \| Wildflower Seed \| Max Conv | PAUSED | PMax | $28,532 | $93,534 | 3.28 |
| Midwest + Atlantic \| PMax \| ROAS | PAUSED | PMax | $30,035 | $81,501 | 2.71 |
| Search \| Pasture Seed (Broad) \| ROAS | PAUSED | Search | $25,353 | $74,819 | 2.95 |
| US \| Performance Max \| Forage Mixes | REMOVED | PMax | $4,352 | $45,481 | **10.45** |
| US \| Shopping \| Catchall - Pasture Seed | PAUSED | Shopping | $2,284 | $25,544 | **11.18** |
| Pacific Northwest \| DSA | PAUSED | Search | $875 | $11,637 | **13.30** |
| US \| DSA \| Pasture Seed | REMOVED | Search | $2,712 | $23,801 | **8.77** |

**The most striking gap: The old PMax Pasture Seed campaign generated $562K in revenue at 3.93x ROAS. Nothing directly replaces it.**

### Keyword Gaps: Proven Keywords Not in Current Campaigns

| Keyword | Match | Historical Spend | Revenue | ROAS | Last Campaign |
|---|---|---|---|---|---|
| pasture seed | PHRASE | $7,646 | $24,102 | 3.15 | Categories (Top) |
| pasture seeds | BROAD | $4,961 | $17,434 | 3.51 | Pasture Seed (Broad) |
| pasture seed | EXACT | $4,195 | $15,331 | 3.65 | Categories (Top) |
| hay seed mix | BROAD | $1,035 | $11,127 | 10.75 | Pasture Seed (Broad) |
| horse pasture seed | PHRASE | $2,587 | $9,695 | 3.75 | Categories (Top) |
| pasture grass mix | BROAD | $2,203 | $7,576 | 3.44 | Pasture Seed (Broad) |
| lawn seed | PHRASE | $2,036 | $7,354 | 3.61 | Categories (Top) |
| sheep pasture mix | PHRASE | $580 | $5,514 | 9.51 | Categories (Top) |
| best cattle pasture mix | PHRASE | $422 | $5,391 | 12.78 | Categories (Top) |
| cattle pasture seed | EXACT | $462 | $5,165 | 11.18 | Categories (Top) |

**"pasture seed" (phrase) alone drove $24K revenue at 3.15x ROAS and is NOT an active keyword.**

**"lawn seed" was driving $7.3K revenue at 3.61x ROAS -- there is NO lawn seed keyword active anywhere.**

**"hay seed mix" returned 10.75x ROAS -- completely absent from current campaigns.**

### Category Coverage Gaps:

| Category | Active Campaign Coverage | Gap |
|---|---|---|
| **Pasture Seed** | Animal Seed (Broad) + Pasture (Exact) + PMax | Covered but diluted |
| **Grass/Lawn Seed** | PMax only (no dedicated search) | MAJOR GAP -- no search keywords |
| **Wildflower Seed** | 2 broad keywords + PMax | Missing dedicated campaign |
| **Clover** | Dutch clover keywords in Animal Broad | Minimal coverage |
| **California** | None (PMax may pick up some) | Was $174K revenue campaign |
| **Regional (PNW, Midwest, etc.)** | None | Previously significant |
| **Food Plot** | 1 Bison ad (no impressions) | Missing entirely |
| **Cover Crop** | None | Missing entirely |
| **DSA (Dynamic Search Ads)** | None | Previously drove $40K+ revenue |

### Search Term Gaps (Queries converting in paused campaigns, Q1 2026):

Even in Q1 2026, some paused campaigns still caught valuable traffic:
| Search Term | Cost | Revenue | ROAS | From Campaign |
|---|---|---|---|---|
| pasture grass seed | $123 | $1,280 | 10.45 | (paused campaign) |
| grass seed for pacific northwest | $4 | $329 | 81.13 | (paused campaign) |
| timothy grass seed for sale | $2 | $310 | 134.16 | (paused campaign) |
| texas pasture grass seed | $1 | $160 | 118.49 | (paused campaign) |

---

## Summary of Critical Findings

### Immediate Action Items (Revenue Impact):

1. **Search | Animal Seed (Broad) ROAS collapsed to 0.84** -- this campaign is now losing money. Either pause non-performing ad groups, tighten match types, or reduce budget immediately.

2. **24 money-losing keywords need attention** -- $2,300+ wasted in 3 months on keywords with ROAS below 1x. Top offender: "horse pasture seed mix" at $949 spend, 0.65 ROAS.

3. **637 search terms with zero conversions** -- $8,038 wasted. Add negatives for irrelevant terms like "johnny seed," "granite seed," "sustane 18 1 8," "st augustine grass seed."

4. **13 ads pointing to old/incorrect URLs** -- $9,482 in spend going to legacy URL paths. Verify redirects work, then update to canonical /products/ paths.

5. **3 ads using www.naturesseed.com** instead of naturesseed.com -- inconsistent, potential tracking issues.

### Strategic Gaps (Growth Opportunity):

6. **No Grass/Lawn Seed search campaign** -- historically a $7K+ revenue keyword category, now entirely dependent on PMax and Shopping.

7. **No California/Regional campaigns** -- the old California PMax drove $174K in revenue. Nothing replaces it.

8. **No DSA campaigns** -- DSA previously drove $40K+ in revenue across pasture, grass, and wildflower. Consider reactivating.

9. **"pasture seed" keyword family not actively targeted** -- $24K+ historical revenue from phrase and exact match, currently absent.

10. **101 products with spend but zero revenue in Shopping** -- need negative product targeting or feed optimization.

### Budget Allocation Concern:

Shopping Catch All has the largest budget ($1,100/day = 42% of total) but only achieves 2.31-3.11x ROAS. Meanwhile, Brand search achieves 5.78-12.55x ROAS on a $220/day budget. Consider reallocating some Shopping budget to proven search categories.

---

## Supporting Files

| File | Location | Contents |
|---|---|---|
| Enabled ads + URLs | `implementation/LIVE_enabled_ads_with_urls.csv` | All 39 enabled ads with URLs, issues flagged |
| Enabled keywords | `implementation/LIVE_enabled_keywords.csv` | All live keywords with 3-month performance |
| URL issues | `implementation/LIVE_url_issues.csv` | Only ads with problematic URLs |
| Wasted search terms | `implementation/LIVE_wasted_search_terms.csv` | 637 terms with spend > $5 and 0 conversions |
| Keyword performance | `implementation/LIVE_top_keywords.csv` | All keywords classified as Winner/Loser/Neutral |
