#!/usr/bin/env python3
"""
Nature's Seed — MTD / YTD Performance Report
=============================================
Fetches order data from WooCommerce, computes KPIs, and generates
a branded PDF dashboard comparing current period vs same time last year.

Metrics: Sales, Orders, AOV, Unique Customers, New Customer Rate
Insights: Product best sellers, Category best sellers, California Collection trend

Output: output/NaturesSeed_Performance_Report_MTD_Mar2026.pdf
"""

import os
import time
import requests
from datetime import date, datetime
from collections import defaultdict
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import RenderStyle, Corner

# ============================================================
# CONFIG
# ============================================================
WC_BASE = 'https://naturesseed.com/wp-json/wc/v3'
WC_CK = 'ck_9629579f1379f272169de8628edddb00b24737f9'
WC_CS = 'cs_bf6dcf206d6ed26b83e55e8af62c16de26339815'

BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / 'output'
TODAY = date(2026, 3, 6)
CURRENT_YEAR = 2026
PRIOR_YEAR = 2025

# Brand colors
GREEN_PRIMARY = (45, 106, 79)
GREEN_DARK = (27, 67, 50)
GREEN_LIGHT = (64, 145, 108)
GREEN_SECONDARY = (82, 183, 136)
EARTH_SAND = (212, 163, 115)
CTA_ORANGE = (201, 106, 46)
WHITE = (255, 255, 255)
DARK_TEXT = (51, 51, 51)
LIGHT_TEXT = (120, 120, 120)
RED_DOWN = (192, 57, 43)
GREEN_UP = (39, 174, 96)

# Top-level WC category IDs
CAT_LAWN = 3881
CAT_PASTURE = 3897
CAT_WILDFLOWER = 3896
CAT_CLOVER = 4688
CAT_CALIFORNIA = 4035
CAT_COVER_CROP = 6002
CAT_FOOD_PLOT = 6000
CAT_TEXAS = 6021

# Rounded-rect corners
ALL_CORNERS = (Corner.TOP_RIGHT, Corner.TOP_LEFT,
               Corner.BOTTOM_LEFT, Corner.BOTTOM_RIGHT)

MONTH_NAMES = {1: 'January', 2: 'February', 3: 'March', 4: 'April',
               5: 'May', 6: 'June', 7: 'July', 8: 'August',
               9: 'September', 10: 'October', 11: 'November', 12: 'December'}


# ============================================================
# DATA FETCHING
# ============================================================

def fetch_orders(after_date, before_date, label=''):
    """Fetch all completed/processing orders in a date range. Returns simplified dicts."""
    print(f'  Fetching orders {label} ({after_date} to {before_date})...')
    orders = []
    page = 1
    while True:
        resp = requests.get(f'{WC_BASE}/orders', params={
            'after': f'{after_date}T00:00:00',
            'before': f'{before_date}T23:59:59',
            'status': 'completed,processing',
            'per_page': 100,
            'page': page,
        }, auth=(WC_CK, WC_CS), timeout=45)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break

        for o in batch:
            order_date = o['date_created'][:10]  # YYYY-MM-DD
            email = (o.get('billing', {}).get('email', '') or '').strip().lower()
            line_items = []
            for li in o.get('line_items', []):
                line_items.append({
                    'product_id': li.get('product_id', 0),
                    'variation_id': li.get('variation_id', 0),
                    'name': li.get('name', ''),
                    'quantity': li.get('quantity', 0),
                    'total': float(li.get('total', 0)),
                })
            orders.append({
                'id': o['id'],
                'date': order_date,
                'month': int(order_date[5:7]),
                'year': int(order_date[:4]),
                'total': float(o.get('total', 0)),
                'email': email,
                'customer_id': o.get('customer_id', 0),
                'line_items': line_items,
            })

        print(f'    Page {page}: {len(batch)} orders (total so far: {len(orders)})')
        page += 1
        time.sleep(0.15)

    print(f'    Done: {len(orders)} orders')
    return orders


def fetch_categories():
    """Fetch all WC product categories. Returns {cat_id: {name, parent}}."""
    print('  Fetching categories...')
    cats = {}
    page = 1
    while True:
        resp = requests.get(f'{WC_BASE}/products/categories',
                            params={'per_page': 100, 'page': page},
                            auth=(WC_CK, WC_CS), timeout=30)
        batch = resp.json()
        if not batch:
            break
        for c in batch:
            cats[c['id']] = {'name': c['name'], 'parent': c['parent']}
        page += 1
        time.sleep(0.15)
    print(f'    {len(cats)} categories')
    return cats


