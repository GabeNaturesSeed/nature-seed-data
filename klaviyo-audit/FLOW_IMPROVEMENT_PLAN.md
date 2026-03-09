# Nature's Seed — Klaviyo Flow Improvement Plan
## Goals 1 & 2: Fill Gaps + Improve Current Setup

> **Date**: March 2026 | Based on: 4-year Klaviyo audit + industry benchmark research
> **North Star**: Grow flow revenue from ~$160K/year (current) to $400K–$700K/year (industry-standard 20–35% of email revenue)

---

## Baseline Reality Check

### Where We Are vs. Where We Should Be

| Metric | Current (NS) | Industry Benchmark | Gap |
|--------|-------------|-------------------|-----|
| Flow revenue as % of email revenue | ~8% | 20–35% | **-$240K to $570K/year** |
| Live flows with meaningful revenue | 3 | 8–12 | 5–9 missing |
| Welcome series RPR | ~$38K/210 = $181 | $2.65–$21 per recipient | Volume too low |
| Cart abandonment RPR | ~$2K/very low volume | $3.65–$14/recipient | Critically underperforming |
| Browse abandonment RPR | ~$1.3K/9 orders | $1.95/recipient | Dead — needs rebuild |
| Winback revenue | $0 | $0.84/recipient (5K segment = $4,200+) | 100% lost |
| Post-purchase flows firing | 3 category-specific | 1 per product category | Volume too low |

**Note on WC revenue history**: The $0 email-attributed revenue in 2022–2023 is a Klaviyo integration artifact, not a reflection of actual orders. WooCommerce orders from 2021 onward exist in WC — they just weren't tracked through Klaviyo attribution. All revenue data used here is 2024–2026 only (post-integration).

---

## GOAL 1: Fill the Gaps

### Gap Analysis: Complete Flow Stack vs. What Exists

| Flow Type | Status | Priority |
|-----------|--------|----------|
| Welcome Series (new sub, non-purchaser) | Draft (NnjZbq / WQBF89) — not live | 🔴 P1 |
| Post-Purchase — Lawn | Draft (XdSdtF) | 🔴 P1 |
| Post-Purchase — Pasture | Draft (VsxGYg) | 🔴 P1 |
| Post-Purchase — Wildflower | Draft (WiP3rK) | 🔴 P1 |
| Winback (rebuilt) | Live but broken (VvvqpW) / Draft 5-stage (WpFDg7) | 🔴 P1 |
| Seasonal Reorder Reminder | Draft (Vzp5Nb, SMZ5NX) | 🔴 P1 |
| Review Request | Test only (XHzESB) — not live | 🟠 P2 |
| Cross-Category Expansion | Draft (Ukxchg) | 🟠 P2 |
| VIP / Loyalty Recognition | Draft (X5iW5B, X4wSKE) | 🟠 P2 |
| Category-Aware Browse Abandonment | Draft (V2q3uA) | 🟠 P2 |
| New Customer Thank You | Draft (HRmUgq) — not live | 🟠 P2 |
| **Back-in-Stock Notification** | ❌ Not built | 🟡 P3 |
| **Planting Success Check-in** | ❌ Not built | 🟡 P3 |
| **Referral / Social Proof** | ❌ Not built | 🟡 P3 |
| **Pre-Season Alert (date-triggered)** | ❌ Not built | 🟡 P3 |
| **Regional Climate Timing** | ❌ Not built | 🟡 P3 |

---

### Gap 1 — Welcome Series (P1) 🔴

**Problem**: The primary subscriber acquisition point has no live welcome flow for new non-purchaser subscribers. The "2025 Welcome Series" draft (NnjZbq) has generated $38K attributed revenue — likely because it was briefly live — but is now showing as draft. The upgraded version (WQBF89, 8 emails) is also draft.

**Industry standard**: Welcome series is the #2 highest-revenue flow behind abandoned cart, generating $2.65–$21/recipient.

**What to build**:
- 5-email welcome series for Newsletter subscribers (non-purchasers)
- Separate 3-email "New Customer Thank You" for first-time buyers
- Both should be persona-branching (Lawn / Pasture / Wildflower) by email 3

