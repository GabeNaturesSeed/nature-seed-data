# Nature's Seed — Level 10 Email & Omnichannel Flow System
## Complete Architecture for a Conversion-Driven, Lifecycle-Aware Program

> **Date**: March 2026 | Authority: 4-year Klaviyo audit + industry research
> **North Star**: $400K–$700K/year in flow revenue (up from ~$160K) + 25%+ of total email revenue from automation

---

## How to Read This Document

This plan operates on three axes simultaneously:
1. **Who** — which persona/category the customer belongs to
2. **Where** — which lifecycle stage they're in
3. **When** — which seasonal window is active

Every flow decision must account for all three. A Pasture rancher in September (fall seeding window) is completely different from a Wildflower hobbyist in July (off-season). The same trigger fires different messages to both.

---

# PART 1: THE CUSTOMER ARCHITECTURE

## 1.1 — Persona × Category Matrix

Nature's Seed serves five distinct buyer personas. Each has different motivations, buying cycles, AOV patterns, and content needs. Every flow, every email, every SMS must know which persona it's speaking to.

```
┌─────────────────┬──────────────────────────────────────────────────────────────────┐
│ PERSONA         │ PROFILE                                                          │
├─────────────────┼──────────────────────────────────────────────────────────────────┤
│ LAWN OWNER      │ Residential. Aesthetic-driven. Wants thick, weed-free lawn.       │
│                 │ AOV: $80–150. Buys spring + fall. Competes on price vs. hardware. │
│                 │ Sub-types: Cool-season (North), Warm-season (South), Transition   │
│                 │ Pain: Seed that doesn't germinate. Patch bare spots.              │
│                 │ Proof: Before/after photos, germination guarantee                  │
│                 │ Tags in Klaviyo: `ns_persona = lawn`                              │
├─────────────────┼──────────────────────────────────────────────────────────────────┤
│ RANCHER /       │ Agricultural. Feed quality + yield. Livestock-driven decisions.   │
│ PASTURE MGR     │ AOV: $200–600+. Buys fall primarily. Multi-year relationship.     │
│                 │ Sub-types: Cattle, Horse, Sheep/Goat, Wildlife/Deer               │
│                 │ Pain: Drought resistance, palatability, stand establishment       │
│                 │ Proof: Yield data, tonnage per acre, expert recommendations       │
│                 │ Tags in Klaviyo: `ns_persona = pasture`                           │
├─────────────────┼──────────────────────────────────────────────────────────────────┤
│ WILDFLOWER /    │ Lifestyle. Pollinator habitat, aesthetics, conservation.          │
│ POLLINATOR      │ AOV: $50–120. Buys spring primarily (Mar–May). Gift potential.    │
│                 │ Sub-types: Backyard, Regional native (CA, TX), Commercial         │
│                 │ Pain: Getting it to bloom, weed competition in first year         │
│                 │ Proof: Customer photos, bloom calendars, regional success          │
│                 │ Tags in Klaviyo: `ns_persona = wildflower`                        │
├─────────────────┼──────────────────────────────────────────────────────────────────┤
│ CLOVER /        │ Practical. Soil health, nitrogen fixing, food plot, cover crop.  │
│ COVER CROP      │ AOV: $80–200. Spring + fall. Often farming-adjacent.              │
│                 │ Sub-types: Lawn clover (microclover), food plot, soil improvement │
│                 │ Pain: Planting timing, mow height, mixing with existing grass     │
│                 │ Proof: USDA data, before/after soil tests, yield improvement      │
│                 │ Tags in Klaviyo: `ns_persona = clover`                            │
├─────────────────┼──────────────────────────────────────────────────────────────────┤
│ CONSERVATION /  │ Mission-driven. Restoration, erosion, habitat, native plants.    │
│ PROFESSIONAL    │ AOV: $300–2,000+. Institutional buying cycles. Bulk orders.       │
│                 │ Sub-types: Land manager, contractor, gov/municipal, nonprofit      │
│                 │ Pain: Species correctness, USDA zone compliance, certifications    │
│                 │ Proof: TWCA certification, native species documentation            │
│                 │ Tags in Klaviyo: `ns_persona = conservation`                      │
└─────────────────┴──────────────────────────────────────────────────────────────────┘
```

**Persona detection rules** (profile property `ns_persona`, set programmatically):
- Set on first purchase based on product category ordered
- Override if second category purchase is different
- Use browse behavior as pre-purchase signal (browsed pasture pages 3x → mark pending)
- Yard Plan data feeds persona detection automatically

---

## 1.2 — The Lifecycle Stage Framework

Every customer is always in exactly one of these stages. Flows route to the correct stage and advance them forward.

```
STAGE 0: PROSPECT (subscribed, no purchase)
         ↓ [Flow: Welcome Series]
STAGE 1: FIRST-TIME BUYER (1 order)
         ↓ [Flow: New Customer Onboarding]
STAGE 2: ENGAGED BUYER (2-3 orders, <12mo since last)
         ↓ [Flow: Reorder Reminder + Cross-Category]
STAGE 3: LOYAL / VIP (4+ orders OR $500+ LTV)
         ↓ [Flow: VIP Recognition + Early Access]
STAGE 4: AT-RISK (Klaviyo churn risk HIGH, or >10mo since last order)
         ↓ [Flow: Pre-Churn Intervention]
STAGE 5: LAPSED (12–24mo since last order)
         ↓ [Flow: Win-Back Sequence]
STAGE 6: DORMANT (24mo+ since last order, low engagement)
         ↓ [Flow: Sunset / Final Offer]
```

**Klaviyo predictive properties to use**:
- `predicted_clv` → route high-value prospects to VIP track earlier
- `churn_risk` → trigger Pre-Churn Intervention before they go lapsed
- `expected_date_of_next_order` → trigger Reorder Reminder at T-21 days from predicted date
- `historic_clv` → used in VIP threshold ($500+ LTV = VIP)

---

## 1.3 — The Seed Customer Clock

Seed is not a monthly repurchase product like supplements. It has a **bimodal annual buying cycle** with persona-specific windows. Every time-sensitive flow must respect this clock — or it fires at the wrong moment.