def fetch_products():
    """Fetch all products. Returns {product_id: {name, sku, category_ids}}."""
    print('  Fetching products...')
    products = {}
    for status in ['publish', 'draft']:
        page = 1
        while True:
            resp = requests.get(f'{WC_BASE}/products', params={
                'per_page': 100, 'page': page, 'status': status,
            }, auth=(WC_CK, WC_CS), timeout=30)
            data = resp.json()
            if isinstance(data, dict) and 'code' in data:
                print(f'    Warning: API error for status={status}: {data.get("message", "")}')
                break
            batch = data
            if not batch:
                break
            for p in batch:
                raw_cats = p.get('categories', [])
                cat_ids = []
                if isinstance(raw_cats, list):
                    for c in raw_cats:
                        if isinstance(c, dict) and 'id' in c:
                            cat_ids.append(c['id'])
                        elif isinstance(c, (int, str)):
                            try:
                                cat_ids.append(int(c))
                            except (ValueError, TypeError):
                                pass
                products[p['id']] = {
                    'name': p.get('name', ''),
                    'sku': p.get('sku', ''),
                    'category_ids': cat_ids,
                }
            print(f'    Page {page} ({status}): {len(batch)} products')
            page += 1
            time.sleep(0.15)
    print(f'    {len(products)} products total')
    return products


def build_category_map(categories):
    """Build cat_id → top-level category name resolver."""
    def get_root(cat_id, depth=0):
        if depth > 10 or cat_id not in categories:
            return None
        cat = categories[cat_id]
        if cat['parent'] == 0:
            return cat_id
        return get_root(cat['parent'], depth + 1)

    cat_to_root = {}
    for cid in categories:
        root = get_root(cid)
        cat_to_root[cid] = root
    return cat_to_root


def classify_product(product_info, cat_to_root):
    """Determine the primary reporting category for a product.
    Returns one of: 'Lawn', 'Pasture', 'Wildflower', 'Clover', 'Other'.
    Also returns whether it's in the California Collection.
    """
    cat_ids = product_info.get('category_ids', [])
    root_ids = {cat_to_root.get(cid) for cid in cat_ids} - {None}
    direct_ids = set(cat_ids)

    is_california = CAT_CALIFORNIA in direct_ids

    # Priority: Clover > Wildflower > Lawn > Pasture
    if CAT_CLOVER in direct_ids or CAT_CLOVER in root_ids:
        return 'Clover', is_california
    if CAT_WILDFLOWER in direct_ids or CAT_WILDFLOWER in root_ids:
        return 'Wildflower', is_california
    if CAT_LAWN in direct_ids or CAT_LAWN in root_ids:
        return 'Lawn', is_california
    if CAT_PASTURE in direct_ids or CAT_PASTURE in root_ids:
        return 'Pasture', is_california
    return 'Other', is_california


# ============================================================
# METRIC COMPUTATION
# ============================================================

def compute_metrics(orders, prior_emails=None):
    """Compute KPIs for a set of orders.
    prior_emails: set of emails from the same period last year (for new customer rate).
    """
    if not orders:
        return {'sales': 0, 'orders': 0, 'aov': 0,
                'unique_customers': 0, 'new_customer_rate': 0, 'new_customers': 0}

    total_sales = sum(o['total'] for o in orders)
    total_orders = len(orders)
    aov = total_sales / total_orders if total_orders else 0
    emails = {o['email'] for o in orders if o['email']}
    unique_customers = len(emails)

    # New customer = buyer this period who did NOT buy in same period last year
    if prior_emails is not None:
        new_emails = emails - prior_emails
        new_customers = len(new_emails)
        new_rate = (new_customers / unique_customers * 100) if unique_customers else 0
    else:
        new_customers = unique_customers
        new_rate = 100.0

    return {
        'sales': total_sales,
        'orders': total_orders,
        'aov': aov,
        'unique_customers': unique_customers,
        'new_customers': new_customers,
        'new_customer_rate': new_rate,
    }


