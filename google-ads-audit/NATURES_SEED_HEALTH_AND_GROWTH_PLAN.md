# Nature's Seed — Google Ads Health & Growth Plan
## Specific Actionable Plan Based on Live Data + COGS Analysis
### March 9, 2026 | Data: Live API Pull + 276-SKU COGS Table

---

## Current Account Health Score: 4.5 / 10

| Dimension | Score | Why |
|-----------|-------|-----|
| Efficiency (ROAS) | 5/10 | 3.13x blended — profitable but barely after shipping |
| Budget Allocation | 3/10 | 71% in catch-all campaigns, best campaign (Brand 17.1x) gets only 5% |
| Keyword Strategy | 4/10 | 24 money-losing keywords still active, major gaps in coverage |
| Conversion Tracking | 3/10 | "Begin Checkout" likely still inflating, changed 5 times |
| Product Feed | 5/10 | 81 products losing money after COGS+ads, 29 with zero revenue |
| Margin Awareness | 2/10 | No bidding aligned to product margins — all treated equally |
| Structural Architecture | 4/10 | Over-consolidated, no category segmentation |
| Growth Coverage | 4/10 | Missing lawn seed, hay seed, DSA, regional campaigns |
| **Overall** | **4.5/10** | Profitable in aggregate but leaving $50K+ on the table annually |

---

## The Margin Reality

**This is the most important section.** Google Ads doesn't know your margins. It optimizes ROAS uniformly across all products. But a 3x ROAS on a 57% margin product is barely profitable, while a 3x ROAS on a 77% margin product is highly profitable. The account needs margin-aware bidding.

### Category Margins & Break-Even ROAS

| Category | Avg Margin | Break-Even ROAS* | Target ROAS** | Current ROAS | Verdict |
|----------|-----------|-------------------|---------------|-------------|---------|
| Pure Grass (Pasture) | 77.6% | 1.29x | 1.68x | n/a (via catch-all) | Unknown |
| Wildflower | 76.9% | 1.30x | 1.69x | 2.7x | ✅ Profitable |
| Lawn/Turf Seed | 73.0% | 1.37x | 1.78x | 2.5x | ✅ Profitable |
| Wildflower Blend | 73.0% | 1.37x | 1.78x | (in wildflower) | ✅ Profitable |
| Food Plot | ~65%*** | 1.54x | 2.00x | 3.5x | ✅ Strong |
| Specialty/Clover | 60.9% | 1.64x | 2.13x | 2.3x | ⚠️ Marginal |
| Pasture Seed Mixes | 57.3% | 1.75x | 2.27x | 3.3x | ✅ Profitable |

*Break-even = COGS cost only. **Target = 30% buffer for shipping, payment processing, overhead. ***Estimated.

**Key insight**: Every category is above its break-even ROAS in aggregate. The problem isn't category-level — it's product-level. 81 individual products are losing money after COGS + ad spend, totaling $5,172 in net losses over 90 days (~$20K/year).

### The Margin-ROAS Matrix

| Scenario | Revenue | COGS (avg 65%) | Gross Profit | Ad Spend | Net | Status |
|----------|---------|----------------|-------------|----------|-----|--------|
| 5x ROAS, 65% margin | $5.00 | $1.75 | $3.25 | $1.00 | **$2.25** | ✅ Very profitable |
| 3x ROAS, 65% margin | $3.00 | $1.05 | $1.95 | $1.00 | **$0.95** | ✅ Profitable |
| 2x ROAS, 73% margin (Lawn) | $2.00 | $0.54 | $1.46 | $1.00 | **$0.46** | ⚠️ Slim |
| 2x ROAS, 57% margin (Pasture) | $2.00 | $0.86 | $1.14 | $1.00 | **$0.14** | ⚠️ Barely |
| 1.5x ROAS, 57% margin | $1.50 | $0.65 | $0.86 | $1.00 | **-$0.14** | ❌ Losing |

**Bottom line**: Pasture Seed Mixes (57% margin) need minimum 2.3x ROAS to truly profit. Lawn/Wildflower (73-77% margin) can afford down to 1.7x. The account should bid differently by category.

---

## Live P&L Snapshot (Last 90 Days — From API)

### Campaign Performance

