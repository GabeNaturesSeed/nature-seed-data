# Reddit Ads Catalog — Design Spec

**Date:** 2026-04-28
**Status:** Approved (awaiting implementation plan)
**Owner:** Gabe

## Goal

Generate a Google-Shopping-spec product feed of every active Nature's Seed product (variation-level) and host it at a public URL so Reddit Ads Manager can ingest it as a Catalog for Catalog Sales / Dynamic Product Ad campaigns.

## Non-goals

- Pushing products via Reddit's Ads API (`ads-api.reddit.com/api/v3/`). Feed-URL ingestion is simpler and Reddit's preferred path.
- Reddit Conversions API integration. `REDDIT_EVENTS_TOKEN` exists for that purpose but is out of scope for this project.
- Other ad platforms (Meta, Pinterest, TikTok). The TSV format is portable, but each platform's setup is its own task.
- Sweeping cleanup of legacy Telegram notification code across the repo (tracked separately as opportunistic cleanup).

## Architecture

```
GitHub Action (cron: 0 6 * * *)
        │
        ▼
build_reddit_catalog.py
        │  fetch products + variations from WC via CF Worker proxy
        │  filter (publish + instock + image + price > 0)
        │  transform to Google Shopping TSV rows
        ▼
marketing/reddit-ads/output/reddit_catalog.tsv
marketing/reddit-ads/output/reddit_catalog_summary.json
        │
        ▼
git commit to main (output/ folder)
        │
        ▼
GitHub Pages serves from main:/marketing/reddit-ads/output/
        │
        ▼
https://gabenaturesseed.github.io/nature-seed-data/marketing/reddit-ads/output/reddit_catalog.tsv
        │
        ▼
Reddit Ads Manager  (configured once: URL + 24h refresh)
```

## Project layout

```
marketing/reddit-ads/
├── build_reddit_catalog.py        # entry point: pull + transform + write
├── transform.py                   # pure functions for row construction (testable)
├── wc_client.py                   # WC API wrapper (proxies through CF Worker if env set)
├── output/
│   ├── reddit_catalog.tsv         # generated, committed
│   └── reddit_catalog_summary.json
├── tests/
│   ├── fixtures/
│   │   ├── simple_product.json
│   │   ├── variable_product.json
│   │   └── edge_cases.json
│   └── test_transform.py
└── README.md                      # one-time Reddit Ads Manager setup
```

GitHub Action: `.github/workflows/reddit-catalog.yml`

## Data flow

### Input

WooCommerce REST API:
- `GET /wp-json/wc/v3/products?per_page=100&status=publish&stock_status=instock` (paginated)
- For each variable product: `GET /wp-json/wc/v3/products/{id}/variations?per_page=100`
- Routed through `CF_WORKER_URL` when set (datacenter IPs are blocked by Bot Fight Mode), direct otherwise.
- 0.3s sleep between calls per project rate-limit policy.

### Filtering (per-product, per-variation)

Skip if any of:
- `status != "publish"`
- `stock_status != "instock"`
- No featured image (`images[]` empty)
- Price is `null`, `""`, or `0`

For variable products: skip the parent's catalog row entirely; emit one row per qualifying variation. If a variation has no override image, fall back to the parent's `images[0]`. Variations that fail any filter are skipped individually.

### Output: TSV columns (Google Shopping spec)

| Column | Source | Required | Notes |
|---|---|:---:|---|
| `id` | `variation.id` or `product.id` | yes | Unique per row |
| `item_group_id` | `product.id` | yes | Same across siblings of a variable product |
| `title` | `product.name` + variation attrs (e.g. `" — 5 lb"`) | yes | Cap 150 chars |
| `description` | `product.short_description` (HTML stripped) → fallback `product.description` | yes | Cap 1000 chars, UTF-8 preserved |
| `link` | `product.permalink` | yes | Permalink Manager `/products/` slug |
| `image_link` | `variation.image.src` ?? `product.images[0].src` | yes |  |
| `additional_image_link` | `product.images[1..9]` joined `,` | no |  |
| `availability` | `"in stock"` | yes | All rows that pass filter are in stock |
| `price` | `"<float> USD"` from `variation.price` or `product.price` | yes | Reddit requires currency suffix |
| `sale_price` | `"<float> USD"` if `sale_price` present and < regular_price | no |  |
| `brand` | `"Nature's Seed"` | yes | Constant |
| `condition` | `"new"` | yes | Constant |
| `gtin` | `meta_data` key `_gtin` if present | no | Skip if blank |
| `mpn` | `variation.sku` or `product.sku` | no |  |
| `product_type` | deepest `categories[].name` | no | For Reddit ad targeting |
| `google_product_category` | `"5587"` (Home & Garden > Lawn & Garden > Gardening > Plants > Seeds) | no | Constant |