def compute_monthly_breakdown(orders_current, orders_prior):
    """Compute metrics by month for current and prior year."""
    months_in_range = sorted(set(o['month'] for o in orders_current + orders_prior))

    current_by_month = defaultdict(list)
    prior_by_month = defaultdict(list)
    for o in orders_current:
        current_by_month[o['month']].append(o)
    for o in orders_prior:
        prior_by_month[o['month']].append(o)

    rows = []
    for m in months_in_range:
        prior_emails = {o['email'] for o in prior_by_month[m] if o['email']}
        prior_emails_current = {o['email'] for o in prior_by_month[m] if o['email']}
        current_metrics = compute_metrics(current_by_month[m], prior_emails_current)
        prior_metrics = compute_metrics(prior_by_month[m], None)
        # For prior year new customer rate, we don't have the year-before data,
        # so we'll mark it as N/A
        prior_metrics['new_customer_rate'] = None
        rows.append({
            'month': m,
            'month_name': MONTH_NAMES.get(m, f'Month {m}'),
            'current': current_metrics,
            'prior': prior_metrics,
        })
    return rows


def compute_best_sellers(orders, products_map, cat_to_root, top_n=10):
    """Compute best-selling products and category totals."""
    product_revenue = defaultdict(lambda: {'revenue': 0, 'qty': 0, 'name': ''})
    category_revenue = defaultdict(lambda: {'revenue': 0, 'orders': 0, 'qty': 0})
    california_monthly = defaultdict(lambda: {'revenue': 0, 'orders': 0})

    order_categories = defaultdict(set)

    for o in orders:
        for li in o['line_items']:
            pid = li['product_id']
            rev = li['total']
            qty = li['quantity']
            pname = li['name']

            # Clean HTML entities and unicode from name
            pname = pname.replace('&amp;', '&').replace('&#8211;', '-')
            pname = pname.replace('&ndash;', '-').replace('&#8212;', '--')
            pname = pname.replace('\u2013', '-').replace('\u2014', '--')
            pname = pname.encode('latin-1', errors='replace').decode('latin-1')

            # Product best sellers
            product_revenue[pid]['revenue'] += rev
            product_revenue[pid]['qty'] += qty
            if not product_revenue[pid]['name']:
                product_revenue[pid]['name'] = pname

            # Category classification
            pinfo = products_map.get(pid)
            if pinfo:
                cat, is_cali = classify_product(pinfo, cat_to_root)
            else:
                cat, is_cali = 'Other', False

            category_revenue[cat]['revenue'] += rev
            category_revenue[cat]['qty'] += qty
            order_categories[o['id']].add(cat)

            # California monthly
            if is_cali:
                month_key = o['month']
                california_monthly[month_key]['revenue'] += rev

        # Count orders per category (each order counted once per category)
        for cat in order_categories[o['id']]:
            category_revenue[cat]['orders'] += 1

    # Sort products by revenue
    top_products = sorted(product_revenue.items(), key=lambda x: x[1]['revenue'], reverse=True)[:top_n]

    # Category summary (only the 4 main + Other)
    cat_summary = {}
    for cat in ['Lawn', 'Pasture', 'Wildflower', 'Clover', 'Other']:
        cat_summary[cat] = category_revenue.get(cat, {'revenue': 0, 'orders': 0, 'qty': 0})

    # California monthly (sorted by month)
    cali_trend = []
    for m in sorted(california_monthly.keys()):
        cali_trend.append({
            'month': m,
            'month_name': MONTH_NAMES.get(m, ''),
            'revenue': california_monthly[m]['revenue'],
        })

    return top_products, cat_summary, cali_trend


# ============================================================
# PDF REPORT
# ============================================================

PAGE_W = 215.9
PAGE_H = 279.4
MARGIN = 12
CONTENT_W = PAGE_W - 2 * MARGIN


