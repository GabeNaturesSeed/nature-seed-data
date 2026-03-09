# Data Orchestrator — Nature's Seed Unified Data Hub

> This is the master routing skill. Invoke this when an agent needs to understand which system holds what data, how systems connect, or how to route a data request across the Nature's Seed ecosystem.

## System Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NATURE'S SEED DATA ECOSYSTEM                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  WooCommerce  │    │   Fishbowl   │    │   Walmart Mktp      │  │
│  │  (Commerce)   │◄──►│  (Inventory) │───►│   (Marketplace)     │  │
│  │               │    │              │    │                      │  │
│  │ Products      │    │ Stock Levels │    │ Listings             │  │
│  │ Orders        │    │ SKU Mapping  │    │ Orders               │  │
│  │ Customers     │    │ Warehouses   │    │ Inventory            │  │
│  │ Coupons       │    │ Kit BOM      │    │ Pricing              │  │
│  │ Shipping      │    │ Weights      │    │                      │  │
│  └──────┬───────┘    └──────────────┘    └──────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Klaviyo     │    │    Stripe    │    │   Next.js Storefront │  │
│  │  (Marketing)  │    │  (Payments)  │    │   (Frontend)         │  │
│  │               │    │              │    │                      │  │
│  │ Email Flows   │    │ Transactions │    │ Product Pages        │  │
│  │ Segments      │    │ Refunds      │    │ Cart/Checkout        │  │
│  │ Campaigns     │    │ Disputes     │    │ Search               │  │
│  │ Profiles      │    │              │    │                      │  │
│  │ Catalog Sync  │    │              │    │                      │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │    Gmail      │    │   Postman    │    │   GitHub             │  │
│  │  (Comms)      │    │  (API Docs)  │    │   (Code)             │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  Supabase     │    │  Google Ads  │    │   Shippo             │  │
│  │  (Database)   │    │  + GA4 + GMC │    │   (Shipping)         │  │
│  │               │    │  + Search    │    │                      │  │
│  │ Daily Sales   │    │  Console     │    │ Label Costs          │  │
│  │ Ad Spend      │    │              │    │ Tracking             │  │
│  │ Shipping      │    │ Spend Data   │    │ Transactions         │  │
│  │ COGS          │    │ Analytics    │    │                      │  │
│  │ Goals         │    │ Products     │    │                      │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐                               │
│  │   Retool      │    │  Algolia     │                               │
│  │  (Dashboard)  │    │  (Search)    │                               │
│  └──────────────┘    └──────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

## "Where Is That Data?" Quick Reference

| I need... | Go to... | Skill | How |
|-----------|----------|-------|-----|
| Product catalog | WooCommerce | `woocommerce-api` | REST API `/products` |
| Product categories | WooCommerce | `woocommerce-api` | REST API `/products/categories` |
| Real-time stock levels | Fishbowl | `fishbowl-inventory` | Fishbowl API |
| Delivery time estimates | WooCommerce | `woocommerce-api` | ACF meta `delivery_time` (synced from Fishbowl) |
| Product weights | WooCommerce + Fishbowl | Both | WC `weight` field, Fishbowl for validation |
| Customer orders | WooCommerce | `woocommerce-api` | REST API `/orders` |
| Walmart orders | Walmart | `walmart-api` | `/v3/orders` |
| Customer profiles | Klaviyo | `klaviyo-api` | MCP `klaviyo_get_profiles` |
| Email engagement data | Klaviyo | `klaviyo-api` | MCP `klaviyo_get_campaign_report` / `get_flow_report` |
| Revenue data | Klaviyo | `klaviyo-api` | Metric ID `VLbLXB` (WC Placed Order) |
| Revenue by channel | Klaviyo + Walmart | Both | Klaviyo for WC, Walmart API for marketplace |
| Customer segments | Klaviyo | `klaviyo-api` | MCP `klaviyo_get_segments` |
| Email templates | Klaviyo | `klaviyo-api` | MCP `klaviyo_get_email_template` |
| Shipping config | WooCommerce | `woocommerce-api` | `/shipping/zones` + `/shipping_methods` |
| Coupon/promo data | WooCommerce | `woocommerce-api` | REST API `/coupons` |
| Sales reports | WooCommerce | `woocommerce-api` | `/reports/sales` |
| Payment data | Stripe (via WC) | `woocommerce-api` | `/wc_stripe/account` |
| Daily P&L / KPIs | Supabase | n/a | `daily_summary` view or `daily_sales` + `daily_ad_spend` tables |
| MTD vs last year vs goal | Supabase | n/a | `mtd_comparison` view |
| Ad spend (Google Ads) | Supabase or Google Ads | n/a | `daily_ad_spend` table or `pull_google_ads()` |
| Shipping costs | Supabase or Shippo | n/a | `daily_shipping` table or `pull_shippo()` |
| COGS by SKU | Supabase or Google Sheet | n/a | `cogs_lookup` table |
| Revenue goals | Supabase | n/a | `financial_goals` table |
| GA4 analytics | Google Analytics | n/a | Property `294622924` |
| Search performance | Google Search Console | n/a | `sc-domain:naturesseed.com` |
| Product feed data | Google Merchant Center | n/a | Merchant ID `138935850` |
| Site pages/URLs | Crawl data | n/a | `naturesseed_pages.csv` in ClaudeProjectsLocal |
| 404 redirects | Redirect data | n/a | `naturesseed_redirects.csv` in ClaudeProjectsLocal |
| Brand guidelines | Brand skill | `natures-seed-brand` | `~/.claude/skills/natures-seed-brand/SKILL.md` |

