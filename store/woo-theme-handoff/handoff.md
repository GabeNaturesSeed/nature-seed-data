# Session Handoff — Nature's Seed / GSNature Theme

> **Date:** 2026-03-11
> **From:** Claude Code (VS Code extension)
> **Purpose:** Full context transfer for the next session. Read this + lessons.md + structure.md before doing any work.

---

## Project Overview

**Nature's Seed** (naturesseed.com) is a WooCommerce e-commerce site selling grass seed, wildflower seed, clover, cover crops, and pasture mixes. The site runs on WordPress with a fully custom theme called **GSNature** (not a child theme, not Elementor-based).

- **Hosting:** WPEngine (production), LocalWP (local dev at `Local Sites/natures-seed/`)
- **Theme:** `GSNature` — custom PHP templates + ACF + WooCommerce
- **Build:** Vite 6 (JS + SCSS → dist/) — `npx vite build` to compile
- **Stack:** PHP 8.x, WordPress 6.x, WooCommerce 8.x, ACF Pro, vanilla JS
- **Local MySQL socket:** `/Users/gabegimenes-silva/Library/Application Support/Local/run/Hl1toHKHq/mysql/mysqld.sock`

---

## ALL Work Done — Complete History

### Sprint 1: Spring Marketing + CRO

- Hero CTA: "Shop Now" → "Shop Spring Seeds" (`template-parts/home/hero.php`)
- Quick-Links Bar: `template-parts/home/quick-links.php` (5 category pills)
- Default sort: `menu_order` → `popularity` with featured-first boost (`inc/ajax-handlers.php`, `inc/woocommerce.php`)
- Product badges from WC tags: `best-seller` (sand), `staff-pick` (green), `new-arrival` (gold) in `template-parts/components/product-card.php`
- Cross-sell helper `gsnature_get_category_cross_sells()` in `inc/woocommerce.php`
- Cart drawer cross-sells in `template-parts/header/mini-cart-contents.php`
- Thank-you page cross-sells in `woocommerce/checkout/thankyou.php`

### Sprint 2: Bug Fixes

| Bug | Root Cause | Fix | File |
|---|---|---|---|
| INVALID SECURITY TOKEN on add-to-cart | WPEngine Varnish caches stale nonces | Removed nonce from public AJAX endpoints; rotate fresh nonce in every response | `inc/ajax-handlers.php` |
| Cart drawer FOUC | Drawer HTML visible before JS | Critical inline CSS `transform:translateX(100%)` in `<head>` | `inc/performance.php` |
| Variation URL deep-links | `pickInitialCard()` not called on load | Added DOMContentLoaded call | `assets/js/product-single.js` |
| ZIP filter "No products found" | Wrong: `product_region` taxonomy | Switched to ACF `allowed_zip_codes` meta LIKE query | `inc/ajax-handlers.php` |
| CSP violations (FB, Bing, Pinterest) | Missing domains / TLD mismatch | Added exact TLDs to CSP array | `inc/security.php` |

### Sprint 3: Texas + WC API

- Verified Texas state template with parent-category fallback
- Queried 7 Texas product compositions via WC REST API
- Built CSS conic-gradient pie chart for seed mix compositions
- Pushed `allowed_zip_codes` ACF field to 7 Texas products via WC REST API

### Sprint 4: Lighthouse Performance (Code Fixes)

All changes in `inc/performance.php`:
- Deferred: `dashicons`, `wc-blocks-style`, Stripe CSS (`upe-classic`, `stripe-link`), `rank-math`/`rank-math-pro`/`rank-math-common`, `admin-bar`
- Deferred `gsnature-woocommerce` CSS on homepage/category/shop/tag pages (NOT on product/checkout)
- Moved `jquery-blockui`, `underscore`, `wp-util`, `gtm4wp-scroll-tracking`, `adroll_adroll_js` to footer
- `gsnature_dequeue_devtools_for_visitors()`: dequeues Query Monitor + dashicons for non-logged-in users
- Added resource hints (preconnect GTM, dns-prefetch GA/Doubleclick/Facebook/Pinterest) in `inc/enqueue.php`
- Expanded critical drawer CSS to category/shop/tag pages (was homepage only)

