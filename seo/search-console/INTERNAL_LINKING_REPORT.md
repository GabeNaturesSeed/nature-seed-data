# Nature's Seed — Internal Linking & Cannibalization Report

*Generated: 2026-03-09 16:36*
*Data period: 2026-02-05 to 2026-03-06 (30 days)*

---
## 1. Executive Summary

### 30-Day Organic Traffic Overview

| Metric | Current 30d | Previous 30d | Change |
|--------|------------|-------------|--------|
| Clicks | 10,689 | 5,442 | +96.4% |
| Impressions | 1,714,892 | 1,030,653 | +66.4% |
| CTR | 0.62% | 0.53% | — |
| Avg Position | 7.6 | 10.6 | -3.0 |

### Key Findings

- **4,050 cannibalized queries** — multiple pages competing for the same keyword
- **752 unique pages** indexed across 14,794 unique queries
- **172 fragment URLs** (anchor links like `#section`) being indexed as separate pages — this is a major crawl-budget and cannibalization issue
- **294 variation/parameter URLs** (product variations with `?variation_id=`) indexed separately
- **499 quick-win opportunities** (positions 5-15, high impressions)
- **807 striking-distance queries** (positions 8-20)
- **12.6% branded traffic** — the rest is non-branded organic

> **Estimated wasted impressions on fragment URLs: 228,491** — these should all be consolidated to base URLs via canonical tags.

---
## 2. Product Catalog vs. Search Demand Mismatch

Analyzed the top 100 queries by impressions against the 112 published WooCommerce products.

### 2a. "We Carry This — Optimize" (Query matches a product we sell)

**38 queries** match products in the catalog.

| # | Query | Impressions | Clicks | CTR | Best Matching Product | Product URL |
|---|-------|------------|--------|-----|----------------------|-------------|
| 1 | grass seed | 41,109 | 107 | 0.26% | Native Cabin Grass Seed Mix | https://naturesseed.com/products/pasture-seed/native-cabin-grass-mix/ |
| 2 | clover seeds for lawn | 4,557 | 14 | 0.31% | Clover Lawn Alternative Mix | https://naturesseed.com/products/grass-seed/clover-lawn-alternative-mix/ |
| 3 | fescue grass seed | 4,146 | 4 | 0.10% | Pet & Kid Friendly Low-Maintenance Fescue Lawn Bundle | https://naturesseed.com/product/bundle/pet-kid-friendly-fescue-lawn-bundle/ |
| 4 | bermuda grass seed | 3,430 | 9 | 0.26% | Bermuda Grass Seed Mix for Lawns | https://naturesseed.com/products/grass-seed/bermudagrass-seed-blend/ |
| 5 | kentucky bluegrass seed | 2,778 | 11 | 0.40% | Kentucky Bluegrass | https://naturesseed.com/products/pasture-seed/kentucky-bluegrass/ |
| 6 | kentucky bluegrass | 2,711 | 30 | 1.11% | Kentucky Bluegrass | https://naturesseed.com/products/pasture-seed/kentucky-bluegrass/ |
| 7 | perennial ryegrass | 2,703 | 15 | 0.55% | Perennial Ryegrass | https://naturesseed.com/products/pasture-seed/perennial-ryegrass/ |
| 8 | fescue grass | 2,644 | 24 | 0.91% | Pet & Kid Friendly Low-Maintenance Fescue Lawn Bundle | https://naturesseed.com/product/bundle/pet-kid-friendly-fescue-lawn-bundle/ |
| 9 | fine fescue grass seed | 2,289 | 9 | 0.39% | Fine Fescue Grass Seed Mix | https://naturesseed.com/products/grass-seed/fine-fescue-grass-seed-mix/ |
| 10 | clover seed | 2,086 | 6 | 0.29% | Pasture Clover Mix for Waterfowl Food Plots | https://naturesseed.com/products/pasture-seed/pasture-clover-mix-for-duck-quail-food-plot/ |
| 11 | clover seeds | 2,065 | 0 | 0.00% | Pasture Clover Mix for Waterfowl Food Plots | https://naturesseed.com/products/pasture-seed/pasture-clover-mix-for-duck-quail-food-plot/ |
| 12 | ryegrass | 1,970 | 10 | 0.51% | Perennial Ryegrass | https://naturesseed.com/products/pasture-seed/perennial-ryegrass/ |
| 13 | rye grass | 1,779 | 12 | 0.67% | Winter (Cereal) Rye Seed | https://naturesseed.com/products/pasture-seed/cereal-rye/ |
| 14 | lawn seed | 1,670 | 4 | 0.24% | Texas Native Lawn Mix | https://naturesseed.com/products/grass-seed/texas-native-lawn-mix/ |
| 15 | best grass seed for texas | 1,510 | 2 | 0.13% | Texas Bluebonnet Seeds | https://naturesseed.com/products/wildflower-seed/texas-bluebonnet-seeds/ |
| 16 | high traffic grass seed | 1,498 | 2 | 0.13% | Hardy Grass Seed Mix for High Traffic Lawns | https://naturesseed.com/products/grass-seed/high-traffic-hardy-lawn/ |
| 17 | clover lawn | 1,346 | 2 | 0.15% | Clover Lawn Alternative Mix | https://naturesseed.com/products/grass-seed/clover-lawn-alternative-mix/ |
| 18 | ryegrass seed | 1,144 | 1 | 0.09% | Perennial Ryegrass | https://naturesseed.com/products/pasture-seed/perennial-ryegrass/ |
| 19 | perennial ryegrass seed | 1,140 | 3 | 0.26% | Perennial Ryegrass | https://naturesseed.com/products/pasture-seed/perennial-ryegrass/ |
| 20 | fescue | 1,083 | 3 | 0.28% | Pet & Kid Friendly Low-Maintenance Fescue Lawn Bundle | https://naturesseed.com/product/bundle/pet-kid-friendly-fescue-lawn-bundle/ |
| 21 | clover grass | 997 | 0 | 0.00% | Pasture Clover Mix for Waterfowl Food Plots | https://naturesseed.com/products/pasture-seed/pasture-clover-mix-for-duck-quail-food-plot/ |
| 22 | grass fertilizer | 865 | 0 | 0.00% | Organic Seed Starter Fertilizer 4-6-4 | https://naturesseed.com/products/planting-aids/organic-seed-starter-fertilizer-4-6-4/ |
| 23 | hay grass | 857 | 1 | 0.12% | Timothy Grass Hay Seed | https://naturesseed.com/products/pasture-seed/timothy/ |
| 24 | blue grass seed | 815 | 2 | 0.25% | Blue-Eyed Grass Seed | https://naturesseed.com/products/wildflower-seed/blue-eyed-grass/ |
| 25 | pasture seed | 801 | 6 | 0.75% | Thin Pasture Fix Kit | https://naturesseed.com/products/pasture-seed/thin-pasture-kit/ |
| 26 | sheep fescue | 797 | 43 | 5.40% | Sheep Fescue Grass Seed | https://naturesseed.com/products/grass-seed/sheep-fescue-grass/ |
| 27 | pasture grass seed | 792 | 7 | 0.88% | Thin Pasture Fix Kit | https://naturesseed.com/products/pasture-seed/thin-pasture-kit/ |
| 28 | clover grass seed | 764 | 1 | 0.13% | Pasture Clover Mix for Waterfowl Food Plots | https://naturesseed.com/products/pasture-seed/pasture-clover-mix-for-duck-quail-food-plot/ |
| 29 | clover lawn seed | 731 | 2 | 0.27% | Clover Lawn Alternative Mix | https://naturesseed.com/products/grass-seed/clover-lawn-alternative-mix/ |
| 30 | best grass seed for shade | 713 | 4 | 0.56% | Shade Tolerant Food Plot Mix | https://naturesseed.com/products/pasture-seed/shade-mix-food-plot/ |
| 31 | switchgrass seed | 685 | 1 | 0.15% | Switchgrass (Panicum Virgatum) Seed | https://naturesseed.com/products/pasture-seed/switchgrass-seed/ |
| 32 | grass hay | 682 | 1 | 0.15% | Timothy Grass Hay Seed | https://naturesseed.com/products/pasture-seed/timothy/ |
| 33 | micro clover | 669 | 6 | 0.90% | Micro Clover Seed (Mini Clover) | https://naturesseed.com/products/clover-seed/microclover/ |
| 34 | bluegrass seed | 666 | 1 | 0.15% | Premium Pet & Kid Friendly Bluegrass Bundle | https://naturesseed.com/product/premium-pet-kid-friendly-bluegrass-bundle/ |
| 35 | tall fescue grass seed | 649 | 1 | 0.15% | Tall Fescue Grass Seed | https://naturesseed.com/products/pasture-seed/tall-fescue/ |
| 36 | fertilizer for grass | 628 | 0 | 0.00% | Organic Seed Starter Fertilizer 4-6-4 | https://naturesseed.com/products/planting-aids/organic-seed-starter-fertilizer-4-6-4/ |
| 37 | goat pasture seed mix | 613 | 21 | 3.43% | Goat Pasture & Forage Mix | https://naturesseed.com/products/pasture-seed/goat-pasture-forage-mix-transitional/ |
| 38 | switchgrass | 600 | 1 | 0.17% | Switchgrass (Panicum Virgatum) Seed | https://naturesseed.com/products/pasture-seed/switchgrass-seed/ |

### 2b. "We Don't Carry This — Deprioritize or Redirect" (No matching product)

**58 queries** from the top 100 have NO matching product in the catalog. These drive impressions but may attract the wrong audience.

| # | Query | Impressions | Clicks | Top Ranking Page | Recommendation |
|---|-------|------------|--------|-----------------|----------------|
| 1 | st augustine grass seed | 5,072 | 11 | `/resources/lawn-turf/how-to-plant-and-grow-st-augustine-grass-seed/` | We don't sell this species — consider adding or redirecting |
| 2 | best grass seed for washington state | 4,691 | 0 | `/grass-seed/washington/` | State guide — add internal links to relevant product pages |
| 3 | best grass seed for florida | 4,483 | 14 | `/resources/lawn-turf/florida/` | State guide — add internal links to relevant product pages |
| 4 | best grass seed | 4,320 | 30 | `/products/grass-seed/` | Resource page — OK for SEO authority |
| 5 | reel mower | 3,409 | 2 | `/resources/lawn-turf/an-oldie-but-a-goodie-advantages-of-reel-mowers/` | Resource page — OK for SEO authority |
| 6 | best grass seed for florida sandy soil | 3,130 | 8 | `/resources/lawn-turf/florida/` | State guide — add internal links to relevant product pages |
| 7 | brittlebush | 3,066 | 1 | `/products/wildflower-seed/brittlebush/` | Resource page — OK for SEO authority |
| 8 | what eats grass | 3,059 | 3 | `/resources/agriculture/unexpected-grazers-5-animals-you-didn-t-know-were-grass-eaters/` | Resource page — OK for SEO authority |
| 9 | best grass seed for michigan | 2,945 | 3 | `/resources/lawn-turf/michigan/` | State guide — add internal links to relevant product pages |
| 10 | grass seed for florida | 2,478 | 9 | `/resources/lawn-turf/florida/` | Resource page — OK for SEO authority |
| 11 | best grass seed for montana | 2,425 | 2 | `/resources/lawn-turf/montana/` | Resource page — OK for SEO authority |
| 12 | what animals eat grass | 2,270 | 3 | `/resources/agriculture/unexpected-grazers-5-animals-you-didn-t-know-were-grass-eaters/` | Resource page — OK for SEO authority |
| 13 | grass seeds | 2,206 | 7 | `/products/grass-seed/` | Resource page — OK for SEO authority |
| 14 | best grass seed for indiana | 1,993 | 8 | `/resources/lawn-turf/indiana/` | State guide — add internal links to relevant product pages |
| 15 | best grass seed for eastern washington | 1,759 | 0 | `/grass-seed/washington/` | State guide — add internal links to relevant product pages |
| 16 | best grass seed for south florida | 1,755 | 5 | `/resources/lawn-turf/florida/` | State guide — add internal links to relevant product pages |
| 17 | florida grass seed | 1,646 | 4 | `/resources/lawn-turf/florida/` | Resource page — OK for SEO authority |
| 18 | sainfoin | 1,623 | 16 | `/resources/agriculture/ancient-crop-new-interest-sainfoin-for-forage-hay-and-honey/` | Resource page — OK for SEO authority |
| 19 | best grass seed for north florida | 1,610 | 5 | `/grass-seed/florida/` | State guide — add internal links to relevant product pages |
| 20 | best grass seed for ohio | 1,403 | 7 | `/resources/lawn-turf/ohio/` | State guide — add internal links to relevant product pages |
| 21 | seed paper | 1,395 | 12 | `/resources/news-and-misc/how-to-make-plantable-seed-paper/` | DIY/informational — drives traffic, not sales. OK to keep |
| 22 | do deer eat wildflowers | 1,379 | 5 | `/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/` | Resource page — OK for SEO authority |
| 23 | best fertilizer for bermuda grass | 1,309 | 0 | `/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/` | Resource page — OK for SEO authority |
| 24 | animals that eat grass | 1,293 | 1 | `/resources/agriculture/unexpected-grazers-5-animals-you-didn-t-know-were-grass-eaters/` | Resource page — OK for SEO authority |
| 25 | how long does grass seed take to grow | 1,249 | 1 | `/resources/lawn-turf/how-long-does-it-take-grass-to-grow/` | Resource page — OK for SEO authority |
| 26 | grass seed florida | 1,240 | 3 | `/resources/lawn-turf/florida/` | Resource page — OK for SEO authority |
| 27 | buffalo grass seed | 1,238 | 18 | `/products/pasture-seed/buffalograss/` | Resource page — OK for SEO authority |
| 28 | best grass seed for oregon coast | 1,138 | 1 | `/resources/best-grass-seed-for-the-pacific-northwest-2026/` | State guide — add internal links to relevant product pages |
| 29 | switch grass | 1,104 | 5 | `/resources/wildlife-habitat-sustainability/switchgrass-a-grass-of-many-uses/` | Resource page — OK for SEO authority |
| 30 | how long does it take for grass seed to grow | 1,104 | 1 | `/resources/lawn-turf/how-long-does-it-take-grass-to-grow/` | Resource page — OK for SEO authority |
| 31 | plantable seed paper | 1,059 | 16 | `/resources/news-and-misc/how-to-make-plantable-seed-paper/` | DIY/informational — drives traffic, not sales. OK to keep |
| 32 | does vinegar kill grass | 1,052 | 5 | `/resources/wildlife-habitat-sustainability/using-vinegar-to-kill-weeds-in-the-lawn-and-garden/` | Resource page — OK for SEO authority |
| 33 | will vinegar kill grass | 1,044 | 8 | `/resources/wildlife-habitat-sustainability/using-vinegar-to-kill-weeds-in-the-lawn-and-garden/` | Resource page — OK for SEO authority |
| 34 | buffalo grass | 1,037 | 9 | `/resources/lawn-turf/an-introduction-to-buffalograss/` | Resource page — OK for SEO authority |
| 35 | brittle bush | 980 | 1 | `/products/wildflower-seed/brittlebush/` | Resource page — OK for SEO authority |
| 36 | how to make seed paper | 923 | 70 | `/resources/news-and-misc/how-to-make-plantable-seed-paper/` | DIY/informational — drives traffic, not sales. OK to keep |
| 37 | best grass seed for sandy soil | 920 | 1 | `/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/` | Resource page — OK for SEO authority |
| 38 | best grass seed for shaded areas | 876 | 4 | `/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/` | Resource page — OK for SEO authority |
| 39 | best grass seed for southwest florida | 855 | 2 | `/resources/lawn-turf/florida/` | State guide — add internal links to relevant product pages |
| 40 | best grass seed for florida lawns | 810 | 3 | `/grass-seed/florida/` | State guide — add internal links to relevant product pages |
| 41 | best grass seed for western washington | 799 | 7 | `/grass-seed/washington/` | State guide — add internal links to relevant product pages |
| 42 | best grass for florida shade | 797 | 0 | `/grass-seed/florida/` | State guide — add internal links to relevant product pages |
| 43 | is dog poop good for grass | 787 | 2 | `/resources/lawn-turf/how-to-grow-grass-with-dogs/` | Resource page — OK for SEO authority |
| 44 | best type of grass for florida | 782 | 0 | `/resources/lawn-turf/florida/` | State guide — add internal links to relevant product pages |
| 45 | clover seed for lawns | 759 | 6 | `/products/clover-seed/` | Resource page — OK for SEO authority |
| 46 | what animal eats grass | 755 | 1 | `/resources/agriculture/unexpected-grazers-5-animals-you-didn-t-know-were-grass-eaters/` | Resource page — OK for SEO authority |
| 47 | purple needle grass | 723 | 5 | `/products/wildflower-seed/purple-needlegrass/` | Resource page — OK for SEO authority |
| 48 | bermuda grass fertilizer | 714 | 0 | `/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/` | Resource page — OK for SEO authority |
| 49 | globemallow | 713 | 1 | `/resources/wildlife-habitat-sustainability/globemallow-wildflowers-tough-as-nails-pretty-too/` | Resource page — OK for SEO authority |
| 50 | encelia farinosa | 704 | 2 | `/products/wildflower-seed/brittlebush/` | Resource page — OK for SEO authority |

