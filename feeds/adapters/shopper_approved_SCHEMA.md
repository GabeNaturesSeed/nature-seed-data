# Shopper Approved — Feed Schema

## Required Fields
| Field | Notes |
|---|---|
| sku | product_id — matched to WC SKU via parent SKU extraction |
| name | Product name |
| url | Product page URL |

## Recommended Fields (Phase 2)
| Field | Notes |
|---|---|
| gtin | For Google Product Reviews XML matching |
| mpn | Manufacturer part number |
| brand | "Nature's Seed" |
| review_count | Useful for coverage audit |

## API Notes
- SA_SITE_ID: 33157
- Review feed output: `docs/reviews/product_reviews.xml` (GitHub Pages)
- Coverage audit = all WC products should have at least 1 review indexed
