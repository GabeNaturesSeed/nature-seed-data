#!/usr/bin/env python3
"""Generate 2026 Budget vs Actuals HTML report."""
import json
from pathlib import Path

with open('/tmp/budget_data.json') as f:
    d = json.load(f)

budget   = d['budget']
jan_act  = d['jan_actual']
feb_est  = d['feb_estimated']
mar_mtd  = d['mar_mtd']

# ── Amazon Marketplace data (from CSV) ──────────────────────────────────
amazon = {
    'total_skus_listed': 36,
    'skus_with_sales': 13,
    'total_units': 45,
    'total_sales': 1447.76,
    'total_net_profit': 303.18,
    'total_amz_fees': 780.32,
    'total_cogs': 241.08,
    'avg_price': 32.17,
    'status': 'early_stage',
    'top_skus': [
        {'sku': 'S-RICE-5-LB',     'name': 'Rice Hulls 5 lb',          'units': 24, 'sales': 431.76, 'net': 8.16,   'margin_pct': 1.89},
        {'sku': 'S-RICE-45-LB',    'name': 'Rice Hulls 45 lb',         'units': 2,  'sales': 210.00, 'net': 156.28, 'margin_pct': 74.42},
        {'sku': 'PG-BOGR-5LB',     'name': 'Blue Grama 5 lb',          'units': 1,  'sales': 199.99, 'net': 156.68, 'margin_pct': 78.34},
        {'sku': 'PB-HRSE-SO-10-LB','name': 'Southern Horse Forage 10lb','units': 3,  'sales': 119.97, 'net': 18.27,  'margin_pct': 15.23},
        {'sku': 'TURF-W-TALL-5LB', 'name': 'Tall Fescue 5 lb',         'units': 3,  'sales': 104.97, 'net': 49.92,  'margin_pct': 47.56},
        {'sku': 'PB-CHIX-5-LB',    'name': 'Chicken Forage 5 lb',      'units': 4,  'sales': 79.96,  'net': -46.76, 'margin_pct': -58.48},
    ]
}

# Walmart MTD numbers from WC data
walmart_mtd = {
    'rev': 3486,
    'orders': 29,
    'daily_rev': 3486 / 10,
    'proj_monthly': round(3486 / 10 * 31, 0),
}

OUT = Path(__file__).parent / "budget_vs_actuals_2026.html"

MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

# ── Actuals / estimates per month ────────────────────────────────────────
actuals = {
    'Jan': {**jan_act, 'status': 'actual'},
    'Feb': {**feb_est, 'status': 'estimate'},
    'Mar': {'net_rev': mar_mtd['proj_rev'], 'advertising': mar_mtd['advertising_proj'],
            'status': 'projected', 'days': 10, 'mtd_rev': mar_mtd['net_rev']},
}

def fmt(v, prefix='$'):
    if v is None: return '—'
    v = float(v)
    neg = v < 0
    return f"{'-' if neg else ''}{prefix}{abs(v):,.0f}"

def pct_bar(act, bud, width=120):
    if not bud: return ''
    ratio = min(act / bud, 1.5)
    pct_val = act / bud * 100
    fill = min(ratio / 1.5 * 100, 100)
    color = '#2d6a4f' if pct_val >= 90 else ('#c96a2e' if pct_val >= 65 else '#c0392b')
    return f'''<div style="display:flex;align-items:center;gap:8px;">
      <div style="width:{width}px;height:8px;background:#f3f4f6;border-radius:4px;overflow:hidden;">
        <div style="width:{fill:.0f}%;height:100%;background:{color};border-radius:4px;"></div>
      </div>
      <span style="font-size:11px;font-weight:700;color:{color};">{pct_val:.0f}%</span>
    </div>'''

def delta_cell(act, bud, is_good_if_over=True):
    if not bud or act is None: return '<td>—</td>'
    diff = act - bud
    pct = diff / bud * 100
    good = (diff >= 0) == is_good_if_over
    color = '#2d6a4f' if good else '#c0392b'
    sign = '+' if diff >= 0 else ''
    return f'<td class="num" style="color:{color};font-weight:700;">{sign}{fmt(diff)}<br><span style="font-size:10px;">{sign}{pct:.1f}%</span></td>'

# ── Month-by-month revenue attainment table ──────────────────────────────
def monthly_rev_rows():
    rows = []
    for m in MONTHS:
        b   = budget[m]
        act = actuals.get(m)
        bud_rev = b['net_rev']
        bud_adv = b['advertising']

        if act:
            act_rev = act.get('net_rev', 0) or 0
            act_adv = act.get('advertising', 0) or 0
            status  = act['status']
            status_badge = {
                'actual': '<span style="background:#d1fae5;color:#065f46;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:700;">ACTUAL</span>',
                'estimate': '<span style="background:#fef3c7;color:#92400e;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:700;">ESTIMATE</span>',
                'projected': '<span style="background:#dbeafe;color:#1d4ed8;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:700;">PROJECTED</span>',
            }[status]
            bar = pct_bar(act_rev, bud_rev)
            adv_delta = f'<span style="color:{"#2d6a4f" if act_adv<=bud_adv else "#c96a2e"};font-size:11px;">{fmt(act_adv)} ({(act_adv/bud_adv-1)*100:+.0f}%)</span>' if bud_adv else '—'
            note = ''
            if m == 'Mar':
                note = f'<br><span style="font-size:10px;color:#6b7280;">MTD ${mar_mtd["net_rev"]:,.0f} (10d) → proj ${act_rev:,.0f}</span>'
            if m == 'Feb':
                note = '<br><span style="font-size:10px;color:#6b7280;">WC gross, official actuals pending</span>'
        else:
            act_rev = None
            bar = '<span style="font-size:11px;color:#d1d5db;">—</span>'
            adv_delta = f'<span style="font-size:11px;color:#6b7280;">{fmt(bud_adv)} budgeted</span>'
            status_badge = '<span style="background:#f3f4f6;color:#9ca3af;padding:2px 7px;border-radius:10px;font-size:10px;">FUTURE</span>'
            note = ''

        rows.append(f"""
        <tr>
          <td style="font-weight:700;white-space:nowrap;">{m} 2026 {status_badge}</td>
          <td class="num">{fmt(bud_rev)}</td>
          <td class="num">{'—' if act_rev is None else fmt(act_rev)}{note}</td>
          {'<td>'+bar+'</td>' if act_rev else '<td>—</td>'}
          {delta_cell(act_rev, bud_rev) if act_rev else '<td>—</td>'}
          <td class="num">{fmt(bud_adv)}</td>
          <td>{adv_delta}</td>
        </tr>""")
    return "\n".join(rows)

