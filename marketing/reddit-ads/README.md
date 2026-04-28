# Reddit Ads Catalog

Daily-regenerated Google-Shopping-spec product feed for Reddit Ads Manager.

## What this does

A GitHub Action runs daily at 6 AM UTC, pulls every in-stock published
WooCommerce product (one row per variation), writes
`docs/reddit-catalog/reddit_catalog.tsv`, and commits it to `main`.
GitHub Pages serves that file (Pages source is `main:/docs`) at:

`https://gabenaturesseed.github.io/nature-seed-data/reddit-catalog/reddit_catalog.tsv`

Reddit Ads Manager fetches that URL on its own daily schedule.

## One-time setup in Reddit Ads Manager

1. Reddit Ads Manager → **Catalog** → **Create Catalog**
2. Source: **Scheduled feed**
3. Feed URL: paste the URL above
4. Refresh frequency: **Daily**
5. Currency: **USD**
6. Save. First validation pass takes ~30 minutes.

Once the catalog populates, link it to a Catalog Sales campaign objective.

## Local development

```bash
pip install -r requirements.txt
python build_reddit_catalog.py
```

Reads `.env` from project root. If `CF_WORKER_URL` is unset, hits the
WC API directly (works from residential IPs only).

## Tests

```bash
pytest tests/ -v
```

All transform logic is pure-function — tests run with no network.

## Files

- `build_reddit_catalog.py` — orchestrator
- `transform.py` — pure functions: filter, format, build rows, write TSV
- `wc_client.py` — paginated WC fetch with retry, routes through CF Worker
- `docs/reddit-catalog/` — generated TSV + summary JSON, committed on every run (lives in `docs/` because GitHub Pages serves from there)
- `tests/` — unit tests + JSON fixtures