| Campaign | 90d Spend | Revenue | ROAS | CPA | IS% | Health |
|----------|----------|---------|------|-----|-----|--------|
| Shopping Catch All | $37,294 | $105,845 | 2.84x | $49 | 32% | ⚠️ Below target, low IS |
| PMax Catch All | $20,030 | $66,791 | 3.33x | $60 | 10% | ⚠️ OK but declining |
| Animal Seed (Broad) | $8,556 | $17,994 | 2.10x | $77 | 10% | ❌ Barely above break-even |
| PMax - Search | $7,378 | $21,467 | 2.91x | $46 | 10% | ⚠️ Improving |
| Brand Search | $4,102 | $30,940 | 7.54x | $27 | 10% | ✅ Star — severely budget-limited |
| Pasture Exact | $3,672 | $10,660 | 2.90x | $48 | 10% | ⚠️ Improving |
| **TOTAL** | **$81,033** | **$253,697** | **3.13x** | **$50** | | |

### Critical Observations

1. **Brand Search is the account's best campaign (7.54x ROAS) but gets only 5% of spend.** It has 10% impression share — meaning 90% of brand searches are NOT showing your ads. This is the single biggest missed opportunity.

2. **Shopping Catch All has only 32% impression share** at $37K spend. This means 68% of eligible Shopping impressions are going to competitors. But blindly increasing budget won't help — need to fix the product mix first.

3. **Animal Seed (Broad) at 2.10x ROAS** is barely profitable after COGS on pasture mixes (57% margin). After shipping costs, this campaign is likely break-even or losing money.

### Product-Level P&L (Shopping/PMax Combined)

| Metric | Value |
|--------|-------|
| Products with ad spend (last 90d) | 200+ |
| Products turning a profit (after COGS + ad spend) | 119 |
| Products losing money (after COGS + ad spend) | **81** |
| Total profit from winners | **+$37,479** |
| Total loss from losers | **-$5,172** |
| Net from all products | **+$32,308** |
| **If losers eliminated** | **+$37,479** (+$5,172 improvement) |

---

## The Specific Plan

### PHASE 1: Stop the Bleeding (This Week)

#### 1.1 Exclude the 25 Worst Money-Losing Products from Shopping

These products are burning the most cash after accounting for their margins:

| Product | 90d Ad Spend | Revenue | Gross Profit | Net Loss |
|---------|-------------|---------|-------------|----------|
| Sun & Shade Lawn Seed Mix (small) | $240 | $21 | $16 | -$224 |
| Wildflower 5 Lb Mix Deer Resistant | $448 | $294 | $226 | -$221 |
| Orchard Grass Pasture 50 Lb | $225 | $17 | $10 | -$215 |
| Xerces Pollinator Wildflower Mix | $176 | $0 | $0 | -$176 |
| Cool-Season Pasture 10 Lb | $163 | $9 | $5 | -$157 |
| Dryland Pasture 50 Lb | $411 | $472 | $271 | -$140 |
| Rocky Mountains Wildflower 0.5 Lb | $204 | $83 | $64 | -$139 |
| Dryland Pasture 10 Lb | $194 | $98 | $56 | -$138 |
| Fine Fescue Lawn (variant) | $131 | $0 | $0 | -$131 |
| Mycorrhizal Inoculant AM 120 | $280 | $251 | $153 | -$127 |

**Action**: Use custom_label_4 in the Merchant Center feed to tag these as "exclude" and create a negative product group in Shopping.

**Expected savings**: ~$2,000/month in pure waste eliminated.

#### 1.2 Pause Money-Losing Keywords (Previously identified, verify still active)

| Keyword | Campaign | 90d Spend | ROAS | Action |
|---------|----------|----------|------|--------|
| horse pasture seed mix | Animal Broad + Pasture Exact | $167 | 0.0x | PAUSE |
| native california grass seed | Shopping (search term) | $138 | 0.0x | Add negative |
| best grass seed for cattle pasture | Shopping (search term) | $101 | 0.0x | Add negative |
| pasture seed mix | Shopping (search term) | $147 | 0.6x | Add negative |
| california native wildflower seeds | Shopping (search term) | $93 | 0.4x | Add negative |

**Action**: Add these as negative keywords in Shopping. Pause the keyword-level losers in Search.

#### 1.3 Triple the Brand Campaign Budget

| Metric | Current | Proposed |
|--------|---------|----------|
| Budget | $220/day | **$500/day** |
| Impression Share | ~10% | Target 50%+ |
| Current ROAS | 7.54x | Expected 6-8x (still exceptional) |
| Current 90d revenue | $30,940 | Projected $75-100K |

