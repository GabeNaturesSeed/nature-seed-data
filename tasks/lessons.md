# Lessons Learned — Nature's Seed Data Projects

## Session: March 10, 2026 — Google Ads Order Attribution & Shopping Benchmarking

### WooCommerce Order Attribution
1. **GCLID is captured**: WooCommerce stores full attribution data in order meta. Key fields:
   - `_wc_order_attribution_session_entry` — full landing URL with `gclid` and `gad_campaignid` as query params
   - `_wc_order_attribution_utm_source`, `_wc_order_attribution_utm_medium`, `_wc_order_attribution_utm_campaign`
   - `_wc_order_attribution_device_type`
2. **Parse GCLID from URL**: Use `urllib.parse.urlparse` + `parse_qs` on `_wc_order_attribution_session_entry` to extract `gclid` and `gad_campaignid`.
3. **95% guest checkouts from Google Ads**: Most Google Ads orders have `customer_id=0`, strongly indicating new customers. Use `billing_email` first occurrence within the analysis window for new customer detection.

### PMax Sub-Campaign IDs
4. **PMax generates invisible sub-campaign IDs**: Campaign IDs in click URLs (`gad_campaignid`) often don't match any campaign in the Google Ads API. These are PMax auto-generated sub-campaigns. Group all unknown IDs with their parent PMax campaign for spend attribution.
   - Known PMax parents: `22944456167` (PMAX | Catch all), `23453477009` (PMAX - Search)

### Google Ads API — shopping_performance_view
5. **`segments.date` requires `campaign.id` in SELECT**: When querying `shopping_performance_view` with `segments.date` in SELECT and filtering by `campaign.id` in WHERE, `campaign.id` MUST also be in the SELECT clause. The API returns an explicit error otherwise.
6. **Daily normalization for fair comparison**: When benchmarking products, use average daily metrics (spend/day, clicks/day) on days with actual spend rather than raw totals. Products running for different durations need per-day normalization for fair comparison.
7. **Waste score formula**: `(daily_spend_normalized * 0.5) + (inverse_roas_normalized * 0.5)` — balances high daily spend against poor returns.

### .env Parsing
8. **Nature's Seed `.env` has spaces around `=`**: Cannot `source .env` in bash. Must parse manually in Python with `line.split('=', 1)` and `.strip()`.

## Session: March 10, 2026 — Klaviyo Campaign Creation

### Klaviyo API — Campaign Creation
1. **Revision header controls field names**: The `revision` header determines the schema. `2024-10-15` uses camelCase (`campaignMessages`, `sendStrategy`), but `2024-07-15` uses hyphenated/snake_case (`campaign-messages`, `send_strategy`). The MCP tool abstracts this away.
2. **Working revision for campaigns**: Use `revision: 2024-07-15` with these field names:
   - `campaign-messages` (hyphenated, not camelCase)
   - `send_strategy` with `options_static.datetime` and `options_static.is_local`
   - Campaign message `attributes` needs `channel: "email"` and `content` (not `definition`)
   - Content fields: `subject`, `preview_text`, `from_email`, `from_label` (snake_case)
3. **Template assignment only via MCP**: The Klaviyo REST API does NOT support `template` as a relationship on `campaign-messages` in ANY revision. Use the MCP tool `klaviyo_assign_template_to_campaign_message` instead.
4. **`send_past_recipients_immediately` requires `is_local: True`**: Don't include this field when `is_local` is False.
5. **Batch workflow**: Create templates via REST API → Create campaigns via REST API → Assign templates via MCP tool. The first two are fast (REST), the last requires individual MCP calls.

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
3. **Variant ordering — smallest first**: When creating/updating variable product variations, always order the `options` array in the parent product's Size attribute from smallest to largest. This ensures the frontend dropdown displays correctly AND bulk discount labels (e.g., "10% Bulk Discount") work properly. Also set `default_attributes` to the smallest variant. The attribute `options` array order controls the dropdown — `menu_order` on individual variations is unreliable.

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

## Session: March 11, 2026 — Product Content Updates & Klaviyo Flow Improvement

### .env Parsing (Critical Fix)
1. **Values have quotes, not just spaces**: Rule 20 covers `=` spaces but values are ALSO quote-wrapped (e.g., `'ck_xxx'`). Must call `.strip("'\"")` on both key and value after `.strip()`. Skipping this causes 401 API errors that look like credential failures.
   - Correct pattern: `k, v = line.split('=', 1); env[k.strip().strip("'\"")] = v.strip().strip("'\"")`

### WooCommerce Product API
2. **Variation IDs return thin data**: `/products/{variation_id}` gives `type: "variation"` with `parent_id` but NO description, ACF meta_data, or full attributes. Always resolve to parent first: `/products/{parent_id}`.
3. **ACF fields live in `meta_data`**: Product content fields (`product_content_2`, `product_card_content_1-5`, `answer_content_1-6`, etc.) are in the `meta_data` array. Access via `{m['key']: m['value'] for m in product['meta_data']}`.
4. **Update ACF via meta_data payload**: `PUT /products/{id}` with `{"meta_data": [{"key": "field_name", "value": "content"}]}`. Works for both standard and ACF fields.

### Klaviyo Flow API Limitations
5. **Flow message editing is UI-only**: Cannot update flow message subject lines, content, or assign templates via REST API or MCP. Can only CREATE templates. Campaign messages support MCP template assignment; flow messages do not.
6. **Browse abandonment key variables**: Klaviyo "Viewed Product" event exposes `event.ProductName`, `event.URL`, `event.ImageURL`, `event.Price`, `event.Categories` in Liquid. Use these for dynamic personalization.
