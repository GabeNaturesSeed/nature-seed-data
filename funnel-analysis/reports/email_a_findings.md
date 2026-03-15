# Nature's Seed Email Retention Funnel Analysis

**Agent:** Email/Retention Agent A
**Date:** 2026-03-15
**Data Source:** Klaviyo API (Account H627hn) — Live data pull
**Period Analyzed:** March 15, 2025 - March 15, 2026 (12 months)

---

## Email Program Health Score: 5.5 / 10

**Rationale:** The program has a solid checkout abandonment flow generating real revenue and above-average open rates on campaigns, but suffers from critical gaps: the upgraded Welcome Series has barely launched (85 total recipients across 3 messages), 32 flows remain in draft including high-value post-purchase and persona-based abandonment flows, the Winback flow has extremely low click rates, and the subscriber list is shrinking (5,707 email marketing unsubs vs 19,847 new subs, but monthly unsubs consistently exceed new subs outside the Aug 2025 bulk import spike). The flow infrastructure is half-built — the bones are good, but execution is incomplete.

---

## Revenue Overview

| Metric | Value |
|--------|-------|
| Total Klaviyo-Tracked Revenue (12mo) | $1,872,949 |
| Email-Attributed Revenue | $370,729 (19.8% of total) |
| SMS-Attributed Revenue | $2,480 (0.1%) |
| Unattributed Revenue | $1,499,740 (80.1%) |
| Flow-Attributed Revenue | $95,349 (25.7% of email revenue) |
| Campaign-Attributed Revenue (90 days) | $49,501 |

**Key Insight:** 80% of tracked revenue has no email/SMS attribution. This means either (a) direct/organic is carrying the business, or (b) email attribution windows are too narrow. Either way, email should be driving 25-40% of total revenue for a mature ecommerce program — Nature's Seed is at ~20%, leaving an estimated **$93,000-$374,000/year** in unrealized email revenue.

---

## Top 5 Email Optimization Opportunities (Ranked by Revenue Impact)

### 1. ACTIVATE THE 32 DRAFT FLOWS — Estimated Revenue Recovery: $120,000-$180,000/year

**The Problem:** 32 flows sit in draft status, including high-value flows that are *already generating revenue from past test sends*:
- `2025 - Browse Abandonment (General)` (DRAFT): **$23,493 revenue** from 6,302 recipients — this flow WORKS but is not live
- `2025 - Abandoned Cart (Email & SMS)` (DRAFT): **$5,222 revenue** from 1,816 recipients
- `Pasture Post Purchase` (DRAFT): **$3,813 revenue** from 1,994 recipients
- `Lawn Post Purchase` (DRAFT): **$1,143 revenue** from 2,291 recipients
- `Wildflower Browse Abandon` (DRAFT): **$985 revenue** from 930 recipients
- `NS - Cross-Category Expansion` (DRAFT): not yet tested
- `NS - VIP Recognition & Loyalty` (DRAFT): not yet tested
- `NS - Win-Back Enhancement (5-Stage)` (DRAFT): not yet tested

**The Fix:** Prioritize launching these in order:
1. Browse Abandonment (General) — already proven at $3.76 RPR
2. Post-Purchase flows (Pasture, Lawn, Wildflower) — build repeat purchase behavior
3. Cart Abandonment (Email & SMS) upgrade — add SMS to existing flow
4. Cross-Category Expansion — increase AOV
5. VIP Recognition — retain best customers
6. 5-Stage Win-Back Enhancement — replace weak 2-email Winback

### 2. FIX THE WELCOME SERIES — Estimated Revenue Recovery: $30,000-$50,000/year

**The Problem:** Two welcome series exist, both underperforming:
- `2025 - Welcome Series` (NnjZbq) — NOW IN DRAFT, was live. Had 1,376 recipients, $5,408 revenue, but only 29.1% avg open rate (below 50% benchmark)
- `NS - Welcome Series (Upgraded)` (WQBF89) — LIVE but barely used: only **85 total recipients** across 3 messages, $59.99 total revenue