### 2c. Branded Queries (4 queries)

These are navigational — users searching for Nature's Seed by name. No action needed.

---
## 3. Cannibalization Analysis — Top 40 Queries

These queries have **multiple pages competing** for the same keyword, diluting click-through and confusing Google about which page to rank.

### 3.1. "grass seed"
**Total impressions:** 41,109 | **Total clicks:** 107 | **Pages competing:** 70

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/grass-seed/` | product | 101 | 25,334 | 0.40% | 6.2 |
| `/products/grass-seed/twca-water-wise-sun-shade-mix/` | product | 0 | 6,945 | 0.00% | 1.0 |
| `/` | homepage | 6 | 5,212 | 0.12% | 12.8 |
| `/resources/lawn-turf/how-long-does-it-take-grass-to-grow/` | resource | 0 | 2,749 | 0.00% | 1.0 |
| `/resources/lawn-turf/common-mistakes-made-when-establishing-a-lawn-from-seed/` | resource | 0 | 269 | 0.00% | 1.2 |
| `/resources/lawn-turf/how-to-choose-the-right-grass-seed/` | resource | 0 | 107 | 0.00% | 2.4 |
| `/resources/lawn-turf/best-grass-seed-for-your-climate/` | resource | 0 | 105 | 0.00% | 1.2 |
| `/products/grass-seed/twca-water-wise-shade-mix/` | product | 0 | 69 | 0.00% | 1.0 |
| `/products/pasture-seed/goat-pasture-forage-mix-transitional/` | product | 0 | 46 | 0.00% | 1.0 |
| `/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/` | resource | 0 | 36 | 0.00% | 1.1 |
| *... +60 more pages* | — | — | 237 | — | — |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 1 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.2. "best grass seed for washington state"
**Total impressions:** 4,691 | **Total clicks:** 0 | **Pages competing:** 12

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/grass-seed/washington/` | state-landing | 0 | 1,465 | 0.00% | 1.9 |
| `/resources/lawn-turf/washington/` | resource | 0 | 740 | 0.00% | 1.0 |
| `/grass-seed/washington/#growing-climate` (FRAGMENT) | state-landing | 0 | 673 | 0.00% | 2.7 |
| `/grass-seed/washington/#kentucky-bluegrass` (FRAGMENT) | state-landing | 0 | 670 | 0.00% | 2.7 |
| `/grass-seed/washington/#fine-fescue` (FRAGMENT) | state-landing | 0 | 641 | 0.00% | 2.5 |
| `/resources/lawn-turf/washington/#growing-climate` (FRAGMENT) | resource | 0 | 182 | 0.00% | 3.1 |
| `/resources/lawn-turf/washington/#kentucky-bluegrass` (FRAGMENT) | resource | 0 | 182 | 0.00% | 3.1 |
| `/grass-seed/washington/#perennial-ryegrass` (FRAGMENT) | state-landing | 0 | 80 | 0.00% | 3.8 |
| `/resources/best-grass-seed-for-the-pacific-northwest-2026/` | resource | 0 | 22 | 0.00% | 14.1 |
| `/resources/lawn-turf/washington/#fine-fescue` (FRAGMENT) | resource | 0 | 18 | 0.00% | 4.1 |
| *... +2 more pages* | — | — | 18 | — | — |

**Recommended canonical:** `/grass-seed/washington/`
**Reason:** Highest impression page — consolidate others via canonical tags or 301 redirects.
**Warning:** 8 fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.

### 3.3. "clover seeds for lawn"
**Total impressions:** 4,557 | **Total clicks:** 14 | **Pages competing:** 12

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/clover-seed/` | product | 14 | 2,905 | 0.48% | 2.4 |
| `/products/clover-seed/white-dutch-clover/` | product | 0 | 1,473 | 0.00% | 1.5 |
| `/resources/lawn-turf/clover-seed-planting-instructions/` | resource | 0 | 152 | 0.00% | 1.7 |
| `/clover-seed-planting-instructions/` | other | 0 | 11 | 0.00% | 1.4 |
| `/products/clover-seed/microclover/` | product | 0 | 7 | 0.00% | 60.3 |
| `/products/clover-seed/white-clover/` | product | 0 | 2 | 0.00% | 1.0 |
| `/products/clover-seed/white-dutch-clover/?variation_id=447282&attribute_size=5+lb+-+Covers+10%2C000+Sq+Ft` (VARIATION) | product | 0 | 2 | 0.00% | 2.5 |
| `/products/clover-seed/white-dutch-clover/?variation_id=447280&attribute_size=10+lb+-+Covers+20%2C000+Sq+Ft` (VARIATION) | product | 0 | 1 | 0.00% | 1.0 |
| `/products/grass-seed/clover-lawn-alternative-mix/` | product | 0 | 1 | 0.00% | 2.0 |
| `/products/grass-seed/clover-lawn-alternative-mix/?variation_id=458445&attribute_pa_coverage-area=10-lbs-2000-sq-ft` (VARIATION) | product | 0 | 1 | 0.00% | 10.0 |
| *... +2 more pages* | — | — | 2 | — | — |

**Recommended canonical:** `/products/clover-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 3 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.4. "best grass seed for florida"
**Total impressions:** 4,483 | **Total clicks:** 14 | **Pages competing:** 22

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/florida/` | resource | 2 | 423 | 0.47% | 7.4 |
| `/grass-seed/florida/` | state-landing | 11 | 340 | 3.24% | 2.1 |
| `/grass-seed/florida/#best-florida-grass-seed` (FRAGMENT) | state-landing | 1 | 303 | 0.33% | 2.6 |
| `/grass-seed/florida/#cool-warm-season-grasses` (FRAGMENT) | state-landing | 0 | 300 | 0.00% | 2.6 |
| `/resources/lawn-turf/florida/#best-florida-grass-seed` (FRAGMENT) | resource | 0 | 300 | 0.00% | 7.7 |
| `/resources/lawn-turf/florida/#cool-warm-season-grasses` (FRAGMENT) | resource | 0 | 298 | 0.00% | 7.7 |
| `/grass-seed/florida/#st-augustine-grass` (FRAGMENT) | state-landing | 0 | 263 | 0.00% | 2.6 |
| `/resources/lawn-turf/florida/#st-augustine-grass` (FRAGMENT) | resource | 0 | 261 | 0.00% | 7.5 |
| `/grass-seed/florida/#bermuda-grass` (FRAGMENT) | state-landing | 0 | 245 | 0.00% | 2.6 |
| `/grass-seed/florida/#growing-zones-florida` (FRAGMENT) | state-landing | 0 | 245 | 0.00% | 2.6 |
| *... +12 more pages* | — | — | 1,505 | — | — |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 14 fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.

### 3.5. "best grass seed"
**Total impressions:** 4,320 | **Total clicks:** 30 | **Pages competing:** 26

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/grass-seed/` | product | 30 | 3,776 | 0.79% | 5.9 |
| `/resources/lawn-turf/new-jersey/` | resource | 0 | 89 | 0.00% | 54.5 |
| `/resources/lawn-turf/best-grass-seed-to-buy/` | resource | 0 | 87 | 0.00% | 69.6 |
| `/resources/lawn-turf/ohio/` | resource | 0 | 83 | 0.00% | 57.0 |
| `/` | homepage | 0 | 77 | 0.00% | 38.7 |
| `/resources/lawn-turf/how-to-choose-the-right-grass-seed/` | resource | 0 | 49 | 0.00% | 17.7 |
| `/resources/lawn-turf/california/` | resource | 0 | 46 | 0.00% | 69.5 |
| `/resources/lawn-turf/texas/` | resource | 0 | 36 | 0.00% | 81.3 |
| `/resources/lawn-turf/best-grass-seed-for-your-climate/` | resource | 0 | 30 | 0.00% | 35.4 |
| `/resources/lawn-turf/best-grass-seed-choices-for-athletic-fields/` | resource | 0 | 17 | 0.00% | 2.9 |
| *... +16 more pages* | — | — | 30 | — | — |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.6. "fescue grass seed"
**Total impressions:** 4,146 | **Total clicks:** 4 | **Pages competing:** 15

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/grass-seed/triblade-elite-fescue-lawn-mix/` | product | 0 | 1,579 | 0.00% | 3.0 |
| `/products/pasture-seed/tall-fescue/` | product | 2 | 1,411 | 0.14% | 2.6 |
| `/products/grass-seed/fine-fescue-grass-seed-mix/` | product | 0 | 725 | 0.00% | 3.5 |
| `/product/bundle/pet-kid-friendly-fescue-lawn-bundle/` | other | 1 | 301 | 0.33% | 1.0 |
| `/products/grass-seed/` | product | 0 | 68 | 0.00% | 38.7 |
| `/resources/lawn-turf/fescue-grass-seed-for-shady-areas/` | resource | 0 | 22 | 0.00% | 36.8 |
| `https://www.naturesseed.com/grass-seed/fescue-grass/triple-play-tall-fescue-seed-blend/` | state-landing | 0 | 16 | 0.00% | 1.0 |
| `/products/grass-seed/sheep-fescue-grass/` | product | 0 | 12 | 0.00% | 6.1 |
| `/resources/lawn-turf/common-mistakes-made-when-establishing-a-lawn-from-seed/` | resource | 0 | 4 | 0.00% | 5.8 |
| `/resources/lawn-turf/how-to-grow-tall-fescue-grass-in-the-shade/` | resource | 0 | 2 | 0.00% | 2.0 |
| *... +5 more pages* | — | — | 6 | — | — |

**Recommended canonical:** `/products/grass-seed/triblade-elite-fescue-lawn-mix/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.7. "bermuda grass seed"
**Total impressions:** 3,430 | **Total clicks:** 9 | **Pages competing:** 15

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/bermuda-grass-seed-best-lawn-seed-for-sunny-yards/` | resource | 8 | 3,207 | 0.25% | 1.2 |
| `/products/grass-seed/bermudagrass-seed-blend/` | product | 0 | 179 | 0.00% | 21.6 |
| `/resources/lawn-turf/how-long-does-it-take-grass-to-grow/` | resource | 0 | 13 | 0.00% | 2.7 |
| `/resources/lawn-turf/a-guide-to-grass-seed-germination/` | resource | 1 | 8 | 12.50% | 2.6 |
| `/products/pasture-seed/bermudagrass/` | product | 0 | 7 | 0.00% | 32.6 |
| `/resources/lawn-turf/common-mistakes-made-when-establishing-a-lawn-from-seed/` | resource | 0 | 4 | 0.00% | 3.2 |
| `/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/` | resource | 0 | 3 | 0.00% | 2.3 |
| `/resources/lawn-turf/how-to-choose-the-right-grass-seed/` | resource | 0 | 2 | 0.00% | 5.0 |
| `/products/grass-seed/bermudagrass-seed-blend/?variation_id=445855&attribute_size=5+lb+-+Covers+1%2C000+Sq+Ft` (VARIATION) | product | 0 | 1 | 0.00% | 7.0 |
| `/products/grass-seed/kentucky-bluegrass-seed-blue-ribbon-mix/` | product | 0 | 1 | 0.00% | 1.0 |
| *... +5 more pages* | — | — | 5 | — | — |

**Recommended canonical:** `/products/grass-seed/bermudagrass-seed-blend/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 1 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.8. "best grass seed for florida sandy soil"
**Total impressions:** 3,130 | **Total clicks:** 8 | **Pages competing:** 18

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/florida/` | resource | 2 | 544 | 0.37% | 3.5 |
| `/grass-seed/florida/` | state-landing | 6 | 376 | 1.60% | 1.7 |
| `/grass-seed/florida/#best-florida-grass-seed` (FRAGMENT) | state-landing | 0 | 340 | 0.00% | 3.5 |
| `/grass-seed/florida/#cool-warm-season-grasses` (FRAGMENT) | state-landing | 0 | 335 | 0.00% | 3.5 |
| `/grass-seed/florida/#st-augustine-grass` (FRAGMENT) | state-landing | 0 | 303 | 0.00% | 3.5 |
| `/grass-seed/florida/#bermuda-grass` (FRAGMENT) | state-landing | 0 | 293 | 0.00% | 3.5 |
| `/grass-seed/florida/#growing-zones-florida` (FRAGMENT) | state-landing | 0 | 293 | 0.00% | 3.5 |
| `/grass-seed/florida/#perennial-ryegrass` (FRAGMENT) | state-landing | 0 | 293 | 0.00% | 3.5 |
| `/grass-seed/florida/#tall-fescue` (FRAGMENT) | state-landing | 0 | 293 | 0.00% | 3.5 |
| `/resources/lawn-turf/florida/#bermuda-grass` (FRAGMENT) | resource | 0 | 8 | 0.00% | 5.1 |
| *... +8 more pages* | — | — | 52 | — | — |

**Recommended canonical:** `/resources/lawn-turf/florida/`
**Reason:** This resource page has the most impressions. If a product page exists, consider creating one and shifting authority there.
**Warning:** 14 fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.

### 3.9. "brittlebush"
**Total impressions:** 3,066 | **Total clicks:** 1 | **Pages competing:** 2

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/wildflower-seed/brittlebush/` | product | 1 | 3,053 | 0.03% | 2.8 |
| `/products/wildflower-seeds/brittlebush/` | product | 0 | 13 | 0.00% | 1.0 |

**Recommended canonical:** `/products/wildflower-seed/brittlebush/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.10. "best grass seed for michigan"
**Total impressions:** 2,945 | **Total clicks:** 3 | **Pages competing:** 4

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/michigan/` | resource | 2 | 1,612 | 0.12% | 4.0 |
| `/resources/lawn-turf/best-grass-seed-for-your-climate/` | resource | 1 | 1,306 | 0.08% | 2.0 |
| `/products/grass-seed/` | product | 0 | 18 | 0.00% | 36.5 |
| `/` | homepage | 0 | 9 | 0.00% | 84.7 |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.11. "kentucky bluegrass seed"
**Total impressions:** 2,778 | **Total clicks:** 11 | **Pages competing:** 7

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/grass-seed/` | product | 2 | 897 | 0.22% | 10.3 |
| `/products/grass-seed/water-wise-bluegrass-blend/` | product | 1 | 806 | 0.12% | 4.3 |
| `/resources/lawn-turf/how-to-plant-and-grow/` | resource | 1 | 766 | 0.13% | 11.3 |
| `/products/grass-seed/kentucky-bluegrass-seed-blue-ribbon-mix/` | product | 1 | 297 | 0.34% | 5.1 |
| `/products/grass-seed/kentucky-bluegrass-seed-blue-ribbon-mix/?variation_id=445413&attribute_size=5+lb+-+Covers+1%2C000+Sq+Ft` (VARIATION) | product | 4 | 5 | 80.00% | 2.8 |
| `/products/grass-seed/kentucky-bluegrass-seed-blue-ribbon-mix/?variation_id=449901&attribute_size=10+lb+-+Covers+2%2C000+Sq+Ft` (VARIATION) | product | 1 | 4 | 25.00% | 2.0 |
| `/products/grass-seed/kentucky-bluegrass-seed-blue-ribbon-mix/?variation_id=449902&attribute_size=25+lb+-+Covers+5%2C000+Sq+Ft` (VARIATION) | product | 1 | 3 | 33.33% | 3.3 |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 3 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.12. "perennial ryegrass"
**Total impressions:** 2,703 | **Total clicks:** 15 | **Pages competing:** 3

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/` | resource | 5 | 1,491 | 0.34% | 2.0 |
| `/resources/lawn-turf/how-to-plant-and-grow-perennial-ryegrass/` | resource | 9 | 1,211 | 0.74% | 9.7 |
| `/products/pasture-seed/perennial-ryegrass/?variation_id=446611&attribute_size=5+lb+-+Covers+20%2C000+Sq+Ft` (VARIATION) | product | 1 | 1 | 100.00% | 3.0 |

**Recommended canonical:** `/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/`
**Reason:** This resource page has the most impressions. If a product page exists, consider creating one and shifting authority there.
**Warning:** 1 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.13. "fescue grass"
**Total impressions:** 2,644 | **Total clicks:** 24 | **Pages competing:** 17

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/fescue-grass-seed-for-shady-areas/` | resource | 21 | 1,901 | 1.10% | 1.8 |
| `/products/grass-seed/fine-fescue-grass-seed-mix/` | product | 3 | 458 | 0.66% | 8.8 |
| `/products/grass-seed/triblade-elite-fescue-lawn-mix/` | product | 0 | 139 | 0.00% | 57.0 |
| `/products/pasture-seed/tall-fescue/` | product | 0 | 92 | 0.00% | 9.1 |
| `/products/grass-seed/` | product | 0 | 21 | 0.00% | 59.3 |
| `/resources/lawn-turf/identifying-5-common-lawn-grass-species/` | resource | 0 | 9 | 0.00% | 3.2 |
| `/resources/lawn-turf/sheep-fescue-as-an-alternative-lawn-grass/` | resource | 0 | 7 | 0.00% | 40.4 |
| `/resources/lawn-turf/what-exactly-is-a-low-maintenance-lawn/` | resource | 0 | 6 | 0.00% | 2.2 |
| `/products/grass-seed/sheep-fescue-grass/` | product | 0 | 2 | 0.00% | 67.0 |
| `/resources/lawn-turf/common-mistakes-made-when-establishing-a-lawn-from-seed/` | resource | 0 | 2 | 0.00% | 2.0 |
| *... +7 more pages* | — | — | 7 | — | — |

