# Conversion Agent B — WooCommerce Store Analysis

**Date:** March 15, 2026
**Data Source:** WooCommerce REST API v3 + Store API v1
**Period Analyzed:** February 13 – March 15, 2026 (30 days)

---

## 1. Executive Summary

Nature's Seed generated **$315,246 in revenue** from **2,044 orders** over 30 days (processing + completed), with an **AOV of $154.23**. The store is in peak spring buying season with daily volumes averaging 96–123 orders/day (Mar 1–14). Key conversion leaks include a **2.3% payment failure rate** ($7,000 lost), a **74.6% single-item order rate** (cross-sell opportunity), **virtually zero product reviews**, and **155,397 on-hold legacy orders** polluting the database. The refund rate is healthy at 0.54%.

---

## 2. Order & Revenue Metrics (30 Days)

| Metric | Value |
|--------|-------|
| Total Revenue (processing + completed) | **$315,246.44** |
| Total Orders | **2,044** |
| Processing | 637 (31.2%) |
| Completed | 1,407 (68.8%) |
| Average Order Value (AOV) | **$154.23** |
| Shipping Revenue | $9,774.00 |
| Tax Collected | $12,637.31 |
| Discounts Given | $6,727.09 |
| Avg Daily Orders (Mar 1-14) | **99 orders/day** |
| Peak Day | Mar 8: 123 orders |

### Order Value Distribution

| Bracket | Orders | % of Total |
|---------|--------|-----------|
| $0–25 | 176 | 8.6% |
| $25–50 | 440 | 21.5% |
| $50–100 | 547 | 26.8% |
| $100–200 | 447 | 21.9% |
| $200–500 | 355 | 17.4% |
| $500+ | 79 | 3.9% |

**Insight:** 56.9% of orders are under $100. The median order sits in the $50–100 range. There is significant room to push AOV higher, especially for the 440 orders in the $25–50 bracket (potential to double these with bundles or upsells).

---

## 3. Refund & Loss Analysis

### Refunds
| Metric | Value | Benchmark |
|--------|-------|-----------|
| Refunded Orders (30 days) | **11** | — |
| Refund Amount | **$2,389.74** | — |
| Refund Rate (by order count) | **0.54%** | < 3% is healthy |
| Refund Rate (by revenue) | **0.76%** | < 2% is healthy |

**Verdict: HEALTHY.** Refund rate is well below industry average of 2–3%.

Largest refunds:
- $718.72 — Perennial Ryegrass (50 lb, qty 2)
- $629.97 — Transitional Zone Goat Pasture (qty 3)
- $319.96 — Goat Pasture & Forage Mix (qty 4)

### Failed Orders (Payment Failures)
| Metric | Value |
|--------|-------|
| Failed Orders | **48** |
| Lost Revenue | **$6,999.75** |
| Avg Failed Order Value | **$145.83** |
| Failure Rate | **2.3% of all orders** |

**Top products in failed orders:** Clover Lawn Alternative Mix (3x), Chicken Forage Seed Mix (2x), Sundancer Buffalograss (2x), Rice Hulls (2x)

**CONVERSION LEAK:** 48 customers wanted to buy but couldn't complete payment. At $145.83 AOV, recovering even half = **$3,500/month**.

### Cancelled Orders
| Metric | Value |
|--------|-------|
| Cancelled | **5** |
| Lost Revenue | **$57.36** |

Negligible — not a concern.

---

## 4. Product Catalog Analysis

| Metric | Value |
|--------|-------|
| Published Products | **112** |
| Draft Products | **540** |
| Variable Products | 101 (90%) |
| Simple Products | 11 (10%) |
| Price Range | $7.99 – $382.35 |
| Median Price | $39.99 |
| Average Price | $75.61 |

### Stock Issues

**Out of Stock (3 products):**
- Crimson Clover Cover Crop Seed (id: 184631)
- Red Clover Seed (id: 184488)
- Alsike Clover Seed (id: 184480)

**CONVERSION LEAK:** All 3 out-of-stock items are **clover seeds** — a popular category (6 products, multiple in the top sellers). Clover Lawn Alternative is the #9 product by revenue ($8,503). Customers searching for clover are hitting dead ends on 3 of 6 SKUs.

