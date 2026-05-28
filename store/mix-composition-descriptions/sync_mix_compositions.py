#!/usr/bin/env python3
"""
Sync mix compositions from mix-compositions.xml → WooCommerce ACF repeater.

For each SKU in the XML:
  1. Find the WooCommerce product by SKU.
  2. Read current mix_components ACF repeater rows.
  3. Compare to XML (by common_name + percentage).
  4. If different → generate per-species descriptions via Claude API,
     then write new mix_components rows to WC.

Exit code 0 = success (updates may or may not have been needed).
Prints a JSON summary to stdout on completion.

Secrets required (env vars):
  WC_CK, WC_CS           — WooCommerce consumer key / secret
  CF_WORKER_URL           — Cloudflare proxy URL (required in prod)
  CF_WORKER_SECRET        — Cloudflare proxy secret
  ANTHROPIC_API_KEY       — Claude API key
"""

import os, sys, json, base64, time, xml.etree.ElementTree as ET
import requests

# ── Config ────────────────────────────────────────────────────────────────────
XML_URL = (
    "https://raw.githubusercontent.com/ekkurpgeweit/nature-seed-mix-feed/main"
    "/mix-compositions.xml"
)
WC_BASE = "https://naturesseed.com/wp-json/wc/v3"
CLAUDE_MODEL = "claude-sonnet-4-6"
RATE_LIMIT_SLEEP = 0.35  # seconds between WC bulk calls

# ACF field references (must match the field keys registered in WP)
REF_COUNT   = "field_mix_components"
REF_SPECIES = "field_mix_species_name"
REF_PCT     = "field_mix_percentage"
REF_DESC    = "field_mix_description"

# ── Credentials ──────────────────────────────────────────────────────────────
WC_CK            = os.environ["WC_CK"]
WC_CS            = os.environ["WC_CS"]
CF_WORKER_URL    = os.environ.get("CF_WORKER_URL", "").strip()
CF_WORKER_SECRET = os.environ.get("CF_WORKER_SECRET", "").strip()
ANTHROPIC_KEY    = os.environ["ANTHROPIC_API_KEY"]

_wc_creds = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()


# ── WooCommerce API helper ────────────────────────────────────────────────────
def wc(method: str, path: str, body=None, params=None):
    params = dict(params or {})
    params["_"] = int(time.time())
    headers = {
        "Authorization": f"Basic {_wc_creds}",
        "Content-Type": "application/json",
    }
    if CF_WORKER_URL:
        params["wc_path"] = f"/{path.lstrip('/')}"
        headers["X-Proxy-Secret"] = CF_WORKER_SECRET
        url = CF_WORKER_URL
    else:
        url = f"{WC_BASE}/{path.lstrip('/')}"

    r = requests.request(method, url, json=body, params=params, headers=headers, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"{method.upper()} {path} → {r.status_code}: {r.text[:300]}")
    return r.json()


# ── Claude API helper ─────────────────────────────────────────────────────────
def claude_descriptions(mix_name: str, category: str, components: list[dict]) -> list[str]:
    """
    Ask Claude to write a 1-2 sentence description for each species explaining
    why it was chosen for this particular mix.

    Returns a list of strings, one per component, in the same order.
    """
    species_list = "\n".join(
        f"  {i+1}. {c['common_name']} ({c['species']}"
        + (f", var. {c['variety']}" if c.get("variety") and c["variety"] != "VNS" else "")
        + f") — {c['percentage']}%"
        for i, c in enumerate(components)
    )

    prompt = f"""You are writing product page copy for Nature's Seed, a premium seed company.

Mix name: {mix_name}
Category: {category}

Seed components:
{species_list}

For each species listed above, write exactly ONE sentence (25–40 words) explaining why it was chosen for this specific mix — focusing on the agronomic, ecological, or performance benefit it provides to a customer using this product. Ground every description in the mix's purpose ({category}).

Return a JSON array of strings, one per species, in the same order as the list above. No extra keys, no markdown fences — just the raw JSON array.
"""

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        json=payload,
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        timeout=60,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Claude API {r.status_code}: {r.text[:300]}")

    raw = r.json()["content"][0]["text"].strip()
    # Strip markdown fences if Claude added them anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    descs = json.loads(raw)
    if len(descs) != len(components):
        raise ValueError(f"Claude returned {len(descs)} descriptions, expected {len(components)}")
    return descs


