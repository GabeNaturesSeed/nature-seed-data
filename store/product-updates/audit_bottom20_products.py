#!/usr/bin/env python3
"""
Audit and report content gaps for the bottom-20 Shopping products.
Outputs a JSON report with current state of each parent product.
"""

import requests
import time
import json
import html as html_lib
from pathlib import Path

# ── Credentials ──────────────────────────────────────────────────────────────
def _load_env():
    env = {}
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip().strip("'\"")] = v.strip().strip("'\"")
    import os
    for key in list(env.keys()):
        os_val = os.environ.get(key)
        if os_val is not None:
            env[key] = os_val
    return env

ENV = _load_env()
WC_CK = ENV.get("WC_CK", "")
WC_CS = ENV.get("WC_CS", "")
BASE = "https://naturesseed.com/wp-json/wc/v3"
AUTH = (WC_CK, WC_CS)

# 20 variation IDs from Shopping bottom-20
VARIATION_IDS = [
    447282, 451076, 458445, 455513, 458447, 451767, 457051, 458446,
    459554, 462926, 446837, 446806, 451769, 445869, 447375, 445278,
    447438, 445906, 447117, 446580
]

ACF_FIELDS = [
    "product_content_2",
    "product_card_content_1", "product_card_content_2", "product_card_content_3",
    "product_card_content_4", "product_card_content_5",
    "product_card_2_content_1", "product_card_2_content_2",
    "product_card_2_content_3", "product_card_2_content_4",
    "answer_content_1", "answer_content_2", "answer_content_3",
    "answer_content_4", "answer_content_5", "answer_content_6",
    "product_card_title_1", "product_card_title_2", "product_card_title_3",
    "product_card_title_4", "product_card_title_5",
]


def wc_get(path, params=None):
    r = requests.get(f"{BASE}{path}", auth=AUTH, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_variation(var_id):
    # Try as simple product first
    r = requests.get(f"{BASE}/products/{var_id}", auth=AUTH, timeout=30)
    if r.ok:
        p = r.json()
        if p.get("type") in ("simple", "variable"):
            return p, p["id"]
        # It's a variation — get parent
        parent_id = p.get("parent_id")
        if parent_id:
            time.sleep(0.3)
            pr = requests.get(f"{BASE}/products/{parent_id}", auth=AUTH, timeout=30)
            if pr.ok:
                return pr.json(), parent_id
    return None, None


def extract_acf(meta_data):
    result = {}
    for item in meta_data:
        if item["key"] in ACF_FIELDS:
            result[item["key"]] = item.get("value", "")
    return result


def char_len(s):
    if not s:
        return 0
    return len(str(s).strip())


print("=" * 70)
print("BOTTOM-20 SHOPPING PRODUCTS — CONTENT AUDIT")
print("=" * 70)

seen_parents = {}
report = []

for var_id in VARIATION_IDS:
    time.sleep(0.3)
    product, parent_id = get_variation(var_id)
    if not product:
        print(f"  [{var_id}] ERROR: could not fetch")
        continue

    if parent_id in seen_parents:
        seen_parents[parent_id]["variation_ids"].append(var_id)
        continue

    name = html_lib.unescape(product.get("name", ""))
    desc = product.get("description", "") or ""
    short = product.get("short_description", "") or ""
    meta = product.get("meta_data", [])
    acf = extract_acf(meta)

    desc_len = char_len(desc)
    short_len = char_len(short)
    acf_content2_len = char_len(acf.get("product_content_2", ""))
    card_count = sum(1 for i in range(1, 6) if char_len(acf.get(f"product_card_content_{i}", "")) > 20)
    card2_count = sum(1 for i in range(1, 5) if char_len(acf.get(f"product_card_2_content_{i}", "")) > 20)
    faq_count = sum(1 for i in range(1, 7) if char_len(acf.get(f"answer_content_{i}", "")) > 20)

    status = {
        "missing_desc": desc_len == 0,
        "missing_short": short_len == 0,
        "missing_acf_content2": acf_content2_len == 0,
        "low_cards": card_count < 3,
        "low_cards2": card2_count < 2,
        "low_faq": faq_count < 3,
    }
    needs_work = [k for k, v in status.items() if v]

    print(f"\n[{parent_id}] {name[:60]}")
    print(f"  desc={desc_len}ch  short={short_len}ch  content2={acf_content2_len}ch")
    print(f"  benefit_cards={card_count}/5  howto_cards={card2_count}/4  faq={faq_count}/6")
    if needs_work:
        print(f"  NEEDS: {', '.join(needs_work)}")
    else:
        print(f"  COMPLETE ✓")

    entry = {
        "parent_id": parent_id,
        "variation_id": var_id,
        "variation_ids": [var_id],
        "name": name,
        "slug": product.get("slug", ""),
        "desc_len": desc_len,
        "short_len": short_len,
        "acf_content2_len": acf_content2_len,
        "card_count": card_count,
        "card2_count": card2_count,
        "faq_count": faq_count,
        "needs_work": needs_work,
        "acf_sample": {k: (v[:100] if v else "") for k, v in acf.items() if v},
    }
    seen_parents[parent_id] = entry
    report.append(entry)

# Save report
out_path = Path(__file__).parent / "google-ads-audit" / "product_content_audit.json"
with open(out_path, "w") as f:
    json.dump(report, f, indent=2)

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
total = len(report)
needs_desc = sum(1 for r in report if r["missing_desc"] if "missing_desc" in r.get("needs_work", []))
needs_short = sum(1 for r in report if "missing_short" in r.get("needs_work", []))
needs_acf2 = sum(1 for r in report if "missing_acf_content2" in r.get("needs_work", []))
needs_cards = sum(1 for r in report if "low_cards" in r.get("needs_work", []))

print(f"  Total parent products: {total}")
print(f"  Missing description:   {needs_desc}")
print(f"  Missing short_desc:    {needs_short}")
print(f"  Missing ACF content2:  {needs_acf2}")
print(f"  Low benefit cards:     {needs_cards}")
print(f"\n  Report saved to: {out_path}")
