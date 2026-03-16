# Crawl Budget Cleanup — Implementation Guide

## Overview

Google is wasting crawl budget on 1,450+ junk URLs instead of crawling our product and category pages. This cleanup has 4 parts:

| Task | Count | Tool | Effort |
|------|-------|------|--------|
| Remove fragment URLs from index | 211 | Google Search Console | Manual, 10 min |
| Noindex parameter/variation pages | 736 | RankMath + Theme code | Config + code |
| 301 redirect old paths | 55 | RankMath Redirections | Upload CSV |
| Canonical tags on variations | 503 | Theme code (automatic) | Code snippet |

---

## 1. Fragment URL Removal (211 URLs)

**File:** `search-console/fragment_urls_for_removal.txt`

Fragment URLs (with `#anchors`) should never be indexed separately — they're sections within a page, not standalone pages. Google is treating them as separate URLs.

### How to submit removal requests:

1. Go to [Google Search Console](https://search.google.com/search-console) → select `sc-domain:naturesseed.com`
2. Left sidebar → **Removals** → **Temporary Removals** tab
3. Click **New Request**
4. For each URL pattern, use **"Remove all URLs with this prefix"**:

**Instead of submitting 211 individual URLs, use these prefix patterns (much faster):**

| Prefix to Submit | URLs Covered |
|-----------------|-------------|
| `https://naturesseed.com/grass-seed/florida/#` | 7 |
| `https://naturesseed.com/grass-seed/new-hampshire/#` | 2 |
| `https://naturesseed.com/grass-seed/oklahoma/#` | 4 |
| `https://naturesseed.com/grass-seed/tennessee/#` | 6 |
| `https://naturesseed.com/grass-seed/washington/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/a-guide-to-grass-seed-germination/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/advantages-of-grass-seed-over-laying-sod/#` | 5 |
| `https://naturesseed.com/resources/lawn-turf/an-oldie-but-a-goodie-advantages-of-reel-mowers/#` | 3 |
| `https://naturesseed.com/resources/lawn-turf/arkansas/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/fertilizing-new-grass-seeds-and-lawn/#` | 7 |
| `https://naturesseed.com/resources/lawn-turf/florida/#` | 7 |
| `https://naturesseed.com/resources/lawn-turf/georgia/#` | 7 |
| `https://naturesseed.com/resources/lawn-turf/how-long-does-it-take-grass-to-grow/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/how-much-sun-does-a-perennial-ryegrass-seed-lawn-require/#` | 3 |
| `https://naturesseed.com/resources/lawn-turf/how-often-should-you-water-new-grass-seed/#` | 5 |
| `https://naturesseed.com/resources/lawn-turf/how-to-choose-the-right-grass-seed/#` | 10 |
| `https://naturesseed.com/resources/lawn-turf/how-to-fertilize-your-new-bermudagrass-seed-lawn/#` | 3 |
| `https://naturesseed.com/resources/lawn-turf/how-to-make-a-putting-green-in-your-yard/#` | 3 |
| `https://naturesseed.com/resources/lawn-turf/how-to-plant-and-grow-st-augustine-grass-seed/#` | 2 |
| `https://naturesseed.com/resources/lawn-turf/how-to-re-seed-your-perennial-ryegrass-lawn/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/identifying-5-common-lawn-grass-species/#` | 6 |
| `https://naturesseed.com/resources/lawn-turf/indiana/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/iowa/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/louisiana/#` | 5 |
| `https://naturesseed.com/resources/lawn-turf/maryland/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/massachusetts/#` | 3 |
| `https://naturesseed.com/resources/lawn-turf/minnesota/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/mississippi/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/missouri/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/montana/#` | 3 |
| `https://naturesseed.com/resources/lawn-turf/more-than-luck-why-you-should-add-clover-to-your-lawn-grass/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/nevada/#` | 3 |
| `https://naturesseed.com/resources/lawn-turf/new-hampshire/#` | 2 |
| `https://naturesseed.com/resources/lawn-turf/new-mexico/#` | 3 |
| `https://naturesseed.com/resources/lawn-turf/ohio/#` | 3 |
| `https://naturesseed.com/resources/lawn-turf/oklahoma/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/oregon/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/overseeding-lawn-101/#` | 5 |
| `https://naturesseed.com/resources/lawn-turf/pennsylvania/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/rhode-island/#` | 5 |
| `https://naturesseed.com/resources/lawn-turf/south-carolina/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/tennessee/#` | 6 |
| `https://naturesseed.com/resources/lawn-turf/texas/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/utah/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/washington/#` | 4 |
| `https://naturesseed.com/resources/lawn-turf/west-virginia/#` | 4 |
| `https://naturesseed.com/resources/news-and-misc/states-with-most-flooding/#` | 4 |
| `https://naturesseed.com/resources/wildlife-habitat-sustainability/firewheel-a-native-wildflower-favorite-rich-in-legend-lore/#` | 3 |
| `https://naturesseed.com/resources/wildlife-habitat-sustainability/peaceful-coexistence-keeping-deer-from-eating-your-wildflowers/#` | 3 |
| `https://naturesseed.com/resources/wildlife-habitat-sustainability/using-vinegar-to-kill-weeds-in-the-lawn-and-garden/#` | 3 |

That's ~50 prefix removal requests covering all 211 fragment URLs.

**Note:** These are temporary removals (6 months). The permanent fix is the theme code in Section 4 which prevents Google from indexing fragments in the future.

---

## 2. Noindex Parameter/Variation Pages (736 URLs)

**File:** `search-console/parameter_urls_for_noindex.txt`

These are URLs with query parameters like `?per_page=`, `?filter_`, `?gclid=`, `?fbclid=`, `?attribute_`, `?variation_id=`, `?page=`, `?shop_view=`, etc.

### Option A: RankMath Settings (handles most cases)

1. Go to **WordPress Admin → Rank Math → General Settings → Links**
2. Scroll to **"Strip Category Base"** and related URL settings
3. Go to **Rank Math → General Settings → Others**
4. Find **"Noindex Empty Category and Tag Archives"** → Enable

### Option B: RankMath URL Inspection (per-URL, not scalable)

RankMath doesn't have a bulk "noindex all parameter URLs" setting. For this volume, we need theme code.

### Option C: Theme Code (RECOMMENDED — handles all cases)

**Send this to the theme editor Claude Code:**

Add to the child theme's `functions.php` — this automatically adds `noindex, nofollow` to any URL with query parameters that shouldn't be indexed:

```php
/**
 * Noindex all URLs with query parameters that indicate
 * filtered/paginated/parameterized views.
 *
 * This prevents Google from indexing:
 * - ?per_page=, ?per_row=, ?shop_view= (WooCommerce grid settings)
 * - ?filter_ (product filters)
 * - ?gclid=, ?fbclid=, ?utm_ (tracking parameters)
 * - ?attribute_pa_, ?variation_id= (product variations)
 * - ?page_id= (WordPress page IDs)
 * - ?post_type= (post type queries)
 */
add_action( 'wp_head', 'ns_noindex_parameter_urls', 1 );

function ns_noindex_parameter_urls() {
    // Only act if there are query parameters
    if ( empty( $_SERVER['QUERY_STRING'] ) ) {
        return;
    }

    $query_string = $_SERVER['QUERY_STRING'];

    // Parameters that should trigger noindex
    $noindex_params = array(
        'per_page',
        'per_row',
        'shop_view',
        'filter_',
        'gclid',
        'gbraid',
        'gad_source',
        'gad_campaignid',
        'fbclid',
        'utm_',
        'attribute_pa_',
        'variation_id',
        'page_id',
        'post_type',
    );

    foreach ( $noindex_params as $param ) {
        if ( strpos( $query_string, $param ) !== false ) {
            echo '<meta name="robots" content="noindex, nofollow">' . "\n";
            return;
        }
    }
}
```

### Also: Tell Google to ignore URL parameters

1. Go to **Google Search Console** → **Settings** → **Crawl Stats** (no longer available directly, but...)
2. **Better approach**: Add to `robots.txt`:

```
# Block parameter URLs from crawling
Disallow: /*?per_page=
Disallow: /*?per_row=
Disallow: /*?shop_view=
Disallow: /*?filter_
Disallow: /*?gclid=
Disallow: /*?gbraid=
Disallow: /*?gad_source=
Disallow: /*?fbclid=
Disallow: /*?utm_
Disallow: /*?attribute_pa_
Disallow: /*?variation_id=
Disallow: /*?page_id=
Disallow: /*?post_type=
```

RankMath can manage `robots.txt`: **Rank Math → General Settings → Edit robots.txt** → add the lines above.

---

## 3. 301 Redirects (55 old paths → new /products/ paths)

**File:** `search-console/301_redirects_for_rankmath.csv`

### How to upload into RankMath:

1. Go to **WordPress Admin → Rank Math → Redirections**
2. Click **Import/Export** (top right)
3. Click **Import** tab
4. Choose **CSV** format
5. Upload `301_redirects_for_rankmath.csv`
6. RankMath expects columns: `source`, `destination` (which is how the CSV is formatted)
7. Click **Import**
8. Verify the redirects appear in the list

### If RankMath import doesn't match the column format:

RankMath's CSV import expects these exact headers:
```
id,source,matching,destination,type,category,status
```

If needed, use this expanded format — save as `301_redirects_rankmath_full.csv`:
```
id,source,matching,destination,type,category,status
,/grass-seed,exact,/products/grass-seed,301,,active
,/grass-seed/bermuda-grass,exact,/products/grass-seed/bermuda-grass,301,,active
...
```

I've included both formats in the files.

### Key redirects (highest traffic):

| Source | Destination | Why |
|--------|------------|-----|
| `/grass-seed/` | `/products/grass-seed/` | Old Magento path → WC path |
| `/grass-seed/bermuda-grass` | `/products/grass-seed/bermuda-grass` | Species page |
| `/grass-seed/buffalograss/` | `/products/grass-seed/buffalograss/` | Species page |
| `/grass-seed/california/` | `/products/california-seeds/` | Regional → proper category |
| `/grass-seed/clover-seeds-lawn-additive/` | `/products/clover-seed/` | Product moved |
| `/california-seeds/` (with params) | `/products/california-seeds/` | Old path |
| `/clover-seed-planting-instructions/` | `/resources/lawn-turf/clover-seed-planting-instructions/` | Old path |
| `/pasture-seed/*` | `/products/pasture-seed/*` | Old Magento paths |

---

## 4. Canonical Tags on Product Variations (503 URLs)

**File:** `search-console/canonical_urls_needed.csv`

Product variation URLs (with `?attribute_pa_size=10-lb` etc.) need a canonical tag pointing to the parent product URL. This tells Google "this is the same page, just a different variant."

### Option A: RankMath handles this automatically (check settings)

1. Go to **Rank Math → Titles & Meta → Products**
2. Ensure **"Canonical URL"** is not overridden
3. RankMath should automatically set the canonical to the clean URL

**Test:** View source on any product page with a variation selected (e.g., `naturesseed.com/products/grass-seed/some-product/?attribute_pa_size=10-lb`) and look for:
```html
<link rel="canonical" href="https://naturesseed.com/products/grass-seed/some-product/" />
```

If it's pointing to the clean URL, RankMath is handling it. If it includes the query params, we need the theme code below.

### Option B: Theme Code (if RankMath isn't handling it)

**Send to theme editor Claude Code:**

```php
/**
 * Force canonical URLs to strip query parameters on product pages.
 * This prevents Google from treating ?attribute_pa_size=X and
 * ?variation_id=Y as separate pages.
 */
add_filter( 'rank_math/frontend/canonical', 'ns_clean_product_canonical' );

function ns_clean_product_canonical( $canonical ) {
    if ( is_product() ) {
        // Strip all query parameters — canonical should always be the clean URL
        $canonical = strtok( $canonical, '?' );
    }
    return $canonical;
}

/**
 * Also handle non-product pages with tracking params.
 * Strip gclid, fbclid, utm_, etc. from canonicals everywhere.
 */
add_filter( 'rank_math/frontend/canonical', 'ns_strip_tracking_from_canonical' );

function ns_strip_tracking_from_canonical( $canonical ) {
    if ( strpos( $canonical, '?' ) === false ) {
        return $canonical;
    }

    $parsed = wp_parse_url( $canonical );
    if ( empty( $parsed['query'] ) ) {
        return $canonical;
    }

    parse_str( $parsed['query'], $params );

    // Remove tracking and filter parameters
    $strip_prefixes = array( 'gclid', 'gbraid', 'gad_', 'fbclid', 'utm_', 'per_page', 'per_row', 'shop_view', 'filter_', 'post_type', 'page_id' );

    foreach ( array_keys( $params ) as $key ) {
        foreach ( $strip_prefixes as $prefix ) {
            if ( strpos( $key, $prefix ) === 0 ) {
                unset( $params[ $key ] );
            }
        }
    }

    // Rebuild URL without stripped params
    $clean = $parsed['scheme'] . '://' . $parsed['host'] . $parsed['path'];
    if ( ! empty( $params ) ) {
        $clean .= '?' . http_build_query( $params );
    }

    return $clean;
}
```

---

## Theme Editor Handoff Summary

**Send these 3 code snippets to the theme editor Claude Code:**

1. **Noindex parameter URLs** (Section 2, Option C) — `ns_noindex_parameter_urls()`
2. **Clean product canonicals** (Section 4, Option B) — `ns_clean_product_canonical()`
3. **Strip tracking from canonicals** (Section 4, Option B) — `ns_strip_tracking_from_canonical()`

All three go in the child theme's `functions.php` or can be added via the Code Snippets plugin.

---

## Verification Checklist

After implementing:

- [ ] Check 3 fragment URLs in GSC → should show "URL is not on Google" within 1-2 days
- [ ] View source on a parameterized URL → should see `<meta name="robots" content="noindex, nofollow">`
- [ ] Test a redirect: visit `/grass-seed/` → should 301 to `/products/grass-seed/`
- [ ] View source on a product variation URL → canonical should point to clean parent URL
- [ ] Check `robots.txt` at `naturesseed.com/robots.txt` → should include the Disallow rules
- [ ] Run Google Rich Results Test on a category page → should show FAQ schema (from the separate FAQ handoff)

---

## Files Generated

| File | Purpose |
|------|---------|
| `search-console/fragment_urls_for_removal.txt` | 211 URLs to submit for removal in GSC |
| `search-console/parameter_urls_for_noindex.txt` | 736 parameter URLs (reference) |
| `search-console/301_redirects_for_rankmath.csv` | 55 redirects: `source,destination` for RankMath import |
| `search-console/canonical_urls_needed.csv` | 503 variation URLs needing canonical tags |
