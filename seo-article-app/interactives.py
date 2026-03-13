"""
Interactive Element Builder for Nature's Seed articles.

Generates HTML/shortcode snippets for interactive elements that enhance
article engagement and SEO value.
"""

import json


def build_product_card(product):
    """Generate a product card HTML block for embedding in articles."""
    name = product.get("name", "")
    slug = product.get("slug", "")
    price = product.get("price", "")
    image_url = ""
    if product.get("images"):
        image_url = product["images"][0].get("src", "")
    short_desc = product.get("short_description", "").replace("<p>", "").replace("</p>", "")
    url = f"https://naturesseed.com/products/{slug}/"

    return f"""<div class="ns-product-card" style="border:1px solid #e2e8f0;border-radius:12px;padding:20px;margin:24px 0;display:flex;gap:20px;align-items:center;background:#f8faf8;">
  <div style="flex-shrink:0;width:120px;height:120px;">
    <img src="{image_url}" alt="{name}" style="width:100%;height:100%;object-fit:cover;border-radius:8px;" loading="lazy"/>
  </div>
  <div style="flex:1;">
    <h4 style="margin:0 0 8px;color:#2d5016;font-size:18px;">{name}</h4>
    <p style="margin:0 0 12px;color:#555;font-size:14px;line-height:1.5;">{short_desc[:150]}</p>
    <div style="display:flex;align-items:center;gap:16px;">
      <span style="font-size:20px;font-weight:700;color:#2d5016;">{"$" + price if price else ""}</span>
      <a href="{url}" style="background:#4a7c2e;color:#fff;padding:8px 20px;border-radius:6px;text-decoration:none;font-weight:600;font-size:14px;">View Product</a>
    </div>
  </div>
</div>"""


def build_comparison_table(items, columns):
    """Generate a comparison table HTML.

    items: list of dicts with column keys
    columns: list of {"key": "field_name", "label": "Display Name"}
    """
    header_cells = "".join(f'<th style="padding:12px 16px;background:#2d5016;color:#fff;text-align:left;font-weight:600;">{col["label"]}</th>' for col in columns)

    rows = []
    for i, item in enumerate(items):
        bg = "#f8faf8" if i % 2 == 0 else "#fff"
        cells = "".join(f'<td style="padding:10px 16px;border-bottom:1px solid #e2e8f0;">{item.get(col["key"], "—")}</td>' for col in columns)
        rows.append(f'<tr style="background:{bg};">{cells}</tr>')

    return f"""<div style="overflow-x:auto;margin:24px 0;">
<table style="width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
  <thead><tr>{header_cells}</tr></thead>
  <tbody>{"".join(rows)}</tbody>
</table>
</div>"""


def build_seeding_calculator():
    """Generate a seeding rate calculator HTML/JS widget."""
    return """<div class="ns-calculator" style="border:2px solid #4a7c2e;border-radius:12px;padding:24px;margin:24px 0;background:#f8faf8;">
  <h3 style="margin:0 0 16px;color:#2d5016;">Seeding Rate Calculator</h3>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
    <div>
      <label style="display:block;font-weight:600;margin-bottom:4px;color:#333;">Area (sq ft)</label>
      <input type="number" id="ns-calc-area" placeholder="e.g. 5000" style="width:100%;padding:10px;border:1px solid #ccc;border-radius:6px;font-size:16px;box-sizing:border-box;"/>
    </div>
    <div>
      <label style="display:block;font-weight:600;margin-bottom:4px;color:#333;">Seeding Rate (lbs/1000 sq ft)</label>
      <input type="number" id="ns-calc-rate" placeholder="e.g. 4" step="0.5" style="width:100%;padding:10px;border:1px solid #ccc;border-radius:6px;font-size:16px;box-sizing:border-box;"/>
    </div>
  </div>
  <button onclick="(function(){var a=parseFloat(document.getElementById('ns-calc-area').value);var r=parseFloat(document.getElementById('ns-calc-rate').value);if(!a||!r){document.getElementById('ns-calc-result').innerHTML='Please enter both values.';return;}var lbs=(a/1000)*r;document.getElementById('ns-calc-result').innerHTML='<strong>You need approximately '+lbs.toFixed(1)+' lbs of seed</strong><br><span style=\\'color:#666;font-size:14px;\\'>Based on '+a.toLocaleString()+' sq ft at '+r+' lbs per 1,000 sq ft</span>';})();" style="background:#4a7c2e;color:#fff;padding:12px 24px;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;width:100%;">Calculate</button>
  <div id="ns-calc-result" style="margin-top:16px;padding:16px;background:#fff;border-radius:6px;min-height:24px;text-align:center;font-size:18px;"></div>
</div>"""