The upgraded series has 8 well-designed messages (buyer/non-buyer splits, category selectors, social proof, urgency coupon) but is not receiving traffic. The old series was deactivated before the new one was proven.

**Individual Message Performance (Upgraded Welcome):**
| Message | Open Rate | Click Rate | Revenue | Recipients |
|---------|-----------|------------|---------|------------|
| Welcome A1 - Hero + Coupon | 41.7% | 16.67% | $0 | 12 |
| Welcome A2 - Category Selector | 47.2% | 0.00% | $60 | 55 |
| Welcome A3 - Education | 41.2% | 5.88% | $0 | 18 |

**The Fix:**
- Verify the Welcome Series (Upgraded) trigger is correctly connected to the Newsletter list signup
- Ensure it is not being suppressed by the old welcome flow
- Target: 50%+ open rate on E1, 5%+ click rate, 2%+ conversion rate
- With ~300+ new subscribers/month flowing through an optimized 8-email series, this should generate $2,500-$4,000/month

### 3. OVERHAUL THE WINBACK FLOW — Estimated Revenue Recovery: $15,000-$25,000/year

**The Problem:** The Winback Flow (VvvqpW) has critically low engagement:
| Message | Open Rate | Click Rate | Conv Rate | Revenue | Recipients |
|---------|-----------|------------|-----------|---------|------------|
| E1 - Thinking about your land? | 45.1% | **1.33%** | 0.19% | $189 | 529 |
| E2 - Educational | 42.2% | **1.47%** | 0.98% | $553 | 408 |

- Click rates of 1.3-1.5% are **far below** the 3-5% benchmark for winback flows
- Only 2 emails in the series — industry best practice is 4-6 emails
- Total revenue: $742 from 937 recipients = $0.79 RPR (should be $3-5+)
- A draft `NS - Win-Back Enhancement (5-Stage)` (WpFDg7) exists but was never launched

**The Fix:**
- Launch the 5-Stage Win-Back Enhancement immediately
- Include: reminder, incentive (10-15% off), social proof, last chance, and sunset
- Add personalization based on purchase history (pasture vs lawn vs wildflower customers)
- Target: 3%+ click rate, 2%+ conversion rate

### 4. SCALE CART & CHECKOUT ABANDONMENT — Estimated Revenue Recovery: $25,000-$40,000/year

**The Problem:** Checkout Abandonment is the #1 revenue-generating flow at $46,174, but cart abandonment is severely underperforming:

**Checkout Abandonment (SxbaYQ) — 3 emails, LIVE:**
| Message | Open Rate | Click Rate | Conv Rate | Revenue | Recipients |
|---------|-----------|------------|-----------|---------|------------|
| E1 - Friendly Reminder | 45.8% | 4.59% | **5.79%** | $38,785 | 2,805 |
| E2 - Need Help | 41.5% | 3.33% | 1.11% | $2,751 | 1,370 |
| E3 - Last Chance | 38.3% | 4.10% | 1.53% | $4,637 | 1,264 |

This is strong — 5.79% recovery on E1 meets the 5-10% benchmark. However:

**Abandoned Cart (Y7Qm8F) — 2 emails, LIVE:**
| Message | Open Rate | Click Rate | Conv Rate | Revenue | Recipients |
|---------|-----------|------------|-----------|---------|------------|
| Cart Abandon E1 | 61.4% | 5.85% | 2.34% | $509 | 172 |
| Cart Abandon E2 | 59.6% | 11.70% | 5.26% | $1,688 | 171 |

The cart abandonment flow has GREAT engagement metrics but **extremely low volume** (172 recipients vs 2,805 for checkout abandonment). This means the "Added to Cart" trigger may not be properly configured, or cart tracking is broken.

**Additionally:** A draft flow `2025 - Abandoned Cart (Email & SMS)` (WhUxF4) has 3 email + SMS messages and generated $5,222 from test sends. This should be launched.

**The Fix:**
- Investigate why cart abandonment volume is 16x lower than checkout abandonment
- Fix the "Added to Cart" metric trigger — likely a WooCommerce tracking issue
- Launch the upgraded Cart Abandonment flow with SMS
- Add a 3rd email to the current cart flow
- Target: matching checkout abandonment volumes (2,800+ recipients) would yield $15,000-$25,000 additional revenue