**Baseline scores (pre-code-fixes):** Home 80 · Category 84 · Product 71

### Sprint 5: Documentation

- `tasks/lessons.md` — 21 lessons (L1-L21)
- `tasks/structure.md` — 12 recipes (S1-S12)
- `Claude/design.md` — Complete design system (18 sections: colors, typography, spacing, components, utilities, patterns, brand voice, performance)

### Sprint 6: UX Fixes + Shipping Page (THIS SESSION)

#### Bug: Planting Aids Not Added to Cart

**Root cause:** The WC `woocommerce_add_to_cart` hook function `gsnature_add_planting_aids_to_cart()` checks `$_POST['gsnature_nonce']`, but the AJAX handler sends the nonce under key `nonce`. Nonce check fails silently.

**Fix:** Added planting aids processing directly inside `gsnature_ajax_add_to_cart()`:
```php
// In inc/ajax-handlers.php, after main product added to cart:
if ( ! empty( $_POST['planting_aid_ids'] ) && is_array( $_POST['planting_aid_ids'] ) ) {
    $aid_ids = array_filter( array_map( 'absint', $_POST['planting_aid_ids'] ) );
    foreach ( $aid_ids as $aid_id ) {
        $aid_product = wc_get_product( $aid_id );
        if ( $aid_product && $aid_product->is_purchasable() && $aid_product->is_in_stock() ) {
            WC()->cart->add_to_cart( $aid_id, 1 );
        }
    }
}
```

#### Bug: Cart Drawer Not Opening After Back Navigation

**Root cause:** During Lighthouse fixes, `visibility:hidden` was added to the `.mini-cart-drawer` critical inline CSS. But the SCSS for `.mini-cart-drawer` only uses `transform` (no `visibility` in either state) — so there was no `visibility:visible` to undo it when the drawer opened.

**Fix:** Removed `visibility:hidden` from `.mini-cart-drawer` in critical inline CSS. Kept only `transform:translateX(100%)`.

Current correct critical inline CSS in `inc/performance.php`:
```css
.mini-cart-drawer{transform:translateX(100%)}
.mini-cart-overlay{visibility:hidden;opacity:0}
```

#### Homepage: Removed Broken Sections

Removed from `front-page.php`:
```php
// gsnature_template_part( 'home/about' );     ← removed
// gsnature_template_part( 'home/usp-bar' );   ← removed
```
Both sections were broken/outdated. The homepage now has: hero → category tiles → quick links → best sellers → testimonials.

#### Footer: Shipping Link Fixed

In `footer.php`, changed all occurrences (2 locations):
- Main footer Resources column (line ~201)
- Checkout minimal footer policy nav

`/shipping-policy/` → `/shipping-and-returns-policy/`

#### New Shipping & Returns Policy Page

**File created:** `page-shipping-and-returns-policy.php`

This is a WordPress page template (served when a page with slug `shipping-and-returns-policy` exists). Key sections:
1. Page header with intro paragraph
2. **Highlight Strip** — 4 icon cards: Free Shipping (up to 125 lbs), 3–5 Business Days, Ships from Utah, 30-Day Returns
3. **Shipping Rates** — Rate table: 0–125 lbs FREE, 126–150 lbs $80, 151–175 lbs $160, etc. (+$80 per 25 lbs above 125)
4. Alaska/Hawaii callout note
5. **FAQ Accordion** — 6 questions via native `<details>/<summary>`
6. **Returns & Refunds** — prose sections + 2 more FAQ items
7. **CTA Strip** — dark green bg, "Still have questions?" + Contact Us + phone buttons

