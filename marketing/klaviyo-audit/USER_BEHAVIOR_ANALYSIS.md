# Nature's Seed — Klaviyo User Behavior Analysis
## 4-Year Retrospective (Jan 2022 – Mar 2026)

> **Purpose**: Establish a baseline of customer behavior, channel performance, and email program maturity before building new flows and campaigns. Reference this document before any new flow/campaign development.

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total emails delivered (4yr) | 6,833,144 |
| Total email-attributed revenue | $726,274 (email channel) |
| Total WooCommerce email revenue (2024–present) | $3,662,841 |
| Average open rate | ~48% (inflated by Apple MPP post-2024) |
| True click rate (pre-MPP baseline) | 2.3–3.1% (2022 baseline) |
| Total flows | 46 (10 live, 36 draft/manual) |
| Total campaigns | 375 (since 2019) |
| Total segments | 219 |
| Total lists | 27 |
| Unsubscribe rate | 0.4% (healthy — below 0.5% danger zone) |

**Key finding**: The email program was running on Magento through 2023. WooCommerce integration activated mid-2024. Revenue attribution data is only reliable from June 2024 onward. The 2022–2023 high engagement numbers reflect a healthy list, but zero attributed revenue because the WC integration wasn't live yet.

---

## 1. Revenue Timeline & Platform Migration

### What Happened
- **2022–2023**: Strong email engagement (25–60% open rates, 2–4% CTR) but **$0 attributed revenue** in Klaviyo. This is because the store was on Magento during this period — the Magento integration was not being used for revenue attribution, or attribution was tracked separately.
- **Early 2024**: WooCommerce integration activated. First attributed orders appear Feb 2024 ($46) and May 2024 ($327) — test/calibration events.
- **June 2024**: WooCommerce integration fully live. **$149,397 attributed revenue** in one month — the first real month. This also coincided with the cold email campaign launch (cohorts starting in 2024-06).
- **2024 Total**: $1,334,628 email-attributed revenue
- **2025 Total**: $1,996,864 email-attributed revenue (+49.6% YoY)
- **2026 YTD (Jan–Mar)**: $331,349 (on pace for $1.3M annualized)

### Revenue Growth Rate
The business is growing strongly. 2025 email-attributed revenue was nearly $2M — up 49.6% from 2024's first full year. The growth driver appears to be both improved flow infrastructure and larger list size.

---

## 2. Seasonal Demand Patterns

### Peak Seasons (by Avg Monthly Email Revenue)
| Rank | Month | Avg Revenue | Why |
|------|-------|------------|-----|
| 1 | September | $131,122 | Fall seeding season — pasture, lawn overseeding |
| 2 | March | $105,433 | Spring seeding — wildflowers, clover, lawn |
| 3 | August | $93,719 | Pre-fall prep + late summer pasture |
| 4 | October | $98,437 | Fall cool-season grass planting |
| 5 | February | $92,085 | Early spring planning + Presidents' Day sale |
| 6 | April | $72,028 | Peak spring wildflower/lawn season |

### Off-Season (Low Revenue, Opportunity)
| Month | Avg Revenue | Notes |
|-------|------------|-------|
| December | $26,504 | Year-end — low purchase intent |
| January | $37,950 | Post-holiday gap |
| July | $57,848 | Mid-summer dormancy for cool-season |
| June | $51,231 | Post-spring lull before fall prep |

**Insight**: The buying cycle is strongly bimodal — **Spring (Feb–Apr)** and **Fall (Aug–Oct)**. Email strategy must front-load revenue generation in these windows. Off-season (Jun–Jul, Dec–Jan) should focus on education, nurture, and list hygiene rather than conversion.

### Top Revenue Months (Actual)
1. **2025-03**: $454,095 — best month ever
2. **2024-09**: $304,823
3. **2025-04**: $288,111
4. **2025-02**: $276,568
5. **2024-08**: $258,022

---

## 3. Email Engagement Analysis

### Open Rate Trends
Open rates show a dramatic shift in 2025 — many months show >100% open rate. This is **Apple Mail Privacy Protection (MPP)** auto-loading images, which inflates open counts. The true open rate baseline is from 2022:

| Period | Delivered Open Rate | Notes |
|--------|-------------------|-------|
| 2022 | 22–53% | Pre-MPP baseline — real opens |
| 2023 | 27–69% | Some MPP impact beginning |
| 2024 | 35–64% | Significant MPP inflation |
| 2025 | 8–112% | Extreme MPP distortion — opens unreliable |

