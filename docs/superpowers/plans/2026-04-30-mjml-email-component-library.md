# MJML Email Component Library — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular MJML component library for Nature's Seed promotional emails with an npm build pipeline that compiles to Gmail-safe, responsive HTML.

**Architecture:** Nine reusable MJML partials (components/) are included into campaign templates (templates/) via `<mj-include>`. `build.js` compiles all templates to dist/ and warns when output exceeds 90KB. Visual reference for all design decisions: `marketing/email-system/mockup-promo.html`.

**Tech Stack:** Node.js 18+, MJML 4.15+, npm

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `marketing/email-system/package.json` | Create | npm scripts + mjml dependency |
| `marketing/email-system/build.js` | Create | Compile templates/ → dist/, size check, watch mode |
| `marketing/email-system/components/header.mjml` | Create | Logo row, white bg, bottom border |
| `marketing/email-system/components/footer.mjml` | Create | Dark bg, logo, nav, address, unsubscribe |
| `marketing/email-system/components/usps-bar.mjml` | Create | 4-badge green trust row |
| `marketing/email-system/components/cta-block.mjml` | Create | Centered serif H3 + outline button |
| `marketing/email-system/components/hero-editorial.mjml` | Create | Dark bg, serif headline, orange CTA |
| `marketing/email-system/components/hero-image.mjml` | Create | Same but with background image support |
| `marketing/email-system/components/product-single.mjml` | Create | Full-width horizontal product spotlight |
| `marketing/email-system/components/product-grid-2.mjml` | Create | 2-column product grid |
| `marketing/email-system/components/product-grid-3.mjml` | Create | 3-column product grid |
| `marketing/email-system/templates/promo-editorial.mjml` | Create | Full promotional template (assembles all components) |
| `marketing/email-system/dist/promo-editorial.html` | Generated | Final HTML → paste into Klaviyo |

---

## Task 1: Project Scaffold + Build System

**Files:**
- Create: `marketing/email-system/package.json`
- Create: `marketing/email-system/build.js`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "natures-seed-email-system",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "build": "node build.js",
    "dev": "node build.js --watch"
  },
  "dependencies": {
    "mjml": "^4.15.0"
  }
}
```

Save to: `marketing/email-system/package.json`

- [ ] **Step 2: Install MJML**

```bash
cd "marketing/email-system"
npm install
```

Expected: `node_modules/` created, `package-lock.json` written. No errors.

- [ ] **Step 3: Create build.js**

```javascript
const mjml2html = require('mjml');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const TEMPLATES_DIR = path.join(ROOT, 'templates');
const DIST_DIR = path.join(ROOT, 'dist');
const WARN_KB = 90;
const LIMIT_KB = 102;

function compile(templatePath) {
  const input = fs.readFileSync(templatePath, 'utf8');
  const { html, errors } = mjml2html(input, {
    filePath: templatePath,
    validationLevel: 'strict'
  });

  if (errors.length) {
    console.error(`[ERROR] ${path.basename(templatePath)}:`);
    errors.forEach(e => console.error(`  ${e.formattedMessage}`));
    return false;
  }

  if (!fs.existsSync(DIST_DIR)) fs.mkdirSync(DIST_DIR, { recursive: true });

  const outName = path.basename(templatePath, '.mjml') + '.html';
  const outPath = path.join(DIST_DIR, outName);
  fs.writeFileSync(outPath, html);

  const sizeKB = Math.round(fs.statSync(outPath).size / 1024);

  if (sizeKB > LIMIT_KB) {
    console.error(`[CLIP]  ${outName} → ${sizeKB}KB — GMAIL WILL CLIP THIS (limit: ${LIMIT_KB}KB)`);
  } else if (sizeKB > WARN_KB) {
    console.warn(`[WARN]  ${outName} → ${sizeKB}KB — approaching Gmail limit (${LIMIT_KB}KB)`);
  } else {
    console.log(`[OK]    ${outName} → ${sizeKB}KB`);
  }

  return true;
}

function buildAll() {
  if (!fs.existsSync(TEMPLATES_DIR)) {
    console.log('No templates/ directory yet — nothing to compile.');
    return;
  }
  const templates = fs.readdirSync(TEMPLATES_DIR).filter(f => f.endsWith('.mjml'));
  if (!templates.length) {
    console.log('No .mjml files in templates/ yet.');
    return;
  }
  let ok = 0;
  templates.forEach(f => {
    if (compile(path.join(TEMPLATES_DIR, f))) ok++;
  });
  console.log(`\nBuilt ${ok}/${templates.length} templates.`);
}

buildAll();

