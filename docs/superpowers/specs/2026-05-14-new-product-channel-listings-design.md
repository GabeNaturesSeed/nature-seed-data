# New Product Channel Listings — Design Spec
_2026-05-14_

## Goal

Add 3 new products (9 size variants total) to Google Merchant Center, Walmart Marketplace, and Amazon (draft) via a single script.

## Products

| Parent SKU | Product Name | WC ID | GTIN | Sizes |
|---|---|---|---|---|
| CV-CNIR | California Native Ignition Resistant Seed Mix | 470543 | 840184629488 | 5 lb, 10 lb, 25 lb |
| PB-SOLS | Southern Livestock Pasture Seed Mix | 470547 | 840184629426 | 10 lb, 20 lb, 50 lb |
| PB-PLPR | Plains Prairie Native Seed Mix | 470555 | 840184629389 | 10 lb, 20 lb, 50 lb |

### Variation IDs (WooCommerce post IDs)

| SKU | WC Variation ID | Price |
|---|---|---|
| CV-CNIR-5-LB | 470544 | $311.87 |
| CV-CNIR-10-LB | 470545 | $561.37 |
| CV-CNIR-25-LB | 470546 | $1,325.44 |
| PB-SOLS-10-LB | 470548 | $56.99 |
| PB-SOLS-20-LB | 470549 | $102.58 |
| PB-SOLS-50-LB | 470550 | $242.21 |
| PB-PLPR-10-LB | 470556 | $157.99 |
| PB-PLPR-20-LB | 470557 | $284.38 |
| PB-PLPR-50-LB | 470558 | $671.46 |

### Mix Compositions (for copy generation)

**CV-CNIR — 7 species:**
Purple Needlegrass 30%, Blue Wildrye 20%, Sandberg Bluegrass 15%, Small Fescue 15%, Deerweed 10%, Miniature Lupine 7%, Great Valley Gumweed 3%. Each species selected for fire resistance or soil-building role.

**PB-SOLS — 9 species:**
Tall Fescue 22%, Bermudagrass 18%, Alfalfa 15%, Ryegrass 12%, Ladino Clover 10%, Orchardgrass 9%, Cicer Milkvetch 7%, Puna Chicory 4%, Birdsfoot Trefoil 3%. Key differentiators: milkvetch (bloat safety), chicory (parasite reduction), season coverage logic.

**PB-PLPR — 12 species:**
Big Bluestem 15% through Yellow Sweet Clover 2%. Ecological roles: nurse crop function, nitrogen fixation, bird nesting structure.

### Coverage Areas

| Product | Rate | Per-size coverage |
|---|---|---|
| CV-CNIR | 1 lb / 1,000 sq ft | 5 lb → 5,000 | 10 lb → 10,000 | 25 lb → 25,000 |
| PB-SOLS | catalog std 2,000 sq ft/lb | 10 lb → 20,000 | 20 lb → 40,000 | 50 lb → 100,000 |
| PB-PLPR | ~2,900 sq ft/lb (ACF: 29k/10 lb) | 10 lb → 29,000 | 20 lb → 58,000 | 50 lb → 145,000 |

---

## Script

**File:** `Amazonimprovement/add_new_listings.py`

**Flags:**
- `--gmc` — append 9 rows to GMC Google Sheet
- `--walmart` — submit 9-item Walmart feed
- `--amazon` — append 3 parent rows to `amazon_missing_products.csv`
- No flags → all three channels

**Dependencies:** existing `.env`, `walmart_client.py`, `GOOGLE_SHEETS_REFRESH_TOKEN` (written 2026-05-14 by `scripts/reauth_google_sheets.py`).

---

## Channel 1: Google Merchant Center Sheet

**Sheet ID:** `12u2Uj0gHNImAQKDA1qnDUxlw4czL4DNuHbuUFqULbuU`

**Auth:** `GOOGLE_SHEETS_REFRESH_TOKEN` → Sheets API v4 `spreadsheets.values.append`.

**9 rows appended to Sheet1 after existing data.**

### Row schema (matches existing columns)

```
id, title, description, availability, condition, price, link, image_link,
brand, google_product_category, fb_product_category, quantity_to_sell_on_facebook,
sale_price, sale_price_effective_date, item_group_id, gender, color, size,
age_group, material, pattern, shipping, shipping_weight, gtin,
video[0].url, video[0].tag[0], product_tags[0], product_tags[1], style[0],
mpn, custom_label_0, custom_label_1, custom_label_2
```

### Fixed values (same for all 9 rows)

| Field | Value |
|---|---|
| availability | in stock |
| condition | new |
| brand | Nature's Seed |
| google_product_category | Home & Garden > Plants > Seeds |
| fb_product_category | patio & garden > plants, seeds & bulbs > seeds & bulbs |
| quantity_to_sell_on_facebook | 75 |
| shipping | US:Ground:9.99 USD |
| custom_label_2 | (empty) |
| gender/color/size/age_group/material/pattern/style[0]/video fields | (empty) |

### Per-product values

