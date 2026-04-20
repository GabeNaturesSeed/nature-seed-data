# Weekly Klaviyo Review — Week of 2026-04-20

## Week at a glance

- Total sends: 0
- Recipients: 0
- Opens (unique): 0
- Clicks (unique): 0
- Email revenue: $0.00
  - Flow: $0.00
  - Campaign: $0.00
- **Flow revenue share (primary C-metric): 0.0%** (WoW change: -8.0pp)
- Email share of WC revenue (board metric): 0.0%

## Flow scorecard

| Flow | Recipients | Revenue | Conv % |
|---|---|---|---|
| 2025 - Welcome Series | 0 | $0.00 | 0.00% |
| Checkout Abandonment - GS | 0 | $0.00 | 0.00% |
| Abandoned Cart Reminder | 0 | $0.00 | 0.00% |
| Browse Abandonment - Standard | 0 | $0.00 | 0.00% |
| Winback Flow | 0 | $0.00 | 0.00% |
| Upsell Flow | 0 | $0.00 | 0.00% |
| Sunset Flow | 0 | $0.00 | 0.00% |
| Shipment Flow - WooCommerce | 0 | $0.00 | 0.00% |
| Yard Plan Welcome Flow | 0 | $0.00 | 0.00% |

## Campaign scorecard

_No campaigns sent this week._

## Segment health check

- Net list growth (30d): +0
- (RFM transition data will populate here in Plan 2 when we have snapshots)

## Deliverability gate snapshot

| Gate | Threshold | Current | Status |
|---|---|---|---|
| net_list_growth | ≥ 0.0 | 0 | ✅ |
| spam_rate | < 0.001 | 0.0 | ✅ |
| bounce_rate | < 0.01 | 0.0 | ✅ |
| unsub_rate | < 0.003 | 0.0 | ✅ |

→ **All gates passing. Aggressive mode eligible at next monthly review.**

## Agent self-grade

**C** — Flow share change -8.0pp, gates passing, 0 critical alert(s), 0 medium alert(s), flow revenue change +0.0%.

## Anomalies / wins

- Winback flow `VvvqpW` had 0 conversions YTD on 774 sends — queued for Phase 0 fix (see winback-fix/ proposals in this file).
- Net list growth remains negative (-558 YTD as of 2026-03-10). Aggressive mode stays locked until rolling-30d growth turns positive.

## Proposed next-week calendar

### Proposal 1: Phase 0: Winback Fix deployment (after copy approval)
- Audience: At Risk (RyASXF) + Lapsed (Sv5cSC)
- Estimated RPR: $0.50

**Your decision:**
- [ ] ✅ APPROVED
- [ ] ❌ REJECTED — reason:
- [ ] 🔄 REVISE — change:

### Proposal 2: Phase 1 Kickoff: Build Seasonal Reorder flow for Warm × Lawn Warm Season
- Audience: WdpJti Warm × Ra4637 Lawn Purchasers
- Estimated RPR: $0.85

**Your decision:**
- [ ] ✅ APPROVED
- [ ] ❌ REJECTED — reason:
- [ ] 🔄 REVISE — change:

## Experiment recommendation

Once Phase 0 Winback fix is approved + deployed, A/B test subject lines on Winback Email 3: 'We miss you — $15 off to come back' vs 'One last spring reminder from Nature's Seed'. Sample: 50/50 split on At Risk + Lapsed segments.

## Approvals

_Add inline comments above in the proposal boxes. This section is for overall direction notes or escalations._

**Status:** ⬜ Awaiting review

---

## Phase 0: Winback Fix — Awaiting Approval

The current Winback flow (`VvvqpW`) has 0 conversions on 774 sends YTD (rated D). Per spec Phase 0, we propose rewriting Email 2 and adding Emails 3–5 with real offers + urgency. Proposals are in `marketing/klaviyo-audit/winback-fix/`. Approve each below:

### Winback Email 2 proposal

→ Full copy at `marketing/klaviyo-audit/winback-fix/email_2_proposal.md`

- [ ] ✅ APPROVED — deploy to Klaviyo
- [ ] ❌ REJECTED — reason:
- [ ] 🔄 REVISE — change:

### Winback Email 3 proposal

→ Full copy at `marketing/klaviyo-audit/winback-fix/email_3_proposal.md`

- [ ] ✅ APPROVED — deploy to Klaviyo
- [ ] ❌ REJECTED — reason:
- [ ] 🔄 REVISE — change:

### Winback Email 4 proposal

→ Full copy at `marketing/klaviyo-audit/winback-fix/email_4_proposal.md`

- [ ] ✅ APPROVED — deploy to Klaviyo
- [ ] ❌ REJECTED — reason:
- [ ] 🔄 REVISE — change:

### Winback Email 5 proposal

→ Full copy at `marketing/klaviyo-audit/winback-fix/email_5_proposal.md`

- [ ] ✅ APPROVED — deploy to Klaviyo
- [ ] ❌ REJECTED — reason:
- [ ] 🔄 REVISE — change:

