# Reddit Ads — Launch Plan (Nature's Seed, DTC/retail)

Scope: naturesseed.com B2C retail only. Never target B2B / municipal / conservation-district / tribal-land personas (separate NSG team owns those).

Account `t2_2d9xohhgkr` · Pixel via GTM `GTM-K8CP73` · Catalog feed live (263 variations).

---

## Phase 0 — clear before any spend
1. **Billing** — add a payment method in Reddit Ads Manager. Hard gate.
2. **Pixel validation** — run `pixel-validation-checklist.md`. Confirm `Purchase` fires with `value` + `currency`. Without this you cannot optimize for or measure revenue.
3. **Catalog ingest** — Ads Manager → Catalog → Create Catalog → Scheduled feed → point at
   `https://gabenaturesseed.github.io/nature-seed-data/reddit-catalog/reddit_catalog.tsv`
   (needed for Dynamic Product Ads only).
4. **Click-ID auto-tagging** — turn ON in Ads Manager so Reddit appends `rdt_cid` to landing URLs. That's how WooCommerce order attribution (and our CAPI sender) recover the Reddit click for revenue attribution. Also add `utm_source=reddit&utm_medium=cpc` to destination URLs as a backup signal.

## Phase 1 — Prospecting (weeks 1–2)
- **Objective:** Conversions. Optimize for **Add to Cart** first (more volume trains the pixel faster than optimizing for Purchase on a cold account). Switch to Purchase once ~50 conversions/week.
  - If pixel Purchase isn't validated yet, run **Traffic** to the 3-Minute Quiz landing page instead, and switch to Conversions the day the pixel is confirmed. Don't run Conversions on an unproven pixel.
- **Budget:** $50–75/day. First-month test ≈ $1.5–2k.
- **Placements:** Feed + Conversation. Auto-bid to start.
- **Targeting** — Community (subreddit) + Interest, split into ad groups by product line so creative matches the room:

| Ad group | Subreddits (community targeting) | Interests |
|---|---|---|
| Lawn / lawn alternatives | r/lawncare, r/landscaping, r/NoLawns, r/fuckinglawns, r/DIY, r/HomeImprovement | Home & Garden, DIY |
| Xeriscape / drought | r/Xeriscape, r/DesertGardening, r/drought + geo-target dry states (AZ, NV, NM, CA, CO, TX, UT) | Gardening, Sustainability |
| Pollinator / wildflower / native | r/NativePlants, r/NativePlantGardening, r/pollinators, r/gardening, r/beekeeping | Gardening, Environment |
| Homestead / pasture / forage | r/homestead, r/homesteading, r/BackYardChickens, r/ranching, r/goats, r/sheep | Agriculture, Pets/Livestock |
| Food plot / hunting | r/foodplots, r/deerhunting, r/Hunting, r/bowhunting | Hunting, Outdoors |

## Phase 2 — Scale + retarget (weeks 3–4)
- Keep winning Phase-1 ad groups; cut anything under target CPA after ≥1k impressions.
- Add a **Dynamic Product Ads** campaign (needs catalog ingested) retargeting **ViewContent + AddToCart non-purchasers** — Reddit auto-builds product carousels from the feed.
- Scale total to $100–150/day split prospecting/retargeting once ROAS is positive.

---

## Creative — 4 concepts (Reddit rewards native, helpful, non-hype copy — which is on-brand)

**A. Lawn alternatives** → r/NoLawns, r/fuckinglawns, r/lawncare
- Headline: *Replace your thirsty lawn with something that actually thrives.*
- Body: Buffalograss and microclover blends, expertly matched to your region — less water, less mowing. Seed you can trust: no fillers, no GMOs, guaranteed to grow.
- CTA: **Take the 3-Minute Lawn Quiz** · Image: lush low-water/clover lawn (not a seed bag)

**B. Xeriscape / drought states** → r/Xeriscape, r/DesertGardening
- Headline: *A beautiful yard that sips water, not guzzles it.*
- Body: Drought-tolerant grass and wildflower seed, blended for your climate by our seed scientists. Regionally tested. Guaranteed to grow.
- CTA: **Find Your Regional Mix** · Image: xeriscape yard in bloom

**C. Pollinator / wildflower** → r/NativePlants, r/pollinators, r/gardening
- Headline: *Turn that empty patch into a pollinator paradise.*
- Body: Regionally tailored wildflower blends — no fillers, independently tested for high germination. Sustainably grown on our own U.S. farms.
- CTA: **Shop Wildflower Seed** · Image: wildflower meadow with bees/butterflies

**D. Homestead / pasture / food plot** → r/homestead, r/foodplots, r/BackYardChickens
- Headline: *Healthy pastures start with seed you can trust.*
- Body: Farm-direct pasture, forage, and food-plot seed — expert-blended for your region and livestock. Ships within one business day.
- CTA: **Ask a Seed Expert** · Image: green pasture with livestock / thriving food plot

Creative notes: lead with the outcome image, not the bag. 1–2 sentences. No urgency tricks or ALL CAPS (Redditors punish ad-speak; brand voice already forbids it). Run 2–3 creatives per ad group and let Reddit rotate.

---

## Measurement
- **Source of truth = WooCommerce revenue** (data-hub rule). Judge Reddit against WC orders attributed via `rdt_cid` in order attribution, not Reddit's self-reported conversions alone — cross-check the two to catch over-reporting.
- **KPIs:** ROAS (primary), CPA, CTR (Reddit feed avg ~0.3–0.5%), CPC (~$0.50–4.00).
- **Target CPA:** set from current WC AOV. If target ROAS = 3×, max CPA = AOV ÷ 3. Pull AOV from `pull_wc_sales.py`.
- Reddit's learning phase needs volume — starving it at ~$15/day means it never learns. Fund $50+/day or don't start.