### 5. LAUNCH POST-PURCHASE FLOWS — Estimated Revenue Recovery: $20,000-$35,000/year

**The Problem:** There is NO live dedicated post-purchase flow. The closest is:
- `New Customer Thank You` (HRmUgq) — only 2 emails, one is a generic thank you, one is an upsell
- `Upsell Flow` (VZsFVy) — 2 emails, $1,154 revenue, decent engagement

Meanwhile, 3 persona-based post-purchase flows sit in DRAFT with proven results:
| Flow | Status | Revenue | Recipients | Open Rate | Click Rate |
|------|--------|---------|------------|-----------|------------|
| Pasture Post Purchase | DRAFT | $3,813 | 1,994 | 46.4% | 3.23% |
| Lawn Post Purchase | DRAFT | $1,143 | 2,291 | 50.4% | 2.90% |
| Wildflower Post Purchase | DRAFT | $125 | 968 | 52.4% | 3.94% |
| NS - Post-Purchase Category Flow | DRAFT | $0 | 0 | — | — |

Also missing:
- **Review request flow** — `TEST - ShopperApproved Review Request` is in draft
- **Reorder reminder** — `NS - Usage-Based Reorder Reminder` is NOW LIVE (good!) with 6 messages
- **Seasonal Re-Order Reminder** — NOW LIVE with 3 messages (good!)

**The Fix:**
- Launch all 3 persona-based post-purchase flows
- Launch the ShopperApproved review request flow
- Build a general post-purchase flow for customers who don't match a persona
- Target: Post-purchase flows should drive 15-20% of total flow revenue

---

## Specific Flow Issues

### Flows with Low Performance

| Flow | Issue | Open Rate | Click Rate | Revenue | Fix |
|------|-------|-----------|------------|---------|-----|
| **Sunset Flow** | 7.7% open on E2, 21.2% on E1 | 14.4% avg | 0.73% | $226 | Expected for sunset — but optimize E1 subject line to recapture |
| **Winback Flow** | Click rates 1.3-1.5% | 43.6% | 1.40% | $742 | Replace with 5-Stage Win-Back Enhancement |
| **Yard Plan Welcome** | Low volume, low open | 26.1% | 2.33% | $280 | Fix trigger; only 164 recipients across 6 messages in 12 months |
| **Welcome Series (Upgraded)** | Barely any volume | 43.3% | 7.52% | $60 | Fix trigger — only 85 recipients total |
| **Shipment Flow** | Low open rate | 34.2% | 10.93% | $98 | Transactional email should have 60%+ open rate — check deliverability |

### Flows That Are Working Well

| Flow | Open Rate | Click Rate | Conv Rate | Revenue | Notes |
|------|-----------|------------|-----------|---------|-------|
| **Checkout Abandonment** | 41.9% | 4.00% | 2.81% | $46,174 | Top performer, E1 has 5.79% conversion |
| **Browse Abandonment - Standard** | 67.5% | 7.19% | 1.95% | $1,277 | Great engagement, low volume |
| **Abandoned Cart Reminder** | 60.5% | 8.77% | 3.80% | $2,198 | Excellent rates, volume is the issue |
| **Usage-Based Reorder** | — | — | — | — | Newly live, good strategic addition |
| **Seasonal Re-Order** | — | — | — | — | Newly live, good strategic addition |

---

## Missing Flows Checklist

| Flow Type | Status | Impact |
|-----------|--------|--------|
| Welcome Series | LIVE but broken (85 recipients) | CRITICAL |
| Cart Abandonment | LIVE but low volume (172 recipients) | CRITICAL |
| Checkout Abandonment | LIVE and working well | OK |
| Browse Abandonment | LIVE (standard) + DRAFT (general, persona) | NEEDS ACTIVATION |
| Post-Purchase | DRAFT only (3 persona flows) | HIGH |
| Winback | LIVE but underperforming | NEEDS OVERHAUL |
| Sunset | LIVE | OK (expected low rates) |
| Reorder Reminder | LIVE (usage-based + seasonal) | OK |
| VIP/Loyalty | DRAFT | MEDIUM |
| Cross-Sell/Upsell | LIVE (basic) | NEEDS UPGRADE |
| Review Request | DRAFT | MEDIUM |
| Birthday/Anniversary | MISSING | LOW |
| Replenishment | LIVE (usage-based) | OK |
| Price Drop | MISSING | MEDIUM |
| Back in Stock | MISSING | LOW-MEDIUM |

