#!/usr/bin/env python3
"""
Walmart SEO content generator for Nature's Seed products.

Generates optimized:
  - Titles (50-75 chars, keyword-front-loaded)
  - Descriptions (150-1000 words, HTML)
  - Key Features (3-5 bullets)
  - Plant Seeds attributes

Cross-references Walmart items with WooCommerce product data.
"""

import re
import json
from pathlib import Path

# ============================================================
# USDA HARDINESS ZONE MAP (from EcommEngineGGS)
# ============================================================

USDA_ZONE_MAP = {
    "2750AL-A": None,
    "LAWN-BUDA": ["7a", "10b"],
    "CV-BGEC": ["3a", "7b"],
    "CV-CHM": ["4a", "8b"],
    "CV-CNEC": ["4a", "8b"],
    "CV-CNFW": ["3a", "7b"],
    "CV-NEC": ["3a", "7b"],
    "PB-ALPACA": ["2a", "10b"],
    "PB-BIRD": ["3a", "11b"],
    "PB-CABIN": ["3a", "7b"],
    "PB-CHIX": ["3a", "9b"],
    "PB-CHSS": ["8a", "10b"],
    "PB-CLV": ["3a", "11a"],
    "PB-COSS": ["8b", "11b"],
    "PB-COW-NTR": ["3a", "11b"],
    "PB-COW-SO": ["8a", "11b"],
    "PB-FULL": ["3a", "11b"],
    "PB-GAME": ["3a", "11b"],
    "PB-GOAT-N": ["3a", "5b"],
    "PB-GOAT-SO": ["8a", "11b"],
    "PB-GOAT-TR": ["6a", "8a"],
    "PB-GRSC": ["3a", "11b"],
    "PB-HONEY": ["3a", "11b"],
    "PB-HRSE-N": ["3a", "5b"],
    "PB-HRSE-SO": ["8a", "11b"],
    "PB-HRSE-TR": ["6a", "8a"],
    "PB-IR": ["3a", "7b"],
    "PB-KRMU": ["3a", "11b"],
    "PB-MUST": ["3a", "11b"],
    "PB-PIG": ["3a", "11b"],
    "PB-PLPR": ["3a", "7b"],
    "PB-SGPR": ["3a", "7b"],
    "PB-SHADE": ["3a", "8a"],
    "PB-SHEP-N": ["3a", "5b"],
    "PB-SHEP-SO": ["8a", "11b"],
    "PB-SHEP-TR": ["6a", "8a"],
    "PB-SHPR": ["3a", "7b"],
    "PB-TORT": ["7a", "10b"],
    "PG-BOGR": ["3a", "10b"],
    "PG-BUCK": ["3a", "11b"],
    "PG-BUDA": ["3a", "9b"],
    "PG-CYDA": ["7a", "11b"],
    "PG-DAGL": ["3a", "9b"],
    "PG-FEAR2": ["3a", "9b"],
    "PG-LOPE": ["3a", "9b"],
    "PG-MESA": ["2a", "9b"],
    "PG-PANO": ["7a", "10b"],
    "PG-PAVI": ["3a", "9b"],
    "PG-PHPR": ["2a", "8b"],
    "PG-POPR": ["3a", "8b"],
    "PG-SECE": ["2a", "9b"],
    "PG-TRRE": ["3a", "11a"],
    "S-AGPA8": ["4a", "9b"],
    "S-DUTCH": ["3a", "11a"],
    "S-FEOV": ["6a", "11b"],
    "S-INNOC": None,
    "S-MICRO": ["3a", "11a"],
    "S-RICE": None,
    "S-TACKI": None,
    "TURF-BERM": ["7a", "10b"],
    "TURF-CLV": ["3a", "11a"],
    "TURF-FINE": ["3a", "7b"],
    "TURF-HLB": ["3a", "8a"],
    "TURF-JBR": ["3a", "7b"],
    "TURF-MLB": ["3a", "8a"],
    "TURF-NFF": ["4a", "8b"],
    "TURF-W-BLUE": ["3a", "7b"],
    "TURF-W-BLUE-BUNDLE": ["3a", "7b"],
    "TURF-W-BR": ["3a", "8a"],
    "TURF-W-RYE": ["3a", "9b"],
    "TURF-W-SS": ["3a", "7b"],
    "TURF-W-TALL": ["4a", "8b"],
    "TURF-WSHD": ["3a", "7b"],
    "WB-AN": ["3a", "11b"],
    "WB-CALN": ["4a", "9b"],
    "WB-CCN": ["4a", "9b"],
    "WB-DR": ["7a", "11b"],
    "WB-RM": ["3a", "7b"],
    "WB-SD": ["3a", "7b"],
    "WB-XCVP": ["3a", "8b"],
    "W-ACLA": ["3a", "7b"],
    "W-ASFA": ["3a", "7b"],
    "W-DIAUA": ["3a", "7b"],
    "W-ENCA": ["3a", "7b"],
    "W-ENFA": ["3a", "7b"],
    "W-ERCO": ["3a", "7b"],
    "W-ESCA": ["3a", "7b"],
    "W-LUBI": ["3a", "7b"],
    "W-LUMI": ["3a", "7b"],
    "W-LUSU": ["3a", "7b"],
    "W-NAPU": ["3a", "7b"],
    "W-SAAP": ["3a", "7b"],
    "W-SIBE": ["3a", "7b"],
    "BDL-POL": ["4a", "9b"],
    "CV-CNIR": ["3a", "7b"],
}