def build_zone_map():
    """Generate a USDA hardiness zone reference widget."""
    return """<div class="ns-zone-map" style="border:1px solid #e2e8f0;border-radius:12px;padding:24px;margin:24px 0;background:#f8faf8;">
  <h3 style="margin:0 0 8px;color:#2d5016;">Find Your Growing Zone</h3>
  <p style="margin:0 0 16px;color:#666;">Enter your ZIP code to find the right seed for your region.</p>
  <div style="display:flex;gap:12px;">
    <input type="text" id="ns-zip" placeholder="ZIP Code" maxlength="5" pattern="[0-9]{5}" style="flex:1;padding:10px;border:1px solid #ccc;border-radius:6px;font-size:16px;"/>
    <button onclick="(function(){var z=document.getElementById('ns-zip').value;if(z.length!==5){document.getElementById('ns-zone-result').innerHTML='Please enter a valid 5-digit ZIP code.';return;}var zones={'0':'3-4','1':'4-5','2':'5-7','3':'7-9','4':'6-8','5':'5-7','6':'5-7','7':'7-9','8':'4-8','9':'5-10'};var first=z[0];var zone=zones[first]||'5-7';document.getElementById('ns-zone-result').innerHTML='<strong>Estimated USDA Zone: '+zone+'</strong><br><span style=\\'color:#666;font-size:14px;\\'>For exact zone, visit <a href=\\'https://planthardiness.ars.usda.gov/\\' target=\\'_blank\\' style=\\'color:#4a7c2e;\\'>USDA Plant Hardiness Zone Map</a></span>';})();" style="background:#4a7c2e;color:#fff;padding:10px 20px;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;">Look Up</button>
  </div>
  <div id="ns-zone-result" style="margin-top:16px;padding:12px;background:#fff;border-radius:6px;min-height:20px;"></div>
</div>"""


def build_faq_schema(faqs):
    """Generate FAQ schema markup (JSON-LD) from Q&A pairs."""
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [],
    }
    faq_html = '<div class="ns-faq" style="margin:32px 0;">\n<h2>Frequently Asked Questions</h2>\n'

    for faq in faqs:
        schema["mainEntity"].append({
            "@type": "Question",
            "name": faq["question"],
            "acceptedAnswer": {
                "@type": "Answer",
                "text": faq["answer"],
            },
        })
        faq_html += f"""<details style="border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin:8px 0;">
  <summary style="font-weight:600;cursor:pointer;color:#2d5016;">{faq["question"]}</summary>
  <p style="margin:12px 0 0;color:#555;line-height:1.6;">{faq["answer"]}</p>
</details>\n"""

    faq_html += "</div>\n"
    faq_html += f'<script type="application/ld+json">{json.dumps(schema, indent=2)}</script>'

    return faq_html


def build_callout_box(text, box_type="tip"):
    """Generate a callout/tip box."""
    colors = {
        "tip": {"bg": "#f0f9e8", "border": "#4a7c2e", "icon": "💡", "label": "Pro Tip"},
        "warning": {"bg": "#fff8e1", "border": "#f59e0b", "icon": "⚠️", "label": "Important"},
        "info": {"bg": "#e8f4fd", "border": "#2196F3", "icon": "ℹ️", "label": "Did You Know"},
    }
    style = colors.get(box_type, colors["tip"])

    return f"""<div style="border-left:4px solid {style['border']};background:{style['bg']};padding:16px 20px;margin:20px 0;border-radius:0 8px 8px 0;">
  <strong style="color:{style['border']};">{style['icon']} {style['label']}:</strong>
  <span style="color:#333;"> {text}</span>
</div>"""


def build_table_of_contents(headings):
    """Generate a table of contents from H2 headings."""
    toc = '<nav class="ns-toc" style="background:#f8faf8;border:1px solid #e2e8f0;border-radius:12px;padding:20px 24px;margin:24px 0;">\n'
    toc += '<h3 style="margin:0 0 12px;color:#2d5016;font-size:16px;">In This Article</h3>\n<ul style="margin:0;padding:0 0 0 20px;">\n'
    for h in headings:
        anchor = h.lower().replace(" ", "-").replace("?", "").replace(":", "")
        toc += f'<li style="margin:6px 0;"><a href="#{anchor}" style="color:#4a7c2e;text-decoration:none;">{h}</a></li>\n'
    toc += '</ul>\n</nav>'
    return toc
