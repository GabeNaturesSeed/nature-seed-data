# Xeriscape Email Flows + Segments Implementation Plan (Revised)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Strategy change (2026-05-05):** This plan was revised to remove all rebate calculator and rebate program content. The original plan tied the lead capture flow to a rebate calculator form that doesn't exist and used custom profile properties (`xeriscape_state`, `xeriscape_sqft`) that aren't being collected. The new strategy is simpler: sell Nature's Seed's existing drought-tolerant and xeriscape products to the right audience using state-conditional product recommendations driven by Klaviyo's built-in `$region` location property.

**Goal:** Build Klaviyo email infrastructure for Nature's Seed's xeriscaping initiative — 1 audience-triggered welcome flow (3 emails with state-conditional product recs), 3 one-time campaigns, and 2 segments.

**Architecture:** MJML templates with inline Klaviyo template tags for state personalization (conditionals live inside `mj-text` blocks — never wrapping `mj-section` elements). Templates compiled to HTML, uploaded to Klaviyo via MCP. Segments created in Klaviyo UI (API times out on GET endpoints). Campaigns created via MCP. Flow emails must be assigned to flow messages in Klaviyo UI — flow messages cannot be edited via API.

**Tech Stack:** MJML (Node.js, `node build.js`), Klaviyo MCP tools (`model: "claude"` required on every call), Klaviyo template tags (Jinja2-style), Bash curl for non-MCP API calls.

---

## Key Variables

- Working dir: `/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketing/email-system/`
- Build command: `cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketing/email-system" && node build.js`
- Placed Order metric: `VLbLXB`
- Newsletter list: `NLT2S2`
- From: `customercare@naturesseed.com` / `Nature's Seed`
- API revision: `2024-07-15`
- CTA button color: `#C96A2E` — NEVER green
- Hero bg: `#1b4332` | USP bar bg: `#2d6a4f` | Outer bg: `#f0ece4`
- All product CTAs go to: `https://www.naturesseed.com/xeriscaping/` (with utm parameters)

## Klaviyo Template Tag Conventions

**All emails (flow + campaigns) use Klaviyo's built-in profile location:**
- State: `{{ person|lookup:'$region' }}`
- Conditionals: `{% if person|lookup:'$region' == 'NV' %}` ... `{% endif %}`

There are no custom `xeriscape_state` or `xeriscape_sqft` properties — those were tied to a form that isn't being built.

**Important:** Klaviyo template tags go INSIDE `mj-text` content only. Never wrap `mj-section` or `mj-column` elements with `{% if %}` tags — MJML cannot parse that structure.

---

## Product Reference (by region)

- **NV / AZ (hot desert):** Bermudagrass Drought-Tolerant Blend, Buffalo Grass, Southwestern Wildflower Mix
- **CA coastal:** Sheep Fescue, Microclover Lawn Mix
- **CA inland:** Bermudagrass Drought-Tolerant Blend, Buffalo Grass, Southwestern Wildflower Mix
- **TX:** Buffalo Grass, Sideoats Grama, TX/OK Wildflower Mix
- **CO / UT / NM (mountain west):** Blue Grama, Sheep Fescue, Buffalo Grass (cold-hardy)
- **Default / other:** Buffalo Grass, Microclover Lawn Mix, Blue Grama

---

## File Map

| File | Purpose |
|---|---|
| `templates/xeriscape-flow-1-welcome.mjml` | Flow Email 1 — welcome / xeriscape intro / state-conditional products |
| `templates/xeriscape-flow-2-native-seed-story.mjml` | Flow Email 2 — why native seed outperforms sod in drought |
| `templates/xeriscape-flow-3-planting-window.mjml` | Flow Email 3 — planting window urgency, state-conditional timing |
| `templates/xeriscape-campaign-summer-reactivation.mjml` | Campaign — summer buyer reactivation (drought-tolerant focus) |
| `templates/xeriscape-campaign-repeat-vip.mjml` | Campaign — repeat 2023+2024 buyer VIP |
| `templates/xeriscape-campaign-nv-urgency.mjml` | Campaign — Nevada SNWA Jan 1 2027 deadline (real law, no rebate $) |

