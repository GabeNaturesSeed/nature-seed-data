#!/usr/bin/env python3
"""
Extract competitor brand terms and irrelevant/wasted search terms from Google Ads data.
Outputs negative keyword lists for Google Ads.

v3 - Comprehensive competitor list (original 18 + 20 additional found in data).
     Precise irrelevant detection using whitelist-first approach to avoid
     false positives on legitimate seed terms like milkweed, flax, carpetgrass, etc.
"""

import csv
import re
from collections import defaultdict

DATA_PATH = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/data/Search_Terms.csv"
OUT_COMPETITORS = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/implementation/negative_keywords_competitors.csv"
OUT_IRRELEVANT = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/implementation/negative_keywords_irrelevant.csv"
OUT_PASTE = "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/google-ads-audit/implementation/negative_keywords_paste_list.txt"

# ══════════════════════════════════════════════════════════════════════
#  COMPETITOR BRAND PATTERNS
# ══════════════════════════════════════════════════════════════════════
# Original 18 requested + additional brands discovered in data
COMPETITOR_PATTERNS = [
    # --- Original 18 requested ---
    (r"nature'?s?\s*finest", "nature's finest"),
    (r"created\s*by\s*nature", "created by nature"),
    (r"createdbynature", "created by nature"),
    (r"american\s*meadows?", "american meadows"),
    (r"ernst\s*seeds?", "ernst seeds"),
    (r"mother\s*nature\s*seeds?", "mother nature seeds"),
    (r"hancock\s*seed", "hancock seed"),
    (r"\bpennington\b", "pennington"),
    (r"\bscotts\b", "scotts"),
    (r"\bbarenbrug\b", "barenbrug"),
    (r"outsidepride", "outsidepride"),
    (r"outside\s*pride", "outsidepride"),
    (r"\bseedland\b", "seedland"),
    (r"prairie\s*moon", "prairie moon"),
    (r"prairie\s*nursery", "prairie nursery"),
    (r"high\s*country\s*gardens?", "high country gardens"),
    (r"plants?\s*of\s*the\s*southwest", "plants of the southwest"),
    (r"\bgranite\s*seed", "granite seed"),
    (r"great\s*basin\s*seed", "great basin seed"),
    (r"western\s*range\s*seed", "western range seed"),
    # --- Additional competitor brands found in data ---
    (r"\bnature\s*jims?\b", "nature jim"),
    (r"\bjohnny'?s?\s*seeds?\b", "johnny's seeds"),
    (r"\bjohnnysseeds\b", "johnny's seeds"),
    (r"\bbaker\s*creek\b", "baker creek"),
    (r"\bmyseeds\b", "myseeds"),
    (r"\bboston\s*seed", "boston seeds"),
    (r"nature'?s?\s*eats\b", "nature's eats"),
    (r"\bnative\s*american\s*seed", "native american seed"),
    (r"\bdeer\s*creek\s*seed", "deer creek seed"),
    (r"\bking\s*seed\s*company\b", "king seed company"),
    (r"\bearthwise\s*seed", "earthwise seed"),
    (r"\bgurneys?\b", "gurneys"),
    (r"\bseed\s*superstore\b", "seed superstore"),
    (r"\bseedsuperstore\b", "seed superstore"),
    (r"\bseed\s*ranch\b", "seed ranch"),
    (r"\bseedranch\b", "seed ranch"),
    (r"\bseed\s*world\b", "seed world"),
    (r"\bseedworld\b", "seed world"),
    (r"\bseed\s*needs\b", "seed needs"),
    (r"\bseedneeds\b", "seed needs"),
    (r"\btrue\s*leaf\s*(market|seed)", "true leaf market"),
    (r"\bseed\s*savers?\b", "seed savers"),
    (r"\bseedsavers?\b", "seed savers"),
    (r"\brare\s*seeds?\b(?!.*baker)", "rare seeds / baker creek"),
    (r"\brareseeds\b", "rare seeds / baker creek"),
    (r"\beden\s*brothers?\b", "eden brothers"),
    (r"\bsouthern\s*exposure\b", "southern exposure"),
    (r"\bseedway\b", "seedway"),
    (r"\bjacklin\s*seed\b", "jacklin seed"),
    (r"\bpure\s*seed\b", "pure seed"),
    (r"\bsimplot\b.*\bseed\b", "simplot"),
    (r"\bseed\b.*\bsimplot\b", "simplot"),
]

