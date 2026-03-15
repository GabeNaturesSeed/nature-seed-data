# Financial Analysis: Unit Economics & Operational Costs

**Agent**: Financial/Operations Agent A
**Period**: 2026-02-13 to 2026-03-14 (30 days)
**MTD Focus**: March 1-14, 2026 (14 days of precise data)
**Generated**: 2026-03-15 01:57
**Data Source**: Local JSON files (docs/data/reporting.json, walmart.json, budget.json)

---

## 1. P&L Summary

### March MTD (Mar 1-14, 2026) — Precise Data

| Line Item | Amount | % of Revenue |
|-----------|--------|-------------|
| **Revenue** | $187,337.39 | 100.0% |
| COGS | ($60,880.21) | 32.5% |
| **Gross Profit** | $126,457.18 | 67.5% |
| Shipping | ($47,229.17) | 25.2% |
| Ad Spend | ($34,844.06) | 18.6% |
| Platform Fees | ($6,212.07) | 3.3% |
| **Net Profit (CM2)** | $38,171.88 | 20.4% |

**Key Metrics**:
- Total Orders: 1,438
- AOV: $130.28
- Avg Daily Revenue: $13,381.24
- MER: 5.38x

### Estimated 30-Day P&L (2026-02-13 to 2026-03-14)

_(Feb 13-28 prorated from monthly data + Mar 1-14 actual)_

| Line Item | Amount | % of Revenue |
|-----------|--------|-------------|
| **Revenue** | $294,534.22 | 100.0% |
| COGS | ($97,839.80) | 33.2% |
| **Gross Profit** | $196,694.42 | 66.8% |
| Shipping | ($74,254.30) | 25.2% |
| Ad Spend | ($60,937.35) | 20.7% |
| Platform Fees (est.) | ($9,766.70) | 3.3% |
| **Net Profit** | $51,736.07 | 17.6% |

- Estimated 30-Day Orders: ~2,087
- Estimated 30-Day AOV: $141.13
- Estimated 30-Day MER: 4.83x

---

## 2. Margin Health

### Current vs Last Year (March MTD, same day count)

| Metric | March 2026 MTD | March 2025 MTD | YoY Change |
|--------|---------------|---------------|------------|
| Revenue | $187,337.39 | $171,181.31 | +9.4% |
| Orders | 1,438 | 910 | +58.0% |
| AOV | $130.28 | $188.11 | -30.7% |
| Ad Spend | $34,844.06 | $33,049.42 | +5.4% |
| MER | 5.38x | 5.18x | +3.9% |
| Gross Margin % | 67.5% | — | — |

### Monthly Margin Trend (2026 YTD)

| Month | Revenue | Gross Margin % | CM2 | CM2 % | MER |
|-------|---------|---------------|-----|-------|-----|
| 2026-01 | $83,872.87 | 72.5% | $23,492.49 | 28.0% | 5.88x |
| 2026-02 | $187,594.46 | 65.5% | $-11,900.00 | -6.3% | 4.11x |
| 2026-03 | $187,337.39 | 67.5% | $38,171.88 | 20.4% | 5.38x |

**Revenue Trend (Mar 1-14)**: IMPROVING
- First week avg: $12,885.98/day
- Second week avg: $15,717.36/day
- Shift: +22.0%

**ALERT: February 2026 was unprofitable** — CM2 was $-11,900.00 (-6.3%)
- February revenue ($187,594.46) was strong but costs exceeded margins
- March is recovering: CM2 at $38,171.88 (20.4%)

---

## 3. Product Margin & COGS Analysis

### COGS Coverage
- The `cogs_lookup` table contains SKU-level unit costs (276 SKUs per CLAUDE.md)
- COGS as % of revenue (Mar MTD): **32.5%**
- Gross margin: **67.5%**

### COGS Trend by Month

| Month | Revenue | COGS | Gross Margin % |
|-------|---------|------|---------------|
| 2026-01 | $83,872.87 | $23,038.29 | 72.5% |
| 2026-02 | $187,594.46 | $64,679.29 | 65.5% |
| 2026-03 | $187,337.39 | $60,880.21 | 67.5% |

### Observations
- January had the best gross margin at 72.5%, indicating lower-cost products or better pricing
- February dropped to 65.5% gross margin — higher-cost mixes sold more
- March is at 67.5% — partial recovery
- **COGS data gaps**: The `daily_cogs` table tracks `unmatched_units` — units sold without matching SKU costs
- Without live Supabase access, exact unmatched unit counts are unavailable, but the schema shows this is tracked
- **Action needed**: Query `cogs_lookup` for SKUs with `selling_price < unit_cost` to find negative-margin products

---

## 4. Shipping Cost Analysis

- **Total shipping cost (Mar MTD)**: $47,229.17
- **Shipping as % of revenue**: **25.2%**
- **Avg shipping cost per order**: $32.84
- **Avg daily shipping cost**: $3,373.51

### Shipping Cost Assessment
- **CRITICAL**: Shipping at 25.2% of revenue is very high
- Industry benchmark for ecommerce: 8-15% of revenue
- This is eating $47,229.17 out of $187,337.39 in revenue
- **Excess shipping cost** (above 15% benchmark): ~$19,128.56 in 14 days = ~$497,342.60 annualized

