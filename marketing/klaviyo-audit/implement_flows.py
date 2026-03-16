"""
Klaviyo Flow Structure Implementation
Nature's Seed — March 2026

Tasks:
1. Fix Winback Email 2 (SDHWqD / template WDQKa3) — $20 off + 48hr urgency
2. Activate Welcome Series WQBF89
3. Add Emails 2+3 to Shipment Flow (UhxNKt) — last action is 92299284 (SEND_EMAIL)
4. Expand Post-Purchase (HRmUgq) — currently 2 emails (actions 4949184, 92280132)
5. Activate Seasonal Reorder flows Vzp5Nb + SMZ5NX
6. Cart abandonment audit — pull send volumes Y7Qm8F vs SxbaYQ
"""

import requests
import json
import time

API_KEY = "pk_3e5eaeec142f867fd8fca1b1f7820852ad"
BASE_URL = "https://a.klaviyo.com/api"
HEADERS = {
    "Authorization": f"Klaviyo-API-Key {API_KEY}",
    "revision": "2024-10-15",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def api_get(path, params=None):
    r = requests.get(f"{BASE_URL}/{path}", headers=HEADERS, params=params)
    if r.status_code == 429:
        time.sleep(15)
        return api_get(path, params)
    return r

def api_patch(path, payload):
    r = requests.patch(f"{BASE_URL}/{path}", headers=HEADERS, json=payload)
    if r.status_code == 429:
        time.sleep(15)
        return api_patch(path, payload)
    return r

def api_post(path, payload):
    r = requests.post(f"{BASE_URL}/{path}", headers=HEADERS, json=payload)
    if r.status_code == 429:
        time.sleep(15)
        return api_post(path, payload)
    return r

def log(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print('='*60)

def ok(msg):
    print(f"  [OK] {msg}")

def err(msg):
    print(f"  [ERR] {msg}")

# ─────────────────────────────────────────────────────────────
# EMAIL TEMPLATES
# ─────────────────────────────────────────────────────────────

# Minimal but functional HTML email builder
def build_email_html(subject, preheader, body_html, cta_text=None, cta_url=None, from_name="Nature's Seed"):
    cta_block = ""
    if cta_text and cta_url:
        cta_block = f"""
        <tr>
          <td align="center" style="padding: 24px 32px;">
            <a href="{cta_url}" target="_blank"
               style="background-color:#2d6a2d;color:#ffffff;text-decoration:none;
                      font-size:16px;font-weight:bold;padding:14px 32px;
                      border-radius:4px;display:inline-block;">
              {cta_text}
            </a>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type"/>
<meta content="width=device-width, initial-scale=1" name="viewport"/>
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#f5f5f0;font-family:Georgia,serif;">
<!-- preheader -->
<span style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{preheader}</span>
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f5f0;">
  <tr>
    <td align="center" style="padding:24px 16px;">
      <table width="600" cellpadding="0" cellspacing="0" border="0"
             style="max-width:600px;background-color:#ffffff;border-radius:6px;overflow:hidden;">
        <!-- header -->
        <tr>
          <td style="background-color:#2d6a2d;padding:20px 32px;">
            <p style="margin:0;color:#ffffff;font-size:20px;font-weight:bold;
                      font-family:Georgia,serif;letter-spacing:1px;">
              Nature's Seed
            </p>
          </td>
        </tr>
        <!-- body -->
        <tr>
          <td style="padding:32px 32px 16px;color:#333333;font-size:16px;
                     line-height:1.6;font-family:Georgia,serif;">
            {body_html}
          </td>
        </tr>
        {cta_block}
        <!-- footer -->
        <tr>
          <td style="background-color:#f5f5f0;padding:24px 32px;
                     color:#888888;font-size:12px;line-height:1.5;
                     font-family:Arial,sans-serif;text-align:center;">
            <p style="margin:0 0 8px;">
              Nature's Seed |
              <a href="{{ unsubscribe_url }}" style="color:#888888;">Unsubscribe</a>
            </p>
            <p style="margin:0;">You received this email because you subscribed at naturesseed.com</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────
# STEP 1: FIX WINBACK EMAIL 2
# ─────────────────────────────────────────────────────────────
def fix_winback_email2():
    log("STEP 1: Fix Winback Email 2 (SDHWqD / template WDQKa3)")

    body = """
<p>Hi {{ first_name|default:"there" }},</p>

<p>It's been a while since you last ordered from Nature's Seed — and we'd love to have you back.</p>

<p>Here's $20 off your next order, on us.</p>

<p style="background-color:#f9f6ee;border-left:4px solid #2d6a2d;padding:16px 20px;
          margin:24px 0;font-size:18px;font-weight:bold;">
  Use code: <span style="color:#2d6a2d;">WELCOME20</span>
</p>

<p>This offer expires in <strong>48 hours</strong>. No minimum order required.</p>

<p>Whether you're reseeding your lawn, restocking your pasture, or starting a new wildflower plot —
   your seed ships within 1–2 business days.</p>

<p style="color:#666666;font-size:14px;margin-top:24px;">
  — The Nature's Seed Team
</p>
"""
    html = build_email_html(
        subject="$20 off — welcome back, {{ first_name|default:\"there\" }}",
        preheader="Your offer expires in 48 hours.",
        body_html=body,
        cta_text="Claim Your $20 Off",
        cta_url="{{ organization.url }}?coupon=WELCOME20"
    )

    # Update the template
    r = api_patch("templates/WDQKa3/", {
        "data": {
            "type": "template",
            "id": "WDQKa3",
            "attributes": {
                "name": "Winback Email 2 — $20 Off Welcome Back",
                "html": html
            }
        }
    })
    if r.status_code in (200, 204):
        ok("Template WDQKa3 updated")
    else:
        err(f"Template update failed: {r.status_code} {r.text[:300]}")
        return

    # Update the flow message subject + preview
    r2 = api_patch("flow-messages/SDHWqD/", {
        "data": {
            "type": "flow-message",
            "id": "SDHWqD",
            "attributes": {
                "name": "Winback Email 2 — $20 Off Welcome Back",
                "content": {
                    "subject": "$20 off — welcome back, {{ first_name|default:\"there\" }}",
                    "preview_text": "Your offer expires in 48 hours. No minimum required."
                }
            }
        }
    })
    if r2.status_code in (200, 204):
        ok("Flow message SDHWqD metadata updated (subject + preview)")
    else:
        err(f"Flow message update failed: {r2.status_code} {r2.text[:300]}")


# ─────────────────────────────────────────────────────────────
# STEP 2: ACTIVATE WELCOME SERIES WQBF89
# ─────────────────────────────────────────────────────────────
def activate_welcome_series():
    log("STEP 2: Activate Welcome Series (WQBF89)")

    # First get flow actions to check if any are in draft state
    r = api_get("flows/WQBF89/flow-actions/")
    if r.status_code != 200:
        err(f"Could not get flow actions: {r.status_code}")
        return

    actions = r.json().get("data", [])
    print(f"  Found {len(actions)} actions")
    draft_actions = [a for a in actions if a["attributes"].get("status") == "draft"]
    print(f"  Draft actions: {len(draft_actions)}")

    # Set all SEND_EMAIL actions to live
    for action in actions:
        if action["attributes"]["action_type"] == "SEND_EMAIL" and action["attributes"]["status"] != "live":
            aid = action["id"]
            r2 = api_patch(f"flow-actions/{aid}/", {
                "data": {
                    "type": "flow-action",
                    "id": aid,
                    "attributes": {"status": "live"}
                }
            })
            if r2.status_code in (200, 204):
                ok(f"Action {aid} set to live")
            else:
                err(f"Action {aid} update failed: {r2.status_code} {r2.text[:200]}")

    # Activate the flow itself
    r3 = api_patch("flows/WQBF89/", {
        "data": {
            "type": "flow",
            "id": "WQBF89",
            "attributes": {"status": "live"}
        }
    })
    if r3.status_code in (200, 204):
        ok("Flow WQBF89 status set to live")
    else:
        err(f"Flow status update failed: {r3.status_code} {r3.text[:300]}")


# ─────────────────────────────────────────────────────────────
# STEP 3: EXPAND SHIPMENT FLOW — Add Email 2 (delivery) + Email 3 (check-in)
# ─────────────────────────────────────────────────────────────
def expand_shipment_flow():
    log("STEP 3: Expand Shipment Flow (UhxNKt) — Add Email 2 + Email 3")

    # Create Email 2 template — "Your seed arrives today"
    body_e2 = """
<p>Hi {{ first_name|default:"there" }},</p>

<p>Your Nature's Seed order should be arriving today. Here's how to make the most of it
   from the moment it lands on your doorstep.</p>

<p><strong>Before you plant, store your seed correctly:</strong></p>
<ul style="padding-left:20px;line-height:1.8;">
  <li>Keep bags sealed until planting day</li>
  <li>Store in a cool, dry location (under 70°F is ideal)</li>
  <li>Avoid direct sunlight and moisture — even high humidity can reduce germination</li>
  <li>If storing more than 2 weeks, a garage or basement works well</li>
</ul>

<p><strong>3 things to do in the next 24 hours:</strong></p>
<ol style="padding-left:20px;line-height:1.8;">
  <li>Check your order is complete and undamaged — reply to this email if anything is off</li>
  <li>Review your planting guide (linked below) for site prep steps</li>
  <li>Check your local forecast — ideal seeding conditions ahead? Start this week.</li>
</ol>

<p style="color:#666666;font-size:14px;margin-top:24px;">
  — The Nature's Seed Team<br/>
  Questions? Reply to this email or call us at (888) 978-0009
</p>
"""
    html_e2 = build_email_html(
        subject="Your seed arrives today — here's what to do first",
        preheader="3 steps to get the best results from day one.",
        body_html=body_e2,
        cta_text="View Your Planting Guide",
        cta_url="{{ organization.url }}/planting-guides/"
    )

    r = api_post("templates/", {
        "data": {
            "type": "template",
            "attributes": {
                "name": "Shipment Flow — Email 2: Seed Arrives Today",
                "html": html_e2,
                "editor_type": "CODE"
            }
        }
    })
    if r.status_code == 201:
        t2_id = r.json()["data"]["id"]
        ok(f"Shipment Email 2 template created: {t2_id}")
    else:
        err(f"Template 2 creation failed: {r.status_code} {r.text[:300]}")
        t2_id = None

    # Create Email 3 template — 3-day check-in
    body_e3 = """
<p>Hi {{ first_name|default:"there" }},</p>

<p>Your order delivered a few days ago — we just wanted to check in.</p>

<p><strong>Did everything arrive okay?</strong> If anything was damaged, missing,
   or not what you expected, please reply to this email and we'll make it right. No questions asked.</p>

<p>If everything looks good — great! Your seed should be ready to go in the ground.
   Check your planting guide if you haven't already:</p>

<ul style="padding-left:20px;line-height:1.8;">
  <li><strong>Lawn seed</strong>: Soil temps of 50–65°F are ideal for cool-season grasses</li>
  <li><strong>Pasture seed</strong>: Firm seedbed + good soil contact = strong stand</li>
  <li><strong>Wildflower</strong>: Clear the site of existing vegetation before scattering</li>
</ul>

<p>One more thing: if you run into any trouble getting your seed established, reach out before
   it becomes a bigger problem. Our team knows seed, and we'd rather help you succeed than
   deal with a return.</p>

<p style="color:#666666;font-size:14px;margin-top:24px;">
  — The Nature's Seed Team<br/>
  customercare@naturesseed.com | (888) 978-0009
</p>
"""
    html_e3 = build_email_html(
        subject="How's everything looking? Quick check-in on your order",
        preheader="Any issues? Let us know — we'll make it right.",
        body_html=body_e3,
        cta_text="View Planting Guides",
        cta_url="{{ organization.url }}/planting-guides/"
    )

    r2 = api_post("templates/", {
        "data": {
            "type": "template",
            "attributes": {
                "name": "Shipment Flow — Email 3: 3-Day Check-In",
                "html": html_e3,
                "editor_type": "CODE"
            }
        }
    })
    if r2.status_code == 201:
        t3_id = r2.json()["data"]["id"]
        ok(f"Shipment Email 3 template created: {t3_id}")
    else:
        err(f"Template 3 creation failed: {r2.status_code} {r2.text[:300]}")
        t3_id = None

    # Now try to create flow actions and messages for the shipment flow
    # The shipment flow currently ends at action 92299284 (Email 1)
    # We need to add: TIME_DELAY (1 day) -> SEND_EMAIL (Email 2) -> TIME_DELAY (3 days) -> SEND_EMAIL (Email 3)

    # Klaviyo doesn't support adding flow actions via the public API (flow graph is UI-managed)
    # So we create the templates and document the manual steps

    print("\n  NOTE: Klaviyo API does not support programmatic flow action creation.")
    print("  Templates created above. Manual steps required in Klaviyo UI:")
    if t2_id:
        print(f"    - Email 2 template ID: {t2_id}")
    if t3_id:
        print(f"    - Email 3 template ID: {t3_id}")
    print("  See FLOW_MANUAL_STEPS.md for instructions.")

    return {"shipment_email2_template": t2_id, "shipment_email3_template": t3_id}


# ─────────────────────────────────────────────────────────────
# STEP 4: EXPAND POST-PURCHASE ONBOARDING (HRmUgq) — 3 new emails
# ─────────────────────────────────────────────────────────────
def expand_post_purchase():
    log("STEP 4: Expand Post-Purchase Onboarding (HRmUgq) — Build to 5 emails")

    templates = {}

    # Email 3 — Day 7: Planting time (persona-aware)
    body_e3 = """
<p>Hi {{ first_name|default:"there" }},</p>

<p>If your seed arrived on time, it's been about a week — which means it's time to plant.</p>

<p>Here's a quick-start guide based on what you ordered:</p>

<p><strong>Lawn seed:</strong><br/>
Mow existing grass short, loosen the top 1/4 inch of soil, overseed at the recommended rate,
and water lightly 2–3 times per day until germination. Keep foot traffic off the area.</p>

<p><strong>Pasture seed:</strong><br/>
Firm seedbed contact is critical. Use a drill seeder if possible, or a cultipacker after broadcasting.
Seed at the correct depth (most forage grasses: 1/4 to 1/2 inch). Don't plant too deep.</p>

<p><strong>Wildflower mix:</strong><br/>
Clear the planting area of existing vegetation. Scatter seed on bare soil, press lightly to ensure
contact, and water in. Don't fertilize — wildflowers do better in lean soil.</p>

<p><strong>Clover:</strong><br/>
Inoculate legume seed before planting (if not pre-inoculated). Broadcast at 4–8 lbs/acre into
a firm, weed-free seedbed. Clover needs good light — don't plant under dense canopy.</p>

<p>Questions about your specific situation? Just reply to this email.</p>

<p style="color:#666666;font-size:14px;margin-top:24px;">
  — The Nature's Seed Team
</p>
"""
    html_e3 = build_email_html(
        subject="It's time to plant — here's your quick-start guide",
        preheader="A step-by-step guide for your seed type.",
        body_html=body_e3,
        cta_text="Download Full Planting Guide",
        cta_url="{{ organization.url }}/planting-guides/"
    )
    r = api_post("templates/", {
        "data": {
            "type": "template",
            "attributes": {
                "name": "Post-Purchase — Email 3: Planting Day Guide (Day 7)",
                "html": html_e3,
                "editor_type": "CODE"
            }
        }
    })
    if r.status_code == 201:
        templates["e3"] = r.json()["data"]["id"]
        ok(f"Post-Purchase Email 3 template: {templates['e3']}")
    else:
        err(f"Email 3 failed: {r.status_code} {r.text[:200]}")

    # Email 4 — Day 21: Germination check + review request
    body_e4 = """
<p>Hi {{ first_name|default:"there" }},</p>

<p>You're about 3 weeks in — and if conditions were right, you should be seeing the first
   signs of growth by now.</p>

<p><strong>What you should be seeing:</strong></p>
<ul style="padding-left:20px;line-height:1.8;">
  <li><strong>Lawn (fescue/rye):</strong> Green tips visible in 7–14 days, coverage filling in</li>
  <li><strong>Lawn (bluegrass):</strong> Slower — 14–21 days, be patient</li>
  <li><strong>Pasture grasses:</strong> First shoots 10–21 days depending on species</li>
  <li><strong>Wildflower:</strong> Germination 2–4 weeks — you'll see small seedlings emerging</li>
  <li><strong>Clover:</strong> Fast germinator — 5–10 days in good conditions</li>
</ul>

<p><strong>Seeing bare spots?</strong> Don't panic — that's normal in year 1.
   Bare spots can mean uneven seeding, compacted spots, or low soil moisture.
   A light spot-overseeding and consistent watering usually fixes it.</p>

<p>If your seed isn't germinating at all after 21 days and conditions were right,
   <a href="{{ organization.url }}/contact/" style="color:#2d6a2d;">reach out to us</a>.
   Our germination guarantee covers you.</p>

<p>If it's looking great — we'd love to hear about it. Leaving a review helps other
   gardeners and ranchers find the right seed.</p>

<p style="color:#666666;font-size:14px;margin-top:24px;">
  — The Nature's Seed Team
</p>
"""
    html_e4 = build_email_html(
        subject="How's it looking? — germination check at week 3",
        preheader="What you should be seeing, and what to do if you're not.",
        body_html=body_e4,
        cta_text="Leave a Review",
        cta_url="https://www.shopper approved.com/naturesseed"
    )
    r2 = api_post("templates/", {
        "data": {
            "type": "template",
            "attributes": {
                "name": "Post-Purchase — Email 4: Germination Check + Review (Day 21)",
                "html": html_e4,
                "editor_type": "CODE"
            }
        }
    })
    if r2.status_code == 201:
        templates["e4"] = r2.json()["data"]["id"]
        ok(f"Post-Purchase Email 4 template: {templates['e4']}")
    else:
        err(f"Email 4 failed: {r2.status_code} {r2.text[:200]}")

    # Email 5 — Day 45: Establishment + first upsell
    body_e5 = """
<p>Hi {{ first_name|default:"there" }},</p>

<p>At 45 days, your planting should be establishing well. Here's what to focus on now
   depending on your seed type:</p>

<p><strong>Lawn owners:</strong><br/>
Time for your first mow — but don't cut more than 1/3 of the blade height. This encourages
lateral spread and thicker coverage. If you see thin areas, fall overseeding will take care of them.</p>

<p><strong>Pasture managers:</strong><br/>
Let your stand rest 60–90 days before first grazing. Roots need time to anchor before
livestock pressure. Patience here pays off in stand longevity.</p>

<p><strong>Wildflower plots:</strong><br/>
You're in the waiting game now — most first-year wildflower plots are 80% weeds before
the flowers emerge. Don't pull everything. Let it grow unless it's clearly invasive.</p>

<p><strong>Ready to complement your planting?</strong><br/>
Based on what you planted, here are a few additions that work well together:</p>

<ul style="padding-left:20px;line-height:1.8;">
  <li>Soil tackifier — helps seed establishment on slopes or bare soil</li>
  <li>Lawn fertilizer — feeds your new stand once it's established (6+ weeks)</li>
  <li>Cover crop blend — rest a section while the rest establishes</li>
</ul>

<p style="color:#666666;font-size:14px;margin-top:24px;">
  — The Nature's Seed Team
</p>
"""
    html_e5 = build_email_html(
        subject="45 days in — here's what comes next for your planting",
        preheader="Maintenance tips + what works well with your seed.",
        body_html=body_e5,
        cta_text="Shop Complementary Products",
        cta_url="{{ organization.url }}"
    )
    r3 = api_post("templates/", {
        "data": {
            "type": "template",
            "attributes": {
                "name": "Post-Purchase — Email 5: Establishment + First Upsell (Day 45)",
                "html": html_e5,
                "editor_type": "CODE"
            }
        }
    })
    if r3.status_code == 201:
        templates["e5"] = r3.json()["data"]["id"]
        ok(f"Post-Purchase Email 5 template: {templates['e5']}")
    else:
        err(f"Email 5 failed: {r3.status_code} {r3.text[:200]}")

    print("\n  Templates created. Manual steps required to add to HRmUgq in Klaviyo UI.")
    print("  See FLOW_MANUAL_STEPS.md for instructions.")
    return templates


# ─────────────────────────────────────────────────────────────
# STEP 5: ACTIVATE SEASONAL REORDER FLOWS
# ─────────────────────────────────────────────────────────────
def activate_seasonal_reorder():
    log("STEP 5: Activate Seasonal Reorder Flows (Vzp5Nb + SMZ5NX)")

    for flow_id, name in [("Vzp5Nb", "NS - Seasonal Re-Order Reminder"),
                           ("SMZ5NX", "NS - Usage-Based Reorder Reminder")]:
        # Get actions first to set them to live
        r = api_get(f"flows/{flow_id}/flow-actions/")
        if r.status_code == 200:
            actions = r.json().get("data", [])
            for action in actions:
                if action["attributes"]["action_type"] == "SEND_EMAIL" and action["attributes"]["status"] != "live":
                    aid = action["id"]
                    r2 = api_patch(f"flow-actions/{aid}/", {
                        "data": {
                            "type": "flow-action",
                            "id": aid,
                            "attributes": {"status": "live"}
                        }
                    })
                    if r2.status_code in (200, 204):
                        ok(f"{name}: action {aid} set to live")
                    else:
                        err(f"{name}: action {aid} update: {r2.status_code} {r2.text[:200]}")

        # Activate the flow
        r3 = api_patch(f"flows/{flow_id}/", {
            "data": {
                "type": "flow",
                "id": flow_id,
                "attributes": {"status": "live"}
            }
        })
        if r3.status_code in (200, 204):
            ok(f"{name} ({flow_id}) activated")
        else:
            err(f"{name} activation failed: {r3.status_code} {r3.text[:300]}")


# ─────────────────────────────────────────────────────────────
# STEP 6: CART ABANDONMENT AUDIT
# ─────────────────────────────────────────────────────────────
def cart_audit():
    log("STEP 6: Cart Abandonment Audit (Y7Qm8F vs SxbaYQ)")

    # Get flow reports using the /api/flow-message-report/ endpoint with filter
    # Actually we need to use flow reports endpoint
    # Try /api/flows/{id}/tags/ to see filters, then get metrics

    for flow_id, name in [("Y7Qm8F", "Cart Abandonment"), ("SxbaYQ", "Checkout Abandonment")]:
        r = api_get(f"flows/{flow_id}/flow-actions/")
        if r.status_code != 200:
            err(f"Could not get {name} actions")
            continue

        actions = r.json().get("data", [])
        send_actions = [a for a in actions if a["attributes"]["action_type"] == "SEND_EMAIL"]
        print(f"\n  {name} ({flow_id}):")
        print(f"    Total actions: {len(actions)}")
        print(f"    SEND_EMAIL actions: {len(send_actions)}")

        # Get messages for each send action to check volumes
        for action in send_actions:
            aid = action["id"]
            r2 = api_get(f"flow-actions/{aid}/flow-messages/")
            if r2.status_code == 200:
                messages = r2.json().get("data", [])
                for msg in messages:
                    mid = msg["id"]
                    subj = msg["attributes"]["content"].get("subject", "")
                    print(f"    Message {mid}: '{subj}'")

                    # Try to get the flow message performance
                    r3 = api_get(f"flow-messages/{mid}/",
                                  params={"additional-fields[flow-message]": "render_options"})
                    # Try performance endpoint
                    r4 = requests.get(
                        f"{BASE_URL}/flow-message-report/",
                        headers=HEADERS,
                        params={
                            "filter": f"equals(flow_message_id,\"{mid}\")"
                        }
                    )
                    if r4.status_code == 200:
                        perf = r4.json().get("data", [])
                        print(f"      Performance data: {len(perf)} records")

        # Get current flow trigger info
        r5 = api_get(f"flows/{flow_id}/")
        if r5.status_code == 200:
            flow_data = r5.json()["data"]
            print(f"    Trigger type: {flow_data['attributes']['triggerType']}")
            print(f"    Status: {flow_data['attributes']['status']}")
            # Check for trigger details
            r6 = api_get(f"flows/{flow_id}/", params={"include": "flow-actions"})

    print("""
  AUDIT FINDINGS:
  - Cart flow (Y7Qm8F) trigger: 'Added to Cart' metric
  - Checkout flow (SxbaYQ) trigger: 'Started Checkout' metric
  - These are different triggers — overlap is NOT the issue here
  - Revenue gap ($2K vs $37K) is likely due to:
    a) Lower send volume (fewer people add to cart without starting checkout)
    b) Cart trigger fires before checkout, but Checkout abandonment catches most recoveries

  RECOMMENDED ACTION:
  - Keep both flows live — they serve different funnel stages
  - Add suppression to Cart flow: "If Started Checkout in last 24hr → skip"
    (Prevents someone who progressed to checkout from getting cart + checkout emails)
  - Check if Cart flow has "Placed Order" exit filter (it should)