**Recommended canonical:** `/products/grass-seed/fine-fescue-grass-seed-mix/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 2 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.14. "grass seed for florida"
**Total impressions:** 2,478 | **Total clicks:** 9 | **Pages competing:** 20

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/florida/` | resource | 2 | 408 | 0.49% | 5.2 |
| `/grass-seed/florida/` | state-landing | 7 | 276 | 2.54% | 3.8 |
| `/grass-seed/florida/#best-florida-grass-seed` (FRAGMENT) | state-landing | 0 | 272 | 0.00% | 3.9 |
| `/grass-seed/florida/#cool-warm-season-grasses` (FRAGMENT) | state-landing | 0 | 272 | 0.00% | 3.9 |
| `/grass-seed/florida/#st-augustine-grass` (FRAGMENT) | state-landing | 0 | 242 | 0.00% | 4.1 |
| `/grass-seed/florida/#bermuda-grass` (FRAGMENT) | state-landing | 0 | 232 | 0.00% | 4.1 |
| `/grass-seed/florida/#growing-zones-florida` (FRAGMENT) | state-landing | 0 | 232 | 0.00% | 4.1 |
| `/grass-seed/florida/#perennial-ryegrass` (FRAGMENT) | state-landing | 0 | 232 | 0.00% | 4.1 |
| `/grass-seed/florida/#tall-fescue` (FRAGMENT) | state-landing | 0 | 232 | 0.00% | 4.1 |
| `/resources/lawn-turf/overseeding-lawn-101/` | resource | 0 | 66 | 0.00% | 1.0 |
| *... +10 more pages* | — | — | 14 | — | — |

**Recommended canonical:** `/resources/lawn-turf/florida/`
**Reason:** This resource page has the most impressions. If a product page exists, consider creating one and shifting authority there.
**Warning:** 14 fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.

### 3.15. "best grass seed for montana"
**Total impressions:** 2,425 | **Total clicks:** 2 | **Pages competing:** 7

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/montana/` | resource | 2 | 1,204 | 0.17% | 1.3 |
| `/resources/lawn-turf/best-grass-seed-for-your-climate/` | resource | 0 | 612 | 0.00% | 1.5 |
| `/resources/lawn-turf/montana/#climate-zones` (FRAGMENT) | resource | 0 | 247 | 0.00% | 4.0 |
| `/resources/lawn-turf/montana/#cool-season` (FRAGMENT) | resource | 0 | 247 | 0.00% | 4.0 |
| `/resources/lawn-turf/montana/#warm-season` (FRAGMENT) | resource | 0 | 86 | 0.00% | 5.3 |
| `/products/grass-seed/` | product | 0 | 28 | 0.00% | 17.5 |
| `/resources/lawn-turf/oklahoma/` | resource | 0 | 1 | 0.00% | 95.0 |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 3 fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.

### 3.16. "fine fescue grass seed"
**Total impressions:** 2,289 | **Total clicks:** 9 | **Pages competing:** 6

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/grass-seed/fine-fescue-grass-seed-mix/` | product | 8 | 1,525 | 0.52% | 2.4 |
| `/resources/lawn-turf/fescue-grass-seed-for-shady-areas/` | resource | 1 | 725 | 0.14% | 1.8 |
| `/products/grass-seed/` | product | 0 | 33 | 0.00% | 10.0 |
| `/products/grass-seed/triblade-elite-fescue-lawn-mix/` | product | 0 | 4 | 0.00% | 39.2 |
| `/products/california-seeds/` | product | 0 | 1 | 0.00% | 16.0 |
| `/products/grass-seed/california-native-lawn-alternative-mix/` | product | 0 | 1 | 0.00% | 7.0 |

**Recommended canonical:** `/products/grass-seed/fine-fescue-grass-seed-mix/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.17. "clover seed"
**Total impressions:** 2,086 | **Total clicks:** 6 | **Pages competing:** 12

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/clover-seed/` | product | 4 | 951 | 0.42% | 10.7 |
| `/products/clover-seed/white-dutch-clover/` | product | 2 | 777 | 0.26% | 9.2 |
| `/clover-seed-planting-instructions/` | other | 0 | 161 | 0.00% | 12.3 |
| `/products/clover-seed/microclover/` | product | 0 | 143 | 0.00% | 47.7 |
| `/resources/lawn-turf/clover-seed-planting-instructions/` | resource | 0 | 38 | 0.00% | 46.8 |
| `/products/clover-seed/white-clover/` | product | 0 | 9 | 0.00% | 12.3 |
| `/products/grass-seed/clover-lawn-alternative-mix/` | product | 0 | 2 | 0.00% | 1.0 |
| `/products/clover-seed/white-clover/?variation_id=452371&attribute_size=5+lb+-+Covers+10%2C000+Sq+Ft` (VARIATION) | product | 0 | 1 | 0.00% | 13.0 |
| `/products/clover-seed/white-dutch-clover/?variation_id=447282&attribute_size=5+lb+-+Covers+10%2C000+Sq+Ft` (VARIATION) | product | 0 | 1 | 0.00% | 5.0 |
| `/products/pasture-seed/poultry-forage-mix/` | product | 0 | 1 | 0.00% | 1.0 |
| *... +2 more pages* | — | — | 2 | — | — |

**Recommended canonical:** `/products/clover-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 2 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.18. "clover seeds"
**Total impressions:** 2,065 | **Total clicks:** 0 | **Pages competing:** 9

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/clover-seed/` | product | 0 | 1,168 | 0.00% | 9.1 |
| `/products/clover-seed/white-dutch-clover/` | product | 0 | 671 | 0.00% | 11.3 |
| `/clover-seed-planting-instructions/` | other | 0 | 122 | 0.00% | 3.2 |
| `/products/clover-seed/microclover/` | product | 0 | 79 | 0.00% | 81.9 |
| `/resources/lawn-turf/clover-seed-planting-instructions/` | resource | 0 | 20 | 0.00% | 41.2 |
| `/products/grass-seed/clover-lawn-alternative-mix/` | product | 0 | 2 | 0.00% | 1.0 |
| `/products/pasture-seed/poultry-forage-mix/` | product | 0 | 1 | 0.00% | 11.0 |
| `/products/pasture-seed/poultry-forage-mix/?variation_id=445261&attribute_size=50+lb+-+Covers+100%2C000+Sq+Ft` (VARIATION) | product | 0 | 1 | 0.00% | 2.0 |
| `/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/` | resource | 0 | 1 | 0.00% | 1.0 |

**Recommended canonical:** `/products/clover-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 1 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.19. "best grass seed for indiana"
**Total impressions:** 1,993 | **Total clicks:** 8 | **Pages competing:** 7

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/indiana/` | resource | 8 | 1,383 | 0.58% | 3.4 |
| `/resources/lawn-turf/indiana/#best-grasses` (FRAGMENT) | resource | 0 | 280 | 0.00% | 3.0 |
| `/resources/lawn-turf/indiana/#seed-mixtures` (FRAGMENT) | resource | 0 | 280 | 0.00% | 3.0 |
| `/resources/lawn-turf/indiana/#best-planting-times` (FRAGMENT) | resource | 0 | 17 | 0.00% | 2.0 |
| `/resources/lawn-turf/indiana/#growing-conditions` (FRAGMENT) | resource | 0 | 17 | 0.00% | 2.0 |
| `/products/grass-seed/` | product | 0 | 13 | 0.00% | 28.4 |
| `/` | homepage | 0 | 3 | 0.00% | 73.7 |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 4 fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.

### 3.20. "natures seed"
**Total impressions:** 1,957 | **Total clicks:** 50 | **Pages competing:** 7

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/` | homepage | 40 | 486 | 8.23% | 1.3 |
| `/products/grass-seed/` | product | 2 | 382 | 0.52% | 1.2 |
| `/products/` | other | 4 | 378 | 1.06% | 1.0 |
| `/contact-us/` | other | 1 | 367 | 0.27% | 3.5 |
| `/products/pasture-seed/` | product | 1 | 219 | 0.46% | 1.1 |
| `/products/grass-seed/triblade-elite-fescue-lawn-mix/` | product | 1 | 66 | 1.52% | 1.0 |
| `/products/wildflower-seed/` | product | 1 | 59 | 1.69% | 1.1 |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.21. "rye grass"
**Total impressions:** 1,779 | **Total clicks:** 12 | **Pages competing:** 2

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/how-to-plant-and-grow-perennial-ryegrass/` | resource | 11 | 1,778 | 0.62% | 5.9 |
| `/products/pasture-seed/goat-pasture-forage-mix-cold-season/` | product | 1 | 1 | 100.00% | 1.0 |

**Recommended canonical:** `/products/pasture-seed/goat-pasture-forage-mix-cold-season/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.22. "best grass seed for eastern washington"
**Total impressions:** 1,759 | **Total clicks:** 0 | **Pages competing:** 5

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/grass-seed/washington/` | state-landing | 0 | 1,259 | 0.00% | 2.1 |
| `/resources/lawn-turf/washington/` | resource | 0 | 482 | 0.00% | 2.2 |
| `/resources/wildlife-habitat-sustainability/native-grass-series-washington-state/` | resource | 0 | 14 | 0.00% | 29.6 |
| `/resources/best-grass-seed-for-the-pacific-northwest-2026/` | resource | 0 | 3 | 0.00% | 77.3 |
| `/products/grass-seed/twca-water-wise-sun-shade-mix/` | product | 0 | 1 | 0.00% | 1.0 |

**Recommended canonical:** `/products/grass-seed/twca-water-wise-sun-shade-mix/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.23. "best grass seed for south florida"
**Total impressions:** 1,755 | **Total clicks:** 5 | **Pages competing:** 19

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/florida/` | resource | 1 | 166 | 0.60% | 5.6 |
| `/grass-seed/florida/` | state-landing | 4 | 134 | 2.99% | 2.4 |
| `/grass-seed/florida/#best-florida-grass-seed` (FRAGMENT) | state-landing | 0 | 133 | 0.00% | 2.5 |
| `/grass-seed/florida/#cool-warm-season-grasses` (FRAGMENT) | state-landing | 0 | 133 | 0.00% | 2.5 |
| `/grass-seed/florida/#st-augustine-grass` (FRAGMENT) | state-landing | 0 | 113 | 0.00% | 2.5 |
| `/resources/lawn-turf/florida/#best-florida-grass-seed` (FRAGMENT) | resource | 0 | 104 | 0.00% | 7.8 |
| `/resources/lawn-turf/florida/#cool-warm-season-grasses` (FRAGMENT) | resource | 0 | 104 | 0.00% | 7.8 |
| `/grass-seed/florida/#bermuda-grass` (FRAGMENT) | state-landing | 0 | 103 | 0.00% | 2.6 |
| `/grass-seed/florida/#growing-zones-florida` (FRAGMENT) | state-landing | 0 | 103 | 0.00% | 2.6 |
| `/grass-seed/florida/#perennial-ryegrass` (FRAGMENT) | state-landing | 0 | 103 | 0.00% | 2.6 |
| *... +9 more pages* | — | — | 559 | — | — |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 14 fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.

### 3.24. "florida grass seed"
**Total impressions:** 1,646 | **Total clicks:** 4 | **Pages competing:** 20

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/florida/` | resource | 1 | 225 | 0.44% | 7.4 |
| `/grass-seed/florida/` | state-landing | 3 | 203 | 1.48% | 4.2 |
| `/grass-seed/florida/#best-florida-grass-seed` (FRAGMENT) | state-landing | 0 | 195 | 0.00% | 3.3 |
| `/grass-seed/florida/#cool-warm-season-grasses` (FRAGMENT) | state-landing | 0 | 195 | 0.00% | 3.3 |
| `/grass-seed/florida/#st-augustine-grass` (FRAGMENT) | state-landing | 0 | 122 | 0.00% | 3.5 |
| `/grass-seed/florida/#bermuda-grass` (FRAGMENT) | state-landing | 0 | 116 | 0.00% | 3.6 |
| `/grass-seed/florida/#growing-zones-florida` (FRAGMENT) | state-landing | 0 | 116 | 0.00% | 3.6 |
| `/grass-seed/florida/#perennial-ryegrass` (FRAGMENT) | state-landing | 0 | 116 | 0.00% | 3.6 |
| `/grass-seed/florida/#tall-fescue` (FRAGMENT) | state-landing | 0 | 116 | 0.00% | 3.6 |
| `/resources/lawn-turf/florida/#best-florida-grass-seed` (FRAGMENT) | resource | 0 | 38 | 0.00% | 13.7 |
| *... +10 more pages* | — | — | 204 | — | — |

**Recommended canonical:** `/resources/lawn-turf/florida/`
**Reason:** This resource page has the most impressions. If a product page exists, consider creating one and shifting authority there.
**Warning:** 14 fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.

### 3.25. "best grass seed for north florida"
**Total impressions:** 1,610 | **Total clicks:** 5 | **Pages competing:** 21

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/grass-seed/florida/` | state-landing | 5 | 133 | 3.76% | 1.2 |
| `/grass-seed/florida/#best-florida-grass-seed` (FRAGMENT) | state-landing | 0 | 125 | 0.00% | 2.1 |
| `/grass-seed/florida/#cool-warm-season-grasses` (FRAGMENT) | state-landing | 0 | 124 | 0.00% | 2.1 |
| `/resources/lawn-turf/florida/` | resource | 0 | 115 | 0.00% | 9.0 |
| `/grass-seed/florida/#st-augustine-grass` (FRAGMENT) | state-landing | 0 | 113 | 0.00% | 2.0 |
| `/grass-seed/florida/#bermuda-grass` (FRAGMENT) | state-landing | 0 | 109 | 0.00% | 2.1 |
| `/grass-seed/florida/#growing-zones-florida` (FRAGMENT) | state-landing | 0 | 109 | 0.00% | 2.1 |
| `/grass-seed/florida/#perennial-ryegrass` (FRAGMENT) | state-landing | 0 | 109 | 0.00% | 2.1 |
| `/grass-seed/florida/#tall-fescue` (FRAGMENT) | state-landing | 0 | 109 | 0.00% | 2.1 |
| `/resources/lawn-turf/florida/#best-florida-grass-seed` (FRAGMENT) | resource | 0 | 85 | 0.00% | 9.0 |
| *... +11 more pages* | — | — | 479 | — | — |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 14 fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.

### 3.26. "best grass seed for texas"
**Total impressions:** 1,510 | **Total clicks:** 2 | **Pages competing:** 9

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/texas/` | resource | 2 | 338 | 0.59% | 12.0 |
| `/resources/lawn-turf/texas/#best-grass-seed` (FRAGMENT) | resource | 0 | 304 | 0.00% | 11.2 |
| `/resources/lawn-turf/texas/#type-3-tall-fescue` (FRAGMENT) | resource | 0 | 304 | 0.00% | 11.2 |
| `/resources/lawn-turf/texas/#type-1-bermudagrass` (FRAGMENT) | resource | 0 | 303 | 0.00% | 11.2 |
| `/resources/lawn-turf/texas/#type-2-perennial` (FRAGMENT) | resource | 0 | 211 | 0.00% | 10.3 |
| `/products/grass-seed/` | product | 0 | 34 | 0.00% | 12.4 |
| `/resources/lawn-turf/how-to-choose-the-right-grass-seed/` | resource | 0 | 14 | 0.00% | 1.0 |
| `/` | homepage | 0 | 1 | 0.00% | 85.0 |
| `/resources/lawn-turf/common-mistakes-made-when-establishing-a-lawn-from-seed/` | resource | 0 | 1 | 0.00% | 3.0 |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 4 fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.

