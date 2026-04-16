# PARTY Setup Wizard — Design Specification

**Date:** 2026-04-15
**Status:** Draft
**Goal:** Make PARTY replicable for any ecommerce company through a guided onboarding wizard.

---

## Overview

A conversational wizard that interviews the user about their business, then generates:
1. A complete ClaudeDataAgent-style data hub (`.env`, skills, instructions)
2. A configured PARTY instance with agents tailored to their specific tech stack
3. Pre-populated AGENT.md files with API patterns for their platforms

The wizard itself runs as a PARTY agent — it's the first agent you talk to, and it builds the rest.

---

## How It Works

### Phase 1: Business Discovery (Conversation)

The wizard asks questions in order:

**Company Basics:**
- Company name
- Website URL
- Industry (ecommerce pre-selected, confirm)
- Annual revenue range (for complexity calibration)
- Team size (who will use PARTY?)

**Website Platform:**
- What platform? (Shopify / WooCommerce / BigCommerce / Magento / Custom)
- API credentials available? (guide them through getting keys)
- Custom fields or plugins? (ACF, Metafields, etc.)

**Advertising:**
- Google Ads? → get Customer ID, OAuth setup
- Meta/Facebook Ads? → get Account ID, access token
- Amazon Ads? → get profile ID
- TikTok Ads? → get advertiser ID
- Other? (Microsoft, Pinterest, etc.)

**Email Marketing:**
- Klaviyo / Mailchimp / Omnisend / ActiveCampaign / Other?
- API key available?
- How many subscribers? (complexity calibration)
- Active flows? Campaigns?

**Marketplaces:**
- Amazon Seller Central? → SP-API credentials
- Walmart Marketplace? → OAuth credentials
- eBay? → OAuth credentials
- Etsy? → API key
- Other?

**Shipping:**
- Shippo / ShipStation / EasyPost / carrier-direct?
- API key?

**Inventory:**
- Same as website? Or separate system?
- Fishbowl / Cin7 / TradeGecko / NetSuite / Custom?
- API access?

**Analytics:**
- Google Analytics? → Property ID
- Other analytics tools?

**Other Integrations:**
- CRM? (HubSpot, Salesforce, etc.)
- Help desk? (Zendesk, HelpScout, Intercom)
- Accounting? (QuickBooks, Xero)
- Review platform? (Yotpo, Stamped, Judge.me, Shopper Approved)

**Brand:**
- Brand voice description
- Primary colors (hex)
- Logo URL
- Target customer description

### Phase 2: Generation (Automated)

Based on answers, the wizard generates:

1. **`.env` file** — all credentials organized by system
2. **`CLAUDE.md`** — project instructions with rules specific to their stack
3. **Skills** — one per platform (copied from templates, customized with their IDs)
4. **Agents** — one per channel, with AGENT.md tailored to their setup
5. **`config.json`** — pointing to their `.env` and working directory

### Phase 3: Validation

The wizard tests each integration:
- Ping each API with the provided credentials
- Report which ones connected, which failed
- Guide fixes for failures

---

## Agent Templates (by Platform)

### Website Agents
| Platform | Template | Key Differences |
|----------|----------|-----------------|
| Shopify | shopify-api skill | GraphQL Admin API, REST fallback |
| WooCommerce | woocommerce-api skill | REST API v3, ACF fields |
| BigCommerce | bigcommerce-api skill | REST v2/v3, webhooks |

### Advertising Agents
| Platform | Template |
|----------|----------|
| Google Ads | google-ads skill (our existing one) |
| Meta Ads | meta-ads skill (Marketing API) |
| Amazon Ads | amazon-ads skill (Advertising API) |

### Email Agents
| Platform | Template |
|----------|----------|
| Klaviyo | klaviyo-api skill (our existing one) |
| Mailchimp | mailchimp-api skill |
| Omnisend | omnisend-api skill |

### Marketplace Agents
| Platform | Template |
|----------|----------|
| Amazon SP | amazon-sp skill (our existing one) |
| Walmart | walmart-api skill (our existing one) |
| eBay | ebay-api skill |

---

## Implementation Priority

1. **v1: The Wizard Agent** — conversational onboarding, generates .env + basic structure
2. **v2: Platform Templates** — skill templates for top 5 platforms (Shopify, Google Ads, Klaviyo, Amazon, Shippo)
3. **v3: Auto-Validation** — API credential testing
4. **v4: More Templates** — expand to cover 20+ platforms

---

## What We Need to Build

1. A "Setup Wizard" agent in PARTY (slug: `setup-wizard`)
2. A template library at `~/.party/templates/` with platform skills
3. A generation script that creates the full directory structure
4. Credential validation helpers per platform
