# URL Health Check Summary -- Nature's Seed Google Ads

**Date:** 2026-03-05

## Overall Health Stats

| Metric | Count | % of Total |
|--------|------:|----------:|
| Total URLs Checked | 1060 | 100% |
| OK (200, no redirect) | 372 | 35.1% |
| Redirects (301/302) | 116 | 10.9% |
| Errors (404/timeout/conn) | 572 | 54.0% |

### Error Breakdown

| Error Type | Count |
|-----------|------:|
| HTTP 404 (Not Found) | 569 |
| Connection Error | 2 |
| Timeout | 1 |

### By Source

| Source | Total | OK | Redirects | Errors |
|--------|------:|---:|----------:|-------:|
| Ad Copy URLs | 690 | 18 | 104 | 568 |
| Merchant Feed URLs | 280 | 270 | 7 | 3 |
| Base URL Checks | 90 | 84 | 5 | 1 |

## Financial Impact

| Issue | URLs Affected | Historical Spend |
|-------|-------------:|-----------------:|
| Redirecting ad URLs (>$10 spend) | 34 | $74,366.26 |
| Broken/404 ad URLs (any spend) | 112 | $1,710.43 |
| Broken/404 ad URLs (all) | 568 | $1,710.43 |
| Merchant feed issues | 10 | N/A (feed) |
| **Total wasted/degraded spend** | **146** | **$76,076.69** |

### Why This Matters

- **301 redirects** add latency (200-500ms per hop), hurt Quality Score, and waste crawl budget. Google Ads charges for the click before the redirect completes -- if users bounce due to slow loads, that spend is wasted.
- **404 errors** mean ads are sending paid traffic to dead pages. Any active ads pointing to 404s are burning budget with zero conversion potential.
- **Merchant feed redirects** cause Google Shopping disapprovals and reduced visibility.

## Priority Fixes by Dollar Impact

### Top 15 Redirect Fixes (by historical spend)

| # | Current URL | Redirects To | Spend | Clicks |
|---|-----------|-------------|------:|-------:|
| 1 | `https://naturesseed.com/pasture-seed/` | `https://naturesseed.com/products/pasture-seed/` | $12,902.96 | 9502 |
| 2 | `https://naturesseed.com/pasture-seed/horse-pastures/` | `https://naturesseed.com/products/pasture-seed/horse-pastu...` | $12,535.47 | 8024 |
| 3 | `https://naturesseed.com/sale/` | `https://naturesseed.com/` | $6,110.65 | 2305 |
| 4 | `https://www.naturesseed.com/` | `https://naturesseed.com/` | $5,453.95 | 1985 |
| 5 | `https://naturesseed.com/grass-seed/clover-seeds-lawn-addi...` | `https://naturesseed.com/products/clover-seed/microclover/` | $5,139.99 | 2615 |
| 6 | `https://naturesseed.com/product/cattle-dairy-cow-pasture-...` | `https://naturesseed.com/products/pasture-seed/cattle-dair...` | $4,583.98 | 3963 |
| 7 | `https://naturesseed.com/pasture-seed/cattle-pastures/` | `https://naturesseed.com/products/pasture-seed/cattle-past...` | $3,769.26 | 4809 |
| 8 | `https://naturesseed.com/wildflower-seed/` | `https://naturesseed.com/products/wildflower-seed/` | $3,361.78 | 2635 |
| 9 | `https://naturesseed.com/pasture-seed/poultry-pastures/` | `https://naturesseed.com/products/pasture-seed/poultry-for...` | $3,232.88 | 2787 |
| 10 | `https://naturesseed.com/pasture-seed/sheep-pastures/` | `https://naturesseed.com/products/pasture-seed/sheep-pastu...` | $2,916.07 | 2283 |
| 11 | `https://naturesseed.com/grass-seed/clover-seeds-lawn-addi...` | `https://naturesseed.com/products/clover-seed/white-dutch-...` | $2,802.62 | 1921 |
| 12 | `https://naturesseed.com/pasture-seed/cattle-pastures/beef...` | `https://naturesseed.com/products/pasture-seed/cattle-past...` | $2,421.00 | 1231 |
| 13 | `https://naturesseed.com/pasture-seed/goat-pastures/` | `https://naturesseed.com/products/pasture-seed/goat-pastur...` | $2,212.23 | 2097 |
| 14 | `https://naturesseed.com/grass-seed/` | `https://naturesseed.com/products/grass-seed/` | $1,130.27 | 1832 |
| 15 | `https://www.naturesseed.com/grass-seed/clover-seeds-lawn-...` | `https://naturesseed.com/products/clover-seed/microclover/` | $979.94 | 216 |

