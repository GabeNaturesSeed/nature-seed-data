# SEO Content Audit — Runbook

How to run the six-stage content audit pipeline against live data. The spec is at `/docs/superpowers/specs/2026-04-24-seo-content-audit-design.md`; the implementation plan is at `/docs/superpowers/plans/2026-04-24-seo-content-audit.md`.

## Prerequisites

1. `.env` at `naturesseed-content-pipeline/.env` (gitignored) with:
   - `WC_BASE_URL=https://naturesseed.com` (no trailing slash)
   - `WP_USERNAME=...` (WP user)
   - `WP_APP_PASSWORD=...` (WP application password)
   - `WC_CK=...` (WooCommerce consumer key)
   - `WC_CS=...` (WooCommerce consumer secret)
   - `ANTHROPIC_API_KEY=...` (for LLM-assisted rules + subtopic proposals)
2. DB exists. For first-time setup:
   - `cd naturesseed-content-pipeline && uv run python -c "from naturesseed_pipeline.db.models import Base; from naturesseed_pipeline.db.session import engine; Base.metadata.create_all(engine)"`
   - Or if the DB is fresh and only has the existing pre-audit schema, `uv run alembic upgrade head` will add the 6 new audit tables.
3. CF Worker proxy is optional — leave `CF_WORKER_URL` unset for local runs; residential IP bypasses Bot Fight Mode.

## First run — full end-to-end

```bash
cd naturesseed-content-pipeline

# Stage 1 — pull every post, page, and product from WordPress
uv run nspipe audit sync

# Stage 2a — assign top-level topics (fast, deterministic) + propose subtopics via LLM
uv run nspipe audit classify
# Note the count of "LLM proposals" — those are pending your review.

# Stage 2b — review the LLM's subtopic proposals in a markdown file
uv run nspipe audit classify --export-proposals docs/content-audit/subtopic-proposals.md
# Open that file, read each section. To approve: leave as-is. To reject: delete the whole `## <Name>` section. To refine: edit the name/keywords.

# Stage 2c — apply your edits
uv run nspipe audit classify --import-approvals docs/content-audit/subtopic-proposals.md

# Stage 2d — now run classify once more so Pass 4 uses the approved subtopics
uv run nspipe audit classify

# Stage 3 — tag products and species in every article
uv run nspipe audit tag-products

# Stage 4 — extract and HTTP-check outbound links (can take a while for 100+ articles)
uv run nspipe audit scan-links
# For a faster first run, skip HTTP: uv run nspipe audit scan-links --skip-http

# Stage 5 — run all 12 decay rules, rebuild refresh_queue
uv run nspipe audit scan-decay

# Stage 6 — generate all reports (markdown + CSV)
uv run nspipe audit report
# Default output: docs/content-audit/YYYY-MM-DD/
```

Reports land in `docs/content-audit/YYYY-MM-DD/`:

- `topic-map.md` — hierarchical topic → subtopic → article list (human browsing)
- `topic-map.csv` — flat row-per-(article × product) — for spreadsheet work
- `per-article.md` — per-article section with decay findings, products mentioned
- `per-article.csv` — one row per article with aggregated counts
- `decay-findings.csv` — every open decay finding (the action list)
- `internal-linking.md` — outbound + inbound link view per article
- `internal-linking.csv` — flat edge list for graph analysis
- `summary.md` — top-level counts

## Re-running after content changes

All six stages are idempotent. Run the same commands again — existing rows are updated, new ones added, and `scan-decay` auto-resolves findings that no longer apply.

## Targeted reruns

```bash
# One rule across all articles
uv run nspipe audit scan-decay --rule DiscontinuedProductRule

# All rules against one article
uv run nspipe audit scan-decay --article 1234

# Re-classify everything (new approved subtopics, changed text)
uv run nspipe audit classify --reclassify

# Approve every pending subtopic without reviewing (not recommended, but fast)
uv run nspipe audit classify --approve-all
```

## Known pre-existing issue

The initial Alembic migration `c97dcec52018` is out of sync with current models — it creates only 14 of the 20 tables the codebase expects. The audit tables were added cleanly on top. Consequences:

- Existing databases (created via `db init` = `Base.metadata.create_all`) have all tables. Safe.
- A brand-new DB built solely from `alembic upgrade head` would miss: `competitor_domains`, `gsc_query_performance`, `media_index`, `orphan_references`, `redirects`, `refresh_queue`, `refresh_history`.
- **Fix when needed:** `uv run python -c "from naturesseed_pipeline.db.models import Base; from naturesseed_pipeline.db.session import engine; Base.metadata.create_all(engine)"` creates any missing tables without touching existing ones. A future task should autogenerate a bridging migration.

This is pre-existing and unrelated to the audit pipeline — noted for transparency.

## Verify installation (dry checks that don't hit the network)

```bash
# 1. Migrations apply cleanly to a fresh DB
DATABASE_URL="sqlite:///smoke.db" uv run alembic upgrade head
rm smoke.db

# 2. CLI wiring is clean
uv run nspipe audit --help   # should show 6 new subcommands + orphans

# 3. All 12 decay rules are registered
uv run python -c "from naturesseed_pipeline.audit_rules import discover_rules; \
  [print(r.name, r.severity) for r in sorted(discover_rules(), key=lambda r: r.name)]"

# 4. Full test suite
uv run pytest tests/
```