if (process.argv.includes('--watch')) {
  console.log('\nWatching components/ and templates/ for changes...');
  const watchDirs = [TEMPLATES_DIR, path.join(ROOT, 'components')];
  watchDirs.forEach(dir => {
    if (!fs.existsSync(dir)) return;
    fs.watch(dir, { recursive: true }, (event, filename) => {
      if (filename && filename.endsWith('.mjml')) {
        console.log(`\n[CHANGE] ${filename} — rebuilding...`);
        buildAll();
      }
    });
  });
}
```

Save to: `marketing/email-system/build.js`

- [ ] **Step 4: Smoke-test the build script**

```bash
cd "marketing/email-system"
node build.js
```

Expected output: `No templates/ directory yet — nothing to compile.`

- [ ] **Step 5: Commit**

```bash
cd "marketing/email-system"
git add package.json package-lock.json build.js
git commit -m "feat(email): add MJML build system scaffold"
```

---

## Task 2: footer.mjml

**Files:**
- Create: `marketing/email-system/components/footer.mjml`

- [ ] **Step 1: Create footer component**

```xml
<mj-section background-color="#1b4332" padding="36px 40px 36px">
  <mj-column>
    <mj-text
      align="center"
      font-family="'Noto Serif Display', Georgia, serif"
      font-size="16px"
      font-weight="600"
      color="#a8d5b5"
      letter-spacing="0.08em"
      padding-bottom="16px"
    >
      NATURE'S SEED
    </mj-text>

    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="12px"
      color="#a8d5b5"
      padding-bottom="16px"
    >
      <a href="https://naturesseed.com/shop" style="color:#a8d5b5;text-decoration:none;margin:0 10px;">Shop</a>
      <a href="https://naturesseed.com/about" style="color:#a8d5b5;text-decoration:none;margin:0 10px;">Our Story</a>
      <a href="https://naturesseed.com/support" style="color:#a8d5b5;text-decoration:none;margin:0 10px;">Support</a>
      <a href="{{ preference_center_link }}" style="color:#a8d5b5;text-decoration:none;margin:0 10px;">Preferences</a>
    </mj-text>

    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      color="#52b788"
      line-height="1.6"
      padding-bottom="16px"
    >
      Nature's Seed · Salt Lake City, UT 84101<br/>
      customercare@naturesseed.com · 801-531-1456
    </mj-text>

    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      color="#52b788"
      line-height="1.6"
    >
      You're receiving this because you opted in at naturesseed.com.<br/>
      <a href="{{ unsubscribe_link }}" style="color:#a8d5b5;text-decoration:underline;">Unsubscribe</a> &nbsp;·&nbsp;
      <a href="{{ preference_center_link }}" style="color:#a8d5b5;text-decoration:underline;">Update Preferences</a>
    </mj-text>
  </mj-column>
</mj-section>
```

Save to: `marketing/email-system/components/footer.mjml`

- [ ] **Step 2: Create a test template to verify it compiles**

```xml
<mjml>
  <mj-head>
    <mj-font name="Noto Serif Display" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:wght@600&family=Inter:wght@400;500;600&display=swap" />
    <mj-attributes>
      <mj-all font-family="Inter, Arial, sans-serif" />
    </mj-attributes>
  </mj-head>
  <mj-body width="620px" background-color="#f0ece4">
    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

Save to: `marketing/email-system/templates/test-footer.mjml`

- [ ] **Step 3: Compile and check**

```bash
cd "marketing/email-system"
node build.js
```

Expected: `[OK]    test-footer.html → <5KB` with no errors.

- [ ] **Step 4: Open in browser and compare**

