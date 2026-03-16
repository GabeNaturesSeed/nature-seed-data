"""
Nature's Seed — March-May 2026 Campaign Creator
Creates all 55 campaigns as drafts in Klaviyo with HTML templates.
"""
import os
import sys
import json
import time
import requests
from datetime import datetime

# ─── Config ──────────────────────────────────────────────────────────────────
KLAVIYO_API_KEY = os.getenv("KLAVIYO_API", "pk_3e5eaeec142f867fd8fca1b1f7820852ad")
BASE_URL = "https://a.klaviyo.com/api"
HEADERS = {
    "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
    "Content-Type": "application/json",
    "revision": "2024-07-15",
}

# ─── Segment IDs (Starred Only) ─────────────────────────────────────────────
SEGMENTS = {
    # RFM
    "active_champions": "VtKptn",
    "champions": "RAQTca",
    "active_this_season": "RbGRqF",
    "new_customer": "T93fB3",
    "warm": "WdpJti",
    "at_risk": "RyASXF",
    "lapsed": "Sv5cSC",
    "dormant": "WjzuUj",
    # Engagement
    "E60D": "RbH7na",
    "E90D": "VduUfa",
    "NOT_E60D": "Y87Rfk",
    "NOT_E90D": "VirYfN",
    # Category
    "lawn": "Ra4637",
    "pasture": "T6TJd6",
    "wildflower": "TJpLMz",
    "other": "XJbjnv",
    # Regional
    "florida": "Tyumbj",
    "texas": "Vh7uqd",
    "california": "XTeFkg",
}

# Active RFM segments to exclude for Win Back targeting
ACTIVE_RFM = ["active_champions", "champions", "active_this_season", "new_customer", "warm"]
# Declining RFM segments to exclude for Spring Activation targeting
DECLINING_RFM = ["at_risk", "lapsed", "dormant"]

# ─── Image URLs ──────────────────────────────────────────────────────────────
LOGO_URL = "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/52272625-f380-43c4-a395-7a40eaef3ff5.png"
HERO_IMAGES = {
    "lawn": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/22c78ad6-d44a-43cd-8ba2-5b32c70ff94d.png",
    "pasture": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/845c1936-86e5-4305-9a25-805777d0a648.png",
    "wildflower": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/de38d48a-ebc1-4fb5-ae92-daac513eb2c0.png",
    "other": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/db37b90a-2da5-412f-981d-1379bc6300be.png",
    "clover": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/72e2fe0e-ea7d-4d48-8ad8-c6be4be14216.png",
    "winback": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/60e2a54b-661f-459e-b663-c44ea1460c21.png",
    "spring": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/f4ec96be-20fb-46b0-8b77-39795481e9b8.png",
    "vip": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/f1b22701-c3e9-4f4e-a137-c514835e33f5.png",
    "cover_crop": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/db37b90a-2da5-412f-981d-1379bc6300be.png",
    "florida": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/de38d48a-ebc1-4fb5-ae92-daac513eb2c0.png",
    "food_plot": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/80ea08b1-f115-4680-8de4-630bfaa21564.png",
    "planting": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/462d481f-3495-4687-8769-2d5b059a6a8b.png",
    "earth_day": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/925d4ab8-879a-4b95-870f-ae47a63b252b.png",
    "memorial_day": "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/f4ec96be-20fb-46b0-8b77-39795481e9b8.png",
}

PRODUCT_IMAGES_3COL = {
    "lawn": [
        ("Premium Lawn Blend", "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/16e5458d-a75f-4009-84e9-0ea9548edeb6.png", "https://www.naturesseed.com/products/grass-seed/"),
        ("Shade Lawn Mix", "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/ff470b12-f9df-441c-b49a-58c630e2763d.png", "https://www.naturesseed.com/products/grass-seed/"),
        ("Drought Resistant Lawn", "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/db70d0e6-1895-4ee0-bc04-8c301fa9883c.png", "https://www.naturesseed.com/products/grass-seed/"),
    ],
    "pasture": [
        ("All-Purpose Pasture", "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/3c96af9d-0ea6-440d-b794-718d0fbb11b9.png", "https://www.naturesseed.com/products/pasture-seed/"),
        ("Hay Field Mix", "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/0345ac15-b935-4450-a574-8737c70e57e7.png", "https://www.naturesseed.com/products/pasture-seed/"),
        ("Cattle Grazing Mix", "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/0bbb1d7a-90ce-49f0-9142-a552ee62bb5f.png", "https://www.naturesseed.com/products/pasture-seed/"),
    ],
    "wildflower": [
        ("Pollinator Mix", "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/740e94c7-5a06-4b8e-8f58-d6af013b2b04.png", "https://www.naturesseed.com/products/wildflower-seed/"),
        ("Native Wildflower Mix", "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/0b75a068-ffba-4e7f-8189-2528f74647bc.png", "https://www.naturesseed.com/products/wildflower-seed/"),
        ("Butterfly Garden Mix", "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/7275841e-02e2-419a-bd58-7d0399341966.png", "https://www.naturesseed.com/products/wildflower-seed/"),
    ],
    "other": [
        ("White Clover Seed", "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/cc208015-810a-4d2f-bc70-af4f4cba02e3.png", "https://www.naturesseed.com/products/clover-seed/"),
        ("Winter Cover Crop Mix", "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/7a5d6710-af79-493d-ba6f-971b606a4e5a.png", "https://www.naturesseed.com/products/cover-crop-seed/"),
        ("Whitetail Food Plot", "https://d3k81ch9hvuctc.cloudfront.net/company/H627hn/images/276fc1b2-51ad-4a7e-988b-82774fb6a2f7.png", "https://www.naturesseed.com/products/food-plot-seed/"),
    ],
}

