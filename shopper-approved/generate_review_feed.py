#!/usr/bin/env python3
"""
Shopper Approved → Google Merchant Center Product Reviews Feed

Pulls all product reviews from Shopper Approved API,
matches them to WooCommerce products (for URLs and SKUs),
and generates a Google Product Reviews XML feed (v2.4).

Output: docs/reviews/product_reviews.xml (served via GitHub Pages)

Usage:
    python3 shopper-approved/generate_review_feed.py
    python3 shopper-approved/generate_review_feed.py --dry-run   # prints stats, no file write
"""
import os, sys, time, json, re, html
import requests
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DRY_RUN = '--dry-run' in sys.argv

# ── Parse .env ──────────────────────────────────────────────
env = {}
with open(os.path.join(PROJECT_DIR, '.env')) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip("'\"")

SA_SITE_ID = env['SA_SITE_ID']
SA_TOKEN = env['SA_API_TOKEN']
WC_BASE = env.get('WC_BASE_URL', 'https://naturesseed.com/wp-json/wc/v3')
WC_CK = env['WC_CK']
WC_CS = env['WC_CS']
WC_AUTH = (WC_CK, WC_CS)
CF_WORKER_URL = env.get('CF_WORKER_URL', '')
CF_WORKER_SECRET = env.get('CF_WORKER_SECRET', '')

SA_BASE = "https://api.shopperapproved.com"


