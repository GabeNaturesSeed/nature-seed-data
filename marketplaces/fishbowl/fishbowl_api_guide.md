# Fishbowl API Guide

## Connection Details

- **Base URL:** `http://naturesseed.myfishbowl.com:3875`
- **Protocol:** HTTP (not HTTPS)
- **Server:** Jetty

## Authentication

### Login

```
POST /api/login
Content-Type: application/json

{
    "appName": "Postman Testing",
    "appId": 101,
    "username": "<username>",
    "password": "<password>"
}
```

Response includes a `token` field. Use this as a Bearer token for all subsequent requests.

### Using the Token

All authenticated requests require:
```
Authorization: Bearer <token>
```

Tokens expire after a period of inactivity. If you get a `401 Unauthorized`, login again to get a fresh token.

### Logout

```
POST /api/logout
Authorization: Bearer <token>
```

## Data Query Endpoint (Primary Method)

This is the most powerful and flexible way to pull data. It accepts raw SQL queries against the Fishbowl database.

```
GET /api/data-query
Authorization: Bearer <token>
Content-Type: text/plain

Body: Your SQL query as plain text
```

### Important Notes

- Method is `GET` but it sends a **body** (unusual). You must disable body pruning in Postman or use a library that allows GET with body.
- Body content type must be `text/plain`, NOT JSON.
- The SQL dialect is MySQL.
- Response is a JSON array of objects, one per row.

### Python Example

```python
import urllib.request, json

url = 'http://naturesseed.myfishbowl.com:3875/api/data-query'
query = 'SELECT p.num AS SKU FROM part p LIMIT 10;'

req = urllib.request.Request(url, data=query.encode('utf-8'), method='GET')
req.add_header('Authorization', 'Bearer <token>')
req.add_header('Content-Type', 'text/plain')

with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    for row in data:
        print(row)
```

## Key Database Tables

### Inventory & Parts

| Table | Purpose | Key Columns |
|---|---|---|
| `part` | SKUs / inventory items | `id`, `num` (SKU), `description`, `stdCost`, `upc`, `activeFlag`, `typeId` |
| `product` | Sellable products (linked to parts) | `id`, `num`, `sku`, `price`, `partId`, `description` |
| `qtyonhand` | Current inventory quantities | `partid`, `locationgroupid`, `qty` |
| `qtyinventorytotals` | Full inventory summary | `partid`, `locationgroupid`, `qtyonhand`, `qtyallocated`, `qtynotavailable`, `qtyonorder` |
| `location` | Individual locations | `id`, `name`, `locationGroupId`, `typeId` |
| `locationgroup` | Location groups (warehouses) | `id`, `name` |

### Sales Orders

| Table | Purpose | Key Columns |
|---|---|---|
| `so` | Sales order headers | `id`, `num`, `dateCreated`, `customerId`, `totalPrice`, `statusId`, `cost` |
| `soitem` | Sales order line items | `id`, `soId`, `productId`, `productNum`, `qtyOrdered`, `unitPrice`, `totalPrice`, `totalCost` |
| `sostatus` | SO status lookup | `id`, `name` |

### Purchase Orders

| Table | Purpose | Key Columns |
|---|---|---|
| `po` (via API) | Purchase order headers | Similar structure to `so` |
| `poitem` | PO line items | `id`, `partId`, `qtyOrdered`, `unitCost`, `totalCost` |

### Manufacturing

| Table | Purpose | Key Columns |
|---|---|---|
| `mo` (via API) | Manufacture orders | `id`, `num`, `statusId` |
| `moitem` | MO line items | `id`, `partId`, `qty` |

### Other Useful Tables

| Table | Purpose |
|---|---|
| `customer` | Customer records |
| `vendor` | Vendor records |
| `inventorylog` | Inventory transaction history |
| `costlayer` | Cost layers for inventory valuation |
| `partcost` | Part cost records |

## Common Queries

### Inventory by Location Group

```sql
SELECT p.num AS SKU, lg.name AS LocationGroup, qoh.qty AS QtyOnHand
FROM qtyonhand qoh
JOIN part p ON p.id = qoh.partid
JOIN locationgroup lg ON lg.id = qoh.locationgroupid
ORDER BY p.num, lg.name;
```

### Full Inventory Totals

```sql
SELECT p.num AS SKU, lg.name AS LocationGroup,
       qit.qtyonhand AS OnHand, qit.qtyallocated AS Allocated,
       qit.qtynotavailable AS NotAvailable, qit.qtyonorder AS OnOrder,
       (qit.qtyonhand - qit.qtyallocated - qit.qtynotavailable) AS Available
FROM qtyinventorytotals qit
JOIN part p ON p.id = qit.partid
JOIN locationgroup lg ON lg.id = qit.locationgroupid
ORDER BY p.num, lg.name;
```

### Sales Order Detail

```sql
SELECT so.num AS OrderNumber, so.dateCreated AS OrderDate,
       soi.productNum AS SKU, soi.description AS Description,
       soi.qtyOrdered AS Qty, soi.unitPrice AS UnitPrice,
       soi.totalPrice AS TotalPrice, p.stdCost AS StdCost
FROM so
JOIN soitem soi ON soi.soId = so.id
LEFT JOIN product pr ON pr.id = soi.productId
LEFT JOIN part p ON p.id = pr.partId
ORDER BY so.dateCreated DESC;
```

### Part / Product Lookup

```sql
SELECT p.num AS PartNum, p.description, p.stdCost, p.upc,
       pr.num AS ProductNum, pr.sku, pr.price
FROM part p
LEFT JOIN product pr ON pr.partId = p.id
WHERE p.activeFlag = 1
ORDER BY p.num;
```

### Table Discovery

```sql
SELECT DISTINCT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY
FROM INFORMATION_SCHEMA.COLUMNS
ORDER BY TABLE_NAME, ORDINAL_POSITION;
```

### Columns for a Specific Table

```sql
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = "part"
ORDER BY ORDINAL_POSITION;
```

## Table Relationships

```
part.id ←── product.partId
part.id ←── qtyonhand.partid
part.id ←── qtyinventorytotals.partid

locationgroup.id ←── qtyonhand.locationgroupid
locationgroup.id ←── qtyinventorytotals.locationgroupid
locationgroup.id ←── location.locationGroupId

so.id ←── soitem.soId
soitem.productId ──→ product.id
product.partId ──→ part.id

so.customerId ──→ customer.id
```

## REST API Endpoints (Alternative to Data Query)

These return paginated JSON but are less flexible than Data Query.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/parts/` | Search parts |
| `GET` | `/api/parts/inventory` | Get inventory for a part |
| `GET` | `/api/purchase-orders` | Search POs |
| `GET` | `/api/manufacture-orders` | Search MOs |
| `GET` | `/api/users` | Search users |
| `GET` | `/api/vendors` | Search vendors |
| `GET` | `/api/uoms` | Search units of measure |
| `POST` | `/api/import/:name` | CSV import |

## SKU Naming Convention (Nature's Seed)

- **Base SKU:** `PB-ALPACA` (product family)
- **Weight variant:** `PB-ALPACA-10-LB` (specific bag size)
- **KIT:** `PB-ALPACA-50-LB-KIT` (bundle of smaller bags)
- A KIT is made up of multiples of the smaller weight variant
- Fishbowl tracks inventory at the **weight variant** level, not the base SKU level

## Location Groups

Current location groups in use:
- **Main** — primary warehouse
- **Amazon FBA** — Amazon fulfillment inventory

## Full Schema Reference

A complete schema dump (all tables, columns, data types) is saved at:
`fishbowl_schema_discovery.csv`
