# Nature's Seed — Google Ads 4-Year Full Audit Report
### Data Range: March 2022 – March 2026 | Generated: March 5, 2026

---

## EXECUTIVE SUMMARY

Nature's Seed has scaled Google Ads spend **8x in 4 years** (from $44K to $354K annually), but ROAS has collapsed **75%** from 10.6x to 3.2x. Revenue grew only 2.5x ($462K → $1.14M) for that 8x spend increase. The account is approaching break-even territory after COGS.

**The 5 most urgent fixes (in order):**

1. **Remove "Begin Checkout" from conversion tracking** — it's inflating conversions by 50%+ and corrupting Smart Bidding
2. **Add negative keywords for competitor brands** — "Nature's Finest," "Created By Nature," "American Meadows" etc. are bleeding ~$8K/year
3. **Rebalance budget from catch-all to high-ROAS segments** — Forage mixes (sheep/goat/horse) deliver 10-25x ROAS on minimal spend
4. **Fix mobile over-allocation** — mobile is 63% of spend but delivers 18% lower ROAS than desktop
5. **Clean the product feed** — 2,822 products got spend with zero conversions; variant-level SKUs are diluting budget

---

## 1. ACCOUNT ARCHITECTURE

### Current State: 13 Enabled / 250 Total Campaigns

| Campaign | Type | Budget/Day | Bidding | % of Budget |
|----------|------|-----------|---------|-------------|
| Shopping \| Catch All | SHOPPING | $1,100 | Target ROAS | 41.9% |
| PMAX \| Catch all | PMAX | $760 | Max Conv Value | 28.9% |
| Search \| Animal Seed (Broad) | SEARCH | $260 | Max Conv Value | 9.9% |
| Search \| Brand \| ROAS | SEARCH | $220 | Max Conv Value | 8.4% |
| PMAX - Search | PMAX | $210 | Max Conv Value | 8.0% |
| Search \| Pasture \| Exact | SEARCH | $78 | Max Conversions | 3.0% |
| **Total Daily Budget** | | **$2,628** | | **~$79K/month** |

**The Problem:** Two "catch-all" campaigns consume **71% of budget** with no product/category segmentation. This eliminates visibility into what's actually working and prevents targeted optimization.

**Historical Pattern:** The account went from extreme fragmentation (24 Horse Pasture campaigns, 20+ regional campaigns with $10-17/day budgets) to extreme consolidation. The pendulum has swung too far in both directions.

### Campaign Type History

| Type | Total Created | Currently Active |
|------|--------------|-----------------|
| SEARCH | 103 | 4 |
| SHOPPING | 80 | 1 |
| PERFORMANCE_MAX | 36 | 2 |
| DISPLAY | 19 | 0 |
| DEMAND_GEN | 2 | 0 |

---

## 2. SPENDING & ROAS TRENDS

### Annual Performance

| Year | Spend | Revenue | ROAS | Conversions | Cost/Conv |
|------|-------|---------|------|-------------|-----------|
| 2022 | $43,669 | $462,223 | **10.58x** | 4,334 | $10.07 |
| 2023 | $112,988 | $623,277 | **5.52x** | 6,476 | $17.45 |
| 2024 | $291,783 | $1,018,477 | **3.49x** | 8,043 | $36.28 |
| 2025 | $353,991 | $1,135,138 | **3.21x** | 9,564 | $37.01 |
| 2026 (Q1) | $56,601 | $151,061 | **2.67x** | 1,054 | $53.70 |

**The core issue:** Each incremental dollar of ad spend produces diminishing returns. The account has pushed well past the efficient frontier. Cost per conversion has **quadrupled** from ~$10 to ~$37.

### Seasonality Pattern

| Period | Typical ROAS | Spend Level | Notes |
|--------|-------------|-------------|-------|
| Q1 (Jan-Mar) | 2.6-3.4x | PEAK spend | Spring planting — highest volume, lowest efficiency |
| Q2 (Apr-May) | 2.8-3.0x | High | Continuation of spring |
| Q3 (Jul-Sep) | 3.5-4.0x | Medium | Fall planting surge — best efficiency |
| Q4 (Oct-Dec) | 2.5-2.7x | Low | Off-season — low volume, low efficiency |