**SCSS added** to `assets/scss/pages/_shipping-policy.scss`:
New classes: `__intro`, `__highlight-strip`, `__highlight-grid`, `__highlight-card`, `__highlight-icon`, `__highlight-title`, `__highlight-text`, `__rate-table`, `__rate-row`, `__rate-row--header`, `__rate-row--highlight`, `__rate-row--note`, `__rate-free`, `__note`, `__cta`, `__cta-inner`, `__cta-title`, `__cta-text`, `__cta-actions`

Vite build ran clean after SCSS additions.

**IMPORTANT:** A WordPress page with slug `shipping-and-returns-policy` must be created in WP Admin → Pages for the template to be served. No body content needed — the template handles everything.

#### Production Badge Tags Pushed

Used WC REST API to push 3 badge tags and assign to 34 products on production:
- **Best Seller** (ID: 6026) — 17 products
- **Staff Pick** (ID: 6027) — 10 products
- **New Arrival** (ID: 6028) — 7 products

All 34 product updates confirmed successful (0 failures).

#### Yard Plan Welcome Flow Verified

Checked the full "Create Your Yard Plan" pipeline:
- **GCF endpoint** (`us-central1-natureseed-sgtm.cloudfunctions.net/generateYardPlanPdf`) — **LIVE and working.** Returns a valid signed GCS PDF URL with 90-day expiry.
- **WordPress options configured:** `gsnature_gcf_pdf_url` and `gsnature_gcf_api_key` both set in DB.
- **Klaviyo flow** "Yard Plan Welcome Flow" (ID: `TFkMLx`) — **status: live**, triggered by `Yard Plan Created` metric (ID: `UwVRsc`).
- **Known limitation:** Klaviyo event fires client-side in `fireKlaviyoEvent()` in `yard-plan.js`. If user closes browser before teaser renders, event never fires and email never sends. (See L20 for mitigation note.)

---

## Current State of the Site (as of 2026-03-11)

### What's Deployed to Production
- Sprint 1–4 code changes were deployed (production scores: Home 80, Category 84, Product 71)
- Production badge tags: best-seller, staff-pick, new-arrival assigned to 34 products

### What's Local Only (NOT yet on production)
- Sprint 6 fixes (planting aids, cart drawer, homepage sections removed)
- New `page-shipping-and-returns-policy.php` template
- Footer shipping link fix
- Lighthouse performance additions from Sprint 6 (`inc/performance.php` changes, `inc/enqueue.php` resource hints)

---

## Critical Files Reference

### PHP (in `app/public/wp-content/themes/GSNature/inc/`)
| File | Purpose |
|---|---|
| `ajax-handlers.php` | All AJAX endpoints (add-to-cart WITH planting aids, filters, mini-cart) |
| `woocommerce.php` | WC hooks, cross-sell helper, ZIP validation, catalog defaults |
| `enqueue.php` | Asset loading via Vite manifest + resource hints |
| `performance.php` | ALL performance: CSS defer, script moves, critical inline CSS, cache headers |
| `security.php` | CSP headers (array-based per directive) |
| `yard-plan.php` | Yard Plan quiz backend (scoring, ZIP lookup, GCF PDF call, Klaviyo data) |
| `setup.php` | Theme supports, menus, image sizes |
| `helpers.php` | `gsnature_template_part()`, `gsnature_load_data()`, general utilities |

### Key JS (in `assets/js/`)
| File | Purpose |
|---|---|
| `cart.js` | Add-to-cart (+ planting aids via `planting_aid_ids[]`), mini cart drawer, cross-sell add |
| `yard-plan.js` | Multi-step quiz modal (ZIP lookup, step navigation, AJAX submit, Klaviyo event) |
| `filters.js` | AJAX product filter sidebar + Seed Finder quiz + URL state |
| `product-single.js` | Variation cards, price-per-lb, ZIP modal, `pickInitialCard()` |
| `main.js` | Mobile nav, search toggle, scroll effects |

