# Nature's Seed — WooCommerce Product Page Creation Guide

**Last updated:** March 2026
**Applies to:** naturesseed.com (WooCommerce + ACF)

---

## API Credentials & Base URL

```
Base URL: https://naturesseed.com/wp-json/wc/v3
Auth: Consumer Key + Consumer Secret from .env
Always add cache-busting param: params={"_": int(time.time())}
```

---

## Product Creation Order of Operations

This order is **non-negotiable**. Skipping or reordering steps causes silent failures.

### Step 1: Create the Parent Product (POST)

```
POST /products
```

- Set `type: "variable"` and `status: "draft"`
- **Do NOT include `meta_data` on the initial POST** — WooCommerce silently drops most meta fields on product creation. They must be added in a separate PUT.
- If the SKU already exists in WooCommerce's lookup table (from a previous import/delete), creation will fail. **Workaround:** Create the product WITHOUT a SKU, then add the SKU via a separate PUT.

**Error you'll see if SKU is stuck in lookup table:**
```
{"code":"woocommerce_rest_product_not_created",
 "message":"The product with SKU (X) you are trying to insert is already present in the lookup table"}
```

**Fix:**
```python
# Create without SKU
body = {"name": "...", "type": "variable", "status": "draft"}
result = api("post", "products", body)
pid = result["id"]
# Then add SKU
api("put", f"products/{pid}", {"sku": "YOUR-SKU"})
```

---

### Step 2: Add the "new" Tag

```python
api("put", f"products/{pid}", {"tags": [{"name": "new"}]})
```

**Why this matters:** Without the `new` tag, all the custom ACF fields we created will NOT appear in the WordPress editor. The tag triggers ACF field group visibility rules. If you skip this, the product looks like it has no custom fields in wp-admin even though the data is in the database.

---

### Step 3: Push All ACF Meta Fields (Two-Step Pattern)

ACF meta fields **must** be added via a two-step process:

1. **GET** the product to retrieve existing `meta_data` with their internal IDs
2. **PUT** the product with the full `meta_data` array, including IDs for existing keys

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

**If you skip the GET step and just PUT new meta_data**, you risk creating duplicate meta entries instead of updating existing ones.

### ACF Paired Fields

Every ACF field has TWO meta entries:
- The value field: e.g., `allowed_zip_codes` → the actual comma-separated zip string
- The underscore reference field: e.g., `_allowed_zip_codes` → `field_684b4e3679784`

**Both must be set.** If you only set the value without the underscore reference, ACF won't recognize the field in the editor.

---

### Step 4: Create Variations (The Tricky Part)

**Critical lesson learned:** Adding Size attributes to a product does NOT create variations. Attributes just define what options exist. You must explicitly create each variation as a separate API call.

#### Step 4a: Delete Existing Variations (if rebuilding)

```python
existing = api("get", f"products/{pid}/variations", params_extra={"per_page": "100"})
for v in existing:
    api("delete", f"products/{pid}/variations/{v['id']}", params_extra={"force": "true"})
```

#### Step 4b: Clear and Reset Attributes + Product Type

**This is the fix that makes variations actually appear in WP Admin.** Without this cycling, the WooCommerce admin UI shows "No variations yet" even though the API returns them.

```python
# Clear attributes
api("put", f"products/{pid}", {"attributes": []})

# Cycle product type (forces WC internal lookup table rebuild)
api("put", f"products/{pid}", {"type": "simple"})
api("put", f"products/{pid}", {"type": "variable"})

# Re-add Size attribute
api("put", f"products/{pid}", {
    "attributes": [{
        "name": "Size",
        "slug": "size",
        "position": 0,
        "visible": True,
        "variation": True,
        "options": ["0.5 lb", "1 lb", "5 lb"],  # your size options
    }]
})
```

#### Step 4c: Create Each Variation

```python
body = {
    "status": "publish",
    "attributes": [{"name": "Size", "option": "0.5 lb"}],
    "weight": "0.5",
    "regular_price": "11.99",
    "sale_price": "9.99",  # optional
    "manage_stock": False,
}
vresult = api("post", f"products/{pid}/variations", body)
vid = vresult["id"]

# Set SKU separately (avoids lookup table conflicts)
api("put", f"products/{pid}/variations/{vid}", {"sku": "WB-TEXN-0.5-LB"})
```

#### Step 4d: Force Parent Save

```python
api("put", f"products/{pid}", {"type": "variable", "catalog_visibility": "visible"})
```

This triggers WooCommerce to rebuild its internal variation caches.

---

### Step 5: Set Product-Level Fields

After variations exist, set these fields on the **parent product**:

#### delivery_time
```python
api("put", f"products/{pid}", {"meta_data": [{"key": "delivery_time", "value": "19"}]})
```

#### price_per_lb_1, price_per_lb_2, price_per_lb_3

Calculate as `regular_price / weight_in_lbs` for each variation, sorted **most expensive per lb first** (smallest size = highest per-lb cost).

```python
# Example: 0.5 lb at $11.99 = $23.98/lb, 1 lb at $23.99 = $23.99/lb, 5 lb at $117.99 = $23.60/lb
# Sorted descending: $23.99, $23.98, $23.60
meta_data = [
    {"key": "price_per_lb_1", "value": "23.99"},
    {"key": "price_per_lb_2", "value": "23.98"},
    {"key": "price_per_lb_3", "value": "23.6"},
]
```

#### allowed_zip_codes (Zone-Based)

Use the USDA Plant Hardiness Zone API (phzmapi.org) to build zone-to-zip mappings. We have saved files `zone_to_zips.json` and `zip_to_zone.json` for reuse.

