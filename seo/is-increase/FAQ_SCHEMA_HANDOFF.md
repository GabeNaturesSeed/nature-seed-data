# FAQ Schema Implementation — Handoff for Theme Editor

## What This Is

Nature's Seed has 26 WooCommerce product categories, each with a FAQ section at the bottom of its description. We need `FAQPage` structured data (JSON-LD) injected into the `<head>` of each category archive page so Google can display rich FAQ snippets in search results.

## The Data

**File:** `IS-Increase/faq_schema_data.json`

This JSON file maps WooCommerce category (term) IDs to arrays of FAQ pairs:

```json
{
  "3897": [
    {
      "question": "How much pasture do I need per animal?",
      "answer": "A general guideline is two acres per horse or cow-calf pair..."
    },
    {
      "question": "When is the best time to plant pasture seed?",
      "answer": "For cool-season pasture grasses in the northern and transitional US..."
    }
  ],
  "3881": [
    ...
  ]
}
```

**26 categories, 157 total FAQ pairs.** Major categories have 8 FAQs, smaller ones have 5.

### Category ID → Name Map

| WC Term ID | Category Name | FAQ Count |
|------------|--------------|-----------|
| 4707 | All Seed | 5 |
| 4035 | California Collection | 8 |
| 4706 | Cattle Pasture Seed | 5 |
| 4688 | Clover Seed | 8 |
| 6002 | Cover Crop Seed | 8 |
| 6029 | Drought-Tolerant Seed | 5 |
| 6000 | Food Plot Seed | 8 |
| 3910 | Goat Pasture Seed | 5 |
| 3915 | Horse Pasture Seed | 8 |
| 3916 | Individual Pasture Species | 5 |
| 4618 | Lawn Alternatives | 5 |
| 3881 | Lawn Seed | 8 |
| 3896 | Native Wildflower Seed & Seed Mixes | 8 |
| 4621 | Northern Lawn | 5 |
| 4613 | Northern US Pasture Seeds & Seed Mixes | 5 |
| 3897 | Pasture Seed | 8 |
| 3889 | Planting Aids | 5 |
| 3927 | Sheep Pastures | 5 |
| 4623 | Southern Lawn | 5 |
| 4616 | Southern US Pasture Seeds & Seed Mixes | 5 |
| 3895 | Specialty Seed | 8 |
| 4617 | Sports Turf/High Traffic | 5 |
| 4614 | TWCA - Water-Wise Lawn | 5 |
| 6021 | Texas Native Grass & Wildflower Seed | 5 |
| 4622 | Transitional Lawn | 5 |
| 4615 | Transitional Zone Pasture Seeds & Seed Mixes | 5 |

## What Needs to Be Built

### 1. Store the FAQ data as a WordPress option

The FAQ data should be stored in the `wp_options` table so it can be read at render time without external files:

```php
// Option name: ns_category_faqs
// Value: JSON-decoded array keyed by term ID
// Structure: { "3897": [{"question": "...", "answer": "..."}, ...], ... }
```

**To populate it initially**, add a one-time admin function or WP-CLI command that reads the JSON and saves it:

```php
$json = file_get_contents( get_template_directory() . '/data/faq_schema_data.json' );
$faqs = json_decode( $json, true );
update_option( 'ns_category_faqs', $faqs );
```

Or store it directly in the theme as a PHP array if you prefer no database call.

### 2. Inject FAQPage JSON-LD on product category archives

Hook into `wp_head` and output the schema only on `is_product_category()` pages:

```php
add_action( 'wp_head', 'ns_inject_category_faq_schema' );

function ns_inject_category_faq_schema() {
    if ( ! is_product_category() ) {
        return;
    }

    $term = get_queried_object();
    if ( ! $term || ! isset( $term->term_id ) ) {
        return;
    }

    $all_faqs = get_option( 'ns_category_faqs', array() );
    $cat_id   = strval( $term->term_id );

    if ( empty( $all_faqs[ $cat_id ] ) ) {
        return;
    }

    $schema = array(
        '@context'   => 'https://schema.org',
        '@type'      => 'FAQPage',
        'mainEntity' => array(),
    );

    foreach ( $all_faqs[ $cat_id ] as $faq ) {
        $schema['mainEntity'][] = array(
            '@type'          => 'Question',
            'name'           => $faq['question'],
            'acceptedAnswer' => array(
                '@type' => 'Answer',
                'text'  => $faq['answer'],
            ),
        );
    }

    echo '<script type="application/ld+json">'
       . wp_json_encode( $schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE )
       . '</script>' . "\n";
}
```

### 3. Expected output in `<head>`

On `naturesseed.com/products/pasture-seed/` the output should be:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "How much pasture do I need per animal?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "A general guideline is two acres per horse or cow-calf pair on well-managed, productive pasture. Sheep and goats require roughly half an acre to one acre per animal. These numbers vary significantly based on soil fertility, annual rainfall, forage species, and whether you practice rotational grazing. Start conservative and increase stocking only after observing how your forage responds through a full growing season."
      }
    },
    {
      "@type": "Question",
      "name": "When is the best time to plant pasture seed?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "For cool-season pasture grasses..."
      }
    }
  ]
}
</script>
```

## Implementation Options (pick one)

### Option A: Theme functions.php (simplest)

1. Copy `faq_schema_data.json` into the child theme directory (e.g., `wp-content/themes/woodmart-child/data/`)
2. Add the `wp_head` hook code above to `functions.php`
3. Run the one-time option population on theme activation or via admin init

### Option B: Hardcoded PHP array (no DB call, fastest)

Convert the JSON to a PHP array and include it directly in the function. No `get_option()` call needed:

```php
function ns_get_category_faqs() {
    return array(
        '3897' => array(
            array('question' => 'How much pasture...', 'answer' => 'A general guideline...'),
            // ... more Q&A pairs
        ),
        '3881' => array(
            // ... Lawn Seed FAQs
        ),
        // ... all 26 categories
    );
}
```

### Option C: Term meta (most WordPress-native)

Store FAQ data as term meta per category:

```php
// Save
update_term_meta( 3897, 'ns_faq_schema', $faqs_array );

// Read in wp_head hook
$faqs = get_term_meta( $term->term_id, 'ns_faq_schema', true );
```

This is the cleanest approach if you want per-category management, but requires a migration script to populate all 26 categories.

## Verification

After implementing, test with:
1. **Google Rich Results Test**: https://search.google.com/test/rich-results — paste any category URL
2. **View page source**: Search for `FAQPage` in the HTML `<head>` section
3. **Schema Markup Validator**: https://validator.schema.org/

## Files Reference

| File | Purpose |
|------|---------|
| `IS-Increase/faq_schema_data.json` | Master FAQ data — 26 categories, 157 Q&A pairs |
| `IS-Increase/faq_schemas/` | Individual JSON-LD files per category (for testing) |
| `IS-Increase/faq-schema-snippet.php` | Standalone PHP snippet (alternative to theme integration) |

## Notes

- The FAQ content is already visible on each category page in the description text (below the product grid). The schema just tells Google to display it as rich snippets.
- RankMath is installed on the site — make sure the FAQ schema doesn't conflict with any RankMath auto-generated schema. You may need to disable RankMath's FAQ schema detection on product category archives.
- All category URLs use `/products/` prefix via Permalink Manager plugin (never `/product-category/`).
