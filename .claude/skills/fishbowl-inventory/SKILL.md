# Fishbowl Inventory — Nature's Seed Warehouse Management

> Invoke this skill whenever any agent needs to work with inventory levels, warehouse stock, SKU data, or delivery time estimates.

## Connection Details (Verified March 2, 2026)

| Key | Value |
|-----|-------|
| API Endpoint | `http://naturesseed.myfishbowl.com:3875` |
| Protocol | HTTP (not HTTPS) |
| Login Endpoint | `POST /api/login` |
| Data Query | `GET /api/data-query` (SQL via body) |
| Logout | `POST /api/logout` |
| Auth Method | Login → Bearer token |
| Username | `gabe` |
| Password | `#Numb3rs!` |
| App Name | `Postman Testing` |
| App ID | `101` |
| Server Version | `25.9.20250916` (Jetty 9.4.57) |

## What Fishbowl Manages

Fishbowl is Nature's Seed's **warehouse management system (WMS)**. It is the **source of truth** for:
- Real-time inventory quantities by warehouse location
- SKU-level stock tracking
- Kit/bundle component inventory
- Warehouse bin locations

## Data Available

### Inventory by Location
- Stock quantities per warehouse
- Location codes and bin positions
- Real-time available quantity

### SKU Cross-References
- Fishbowl SKU ↔ WooCommerce SKU mapping
- Kit SKUs with component breakdowns
- Pattern: KIT SKUs contain compound identifiers

### Schema Discovery
A full schema discovery file exists at:
`/Users/gabegimenes-silva/Desktop/ClaudeProjectsLocal/fishbowl_schema_discovery.csv` (301KB)
— Contains all Fishbowl database tables and field definitions

### Generated Reports
Located in `/Users/gabegimenes-silva/Desktop/ClaudeProjectsLocal/`:
- `report1_inventory_by_location.csv` — Current stock by warehouse
- `report2_orders_detail.csv` (5.3 MB) — Full order history
- `stock_crossref.json` (16 KB) — SKU matching reference

## Integration Script: sync_delivery_time.py

**Location**: `/Users/gabegimenes-silva/Desktop/ClaudeProjectsLocal/sync_delivery_time.py`

**Purpose**: Syncs Fishbowl inventory → WooCommerce ACF `delivery_time` field

**Logic**:
1. Query Fishbowl for current stock levels
2. Check if SKU is in stock at warehouse
3. Handle KIT SKUs with pattern matching (all components must be in stock)
4. Update WooCommerce product `delivery_time` meta field
5. Rate limited: 0.3s between API calls

**Delivery Time Values**:
- In stock → "Ships in 1-2 business days"
- Low stock → "Ships in 3-5 business days"
- Out of stock → "Ships in 2-3 weeks"

## SKU Patterns

```
Simple SKUs:     PG-TRDA         (Pure Grass - Tripsacum dactyloides)
Weight variants: PB-ALPACA-10-LB (Pasture Blend - Alpaca - 10 lbs)
Kit SKUs:        CV-BGEC-50-LB-KIT (Conservation - 50lb Kit)

Prefixes:
  PG-  = Pure Grass (single species)
  PB-  = Pasture Blend
  CV-  = Conservation / Cover
  LG-  = Lawn Grass
  WF-  = Wildflower
  PA-  = Planting Aid
```

## Integration Architecture

```
                    ┌──────────────┐
                    │   Fishbowl   │
                    │  (Inventory  │
                    │   Source of  │
                    │    Truth)    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ↓            ↓            ↓
    ┌─────────────┐ ┌──────────┐ ┌──────────┐
    │ WooCommerce │ │ Walmart  │ │ Reports  │
    │ delivery_   │ │ Inventory│ │ & Demand │
    │ time field  │ │ (manual) │ │ Forecast │
    └─────────────┘ └──────────┘ └──────────┘
```

## Weight Data Management

Several scripts manage product weight accuracy between Fishbowl and WooCommerce:
- `fix_weights.py` — Corrects weight mismatches
- `populate_weights.py` — Fills missing weights
- `weight_audit.py` / `final_weight_audit.py` — Audits weight accuracy
- `final_weight_audit.csv` (40 KB) — Latest audit results

Weight accuracy is critical because shipping is weight-based:
- Free shipping up to 100 lbs
- $80/25 lbs over 100 lbs
- Flat $640 over 300 lbs

## Demand Forecasting (Advanced)

Located at `/Users/gabegimenes-silva/Desktop/CascadeProjects/Naturesseed inventory helper/`:
- Seed demand reconstruction algorithms
- Coverage rate calculations (sq ft per lb)
- SKU parsing and aliasing
- Config: `ValuesConfig.JSON`
- Templates for: `sku_weight_overrides.csv`, `coverage_to_weight_rates.csv`, `seed_code_aliases.csv`

## API Usage Pattern (Verified Working)

### Step 1: Login
```bash
curl -s -X POST "http://naturesseed.myfishbowl.com:3875/api/login" \
  -H "Content-Type: application/json" \
  -d '{"appName":"Postman Testing","appId":101,"username":"gabe","password":"#Numb3rs!"}'
# Returns: {"token": "xxx", "sessionId": "yyy", "user": {...}}
```

### Step 2: Query Data (SQL via body)
```bash
curl -s -X GET "http://naturesseed.myfishbowl.com:3875/api/data-query" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: text/plain" \
  -d "SELECT p.num AS SKU, SUM(qoh.qty) AS TotalQty FROM qtyonhand qoh JOIN part p ON p.id = qoh.partid WHERE qoh.qty > 0 GROUP BY p.num ORDER BY p.num;"
# Returns: [{"SKU":"CV-BGEC-10-LB","TotalQty":60.0}, ...]
```

### Step 3: Logout
```bash
curl -s -X POST "http://naturesseed.myfishbowl.com:3875/api/logout" \
  -H "Authorization: Bearer {token}"
```

### Python Pattern
```python
import urllib.request, json

FB_URL = "http://naturesseed.myfishbowl.com:3875"

def fb_login():
    payload = json.dumps({"appName":"Postman Testing","appId":101,"username":"gabe","password":"#Numb3rs!"}).encode()
    req = urllib.request.Request(f"{FB_URL}/api/login", data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())["token"]

def fb_query(token, sql):
    req = urllib.request.Request(f"{FB_URL}/api/data-query", data=sql.encode(), method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "text/plain")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def fb_logout(token):
    req = urllib.request.Request(f"{FB_URL}/api/logout", method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    urllib.request.urlopen(req, timeout=10)
```

### Useful SQL Queries
```sql
-- All in-stock SKUs with quantities
SELECT p.num AS SKU, SUM(qoh.qty) AS TotalQty
FROM qtyonhand qoh JOIN part p ON p.id = qoh.partid
WHERE qoh.qty > 0 GROUP BY p.num ORDER BY p.num;

-- Stock for specific SKU
SELECT p.num AS SKU, qoh.qty, l.name AS Location
FROM qtyonhand qoh
JOIN part p ON p.id = qoh.partid
JOIN location l ON l.id = qoh.locationid
WHERE p.num = 'PG-PHPR-25-LB-KIT';
```

### Sync Delivery Times (Bulk)
```bash
# Run the sync script (from ClaudeProjectsLocal/)
python3 ~/Desktop/ClaudeProjectsLocal/sync_delivery_time.py          # Full sync
python3 ~/Desktop/ClaudeProjectsLocal/sync_delivery_time.py --dry-run  # Preview
```
