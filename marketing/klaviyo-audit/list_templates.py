"""List all Klaviyo templates, separating new design system ones from old."""
import requests
import urllib.parse

API_KEY = "pk_3e5eaeec142f867fd8fca1b1f7820852ad"
BASE_URL = "https://a.klaviyo.com/api"
HEADERS = {
    "Authorization": f"Klaviyo-API-Key {API_KEY}",
    "revision": "2024-10-15",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

cursor = None
all_templates = []
while True:
    params = {"sort": "-updated", "fields[template]": "name,created,updated,editor_type"}
    if cursor:
        params["page[cursor]"] = cursor
    r = requests.get(f"{BASE_URL}/templates/", headers=HEADERS, params=params)
    if r.status_code != 200:
        print(f"ERROR: {r.status_code}")
        break
    data = r.json()
    all_templates.extend(data.get("data", []))
    nxt = data.get("links", {}).get("next")
    if not nxt:
        break
    parsed = urllib.parse.urlparse(nxt)
    qs = urllib.parse.parse_qs(parsed.query)
    cursor = qs.get("page[cursor]", [None])[0]
    if not cursor:
        break

print(f"Total templates: {len(all_templates)}")

new_ones = [t for t in all_templates if t["attributes"].get("created", "").startswith("2026-03-06")]
print(f"\nNew templates created 2026-03-06 ({len(new_ones)}):")
for t in sorted(new_ones, key=lambda x: x["attributes"]["name"]):
    tid = t["id"]
    name = t["attributes"]["name"]
    print(f"  {tid} | {name}")

old_ones = [t for t in all_templates if not t["attributes"].get("created", "").startswith("2026-03-06")]
print(f"\nOlder templates ({len(old_ones)}):")
for t in sorted(old_ones, key=lambda x: x["attributes"]["name"]):
    tid = t["id"]
    name = t["attributes"]["name"]
    created = t["attributes"].get("created", "")[:10]
    print(f"  {tid} | {created} | {name}")
