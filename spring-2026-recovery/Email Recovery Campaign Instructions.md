# Email Recovery Campaign Instructions

> Context document for agents working on the Nature's Seed Spring 2026 Recovery campaign.
> Created: 2026-03-02 | Source project: `~/Desktop/ClaudeProjectsLocal/natures-seed-email-audit/`

---

## 1. What Was Done (Summary)

### Phase 1 — Full Klaviyo Email Flow Audit & Rebrand

We audited every active and draft (`NS`-prefixed) email flow in the Nature's Seed Klaviyo account, then built 10 fully branded HTML email templates from scratch. Each template uses:

- **Nature's Seed brand system:** `#2d6a4f` primary green, `#C96A2E` CTA orange, `#1b4332` dark green, `#f0f7f3` light green background, `#fef9f4` warm accent background
- **Typography:** Noto Serif Display for headings, Inter for body text
- **Table-based layout** with MSO conditionals for Outlook, responsive media queries at 620px
- **Real CDN images** extracted from existing Klaviyo templates
- **Real Klaviyo dynamic codes** extracted from active flow templates
- **CAN-SPAM compliance:** `{{ organization.name }}`, `{{ organization.full_address }}`, `{% unsubscribe %}`, `{% manage_preferences %}`
- **Shipping policy:** Free shipping on all orders up to 100 lbs, then $80 per 25 lb after that

### Phase 2 — Spring Product Recovery Campaign (3 Emails)

Built a 3-email recovery campaign targeting previous customers who bought discontinued regional products, guiding them to the new USDA zone-based equivalents.

---

## 2. All Templates Created

### Flow Templates (10) — In Klaviyo, awaiting manual assignment to flows

| # | File | Klaviyo Template ID | Target Flow ID | Purpose |
|---|------|--------------------:|:--------------:|---------|
| 01 | `01-welcome-email-1.html` | `QXkeww` | `WQBF89` | Welcome series opener |
| 02 | `02-abandoned-cart.html` | `VBxPXM` | N/A (standalone) | Cart recovery |
| 03 | `03-browse-abandonment.html` | `RhBZSD` | `V2q3uA` | Browse abandonment |
| 04 | `04-winback.html` | `XetWL3` | `WpFDg7` | Win-back |
| 05 | `05-post-purchase-category.html` | `VR66U2` | `XdYcJ3` | Post-purchase cross-sell |
| 06 | `06-reorder-reminder.html` | `TjAajm` | `SMZ5NX` | Reorder reminder |
| 07 | `07-cross-category.html` | `S27iPr` | `Ukxchg` | Cross-category upsell |
| 08 | `08-vip-loyalty.html` | `XPHKay` | `X5iW5B` | VIP loyalty |
| 09 | `09-lapsed-recapture.html` | `Tp9Ezv` | `UDPtYM` | Lapsed customer recapture |
| 10 | `10-seasonal-reorder.html` | `RHJ3zQ` | `Vzp5Nb` | Seasonal reorder nudge |

> **Action needed:** The Klaviyo API does not support assigning templates to flow messages. Each template must be manually assigned in the Klaviyo UI by opening the flow, clicking the email action, and selecting the template.

### Campaign Templates (3) — In Klaviyo, assigned to draft campaigns

| # | File | Klaviyo Template ID | Campaign ID | Message ID |
|---|------|--------------------:|:-----------:|:----------:|
| 11 | `11-spring-recovery-1.html` | `TfFpUK` | `01KJQTPVJRM4PMFMKWC1Z2D5XQ` | `01KJQTPVK6GW3M9AKBA48AF1NA` |
| 12 | `12-spring-recovery-2.html` | `W9u824` | `01KJQTQ8GBR18R5YTJHWM7ZRF6` | `01KJQTQ8GRXK7VZQC4Y7ZM53TH` |
| 13 | `13-spring-recovery-3.html` | `UhBueT` | `01KJQTQCCZKSRZ02RET2ZGJGD7` | `01KJQTQCDCK4MW2B35JS9MZKX1` |

All 3 campaigns are in **Draft** status, targeting segment `R3WfED` (Pasture Purchasers - All-Time).

---

## 3. Spring Recovery Campaign Details

### Campaign Strategy

Nature's Seed switched from 16+ regional seed products (e.g., "Pacific Northwest Horse Forage Mix") to 3 USDA zone-based products (Cool Season / Transitional / Warm Season). Previous customers who bought the old regional products are not returning because they can't find their old product. This campaign re-engages them.

### Email 1 — "Your Favorite Mix Got an Upgrade" (Week 1)

