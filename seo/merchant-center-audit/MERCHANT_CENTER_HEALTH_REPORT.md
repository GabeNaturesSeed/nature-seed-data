# Google Merchant Center — Account Health Report

**Account**: Nature's Seed (ID: 138935850)
**Website**: naturesseed.com
**Audit Date**: March 9, 2026
**Total Products**: 306

---

## Overall Health: B+ (Good, with fixable issues)

| Metric | Status | Detail |
|--------|--------|--------|
| Account Status | ✅ No issues | Zero account-level warnings |
| Product Approval | ✅ 100% | All 306 products approved for US Shopping |
| Disapprovals | ✅ Zero | No products disapproved |
| Products with Issues | ⚠️ 120 products | All "unaffected" severity — informational, not blocking |
| GTIN Coverage | ⚠️ 93.5% | 286/306 have GTINs, 20 missing |
| COGS Coverage | ⚠️ 67% | 205/306 have costOfGoodsSold |
| Brand Coverage | ⚠️ 98.7% | 302/306, 4 missing |
| Description Coverage | ⚠️ 99.3% | 304/306, 2 missing |
| Google Category | ⚠️ 95.8% | 293/306, 13 missing |
| Custom Label Strategy | ⚠️ Partial | CL0-CL3 used, CL4 completely empty |

---

## Issue Breakdown

### 1. Invalid Price Format — 264 issues (88 products)

**Severity**: Unaffected (informational only)
**What it means**: Google is flagging the price format but still accepting it. The current format works but doesn't match Google's strict ISO 4217 spec.
**Impact**: None currently — all products are approved. But this could become enforced.
**Fix**: Ensure price values are submitted as `XX.XX USD` format in the feed. This is likely a WooCommerce-to-GMC sync formatting issue.
**Priority**: Low (monitoring)

### 2. Image Too Small for High Resolution — 39 products

**Severity**: Unaffected
**What it means**: Images are under 500x500px, which means they can't serve on TV/Connected TV surfaces (YouTube Shopping, etc.)
**Impact**: Missing out on YouTube Shopping and CTV ad placements.

**Affected products include**:
- Perennial Ryegrass variants
- Fescue Lawn variants
- Drought-Tolerant Bluegrass
- Cereal Rye Cover Crop
- Buckwheat variants
- Timothy variants
- Several wildflower mixes
- Bahia Grass
- Organic Fertilizers
- M-Binder Tackifier

**Fix**: Replace product images with 1000x1000px+ photos (Google recommends 1500x1500 for best results).
**Priority**: Medium — especially for best sellers like Fescue and Bluegrass.

### 3. Paused Products — Expired (4 products) + Near Expiration (2 products)

**Expired (paused 2+ weeks — will take longer to unpause)**:
- Thin Pasture Fix Kit
- Overseed & Repair Lawn Kit
- Soil Builder Cover Crop Kit
- Weed Smother Cover Crop Kit

**Near Expiration (paused, about to expire)**:
- First-Year Color + Perennial Foundation Wildflower Kit
- Pollinator Corridor Kit

**Impact**: These 6 kit products are effectively invisible in Shopping. If they're intentionally paused, fine. If they should be active, they need to be unpaused ASAP — the longer they stay paused, the longer the reactivation takes.
**Decision needed**: Are these kits still sold? If yes, unpause immediately.
**Priority**: High (if products should be active)

### 4. Text Value Truncated — 9 issues (1 product group)

**Product**: "Nature's Seed Lawn Bluegrass & Rye Expertly Curated Seed" (all variants)
**Fix**: Shorten the product title to stay under Google's 150-character limit.
**Priority**: Low

### 5. Missing Unit Pricing — 8 issues (4 products)

**Products**:
- Overseed & Repair Lawn Kit
- First-Year Color Wildflower Kit
- Rice Hulls
- White Dutch Clover Soil & Grass Health Boost

**Fix**: Add `unit_pricing_base_measure` (e.g., "5lb") to the feed for these products.
**Priority**: Low (informational)

### 6. Broken Image Link — 3 issues (1 product)

**Product**: Pet & Kid Safe Bluegrass Lawn Seed Bundle
**What's happening**: Google is using the old image because the new URL is broken. The product is still showing, just with an outdated image.
**Fix**: Update the image URL in WooCommerce and re-sync.
**Priority**: Medium

### 7. Price Updated — 12 issues

**Severity**: Unaffected
**What it means**: Google detected a price change between the feed and the landing page. This is normal during price updates — Google just logs it.
**Priority**: None (informational)

---

## Feed Quality Analysis

### Product Data Completeness

| Field | Coverage | Count | Status |
|-------|----------|-------|--------|
| Title | 100% | 306/306 | ✅ |
| Description | 99.3% | 304/306 | ⚠️ 2 missing |
| Brand | 98.7% | 302/306 | ⚠️ 4 missing |
| GTIN | 93.5% | 286/306 | ⚠️ 20 missing |
| MPN | 95.8% | 293/306 | ⚠️ 13 missing |
| Google Category | 95.8% | 293/306 | ⚠️ 13 missing |
| Image | 100% | 306/306 | ✅ |
| Price | 100% | 306/306 | ✅ |
| Link | 100% | 306/306 | ✅ |
| Shipping Weight | 98.7% | 302/306 | ✅ |
| Product Highlights | 95.8% | 293/306 | ✅ |
| Cost of Goods Sold | 67% | 205/306 | ⚠️ 101 missing |
| Sale Price | 1% | 3/306 | ℹ️ Only 3 products on sale |