**Suggested sequence (Newsletter Welcome)**:
```
Email 1 (Day 0): Brand story + "What seed is right for you?" quiz/guide
Email 2 (Day 3): Educational — How Nature's Seed is different (quality, germination rates)
Email 3 (Day 7): Product spotlight — best sellers by category (dynamic by sign-up source)
Email 4 (Day 14): Social proof + urgency — "X customers planted [product] this season"
Email 5 (Day 21): First-purchase offer (10% off or free shipping) with deadline
```

**Expected lift**: At $2.65 RPR industry average × newsletter list volume (~10K active subs) = **$26,500+ per cohort year**.

---

### Gap 2 — Post-Purchase Flows (P1) 🔴

**Problem**: Three category-specific post-purchase flows exist as drafts (Lawn, Pasture, Wildflower) but are barely active. The Pasture one has $3,813 from only 4 orders — $953 AOV — proving the customer value when they DO receive the flow. Wildflower is $963/7 orders. These work when they fire. They just don't fire often enough or they lack enough emails.

**What each flow needs** (minimum 4 emails per category):
```
Email 1 (Day 1): Order confirmation + "what to expect" planting prep
Email 2 (Day 5): Category-specific care guide (Lawn: soil prep, overseeding tips)
Email 3 (Day 14): "Your seed should be arriving soon / germinating" check-in
Email 4 (Day 30): "How's it looking?" + invite to review + related products
Email 5 (Day 60–90): Seasonal follow-up + reorder prompt (before next planting window)
```

**Missing category**: Clover post-purchase (Clover is a top campaign performer — "Clover Sale", "3/16 Clover Sale" — but has no dedicated post-purchase flow).

**Expected lift**: At $953 AOV × 20 more orders/month activated = **$19,000+/month** from post-purchase alone.

---

### Gap 3 — Seasonal Reorder Reminder (P1) 🔴

**Problem**: Seed is an annual/biennial purchase. The customer who bought lawn seed in March 2024 needs a nudge in February 2025. Neither the Usage-Based Reorder (SMZ5NX, 6 emails) nor the Seasonal Re-Order (Vzp5Nb, 3 emails) have launched.

**The opportunity**: This is nature's seed's most defensible revenue — these customers already bought, already trust the brand. They just need a reminder timed to their planting window.

**Trigger logic**:
```
Trigger: Placed Order → Wait X days (based on product category/season)
  Lawn seed (cool season) → 8–10 months wait → send in fall (Aug–Sep)
  Lawn seed (warm season) → 8–10 months wait → send in spring (Feb–Mar)
  Pasture seed → 10–11 months wait → send in Aug–Sep
  Wildflower → 10–11 months wait → send in Mar–Apr (spring) or Aug–Sep (fall)
  Clover → 10–11 months wait → send in Mar–Apr
```

**Suggested sequence**:
```
Email 1: "It's almost [season] — is your lawn/pasture ready?"
Email 2 (+7 days): Educational — "Signs your [lawn/pasture] needs overseeding"
Email 3 (+14 days): Last chance + offer — "Reorder + save 10% before [season] starts"
```

**Expected lift**: If 20% of past buyers reorder via this flow × $180 AOV × 1,000 past customers = **$36,000/year incremental**.

---

### Gap 4 — Review Request Flow (P2) 🟠

**Problem**: A ShopperApproved test flow (XHzESB) exists but has 0 emails active. Reviews are a conversion driver for new visitors — especially critical for specialty seed products where "did this actually grow?" is the top purchase barrier.

**What to build**:
```
Trigger: Fulfillment/shipment event → Wait 21 days (enough time for germination)
Email 1 (Day 21): "How's your seed doing?" + review request link
Email 2 (Day 35, if no review): Photo prompt + "Show us your results" (UGC play)
```

**Note**: Time this AFTER germination is visible (3–4 weeks for most species). Not at shipping like most ecommerce — that's too early for seed.

---

### Gap 5 — Cross-Category Expansion (P2) 🟠

**Problem**: The draft NS - Cross-Category Expansion (Ukxchg, 2 emails) is not live. Campaign data shows strong results from cross-category sends (Lawn customers + Wildflower angle, Pasture customers + Clover, etc.).

**What to build**:
```
Trigger: Placed Order (segment: Pasture Purchaser, never bought Wildflower)
Email 1 (+30 days): "You planted your pasture — have you thought about pollinators?"
Email 2 (+14 days): "The most popular wildflower blend for pasture properties"
```