Segments and flow structure: created in Klaviyo UI (see Task 1 and Task 7).

---

## Task 1: Create Klaviyo Segments (UI) — STILL VALID

**Segments to create in Klaviyo UI at https://www.klaviyo.com/segments:**

> Klaviyo's segment GET API is unreliable — build both segments in the UI for reliability. Star both after creation. Record IDs from the URL after saving.

### Segment A: `Xeriscape Audience — 7 States`

Conditions (match ALL):
- `Location > Region` **is in** `CA, AZ, TX, NV, CO, NM, UT`
- AND one of:
  - `Has placed order` (any time) — OR
  - `Is in list` → `NLT2S2` (Newsletter)

Star this segment after saving.

### Segment B: `Summer Repeat Buyers (2023+2024)`

Conditions (match ALL):
- `Placed Order` — date between `2023-05-01` and `2023-08-31`
- AND `Placed Order` — date between `2024-05-01` and `2024-08-31`

Expected count: ~495 profiles. Do not add a state filter — the campaign email handles state-conditional content.

- [ ] Create Segment A in Klaviyo UI, star it, record ID
- [ ] Create Segment B in Klaviyo UI, record ID
- [ ] Write both IDs in a comment at the top of this plan file

---

## Task 2: Flow Email 1 — Welcome / Xeriscape Intro

**File:** `templates/xeriscape-flow-1-welcome.mjml` ✅ WRITTEN

Send timing: Immediate (0 delay after trigger)
Subject: `Grow the right thing for your climate`
Preheader: `Drought-tolerant seed, regionally selected.`

Content summary:
- Hero: "Grow the Right Thing for Your Climate"
- Welcome paragraph + xeriscape intro
- State-conditional region intro paragraph (NV/AZ, CA, TX, CO/UT/NM, default)
- 3-column state-conditional product grid (same per-region picks as product reference above)
- CTA: "Browse Xeriscape Seed" → `/xeriscaping/`

