# Regenerative Agriculture Hub — Design Spec
**Date:** 2026-04-30
**Sub-project:** 1 of 3 (Category page + WC structure + product mapping)
**Status:** Draft — pending user review

---

## 1. Overview

An editorial landing page that teaches motivated homesteaders (5–50 acres, mixed livestock) what regenerative agriculture means *for their land*, then equips them with the right products. Educate first, sell second.

**Primary persona:** Motivated homesteader — already doing some regen practices, wants to go deeper. Speaks the language (soil health, rotational grazing, cover crops). Doesn't need basic definitions, needs practical implementation.

---

## 2. URLs & WordPress Structure

| Layer | Value |
|---|---|
| Page URL | `/products/regenerative-agriculture/` |
| WordPress page template | `page-regenerative-agriculture.php` |
| WC product category name | Regenerative Agriculture |
| WC category slug | `regenerative-ag` |
| Permalink Manager override | `/products/regenerative-agriculture/` on WC category |
| Nav visibility | Hidden from main nav until approved |
| SCSS file | `assets/scss/pages/_regenerative-agriculture.scss` |

The WordPress page at `/products/regenerative-agriculture/` uses the custom template. The WC category exists in the background for product assignment and individual PDP breadcrumbs.

---

## 3. Page Sections (Top to Bottom)

### 3.1 Hero
- **Headline:** Farming With Nature, Not Against It
- **Subhead:** Practical seeds and soil tools for smaller-scale ranchers and farmers building healthier land — one season at a time.
- **Body (2 sentences):** Regenerative agriculture isn't a certification or a philosophy seminar. It's a set of practices that improve your land, reduce your input costs, and build something worth passing on.
- **CTA:** "Find your starting point →" — smooth scrolls to challenge selector
- **BEM block:** `.regen-hero`

### 3.2 Challenge Selector
Five pill buttons in a horizontal row. Each anchors to its outcome section. On mobile: 2-column grid.

| Button Label | Anchor |
|---|---|
| My soil is tired and compacted | `#build-soil` |
| I'm spending too much on inputs | `#reduce-inputs` |
| My pastures aren't feeding my animals | `#feed-livestock` |
| I want to support pollinators | `#support-pollinators` |
| I want to capture carbon | `#sequester-carbon` |

**BEM block:** `.regen-challenge-selector`
No JS required — pure CSS anchor links with `scroll-behavior: smooth` on `html`.

### 3.3 Outcome Sections (×5)
Each section follows identical template:

```
[Icon] [Outcome Headline]
[2–3 sentence explainer — practical, small-farm lens]
[3 featured product cards]
[See all products for this outcome →] (anchor to #all-products, filtered by outcome)
```

**BEM block:** `.regen-outcome` with modifier `.regen-outcome--[slug]`
**Product cards:** Use existing WoodMart/theme product card shortcode or manual HTML matching site card style.

#### Build Soil (`#build-soil`)
> Compacted, depleted soil is the root cause of most pasture and crop problems. Cover crops, nitrogen-fixing legumes, and mycorrhizal inoculants restore what decades of conventional management removed — without tillage.

Featured products:
1. S-INNOC — Am 120 Mycorrhizal Inoculant
2. BDL-SBC — Soil Builder Cover Crop Kit
3. PG-TRIN — Crimson Clover

Full set also includes: S-DUTCH, PB-MUST, PG-BUCK, PG-SECE, SUSTANE-4-6-4, PG-TRRE

#### Reduce Inputs (`#reduce-inputs`)
> Every bag of synthetic fertilizer, every herbicide pass, every irrigation cycle is a cost you can reduce. The right plants — clovers, deep-rooted grasses, weed-smothering cover crops — do the work for free once established.

Featured products:
1. BDL-WSC — Weed Smother Cover Crop Kit
2. S-MICRO — Micro Clover
3. SUSTANE-18-1-8+FE — Organic Maintenance Fertilizer

Full set also includes: PG-BUDA, PG-BOGR, PG-PAVI, TURF-CLV

#### Feed Livestock Better (`#feed-livestock`)
> A diverse pasture — grasses, legumes, forbs — produces more nutrition per acre than a monoculture stand and reduces supplemental feed costs. Rotation keeps it productive instead of overgrazed.

Featured products:
1. BDL-TPF — Thin Pasture Fix Kit
2. PG-MESA — Alfalfa
3. PG-TRPR — Red Clover

Full set also includes: PB-COW-NTR, PB-COW-SO, PB-HRSE-N/SO/TR, PB-SHEP-N/SO/TR, PB-GOAT-TR, PG-DAGL

#### Support Pollinators (`#support-pollinators`)
> Healthy pollinator populations signal a functioning ecosystem — and benefit every neighboring farm. Clover and diverse forage mixes are the lowest-effort, highest-impact starting point.

Featured products:
1. PB-HONEY — Honey Bee Cover Crop & Pasture Mix
2. BDL-POL — Pollinator Corridor Kit
3. S-DUTCH — White Dutch Clover

Full set also includes: PG-TRIN, WB-AN, WB-RM, WB-SD, PG-TRRE

