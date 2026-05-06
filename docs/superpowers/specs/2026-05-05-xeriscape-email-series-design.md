# Xeriscape Email Series — Design Spec

**Date:** 2026-05-05
**Status:** Email 1 approved, full series pending

---

## Strategy

Education-first campaign series targeting lawn buyers in 7 xeriscape states. Each email covers a distinct topic. Emails are self-contained educational content — not article teasers. A "Suggested Resources" section at the bottom links to web articles as a bonus.

**Series arc (per state):**
- Monthly educational sends: May, June, July, August
- Promotional sends: end of Month 1 (May), end of Month 3 (July), and when fall planting picks up
- Fall sends (3 emails): September, October, November as planting window opens

**This spec covers Email 1 only.** Full series spec to follow after Email 1 validates the conditional block pattern in Klaviyo.

---

## Audience Architecture

### 7 State Sub-Segments (create in Klaviyo UI, star each)

One segment per state, all targeting lawn buyers:

| Segment Name | Conditions |
|---|---|
| `Lawn Buyers — CA` | Placed Order (any time) AND `$region` = CA |
| `Lawn Buyers — NV` | Placed Order (any time) AND `$region` = NV |
| `Lawn Buyers — AZ` | Placed Order (any time) AND `$region` = AZ |
| `Lawn Buyers — TX` | Placed Order (any time) AND `$region` = TX |
| `Lawn Buyers — CO` | Placed Order (any time) AND `$region` = CO |
| `Lawn Buyers — UT` | Placed Order (any time) AND `$region` = UT |
| `Lawn Buyers — NM` | Placed Order (any time) AND `$region` = NM |

> Note: "Placed Order" is a proxy for lawn buyer without a category filter. If Klaviyo allows filtering by product category in segment conditions, add: product category contains "Lawn" OR "Grass Seed". Otherwise use the simpler condition and refine later.

### Campaign Structure

7 campaigns, one per state, all sending simultaneously. Single shared MJML template — state personalization via Klaviyo `{% if person|lookup:'$region' == 'STATE' %}` conditional blocks inside `mj-text` elements.

---

## Email 1 Spec

