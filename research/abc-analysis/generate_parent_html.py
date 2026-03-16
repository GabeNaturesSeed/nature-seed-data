#!/usr/bin/env python3
"""Generate ABC parent-level HTML dashboard with size variant breakdown and category trends."""
import json, html as html_mod
from pathlib import Path

SRC = Path(__file__).parent / "abc_parent_results.json"
OUT = Path(__file__).parent / "abc_parent_dashboard.html"

with open(SRC) as f:
    data = json.load(f)

products   = data["products"]
total_rev  = data["total_revenue"]
total_units = data["total_units"]
period     = data["period"].replace(" to ", " – ")
cat_trends = data["category_size_trends"]

CAT_MAP = {
    "Lawn & Turf":              "Lawn",
    "Pasture & Forage":         "Pasture",
    "Forage Grasses & Legumes": "Pasture",
    "Wildflower":               "Wildflower",
    "Amendments & Specialty":   "Planting Aids",
    "Conservation":             "Other",
    "Food Plot & Wildlife":     "Other",
    "Cover Crop":               "Other",
    "Other":                    "Other",
}

def parent_cat(p):
    return CAT_MAP.get(p["category"], "Other")

# Attach parent_cat to each product for easy access
for p in products:
    p["parent_cat"] = parent_cat(p)

PARENT_CATS = ["Lawn", "Pasture", "Wildflower", "Planting Aids", "Other"]

def stats(cls):
    s = [p for p in products if p["class"] == cls]
    return len(s), sum(p["rev"] for p in s), sum(p["qty"] for p in s)

a_n, a_r, a_u = stats("A")
b_n, b_r, b_u = stats("B")
c_n, c_r, c_u = stats("C")

# ── Product rows HTML ─────────────────────────────────────────────────────────
def product_rows():
    rows = []
    for i, p in enumerate(products):
        cls     = p["class"]
        pid     = p["pid"]
        name    = html_mod.escape(p["name"])
        sku     = html_mod.escape(p["sku_base"])
        cat     = html_mod.escape(p["category"])
        rev     = p["rev"]
        qty     = p["qty"]
        orders  = p["orders"]
        drev    = p["daily_rev"]
        dqty    = p["daily_qty"]
        rpct    = p["rev_pct"]
        bar_w   = min(int(rpct * 8), 100)
        variants = p["variants"]

        # Build variant detail rows
        var_rows = []
        top_rev = max((v["rev"] for v in variants.values()), default=1)
        for size, sv in variants.items():
            pct_of_parent = sv["rev"] / rev * 100 if rev else 0
            bar = min(int(pct_of_parent * 1.5), 100)
            var_rows.append(f"""
              <tr class="variant-row">
                <td colspan="2"></td>
                <td class="var-size">{html_mod.escape(size)}</td>
                <td class="var-sku">{html_mod.escape(sv['sku'])}</td>
                <td class="num">{sv['qty']:,}</td>
                <td class="num">${sv['rev']:,.2f}</td>
                <td class="num" colspan="2">
                  <div class="var-bar-wrap">
                    <div class="var-bar var-bar-{cls.lower()}" style="width:{bar}%"></div>
                    <span>{pct_of_parent:.1f}% of product</span>
                  </div>
                </td>
                <td></td>
              </tr>""")

        var_html = "\n".join(var_rows)
        toggle_id = f"vars-{pid}"

        pcat = p["parent_cat"]
        rows.append(f"""
        <tr class="cls-{cls.lower()} parent-row" data-pid="{pid}" data-pcat="{pcat}" onclick="toggleVariants('{toggle_id}', this)">
          <td class="rank">{i+1}</td>
          <td><span class="badge-{cls.lower()}">{cls}</span></td>
          <td class="sku-cell">{sku}</td>
          <td class="name-cell">
            <span class="expand-icon">▶</span> {name}
            <br><span class="cat-tag">{cat}</span>
          </td>
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
        </tr>
        <tr id="{toggle_id}" class="variant-group hidden">
          <td colspan="9" class="variant-container">
            <table class="variant-table">
              <thead>
                <tr>
                  <th colspan="2"></th>
                  <th>Size</th>
                  <th>SKU</th>
                  <th class="num">Units</th>
                  <th class="num">Revenue</th>
                  <th colspan="2">Share of Product</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {var_html}
              </tbody>
            </table>
          </td>
        </tr>""")
    return "\n".join(rows)


