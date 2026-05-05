# May 2026 Email Promotional Campaign Design

**Date:** 2026-05-05  
**Goal:** Generate +$25,239 in email-attributed revenue in May 2026  
**Approach:** Option B — one new standalone campaign + one scheduled upgrade + one late-month close

---

## Context

### Revenue Gap

- May 2026 budget (total net revenue): $215,931
- Projected email revenue at current trajectory (~32% of projected WC): ~$57,500
- Required email revenue: ~$82,756
- Gap: $25,239 (44% lift over baseline)

### YTD Performance

- Jan–Feb: 55–69% of budget
- Mar–Apr: 100–110% of budget (recovered)
- Average attainment Jan–Apr: 84%

### Existing May Schedule (unchanged)

The following campaigns remain as planned and are not modified:

- May 6: C4 Spring Activation (Lawn, Pasture, Wildflower, Specialty) — pure brand, no offer
- May 8: Drought Campaign Email 2 (Lawn, Pasture, Wildflower buyers) — educational
- May 14: May Spring Window — At Risk/Lapsed Winback
- May 22: Drought Campaign Email 3 — educational, Memorial Day angle
- May 25: Memorial Day Sale — Start
- May 26: Memorial Day — At Risk/Lapsed Winback
- May 27: Memorial Day Sale — Last Chance

---

## Campaigns

### Campaign 1 — Mother's Day Wildflower & Lawn Gift

| Field | Value |
|---|---|
| Name | `Mother's Day — Wildflower & Lawn Gift` |
| Send date | May 9, 10:00 AM MT |
| Segments | E60D (RbH7na) — wildflower buyers (send 1), lawn buyers (send 2). Starred segments only. Filter by category purchase history. |
| Offer | 10% off, code `MOM10`, expires May 11 |
| Angle | Gifting frame: "give her something that grows." Wildflower version leads with native meadow gifting. Lawn version leads with gifting a better yard. |
| Template | Hero image (wildflower field, 16:9 via assets.py `email_header`) → headline → 2-line body → CTA button (#C96A2E, "Shop Mother's Day Gifts") → 3-card product grid → discount callout footer |
| Revenue target | $12,000–$15,000 attributed (~18K total contacts, 1.5–2.0 RPE) |

**Notes:**
- Two separate Klaviyo sends, same template, category-specific product grid and subject line
- Subject line direction: wildflower — "Give her a meadow this Mother's Day"; lawn — "The gift of a better yard (10% off this weekend)"
- Suppress anyone who purchased in the last 14 days

---

### Campaign 2 — C5 Spring Activation Upgrade (Existing → Promotional)

| Field | Value |
|---|---|
| Existing campaigns | C5 Spring Activation — Lawn, Pasture, Wildflower, Specialty (all four) |
| Send date | May 20, 17:00 MT (already scheduled) |
| Segments | Existing per-campaign segments (already assigned, do not change) |
| Offer | 12% off, code `SPRING12`, expires May 25 |
| Angle | "The planting window is closing." Practical urgency, not hype. Category-specific: lawn = before summer dormancy, pasture = summer establishment window, wildflower = plant now for fall bloom, specialty = limited install window. |
| Template | Hero image (category-matched seasonal, via assets.py) → urgency headline → 2-line practical body → CTA (#C96A2E, "Plant Before Summer") → 3-card product grid → expiry callout |
| Revenue target | $13,000–$14,000 attributed across all four sends (~35K total contacts, ~0.90 RPE blended) |

**Notes:**
- Upgrade existing campaigns in place — update template and subject lines, do not create new campaigns
- Expiry May 25 is intentional: SPRING12 expires the same day Memorial Day Sale starts, preventing overlap
- Subject line direction: "You have about 3 weeks. Here's 12% off."

---

### Campaign 3 — Summer Arrives / Final Planting Window

| Field | Value |
|---|---|
| Name | `Summer Arrives — Final Planting Window` |
| Send date | May 28, 10:00 AM MT |
| Segments | Champions Active (VtKptn) + Champions (RAQTca) + Active This Season (RbGRqF) + Warm (WdpJti) — exclude anyone with a Placed Order event in May 2026 |
| Offer | No discount code. Urgency-only close. |
| Angle | "Summer heat arrives in most zones by mid-June. This is the final planting window." Content-first, feels like advice not a push. |
| Template | Hero image (warm summer field tone, via assets.py) → "Where are you in the planting window?" headline → 2-sentence zone-agnostic practical body → CTA (#C96A2E, "See What to Plant Now") → 3-card product grid (best sellers for late planting) → no discount callout |
| Revenue target | $6,000–$9,000 attributed (Champions + Active + Warm, late-window buyers) |

**Notes:**
- No coupon: SPRING12 expired May 25, Memorial Day just closed. Adding another code trains the list to wait for deals.
- Product grid should feature fast-establishing varieties appropriate for late planting
- Send after Memorial Day Last Chance (May 27) — does not compete with any active offer

---

## Revenue Summary

| Campaign | Send Date | Est. Incremental Revenue |
|---|---|---|
| Mother's Day — Wildflower & Lawn Gift | May 9 | $12,000–$15,000 |
| C5 Spring Activation Upgrade | May 20 | $13,000–$14,000 |
| Summer Arrives — Final Planting Window | May 28 | $6,000–$9,000 |
| **Total** | | **$31,000–$38,000** |

Target: $25,239. Buffer: $5,761–$12,761.

---

## Implementation Notes

- Invoke `natures-seed-brand` skill before writing any copy
- All images via `~/.party/lib/assets.py` — use `get_asset(suggested_use="email_header", aspect_ratio="16:9")`
- CTA button color: `#C96A2E` (orange). Never green.
- Max discount hard cap: 15%. Both codes (MOM10 at 10%, SPRING12 at 12%) are within cap.
- Template assignment via MCP tool `klaviyo_assign_template_to_campaign_message` only
- Campaign 2 is an upgrade of existing scheduled campaigns — update via Klaviyo MCP, do not recreate
- Campaign 1 and 3 are net-new — create via `klaviyo_create_campaign` with revision `2024-07-15`
- API revision: `2024-07-15` (required for campaign creation)