class PerformanceReport(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.set_auto_page_break(auto=False)
        self.set_margins(MARGIN, MARGIN, MARGIN)

    def _rr(self, x, y, w, h, r, style='DF'):
        st = RenderStyle.coerce(style)
        self._draw_rounded_rect(x, y, w, h, st, ALL_CORNERS, r)

    def _pill(self, x, y, w, h, text, fill, text_color=WHITE, fs=6, bold=True):
        r = h / 2
        self.set_fill_color(*fill)
        self.set_draw_color(*fill)
        self._rr(x, y, w, h, r, 'DF')
        self.set_xy(x, y)
        self.set_font('Helvetica', 'B' if bold else '', fs)
        self.set_text_color(*text_color)
        self.cell(w, h, text, align='C')

    def header(self):
        pass  # Custom headers per page

    def footer(self):
        if self.page_no() <= 1:
            return
        self.set_y(-8)
        self.set_font('Helvetica', '', 6)
        self.set_text_color(*LIGHT_TEXT)
        self.cell(0, 3, f'Nature\'s Seed Performance Report  |  Generated {TODAY.strftime("%B %d, %Y")}  |  Page {self.page_no()}', align='C')

    # ---- HELPER: Metric widget card ----
    def _metric_card(self, x, y, w, h, label, current_val, prior_val,
                     fmt='${:,.0f}', is_pct=False):
        """Draw a single KPI card with value + YoY change."""
        # Card background
        self.set_fill_color(248, 251, 249)
        self.set_draw_color(220, 232, 226)
        self.set_line_width(0.2)
        self._rr(x, y, w, h, 3, 'DF')

        # Label
        self.set_xy(x + 3, y + 3)
        self.set_font('Helvetica', '', 5.5)
        self.set_text_color(*LIGHT_TEXT)
        self.cell(w - 6, 3.5, label.upper(), align='L')

        # Current value
        self.set_xy(x + 3, y + 8)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(*GREEN_DARK)
        if is_pct:
            val_str = f'{current_val:.1f}%'
        else:
            val_str = fmt.format(current_val)
        self.cell(w - 6, 8, val_str, align='L')

        # Prior year value + change
        if prior_val is not None and prior_val != 0:
            if is_pct:
                change = current_val - prior_val
                change_str = f'{change:+.1f}pp'
                prior_str = f'vs {prior_val:.1f}%'
            else:
                change_pct = ((current_val - prior_val) / abs(prior_val)) * 100
                change_str = f'{change_pct:+.0f}%'
                prior_str = f'vs {fmt.format(prior_val)}'
                change = change_pct

            is_positive = current_val >= prior_val
            arrow = '+' if is_positive else ''
            color = GREEN_UP if is_positive else RED_DOWN

            # Change badge
            self.set_xy(x + 3, y + 18)
            badge_text = change_str
            badge_w = len(badge_text) * 2.5 + 6
            self._pill(x + 3, y + 18, badge_w, 5, badge_text, color, WHITE, 5)

            # Prior year text
            self.set_xy(x + 3 + badge_w + 2, y + 18)
            self.set_font('Helvetica', '', 5.5)
            self.set_text_color(*LIGHT_TEXT)
            self.cell(w - badge_w - 8, 5, prior_str, align='L')
        elif prior_val == 0:
            self.set_xy(x + 3, y + 18)
            self.set_font('Helvetica', '', 5.5)
            self.set_text_color(*LIGHT_TEXT)
            self.cell(w - 6, 5, 'vs $0 last year', align='L')

    # ---- HELPER: Section title ----
    def _section_title(self, y, title, subtitle=''):
        self.set_xy(MARGIN, y)
        self.set_font('Times', 'B', 14)
        self.set_text_color(*GREEN_DARK)
        self.cell(CONTENT_W, 7, title, align='L')
        if subtitle:
            self.set_xy(MARGIN, y + 7)
            self.set_font('Helvetica', '', 7)
            self.set_text_color(*LIGHT_TEXT)
            self.cell(CONTENT_W, 4, subtitle, align='L')
            return y + 13
        return y + 9

    # =========================================================
    # PAGE 1: MTD DASHBOARD
    # =========================================================
    def render_dashboard(self, mtd_current, mtd_prior, ytd_current, ytd_prior):
        self.add_page()

        # --- Header bar ---
        self.set_fill_color(*GREEN_DARK)
        self._rr(0, 0, PAGE_W, 36, 0, 'F')
        self.set_fill_color(*GREEN_PRIMARY)
        self.rect(0, 36, PAGE_W, 2, 'F')

        self.set_xy(MARGIN, 6)
        self.set_font('Times', 'B', 22)
        self.set_text_color(*WHITE)
        self.cell(CONTENT_W, 10, "Nature's Seed", align='L')

        self.set_xy(MARGIN, 17)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*EARTH_SAND)
        self.cell(CONTENT_W, 5, 'Performance Report', align='L')

        self.set_xy(MARGIN, 24)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(180, 200, 190)
        self.cell(CONTENT_W, 4, f'Generated {TODAY.strftime("%B %d, %Y")}  |  Data through {TODAY.strftime("%b %d")}', align='L')

        # Report period pill
        period_text = f'March 1-{TODAY.day}, {CURRENT_YEAR} vs {PRIOR_YEAR}'
        pw = len(period_text) * 2.5 + 12
        self._pill(PAGE_W - MARGIN - pw, 10, pw, 8, period_text,
                   GREEN_PRIMARY, WHITE, 6.5)

        # --- MTD Section ---
        y = 44
        y = self._section_title(y, 'Month-to-Date',
                                f'March 1-{TODAY.day}, {CURRENT_YEAR} compared to same dates in {PRIOR_YEAR}')

        # 5 metric cards
        card_w = (CONTENT_W - 4 * 3) / 5  # 5 cards with 3mm gaps
        card_h = 27
        metrics_data = [
            ('Revenue', mtd_current['sales'], mtd_prior['sales'], '${:,.0f}', False),
            ('Orders', mtd_current['orders'], mtd_prior['orders'], '{:,.0f}', False),
            ('Avg Order Value', mtd_current['aov'], mtd_prior['aov'], '${:,.2f}', False),
            ('Unique Customers', mtd_current['unique_customers'],
             mtd_prior['unique_customers'], '{:,.0f}', False),
            ('New Customer Rate', mtd_current['new_customer_rate'],
             mtd_prior.get('new_customer_rate'), None, True),
        ]
        for i, (label, curr, prior, fmt, is_pct) in enumerate(metrics_data):
            cx = MARGIN + i * (card_w + 3)
            self._metric_card(cx, y, card_w, card_h, label, curr, prior,
                              fmt=fmt or '${:,.0f}', is_pct=is_pct)

        # --- YTD Section ---
        y += card_h + 10
        y = self._section_title(y, 'Year-to-Date',
                                f'January 1 - March {TODAY.day}, {CURRENT_YEAR} compared to {PRIOR_YEAR}')

        ytd_metrics = [
            ('Revenue', ytd_current['sales'], ytd_prior['sales'], '${:,.0f}', False),
            ('Orders', ytd_current['orders'], ytd_prior['orders'], '{:,.0f}', False),
            ('Avg Order Value', ytd_current['aov'], ytd_prior['aov'], '${:,.2f}', False),
            ('Unique Customers', ytd_current['unique_customers'],
             ytd_prior['unique_customers'], '{:,.0f}', False),
            ('New Customer Rate', ytd_current['new_customer_rate'],
             ytd_prior.get('new_customer_rate'), None, True),
        ]
        for i, (label, curr, prior, fmt, is_pct) in enumerate(ytd_metrics):
            cx = MARGIN + i * (card_w + 3)
            self._metric_card(cx, y, card_w, card_h, label, curr, prior,
                              fmt=fmt or '${:,.0f}', is_pct=is_pct)

        # --- YTD Monthly Breakdown Table ---
        y += card_h + 10
        y = self._section_title(y, 'YTD Monthly Breakdown',
                                f'{CURRENT_YEAR} vs {PRIOR_YEAR} by month')
        y += 2
        self._draw_monthly_table(y, self._monthly_data)

    def _draw_monthly_table(self, y, monthly_rows):
        """Draw a comparison table: month rows, metric columns."""
        # Column definitions
        cols = [
            ('Month', 24),
            ('Year', 14),
            ('Revenue', 28),
            ('Orders', 20),
            ('AOV', 22),
            ('Customers', 24),
            ('New Cust %', 22),
        ]
        total_col_w = sum(c[1] for c in cols)
        # Scale to fit content width
        scale = CONTENT_W / total_col_w
        cols = [(name, w * scale) for name, w in cols]

        row_h = 5.5
        x_start = MARGIN

        # Header row
        self.set_fill_color(*GREEN_DARK)
        self.set_font('Helvetica', 'B', 5.5)
        self.set_text_color(*WHITE)
        cx = x_start
        for col_name, col_w in cols:
            self.set_xy(cx, y)
            self.cell(col_w, row_h + 1, col_name, align='C')
            cx += col_w
        y += row_h + 1

        # Data rows
        row_idx = 0
        for row in monthly_rows:
            for year_label, data, year in [
                (f'{CURRENT_YEAR}', row['current'], CURRENT_YEAR),
                (f'{PRIOR_YEAR}', row['prior'], PRIOR_YEAR),
            ]:
                # Alternate row bg
                if row_idx % 2 == 0:
                    self.set_fill_color(248, 251, 249)
                else:
                    self.set_fill_color(*WHITE)
                cx = x_start
                self.rect(cx, y, CONTENT_W, row_h, 'F')

                # Is this the current year row? Bold it
                is_current = (year == CURRENT_YEAR)
                font_style = 'B' if is_current else ''

                values = [
                    row['month_name'][:3],
                    str(year),
                    f"${data['sales']:,.0f}",
                    f"{data['orders']:,}",
                    f"${data['aov']:,.2f}",
                    f"{data['unique_customers']:,}",
                    f"{data['new_customer_rate']:.1f}%" if data['new_customer_rate'] is not None else '-',
                ]
                aligns = ['L', 'C', 'R', 'R', 'R', 'R', 'R']

                for i, (col_name, col_w) in enumerate(cols):
                    self.set_xy(cx + 1, y)
                    self.set_font('Helvetica', font_style, 5.5)
                    color = GREEN_DARK if is_current else DARK_TEXT
                    self.set_text_color(*color)
                    self.cell(col_w - 2, row_h, values[i], align=aligns[i])
                    cx += col_w

                y += row_h
                row_idx += 1

            # Light divider between month groups
            self.set_draw_color(220, 232, 226)
            self.set_line_width(0.15)
            self.line(x_start, y, x_start + CONTENT_W, y)

        # YTD Totals row
        y += 1
        self.set_fill_color(*GREEN_DARK)
        cx = x_start
        self.rect(cx, y, CONTENT_W, row_h + 1, 'F')
        self.set_font('Helvetica', 'B', 5.5)
        self.set_text_color(*WHITE)

        # Compute YTD totals from monthly data
        ytd_curr = {'sales': 0, 'orders': 0, 'customers': set()}
        ytd_prior = {'sales': 0, 'orders': 0, 'customers': set()}
        for row in monthly_rows:
            ytd_curr['sales'] += row['current']['sales']
            ytd_curr['orders'] += row['current']['orders']
            ytd_prior['sales'] += row['prior']['sales']
            ytd_prior['orders'] += row['prior']['orders']

        totals_curr = [
            'YTD', str(CURRENT_YEAR),
            f"${ytd_curr['sales']:,.0f}",
            f"{ytd_curr['orders']:,}",
            f"${ytd_curr['sales']/max(ytd_curr['orders'],1):,.2f}",
            '', '',
        ]
        for i, (col_name, col_w) in enumerate(cols):
            self.set_xy(cx + 1, y)
            self.cell(col_w - 2, row_h + 1, totals_curr[i], align='C' if i < 2 else 'R')
            cx += col_w

    # =========================================================
    # PAGE 2: INSIGHTS
    # =========================================================
    def render_insights(self, top_products, cat_summary, cali_trend):
        self.add_page()

        # Header
        self.set_fill_color(*GREEN_DARK)
        self._rr(MARGIN, 8, CONTENT_W, 14, 3, 'F')
        self.set_xy(MARGIN + 5, 10)
        self.set_font('Times', 'B', 13)
        self.set_text_color(*WHITE)
        self.cell(CONTENT_W - 10, 10, 'Insights & Best Sellers', align='L')
        self._pill(PAGE_W - MARGIN - 42, 12, 38, 7,
                   f'YTD {CURRENT_YEAR}', GREEN_PRIMARY, EARTH_SAND, 6)

        # ---- Insight 1: Top 10 Products ----
        y = 28
        y = self._section_title(y, 'Top 10 Products by Revenue')
        y += 1

        # Table header
        prod_cols = [('Rank', 10), ('Product', 80), ('Revenue', 30),
                     ('Qty Sold', 22), ('Share', 20)]
        scale = (CONTENT_W * 0.6) / sum(c[1] for c in prod_cols)
        prod_cols = [(n, w * scale) for n, w in prod_cols]
        row_h = 5

        total_rev = sum(p[1]['revenue'] for p in top_products) if top_products else 1
        all_rev = sum(p[1]['revenue'] for p in top_products)

        self.set_fill_color(*GREEN_DARK)
        cx = MARGIN
        for col_name, col_w in prod_cols:
            self.set_xy(cx, y)
            self.set_font('Helvetica', 'B', 5)
            self.set_text_color(*WHITE)
            self.cell(col_w, row_h, col_name, align='C')
            cx += col_w
        y += row_h

        for rank, (pid, pdata) in enumerate(top_products, 1):
            bg = (248, 251, 249) if rank % 2 == 0 else WHITE
            self.set_fill_color(*bg)
            cx = MARGIN
            table_w = sum(c[1] for c in prod_cols)
            self.rect(cx, y, table_w, row_h, 'F')

            name = pdata['name']
            # Clean up long variation names and HTML entities
            if ' - ' in name:
                name = name.split(' - ')[0]
            name = name.replace('&#8211;', '-').replace('&amp;', '&')
            name = name.replace('&ndash;', '-').replace('&#8212;', '--')
            name = name.replace('\u2013', '-').replace('\u2014', '--')
            name = name.encode('latin-1', errors='replace').decode('latin-1')
            if len(name) > 42:
                name = name[:40] + '...'

            share = (pdata['revenue'] / all_rev * 100) if all_rev else 0
            values = [
                str(rank),
                name,
                f"${pdata['revenue']:,.0f}",
                f"{pdata['qty']:,}",
                f"{share:.1f}%",
            ]
            aligns = ['C', 'L', 'R', 'R', 'R']

            for i, (col_name, col_w) in enumerate(prod_cols):
                self.set_xy(cx + 1, y)
                style = 'B' if rank <= 3 else ''
                self.set_font('Helvetica', style, 5)
                self.set_text_color(*DARK_TEXT)
                self.cell(col_w - 2, row_h, values[i], align=aligns[i])
                cx += col_w
            y += row_h

        # ---- Insight 1b: Category Best Sellers (right side) ----
        cat_x = MARGIN + sum(c[1] for c in prod_cols) + 8
        cat_w = CONTENT_W - (cat_x - MARGIN)
        cat_y = 28
        cat_y = 37  # Same starting y as products table

        self.set_xy(cat_x, 28)
        self.set_font('Times', 'B', 11)
        self.set_text_color(*GREEN_DARK)
        self.cell(cat_w, 6, 'Revenue by Category')

        cat_y = 36
        # Find max revenue for bar scaling
        main_cats = ['Lawn', 'Pasture', 'Wildflower', 'Clover']
        max_rev = max((cat_summary.get(c, {}).get('revenue', 0) for c in main_cats), default=1)
        total_cat_rev = sum(cat_summary.get(c, {}).get('revenue', 0) for c in main_cats)

        bar_h = 9
        bar_max_w = cat_w - 4
        cat_colors = {
            'Lawn': (76, 175, 80),
            'Pasture': (139, 195, 74),
            'Wildflower': (255, 167, 38),
            'Clover': (102, 187, 106),
        }

        for cat_name in main_cats:
            data = cat_summary.get(cat_name, {'revenue': 0, 'orders': 0, 'qty': 0})
            rev = data['revenue']
            orders = data['orders']
            share = (rev / total_cat_rev * 100) if total_cat_rev else 0

            # Category label
            self.set_xy(cat_x, cat_y)
            self.set_font('Helvetica', 'B', 6)
            self.set_text_color(*GREEN_DARK)
            self.cell(cat_w, 4, cat_name)
            cat_y += 4

            # Revenue bar
            bar_w = (rev / max_rev) * bar_max_w if max_rev else 0
            bar_w = max(bar_w, 2)
            self.set_fill_color(*cat_colors.get(cat_name, GREEN_PRIMARY))
            self._rr(cat_x, cat_y, bar_w, 5, 2.5, 'F')

            # Revenue text on bar
            rev_text = f'${rev:,.0f}  ({share:.0f}%)'
            self.set_xy(cat_x + bar_w + 2, cat_y)
            self.set_font('Helvetica', '', 5)
            self.set_text_color(*DARK_TEXT)
            self.cell(cat_w - bar_w - 4, 5, rev_text, align='L')

            # Orders count below bar
            self.set_xy(cat_x, cat_y + 5)
            self.set_font('Helvetica', '', 4.5)
            self.set_text_color(*LIGHT_TEXT)
            self.cell(cat_w, 3, f'{orders:,} orders  |  {data["qty"]:,} units')
            cat_y += bar_h + 3

        # ---- Insight 2: California Collection Trend ----
        y = max(y, cat_y) + 8
        y = self._section_title(y, 'California Collection - YTD Monthly Trend',
                                f'Revenue from California Collection products, {CURRENT_YEAR}')
        y += 2

        if cali_trend:
            max_cali = max((m['revenue'] for m in cali_trend), default=1)
            bar_area_w = CONTENT_W - 40
            bar_height = 14

            for entry in cali_trend:
                # Month label
                self.set_xy(MARGIN, y + 2)
                self.set_font('Helvetica', 'B', 7)
                self.set_text_color(*GREEN_DARK)
                self.cell(22, bar_height - 4, entry['month_name'][:3], align='R')

                # Bar
                bw = (entry['revenue'] / max_cali) * bar_area_w if max_cali else 0
                bw = max(bw, 3)
                self.set_fill_color(*EARTH_SAND)
                self._rr(MARGIN + 24, y + 2, bw, bar_height - 4, 3, 'F')

                # Revenue label
                self.set_xy(MARGIN + 26 + bw, y + 2)
                self.set_font('Helvetica', 'B', 7)
                self.set_text_color(*DARK_TEXT)
                self.cell(40, bar_height - 4, f'${entry["revenue"]:,.0f}', align='L')

                y += bar_height
        else:
            self.set_xy(MARGIN, y)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(*LIGHT_TEXT)
            self.cell(CONTENT_W, 6, 'No California Collection sales data for this period.')


