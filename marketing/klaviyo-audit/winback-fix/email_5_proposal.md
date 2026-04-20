# Winback Email 5 Proposal — NEW (final feedback + sunset)

**Flow:** `VvvqpW` Winback Flow
**Timing:** Day 30 after entry
**Purpose:** Capture exit intent data before routing to Sunset flow

## Subject line
`Before we stop emailing — one quick question`

(45 chars; not salesy; implies restraint)

## Preview text
`Two clicks. We'll stop emailing if you pick "yes."`

## Body (outline)

```
Hi {{ first_name|default:"there" }},

We don't want to clog your inbox.

If you'd like us to stop, just click the last option — it's no-fault.
We just want to know why so we can get better.

WHY HAVEN'T YOU ORDERED RECENTLY?

  🌱 I already ordered elsewhere — click here
  💰 Price was a factor — click here
  ⏰ Wrong time of year for me — click here
  📭 Please stop emailing — click here

(Each link tags your profile and, for the last option, unsubscribes you.)

Thanks for being a Nature's Seed customer.

—
The Nature's Seed Team
{% unsubscribe 'Unsubscribe' %}
```

## CTA (four tracked click options)
Each button links to a tagged destination that fires a `Clicked Email` event with a category tag. For the fourth option, additionally route through `{% unsubscribe %}`.

## Why this works
- **Non-salesy tone** — matches the lapsed state of the relationship
- **Data capture** — turns the dead email into learning (why did they lapse?)
- **Honest exit option** — the fourth link is unsubscribe, framed as respect, not as a threat
- **Routing signal** — profiles that click "stop emailing" get Suppressed tag → Sunset flow; profiles that click any other option stay eligible for seasonal campaigns (with cooler cadence)

## Post-flow routing (implementation note for flow filters)
- Clicked `price`, `wrong_time`, `ordered_elsewhere` → tag profile, exit flow, enter seasonal-only campaign eligibility (lower cadence tier)
- Clicked `stop_emailing` → route to Sunset flow → 1 confirmation email → permanent suppress
- No click after 14 days → enter Sunset flow automatically
