"""
Build Klaviyo Knowledge Base from raw_klaviyo_data.json
Outputs:
  - FLOWS_KB.md       — all flows, statuses, email counts, revenue
  - CAMPAIGNS_KB.md   — all campaigns with dates, stats, subjects
  - REVENUE_KB.md     — monthly revenue, flow revenue, channel breakdown
  - AUDIENCES_KB.md   — lists, segments, subscription trends
  - BEHAVIOR_KB.md    — email engagement, open rates, client breakdown
"""

import json
import os
from collections import defaultdict

DIR = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(DIR, "raw_klaviyo_data.json")

with open(INPUT) as f:
    D = json.load(f)

flows     = D.get("flows", [])
campaigns = D.get("campaigns", [])
revenue   = D.get("revenue", {})
ls        = D.get("lists_segments", {})
metrics   = D.get("metrics", [])
templates = D.get("templates", [])

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def fmt_dollars(v):
    return f"${v:,.0f}"

def fmt_pct(num, denom):
    if denom == 0:
        return "n/a"
    return f"{num/denom*100:.1f}%"

def safe_sum(lst):
    return sum(x for x in lst if isinstance(x, (int, float)))

def get_monthly_series(key):
    """Return list of (date, value) tuples for first measurement of a metric."""
    block = revenue.get(key, {})
    dates = block.get("dates", [])
    data  = block.get("data", [])
    if not data or not dates:
        return []
    measurements = data[0].get("measurements", {})
    first_metric = list(measurements.values())[0] if measurements else []
    return list(zip(dates, first_metric))

def get_flow_revenue():
    """Return dict: flow_id -> {revenue, orders}"""
    block = revenue.get("revenue_by_flow_wc", {})
    dates = block.get("dates", [])
    data  = block.get("data", [])
    result = {}
    for item in data:
        dims = item.get("dimensions", [""])
        flow_id = dims[0] if dims else ""
        m = item.get("measurements", {})
        rev_arr = m.get("sum_value", [])
        cnt_arr = m.get("count", [])
        total_rev = safe_sum(rev_arr)
        total_cnt = safe_sum(cnt_arr)
        if flow_id and total_rev > 0:
            result[flow_id] = {"revenue": total_rev, "orders": total_cnt}
    return result

def get_message_revenue():
    """Return dict: message_id -> {revenue, orders}"""
    block = revenue.get("revenue_by_message_wc", {})
    data  = block.get("data", [])
    result = {}
    for item in data:
        dims = item.get("dimensions", [""])
        mid = dims[0] if dims else ""
        m = item.get("measurements", {})
        rev_arr = m.get("sum_value", [])
        cnt_arr = m.get("count", [])
        total_rev = safe_sum(rev_arr)
        total_cnt = safe_sum(cnt_arr)
        if mid and total_rev > 0:
            result[mid] = {"revenue": total_rev, "orders": total_cnt}
    return result

def get_channel_revenue():
    block = revenue.get("revenue_by_channel_wc", {})
    data  = block.get("data", [])
    result = {}
    for item in data:
        dims = item.get("dimensions", [""])
        ch = dims[0] if dims else "direct"
        m = item.get("measurements", {})
        rev_arr = m.get("sum_value", [])
        cnt_arr = m.get("count", [])
        result[ch] = {
            "revenue": safe_sum(rev_arr),
            "orders":  safe_sum(cnt_arr)
        }
    return result

def get_monthly_totals(key, metric_name):
    """Return list of (YYYY-MM, value)."""
    block = revenue.get(key, {})
    dates = block.get("dates", [])
    data  = block.get("data", [])
    if not data:
        return []
    m = data[0].get("measurements", {})
    vals = m.get(metric_name, [])
    result = []
    for date, val in zip(dates, vals):
        month = date[:7]  # YYYY-MM
        result.append((month, val))
    return result


