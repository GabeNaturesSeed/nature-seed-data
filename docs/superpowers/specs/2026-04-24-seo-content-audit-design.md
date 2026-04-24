# SEO Content Audit & Topic Map — Design Spec

**Date:** 2026-04-24
**Owner:** Gabe / Nature's Seed
**Status:** Approved, pending implementation plan
**Project home:** `naturesseed-content-pipeline/` (extend existing)

## Goal

Build a repeatable, DB-backed audit pipeline that inventories every editorial page on naturesseed.com, classifies each into a topic/subtopic, tags products mentioned (active and discontinued), extracts outbound links, and flags decay signals. The output is the foundation for two downstream workstreams:

1. **Content refresh** — a prioritized queue of articles needing updates (discontinued products, outdated USDA maps, stale shipping claims, etc.)
2. **Automation substrate** — a topic/subtopic map that powers future internal-linking automations, content coverage maps, and content-generation automations

## Scope

**In scope:**
- All editorial content on naturesseed.com: WP `posts` + `pages` + `product` descriptions (WooCommerce)
- Topic/subtopic taxonomy rooted in WooCommerce categories
- Product mention tagging (active + discontinued) and species mention tagging
- Outbound link extraction with internal/external classification and HTTP status checks
- Decay-signal scanning via a pluggable rule engine
- Markdown and CSV report generation