### Top 15 Broken URL Fixes (404s with spend)

| # | Broken URL | Campaign | Spend | Clicks |
|---|----------|---------|------:|-------:|
| 1 | `https://www.naturesseed.com/big-bluestem` | US | Search | Product Ads | $304.96 | 288 |
| 2 | `https://www.naturesseed.com/kentucky-bluegrass-...` | US | Search | Product Ads | $278.31 | 119 |
| 3 | `https://www.naturesseed.com/fine-fescue-grass-s...` | US | Search | Product Ads | $179.48 | 97 |
| 4 | `https://www.naturesseed.com/crimson-clover` | US | Search | Product Ads | $90.63 | 59 |
| 5 | `https://www.naturesseed.com/cereal-rye` | US | Search | Product Ads | $48.66 | 33 |
| 6 | `https://www.naturesseed.com/bermudagrass-seed-b...` | US | Search | Product Ads | $46.85 | 37 |
| 7 | `https://www.naturesseed.com/bahia-grass-seed-blend` | US | Search | Product Ads | $41.26 | 24 |
| 8 | `https://www.naturesseed.com/little-bluestem` | US | Search | Product Ads | $41.08 | 29 |
| 9 | `https://www.naturesseed.com/annual-ryegrass` | US | Search | Product Ads | $31.73 | 18 |
| 10 | `https://www.naturesseed.com/sheep-fescue-grass` | US | Search | Product Ads | $30.18 | 21 |
| 11 | `https://www.naturesseed.com/crested-wheatgrass` | US | Search | Product Ads | $29.42 | 17 |
| 12 | `https://www.naturesseed.com/seed-aide-cover-gro...` | US | Search | Product Ads | $26.14 | 16 |
| 13 | `https://www.naturesseed.com/northeast-seed-mix` | US | Search | Product Ads | $23.17 | 12 |
| 14 | `https://www.naturesseed.com/black-eyed-susan` | US | Search | Product Ads | $22.61 | 10 |
| 15 | `https://www.naturesseed.com/alsike-clover` | US | Search | Product Ads | $20.70 | 14 |

## Redirect Pattern Mapping

These are the systematic URL structure changes that caused redirects across the site:

| Pattern | Count |
|---------|------:|
| www.naturesseed.com/{slug} --> naturesseed.com/{slug}/ (www redirect) | 78 |
| /pasture-seed/{path} --> /products/pasture-seed/{slug}/ | 9 |
| /product/{slug} --> /products/{category}/{slug}/ | 6 |
| /grass-seed/{path} --> /products/grass-seed/{slug}/ | 5 |
| Other redirect | 3 |
| Missing trailing slash: /products/grass-seed --> /products/grass-seed/ | 1 |
| /sale/ --> / (302 temporary redirect, sale page gone) | 1 |
| /wildflower-seed/ --> /products/wildflower-seed/ | 1 |

### Key Structural Changes

The site underwent a major URL restructuring:

1. **`/product/{slug}` changed to `/products/{category}/{slug}/`** -- Old WooCommerce default product URLs now use category-based paths.
2. **`/grass-seed/{subcategory}/{slug}` changed to `/products/grass-seed/{slug}/`** -- Flattened subcategory structure.
3. **`/pasture-seed/{animal}/` changed to `/products/pasture-seed/{animal}-seed/`** -- Added `-seed` suffix and moved under `/products/`.
4. **`/wildflower-seed/` changed to `/products/wildflower-seed/`** -- Added `/products/` prefix.
5. **`www.naturesseed.com` redirects to `naturesseed.com`** -- www subdomain redirect (minor, but adds latency).
6. **`/products/grass-seeds/` changed to `/products/grass-seed/`** -- Pluralization fix (seeds to seed).
7. **`/products/pasture-seeds/` changed to `/products/pasture-seed/`** -- Same pluralization fix.
8. **`/sale/` redirects to `/`** -- Sale page removed, 302 temp redirect to homepage.

### 404 URL Pattern (US | Search | Product Ads campaign)

The vast majority of 404s come from the **US | Search | Product Ads** campaign which uses the URL pattern:
`www.naturesseed.com/{product-slug}` (e.g., `www.naturesseed.com/big-bluestem`)

