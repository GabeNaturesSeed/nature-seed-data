# WooCommerce Product Creation — Nature's Seed

> Follow this skill for any task that creates or rebuilds product pages on naturesseed.com via the WooCommerce REST API.

---

## Base URL & Auth

```
Base URL: https://naturesseed.com/wp-json/wc/v3
Auth: Consumer Key + Consumer Secret from .env (WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
Always add cache-busting: params={"_": int(time.time())}
CF Worker proxy: set CF_WORKER_URL + CF_WORKER_SECRET in .env — auto-routes via proxy when set
```

---

## Order of Operations (NON-NEGOTIABLE — skipping or reordering causes silent failures)

### Step 1 — Create Parent Product (POST, no meta, no SKU)

```python
POST /products
{"name": "...", "type": "variable", "status": "draft"}
```

- **Never include `meta_data` on initial POST** — WC silently drops it
- **Never include `sku` on initial POST if there's any chance the SKU exists** in the lookup table (even from a deleted product). Add SKU via separate PUT:
  ```python
  api("put", f"products/{pid}", {"sku": "YOUR-SKU"})
  ```
- Error `woocommerce_rest_product_not_created` + "already present in the lookup table" = SKU conflict — create without SKU first, add via PUT

### Step 2 — Add the "new" Tag

```python
api("put", f"products/{pid}", {"tags": [{"name": "new"}]})
```

**Without "new" tag → ACF fields will NOT appear in WP Admin editor.** This tag triggers ACF field group visibility rules.

### Step 3 — Push ACF Meta Fields (Two-Step Pattern)

ACF meta requires GET-then-PUT with IDs:

```python
# Step 1: Get existing meta IDs
product = api("get", f"products/{pid}")
existing_meta = {m["key"]: m["id"] for m in product.get("meta_data", [])}

# Step 2: Build update array
meta_data = []
for key, value in acf_fields.items():
    if key in existing_meta:
        meta_data.append({"id": existing_meta[key], "key": key, "value": value})
    else:
        meta_data.append({"key": key, "value": value})

api("put", f"products/{pid}", {"meta_data": meta_data})
```

**Every ACF field has TWO entries:**
- Value field: `allowed_zip_codes` → the actual value
- Reference field: `_allowed_zip_codes` → `field_684b4e3679784`

Both must be set or ACF won't recognize the field in the editor.

### Step 4 — Create Variations

#### 4a — Delete Existing Variations (if rebuilding)
```python
existing = api("get", f"products/{pid}/variations", params_extra={"per_page": "100"})
for v in existing:
    api("delete", f"products/{pid}/variations/{v['id']}", params_extra={"force": "true"})
```

#### 4b — Clear Attributes + Cycle Product Type (REQUIRED for WP Admin visibility)
```python
api("put", f"products/{pid}", {"attributes": []})
api("put", f"products/{pid}", {"type": "simple"})   # cycle triggers lookup table rebuild
api("put", f"products/{pid}", {"type": "variable"})
api("put", f"products/{pid}", {
    "attributes": [{
        "name": "Size", "slug": "size", "position": 0,
        "visible": True, "variation": True,
        "options": ["5 lb", "10 lb", "25 lb"],  # smallest → largest
    }]
})
```

WC CLAUDE.md rule: **Always list Size options smallest-to-largest** and set `default_attributes` to the smallest variant.

#### 4c — Create Each Variation
```python
body = {
    "status": "publish",
    "attributes": [{"name": "Size", "option": "5 lb"}],
    "weight": "5",
    "regular_price": "39.99",
    "manage_stock": False,
}
vresult = api("post", f"products/{pid}/variations", body)
vid = vresult["id"]
api("put", f"products/{pid}/variations/{vid}", {"sku": "WB-TEXN-5-LB"})
```

SKU naming: smallest size has no -KIT suffix (`WB-TEXN-5-LB`), larger sizes get -KIT (`WB-TEXN-10-LB-KIT`).

If `product_type_mismatch` error → **Setary plugin is intercepting**. Deactivate Setary, create variations, reactivate.

#### 4d — Force Parent Save
```python
api("put", f"products/{pid}", {"type": "variable", "catalog_visibility": "visible"})
```

### Step 5 — Set Product-Level ACF Fields

After variations exist, set these on the parent:

#### delivery_time
```python
{"key": "delivery_time", "value": "19"}
```

#### price_per_lb_1, price_per_lb_2, price_per_lb_3
Calculate as `price / weight_lbs` for each variation. Sort **most expensive first** (smallest size = highest $/lb):
```python
# 5 lb @ $39.99 = $7.998/lb, 10 lb @ $69.99 = $6.999/lb, 25 lb @ $149.99 = $5.999/lb
# Sorted descending:
{"key": "price_per_lb_1", "value": "7.998"},
{"key": "price_per_lb_2", "value": "6.999"},
{"key": "price_per_lb_3", "value": "5.999"},
```

#### allowed_zip_codes (Zone-Based)
Use saved zone files (reusable, no API call needed):
- `zone_to_zips.json` — Zone number → zip array
- `zip_to_zone.json` — Zip → zone

```python
{"key": "allowed_zip_codes", "value": "73301,73344,75001,..."},
{"key": "_allowed_zip_codes", "value": "field_684b4e3679784"},
```

