"""
Klaviyo Template Swap v2 — Overwrite old template HTML with new design system HTML.
Also updates flow message subjects/previews and activates flows.

Strategy: Instead of changing template relationships (not supported),
copy the HTML content from the new template INTO the old template.
"""
import requests
import time
import json

API_KEY = "pk_3e5eaeec142f867fd8fca1b1f7820852ad"
BASE_URL = "https://a.klaviyo.com/api"
REVISION = "2025-01-15"
HEADERS = {
    "Authorization": f"Klaviyo-API-Key {API_KEY}",
    "revision": REVISION,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

results = {"success": [], "failed": []}


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


def get_template_html(template_id):
    """Fetch the HTML content from a template."""
    r = api_get(f"templates/{template_id}/")
    if r.status_code == 200:
        return r.json()["data"]["attributes"].get("html", "")
    print(f"    [ERR] Could not fetch template {template_id}: {r.status_code}")
    return None


def overwrite_template(old_template_id, new_template_id, new_name):
    """Copy HTML from new template into old template, update name."""
    html = get_template_html(new_template_id)
    if html is None:
        results["failed"].append(f"{old_template_id}: could not read source {new_template_id}")
        return False

    r = api_patch(f"templates/{old_template_id}/", {
        "data": {
            "type": "template",
            "id": old_template_id,
            "attributes": {
                "name": new_name,
                "html": html
            }
        }
    })
    if r.status_code in (200, 204):
        print(f"    [OK] Template {old_template_id} overwritten with {new_template_id} content")
        return True
    else:
        print(f"    [ERR] Template overwrite failed: {r.status_code} {r.text[:300]}")
        results["failed"].append(f"{old_template_id}: overwrite ({r.status_code})")
        return False


def update_message(message_id, new_name, new_subject, new_preview):
    """Update flow message name, subject, preview."""
    r = api_patch(f"flow-messages/{message_id}/", {
        "data": {
            "type": "flow-message",
            "id": message_id,
            "attributes": {
                "name": new_name,
                "content": {
                    "subject": new_subject,
                    "preview_text": new_preview
                }
            }
        }
    })
    if r.status_code in (200, 204):
        print(f"    [OK] Message {message_id} metadata updated")
        results["success"].append(f"{message_id}: {new_name}")
        return True
    else:
        print(f"    [ERR] Message update failed: {r.status_code} {r.text[:300]}")
        results["failed"].append(f"{message_id}: message update ({r.status_code})")
        return False


def swap(message_id, old_tmpl, new_tmpl, msg_name, subject, preview):
    """Full swap: overwrite template HTML + update message metadata."""
    print(f"\n  [{msg_name}]")
    print(f"    Old template: {old_tmpl} → New source: {new_tmpl}")
    overwrite_template(old_tmpl, new_tmpl, msg_name)
    time.sleep(0.3)
    update_message(message_id, msg_name, subject, preview)
    time.sleep(0.3)


def set_action_live(action_id, name=""):
    r = api_patch(f"flow-actions/{action_id}/", {
        "data": {
            "type": "flow-action",
            "id": action_id,
            "attributes": {"status": "live"}
        }
    })
    if r.status_code in (200, 204):
        print(f"  [OK] Action {action_id} ({name}) → live")
    else:
        print(f"  [ERR] Action {action_id}: {r.status_code} {r.text[:200]}")


def set_flow_live(flow_id, name=""):
    r = api_patch(f"flows/{flow_id}/", {
        "data": {
            "type": "flow",
            "id": flow_id,
            "attributes": {"status": "live"}
        }
    })
    if r.status_code in (200, 204):
        print(f"  [OK] Flow {flow_id} ({name}) → live")
    else:
        print(f"  [ERR] Flow {flow_id}: {r.status_code} {r.text[:200]}")


# ═══════════════════════════════════════════════════════════════
# FLOW 1: WINBACK (VvvqpW) — 2 emails
# ═══════════════════════════════════════════════════════════════
def do_winback():
    print("\n" + "=" * 60)
    print("  FLOW 1: WINBACK (VvvqpW)")
    print("=" * 60)

    swap("TdDYQ2", "Y4TR79", "UesPJT",
         "Winback E1 — We Miss You",
         "We've been thinking about your lawn, {{ first_name|default:\"there\" }}",
         "It's been a while — here's what's new at Nature's Seed.")

    swap("SDHWqD", "WpZeXn", "TjLfX2",
         "Winback E2 — $20 Off Welcome Back",
         "$20 off — welcome back, {{ first_name|default:\"there\" }}",
         "Your offer expires in 48 hours. No minimum required.")


# ═══════════════════════════════════════════════════════════════
# FLOW 2: WELCOME SERIES (WQBF89) — 8 emails across A/B branches
# ═══════════════════════════════════════════════════════════════
def do_welcome():
    print("\n" + "=" * 60)
    print("  FLOW 2: WELCOME SERIES (WQBF89)")
    print("=" * 60)

    # A-path (non-buyer)
    swap("RZHNRV", "TN9Gnq", "WuLv5D",
         "Welcome A1 — Welcome to Nature's Seed",
         "Welcome to Nature's Seed — here's 10% off your first order",
         "Your lawn journey starts here. Plus a welcome gift inside.")

    swap("UXyxgg", "WKYqLK", "VaGpxm",
         "Welcome A2 — What Kind of Grower Are You?",
         "What are you planting this season?",
         "Lawn, pasture, wildflower — we'll help you pick the right seed.")

    swap("RV6ywx", "THws32", "URX8gR",
         "Welcome A3 — How to Seed Your Lawn Right",
         "Tips for your planting project",
         "Step-by-step seeding guide from our agronomists.")

    swap("Xind3Y", "Ri5vTU", "SaBqX4",
         "Welcome A4 — What Customers Are Saying",
         "150,000+ customers planted with us last season",
         "See why growers across the country trust Nature's Seed.")

    swap("StukML", "UfUeif", "RLDDiN",
         "Welcome A5 — Last Chance: Your 10% Off Expires",
         "Your 10% off expires tomorrow",
         "Don't miss your welcome discount — it's almost gone.")

    # B-path (buyer)
    swap("UraJZ3", "WdACvw", "WHPL42",
         "Welcome B1 — The Nature's Seed Difference",
         "Thanks for your order — here's what makes us different",
         "Farm-direct, expert-blended, independently tested since 1994.")

    swap("VAzzST", "RnGLfi", "Tpt27A",
         "Welcome B2 — Our Top Picks for You",
         "Did you know we also carry this?",
         "Products that pair perfectly with what you ordered.")

    swap("UkxuDD", "W8Xna8", "U6S54a",
         "Welcome B3 — Seeding Season Is Here",
         "We'll remind you when it's time to plant",
         "Your seasonal planting calendar is ready.")


# ═══════════════════════════════════════════════════════════════
# FLOW 3: POST-PURCHASE (HRmUgq) — 2 existing emails + activate
# ═══════════════════════════════════════════════════════════════
def do_post_purchase():
    print("\n" + "=" * 60)
    print("  FLOW 3: POST-PURCHASE (HRmUgq)")
    print("=" * 60)

    swap("Qq4pFH", "JpKGxD", "SkzbPd",
         "Post-Purchase E1 — Order Confirmed + Seeding Guide",
         "Your order is confirmed — here's your seeding guide, {{ first_name|default:\"there\" }}",
         "Everything you need to get started with your new seed.")

    swap("W4RdRQ", "RExDqe", "V7HDqB",
         "Post-Purchase E2 — How to Seed Your Lawn Right",
         "Before you plant — these tips make all the difference",
         "Step-by-step guide to get the best results from your seed.")

    # Activate draft actions
    print("\n  Activating draft actions...")
    set_action_live("4949184", "E1")
    time.sleep(0.3)
    set_action_live("92280132", "E2")
    time.sleep(0.3)

    # Activate flow
    set_flow_live("HRmUgq", "Post-Purchase")


# ═══════════════════════════════════════════════════════════════
# FLOW 4: SHIPMENT (UhxNKt) — 1 email
# ═══════════════════════════════════════════════════════════════
def do_shipment():
    print("\n" + "=" * 60)
    print("  FLOW 4: SHIPMENT (UhxNKt)")
    print("=" * 60)

    swap("SdNq6D", "UYWRG3", "Vbq9BG",
         "Shipment E1 — Your Order Is On Its Way",
         "Get ready to plant — your seeds are on the way!",
         "Track your order + prep tips while you wait.")


# ═══════════════════════════════════════════════════════════════
# FLOW 5: CART ABANDONMENT (Y7Qm8F) — 2 emails
# ═══════════════════════════════════════════════════════════════
def do_cart():
    print("\n" + "=" * 60)
    print("  FLOW 5: CART ABANDONMENT (Y7Qm8F)")
    print("=" * 60)

    swap("RuwBmY", "TgWuSt", "VyTbfz",
         "Cart E1 — You Left Something Behind",
         "You left something behind, {{ first_name|default:\"there\" }}",
         "Your cart is waiting — don't miss out on these seeds.")

    swap("Vx8UiM", "XjyMPg", "QTR5Jv",
         "Cart E2 — Seed Season Moves Fast",
         "Still thinking it over? Seed season moves fast",
         "Your items won't last forever — complete your order today.")


# ═══════════════════════════════════════════════════════════════
# FLOW 6: UPSELL (VZsFVy) — 2 emails
# ═══════════════════════════════════════════════════════════════
def do_upsell():
    print("\n" + "=" * 60)
    print("  FLOW 6: UPSELL (VZsFVy)")
    print("=" * 60)

    swap("XmTMDg", "W8VGsK", "UuAkHu",
         "Upsell E1 — Products That Go Great with Your Seed",
         "Products that go great with your seed, {{ first_name|default:\"there\" }}",
         "Expert-picked complements to get the most from your planting.")

    swap("VPQrbk", "VjtT27", "UCr7i7",
         "Upsell E2 — Seasonal Calendar + Top Picks",
         "Your planting calendar + top picks for this season",
         "When to plant, what to add, and how to get the best results.")


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  KLAVIYO TEMPLATE SWAP v2")
    print("  Strategy: Overwrite old template HTML with new design")
    print("  Nature's Seed — March 6, 2026")
    print("=" * 60)

    do_winback()
    time.sleep(0.5)
    do_welcome()
    time.sleep(0.5)
    do_post_purchase()
    time.sleep(0.5)
    do_shipment()
    time.sleep(0.5)
    do_cart()
    time.sleep(0.5)
    do_upsell()

    # SUMMARY
    print("\n\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    print(f"\n  Successful: {len(results['success'])}")
    for s in results["success"]:
        print(f"    [OK] {s}")
    if results["failed"]:
        print(f"\n  Failed: {len(results['failed'])}")
        for f in results["failed"]:
            print(f"    [FAIL] {f}")

    print("\n  REMAINING UI STEPS:")
    print("  ─────────────────────")
    print("  1. Post-Purchase (HRmUgq) — Add Emails 3-5:")
    print("     • Time Delay 5d → Email template VPnshA (Day 7: Time to Plant)")
    print("     • Time Delay 14d → Email template Tfgfw4 (Day 21: Germination Check)")
    print("     • Time Delay 24d → Email template UfZPKu (Day 45: Established)")
    print("")
    print("  2. Shipment (UhxNKt) — Add Emails 2-3:")
    print("     • Time Delay 1d → Email template WmqexU (Seed Arrives Today)")
    print("     • Time Delay 3d → Email template XKSkq9 (3-Day Check-In)")
    print("")
    print("  3. Browse Abandonment — Build or activate flow:")
    print("     • Lawn: T5ZuRM | Pasture: VZPd7B | Wildflower: Vg9TZ5 | General: WiUup2")
    print("")
    print("  4. Sunset Flow — Build new flow:")
    print("     • E1: VuBUV6 | E2: XS3QTF")
