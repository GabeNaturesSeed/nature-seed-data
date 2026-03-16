#!/usr/bin/env python3
"""Generate ABC analysis HTML dashboard from results JSON."""
import json, html as html_mod
from pathlib import Path

SRC = Path(__file__).parent / "abc_analysis_results.json"
OUT = Path(__file__).parent / "abc_dashboard.html"

with open(SRC) as f:
    data = json.load(f)

skus = data["skus"]
total_rev = data["total_revenue"]
total_units = data["total_units"]
period = "Feb 25 – Mar 11, 2026"

def stats(cls):
    s = [r for r in skus if r["class"] == cls]
    return len(s), sum(r["revenue"] for r in s), sum(r["qty"] for r in s)

a_n, a_r, a_u = stats("A")
b_n, b_r, b_u = stats("B")
c_n, c_r, c_u = stats("C")

def rows_html(cls):
    subset = [r for r in skus if r["class"] == cls]
    out = []
    for i, r in enumerate(subset):
        name = html_mod.unescape(r["name"])
        sku  = r["sku"]
        qty  = r["qty"]
        rev  = r["revenue"]
        drev = r["daily_rev"]
        dqty = r["daily_qty"]
        rpct = r["rev_pct"]
        bar_w = min(int(rpct * 8), 100)  # scale for visual
        out.append(f"""
        <tr class="cls-{cls.lower()}">
          <td class="rank">{i+1}</td>
          <td class="badge-{cls.lower()}">{cls}</td>
          <td class="sku-cell">{sku}</td>
          <td class="name-cell">{name}</td>
          <td class="num">{qty:,}</td>
          <td class="num">${rev:,.2f}</td>
          <td class="num">${drev:,.2f}</td>
          <td class="num">{dqty:.1f}</td>
          <td class="pct-cell">
            <div class="bar-wrap">
              <div class="bar bar-{cls.lower()}" style="width:{bar_w}%"></div>
              <span>{rpct:.2f}%</span>
            </div>
          </td>
        </tr>""")
    return "\n".join(out)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ABC Analysis — Nature's Seed</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #f4f6f8; color: #1a1a1a; font-size: 13px; }}

  /* ── Header ── */
  .header {{ background: #1b4332; color: #fff; padding: 18px 28px; display: flex;
             align-items: baseline; justify-content: space-between; }}
  .header h1 {{ font-size: 18px; font-weight: 700; letter-spacing: -0.3px; }}
  .header .meta {{ font-size: 12px; color: #74c69d; }}

  /* ── KPI cards ── */
  .kpi-row {{ display: flex; gap: 12px; padding: 16px 28px; }}
  .kpi {{ background: #fff; border-radius: 8px; border: 1px solid #e2e8f0;
           padding: 14px 18px; flex: 1; }}
  .kpi .val {{ font-size: 22px; font-weight: 700; color: #1b4332; }}
  .kpi .lbl {{ font-size: 11px; color: #6b7280; margin-top: 2px; }}
  .kpi.kpi-a .val {{ color: #1b4332; }}
  .kpi.kpi-b .val {{ color: #c96a2e; }}
  .kpi.kpi-c .val {{ color: #6b7280; }}

  /* ── Class summary bars ── */
  .class-bars {{ display: flex; gap: 0; margin: 0 28px 16px; border-radius: 6px;
                 overflow: hidden; height: 8px; }}
  .cb-a {{ background: #2d6a4f; flex: 79.9; }}
  .cb-b {{ background: #c96a2e; flex: 15.1; }}
  .cb-c {{ background: #d1d5db; flex: 5.0; }}

  /* ── Controls ── */
  .controls {{ padding: 0 28px 12px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
  .controls input {{ padding: 7px 12px; border: 1px solid #d1d5db; border-radius: 6px;
                      font-size: 13px; width: 260px; outline: none; }}
  .controls input:focus {{ border-color: #2d6a4f; box-shadow: 0 0 0 2px rgba(45,106,79,.15); }}
  .filter-btns {{ display: flex; gap: 6px; }}
  .filter-btn {{ padding: 6px 14px; border-radius: 6px; border: 1px solid #d1d5db;
                  background: #fff; cursor: pointer; font-size: 12px; font-weight: 600;
                  transition: all .15s; }}
  .filter-btn:hover {{ background: #f1f5f9; }}
  .filter-btn.active {{ background: #1b4332; color: #fff; border-color: #1b4332; }}
  .filter-btn.btn-a.active {{ background: #2d6a4f; border-color: #2d6a4f; }}
  .filter-btn.btn-b.active {{ background: #c96a2e; border-color: #c96a2e; }}
  .filter-btn.btn-c.active {{ background: #6b7280; border-color: #6b7280; }}
  .count-label {{ font-size: 12px; color: #6b7280; margin-left: auto; }}

  /* ── Table ── */
  .table-wrap {{ margin: 0 28px 28px; border-radius: 8px; overflow: hidden;
                  border: 1px solid #e2e8f0; background: #fff; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead tr {{ background: #f8fafc; border-bottom: 2px solid #e2e8f0; }}
  thead th {{ padding: 10px 12px; text-align: left; font-size: 11px; font-weight: 700;
               color: #6b7280; text-transform: uppercase; letter-spacing: .5px;
               cursor: pointer; user-select: none; white-space: nowrap; }}
  thead th:hover {{ color: #1b4332; }}
  thead th.num {{ text-align: right; }}
  tbody tr {{ border-bottom: 1px solid #f1f5f9; transition: background .1s; }}
  tbody tr:hover {{ background: #f8fafc; }}
  tbody tr:last-child {{ border-bottom: none; }}
  td {{ padding: 8px 12px; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; color: #374151; }}
  td.rank {{ color: #9ca3af; font-size: 11px; width: 32px; }}
  td.sku-cell {{ font-family: 'SF Mono', 'Fira Code', monospace; font-size: 11px;
                  color: #4b5563; white-space: nowrap; }}
  td.name-cell {{ max-width: 280px; }}
  td.pct-cell {{ width: 120px; }}

  /* ── Class badges ── */
  .badge-a, .badge-b, .badge-c {{
    display: inline-block; width: 22px; height: 22px; border-radius: 50%;
    text-align: center; line-height: 22px; font-weight: 700; font-size: 11px; }}
  .badge-a {{ background: #d1fae5; color: #065f46; }}
  .badge-b {{ background: #ffedd5; color: #9a3412; }}
  .badge-c {{ background: #f3f4f6; color: #6b7280; }}

  /* ── Progress bars ── */
  .bar-wrap {{ display: flex; align-items: center; gap: 6px; }}
  .bar-wrap span {{ font-size: 11px; color: #9ca3af; white-space: nowrap; }}
  .bar {{ height: 6px; border-radius: 3px; min-width: 2px; }}
  .bar-a {{ background: #2d6a4f; }}
  .bar-b {{ background: #c96a2e; }}
  .bar-c {{ background: #d1d5db; }}

  /* ── Row classes for filtering ── */
  tr.hidden {{ display: none; }}

  /* ── Sticky header ── */
  thead {{ position: sticky; top: 0; z-index: 10; }}
</style>
</head>
<body>

<div class="header">
  <h1>ABC Product Classification &mdash; Nature&#39;s Seed</h1>
  <span class="meta">{period} &nbsp;·&nbsp; 14 days &nbsp;·&nbsp; 1,266 orders</span>
</div>

<div class="kpi-row">
  <div class="kpi">
    <div class="val">${total_rev:,.0f}</div>
    <div class="lbl">Total Revenue (14 days)</div>
  </div>
  <div class="kpi">
    <div class="val">${total_rev/14:,.0f}<span style="font-size:14px;color:#6b7280">/day</span></div>
    <div class="lbl">Avg Daily Revenue</div>
  </div>
  <div class="kpi">
    <div class="val">{total_units:,}</div>
    <div class="lbl">Total Units Sold</div>
  </div>
  <div class="kpi kpi-a">
    <div class="val">A &nbsp;{a_n} SKUs</div>
    <div class="lbl">${a_r:,.0f} &nbsp;·&nbsp; {a_r/total_rev*100:.1f}% of revenue</div>
  </div>
  <div class="kpi kpi-b">
    <div class="val">B &nbsp;{b_n} SKUs</div>
    <div class="lbl">${b_r:,.0f} &nbsp;·&nbsp; {b_r/total_rev*100:.1f}% of revenue</div>
  </div>
  <div class="kpi kpi-c">
    <div class="val">C &nbsp;{c_n} SKUs</div>
    <div class="lbl">${c_r:,.0f} &nbsp;·&nbsp; {c_r/total_rev*100:.1f}% of revenue</div>
  </div>
</div>

<div class="class-bars">
  <div class="cb-a" title="Class A: 79.9%"></div>
  <div class="cb-b" title="Class B: 15.1%"></div>
  <div class="cb-c" title="Class C: 5.0%"></div>
</div>

<div class="controls">
  <input type="text" id="search" placeholder="Search SKU or product name…" oninput="filterTable()">
  <div class="filter-btns">
    <button class="filter-btn active" data-cls="all" onclick="setFilter('all',this)">All 212</button>
    <button class="filter-btn btn-a" data-cls="A" onclick="setFilter('A',this)">A &nbsp;{a_n}</button>
    <button class="filter-btn btn-b" data-cls="B" onclick="setFilter('B',this)">B &nbsp;{b_n}</button>
    <button class="filter-btn btn-c" data-cls="C" onclick="setFilter('C',this)">C &nbsp;{c_n}</button>
  </div>
  <span class="count-label" id="count-label">212 of 212 SKUs</span>
</div>

<div class="table-wrap">
<table id="abc-table">
  <thead>
    <tr>
      <th>#</th>
      <th>Class</th>
      <th onclick="sortTable(2)">SKU &#8597;</th>
      <th onclick="sortTable(3)">Product &#8597;</th>
      <th class="num" onclick="sortTable(4)">14d Units &#8597;</th>
      <th class="num" onclick="sortTable(5)">14d Revenue &#8597;</th>
      <th class="num" onclick="sortTable(6)">$/day &#8597;</th>
      <th class="num" onclick="sortTable(7)">Units/day &#8597;</th>
      <th>Rev %</th>
    </tr>
  </thead>
  <tbody id="table-body">
    {rows_html("A")}
    {rows_html("B")}
    {rows_html("C")}
  </tbody>
</table>
</div>

<script>
let activeFilter = 'all';

function setFilter(cls, btn) {{
  activeFilter = cls;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  filterTable();
}}

function filterTable() {{
  const q = document.getElementById('search').value.toLowerCase();
  const rows = document.querySelectorAll('#table-body tr');
  let visible = 0;
  rows.forEach(row => {{
    const cls = row.className.replace('cls-','').trim();
    const text = row.textContent.toLowerCase();
    const clsMatch = activeFilter === 'all' || cls === activeFilter.toLowerCase();
    const textMatch = !q || text.includes(q);
    if (clsMatch && textMatch) {{
      row.classList.remove('hidden');
      visible++;
    }} else {{
      row.classList.add('hidden');
    }}
  }});
  document.getElementById('count-label').textContent = visible + ' of 212 SKUs';
}}

let sortDir = {{}};
function sortTable(col) {{
  const tbody = document.getElementById('table-body');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const dir = sortDir[col] = !(sortDir[col]);
  rows.sort((a, b) => {{
    const av = a.cells[col]?.textContent.replace(/[$,]/g,'').trim() || '';
    const bv = b.cells[col]?.textContent.replace(/[$,]/g,'').trim() || '';
    const an = parseFloat(av), bn = parseFloat(bv);
    if (!isNaN(an) && !isNaN(bn)) return dir ? an-bn : bn-an;
    return dir ? av.localeCompare(bv) : bv.localeCompare(av);
  }});
  rows.forEach(r => tbody.appendChild(r));
  // re-number
  let counts = {{a:0,b:0,c:0}};
  rows.forEach(r => {{
    const cls = r.className.replace('cls-','').trim();
    counts[cls] = (counts[cls]||0)+1;
    r.cells[0].textContent = counts[cls];
  }});
}}
</script>
</body>
</html>"""

OUT.write_text(html)
print(f"Dashboard: {OUT}")
