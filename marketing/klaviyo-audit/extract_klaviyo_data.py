"""
Klaviyo 4-Year Historical Audit Extractor
Nature's Seed — pulls flows, campaigns, revenue, profiles, behavior
API revision: 2024-10-15
"""

import requests
import json
import time
import os
from datetime import datetime

API_KEY    = "pk_3e5eaeec142f867fd8fca1b1f7820852ad"
REVISION   = "2024-10-15"
BASE_URL   = "https://a.klaviyo.com/api"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

HEADERS = {
    "Authorization": f"Klaviyo-API-Key {API_KEY}",
    "revision":      REVISION,
    "Content-Type":  "application/json",
    "Accept":        "application/json",
}

START_DATE  = "2022-01-01T00:00:00"
END_DATE    = "2026-03-05T23:59:59"
DATE_FILTER = f"greater-or-equal(datetime,{START_DATE}),less-or-equal(datetime,{END_DATE})"

# Metric IDs
METRIC_WC_ORDER   = "VLbLXB"
METRIC_MAG_ORDER  = "MpBr6v"
METRIC_WC_ITEM    = "WpcPAe"
METRIC_OPENED     = "LBjRM6"
METRIC_CLICKED    = "JgwbZn"
METRIC_RECEIVED   = "NpKKhz"
METRIC_BOUNCED    = "MTYddd"
METRIC_UNSUB_MKT  = "UwnyvV"
METRIC_SUB_LIST   = "JPFQsA"
METRIC_UNSUB_LIST = "Mn5m7r"


def get_all(path, params=None):
    url = f"{BASE_URL}/{path}"
    results = []
    while url:
        r = requests.get(url, headers=HEADERS, params=params)
        if r.status_code == 429:
            print("    [rate limit] waiting 15s...")
            time.sleep(15)
            continue
        if r.status_code == 404:
            break  # old/unsupported endpoint — skip silently
        if r.status_code != 200:
            print(f"    ERROR {r.status_code}: {r.text[:180]}")
            break
        d = r.json()
        items = d.get("data", [])
        if isinstance(items, list):
            results.extend(items)
        elif isinstance(items, dict):
            results.append(items)
        url    = d.get("links", {}).get("next")
        params = None
        time.sleep(0.25)
    return results


def post_api(path, payload):
    url = f"{BASE_URL}/{path}"
    for attempt in range(3):
        r = requests.post(url, headers=HEADERS, json=payload)
        if r.status_code == 429:
            wait = 15 * (attempt + 1)
            print(f"    [rate limit] waiting {wait}s...")
            time.sleep(wait)
            continue
        if r.status_code not in (200, 201, 202):
            print(f"    ERROR {r.status_code}: {r.text[:300]}")
            return {}
        return r.json()
    return {}


def metric_agg(metric_id, measurements, group_by=None):
    """
    POST /api/metric-aggregates
    Valid `by` values: $attributed_channel, $attributed_flow, $attributed_message,
                       $attributed_variation, Bounce Type, Client Canonical Name,
                       Client Name, Client Type, Email Domain, List, Variation, etc.
    Valid intervals: day, week, month
    sort must be omitted or be a valid dimension name
    """
    attrs = {
        "metric_id":    metric_id,
        "measurements": measurements,
        "interval":     "month",
        "page_size":    500,
        "filter":       DATE_FILTER,
    }
    if group_by:
        attrs["by"] = [group_by]

    return post_api("metric-aggregates", {
        "data": {"type": "metric-aggregate", "attributes": attrs}
    })


# ─────────────────────────────────────────────
# 1. FLOWS
# ─────────────────────────────────────────────