COMPETITOR_RE = [(re.compile(pat, re.IGNORECASE), label) for pat, label in COMPETITOR_PATTERNS]


# ══════════════════════════════════════════════════════════════════════
#  OWN BRAND DETECTION (Nature's Seed)
# ══════════════════════════════════════════════════════════════════════
OWN_BRAND_PATTERNS = [
    r"^nature'?s?\s*seed",
    r"^natures?\s*seed",
    r"^natureseed",
    r"^naturesseed",
    r"naturesseed\.com",
    r"naturesseed\b",
    r"natureseed\b",
    r"nature'?s?\s*seed\s*(company|store|reviews?|coupon|code|promo|discount|website|online|shop|micro\s*clover|phone|number|rating)",
    r"^nature\s*seed\b",
]
OWN_BRAND_RE = [re.compile(pat, re.IGNORECASE) for pat in OWN_BRAND_PATTERNS]


def is_own_brand(term):
    for regex in OWN_BRAND_RE:
        if regex.search(term):
            return True
    return False


def check_competitor(term):
    if is_own_brand(term):
        return None
    for regex, label in COMPETITOR_RE:
        if regex.search(term):
            return label
    return None


# ══════════════════════════════════════════════════════════════════════
#  WHITELIST: terms clearly on-topic for a seed company
# ══════════════════════════════════════════════════════════════════════
WHITELIST_PATTERNS = [
    r"\bseed\b", r"\bseeds\b", r"\bgrass\b", r"\blawn\b", r"\bturf\b",
    r"\bpasture\b", r"\bhay\b", r"\bforage\b", r"\bclover\b", r"\balfalfa\b",
    r"\bwildflower", r"\bwild\s*flower", r"\bmeadow\b",
    r"\bmilkweed\b", r"\bflax\b", r"\bfescue\b", r"\bbluegrass\b",
    r"\bbermuda\b", r"\bbahia\b", r"\bbuffalo\s*grass\b", r"\bzoysia\b",
    r"\bryegrass\b", r"\borchard\s*grass\b", r"\btimothy\b",
    r"\bcarpet\s*grass\b", r"\bcarpetgrass\b", r"\bcentipede\b",
    r"\bst\.?\s*augustine\b",
    r"\bfireweed\b", r"\bchickweed\b", r"\bragweed\b", r"\bsmartweed\b",
    r"\bswitchgrass\b", r"\bgamma\s*grass\b", r"\bindian\s*grass\b",
    r"\bbluestem\b", r"\bgrama\b", r"\bwheatgrass\b",
    r"\bcover\s*crop\b", r"\bfood\s*plot\b", r"\bdeer\s*plot\b",
    r"\bpoppy\b", r"\blupine\b", r"\bcolumbine\b", r"\bconeflower\b",
    r"\bsunflower\b", r"\bmarigold\b", r"\baster\b", r"\bdaisy\b",
    r"\bsow\b", r"\bplant\b", r"\bgrow\b", r"\bgarden\b", r"\byard\b",
    r"\bmow\b", r"\bmowing\b", r"\boverseeding\b", r"\boverseed\b",
    r"\bsoil\b", r"\bfertiliz", r"\bmulch\b", r"\baerat",
    r"\bdrought\b", r"\bshade\b",
    r"\bhorse\b", r"\bcattle\b", r"\blivestock\b", r"\bgoat\b", r"\bsheep\b",
    r"\bchicken\b", r"\bpoultry\b",
    r"\bnature'?s?\s*seed", r"\bnatureseed", r"\bnaturesseed",
    r"\berosion\b", r"\breclamation\b", r"\brestoration\b",
    r"\bnative\b", r"\bdryland\b", r"\birrigat",
    r"\bpollinator\b", r"\bbee\b", r"\bbutterfly\b", r"\bmonarch\b",
    r"\bsprinkler\b", r"\birrigation\b",
    r"\bsod\b", r"\bhydroseed\b",
    r"\bacreage\b", r"\bpastureland\b", r"\brangeland\b",
    r"\brice\s*hull", r"\binoculant\b",
    r"\bmicroclover\b", r"\bmicro\s*clover\b",
    r"\bcoating\b", r"\binoculat",
    r"\bprairie\b",
    r"\bbrome\b", r"\bfestulolium\b", r"\btriticale\b",
    r"\bsorghum\b", r"\bmillet\b", r"\boat\b", r"\boats\b",
    r"\bturnip\b", r"\bradish\b", r"\bbrassica\b",
    r"\bcrimson\b", r"\bmedic\b", r"\bvetch\b", r"\bpea\b",
    r"\bcouch\b",  # couch grass is a legitimate grass variety
    r"\bsprout",  # sprouting seeds for chickens are on-topic
    r"\bmicrogreen",  # microgreens for chickens
    r"\bbulb",  # flower bulbs are borderline but on-topic
]
WHITELIST_RE = [re.compile(pat, re.IGNORECASE) for pat in WHITELIST_PATTERNS]