# ─────────────────────────────────────────────
# 1. FLOWS KNOWLEDGE BASE
# ─────────────────────────────────────────────

flow_revenue = get_flow_revenue()

def build_flows_kb():
    lines = [
        "# Klaviyo Flows — Knowledge Base",
        f"> Extracted: {D.get('extracted_at','?')} | Total: {len(flows)} flows",
        "",
        "## Overview",
        "",
    ]

    live    = [f for f in flows if f.get("status") == "live"]
    draft   = [f for f in flows if f.get("status") == "draft"]
    manual  = [f for f in flows if f.get("status") == "manual"]
    archived= [f for f in flows if f.get("archived")]

    lines += [
        f"- **Live**: {len(live)}",
        f"- **Draft**: {len(draft)}",
        f"- **Manual**: {len(manual)}",
        f"- **Archived**: {len(archived)}",
        "",
        "---",
        "",
        "## Live Flows (Active — Revenue Generating)",
        "",
    ]

    # Sort live flows by revenue
    live_sorted = sorted(live, key=lambda f: flow_revenue.get(f["id"], {}).get("revenue", 0), reverse=True)

    for flow in live_sorted:
        fid   = flow["id"]
        name  = flow.get("name", "Unknown")
        rev   = flow_revenue.get(fid, {}).get("revenue", 0)
        orders= flow_revenue.get(fid, {}).get("orders", 0)
        msgs  = flow.get("messages", [])
        email_count = flow.get("email_count", len(msgs))
        trigger = flow.get("trigger_type", "?")
        created = (flow.get("created") or "")[:10]
        updated = (flow.get("updated") or "")[:10]

        lines += [
            f"### {name} (`{fid}`)",
            f"- **Status**: Live",
            f"- **Trigger**: {trigger}",
            f"- **Emails**: {email_count}",
            f"- **Revenue (4yr, email-attributed)**: {fmt_dollars(rev)}",
            f"- **Orders attributed**: {int(orders)}",
            f"- **Created**: {created} | **Updated**: {updated}",
        ]

        if msgs:
            lines.append("- **Messages**:")
            for msg in msgs:
                mid = msg.get("message_id","")
                msg_name = msg.get("name","(unnamed)")
                channel = msg.get("channel","email")
                action_status = msg.get("action_status","?")
                lines.append(f"  - `{mid}` — {msg_name} [{channel}/{action_status}]")
        lines.append("")

    lines += [
        "---",
        "",
        "## Draft Flows (In Development)",
        "",
        "| ID | Name | Emails | Last Updated |",
        "|----|------|--------|-------------|",
    ]

    for flow in sorted(draft, key=lambda f: f.get("updated",""), reverse=True):
        fid     = flow["id"]
        name    = flow.get("name","?")
        emails  = flow.get("email_count", 0)
        updated = (flow.get("updated") or "")[:10]
        lines.append(f"| `{fid}` | {name} | {emails} | {updated} |")

    lines += [
        "",
        "---",
        "",
        "## Flow Revenue Summary (WooCommerce Placed Order attribution)",
        "",
        "| Flow | Revenue | Orders | AOV |",
        "|------|---------|--------|-----|",
    ]

    for fid, rdata in sorted(flow_revenue.items(), key=lambda x: x[1]["revenue"], reverse=True):
        flow_name = next((f["name"] for f in flows if f["id"] == fid), fid)
        rev    = rdata["revenue"]
        orders = rdata["orders"]
        aov    = rev / orders if orders > 0 else 0
        lines.append(f"| {flow_name} (`{fid}`) | {fmt_dollars(rev)} | {int(orders)} | {fmt_dollars(aov)} |")

    lines += ["", "---", ""]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 2. CAMPAIGNS KNOWLEDGE BASE
# ─────────────────────────────────────────────

msg_revenue = get_message_revenue()

