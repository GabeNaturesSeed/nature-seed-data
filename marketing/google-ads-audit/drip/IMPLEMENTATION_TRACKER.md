# Nature's Seed — Google Ads Drip Implementation Tracker
## Living Document: Updated Every Cycle (Monday/Thursday)

---

## How This Document Works

This is the **single source of truth** for the automated Google Ads optimization agent. Every Monday and Thursday, the agent:

1. **Reads this document** to understand goals, history, constraints, and next steps
2. **Pulls live account data** via Google Ads API
3. **Creates a "Today's Plan"** with proposed changes
4. **Discusses the plan** with Gabe via messaging (Telegram/Discord)
5. **Implements approved changes** after final confirmation
6. **Updates this document** with results, lessons, and next cycle's priorities

---

## Strategic Goals (from NATURES_SEED_HEALTH_AND_GROWTH_PLAN.md)

### Target State
| Metric | Current (March 2026) | Target (6 months) | Target (12 months) |
|--------|---------------------|-------------------|-------------------|
| Blended ROAS | 3.13x | 3.75x | 4.25x |
| Brand Search IS | ~10% | 40% | 60% |
| Shopping IS | 32% | 40% | 50% |
| Money-losing products | 81 | <30 | <15 |
| Net profit (90d) | $32,308 | $55,000 | $82,000 |

### Guiding Principles
1. **Margin-aware bidding** — Different ROAS targets per product margin tier
2. **Drip changes** — Small, measured adjustments every cycle. Never shock the account.
3. **Data-driven** — Every change backed by API data, every result measured
4. **No learning mode during peak** — Protect March-May and September-October

---

## Hard Guardrails (NEVER VIOLATE)

### Change Limits Per Cycle
| Parameter | Max Change Per Cycle | Example |
|-----------|---------------------|---------|
| Campaign budget | ±30% of current value | $220 → max $286 or min $154 |
| Target ROAS | ±30% of current value | 3.0x → max 3.9x or min 2.1x |
| Keywords paused | Max 10 per cycle | Spread impact over multiple cycles |
| Negative keywords added | Max 20 per cycle | Review in batches |
| Products excluded | Max 15 per cycle | Monitor for false negatives |

### Peak Season Protection (NO structural changes)
| Period | Status | Allowed Actions |
|--------|--------|----------------|
| **March 1 – May 31** | 🔴 PEAK | Budget adjustments only (within 30% limit), negative keywords, product exclusions. NO bidding strategy changes, NO campaign restructuring. |
| **June 1 – August 31** | 🟢 OFF-PEAK | All changes allowed. Best time for structural changes. |
| **September 1 – October 31** | 🔴 PEAK | Same restrictions as March-May. |
| **November 1 – February 28** | 🟡 MODERATE | Most changes allowed. Avoid major restructuring in November (holiday season). |

### Today's Date Context
- **Current month**: March 2026
- **Season status**: 🔴 PEAK — Budget adjustments, negatives, and exclusions ONLY
- **Next structural window**: June 2026

---

## Implementation Phases & Status

### Phase 1: Stop the Bleeding
| Action | Status | Cycle | Date | Notes |
|--------|--------|-------|------|-------|
| Exclude 25 worst money-losing products | ⬜ Not started | — | — | Split into 2 cycles (15 + 10) |
| Pause money-losing keywords (batch 1) | ✅ Complete | 1 | 2026-03-12 | Top 10 worst first |
| Add negative keywords (batch 1) | ✅ Complete | 1 | 2026-03-12 | Competitor brands + irrelevant |
| Increase Brand Search budget (step 1) | ✅ Complete | 1 | 2026-03-12 | $220 → $286 (30% max) |
| Increase Brand Search budget (step 2) | ✅ Complete | 1 | 2026-03-12 | $286 → $372 |
| Increase Brand Search budget (step 3) | ⬜ Not started | — | — | $372 → $483 ≈ $500 target |

### Phase 2: Reallocate & Restructure
| Action | Status | Cycle | Date | Notes |
|--------|--------|-------|------|-------|
| Cut Animal Seed Broad budget (step 1) | ✅ Complete | 1 | 2026-03-12 | $260 → $182 (30% max) |
| Cut Animal Seed Broad budget (step 2) | ⬜ Not started | — | — | $182 → $130 target |
| Increase Pasture Exact budget (step 1) | ✅ Complete | 1 | 2026-03-12 | $78 → $101 |
| Increase Pasture Exact budget (step 2) | ✅ Complete | 1 | 2026-03-12 | $101 → $131 |
| Increase Pasture Exact budget (step 3) | ⬜ Not started | — | — | $131 → $170 → $200 |
| Add missing keywords to Pasture Exact | ⬜ Not started | — | — | "pasture seed", "hay seed mix", etc. |
| Fix Pasture Exact bidding strategy | ⬜ Blocked | — | — | 🔴 PEAK — defer to June |
| Audit conversion tracking | ⬜ Not started | — | — | Can investigate but don't change during peak |

