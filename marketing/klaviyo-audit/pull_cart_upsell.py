"""Pull Cart Abandonment + Upsell flow state."""
import requests

API_KEY = "pk_3e5eaeec142f867fd8fca1b1f7820852ad"
BASE_URL = "https://a.klaviyo.com/api"
HEADERS = {
    "Authorization": f"Klaviyo-API-Key {API_KEY}",
    "revision": "2024-10-15",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

for fid, fname in [("Y7Qm8F", "Cart Abandonment"), ("VZsFVy", "Upsell Flow")]:
    print(f"\n===== {fname} ({fid}) =====")
    r = requests.get(f"{BASE_URL}/flows/{fid}/", headers=HEADERS,
                     params={"fields[flow]": "name,status,trigger_type"})
    if r.status_code == 200:
        flow = r.json()["data"]
        print(f"  Status: {flow['attributes'].get('status')}")
        print(f"  Trigger: {flow['attributes'].get('trigger_type')}")
    else:
        print(f"  Flow fetch error: {r.status_code}")

    r2 = requests.get(f"{BASE_URL}/flows/{fid}/flow-actions/", headers=HEADERS)
    if r2.status_code == 200:
        actions = r2.json().get("data", [])
        for a in actions:
            aid = a["id"]
            atype = a["attributes"]["action_type"]
            status = a["attributes"]["status"]
            print(f"  Action {aid} | {atype} | status={status}")
            if atype == "SEND_EMAIL":
                r3 = requests.get(f"{BASE_URL}/flow-actions/{aid}/flow-messages/", headers=HEADERS)
                if r3.status_code == 200:
                    for m in r3.json().get("data", []):
                        mid = m["id"]
                        name = m["attributes"].get("name", "")
                        subj = m["attributes"].get("content", {}).get("subject", "")
                        r4 = requests.get(f"{BASE_URL}/flow-messages/{mid}/relationships/template/", headers=HEADERS)
                        tid = "unknown"
                        if r4.status_code == 200:
                            td = r4.json().get("data")
                            tid = td.get("id", "none") if td else "none"
                        print(f'    Msg {mid}: "{name}" | subj: {subj} | tmpl: {tid}')
            elif atype == "TIME_DELAY":
                print(f"    Delay")
            elif atype == "BOOLEAN_BRANCH":
                print(f"    Branch")
    else:
        print(f"  Actions fetch error: {r2.status_code}")
