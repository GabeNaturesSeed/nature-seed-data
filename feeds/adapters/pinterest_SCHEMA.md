# Pinterest — Feed Schema

## Required Fields (Phase 3)
| Field | Notes |
|---|---|
| id | Unique product ID |
| title | Product name |
| description | Product description |
| link | Product page URL |
| image_link | Primary image URL |
| price | "X.XX USD" |
| availability | "in stock" / "out of stock" |

## Recommended Fields (Phase 3)
| Field | Notes |
|---|---|
| additional_image_link | Up to 10 extra images |
| brand | "Nature's Seed" |
| google_product_category | Google taxonomy |
| condition | "new" |
| item_group_id | Groups variants |
| gtin | UPC |

## Setup Steps (Phase 3)
1. Create Pinterest Business account + Catalog
2. Add `PINTEREST_ACCESS_TOKEN` to .env
3. Use Pinterest API v5 Catalogs endpoint to upload feed
4. Wire up `pinterest.py` adapter to API
