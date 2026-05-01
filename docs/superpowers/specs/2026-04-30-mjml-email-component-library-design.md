# MJML Email Component Library — Design Spec
**Date:** 2026-04-30
**Author:** Claude (Klaviyo Email Agent)
**Status:** Approved

---

## Overview

Build a modular MJML-based email component library for Nature's Seed promotional campaigns. Replaces one-off hand-coded HTML templates with a reusable component system that compiles to battle-tested, responsive email HTML via an npm build pipeline.

**Primary use case:** Promotional campaigns (product spotlights, seasonal sales, category pushes). Component count and layout flex to match each campaign.

---

## Goals

- Eliminate from-scratch template work for each campaign
- Establish a consistent, high-quality visual design language (80% editorial, 20% conversion-focused)
- Produce Gmail-safe HTML output (<102KB per email)
- Preserve Liquid templating for Klaviyo personalization
- Enable non-technical iteration via local HTML mockups

---

## Design Direction

**Style:** Typography-led editorial. Large Noto Serif Display headlines, generous white space, brand color blocks carry the premium feel — not photography. Strong imagery is an enhancement, not a requirement.

**Color system:**
| Token | Hex | Role |
|---|---|---|
| Primary Dark | `#1b4332` | Hero backgrounds, footer |
| Primary Green | `#2d6a4f` | USP bar, brand accents |
| Accent Light | `#a8d5b5` | Hero subtext, footer text |
| Earth/Sand | `#d4a373` | Eyebrow labels, dividers |
| CTA Orange | `#C96A2E` | ALL buttons — never green |
| White | `#ffffff` | Card backgrounds |
| Off-white | `#f0ece4` | Page bg, placeholder fills |
| Divider | `#e8e4dc` | Borders, grid gaps |

**Typography:**
- Headlines: Noto Serif Display, 600–700 weight, tight line-height (1.10)
- Eyebrows/labels: Inter, 10–11px, 600 weight, 0.12em letter-spacing, uppercase
- Body: Inter, 13–16px, 400–500 weight, 1.5–1.6 line-height
- CTAs: Inter, 12–14px, 600 weight, 0.04–0.05em letter-spacing, uppercase

**Max width:** 620px. Table-based layout (MJML output). 2px gaps between grid cells (creates a subtle ruled effect).

---

## Architecture

```
marketing/email-system/
├── package.json              # mjml dependency + build scripts
├── build.js                  # compiles templates/ → dist/
├── components/               # reusable MJML partials
│   ├── header.mjml
│   ├── hero-editorial.mjml   # color block + serif type (default)
│   ├── hero-image.mjml       # with background image
│   ├── product-single.mjml   # full-width product spotlight
│   ├── product-grid-2.mjml   # 2-column grid
│   ├── product-grid-3.mjml   # 3-column grid
│   ├── usps-bar.mjml         # 4-badge trust bar
│   ├── cta-block.mjml        # standalone CTA section
│   └── footer.mjml
├── templates/                # assembled campaign templates
│   └── promo-editorial.mjml  # first template (hero + grid-2 + feature + usps + cta + footer)
├── dist/                     # compiled HTML output → paste into Klaviyo
└── mockup-promo.html         # approved visual reference
```

---

## Components

### header.mjml
- White background, 24px vertical padding
- Nature's Seed logo (text-based: "Nature's" + "Seed" in dark green)
- 1px bottom border in `#e8e4dc`

### hero-editorial.mjml
- `#1b4332` background, 64px top / 56px bottom padding
- Eyebrow: Inter 11px, `#d4a373`, uppercase, 0.14em tracking
- H1: Noto Serif Display 46px, white, 1.10 line-height. `<em>` in `#a8d5b5`
- Subhead: Inter 16px, `#a8d5b5`, max-width 380px
- CTA button: `#C96A2E`, 16px/36px padding, 2px border-radius
- Accent bar: 48×3px `#d4a373` divider at bottom

### hero-image.mjml
- Same structure, adds full-width background image support
- Text overlaid on image with semi-transparent dark overlay for legibility

### product-single.mjml
- `#f8f6f2` background, 36px padding
- Horizontal layout: 140px square image left, content right
- Eyebrow + serif name (22px) + description + CTA button

### product-grid-2.mjml
- 2-column, 2px gap (creates ruled grid effect)
- Per card: square image → category eyebrow → serif name → description → CTA
- Scales gracefully to single column on mobile

### product-grid-3.mjml
- Same pattern, 3 columns
- Smaller product names (16px) and tighter padding to fit

### usps-bar.mjml
- `#2d6a4f` background, 28px padding
- 4 badges: Free Shipping, Satisfaction Guaranteed, Family Owned, Expert Support
- Badge icon: 28px circle placeholder (swap for SVG icon)
- Title: Inter 11px white uppercase; Sub: Inter 11px `#a8d5b5`

### cta-block.mjml
- White background, 44px padding, centered
- Serif H3 (22px) + body copy (14px, max 340px) + outline button
- Outline button: 2px solid `#2d6a4f`, green text — used for soft CTAs ("Ask a Seed Expert")

### footer.mjml
- `#1b4332` background, 36px padding
- Logo → nav links → address → unsubscribe
- All text in `#a8d5b5` / `#52b788`
- Always includes: customercare@naturesseed.com, 801-531-1456, unsubscribe link

---

## Build System

### package.json scripts
```json
{
  "scripts": {
    "build": "node build.js",
    "dev": "node build.js --watch"
  },
  "dependencies": {
    "mjml": "^4.15.0"
  }
}
```

### build.js behavior
- Reads all `.mjml` files in `templates/`
- Compiles each to HTML via MJML
- Writes output to `dist/<template-name>.html`
- Logs file size — warns if >90KB (approaching Gmail clip threshold)
- `--watch` flag: watches `components/` and `templates/` for changes, recompiles on save

---

## Liquid Templating

MJML compiles to HTML; Liquid tags pass through untouched. Standard personalization patterns remain:

```liquid
{{ person.first_name | default: 'there' }}
{% if person|lookup: 'last_product_category' == 'lawn' %}...{% endif %}
```

Liquid goes inside MJML text/button content — not in MJML attributes.

---

## Gmail Safety

- Target output: <90KB compiled HTML (warn threshold)
- Hard limit: <102KB (Gmail clips above this)
- Max 3–4 product blocks per email
- No base64-encoded images in HTML — always use hosted URLs
- Test with: `wc -c dist/template.html`

---

## First Deliverable

Build and validate `promo-editorial.mjml` — the full promotional template:

1. header
2. hero-editorial (Spring 2026 messaging)
3. section label
4. product-grid-2
5. product-single (featured/staff pick)
6. usps-bar
7. cta-block ("Ask a Seed Expert")
8. footer

Visual reference: `marketing/email-system/mockup-promo.html` (approved 2026-04-30)

---

## Out of Scope (v1)

- Flow/nurture email templates (welcome series, win-back) — Phase 2
- Dark mode support
- AMP for email
- Automated Klaviyo upload (manual paste into template editor for now)
