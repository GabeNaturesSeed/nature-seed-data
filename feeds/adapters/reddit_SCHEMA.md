# Reddit Ads — Feed Schema

## Required Fields
| Field | Notes |
|---|---|
| sku | id — maps to WC variation SKU |
| name | title (max 150 chars) |
| price | "USD X.XX" format |
| main_image_url | image_link |

## Recommended Fields (Phase 2)
| Field | Notes |
|---|---|
| description | max 1000 chars |
| availability | "in stock" / "out of stock" |
| brand | "Nature's Seed" |
| product_type | Full category path |

## Notes
- Catalog built by separate reddit-ads agent at `docs/reddit-catalog/reddit_catalog.csv`
- Audit is file-based (no API call) — just compares CSV against feed_master
- Phase 3: wire up catalog upload to Reddit Ads API
