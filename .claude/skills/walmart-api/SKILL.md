# Walmart Marketplace API — Nature's Seed

> Invoke this skill whenever any agent needs to work with Walmart Marketplace for product listings, orders, inventory, or pricing.

## Connection Details

| Key | Value |
|-----|-------|
| Client ID | `WALMART_CLIENT_ID` from `.env` |
| Client Secret | `WALMART_CLIENT_SECRET` from `.env` |
| Auth Endpoint | `https://marketplace.walmartapis.com/v3/token` |
| API Base | `https://marketplace.walmartapis.com/v3` |
| Auth Method | OAuth 2.0 Client Credentials |
| Content Type | `application/json` |

## Authentication Flow

Walmart uses OAuth 2.0. You must get a token before making API calls:

```bash
# Get access token
curl -X POST "https://marketplace.walmartapis.com/v3/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Accept: application/json" \
  -H "WM_SVC.NAME: Nature's Seed" \
  -H "WM_QOS.CORRELATION_ID: $(uuidgen)" \
  -d "grant_type=client_credentials" \
  --user "$WALMART_CLIENT_ID:$WALMART_CLIENT_SECRET"
```

Response:
```json
{
  "access_token": "eyJra...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

**Token expires in 15 minutes.** Cache and refresh as needed.

## Required Headers for All Requests

**IMPORTANT:** Walmart uses `WM_SEC.ACCESS_TOKEN` header, NOT `Authorization: Bearer`.

```
# For token endpoint:
Authorization: Basic base64(CLIENT_ID:CLIENT_SECRET)  ← via --user flag in curl

# For ALL other endpoints:
WM_SEC.ACCESS_TOKEN: {access_token}   ← NOT "Authorization: Bearer"!
WM_SVC.NAME: Nature's Seed
WM_QOS.CORRELATION_ID: {unique-uuid}
Accept: application/json
Content-Type: application/json
```

## Available API Endpoints

### Items (Products)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v3/items` | GET | List all items. Params: `limit`, `offset`, `lifecycleStatus` |
| `/v3/items/{sku}` | GET | Get single item by SKU |
| `/v3/items/retire` | DELETE | Retire item by SKU |
| `/v3/items` | POST | Bulk item setup (XML/JSON feed) |
| `/v3/items/search` | GET | Search items. Params: `query`, `limit` |
| `/v3/items/taxonomy` | GET | Category taxonomy |

### Inventory
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v3/inventory` | GET | Get inventory for SKU. Param: `sku` |
| `/v3/inventory` | PUT | Update inventory for SKU |
| `/v3/feeds` | POST | Bulk inventory update feed |

### Prices
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v3/prices` | PUT | Update price for SKU |
| `/v3/feeds` | POST | Bulk price update feed |

### Orders
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v3/orders` | GET | List orders. Params: `status`, `createdStartDate`, `createdEndDate`, `limit` |
| `/v3/orders/{purchaseOrderId}` | GET | Single order details |
| `/v3/orders/{purchaseOrderId}/acknowledge` | POST | Acknowledge order |
| `/v3/orders/{purchaseOrderId}/shipping` | POST | Ship order (add tracking) |
| `/v3/orders/{purchaseOrderId}/cancel` | POST | Cancel order |
| `/v3/orders/{purchaseOrderId}/refund` | POST | Refund order |

### Feeds (Bulk Operations)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v3/feeds` | POST | Submit bulk feed. Param: `feedType` |
| `/v3/feeds/{feedId}` | GET | Check feed status |
| `/v3/feeds` | GET | List all feeds |

Feed Types: `item`, `inventory`, `price`, `RETIRE_ITEM`, `MP_ITEM_MATCH`

### Reports
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v3/report/reconreport/reconFile` | GET | Reconciliation report |
| `/v3/reports/items` | GET | Item performance report |

### Returns
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v3/returns` | GET | List returns. Param: `returnOrderId`, `status` |
| `/v3/returns/{returnOrderId}/refund` | POST | Issue refund for return |

## SKU Mapping (WooCommerce → Walmart)

Nature's Seed products share the same SKU system across WooCommerce and Walmart:
- SKU format: `{PREFIX}-{SPECIES}-{WEIGHT}`
- Example: `PB-ALPACA-10-LB`
- **Same SKU used in both platforms** — this enables cross-platform inventory sync

## Python Client Pattern

```python
import requests, os, uuid, base64

class WalmartClient:
    BASE = "https://marketplace.walmartapis.com/v3"

    def __init__(self):
        self.client_id = os.getenv('WALMART_CLIENT_ID')
        self.client_secret = os.getenv('WALMART_CLIENT_SECRET')
        self._token = None

    def _get_token(self):
        r = requests.post(f"{self.BASE}/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "WM_SVC.NAME": "Nature's Seed",
                "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
            },
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret)
        )
        r.raise_for_status()
        self._token = r.json()["access_token"]
        return self._token

    def _headers(self):
        if not self._token:
            self._get_token()
        return {
            "WM_SEC.ACCESS_TOKEN": self._token,  # NOT Authorization: Bearer!
            "WM_SVC.NAME": "Nature's Seed",
            "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_items(self, limit=20, offset=0):
        r = requests.get(f"{self.BASE}/items",
            headers=self._headers(),
            params={"limit": limit, "offset": offset})
        r.raise_for_status()
        return r.json()

    def get_inventory(self, sku):
        r = requests.get(f"{self.BASE}/inventory",
            headers=self._headers(),
            params={"sku": sku})
        r.raise_for_status()
        return r.json()

    def update_inventory(self, sku, quantity):
        r = requests.put(f"{self.BASE}/inventory",
            headers=self._headers(),
            params={"sku": sku},
            json={"sku": sku, "quantity": {"unit": "EACH", "amount": quantity}})
        r.raise_for_status()
        return r.json()

    def get_orders(self, status="Created", limit=100):
        r = requests.get(f"{self.BASE}/orders",
            headers=self._headers(),
            params={"status": status, "limit": limit})
        r.raise_for_status()
        return r.json()
```

## Integration Points

```
WooCommerce Stock ──→ Walmart Inventory (sync needed)
WooCommerce Price ──→ Walmart Price (sync needed)
WooCommerce Products ──→ Walmart Item Listings (manual currently)
Walmart Orders ──→ (not yet integrated with WooCommerce)
Fishbowl ──→ Both WooCommerce & Walmart inventory
```

## Current Status (Verified March 2, 2026)

- **257 total items** listed on Walmart Marketplace
- Items have `lifecycleStatus: "ACTIVE"` with some in `STAGE` (unpublished)
- `publishedStatus` values: `PUBLISHED` (live) or `STAGE` (not yet live)
- Items use variant groups (e.g., `PGPHPR` groups weight variants)
- Orders are actively flowing (confirmed via API test)
- Inventory is tracked per-SKU with unit `EACH`
- Inventory sync is **manual** — opportunity for automation
- Price sync is **manual** — opportunity for automation
- Same SKU system as WooCommerce enables automated cross-platform sync

### Sample Live Data
```
SKU: PG-PHPR-25-LB-KIT | Timothy Grass Hay Seed | $159.99 | Stock: 40 units
SKU: PB-GRSC-50-LB-KIT | Green Screen Food Plot | $152.99 | Published
```

## Priority Automation Opportunities

1. **Inventory Sync**: Fishbowl → WooCommerce + Walmart simultaneously
2. **Price Sync**: WooCommerce price changes → Walmart
3. **Order Aggregation**: Combined order view across both platforms
4. **Product Listing Sync**: New WooCommerce products → Walmart feed