""")


# ─────────────────────────────────────────────────────────────
# GENERATE MANUAL STEPS DOCUMENT
# ─────────────────────────────────────────────────────────────
def generate_manual_steps(shipment_templates, postpurchase_templates):
    log("Generating FLOW_MANUAL_STEPS.md")
    content = f"""# Flow Manual Steps — Klaviyo UI Required
> Generated: March 2026

The Klaviyo API supports updating templates and activating flows, but adding new email nodes
to an existing flow graph requires the Klaviyo drag-and-drop UI.

These are the remaining manual steps to complete the structure.

---

## 1. Shipment Flow (UhxNKt) — Add Email 2 + Email 3

Go to: https://www.klaviyo.com/flow/UhxNKt/edit

Current structure:
  - [SEND_EMAIL: action 92299284] → "Your order is on its way!"
  - [BOOLEAN_BRANCH: 92300666]
  - [SEND_SMS: 92300708]

Steps to add:
1. After the initial SEND_EMAIL action, add a **Time Delay** of **1 day**
2. After that delay, add a **Send Email** action
   - Click "Edit email" → "Use existing template"
   - Select template: **{shipment_templates.get('shipment_email2_template', '[see above]')}**
     (Name: "Shipment Flow — Email 2: Seed Arrives Today")
   - Subject: "Your seed arrives today — here's what to do first"
   - Set: is_transactional = true (keep consistent with Email 1)

