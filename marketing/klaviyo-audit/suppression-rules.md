# Klaviyo Suppression Rules — Applied to All Sends

> Derived from strategy spec §2.4. These rules must be applied to every
> flow's filter logic and every broadcast campaign's exclusion list.

## The five rules (flows + broadcasts)

### 1. Bought in last 48 hours

- **Who:** Any profile with `Placed Order` (metric `VLbLXB`) in last 48h
- **Why:** Don't undercut a fresh purchase with a sale email or a cross-sell email too early
- **Flow filter syntax:** `Placed Order [0 times] in the last 2 days`
- **Campaign exclusion:** Klaviyo audience exclusion set to segment `Y7bP52` (Purchased in Last 48 Hours)

### 2. Currently in active flow (broadcasts only)

- **Who:** Profile currently inside Checkout Abandonment, Cart Abandonment, Post-Purchase, or Welcome Series
- **Why:** Prevents a broadcast from interrupting a carefully-timed automated journey
- **Enforcement:** Each broadcast's exclusion list includes segment `TzYTy7` (NS Campaign — EXCLUDE: In Active Flow)
- **Note:** This does NOT apply flow-to-flow — a person in Welcome can still enter Cart Abandonment if they browse mid-series.

### 3. NOT-E90 (Disengaged)

- **Who:** Segment `VirYfN` / `VrqmRz` — 0 email opens in the last 90 days
- **Why:** Sending to disengaged profiles damages deliverability (spam filters infer poor engagement); per spec they get FLOW-ONLY recovery path until they re-engage
- **Enforcement:** All broadcasts exclude this segment; Sunset flow handles final outreach + suppression

### 4. Unsubscribed from email (≤730 days)

- **Who:** Anyone with `Unsubscribed from Email Marketing` event (`UwnyvV`) in last 2 years
- **Why:** Legal (CAN-SPAM), respectful, deliverability
- **Enforcement:** Klaviyo auto-suppresses; no manual action needed

### 5. Hard bounced ≥2 times in 30 days

- **Who:** Profile with `Bounced Email` (`MTYddd`) ≥2 in last 30d
- **Why:** Bad address → repeat bounces hurt sender reputation
- **Enforcement:** Klaviyo auto-suppresses after 5 bounces; we proactively suppress at 2 to protect domain rep
- **Segment:** `U7H5u5` (bounces) — add to all broadcast exclusion lists

## Application checklist — to run once per live flow

For each flow listed below, open in Klaviyo UI and verify the flow's audience filters include all applicable rules above. This is a MANUAL UI step (Klaviyo REST API can't edit flow filters — see CLAUDE.md rule 21).

- [ ] `NnjZbq` 2025 - Welcome Series — rules 1, 4, 5
- [ ] `SxbaYQ` Checkout Abandonment - GS — rules 1, 4, 5
- [ ] `Y7Qm8F` Abandoned Cart Reminder — rules 1, 4, 5
- [ ] `Xz9k4a` Browse Abandonment - Standard — rules 1, 4, 5
- [ ] `VvvqpW` Winback Flow — rules 1, 3, 4, 5
- [ ] `VZsFVy` Upsell Flow — rules 1, 4, 5
- [ ] `UZf9UD` Sunset Flow — rules 4, 5
- [ ] `UhxNKt` Shipment Flow — rule 5 only (transactional)
- [ ] `TFkMLx` Yard Plan Welcome Flow — rules 1, 4, 5

## Broadcast-only rules (apply to every campaign)

For every broadcast: add `Y7bP52`, `TzYTy7`, `VirYfN`, `U7H5u5` to the exclusion list. This can be templated in `create_campaigns.py` as a default.

## Changelog
- 2026-04-17: Initial documentation (Plan 1 Phase 0).