**Low Stock (Critical):**
- Hardy Grass Seed Mix for High Traffic Lawns: **1 unit left**
- Sandhills Prairie Mix: **0 left** (but shows in-stock)
- Miniature Lupine Seed: **1 unit left**
- White Clover Seed: **1 unit left** — this is the **#19 product by revenue** ($5,069)

### Missing Product Descriptions
**39 products (35%) have no description.** This is a significant SEO and conversion issue. Products without descriptions have lower Google rankings and give customers less confidence to purchase.

### Product Reviews — CRITICAL GAP
| Metric | Value |
|--------|-------|
| Products with reviews enabled | 66 of 112 (59%) |
| Total reviews across entire store | **1** |
| Products with any review | **1** (Sonoran Desert Wildflower Mix: 3.0 avg) |

**MAJOR CONVERSION LEAK:** The store has essentially **zero social proof** at the product level. Industry data shows that products with reviews convert 270% better than those without. With 28,619 paying customers in the database, there is a massive untapped review generation opportunity.

---

## 5. Top Products by Revenue (30 Days)

| Rank | Product | Qty Sold | Revenue |
|------|---------|----------|---------|
| 1 | Transitional Zone Goat Pasture & Forage Mix (10 lb) | 154 | $14,628 |
| 2 | White Dutch Clover Seed (10 lb) | 196 | $13,421 |
| 3 | Chicken Forage Seed Mix (50 lb) | 328 | $13,402 |
| 4 | Warm Season Cattle Pasture Seed Mix (10 lb) | 96 | $12,242 |
| 5 | Transitional Zone Horse Pasture Mix (50 lb) | 84 | $12,051 |
| 6 | Cool Season Cattle Pasture Seed Mix (50 lb) | 102 | $11,957 |
| 7 | Triblade Elite Tall Fescue (5 lb) | 121 | $11,001 |
| 8 | Warm Season Horse Pasture Mix (50 lb) | 100 | $10,990 |
| 9 | Clover Lawn Alternative Mix (10 lb) | 188 | $8,503 |
| 10 | Sundancer Buffalograss Lawn Seed (6 lb) | 30 | $7,329 |

