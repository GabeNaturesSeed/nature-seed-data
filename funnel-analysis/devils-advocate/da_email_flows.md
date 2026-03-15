# Devil's Advocate: Email Flow Claims

**Date**: 2026-03-15
**Purpose**: Systematically challenge 5 claims from the funnel analysis email findings
**Data Sources**: FLOWS_KB.md, REVENUE_KB.md, AUDIENCES_KB.md, email_a/b/c_findings.md, financial_a_findings.md, web research on industry benchmarks

---

## Claim 1: "42 email flows sitting in draft is the #2 retention problem, worth $240-570K/year"

### Counter-Arguments

**1a. The actual count is 36 drafts, not 42 — the number is inflated.**
- FLOWS_KB.md (extracted 2026-03-05) explicitly states: **Live: 9, Draft: 36, Manual: 1, Archived: 0 = 46 total.**
- Agent A says "32 draft flows," Agent B says "42 draft flows," Agent C says "36 draft flows." The agents cannot even agree on the number. The source-of-truth extraction says 36.
- **Rating: STRONG** — The claim uses the highest number across the three agents. The real count is 36.

**1b. Many drafts are duplicates, deprecated versions, or scaffolding — not unique lost opportunities.**
- Examining the 36 drafts reveals significant overlap and redundancy:
  - **3 "Essential Flow Recommendation_" flows** (TSFXi2, SSxD6W, UEXwBr) — these are Klaviyo auto-generated template suggestions, not human-designed flows. They are placeholder recommendations that every Klaviyo account generates.
  - **2 Welcome Series** (NnjZbq and WQBF89) — one is the old version, one is the upgraded replacement. Only one should ever be live. Having both in draft is expected during a transition, not "two lost flows."
  - **2 VIP flows** (X5iW5B from 2026-02-25 and X4wSKE from 2024-07-29) — the newer one replaced the older. This is one opportunity, not two.
  - **2 Winback flows** (WpFDg7 from 2026-02-25 and WLkn9E from 2024-06-13) — same situation.
  - **2 Post-purchase flows per category** in some cases (e.g., VsxGYg "2025 Pasture Post Purchase" and V4LZ22 "Persona Post Purchase 2024") — the 2025 version replaced the 2024 version.
  - **Cart Abandonment has 3 draft versions** (VkBvw5 "Cart Abandonment-GS", WhUxF4 "2025 Cart Reminder Email & SMS", TAMv2i "Checkout Abandonment-GS") — these are iterations, not separate opportunities.
  - **Browse Abandonment has 5+ draft versions** across general, persona-specific, and regional variants — massive overlap.
  - **1 flow has 0 emails** (XHzESB "TEST - ShopperApproved Review Request" has 0 messages) — this is an empty shell, not a lost flow.
  - **1 flow has 0 emails** (VWgJHK "Pasture Persona - Browse Abandonment" has 0 messages) — another empty shell.

  After deduplication, the unique flow *opportunities* number closer to **12-15**, not 36 or 42.
- **Rating: STRONG** — The headline "42 draft flows" dramatically overstates the situation. The real number of unique, non-redundant opportunities is roughly one-third that.

**1c. Some draft flows were deliberately tested and pulled back — draft does not equal "forgotten."**
- Several draft flows have significant revenue attributed to them from test sends:
  - Browse Abandonment General (Rmz2fN): $27,981 from 107 orders
  - 2025 Welcome Series (NnjZbq): $38,037 from 210 orders
  - 2025 Cart (Email & SMS) (WhUxF4): $29,738 from 150 orders
- These were clearly run live at some point and then deliberately moved back to draft. The decision to deactivate may have been intentional (e.g., during the Klaviyo account suspension in Aug-Sep 2025 when 12+ campaigns were cancelled due to policy violations from the cold email program).
- The Aug-Sep 2025 account suspension likely forced an emergency shutdown of flows. Many may not have been re-enabled after reinstatement.
- **Rating: MODERATE** — The suspension explains why flows went to draft, but it does not justify leaving them there for 6+ months afterward.