CATEGORY_URLS = {
    "lawn": "https://www.naturesseed.com/products/grass-seed/",
    "pasture": "https://www.naturesseed.com/products/pasture-seed/",
    "wildflower": "https://www.naturesseed.com/products/wildflower-seed/",
    "other": "https://www.naturesseed.com/products/",
}

CATEGORY_LABELS = {
    "lawn": "Lawn Seed",
    "pasture": "Pasture Seed",
    "wildflower": "Wildflower Seed",
    "other": "Specialty Seed",
}


# ─── HTML Template Builders ──────────────────────────────────────────────────

def _header():
    return f'''<tr>
  <td align="center" style="background-color:#2d6a4f;padding:16px 24px;">
    <a href="https://www.naturesseed.com" target="_blank">
      <img src="{LOGO_URL}" alt="Nature's Seed" width="180" height="45" style="display:block;border:0;">
    </a>
  </td>
</tr>'''


def _hero(img_url, alt, link="https://www.naturesseed.com"):
    return f'''<tr>
  <td>
    <a href="{link}" target="_blank">
      <img src="{img_url}" alt="{alt}" width="600" height="250" style="display:block;width:100%;height:auto;border:0;">
    </a>
  </td>
</tr>'''


def _body(headline, body_copy):
    return f'''<tr>
  <td style="padding:32px 24px;background-color:#ffffff;">
    <h1 style="margin:0 0 16px 0;font-family:Georgia,'Times New Roman',serif;font-size:28px;font-weight:bold;color:#1a1a1a;line-height:1.3;">
      {headline}
    </h1>
    <p style="margin:0 0 16px 0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:16px;color:#555555;line-height:1.6;mso-line-height-rule:exactly;">
      {body_copy}
    </p>
  </td>
</tr>'''


def _cta(text, url):
    return f'''<tr>
  <td align="center" style="padding:8px 24px 32px 24px;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0">
      <tr>
        <td align="center" style="background-color:#C96A2E;border-radius:4px;">
          <a href="{url}" target="_blank"
             style="display:inline-block;padding:14px 32px;font-family:Arial,'Helvetica Neue',sans-serif;
                    font-size:16px;font-weight:bold;color:#ffffff;text-decoration:none;letter-spacing:0.5px;">
            {text}
          </a>
        </td>
      </tr>
    </table>
  </td>
</tr>'''


def _callout(title, text):
    return f'''<tr>
  <td style="padding:0 24px 24px 24px;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%"
           style="background-color:#e8f5e9;border-left:4px solid #2d6a4f;border-radius:0 4px 4px 0;">
      <tr>
        <td style="padding:16px 20px;">
          <p style="margin:0 0 6px 0;font-family:Georgia,'Times New Roman',serif;font-size:15px;font-weight:bold;color:#2d6a4f;">
            {title}
          </p>
          <p style="margin:0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:15px;color:#555555;line-height:1.5;">
            {text}
          </p>
        </td>
      </tr>
    </table>
  </td>
</tr>'''


def _coupon(code, expiry_text):
    return f'''<tr>
  <td style="padding:0 24px 24px;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%"
           style="border:2px dashed #C96A2E;border-radius:4px;background-color:#fff9f5;">
      <tr>
        <td align="center" style="padding:20px;">
          <p style="margin:0 0 6px;font-family:Arial,'Helvetica Neue',sans-serif;font-size:13px;color:#888888;text-transform:uppercase;letter-spacing:1px;">Your Discount Code</p>
          <p style="margin:0 0 12px;font-family:Georgia,'Times New Roman',serif;font-size:28px;font-weight:bold;color:#C96A2E;letter-spacing:3px;">{code}</p>
          <p style="margin:0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:13px;color:#888888;">{expiry_text}</p>
        </td>
      </tr>
    </table>
  </td>
</tr>'''


def _products_3col(category):
    products = PRODUCT_IMAGES_3COL.get(category, PRODUCT_IMAGES_3COL["other"])
    cols = ""
    for name, img, url in products:
        cols += f'''<td class="mobile-stack" width="31%" align="center" valign="top" style="padding:8px;">
          <a href="{url}" target="_blank"><img src="{img}" alt="{name}" width="170" height="130"
             style="display:block;border:0;border-radius:4px;width:100%;height:auto;"></a>
          <p style="margin:8px 0 0;font-family:Georgia,'Times New Roman',serif;font-size:14px;font-weight:bold;color:#1a1a1a;text-align:center;">{name}</p>
        </td>'''
    return f'''<tr>
  <td style="padding:0 24px 24px 24px;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
      <tr>{cols}</tr>
    </table>
  </td>
</tr>'''


def _trust_bar():
    return '''<tr>
  <td style="background-color:#f8f9fa;padding:16px 24px;border-top:1px solid #dee2e6;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td align="center" width="33%" style="padding:0 8px;">
          <p style="margin:0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:13px;color:#2d6a4f;font-weight:bold;text-align:center;">Free Shipping</p>
          <p style="margin:2px 0 0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:12px;color:#888888;text-align:center;">Orders over $75</p>
        </td>
        <td align="center" width="33%" style="padding:0 8px;border-left:1px solid #dee2e6;border-right:1px solid #dee2e6;">
          <p style="margin:0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:13px;color:#2d6a4f;font-weight:bold;text-align:center;">Expert Formulated</p>
          <p style="margin:2px 0 0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:12px;color:#888888;text-align:center;">Since 1994</p>
        </td>
        <td align="center" width="33%" style="padding:0 8px;">
          <p style="margin:0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:13px;color:#2d6a4f;font-weight:bold;text-align:center;">Satisfaction Guaranteed</p>
          <p style="margin:2px 0 0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:12px;color:#888888;text-align:center;">No-hassle returns</p>
        </td>
      </tr>
    </table>
  </td>
</tr>'''


