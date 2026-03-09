# Klaviyo Template Swap — Complete UI Guide
> Generated: March 6, 2026
> All 34 new design-system templates are created and approved. This guide walks through swapping them into each flow.

**Why UI?** Klaviyo's API does not support updating flow message content, subjects, or template assignments. All swaps must be done in the Klaviyo flow editor.

---

## Quick Reference: New Template IDs

| Template ID | Name |
|-------------|------|
| **Winback** | |
| UesPJT | Winback Email 1 -- We've Been Thinking About Your Lawn |
| TjLfX2 | Winback Email 2 -- $20 Off Welcome Back (Lawn) |
| **Welcome Series** | |
| WuLv5D | Welcome E1 -- Welcome to Nature's Seed |
| VaGpxm | Welcome E2 -- What Kind of Grower Are You? |
| WHPL42 | Welcome E3 -- The Nature's Seed Difference |
| Tpt27A | Welcome E4 -- Our Top Lawn Seed Picks for You |
| URX8gR | Welcome E5 -- How to Seed Your Lawn Right |
| SaBqX4 | Welcome E6 -- What Customers Are Saying |
| U6S54a | Welcome E7 -- Seeding Season Is Here |
| RLDDiN | Welcome E8 -- Last Chance: Ready to Start Your Lawn? |
| **Post-Purchase** | |
| SkzbPd | Post-Purchase E1 -- Order Confirmed + Seeding Guide |
| V7HDqB | Post-Purchase E2 -- How to Seed Your Lawn Right |
| VPnshA | Post-Purchase E3 -- Day 7: Time to Plant |
| Tfgfw4 | Post-Purchase E4 -- Day 21: Germination Check |
| UfZPKu | Post-Purchase E5 -- Day 45: Established |
| **Shipment** | |
| Vbq9BG | Shipment E1 -- Your Order Is On Its Way |
| WmqexU | Shipment E2 -- Your Seed Arrives Today |
| XKSkq9 | Shipment E3 -- 3-Day Check-In |
| **Cart Abandonment** | |
| VyTbfz | Cart E1 -- You Left Something Behind |
| QTR5Jv | Cart E2 -- Still There? Seed Season Moves Fast |
| **Upsell** | |
| UuAkHu | Upsell E1 -- Products That Go Great with Your Seed |
| UCr7i7 | Upsell E2 -- Seasonal Calendar + Top Picks |
| **Browse Abandonment** | |
| T5ZuRM | Browse -- Lawn Seed |
| VZPd7B | Browse -- Pasture Seed |
| Vg9TZ5 | Browse -- Wildflower Seed |
| WiUup2 | Browse -- General Seed |
| **Sunset** | |
| VuBUV6 | Sunset E1 -- Still Want to Hear from Us? |
| XS3QTF | Sunset E2 -- This Is Our Last Email |

---

## FLOW 1: WINBACK (VvvqpW) -- SWAP 2 EMAILS

URL: https://www.klaviyo.com/flow/VvvqpW/edit

| Step | Current Email | Action | New Template | New Subject | New Preview |
|------|-------------|--------|-------------|-------------|-------------|
| 1 | "Thinking about your land?" (TdDYQ2) | Swap template | UesPJT | We've been thinking about your lawn, {{ first_name\|default:"there" }} | It's been a while -- here's what's new at Nature's Seed. |
| 2 | "Educational -" (SDHWqD) | Swap template | TjLfX2 | $20 off -- welcome back, {{ first_name\|default:"there" }} | Your offer expires in 48 hours. No minimum required. |

**Steps for each email:**
1. Click the email action in the flow
2. Click "Edit Email" (opens the email editor)
3. Click the template/design dropdown or "Change Template"
4. Search for the template name or ID from the table above
5. Apply the template
6. Update the Subject line and Preview text from the table
7. Save
8. Confirm action is set to **Live**

---

## FLOW 2: WELCOME SERIES (WQBF89) -- SWAP 8 EMAILS

URL: https://www.klaviyo.com/flow/WQBF89/edit

### A-Path (Non-Buyer)

