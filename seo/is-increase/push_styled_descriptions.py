#!/usr/bin/env python3
"""
Push styled category descriptions + FAQ schema to WooCommerce.

Reads styled_batch1.json, styled_batch2.json, styled_batch3.json,
styled_small_categories.json — pushes description_text to WC category
descriptions, and collects FAQ data for schema injection.

Usage: python3 IS-Increase/push_styled_descriptions.py
"""
import requests
import os
import time
import json

# Parse .env (has spaces around = and quotes around values)
env = {}
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip("'\"")

WC_BASE = env.get('WC_BASE_URL', 'https://naturesseed.com/wp-json/wc/v3')
WC_AUTH = (env.get('WC_CK'), env.get('WC_CS'))

# Load all styled description files
all_descriptions = {}
all_faqs = {}
script_dir = os.path.dirname(os.path.abspath(__file__))

files_to_load = [
    'styled_batch1.json',
    'styled_batch2.json',
    'styled_batch3.json',
    'styled_small_categories.json',
]

for fname in files_to_load:
    fpath = os.path.join(script_dir, fname)
    if os.path.exists(fpath):
        with open(fpath) as f:
            data = json.load(f)
        print(f"Loaded {fname}: {len(data)} categories")
        for cat_id, cat_data in data.items():
            all_descriptions[cat_id] = {
                'name': cat_data['name'],
                'description_text': cat_data['description_text'],
                'word_count': cat_data.get('word_count', 0),
            }
            if 'faq' in cat_data and cat_data['faq']:
                all_faqs[cat_id] = cat_data['faq']
    else:
        print(f"SKIP {fname}: not found")

print(f"\nTotal: {len(all_descriptions)} descriptions, {len(all_faqs)} FAQ sets")
print()

# Push descriptions to WooCommerce
results = {}
for cat_id, cat_data in sorted(all_descriptions.items(), key=lambda x: x[1]['name']):
    name = cat_data['name']
    desc = cat_data['description_text']
    wc = cat_data.get('word_count', 'N/A')

    try:
        r = requests.put(
            f'{WC_BASE}/products/categories/{cat_id}',
            auth=WC_AUTH,
            json={'description': desc}
        )
        r.raise_for_status()
        results[cat_id] = {
            'name': name,
            'status': 'success',
            'http_code': r.status_code,
            'word_count': wc,
        }
        print(f"  ✅ {name} (ID:{cat_id}) — {wc} words — HTTP {r.status_code}")
    except Exception as e:
        results[cat_id] = {
            'name': name,
            'status': 'error',
            'error': str(e),
            'word_count': wc,
        }
        print(f"  ❌ {name} (ID:{cat_id}) — ERROR: {e}")

    time.sleep(0.3)

# Save results
results_path = os.path.join(script_dir, 'styled_push_results.json')
with open(results_path, 'w') as f:
    json.dump(results, f, indent=2)

success_count = sum(1 for r in results.values() if r['status'] == 'success')
print(f"\nDescriptions: {success_count}/{len(results)} pushed successfully")

# Save FAQ schema data as standalone JSON-LD file
# This can be used to populate the WordPress option via the REST endpoint
# or manually pasted into the Code Snippets plugin
faq_schema_path = os.path.join(script_dir, 'faq_schema_data.json')
with open(faq_schema_path, 'w') as f:
    json.dump(all_faqs, f, indent=2)
print(f"FAQ schema data saved to {faq_schema_path} ({len(all_faqs)} categories)")

# Generate individual JSON-LD files for reference/verification
schema_dir = os.path.join(script_dir, 'faq_schemas')
os.makedirs(schema_dir, exist_ok=True)
for cat_id, faqs in all_faqs.items():
    name = all_descriptions.get(cat_id, {}).get('name', f'Category {cat_id}')
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq['question'],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq['answer'],
                }
            }
            for faq in faqs
        ]
    }
    safe_name = name.lower().replace(' ', '_').replace('&', 'and').replace('/', '_')
    schema_path = os.path.join(schema_dir, f'{cat_id}_{safe_name}.json')
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)

print(f"Individual FAQ schema files saved to {schema_dir}/")
print("\nDone!")