---

## Campaign Analysis (Last 90 Days)

### Volume & Frequency
| Month | Campaigns Sent | Notes |
|-------|---------------|-------|
| Dec 2025 | 3 | Dangerously low — holiday season should be 8-12+ |
| Jan 2026 | 10 | Ramping up |
| Feb 2026 | 29 | Heavy send month (Spring push) |
| Mar 2026 (half) | 13 | On pace for 26 |

**Assessment:** Campaign frequency is inconsistent. December was a massive missed opportunity — only 3 campaigns during the holiday season. February/March show aggressive sending which is appropriate for spring (peak season for seed). Recommended: maintain 8-12 campaigns/month year-round, 15-20 during peak seasons.

### Aggregate Campaign Performance (Last 90 Days)
| Metric | Value | Benchmark | Assessment |
|--------|-------|-----------|------------|
| Avg Open Rate | 44.7% | 15-25% | EXCELLENT (likely inflated by Apple MPP) |
| Avg Click Rate | 5.48% | 2-3% | ABOVE BENCHMARK |
| Avg Unsub Rate | 0.577% | <0.5% | SLIGHTLY HIGH |
| Total Revenue | $49,501 | — | Moderate |
| Revenue/Campaign | $643 | — | Below target |
| Total Recipients | 256,420 | — | Good reach |

**Note on Open Rates:** The high open rates (44-80%+) are almost certainly inflated by Apple Mail Privacy Protection (MPP), which auto-opens emails. Real open rates are likely 20-35%. Click rate is a more reliable engagement metric.

### Worst Performing Campaigns (>100 recipients)
Several campaigns showed click rates under 1%:
- One campaign with 456 recipients had 0% open rate (deliverability issue)
- Multiple campaigns with 33,997 and 47,107 recipients had 0.90% and 0.97% click rates respectively — these large-blast, low-engagement campaigns are hurting sender reputation
- Two campaigns targeting 3,919 and 4,421 recipients had 0.33% and 0.46% click rates

**Fix:** Avoid large undifferentiated blasts. Segment campaigns by engagement level and persona. Limit sends to engaged segments for non-critical campaigns.

---

## Segment & List Analysis

### Subscriber Growth (12 months)
| Metric | Count |
|--------|-------|
| New Email Marketing Subscribers | 19,847 |
| Email Marketing Unsubscribes | 5,707 |
| Net Growth | +14,140 |
| Monthly Unsub Rate | ~476/month |

**Concerning Pattern:** The Aug 2025 spike of 18,201 new subscribers was a bulk import (likely the "Old Email List" migration). Excluding that anomaly, organic growth is roughly 137 new subscribers/month — while unsubscribes average 476/month. **The list is shrinking organically.**

Monthly net subscriber analysis (excluding Aug bulk import):
| Month | New Subs | Unsubs | Net |
|-------|----------|--------|-----|
| Mar 2025 | 364 | 676 | -312 |
| Apr 2025 | 385 | 824 | -439 |
| May 2025 | 201 | 587 | -386 |
| Jun 2025 | 83 | 197 | -114 |
| Jul 2025 | 73 | 234 | -161 |
| Sep 2025 | 154 | 758 | -604 |
| Oct 2025 | 135 | 336 | -201 |
| Nov 2025 | 19 | 223 | -204 |
| Dec 2025 | 0 | 291 | -291 |
| Jan 2026 | 10 | 262 | -252 |
| Feb 2026 | 100 | 342 | -242 |
| Mar 2026 | 122 | 251 | -129 |

**CRITICAL:** The list has been net-negative EVERY single month (excluding the bulk import). Total organic attrition: ~3,335 subscribers lost over 12 months. This is unsustainable.