**Insight:** ROAS improves when spend decreases (summer/fall). The Q1 spending ramp pushes aggressively beyond efficient levels.

---

## 3. PRODUCT CATEGORY PERFORMANCE

### Revenue by Category (Shopping/PMax Data)

| Category | Spend | Revenue | ROAS | % Revenue |
|----------|-------|---------|------|-----------|
| Pasture Seed | $170,088 | $660,383 | **3.88x** | 43.0% |
| Grass Seed (Turf) | $44,868 | $279,972 | **6.24x** | 18.2% |
| Specialty Seed | $73,736 | $214,862 | **2.91x** | 14.0% |
| Lawn Seed | $54,600 | $131,244 | **2.40x** | 8.5% |
| Wildflower Seed | $24,482 | $62,651 | **2.56x** | 4.1% |
| Heartland Collection | $2,732 | $791 | **0.29x** | 0.1% |

### Star Products (Highest Revenue)

| Product | Spend | Revenue | ROAS |
|---------|-------|---------|------|
| White Dutch Clover | $15,072 | $132,792 | **8.81x** |
| Microclover | $5,755 | $43,824 | **7.61x** |
| Fine Fescue Mix | $1,493 | $11,548 | **7.73x** |
| PNW Erosion Control | $2,105 | $12,550 | **5.96x** |
| PNW Dryland Pasture | $1,553 | $11,360 | **7.31x** |
| GL/NE Horse Forage | $1,052 | $9,973 | **9.48x** |

### ROAS Champions (Underinvested)

| Product | Spend | Revenue | ROAS | Opportunity |
|---------|-------|---------|------|-------------|
| SW Desert Goat Forage | $122 | $3,515 | **28.9x** | Needs 10x budget |
| PNW Sheep Forage | $173 | $4,451 | **25.7x** | Needs 10x budget |
| GL/NE Sheep Forage | $510 | $9,627 | **18.9x** | Needs 5x budget |
| Native Fine Fescue | $361 | $6,294 | **17.4x** | Needs 5x budget |
| Southern Sheep Forage | $312 | $5,186 | **16.7x** | Needs 5x budget |
| GL/NE Goat Forage | $178 | $2,883 | **16.2x** | Needs 10x budget |

**These forage mixes are generating 16-29x ROAS on trivial budgets.** The catch-all campaign structure prevents Google from allocating more budget to these winners.

### Money Losers

| Product/Category | Spend | Revenue | ROAS | Action |
|-----------------|-------|---------|------|--------|
| Heartland Collection | $2,732 | $791 | 0.29x | Exclude from feed |
| Lawn Seed (overall) | $54,600 | $131,244 | 2.40x | Reduce budget |
| 2,822 zero-conv products | $33,004 | $0 | 0.00x | Clean feed |

---

## 4. KEYWORD & SEARCH TERM ANALYSIS

### Brand vs Non-Brand Split (THE Critical Finding)

| Segment | Spend | Revenue | ROAS | % of Conversions |
|---------|-------|---------|------|------------------|
| **Brand** | $29,888 | $591,060 | **19.8x** | 61.6% |
| **Non-Brand** | $153,784 | $419,874 | **2.7x** | 38.4% |

**The account is heavily brand-dependent.** 62% of all keyword conversions come from brand terms. Non-brand ROAS at 2.7x is barely profitable after COGS.

### Match Type Performance

| Match Type | Spend | ROAS | CPA |
|-----------|-------|------|-----|
| EXACT | $47,228 | **13.08x** | $10.86 |
| PHRASE | $93,355 | **2.49x** | $62.28 |
| BROAD | $57,680 | **2.12x** | $45.71 |

EXACT match (dominated by brand) is 5x more efficient than PHRASE/BROAD. The account spends 76% of keyword budget on PHRASE+BROAD for only 39% of conversion value.

### Top Wasted Spend: Competitor Brand Bleed (~$8K/year)