**This is the single highest-ROI action available.** At 10% impression share and 7.54x ROAS, you're leaving ~$60-80K in high-margin revenue on the table every 90 days because of a $220 budget cap. Even if ROAS drops to 5x as you scale, it's still 3x more efficient than Shopping.

**The math**: $280/day increase × 90 days = $25,200 additional spend. At 5x ROAS = $126,000 additional revenue. At 65% margin = $81,900 gross profit. Net after ad spend: **+$56,700 in 90 days.**

---

### PHASE 2: Reallocate & Restructure (Next 2 Weeks)

#### 2.1 Budget Reallocation

| Campaign | Current | New | Change | Rationale |
|----------|---------|-----|--------|-----------|
| Shopping Catch All | $1,450 | $1,200 | -$250 | Trim waste, still majority of budget |
| PMax Catch All | $760 | $760 | — | Hold, volatile |
| Animal Seed (Broad) | $260 | **$130** | -$130 | 2.10x ROAS, barely profitable |
| PMax Search | $300 | $300 | — | Hold, improving |
| Brand Search | $220 | **$500** | +$280 | 7.54x ROAS, 10% IS — massive headroom |
| Pasture Exact | $78 | **$200** | +$122 | Add new keyword groups |
| **Total** | **$3,068** | **$3,090** | **+$22** | Nearly budget-neutral |

**Net effect**: Same total spend, but shifted from 2.1x ROAS campaigns to 7.5x ROAS campaigns. Expected blended ROAS improvement: 3.13x → 3.5-4.0x.

#### 2.2 Add Missing High-Value Keywords to Pasture Exact

These search terms are already converting profitably in Shopping but have NO dedicated keywords:

| Search Term | 90d Shopping Revenue | Shopping ROAS | Action |
|-------------|---------------------|---------------|--------|
| pasture seed | $1,558 | 9.0x | Add as PHRASE + EXACT |
| kentucky bluegrass seed | $1,070 | 5.0x | Add as PHRASE |
| horse pasture seed | $907 | 8.3x | Add as PHRASE |
| bermuda grass seed | $677 | 5.0x | Add as PHRASE |
| rice hulls | $518 | 5.7x | Add as EXACT |
| sheep pasture seed mix | $430 | 9.6x | Add as PHRASE |
| goat pasture seed mix | $3,005 | 28.5x | Already in Animal Broad — verify |

**Expected impact**: These terms are already converting. Adding them as explicit keywords ensures they always show (not dependent on catch-all matching) and gives granular bid control.

#### 2.3 Fix Pasture Exact Bidding Strategy

**Current**: Maximize Conversions (optimizes for count)
**Change to**: Maximize Conversion Value (optimizes for revenue)
**Set target ROAS**: 250% (2.5x) — conservative floor given 57% pasture margins

This single setting change will make Google prioritize the $200 pasture orders over the $20 ones.

#### 2.4 Review Conversion Tracking

Check in Google Ads → Tools → Conversions:
- Only "Purchase" should be Primary (Include in Conversions = Yes)
- "Begin Checkout" must be Secondary (observation only)
- Count total Primary conversion actions — should be exactly 1

**If Begin Checkout is still Primary**: Changing it will cause a 2-3 week Smart Bidding learning period. Plan for temporarily lower performance. Worth it for long-term accuracy.

---

### PHASE 3: Strategic Growth (Next 30 Days)

#### 3.1 Margin-Tiered Shopping Structure

Replace the single "Shopping Catch All" with 3 product groups based on margins:

| Tier | Products | Avg Margin | Target ROAS | Budget Share |
|------|----------|-----------|-------------|-------------|
| **Tier 1: High Margin** | Pure Grass, Wildflowers, Lawn/Turf | 73-78% | 2.0x minimum | 50% |
| **Tier 2: Medium Margin** | Specialty/Clover, Food Plot, Planting Aids | 61-65% | 2.5x minimum | 30% |
| **Tier 3: Low Margin** | Pasture Mixes, Covers Crop | 57% | 3.0x minimum | 20% |

**Implementation**: Use `custom_label_3` (currently "margin tier" in the feed) to group products. Create subdivision product groups in the Shopping campaign by custom_label_3.

**Why this matters**: Right now, Google gives equal bidding priority to a 95% margin Pure Grass product and a 57% margin Pasture Mix. By setting different target ROAS by tier, Google bids more aggressively on high-margin items (where you can afford to) and more conservatively on low-margin items.

#### 3.2 The Star Products — Double Down

These are the products generating the most net profit. They deserve explicit attention:

| Product | 90d Net Profit | ROAS | Category | Margin |
|---------|---------------|------|----------|--------|
| Shortgrass Prairie Mix (large) | +$2,655 | 12.3x | Food Plot | ~65% |
| California Wildflower Blend 5 Lb | +$2,145 | 10.9x | Wildflower | 77% |
| Transitional Pasture 50 Lb (variant A) | +$1,564 | 8.0x | Pasture | 57% |
| Transitional Pasture 50 Lb (variant B) | +$1,556 | 6.0x | Pasture | 57% |
| California Wildflower Mix 5 Lb | +$1,247 | 6.8x | Wildflower | 77% |
| Full Shade Lawn Mix 5 Lb | +$1,236 | 3.9x | Lawn | 73% |
| Sundancer Buffalograss (large) | +$1,229 | 4.5x | Lawn | 73% |
| White Dutch Clover (large) | +$862 | 2.4x | Specialty | 61% |

**Action**: Ensure these products are NOT being limited by Shopping bid caps. Consider creating a "Star Products" product group with higher bids or a separate high-priority Shopping campaign.

#### 3.3 Recover California Revenue

**History**: The paused California PMax campaign generated $174,363 in lifetime revenue at 3.17x ROAS.
**Today**: California Wildflower Blend is the #2 most profitable product (+$2,145 net in 90 days). California Poppy generates +$1,528 combined from its variants.

**Action**: Add a California-focused asset group in PMax Catch All:
- Filter: `custom_label_1 = "California"`
- Headlines: "California Native Wildflower Seeds", "California Poppy Seeds", "Drought-Tolerant California Seeds"
- Landing page: `/products/wildflower-seed/` and `/products/grass-seed/`
- Budget: Shared with PMax Catch All (no separate campaign needed)

#### 3.4 Launch DSA Discovery Campaign

**History**: Paused DSA campaigns generated $35K+ at 8.8-13.3x ROAS.

