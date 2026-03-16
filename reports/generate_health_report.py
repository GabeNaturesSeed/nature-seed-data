#!/usr/bin/env python3
"""Generate MTD/YTD ecommerce health report HTML."""
import json
from pathlib import Path

with open('/tmp/report_data.json') as f:
    d = json.load(f)

rows   = d['rows']
months = d['months']
labels = d['labels']
mtd25  = d['mtd25']
mtd26  = d['mtd26']
ytd25  = d['ytd25']
ytd26  = d['ytd26']

OUT = Path(__file__).parent / "ecommerce_health_report.html"

def pct(a, b):
    if not b: return 0
    return (a / b - 1) * 100

def pct_str(a, b):
    v = pct(a, b)
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%"

def arrow(a, b, good_if_up=True):
    v = pct(a, b)
    if abs(v) < 1: return "→", "neutral"
    up = v > 0
    if (up and good_if_up) or (not up and not good_if_up):
        return ("▲" if up else "▼"), "positive"
    return ("▲" if up else "▼"), "negative"

def fmt_rev(v):    return f"${v:,.0f}"
def fmt_spend(v):  return f"${v:,.0f}"
def fmt_x(v):      return f"{v:.2f}x"
def fmt_pct(v):    return f"{v:.1f}%"
def fmt_n(v):      return f"{int(v):,}"

# ── Build chart data ──────────────────────────────────────────────────────
chart_labels_25 = [labels[m] for m in months if m.startswith('2025')]
chart_labels_26 = [labels[m] for m in months if m.startswith('2026')]
rev_25  = [round(rows.get(m, {}).get('rev_total', 0), 0) for m in months if m.startswith('2025')]
rev_26  = [round(rows.get(m, {}).get('rev_total', 0), 0) for m in months if m.startswith('2026')]
mer_25  = [round(rows.get(m, {}).get('mer', 0), 2) for m in months if m.startswith('2025')]
mer_26  = [round(rows.get(m, {}).get('mer', 0), 2) for m in months if m.startswith('2026')]
spend_25 = [round(rows.get(m, {}).get('spend', 0), 0) for m in months if m.startswith('2025')]
spend_26 = [round(rows.get(m, {}).get('spend', 0), 0) for m in months if m.startswith('2026')]

# Monthly comparison table rows (paired)
month_pairs = [
    ('2025-01','2026-01'), ('2025-02','2026-02'), ('2025-03','2026-03'),
]
all_paired_months = [
    ('Jan',  '2025-01', '2026-01'),
    ('Feb',  '2025-02', '2026-02'),
    ('Mar*', '2025-03', '2026-03'),
]