- **Subject:** `Your Favorite Mix Got an Upgrade{% if first_name %}, {{ first_name }}{% endif %}`
- **Preview:** "We upgraded your pasture blend to a USDA zone-based formula - same quality, better science."
- **Goal:** Education. Explain the transition, show the 3 USDA zones, present their personalized replacement product.
- **Dynamic content:** Uses `{{ person|lookup:'ns_p1_name' }}` for old product name, `{{ person|lookup:'ns_p1_replacement_name' }}` etc. for replacement product data.
- **No discount** — pure education & trust-building.

### Email 2 — "Spring Planting Season Is Here" (Week 2)

- **Subject:** `Your Planting Window Is Opening{% if first_name %}, {{ first_name }}{% endif %} - 10% Off Inside`
- **Preview:** "Your spring planting window is opening - use code SPRING10 for 10% off"
- **Goal:** Urgency + incentive. Planting calendar by zone, 10% off with code `SPRING10`.
- **Key section:** Spring Planting Calendar showing planting windows for all 3 zones.

### Email 3 — "Last Call - Don't Miss Peak Planting" (Week 3)

- **Subject:** `Last Call{% if first_name %}, {{ first_name }}{% endif %} - 15% Off Your Zone-Matched Blend`
- **Preview:** "Final chance: 15% off your zone-matched pasture blend with code COMEBACK15"
- **Goal:** Final push with increased urgency + deeper discount (15%, code `COMEBACK15`).
- **Key sections:** Orange urgency banner, testimonials (Sarah M./Oregon, Jim R./Texas), trust stats (4.8/5, 25K+, 100% Non-GMO).

### Discount Codes Required

| Code | Discount | Used In |
|------|----------|---------|
| `SPRING10` | 10% off | Email 2 |
| `COMEBACK15` | 15% off | Email 3 |

These need to be created in WooCommerce before sending.

---

## 4. Profile Properties (from this project's data pipeline)

The `push_replacement_properties.py` script in `spring-2026-recovery/scripts/` pushes these custom profile properties to Klaviyo:

| Property | Description | Example |
|----------|-------------|---------|
| `ns_p1_name` | Discontinued product they bought | "Pacific Northwest Horse Forage Mix - 25 lbs" |
| `ns_p1_sku` | SKU of discontinued product | "PB-PNWHF-25-LB-OLD" |
| `ns_p1_status` | Always "discontinued" | "discontinued" |
| `ns_p1_replacement_name` | Recommended replacement product | "Cold Season Horse Forage Mix" |
| `ns_p1_replacement_sku` | Replacement SKU | "PB-NRHF" |
| `ns_p1_replacement_url` | Product page URL | "https://naturesseed.com/products/..." |
| `ns_p1_replacement_price` | Price | "149.99" |
| `ns_p1_replacement_image` | Product image URL | "https://naturesseed.com/wp-content/..." |
| `ns_p1_replacement_bullets` | Selling points (pipe-separated) | "USDA zone-matched | Agronomist-designed | ..." |
| `ns_draft_hit` | Flag for segment/flow targeting | `true` |
| `primary_seed_category` | Customer's primary category | "Pasture", "Lawn", "Clover", etc. |

### How the Templates Reference These Properties

```
{{ person|lookup:'ns_p1_name'|default:'your previous seed mix' }}
{{ person|lookup:'ns_p1_replacement_name'|default:'a premium seed product' }}
{{ person|lookup:'ns_p1_replacement_url'|default:'https://naturesseed.com/products/' }}
{{ person|lookup:'ns_p1_replacement_price'|default:'' }}
{{ person|lookup:'ns_p1_replacement_image' }}
```

The `campaign1_dynamic_replacement.html` template in `spring-2026-recovery/campaigns/` also uses these properties for the data-driven version.

---

## 5. Region-to-Zone Product Mapping

### USDA Zone Mapping

| USDA Zone | Old Regional Products | New Product Prefix |
|-----------|----------------------|-------------------|
| **Cool Season (Northern)** | Pacific Northwest, Great Lakes/New England, Intermountain West, Northeast | "Cold Season [Livestock] Forage Mix" |
| **Warm Season (Southern)** | Florida Tropics, Southern Subtropics, Southwest Desert, Southwest Semi-Arid Steppe | "Warm Season [Livestock] Forage Mix" |
| **Transitional Zone (Central)** | South-Atlantic Transitional, Mid-West/Mid-Atlantic, Great Plains, Southwest Transitional | "Transitional [Livestock] Forage Mix" |

### Complete Product Categories Affected

