# Klaviyo Email Design — Nature's Seed
> Email creation guide for all Klaviyo CODE templates. Reference before building any email template.

---

## Template Type
Always use `editor_type: "CODE"` when creating templates via API (`POST /api/templates/`).
Never use SYSTEM_DRAGGABLE — those are flow-embedded and cannot be updated via API.

---

## Design Tokens (Email-Safe)

### Colors
| Token | Hex | Usage |
|-------|-----|-------|
| Primary green | `#2d6a4f` | Brand trust, headers, borders, soft CTAs |
| CTA orange | `#C96A2E` | ALL conversion/purchase buttons — NEVER swap with green |
| Dark text | `#1a1a1a` | Body copy |
| Medium text | `#555555` | Secondary copy, captions |
| Light text | `#888888` | Fine print, timestamps |
| Section bg | `#f8f9fa` | Alternating section backgrounds |
| White | `#ffffff` | Primary email background |
| Border | `#dee2e6` | Dividers, card borders |
| Green accent bg | `#e8f5e9` | Callout boxes, tip sections |

### Rule: Green = trust/brand. Orange = action/buy. NEVER swap.

### Typography (Email-Safe Stacks)
```
Headings:  Georgia, 'Times New Roman', serif
           (Noto Serif Display fallback — loads where Google Fonts supported)
Body:      Arial, 'Helvetica Neue', Helvetica, sans-serif
           (Inter fallback — loads where Google Fonts supported)
```

### Font Sizes
| Use | Size | Weight |
|-----|------|--------|
| H1 (hero headline) | 28–32px | bold |
| H2 (section head) | 22–24px | bold |
| H3 (card title) | 18px | bold |
| Body copy | 16px | normal |
| Small / caption | 14px | normal |
| Fine print | 12px | normal |

### Spacing
- Email max-width: **600px**
- Section padding: **32px 24px** (top/bottom, left/right)
- Card padding: **20px**
- Button padding: **14px 28px**

---

## Layout Rules (Email Client Compatibility)

### Required
- **Table-based layouts** — no CSS Grid, no Flexbox
- **Inline styles** — no `<style>` blocks (some clients strip them)
- **100% width tables** with `max-width: 600px` on outer wrapper
- **`border-collapse: collapse`** on all tables
- **`cellpadding="0" cellspacing="0"`** on all tables
- **`display: block`** on all `<img>` tags to kill phantom spacing
- **`mso-line-height-rule: exactly`** on paragraphs for Outlook line-height

### Forbidden
- CSS Grid
- Flexbox
- Box shadows (not supported in Outlook)
- CSS variables / custom properties
- `calc()` in inline styles
- SVG images
- `position: absolute/fixed`

### Images
- Always include `width` and `height` attributes
- Always include `alt` text
- Use `display: block` inline style
- Link all images to relevant pages
- Use hosted CloudFront URLs from the content library (see Image Library below)

---

