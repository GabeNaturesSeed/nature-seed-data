#!/usr/bin/env python3
"""Upload 4 Seasonal Reorder email templates to Klaviyo and print their IDs.

Usage: python3 scripts/upload_seasonal_reorder_templates.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "marketing" / "klaviyo-audit"))

import requests

API_BASE = "https://a.klaviyo.com/api"
API_REVISION = "2024-07-15"

env_path = REPO_ROOT / ".env"
if not env_path.exists():
    print(f"[ERROR] .env not found at {env_path}", file=sys.stderr)
    sys.exit(1)

env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

KLAVIYO_API_KEY = env_vars.get("KLAVIYO_API")
if not KLAVIYO_API_KEY:
    print("[ERROR] KLAVIYO_API not set in .env", file=sys.stderr)
    sys.exit(1)

TEMPLATES = [
    {
        "filename": "email1.html",
        "name": "Seasonal Reorder — Email 1: Replant Moment",
    },
    {
        "filename": "email2.html",
        "name": "Seasonal Reorder — Email 2: Planting Guide",
    },
    {
        "filename": "email3.html",
        "name": "Seasonal Reorder — Email 3: Social Proof",
    },
    {
        "filename": "email4.html",
        "name": "Seasonal Reorder — Email 4: Seasonal Urgency",
    },
]

TEMPLATES_DIR = REPO_ROOT / "marketing" / "klaviyo-audit" / "seasonal-reorder"
headers = {
    "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
    "revision": API_REVISION,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

template_ids = {}

for t in TEMPLATES:
    html_path = TEMPLATES_DIR / t["filename"]
    if not html_path.exists():
        print(f"[ERROR] {html_path} not found", file=sys.stderr)
        sys.exit(1)

    html_content = html_path.read_text()
    payload = {
        "data": {
            "type": "template",
            "attributes": {
                "name": t["name"],
                "editor_type": "CODE",
                "html": html_content,
                "text": f"View this email in your browser.",
            },
        }
    }

    resp = requests.post(f"{API_BASE}/templates", headers=headers, json=payload, timeout=30)
    if resp.status_code == 201:
        template_id = resp.json()["data"]["id"]
        template_ids[t["filename"]] = template_id
        print(f"[OK] {t['name']} → {template_id}")
    else:
        print(f"[ERROR] {t['name']}: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

print("\n--- Template IDs (copy into flow-setup.md) ---")
for filename, tid in template_ids.items():
    print(f"{filename}: {tid}")