| Step | Current Email | New Template | New Subject | New Preview |
|------|-------------|-------------|-------------|-------------|
| 1 | "Welcome A1 - Hero + Coupon" (RZHNRV) | WuLv5D | Welcome to Nature's Seed -- here's 10% off your first order | Your lawn journey starts here. Plus a welcome gift inside. |
| 2 | "Welcome A2 - Category Selector" (UXyxgg) | VaGpxm | What are you planting this season? | Lawn, pasture, wildflower -- we'll help you pick the right seed. |
| 3 | "Welcome A3 - Education" (RV6ywx) | URX8gR | Tips for your planting project | Step-by-step seeding guide from our agronomists. |
| 4 | "Welcome A4 - Social Proof" (Xind3Y) | SaBqX4 | 150,000+ customers planted with us last season | See why growers across the country trust Nature's Seed. |
| 5 | "Welcome A5 - Urgency Coupon" (StukML) | RLDDiN | Your 10% off expires tomorrow | Don't miss your welcome discount -- it's almost gone. |

### B-Path (Buyer)

| Step | Current Email | New Template | New Subject | New Preview |
|------|-------------|-------------|-------------|-------------|
| 6 | "Welcome B1 - Buyer Welcome" (UraJZ3) | WHPL42 | Thanks for your order -- here's what makes us different | Farm-direct, expert-blended, independently tested since 1994. |
| 7 | "Welcome B2 - Cross Category" (VAzzST) | Tpt27A | Did you know we also carry this? | Products that pair perfectly with what you ordered. |
| 8 | "Welcome B3 - Seasonal Setup" (UkxuDD) | U6S54a | We'll remind you when it's time to plant | Your seasonal planting calendar is ready. |

---

## FLOW 3: POST-PURCHASE (HRmUgq) -- SWAP 2 + ADD 3 + ACTIVATE

URL: https://www.klaviyo.com/flow/HRmUgq/edit
**Flow status: Currently DRAFT -- needs activation after edits**

### Part A: Swap existing emails

| Step | Current Email | New Template | New Subject | New Preview |
|------|-------------|-------------|-------------|-------------|
| 1 | "New Customer Thank You: Email 1" (Qq4pFH) | SkzbPd | Your order is confirmed -- here's your seeding guide, {{ first_name\|default:"there" }} | Everything you need to get started with your new seed. |
| 2 | "Upsell 1" (W4RdRQ) | V7HDqB | Before you plant -- these tips make all the difference | Step-by-step guide to get the best results from your seed. |

### Part B: Add 3 new emails after Email 2

After Email 2, the current flow has a 2-hour Time Delay then a Boolean Branch. Modify as follows:

3. **Change the Time Delay** (action 92280142) from 2 hours to **5 days**
4. **Add Send Email** after the delay:
   - Template: **VPnshA**
   - Name: Post-Purchase E3 -- Day 7: Time to Plant
   - Subject: `It's time to plant -- here's your quick-start guide`
   - Preview: `A step-by-step guide for your seed type.`

5. **Add Time Delay: 14 days**

6. **Add Send Email:**
   - Template: **Tfgfw4**
   - Name: Post-Purchase E4 -- Day 21: Germination Check
   - Subject: `How's it looking? -- germination check at week 3`
   - Preview: `What you should be seeing, and what to do if you're not.`

7. **Add Time Delay: 24 days**

8. **Add Send Email:**
   - Template: **UfZPKu**
   - Name: Post-Purchase E5 -- Day 45: Established
   - Subject: `45 days in -- here's what comes next for your planting`
   - Preview: `Maintenance tips + what works well with your seed.`

### Part C: Activate

9. Set Email 1 action (4949184) to **Live**
10. Set Email 2 action (92280132) to **Live**
11. Set all new email actions to **Live**
12. Set the flow itself to **Live**

---

## FLOW 4: SHIPMENT (UhxNKt) -- SWAP 1 + ADD 2

URL: https://www.klaviyo.com/flow/UhxNKt/edit

### Part A: Swap existing email

| Step | Current Email | New Template | New Subject | New Preview |
|------|-------------|-------------|-------------|-------------|
| 1 | "Your Order has been shipped" (SdNq6D) | Vbq9BG | Get ready to plant -- your seeds are on the way! | Track your order + prep tips while you wait. |

### Part B: Add 2 new emails after Email 1

Current structure after E1: Boolean Branch then SMS. Add BEFORE the branch:

2. **Add Time Delay: 1 day** (after Email 1, before the branch)

3. **Add Send Email:**
   - Template: **WmqexU**
   - Name: Shipment E2 -- Your Seed Arrives Today
   - Subject: `Your seed arrives today -- here's what to do first`
   - Preview: `3 steps to get the best results from day one.`
   - Settings: `is_transactional = true`

4. **Add Time Delay: 3 days**

5. **Add Send Email:**
   - Template: **XKSkq9**
   - Name: Shipment E3 -- 3-Day Check-In
   - Subject: `How's everything looking? Quick check-in on your order`
   - Preview: `Any issues? Let us know -- we'll make it right.`
   - Settings: `is_transactional = true`

