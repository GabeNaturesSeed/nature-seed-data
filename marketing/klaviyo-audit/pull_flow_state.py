"""Pull current state of all flows we're working on."""
import requests
import json

API_KEY = "pk_3e5eaeec142f867fd8fca1b1f7820852ad"
BASE_URL = "https://a.klaviyo.com/api"
HEADERS = {
    "Authorization": f"Klaviyo-API-Key {API_KEY}",
    "revision": "2024-10-15",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

flows = ["VvvqpW", "WQBF89", "UhxNKt", "HRmUgq", "Vzp5Nb", "SMZ5NX"]
flow_names = {
    "VvvqpW": "Winback Flow",
    "WQBF89": "Welcome Series (Upgraded)",
    "UhxNKt": "Shipment Flow",
    "HRmUgq": "New Customer Thank You (Post-Purchase)",
    "Vzp5Nb": "Seasonal Re-Order",
    "SMZ5NX": "Usage-Based Reorder",
}

for fid in flows:
    print(f"\n===== {flow_names[fid]} ({fid}) =====")
    r = requests.get(f"{BASE_URL}/flows/{fid}/flow-actions/", headers=HEADERS)
    if r.status_code != 200:
        print(f"  ERROR: {r.status_code}")
        continue
    actions = r.json().get("data", [])
    for a in actions:
        aid = a["id"]
        atype = a["attributes"]["action_type"]
        status = a["attributes"]["status"]
        settings = a["attributes"].get("settings", {})
        print(f"  Action {aid} | {atype} | status={status}")
        if atype == "SEND_EMAIL":
            r2 = requests.get(f"{BASE_URL}/flow-actions/{aid}/flow-messages/", headers=HEADERS)
            if r2.status_code == 200:
                msgs = r2.json().get("data", [])
                for m in msgs:
                    mid = m["id"]
                    content = m["attributes"].get("content", {})
                    name = m["attributes"].get("name", "unnamed")
                    subj = content.get("subject", "")
                    r3 = requests.get(f"{BASE_URL}/flow-messages/{mid}/relationships/template/", headers=HEADERS)
                    tmpl_id = "unknown"
                    if r3.status_code == 200:
                        tmpl_data = r3.json().get("data")
                        if tmpl_data:
                            tmpl_id = tmpl_data.get("id", "none")
                        else:
                            tmpl_id = "none"
                    print(f'    Message {mid}: "{name}"')
                    print(f"      Subject: {subj}")
                    print(f"      Template: {tmpl_id}")
        elif atype == "TIME_DELAY":
            delay = settings.get("delay", {})
            print(f"    Delay: {delay}")
        elif atype == "BOOLEAN_BRANCH":
            print(f"    Branch condition")