# Category mapping based on SKU prefix
CATEGORY_MAP = {
    "PG-": "Grass Seeds",
    "PB-": "Grass Seeds",
    "S-": "Grass Seeds",
    "TURF-": "Grass Seeds",
    "LAWN-": "Grass Seeds",
    "CV-": "Grass Seeds",
    "W-": "Wildflower Seeds",
    "WB-": "Wildflower Seeds",
    "BDL-": "Grass Seeds",
}

# Plant category for Walmart attributes
PLANT_CATEGORY_MAP = {
    "PG-": "Grasses",
    "PB-": "Grasses",
    "S-": "Grasses",
    "TURF-": "Grasses",
    "LAWN-": "Grasses",
    "CV-": "Grasses",
    "W-": "Flowers",
    "WB-": "Flowers",
    "BDL-": "Grasses",
}


# ============================================================
# HELPERS
# ============================================================

def get_base_sku(sku):
    """Extract base SKU (e.g., PB-ALPACA-10-LB-KIT → PB-ALPACA)."""
    s = sku.upper().strip()
    s = re.sub(r"-KIT$", "", s)
    s = re.sub(r"-ADDON$", "", s)
    s = re.sub(r"-[\d.]+-(?:LB|LBS|OZ)$", "", s)
    s = re.sub(r"-BUNDLE$", "", s)
    return s


def get_weight_from_sku(sku):
    """Extract weight string from SKU (e.g., '10 lb')."""
    m = re.search(r"([\d.]+)-(LB|LBS|OZ)", sku.upper())
    if m:
        num = m.group(1)
        unit = m.group(2).replace("LBS", "lb").replace("LB", "lb").replace("OZ", "oz")
        return f"{num} {unit}"
    return None