**Name pattern:** `Xeriscape Series 1 — [STATE] Lawn Buyers`
**Send date:** Week of 2026-05-11 (after Mother's Day campaigns clear)
**From:** `customercare@naturesseed.com` / `Nature's Seed`
**Subject:** `Xeriscaping in {{ person|lookup:'$region' }}: what it means and how to start`
**Preview text:** `Your state's water situation, the right seed for your climate, and a simple place to begin.`

---

## Template Structure

**File:** `templates/xeriscape-series-1-state-intro.mjml`

### Section 1 — Hero (static)

- Background: `#1b4332`
- Hero label: `Xeriscape Series — {{ person|lookup:'$region' }}`
- Headline: `Xeriscaping in<br/>{{ person|lookup:'$region' }}:<br/><span style="font-style:italic;color:#a8d5b5;">What It Means</span>`
- Sub-headline: `Your state's water situation, the right seed for your climate, and a simple place to begin.`
- CTA button (`#C96A2E`): `Explore Xeriscape Seed` → `https://www.naturesseed.com/xeriscaping/?utm_source=klaviyo&utm_campaign=xeriscape-series-1&utm_content=hero`

### Section 2 — What Is Xeriscaping (static, 2 paragraphs)

P1:
> Xeriscaping is the practice of designing and planting your lawn or landscape to use significantly less water — without sacrificing a green, healthy yard. It doesn't mean gravel and cacti. It means choosing species that are native or adapted to your region's rainfall patterns so they thrive without constant irrigation.

P2:
> The difference comes down to roots. Cool-season grasses like Kentucky bluegrass develop shallow root systems — 2 to 3 inches — that need frequent watering to stay alive. Drought-tolerant native grasses like buffalo grass and blue grama root 4 to 6 feet deep, drawing moisture long after the surface has dried. Once established, they need a fraction of the water — and in many cases, none at all after the first season.

### Section 3 — Your State's Water Situation (state-conditional)

One paragraph per state. Use `{% if person|lookup:'$region' == 'STATE' %}` inside a single `mj-text` block.

**NV:**
> Nevada is the driest state in the U.S. and Southern Nevada's water authority — the SNWA — is in the middle of one of the most aggressive water conservation programs in the country. Starting January 1, 2027, decorative turf irrigation will be restricted statewide. If you have a lawn that serves no functional purpose, the clock is running. The good news: drought-tolerant seed establishes quickly in Las Vegas's climate, and the window to convert before the deadline is still open.

**CA:**
> California has been in various stages of drought emergency for most of the last decade. Water districts across the state — MWD, LADWP, EBMUD, and others — have made turf removal a centerpiece of their conservation strategy. The state also passed AB 1572 in 2023, which phases out non-functional decorative turf irrigation at commercial properties. For homeowners, the shift is voluntary — but incentivized. Converting to native or drought-tolerant seed is one of the most direct things a California lawn owner can do to reduce water consumption.

**AZ:**
> Arizona's cities are growing faster than almost anywhere in the U.S., and the Colorado River — which supplies most of the Southwest's water — is at historically low levels. AMWUA member cities including Phoenix, Scottsdale, Tempe, Mesa, and Chandler have all introduced programs to encourage turf reduction. The desert climate is actually ideal for drought-tolerant native grasses: bermudagrass and buffalo grass both go dormant in winter and green up fast in spring without supplemental water.

**TX:**
> Texas doesn't have a statewide water restriction, but most of its major cities do. SAWS in San Antonio and Austin Water have both made turf rebates and xeriscape education a priority. More broadly, Texas lawns face a real problem: the summer heat and periodic drought cycles that most cool-season grasses simply can't handle. Native Texas grasses — buffalo grass, sideoats grama — are adapted to exactly these conditions. They've been growing in Texas soils without irrigation for thousands of years.

**CO:**
> Colorado's water comes almost entirely from snowpack and river systems that are increasingly strained. Denver Water, the largest water utility in the state, has run a Cash-for-Grass program for years — and the state legislature passed SB23-192 in 2023 requiring water providers to phase out non-functional turf irrigation at commercial properties. For homeowners, blue grama and sheep fescue are the workhorses: cold-hardy enough for Colorado winters, drought-tolerant enough for Colorado summers.

**UT:**
> Utah is the second-driest state in the U.S. and faces some of the fastest population growth in the country — a difficult combination. The Great Salt Lake has dropped to historic lows, largely because of water diverted for landscaping and agriculture. Utah passed HB 410 in 2023 phasing out non-functional grass in commercial settings, and local water conservancy districts across the Wasatch Front have incentive programs for residential conversion. Blue grama, sheep fescue, and buffalo grass all perform well in Utah's semi-arid climate.

**NM:**
> New Mexico gets an average of 14 inches of rain per year — less than most of the American Southwest thinks it does. Albuquerque and Santa Fe have both run active conservation programs for years, and the state's acequia system and water rights infrastructure are under increasing pressure. The Chihuahuan Desert climate that covers most of the state is actually ideal for native grasses: blue grama is New Mexico's state grass for a reason. It's drought-tolerant, cold-hardy, and thrives in the alkaline soils common across the region.

### Section 4 — Products for Your State (state-conditional, 3-column grid)

One `mj-section` with three `mj-column` elements. Product name, 1-line description, and "Shop Now" button (`#C96A2E`) inside each column. All CTAs → `https://www.naturesseed.com/xeriscaping/?utm_source=klaviyo&utm_campaign=xeriscape-series-1&utm_content=product-[1|2|3]`

State-conditional content inside each column's `mj-text` blocks:

| State | Product 1 | Product 2 | Product 3 |
|---|---|---|---|
| NV / AZ | Bermudagrass Drought-Tolerant Blend | Buffalo Grass | Southwestern Wildflower Mix |
| CA | Sheep Fescue | Microclover Lawn Mix | Buffalo Grass |
| TX | Buffalo Grass | Sideoats Grama | TX/OK Wildflower Mix |
| CO / UT / NM | Blue Grama | Sheep Fescue | Buffalo Grass |

Product descriptions (1 line each):

- **Bermudagrass Drought-Tolerant Blend:** Heat and drought resistant. Thrives in desert climates with minimal irrigation.
- **Buffalo Grass:** Native short grass. Deep roots, no irrigation after establishment. Widely adapted.
- **Southwestern Wildflower Mix:** Drought-adapted color and pollinator habitat. Zero irrigation after establishment.
- **Sheep Fescue:** Low-water, low-mow fescue. Ideal for California coastal and transitional climates.
- **Microclover Lawn Mix:** Self-fertilizing and drought tolerant. Works as a full lawn replacement or mixed cover.
- **Sideoats Grama:** Texas state grass. Native, drought-hardy, extremely low maintenance.
- **TX/OK Wildflower Mix:** Bluebonnets and Texas natives. Adds color while qualifying as drought-tolerant ground cover.
- **Blue Grama:** New Mexico's state grass. Cold-hardy, drought-tolerant, thrives in alkaline western soils.

### Section 5 — Suggested Resources (static)

A simple text section with 2–3 article links. URLs are placeholders until articles are published — use `/xeriscaping/` as base for now.

```
Further reading:
• What is xeriscaping? → https://www.naturesseed.com/resources/lawn-and-turf/what-is-xeriscaping/
• Buffalo grass: the low-water native lawn → https://www.naturesseed.com/resources/lawn-and-turf/buffalo-grass-lawn/
• Xeriscape seed vs. sod: the real cost comparison → https://www.naturesseed.com/resources/lawn-and-turf/xeriscape-seed-vs-sod/
```

### Section 6 — USP Bar (standard)

`#2d6a4f` background, 4 columns: American Farm-Direct / No GMOs / Ships in 1 Business Day / Satisfaction Guaranteed

### Section 7 — Footer

`<mj-include path="../components/footer.mjml" />`

---

## Klaviyo Conventions

- All MCP calls: `model: "claude"`
- API revision: `2024-07-15`
- CTA buttons: `#C96A2E` — never green
- State conditionals: `{% if person|lookup:'$region' == 'NV' %}` inside `mj-text` only
- Never wrap `mj-section` or `mj-column` in `{% if %}` tags

---

## Validation Plan

After building Email 1:
1. Compile MJML → verify all 7 build `[OK]` under 90KB
2. Grep compiled HTML for `person|lookup` — count must be > 0 (Klaviyo tags intact, not URL-encoded)
3. Create one test campaign in Klaviyo (NV), send preview to internal email
4. Verify NV state block renders, NV product grid shows, `$region` resolves to "NV" in subject line
5. If validation passes → build remaining 6 campaigns and schedule