**Fix:**
- Add exit-intent popups with coupon incentive on the website
- Implement a quiz/guide lead magnet (e.g., "Find Your Perfect Seed Mix")
- Add SMS capture at checkout
- Review the Sunset Flow — it's suppressing 12,265 profiles which is aggressive
- Optimize the signup form placement and offer

### Key Segments
| Segment | Purpose | Notes |
|---------|---------|-------|
| Champions (RFM) | Best customers | Has profiles — size unknown without full pagination |
| Win-Back Opportunities | Lapsed customers | Has profiles — needs activation through improved Winback flow |

---

## Benchmarks Comparison

### Flow Performance vs Industry

| Flow | Metric | Nature's Seed | Industry Benchmark | Status |
|------|--------|--------------|-------------------|--------|
| **Welcome Series** | Open Rate | 43.3% (upgraded) | 50%+ | BELOW |
| | Click Rate | 7.52% | 5%+ | ABOVE |
| | Volume | 85 recipients | — | BROKEN |
| **Checkout Abandonment** | Open Rate | 45.8% (E1) | 40%+ | ABOVE |
| | Click Rate | 4.59% | 5%+ | SLIGHTLY BELOW |
| | Recovery Rate | 5.79% | 5-10% | MEETS BENCHMARK |
| **Cart Abandonment** | Open Rate | 61.4% (E1) | 40%+ | EXCELLENT |
| | Click Rate | 5.85% | 5%+ | MEETS BENCHMARK |
| | Recovery Rate | 2.34% | 5-10% | BELOW (E1 only) |
| | Volume | 172 recipients | — | CRITICALLY LOW |
| **Browse Abandonment** | Open Rate | 67.5% | 35-45% | EXCELLENT |
| | Click Rate | 7.19% | 3-5% | EXCELLENT |
| **Winback** | Open Rate | 43.6% | 20%+ | ABOVE |
| | Click Rate | 1.40% | 3-5% | CRITICAL FAIL |
| **Post-Purchase** | — | NO LIVE FLOW | 40%+ open | MISSING |
| **Campaigns** | Open Rate | 44.7% (MPP inflated) | 15-25% | LIKELY OK |
| | Click Rate | 5.48% | 2-3% | ABOVE |

---

## Estimated Revenue Leakage from Missing/Broken Flows

| Issue | Annual Revenue Leak | Confidence |
|-------|-------------------|------------|
| Draft flows not activated (Browse, Post-Purchase, Cart upgrade) | $60,000 - $100,000 | HIGH — proven revenue from test sends |
| Welcome Series broken (85 recipients vs 300+/mo expected) | $30,000 - $50,000 | MEDIUM — based on old series revenue |
| Winback Flow underperforming | $15,000 - $25,000 | MEDIUM — based on benchmark RPR |
| Cart Abandonment volume issue | $25,000 - $40,000 | HIGH — 16x volume gap vs checkout |
| Missing post-purchase flow (general) | $10,000 - $20,000 | MEDIUM |
| Missing VIP/loyalty flow | $5,000 - $15,000 | LOW-MEDIUM |
| December campaign gap | $5,000 - $10,000 | MEDIUM — holiday revenue missed |
| List shrinkage (organic decline) | $10,000 - $20,000 | MEDIUM — fewer recipients = less revenue |
| **TOTAL ESTIMATED LEAK** | **$160,000 - $280,000/year** | |

---

## Immediate Action Items (Priority Order)

1. **FIX Welcome Series trigger** — The Upgraded Welcome (WQBF89) is live but only 85 people have entered it in 12 months. Check the list trigger, ensure the old series (NnjZbq) is not capturing subscribers first.

2. **Activate Browse Abandonment (General)** — Already proven at $3.76 RPR with $23,493 revenue from drafts. Turn it live.

3. **Investigate Cart Abandonment volume** — Why are only 172 people entering the cart flow when 2,805 enter checkout abandonment? Fix the "Added to Cart" metric trigger in WooCommerce.