def _wc_get(path, params=None):
    """GET from WooCommerce REST API, routing through CF Worker if configured."""
    import base64
    if CF_WORKER_URL:
        p = {"wc_path": path, **(params or {})}
        auth_str = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        headers = {"X-Proxy-Secret": CF_WORKER_SECRET, "Authorization": f"Basic {auth_str}"}
        resp = requests.get(CF_WORKER_URL, headers=headers, params=p, timeout=30)
    else:
        resp = requests.get(f"{WC_BASE}{path}", auth=WC_AUTH, params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp


# ── WooCommerce: build product_id → URL+SKU map ────────────
def build_wc_product_map():
    """Build a map from SA product_id (parent SKU) to WC product URL and SKUs.

    SA uses parent SKUs like 'S-DUTCH', 'PB-CHIX', 'TURF-W-TALL'.
    WC has both simple products (SKU = parent) and variable products
    (parent SKU on the product, variation SKUs like 'S-DUTCH-5-LB').
    We index both simple and variable parent products by their SKU.
    """
    products = {}  # sku → {url, name, skus[], gtins[]}
    page = 1
    while True:
        # Include draft products too — many have SA reviews from before SKU consolidation
        r = _wc_get("/products", params={'status': 'any', 'per_page': 100, 'page': page})
        items = r.json()
        if not items:
            break
        for p in items:
            sku = p.get('sku', '')
            if not sku:
                continue

            entry = {
                'url': p.get('permalink', ''),
                'name': p['name'],
                'skus': [sku],
                'gtins': [],
            }

            # Check for GTIN in meta
            for m in p.get('meta_data', []):
                if any(x in m['key'].lower() for x in ['gtin', 'upc', 'ean', 'barcode']):
                    if m.get('value'):
                        entry['gtins'].append(str(m['value']))

            # Index by parent SKU (this catches both simple and variable products)
            products[sku] = entry

        page += 1
        print(f"  WC page {page-1}: {len(items)} products (map size: {len(products)})")
        time.sleep(0.3)
    return products


def extract_parent_sku(sa_product_id):
    """Extract the parent SKU prefix from an SA product ID.

    SA uses variation-level IDs in multiple formats:
      - Current: S-FEOV-10-LB, PG-TRRE-1-LB, WB-RM-1-LB-KIT
      - Legacy:  S-TRRE-1000-F, S-MICRO-500-F, TURF-BR-2000-F
      - Parent:  S-DUTCH, PB-CHIX, TURF-W-TALL (already parent SKU)

    We strip the size/weight suffix to get the parent SKU.
    """
    pid = sa_product_id.strip()
    if not pid:
        return pid

    # Strip known suffixes: -KIT at the end
    base = re.sub(r'-KIT$', '', pid)

    # Strip weight patterns: -10-LB, -0.5-LB, -25-LB, -1-LB
    base = re.sub(r'-\d+(?:\.\d+)?-LB$', '', base)

    # Strip legacy sqft patterns: -1000-F, -500-F, -2000-F, -5000-F
    base = re.sub(r'-\d+-F$', '', base)

    # Strip patterns like -0.25-A, -0.5-A (old format)
    base = re.sub(r'-\d+(?:\.\d+)?-A$', '', base)

    # Strip wildflower packet patterns: -5-P, -1-P, -50-P, -25-P
    base = re.sub(r'-\d+(?:\.\d+)?-P$', '', base)

    # Strip regional variant suffix: -N (Northern variant)
    base = re.sub(r'-N$', '', base)

    return base


# Consolidated product aliases: checked FIRST (before direct WC match)
# so that reviews from old/split SKUs always point to the current live page.
ALIASES = {
    # Turf/lawn mixes: SA "TURF-X" → WC "TURF-W-X"
    'TURF-BR': 'TURF-W-BR',
    'TURF-TALL': 'TURF-W-TALL',
    'TURF-BLUE': 'TURF-W-BLUE',
    'TURF-NW': 'TURF-W-NWE',
    'TURF-NEAST': 'TURF-W-NEAST',
    'TURF-RYE': 'TURF-W-RYE',
    'TURF-SS': 'TURF-W-SS',
    'TURF-NE': 'TURF-W-NEAST',
    'TURF-FF': 'TURF-FINE',
    'TURF-NFF': 'TURF-NFF',
    'TURF-FEAR2': 'TURF-FEAR2',
    # Grass species: SA "S-X" or "TURF-X" → WC "PG-X"
    'TURF-CYDA': 'PG-CYDA',
    'S-TRRE': 'PG-TRRE',
    'S-FERU': 'PG-FERU',
    'S-FELO': 'PG-FELO',
    # Pasture blends — consolidated pages
    'PB-MWPB': 'PB-HRSE-N',
    'PB-MWS': 'PB-SHEP-N',
    'PB-PNWP': 'PB-HRSE-N',
    'PB-GPPB': 'PB-GAME',
    'PB-GLH': 'PB-GOAT-TR',      # old goat pasture → consolidated page
    'PB-GLHB': 'PB-GOAT-TR',     # old goat horse blend → consolidated page
    'PB-GOAT-SO': 'PB-GOAT-TR',  # warm season goat → consolidated page
    'PB-GOAT-N': 'PB-GOAT-TR',   # cool season goat → consolidated page
    'PB-GLG': 'PB-GOAT-TR',      # old goat sub-blend
    'PB-GPG': 'PB-GOAT-TR',      # old goat sub-blend
    'PB-IWG': 'PB-GOAT-TR',      # old goat sub-blend
    'PB-MWG': 'PB-GOAT-TR',      # old goat sub-blend
    'PB-PNWG': 'PB-GOAT-TR',     # old goat sub-blend
    'PB-SWTG': 'PB-GOAT-TR',     # old goat sub-blend
    'PB-PSWG': 'PB-GOAT-TR',     # old goat sub-blend (warm season)
    'PB-SATG': 'PB-GOAT-TR',     # old goat sub-blend (warm season)
    'PB-SSAG': 'PB-GOAT-TR',     # old goat sub-blend (warm season)
    'PB-SWDG': 'PB-GOAT-TR',     # old goat sub-blend (warm season)
    'PB-SATH': 'PB-SHEP-TR',
    # Horse sub-blends (PB/H/HB suffix = horse, by region → N/TR/SO)
    'PB-PNWPB': 'PB-HRSE-N',   # Pacific NW horse blend
    'PB-IWPB': 'PB-HRSE-N',    # Intermountain West horse blend
    'PB-GLPB': 'PB-HRSE-N',    # Great Lakes horse blend
    'PB-PNWH': 'PB-HRSE-N',    # Pacific NW horse
    'PB-MWH': 'PB-HRSE-N',     # Midwest horse
    'PB-IWH': 'PB-HRSE-N',     # Intermountain West horse
    'PB-PNWHB': 'PB-HRSE-N',   # Pacific NW horse blend
    'PB-IWHB': 'PB-HRSE-N',    # Intermountain West horse blend
    'PB-MWHB': 'PB-HRSE-N',    # Midwest horse blend
    'PB-SATPB': 'PB-HRSE-TR',  # South Atlantic horse blend
    'PB-GPHB': 'PB-HRSE-TR',   # Great Plains horse blend
    'PB-SWTH': 'PB-HRSE-TR',   # Southwest horse
    'PB-GPH': 'PB-HRSE-TR',    # Great Plains horse
    'PB-SWTPB': 'PB-HRSE-TR',  # Southwest horse blend
    'PB-PSWH': 'PB-HRSE-SO',   # Pacific SW horse
    'PB-SSH': 'PB-HRSE-SO',    # Southern States horse
    'PB-SSAPB': 'PB-HRSE-SO',  # Southern States Atlantic horse blend
    'PB-SSPB': 'PB-HRSE-SO',   # Southern States horse blend
    'PB-SSAHB': 'PB-HRSE-SO',  # Southern States Atlantic horse blend
    'PB-SWDPB': 'PB-HRSE-SO',  # Southwest Desert horse blend
    'PB-SWDH': 'PB-HRSE-SO',   # Southwest Desert horse
    'PB-SSAH': 'PB-HRSE-SO',   # Southern States Atlantic horse
    'PB-PSWPB': 'PB-HRSE-SO',  # Pacific SW horse blend
    'PB-FTPB': 'PB-HRSE-SO',   # Florida horse blend
    'PB-FTH': 'PB-HRSE-SO',    # Florida horse
    # Sheep sub-blends (S suffix)
    'PB-GLS': 'PB-SHEP-N',     # Great Lakes sheep
    'PB-PNWS': 'PB-SHEP-N',    # Pacific NW sheep
    'PB-IWS': 'PB-SHEP-N',     # Intermountain West sheep
    'PB-SATS': 'PB-SHEP-TR',   # South Atlantic sheep
    'PB-GPS': 'PB-SHEP-TR',    # Great Plains sheep
    'PB-SSD': 'PB-SHEP-SO',    # Southern States sheep (D=flock variant)
    'PB-SSG': 'PB-SHEP-SO',    # Southern States sheep (variant)
    # Alpaca sub-blends (AL suffix)
    'PB-GLAL': 'PB-ALPACA',    # Great Lakes alpaca
    'PB-SATAL': 'PB-ALPACA',   # South Atlantic alpaca
    'PB-PSWAL': 'PB-ALPACA',   # Pacific SW alpaca
    'PB-PNWAL': 'PB-ALPACA',   # Pacific NW alpaca
    'PB-MWAL': 'PB-ALPACA',    # Midwest alpaca
    'PB-GPAL': 'PB-ALPACA',    # Great Plains alpaca
    'PB-FTAL': 'PB-ALPACA',    # Florida alpaca
    # Cattle sub-blends (BC=Beef Cattle, DC=Dairy Cow)
    'PB-PNWBC': 'PB-COW-NTR',  # Pacific NW beef cattle
    'PB-IWBC': 'PB-COW-NTR',   # Intermountain West beef cattle
    'PB-MWBC': 'PB-COW-NTR',   # Midwest beef cattle
    'PB-GLBC': 'PB-COW-NTR',   # Great Lakes beef cattle
    'PB-SSDC': 'PB-COW-SO',    # Southern States dairy cow
    'PB-SATDC': 'PB-COW-NTR',  # South Atlantic dairy cow (transitional)
    'PB-PSWBC': 'PB-COW-SO',   # Pacific SW beef cattle
    # Deer/Game sub-blends (D suffix where context = deer)
    'PB-SWDD': 'PB-GAME',      # Southwest Desert deer
    'PB-IWD': 'PB-GAME',       # Intermountain West deer
    'PB-PNWD': 'PB-GAME',      # Pacific NW deer
    'PB-PNWDC': 'PB-GAME',     # Pacific NW deer/game (DC variant)
    # General pasture sub-blends (P suffix → horse as closest match)
    'PB-MWP': 'PB-HRSE-N',     # Midwest general pasture
    'PB-GLP': 'PB-HRSE-N',     # Great Lakes general pasture
    'PB-IWP': 'PB-HRSE-N',     # Intermountain West general pasture
    'PB-WLWP': 'PB-GAME',      # Wildlife pasture → game plot
    # Bermuda/grass blend sub-blends (BG suffix → regional horse)
    'PB-MWBG': 'PB-HRSE-N',    # Midwest bermuda blend
    'PB-PNWBG': 'PB-HRSE-N',   # Pacific NW bermuda blend
    'PB-SWDBG': 'PB-HRSE-SO',  # Southwest Desert bermuda blend
    'PB-IWBG': 'PB-HRSE-N',    # Intermountain West bermuda blend
    'PB-GLBG': 'PB-HRSE-N',    # Great Lakes bermuda blend
    # Erosion control / specialty (EC suffix → dry pasture as closest)
    'PB-MWEC': 'PB-DRY',       # Midwest erosion control
    'PB-SSEC': 'PB-DRY',       # Southern States erosion control
    'PB-GLEC': 'PB-DRY',       # Great Lakes erosion control
    # Tortoise (discontinued — keep mapped to draft for now)
    'PB-TORT': 'PB-TORT',
    # Misc
    'PB-IWUG': 'PB-HRSE-N',    # Intermountain West utility grade
    'PB-MWDC': 'PB-COW-NTR',   # Midwest dairy cow
    # Wildflower
    'WB-CA': 'WB-CALN',
    'WB-MW': 'WB-MW',
    'WB-DR': 'WB-DR',
    # Individual species / misc
    'LLW-ESCA': 'W-ESCA',
    'W-ASSY': 'W-ASTU',
    'W-BASA': 'W-BASA',
    'TURF-LOPE': 'PG-LOPE',
    'TURF-PANO': 'PG-PANO',
    'TURF-BUDA': 'PG-BUDA',
    'TURF-ZOJA': 'PG-ZOJA',
    'TURF-LM': 'TURF-LM',
    'TURF-POPR': 'PG-POPR',
    'S-TACKI': 'S-TACKI',
    'S-RICE': 'S-RICE',
    'S-FERUC': 'S-FERUC',
    'LLWB-SW': 'WB-SW',
    'SA-A': 'SA-A',       # Shopper Approved site review — no product
    '2750AL-A': '2750AL',  # legacy format
}


def build_gmc_gtin_map():
    """Build parent SKU → GTINs/MPNs map from Google Merchant Center raw product data.

    GMC has 93.5% GTIN coverage (286/306 products). GTINs are the strongest
    product identifier for matching reviews to products in Merchant Center.

    IMPORTANT: GMC feed contains VARIATIONS (e.g., PG-TRRE-10-LB-KIT) while
    Shopper Approved reviews are on PARENT products (e.g., PG-TRRE). We collect
    ALL variation GTINs per parent so the review matches any variant in Shopping.
    """
    gmc_path = os.path.join(PROJECT_DIR, 'seo', 'merchant-center-audit', 'data', 'raw_products.json')
    if not os.path.exists(gmc_path):
        print("  ⚠ GMC raw_products.json not found — run pull_merchant_data.py first")
        return {}

    with open(gmc_path) as f:
        products = json.load(f)

    parent_gtins = {}  # parent_sku → list of ALL variant GTINs
    parent_mpns = {}   # parent_sku → list of ALL variant MPNs
    for p in products:
        mpn = p.get('mpn', '')
        gtin = p.get('gtin', '')
        parent = extract_parent_sku(mpn)
        if parent and gtin:
            parent_gtins.setdefault(parent, []).append(gtin)
        if parent and mpn:
            parent_mpns.setdefault(parent, []).append(mpn)

    print(f"  → {len(parent_gtins)} parent SKUs with GTINs from GMC feed")
    total_gtins = sum(len(v) for v in parent_gtins.values())
    print(f"  → {total_gtins} total variant GTINs across all parents")
    return parent_gtins, parent_mpns


def match_sa_to_wc(sa_product_id, wc_map):
    """Match an SA product_id to WC product data.

    Priority order:
    0. Aliases (consolidated products) — ALWAYS win over direct match
    1. Direct match (SA ID = WC parent SKU)
    2. Extract parent prefix from SA variation ID
    3. Case-insensitive match
    4. Check if SA ID is a variation SKU within any WC product
    """
    if not sa_product_id:
        return None

    parent = extract_parent_sku(sa_product_id)

    # 0. Alias check FIRST — consolidated products always take priority
    for check in [sa_product_id, parent]:
        if check and check in ALIASES:
            target = ALIASES[check]
            if target in wc_map:
                return wc_map[target]

    # 1. Direct match
    if sa_product_id in wc_map:
        return wc_map[sa_product_id]

    # 2. Extract parent prefix
    if parent and parent in wc_map:
        return wc_map[parent]

    # 3. Case-insensitive
    sa_upper = sa_product_id.upper()
    parent_upper = parent.upper() if parent else ''
    for sku, data in wc_map.items():
        sku_upper = sku.upper()
        if sku_upper == sa_upper or sku_upper == parent_upper:
            return data

    # 4. Check if SA ID matches any variation SKU in WC
    for sku, data in wc_map.items():
        if sa_product_id in data.get('skus', []):
            return data

    return None


# ── Shopper Approved: pull all product reviews ──────────────
def pull_all_reviews():
    """Pull all product reviews from SA API, paginated."""
    all_reviews = []
    page = 0
    limit = 100
    while True:
        r = requests.get(f"{SA_BASE}/products/reviews/{SA_SITE_ID}",
                         params={
                             'token': SA_TOKEN,
                             'limit': limit,
                             'page': page,
                             'from': '2010-01-01',  # all time
                             'xml': 'false',
                         }, timeout=30)
        r.raise_for_status()
        data = r.json()

        if not data:
            break

        for review_id, review in data.items():
            if not isinstance(review, dict):
                continue
            # Only include public reviews
            if not review.get('visible_to_public'):
                continue
            all_reviews.append(review)

        print(f"  SA page {page}: {len(data)} reviews (total: {len(all_reviews)})")

        if len(data) < limit:
            break
        page += 1
        time.sleep(0.5)

    return all_reviews


# ── XML Feed Generation ────────────────────────────────────
def clean_text(text, strip_urls=False):
    """Clean review text for XML: decode HTML entities, strip tags, optionally remove URLs."""
    if not text:
        return ""
    # Decode HTML entities
    text = html.unescape(text)
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Strip URLs and emails from review content (GMC rejects these)
    if strip_urls:
        text = re.sub(r'https?://[^\s<>"]+', '', text)
        text = re.sub(r'www\.[^\s<>"]+', '', text)
        text = re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_review_date(date_str):
    """Parse SA date format to ISO 8601."""
    if not date_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        # "Wed, 11 Jun 2025 18:22:15 GMT"
        dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def generate_xml_feed(reviews, wc_map, gmc_gtins=None, gmc_mpns=None):
    """Generate Google Product Reviews XML feed v2.4."""
    feed = Element('feed')
    # Version
    version = SubElement(feed, 'version')
    version.text = '2.4'

    # Publisher
    publisher = SubElement(feed, 'publisher')
    pub_name = SubElement(publisher, 'name')
    pub_name.text = "Nature's Seed"
    pub_favicon = SubElement(publisher, 'favicon')
    pub_favicon.text = "https://naturesseed.com/favicon.ico"

    # Reviews container
    reviews_el = SubElement(feed, 'reviews')

    matched = 0
    unmatched = 0
    skipped_no_content = 0

    for review in reviews:
        product_id = review.get('product_id', '')
        comments = clean_text(review.get('comments', ''), strip_urls=True)
        rating = review.get('rating')

        # Skip reviews with no content
        if not comments or len(comments) < 10:
            skipped_no_content += 1
            continue

        # Skip reviews with no product ID
        if not product_id:
            unmatched += 1
            continue

        # Match to WC product
        wc_product = match_sa_to_wc(product_id, wc_map)
        product_url = wc_product['url'] if wc_product else f"https://naturesseed.com/?s={product_id}"

        if wc_product:
            matched += 1
        else:
            unmatched += 1

        # Build review element
        review_el = SubElement(reviews_el, 'review')

        # Review ID (required)
        rid = SubElement(review_el, 'review_id')
        rid.text = str(review.get('product_review_id', ''))

        # Reviewer (required)
        reviewer = SubElement(review_el, 'reviewer')
        name = SubElement(reviewer, 'name')
        display_name = review.get('display_name', 'Anonymous')
        name.text = display_name if display_name else 'Anonymous'

        # Timestamp (required)
        timestamp = SubElement(review_el, 'review_timestamp')
        timestamp.text = parse_review_date(review.get('review_date'))

        # Title (optional)
        heading = clean_text(review.get('heading', ''))
        if heading:
            title = SubElement(review_el, 'title')
            title.text = heading

        # Content (required)
        content = SubElement(review_el, 'content')
        content.text = comments

        # Review URL (required)
        review_url = SubElement(review_el, 'review_url')
        review_url.set('type', 'singleton')
        review_url.text = product_url

        # Ratings (required)
        ratings = SubElement(review_el, 'ratings')
        overall = SubElement(ratings, 'overall')
        overall.set('min', '1')
        overall.set('max', '5')
        overall.text = str(int(rating)) if rating == int(rating) else str(rating)

        # Products (required)
        products = SubElement(review_el, 'products')
        product = SubElement(products, 'product')

        # Product URL (always required)
        prod_url = SubElement(product, 'product_url')
        prod_url.text = product_url

        # Product name
        prod_name = SubElement(product, 'product_name')
        prod_name.text = clean_text(review.get('product', product_id))

        # Product identifiers — GTIN is strongest, then Brand+MPN, then SKU
        # GMC feed has VARIATIONS, SA reviews are on PARENTS. Include ALL variant
        # GTINs+MPNs so the review matches any variant in Google Shopping.
        product_ids_el = SubElement(product, 'product_ids')

        # Resolve the parent SKU for GMC lookup
        parent_sku = extract_parent_sku(product_id)
        resolved_sku = ALIASES.get(product_id, ALIASES.get(parent_sku, parent_sku))

        # GTINs: include ALL unique variant GTINs from GMC (strongest match)
        gtin_list = []
        if gmc_gtins:
            gtin_list = gmc_gtins.get(resolved_sku, []) or gmc_gtins.get(parent_sku, [])
        if not gtin_list and wc_product and wc_product.get('gtins'):
            gtin_list = wc_product['gtins']
        # Deduplicate (many variants share the same UPC)
        gtin_list = list(dict.fromkeys(gtin_list))
        if gtin_list:
            gtins_el = SubElement(product_ids_el, 'gtins')
            for gtin_val in gtin_list:
                gtin_el = SubElement(gtins_el, 'gtin')
                gtin_el.text = gtin_val

        # MPNs: include ALL variant MPNs (these match GMC's mpn field exactly)
        mpn_list = []
        if gmc_mpns:
            mpn_list = gmc_mpns.get(resolved_sku, []) or gmc_mpns.get(parent_sku, [])
        if not mpn_list:
            mpn_list = [wc_product['skus'][0] if wc_product else product_id]
        mpns_el = SubElement(product_ids_el, 'mpns')
        for mpn_val in mpn_list:
            mpn_el = SubElement(mpns_el, 'mpn')
            mpn_el.text = mpn_val

        # SKUs
        skus_el = SubElement(product_ids_el, 'skus')
        sku_val = SubElement(skus_el, 'sku')
        sku_val.text = wc_product['skus'][0] if wc_product else product_id

        # Brand (always Nature's Seed)
        brands_el = SubElement(product_ids_el, 'brands')
        brand_el = SubElement(brands_el, 'brand')
        brand_el.text = "Nature's Seed"

        # Is verified purchase
        if review.get('verified'):
            verified = SubElement(review_el, 'is_verified_purchase')
            verified.text = 'true'

    return feed, matched, unmatched, skipped_no_content


def pretty_xml(element):
    """Convert ElementTree element to pretty-printed XML string."""
    rough = tostring(element, encoding='unicode')
    # Add XML declaration
    dom = parseString(rough)
    pretty = dom.toprettyxml(indent="  ", encoding="UTF-8")
    return pretty


def main():
    print("=" * 60)
    print("SHOPPER APPROVED → GOOGLE PRODUCT REVIEWS FEED")
    print("=" * 60)

    # Step 1: Build WC product map
    print("\n[1/4] Building WooCommerce product map...")
    wc_map = build_wc_product_map()
    print(f"  → {len(wc_map)} WC products indexed")

    # Step 2: Load GMC GTIN data
    print("\n[2/5] Loading Google Merchant Center GTIN data...")
    gmc_result = build_gmc_gtin_map()
    if gmc_result:
        gmc_gtins, gmc_mpns = gmc_result
    else:
        gmc_gtins, gmc_mpns = {}, {}

    # Step 3: Pull all SA reviews
    print("\n[3/5] Pulling Shopper Approved reviews...")
    reviews = pull_all_reviews()
    print(f"  → {len(reviews)} public reviews pulled")

    # Step 4: Generate XML feed
    print("\n[4/5] Generating Google Product Reviews XML feed...")
    feed, matched, unmatched, skipped = generate_xml_feed(reviews, wc_map, gmc_gtins, gmc_mpns)
    print(f"  Matched to WC products: {matched}")
    print(f"  Unmatched (search URL):  {unmatched}")
    print(f"  Skipped (no content):    {skipped}")
    print(f"  Total reviews in feed:   {matched + unmatched}")

    # Step 5: Write XML
    if DRY_RUN:
        print("\n*** DRY RUN — no file written ***")
        xml_bytes = pretty_xml(feed)
        print(f"  XML size: {len(xml_bytes):,} bytes")
        # Show first 2000 chars
        print(xml_bytes.decode('utf-8')[:2000])
        return

    output_dir = os.path.join(PROJECT_DIR, 'docs', 'reviews')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'product_reviews.xml')

    xml_bytes = pretty_xml(feed)
    with open(output_path, 'wb') as f:
        f.write(xml_bytes)

    print(f"\n[5/5] Written to: {output_path}")
    print(f"  File size: {len(xml_bytes):,} bytes")
    print(f"  URL (GitHub Pages): https://gabenaturesseed.github.io/nature-seed-data/reviews/product_reviews.xml")

    print(f"\n{'=' * 60}")
    print("DONE — Submit this URL in Google Merchant Center:")
    print("  Merchant Center → Growth → Product Reviews → Manage feeds")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
