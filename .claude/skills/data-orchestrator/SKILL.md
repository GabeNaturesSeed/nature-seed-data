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
WALMART_CLIENT_ID     — Walmart OAuth client
WALMART_CLIENT_SECRET — Walmart OAuth secret
WC_BASE_URL           — WooCommerce REST API base
WC_CK                 — WooCommerce consumer key
WC_CS                 — WooCommerce consumer secret
KLAVIYO_API           — Klaviyo private API key
POSTMAN_API           — Postman API key
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
```