4. **Launch 3 persona post-purchase flows** — Pasture, Lawn, Wildflower are built and tested. Turn them live.

5. **Replace Winback with 5-Stage Enhancement** — Current 2-email flow has 1.4% click rate. The draft 5-stage version should be tested and launched.

6. **Implement list growth strategy** — Exit-intent popup, quiz lead magnet, and homepage signup optimization to reverse the organic subscriber decline of ~275/month.

7. **Stabilize campaign frequency** — Maintain minimum 8 campaigns/month even in offseason. December with only 3 campaigns was a costly miss.

8. **Reduce large undifferentiated blasts** — Several campaigns sent to 30,000-47,000 recipients had under 1% click rates. Segment by engagement and persona.

9. **Launch review request flow** — ShopperApproved integration exists, test flow is in draft. Social proof drives conversions.

10. **Add Price Drop and Back-in-Stock flows** — Standard ecommerce flows that are completely missing.

---

## Data Appendix

### Email Engagement Summary (12 months)
| Metric | Total | Unique |
|--------|-------|--------|
| Emails Received | 1,340,563 | 634,655 |
| Emails Opened | 980,698 | 300,572 |
| Emails Clicked | 39,622 | 22,106 |
| Emails Bounced | 21,904 | 19,136 |
| Marked as Spam | 441 | 371 |

**Derived Rates:**
- Overall Open Rate: 73.2% (heavily MPP-inflated)
- Overall Click Rate: 2.96%
- Bounce Rate: 1.63%
- Spam Rate: 0.03% (healthy)
- Click-to-Open Rate: 4.04%

### Monthly Revenue Trend (All Channels)
| Month | Revenue | Orders |
|-------|---------|--------|
| Mar 2025 | $265,077 | 1,537 |
| Apr 2025 | $288,111 | 1,589 |
| May 2025 | $177,205 | 1,129 |
| Jun 2025 | $55,527 | 340 |
| Jul 2025 | $42,923 | 236 |
| Aug 2025 | $116,852 | 617 |
| Sep 2025 | $219,664 | 1,073 |
| Oct 2025 | $151,696 | 796 |
| Nov 2025 | $63,402 | 312 |
| Dec 2025 | $35,536 | 212 |
| Jan 2026 | $74,467 | 420 |
| Feb 2026 | $183,813 | 985 |
| Mar 2026 (partial) | $198,675 | 1,406 |

**Seasonality:** Clear spring peak (Mar-May), fall secondary peak (Aug-Oct), winter trough (Nov-Jan). Email strategy should align with these cycles.

### Flow Revenue Attribution (12 months)
| Flow | Revenue | Orders | Status |
|------|---------|--------|--------|
| Checkout Abandonment | $46,174 | 200 | LIVE |
| Browse Abandonment (General) | $23,493 | 81 | DRAFT |
| 2025 Welcome Series | $5,408 | 26 | DRAFT |
| 2025 Cart Abandon (SMS+Email) | $5,222 | 26 | DRAFT |
| Pasture Post Purchase | $3,813 | 4 | DRAFT |
| Abandoned Cart Reminder | $2,198 | 13 | LIVE |
| Cart Abandonment GS | $1,730 | 10 | DRAFT |
| Browse Abandonment Standard | $1,277 | 9 | LIVE |
| Upsell Flow | $1,154 | 7 | LIVE |
| Lawn Post Purchase | $1,143 | 9 | DRAFT |
| Tracking ID Flow | $1,048 | 5 | DRAFT |
| Wildflower Browse Abandon | $985 | 7 | DRAFT |
| Winback Flow | $742 | 5 | LIVE |
| Yard Plan Welcome | $280 | 1 | LIVE |
| Sunset Flow | $226 | 2 | LIVE |
| Regional Browse Heartland | $160 | 1 | DRAFT |
| Wildflower Post Purchase | $125 | 2 | DRAFT |
| Shipment Flow | $98 | 2 | LIVE |
| Welcome Series (Upgraded) | $60 | 1 | LIVE |

**Key Finding:** Draft flows have generated **$43,178 in revenue** from test sends alone. If activated at scale, these represent massive untapped revenue.
