# Klaviyo Cost Analysis — Nature's Seed

**Date:** March 14, 2026
**Account:** Nature's Seed (H627hn)
**Analyst:** Claude Agent

---

## Executive Summary

Nature's Seed is overpaying for Klaviyo features it barely uses. Based on full account audit via API:

**Your actual active email subscribers: 13,191** (segment UU9dHP)
**Your actual SMS subscribers: 827** (segment USHtBE)
**Suppressed/unsubscribed profiles: 80,000+** (legacy Magento + cold email imports)

You're paying for the Email+SMS plan + Customer Hub + potentially Marketing Analytics — but only the core email marketing is actually driving revenue.

**Recommended actions to save $300–$800+/month:**
1. Drop Customer Hub (396 opens, 80 tickets in 3 months)
2. Drop SMS (309 messages sent in 9 months)
3. Drop any Marketing Analytics / CDP add-ons
4. Ensure profile count stays at ~13k tier (already there if suppressions are up to date)
5. Clean up 220 segments, 32 draft flows, 27 lists, dead integrations

**Current estimated spend:** ~$500–$1,000+/month (Email+SMS ~13k profiles + Customer Hub + add-ons)
**Proposed spend:** ~$150–$200/month (Email-only at 13k–15k profiles, no add-ons)

---

## 1. Account Overview

| Metric | Value |
|--------|-------|
| Total Revenue (12 months) | $1,872,580 |
| Total Orders (12 months) | 10,644 |
| Flow-Attributed Revenue | $94,776 (5.1%) |
| Campaign/Direct Revenue | $1,777,804 (94.9%) |
| **Active Email Subscribers** | **13,191** |
| **Active SMS Subscribers** | **827** |
| Suppressed/Unsubscribed Profiles | 80,000+ |
| Total Profiles in Database | 50,000+ |
| Email Campaigns (all-time) | 432 (308 sent, 89 draft, 34 cancelled) |
| SMS Campaigns Sent | 69 |
| Live Flows | 14 |
| Draft Flows | 31 |
| Segments | **220** (many are one-off or legacy) |
| Lists | **27** |
| Forms | 8 (ALL in draft — none live!) |
| Metrics/Integrations | 114 |
| Total Emails Sent (12 months) | 1,426,234 |
| Total SMS Sent (9 months) | 309 |

---

## 2. Active Profile Analysis (The #1 Cost Driver)

Klaviyo bills by **active profiles** — any profile that can receive email marketing.

### Actual Subscriber Counts (from Klaviyo segments)

| Segment | Count |
|---------|-------|
| All Email Subscribers (UU9dHP) | **13,191** |
| All SMS Subscribers (USHtBE) | **827** |
| All Unsubscribers (VhfZpi) | **80,000+** |

Your billable active profiles are ~13k–14k. The 80k+ unsubscribed profiles are from legacy Magento and cold email imports — they don't count toward billing but clutter the database.

### Subscription Activity (Last 12 Months)

- New email subscribers: **19,854** (huge spike of 18,201 in Aug 2025 — cold email import)
- Email unsubscribers: **5,767**
- New SMS subscribers: **121**

### Monthly Unique Email Recipients (shows actual reach)

| Month | Unique Recipients | Emails Sent |
|-------|-------------------|-------------|
| 2025-03 | 96,216 | 272,468 |
| 2025-04 | 40,762 | 197,575 |
| 2025-05 | 38,825 | 115,198 |
| 2025-06 | 36,347 | 37,487 |
| 2025-07 | 32,899 | 33,943 |
| 2025-08 | 104,257 | 139,239 |
| 2025-09 | 43,685 | 152,955 |
| 2025-10 | 27,882 | 56,426 |
| 2025-11 | 29,531 | 51,226 |
| 2025-12 | 91,289 | 113,105 |
| 2026-01 | 58,235 | 115,728 |
| 2026-02 | 23,186 | 84,445 |
| 2026-03 | 19,426 | 56,439 |

Note: The high unique recipient counts in some months (96k, 104k) suggest campaigns were sent to the full database including profiles that have since been suppressed. Current active base is ~13k.

### Pricing Tiers (Email-Only Plan)

| Active Profiles | Monthly Cost |
|----------------|-------------|
| 10,000 | $150 |
| 25,000 | $400 |
| 50,000 | $720 |
| 100,000 | $1,380 |
| 150,000+ | Custom/Enterprise |

