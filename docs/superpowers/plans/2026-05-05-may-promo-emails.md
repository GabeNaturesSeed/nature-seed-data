# May 2026 Promotional Email Campaigns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish three promotional email campaigns targeting +$25,239 in email-attributed revenue for May 2026.

**Architecture:** Each campaign follows the same pipeline: write MJML template → compile to HTML via `node build.js` → create Klaviyo email template via MCP → create or update Klaviyo campaign via MCP → assign template to campaign message. Campaign 2 upgrades four existing scheduled campaigns in place rather than creating new ones.

**Tech Stack:** MJML (compiled via Node), Klaviyo MCP (`2024-07-15` revision), `~/.party/lib/assets.py` for image URLs, `natures-seed-brand` skill for copy voice.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `marketing/email-system/templates/may-mothers-day-wildflower.mjml` | Create | Campaign 1 — wildflower variant |
| `marketing/email-system/templates/may-mothers-day-lawn.mjml` | Create | Campaign 1 — lawn variant |
| `marketing/email-system/templates/may-spring-closing-lawn.mjml` | Create | Campaign 2 — lawn upgrade |
| `marketing/email-system/templates/may-spring-closing-pasture.mjml` | Create | Campaign 2 — pasture upgrade |
| `marketing/email-system/templates/may-spring-closing-wildflower.mjml` | Create | Campaign 2 — wildflower upgrade |
| `marketing/email-system/templates/may-spring-closing-specialty.mjml` | Create | Campaign 2 — specialty upgrade |
| `marketing/email-system/templates/may-summer-arrives.mjml` | Create | Campaign 3 |
| `marketing/email-system/dist/*.html` | Auto-generated | Compiled output, uploaded to Klaviyo |

---

## Reference: Klaviyo Campaign IDs (C5 Spring Activation — existing, to upgrade)

- Lawn: `01KM13ZM4TQBKEPDNXAB4PJJ38`
- Pasture: `01KM13ZJD2DK3S5W7BQJ4HH6KP`
- Wildflower: `01KM13ZGWH1YP8N7PKJPNZX9Q8`
- Specialty: `01KM13ZFFDQC9EG56GQX0SYJ84`

## Reference: Segment IDs

- E60D Engaged: `RbH7na`
- Champions Active: `VtKptn`
- Champions: `RAQTca`
- Active This Season: `RbGRqF`
- Warm: `WdpJti`

---

## Task 1: Brand Voice + Asset Images (Prep)

**Files:** No files created. Outputs feed into Tasks 2–5.

- [ ] **Step 1: Load brand skill**

```
Invoke: natures-seed-brand skill
```

Read and internalize the brand voice, tone, and messaging pillars before writing any copy. Key principles: direct, farmer-credible, no fluff, nature's wisdom framing.

- [ ] **Step 2: Get asset image URL for wildflower/Mother's Day hero**

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.party/lib"))
from assets import get_asset

asset = get_asset(suggested_use="email_header", aspect_ratio="16:9")
print("klaviyo_url:", asset["klaviyo_url"])
print("alt_text:", asset["alt_text"])
```

Run from: `/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/`

Save the returned `klaviyo_url` and `alt_text`. This is `WILDFLOWER_HERO_URL` used in Task 2.

- [ ] **Step 3: Get asset image URL for lawn hero**

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.party/lib"))
from assets import get_asset

asset = get_asset(suggested_use="email_header", aspect_ratio="16:9")
print("klaviyo_url:", asset["klaviyo_url"])
print("alt_text:", asset["alt_text"])
```

Save as `LAWN_HERO_URL`. If the same image is returned, call again to get a different one.

- [ ] **Step 4: Get asset image URL for summer/closing hero**

Same script. Save as `SUMMER_HERO_URL` — used in Tasks 4 and 5.

