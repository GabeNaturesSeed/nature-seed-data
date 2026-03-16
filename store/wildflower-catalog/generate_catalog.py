#!/usr/bin/env python3
"""
Nature's Seed — Wildflower Seed Catalog PDF Generator
=====================================================

Fetches all 16 single-species wildflower products from WooCommerce,
downloads product images + logo, and generates a branded PDF catalog.

Layout: Organic menu-style — 4 products per page with rounded cards,
pill badges, image overlays, and modern visual design.

Output: output/NaturesSeed_Wildflower_Catalog_2026.pdf

Requirements: fpdf2, Pillow, requests, beautifulsoup4
"""

import os
import re
import sys
import time
import json
import textwrap
import requests
from io import BytesIO
from datetime import date
from pathlib import Path
from html import unescape

from fpdf import FPDF
from fpdf.enums import RenderStyle, Corner
from PIL import Image
from bs4 import BeautifulSoup

# All four corners for rounded_rect
ALL_CORNERS = (Corner.TOP_RIGHT, Corner.TOP_LEFT, Corner.BOTTOM_LEFT, Corner.BOTTOM_RIGHT)

# ============================================================
# CONFIG
# ============================================================
WC_BASE = 'https://naturesseed.com/wp-json/wc/v3'
WC_CK = 'ck_9629579f1379f272169de8628edddb00b24737f9'
WC_CS = 'cs_bf6dcf206d6ed26b83e55e8af62c16de26339815'

LOGO_URL = 'https://naturesseed.com/wp-content/themes/GSNature%20V1/assets/images/NSlogo.png'
WILDFLOWER_CATEGORY = 3896  # "Native Wildflower Seed & Seed Mixes"

BASE_DIR = Path(__file__).parent
IMG_DIR = BASE_DIR / 'data' / 'images'
OUT_DIR = BASE_DIR / 'output'
OUTPUT_PDF = OUT_DIR / 'NaturesSeed_Wildflower_Catalog_2026.pdf'

# Brand colors (RGB)
GREEN_PRIMARY = (45, 106, 79)      # #2d6a4f
GREEN_DARK = (27, 67, 50)          # #1b4332
GREEN_LIGHT = (64, 145, 108)       # #40916c
GREEN_SECONDARY = (82, 183, 136)   # #52b788
EARTH_SAND = (212, 163, 115)       # #d4a373
CTA_ORANGE = (201, 106, 46)        # #C96A2E
WHITE = (255, 255, 255)
DARK_TEXT = (51, 51, 51)
LIGHT_TEXT = (120, 120, 120)
LIGHTEST_TEXT = (180, 180, 180)
CARD_BG = (248, 251, 249)          # very light green-tint bg
CARD_BORDER = (220, 232, 226)      # subtle green-gray border

# SKUs that are MIXES (exclude from single-species catalog)
MIX_SKUS = {'WB-TEXN', 'WB-TXPB', 'WB-CANA', 'WB-CAPO', 'WB-CASE',
            'WB-CABU', 'WB-CAER', 'WB-CAEN', 'WB-CASC', 'WB-CAFW',
            'PB-TXPR', 'TURF-TXN'}

# ACF field keys for product data
ACF_FIELDS = {
    'description': 'product_content_2',
    'scientific_name': 'scientific_name',
    'sun': 'sun_requirements',
    'height': 'height_when_mature',
    'germination': 'days_to_maturity',
    'seeding_rate': 'seeding_rate',
    'planting_depth': 'planting_depth',
    'soil': 'soil_preference',
    'color': 'detail_5_color',
    'water': 'detail_5_water',
    'native': 'detail_5_native',
    'uses': 'detail_5_uses',
}


# ============================================================
# DATA PIPELINE
# ============================================================