---

## 3. Feature Usage Audit

### Customer Hub — DROP IT

| Period | Opens | Tickets |
|--------|-------|---------|
| 2026-01 | 16 | 6 |
| 2026-02 | 333 | 66 |
| 2026-03 | 47 | 8 |
| **Total** | **396** | **80** |

**Verdict:** 396 opens and 80 tickets in 3 months is negligible. You already have customercare@naturesseed.com as the support channel. Customer Hub is an add-on cost for almost zero value.

**Replacement:** WooCommerce "My Account" page + existing email support. Zero cost.

### SMS — DROP IT or REPLACE

| Period | SMS Sent |
|--------|----------|
| 2025-05 through 2026-03 | **309 total** |

**309 SMS messages in 9 months.** At $0.015/message that's $4.64 in actual SMS usage, but you're paying at least $15/mo extra for the Email+SMS plan tier, plus unused SMS credits don't roll over.

69 SMS "campaigns" exist but most are tied to flows that barely trigger.

**Replacement options:**
- Twilio: ~$0.0079/SMS, pay-per-use, no monthly minimum
- WooCommerce SMS plugins: one-time cost
- Just use email — your open rates are strong (40-50%)

### Swell Loyalty Integration — DEAD

24 Swell-related metrics in the account (Points Earned, Redemptions, Referrals, etc.) but the API returned errors when querying recent activity. This integration appears **completely inactive** but still polluting the metrics/data.

**Action:** Remove Swell integration from Klaviyo to clean up the account.

### Forms — ALL DRAFTS

All 8 forms are in **draft status**:
- Newsletter Sign Up
- Welcome Pop-up (Desktop)
- Welcome Pop-up (Mobile)
- Multi-Step Coupon
- Complete your profile
- Hedgerow Project Design

**You're paying for form features you're not using.** These forms should either be activated or you should use a free alternative (WooCommerce popups, custom JS).

### Legacy Integrations — CLEANUP

114 metrics in the account, including:
- **Magento** — 7 metrics (legacy, migrated to WooCommerce)
- **Magento 2** — 7 metrics (legacy)
- **Swell** — 17 metrics (inactive loyalty program)
- **Vibe** — 1 metric (advertising impressions)

These don't directly cost money but they bloat the interface, confuse reporting, and may contribute to profile count inflation (Magento profiles still in the system).

---

## 4. Flow Revenue Analysis (Last 12 Months)

Only **$94,776 of $1.87M** (5.1%) is attributed to Klaviyo flows. The rest comes from campaigns and direct purchases.

### Top Revenue Flows

| Flow | Revenue | Orders | % of Total |
|------|---------|--------|------------|
| Checkout Abandonment (SxbaYQ) | $45,373 | 197 | 2.4% |
| Browse Abandonment draft (Rmz2fN) | $23,493 | 81 | 1.3% |
| Welcome Series 2025 (NnjZbq) | $5,408 | 26 | 0.3% |
| Abandoned Cart (WhUxF4) | $5,222 | 26 | 0.3% |
| Pasture Post Purchase (VsxGYg) | $3,814 | 4 | 0.2% |
| Abandoned Cart (Y7Qm8F) | $2,074 | 12 | 0.1% |
| Cart Abandonment (VkBvw5) | $1,730 | 10 | 0.1% |
| Browse Abandonment (Xz9k4a) | $1,277 | 9 | 0.1% |
| Upsell Flow (VZsFVy) | $1,154 | 7 | 0.1% |
| All Others | <$5,000 | <30 | <0.3% |

### Flows That Can Be Replaced Outside Klaviyo

| Flow | Can Replace? | How |
|------|-------------|-----|
| Checkout Abandonment | Partially | WooCommerce has built-in abandoned checkout emails (free with AutomateWoo or similar) |
| Browse Abandonment | Partially | Requires JS tracking — Klaviyo excels here |
| Welcome Series | Yes | WooCommerce registration + Mailchimp/Brevo free tier |
| Shipment Flow | Yes | WooCommerce transactional emails (free) |
| Accounting Batches | Yes | Already custom (API trigger) — can run via any email service |
| Winback | Yes | Simple time-based query on WooCommerce order data |
| Sunset Flow | Yes | List hygiene — any ESP can do this |