## Cross-System Data Flows (Automated)

| Source | Destination | Mechanism | Frequency |
|--------|-------------|-----------|-----------|
| Fishbowl stock | WC `delivery_time` | `sync_delivery_time.py` | On-demand script |
| WC orders | Klaviyo "Placed Order" | Klaviyo-WooCommerce integration | Real-time |
| WC products | Klaviyo catalog | Klaviyo-WooCommerce integration | Periodic sync |
| WC browse events | Klaviyo "Viewed Product" | Klaviyo JS tracking | Real-time |
| WC cart events | Klaviyo "Added to Cart" | Klaviyo-WooCommerce integration | Real-time |
| Customer signups | Klaviyo lists | Klaviyo forms | Real-time |

## Cross-System Data Flows (Manual / Needs Automation)

| Source | Destination | Current Method | Priority |
|--------|-------------|----------------|----------|
| WC products | Walmart listings | Manual upload | HIGH |
| Fishbowl stock | Walmart inventory | Not synced | HIGH |
| WC prices | Walmart prices | Manual update | HIGH |
| Walmart orders | WC/Fishbowl | Manual check | MEDIUM |
| WC product weights | Fishbowl weights | Audit scripts | LOW |

## Environment Variables Available (.env)

```
WALMART_CLIENT_ID             — Walmart OAuth client
WALMART_CLIENT_SECRET         — Walmart OAuth secret
WC_BASE_URL                   — WooCommerce REST API base
WC_CK                        — WooCommerce consumer key
WC_CS                        — WooCommerce consumer secret
KLAVIYO_API                   — Klaviyo private API key
POSTMAN_API                   — Postman API key
GOOGLE_ADS_DEVELOPER_TOKEN    — Google Ads API developer token
GOOGLE_ADS_CLIENT_ID          — Google OAuth client ID (shared across all Google APIs)
GOOGLE_ADS_CLIENT_SECRET      — Google OAuth client secret
GOOGLE_ADS_REFRESH_TOKEN      — Multi-scope token (Ads + GA4 + Merchant + Search Console)
GOOGLE_ADS_CUSTOMER_ID        — Google Ads customer ID (599-287-9586)
GOOGLE_ADS_LOGIN_CUSTOMER_ID  — Google Ads MCC ID (838-619-4588)
GOOGLE_ANALYTICS_PROPERTY_ID  — GA4 property (294622924)
GOOGLE_MERCHANT_CENTER_ID     — Merchant Center (138935850)
SHIPPO_API_KEY                — Shippo live API key
SUPABASE_URL                  — Supabase project URL
SUPABASE_SECRET_API_KEY       — Supabase secret key (sb_secret_* format)
RETOOL_API                    — Retool API key
```

## MCP Servers Connected

| Server | Tools Available | Use For |
|--------|-----------------|---------|
| **Klaviyo** | 20+ tools (see `klaviyo-api` skill) | All Klaviyo operations |
| **Postman** | 30+ tools (workspace, collection, env CRUD) | API documentation |
| **Gmail** | Search, read, draft, send | Customer communications |
| **Chrome** | Browser automation, screenshots | Visual testing, scraping |

## Project Locations