- **Pasture/Forage:** Horse, Cattle, Sheep, Goat, Pig, Deer, Elk, Llama/Alpaca, General Pasture
- **Lawn:** Replaced regional lawn mixes with zone-appropriate turf blends
- **Wildflower:** Regional wildflower mixes replaced with zone-matched mixes
- **Clover:** Regional clover mixes consolidated

The full replacement mapping (359 entries) is in:
- `spring-2026-recovery/analysis/replacement_map_final.json` (structured, with match scores, bullets, images)
- `spring-2026-recovery/analysis/replacement_map_final.csv` (flat CSV version)
- `spring-2026-recovery/analysis/category_replacement_products.json` (grouped by category with revenue data)

Unmatched products (no clear replacement found) are logged in:
- `spring-2026-recovery/analysis/unmatched_discontinued_products.csv`

---

## 6. Key Klaviyo IDs

### Lists

| Name | ID | Notes |
|------|:--:|-------|
| Customers - All Time | `R2JDwR` | Full customer list |
| Customers | `Sy6vRV` | Single opt-in, updated Feb 2025 |
| Newsletter | `NLT2S2` | Newsletter subscribers |
| Old Email List | `HzC8DX` | Legacy list |

### Segments

| Name | ID | Notes |
|------|:--:|-------|
| **Pasture Purchasers - All-Time (Woo + Magento)** | `R3WfED` | **Used as campaign audience** |
| Win-Back Opportunities | `JNTYgB` | Lapsed customers |
| Champions (RFM) | `RAQTca` | Top-tier RFM segment |
| BF/CM 2025 | `QYWWV6` | Black Friday / Cyber Monday |
| Warm Season Sheep Pasture Mix | `RAQx4u` | SKU-specific |
| Pig Forage Mix Purchasers | `RE7tEZ` | SKU-specific |
| Southern Sheep Forage Mix Purchasers | `RLCYbs` | SKU-specific |
| Purchased Lawn Seed | `RNkiLg` | Category segment |

### Metrics

| Name | ID | Notes |
|------|:--:|-------|
| Placed Order (WooCommerce) | `VLbLXB` | **Use as `conversionMetricId` in API calls** |
| Ordered Product | `WpcPAe` | Individual product orders |
| Ordered Product (alt) | `X3UByC` | Alternative ordered product metric |
| Placed Order (legacy) | `MpBr6v` | Older metric |

### CDN Image URLs

```
Logo:    https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/907e11d1-8cf0-420f-81cc-be3ecea762be.png
Hero:    https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/cf7f31c5-0967-48bb-8c89-79ec6b03889f.png
Social:  https://d3k81ch9hvuctc.cloudfront.net/assets/email/buttons/subtle/{platform}_96.png
```

---

## 7. Remaining Action Items

### Must-Do Before Sending

- [ ] **Create WooCommerce coupon codes** — `SPRING10` (10% off) and `COMEBACK15` (15% off)
- [ ] **Verify profile properties are pushed** — Run `push_replacement_properties.py` if not already done. Check `replacement_push_report.csv` for status.
- [ ] **Assign flow templates in Klaviyo UI** — Open each NS flow, click the email action, select the matching template from the table in Section 2.

### Recommended: Convert Campaigns to a Klaviyo Flow

The 3 campaigns were created as separate drafts because the Klaviyo API doesn't support flow creation. For the intended behavior (weekly drip + purchase exit), the best approach is:

1. Create a new Flow in the Klaviyo UI triggered by segment entry into "Pasture Purchasers - All-Time" (`R3WfED`)
2. Add 3 email actions with **7-day time delays** between each
3. Add a **Conditional Split** before Emails 2 and 3:
   - Condition: "Has Placed Order **zero times** since starting this flow"
   - YES branch: continue to next email
   - NO branch: exit flow (they purchased, mission accomplished)
4. Assign templates `TfFpUK`, `W9u824`, `UhBueT` to the 3 email actions

### Alternative: Keep as Campaigns (Simpler, Manual)

If staying with campaigns:

1. Schedule Email 1 immediately
2. Schedule Email 2 one week later
3. Schedule Email 3 two weeks later
4. Before each subsequent send, create an **exclusion segment**: "Placed Order at least once after [Email 1 send date]" and exclude from Emails 2 and 3

### Optional Enhancements

- [ ] **Category-specific campaign variants** — The `spring-2026-recovery/campaigns/` folder has category-specific templates for Pasture, Lawn, Clover, and Wildflower customers. These could be used for more targeted messaging.
- [ ] **SMS companion messages** — Add SMS touchpoints between emails for omnichannel coverage
- [ ] **Seed Quiz CTA tracking** — Set up event tracking for the Seed Quiz link (`https://naturesseed.com/seed-quiz/`) to measure engagement

