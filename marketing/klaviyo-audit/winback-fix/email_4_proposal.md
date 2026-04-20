# Winback Email 4 Proposal — NEW (last-chance)

**Flow:** `VvvqpW` Winback Flow
**Timing:** Day 20 after entry (offer expiration day)
**Purpose:** Final push before sunset routing

## Subject line
`Tonight — your $15 credit expires`

(36 chars; urgency; minimal)

## Preview text
`Last chance. One click to shop with $15 off.`

## Body (outline — deliberately short)

```
Hi {{ first_name|default:"there" }},

This is the last email about your $15 credit.

It expires tonight at midnight MST.

Code: WELCOME-BACK-15

Use it before it's gone →

(Orders $75 or more. One use per customer.)

—
The Nature's Seed Team
{% unsubscribe 'Unsubscribe' %}
```

## CTA
Primary: "Use it before it's gone →"
Single CTA, high contrast, above the fold.

## Why this works
- **Radical simplicity** — one message, one CTA, no product recommendations
- **Matches the moment** — by day 20 they've decided; a long email wastes the opportunity
- **Honest framing** — "This is the last email about your $15 credit" — truth as a feature
- **Anti-pattern avoided** — NOT a second discount, NOT a bigger discount, NOT a new hook. Consistent with spec rule against "stacking offers that train discount-waiting"