def build_campaigns_kb():
    lines = [
        "# Klaviyo Campaigns — Knowledge Base",
        f"> Extracted: {D.get('extracted_at','?')} | Total: {len(campaigns)} campaigns",
        "",
        "## Campaign Count by Status",
        "",
    ]

    by_status = defaultdict(list)
    for c in campaigns:
        by_status[c.get("status","?")].append(c)

    for status, clist in sorted(by_status.items()):
        lines.append(f"- **{status}**: {len(clist)}")

    lines += ["", "---", ""]

    # Extract campaigns with performance stats
    lines += [
        "## Campaigns With Performance Data (Recent — 2024+)",
        "",
        "| Campaign | Date | Recipients | Open Rate | Click Rate | Revenue |",
        "|----------|------|-----------|-----------|------------|---------|",
    ]

    campaigns_with_stats = []
    for camp in campaigns:
        for msg in camp.get("messages", []):
            stats = msg.get("stats", {})
            if stats:  # Only campaigns that have performance data
                campaigns_with_stats.append({
                    "campaign_name": camp["name"],
                    "campaign_id":   camp["id"],
                    "message_id":    msg.get("message_id",""),
                    "subject":       msg.get("subject",""),
                    "status":        camp.get("status",""),
                    "send_time":     camp.get("send_time") or msg.get("send_time",""),
                    "stats":         stats,
                    "revenue":       msg_revenue.get(msg.get("message_id",""), {}).get("revenue", 0),
                })

    # Sort by revenue desc
    for c in sorted(campaigns_with_stats, key=lambda x: x["revenue"], reverse=True)[:80]:
        stats     = c["stats"]
        recipients = stats.get("recipients", stats.get("delivered", 0))
        opens     = stats.get("opens", 0)
        clicks    = stats.get("clicks", 0)
        open_rate  = fmt_pct(opens, recipients) if recipients else "n/a"
        click_rate = fmt_pct(clicks, recipients) if recipients else "n/a"
        rev        = fmt_dollars(c["revenue"]) if c["revenue"] else "-"
        date       = (c.get("send_time") or "")[:10]
        name       = c["campaign_name"][:55]
        lines.append(f"| {name} | {date} | {recipients:,} | {open_rate} | {click_rate} | {rev} |")

    lines += ["", "---", ""]

    # Full campaign list by year
    lines += ["## All Campaigns by Year", ""]

    by_year = defaultdict(list)
    for camp in campaigns:
        created = camp.get("created_at") or camp.get("send_time") or ""
        year = created[:4] if created else "Unknown"
        by_year[year].append(camp)

    for year in sorted(by_year.keys(), reverse=True):
        clist = by_year[year]
        sent  = [c for c in clist if c.get("status","").lower() in ("sent","sending")]
        lines += [
            f"### {year} — {len(clist)} campaigns ({len(sent)} sent)",
            "",
        ]
        for camp in sorted(clist, key=lambda c: c.get("created_at",""), reverse=True):
            name   = camp.get("name","?")
            status = camp.get("status","?")
            date   = (camp.get("send_time") or camp.get("created_at",""))[:10]
            aud    = camp.get("audiences",{})
            inc    = ", ".join(aud.get("included", []))
            lines.append(f"- [{status}] **{name}** ({date}){' → '+inc if inc else ''}")
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# 3. REVENUE KNOWLEDGE BASE
# ─────────────────────────────────────────────