def get_coverage_from_name(name):
    """Extract coverage from product name (e.g., 'Covers 50,000 Sq Ft')."""
    m = re.search(r"Covers\s+([\d,]+)\s+S", name, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def get_product_type(sku):
    """Determine Walmart product type from SKU."""
    upper = sku.upper()
    for prefix, ptype in CATEGORY_MAP.items():
        if upper.startswith(prefix):
            return ptype
    return "Grass Seeds"


def get_plant_category(sku):
    """Determine plant category for Walmart attributes."""
    upper = sku.upper()
    for prefix, cat in PLANT_CATEGORY_MAP.items():
        if upper.startswith(prefix):
            return cat
    return "Grasses"


def get_usda_zones(sku):
    """Look up USDA hardiness zones for a SKU."""
    base = get_base_sku(sku)
    # Try exact base match, then progressively shorter prefixes
    if base in USDA_ZONE_MAP:
        return USDA_ZONE_MAP[base]

    # Try without trailing parts
    parts = base.split("-")
    for i in range(len(parts), 1, -1):
        prefix = "-".join(parts[:i])
        if prefix in USDA_ZONE_MAP:
            return USDA_ZONE_MAP[prefix]

    return None


def get_wc_meta(wc_product, key, default=""):
    """Get a meta_data value from a WC product."""
    for m in wc_product.get("meta_data", []):
        if m["key"] == key:
            return m.get("value", default) or default
    return default


def clean_product_name(name):
    """Clean up product name — remove coverage/weight suffixes."""
    # Remove " - 10 lb - Covers 50,000 Sq Ft" suffixes
    name = re.sub(r"\s*-\s*[\d.]+\s*(?:lb|lbs|oz)\s*-\s*Covers.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*-\s*[\d.]+\s*(?:lb|lbs|oz)$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*-\s*[\d.]+\s*Lbs\s*-\s*[\d,]+\s*Sq\s*Ft.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*-\s*Covers.*$", "", name, flags=re.IGNORECASE)
    return name.strip()


def strip_html_to_text(html_str):
    """Strip all HTML tags and normalize whitespace from a string."""
    text = re.sub(r"<[^>]+>", " ", html_str)
    text = re.sub(r"<!--.*?-->", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sanitize_html(html_str):
    """
    Sanitize HTML for Walmart — keep only allowed tags.
    Walmart allows: p, b, ul, ol, li, br, strong, em, i
    Remove: div, span, h1-h6, style attrs, Notion comments, etc.
    """
    # Remove HTML comments (including Notion VC comments)
    html_str = re.sub(r"<!--.*?-->", "", html_str, flags=re.DOTALL)
    # Remove <span> tags but keep content
    html_str = re.sub(r"<span[^>]*>", "", html_str)
    html_str = re.sub(r"</span>", "", html_str)
    # Remove <div> tags but keep content
    html_str = re.sub(r"<div[^>]*>", "", html_str)
    html_str = re.sub(r"</div>", "", html_str)
    # Remove <h1>-<h6> tags, replace with <b>
    html_str = re.sub(r"<h[1-6][^>]*>", "<b>", html_str)
    html_str = re.sub(r"</h[1-6]>", "</b>", html_str)
    # Strip style attributes from remaining tags
    html_str = re.sub(r'\s+style="[^"]*"', "", html_str)
    html_str = re.sub(r"\s+style='[^']*'", "", html_str)
    # Remove &nbsp;
    html_str = re.sub(r"&nbsp;", " ", html_str)
    # Clean up excessive whitespace and newlines
    html_str = re.sub(r"\r\n", "\n", html_str)
    html_str = re.sub(r"\n{3,}", "\n\n", html_str)
    html_str = re.sub(r"  +", " ", html_str)
    return html_str.strip()


# ============================================================
# CONTENT GENERATORS
# ============================================================

def generate_title(wm_item, wc_product=None):
    """
    Generate Walmart-optimized title (50-75 chars, max 90).
    Formula: Nature's Seed {Product Name} - {Weight}
    """
    name = wm_item.get("productName", "")
    sku = wm_item.get("sku", "")

    # Clean the name
    clean_name = clean_product_name(name)
    weight = get_weight_from_sku(sku)

    # Remove "Nature's Seed" if already present
    clean_name = re.sub(r"^Nature'?s?\s+Seed\s+", "", clean_name, flags=re.IGNORECASE)

    # Build title
    if weight:
        title = f"Nature's Seed {clean_name} - {weight}"
    else:
        title = f"Nature's Seed {clean_name}"

    # Title case
    title = title.title()
    # Fix common title case issues
    title = title.replace("'S", "'s")
    title = title.replace(" And ", " and ")
    title = title.replace(" Of ", " of ")
    title = title.replace(" For ", " for ")
    title = title.replace(" The ", " the ")
    title = title.replace(" In ", " in ")
    title = title.replace(" Or ", " or ")
    title = title.replace("Sq Ft", "sq ft")
    # Make sure Nature's Seed stays capitalized
    title = re.sub(r"^Nature's Seed", "Nature's Seed", title, flags=re.IGNORECASE)

    # Truncate to 90 chars if needed
    if len(title) > 90:
        title = title[:87] + "..."

    return title


def generate_description(wm_item, wc_product=None):
    """
    Generate Walmart-optimized HTML description (150-1000 words).
    Uses WC product data when available.
    """
    sku = wm_item.get("sku", "")
    name = clean_product_name(wm_item.get("productName", ""))
    weight = get_weight_from_sku(sku)
    coverage = get_coverage_from_name(wm_item.get("productName", ""))

    parts = []

    # Opening paragraph
    if wc_product:
        content2 = get_wc_meta(wc_product, "product_content_2")
        if content2:
            # Strip any existing HTML, use first 2 sentences
            clean_content = strip_html_to_text(content2)
            sentences = re.split(r'(?<=[.!?])\s+', clean_content)
            opener = " ".join(sentences[:2])
            parts.append(f"<p>{opener}</p>")
        else:
            parts.append(f"<p>{name} from Nature's Seed is a premium seed product designed for optimal germination and establishment. "
                        f"Each batch is tested for purity and germination to ensure the best results.</p>")
    else:
        parts.append(f"<p>{name} from Nature's Seed is a premium seed product designed for optimal germination and establishment. "
                    f"Each batch is tested for purity and germination to ensure the best results.</p>")

    # Key Benefits section
    if wc_product:
        highlights = []
        for i in range(1, 6):
            h = get_wc_meta(wc_product, f"product_highlight_{i}")
            if h:
                highlights.append(h)

        if highlights:
            parts.append("<p><b>Key Benefits:</b></p>")
            parts.append("<ul>")
            for h in highlights:
                parts.append(f"<li>{h}</li>")
            parts.append("</ul>")

    # Growing Information
    if wc_product:
        sun = get_wc_meta(wc_product, "sun_requirements")
        soil = get_wc_meta(wc_product, "soil_preference")
        seeding_rate = get_wc_meta(wc_product, "seeding_rate")
        planting_depth = get_wc_meta(wc_product, "planting_depth")

        if any([sun, soil, seeding_rate, planting_depth]):
            parts.append("<p><b>Growing Information:</b></p>")
            parts.append("<ul>")
            if sun:
                parts.append(f"<li>Sun: {sun}</li>")
            if soil:
                parts.append(f"<li>Soil: {soil}</li>")
            if seeding_rate:
                parts.append(f"<li>Seeding Rate: {seeding_rate}</li>")
            if planting_depth:
                parts.append(f"<li>Planting Depth: {planting_depth}</li>")
            parts.append("</ul>")

    # Uses
    if wc_product:
        uses = get_wc_meta(wc_product, "detail_5_uses")
        if uses:
            parts.append(f"<p><b>Uses:</b> {uses}</p>")

    # Product details card content
    if wc_product:
        card_items = []
        for i in range(1, 6):
            header = get_wc_meta(wc_product, f"product_card_header_{i}")
            content = get_wc_meta(wc_product, f"product_card_content_{i}")
            if header and content:
                card_items.append((header, content))

        if card_items:
            parts.append("<p><b>How to Plant:</b></p>")
            parts.append("<ul>")
            for header, content in card_items[:4]:
                parts.append(f"<li><b>{header}:</b> {content}</li>")
            parts.append("</ul>")

    # Weight/Coverage section
    spec_items = []
    if weight:
        spec_items.append(f"<li>Weight: {weight}</li>")
    if coverage:
        spec_items.append(f"<li>Coverage: {coverage} sq ft</li>")

    zones = get_usda_zones(sku)
    if zones:
        spec_items.append(f"<li>USDA Hardiness Zones: {zones[0]} - {zones[1]}</li>")

    if wc_product:
        sci_name = get_wc_meta(wc_product, "scientific_name")
        if sci_name:
            spec_items.append(f"<li>Scientific Name: {sci_name}</li>")

    if spec_items:
        parts.append("<p><b>Product Specifications:</b></p>")
        parts.append("<ul>")
        parts.extend(spec_items)
        parts.append("</ul>")

    # Closing
    parts.append("<p>Nature's Seed products are grown and processed in the USA. "
                "All seed is tested for purity and germination rates to meet or exceed industry standards.</p>")

    return sanitize_html("\n".join(parts))


def generate_key_features(wm_item, wc_product=None):
    """
    Generate 3-5 key feature bullets (100-500 chars each).
    """
    sku = wm_item.get("sku", "")
    name = clean_product_name(wm_item.get("productName", ""))
    weight = get_weight_from_sku(sku)
    coverage = get_coverage_from_name(wm_item.get("productName", ""))

    features = []

    if wc_product:
        # Pull from product_highlight (1-4) + card_content for richer features
        # Skip highlight_5 — it's usually the USDA zone code, not a feature
        for i in range(1, 5):
            highlight = get_wc_meta(wc_product, f"product_highlight_{i}")
            card_content = get_wc_meta(wc_product, f"product_card_content_{i}")
            if highlight and card_content:
                clean_card = strip_html_to_text(card_content)
                combined = f"{highlight}: {clean_card}"
                if len(combined) > 500:
                    combined = combined[:497] + "..."
                features.append(combined)
            elif highlight and len(highlight) > 20:
                features.append(highlight)

    # If we still need features, generate from available data
    if len(features) < 3:
        if wc_product:
            sun = get_wc_meta(wc_product, "sun_requirements")
            soil = get_wc_meta(wc_product, "soil_preference")
            if sun and soil:
                features.append(f"Thrives in {sun.lower()} with {soil.lower()} soil conditions for reliable establishment and growth")

            uses = get_wc_meta(wc_product, "detail_5_uses")
            if uses:
                features.append(f"Ideal for {uses.lower()}")

        if coverage:
            features.append(f"Covers up to {coverage} square feet per bag for efficient, uniform coverage")

        features.append("Tested for purity and germination to meet or exceed industry standards for reliable results")
        features.append("Grown and processed in the USA by Nature's Seed with decades of seed industry expertise")

    # Ensure each feature is 100-500 chars
    final = []
    for f in features[:5]:
        if len(f) < 100:
            f = f + ". Nature's Seed provides premium seed products tested for quality and backed by expert growing guides."
        if len(f) > 500:
            f = f[:497] + "..."
        final.append(f)

    # Ensure at least 3
    while len(final) < 3:
        final.append("Premium seed product from Nature's Seed, tested for quality and germination. "
                     "Backed by decades of seed industry expertise and detailed planting instructions.")

    return final[:5]


def generate_attributes(wm_item, wc_product=None):
    """
    Generate Walmart Plant Seeds attributes.
    """
    sku = wm_item.get("sku", "")
    name = clean_product_name(wm_item.get("productName", ""))

    attrs = {}

    # Light needs
    if wc_product:
        sun = get_wc_meta(wc_product, "sun_requirements")
        if sun:
            sun_lower = sun.lower()
            if "full sun" in sun_lower and "shade" in sun_lower:
                attrs["light_needs"] = "Full Sun to Partial Shade"
            elif "full sun" in sun_lower:
                attrs["light_needs"] = "Full Sun"
            elif "partial" in sun_lower or "part" in sun_lower:
                attrs["light_needs"] = "Partial Shade"
            elif "shade" in sun_lower:
                attrs["light_needs"] = "Full Shade"
            else:
                attrs["light_needs"] = sun
    if "light_needs" not in attrs:
        attrs["light_needs"] = "Full Sun to Partial Shade"

    # Plant category
    attrs["plantCategory"] = get_plant_category(sku)

    # USDA zone
    zones = get_usda_zones(sku)
    if zones:
        attrs["usdaHardinessZone"] = f"{zones[0]}-{zones[1]}"

    # Net content (weight)
    weight = get_weight_from_sku(sku)
    if weight:
        attrs["netContent"] = weight

    # Plant name (clean, no weight/coverage)
    attrs["plantName"] = clean_product_name(name)

    # Standard attributes
    attrs["recommendedLocations"] = "Outdoor"
    attrs["isProp65WarningRequired"] = "No"
    attrs["condition"] = "New"
    attrs["brand"] = "Nature's Seed"

    # Scientific name
    if wc_product:
        sci = get_wc_meta(wc_product, "scientific_name")
        if sci:
            attrs["scientificName"] = sci

    return attrs


# ============================================================
# CROSS-REFERENCE & BUILD
# ============================================================

def load_wc_products():
    """Load WooCommerce products and index by base SKU."""
    wc_path = Path(__file__).parent.parent / "spring-2026-recovery" / "data" / "products_active.json"
    if not wc_path.exists():
        print(f"  WARNING: WC products not found at {wc_path}")
        return {}

    with open(wc_path) as f:
        products = json.load(f)

    # Index by SKU (both exact and base)
    index = {}
    for p in products:
        sku = (p.get("sku") or "").upper()
        if sku:
            index[sku] = p
            base = get_base_sku(sku)
            if base not in index:
                index[base] = p

    print(f"  Loaded {len(products)} WC products ({len(index)} index entries)")
    return index


def find_wc_match(walmart_sku, wc_index):
    """Find matching WC product for a Walmart SKU."""
    upper = walmart_sku.upper()

    # Direct match
    if upper in wc_index:
        return wc_index[upper]

    # Base SKU match
    base = get_base_sku(upper)
    if base in wc_index:
        return wc_index[base]

    # Try progressively shorter prefixes
    parts = base.split("-")
    for i in range(len(parts), 1, -1):
        prefix = "-".join(parts[:i])
        if prefix in wc_index:
            return wc_index[prefix]

    return None


def generate_all(walmart_items, wc_index):
    """
    Generate optimized content for all Walmart items.

    Returns list of dicts with: sku, title, description, key_features, attributes, wc_matched
    """
    results = []
    matched = 0

    for item in walmart_items:
        sku = item.get("sku", "")
        wc = find_wc_match(sku, wc_index)
        if wc:
            matched += 1

        result = {
            "sku": sku,
            "current_name": item.get("productName", ""),
            "wc_matched": bool(wc),
            "wc_sku": wc.get("sku", "") if wc else "",
            "title": generate_title(item, wc),
            "description": generate_description(item, wc),
            "key_features": generate_key_features(item, wc),
            "attributes": generate_attributes(item, wc),
            "product_type": get_product_type(sku),
        }
        results.append(result)

    print(f"  Generated content for {len(results)} items ({matched} matched to WC data)")
    return results


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    # Load data
    print("Loading Walmart items...")
    with open(Path(__file__).parent / "data" / "walmart_items.json") as f:
        wm_items = json.load(f)

    # Deduplicate
    seen = set()
    unique = []
    for it in wm_items:
        if it["sku"] not in seen:
            seen.add(it["sku"])
            unique.append(it)
    wm_items = unique
    print(f"  {len(wm_items)} unique items")

    print("\nLoading WC products...")
    wc_index = load_wc_products()

    print("\nGenerating content...")
    results = generate_all(wm_items, wc_index)

    # Show 3 samples
    for i, r in enumerate(results[:3]):
        print(f"\n{'='*60}")
        print(f"Sample {i+1}: {r['sku']}")
        print(f"  Current name: {r['current_name']}")
        print(f"  WC matched:   {r['wc_matched']} ({r['wc_sku']})")
        print(f"  New title:    {r['title']} ({len(r['title'])} chars)")
        print(f"  Description:  {r['description'][:200]}...")
        print(f"  Key features: {len(r['key_features'])} bullets")
        for j, kf in enumerate(r['key_features']):
            print(f"    [{j+1}] {kf[:80]}...")
        print(f"  Attributes:   {r['attributes']}")

    # Stats
    wc_matched = sum(1 for r in results if r["wc_matched"])
    title_lens = [len(r["title"]) for r in results]
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  WC matched: {wc_matched}/{len(results)}")
    print(f"  Title lengths: min={min(title_lens)}, max={max(title_lens)}, avg={sum(title_lens)/len(title_lens):.0f}")