### Shipping's Impact on Profitability
- Gross profit before shipping: $126,457.18 (67.5%)
- After shipping: $79,228.01 (42.3%)
- Shipping consumes **37.3%** of gross profit

---

## 5. Ad Spend Efficiency

- **Total ad spend (Mar MTD)**: $34,844.06
- **Ad spend as % of revenue**: 18.6%
- **MER**: 5.38x (revenue per $1 ad spend)
- **ROAS**: 5.38x

### MER Trend

| Month | Ad Spend | Revenue | MER |
|-------|---------|---------|-----|
| 2026-01 | $14,271.02 | $83,872.87 | 5.88x |
| 2026-02 | $45,663.26 | $187,594.46 | 4.11x |
| 2026-03 | $34,844.06 | $187,337.39 | 5.38x |

### Assessment
- MER of 5.38x is **healthy** (target: 5x+)
- February MER dropped to 4.11x (highest spend relative to revenue)
- March recovered to 5.38x

### YoY Ad Efficiency
- March 2025 MTD ad spend: $33,049.42
- March 2025 MTD MER: 5.18x
- YoY MER change: +3.9%

---

## 6. Channel Comparison (WC vs Walmart vs Amazon)

_Note: Channel-level COGS and shipping are estimated proportionally. Ad spend allocation is estimated._

| Metric | WooCommerce | Walmart | Amazon |
|--------|-------|-------|-------|
| Revenue (MTD) | $180,196.17 | $4,239.17 | $2,902.05 |
| Orders | 1,383 | 48 | 22 |
| AOV | $130.29 | $99.20 | $131.91 |
| COGS (est.) | $58,559.48 | $1,377.63 | $943.10 |
| Shipping (est.) | $45,428.81 | $1,068.73 | $731.63 |
| Ad Spend (est.) | $33,101.86 | $696.88 | $1,045.32 |
| Platform Fees | $0.00 | $140.57 | $96.23 |
| Gross Profit | $121,636.69 | $2,861.54 | $1,958.95 |
| Net Profit | $43,106.02 | $955.36 | $85.77 |
| Gross Margin % | 67.5% | 67.5% | 67.5% |
| Net Margin % | 23.9% | 22.5% | 3.0% |

### Revenue Mix
- **WooCommerce**: $180,196.17 (96.2% of total)
- **Walmart**: $4,239.17 (2.3% of total)
- **Amazon**: $2,902.05 (1.5% of total)

### Walmart Profitability Deep Dive
- Walmart revenue: $4,239.17 (48 orders)
- Walmart AOV: $99.20
- Revenue share: 2.3%
- Walmart is marginally profitable at 22.5% net margin

---

## 7. YoY Financial Health Comparison

### March MTD: 2026 vs 2025

| Metric | 2026 | 2025 | YoY Change |
|--------|------|------|------------|
| Revenue | $187,337.39 | $171,181.31 | +9.4% |
| Orders | 1,438 | 910 | +58.0% |
| AOV | $130.28 | $188.11 | -30.7% |
| Ad Spend | $34,844.06 | $33,049.42 | +5.4% |
| MER | 5.38x | 5.18x | +3.9% |

### YTD Comparison

| Metric | 2026 YTD | 2025 YTD (same period) | YoY | Budget | % to Budget |
|--------|---------|----------------------|-----|--------|------------|
| Revenue | $458,804.72 | $562,143.86 | -18.4% | $825,509.00 | 55.6% |
| Gross Margin % | 67.6% | — | — | — | — |
| CM2 | $49,764.37 | — | — | — | — |
| CM2 % | 10.8% | — | — | — | — |

**YTD revenue is -18.4% vs last year** — tracking at 81.6% of LY pace
**YTD revenue is at 55.6% of budget** — behind target

---

## 8. Top 5 Financial Optimization Opportunities

### 1. [CRITICAL] Reduce Shipping Costs
- Shipping is 25.2% of revenue ($47,229.17 MTD)
- At $32.84/order, this is the single largest margin drain after COGS
- Reducing to 12% of revenue would save ~$645,233.53/year
- **Actions**: Negotiate Shippo rates, increase free-shipping threshold, optimize packaging, consider regional carriers
- **Estimated annual impact**: $184,699.79 (15% shipping cost reduction)

### 2. [HIGH] Fix February-Type Cost Blowouts
- February 2026 had **negative CM2** ($-11,900.00, -6.3%)
- Revenue was $187,594.46 but costs consumed all margin
- This pattern suggests seasonal spend ramp without proportional revenue
- **Actions**: Set hard budget caps, pause underperforming campaigns earlier, watch shipping costs during high-volume periods
- **Estimated annual impact**: Avoiding one bad month = $23,800.00 saved

### 3. [HIGH] Improve COGS Tracking & Coverage
- The `daily_cogs` table tracks `unmatched_units` (orders with no SKU cost data)
- Any unmatched units mean reported margins are OVERSTATED
- With 276 SKUs in `cogs_lookup`, coverage may not be 100%
- **Actions**: Audit `cogs_lookup` for missing SKUs, reconcile Fishbowl costs, add selling_price for margin analysis
- **Estimated annual impact**: 5% better COGS accuracy could reveal $7,429.89 in hidden costs

