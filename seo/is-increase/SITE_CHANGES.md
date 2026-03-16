# IS Increase — Site-Side Landing Page Instructions

## What Was Already Done (via Google Ads API — March 12, 2026)

### Ad Account Changes (Completed)
1. **Created "Wildflower Seeds" ad group** — moved 5 wildflower keywords out of Pasture campaign where they had BELOW AVERAGE ad relevance
2. **Paused 4 misplaced wildflower keywords** in old Pasture ad groups (were dragging down Quality Score)
3. **Created 9 intent-matched RSA ads:**
   - Wildflower-intent RSA → Wildflower Seeds ad group
   - Horse/equine-intent RSA → Horse ad group, Sheep ad group
   - Drought-intent RSA → Cattle ad group
   - Regional-intent RSA → Cattle, Wildflowers, Regional/Lawn, Clover, Wildflower Seeds ad groups
4. **Added 16 sitelinks** (4 per campaign × 4 campaigns: Animal Seed, Pasture, PMax Search, Brand)
5. **Added 16 callout extensions** (4 per campaign: Free Shipping, USDA Tested Seed, Since 1998, Expert Growing Guides)

### WooCommerce + Google Ads Changes (Completed)
6. **Created "Drought-Tolerant Pasture Seed" category** (ID: 6029) under Pasture Seed
   - URL: `naturesseed.com/product-category/pasture-seed/drought-tolerant-pasture-seed/`
   - **45 products assigned** — identified via species analysis (Bermuda, Blue Grama, Buffalograss, Tall Fescue, Wheatgrass, Switchgrass, etc.)
   - Category description with drought-tolerant content already added
   - Google Ads "drought tolerant pasture grass seed" keyword URL updated to point here
7. **Horse Pasture Seed page already exists** at `/products/pasture-seed/horse-pastures-seed/` — just needs UX improvements

---

## What Needs to Be Done on the Site

These are the remaining changes that need manual work in WordPress. Each one directly improves Google Ads Quality Score "Landing Page Experience" rating.

---

### Priority 1: Set RankMath SEO + Custom Permalink on Drought-Tolerant Category (5 minutes)