**Key Observations:**
- Pasture mixes dominate revenue (4 of top 8)
- Animal-specific products (goat, chicken, horse, cattle) are the growth engine
- Chicken Forage is the volume leader (328 units) — highly promotable
- Clover products are strong (#2 and #9) despite stock issues

---

## 6. Customer Behavior

| Metric | Value |
|--------|-------|
| Total Paying Customers (all-time) | **28,619** |
| Non-paying Accounts | 38,897 |
| Unique Customers (30 days) | **1,959** |
| Repeat Buyers (2+ orders in 30 days) | **65 (3.3%)** |
| Repeat Customer Revenue | $22,280 (7.1%) |
| New Customer Revenue | $292,966 (92.9%) |

**CONVERSION LEAK:** 96.7% of customers buy once and don't return within 30 days. The repeat rate is low even for seasonal products. Post-purchase email flows, loyalty programs, and cross-sell campaigns could significantly improve this.

### Items Per Order
| Metric | Value |
|--------|-------|
| Avg Items Per Order | **1.4** |
| Single-Item Orders | **1,524 (74.6%)** |
| Multi-Item Orders | 520 (25.4%) |

**CONVERSION LEAK:** Nearly 3 out of 4 customers buy just one product. For a store with 112 products across complementary categories (seed + fertilizer + planting aids), this signals weak cross-selling. "Frequently Bought Together" bundles and cart upsells could materially increase AOV.

---

## 7. Payment & Checkout

| Payment Method | Orders | % |
|----------------|--------|---|
| Credit/Debit Card (Stripe) | 1,796 | 87.9% |
| Apple Pay | 177 | 8.7% |
| Google Pay | 67 | 3.3% |
| Unknown | 4 | 0.2% |

**Observation:** Only Stripe is enabled. No PayPal, Affirm/Klarna (BNPL), or Amazon Pay. For orders $200–500+ (21.3% of volume), BNPL options could increase conversion significantly.

**Checkout:** Guest checkout is supported (good). Shopper Approved badge present. Multi-step checkout flow.

---

## 8. Shipping Analysis

| Metric | Value |
|--------|-------|
| Free Shipping Orders | **1,762 (86.2%)** |
| Paid Shipping Orders | 282 (13.8%) |
| Avg Paid Shipping Cost | **$34.66** |
| Free Shipping Threshold | $150 |
| Orders $100–149 (near threshold) | **233 (11.4%)** |

**CONVERSION LEAK:** 233 orders (11.4%) landed between $100–149, just below the $150 free shipping threshold. These customers paid for shipping when a small upsell could have pushed them to free shipping. A progress bar ("You're $XX away from free shipping!") could capture an estimated **$23–35 additional revenue per order** from this segment.

**Note:** The homepage advertises "Free Shipping On orders over $150" but the actual WooCommerce config shows free shipping is **disabled** and flat rate is the only active method. This needs verification — there may be a disconnect between what's advertised and what's configured.

---

## 9. Coupon Usage

| Metric | Value |
|--------|-------|
| Active Coupons | 100+ |
| Orders Using Coupons | **205 (10.0%)** |
| Total Discount Given | $6,727.09 |
| Avg Discount per Coupon Order | $32.81 |

### Top Coupons (30 Days)
| Code | Type | Uses | Discount |
|------|------|------|----------|
| spring10 | 10% off | 71 | Percentage |
| save15 | 15% off | 45 | Percentage |
| welcome10 | 10% off | 26 | Percentage |
| lucky15 | 15% off | 17 | Percentage |
| springpasture | 10% off | 12 | Percentage |

### Coupon Impact on AOV
| Segment | AOV |
|---------|-----|
| With Coupon | **$192.17** |
| Without Coupon | **$150.00** |

**Counter-intuitive finding:** Coupon users actually spend **$42 more** per order than non-coupon users. This suggests coupons are attracting customers who buy larger quantities (likely pasture/bulk buyers) rather than bargain hunters. The coupon strategy is working well — it's not eroding margins on small orders.

---

## 10. Database Health Issue

**155,397 on-hold orders** dominate the database. The most recent ones are from April 2025 (nearly a year old). These appear to be legacy/abandoned orders that were never cleaned up. This massive number:
- Slows WooCommerce admin performance
- Skews reporting (the sales report API returned $0 for 30 days because it may be filtering by status)
- Creates confusion in order management

**Recommendation:** Bulk-delete or archive on-hold orders older than 90 days.

---

## 11. Geographic Distribution (Top States)

| State | Orders | % |
|-------|--------|---|
| California | 246 | 12.0% |
| Texas | 145 | 7.1% |
| Colorado | 107 | 5.2% |
| Washington | 103 | 5.0% |
| Virginia | 86 | 4.2% |
| North Carolina | 83 | 4.1% |
| Missouri | 69 | 3.4% |
| Utah | 67 | 3.3% |
| Georgia | 67 | 3.3% |
| Tennessee | 65 | 3.2% |

California and Texas drive 19.1% of orders — strong alignment with the California Collection and Texas Seeds categories.

---

## 12. Prioritized Conversion Recommendations

### Priority 1 — HIGH IMPACT, LOW EFFORT

**1. Implement Product Reviews System** (Est. Impact: +8-15% conversion rate)
- Currently: 1 review across 112 products = zero social proof
- Action: Deploy Klaviyo post-purchase review request flow
- 28,619 paying customers = massive untapped review pool
- Target: 500+ reviews within 60 days via automated email asks
- Cost: $0 (use existing Klaviyo)

**2. Fix Payment Failures** (Est. Impact: +$3,500/mo revenue recovery)
- 48 failed payments = $6,999 lost in 30 days
- Action: Implement Stripe failed payment retry + abandoned checkout recovery email
- Check if 3D Secure is causing friction for legitimate cards
- Add PayPal as alternative payment (captures customers with card issues)

**3. Restock Clover Seeds** (Est. Impact: +$2,000–4,000/mo)
- 3 of 6 clover products are OOS (Crimson, Red, Alsike)
- White Clover at 1 unit remaining
- Clover is a top category driving $13,421 (White Dutch) + $8,503 (Clover Lawn Alt) + $5,069 (White Clover)
- Action: Emergency restock + back-in-stock notification to subscribers

### Priority 2 — HIGH IMPACT, MEDIUM EFFORT

**4. Cross-Sell/Bundle Strategy** (Est. Impact: +$15-25 AOV increase)
- 74.6% of orders are single-item
- Action: Add "Frequently Bought Together" (seed + fertilizer + planting aids)
- Create curated bundles: "Pasture Starter Kit" (seed + fertilizer + seeder)
- Add cart upsell: "Add Organic Seed Starter Fertilizer for $119.99"
- Complementary pairings exist: Chicken Forage + Cover Crop, Lawn Seed + Fertilizer

**5. Free Shipping Progress Bar** (Est. Impact: +$5,000–8,000/mo)
- 233 orders (11.4%) fall between $100–149
- Action: Add "You're $XX away from free shipping!" banner in cart
- Show threshold progress on all product pages
- Estimated additional spend: ~$30/order x 233 orders = $6,990/mo

**6. Add BNPL Payment Option** (Est. Impact: +5-10% on orders $200+)
- 434 orders (21.3%) are $200+, with 79 orders $500+
- Affirm/Klarna/Afterpay reduces friction for high-value pasture orders
- Pasture mixes ($100–$900 range) are ideal BNPL candidates

### Priority 3 — MEDIUM IMPACT, HIGHER EFFORT

**7. Product Description Content** (Est. Impact: +SEO traffic, +conversion)
- 39 products (35%) have no description
- Action: Write descriptions for all 39 — prioritize top sellers first
- Include: species list, coverage area, regional suitability, planting instructions

**8. Post-Purchase Retention Flow** (Est. Impact: +2-5% repeat rate)
- Current repeat rate: 3.3% (30-day window)
- Action: Klaviyo post-purchase sequence: planting tips (day 3), care guide (day 14), reorder reminder (day 45), seasonal cross-sell (seasonal)
- Pasture customers especially should get "time to overseed" reminders in fall

**9. Enable Reviews on All Products** (Quick Fix)
- Only 66 of 112 products (59%) have reviews enabled
- Action: Bulk-enable reviews on all 112 products via WC API batch update

**10. Database Cleanup — Archive On-Hold Orders**
- 155,397 on-hold orders are degrading performance
- Action: Bulk-cancel or delete orders in on-hold status older than 90 days
- Will improve admin speed and fix sales reporting

---

## 13. Revenue Impact Summary

| Recommendation | Est. Monthly Revenue Impact |
|----------------|----------------------------|
| Product reviews system | +$2,500–4,700 (via higher CVR) |
| Payment failure recovery | +$3,500 |
| Restock clover seeds | +$2,000–4,000 |
| Cross-sell/bundles (AOV lift) | +$5,000–8,300 |
| Free shipping progress bar | +$5,000–8,000 |
| BNPL payment option | +$3,000–6,000 |
| Product descriptions | +$1,000–2,000 (SEO) |
| Post-purchase retention | +$2,000–5,000 |
| **Total Estimated Opportunity** | **$24,000–41,500/mo** |

---

## 14. Data Caveats

1. **Sales report API returned $0** — The WC reports/sales endpoint showed zero revenue despite 2,044 orders existing. This is likely caused by the 155K on-hold orders or a reporting bug. Revenue figures in this report are calculated directly from order line items.
2. **On-hold orders (155K)** appear to be legacy data from a previous store configuration or migration. The most recent on-hold orders are from April 2025.
3. **Free shipping configuration** — The WooCommerce shipping zone shows free shipping as disabled, but the homepage advertises it. This may be handled by a plugin (Flexible Shipping is installed) rather than native WC shipping.
4. **Customer data window** — Repeat customer analysis covers only 30 days. Seasonal businesses will naturally have lower 30-day repeat rates; a 90-day or YoY analysis would give a more accurate picture.