### 4. [MEDIUM] Optimize Channel Mix (Reduce Marketplace Losses)
- WooCommerce generates 96.2% of revenue with best margins
- Walmart ($4,239.17) and Amazon ($2,902.05) carry platform fees + higher shipping
- **Actions**: Raise marketplace prices by 10-15% to cover fees, focus ad spend on WC, audit Walmart SKU profitability
- **Estimated annual impact**: 10% price increase on marketplace = ~$18,567.17/year

### 5. [MEDIUM] Maintain MER Above 5x
- Current MER: 5.38x (healthy)
- February dropped to 4.11x (dangerous)
- **Actions**: Set 4.5x MER floor as campaign pause trigger, reallocate budget to highest-ROAS campaigns
- **Estimated annual impact**: Maintaining 5x vs 4x MER on $94,778.34 annual ad spend = $23,694.58 additional revenue captured


---

## 9. Break-Even Analysis & Risk Assessment

- **Average daily fixed costs** (ads + shipping + platform fees): $6,306.09
- **COGS as % of revenue**: 32.5%
- **Contribution margin ratio**: 67.5%
- **Break-even daily revenue**: **$9,342.36**
- **Actual avg daily revenue (Mar MTD)**: $13,381.24
- **Buffer above break-even**: $4,038.88 (43.2%)
- **Days below break-even (Mar 1-14)**: 0 of 13

**RISK: LOW** — 43% buffer above break-even. Strong daily performance.

### Monthly Break-Even Target
- Monthly break-even revenue: ~$280,270.79
- March budget target: $433,213.00
- Current March run rate (14d annualized): $401,437.26
- **Budget shortfall risk**: ~$31,775.74 below March target at current pace

### Daily Revenue (Mar 1-14)

| Date | Revenue | vs Break-Even |
|------|---------|--------------|
| 2026-03-01 | $13,153.02 | ABOVE ($3,811) |
| 2026-03-02 | $11,680.58 | ABOVE ($2,338) |
| 2026-03-03 | $11,366.97 | ABOVE ($2,025) |
| 2026-03-04 | $13,885.16 | ABOVE ($4,543) |
| 2026-03-05 | $15,275.25 | ABOVE ($5,933) |
| 2026-03-06 | $11,954.92 | ABOVE ($2,613) |
| 2026-03-07 | $13,567.65 | ABOVE ($4,225) |
| 2026-03-08 | $17,037.98 | ABOVE ($7,696) |
| 2026-03-09 | $19,048.56 | ABOVE ($9,706) |
| 2026-03-10 | $15,410.14 | ABOVE ($6,068) |
| 2026-03-11 | $17,160.16 | ABOVE ($7,818) |
| 2026-03-12 | $12,619.30 | ABOVE ($3,277) |
| 2026-03-13 | $15,177.70 | ABOVE ($5,835) |

---

## 10. Budget vs Actual (March 2026)

| Metric | Budget (Full Month) | Actual (14d) | Run Rate (30d) | % of Budget |
|--------|-------------------|-------------|---------------|------------|
| Revenue | $433,213.00 | $187,337.39 | $401,437.26 | 93% |
| COGS | $111,656.00 | $60,880.21 | $130,457.59 | 117% |
| Ad Spend | $72,602.00 | $34,844.06 | $74,665.84 | 103% |
| Net Income | $167,089.00 | $38,171.88 | $81,796.89 | 49% |

---

## Appendix: Raw Data Summary

### Source: `docs/data/reporting.json` (as of 2026-03-14)

```
MTD Revenue:    $187,337.39
MTD Orders:     1,438
MTD COGS:       $60,880.21
MTD Shipping:   $47,229.17
MTD Ad Spend:   $34,844.06
MTD Plat Fees:  $6,212.07
MTD Net (CM2):  $38,171.88
MTD GM%:        67.5%
MTD CM2%:       20.4%
MTD MER:        5.38x
MTD AOV:        $130.28

YTD Revenue:    $458,804.72
YTD CM2:        $49,764.37
YTD CM2%:       10.8%
YTD GM%:        67.6%
```

### Walmart Top Products (MTD)

| Product | SKU | Revenue | Orders |
|---------|-----|---------|--------|
| Cool Season Cattle Pasture Seed Mix - 50 lb - Covers 100,000 | PB-COW-NTR-50-LB-KIT | $959.94 | 6 |
| Nature's Seed Cool Season Horse Pasture Mix - 20 Lb | PB-HRSE-N-20-LB-KIT | $749.85 | 15 |
| Nature's Seed Rice Hulls - 45 Lb | S-RICE-45-LB | $629.94 | 6 |
| Nature's Seed Pig Pasture & Forage Mix - 50 Lb | PB-PIG-50-LB-KIT | $209.99 | 1 |
| Warm Season Goat Pasture & Forage Mix - 50 lb - Covers 100,0 | PB-GOAT-N-50-LB-KIT | $209.99 | 1 |