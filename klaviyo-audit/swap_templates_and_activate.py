"""
Klaviyo Flow Template Swap & Activation Script
Nature's Seed — March 6, 2026

Swaps old templates for new design-system templates on all flow emails,
updates subjects/previews, and activates flows.

API Limitations:
- CAN: swap templates, update subjects, change action/flow status
- CANNOT: add/delete flow actions (requires Klaviyo UI)
"""
import requests
import time
import json

API_KEY = "pk_3e5eaeec142f867fd8fca1b1f7820852ad"
BASE_URL = "https://a.klaviyo.com/api"
HEADERS = {
    "Authorization": f"Klaviyo-API-Key {API_KEY}",
    "revision": "2024-10-15",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

results = {"success": [], "failed": [], "skipped": []}


def api_patch(path, payload):
    r = requests.patch(f"{BASE_URL}/{path}", headers=HEADERS, json=payload)
    if r.status_code == 429:
        print("    [RATE LIMITED] Waiting 15s...")
        time.sleep(15)
        return api_patch(path, payload)
    return r


def swap_template(message_id, new_template_id, new_name, new_subject, new_preview):
    """Swap a flow message's template and update its metadata."""
    print(f"\n  Swapping message {message_id}:")
    print(f"    New template: {new_template_id}")
    print(f"    New name: {new_name}")
    print(f"    New subject: {new_subject}")

    # Step 1: Update template relationship
    r1 = requests.patch(
        f"{BASE_URL}/flow-messages/{message_id}/relationships/template/",
        headers=HEADERS,
        json={"data": {"type": "template", "id": new_template_id}}
    )
    if r1.status_code not in (200, 204):
        print(f"    [ERR] Template swap failed: {r1.status_code} {r1.text[:300]}")
        results["failed"].append(f"{message_id}: template swap ({r1.status_code})")
        return False

    print(f"    [OK] Template swapped to {new_template_id}")
    time.sleep(0.3)

    # Step 2: Update message name, subject, preview
    r2 = api_patch(f"flow-messages/{message_id}/", {
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
    if r2.status_code in (200, 204):
        print(f"    [OK] Subject/preview updated")
        results["success"].append(f"{message_id}: {new_name}")
        return True
    else:
        print(f"    [ERR] Metadata update failed: {r2.status_code} {r2.text[:300]}")
        results["failed"].append(f"{message_id}: metadata ({r2.status_code})")
        return False


def set_action_live(action_id, name=""):
    """Set a flow action to live status."""
    r = api_patch(f"flow-actions/{action_id}/", {
        "data": {
            "type": "flow-action",
            "id": action_id,
            "attributes": {"status": "live"}
        }
    })
    if r.status_code in (200, 204):
        print(f"  [OK] Action {action_id} ({name}) set to live")
        return True
    else:
        print(f"  [ERR] Action {action_id} status update: {r.status_code} {r.text[:200]}")
        return False


def set_flow_live(flow_id, name=""):
    """Set a flow to live status."""
    r = api_patch(f"flows/{flow_id}/", {
        "data": {
            "type": "flow",
            "id": flow_id,
            "attributes": {"status": "live"}
        }
    })
    if r.status_code in (200, 204):
        print(f"  [OK] Flow {flow_id} ({name}) set to live")
        return True
    else:
        print(f"  [ERR] Flow {flow_id} status: {r.status_code} {r.text[:200]}")
        return False


# ═══════════════════════════════════════════════════════════════
# FLOW 1: WINBACK (VvvqpW) — 2 emails, direct swap
# ═══════════════════════════════════════════════════════════════
def swap_winback():
    print("\n" + "=" * 60)
    print("  FLOW 1: WINBACK (VvvqpW)")
    print("=" * 60)

    # Email 1: TdDYQ2 (old: Y4TR79) → UesPJT (Winback E1 — Lawn)
    swap_template(
        message_id="TdDYQ2",
        new_template_id="UesPJT",
        new_name="Winback E1 — We Miss You",
        new_subject="We've been thinking about your lawn, {{ first_name|default:\"there\" }}",
        new_preview="It's been a while — here's what's new at Nature's Seed."
    )
    time.sleep(0.5)

    # Email 2: SDHWqD (old: WpZeXn) → TjLfX2 (Winback E2 — $20 Off Lawn)
    swap_template(
        message_id="SDHWqD",
        new_template_id="TjLfX2",
        new_name="Winback E2 — $20 Off Welcome Back",
        new_subject="$20 off — welcome back, {{ first_name|default:\"there\" }}",
        new_preview="Your offer expires in 48 hours. No minimum required."
    )


# ═══════════════════════════════════════════════════════════════
# FLOW 2: WELCOME SERIES (WQBF89) — 8 emails, map onto branches
# ═══════════════════════════════════════════════════════════════
def swap_welcome():
    print("\n" + "=" * 60)
    print("  FLOW 2: WELCOME SERIES (WQBF89)")
    print("=" * 60)
    print("  Mapping new E1-E8 templates onto existing branched structure:")
    print("    A-path (non-buyer): A1→E1, A2→E2, A3→E5, A4→E6, A5→E8")
    print("    B-path (buyer):     B1→E3, B2→E4, B3→E7")

    # A-PATH (non-buyer welcome)
    # A1: UraJZ3 (old: WdACvw) → WuLv5D (E1 Welcome to NS)
    # Wait — the flow data shows B1 as UraJZ3 "Welcome B1 - Buyer Welcome" and A1 as RZHNRV "Welcome A1 - Hero + Coupon"
    # Let me map correctly:
    # A1 (RZHNRV) → E1: Welcome to Nature's Seed
    swap_template(
        message_id="RZHNRV",
        new_template_id="WuLv5D",
        new_name="Welcome A1 — Welcome to Nature's Seed",
        new_subject="Welcome to Nature's Seed — here's 10% off your first order",
        new_preview="Your lawn journey starts here. Plus a welcome gift inside."
    )
    time.sleep(0.5)

    # A2 (UXyxgg) → E2: What Kind of Grower Are You?
    swap_template(
        message_id="UXyxgg",
        new_template_id="VaGpxm",
        new_name="Welcome A2 — What Kind of Grower Are You?",
        new_subject="What are you planting this season?",
        new_preview="Lawn, pasture, wildflower, or something else? We'll help you pick."
    )
    time.sleep(0.5)

    # A3 (RV6ywx) → E5: How to Seed Your Lawn Right (Education)
    swap_template(
        message_id="RV6ywx",
        new_template_id="URX8gR",
        new_name="Welcome A3 — How to Seed Your Lawn Right",
        new_subject="Tips for your planting project",
        new_preview="Step-by-step seeding guide from our agronomists."
    )
    time.sleep(0.5)

    # A4 (Xind3Y) → E6: Social Proof
    swap_template(
        message_id="Xind3Y",
        new_template_id="SaBqX4",
        new_name="Welcome A4 — What Customers Are Saying",
        new_subject="150,000+ customers planted with us last season",
        new_preview="See why growers across the country trust Nature's Seed."
    )
    time.sleep(0.5)

    # A5 (StukML) → E8: Last Chance Urgency Coupon
    swap_template(
        message_id="StukML",
        new_template_id="RLDDiN",
        new_name="Welcome A5 — Last Chance: Your 10% Off Expires",
        new_subject="Your 10% off expires tomorrow",
        new_preview="Don't miss your welcome discount — it's almost gone."
    )
    time.sleep(0.5)

    # B-PATH (buyer welcome)
    # B1 (UraJZ3) → E3: The Nature's Seed Difference
    swap_template(
        message_id="UraJZ3",
        new_template_id="WHPL42",
        new_name="Welcome B1 — The Nature's Seed Difference",
        new_subject="Thanks for your order — here's what makes us different",
        new_preview="Farm-direct, expert-blended, independently tested since 1994."
    )
    time.sleep(0.5)

    # B2 (VAzzST) → E4: Top Lawn Seed Picks
    swap_template(
        message_id="VAzzST",
        new_template_id="Tpt27A",
        new_name="Welcome B2 — Our Top Picks for You",
        new_subject="Did you know we also carry this?",
        new_preview="Products that pair perfectly with what you ordered."
    )
    time.sleep(0.5)

    # B3 (UkxuDD) → E7: Seeding Season Alert
    swap_template(
        message_id="UkxuDD",
        new_template_id="U6S54a",
        new_name="Welcome B3 — Seeding Season Is Here",
        new_subject="We'll remind you when it's time to plant",
        new_preview="Your seasonal planting calendar is ready."
    )


# ═══════════════════════════════════════════════════════════════
# FLOW 3: POST-PURCHASE (HRmUgq) — Swap 2 existing, activate
# ═══════════════════════════════════════════════════════════════
def swap_post_purchase():
    print("\n" + "=" * 60)
    print("  FLOW 3: POST-PURCHASE (HRmUgq)")
    print("=" * 60)

    # Email 1: Qq4pFH (old: JpKGxD) → SkzbPd (Post-Purchase E1 — Order Confirmed)
    swap_template(
        message_id="Qq4pFH",
        new_template_id="SkzbPd",
        new_name="Post-Purchase E1 — Order Confirmed + Seeding Guide",
        new_subject="Your order is confirmed — here's your seeding guide, {{ first_name|default:\"there\" }}",
        new_preview="Everything you need to get started with your new seed."
    )
    time.sleep(0.5)

    # Email 2: W4RdRQ (old: RExDqe) → V7HDqB (Post-Purchase E2 — How to Seed)
    swap_template(
        message_id="W4RdRQ",
        new_template_id="V7HDqB",
        new_name="Post-Purchase E2 — How to Seed Your Lawn Right",
        new_subject="Before you plant — these tips make all the difference",
        new_preview="Step-by-step guide to get the best results from your seed."
    )
    time.sleep(0.5)

    # Activate both email actions (currently draft)
    print("\n  Activating draft actions...")
    set_action_live("4949184", "Post-Purchase Email 1")
    time.sleep(0.3)
    set_action_live("92280132", "Post-Purchase Email 2")
    time.sleep(0.3)

    # Activate the flow
    set_flow_live("HRmUgq", "New Customer Thank You")

    print("\n  NOTE: Emails 3-5 need to be added in Klaviyo UI:")
    print(f"    E3 template: VPnshA (Day 7: Time to Plant)")
    print(f"    E4 template: Tfgfw4 (Day 21: Germination Check)")
    print(f"    E5 template: UfZPKu (Day 45: Established)")


# ═══════════════════════════════════════════════════════════════
# FLOW 4: SHIPMENT (UhxNKt) — Swap Email 1
# ═══════════════════════════════════════════════════════════════
def swap_shipment():
    print("\n" + "=" * 60)
    print("  FLOW 4: SHIPMENT (UhxNKt)")
    print("=" * 60)

    # Email 1: SdNq6D (old: UYWRG3) → Vbq9BG (Shipment E1 — On Its Way)
    swap_template(
        message_id="SdNq6D",
        new_template_id="Vbq9BG",
        new_name="Shipment E1 — Your Order Is On Its Way",
        new_subject="Get ready to plant — your seeds are on the way!",
        new_preview="Track your order + prep tips while you wait."
    )

    print("\n  NOTE: Emails 2-3 need to be added in Klaviyo UI:")
    print(f"    E2 template: WmqexU (Seed Arrives Today)")
    print(f"    E3 template: XKSkq9 (3-Day Check-In)")


# ═══════════════════════════════════════════════════════════════
# FLOW 5: CART ABANDONMENT (Y7Qm8F) — Swap 2 emails
# ═══════════════════════════════════════════════════════════════
def swap_cart_abandonment():
    print("\n" + "=" * 60)
    print("  FLOW 5: CART ABANDONMENT (Y7Qm8F)")
    print("=" * 60)

    # Email 1: RuwBmY (old: TgWuSt) → VyTbfz (Cart E1 — Left Something Behind)
    swap_template(
        message_id="RuwBmY",
        new_template_id="VyTbfz",
        new_name="Cart E1 — You Left Something Behind",
        new_subject="You left something behind, {{ first_name|default:\"there\" }}",
        new_preview="Your cart is waiting — don't miss out on these seeds."
    )
    time.sleep(0.5)

    # Email 2: Vx8UiM (old: XjyMPg) → QTR5Jv (Cart E2 — Still There?)
    swap_template(
        message_id="Vx8UiM",
        new_template_id="QTR5Jv",
        new_name="Cart E2 — Seed Season Moves Fast",
        new_subject="Still thinking it over? Seed season moves fast",
        new_preview="Your items won't last forever — complete your order today."
    )


# ═══════════════════════════════════════════════════════════════
# FLOW 6: UPSELL (VZsFVy) — Swap 2 emails
# ═══════════════════════════════════════════════════════════════
def swap_upsell():
    print("\n" + "=" * 60)
    print("  FLOW 6: UPSELL (VZsFVy)")
    print("=" * 60)

    # Email 1: XmTMDg (old: W8VGsK) → UuAkHu (Upsell E1 — Products That Go Great)
    swap_template(
        message_id="XmTMDg",
        new_template_id="UuAkHu",
        new_name="Upsell E1 — Products That Go Great with Your Seed",
        new_subject="Products that go great with your seed, {{ first_name|default:\"there\" }}",
        new_preview="Expert-picked complements to get the most from your planting."
    )
    time.sleep(0.5)

    # Email 2: VPQrbk (old: VjtT27) → UCr7i7 (Upsell E2 — Seasonal Calendar + Picks)
    swap_template(
        message_id="VPQrbk",
        new_template_id="UCr7i7",
        new_name="Upsell E2 — Seasonal Planting Calendar + Top Picks",
        new_subject="Your planting calendar + top picks for this season",
        new_preview="When to plant, what to add, and how to get the best results."
    )


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  KLAVIYO TEMPLATE SWAP & ACTIVATION")
    print("  Nature's Seed — March 6, 2026")
    print("=" * 60)

    swap_winback()
    time.sleep(1)

    swap_welcome()
    time.sleep(1)

    swap_post_purchase()
    time.sleep(1)

    swap_shipment()
    time.sleep(1)

    swap_cart_abandonment()
    time.sleep(1)

    swap_upsell()

    # ── SUMMARY ──
    print("\n\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"\n  Successful swaps: {len(results['success'])}")
    for s in results["success"]:
        print(f"    [OK] {s}")
    if results["failed"]:
        print(f"\n  Failed: {len(results['failed'])}")
        for f in results["failed"]:
            print(f"    [FAIL] {f}")
    if results["skipped"]:
        print(f"\n  Skipped: {len(results['skipped'])}")
        for s in results["skipped"]:
            print(f"    [SKIP] {s}")

    print("\n\n  REMAINING UI STEPS:")
    print("  ─────────────────────")
    print("  1. Post-Purchase (HRmUgq) — Add 3 emails in UI:")
    print("     • After E2, add Time Delay (5 days) → Email using template VPnshA")
    print("     • Add Time Delay (14 days) → Email using template Tfgfw4")
    print("     • Add Time Delay (24 days) → Email using template UfZPKu")
    print("")
    print("  2. Shipment (UhxNKt) — Add 2 emails in UI:")
    print("     • After E1, add Time Delay (1 day) → Email using template WmqexU")
    print("     • Add Time Delay (3 days) → Email using template XKSkq9")
    print("")
    print("  3. Browse Abandonment — New flow needed (or activate V2q3uA):")
    print("     • Lawn: T5ZuRM | Pasture: VZPd7B | Wildflower: Vg9TZ5 | General: WiUup2")
    print("")
    print("  4. Sunset — New flow needed:")
    print("     • E1: VuBUV6 | E2: XS3QTF")
    print("")
    print("  5. Welcome Series (WQBF89) — Consider restructuring to linear E1-E8")
    print("     in a future pass (currently mapped onto branched A/B structure)")