```
    JAN   FEB   MAR   APR   MAY   JUN   JUL   AUG   SEP   OCT   NOV   DEC
    ───   ───   ───   ───   ───   ───   ───   ───   ───   ───   ───   ───
LAWN      ████  ████  ████              ████  ████  ████
(cool-season)  [early spring planning] [late summer/fall overseeding window]

PASTURE                                 ████  ████  ████  ████
(most regions)              [fall primary planting window — Aug through Oct]
                  [spring secondary — some regions plant in Feb–Apr]

WILDFLOWER        ████  ████  ████                          ████  [fall sow]
(spring peak)     [spring planting — Feb through May]

CLOVER      ████  ████  ████              ████  ████
(bimodal)   [early spring] and [late summer — Aug/Sep establishment]

CONSERVATION varies by project — treat as year-round with consultation trigger
```

**Implication**: The Reorder Reminder flow doesn't fire "X months after purchase." It fires when the customer's planting window opens — derived from their persona + USDA zone (stored as profile property).

---

# PART 2: THE COMPLETE FLOW STACK

## 2.1 — Flow Map Overview

48 distinct flow programs organized into 8 layers. Each has a unique trigger, audience, channel mix, and goal.

```
LAYER 1: ACQUISITION        (Prospect → First Buyer)
LAYER 2: CONSIDERATION      (High-intent behavior before purchase)
LAYER 3: CONVERSION         (Cart/Checkout recovery)
LAYER 4: ONBOARDING         (First purchase experience)
LAYER 5: RETENTION          (Repeat purchase + category expansion)
LAYER 6: LOYALTY            (VIP recognition + rewards)
LAYER 7: WIN-BACK           (Reactivation at every lapse stage)
LAYER 8: OPERATIONAL        (Transactional + hygiene)
```

---

## LAYER 1: ACQUISITION FLOWS

### Flow A1 — Subscriber Welcome Series
**Status**: Activate now (WQBF89 draft exists, 8 emails)
**Trigger**: Subscribed to Newsletter list (NLT2S2) AND NOT placed order
**Goal**: Convert subscriber to first buyer within 21 days
**Target RPR**: $3–$5 (industry avg $2.65)
**Channel**: Email only (pre-purchase; no SMS consent yet)

```
Day 0  → Email 1: "Welcome to Nature's Seed" — Brand story + quality differentiation
          Subject: "Welcome — here's what makes our seed different"
          CTA: Shop by category quiz or Yard Plan
          Persona tag: SET based on sign-up source/click behavior

Day 3  → Email 2: Category-aware education (split by persona tag if set)
          [Lawn path]: "Why germination rate matters more than price"
          [Pasture path]: "How to read a forage quality analysis"
          [Wildflower path]: "When to plant wildflowers in your region"
          [Generic]: "The #1 mistake people make when buying seed"

Day 7  → Email 3: Social proof + bestsellers in their category
          "What [5,000] customers planted this season"
          Dynamic product block: top 3 SKUs in their persona category

Day 12 → Email 4: Address the objection
          [Lawn]: "Our seed vs. hardware store seed — what they don't tell you"
          [Pasture]: "Why cheap seed costs more per pound of dry matter"
          [Wildflower]: "Why your wildflowers failed (and how to fix it)"
          [Clover]: "The right clover for your region and soil"

Day 17 → Email 5: Urgency — seasonal window closing
          "Spring planting window is [X weeks away] in [region]"
          OR "[Season] is the right time to plant your [category]"
          Intro offer: 10% off first order (expires 72 hours)

Day 21 → Email 6 (if no purchase): Final offer
          "$15 off your first order — expires tonight"
          Dollar amount (not %) — proven more effective for conversion
          → If still no purchase: move to Browse Abandonment or suppress
```

**Persona routing**: By email 2, split into 5 tracks using conditional split on `ns_persona` property. If unknown, send the generic "mistake" angle — it works cross-category.

**Flow exit condition**: Placed Order → immediately exit and enter Onboarding flow

---

### Flow A2 — Yard Plan Nurture (Upgrade)
**Status**: Live but 6 emails need expansion (TFkMLx)
**Trigger**: Yard Plan Created metric (UwVRsc)
**Goal**: Convert Yard Plan user into purchaser using their plan data
**Unique advantage**: We KNOW exactly what they need. We have their specific seed recommendation.

```
Day 0  → Email 1 (existing): "Your Yard Plan is ready" + personalized results
Day 2  → Email 2 (existing): Zone-specific care guide
Day 5  → NEW: "Your plan calls for [specific seed] — here's why this blend"
          Pull the specific recommended product from Yard Plan data
          Deep dive on that product — ingredients, germination, results
Day 10 → NEW: "3 customers with similar yards chose this blend"
          UGC / review block for the recommended product
Day 14 → NEW: Time-sensitive planting window message
          "In [their region], the best time to plant is [date range] — that's [X] weeks away"
Day 21 → NEW: Final offer — "10% off your Yard Plan recommendation"
```

---

### Flow A3 — Lead Magnet / Content Nurture
**Status**: Not built
**Trigger**: Newsletter Signup metric (WfLs7p) via site forms other than checkout
**Goal**: Warm up educational leads who didn't sign up via purchase intent
**Use case**: People who sign up from blog posts, planting guides, or educational content

```
Day 0  → "Thanks for subscribing — here's [the guide you requested]"
Day 5  → Related educational content (based on guide topic)
Day 10 → Product relevance bridge: "The guide talked about X — here's the seed for it"
Day 15 → Enter Welcome Series at Email 3 (skip brand intro, they already know NS)
```

---

## LAYER 2: CONSIDERATION FLOWS (Pre-Purchase Intent)

### Flow B1 — Category-Aware Browse Abandonment
**Status**: Activate V2q3uA draft (3 emails). Replace Standard flow (Xz9k4a).
**Trigger**: Viewed Product (WooCommerce event) — has not placed order in last 30 days
**Suppression**: In Checkout Abandonment or Cart Abandonment flow

The Standard flow sending 4 generic emails is wrong. Each persona needs its own voice.

