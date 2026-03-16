#!/usr/bin/env python3
"""
Fetch all published WooCommerce products/variations and generate pricing HTML report.
"""

import requests
import json
import time
import csv
import os
import re
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
WC_BASE       = "https://naturesseed.com/wp-json/wc/v3"
WC_CK         = "ck_9629579f1379f272169de8628edddb00b24737f9"
WC_CS         = "cs_bf6dcf206d6ed26b83e55e8af62c16de26339815"
CF_WORKER_URL = "https://wc-api-proxy.skylar-d51.workers.dev"
CF_SECRET     = "afbd1ef8cfbda2255fb6bc1b45be78c0d8fbe48aca44ff2a8d9b1ecf65ed7dde"

OUTPUT_DIR    = Path("/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/reports")
COGS_CSV      = Path("/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/Woo-COGS/Cost per SKU - Sheet1.csv")

USE_PROXY = True   # flip to False if proxy fails


def api_get(endpoint: str, params: dict = None) -> requests.Response:
    """GET via CF Worker proxy with fallback to direct WC API.

    The Worker expects:
      GET https://wc-api-proxy.skylar-d51.workers.dev/?wc_path=/products&per_page=100&...
      Header: X-Proxy-Secret: <secret>
      Header: Authorization: Basic <base64(ck:cs)>
    """
    import base64
    global USE_PROXY
    params = params or {}

    if USE_PROXY:
        # Build proxy params: inject wc_path, keep everything else
        proxy_params = {"wc_path": f"/{endpoint}", **params}
        # The worker forwards the Authorization header to WC origin
        credentials = base64.b64encode(f"{WC_CK}:{WC_CS}".encode()).decode()
        headers = {
            "X-Proxy-Secret": CF_SECRET,
            "Authorization": f"Basic {credentials}",
        }
        try:
            r = requests.get(CF_WORKER_URL, params=proxy_params, headers=headers, timeout=30)
            if r.status_code in (400, 401, 403, 500, 502, 503):
                print(f"  [proxy] HTTP {r.status_code} for {endpoint}: {r.text[:120]} — falling back to direct")
                USE_PROXY = False
            else:
                return r
        except Exception as e:
            print(f"  [proxy] exception: {e} — falling back to direct")
            USE_PROXY = False

    # Direct WC API (residential IPs work fine without proxy)
    url = f"{WC_BASE}/{endpoint}"
    r = requests.get(url, params=params, auth=(WC_CK, WC_CS), timeout=30)
    return r


def paginate(endpoint: str, extra_params: dict = None) -> list:
    """Fetch all pages from a paginated WC endpoint."""
    results = []
    page = 1
    while True:
        params = {"per_page": 100, "page": page, **(extra_params or {})}
        r = api_get(endpoint, params)
        if r.status_code != 200:
            print(f"  ERROR {r.status_code} on {endpoint} page {page}: {r.text[:200]}")
            break
        data = r.json()
        if not data:
            break
        results.extend(data)
        total_pages = int(r.headers.get("X-WP-TotalPages", 1))
        print(f"  {endpoint} page {page}/{total_pages} — {len(data)} items")
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)
    return results


# ── STEP 1: Fetch products ───────────────────────────────────────────────────
print("=" * 60)
print("Fetching published VARIABLE products…")
variable_products = paginate("products", {"status": "publish", "type": "variable"})
print(f"  Total variable products: {len(variable_products)}")

time.sleep(0.3)

print("\nFetching published SIMPLE products…")
simple_products = paginate("products", {"status": "publish", "type": "simple"})
print(f"  Total simple products: {len(simple_products)}")

# Collect simple SKUs
simple_skus = set()
for p in simple_products:
    sku = (p.get("sku") or "").strip()
    if sku:
        simple_skus.add(sku)

print(f"\n  Simple SKUs collected: {len(simple_skus)}")

# Fetch variations for each variable product
print("\nFetching variations for each variable product…")
variation_skus = set()
parent_products = []

for idx, prod in enumerate(variable_products):
    pid   = prod["id"]
    pname = prod.get("name", "")
    psku  = (prod.get("sku") or "").strip()

    parent_products.append({"id": pid, "sku": psku, "name": pname})

    vars_ = paginate(f"products/{pid}/variations")
    for v in vars_:
        vsku = (v.get("sku") or "").strip()
        if vsku:
            variation_skus.add(vsku)

    print(f"  [{idx+1}/{len(variable_products)}] {pname[:50]} — {len(vars_)} variations")
    time.sleep(0.3)

print(f"\nVariation SKUs collected: {len(variation_skus)}")

# Save JSON
output = {
    "variation_skus": sorted(variation_skus),
    "simple_skus":    sorted(simple_skus),
    "parent_products": parent_products,
}
json_path = OUTPUT_DIR / "published_skus.json"
json_path.write_text(json.dumps(output, indent=2))
print(f"\nSaved: {json_path}")