### 3.27. "best grass seed for ohio"
**Total impressions:** 1,403 | **Total clicks:** 7 | **Pages competing:** 4

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/ohio/` | resource | 7 | 1,389 | 0.50% | 7.0 |
| `/products/grass-seed/kentucky-bluegrass-seed-blue-ribbon-mix/` | product | 0 | 7 | 0.00% | 1.0 |
| `/products/grass-seed/` | product | 0 | 4 | 0.00% | 25.5 |
| `/` | homepage | 0 | 3 | 0.00% | 69.0 |

**Recommended canonical:** `/products/grass-seed/kentucky-bluegrass-seed-blue-ribbon-mix/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.28. "do deer eat wildflowers"
**Total impressions:** 1,379 | **Total clicks:** 5 | **Pages competing:** 5

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/` | resource | 4 | 330 | 1.21% | 1.5 |
| `/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/#deterring-deer-through-plant-selection` (FRAGMENT) | resource | 1 | 298 | 0.34% | 5.2 |
| `/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/#using-scents-to-humanely-deter-deer` (FRAGMENT) | resource | 0 | 298 | 0.00% | 5.2 |
| `/products/wildflower-seed/deer-resistant-wildflower-mix/` | product | 0 | 228 | 0.00% | 2.0 |
| `/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/#understanding-deer-behavior` (FRAGMENT) | resource | 0 | 225 | 0.00% | 5.0 |

**Recommended canonical:** `/products/wildflower-seed/deer-resistant-wildflower-mix/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 3 fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.

### 3.29. "clover lawn"
**Total impressions:** 1,346 | **Total clicks:** 2 | **Pages competing:** 11

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/clover-seed/` | product | 2 | 1,275 | 0.16% | 10.2 |
| `/products/grass-seed/clover-lawn-alternative-mix/` | product | 0 | 26 | 0.00% | 1.0 |
| `/resources/lawn-turf/teeny-tiny-clover-trend/` | resource | 0 | 19 | 0.00% | 83.0 |
| `/products/clover-seed/white-dutch-clover/` | product | 0 | 9 | 0.00% | 11.9 |
| `/clover-seed-planting-instructions/` | other | 0 | 6 | 0.00% | 1.0 |
| `/products/clover-seed/microclover/` | product | 0 | 6 | 0.00% | 1.0 |
| `/products/clover-seed/white-clover/` | product | 0 | 1 | 0.00% | 1.0 |
| `/products/grass-seed/jimmys-blue-ribbon-premium-grass-seed-mix/` | product | 0 | 1 | 0.00% | 1.0 |
| `/resources/agriculture/selecting-ground-cover-in-orchards-and-vineyards/` | resource | 0 | 1 | 0.00% | 1.0 |
| `/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/` | resource | 0 | 1 | 0.00% | 1.0 |
| *... +1 more pages* | — | — | 1 | — | — |

**Recommended canonical:** `/products/clover-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.30. "grass seed florida"
**Total impressions:** 1,240 | **Total clicks:** 3 | **Pages competing:** 18

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/florida/` | resource | 2 | 158 | 1.27% | 5.5 |
| `/grass-seed/florida/` | state-landing | 1 | 142 | 0.70% | 5.4 |
| `/grass-seed/florida/#best-florida-grass-seed` (FRAGMENT) | state-landing | 0 | 140 | 0.00% | 5.2 |
| `/grass-seed/florida/#cool-warm-season-grasses` (FRAGMENT) | state-landing | 0 | 140 | 0.00% | 5.2 |
| `/grass-seed/florida/#st-augustine-grass` (FRAGMENT) | state-landing | 0 | 127 | 0.00% | 5.2 |
| `/grass-seed/florida/#bermuda-grass` (FRAGMENT) | state-landing | 0 | 120 | 0.00% | 5.3 |
| `/grass-seed/florida/#growing-zones-florida` (FRAGMENT) | state-landing | 0 | 120 | 0.00% | 5.3 |
| `/grass-seed/florida/#perennial-ryegrass` (FRAGMENT) | state-landing | 0 | 120 | 0.00% | 5.3 |
| `/grass-seed/florida/#tall-fescue` (FRAGMENT) | state-landing | 0 | 120 | 0.00% | 5.3 |
| `/resources/lawn-turf/overseeding-lawn-101/` | resource | 0 | 38 | 0.00% | 1.0 |
| *... +8 more pages* | — | — | 15 | — | — |

**Recommended canonical:** `/resources/lawn-turf/florida/`
**Reason:** This resource page has the most impressions. If a product page exists, consider creating one and shifting authority there.
**Warning:** 14 fragment URL(s) are being indexed as separate pages for this query. Add canonical tags immediately.

### 3.31. "buffalo grass seed"
**Total impressions:** 1,238 | **Total clicks:** 18 | **Pages competing:** 19

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/pasture-seed/buffalograss/` | product | 10 | 967 | 1.03% | 5.8 |
| `/resources/lawn-turf/planting-a-buffalograss-lawn/` | resource | 0 | 189 | 0.00% | 18.9 |
| `/resources/lawn-turf/an-introduction-to-buffalograss/` | resource | 0 | 23 | 0.00% | 60.9 |
| `/products/grass-seed/sundancer-buffalograss-seed/?variation_id=457051&attribute_size=3+lb+-+Covers+1%2C000+Sq+Ft` (VARIATION) | product | 7 | 16 | 43.75% | 4.0 |
| `/products/pasture-seed/buffalograss/?variation_id=445486&attribute_size=5+lb+-+Covers+20%2C000+Sq+Ft` (VARIATION) | product | 0 | 10 | 0.00% | 3.2 |
| `/resources/lawn-turf/how-to-prepare-your-soil-for-a-buffalo-grass-seed-lawn/` | resource | 0 | 7 | 0.00% | 5.3 |
| `/resources/agriculture/the-sustainable-attributes-of-buffalo-grass-seed/` | resource | 0 | 6 | 0.00% | 71.0 |
| `/products/grass-seed/sundancer-buffalograss-seed/` | product | 1 | 5 | 20.00% | 1.2 |
| `/products/` | other | 0 | 3 | 0.00% | 13.0 |
| `/resources/lawn-turf/common-mistakes-made-when-establishing-a-lawn-from-seed/` | resource | 0 | 3 | 0.00% | 3.0 |
| *... +9 more pages* | — | — | 9 | — | — |

**Recommended canonical:** `/products/pasture-seed/buffalograss/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 4 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.32. "perennial ryegrass seed"
**Total impressions:** 1,140 | **Total clicks:** 3 | **Pages competing:** 2

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/grass-seed/perennial-ryegrass-seed-blend/` | product | 2 | 655 | 0.31% | 5.7 |
| `/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/` | resource | 1 | 485 | 0.21% | 13.7 |

**Recommended canonical:** `/products/grass-seed/perennial-ryegrass-seed-blend/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.33. "best grass seed for oregon coast"
**Total impressions:** 1,138 | **Total clicks:** 1 | **Pages competing:** 3

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/best-grass-seed-for-the-pacific-northwest-2026/` | resource | 0 | 815 | 0.00% | 8.8 |
| `/resources/lawn-turf/oregon/` | resource | 1 | 209 | 0.48% | 9.7 |
| `/products/grass-seed/` | product | 0 | 114 | 0.00% | 10.2 |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.34. "fescue"
**Total impressions:** 1,083 | **Total clicks:** 3 | **Pages competing:** 12

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/fescue-grass-seed-for-shady-areas/` | resource | 1 | 579 | 0.17% | 1.2 |
| `/resources/lawn-turf/sheep-fescue-as-an-alternative-lawn-grass/` | resource | 1 | 331 | 0.30% | 1.4 |
| `/products/grass-seed/fine-fescue-grass-seed-mix/` | product | 0 | 125 | 0.00% | 18.1 |
| `/products/grass-seed/triblade-elite-fescue-lawn-mix/` | product | 0 | 29 | 0.00% | 17.2 |
| `/products/grass-seed/sheep-fescue-grass/` | product | 0 | 6 | 0.00% | 1.0 |
| `/products/pasture-seed/tall-fescue/` | product | 0 | 6 | 0.00% | 20.7 |
| `/resources/lawn-turf/common-mistakes-made-when-establishing-a-lawn-from-seed/` | resource | 0 | 2 | 0.00% | 2.0 |
| `/products/grass-seed/twca-water-wise-shade-mix/?variation_id=451768&attribute_size=25+lb+-+Covers+5%2C000+Sq+Ft` (VARIATION) | product | 1 | 1 | 100.00% | 1.0 |
| `/products/grass-seed/` | product | 0 | 1 | 0.00% | 2.0 |
| `/resources/lawn-turf/advantages-of-grass-seed-over-laying-sod/` | resource | 0 | 1 | 0.00% | 3.0 |
| *... +2 more pages* | — | — | 2 | — | — |

**Recommended canonical:** `/products/grass-seed/fine-fescue-grass-seed-mix/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 1 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.35. "buffalo grass"
**Total impressions:** 1,037 | **Total clicks:** 9 | **Pages competing:** 22

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/an-introduction-to-buffalograss/` | resource | 8 | 890 | 0.90% | 8.4 |
| `/products/pasture-seed/buffalograss/` | product | 0 | 90 | 0.00% | 13.8 |
| `/resources/lawn-turf/buffalo-grass-lawn-wear-and-tear-tips/` | resource | 0 | 18 | 0.00% | 6.3 |
| `/products/grass-seed/sundancer-buffalograss-seed/?variation_id=457051&attribute_size=3+lb+-+Covers+1%2C000+Sq+Ft` (VARIATION) | product | 1 | 6 | 16.67% | 2.8 |
| `/resources/lawn-turf/planting-a-buffalograss-lawn/` | resource | 0 | 6 | 0.00% | 2.5 |
| `/resources/agriculture/the-sustainable-attributes-of-buffalo-grass-seed/` | resource | 0 | 5 | 0.00% | 4.8 |
| `/resources/lawn-turf/common-mistakes-made-when-establishing-a-lawn-from-seed/` | resource | 0 | 3 | 0.00% | 2.7 |
| `/resources/lawn-turf/how-much-sun-for-buffalo-grass-seeds/` | resource | 0 | 3 | 0.00% | 4.3 |
| `/products/grass-seed/sundancer-buffalograss-seed/` | product | 0 | 2 | 0.00% | 1.0 |
| `/products/pasture-seed/buffalograss/?variation_id=445486&attribute_size=5+lb+-+Covers+20%2C000+Sq+Ft` (VARIATION) | product | 0 | 2 | 0.00% | 1.5 |
| *... +12 more pages* | — | — | 12 | — | — |

**Recommended canonical:** `/products/pasture-seed/buffalograss/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 4 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.36. "clover grass"
**Total impressions:** 997 | **Total clicks:** 0 | **Pages competing:** 10

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/clover-seed/` | product | 0 | 701 | 0.00% | 7.0 |
| `/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/` | resource | 0 | 207 | 0.00% | 1.0 |
| `/products/clover-seed/white-dutch-clover/` | product | 0 | 72 | 0.00% | 2.3 |
| `/clover-seed-planting-instructions/` | other | 0 | 5 | 0.00% | 2.2 |
| `/products/clover-seed/microclover/` | product | 0 | 4 | 0.00% | 1.0 |
| `/products/grass-seed/clover-lawn-alternative-mix/` | product | 0 | 2 | 0.00% | 1.0 |
| `/resources/lawn-turf/more-than-luck-why-you-should-add-clover-to-your-lawn-grass/` | resource | 0 | 2 | 0.00% | 6.0 |
| `/resources/lawn-turf/teeny-tiny-clover-trend/` | resource | 0 | 2 | 0.00% | 77.0 |
| `/products/clover-seed/white-clover/` | product | 0 | 1 | 0.00% | 1.0 |
| `/products/clover-seed/white-dutch-clover/?variation_id=447282&attribute_size=5+lb+-+Covers+10%2C000+Sq+Ft` (VARIATION) | product | 0 | 1 | 0.00% | 3.0 |

**Recommended canonical:** `/products/clover-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.
**Warning:** 1 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.37. "brittle bush"
**Total impressions:** 980 | **Total clicks:** 1 | **Pages competing:** 2

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/products/wildflower-seed/brittlebush/` | product | 1 | 971 | 0.10% | 3.6 |
| `/products/wildflower-seeds/brittlebush/` | product | 0 | 9 | 0.00% | 1.0 |

**Recommended canonical:** `/products/wildflower-seed/brittlebush/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.38. "best grass seed for sandy soil"
**Total impressions:** 920 | **Total clicks:** 1 | **Pages competing:** 8

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/` | resource | 0 | 447 | 0.00% | 5.4 |
| `/products/grass-seed/` | product | 0 | 204 | 0.00% | 14.2 |
| `/resources/lawn-turf/wisconsin/` | resource | 1 | 156 | 0.64% | 15.8 |
| `/resources/lawn-turf/best-grass-seed-for-your-climate/` | resource | 0 | 46 | 0.00% | 75.2 |
| `/grass-seed/florida/` | state-landing | 0 | 40 | 0.00% | 22.7 |
| `/resources/lawn-turf/best-grass-seed-to-buy/` | resource | 0 | 13 | 0.00% | 63.3 |
| `/resources/lawn-turf/newyork/` | resource | 0 | 8 | 0.00% | 55.4 |
| `/resources/lawn-turf/florida/` | resource | 0 | 6 | 0.00% | 15.3 |

**Recommended canonical:** `/products/grass-seed/`
**Reason:** Product page should be the primary landing page for commercial queries. Resource pages and blog posts should internally link TO this product page, not compete with it.

### 3.39. "best grass seed for shaded areas"
**Total impressions:** 876 | **Total clicks:** 4 | **Pages competing:** 7

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/` | resource | 2 | 578 | 0.35% | 2.8 |
| `/resources/lawn-turf/fescue-grass-seed-for-shady-areas/` | resource | 2 | 247 | 0.81% | 2.3 |
| `/resources/lawn-turf/how-to-grow-tall-fescue-grass-in-the-shade/` | resource | 0 | 47 | 0.00% | 1.0 |
| `/products/grass-seed/kentucky-bluegrass-seed-blue-ribbon-mix/?variation_id=445413&attribute_size=5+lb+-+Covers+1%2C000+Sq+Ft` (VARIATION) | product | 0 | 1 | 0.00% | 1.0 |
| `/products/grass-seed/twca-water-wise-shade-mix/?variation_id=451767&attribute_size=10+lb+-+Covers+2%2C000+Sq+Ft` (VARIATION) | product | 0 | 1 | 0.00% | 2.0 |
| `/products/grass-seed/twca-water-wise-shade-mix/?variation_id=451769&attribute_size=5+lb+-+Covers+1%2C000+Sq+Ft` (VARIATION) | product | 0 | 1 | 0.00% | 2.0 |
| `/resources/lawn-turf/lawn-and-garden-solutions-for-shady-areas/` | resource | 0 | 1 | 0.00% | 1.0 |

**Recommended canonical:** `/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/`
**Reason:** This resource page has the most impressions. If a product page exists, consider creating one and shifting authority there.
**Warning:** 3 variation URL(s) with query parameters indexed. Block with robots.txt or canonical tags.

### 3.40. "grass fertilizer"
**Total impressions:** 865 | **Total clicks:** 0 | **Pages competing:** 6

| Page | Type | Clicks | Impressions | CTR | Avg Pos |
|------|------|--------|------------|-----|---------|
| `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/` | resource | 0 | 646 | 0.00% | 1.9 |
| `/resources/lawn-turf/how-to-fertilize-your-new-fescue-grass-seed-lawn/` | resource | 0 | 211 | 0.00% | 1.0 |
| `/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/` | resource | 0 | 4 | 0.00% | 1.0 |
| `/resources/lawn-turf/how-to-grow-grass-with-dogs/` | resource | 0 | 2 | 0.00% | 1.0 |
| `/resources/lawn-turf/grass-seed-kentucky-bluegrass-tips-for-fertilizing-your-existing-bluegrass-lawn/` | resource | 0 | 1 | 0.00% | 1.0 |
| `/resources/lawn-turf/organic-matter-achieving-the-best-possible-soil-conditions-for-grass-seed/` | resource | 0 | 1 | 0.00% | 1.0 |

**Recommended canonical:** `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/`
**Reason:** This resource page has the most impressions. If a product page exists, consider creating one and shifting authority there.

---
## 4. Fragment URL Problem

**172 fragment URLs** are being indexed by Google as separate pages.
These are anchor links (e.g., `/page/#section`) that Google is treating as distinct URLs.

**Total wasted impressions across fragment URLs: 228,491**
**Total wasted clicks: 23**

### Impact by Base URL