Repeat logic for each category pairing:
- Lawn → Wildflower (curb appeal angle)
- Pasture → Clover (feed quality/soil health angle)
- Wildflower → Lawn or Cover Crop
- Any category → Tackifier or soil amendment (the add-on play)

---

### Gap 6 — Completely Missing Flows (P3) 🟡

These don't exist anywhere in the draft library and should be scoped after P1/P2 are complete:

**Back-in-Stock**: When a product that was out of stock comes back, trigger to anyone who browsed that product page. Particularly useful for specialty/seasonal SKUs.

**Planting Success / 60-Day Check-in**: "It's been 60 days — did your [product] germinate?" with embedded care tips and a re-engagement hook. Builds trust, generates UGC, reduces buyer's remorse returns.

**Pre-Season Awareness (date-triggered)**: 6 weeks before spring planting window in customer's region, send a "Get your land ready" email series. Uses region profile property to time correctly.

**Referral Flow**: After a confirmed purchase + review, invite to share with friends. Nature's Seed's customer base (farmers, ranchers, property owners) has strong peer networks — word of mouth is undermonetized.

---

## GOAL 2: Improve Current Live Flows

### Flow 1: Checkout Abandonment (SxbaYQ) — Optimize 🟠

**Current**: 3 emails, $37K revenue, $255 AOV, 145 orders
**Status**: Best-performing flow — working but benchmarks suggest 2-3x more revenue possible

**Issues to fix**:
1. Email 1 subject: Unknown — needs A/B test with urgency vs. benefit framing
2. Email 2 ("Need Help or More Info?") — likely too soft. Should include strong social proof + a specific product recommendation
3. Email 3 ("Last Chance Offer") — confirm it has a real offer (% or $ discount). If it's only free shipping, upgrade to dollar amount off (research shows $ > % for conversions)

**Recommended changes**:
```
Email 1 (1hr): Keep — personal, non-pushy reminder
Email 2 (12hr): Add "why customers love this" block + top 3 review quotes + reply CTA
Email 3 (24hr): Stronger offer — "$15 off your order, expires in 24 hours" with countdown
[Consider Email 4 at 48hr for high cart value (>$150): "Last chance + free shipping"]
```

**Expected lift**: +20–30% conversion rate improvement = +$7,400–$11,100/year

---

### Flow 2: Cart Abandonment (Y7Qm8F) — Investigate + Rebuild 🔴

