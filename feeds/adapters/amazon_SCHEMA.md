# Amazon — Feed Schema

## Required Fields
| Field | Notes |
|---|---|
| sku | Seller SKU (must match WC SKU via channel_sku_map) |
| name | Product title (max 200 chars) |
| price | USD decimal string |
| main_image_url | Primary image (white background preferred) |
| brand | "Nature's Seed" |

## Recommended Fields (Phase 2)
| Field | Notes |
|---|---|
| bullet_points | 3–5 bullet points (each < 500 chars) |
| description | Product description (< 2000 chars) |
| gtin | UPC — required for GTIN-based matching |
| search_terms | Backend keywords (< 250 chars per field) |
| material_type | e.g. "Grass Seed" |
| item_form | e.g. "Pellets", "Seeds" |
| product_type_name | Amazon browse node category |

## API Notes
- SP-API LWA OAuth (refresh token flow)
- Catalog Items API: `GET /catalog/2022-04-01/items`
- SKU aliases live in channel_sku_map.json under "amazon" key
- Content writes use Listings API (draft submissions only — requires Gabe approval)