| Base URL | # Fragments | Total Fragment Impressions | Total Fragment Clicks |
|----------|------------|---------------------------|----------------------|
| `/grass-seed/florida/` | 7 | 42,670 | 11 |
| `/resources/lawn-turf/florida/` | 7 | 30,230 | 3 |
| `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/` | 7 | 27,365 | 1 |
| `/resources/lawn-turf/georgia/` | 7 | 13,066 | 2 |
| `/resources/lawn-turf/how-often-should-you-water-new-grass-seed/` | 5 | 10,571 | 0 |
| `/resources/lawn-turf/oklahoma/` | 4 | 10,275 | 0 |
| `/resources/lawn-turf/how-long-does-it-take-grass-to-grow/` | 4 | 8,024 | 0 |
| `/resources/lawn-turf/texas/` | 4 | 7,886 | 1 |
| `/resources/lawn-turf/indiana/` | 4 | 6,826 | 3 |
| `/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/` | 3 | 6,677 | 1 |
| `/resources/lawn-turf/a-guide-to-grass-seed-germination/` | 4 | 5,820 | 0 |
| `/resources/wildlife-habitat-sustainability/using-vinegar-to-kill-weeds-in-the-lawn-and-garden/` | 3 | 5,658 | 0 |
| `/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/` | 4 | 5,336 | 0 |
| `/resources/lawn-turf/identifying-5-common-lawn-grass-species/` | 6 | 5,176 | 0 |
| `/grass-seed/washington/` | 4 | 4,641 | 0 |
| `/resources/lawn-turf/advantages-of-grass-seed-over-laying-sod/` | 5 | 4,097 | 0 |
| `/resources/lawn-turf/mississippi/` | 4 | 4,084 | 0 |
| `/resources/lawn-turf/arkansas/` | 4 | 3,507 | 0 |
| `/grass-seed/oklahoma/` | 4 | 3,292 | 0 |
| `/resources/lawn-turf/how-much-sun-does-a-perennial-ryegrass-seed-lawn-require/` | 3 | 3,019 | 0 |
| `/resources/lawn-turf/how-to-choose-the-right-grass-seed/` | 10 | 2,403 | 0 |
| `/resources/lawn-turf/new-mexico/` | 3 | 2,290 | 0 |
| `/resources/lawn-turf/tennessee/` | 6 | 2,024 | 0 |
| `/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/` | 3 | 2,017 | 1 |
| `/resources/news-and-misc/states-with-most-flooding/` | 4 | 1,880 | 0 |
| `/resources/lawn-turf/pennsylvania/` | 4 | 1,752 | 0 |
| `/resources/lawn-turf/montana/` | 3 | 1,637 | 0 |
| `/resources/lawn-turf/washington/` | 4 | 1,017 | 0 |
| `/resources/lawn-turf/utah/` | 4 | 964 | 0 |
| `/resources/wildlife-habitat-sustainability/firewheel-a-native-wildflower-favorite-rich-in-legend-lore/` | 3 | 913 | 0 |

### Worst Offenders — Individual Fragment URLs by Impressions

| Fragment URL | Impressions | Clicks | Avg Pos |
|-------------|------------|--------|---------|
| `/grass-seed/florida/#best-florida-grass-seed` | 7,240 | 9 | 4.3 |
| `/grass-seed/florida/#cool-warm-season-grasses` | 7,187 | 0 | 4.3 |
| `/grass-seed/florida/#st-augustine-grass` | 6,184 | 0 | 4.4 |
| `/grass-seed/florida/#bermuda-grass` | 5,604 | 1 | 4.2 |
| `/grass-seed/florida/#tall-fescue` | 5,512 | 0 | 4.2 |
| `/grass-seed/florida/#perennial-ryegrass` | 5,473 | 0 | 4.2 |
| `/grass-seed/florida/#growing-zones-florida` | 5,470 | 1 | 4.2 |
| `/resources/lawn-turf/florida/#best-florida-grass-seed` | 5,037 | 3 | 7.3 |
| `/resources/lawn-turf/florida/#cool-warm-season-grasses` | 5,021 | 0 | 7.3 |
| `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/#why-fertilization-is-key` | 4,357 | 0 | 7.7 |
| `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/#understanding-fertilizer-impact` | 4,318 | 1 | 7.7 |
| `/resources/lawn-turf/florida/#st-augustine-grass` | 4,288 | 0 | 7.3 |
| `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/#starter-vs-regular-fertilizer` | 4,137 | 0 | 7.6 |
| `/resources/lawn-turf/florida/#bermuda-grass` | 4,070 | 0 | 7.4 |
| `/resources/lawn-turf/florida/#tall-fescue` | 3,972 | 0 | 7.3 |
| `/resources/lawn-turf/florida/#growing-zones-florida` | 3,924 | 0 | 7.4 |
| `/resources/lawn-turf/florida/#perennial-ryegrass` | 3,918 | 0 | 7.4 |
| `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/#preparing-your-lawn-for-growth` | 3,727 | 0 | 7.6 |
| `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/#the-science-of-npk-ratios` | 3,655 | 0 | 7.6 |
| `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/#featured-snippet` | 3,621 | 0 | 7.5 |
| `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/#soil-testing-and-ph` | 3,550 | 0 | 7.6 |
| `/resources/lawn-turf/oklahoma/#best-types` | 2,827 | 0 | 7.6 |
| `/resources/lawn-turf/oklahoma/#when-to-plant` | 2,732 | 0 | 7.6 |
| `/resources/lawn-turf/how-often-should-you-water-new-grass-seed/#how-often-to-water-grass-seed` | 2,506 | 0 | 7.1 |
| `/resources/lawn-turf/oklahoma/#soil` | 2,406 | 0 | 7.6 |
| `/resources/lawn-turf/how-often-should-you-water-new-grass-seed/#effect-of-climate-on-watering-new-grass-seed` | 2,388 | 0 | 7.1 |
| `/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/#selecting-the-right-starter-fertilizer` | 2,373 | 1 | 7.3 |
| `/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/#understanding-bermudagrass-nutritional-needs` | 2,368 | 0 | 7.3 |
| `/resources/lawn-turf/oklahoma/#cool-season` | 2,310 | 0 | 7.6 |
| `/resources/lawn-turf/how-long-does-it-take-grass-to-grow/#grass-seed-growth-timeline` | 2,259 | 0 | 9.2 |
| `/resources/lawn-turf/texas/#best-grass-seed` | 2,219 | 1 | 10.3 |
| `/resources/lawn-turf/texas/#type-1-bermudagrass` | 2,212 | 0 | 10.3 |
| `/resources/lawn-turf/how-long-does-it-take-grass-to-grow/#us-grass-climates-when-to-plant-based-on-your-state` | 2,200 | 0 | 9.2 |
| `/resources/lawn-turf/texas/#type-3-tall-fescue` | 2,135 | 0 | 10.3 |
| `/resources/lawn-turf/how-often-should-you-water-new-grass-seed/#what-time-of-day-is-best-to-water-new-grass-seeds` | 2,087 | 0 | 7.1 |
| `/resources/lawn-turf/indiana/#seed-mixtures` | 2,058 | 1 | 4.7 |
| `/resources/lawn-turf/georgia/#georgia-climate-zones` | 2,049 | 1 | 6.7 |
| `/resources/wildlife-habitat-sustainability/using-vinegar-to-kill-weeds-in-the-lawn-and-garden/#the-science-behind-vinegar-as-a-natural-herbicide` | 2,036 | 0 | 6.6 |
| `/resources/lawn-turf/georgia/#warm-season-grasses` | 2,023 | 0 | 6.7 |
| `/resources/wildlife-habitat-sustainability/using-vinegar-to-kill-weeds-in-the-lawn-and-garden/#methods-for-applying-vinegar-to-weeds` | 2,014 | 0 | 6.6 |

### Fix

1. **Add `<link rel="canonical" href="BASE_URL">` to every page** — this tells Google that `page/#section` is the same as `page/`
2. **Check for JavaScript-generated anchor links** that Google is crawling as separate URLs
3. **Verify in Google Search Console** that fragment URLs stop appearing after canonical tags are added
4. **Consider using `scrollTo` JavaScript** instead of anchor `#id` links for in-page navigation

### Variation/Parameter URLs

**294 variation URLs** (with `?variation_id=...`) are indexed.

Total impressions on variation URLs: 2,949

**Top variation URLs by impressions:**

| URL | Impressions | Clicks |
|-----|------------|--------|
| `/resources/agriculture/the-sustainable-attributes-of-buffalo-grass-seed/` | 815 | 1 |
| `/products/grass-seed/kentucky-bluegrass-seed-blue-ribbon-mix/?variation_id=449901&attribute_size=...` | 68 | 3 |
| `/products/grass-seed/sundancer-buffalograss-seed/?variation_id=457051&attribute_size=3+lb+-+Cover...` | 62 | 17 |
| `/products/pasture-seed/horse-pasture-mix-transitional/?variation_id=445282&attribute_size=20+lb+-...` | 43 | 0 |
| `/products/grass-seed/kentucky-bluegrass-seed-blue-ribbon-mix/?variation_id=445413&attribute_size=...` | 41 | 9 |
| `/products/pasture-seed/horse-pasture-mix-cold-season/?variation_id=445860&attribute_size=20+lb+-+...` | 40 | 11 |
| `/products/pasture-seed/cattle-dairy-cow-pasture-mix-cold-warm-season/?variation_id=446796&attribu...` | 40 | 8 |
| `/products/clover-seed/white-dutch-clover/?variation_id=447282&attribute_size=5+lb+-+Covers+10,000...` | 38 | 1 |
| `/products/planting-aids/rice-hull?attribute_pa_c2c_coverage_area=5-lbs-500-1000-sq-ft-for-lawns` | 38 | 0 |
| `/products/grass-seed/twca-water-wise-sun-shade-mix/?variation_id=447116&attribute_size=5+lb+-+Cov...` | 37 | 6 |
| `/products/pasture-seed/poultry-forage-mix/?variation_id=445869&attribute_size=5+lb+-+Covers+10,00...` | 37 | 5 |
| `/products/pasture-seed/cattle-dairy-cow-pasture-mix-cold-warm-season/?variation_id=446797&attribu...` | 36 | 2 |
| `/products/pasture-seed/buffalograss/?variation_id=445486&attribute_size=5+lb+-+Covers+20,000+Sq+Ft` | 35 | 2 |
| `/products/pasture-seed/orchardgrass/?variation_id=445463&attribute_size=5+lb+-+Covers+10,000+Sq+Ft` | 34 | 0 |
| `/products/clover-seed/white-dutch-clover/?variation_id=447280&attribute_size=10+lb+-+Covers+20,00...` | 32 | 3 |

**Fix:** Add `<link rel="canonical">` pointing to the base product URL (without query params). Optionally add `<meta name="robots" content="noindex">` on variation pages or block `?variation_id` in robots.txt.

---
## 5. Internal Linking Action Plan

### 5a. High-Impression Resource Pages That Should Link to Product Pages

These resource/blog pages get significant organic traffic but may not link to the relevant product pages, missing conversion opportunities.