def extract_flows():
    print("\n=== FLOWS ===")
    flows = get_all("flows", {
        "fields[flow]": "name,status,trigger_type,created,updated,archived",
        "sort": "-updated"
    })
    print(f"  {len(flows)} flows total")

    flow_data = []
    for flow in flows:
        fid  = flow["id"]
        attr = flow.get("attributes", {})
        print(f"  [{attr.get('status','?'):8}] {attr.get('name', fid)[:65]}")

        actions = get_all(f"flows/{fid}/flow-actions", {
            "fields[flow-action]": "action_type,status,created,updated",
            "filter": "equals(action_type,'SEND_EMAIL')"
        })

        messages = []
        for action in actions:
            aid      = action["id"]
            act_attr = action.get("attributes", {})

            msgs = get_all(f"flow-actions/{aid}/flow-messages", {
                "fields[flow-message]": "name,created,updated,channel"
            })

            for msg in msgs:
                mid      = msg["id"]
                msg_attr = msg.get("attributes", {})
                messages.append({
                    "message_id":    mid,
                    "name":          msg_attr.get("name"),
                    "channel":       msg_attr.get("channel"),
                    "created":       msg_attr.get("created"),
                    "action_id":     aid,
                    "action_status": act_attr.get("status"),
                })

        flow_data.append({
            "id":           fid,
            "name":         attr.get("name"),
            "status":       attr.get("status"),
            "trigger_type": attr.get("trigger_type"),
            "created":      attr.get("created"),
            "updated":      attr.get("updated"),
            "archived":     attr.get("archived", False),
            "messages":     messages,
            "email_count":  len(messages),
        })

    return flow_data


# ─────────────────────────────────────────────
# 2. CAMPAIGNS
# ─────────────────────────────────────────────

def extract_campaigns():
    print("\n=== CAMPAIGNS ===")
    campaigns = get_all("campaigns", {
        "filter": "equals(messages.channel,'email')",
        "fields[campaign]": "name,status,created_at,scheduled_at,send_time,send_strategy,audiences",
        "sort": "-created_at"
    })
    print(f"  {len(campaigns)} campaigns total")

    campaign_data = []
    for camp in campaigns:
        cid  = camp["id"]
        attr = camp.get("attributes", {})
        name = attr.get("name", "")
        print(f"  [{attr.get('status','?'):10}] {name[:65]}")

        # Fetch messages (no field filter — let API return defaults)
        msgs = get_all(f"campaigns/{cid}/campaign-messages")

        msg_list = []
        for msg in msgs:
            mid      = msg["id"]
            msg_attr = msg.get("attributes", {})

            # Performance only exists for newer campaigns; 404 returns [] silently
            perf_items = get_all(f"campaign-messages/{mid}/campaign-message-performance")
            perf_stats = {}
            if perf_items:
                perf_stats = perf_items[0].get("attributes", {}).get("statistics", {})

            msg_list.append({
                "message_id":   mid,
                "channel":      msg_attr.get("channel"),
                "label":        msg_attr.get("label"),
                "status":       msg_attr.get("status"),
                "subject":      msg_attr.get("subject"),
                "preview_text": msg_attr.get("preview_text"),
                "send_time":    msg_attr.get("send_time"),
                "stats":        perf_stats,
            })
            time.sleep(0.15)

        campaign_data.append({
            "id":           cid,
            "name":         name,
            "status":       attr.get("status"),
            "created_at":   attr.get("created_at"),
            "scheduled_at": attr.get("scheduled_at"),
            "send_time":    attr.get("send_time"),
            "audiences":    attr.get("audiences", {}),
            "messages":     msg_list,
        })

    return campaign_data


# ─────────────────────────────────────────────
# 3. REVENUE & ENGAGEMENT AGGREGATES
# ─────────────────────────────────────────────

def extract_revenue():
    print("\n=== REVENUE & ENGAGEMENT AGGREGATES ===")
    out = {}

    queries = [
        # key                       metric_id           measurements                   group_by
        ("monthly_revenue_wc",      METRIC_WC_ORDER,    ["sum_value","count","unique"], None),
        ("monthly_revenue_magento", METRIC_MAG_ORDER,   ["sum_value","count","unique"], None),
        ("revenue_by_flow_wc",      METRIC_WC_ORDER,    ["sum_value","count"],          "$attributed_flow"),
        ("revenue_by_message_wc",   METRIC_WC_ORDER,    ["sum_value","count"],          "$attributed_message"),
        ("revenue_by_channel_wc",   METRIC_WC_ORDER,    ["sum_value","count"],          "$attributed_channel"),
        ("revenue_by_flow_mag",     METRIC_MAG_ORDER,   ["sum_value","count"],          "$attributed_flow"),
        ("monthly_received",        METRIC_RECEIVED,    ["count"],                      None),
        ("monthly_opens",           METRIC_OPENED,      ["count","unique"],             None),
        ("monthly_clicks",          METRIC_CLICKED,     ["count","unique"],             None),
        ("monthly_bounced",         METRIC_BOUNCED,     ["count"],                      None),
        ("monthly_unsubscribes",    METRIC_UNSUB_MKT,   ["count"],                      None),
        ("monthly_subscribes",      METRIC_SUB_LIST,    ["count"],                      None),
        ("monthly_orders_wc",       METRIC_WC_ORDER,    ["count","unique"],             None),
        ("opens_by_variation",      METRIC_OPENED,      ["count","unique"],             "Variation"),
        ("clicks_by_variation",     METRIC_CLICKED,     ["count","unique"],             "Variation"),
        ("email_client_opens",      METRIC_OPENED,      ["count"],                      "Client Name"),
    ]

    for key, metric_id, measurements, group_by in queries:
        print(f"  Querying: {key}...")
        out[key] = metric_agg(metric_id, measurements, group_by)
        time.sleep(0.5)

    return out