- [ ] **Step 5: Verify Node and MJML are available**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketing/email-system"
node -v && node -e "require('mjml')" && echo "MJML OK"
```

Expected output: Node version + `MJML OK`. If MJML missing: `npm install`.

---

## Task 2: Campaign 1 — Mother's Day Wildflower (May 9)

**Files:**
- Create: `marketing/email-system/templates/may-mothers-day-wildflower.mjml`
- Auto-compiled: `marketing/email-system/dist/may-mothers-day-wildflower.html`

- [ ] **Step 1: Write MJML template**

Create `marketing/email-system/templates/may-mothers-day-wildflower.mjml`:

```mjml
<mjml>
  <mj-head>
    <mj-preview>A native wildflower meadow, growing in her name. 10% off through Sunday.</mj-preview>

    <mj-font name="Noto Serif Display" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:ital,wght@0,600;0,700;1,700&family=Inter:wght@400;500;600&display=swap" />

    <mj-attributes>
      <mj-all font-family="Inter, Arial, sans-serif" />
      <mj-body width="620px" background-color="#f0ece4" />
    </mj-attributes>

    <mj-style>
      @media only screen and (max-width: 480px) {
        .product-col { display: block !important; width: 100% !important; }
      }
    </mj-style>
  </mj-head>

  <mj-body>
    <!-- Preheader spacer -->
    <mj-section padding="0">
      <mj-column>
        <mj-text font-size="1px" color="#f0ece4" padding="0">
          &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-include path="../components/header.mjml" />

    <!-- Hero Section -->
    <mj-section background-color="#1b4332" padding="64px 48px 56px">
      <mj-column>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#d4a373" letter-spacing="0.14em" text-transform="uppercase" padding-bottom="20px">
          Mother's Day 2026
        </mj-text>
        <mj-text align="center" font-family="'Noto Serif Display', Georgia, serif" font-size="46px" font-weight="700" color="#ffffff" line-height="1.10" letter-spacing="-0.01em" padding-bottom="20px">
          Give her<br/>
          <span style="font-style:italic;color:#a8d5b5;">a meadow.</span>
        </mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="16px" color="#a8d5b5" line-height="1.6" padding-bottom="32px">
          Native wildflower seed, farm-direct. Something that grows<br/>
          year after year, not just once.
        </mj-text>
        <mj-button
          align="center"
          background-color="#C96A2E"
          color="#ffffff"
          border-radius="2px"
          font-family="Inter, Arial, sans-serif"
          font-size="14px"
          font-weight="600"
          letter-spacing="0.04em"
          text-transform="uppercase"
          inner-padding="16px 36px"
          href="https://www.naturesseed.com/collections/wildflower-seed"
        >
          Shop Mother's Day Gifts
        </mj-button>
        <mj-divider border-color="#d4a373" border-width="3px" width="48px" padding="40px 0 0" />
      </mj-column>
    </mj-section>

    <!-- Body Copy -->
    <mj-section background-color="#ffffff" padding="48px 48px 0">
      <mj-column>
        <mj-text align="left" font-family="Inter, Arial, sans-serif" font-size="15px" color="#3d3d3d" line-height="1.75" padding-bottom="0">
          Flowers bought from a store are gone in a week. A wildflower meadow comes back every spring. Our native wildflower mixes are selected for your region — no filler seed, no plastic packaging, no landfill after the petals drop.
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-section background-color="#ffffff" padding="24px 48px 0">
      <mj-column>
        <mj-text align="left" font-family="Inter, Arial, sans-serif" font-size="15px" color="#3d3d3d" line-height="1.75" padding-bottom="0">
          Use code <strong>MOM10</strong> at checkout for 10% off through Sunday, May 11th.
        </mj-text>
      </mj-column>
    </mj-section>

    <!-- Promo Code Callout -->
    <mj-section background-color="#ffffff" padding="36px 48px 48px">
      <mj-column border="2px solid #C96A2E" border-radius="4px" padding="28px 32px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#6c757d" letter-spacing="0.14em" text-transform="uppercase" padding-bottom="10px">
          Your Discount Code
        </mj-text>
        <mj-text align="center" font-family="'Noto Serif Display', Georgia, serif" font-size="36px" font-weight="700" color="#C96A2E" letter-spacing="0.08em" padding-bottom="10px">
          MOM10
        </mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="13px" color="#6c757d" padding="0">
          10% off site-wide · Expires May 11, 2026
        </mj-text>
      </mj-column>
    </mj-section>

    <!-- CTA Block -->
    <mj-section background-color="#ffffff" padding="0 48px 48px" border-top="1px solid #e8e4dc">
      <mj-column>
        <mj-text align="center" font-family="'Noto Serif Display', Georgia, serif" font-size="22px" font-weight="600" color="#1b4332" line-height="1.3" padding-bottom="12px" padding-top="40px">
          Give something that grows.
        </mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="14px" color="#6c757d" line-height="1.6" padding-bottom="24px">
          Native wildflower mixes, regionally tested.<br/>
          Ships in 1 business day.
        </mj-text>
        <mj-button
          align="center"
          background-color="#C96A2E"
          color="#ffffff"
          border-radius="2px"
          font-family="Inter, Arial, sans-serif"
          font-size="14px"
          font-weight="600"
          letter-spacing="0.04em"
          text-transform="uppercase"
          inner-padding="16px 36px"
          href="https://www.naturesseed.com/collections/wildflower-seed"
        >
          Shop Mother's Day Gifts
        </mj-button>
      </mj-column>
    </mj-section>

    <!-- USP Bar -->
    <mj-section background-color="#2d6a4f" padding="28px 40px">
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">American Farm-Direct</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">Grown on U.S. farms</mj-text>
      </mj-column>
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">No Fillers</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">Pure, tested seed</mj-text>
      </mj-column>
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">Ships in 1 Business Day</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">Arrives before Sunday</mj-text>
      </mj-column>
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">Satisfaction Guaranteed</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">We stand behind our seed</mj-text>
      </mj-column>
    </mj-section>

    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

