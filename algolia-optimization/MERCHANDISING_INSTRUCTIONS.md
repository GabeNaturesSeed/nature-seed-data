# Nature's Seed — Merchandising Optimization Instructions

**Date:** March 4, 2026
**For:** Frontend designer + WooCommerce admin
**Season:** Spring (peak planting)

---

## CRITICAL BUSINESS RULE

**Jimmy's Blue Ribbon** is an influencer product — it CANNOT be advertised, featured, or merchandised anywhere. Use **Kentucky Bluegrass Mix** and **Perennial Ryegrass Mix** (same composition, NS brand) in all merchandising instead.

---

## What's Already Done (Algolia — No Action Needed)

The following Algolia backend changes are live and working:

- **10 merchandising rules** — spring pinning, drought/pollinator/pet/clover/lawn rules, 4 no-catalog redirects (zoysia, creeping thyme, sorghum, thyme)
- **81 synonyms** — including 6 new search gap synonyms (sainfoin, milkweed, sunflower, ground cover, no mow, overseeding)
- **Expanded enrichment** — all ACF fields now indexed (FAQ answers, product cards, mix contents). Average content: 8,300+ chars/product
- **Popularity scoring** — `popularity_score` (0-100 from order data) + `seasonal_boost` (spring: lawn/clover/wildflower boosted) driving `customRanking`
- **37 contextual tags** on every product (`contextual_tags` array)
- **17 "We Don't Carry This" redirect rules** with `userData` messages
- **Cron job** re-enriches every 6 hours automatically

---

## URGENT: Product Content Quality

The Algolia `content` field is enriched via cron, but **thin WooCommerce product descriptions hurt both search relevance and SEO**.

**Immediate action needed:**
1. Check WP Search with Algolia plugin settings — ensure product descriptions are included in sync
2. **Rewrite Planting Aid descriptions** (Rice Hulls, Tackifier, Fertilizer have minimal content)
   - Every description should include: what it is, how to use it, benefits, application rates
3. **Every product** should have at minimum:
   - 150+ word description
   - `short_description` filled
   - Product highlights 1-5 filled

---

## TIER 1: QUICK WINS (This Week)

### 1.1 Spring CTA on Homepage Hero

| | |
|---|---|
| **Where** | Frontend/Theme — homepage hero section |
| **What** | Change CTA button text: "Shop Now" to **"Shop Spring Seeds"** |
| **Link** | `/products` page filtered to show Warm Season Seeds + all Wildflowers |
| **Effort** | 15 minutes |

---

### 1.2 Use-Case Quick-Links Bar Below Category Cards