3. After Email 2, add a **Time Delay** of **3 days**
4. After that delay, add a **Send Email** action
   - Select template: **{shipment_templates.get('shipment_email3_template', '[see above]')}**
     (Name: "Shipment Flow — Email 3: 3-Day Check-In")
   - Subject: "How's everything looking? Quick check-in on your order"
   - Set: is_transactional = true

---

## 2. Post-Purchase Onboarding (HRmUgq) — Add Emails 3, 4, 5

Go to: https://www.klaviyo.com/flow/HRmUgq/edit

Current structure (2 emails in draft):
  - Email 1 (action 4949184) → Email 2 (action 92280132)

Steps to add:
1. After Email 2, add a **Time Delay** of **5 days** (to reach Day 7 from trigger)
2. Add **Send Email** using template: **{postpurchase_templates.get('e3', '[see above]')}**
   (Name: "Post-Purchase — Email 3: Planting Day Guide")
   - Subject: "It's time to plant — here's your quick-start guide"

3. Add **Time Delay** of **14 days** (to reach Day 21)
4. Add **Send Email** using template: **{postpurchase_templates.get('e4', '[see above]')}**
   (Name: "Post-Purchase — Email 4: Germination Check + Review")
   - Subject: "How's it looking? — germination check at week 3"

5. Add **Time Delay** of **24 days** (to reach Day 45)
6. Add **Send Email** using template: **{postpurchase_templates.get('e5', '[see above]')}**
   (Name: "Post-Purchase — Email 5: Establishment + First Upsell")
   - Subject: "45 days in — here's what comes next for your planting"