### Products Missing Key Fields

**Missing GTIN (20 products)** — Mostly kits and bundles that don't have individual GTINs:
- Wildflower kits, Pasture Fix Kit, Cover Crop kits
- Jimmy's Perennial Wildflower Mix (2 variants)
- Fescue/Bluegrass bundles
- Rice Hulls, White Dutch Clover Boost

**Missing Brand (4 products)**:
- Overseed & Repair Lawn Kit (variant)
- First-Year Color Wildflower Kit (variant)
- Rice Hulls
- White Dutch Clover Soil & Grass Health Boost

**Missing Description (2 products)**:
- Rice Hulls
- White Dutch Clover Soil & Grass Health Boost

**Missing Google Category (13 products)** — All defaulting to "(none)":
- All kit products (Wildflower, Pasture, Lawn, Cover Crop)
- Jimmy's Perennial Wildflower Mix
- Rice Hulls
- White Dutch Clover Boost

### Price Distribution

| Range | Count | % |
|-------|-------|---|
| Under $10 | 1 | 0.3% |
| $10 – $25 | 19 | 6.2% |
| $25 – $50 | 73 | 23.9% |
| $50 – $100 | 69 | 22.5% |
| $100 – $200 | 68 | 22.2% |
| Over $200 | 76 | 24.8% |

Healthy distribution — good mix of entry-point and premium products.

### Item Group Structure

| Metric | Value |
|--------|-------|
| Total item groups | 97 |
| Multi-variant groups | 96 |
| Single-variant groups | 2 |
| Products with no group | 14 |
| Largest group | 14 variants |
| Typical group size | 3 variants |

14 products have no item group ID — these are likely standalone products (kits, rice hulls, etc.) that should still have groups for proper variant handling.

---

## Custom Label Strategy

| Label | Purpose | Usage | Status |
|-------|---------|-------|--------|
| CL0 | Product Category | 293/306 | ✅ Good |
| CL1 | Regional Tag | 86/306 | ⚠️ Only CA (65) + TX (21), 220 untagged |
| CL2 | Price Bucket | 293/306 | ✅ Good |
| CL3 | Margin Tier | 293/306 | ✅ Good |
| CL4 | (Unused) | 0/306 | ❌ Wasted |

**CL0 values**: pasture (120), wildflower (69), grass-seed (47), clover (24), specialty (19), planting aid (14)
**CL1 values**: California (65), Texas (21), rest are blank
**CL3 values**: High Margin (120), Average Margin (88), Low Margin (85)

**Opportunity**: CL4 is completely unused — could be used for:
- Seasonal tags (spring-seller, fall-seller)
- Performance tiers (star-product, hidden-gem, low-performer)
- New/featured flags
- Promotion eligibility

---

## Recommendations (Priority Order)

### P0 — Quick Wins (fix this week)

1. **Decide on paused kit products** — 6 products are paused and expiring. Either unpause or remove from feed.
2. **Add brand to 4 products** — Set `brand` = "Nature's Seed" for Rice Hulls, White Dutch Clover Boost, and 2 kit variants.
3. **Add descriptions to 2 products** — Rice Hulls and White Dutch Clover Boost have no description.
4. **Fix broken image** — Pet & Kid Safe Bluegrass Lawn Seed Bundle has a broken image URL.

### P1 — Feed Completeness (next 2 weeks)

5. **Add Google Category to 13 products** — All should be `Home & Garden > Plants > Seeds > Seeds & Seed Tape` (or `Spreaders` for applicator products).
6. **Add COGS to remaining 101 products** — Only 67% have `costOfGoodsSold`. This data feeds Google's automated bidding and Smart Shopping optimization. Significant missed signal.
7. **Add MPN to 13 products** — Missing MPN = missing product identifier for Google matching.

### P2 — Image Quality (next month)

8. **Upgrade 39 product images to 1000x1000px+** — Unlocks YouTube Shopping, CTV placements, and better Shopping ad quality.
9. **Focus on best sellers first** — Fescue, Bluegrass, Ryegrass, and Cereal Rye should get priority image upgrades.

### P3 — Strategic Optimization

10. **Use Custom Label 4** — Tag products by performance tier or seasonal relevance for Shopping campaign segmentation.
11. **Expand Custom Label 1** — Only 86/306 products have regional tags. Consider adding regional tags for products popular in specific states (based on nightly review state data).
12. **Add sale prices strategically** — Only 3/306 products have sale prices. Sale price annotations in Shopping ads get significantly higher CTR.
13. **Shorten truncated title** — Bluegrass & Rye product title is too long.

---

## Account Strengths

- **100% approval rate** — Zero disapprovals is excellent
- **No account-level issues** — Clean standing with Google
- **Strong product highlights** — 96% of products have highlights (unusual for most merchants)
- **Good shipping weight coverage** — 99% have shipping data
- **Well-organized item groups** — 97 groups covering 292 products with proper variant structure
- **Custom labels actively used** — CL0/CL2/CL3 enable sophisticated Shopping campaign segmentation
- **COGS data on 67%** — Better than most, but room to improve

## Key Numbers

| Metric | Value |
|--------|-------|
| Products in feed | 306 |
| Approved for US Shopping | 306 (100%) |
| Disapproved | 0 |
| Item groups (parent products) | 97 |
| Unique product types | 32 |
| Products with issues (informational) | 120 |
| Blocking issues | 0 |

---

*Generated by Nature's Seed Data Orchestrator — March 9, 2026*
