# Influencer Media Kit — Design Spec
**Date:** 2026-04-17  
**Output:** WordPress page at `/resources/partners/`  
**Script:** `marketing/influencer-media-kit/publish_media_kit.py`  
**Status:** Ready to build

---

## Goal

A content page that serves as the landing page for inbound creator interest and as the URL in Gabe's outreach emails. Framing: "we love to partner with any content creators" — no tiers, no grid, no application form.

---

## Decisions Locked

| Decision | Value |
|---|---|
| Tone | Editorial / vibe-first — story → Jimmy Lewis proof → soft invite |
| Tiers | None — flexible framing |
| URL | `/resources/partners/` |
| Parent | "Resources" page — auto-detect existing; create minimal index if missing |
| CTA | Email only → `customercare@naturesseed.com` |
| PDF | Skip for v1 |
| Auth | WP Application Password (`WP_USERNAME` / `WP_APP_PASSWORD` from `.env`) |
| API | WP REST Core `/wp-json/wp/v2/pages` — NOT WooCommerce API |
| Publish flow | Create as `draft` → Gabe previews in WP admin → Gabe clicks Publish |
| Content format | Gutenberg block markup (visual-edit-friendly in WP admin) |

---

## Page Content

### Section 1 — Hero
```
We love partnering with content creators.

Whether you're building a signature product with us or planting our seed on
camera — we're open to the conversation.
```

### Section 2 — Who We Are
```
Nature's Seed is a vertically-integrated, family-owned seed company covering
13 western states. We grow and test our blends regionally — no fillers,
no generic mixes. Every product is built for where it's planted.
```

### Section 3 — Why This Might Fit
```
We work with creators the same way we work with seed: one at a time, with
intention. We're not looking for a content farm. We're looking for people who
care about what they're recommending — and who want something real to talk about.

Farm-direct. Outcome-focused. One partner at a time.
```

### Section 4 — Proof (Jimmy Lewis)
```
Jimmy Lewis runs jimmylewismows.com — one of the most trusted voices in lawn
care on YouTube. We built Jimmy's Blue Ribbon Bluegrass & Rye Lawn Seed Mix
together. It's his signature blend, sold on our site, and he's one of our
partners. That's the kind of partnership we're made for.
```
Link: `https://jimmylewismows.com` on "jimmylewismows.com"

### Section 5 — What's Possible
```
Some creators build a named product with us. Others try our seed on camera.
Some want to share a favorite mix with their audience in exchange for free
product. We're flexible — if you think there's a fit, let's talk.
```

### Section 6 — CTA
```
Interested? Reach out at customercare@naturesseed.com and tell us a little
about what you do and what you're thinking.
```
CTA link: `mailto:customercare@naturesseed.com`

---

## Technical Spec

### Auth
- `WP_USERNAME` + `WP_APP_PASSWORD` from `.env`
- Basic Auth header: `base64(username:app_password)`
- Endpoint: `https://naturesseed.com/wp-json/wp/v2/pages`

### Parent Page Logic
1. GET `/wp-json/wp/v2/pages?slug=resources`
2. If found → use that page's `id` as parent
3. If not found → create Resources page (`status: draft`, minimal content), use new ID as parent

### Partners Page
- `slug`: `partners`
- `parent`: Resources page ID
- `status`: `draft`
- `title`: `Partner With Us`
- Content: Gutenberg block markup (see below)

### Gutenberg Block Structure
```
<!-- wp:heading {"level":1} -->
<h1>We love partnering with content creators.</h1>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Whether you're building a signature product with us or planting our seed on camera — we're open to the conversation.</p>
<!-- /wp:paragraph -->

<!-- [each section as wp:heading + wp:paragraph blocks] -->
```

### .env Keys Used
```
WP_USERNAME = <wp_admin_username>
WP_APP_PASSWORD = xxxx xxxx xxxx xxxx xxxx xxxx
```

---

## Output

Script prints:
- Resources page status (found existing / created new) + ID
- Partners page URL (draft preview link)
- Instructions to Gabe: "Open this URL in WP admin to preview, then click Publish"

---

## Post-Run Actions (Gabe)

1. Open draft preview URL in WP admin
2. Review layout and content
3. Click **Publish**
4. Verify live at `naturesseed.com/resources/partners/`

---

## Future Iterations (v2+)

- Add hero farm photo (upload via WP Media API, reference by media ID)
- Add Jimmy's product image alongside his section
- PDF download for email outreach
- Klaviyo embed if volume warrants a form
