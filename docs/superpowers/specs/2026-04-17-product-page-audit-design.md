# Product Page Audit — Design Spec

**Date:** 2026-04-17
**Owner:** Gabe / Nature's Seed
**Status:** Approved, pending implementation

## Goal

Produce a repeatable, data-driven audit of every published WooCommerce product on naturesseed.com that grades completeness of frontend-visible ACF content fields + core content + supporting PDP elements. Output ranks products worst → best so the team knows where to focus copy and content work.

## Scope

**In scope:**
- Every product in `status=publish` on naturesseed.com
- All frontend-visible ACF content groups: mix_components repeater, product_content_2, 5× benefit cards, 4× how-to cards, 6× FAQ answers
- Core WC content: `description`, `short_description`
- PDP supporting elements: main image + gallery count, upsell IDs

**Out of scope (this audit):**
- Planting Aids category (id 3889) — gets its own audit
- RankMath SEO fields (focus keyword, meta title, meta description) — manual workstream per CLAUDE.md
- Product weight + variation coverage — infrastructure concerns, separate audit
- Image quality judgement (we only count presence)
- Category and blog page content

## Rubric — Hybrid Scoring

Each field gets one of three statuses:

- **`missing`** — empty or absent
- **`thin`** — filled but below the length threshold for that field type
- **`present`** — meets or exceeds the length threshold

### Thin thresholds

| Field group | Key pattern | Thin threshold (chars, stripped HTML) |
|---|---|---|
| Main description | `description` | <200 |
| Short description | `short_description` | <40 |
| Secondary description | `product_content_2` | <200 |
| Benefit card titles ×5 | `product_card_title_{1–5}` | no thin (title-length naturally short; binary only) |
| Benefit card content ×5 | `product_card_content_{1–5}` | <50 |
| How-To card content ×4 | `product_card_2_content_{1–4}` | <80 |
| FAQ answers ×6 | `answer_content_{1–6}` | <60 |
| Mix component descriptions | `mix_components_{N}_description` | <30 (conditional — only if `mix_components` count > 0) |
| Main image | `images[0]` | missing if no image; no thin tier |
| Gallery image(s) | `images[1+]` | missing if no gallery, thin if exactly 1, present if ≥2 |
| Upsell IDs | `upsell_ids` | missing if 0, thin if 1-2, present if ≥3 |

### Scoring formula

```
score = (count("present") + 0.5 * count("thin")) / applicable_fields * 100
```

`applicable_fields` excludes mix_components rows when the product has no repeater. Every other field counts for every product.

## Output artifacts

1. **`store/product-updates/audit_results.json`** — machine-readable scorecard. Structure:
   ```jsonc
   {
     "generated_at": "2026-04-18 01:00:00 UTC",
     "total_products": 114,
     "skipped_planting_aids": 5,
     "rubric_version": "2026-04-17",
     "thin_thresholds": {...},
     "results": [
       {
         "id": 182825,
         "name": "Sonoran Desert Wildflower Mix",
         "sku": "WB-SD",
         "permalink": "https://...",
         "categories": ["Native Wildflower Seed"],
         "type": "variable",
         "score": 74.2,
         "counts": {"present": 26, "thin": 5, "missing": 4},
         "total_fields": 35,
         "has_mix": true,
         "fields": [{"key": "description", "status": "present", "length": 412}, ...]
       }
     ]
   }
   ```

2. **`reports/product_page_audit.html`** — human-readable report:
   - Header summary (avg score, total missing/thin/present counts)
   - Sortable table: Name · SKU · Categories · Score · Missing · Thin · Present · Live link
   - Products sorted worst → best so action items surface at top
   - Per-product drill-down section with every field's status chip + character length
   - Brand styling: primary green accents, Noto Serif Display headings, Inter body

## Architecture

**Script:** `store/product-updates/audit_all_products.py`

**Data flow:**
```
CF Worker proxy (wc-api-proxy.skylar-d51.workers.dev)
  ↓ GET /products?status=publish&per_page=100&page=N  (paginated)
All published products (~119 expected)
  ↓ filter: skip Planting Aids (cat 3889)
Audited set (~114)
  ↓ score_product() — rubric applied per product
Scored results
  ↓ write JSON + render HTML
audit_results.json + product_page_audit.html
```

**Rate limit:** 0.3s between paginated GETs (~1 min total runtime at 100 products/page).

**Routing:** Always through CF Worker (`CF_WORKER_URL` + `CF_WORKER_SECRET` env vars) — Bot Fight Mode blocks direct WC API calls from automation environments.

## Assumptions

- `mix_components` count is stored as a string integer under the meta key `mix_components` (confirmed from Sonoran audit — value was "12", then "14").
- ACF card/FAQ keys use the pattern documented in `store/product-updates/audit_bottom20_products.py`.
- HTML is stripped from description/short_description before measuring length (WC stores with `<p>` tags).
- The 119 products total count from `docs/data/inventory.json` is approximate; the script pages until the API returns an empty set.

## Out of scope / future work

- **Content quality grading beyond length heuristics.** A future pass could run an LLM read on long-form copy to flag repetition, generic claims, or off-brand voice.
- **Category page audit.** Category/taxonomy pages have their own ACF fields and warrant a separate rubric.
- **Fix generation.** This audit is read-only. A follow-up tool could draft content for top-priority missing fields using brand voice skill.
- **Historical trending.** Re-running the audit over time to track improvement would need persisted results in Supabase or similar.

## Success criteria

- 100% of published non-Planting-Aids products are scored.
- Report highlights the 10 worst products by score on first visible screen.
- Each scored product has every rubric field categorized as `missing`/`thin`/`present` with its length attached.
- Output JSON is idempotent and diff-friendly (stable key order).