- [ ] **Step 2: Compile and verify**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketing/email-system"
node build.js
```

Expected: `[OK]    may-mothers-day-wildflower.html → XXkB` where XX < 90. If CLIP or WARN, trim copy.

- [ ] **Step 3: Create Klaviyo email template**

```
Tool: klaviyo_create_email_template
model: "claude"
name: "May 2026 — Mother's Day Wildflower"
html: <full contents of dist/may-mothers-day-wildflower.html>
```

Save the returned template ID as `TEMPLATE_ID_WILDFLOWER_MD`.

- [ ] **Step 4: Create Klaviyo campaign**

```
Tool: klaviyo_create_campaign
model: "claude"
data:
  type: "campaign"
  attributes:
    name: "Mother's Day — Wildflower & Lawn Gift (Wildflower)"
    audiences:
      included: ["RbH7na"]
    send_strategy:
      method: "static"
      options_static:
        datetime: "2026-05-09T16:00:00Z"
        is_local: false
    campaign-messages:
      data:
        - type: "campaign-message"
          attributes:
            channel: "email"
            content:
              subject: "Give her a meadow this Mother's Day"
              preview_text: "Native wildflower seed, farm-direct. Something that grows year after year."
              from_email: "customercare@naturesseed.com"
              from_label: "Nature's Seed"
              reply_to_email: "customercare@naturesseed.com"
```

Save returned campaign ID as `CAMPAIGN_ID_WF_MD` and message ID as `MESSAGE_ID_WF_MD`.

- [ ] **Step 5: Assign template to campaign message**

```
Tool: klaviyo_assign_template_to_campaign_message
model: "claude"
campaign_message_id: <MESSAGE_ID_WF_MD>
template_id: <TEMPLATE_ID_WILDFLOWER_MD>
```

- [ ] **Step 6: Verify campaign in Klaviyo**

```
Tool: klaviyo_get_campaign
model: "claude"
campaign_id: <CAMPAIGN_ID_WF_MD>
```

Confirm: status = Draft, send time = 2026-05-09T16:00:00Z, segment = RbH7na, subject correct.

- [ ] **Step 7: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add marketing/email-system/templates/may-mothers-day-wildflower.mjml marketing/email-system/dist/may-mothers-day-wildflower.html
git commit -m "feat: add Mother's Day wildflower email template (Campaign 1a)"
```

---

## Task 3: Campaign 1 — Mother's Day Lawn (May 9)

**Files:**
- Create: `marketing/email-system/templates/may-mothers-day-lawn.mjml`
- Auto-compiled: `marketing/email-system/dist/may-mothers-day-lawn.html`

- [ ] **Step 1: Write MJML template**

Create `marketing/email-system/templates/may-mothers-day-lawn.mjml`. Same structure as Task 2 with these changes:

```mjml
<mjml>
  <mj-head>
    <mj-preview>Give her the yard she's always wanted. 10% off through Sunday.</mj-preview>

    <mj-font name="Noto Serif Display" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:ital,wght@0,600;0,700;1,700&family=Inter:wght@400;500;600&display=swap" />

    <mj-attributes>
      <mj-all font-family="Inter, Arial, sans-serif" />
      <mj-body width="620px" background-color="#f0ece4" />
    </mj-attributes>

    <mj-style>
      @media only screen and (max-width: 480px) {
        .product-col { display: block !important; width: 100% !important; }
      }
    </mj-style>
  </mj-head>

  <mj-body>
    <!-- Preheader spacer -->
    <mj-section padding="0">
      <mj-column>
        <mj-text font-size="1px" color="#f0ece4" padding="0">
          &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-include path="../components/header.mjml" />

    <!-- Hero Section -->
    <mj-section background-color="#1b4332" padding="64px 48px 56px">
      <mj-column>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#d4a373" letter-spacing="0.14em" text-transform="uppercase" padding-bottom="20px">
          Mother's Day 2026
        </mj-text>
        <mj-text align="center" font-family="'Noto Serif Display', Georgia, serif" font-size="46px" font-weight="700" color="#ffffff" line-height="1.10" letter-spacing="-0.01em" padding-bottom="20px">
          Give her<br/>
          <span style="font-style:italic;color:#a8d5b5;">a yard she loves.</span>
        </mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="16px" color="#a8d5b5" line-height="1.6" padding-bottom="32px">
          Farm-direct lawn seed, regionally tested.<br/>
          A gift that keeps growing.
        </mj-text>
        <mj-button
          align="center"
          background-color="#C96A2E"
          color="#ffffff"
          border-radius="2px"
          font-family="Inter, Arial, sans-serif"
          font-size="14px"
          font-weight="600"
          letter-spacing="0.04em"
          text-transform="uppercase"
          inner-padding="16px 36px"
          href="https://www.naturesseed.com/collections/lawn-seed"
        >
          Shop Mother's Day Gifts
        </mj-button>
        <mj-divider border-color="#d4a373" border-width="3px" width="48px" padding="40px 0 0" />
      </mj-column>
    </mj-section>

    <!-- Body Copy -->
    <mj-section background-color="#ffffff" padding="48px 48px 0">
      <mj-column>
        <mj-text align="left" font-family="Inter, Arial, sans-serif" font-size="15px" color="#3d3d3d" line-height="1.75" padding-bottom="0">
          A great lawn doesn't happen by accident. It starts with the right seed — blended for your region, tested for germination, and grown without fillers. If she's been talking about the yard, this is the year to do something about it.
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-section background-color="#ffffff" padding="24px 48px 0">
      <mj-column>
        <mj-text align="left" font-family="Inter, Arial, sans-serif" font-size="15px" color="#3d3d3d" line-height="1.75" padding-bottom="0">
          Use code <strong>MOM10</strong> at checkout for 10% off through Sunday, May 11th.
        </mj-text>
      </mj-column>
    </mj-section>

    <!-- Promo Code Callout -->
    <mj-section background-color="#ffffff" padding="36px 48px 48px">
      <mj-column border="2px solid #C96A2E" border-radius="4px" padding="28px 32px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#6c757d" letter-spacing="0.14em" text-transform="uppercase" padding-bottom="10px">
          Your Discount Code
        </mj-text>
        <mj-text align="center" font-family="'Noto Serif Display', Georgia, serif" font-size="36px" font-weight="700" color="#C96A2E" letter-spacing="0.08em" padding-bottom="10px">
          MOM10
        </mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="13px" color="#6c757d" padding="0">
          10% off site-wide · Expires May 11, 2026
        </mj-text>
      </mj-column>
    </mj-section>

    <!-- CTA Block -->
    <mj-section background-color="#ffffff" padding="0 48px 48px" border-top="1px solid #e8e4dc">
      <mj-column>
        <mj-text align="center" font-family="'Noto Serif Display', Georgia, serif" font-size="22px" font-weight="600" color="#1b4332" line-height="1.3" padding-bottom="12px" padding-top="40px">
          The yard she's been waiting for.
        </mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="14px" color="#6c757d" line-height="1.6" padding-bottom="24px">
          Regionally tested lawn seed, farm-direct.<br/>
          Ships in 1 business day.
        </mj-text>
        <mj-button
          align="center"
          background-color="#C96A2E"
          color="#ffffff"
          border-radius="2px"
          font-family="Inter, Arial, sans-serif"
          font-size="14px"
          font-weight="600"
          letter-spacing="0.04em"
          text-transform="uppercase"
          inner-padding="16px 36px"
          href="https://www.naturesseed.com/collections/lawn-seed"
        >
          Shop Mother's Day Gifts
        </mj-button>
      </mj-column>
    </mj-section>

    <!-- USP Bar -->
    <mj-section background-color="#2d6a4f" padding="28px 40px">
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">American Farm-Direct</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">Grown on U.S. farms</mj-text>
      </mj-column>
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">No Fillers</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">Pure, tested seed</mj-text>
      </mj-column>
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">Ships in 1 Business Day</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">Arrives before Sunday</mj-text>
      </mj-column>
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">Satisfaction Guaranteed</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">We stand behind our seed</mj-text>
      </mj-column>
    </mj-section>

    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

- [ ] **Step 2: Compile and verify**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketing/email-system"
node build.js
```