## HTML Email Base Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>{{ subject }}</title>
<style>
  /* Limited global styles — inline everything critical */
  body { margin: 0; padding: 0; background-color: #f4f4f4; }
  img { border: 0; outline: none; text-decoration: none; }
  a { color: #C96A2E; }
  @media only screen and (max-width: 600px) {
    .email-wrapper { width: 100% !important; }
    .mobile-padding { padding: 20px 16px !important; }
    .mobile-stack { display: block !important; width: 100% !important; }
    .mobile-full { width: 100% !important; }
    .mobile-hide { display: none !important; }
  }
</style>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f4;">

<!-- OUTER WRAPPER -->
<table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%"
       style="background-color:#f4f4f4;">
  <tr>
    <td align="center" style="padding:20px 0;">

      <!-- EMAIL CONTAINER (600px max) -->
      <table class="email-wrapper" role="presentation" border="0" cellpadding="0" cellspacing="0"
             width="600" style="max-width:600px;background-color:#ffffff;border-radius:4px;
             overflow:hidden;border:1px solid #dee2e6;">

        <!-- HEADER -->
        [HEADER_COMPONENT]

        <!-- HERO IMAGE -->
        [HERO_COMPONENT]

        <!-- BODY SECTIONS -->
        [BODY_SECTIONS]

        <!-- FOOTER -->
        [FOOTER_COMPONENT]

      </table>

    </td>
  </tr>
</table>

</body>
</html>
```

---

## Reusable Components

### HEADER — Logo Bar
```html
<!-- HEADER -->
<tr>
  <td align="center" style="background-color:#2d6a4f;padding:16px 24px;">
    <a href="https://www.naturesseed.com" target="_blank">
      <img src="https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/52272625-f380-43c4-a395-7a40eaef3ff5.png"
           alt="Nature's Seed" width="180" height="45" style="display:block;border:0;">
    </a>
  </td>
</tr>
```
Note: Logo is white on `#2d6a4f` green — perfect contrast.

### HERO IMAGE (600x250)
```html
<!-- HERO -->
<tr>
  <td>
    <a href="{{ CTA_URL }}" target="_blank">
      <img src="{{ HERO_IMAGE_URL }}" alt="{{ HERO_ALT }}"
           width="600" height="250" style="display:block;width:100%;height:auto;border:0;">
    </a>
  </td>
</tr>
```

### HEADLINE + BODY COPY SECTION
```html
<!-- BODY COPY -->
<tr>
  <td style="padding:32px 24px;background-color:#ffffff;">
    <h1 style="margin:0 0 16px 0;font-family:Georgia,'Times New Roman',serif;
                font-size:28px;font-weight:bold;color:#1a1a1a;line-height:1.3;">
      {{ HEADLINE }}
    </h1>
    <p style="margin:0 0 16px 0;font-family:Arial,'Helvetica Neue',sans-serif;
               font-size:16px;color:#555555;line-height:1.6;mso-line-height-rule:exactly;">
      {{ BODY_COPY }}
    </p>
  </td>
</tr>
```

### CTA BUTTON (Orange — Conversion)
```html
<!-- CTA BUTTON -->
<tr>
  <td align="center" style="padding:8px 24px 32px 24px;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0">
      <tr>
        <td align="center" style="background-color:#C96A2E;border-radius:4px;">
          <a href="{{ CTA_URL }}" target="_blank"
             style="display:inline-block;padding:14px 32px;font-family:Arial,'Helvetica Neue',sans-serif;
                    font-size:16px;font-weight:bold;color:#ffffff;text-decoration:none;
                    letter-spacing:0.5px;">
            {{ CTA_TEXT }}
          </a>
        </td>
      </tr>
    </table>
  </td>
</tr>
```

### DIVIDER
```html
<tr>
  <td style="padding:0 24px;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td style="border-top:1px solid #dee2e6;font-size:0;line-height:0;">&nbsp;</td>
      </tr>
    </table>
  </td>
</tr>
```

### CALLOUT BOX (Green — Tips / Info)
```html
<!-- CALLOUT BOX -->
<tr>
  <td style="padding:0 24px 24px 24px;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%"
           style="background-color:#e8f5e9;border-left:4px solid #2d6a4f;border-radius:0 4px 4px 0;">
      <tr>
        <td style="padding:16px 20px;">
          <p style="margin:0 0 6px 0;font-family:Georgia,'Times New Roman',serif;
                     font-size:15px;font-weight:bold;color:#2d6a4f;">
            {{ CALLOUT_TITLE }}
          </p>
          <p style="margin:0;font-family:Arial,'Helvetica Neue',sans-serif;
                     font-size:15px;color:#555555;line-height:1.5;">
            {{ CALLOUT_TEXT }}
          </p>
        </td>
      </tr>
    </table>
  </td>
</tr>
```

### 2-COLUMN PRODUCT CARD ROW
```html
<!-- 2-COL PRODUCT CARDS -->
<tr>
  <td style="padding:0 24px 24px 24px;background-color:#f8f9fa;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <!-- Card 1 -->
        <td class="mobile-stack" width="48%" valign="top"
            style="background-color:#ffffff;border:1px solid #dee2e6;border-radius:4px;padding:16px;">
          <a href="{{ PRODUCT_1_URL }}" target="_blank">
            <img src="{{ PRODUCT_1_IMG }}" alt="{{ PRODUCT_1_ALT }}"
                 width="100%" height="auto" style="display:block;border:0;border-radius:4px;">
          </a>
          <p style="margin:12px 0 4px 0;font-family:Georgia,'Times New Roman',serif;
                     font-size:15px;font-weight:bold;color:#1a1a1a;">{{ PRODUCT_1_NAME }}</p>
          <p style="margin:0 0 12px 0;font-family:Arial,'Helvetica Neue',sans-serif;
                     font-size:14px;color:#888888;">{{ PRODUCT_1_PRICE }}</p>
          <a href="{{ PRODUCT_1_URL }}" target="_blank"
             style="display:inline-block;padding:10px 20px;background-color:#C96A2E;color:#ffffff;
                    font-family:Arial,'Helvetica Neue',sans-serif;font-size:14px;font-weight:bold;
                    text-decoration:none;border-radius:4px;">Shop Now</a>
        </td>
        <!-- Spacer -->
        <td width="4%">&nbsp;</td>
        <!-- Card 2 -->
        <td class="mobile-stack" width="48%" valign="top"
            style="background-color:#ffffff;border:1px solid #dee2e6;border-radius:4px;padding:16px;">
          <a href="{{ PRODUCT_2_URL }}" target="_blank">
            <img src="{{ PRODUCT_2_IMG }}" alt="{{ PRODUCT_2_ALT }}"
                 width="100%" height="auto" style="display:block;border:0;border-radius:4px;">
          </a>
          <p style="margin:12px 0 4px 0;font-family:Georgia,'Times New Roman',serif;
                     font-size:15px;font-weight:bold;color:#1a1a1a;">{{ PRODUCT_2_NAME }}</p>
          <p style="margin:0 0 12px 0;font-family:Arial,'Helvetica Neue',sans-serif;
                     font-size:14px;color:#888888;">{{ PRODUCT_2_PRICE }}</p>
          <a href="{{ PRODUCT_2_URL }}" target="_blank"
             style="display:inline-block;padding:10px 20px;background-color:#C96A2E;color:#ffffff;
                    font-family:Arial,'Helvetica Neue',sans-serif;font-size:14px;font-weight:bold;
                    text-decoration:none;border-radius:4px;">Shop Now</a>
        </td>
      </tr>
    </table>
  </td>
</tr>
```

### 3-COLUMN PRODUCT ROW
```html
<!-- 3-COL PRODUCT ROW -->
<tr>
  <td style="padding:0 24px 24px 24px;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td class="mobile-stack" width="31%" align="center" valign="top" style="padding:8px;">
          <a href="{{ URL_1 }}"><img src="{{ IMG_1 }}" alt="{{ ALT_1 }}" width="170" height="130"
             style="display:block;border:0;border-radius:4px;width:100%;height:auto;"></a>
          <p style="margin:8px 0 0;font-family:Georgia,'Times New Roman',serif;font-size:14px;
                     font-weight:bold;color:#1a1a1a;text-align:center;">{{ LABEL_1 }}</p>
        </td>
        <td class="mobile-stack" width="31%" align="center" valign="top" style="padding:8px;">
          <a href="{{ URL_2 }}"><img src="{{ IMG_2 }}" alt="{{ ALT_2 }}" width="170" height="130"
             style="display:block;border:0;border-radius:4px;width:100%;height:auto;"></a>
          <p style="margin:8px 0 0;font-family:Georgia,'Times New Roman',serif;font-size:14px;
                     font-weight:bold;color:#1a1a1a;text-align:center;">{{ LABEL_2 }}</p>
        </td>
        <td class="mobile-stack" width="31%" align="center" valign="top" style="padding:8px;">
          <a href="{{ URL_3 }}"><img src="{{ IMG_3 }}" alt="{{ ALT_3 }}" width="170" height="130"
             style="display:block;border:0;border-radius:4px;width:100%;height:auto;"></a>
          <p style="margin:8px 0 0;font-family:Georgia,'Times New Roman',serif;font-size:14px;
                     font-weight:bold;color:#1a1a1a;text-align:center;">{{ LABEL_3 }}</p>
        </td>
      </tr>
    </table>
  </td>
</tr>
```

### TRUST SIGNAL BAR
```html
<!-- TRUST BAR -->
<tr>
  <td style="background-color:#f8f9fa;padding:16px 24px;border-top:1px solid #dee2e6;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td align="center" width="33%" style="padding:0 8px;">
          <p style="margin:0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:13px;
                     color:#2d6a4f;font-weight:bold;text-align:center;">Free Shipping</p>
          <p style="margin:2px 0 0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:12px;
                     color:#888888;text-align:center;">Orders over $50</p>
        </td>
        <td align="center" width="33%" style="padding:0 8px;border-left:1px solid #dee2e6;border-right:1px solid #dee2e6;">
          <p style="margin:0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:13px;
                     color:#2d6a4f;font-weight:bold;text-align:center;">Expert Formulated</p>
          <p style="margin:2px 0 0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:12px;
                     color:#888888;text-align:center;">Since 1994</p>
        </td>
        <td align="center" width="33%" style="padding:0 8px;">
          <p style="margin:0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:13px;
                     color:#2d6a4f;font-weight:bold;text-align:center;">Satisfaction Guaranteed</p>
          <p style="margin:2px 0 0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:12px;
                     color:#888888;text-align:center;">No-hassle returns</p>
        </td>
      </tr>
    </table>
  </td>
</tr>
```

### COUPON CODE BLOCK
```html
<!-- COUPON BLOCK -->
<tr>
  <td style="padding:0 24px 24px;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%"
           style="border:2px dashed #C96A2E;border-radius:4px;background-color:#fff9f5;">
      <tr>
        <td align="center" style="padding:20px;">
          <p style="margin:0 0 6px;font-family:Arial,'Helvetica Neue',sans-serif;font-size:13px;
                     color:#888888;text-transform:uppercase;letter-spacing:1px;">Your Discount Code</p>
          <p style="margin:0 0 12px;font-family:Georgia,'Times New Roman',serif;font-size:28px;
                     font-weight:bold;color:#C96A2E;letter-spacing:3px;">{{ COUPON_CODE }}</p>
          <p style="margin:0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:13px;
                     color:#888888;">{{ EXPIRY_TEXT }}</p>
        </td>
      </tr>
    </table>
  </td>
</tr>
```

### SECTION HEADING (Gray BG)
```html
<!-- SECTION BG HEADING -->
<tr>
  <td style="background-color:#f8f9fa;padding:24px 24px 16px;border-top:1px solid #dee2e6;">
    <h2 style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:22px;
                font-weight:bold;color:#1a1a1a;">{{ SECTION_HEADING }}</h2>
  </td>
</tr>
```

---

## Image Library — Hosted CloudFront URLs

### Logo
| Asset | Size | URL |
|-------|------|-----|
| Nature's Seed logo | 200x50 | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/52272625-f380-43c4-a395-7a40eaef3ff5.png` |

### Hero Images (600x250)
| Asset | URL |
|-------|-----|
| Lawn Care Guide | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/22c78ad6-d44a-43cd-8ba2-5b32c70ff94d.png` |
| Pasture Care Guide | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/845c1936-86e5-4305-9a25-805777d0a648.png` |
| Wildflower Care Guide | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/de38d48a-ebc1-4fb5-ae92-daac513eb2c0.png` |
| Food Plot Care Guide | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/80ea08b1-f115-4680-8de4-630bfaa21564.png` |
| Clover Care Guide | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/72e2fe0e-ea7d-4d48-8ad8-c6be4be14216.png` |
| Cover Crop Care Guide | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/db37b90a-2da5-412f-981d-1379bc6300be.png` |
| Planting Care Guide | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/462d481f-3495-4687-8769-2d5b059a6a8b.png` |
| Micro Clover Lawn | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/9018b9e4-7f08-458d-b525-8e676caab940.png` |
| Pollinator Garden | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/a63d787e-61bb-4d6b-aa7f-f42c08b4e1d2.png` |
| Healthy Pasture Land | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/3bf10932-9545-4633-bccd-4735939fc56a.png` |
| We Miss You | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/60e2a54b-661f-459e-b663-c44ea1460c21.png` |
| Seasonal Planting Guide | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/925d4ab8-879a-4b95-870f-ae47a63b252b.png` |
| Spring Planting Season | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/f4ec96be-20fb-46b0-8b77-39795481e9b8.png` |
| Welcome to Nature's Seed | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/0446896b-3b77-4cce-941a-95b629e84656.png` (600x300) |
| Welcome to the Community | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/a9f93cf6-e4ab-421d-aa42-845814e72297.png` |
| More from Nature's Seed | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/8f062a86-4a7b-4ac3-a57e-1980d64c0d89.png` |

### Category Images (260x140)
| Asset | URL |
|-------|-----|
| Lawn | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/f9eb26e7-16ad-4c16-9f84-f5b05ed46aba.png` |
| Pasture | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/c43e7254-74d9-442c-a051-00e905cb24d5.png` |
| Wildflower | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/6f04f97f-4a17-4cb8-b471-073e7b3623e2.png` |
| Food Plot | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/e91f5270-1fef-442c-8b9a-90b55c53b983.png` |

### Product Images (260x180)
| Asset | URL |
|-------|-----|
| Premium Lawn Seed Blend | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/c9a09277-2cb0-4658-9b91-1ef8a7a9acbd.png` |
| Shade Tolerant Lawn Seed | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/11d16584-4ed0-4f35-a8b4-a5e6a5231910.png` |
| Pollinator Wildflower Mix | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/c1d9f1f6-1abf-4e2e-b0b8-37584108c5d7.png` |
| Regional Wildflower Blend | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/f16d4ca3-f24a-41b9-b66a-c145fe92ca89.png` |
| Whitetail Food Plot Mix | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/276fc1b2-51ad-4a7e-988b-82774fb6a2f7.png` |
| Year-Round Food Plot Blend | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/bf2a6fd9-71ed-475f-bcbd-f9f310bceb9a.png` |
| White Clover Seed | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/cc208015-810a-4d2f-bc70-af4f4cba02e3.png` |
| Winter Cover Crop Mix | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/7a5d6710-af79-493d-ba6f-971b606a4e5a.png` |

### Product Images (170x130) — 3-column rows
| Asset | URL |
|-------|-----|
| Premium Lawn Blend | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/16e5458d-a75f-4009-84e9-0ea9548edeb6.png` |
| Shade Lawn Mix | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/ff470b12-f9df-441c-b49a-58c630e2763d.png` |
| Drought Resistant Lawn | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/db70d0e6-1895-4ee0-bc04-8c301fa9883c.png` |
| Pollinator Mix | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/740e94c7-5a06-4b8e-8f58-d6af013b2b04.png` |
| Native Wildflower Mix | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/0b75a068-ffba-4e7f-8189-2528f74647bc.png` |
| Butterfly Garden Mix | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/7275841e-02e2-419a-bd58-7d0399341966.png` |
| Best-Selling Lawn Seed | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/5588e15d-5519-4198-ad0a-0ed3f2d945b4.png` |
| All-Purpose Pasture | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/3c96af9d-0ea6-440d-b794-718d0fbb11b9.png` |
| Hay Field Mix | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/0345ac15-b935-4450-a574-8737c70e57e7.png` |
| Cattle Grazing Mix | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/0bbb1d7a-90ce-49f0-9142-a552ee62bb5f.png` |

### VIP / Special Images (600x300)
| Asset | URL |
|-------|-----|
| Platinum VIP | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/f1b22701-c3e9-4f4e-a137-c514835e33f5.png` |
| Gold VIP | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/15a05a5d-8fdd-4b4f-90cf-c02aee3d036f.png` |
| Silver VIP | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/c18d792c-8f88-4ddc-a18d-6a332ce64cca.png` |

### Planting Aid Product (520x300)
| Asset | URL |
|-------|-----|
| Nature's Seed Planting Aid | `https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/60d8d9a6-39ec-4cc8-a9a5-5dcc2b7523b3.png` |

---

## Persona Image Selection Guide

| Persona | Hero Image | Product Images (3-col) |
|---------|-----------|----------------------|
| Lawn | Lawn Care Guide (600x250) | Premium Lawn Blend, Shade Lawn Mix, Drought Resistant Lawn |
| Pasture | Healthy Pasture Land (600x250) | All-Purpose Pasture, Hay Field Mix, Cattle Grazing Mix |
| Wildflower | Wildflower Care Guide (600x250) | Pollinator Mix, Native Wildflower Mix, Butterfly Garden Mix |
| Food Plot | Food Plot Care Guide (600x250) | Whitetail Food Plot Mix, Year-Round Food Plot Blend (260x180) |
| Clover | Clover Care Guide (600x250) | White Clover, Micro Clover (160x160) |
| Winback (any) | We Miss You (600x250) | Match to customer's last purchase category |

---

## Klaviyo Personalization Tags
```
{{ first_name|default:"there" }}             — Safe first name with fallback
{{ organization.name }}                       — "Nature's Seed"
{{ organization.website }}                    — https://www.naturesseed.com
{{ event.extra.order_id }}                    — WooCommerce order ID
{{ event.extra.line_items.0.product_name }}   — First item in order
{{ person.city }}                             — Customer city
{% if person.lawn_type %}...{% endif %}       — Conditional persona content
```

---

## Brand Voice Quick Rules (from natures-seed-brand skill)
- Direct and expert, never condescending
- Use "your lawn/pasture/field" — personal ownership language
- Avoid: "amazing", "incredible", "game-changer", corporate buzzwords
- Numbers and specifics beat adjectives: "covers 5,000 sq ft" not "great coverage"
- Urgency: specific timeframes ("48 hours", "This weekend") not vague ("soon")
- Coupon copy: always show savings in dollars, not just percent

---

## Template Checklist Before Publishing
- [ ] All images have width, height, and alt attributes
- [ ] All links open in `target="_blank"`
- [ ] All links use `https://`
- [ ] CTA button uses `#C96A2E` (orange), NOT green
- [ ] Subject line uses Klaviyo personalization tag
- [ ] Preview text is different from subject line (50–90 chars)
- [ ] Mobile responsive: no elements wider than 600px
- [ ] No box-shadows anywhere
- [ ] No CSS Grid or Flexbox
- [ ] All tables have `role="presentation"`
- [ ] Unsubscribe handled by Klaviyo footer (do not add manually)