```
PASTURE TRACK (browsed pasture products):
  Email 1 (2hr): "Still looking for pasture seed?"
    Lead with: stocking rate calculator or "how many acres" copy
    Product: top 2–3 pasture blends most similar to viewed product
    CTA: "Find the right blend for your acres"

  Email 2 (24hr): "What [ranchers/horse owners/deer hunters] are planting this season"
    Social proof: category-specific reviews
    Urgency: "Fall planting window opens in [X weeks]" (seasonal)

  SMS (36hr, if consented): "[Name], your pasture seed is waiting — [short link]"
    Only if SMS consent AND email 1 was not clicked

LAWN TRACK:
  Email 1 (2hr): "Still looking for lawn seed?"
    Lead with: germination guarantee, before/after photos
    Product: their browsed product + 1 recommended alternative

  Email 2 (24hr): "Why our fescue/rye/bluegrass outperforms big-box store blends"
    Educational angle → leads to product

  SMS (36hr): "[Name], that lawn seed is still here — plus 10% off today only"

WILDFLOWER TRACK:
  Email 1 (2hr): Visual-led email — full color wildflower imagery
    "Imagine this in your yard"
    Less copy, more visuals, big CTA

  Email 2 (24hr): "Bloom calendar for [their region]" + product
    Show what's blooming month by month with the seed they viewed
    CTA: "Plant before [date] for first-year blooms"

  Email 3 (72hr): "Our best seller in your region ships free over $75"
    Urgency + free shipping threshold

CLOVER TRACK:
  Email 1 (2hr): "The right clover for [their use case]"
    Functional copy: nitrogen, palatability, mow height
  Email 2 (24hr): Soil health angle + social proof from similar customers

GENERIC TRACK (no persona detected):
  Email 1: "You were looking at something — can we help?"
    Category filter buttons in email — click to reveal persona
  Email 2 (24hr): Top sellers across all categories
```

**Expected RPR target**: $1.95 (industry avg) → $3+ with persona-specific messaging

---

### Flow B2 — High-Intent Browse (Multi-Session Signal)
**Status**: Not built
**Trigger**: Custom — profile has viewed same product 3+ times in 14 days, no purchase
**Goal**: Intercept the "almost ready" buyer before they go dormant

This customer is not browsing casually — they're doing research. The message should acknowledge that.

```
Email 1 (same day as 3rd view): "You've been looking at [product] — questions?"
  Conversational subject: "Had a chance to look into [product name]?"
  Body: Address the top 3 objections for that category
  CTA: "Chat with us" OR "Call [phone number]" OR "Read the planting guide"

Email 2 (+48hr, if no purchase): Expert recommendation
  "Our seed specialist recommends this for [their region/use]"
  Include a specific expertise signal (TWCA certification, germination data)
  Light offer: free shipping on first order
```

---

### Flow B3 — Wishlist / Saved Product (Future)
**Status**: Requires WooCommerce wishlist plugin integration
**Trigger**: Product added to wishlist but not to cart in 72 hours
**Goal**: Convert wishlisted items during seasonal windows

Not a current priority — flag for Q4 2026 after other layers are built.

---

## LAYER 3: CONVERSION FLOWS

### Flow C1 — Checkout Abandonment (Optimize existing: SxbaYQ)
**Status**: Live — 3 emails. Top revenue flow at $37K. Optimize, don't rebuild.
**Trigger**: Started Checkout metric (no order placed in 4 hours)

Current structure is functional. Specific upgrades:

```
Email 1 (1hr) — Keep: Friendly reminder, no pressure, show cart
  UPGRADE: Add germination guarantee badge + free shipping threshold reminder
  Subject test: A "Your cart is waiting" vs. B "[Product name] almost yours"

Email 2 (12hr) — Upgrade: Add persona-specific social proof block
  Current: "Need Help or More Info?" (too passive)
  Replace with: 3 reviews from similar customers + a specific expertise signal
  Subject test: A "Here's what [1,200] customers say" vs. B "A quick question about your cart"

Email 3 (24hr) — Upgrade: Dollar offer (not %)
  Current: "Last Chance Offer" — confirm this has an actual offer
  Set: "$15 off your order — expires in 24 hours" with countdown timer
  Add: Live inventory signal if product stock is low ("Only 12 bags left")

SMS (if consented, 36hr after email 3 if no click):
  "Last chance: $15 off your cart at Nature's Seed. Expires tonight → [link]"

Email 4 (NEW, 48hr, HIGH VALUE CARTS ONLY — >$150):
  Segment: cart value above $150
  "We saved your cart — and your discount still works"
  Include: consultation CTA ("talk to a seed specialist about your order")
```

---

### Flow C2 — Cart Abandonment (Fix existing: Y7Qm8F)
**Status**: Live but broken — $2K vs. $37K checkout flow. Diagnosis required first.

**Diagnosis steps before any rebuild**:
1. Pull send volume: how many people enter Y7Qm8F per month?
2. Compare to SxbaYQ volume: if <20% of checkout abandonment volume, the cart trigger isn't firing properly
3. Check Klaviyo flow filter: is there a "started checkout" suppression? There should be — someone who reaches checkout shouldn't also be in cart abandonment

**If diagnosis reveals overlap (likely)**:
```
New architecture:
  Cart Abandonment (Added to Cart → No Checkout Started in 1 hour):
    Email 1 (1hr): Simple "You left something" — lighter than checkout abandonment
    Email 2 (12hr): Category-specific "what others add to their cart" — social proof play
    → If they reach checkout: exit C2, enter C1

  Checkout Abandonment (SxbaYQ):
    Add C2 exit filter: "Suppress anyone currently in Cart Abandonment"
```

**Expected lift after fix**: +$5,000–15,000/year from recovering the overlap leak

---

### Flow C3 — Back-in-Stock
**Status**: ~~Not applicable — removed from scope~~
**Note (March 2026)**: Nature's Seed does not place products out of stock. When a product has a long lead time, a "delivery time 3–4 weeks" notice is displayed on the product page, cart, and checkout. Customers are already aware of lead times at purchase. No back-in-stock trigger exists, and no flow is needed.

**Future consideration**: If NS ever introduces a true waitlist/notify-me feature, revisit this flow.

---

### Flow C4 — Price Drop Alert
**Status**: Not built. Triggered by WooCommerce sale price events.
**Trigger**: Product price decreases for a product a profile has browsed
**Goal**: Convert price-sensitive browsers

```
Email 1: "[Product] just went on sale — [X]% off"
  Body: Simple, clean. The news is the email.
  Urgency: "Sale ends [date]"
```

**SMS (same)**: Price drop alerts are one of the highest-converting SMS use cases.

---

## LAYER 4: ONBOARDING FLOWS

### Flow D1 — New Customer Onboarding (First Purchase)
**Status**: Draft exists (HRmUgq — "New Customer Thank You", 2 emails). Needs full build.
**Trigger**: Placed Order (WooCommerce) — first order only (filter: order count = 1)
**Goal**: Ensure product success → prevent buyer's remorse → set up reorder behavior
**Channel**: Email primary, SMS for time-sensitive planting alerts

This is the most important relationship-building flow. The customer just trusted you with money. Every email should earn more trust than it asks for.

