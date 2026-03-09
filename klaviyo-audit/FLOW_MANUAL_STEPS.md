# Flow Manual Steps — Klaviyo UI Required
> Generated: March 6, 2026

The Klaviyo API handles template updates, flow activation, and status changes.
However, adding new email nodes to an existing flow graph requires the Klaviyo drag-and-drop UI.
These are the remaining steps to complete after the automated implementation.

---

## STATUS SUMMARY (post-script)

| Task | Status | Notes |
|------|--------|-------|
| Winback Email 2 content | NEEDS UI STEP | Full design template TjLfX2 created — swap in UI (replaces placeholder VSEWPU) |
| Welcome Series WQBF89 | LIVE | All 18 actions verified live |
| Seasonal Reorder Vzp5Nb | LIVE | Status confirmed |
| Seasonal Reorder SMZ5NX | LIVE | Status confirmed |
| Shipment Email 2 template | CREATED | ID: VF9s6H — needs to be added to flow in UI |
| Shipment Email 3 template | CREATED | ID: V48pu6 — needs to be added to flow in UI |
| Post-Purchase Email 3 template | CREATED | ID: TN6ieQ — needs to be added to flow in UI |
| Post-Purchase Email 4 template | CREATED | ID: XiiNUq — needs to be added to flow in UI |
| Post-Purchase Email 5 template | CREATED | ID: USRSMi — needs to be added to flow in UI |
| Cart overlap filter | NEEDS UI STEP | Add filter to Y7Qm8F |

---

## STEP 1: Winback Email 2 — Swap Template

**Flow:** https://www.klaviyo.com/flow/VvvqpW/edit
**Target message:** SDHWqD ("Educational -")
**New template:** `VSEWPU` — "Winback Email 2 — $20 Off Welcome Back"

**Steps:**
1. Open the Winback Flow
2. Click on Email 2 ("Educational -")
3. Click "Edit email"
4. Click "Change template" or use the template selector
5. Search for template name: **"Winback Email 2 — $20 Off Welcome Back (Lawn)"** (ID: TjLfX2)
6. Apply the template
7. Update subject line to: `$20 off — welcome back, {{ first_name|default:"there" }}`
8. Update preview text to: `Your offer expires in 48 hours. No minimum required.`
9. Save and confirm the action is set to Live