# ── STEP 2: Load COGS CSV ────────────────────────────────────────────────────
print("\nLoading COGS CSV…")
cogs = {}
with open(COGS_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        sku = row.get("SKU", "").strip()
        cost_raw  = row.get("Unit Cost", "").replace("$", "").replace(",", "").strip()
        price_raw = row.get("Selling Price", "").replace("$", "").replace(",", "").strip()
        try:
            cost  = float(cost_raw)  if cost_raw  else None
        except ValueError:
            cost = None
        try:
            price = float(price_raw) if price_raw else None
        except ValueError:
            price = None
        if sku:
            cogs[sku] = {"cost": cost, "price": price}

print(f"  COGS entries loaded: {len(cogs)}")


# ── STEP 3: Pricing recommendations ─────────────────────────────────────────
PRICING_RECS = [
  # LAWN
  ["Lawn","TURF-BERM-5-LB","Bermuda Grass Seed",35.00,119.99,"$10–12/lb","overpriced",59.99,"At $24/lb vs $10/lb market"],
  ["Lawn","TURF-BUDA-3-LB-KIT","Buffalograss (turf)",28.89,116.99,"$45/lb at 2lb bags","raise",149.99,"You're BELOW market – buffalograss is scarce"],
  ["Lawn","TURF-CLV-5-LB","Clover Lawn",7.14,17.99,"$4.80–5/lb","raise",24.99,"Underpriced by ~$7 vs market"],
  ["Lawn","TURF-FINE-5-LB","Fine Fescue Blend",10.65,39.99,"$5–6/lb","overpriced",29.99,"2x market for comparable fescue blends"],
  ["Lawn","TURF-HLB-5-LB","Hard Lean Blend",17.75,44.99,"$5–8/lb","overpriced",34.99,"Reduce ~$10"],
  ["Lawn","TURF-JBR-5-LB","Jimmy Blue Ribbon (KBG)",10.90,89.99,"$7–10/lb","overpriced",49.99,"KBG at $18/lb vs $7/lb market"],
  ["Lawn","TURF-MLB-5-LB","Mountain Lawn Blend",11.30,28.99,"$5–6/lb","hold",None,"Competitive for custom mountain blend"],
  ["Lawn","TURF-NFF-5-LB","No-Filler Fine Fescue",48.90,230.58,"Unknown","review",89.99,"At $46/lb needs review – specialty or pricing error?"],
  ["Lawn","TURF-W-BLUE-5-LB","Western Kentucky Bluegrass",13.75,84.99,"$7/lb","overpriced",44.99,"2.4x market – losing KBG category sales"],
  ["Lawn","TURF-W-BR-5-LB","Western Browntop Rye",12.50,39.99,"$4–5/lb","overpriced",24.99,"Still 50% margin at $24.99"],
  ["Lawn","TURF-W-RYE-5-LB","Western Perennial Ryegrass",6.15,49.99,"$3–5/lb","overpriced",24.99,"Ryegrass is commodity – at $10/lb you lose on price search"],
  ["Lawn","TURF-W-SS-5-LB","Western Sun & Shade Mix",10.68,39.99,"$4–6/lb","overpriced",29.99,"Moderate overpricing"],
  ["Lawn","TURF-W-TALL-5-LB","Western Tall Fescue",5.50,39.99,"$1.70–5/lb","overpriced",24.99,"Tall fescue is most-searched lawn grass – price sensitivity high"],
  ["Lawn","TURF-WSHD-5-LB","Weed & Shade Blend",7.44,39.99,"$4–6/lb","overpriced",29.99,"Slight overpricing vs comparable shade blends"],
  ["Lawn","TURF-W-BLUE-BUNDLE-5-LB","Western KBG + Fertilizer Bundle",38.61,199.99,"Bundle","hold",None,"Bundle premium acceptable if fertilizer value communicated"],
  ["Lawn","TURF-W-TALL-BUNDLE-5-LB-KIT","Western Tall Fescue + Bundle",30.93,159.99,"Bundle","hold",None,"Bundle premium acceptable"],
  # PASTURE
  ["Pasture","PB-ALPACA-10-LB","Alpaca Pasture Blend",15.50,29.99,"$4–5/lb","raise",39.99,"Underpriced by $10 vs specialty livestock mixes"],
  ["Pasture","PB-BIRD-10-LB","Bird/Gamebird Mix",10.05,24.99,"$3–5/lb","raise",34.99,"Below market for wildlife habitat mixes"],
  ["Pasture","PB-CABIN-10-LB-KIT","Cabin Orchard Blend",35.00,79.19,"$6/lb","overpriced",59.99,"At $7.92/lb vs $6/lb market"],
  ["Pasture","PB-CHIX-5-LB","Chicken Forage Mix",8.90,19.99,"$7/lb","raise",34.99,"URGENT – Hancock charges $34.99 for same product"],
  ["Pasture","PB-CHSS-0.5-LB","Chicory + Soft Legume",9.45,37.64,"$10–20/lb","review",21.99,"At $75/lb vs $10-20/lb market – review composition"],
  ["Pasture","PB-CLV-10-LB","Clover Pasture Mix",25.39,47.99,"$4–5/lb","hold",None,"Competitive"],
  ["Pasture","PB-COSS-0.5-LB","Cow Soft Legume Mix",8.23,38.82,"$10–20/lb","review",21.99,"At $77/lb – same concern as CHSS"],
  ["Pasture","PB-COW-NTR-10-LB","Cow Pasture (Native)",17.30,39.99,"$3–5/lb","hold",None,"Competitive"],
  ["Pasture","PB-COW-SO-10-LB","Cow Pasture (Southern)",23.00,39.99,"$3–5/lb","hold",None,"Competitive"],
  ["Pasture","PB-DRY-10-LB","Dryland Pasture",20.40,50.99,"$3.50–5/lb","hold",None,"Competitive"],
  ["Pasture","PB-DRY-50-LB-KIT","Dryland Pasture 50lb",102.00,91.78,"n/a","review",179.99,"SELLING AT A LOSS – cost $102 vs price $91.78"],
  ["Pasture","PB-FULL-10-LB","Full Season Pasture",27.46,111.99,"$5–7/lb","overpriced",79.99,"At $11.20/lb vs $5-7/lb market"],
  ["Pasture","PB-GAME-10-LB","Game Bird Mix",10.10,29.99,"$4–5/lb","raise",39.99,"Below market for wildlife mixes"],
  ["Pasture","PB-GOAT-N-10-LB","Goat Pasture (Native)",21.90,49.99,"$4–6/lb","hold",None,"Competitive"],
  ["Pasture","PB-GOAT-SO-10-LB","Goat Pasture (Southern)",20.50,49.99,"$4–6/lb","hold",None,"Competitive"],
  ["Pasture","PB-GOAT-TR-10-LB","Goat Pasture (Trail)",21.10,49.99,"$4–6/lb","hold",None,"Competitive"],
  ["Pasture","PB-GRSC-10-LB","Grass + Clover Mix",8.72,35.99,"$3–4.50/lb","hold",None,"Competitive"],
  ["Pasture","PB-HONEY-5-LB","Honey Bee Forage",24.65,59.99,"$7–8/lb","hold",None,"Well-positioned between commodity and premium"],
  ["Pasture","PB-HRSE-N-10-LB","Horse Pasture (Native)",11.80,29.99,"$3–4/lb","hold",None,"Competitive"],
  ["Pasture","PB-HRSE-SO-10-LB","Horse Pasture (Southern)",11.80,39.99,"$3–4/lb","hold",None,"Competitive"],
  ["Pasture","PB-HRSE-TR-10-LB","Horse Pasture (Trail)",12.70,49.99,"$3–5/lb","hold",None,"Competitive"],
  ["Pasture","PB-IR-10-LB","Irrigation Pasture",15.90,39.99,"$3–4/lb","hold",None,"Competitive"],
  ["Pasture","PB-KRMU-10-LB","Kura/Multiuse Pasture",7.31,29.99,"$5–10/lb","raise",59.99,"If Kura clover-based – verify composition first"],
  ["Pasture","PB-MUST-10-LB","Mustard Pasture Mix",18.70,46.99,"$4–6/lb","hold",None,"Competitive"],
  ["Pasture","PB-PIG-10-LB","Pig Forage Mix",23.80,49.99,"$4–6/lb","hold",None,"Competitive"],
  ["Pasture","PB-SGPR-5-LB","Sagebrush Prairie Mix",43.53,84.99,"$10–20/lb","hold",None,"Native prairie specialty – premium justified"],
  ["Pasture","PB-SHADE-10-LB","Shade Pasture Mix",21.00,113.99,"$6–10/lb","overpriced",89.99,"At $11.40/lb vs $6-10/lb market"],
  ["Pasture","PB-SHEP-N-10-LB","Sheep Pasture (Native)",20.20,49.99,"$4–6/lb","hold",None,"Competitive"],
  ["Pasture","PB-SHEP-SO-10-LB","Sheep Pasture (Southern)",27.80,69.99,"$4–6/lb","hold",None,"Competitive"],
  ["Pasture","PB-SHEP-TR-10-LB","Sheep Pasture (Trail)",14.40,39.99,"$3–5/lb","hold",None,"Competitive"],
  ["Pasture","PB-SHPR-10-LB-KIT","Short Prairie Mix",80.00,159.99,"$8–15/lb","overpriced",129.99,"At $16/lb vs $8-15/lb native prairie market"],
  ["Pasture","PB-TORT-2-LB","Tortoise Forage Mix",17.90,44.99,"$15–30/lb","hold",None,"Niche specialty – competitive for tortoise forage"],
  # NATIVE GRASSES
  ["Native Grasses","PG-BOGR-5-LB","Blue Grama Grass",55.40,325.87,"$15–20/lb","overpriced",129.99,"At $65/lb vs $15-20/lb market – major conversion killer"],
  ["Native Grasses","PG-BUCK-5-LB","Buckwheat",1.75,39.99,"$3–6/lb","overpriced",24.99,"Very low cost – still 93% margin at $24.99"],
  ["Native Grasses","PG-BUDA-5-LB","Buffalograss (pure native)",84.30,299.99,"$45/lb","hold",249.99,"Slightly above market – minor reduction ok"],
  ["Native Grasses","PG-CYDA-5-LB","Cypress/Dalea Mix",27.50,84.99,"$10–20/lb","hold",None,"Competitive for niche native"],
  ["Native Grasses","PG-CYDA-25-LB-KIT","Cypress/Dalea 25lb",137.50,139.99,"n/a","review",229.99,"CRITICAL: only $2.49 gross profit – $137.50 cost on $139.99 sale"],
  ["Native Grasses","PG-DAGL-5-LB","Dallisgrass",1.60,34.99,"$4–6/lb","overpriced",24.99,"At $7/lb vs $4-6/lb market"],
  ["Native Grasses","PG-FEAR2-5-LB","Festuca/Arizona Mix",3.55,34.99,"$5–8/lb","hold",None,"Competitive for native fescue mix"],
  ["Native Grasses","PG-LOPE-5-LB","Lovegrass",4.55,34.99,"$5–10/lb","hold",None,"Competitive for lovegrass specialty"],
  ["Native Grasses","PG-MESA-5-LB","Mesa/Sideoats Grama",9.95,39.99,"$10–15/lb","raise",49.99,"Sideoats grama is specialty – you're BELOW market"],
  ["Native Grasses","PG-PANO-5-LB","Panicum/Switchgrass",27.50,99.99,"$10–12/lb","overpriced",59.99,"At $20/lb vs $10-12/lb market for switchgrass"],
  ["Native Grasses","PG-PAVI-5-LB","Panic Virgatum (switchgrass)",11.75,84.99,"$10–12/lb","overpriced",59.99,"At $17/lb vs $10-12/lb – can reduce with healthy margin"],
  ["Native Grasses","PG-PHPR-5-LB","Plains/Prairie Mix",7.45,34.99,"$6–10/lb","hold",None,"Competitive"],
  ["Native Grasses","PG-POPR-5-LB","Poa pratensis (pure KBG)",8.20,39.99,"$7/lb","hold",None,"Competitive for pure KBG"],
  ["Native Grasses","PG-SECE-5-LB","Sedge (specialty)",1.55,24.99,"$10–25/lb","raise",79.99,"If true Carex sedge – drastically underpriced. Verify species."],
  ["Native Grasses","PG-TRRE-5-LB","Turf/Range Rye",16.30,34.99,"$3–4/lb","hold",None,"High cost protects from reduction (margin 53.4%)"],
  # COVER CROPS
  ["Cover Crops","CV-BGEC-10-LB","Big Eastern Coneflower",58.50,199.99,"$15–25/lb","hold",None,"Competitive for specialty coneflower"],
  ["Cover Crops","CV-CHM-25-LB-KIT","Chamomile Mix",268.50,1455.88,"$10–15/lb","review",599.99,"Cost $10.74/lb – at $58/lb you are 4-6x market rate"],
  ["Cover Crops","CV-CNEC-5-LB","Crimson/East Cover Crop",74.75,205.88,"Specialty","review",None,"Cost $14.95/lb – NOT commodity crimson clover. Hold pending composition review."],
  ["Cover Crops","CV-CNFW-5-LB","Crimson/North Cover+Wildflowers",72.21,382.35,"Specialty","review",None,"Cost $14.44/lb – specialty content justifies premium. Hold pending review."],
  ["Cover Crops","CV-NEC-10-LB","Northern/Eastern Cover Crop",25.60,99.99,"$4–5/lb","overpriced",69.99,"At $10/lb vs $4-5/lb market – 2x overpriced"],
  # WILDFLOWER BLENDS
  ["Wildflower Blends","WB-AN-0.5-LB","Annual Wildflower Blend",5.46,29.99,"$12–20/lb","overpriced",14.99,"Eden Brothers 1lb = $12.50 – your 0.5lb should be ~$8-12"],
  ["Wildflower Blends","WB-CALN-0.5-LB","California Native Blend",8.55,41.16,"$15–25/lb","overpriced",18.99,"At $82/lb vs $15-25/lb market for regional native blends"],
  ["Wildflower Blends","WB-CCN-0.5-LB","Cottage/Country Native",7.57,37.63,"$12–20/lb","overpriced",15.99,"3-4x market for cottage garden mixes"],
  ["Wildflower Blends","WB-DR-0.5-LB","Drought Resistant Blend",6.27,29.99,"$12–18/lb","overpriced",14.99,"At $60/lb vs $12-18/lb – reduce significantly"],
  ["Wildflower Blends","WB-RM-0.5-LB","Rocky Mountain Blend",7.10,29.99,"$12–18/lb","overpriced",14.99,"BBB Seed and Mountain Valley sell comparable at $12-18/lb"],
  ["Wildflower Blends","WB-SD-0.5-LB","Sun/Desert Blend",8.62,24.99,"$12–18/lb","overpriced",12.99,"Minor reduction – still 33% margin"],
  ["Wildflower Blends","WB-XCVP-0.5-LB","Xeriscape Pollinator",8.62,58.82,"$25–34/lb","overpriced",19.99,"At $117/lb vs $34/lb (American Meadows) – worst outlier"],
  # SINGLE SPECIES
  ["Single Species","W-ACLA-0.25-LB","Achillea/Yarrow",2.95,17.64,"$15–25/lb","overpriced",8.99,"At $70/lb vs $15-25/lb market for yarrow"],
  ["Single Species","W-ASFA-0.25-LB","Aster/Aspen Fleabane",20.18,100.99,"$30–60/lb","hold",39.99,"High cost ($80/lb) limits reduction – min $39.99 for 49% margin"],
  ["Single Species","W-DIAUA-0.25-LB","Diamond Alyssum",2.49,19.99,"$10/lb","overpriced",5.99,"At $80/lb vs $10/lb for alyssum"],
  ["Single Species","W-ENCA-0.25-LB","Engelmann Coneflower",11.47,21.16,"$15–30/lb","raise",29.99,"Cost $45.88/lb – UNDERPRICED. Current margin only 45.8%."],
  ["Single Species","W-ENFA-0.25-LB","English/Annual Fescue",1.66,10.58,"$2–5/lb","overpriced",2.99,"At $42/lb for commodity fescue"],
  ["Single Species","W-ERCO-0.25-LB","Erigeron/Coneflower",8.20,54.11,"$15–30/lb","overpriced",19.99,"Cost allows reduction – 59% margin at $19.99"],
  ["Single Species","W-ESCA-1-LB-KIT","California Poppy",12.14,27.89,"$10/lb","overpriced",22.99,"Commodity wildflower – 2.8x Eden Brothers rate"],
  ["Single Species","W-LUBI-0.25-LB","Lupine",3.83,18.81,"$15–25/lb","overpriced",5.99,"At $75/lb vs $15-25/lb market"],
  ["Single Species","W-LUMI-0.25-LB","Lupine Mix",6.95,29.41,"$20–25/lb","overpriced",6.99,"At $117/lb – minor reduction to $6.99 (≈$28/lb)"],
  ["Single Species","W-LUSU-0.25-LB","Lupinus succulentus",3.14,15.28,"$15–25/lb","hold",None,"Borderline – at $61/lb but specialty lupine"],
  ["Single Species","W-NAPU-0.25-LB","Native Purple",3.32,19.99,"$15–25/lb","overpriced",5.99,"At $80/lb vs $15-25/lb"],
  ["Single Species","W-SAAP-0.25-LB","Salvia",7.56,32.93,"$20–30/lb","overpriced",7.99,"At $131/lb vs $20-30/lb – significant reduction needed"],
  ["Single Species","W-SIBE-0.25-LB","Siberian Iris",3.83,50.58,"$30–60/lb","hold",None,"Iris seed genuinely expensive – competitive at $202/lb"],
  # SPECIALTY
  ["Specialty","S-AGPA8-1-LB","Agapanthus Seed",22.58,107.05,"$40–80/lb","review",None,"Review product type – if specialty perennial seed, competitive"],
  ["Specialty","S-DUTCH-5-LB","Dutch White Clover",21.50,44.99,"$4.80–5/lb","overpriced",39.99,"At $9/lb vs $4.80/lb Outsidepride – $39.99 is minimum safe (46% margin)"],
  ["Specialty","S-FEOV-5-LB","Fescue Ovation",14.95,39.99,"$4–6/lb","overpriced",29.99,"At $8/lb vs $4-6/lb – reduce to $29.99 for 50% margin"],
  ["Specialty","S-INNOC-5-LB","Legume Inoculant",26.00,74.99,"$10–20/lb","hold",None,"Competitive vs Johnny's Seeds at $12/lb"],
  ["Specialty","S-MICRO-1-LB","Micro Clover",14.57,44.99,"$34.99/lb","overpriced",34.99,"Match Outsidepride MiniClover 1lb = $34.99 (58% margin)"],
  ["Specialty","S-RICE-5-LB","Rice Hulls",1.25,17.99,"$2–4/lb","hold",None,"Competitive for rice hull mulch"],
  ["Specialty","S-TACKI-50-LB","Tackifier",25.50,119.99,"$1.50–3/lb","hold",None,"Competitive for hydroseeding tackifier"],
  ["Specialty","SUSTANE-4-6-4","Sustane Organic Fertilizer 4-6-4",24.50,119.99,"$2–3/lb","hold",None,"Competitive retail over trade pricing"],
  ["Specialty","SUSTANE-18-1-8+FE","Sustane 18-1-8+FE",55.00,154.99,"$2.50–3.50/lb","hold",None,"Competitive retail"],
]

# All published SKUs (combined)
all_published_skus = variation_skus | simple_skus

# Filter recs to published only
published_recs = []
excluded_recs  = []
for rec in PRICING_RECS:
    sku = rec[1]
    if sku in all_published_skus:
        published_recs.append(rec)
    else:
        excluded_recs.append(rec)

print(f"\nTotal pricing recs:      {len(PRICING_RECS)}")
print(f"Matched (published):     {len(published_recs)}")
print(f"Excluded (not in WC):    {len(excluded_recs)}")

print("\n--- EXCLUDED (not found in published WC catalog) ---")
for rec in excluded_recs:
    print(f"  [{rec[0]}] {rec[1]} — {rec[2]}")


# ── STEP 3: Build HTML ───────────────────────────────────────────────────────
def fmt_currency(v):
    if v is None:
        return "—"
    return f"${v:,.2f}"

def calc_margin(cost, price):
    if cost is None or price is None or price == 0:
        return None
    return (price - cost) / price * 100

def margin_color_class(m):
    if m is None:
        return ""
    if m >= 60:
        return "mg-green"
    if m >= 40:
        return "mg-yellow"
    return "mg-red"

def verdict_badge(v):
    classes = {
        "overpriced": "badge-overpriced",
        "raise":      "badge-raise",
        "hold":       "badge-hold",
        "review":     "badge-review",
    }
    labels = {
        "overpriced": "Overpriced",
        "raise":      "Raise",
        "hold":       "Hold",
        "review":     "Review",
    }
    cls = classes.get(v, "badge-hold")
    lbl = labels.get(v, v.title())
    return f'<span class="badge {cls}">{lbl}</span>'

# Build rows
rows_html = []
for rec in published_recs:
    cat, sku, name, cost_rec, price_rec, market, verdict, rec_price, notes = rec
    # Prefer COGS CSV data if available
    cog = cogs.get(sku, {})
    cost  = cog.get("cost")  if cog.get("cost")  is not None else cost_rec
    price = cog.get("price") if cog.get("price") is not None else price_rec

    margin     = calc_margin(cost, price)
    new_margin = calc_margin(cost, rec_price) if rec_price else None

    row_class = {
        "overpriced": "row-overpriced",
        "raise":      "row-raise",
        "hold":       "row-hold",
        "review":     "row-review",
    }.get(verdict, "")

    # Cost/price display — highlight loss
    is_loss = (cost is not None and price is not None and cost > price)
    cost_html  = f'<span class="loss-warn">⚠️ {fmt_currency(cost)}</span>' if is_loss else fmt_currency(cost)
    price_html = f'<span class="loss-warn">{fmt_currency(price)} LOSS</span>' if is_loss else fmt_currency(price)

    mg_class     = margin_color_class(margin)
    new_mg_class = margin_color_class(new_margin)

    mg_str     = f'<span class="{mg_class}">{margin:.1f}%</span>'     if margin     is not None else "—"
    new_mg_str = f'<span class="{new_mg_class}">{new_margin:.1f}%</span>' if new_margin is not None else "—"

    rows_html.append(f"""
    <tr class="{row_class}" data-verdict="{verdict}" data-category="{cat}"
        data-sku="{sku.lower()}" data-name="{name.lower()}">
      <td>{cat}</td>
      <td class="mono">{sku}</td>
      <td>{name}</td>
      <td class="num">{cost_html}</td>
      <td class="num">{price_html}</td>
      <td class="num">{mg_str}</td>
      <td>{market}</td>
      <td>{verdict_badge(verdict)}</td>
      <td class="num">{fmt_currency(rec_price)}</td>
      <td class="num">{new_mg_str}</td>
      <td class="notes">{notes}</td>
    </tr>""")

# Summary counts (published only)
from collections import Counter
verdict_counts = Counter(r[6] for r in published_recs)

categories = sorted(set(r[0] for r in published_recs))
cat_pills = '<button class="pill active" onclick="filterCat(\'all\')">All</button>\n'
for c in categories:
    cat_pills += f'    <button class="pill" onclick="filterCat(\'{c}\')">{c}</button>\n'

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nature's Seed — Pricing & COGS Report</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         font-size: 13px; background: #f0f4f0; color: #1a1a1a; }}

  /* ── Header ── */
  .site-header {{
    position: sticky; top: 0; z-index: 100;
    background: #1b4332; color: #fff; padding: 14px 20px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 2px 6px rgba(0,0,0,.4);
  }}
  .site-header h1 {{ font-size: 18px; font-weight: 700; letter-spacing: .3px; }}
  .site-header .subtitle {{ font-size: 11px; opacity: .75; margin-top: 2px; }}

  /* ── Controls ── */
  .controls {{
    background: #fff; padding: 12px 20px; border-bottom: 1px solid #d8e4d8;
  }}
  .controls-row {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }}
  .search-box {{
    padding: 7px 12px; border: 1px solid #c5d8c5; border-radius: 6px;
    font-size: 13px; width: 240px; outline: none;
  }}
  .search-box:focus {{ border-color: #2d6a4f; }}
  label.toggle {{ display: flex; align-items: center; gap: 6px; cursor: pointer; user-select: none; }}
  label.toggle input {{ width: 15px; height: 15px; accent-color: #2d6a4f; }}
  .btn-export {{
    margin-left: auto; padding: 7px 16px; background: #2d6a4f; color: #fff;
    border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;
  }}
  .btn-export:hover {{ background: #1b4332; }}

  /* ── Pills ── */
  .pills {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }}
  .pill {{
    padding: 4px 12px; border-radius: 20px; border: 1px solid #2d6a4f;
    background: transparent; color: #2d6a4f; cursor: pointer; font-size: 12px;
    transition: all .15s;
  }}
  .pill:hover, .pill.active {{
    background: #2d6a4f; color: #fff;
  }}

  /* ── Summary bar ── */
  .summary-bar {{
    background: #fff; padding: 10px 20px;
    display: flex; align-items: center; gap: 20px; border-bottom: 1px solid #d8e4d8;
    flex-wrap: wrap;
  }}
  .summary-bar .lbl {{ font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: .5px; }}
  .count-chip {{ display: flex; align-items: center; gap: 6px; }}
  .count-chip .num {{ font-size: 20px; font-weight: 700; }}
  .c-red    {{ color: #c0392b; }}
  .c-green  {{ color: #27ae60; }}
  .c-orange {{ color: #e67e22; }}
  .c-gray   {{ color: #7f8c8d; }}
  .row-count {{ margin-left: auto; font-size: 12px; color: #666; }}

  /* ── Table wrapper ── */
  .table-wrap {{ overflow-x: auto; padding: 0 20px 40px; }}
  table {{
    width: 100%; min-width: 1100px; border-collapse: collapse;
    background: #fff; border-radius: 8px; overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-top: 16px;
  }}
  thead th {{
    background: #2d6a4f; color: #fff; padding: 10px 12px;
    text-align: left; font-size: 12px; font-weight: 600; white-space: nowrap;
    cursor: pointer; user-select: none;
  }}
  thead th:hover {{ background: #1b4332; }}
  thead th .sort-arrow {{ margin-left: 4px; opacity: .5; }}
  thead th.sorted .sort-arrow {{ opacity: 1; }}

  tbody tr:nth-child(even) {{ filter: brightness(.97); }}
  tbody tr:hover {{ filter: brightness(.93); }}

  td {{ padding: 8px 12px; border-bottom: 1px solid #e8f0e8; vertical-align: top; }}
  .mono  {{ font-family: "SF Mono", "Consolas", monospace; font-size: 11.5px; }}
  .num   {{ text-align: right; white-space: nowrap; }}
  .notes {{ font-size: 11.5px; color: #444; max-width: 260px; }}

  /* ── Row colors ── */
  .row-overpriced {{ background: #fdecea !important; }}
  .row-raise      {{ background: #eafaf1 !important; }}
  .row-review     {{ background: #fef6ec !important; }}
  .row-hold       {{ background: #ffffff !important; }}

  /* ── Badges ── */
  .badge {{ padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
  .badge-overpriced {{ background: #fde8e8; color: #c0392b; }}
  .badge-raise      {{ background: #d5f5e3; color: #1e8449; }}
  .badge-hold       {{ background: #eaecee; color: #5d6d7e; }}
  .badge-review     {{ background: #fdebd0; color: #ca6f1e; }}

  /* ── Margin colors ── */
  .mg-green  {{ color: #1e8449; font-weight: 600; }}
  .mg-yellow {{ color: #b7950b; font-weight: 600; }}
  .mg-red    {{ color: #c0392b; font-weight: 600; }}

  /* ── Loss warning ── */
  .loss-warn {{ color: #c0392b; font-weight: 700; }}

  /* ── Hidden rows ── */
  tr.hidden {{ display: none; }}
</style>
</head>
<body>

<div class="site-header">
  <div>
    <h1>Nature's Seed — Pricing &amp; COGS Report</h1>
    <div class="subtitle">Published products only &nbsp;·&nbsp; Generated {time.strftime('%B %d, %Y')}</div>
  </div>
</div>

<div class="controls">
  <div class="controls-row">
    <input class="search-box" id="searchBox" type="text" placeholder="Search SKU or product name…"
           oninput="applyFilters()">
    <label class="toggle">
      <input type="checkbox" id="priorityOnly" onchange="applyFilters()">
      Priority actions only (hide Hold)
    </label>
    <button class="btn-export" onclick="exportCsv()">Export CSV</button>
  </div>
  <div class="pills" id="catPills">
    {cat_pills}
  </div>
</div>

<div class="summary-bar">
  <div class="lbl">Published matches: <strong>{len(published_recs)}</strong></div>
  <div class="count-chip"><span class="num c-red">{verdict_counts.get('overpriced', 0)}</span><span class="lbl">Overpriced</span></div>
  <div class="count-chip"><span class="num c-green">{verdict_counts.get('raise', 0)}</span><span class="lbl">Raise</span></div>
  <div class="count-chip"><span class="num c-gray">{verdict_counts.get('hold', 0)}</span><span class="lbl">Hold</span></div>
  <div class="count-chip"><span class="num c-orange">{verdict_counts.get('review', 0)}</span><span class="lbl">Review</span></div>
  <div class="row-count" id="rowCount"></div>
</div>

<div class="table-wrap">
<table id="pricingTable">
  <thead>
    <tr>
      <th onclick="sortTable(0)">Category <span class="sort-arrow">↕</span></th>
      <th onclick="sortTable(1)">Parent SKU <span class="sort-arrow">↕</span></th>
      <th onclick="sortTable(2)">Product Name <span class="sort-arrow">↕</span></th>
      <th onclick="sortTable(3)" class="num">Unit Cost <span class="sort-arrow">↕</span></th>
      <th onclick="sortTable(4)" class="num">Current Price <span class="sort-arrow">↕</span></th>
      <th onclick="sortTable(5)" class="num">Margin % <span class="sort-arrow">↕</span></th>
      <th onclick="sortTable(6)">Market $/lb <span class="sort-arrow">↕</span></th>
      <th onclick="sortTable(7)">Verdict <span class="sort-arrow">↕</span></th>
      <th onclick="sortTable(8)" class="num">Rec Price <span class="sort-arrow">↕</span></th>
      <th onclick="sortTable(9)" class="num">New Margin % <span class="sort-arrow">↕</span></th>
      <th onclick="sortTable(10)">Notes <span class="sort-arrow">↕</span></th>
    </tr>
  </thead>
  <tbody id="tableBody">
{''.join(rows_html)}
  </tbody>
</table>
</div>

<script>
let currentCat = 'all';
let sortCol = -1;
let sortAsc = true;

function filterCat(cat) {{
  currentCat = cat;
  document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
  event.target.classList.add('active');
  applyFilters();
}}

function applyFilters() {{
  const search   = document.getElementById('searchBox').value.toLowerCase();
  const prioOnly = document.getElementById('priorityOnly').checked;
  const rows     = document.querySelectorAll('#tableBody tr');
  let visible = 0;
  rows.forEach(row => {{
    const cat     = row.dataset.category;
    const verdict = row.dataset.verdict;
    const sku     = row.dataset.sku;
    const name    = row.dataset.name;
    const catOk   = currentCat === 'all' || cat === currentCat;
    const prioOk  = !prioOnly || verdict !== 'hold';
    const srchOk  = !search || sku.includes(search) || name.includes(search);
    const show    = catOk && prioOk && srchOk;
    row.classList.toggle('hidden', !show);
    if (show) visible++;
  }});
  document.getElementById('rowCount').textContent = `Showing ${{visible}} of ${{rows.length}} products`;
}}

function sortTable(col) {{
  if (sortCol === col) {{ sortAsc = !sortAsc; }}
  else {{ sortCol = col; sortAsc = true; }}
  document.querySelectorAll('thead th').forEach((th, i) => {{
    th.classList.toggle('sorted', i === col);
    const arrow = th.querySelector('.sort-arrow');
    if (i === col) arrow.textContent = sortAsc ? '↑' : '↓';
    else arrow.textContent = '↕';
  }});
  const tbody = document.getElementById('tableBody');
  const rows  = Array.from(tbody.querySelectorAll('tr'));
  rows.sort((a, b) => {{
    const aVal = a.cells[col].textContent.replace(/[^0-9.\-]/g, '') || a.cells[col].textContent;
    const bVal = b.cells[col].textContent.replace(/[^0-9.\-]/g, '') || b.cells[col].textContent;
    const aNum = parseFloat(aVal);
    const bNum = parseFloat(bVal);
    let cmp;
    if (!isNaN(aNum) && !isNaN(bNum)) {{ cmp = aNum - bNum; }}
    else {{ cmp = aVal.localeCompare(bVal); }}
    return sortAsc ? cmp : -cmp;
  }});
  rows.forEach(r => tbody.appendChild(r));
}}

function exportCsv() {{
  const headers = ['Category','Parent SKU','Product Name','Unit Cost','Current Price','Margin%','Market $/lb','Verdict','Rec Price','New Margin%','Notes'];
  const rows = Array.from(document.querySelectorAll('#tableBody tr:not(.hidden)'));
  const lines = [headers.join(',')];
  rows.forEach(row => {{
    const cells = Array.from(row.cells).map(c => `"${{c.textContent.replace(/"/g,'""').trim()}}"`);
    lines.push(cells.join(','));
  }});
  const blob = new Blob([lines.join('\\n')], {{type: 'text/csv'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'natures_seed_pricing_' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
}}

// Init row count on load
window.addEventListener('DOMContentLoaded', () => applyFilters());
</script>
</body>
</html>
"""

html_path = OUTPUT_DIR / "pricing_cogs_table.html"
html_path.write_text(HTML, encoding="utf-8")
print(f"\nHTML report saved: {html_path}")
print(f"\nDone. Published variable products: {len(variable_products)}, simple: {len(simple_products)}")
print(f"Variation SKUs: {len(variation_skus)}, Simple SKUs: {len(simple_skus)}")
print(f"Pricing recs matched: {len(published_recs)} / {len(PRICING_RECS)}")