```
Email 1 (Day 0, order confirmation + more):
  NOT just a receipt. A welcome into a community.
  Subject: "Your seed is on its way — here's how to set it up for success"
  Content:
    - Order summary (functional)
    - Planting prep guide link for their category
    - What to expect timeline: "Your seed arrives in 3–5 days. Best time to plant: [window]"
    - 1-sentence brand promise: "If your seed doesn't germinate, we make it right."
  NO upsell in email 1. Pure value delivery.

Email 2 (Day 3 — delivery window):
  "Your seed should be arriving today or tomorrow"
  Content: Storage instructions (important! improperly stored seed fails)
  Video embed or GIF: unboxing / planting walkthrough
  CTA: "Download your [Lawn/Pasture/Wildflower] planting guide (PDF)"

SMS (Day 5 — if consented): "Your Nature's Seed order is delivered! Ready to plant? Your guide: [link]"

Email 3 (Day 7 — planting time):
  "[Persona]: it's time to plant"
  [Lawn]: Soil prep → seeding rate → watering schedule
  [Pasture]: Seedbed prep → inoculation → planting depth
  [Wildflower]: Site clearing → scatter method → what to expect month 1
  Include: "Reply to this email if you have questions" — builds trust, generates conversations

Email 4 (Day 21 — germination window):
  "How's it looking?"
  [Lawn/Wildflower/Clover]: germination should be visible
  Include: "What to do if you see bare spots" (prevention of return/complaint)
  CTA: "Share a photo with us" — UGC collection
  CTA 2: "Leave a review" — timed perfectly (first sign of success)

Email 5 (Day 45 — establishment stage):
  "Your [product] should be established now — here's what comes next"
  Content: maintenance guide for their specific product
  Introduce: complementary products for their stage (fertilizer, tackifier, etc.)
  This is the FIRST appropriate upsell moment — after success is confirmed
```

---

### Flow D2 — Shipment Flow (Upgrade: UhxNKt)
**Status**: Live — 1 email only (tracking). Massive missed opportunity.
**Trigger**: Fulfilled Order / Shipped metric
**Integration note (March 2026)**: Can integrate with the Shippo API to pull real-time carrier tracking data — use actual delivery ETA/confirmation instead of estimated windows. This makes Email 2 fire on true delivery confirmation rather than a day estimate.

```
Email 1 (Ship day): "Your order is on its way!"
  Keep existing. Add: Tracking link + estimated arrival + "prep while you wait" guide link

Email 2 (NEW — Day of delivery):
  "Your seed arrives today"
  Content: Seed storage best practices (critical for product success)
  [Bonus]: "3 things to do in the next 24 hours" checklist

Email 3 (NEW — 3 days after delivery):
  "Did everything arrive okay?"
  Short check-in. Invite reply. Flag any issues before they become reviews.
  → Satisfied: bridge to Onboarding Email 3 (planting guide)
  → Issue flagged: alert customer service (tag profile)
```

**Transactional open rates are 60–80%** — this is the most-read email type. Currently using it for only one message.

---

## LAYER 5: RETENTION FLOWS

### Flow E1 — Seasonal Reorder Reminder (Activate: Vzp5Nb / SMZ5NX)
**Status**: Draft (both). Priority P1 — highest ROI per email sent.
**Trigger**: Placed Order → time delay → seasonal window check
**Logic**: Fire based on `ns_persona` + `ns_region` (USDA zone or state) to hit the RIGHT planting window

This is where the Seed Customer Clock (section 1.3) becomes a flow.

```
[PERSONA × SEASON TIMING]:
  Lawn (cool-season) → Reorder reminder fires: July 15 – Aug 15 (before fall seeding)
  Lawn (warm-season) → Reorder reminder fires: Jan 15 – Feb 15 (before spring seeding)
  Pasture → Reorder reminder fires: July 1 – Aug 1 (before primary fall window)
  Wildflower → Reorder reminder fires: Jan 15 – Feb 15 (before spring scatter)
  Clover → Reorder reminder fires: July 15 – Aug 15 (late summer planting)

Trigger: Placed Order → Wait until X months before season window → Enter flow
  (Klaviyo time delay set dynamically using Delivery Windows feature or date-based logic)

Email 1 — "It's almost [season] — is your [lawn/pasture] ready?"
  Subject: "Is your lawn ready for fall? Here's what to do now"
  Content:
    - "You planted [product name] [X months] ago — time to assess your stand"
    - Quick 3-question "stand health" self-assessment
    - CTA: "Reorder the same blend" (single-click reorder link)
    - Alt CTA: "Has anything changed about your acreage?" (for larger properties)

Email 2 (+7 days, no purchase):
  "Signs your [lawn/pasture] needs overseeding"
  Educational angle — "thin spots, bare patches, weed pressure" are all triggers
  CTA: Product page of their exact previous purchase
  Add: Customer photos showing before/after overseeding

Email 3 (+14 days, no purchase):
  "Last call before [season] — 10% off reorders"
  Introduce the reorder offer at email 3, not earlier
  Urgency: "Shipping takes 3–5 days — order by [date] to plant on time"

SMS (+Day 3 of Email 2, if not clicked email):
  "Hey [name], fall seeding time is coming. Your [product] is ready to ship → [link]"
```

**Expected yield**: If 15% of 3,000 past buyers reorder at $180 AOV = **$81,000/year**. This single flow has the highest ROI of any unbuilt piece.

---

### Flow E2 — Cross-Category Expansion (Activate: Ukxchg)
**Status**: Draft (2 emails). Extend to 4 emails.
**Trigger**: Placed Order → 45 days later → persona cross-check (has NOT ordered from category B)
**Goal**: Grow share of wallet by introducing the second seed category

The category ladder model — customers who buy from 2+ categories have 3–5x higher LTV.

```
CATEGORY LADDER (proven paths from campaign data):
  Pasture → Clover (soil health angle; "feed your land and your livestock")
  Pasture → Cover Crop (rotation angle; "rest your pasture with a cover crop")
  Lawn → Wildflower (curb appeal + pollinators; "your neighbors will notice")
  Lawn → Microclover (weed suppression angle; "eliminate weeds, fix nitrogen")
  Wildflower → Native Grasses (habitat completion angle)
  Clover → Pasture (scaling up from hobby to acreage)
  Any → Tackifier / soil amendment (not a new category — an add-on for success)

Email 1 (+45 days post-purchase):
  [Lawn → Wildflower]: "Most homeowners with great lawns add wildflowers too"
  Content: 3 photos of wildflowers + lawn combo. Make it aspirational.
  CTA: "Shop [category] best sellers"

Email 2 (+7 days):
  "The #1 wildflower blend for [their state]"
  Regional specificity builds trust immediately
  Product recommendation: the top wildflower SKU for their USDA zone

Email 3 (+14 days):
  "Plant wildflowers with your [product name] — here's how"
  Educational integration: "these two plantings complement each other"
  Add: customer story of someone who did both

Email 4 (+21 days):
  "10% off your first [category] order — valid 72 hours"
  Cross-category introductory offer
```

