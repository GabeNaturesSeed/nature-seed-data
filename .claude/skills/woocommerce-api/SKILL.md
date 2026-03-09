# WooCommerce API — Nature's Seed (naturesseed.com)

> Invoke this skill whenever any agent needs to read/write product, order, customer, coupon, or shipping data from the Nature's Seed WooCommerce store.

## Connection Details

| Key | Value |
|-----|-------|
| Base URL | `https://naturesseed.com/wp-json/wc/v3` |
| Store API | `https://naturesseed.com/wp-json/wc/store/v1` |
| Auth | Basic Auth — `WC_CK` + `WC_CS` from `.env` |
| Rate Limit | 0.3s between calls for bulk ops |
| Pagination | `per_page` (max 100), `page` param; total in `X-WP-Total` / `X-WP-TotalPages` headers |

## Two APIs — When to Use Which

### REST API v3 (Authenticated, Server-Only)
Use for **admin/backend operations**: creating products, reading orders, managing customers, updating inventory, coupons, shipping, settings.
```
GET/POST/PUT/DELETE https://naturesseed.com/wp-json/wc/v3/{endpoint}
Authorization: Basic base64(CK:CS)
```

### Store API v1 (Public, Cart-Token)
Use for **storefront operations**: browsing products, cart management, checkout.
```
GET/POST https://naturesseed.com/wp-json/wc/store/v1/{endpoint}
Cart-Token: {token}   ← required for cart/checkout
```

## Available REST API v3 Endpoints

### Products
| Endpoint | Methods | Notes |
|----------|---------|-------|
| `/products` | GET, POST | List/create. Filters: `status`, `category`, `sku`, `search`, `tag` |
| `/products/{id}` | GET, PUT, DELETE | Single product CRUD |
| `/products/batch` | POST | Bulk create/update/delete |
| `/products/{id}/variations` | GET, POST | Variable product variants |
| `/products/{id}/variations/{vid}` | GET, PUT, DELETE | Single variation |
| `/products/{id}/variations/batch` | POST | Bulk variation ops |
| `/products/{id}/duplicate` | POST | Clone a product |
| `/products/categories` | GET, POST | Category tree |
| `/products/categories/{id}` | GET, PUT, DELETE | Single category |
| `/products/tags` | GET, POST | Product tags |
| `/products/attributes` | GET, POST | Global attributes (e.g. Size) |
| `/products/attributes/{id}/terms` | GET, POST | Attribute values |
| `/products/brands` | GET, POST | Brand taxonomy |
| `/products/reviews` | GET, POST | Customer reviews |
| `/products/shipping_classes` | GET, POST | Shipping classes |

### Orders
| Endpoint | Methods | Notes |
|----------|---------|-------|
| `/orders` | GET, POST | List/create orders. Filters: `status`, `customer`, `after`, `before` |
| `/orders/{id}` | GET, PUT, DELETE | Single order |
| `/orders/batch` | POST | Bulk ops |
| `/orders/{id}/notes` | GET, POST | Order notes |
| `/orders/{id}/refunds` | GET, POST | Refunds |
| `/orders/{id}/shipment-trackings` | GET, POST | Shipment tracking |
| `/orders/statuses` | GET | All order statuses |
| `/refunds` | GET | All refunds across orders |

### Customers
| Endpoint | Methods | Notes |
|----------|---------|-------|
| `/customers` | GET, POST | List/create. Filters: `email`, `role` |
| `/customers/{id}` | GET, PUT, DELETE | Single customer |
| `/customers/{id}/downloads` | GET | Customer downloads |

### Coupons
| Endpoint | Methods | Notes |
|----------|---------|-------|
| `/coupons` | GET, POST | List/create |
| `/coupons/{id}` | GET, PUT, DELETE | Single coupon |

### Shipping
| Endpoint | Methods | Notes |
|----------|---------|-------|
| `/shipping/zones` | GET, POST | Shipping zones |
| `/shipping/zones/{id}/methods` | GET, POST | Zone methods |
| `/shipping_methods` | GET | Available methods |

### Reports
| Endpoint | Methods | Notes |
|----------|---------|-------|
| `/reports/sales` | GET | Sales reports. Params: `date_min`, `date_max`, `period` |
| `/reports/top_sellers` | GET | Top selling products |
| `/reports/orders/totals` | GET | Order count by status |
| `/reports/products/totals` | GET | Product count by type |
| `/reports/customers/totals` | GET | Customer count by role |
| `/reports/coupons/totals` | GET | Coupon usage stats |

### Settings & System
| Endpoint | Methods | Notes |
|----------|---------|-------|
| `/settings` | GET | All setting groups |
| `/settings/{group}` | GET | Group settings |
| `/settings/{group}/{id}` | GET, PUT | Individual setting |
| `/taxes` | GET, POST | Tax rates |
| `/taxes/classes` | GET, POST | Tax classes |
| `/payment_gateways` | GET | Payment methods |
| `/system_status` | GET | Full system info |
| `/webhooks` | GET, POST | Webhook management |
| `/data/countries` | GET | Country/state data |
| `/data/currencies` | GET | Currency data |

### Stripe (via WC Stripe plugin)
| Endpoint | Methods | Notes |
|----------|---------|-------|
| `/wc_stripe/account` | GET | Stripe account info |
| `/wc_stripe/settings` | GET, POST | Stripe config |

### Other
| Endpoint | Methods | Notes |
|----------|---------|-------|
| `/back-in-stock/notifications/deactivate` | POST | BIS notification mgmt |

