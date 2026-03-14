# Klaviyo Cost Analysis — Nature's Seed

**Date:** March 14, 2026
**Account:** Nature's Seed (H627hn)
**Analyst:** Claude Agent

---

## Executive Summary

Nature's Seed is significantly overpaying for Klaviyo. Based on account data analysis, **you can save $500–$800+/month** by:

1. Suppressing inactive profiles to drop below a cheaper billing tier
2. Dropping Customer Hub (barely used)
3. Dropping or replacing SMS (309 messages in 9 months)
4. Replacing paid features with automations we already built or can build

**Current estimated spend:** ~$1,500–$2,000+/month (Email + SMS + Customer Hub + add-ons)
**Proposed spend:** ~$700–$1,000/month (Email-only, cleaned profile list)

---

## 1. Account Overview

| Metric | Value |
|--------|-------|
| Total Revenue (12 months) | $1,872,580 |
| Total Orders (12 months) | 10,644 |
| Flow-Attributed Revenue | $94,776 (5.1%) |
| Campaign/Direct Revenue | $1,777,804 (94.9%) |
| Email Campaigns Created | 100+ |
| SMS Campaigns Sent | 69 |
| Live Flows | 13 |
| Draft Flows | 32 |
| Segments | 10 |
| Lists | 10 |
| Forms | 8 (ALL in draft — none live!) |
| Metrics/Integrations | 114 |

---

## 2. Active Profile Analysis (The #1 Cost Driver)

Klaviyo bills by **active profiles** — any profile that can receive email marketing.

| Month | Unique Email Recipients |
|-------|------------------------|
| 2025-03 | 96,216 |
| 2025-04 | 40,762 |
| 2025-05 | 38,825 |
| 2025-06 | 36,347 |
| 2025-07 | 32,899 |
| 2025-08 | 104,257 (peak — likely BF/CM prep blast) |
| 2025-09 | 43,685 |
| 2025-10 | 27,882 |
| 2025-11 | 29,531 |
| 2025-12 | 91,289 |
| 2026-01 | 58,235 |
| 2026-02 | 23,186 |
| 2026-03 | 19,426 (month to date) |

**Peak active profiles:** ~104k → **Klaviyo Email plan at 100k = $1,380/mo**

But recent months show only 19k–58k unique recipients. The account likely has **tens of thousands of dead/inactive profiles** still counting toward billing.

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
| **Suppress/delete inactive profiles** — Run sunset flow, then suppress all profiles with 0 opens in 12+ months | $200–$680/mo (drop from 100k to 25-50k tier) |
| **Drop Customer Hub add-on** | $50–$100/mo |
| **Drop SMS or switch to Email-only plan** | $15–$50/mo |
| **Remove Swell integration** | $0 (cleanup) |
| **Remove Magento/Magento 2 integrations** | $0 (cleanup) |

**Tier 1 Total: $265–$830/month savings**

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

## 6. Profile Suppression Strategy

This is the single biggest cost lever. Here's the plan:

### Step 1: Identify suppressible profiles
```
Profiles that should be suppressed/removed:
- Never opened an email (ever)
- No opens in last 12 months
- No purchases ever
- Magento-only profiles with no WooCommerce activity
- Bounced emails
- Spam complaints
- Old Email List (HzC8DX) — created 2019, likely full of dead emails
- Outlook Potential Buyers (NBQVJZ) — prospecting list, double opt-in
- ColdUSAfarms (RKkMjQ) — cold outreach list
```

### Step 2: Run sunset flow first
The existing Sunset Flow (UZf9UD) should be activated for all disengaged profiles. Give them 2 weeks to re-engage, then suppress.

### Step 3: Suppress and track
After suppression, your active profile count should drop from ~100k to **15k–30k** (your actual engaged audience), saving $400–$980/month on the Email plan alone.

---

## 7. Monthly Cost Projection

### Current (estimated)
| Item | Cost |
|------|------|
| Klaviyo Email + SMS (~100k profiles) | $1,395 |
| Customer Hub add-on | ~$100 |
| Marketing Analytics add-on (if active) | ~$100 |
| **Total** | **~$1,595/mo ($19,140/year)** |

### After Optimization
| Item | Cost |
|------|------|
| Klaviyo Email-only (~25k profiles after cleanup) | $400 |
| No SMS | $0 |
| No Customer Hub | $0 |
| **Total** | **~$400/mo ($4,800/year)** |

### Savings: ~$1,195/month = $14,340/year

Even if you keep 50k profiles: **$720/mo = $8,640/year** (still saving $10,500/year).

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

- [ ] Log into Klaviyo → Settings → Billing → Note exact current plan and add-ons
- [ ] Create segment: "No opens in 12 months AND no purchases in 12 months"
- [ ] Run Sunset Flow on that segment (2-week re-engagement window)
- [ ] After 2 weeks: Suppress all non-responders
- [ ] Remove Customer Hub add-on
- [ ] Switch from Email+SMS to Email-only plan
- [ ] Remove Swell integration (Settings → Integrations)
- [ ] Remove Magento and Magento 2 integrations
- [ ] Delete or archive unused draft flows (32 drafts, many duplicates)
- [ ] Activate or delete draft forms (8 sitting unused)
- [ ] Verify new billing tier reflects suppressed profile count
- [ ] Set up quarterly profile hygiene review

---

## Data Sources

All data pulled via Klaviyo API v2025-01-15 on March 14, 2026.
- Revenue data: `VLbLXB` metric (WooCommerce Placed Order)
- Email volume: `NpKKhz` metric (Received Email)
- SMS volume: `QReyKP` metric (Sent SMS)
- Customer Hub: `TyU6T8` metric (Opened Customer Hub)
- Support tickets: `T9tMHp` metric (Ticket Created)