6. Set new actions to **Live**

---

## FLOW 5: CART ABANDONMENT (Y7Qm8F) -- SWAP 2

URL: https://www.klaviyo.com/flow/Y7Qm8F/edit

| Step | Current Email | New Template | New Subject | New Preview |
|------|-------------|-------------|-------------|-------------|
| 1 | "Abandoned Cart 1" (RuwBmY) | VyTbfz | You left something behind, {{ first_name\|default:"there" }} | Your cart is waiting -- don't miss out on these seeds. |
| 2 | "Abandoned Cart, Email #2" (Vx8UiM) | QTR5Jv | Still thinking it over? Seed season moves fast | Your items won't last forever -- complete your order today. |

**Also add flow filter (while you're here):**
- Flow Filters > Add condition: `IF 'Started Checkout' at least once in the last 1 day > SKIP`
- This prevents overlap with the Checkout Abandonment flow (SxbaYQ)

---

## FLOW 6: UPSELL (VZsFVy) -- SWAP 2

URL: https://www.klaviyo.com/flow/VZsFVy/edit

| Step | Current Email | New Template | New Subject | New Preview |
|------|-------------|-------------|-------------|-------------|
| 1 | "Seed update: these products..." (XmTMDg) | UuAkHu | Products that go great with your seed, {{ first_name\|default:"there" }} | Expert-picked complements to get the most from your planting. |
| 2 | "calendar+Upsell" (VPQrbk) | UCr7i7 | Your planting calendar + top picks for this season | When to plant, what to add, and how to get the best results. |

---

## FLOW 7: BROWSE ABANDONMENT -- NEW FLOW SETUP

The Category-Aware Browse Abandonment flow (V2q3uA) exists as a draft.
URL: https://www.klaviyo.com/flow/V2q3uA/edit

If the draft has email actions, assign these templates by persona branch:

| Branch | Template | Subject | Preview |
|--------|----------|---------|---------|
| Lawn browsed | T5ZuRM | Still looking for lawn seed, {{ first_name\|default:"there" }}? | These are our most popular lawn blends this season. |
| Pasture browsed | VZPd7B | Still thinking about pasture seed? | Top-rated pasture blends for your land. |
| Wildflower browsed | Vg9TZ5 | Those wildflower seeds are still waiting | Create something beautiful -- our best wildflower mixes. |
| General/other | WiUup2 | You were looking at something special | The seed you browsed is still available. |

Then activate the flow to **Live** and pause the old Standard flow (Xz9k4a).

---

## FLOW 8: SUNSET -- NEW FLOW BUILD

No sunset flow exists yet. Build one:

1. Create new flow: Trigger = Segment (Inactive subscribers -- no opens in 90 days)
2. Email 1 (Day 0): Template **VuBUV6**
   - Subject: `Still want to hear from us, {{ first_name|default:"there" }}?`
   - Preview: `We noticed you haven't opened our emails in a while.`
3. Time Delay: 7 days
4. Email 2: Template **XS3QTF**
   - Subject: `This is our last email unless you tell us otherwise`
   - Preview: `Click to stay subscribed, or we'll remove you to keep your inbox clean.`
5. If no click after Email 2 > Suppress/unsubscribe from marketing

---

## EXECUTION ORDER (Recommended)

Do these in order of impact and simplicity:

1. **Winback** (VvvqpW) -- 2 swaps, 5 min
2. **Cart Abandonment** (Y7Qm8F) -- 2 swaps + filter, 10 min
3. **Upsell** (VZsFVy) -- 2 swaps, 5 min
4. **Shipment** (UhxNKt) -- 1 swap + 2 new emails, 15 min
5. **Welcome Series** (WQBF89) -- 8 swaps, 20 min
6. **Post-Purchase** (HRmUgq) -- 2 swaps + 3 new emails + activate, 20 min
7. **Browse Abandonment** (V2q3uA) -- assign 4 templates + activate, 15 min
8. **Sunset** -- build from scratch, 20 min

**Estimated total: ~2 hours of focused UI work**

---

## VERIFICATION AFTER COMPLETION

After all swaps, verify:
- [ ] Each flow is set to Live
- [ ] Each email action within flows is set to Live
- [ ] Send yourself a test email from each flow to confirm the new design renders
- [ ] Check subject lines and preview text display correctly
- [ ] Confirm Winback coupon code WELCOME20 exists in WooCommerce