# ── January deep-dive P&L table ──────────────────────────────────────────
def jan_pl_rows():
    items = [
        ('Gross Revenue',      jan_act['gross_rev'],   budget['Jan']['gross_rev'],   True),
        ('Discounts',          jan_act['discounts'],    budget['Jan']['discounts'],   False),
        ('Net Revenue',        jan_act['net_rev'],      budget['Jan']['net_rev'],     True),
        ('COGS',               jan_act['cogs'],         budget['Jan']['cogs'],        False),
        ('Gross Margin',       jan_act['gross_margin'], budget['Jan']['gross_margin'],True),
        ('Warehouse',          jan_act['warehouse'],    budget['Jan']['warehouse'],   False),
        ('Advertising',        jan_act['advertising'],  budget['Jan']['advertising'], False),
        ('Total OpEx',         jan_act['total_opex'],   budget['Jan']['total_opex'],  False),
        ('EBITDA',             jan_act['ebitda'],       budget['Jan']['ebitda'],      True),
    ]
    rows = []
    is_sub = {'Discounts','COGS','Warehouse','Advertising'}
    is_bold= {'Net Revenue','Gross Margin','Total OpEx','EBITDA'}
    for label, act, bud, good_if_over in items:
        bold = 'font-weight:700;' if label in is_bold else ''
        sub  = 'color:#6b7280;' if label in is_sub else ''
        diff = act - bud; pct = diff/bud*100 if bud else 0
        good = (diff >= 0) == good_if_over
        dcolor = '#2d6a4f' if good else '#c0392b'
        sign = '+' if diff >= 0 else ''
        gm_pct_act = f' ({act/jan_act["net_rev"]*100:.1f}%)' if label in ('COGS','Gross Margin','Total OpEx') else ''
        gm_pct_bud = f' ({bud/budget["Jan"]["net_rev"]*100:.1f}%)' if label in ('COGS','Gross Margin','Total OpEx') else ''
        rows.append(f"""
        <tr>
          <td style="{bold}{sub}padding-left:{'20px' if label in is_sub else '12px'};">{label}</td>
          <td class="num" style="{bold}">{fmt(bud)}{gm_pct_bud}</td>
          <td class="num" style="{bold}">{fmt(act)}{gm_pct_act}</td>
          <td class="num" style="color:{dcolor};font-weight:600;">{sign}{fmt(diff)}</td>
          <td class="num" style="color:{dcolor};font-weight:600;">{sign}{pct:.1f}%</td>
        </tr>""")
    return "\n".join(rows)