Use the overlap zone range where ALL species in the mix can grow.

| Zone Range | Zip Count | Use Case |
|-----------|-----------|----------|
| 3-8 | ~33,000 | Cool-to-warm (Lanceleaf Coreopsis) |
| 3-9 | ~37,500 | Nearly nationwide (Drummond Phlox, Butterfly Milkweed) |
| 4-9 | ~37,300 | Most of continental US (Evening Primrose, TX Prairie) |
| 6-10 | ~32,000 | Warm-zone mixes (TX Wildflower/Pollinator) |
| 7-9 | ~19,600 | Southern/central (Bluebonnet, TX Turf) |
| 8-10 | ~12,900 | Deep South/FL |
| 9-10 | ~6,200 | Subtropical/coastal (FL Coastal) |

#### price_discount_2 (Variation Box Nudge Label)
```python
{"key": "price_discount_2", "value": "10% Off - MOST PICKED"}
```
This controls the discount badge shown on the second/mid-tier variation in the PDP variation selector.

### Step 6 — Verify via API
```python
p = api("get", f"products/{pid}")
meta = {m["key"]: m["value"] for m in p.get("meta_data", [])}
variations = api("get", f"products/{pid}/variations", params_extra={"per_page": "100"})

# Assert:
assert "new" in [t["name"] for t in p.get("tags", [])]
assert meta.get("delivery_time") == "19"
assert meta.get("price_per_lb_1")
assert meta.get("allowed_zip_codes")
assert meta.get("_allowed_zip_codes") == "field_684b4e3679784"
assert len(variations) == expected_variation_count
for v in variations:
    assert v.get("sku")
    assert v.get("price")
    assert v.get("weight")
```

---

## ACF Field Reference

| Meta Key | ACF Reference | Description |
|----------|-------------|-------------|
| `allowed_zip_codes` | `field_684b4e3679784` | Zone-based zip restriction |
| `delivery_time` | — | Days to deliver (typically "19") |
| `price_per_lb_1` | — | $/lb for smallest size (highest $/lb) |
| `price_per_lb_2` | — | $/lb for middle size |
| `price_per_lb_3` | — | $/lb for largest size (lowest $/lb) |
| `price_discount_2` | — | Variation box label, e.g. "10% Off - MOST PICKED" |

For other ACF fields: GET the product after creation and inspect `meta_data` keys. Every value key `field_name` has a paired `_field_name` = `field_XXXXX`.

---

## SKU Naming Convention

```
[TYPE]-[SPECIES/REGION]-[WEIGHT]-LB[-KIT]
```

| Prefix | Use |
|--------|-----|
| `W-` | Single wildflower species (W-LUTE, W-OESP) |
| `WB-` | Wildflower blend (WB-TEXN, WB-FLN) |
| `TURF-` | Lawn/turf mix (TURF-TXN) |
| `PB-` | Pasture blend (PB-TXPR) |
| `PG-` | Prairie/native grass (PG-TRDA) |
| `CV-` | Cover crop |
| `S-` | Specialty/planting aid |

Smallest size = no `-KIT` → `WB-TEXN-0.5-LB`
Larger sizes = with `-KIT` → `WB-TEXN-1-LB-KIT`, `WB-TEXN-5-LB-KIT`

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `woocommerce_rest_product_not_created` + lookup table | SKU exists in WC lookup from deleted product | Create without SKU, add via PUT |
| `product_type_mismatch` on variation creation | Setary plugin intercepting | Deactivate Setary, create variations, reactivate |
| "No variations yet" in WP Admin but API returns them | `wp_wc_product_attributes_lookup` table not synced | Run type-cycling + attribute-clear + recreate (Step 4b) |
| `product_invalid_sku` with `resource_id` | SKU belongs to another product | Check that product ID, fix or choose new SKU |
| meta_data silently dropped | SET on POST instead of PUT | Always add meta via separate PUT after product exists |
| Duplicate meta entries | PUT without existing meta IDs | Always GET first to get IDs, then PUT with IDs |
| ACF fields not in WP Admin | Missing "new" tag | Add `{"tags": [{"name": "new"}]}` |

---

## Complete Checklist

```
[ ] 1. POST parent product (no meta, no SKU if lookup table risk)
[ ] 2. PUT SKU separately
[ ] 3. PUT "new" tag
[ ] 4. GET existing meta IDs → PUT all ACF fields with IDs
[ ] 5. DELETE any existing variations
[ ] 6. PUT clear attributes (attributes: [])
[ ] 7. PUT type: "simple" (cycle)
[ ] 8. PUT type: "variable"
[ ] 9. PUT Size attribute with options smallest→largest
[ ] 10. POST each variation (status, attributes, weight, price)
[ ] 11. PUT SKU on each variation
[ ] 12. PUT force parent save (type: variable, catalog_visibility: visible)
[ ] 13. PUT delivery_time = "19"
[ ] 14. PUT price_per_lb_1/2/3 (most expensive $/lb first)
[ ] 15. PUT allowed_zip_codes + _allowed_zip_codes (zone-based)
[ ] 16. PUT price_discount_2 = "10% Off - MOST PICKED"
[ ] 17. GET product + variations to verify all fields
[ ] 18. Check WP Admin — variations visible?
```
