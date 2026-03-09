# Klaviyo API — Nature's Seed Email Marketing

> Invoke this skill whenever any agent needs to work with Klaviyo for email marketing, flows, segments, campaigns, or customer data.

## Connection Details

| Key | Value |
|-----|-------|
| Account ID | H627hn |
| Organization | Nature's Seed |
| Public API Key | H627hn |
| Private API Key | `KLAVIYO_API` from `.env` (pk_3e5ea...) |
| Default Sender | customercare@naturesseed.com |
| Timezone | US/Mountain |
| Industry | Ecommerce / Garden |
| Website | https://www.naturesseed.com/ |
| Address | 1697 W 2100 N, Lehi, UT 84043 |

## MCP Tools Available

This project has Klaviyo MCP tools connected. **Always prefer MCP tools over raw API calls.** Available tools:

| Tool | Purpose |
|------|---------|
| `klaviyo_get_account_details` | Account info |
| `klaviyo_get_lists` / `klaviyo_get_list` | Lists management |
| `klaviyo_get_segments` / `klaviyo_get_segment` | Segments |
| `klaviyo_get_flows` / `klaviyo_get_flow` | Flow details |
| `klaviyo_get_campaigns` / `klaviyo_get_campaign` | Campaign management |
| `klaviyo_get_campaign_report` | Campaign performance metrics |
| `klaviyo_get_flow_report` | Flow performance metrics |
| `klaviyo_get_metrics` / `klaviyo_get_metric` | Available metrics |
| `klaviyo_get_profiles` / `klaviyo_get_profile` | Customer profiles |
| `klaviyo_get_events` | Individual event records |
| `klaviyo_get_catalog_items` | Product catalog |
| `klaviyo_get_email_template` | Email template HTML |
| `klaviyo_create_email_template` | Create new template |
| `klaviyo_create_campaign` | Create campaign |
| `klaviyo_create_profile` | Create profile |
| `klaviyo_update_profile` | Update profile |
| `klaviyo_subscribe_profile_to_marketing` | Subscribe |
| `klaviyo_unsubscribe_profile_from_marketing` | Unsubscribe |
| `klaviyo_query_metric_aggregates` | Aggregate event data |
| `klaviyo_assign_template_to_campaign_message` | Link template to campaign |
| `klaviyo_upload_image_from_url` | Upload images |

**Important:** Always pass `model: "claude"` in MCP tool calls.

## Lists (10 Total)

| ID | Name | Opt-in | Purpose |
|----|------|--------|---------|
| **NLT2S2** | Newsletter | Single | Main newsletter signup |
| **Sy6vRV** | Customers | Single | Active customer list |
| **R2JDwR** | Customers - All Time | Double | Historical customers |
| **HzC8DX** | Old Email List | Double | Legacy list |
| **NBQVJZ** | Outlook Potential Buyers | Double | Prospecting |
| **QTBztw** | Stakeholder List | Double | Internal stakeholders |
| **R4heDK** | Hedgerow - Newsletter Sign Ups | Single | Hedgerow brand |
| **RKkMjQ** | ColdUSAfarms - first 1,000 safe | Double | Cold outreach |
| **RTjzWA** | Hedgerow - Counties and Municipalities | Double | Gov/institutional |
| **RtU3Ji** | Application Workshop Confirmation | Double | Event signups |

## Key Segments

| ID | Name | Purpose |
|----|------|---------|
| **RAQTca** | Champions (RFM) | Best customers - RFM based, starred |
| **JNTYgB** | Win-Back Opportunities | Lapsed customers (Placed Order based) |
| **QYWWV6** | BF/CM 2025 | Black Friday/Cyber Monday segment |
| **R3WfED** | Pasture Purchasers - All-Time | Pasture persona |
| **QPMErE** | Deer-Resistant Wildflower Mix | Product-specific |
| **QRzqyJ** | Rocky Mountain Wildflower Mix | Product-specific |
| **QSqEuY** | Tackifier Purchasers | Product-specific |
| **R48Vnd** | California Native Wildflower Mix | Regional segment |
| **R98FDu** | Perennial Ryegrass Blend | Product-specific |
| **QQxWg2** | Cold Email Pasture - Aug 2025 | Outreach cohort |

## Active Flows (Live)

| ID | Name | Trigger | Key Info |
|----|------|---------|----------|
| **NnjZbq** | 2025 - Welcome Series | Added to List | 3 emails, primary onboarding |
| **SxbaYQ** | Checkout Abandonment - GS | Metric | 3 emails, 3.5% click rate (needs improvement) |
| **Y7Qm8F** | Abandoned Cart Reminder | Metric | 2 emails, Added to Cart trigger |
| **Xz9k4a** | Browse Abandonment - Standard | Metric | 3 emails |
| **VvvqpW** | Winback Flow | Added to List | 2 emails, 0% click on email 2 (CRITICAL) |
| **VZsFVy** | Upsell Flow | Metric | 2 emails |
| **UZf9UD** | Sunset Flow | Added to List | 2 emails, list hygiene |
| **UhxNKt** | Shipment Flow - WooCommerce | Metric | 1 email, transactional |
| **SjDhxB** | OPERATIONAL - Accounting Batches | Metric | Internal ops |
| **TFkMLx** | Yard Plan Welcome Flow | Metric | New (Feb 2026) |

## Draft Flows (In Development) — 42 Total

