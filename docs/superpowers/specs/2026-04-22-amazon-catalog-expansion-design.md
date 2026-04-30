# Amazon Catalog Expansion — Design Spec
**Date:** 2026-04-22
**Author:** Claude (amazon agent)
**Status:** Approved

---

## Goal

Identify all WooCommerce products not currently listed on Amazon, create SP-API draft listings for those with complete content, and produce a structured to-do for the content manager covering all listings that need images or A+ content.

---

## Architecture

```
pull_amazon_catalog.py  →  amazon_catalog.json
pull_wc_catalog.py      →  wc_catalog.json
amazon_wc_crossref.py   →  amazon_missing_products.csv
                                    ↓
                        push_amazon_drafts.py
                        ├── Ready (title + 5 bullets + desc + 1 image)
                        │     └── POST to SP-API listings/items (INACTIVE)
                        └── Incomplete
                              └── flagged row in content_manager_todo.md
                                    ↓
                        amazon_expansion_status.csv   (all candidates)
                        Supabase: amazon_listing_queue (upsert per SKU)
```

---

## Scripts

### Existing (run as-is)
| Script | Output |
|---|---|
| `pull_amazon_catalog.py` | `amazon_catalog.json` |
| `pull_wc_catalog.py` | `wc_catalog.json` |
| `amazon_wc_crossref.py` | `amazon_missing_products.csv` |

### New
**`Amazonimprovement/push_amazon_drafts.py`**

Reads `amazon_missing_products.csv` and for each candidate:

1. **Completeness check** — a listing is "ready" if it has:
   - Title (non-empty)
   - At least 5 bullet points
   - Product description (non-empty)
   - At least 1 product image URL
   - Price (from WC variations or simple price)

2. **Ready path** — POST to SP-API `PUT /listings/items/{sellerId}/{sku}` with `status: INACTIVE`. Payload includes:
   - `item_name`, `bullet_point[]`, `product_description`
   - `list_price`, `fulfillment_availability`
   - Image URLs (from WC `images` field)
   - `generic_keyword` (from WC tags/ACF)
   - Rate limit: sleep 2s between each call (SP-API 0.5 req/s, conservative)

3. **Incomplete path** — writes a flagged section to `content_manager_todo.md` with:
   - Product name, SKU, WC permalink
   - Missing fields list
   - Existing WC description (for copywriter reference)
   - Existing images (what's available vs what's needed)
   - A+ content guidelines (per category)
   - Suggested keyword targets (pulled from top Amazon listings in `amazon_catalog.json`)

4. **Status output** — writes `Amazonimprovement/amazon_expansion_status.csv`:

| Column | Description |
|---|---|
| sku | Nature's Seed SKU |
| title | Product title |
| status | `drafted` / `needs-content` / `error` |
| missing_fields | Comma-separated list of what's missing |
| image_count | Number of available images |
| asin | Populated if SP-API returns one, else empty |
| pushed_at | ISO timestamp |
| notes | Error message or content guidance |

5. **Supabase upsert** — upserts each row into `amazon_listing_queue` table (same columns as CSV). Conflict key: `sku`.

---

## Content Manager To-Do (`content_manager_todo.md`)

One section per flagged product. Structure per product:

```markdown
## [Product Name] — SKU: XXX-YYY-ZZZ

**WC Link:** https://...
**Missing:** images, A+ content
**Available Images:** 2 (links below)
**Recommended Image Count:** 7

### Copy Reference
[WC description pasted here, HTML stripped]

### Bullets (existing or suggested)
1. ...

### A+ Content Guideline
- Module type: Brand Story + Comparison Chart
- Tone: [nature's seed brand voice notes]
- Keywords to feature: [top search terms from Amazon catalog]

### Image Shot List
- Hero: product on white background
- Lifestyle: product in use / field context
- Infographic: coverage area, seeding rate
- Detail: seed closeup
```

---

## Supabase Table: `amazon_listing_queue`

```sql
create table amazon_listing_queue (
  sku text primary key,
  title text,
  status text,          -- drafted | needs-content | error | live
  missing_fields text,
  image_count int,
  asin text,
  pushed_at timestamptz,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

---

## Completeness Thresholds

| Field | Required | Notes |
|---|---|---|
| Title | Yes | Non-empty string |
| Bullets | Yes | Minimum 5 |
| Description | Yes | >50 characters after HTML strip |
| Images | Yes | At least 1 URL |
| Price | Yes | >0, from WC |
| Search terms | No | Nice to have, pulled from tags |

---

## Error Handling

- SP-API 429 → exponential backoff (2s, 4s, 8s), max 3 retries, then write `error` row
- SP-API 400 (invalid payload) → log raw response in `notes` column, skip listing
- Missing env vars → fail fast with clear error before processing any listings

---

## Deliverables

1. `amazon_catalog.json` — current Amazon listings
2. `wc_catalog.json` — all published WC products
3. `amazon_missing_products.csv` — WC products not on Amazon
4. `content_manager_todo.md` — structured to-do per product needing content
5. `amazon_expansion_status.csv` — full status per candidate
6. Supabase `amazon_listing_queue` table populated
7. Inactive draft listings live in Seller Central for ready products