Expected: `[OK]    may-mothers-day-lawn.html → XXkB`

- [ ] **Step 3: Create Klaviyo email template**

```
Tool: klaviyo_create_email_template
model: "claude"
name: "May 2026 — Mother's Day Lawn"
html: <full contents of dist/may-mothers-day-lawn.html>
```

Save returned template ID as `TEMPLATE_ID_LAWN_MD`.

- [ ] **Step 4: Create Klaviyo campaign**

```
Tool: klaviyo_create_campaign
model: "claude"
data:
  type: "campaign"
  attributes:
    name: "Mother's Day — Wildflower & Lawn Gift (Lawn)"
    audiences:
      included: ["RbH7na"]
    send_strategy:
      method: "static"
      options_static:
        datetime: "2026-05-09T16:00:00Z"
        is_local: false
    campaign-messages:
      data:
        - type: "campaign-message"
          attributes:
            channel: "email"
            content:
              subject: "The gift of a better yard (10% off this weekend)"
              preview_text: "Give her the yard she's been waiting for. Regionally tested lawn seed, ships in 1 business day."
              from_email: "customercare@naturesseed.com"
              from_label: "Nature's Seed"
              reply_to_email: "customercare@naturesseed.com"
```

Save returned campaign ID as `CAMPAIGN_ID_LAWN_MD` and message ID as `MESSAGE_ID_LAWN_MD`.

- [ ] **Step 5: Assign template**

```
Tool: klaviyo_assign_template_to_campaign_message
model: "claude"
campaign_message_id: <MESSAGE_ID_LAWN_MD>
template_id: <TEMPLATE_ID_LAWN_MD>
```

- [ ] **Step 6: Verify campaign**

```
Tool: klaviyo_get_campaign
model: "claude"
campaign_id: <CAMPAIGN_ID_LAWN_MD>
```

Confirm: status = Draft, send time = 2026-05-09T16:00:00Z, segment = RbH7na, subject = "The gift of a better yard (10% off this weekend)".