Key drafts being developed:
- **WQBF89** — NS - Welcome Series (Upgraded)
- **SMZ5NX** — NS - Usage-Based Reorder Reminder
- **Ukxchg** — NS - Cross-Category Expansion
- Multiple persona-based flows: Lawn, Wildflower, Pasture, California
- Browse Abandonment variants by persona

## Key Metrics & Their IDs

### Email Metrics
| ID | Name | Integration |
|----|------|-------------|
| **LBjRM6** | Opened Email | Klaviyo |
| **JgwbZn** | Clicked Email | Klaviyo |
| **NpKKhz** | Received Email | Klaviyo |
| **MTYddd** | Bounced Email | Klaviyo |
| **HG7pzC** | Dropped Email | Klaviyo |
| **NwZfPQ** | Marked Email as Spam | Klaviyo |

### Order Metrics (IMPORTANT: Multiple Sources)
| ID | Name | Integration | Notes |
|----|------|-------------|-------|
| **VLbLXB** | Placed Order | WooCommerce | **Use this one for current data** |
| **MpBr6v** | Placed Order | Magento | Legacy |
| **VfuJ49** | Placed Order | Magento 2 | Legacy |
| **WpcPAe** | Ordered Product | WooCommerce | Item-level |
| **PP4mdB** | Ordered Product | Magento | Legacy item-level |

### Subscription Metrics
| ID | Name |
|----|------|
| **JPFQsA** | Subscribed to List |
| **Mn5m7r** | Unsubscribed from List |
| **RDUMLh** | Subscribed to Email Marketing |
| **UwnyvV** | Unsubscribed from Email Marketing |

### Custom/API Metrics
| ID | Name | Notes |
|----|------|-------|
| **UwVRsc** | Yard Plan Created | Custom feature metric |
| **WfLs7p** | Newsletter Signup | Form submission |
| **VcUYec** | Eligible for Shopper Approved Review | Review platform |
| **YtsvSz** | Shopper Approved Review Completed | Review platform |
| **RcBsPb** | Invoice Batch Generated | Internal ops |
| **T9tMHp** | Ticket Created | Support |
| **SQJSm8** | Ticket Closed | Support |

### SMS Metrics
| ID | Name |
|----|------|
| **QReyKP** | Sent SMS |
| **Xuyiww** | Received SMS |
| **RufBns** | Clicked SMS |

## Integrations Active in Account

- **WooCommerce** — Primary ecommerce (current)
- **Magento / Magento 2** — Legacy (still has historical data)
- **Meta Ads** — Facebook/Instagram advertising
- **Swell** — Loyalty/referral program
- **Vibe** — Advertising (impression tracking)
- **API** — Custom integrations (Yard Plan, Newsletter Signup)

## Catalog (100+ Products Synced)

Products synced from WooCommerce. SKU pattern: `{PREFIX}-{SPECIES}-{WEIGHT}`
- `CV-` = Cover/Conservation
- `PB-` = Pasture Blend
- `PG-` = Pure Grass
- Weights: `-5-LB`, `-10-LB`, `-25-LB-KIT`, `-50-LB-KIT`

All items status: Published, created January 28, 2026.

## Campaign Patterns

- **A/B/C testing** common (variation sends)
- **Smart Send Time** strategy used on scheduled campaigns
- **Tracking**: Opens + Clicks enabled
- **Sender**: customercare@naturesseed.com / "Nature's Seed"
- **Audience**: Segment-based targeting with exclusions

## Performance Benchmarks (From Audit)

| Flow | Open Rate | Click Rate | Target |
|------|-----------|------------|--------|
| Welcome Series | 50-69% | 2-4% | 5%+ |
| Checkout Abandonment | 45% | 3.5% | 5-10% |
| Abandoned Cart | 39-50% | 2% | 5%+ |
| Winback | 40% | 0-1.2% | CRITICAL FIX |
| Browse Abandonment | 40-45% | 1-3% | 3%+ |

## How to Get Performance Data

```
# Campaign report (use MCP tool)
klaviyo_get_campaign_report:
  statistics: ["open_rate", "click_rate", "conversion_rate", "recipients", "delivered"]
  conversionMetricId: "VLbLXB"  ← WooCommerce Placed Order
  timeframe: {"key": "last_30_days"}

# Flow report
klaviyo_get_flow_report:
  statistics: ["open_rate", "click_rate", "conversion_rate", "recipients"]
  conversionMetricId: "VLbLXB"
  timeframe: {"key": "last_30_days"}

# Revenue by flow (use query_metric_aggregates)
klaviyo_query_metric_aggregates:
  metricId: "VLbLXB"
  measurements: ["sum_value", "count"]
  groupBy: ["$attributed_flow"]
  startDate: "2025-03-01T00:00:00"
  endDate: "2026-03-01T00:00:00"
```

## Email Template Design Standards

From the brand skill (`natures-seed-brand`):
- CTA color: `#C96A2E` (orange)
- Primary green: `#2d6a4f`
- Body font: Inter
- Heading font: Noto Serif Display
- Subject lines: <50 chars, benefit-led
- Always include unsubscribe: `{% unsubscribe 'Unsubscribe' %}`

## Existing Email Templates (13 Created)

Located at `/Users/gabegimenes-silva/Desktop/ClaudeProjectsLocal/natures-seed-email-audit/`:
1. `01-welcome-email-1.html` through `13-spring-recovery-3.html`
- All follow Nature's Seed brand guidelines
- Mobile-responsive, clean design