---

### Flow E3 — Anniversary & Milestone Flow
**Status**: Not built
**Trigger**: 12-month anniversary of first order date
**Goal**: Celebrate loyalty, invite reorder, reinforce brand relationship

```
Email 1: "One year ago, you planted [product name] — here's what we noticed"
  Personalize with their order history
  If they've ordered multiple times: celebrate their loyalty
  If they've only ordered once: "Time to see what you've been missing"
  CTA: "See what's new this season"

Email 2 (+3 days, if no click):
  "Happy anniversary — a gift from us"
  Annual loyalty discount: $10 off any order
  No expiry pressure — this is a genuine gift, not a manipulation
```

---

## LAYER 6: LOYALTY FLOWS

### Flow F1 — VIP Recognition & Early Access (Activate: X5iW5B)
**Status**: Draft (1 email). Build to 3 emails with ongoing logic.
**Trigger**: Customer reaches $500 historic CLV OR 4+ orders (whichever first)
**Goal**: Make them feel special. VIP customers have 5x higher retention.

```
Email 1 (VIP unlock): "You've earned something"
  NOT a discount email. A genuine recognition moment.
  Content: "You're one of [X] customers who've ordered [4]+ times from Nature's Seed"
  "We built something for our best customers — early access to new products"
  Introduce VIP badge / status (even if informal)
  CTA: "Shop our new arrivals 48 hours before anyone else"

Email 2 (+3 days): "Your VIP discount — always on"
  5% VIP-always-on discount code (permanent, not expiring)
  Reinforce: "This is our way of saying thanks for trusting us season after season"

Email 3 (+7 days): "Introduce a friend — they get your VIP rate too"
  Referral hook: "Give a friend 10% off and get $15 in store credit"
  → Enter referral flow if clicked
```

**Ongoing VIP track** (campaigns, not flows):
- Early access emails sent 48hr before public launches
- Private sale invitations
- Direct line to seed specialist (email/phone)
- Year-end "thank you" with personalized order history recap

---

### Flow F2 — Referral & Advocacy
**Status**: Not built
**Trigger**: Placed Order + Review Left (VcUYec or YtsvSz metric)
**Goal**: Turn satisfied customers into acquisition channels

```
Email 1 (post-review): "Thank you for your review — help a friend too"
  Content: "Your neighbors, ranching friends, and family face the same seed challenges"
  Referral mechanism: unique link or code ("Give [first name]'s link")
  Offer: Friend gets $15 off first order. You get $15 store credit.

Email 2 (+7 days, if no referral click):
  "Sharing is rewarding — here's how easy it is"
  Simplify the ask: text/share a single link
  Add: "The [Wildflower/Pasture/Lawn] community is better when more people know about NS"
```

**Channel**: Email + SMS (if consented). Referrals are a high-trust, personal action — SMS from a friend's recommendation is more compelling.

---

## LAYER 7: WIN-BACK FLOWS

### Flow G1 — Pre-Churn Intervention (New — AI-powered)
**Status**: Not built. Trigger setup needed — RFM segments already exist (see note).
**Trigger**: Churn risk changes to "HIGH" (>66%) for a customer with at least 1 order
**RFM note (March 2026)**: RFM segments are already built in Klaviyo — identifiable by "(rfm)" in their title. However, Klaviyo's native marketing tools are not recognizing these as RFM segments (known issue — fix scheduled for a later session). The segments themselves are valid and can be used as flow triggers today.
**Goal**: Prevent lapse before it happens — far cheaper than win-back after the fact

```
Email 1 (churn risk goes HIGH):
  Subject: "Haven't heard from you in a while, [name]"
  Content: Soft check-in. "Is there anything we can do better?"
  3-button survey: "Didn't need seed yet" / "Found a different source" / "Price / other"

  → Branch A (clicked "Didn't need seed yet"):
    Tag `ns_not_season` → suppress from sales emails until their next season window
    Send: "We'll reach out when it's time to plant again in [region/season]"

  → Branch B (clicked "Found different source"):
    Send: competitive comparison email — "Here's how we compare on [key factors]"
    + Small win-back offer: $10 off

  → Branch C (clicked "Price / other"):
    Send: value justification email + loyalty discount
    "Your loyal customer discount: 10% off your next order"

Email 2 (+10 days, no click on any):
  "A gift — just in case you're ready to plant again"
  $10 off, no conditions, expires in 7 days
  Keep it short. One CTA.
```

---

### Flow G2 — Win-Back Sequence (Rebuild: VvvqpW + WpFDg7)
**Status**: VvvqpW live but $0 revenue. WpFDg7 draft (5 emails) ready to activate.
**Trigger**: Added to Win-Back Opportunities segment (JNTYgB) — lapsed 12–18 months
**Goal**: Reactivate at least 3–5% of lapsed customers (industry target)

**The current flow fails because**: Email 2 is "Educational." Lapsed customers don't need education. They need a reason to come back TODAY.

```
Email 1 (Day 0): "We've missed you — here's what's new"
  Warm, personal tone. Not desperate.
  Content:
    - "A lot has changed since you last ordered"
    - New product spotlight (2–3 SKUs launched since their last order)
    - "Your previous order: [product name]" (personalization signal)
  CTA: "See what's new"
  NO offer yet — this is the re-introduction

Email 2 (Day 5): "What [ranchers/lawn owners/wildflower fans] planted this season"
  Social proof from their persona category
  Recent customer results photos / reviews
  Light urgency: "[Season] planting window is [X weeks away]"
  CTA: "Get ready for [season]"
  Still no offer — building the case

Email 3 (Day 12): THE OFFER
  "$20 off — welcome back, [name]"
  Dollar amount, not percent
  Clear expiry: "This offer expires in 48 hours"
  Short email. The offer IS the email. Don't bury it.

Email 4 (Day 20, no purchase): "Last chance — your $20 expires tonight"
  Countdown timer
  One sentence: "[Name], $20 off your comeback order at Nature's Seed. Tonight only."
  One CTA button.

Email 5 (Day 30): The survey / exit
  "Before we stop reaching out — can you help us understand?"
  3-button: "Not the right time" / "Found a better option" / "Price"
  → "Not the right time" → suppress until next season window
  → "Better option" → competitor acknowledgment + value comparison
  → "Price" → send a final 15% off (deeper discount only after learning the barrier)

  → If no response: exit to Sunset flow

SMS (between Email 2 and Email 3, if consented):
  "Hey [name] — it's been a while. We have something for you → [link]"
  SMS should arrive the day BEFORE Email 3's offer, priming them
```

