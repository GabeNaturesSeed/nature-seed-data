#!/usr/bin/env python3
"""
Update WooCommerce product descriptions for bottom-20 Shopping products.
Adds missing short_description, description, and product_content_2 ACF field
where gaps were identified in the content audit.
"""

import requests
import time
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


def wc_put(product_id, payload):
    r = requests.put(f"{BASE}/products/{product_id}", auth=AUTH, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def meta(key, value):
    return {"key": key, "value": value}


# ── Product Content Definitions ───────────────────────────────────────────────
# Format: parent_id -> { fields to update }
# Only includes products/fields that are MISSING from audit.
# Descriptions are brand-aligned (expert-neighbor voice, outcome-led, trust signals).

UPDATES = {

    # ────────────────────────────────────────────────────────────────────────
    # White Dutch Clover Seed (445312) — missing desc + short_desc
    # ────────────────────────────────────────────────────────────────────────
    445312: {
        "short_description": (
            "<p>White Dutch Clover (Trifolium repens) is a hardy, low-growing perennial that doubles as a "
            "lawn alternative and pasture supplement. It fixes nitrogen, stays green through summer heat, and "
            "attracts pollinators — all with less water and mowing than traditional grass.</p>"
        ),
        "description": (
            "<p>White Dutch Clover is one of the most versatile plants you can grow. Whether you're replacing "
            "a high-maintenance lawn, overseeding a tired pasture, or building a pollinator-friendly ground cover, "
            "this low-growing perennial delivers exceptional results with minimal inputs.</p>"
            "<p>As a legume, White Dutch Clover naturally fixes atmospheric nitrogen into the soil — reducing your "
            "need for fertilizer by up to 50%. It stays lush and green even during dry summers, and its small white "
            "blooms attract honeybees and native pollinators throughout the season. Once established, it crowds out "
            "common weeds and resists foot traffic better than most cover options.</p>"
            "<p>Our White Dutch Clover seed is independently tested for purity and germination, sourced from "
            "trusted U.S. farms, and packaged filler-free. One 5 lb bag covers up to 10,000 sq ft. For best "
            "results, seed in early spring or fall when soil temps are 50–65°F.</p>"
        ),
    },

    # ────────────────────────────────────────────────────────────────────────
    # California Native Fire-Resistant Mix (445160) — missing desc + short_desc
    # ────────────────────────────────────────────────────────────────────────
    445160: {
        "short_description": (
            "<p>A California native wildflower and groundcover mix selected for fire resistance, drought tolerance, "
            "and year-round beauty. Ideal for WUI properties, hillsides, and fire-prone landscapes across the "
            "Western U.S.</p>"
        ),
        "description": (
            "<p>The California Native Fire-Wise Mix combines regionally-tested native species chosen specifically "
            "for their low fuel load, drought resilience, and ability to thrive in California's fire-prone "
            "landscapes. Every species in this blend is selected to reduce ignition risk while maintaining a "
            "living, beautiful groundcover.</p>"
            "<p>These low-growing natives stay succulent and moisture-retentive even in summer drought — the "
            "opposite of the dry, fine-fuel grasses that carry wildfire. The mix includes flowering groundcovers "
            "and natives that support local pollinators and wildlife, making your defensible space both safer and "
            "ecologically valuable.</p>"
            "<p>Expertly blended for California and Western U.S. conditions. Ideal for slopes, roadsides, "
            "wildland-urban interface (WUI) properties, and any homeowner looking to create a lower-risk, "
            "low-water landscape that still looks beautiful through the growing season.</p>"
        ),
    },

    # ────────────────────────────────────────────────────────────────────────
    # Clover Lawn Alternative Mix (458434) — missing desc + short_desc
    # ────────────────────────────────────────────────────────────────────────
    458434: {
        "short_description": (
            "<p>A low-mow clover and microclover lawn alternative that replaces traditional grass with a soft, "
            "walkable green carpet. Stays lush with less water, no fertilizer, and far less mowing — ideal for "
            "eco-conscious homeowners.</p>"
        ),
        "description": (
            "<p>The Lawn Alternative Clover Mix gives you a beautiful, low-maintenance ground cover that replaces "
            "or complements traditional turf. Blending White Dutch Clover, microclover, and complementary species, "
            "this mix forms a dense, soft-textured lawn that stays green through summer without the chemical "
            "inputs or frequent mowing that grass demands.</p>"
            "<p>Clover is a natural nitrogen-fixer — it feeds itself from the air, meaning you can skip synthetic "
            "fertilizers entirely. It handles foot traffic well, tolerates drought better than cool-season grasses, "
            "and produces gentle blooms that pollinators love. This makes it a perfect choice for families, dog "
            "owners, and anyone who wants a functional, low-cost lawn that's also good for the environment.</p>"
            "<p>Our blend is expertly proportioned for quick establishment and season-long coverage. Seed in spring "
            "or fall into a prepared seedbed. Works as a standalone lawn or blended into existing turf for a "
            "natural, sustainable upgrade.</p>"
        ),
    },

    # ────────────────────────────────────────────────────────────────────────
    # Green Screen Food Plot Mix (455414) — missing desc + short_desc
    # ────────────────────────────────────────────────────────────────────────
    455414: {
        "short_description": (
            "<p>A high-attraction food plot seed blend designed to hold deer and wildlife on your property "
            "through fall and winter. Fast-establishing annuals and perennials provide reliable forage from "
            "early season through hard frosts.</p>"
        ),
        "description": (
            "<p>Green Screen Food Plot Mix is engineered to attract and hold deer, turkey, and other wildlife "
            "from early fall through late season. The blend combines fast-germinating annuals with persistent "
            "perennials to give you green, palatable forage exactly when hunting pressure peaks and natural "
            "food sources decline.</p>"
            "<p>The mix includes species proven to draw heavy browse pressure: brassicas for cool-season attraction, "
            "clovers for warm-season protein, and grains that remain standing through early frosts. Together they "
            "create a food plot that produces from the first cool nights of fall through the end of deer season — "
            "giving wildlife a reason to stay on your land.</p>"
            "<p>Seed into a well-prepared seedbed in late summer for fall establishment. The 10 lb kit covers "
            "approximately one acre in average soil conditions. Developed by Nature's Seed wildlife specialists "
            "with regional foraging behavior in mind.</p>"
        ),
    },

    # ────────────────────────────────────────────────────────────────────────
    # Sundancer Buffalograss (456233) — missing desc + short_desc
    # ────────────────────────────────────────────────────────────────────────
    456233: {
        "short_description": (
            "<p>Sundancer Buffalograss is a native, warm-season lawn grass that stays green and beautiful "
            "with up to 75% less water than conventional turf. Perfect for drought-prone regions, it requires "
            "minimal mowing and no synthetic inputs once established.</p>"
        ),
        "description": (
            "<p>Sundancer Buffalograss (Bouteloua dactyloides) is one of the most water-efficient lawn grasses "
            "available — a native North American species naturally adapted to heat, drought, and hard clay soils. "
            "Sundancer is a selected cultivar bred specifically for improved density, color, and wear tolerance "
            "compared to wild-type buffalograss, making it a genuine premium lawn option for water-conscious "
            "homeowners across the Great Plains and Southwest.</p>"
            "<p>Once established, Sundancer needs irrigation only during extended drought — dramatically reducing "
            "your water bill and maintenance time. It grows to a tidy 4–6 inch height without mowing, turns a "
            "rich blue-green through summer, and goes naturally dormant (tan) in winter before greening back "
            "up in spring. No fertilizers, no pesticides, and no constant watering required.</p>"
            "<p>This is a warm-season grass best suited to USDA Zones 3–9 in the central and western U.S. "
            "Seed in late spring when soil temps exceed 60°F. Our 3 lb kit covers up to 600 sq ft of new lawn "
            "or larger areas as a mix with other native species.</p>"
        ),
    },

    # ────────────────────────────────────────────────────────────────────────
    # Dryland Pasture Mix (458472) — missing desc + missing product_content_2
    # Already has short_description — derive description from it
    # ────────────────────────────────────────────────────────────────────────
    458472: {
        "description": (
            "<p>Dryland Pasture Mix is engineered for semi-arid landscapes where water is scarce but pasture "
            "productivity still matters. This drought-tolerant seed blend establishes a resilient grazing stand "
            "for horses, cattle, sheep, and other livestock across the intermountain West, High Plains, and "
            "other regions with less than 15 inches of annual precipitation.</p>"
            "<p>The blend prioritizes proven dryland species: native and introduced grasses with deep root systems "
            "that tap subsoil moisture, legumes for nitrogen and palatability, and forbs that add mineral diversity "
            "to the forage base. Every species is selected for establishment success without irrigation, long-term "
            "persistence under grazing pressure, and nutritional value for a range of livestock.</p>"
            "<p>Seed in early spring or late fall (dormant seeding) into a firm, weed-suppressed seedbed. "
            "Our 50 lb bag covers up to 50 acres at a light overseeding rate, or is suitable for 5–10 acres of "
            "new establishment. Developed in partnership with our in-house pasture specialists for the specific "
            "conditions of dryland ranching across the Western U.S.</p>"
        ),
        "meta_data_extra": {
            "product_content_2": (
                "Dryland Pasture Mix is a carefully proportioned blend of drought-tolerant grasses, legumes, and "
                "forbs developed for semi-arid regions receiving under 15 inches of annual rainfall. It establishes "
                "without irrigation, persists under grazing pressure, and delivers nutritionally diverse forage "
                "across the full growing season. Trusted by ranchers across the intermountain West, Great Basin, "
                "and High Plains for its reliable establishment and long-term pasture productivity."
            ),
        },
    },

    # ────────────────────────────────────────────────────────────────────────
    # Texas Bluebonnet (462219) — missing desc (has short)
    # ────────────────────────────────────────────────────────────────────────
    462219: {
        "description": (
            "<p>Texas Bluebonnet (Lupinus texensis) is the official state flower of Texas and one of the most "
            "iconic wildflowers in North America. Each spring, Bluebonnets transform roadsides, meadows, and "
            "home gardens into seas of brilliant blue-purple color — a defining image of the Texas Hill Country "
            "and one that every Texan recognizes from childhood.</p>"
            "<p>Beyond their beauty, Bluebonnets are a native legume that enriches the soil with nitrogen and "
            "provides early-season nectar for native bees and other pollinators. They reseed naturally when "
            "allowed to set seed, building a self-sustaining colony over time. Once established in the right "
            "conditions, a Bluebonnet planting comes back reliably each year with minimal care.</p>"
            "<p>For best results in Texas and surrounding states, sow in fall (September–November) into a "
            "prepared, well-draining seedbed. Scarify seed before planting or purchase pre-scarified. Our "
            "1 lb bag covers up to 200–300 sq ft in garden applications. Seed you can trust — from a team "
            "that knows Texas wildflowers.</p>"
        ),
    },

    # ────────────────────────────────────────────────────────────────────────
    # Chicken Forage Mix (445163) — missing desc + short_desc
    # ────────────────────────────────────────────────────────────────────────
    445163: {
        "short_description": (
            "<p>An Omega-3-rich poultry forage blend that gives chickens, ducks, and other backyard birds "
            "access to living forages, insects, and nutrients year-round. Reduces feed costs while improving "
            "flock health, egg quality, and yolk color.</p>"
        ),
        "description": (
            "<p>Chicken Forage Mix is a specially formulated blend designed to bring the benefits of rotational "
            "pasture grazing to backyard poultry keepers. By growing living forages in your run or designated "
            "forage paddocks, you give your flock access to natural greens, insects, and soil microbes that "
            "dramatically improve their nutrition and wellbeing.</p>"
            "<p>The mix is rich in species that boost Omega-3 fatty acid content in eggs — the same nutrients "
            "that make pastured eggs visibly different from store-bought: deeper orange yolks, richer flavor, "
            "and better nutritional profiles. Clover, chicory, plantain, and other forbs in the blend offer "
            "diverse nutrition while the grasses provide habitat for beneficial insects and scratch material.</p>"
            "<p>Seed in spring or fall into a designated forage area. For best results, use a rotational system: "
            "allow growth to 6–8 inches before introducing birds, then rotate to a fresh paddock. Manageable "
            "on as little as 500 sq ft for a small flock. One bag covers up to 2,000 sq ft.</p>"
        ),
    },

    # ────────────────────────────────────────────────────────────────────────
    # California Poppy (445350) — missing desc + short_desc
    # ────────────────────────────────────────────────────────────────────────
    445350: {
        "short_description": (
            "<p>California Poppy (Eschscholzia californica) is the iconic golden wildflower of the Western U.S., "
            "beloved for its brilliant orange blooms, extreme drought tolerance, and ease of establishment. "
            "Perfect for meadows, roadsides, and low-water garden beds.</p>"
        ),
        "description": (
            "<p>California Poppy is one of the easiest and most rewarding wildflowers you can grow. Native to "
            "California and the Southwest, this annual and short-lived perennial thrives in poor, dry soils where "
            "other plants struggle — blooming reliably from spring through fall with minimal care. Its brilliant "
            "gold and orange flowers close at night and open with the morning sun, creating a dynamic, living "
            "display that pollinators and people both love.</p>"
            "<p>Once established, California Poppy reseeds prolifically, building a self-sustaining colony that "
            "returns year after year. It requires no irrigation once established, needs no fertilizer, and handles "
            "the heat of California summers without the stress that wilts most flowers. This makes it an ideal "
            "choice for xeriscaping, meadow restoration, and wildfire recovery seeding across the Western U.S.</p>"
            "<p>Sow seed directly in fall or early spring into a prepared, weed-free seedbed. Scatter seed and "
            "lightly press into soil — do not cover, as California Poppy needs light to germinate. Our pure seed "
            "is independently tested for germination and free of filler species or grasses.</p>"
        ),
    },

    # ────────────────────────────────────────────────────────────────────────
    # Goat Pasture & Forage Mix (445267) — missing short_desc only
    # ────────────────────────────────────────────────────────────────────────
    445267: {
        "short_description": (
            "<p>A premium pasture and forage blend expertly formulated for goats, sheep, and other small "
            "ruminants. Combines high-palatability grasses and legumes for optimal browse nutrition, reducing "
            "supplement costs and improving herd health.</p>"
        ),
    },

    # ────────────────────────────────────────────────────────────────────────
    # Narrowleaf Milkweed (445347) — missing desc + short_desc
    # ────────────────────────────────────────────────────────────────────────
    445347: {
        "short_description": (
            "<p>Narrowleaf Milkweed (Asclepias fascicularis) is the essential Western U.S. host plant for "
            "Monarch butterflies. Plant it to support Monarch migration, provide nectar for native bees, "
            "and restore native pollinator habitat in your garden or landscape.</p>"
        ),
        "description": (
            "<p>Narrowleaf Milkweed is the native milkweed of choice for most of the Western United States. "
            "Unlike Tropical Milkweed (Asclepias curassavica), which can disrupt Monarch migration patterns, "
            "Narrowleaf Milkweed is a true native perennial that goes dormant in winter — naturally cuing "
            "Monarchs to continue their migration south. Planting native milkweed is one of the most impactful "
            "things you can do for Monarch butterfly conservation.</p>"
            "<p>Beyond Monarchs, Narrowleaf Milkweed's small pink and white flower clusters are rich in nectar "
            "and attract a wide range of native bees, beetles, and other beneficial insects. It spreads slowly "
            "by underground rhizomes to form a naturalized colony over time, providing reliable, low-maintenance "
            "pollinator habitat that improves each year.</p>"
            "<p>Native to California, Oregon, Washington, Nevada, and neighboring western states. Thrives in "
            "well-drained soils, full sun, and is highly drought tolerant once established. Direct sow in fall "
            "for natural cold stratification, or cold-stratify seed for 30 days before spring planting. "
            "Our pure seed is sourced from Western U.S. ecotypes for the best regional adaptation.</p>"
        ),
    },

    # ────────────────────────────────────────────────────────────────────────
    # Triblade Elite Tall Fescue (445117) — missing desc (has short)
    # ────────────────────────────────────────────────────────────────────────
    445117: {
        "description": (
            "<p>Triblade Elite is a premium tri-blend tall fescue lawn mix combining three of the latest "
            "elite turf-type tall fescue cultivars for exceptional performance across a wide range of "
            "conditions. The three-variety blend provides genetic diversity that improves disease resistance, "
            "stress tolerance, and long-term appearance compared to single-variety plantings.</p>"
            "<p>Turf-type tall fescue has become the preferred lawn grass for transitional and cool-season "
            "regions because it combines the heat tolerance of warm-season grasses with the cool-season "
            "green period of bluegrass and ryegrass. Triblade Elite stays green longer into summer, "
            "establishes quickly from seed, and develops a deep root system that reduces irrigation needs "
            "by 30–50% compared to Kentucky bluegrass.</p>"
            "<p>Ideal for lawns, sports fields, parks, and commercial turf across the Pacific Northwest, "
            "transitional zone, and mid-Atlantic states. Seed in late summer or early fall when soil temps "
            "are 55–65°F for best establishment. Our Triblade Elite seed is independently tested and "
            "certified for high germination, backed by Nature's Seed's satisfaction guarantee.</p>"
        ),
    },

    # ────────────────────────────────────────────────────────────────────────
    # Sun and Shade Grass Mix (447115) — missing desc + missing product_content_2
    # Already has short_description referencing KY bluegrass + fescue
    # ────────────────────────────────────────────────────────────────────────
    447115: {
        "description": (
            "<p>Sun and Shade Grass Seed Mix is a balanced blend of Kentucky Bluegrass, creeping red fescue, "
            "and perennial ryegrass designed to perform across the full range of light conditions — from "
            "full-sun open lawns to partially shaded areas under trees and along building foundations. "
            "Most lawns have both, and this blend adapts to them all.</p>"
            "<p>Kentucky Bluegrass provides the fine-textured, dense turf that self-repairs through underground "
            "rhizomes. Fine fescues thrive in shade and low-fertility soils where bluegrass struggles. "
            "Perennial ryegrass germinates in as few as 5–7 days, providing quick cover while the slower "
            "species establish. Together, they create a resilient, self-balancing lawn that fills in "
            "naturally based on where each species performs best in your yard.</p>"
            "<p>This blend is expertly proportioned for the Northeast, Mid-Atlantic, and Upper Midwest — "
            "regions with humid summers and cold winters where a diverse mix outperforms single-species "
            "plantings. Seed in early fall for optimal establishment. Our mix is filler-free, independently "
            "tested, and backed by Nature's Seed's germination guarantee.</p>"
        ),
        "meta_data_extra": {
            "product_content_2": (
                "Sun and Shade Grass Mix takes the guesswork out of seeding a yard with multiple light zones. "
                "By combining Kentucky Bluegrass, fine fescue, and perennial ryegrass in expert-tested ratios, "
                "this blend naturally self-selects — each species thriving in the areas it's best suited for "
                "while forming a continuous, uniform-looking lawn across your full yard. No more choosing "
                "between a sun mix and a shade mix. Seed once, grow everywhere."
            ),
        },
    },

    # ────────────────────────────────────────────────────────────────────────
    # Coastal CA Wildflower Mix (445349) — missing desc + short_desc
    # ────────────────────────────────────────────────────────────────────────
    445349: {
        "short_description": (
            "<p>A stunning blend of California coastal native wildflowers selected for drought tolerance, "
            "salt spray resistance, and year-round bloom interest. Brings vibrant color to coastal gardens, "
            "roadsides, and restoration sites while supporting native bees and pollinators.</p>"
        ),
        "description": (
            "<p>The Coastal California Wildflower Mix brings together native wildflower species specifically "
            "adapted to California's coastal climate: cool summers, mild winters, salt-laden air, and the "
            "lean, sandy or clay soils common to coastal bluffs and hillsides. Every species in this blend "
            "is tested for performance in coastal conditions — not just California overall, but the specific "
            "challenge of the coastal zone.</p>"
            "<p>The mix includes a rich diversity of annual and perennial natives that bloom in succession "
            "from early spring through summer, providing a continuous color display and a reliable nectar "
            "source for native bees, butterflies, and hummingbirds. Species are selected to reseed naturally "
            "and build in density over time, reducing maintenance needs each season.</p>"
            "<p>Ideal for coastal home gardens, restoration projects, and Cal Fire defensible space zones. "
            "Seed in fall (October–December) to take advantage of winter rains for natural germination. "
            "Our blend is collected from California ecotypes where possible, expertly tested for coastal "
            "adaptability, and packaged filler-free for pure, predictable results.</p>"
        ),
    },

}

# ── Shady Areas FAQ (444217) — separate update ────────────────────────────────
SHADY_AREAS_FAQ = {
    444217: {
        "meta_data_extra": {
            "question_content_1": "What types of grass grow best in shade?",
            "answer_content_1": (
                "Fine fescues — including creeping red fescue, hard fescue, and chewings fescue — are the "
                "gold standard for shaded lawns. They tolerate as little as 2–3 hours of dappled sunlight per "
                "day and stay green where Kentucky bluegrass and ryegrass fail. Our Shady Areas mix prioritizes "
                "fine fescues for exactly this reason."
            ),
            "question_content_2": "How much sunlight does a shady lawn need?",
            "answer_content_2": (
                "Most shade-tolerant grasses need a minimum of 2–4 hours of light per day — even indirect or "
                "dappled light counts. In areas with zero light year-round (dense evergreen canopy, north-facing "
                "walls with no reflection), grass will not establish well and groundcovers like moss or mulch "
                "may be a better option."
            ),
            "question_content_3": "When should I seed a shady lawn?",
            "answer_content_3": (
                "Early fall (August–October) is the ideal seeding window for shady cool-season mixes. "
                "Soil temperatures are still warm enough for fast germination (55–65°F), but the cooler air "
                "and reduced light competition from deciduous trees makes establishment easier. Early spring "
                "is the second-best option if fall seeding isn't possible."
            ),
            "question_content_4": "How do I overseed an existing shaded lawn?",
            "answer_content_4": (
                "Rake or dethatch the existing lawn to expose bare soil, then spread seed at half the new-seeding "
                "rate. Keep the seedbed consistently moist for 3–4 weeks. In heavy shade, reduce tree canopy "
                "if possible — even removing a few lower limbs can dramatically improve the light reaching "
                "the turf below."
            ),
            "question_content_5": "How often should I water a shade lawn seed mix?",
            "answer_content_5": (
                "Keep the top inch of soil consistently moist until germination is complete (typically 14–21 days "
                "for fine fescues). Light, frequent watering (2–3x daily) is better than deep, infrequent "
                "irrigation during the seedling phase. Once established, shady lawns typically need less water "
                "than sunny areas because shade reduces evapotranspiration."
            ),
            "question_content_6": "Why does grass thin out under trees every year?",
            "answer_content_6": (
                "Tree roots compete aggressively for water and nutrients, and canopy shade reduces "
                "photosynthesis. Additionally, many trees release allelopathic compounds (natural herbicides) "
                "that inhibit grass growth. Annual overseeding with a fine fescue shade mix, combined with "
                "light top-dressing and reduced fertilizer competition from trees, is the most reliable "
                "long-term strategy."
            ),
        }
    }
}


# ── Execute Updates ───────────────────────────────────────────────────────────
def run_updates():
    results = []

    all_updates = {**UPDATES, **SHADY_AREAS_FAQ}

    for product_id, fields in all_updates.items():
        print(f"\n[{product_id}] Updating...")

        payload = {}

        if "short_description" in fields:
            payload["short_description"] = fields["short_description"]

        if "description" in fields:
            payload["description"] = fields["description"]

        # Standard meta_data fields
        meta_list = []
        if "meta_data_extra" in fields:
            for key, value in fields["meta_data_extra"].items():
                meta_list.append({"key": key, "value": value})
        if meta_list:
            payload["meta_data"] = meta_list

        if not payload:
            print(f"  SKIP (nothing to update)")
            continue

        try:
            time.sleep(0.4)
            result = wc_put(product_id, payload)
            name = html_lib.unescape(result.get("name", ""))
            print(f"  OK: {name[:55]}")
            updated_fields = [k for k in ("short_description", "description") if k in payload]
            if meta_list:
                updated_fields += [m["key"] for m in meta_list]
            print(f"     Updated: {', '.join(updated_fields)}")
            results.append({"id": product_id, "name": name, "status": "ok", "fields": updated_fields})
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"id": product_id, "status": "error", "error": str(e)})

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    ok = [r for r in results if r["status"] == "ok"]
    err = [r for r in results if r["status"] == "error"]
    print(f"  Updated: {len(ok)}/{len(results)} products")
    for r in ok:
        print(f"  ✓ [{r['id']}] {r['name'][:45]}: {r['fields']}")
    if err:
        print(f"\n  Errors ({len(err)}):")
        for r in err:
            print(f"  ✗ [{r['id']}]: {r['error']}")


if __name__ == "__main__":
    run_updates()
