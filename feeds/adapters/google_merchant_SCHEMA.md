# Google Merchant Center — Feed Schema

## Required Fields (suppression risk without these)
| Field | Notes |
|---|---|
| sku | offerId — must be unique per variant |
| name | title (max 150 chars) |
| price | USD with currency code |
| gtin | UPC/EAN — required for Shopping ads |
| brand | "Nature's Seed" |
| main_image_url | Primary image (min 100x100px) |
| description | Product description |

## Recommended Fields (Phase 2)
| Field | Notes |
|---|---|
| product_type | Full category path (e.g. "Lawn > Grass Seed > Cool Season") |
| additional_image_links | Up to 10 additional images |
| custom_label_0–4 | Campaign segmentation labels |
| shipping_weight | Weight for shipping cost calculation |
| condition | "new" |

## API Notes
- Read-only currently (Content API v2.1)
- Merchant ID: 138935850
- Uses shared Google refresh token (same as Ads + GA4)
- GTIN missing = suppression from Shopping — highest priority quality fix