### Templates
| File | Purpose |
|---|---|
| `front-page.php` | Homepage (hero → category tiles → quick links → best sellers → testimonials) |
| `footer.php` | Site footer with shipping link pointing to `/shipping-and-returns-policy/` |
| `page-shipping-and-returns-policy.php` | **NEW** — Full branded shipping & returns page |
| `template-parts/home/` | Hero, category-tiles, quick-links, best-sellers, testimonials |
| `template-parts/components/product-card.php` | Product card with badge rendering |
| `template-parts/header/mini-cart-drawer.php` | Cart drawer shell |
| `template-parts/header/mini-cart-contents.php` | Cart items + cross-sells |

### Documentation (in `Claude/`)
| File | Purpose |
|---|---|
| `design.md` | Complete design system (18 sections) — tokens, components, patterns, brand voice |

---

## Key Credentials

### WooCommerce REST API (Production)
- **Base URL:** `https://naturesseed.com/wp-json/wc/v3`
- **Consumer Key:** `ck_9629579f1379f272169de8628edddb00b24737f9`
- **Consumer Secret:** `cs_bf6dcf206d6ed26b83e55e8af62c16de26339815`
- **Required:** `User-Agent: GSNature/1.0` header (Cloudflare blocks without it)

### Local MySQL
- **Binary:** `/Users/gabegimenes-silva/Library/Application Support/Local/lightning-services/mysql-8.0.35+4/bin/darwin-arm64/bin/mysql`
- **Socket:** `/Users/gabegimenes-silva/Library/Application Support/Local/run/Hl1toHKHq/mysql/mysqld.sock`
- **Database:** `local` / **User:** `root` / **Password:** `root`

### Google Cloud Function (PDF Generator)
- **URL:** `https://us-central1-natureseed-sgtm.cloudfunctions.net/generateYardPlanPdf`
- **API Key:** `XTRRLEY9kRq5XK8vkgeoxbUHTskJrT6XFnMHaRibZmo=`
- Configured via WordPress options: `gsnature_gcf_pdf_url`, `gsnature_gcf_api_key`

### Klaviyo
- Accessible via MCP tool `mcp__claude_ai_Klaviyo__*`
- Yard Plan flow: ID `TFkMLx`, metric "Yard Plan Created" ID `UwVRsc`

---

## Immediate Next Priorities

1. **Deploy Sprint 6 fixes to production** — planting aids fix, cart drawer fix, footer link, new shipping page (all local only)
2. **Create WordPress page for shipping-and-returns-policy slug** — must exist in DB for template to serve
3. **Re-upload product images as WebP** — biggest Lighthouse win remaining (~700 KiB savings on LCP images)
4. **Disable Query Monitor plugin on production** — it's loading on every frontend page for all visitors
5. **Lighthouse re-audit** after all fixes are live on production

---

## Architecture Decisions (Don't Change Without Reason)

1. **No nonces on public AJAX endpoints** — WPEngine Varnish caches pages with embedded nonces, making them stale. Instead, every AJAX response includes a fresh nonce.
2. **Cross-sells computed at runtime** — `gsnature_get_category_cross_sells()` maps cart categories → companions dynamically. No `_crosssell_ids` stored on products.
3. **Featured-first sorting via posts_clauses** — LEFT JOINs for ordering only, no WHERE side-effect (critical — named meta_query clauses also filter).
4. **ZIP filter uses ACF meta, not taxonomy** — `allowed_zip_codes` ACF field, comma-separated ZIP codes, LIKE query with 3 OR conditions.
5. **Performance code centralized in `inc/performance.php`** — All lazy loading, CSS deferral, script moves, cache headers live here. Don't scatter performance code.
6. **Cart drawer hidden via `transform` only** — Never add `visibility:hidden` to `.mini-cart-drawer` critical CSS unless SCSS gets a corresponding `visibility:visible` on the open state.