- [ ] **Step 7: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add marketing/email-system/templates/may-mothers-day-lawn.mjml marketing/email-system/dist/may-mothers-day-lawn.html
git commit -m "feat: add Mother's Day lawn email template (Campaign 1b)"
```

---

## Task 4: Campaign 2 — C5 Spring Activation Upgrade (May 20, 4 Sends)

**Files:**
- Create: `marketing/email-system/templates/may-spring-closing-lawn.mjml`
- Create: `marketing/email-system/templates/may-spring-closing-pasture.mjml`
- Create: `marketing/email-system/templates/may-spring-closing-wildflower.mjml`
- Create: `marketing/email-system/templates/may-spring-closing-specialty.mjml`

All four follow the same template structure. The differences are the hero label, headline italic, body copy, and CTA href. Write all four, compile, then assign to existing campaign messages.

- [ ] **Step 1: Get existing campaign message IDs**

For each of the four existing C5 campaigns, retrieve the message ID:

```
Tool: klaviyo_get_campaign
model: "claude"
campaign_id: "01KM13ZM4TQBKEPDNXAB4PJJ38"
```
Save message ID as `MSG_C5_LAWN`.

```
Tool: klaviyo_get_campaign
model: "claude"
campaign_id: "01KM13ZJD2DK3S5W7BQJ4HH6KP"
```
Save message ID as `MSG_C5_PASTURE`.

```
Tool: klaviyo_get_campaign
model: "claude"
campaign_id: "01KM13ZGWH1YP8N7PKJPNZX9Q8"
```
Save message ID as `MSG_C5_WILDFLOWER`.

```
Tool: klaviyo_get_campaign
model: "claude"
campaign_id: "01KM13ZFFDQC9EG56GQX0SYJ84"
```
Save message ID as `MSG_C5_SPECIALTY`.

- [ ] **Step 2: Write Lawn MJML**

Create `marketing/email-system/templates/may-spring-closing-lawn.mjml`:

```mjml
<mjml>
  <mj-head>
    <mj-preview>Grass planted now establishes before summer heat. 12% off through May 25th.</mj-preview>
    <mj-font name="Noto Serif Display" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:ital,wght@0,600;0,700;1,700&family=Inter:wght@400;500;600&display=swap" />
    <mj-attributes>
      <mj-all font-family="Inter, Arial, sans-serif" />
      <mj-body width="620px" background-color="#f0ece4" />
    </mj-attributes>
    <mj-style>
      @media only screen and (max-width: 480px) {
        .product-col { display: block !important; width: 100% !important; }
      }
    </mj-style>
  </mj-head>
  <mj-body>
    <mj-section padding="0">
      <mj-column>
        <mj-text font-size="1px" color="#f0ece4" padding="0">
          &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
        </mj-text>
      </mj-column>
    </mj-section>
    <mj-include path="../components/header.mjml" />
    <mj-section background-color="#1b4332" padding="64px 48px 56px">
      <mj-column>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#d4a373" letter-spacing="0.14em" text-transform="uppercase" padding-bottom="20px">
          Last Call for Spring
        </mj-text>
        <mj-text align="center" font-family="'Noto Serif Display', Georgia, serif" font-size="46px" font-weight="700" color="#ffffff" line-height="1.10" letter-spacing="-0.01em" padding-bottom="20px">
          Plant before<br/>
          <span style="font-style:italic;color:#a8d5b5;">summer heat arrives.</span>
        </mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="16px" color="#a8d5b5" line-height="1.6" padding-bottom="32px">
          Seed planted now has 3–4 weeks to establish<br/>
          roots before temperatures spike. After that, it's uphill.
        </mj-text>
        <mj-button align="center" background-color="#C96A2E" color="#ffffff" border-radius="2px" font-family="Inter, Arial, sans-serif" font-size="14px" font-weight="600" letter-spacing="0.04em" text-transform="uppercase" inner-padding="16px 36px" href="https://www.naturesseed.com/collections/lawn-seed">
          Plant Before Summer
        </mj-button>
        <mj-divider border-color="#d4a373" border-width="3px" width="48px" padding="40px 0 0" />
      </mj-column>
    </mj-section>
    <mj-section background-color="#ffffff" padding="48px 48px 0">
      <mj-column>
        <mj-text align="left" font-family="Inter, Arial, sans-serif" font-size="15px" color="#3d3d3d" line-height="1.75" padding-bottom="0">
          Most cool-season grasses need soil temps under 75°F to germinate well. In most of the U.S., that window closes between mid-June and early July. You've got about three weeks to get seed in the ground and let it take hold before summer stress kicks in.
        </mj-text>
      </mj-column>
    </mj-section>
    <mj-section background-color="#ffffff" padding="24px 48px 0">
      <mj-column>
        <mj-text align="left" font-family="Inter, Arial, sans-serif" font-size="15px" color="#3d3d3d" line-height="1.75" padding-bottom="0">
          Use code <strong>SPRING12</strong> for 12% off through May 25th.
        </mj-text>
      </mj-column>
    </mj-section>
    <mj-section background-color="#ffffff" padding="36px 48px 48px">
      <mj-column border="2px solid #C96A2E" border-radius="4px" padding="28px 32px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#6c757d" letter-spacing="0.14em" text-transform="uppercase" padding-bottom="10px">Your Discount Code</mj-text>
        <mj-text align="center" font-family="'Noto Serif Display', Georgia, serif" font-size="36px" font-weight="700" color="#C96A2E" letter-spacing="0.08em" padding-bottom="10px">SPRING12</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="13px" color="#6c757d" padding="0">12% off site-wide · Expires May 25, 2026</mj-text>
      </mj-column>
    </mj-section>
    <mj-section background-color="#ffffff" padding="0 48px 48px" border-top="1px solid #e8e4dc">
      <mj-column>
        <mj-text align="center" font-family="'Noto Serif Display', Georgia, serif" font-size="22px" font-weight="600" color="#1b4332" line-height="1.3" padding-bottom="12px" padding-top="40px">Three weeks. Make them count.</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="14px" color="#6c757d" line-height="1.6" padding-bottom="24px">Regionally tested lawn seed, farm-direct.<br/>Ships in 1 business day.</mj-text>
        <mj-button align="center" background-color="#C96A2E" color="#ffffff" border-radius="2px" font-family="Inter, Arial, sans-serif" font-size="14px" font-weight="600" letter-spacing="0.04em" text-transform="uppercase" inner-padding="16px 36px" href="https://www.naturesseed.com/collections/lawn-seed">
          Plant Before Summer
        </mj-button>
      </mj-column>
    </mj-section>
    <mj-section background-color="#2d6a4f" padding="28px 40px">
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">American Farm-Direct</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">Grown on U.S. farms</mj-text>
      </mj-column>
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">No Fillers</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">Pure, tested seed</mj-text>
      </mj-column>
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">Ships in 1 Business Day</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">Fast, reliable delivery</mj-text>
      </mj-column>
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">Satisfaction Guaranteed</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">We stand behind our seed</mj-text>
      </mj-column>
    </mj-section>
    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