**Note:** The coupon code `WELCOME20` in the template will need to be created in WooCommerce
if it doesn't already exist — set to $20 flat off, 1-use per customer, expires 48 hours
(or set as a floating expiry via Klaviyo's time-based coupon block).

---

## STEP 2: Shipment Flow — Add Email 2 + Email 3

**Flow:** https://www.klaviyo.com/flow/UhxNKt/edit

Current structure:
```
[SEND_EMAIL: Email 1 — "Your order is on its way!"] (action 92299284)
  └─ [BOOLEAN_BRANCH] (92300666)
       └─ [SEND_SMS] (92300708)
```

**Add after Email 1:**

1. Click the `+` after Email 1 action
2. Add **Time Delay**: 1 day
3. Add **Send Email** → "Use existing template" → select **`VF9s6H`**
   - Name: "Shipment Flow — Email 2: Seed Arrives Today"
   - Subject: `Your seed arrives today — here's what to do first`
   - Preview: `3 steps to get the best results from day one.`
   - Send settings: `is_transactional = true` (keep consistent with Email 1)

4. Add **Time Delay** after Email 2: 3 days
5. Add **Send Email** → "Use existing template" → select **`V48pu6`**
   - Name: "Shipment Flow — Email 3: 3-Day Check-In"
   - Subject: `How's everything looking? Quick check-in on your order`
   - Preview: `Any issues? Let us know — we'll make it right.`
   - Send settings: `is_transactional = true`

**Shippo integration note (future):** When the Shippo API integration is set up,
change Email 2 trigger from "1 day delay" to "Delivered" webhook event.
This makes the email fire on actual delivery confirmation, not an estimate.

---

## STEP 3: Post-Purchase Onboarding — Expand to 5 Emails

**Flow:** https://www.klaviyo.com/flow/HRmUgq/edit

Current structure (2 draft emails):
```
[SEND_EMAIL: Email 1] (action 4949184, DRAFT)
  └─ [TIME_DELAY: 1 day] (action 4949185)
       └─ [SEND_EMAIL: Email 2] (action 92280132, DRAFT)
            └─ [TIME_DELAY: 2 hours] (action 92280142)
                 └─ [BOOLEAN_BRANCH] (92295266)
```

**First:** Activate the existing emails:
- Set action 4949184 status to Live
- Set action 92280132 status to Live
- Set the flow itself to Live (HRmUgq)

**Then add after Email 2:**

1. Fix the 2-hour Time Delay (92280142) — change to **5 days** (to reach Day 7 from trigger)
2. Add **Send Email** → select **`TN6ieQ`**
   - Name: "Post-Purchase — Email 3: Planting Day Guide"
   - Subject: `It's time to plant — here's your quick-start guide`
   - Preview: `A step-by-step guide for your seed type.`

3. Add **Time Delay**: 14 days (to reach Day 21)
4. Add **Send Email** → select **`XiiNUq`**
   - Name: "Post-Purchase — Email 4: Germination Check + Review"
   - Subject: `How's it looking? — germination check at week 3`
   - Preview: `What you should be seeing, and what to do if you're not.`

5. Add **Time Delay**: 24 days (to reach Day 45)
6. Add **Send Email** → select **`USRSMi`**
   - Name: "Post-Purchase — Email 5: Establishment + First Upsell"
   - Subject: `45 days in — here's what comes next for your planting`
   - Preview: `Maintenance tips + what works well with your seed.`

**Flow filter to add (important):**
- "IF person has placed order more than once AND order count = 1 → PASS" (first-order only)
- This flow should only trigger on a customer's FIRST order

---

## STEP 4: Cart Abandonment — Add Overlap Suppression

**Flow:** https://www.klaviyo.com/flow/Y7Qm8F/edit

**Cart audit findings:**
- Cart flow: trigger = "Added to Cart" (Metric), 2 emails
- Checkout flow: trigger = "Started Checkout" (Metric), 3 emails
- Problem: A customer who adds to cart AND starts checkout can receive emails from BOTH flows

**Add flow filter to Y7Qm8F:**
- Navigate to Flow Filters (settings gear icon on the flow trigger)
- Add condition: `IF 'Started Checkout' at least once in the last 1 day → skip`

This ensures cart emails only reach people who added to cart but NEVER started checkout.
Anyone who reached checkout gets the higher-intent checkout abandonment emails instead.

**Additional check:** Verify VkBvw5 ("Cart Abandonment- GS") is in Draft — it is.
Review whether this is redundant with Y7Qm8F. If so, leave in Draft or archive.

---

## STEP 5: Welcome Series — Verify Trigger

**Flow:** https://www.klaviyo.com/flow/WQBF89/edit

The flow is LIVE with all 18 actions live. Before confirming it's working correctly:

1. Verify trigger list is the main Newsletter list (`NLT2S2`)
2. Verify flow filter: **"Has NOT placed an order"** — so existing buyers don't enter the welcome series
3. Check flow exit: **"Placed Order"** → exit immediately and enter Onboarding flow
4. If the old Welcome Series (NnjZbq — "2025 - Welcome Series") is also live, coordinate:
   - Either set NnjZbq to Draft once WQBF89 is confirmed working
   - Or A/B test both for 2 weeks before sunsetting the old one

---

## COUPON CODE: WELCOME20

For Step 1 to work, create this coupon in WooCommerce:
- Code: `WELCOME20`
- Type: Fixed cart discount
- Amount: $20
- Usage limit per user: 1
- Expiry: Consider using Klaviyo's "Unique Coupon" block instead of a static code
  (Klaviyo can generate per-customer 1-use coupons synced to WooCommerce)

---