| Resource Page | Impressions | Clicks | Suggested Product Link(s) |
|--------------|------------|--------|--------------------------|
| `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/` | 37,047 | 86 | *Review manually — no obvious product match* |
| `/resources/wildlife-habitat-sustainability/using-vinegar-to-kill-weeds-in-the-lawn-and-garden/` | 33,548 | 172 | *Review manually — no obvious product match* |
| `/resources/lawn-turf/how-long-does-it-take-grass-to-grow/` | 32,860 | 23 | *Review manually — no obvious product match* |
| `/resources/agriculture/unexpected-grazers-5-animals-you-didn-t-know-were-grass-eaters/` | 30,217 | 54 | *Review manually — no obvious product match* |
| `/resources/lawn-turf/how-often-should-you-water-new-grass-seed/` | 29,005 | 76 | *Review manually — no obvious product match* |
| `/resources/lawn-turf/advantages-of-grass-seed-over-laying-sod/` | 27,633 | 62 | *Review manually — no obvious product match* |
| `/resources/lawn-turf/how-to-plant-and-grow-perennial-ryegrass/` | 25,839 | 148 | [First-Year Color + Perennial Foundation Wildflower Kit](https://naturesseed.com/products/wildflower-seed/first-year-and-perennial-foundation-wildflower-kit/); [Jimmy's Perennial Wildflower Mix](https://naturesseed.com/products/wildflower-seed/jimmys-perennial-wildflower-mix/); [Perennial Ryegrass](https://naturesseed.com/products/pasture-seed/perennial-ryegrass/) |
| `/resources/lawn-turf/florida/` | 25,381 | 171 | *Review manually — no obvious product match* |
| `/resources/lawn-turf/identifying-5-common-lawn-grass-species/` | 23,409 | 66 | *Review manually — no obvious product match* |
| `/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/` | 23,349 | 85 | *Review manually — no obvious product match* |
| `/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/` | 23,220 | 119 | [Soil Builder Cover Crop Kit](https://naturesseed.com/products/pasture-seed/soil-builder-cover-crop-kit/); [Shade Tolerant Food Plot Mix](https://naturesseed.com/products/pasture-seed/shade-mix-food-plot/); [White Dutch Clover Soil & Grass Health Boost - 5lb for 10,000 Sq ft.](https://naturesseed.com/product/white-dutch-clover-soil-grass-health-boost-5lb-for-10000-sq-ft/) |
| `/resources/lawn-turf/how-to-plant-and-grow/` | 22,802 | 143 | *Review manually — no obvious product match* |
| `/resources/news-and-misc/how-to-make-plantable-seed-paper/` | 22,538 | 395 | *Review manually — no obvious product match* |
| `/resources/news-and-misc/sand-silt-clay/` | 20,462 | 23 | *Review manually — no obvious product match* |
| `/resources/lawn-turf/a-guide-to-grass-seed-germination/` | 19,216 | 81 | [Rice Hulls: Improve Seed Contact, Germination & Hold Moisture](https://naturesseed.com/products/planting-aids/rice-hulls-improve-seed-contact-germination-hold-moisture/) |
| `/resources/lawn-turf/fescue-grass-seed-for-shady-areas/` | 19,083 | 112 | [Pet & Kid Friendly Low-Maintenance Fescue Lawn Bundle](https://naturesseed.com/product/bundle/pet-kid-friendly-fescue-lawn-bundle/); [Tall Fescue Grass Seed](https://naturesseed.com/products/pasture-seed/tall-fescue/); [Sheep Fescue Grass Seed](https://naturesseed.com/products/grass-seed/sheep-fescue-grass/) |
| `/resources/lawn-turf/how-to-grow-grass-with-dogs/` | 18,449 | 86 | *Review manually — no obvious product match* |
| `/resources/lawn-turf/best-grass-seed-choices-for-athletic-fields/` | 16,610 | 106 | *Review manually — no obvious product match* |
| `/resources/lawn-turf/georgia/` | 15,129 | 143 | *Review manually — no obvious product match* |
| `/resources/wildlife-habitat-sustainability/switchgrass-a-grass-of-many-uses/` | 14,313 | 50 | [Switchgrass (Panicum Virgatum) Seed](https://naturesseed.com/products/pasture-seed/switchgrass-seed/) |
| `/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/` | 14,111 | 57 | [Soil Builder Cover Crop Kit](https://naturesseed.com/products/pasture-seed/soil-builder-cover-crop-kit/); [White Dutch Clover Soil & Grass Health Boost - 5lb for 10,000 Sq ft.](https://naturesseed.com/product/white-dutch-clover-soil-grass-health-boost-5lb-for-10000-sq-ft/); [M-Binder Tackifier-Soil Stabilizer](https://naturesseed.com/products/planting-aids/m-binder-tackifier-soil-stabilizer/) |
| `/resources/lawn-turf/how-to-plant-and-grow-st-augustine-grass-seed/` | 14,032 | 49 | *Review manually — no obvious product match* |
| `/resources/lawn-turf/how-to-fertilize-your-new-fescue-grass-seed-lawn/` | 13,966 | 81 | [Pet & Kid Friendly Low-Maintenance Fescue Lawn Bundle](https://naturesseed.com/product/bundle/pet-kid-friendly-fescue-lawn-bundle/); [Tall Fescue Grass Seed](https://naturesseed.com/products/pasture-seed/tall-fescue/); [Sheep Fescue Grass Seed](https://naturesseed.com/products/grass-seed/sheep-fescue-grass/) |
| `/resources/agriculture/which-pasture-plants-make-the-best-hay/` | 13,632 | 71 | [Thin Pasture Fix Kit](https://naturesseed.com/products/pasture-seed/thin-pasture-kit/); [Dryland Pasture Mix](https://naturesseed.com/products/pasture-seed/dryland-pasture-mix/); [Premium Irrigated Pasture Mix](https://naturesseed.com/products/pasture-seed/premium-irrigated-pasture-mix/) |
| `/resources/lawn-turf/best-grass-seed-for-your-climate/` | 13,452 | 25 | *Review manually — no obvious product match* |
| `/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/` | 12,451 | 88 | [Pasture Clover Mix for Waterfowl Food Plots](https://naturesseed.com/products/pasture-seed/pasture-clover-mix-for-duck-quail-food-plot/); [Green Screen Food Plot Mix](https://naturesseed.com/products/pasture-seed/green-screen-food-plot-screen/); [Full Potential Food Plot Mix](https://naturesseed.com/products/pasture-seed/full-potential-food-plot/) |
| `/resources/news-and-misc/states-with-most-flooding/` | 11,973 | 36 | *Review manually — no obvious product match* |
| `/resources/lawn-turf/oklahoma/` | 11,758 | 102 | *Review manually — no obvious product match* |
| `/resources/agriculture/best-cover-crops-for-the-midwest/` | 11,479 | 7 | [Weed Smother Cover Crop Kit](https://naturesseed.com/products/pasture-seed/weed-smother-cover-crop-kit/); [Soil Builder Cover Crop Kit](https://naturesseed.com/products/pasture-seed/soil-builder-cover-crop-kit/); [Mustard Biofumigant Blend Cover Crop Seed Mix](https://naturesseed.com/products/pasture-seed/mustard-biofumigant-blend-cover-crop-seed-mix/) |
| `/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/` | 11,214 | 61 | [Thin Pasture Fix Kit](https://naturesseed.com/products/pasture-seed/thin-pasture-kit/); [Dryland Pasture Mix](https://naturesseed.com/products/pasture-seed/dryland-pasture-mix/); [Premium Irrigated Pasture Mix](https://naturesseed.com/products/pasture-seed/premium-irrigated-pasture-mix/) |

### 5b. Product Pages That Should Link to Resource Guides

| Product Page | Impressions | Clicks | Suggested Resource Link(s) |
|-------------|------------|--------|---------------------------|
| `/products/grass-seed/` | 115,732 | 344 | *No matching resource found — consider creating a guide* |
| `/products/clover-seed/` | 27,311 | 112 | [teeny-tiny-clover-trend](https://naturesseed.com/resources/lawn-turf/teeny-tiny-clover-trend/); [clover-seed-planting-instructions](https://naturesseed.com/resources/lawn-turf/clover-seed-planting-instructions/); [classy-clover-the-best-addition-to-your-lawn](https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/) |
| `/products/grass-seed/twca-water-wise-sun-shade-mix/` | 14,647 | 15 | [how-often-should-you-water-new-grass-seed](https://naturesseed.com/resources/lawn-turf/how-often-should-you-water-new-grass-seed/); [best-grass-seed-for-shade-and-poor-soil](https://naturesseed.com/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/); [how-much-sun-does-a-perennial-ryegrass-seed-lawn-require](https://naturesseed.com/resources/lawn-turf/how-much-sun-does-a-perennial-ryegrass-seed-lawn-require/) |
| `/products/pasture-seed/` | 13,636 | 104 | [which-pasture-plants-make-the-best-hay](https://naturesseed.com/resources/agriculture/which-pasture-plants-make-the-best-hay/); [pasture-establishment-which-seeding-method-should-you-use](https://naturesseed.com/resources/agriculture/pasture-establishment-which-seeding-method-should-you-use/); [pasture-pig-forage-mixes](https://naturesseed.com/resources/agriculture/pasture-pig-forage-mixes/) |
| `/products/clover-seed/white-dutch-clover/` | 13,074 | 34 | [teeny-tiny-clover-trend](https://naturesseed.com/resources/lawn-turf/teeny-tiny-clover-trend/); [clover-seed-planting-instructions](https://naturesseed.com/resources/lawn-turf/clover-seed-planting-instructions/); [classy-clover-the-best-addition-to-your-lawn](https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/) |
| `/products/grass-seed/triblade-elite-fescue-lawn-mix/` | 11,723 | 49 | [fescue-grass-seed-for-shady-areas](https://naturesseed.com/resources/lawn-turf/fescue-grass-seed-for-shady-areas/); [how-to-fertilize-your-new-fescue-grass-seed-lawn](https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-fescue-grass-seed-lawn/); [how-to-grow-tall-fescue-grass-in-the-shade](https://naturesseed.com/resources/lawn-turf/how-to-grow-tall-fescue-grass-in-the-shade/) |
| `/products/wildflower-seed/` | 11,615 | 32 | [growing-indian-paintbrush-wildflower-seed-challenging-yet-so-rewarding](https://naturesseed.com/resources/wildlife-habitat-sustainability/growing-indian-paintbrush-wildflower-seed-challenging-yet-so-rewarding/); [firewheel-a-native-wildflower-favorite-rich-in-legend-lore](https://naturesseed.com/resources/wildlife-habitat-sustainability/firewheel-a-native-wildflower-favorite-rich-in-legend-lore/); [prevent-water-pollution-using-grass-and-wildflower-buffer-strips](https://naturesseed.com/resources/wildlife-habitat-sustainability/prevent-water-pollution-using-grass-and-wildflower-buffer-strips/) |
| `/products/california-seeds/` | 11,069 | 234 | [california](https://naturesseed.com/resources/lawn-turf/california/); [native-grass-series-california-state](https://naturesseed.com/resources/wildlife-habitat-sustainability/native-grass-series-california-state/); [introducing-the-california-collection](https://naturesseed.com/resources/wildlife-habitat-sustainability/introducing-the-california-collection/) |
| `/products/grass-seed/bermudagrass-seed-blend/` | 10,446 | 24 | [how-to-fertilize-your-new-bermudagrass-seed-lawn](https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/); [how-to-avoid-winter-time-browning-of-bermudagrass-lawns](https://naturesseed.com/resources/lawn-turf/how-to-avoid-winter-time-browning-of-bermudagrass-lawns/); [how-to-dethatch-a-bermudagrass-lawn](https://naturesseed.com/resources/lawn-turf/how-to-dethatch-a-bermudagrass-lawn/) |
| `/products/pasture-seed/tall-fescue/` | 10,295 | 27 | [fescue-grass-seed-for-shady-areas](https://naturesseed.com/resources/lawn-turf/fescue-grass-seed-for-shady-areas/); [how-to-fertilize-your-new-fescue-grass-seed-lawn](https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-fescue-grass-seed-lawn/); [how-to-grow-tall-fescue-grass-in-the-shade](https://naturesseed.com/resources/lawn-turf/how-to-grow-tall-fescue-grass-in-the-shade/) |
| `/products/clover-seed/microclover/` | 10,065 | 45 | *No matching resource found — consider creating a guide* |
| `/products/pasture-seed/alfalfa/` | 9,219 | 50 | [converting-your-old-alfalfa-field-into-a-productive-pasture](https://naturesseed.com/resources/agriculture/converting-your-old-alfalfa-field-into-a-productive-pasture/) |
| `/products/grass-seed/fine-fescue-grass-seed-mix/` | 8,538 | 52 | [fescue-grass-seed-for-shady-areas](https://naturesseed.com/resources/lawn-turf/fescue-grass-seed-for-shady-areas/); [how-to-fertilize-your-new-fescue-grass-seed-lawn](https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-fescue-grass-seed-lawn/); [how-to-grow-tall-fescue-grass-in-the-shade](https://naturesseed.com/resources/lawn-turf/how-to-grow-tall-fescue-grass-in-the-shade/) |
| `/products/wildflower-seed/brittlebush/` | 7,868 | 39 | *No matching resource found — consider creating a guide* |
| `/products/pasture-seed/cereal-rye/` | 7,851 | 15 | *No matching resource found — consider creating a guide* |
| `/products/planting-aids/rice-hull/` | 7,610 | 30 | *No matching resource found — consider creating a guide* |
| `/products/clover-seed/white-clover/` | 7,159 | 13 | [teeny-tiny-clover-trend](https://naturesseed.com/resources/lawn-turf/teeny-tiny-clover-trend/); [clover-seed-planting-instructions](https://naturesseed.com/resources/lawn-turf/clover-seed-planting-instructions/); [classy-clover-the-best-addition-to-your-lawn](https://naturesseed.com/resources/lawn-turf/classy-clover-the-best-addition-to-your-lawn/) |
| `/products/grass-seed/perennial-ryegrass-seed-blend/` | 6,629 | 13 | [how-to-plant-and-grow-perennial-ryegrass](https://naturesseed.com/resources/lawn-turf/how-to-plant-and-grow-perennial-ryegrass/); [how-to-re-seed-your-perennial-ryegrass-lawn](https://naturesseed.com/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/); [how-much-sun-does-a-perennial-ryegrass-seed-lawn-require](https://naturesseed.com/resources/lawn-turf/how-much-sun-does-a-perennial-ryegrass-seed-lawn-require/) |
| `/products/pasture-seed/bermudagrass/` | 6,339 | 31 | [how-to-fertilize-your-new-bermudagrass-seed-lawn](https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/); [how-to-avoid-winter-time-browning-of-bermudagrass-lawns](https://naturesseed.com/resources/lawn-turf/how-to-avoid-winter-time-browning-of-bermudagrass-lawns/); [how-to-dethatch-a-bermudagrass-lawn](https://naturesseed.com/resources/lawn-turf/how-to-dethatch-a-bermudagrass-lawn/) |
| `/products/pasture-seed/horse-pastures-seed/` | 6,223 | 54 | [erosion-control-in-pastures-and-farmland](https://naturesseed.com/resources/agriculture/erosion-control-in-pastures-and-farmland/); [the-importance-of-legumes-in-pastures](https://naturesseed.com/resources/agriculture/the-importance-of-legumes-in-pastures/); [what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures](https://naturesseed.com/resources/agriculture/what-you-need-to-know-about-endophyte-toxicity-in-tall-fescue-pastures/) |
| `/products/pasture-seed/poultry-forage-mix/` | 6,205 | 85 | [pasture-pig-forage-mixes](https://naturesseed.com/resources/agriculture/pasture-pig-forage-mixes/); [ancient-crop-new-interest-sainfoin-for-forage-hay-and-honey](https://naturesseed.com/resources/agriculture/ancient-crop-new-interest-sainfoin-for-forage-hay-and-honey/); [pastured-poultry-what-kind-of-forages-should-your-chickens-be-grazing-on](https://naturesseed.com/resources/agriculture/pastured-poultry-what-kind-of-forages-should-your-chickens-be-grazing-on/) |
| `/products/pasture-seed/orchardgrass/` | 5,731 | 41 | *No matching resource found — consider creating a guide* |
| `/products/grass-seed/water-wise-bluegrass-blend/` | 5,487 | 20 | [how-often-should-you-water-new-grass-seed](https://naturesseed.com/resources/lawn-turf/how-often-should-you-water-new-grass-seed/); [how-much-sun-or-shade-does-a-bluegrass-seed-lawn-require](https://naturesseed.com/resources/lawn-turf/how-much-sun-or-shade-does-a-bluegrass-seed-lawn-require/); [how-to-fertilize-your-new-bluegrass-seed-lawn](https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bluegrass-seed-lawn/) |
| `/products/pasture-seed/shade-mix-food-plot/` | 5,191 | 95 | [best-grass-seed-for-shade-and-poor-soil](https://naturesseed.com/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/); [attract-those-gobblers-with-turkey-food-plots](https://naturesseed.com/resources/wildlife-habitat-sustainability/attract-those-gobblers-with-turkey-food-plots/); [how-to-grow-tall-fescue-grass-in-the-shade](https://naturesseed.com/resources/lawn-turf/how-to-grow-tall-fescue-grass-in-the-shade/) |
| `/products/planting-aids/organic-seed-starter-fertilizer-4-6-4/` | 4,961 | 13 | [understanding-fertilizer-components](https://naturesseed.com/resources/news-and-misc/understanding-fertilizer-components/); [organic-matter-achieving-the-best-possible-soil-conditions-for-grass-seed](https://naturesseed.com/resources/lawn-turf/organic-matter-achieving-the-best-possible-soil-conditions-for-grass-seed/); [does-a-lot-of-fertilizer-make-for-better-plants](https://naturesseed.com/resources/news-and-misc/does-a-lot-of-fertilizer-make-for-better-plants/) |

### 5c. Hub-and-Spoke: Category Pages and Their Products

Each category page should link prominently to all its child product pages (hub → spoke). Product pages should link back to the category and cross-link to related products.

#### Grass Seed (Category)
**Category URL:** `/products/grass-seed/` — 115,732 impressions, 344 clicks
**Products (19):**

- `/products/grass-seed/texas-native-lawn-mix/` — Texas Native Lawn Mix (0 imp)
- `/products/grass-seed/overseed-and-repair-lawn-kit/` — Overseed & Repair Lawn Kit (43 imp)
- `/products/grass-seed/clover-lawn-alternative-mix/` — Clover Lawn Alternative Mix (2,519 imp)
- `/products/grass-seed/meadow-lawn-blend/` — Meadow Lawn Blend (481 imp)
- `/products/grass-seed/high-traffic-hardy-lawn/` — Hardy Grass Seed Mix for High Traffic Lawns (3,521 imp)
- `/products/grass-seed/sundancer-buffalograss-seed/` — Sundancer Buffalograss Lawn Seed (340 imp)
- `/products/grass-seed/twca-water-wise-sun-shade-mix/` — Sun and Shade Grass Seed Mix (14,647 imp)
- `/products/grass-seed/california-habitat-mix/` — California Habitat Mix (889 imp)
- `/products/grass-seed/california-native-lawn-alternative-mix/` — California Native Grass Seed Mix (1,154 imp)
- `/products/grass-seed/thingrass/` — Thingrass (California Bentgrass) (1,529 imp)
- `/products/grass-seed/sheep-fescue-grass/` — Sheep Fescue Grass Seed (2,622 imp)
- `/products/grass-seed/kentucky-bluegrass-seed-blue-ribbon-mix/` — Kentucky Bluegrass and Perennial Ryegrass Mix (4,140 imp)
- `/products/grass-seed/bermudagrass-seed-blend/` — Bermuda Grass Seed Mix for Lawns (10,446 imp)
- `/products/grass-seed/jimmys-blue-ribbon-premium-grass-seed-mix/` — Jimmy's Blue Ribbon Lawn Seed Mix (3,055 imp)
- `/products/grass-seed/water-wise-bluegrass-blend/` — Kentucky Bluegrass Seed Mix (5,487 imp)
- `/products/grass-seed/perennial-ryegrass-seed-blend/` — Perennial Ryegrass Seed Mix (6,629 imp)
- `/products/grass-seed/fine-fescue-grass-seed-mix/` — Fine Fescue Grass Seed Mix (8,538 imp)
- `/products/grass-seed/triblade-elite-fescue-lawn-mix/` — Triblade Elite Tall Fescue Grass Seed Mix (11,723 imp)
- `/products/grass-seed/twca-water-wise-shade-mix/` — Grass Seed Mix for Shady Areas (1,534 imp)

#### Pasture Seed (Category)
**Category URL:** `/products/pasture-seed/` — 13,636 impressions, 104 clicks
**Products (43):**

- `/products/pasture-seed/texas-native-prairie-mix/` — Texas Native Prairie Mix (0 imp)
- `/products/pasture-seed/weed-smother-cover-crop-kit/` — Weed Smother Cover Crop Kit (49 imp)
- `/products/pasture-seed/soil-builder-cover-crop-kit/` — Soil Builder Cover Crop Kit (29 imp)
- `/products/pasture-seed/thin-pasture-kit/` — Thin Pasture Fix Kit (32 imp)
- `/products/pasture-seed/dryland-pasture-mix/` — Dryland Pasture Mix (169 imp)
- `/products/pasture-seed/upland-game-mix/` — Upland Game Mix (0 imp)
- `/products/pasture-seed/native-cabin-grass-mix/` — Native Cabin Grass Seed Mix (16 imp)
- `/products/pasture-seed/premium-irrigated-pasture-mix/` — Premium Irrigated Pasture Mix (65 imp)
- `/products/pasture-seed/mustard-biofumigant-blend-cover-crop-seed-mix/` — Mustard Biofumigant Blend Cover Crop Seed Mix (105 imp)
- `/products/pasture-seed/pasture-clover-mix-for-duck-quail-food-plot/` — Pasture Clover Mix for Waterfowl Food Plots (0 imp)
- `/products/pasture-seed/shortgrass-prairie-mix/` — Shortgrass Prairie Seed Mix (399 imp)
- `/products/pasture-seed/sandhills-prairie-mix/` — Sandhills Prairie Mix (614 imp)
- `/products/pasture-seed/green-screen-food-plot-screen/` — Green Screen Food Plot Mix (1,810 imp)
- `/products/pasture-seed/full-potential-food-plot/` — Full Potential Food Plot Mix (600 imp)
- `/products/pasture-seed/krunch-and-munch-food-plot/` — Krunch N Munch Food Plot Mix (248 imp)
- `/products/pasture-seed/shade-mix-food-plot/` — Shade Tolerant Food Plot Mix (5,191 imp)
- `/products/pasture-seed/plains-prairie-mix/` — Plains Prairie Mix (686 imp)
- `/products/pasture-seed/bahia-grass/` — Bahia Grass Seed (4,609 imp)
- `/products/pasture-seed/cereal-rye/` — Winter (Cereal) Rye Seed (7,851 imp)
- `/products/pasture-seed/common-buckwheat/` — Buckwheat Seed (3,914 imp)
- `/products/pasture-seed/blue-grama/` — Blue Grama Seed (2,315 imp)
- `/products/pasture-seed/switchgrass-seed/` — Switchgrass (Panicum Virgatum) Seed (1,894 imp)
- `/products/pasture-seed/alfalfa/` — Alfalfa Seed (9,219 imp)
- `/products/pasture-seed/kentucky-bluegrass/` — Kentucky Bluegrass (0 imp)
- `/products/pasture-seed/perennial-ryegrass/` — Perennial Ryegrass (0 imp)
- `/products/pasture-seed/buffalograss/` — Buffalograss Seed (4,657 imp)
- `/products/pasture-seed/tall-fescue/` — Tall Fescue Grass Seed (10,295 imp)
- `/products/pasture-seed/orchardgrass/` — Orchardgrass Seed (5,731 imp)
- `/products/pasture-seed/timothy/` — Timothy Grass Hay Seed (4,887 imp)
- `/products/pasture-seed/sheep-pasture-forage-mix-cold-season/` — Cool Season Sheep Pasture Mix (1,635 imp)
- `/products/pasture-seed/sheep-pasture-forage-mix-warm-season/` — Warm Season Sheep Pasture Mix (528 imp)
- `/products/pasture-seed/sheep-pasture-forage-mix-transitional/` — Transitional Zone Sheep Pasture Mix (1,385 imp)
- `/products/pasture-seed/horse-pasture-mix-warm-season/` — Warm Season Horse Pasture Mix (1,335 imp)
- `/products/pasture-seed/horse-pasture-mix-transitional/` — Transitional Zone Horse Pasture Mix (2,485 imp)
- `/products/pasture-seed/pig-pasture-forage-mix/` — Pig Pasture & Forage Mix (1,494 imp)
- `/products/pasture-seed/goat-pasture-forage-mix-transitional/` — Goat Pasture & Forage Mix (4,045 imp)
- `/products/pasture-seed/honey-bee-cover-crop-pasture-mix/` — Honey Bee Cover Crop & Pasture Mix (733 imp)
- `/products/pasture-seed/horse-pasture-mix-cold-season/` — Cool Season Horse Pasture Mix (807 imp)
- `/products/pasture-seed/big-game-food-plot-forage-mix/` — Big Game Food Plot & Forage Mix (1,750 imp)
- `/products/pasture-seed/poultry-forage-mix/` — Chicken Forage Seed Mix (6,205 imp)
- `/products/pasture-seed/cattle-dairy-cow-pasture-mix-for-warm-season/` — Warm Season Cattle Pasture Seed Mix (2,413 imp)
- `/products/pasture-seed/cattle-dairy-cow-pasture-mix-cold-warm-season/` — Cool Season Cattle Pasture Seed Mix (2,071 imp)
- `/products/pasture-seed/alpaca-llama-pasture-forage-mix/` — Llama & Alpaca Pasture Seed Mix (1,778 imp)

#### Wildflower Seed (Category)
**Category URL:** `/products/wildflower-seed/` — 11,615 impressions, 32 clicks
**Products (29):**

- `/products/wildflower-seed/texas-bluebonnet-seeds/` — Texas Bluebonnet Seeds (0 imp)
- `/products/wildflower-seed/texas-native-wildflower-mix/` — Texas Native Wildflower Mix (0 imp)
- `/products/wildflower-seed/texas-pollinator-wildflower-mix/` — Texas Pollinator Wildflower Mix (0 imp)
- `/products/wildflower-seed/pink-evening-primrose-seeds/` — Mexican Primrose (Pinkladies) (0 imp)
- `/products/wildflower-seed/drummond-phlox-seeds/` — Drummond Phlox Seeds (0 imp)
- `/products/wildflower-seed/pollinator-corridor-kit/` — Pollinator Corridor Kit (0 imp)
- `/products/wildflower-seed/first-year-and-perennial-foundation-wildflower-kit/` — First-Year Color + Perennial Foundation Wildflower Kit (35 imp)
- `/products/wildflower-seed/jimmys-perennial-wildflower-mix/` — Jimmy's Perennial Wildflower Mix (0 imp)
- `/products/wildflower-seed/chaparral-sage-scrub-mix/` — Chaparral Sage Scrub Mix (551 imp)
- `/products/wildflower-seed/coastal-sage-scrub-mix/` — Coastal California Sage Scrub Mix (675 imp)
- `/products/wildflower-seed/california-bush-sunflower/` — California Bush Sunflower Seed (2,770 imp)
- `/products/wildflower-seed/white-sage/` — White Sage Seed (2,594 imp)
- `/products/wildflower-seed/purple-needlegrass/` — Purple Needlegrass Seed (3,814 imp)
- `/products/wildflower-seed/arroyo-lupine/` — Arroyo Lupine Seed (755 imp)
- `/products/wildflower-seed/golden-yarrow/` — Golden Yarrow Seed (1,816 imp)
- `/products/wildflower-seed/central-valley-pollinator-mix-xerces-society/` — Central Valley Pollinator Wildflower Mix (510 imp)
- `/products/wildflower-seed/yellow-lupine/` — Yellow Lupine Seed (1,421 imp)
- `/products/wildflower-seed/western-yarrow/` — Western Yarrow Seed (854 imp)
- `/products/wildflower-seed/brittlebush/` — Brittlebrush Seed (7,868 imp)
- `/products/wildflower-seed/bush-monkeyflower/` — Bush Monkeyflower Seed (710 imp)
- `/products/wildflower-seed/blue-eyed-grass/` — Blue-Eyed Grass Seed (1,471 imp)
- `/products/wildflower-seed/miniature-lupine/` — Miniature Lupine Seed (579 imp)
- `/products/wildflower-seed/california-native-wildflower-mix/` — California Native Wildflower Mix (2,358 imp)
- `/products/wildflower-seed/california-coastal-native-wildflower-mix/` — Coastal California Wildflower Seed Mix (4,171 imp)
- `/products/wildflower-seed/california-poppy/` — California Poppy (1,428 imp)
- `/products/wildflower-seed/narrowleaf-milkweed/` — Narrowleaf Milkweed Seed (359 imp)
- `/products/wildflower-seed/deer-resistant-wildflower-mix/` — Deer Resistant Wildflower Seed Mix (2,656 imp)
- `/products/wildflower-seed/rocky-mountain-wildflower-mix/` — Rocky Mountain Wildflower Seed Mix (1,320 imp)
- `/products/wildflower-seed/annual-wildflower-mix/` — Annual Wildflower Seed Mix (3,950 imp)

#### Clover Seed (Category)
**Category URL:** `/products/clover-seed/` — 27,311 impressions, 112 clicks
**Products (6):**

- `/products/clover-seed/white-clover/` — White Clover Seed (7,159 imp)
- `/products/clover-seed/microclover/` — Micro Clover Seed (Mini Clover) (10,065 imp)
- `/products/clover-seed/white-dutch-clover/` — White Dutch Clover Seed (13,074 imp)
- `/products/clover-seed/crimsom-clover-crop-seed/` — Crimson Clover Cover Crop Seed (0 imp)
- `/products/clover-seed/red-clover-seed/` — Red Clover Seed (879 imp)
- `/products/clover-seed/alsike-clover-seed/` — Alsike Clover Seed (202 imp)

#### California Seeds (Category)
**Category URL:** `/products/california-seeds/` — 11,069 impressions, 234 clicks
**Products (0):**

- *No published products found under this category slug*

### 5d. Cross-Category Linking Opportunities

These are thematic connections across categories that could benefit from cross-linking:

| From Category | To Category | Linking Theme |
|--------------|------------|---------------|
| Grass Seed (lawn mixes) | Resources/Lawn Turf (state guides) | State-specific recommendations → product links |
| Pasture Seed (horse/goat/cattle) | Resources/Agriculture | Animal-specific guides → pasture product links |
| Wildflower Seed | Resources/Wildlife Habitat | Pollinator/habitat guides → wildflower product links |
| Clover Seed | Resources/Lawn Turf | Lawn alternative guides → clover product links |
| California Seeds | Resources/Lawn Turf (state guides) | California-specific guides → CA product links |
| Cover Crop Seed | Resources/Agriculture | Soil health guides → cover crop product links |

### 5e. Potentially Orphaned Pages (High Impressions, Likely Few Internal Links)

These pages get significant impressions but are likely not well-linked internally. Verify in the site and add links from relevant pages.

| Page | Type | Impressions | Clicks | Suggested Internal Link Source |
|------|------|------------|--------|-------------------------------|
| `/products/grass-seed/` | product | 115,732 | 344 | Ensure category page links here; add to related resource articles |
| `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/` | resource | 37,047 | 86 | Add links from category pages & product pages in same topic |
| `/resources/wildlife-habitat-sustainability/using-vinegar-to-kill-weeds-in-the-lawn-and-garden/` | resource | 33,548 | 172 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/how-long-does-it-take-grass-to-grow/` | resource | 32,860 | 23 | Add links from category pages & product pages in same topic |
| `/resources/agriculture/unexpected-grazers-5-animals-you-didn-t-know-were-grass-eaters/` | resource | 30,217 | 54 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/how-often-should-you-water-new-grass-seed/` | resource | 29,005 | 76 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/advantages-of-grass-seed-over-laying-sod/` | resource | 27,633 | 62 | Add links from category pages & product pages in same topic |
| `/products/clover-seed/` | product | 27,311 | 112 | Ensure category page links here; add to related resource articles |
| `/clover-seed-planting-instructions/` | other | 26,296 | 128 | Review — may need links from homepage or navigation |
| `/resources/lawn-turf/how-to-plant-and-grow-perennial-ryegrass/` | resource | 25,839 | 148 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/florida/` | resource | 25,381 | 171 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/identifying-5-common-lawn-grass-species/` | resource | 23,409 | 66 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/` | resource | 23,349 | 85 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/` | resource | 23,220 | 119 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/how-to-plant-and-grow/` | resource | 22,802 | 143 | Add links from category pages & product pages in same topic |
| `/resources/news-and-misc/how-to-make-plantable-seed-paper/` | resource | 22,538 | 395 | Add links from category pages & product pages in same topic |
| `/resources/news-and-misc/sand-silt-clay/` | resource | 20,462 | 23 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/a-guide-to-grass-seed-germination/` | resource | 19,216 | 81 | Add links from category pages & product pages in same topic |
| `/grass-seed/florida/` | state-landing | 19,205 | 277 | Link from main grass-seed category; link from state resource page |
| `/resources/lawn-turf/fescue-grass-seed-for-shady-areas/` | resource | 19,083 | 112 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/how-to-grow-grass-with-dogs/` | resource | 18,449 | 86 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/best-grass-seed-choices-for-athletic-fields/` | resource | 16,610 | 106 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/georgia/` | resource | 15,129 | 143 | Add links from category pages & product pages in same topic |
| `/products/grass-seed/twca-water-wise-sun-shade-mix/` | product | 14,647 | 15 | Ensure category page links here; add to related resource articles |
| `/resources/wildlife-habitat-sustainability/switchgrass-a-grass-of-many-uses/` | resource | 14,313 | 50 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/how-to-prepare-soil-for-grass-seed/` | resource | 14,111 | 57 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/how-to-plant-and-grow-st-augustine-grass-seed/` | resource | 14,032 | 49 | Add links from category pages & product pages in same topic |
| `/resources/lawn-turf/how-to-fertilize-your-new-fescue-grass-seed-lawn/` | resource | 13,966 | 81 | Add links from category pages & product pages in same topic |
| `/products/pasture-seed/` | product | 13,636 | 104 | Ensure category page links here; add to related resource articles |
| `/resources/agriculture/which-pasture-plants-make-the-best-hay/` | resource | 13,632 | 71 | Add links from category pages & product pages in same topic |

---
## 6. Canonical URL Structure Recommendations

### 6a. Pages That Need Canonical Tags

Every page with fragment or parameter variations should have a `<link rel="canonical">` pointing to the clean base URL.

- **172 fragment URLs** need canonical → base URL
- **294 variation URLs** need canonical → base product URL

### 6b. Fragment URL Cleanup Priority

Ordered by total fragment impressions per base URL:

1. **`/grass-seed/florida/`** — 7 fragments, 42,670 impressions
   Fragments: `#best-florida-grass-seed`, `#cool-warm-season-grasses`, `#st-augustine-grass`, `#bermuda-grass`, `#tall-fescue` +2 more
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/grass-seed/florida/">` to this page

2. **`/resources/lawn-turf/florida/`** — 7 fragments, 30,230 impressions
   Fragments: `#best-florida-grass-seed`, `#cool-warm-season-grasses`, `#st-augustine-grass`, `#bermuda-grass`, `#tall-fescue` +2 more
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/lawn-turf/florida/">` to this page

3. **`/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/`** — 7 fragments, 27,365 impressions
   Fragments: `#why-fertilization-is-key`, `#understanding-fertilizer-impact`, `#starter-vs-regular-fertilizer`, `#preparing-your-lawn-for-growth`, `#the-science-of-npk-ratios` +2 more
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/">` to this page

4. **`/resources/lawn-turf/georgia/`** — 7 fragments, 13,066 impressions
   Fragments: `#georgia-climate-zones`, `#warm-season-grasses`, `#tall-fescue`, `#bermuda-grass`, `#cool-season-grasses` +2 more
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/lawn-turf/georgia/">` to this page

5. **`/resources/lawn-turf/how-often-should-you-water-new-grass-seed/`** — 5 fragments, 10,571 impressions
   Fragments: `#how-often-to-water-grass-seed`, `#effect-of-climate-on-watering-new-grass-seed`, `#what-time-of-day-is-best-to-water-new-grass-seeds`, `#how-long-does-it-take-for-new-grass-seed-to-grow`, `#cool-season-grass-vs-warm-season-grass`
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/lawn-turf/how-often-should-you-water-new-grass-seed/">` to this page

6. **`/resources/lawn-turf/oklahoma/`** — 4 fragments, 10,275 impressions
   Fragments: `#best-types`, `#when-to-plant`, `#soil`, `#cool-season`
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/lawn-turf/oklahoma/">` to this page

7. **`/resources/lawn-turf/how-long-does-it-take-grass-to-grow/`** — 4 fragments, 8,024 impressions
   Fragments: `#grass-seed-growth-timeline`, `#us-grass-climates-when-to-plant-based-on-your-state`, `#pre-planting-decisions-for-lawn-success`, `#cool-season-grasses-love-early-autumn`
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/lawn-turf/how-long-does-it-take-grass-to-grow/">` to this page

8. **`/resources/lawn-turf/texas/`** — 4 fragments, 7,886 impressions
   Fragments: `#best-grass-seed`, `#type-1-bermudagrass`, `#type-3-tall-fescue`, `#type-2-perennial`
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/lawn-turf/texas/">` to this page

9. **`/resources/lawn-turf/indiana/`** — 4 fragments, 6,826 impressions
   Fragments: `#seed-mixtures`, `#best-grasses`, `#best-planting-times`, `#growing-conditions`
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/lawn-turf/indiana/">` to this page

10. **`/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/`** — 3 fragments, 6,677 impressions
   Fragments: `#selecting-the-right-starter-fertilizer`, `#understanding-bermudagrass-nutritional-needs`, `#step-by-step-guide-to-pre-seeding-fertilization`
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/">` to this page

11. **`/resources/lawn-turf/a-guide-to-grass-seed-germination/`** — 4 fragments, 5,820 impressions
   Fragments: `#three-ways-to-germinate-grass-seed`, `#how-much-to-water-your-grass-seed`, `#pre-germinating-your-grass-seed`, `#mastering-the-four-growth-factors-for-rapid-sprouting`
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/lawn-turf/a-guide-to-grass-seed-germination/">` to this page

12. **`/resources/wildlife-habitat-sustainability/using-vinegar-to-kill-weeds-in-the-lawn-and-garden/`** — 3 fragments, 5,658 impressions
   Fragments: `#the-science-behind-vinegar-as-a-natural-herbicide`, `#methods-for-applying-vinegar-to-weeds`, `#vinegar-a-safe-and-eco-friendly-herbicide`
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/wildlife-habitat-sustainability/using-vinegar-to-kill-weeds-in-the-lawn-and-garden/">` to this page

13. **`/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/`** — 4 fragments, 5,336 impressions
   Fragments: `#understanding-why-you-need-to-reseed-ryegrass`, `#selecting-seed-and-optimal-planting-time`, `#soil-preparation-the-foundation-for-successful-reseeding`, `#proper-soil-amendments-and-fertilization`
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/">` to this page

14. **`/resources/lawn-turf/identifying-5-common-lawn-grass-species/`** — 6 fragments, 5,176 impressions
   Fragments: `#identification-of-fescue-grass-varieties`, `#understanding-grass-compatibility`, `#identification-of-popular-cool-season-grasses`, `#kentucky-bluegrass-identification`, `#perennial-ryegrass-identification` +1 more
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/resources/lawn-turf/identifying-5-common-lawn-grass-species/">` to this page

15. **`/grass-seed/washington/`** — 4 fragments, 4,641 impressions
   Fragments: `#growing-climate`, `#fine-fescue`, `#kentucky-bluegrass`, `#perennial-ryegrass`
   Fix: Add `<link rel="canonical" href="https://naturesseed.com/grass-seed/washington/">` to this page

### 6c. Duplicate Content / URL Inconsistencies

| Issue | URLs | Combined Impressions | Recommendation |
|-------|------|---------------------|----------------|
| Duplicate slug `growing-indian-paintbrush-wildflower-seed-challenging-yet-so-rewarding` | `/blog/growing-indian-paintbrush-wildflower-seed-challenging-yet-so-rewarding` vs `/resources/wildlife-habitat-sustainability/growing-indian-paintbrush-wildflower-seed-challenging-yet-so-rewarding` | 2,897 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `how-to-deal-with-overgrown-roses` | `/blog/how-to-deal-with-overgrown-roses` vs `/resources/gardening/how-to-deal-with-overgrown-roses` | 3,147 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `unexpected-grazers-5-animals-you-didn-t-know-were-grass-eaters` | `/blog/unexpected-grazers-5-animals-you-didn-t-know-were-grass-eaters` vs `/resources/agriculture/unexpected-grazers-5-animals-you-didn-t-know-were-grass-eaters` | 30,222 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `what-you-need-to-know-about-plant-hardiness-zones` | `/blog/what-you-need-to-know-about-plant-hardiness-zones` vs `/resources/news-and-misc/what-you-need-to-know-about-plant-hardiness-zones` | 77 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `worm-mounds-in-lawn-grass-much-ado-about-nothing` | `/blog/worm-mounds-in-lawn-grass-much-ado-about-nothing` vs `/resources/lawn-turf/worm-mounds-in-lawn-grass-much-ado-about-nothing` | 2,360 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `clover-planting-instructions` | `/clover-planting-instructions` vs `/resource/agriculture/clover-planting-instructions` | 137 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `clover-seed-planting-instructions` | `/clover-seed-planting-instructions` vs `/resources/lawn-turf/clover-seed-planting-instructions` | 34,821 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `conservation-seed-planting-instructions` | `/conservation-seed-planting-instructions` vs `/resources/wildlife-habitat-sustainability/conservation-seed-planting-instructions` | 742 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `grass-seed` | `/grass-seed` vs `/products/grass-seed` | 115,734 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `repairing-flood-damagae-in-a-bermuda-grass-lawn` | `/grass-seed/bermuda-grass/repairing-flood-damagae-in-a-bermuda-grass-lawn` vs `/resources/lawn-turf/repairing-flood-damagae-in-a-bermuda-grass-lawn` | 408 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `buffalograss` | `/grass-seed/buffalograss` vs `/pasture-seed/individual-pasture-species/buffalograss` | 65 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `buffalograss` | `/grass-seed/buffalograss` vs `/products/pasture-seed/buffalograss` | 4,679 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `planting-a-buffalograss-lawn` | `/grass-seed/buffalograss/planting-a-buffalograss-lawn` vs `/resources/lawn-turf/planting-a-buffalograss-lawn` | 2,981 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `california` | `/grass-seed/california` vs `/resources/lawn-turf/california` | 6,000 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `white-dutch-clover` | `/grass-seed/clover-seeds-lawn-additive/white-dutch-clover` vs `/products/clover-seed/white-dutch-clover` | 13,132 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `florida` | `/grass-seed/florida` vs `/resources/lawn-turf/florida` | 44,586 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `how-to-prepare-soil-for-grass-seed` | `/grass-seed/how-to-prepare-soil-for-grass-seed` vs `/resources/lawn-turf/how-to-prepare-soil-for-grass-seed` | 14,112 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `iowa` | `/grass-seed/iowa` vs `/resources/lawn-turf/iowa` | 2,248 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `new-hampshire` | `/grass-seed/new-hampshire` vs `/resources/lawn-turf/new-hampshire` | 800 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `north-carolina` | `/grass-seed/north-carolina` vs `/resources/lawn-turf/north-carolina` | 21,731 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `oklahoma` | `/grass-seed/oklahoma` vs `/resources/lawn-turf/oklahoma` | 15,345 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `how-to-plant-and-grow` | `/grass-seed/perennial-ryegrass/how-to-plant-and-grow` vs `/resources/lawn-turf/how-to-plant-and-grow` | 22,803 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `tennessee` | `/grass-seed/tennessee` vs `/resources/lawn-turf/tennessee` | 6,037 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `texas` | `/grass-seed/texas` vs `/resources/lawn-turf/texas` | 9,724 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `washington` | `/grass-seed/washington` vs `/resources/lawn-turf/washington` | 10,876 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `erosion-control-blends` | `/index.php/specialty-seed/erosion-control-blends` vs `/specialty-seed/erosion-control-blends` | 176 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `lawn-seed-planting-instructions` | `/lawn-seed-planting-instructions` vs `/resources/lawn-turf/lawn-seed-planting-instructions` | 3,467 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `buffalograss` | `/pasture-seed/individual-pasture-species/buffalograss` vs `/products/pasture-seed/buffalograss` | 4,700 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `timothy` | `/pasture-seed/individual-pasture-species/timothy` vs `/products/pasture-seed/timothy` | 4,889 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `horse-pasture-mix-transitional` | `/product/horse-pasture-mix-transitional` vs `/products/pasture-seed/horse-pasture-mix-transitional` | 2,486 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `california-native-lawn-alternative-mix` | `/products/grass-seed/california-native-lawn-alternative-mix` vs `/products/grass-seeds/california-native-lawn-alternative-mix` | 1,156 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `kentucky-bluegrass-seed-blue-ribbon-mix` | `/products/grass-seed/kentucky-bluegrass-seed-blue-ribbon-mix` vs `/products/grass-seeds/kentucky-bluegrass-seed-blue-ribbon-mix` | 4,146 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `twca-water-wise-shade-mix` | `/products/grass-seed/twca-water-wise-shade-mix` vs `/products/grass-seeds/twca-water-wise-shade-mix` | 1,535 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `water-wise-bluegrass-blend` | `/products/grass-seed/water-wise-bluegrass-blend` vs `/products/grass-seeds/water-wise-bluegrass-blend` | 5,488 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `alfalfa` | `/products/pasture-seed/alfalfa` vs `/products/pasture-seeds/alfalfa` | 9,257 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `horse-pasture-mix-transitional` | `/products/pasture-seed/horse-pasture-mix-transitional` vs `/products/pasture-seeds/horse-pasture-mix-transitional` | 2,486 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `specialty-seed` | `/products/specialty-seed` vs `/specialty-seed` | 2,247 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `california-native-erosion-control-mix` | `/products/specialty-seed/california-native-erosion-control-mix` vs `/products/specialty-seeds/california-native-erosion-control-mix` | 235 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `brittlebush` | `/products/wildflower-seed/brittlebush` vs `/products/wildflower-seeds/brittlebush` | 7,904 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `bush-monkeyflower` | `/products/wildflower-seed/bush-monkeyflower` vs `/products/wildflower-seeds/bush-monkeyflower` | 711 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `coastal-sage-scrub-mix` | `/products/wildflower-seed/coastal-sage-scrub-mix` vs `/products/wildflower-seeds/coastal-sage-scrub-mix` | 678 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `miniature-lupine` | `/products/wildflower-seed/miniature-lupine` vs `/products/wildflower-seeds/miniature-lupine` | 580 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `purple-needlegrass` | `/products/wildflower-seed/purple-needlegrass` vs `/products/wildflower-seeds/purple-needlegrass` | 3,815 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `western-yarrow` | `/products/wildflower-seed/western-yarrow` vs `/products/wildflower-seeds/western-yarrow` | 856 | 301 redirect lower-imp version → higher-imp version |
| Duplicate slug `wildflower-seed-planting-instructions` | `/resources/wildlife-habitat-sustainability/wildflower-seed-planting-instructions` vs `/wildflower-seed-planting-instructions` | 2,660 | 301 redirect lower-imp version → higher-imp version |

### 6d. WWW vs Non-WWW / HTTP vs HTTPS

**15 non-standard URLs found:**
- `https://www.naturesseed.com/` (339 impressions)
- `http://naturesseed.com/` (1 impressions)
- `https://www.naturesseed.com/pasture-seed/by-region/southern-subtropics-pasture-seed/?p=3` (56 impressions)
- `https://www.naturesseed.com/blog?limit=20` (1 impressions)
- `https://www.naturesseed.com/grass-seed/buffalograss/planting-a-buffalograss-lawn/` (107 impressions)
- `https://www.naturesseed.com/grass-seed/fescue-grass/triple-play-tall-fescue-seed-blend/` (34 impressions)
- `https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures?add-to-cart=440345` (8 impressions)
- `https://www.naturesseed.com/pasture-seed/sheep-pastures?add-to-cart=440380` (1 impressions)
- `https://www.naturesseed.com/resources/lawn-turf/give-your-lawn-a-head-start-this-spring-through-dormant-seeding/` (2 impressions)
- `https://www.naturesseed.com/seed-selector/?seed_type=lawn+wildflower+pasture+specialty+planting-aids&region=intermountain-west` (4 impressions)

---
## 7. Priority Action Items

Ordered by **impact** (impressions affected x ease of fix).

### Priority 1: Quick Wins (Fix This Week)

1. **Add canonical tags to ALL pages** — This single fix addresses 172 fragment URLs and 294 variation URLs (231,440 combined impressions)
   - Implementation: Add `<link rel="canonical" href="{{base_url}}">` in the `<head>` of every page
   - For WooCommerce: Install/configure Yoast SEO or RankMath to auto-set canonicals
   - For fragment URLs: Canonical should point to the URL without `#fragment`
   - For variation URLs: Canonical should point to the URL without `?variation_id=...`

2. **Block variation URLs in robots.txt** — Add: `Disallow: /*?variation_id`

3. **Highest-priority canonical fixes (by impressions):**
   - `/grass-seed/florida/` — 7 fragments, 42,670 impressions
   - `/resources/lawn-turf/florida/` — 7 fragments, 30,230 impressions
   - `/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/` — 7 fragments, 27,365 impressions
   - `/resources/lawn-turf/georgia/` — 7 fragments, 13,066 impressions
   - `/resources/lawn-turf/how-often-should-you-water-new-grass-seed/` — 5 fragments, 10,571 impressions

### Priority 2: High-Impact Internal Links (This Month)

Add internal links from high-traffic resource pages to relevant product pages:

1. **`/resources/lawn-turf/how-to-plant-and-grow-perennial-ryegrass/`** (25,839 imp) → link to [First-Year Color + Perennial Foundation Wildflower Kit](https://naturesseed.com/products/wildflower-seed/first-year-and-perennial-foundation-wildflower-kit/)
2. **`/resources/lawn-turf/how-to-plant-and-grow-perennial-ryegrass/`** (25,839 imp) → link to [Jimmy's Perennial Wildflower Mix](https://naturesseed.com/products/wildflower-seed/jimmys-perennial-wildflower-mix/)
3. **`/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/`** (23,220 imp) → link to [Soil Builder Cover Crop Kit](https://naturesseed.com/products/pasture-seed/soil-builder-cover-crop-kit/)
4. **`/resources/lawn-turf/best-grass-seed-for-shade-and-poor-soil/`** (23,220 imp) → link to [Shade Tolerant Food Plot Mix](https://naturesseed.com/products/pasture-seed/shade-mix-food-plot/)
5. **`/resources/lawn-turf/a-guide-to-grass-seed-germination/`** (19,216 imp) → link to [Rice Hulls: Improve Seed Contact, Germination & Hold Moisture](https://naturesseed.com/products/planting-aids/rice-hulls-improve-seed-contact-germination-hold-moisture/)

### Priority 3: Pages to Consolidate or Redirect (This Month)

These are the most cannibalized queries where consolidation would have the biggest impact:

1. **"grass seed"** (41,109 imp, 70 pages)
   - Keep: `/products/grass-seed/`
   - Consolidate: `/products/grass-seed/twca-water-wise-sun-shade-mix/` (6,945 imp) → 301 or canonical to primary
   - Consolidate: `/products/grass-seed/twca-water-wise-shade-mix/` (69 imp) → 301 or canonical to primary
   - Consolidate: `/products/pasture-seed/goat-pasture-forage-mix-transitional/` (46 imp) → 301 or canonical to primary
2. **"best grass seed for washington state"** (4,691 imp, 12 pages)
   - Primary: `/grass-seed/washington/` — add canonical; ensure other pages link here instead of competing
3. **"clover seeds for lawn"** (4,557 imp, 12 pages)
   - Keep: `/products/clover-seed/`
   - Consolidate: `/products/clover-seed/white-dutch-clover/` (1,473 imp) → 301 or canonical to primary
4. **"best grass seed for florida"** (4,483 imp, 22 pages)
   - Primary: `/resources/lawn-turf/florida/` — add canonical; ensure other pages link here instead of competing
5. **"best grass seed"** (4,320 imp, 26 pages)
   - Primary: `/products/grass-seed/` — add canonical; ensure other pages link here instead of competing
6. **"fescue grass seed"** (4,146 imp, 15 pages)
   - Keep: `/products/grass-seed/triblade-elite-fescue-lawn-mix/`
   - Consolidate: `/products/pasture-seed/tall-fescue/` (1,411 imp) → 301 or canonical to primary
   - Consolidate: `/products/grass-seed/fine-fescue-grass-seed-mix/` (725 imp) → 301 or canonical to primary
   - Consolidate: `/products/grass-seed/` (68 imp) → 301 or canonical to primary
7. **"bermuda grass seed"** (3,430 imp, 15 pages)
   - Keep: `/resources/lawn-turf/bermuda-grass-seed-best-lawn-seed-for-sunny-yards/`
   - Consolidate: `/resources/lawn-turf/how-long-does-it-take-grass-to-grow/` (13 imp) → 301 or canonical to primary
8. **"best grass seed for florida sandy soil"** (3,130 imp, 18 pages)
   - Primary: `/resources/lawn-turf/florida/` — add canonical; ensure other pages link here instead of competing
9. **"brittlebush"** (3,066 imp, 2 pages)
   - Keep: `/products/wildflower-seed/brittlebush/`
   - Consolidate: `/products/wildflower-seeds/brittlebush/` (13 imp) → 301 or canonical to primary
10. **"best grass seed for michigan"** (2,945 imp, 4 pages)
   - Keep: `/resources/lawn-turf/michigan/`
   - Consolidate: `/resources/lawn-turf/best-grass-seed-for-your-climate/` (1,306 imp) → 301 or canonical to primary

### Priority 4: Content Gaps to Fill (Next Quarter)

High-impression queries where we carry the product but have weak or no dedicated landing pages:

4. **"bermuda grass seed"** (3,430 imp)
   - Product: [Bermuda Grass Seed Mix for Lawns](https://naturesseed.com/products/grass-seed/bermudagrass-seed-blend/)
   - Currently ranking: `/resources/lawn-turf/bermuda-grass-seed-best-lawn-seed-for-sunny-yards/` (a resource page)
   - Action: Optimize the product page for this query; add internal links from the ranking resource page to the product page
6. **"kentucky bluegrass"** (2,711 imp)
   - Product: [Kentucky Bluegrass](https://naturesseed.com/products/pasture-seed/kentucky-bluegrass/)
   - Currently ranking: `/resources/lawn-turf/how-to-plant-and-grow/` (a resource page)
   - Action: Optimize the product page for this query; add internal links from the ranking resource page to the product page
7. **"perennial ryegrass"** (2,703 imp)
   - Product: [Perennial Ryegrass](https://naturesseed.com/products/pasture-seed/perennial-ryegrass/)
   - Currently ranking: `/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/` (a resource page)
   - Action: Optimize the product page for this query; add internal links from the ranking resource page to the product page
8. **"fescue grass"** (2,644 imp)
   - Product: [Pet & Kid Friendly Low-Maintenance Fescue Lawn Bundle](https://naturesseed.com/product/bundle/pet-kid-friendly-fescue-lawn-bundle/)
   - Currently ranking: `/resources/lawn-turf/fescue-grass-seed-for-shady-areas/` (a resource page)
   - Action: Optimize the product page for this query; add internal links from the ranking resource page to the product page

---
*End of report. All data sourced from Google Search Console (30-day window) and WooCommerce product catalog.*