## Product Data Structure (Key Fields)

```json
{
  "id": 462298,
  "name": "Product Name",
  "slug": "product-slug",
  "type": "simple|variable|grouped|external",
  "status": "publish|draft|pending|private",
  "sku": "PG-TRDA",
  "price": "29.99",
  "regular_price": "29.99",
  "sale_price": "",
  "manage_stock": true,
  "stock_quantity": 50,
  "weight": "10",
  "categories": [{"id": 3881, "name": "Lawn Seed", "slug": "products-grass-seed"}],
  "attributes": [{"name": "Size", "options": ["5 lb", "10 lb", "25 lb"]}],
  "images": [{"src": "url", "alt": ""}],
  "meta_data": [{"key": "delivery_time", "value": "Ships in 1-2 days"}]
}
```

## Category Tree (Current)

```
Root Categories:
├── All Seed (id:4707, 87 products)
├── Lawn Seed (id:3881, 17 products)
│   ├── Lawn Alternatives (id:4618)
│   ├── Northern Lawn (id:4621, 8)
│   ├── Southern Lawn (id:4623, 1)
│   ├── Transitional Lawn (id:4622, 4)
│   ├── TWCA - Water-Wise Lawn (id:4614, 5)
│   └── Sports Turf/High Traffic (id:4617, 6)
├── Pasture Seed (id:3897, 41 products)
│   ├── Northern US Pasture (id:4613, 20)
│   ├── Southern US Pasture (id:4616, 18)
│   ├── Transitional Zone Pasture (id:4615, 18)
│   ├── Horse Pasture (id:3915, 3)
│   ├── Cattle Pasture (id:4706, 2)
│   ├── Goat Pasture (id:3910, 1)
│   ├── Sheep Pastures (id:3927, 3)
│   └── Individual Pasture Species (id:3916, 12)
├── Native Wildflower Seed (id:3896, 22 products)
├── California Collection (id:4035, 24 products)
├── Clover Seed (id:4688, 6 products)
├── Specialty Seed (id:3895, 34 products)
│   ├── Food Plot Seed (id:6000, 9)
│   └── Cover Crop Seed (id:6002, 11)
├── Planting Aids (id:3889, 5 products)
└── Uncategorized (id:6015, 0)
```

## ACF Custom Fields in Use

| Meta Key | Purpose | Synced From |
|----------|---------|-------------|
| `delivery_time` | Estimated shipping time | Fishbowl inventory via `sync_delivery_time.py` |

## Shipping Rules (Current Config)

- **Free shipping** for orders up to 100 lbs
- **$80 per 25 lbs** over 100 lbs
- **Flat $640** for orders above 300 lbs
- Weight-based — products require accurate `weight` field

## Integration Points

```
Fishbowl → sync_delivery_time.py → WC meta_data[delivery_time]
WooCommerce Orders → Klaviyo "Placed Order" metric (VLbLXB)
WooCommerce → Next.js Storefront (headless via Store API)
WooCommerce → Stripe (payment processing)
WooCommerce → Walmart (manual product sync)
```

## Common curl Patterns

```bash
# List published products
curl -s -u "$WC_CK:$WC_CS" "$WC_BASE_URL/products?status=publish&per_page=100"

# Get single product
curl -s -u "$WC_CK:$WC_CS" "$WC_BASE_URL/products/{id}"

# Update product stock
curl -s -X PUT -u "$WC_CK:$WC_CS" "$WC_BASE_URL/products/{id}" \
  -H "Content-Type: application/json" \
  -d '{"stock_quantity": 50, "manage_stock": true}'

# List orders (last 30 days)
curl -s -u "$WC_CK:$WC_CS" "$WC_BASE_URL/orders?after=$(date -v-30d +%Y-%m-%dT00:00:00)&per_page=100"

# Search products by SKU
curl -s -u "$WC_CK:$WC_CS" "$WC_BASE_URL/products?sku=PG-TRDA"

# Get sales report
curl -s -u "$WC_CK:$WC_CS" "$WC_BASE_URL/reports/sales?date_min=2026-01-01&date_max=2026-03-01"
```

## Python Client Pattern (from existing scripts)

```python
import requests, os, time

WC_BASE = os.getenv('WC_BASE_URL', 'https://naturesseed.com/wp-json/wc/v3')
WC_AUTH = (os.getenv('WC_CK'), os.getenv('WC_CS'))

def wc_get(endpoint, params=None):
    r = requests.get(f"{WC_BASE}/{endpoint}", auth=WC_AUTH, params=params)
    r.raise_for_status()
    return r.json()

def wc_put(endpoint, data):
    r = requests.put(f"{WC_BASE}/{endpoint}", auth=WC_AUTH, json=data)
    r.raise_for_status()
    return r.json()

def wc_get_all(endpoint, params=None):
    """Paginate through all results"""
    params = params or {}
    params['per_page'] = 100
    page = 1
    all_items = []
    while True:
        params['page'] = page
        items = wc_get(endpoint, params)
        if not items:
            break
        all_items.extend(items)
        page += 1
        time.sleep(0.3)  # rate limit
    return all_items
```

## Storefront Integration (Next.js)

The headless storefront at `woodmart2:16-ClaudeWork/` uses:
- **Store API v1** for public product browsing (no auth needed)
- **REST API v3** for authenticated server-side ops (variations, reviews)
- **Cart-Token** flow for cart/checkout session management
- Client file: `lib/wc-client.ts` (371 lines)
- Types: `types/woocommerce.ts`