### Phase 3: Strategic Growth
| Action | Status | Cycle | Date | Notes |
|--------|--------|-------|------|-------|
| Create margin-tiered Shopping groups | ⬜ Blocked | — | — | 🔴 PEAK — defer to June |
| Add California asset group to PMax | ⬜ Blocked | — | — | 🔴 PEAK — defer to June |
| Launch DSA campaign | ⬜ Blocked | — | — | 🔴 PEAK — defer to June |
| Implement seasonal budget pacing | ⬜ Not started | — | — | Plan now, implement in June |

### Phase 4: Ongoing Optimization
| Action | Status | Cycle | Date | Notes |
|--------|--------|-------|------|-------|
| Bi-weekly search term mining | ⬜ Recurring | — | — | Every cycle |
| Monthly product exclusion review | ⬜ Recurring | — | — | First/last Monday of month |
| Quarterly conversion audit | ⬜ Recurring | — | — | June, September, December |

---

## Change History Log

### Template for each entry:
```
### Cycle [N] — [Day], [Date]
**Plan proposed**: [summary]
**Plan approved**: [Yes/No/Modified]
**Changes implemented**:
- [change 1]: [before] → [after] | Result: [pending/measured]
- [change 2]: [before] → [after] | Result: [pending/measured]
**Deferred to next cycle**: [items]
**Lessons learned**: [any insights]
**Account snapshot**: Spend $X | Revenue $Y | ROAS Z.Zx (last 7 days)
```


### Cycle 1 — Monday, 2026-03-09
**Season**: 🔴 PEAK
**Plan proposed**: 6 actions
**Executed**: 5 | **Skipped**: 0 | **Errors**: 0
**Changes implemented**:
- ✅ Search | Animal Seed (Broad) | ROAS: $260 → $182/day
- ✅ Search | Brand | ROAS: $220 → $286/day
- ✅ Search | Pasture | Exact: $78 → $101/day
- ✅ Added 10 negative keywords (account-level)
- ✅ Paused 5 money-losing keywords
- 📋 keyword_opportunities — requires manual implementation
**Account snapshot**: Spend $58,517 | Revenue $178,629 | ROAS 3.05x (30d)


---

## Conversation History Index

| Cycle | Date | Platform | Key Decisions |
|-------|------|----------|--------------|
| — | — | — | *(First cycle pending)* |

---

## Lessons & Patterns

### From Prior Audit Work
1. `LAST_90_DAYS` is not valid in GAQL — use explicit date range: `BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`
2. Google Ads scripts use `DRY_RUN = true` by default — always test first
3. Budget changes take effect next day (Google limitation)
4. `validate_only=True` on all mutate calls for dry-run testing
5. Batch operations count as single API request — use for scale
6. Campaign bidding strategy changes trigger learning period (2-4 weeks)
7. Conversion tracking changes trigger learning period

### From This Drip Process
*(Will be populated as cycles run)*

---

## Quick Reference: Account IDs

| Resource | ID |
|----------|----|
| Google Ads Customer | `5992879586` |
| Google Ads Login | `8386194588` |
| Merchant Center | `138935850` |
| GA4 Property | `294622924` |

## Quick Reference: Current Campaign Budgets

| Campaign | Budget/Day | Last Updated |
|----------|-----------|-------------|
| Shopping Catch All | $1,450 | Baseline (pre-drip) |
| PMax Catch All | $760 | Baseline |
| Animal Seed Broad | $260 | Baseline |
| PMax Search | $300 | Baseline |
| Brand Search | $220 | Baseline |
| Pasture Exact | $78 | Baseline |

## Quick Reference: Category Margins

| Category | Avg Margin | Break-Even ROAS | Target ROAS |
|----------|-----------|----------------|-------------|
| Pure Grass | 77.6% | 1.29x | 1.68x |
| Wildflower | 76.9% | 1.30x | 1.69x |
| Lawn/Turf | 73.0% | 1.37x | 1.78x |
| Specialty/Clover | 60.9% | 1.64x | 2.13x |
| Pasture Mixes | 57.3% | 1.75x | 2.27x |