# ── Parse XML ─────────────────────────────────────────────────────────────────
def load_xml() -> list[dict]:
    r = requests.get(XML_URL, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    mixes = []
    for mix_el in root.findall("mix"):
        components = []
        for comp in mix_el.find("components").findall("component"):
            components.append({
                "code":        comp.findtext("code", "").strip(),
                "common_name": comp.findtext("common_name", "").strip(),
                "species":     comp.findtext("species", "").strip(),
                "variety":     comp.findtext("variety", "").strip(),
                "percentage":  comp.findtext("percentage", "0").strip(),
            })
        mixes.append({
            "sku":        mix_el.get("sku", "").strip(),
            "category":   mix_el.get("category", "").strip(),
            "name":       mix_el.findtext("name", "").strip(),
            "components": components,
        })
    return mixes


# ── Read current WC mix ───────────────────────────────────────────────────────
def read_current_mix(meta_data: list[dict]) -> list[dict]:
    """Extract current mix_components rows from WC meta_data."""
    by_key = {m["key"]: m["value"] for m in meta_data}
    count_str = by_key.get("mix_components", "0")
    try:
        count = int(count_str)
    except (ValueError, TypeError):
        count = 0

    rows = []
    for i in range(count):
        rows.append({
            "species_name": by_key.get(f"mix_components_{i}_species_name", ""),
            "percentage":   by_key.get(f"mix_components_{i}_percentage", "0"),
            "description":  by_key.get(f"mix_components_{i}_description", ""),
        })
    return rows


# ── Diff ──────────────────────────────────────────────────────────────────────
def needs_update(current_rows: list[dict], xml_components: list[dict]) -> bool:
    """
    Return True if the number of rows or any (species_name, percentage) pair differs.
    Descriptions are not compared — they are always regenerated when composition changes.
    """
    if len(current_rows) != len(xml_components):
        return True
    for cur, xml_c in zip(current_rows, xml_components):
        if cur["species_name"] != xml_c["common_name"]:
            return True
        # Normalize percentage: "25.00" == "25"
        try:
            if abs(float(cur["percentage"]) - float(xml_c["percentage"])) > 0.01:
                return True
        except (ValueError, TypeError):
            return True
    return False


# ── Build PUT payload ─────────────────────────────────────────────────────────
def build_meta_payload(
    existing_meta: list[dict],
    components: list[dict],
    descriptions: list[str],
) -> list[dict]:
    id_map = {m["key"]: m["id"] for m in existing_meta if "id" in m}

    def entry(key, value):
        if key in id_map:
            return {"id": id_map[key], "key": key, "value": value}
        return {"key": key, "value": value}

    payload = [
        entry("mix_components", str(len(components))),
        entry("_mix_components", REF_COUNT),
    ]
    for i, (comp, desc) in enumerate(zip(components, descriptions)):
        payload.append(entry(f"mix_components_{i}_species_name", comp["common_name"]))
        payload.append(entry(f"_mix_components_{i}_species_name", REF_SPECIES))
        payload.append(entry(f"mix_components_{i}_percentage", comp["percentage"]))
        payload.append(entry(f"_mix_components_{i}_percentage", REF_PCT))
        payload.append(entry(f"mix_components_{i}_description", desc))
        payload.append(entry(f"_mix_components_{i}_description", REF_DESC))
    return payload


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Loading XML…")
    mixes = load_xml()
    print(f"  {len(mixes)} mixes in feed")

    results = {"updated": [], "skipped": [], "not_found": [], "errors": []}

    for mix in mixes:
        sku  = mix["sku"]
        name = mix["name"]
        comps = mix["components"]

        # Find WC product by SKU
        try:
            products = wc("get", "products", params={"sku": sku, "per_page": 5})
        except Exception as e:
            print(f"  [ERROR] {sku}: WC lookup failed — {e}")
            results["errors"].append({"sku": sku, "error": str(e)})
            continue

        if not products:
            # Try variations (parent lookup)
            try:
                variations = wc("get", "products", params={"sku": sku, "type": "variation", "per_page": 5})
                if variations:
                    pid = variations[0].get("parent_id")
                    if pid:
                        products = [wc("get", f"products/{pid}")]
            except Exception:
                pass

        if not products:
            print(f"  [NOT FOUND] {sku}")
            results["not_found"].append(sku)
            time.sleep(RATE_LIMIT_SLEEP)
            continue

        product = products[0]
        pid = product["id"]
        meta = product.get("meta_data", [])
        current = read_current_mix(meta)

        if not needs_update(current, comps):
            print(f"  [OK] {sku} ({name}) — no change")
            results["skipped"].append(sku)
            time.sleep(RATE_LIMIT_SLEEP)
            continue

        print(f"  [UPDATE] {sku} ({name}): {len(current)} rows → {len(comps)} rows")

        # Generate descriptions via Claude
        try:
            descs = claude_descriptions(name, mix["category"], comps)
        except Exception as e:
            print(f"    Claude error: {e}")
            results["errors"].append({"sku": sku, "error": f"Claude: {e}"})
            time.sleep(RATE_LIMIT_SLEEP)
            continue

        # Build and push payload
        payload = build_meta_payload(meta, comps, descs)
        try:
            wc("put", f"products/{pid}", body={"meta_data": payload})
            print(f"    ✓ Updated product {pid}")
            results["updated"].append({"sku": sku, "pid": pid, "rows": len(comps)})
        except Exception as e:
            print(f"    WC update error: {e}")
            results["errors"].append({"sku": sku, "error": f"WC PUT: {e}"})

        time.sleep(RATE_LIMIT_SLEEP)

    # Summary
    print("\n── Summary ──────────────────────────────────────────────")
    print(f"  Updated  : {len(results['updated'])}")
    print(f"  No change: {len(results['skipped'])}")
    print(f"  Not found: {len(results['not_found'])}")
    print(f"  Errors   : {len(results['errors'])}")
    print(json.dumps(results, indent=2))

    if results["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