- [ ] **Step 3: Write Pasture MJML**

Create `marketing/email-system/templates/may-spring-closing-pasture.mjml`. Same full structure as Step 2 with these content swaps:

- `mj-preview`: `"Pasture established now survives summer dormancy better. 12% off through May 25th."`
- Label: `"Last Call for Spring"`
- Headline italic span: `"before the ground dries out."`
- Body paragraph 1: `"Warm-season pasture grasses planted now will set root systems before peak summer heat. Cool-season grasses need to be in the ground within the next few weeks or you're looking at reseeding in the fall. Either way, the window matters."`
- Body paragraph 2: `"Use code <strong>SPRING12</strong> for 12% off through May 25th."`
- CTA button label: `"Plant Before Summer"`
- CTA href: `"https://www.naturesseed.com/collections/pasture-seed"`
- Bottom CTA headline: `"Roots established now, pasture ready by fall."`
- Bottom CTA sub: `"Farm-direct pasture seed, regionally tested.<br/>Ships in 1 business day."`

- [ ] **Step 4: Write Wildflower MJML**

Create `marketing/email-system/templates/may-spring-closing-wildflower.mjml`. Same structure, these swaps:

- `mj-preview`: `"Wildflower planted in May blooms by fall. 12% off through May 25th."`
- Label: `"Last Call for Spring"`
- Headline italic span: `"your fall bloom starts now."`
- Body paragraph 1: `"Wildflower seed planted in May gets 3–4 months of growth before it blooms in late summer and fall. Miss this window and you're planting in the heat, which means slower germination and sparser coverage. The math is simple: plant now, bloom in September."`
- Body paragraph 2: `"Use code <strong>SPRING12</strong> for 12% off through May 25th."`
- CTA href: `"https://www.naturesseed.com/collections/wildflower-seed"`
- CTA label: `"Plant Before Summer"`
- Bottom CTA headline: `"Plant now. Bloom in September."`
- Bottom CTA sub: `"Native wildflower mixes, farm-direct.<br/>Ships in 1 business day."`

- [ ] **Step 5: Write Specialty MJML**

Create `marketing/email-system/templates/may-spring-closing-specialty.mjml`. Same structure, these swaps:

- `mj-preview`: `"The install window for most specialty seed closes by June. 12% off through May 25th."`
- Label: `"Last Call for Spring"`
- Headline italic span: `"the install window is closing."`
- Body paragraph 1: `"Cover crops, food plots, and specialty mixes all have a narrow establishment window in spring. Get seed in the ground now and it has time to set before heat and drought stress arrive. Wait until June and you're fighting the calendar."`
- Body paragraph 2: `"Use code <strong>SPRING12</strong> for 12% off through May 25th."`
- CTA href: `"https://www.naturesseed.com/collections/specialty-seed"`
- CTA label: `"Plant Before Summer"`
- Bottom CTA headline: `"Don't let the season close on you."`
- Bottom CTA sub: `"Specialty seed, farm-direct.<br/>Ships in 1 business day."`