**Takeaway**: Do NOT use open rate as a primary engagement metric for 2025+ data. Use **click rate** as the true engagement signal.

### Click Rate Analysis (More Reliable Signal)
| Period | Typical CTR | Notes |
|--------|------------|-------|
| 2022 | 1.6–3.1% | Baseline pre-Cold Email |
| 2023 | 1.9–3.4% | Similar |
| 2024 | 1.9–19.7% | June spike = cold email list (high unengaged) |
| 2025 | 0.6–3.6% | Normal range after cold email cleanup |

**Notable**: June 2024 had 19.7% CTR — anomalously high. This coincided with the Cold Email Campaign cohorts being activated. This likely distorts the average because the cold email list included people who were already highly interested (they opted into a cold outreach list). This is not sustainable and not repeatable with the regular audience.

### 2025 January Anomaly
January 2025 shows only 8.7% open rate and 0.6% CTR on 180,386 delivered — dramatically lower than other months. This is likely the **cold email campaign** being sent to a large unengaged list. The Sunset Flow and list hygiene operations should address this over time.

---

## 4. Flow Performance Deep Dive

### Live Flows — Revenue Attribution (4-Year Total)

| Flow | Revenue | Orders | AOV | Status |
|------|---------|--------|-----|--------|
| 2025 Welcome Series | $38,037 | 210 | $181 | Live (draft in Klaviyo — was recently rebuilt) |
| Checkout Abandonment | $37,006 | 145 | $255 | Live — highest AOV of top flows |
| Abandoned Cart (2025 version) | $29,738 | 150 | $198 | Live |
| Browse Abandonment (2025) | $27,981 | 107 | $262 | Live — highest AOV overall |
| Unknown flow (VisERh) | $10,068 | 47 | $214 | Possibly deleted/archived |
| Pasture Post Purchase | $3,813 | 4 | $953 | Live but low volume |
| Wildflower Browse Abandon | $3,601 | 24 | $150 | Live |
| Lawn Post Purchase | $2,323 | 19 | $122 | Live |
| Cart Abandonment (Old GS) | $2,008 | 11 | $183 | Draft — being replaced |
| Browse Abandonment (Standard) | $1,277 | 9 | $142 | Live — low but present |

**Critical gaps**:
- **Winback Flow**: Not showing in revenue attribution at all — 0% click rate = 0 conversions
- **Upsell Flow**: Only $255 (3 orders) — essentially non-functional
- **Sunset Flow**: $378 (3 orders) — works but negligible
- **Shipment Flow**: $98 — transactional, revenue attribution here is incidental

### Flow Architecture Assessment
The flow library has grown to 46 total but only 10 are live. The 36 drafts represent 2+ years of planned improvements that haven't launched. **The core active flows are all abandonment and acquisition flows — there is almost nothing post-purchase driving retention and repeat revenue.**

---

## 5. Campaign Analysis

### Campaign Volume by Year
| Year | Total Campaigns | Sent | Notable |
|------|----------------|------|---------|
| 2019 | ~5 | 4 | Spring Launch, Newsletter, Memorial Day |
| 2020 | ~20 | 18 | COVID ATHOME sale, Wildflower themed |
| 2021 | ~5 | 4 | Light volume year |
| 2022 | ~25 | 22 | Date-coded weekly sends begin |
| 2023 | ~40 | 35 | Cold email campaigns start, persona testing |
| 2024 | ~120 | 85 | Explosion in campaign volume — cold outreach, regional |
| 2025 | ~150 | 110 | Continued growth — Spring Recovery, VIP, regional |
| 2026 | ~15 | 10 | Spring 2026 Recovery, Presidents Day, St. Patrick's |

### Campaign Theme History
**2019–2021 (Early Era)**: Simple newsletter model. 1–2 campaigns/month. Themes: seasonal awareness, product spotlights, basic sales.

**2022 (Date-Coded Era)**: Shifted to frequent, date-stamped sends. "3/17 - Spring Seed Sale", "2/01 - Clover Sale". High volume, product-sale focused. Shows the business was learning email velocity.

**2023 (Persona & Cold Outreach Era)**: First persona-based campaigns (Lawn Persona Fertilizer Upsell, Pasture Persona Survey). Cold email program launched with ColdUSAfarms list. Native Application Workshop — educational event marketing. First A/B testing.