The category page was created via API but RankMath SEO and Permalink Manager require WordPress admin access (WC API keys can't authenticate to WP REST API for term meta).

**Go to:** WordPress Admin → Products → Categories → Drought-Tolerant Seed → Edit

Set these RankMath fields:
- **SEO Title:** `Drought-Tolerant Pasture Seed | Water-Wise Forage Mixes | Nature's Seed`
- **Meta Description:** `Shop drought-tolerant pasture grass seed mixes for dry climates & arid conditions. Deep-rooting varieties like Bermuda, Blue Grama & Tall Fescue. USDA-tested, free shipping. Perfect for Western, Texas & low-rainfall pastures.`
- **Focus Keyword:** `drought tolerant pasture seed`

**Set Custom Permalink (Permalink Manager):**
- **Go to:** WordPress Admin → Permalink Manager → find "Drought-Tolerant Seed" category
- **Set custom permalink to:** `products/drought-tolerant-seed`
- This replaces the default `/product-category/pasture-seed/drought-tolerant-seed/` path
- After saving, verify the page loads at `naturesseed.com/products/drought-tolerant-seed/`
- **Then tell me** so I can update the Google Ads keyword final URLs to point to the new permalink

---

### Priority 2: Improve Horse Pasture Seed Page UX

**URL:** `naturesseed.com/products/pasture-seed/horse-pastures-seed/`

This page already exists. Improvements needed:
- Ensure H1 contains "Horse Pasture Grass Seed"
- Add intro paragraph above products mentioning: equine-safe, forage nutrition, heavy grazing, fast recovery
- Add a "Why Choose Our Horse Pasture Seed" section with benefits
- Add a brief planting guide section
- Ensure mobile layout shows first product above the fold

---

### Priority 3: Create Dedicated Landing Pages (Remaining)

Google scores landing page relevance by matching the ad keyword → landing page content. The Pasture campaign is losing **66% impression share to rank** partly because keywords like "texas pasture seed" land on the generic `/product-category/pasture-grass-seed/` page.

~~#### Page 1: Horse & Equine Pasture Seed~~ ✅ Already exists
~~#### Page 2: Drought-Tolerant Pasture Seed~~ ✅ Created via API

#### Page 3: Texas/Regional Pasture Seed
- **URL:** Create a new category or page at `/texas-pasture-grass-seed/`
- **Current ad keywords landing here:** texas pasture grass seed, texas pasture seed, southern pasture grass
- **Page must include:**
  - H1: "Horse Pasture Grass Seed"
  - Opening paragraph mentioning: horse pasture, equine-safe, forage, grazing, nutrient-rich
  - Product grid filtered to horse/equine pasture products only
  - Section: "Why Choose Our Horse Pasture Seed" (benefits: equine-safe species, heavy grazing tolerance, fast recovery, nutritional value)
  - Section: "How to Establish a Horse Pasture" (brief planting guide)
  - Customer testimonials from horse/ranch customers if available
  - Internal links to related products (livestock, clover)
- **After creating:** Update Google Ads → Horse ad group → final URLs to point here

#### Page 2: Drought-Tolerant Pasture Seed
- **URL:** `/drought-tolerant-pasture-seed/` (new page)
- **Current ad keywords:** drought tolerant pasture grass seed, dry climate pasture, arid pasture seed
- **Page must include:**
  - H1: "Drought-Tolerant Pasture Grass Seed"
  - Content about: water-wise, deep-rooting, arid climates, heat tolerance, low rainfall
  - Product grid filtered to drought-tolerant pasture varieties
  - Section: "Best Pasture Grasses for Dry Climates"
  - Water usage comparison table (our seed vs standard pasture)
  - Growing zone map or recommendations by state
- **After creating:** Update Google Ads → Cattle ad group drought keywords → final URLs

#### Page 3: Texas/Regional Pasture Seed
- **URL:** `/texas-pasture-grass-seed/` (new page)
- **Current ad keywords:** texas pasture grass seed, texas pasture seed, southern pasture grass
- **Page must include:**
  - H1: "Texas Pasture Grass Seed"
  - Content specifically about Texas growing conditions, soil types, climate zones
  - Product grid filtered to Texas-appropriate varieties
  - Section: "Best Pasture Grasses for Texas" with species recommendations by region (East TX, Central TX, West TX)
  - Planting calendar for Texas
- **After creating:** Update Google Ads → regional keywords → final URLs
- **Consider also:** California, Western states pages if those keywords grow

#### Page 4: Wildflower Seed (verify existing page)
- **URL:** `/product-category/wildflower-seed/` (should already exist)
- **Verify it has:**
  - H1 containing "Wildflower Seeds" or "Native Wildflower Seed"
  - Content mentioning: native, California, Texas, pollinators, meadow, easy-grow
  - Product grid with all wildflower products
  - If the page is thin (just a product grid with no text), add 200-300 words of introductory content

---

### Priority 4: Page Speed Optimization (All Landing Pages)

Google's "Landing Page Experience" score heavily weighs page load speed, especially on mobile. Run PageSpeed Insights on each landing page and fix:

#### Pages to Audit (in order of ad spend)
1. `naturesseed.com/product-category/grass-seed/` — receives most Shopping traffic
2. `naturesseed.com/product-category/pasture-grass-seed/` — Pasture campaign landing
3. `naturesseed.com/` — Brand campaign landing
4. `naturesseed.com/product-category/wildflower-seed/` — new Wildflower ad group
5. Individual product pages linked from Shopping ads

#### Common Fixes
- [ ] **Compress all product images** — use WebP format, max 200KB per image
- [ ] **Lazy-load below-fold images** — only load product images as user scrolls
- [ ] **Defer non-critical JavaScript** — move analytics/chat/review scripts to after page load
- [ ] **Enable browser caching** — set Cache-Control headers for static assets
- [ ] **Minify CSS/JS** — reduce file sizes
- [ ] **Target:** 90+ mobile PageSpeed score on all ad landing pages
- [ ] **Tool:** Run `https://pagespeed.web.dev/` on each URL above

---

### Priority 5: Above-the-Fold Content (All Category Pages)

Google checks if the landing page immediately shows relevant content to the search query. Category pages that start with just a product grid and no text get lower scores.

#### For Each Category Landing Page:
- [ ] Add **H1 heading** that matches the primary keyword (e.g., "Premium Grass Seed" not "Shop")
- [ ] Add **2-3 sentences of intro text** above the product grid that include the target keywords naturally
- [ ] Add a **visible CTA** above the fold ("Shop [Category] →" or "Browse All [Category] Seed")
- [ ] Ensure the **first product is visible** without scrolling on mobile
- [ ] Remove or minimize any banners/sliders that push products below the fold

---

### Priority 6: Mobile UX Audit

Google evaluates landing pages mobile-first. Since 65% of your traffic is mobile:

- [ ] **Tap targets:** Buttons and links must be at least 48x48px with 8px spacing
- [ ] **Text readability:** Body text ≥ 16px, no need to pinch-zoom
- [ ] **No horizontal scroll:** All content fits within the viewport width
- [ ] **Add-to-cart visible:** Product pages should have the add-to-cart button visible without scrolling past the fold
- [ ] **Filter/sort accessible:** Category pages should have easy filter/sort on mobile (not hidden behind tiny icons)
- [ ] **Checkout flow:** Test the full checkout on mobile — any friction here hurts both QS and conversions

---

### Priority 7: Trust & Content Signals

These factors also feed into Landing Page Experience:

- [ ] **HTTPS active** on all pages (should already be done)
- [ ] **No interstitial popups** on page load (newsletter popups that block content before user engages hurt QS)
- [ ] **Shopper Approved reviews** visible on product pages and category pages
- [ ] **Unique product descriptions** — if any products have manufacturer-copy descriptions, rewrite them with unique content
- [ ] **Return policy + shipping info** visible on product pages (builds trust signals Google looks for)
- [ ] **Contact information** easily accessible (phone, email in header/footer)

---

### Priority 8: PMax Feed Optimization (Google Merchant Center)

PMax campaigns don't have keyword Quality Scores but feed quality directly affects auction rank. Currently losing **80-84% IS to rank**.

- [ ] **Product titles:** Prepend key search terms. Instead of "KBG Supreme Blend" use "Premium Kentucky Bluegrass Seed - KBG Supreme Blend 5lb"
- [ ] **Product descriptions:** Include top search queries naturally (grass seed, lawn seed, premium seed)
- [ ] **High-quality images:** Add lifestyle/in-use images alongside white-background product shots
- [ ] **Product type:** Ensure Google product taxonomy is specific (Home & Garden > Lawn & Garden > Gardening > Seeds > Grass Seeds)
- [ ] **Custom labels:** Use custom_label_0-4 for ROAS tiers, seasonal relevance, margin tiers
- [ ] **Shipping/availability:** Ensure "in_stock" and accurate shipping data for all products
- [ ] **Sale price:** If running any promotions, use `sale_price` field — Google highlights deals in Shopping ads

---

## Expected Impact

| Change | Affects | Est. IS Recovery | Timeline |
|--------|---------|-----------------|----------|
| Intent-matched RSA ads (done) | Ad Relevance | +10-15% IS | 1-2 weeks |
| Sitelinks + callouts (done) | Expected CTR | +5-10% IS | 1-2 weeks |
| Wildflower keyword move (done) | Ad Relevance | +5% IS | 1-2 weeks |
| Dedicated landing pages | LP Experience | +15-25% IS | 2-4 weeks |
| Page speed optimization | LP Experience | +5-10% IS | 1-2 weeks |
| Above-fold content | LP Experience | +5-10% IS | 1 week |
| PMax feed optimization | Auction rank | +10-20% IS | 2-4 weeks |

**Combined target:** Reduce rank-based IS loss from 66-84% down to 20-30% within 4-6 weeks.

---

## How to Verify Progress

1. **Google Ads → Campaigns → Columns → Competitive metrics** — add "Search impr. share", "Search lost IS (rank)", "Search lost IS (budget)"
2. **Google Ads → Keywords → Columns → Quality Score** — add QS, LP Experience, Ad Relevance, Expected CTR
3. **Re-run audit:** `python3 reports/landing_page_audit.py` after 2 weeks to compare
4. **Re-run constraints:** `python3 reports/campaign_constraints.py` to see IS changes

---

*Generated March 12, 2026 by Nature's Seed Data Orchestrator*
