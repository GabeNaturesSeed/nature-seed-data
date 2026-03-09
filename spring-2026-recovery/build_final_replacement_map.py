#!/usr/bin/env python3
"""Build final consolidated replacement map with mix composition + bullet points."""

import json
import csv
import os
import re
from collections import defaultdict
from html.parser import HTMLParser

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
ANALYSIS_DIR = os.path.join(os.path.dirname(__file__), 'analysis')

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
    def handle_data(self, d):
        self.result.append(d.strip())
    def get_text(self):
        return ' '.join(t for t in self.result if t)

def strip_html(html):
    if not html:
        return ''
    e = HTMLTextExtractor()
    try:
        e.feed(str(html))
    except:
        return str(html)
    return e.get_text()

def extract_mix_from_html(html):
    """Extract species and percentages from product_content_2 HTML."""
    if not html:
        return []
    text = strip_html(html)
    species = []
    # Pattern: Species Name followed by percentage
    # Match things like "Perennial Ryegrass 30%" or "Tall Fescue 50%"
    # But skip prefix text like "What's in This Mix" or "This Mix"
    # Clean the text first
    text = re.sub(r"What'?s\s+[Ii]n\s+[Tt]his\s+[Mm]ix", "", text)
    text = re.sub(r"This\s+Mix", "", text)

    matches = re.findall(r'([A-Z][a-z]+(?:[\s-]+[A-Za-z]+){0,5}?)\s+(\d{1,3})%', text)
    seen = set()
    for name, pct in matches:
        name = name.strip()
        # Skip false positives
        if any(skip in name.lower() for skip in ['chosen for', 'selected for', 'provides', 'known for']):
            continue
        if name not in seen and int(pct) <= 100:
            species.append({'name': name, 'percentage': int(pct)})
            seen.add(name)
    return species

def base_product_name(name):
    """Strip size suffixes to get base product name."""
    name = re.sub(r'\s*-\s*\d+(?:\.\d+)?\s*(?:lb|lbs|oz)\s*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*-\s*(?:\d+(?:,\d+)?)\s*(?:ft|sq\s*ft|ft2|ft²).*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*-\s*(?:1/4|1/2|2\.5|0\.25|0\.5)\s*(?:acre|acres).*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*,\s*(?:Standard|Premium|Deluxe)\s+Mix\s*$', '', name, flags=re.IGNORECASE)
    return name.strip()

