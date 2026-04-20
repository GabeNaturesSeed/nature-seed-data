# Winback Email 2 Proposal — REPLACE "Educational"

**Flow:** `VvvqpW` Winback Flow
**Timing:** Day 5 after entry (At Risk `RyASXF` / Lapsed `Sv5cSC` segment entry)
**Replaces:** Current Email 2 labeled "Educational" (0% click rate on current flow)

## Subject line
`We miss you — customers like you are planting this month`

(45 chars; benefit-led; social-proof hook; no spam triggers)

## Preview text
`See what 1,200+ Nature's Seed customers are planting right now.`

## Body (plain-text outline — HTML template in creative spec)

```
Hi {{ first_name|default:"there" }},

It's been a while since your last Nature's Seed order. Spring is here, and
we wanted you to see what's working for other customers right now.

{% if last_category_purchased == "lawn" %}
LAWN CUSTOMERS ARE SEEDING:
→ TWCA Water-Wise Bluegrass Blend — the spring favorite
→ Fine Fescue Turf Blend — for shaded yards
→ Our Clover-Lawn combo — for pollinator-friendly turf

Show me the spring lawn lineup →
{% elif last_category_purchased == "pasture" %}
PASTURE CUSTOMERS ARE SEEDING:
→ Cool Season Cattle Pasture Mix — top seller this month
→ Horse Pasture Seed Mix — proven blend
→ Clover-Pasture interseeds for soil health

Show me the spring pasture lineup →
{% elif last_category_purchased == "wildflower" %}
WILDFLOWER CUSTOMERS ARE SEEDING:
→ Annual Wildflower Mix — instant color
→ Regional native blends for your zone
→ Monarch / pollinator specialty mixes

Show me the spring wildflower lineup →
{% else %}
CUSTOMERS ARE SEEDING:
→ Spring lawn favorites — TWCA-certified blends
→ Wildflower season is open — native blends in stock
→ Pasture blends restocked after winter

Show me what's new this spring →
{% endif %}

Want a little extra reason to come back? Keep an eye on your inbox —
a welcome-back offer is coming shortly.

—
The Nature's Seed Team
1697 W 2100 N, Lehi, UT 84043
{% unsubscribe 'Unsubscribe' %}
```

## CTA
Primary: "Show me the spring [category] lineup →"
Link target: Category PLP matching `last_category_purchased`, fallback to homepage.

## Why this works (rationale per spec)
- **Benefit-led subject** (spec §4.2) — replaces vague/passive "Educational"
- **Social proof hook** — lean on peer customers, not our own pitch
- **Category personalization** (spec §4.5 Mid tier) — uses `last_category_purchased`
- **Teaser for offer email** — sets up Email 3 without burning the discount yet
- **No discount in this email** — per offer rules, discount is concentrated in Email 3 for max impact