def build_revenue_kb():
    wc_monthly  = get_monthly_totals("monthly_revenue_wc", "sum_value")
    wc_orders   = get_monthly_totals("monthly_orders_wc",  "count")
    mag_monthly = get_monthly_totals("monthly_revenue_magento", "sum_value")
    receives    = get_monthly_totals("monthly_received",   "count")
    opens       = get_monthly_totals("monthly_opens",      "count")
    clicks      = get_monthly_totals("monthly_clicks",     "count")
    bounces     = get_monthly_totals("monthly_bounced",    "count")
    unsubs      = get_monthly_totals("monthly_unsubscribes","count")

    channel_rev = get_channel_revenue()

    lines = [
        "# Revenue & Email Performance — Knowledge Base",
        f"> Source: Klaviyo metric-aggregates (WooCommerce + Magento legacy) | {len(wc_monthly)} months of data",
        "",
        "## Revenue by Channel (WooCommerce Email Attribution, 4-Year Total)",
        "",
        "| Channel | Revenue | Orders |",
        "|---------|---------|--------|",
    ]
    total_ch_rev = sum(v["revenue"] for v in channel_rev.values())
    for ch, data in sorted(channel_rev.items(), key=lambda x: x[1]["revenue"], reverse=True):
        lines.append(f"| {ch or '(direct/none)'} | {fmt_dollars(data['revenue'])} | {int(data['orders'])} |")

    lines += [
        "",
        f"**Total email-attributed revenue (4yr)**: {fmt_dollars(total_ch_rev)}",
        "",
        "---",
        "",
        "## Monthly Revenue — WooCommerce (Email-Attributed)",
        "",
        "| Month | Revenue | Orders | Open Count | Click Count | Received | Bounced | Unsubs |",
        "|-------|---------|--------|------------|-------------|---------|---------|--------|",
    ]

    # Zip all series by month
    wc_rev_dict  = dict(wc_monthly)
    wc_ord_dict  = dict(wc_orders)
    rec_dict     = dict(receives)
    open_dict    = dict(opens)
    click_dict   = dict(clicks)
    bounce_dict  = dict(bounces)
    unsub_dict   = dict(unsubs)

    all_months = sorted(set(
        [m for m,_ in wc_monthly] +
        [m for m,_ in receives]
    ))

    for month in all_months:
        rev    = wc_rev_dict.get(month, 0)
        ords   = wc_ord_dict.get(month, 0)
        rec    = rec_dict.get(month, 0)
        opn    = open_dict.get(month, 0)
        clk    = click_dict.get(month, 0)
        bnc    = bounce_dict.get(month, 0)
        unsb   = unsub_dict.get(month, 0)
        lines.append(
            f"| {month} | {fmt_dollars(rev)} | {int(ords)} | "
            f"{int(opn):,} | {int(clk):,} | {int(rec):,} | {int(bnc):,} | {int(unsb):,} |"
        )

    lines += ["", "---", ""]

    # Annual summaries
    lines += ["## Annual Revenue Summary", "", "| Year | Email Revenue (WC) | Orders | Avg/Month |", "|------|-------------------|--------|-----------|"]
    annual = defaultdict(lambda: {"rev": 0.0, "orders": 0.0, "months": 0})
    for month, rev in wc_monthly:
        yr = month[:4]
        annual[yr]["rev"]    += rev
        annual[yr]["orders"] += wc_ord_dict.get(month, 0)
        annual[yr]["months"] += 1
    for yr in sorted(annual.keys()):
        a = annual[yr]
        avg = a["rev"] / a["months"] if a["months"] else 0
        lines.append(f"| {yr} | {fmt_dollars(a['rev'])} | {int(a['orders'])} | {fmt_dollars(avg)}/mo |")

    lines += ["", "---", ""]

    # Flow revenue table
    lines += [
        "## Revenue by Flow (WooCommerce Attribution, 4-Year Total)",
        "",
        "| Flow | Revenue | Orders | AOV |",
        "|------|---------|--------|-----|",
    ]
    for fid, rdata in sorted(flow_revenue.items(), key=lambda x: x[1]["revenue"], reverse=True):
        flow_name = next((f["name"] for f in flows if f["id"] == fid), fid)
        rev    = rdata["revenue"]
        orders = rdata["orders"]
        aov    = rev / orders if orders > 0 else 0
        lines.append(f"| {flow_name} | {fmt_dollars(rev)} | {int(orders)} | {fmt_dollars(aov)} |")

    lines += ["", "---", ""]

    # Legacy Magento revenue
    mag_total = sum(v for _, v in mag_monthly)
    if mag_total > 0:
        lines += [
            "## Legacy Magento Revenue (Pre-WooCommerce Migration)",
            "",
            f"Total Magento email-attributed revenue in window: {fmt_dollars(mag_total)}",
            "",
            "| Month | Revenue |",
            "|-------|---------|",
        ]
        for month, rev in mag_monthly:
            if rev > 0:
                lines.append(f"| {month} | {fmt_dollars(rev)} |")
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# 4. AUDIENCES KNOWLEDGE BASE
# ─────────────────────────────────────────────