# ── Category size trends HTML ─────────────────────────────────────────────────
def cat_trends_html():
    cards = []
    cat_colors = {
        "Pasture & Forage":        "#2d6a4f",
        "Lawn & Turf":             "#40916c",
        "Wildflower":              "#8B5CF6",
        "Conservation":            "#0369A1",
        "Forage Grasses & Legumes":"#B45309",
        "Amendments & Specialty":  "#6B7280",
        "Food Plot & Wildlife":    "#92400E",
        "Cover Crop":              "#065F46",
        "Other":                   "#9CA3AF",
    }
    for cat, sizes in cat_trends.items():
        color = cat_colors.get(cat, "#6b7280")
        total_cat_rev = sum(sizes.values())
        top_sizes = list(sizes.items())[:6]
        max_rev = top_sizes[0][1] if top_sizes else 1
        size_bars = []
        for size, rev in top_sizes:
            pct = rev / total_cat_rev * 100
            bar_w = int(rev / max_rev * 100)
            size_bars.append(f"""
              <div class="trend-row">
                <span class="trend-size">{html_mod.escape(size)}</span>
                <div class="trend-bar-wrap">
                  <div class="trend-bar" style="width:{bar_w}%;background:{color}"></div>
                </div>
                <span class="trend-rev">${rev:,.0f}</span>
                <span class="trend-pct">({pct:.1f}%)</span>
              </div>""")

        cards.append(f"""
      <div class="trend-card">
        <div class="trend-cat-header" style="border-left:4px solid {color}">
          <span class="trend-cat-name">{html_mod.escape(cat)}</span>
          <span class="trend-cat-total">${total_cat_rev:,.0f} total</span>
        </div>
        {"".join(size_bars)}
      </div>""")
    return "\n".join(cards)