| Competitor Term | Total Spend | ROAS |
|-----------------|-------------|------|
| "Nature's Finest" (Scotts brand) | $3,472 | 0.2-0.4x |
| "Created By Nature" (diff company) | $1,636 | 0.0x |
| "American Meadows" (competitor) | $170 | 0.0x |
| "Ernst Seeds" (competitor) | $137 | 0.0x |
| "Mother Nature Seeds" (diff company) | $208 | 0.0x |
| "Hancock Seed" (competitor) | $88 | 0.1x |
| Other competitor terms | ~$2,251 | <1.0x |

**Immediate fix: Add these as negative keywords across all campaigns.**

### Top Converting Non-Brand Search Terms

| Search Term | Revenue | ROAS | Opportunity |
|-------------|---------|------|-------------|
| pasture seed | $12,504 | 3.9x | Core term — maintain |
| pasture grass seed | $10,986 | 4.4x | Strong performer |
| goat pasture seed mix | $8,149 | **9.6x** | Increase budget |
| cattle pasture seed | $4,648 | **23.4x** | Massively underinvested |
| sheep pasture seed mix | $4,041 | **5.7x** | Increase budget |
| organic pasture seed | $3,837 | **13.6x** | Increase budget |
| white clover seed | $5,188 | 5.1x | Strong performer |

---

## 5. AD COPY INSIGHTS

### What Works

| Pattern | ROAS | Example |
|---------|------|---------|
| Brand + quality claim | **8.72x** | "Nature's Seed Quality Seed" |
| Sale/promo messaging | **10.92x** | "Black Friday Sale - 25% Off" |
| Dynamic Keyword Insertion | **4.62x** | "{KeyWord:Cattle Pasture Seed}" |
| Animal-specific headlines | **3-5x** | "Cattle Pasture Seed," "Poultry Forage Mix" |

### What Doesn't Work

| Pattern | ROAS | Issue |
|---------|------|-------|
| Generic category headlines | 0.5-1.2x | "Grass Seed," "Wildflower Seed" |
| Microclover ads | 0.12x | $980 spend, $118 return |
| Wildflower ads (all) | 0.05-0.89x | 5 of 10 worst ads are wildflower |

### Landing Page Issues

- **Two pasture seed URLs splitting traffic:** `/products/pasture-seed/` and `/pasture-seed/` — consolidate to one
- **`get.naturesseed.com` subdomain:** 17,220 clicks, only 2.83x ROAS — test against main domain
- **Goat/Sheep pasture pages are highest-ROAS destinations** (4.66x and 3.99x) — send more traffic there

---

## 6. DEVICE & GEO PERFORMANCE

### Device Split

| Device | % of Spend | ROAS | Trend |
|--------|-----------|------|-------|
| Mobile | 63% | **3.50x** | Growing share, declining ROAS |
| Desktop | 38% | **4.28x** | Shrinking share, higher ROAS |
| Tablet | 2% | **3.03x** | Declining to unprofitable (1.92x in 2026) |

**Mobile over-allocation is costing ~$50-70K/year in lost efficiency.** Desktop converts 22% more efficiently but receives less budget. Apply -15% to -20% mobile bid adjustment.

### Regional Performance

| Region | ROAS | Current Spend | Action |
|--------|------|--------------|--------|
| Southwest Desert | **15.11x** | $297 | MASSIVELY increase |
| Great Lakes/NE | **12.03x** | $533 | MASSIVELY increase |
| Pacific Northwest | **11.66x** | $2,021 | Significantly increase |
| National | **4.30x** | $301,021 | Maintain |
| California | **3.16x** | $55,085 | Optimize |
| Great Plains | **2.25x** | $19,977 | Reduce or optimize |

---

## 7. CONVERSION TRACKING — CRITICAL ISSUES

### Issue #1: "Begin Checkout" Inflating Conversions by 50%+

The "Begin checkout" conversion action is **ENABLED and INCLUDED IN CONVERSIONS.** It's counting every checkout page load as a conversion with $1.00 value.