def main():
    active = json.load(open(os.path.join(DATA_DIR, 'products_active.json')))
    inactive = json.load(open(os.path.join(DATA_DIR, 'products_inactive.json')))

    # Build active product info with extracted mix data
    active_info = {}
    for p in active:
        meta = {m['key']: m['value'] for m in p.get('meta_data', [])}
        pc2 = meta.get('product_content_2', '')
        pc2_text = strip_html(pc2)
        mix = extract_mix_from_html(pc2)
        highlights = [meta.get(f'product_highlight_{i}', '') for i in range(1, 7)]
        highlights = [h for h in highlights if h]
        coverage = meta.get('product_coverage', '')

        active_info[p['sku']] = {
            'sku': p['sku'],
            'name': p['name'],
            'permalink': p['permalink'],
            'price': p['price'],
            'categories': [c['name'] for c in p.get('categories', [])],
            'image': p['images'][0]['src'] if p.get('images') else '',
            'description_text': pc2_text[:800],
            'mix_species': mix,
            'highlights': highlights,
            'coverage': coverage,
        }

    # Load replacement map from initial analysis
    with open(os.path.join(ANALYSIS_DIR, 'replacement_map.csv')) as f:
        replacements = list(csv.DictReader(f))

    # Consolidate by base old product name
    consolidated = defaultdict(lambda: {
        'old_base_name': '',
        'old_variants': [],
        'total_revenue': 0.0,
        'total_customers': 0,
        'total_units': 0,
        'best_new_sku': None,
        'best_score': 0,
        'customer_emails': set(),
    })

    # Also load orders to get email lists
    q1 = json.load(open(os.path.join(DATA_DIR, 'orders_q1_2025.json')))
    q2 = json.load(open(os.path.join(DATA_DIR, 'orders_q2_2025.json')))

    # Build SKU -> customer emails map
    sku_to_emails = defaultdict(set)
    for order in q1 + q2:
        email = order.get('customer_email', '').lower().strip()
        if not email:
            continue
        for li in order['line_items']:
            sku = li.get('sku', '')
            if sku:
                sku_to_emails[sku].add(email)

    for r in replacements:
        bn = base_product_name(r['old_name'])
        c = consolidated[bn]
        c['old_base_name'] = bn
        c['old_variants'].append(r['old_sku'])
        c['total_revenue'] += float(r['old_revenue_q1q2'])
        c['total_units'] += int(r['old_units_sold'])
        c['customer_emails'] |= sku_to_emails.get(r['old_sku'], set())

        score = int(r['match_score'])
        if score > c['best_score']:
            c['best_score'] = score
            c['best_new_sku'] = r['new_sku']

    # Build final output
    final_map = []
    for bn, data in sorted(consolidated.items(), key=lambda x: x[1]['total_revenue'], reverse=True):
        new_sku = data['best_new_sku']
        new = active_info.get(new_sku, {})
        if not new:
            continue

        # Generate bullet points based on mix data + product description
        bullets = generate_bullets(bn, new, data)

        final_map.append({
            'old_base_name': bn,
            'old_variant_count': len(data['old_variants']),
            'old_variant_skus': ';'.join(data['old_variants']),
            'total_revenue_q1q2': round(data['total_revenue'], 2),
            'total_units_sold': data['total_units'],
            'unique_customer_count': len(data['customer_emails']),
            'new_sku': new_sku,
            'new_name': new.get('name', ''),
            'new_permalink': new.get('permalink', ''),
            'new_price': new.get('price', ''),
            'new_image': new.get('image', ''),
            'new_categories': ', '.join(new.get('categories', [])),
            'mix_composition': '; '.join(f"{s['name']} {s['percentage']}%" for s in new.get('mix_species', [])),
            'match_score': data['best_score'],
            'bullet_1': bullets[0] if len(bullets) > 0 else '',
            'bullet_2': bullets[1] if len(bullets) > 1 else '',
            'bullet_3': bullets[2] if len(bullets) > 2 else '',
            'bullet_4': bullets[3] if len(bullets) > 3 else '',
        })

    # Write final consolidated replacement map
    with open(os.path.join(ANALYSIS_DIR, 'replacement_map_final.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(final_map[0].keys()))
        w.writeheader()
        w.writerows(final_map)

    # Also save as JSON for easier programmatic access
    # Convert sets to lists for JSON serialization
    json_data = []
    for bn, data in sorted(consolidated.items(), key=lambda x: x[1]['total_revenue'], reverse=True):
        new_sku = data['best_new_sku']
        new = active_info.get(new_sku, {})
        if not new:
            continue
        bullets = generate_bullets(bn, new, data)
        json_data.append({
            'old_base_name': bn,
            'old_variant_skus': data['old_variants'],
            'total_revenue': round(data['total_revenue'], 2),
            'unique_customers': len(data['customer_emails']),
            'new_product': new,
            'bullets': bullets,
            'match_score': data['best_score'],
        })

    with open(os.path.join(ANALYSIS_DIR, 'replacement_map_final.json'), 'w') as f:
        json.dump(json_data, f, indent=2)

    # Summary
    print(f"Final consolidated replacement map: {len(final_map)} unique products")
    print(f"Total revenue at risk: ${sum(r['total_revenue_q1q2'] for r in final_map):,.2f}")
    print(f"Total unique customers: {sum(r['unique_customer_count'] for r in final_map)}")
    print(f"\nSaved to:")
    print(f"  analysis/replacement_map_final.csv")
    print(f"  analysis/replacement_map_final.json")

    # Top 20
    print(f"\n{'='*100}")
    print(f"TOP 20 REPLACEMENTS (with bullets)")
    print(f"{'='*100}")
    for r in final_map[:20]:
        print(f"\n--- {r['old_base_name'][:50]} -> {r['new_name'][:50]} ---")
        print(f"    Revenue: ${r['total_revenue_q1q2']:,.2f} | Customers: {r['unique_customer_count']} | Score: {r['match_score']}")
        if r['mix_composition']:
            print(f"    Mix: {r['mix_composition'][:100]}")
        for i in range(1, 5):
            b = r.get(f'bullet_{i}', '')
            if b:
                print(f"    {i}. {b}")


def generate_bullets(old_name, new_product, data):
    """Generate 3-4 scientific + personable bullet points for a replacement."""
    bullets = []
    name = new_product.get('name', '')
    desc = new_product.get('description_text', '')
    mix = new_product.get('mix_species', [])
    cats = new_product.get('categories', [])
    highlights = new_product.get('highlights', [])
    coverage = new_product.get('coverage', '')
    price = new_product.get('price', '')

    old_lower = old_name.lower()
    new_lower = name.lower()

    # Bullet 1: Mix composition or key feature
    if mix:
        species_str = ', '.join(f"{s['name']} ({s['percentage']}%)" for s in mix[:4])
        bullets.append(f"Scientifically balanced blend of {species_str} — each species chosen for complementary growth habits and root structures.")
    elif desc:
        # Extract first key sentence from description
        first_sent = desc.split('.')[0].strip()
        if len(first_sent) > 20:
            bullets.append(first_sent + '.')

    # Bullet 2: Use-case / benefit
    use_cases = {
        'horse': "Formulated specifically for equine pastures — high palatability, safe for horses, and designed for heavy hoof traffic recovery.",
        'cattle': "Optimized for cattle grazing with high-yield forage species that maximize feed value per acre and support rotational grazing programs.",
        'sheep': "Selected for sheep-friendly grazing with species that tolerate close cropping and recover quickly between rotations.",
        'goat': "Designed for goat browsing habits with species that withstand aggressive grazing patterns and thrive in varied terrain.",
        'chicken': "Crafted for poultry foraging with nutrient-dense greens that support egg production and provide natural pest control in the run.",
        'pig': "Built for pig pastures with deep-rooted species that withstand rooting behavior and provide year-round forage.",
        'lawn': "Engineered for a dense, resilient lawn that handles foot traffic, recovers from wear, and stays green through seasonal changes.",
        'wildflower': "A carefully curated wildflower selection featuring native species adapted to your region's climate and soil conditions.",
        'pasture': "Purpose-built forage blend designed for productive grazing with species proven in real-world pasture conditions.",
        'clover': "Nitrogen-fixing legume that naturally enriches your soil while providing dense, attractive ground cover that crowds out weeds.",
        'fescue': "Deep-rooted fescue variety selected for drought tolerance, shade adaptation, and year-round color with minimal irrigation.",
        'conservation': "Designed for land stabilization and habitat restoration with native species that establish deep root networks for long-term erosion control.",
        'bermuda': "Warm-season grass engineered for heat tolerance, rapid establishment, and dense turf coverage in southern climates.",
        'buffalo': "Native prairie grass that thrives on natural rainfall — minimal mowing, no irrigation, and naturally pest-resistant for a true low-maintenance lawn.",
        'food plot': "Wildlife food plot blend timed for peak nutritional value during hunting season, attracting and holding game on your property.",
        'tortoise': "Habitat-specific forage blend with species safe for tortoises, providing both nutrition and natural shelter.",
        'deer': "Selected wildflower species that deer naturally avoid, giving you vibrant color in areas with heavy browse pressure.",
        'shade': "Shade-tolerant varieties that maintain density and color under tree canopy where standard grasses struggle.",
        'ryegrass': "Fast-establishing perennial ryegrass with improved turf density and dark green color — visible results in as little as 5-10 days.",
    }
    for keyword, bullet in use_cases.items():
        if keyword in old_lower or keyword in new_lower:
            bullets.append(bullet)
            break
    else:
        # Generic benefit
        if desc:
            sentences = [s.strip() for s in desc.split('.') if len(s.strip()) > 30]
            if len(sentences) > 1:
                bullets.append(sentences[1].strip() + '.')

    # Bullet 3: Climate / adaptability
    climate_bullets = {
        'northern': "Adapted for USDA zones 3-6 with cold-hardy species that establish quickly in cool soils and survive harsh winters.",
        'southern': "Selected for USDA zones 7-10 with heat-tolerant varieties that maintain productivity through hot summers and mild winters.",
        'transitional': "Versatile mix designed for the challenging transition zone (USDA zones 6-7) where both cool and warm-season species can thrive.",
        'california': "Native California species adapted to Mediterranean climate patterns — drought-tolerant once established, thriving on seasonal rainfall.",
        'pacific northwest': "Selected for the Pacific Northwest's cool, moist conditions with species that handle frequent rainfall and mild temperatures.",
        'drought': "Drought-engineered varieties with deep root systems that access subsoil moisture, maintaining productivity even during extended dry periods.",
        'cool season': "Cool-season species that peak during spring and fall, staying green through mild winters and handling light frost without damage.",
        'warm season': "Warm-season varieties that thrive in summer heat, going dormant in winter and returning vigorously each spring.",
    }
    for keyword, bullet in climate_bullets.items():
        if keyword in old_lower or keyword in new_lower or keyword in ' '.join(cats).lower():
            bullets.append(bullet)
            break

    # Bullet 4: Coverage / establishment or highlights
    if coverage:
        bullets.append(f"Coverage: {coverage}. Establishes within the first growing season with proper soil preparation and timing.")
    elif highlights:
        # Use product highlights
        hl_str = ' | '.join(highlights[:3])
        bullets.append(f"Key features: {hl_str}")
    elif price:
        bullets.append(f"Available now at ${price} — ships direct to your door, ready for spring planting season.")

    return bullets[:4]


if __name__ == '__main__':
    main()
