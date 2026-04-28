# Facebook / Meta — Feed Schema (Dynamic Product Ads)

## Required Fields (Phase 3)
| Field | Notes |
|---|---|
| id | Unique product ID (WC variation SKU) |
| title | Product name (max 150 chars) |
| description | Product description (max 5000 chars) |
| availability | "in stock" / "out of stock" |
| condition | "new" |
| price | "X.XX USD" format |
| link | Product page URL |
| image_link | Primary image URL |
| brand | "Nature's Seed" |
| google_product_category | Google taxonomy ID or text |

## Recommended Fields (Phase 3)
| Field | Notes |
|---|---|
| gtin | UPC |
| additional_image_link | Up to 10 extra images |
| sale_price | "X.XX USD" if on sale |
| item_group_id | Groups variants of same parent product |

## Setup Steps (Phase 3)
1. Create Meta Business account + Catalog in Commerce Manager
2. Add `FACEBOOK_PIXEL_ID` and `FACEBOOK_CATALOG_ID` to .env
3. Use Facebook Marketing API v18+ to upload feed CSV