- [x] **Write the MJML template**
- [ ] **Compile and verify:**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketing/email-system" && node build.js
```

Expected: `[OK]    xeriscape-flow-1-welcome.html → XXkB` (under 90KB) — actual: 47KB ✅

- [ ] **Verify compiled HTML contains Klaviyo tags unmodified** (not HTML-encoded):

```bash
grep -c 'person|lookup' "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketing/email-system/dist/xeriscape-flow-1-welcome.html"
```

Expected: count > 0 (actual: 10). If count is 0 or if `{%25` appears instead of `{%`, the build pipeline is encoding the tags — flag as BLOCKED.

---

## Task 3: Flow Emails 2 and 3

**Files:**
- `templates/xeriscape-flow-2-native-seed-story.mjml` ✅ WRITTEN
- `templates/xeriscape-flow-3-planting-window.mjml` ✅ WRITTEN

Use the same MJML head, preheader spacer, header include, USP bar, and footer include as Email 1. Only the hero copy, body copy, and CTA block differ.

### Email 2 — Native Seed Story (Day 5)

Send timing: 5 days after Email 1
Subject: `Why native seed outperforms sod in a drought`
Preheader: `The deeper roots, the lower water bill, and the lawn that lasts.`

Content summary:
- Hero: "Why Native Seed Outperforms Sod in a Drought"
- 3 paragraphs on root depth: sod = 2-3 inches; native species (buffalo grass, blue grama, bermudagrass) = 4-6 feet
- State-conditional featured product paragraph (NV/AZ → Bermudagrass, CA → Sheep Fescue, TX → Buffalo Grass, CO/UT/NM → Blue Grama, default → Buffalo Grass)
- CTA: "Shop Xeriscape Seed" → `/xeriscaping/`

### Email 3 — Planting Window Urgency (Day 14, non-purchasers only)

Send timing: 14 days after Email 1, with conditional split — only sends to profiles who have NOT placed an order in the 14 days since flow entry.
Subject: `Your planting window is closing — order this week`
Preheader: `Drought-tolerant grasses need warm soil and time to root.`

Content summary:
- Hero: "The Window Is Closing — Plant Now"
- State-conditional planting timing paragraph (per-region: NV/AZ heat thresholds, CA coastal vs. inland, TX spring window, Mountain West late spring/early summer)
- Static value prop: U.S. farms, no fillers, 1-business-day shipping
- State-conditional best-product paragraph
- CTA: "Order My Seed" → `/xeriscaping/`

- [x] **Write all MJML files**
- [ ] **Compile all** — actual results: flow-2 = 37KB, flow-3 = 37KB ✅
- [ ] **Commit** all 3 flow templates together

```bash
git add templates/xeriscape-flow-1-welcome.mjml templates/xeriscape-flow-2-native-seed-story.mjml templates/xeriscape-flow-3-planting-window.mjml
git commit -m "feat: add xeriscape flow emails 1-3 (welcome, native-seed story, planting window)"
```

---

## Task 4: Campaign Templates

**Files:**
- `templates/xeriscape-campaign-summer-reactivation.mjml` ✅ WRITTEN
- `templates/xeriscape-campaign-repeat-vip.mjml` ✅ WRITTEN
- `templates/xeriscape-campaign-nv-urgency.mjml` ✅ WRITTEN

All three use identical MJML structure (head, preheader, header include, USP bar, footer include) and use `person|lookup:'$region'` for state conditionals. The NV urgency campaign has no state conditionals (it's NV-only — sent to a Nevada-only segment).

### Campaign A: Summer Buyer Xeriscape Reactivation

Subject: `The right seed for the dry West`
Preheader: `Drought-tolerant grass and native seed selected for your climate.`

Content summary:
- Hero: "The Lawn That Belongs in the Dry West"
- P1: Cool-season turf doesn't work anymore in the West; drought-tolerant natives (buffalo grass, blue grama, bermudagrass) do
- P2 (state-conditional): NV (Jan 1 2027 deadline angle), CA (drought + coastal sheep fescue), CO (2026 commercial turf ban), TX (state grasses), AZ (desert grasses), default
- 3-column state-conditional product grid
- CTA: "Shop Xeriscape Seed" → `/xeriscaping/`

### Campaign B: Repeat Buyer VIP

Subject: `You know how to seed — try xeriscape this summer`
Preheader: `You seed every summer. Here's our drought-tolerant lineup for yours.`

Content summary:
- Hero: "You Know How to Seed — Try Xeriscape"
- P1: You're a returning customer; we want to flag the drought-tolerant xeriscape category — same farm-direct seed program
- P2 (state-conditional): per-region context (NV deadline, CA drought, CO turf ban, TX natives, AZ desert)
- P3: "Here's what we recommend for your region this summer..."
- 3-column state-conditional product grid
- CTA: "Shop My Summer Picks" → `/xeriscaping/`

### Campaign C: NV Urgency (June 2026)

Subject: `Las Vegas: 6 months until decorative turf irrigation is illegal`
Preheader: `Nevada's restriction on decorative turf irrigation takes effect Jan 1, 2027.`

Content summary (NV-only — no state conditionals):
- Hero: "Jan 1, 2027: Watering Your Grass Becomes Illegal"
- P1: SNWA restriction details — medians, commercial strips, HOA common areas, residential decorative turf
- P2: Path forward = drought-tolerant native species (Bermudagrass, buffalo grass, Southwestern Wildflower Mix)
- P3: October 2026 = practical seed-in-ground deadline for fall establishment before winter
- 3-column fixed product grid (NV products): Bermudagrass Drought-Tolerant Blend, Buffalo Grass, Southwestern Wildflower Mix
- CTA: "Shop Drought-Tolerant Seed" → `/xeriscaping/`

**No rebate dollar amounts mentioned anywhere.** The Jan 1 2027 SNWA restriction is a real Nevada law — that urgency angle stays. No `$2/sq ft` numbers, no `your rebate is $X` content.

- [x] **Write all three MJML campaign files**
- [ ] **Compile** — actual results: summer-reactivation = 45KB, repeat-vip = 47KB, nv-urgency = 46KB ✅
- [ ] **Commit:**

```bash
git add templates/xeriscape-campaign-summer-reactivation.mjml templates/xeriscape-campaign-repeat-vip.mjml templates/xeriscape-campaign-nv-urgency.mjml
git commit -m "feat: add xeriscape campaign templates (reactivation, VIP, NV urgency)"
```

---

## Task 5: Create Klaviyo Email Templates (6 Total)

For each of the 6 compiled HTML files, call `klaviyo_create_email_template`. Read the compiled HTML from the `dist/` directory first.

> **Currently blocked:** Klaviyo MCP tools have been timing out in this session. Defer this task to a session where the MCP tools are responsive. Templates are built and compiled — uploading them is a mechanical step.

**Files to upload (in order):**
1. `dist/xeriscape-flow-1-welcome.html` → template name: `Xeriscape Flow 1 — Welcome`
2. `dist/xeriscape-flow-2-native-seed-story.html` → template name: `Xeriscape Flow 2 — Native Seed Story`
3. `dist/xeriscape-flow-3-planting-window.html` → template name: `Xeriscape Flow 3 — Planting Window`
4. `dist/xeriscape-campaign-summer-reactivation.html` → template name: `Xeriscape — Summer Reactivation`
5. `dist/xeriscape-campaign-repeat-vip.html` → template name: `Xeriscape — Repeat Buyer VIP`
6. `dist/xeriscape-campaign-nv-urgency.html` → template name: `Xeriscape — NV Urgency`

For each, call:
```
klaviyo_create_email_template(
  model="claude",
  name="<template name>",
  html="<full compiled HTML content>"
)
```

- [ ] Create all 6 Klaviyo email templates
- [ ] Record all 6 template IDs
- [ ] Write template IDs to a comment block at the top of this plan file:

```
<!-- TEMPLATE IDs
  Flow 1 (Welcome): XXXXXX
  Flow 2 (Native Seed Story): XXXXXX
  Flow 3 (Planting Window): XXXXXX
  Campaign - Summer Reactivation: XXXXXX
  Campaign - Repeat VIP: XXXXXX
  Campaign - NV Urgency: XXXXXX
-->
```

---

## Task 6: Create Campaigns + Assign Templates

Create 3 Klaviyo campaigns via `klaviyo_create_campaign` (all require `model: "claude"`):

### Campaign A: Summer Buyer Xeriscape Reactivation

```python
klaviyo_create_campaign(
  model="claude",
  input={
    "data": {
      "type": "campaign",
      "attributes": {
        "name": "Xeriscape Summer 2026 Reactivation",
        "audiences": {
          "included": ["<XERISCAPE_7_STATE_SEGMENT_ID>"]
          # NOTE: To target only past summer buyers without recent purchase / not in flow,
          # build a dedicated segment in UI (Region in 7 states AND past summer order AND
          # no order in last 90d AND not in xeriscape welcome flow). For initial send,
          # using the Xeriscape 7-State segment is acceptable — refine after first send.
        },
        "campaignMessages": {
          "data": [{
            "type": "campaign-message",
            "attributes": {
              "definition": {
                "channel": "email",
                "content": {
                  "subject": "The right seed for the dry West",
                  "fromEmail": "customercare@naturesseed.com",
                  "fromLabel": "Nature's Seed",
                  "previewText": "Drought-tolerant grass and native seed selected for your climate."
                }
              }
            }
          }]
        },
        "sendStrategy": {
          "method": "static",
          "options_static": {
            "datetime": "2026-05-08T16:00:00+00:00",
            "is_local": false
          }
        }
      }
    }
  }
)
```

After creation:
1. Call `klaviyo_get_campaign` to get the message ID
2. Call `klaviyo_assign_template_to_campaign_message` with the Summer Reactivation template ID

### Campaign B: Repeat Buyer VIP

```python
klaviyo_create_campaign(
  model="claude",
  input={
    "data": {
      "type": "campaign",
      "attributes": {
        "name": "Xeriscape Repeat Buyer VIP 2026",
        "audiences": {
          "included": ["<SUMMER_REPEAT_BUYERS_SEGMENT_ID>"]
        },
        "campaignMessages": {
          "data": [{
            "type": "campaign-message",
            "attributes": {
              "definition": {
                "channel": "email",
                "content": {
                  "subject": "You know how to seed — try xeriscape this summer",
                  "fromEmail": "customercare@naturesseed.com",
                  "fromLabel": "Nature's Seed",
                  "previewText": "You seed every summer. Here's our drought-tolerant lineup for yours."
                }
              }
            }
          }]
        },
        "sendStrategy": {
          "method": "static",
          "options_static": {
            "datetime": "2026-05-07T16:00:00+00:00",
            "is_local": false
          }
        }
      }
    }
  }
)
```

After creation: get message ID → assign Repeat VIP template.

### Campaign C: NV Urgency (June 2026)

Audience: all Nevada profiles — create an NV-only segment in Klaviyo UI (`Location > Region equals NV` AND `Has placed order` OR `Is in list NLT2S2`) and use that segment ID.

```python
klaviyo_create_campaign(
  model="claude",
  input={
    "data": {
      "type": "campaign",
      "attributes": {
        "name": "Xeriscape NV Urgency — June 2026",
        "audiences": {
          "included": ["<NV_ONLY_SEGMENT_ID>"]
        },
        "campaignMessages": {
          "data": [{
            "type": "campaign-message",
            "attributes": {
              "definition": {
                "channel": "email",
                "content": {
                  "subject": "Las Vegas: 6 months until decorative turf irrigation is illegal",
                  "fromEmail": "customercare@naturesseed.com",
                  "fromLabel": "Nature's Seed",
                  "previewText": "Nevada's restriction on decorative turf irrigation takes effect Jan 1, 2027."
                }
              }
            }
          }]
        },
        "sendStrategy": {
          "method": "static",
          "options_static": {
            "datetime": "2026-06-02T16:00:00+00:00",
            "is_local": false
          }
        }
      }
    }
  }
)
```

After creation: get message ID → assign NV Urgency template.

- [ ] Create all 3 campaigns
- [ ] Get message IDs for all 3
- [ ] Assign templates to all 3 messages
- [ ] Record campaign IDs, message IDs, template IDs assigned
- [ ] Do NOT schedule (leave as Draft — user will activate after review)

---

## Task 7: Flow Setup (Klaviyo UI)

> Flow messages cannot be created or edited via API. The entire flow must be built in the Klaviyo UI. Complete Task 5 first so the template IDs are ready to assign.

**Flow name:** `Xeriscape Welcome`

**Trigger:** **Segment Trigger** — Profile added to segment `Xeriscape Audience — 7 States` (segment ID from Task 1)

This replaces the original "Profile Added to List with `xeriscape_rebate_lead = true` filter" trigger because the rebate form was cancelled. Segment-triggered flows fire whenever a profile newly enters the segment, which gives every existing customer in the 7-state region a clean entry point.

**Step-by-step in Klaviyo UI (https://www.klaviyo.com/flows):**

1. Click **Create Flow** → **Create From Scratch**
2. Name: `Xeriscape Welcome`
3. Trigger: **Segment** → select `Xeriscape Audience — 7 States`
4. Click **Save** on trigger config

**Add Email 1 (immediate):**
5. Click **+** below trigger → **Action** → **Send Email**
6. Click the email block → **Edit** → under template, search for `Xeriscape Flow 1 — Welcome`
7. Subject: `Grow the right thing for your climate`
8. From: `customercare@naturesseed.com` / `Nature's Seed`
9. Click **Done**

**Add Time Delay → Email 2 (Day 5):**
10. Click **+** below Email 1 → **Time Delay** → 5 days
11. Click **+** below delay → **Action** → **Send Email**
12. Assign template: `Xeriscape Flow 2 — Native Seed Story`
13. Subject: `Why native seed outperforms sod in a drought`

**Add Conditional Split → Email 3 (Day 14, non-purchasers only):**
14. Click **+** below Email 2 → **Time Delay** → 9 days (total 14 from trigger)
15. Add **Conditional Split**:
    - Condition: `Has placed order` → **at least once** → **in the last 14 days**
    - YES path → End flow (do not send Email 3)
    - NO path → continue
16. On NO path, add **Send Email** → assign `Xeriscape Flow 3 — Planting Window`
17. Subject: `Your planting window is closing — order this week`

18. Set flow to **Draft** until reviewed. Do not activate yet.
19. Record flow ID from the URL: `https://www.klaviyo.com/flows/FLOW_ID`

- [ ] Build flow in Klaviyo UI following steps above
- [ ] Assign all 3 templates to flow email messages
- [ ] Set conditional split on Email 3 for non-purchasers only
- [ ] Leave as Draft
- [ ] Record flow ID

---

## Self-Review

**Spec coverage check:**

| Requirement | Covered in |
|---|---|
| Xeriscape Welcome Flow — 3 emails | Tasks 2, 3, 7 |
| State-conditional product recs (`$region`) | Tasks 2, 3, 4 |
| Email 3 non-purchasers only | Task 7 (conditional split) |
| Summer Buyer Xeriscape Reactivation campaign | Tasks 4, 6 |
| Repeat Buyer VIP segment + campaign | Tasks 1, 4, 6 |
| NV Urgency campaign (June, real-law angle, no rebate $) | Tasks 4, 6 |
| Xeriscape Audience — 7 States segment (starred) | Task 1 |
| Summer Repeat Buyers segment | Task 1 |
| All product CTAs to `/xeriscaping/` | Tasks 2, 3, 4 |
| No rebate calculator content | Removed from all templates |
| No `xeriscape_state` / `xeriscape_sqft` properties | Removed from all templates |

**Removed from previous plan version (deliberate):**
- Task 2 (Email 1 "Rebate Estimate") — replaced with welcome
- Task 3 Email 2 ($8K vs $200 cost comparison) — replaced with native seed root-depth story (no rebate stacking math)
- Task 3 Email 3 (rebate paperwork checklist) — dropped entirely
- Task 3 Email 4 (state-deadline urgency tied to rebates) — replaced with planting-window urgency
- All `$X/sq ft` rebate dollar amounts (SNWA $2, MWD $5, Denver Water $1) — removed
- Custom profile properties (`xeriscape_state`, `xeriscape_sqft`)
- Form-trigger filter on flow

**Flags for manual review:**
1. **Audience for Summer Reactivation:** The original spec called for filtering for past summer buyers + no purchase 90d + excluding flow entrants. That layered filter requires a custom segment in UI. For first send, using the `Xeriscape Audience — 7 States` segment is acceptable; refine after measuring engagement.
2. **NV-only segment:** Create `Xeriscape Audience — NV` in UI (Region = NV AND has placed order OR in NLT2S2) before Task 6 Campaign C.
3. **Segment trigger debouncing:** Klaviyo segment-triggered flows can re-fire if a profile leaves and re-enters the segment. For an evergreen welcome flow this is fine; if seasonal repeats become a concern, add a flow-level filter "Has not been in this flow in last 365 days."
4. **Klaviyo MCP timeout:** Tasks 5 and 6 are deferred — execute when MCP tools are responsive. Templates and plan are ready.