These URLs redirect `www` to non-www, but then land on `naturesseed.com/{slug}/` which returns 404.
The correct URLs should be `naturesseed.com/products/{category}/{slug}/`.

**Recommended action:** Pause or rebuild the US | Search | Product Ads campaign with corrected URLs. Most of these ads have $0 or minimal spend, suggesting they may already be paused or have low impressions.

## Campaigns Needing Attention

| Campaign | Redirect Spend | Redirect URLs | Error Spend | Error URLs | Total Impact |
|----------|---------------:|--------------:|------------:|-----------:|-------------:|
| Search | Pasture Seed (Broad) | ROAS | $59,021.65 | 18 | $0.00 | 0 | $59,021.65 |
| Search | Categories (Top) | ROAS | $56,306.68 | 14 | $0.00 | 0 | $56,306.68 |
| Search | Animal Seed (Broad) | ROAS | $46,099.95 | 16 | $0.00 | 0 | $46,099.95 |
| Search | Brand | ROAS | $11,686.24 | 15 | $0.00 | 2 | $11,686.24 |
| Search | Pasture | Exact | $5,607.14 | 3 | $0.00 | 0 | $5,607.14 |
| Max Conversion Value | $5,575.59 | 13 | $0.00 | 2 | $5,575.59 |
| California | Search | Best Grass Seed | $5,484.26 | 2 | $0.00 | 0 | $5,484.26 |
| Search | Lawn Seed | $2,105.70 | 6 | $0.00 | 0 | $2,105.70 |
| US | Search | Product Ads | $31.11 | 7 | $1,705.80 | 452 | $1,736.91 |
| US | Search | Microclover | $979.94 | 1 | $0.00 | 0 | $979.94 |
| US | Search | Grass Seed | $965.20 | 10 | $0.00 | 0 | $965.20 |
| Grass Seed (S) - Target ROAS of 700% | $965.20 | 9 | $0.00 | 0 | $965.20 |
| Southern States | Search | Warm-Season Grasses | $846.79 | 2 | $0.00 | 0 | $846.79 |
| Bermudagrass - Southern States (S) | $607.92 | 1 | $0.00 | 0 | $607.92 |
| Buffalograss Lawn Seed - Southern States (S) | $607.92 | 2 | $0.00 | 0 | $607.92 |
| Search | Lawn - Broad | $370.88 | 1 | $0.00 | 0 | $370.88 |
| Bahia Grass Seed (S) | $238.87 | 1 | $0.00 | 0 | $238.87 |
| Bahia Grass Seed - Southern States (S) | $238.87 | 1 | $0.00 | 0 | $238.87 |
| Remarketing | $121.64 | 13 | $0.00 | 1 | $121.64 |
| Placements (D) | $121.64 | 13 | $0.00 | 1 | $121.64 |

## Recommended Action Plan

### Immediate (This Week)

1. **Update top 5 redirecting ad URLs** -- These represent the highest spend and are easy fixes. Just update the Final URL in each ad to the destination URL (see `FINAL_url_redirect_fixes.csv`).
2. **Pause any active ads pointing to 404 URLs** -- Check `FINAL_url_404_fixes.csv` for ads with recent spend.
3. **Fix merchant feed URLs** -- Update product URLs in feed to use the new `/products/{category}/{slug}/` structure.

### Short-Term (This Month)

4. **Update ALL redirecting ad URLs** -- Work through the full `FINAL_url_redirect_fixes.csv` list.
5. **Rebuild US | Search | Product Ads campaign** -- The old `www.naturesseed.com/{slug}` URL pattern is completely broken. Rebuild with the correct `/products/{category}/{slug}/` URLs.
6. **Update `www.` prefixed URLs** -- All ads using `www.naturesseed.com` should use `naturesseed.com` instead.

### Ongoing

7. **Set up URL monitoring** -- Run this health check monthly to catch new redirects before they accumulate.
8. **Update ad templates** -- Ensure all new ads use the current URL structure.
9. **Merchant feed automation** -- Ensure the WooCommerce-to-Google feed uses canonical URLs.

## Output File Reference

| File | Description | Records |
|------|------------|--------:|
| `FINAL_url_redirect_fixes.csv` | Ad URLs that 301-redirect, sorted by spend | 34 |
| `FINAL_url_404_fixes.csv` | Ad URLs returning 404, with suggested replacements | 568 |
| `FINAL_merchant_feed_url_fixes.csv` | Merchant feed URLs with issues | 10 |
| `FINAL_url_health_summary.md` | This summary document | -- |