**Current**: 2 emails, only $2,008 revenue (vs. checkout abandonment's $37K — same intent, 18x less revenue)
**Status**: Something is fundamentally wrong

**Likely issues**:
1. "Added to Cart" trigger fires for people who may also trigger "Started Checkout" → double-triggering with the Checkout Abandonment flow
2. Email 1 timing may be wrong (too early or too late)
3. Email 2 is an "Omni-Channel" message — may be SMS-focused and email-light

**Diagnostic plan before rebuilding**:
- Check: Is there a Klaviyo flow filter preventing people in Checkout Abandonment from entering Cart Abandonment?
- Check: What's the actual send volume (recipients) for this flow vs. the checkout flow?
- Check: What does "Email #2 Omni-Channel" mean in practice — is it sending email at all?

**Recommended changes if diagnosis confirms overlap issue**:
- Add exclusion filter: "Suppress if person started checkout in last 24 hours"
- Or consolidate: Use Cart Abandonment as email 1, then hand off to Checkout Abandonment for emails 2–3

---

### Flow 3: Browse Abandonment Standard (Xz9k4a) — Rebuild Strategy 🔴

**Current**: 4 emails, $1,277 revenue, 9 orders — terrible for 4 emails
**Status**: Low volume AND low conversion. The 4 browsing-persona emails (Pasture, Lawn, Wildflower, Generic) likely aren't segmenting correctly

**Issues**:
1. 4 emails in browse abandonment is too many — industry norm is 2–3
2. Subjects suggest category-based split but the standard flow may not have correct conditional logic to route users
3. The draft "Category-Aware Browse Abandonment" (V2q3uA) would fix this but isn't live

**Recommended approach**:
- Pause the Standard flow (Xz9k4a) after launching the Category-Aware version (V2q3uA)
- Priority: Get V2q3uA live first with 2 emails per category:
  ```
  Pasture browsed → "Still looking for pasture seed?" + top pasture products
  Lawn browsed → "Still looking for lawn seed?" + top lawn products
  Wildflower browsed → "Still looking for wildflower seed?" + visual-led wildflower email
  All others → Generic "You were looking at something special"
  ```
- Industry benchmark: $1.95 RPR × 500 monthly browse abandons = **$975/month = $11,700/year**. Current is $106/year. This is a 100x gap.

---

### Flow 4: Winback Flow (VvvqpW) — Full Rebuild 🔴 CRITICAL

**Current**: 2 emails, $0 revenue, 0 orders
**Status**: Completely broken — the Win-Back Opportunities segment (JNTYgB) has real customers. They're not responding to the current messaging.

**The problem**: Email 2 is titled "Educational" — educational content to a lapsed customer is the wrong medicine. They already know about seeds. They need a reason to come back NOW.

**Root cause hypothesis**:
- Email 1 "Thinking about your land?" — vague. No specific product, no offer, no urgency
- Email 2 "Educational" — passive. Wrong for win-back. Should be an irresistible offer

**Recommended rebuild (5-email sequence from draft WpFDg7)**:
```
Email 1 (Day 0): "We noticed you haven't ordered in a while" — warm, personal, no hard sell
  → Body: What's new at Nature's Seed + 1 product they bought before (dynamic)

Email 2 (Day 5): Urgency + social proof — "X customers replanted [their product] this season"
  → Body: Results/testimonials from customers like them + top products in their category

Email 3 (Day 12): Make an offer — "$20 off, just for you, expires in 48 hours"
  → Body: Dollar amount (not %) + countdown + limited availability hook

Email 4 (Day 20): Last chance — "This is our last email to you about this offer"
  → Body: Simple, short. One CTA. The offer expires.

Email 5 (Day 30): Feedback request — "Before we stop emailing you, can you tell us why?"
  → Body: 3-button survey (moved to competitor / not the right season / budget / other)
  → Route to Sunset flow if no click
```

**Expected lift**: At $0.84 industry RPR × Win-Back segment size — even 500 reactivations/year = **$4,200+ annual recovery**. Currently: $0.

---

### Flow 5: Upsell Flow (VZsFVy) — Rethink Product Logic 🟠

**Current**: 2 emails, $255 revenue, $85 AOV — worst AOV of all flows
**Status**: The product being recommended is the wrong product (too cheap relative to the original purchase)

**Issue**: If someone just bought $200 worth of pasture seed, recommending an $18 Tackifier add-on as Email 1 doesn't move the needle. The "upsell" feels like a $15 after-thought vs. a meaningful enhancement.

**Recommended rethink**:
- Rename mentality: this is a cross-sell/value-expansion flow, not upsell
- Email 1 (1 week post-purchase): Recommend the NEXT category, not an add-on
  - Pasture buyer → "Many pasture owners also plant cover crops" (higher-ticket)
  - Lawn buyer → "Add wildflower accents for curb appeal" (new category)
  - Wildflower buyer → "Native grasses to complement your wildflower planting"
- Email 2 (2 weeks): Tackle add-ons AFTER the cross-category pitch lands: Tackifier, soil amendments, seeding supplies

**Expected lift**: Increase AOV from $85 to $150+ = **3x revenue from same send volume**

---

### Flow 6: Shipment Flow (UhxNKt) — Expand 🟡

**Current**: 1 email, "Your order has been shipped"
**Status**: Transactional only — massive opportunity being wasted

**What it should do** (2–3 emails):
```
Email 1 (Ship confirmation): Tracking link + "What to do while you wait" planting prep guide
Email 2 (Day of delivery): "Your seed should be arriving today" + seed storage tips + start date calc
Email 3 (Day 3 after delivery): "You've had your seed for 3 days — here's your planting guide"
```

This is the highest-trust touchpoint in the entire flow stack (transactional open rates are 60–80%). Using it for one tracking email wastes the relationship window.

---

## Implementation Plan

### Phase 1: Critical Revenue Recovery (March–April 2026)

**Objective**: Stop the bleeding, capture the easiest money

| Action | Flow | Est. Effort | Est. Revenue Lift |
|--------|------|------------|------------------|
| Rebuild Winback Email 2 (immediate) | VvvqpW | 2hrs | $4,200+/year |
| Launch Category-Aware Browse Abandonment | V2q3uA | 4hrs | $10,000+/year |
| Fix Cart Abandonment overlap/timing | Y7Qm8F | 3hrs | $5,000+/year |
| Activate Welcome Series | NnjZbq or WQBF89 | 6hrs | $25,000+/year |

**Phase 1 target lift**: +$44,000+/year from existing drafts + quick fixes

---

### Phase 2: Post-Purchase & Retention (April–May 2026)

**Objective**: Capture repeat purchase value — the biggest long-term lever

| Action | Flow | Est. Effort | Est. Revenue Lift |
|--------|------|------------|------------------|
| Activate Post-Purchase — Lawn + expand to 5 emails | XdSdtF | 6hrs | $15,000+/year |
| Activate Post-Purchase — Pasture + expand to 5 emails | VsxGYg | 6hrs | $15,000+/year |
| Build Post-Purchase — Clover (new) | New flow | 6hrs | $8,000+/year |
| Activate Seasonal Reorder Reminder | Vzp5Nb/SMZ5NX | 8hrs | $36,000+/year |
| Expand Shipment Flow to 3 emails | UhxNKt | 3hrs | $5,000+/year |

**Phase 2 target lift**: +$79,000+/year

---

### Phase 3: Growth Flows (May–July 2026)

**Objective**: Build the flows that separate good email programs from great ones

| Action | Flow | Est. Effort | Est. Revenue Lift |
|--------|------|------------|------------------|
| Launch Review Request Flow | New (from XHzESB) | 4hrs | UGC + trust lift |
| Launch Cross-Category Expansion | Ukxchg | 6hrs | $12,000+/year |
| Launch VIP Recognition Flow | X5iW5B | 4hrs | Retention + AOV |
| Fix Upsell Flow product logic | VZsFVy | 3hrs | +$5,000+/year |
| Build Planting Success Check-in (60-day) | New | 6hrs | Retention + reviews |

**Phase 3 target lift**: +$17,000+/year + significant indirect lift from reviews/trust

---

### Phase 4: Systemic Improvements (Q3 2026)

| Action | Priority |
|--------|----------|
| Build Pre-Season Alert flows (date-triggered, regional) | High |
| Build Back-in-Stock flow | Medium |
| Build Referral / Share flow | Medium |
| Rebuild full 5-stage Win-Back (WpFDg7 draft) | High |
| Optimize Checkout Abandonment Email 3 offer amount | High |

---

## Success Metrics

### How to Measure Each Goal

**Goal 1 (Gap Flows) — Track on activation:**
- Flow entry rate vs. eligible audience size
- Revenue per recipient vs. industry benchmark
- Conversion rate (Placed Order within 7-day attribution window)

**Goal 2 (Improvements) — Track before/after:**
- Click rate on rebuilt flows (not open rate — MPP inflated)
- Revenue per recipient (30-day window)
- Orders attributed per month by flow

**Monthly dashboard targets (after full Phase 1–2 completion):**
| Metric | Current | Target |
|--------|---------|--------|
| Monthly flow revenue | ~$13,000 | $35,000–$50,000 |
| Flow revenue % of email total | 8% | 20–25% |
| Active live flows with >$1K/mo | 3 | 8+ |
| Winback reactivation rate | 0% | 2–5% |
| Browse abandonment RPR | ~$0.14 | $1.50+ |
| Cart abandonment RPR | ~$0.20 | $3.50+ |

---

## Prioritized Quick-Win List (Start Here)

If only 3 things get done this week:

1. **Fix Winback Email 2** — Replace "Educational" with an irresistible offer ($20 off, 48hr expiry). Zero new infrastructure needed. Could generate thousands this month.

2. **Activate Welcome Series** — Pick the best of NnjZbq or WQBF89 and set it live. Every new subscriber currently enters no automation. This is leaving $2–$20 per subscriber on the table every day.

3. **Diagnose Cart Abandonment** — Pull the send volume on Y7Qm8F and compare to checkout abandonment volume. If it's firing at <10% the rate, there's an audience suppression or overlap bug.

---

*Sources:*
- *Klaviyo 2025 Benchmark Report (AMER) — klaviyo.com*
- *Enflow Digital — Ecommerce Email Automation Playbook 2025*
- *Titan Marketing Agency — Klaviyo Replenishment Flow Strategies 2025*
- *Astra Results — E-Commerce Email Flows for Repeat Revenue (Feb 2026)*
- *Flowium — Winback Email Campaigns 2025*
- *Klaviyo Help Center — Post-purchase, replenishment, winback flow guides*