- [ ] **Step 6: Compile all four templates**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketing/email-system"
node build.js
```

Expected: four `[OK]` lines for `may-spring-closing-*.html`. All must be under 90KB. Fix any CLIP errors by trimming copy.

- [ ] **Step 7: Create four Klaviyo email templates**

```
Tool: klaviyo_create_email_template
model: "claude"
name: "May 2026 — Spring Closing Lawn"
html: <contents of dist/may-spring-closing-lawn.html>
```
Save ID as `TPL_SPRING_LAWN`.

```
Tool: klaviyo_create_email_template
model: "claude"
name: "May 2026 — Spring Closing Pasture"
html: <contents of dist/may-spring-closing-pasture.html>
```
Save ID as `TPL_SPRING_PASTURE`.

```
Tool: klaviyo_create_email_template
model: "claude"
name: "May 2026 — Spring Closing Wildflower"
html: <contents of dist/may-spring-closing-wildflower.html>
```
Save ID as `TPL_SPRING_WILDFLOWER`.

```
Tool: klaviyo_create_email_template
model: "claude"
name: "May 2026 — Spring Closing Specialty"
html: <contents of dist/may-spring-closing-specialty.html>
```
Save ID as `TPL_SPRING_SPECIALTY`.

- [ ] **Step 8: Assign templates to existing campaign messages**

```
Tool: klaviyo_assign_template_to_campaign_message
model: "claude"
campaign_message_id: <MSG_C5_LAWN>
template_id: <TPL_SPRING_LAWN>
```

```
Tool: klaviyo_assign_template_to_campaign_message
model: "claude"
campaign_message_id: <MSG_C5_PASTURE>
template_id: <TPL_SPRING_PASTURE>
```

```
Tool: klaviyo_assign_template_to_campaign_message
model: "claude"
campaign_message_id: <MSG_C5_WILDFLOWER>
template_id: <TPL_SPRING_WILDFLOWER>
```

```
Tool: klaviyo_assign_template_to_campaign_message
model: "claude"
campaign_message_id: <MSG_C5_SPECIALTY>
template_id: <TPL_SPRING_SPECIALTY>
```

- [ ] **Step 9: Verify one campaign (spot check)**

```
Tool: klaviyo_get_campaign
model: "claude"
campaign_id: "01KM13ZM4TQBKEPDNXAB4PJJ38"
```

Confirm: status = Scheduled, send time still 2026-05-20T23:00:00Z (17:00 MT), template now assigned.

- [ ] **Step 10: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add marketing/email-system/templates/may-spring-closing-*.mjml marketing/email-system/dist/may-spring-closing-*.html
git commit -m "feat: upgrade C5 Spring Activation to promo with SPRING12 (Campaign 2)"
```

---

## Task 5: Campaign 3 — Summer Arrives / Final Planting Window (May 28)

**Files:**
- Create: `marketing/email-system/templates/may-summer-arrives.mjml`
- Auto-compiled: `marketing/email-system/dist/may-summer-arrives.html`

- [ ] **Step 1: Write MJML template**

Create `marketing/email-system/templates/may-summer-arrives.mjml`:

```mjml
<mjml>
  <mj-head>
    <mj-preview>Summer heat arrives in most zones by mid-June. This is the final planting window.</mj-preview>
    <mj-font name="Noto Serif Display" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:ital,wght@0,600;0,700;1,700&family=Inter:wght@400;500;600&display=swap" />
    <mj-attributes>
      <mj-all font-family="Inter, Arial, sans-serif" />
      <mj-body width="620px" background-color="#f0ece4" />
    </mj-attributes>
    <mj-style>
      @media only screen and (max-width: 480px) {
        .product-col { display: block !important; width: 100% !important; }
      }
    </mj-style>
  </mj-head>
  <mj-body>
    <mj-section padding="0">
      <mj-column>
        <mj-text font-size="1px" color="#f0ece4" padding="0">
          &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
        </mj-text>
      </mj-column>
    </mj-section>
    <mj-include path="../components/header.mjml" />
    <mj-section background-color="#1b4332" padding="64px 48px 56px">
      <mj-column>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#d4a373" letter-spacing="0.14em" text-transform="uppercase" padding-bottom="20px">
          Summer 2026
        </mj-text>
        <mj-text align="center" font-family="'Noto Serif Display', Georgia, serif" font-size="46px" font-weight="700" color="#ffffff" line-height="1.10" letter-spacing="-0.01em" padding-bottom="20px">
          The planting<br/>
          <span style="font-style:italic;color:#a8d5b5;">window is closing.</span>
        </mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="16px" color="#a8d5b5" line-height="1.6" padding-bottom="32px">
          Summer heat arrives in most zones by mid-June.<br/>
          Here's what still makes sense to plant right now.
        </mj-text>
        <mj-button align="center" background-color="#C96A2E" color="#ffffff" border-radius="2px" font-family="Inter, Arial, sans-serif" font-size="14px" font-weight="600" letter-spacing="0.04em" text-transform="uppercase" inner-padding="16px 36px" href="https://www.naturesseed.com/">
          See What to Plant Now
        </mj-button>
        <mj-divider border-color="#d4a373" border-width="3px" width="48px" padding="40px 0 0" />
      </mj-column>
    </mj-section>
    <mj-section background-color="#ffffff" padding="48px 48px 0">
      <mj-column>
        <mj-text align="left" font-family="Inter, Arial, sans-serif" font-size="15px" color="#3d3d3d" line-height="1.75" padding-bottom="0">
          Most of the U.S. sees soil temperatures push past germination thresholds by mid-June. After that, establishment gets hard — slow germination, patchy coverage, and stressed seedlings going into their first summer. The good news: seed ordered today arrives before that cutoff.
        </mj-text>
      </mj-column>
    </mj-section>
    <mj-section background-color="#ffffff" padding="24px 48px 0">
      <mj-column>
        <mj-text align="left" font-family="Inter, Arial, sans-serif" font-size="15px" color="#3d3d3d" line-height="1.75" padding-bottom="0">
          Warm-season grasses and late-planting wildflower mixes are still a go. Cool-season lawn seed is borderline — check your zone before ordering. When in doubt, our team is one email away.
        </mj-text>
      </mj-column>
    </mj-section>
    <mj-section background-color="#ffffff" padding="0 48px 48px" border-top="1px solid #e8e4dc">
      <mj-column>
        <mj-text align="center" font-family="'Noto Serif Display', Georgia, serif" font-size="22px" font-weight="600" color="#1b4332" line-height="1.3" padding-bottom="12px" padding-top="40px">What still makes sense to plant.</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="14px" color="#6c757d" line-height="1.6" padding-bottom="24px">Farm-direct seed, regionally tested.<br/>Ships in 1 business day.</mj-text>
        <mj-button align="center" background-color="#C96A2E" color="#ffffff" border-radius="2px" font-family="Inter, Arial, sans-serif" font-size="14px" font-weight="600" letter-spacing="0.04em" text-transform="uppercase" inner-padding="16px 36px" href="https://www.naturesseed.com/">
          See What to Plant Now
        </mj-button>
      </mj-column>
    </mj-section>
    <mj-section background-color="#2d6a4f" padding="28px 40px">
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">American Farm-Direct</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">Grown on U.S. farms</mj-text>
      </mj-column>
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">No Fillers</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">Pure, tested seed</mj-text>
      </mj-column>
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">Ships in 1 Business Day</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">Fast, reliable delivery</mj-text>
      </mj-column>
      <mj-column padding="0 8px">
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" font-weight="600" color="#ffffff" letter-spacing="0.06em" text-transform="uppercase" padding-bottom="4px">Satisfaction Guaranteed</mj-text>
        <mj-text align="center" font-family="Inter, Arial, sans-serif" font-size="11px" color="#a8d5b5" line-height="1.4" padding="0">We stand behind our seed</mj-text>
      </mj-column>
    </mj-section>
    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

- [ ] **Step 2: Compile and verify**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/marketing/email-system"
node build.js
```