| Project | Path | Purpose |
|---------|------|---------|
| **Data Agent (this)** | `~/Desktop/ClaudeDataAgent -/` | Orchestrator hub |
| **Next.js Storefront** | `~/Desktop/woodmart2:16-ClaudeWork/` | Headless frontend |
| **Data Scripts** | `~/Desktop/ClaudeProjectsLocal/` | Python sync/audit scripts |
| **Email Audit** | `~/Desktop/ClaudeProjectsLocal/natures-seed-email-audit/` | Klaviyo templates & audit |
| **Inventory Helper** | `~/Desktop/CascadeProjects/Naturesseed inventory helper/` | Demand forecasting |
| **Brand Skill** | `~/.claude/skills/natures-seed-brand/SKILL.md` | Brand guidelines |

## Token-Saving Patterns

### Instead of exploring, use these shortcuts:

**"What products do we sell?"**
→ `curl -s -u "$WC_CK:$WC_CS" "$WC_BASE_URL/products/categories?per_page=100"` for category tree
→ Or MCP: `klaviyo_get_catalog_items` for synced catalog

**"How are our emails performing?"**
→ MCP: `klaviyo_get_campaign_report` with `conversionMetricId: "VLbLXB"` and `timeframe: {"key": "last_30_days"}`

**"What's our revenue?"**
→ MCP: `klaviyo_query_metric_aggregates` with `metricId: "VLbLXB"`, `measurements: ["sum_value"]`

**"How many orders this month?"**
→ WC: `curl -s -u "$WC_CK:$WC_CS" "$WC_BASE_URL/reports/orders/totals"`

**"What's in stock?"**
→ Check Fishbowl via scripts in `ClaudeProjectsLocal/`
→ Or check WC: `curl -s -u "$WC_CK:$WC_CS" "$WC_BASE_URL/products?stock_status=instock&per_page=100"`

**"What email flows are active?"**
→ MCP: `klaviyo_get_flows` with filter `status: "live"`

**"Customer lookup"**
→ MCP: `klaviyo_get_profiles` with email filter for marketing data
→ WC: `/customers?email=...` for order data

## Decision Tree: Which API Should I Call?

```
Need product/catalog data?
  ├── Browsing/display → WC Store API v1 (no auth)
  ├── Admin/edit → WC REST API v3 (auth required)
  └── Marketing context → Klaviyo catalog (MCP)

Need order data?
  ├── WooCommerce orders → WC REST API v3
  ├── Walmart orders → Walmart API v3
  └── Combined revenue → Klaviyo metric VLbLXB + Walmart API

Need customer data?
  ├── Purchase history → WC REST API v3 /customers
  ├── Email engagement → Klaviyo profiles (MCP)
  ├── Segment membership → Klaviyo segments (MCP)
  └── Support tickets → Klaviyo metric T9tMHp

Need inventory data?
  ├── Source of truth → Fishbowl API
  ├── Current WC stock → WC REST API /products (stock_quantity)
  └── Delivery estimate → WC meta delivery_time

Need marketing data?
  ├── Campaign performance → Klaviyo campaign report (MCP)
  ├── Flow performance → Klaviyo flow report (MCP)
  ├── Email templates → Klaviyo get_email_template (MCP)
  └── Customer segments → Klaviyo segments (MCP)

Need to create content?
  ├── Email → Invoke natures-seed-brand skill FIRST, then Klaviyo MCP
  ├── Product copy → Invoke natures-seed-brand skill
  └── Any customer-facing → ALWAYS invoke natures-seed-brand skill

Need reporting / KPI data?
  ├── Daily P&L → Supabase `daily_summary` view
  ├── MTD vs last year / goal → Supabase `mtd_comparison` view
  ├── Ad spend trends → Supabase `daily_ad_spend` table
  ├── Shipping costs → Supabase `daily_shipping` table
  ├── COGS lookup → Supabase `cogs_lookup` table
  └── Revenue goals → Supabase `financial_goals` table

Need Google ecosystem data?
  ├── Ad spend / clicks / ROAS → Google Ads API or Supabase (backfilled)
  ├── Site traffic / pageviews → GA4 Property 294622924
  ├── Product feed / shopping → Merchant Center 138935850
  └── Search queries / rankings → Search Console sc-domain:naturesseed.com
```

## Supabase API Patterns

**Auth**: Only `apikey` header needed (no `Authorization: Bearer`). Keys are `sb_secret_*` format (opaque, not JWT).

**Upsert**:
```python
url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={unique_cols}"
headers = {"apikey": KEY, "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"}
requests.post(url, headers=headers, json=rows)
```

**Query**:
```python
url = f"{SUPABASE_URL}/rest/v1/{table}?select=*&report_date=gte.2026-01-01&order=report_date.desc"
headers = {"apikey": KEY}
requests.get(url, headers=headers)
```