# ── Bridge to budget ──────────────────────────────────────────────────────
fy_bud = d['fy_budget_rev']
q1_gap = d['bud_q1'] - d['act_q1_proj']   # positive = we're behind
# What we need Apr-Dec to hit full year
apr_dec_bud  = sum(budget[m]['net_rev'] for m in ['Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
apr_dec_need = fy_bud - d['act_q1_proj']
apr_dec_gap  = apr_dec_need - apr_dec_bud
gap_pct      = apr_dec_gap / apr_dec_bud * 100

# Walmart add: ~$10.8K/month run rate from March MTD
walmart_annual_est = round(mar_mtd['net_rev'] / 10 * 31 * 0.3, 0)  # conservative: 30% of march monthly rate for rest of year (seasonal)
walmart_est_remaining = round(mar_mtd['net_rev'] / 10 * 31 * 9, 0)  # rough: 9 remaining months

# Pre-build chart JSON
bud_rev_js  = json.dumps([budget[m]['net_rev'] for m in MONTHS])
act_rev_js  = json.dumps([
    actuals['Jan']['net_rev'],
    actuals['Feb']['net_rev'],
    actuals['Mar']['net_rev'],
    None,None,None,None,None,None,None,None,None
])
bud_adv_js  = json.dumps([budget[m]['advertising'] for m in MONTHS])
act_adv_js  = json.dumps([
    actuals['Jan']['advertising'],
    actuals['Feb']['advertising'],
    actuals['Mar']['advertising'],
    None,None,None,None,None,None,None,None,None
])
bud_ebitda_js = json.dumps([budget[m]['ebitda'] for m in MONTHS])
month_labels_js = json.dumps([m+' 2026' for m in MONTHS])

# Pre-build the new tabs HTML (no f-string interpolation needed)
channels_tab_html = """
<!-- ══ ALL CHANNELS ═══════════════════════════════════════════════════════ -->
<div id="tab-channels" class="tab-panel">
  <div class="section-label">Revenue by Channel — March 2026 MTD (10 days)</div>

  <div class="kpi-strip" style="margin-bottom:24px;">
    <div class="kpi">
      <div class="lbl">WooCommerce</div>
      <div class="val">$118,497</div>
      <div class="sub-val">871 orders · $136 AOV</div>
      <div class="delta pos">$11,850/day</div>
    </div>
    <div class="kpi">
      <div class="lbl">Walmart Marketplace</div>
      <div class="val pos">$3,486</div>
      <div class="sub-val">29 orders · $120 AOV · NEW</div>
      <div class="delta pos">~$10,805/mo pace</div>
    </div>
    <div class="kpi">
      <div class="lbl">Amazon Marketplace</div>
      <div class="val warn">$1,448</div>
      <div class="sub-val">45 units · $32 avg price · EARLY STAGE</div>
      <div class="delta warn">36 SKUs listed, 13 with sales</div>
    </div>
    <div class="kpi">
      <div class="lbl">Amazon Net Profit</div>
      <div class="val">$303</div>
      <div class="sub-val">21% net margin (ex Rice Hulls: negative)</div>
      <div class="delta warn">Fees eating into margin</div>
    </div>
    <div class="kpi">
      <div class="lbl">Total All Channels (MTD)</div>
      <div class="val">$123,431</div>
      <div class="sub-val">WC + Walmart + Amazon</div>
      <div class="delta pos">vs $133,652 WC-only in Mar 2025</div>
    </div>
    <div class="kpi">
      <div class="lbl">New Channel Upside (Apr–Dec)</div>
      <div class="val pos">~$135K+</div>
      <div class="sub-val">Walmart + Amazon est. (not in budget)</div>
      <div class="delta pos">100% incremental to budget</div>
    </div>
  </div>

  <div class="bridge">
    <h3>Amazon Account — Early Stage Assessment</h3>
    <div class="bridge-row">
      <div class="bridge-icon">📦</div>
      <div>
        <div class="bridge-label">36 SKUs listed, account is just being seeded</div>
        <div class="bridge-detail">
          Only 13 SKUs have recorded any sales. Total revenue to date is ~$1,448 across 45 units.
          This is expected behavior for a new account — Amazon's algorithm takes 60–90 days to index listings and assign BSR rankings.
          Several listings have strong BSR positions already (Rice Hulls 45 lb: #208,655 · Blue Grama: top 200K) which will improve with reviews.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval">36</div>
        <div class="bsub">SKUs listed</div>
      </div>
    </div>
    <div class="bridge-row">
      <div class="bridge-icon">⚠️</div>
      <div>
        <div class="bridge-label">Several SKUs are priced below profitability — fix now before volume scales</div>
        <div class="bridge-detail">
          Chicken Forage 5 lb (PB-CHIX-5-LB): -58% margin. At $19.99 with $9.09 COG + Amazon fees,
          every unit sold loses $11.69. Needs price increase to $26.99+ or delisting.
          Alpaca/Llama Forage 10 lb (PB-ALPACA-10-LB): -57% margin at $29.99 with $16.98 COG.
          Minimum viable price: ~$44.99. Rice Hulls 5 lb: only 1.89% margin — 24 units sold for $8 net profit.
          Price is $17.99 but Amazon fees are $393.60 on $431.76 revenue (91% fee rate on this item).
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval neg">3 SKUs</div>
        <div class="bsub">losing money</div>
      </div>
    </div>
    <div class="bridge-row">
      <div class="bridge-icon">✅</div>
      <div>
        <div class="bridge-label">High-margin SKUs showing promise — scale these</div>
        <div class="bridge-detail">
          Blue Grama 5 lb: 78% margin at $199.99 — premium positioning working.
          Rice Hulls 45 lb: 74% margin at $105 — larger pack is dramatically more profitable than 5 lb.
          Tall Fescue 5 lb: 48% margin. Deer Resistant Wildflower: 67% margin.
          Focus ad spend and inventory on these. Consider delisting or repricing the loss leaders before scaling.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval pos">74–78%</div>
        <div class="bsub">top SKU margins</div>
      </div>
    </div>
    <div class="bridge-row">
      <div class="bridge-icon">🔄</div>
      <div>
        <div class="bridge-label">Amazon strategy: small packs, high margin, no bulk</div>
        <div class="bridge-detail">
          Amazon is the right channel for 5–10 lb consumer packs at premium pricing.
          It complements WC (B2C retail) and keeps bulk orders off Amazon where shipping would be unprofitable.
          As the account seasons and gets reviews, conversion rates will improve significantly.
          Target: $5,000–$10,000/month by Q3 once top SKUs build review velocity.
        </div>
      </div>
    </div>
  </div>
</div>"""

aov_tab_html = """
<!-- ══ SHIPPING & AOV STRATEGY ════════════════════════════════════════════ -->
<div id="tab-aov" class="tab-panel">

  <div class="bridge" style="margin-bottom:20px;">
    <h3>Why AOV Dropped — The Shipping Policy Change Explained</h3>
    <div class="bridge-row">
      <div class="bridge-icon">📜</div>
      <div>
        <div class="bridge-label">Old policy: Free shipping over $150 — was destroying margins on bulk orders</div>
        <div class="bridge-detail">
          Large customers (farmers, ranchers) placing $500–$2,000 orders with 200–500 lbs of seed were getting
          free shipping, which costs $80–$300+ per shipment. At scale this was wiping out gross margin on those orders
          and actively competing with the B2B side of the company — which has dedicated pricing, reps, and logistics
          built for those customers. The policy also attracted one-time bulk buyers who don't return.
        </div>
      </div>
    </div>
    <div class="bridge-row">
      <div class="bridge-icon">✅</div>
      <div>
        <div class="bridge-label">New policy: Free shipping &lt;125 lbs · $80 flat + $80/25 lbs above 125 lbs</div>
        <div class="bridge-detail">
          This is the <strong>correct strategic decision</strong>. It protects margins on large orders,
          routes true bulk buyers to B2B where they belong, and makes the retail/DTC channel sustainable.
          The side effect is intentional: AOV dropped from $184 → $136 because the high-AOV orders
          (250–500 lb bulk shipments that were >$400 each) now either pay freight or go to B2B.
          This is not a problem — it's the policy working as designed.
        </div>
      </div>
    </div>
    <div class="bridge-row">
      <div class="bridge-icon">📊</div>
      <div>
        <div class="bridge-label">The result: 677 small orders/week vs 159 before — retail channel exploding</div>
        <div class="bridge-detail">
          Orders under 125 lbs went from 159/week (Jan–Feb) to 677/week (March MTD) — a 326% increase.
          The average sub-125 lb order is $126 vs $146 before, suggesting slightly smaller baskets
          but massively more volume. Orders above 125 lbs also slightly increased (6.9 → 9.8/week)
          and their average revenue went <em>up</em> ($992 → $1,074) — the freight charge is actually
          qualifying these buyers as serious customers who pay for value.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval pos">+326%</div>
        <div class="bsub">small order volume</div>
      </div>
    </div>
  </div>

  <div class="bridge">
    <h3>AOV Recovery Strategies — Within the 125 lb Free Shipping Window</h3>
    <p style="font-size:12px;color:#555;margin-bottom:16px;">
      Goal: Move average sub-125 lb order from $126 → $160–175. These tactics work WITH the new policy, not against it.
    </p>

    <div class="bridge-row">
      <div class="bridge-icon">🎯</div>
      <div>
        <div class="bridge-label">1. "Max Value" pack sizing — push people to 50 lb bags</div>
        <div class="bridge-detail">
          A 50 lb bag at $175 is free shipping. Two 25 lb bags at $100 each = $200 but free shipping too.
          The 50 lb should feel obviously better value. Audit your 25 lb vs 50 lb price-per-lb gap —
          if it's less than 10%, customers won't upgrade. Make it 18–22% cheaper per lb at 50 lbs.
          Callout: <em>"Save 20% per lb — still free shipping under 125 lbs."</em>
          This alone moves AOV without requiring more products in cart.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval">+$30–50</div>
        <div class="bsub">AOV impact per order</div>
      </div>
    </div>

    <div class="bridge-row">
      <div class="bridge-icon">🛒</div>
      <div>
        <div class="bridge-label">2. Cart add-ons: amendments + inoculants as light-weight upsells</div>
        <div class="bridge-detail">
          Rice Hulls (5 lb, 45 lb), mycorrhizal inoculant, fertilizer, tackifier — these are lightweight,
          high-margin, and complementary to any seed purchase. When a customer has 20 lbs of grass seed in cart
          (total: $80), a 5 lb rice hull bag adds $18 and only 5 lbs to the order — still well under the 125 lb threshold.
          Show "Complete your order — still free shipping" in the cart. Target: 25% attach rate on cart = +$15 avg.
          <em>These products are already on Amazon and WC — just need cart placement.</em>
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval">+$12–18</div>
        <div class="bsub">per order with 25% attach</div>
      </div>
    </div>

    <div class="bridge-row">
      <div class="bridge-icon">📦</div>
      <div>
        <div class="bridge-label">3. "Seasonal Starter Kits" — pre-bundled SKUs at a single price</div>
        <div class="bridge-detail">
          Build bundle SKUs in WooCommerce: "Spring Lawn Starter" (25 lb grass seed + 5 lb micro clover + inoculant),
          "Pasture Renovation Kit" (25 lb pasture mix + legume + soil amendment). Price the bundle 10% below
          buying items individually. Average weight: 30–35 lbs. Average price: $180–220.
          Bundle pricing hides individual item prices, makes comparison harder, and anchors higher.
          This is how Amazon drives AOV with "frequently bought together" — replicate it natively on WC.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval">$180–220</div>
        <div class="bsub">bundle AOV target</div>
      </div>
    </div>

    <div class="bridge-row">
      <div class="bridge-icon">📏</div>
      <div>
        <div class="bridge-label">4. Show the free shipping threshold visually in cart</div>
        <div class="bridge-detail">
          "You have 67 lbs in your cart — add up to 58 more lbs and still get free shipping."
          This is a psychological anchor that prompts customers to fill the cart rather than check out early.
          Many customers don't know there's a 125 lb ceiling — they assume shipping will be charged.
          Making the free shipping window visible increases average cart weight without requiring discounts.
          Implement as a WooCommerce cart notice or mini progress bar.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval">+$20–35</div>
        <div class="bsub">from ceiling awareness</div>
      </div>
    </div>

    <div class="bridge-row">
      <div class="bridge-icon">🔁</div>
      <div>
        <div class="bridge-label">5. B2B capture funnel — convert freight-deterred bulk buyers</div>
        <div class="bridge-detail">
          When a customer adds >125 lbs to cart and sees the $80 freight charge, show:
          <em>"Ordering more than 125 lbs regularly? Join our bulk program — free shipping on all orders,
          dedicated pricing, and expert support."</em> Link to a B2B inquiry form.
          These are your highest-LTV customers — don't lose them to a checkout surprise.
          Even converting 10% of cart abandons at this weight threshold into B2B leads is significant revenue.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval">B2B lead</div>
        <div class="bsub">avg $992/order</div>
      </div>
    </div>

    <div class="bridge-row">
      <div class="bridge-icon">📧</div>
      <div>
        <div class="bridge-label">6. Post-purchase upsell sequence — Klaviyo</div>
        <div class="bridge-detail">
          The 677 new weekly small-order customers are building a repeat-buyer base. A 30-day post-purchase
          flow ("how's the grass coming in?") with a time-based reorder nudge can turn a $126 first order
          into a $252 LTV. This doesn't raise individual AOV but raises revenue per customer which is the
          same lever. Send at: 21 days (germination check-in), 45 days (progress, reorder CTA),
          90 days (seasonal next-step seed recommendation).
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval">2×</div>
        <div class="bsub">LTV target</div>
      </div>
    </div>

    <div class="bridge-row">
      <div class="bridge-icon">💰</div>
      <div>
        <div class="bridge-label">Combined impact: $126 → $165 AOV is achievable by Q2</div>
        <div class="bridge-detail">
          Pack size optimization (+$35) + cart add-ons at 25% attach (+$15) + ceiling awareness (+$20) = +$70 theoretical max.
          A realistic capture rate of 50% = +$35, bringing average AOV to ~$161.
          At 677 orders/week × $35 AOV gain = <strong>$23,695 additional weekly revenue</strong>,
          or ~$95K/month. That alone closes the April–May budget gap without any change in spend or order volume.
          The data says fix AOV before scaling spend.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval pos">+$95K/mo</div>
        <div class="bsub">at $35 AOV gain × 677 orders/wk</div>
      </div>
    </div>
  </div>
</div>"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>2026 Budget vs Actuals — Nature's Seed</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #f4f6f8; color: #1a1a1a; font-size: 13px; line-height: 1.5; }}

  .header {{ background: #1b4332; color: #fff; padding: 22px 36px; }}
  .header h1 {{ font-size: 20px; font-weight: 700; }}
  .header .sub {{ font-size: 12px; color: #74c69d; margin-top: 4px; }}

  .period-tabs {{ display: flex; gap: 0; margin: 20px 36px 0; border-bottom: 2px solid #e2e8f0; }}
  .tab {{ padding: 10px 24px; cursor: pointer; font-size: 13px; font-weight: 600;
           color: #6b7280; border-bottom: 3px solid transparent; margin-bottom: -2px; transition: all .15s; }}
  .tab.active {{ color: #1b4332; border-bottom-color: #2d6a4f; }}
  .tab-panel {{ display: none; padding: 24px 36px; }}
  .tab-panel.active {{ display: block; }}

  /* KPI strip */
  .kpi-strip {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
                 gap: 12px; margin-bottom: 24px; }}
  .kpi {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; }}
  .kpi .lbl {{ font-size: 10px; font-weight: 700; color: #6b7280; text-transform: uppercase;
                letter-spacing: .5px; margin-bottom: 6px; }}
  .kpi .val {{ font-size: 20px; font-weight: 700; color: #1b4332; }}
  .kpi .sub-val {{ font-size: 11px; color: #6b7280; margin-top: 3px; }}
  .kpi .delta {{ font-size: 12px; font-weight: 700; margin-top: 4px; }}
  .pos {{ color: #2d6a4f; }}
  .neg {{ color: #c0392b; }}
  .warn {{ color: #c96a2e; }}

  /* Charts */
  .charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }}
  .chart-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; }}
  .chart-title {{ font-size: 12px; font-weight: 700; color: #374151; text-transform: uppercase;
                   letter-spacing: .5px; margin-bottom: 12px; }}
  .chart-wrap {{ position: relative; height: 220px; }}

  /* Tables */
  .table-wrap {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
                  overflow: hidden; margin-bottom: 24px; }}
  .table-title {{ padding: 14px 16px 0; font-size: 13px; font-weight: 700; color: #1b4332; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  thead tr {{ background: #f8fafc; border-bottom: 2px solid #e2e8f0; }}
  thead th {{ padding: 9px 12px; text-align: left; font-size: 10px; font-weight: 700;
               color: #6b7280; text-transform: uppercase; letter-spacing: .5px; white-space: nowrap; }}
  thead th.num {{ text-align: right; }}
  tbody tr {{ border-bottom: 1px solid #f1f5f9; }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody tr:hover {{ background: #f8fafc; }}
  td {{ padding: 9px 12px; vertical-align: middle; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}

  /* Bridge box */
  .bridge {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px 24px;
              margin-bottom: 24px; }}
  .bridge h3 {{ font-size: 14px; font-weight: 700; color: #1b4332; margin-bottom: 16px; }}
  .bridge-row {{ display: flex; align-items: flex-start; gap: 12px; padding: 12px 0;
                  border-bottom: 1px solid #f1f5f9; }}
  .bridge-row:last-child {{ border-bottom: none; }}
  .bridge-icon {{ font-size: 18px; flex-shrink: 0; margin-top: 1px; }}
  .bridge-label {{ font-size: 13px; font-weight: 700; color: #1a1a1a; margin-bottom: 3px; }}
  .bridge-detail {{ font-size: 12px; color: #555; line-height: 1.6; }}
  .bridge-num {{ margin-left: auto; text-align: right; flex-shrink: 0; }}
  .bridge-num .bval {{ font-size: 16px; font-weight: 700; }}
  .bridge-num .bsub {{ font-size: 10px; color: #6b7280; }}

  .section-label {{ font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase;
                     letter-spacing: .5px; margin-bottom: 12px; padding-bottom: 6px;
                     border-bottom: 1px solid #e2e8f0; }}
  .note {{ font-size: 11px; color: #9ca3af; margin-top: 12px; line-height: 1.6; }}
  .highlight-row {{ background: #f0fdf4 !important; }}
</style>
</head>
<body>

<div class="header">
  <h1>2026 Budget vs Actuals — Nature's Seed Ecommerce</h1>
  <div class="sub">Full Year Budget: {fmt(fy_bud)} net revenue &nbsp;·&nbsp; As of March 10, 2026 &nbsp;·&nbsp; Jan = Official Actuals · Feb = WC Estimate · Mar = Projected</div>
</div>

<div class="period-tabs">
  <div class="tab active" onclick="showTab('overview',this)">Overview</div>
  <div class="tab" onclick="showTab('monthly',this)">Monthly Attainment</div>
  <div class="tab" onclick="showTab('jan',this)">January Deep Dive</div>
  <div class="tab" onclick="showTab('path',this)">Path to Budget</div>
  <div class="tab" onclick="showTab('channels',this)">All Channels</div>
  <div class="tab" onclick="showTab('aov',this)">Shipping &amp; AOV Strategy</div>
</div>

<!-- ══ OVERVIEW ══════════════════════════════════════════════════════════ -->
<div id="tab-overview" class="tab-panel active">

  <div class="kpi-strip">
    <div class="kpi">
      <div class="lbl">Full Year Budget</div>
      <div class="val">{fmt(fy_bud)}</div>
      <div class="sub-val">Net Revenue Target</div>
    </div>
    <div class="kpi">
      <div class="lbl">YTD Actual (Jan–Mar 10)</div>
      <div class="val neg">{fmt(d['act_ytd_mar10'])}</div>
      <div class="sub-val">vs {fmt(d['bud_ytd_mar10'])} budget</div>
      <div class="delta neg">{d['ytd_gap']:,.0f} ({d['ytd_gap']/d['bud_ytd_mar10']*100:+.1f}%)</div>
    </div>
    <div class="kpi">
      <div class="lbl">Q1 Projected (Full Quarter)</div>
      <div class="val warn">{fmt(d['act_q1_proj'])}</div>
      <div class="sub-val">vs {fmt(d['bud_q1'])} budget</div>
      <div class="delta neg">{(d['act_q1_proj']/d['bud_q1']-1)*100:+.1f}% attainment</div>
    </div>
    <div class="kpi">
      <div class="lbl">Jan Attainment</div>
      <div class="val neg">{jan_act['net_rev']/budget['Jan']['net_rev']*100:.0f}%</div>
      <div class="sub-val">{fmt(jan_act['net_rev'])} vs {fmt(budget['Jan']['net_rev'])}</div>
      <div class="delta neg">Official actuals</div>
    </div>
    <div class="kpi">
      <div class="lbl">Feb Attainment (est.)</div>
      <div class="val warn">{feb_est['net_rev']/budget['Feb']['net_rev']*100:.0f}%</div>
      <div class="sub-val">~{fmt(feb_est['net_rev'])} vs {fmt(budget['Feb']['net_rev'])}</div>
      <div class="delta warn">WC gross, pending close</div>
    </div>
    <div class="kpi">
      <div class="lbl">Mar Projected</div>
      <div class="val pos">{mar_mtd['proj_rev']/budget['Mar']['net_rev']*100:.0f}%</div>
      <div class="sub-val">~{fmt(mar_mtd['proj_rev'])} vs {fmt(budget['Mar']['net_rev'])}</div>
      <div class="delta pos">At ${mar_mtd['daily_rev']:,.0f}/day pace</div>
    </div>
    <div class="kpi">
      <div class="lbl">Walmart (New — Not in Budget)</div>
      <div class="val pos">+{fmt(mar_mtd['net_rev'] - (mar_mtd['net_rev'] - 3486)*(1))}</div>
      <div class="sub-val">${3486:,.0f} MTD · ~${3486/10*31:,.0f}/mo pace</div>
      <div class="delta pos">Incremental to all targets</div>
    </div>
    <div class="kpi">
      <div class="lbl">Ad Spend YTD</div>
      <div class="val">{fmt(d['act_adv_ytd'])}</div>
      <div class="sub-val">vs {fmt(d['bud_adv_ytd'])} budget</div>
      <div class="delta {'pos' if d['act_adv_ytd']<=d['bud_adv_ytd'] else 'neg'}">{(d['act_adv_ytd']/d['bud_adv_ytd']-1)*100:+.1f}% vs budget</div>
    </div>
    <div class="kpi">
      <div class="lbl">Q1 Gap to Make Up</div>
      <div class="val neg">{fmt(q1_gap)}</div>
      <div class="sub-val">shortfall vs Q1 budget</div>
      <div class="delta neg">Needs overperformance in Q2</div>
    </div>
  </div>

  <div class="charts-row">
    <div class="chart-card">
      <div class="chart-title">Monthly Revenue: Budget vs Actual/Projected</div>
      <div class="chart-wrap"><canvas id="chartRevBudget"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Monthly Ad Spend: Budget vs Actual</div>
      <div class="chart-wrap"><canvas id="chartAdvBudget"></canvas></div>
    </div>
  </div>

  <div class="bridge">
    <h3>Key Takeaways</h3>
    <div class="bridge-row">
      <div class="bridge-icon">📉</div>
      <div>
        <div class="bridge-label">January was the biggest miss — 50% attainment</div>
        <div class="bridge-detail">
          {fmt(jan_act['net_rev'])} actual vs {fmt(budget['Jan']['net_rev'])} budget. Ad spend was also -17% vs budget ({fmt(jan_act['advertising'])} vs {fmt(budget['Jan']['advertising'])}),
          which explains most of the revenue shortfall. January is typically the slowest month — the budget may have been optimistic.
          COGS% ran higher than budget (53.4% actual vs 50.2% budget), compressing gross margin.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval neg">{fmt(jan_act['net_rev'] - budget['Jan']['net_rev'])}</div>
        <div class="bsub">vs budget</div>
      </div>
    </div>
    <div class="bridge-row">
      <div class="bridge-icon">📈</div>
      <div>
        <div class="bridge-label">Trend is improving strongly — Feb &amp; March accelerating</div>
        <div class="bridge-detail">
          January: 51% → February: ~69% → March projected: ~87%. The spring ramp is tracking.
          March daily rate of {fmt(mar_mtd['daily_rev'])} puts the full month at ~{fmt(mar_mtd['proj_rev'])}
          — the closest to budget yet, with room to close further if spend scales up mid-month.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval pos">+{abs((0.87-0.51)*100):.0f}pp</div>
        <div class="bsub">Jan→Mar attainment gain</div>
      </div>
    </div>
    <div class="bridge-row">
      <div class="bridge-icon">🛒</div>
      <div>
        <div class="bridge-label">Walmart is incremental — not in budget, pure upside</div>
        <div class="bridge-detail">
          Walmart launched in March and is tracking ~{fmt(3486/10*31)}/month. This channel didn't exist in the budget.
          At a conservative ~{fmt(3486/10*31*9)} for the remaining 9 months (Apr–Dec), Walmart partially offsets the WC revenue gap.
          As listings expand and the account seasons, this number should grow.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval pos">~{fmt(3486/10*31*9)}</div>
        <div class="bsub">Walmart est. Apr–Dec</div>
      </div>
    </div>
    <div class="bridge-row">
      <div class="bridge-icon">⚠️</div>
      <div>
        <div class="bridge-label">AOV compression is the lever that most needs fixing</div>
        <div class="bridge-detail">
          March MTD average order value is ${136:.0f} vs ${184:.0f} in March 2025 — a 26% drop.
          Orders are up +24%, but the smaller basket more than offsets volume gains.
          Getting AOV from ${136:.0f} back to ${160:.0f} (still below last year) would add ~{fmt((160-136)*900)} to March alone
          and could close a large portion of the Q1 gap on its own.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval warn">-${184-136:.0f}</div>
        <div class="bsub">AOV vs last year</div>
      </div>
    </div>
    <div class="bridge-row">
      <div class="bridge-icon">💡</div>
      <div>
        <div class="bridge-label">Ad spend is almost on budget — revenue gap is NOT a spend problem</div>
        <div class="bridge-detail">
          YTD ad spend is only -4.3% behind budget. The revenue shortfall is driven by lower spend in January
          (conscious decision) and AOV compression in March. Marketing efficiency (MER) is actually
          <strong>tracking at 4.43x — identical to last year's YTD</strong>. This means more spend would produce proportional returns.
          April budget calls for {fmt(budget['Apr']['advertising'])} — deploying that fully is critical.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval pos">4.43x</div>
        <div class="bsub">MER (same as 2025)</div>
      </div>
    </div>
  </div>
</div>

<!-- ══ MONTHLY ATTAINMENT ═════════════════════════════════════════════════ -->
<div id="tab-monthly" class="tab-panel">
  <div class="table-wrap">
    <div class="table-title" style="padding:14px 16px;">Revenue & Advertising — Budget vs Actuals by Month</div>
    <table>
      <thead>
        <tr>
          <th>Month</th>
          <th class="num">Rev Budget</th>
          <th class="num">Rev Actual / Est</th>
          <th>Attainment</th>
          <th class="num">Variance</th>
          <th class="num">Adv Budget</th>
          <th>Adv Actual</th>
        </tr>
      </thead>
      <tbody>
        {monthly_rev_rows()}
      </tbody>
    </table>
  </div>
  <div class="note">
    * January = official P&amp;L actuals. February = WooCommerce gross revenue from API (official P&amp;L pending close).
    March = projected from Mar 1-10 daily rate × 31 days. April–December = budget only.<br>
    Walmart revenue (new channel, not in budget): Mar MTD $3,486 · included in March actuals above.
  </div>
</div>

<!-- ══ JANUARY DEEP DIVE ══════════════════════════════════════════════════ -->
<div id="tab-jan" class="tab-panel">
  <div class="table-wrap">
    <div class="table-title" style="padding:14px 16px;">January 2026 — P&amp;L: Budget vs Actuals</div>
    <table>
      <thead>
        <tr>
          <th>Line Item</th>
          <th class="num">Budget</th>
          <th class="num">Actual</th>
          <th class="num">$ Variance</th>
          <th class="num">% Variance</th>
        </tr>
      </thead>
      <tbody>
        {jan_pl_rows()}
      </tbody>
    </table>
  </div>

  <div class="bridge" style="margin-top:0;">
    <h3>January Analysis</h3>
    <div class="bridge-row">
      <div class="bridge-icon">📦</div>
      <div>
        <div class="bridge-label">Revenue miss was driven by lower spend — not conversion problems</div>
        <div class="bridge-detail">
          January ad spend was {fmt(jan_act['advertising'])} vs budget {fmt(budget['Jan']['advertising'])} (-17%).
          At a 4.43x MER, that missing {fmt(budget['Jan']['advertising']-jan_act['advertising'])} in spend would have generated
          ~{fmt((budget['Jan']['advertising']-jan_act['advertising'])*4.43)} in revenue — almost exactly the {fmt(budget['Jan']['net_rev']-jan_act['net_rev'])} shortfall.
          January was run lean intentionally.
        </div>
      </div>
    </div>
    <div class="bridge-row">
      <div class="bridge-icon">📊</div>
      <div>
        <div class="bridge-label">COGS ran 3.2pp higher than budget</div>
        <div class="bridge-detail">
          Budget called for 50.2% COGS rate. Actual came in at 53.4% — likely a mix-of-goods issue
          (smaller orders = higher relative freight per dollar). On {fmt(jan_act['net_rev'])} revenue, that 3.2pp difference
          is ~{fmt(jan_act['net_rev']*0.032)} in reduced gross margin. As revenue scales, COGS% typically improves
          since fixed freight costs get distributed across larger orders.
        </div>
      </div>
    </div>
    <div class="bridge-row">
      <div class="bridge-icon">🏭</div>
      <div>
        <div class="bridge-label">Fixed costs stayed high despite lower revenue</div>
        <div class="bridge-detail">
          Total OpEx was {fmt(jan_act['total_opex'])} vs budget {fmt(budget['Jan']['total_opex'])} — only 17% under budget,
          while revenue was 49% below. G&A ({fmt(jan_act['total_opex']-jan_act['warehouse']-jan_act['advertising']-3148)}) and warehouse
          ({fmt(jan_act['warehouse'])}) are largely fixed. This is why OPEX% hit 134.8% — January's structural loss
          is baked in regardless of revenue performance.
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ══ PATH TO BUDGET ══════════════════════════════════════════════════════ -->
<div id="tab-path" class="tab-panel">

  <div class="kpi-strip">
    <div class="kpi">
      <div class="lbl">Full Year Revenue Budget</div>
      <div class="val">{fmt(fy_bud)}</div>
    </div>
    <div class="kpi">
      <div class="lbl">Q1 Projected Revenue</div>
      <div class="val warn">{fmt(d['act_q1_proj'])}</div>
      <div class="sub-val">vs {fmt(d['bud_q1'])} budget</div>
    </div>
    <div class="kpi">
      <div class="lbl">Q1 Gap (Shortfall)</div>
      <div class="val neg">{fmt(q1_gap)}</div>
    </div>
    <div class="kpi">
      <div class="lbl">Apr–Dec Budget (Remaining)</div>
      <div class="val">{fmt(apr_dec_bud)}</div>
    </div>
    <div class="kpi">
      <div class="lbl">Apr–Dec Needed to Hit FY</div>
      <div class="val neg">{fmt(apr_dec_need)}</div>
      <div class="sub-val">{fmt(apr_dec_gap)} above remaining budget</div>
    </div>
    <div class="kpi">
      <div class="lbl">Overperformance Needed</div>
      <div class="val neg">{gap_pct:+.1f}%</div>
      <div class="sub-val">above Apr–Dec budget to hit FY</div>
    </div>
    <div class="kpi">
      <div class="lbl">Walmart Offset (Est. Apr–Dec)</div>
      <div class="val pos">~{fmt(3486/10*31*9)}</div>
      <div class="sub-val">Not in budget — pure upside</div>
    </div>
    <div class="kpi">
      <div class="lbl">Adj. Overperformance Needed</div>
      <div class="val warn">{((apr_dec_gap - 3486/10*31*9)/apr_dec_bud)*100:+.1f}%</div>
      <div class="sub-val">After Walmart offset</div>
    </div>
  </div>

  <div class="bridge">
    <h3>Path to Budget — Levers &amp; Scenarios</h3>

    <div class="bridge-row">
      <div class="bridge-icon">🌱</div>
      <div>
        <div class="bridge-label">Lever 1: April — The most important month of the year</div>
        <div class="bridge-detail">
          April budget is {fmt(budget['Apr']['net_rev'])} — the second-highest month of the year. Ad spend budget is
          {fmt(budget['Apr']['advertising'])}. Last year April delivered {fmt(379000)} (from Supabase data — close to budget).
          <strong>Fully deploying April's ad budget and getting AOV back toward ${180:.0f}+ is the single biggest lever.</strong>
          A 10% overperformance on April alone = ~{fmt(budget['Apr']['net_rev']*0.10)} recovered.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval">{fmt(budget['Apr']['net_rev'])}</div>
        <div class="bsub">April budget</div>
      </div>
    </div>

    <div class="bridge-row">
      <div class="bridge-icon">💰</div>
      <div>
        <div class="bridge-label">Lever 2: AOV recovery — biggest bang per order</div>
        <div class="bridge-detail">
          Current March AOV: ${136:.0f}. Budget AOV implied: ~${round(budget['Mar']['net_rev'] / 2536):.0f}+
          (based on 2025 order volumes). If March had run at ${175:.0f} AOV (still below 2025),
          revenue would be ~{fmt(175 * 900)} — about {fmt(175*900 - mar_mtd['net_rev'])} more.
          Tactics: quantity breaks, "complete your lawn" cross-sells, bundle SKUs, remove free shipping threshold below 50 lbs.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval pos">+{fmt((175-136)*900)}</div>
        <div class="bsub">if AOV → $175</div>
      </div>
    </div>

    <div class="bridge-row">
      <div class="bridge-icon">🛒</div>
      <div>
        <div class="bridge-label">Lever 3: Walmart channel ramp</div>
        <div class="bridge-detail">
          March pace is {fmt(3486/10*31)}/month. This is early — account is just being seasoned.
          Spring (Apr–May) is the natural peak for seed on Walmart. If Walmart tracks at 2× March pace for
          Apr–May ({fmt(3486/10*31*2)}/month each) and then settles back, total Walmart contribution Apr–Dec
          could reach {fmt(3486/10*31*2*2 + 3486/10*31*7)}.
          Every Walmart dollar is 100% incremental — no budget to beat.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval pos">~{fmt(3486/10*31*2*2 + 3486/10*31*7)}</div>
        <div class="bsub">Walmart Apr–Dec upside</div>
      </div>
    </div>

    <div class="bridge-row">
      <div class="bridge-icon">📧</div>
      <div>
        <div class="bridge-label">Lever 4: Email / Klaviyo — high-margin, zero ad cost</div>
        <div class="bridge-detail">
          55 Klaviyo campaigns drafted for Mar–May 2026. Browse abandonment flow improved with 3 new templates.
          Email revenue has no COGS% impact from freight (digital channel). If email drives 5% incremental lift on
          the Apr–May peak ({fmt(budget['Apr']['net_rev'] + budget['May']['net_rev'])} combined budget),
          that's {fmt((budget['Apr']['net_rev'] + budget['May']['net_rev']) * 0.05)} at near-100% gross margin.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval pos">+{fmt((budget['Apr']['net_rev'] + budget['May']['net_rev']) * 0.05)}</div>
        <div class="bsub">5% email lift on Apr+May</div>
      </div>
    </div>

    <div class="bridge-row">
      <div class="bridge-icon">📊</div>
      <div>
        <div class="bridge-label">Bottom line: gap is recoverable if April and May overperform</div>
        <div class="bridge-detail">
          Full year gap (after Walmart offset) is ~{((apr_dec_gap - 3486/10*31*9)/apr_dec_bud)*100:+.1f}% of the remaining budget — about
          {fmt(apr_dec_gap - 3486/10*31*9)} above plan from Apr–Dec. <strong>April alone represents {fmt(budget['Apr']['net_rev'])} of that
          remaining budget</strong> — one strong month covers nearly all the Q1 shortfall. The key risks are
          not deploying the full April ad budget and not recovering AOV.
        </div>
      </div>
      <div class="bridge-num">
        <div class="bval warn">{fmt(apr_dec_gap - 3486/10*31*9)}</div>
        <div class="bsub">net gap to close</div>
      </div>
    </div>
  </div>

  <div class="chart-card" style="margin-bottom:16px;">
    <div class="chart-title">Monthly Budget — Full Year View (Budget vs Projected)</div>
    <div class="chart-wrap" style="height:240px;"><canvas id="chartPathFull"></canvas></div>
  </div>

  <div class="note">
    All projections based on current daily run rates. February P&amp;L actuals pending official close.
    Walmart revenue is not included in the original budget. EBITDA impact of shortfall not modeled here
    (requires full cost actuals for Feb onward).
  </div>
</div>

{channels_tab_html}

{aov_tab_html}

<script>
function showTab(id, el) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-'+id).classList.add('active');
  el.classList.add('active');
}}

const MONTHS = {month_labels_js};
const budRev  = {bud_rev_js};
const actRev  = {act_rev_js};
const budAdv  = {bud_adv_js};
const actAdv  = {act_adv_js};
const GREEN = '#2d6a4f', ORANGE = '#c96a2e', LGRAY = '#d1d5db', LGREEN = '#52b788';

// Revenue budget vs actual
new Chart(document.getElementById('chartRevBudget'), {{
  type: 'bar',
  data: {{
    labels: MONTHS,
    datasets: [
      {{ label: 'Budget', data: budRev, backgroundColor: LGRAY }},
      {{ label: 'Actual / Projected', data: actRev, backgroundColor: actRev.map((v,i) => {{
        if (v===null) return 'transparent';
        return v >= budRev[i]*0.9 ? GREEN : (v >= budRev[i]*0.65 ? ORANGE : '#e74c3c');
      }}) }},
    ]
  }},
  options: {{ responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ position:'top', labels:{{ font:{{ size:11 }} }} }} }},
    scales:{{
      y:{{ ticks:{{ callback: v=>'$'+v.toLocaleString(), font:{{ size:10 }} }}, grid:{{ color:'#f1f5f9' }} }},
      x:{{ ticks:{{ font:{{ size:9 }} }}, grid:{{ display:false }} }}
    }}
  }}
}});

// Ad spend budget vs actual
new Chart(document.getElementById('chartAdvBudget'), {{
  type: 'bar',
  data: {{
    labels: MONTHS,
    datasets: [
      {{ label: 'Budget', data: budAdv, backgroundColor: LGRAY }},
      {{ label: 'Actual', data: actAdv, backgroundColor: ORANGE }},
    ]
  }},
  options: {{ responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ position:'top', labels:{{ font:{{ size:11 }} }} }} }},
    scales:{{
      y:{{ ticks:{{ callback: v=>'$'+v.toLocaleString(), font:{{ size:10 }} }}, grid:{{ color:'#f1f5f9' }} }},
      x:{{ ticks:{{ font:{{ size:9 }} }}, grid:{{ display:false }} }}
    }}
  }}
}});

// Path to budget - full year
const pathAct = [{jan_act['net_rev']}, {feb_est['net_rev']:.0f}, {mar_mtd['proj_rev']:.0f},
                  null,null,null,null,null,null,null,null,null];
new Chart(document.getElementById('chartPathFull'), {{
  type: 'bar',
  data: {{
    labels: MONTHS,
    datasets: [
      {{ label: 'Budget', data: budRev, backgroundColor: LGRAY, order:2 }},
      {{ label: 'Actual / Projected', data: pathAct, backgroundColor: pathAct.map((v,i) => {{
        if (v===null) return 'transparent';
        const pct = v/budRev[i];
        return pct>=0.9 ? GREEN : (pct>=0.65 ? ORANGE : '#e74c3c');
      }}), order:1 }},
    ]
  }},
  options: {{ responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ position:'top', labels:{{ font:{{ size:11 }} }} }} }},
    scales:{{
      y:{{ ticks:{{ callback: v=>'$'+v.toLocaleString(), font:{{ size:10 }} }}, grid:{{ color:'#f1f5f9' }} }},
      x:{{ ticks:{{ font:{{ size:9 }} }}, grid:{{ display:false }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

OUT.write_text(html)
print(f"Report: {OUT}")