# ─────────────────────────────────────────────
# 4. LISTS & SEGMENTS
# ─────────────────────────────────────────────

def extract_lists_segments():
    print("\n=== LISTS & SEGMENTS ===")
    lists = get_all("lists", {
        "fields[list]": "name,created,updated,opt_in_process"
    })
    segs = get_all("segments", {
        "fields[segment]": "name,created,updated,is_starred"
    })
    print(f"  {len(lists)} lists, {len(segs)} segments")

    return {
        "lists": [{
            "id":             l["id"],
            "name":           l.get("attributes", {}).get("name"),
            "created":        l.get("attributes", {}).get("created"),
            "updated":        l.get("attributes", {}).get("updated"),
            "opt_in_process": l.get("attributes", {}).get("opt_in_process"),
        } for l in lists],
        "segments": [{
            "id":         s["id"],
            "name":       s.get("attributes", {}).get("name"),
            "created":    s.get("attributes", {}).get("created"),
            "updated":    s.get("attributes", {}).get("updated"),
            "is_starred": s.get("attributes", {}).get("is_starred", False),
        } for s in segs],
    }


# ─────────────────────────────────────────────
# 5. METRICS CATALOG
# ─────────────────────────────────────────────

def extract_metrics():
    print("\n=== METRICS ===")
    metrics = get_all("metrics", {
        "fields[metric]": "name,created,updated,integration"
    })
    print(f"  {len(metrics)} metrics")
    return [{
        "id":          m["id"],
        "name":        m.get("attributes", {}).get("name"),
        "created":     m.get("attributes", {}).get("created"),
        "integration": m.get("attributes", {}).get("integration", {}),
    } for m in metrics]


# ─────────────────────────────────────────────
# 6. TEMPLATES
# ─────────────────────────────────────────────

def extract_templates():
    print("\n=== TEMPLATES ===")
    templates = get_all("templates", {
        "fields[template]": "name,created,updated,editor_type",
        "sort": "-created"
    })
    print(f"  {len(templates)} templates")
    return [{
        "id":          t["id"],
        "name":        t.get("attributes", {}).get("name"),
        "created":     t.get("attributes", {}).get("created"),
        "updated":     t.get("attributes", {}).get("updated"),
        "editor_type": t.get("attributes", {}).get("editor_type"),
    } for t in templates]


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Nature's Seed — Klaviyo 4-Year Audit Extraction")
    print(f"Range: {START_DATE} → {END_DATE}")
    print("=" * 60)

    all_data = {"extracted_at": datetime.now().isoformat()}

    all_data["flows"]          = extract_flows()
    all_data["campaigns"]      = extract_campaigns()
    all_data["revenue"]        = extract_revenue()
    all_data["lists_segments"] = extract_lists_segments()
    all_data["metrics"]        = extract_metrics()
    all_data["templates"]      = extract_templates()

    out_path = os.path.join(OUTPUT_DIR, "raw_klaviyo_data.json")
    with open(out_path, "w") as f:
        json.dump(all_data, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print("EXTRACTION COMPLETE")
    print(f"  Flows:     {len(all_data['flows'])}")
    print(f"  Campaigns: {len(all_data['campaigns'])}")
    print(f"  Templates: {len(all_data['templates'])}")
    print(f"  Lists:     {len(all_data['lists_segments']['lists'])}")
    print(f"  Segments:  {len(all_data['lists_segments']['segments'])}")
    print(f"  Saved →    {out_path}")


if __name__ == "__main__":
    main()