**2024 (Scale & Segmentation Era)**: Regional campaigns (California, Texas, Heartland). Flash sales, VIP segments. Cold email scaled to 19+ cohorts. "Cancelled: Account Disabled" campaigns visible — appears account was temporarily suspended during cold email scaling.

**2025 (Lifecycle & Recovery Era)**: Spring Recovery Campaign (custom replacement-product flows). VIP Pasture Sale. Regional best-sellers series. New generation seed announcement. Focus on lifecycle communication over broad blasts.

### Best Performing Campaign Subjects (Themes)
Based on send volumes and campaign names:
1. **Seasonal sale + deadline** ("Last Day", "Last Chance") — urgency drives clicks
2. **Product-specific focus** (Clover Sale, Perennial Ryegrass, Microclover) — niche audiences engage higher
3. **Regional targeting** (California, Texas) — personalization improves relevance
4. **Educational hooks** (Yard Plan, Drone Seeding Demo, TWCA) — builds brand trust

---

## 6. Audience & List Health

### List Architecture (27 Total)
| List | Purpose | Health |
|------|---------|--------|
| Newsletter (NLT2S2) | Main acquisition list | Primary engagement |
| Customers (Sy6vRV) | Active buyers | Highest value |
| Customers - All Time (R2JDwR) | Historical buyers | Includes lapsed |
| Old Email List (HzC8DX) | Legacy list | Likely stale |
| ColdUSAfarms (RKkMjQ) | Cold outreach list | First 1,000 safe |
| Outlook Potential Buyers (NBQVJZ) | Prospecting | Low engagement expected |

### Segment Library (219 Total)
The 219 segments represent strong audience sophistication:
- **Purchase behavior**: Pasture Purchasers, Champions (RFM), Win-Back Opportunities
- **Regional**: California, Texas native
- **Product-specific**: Deer-Resistant Wildflower, Rocky Mountain Mix, Tackifier
- **Lifecycle**: BF/CM cohorts, lapsed customers

**Issue**: With 219 segments, there's significant redundancy and potential audience fragmentation. Many segments appear to be created for one-time campaigns and never cleaned up.

### Subscription Health
- **Unsubscribe rate**: 0.4% (healthy — industry average is 0.5%)
- **Peak unsub months**: Jun–Aug 2023 (cold email impact — 789–1,219/month)
- **Normal unsub volume**: 100–400/month in non-campaign-heavy periods
- **2025 pattern**: Unsubscribes dropping (187–864/month) — list is maturing

---

## 7. Critical Issues Identified

### Issue 1: Winback Flow — Revenue Dead Zone ⚠️ CRITICAL
- The Winback Flow (VvvqpW) generated **$0 in attributed revenue** in the entire dataset
- Email 2 has 0% click rate (confirmed in HANDOFF.md)
- This flow targets "Win-Back Opportunities" — the highest-value dormant segment
- **Estimated lost revenue**: If even 1% of ~5,000 win-back segment purchases at $150 AOV = $7,500/activation

### Issue 2: Upsell Flow — Functionally Non-Existent
- $255 over the entire 4-year window (3 orders)
- The trigger fires AFTER purchase but the messaging clearly isn't compelling
- At $85 AOV vs. general $150-255 AOV — the upsell product selection may be off

### Issue 3: No Post-Purchase Retention System
- Cart/checkout abandonment flows perform well ($37K–$38K)
- But there's no meaningful post-purchase nurture for REPEAT buying
- The top-revenue Pasture Post Purchase flow gets only 4 orders at $953 AOV — it's working when it fires, but not firing often enough
- **Repeat purchase rate** cannot be directly measured from this data but the gap between "Ordered Product" attribution and "flow revenue" suggests most orders are one-time

### Issue 4: Pre-WooCommerce Revenue Blind Spot
- 2022–2023 show $0 email revenue despite ~1,000–2,000+ orders/month on the Magento store
- This data is permanently missing from Klaviyo attribution
- Cannot measure true ROI for campaigns before June 2024

### Issue 5: Open Rate Metric Invalidity (Apple MPP)
- From 2024 onward, open rates are unreliable due to Apple Mail Privacy Protection
- 2025 months routinely show 70–112% "open rates"
- **Email-level A/B testing on opens is meaningless** — must switch to click-based or revenue-based test evaluation

### Issue 6: Cold Email Program — Deliverability Risk
- 2023–2024 saw 19+ cohorts of cold email campaigns
- Account appears to have been suspended ("Cancelled: Account Disabled") across 12+ campaigns
- Jun–Aug 2023 saw unsubscribes spike to 789–1,219/month (vs. 94–199 typical)
- This cold outreach may have damaged sender reputation