def build_audiences_kb():
    lists    = ls.get("lists", [])
    segments = ls.get("segments", [])

    sub_monthly   = get_monthly_totals("monthly_subscribes", "count")
    unsub_monthly = get_monthly_totals("monthly_unsubscribes","count")

    lines = [
        "# Audiences — Lists, Segments & Subscription Trends",
        f"> Extracted: {D.get('extracted_at','?')} | {len(lists)} lists | {len(segments)} segments",
        "",
        "## Lists",
        "",
        "| ID | Name | Opt-in | Created |",
        "|----|------|--------|---------|",
    ]
    for lst in sorted(lists, key=lambda l: l.get("created","") or "", reverse=True):
        lines.append(
            f"| `{lst['id']}` | {lst.get('name','?')} | "
            f"{lst.get('opt_in_process','?')} | {(lst.get('created') or '')[:10]} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Starred Segments (Priority)",
        "",
        "| ID | Name | Created |",
        "|----|------|---------|",
    ]
    starred = [s for s in segments if s.get("is_starred")]
    for seg in sorted(starred, key=lambda s: s.get("name","")):
        lines.append(
            f"| `{seg['id']}` | {seg.get('name','?')} | {(seg.get('created') or '')[:10]} |"
        )

    lines += [
        "",
        "## All Segments by Category",
        "",
    ]

    # Group by inferred category
    cats = defaultdict(list)
    for seg in segments:
        name = seg.get("name","").lower()
        if "winback" in name or "win-back" in name or "lapsed" in name:
            cats["Re-engagement"].append(seg)
        elif "persona" in name or "purchaser" in name:
            cats["Purchase Behavior"].append(seg)
        elif "california" in name or "texas" in name or "heartland" in name or "regional" in name:
            cats["Regional"].append(seg)
        elif "bfcm" in name or "black friday" in name or "holiday" in name:
            cats["Seasonal/Promotional"].append(seg)
        elif "rfm" in name or "champion" in name or "vip" in name:
            cats["VIP/Loyalty"].append(seg)
        elif "cold" in name or "prospect" in name or "outlook" in name:
            cats["Prospecting"].append(seg)
        elif "pasture" in name:
            cats["Pasture Persona"].append(seg)
        elif "lawn" in name or "grass" in name or "turf" in name:
            cats["Lawn Persona"].append(seg)
        elif "wildflower" in name or "flower" in name or "pollinator" in name:
            cats["Wildflower Persona"].append(seg)
        elif "clover" in name or "cover crop" in name:
            cats["Clover/Cover Crop"].append(seg)
        else:
            cats["Other"].append(seg)

    for cat, segs in sorted(cats.items()):
        lines.append(f"### {cat} ({len(segs)})\n")
        for seg in sorted(segs, key=lambda s: s.get("name","")):
            starred_mark = " ★" if seg.get("is_starred") else ""
            lines.append(f"- `{seg['id']}` {seg.get('name','?')}{starred_mark}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Subscription Trends (Monthly)",
        "",
        "| Month | New Subscribers | Unsubscribes | Net |",
        "|-------|----------------|--------------|-----|",
    ]
    sub_dict   = dict(sub_monthly)
    unsub_dict = dict(unsub_monthly)
    all_months = sorted(set(list(sub_dict.keys()) + list(unsub_dict.keys())))
    for month in all_months:
        subs   = sub_dict.get(month, 0)
        unsubs = unsub_dict.get(month, 0)
        net    = subs - unsubs
        net_str = f"+{int(net)}" if net >= 0 else str(int(net))
        lines.append(f"| {month} | {int(subs):,} | {int(unsubs):,} | {net_str} |")

    lines += ["", "---", ""]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 5. BEHAVIOR KNOWLEDGE BASE