**1d. The $240K-$570K estimate is speculative and likely inflated.**
- Agent C arrives at this by comparing the 8% flow revenue share to a "20-35% industry benchmark." But:
  - The 8% figure divides $160,792 (flow revenue) by $3,662,841 (total email revenue). However, the total email revenue figure includes ALL of 2024-2026 data, while flow revenue is explicitly labeled as "4-year total." These time windows are inconsistent.
  - The $3.66M "total email revenue" figure does not appear in REVENUE_KB.md. That source shows total 4-year email-attributed revenue of $726,274 (from $724,249 email + $2,025 SMS). Where does $3.66M come from? Agent C may be conflating Klaviyo-tracked revenue ($1,872,949 per Agent A's 12-month figure) with email-attributed revenue.
  - If we use the actual data: $160,792 flow revenue out of $726,274 total email revenue = **22.1%** from flows. This is *within* the 20-35% benchmark range.
  - Even using Agent A's 12-month figures: $95,349 flow revenue out of $370,729 email revenue = **25.7%** from flows. This is solidly within the benchmark.
  - **The 8% figure appears to be calculated incorrectly.**
- **Rating: STRONG** — The revenue gap estimate is built on a flow revenue percentage that contradicts the source data. Using verified numbers, flow revenue share is 22-26%, which is within industry norms.

**1e. The "NS -" prefixed flows were all created on the same date (2026-02-25) — these are freshly built, not long-neglected.**
- 10 flows with the "NS -" prefix were all created/updated on 2026-02-25 — just 18 days before this analysis:
  - NS - Cross-Category Expansion
  - NS - Usage-Based Reorder Reminder
  - NS - SmartLead Lapsed Recapture
  - NS - Welcome Series (Upgraded)
  - NS - Seasonal Re-Order Reminder
  - NS - VIP Recognition & Loyalty
  - NS - Win-Back Enhancement (5-Stage)
  - NS - Browse Abandonment (Category-Aware)
  - NS - Post-Purchase Category Flow
- These were part of the Klaviyo audit improvement plan (see FLOW_IMPROVEMENT_PLAN.md). They are newly created flows in a phased rollout, not abandoned projects.
- **Rating: STRONG** — Counting brand-new flows that are 18 days old as "sitting in draft" misrepresents their status. They are in an active deployment pipeline.

### Verdict: PARTIALLY DISPROVED

The core issue (some flows should be live and are not) has merit, but the claim is materially overstated:
- The count is wrong (36, not 42)
- After deduplication, unique opportunities are ~12-15
- The flow revenue percentage (8%) appears to be calculated incorrectly; actual data shows 22-26%
- 10 of the 36 drafts are brand-new (18 days old) and in active deployment
- The $240K-$570K estimate collapses if the 8% figure is wrong

**Realistic assessment**: There are approximately 8-10 genuinely neglected flow opportunities (the 2025-era flows with proven revenue that were not re-enabled after the account suspension). The revenue gap is more likely $40K-$80K/year, not $240K-$570K.

---

## Claim 2: "Email list is shrinking (-537 in 2.5 months) — compounding loss"

### Counter-Arguments

**2a. A shrinking list can be a sign of HEALTHY list hygiene, not decline.**
- Industry consensus is clear: a smaller, engaged list outperforms a bloated, disengaged one ([Klaviyo](https://www.klaviyo.com/blog/clean-up-email-list-hygiene-process), [Twilio](https://www.twilio.com/en-us/blog/insights/email-list-hygiene-5-tips), [The Digital Merchant](https://thedigitalmerchant.com/email-list-hygiene-best-practices/)).
- Nature's Seed had a Klaviyo account suspension in 2025 due to cold email violations. List cleaning is exactly what SHOULD happen after that kind of deliverability crisis.
- The Sunset Flow (UZf9UD) is live and actively removing disengaged subscribers. Agent A notes it is "suppressing 12,265 profiles." This is intentional hygiene, not passive loss.
- There are segments specifically created for cleaning: "Clean List Mar 2026" (VweMYt), "Cleaning Profiles" (Xyfysn), "Never Engaged (Email)" (SWKXsL, Y9nkTW), "Inactive" segments at 45/60/100 day windows. This is evidence of deliberate, systematic list hygiene.
- **Rating: MODERATE** — The hygiene argument is legitimate, but only partially explains the decline. True hygiene removes bad addresses; the -537 includes people actively unsubscribing, not just suppression.

**2b. The unsubscribes are largely driven by aggressive campaign volume, not a structural problem.**
- 2026 campaign volume is 18.8/month (vs. 6.8/month in 2025) — a 3x increase.
- More sends = more unsubscribes. This is a mechanical relationship, not a list health crisis.
- The unsubscribe rate per campaign is 0.577% — slightly above the 0.5% threshold but not alarming.
- The increased sending is strategically justified: it is spring season (peak buying period for seeds), and the business needs to push hard on the catalog transition messaging.
- **Rating: MODERATE** — Higher send volume partially explains higher unsub volume, but the unsubscribe rate should be monitored.

**2c. The 2.5-month window is misleading — look at the full trend.**
- Looking at AUDIENCES_KB.md subscription trends, the list has been net-negative in MOST months going back to 2022:
  - 2022: Net negative 7 of 12 months (May-Dec all negative)
  - 2023: Net negative 5 of 12 months
  - 2024: Net negative 6 of 12 months (but massive Q3 2024 cold import offset this)
  - 2025: Net negative 10 of 12 months (Aug 2025 bulk import of 20,956 masked this)
- This is a chronic pattern, not a new crisis. The -537 in Q1 2026 is actually LESS severe than Q1 2025 (-415 in Jan-Mar 2025) or Q3-Q4 2024 (-1,707 in Dec alone if you exclude cold imports).
- The "compounding loss" framing is misleading because the list has been buffered by periodic bulk imports. The organic trend has always been negative.
- **Rating: WEAK** — This actually reinforces the claim rather than disproves it. The problem is chronic, which makes it worse, not better. However, it does undermine the implication that Q1 2026 is a sudden deterioration.

**2d. For a seasonal business, off-season list shrinkage is normal.**
- Seed customers buy in spring and fall. Q1 is the ramp-up from the winter trough (Dec 2025 revenue: $35K, the lowest month of the year).
- People who signed up during peak season and see no reason to engage in winter will naturally unsubscribe.
- The real test is whether the list grows during peak season (March-May). The March 2025 data shows +364 new subs, and historically spring months have higher acquisition.
- However, March 2026 data (partial, through March 5) shows only +43 new subs — this IS concerning if it continues.
- **Rating: WEAK** — Seasonal patterns explain some of the decline, but organic acquisition of only 154 subscribers in 2.5 months is genuinely low regardless of season.

### Verdict: PARTIALLY DISPROVED

The list IS shrinking, and that is a real concern. But:
- Some of the decline is intentional hygiene after the 2025 account suspension
- The 3x increase in campaign volume mechanically drives more unsubs
- The chronic nature of this trend means it is not a new crisis — it has been masked by periodic bulk imports
- The framing as "compounding loss" overstates urgency when deliverability improvement from cleaning may offset the raw number decline

**Realistic assessment**: The list shrinkage is a real but moderate concern. The bigger problem is the near-zero organic acquisition (154 subs in 2.5 months), not the unsubscribes. Framing it as "-537 net" buries the lead: the acquisition engine is broken, not the retention engine.

---

## Claim 3: "Welcome Series has only 85 recipients — trigger is broken"

### Counter-Arguments

**3a. The upgraded Welcome Series (WQBF89) was created on 2026-02-25 — it is only 18 days old.**
- FLOWS_KB.md shows WQBF89 was created/updated on 2026-02-25. The analysis is dated 2026-03-15. That is 18 days.
- 85 recipients in 18 days = ~4.7 recipients per day.
- With only 154 new subscribers in all of Q1 2026 (and 43 in March through March 5), the pool of people who COULD enter this flow is tiny.
- If 85 out of ~154 total new subscribers entered the flow, that is a **55% capture rate** — not ideal but far from "broken."
- **Rating: STRONG** — The 85 number is presented without context of when the flow was created. 85 in 18 days with minimal new subscriber acquisition is consistent with low volume, not a broken trigger.

**3b. The old Welcome Series (NnjZbq) was deliberately deactivated, and its revenue was captured while live.**
- NnjZbq generated $38,037 from 210 orders — making it the highest-revenue flow in the account.
- It was moved to draft on 2026-03-05 (the FLOWS_KB extraction date shows it with status "draft" and updated date 2026-03-05). This was done to make way for the upgraded version.
- The transition from old to new welcome series is a planned migration, not a system failure.
- **Rating: MODERATE** — The transition is planned, but the gap between deactivating the old (sometime before 2026-03-05) and scaling the new (2026-02-25 with low volume) means there was likely a period where new subscribers entered neither flow. This IS a problem, just not the one described.

**3c. Agent A pulled 12-month data — but the flow has only existed for 18 days.**
- Agent A's report says "only 85 total recipients across 3 messages" and implies this is over the 12-month analysis period (March 2025 - March 2026). But the flow did not exist until February 25, 2026.
- The framing "85 total recipients" compared to "300+/month expected" sets an expectation based on a full year of operation. The flow has been live for less than 3 weeks.
- **Rating: STRONG** — The comparison is fundamentally unfair. You cannot judge a flow that has been live for 18 days against annual benchmarks.

**3d. The low subscriber acquisition rate is the real constraint, not the trigger.**
- Even if the trigger were working perfectly, there are only ~43 new subscribers in March 2026 (from AUDIENCES_KB). The maximum possible welcome series recipients would be 43, not 300+.
- The problem is upstream (no one is subscribing) not at the flow level (trigger not firing).
- **Rating: STRONG** — The trigger may or may not be broken, but the available evidence is consistent with simply having very few new subscribers.

### Verdict: PARTIALLY DISPROVED

The 85-recipient count is real, but the "trigger is broken" conclusion is unsupported:
- The flow is only 18 days old
- Total new subscribers in Q1 2026 is only 154, so 85 entering the flow is roughly half — which could indicate a trigger issue OR could indicate timing (flow went live mid-period)
- The real problem is subscriber acquisition, not the flow trigger
- However, verifying the trigger is still worthwhile — it is low-cost to check and high-cost if genuinely broken

**Realistic assessment**: The trigger SHOULD be verified (takes 5 minutes), but the claim that 85 recipients proves it is "broken" is not supported by the data. The low number is primarily explained by anemic subscriber acquisition.

---

## Claim 4: "Flows generate only 8% of email revenue vs 20-35% benchmark = $240K-$570K gap"

### Counter-Arguments

**4a. The 8% figure appears to be calculated incorrectly.**
- Agent C's calculation: $160,792 flow revenue / ~$3,662,841 total email revenue = ~8%.
- But REVENUE_KB.md shows total 4-year email-attributed revenue of **$726,274** (email: $724,249 + SMS: $2,025). Where does $3.66M come from?
- The $3.66M figure seems to conflate Klaviyo-tracked total revenue (which includes direct/organic attributed in the Klaviyo dashboard) with email-attributed revenue. These are not the same thing.
- Using verified data:
  - **4-year view**: $160,792 / $726,274 = **22.1% from flows** (within benchmark)
  - **12-month view** (Agent A): $95,349 / $370,729 = **25.7% from flows** (within benchmark)
- Both calculations place Nature's Seed within the 20-35% benchmark range.
- **Rating: STRONG** — The foundational calculation is wrong. The claim evaporates when using correct numbers.

**4b. The 20-35% benchmark is for general ecommerce — seasonal businesses are different.**
- Web research confirms: for general ecommerce, flows generate 30-40% of email revenue ([Klaviyo benchmark report](https://www.klaviyo.com/marketing-resources/ecommerce-benchmarks), [FlowFixer](https://www.flowfixer.com/blog/the-complete-guide-to-klaviyo-flows-for-ecommerce-2026)).
- However, no specific benchmarks exist for agricultural/seasonal ecommerce with 1-2 purchases per year ([Klaviyo Help Center](https://help.klaviyo.com/hc/en-us/articles/360033669452)).
- Seed customers have fundamentally different buying behavior from general ecommerce:
  - Purchase frequency: 1-2x per year (vs. consumables at 4-8x/year)
  - Buying window: concentrated in spring and fall
  - Decision cycle: seasonal, planned purchases (not impulse)
- For a seasonal business, campaigns SHOULD dominate over flows because the revenue comes in concentrated bursts tied to planting seasons. Campaign-heavy revenue allocation (75%+ campaigns) may be structurally appropriate for this business model.
- Browse abandonment and cart abandonment flows fire less often when traffic is concentrated in 4-5 months of the year.
- Post-purchase flows have limited utility when the next natural purchase is 6-12 months away.
- **Rating: MODERATE** — The seasonal argument has merit but does not fully excuse the gap. Even seasonal businesses benefit from well-timed reorder flows, and the welcome series and abandonment flows should perform regardless of seasonality.

**4c. Campaign revenue is strong, which may indicate flows are less critical.**
- Agent A shows campaign performance: 44.7% open rate, 5.48% click rate (above 2-3% benchmark).
- The business generated $1,996,864 in email-attributed revenue in 2025 — a 49.6% increase over 2024.
- If campaigns are already performing above benchmark, the marginal return from additional flow investment may be lower than the raw gap suggests.
- **Rating: WEAK** — Strong campaign performance does not mean flows are unnecessary. They serve different purposes (automated recovery vs. proactive engagement).

### Verdict: DISPROVED

The 8% calculation is wrong. Verified data shows flow revenue at 22-26% of email revenue, which is within the 20-35% benchmark. The $240K-$570K "gap" does not exist as stated.

There IS still room for improvement (moving from 22-26% toward 30-35%), but this represents a much smaller opportunity — perhaps $30K-$60K/year, not $240K-$570K.

---

## Claim 5: "Q1 2026 email revenue is -34% vs Q1 2025"

### Counter-Arguments

**5a. The comparison periods are not equivalent.**
- Agent C states: Q1 2025 = $615,946 vs Q1 2026 = $331,349 = -46% (note: Agent C actually says "54% of Q1 2025" which is -46%, then elsewhere says "-34% YoY pace").
- Let us verify from REVENUE_KB.md:
  - Q1 2025 (Jan+Feb+Mar): $115,283 + $276,568 + $454,095 = **$845,946**
  - Q1 2026 (Jan+Feb+Mar partial): $74,467 + $183,813 + $73,068 = **$331,349**
- But March 2026 data is only through March 5-15 (partial month). Comparing a partial Q1 to a complete Q1 is misleading.
- If we compare Jan+Feb only:
  - Jan+Feb 2025: $115,283 + $276,568 = **$391,851**
  - Jan+Feb 2026: $74,467 + $183,813 = **$258,280**
  - YoY change: **-34.1%**
- The -34% holds for the Jan+Feb comparison, but March 2026 is pacing well: $73,068 in ~15 days, annualizing to ~$146K for the month vs $454,095 in March 2025.
- **Rating: WEAK** — The -34% figure is approximately correct for the completed months (Jan+Feb), though March 2026 is too early to judge.

**5b. The revenue decline is a business-wide problem, not an email-specific problem.**
- Financial findings show overall business metrics:
  - March 2026 MTD revenue: $187,337 vs March 2025 MTD: $171,181 = **+9.4% YoY** (March is actually UP)
  - January 2026 actual: $83,873 revenue (from financial report) — below budget but not catastrophic
  - February 2026: $187,594 — strong
- From Agent A's monthly revenue trend (ALL channels, not just email):
  - Q1 2025: $265,077 (Mar) + $288,111 (Apr) — but these are total revenue, not email-attributed
- The email revenue decline (-34%) may be larger than the overall business decline, which would suggest email IS underperforming. But it may also be an attribution artifact:
  - Email attribution windows and methodology may have changed
  - The 2025 cold email program inflated Q1 2025 email-attributed numbers (cold email campaigns sent to purchased lists would attribute revenue to email even if the customer would have bought anyway)
  - The account suspension in 2025 likely disrupted attribution tracking
- **Rating: MODERATE** — There is a real decline, but email attribution is messy and comparing a period with aggressive cold email campaigns to one without them is not apples-to-apples.

**5c. Q1 2025 was inflated by the cold email program, making the baseline artificially high.**
- AUDIENCES_KB shows Q1 2025 had significant sending activity (864 unsubs in March 2025 alone, indicating heavy volume).
- The cold email program was running in 2025, sending to purchased lists. This would inflate email-attributed revenue because:
  - People receiving cold emails who later purchase get attributed to email
  - The cold program sent to agricultural contacts who may have bought organically
- Comparing Q1 2026 (no cold email program) to Q1 2025 (active cold email program) creates an artificially large decline.
- **Rating: MODERATE** — The cold email program likely inflated 2025 numbers, but we cannot quantify by how much without campaign-level attribution data (which Agent C confirms is missing — the CAMPAIGNS_KB performance table is empty).

**5d. March 2026 is actually showing recovery.**
- March 2026 MTD (14 days): $187,337 revenue, 1,438 orders
- Second-week daily average: $15,717/day (+22% vs first week)
- At this pace, March 2026 could reach $350K-$400K+ in total revenue
- The email contribution to this is $73,068 through ~March 15, annualizing to $146K+ for the month
- This suggests the decline is concentrated in January (which is always the trough for a seed company) and the business is recovering as spring arrives
- **Rating: MODERATE** — March is recovering, but January and February were genuinely weak. The seasonal pattern explains some but not all of the decline.

### Verdict: CLAIM STANDS (with caveats)

The -34% decline in Q1 2026 email revenue is approximately correct for the completed months. However:
- Part of the decline is due to the absence of the cold email program that inflated 2025 numbers
- Part is seasonal (January is always weak for seeds)
- March 2026 is showing strong recovery
- This is more a business-level issue (overall revenue trend, catalog transition) than a pure email execution problem
- Blaming this on "42 draft flows" ignores the much larger factors at play

---

## Overall Assessment

| Claim | Verdict | Severity of Overstatement |
|-------|---------|--------------------------|
| 1. 42 draft flows = $240-570K gap | PARTIALLY DISPROVED | HIGH — count is wrong (36, not 42), ~10 are brand new, many are duplicates, and the revenue estimate is based on a flawed 8% calculation |
| 2. List shrinking (-537) = compounding loss | PARTIALLY DISPROVED | MODERATE — list IS shrinking but partly from intentional hygiene; the real problem is acquisition, not retention |
| 3. Welcome Series 85 recipients = broken trigger | PARTIALLY DISPROVED | HIGH — flow is only 18 days old and subscriber acquisition is near-zero; 85 may be reasonable given the available pool |
| 4. 8% flow revenue vs 20-35% benchmark | DISPROVED | CRITICAL — actual flow revenue share is 22-26% using verified data, which is within the benchmark range |
| 5. Q1 email revenue -34% YoY | CLAIM STANDS (with caveats) | LOW — the number is roughly correct but is partly explained by the absence of the 2025 cold email program, seasonal patterns, and a broader business decline |

### What IS Actually Wrong (After Devil's Advocacy)

After stripping away the overstatements, real problems remain:

1. **Organic subscriber acquisition is critically low** — 154 new subscribers in 2.5 months. This is the actual emergency, not the draft flows or list shrinkage.

2. **The Winback flow generates $0 revenue** — This is confirmed across all sources and is a genuine failure. However, the potential is modest ($2,500-$10,000/year), not the $240K+ claimed.

3. **8-10 proven flows should be re-enabled** — Flows like Browse Abandonment General ($27,981 revenue from tests) and the 2025 Cart flow ($29,738) were turned off during the account suspension and never turned back on. This is a real $40K-$80K/year opportunity.

4. **The catalog transition is the biggest revenue headwind** — 6,682 customers (50.5%) cannot find replacement products for discontinued items. This dwarfs any email flow issue.

5. **January 2026 revenue was genuinely weak** — 48.5% of budget target. This is partly seasonal, partly structural.

### The Biggest Analytical Error in the Original Reports

The foundational claim that "flows generate only 8% of email revenue" is the linchpin for the $240K-$570K opportunity estimate, and it appears to be **calculated using the wrong denominator**. Agent C divided flow revenue ($160K) by a $3.66M figure that likely includes non-email-attributed Klaviyo-tracked revenue. Using the actual email-attributed revenue from REVENUE_KB.md ($726K over 4 years), the flow share is 22%, which is within the industry benchmark. This single error inflates the perceived opportunity by 4-10x.

---

## Sources

- [Klaviyo Ecommerce Email Benchmarks](https://www.klaviyo.com/marketing-resources/ecommerce-benchmarks)
- [Klaviyo Flow Benchmarks Reference](https://help.klaviyo.com/hc/en-us/articles/360033669452)
- [FlowFixer: Complete Guide to Klaviyo Flows 2026](https://www.flowfixer.com/blog/the-complete-guide-to-klaviyo-flows-for-ecommerce-2026)
- [Opensend: Revenue Per Email Subscriber Statistics](https://www.opensend.com/post/revenue-per-email-subscriber-statistics-ecommerce)
- [Klaviyo: Email List Hygiene Best Practices](https://www.klaviyo.com/blog/clean-up-email-list-hygiene-process)
- [Twilio: Email List Hygiene Tips](https://www.twilio.com/en-us/blog/insights/email-list-hygiene-5-tips)
- [The Digital Merchant: Email List Hygiene](https://thedigitalmerchant.com/email-list-hygiene-best-practices/)
- [SmartBug Media: Klaviyo Benchmark Report](https://www.smartbugmedia.com/klaviyo-benchmark-report-strategies)
- [Omnisend: Email Marketing Statistics](https://www.omnisend.com/blog/email-marketing-statistics/)
- [Klaviyo: A/B Testing Flows](https://help.klaviyo.com/hc/en-us/articles/6960371049115)
