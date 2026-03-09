# Nature's Seed — Design System

> Single source of truth for visual design, tokens, components, and conventions.
> Recreate this system in any project by following this document top to bottom.

---

## Table of Contents

1. [Brand Identity](#1-brand-identity)
2. [Color Tokens](#2-color-tokens)
3. [Typography](#3-typography)
4. [Spacing Scale](#4-spacing-scale)
5. [Breakpoints & Layout](#5-breakpoints--layout)
6. [Borders, Radius & Shadows](#6-borders-radius--shadows)
7. [Transitions & Motion](#7-transitions--motion)
8. [Z-Index Scale](#8-z-index-scale)
9. [CSS Architecture](#9-css-architecture)
10. [Components — Buttons](#10-components--buttons)
11. [Components — Badges](#11-components--badges)
12. [Components — Cards](#12-components--cards)
13. [Components — Forms](#13-components--forms)
14. [Components — Accordion](#14-components--accordion)
15. [Utility Classes](#15-utility-classes)
16. [Page Layout Patterns](#16-page-layout-patterns)
17. [Brand Voice & Copy](#17-brand-voice--copy)
18. [Performance Rules](#18-performance-rules)

---

## 1. Brand Identity

**Company:** Nature's Seed (The NativeSeed Group)
**Positioning:** North America's only vertically-integrated seed company. Farm-direct, expert-blended, independently tested.
**Audience:** Dual — homeowners (lawn/garden) AND serious growers (farmers, ranchers, land managers).
**Brand feeling:** Premium but approachable. Expert neighbor, not a corporation.

### Logo
- Primary: horizontal lockup, forest green on white
- Inverse: white on green background
- Never stretch, recolor, or place on busy backgrounds
- Minimum clear space: equal to the height of the "N" in Nature's

### Core Rule: Green = Brand Trust. Orange = Action/Conversion. Never swap them.

---

## 2. Color Tokens

### Brand Greens
| Token | Hex | Usage |
|---|---|---|
| `$color-primary` | `#2d6a4f` | Primary buttons (non-CTA), links, icons, trust signals |
| `$color-primary-dark` | `#1b4332` | Hover states, dark hero backgrounds |
| `$color-primary-light` | `#40916c` | Accents, left-border callouts, secondary elements |
| `$color-secondary` | `#52b788` | Highlights, "New" badges, vibrant accents |
| `$color-secondary-dark` | `#3a8d6e` | Secondary hover |

### CTA (Orange — conversion only)
| Token | Hex | Usage |
|---|---|---|
| `$color-cta` | `#C96A2E` | ALL add-to-cart / buy / primary conversion buttons |
| `$color-cta-hover` | `#A85824` | CTA button hover state |

> WCAG AA: CTA orange achieves 4.5:1 contrast on white. Never use it decoratively.

### Accent
| Token | Hex | Usage |
|---|---|---|
| `$color-accent` | `#d4a373` | Warm earth/sand — premium badges, seasonal accents |
| `$color-accent-light` | `#e9c89b` | Lighter accent tint |

### Neutrals (full gray scale)
| Token | Hex | Usage |
|---|---|---|
| `$color-white` | `#ffffff` | Page backgrounds, card backgrounds |
| `$color-off-white` | `#f8f9fa` | Alternate section backgrounds |
| `$color-gray-50` | `#f1f3f5` | Hover backgrounds, table header |
| `$color-gray-100` | `#e9ecef` | Light borders, badge default bg |
| `$color-gray-200` | `#dee2e6` | Default border color |
| `$color-gray-300` | `#ced4da` | Input hover borders |
| `$color-gray-400` | `#adb5bd` | Muted icons, chevrons |
| `$color-gray-500` | `#868e96` | Placeholder text |
| `$color-gray-600` | `#6c757d` | Secondary text alt |
| `$color-gray-700` | `#495057` | Body secondary text (WCAG AA: 7:1 on white) |
| `$color-gray-800` | `#343a40` | Dark text on light bg |
| `$color-gray-900` | `#212529` | Primary text color |
| `$color-black` | `#000000` | Overlays only |

### Semantic
| Token | Hex | Usage |
|---|---|---|
| `$color-success` | `#2d6a4f` | Success states, "FREE" labels (same as primary green) |
| `$color-warning` | `#e9c46a` | Warning states |
| `$color-error` | `#d62828` | Error states, validation, sale badges |
| `$color-info` | `#457b9d` | Info messages |

### Semantic Assignments
```scss
// Backgrounds
$color-bg-body:    $color-white;
$color-bg-section: $color-off-white;   // Use for alternating sections
$color-bg-card:    $color-white;

// Text
$color-text-primary:   $color-gray-900;   // All headings, labels
$color-text-secondary: $color-gray-700;   // Body paragraphs
$color-text-muted:     $color-gray-400;   // Placeholders, captions, icons
$color-text-inverse:   $color-white;      // Text on dark backgrounds

// Borders
$color-border:         $color-gray-200;   // Default borders
$color-border-light:   $color-gray-100;   // Subtle separators
```

---

## 3. Typography

### Fonts
| Role | Family | Fallback | Weights Used |
|---|---|---|---|
| Body | Inter | `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif` | 400, 500, 600 |
| Headings | Noto Serif Display | `Georgia, 'Times New Roman', serif` | 600, 700 |
| Code | JetBrains Mono | `'Fira Code', 'Consolas', monospace` | 400 |

**Rule:** Serif headings create a premium, rooted brand feel. Sans-serif body ensures readability at all sizes.

### Font Size Scale
| Token | rem | px | Usage |
|---|---|---|---|
| `$font-size-xs` | `0.75rem` | 12px | Captions, badge labels, fine print |
| `$font-size-sm` | `0.875rem` | 14px | Secondary labels, card metadata, form hints |
| `$font-size-base` | `1rem` | 16px | Body copy baseline |
| `$font-size-md` | `1.125rem` | 18px | Lead paragraphs, prominent body |
| `$font-size-lg` | `1.25rem` | 20px | h3 mobile, sub-headings |
| `$font-size-xl` | `1.5rem` | 24px | h2 mobile, section leads |
| `$font-size-2xl` | `1.875rem` | 30px | h1 mobile, page titles |
| `$font-size-3xl` | `2.25rem` | 36px | h1 tablet |
| `$font-size-4xl` | `3rem` | 48px | h1 desktop, hero titles |
| `$font-size-5xl` | `3.75rem` | 60px | Extra-large hero display |

### Font Weights
| Token | Value |
|---|---|
| `$font-weight-light` | 300 |
| `$font-weight-regular` | 400 |
| `$font-weight-medium` | 500 |
| `$font-weight-semibold` | 600 |
| `$font-weight-bold` | 700 |
| `$font-weight-black` | 900 |

### Line Heights
| Token | Value | Usage |
|---|---|---|
| `$line-height-tight` | 1.2 | Headings, large display text |
| `$line-height-base` | 1.6 | Body paragraphs |
| `$line-height-relaxed` | 1.8 | Long-form content, answers, policy text |

### Letter Spacing
| Token | Value | Usage |
|---|---|---|
| `$letter-spacing-tight` | `-0.025em` | Large headings (applied via `heading` mixin) |
| `$letter-spacing-normal` | `0` | Default |
| `$letter-spacing-wide` | `0.025em` | Badge labels |
| `$letter-spacing-wider` | `0.05em` | h6, uppercase labels, table headers |

### Heading Scale (responsive)
| Element | Mobile | Tablet (`md`) | Desktop (`xl`) |
|---|---|---|---|
| h1 | 30px (2xl) | 36px (3xl) | 48px (4xl) |
| h2 | 24px (xl) | 30px (2xl) | 36px (3xl) |
| h3 | 20px (lg) | 24px (xl) | — |
| h4 | 18px (md) | — | — |
| h5 | 16px (base) | — | — |
| h6 | 14px (sm), uppercase | — | — |

All headings use `font-family: Noto Serif Display`, `line-height: 1.2`, `letter-spacing: -0.025em`.

### Base Document Styles
```scss
body {
  font-family: Inter, ...sans-serif fallback;
  font-size: 1rem;         // 16px
  font-weight: 400;
  line-height: 1.6;
  color: #212529;          // $color-text-primary
  background: #ffffff;
  -webkit-font-smoothing: antialiased;
}
```

---

## 4. Spacing Scale

Based on a 4px base unit. All spacing uses `rem`.

| Token | rem | px |
|---|---|---|
| `$spacing-0` | `0` | 0 |
| `$spacing-1` | `0.25rem` | 4px |
| `$spacing-2` | `0.5rem` | 8px |
| `$spacing-3` | `0.75rem` | 12px |
| `$spacing-4` | `1rem` | 16px |
| `$spacing-5` | `1.25rem` | 20px |
| `$spacing-6` | `1.5rem` | 24px |
| `$spacing-8` | `2rem` | 32px |
| `$spacing-10` | `2.5rem` | 40px |
| `$spacing-12` | `3rem` | 48px |
| `$spacing-16` | `4rem` | 64px |
| `$spacing-20` | `5rem` | 80px |
| `$spacing-24` | `6rem` | 96px |
| `$spacing-32` | `8rem` | 128px |

### Section Vertical Padding
| Breakpoint | Top + Bottom padding |
|---|---|
| Mobile (default) | 48px (`$spacing-12`) |
| Tablet (`md` 768px+) | 64px (`$spacing-16`) |
| Desktop (`xl` 1200px+) | 80px (`$spacing-20`) |

Apply with the `section-padding` mixin or `.section` utility class.

---

## 5. Breakpoints & Layout

### Breakpoints (mobile-first, min-width)
| Token | px | Mixin |
|---|---|---|
| `$breakpoint-xs` | 0 | — (default) |
| `$breakpoint-sm` | 576px | `@include sm` |
| `$breakpoint-md` | 768px | `@include md` |
| `$breakpoint-lg` | 992px | `@include lg` |
| `$breakpoint-xl` | 1200px | `@include xl` |
| `$breakpoint-xxl` | 1400px | `@include xxl` |

Max-width helpers (use sparingly — prefer mobile-first):
`@include max-sm` / `@include max-md` / `@include max-lg`

### Container Widths
| Token | Max-width | Context |
|---|---|---|
| `$container-xxl` | 1320px | Default site container |
| `$container-xl` | 1140px | — |
| `$container-lg` | 960px | Narrow container (`container-narrow`) |

**Container padding:** 16px on mobile, 24px on md+.

Use `.container` for full-width pages, `.container-narrow` for content-heavy pages (policy, FAQ, etc.).

### Grid System
12-column grid, 24px gutter (16px mobile).

**Product grid pattern** (auto-responsive):
- Mobile: 1 column
- `sm` (576px+): 2 columns
- `lg` (992px+): 3 columns
- `xl` (1200px+): 4 columns

```scss
@include product-grid;  // Applies above breakpoints automatically
```

### Header Heights
| Breakpoint | Height |
|---|---|
| Mobile | 60px (`$header-height-mobile`) |
| Desktop (`md`+) | 72px (`$header-height`) |

Announcement bar adds 40px above header (`$announcement-bar-height`).
`scroll-padding-top` is set to match header height to prevent anchors hiding under sticky nav.

---

## 6. Borders, Radius & Shadows

### Borders
| Token | Value |
|---|---|
| `$border-width` | `1px` |
| `$color-border` | `#dee2e6` (gray-200) — default |
| `$color-border-light` | `#e9ecef` (gray-100) — subtle separators |

### Border Radius
| Token | Value | Usage |
|---|---|---|
| `$border-radius-sm` | `4px` | Code blocks, checkboxes, small chips |
| `$border-radius` | `8px` | Inputs, default buttons |
| `$border-radius-md` | `12px` | Cards, modals, accordions, sections |
| `$border-radius-lg` | `16px` | Large cards, CTA strips |
| `$border-radius-xl` | `24px` | Hero banners, overlay panels |
| `$border-radius-full` | `9999px` | Pills, badges, circular icons, avatar rings |

### Shadows
| Token | Value | Usage |
|---|---|---|
| `$shadow-xs` | `0 1px 2px rgba(0,0,0,.05)` | Minimal lift |
| `$shadow-sm` | `0 1px 3px rgba(0,0,0,.1), 0 1px 2px rgba(0,0,0,.06)` | Subtle depth |
| `$shadow-md` | `0 4px 6px -1px rgba(0,0,0,.1), 0 2px 4px -1px rgba(0,0,0,.06)` | Dropdowns, small modals |
| `$shadow-lg` | `0 10px 15px -3px rgba(0,0,0,.1), 0 4px 6px -2px rgba(0,0,0,.05)` | Large modals, drawers |
| `$shadow-xl` | `0 20px 25px -5px rgba(0,0,0,.1), 0 10px 10px -5px rgba(0,0,0,.04)` | Full-screen overlays |
| `$shadow-card` | `0 2px 8px rgba(0,0,0,.08)` | Default card resting state |
| `$shadow-card-hover` | `0 8px 24px rgba(0,0,0,.12)` | Card hover elevation |

Card hover pattern: `box-shadow: $shadow-card-hover; transform: translateY(-2px);`

---

## 7. Transitions & Motion

| Token | Value | Usage |
|---|---|---|
| `$transition-fast` | `150ms ease` | Hover color changes, small state changes |
| `$transition-base` | `250ms ease` | Standard interactions (card hover, accordion) |
| `$transition-slow` | `350ms ease` | Drawer slides, panel reveals |
| `$transition-spring` | `300ms cubic-bezier(0.34, 1.56, 0.64, 1)` | Springy pop-in effects (modals, toasts) |

**Reduced motion:** Always wrap animations in `@media (prefers-reduced-motion: reduce)` and disable. The reset already sets `animation-duration: 0.01ms` and `transition-duration: 0.01ms` globally when reduced motion is preferred.

---

## 8. Z-Index Scale

| Token | Value | Usage |
|---|---|---|
| `$z-dropdown` | 100 | Dropdown menus |
| `$z-sticky` | 200 | Sticky elements (filter bar) |
| `$z-fixed` | 300 | Fixed nav header |
| `$z-overlay` | 400 | Overlay backgrounds |
| `$z-modal` | 500 | Modal containers |
| `$z-popover` | 600 | Popovers / tooltips trigger layers |
| `$z-tooltip` | 700 | Tooltips |
| `$z-toast` | 800 | Toast notifications |

---

## 9. CSS Architecture

### Tech Stack
- **Preprocessor:** SCSS via Vite 6
- **Output:** `dist/css/main.css` + `dist/css/woocommerce.css`
- **Naming convention:** BEM (`block__element--modifier`)
- **Approach:** Mobile-first, component-scoped, token-driven

### File Structure
```
assets/scss/
├── main.scss              # Root import manifest
├── base/
│   ├── _variables.scss    # All design tokens (source of truth)
│   ├── _mixins.scss       # Responsive, layout, typography, utility mixins
│   ├── _reset.scss        # Modern CSS reset
│   ├── _typography.scss   # Heading + body type styles
│   └── _utilities.scss    # Utility classes (.container, .d-flex, etc.)
├── components/
│   ├── _buttons.scss
│   ├── _badges.scss
│   ├── _cards.scss
│   ├── _forms.scss
│   ├── _accordion.scss
│   ├── _modal.scss
│   ├── _pagination.scss
│   └── ...
└── pages/
    ├── _home.scss
    ├── _product.scss
    ├── _category.scss
    ├── _shipping-policy.scss
    └── ...
```

### How to Use Tokens
Every component file starts with:
```scss
@use '../base/variables' as *;
@use '../base/mixins' as *;
```
This imports all `$tokens` and `@mixin` helpers into scope.

### Core Mixins Reference

**Breakpoints:**
```scss
@include sm  // 576px+
@include md  // 768px+
@include lg  // 992px+
@include xl  // 1200px+
@include xxl // 1400px+
```

**Layout:**
```scss
@include container;         // Max 1320px, auto margins, responsive padding
@include container-narrow;  // Max 960px
@include section-padding;   // Responsive vertical padding (48/64/80px)
@include grid($columns, $gap);
@include product-grid;      // 1→2→3→4 col responsive product grid
```

**Flexbox shortcuts:**
```scss
@include flex-center;   // align + justify: center
@include flex-between;  // align: center, justify: space-between
@include flex-start;    // align: center, justify: flex-start
```

**Typography:**
```scss
@include heading($size, $weight);   // Serif font, tight line-height, negative tracking
@include body-text($size);          // Sans-serif, regular weight, base line-height
@include text-truncate;             // Single-line ellipsis overflow
@include text-clamp($lines);        // Multi-line ellipsis (-webkit-line-clamp)
```

**Buttons:**
```scss
@include button-base;       // Shared structure (flex, padding, font, border, transition)
@include button-primary;    // CTA orange fill
@include button-secondary;  // Green outline → fill on hover
@include button-ghost;      // Transparent, gray border
```

**Other:**
```scss
@include card;              // White bg, light border, radius-md, card hover effect
@include aspect-ratio($w, $h);  // Ratio wrapper with cover img
@include responsive-image;      // display:block, width:100%, object-fit:cover
@include visually-hidden;       // Accessible SR-only (not display:none)
@include focus-ring;            // :focus-visible outline with $color-primary
@include overlay($opacity);     // ::after pseudo overlay
@include scrollbar-hidden;      // Hide scrollbar cross-browser
@include backdrop-blur($blur);  // backdrop-filter: blur()
```

---

## 10. Components — Buttons

### HTML Pattern
```html
<a class="btn btn--primary btn--lg" href="#">Shop Lawn Seed</a>
<button class="btn btn--secondary">Learn More</button>
<button class="btn btn--ghost btn--sm">Cancel</button>
<button class="btn btn--icon btn--lg"><svg>...</svg></button>
```

### Variants
| Class | Background | Text | Border | Usage |
|---|---|---|---|---|
| `.btn` (base) | Transparent | Primary text | Gray-200 | Default ghost |
| `.btn--primary` | `#2d6a4f` green | White | Green | Brand actions (non-conversion) |
| `.btn--secondary` | Transparent | Green | Green | Outline → fills on hover |
| `.btn--ghost` | Transparent | Primary text | Gray-200 | Low-emphasis actions |
| `.btn--accent` | `#d4a373` sand | White | Sand | Premium/seasonal highlights |
| `.btn--danger` | `#d62828` red | White | Red | Destructive actions |
| `.btn--link` | Transparent | Green | None | Inline text links |

> **Note:** For WooCommerce add-to-cart buttons, use `$color-cta` (#C96A2E orange) — these are styled at the WC level, not via `.btn--primary`.

### Sizes
| Class | Padding | Font size |
|---|---|---|
| `.btn--sm` | 8px 16px | 12px |
| (default) | 12px 24px | 14px |
| `.btn--lg` | 16px 32px | 16px |
| `.btn--xl` | 20px 40px | 18px |

### Modifiers
- `.btn--block` — Full width
- `.btn--rounded` — Pill shape (radius-full)
- `.btn--square` — No border-radius
- `.btn--icon` — Square icon-only button (40×40px default)
- `.btn--loading` — Loading spinner (hides text, shows spinner via ::after)

### Button Group
```html
<div class="btn-group">
  <button class="btn btn--primary">Save</button>
  <button class="btn btn--ghost">Cancel</button>
</div>

<div class="btn-group btn-group--attached">
  <button class="btn">Left</button>
  <button class="btn">Middle</button>
  <button class="btn">Right</button>
</div>
```

---

## 11. Components — Badges

### HTML Pattern
```html
<span class="badge badge--highlight">Best Seller</span>
<span class="badge badge--new">New Arrival</span>
<span class="badge badge--secondary">Staff Pick</span>
<span class="badge badge--sale">Sale</span>
```

### Variants
| Class | Background | Text | Usage |
|---|---|---|---|
| `.badge` (base) | Gray-100 | Primary text | Generic label |
| `.badge--highlight` | `#d4a373` sand | White | Best Seller, featured |
| `.badge--primary` | `#2d6a4f` green | White | Organic, certified |
| `.badge--secondary` | Green 10% opacity | Green | Staff Pick, curated |
| `.badge--success` | Green 10% opacity | Green | In Stock, Available |
| `.badge--warning` | Yellow 15% opacity | Dark yellow | Low Stock |
| `.badge--error` / `--sale` | `#d62828` red | White | Sale, Discontinued |
| `.badge--new` | `#52b788` light green | White | New Arrival |
| `.badge--organic` | `#2d6a4f` green | White | Organic certified |
| `.badge--info` | Blue 10% opacity | Blue | Informational |
| `.badge--outline` | Transparent | Current color | Outline style |

### Sizes
| Class | Padding | Font size |
|---|---|---|
| `.badge--sm` | 2px 8px | 10px |
| (default) | 4px 12px | 12px |
| `.badge--lg` | 8px 16px | 14px |

Base styles: `border-radius-full`, uppercase, `letter-spacing: 0.025em`, `font-weight: 600`.

---

## 12. Components — Cards

### HTML Pattern
```html
<div class="card">
  <div class="card__image">
    <img src="..." alt="..." loading="lazy" width="400" height="300">
  </div>
  <div class="card__body">
    <h3 class="card__title"><a href="#">Tall Fescue Blend</a></h3>
    <p class="card__text">Premium cool-season lawn seed, expertly blended for your region.</p>
    <div class="card__meta">
      <span>5 lbs — covers 2,000 sq ft</span>
    </div>
  </div>
  <div class="card__footer">
    <span>$29.99</span>
    <button class="btn btn--sm btn--primary">Add to Cart</button>
  </div>
</div>
```

### Variants
| Class | Effect |
|---|---|
| `.card` (base) | White bg, light border, radius-md, hover: shadow + lift |
| `.card--horizontal` | Side-by-side image+body on `md`+ |
| `.card--flat` | No shadow or border |
| `.card--compact` | Reduced padding (`$spacing-3`) |

### Card hover behavior
```scss
box-shadow: 0 8px 24px rgba(0,0,0,.12);
transform: translateY(-2px);
transition: 250ms ease;
```

---

## 13. Components — Forms

### HTML Pattern
```html
<div class="form-group">
  <label class="form-label" for="email">
    Email <span class="required">*</span>
  </label>
  <input class="form-input" type="email" id="email" placeholder="you@example.com">
  <span class="form-hint">We'll never share your email.</span>
</div>

<div class="form-check">
  <input class="form-check-input" type="checkbox" id="agree">
  <label class="form-check-label" for="agree">I agree to the terms</label>
</div>
```

### Form Elements
| Class | Element | Notes |
|---|---|---|
| `.form-group` | Wrapper | 20px bottom margin |
| `.form-label` | `<label>` | 14px, medium weight |
| `.form-input` | `<input>` | Full width, 8px radius |
| `.form-select` | `<select>` | Custom chevron arrow via bg-image |
| `.form-textarea` | `<textarea>` | Min 120px height |
| `.form-check` | Checkbox/radio wrapper | Flex layout |
| `.form-check-input` | Checkbox/radio | Custom styled, green when checked |
| `.form-check-label` | Checkbox/radio label | 14px |
| `.form-error` | Error message | 12px, `$color-error` red |
| `.form-hint` | Help text | 12px, muted gray |

### Sizes
- `.form-input--sm` — 8px 12px padding, 14px font
- Default — 12px 16px padding, 16px font
- `.form-input--lg` — 16px 20px padding, 18px font

### States
- `:focus` — Green border + `rgba(#2d6a4f, 0.1)` box shadow
- `.is-invalid` / `.form-input--error` — Red border + red shadow on focus
- `.is-valid` / `.form-input--success` — Green border
- `:disabled` — Gray-50 background, muted text, `cursor: not-allowed`

### Native elements automatically styled
`input[type="text/email/password/search/tel/url/number"]`, `select`, `textarea` all inherit form-field styles without needing a class.

---

## 14. Components — Accordion

### HTML Pattern (native `<details>` — used in policy pages)
```html
<div class="shipping-policy__accordion">
  <details class="shipping-policy__item" open>
    <summary class="shipping-policy__question">
      <span>How long does processing take?</span>
      <svg class="shipping-policy__chevron" ...><polyline points="6 9 12 15 18 9"></polyline></svg>
    </summary>
    <div class="shipping-policy__answer">
      <p>Orders ship within 3–5 business days...</p>
    </div>
  </details>
</div>
```

### JS-driven Accordion (reusable `.accordion` component)
```html
<div class="accordion accordion--faq">
  <div class="accordion__item">
    <button class="accordion__trigger" aria-expanded="false" aria-controls="panel-1">
      <span>Question text here?</span>
      <span class="accordion__icon">
        <svg><!-- chevron --></svg>
      </span>
    </button>
    <div class="accordion__panel" id="panel-1" aria-hidden="true">
      <div class="accordion__content">
        <p>Answer content...</p>
      </div>
    </div>
  </div>
</div>
```

### Variants
| Class | Effect |
|---|---|
| `.accordion` (base) | Border, radius-md, overflow hidden |
| `.accordion--borderless` | No outer border |
| `.accordion--faq` | Wider padding, larger font for FAQ pages |

### Chevron rotation
When open: `transform: rotate(180deg)` on `.accordion__icon` or `.shipping-policy__chevron`.

---

## 15. Utility Classes

### Layout
```html
<div class="container">...</div>         <!-- Max 1320px, centered -->
<div class="container-narrow">...</div>  <!-- Max 960px, centered -->
<section class="section">...</section>   <!-- Section padding -->
<section class="section section--alt">   <!-- Alt bg (#f8f9fa) + padding -->
```

### Display
`.d-none` `.d-block` `.d-flex` `.d-grid` `.d-inline` `.d-inline-block` `.d-inline-flex`
Responsive: `.d-md-none` `.d-md-block` `.d-md-flex` `.d-lg-none` `.d-lg-block` `.d-lg-flex`
`.mobile-only` (hides on md+) / `.desktop-only` (hides on mobile)

### Flexbox
`.flex-center` `.flex-between` `.flex-start` `.flex-col` `.flex-wrap` `.flex-1` `.flex-shrink-0`
`.items-start` `.items-end` `.justify-end`
`.gap-1` `.gap-2` `.gap-3` `.gap-4` `.gap-6` `.gap-8`

### Spacing
`.m-0` `.mt-0` `.mb-0` `.mb-2` `.mb-4` `.mb-6` `.mb-8` `.mt-4` `.mt-8` `.mx-auto`
`.p-0` `.p-2` `.p-4` `.p-6` `.px-4` `.py-4`

### Text
`.text-left` `.text-center` `.text-right`
`.text-uppercase` `.text-capitalize`
`.font-medium` `.font-semibold` `.font-bold`
`.text-truncate` (single-line ellipsis)
`.text-muted` (gray-400) `.text-secondary` (gray-700) `.text-small` (14px) `.text-xs` (12px)
`.text-primary` (green) `.text-success` `.text-error` `.text-warning`

### Backgrounds
`.bg-primary` `.bg-white` `.bg-off-white` `.bg-gray-50`

### Borders
`.border` `.border-top` `.border-bottom`
`.rounded` `.rounded-md` `.rounded-lg` `.rounded-full`

### Shadows
`.shadow-sm` `.shadow-md` `.shadow-lg`

### Visibility / Accessibility
`.sr-only` — visually hidden but accessible to screen readers (use for icon button labels, etc.)
`.gsnature-sr-only` — `display:none !important` (DOM hidden)

### Misc
`.w-full` `.h-full` `.min-h-screen`
`.relative` `.absolute` `.sticky`
`.overflow-hidden` `.overflow-x-auto` `.overflow-y-auto`
`.cursor-pointer`
`.img-cover` — `object-fit: cover; width/height: 100%`

---

## 16. Page Layout Patterns

### Alternating Sections
```html
<section class="section">        <!-- White bg -->
<section class="section section--alt">  <!-- Off-white bg -->
<section class="section">        <!-- White bg -->
```

### Content + Sidebar (Category / Shop)
```scss
display: grid;
grid-template-columns: $sidebar-width 1fr;  // 280px sidebar + fluid content
gap: $spacing-8;
```
Mobile: sidebar collapses to drawer/panel.

### Hero Banner
- Full-width background image with overlay
- Text centered or left-aligned, white on dark overlay
- CTA: `btn--primary` (green) OR two-button group: primary + ghost
- Headline: Noto Serif Display, 4xl desktop, 2xl mobile
- `@include overlay(0.5)` for background darkening

### Product Card Grid
Apply `@include product-grid` to the grid container. Cards use `.card` component.

### CTA Strip (on dark bg)
```html
<section class="[block]__cta">          <!-- bg: $color-primary -->
  <div class="[block]__cta-inner">      <!-- max-width: 560px, centered -->
    <h2>Still have questions?</h2>
    <p>Supporting text here.</p>
    <div class="[block]__cta-actions">  <!-- flex, centers buttons -->
      <a class="btn btn--primary">...</a>  <!-- Overridden: white bg, green text -->
      <a class="btn btn--outline">...</a>  <!-- Overridden: white text, white border -->
    </div>
  </div>
</section>
```
On dark green backgrounds, invert button colors: white-filled primary, white-bordered outline.

### Rate/Pricing Table
```html
<div class="[block]__rate-table">          <!-- border, radius-md, max-width: 480px -->
  <div class="... --header">              <!-- gray-50 bg, uppercase, muted text -->
  <div class="... --highlight">           <!-- green 6% tint bg, medium weight -->
  <div class="...">                       <!-- plain row, alternating with default -->
  <div class="... --note">               <!-- off-white bg, italic, muted, centered -->
</div>
```

### Highlight Strip (Info Cards)
4-column grid (2×2 on mobile, 4 across on md+) of icon cards:
```html
<div class="grid" style="grid-template-columns: 1fr 1fr">
  <div class="card">
    <div class="icon-circle"><!-- 56×56, green 8% bg, green icon --></div>
    <h3>Title</h3>
    <p>Supporting text</p>
  </div>
</div>
```

---

## 17. Brand Voice & Copy

### Tone
Professional + Approachable. Expert neighbor, not a lecturer.
- Short, punchy sentences
- "We" and "you" — personal and inclusive
- Specific over vague ("3–5 business days", not "fast shipping")
- Lead with customer outcome, not product features
- 8th grade reading level

### Heading Formula
> "[Aspirational Outcome] starts with Seed you can trust."

Examples:
- "Beautiful Lawns start with Seed you can trust."
- "Healthy Pastures start with Seed you can trust."

### Description Formula
> [Specific benefit] + [regional/quality proof] + [action close]

Example: "Expertly blended for lush, durable growth in every region of the U.S."

### CTA Copy Rules
Specific and low-friction. Never generic.
| Instead of | Write |
|---|---|
| "Contact Us" | "Ask a Seed Expert" |
| "Start Now" | "Take 3-Minute Quiz" |
| "Read More" | "Learn More About Our Story" |
| "Buy Now" | "Shop Lawn Seed" |

### Key Phrases (use naturally)
- "Seed you can trust"
- "Farm-direct"
- "Expertly blended for your region"
- "Premium seed"
- "No fillers, no GMOs"
- "Independently tested"
- "Guaranteed to grow"

### Trust Signals (use at least one per page/email)
- Farm-direct / American farm-direct
- Independently tested
- High germination rates
- Non-GMO
- Satisfaction guaranteed
- Expert support / seed specialists

### USP Bar Badges
| Badge | Supporting text |
|---|---|
| Free Shipping | On orders over $X |
| Satisfaction Guaranteed | Quality seeds you can trust |
| Family Owned | Since day one |
| Expert Support | Guidance for your region |

---

## 18. Performance Rules

These rules are enforced site-wide and must be maintained in any implementation.

### Images
- Always use WebP or AVIF format
- Always set explicit `width` and `height` attributes (prevents CLS)
- Use `loading="lazy"` on all below-the-fold images
- Use `fetchpriority="high"` on the hero/LCP image only
- Compress before uploading — no raw exports

### Scripts
- All custom JS is deferred (`type="module"` via Vite, or `defer` attribute)
- Third-party scripts (GTM, Adroll, Pinterest) moved to footer or deferred
- jQuery-dependent scripts moved to footer on pages where they aren't needed above the fold

### CSS
- Non-critical CSS is loaded with deferred pattern:
  ```html
  <link rel="stylesheet" href="..." media="print" onload="this.media='all'">
  <noscript><link rel="stylesheet" href="..."></noscript>
  ```
- Critical CSS for above-the-fold elements (header, hero, drawer hidden state) is inlined in `<head>`
- Off-screen panels (cart drawer, mobile nav) hidden via `transform: translateX(100%)` in critical inline CSS — NOT `display:none` or `visibility:hidden` without a corresponding visible state

### Fonts
- Inter and Noto Serif Display loaded from Google Fonts (or self-hosted for max performance)
- Preconnect to font origins: `<link rel="preconnect" href="https://fonts.googleapis.com">`
- Use `font-display: swap` to prevent invisible text during font load

### Resource Hints
```html
<link rel="preconnect" href="https://www.googletagmanager.com">
<link rel="dns-prefetch" href="https://www.google-analytics.com">
<link rel="dns-prefetch" href="https://googleads.g.doubleclick.net">
<link rel="dns-prefetch" href="https://connect.facebook.net">
```

### Core Web Vitals Targets
| Metric | Target |
|---|---|
| LCP (Largest Contentful Paint) | < 2.5s |
| CLS (Cumulative Layout Shift) | < 0.1 |
| TBT (Total Blocking Time) | < 200ms |
| Lighthouse Performance | >= 90 |
| Lighthouse Accessibility | >= 90 |
| Lighthouse Best Practices | >= 90 |
| Lighthouse SEO | >= 90 |