def _footer():
    return '''<tr>
  <td style="background-color:#2d6a4f;padding:24px;text-align:center;">
    <p style="margin:0 0 8px;font-family:Arial,'Helvetica Neue',sans-serif;font-size:14px;color:#ffffff;">
      Questions? <a href="mailto:customercare@naturesseed.com" style="color:#ffffff;text-decoration:underline;">customercare@naturesseed.com</a> | 801-531-1456
    </p>
    <p style="margin:0 0 8px;font-family:Arial,'Helvetica Neue',sans-serif;font-size:12px;color:#a8d5ba;">
      Nature's Seed | 1697 W 2100 N, Lehi, UT 84043
    </p>
    <p style="margin:0;font-family:Arial,'Helvetica Neue',sans-serif;font-size:12px;color:#a8d5ba;">
      {% unsubscribe 'Unsubscribe' %} | {% manage_preferences 'Manage Preferences' %}
    </p>
  </td>
</tr>'''


def _wrap(inner_rows):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>Nature\'s Seed</title>
<style>
  body {{ margin: 0; padding: 0; background-color: #f4f4f4; }}
  img {{ border: 0; outline: none; text-decoration: none; }}
  a {{ color: #C96A2E; }}
  @media only screen and (max-width: 600px) {{
    .email-wrapper {{ width: 100% !important; }}
    .mobile-padding {{ padding: 20px 16px !important; }}
    .mobile-stack {{ display: block !important; width: 100% !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f4;">
<table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:#f4f4f4;">
  <tr>
    <td align="center" style="padding:20px 0;">
      <table class="email-wrapper" role="presentation" border="0" cellpadding="0" cellspacing="0"
             width="600" style="max-width:600px;background-color:#ffffff;border-radius:4px;overflow:hidden;border:1px solid #dee2e6;">
        {inner_rows}
      </table>
    </td>
  </tr>
</table>
</body>
</html>'''


# ─── Template Content Generators ─────────────────────────────────────────────

WIN_BACK_CONTENT = {
    1: {
        "headline": "Spring Is Here \u2014 Your {category} Needs You",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>It's been a while since your last order, and we wanted to share what's new this spring. The planting window is open, and your {category_lower} could use some attention.<br><br>Here are a few seasonal tips to help you get the most out of this growing season:",
        "callout_title": "Spring {category} Tip",
        "callout_text": "{tip}",
        "cta": "Browse {category}",
        "subject": "Your spring {category_lower} checklist",
    },
    2: {
        "headline": "Your Spring Planting Checklist",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>Spring planting season is in full swing. Whether you're starting fresh or maintaining what you've got, here's a practical checklist to make sure you're set up for success this year.",
        "callout_title": "Don't Skip This Step",
        "callout_text": "{tip}",
        "cta": "Shop {category}",
        "subject": "Spring planting checklist for your {category_lower}",
    },
    3: {
        "headline": "Did You Know? {category} Facts",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>We're seed scientists, and we love sharing what we've learned. Here are some surprising facts about {category_lower} that most people don't know \u2014 and how they can help you grow better results.",
        "callout_title": "Expert Insight",
        "callout_text": "{tip}",
        "cta": "Explore {category}",
        "subject": "3 things you didn't know about {category_lower}",
    },
    4: {
        "headline": "Common {category} Mistakes to Avoid",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>After 30+ years in the seed business, we've seen the same mistakes come up again and again. Here's how to avoid the most common ones \u2014 and set yourself up for a great season.",
        "callout_title": "Avoid This Mistake",
        "callout_text": "{tip}",
        "cta": "Shop {category}",
        "subject": "Don't make these {category_lower} mistakes",
    },
    5: {
        "headline": "Last Call for Spring Planting",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>The spring planting window is closing soon for many regions. If you've been thinking about planting {category_lower} this year, now is the time to act \u2014 before the heat sets in.",
        "callout_title": "Planting Window Alert",
        "callout_text": "Most regions have 2-4 weeks left for optimal spring {category_lower} planting. Check your USDA zone for exact timing.",
        "cta": "Shop {category} Now",
        "subject": "Last chance for spring {category_lower} planting",
    },
}

SPRING_ACTIVATION_CONTENT = {
    1: {
        "headline": "Your Spring {category} Guide",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>Spring planting season is here, and we've put together a region-specific guide to help you get the best results with your {category_lower}. From soil prep to seeding rates, here's everything you need to know.",
        "callout_title": "Planting Tip",
        "callout_text": "{tip}",
        "cta": "Shop {category}",
        "subject": "Your spring {category_lower} planting guide",
    },
    2: {
        "headline": "See What Others Planted Last Spring",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>Nothing beats seeing real results. Here are some of the best {category_lower} transformations from our customers last season \u2014 and how they did it.",
        "callout_title": "Customer Spotlight",
        "callout_text": "\"I was amazed at how quickly my {category_lower} established. Nature's Seed made it easy.\" \u2014 Verified Customer",
        "cta": "Get Started",
        "subject": "Real results from Nature's Seed customers",
    },
    3: {
        "headline": "Plant Something That Matters",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>This Earth Day, we're celebrating the people who plant with purpose. Every {category_lower} you grow supports healthier soil, cleaner air, and stronger ecosystems. Here's how you can make an impact.",
        "callout_title": "Earth Day Impact",
        "callout_text": "{tip}",
        "cta": "Shop {category}",
        "subject": "Plant something that matters this Earth Day",
    },
    4: {
        "headline": "Still Time to Plant {category}",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>Good news \u2014 there's still time to get your {category_lower} in the ground this spring. Here are the zone-specific windows you need to know about, plus our top picks for the season.",
        "callout_title": "Planting Window",
        "callout_text": "Most regions still have 3-6 weeks of ideal planting conditions for {category_lower}. Don't wait too long \u2014 soil temps are key.",
        "cta": "Shop {category}",
        "subject": "Still time to plant {category_lower} this spring",
    },
    5: {
        "headline": "Your Neighbors Are Planting",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>Spring is peak season, and orders for {category_lower} are surging across the country. Here's what's trending in your region \u2014 and why so many people are planting right now.",
        "callout_title": "Trending Now",
        "callout_text": "{category} orders are up 40% this month compared to last year. Join thousands of growers who are planting with confidence.",
        "cta": "Shop {category}",
        "subject": "See what's trending in {category_lower}",
    },
}

VIP_CONTENT = {
    1: {
        "headline": "We Want to Hear From You",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>As one of our most valued customers, your opinion matters to us. We're exploring the idea of creating native seed categories for specific states \u2014 and we'd love your input.<br><br><strong>Would you want us to create a native seed category for your state?</strong><br><br>Just reply to this email and tell us which state you'd like to see. We read every single response.",
        "cta_text": "Reply to This Email",
        "subject": "Quick question from Nature's Seed",
    },
    2: {
        "headline": "How Can We Help?",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>We know that every property is different, and sometimes you need something specific. Is there a seed or product you've been looking for that we don't carry? A project you need help with?<br><br><strong>Reply to this email \u2014 we read every single one.</strong><br><br>Our seed specialists can help with custom recommendations, bulk orders, and planting advice for your specific region.",
        "cta_text": "Reply to This Email",
        "subject": "Is there something we can help with?",
    },
    3: {
        "headline": "Show Us What You've Grown",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>We'd love to see what you've accomplished with Nature's Seed. Whether it's a lush lawn, thriving pasture, or blooming wildflower field \u2014 we want to see it.<br><br><strong>Reply to this email with a photo of your results.</strong> We might feature you on our website or social media!",
        "cta_text": "Reply With a Photo",
        "subject": "We'd love to see your results",
    },
    4: {
        "headline": "What Do You Want to See Next?",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>We're already planning our fall lineup, and we want your input. What products, categories, or seed types would make your life easier?<br><br><strong>Reply to this email with your wish list.</strong> Your feedback directly influences what we stock next season.",
        "cta_text": "Reply With Your Wish List",
        "subject": "Help us plan our fall lineup",
    },
    5: {
        "headline": "Any Requests Before Summer?",
        "body": "Hey {{{{ first_name|default:\"there\" }}}},<br><br>Summer's around the corner, and before we shift gears, we want to make sure you have everything you need. Whether it's a recommendation, a bulk order, or a custom mix \u2014 we're here to help.<br><br><strong>Reply to this email and let us know what you need.</strong> Our team will get back to you within 24 hours.",
        "cta_text": "Reply to This Email",
        "subject": "Anything you need before summer?",
    },
}

CATEGORY_TIPS = {
    "lawn": [
        "For spring seeding, soil temps should be 50-65\u00b0F consistently. Morning is best for seed application when dew is still on the ground.",
        "Mow your existing lawn to 1.5 inches before overseeding. This gives new seed better soil contact and light access.",
        "A single lawn can produce enough oxygen for a family of four. Healthy grass also filters 12 million tons of dust and dirt annually.",
        "The #1 mistake: planting too deep. Lawn seed needs light to germinate. Rake lightly \u2014 don't bury it. 1/4 inch max.",
    ],
    "pasture": [
        "Spring frost-seeding works great for pasture renovation. Broadcast seed onto frozen ground in late winter and let freeze-thaw cycles work it in.",
        "Soil test before you seed. Pasture grasses need a pH between 6.0-7.0 for optimal growth. Lime if needed \u2014 it takes 3-6 months to adjust.",
        "One acre of well-managed pasture can sequester 1-3 tons of carbon per year. Rotational grazing doubles that capacity.",
        "Over-grazing kills root systems. Never graze below 3 inches. Rest pastures 30-45 days between grazing cycles for full recovery.",
    ],
    "wildflower": [
        "Most wildflower seeds need cold stratification. If you haven't winter-sown, plant now while soil temps are still cool.",
        "Don't fertilize wildflower beds. Most native species prefer lean soil. Fertilizer favors weeds over wildflowers.",
        "A single wildflower meadow can support 10x more pollinators than a maintained lawn. Native species attract specialist bees that honeybees can't replace.",
        "Planting depth matters: most wildflower seeds should be surface-sown or pressed in, not buried. They need light to germinate.",
    ],
    "other": [
        "Cover crops planted now will be ready to terminate before summer cash crops. Crimson clover and winter peas are excellent spring choices.",
        "Food plots planted in April-May give deer browse all summer. Combine clover with chicory for a perennial plot that lasts 3-5 years.",
        "Cover crops can add 50-150 lbs of nitrogen per acre, reducing fertilizer costs by 30-50%. Legume mixes are the most efficient.",
        "Don't wait too long to terminate cover crops. Let them flower but cut before seed set to prevent volunteer problems in your next planting.",
    ],
}


def build_winback_html(category, cycle):
    content = WIN_BACK_CONTENT[cycle]
    cat_label = CATEGORY_LABELS[category]
    cat_lower = cat_label.lower()
    tip_idx = min(cycle - 1, len(CATEGORY_TIPS[category]) - 1)
    tip = CATEGORY_TIPS[category][tip_idx]

    headline = content["headline"].format(category=cat_label)
    body_text = content["body"].format(category_lower=cat_lower)
    callout_title = content["callout_title"].format(category=cat_label)
    callout_text = content["callout_text"].format(tip=tip, category_lower=cat_lower)
    cta_text = content["cta"].format(category=cat_label)
    cta_url = CATEGORY_URLS[category]

    hero_img = HERO_IMAGES.get("winback") if cycle <= 2 else HERO_IMAGES.get(category, HERO_IMAGES["spring"])

    rows = _header()
    rows += _hero(hero_img, f"{cat_label} Spring Planting", cta_url)
    rows += _body(headline, body_text)
    rows += _callout(callout_title, callout_text)
    rows += _products_3col(category)
    rows += _cta(cta_text, cta_url)
    rows += _trust_bar()
    rows += _footer()
    return _wrap(rows)


def build_spring_activation_html(category, cycle):
    content = SPRING_ACTIVATION_CONTENT[cycle]
    cat_label = CATEGORY_LABELS[category]
    cat_lower = cat_label.lower()
    tip_idx = min(cycle - 1, len(CATEGORY_TIPS[category]) - 1)
    tip = CATEGORY_TIPS[category][tip_idx]

    headline = content["headline"].format(category=cat_label)
    body_text = content["body"].format(category_lower=cat_lower)
    callout_title = content["callout_title"].format(category=cat_label)
    callout_text = content["callout_text"].format(tip=tip, category=cat_label, category_lower=cat_lower)
    cta_text = content["cta"].format(category=cat_label)
    cta_url = CATEGORY_URLS[category]

    hero_key = "earth_day" if cycle == 3 else category
    hero_img = HERO_IMAGES.get(hero_key, HERO_IMAGES["spring"])

    rows = _header()
    rows += _hero(hero_img, f"{cat_label} Spring Guide", cta_url)
    rows += _body(headline, body_text)
    rows += _callout(callout_title, callout_text)
    rows += _products_3col(category)
    rows += _cta(cta_text, cta_url)
    rows += _trust_bar()
    rows += _footer()
    return _wrap(rows)


def build_vip_html(cycle):
    content = VIP_CONTENT[cycle]
    rows = _header()
    rows += _hero(HERO_IMAGES["vip"], "VIP Customer", "https://www.naturesseed.com")
    rows += _body(content["headline"], content["body"])
    rows += _callout("You're a VIP", "As one of our most loyal customers, your feedback shapes what we do next. We genuinely read and respond to every reply.")
    rows += _trust_bar()
    rows += _footer()
    return _wrap(rows)


def build_promo_html(name, headline, body_text, code, expiry, cta_text, cta_url, hero_key="spring"):
    rows = _header()
    rows += _hero(HERO_IMAGES.get(hero_key, HERO_IMAGES["spring"]), name, cta_url)
    rows += _body(headline, body_text)
    rows += _coupon(code, expiry)
    rows += _cta(cta_text, cta_url)
    rows += _trust_bar()
    rows += _footer()
    return _wrap(rows)


def build_content_intro_html(headline, body_text, hero_key, cta_text, cta_url, callout_title=None, callout_text=None):
    rows = _header()
    rows += _hero(HERO_IMAGES.get(hero_key, HERO_IMAGES["spring"]), headline, cta_url)
    rows += _body(headline, body_text)
    if callout_title:
        rows += _callout(callout_title, callout_text)
    rows += _cta(cta_text, cta_url)
    rows += _trust_bar()
    rows += _footer()
    return _wrap(rows)


# ─── Klaviyo API Helpers ─────────────────────────────────────────────────────

def create_template(name, html):
    """Create a CODE template in Klaviyo. Returns template ID."""
    payload = {
        "data": {
            "type": "template",
            "attributes": {
                "name": name,
                "editor_type": "CODE",
                "html": html,
            }
        }
    }
    resp = requests.post(f"{BASE_URL}/templates/", headers=HEADERS, json=payload)
    if resp.status_code in (200, 201):
        tid = resp.json()["data"]["id"]
        print(f"  [TEMPLATE] Created: {name} -> {tid}")
        return tid
    else:
        print(f"  [TEMPLATE ERROR] {name}: {resp.status_code} {resp.text[:200]}")
        return None


def create_campaign(name, subject, preview_text, included_ids, excluded_ids, send_datetime, from_email="customercare@naturesseed.com", from_label="Nature's Seed"):
    """Create a draft email campaign. Returns (campaign_id, message_id)."""
    payload = {
        "data": {
            "type": "campaign",
            "attributes": {
                "name": name,
                "audiences": {
                    "included": included_ids,
                    "excluded": excluded_ids or [],
                },
                "campaign-messages": {
                    "data": [
                        {
                            "type": "campaign-message",
                            "attributes": {
                                "channel": "email",
                                "content": {
                                    "subject": subject,
                                    "preview_text": preview_text,
                                    "from_email": from_email,
                                    "from_label": from_label,
                                },
                                "label": name,
                            }
                        }
                    ]
                },
                "send_strategy": {
                    "method": "static",
                    "options_static": {
                        "datetime": send_datetime,
                        "is_local": False,
                    },
                },
            }
        }
    }
    resp = requests.post(f"{BASE_URL}/campaigns/", headers=HEADERS, json=payload)
    if resp.status_code in (200, 201):
        data = resp.json()["data"]
        cid = data["id"]
        # Extract message ID from relationships
        msgs = data.get("relationships", {}).get("campaign-messages", {}).get("data", [])
        mid = msgs[0]["id"] if msgs else None
        print(f"  [CAMPAIGN] Created: {name} -> {cid} (msg: {mid})")
        return cid, mid
    else:
        print(f"  [CAMPAIGN ERROR] {name}: {resp.status_code} {resp.text[:300]}")
        return None, None


def create_full_campaign(name, subject, preview_text, html, included_ids, excluded_ids, send_datetime):
    """Create template + campaign. Template assignment done separately via MCP. Returns (campaign_id, template_id, message_id)."""
    template_id = create_template(f"TPL - {name}", html)
    if not template_id:
        return None, None, None
    time.sleep(0.5)

    cid, mid = create_campaign(name, subject, preview_text, included_ids, excluded_ids, send_datetime)
    if not cid:
        return None, template_id, None
    time.sleep(0.5)

    return cid, template_id, mid


# ─── Campaign Definitions ───────────────────────────────────────────────────

def get_audience_winback(category):
    """Win Back: category purchasers who are At Risk/Lapsed/Dormant AND E90D engaged."""
    included = [SEGMENTS[category]]
    excluded = [SEGMENTS[s] for s in ACTIVE_RFM] + [SEGMENTS["NOT_E90D"]]
    return included, excluded


def get_audience_spring_activation(category):
    """Spring Activation: category purchasers who are Champions/New/Warm AND E60D engaged."""
    included = [SEGMENTS[category]]
    excluded = [SEGMENTS["active_this_season"]] + [SEGMENTS[s] for s in DECLINING_RFM] + [SEGMENTS["NOT_E60D"]]
    return included, excluded


def get_audience_vip():
    """VIP: Champions + Warm, E60D engaged."""
    included = [SEGMENTS["champions"], SEGMENTS["warm"]]
    excluded = [SEGMENTS["NOT_E60D"]]
    return included, excluded


def get_audience_broad_engaged():
    """Full engaged database: E90D."""
    return [SEGMENTS["E90D"]], []


def build_all_campaigns():
    """Build and return list of all 55 campaign specs."""
    campaigns = []
    categories = ["lawn", "pasture", "wildflower", "other"]

    # ─── Week 1: St Patrick's + Food Plot ────────────────────────────────
    # W1-001: Clover Sale
    campaigns.append({
        "name": "Clover Seeds — St. Patrick's Day Sale",
        "subject": "15% off clover seeds this week",
        "preview": "St. Patrick's Day special — pair clover with any product and save",
        "html": build_promo_html(
            "St. Patrick's Day Clover Sale",
            "15% Off Clover Seeds This Week",
            'Hey {{ first_name|default:"there" }},<br><br>Celebrate St. Patrick\'s Day with 15% off our entire clover seed line when you add any other product to your cart. Clover is one of the best investments you can make for your soil — it fixes nitrogen, crowds out weeds, and supports pollinators.<br><br>Use code <strong>LUCKY15</strong> at checkout. Valid through March 17.',
            "LUCKY15", "Valid through March 17, 2026", "Shop Clover Seeds",
            "https://www.naturesseed.com/products/clover-seed/", "clover"
        ),
        "included": [SEGMENTS["E90D"]],
        "excluded": [],
        "send_dt": "2026-03-10T17:00:00+00:00",
    })

    # W1-002: Food Plot Follow-up
    campaigns.append({
        "name": "Follow-up: Introduction to Food Plot Seed",
        "subject": "Food plots that keep deer coming back",
        "preview": "Practical tips for building a food plot that lasts",
        "html": build_content_intro_html(
            "Your Guide to Food Plot Seed",
            'Hey {{ first_name|default:"there" }},<br><br>Food plots are one of the most rewarding projects you can take on — whether you\'re managing wildlife habitat or just want to see more deer on your property. Here\'s what you need to know to get started this spring.<br><br>The key is choosing the right mix for your region and soil type. Our blends are formulated by seed scientists who understand wildlife nutrition and seasonal browse patterns.',
            "food_plot", "Shop Food Plot Seed", "https://www.naturesseed.com/products/food-plot-seed/",
            "Spring Food Plot Tip", "For spring plots, combine clover with chicory for a perennial plot that provides browse from April through November. Plant when soil temps hit 50°F."
        ),
        "included": [SEGMENTS["E90D"]],
        "excluded": [],
        "send_dt": "2026-03-12T17:00:00+00:00",
    })

    # W1-003: Clover Reminder
    campaigns.append({
        "name": "Clover Seeds — St. Patrick's Reminder",
        "subject": "Last chance: 15% off clover seeds",
        "preview": "LUCKY15 expires tomorrow — don't miss out",
        "html": build_promo_html(
            "St. Patrick's Day — Last Chance",
            "Last Chance: 15% Off Clover Seeds",
            'Hey {{ first_name|default:"there" }},<br><br>Just a quick reminder — our St. Patrick\'s Day clover sale ends tomorrow. Use code <strong>LUCKY15</strong> to get 15% off clover seeds when you add any other product to your cart.<br><br>Clover fixes nitrogen in your soil, supports pollinators, and makes a beautiful lawn alternative. Don\'t miss this deal.',
            "LUCKY15", "Expires March 17, 2026", "Shop Clover Seeds",
            "https://www.naturesseed.com/products/clover-seed/", "clover"
        ),
        "included": [SEGMENTS["E90D"]],
        "excluded": [],
        "send_dt": "2026-03-13T17:00:00+00:00",
    })

    # ─── Week 2: Cover Crop + Florida ────────────────────────────────────
    campaigns.append({
        "name": "Introduction: Cover Crop Seeds & Kits",
        "subject": "Build better soil with cover crops",
        "preview": "The secret weapon for healthier soil and lower costs",
        "html": build_content_intro_html(
            "Cover Crops: Your Soil's Best Friend",
            'Hey {{ first_name|default:"there" }},<br><br>Cover crops are one of the most powerful tools in any grower\'s toolkit. They fix nitrogen, prevent erosion, suppress weeds, and improve soil structure — all while you\'re not actively growing anything else.<br><br>Whether you\'re managing a large farm or a backyard garden, there\'s a cover crop mix that fits your needs. Here\'s what you need to know.',
            "cover_crop", "Shop Cover Crops", "https://www.naturesseed.com/products/cover-crop-seed/",
            "Did You Know?", "Cover crops can add 50-150 lbs of nitrogen per acre, reducing fertilizer costs by 30-50%. Legume mixes like crimson clover and winter peas are the most efficient."
        ),
        "included": [SEGMENTS["E90D"]],
        "excluded": [],
        "send_dt": "2026-03-16T17:00:00+00:00",
    })

    campaigns.append({
        "name": "Introduction: Florida Native Seeds",
        "subject": "New: Florida native seed collection",
        "preview": "Seed adapted to Florida's unique growing conditions",
        "html": build_content_intro_html(
            "Introducing Florida Native Seeds",
            'Hey {{ first_name|default:"there" }},<br><br>We\'re excited to announce our new Florida-specific native seed offerings. Developed for Florida\'s unique climate, soil types, and growing conditions, these mixes are perfect for restoration projects, landscaping, and wildlife habitat.<br><br>Every seed in this collection is adapted to thrive in Florida\'s heat, humidity, and sandy soils.',
            "florida", "Shop Florida Native Seeds", "https://www.naturesseed.com/products/",
            "Why Go Native?", "Native plants require less water, no fertilizer, and support 10x more native wildlife than non-native landscaping. They're adapted to your local conditions — so they just work."
        ),
        "included": [SEGMENTS["florida"], SEGMENTS["E90D"]],
        "excluded": [],
        "send_dt": "2026-03-18T17:00:00+00:00",
    })

    # ─── Cycles 1-5: Win Back + Spring Activation + VIP ──────────────────
    cycle_dates = {
        1: {"wb": "2026-03-23", "sa": "2026-03-25", "vip": "2026-03-27"},
        2: {"wb": "2026-04-06", "sa": "2026-04-08", "vip": "2026-04-10"},
        3: {"wb": "2026-04-20", "sa": "2026-04-23", "vip": "2026-04-24"},
        4: {"wb": "2026-05-04", "sa": "2026-05-06", "vip": "2026-05-08"},
        5: {"wb": "2026-05-18", "sa": "2026-05-20", "vip": "2026-05-22"},
    }

    for cycle in range(1, 6):
        dates = cycle_dates[cycle]
        wb_content = WIN_BACK_CONTENT[cycle]
        sa_content = SPRING_ACTIVATION_CONTENT[cycle]

        # Win Back × 4 categories
        for cat in categories:
            cat_label = CATEGORY_LABELS[cat]
            cat_lower = cat_label.lower()
            incl, excl = get_audience_winback(cat)
            subject = wb_content["subject"].format(category=cat_label, category_lower=cat_lower)
            campaigns.append({
                "name": f"C{cycle} Win Back — {cat_label}",
                "subject": subject,
                "preview": f"Tips and inspiration for your {cat_lower}",
                "html": build_winback_html(cat, cycle),
                "included": incl,
                "excluded": excl,
                "send_dt": f"{dates['wb']}T17:00:00+00:00",
            })

        # Spring Activation × 4 categories
        for cat in categories:
            cat_label = CATEGORY_LABELS[cat]
            cat_lower = cat_label.lower()
            incl, excl = get_audience_spring_activation(cat)
            subject = sa_content["subject"].format(category=cat_label, category_lower=cat_lower)
            campaigns.append({
                "name": f"C{cycle} Spring Activation — {cat_label}",
                "subject": subject,
                "preview": f"Spring {cat_lower} guide from Nature's Seed",
                "html": build_spring_activation_html(cat, cycle),
                "included": incl,
                "excluded": excl,
                "send_dt": f"{dates['sa']}T17:00:00+00:00",
            })

        # VIP Engagement
        vip_content = VIP_CONTENT[cycle]
        vip_incl, vip_excl = get_audience_vip()
        campaigns.append({
            "name": f"C{cycle} VIP — {vip_content['headline']}",
            "subject": vip_content["subject"],
            "preview": "Your opinion matters to us",
            "html": build_vip_html(cycle),
            "included": vip_incl,
            "excluded": vip_excl,
            "send_dt": f"{dates['vip']}T17:00:00+00:00",
        })

    # ─── Week 4 Follow-ups ───────────────────────────────────────────────
    campaigns.append({
        "name": "Follow-up: Cover Crop Seeds & Kits",
        "subject": "Cover crops: a deeper dive",
        "preview": "Everything you need to know about cover crop selection",
        "html": build_content_intro_html(
            "Cover Crops: The Complete Guide",
            'Hey {{ first_name|default:"there" }},<br><br>A couple weeks ago we introduced our cover crop lineup. Today we\'re going deeper — species selection, termination timing, and how to maximize the soil-building benefits for your next cash crop or garden season.',
            "cover_crop", "Shop Cover Crops", "https://www.naturesseed.com/products/cover-crop-seed/",
            "Pro Tip", "Mix legumes (clover, peas) with grasses (rye, oats) for the best soil improvement. Legumes fix nitrogen while grasses build organic matter and prevent erosion."
        ),
        "included": [SEGMENTS["E90D"]],
        "excluded": [],
        "send_dt": "2026-03-30T17:00:00+00:00",
    })

    campaigns.append({
        "name": "Follow-up: Florida Native Seeds",
        "subject": "Florida native seeds: your top questions answered",
        "preview": "Planting guides and species recommendations for Florida",
        "html": build_content_intro_html(
            "Florida Native Seeds: Deep Dive",
            'Hey {{ first_name|default:"there" }},<br><br>Since we launched our Florida native seed collection, we\'ve gotten a lot of great questions. Here are the answers to the most common ones — plus planting tips specific to Florida\'s climate zones.',
            "florida", "Shop Florida Natives", "https://www.naturesseed.com/products/",
            "Florida Planting Tip", "Florida's long growing season means you can plant native wildflowers almost year-round. For best results, plant during the cooler months (October-March) to let root systems establish before summer heat."
        ),
        "included": [SEGMENTS["florida"], SEGMENTS["E90D"]],
        "excluded": [],
        "send_dt": "2026-04-01T17:00:00+00:00",
    })

    # ─── Earth Day (inserted in Cycle 3) ─────────────────────────────────
    campaigns.append({
        "name": "Earth Day — $25 Off Orders Over $150",
        "subject": "$25 off for Earth Day",
        "preview": "Plant something that matters — $25 off seed orders over $150",
        "html": build_promo_html(
            "Earth Day Sale",
            "Earth Day: $25 Off Seed Orders Over $150",
            'Hey {{ first_name|default:"there" }},<br><br>This Earth Day, we\'re celebrating everyone who plants with purpose. Use code <strong>EARTH25</strong> to get $25 off any seed order over $150.<br><br>Every seed you plant supports healthier soil, cleaner air, and stronger ecosystems. Whether you\'re growing a lawn, managing pasture, or planting wildflowers — you\'re making a difference.',
            "EARTH25", "Valid April 22-29, 2026", "Shop Seeds",
            "https://www.naturesseed.com/products/", "earth_day"
        ),
        "included": [SEGMENTS["E90D"]],
        "excluded": [],
        "send_dt": "2026-04-22T17:00:00+00:00",
    })

    # ─── Memorial Day ────────────────────────────────────────────────────
    campaigns.append({
        "name": "Memorial Day Sale — Start",
        "subject": "Memorial Day: 15% off everything",
        "preview": "Save 15% on your entire order through May 31",
        "html": build_promo_html(
            "Memorial Day Sale",
            "Memorial Day Sale: 15% Off Everything",
            'Hey {{ first_name|default:"there" }},<br><br>This Memorial Day weekend, we\'re offering 15% off your entire order. No minimums, no restrictions — just use code <strong>MEMORIAL15</strong> at checkout.<br><br>Whether you\'re starting a new project or stocking up for the season, now is the time. Sale runs through May 31.',
            "MEMORIAL15", "Valid May 25-31, 2026", "Shop Now",
            "https://www.naturesseed.com/products/", "memorial_day"
        ),
        "included": [SEGMENTS["E90D"]],
        "excluded": [],
        "send_dt": "2026-05-25T17:00:00+00:00",
    })

    campaigns.append({
        "name": "Memorial Day Sale — Last Chance",
        "subject": "Last chance: 15% off ends tomorrow",
        "preview": "MEMORIAL15 expires May 31 — don't miss out",
        "html": build_promo_html(
            "Memorial Day — Last Chance",
            "Last Chance: 15% Off Ends Tomorrow",
            'Hey {{ first_name|default:"there" }},<br><br>Just a quick reminder — our Memorial Day sale ends tomorrow. Use code <strong>MEMORIAL15</strong> for 15% off your entire order.<br><br>This is our last big sale before summer. Don\'t miss out.',
            "MEMORIAL15", "Expires May 31, 2026", "Shop Now",
            "https://www.naturesseed.com/products/", "memorial_day"
        ),
        "included": [SEGMENTS["E90D"]],
        "excluded": [],
        "send_dt": "2026-05-27T17:00:00+00:00",
    })

    return campaigns


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    all_campaigns = build_all_campaigns()
    print(f"\n{'='*60}")
    print(f"Total campaigns to create: {len(all_campaigns)}")
    print(f"{'='*60}\n")

    results = []
    for i, camp in enumerate(all_campaigns, 1):
        print(f"\n[{i}/{len(all_campaigns)}] {camp['name']}")
        cid, tid, mid = create_full_campaign(
            name=camp["name"],
            subject=camp["subject"],
            preview_text=camp["preview"],
            html=camp["html"],
            included_ids=camp["included"],
            excluded_ids=camp["excluded"],
            send_datetime=camp["send_dt"],
        )
        results.append({
            "name": camp["name"],
            "campaign_id": cid,
            "template_id": tid,
            "message_id": mid,
            "success": cid is not None,
        })
        time.sleep(1)  # rate limit

    # Summary
    success = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    print(f"\n{'='*60}")
    print(f"DONE: {success} created, {failed} failed out of {len(results)} total")
    print(f"{'='*60}")

    if failed:
        print("\nFailed campaigns:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['name']}")

    # Save template assignments needed (for MCP tool)
    assignments = [
        {"message_id": r["message_id"], "template_id": r["template_id"], "name": r["name"]}
        for r in results if r["message_id"] and r["template_id"]
    ]
    print(f"\n{len(assignments)} template assignments pending (use MCP tool)")

    # Save results
    with open("campaign_creation_results.json", "w") as f:
        json.dump({"results": results, "pending_assignments": assignments}, f, indent=2)
    print(f"Results saved to campaign_creation_results.json")


if __name__ == "__main__":
    main()