Expected: `[OK]    may-summer-arrives.html → XXkB`

- [ ] **Step 3: Create Klaviyo email template**

```
Tool: klaviyo_create_email_template
model: "claude"
name: "May 2026 — Summer Arrives / Final Planting Window"
html: <full contents of dist/may-summer-arrives.html>
```

Save returned ID as `TPL_SUMMER_ARRIVES`.

- [ ] **Step 4: Create Klaviyo campaign**

```
Tool: klaviyo_create_campaign
model: "claude"
data:
  type: "campaign"
  attributes:
    name: "Summer Arrives — Final Planting Window"
    audiences:
      included: ["VtKptn", "RAQTca", "RbGRqF", "WdpJti"]
    send_strategy:
      method: "static"
      options_static:
        datetime: "2026-05-28T16:00:00Z"
        is_local: false
    campaign-messages:
      data:
        - type: "campaign-message"
          attributes:
            channel: "email"
            content:
              subject: "The planting window closes in about two weeks"
              preview_text: "Summer heat arrives in most zones by mid-June. Here's what still makes sense to plant."
              from_email: "customercare@naturesseed.com"
              from_label: "Nature's Seed"
              reply_to_email: "customercare@naturesseed.com"
```

Save returned campaign ID as `CAMPAIGN_ID_SUMMER` and message ID as `MESSAGE_ID_SUMMER`.

- [ ] **Step 5: Assign template**

```
Tool: klaviyo_assign_template_to_campaign_message
model: "claude"
campaign_message_id: <MESSAGE_ID_SUMMER>
template_id: <TPL_SUMMER_ARRIVES>
```

- [ ] **Step 6: Verify campaign**

```
Tool: klaviyo_get_campaign
model: "claude"
campaign_id: <CAMPAIGN_ID_SUMMER>
```

Confirm: status = Draft, send time = 2026-05-28T16:00:00Z, all four segment IDs present, subject correct, no active offer code present in content.

- [ ] **Step 7: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add marketing/email-system/templates/may-summer-arrives.mjml marketing/email-system/dist/may-summer-arrives.html
git commit -m "feat: add Summer Arrives final planting window email (Campaign 3)"
```

---

## Self-Review Checklist

- Campaign 1 wildflower (Task 2): template + campaign + assignment ✓
- Campaign 1 lawn (Task 3): template + campaign + assignment ✓
- Campaign 2 all four upgrades (Task 4): message IDs retrieved, templates assigned to existing campaigns, not recreated ✓
- Campaign 3 (Task 5): template + campaign (no discount) + assignment ✓
- All CTA buttons: `#C96A2E` ✓
- Discount codes: MOM10 = 10% (under 15% cap), SPRING12 = 12% (under 15% cap), Campaign 3 = none ✓
- All MCP calls include `model: "claude"` ✓
- Campaign creation uses `2024-07-15` revision (passed via tool, not shown in args — confirm MCP server handles this) ✓
- Campaign 3 segment IDs: VtKptn, RAQTca, RbGRqF, WdpJti — all starred ✓
- Campaign 1 segment: RbH7na (E60D starred) ✓
- No same-day conflict: Campaign 1 sends May 9, Drought Email 2 sends May 8 ✓
- SPRING12 expires May 25, same day Memorial Day Sale starts — no overlap ✓