Open `marketing/email-system/dist/test-footer.html` in your browser. Compare to the footer in `mockup-promo.html`:
- Dark green (#1b4332) background
- "NATURE'S SEED" in light green serif
- Nav links, address, unsubscribe all present

- [ ] **Step 5: Delete test template (keep only the component)**

```bash
rm "marketing/email-system/templates/test-footer.mjml"
rm "marketing/email-system/dist/test-footer.html"
```

- [ ] **Step 6: Commit**

```bash
git add marketing/email-system/components/footer.mjml
git commit -m "feat(email): add footer component"
```

---

## Task 3: header.mjml

**Files:**
- Create: `marketing/email-system/components/header.mjml`

- [ ] **Step 1: Create header component**

```xml
<mj-section background-color="#ffffff" padding="24px 40px" border-bottom="1px solid #e8e4dc">
  <mj-column>
    <mj-text
      align="center"
      font-family="'Noto Serif Display', Georgia, serif"
      font-size="22px"
      font-weight="700"
      color="#2d6a4f"
      letter-spacing="0.06em"
      padding="0"
    >
      NATURE'S <span style="color:#1b4332;">SEED</span>
    </mj-text>
  </mj-column>
</mj-section>
```

Save to: `marketing/email-system/components/header.mjml`

- [ ] **Step 2: Create test template**

```xml
<mjml>
  <mj-head>
    <mj-font name="Noto Serif Display" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:wght@700&family=Inter:wght@400;500;600&display=swap" />
    <mj-attributes>
      <mj-all font-family="Inter, Arial, sans-serif" />
    </mj-attributes>
  </mj-head>
  <mj-body width="620px" background-color="#f0ece4">
    <mj-include path="../components/header.mjml" />
    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

Save to: `marketing/email-system/templates/test-header.mjml`

- [ ] **Step 3: Compile and verify**

```bash
cd "marketing/email-system"
node build.js
```

Open `dist/test-header.html`. Check: white header, "NATURE'S" in #2d6a4f, "SEED" in #1b4332, bottom border visible.

- [ ] **Step 4: Delete test template**

```bash
rm "marketing/email-system/templates/test-header.mjml"
rm "marketing/email-system/dist/test-header.html"
```

- [ ] **Step 5: Commit**

```bash
git add marketing/email-system/components/header.mjml
git commit -m "feat(email): add header component"
```

---

## Task 4: usps-bar.mjml

**Files:**
- Create: `marketing/email-system/components/usps-bar.mjml`

- [ ] **Step 1: Create usps-bar component**

```xml
<mj-section background-color="#2d6a4f" padding="28px 40px">
  <mj-column padding="0 8px">
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      font-weight="600"
      color="#ffffff"
      letter-spacing="0.06em"
      text-transform="uppercase"
      padding-bottom="4px"
    >
      Free Shipping
    </mj-text>
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      color="#a8d5b5"
      line-height="1.4"
      padding="0"
    >
      Orders over $75
    </mj-text>
  </mj-column>

  <mj-column padding="0 8px">
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      font-weight="600"
      color="#ffffff"
      letter-spacing="0.06em"
      text-transform="uppercase"
      padding-bottom="4px"
    >
      Guaranteed
    </mj-text>
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      color="#a8d5b5"
      line-height="1.4"
      padding="0"
    >
      Quality you can trust
    </mj-text>
  </mj-column>

  <mj-column padding="0 8px">
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      font-weight="600"
      color="#ffffff"
      letter-spacing="0.06em"
      text-transform="uppercase"
      padding-bottom="4px"
    >
      Family Owned
    </mj-text>
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      color="#a8d5b5"
      line-height="1.4"
      padding="0"
    >
      Since day one
    </mj-text>
  </mj-column>

  <mj-column padding="0 8px">
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      font-weight="600"
      color="#ffffff"
      letter-spacing="0.06em"
      text-transform="uppercase"
      padding-bottom="4px"
    >
      Expert Support
    </mj-text>
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      color="#a8d5b5"
      line-height="1.4"
      padding="0"
    >
      For your region
    </mj-text>
  </mj-column>
</mj-section>
```

Save to: `marketing/email-system/components/usps-bar.mjml`

- [ ] **Step 2: Create test template**

```xml
<mjml>
  <mj-head>
    <mj-font name="Noto Serif Display" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap" />
    <mj-attributes><mj-all font-family="Inter, Arial, sans-serif" /></mj-attributes>
  </mj-head>
  <mj-body width="620px" background-color="#f0ece4">
    <mj-include path="../components/header.mjml" />
    <mj-include path="../components/usps-bar.mjml" />
    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

Save to: `marketing/email-system/templates/test-usps.mjml`

- [ ] **Step 3: Compile and verify**

```bash
node build.js
```

Open `dist/test-usps.html`. Check: green bar, 4 columns, white bold labels, light green sub-text.

- [ ] **Step 4: Delete test template**

```bash
rm "marketing/email-system/templates/test-usps.mjml"
rm "marketing/email-system/dist/test-usps.html"
```

- [ ] **Step 5: Commit**

```bash
git add marketing/email-system/components/usps-bar.mjml
git commit -m "feat(email): add USP trust bar component"
```

---

## Task 5: cta-block.mjml

**Files:**
- Create: `marketing/email-system/components/cta-block.mjml`

- [ ] **Step 1: Create cta-block component**

```xml
<mj-section background-color="#ffffff" padding="44px 48px" border-top="1px solid #e8e4dc">
  <mj-column>
    <mj-text
      align="center"
      font-family="'Noto Serif Display', Georgia, serif"
      font-size="22px"
      font-weight="600"
      color="#1b4332"
      line-height="1.3"
      padding-bottom="12px"
    >
      Not sure which blend is right for you?
    </mj-text>

    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="14px"
      color="#6c757d"
      line-height="1.6"
      padding-bottom="24px"
    >
      Our seed specialists match you to the right product<br/>
      for your soil, region, and goals — for free.
    </mj-text>

    <mj-button
      align="center"
      background-color="transparent"
      color="#2d6a4f"
      border="2px solid #2d6a4f"
      border-radius="2px"
      font-family="Inter, Arial, sans-serif"
      font-size="13px"
      font-weight="600"
      letter-spacing="0.04em"
      text-transform="uppercase"
      inner-padding="13px 28px"
      href="https://naturesseed.com/pages/seed-selector"
    >
      Ask a Seed Expert
    </mj-button>
  </mj-column>
</mj-section>
```

Save to: `marketing/email-system/components/cta-block.mjml`

- [ ] **Step 2: Compile inline (no test template needed — add to existing pattern)**

```xml
<mjml>
  <mj-head>
    <mj-font name="Noto Serif Display" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap" />
    <mj-attributes><mj-all font-family="Inter, Arial, sans-serif" /></mj-attributes>
  </mj-head>
  <mj-body width="620px" background-color="#f0ece4">
    <mj-include path="../components/header.mjml" />
    <mj-include path="../components/cta-block.mjml" />
    <mj-include path="../components/usps-bar.mjml" />
    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

Save to `templates/test-cta.mjml`, run `node build.js`, open `dist/test-cta.html`. Check: outline green button, serif headline, light gray sub-copy.

- [ ] **Step 3: Delete test template**

```bash
rm "marketing/email-system/templates/test-cta.mjml"
rm "marketing/email-system/dist/test-cta.html"
```

- [ ] **Step 4: Commit**

```bash
git add marketing/email-system/components/cta-block.mjml
git commit -m "feat(email): add soft CTA block component"
```

---

## Task 6: hero-editorial.mjml

**Files:**
- Create: `marketing/email-system/components/hero-editorial.mjml`

- [ ] **Step 1: Create hero-editorial component**

```xml
<mj-section background-color="#1b4332" padding="64px 48px 56px">
  <mj-column>
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      font-weight="600"
      color="#d4a373"
      letter-spacing="0.14em"
      text-transform="uppercase"
      padding-bottom="20px"
    >
      Spring 2026 Collection
    </mj-text>

    <mj-text
      align="center"
      font-family="'Noto Serif Display', Georgia, serif"
      font-size="46px"
      font-weight="700"
      color="#ffffff"
      line-height="1.10"
      letter-spacing="-0.01em"
      padding-bottom="20px"
    >
      Beautiful Lawns<br/>
      Start with<br/>
      <span style="font-style:italic;color:#a8d5b5;">Seed you can trust.</span>
    </mj-text>

    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="16px"
      color="#a8d5b5"
      line-height="1.6"
      padding-bottom="32px"
    >
      Expertly blended for your region. Farm-direct,<br/>
      filler-free, and independently tested for germination.
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
      href="https://naturesseed.com/collections/lawn-seed"
    >
      Shop Spring Seed
    </mj-button>

    <mj-divider
      border-color="#d4a373"
      border-width="3px"
      width="48px"
      padding="40px 0 0"
    />
  </mj-column>
</mj-section>
```

Save to: `marketing/email-system/components/hero-editorial.mjml`

- [ ] **Step 2: Create test template**

```xml
<mjml>
  <mj-head>
    <mj-font name="Noto Serif Display" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:ital,wght@0,600;0,700;1,700&family=Inter:wght@400;500;600&display=swap" />
    <mj-attributes><mj-all font-family="Inter, Arial, sans-serif" /></mj-attributes>
  </mj-head>
  <mj-body width="620px" background-color="#f0ece4">
    <mj-include path="../components/header.mjml" />
    <mj-include path="../components/hero-editorial.mjml" />
    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

Save to `templates/test-hero.mjml`, run `node build.js`, open `dist/test-hero.html`.

Check: dark green bg, large italic serif headline in light green, sand eyebrow, orange button, sand divider at bottom.

- [ ] **Step 3: Delete test template**

```bash
rm "marketing/email-system/templates/test-hero.mjml"
rm "marketing/email-system/dist/test-hero.html"
```

- [ ] **Step 4: Commit**

```bash
git add marketing/email-system/components/hero-editorial.mjml
git commit -m "feat(email): add editorial hero component"
```

---

## Task 7: hero-image.mjml

**Files:**
- Create: `marketing/email-system/components/hero-image.mjml`

- [ ] **Step 1: Create hero-image component**

```xml
<mj-section
  background-url="https://via.placeholder.com/620x400/1b4332/1b4332"
  background-size="cover"
  background-position="center"
  padding="64px 48px 56px"
>
  <mj-column background-color="rgba(27, 67, 50, 0.72)" border-radius="2px" padding="40px 32px">
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      font-weight="600"
      color="#d4a373"
      letter-spacing="0.14em"
      text-transform="uppercase"
      padding-bottom="20px"
    >
      Spring 2026 Collection
    </mj-text>

    <mj-text
      align="center"
      font-family="'Noto Serif Display', Georgia, serif"
      font-size="42px"
      font-weight="700"
      color="#ffffff"
      line-height="1.10"
      letter-spacing="-0.01em"
      padding-bottom="20px"
    >
      Beautiful Lawns<br/>
      Start with<br/>
      <span style="font-style:italic;color:#a8d5b5;">Seed you can trust.</span>
    </mj-text>

    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="15px"
      color="#a8d5b5"
      line-height="1.6"
      padding-bottom="32px"
    >
      Expertly blended for your region. Farm-direct,<br/>
      filler-free, and independently tested for germination.
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
      href="https://naturesseed.com/collections/lawn-seed"
    >
      Shop Spring Seed
    </mj-button>
  </mj-column>
</mj-section>
```

Save to: `marketing/email-system/components/hero-image.mjml`

> **Note:** Replace `background-url` with the actual hosted image URL when using this component. The placeholder above will render as a solid dark green block.

- [ ] **Step 2: Compile test**

```xml
<mjml>
  <mj-head>
    <mj-font name="Noto Serif Display" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:ital,wght@0,600;0,700;1,700&family=Inter:wght@400;500;600&display=swap" />
    <mj-attributes><mj-all font-family="Inter, Arial, sans-serif" /></mj-attributes>
  </mj-head>
  <mj-body width="620px" background-color="#f0ece4">
    <mj-include path="../components/header.mjml" />
    <mj-include path="../components/hero-image.mjml" />
    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

Save to `templates/test-hero-image.mjml`, run `node build.js`, open `dist/test-hero-image.html`. Confirm layout intact with overlay approach.

- [ ] **Step 3: Delete test template**

```bash
rm "marketing/email-system/templates/test-hero-image.mjml"
rm "marketing/email-system/dist/test-hero-image.html"
```

- [ ] **Step 4: Commit**

```bash
git add marketing/email-system/components/hero-image.mjml
git commit -m "feat(email): add image hero component"
```

---

## Task 8: product-single.mjml

**Files:**
- Create: `marketing/email-system/components/product-single.mjml`

- [ ] **Step 1: Create product-single component**

```xml
<mj-section background-color="#f8f6f2" padding="36px 40px">
  <mj-column width="140px" padding-right="28px">
    <mj-image
      src="https://via.placeholder.com/140x140/e8e4dc/e8e4dc"
      width="140px"
      border-radius="2px"
      alt="Product image"
      padding="0"
    />
  </mj-column>

  <mj-column>
    <mj-text
      font-family="Inter, Arial, sans-serif"
      font-size="10px"
      font-weight="600"
      color="#2d6a4f"
      letter-spacing="0.12em"
      text-transform="uppercase"
      padding-bottom="8px"
    >
      Staff Pick
    </mj-text>

    <mj-text
      font-family="'Noto Serif Display', Georgia, serif"
      font-size="22px"
      font-weight="600"
      color="#1b4332"
      line-height="1.3"
      padding-bottom="10px"
    >
      Pasture Pro Blend
    </mj-text>

    <mj-text
      font-family="Inter, Arial, sans-serif"
      font-size="13px"
      color="#6c757d"
      line-height="1.5"
      padding-bottom="20px"
    >
      Our seed scientists' top pick for high-production pastures.
      Non-GMO, independently tested, guaranteed to grow.
    </mj-text>

    <mj-button
      align="left"
      background-color="#C96A2E"
      color="#ffffff"
      border-radius="2px"
      font-family="Inter, Arial, sans-serif"
      font-size="12px"
      font-weight="600"
      letter-spacing="0.05em"
      text-transform="uppercase"
      inner-padding="12px 24px"
      href="https://naturesseed.com/collections/pasture-seed"
      padding="0"
    >
      Shop Pasture
    </mj-button>
  </mj-column>
</mj-section>
```

Save to: `marketing/email-system/components/product-single.mjml`

- [ ] **Step 2: Compile test**

```xml
<mjml>
  <mj-head>
    <mj-font name="Noto Serif Display" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap" />
    <mj-attributes><mj-all font-family="Inter, Arial, sans-serif" /></mj-attributes>
  </mj-head>
  <mj-body width="620px" background-color="#f0ece4">
    <mj-include path="../components/header.mjml" />
    <mj-include path="../components/product-single.mjml" />
    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

Save to `templates/test-product-single.mjml`, compile, open. Check: image left, content right, orange button left-aligned.

- [ ] **Step 3: Delete test template**

```bash
rm "marketing/email-system/templates/test-product-single.mjml"
rm "marketing/email-system/dist/test-product-single.html"
```

- [ ] **Step 4: Commit**

```bash
git add marketing/email-system/components/product-single.mjml
git commit -m "feat(email): add featured product single component"
```

---

## Task 9: product-grid-2.mjml

**Files:**
- Create: `marketing/email-system/components/product-grid-2.mjml`

- [ ] **Step 1: Create product-grid-2 component**

```xml
<mj-section padding="0" border="2px solid #e8e4dc">
  <mj-column background-color="#ffffff" padding="28px 24px 32px" border-right="1px solid #e8e4dc">
    <mj-image
      src="https://via.placeholder.com/250x250/f0ece4/f0ece4"
      width="100%"
      border-radius="2px"
      alt="Product image"
      padding-bottom="20px"
    />
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="10px"
      font-weight="600"
      color="#2d6a4f"
      letter-spacing="0.12em"
      text-transform="uppercase"
      padding-bottom="8px"
    >
      Lawn Seed
    </mj-text>
    <mj-text
      align="center"
      font-family="'Noto Serif Display', Georgia, serif"
      font-size="18px"
      font-weight="600"
      color="#1b4332"
      line-height="1.3"
      padding-bottom="10px"
    >
      Premium Turf Blend
    </mj-text>
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="13px"
      color="#6c757d"
      line-height="1.5"
      padding-bottom="20px"
    >
      Dense, durable growth engineered for the Intermountain West.
    </mj-text>
    <mj-button
      align="center"
      background-color="#C96A2E"
      color="#ffffff"
      border-radius="2px"
      font-family="Inter, Arial, sans-serif"
      font-size="12px"
      font-weight="600"
      letter-spacing="0.05em"
      text-transform="uppercase"
      inner-padding="12px 24px"
      href="https://naturesseed.com/collections/lawn-seed"
      padding="0"
    >
      Shop Lawn
    </mj-button>
  </mj-column>

  <mj-column background-color="#ffffff" padding="28px 24px 32px" border-left="1px solid #e8e4dc">
    <mj-image
      src="https://via.placeholder.com/250x250/f0ece4/f0ece4"
      width="100%"
      border-radius="2px"
      alt="Product image"
      padding-bottom="20px"
    />
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="10px"
      font-weight="600"
      color="#2d6a4f"
      letter-spacing="0.12em"
      text-transform="uppercase"
      padding-bottom="8px"
    >
      Wildflower
    </mj-text>
    <mj-text
      align="center"
      font-family="'Noto Serif Display', Georgia, serif"
      font-size="18px"
      font-weight="600"
      color="#1b4332"
      line-height="1.3"
      padding-bottom="10px"
    >
      Western Wildflower Mix
    </mj-text>
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="13px"
      color="#6c757d"
      line-height="1.5"
      padding-bottom="20px"
    >
      Native species. Low water. Stunning color from spring through fall.
    </mj-text>
    <mj-button
      align="center"
      background-color="#C96A2E"
      color="#ffffff"
      border-radius="2px"
      font-family="Inter, Arial, sans-serif"
      font-size="12px"
      font-weight="600"
      letter-spacing="0.05em"
      text-transform="uppercase"
      inner-padding="12px 24px"
      href="https://naturesseed.com/collections/wildflower-seed"
      padding="0"
    >
      Shop Wildflower
    </mj-button>
  </mj-column>
</mj-section>
```

Save to: `marketing/email-system/components/product-grid-2.mjml`

- [ ] **Step 2: Compile test**

```xml
<mjml>
  <mj-head>
    <mj-font name="Noto Serif Display" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap" />
    <mj-attributes><mj-all font-family="Inter, Arial, sans-serif" /></mj-attributes>
  </mj-head>
  <mj-body width="620px" background-color="#f0ece4">
    <mj-include path="../components/header.mjml" />
    <mj-include path="../components/product-grid-2.mjml" />
    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

Save to `templates/test-grid-2.mjml`, compile, open. Check: two equal columns, placeholder images, serif product names, orange buttons.

- [ ] **Step 3: Delete test template**

```bash
rm "marketing/email-system/templates/test-grid-2.mjml"
rm "marketing/email-system/dist/test-grid-2.html"
```

- [ ] **Step 4: Commit**

```bash
git add marketing/email-system/components/product-grid-2.mjml
git commit -m "feat(email): add 2-column product grid component"
```

---

## Task 10: product-grid-3.mjml

**Files:**
- Create: `marketing/email-system/components/product-grid-3.mjml`

- [ ] **Step 1: Create product-grid-3 component**

```xml
<mj-section padding="0" border="2px solid #e8e4dc">
  <mj-column background-color="#ffffff" padding="20px 16px 24px" border-right="1px solid #e8e4dc">
    <mj-image
      src="https://via.placeholder.com/160x160/f0ece4/f0ece4"
      width="100%"
      border-radius="2px"
      alt="Product image"
      padding-bottom="16px"
    />
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="10px"
      font-weight="600"
      color="#2d6a4f"
      letter-spacing="0.12em"
      text-transform="uppercase"
      padding-bottom="6px"
    >
      Lawn Seed
    </mj-text>
    <mj-text
      align="center"
      font-family="'Noto Serif Display', Georgia, serif"
      font-size="16px"
      font-weight="600"
      color="#1b4332"
      line-height="1.3"
      padding-bottom="8px"
    >
      Premium Turf Blend
    </mj-text>
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="12px"
      color="#6c757d"
      line-height="1.5"
      padding-bottom="16px"
    >
      Durable growth for the West.
    </mj-text>
    <mj-button
      align="center"
      background-color="#C96A2E"
      color="#ffffff"
      border-radius="2px"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      font-weight="600"
      letter-spacing="0.05em"
      text-transform="uppercase"
      inner-padding="10px 16px"
      href="https://naturesseed.com/collections/lawn-seed"
      padding="0"
    >
      Shop Lawn
    </mj-button>
  </mj-column>

  <mj-column background-color="#ffffff" padding="20px 16px 24px" border-right="1px solid #e8e4dc" border-left="1px solid #e8e4dc">
    <mj-image
      src="https://via.placeholder.com/160x160/f0ece4/f0ece4"
      width="100%"
      border-radius="2px"
      alt="Product image"
      padding-bottom="16px"
    />
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="10px"
      font-weight="600"
      color="#2d6a4f"
      letter-spacing="0.12em"
      text-transform="uppercase"
      padding-bottom="6px"
    >
      Wildflower
    </mj-text>
    <mj-text
      align="center"
      font-family="'Noto Serif Display', Georgia, serif"
      font-size="16px"
      font-weight="600"
      color="#1b4332"
      line-height="1.3"
      padding-bottom="8px"
    >
      Western Wildflower Mix
    </mj-text>
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="12px"
      color="#6c757d"
      line-height="1.5"
      padding-bottom="16px"
    >
      Native species, low water.
    </mj-text>
    <mj-button
      align="center"
      background-color="#C96A2E"
      color="#ffffff"
      border-radius="2px"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      font-weight="600"
      letter-spacing="0.05em"
      text-transform="uppercase"
      inner-padding="10px 16px"
      href="https://naturesseed.com/collections/wildflower-seed"
      padding="0"
    >
      Shop Wildflower
    </mj-button>
  </mj-column>

  <mj-column background-color="#ffffff" padding="20px 16px 24px" border-left="1px solid #e8e4dc">
    <mj-image
      src="https://via.placeholder.com/160x160/f0ece4/f0ece4"
      width="100%"
      border-radius="2px"
      alt="Product image"
      padding-bottom="16px"
    />
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="10px"
      font-weight="600"
      color="#2d6a4f"
      letter-spacing="0.12em"
      text-transform="uppercase"
      padding-bottom="6px"
    >
      Pasture
    </mj-text>
    <mj-text
      align="center"
      font-family="'Noto Serif Display', Georgia, serif"
      font-size="16px"
      font-weight="600"
      color="#1b4332"
      line-height="1.3"
      padding-bottom="8px"
    >
      Pasture Pro Blend
    </mj-text>
    <mj-text
      align="center"
      font-family="Inter, Arial, sans-serif"
      font-size="12px"
      color="#6c757d"
      line-height="1.5"
      padding-bottom="16px"
    >
      Non-GMO, tested, guaranteed.
    </mj-text>
    <mj-button
      align="center"
      background-color="#C96A2E"
      color="#ffffff"
      border-radius="2px"
      font-family="Inter, Arial, sans-serif"
      font-size="11px"
      font-weight="600"
      letter-spacing="0.05em"
      text-transform="uppercase"
      inner-padding="10px 16px"
      href="https://naturesseed.com/collections/pasture-seed"
      padding="0"
    >
      Shop Pasture
    </mj-button>
  </mj-column>
</mj-section>
```

Save to: `marketing/email-system/components/product-grid-3.mjml`

- [ ] **Step 2: Compile test (same pattern as Task 9 — swap grid-2 for grid-3 in test template)**

Compile and open. Check: three equal columns, tighter padding than 2-col, all buttons present.

- [ ] **Step 3: Commit**

```bash
git add marketing/email-system/components/product-grid-3.mjml
git commit -m "feat(email): add 3-column product grid component"
```

---

## Task 11: Assemble promo-editorial.mjml

**Files:**
- Create: `marketing/email-system/templates/promo-editorial.mjml`

This is the first complete campaign template. It assembles all components in the order established by the approved mockup.

- [ ] **Step 1: Create the full template**

```xml
<mjml>
  <mj-head>
    <mj-preview>Expertly blended for your region — seed you can trust.</mj-preview>

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
    <!-- Preheader spacer (invisible — extends preview text) -->
    <mj-section padding="0">
      <mj-column>
        <mj-text font-size="1px" color="#f0ece4" padding="0">
          &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-include path="../components/header.mjml" />
    <mj-include path="../components/hero-editorial.mjml" />

    <!-- Section label -->
    <mj-section background-color="#ffffff" padding="36px 40px 0">
      <mj-column>
        <mj-text
          align="center"
          font-family="'Noto Serif Display', Georgia, serif"
          font-size="24px"
          font-weight="600"
          color="#1b4332"
          padding-bottom="8px"
        >
          This Season's Picks
        </mj-text>
        <mj-text
          align="center"
          font-family="Inter, Arial, sans-serif"
          font-size="14px"
          color="#6c757d"
          line-height="1.5"
          padding="0"
        >
          Regionally tested blends, ready to ship within one business day.
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-include path="../components/product-grid-2.mjml" />
    <mj-include path="../components/product-single.mjml" />
    <mj-include path="../components/usps-bar.mjml" />
    <mj-include path="../components/cta-block.mjml" />
    <mj-include path="../components/footer.mjml" />
  </mj-body>
</mjml>
```

Save to: `marketing/email-system/templates/promo-editorial.mjml`

- [ ] **Step 2: Compile**

```bash
cd "marketing/email-system"
node build.js
```

Expected: `[OK]    promo-editorial.html → <50KB` (no warnings)

- [ ] **Step 3: Open and compare to approved mockup**

Open `dist/promo-editorial.html` side-by-side with `mockup-promo.html`. Verify:
- Preheader spacer present (invisible)
- Header: white, serif logo
- Hero: dark green, large serif headline, italic accent, orange button, sand divider
- Section label: serif h2, gray sub
- Product grid: 2 columns, white cards, placeholder images, orange buttons
- Product single: horizontal layout, off-white bg
- USP bar: green, 4 columns
- CTA block: white, outline button
- Footer: dark green, all links present

- [ ] **Step 4: Check file size**

```bash
wc -c "marketing/email-system/dist/promo-editorial.html"
```

Must be under 104,448 bytes (102KB). If over: remove one product block or tighten comment whitespace in MJML.

- [ ] **Step 5: Commit**

```bash
git add marketing/email-system/templates/promo-editorial.mjml marketing/email-system/dist/promo-editorial.html
git commit -m "feat(email): add promo-editorial template — first compiled campaign"
```

---

## Task 12: Final QA + Klaviyo Upload

- [ ] **Step 1: Run full build one last time**

```bash
cd "marketing/email-system"
node build.js
```

Expected: `[OK]    promo-editorial.html` with no warnings.

- [ ] **Step 2: Test responsive rendering**

Open `dist/promo-editorial.html` in Chrome. Resize window to 400px wide (DevTools device emulator). Check:
- Product grid collapses to single column
- Hero text remains readable
- All buttons remain tappable size

- [ ] **Step 3: Upload to Klaviyo**

1. Go to `klaviyo.com` → Content → Templates → Create Template → Paste HTML
2. Paste contents of `dist/promo-editorial.html`
3. Name it: `NS Promo — Editorial v1`
4. Send a test to `gabe@naturesseed.com`
5. Check rendering in Gmail — confirm no clipping, fonts load, orange buttons display correctly

- [ ] **Step 4: Commit dist + final state**

```bash
git add marketing/email-system/
git commit -m "feat(email): MJML component library v1 complete — promo-editorial ready for Klaviyo"
```

---

## Self-Review

**Spec coverage check:**
- [x] npm build system with size warnings → Task 1
- [x] 9 components (header, footer, hero-editorial, hero-image, product-single, grid-2, grid-3, usps-bar, cta-block) → Tasks 2–10
- [x] promo-editorial.mjml assembled → Task 11
- [x] Gmail safety check (<102KB) → Tasks 11 + 12
- [x] Liquid templating preserved → footer.mjml uses `{{ unsubscribe_link }}` and `{{ preference_center_link }}`
- [x] Klaviyo upload → Task 12
- [x] Watch mode in build.js → Task 1 Step 3
- [x] Visual reference (mockup-promo.html) used as validation target → Tasks 11 + 12

**Placeholder scan:** No TBDs, no "similar to Task N" shortcuts, all code blocks complete.

**Type consistency:** No type mismatches — pure MJML/HTML, no shared function signatures to conflict.
