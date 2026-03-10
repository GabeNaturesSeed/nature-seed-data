# Lessons Learned — Nature's Seed Data Projects

## Session: March 9, 2026 — Daily Report Pipeline

### Supabase API Patterns
1. **New API key format**: `sb_secret_*` keys are opaque tokens, NOT JWTs. Only use `apikey` header. Do NOT add `Authorization: Bearer` header — it will fail.
2. **Upsert requires explicit conflict columns**: PostgREST upsert with `GENERATED ALWAYS AS IDENTITY` columns fails without `on_conflict` query param. Always specify: `?on_conflict=col1,col2` + `Prefer: resolution=merge-duplicates`.
3. **Strip auto-generated columns**: Before upserting, remove `id`, `created_at`, `updated_at` from row dicts to avoid identity column conflicts.
4. **Env var naming**: Always double-check that script variable names match `.env` key names exactly. Caught `SUPABASE_SERVICE_KEY` vs `SUPABASE_SECRET_API_KEY` mismatch.

### Shippo API Gotchas
1. **No reliable date filtering**: `object_created_gt/lt` params don't work reliably. Must paginate ALL transactions and filter by `object_created[:10]` locally.
2. **Rate cost is separate**: Transaction objects don't have cost. Must call `/rates/{rate_id}` endpoint to get `amount`. Cache results to avoid redundant lookups.
3. **Deduplication needed**: Voided and recreated labels create duplicate SUCCESS transactions. Deduplicate by `tracking_number` to count each shipment once.
4. **Multi-parcel awareness**: Nature's Seed ships multiple bags per order. Each bag gets its own tracking number and transaction — this is expected, not a duplicate.

### Google OAuth
1. **Multi-scope tokens work**: One refresh token can cover Ads + Analytics + Merchant Center + Search Console. Use combined scope string in authorization URL.
2. **API must be enabled first**: Each Google API must be enabled in Cloud Console before it will accept requests, even with a valid token. Check for 403 "API not enabled" errors.

### Walmart API
1. **404 = no orders**: Walmart returns HTTP 404 when there are no orders for the given date range. Handle as empty result, not error.
2. **Revenue is nested deep**: `orderLines.orderLine[].charges.charge[]` → filter for `chargeType == "PRODUCT"` → `chargeAmount.amount`.

### WooCommerce
1. **Pull both statuses**: Orders can be in "completed" OR "processing" status. Pull both to get complete daily revenue.
2. **Pagination**: Use `X-WP-TotalPages` response header, not `X-WP-Total`, for page iteration.

### GitHub
1. **Collaborator access**: When pushing to an org repo from a personal account, the personal account must be added as a collaborator on the repo.
2. **Secrets naming**: GitHub Actions secrets can't have leading/trailing spaces. Trim values when adding.
3. **Repository vs Environment secrets**: Secrets must be added as **Repository secrets** (Settings → Secrets → Actions → Repository secrets). Environment secrets are scoped to specific environments and won't be available unless the workflow job specifies `environment:`. This distinction caused the CF Worker proxy to silently fail — secrets were empty, code fell back to direct WC API calls.

### Cloudflare
1. **Bot Fight Mode blocks datacenter IPs**: GitHub Actions, AWS, GCP, Azure — all datacenter IPs get JS challenges (403 + `CF-Mitigated: challenge`). This is NOT a WAF rule and CANNOT be bypassed with custom WAF rules on the free plan.
2. **WAF Skip action limitations (free plan)**: The "Skip" action only skips other custom rules and managed rules — it does NOT skip Bot Fight Mode, rate limiting, or other built-in protections.
3. **Cloudflare Workers bypass Bot Fight Mode**: Workers execute inside CF's network, so their `fetch()` calls to the same zone go through an internal path that bypasses security features. This is the only free-tier solution.
4. **Worker proxy pattern**: Accept secret header → validate → build origin URL → forward with auth → return response. Only pass through headers you need (Content-Type, X-WP-TotalPages, etc.).
5. **Debug CF blocks**: Check `CF-Mitigated` response header — `challenge` means Bot Fight Mode, not WAF. Also check `Server: cloudflare` + HTML body containing "Just a moment...".

### General Patterns
1. **Backfill vs daily pull**: For historical backfills, skip expensive operations (Shippo rate lookups, COGS matching) that aren't needed for YoY comparisons.
2. **Retool API limitations**: Can create resources but CANNOT create apps or queries programmatically. Dashboard must be built in UI.
3. **Always test with real data first**: Run a single-date pull before attempting backfill to catch schema/auth issues early.
