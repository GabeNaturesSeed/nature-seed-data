# Walmart Marketplace — Feed Schema

## Required Fields (quality check fails without these)
| Field | Notes |
|---|---|
| sku | Must match WC SKU exactly |
| price | USD decimal string |
| name | Product title (max 200 chars) |
| short_description | Shelf description |
| main_image_url | Primary image URL |
| stock_status | instock / outofstock |

## Recommended Fields (Phase 2 — completeness score)
| Field | Notes |
|---|---|
| long_description | Full product description |
| brand | "Nature's Seed" |
| category | Walmart taxonomy category |
| weight | Shipping weight |
| gtin | UPC/EAN |
| shelf_description | Additional shelf copy |
| secondary_image_urls | Additional product images |
| key_features | Bullet points (up to 5) |

## API Notes
- Token header: `WM_SEC.ACCESS_TOKEN` (NOT `Authorization: Bearer`)
- Token expires: 15 minutes
- Rate limit: 0.5s between calls
- 404 on /items = no items listed (not an error)