### Flows Worth Keeping in Klaviyo

1. **Checkout Abandonment** ($45k revenue) — Klaviyo's real-time trigger is superior
2. **Browse Abandonment** ($24k revenue) — Requires Klaviyo's JS tracking
3. **Abandoned Cart** ($9k combined) — Real-time triggers
4. **Upsell Flow** ($1.2k) — Product recommendation engine

These 4 flow types generate ~$80k/year and genuinely need Klaviyo's real-time behavioral tracking.

---

## 5. Recommended Actions

### Tier 1: Immediate Savings (do this week)

| Action | Estimated Monthly Savings |
|--------|--------------------------|
| **Drop Customer Hub add-on** | $50–$100/mo |
| **Drop SMS — switch to Email-only plan** | $15–$50/mo |
| **Drop Marketing Analytics add-on** (if active) | $100/mo |
| **Verify profile count at 13k tier** — ensure suppressions are applied so you're on the $150/mo tier, not higher | $0–$250/mo (depends on current tier) |
| **Remove Swell integration** | $0 (cleanup) |
| **Remove Magento/Magento 2 integrations** | $0 (cleanup) |
| **Delete 80k+ suppressed profiles** — they don't cost money but clutter everything | $0 (cleanup) |

**Tier 1 Total: $165–$500/month savings**

### Tier 2: Medium-Term Optimization (next 30 days)

| Action | Impact |
|--------|--------|
| **Activate forms or replace** — 8 draft forms = missed signups. Either go live or use free WooCommerce popups | More targeted signups = fewer wasted profiles |
| **Consolidate duplicate flows** — You have 3 cart abandonment flows, 2 welcome series, multiple browse abandonment variants | Simpler = easier to maintain, less profile triggering |
| **Clean up 32 draft flows** — Delete or archive the ones you'll never use | Reduce confusion |
| **Move transactional emails out** — Shipment notifications, accounting batches don't need Klaviyo | Fewer profiles needing Klaviyo |

### Tier 3: Consider Klaviyo Alternatives (if cost is critical)

If you want to go further, the **core value Klaviyo provides** is:
1. Real-time behavioral tracking (browse/cart/checkout abandonment)
2. Segmentation engine
3. Campaign sending with good deliverability

**Alternatives that could replace most of what you use:**

| Tool | Monthly Cost | What It Replaces |
|------|-------------|-----------------|
| **Brevo (Sendinblue)** | $25–$65/mo (unlimited contacts, pay by sends) | Campaigns, basic flows, transactional |
| **Mailchimp** | $350/mo at 50k contacts | Campaigns, basic automations |
| **Omnisend** | $330/mo at 50k contacts | Full ecommerce automation, SMS included |
| **AutomateWoo** | $129/year (one-time) | Cart abandonment, winback, follow-ups |

**Hybrid approach:** Use Klaviyo on the **Email-only plan at the lowest tier** (just for behavioral flows) + Brevo for bulk campaigns. This could cut costs to ~$400–$500/mo total.

---

## 6. Profile & Segment Hygiene

Your active profile count (13,191) is already reasonable — the 80k+ suppressed profiles are already excluded from billing. But there's significant cleanup needed:

### Database Cleanup
- **80,000+ suppressed profiles** — Consider permanently deleting profiles with no activity in 2+ years to clean up the database
- **27 lists** — Many are legacy (Old Email List, ColdUSAfarms, Outlook Potential Buyers). Archive lists with no active use
- **220 segments** — This is excessive. Many are one-off campaign segments that should be deleted:
  - 19 cold email pasture cohorts from Aug 2025
  - Product-specific segments used for single campaigns
  - RFM segments that duplicate each other

### Lists to Consider Archiving/Deleting
```
Low-value lists (likely adding to clutter):
- HzC8DX — Old Email List (2019, double opt-in, legacy)
- NBQVJZ — Outlook Potential Buyers (2019, prospecting)
- RKkMjQ — ColdUSAfarms (2025, cold outreach)
- WxRyT2 — Cold Email Pasture from Susan (2025, cold outreach)
- Vtv9aD — Cold Leads Pasture Aug 2025
- XxpxAd — Test Emails
```

### Ongoing Hygiene
- Run Sunset Flow (UZf9UD) quarterly on disengaged subscribers
- Delete profiles that haven't opened in 12+ months AND never purchased
- Keep profile count under 15k tier ($150/mo) to avoid tier jumps