| SKU | id | item_group_id | custom_label_0 | product_tags[0] |
|---|---|---|---|---|
| CV-CNIR-* | gla_470544/45/46 | NS_0103 | specialty | specialty |
| PB-SOLS-* | gla_470548/49/50 | NS_0104 | pasture | pasture |
| PB-PLPR-* | gla_470556/57/58 | NS_0105 | pasture | pasture |

### Title format
`{Product Name} - {N} Lb - {Coverage} Sq Ft`
Example: `California Native Ignition Resistant Seed Mix - 5 Lb - 5,000 Sq Ft`

### Link format
`https://naturesseed.com/products/{category}/{slug}/?attribute_pa_size={size-slug}`
- CV-CNIR: `/products/specialty-seed/california-native-ignition-resistant-seed-mix/`
- PB-SOLS: `/products/pasture-seed/southern-livestock-pasture-seed-mix/`
- PB-PLPR: `/products/pasture-seed/plains-prairie-native-seed-mix/`
- Size slugs: `5-lb`, `10-lb`, `20-lb`, `25-lb`, `50-lb`

### Image links (from WC)
- CV-CNIR: `https://naturesseed.com/wp-content/uploads/2026/05/California-Native-Ignition-Resistant-Seed-Mix-.png`
- PB-SOLS: `https://naturesseed.com/wp-content/uploads/2026/05/SouthernPasture.png`
- PB-PLPR: `https://naturesseed.com/wp-content/uploads/2026/05/plainsprairie.webp`

### Price format
`{price} USD` — e.g., `311.87 USD`

### custom_label_1 / product_tags[1] (price bucket)
All 9 variants are >$50, so: `>200` for all (matches NS_0049, NS_0084 pattern for high-value specialty/pasture products).

---

## Channel 2: Walmart Marketplace

**Feed type:** MP_ITEM / `Grass Seeds` productType.

**variantGroupId:** SKU prefix without hyphens — `CVCNIR`, `PBSOLS`, `PBPLPR`.

**groupingAttributes:** `assembled_product_weight` (numeric lb value).

**lifecycleStatus:** ACTIVE, publishedStatus: STAGE (activates via existing `activate_stage_items.py`).

### Item payload structure per variant

```json
{
  "sku": "CV-CNIR-5-LB-KIT",
  "productName": "California Native Ignition Resistant Seed Mix - 5 lb - Covers 5,000 Sq Ft",
  "productType": "Grass Seeds",
  "price": { "currency": "USD", "amount": 311.87 },
  "upc": "840184629488",
  "brand": "Nature's Seed",
  "condition": "New",
  "availability": "In_stock",
  "variantGroupId": "CVCNIR",
  "variantGroupInfo": {
    "isPrimary": false,
    "groupingAttributes": [{ "name": "assembled_product_weight", "value": "5" }]
  }
}
```

Note: Walmart SKU convention appends `-KIT` suffix (matching existing items e.g. `PB-SHEP-SO-20-LB-KIT`).

---

## Channel 3: Amazon (Draft)

**File:** `Amazonimprovement/amazon_missing_products.csv`

**3 rows appended** (one per parent product — Amazon uses parent+child variation model handled by `push_amazon_drafts.py`).

### Columns populated per row

| Column | Value |
|---|---|
| wc_id | Parent WC ID (470543 / 470547 / 470555) |
| parent_sku | CV-CNIR / PB-SOLS / PB-PLPR |
| product_name | Full product name |
| product_type | variable |
| bullet_1–5 | Generated from species mix and key differentiators |
| description_plain | ~400-word description based on species compositions |
| size_options | Pipe-delimited size+coverage labels |
| variation_skus | Pipe-delimited child SKUs |
| variation_prices | Pipe-delimited prices |
| wc_url | WC permalink |
| image_1 | Primary WC image URL |
| image_2 | Secondary WC image URL |
| search_terms | Comma-separated keyword string |

### Content approach for bullets

**CV-CNIR:** Lead with fire resistance angle — bunchgrass structure reduces surface fuel, species-by-species fire/soil role, native to California, low water after establishment, seeding rate 1 lb/1,000 sq ft.

**PB-SOLS:** Lead with livestock safety differentiators — bloat-safe milkvetch, parasite reduction via chicory, 9-species season coverage, dual-use warm/cool season, seeding rate 25–30 lbs/acre.

**PB-PLPR:** Lead with prairie ecology — 12 native species, nurse crop and nitrogen fixation roles, bird habitat structure, Great Plains provenance, 10–15 lbs PLS/acre.

---

## Auth / Env Requirements

| Key | Used by | Status |
|---|---|---|
| GOOGLE_SHEETS_REFRESH_TOKEN | GMC sheet append | Written 2026-05-14 |
| GOOGLE_ADS_CLIENT_ID / SECRET | Sheets token exchange | Existing |
| WC_CK / WC_CS + CF_WORKER_URL/SECRET | WC data verification | Existing |
| WALMART_CLIENT_ID / SECRET | Walmart feed | Existing |
| AMAZON_* | Amazon push | Existing |

---

## Out of Scope

- Activating Walmart STAGE items (use existing `activate_stage_items.py`)
- Pushing Amazon drafts to live (use existing `push_amazon_drafts.py`)
- Adding GTINs to WC product meta (done separately in WC admin)
