# Klaviyo — Feed Schema (Catalog Items)

## Required Fields
| Field | Notes |
|---|---|
| sku | external_id — maps to WC SKU |
| name | title |
| price | Decimal (used in dynamic email blocks) |
| main_image_url | image_full_url |
| url | Product page URL — MUST use /products/ path (Permalink Manager) |

## Recommended Fields (Phase 2)
| Field | Notes |
|---|---|
| description | Product description for email rendering |
| categories | For segmentation and browse abandonment flows |
| custom_metadata | Any extra fields for personalization |

## API Notes
- Revision: `2024-07-15`
- Catalog items endpoint: `GET /api/catalog-items`
- Rate limit: 0.3s between calls
- URL rule: NEVER /product-category/ — always /products/