cat_filter_buttons = "".join(
    f'<button class="cat-filter-btn" data-pcat="{c}" onclick="setCatFilter(\'{c}\',this)">{c}</button>'
    for c in PARENT_CATS
)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ABC Parent Analysis — Nature's Seed</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #f4f6f8; color: #1a1a1a; font-size: 13px; }}

  /* Header */
  .header {{ background: #1b4332; color: #fff; padding: 18px 28px; display: flex;
             align-items: baseline; justify-content: space-between; }}
  .header h1 {{ font-size: 18px; font-weight: 700; letter-spacing: -0.3px; }}
  .header .meta {{ font-size: 12px; color: #74c69d; }}

  /* KPI cards */
  .kpi-row {{ display: flex; gap: 12px; padding: 16px 28px; flex-wrap: wrap; }}
  .kpi {{ background: #fff; border-radius: 8px; border: 1px solid #e2e8f0;
           padding: 14px 18px; flex: 1; min-width: 140px; }}
  .kpi .val {{ font-size: 22px; font-weight: 700; color: #1b4332; }}
  .kpi .lbl {{ font-size: 11px; color: #6b7280; margin-top: 2px; }}
  .kpi.kpi-a .val {{ color: #2d6a4f; }}
  .kpi.kpi-b .val {{ color: #c96a2e; }}
  .kpi.kpi-c .val {{ color: #6b7280; }}

  /* Color bar */
  .class-bars {{ display: flex; margin: 0 28px 16px; border-radius: 6px;
                 overflow: hidden; height: 8px; }}
  .cb-a {{ background: #2d6a4f; flex: {a_r}; }}
  .cb-b {{ background: #c96a2e; flex: {b_r}; }}
  .cb-c {{ background: #d1d5db; flex: {max(c_r,1)}; }}

  /* Controls */
  .controls {{ padding: 0 28px 12px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
  .controls input {{ padding: 7px 12px; border: 1px solid #d1d5db; border-radius: 6px;
                      font-size: 13px; width: 260px; outline: none; }}
  .controls input:focus {{ border-color: #2d6a4f; box-shadow: 0 0 0 2px rgba(45,106,79,.15); }}
  .filter-btns {{ display: flex; gap: 6px; }}
  .filter-btn {{ padding: 6px 14px; border-radius: 6px; border: 1px solid #d1d5db;
                  background: #fff; cursor: pointer; font-size: 12px; font-weight: 600; transition: all .15s; }}
  .filter-btn.active {{ background: #1b4332; color: #fff; border-color: #1b4332; }}
  .filter-btn.btn-a.active {{ background: #2d6a4f; border-color: #2d6a4f; }}
  .filter-btn.btn-b.active {{ background: #c96a2e; border-color: #c96a2e; }}
  .filter-btn.btn-c.active {{ background: #6b7280; border-color: #6b7280; }}
  .count-label {{ font-size: 12px; color: #6b7280; margin-left: auto; }}
  .cat-filter-btns {{ display: flex; gap: 6px; flex-wrap: wrap; }}
  .cat-filter-btn {{ padding: 5px 12px; border-radius: 20px; border: 1px solid #d1d5db;
                      background: #fff; cursor: pointer; font-size: 12px; font-weight: 500; transition: all .15s; }}
  .cat-filter-btn:hover {{ background: #f1f5f9; }}
  .cat-filter-btn.active {{ background: #1b4332; color: #fff; border-color: #1b4332; }}
  .controls-row2 {{ padding: 0 28px 14px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
  .controls-row2 label {{ font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase;
                           letter-spacing: .5px; white-space: nowrap; }}

  /* Table */
  .table-wrap {{ margin: 0 28px 28px; border-radius: 8px; overflow: hidden;
                  border: 1px solid #e2e8f0; background: #fff; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead tr {{ background: #f8fafc; border-bottom: 2px solid #e2e8f0; }}
  thead th {{ padding: 10px 12px; text-align: left; font-size: 11px; font-weight: 700;
               color: #6b7280; text-transform: uppercase; letter-spacing: .5px;
               white-space: nowrap; }}
  thead th.num {{ text-align: right; }}
  tbody tr.parent-row {{ border-bottom: 1px solid #f1f5f9; cursor: pointer; transition: background .1s; }}
  tbody tr.parent-row:hover {{ background: #f0fdf4; }}
  tbody tr.parent-row.expanded {{ background: #f0fdf4; }}
  td {{ padding: 8px 12px; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; color: #374151; }}
  td.rank {{ color: #9ca3af; font-size: 11px; width: 32px; }}
  td.sku-cell {{ font-family: 'SF Mono', 'Fira Code', monospace; font-size: 11px;
                  color: #4b5563; white-space: nowrap; }}
  td.name-cell {{ max-width: 300px; }}
  td.pct-cell {{ width: 140px; }}

  /* Expand icon */
  .expand-icon {{ display: inline-block; transition: transform .2s; font-size: 9px; color: #9ca3af; }}
  tr.parent-row.expanded .expand-icon {{ transform: rotate(90deg); color: #2d6a4f; }}

  /* Category tag */
  .cat-tag {{ font-size: 10px; color: #6b7280; margin-top: 2px; }}

  /* Badges */
  .badge-a, .badge-b, .badge-c {{
    display: inline-block; width: 22px; height: 22px; border-radius: 50%;
    text-align: center; line-height: 22px; font-weight: 700; font-size: 11px; }}
  .badge-a {{ background: #d1fae5; color: #065f46; }}
  .badge-b {{ background: #ffedd5; color: #9a3412; }}
  .badge-c {{ background: #f3f4f6; color: #6b7280; }}

  /* Progress bars */
  .bar-wrap {{ display: flex; align-items: center; gap: 6px; }}
  .bar-wrap span {{ font-size: 11px; color: #9ca3af; white-space: nowrap; }}
  .bar {{ height: 6px; border-radius: 3px; min-width: 2px; }}
  .bar-a {{ background: #2d6a4f; }}
  .bar-b {{ background: #c96a2e; }}
  .bar-c {{ background: #d1d5db; }}

  /* Variant rows */
  tr.variant-group {{ display: none; }}
  tr.variant-group.visible {{ display: table-row; }}
  tr.hidden {{ display: none !important; }}
  td.variant-container {{ padding: 0; background: #f8fffe; border-bottom: 2px solid #d1fae5; }}
  .variant-table {{ width: 100%; border-collapse: collapse; }}
  .variant-table thead tr {{ background: #ecfdf5; border-bottom: 1px solid #d1fae5; }}
  .variant-table thead th {{ padding: 6px 12px; font-size: 10px; color: #065f46; }}
  .variant-table thead th.num {{ text-align: right; }}
  tr.variant-row td {{ padding: 6px 12px; border-bottom: 1px solid #f0fdf4; font-size: 12px; }}
  tr.variant-row:last-child td {{ border-bottom: none; }}
  td.var-size {{ font-weight: 600; color: #2d6a4f; white-space: nowrap; }}
  td.var-sku {{ font-family: 'SF Mono', 'Fira Code', monospace; font-size: 10px; color: #6b7280; }}
  .var-bar-wrap {{ display: flex; align-items: center; gap: 6px; }}
  .var-bar-wrap span {{ font-size: 10px; color: #9ca3af; white-space: nowrap; }}
  .var-bar {{ height: 5px; border-radius: 3px; min-width: 2px; }}
  .var-bar-a {{ background: #52b788; }}
  .var-bar-b {{ background: #f4a261; }}
  .var-bar-c {{ background: #adb5bd; }}

  /* Sticky header */
  thead {{ position: sticky; top: 0; z-index: 10; }}

  /* Category size trends section */
  .section-heading {{ margin: 0 28px 12px; padding: 16px 0 8px;
                       border-top: 2px solid #e2e8f0; }}
  .section-heading h2 {{ font-size: 15px; font-weight: 700; color: #1b4332; }}
  .section-heading p {{ font-size: 12px; color: #6b7280; margin-top: 4px; }}
  .trends-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                   gap: 16px; margin: 0 28px 32px; }}
  .trend-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }}
  .trend-cat-header {{ display: flex; justify-content: space-between; align-items: center;
                        padding-left: 10px; margin-bottom: 12px; }}
  .trend-cat-name {{ font-size: 13px; font-weight: 700; color: #1a1a1a; }}
  .trend-cat-total {{ font-size: 11px; color: #6b7280; }}
  .trend-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }}
  .trend-size {{ font-size: 12px; font-weight: 600; color: #374151; width: 70px; flex-shrink: 0; }}
  .trend-bar-wrap {{ flex: 1; height: 8px; background: #f3f4f6; border-radius: 4px; overflow: hidden; }}
  .trend-bar {{ height: 100%; border-radius: 4px; transition: width .3s; }}
  .trend-rev {{ font-size: 11px; color: #374151; width: 60px; text-align: right; flex-shrink: 0; }}
  .trend-pct {{ font-size: 10px; color: #9ca3af; width: 48px; flex-shrink: 0; }}
</style>
</head>
<body>

<div class="header">
  <h1>ABC Parent Product Analysis &mdash; Nature&#39;s Seed</h1>
  <span class="meta">{period} &nbsp;·&nbsp; 14 days &nbsp;·&nbsp; {data['total_parent_skus']} parent SKUs</span>
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
    <div class="val">A &nbsp;{a_n} parents</div>
    <div class="lbl">${a_r:,.0f} &nbsp;·&nbsp; {a_r/total_rev*100:.1f}% of revenue</div>
  </div>
  <div class="kpi kpi-b">
    <div class="val">B &nbsp;{b_n} parents</div>
    <div class="lbl">${b_r:,.0f} &nbsp;·&nbsp; {b_r/total_rev*100:.1f}% of revenue</div>
  </div>
  <div class="kpi kpi-c">
    <div class="val">C &nbsp;{c_n} parents</div>
    <div class="lbl">${c_r:,.0f} &nbsp;·&nbsp; {c_r/total_rev*100:.1f}% of revenue</div>
  </div>
</div>

<div class="class-bars">
  <div class="cb-a" title="Class A: {a_r/total_rev*100:.1f}%"></div>
  <div class="cb-b" title="Class B: {b_r/total_rev*100:.1f}%"></div>
  <div class="cb-c" title="Class C: {c_r/total_rev*100:.1f}%"></div>
</div>

<div class="controls">
  <input type="text" id="search" placeholder="Search product or SKU…" oninput="filterTable()">
  <div class="filter-btns">
    <button class="filter-btn active" data-cls="all" onclick="setClassFilter('all',this)">All {data['total_parent_skus']}</button>
    <button class="filter-btn btn-a" data-cls="A" onclick="setClassFilter('A',this)">A &nbsp;{a_n}</button>
    <button class="filter-btn btn-b" data-cls="B" onclick="setClassFilter('B',this)">B &nbsp;{b_n}</button>
    <button class="filter-btn btn-c" data-cls="C" onclick="setClassFilter('C',this)">C &nbsp;{c_n}</button>
  </div>
  <span class="count-label" id="count-label">{data['total_parent_skus']} of {data['total_parent_skus']} products</span>
</div>
<div class="controls-row2">
  <label>Category:</label>
  <div class="cat-filter-btns">
    <button class="cat-filter-btn active" data-pcat="all" onclick="setCatFilter('all',this)">All Categories</button>
    {cat_filter_buttons}
  </div>
</div>

<div class="table-wrap">
<table id="abc-table">
  <thead>
    <tr>
      <th>#</th>
      <th>Class</th>
      <th>Base SKU</th>
      <th>Product</th>
      <th class="num">14d Units</th>
      <th class="num">14d Revenue</th>
      <th class="num">$/day</th>
      <th class="num">Units/day</th>
      <th>Rev %</th>
    </tr>
  </thead>
  <tbody id="table-body">
    {product_rows()}
  </tbody>
</table>
</div>

<div class="section-heading" style="margin-top:8px;">
  <h2>Category Size Trends</h2>
  <p>Revenue share by size variant within each product category — reveals customer purchase patterns and preferred pack sizes.</p>
</div>
<div class="trends-grid">
  {cat_trends_html()}
</div>

<script>
let activeClsFilter = 'all';
let activeCatFilter = 'all';
const TOTAL = {data['total_parent_skus']};

function collapseAll() {{
  document.querySelectorAll('.variant-group.visible').forEach(r => {{
    r.classList.remove('visible'); r.classList.add('hidden');
  }});
  document.querySelectorAll('.parent-row.expanded').forEach(r => r.classList.remove('expanded'));
}}

function setClassFilter(cls, btn) {{
  activeClsFilter = cls;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  collapseAll();
  filterTable();
}}

function setCatFilter(cat, btn) {{
  activeCatFilter = cat;
  document.querySelectorAll('.cat-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  collapseAll();
  filterTable();
}}

function filterTable() {{
  const q = document.getElementById('search').value.toLowerCase();
  const rows = document.querySelectorAll('#table-body .parent-row');
  let visible = 0;
  rows.forEach(row => {{
    const cls = row.className.match(/cls-([abc])/)?.[1] || '';
    const pcat = row.dataset.pcat || '';
    const text = row.textContent.toLowerCase();
    const clsMatch = activeClsFilter === 'all' || cls === activeClsFilter.toLowerCase();
    const catMatch = activeCatFilter === 'all' || pcat === activeCatFilter;
    const textMatch = !q || text.includes(q);
    const show = clsMatch && catMatch && textMatch;
    const pid = row.dataset.pid;
    const varGroup = document.getElementById('vars-' + pid);
    if (show) {{
      row.classList.remove('hidden');
      visible++;
    }} else {{
      row.classList.add('hidden');
      if (varGroup) {{ varGroup.classList.remove('visible'); varGroup.classList.add('hidden'); }}
    }}
  }});
  document.getElementById('count-label').textContent = visible + ' of ' + TOTAL + ' products';
}}

function toggleVariants(groupId, parentRow) {{
  const group = document.getElementById(groupId);
  if (!group) return;
  const isOpen = group.classList.contains('visible');
  if (isOpen) {{
    group.classList.remove('visible');
    group.classList.add('hidden');
    parentRow.classList.remove('expanded');
  }} else {{
    group.classList.add('visible');
    group.classList.remove('hidden');
    parentRow.classList.add('expanded');
  }}
}}
</script>
</body>
</html>"""

OUT.write_text(html)
print(f"Dashboard: {OUT}")
