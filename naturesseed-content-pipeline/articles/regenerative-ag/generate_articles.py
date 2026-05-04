"""
Generate .docx files for Nature's Seed regenerative ag article series.
Run: python3 generate_articles.py
"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def set_font(run, name, size, bold=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def add_heading(doc, text, level):
    """Add a styled heading using Noto Serif Display style fallback."""
    para = doc.add_paragraph()
    run = para.add_run(text)
    sizes = {1: 22, 2: 16, 3: 14}
    set_font(run, "Noto Serif Display", sizes.get(level, 14), bold=True, color=(29, 67, 50))
    para.paragraph_format.space_before = Pt(14)
    para.paragraph_format.space_after = Pt(6)
    return para


def add_body(doc, text):
    para = doc.add_paragraph()
    run = para.add_run(text)
    set_font(run, "Inter", 11, color=(33, 37, 41))
    para.paragraph_format.space_after = Pt(8)
    return para


def add_meta_block(doc, category, read_time, meta_desc):
    """Add category / read time / meta description block."""
    para = doc.add_paragraph()
    run = para.add_run(f"Category: {category}  |  {read_time}  |  For internal use")
    set_font(run, "Inter", 9, color=(73, 80, 87))
    para.paragraph_format.space_after = Pt(4)

    para2 = doc.add_paragraph()
    run2 = para2.add_run(f"META: {meta_desc}")
    set_font(run2, "Inter", 9, bold=True, color=(44, 106, 79))
    para2.paragraph_format.space_after = Pt(12)

    doc.add_paragraph()  # spacer


def add_divider(doc):
    para = doc.add_paragraph()
    run = para.add_run("─" * 60)
    set_font(run, "Inter", 9, color=(200, 200, 200))
    para.paragraph_format.space_after = Pt(4)


def _set_cell_shading(cell, hex_color):
    """Set background fill color on a table cell."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def add_table(doc, headers, rows):
    """Add a styled table. headers = list of str, rows = list of list of str."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"

    # Header row
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        para = hdr_cells[i].paragraphs[0]
        para.clear()
        run = para.add_run(h)
        run.font.name = "Inter"
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)
        _set_cell_shading(hdr_cells[i], "2D6A4F")

    # Data rows
    for r_idx, row_data in enumerate(rows):
        row_cells = table.rows[r_idx + 1].cells
        fill = "F8F9FA" if r_idx % 2 == 0 else "FFFFFF"
        for c_idx, cell_text in enumerate(row_data[:len(headers)]):
            para = row_cells[c_idx].paragraphs[0]
            para.clear()
            run = para.add_run(cell_text)
            run.font.name = "Inter"
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(33, 37, 41)
            _set_cell_shading(row_cells[c_idx], fill)

    doc.add_paragraph()  # spacing after table


def add_references_section(doc, refs):
    """Add an APA references section. refs = list of str (formatted citations)."""
    if not refs:
        return
    add_divider(doc)
    add_heading(doc, "References", 2)
    for i, ref in enumerate(refs, 1):
        para = doc.add_paragraph()
        num_run = para.add_run(f"[{i}] ")
        set_font(num_run, "Inter", 9, bold=True, color=(44, 106, 79))
        ref_run = para.add_run(ref)
        set_font(ref_run, "Inter", 9, color=(73, 80, 87))
        para.paragraph_format.space_after = Pt(4)
        para.paragraph_format.left_indent = Inches(0.25)


def build_doc(article):
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.25)

    # Title
    title_para = doc.add_paragraph()
    title_run = title_para.add_run(article["title"])
    set_font(title_run, "Noto Serif Display", 26, bold=True, color=(27, 67, 50))
    title_para.paragraph_format.space_after = Pt(8)

    add_meta_block(doc, article["category"], article["read_time"], article["meta"])
    add_divider(doc)
    doc.add_paragraph()

    # Body parsing
    for block in article["body"]:
        kind = block["type"]
        text = block.get("text", "")

        if kind == "h2":
            add_heading(doc, text, 2)
        elif kind == "h3":
            add_heading(doc, text, 3)
        elif kind == "p":
            add_body(doc, text)
        elif kind == "bullet":
            para = doc.add_paragraph(style="List Bullet")
            run = para.add_run(text)
            set_font(run, "Inter", 11, color=(33, 37, 41))
            para.paragraph_format.space_after = Pt(4)
        elif kind == "cta":
            para = doc.add_paragraph()
            run = para.add_run(text)
            set_font(run, "Inter", 11, bold=True, color=(201, 106, 46))
            para.paragraph_format.space_before = Pt(14)
            para.paragraph_format.space_after = Pt(8)
        elif kind == "table":
            add_table(doc, block["headers"], block["rows"])
        elif kind == "note":
            para = doc.add_paragraph()
            run = para.add_run(text)
            set_font(run, "Inter", 10, color=(73, 80, 87))
            para.paragraph_format.space_after = Pt(6)
            para.paragraph_format.left_indent = Inches(0.25)

    if article.get("references"):
        add_references_section(doc, article["references"])

    return doc


# ---------------------------------------------------------------------------
# ARTICLE DATA
# ---------------------------------------------------------------------------

ARTICLES = [

# ── ARTICLE 1 ──────────────────────────────────────────────────────────────
{
  "title": "What Is Regenerative Agriculture? A Plain-English Guide",
  "category": "Foundations",
  "read_time": "6 min read",
  "meta": "Regenerative agriculture for small farms explained simply — what it actually means, what it costs, and how to start with one practice on your land.",
  "slug": "01-what-is-regenerative-agriculture",
  "body": [
    {"type":"p","text":"Your hay bill climbed again this year. You've got bare patches spreading in the back pasture, and your fertilizer rep keeps telling you to apply more. Then someone at the farm show mentioned \"regenerative agriculture\" and you walked away skeptical — it sounded like a sales pitch dressed up in ecology."},
    {"type":"p","text":"That skepticism is reasonable. But here's what's actually true: regenerative agriculture isn't a certification or a philosophy. It's a set of practices aimed at leaving your land in better shape than you found it — better soil, more water retention, lower input costs over time."},
    {"type":"p","text":"Your hay bill and those bare patches? Both are symptoms of declining soil health. That's exactly what regenerative practices address. Let's cut through the noise and talk about what it actually means on your farm."},
    {"type":"h2","text":"It's Not Organic — Here's the Difference"},
    {"type":"p","text":"A lot of people assume regenerative and organic are the same thing. They're not. Organic farming is defined by what you don't use — no synthetic pesticides, no synthetic fertilizers. It's a certification with specific rules."},
    {"type":"p","text":"You can farm organically and still plow your fields every year, leave soil bare between seasons, and run a monoculture. Technically organic. Not regenerative."},
    {"type":"p","text":"Regenerative agriculture is defined by what you're building. The focus is on soil health, biological activity, and long-term resilience. You can use regenerative practices without ever pursuing organic certification — and many farmers do."},
    {"type":"h2","text":"Three Goals, Not a Philosophy"},
    {"type":"p","text":"Strip away the marketing and you're left with three practical goals. Here's what each one means and what it looks like on your farm."},
    {"type":"table","headers":["Goal","What It Means","On Your Farm"],"rows":[["Build soil organic matter","Adds dark, spongy material that holds water and feeds biology","Cover crops, less tillage, managed grazing"],["Close nutrient cycles","Keep fertility on the farm — don't export it with every crop","Legumes fix N; livestock manure stays on-farm; residue decomposes in place"],["Reduce inputs over time","Healthy biology means less fertilizer and herbicide needed","Takes 3–5 years of consistent practice; costs drop each year"]]},
    {"type":"p","text":"That first goal — building organic matter — has a number attached to it. Every 1% increase in soil organic matter helps your soil hold an additional 20,000 gallons of water per acre [1]. In a dry summer, that's the difference between a struggling crop and a productive one."},
    {"type":"h2","text":"What It Looks Like on a Small Operation"},
    {"type":"p","text":"On a 50-acre farm or ranch, regenerative agriculture isn't some grand redesign. It's a handful of specific practices layered in over time."},
    {"type":"p","text":"Cover crops keep living roots in the ground between your cash crops or after hay harvest. Legumes like clover and hairy vetch fix atmospheric nitrogen. Grasses add organic matter. Brassicas break up compaction. A simple two- or three-species mix after your main crop starts improving your soil biology immediately."},
    {"type":"p","text":"Rotational grazing moves livestock frequently rather than leaving them on the same pasture all season. Grass that recovers builds deeper roots. Deeper roots deposit more carbon in the soil. It's one of the fastest ways to address bare patches and build organic matter."},
    {"type":"p","text":"Reducing tillage passes lets fungal networks and microbial communities rebuild between crops. You don't have to go no-till from day one — just ask whether every pass is earning its keep."},
    {"type":"h2","text":"You Don't Have to Do This All at Once"},
    {"type":"p","text":"Here's what nobody says upfront: you start with one practice on one field. Cover crop seed for a 20-acre field costs a few hundred dollars. Splitting one pasture with a single strand of temporary electric fence to start a basic rotation is cheap. Neither requires a loan."},
    {"type":"p","text":"Most farmers who've gone down this road say the same thing: they started with one thing, saw a result, and added the next practice when they were ready. Patience is the main input."},
    {"type":"h2","text":"Where to Start Without Hiring Anyone"},
    {"type":"p","text":"You don't need a consultant. Here's a simple sequence you can run yourself:"},
    {"type":"bullet","text":"Get a soil test first. A standard test from your county extension office costs $15–30. It tells you your pH, organic matter, and major nutrients. This is your baseline."},
    {"type":"bullet","text":"Pick one practice. If you grow row crops, plant a cover crop after harvest. If you run cattle, try a simple two-paddock rotation."},
    {"type":"bullet","text":"Track it. Take photos. Note which fields you changed. Run another soil test in two to three years and compare."},
    {"type":"bullet","text":"Use what's available. NRCS offers cost-share for cover cropping and rotational grazing fencing. Your local office can tell you what's available. It's free money most small landowners leave on the table."},
    {"type":"cta","text":"→ Shop cover crop seed at naturesseed.com/products/cover-crop-seed/"},
  ],
  "references": ["USDA Natural Resources Conservation Service. (2014). Soil health: Unlock the secrets in the soil. https://www.nrcs.usda.gov/wps/portal/nrcs/main/soils/health/"]
},

# ── ARTICLE 2 ──────────────────────────────────────────────────────────────
{
  "title": "The 5 Principles of Soil Health: Gabe Brown's Framework for Skeptical Ranchers",
  "category": "Foundations",
  "read_time": "7 min read",
  "meta": "Gabe Brown's 5 soil health principles for ranchers — practical, no-fluff breakdown of how a nearly-broke North Dakota rancher rebuilt his land without inputs.",
  "slug": "02-5-principles-soil-health",
  "body": [
    {"type":"p","text":"Gabe Brown nearly lost his farm. Four consecutive crop failures in the late 1990s — hail, drought, ice storms — stripped his inputs budget down to nothing. He couldn't afford fertilizer. He couldn't afford to keep doing things the way he'd been doing them."},
    {"type":"p","text":"What he built to survive became the most-cited soil health framework in agriculture. Five principles. No theory — just what worked when he had no other options."},
    {"type":"p","text":"Brown's framework has since been adopted by the NRCS, studied by soil scientists, and replicated on farms across the country. If you're skeptical about regenerative agriculture, start here. This is the practical core of it."},
    {"type":"table","headers":["Principle","The Rule","Where Most Farmers Fall Short"],"rows":[["1. Limit Disturbance","Every tillage pass and overgrazing event costs you biology","Running tillage as routine when it isn't earning its keep"],["2. Keep Soil Covered","Something covers the ground at all times: plant, residue, or mulch","Leaving fields bare from harvest through spring"],["3. Living Roots Year-Round","Always have roots feeding the soil food web","Monoculture calendars with weeks of bare ground between crops"],["4. Maximize Diversity","Multiple species = diverse biology below ground","Single-species cover crops or monoculture pasture"],["5. Integrate Livestock","Managed grazing accelerates every other principle","Crop-only operations that have cut out animals entirely"]]},
    {"type":"h2","text":"Principle 1: Every Disturbance Has a Cost"},
    {"type":"p","text":"Disturbance comes in three forms: mechanical, chemical, and biological. Mechanical disturbance is tillage — every pass destroys the mycorrhizal fungi (underground fungal networks that connect your plants to nutrients and water) you've been building. Chemical disturbance from herbicides and high-rate synthetic fertilizers suppresses soil biology. Biological disturbance is overgrazing — leaving livestock on the same ground too long compacts soil and removes plant canopy."},
    {"type":"p","text":"Brown considers overgrazing as damaging as tillage on rangelands. Your starting point: identify your highest-disturbance practice and ask whether it's necessary at current rates."},
    {"type":"h2","text":"Principle 2: Bare Soil Is a Liability"},
    {"type":"p","text":"Bare soil loses moisture, erodes in wind and rain, heats up to temperatures that kill surface biology, and invites weeds. Brown's rule is simple: something covers the ground at all times — living plants, crop residue, or mulch."},
    {"type":"p","text":"Even a simple winter rye seeding after harvest keeps your soil protected through the cold months. The economic argument is direct: every inch of topsoil you keep is money you didn't have to replace with fertilizer."},
    {"type":"h2","text":"Principle 3: Roots Feed the System"},
    {"type":"p","text":"Plants feed soil biology through their roots. They release sugars and other compounds — called root exudates — that feed bacteria and fungi. Those organisms make nutrients available to your plants. When the ground is bare, that exchange stops and you have to restart it every season."},
    {"type":"p","text":"Living roots year-round means something is always growing. For crop farmers, that means cover crops filling every calendar gap. For ranchers, it means managing grazing so pastures have adequate rest and root systems stay intact. Perennial clovers are cheap to establish and provide both biological nitrogen fixation and continuous root activity."},
    {"type":"h2","text":"Principle 4: Diversity Above Ground Means Diversity Below"},
    {"type":"p","text":"Different plant species have different root architectures. Some go deep and break compaction. Some stay shallow and add organic matter near the surface. Different species host different microbial communities. A diverse plant community above ground means a diverse, resilient biology below ground."},
    {"type":"p","text":"A cover crop mix with five to seven species outperforms a single-species planting on almost every biological metric — nitrogen fixation, organic matter addition, weed suppression, and forage quality. You don't have to do all of this at once. Start by adding one or two species to your current planting."},
    {"type":"h2","text":"Principle 5: Livestock Are a Tool, Not a Problem"},
    {"type":"p","text":"This is the principle most crop farmers skip. Livestock managed well accelerate every other principle. They trample residue into the soil surface, speeding decomposition. Their manure introduces diverse biology. Their hooves create depressions that capture water and seed. Managed grazing has been shown to measurably improve soil carbon levels compared to ungrazed or continuously grazed land [2]."},
    {"type":"p","text":"For ranchers who already have livestock, this principle is about how you graze, not whether you graze. High-density, short-duration grazing with long rest periods mimics the movement of wild herds and produces dramatically different results than continuous grazing on the same ground."},
    {"type":"h2","text":"A Realistic Implementation Sequence"},
    {"type":"p","text":"You don't implement all five principles in year one. Here's a sequence that works for a small operation with limited capital:"},
    {"type":"bullet","text":"Year 1: Principle 2 (soil cover). Plant a simple, affordable cover crop on your most vulnerable ground. Winter rye is cheap, reliable, and works almost everywhere."},
    {"type":"bullet","text":"Year 2: Principle 3 (living roots). Extend your cover crop calendar. Find where you have bare ground in late summer or early fall and fill it."},
    {"type":"bullet","text":"Year 3: Principle 4 (diversity). Upgrade from a single-species cover to a mix. Add a legume to your pasture seeding."},
    {"type":"bullet","text":"Year 4 and beyond: Principles 1 and 5 as your system matures — reduce disturbance and integrate livestock into your crop ground rotation."},
    {"type":"cta","text":"→ Shop cover crop seed at naturesseed.com/products/cover-crop-seed/"},
  ],
  "references": ["Teague, W. R., Apfelbaum, S., Lal, R., Kreuter, U. P., Rowntree, J., Davies, C. A., & Wang, F. (2016). The role of ruminants in reducing agriculture's carbon footprint in North America. Journal of Soil and Water Conservation, 71(2), 156\u2013164. https://doi.org/10.2489/jswc.71.2.156", "USDA Natural Resources Conservation Service. (2014). Soil health: Unlock the secrets in the soil. https://www.nrcs.usda.gov/wps/portal/nrcs/main/soils/health/"]
},

# ── ARTICLE 3 ──────────────────────────────────────────────────────────────
{
  "title": "What Your Soil Test Actually Tells You (And What Most Farmers Miss)",
  "category": "Foundations",
  "read_time": "5 min read",
  "meta": "Learn how to read a soil test — which numbers actually drive yield, what pH really controls, and why organic matter is the most overlooked result on the page.",
  "slug": "03-what-your-soil-test-tells-you",
  "body": [
    {"type":"p","text":"You ran the test, got the report, ordered what the fertilizer recommendation said, and filed it away. You just used 20% of the information on that page."},
    {"type":"p","text":"A soil test is one of the cheapest tools in agriculture — $15 to $30 at most extension offices. But the value only comes if you know which numbers actually matter and what to do when they're off."},
    {"type":"p","text":"Here's how to read the whole page."},
    {"type":"h2","text":"The Numbers That Actually Drive Your Results"},
    {"type":"p","text":"A standard soil test reports pH, organic matter (OM), cation exchange capacity (CEC), phosphorus (P), and potassium (K). Some tests include secondary and micronutrients. Here's what each one means for your farm and what to do when it's wrong."},
    {"type":"table","headers":["Test Result","Why It Matters","Target Range","Fix If Wrong"],"rows":[["pH","Controls whether nutrients already in your soil are available to plants","6.0\u20137.0","Ag lime \u2014 cheap, long-lasting, unlocks fertilizer you've already paid for"],["Organic Matter %","Drives water-holding capacity and biological activity","3%+ (most Midwest/Plains soils)","Cover crops, reduced tillage \u2014 1% increase = 20,000 gal/acre more water [1]"],["CEC (cation exchange capacity \u2014 your soil's nutrient-holding bucket)","How well your soil holds nutrients between applications","Higher = better; clay > sandy","Build OM over time; can't be quickly changed"],["Phosphorus","Fuel for root growth and energy transfer","Medium per your lab","Fix pH first \u2014 P locks up chemically when pH < 6.0 [2]"],["Potassium","Cell function and stress tolerance","Medium per your lab","Cycle through plant residue and manure before buying more"]]},
    {"type":"h2","text":"pH Controls More Than You Think"},
    {"type":"p","text":"Most farmers look at pH and think: acidic or alkaline. That's not the half of it. Your pH controls whether the nutrients already in your soil are chemically available to your plants — regardless of how much is there."},
    {"type":"p","text":"Phosphorus locks up chemically at pH below 6.0 [2]. You could have plenty of P in your soil and still have plants that can't access it. You're not low on phosphorus. You're low on pH management. Fix pH first, and you may not need to buy more P at all."},
    {"type":"p","text":"Ag lime is cheap and long-lasting. If your pH is below 6.0, it's almost always the highest-ROI move on your farm before you touch any other input."},
    {"type":"h2","text":"Organic Matter Is the Number Nobody Watches — Until They Should"},
    {"type":"p","text":"Organic matter is reported as a percentage. Most degraded agricultural soils sit at 1–2%. A healthy, biologically active soil is 3–5% or higher."},
    {"type":"p","text":"Every 1% increase in organic matter allows your soil to hold an additional 20,000 gallons of water per acre [1]. In a dry summer, that's the difference between a stressed crop and a productive one. It's also a direct measure of whether your management is moving in the right direction."},
    {"type":"p","text":"If you're below 2%, building organic matter should be your primary goal — ahead of fertilizer optimization. Cover crops are your most cost-effective tool for moving that number."},
    {"type":"h2","text":"Don't Chase Big P and K Numbers"},
    {"type":"p","text":"Most extension recommendations are calibrated for maximum yield under conventional management. They're not optimized for cost efficiency, and they don't account for biological nutrient cycling."},
    {"type":"p","text":"In a healthy, biologically active soil, phosphorus availability is enhanced by mycorrhizal fungi (underground fungal networks that extend your plant's effective root zone). Potassium cycles through plant residue and microbial activity. If your P and K test at medium or above, hold your fertilizer application and focus on pH and organic matter first."},
    {"type":"h2","text":"What the Test Can't Tell You"},
    {"type":"p","text":"A standard soil test is a chemical snapshot. It doesn't show you:"},
    {"type":"bullet","text":"Biological activity — microbial and fungal populations that drive nutrient cycling don't appear on a standard test. A Haney test or PLFA analysis gives you a window into this."},
    {"type":"bullet","text":"Compaction — a penetrometer test or a screwdriver pushed into the ground tells you more than any lab report about this problem."},
    {"type":"bullet","text":"Water infiltration — pour a gallon of water on bare soil and time how long it takes to absorb. That observation captures something no test does."},
    {"type":"h2","text":"Your Next Move After You Read the Report"},
    {"type":"bullet","text":"Fix pH first if you're outside 6.0–7.0. Lime pays for itself by unlocking fertilizer you've already bought."},
    {"type":"bullet","text":"Plan for organic matter if you're below 3%. Cover crops are your most cost-effective tool."},
    {"type":"bullet","text":"Address genuine nutrient deficiencies once pH is corrected. You may need less than the report suggests."},
    {"type":"bullet","text":"Repeat the test in two to three years and track your trend, not just a single data point."},
    {"type":"cta","text":"→ Shop cover crop seed at naturesseed.com/products/cover-crop-seed/"},
  ],
  "references": ["USDA Natural Resources Conservation Service. (2014). Soil health: Unlock the secrets in the soil. https://www.nrcs.usda.gov/wps/portal/nrcs/main/soils/health/", "Penn State Extension. (2020). Soil acidity and liming: Basic information for farmers and gardeners. https://extension.psu.edu/soil-acidity-and-liming-basic-information-for-farmers-and-gardeners"]
},

# ── ARTICLE 4 ──────────────────────────────────────────────────────────────
{
  "title": "Cover Crops 101: How to Pick Your First Mix Without an Agronomy Degree",
  "category": "Foundations",
  "read_time": "8 min read",
  "meta": "Choosing the right cover crop mix for small farms doesn't have to be complicated. Practical guide to species, seeding rates, and termination for beginners.",
  "slug": "04-cover-crops-101-first-mix",
  "body": [
    {"type":"p","text":"You don't need a formula. A simple three-species mix, planted at a reasonable rate, terminated before it seeds out — that's going to improve your soil this season. Here's how to build one."},
    {"type":"p","text":"Cover crop selection has gotten overcomplicated. People argue about seeding rates to the ounce and termination windows timed to the hour. It's enough to make a first-timer quit before they start."},
    {"type":"p","text":"Don't let it stop you. A simple mix that's in the ground beats a perfect mix that never gets planted."},
    {"type":"h2","text":"Why a Mix Beats a Single Species"},
    {"type":"p","text":"A lot of farmers start with straight winter rye. It's cheap, it grows, it covers the ground. Not a bad start — but a diverse mix outperforms a single species on almost every measure [2]."},
    {"type":"bullet","text":"Functional diversity means more soil benefits at once. Grasses add biomass and organic matter. Legumes fix nitrogen. Brassicas break up compaction. A three-species mix does all three simultaneously."},
    {"type":"bullet","text":"Diverse plantings support more soil biology. Different root architectures host different microbial communities. A field with five species supports a richer soil food web than a monoculture cover crop."},
    {"type":"bullet","text":"Risk management. If one species fails, the others carry the mix. Single-species plantings are all-or-nothing."},
    {"type":"p","text":"Three to five well-chosen species is plenty. You don't need twelve to see the benefits."},
    {"type":"h2","text":"The Three Functional Groups — What Each Does and What to Plant"},
    {"type":"table","headers":["Group","What It Does","Best Species","Drilled Rate","Nature's Seed"],"rows":[["Grasses","Biomass, organic matter, weed suppression","Winter rye, oats","Rye: 60\u201390 lbs/ac; Oats: 60\u201380 lbs/ac","naturesseed.com/products/pasture-seed/cereal-rye/"],["Legumes","Fixes nitrogen \u2014 60\u2013120 lbs N/ac under good conditions [1]","Crimson clover, hairy vetch, field peas","Crimson: 15\u201320 lbs/ac; Vetch: 15\u201325 lbs/ac","naturesseed.com/pasture-seed/individual-pasture-species/crimson-clover/"],["Brassicas","Deep taproot breaks compaction; scavenges nutrients from depth","Daikon radish, turnip","Radish: 5\u20138 lbs/ac; Turnip: 3\u20135 lbs/ac","NS Soil Builder Kit includes mustard (similar function)"]]},
    {"type":"p","text":"When you're mixing species, reduce each individual rate by roughly 30–40% from the drilled rate above. When broadcasting into standing crops, increase total rates by 25–30%."},
    {"type":"h2","text":"Build Your Mix Around One Goal"},
    {"type":"p","text":"Don't just pick random species. Decide what your field needs most, then build around it."},
    {"type":"bullet","text":"Suppress weeds: Lead with high-biomass grasses. Suggested mix: Winter rye + hairy vetch."},
    {"type":"bullet","text":"Build organic matter: Maximize biomass with grasses and brassicas. Suggested mix: Oats + winter rye + turnip."},
    {"type":"bullet","text":"Fix nitrogen for next crop: Lead with legumes. Suggested mix: Hairy vetch + crimson clover + winter rye."},
    {"type":"bullet","text":"Establish grazeable forage: Choose palatable species. Suggested mix: Oats + field peas + crimson clover."},
    {"type":"h2","text":"Termination: Decide Before You Plant"},
    {"type":"p","text":"Termination is where first-timers most often wait too long. The cover crop sets seed, becomes harder to kill, and creates a bigger mess than planned. The main rule: terminate before seed set."},
    {"type":"bullet","text":"Mowing: Low-cost, works well for clover and oats. Less effective on thick-stemmed covers like mature rye or sorghum-sudan."},
    {"type":"bullet","text":"Grazing: The best method when it fits. Livestock do the work, deposit nutrients, and you get a forage benefit. Works well for mixes with field peas, oats, and clovers."},
    {"type":"bullet","text":"Rolling/crimping: No-till termination for organic producers. Requires the cover to be at or past anthesis (flowering stage) to work effectively."},
    {"type":"bullet","text":"Herbicide termination: Fastest and most reliable. Glyphosate at label rate terminates most cover crops cleanly when weather or timing is tight."},
    {"type":"h2","text":"What to Avoid in Year One"},
    {"type":"bullet","text":"Over-complicating the mix. Three to five species is enough. Eight-species mixes are impressive on paper, not necessary in practice."},
    {"type":"bullet","text":"Planting too late. Cool-season covers need 4–6 weeks of growth before hard frost to do any good."},
    {"type":"bullet","text":"Forgetting inoculant on legumes. Legumes need specific rhizobia bacteria to fix nitrogen. If you haven't grown legumes in a field before, inoculate the seed — it's cheap and makes a real difference."},
    {"type":"h2","text":"A Simple Starter Mix for Pasture Improvement"},
    {"type":"p","text":"If you want a reliable first-year mix, here's one that covers the bases without overthinking it:"},
    {"type":"bullet","text":"Winter rye: 40 lbs/acre"},
    {"type":"bullet","text":"Crimson clover: 10 lbs/acre"},
    {"type":"bullet","text":"Daikon radish: 4 lbs/acre"},
    {"type":"p","text":"Broadcast or drill in late summer to early fall. Inoculate the clover. Graze or mow before rye heads out in spring. The rye adds biomass and winter cover, the clover fixes nitrogen and improves forage quality, and the radish breaks up compaction. That's a full season of soil improvement from one simple planting."},
    {"type":"cta","text":"→ Shop cover crop seed at naturesseed.com/products/cover-crop-seed/"},
  ],
  "references": ["Sustainable Agriculture Research & Education (SARE). (2012). Managing cover crops profitably (3rd ed.). https://www.sare.org/resources/managing-cover-crops-profitably-3rd-edition/", "Blanco-Canqui, H., et al. (2015). Cover crops and ecosystem services: Insights from studies in temperate soils. Agronomy Journal, 107(6), 2449\u20132474. https://doi.org/10.2134/agronj15.0086"]
},


# ── ARTICLE 5 ──────────────────────────────────────────────────────────────
{
  "title": "Frost Seeding Clover Into an Existing Pasture",
  "category": "Practical How-To",
  "read_time": "5 min read",
  "meta": "Frost seeding clover is the lowest-cost pasture improvement available — no tillage, no equipment, just seed and timing. Here's how to do it right.",
  "slug": "05-frost-seeding-clover",
  "body": [
    {"type":"p","text":"It's mid-February. The ground is still frozen before sunrise but thaws by noon. You've got nothing useful to do outside. And there's a bag of clover seed sitting in the barn. That's your window — and it costs almost nothing to use it."},
    {"type":"p","text":"Frost seeding is the practice of broadcasting clover seed directly onto existing pasture in late winter and letting freeze-thaw cycles work the seed into the soil naturally. No tillage. No drill. No seedbed prep."},
    {"type":"p","text":"As temperatures swing above and below freezing, the soil surface heaves slightly. That movement creates micro-pockets that capture seed and pull it into contact with the soil. When spring arrives, your clover germinates into an already-established pasture."},
    {"type":"h2","text":"Why Clover Specifically"},
    {"type":"p","text":"Clover seed is tiny — small enough to work into soil crevices created by freeze-thaw movement. Large-seeded species like grasses need actual soil disturbance to establish reliably. Clover doesn't."},
    {"type":"p","text":"Red and white clovers fix 80–150 lbs of atmospheric nitrogen per acre per year under good conditions [1]. That's fertilizer your pasture produces itself. Every acre of established clover is an acre that needs less purchased nitrogen input."},
    {"type":"p","text":"Adding 20–30% clover to a grass-dominated stand measurably improves average daily gain in cattle and reduces your hay window in spring by boosting early-season forage quality. Your animals eat better and you spend less — that's the so what."},
    {"type":"h2","text":"Timing Is the One Variable That Matters Most"},
    {"type":"p","text":"You want the last consistent freeze-thaw cycles of winter — not the dead of winter, not spring. The target window is when nighttime temperatures are still dropping below freezing but daytime temperatures are climbing above 32°F."},
    {"type":"p","text":"In most of the Midwest and Northeast, that's mid-February through early March. In the upper Midwest or mountain states, it shifts two to four weeks later."},
    {"type":"p","text":"Seed too early and it just sits on frozen ground. Seed too late — when soil has thawed and grass is actively growing — and you lose the mechanical advantage of heaving soil entirely."},
    {"type":"h2","text":"Which Species Should You Plant?"},
    {"type":"table","headers":["Species","Best For","Seeding Rate","Lifespan","Key Note"],"rows":[
      ["Red clover","Quick-establishing forage and hay fields","6–10 lbs/acre","2–3 years (reseeds if allowed to flower)","Establishes faster than white; higher biomass in year one"],
      ["White clover","Continuously grazed pastures","2–4 lbs/acre","Perennial — spreads by stolons indefinitely","Lower-growing; more persistent under frequent grazing pressure"],
      ["Red + white mix","Best of both — quick start and long-term persistence","4–6 lbs red + 2 lbs white per acre","Perennial base with fast establishment","Recommended approach for most operations"]
    ]},
    {"type":"p","text":"Inoculate your seed if you haven't grown clover in the field in the past three to five years. Clover needs specific Rhizobium bacteria to fix nitrogen. If that history is absent, pre-inoculated seed or a powder inoculant is cheap insurance."},
    {"type":"h2","text":"Pasture Conditions That Set You Up for Success"},
    {"type":"p","text":"Your frost seeding success rate is highest when the existing stand is thin or patchy. Thick, established grass will outcompete clover seedlings. Frost seeding works best where there are visible gaps in the canopy."},
    {"type":"p","text":"Check your soil pH before you broadcast. Clover struggles to establish and fix nitrogen in acidic soils — if your pH is below 6.0, lime the field first. Frost seeding into low-pH ground is money wasted."},
    {"type":"p","text":"After seeding, keep livestock off the field until clover reaches 4–6 inches in height. A single early grazing pass before establishment can wipe out your stand before it ever gets going."},
    {"type":"h2","text":"What to Expect the First Year"},
    {"type":"p","text":"Frost-seeded clover doesn't look impressive until late spring. Germination is slow and seedlings are tiny. Don't panic — this is normal. By July of the seeding year, a successful stand will be visible and providing real forage contribution."},
    {"type":"p","text":"Establishment success rates for frost seeding run 60–80% in good conditions. It's not perfect. But it's cheap enough that you can repeat it two years running and still come out ahead compared to drilling."},
    {"type":"cta","text":"→ Shop red clover and white clover seed at naturesseed.com/products/clover-seed/"},
  ],
  "references": ["Sustainable Agriculture Research & Education (SARE). (2012). Managing cover crops profitably (3rd ed.). https://www.sare.org/resources/managing-cover-crops-profitably-3rd-edition/"]
},

# ── ARTICLE 6 ──────────────────────────────────────────────────────────────
{
  "title": "Renovating a Tired Hobby Farm Pasture in One Season",
  "category": "Practical How-To",
  "read_time": "9 min read",
  "meta": "Overseeding vs. full renovation for a depleted hobby farm pasture — how to diagnose which your ground needs, and what to plant to turn it around in one season.",
  "slug": "06-renovating-hobby-farm-pasture",
  "body": [
    {"type":"p","text":"Most small farms inherit a tired pasture. Someone grazed it hard for a few years, never reseeded, and handed you the problem. Here's how to fix it — and how to know whether you can do it cheaply or need to start over."},
    {"type":"p","text":"The key is diagnosing how bad it actually is. That answer determines whether you overseed into what's there or burn it down and start fresh. Get the diagnosis wrong and you waste a full growing season and your seed budget."},
    {"type":"h2","text":"Overseed or Renovate? Walk the Pasture First"},
    {"type":"p","text":"Walk your pasture and estimate your existing stand coverage. This single number determines your path."},
    {"type":"table","headers":["Existing Stand Coverage","Verdict","Approach","Estimated Cost/Acre"],"rows":[
      [">50% desirable species","Overseed","No-till drill or slit-seeder into existing stand","$25–50 seed + $50–100 equipment rental"],
      ["25–50% desirable species","Borderline — evaluate","Light herbicide + overseed, or full renovation","$80–150 depending on conditions"],
      ["<25% desirable species","Full renovation","Kill stand, prep seedbed, replant from scratch","$80–120 all-in for a 10-acre field"]
    ]},
    {"type":"p","text":"The honest calculus is cost vs. reliability. Overseeding is cheaper and less disruptive. Full renovation costs more upfront but gives you a predictable outcome. If you're below 30–35% desirable cover, the extra cost of renovation often pays for itself in first-year forage production."},
    {"type":"h2","text":"Overseeding a Tired Stand"},
    {"type":"p","text":"Overseeding works by introducing new seed into a thinned existing stand. For it to succeed, you need seed-to-soil contact — not seed sitting on top of thatch or dense sod."},
    {"type":"h3","text":"Step 1 — Stress the existing stand first"},
    {"type":"p","text":"Graze the pasture hard in early spring or late fall, just before you overseed. Get existing grass short — 2 to 3 inches. This reduces competition for new seedlings and exposes the soil surface. If grazing isn't an option, mow it low."},
    {"type":"h3","text":"Step 2 — Test and fix your soil"},
    {"type":"p","text":"Run a soil test before you spend money on seed. pH below 6.0 will cost you your clover. Compaction will cost you establishment depth. Lime if needed. This is the step most hobby farm operators skip, and it explains why their overseeding fails."},
    {"type":"h3","text":"Step 3 — Use a no-till drill or slit seeder"},
    {"type":"p","text":"A no-till drill or slit seeder — widely available at farm co-ops and equipment dealers — places seed directly into the soil without full tillage. You get consistent seed-to-soil contact, better germination, and higher establishment rates than broadcasting. Budget $50–100/acre for rental. It's worth it."},
    {"type":"h3","text":"Step 4 — Protect new seedlings from grazing"},
    {"type":"p","text":"New seedlings need at least 60–90 days to develop root systems before they can withstand grazing pressure. Fence animals out completely if possible, or use temporary electric fence to protect newly seeded areas. This is where most renovations fail."},
    {"type":"h2","text":"Full Renovation: When to Start Over"},
    {"type":"p","text":"Full renovation means killing the existing stand and starting from scratch. Done right, it gives you a clean seedbed and the flexibility to choose exactly what goes back in the ground."},
    {"type":"h3","text":"Killing the old stand"},
    {"type":"p","text":"The most reliable method is a full-rate glyphosate application when the existing grass is actively growing — temperatures above 55°F, stand green and growing. A single application at label rate terminates most cool-season grass pastures cleanly. Allow 10–14 days before tillage or seeding."},
    {"type":"p","text":"For organic operations: repeated intensive tillage (two to three passes) in summer will desiccate most stands if timing aligns with hot, dry conditions. It takes longer but achieves a similar result."},
    {"type":"h3","text":"Seedbed preparation"},
    {"type":"p","text":"One to two passes with a disk or field cultivator creates a workable seedbed. You want firm, fine soil — not fluffy or cloddy. A culti-packer or roller after seeding improves seed-to-soil contact."},
    {"type":"h2","text":"What to Plant After Renovation"},
    {"type":"p","text":"Your renovation is also your chance to be intentional about what goes back in the ground. Here's a practical species selection framework for hobby farm pastures."},
    {"type":"table","headers":["Component","Species","Purpose","NS Link"],"rows":[
      ["Base grass","Orchardgrass","Shade-tolerant, palatable, productive","naturesseed.com/products/pasture-seed/orchardgrass/"],
      ["Base grass","Tall fescue","Durable, drought-tolerant, stockpile-ready in winter","naturesseed.com/products/pasture-seed/tall-fescue/"],
      ["Legume","Red clover","Fast nitrogen contribution, improves forage quality","naturesseed.com/products/clover-seed/red-clover-seed/"],
      ["Legume","White clover","Persistent, grazing-tolerant, long-term nitrogen","naturesseed.com/products/clover-seed/white-dutch-clover/"]
    ]},
    {"type":"h2","text":"Timing: Late Summer Beats Spring"},
    {"type":"p","text":"For cool-season grasses, two windows work: late summer (August–September) or spring (March–May). Late summer is better — cooler temperatures reduce weed competition, and seedlings establish through fall and are ready to graze the following spring."},
    {"type":"p","text":"If you have to seed in spring, use a companion crop like oats to suppress weeds and provide early forage while your perennials establish."},
    {"type":"h2","text":"Budget Reality for a 10-Acre Field"},
    {"type":"p","text":"Seed runs $150–250, herbicide $80–120, equipment rental $400–600 for drill and light tillage, and lime $150–200 if needed. All-in: $800–1,200 for a 10-acre full renovation, or $80–120 per acre for a pasture you'll use for the next decade."},
    {"type":"p","text":"Against the cost of hay, or a nutritionist explaining why your livestock aren't gaining, it's one of the better investments you'll make on a small farm."},
    {"type":"cta","text":"→ The Thin Pasture Fix Kit at naturesseed.com/products/pasture-seed/thin-pasture-kit/ is a ready-to-go mix for exactly this situation."},
  ],
  "references": ["Sustainable Agriculture Research & Education (SARE). (2012). Managing cover crops profitably (3rd ed.). https://www.sare.org/resources/managing-cover-crops-profitably-3rd-edition/"]
},

# ── ARTICLE 7 ──────────────────────────────────────────────────────────────
{
  "title": "Stockpile Grazing: How to Save on Hay When You Have the Right Grass",
  "category": "Practical How-To",
  "read_time": "6 min read",
  "meta": "Stockpile grazing with tall fescue is one of the most cost-effective winter feeding strategies for small operations. Here's how the timing and management works.",
  "slug": "07-stockpile-grazing-save-on-hay",
  "body": [
    {"type":"p","text":"Every bale you don't have to feed this winter is money that stays in your pocket. Stockpile grazing — letting grass accumulate in fall and grazing it through winter — can cut your hay consumption by 30–50% [1] with the right grass and the right timing."},
    {"type":"p","text":"The practice is simple: close a field to grazing in late summer, let it accumulate growth, and graze it standing during the months when it would otherwise be unavailable. Done well, you extend your grazing season by 60–90 days without a dollar in additional feed cost."},
    {"type":"p","text":"The grass that makes this possible is tall fescue. But it's not the only option — and knowing which grasses stockpile well in your climate determines how much hay you actually save."},
    {"type":"h2","text":"Which Grasses Stockpile Well?"},
    {"type":"table","headers":["Grass","Winter Quality Retention","Cold Hardiness","Stockpile Potential","Notes"],"rows":[
      ["Tall fescue","Excellent — 12–16% crude protein [2] after frost","Excellent","Best nationwide","Use novel-endophyte variety to avoid toxicosis in cattle"],
      ["Orchardgrass","Moderate — quality declines faster than fescue","Good","Second-best option","Worth stockpiling if fescue isn't established yet"],
      ["Annual ryegrass","Good quality in mild climates","Moderate (winter-kills above zone 6)","Reliable in zones 6+","Fast-establishing alternative where fescue isn't an option"],
      ["Kentucky bluegrass","Moderate — semi-dormant in cold","Good","Low","Not recommended as primary stockpile grass"],
      ["Bermudagrass","Moderate (semi-dormant)","Poor north of zone 7","Good in the South only","Southern operations only"]
    ]},
    {"type":"p","text":"Tall fescue stands out because freeze-thaw cycling actually improves its palatability — by the time you're grazing it in December and January, the quality is often better than it was in September. That's the so what: the longer you wait, the better it gets."},
    {"type":"h2","text":"One Note on Fescue Variety"},
    {"type":"p","text":"Endophyte-infected tall fescue can cause toxicosis in cattle, particularly in late gestation and finishing animals. If you're establishing new fescue for stockpiling, use a novel-endophyte variety (like MaxQ) or endophyte-free seed."},
    {"type":"p","text":"Existing fescue stands should be assessed — many older fields in the transition zone carry the toxic endophyte, and the negative effects on animal performance can offset your hay savings entirely."},
    {"type":"h2","text":"The Accumulation Window: Timing Is Everything"},
    {"type":"p","text":"Close the field to grazing in late August to early September — ideally 60 to 75 days before your expected first hard frost. That's your accumulation window. The fescue grows during the relatively warm days of late summer and builds significant dry matter."},
    {"type":"p","text":"Apply 50 lbs of actual nitrogen per acre in the first week of the accumulation period. At current urea prices, you're spending $30–50/acre to potentially grow an additional 1,000–1,500 lbs of dry matter. That's one of the best single-fertilizer ROI moves on a cow-calf operation."},
    {"type":"p","text":"Don't touch the field — no grazing, no clipping — from closure until you're ready to graze in late fall or early winter."},
    {"type":"h2","text":"Strip Grazing: Don't Open the Whole Field at Once"},
    {"type":"p","text":"Cattle are wasteful grazers when given large areas. They'll graze the most accessible sections repeatedly, trample a significant portion of your stockpile, and burn through your 90-day supply in 30 days."},
    {"type":"p","text":"Strip grazing — using temporary electric fence to give animals access to a fresh strip every few days — reduces waste by 40–60% and forces uniform utilization across the field. Setup cost: under $200. Payback: immediate."},
    {"type":"p","text":"Run a single strand of polywire parallel to a fence line and move it every three to five days. A step-in post every 20 feet, a reel, and a single wire energizer is all the equipment you need."},
    {"type":"h2","text":"How Much Stockpile Do You Actually Need?"},
    {"type":"p","text":"A 1,200-lb cow requires 24–30 lbs of dry matter daily. Well-managed stockpile can yield 2,000–3,500 lbs of dry matter per acre depending on fertility, rainfall, and variety."},
    {"type":"p","text":"For a 30-cow herd, 60 extra hay-free days: 30 cows × 27 lbs/day × 60 days = 48,600 lbs dry matter needed. At 2,500 lbs/acre stockpile, that's roughly 20 acres. Adjust the math to your herd size and your target days off hay."},
    {"type":"cta","text":"→ Shop tall fescue seed at naturesseed.com/products/pasture-seed/tall-fescue/ — or annual ryegrass at naturesseed.com/pasture-seed/individual-pasture-species/annual-ryegrass/ for a faster-establishing option."},
  ],
  "references": ["Ball, D. M., Hoveland, C. S., & Lacefield, G. D. (2015). Southern forages (5th ed.). International Plant Nutrition Institute.", "University of Kentucky Cooperative Extension Service. (2016). Stockpiling tall fescue for fall and winter grazing (AGR-162). https://publications.ca.uky.edu/sites/publications.ca.uky.edu/files/agr162.pdf"]
},

# ── ARTICLE 8 ──────────────────────────────────────────────────────────────
{
  "title": "Why Mycorrhizae Matter for Pasture Establishment (And How to Use Them)",
  "category": "Practical How-To",
  "read_time": "5 min read",
  "meta": "Mycorrhizal fungi dramatically improve pasture and cover crop establishment — here's the soil biology behind it and a practical guide to inoculating at seeding.",
  "slug": "08-mycorrhizae-pasture-establishment",
  "body": [
    {"type":"p","text":"You prep your seedbed. You buy quality seed. You plant at the right time. And still you get spotty establishment in dry years. The missing piece is usually invisible: the fungal community living in your soil."},
    {"type":"p","text":"Specifically, arbuscular mycorrhizal fungi (AMF) — the most common type, and the one that colonizes grasses, legumes, and most pasture species. AMF form a symbiotic relationship with plant roots, extending far beyond the root zone to access phosphorus, water, and micronutrients the plant can't reach on its own."},
    {"type":"p","text":"In exchange, the plant supplies the fungi with sugars. It's a trade your establishing seedlings can't afford to skip — and in many farmed soils, the fungi aren't there to show up to the deal."},
    {"type":"h2","text":"What Mycorrhizal Fungi Actually Do for Your Seedlings"},
    {"type":"p","text":"Under drought conditions, colonized seedlings can access moisture from a soil volume 10–100 times larger than their actual root zone [1]. During the vulnerable establishment window — when seedlings are small and root systems shallow — that's often the difference between a stand and a failure."},
    {"type":"p","text":"Beyond establishment, AMF also improve phosphorus uptake in low-P soils and improve soil structure through glomalin production (a glue-like protein that binds soil aggregates) [2]. The benefits compound over time as the fungal network builds."},
    {"type":"p","text":"That's the so what: one cheap inoculant application at seeding pays dividends through the entire life of your pasture."},
    {"type":"h2","text":"Why Many Farmed Soils Are Mycorrhizal Deserts"},
    {"type":"p","text":"Native soils with undisturbed plant communities are rich in mycorrhizal spore banks — dormant spores that germinate when roots pass nearby. Farmed soils are often depleted. Frequent tillage physically disrupts fungal networks. High phosphorus fertility reduces the plant's incentive to maintain mycorrhizal associations — plants outsource nutrient acquisition to fungi only when they're nutrient-limited."},
    {"type":"p","text":"This is why establishing a new pasture in a recently tilled, fertilized field often produces uneven results in the first two to three years. The biology isn't there to support robust establishment. Your seed is doing the work alone."},
    {"type":"h2","text":"Which Species Respond to Inoculation?"},
    {"type":"table","headers":["Species","Forms AMF Association?","Inoculant Recommended?","Notes"],"rows":[
      ["Orchardgrass","Yes","Yes — in fields without recent grass history","Particularly valuable on sandy or low-P soils"],
      ["Tall fescue","Yes","Yes — in new or renovated fields","AMF colonization improves drought survival during establishment"],
      ["Red clover / white clover","Yes (AMF + Rhizobium bacteria)","Yes — both types needed","Two separate inoculants; don't skip either one"],
      ["Alfalfa","Yes (AMF + Rhizobium)","Yes — both types needed","High-value legume; inoculant pays back quickly"],
      ["Brassicas (turnip, radish, kale, mustard)","No","No — don't waste inoculant","Brassicas do not form mycorrhizal associations"]
    ]},
    {"type":"h2","text":"How to Inoculate at Seeding"},
    {"type":"p","text":"Apply a mycorrhizal inoculant at seeding — this introduces AMF spores directly to the seedling root zone, where they can colonize quickly without waiting for a depleted spore bank. Commercial inoculants come in powder, granular, and liquid forms."},
    {"type":"bullet","text":"Seed coating: Mix dry inoculant powder with seed before loading the drill or spreader. Most products specify a ratio by weight. Gets inoculant directly in contact with germinating seeds."},
    {"type":"bullet","text":"In-furrow granular: Apply granular inoculant through the fertilizer hopper on a grain drill, placing it in the seed trench. More precise than seed coating, and no concern about inoculant viability if there's a delay between coating and planting."},
    {"type":"h2","text":"Protecting the Fungal Community After Establishment"},
    {"type":"p","text":"Inoculating at seeding is just the start. How you manage afterward determines whether the fungal community builds or collapses."},
    {"type":"bullet","text":"Avoid unnecessary tillage. Every pass severs hyphal networks. In an established pasture, this isn't usually an issue — but renovation is another reason to overseed rather than till when possible."},
    {"type":"bullet","text":"Keep living roots in the ground. Fungi depend on plant hosts for energy. Bare soil periods — extreme overgrazing, prolonged fallow — allow the fungal population to decline."},
    {"type":"bullet","text":"Use phosphorus inputs carefully. High soil phosphorus suppresses mycorrhizal associations. Apply based on soil test results, not standard rates. Over-application is expensive and biologically counterproductive."},
    {"type":"cta","text":"→ Shop orchardgrass, tall fescue, and clover seed at naturesseed.com/products/pasture-seed/"},
  ],
  "references": ["Smith, S. E., & Read, D. J. (2008). Mycorrhizal symbiosis (3rd ed.). Academic Press.", "Rillig, M. C. (2004). Arbuscular mycorrhizae, glomalin, and soil aggregation. Canadian Journal of Soil Science, 84(4), 355\u2013363. https://doi.org/10.4141/S04-003"]
},

# ── ARTICLE 9 ──────────────────────────────────────────────────────────────
{
  "title": "Silvopasture: Growing Forage Under Trees Without Killing Either",
  "category": "Niche Deep Dives",
  "read_time": "10 min read",
  "meta": "Silvopasture integrates trees and livestock pasture for long-term productivity. Species selection, spacing, and shade management for small and medium operations.",
  "slug": "09-silvopasture-forage-under-trees",
  "body": [
    {"type":"p","text":"Silvopasture is one of the older land use systems in agriculture, predating modern row cropping by centuries. Farmers in Europe and Latin America have grazed livestock in wooded settings for generations. In North America, it largely disappeared as agriculture industrialized. It's coming back now — partly because of carbon payment programs, partly because a growing number of ranchers have rediscovered that trees and livestock can coexist profitably."},
    {"type":"p","text":"The pitch for silvopasture on a small or medium operation isn't primarily about carbon credits. It's about stacking productive uses on the same acre: timber or nut crop income layered on top of grazing income, with a microclimate under the canopy that can actually improve forage quality compared to open pasture in hot summer months."},
    {"type":"p","text":"The challenge: getting the tree and forage components to coexist without the trees shading out the grass or the livestock girdling the trees. That's a management and design problem, and it's solvable."},
    {"type":"h2","text":"What Silvopasture Actually Looks Like"},
    {"type":"p","text":"There are three basic configurations, and the right one depends on what you're starting with."},
    {"type":"h3","text":"Trees planted into existing pasture"},
    {"type":"p","text":"The most common approach for small operations starting from scratch. Establish rows of trees across existing pasture at wide spacing — 30 to 60 feet between rows depending on species — and manage the alleys between rows as normal pasture. Tree density is low enough that ground-level light is maintained for forage production."},
    {"type":"h3","text":"Pasture established under existing trees"},
    {"type":"p","text":"Common on farms that have existing woodland or established shelter belts. Clear the understory brush, open up canopy where needed for adequate light, and establish shade-tolerant forage species in the openings. This approach is cheaper than planting new trees and produces faster results."},
    {"type":"h3","text":"Thinned forest conversion"},
    {"type":"p","text":"Take an existing woodlot, thin it to a target basal area that allows enough light for forage growth (typically 40–60% canopy cover), and establish forage in the openings. This is the most complex approach but also the one with the most potential for existing forested land."},
    {"type":"h2","text":"Light: The Variable Everything Else Depends On"},
    {"type":"p","text":"Forage grasses need light. Most cool-season grasses require at least 50–60% of full sunlight to maintain productive stands. Below that threshold, grass thins out, weed species tolerant of shade move in, and forage quality declines."},
    {"type":"p","text":"The design goal of silvopasture is to maintain canopy cover in the 30–50% range — enough shade to provide livestock comfort on hot summer days and buffer forage quality, but not so much that forage production collapses. Getting there requires attention to tree row orientation (east-west rows create more uniform shade distribution), spacing, and long-term pruning management."},
    {"type":"p","text":"As trees mature and canopy closes, you'll need to either manage row width through pruning or accept that forage production gradually shifts from light-demanding grasses to shade-tolerant species and eventually to a forest understory system."},
    {"type":"h2","text":"Tree Species Selection"},
    {"type":"p","text":"The right tree species depends on your goals, region, and market access. General categories:"},
    {"type":"h3","text":"Timber species"},
    {"type":"p","text":"Black walnut, white oak, and black locust are common choices in the eastern US. Black locust fixes nitrogen, grows fast, and produces rot-resistant wood — it's arguably the best multifunctional silvopasture tree in humid climates east of the Mississippi. Black walnut allelopathic compounds can suppress some pasture species; keep grass rows 10–12 feet from walnut trunks and focus on allelopathy-tolerant species (tall fescue handles it reasonably well)."},
    {"type":"h3","text":"Nut and fruit species"},
    {"type":"p","text":"Chestnut and pecan for nut production. Chestnuts in particular work well in silvopasture — fast-growing, non-allelopathic, and the nuts make excellent livestock feed for the portion that falls and isn't harvested. Apples and pears in orchard configurations with livestock grazing between rows (a practice common in old orchards) is a simpler, lower-establishment-cost version of the same idea."},
    {"type":"h3","text":"Fodder trees"},
    {"type":"p","text":"Mulberry and willow cut-and-carry systems have gotten renewed attention as a direct livestock feed supplement. Mulberry leaves have crude protein levels of 15–20%, comparable to alfalfa, and can be harvested by coppicing — cutting back to a stump to produce fresh growth repeatedly."},
    {"type":"h2","text":"Forage Species for Shade"},
    {"type":"p","text":"Not all pasture species tolerate partial shade equally well. Performance ranking under moderate shade (30–50% canopy cover):"},
    {"type":"bullet","text":"Good tolerance: Orchardgrass, endophyte-free tall fescue, white clover, birdsfoot trefoil."},
    {"type":"bullet","text":"Moderate tolerance: Timothy, red clover, annual ryegrass."},
    {"type":"bullet","text":"Poor tolerance: Bermudagrass, most warm-season grasses, alfalfa."},
    {"type":"p","text":"Orchardgrass is the standout performer in silvopasture systems across the temperate US. It was named for its original habitat — orchards — and its shade tolerance reflects that history. It's productive, palatable, and persistent under the kind of partial shade a well-managed silvopasture system provides."},
    {"type":"h2","text":"Protecting Young Trees From Livestock"},
    {"type":"p","text":"This is where most silvopasture attempts fail in years one through five. Young trees are defenseless against livestock. Cattle will rub, browse, and girdle a sapling in a single grazing event."},
    {"type":"p","text":"Tree protection options in roughly increasing cost:"},
    {"type":"bullet","text":"Individual tree tubes (treeshelters): Plastic tubes that protect the trunk and accelerate early growth. Cost: $3–6 per tree. Works well for smaller diameter planting stock. Provides 3–5 years of protection before trees outgrow them."},
    {"type":"bullet","text":"Wire cages: 4–5 feet of hardware cloth or cattle panel formed into a cylinder. More durable than treeshelters and better for browsing pressure from sheep and goats. Cost: $8–15 per tree."},
    {"type":"bullet","text":"Temporary electric fence exclusion: Fence off entire tree rows until trees reach a size that can withstand livestock contact (typically 3-inch trunk diameter or larger). Remove fencing once trees are established. Higher upfront cost but flexible and reusable."},
    {"type":"h2","text":"Carbon and Cost-Share Opportunities"},
    {"type":"p","text":"Silvopasture is one of the practices explicitly supported under USDA EQIP (Environmental Quality Incentives Program) cost-sharing. Payments vary by state but can offset 50–75% of tree establishment costs. Your local NRCS office is the starting point for applications."},
    {"type":"p","text":"Carbon markets are increasingly offering payments for silvopasture establishment through programs like the USDA's voluntary carbon market initiatives and private aggregators. Per-acre payments range widely ($10–50/acre/year depending on the program and verification standards). The market is immature and monitoring requirements can be burdensome for small operations, but it's worth understanding what's available."},
    {"type":"cta","text":"→ Orchardgrass and white clover are the core of most silvopasture forage mixes. Nature's Seed carries both, along with regionally appropriate shade-tolerant species. Browse pasture seed at naturesseed.com."},
  ]
},

# ── ARTICLE 10 ──────────────────────────────────────────────────────────────
{
  "title": "Pollinator Forage for Beekeepers With Acreage: Beyond Clover",
  "category": "Niche Deep Dives",
  "read_time": "7 min read",
  "meta": "Building a season-long pollinator forage calendar for beekeepers with acreage — species selection, bloom timing, and how to sequence plantings for continuous nectar flow.",
  "slug": "10-pollinator-forage-beekeepers",
  "body": [
    {"type":"p","text":"Most beekeeping guides tell you to plant clover and call it done. That's not wrong — clovers are excellent pollinator plants and easy to establish on acreage. But if you have more than a few acres to work with, you can build something significantly better: a managed forage calendar that provides nectar and pollen from spring through hard frost, extending your colony's productive season and reducing supplemental feeding."},
    {"type":"p","text":"The goal isn't more species for the sake of diversity. It's strategic bloom sequencing — different plants flowering at different windows so your colonies always have something working."},
    {"type":"h2","text":"The Calendar Problem"},
    {"type":"p","text":"Most forage landscapes have boom-and-bust patterns. There's an intense spring flush — dandelions, fruit tree bloom, early clover — followed by a mid-summer dearth as temperatures spike and most plantings finish blooming. Then a fall flow from asters and goldenrod, if you're lucky."},
    {"type":"p","text":"The summer dearth is when colonies starve, swarm from stress, or simply fail to build winter reserves. If you have acreage, you can fill that gap with intentional plantings."},
    {"type":"h2","text":"Early Season (April–May)"},
    {"type":"p","text":"The goal in early season is building colony population ahead of the main nectar flow. Pollen matters as much as nectar here — bees need protein to raise brood."},
    {"type":"bullet","text":"Phacelia (Phacelia tanacetifolia): One of the best early-season bee plants in North America. Deep blue flowers, long bloom window of 4–6 weeks, extremely high nectar and pollen production. Reseeds aggressively if you let it go to seed. Annual. Seeding rate: 2–4 lbs/acre."},
    {"type":"bullet","text":"Crimson clover: Earlier-blooming than red or white clover, typically April–May in zones 6+. Excellent pollen source. Annual in most climates. Seeding rate: 10–15 lbs/acre."},
    {"type":"bullet","text":"Borage: Fast-establishing annual with a very long bloom window. Self-seeds readily. Good gap-filler in small plots."},
    {"type":"h2","text":"Main Flow Season (June–July)"},
    {"type":"p","text":"This is when most colonies make their surplus honey. The foundation:"},
    {"type":"bullet","text":"White clover (Trifolium repens): The gold standard for honey production. High nectar sugar concentration, exceptionally accessible flower depth for honeybees. Persistent perennial that spreads by stolons. Tolerates repeated mowing and grazing. The non-negotiable inclusion in any beekeeper's forage plan. Seeding rate: 2–4 lbs/acre."},
    {"type":"bullet","text":"Red clover: Higher biomass than white, blooms slightly later. Flower tube depth can limit nectar access for short-tongued honeybees — mixed results. Better for bumblebees and long-tongued species. Worth including but not the primary honey producer."},
    {"type":"bullet","text":"Sweet clover (Melilotus officinalis / M. alba): One of the best honey plants in North America when allowed to bloom freely. Biennial. Produces enormous biomass in year two before flowering and dying. Honey from sweet clover operations commands a premium. Note: sweet clover contains coumarin and can be problematic in hay — keep it in designated pollinator plots rather than multi-use hay fields."},
    {"type":"bullet","text":"Buckwheat: A warm-season annual that fills the midsummer gap where cool-season clovers have finished. Blooms intensely for 4–6 weeks in midsummer. Honey is dark and strongly flavored — valued by some markets, not others. Seeding rate: 40–50 lbs/acre. Plant after last frost."},
    {"type":"h2","text":"Late Season and Fall (August–October)"},
    {"type":"p","text":"Fall forage is critical for winter prep. Colonies need to build winter stores through September. Native plants are your best allies here."},
    {"type":"bullet","text":"Goldenrod (Solidago spp.): The most important fall nectar plant in North America east of the Rockies. Blooms August through October depending on species. Native perennial, spreads readily, requires zero maintenance once established. Often viewed as a weed; beekeepers know better."},
    {"type":"bullet","text":"Native asters (Symphyotrichum spp.): Bloom alongside and after goldenrod, extending the fall flow into October. Excellent both as nectar and pollen sources. Low-growing species like heath aster work well in wildflower mixes."},
    {"type":"bullet","text":"Phacelia as a fall planting: A second seeding of phacelia in August will bloom in September–October in warmer zones. Where timing works, it's one of the best late-season additions."},
    {"type":"h2","text":"Designing the Acreage Layout"},
    {"type":"p","text":"You don't need to dedicate every acre to pollinator forage. A practical approach for a 10–50 acre operation:"},
    {"type":"bullet","text":"Permanent perennial base: White clover overseeded into your general pasture provides the main-flow foundation. This doubles as livestock forage and doesn't require dedicated acres."},
    {"type":"bullet","text":"Dedicated annual strips: Rotated 1–3 acre plots for high-value annuals like phacelia, buckwheat, and sweet clover. Move these strips around your acreage on a 2–3 year rotation to maintain soil health and prevent stand decline."},
    {"type":"bullet","text":"Permanent native perennial patches: Establish goldenrod and native asters in edges, fence lines, and rough areas that aren't productive pasture. These areas contribute fall forage without competing with other land uses."},
    {"type":"h2","text":"What to Avoid"},
    {"type":"bullet","text":"Alfalfa: High nectar producer but flower mechanism restricts honeybee access. Better suited to leafcutter bees and bumbles."},
    {"type":"bullet","text":"Most ornamental flowers: Selected for appearance, not nectar production. Often double-petaled varieties that physically block bee access."},
    {"type":"bullet","text":"Treated seed: Neonicotinoid-coated seed in pollinator plots undermines the entire effort. Verify seed is untreated if your supplier doesn't specify."},
    {"type":"cta","text":"→ Nature's Seed carries white clover, sweet clover, crimson clover, and wildflower mixes including pollinator-specific blends. Farm-direct, no fillers. Browse at naturesseed.com."},
  ]
},

# ── ARTICLE 11 ──────────────────────────────────────────────────────────────
{
  "title": "Carbon Capture on a Small Farm: What's Real, What's Hype",
  "category": "Niche Deep Dives",
  "read_time": "8 min read",
  "meta": "Soil carbon programs for farms under 500 acres explained — what the science actually says, what payments are realistic, and whether it's worth the paperwork.",
  "slug": "11-carbon-capture-small-farm",
  "body": [
    {"type":"p","text":"Every few months a new carbon farming program gets announced with promises of meaningful income for small landowners. Most of them deliver less than the headline suggests. A few are worth the time to understand."},
    {"type":"p","text":"If you manage fewer than 500 acres and are wondering whether soil carbon sequestration is a real opportunity or a distraction, this is the honest breakdown."},
    {"type":"h2","text":"What the Science Actually Says"},
    {"type":"p","text":"Soils can sequester carbon. This is not disputed. When organic matter builds in soil — through cover crops, reduced tillage, improved grazing management — a portion of that carbon becomes stable in the soil for years to decades. This is measurable."},
    {"type":"p","text":"What's more complicated is the rate, permanence, and additionality of sequestration at farm scale. Here's where the science gets honest:"},
    {"type":"bullet","text":"Rates vary enormously. Well-managed pasture under rotational grazing can sequester 0.5–1.5 metric tons of CO2 equivalent per acre per year. Converting tilled cropland to no-till can sequester 0.1–0.5 tons/acre/year. These are ranges from real research — not maximums you'll achieve every year."},
    {"type":"bullet","text":"Carbon already in the soil doesn't stay there forever. A drought year, a policy change that reverts you to tillage, or a change in ownership can release sequestered carbon. This is the permanence problem that markets are still working out."},
    {"type":"bullet","text":"Additionality is a bureaucratic term that matters practically: markets pay for carbon sequestered beyond what would have happened anyway. If you were already no-tilling, you may not qualify for credit for that practice — even though your soil has more carbon than a tilled field."},
    {"type":"h2","text":"The Market Reality for Operations Under 500 Acres"},
    {"type":"p","text":"Carbon markets have three cost structures that create a problem for small operations:"},
    {"type":"p","text":"Monitoring, reporting, and verification (MRV) costs. Documenting soil carbon requires baseline soil sampling, periodic re-sampling, and third-party verification. Soil sampling alone costs $20–50 per sample point, and a rigorous baseline requires multiple points per field per soil type. These fixed costs don't scale down with acreage — they eat a disproportionate share of small-operation payments."},
    {"type":"p","text":"Market carbon prices. Voluntary carbon markets have been paying $10–25 per metric ton of CO2 equivalent for agricultural soil carbon. At 0.5 tons/acre/year sequestration (a reasonable middle estimate), that's $5–12.50 per acre per year before MRV costs."},
    {"type":"p","text":"The math for 100 acres: gross revenue of $500–1,250/year, minus MRV costs that can easily run $2,000–5,000/year for a rigorous program. Many small operations lose money in year one and two and don't break even until later in a long-term contract."},
    {"type":"p","text":"The economic threshold for standalone carbon revenue is roughly 300–500 acres under current market conditions. Below that, direct payment programs are better suited to small operations."},
    {"type":"h2","text":"What Actually Works for Small Operations"},
    {"type":"h3","text":"USDA RCPP and EQIP Programs"},
    {"type":"p","text":"The USDA's Regional Conservation Partnership Program (RCPP) and Environmental Quality Incentives Program (EQIP) provide cost-share and direct payments for soil health practices — cover cropping, no-till, rotational grazing fencing and water infrastructure. These aren't framed as carbon payments, but the practices they support are exactly the ones that sequester carbon."},
    {"type":"p","text":"The advantage over carbon markets: no MRV costs, no contract lock-in beyond the agreement period, and payments are based on practice implementation rather than measured carbon outcomes. A 50-acre farm can receive meaningful cost-share for cover crop seed and fencing through EQIP that a carbon market contract would never make economical."},
    {"type":"h3","text":"Aggregated Carbon Programs"},
    {"type":"p","text":"Some programs aggregate small producers under a single verification umbrella, spreading MRV costs across many farms. Indigo Agriculture, Ecosystem Services Market Consortium (ESMC), and several state-level programs have used this model. The economics improve compared to individual contracts, but additionality requirements still limit eligibility for farms already practicing no-till or cover cropping."},
    {"type":"h2","text":"The Honest Framing"},
    {"type":"p","text":"For most small farms, soil carbon sequestration is a co-benefit of good land management — not a primary revenue source. The practices that build carbon also reduce input costs, improve drought resilience, and maintain long-term productivity. Those operational benefits are real and accessible at any scale."},
    {"type":"p","text":"Carbon payments may become more meaningful as market standards mature and MRV costs come down through remote sensing and AI-assisted monitoring. The trajectory is positive. But in 2025, the realistic carbon revenue for a 100-acre farm is a rounding error compared to the operational benefits of the underlying practices."},
    {"type":"p","text":"Do the practices. Pursue the USDA cost-share. Evaluate carbon program eligibility honestly. Don't make land management decisions based on speculative carbon payment projections."},
    {"type":"h2","text":"Where to Learn More"},
    {"type":"bullet","text":"NRCS EQIP: Contact your local NRCS office. Applications open in fall for the following year in most states."},
    {"type":"bullet","text":"Soil Carbon Initiative (sciencebasedtargets.org): Overview of corporate demand for soil carbon that drives private market programs."},
    {"type":"bullet","text":"Rodale Institute: Long-term research on organic and regenerative system carbon outcomes."},
    {"type":"cta","text":"→ Cover crops and managed grazing are the highest-ROI soil carbon practices — and they don't require a carbon contract to be worthwhile. Nature's Seed carries cover crop mixes and pasture seed designed for real operations. Browse at naturesseed.com."},
  ]
},

# ── ARTICLE 12 ──────────────────────────────────────────────────────────────
{
  "title": "Multi-Species Cover Crop Mixes Explained: Why Single Species Are Leaving Performance on the Table",
  "category": "Niche Deep Dives",
  "read_time": "7 min read",
  "meta": "Multi-species cover crop mixes outperform single-species plantings on nearly every metric. Here's the science and practical design guide for building effective mixes.",
  "slug": "12-multi-species-cover-crop-mixes",
  "body": [
    {"type":"p","text":"Straight winter rye is still the most commonly planted cover crop in the US. It's cheap, it's reliable, and it works. But if you've been planting single-species covers for a few years and wondering whether there's more to get out of them, the answer is yes — and the path there is mixing species."},
    {"type":"p","text":"Multi-species cover crop mixes consistently outperform single-species plantings across biomass production, weed suppression, nitrogen contribution, soil biology, and cash crop yield response. This isn't theoretical — it's been studied extensively on working farms across multiple soil types and climates."},
    {"type":"h2","text":"The Functional Diversity Principle"},
    {"type":"p","text":"Different plant species do different things in the soil. Root architectures vary — some go deep, some stay shallow. Some produce fine roots that feed bacteria, others produce coarser roots that support fungal networks. Some plants exude sugars that feed specific microbial communities. Some fix nitrogen. Some scavenge nutrients from deeper horizons and bring them to the surface."},
    {"type":"p","text":"A single species optimizes for one function. A well-designed mix optimizes for several simultaneously."},
    {"type":"p","text":"The principle is similar to a work crew: one person who's excellent at one task is good, but a small team with complementary skills accomplishes more. A five-species cover crop mix with a grass, two legumes, a brassica, and a broadleaf covers biological nitrogen fixation, biomass production, compaction-breaking, nutrient scavenging, and surface soil biology in a single planting."},
    {"type":"h2","text":"What the Research Shows"},
    {"type":"p","text":"Studies from multiple university extension programs comparing single-species covers to diverse mixes have consistently found:"},
    {"type":"bullet","text":"Biomass: 3–5 species mixes produce 20–40% more total above-ground biomass than single-species plantings at comparable seeding costs."},
    {"type":"bullet","text":"Nitrogen contribution: Mixed legume-grass plantings deliver more plant-available nitrogen to the following cash crop than monoculture legume stands, because the grass component protects legume biomass from premature breakdown."},
    {"type":"bullet","text":"Weed suppression: Multi-species mixes create more complete canopy coverage, reducing weed emergence by 30–60% compared to single-species covers."},
    {"type":"bullet","text":"Soil biology: Diverse plantings support measurably higher fungal-to-bacterial ratios and greater microbial diversity in the soil."},
    {"type":"h2","text":"The Four Functional Groups to Design Around"},
    {"type":"h3","text":"Grasses (biomass and organic matter)"},
    {"type":"p","text":"High carbon-to-nitrogen ratio. Slow decomposition. Provides long-lasting organic matter addition. Also the primary weed-suppression driver through sheer biomass. Core options: winter rye, oats, sorghum-sudan (warm season), winter wheat."},
    {"type":"h3","text":"Legumes (nitrogen fixation)"},
    {"type":"p","text":"Low carbon-to-nitrogen ratio. Decompose quickly and release nitrogen into soil. Target 30–50% of your mix by species, not by weight — legumes are small-seeded. Core options: hairy vetch, crimson clover, field peas, sunn hemp (warm season)."},
    {"type":"h3","text":"Brassicas (compaction and nutrient scavenging)"},
    {"type":"p","text":"Taproots physically penetrate compaction layers. Scavenge nitrate from depth. Biofumigation effect from glucosinolates (natural fungicide activity) can suppress some root pathogens. Core options: daikon radish, turnip, rapeseed, kale."},
    {"type":"h3","text":"Broadleaf non-legumes (biology and diversity)"},
    {"type":"p","text":"Often the most overlooked group. Plants like sunflower, buckwheat, phacelia, and flax bring root exudate diversity that feeds different soil microbial communities. Some provide pollinator benefit. Small amounts (1–3 lbs/acre) add biological diversity without driving cost."},
    {"type":"h2","text":"Designing a Mix: Practical Framework"},
    {"type":"p","text":"Start with your primary goal and build around it."},
    {"type":"bullet","text":"Primary goal: nitrogen for next crop — Lead with legumes (40–50% of seeding rate). Add a supporting grass to protect legume biomass. Example: hairy vetch 15 lbs + winter rye 40 lbs + crimson clover 8 lbs."},
    {"type":"bullet","text":"Primary goal: biomass / organic matter — Lead with grasses. Example: winter rye 50 lbs + oats 30 lbs + hairy vetch 12 lbs + daikon radish 4 lbs."},
    {"type":"bullet","text":"Primary goal: forage / grazing — Include palatable species. Example: oats 50 lbs + field peas 30 lbs + crimson clover 10 lbs + turnip 3 lbs."},
    {"type":"bullet","text":"Primary goal: soil biology recovery — Maximize diversity across all four groups. Small amounts of many species. Example: winter rye 30 lbs + hairy vetch 12 lbs + crimson clover 8 lbs + daikon radish 4 lbs + phacelia 2 lbs + sunflower 3 lbs."},
    {"type":"h2","text":"Seeding Rate Math for Mixes"},
    {"type":"p","text":"The key principle: when mixing species, reduce individual species rates by 30–50% from their monoculture rate. The competition between species in a dense mix means each doesn't need its full rate to achieve adequate stand."},
    {"type":"p","text":"A five-species mix targeting 80–90 lbs/acre total isn't unusual. The cost often comes in similar to a high-rate monoculture because you're reducing each individual rate, even though you're buying more SKUs."},
    {"type":"h2","text":"Common Mistakes in Mix Design"},
    {"type":"bullet","text":"Too many species without functional reason. Eight species can outperform five, but not reliably. Adding species for complexity rather than function dilutes focus."},
    {"type":"bullet","text":"Ignoring termination timing differences. Species in a mix don't all terminate at the same time or with the same method. Winter rye at anthesis and immature crimson clover have different response rates to rolling. Design for how you're going to kill it."},
    {"type":"bullet","text":"Forgetting inoculant on legumes. Every legume species has specific rhizobia requirements. A hairy vetch + crimson clover + field pea mix needs inoculant that covers all three, or separate inoculants for each."},
    {"type":"bullet","text":"Mixing incompatible species. Brassicas and legumes can compete heavily in wet years. Dominant grasses can shade out small-seeded legumes if rates aren't balanced. Test new mixes on a small acreage before scaling."},
    {"type":"cta","text":"→ Nature's Seed carries the individual species you need to build custom cover crop mixes — grasses, legumes, brassicas, and specialty broadleafs. Farm-direct, no fillers, with seed experts who can help you dial in a mix for your ground. Browse cover crop seed at naturesseed.com."},
  ]
},
]


def slugify(slug):
    return slug.replace("/", "-").replace(" ", "-").lower()


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for article in ARTICLES:
        doc = build_doc(article)
        filename = f"{article['slug']}.docx"
        path = os.path.join(OUTPUT_DIR, filename)
        doc.save(path)
        print(f"  Saved: {filename}")
    print(f"\nDone. {len(ARTICLES)} articles written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