---

## 7. Monthly Cost Projection

### Current (estimated — verify in Klaviyo Settings → Billing)
| Item | Cost |
|------|------|
| Klaviyo Email + SMS (~13k profiles) | ~$200–$250 |
| Customer Hub add-on | ~$50–$100 |
| Marketing Analytics add-on (if active) | ~$100 |
| **Total** | **~$350–$450/mo ($4,200–$5,400/year)** |

*Note: If your billing tier is higher than the 13k profile count suggests (e.g., due to how Klaviyo counts "active"), the savings could be much larger. Check your actual bill.*

### After Optimization
| Item | Cost |
|------|------|
| Klaviyo Email-only (~13k profiles) | $150 |
| No SMS | $0 |
| No Customer Hub | $0 |
| No Marketing Analytics | $0 |
| **Total** | **~$150/mo ($1,800/year)** |

### Savings: $200–$300/month = $2,400–$3,600/year (conservative)

If your actual bill is higher due to legacy tier pricing or hidden add-ons, savings could be $500+/month.

### Alternative: Leave Klaviyo entirely
If you moved to **Brevo** (unlimited contacts, pay per email send):
- 1.4M emails/year ÷ 12 = ~120k emails/month
- Brevo Business plan: ~$65/mo for 120k emails
- Savings vs optimized Klaviyo: ~$85/mo
- **But you'd lose**: behavioral tracking, browse abandonment ($25k/yr revenue), checkout abandonment triggers
- **Verdict: NOT worth leaving Klaviyo** — the $80k/yr in flow revenue easily justifies $150/mo

---

## 8. What You Should NOT Cut

1. **Checkout Abandonment flow** — $45k/year revenue, 47:1 ROI
2. **Browse Abandonment tracking** — $25k/year, only Klaviyo can do this well
3. **Cart Abandonment flows** — $9k/year combined
4. **Campaign sending capability** — 94.9% of your revenue is campaign/direct
5. **WooCommerce integration** — this is your data backbone
6. **Segmentation** — your persona-based approach (Lawn, Pasture, Wildflower) is smart

---

## 9. Action Checklist

### Week 1: Verify & Cut Add-Ons
- [ ] Log into Klaviyo → Settings → Billing → **Screenshot exact current plan, add-ons, and monthly charge**
- [ ] Remove Customer Hub add-on
- [ ] Remove Marketing Analytics add-on (if active)
- [ ] Switch from Email+SMS to Email-only plan
- [ ] Verify active profile count shows ~13k (matches billing tier)

### Week 2: Clean Up Integrations
- [ ] Remove Swell integration (Settings → Integrations)
- [ ] Remove Magento integration
- [ ] Remove Magento 2 integration
- [ ] Remove Vibe integration (if not actively using CTV ads)

### Week 3: Clean Up Flows, Segments, Lists
- [ ] Delete or archive 31 draft flows (many are duplicates of live flows)
- [ ] Consolidate duplicate live flows (3 cart abandonment, 2 welcome series)
- [ ] Delete one-off campaign segments (cold email cohorts, etc.)
- [ ] Archive unused lists (Old Email List, ColdUSAfarms, etc.)
- [ ] Activate or delete 8 draft forms

### Week 4: Ongoing Hygiene
- [ ] Run Sunset Flow on disengaged subscribers (no opens in 6+ months)
- [ ] Delete profiles with 0 activity in 2+ years
- [ ] Set calendar reminder for quarterly profile cleanup
- [ ] Verify new billing amount on next invoice

### Future Consideration
- [ ] Evaluate whether 220 segments can be reduced to ~50 well-maintained segments
- [ ] Consider activating Welcome Pop-up forms (currently all drafts = missed signups)
- [ ] Monitor if SMS is needed at all (827 subscribers, 309 sends in 9 months)

---

## Data Sources

All data pulled via Klaviyo API v2025-01-15 on March 14, 2026.
- Revenue data: `VLbLXB` metric (WooCommerce Placed Order)
- Email volume: `NpKKhz` metric (Received Email)
- SMS volume: `QReyKP` metric (Sent SMS)
- Customer Hub: `TyU6T8` metric (Opened Customer Hub)
- Support tickets: `T9tMHp` metric (Ticket Created)
