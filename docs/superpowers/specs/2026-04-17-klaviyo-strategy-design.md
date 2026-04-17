# Klaviyo Strategy & Measurement Framework — Design Spec

**Date**: 2026-04-17
**Scope**: Subsystem A of the Klaviyo overhaul — Strategy & Measurement. Subsystem B (Creative Production System — templates, images, product links) is deferred to a separate spec.
**Status**: Ready for user review, then implementation planning

---

## Purpose

Make every Klaviyo decision traceable to the retention/LTV goal, within deliverability-safe guardrails, with a weekly feedback loop.

The framework replaces ad-hoc campaign decisions (which produced 95 campaigns in 69 days at an average RPR of $0.21) with a structured decision-tree that gates every send against segment goals, cadence caps, offer rules, and deliverability health.

---

## Key Definitions

- **Peak seasons**: February–April (spring planting) and September–October (fall overseed). Used to gate aggressive cadence, seasonal broadcast offers, and higher-frequency sale moments.
- **Low seasons**: May–August and November–January. Conservative cadence default, zero broadcast discounts except BFCM in late November.
- **Reorder window** (per category, based on 8–11 month replant cycle):
  - Lawn cool-season → trigger Aug–Sept (prev year Feb–Mar purchase)
  - Lawn warm-season → trigger Feb–Mar (prev year Aug–Sept purchase)
  - Pasture → trigger Aug–Sept
  - Wildflower → trigger Mar–Apr (primary) or Aug–Sept (secondary)
  - Clover → trigger Mar–Apr
  - Cover Crop → trigger Aug–Sept
- **Aggressive mode**: unlocked only when all 4 deliverability gates (§2.2) pass on rolling 30 days. Default state: conservative.
- **Engagement gate**: every broadcast must include E60D (`RbH7na`) or E90D (`VduUfa`) segment in the audience; NOT-E60/NOT-E90 are never included in broadcasts.

---

## Strategic Decisions (Locked)

| Decision | Choice | Rationale |
|---|---|---|
| **Primary business goal** | Retention / LTV | Seed buyers replant annually — repeat-purchase is the most defensible revenue lever. Current repeat rate 1.03 orders/buyer leaves room. |
| **Primary cohort** | Replant Moment (Warm RFM `WdpJti`) | Spring 2025 buyers are due for reorder NOW. Projected $36K+/year from Seasonal Reorder flow alone. |
| **Quick win before main lever** | Fix Winback flow (`VvvqpW`) | Currently 0.13% conversion on 774 sends — rated D. Fast to ship, proves framework, frees focus for Replant work. |
| **Ops model** | Hybrid D — autonomous on flows, approval-gated on broadcasts | Flows have stable rules → agent autonomy is safe. Broadcasts have blast-radius risk → user gate. |
| **Framework architecture** | Hybrid rules + principles + playbooks | Strict rules for blast-radius guardrails (frequency, offers, gates). Principles + playbooks for everything else. Auditable: every decision traces to a rule or principle. |
| **Cadence** | RFM-tiered caps × seasonal mode | Starts conservative Spring 2026 to rebuild deliverability; unlocks aggressive mode only after deliverability gates pass. |
| **Offer philosophy** | Targeted + seasonal-dynamic (B + D overlay), 15% max discount cap | Winback/VIP/Welcome get standing offers; peak seasons get 2 broadcast sale moments; low seasons get zero broadcast discounts except BFCM. `$` off preferred over `%` for AOV ≥$100. |
| **North Star metric (agent steering)** | C — Flow revenue % of email revenue (current 8% → 20–25% target) | Measures whether the retention engine is being built. |
| **Secondary metric (new-customer acquisition flows)** | A — Email-attributed revenue, RPR for Cart/Browse/Checkout recovery flows | These flows serve new customers, so measure conversion directly. |
| **Review cadence** | Weekly file drops + monthly strategic review | No Telegram — files in `marketing/klaviyo-audit/reviews/` with inline approvals. |

---

## Section 1 — Segment → Goal → Action Matrix

### 1.1 RFM Lifecycle (the retention spine)