# ============================================================
# MAIN
# ============================================================

def main():
    print('=' * 60)
    print("Nature's Seed — MTD/YTD Performance Report")
    print('=' * 60)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Phase 1: Fetch data ----
    print('\n[Phase 1] Fetching data from WooCommerce...')

    categories = fetch_categories()
    products = fetch_products()
    cat_to_root = build_category_map(categories)

    # Current year YTD
    orders_current = fetch_orders('2026-01-01', '2026-03-06', label='2026 YTD')

    # Prior year same period
    orders_prior = fetch_orders('2025-01-01', '2025-03-06', label='2025 YTD')

    # Historical emails for new customer rate (2024 full year)
    orders_2024 = fetch_orders('2024-01-01', '2024-12-31', label='2024 (historical)')
    emails_2024 = {o['email'] for o in orders_2024 if o['email']}

    # Also get 2025 Apr-Dec emails for better 2026 new customer check
    orders_2025_rest = fetch_orders('2025-03-07', '2025-12-31', label='2025 Apr-Dec (historical)')
    emails_2025_full = {o['email'] for o in orders_prior if o['email']} | \
                       {o['email'] for o in orders_2025_rest if o['email']}

    print(f'\n  Total orders fetched: {len(orders_current) + len(orders_prior) + len(orders_2024) + len(orders_2025_rest)}')

    # ---- Phase 2: Compute metrics ----
    print('\n[Phase 2] Computing metrics...')

    # MTD = March only
    mtd_current_orders = [o for o in orders_current if o['month'] == 3]
    mtd_prior_orders = [o for o in orders_prior if o['month'] == 3]

    # Historical emails for new customer calculations
    hist_pre_2025 = emails_2024
    hist_pre_2026 = emails_2024 | emails_2025_full

    # Emails from Jan-Feb of each year (for MTD new customer check)
    emails_curr_jan_feb = {o['email'] for o in orders_current if o['month'] < 3 and o['email']}
    emails_prior_jan_feb = {o['email'] for o in orders_prior if o['month'] < 3 and o['email']}

    # MTD metrics
    mtd_prior_emails = hist_pre_2025 | emails_prior_jan_feb
    mtd_current_emails = hist_pre_2026 | emails_curr_jan_feb
    mtd_current = compute_metrics(mtd_current_orders, mtd_current_emails)
    mtd_prior = compute_metrics(mtd_prior_orders, mtd_prior_emails)

    # YTD metrics
    ytd_current = compute_metrics(orders_current, hist_pre_2026)
    ytd_prior = compute_metrics(orders_prior, hist_pre_2025)

    # Monthly breakdown
    monthly = compute_monthly_breakdown(orders_current, orders_prior)

    # Best sellers (current year only)
    top_products, cat_summary, cali_trend = compute_best_sellers(
        orders_current, products, cat_to_root
    )

    # Print summary
    print(f'\n  MTD {CURRENT_YEAR}: ${mtd_current["sales"]:,.0f} revenue, {mtd_current["orders"]} orders')
    print(f'  MTD {PRIOR_YEAR}: ${mtd_prior["sales"]:,.0f} revenue, {mtd_prior["orders"]} orders')
    print(f'  YTD {CURRENT_YEAR}: ${ytd_current["sales"]:,.0f} revenue, {ytd_current["orders"]} orders')
    print(f'  YTD {PRIOR_YEAR}: ${ytd_prior["sales"]:,.0f} revenue, {ytd_prior["orders"]} orders')

    # ---- Phase 3: Generate PDF ----
    print('\n[Phase 3] Generating PDF...')

    report = PerformanceReport()
    report._monthly_data = monthly  # pass to the table renderer

    report.render_dashboard(mtd_current, mtd_prior, ytd_current, ytd_prior)
    print('  [done] Dashboard page')

    report.render_insights(top_products, cat_summary, cali_trend)
    print('  [done] Insights page')

    output_path = OUT_DIR / f'NaturesSeed_Performance_Report_MTD_Mar{CURRENT_YEAR}.pdf'
    report.output(str(output_path))

    print(f'\nPDF saved to: {output_path}')
    print(f'Total pages: {report.page_no()}')
    print('=' * 60)
    return str(output_path)


if __name__ == '__main__':
    main()
