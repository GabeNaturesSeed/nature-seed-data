# Nature's Seed — Data Hub

Credentials: `.env` (spaces around `=`, quotes around values — parse manually).
Skills: `.claude/skills/` — read before working on any system.

## Key Rules
- `.env` parsing: `line.split('=', 1)` then `.strip().strip("'\"")`
- URLs: NEVER `/product-category/` — always `/products/` (Permalink Manager)
- WC rate limit: 0.3s between calls. Use CF Worker proxy when `CF_WORKER_URL` set
- Walmart: `WM_SEC.ACCESS_TOKEN` header (NOT `Authorization: Bearer`), 15-min token expiry
- Klaviyo: revision `2024-07-15`, MCP for template assignment, starred segments only
- Google OAuth: single refresh token for Ads+GA4+Merchant+GSC
- Supabase: `apikey` header only, upsert needs `on_conflict` + `Prefer: resolution=merge-duplicates`
- Reporting: WooCommerce revenue ONLY — exclude marketplace channels
- Subagents: use for file reads, API calls, research. Keep context clean.
- No emojis. Direct answers. Code over prose.

## Structure
```
infrastructure/daily-report/  — Supabase pipeline
infrastructure/cloudflare-worker/ — WC API proxy
marketing/google-ads-audit/   — ads scripts
marketing/klaviyo-audit/      — email campaigns
store/product-updates/        — WC product ops
marketplaces/                 — Walmart, Amazon
seo/                          — GSC, Algolia, IS
.claude/skills/               — API docs per system
```

## IDs
Google Ads: 599-287-9586 (login: 838-619-4588)
GA4: 294622924 | Merchant: 138935850
Klaviyo: H627hn | Metric VLbLXB (Placed Order)
Supabase: zoeuacgxthkiemzyunsd.supabase.co