def sanitize_for_latin1(text):
    """Replace Unicode characters with Latin-1 safe equivalents for built-in fonts."""
    if not text:
        return ''
    replacements = {
        '\u2013': '-',   # en-dash
        '\u2014': '--',  # em-dash
        '\u2018': "'",   # left single quote
        '\u2019': "'",   # right single quote
        '\u201c': '"',   # left double quote
        '\u201d': '"',   # right double quote
        '\u2026': '...', # ellipsis
        '\u2022': '-',   # bullet
        '\u00a0': ' ',   # non-breaking space
        '\u2032': "'",   # prime
        '\u2033': '"',   # double prime
        '\u00b0': ' deg',# degree sign
        '\u00ae': '(R)', # registered
        '\u2122': '(TM)',# trademark
        '\u00bd': '1/2', # fraction half
        '\u00bc': '1/4', # fraction quarter
        '\u00be': '3/4', # fraction three-quarters
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    # Fallback: strip any remaining non-latin1 characters
    text = text.encode('latin-1', errors='replace').decode('latin-1')
    return text


def strip_html(html_text):
    """Remove HTML tags and decode entities, return clean text."""
    if not html_text:
        return ''
    soup = BeautifulSoup(html_text, 'html.parser')
    text = soup.get_text(separator=' ')
    text = unescape(text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Make safe for built-in PDF fonts
    text = sanitize_for_latin1(text)
    return text


def fetch_products():
    """Fetch all published wildflower products from WC REST API."""
    print('Fetching wildflower products from WooCommerce...')
    products = []
    page = 1
    while True:
        url = f'{WC_BASE}/products'
        params = {
            'category': str(WILDFLOWER_CATEGORY),
            'status': 'publish',
            'per_page': 50,
            'page': page,
        }
        resp = requests.get(url, params=params, auth=(WC_CK, WC_CS), timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        products.extend(batch)
        print(f'  Page {page}: {len(batch)} products')
        page += 1
        time.sleep(0.3)

    print(f'  Total fetched: {len(products)}')
    return products


def is_single_species(product):
    """Determine if a product is a single species (not a mix)."""
    sku = product.get('sku', '')
    name = product.get('name', '').lower()

    # Check SKU against known mix prefixes
    sku_prefix = sku.split('-')[0] + '-' + sku.split('-')[1] if '-' in sku and len(sku.split('-')) > 1 else sku
    if sku_prefix in MIX_SKUS:
        return False

    # Check name for mix indicators
    mix_words = ['mix', 'blend', 'collection', 'combo', 'lawn', 'turf', 'prairie', 'pasture']
    if any(w in name for w in mix_words):
        return False

    # Single-species wildflower SKUs start with 'W-'
    if sku.startswith('W-'):
        return True

    return False


def get_acf_field(product, field_key):
    """Extract an ACF field value from product meta_data."""
    for meta in product.get('meta_data', []):
        if meta.get('key') == field_key:
            val = meta.get('value', '')
            if isinstance(val, str):
                return strip_html(val)
            return str(val) if val else ''
    return ''


def normalize_product(product):
    """Extract all needed fields from a WC product into a clean dict."""
    # Get prices from variations or base product
    price_range = ''
    sizes = []
    if product.get('type') == 'variable' and product.get('variations'):
        # Fetch variation data
        var_prices = []
        pid = product['id']
        try:
            resp = requests.get(
                f'{WC_BASE}/products/{pid}/variations',
                params={'per_page': 20},
                auth=(WC_CK, WC_CS), timeout=30
            )
            resp.raise_for_status()
            variations = resp.json()
            for v in variations:
                p = v.get('price', '')
                if p:
                    var_prices.append(float(p))
                # Get size from attributes
                for attr in v.get('attributes', []):
                    if attr.get('name', '').lower() in ('size', 'weight', 'pa_size'):
                        sizes.append(attr.get('option', ''))
            if var_prices:
                price_range = f'${min(var_prices):.2f} - ${max(var_prices):.2f}'
            time.sleep(0.3)
        except Exception as e:
            print(f'  Warning: Could not fetch variations for {product["name"]}: {e}')

    if not price_range:
        p = product.get('price', '')
        if p:
            price_range = f'${float(p):.2f}'

    # Get image URL
    images = product.get('images', [])
    image_url = images[0]['src'] if images else ''

    return {
        'id': product['id'],
        'name': product.get('name', ''),
        'sku': product.get('sku', ''),
        'slug': product.get('slug', ''),
        'price_range': price_range,
        'image_url': image_url,
        'scientific_name': get_acf_field(product, ACF_FIELDS['scientific_name']),
        'description': get_acf_field(product, ACF_FIELDS['description']),
        'sun': get_acf_field(product, ACF_FIELDS['sun']),
        'height': get_acf_field(product, ACF_FIELDS['height']),
        'germination': get_acf_field(product, ACF_FIELDS['germination']),
        'seeding_rate': get_acf_field(product, ACF_FIELDS['seeding_rate']),
        'planting_depth': get_acf_field(product, ACF_FIELDS['planting_depth']),
        'soil': get_acf_field(product, ACF_FIELDS['soil']),
        'color': get_acf_field(product, ACF_FIELDS['color']),
        'water': get_acf_field(product, ACF_FIELDS['water']),
        'native': get_acf_field(product, ACF_FIELDS['native']),
        'uses': get_acf_field(product, ACF_FIELDS['uses']),
        'sizes': sizes,
        'url': product.get('permalink', f'https://naturesseed.com/product/{product.get("slug", "")}'),
    }


def download_image(url, filename):
    """Download an image and save it to IMG_DIR. Returns local path or None."""
    if not url:
        return None
    filepath = IMG_DIR / filename
    if filepath.exists():
        print(f'  [cached] {filename}')
        return str(filepath)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        # Convert to RGB JPEG for consistent PDF embedding
        img = Image.open(BytesIO(resp.content))
        if img.mode in ('RGBA', 'P', 'LA'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                bg.paste(img, mask=img.split()[-1])
            else:
                bg.paste(img)
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        max_dim = 800
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)

        img.save(str(filepath), 'JPEG', quality=85)
        print(f'  [downloaded] {filename}')
        return str(filepath)
    except Exception as e:
        print(f'  [error] {filename}: {e}')
        return None


def download_all_images(products):
    """Download product images and logo."""
    print('\nDownloading images...')

    # Logo — keep original PNG for transparency on dark backgrounds
    logo_path = str(IMG_DIR / 'logo.png')
    if not (IMG_DIR / 'logo.png').exists():
        try:
            resp = requests.get(LOGO_URL, timeout=30)
            resp.raise_for_status()
            with open(logo_path, 'wb') as f:
                f.write(resp.content)
            print(f'  [downloaded] logo.png')
        except Exception as e:
            print(f'  [error] logo.png: {e}')
            logo_path = None
    else:
        print(f'  [cached] logo.png')

    # Product images
    for p in products:
        if p['image_url']:
            fname = f"product_{p['id']}.jpg"
            img_path = download_image(p['image_url'], fname)
            p['image_local'] = img_path
        else:
            p['image_local'] = None
        time.sleep(0.3)

    return logo_path


# ============================================================
# PDF CATALOG — Organic Visual Design
# ============================================================

# Layout constants (Letter: 215.9 x 279.4 mm)
MARGIN = 15
PAGE_W = 215.9
PAGE_H = 279.4
CONTENT_W = PAGE_W - 2 * MARGIN  # ~185.9mm

# Product card dimensions — tuned for 4 per page, organic feel
CARD_H = 58          # total card height
CARD_PAD = 3         # padding inside card
CARD_GAP = 2.5       # gap between cards
CORNER_R = 3         # rounded corner radius for cards
PILL_R = 2.5         # pill badge corner radius

# Image dimensions within card
IMG_W = 48           # product image width
IMG_H = 40           # product image height
OVERLAY_H = 13       # dark overlay at bottom of image for title

# Column layout
DESC_W = 70          # description column width
INFO_W = CONTENT_W - IMG_W - CARD_PAD * 3 - DESC_W  # middle info column


class WildflowerCatalog(FPDF):
    """Branded PDF catalog with organic, modern visual design."""

    def __init__(self, logo_path=None):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.logo_path = logo_path
        self.set_auto_page_break(auto=False)
        self.alias_nb_pages()
        self.set_margins(MARGIN, MARGIN, MARGIN)

    # --- Helpers ---

    def _rounded_rect(self, x, y, w, h, r, style='DF'):
        """Draw a rectangle with rounded corners using fpdf2 internal API."""
        st = RenderStyle.coerce(style)
        self._draw_rounded_rect(x, y, w, h, st, ALL_CORNERS, r)

    def _pill(self, x, y, w, h, text, fill_color, text_color=(255, 255, 255),
              font_size=5.5, bold=False):
        """Draw a pill-shaped badge with centered text."""
        r = h / 2  # full half-circle ends
        self.set_fill_color(*fill_color)
        self.set_draw_color(*fill_color)
        self._rounded_rect(x, y, w, h, r, style='DF')
        self.set_xy(x, y)
        self.set_font('Helvetica', 'B' if bold else '', font_size)
        self.set_text_color(*text_color)
        self.cell(w, h, text, align='C')

    def _rounded_card(self, x, y, w, h, fill=CARD_BG, border_color=CARD_BORDER):
        """Draw a card with rounded corners and subtle border."""
        self.set_fill_color(*fill)
        self.set_draw_color(*border_color)
        self.set_line_width(0.25)
        self._rounded_rect(x, y, w, h, CORNER_R, style='DF')

    # --- Header / Footer ---

    def header(self):
        if self.page_no() <= 1:
            return  # No header on cover
        self.set_font('Helvetica', '', 7)
        self.set_text_color(*LIGHT_TEXT)
        self.set_y(6)
        self.cell(0, 4, "Nature's Seed  |  Wildflower Seed Catalog  |  Spring 2026", align='C')
        # Subtle line
        self.set_draw_color(*GREEN_LIGHT)
        self.set_line_width(0.15)
        self.line(MARGIN + 10, 11.5, PAGE_W - MARGIN - 10, 11.5)

    def footer(self):
        if self.page_no() <= 1:
            return
        self.set_y(-10)
        self.set_font('Helvetica', '', 6.5)
        self.set_text_color(*LIGHT_TEXT)
        self.cell(0, 4, 'naturesseed.com  |  customercare@naturesseed.com  |  801-531-1456', align='L')
        self.set_x(MARGIN)
        self.cell(0, 4, f'Page {self.page_no()} of {{nb}}', align='R')

    # =========================================================
    # COVER PAGE — warm, organic, inviting
    # =========================================================

    def render_cover_page(self):
        self.add_page()

        # Full-page dark green background
        self.set_fill_color(*GREEN_DARK)
        self.rect(0, 0, PAGE_W, PAGE_H, 'F')

        # Top accent — gradient-like with two thin strips
        self.set_fill_color(*GREEN_PRIMARY)
        self.rect(0, 0, PAGE_W, 3, 'F')
        self.set_fill_color(*GREEN_LIGHT)
        self.rect(0, 3, PAGE_W, 1.5, 'F')

        # Logo — centered, prominent
        y = 30
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                logo_w = 65
                self.image(self.logo_path, x=(PAGE_W - logo_w) / 2, y=y, w=logo_w)
                y += 40
            except Exception:
                y += 10

        # Season pill badge
        y += 4
        pill_w = 50
        self._pill((PAGE_W - pill_w) / 2, y, pill_w, 8, 'SPRING 2026',
                    GREEN_PRIMARY, EARTH_SAND, font_size=7, bold=True)
        y += 16

        # Title
        self.set_y(y)
        self.set_font('Times', 'B', 32)
        self.set_text_color(*WHITE)
        self.cell(0, 13, 'Wildflower Seed', align='C')
        self.ln(14)
        self.cell(0, 13, 'Catalog', align='C')
        self.ln(18)

        # Gold accent line — short, elegant
        mid = PAGE_W / 2
        self.set_draw_color(*EARTH_SAND)
        self.set_line_width(0.6)
        self.line(mid - 30, self.get_y(), mid + 30, self.get_y())
        self.ln(12)

        # Semi-transparent intro panel
        panel_x = 30
        panel_w = PAGE_W - 2 * panel_x
        panel_y = self.get_y()
        panel_h = 32
        with self.local_context(fill_opacity=0.15):
            self.set_fill_color(*GREEN_SECONDARY)
            self._rounded_rect(panel_x, panel_y, panel_w, panel_h, 4, style='F')

        # Intro text inside panel
        self.set_xy(panel_x + 6, panel_y + 4)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(210, 225, 218)
        self.multi_cell(panel_w - 12, 5,
            "For over a decade, our family-owned team in Lehi, Utah has been "
            "helping gardeners, ranchers, and land stewards grow something beautiful. "
            "Every seed we sell is tested for purity and germination so you can "
            "plant with confidence.",
            align='C'
        )
        self.set_y(panel_y + panel_h + 10)

        # Tagline
        self.set_font('Times', 'I', 22)
        self.set_text_color(*GREEN_SECONDARY)
        self.cell(0, 10, 'Seed You Can Trust', align='C')
        self.ln(18)

        # Trust pills row
        trust_items = [
            'Free Shipping $150+',
            'Satisfaction Guaranteed',
            'Family Owned',
            'Expert Support',
        ]
        total_pill_w = 42 * len(trust_items) + 3 * (len(trust_items) - 1)
        start_x = (PAGE_W - total_pill_w) / 2
        pill_y = self.get_y()
        for i, item in enumerate(trust_items):
            px = start_x + i * (42 + 3)
            with self.local_context(fill_opacity=0.25):
                self.set_fill_color(*GREEN_LIGHT)
                self._rounded_rect(px, pill_y, 42, 7, 3.5, style='F')
            self.set_xy(px, pill_y)
            self.set_font('Helvetica', '', 5.5)
            self.set_text_color(*WHITE)
            self.cell(42, 7, item, align='C')
        self.set_y(pill_y + 14)

        # Delivery pill
        deliv_w = 72
        self._pill((PAGE_W - deliv_w) / 2, self.get_y(), deliv_w, 8,
                    '4-7 Business Day Delivery', GREEN_PRIMARY, EARTH_SAND,
                    font_size=6.5, bold=True)
        self.ln(22)

        # Contact info
        self.set_font('Helvetica', '', 8)
        self.set_text_color(140, 165, 155)
        self.cell(0, 5, 'www.naturesseed.com  |  customercare@naturesseed.com  |  801-531-1456', align='C')
        self.ln(5)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(110, 135, 125)
        self.cell(0, 4, '1697 W 2100 N, Lehi, UT 84043', align='C')

        # Bottom accent
        self.set_fill_color(*GREEN_PRIMARY)
        self.rect(0, PAGE_H - 3, PAGE_W, 1.5, 'F')
        self.set_fill_color(*GREEN_LIGHT)
        self.rect(0, PAGE_H - 1.5, PAGE_W, 1.5, 'F')

    # =========================================================
    # PRODUCT CARDS — organic, rounded, modern
    # =========================================================

    def render_product_pages(self, products):
        """Render all products in organic card layout, 4 per page."""
        y_cursor = 0
        cards_on_page = 0

        for i, product in enumerate(products):
            # Check if we need a new page
            if cards_on_page == 0 or (y_cursor + CARD_H) > (PAGE_H - 12):
                self.add_page()
                y_cursor = 14  # below header line
                cards_on_page = 0

            self._draw_product_card(product, y_cursor)
            y_cursor += CARD_H + CARD_GAP
            cards_on_page += 1

    def _draw_product_card(self, product, y_top):
        """
        Draw one organic product card at y_top.

        Layout:
        +--------------------------------------------+
        | [Image with title  ] | Info col | Desc col |
        | [overlay at bottom ] | Price    | (text)   |
        |                      | Sizes    |          |
        +-- Spec pills row ---  --- ----- --- -------+
        """
        x_left = MARGIN
        full_w = CONTENT_W

        # --- Rounded card background ---
        self._rounded_card(x_left, y_top, full_w, CARD_H)

        # --- Subtle left accent: thin rounded bar ---
        self.set_fill_color(*GREEN_PRIMARY)
        self._rounded_rect(x_left + 1.5, y_top + 4, 1.8, CARD_H - 8, 0.9, style='F')

        # Positions
        img_x = x_left + CARD_PAD + 3
        img_y = y_top + CARD_PAD
        info_x = img_x + IMG_W + CARD_PAD + 1
        desc_x = info_x + INFO_W + 2
        desc_right = x_left + full_w - CARD_PAD

        # Specs row at bottom
        spec_row_h = 9
        top_section_h = CARD_H - spec_row_h
        specs_y = y_top + top_section_h

        # ====== PRODUCT IMAGE with overlay ======
        img_drawn = False
        if product.get('image_local') and os.path.exists(product['image_local']):
            try:
                # Clip image to rounded rect area
                self.image(product['image_local'], x=img_x, y=img_y,
                           w=IMG_W, h=IMG_H)
                img_drawn = True
            except Exception:
                pass

        if not img_drawn:
            # Placeholder
            self.set_fill_color(230, 235, 232)
            self._rounded_rect(img_x, img_y, IMG_W, IMG_H, 2, style='F')
            self.set_font('Helvetica', 'I', 7)
            self.set_text_color(*LIGHT_TEXT)
            self.set_xy(img_x, img_y + IMG_H / 2 - 2)
            self.cell(IMG_W, 4, 'No image', align='C')

        # --- Dark overlay on bottom of image with product name ---
        overlay_y = img_y + IMG_H - OVERLAY_H
        with self.local_context(fill_opacity=0.7):
            self.set_fill_color(20, 20, 20)
            self.rect(img_x, overlay_y, IMG_W, OVERLAY_H, 'F')

        # Product name on overlay — white, bold, full name always shown
        name = product['name']
        self.set_xy(img_x + 2, overlay_y + 1)
        self.set_font('Times', 'B', 8.5)
        self.set_text_color(*WHITE)
        self.multi_cell(IMG_W - 4, 4, name, align='L')

        # Scientific name under overlay — full name, smaller font if needed
        sci = product.get('scientific_name', '')
        if sci:
            sci_y = img_y + IMG_H + 0.5
            self.set_xy(img_x, sci_y)
            font_sz = 5.5 if len(sci) > 28 else 6
            self.set_font('Times', 'I', font_sz)
            self.set_text_color(*LIGHT_TEXT)
            self.cell(IMG_W, 3, sci, align='C')

        # ====== INFO COLUMN: Price + Delivery + Sizes ======
        cy = y_top + CARD_PAD + 1
        info_inner_w = INFO_W

        # Price — orange pill
        price = product.get('price_range', '')
        if price:
            # Determine pill width based on price length
            price_pill_w = min(len(price) * 3.8 + 8, info_inner_w - 2)
            self._pill(info_x, cy, price_pill_w, 7, price,
                       CTA_ORANGE, WHITE, font_size=7, bold=True)
            cy += 10

        # Delivery badge — green pill
        deliv_w = min(48, info_inner_w - 2)
        self._pill(info_x, cy, deliv_w, 6, '4-7 Day Delivery',
                   GREEN_PRIMARY, WHITE, font_size=5.5, bold=True)
        cy += 9

        # Available sizes
        sizes = product.get('sizes', [])
        if sizes:
            self.set_xy(info_x, cy)
            self.set_font('Helvetica', 'B', 5)
            self.set_text_color(*GREEN_DARK)
            self.cell(info_inner_w, 3.5, 'AVAILABLE SIZES')
            cy += 4
            self.set_xy(info_x, cy)
            self.set_font('Helvetica', '', 5.5)
            self.set_text_color(*DARK_TEXT)
            for s in sizes[:4]:
                if cy + 3.5 >= specs_y - 1:
                    break
                self.set_xy(info_x + 1, cy)
                if len(s) > 30:
                    s = s[:28] + '..'
                self.cell(info_inner_w - 2, 3.5, f'  {s}')
                cy += 3.5

        # Shop link
        link_y = specs_y - 5
        if link_y > cy + 1:
            self.set_xy(info_x, link_y)
            self.set_font('Helvetica', '', 4.5)
            self.set_text_color(*GREEN_LIGHT)
            self.cell(info_inner_w, 3, 'Shop at naturesseed.com')

        # ====== DESCRIPTION COLUMN ======
        desc = product.get('description', '')
        if desc:
            # Truncate to fit card but try to break at sentence boundaries
            max_chars = 420
            if len(desc) > max_chars:
                # Try to break at a sentence ending (period + space)
                truncated = desc[:max_chars]
                last_period = truncated.rfind('. ')
                if last_period > max_chars * 0.5:
                    desc = truncated[:last_period + 1]
                else:
                    # Fall back to word break
                    desc = truncated.rsplit(' ', 1)[0] + '...'

            self.set_xy(desc_x, y_top + CARD_PAD + 1)
            self.set_font('Helvetica', '', 6)
            self.set_text_color(*DARK_TEXT)
            desc_w = desc_right - desc_x - 2
            self.multi_cell(desc_w, 3.2, desc, align='L')

        # ====== SPEC PILLS ROW ======
        self._draw_spec_pills(product, x_left + 5, specs_y, full_w - 10)

    def _draw_spec_pills(self, product, x, y, full_w):
        """Draw specs as small pills across the bottom of the card."""
        spec_candidates = [
            ('Sun', product.get('sun', '')),
            ('Height', product.get('height', '')),
            ('Water', product.get('water', '')),
            ('Color', product.get('color', '')),
            ('Soil', product.get('soil', '')),
            ('Native', product.get('native', '')),
        ]
        # Filter to specs with values, pick ones that fit best
        active = [(l, v) for l, v in spec_candidates if v]

        if not active:
            return

        # Light divider line
        self.set_draw_color(210, 225, 218)
        self.set_line_width(0.15)
        self.line(x, y, x + full_w, y)

        # Smart truncation: keep the most meaningful part of a spec value
        def smart_truncate(val, max_len=28):
            if len(val) <= max_len:
                return val
            # Try breaking at a semicolon, dash, or paren first
            for sep in [';', ' - ', '--', ' (']:
                idx = val.find(sep)
                if 0 < idx <= max_len:
                    return val[:idx].strip()
            # Word-break with ellipsis
            trimmed = val[:max_len - 3]
            space = trimmed.rfind(' ')
            if space > max_len * 0.4:
                return trimmed[:space] + '...'
            return trimmed + '...'

        # Draw spec pills — show up to 3 that fit
        px = x + 2
        pill_y = y + 1.5
        pill_h = 5.5
        pills_drawn = 0
        remaining_w = full_w - 4
        for label, val in active:
            if pills_drawn >= 3:
                break
            val = smart_truncate(val, 28)
            # Compute pill width
            combined = f'{label}: {val}'
            pw = len(combined) * 2.0 + 8
            pw = max(pw, 22)
            pw = min(pw, 58)

            # Check if we overflow — skip this pill if it won't fit
            if px + pw > x + full_w - 2:
                continue

            # Draw pill background
            with self.local_context(fill_opacity=0.12):
                self.set_fill_color(*GREEN_PRIMARY)
                self._rounded_rect(px, pill_y, pw, pill_h, pill_h / 2, style='F')

            # Draw label + value text
            self.set_xy(px, pill_y)
            self.set_font('Helvetica', 'B', 4.5)
            self.set_text_color(*GREEN_PRIMARY)
            label_w = len(label) * 2.2 + 2
            self.cell(label_w, pill_h, label + ':', align='R')
            self.set_font('Helvetica', '', 4.5)
            self.set_text_color(*DARK_TEXT)
            self.cell(pw - label_w - 1, pill_h, ' ' + val, align='L')

            px += pw + 2
            pills_drawn += 1

    # =========================================================
    # BACK COVER — organic, warm
    # =========================================================

    def render_back_cover(self):
        self.add_page()
        self.set_fill_color(*GREEN_DARK)
        self.rect(0, 0, PAGE_W, PAGE_H, 'F')

        # Top accent strips
        self.set_fill_color(*GREEN_PRIMARY)
        self.rect(0, 0, PAGE_W, 3, 'F')
        self.set_fill_color(*GREEN_LIGHT)
        self.rect(0, 3, PAGE_W, 1.5, 'F')

        y = 55
        mid = PAGE_W / 2

        # Logo
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                logo_w = 55
                self.image(self.logo_path, x=(PAGE_W - logo_w) / 2, y=y, w=logo_w)
                y += 35
            except Exception:
                y += 10

        y += 6
        self.set_y(y)

        # Tagline
        self.set_font('Times', 'I', 22)
        self.set_text_color(*GREEN_SECONDARY)
        self.cell(0, 10, 'Seed You Can Trust', align='C')
        self.ln(16)

        # Gold line
        self.set_draw_color(*EARTH_SAND)
        self.set_line_width(0.5)
        self.line(mid - 30, self.get_y(), mid + 30, self.get_y())
        self.ln(12)

        # Warm closing panel
        panel_x = 35
        panel_w = PAGE_W - 2 * panel_x
        panel_y = self.get_y()
        panel_h = 28
        with self.local_context(fill_opacity=0.15):
            self.set_fill_color(*GREEN_SECONDARY)
            self._rounded_rect(panel_x, panel_y, panel_w, panel_h, 4, style='F')

        self.set_xy(panel_x + 6, panel_y + 4)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(200, 215, 208)
        self.multi_cell(panel_w - 12, 5,
            "Thank you for considering Nature's Seed for your next project. "
            "From backyard gardens to large-scale restoration, our team is "
            "here to help you find the right seed for your land and goals. "
            "Questions? We'd love to hear from you.",
            align='C'
        )
        self.set_y(panel_y + panel_h + 12)

        # Trust pills
        trust_items = [
            'Free Shipping $150+',
            'Satisfaction Guaranteed',
            'Family Owned',
            'Expert Support',
        ]
        total_pw = 42 * len(trust_items) + 3 * (len(trust_items) - 1)
        start_x = (PAGE_W - total_pw) / 2
        pill_y = self.get_y()
        for i, item in enumerate(trust_items):
            px = start_x + i * (42 + 3)
            with self.local_context(fill_opacity=0.25):
                self.set_fill_color(*GREEN_LIGHT)
                self._rounded_rect(px, pill_y, 42, 7, 3.5, style='F')
            self.set_xy(px, pill_y)
            self.set_font('Helvetica', '', 5.5)
            self.set_text_color(*WHITE)
            self.cell(42, 7, item, align='C')
        self.set_y(pill_y + 16)

        # Gold line
        self.set_draw_color(*EARTH_SAND)
        self.set_line_width(0.4)
        self.line(mid - 25, self.get_y(), mid + 25, self.get_y())
        self.ln(10)

        # Contact
        self.set_font('Helvetica', '', 10)
        self.set_text_color(180, 200, 190)
        self.cell(0, 6, 'www.naturesseed.com', align='C')
        self.ln(6)
        self.cell(0, 6, 'customercare@naturesseed.com', align='C')
        self.ln(6)
        self.cell(0, 6, '801-531-1456', align='C')
        self.ln(8)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(130, 150, 140)
        self.cell(0, 4, '1697 W 2100 N, Lehi, UT 84043', align='C')
        self.ln(12)

        # Copyright
        self.set_font('Helvetica', '', 7)
        self.set_text_color(100, 120, 110)
        self.cell(0, 4, f"Copyright {date.today().year} Nature's Seed LLC. All rights reserved.", align='C')

        # Bottom accent
        self.set_fill_color(*GREEN_PRIMARY)
        self.rect(0, PAGE_H - 3, PAGE_W, 1.5, 'F')
        self.set_fill_color(*GREEN_LIGHT)
        self.rect(0, PAGE_H - 1.5, PAGE_W, 1.5, 'F')


# ============================================================
# MAIN
# ============================================================

def main():
    print('=' * 60)
    print("Nature's Seed — Wildflower Catalog Generator")
    print('=' * 60)

    # Ensure directories exist
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Fetch products
    raw_products = fetch_products()

    # 2. Filter to single-species
    singles = [p for p in raw_products if is_single_species(p)]

    # Ensure Mexican Primrose (W-OESP, ID 462260) is included — can miss the filter
    known_ids = {p['id'] for p in singles}
    EXTRA_IDS = [462260]  # Mexican Primrose
    for eid in EXTRA_IDS:
        if eid not in known_ids:
            print(f'  Fetching missing product ID {eid}...')
            try:
                resp = requests.get(f'{WC_BASE}/products/{eid}', auth=(WC_CK, WC_CS), timeout=30)
                resp.raise_for_status()
                singles.append(resp.json())
                time.sleep(0.3)
            except Exception as e:
                print(f'  Warning: Could not fetch product {eid}: {e}')

    print(f'\nSingle-species wildflowers found: {len(singles)}')

    # 3. Normalize product data
    print('\nNormalizing product data and fetching variations...')
    products = []
    for p in singles:
        normalized = normalize_product(p)
        products.append(normalized)
        print(f'  {normalized["name"]} ({normalized["sku"]}) — {normalized["price_range"]}')
        time.sleep(0.3)

    # Sort alphabetically
    products.sort(key=lambda p: p['name'])
    print(f'\n{len(products)} products ready for catalog (sorted A-Z)')

    # 4. Download images
    logo_path = download_all_images(products)

    # 5. Generate PDF
    print('\nGenerating PDF...')
    catalog = WildflowerCatalog(logo_path=str(IMG_DIR / 'logo.png'))

    # Cover
    catalog.render_cover_page()
    print('  [done] Cover page')

    # Product pages (organic card layout)
    catalog.render_product_pages(products)
    print(f'  [done] {len(products)} product cards')

    # Back cover
    catalog.render_back_cover()
    print('  [done] Back cover')

    # Save
    catalog.output(str(OUTPUT_PDF))

    print(f'\nPDF saved to: {OUTPUT_PDF}')
    print(f'Total pages: {catalog.page_no()}')
    print(f'Products: {len(products)}')
    print(f'Layout: 4 products per page (organic design)')
    print('=' * 60)

    return str(OUTPUT_PDF)


if __name__ == '__main__':
    main()