def is_on_topic(term):
    for regex in WHITELIST_RE:
        if regex.search(term):
            return True
    return False


# ══════════════════════════════════════════════════════════════════════
#  IRRELEVANT: Precise off-topic patterns
# ══════════════════════════════════════════════════════════════════════
# These only match terms that are clearly NOT about buying seeds for planting.
# The whitelist check runs FIRST, so any seed-related term is safe.
IRRELEVANT_PATTERNS = [
    # Pet food
    (r"\bdog\s*food\b", "dog food"),
    (r"\bcat\s*food\b", "cat food"),
    (r"\bpet\s*food\b", "pet food"),
    (r"\bbird\s*food\b", "bird food"),
    (r"\bkibble\b", "kibble"),
    (r"\bpuppy\s*food\b", "puppy food"),
    (r"\bfish\s*food\b", "fish food"),
    (r"\bdog\s*treat", "dog treat"),
    (r"\bcat\s*treat", "cat treat"),
    # Bird feed
    (r"\bbird\s*feed\b", "bird feed"),
    (r"\bbird\s*feeder\b", "bird feeder"),
    # Health food seeds (eating not planting)
    (r"\bchia\s*seed", "chia seed (food)"),
    (r"\bsesame\s*seed", "sesame seed (food)"),
    # Cannabis / marijuana
    (r"\bmarijuana\b", "marijuana"),
    (r"\bcannabis\b", "cannabis"),
    (r"\bcbd\b", "CBD"),
    (r"\bautoflower\b", "marijuana autoflower"),
    (r"\bfeminized\s*seed", "marijuana feminized seed"),
    # Completely unrelated industries
    (r"\bmattress\b", "mattress"),
    (r"\bperfume\b", "perfume"),
    (r"\bcologne\b", "cologne"),
    (r"\bfragrance\b", "fragrance"),
    (r"\bshampoo\b", "shampoo"),
    (r"\bessential\s*oil\b", "essential oil"),
    (r"\baromatherapy\b", "aromatherapy"),
    (r"\bjewelry\b", "jewelry"),
    (r"\belectronics\b", "electronics"),
    (r"\blaptop\b", "laptop"),
    (r"\bcomputer\b", "computer"),
    (r"\btelevision\b", "television"),
    (r"\bgaming\b", "gaming"),
    (r"\bvideo\s*game\b", "video game"),
    (r"\binsurance\b", "insurance"),
    (r"\bmortgage\b", "mortgage"),
    (r"\bcredit\s*card\b", "credit card"),
    (r"\bnetflix\b", "netflix"),
    (r"\bstreaming\b", "streaming"),
    # Nature-themed but not seeds
    (r"\bnature\s*documentary\b", "nature documentary"),
    (r"\bnature\s*show\b", "nature show"),
    (r"\bnature\s*film\b", "nature film"),
    (r"\bnature\s*walk\b", "nature walk"),
    (r"\bnature\s*trail\b", "nature trail"),
    (r"\bnature\s*hike\b", "nature hike"),
    (r"\bnature\s*sounds?\b", "nature sounds"),
    (r"\bnature\s*music\b", "nature music"),
    (r"\bnature\s*wallpaper\b", "nature wallpaper"),
    (r"\bnature\s*photograph", "nature photography"),
    (r"\bnature\s*painting\b", "nature painting"),
    (r"\bnature\s*art\b", "nature art"),
    (r"\bnature\s*tattoo\b", "nature tattoo"),
    (r"\bnature\s*quote", "nature quotes"),
    (r"\bnature\s*valley\b", "nature valley (brand)"),
    (r"\bnature\s*made\b", "nature made (brand)"),
    (r"\bnaturebox\b", "naturebox (brand)"),
    (r"\bnature\s*box\b", "nature box (brand)"),
    (r"\bnatural\s*gas\b", "natural gas"),
    (r"\bnature\s*center\b", "nature center"),
    (r"\bnature\s*preserve\b", "nature preserve"),
    # Cooking/recipes
    (r"\brecipe\b", "recipe"),
    (r"\bcooking\b", "cooking"),
    # Furniture / home
    (r"\bfurniture\b", "furniture"),
    (r"\broofing\b", "roofing"),
    (r"\bsiding\b", "siding"),
    # Retail stores (people searching for products at other retailers)
    (r"\bhome\s*depot\b", "home depot"),
    (r"\blowes\b", "lowes"),
    (r"\bwalmart\b", "walmart"),
    (r"\bamazon\b", "amazon"),
    (r"\bcostco\b", "costco"),
    (r"\btractor\s*supply\b", "tractor supply"),
    # Feed store (looking for animal feed, not seed)
    (r"\bfeed\s*store\b", "feed store"),
    (r"\blivestock\s*feed\b", "livestock feed"),
    (r"\bchicken\s*feed\b(?!.*seed)", "chicken feed (not seed)"),
    (r"\borganic\s*chicken\s*(feed|food)\b", "organic chicken feed"),
]