**Expected impact**: 45% open rate (industry stat for winback), 11% CTR, 3–5% conversion = significant.

---

### Flow G3 — Sunset / Final Suppression (Upgrade: UZf9UD)
**Status**: Live (2 emails). Extend to 3 with better final-offer logic.
**Trigger**: Added to Sunset segment (no engagement in 18+ months)

```
Email 1 (existing): Keep — "Are you still there?"
  Add: explicit "click to stay subscribed" CTA + "let us know your season" dropdown

Email 2 (existing): Keep — "Last email" concept
  Upgrade: Add a final offer — $10 off "just in case you want to plant again"

Email 3 (NEW, +14 days): Final engagement check before hard suppression
  Ultra-minimal: "One click to stay on our list — or we'll stop emailing you"
  → Click: re-enter appropriate lifecycle stage
  → No click: move to suppression list. Done.
```

**List hygiene note**: Aggressively suppressing unengaged contacts improves deliverability for active contacts. The Sunset flow IS a revenue protection mechanism, not just a cleanup.

---

## LAYER 8: OPERATIONAL FLOWS

### Flow H1 — Review Request (Activate: XHzESB)
**Trigger**: Placed Order → Wait 21 days (germination window for most species)
**Note on timing**: Do NOT trigger at ship/deliver. Seed reviews at "did it germinate?" not "did it arrive?"

```
Email 1 (Day 21): "How's your [product] doing?"
  Conversational. Ask about the seed experience.
  Include: germination check ("should be visible in 7–14 days for most varieties")
  CTA: "Leave a review" [ShopperApproved link]
  Alt CTA: "Something wrong? Tell us" → customer service tag

Email 2 (Day 35, if no review):
  "One photo can help thousands of gardeners"
  UGC angle — "share a photo of your results"
  Lower barrier: photo review vs. written review
  CTA: "Submit photo review" OR "Written review"
```

---

### Flow H2 — Order Issue / Delay Notification
**Status**: Not built
**Trigger**: WooCommerce order status change (processing → on hold / delayed)
**Goal**: Proactive communication prevents bad reviews from surprise delays

```
Email 1 (immediate upon delay flag):
  "An update on your order — [order number]"
  Transparent, apologetic, specific
  New estimated ship date
  CTA: "Questions? Reply to this email" (personal, not ticket system link)
```

---

### Flow H3 — Post-Planting Care Sequence (NEW — 60-day)
**Status**: Not built
**Trigger**: Placed Order → Wait 30 days (seed should be in the ground)
**Goal**: Ensure planting success → prevent churn from product failure perception

This flow exists because **customer churn from NS often isn't price-related — it's failure to get seed established.** A customer who had poor germination blames the seed, not their technique. This flow prevents that attribution error.

```
Day 30 → Email 1: "Check-in: how's your [product] looking?"
  Category-specific troubleshooting:
  [Lawn]: "Is it patchy? Here's why and what to do"
  [Pasture]: "Thin stand? Could be soil, moisture, or timing — let's diagnose"
  [Wildflower]: "Nothing sprouted yet? Wildflowers are slow — here's what's normal"
  CTA: "I'm having trouble [button]" → tags profile for customer service follow-up
  CTA: "It looks great! [button]" → triggers review request flow

Day 45 → Email 2: "Maintenance guide for [product] — season 1"
  Mowing height, watering schedule, what to expect through the season
  First appropriate cross-sell: "Complement your [lawn/pasture] with [product]"

Day 60 → Email 3: "You're 60 days in — here's what the best [lawn/pasture] owners do next"
  Advanced care + year 2 planning
  CTA: "Plan for next season" → early reorder reminder
```

---

# PART 3: OMNICHANNEL ARCHITECTURE

## 3.1 — Channel Decision Framework

Not every message deserves every channel. Here's when to use each:

```
EMAIL → Default channel. All flows start here. Long-form education, product showcases,
        newsletters. Best for relationship-building and complex messages.

SMS   → High urgency only. Cart recovery, flash sales, time-sensitive planting windows,
        back-in-stock alerts. Max 2 SMS/month per customer outside of transactional.

META RETARGETING → Audience sync from Klaviyo segments. Use for:
        - Browse abandonment audience → Facebook/Instagram product ads
        - Active buyer segments → lookalike audiences for acquisition
        - Lapsed customers → retargeting to re-engage before winback email

DIRECT MAIL → Future consideration for high-value lapsed customers ($500+ CLV)
              A physical catalog to your best dormant customers converts exceptionally.
```

## 3.2 — Omnichannel Sequencing by Flow

```
CHECKOUT ABANDONMENT (highest urgency):
  T+0hr:  [Email 1] Friendly reminder
  T+12hr: [Email 2] Social proof
  T+24hr: [Email 3] Offer ($15 off)
  T+36hr: [SMS] "Last chance — your cart + discount" (if email 3 not clicked)
  T+48hr: [Meta Retargeting] Product carousel ad fires to this audience
  T+72hr: [Email 4, HIGH VALUE ONLY] Final outreach

BROWSE ABANDONMENT:
  T+2hr:  [Email 1] Category-specific browse recovery
  T+24hr: [Email 2] Social proof + seasonal urgency
  T+36hr: [SMS] Ultra-short nudge (if email not clicked)
  T+48hr: [Meta Retargeting] Product-specific ad (synced from Klaviyo segment)
  T+72hr: [Email 3, Wildflower only] Visual-led final email

WIN-BACK:
  Day 0:  [Email 1] Re-introduction — "what's new"
  Day 2:  [Meta Retargeting] "We miss you" audience activated in Meta Custom Audience
  Day 5:  [Email 2] Social proof
  Day 6:  [SMS] Pre-offer warm-up nudge
  Day 12: [Email 3] The offer
  Day 20: [Email 4] Last chance
  Day 30: [Email 5] Survey / exit

SEASONAL REORDER:
  T-21:   [Email 1] Season awareness — "it's almost time"
  T-14:   [Meta Retargeting] "Time to reorder" ads to past buyer audience
  T-7:    [Email 2] Educational + product
  T-3:    [SMS] "Planting window opens [date] — reorder your seed now"
  T-0:    [Email 3] Last call offer
```

## 3.3 — Suppression Architecture (Prevent Fatigue + Overlap)