| | |
|---|---|
| **Where** | Frontend/Theme — new section below the existing category card tiles on homepage |
| **What** | Horizontal row of 5 quick-link tiles (see below) |
| **Style** | Smaller than category cards, pill/button style, brand green (#52b788) or neutral |
| **Effort** | Half day |

**5 Quick Links:**
1. "Spring Lawn Seed" — links to Lawn category
2. "Pollinator Gardens" — links to Wildflower filtered by pollinator
3. "Cover Crops for Spring" — links to Cover Crop category
4. "Clover — Best Value" — links to Clover category
5. "New Arrivals" — links to Products sorted by newest

---

### 1.3 Featured Products as First Row of Category Grids

| | |
|---|---|
| **Where** | WooCommerce Admin + Frontend/Theme |
| **WC Admin** | Edit Product > check "Featured" for products below. Set category page to show Featured first. |
| **Effort** | 1 hour in WC admin |

**Products to Feature:**

| Category | Featured Products |
|---|---|
| **Lawn** | Kentucky Bluegrass Mix, Perennial Ryegrass Mix, Triple-Play Tall Fescue |
| **Clover** | White Dutch Clover, Micro Clover, Clover Lawn Alternative Mix |
| **Wildflower** | CA Native Wildflower Mix, Annual Wildflower Mix, Deer Resistant Mix |
| **Pasture** | Horse Pasture Mix, Cattle/Dairy Pasture Mix, Goat Pasture Mix |
| **Cover Crop** | Weed Smother Kit, Soil Builder Kit, Mustard Biofumigant |
| **Food Plot** | Full Potential Mix, Green Screen Mix, Krunch N Munch Mix |

---

### 1.4 Default Category Sort to Popularity

| | |
|---|---|
| **Where** | WooCommerce Admin > Appearance > Customize > WooCommerce > Product Catalog |
| **What** | Change default sorting from "Default" to "Sort by popularity (sales)" |
| **Effort** | 5 minutes |

---

### 1.5 Implement Algolia Frontend Features

Full implementation specs with JS/CSS/HTML are in a separate document:
**`FRONTEND_INSTRUCTIONS.md`** (same folder as this file)

**3 features to implement:**

#### Feature 1: Contextual Tag Pills on Search Results
- Data: `contextual_tags` array already on every Algolia record
- Shows small pill badges (e.g., "Drought Tolerant", "Lawn Seed") on search results when they match the query
- Limit: 3 pills max per result

```
Search: "drought tolerant lawn"

[img] Bermuda Grass Seed Mix for Lawns
      $119.99 - $499.99
      Lawn Seed
      [Drought Tolerant] [Lawn Seed]        <-- pills
```

#### Feature 2: "We Don't Carry This" Redirect Banners
- Data: `userData` array in Algolia response (only present when redirect rule fires)
- Shows friendly message above results when customer searches for products we don't carry
- 17 redirect rules configured (zoysia, sorghum, creeping thyme, centipede, etc.)

```
Search: "zoysia"

  (i) We don't carry Zoysia grass seed this season.
      Here are other warm-season lawn grasses
      that might interest you:              <-- banner

[img] Bermuda Grass Seed Mix for Lawns
      $119.99 - $499.99
```

#### Feature 3: Click Analytics
- Add `clickAnalytics: true` to Algolia query params
- Send click events via Insights API when user clicks a search result
- Enables Algolia to learn from user behavior and improve relevance

**See `FRONTEND_INSTRUCTIONS.md` for complete implementation code.**

---

## TIER 2: MEDIUM EFFORT (Weeks 2-4)

### 2.1 Product Badges on Category Pages

| | |
|---|---|
| **Where** | WooCommerce Admin (tags) + Frontend/Theme (badge component) |
| **WC Admin** | Create tags: `best-seller`, `staff-pick`, `new-arrival` |
| **Frontend** | Render badges on product cards in category grids |
| **Performance** | Badges MUST be CSS-only (no JS). Site TTI is 15-20s. |

**Badge Styles:**
- Green badge (#52b788): "Best Seller" / "Staff Pick"
- Earth badge (#d4a373): "New"

**Tag as `best-seller`:**
- Kentucky Bluegrass Mix
- Perennial Ryegrass Mix
- Triple-Play Tall Fescue
- White Dutch Clover
- Micro Clover
- CA Native Wildflower Mix
- M-Binder Tackifier

---

### 2.2 Cross-Sell in Cart Drawer + Thank You Page

#### Cart Drawer Cross-Sell

| | |
|---|---|
| **Where** | Frontend/Theme — cart drawer that opens when adding products |
| **What** | Small scrollable section showing 3-4 cross-sell products |
| **Design** | Horizontal scroll, compact cards (thumbnail + name + price + "Add" button) |
| **Label** | "Complete Your Order" or "Don't Forget These" |

**Cross-sell logic (from real purchase data):**

| If cart contains... | Show these cross-sells |
|---|---|
| Lawn Seed | Rice Hulls, White Dutch Clover, Organic Fertilizer |
| Wildflower | Clover Lawn Alt Mix, Kentucky Bluegrass Mix |
| Clover | Kentucky Bluegrass Mix, Annual Wildflower Mix |
| Cover Crop | White Dutch Clover (57.6% cross-buy!), Cattle Pasture Mix |
| Pasture | White Dutch Clover, Rice Hulls, M-Binder Tackifier |
| Food Plot | White Dutch Clover, Rice Hulls |
| **Always show** | **Rice Hulls + Organic Seed Starter Fertilizer** (universal companions) |

#### Thank You Page Cross-Sell

| | |
|---|---|
| **Where** | WooCommerce Thank You / Order Confirmation page |
| **Heading** | **"There's still time to supplement your seed"** |
| **What** | 3-4 product cards based on what they just purchased (same logic as cart drawer) |
| **CTA** | "Buy Now" button that adds to a new order or goes directly to checkout |

**Why:** Post-purchase is a high-intent moment. Cross-sells increase AOV 10-30%.

#### 2.2b WooCommerce Admin: Set Cross-Sells

Set in WC Admin (Products > Edit > Linked Products > Cross-sells):

| Product Category | Cross-sell Products |
|---|---|
| All Lawn Seed products | Rice Hulls, White Dutch Clover, Organic Fertilizer |
| All Pasture products | White Dutch Clover, Rice Hulls, M-Binder Tackifier |
| All Wildflower products | Clover Lawn Alt Mix, Kentucky Bluegrass Mix |
| All Clover products | Kentucky Bluegrass Mix, Annual Wildflower Mix |
| All Cover Crop products | White Dutch Clover, Cattle Pasture Mix |
| All Food Plot products | White Dutch Clover, Rice Hulls |
| ALL seed products | Rice Hulls + Organic Seed Starter Fertilizer (universal) |

---

## TIER 3: LONG-TERM

### Bundles to Create

Cross-purchase data shows strong natural pairings. Requires WC Product Bundles extension or similar.

| Bundle Name | Products | Data Basis | Target Price |
|---|---|---|---|
| **Lawn Starter Kit** | Kentucky Bluegrass Mix + Rice Hulls + Organic Fertilizer | 32.3% of Lawn buyers buy Planting Aids | ~$130, save $15 |
| **Pollinator Garden Bundle** | Pollinator Corridor Kit + Micro Clover + Rice Hulls | Wildflower to Clover 14.4% cross-buy | ~$110, save $10 |
| **Cover Crop & Soil Builder** | Soil Builder Kit + White Dutch Clover + Organic Fertilizer | Cover Crop to Clover 57.6% cross-buy | ~$90, save $10 |
| **Pasture Renewal Bundle** | Horse/Cattle Pasture Mix + White Dutch Clover + Tackifier | Pasture to Clover 11.7%, to Planting Aids 18.5% | ~$200, save $20 |
| **Drought-Tolerant Lawn Kit** | Buffalograss or Bermuda + Tackifier | Drought trend: $4.8B market | ~$150, save $15 |
| **Clover Lawn Conversion Kit** | Clover Lawn Alt Mix + Micro Clover + Rice Hulls | Clover best per-SKU efficiency ($2,511/SKU) | ~$100, save $10 |

**Frontend:** Feature bundles as a homepage section ("Save with Seed Kits") and on relevant category pages. Each bundle should have a product page showing all included items + a "What's Included" breakdown.

---

### Seasonal Content Calendar

Rotate homepage content, category banners, and search rules quarterly. The Algolia `seasonal_boost` attribute rotates automatically via cron.

| Season | Hero CTA | Featured Products | Email/Blog Topics |
|---|---|---|---|
| **Spring (Mar-May)** | "Shop Spring Seeds" | Lawn, Clover, Wildflower, Cover Crop | Spring planting guides, regional tips |
| **Summer (Jun-Aug)** | "Summer Seeding Guide" | Drought-tolerant, Bermuda, Buffalo | Overseeding tips, drought care |
| **Fall (Sep-Nov)** | "Fall Is the Best Time to Seed" | Cool-season lawn, Cover Crops | Fall planting campaigns, soil prep |
| **Winter (Dec-Feb)** | "Plan Your Spring Planting" | Gift ideas, planning content | Pre-order specials, planning content |

**Process:** Set calendar reminders for March 1, June 1, September 1, December 1. Update:
1. Hero CTA text + link
2. Featured products in WC admin
3. Algolia seasonal boost rotates automatically

---

### Future: Homepage "Shop by Use Case" Section
- 6 tiles organized by customer intent: "Drought-Tolerant Lawn", "Pollinator Garden", "Low-Maintenance Ground Cover", "Animal Pasture", "Cover Crops & Soil Building", "Native & Regional Seed"
- Deferred until category filtering infrastructure is ready

---

## WOOCOMMERCE ADMIN CHECKLIST

### Week 1
- [ ] Default sorting to "Sort by popularity" (Customize > WooCommerce > Product Catalog)
- [ ] Feature top 3-5 products per category (Edit Product > check "Featured")
- [ ] Change homepage hero CTA: "Shop Now" to "Shop Spring Seeds" (link to /products filtered warm season + wildflowers)
- [ ] Create tags: `best-seller`, `staff-pick`, `new-arrival`, `spring-favorite`
- [ ] Apply `best-seller` tag to: KY Bluegrass, Perennial Ryegrass, Triple-Play Fescue, White Dutch Clover, Micro Clover, CA Native Wildflower, M-Binder Tackifier

### Weeks 2-3
- [ ] Set cross-sells on all Lawn products (Rice Hulls, Clover, Fertilizer)
- [ ] Set cross-sells on all Pasture products (Clover, Rice Hulls, Tackifier)
- [ ] Set cross-sells on all Wildflower products (Clover, Lawn Seed)
- [ ] Set cross-sells on all Clover products (KY Bluegrass, Wildflower)
- [ ] Set cross-sells on all Cover Crop products (Clover, Pasture)
- [ ] Add Rice Hulls + Fertilizer as cross-sells on ALL seed products

### Weeks 4+
- [ ] Evaluate WC Product Bundles extension
- [ ] Create bundle products (see bundle table above)
- [ ] **URGENT:** Rewrite Planting Aid product descriptions (thin content)
- [ ] Check WP Algolia plugin settings for description sync

---

## PERFORMANCE WARNING

Homepage TTI: 15.9s | Category TTI: 20.3s | Product TTI: 20.9s

**All new frontend work must be:**
- CSS-only where possible (no new JS bundles)
- Lazy-loaded below the fold
- No blocking resources added to `<head>`