IRRELEVANT_RE = [(re.compile(pat, re.IGNORECASE), reason) for pat, reason in IRRELEVANT_PATTERNS]


# ── High-priority irrelevant: these OVERRIDE the whitelist ─────────────
# Retail store searches: even with seed keywords, the intent is to buy elsewhere.
# Chicken feed without "seed": looking for animal feed, not planting seed.
# These are checked BEFORE the whitelist.
OVERRIDE_PATTERNS = [
    (r"\bhome\s*depot\b", "retail: home depot"),
    (r"\blowes\b", "retail: lowes"),
    (r"\bwalmart\b", "retail: walmart"),
    (r"\bamazon\b", "retail: amazon"),
    (r"\bcostco\b", "retail: costco"),
    (r"\btractor\s*supply\b", "retail: tractor supply"),
    (r"\borganic\s*chicken\s*(feed|food)\b", "chicken feed (not seed)"),
    (r"\bchicken\s*feed\b", "chicken feed (not seed)"),
    (r"\bchicken\s*food\b", "chicken food (not seed)"),
    (r"\bchickenfeed\b", "chicken feed (not seed)"),
    (r"\bfeed\s*store\b", "feed store"),
    (r"\blivestock\s*feed\b", "livestock feed"),
]
OVERRIDE_RE = [(re.compile(pat, re.IGNORECASE), reason) for pat, reason in OVERRIDE_PATTERNS]


def check_irrelevant(term, spend, conversions):
    """Return reason string if the term is clearly irrelevant, else None.

    Three-pass approach:
      1. Override patterns (retail stores, chicken feed) - checked FIRST, bypass whitelist
      2. Whitelist: if the term contains seed/grass/lawn keywords, skip it
      3. Other irrelevant patterns: checked last
    """
    # Pass 1: Override patterns bypass whitelist
    for regex, reason in OVERRIDE_RE:
        if regex.search(term):
            return f"off-topic: {reason}"

    # Pass 2: If on-topic (seed-related), never flag
    if is_on_topic(term):
        return None

    # Pass 3: Check against precise off-topic patterns
    for regex, reason in IRRELEVANT_RE:
        if regex.search(term):
            return f"off-topic: {reason}"

    return None


