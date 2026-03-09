"""
Pull metric-aggregates in yearly chunks, merge dates+data, append to raw_klaviyo_data.json
"""

import requests
import json
import time
import os

API_KEY  = "pk_3e5eaeec142f867fd8fca1b1f7820852ad"
BASE_URL = "https://a.klaviyo.com/api"
HEADERS  = {
    "Authorization": f"Klaviyo-API-Key {API_KEY}",
    "revision":      "2024-10-15",
    "Content-Type":  "application/json",
    "Accept":        "application/json",
}

# Max 1 year per request; iterate across 4-year window
YEAR_RANGES = [
    ("2022-01-01T00:00:00", "2023-01-01T00:00:00"),
    ("2023-01-01T00:00:00", "2024-01-01T00:00:00"),
    ("2024-01-01T00:00:00", "2025-01-01T00:00:00"),
    ("2025-01-01T00:00:00", "2026-01-01T00:00:00"),
    ("2026-01-01T00:00:00", "2026-03-07T00:00:00"),
]

METRIC_WC_ORDER  = "VLbLXB"
METRIC_MAG_ORDER = "MpBr6v"
METRIC_WC_ITEM   = "WpcPAe"
METRIC_OPENED    = "LBjRM6"
METRIC_CLICKED   = "JgwbZn"
METRIC_RECEIVED  = "NpKKhz"
METRIC_BOUNCED   = "MTYddd"
METRIC_UNSUB_MKT = "UwnyvV"
METRIC_SUB_LIST  = "JPFQsA"

OUTPUT = os.path.join(os.path.dirname(__file__), "raw_klaviyo_data.json")


def post_agg(metric_id, measurements, start, end_lt, group_by=None):
    date_f = f"greater-or-equal(datetime,{start}),less-than(datetime,{end_lt})"
    attrs = {
        "metric_id":    metric_id,
        "measurements": measurements,
        "interval":     "month",
        "page_size":    500,
        "filter":       date_f,
    }
    if group_by:
        attrs["by"] = [group_by]

    url = f"{BASE_URL}/metric-aggregates"
    for attempt in range(3):
        r = requests.post(url, headers=HEADERS, json={
            "data": {"type": "metric-aggregate", "attributes": attrs}
        })
        if r.status_code == 429:
            wait = 15 * (attempt + 1)
            print(f"    [rate limit] waiting {wait}s...")
            time.sleep(wait)
            continue
        if r.status_code not in (200, 201, 202):
            print(f"    ERROR {r.status_code}: {r.text[:200]}")
            return None
        return r.json()
    return None


def merge_yearly(yearly_responses):
    """
    Each response has:
      data.attributes.dates  = list of ISO date strings (one per month)
      data.attributes.data   = list of {dimensions, measurements: {metric: [val per month]}}

    Merge across years: combine dates and align measurement arrays.
    For grouped results (by dimension), merge per dimension value.
    """
    merged_dates = []
    # Dict: dimension_key -> {measurements: {metric: [values]}}
    merged_dims = {}

    for resp in yearly_responses:
        if not resp or "data" not in resp:
            continue
        attrs = resp["data"].get("attributes", {})
        dates = attrs.get("dates", [])
        data_arr = attrs.get("data", [])

        merged_dates.extend(dates)

        for item in data_arr:
            dim_key = tuple(item.get("dimensions", []))
            measurements = item.get("measurements", {})

            if dim_key not in merged_dims:
                merged_dims[dim_key] = {k: [] for k in measurements}

            for metric, vals in measurements.items():
                merged_dims[dim_key].setdefault(metric, []).extend(vals)

    # Convert back to list format
    merged_data = []
    for dim_key, measurements in merged_dims.items():
        merged_data.append({
            "dimensions":   list(dim_key),
            "measurements": measurements,
        })

    return {
        "dates": merged_dates,
        "data":  merged_data,
    }


def query_all_years(metric_id, measurements, group_by=None):
    yearly = []
    for start, end_lt in YEAR_RANGES:
        res = post_agg(metric_id, measurements, start, end_lt, group_by)
        yearly.append(res)
        time.sleep(0.3)
    return merge_yearly(yearly)


def main():
    print("=== EXTRACTING METRIC AGGREGATES (4-year, yearly chunks) ===\n")
    revenue = {}

    queries = [
        ("monthly_revenue_wc",      METRIC_WC_ORDER,  ["sum_value","count","unique"], None),
        ("monthly_revenue_magento", METRIC_MAG_ORDER, ["sum_value","count","unique"], None),
        ("revenue_by_flow_wc",      METRIC_WC_ORDER,  ["sum_value","count"],          "$attributed_flow"),
        ("revenue_by_message_wc",   METRIC_WC_ORDER,  ["sum_value","count"],          "$attributed_message"),
        ("revenue_by_channel_wc",   METRIC_WC_ORDER,  ["sum_value","count"],          "$attributed_channel"),
        ("revenue_by_flow_mag",     METRIC_MAG_ORDER, ["sum_value","count"],          "$attributed_flow"),
        ("monthly_received",        METRIC_RECEIVED,  ["count"],                      None),
        ("monthly_opens",           METRIC_OPENED,    ["count","unique"],             None),
        ("monthly_clicks",          METRIC_CLICKED,   ["count","unique"],             None),
        ("monthly_bounced",         METRIC_BOUNCED,   ["count"],                      None),
        ("monthly_unsubscribes",    METRIC_UNSUB_MKT, ["count"],                      None),
        ("monthly_subscribes",      METRIC_SUB_LIST,  ["count"],                      None),
        ("monthly_orders_wc",       METRIC_WC_ORDER,  ["count","unique"],             None),
        ("opens_by_client",         METRIC_OPENED,    ["count"],                      "Client Name"),
    ]

    for key, metric_id, measurements, group_by in queries:
        print(f"  {key}...")
        revenue[key] = query_all_years(metric_id, measurements, group_by)
        dates_count = len(revenue[key].get("dates", []))
        data_count  = len(revenue[key].get("data", []))
        print(f"    → {dates_count} months, {data_count} dimension groups")
        time.sleep(0.2)

    # Merge into existing JSON
    existing = {}
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            existing = json.load(f)

    existing["revenue"] = revenue
    with open(OUTPUT, "w") as f:
        json.dump(existing, f, indent=2, default=str)

    print(f"\nSaved → {OUTPUT}")


if __name__ == "__main__":
    main()
