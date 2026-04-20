# Winback Email 3 Proposal — NEW (standing offer slot per spec §2.3)

**Flow:** `VvvqpW` Winback Flow
**Timing:** Day 12 after entry
**Purpose:** The real reactivation lever — offer + urgency

## Subject line
`{{ first_name|default:"Friend" }}, $15 off — 48 hours only`

(44 chars; dollar-off preferred over percentage for our $181 AOV)

## Preview text
`A come-back gift from Nature's Seed. Ends Friday at midnight.`

## Body (outline)

```
Hi {{ first_name|default:"there" }},

We've set aside a $15 credit for you — no strings attached.

Here's the code:

  WELCOME-BACK-15

→ Apply it to any order $75 or more
→ Expires Friday at midnight MST
→ Combines with free shipping on orders $125+

{% if last_category_purchased %}
WE PICKED A FEW THINGS YOU'VE ORDERED BEFORE:
{% for item in past_purchased_products|slice:":3" %}
  • {{ item.name }} — {{ item.price }}
{% endfor %}
{% else %}
SHOP WHAT'S IN SEASON NOW:
  • Spring lawn seed
  • Native wildflower blends
  • Pasture seed blends for cool-season regions
{% endif %}

Use my $15 credit →

This credit is yours whether you order today or Friday. But it does
expire at midnight Friday.

—
The Nature's Seed Team
{% unsubscribe 'Unsubscribe' %}
```

## CTA
Primary: "Use my $15 credit →"
Link target: Cart with `WELCOME-BACK-15` pre-applied if WC coupon plugin allows; else category PLP.

## Offer economics (spec §2.3)
- **$15 off order $75+** = 20% off at threshold, 12% off at average AOV ($125), 8% off at typical $181 AOV — effective discount stays well inside the 15% cap for typical orders.
- **Expires 48h** — creates urgency without anchoring scarcity-discount-waiting behavior.
- **Standing offer slot** — this is allowed at any time per spec §2.3 (Winback email 3 = standing slot).

## Why this works
- **$ off, not %** (spec §4.2) — scales with AOV, protects margin on heavy orders
- **Urgency framing** — "48 hours only" triggers action without false scarcity
- **Past-purchase product block** — dynamic personalization (spec §4.5 Max tier for reorder flows)
- **Unconditional tone** — "Your credit is yours whether you order today or Friday" removes pressure