def main():
    # ── Aggregate by search term ───────────────────────────────────────
    agg = defaultdict(lambda: {"spend": 0.0, "conversions": 0.0, "conv_value": 0.0})

    with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            term = row["Search Term"].strip().lower()
            try:
                spend = float(row["Cost ($)"].replace(",", ""))
            except (ValueError, KeyError):
                spend = 0.0
            try:
                conv = float(row["Conversions"].replace(",", ""))
            except (ValueError, KeyError):
                conv = 0.0
            try:
                conv_val = float(row["Conv. Value ($)"].replace(",", ""))
            except (ValueError, KeyError):
                conv_val = 0.0

            agg[term]["spend"] += spend
            agg[term]["conversions"] += conv
            agg[term]["conv_value"] += conv_val

    print(f"Total unique search terms: {len(agg)}")

    # ── Classify ───────────────────────────────────────────────────────
    competitors = []
    irrelevant = []

    for term, data in sorted(agg.items(), key=lambda x: -x[1]["spend"]):
        spend = round(data["spend"], 2)
        conv = round(data["conversions"], 2)
        conv_val = round(data["conv_value"], 2)
        roas = round(conv_val / spend, 2) if spend > 0 else 0.0

        comp_label = check_competitor(term)
        if comp_label:
            competitors.append({
                "search_term": term,
                "total_spend": spend,
                "total_conversions": conv,
                "total_conv_value": conv_val,
                "roas": roas,
                "reason": f"Competitor: {comp_label}",
            })
            continue

        irr_reason = check_irrelevant(term, spend, conv)
        if irr_reason:
            irrelevant.append({
                "search_term": term,
                "total_spend": spend,
                "total_conversions": conv,
                "total_conv_value": conv_val,
                "roas": roas,
                "reason": irr_reason,
            })

    # Sort by spend descending
    competitors.sort(key=lambda x: -x["total_spend"])
    irrelevant.sort(key=lambda x: -x["total_spend"])

    print(f"\nCompetitor brand terms found: {len(competitors)}")
    print(f"Irrelevant/wasted terms found: {len(irrelevant)}")

    total_comp_spend = sum(r["total_spend"] for r in competitors)
    total_irr_spend = sum(r["total_spend"] for r in irrelevant)
    total_comp_conv = sum(r["total_conversions"] for r in competitors)
    total_irr_conv = sum(r["total_conversions"] for r in irrelevant)
    total_comp_value = sum(r["total_conv_value"] for r in competitors)
    total_irr_value = sum(r["total_conv_value"] for r in irrelevant)

    print(f"\nTotal competitor spend: ${total_comp_spend:,.2f}  ({total_comp_conv:.0f} conversions, ${total_comp_value:,.2f} value)")
    print(f"Total irrelevant spend: ${total_irr_spend:,.2f}  ({total_irr_conv:.0f} conversions, ${total_irr_value:,.2f} value)")
    print(f"Combined wasted spend: ${total_comp_spend + total_irr_spend:,.2f}")

    # ── Write competitor CSV ───────────────────────────────────────────
    fields = ["search_term", "total_spend", "total_conversions", "total_conv_value", "roas", "reason"]
    with open(OUT_COMPETITORS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(competitors)
    print(f"\nWrote {OUT_COMPETITORS}")

    # ── Write irrelevant CSV ───────────────────────────────────────────
    with open(OUT_IRRELEVANT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(irrelevant)
    print(f"Wrote {OUT_IRRELEVANT}")

    # ── Write paste list ───────────────────────────────────────────────
    all_keywords = set()
    for r in competitors:
        all_keywords.add(r["search_term"])
    for r in irrelevant:
        all_keywords.add(r["search_term"])

    with open(OUT_PASTE, "w", encoding="utf-8") as f:
        for kw in sorted(all_keywords):
            f.write(kw + "\n")
    print(f"Wrote {OUT_PASTE} ({len(all_keywords)} keywords)")

    # ── Print top offenders ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  TOP 30 COMPETITOR TERMS BY SPEND")
    print("=" * 70)
    for r in competitors[:30]:
        print(f"  ${r['total_spend']:>8.2f}  conv={r['total_conversions']:>6.1f}  ROAS={r['roas']:>6.2f}  {r['search_term']}")
        print(f"             {r['reason']}")

    print("\n" + "=" * 70)
    print("  ALL IRRELEVANT TERMS (sorted by spend)")
    print("=" * 70)
    for r in irrelevant:
        print(f"  ${r['total_spend']:>8.2f}  conv={r['total_conversions']:>6.1f}  ROAS={r['roas']:>6.2f}  {r['search_term']}")
        print(f"             {r['reason']}")

    # ── Competitor breakdown by brand ──────────────────────────────────
    print("\n" + "=" * 70)
    print("  COMPETITOR SPEND BREAKDOWN BY BRAND")
    print("=" * 70)
    brand_spend = defaultdict(lambda: {"spend": 0.0, "conv": 0.0, "value": 0.0, "count": 0})
    for r in competitors:
        brand = r["reason"].replace("Competitor: ", "")
        brand_spend[brand]["spend"] += r["total_spend"]
        brand_spend[brand]["conv"] += r["total_conversions"]
        brand_spend[brand]["value"] += r["total_conv_value"]
        brand_spend[brand]["count"] += 1

    for brand, d in sorted(brand_spend.items(), key=lambda x: -x[1]["spend"]):
        roas = round(d["value"] / d["spend"], 2) if d["spend"] > 0 else 0.0
        print(f"  {brand:<30s}  ${d['spend']:>8.2f}  {d['count']:>3d} terms  conv={d['conv']:>5.1f}  ROAS={roas:>5.2f}")


if __name__ == "__main__":
    main()