---

## 8. Opportunities Identified

### Opportunity 1: Seasonal Email Cadence Optimization
Current email volume is inconsistent. The data shows:
- March and September are highest-revenue months
- But email volume doesn't consistently front-load into these windows
- **Recommendation**: Build a 12-month email calendar with explicit "peak season" and "nurture season" modes

### Opportunity 2: Abandonment Flow Upgrade
The abandonment flows (checkout, cart, browse) are top revenue drivers but benchmarks suggest room for improvement:
- Browse Abandonment: $262 AOV (highest!) — needs more volume/sequencing
- Checkout Abandonment: $255 AOV — 3 emails exist but conversion could improve

### Opportunity 3: Post-Purchase Sequencing
The Pasture Post Purchase flow generates $953 AOV on the few orders it touches. This suggests:
- Customers who get a targeted post-purchase experience spend more
- Wildflower, Lawn, and Clover post-purchase flows need activation
- **Cross-category expansion** (NS-Ukxchg draft) should be prioritized for launch

### Opportunity 4: VIP/Champions Segment
The Champions (RFM) segment (RAQTca) is starred — it's important. But no dedicated revenue-generating flow exists for it.
- VIP Flow (X4wSKE) is in draft since 2023
- Flash Campaign - VIP $1000 segment showed the model works
- **Launch the VIP flow**

### Opportunity 5: Winback Rebuild
The entire winback program is broken. With 219 segments and a dedicated "Win-Back Opportunities" segment (JNTYgB), the audience is defined — the messaging just doesn't work. Rebuilding email 2 alone would address the 0% click problem.

### Opportunity 6: Seasonal Re-Order Reminder
The `NS - Usage-Based Reorder Reminder` (SMZ5NX) is in draft. The customer behavior data shows:
- Seed purchases are seasonal/annual
- Average lawn/pasture seed usage = 1 re-seed per year
- A triggered "it's been 12 months, time to overseed" email is a near-guaranteed revenue driver

---

## 9. Benchmark Reference Card

Use these benchmarks when evaluating new flows and campaigns:

| Metric | 2022 Baseline | 2024 Mature | 2025 Mature | Industry Avg |
|--------|--------------|-------------|-------------|-------------|
| Open Rate (true, pre-MPP) | 25–53% | N/A (MPP) | N/A (MPP) | 20–35% |
| Click Rate | 1.6–3.1% | 1.9–7.9% | 0.6–3.6% | 2–5% |
| Unsubscribe Rate | 0.1–0.4% | 0.2–0.6% | 0.1–0.4% | <0.5% |
| AOV (email-attributed) | Unknown | $150–260 | $150–260 | — |
| Flow Revenue Share | Unknown | ~$160K/year | ~$160K/year | — |
| Campaign Revenue Share | Unknown | ~$1.17M/year | ~$1.84M/year | — |

**Key ratio**: Campaigns drive ~92% of email revenue; flows drive ~8%. This is backwards for a healthy email program — flows should grow to 30–40% of email revenue over time through better post-purchase, winback, and lifecycle flows.

---

## 10. Pre-Build Checklist

Before building any new flow or campaign, verify against this analysis:

**Customer Understanding**:
- [ ] Is this targeting the right seasonal window? (Sep/Mar/Aug/Oct = peak; Jun/Jul/Dec = nurture)
- [ ] Does the segment exclude people already in a higher-priority flow?
- [ ] Does this use click rate (not open rate) for success measurement?

**Audience Hygiene**:
- [ ] Are we suppressing unengaged contacts (Sunset Flow audience)?
- [ ] Are we excluding recent purchasers from sale campaigns?
- [ ] For win-back: is this the Win-Back Opportunities segment (JNTYgB)?

**Flow Architecture**:
- [ ] Is this a new flow or an improvement to an existing draft?
- [ ] Does it feed into the repeat-purchase funnel?
- [ ] Does it avoid competing with the Abandoned Cart / Checkout flows?

**Revenue Measurement**:
- [ ] Is the conversion metric set to VLbLXB (WooCommerce Placed Order)?
- [ ] Is there a 5-day attribution window configured?
- [ ] Are we measuring by click/conversion, not open rate?

---

*Generated: March 2026 | Data source: Klaviyo API v2024-10-15 | Period: Jan 2022 – Mar 2026*
