#!/usr/bin/env python3
"""Fava Bean — One-Page Retail Brief for CFO"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.colors import HexColor
import os

NS_GREEN      = HexColor('#1b4332')
NS_GREEN_MID  = HexColor('#2d6a4f')
NS_GREEN_LIGHT= HexColor('#d4edda')
NS_ORANGE     = HexColor('#C96A2E')
NS_GREY       = HexColor('#333333')
NS_GREY_LIGHT = HexColor('#f4f4f4')
NS_RULE       = HexColor('#cccccc')
WHITE         = colors.white

OUT = os.path.join(os.path.dirname(__file__), "fava_bean_one_pager.pdf")

doc = SimpleDocTemplate(
    OUT,
    pagesize=letter,
    leftMargin=0.6*inch, rightMargin=0.6*inch,
    topMargin=0.5*inch, bottomMargin=0.5*inch,
)

H1 = ParagraphStyle('H1', fontName='Helvetica-Bold', fontSize=13, textColor=WHITE, leading=17, spaceAfter=0)
H2 = ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=9.5, textColor=NS_GREEN, leading=13, spaceBefore=8, spaceAfter=3)
BODY = ParagraphStyle('BODY', fontName='Helvetica', fontSize=8.5, textColor=NS_GREY, leading=12, spaceAfter=2)
BOLD = ParagraphStyle('BOLD', fontName='Helvetica-Bold', fontSize=8.5, textColor=NS_GREY, leading=12, spaceAfter=2)
CAP = ParagraphStyle('CAP', fontName='Helvetica', fontSize=7.5, textColor=HexColor('#888888'), leading=11, spaceAfter=0)
TH = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, leading=11)
TD = ParagraphStyle('TD', fontName='Helvetica', fontSize=8, textColor=NS_GREY, leading=11)
TDB = ParagraphStyle('TDB', fontName='Helvetica-Bold', fontSize=8, textColor=NS_GREY, leading=11)

def bar(text):
    t = Table([[Paragraph(text, H1)]], colWidths=[7.3*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NS_GREEN),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
    ]))
    return t

def rule():
    return HRFlowable(width='100%', thickness=0.5, color=NS_RULE, spaceAfter=4, spaceBefore=4)

W = 7.3*inch

story = []

# ── HEADER ────────────────────────────────────────────────────────────────────
header = Table([[
    Paragraph('FAVA BEAN SEED — RETAIL OPPORTUNITY', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=14, textColor=WHITE, leading=18)),
    Paragraph('Nature\'s Seed · March 2026 · CONFIDENTIAL', ParagraphStyle('', fontName='Helvetica', fontSize=8.5, textColor=NS_GREEN_LIGHT, leading=12, alignment=2)),
]], colWidths=[4.5*inch, 2.8*inch])
header.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), NS_GREEN),
    ('TOPPADDING', (0,0), (-1,-1), 10), ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ('LEFTPADDING', (0,0), (-1,-1), 10), ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
]))
story.append(header)
story.append(Spacer(1, 8))

# ── KPI ROW ───────────────────────────────────────────────────────────────────
kpis = [
    ('18K–22K/mo', 'US searches\n"fava bean seeds"'),
    ('4×–12×', 'Retail premium\nover B2B bulk'),
    ('65–72%', 'Gross margin\nat retail'),
    ('$35K–$65K', 'Base case\nyr-1 revenue'),
    ('<$500', 'Setup cost\nall channels'),
]
kpi_cells = [[Paragraph(v, ParagraphStyle('', fontName='Helvetica-Bold', fontSize=13, textColor=NS_ORANGE, leading=16, alignment=1)),
              Paragraph(l, ParagraphStyle('', fontName='Helvetica', fontSize=7.5, textColor=NS_GREY, leading=10, alignment=1))]
             for v, l in kpis]
kpi_row = Table([[c[0] for c in kpi_cells], [c[1] for c in kpi_cells]],
                colWidths=[W/5]*5, rowHeights=[18, 20])
kpi_row.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), NS_GREY_LIGHT),
    ('TOPPADDING', (0,0), (4,0), 8), ('BOTTOMPADDING', (1,0), (-1,-1), 4),
    ('LEFTPADDING', (0,0), (-1,-1), 4), ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ('LINEAFTER', (0,0), (3,1), 0.5, NS_RULE),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
]))
story.append(kpi_row)
story.append(Spacer(1, 8))

# ── TWO-COLUMN LAYOUT ─────────────────────────────────────────────────────────
COL1 = 3.5*inch
COL2 = 3.65*inch
GAP  = 0.15*inch

# ── LEFT: USES + SEO ──────────────────────────────────────────────────────────
left = []

left.append(bar('RETAIL USE CASES'))
left.append(Spacer(1, 4))

left.append(Paragraph('Cover Crop (Primary Channel)', H2))
left.append(Paragraph(
    'Fava fixes <b>200–300 lbs nitrogen/acre</b> — highest of any common cover crop. '
    'Deep taproot breaks compaction. Cool-season (plant Oct–Feb, Mar–May). '
    'Identical buyer profile to existing NS pasture customers. '
    'Cover crop seed market: <b>$1.5B, 7% CAGR.</b>', BODY))

left.append(Paragraph('Home Garden / Vegetable (High-Margin)', H2))
left.append(Paragraph(
    'Fava bean is a cool-season vegetable with strong appeal to home gardeners. '
    '<b>>25% protein</b> — highest among common legumes. '
    '"Grow your own superfood" narrative. Peak demand: Jan–Apr. '
    'Small packets (2 oz) sell at $7.99 = <b>$63/lb equivalent.</b>', BODY))

left.append(Paragraph('Sprouting / Microgreens (Premium Niche)', H2))
left.append(Paragraph(
    'Fava sprouts and microgreens command <b>$9–$18/lb retail.</b> '
    'Growing traction on health/foodie channels. Low setup — same seed, different positioning and packaging.', BODY))

left.append(Paragraph('Mix Inclusion Opportunity', H2))
left.append(Paragraph(
    'Add fava to existing NS cover crop blends (nitrogen-fixer component). '
    'No separate listing needed — increases blend value and reduces overstock. '
    'Positioning: "Fava + Crimson Clover nitrogen-fixing blend" — <b>no competitor offers this.</b>', BODY))

left.append(Spacer(1, 6))
left.append(bar('SEO KEYWORD OPPORTUNITY'))
left.append(Spacer(1, 4))

kw_data = [
    [Paragraph('Keyword', TH), Paragraph('US Mo. Searches', TH), Paragraph('Competition', TH), Paragraph('CPC', TH)],
    [Paragraph('fava bean seeds', TD), Paragraph('18K–22K', TD), Paragraph('Medium', TD), Paragraph('$0.45', TD)],
    [Paragraph('fava bean seed for planting', TD), Paragraph('8K–12K', TD), Paragraph('Low', TD), Paragraph('$0.38', TD)],
    [Paragraph('fava bean cover crop', TD), Paragraph('5K–8K', TD), Paragraph('Low', TD), Paragraph('$0.35', TD)],
    [Paragraph('buy fava bean seed', TD), Paragraph('3K–5K', TD), Paragraph('Low', TD), Paragraph('$0.52', TD)],
    [Paragraph('fava bean sprouting seeds', TD), Paragraph('2K–4K', TD), Paragraph('Low', TD), Paragraph('$0.55', TD)],
]
kw_t = Table(kw_data, colWidths=[1.7*inch, 0.85*inch, 0.7*inch, 0.45*inch])
kw_t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), NS_GREEN_MID),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, NS_GREY_LIGHT]),
    ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ('LEFTPADDING', (0,0), (-1,-1), 5), ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ('GRID', (0,0), (-1,-1), 0.3, NS_RULE),
]))
left.append(kw_t)
left.append(Spacer(1, 3))
left.append(Paragraph('NS currently has ZERO impressions for fava terms → entire search demand is incremental.', CAP))

# ── RIGHT: AMAZON + WALMART ───────────────────────────────────────────────────
right = []

right.append(bar('AMAZON IMPLEMENTATION'))
right.append(Spacer(1, 4))

right.append(Paragraph('Competitive Pricing Benchmarks', H2))
comp_data = [
    [Paragraph('Competitor', TH), Paragraph('Small Packet', TH), Paragraph('1 lb', TH), Paragraph('5 lb', TH)],
    [Paragraph('Urban Farmer', TD), Paragraph('$3.75 (1oz)', TD), Paragraph('$12.75', TD), Paragraph('$42.00', TD)],
    [Paragraph('True Leaf Market', TD), Paragraph('$3.99–$5.99', TD), Paragraph('$8.50–$12', TD), Paragraph('$35–$50', TD)],
    [Paragraph('Outsidepride', TD), Paragraph('$5.99 (1oz)', TD), Paragraph('$9–$11', TD), Paragraph('$35–$45', TD)],
    [Paragraph('Baker Creek', TD), Paragraph('$4.25–$5.00', TD), Paragraph('$12–$15', TD), Paragraph('—', TD)],
    [Paragraph('<b>NS Target Price</b>', TDB), Paragraph('<b>$6.99–$8.99</b>', TDB), Paragraph('<b>$14.99</b>', TDB), Paragraph('<b>$44.99</b>', TDB)],
]
comp_t = Table(comp_data, colWidths=[1.15*inch, 0.95*inch, 0.75*inch, 0.8*inch])
comp_t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), NS_GREEN_MID),
    ('ROWBACKGROUNDS', (0,1), (-1,-2), [WHITE, NS_GREY_LIGHT]),
    ('BACKGROUND', (0,-1), (-1,-1), HexColor('#fff3e0')),
    ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ('LEFTPADDING', (0,0), (-1,-1), 4), ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ('GRID', (0,0), (-1,-1), 0.3, NS_RULE),
]))
right.append(comp_t)

right.append(Paragraph('Amazon Tactics', H2))
tactics = [
    '<b>Category:</b> "Vegetable Seeds" > "Bean Seeds" + "Cover Crop Seeds"',
    '<b>Title formula:</b> "Fava Bean Seeds for Planting – [Weight] – Non-GMO, Heirloom – Cover Crop & Garden – Nature\'s Seed"',
    '<b>Backend keywords:</b> broad bean seed, vicia faba, nitrogen fixing cover crop, cool season cover crop, fava sprouting seeds',
    '<b>PPC:</b> Target "fava bean seeds" + "broad bean seeds" exact. Budget $10–$15/day to launch. Expected ACoS: 25–35%.',
    '<b>Brand Registry:</b> Enroll immediately to protect listings and unlock A+ content.',
    '<b>FBA:</b> Use FBA for small packets (Prime eligibility critical for garden category).',
    '<b>Reviews:</b> Route naturesseed.com buyers to leave Amazon reviews via Vine or post-purchase email.',
]
for t in tactics:
    right.append(Paragraph(f'• {t}', BODY))

right.append(Spacer(1, 5))
right.append(bar('WALMART IMPLEMENTATION'))
right.append(Spacer(1, 4))

right.append(Paragraph('Current Walmart Landscape', H2))
right.append(Paragraph(
    '<b>Very few fava bean listings on Walmart.com</b> — significant white space vs Amazon. '
    'NS already has a Walmart Marketplace account → <b>zero incremental setup cost.</b> '
    'Walmart referral fee: 0% first 90 days, then ~8% avg (vs Amazon\'s 15%). '
    'Higher margin channel than Amazon.', BODY))

right.append(Paragraph('Walmart Listing Strategy', H2))
wmt_tactics = [
    '<b>Start with 2 SKUs:</b> 1 lb cover crop ($14.99) + 5 lb cover crop ($44.99). Garden packets underperform on Walmart vs Amazon.',
    '<b>Category:</b> "Garden Center > Seeds > Vegetable Seeds"',
    '<b>Walmart SEO:</b> Front-load primary keyword in item title. "Fava Bean Seeds – 1 lb – Cover Crop & Garden – Non-GMO, Heirloom"',
    '<b>Fulfillment:</b> Use WFS (Walmart Fulfillment Services) if volume warrants; otherwise ship from NS warehouse.',
    '<b>Pricing:</b> Match or beat Amazon pricing to avoid Walmart buy-box suppression (Walmart price-parity enforces lowest price).',
    '<b>Timeline:</b> Listing live within 1–2 business days via existing Seller Center account.',
]
for t in wmt_tactics:
    right.append(Paragraph(f'• {t}', BODY))

right.append(Spacer(1, 5))
right.append(bar('LAUNCH SEQUENCE'))
right.append(Spacer(1, 4))

seq_data = [
    [Paragraph('Week', TH), Paragraph('Action', TH), Paragraph('Channel', TH)],
    [Paragraph('1', TD), Paragraph('Germination test + photography + copywriting', TD), Paragraph('Prep', TD)],
    [Paragraph('1', TD), Paragraph('Create 3 WC SKUs: 2oz ($7.99), 1lb ($14.99), 5lb ($44.99)', TD), Paragraph('naturesseed.com', TD)],
    [Paragraph('2', TD), Paragraph('Mirror listings on Amazon (FBA shipment)', TD), Paragraph('Amazon', TD)],
    [Paragraph('2', TD), Paragraph('Create 2 Walmart listings: 1lb + 5lb', TD), Paragraph('Walmart', TD)],
    [Paragraph('3', TD), Paragraph('Launch Amazon PPC ($10/day) + Klaviyo email to cover crop segment', TD), Paragraph('Paid + Email', TD)],
    [Paragraph('4+', TD), Paragraph('Add sprouting SKU, bundle with crimson clover mix', TD), Paragraph('All', TD)],
]
seq_t = Table(seq_data, colWidths=[0.4*inch, 2.35*inch, 0.9*inch])
seq_t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), NS_GREEN_MID),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, NS_GREY_LIGHT]),
    ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ('LEFTPADDING', (0,0), (-1,-1), 4), ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ('GRID', (0,0), (-1,-1), 0.3, NS_RULE),
    ('ALIGN', (0,0), (0,-1), 'CENTER'),
]))
right.append(seq_t)

# ── ASSEMBLE TWO COLUMNS ──────────────────────────────────────────────────────
from reportlab.platypus import KeepInFrame

left_frame  = KeepInFrame(COL1, 9.5*inch, left,  mode='shrink')
right_frame = KeepInFrame(COL2, 9.5*inch, right, mode='shrink')

two_col = Table([[left_frame, Spacer(GAP, 1), right_frame]], colWidths=[COL1, GAP, COL2])
two_col.setStyle(TableStyle([
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('TOPPADDING', (0,0), (-1,-1), 0),
    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ('LEFTPADDING', (0,0), (-1,-1), 0),
    ('RIGHTPADDING', (0,0), (-1,-1), 0),
]))
story.append(two_col)

doc.build(story)
print(f'One-pager created: {OUT}')