**Setup**:
- Campaign: "DSA | All Products"
- Target: `naturesseed.com/products/` (entire product catalog)
- Bidding: Maximize Conversion Value
- Budget: $75/day
- Negatives: All negatives from Phase 1 + brand terms (don't cannibalize Brand campaign)

**Purpose**: Catch long-tail queries the keyword campaigns miss. Mine the search term report every 2 weeks and graduate winners into Pasture Exact.

---

### PHASE 4: Advanced Optimization (Ongoing)

#### 4.1 Search Term Mining Cadence

**Every 2 weeks**:
1. Pull search terms from all campaigns
2. Winning terms (ROAS > 3x, 2+ conversions) → Add as explicit keywords in Pasture Exact or new ad groups
3. Losing terms (ROAS < 1x, $20+ spend) → Add as negatives
4. Competitor brand names → Add as negatives

**Current winners to watch** (already converting via Shopping, no dedicated keywords):
- "goat pasture seed mix" — 28.5x ROAS, $3,005 revenue
- "pasture seed" — 9.0x ROAS, $1,558 revenue
- "horse pasture seed" — 8.3x ROAS, $907 revenue
- "sheep pasture seed mix" — 9.6x ROAS, $430 revenue
- "rice hulls" — 5.7x ROAS, $518 revenue

#### 4.2 Seasonal Budget Pacing

Based on 4-year data:

| Period | ROAS Pattern | Budget Strategy |
|--------|-------------|----------------|
| Q1 (Jan-Mar) | 2.6-3.4x (lowest) | Moderate — spring demand offsets lower efficiency |
| Q2 (Apr-May) | 2.8-3.0x | Pull back — demand drops, ROAS still low |
| Q3 (Jul-Sep) | 3.5-4.0x (highest) | **Push hard** — fall planting, best efficiency |
| Q4 (Oct-Dec) | 2.5-2.7x | Conservative — off-season |

**Concrete action**: In July, increase Shopping and Pasture Exact budgets by 30-50%. In November-December, reduce Animal Seed Broad and PMax budgets by 30%.

#### 4.3 Product-Level Exclusion Review (Monthly)

Every month, run this query against Shopping performance:
1. Products with $50+ spend and zero revenue → Exclude
2. Products with ROAS below category break-even for 60+ days → Exclude
3. Small variants (0.25 lb, 0.5 lb, 1 oz) that don't convert → Exclude (keep the 5 lb and 25 lb variants that do)

**Pattern spotted**: Small package sizes consistently underperform. The 0.5 lb Wildflower (-$139 net), 1 oz California Poppy variants, and small pasture bags get clicks but don't convert well. Customers searching on Google tend to buy larger quantities. Consider excluding sub-5lb variants from Shopping.

#### 4.4 The Negative Margin Alert

**Only 1 SKU is negative margin (PB-DRY-50-LB-KIT at -11.1%)**, but some products have razor-thin margins:

| SKU | Cost | Price | Margin |
|-----|------|-------|--------|
| PB-DRY-50-LB-KIT | $102.00 | $91.78 | **-11.1%** |
| PG-CYDA-25-LB-KIT | $137.50 | $139.99 | 1.8% |
| W-LUTE-0.5-LB-KIT (Texas Bluebonnet) | $18.30 | $16.06 | **-14.0%** |

**Any ad spend on negative-margin products is pure loss.** Verify these are excluded from Shopping campaigns.

---

## Projected Impact

### Conservative Scenario (Phase 1-2 only)

| Metric | Current (90d) | After Phase 1-2 | Annualized Improvement |
|--------|--------------|-----------------|----------------------|
| Total Spend | $81,033 | $83,000 (+2%) | Flat |
| Total Revenue | $253,697 | $310,000 (+22%) | +$225K/year |
| Blended ROAS | 3.13x | 3.73x | +0.60x |
| Net Profit (after COGS + ads) | ~$32,308 | ~$55,000 | +$90K/year |
| Waste eliminated | $5,172 | ~$1,000 | ~$17K/year saved |

### Aggressive Scenario (All Phases)

| Metric | Current (90d) | After All Phases | Annualized Improvement |
|--------|--------------|-----------------|----------------------|
| Total Spend | $81,033 | $90,000 | +$36K/year |
| Total Revenue | $253,697 | $375,000 (+48%) | +$485K/year |
| Blended ROAS | 3.13x | 4.17x | +1.04x |
| Net Profit (after COGS + ads) | ~$32,308 | ~$82,000 | +$200K/year |

---

## Implementation Priority Queue

| Priority | Action | Effort | Expected Impact |
|----------|--------|--------|----------------|
| 🔴 P0 | Triple Brand budget ($220 → $500) | 5 min | +$50-80K rev / quarter |
| 🔴 P0 | Exclude 25 worst products from Shopping | 1 hour | Save ~$2K/month |
| 🔴 P0 | Pause/negative money-losing search terms | 30 min | Save ~$500/month |
| 🟡 P1 | Cut Animal Seed Broad budget 50% | 5 min | Stop $130/day bleed |
| 🟡 P1 | Add "pasture seed" + 6 other keywords | 30 min | Capture $5-10K/quarter |
| 🟡 P1 | Fix Pasture Exact bidding to Max Conv Value | 5 min | Lift ROAS ~20% |
| 🟡 P1 | Audit conversion tracking | 30 min | Fix Smart Bidding accuracy |
| 🟢 P2 | Increase Pasture Exact budget ($78 → $200) | 5 min | Capture keyword gaps |
| 🟢 P2 | Create margin-tiered Shopping product groups | 2 hours | Margin-aware bidding |
| 🟢 P2 | Add California asset group in PMax | 1 hour | Recover ~$50K/year |
| 🟢 P2 | Launch DSA campaign ($75/day) | 1 hour | Capture long-tail at 8-13x ROAS |
| 🔵 P3 | Small variant exclusion in Shopping | 1 hour | Reduce low-value clicks |
| 🔵 P3 | Seasonal budget automation | 2 hours | +15-20% ROAS in Q3 |
| 🔵 P3 | Bi-weekly search term mining process | Ongoing | Compound improvement |

---

## Supporting Data Files

| File | Contents |
|------|---------|
| `live_google_ads_data.json` | Live API pull — campaigns, search terms, products (March 9, 2026) |
| `cogs_analysis.json` | Full COGS analysis — 276 SKUs, category margins, break-even ROAS |
| `GOOGLE_ADS_HEALTH_AND_GROWTH_GUIDE.md` | General framework (not Nature's Seed specific) |
| `LIVE_STATE_AUDIT.md` | Detailed live account audit (March 5, 2026) |
| `LIVE_IMPLEMENTATION_GUIDE.md` | Prior implementation guide with scripts |
| `FULL_AUDIT_REPORT.md` | Historical 4-year analysis |

---

*Generated March 9, 2026 | Data sources: Google Ads API (live), Supabase COGS table (276 SKUs), 4-year historical CSVs*
*Nature's Seed Data Orchestrator*