#### Sequester Carbon (`#sequester-carbon`)
> Deep-rooted perennial grasses are among the most effective carbon sinks on land. Restoring native prairie species builds soil organic matter that compounds over years — and increasingly qualifies for carbon credit programs.

Featured products:
1. PG-PAVI — Switchgrass
2. PB-SGPR — Shortgrass Prairie Mix
3. CV-BGEC — Prairie Native Drought-Tolerant & Erosion Control

Full set also includes: PG-BUDA, PG-BOGR, PB-PLPR, PG-MESA, PB-TXPR

### 3.4 Full Product Grid (`#all-products`)
All regen ag products in a standard product grid. Filter tabs across the top:
`All | Build Soil | Reduce Inputs | Feed Livestock | Support Pollinators | Sequester Carbon`

Implemented via WooCommerce `[products]` shortcode filtered by category tag, or PHP WC_Product_Query. Tab filtering via lightweight JS (show/hide by data attribute — no page reload).

**BEM block:** `.regen-product-grid`

### 3.5 Learn More — Blog Cards (`#learn-more`)
Three pillar rows. Each row has a colored label + 4 article cards in a responsive grid (4-col desktop, 2-col tablet, 1-col mobile).

| Pillar | Badge Color | Articles |
|---|---|---|
| Foundations | `#8B6914` (earthy brown) | 4 |
| Practical How-To | `#2D5A27` (forest green) | 4 |
| Niche Deep Dives | `#3D5A73` (slate blue) | 4 |

**Article card anatomy:**
```
[Pillar badge — top left]
[Article title — 2 lines max]
[1-line teaser]
[Read time — e.g. "6 min read"]
[Read article →]
```

**BEM block:** `.regen-article-card`

Articles (stub titles — full content is Sub-project 3):

**Foundations:**
1. What Is Regenerative Agriculture? A Plain-English Guide
2. The 5 Principles of Soil Health
3. What Your Soil Test Actually Tells You
4. Cover Crops 101: How to Pick Your First Mix

**Practical How-To:**
1. Frost Seeding Clover Into an Existing Pasture
2. Renovating a Tired Hobby Farm Pasture in One Season
3. Stockpile Grazing: How to Save on Hay
4. Why Mycorrhizae Matter for Pasture Establishment

**Niche Deep Dives:**
1. Silvopasture: Forage Under Trees Without Killing Either
2. Pollinator Forage for Beekeepers With Acreage
3. Carbon Capture on a Small Farm: What's Real, What's Hype
4. Multi-Species Cover Crop Mixes Explained

### 3.6 Footer CTA
- **Headline:** Not sure where to start?
- **Body:** Most small operations see the biggest return from improving soil biology first. A cover crop mix and a mycorrhizal inoculant — two products, one season, measurable difference.
- **CTA button:** "Shop Cover Crops & Soil Builders →" → anchors to `#build-soil`
- **BEM block:** `.regen-footer-cta`

---

## 4. WC Category Structure

Create via API before or alongside page build. All hidden from shop nav.

```
Regenerative Agriculture (slug: regenerative-ag)
├── Build Soil (slug: regen-build-soil)
├── Reduce Inputs (slug: regen-reduce-inputs)
├── Feed Livestock Better (slug: regen-feed-livestock)
├── Support Pollinators (slug: regen-support-pollinators)
└── Sequester Carbon (slug: regen-sequester-carbon)
```

Products assigned per the mapping in Section 3.3. Products can belong to multiple sub-categories (e.g., S-DUTCH appears in both Build Soil and Support Pollinators).

---

## 5. SCSS Architecture

```
assets/scss/pages/_regenerative-agriculture.scss
  .regen-hero
  .regen-challenge-selector
    .regen-challenge-selector__pills
    .regen-challenge-selector__pill (+ :hover, .is-active)
  .regen-outcome
    .regen-outcome__header
    .regen-outcome__explainer
    .regen-outcome__products
    .regen-outcome__cta
  .regen-product-grid
    .regen-product-grid__filters
    .regen-product-grid__filter-tab (+ .is-active)
    .regen-product-grid__grid
  .regen-article-card
    .regen-article-card__badge
    .regen-article-card__title
    .regen-article-card__teaser
    .regen-article-card__meta
    .regen-article-card__link
  .regen-footer-cta
```

Color tokens to use from existing theme variables where possible. New tokens only for pillar badge colors.

---

## 6. Implementation Order

1. Create WC categories + subcategories via API script
2. Assign existing products to subcategories via API
3. Set Permalink Manager URL to `/products/regenerative-agriculture/`
4. Build `page-regenerative-agriculture.php` template
5. Build `_regenerative-agriculture.scss` + run Vite build
6. Wire up challenge selector anchor links
7. Wire up product grid tab filter (JS)
8. Stub article cards with placeholder links (articles written in Sub-project 3)
9. QA on desktop + mobile
10. Share preview link for approval before adding to nav

---

## 7. Out of Scope (This Sub-project)

- Writing the 12 blog articles (Sub-project 3)
- New product SKUs / bundles (Sub-project 2)
- Adding the hub to site navigation
- Carbon credit program partnerships or external links