| Segment | Goal | Primary Channel | Success Metric |
|---|---|---|---|
| `T93fB3` New Customer | Drive 2nd purchase within 180d | Welcome + Post-Purchase flows | % → Active Customer in 180d |
| `VtKptn` Active Champions | VIP retention; protect crown jewel | Exclusive-access campaigns, VIP flow | % stay Champions 90d |
| `RAQTca` Champions | Reactivate dormant champion behavior | Category-expansion flow + targeted campaigns | % → Active Champion 60d |
| `RbGRqF` Active This Season | Encourage same-season 2nd order | Cross-sell flow, category-specific campaigns | Items/order lift |
| `WdpJti` Warm | 🎯 **REPLANT NUDGE — #1 priority** | Seasonal Reorder flow (category × season) | % → Active Champion next season |
| `RyASXF` At Risk | Winback before lapse | Winback flow ($15 off email 3) | % → Warm+ in 30d |
| `Sv5cSC` Lapsed | Final reactivation push | Extended Winback ($20 off + urgency) | % → Warm+ in 60d, else sunset |
| `WjzuUj` Dormant | Annual re-permission only | Minimal — sunset candidate | Suppress from broadcasts |

### 1.2 Category purchasers (the what-to-send spine)

| Segment | Primary Use |
|---|---|
| `Ra4637` Lawn Purchasers | Replant timing (cool/warm season), Wildflower cross-sell, Planting Aids upsell |
| `T6TJd6` Pasture Purchasers | Replant timing, Clover/Cover Crop cross-sell |
| `TJpLMz` Wildflower Purchasers | Replant timing, Native grass cross-sell, Tackifier upsell |
| `XJbjnv` Other Purchasers | Primary-category discovery (quiz/guide) |

### 1.3 Engagement tiers (the gatekeeper)

| Segment | Role |
|---|---|
| `VKVpf9` E30D Highly Engaged | Test audience for new content, early-access sends |
| `RbH7na`/`VduUfa` E60D/E90D | **Primary broadcast audiences** — include in all broadcasts |
| `Y87Rfk`/`VirYfN` NOT-E60/E90 | **SUPPRESS from broadcasts** — flow-only, sunset-bound |

### 1.4 Regional (the timing modifier)

`XTeFkg` CA, `Vh7uqd` TX, `Tyumbj` FL → climate-adjusted planting-window campaigns only; not primary segments.

### 1.5 The rule: "no orphan sends"

Every send must map to (RFM goal) × (Category context) × (Engagement gate). A broadcast lacking all three is rejected at the proposal stage.

---

## Section 2 — Strict Rules (Guardrails)

### 2.1 Frequency Caps (per person, rolling 7 days, all channels combined)

| Segment | Conservative Mode *(current — Spring 2026)* | Aggressive Mode *(unlocked only after gate pass)* |
|---|---|---|
| Active Champions (`VtKptn`) | 3/week | 4/week |
| Champions (`RAQTca`) | 2/week | 3/week |
| Active This Season (`RbGRqF`) | 2/week | 3/week |
| Warm (`WdpJti`) — reorder window | 2/week | 3/week |
| Warm — outside reorder window | 1/week | 2/week |
| New Customer (`T93fB3`) | Flow cadence only (no broadcast layer) | Flow + 1 broadcast/week |
| At Risk / Lapsed (`RyASXF`/`Sv5cSC`) | 1/week, max 4 total in winback sequence | Same (never aggressive — fragile) |
| Dormant (`WjzuUj`) | 0 broadcasts; flow-only; suppress from campaigns | Same |
| NOT-E60 / NOT-E90 | 0 broadcasts ever | 0 broadcasts ever |

**Enforcement**: Before any campaign is drafted, run an overlap check — count past-7d + scheduled-next-7d sends per audience. If any audience exceeds cap, shrink send or delay.

### 2.2 Mode-Switching Gates (Conservative → Aggressive)

All four must hold on rolling 30-day basis:

1. Net list growth ≥ 0 (current: -558 YTD — primary blocker)
2. Spam complaint rate < 0.1% (current: 0.02% ✅)
3. Hard bounce rate < 1% (current: <0.1% ✅)
4. Unsubscribe rate < 0.3% per send (current: borderline)

One mode check per month, during the monthly strategic review. Failing any gate at any weekly check auto-drops to conservative with an alert file.

### 2.3 Offer Rules