Header row first; rows separated by `\n`; columns by `\t`. Embedded tabs/newlines in any field are replaced with spaces.

### Output: summary JSON

```json
{
  "generated_at": "2026-04-29T06:00:00Z",
  "row_count": 847,
  "products_seen": 312,
  "variations_seen": 547,
  "skipped": [
    {"id": 12345, "reason": "no_image"},
    {"id": 12346, "reason": "out_of_stock"}
  ],
  "previous_row_count": 850
}
```

Committed alongside the TSV so `git log marketing/reddit-ads/output/` is the catalog audit trail.

## Error handling

1. **WC API fetch failure** (5xx, 429, network) — Retry 3x with exponential backoff (1s, 4s, 16s). On final failure, exit non-zero. Do not overwrite the existing TSV; Reddit keeps fetching the last good file.
2. **Per-product malformed data** — Log to summary `skipped[]` with a reason, continue.
3. **Row-count regression guard** — If new `row_count < previous_row_count * 0.5`, exit non-zero without committing. Prevents an upstream bug from wiping the catalog.
4. **GitHub Action failure** — GitHub emails the repo owner on failed runs; no extra notification needed.

## Testing

Pure-function unit tests on the transform layer (no live API calls):

| Test | Verifies |
|---|---|
| `test_simple_product_to_row` | One row, IDs match, all required fields populated |
| `test_variable_product_to_rows` | One row per variation, shared `item_group_id`, variation attrs in title |
| `test_skip_no_image` | Product without images is excluded |
| `test_skip_zero_price` | Product with `price = "0"` or `null` is excluded |
| `test_skip_out_of_stock` | `stock_status = "outofstock"` excluded |
| `test_format_price` | `19.99 → "19.99 USD"`, handles `None`, `0`, string inputs |
| `test_truncate_description` | HTML stripped, capped at 1000 chars, no broken UTF-8 |
| `test_variation_image_fallback` | Variation with no image inherits parent image |
| `test_tsv_escaping` | Tabs/newlines in titles/descriptions replaced with spaces |

Fixtures in `tests/fixtures/` are real WC API response shapes captured once via the live API, then static.

The WC fetch layer (`wc_client.py`) is integration-tested behind a `--integration` flag — single live call, not run in CI.

## Schedule

GitHub Action `.github/workflows/reddit-catalog.yml`:
- Cron `0 6 * * *` (6 AM UTC daily)
- Manual trigger via `workflow_dispatch`
- Uses Repository secrets `WC_CK`, `WC_CS`, `CF_WORKER_URL`, `CF_WORKER_SECRET`
- Python 3.11, `pip install -r marketing/reddit-ads/requirements.txt`
- On success: commit the regenerated TSV + summary JSON to `main` under `marketing/reddit-ads/output/` (one commit per run; the diff is small — just the TSV — so history stays manageable and provides an audit trail via `git log`)
- GitHub Pages is configured (one-time, in repo Settings → Pages) to serve from `main` branch root. Since the output files live at `marketing/reddit-ads/output/`, the public URL becomes `https://<user>.github.io/<repo>/marketing/reddit-ads/output/reddit_catalog.tsv`.

## One-time Reddit Ads Manager setup (manual)

Documented in `marketing/reddit-ads/README.md`:
1. In Reddit Ads Manager → Catalog → Create Catalog → Source: "Scheduled feed"
2. URL: `https://gabenaturesseed.github.io/nature-seed-data/marketing/reddit-ads/output/reddit_catalog.tsv`
3. Refresh frequency: Daily
4. Currency: USD
5. Once catalog populates, link to a Catalog Sales campaign.

## Open assumptions to verify during implementation

- GitHub Pages is enabled for `GabeNaturesSeed/nature-seed-data` (need to confirm; if not, enable in repo settings or fall back to gh-pages branch with Pages config).
- Reddit Ads account is provisioned and Catalog Sales objective is available on this ad account tier (most accounts have it; confirm in Ads Manager before implementation).
- WC product count (~est. 300 parent products + 500 variations = ~800 rows) is well under any TSV size limit Reddit imposes; no chunking needed.

## Out of scope (future work)

- Sweeping Telegram cleanup across other projects (opportunistic only)
- Reddit Conversions API wiring (separate spec when needed)
- Catalog ads creative + audience setup in Reddit Ads Manager (not a code task)
- Multi-platform catalog reuse (the TSV is portable; setup for Meta/Pinterest is per-platform manual config)