```
GLOBAL SUPPRESSION RULES (apply across ALL flows):
├── Max 1 promotional email per day per profile
├── Max 2 SMS per week per profile (non-transactional)
├── If Email clicked today → suppress SMS for 24 hours
├── If SMS clicked today → suppress next promotional email for 12 hours
├── If placed order in last 7 days → suppress ALL cart/browse/checkout abandonment
├── If in active Checkout Abandonment flow → suppress Cart Abandonment
├── If churn risk = HIGH → pause ALL promotional flows, enter Pre-Churn flow only
├── If in Sunset flow → suppress ALL other flows
└── If unsubscribed from email → never send SMS (respect channel opt-out intent)

FLOW-SPECIFIC SUPPRESSION:
├── Welcome Series: exit immediately on first order → enter Onboarding
├── Browse Abandonment: exit if cart or checkout abandonment triggered
├── Win-Back: exit if purchase → enter Onboarding (treat as new customer)
├── VIP Flow: always takes priority over Browse Abandonment
└── Pre-Churn: overrides all other promotional flows until resolved

META AUDIENCE SYNC:
├── Active buyers (Placed Order in last 90 days) → suppress from acquisition ads
├── Lapsed buyers (no order 12+ months) → activate Win-Back audience in Meta
├── Browse abandoners → activate retargeting audience (24hr post-browse)
├── Suppressed / unsubscribed → remove from ALL Meta Custom Audiences
└── Champions segment → seed Lookalike Audience for new customer acquisition
```

---

# PART 4: THE PREDICTIVE LAYER

Klaviyo's predictive analytics are available now and largely unused. These unlock a fundamentally different class of marketing — intervening BEFORE problems occur rather than reacting after.

## 4.1 — Predictive Triggers to Activate

```
PREDICTED NEXT ORDER DATE → Reorder Reminder
  Use case: Customer's expected_date_of_next_order is 21 days from today
  Trigger: Date property crosses threshold
  Action: Enter Seasonal Reorder Reminder at Email 1
  Why it's better than time-delay: Personalized to actual buying rhythm, not generic X months

CHURN RISK → HIGH → Pre-Churn Intervention
  Use case: Customer who ordered 3x now showing HIGH churn risk
  Trigger: churn_risk changes to "high"
  Action: Enter Flow G1 immediately — intercept before they go cold

PREDICTED CLV → VIP Fast-Track
  Use case: New customer whose predicted_clv exceeds $500 even after 1 order
  Trigger: predicted_clv > 500 after first purchase
  Action: Enter VIP Recognition flow early — don't wait for 4th order
  Why: High-CLV customers should be treated as VIPs from day 1 — the model can see it, we should act on it

AVERAGE ORDER VALUE CHANGE → Downgrade Alert
  Use case: Customer who previously bought $200 orders now buying $50
  Use: Flag for customer service / VIP outreach
  Possible cause: Budget constraint, reduced acreage, trying competitor
```

## 4.2 — RFM Routing in Campaigns

All campaigns (not just flows) should be routed through RFM:

```
CHAMPIONS (high R, high F, high M):
  → Early access emails 48hr before public
  → Exclusive offers (VIP-only products)
  → Skip "sale" campaigns — Champions don't need price incentives

LOYAL CUSTOMERS (high F, medium R):
  → Standard campaign recipients
  → Eligible for cross-category offers
  → Include in seasonal campaigns

AT RISK (low R, but historically high F/M):
  → Trigger Pre-Churn flow
  → More frequent win-back touchpoints
  → Higher-value offer when re-engaging

PROMISING (medium everything, trending up):
  → Target with cross-category expansion
  → Eligible for VIP fast-track if CLV threshold hit

NEW CUSTOMERS (1 order, high R):
  → In Onboarding flow — don't also add to broadcast campaigns
  → Protect the experience — no sale blasts during first 30 days

LOST CUSTOMERS (very low R):
  → Win-Back flow only
  → Suppress from ALL standard campaigns
```

---

# PART 5: SEASONAL ORCHESTRATION

The entire system should operate in two modes: **PEAK** and **NURTURE**. These modes are not calendar-fixed — they're persona-specific.

## 5.1 — Operating Modes

```
PEAK MODE (6–8 weeks per season window per persona):
  ├── Increase campaign frequency to 2–3/week
  ├── All conversion flows at maximum priority
  ├── Abandon flows running with full SMS/retargeting
  ├── Reorder reminders in peak urgency mode
  ├── Suppression rules loosen slightly (exception: SMS max still applies)
  └── Revenue goal: 60–70% of annual email revenue generated in peak periods

NURTURE MODE (between peaks):
  ├── Reduce campaign cadence to 1/week or less
  ├── Focus: educational content, community building, product education
  ├── List growth and health: Sunset flow runs aggressively
  ├── Cross-category flows active (less time pressure)
  ├── Review collection campaigns
  └── Predictive model building: track which behaviors predict next-season purchase
```

## 5.2 — Annual Operating Calendar

```
MONTH     LAWN        PASTURE      WILDFLOWER    CLOVER       SYSTEM
───────────────────────────────────────────────────────────────────────────
JAN       PEAK start  NURTURE      PEAK start    NURTURE      Reorder reminders fire for spring
FEB       PEAK        NURTURE      PEAK          NURTURE      Pres. Day sale + Spring launch
MAR       PEAK        NURTURE      PEAK peak     NURTURE      Biggest month — all conversion flows maxed
APR       WIND-DOWN   NURTURE      PEAK          NURTURE      Earth Day, last spring push
MAY       NURTURE     NURTURE      WIND-DOWN     NURTURE      Post-spring nurture begins
JUN       NURTURE     NURTURE      NURTURE       NURTURE      List hygiene, Sunset flow aggressive
JUL       PEAK start  NURTURE      NURTURE       PEAK start   4th of July sale; fall prep early signals
AUG       PEAK        PEAK start   NURTURE       PEAK         Back-to-school = fall planting prep
SEP       PEAK        PEAK peak    NURTURE       PEAK         Biggest fall month
OCT       PEAK        PEAK         FALL SOW      PEAK         Last fall window
NOV       WIND-DOWN   WIND-DOWN    NURTURE       NURTURE      BFCM (opportunistic; not core for seed)
DEC       NURTURE     NURTURE      NURTURE       NURTURE      Holiday gift angle + list growth
```

---

# PART 6: MEASUREMENT FRAMEWORK

## 6.1 — Flow-Level KPIs

Every flow has a primary metric. Not open rate (MPP-corrupted). These are the real numbers:

```
FLOW TYPE             PRIMARY METRIC          TARGET RPR         SECONDARY
─────────────────────────────────────────────────────────────────────────
Welcome Series        Placed Order rate        $3–$5             CTR > 3%
Browse Abandonment    Placed Order rate        $2–$4             CTR > 2%
Cart Abandonment      Placed Order rate        $4–$8             CTR > 4%
Checkout Abandonment  Placed Order rate        $6–$12            CTR > 5%
Post-Purchase         Cross-sell revenue       $1–$3             Review rate
Reorder Reminder      Reorder rate             $5–$10            CTR > 4%
Win-Back              Reactivation rate (%)    $0.84+ (industry) 3–5% conversion
VIP Flow              LTV change (90-day)      Track only        Referral rate
Cross-Category        Category expansion rate  $2–$4             New category %
```

## 6.2 — Program-Level Dashboard (Monthly Review)

```
GOAL 1: FLOW HEALTH
├── Flow revenue this month vs. last month vs. year ago
├── Flow revenue as % of total email revenue (target: 20%+)
├── Active flows with revenue > $1,000/month (target: 8+)
├── Flow entry rate by flow (are triggers firing correctly?)
└── Suppression effectiveness (% who exited flow due to purchase, not unsubscribe)

GOAL 2: LIFECYCLE HEALTH
├── % of subscribers in each stage (Prospect / First-time / Engaged / VIP / At-Risk / Lapsed)
├── Stage progression rate (% of Prospects who became First-time buyers in 30 days)
├── Churn rate by persona (which category is losing customers fastest?)
├── CLV growth by cohort (is the 2024 cohort worth more than 2023 cohort after 12 months?)
└── Reactivation rate from Win-Back flow

GOAL 3: CHANNEL HEALTH
├── Email deliverability: spam rate <0.08%, bounce rate <2%
├── SMS consent rate (% of email subscribers who have SMS consent)
├── Click rate by channel (email vs. SMS — which drives more to purchase?)
├── Meta audience sync accuracy (suppressed customers removed from ad audiences?)
└── Unsubscribe rate by flow (flag any flow with >0.3% unsub rate)

GOAL 4: SEASONAL PERFORMANCE
├── Revenue per planting window (spring vs. fall vs. off-season)
├── Reorder reminder conversion by persona + season
├── Campaign-vs-flow revenue ratio (target: campaigns 75%, flows 25%)
└── New customer acquisition by month (are campaigns growing the list in off-season?)
```

---

# PART 7: IMPLEMENTATION ROADMAP

## Phase 1 — Stop the Bleeding (Week 1–2)

| Task | What | Est. Time | Rev. Impact |
|------|------|-----------|-------------|
| Rebuild Winback Email 2 | Replace "Educational" with $20 off + 48hr urgency | 2hr | $4K+/yr |
| Diagnose Cart Abandonment | Pull send volume vs. checkout flow, identify overlap | 1hr | Diagnosis |
| Fix Cart suppression | Add checkout started filter to Y7Qm8F | 1hr | $5K+/yr |
| Activate Welcome Series | Launch WQBF89 with existing 8 emails, minimal edits | 3hr | $25K+/yr |
| Expand Shipment Flow | Add 2 emails to UhxNKt (delivery + 3-day check-in) | 3hr | $5K+/yr |

---

## Phase 2 — Activate the Drafts (Weeks 3–6)

| Task | What | Est. Time | Rev. Impact |
|------|------|-----------|-------------|
| Launch Category-Aware Browse Abandonment | Activate V2q3uA, pause Xz9k4a | 4hr | $12K+/yr |
| Activate Seasonal Reorder Reminder | Launch Vzp5Nb for spring window (time-sensitive) | 6hr | $36K+/yr |
| Build Post-Purchase — Clover (new) | Only category without a PP flow | 6hr | $8K+/yr |
| Activate Post-Purchase Lawn + Pasture | Expand XdSdtF + VsxGYg to 5 emails | 8hr | $20K+/yr |
| Launch Review Request | Activate XHzESB for Day 21 trigger | 3hr | UGC/trust |

---

## Phase 3 — Build the Retention Engine (Weeks 7–12)

| Task | What | Est. Time | Rev. Impact |
|------|------|-----------|-------------|
| Launch Cross-Category Expansion | Activate Ukxchg + build remaining 2 emails | 6hr | $15K+/yr |
| Launch VIP Recognition | Activate X5iW5B + build 2 additional emails | 5hr | Retention |
| Build Pre-Churn Intervention | New flow using Klaviyo churn risk trigger | 8hr | $10K+/yr |
| Rebuild Win-Back full 5-stage | Activate WpFDg7, replace VvvqpW | 8hr | $10K+/yr |
| Build Referral Flow | Post-review referral invitation | 6hr | Acquisition |
| Fix Upsell Flow product logic | Rethink VZsFVy to cross-sell, not add-on | 3hr | $5K+/yr |

---

## Phase 4 — Intelligence Layer (Q3 2026)

| Task | What |
|------|------|
| Predictive Next Order Date trigger | Replace time-delay reorder with AI-predicted trigger |
| Meta Audience Sync | Connect Klaviyo segments → Facebook Custom Audiences |
| SMS Consent Growth Campaign | Systematic SMS opt-in across all email subscribers |
| Post-Planting Care Sequence | 30/45/60-day post-purchase care flow (H3) |
| Back-in-Stock Flow | WooCommerce + Klaviyo integration for restock alerts |
| Pre-Season Date-Triggered Alerts | USDA zone-aware seasonal window triggers |
| Referral Program Formalization | Swell loyalty program + Klaviyo integration |

---

## Total Revenue Projection

```
PHASE 1 (quick fixes):        +$39,000/yr
PHASE 2 (activate drafts):    +$76,000/yr
PHASE 3 (retention engine):   +$40,000/yr
PHASE 4 (intelligence):       +$50,000/yr (estimate)
──────────────────────────────────────────
TOTAL PROJECTED LIFT:         +$205,000/yr

Current flow revenue:         ~$160,000/yr
Target after full build:      ~$365,000/yr

As % of $2M email revenue:    18% → target 20–25% ✓
```

---

*Research sources: Klaviyo 2025 Benchmark Report, Klaviyo Predictive Analytics documentation, Titan Marketing Agency Replenishment Flow Guide, Astra Results February 2026, Flowium Win-Back Guide, 1800DTC Suppression Architecture Guide, Magnet Monster Predictive Analytics, Enflow Digital 2025 Automation Playbook*