```python
# Both the value AND the ACF reference must be set
meta_data = [
    {"key": "allowed_zip_codes", "value": "73301,73344,75001,..."},
    {"key": "_allowed_zip_codes", "value": "field_684b4e3679784"},
]
```

Zone assignments are based on species composition — use the overlap zone range where all species in a mix can grow.

---

### Step 6: Verify Everything via API

**Always pull the product back and check.** Don't trust that the PUT worked.

```python
p = api("get", f"products/{pid}")
meta = {m["key"]: m["value"] for m in p.get("meta_data", [])}
variations = api("get", f"products/{pid}/variations", params_extra={"per_page": "100"})

# Check: tag "new" present
# Check: delivery_time = "19"
# Check: price_per_lb_1/2/3 populated
# Check: allowed_zip_codes has correct count
# Check: _allowed_zip_codes = "field_684b4e3679784"
# Check: variations count matches expected
# Check: each variation has SKU, price, weight, size attribute
```

---

## SKU Naming Convention

```
[TYPE]-[SPECIES/REGION]-[WEIGHT]-LB[-KIT]
```

- **Smallest size:** No -KIT suffix → `WB-TEXN-0.5-LB`
- **Larger sizes:** -KIT suffix → `WB-TEXN-1-LB-KIT`, `WB-TEXN-5-LB-KIT`
- **Parent SKU:** Just the base → `WB-TEXN`

Prefixes:
- `W-` = Individual wildflower species (e.g., W-LUTE, W-OESP)
- `WB-` = Wildflower blend/mix (e.g., WB-TEXN, WB-FLN)
- `TURF-` = Lawn/turf mix (e.g., TURF-TXN, TURF-FLN)
- `PB-` = Prairie blend (e.g., PB-TXPR)
- `PG-` = Prairie grass (e.g., PG-TRDA)

---

## Common Errors and Fixes

### "product_type_mismatch" on variation creation
**Cause:** Setary plugin (or similar) intercepting the API.
**Fix:** Deactivate Setary before creating variations. Reactivate after.

### Variations exist in API but "No variations yet" in WP Admin
**Cause:** WooCommerce's internal `wp_wc_product_attributes_lookup` table not synced.
**Fix:** The type-cycling approach (Step 4b above). Delete all variations, clear attributes, cycle simple→variable, re-add attributes, recreate variations, force parent save.

### "product_invalid_sku" with a resource_id in the error
**Cause:** SKU already belongs to another product.
**Fix:** The error includes the existing product ID. Either update that product or use a different SKU.
```
{"code":"product_invalid_sku","data":{"resource_id":185416}}
```

### meta_data silently dropped on POST
**Cause:** WooCommerce ignores most meta_data during product creation.
**Fix:** Always add meta in a separate PUT after the product exists.

### Duplicate meta entries accumulating
**Cause:** PUTting meta_data without including the existing meta `id`.
**Fix:** Always GET first to retrieve meta IDs, then PUT with IDs for existing keys.

### ACF fields not showing in WP Admin editor
**Cause:** Missing the "new" tag.
**Fix:** Add `{"tags": [{"name": "new"}]}` to the product.

---

## Zone-to-Zip Reference

Saved files for reuse (in project directory):
- `zone_to_zips.json` — Zone number → array of zip codes
- `zip_to_zone.json` — Zip code → zone number
- Source: phzmapi.org (USDA Plant Hardiness Zone data from PRISM/Oregon State)

| Zone Range | Typical Zip Count | Use Case |
|-----------|-------------------|----------|
| 3-8 | ~33,000 | Broad cool-to-warm (e.g., Lanceleaf Coreopsis) |
| 3-9 | ~37,500 | Nearly nationwide (e.g., Drummond Phlox, Butterfly Milkweed) |
| 4-9 | ~37,300 | Most of continental US (e.g., Evening Primrose, TX Prairie) |
| 6-10 | ~32,000 | Warm-zone mixes (e.g., TX Wildflower/Pollinator) |
| 7-9 | ~19,600 | Southern/central (e.g., Bluebonnet, TX Turf) |
| 8-10 | ~12,900 | Deep South/FL (e.g., FL mixes) |
| 9-10 | ~6,200 | Subtropical/coastal (e.g., FL Coastal mix) |

---

## ACF Field Reference Keys

These underscore-prefixed field references must match exactly:

| Field | ACF Reference |
|-------|--------------|
| `_allowed_zip_codes` | `field_684b4e3679784` |

For other ACF fields, the reference values are in the ACF JSON export files. Every meta field like `product_highlight_1` has a corresponding `_product_highlight_1` with a `field_XXXXX` value.

---

## Complete Workflow Checklist

```
[ ] 1. Create parent product (POST, no meta, no SKU if lookup table conflict)
[ ] 2. Add SKU via PUT (if skipped in step 1)
[ ] 3. Add "new" tag via PUT
[ ] 4. Push all ACF meta fields (two-step: GET IDs → PUT with IDs)
[ ] 5. Delete any existing variations
[ ] 6. Clear attributes from parent
[ ] 7. Cycle product type: simple → variable
[ ] 8. Re-add Size attribute with correct options
[ ] 9. Create each variation (POST to /variations)
[ ] 10. Set SKU on each variation via PUT
[ ] 11. Force parent product save
[ ] 12. Set delivery_time = 19
[ ] 13. Calculate and set price_per_lb_1/2/3 (most expensive first)
[ ] 14. Set allowed_zip_codes + _allowed_zip_codes (zone-based)
[ ] 15. GET product + variations to verify everything
[ ] 16. Check WP Admin to confirm variations visible
```