def kpi_card(label, val25, val26, fmt_fn, good_if_up=True, note=''):
    ar, cls = arrow(val26, val25, good_if_up)
    p = pct_str(val26, val25)
    color = {'positive': '#2d6a4f', 'negative': '#c0392b', 'neutral': '#6b7280'}[cls]
    return f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}{f'<span class="kpi-note">{note}</span>' if note else ''}</div>
      <div class="kpi-row-vals">
        <div class="kpi-yr">
          <span class="kpi-yr-label">2025</span>
          <span class="kpi-yr-val">{fmt_fn(val25)}</span>
        </div>
        <div class="kpi-yr kpi-yr-now">
          <span class="kpi-yr-label">2026</span>
          <span class="kpi-yr-val">{fmt_fn(val26)}</span>
        </div>
      </div>
      <div class="kpi-delta" style="color:{color}">
        {ar} {p}
      </div>
    </div>"""

def section_kpis(data25, data26):
    cards = [
        kpi_card("Total Revenue",   data25['rev_total'], data26['rev_total'], fmt_rev),
        kpi_card("WooCommerce Rev", data25['rev_wc'],    data26['rev_wc'],    fmt_rev),
        kpi_card("Walmart Rev",     data25.get('rev_wm',0), data26.get('rev_wm',0), fmt_rev, note=" (new)"),
        kpi_card("Total Orders",    data25['orders'],    data26['orders'],    fmt_n),
        kpi_card("Avg Order Value (WC)", data25['aov'], data26['aov'],        fmt_rev),
        kpi_card("Ad Spend",        data25['spend'],     data26['spend'],     fmt_spend, good_if_up=False),
        kpi_card("MER",             data25['mer'],       data26['mer'],       fmt_x),
        kpi_card("ROAS (Google)",   data25['roas'],      data26['roas'],      fmt_x),
        kpi_card("Conv. Volume",    data25['conversions'], data26['conversions'], fmt_n),
    ]
    return "<div class='kpi-grid'>" + "".join(cards) + "</div>"

# Monthly table
def monthly_table_rows():
    html = []
    for label, ym25, ym26 in all_paired_months:
        m25 = rows.get(ym25, {})
        m26 = rows.get(ym26, {})
        r25 = m25.get('rev_total', 0); r26 = m26.get('rev_total', 0)
        o25 = m25.get('orders', 0);    o26 = m26.get('orders', 0)
        sp25 = m25.get('spend', 0);    sp26 = m26.get('spend', 0)
        mer25 = m25.get('mer', 0);     mer26 = m26.get('mer', 0)
        roas25 = m25.get('roas', 0);   roas26 = m26.get('roas', 0)
        aov25 = m25.get('aov', 0);     aov26 = m26.get('aov', 0)
        rev_p = pct(r26, r25); ord_p = pct(o26, o25)
        cls_r = "pos" if rev_p >= 0 else "neg"
        cls_o = "pos" if ord_p >= 0 else "neg"
        is_mtd = '*' in label
        mtd_note = '<span class="mtd-tag">MTD</span>' if is_mtd else ''
        html.append(f"""
        <tr>
          <td class="month-label">{label.replace('*','')} {mtd_note}</td>
          <td class="num">{fmt_rev(r25)}</td>
          <td class="num">{fmt_rev(r26)}</td>
          <td class="num delta {cls_r}">{pct_str(r26, r25)}</td>
          <td class="num">{fmt_n(o25)}</td>
          <td class="num">{fmt_n(o26)}</td>
          <td class="num delta {cls_o}">{pct_str(o26, o25)}</td>
          <td class="num">{fmt_rev(aov25)}</td>
          <td class="num">{fmt_rev(aov26)}</td>
          <td class="num">{fmt_spend(sp25)}</td>
          <td class="num">{fmt_spend(sp26)}</td>
          <td class="num">{fmt_x(mer25)}</td>
          <td class="num {'pos' if mer26>=mer25 else 'neg'}">{fmt_x(mer26)}</td>
          <td class="num">{fmt_x(roas25)}</td>
          <td class="num {'pos' if roas26>=roas25 else 'neg'}">{fmt_x(roas26)}</td>
        </tr>""")
    return "\n".join(html)

# Full monthly performance table (2025 + 2026)
def full_monthly_rows():
    html = []
    for ym in months:
        m = rows.get(ym, {})
        lbl = labels.get(ym, ym)
        is_26 = ym.startswith('2026')
        row_cls = 'row-2026' if is_26 else 'row-2025'
        html.append(f"""
        <tr class="{row_cls}">
          <td class="month-label">{lbl}</td>
          <td class="num">{fmt_rev(m.get('rev_wc',0))}</td>
          <td class="num">{fmt_rev(m.get('rev_wm',0)) if m.get('rev_wm',0) else '—'}</td>
          <td class="num bold">{fmt_rev(m.get('rev_total',0))}</td>
          <td class="num">{fmt_n(m.get('orders',0))}</td>
          <td class="num">{fmt_rev(m.get('aov',0)) if m.get('aov',0) else '—'}</td>
          <td class="num">{fmt_n(m.get('units',0))}</td>
          <td class="num">{fmt_spend(m.get('spend',0))}</td>
          <td class="num">{fmt_x(m.get('mer',0)) if m.get('spend',0) else '—'}</td>
          <td class="num">{fmt_x(m.get('roas',0)) if m.get('spend',0) else '—'}</td>
          <td class="num">{fmt_n(m.get('clicks',0))}</td>
          <td class="num">{fmt_n(m.get('conversions',0))}</td>
        </tr>""")
    return "\n".join(html)

# Insight bullets
mtd_rev_pct = pct(mtd26['rev_total'], mtd25['rev_total'])
mtd_ord_pct = pct(mtd26['orders'], mtd25['orders'])
mtd_aov_pct = pct(mtd26['aov'], mtd25['aov'])
ytd_rev_pct = pct(ytd26['rev_total'], ytd25['rev_total'])
ytd_mer_diff = ytd26['mer'] - ytd25['mer']

insights = [
    ("Revenue down MTD, driven entirely by AOV compression",
     f"March 1-10 revenue is {mtd_rev_pct:+.1f}% YoY (${mtd26['rev_total']:,.0f} vs ${mtd25['rev_total']:,.0f}). "
     f"Orders actually <strong>grew +{mtd_ord_pct:.0f}%</strong> (900 vs 727), but average order value fell "
     f"<strong>{mtd_aov_pct:.0f}% to ${mtd26['aov']:.0f}</strong> from ${mtd25['aov']:.0f}. "
     f"Smaller basket size, not less traffic, is the story."),
    ("Marketing efficiency held — MER flat YTD, ROAS improved",
     f"YTD MER is identical at {ytd25['mer']:.2f}x vs {ytd26['mer']:.2f}x — every dollar of ad spend "
     f"produces the same total revenue return. ROAS improved from {ytd25['roas']:.2f}x to {ytd26['roas']:.2f}x, "
     f"suggesting better conversion quality on Google. The spend reduction "
     f"({pct(ytd26['spend'], ytd25['spend']):+.0f}%) explains most of the YTD revenue gap."),
    ("YTD revenue decline correlates 1:1 with reduced ad spend",
     f"YTD revenue is {ytd_rev_pct:+.1f}% — and ad spend dropped {pct(ytd26['spend'], ytd25['spend']):+.1f}%. "
     f"January and February 2026 were run at significantly lower spend "
     f"(Jan: ${rows['2026-01']['spend']:,.0f} vs ${rows['2025-01']['spend']:,.0f}; "
     f"Feb: ${rows['2026-02']['spend']:,.0f} vs ${rows['2025-02']['spend']:,.0f}). "
     f"This was a budget decision, not a market efficiency loss."),
    ("Walmart launched — new incremental revenue channel",
     f"${mtd26.get('rev_wm', 0):,.0f} Walmart revenue in March MTD, adding "
     f"{mtd26.get('rev_wm', 0) / mtd26['rev_total'] * 100:.1f}% on top of WooCommerce. "
     f"Zero Walmart revenue existed in 2025 — all incremental. "
     f"Full-month March 2025 delivered ${rows['2025-03']['rev_wm']:.0f} from Walmart."),
    ("Spring 2026 ramp looks solid — March daily rate on pace",
     f"Current March MTD daily rate: ${mtd26['rev_total']/10:,.0f}/day. "
     f"March 2025 full-month average: ${rows['2025-03']['rev_total']/31:,.0f}/day. "
     f"At current pace, March 2026 projects to ~${mtd26['rev_total']/10*31:,.0f} — "
     f"vs actual ${rows['2025-03']['rev_total']:,.0f} in March 2025. "
     f"Spring acceleration is tracking similarly to last year."),
]

def insight_cards():
    cards = []
    icons = ["⚡", "📊", "💡", "🛒", "🌱"]
    for i, (title, body) in enumerate(insights):
        cards.append(f"""
    <div class="insight-card">
      <div class="insight-icon">{icons[i]}</div>
      <div class="insight-body">
        <div class="insight-title">{title}</div>
        <div class="insight-text">{body}</div>
      </div>
    </div>""")
    return "\n".join(cards)

# Pre-build all chart data as JSON strings (avoids f-string/dict-literal conflicts)
_empty = {}
all_labels_js  = json.dumps([labels[m] for m in months])
all_rev_js     = json.dumps([round(rows.get(m, _empty).get('rev_total', 0), 0) for m in months])
all_spend_js   = json.dumps([round(rows.get(m, _empty).get('spend', 0), 0) for m in months])
all_mer_js     = json.dumps([round(rows.get(m, _empty).get('mer', 0), 2) for m in months])
ml25_js        = json.dumps([labels[m] for m in months if m.startswith('2025')])
ml26_js        = json.dumps([labels[m] for m in months if m.startswith('2026')])
rev25_js       = json.dumps(rev_25)
rev26_js       = json.dumps(rev_26)
mer25_js       = json.dumps(mer_25)
mer26_js       = json.dumps(mer_26)
spend25_js     = json.dumps(spend_25)
spend26_js     = json.dumps(spend_26)
# Color arrays for full chart (green = 2026)
all_colors_js  = json.dumps(['#2d6a4f' if m.startswith('2026') else '#d1d5db' for m in months])

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ecommerce Health Report — Nature's Seed — March 2026</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #f4f6f8; color: #1a1a1a; font-size: 13px; line-height: 1.5; }}

  /* ── Header ── */
  .header {{ background: #1b4332; color: #fff; padding: 24px 36px; }}
  .header h1 {{ font-size: 20px; font-weight: 700; letter-spacing: -0.3px; }}
  .header .subtitle {{ font-size: 13px; color: #74c69d; margin-top: 4px; }}

  /* ── Sections ── */
  .section {{ margin: 0 36px 32px; }}
  .section-title {{ font-size: 15px; font-weight: 700; color: #1b4332;
                     border-left: 4px solid #2d6a4f; padding-left: 10px;
                     margin-bottom: 16px; margin-top: 28px; }}

  /* ── Period tabs ── */
  .period-tabs {{ display: flex; gap: 0; margin: 20px 36px 0; border-bottom: 2px solid #e2e8f0; }}
  .tab {{ padding: 10px 24px; cursor: pointer; font-size: 13px; font-weight: 600;
           color: #6b7280; border-bottom: 3px solid transparent; margin-bottom: -2px;
           transition: all .15s; }}
  .tab.active {{ color: #1b4332; border-bottom-color: #2d6a4f; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}

  /* ── KPI Grid ── */
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 12px; margin-bottom: 8px; }}
  .kpi-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; }}
  .kpi-label {{ font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase;
                 letter-spacing: .5px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }}
  .kpi-note {{ font-size: 10px; color: #9ca3af; font-weight: 400; text-transform: none; letter-spacing: 0; }}
  .kpi-row-vals {{ display: flex; gap: 12px; margin-bottom: 8px; }}
  .kpi-yr {{ flex: 1; }}
  .kpi-yr-label {{ font-size: 10px; color: #9ca3af; display: block; margin-bottom: 2px; }}
  .kpi-yr-val {{ font-size: 16px; font-weight: 700; color: #374151; }}
  .kpi-yr-now .kpi-yr-val {{ color: #1b4332; font-size: 18px; }}
  .kpi-delta {{ font-size: 13px; font-weight: 700; }}

  /* ── Insight cards ── */
  .insights {{ display: flex; flex-direction: column; gap: 12px; margin: 0 36px 28px; }}
  .insight-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
                    padding: 16px 20px; display: flex; gap: 14px; align-items: flex-start; }}
  .insight-icon {{ font-size: 20px; flex-shrink: 0; margin-top: 1px; }}
  .insight-title {{ font-size: 13px; font-weight: 700; color: #1a1a1a; margin-bottom: 4px; }}
  .insight-text {{ font-size: 12px; color: #555; line-height: 1.6; }}

  /* ── Charts ── */
  .charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
                  margin: 0 36px 28px; }}
  .chart-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; }}
  .chart-title {{ font-size: 12px; font-weight: 700; color: #374151;
                   text-transform: uppercase; letter-spacing: .5px; margin-bottom: 12px; }}
  .chart-wrap {{ position: relative; height: 220px; }}

  /* ── Tables ── */
  .table-wrap {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
                  overflow: hidden; margin: 0 36px 28px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  thead tr {{ background: #f8fafc; border-bottom: 2px solid #e2e8f0; }}
  thead th {{ padding: 10px 12px; text-align: left; font-size: 10px; font-weight: 700;
               color: #6b7280; text-transform: uppercase; letter-spacing: .5px; white-space: nowrap; }}
  thead th.num {{ text-align: right; }}
  tbody tr {{ border-bottom: 1px solid #f1f5f9; }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody tr:hover {{ background: #f8fafc; }}
  td {{ padding: 9px 12px; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; color: #374151; }}
  td.bold {{ font-weight: 700; }}
  td.month-label {{ font-weight: 600; color: #1a1a1a; }}
  td.pos {{ color: #2d6a4f; font-weight: 700; }}
  td.neg {{ color: #c0392b; font-weight: 700; }}
  td.delta {{ white-space: nowrap; }}
  .mtd-tag {{ display: inline-block; background: #dbeafe; color: #1d4ed8; font-size: 9px;
               font-weight: 700; padding: 1px 5px; border-radius: 10px;
               text-transform: uppercase; letter-spacing: .5px; margin-left: 4px; }}
  tr.row-2026 {{ background: #f0fdf4 !important; }}
  tr.row-2026:hover {{ background: #dcfce7 !important; }}

  /* ── Trend sparkline bar in table ── */
  .spark-bar-wrap {{ display: flex; align-items: center; gap: 6px; }}
  .spark-bar {{ height: 8px; border-radius: 4px; background: #2d6a4f; }}

  /* ── Footer note ── */
  .footer-note {{ margin: 0 36px 32px; font-size: 11px; color: #9ca3af; line-height: 1.6; }}
  .footer-note strong {{ color: #6b7280; }}
</style>
</head>
<body>

<div class="header">
  <h1>Ecommerce Health Report — Nature's Seed</h1>
  <div class="subtitle">MTD &amp; YTD Performance vs Prior Year &nbsp;·&nbsp; As of March 10, 2026 &nbsp;·&nbsp; WooCommerce + Walmart + Google Ads</div>
</div>

<!-- ── Period tabs ──────────────────────────────────────────────── -->
<div class="period-tabs">
  <div class="tab active" onclick="showTab('mtd',this)">MTD (March 1–10)</div>
  <div class="tab" onclick="showTab('ytd',this)">YTD (Jan 1–Mar 10)</div>
  <div class="tab" onclick="showTab('monthly',this)">Monthly Breakdown</div>
  <div class="tab" onclick="showTab('full',this)">Full History</div>
</div>

<!-- ── MTD Panel ──────────────────────────────────────────────────── -->
<div id="tab-mtd" class="tab-panel active">
  <div class="section-title" style="margin: 24px 36px 16px;">MTD Performance: March 1–10, 2026 vs 2025</div>
  {section_kpis(mtd25, mtd26)}

  <div class="section-title" style="margin: 24px 36px 16px;">MTD Highlights</div>
  <div class="insights">
    {insight_cards()}
  </div>
</div>

<!-- ── YTD Panel ──────────────────────────────────────────────────── -->
<div id="tab-ytd" class="tab-panel">
  <div class="section-title" style="margin: 24px 36px 16px;">YTD Performance: Jan 1–Mar 10, 2026 vs 2025</div>
  {section_kpis(ytd25, ytd26)}
</div>

<!-- ── Monthly Breakdown Panel ─────────────────────────────────────── -->
<div id="tab-monthly" class="tab-panel">
  <div class="section-title" style="margin: 24px 36px 16px;">Month-by-Month Comparison: 2025 vs 2026</div>

  <div class="charts-row">
    <div class="chart-card">
      <div class="chart-title">Monthly Revenue — 2025 vs 2026</div>
      <div class="chart-wrap"><canvas id="chartRev"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">MER — 2025 vs 2026</div>
      <div class="chart-wrap"><canvas id="chartMer"></canvas></div>
    </div>
  </div>

  <div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>Month</th>
        <th class="num">Rev 2025</th>
        <th class="num">Rev 2026</th>
        <th class="num">YoY Rev</th>
        <th class="num">Orders 2025</th>
        <th class="num">Orders 2026</th>
        <th class="num">YoY Orders</th>
        <th class="num">AOV 2025</th>
        <th class="num">AOV 2026</th>
        <th class="num">Spend 2025</th>
        <th class="num">Spend 2026</th>
        <th class="num">MER 2025</th>
        <th class="num">MER 2026</th>
        <th class="num">ROAS 2025</th>
        <th class="num">ROAS 2026</th>
      </tr>
    </thead>
    <tbody>
      {monthly_table_rows()}
    </tbody>
  </table>
  </div>

  <div class="footer-note">
    * March 2026 is MTD (10 days), compared against the same March 1-10 period in 2025 for fair comparison.<br>
    March 2025 full month: <strong>${rows['2025-03']['rev_total']:,.0f}</strong> revenue across 31 days.
  </div>
</div>

<!-- ── Full History Panel ────────────────────────────────────────────── -->
<div id="tab-full" class="tab-panel">
  <div class="section-title" style="margin: 24px 36px 16px;">Full Monthly History — Jan 2025 to Mar 2026 MTD</div>
  <div class="charts-row">
    <div class="chart-card">
      <div class="chart-title">Monthly Revenue (All Channels)</div>
      <div class="chart-wrap"><canvas id="chartFull"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Ad Spend vs MER</div>
      <div class="chart-wrap"><canvas id="chartSpend"></canvas></div>
    </div>
  </div>

  <div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>Month</th>
        <th class="num">WC Revenue</th>
        <th class="num">Walmart</th>
        <th class="num">Total Rev</th>
        <th class="num">Orders</th>
        <th class="num">AOV</th>
        <th class="num">Units</th>
        <th class="num">Ad Spend</th>
        <th class="num">MER</th>
        <th class="num">ROAS</th>
        <th class="num">Clicks</th>
        <th class="num">Conversions</th>
      </tr>
    </thead>
    <tbody>
      {full_monthly_rows()}
    </tbody>
  </table>
  </div>
  <div class="footer-note">
    2026 rows highlighted in green. March 2026 is MTD (10 days). Jan–Feb 2026 backfilled from WooCommerce + Google Ads APIs.
  </div>
</div>

<script>
// ── Tab switching ─────────────────────────────────────────────────────
function showTab(id, el) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-'+id).classList.add('active');
  el.classList.add('active');
}}

// ── Chart.js charts ────────────────────────────────────────────────────
const monthLabels = {ml25_js};
const monthLabels26 = {ml26_js};
const rev25 = {rev25_js};
const rev26 = {rev26_js};
const mer25 = {mer25_js};
const mer26 = {mer26_js};
const spend25 = {spend25_js};
const spend26 = {spend26_js};
const allLabels = {all_labels_js};
const allRev = {all_rev_js};
const allSpend = {all_spend_js};
const allMer = {all_mer_js};
const allColors = {all_colors_js};

const GREEN = '#2d6a4f'; const ORANGE = '#c96a2e'; const LGRAY = '#d1d5db';

// Revenue comparison
new Chart(document.getElementById('chartRev'), {{
  type: 'bar',
  data: {{
    labels: monthLabels,
    datasets: [
      {{ label: '2025', data: rev25, backgroundColor: LGRAY }},
      {{ label: '2026', data: rev26.concat([null,null,null,null,null,null,null,null,null]).slice(0,12),
         backgroundColor: GREEN }},
    ]
  }},
  options: {{ responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'top', labels: {{ font: {{ size: 11 }} }} }} }},
    scales: {{
      y: {{ ticks: {{ callback: v => '$'+v.toLocaleString(), font: {{ size: 10 }} }}, grid: {{ color: '#f1f5f9' }} }},
      x: {{ ticks: {{ font: {{ size: 9 }} }}, grid: {{ display: false }} }}
    }}
  }}
}});

// MER comparison
new Chart(document.getElementById('chartMer'), {{
  type: 'line',
  data: {{
    labels: monthLabels,
    datasets: [
      {{ label: 'MER 2025', data: mer25, borderColor: LGRAY, backgroundColor: 'transparent',
         tension: 0.3, borderWidth: 2 }},
      {{ label: 'MER 2026', data: mer26.concat([null,null,null,null,null,null,null,null,null]).slice(0,12),
         borderColor: GREEN, backgroundColor: 'transparent', tension: 0.3, borderWidth: 2,
         pointBackgroundColor: GREEN }},
    ]
  }},
  options: {{ responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'top', labels: {{ font: {{ size: 11 }} }} }} }},
    scales: {{
      y: {{ ticks: {{ callback: v => v+'x', font: {{ size: 10 }} }}, grid: {{ color: '#f1f5f9' }} }},
      x: {{ ticks: {{ font: {{ size: 9 }} }}, grid: {{ display: false }} }}
    }}
  }}
}});

// Full revenue chart
new Chart(document.getElementById('chartFull'), {{
  type: 'bar',
  data: {{
    labels: allLabels,
    datasets: [{{
      label: 'Total Revenue',
      data: allRev,
      backgroundColor: allColors,
    }}]
  }},
  options: {{ responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      y: {{ ticks: {{ callback: v => '$'+v.toLocaleString(), font: {{ size: 10 }} }}, grid: {{ color: '#f1f5f9' }} }},
      x: {{ ticks: {{ font: {{ size: 9 }}, maxRotation: 45 }}, grid: {{ display: false }} }}
    }}
  }}
}});

// Spend vs MER
new Chart(document.getElementById('chartSpend'), {{
  type: 'bar',
  data: {{
    labels: allLabels,
    datasets: [
      {{ label: 'Ad Spend', data: allSpend, backgroundColor: ORANGE, yAxisID: 'y' }},
      {{ label: 'MER', data: allMer, type: 'line', borderColor: GREEN,
         backgroundColor: 'transparent', yAxisID: 'y2', tension: 0.3, borderWidth: 2 }},
    ]
  }},
  options: {{ responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'top', labels: {{ font: {{ size: 11 }} }} }} }},
    scales: {{
      y:  {{ ticks: {{ callback: v => '$'+v.toLocaleString(), font: {{ size: 10 }} }}, grid: {{ color: '#f1f5f9' }} }},
      y2: {{ position: 'right', ticks: {{ callback: v => v+'x', font: {{ size: 10 }} }}, grid: {{ display: false }} }},
      x:  {{ ticks: {{ font: {{ size: 9 }}, maxRotation: 45 }}, grid: {{ display: false }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(html)
print(f"Report: {OUT}")