| Quarter | Fake "Conversions" Added | Impact |
|---------|------------------------|--------|
| Q3 2025 | +1,790 | ~30% inflation |
| Q4 2025 | +1,859 | ~35% inflation |
| Q1 2026 | +3,753 | **~54% inflation** |

**This is corrupting Smart Bidding.** The algorithm sees artificially high conversion rates and bids too aggressively for low-quality traffic. **Remove from "Include in Conversions" immediately.**

### Issue #2: Purchase Tracking Changed 5 Times

The dominant purchase conversion action has changed every 6-12 months:
- 2022: Universal Analytics "Transactions"
- 2023: Profit Metrics "PM Revenue - Browser"
- 2024: Mix of PM + GA4 + WooCommerce
- 2025-2026: "Purchase" (Data-Driven)

Each transition created a learning period where Smart Bidding lost its optimization signals. This explains some of the ROAS decline beyond just scaling effects.

### Issue #3: 20 Purchase Actions Over 4 Years

45 total conversion actions, 20 of which are purchase-type. In Q1 2024, **SEVEN fired simultaneously.** While not all are "included," this creates noise in reporting.

---

## 8. STRATEGIC RECOMMENDATIONS

### Tier 1: Do This Week (Immediate Revenue Impact)

| Action | Est. Impact | Effort |
|--------|-------------|--------|
| Remove "Begin Checkout" from Include in Conversions | Fixes bidding algorithm; may reduce wasted spend 15-20% | 5 min |
| Add competitor negative keywords | Saves ~$8K/year immediately | 30 min |
| Audit HIDDEN conversion actions with Include=TRUE | Removes zombie signals from Smart Bidding | 1 hour |

### Tier 2: Do This Month (Structural Improvements)

| Action | Est. Impact | Effort |
|--------|-------------|--------|
| Create dedicated Forage Mix campaigns (sheep/goat/horse) | Capture 16-29x ROAS opportunities | 4 hours |
| Clean product feed (remove variants, exclude zero-conv products) | Saves ~$33K/year in wasted product spend | 2-4 hours |
| Apply mobile bid adjustment (-15 to -20%) | Improves efficiency by ~$50-70K/year | 30 min |
| Consolidate pasture seed landing pages | Stops splitting conversion signals | 1 hour |
| Pause/exclude Heartland Collection from Shopping | Stops 0.29x ROAS waste | 15 min |

### Tier 3: Do This Quarter (Strategic Shifts)

| Action | Est. Impact | Effort |
|--------|-------------|--------|
| Build out PNW/GL-NE/SW Desert regional campaigns | These regions show 12-15x ROAS; scaling 5x could add $50K+ revenue | 8 hours |
| Test seasonal budget pacing (reduce Q1 ramp, maintain Q3) | ROAS is 30% better in Q3 vs Q1 at lower spend | Ongoing |
| Move from catch-all to segmented PMax (by category) | Regains visibility and control over product-level optimization | 4-6 hours |
| Re-evaluate Wildflower paid strategy | Consistently sub-1x ROAS on search; may be better as Shopping-only | 2 hours |
| Increase Brand Search budget | Best ROAS campaign (8-20x) only gets 8.4% of budget | 15 min |

### Tier 4: Ongoing Optimization

- Build exact-match non-brand keyword list from top-converting search terms
- Use DKI (Dynamic Keyword Insertion) more aggressively in ad copy
- Monthly search term mining for new negatives
- Quarterly conversion tracking audit
- Test promotional ad copy more frequently (Black Friday ads hit 10.9x ROAS)

---

## 9. PROJECTED IMPACT

If all Tier 1-2 actions are implemented:

| Metric | Current (2025) | Projected |
|--------|---------------|-----------|
| Annual Spend | $354K | $300-320K (reduced waste) |
| Annual Revenue | $1.14M | $1.3-1.5M (better allocation) |
| ROAS | 3.21x | **4.0-4.5x** |
| Cost/Conversion | $37 | $25-28 |
| Wasted Spend | ~$80-100K | ~$20-30K |

**Conservative estimate: $150-300K in additional revenue on less spend by reallocating budget from waste to proven winners.**