**Out of scope (this spec):**
- Retool dashboard wiring (follow-on; DB is the source of truth)
- Content brief generation and automated drafting (downstream of this audit)
- Internal-linking automation itself (this produces the map; the automation is a later project)
- Keyword research and SERP analysis (other agents already exist in the pipeline)
- Refreshing article content (downstream — this populates `refresh_queue`, doesn't act on it)

## Architecture

Extend `naturesseed-content-pipeline/`. Split the existing `pipelines/audit.py` stub into six idempotent stages under `pipelines/audit/`, add a new `audit_rules/` directory of pluggable decay rules.

```
nspipe audit sync          → WP REST ──► content_inventory, wc_catalog_snapshot
nspipe audit classify      → content_inventory + WC cats ──► topics, content_topics (LLM for subtopics)
nspipe audit tag-products  → content + wc_catalog_snapshot ──► content_product_mentions, orphan_references
nspipe audit scan-links    → content HTML ──► outbound_links (+ HTTP status checks)
nspipe audit scan-decay    → all prior ──► decay_findings (pluggable rules), refresh_queue
nspipe audit report        → all prior ──► docs/content-audit/YYYY-MM-DD/*.md + *.csv
```

**Dependency order:** `sync` first. `classify`, `tag-products`, `scan-links` can run in any order after `sync`. `scan-decay` depends on all three. `report` runs last.

**State:** SQLite at `naturesseed-content-pipeline/content_pipeline.db` is authoritative. Reports are derived views, regeneratable at any time.

**LLM usage is isolated to exactly two places:**
- `classify` — proposes subtopic names per top-level topic (one-shot, human-approved)
- `scan-decay` — judges candidates surfaced by cheap regex filters in the two LLM-assisted rules (`UsdaZoneMapRule`, `OutdatedShippingRule`)

All other logic is deterministic.

## Data Model

Additive migration (no destructive changes to existing tables). Six new tables:

### `topics`
```
id                   INTEGER PK
parent_topic_id      INTEGER FK topics.id NULL    -- null for top-level
name                 TEXT NOT NULL
slug                 TEXT NOT NULL UNIQUE
wc_category_slug     TEXT NULL                    -- set only for top-level WC-derived topics
source               TEXT NOT NULL                -- 'wc_category' | 'llm_proposed' | 'user_created'
approved             INTEGER NOT NULL DEFAULT 0   -- proposals start false
created_at           DATETIME DEFAULT CURRENT_TIMESTAMP
```

### `content_topics` (join)
```
content_inventory_id INTEGER FK content_inventory.id NOT NULL
topic_id             INTEGER FK topics.id NOT NULL
confidence           REAL
assigned_by          TEXT NOT NULL                -- 'auto' | 'user'
UNIQUE (content_inventory_id, topic_id)
```

### `content_product_mentions`
```
content_inventory_id INTEGER FK content_inventory.id NOT NULL
wp_product_id        INTEGER NOT NULL
product_slug         TEXT NOT NULL
product_name         TEXT NOT NULL
mention_count        INTEGER NOT NULL DEFAULT 1
first_snippet        TEXT
match_type           TEXT NOT NULL                -- 'exact' | 'fuzzy' | 'url'
confidence           REAL NOT NULL
created_at           DATETIME DEFAULT CURRENT_TIMESTAMP
UNIQUE (content_inventory_id, wp_product_id)
```

Only holds mentions of products with WC status = `publish`. Discontinued-product mentions and species mentions go to `orphan_references` (reused, already in schema).

### `outbound_links`
```
id                   INTEGER PK
content_inventory_id INTEGER FK content_inventory.id NOT NULL
href                 TEXT NOT NULL
anchor_text          TEXT
link_type            TEXT NOT NULL                -- 'internal_content' | 'internal_product' | 'external' | 'anchor'
target_content_id    INTEGER FK content_inventory.id NULL
http_status          INTEGER NULL
last_checked_at      DATETIME NULL
INDEX (content_inventory_id)
INDEX (target_content_id)
```

### `decay_findings`
```
id                   INTEGER PK
content_inventory_id INTEGER FK content_inventory.id NOT NULL
rule_name            TEXT NOT NULL
severity             TEXT NOT NULL                -- 'critical' | 'warning' | 'info'
snippet              TEXT
suggested_action     TEXT
status               TEXT NOT NULL DEFAULT 'open' -- 'open' | 'resolved' | 'dismissed' | 'stale'
detected_at          DATETIME DEFAULT CURRENT_TIMESTAMP
resolved_at          DATETIME NULL
INDEX (content_inventory_id, status)
INDEX (rule_name, status)
```

### `wc_catalog_snapshot`
```
wp_product_id        INTEGER PK
slug                 TEXT NOT NULL UNIQUE
name                 TEXT NOT NULL
status               TEXT NOT NULL                -- 'publish' | 'draft' | 'private' | 'trash' | 'missing'
species_list         JSON                         -- parsed from ACF / product attrs
price                REAL NULL
permalink            TEXT
last_synced_at       DATETIME DEFAULT CURRENT_TIMESTAMP
```

### Reused table

`orphan_references` receives three new `reference_type` values:
- `inactive_product` — article mentions a product where WC status = `draft`
- `species_mention` — article mentions a species name (later judged by `DiscontinuedSpeciesRule`)
- `discontinued_species` — populated by the decay rule (species not in any `publish` product)

## Stages

### 1. `audit sync`

Pulls content + catalog via WP REST API (routes through CF Worker proxy when `CF_WORKER_URL` is set).

Fetches:
- `/wp/v2/posts?status=any&per_page=100` (paginated)
- `/wp/v2/pages?status=any&per_page=100` (paginated)
- `/wp/v2/product?status=any&per_page=100` (paginated — WooCommerce)

For each item:
- Upsert into `content_inventory` keyed on `wp_post_id` (preserves existing IDs)
- Store `content_html` (raw) and `content_text` (HTML-stripped, used by regex rules)
- Compute `word_count` from `content_text`

For each product, also upsert into `wc_catalog_snapshot` with status, slug, name, species list (from ACF or product attributes), price, permalink.

Idempotent. Rerunning updates changed rows. A `--force` flag re-syncs all rows even if unchanged.

### 2. `audit classify`

**Pass 1 — deterministic top-level assignment (`topics` with source=`wc_category`):**
- Seed `topics` once from the WC category list (e.g., Grass Seed, Pasture Seed, Wildflower Seed, Food Plot). `parent_topic_id=NULL`, `wc_category_slug` set, `approved=1`.
- For each article in `content_inventory`:
  - If article is a WC product → top-level topic = its category
  - If article's WP categories map to a WC category (by name or slug) → use that
  - Else → "Unclassified" bucket (auto-created top-level topic)
- Write `content_topics` row with `assigned_by='auto'`.

**Pass 2 — LLM subtopic proposal (`topics` with source=`llm_proposed`, `approved=0`):**
- For each top-level topic, sample 20-40 articles (or all if fewer) and call the LLM with their titles + first 500 chars
- LLM returns 3-7 proposed subtopic names + keyword phrases that define each
- Write proposed subtopics as `topics` rows with `parent_topic_id` set, `approved=0`
- Skip this pass if the topic already has approved subtopics (unless `--reclassify-subtopics`)

**Pass 3 — subtopic approval gate:**
- `nspipe audit classify --approve-subtopics` — shows pending proposals, user edits/approves via CLI prompts or by editing the DB directly
- Only approved subtopics participate in Pass 4

**Pass 4 — deterministic subtopic assignment:**
- For each article in a top-level topic, match against its approved subtopics' keyword phrases
- Write `content_topics` row for best-match subtopic with `assigned_by='auto'` and a confidence score
- Articles that match no subtopic stay classified only at top-level

Flags: `--reclassify` (re-run all assignments), `--reclassify-subtopics` (re-propose subtopics per topic).

### 3. `audit tag-products`

Per article in `content_inventory`:

1. **URL-based exact match:** scan `outbound_links` for links to product permalinks. For each match, write `content_product_mentions` (match_type=`url`, confidence=1.0) if WC status is `publish`, else `orphan_references` with `reference_type='inactive_product'`.

2. **Name-based exact match:** build a matcher from `wc_catalog_snapshot` product names (case-insensitive, punctuation-normalized). Scan `content_text`. For matches, write to appropriate table with match_type=`exact`, confidence=0.9.

3. **Name-based fuzzy match:** for product names not matched above, use a stemmed/tokenized fuzzy pass (threshold ≥ 0.85 Levenshtein). match_type=`fuzzy`, confidence=the similarity score.

4. **Species mentions:** build a flat set of species names from all `species_list` values in `wc_catalog_snapshot`. Scan `content_text`. Write unmatched species to `orphan_references` with `reference_type='species_mention'` (not yet judged — `DiscontinuedSpeciesRule` decides in the decay scan).

For multi-method matches on the same product, keep the highest-confidence row.

Idempotent — rerun clears prior rows for the article and re-populates.

### 4. `audit scan-links`

Per article:

1. Parse `content_html` with BeautifulSoup. Extract all `<a href>` + anchor text.
2. Classify each href:
   - `#...` → `anchor`
   - `naturesseed.com/products/...` or `naturesseed.com/product/...` → `internal_product`
   - Other `naturesseed.com/...` → `internal_content`; set `target_content_id` by matching URL to a `content_inventory.url`
   - Everything else → `external`
3. Upsert to `outbound_links` keyed on `(content_inventory_id, href)`.

**HTTP status checks:**
- Collect unique `href` values where `last_checked_at IS NULL OR last_checked_at < now() - 30 days`
- HTTP HEAD each (fall back to GET if HEAD returns ≥400). Rate-limit to 5 req/sec, concurrent with a semaphore.
- Update `http_status`, `last_checked_at`.
- Internal URLs where `target_content_id IS NULL` OR target `content_inventory.status != 'publish'` are effectively broken — this is surfaced in `DeadInternalLinkRule`, not here.

Flags: `--skip-http` (parse only, no HTTP checks), `--recheck-all` (ignore 30-day cache).

### 5. `audit scan-decay`

Run every rule in `audit_rules/` against every article. Rules are classes discovered via directory introspection, each with:

```python
class DecayRule(Protocol):
    name: str                                        # stable identifier
    severity: Literal['critical', 'warning', 'info']
    def check(self, content: ContentInventory, ctx: AuditContext) -> list[Finding]: ...
```

`AuditContext` provides pre-loaded access to `wc_catalog_snapshot`, this article's `outbound_links`, `content_product_mentions`, and `orphan_references`.

**Before running rules:** mark all existing `decay_findings.status='open'` for this article as `status='stale'`.

**After running rules:** for each finding a rule produces, upsert by `(content_inventory_id, rule_name, snippet_hash)`. Matching existing rows are re-activated to `status='open'` and `detected_at` refreshed. Findings that remain `stale` after the run (no rule re-detected them) are auto-transitioned to `status='resolved'` with `resolved_at=now()`.

**After all rules:** rebuild `refresh_queue` — one row per article that has ≥1 open finding, with `reason` = a short summary (e.g., "3 decay findings: discontinued product, dead internal link, outdated USDA map").

Flags: `--rule <name>` (run only one rule), `--article <id>` (run against one article).

### 6. `audit report`

Generates into `docs/content-audit/YYYY-MM-DD/`:

1. **`topic-map.md`** — hierarchical: topic → subtopic → articles, with product tags inline
2. **`topic-map.csv`** — flat: one row per article × topic × subtopic × product
3. **`per-article.md`** — one section per article: topic, products, outbound link counts, open decay findings with snippets
4. **`per-article.csv`** — flat summary: one row per article with aggregated counts and status
5. **`decay-findings.csv`** — every open finding (article, rule, severity, snippet, suggested_action)
6. **`internal-linking.md`** — for each article, list of pages it links to; separate reverse-view section showing what links *to* each article
7. **`internal-linking.csv`** — flat edge list: source_content_id, target_content_id, anchor_text
8. **`summary.md`** — top-level counts: articles by topic, top 10 decay signals by frequency, internal link density stats

Reports are deterministic from DB state — regeneratable any time. Written under a dated folder so past audits remain as committed history.

## Decay Rules Catalog

Each rule lives in `audit_rules/<rule_name>.py`, registered by directory discovery.

| # | Rule (class) | Detection | Severity | Type |
|---|---|---|---|---|
| 1 | `DiscontinuedProductRule` | `orphan_references.reference_type='inactive_product'` OR product in `content_product_mentions` where `wc_catalog_snapshot.status='draft'` | critical | deterministic |
| 2 | `DiscontinuedSpeciesRule` | `orphan_references.reference_type='species_mention'` where species not in `species_list` of any `publish` product → upsert row as `discontinued_species` + emit finding | critical | deterministic |
| 3 | `MissingProductCardRule` | Article has `content_product_mentions` for product P but no `outbound_links.href` containing P's permalink | warning | deterministic |
| 4 | `DeadExternalLinkRule` | `outbound_links` where `link_type='external' AND http_status IN (404, 410) OR http_status >= 500` | warning | deterministic |
| 5 | `DeadInternalLinkRule` | `outbound_links` where `link_type LIKE 'internal_%' AND (target_content_id IS NULL OR target content status != 'publish')` | critical | deterministic |
| 6 | `StaleDateRule` | Regex for years `\b(19\d{2}\|20[0-1]\d\|202[0-2])\b` in `content_text`, OR phrases "last year" / "this year" / "recently" within 50 chars of a year reference | warning | deterministic |
| 7 | `UsdaZoneMapRule` | Cheap filter: phrase match on "hardiness zone map" OR "USDA map" OR year ≤ 2022 near "hardiness". LLM judges whether flagged snippets reference the pre-2023 map | warning | LLM-assisted |
| 8 | `OutdatedShippingRule` | Cheap filter: regex on "free shipping" / dollar thresholds / "ships in \d days" / carrier names. LLM judges whether the claim matches current policy (current policy provided via config) | warning | LLM-assisted |
| 9 | `OutdatedPricingRule` | Regex `\$\d+(\.\d{2})?` in article where article mentions a product (from `content_product_mentions`); compare to current `wc_catalog_snapshot.price`. Flag if differs by >5% | info | deterministic |
| 10 | `ThinContentRule` | `content_inventory.word_count < 300` | info | deterministic |
| 11 | `SchemaGapRule` | Missing `<h1>` in HTML, no `target_keyword` set, no JSON-LD `<script type="application/ld+json">`, or meta description absent | info | deterministic |
| 12 | `ProductCategoryUrlRule` | `outbound_links.href` contains `/product-category/` (should be `/products/` per Permalink Manager) | critical | deterministic |

**LLM-assisted rules**: the cheap filter runs first and produces a list of candidate snippets. Only candidates go to the LLM, one call per article (batched snippets), with a strict JSON response schema. Cost cap: if a single run would exceed N tokens, the rule logs a warning and skips remaining candidates.

**Suggested action text**: each rule produces a human-readable string written to `decay_findings.suggested_action`. Examples:
- `DiscontinuedProductRule`: "Replace mention of `{old_slug}` with currently-sold `{suggested_active_slug}` or remove section"
- `MissingProductCardRule`: "Add product card or CTA linking to `{product_permalink}`"
- `ProductCategoryUrlRule`: "Rewrite URL from `/product-category/{slug}/` to `/products/{slug}/`"

## Configuration

Add to `config.py` (pydantic-settings, reads from `.env`):

```
WC_BASE_URL                (already present via CF Worker config)
WP_REST_USERNAME           (WP application password for REST auth)
WP_REST_PASSWORD
AUDIT_LLM_MODEL            default 'claude-sonnet-4-6'
AUDIT_CURRENT_SHIPPING     JSON or str describing current shipping policy (for OutdatedShippingRule)
AUDIT_HTTP_CHECK_CONCURRENCY  default 5
AUDIT_HTTP_CHECK_CACHE_DAYS   default 30
AUDIT_FUZZY_MATCH_THRESHOLD   default 0.85
AUDIT_THIN_WORD_COUNT         default 300
```

## Testing

pytest + fixtures. Each stage has its own test module.

**Fixtures:**
- `sample_content_inventory` — 5-10 representative articles (posts + pages + product) with known content
- `sample_wc_catalog` — products covering publish/draft/missing statuses with varying species lists
- `sample_outbound_links` — mix of internal/external/anchor, some 404s

**Stage tests:**
- `test_sync.py` — mocks WP REST responses, verifies upsert logic and HTML/text extraction
- `test_classify.py` — deterministic passes only (mock LLM for Pass 2), verifies topic assignment correctness on fixture articles
- `test_tag_products.py` — URL / exact / fuzzy matching, discontinued vs active routing
- `test_scan_links.py` — HTML parsing correctness, URL classification, HTTP mock
- `test_scan_decay.py` — one test per rule, using fixture articles with known findings. LLM-assisted rules use mocked LLM responses.
- `test_report.py` — snapshot tests on generated markdown (using `pytest-snapshot` or equivalent)

**Idempotency tests:** each stage, `run → run again → assert DB state unchanged`.

## Deliverables

1. **SQLite DB** (`naturesseed-content-pipeline/content_pipeline.db`) — canonical source, all new tables populated
2. **CLI commands** under `nspipe audit` — six new subcommands matching the stages above
3. **Reports** under `docs/content-audit/YYYY-MM-DD/` — committed to repo per audit run
4. **Alembic migration** adding the six new tables
5. **Test suite** covering each stage

## Out of scope / follow-ons

- **Retool dashboard** — DB view of topic map, decay findings, internal linking. Queued as a separate project once reports reveal what views are most useful.
- **Refresh brief generation** — `refresh_queue` rows feed the existing `refresh_planner.py` agent stub (empty today). Separate spec.
- **Internal linking automation** — the generated `internal-linking.csv` becomes the input for automation that proposes new internal links in existing articles. Separate spec.
- **Content generation automation** — gaps identified in the topic map (thin subtopics, missing coverage) feed the existing `writer.py` / `researcher.py` agent stubs. Separate spec.