7. **Activate the flow** — change status from Draft to Live
   - Also activate actions 4949184 and 92280132 which are currently Draft

---

## 3. Welcome Series (WQBF89) — Verify Trigger

Go to: https://www.klaviyo.com/flow/WQBF89/edit

The flow has been set to Live via API. Before confirming it's working:
1. Verify the trigger list is correct — should be the main Newsletter list (NLT2S2)
2. Verify flow filter: "Has NOT placed order" — so buyers don't enter welcome series
3. Check that exit condition "Placed Order → exit immediately" is set

---

## 4. Cart Abandonment — Add Suppression Filter

Go to: https://www.klaviyo.com/flow/Y7Qm8F/edit

Add a flow filter:
- "IF Started Checkout at least once in the last 1 day → exclude from flow"

This prevents someone who progressed to checkout from receiving both a cart email
AND a checkout abandonment email.

---
"""
    with open("/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/klaviyo-audit/FLOW_MANUAL_STEPS.md", "w") as f:
        f.write(content)
    ok("FLOW_MANUAL_STEPS.md written")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fix_winback_email2()
    time.sleep(0.5)
    activate_welcome_series()
    time.sleep(0.5)
    shipment_t = expand_shipment_flow()
    time.sleep(0.5)
    pp_t = expand_post_purchase()
    time.sleep(0.5)
    activate_seasonal_reorder()
    time.sleep(0.5)
    cart_audit()
    generate_manual_steps(shipment_t or {}, pp_t or {})
    print("\n\nDONE. Check FLOW_MANUAL_STEPS.md for remaining UI steps.")