# ─────────────────────────────────────────────

def build_behavior_kb():
    rec_monthly   = get_monthly_totals("monthly_received",   "count")
    open_monthly  = get_monthly_totals("monthly_opens",      "count")
    click_monthly = get_monthly_totals("monthly_clicks",     "count")
    unsub_monthly = get_monthly_totals("monthly_unsubscribes","count")

    rec_dict   = dict(rec_monthly)
    open_dict  = dict(open_monthly)
    click_dict = dict(click_monthly)
    unsub_dict = dict(unsub_monthly)

    # Client breakdown
    client_block = revenue.get("opens_by_client", {})
    client_data  = client_block.get("data", [])
    client_totals = {}
    for item in client_data:
        dims = item.get("dimensions", ["?"])
        client = dims[0] if dims else "Unknown"
        cnt_arr = item.get("measurements", {}).get("count", [])
        total = safe_sum(cnt_arr)
        if total > 0:
            client_totals[client] = total

    lines = [
        "# User Behavior Analysis — 4-Year Overview",
        f"> Source: Klaviyo Metric Aggregates | {len(rec_monthly)} months of data",
        "",
        "## Email Engagement Summary (4-Year Totals)",
        "",
    ]

    total_received  = sum(v for _,v in rec_monthly)
    total_opens     = sum(v for _,v in open_monthly)
    total_clicks    = sum(v for _,v in click_monthly)
    total_unsubs    = sum(v for _,v in unsub_monthly)
    avg_open_rate   = fmt_pct(total_opens, total_received)
    avg_click_rate  = fmt_pct(total_clicks, total_received)

    lines += [
        f"| Metric | 4-Year Total |",
        f"|--------|-------------|",
        f"| Emails Delivered | {int(total_received):,} |",
        f"| Total Opens | {int(total_opens):,} |",
        f"| Total Clicks | {int(total_clicks):,} |",
        f"| Unsubscribes | {int(total_unsubs):,} |",
        f"| Overall Open Rate | {avg_open_rate} |",
        f"| Overall Click Rate | {avg_click_rate} |",
        f"| Unsubscribe Rate | {fmt_pct(total_unsubs, total_received)} |",
        "",
        "---",
        "",
        "## Monthly Engagement Trends",
        "",
        "| Month | Delivered | Opens | Clicks | Open Rate | CTR | Unsubs |",
        "|-------|-----------|-------|--------|-----------|-----|--------|",
    ]

    all_months = sorted(set(list(rec_dict.keys()) + list(open_dict.keys())))
    for month in all_months:
        rec    = rec_dict.get(month, 0)
        opn    = open_dict.get(month, 0)
        clk    = click_dict.get(month, 0)
        unsb   = unsub_dict.get(month, 0)
        or_    = fmt_pct(opn, rec)
        cr_    = fmt_pct(clk, rec)
        lines.append(
            f"| {month} | {int(rec):,} | {int(opn):,} | {int(clk):,} | {or_} | {cr_} | {int(unsb):,} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Email Client Distribution (4-Year Opens)",
        "",
        "| Email Client | Opens | % of Total |",
        "|-------------|-------|------------|",
    ]
    total_client_opens = sum(client_totals.values())
    for client, total in sorted(client_totals.items(), key=lambda x: x[1], reverse=True)[:20]:
        pct = fmt_pct(total, total_client_opens)
        lines.append(f"| {client} | {int(total):,} | {pct} |")

    lines += [
        "",
        "---",
        "",
        "## Seasonal Patterns (Annual Email Revenue vs Engagement)",
        "",
    ]

    # Calculate annual averages by calendar month (Jan=1 through Dec=12)
    monthly_avg = defaultdict(lambda: {"rev": [], "opens": [], "clicks": [], "rec": []})
    wc_rev_dict = dict(get_monthly_totals("monthly_revenue_wc","sum_value"))

    for month_key in all_months:
        cal_month = month_key[5:7]  # "01" through "12"
        monthly_avg[cal_month]["rev"].append(wc_rev_dict.get(month_key, 0))
        monthly_avg[cal_month]["opens"].append(open_dict.get(month_key, 0))
        monthly_avg[cal_month]["clicks"].append(click_dict.get(month_key, 0))
        monthly_avg[cal_month]["rec"].append(rec_dict.get(month_key, 0))

    month_names = {
        "01":"Jan","02":"Feb","03":"Mar","04":"Apr","05":"May","06":"Jun",
        "07":"Jul","08":"Aug","09":"Sep","10":"Oct","11":"Nov","12":"Dec"
    }

    lines += [
        "| Month | Avg Revenue | Avg Delivered | Avg Opens | Avg Open Rate |",
        "|-------|------------|--------------|-----------|---------------|",
    ]
    for cal in sorted(monthly_avg.keys()):
        avgs = monthly_avg[cal]
        avg_rev   = sum(avgs["rev"])   / len(avgs["rev"])   if avgs["rev"]   else 0
        avg_rec   = sum(avgs["rec"])   / len(avgs["rec"])   if avgs["rec"]   else 0
        avg_opn   = sum(avgs["opens"]) / len(avgs["opens"]) if avgs["opens"] else 0
        avg_or    = fmt_pct(avg_opn, avg_rec)
        lines.append(
            f"| {month_names[cal]} | {fmt_dollars(avg_rev)} | "
            f"{int(avg_rec):,} | {int(avg_opn):,} | {avg_or} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Key Behavioral Insights",
        "",
        "These patterns emerge from 4 years of Klaviyo data:",
        "",
    ]

    # Compute peak months by revenue
    sorted_rev = sorted(
        [(m, wc_rev_dict.get(m, 0)) for m in all_months],
        key=lambda x: x[1], reverse=True
    )
    top5 = sorted_rev[:5]
    lines.append("**Top 5 Revenue Months (Email-Attributed):**")
    for month, rev in top5:
        lines.append(f"- {month}: {fmt_dollars(rev)}")

    lines += [""]

    # Compute best engagement months
    sorted_ctr = []
    for month in all_months:
        rec = rec_dict.get(month, 0)
        clk = click_dict.get(month, 0)
        if rec > 1000:  # Only months with meaningful volume
            sorted_ctr.append((month, clk/rec))
    sorted_ctr.sort(key=lambda x: x[1], reverse=True)
    lines.append("**Top 5 Click-Rate Months (min 1,000 delivered):**")
    for month, ctr in sorted_ctr[:5]:
        lines.append(f"- {month}: {ctr*100:.1f}%")

    lines += ["", "---", ""]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# WRITE ALL FILES
# ─────────────────────────────────────────────

print("Building knowledge base files...")

files = {
    "FLOWS_KB.md":     build_flows_kb(),
    "CAMPAIGNS_KB.md": build_campaigns_kb(),
    "REVENUE_KB.md":   build_revenue_kb(),
    "AUDIENCES_KB.md": build_audiences_kb(),
    "BEHAVIOR_KB.md":  build_behavior_kb(),
}

for filename, content in files.items():
    path = os.path.join(DIR, filename)
    with open(path, "w") as f:
        f.write(content)
    lines = content.count("\n")
    print(f"  ✓ {filename} ({lines} lines)")

print("\nDone. Knowledge base saved to klaviyo-audit/")