---

## 8. File Locations

### Source Templates (HTML)

```
~/Desktop/ClaudeProjectsLocal/natures-seed-email-audit/
  01-welcome-email-1.html          # Flow template
  02-abandoned-cart.html            # Flow template
  03-browse-abandonment.html        # Flow template
  04-winback.html                   # Flow template
  05-post-purchase-category.html    # Flow template
  06-reorder-reminder.html          # Flow template
  07-cross-category.html            # Flow template
  08-vip-loyalty.html               # Flow template
  09-lapsed-recapture.html          # Flow template
  10-seasonal-reorder.html          # Flow template
  11-spring-recovery-1.html         # Campaign Email 1
  12-spring-recovery-2.html         # Campaign Email 2
  13-spring-recovery-3.html         # Campaign Email 3
  AUDIT-REPORT.md                   # Full flow audit report
```

### Data & Scripts (this project)

```
~/Desktop/ClaudeDataAgent -/spring-2026-recovery/
  data/
    products_active.json             # All active WC products (26MB)
    products_inactive.json           # All inactive WC products (12MB)
    categories.json                  # WC category tree
    orders_q1_2025.json              # Q1 2025 order history
    orders_q2_2025.json              # Q2 2025 order history
    orders_2024_q3q4.json            # Q3-Q4 2024 order history
    orders_2025_q3.json              # Q3 2025
    orders_2025_q4.json              # Q4 2025
    orders_2026_q1.json              # Q1 2026

  analysis/
    replacement_map_final.json       # 359-entry product replacement mapping
    replacement_map_final.csv        # Flat CSV version with revenue data
    category_replacement_products.json  # Grouped by category
    sku_comparison.csv               # Old vs new SKU comparison
    cross_purchase_matrix.csv        # Customer cross-purchase patterns
    customer_category_map.json       # Customer -> primary category mapping
    replacement_push_report.csv      # Profile property push results
    unmatched_discontinued_products.csv  # Products with no clear replacement
    no_replacement.csv               # Products needing manual mapping
    upsell_recommendations.csv       # Upsell opportunity data
    profile_properties_report.csv    # Full profile properties audit

  campaigns/
    campaign1_dynamic_replacement.html   # Data-driven template using ns_p1_* properties
    campaign1_pasture_replacement.html   # Pasture-specific variant
    campaign1_lawn_replacement.html      # Lawn-specific variant
    campaign1_clover_replacement.html    # Clover-specific variant
    campaign1_wildflower_replacement.html # Wildflower-specific variant
    campaign1_replacement_guide.html     # General replacement guide
    campaign2_spring_is_here.html        # Email 2 variant
    campaign3_new_lineup.html            # Email 3 variant

  scripts/
    push_replacement_properties.py       # Pushes ns_p1_* properties to Klaviyo profiles
    push_profile_properties.py           # General profile property push utility

  analyze_skus.py                        # SKU comparison analysis
  build_cross_purchase.py                # Cross-purchase matrix builder
  build_final_replacement_map.py         # Final replacement map generator
  fetch_orders.py                        # WooCommerce order fetcher
  pull_wc_data.py                        # WooCommerce product data puller
```

---

## 9. Brand Quick Reference

Always invoke the `natures-seed-brand` skill before writing any customer-facing content.

| Element | Value |
|---------|-------|
| Primary Green | `#2d6a4f` |
| CTA Orange | `#C96A2E` |
| Dark Green | `#1b4332` |
| Light Green BG | `#f0f7f3` |
| Warm Accent BG | `#fef9f4` |
| Heading Font | Noto Serif Display (600, 700) |
| Body Font | Inter (400, 500, 600) |
| Email Width | 600px max, responsive at 620px breakpoint |
| CTA Style | Orange button, 16px 40px padding, 6px border-radius |
| Trust Bar | 4.8/5 Rating, 25,000+ Customers, 100% Non-GMO, USDA-Tested |

---

## 10. API Notes for Agents

- **Always pass `model: "claude"` in Klaviyo MCP tool calls**
- **Use `VLbLXB` as `conversionMetricId`** in Klaviyo reporting API calls (it's the WooCommerce "Placed Order" metric)
- **Klaviyo API cannot create flows** — only campaigns. Flows must be built in the Klaviyo UI.
- **Klaviyo API cannot assign templates to flow messages** — only to campaign messages via `klaviyo_assign_template_to_campaign_message`
- **WooCommerce API rate limit:** 0.3s between bulk operations
- **Credentials** are in `.env` in the `ClaudeDataAgent -` root directory