- **Max discount cap: 15%.** `$` off preferred over `%` for AOV ≥$100 orders.
- **Standing-offer slots** (always allowed, don't consume seasonal budget):
  - Winback email 3: $15 off
  - Lapsed Winback email 3: $20 off
  - Welcome email 5: 10% off first purchase
  - VIP Champions: early access + free shipping (not %)
- **Seasonal-broadcast offers**:
  - Peak seasons (Feb–Apr, Sept–Oct): max 2 sale moments per peak, max 15% off
  - Low seasons (May–Aug, Nov–Jan): zero broadcast discounts except BFCM
- **Anti-patterns (auto-rejected)**:
  - >2 discount broadcasts in 30-day window
  - Discount to a segment already inside a discount-bearing flow
  - Discount to Dormant or NOT-E90

### 2.4 Suppression Rules (applied to all sends, flows and broadcasts)

- Bought in last 48h → suppress from broadcasts
- Currently in active flow → suppress from overlapping broadcasts
- NOT-E90 → suppress from all broadcasts
- Unsubscribed from email (≤730d) → permanent suppress
- Bounced ≥2 times in 30d → suppress until re-verification

### 2.5 Approval Gates (per Hybrid D ops model)

| Decision | Approval Required? |
|---|---|
| New flow activation | ✅ Yes |
| Existing flow: copy or offer amount change | ✅ Yes |
| Existing flow: A/B variant rotation | ❌ No |
| Broadcast campaign (any segment) | ✅ Yes — always |
| Flow suppression additions | ❌ No |
| Cadence mode switch | ✅ Yes (monthly) |
| Offer rule exceptions (>15% request) | ✅ Yes (explicit override) |

---

## Section 3 — Flow Priority Stack

### Phase 0 — Week 1 (Quick Wins)

| Action | Flow | Owner | Estimated Lift |
|---|---|---|---|
| Fix Winback: rewrite email 2, add emails 3–5 with $15/$20 offer + urgency | `VvvqpW` → migrate to `WpFDg7` 5-stage draft | Agent (autonomous) | $4K+/yr |
| Apply suppression rules (NOT-E90, 48hr-purchase, in-flow overlap) to all live flows | All live flows | Agent (autonomous) | Deliverability ↑ |
| Deliverability gate audit: baseline against 4 gate thresholds | — | Agent → weekly report | Unlocks mode switch |

### Phase 1 — Weeks 2–3 (The Replant Engine + Welcome)

| Action | Flow | Owner | Estimated Lift |
|---|---|---|---|
| **Build Seasonal Reorder Reminder** (category × season: lawn cool/warm, pasture, wildflower, clover) — trigger on Warm RFM entry | `Vzp5Nb` / `SMZ5NX` drafts → activate | Agent builds, user approves | **$36K+/yr** |
| Activate Welcome Series (5 emails, persona-branching by email 3) | `WQBF89` draft | Agent builds, user approves | $25K+/yr |

### Phase 2 — Weeks 4–6 (New-Customer Recovery + Post-Purchase)

| Action | Flow | Owner | Estimated Lift |
|---|---|---|---|
| Launch Category-Aware Browse Abandonment (2 emails × 4 personas) | `V2q3uA` → activate, pause standard `Xz9k4a` | Agent builds, user approves | $10K+/yr |
| Diagnose + fix Cart Abandonment overlap with Checkout Abandon | `Y7Qm8F` | Agent (diagnosis autonomous; fix = approval) | $5K+/yr |
| Activate Post-Purchase flows: Lawn, Pasture, Wildflower + **new Clover** (5 emails each) | `XdSdtF`, `VsxGYg`, `WiP3rK`, new | Agent builds, user approves | $50K+/yr |

### Phase 3 — May–June (Trust + Cross-Sell Depth)

| Action | Flow | Owner | Estimated Lift |
|---|---|---|---|
| Expand Shipment Flow to 3 emails (tracking + planting prep + post-delivery) | `UhxNKt` | Agent (autonomous) | $5K+/yr |
| Launch Review Request Flow — Day 21 post-delivery (after germination) | New (from `XHzESB` test) | Agent builds, user approves | UGC + trust |
| Fix Upsell Flow: swap add-on logic for next-category cross-sell | `VZsFVy` | Agent (autonomous) | $5K+/yr |

### Phase 4 — July–August (Summer Low-Season Build)

| Action | Flow | Owner |
|---|---|---|
| Launch Cross-Category Expansion (Lawn→Wildflower, Pasture→Clover, etc.) | `Ukxchg` draft | Agent + approval |
| Launch VIP Recognition for Champions | `X5iW5B` draft | Agent + approval |
| Build Planting Success Check-in (60-day post-delivery) | New | Agent + approval |

### Phase 5 — September Peak Prep (reassess mode)

- Monthly review: do all 4 deliverability gates pass? If yes → unlock aggressive mode for fall peak
- Build Pre-Season Alert (date-triggered by region) for Sept overseed
- Build Back-in-Stock + Referral flows
- Full 5-stage Winback rebuild if Phase 0 version validates the approach

### Cumulative target

If Phase 0–3 ships on time, monthly flow revenue moves from ~$13K to ~$35–50K, putting flow share of email revenue on track from 8% → 20% (primary C-metric North Star).

---

## Section 4 — Campaign Decision Tree + Engagement Playbook

### 4.1 Campaign Proposal Decision Tree

Every broadcast must pass all 6 checks. Failing any one = auto-rejected.

1. **Goal check** — Which business goal? (Replant / Acquisition recovery / Retention depth / Seasonal moment). "None" → reject.
2. **Audience check** — (RFM tier) × (Category or Regional context) × (E60D or E90D engagement gate). "All subscribers" or non-starred segment → reject.
3. **Cadence check** — Has audience received ≤ (tier cap – 1) sends in past 7d AND not scheduled next 7d? If cap breached → shrink or delay.
4. **Suppression check** — Excludes: bought-48hr, in-active-flow, NOT-E90, unsubscribed-730d? Missing → auto-apply.
5. **Offer check** — If offer: inside 15% cap, allowed slot, not double-dipping active-flow offer? If no → reject.
6. **RPR target check** — Expected RPR ≥ $0.50 for targeted segment, ≥ $0.15 for broader. Below → reject or reframe.

Output: one-page proposal doc per campaign, 6 checks shown as ✅/❌, plus subject line, audience size, estimated RPR, offer terms. User approves or kicks back in the weekly review file.

### 4.2 Subject Line Playbook

**Rules**:
- <50 characters (mobile truncation)
- Benefit-led, not feature-led
- Personalization variable when data exists (`{{ first_name|default:"there" }}`, `{{ last_category_purchased }}`)
- Emoji: seasonal only (🌱 spring, 🍂 fall), max 1, never in every send
- **Forbidden**: all caps, "FREE", multiple `!`, "SAVE NOW", "$$$", "ACT NOW"

**Pattern library** (expand via testing):
- Reorder: `Time to reorder your {{category}}?`
- Winback: `We miss you — $15 off to come back`
- Educational: `How to tell if your {{category}} needs overseeding`
- Seasonal: `Spring is here — plan your {{category}}`
- Social proof: `1,247 customers planted this in March`
- Urgency: `Last day — spring seed ends Friday`

### 4.3 Send Time Playbook

- **Default**: Klaviyo Smart Send Time (respects individual open behavior; ~5% open-rate lift)
- **Override** for time-sensitive sends (flash, last-day): Tuesday 10am MST
- **Regional sends**: use recipient's local TZ (CA=PT, TX=CT, FL=ET)
- **Never send**: Monday before 9am, after 7pm any day, Saturdays to DTC, weekends to Hedgerow B2B

### 4.4 A/B Testing Discipline

- **One** variable per campaign (subject line OR CTA OR hero — never multiple)
- Sample: 10% per variant, minimum 1,000 per arm; decide winner at 48h
- Metric: open rate for subject tests; click rate for body tests; RPR for offer tests
- Minimum detectable effect: 5% relative. Inconclusive (±3%) → keep control
- Every test logged to `marketing/klaviyo-audit/tests/YYYY-MM-DD-test-name.md`
- Re-test winners quarterly (audience preferences drift)

### 4.5 Personalization Depth (ratchet up)

| Level | Required | Applies To |
|---|---|---|
| Min | First name fallback, unsubscribe link, preview text (<90 chars) | Every send |
| Mid | Last-purchased category in product recs; regional weather/planting window | All retention sends |
| Max | Dynamic product feed from viewed/purchased catalog; review quotes from same category; reorder link with past SKU | Reorder + Winback + VIP sends |

### 4.6 Auto-flagged patterns (never ships)

- Subject >50 chars
- All-caps words
- Image-only email (no fallback text) — Gmail image proxy shows blank
- >2 competing CTAs
- Broken or redirect-chain links
- Missing `{% unsubscribe %}` tag (CAN-SPAM violation)

---

## Section 5 — Measurement & Review OS

### 5.1 KPI Tiers

| Tier | Metric | Formula | Current | 90d Target | 12mo Target |
|---|---|---|---|---|---|
| **Primary (agent's steering metric)** | Flow revenue % of email revenue | `flow_revenue / (flow_revenue + campaign_revenue)` | 8% | 15% | 20–25% |
| **Secondary (acquisition flows)** | Cart/Browse/Checkout recovery RPR | `revenue / recipients` | $3.44–$9.30 | $5+ avg | $8+ avg |
| **Board-facing** | Email-attributed % of WC revenue | `email_revenue / total_wc_revenue` | 22% | 24% | 28–30% |
| **Long-horizon** | Repeat purchase rate (12mo rolling) | `orders / unique_buyers` | 1.03 | 1.10 | 1.25 |
| **Health gates (binary)** | Net list growth, spam, bounce, unsub | See 2.2 | Failing #1 | Pass all 4 | Pass all 4 |

### 5.2 Weekly Review File (every Monday)

**Location**: `marketing/klaviyo-audit/reviews/weekly/YYYY-MM-DD-weekly-review.md` (date = that Monday)

**Template sections** (agent fills by 9am MST Monday):

1. Week at a glance — sends, recipients, opens, clicks, revenue; tier-1 metric movement
2. Flow scorecard — per live flow: recipients, RPR, conv %, vs last week
3. Campaign scorecard — what sent, to whom, RPR, winners/losers
4. Segment health check — RFM movement, list growth, engagement tiers
5. Deliverability gate snapshot — 4 gates as ✅/❌
6. Agent self-grade — A/B/C/D with one-line reasoning
7. Anomalies / wins
8. Proposed next-week calendar — 3–7 proposals, each with 6-step decision-tree check, awaiting approval
9. One experiment recommendation
10. Approvals area — inline kick-back: `✅ APPROVED`, `❌ REJECTED`, `🔄 REVISE`

### 5.3 Monthly Strategic Review (first Monday of each month)

**Location**: `marketing/klaviyo-audit/reviews/monthly/YYYY-MM-monthly-review.md`

**Extra sections**:
1. MoM + YoY scorecard
2. Flow stack status — shipped, on deck, kill candidates
3. RFM lifecycle movement (Warm→Champion wins, Active→Warm losses)
4. **Mode-switch decision** — all 4 gates green on 30d rolling? Propose aggressive unlock
5. Offer-rule review — exception requests, rule violations caught
6. Test roll-up from `tests/` folder
7. Strategic questions for user judgment

### 5.4 Alert Triggers

File location: `marketing/klaviyo-audit/alerts/YYYY-MM-DD-HH-alert-{type}.md` (no Telegram — per user's file-based preference)

| Trigger | Severity | Action |
|---|---|---|
| Flow conversion drops >30% WoW | High | File alert + propose root-cause investigation |
| Spam rate >0.1% in 24h | Critical | File alert + auto-pause all broadcasts pending review |
| Bounce rate >2% on any send | High | File alert + flag audience for suppression |
| Campaign unsub rate >1% | High | File alert + document in tests folder |
| Frequency cap breached by scheduled send | Critical | File alert + auto-block send |
| Deliverability gate fails during weekly check | Medium | File alert + drop to conservative if in aggressive |
| Net list growth turns positive (rolling 30d) | Info | File alert — triggers mode-switch decision next monthly |

### 5.5 Agent Self-Grading (weekly, auto-computed)

- **A** — Primary metric (C) grew ≥5% WoW, all 4 gates passing, no critical alerts
- **B** — Primary metric flat or grew <5%, gates passing, no critical alerts
- **C** — Primary metric shrank, OR 1 gate failing, OR 1+ medium alerts — investigation required
- **D** — 2+ gates failing, OR any critical alert, OR flow revenue dropped >10% — immediate remediation

Three consecutive C/D weeks → escalation: agent proposes a framework audit in the next monthly review.

### 5.6 File Organization

```
marketing/klaviyo-audit/
├── reviews/
│   ├── weekly/YYYY-MM-DD-weekly-review.md    (every Monday)
│   └── monthly/YYYY-MM-monthly-review.md     (first Monday of month)
├── alerts/YYYY-MM-DD-HH-alert-{type}.md      (event-driven)
├── tests/YYYY-MM-DD-test-{name}.md           (every A/B result)
├── flows/{flow_id}.md                        (one doc per live flow — copy, cadence, offer, last-changed)
├── campaigns/YYYY-MM-DD-{name}.md            (one doc per sent broadcast — proposal + outcome)
└── STRATEGY_SPEC.md                          (symlink/copy of this spec for quick access)
```

---

## Out of Scope (deferred to follow-up specs)

- **Creative Production System (Subsystem B)** — template rules, image libraries, product-link patterns, brand enforcement. User will upload creative improvements separately.
- **Seasonality Calendar Visualization** — per-category × per-month strategy view (planting windows, cadence mode, messaging angle, offer type). Queued after both Subsystem A + B ship. Will use WooCommerce + Klaviyo APIs + USDA planting-zone data.
- **SMS strategy** — SMS list is much smaller (~$2K of lifetime revenue); not addressed in this spec. Future work if list grows.
- **Hedgerow (B2B) strategy** — separate list, different sender persona, different cadence norms. Not in scope.

---

## Open Questions (none blocking)

All strategic decisions are locked via the brainstorming session on 2026-04-17. Implementation-level questions will surface during the writing-plans step.

---

## Implementation

Next step: invoke `superpowers:writing-plans` to convert this design into a step-by-step implementation plan with review checkpoints, starting with Phase 0 (Winback fix + suppression rules application).
