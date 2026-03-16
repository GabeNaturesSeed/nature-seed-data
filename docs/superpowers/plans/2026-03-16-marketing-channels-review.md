# Marketing Channels Review Tab — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Marketing" tab to the GitHub Pages dashboard showing LTV, CAC, contribution margin, channel performance, and a 90-day daily spend/revenue table.

**Architecture:** New `generate_marketing()` function in `generate_data.py` pulls 12 months of WC orders + Google Ads spend, computes customer economics, and writes `marketing.json`. Dashboard `index.html` gets a new tab with KPI cards, channel table, and daily table — all following existing patterns.

**Tech Stack:** Python 3 (requests, google-ads), vanilla JS + Chart.js, Supabase PostgREST, WooCommerce REST API v3

**Spec:** `docs/superpowers/specs/2026-03-16-marketing-channels-review-design.md`

---

## Chunk 1: Data Generation (`generate_data.py`)

### Task 1: Add Google Ads 12-month pull helper

**Files:**
- Modify: `infrastructure/dashboard/generate_data.py` (after line 126, after `_wc_get`)

- [ ] **Step 1: Add Google Ads env vars and imports**

Add after the WC env vars block (line 75):

```python
# Google Ads (for marketing metrics — 12-month ad spend)
GADS_DEVELOPER_TOKEN = env_vars.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
GADS_CLIENT_ID = env_vars.get("GOOGLE_ADS_CLIENT_ID", "")
GADS_CLIENT_SECRET = env_vars.get("GOOGLE_ADS_CLIENT_SECRET", "")
GADS_REFRESH_TOKEN = env_vars.get("GOOGLE_ADS_REFRESH_TOKEN", "")
GADS_LOGIN_CID = env_vars.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
GADS_CUSTOMER_ID = env_vars.get("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")
COGS_SHEET_ID = env_vars.get("COGS_SHEET_ID", "1nve5yRvw7fY0caVqZDHYDjhoQmj_a6S9PkC3BMKm1S4")
```

Add to imports at top (line 28, after `import requests`):

```python
try:
    from google.ads.googleads.client import GoogleAdsClient
    HAS_GOOGLE_ADS = True
except ImportError:
    HAS_GOOGLE_ADS = False
```

- [ ] **Step 2: Add `_pull_google_ads_range()` helper**

Add after `_wc_get` (after line 126):

```python
def _pull_google_ads_range(start_date, end_date):
    """Pull aggregated Google Ads spend/conversions for a date range.
    Returns dict with spend, conversions_value, impressions, clicks.
    """
    if not HAS_GOOGLE_ADS or not GADS_DEVELOPER_TOKEN:
        print("    [SKIP] Google Ads not configured")
        return {"spend": 0, "conversions_value": 0, "impressions": 0, "clicks": 0}

    config = {
        "developer_token": GADS_DEVELOPER_TOKEN,
        "client_id": GADS_CLIENT_ID,
        "client_secret": GADS_CLIENT_SECRET,
        "refresh_token": GADS_REFRESH_TOKEN,
        "use_proto_plus": True,
    }
    if GADS_LOGIN_CID:
        config["login_customer_id"] = GADS_LOGIN_CID

    client = GoogleAdsClient.load_from_dict(config)
    ga_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
          AND campaign.status != 'REMOVED'
    """

    response = ga_service.search(customer_id=GADS_CUSTOMER_ID, query=query)
    rows = list(response)

    return {
        "spend": round(sum(r.metrics.cost_micros / 1_000_000 for r in rows), 2),
        "conversions_value": round(sum(r.metrics.conversions_value for r in rows), 2),
        "impressions": sum(r.metrics.impressions for r in rows),
        "clicks": sum(r.metrics.clicks for r in rows),
    }


def _pull_google_ads_daily(start_date, end_date):
    """Pull daily Google Ads spend/conversions for a date range.
    Returns list of dicts with date, spend, conversions_value.
    """
    if not HAS_GOOGLE_ADS or not GADS_DEVELOPER_TOKEN:
        return []

    config = {
        "developer_token": GADS_DEVELOPER_TOKEN,
        "client_id": GADS_CLIENT_ID,
        "client_secret": GADS_CLIENT_SECRET,
        "refresh_token": GADS_REFRESH_TOKEN,
        "use_proto_plus": True,
    }
    if GADS_LOGIN_CID:
        config["login_customer_id"] = GADS_LOGIN_CID

    client = GoogleAdsClient.load_from_dict(config)
    ga_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            segments.date,
            metrics.cost_micros,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
          AND campaign.status != 'REMOVED'
    """

    response = ga_service.search(customer_id=GADS_CUSTOMER_ID, query=query)

    daily = {}
    for row in response:
        d = row.segments.date
        if d not in daily:
            daily[d] = {"spend": 0, "conversions_value": 0}
        daily[d]["spend"] += row.metrics.cost_micros / 1_000_000
        daily[d]["conversions_value"] += row.metrics.conversions_value

    return [
        {"date": d, "spend": round(v["spend"], 2), "conversions_value": round(v["conversions_value"], 2)}
        for d, v in sorted(daily.items())
    ]
```

- [ ] **Step 3: Commit**

```bash
git add infrastructure/dashboard/generate_data.py
git commit -m "feat: add Google Ads range pull helpers to generate_data.py"
```

---

### Task 2: Add WC order pull and customer classification helpers

**Files:**
- Modify: `infrastructure/dashboard/generate_data.py` (after the Google Ads helpers)

- [ ] **Step 1: Add `_pull_wc_orders_range()` helper**

```python
def _pull_wc_orders_range(start_date, end_date):
    """Pull all WooCommerce orders in a date range. Returns list of order dicts.
    Uses CF Worker proxy if configured (for GitHub Actions).
    """
    all_orders = []
    page = 1
    after = f"{start_date}T00:00:00"
    before = f"{end_date}T23:59:59"

    while True:
        params = {
            "after": after,
            "before": before,
            "status": "completed,processing",
            "per_page": 100,
            "page": page,
        }
        resp = _wc_get("/orders", params)
        orders = resp.json()
        if not orders:
            break
        all_orders.extend(orders)
        page += 1
        time.sleep(0.3)

    return all_orders


def _pull_wc_customers_batch(customer_ids):
    """Fetch customer records to get date_created for new/returning classification.
    Uses WC 'include' param to batch-fetch up to 100 customers per request.
    Returns dict of {customer_id: date_created_str}.
    """
    result = {}
    ids = [cid for cid in customer_ids if cid and cid != 0]

    # Batch in chunks of 100 (WC API limit)
    for i in range(0, len(ids), 100):
        chunk = ids[i:i+100]
        try:
            params = {
                "include": ",".join(str(c) for c in chunk),
                "per_page": 100,
            }
            resp = _wc_get("/customers", params)
            for cust in resp.json():
                result[cust["id"]] = cust.get("date_created", "")
            time.sleep(0.3)
        except Exception as e:
            print(f"    [WARN] Customer batch fetch failed: {e}")
    return result
```

- [ ] **Step 2: Add COGS calculation helper**

```python
def _load_cogs_cache():
    """Load COGS lookup from Google Sheet (same as daily_pull.py pattern)."""
    url = f"https://docs.google.com/spreadsheets/d/{COGS_SHEET_ID}/export?format=csv"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"    [WARN] COGS sheet fetch failed: {e}")
        return {}

    cache = {}
    reader = csv.DictReader(io.StringIO(resp.text))
    for row in reader:
        sku = (row.get("SKU") or "").strip()
        cost_str = (row.get("Unit Cost") or "").strip()
        if not sku or not cost_str:
            continue
        unit_cost = _parse_dollar(cost_str)
        if unit_cost > 0:
            cache[sku] = unit_cost
    return cache


def _calculate_cogs_from_orders(orders, cogs_cache):
    """Calculate total COGS from order line items using the COGS lookup."""
    total_cogs = 0.0
    for order in orders:
        for item in order.get("line_items", []):
            sku = (item.get("sku") or "").strip()
            qty = item.get("quantity", 0)
            if sku in cogs_cache:
                total_cogs += cogs_cache[sku] * qty
    return round(total_cogs, 2)
```

- [ ] **Step 3: Commit**

```bash
git add infrastructure/dashboard/generate_data.py
git commit -m "feat: add WC order pull and COGS helpers for marketing metrics"
```

---

### Task 3: Implement `generate_marketing()` function

**Files:**
- Modify: `infrastructure/dashboard/generate_data.py` (before `main()`, around line 1285)

- [ ] **Step 1: Write the `generate_marketing()` function**

```python
def generate_marketing():
    """Generate marketing channel metrics: LTV, CAC, contribution margin, 90-day daily table."""
    print("\n[Marketing] Computing customer economics...")

    today = TODAY
    period_start = today - timedelta(days=365)
    period_90d_start = today - timedelta(days=90)
    yesterday = today - timedelta(days=1)

    # ── 1. Pull 12 months of WC orders ──────────────────────
    print("  Pulling 12 months of WooCommerce orders...")
    orders = _pull_wc_orders_range(str(period_start), str(yesterday))
    print(f"    Fetched {len(orders)} orders")

    if not orders:
        print("    [SKIP] No orders found — writing empty marketing.json")
        _write_json("marketing.json", {"generated_at": TODAY_STR, "error": "no_orders"})
        return True

    # ── 2. Customer segmentation ────────────────────────────
    # Group orders by customer
    customer_orders = {}  # {customer_key: [order_dates]}
    customer_revenue = {}  # {customer_key: total_revenue}
    guest_emails = {}  # {email: [order_dates]}

    total_revenue = 0.0
    for o in orders:
        rev = float(o.get("total", 0))
        total_revenue += rev
        cid = o.get("customer_id", 0)
        odate = o.get("date_created", "")[:10]

        if cid and cid != 0:
            customer_orders.setdefault(cid, []).append(odate)
            customer_revenue[cid] = customer_revenue.get(cid, 0) + rev
        else:
            email = (o.get("billing", {}).get("email") or "").lower().strip()
            if email:
                guest_emails.setdefault(email, []).append(odate)
                customer_revenue[f"guest_{email}"] = customer_revenue.get(f"guest_{email}", 0) + rev

    # Fetch customer date_created for new/returning classification
    registered_ids = list(customer_orders.keys())
    print(f"  Fetching {len(registered_ids)} customer records for classification...")
    customer_dates = _pull_wc_customers_batch(registered_ids)

    period_start_str = str(period_start)
    new_customers = 0
    returning_customers = 0

    for cid in registered_ids:
        created = customer_dates.get(cid, "")[:10]
        if created >= period_start_str:
            new_customers += 1
        else:
            returning_customers += 1

    # Guest orders: treat as new (no historical data)
    new_customers += len(guest_emails)

    unique_customers = len(registered_ids) + len(guest_emails)
    print(f"    Unique customers: {unique_customers} (new: {new_customers}, returning: {returning_customers})")

    # ── 3. Pull 12-month Google Ads spend ────────────────────
    print("  Pulling 12-month Google Ads spend...")
    try:
        ads_12m = _pull_google_ads_range(str(period_start), str(yesterday))
    except Exception as e:
        print(f"    [ERR] Google Ads 12m failed: {e}")
        ads_12m = {"spend": 0, "conversions_value": 0}

    total_ad_spend = ads_12m["spend"]
    total_conv_value = ads_12m["conversions_value"]

    # ── 4. COGS calculation ──────────────────────────────────
    print("  Calculating COGS from order line items...")
    cogs_cache = _load_cogs_cache()
    total_cogs = _calculate_cogs_from_orders(orders, cogs_cache)

    # Shipping: pull from Supabase (available data only)
    # Uses raw requests with list-of-tuples pattern (same as fetch_date_range in generate_reporting)
    print("  Pulling shipping costs from Supabase...")
    try:
        url = f"{SUPABASE_URL}/rest/v1/daily_shipping"
        headers = {"apikey": SUPABASE_KEY}
        params = [
            ("report_date", f"gte.{period_start}"),
            ("report_date", f"lte.{yesterday}"),
            ("select", "total_cost"),
        ]
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        shipping_rows = resp.json()
        total_shipping = sum(float(r.get("total_cost", 0)) for r in shipping_rows)
    except Exception:
        total_shipping = 0.0

    # ── 5. Compute widget metrics ────────────────────────────
    ltv = round(total_revenue / unique_customers, 2) if unique_customers else 0
    contribution_margin = round((total_revenue - total_cogs - total_shipping) / total_revenue, 4) if total_revenue else 0
    cac = round(total_ad_spend / unique_customers, 2) if unique_customers else 0
    ncac = round(total_ad_spend / new_customers, 2) if new_customers else 0
    max_cac_be = round(ltv * contribution_margin, 2)
    max_cac_20 = round(ltv * contribution_margin * 0.8, 2)
    payback = round(cac / (ltv / 12), 1) if ltv else 0
    ltv_cac = round(ltv / cac, 2) if cac else 0
    roas = round(total_conv_value / total_ad_spend, 2) if total_ad_spend else 0

    widgets = {
        "ltv_12m": ltv,
        "contribution_margin": contribution_margin,
        "cac": cac,
        "max_cac_breakeven": max_cac_be,
        "max_cac_20pct": max_cac_20,
        "ncac": ncac,
        "payback_months": payback,
        "ltv_cac_ratio": ltv_cac,
    }

    print(f"    LTV: ${ltv} | CM: {contribution_margin:.1%} | CAC: ${cac} | nCAC: ${ncac}")
    print(f"    Payback: {payback} mo | LTV:CAC: {ltv_cac}x | ROAS: {roas}x")

    # ── 6. Channel table (blended — single channel for now) ─
    channels = [{
        "name": "Google Ads",
        "cac": cac,
        "ltv": ltv,
        "ncac": ncac,
        "payback_months": payback,
        "revenue_contribution_pct": round(total_conv_value / total_revenue * 100, 1) if total_revenue else 0,
        "roas": roas,
    }]

    # ── 7. 90-day daily table ────────────────────────────────
    print("  Building 90-day daily table...")

    # Google Ads daily
    try:
        ads_daily = _pull_google_ads_daily(str(period_90d_start), str(yesterday))
    except Exception as e:
        print(f"    [ERR] Google Ads daily failed: {e}")
        ads_daily = []
    ads_by_date = {r["date"]: r for r in ads_daily}

    # WC daily revenue from Supabase
    # Uses raw requests with list-of-tuples pattern for duplicate key support
    try:
        url = f"{SUPABASE_URL}/rest/v1/daily_sales"
        headers = {"apikey": SUPABASE_KEY}
        params = [
            ("report_date", f"gte.{period_90d_start}"),
            ("report_date", f"lte.{yesterday}"),
            ("channel", "eq.woocommerce"),
            ("select", "report_date,revenue"),
        ]
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        wc_daily_rows = resp.json()
        wc_by_date = {r["report_date"]: float(r.get("revenue", 0)) for r in wc_daily_rows}
    except Exception:
        wc_by_date = {}

    daily_90d = []
    d = period_90d_start
    while d <= yesterday:
        ds = str(d)
        ads = ads_by_date.get(ds, {})
        spend = ads.get("spend", 0)
        conv_val = ads.get("conversions_value", 0)
        wc_rev = wc_by_date.get(ds, 0)
        mer = round(wc_rev / spend, 2) if spend > 0 else None

        daily_90d.append({
            "date": ds,
            "ad_spend": spend,
            "ad_spend_google": spend,
            "channel_revenue": conv_val,
            "wc_revenue": round(wc_rev, 2),
            "mer": mer,
        })
        d += timedelta(days=1)

    # ── 8. Write JSON ────────────────────────────────────────
    output = {
        "generated_at": TODAY_STR,
        "period_start": str(period_start),
        "period_end": str(yesterday),
        "total_customers": unique_customers,
        "new_customers": new_customers,
        "returning_customers": returning_customers,
        "total_revenue": round(total_revenue, 2),
        "total_ad_spend": total_ad_spend,
        "total_cogs": total_cogs,
        "total_shipping": round(total_shipping, 2),
        "widgets": widgets,
        "channels": channels,
        "daily_90d": daily_90d,
    }

    _write_json("marketing.json", output)
    print(f"  [OK] marketing.json written")
    return True
```

- [ ] **Step 2: Register in `main()` sources list**

In `main()` (line ~1300), add to the `sources` list after the Notes entry:

```python
        ("Marketing (Channels)", generate_marketing),
```

- [ ] **Step 3: Commit**

```bash
git add infrastructure/dashboard/generate_data.py
git commit -m "feat: implement generate_marketing() for customer economics and 90-day table"
```

---

### Task 4: Test data generation locally

**Files:**
- Run: `infrastructure/dashboard/generate_data.py`
- Verify: `docs/data/marketing.json`

- [ ] **Step 1: Run generate_data.py locally**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
python3 infrastructure/dashboard/generate_data.py
```

Expected: Script completes, prints Marketing section output with LTV/CAC numbers, writes `docs/data/marketing.json`.

- [ ] **Step 2: Verify marketing.json structure**

Check that `marketing.json` has: `widgets`, `channels`, `daily_90d` arrays with expected fields. Spot-check that LTV > 0, CAC > 0, daily_90d has ~90 entries.

- [ ] **Step 3: Fix any issues and commit**

```bash
git add docs/data/marketing.json infrastructure/dashboard/generate_data.py
git commit -m "fix: resolve any data generation issues for marketing metrics"
```

---

## Chunk 2: Dashboard UI (`index.html`)

### Task 5: Add Marketing tab button and panel HTML

**Files:**
- Modify: `docs/index.html`

- [ ] **Step 1: Add Marketing main tab button**

After the Inventory tab (line 491):

```html
<div class="main-tab" data-tab="marketing" onclick="switchMain('marketing', this)">Marketing</div>
```

- [ ] **Step 2: Add Marketing panel div**

After `panel-forecasting` (line 519), before the closing `</div>`:

```html
  <div id="panel-marketing" class="panel"></div>
```

- [ ] **Step 3: Update JavaScript tab routing**

In `mainPanelMap` (line ~558), add:

```javascript
marketing: ['marketing'],
```

No sub-tabs needed, so no entry in `subGroups`.

- [ ] **Step 4: Commit**

```bash
git add docs/index.html
git commit -m "feat: add Marketing tab shell to dashboard"
```

---

### Task 6: Add `marketing.json` to data loading

**Files:**
- Modify: `docs/index.html` (loadAllData function, line ~650)

- [ ] **Step 1: Add 'marketing' to the files array in `loadAllData()`**

Change line ~651:

```javascript
const files = ['reporting','budget','klaviyo','amazon','walmart','inventory','notes','marketing'];
```

- [ ] **Step 2: Commit**

```bash
git add docs/index.html
git commit -m "feat: load marketing.json in dashboard data pipeline"
```

---

### Task 7: Implement `renderMarketing()` function

**Files:**
- Modify: `docs/index.html` (add after last render function, before `loadAllData`)

- [ ] **Step 1: Write the renderMarketing function**

Add before `loadAllData()`:

```javascript
function renderMarketing(marketing) {
  const el = document.getElementById('panel-marketing');
  if (!marketing || marketing.error) {
    el.innerHTML = '<div class="data-unavailable">Marketing data unavailable</div>';
    return;
  }

  const w = marketing.widgets || {};
  const channels = marketing.channels || [];
  const daily = marketing.daily_90d || [];

  // ── KPI Cards ──────────────────────────────────
  const kpis = [
    { label: '12-Month LTV', val: fmt(w.ltv_12m), sub: 'Avg customer value' },
    { label: 'Contribution Margin', val: w.contribution_margin != null ? (w.contribution_margin * 100).toFixed(1) + '%' : '—', sub: 'After COGS + shipping' },
    { label: 'Current CAC', val: fmt(w.cac), sub: `Break-even: ${fmt(w.max_cac_breakeven)} · 20% profit: ${fmt(w.max_cac_20pct)}` },
    { label: 'Payback Time', val: w.payback_months != null ? w.payback_months.toFixed(1) + ' mo' : '—', sub: 'Months to recover CAC' },
    { label: 'LTV:CAC', val: w.ltv_cac_ratio != null ? w.ltv_cac_ratio.toFixed(2) + 'x' : '—', sub: w.ltv_cac_ratio >= 3 ? 'Healthy' : w.ltv_cac_ratio >= 2 ? 'Marginal' : 'Needs improvement',
      color: w.ltv_cac_ratio >= 3 ? 'var(--green-med)' : w.ltv_cac_ratio >= 2 ? 'var(--yellow)' : 'var(--red)' },
    { label: 'nCAC', val: fmt(w.ncac), sub: 'New customers only' },
  ];

  let html = '<div style="padding:24px;">';
  html += '<h2 style="margin-bottom:16px;font-size:1.2rem;">Marketing Channels Review</h2>';
  html += `<div style="font-size:0.8rem;color:var(--gray);margin-bottom:16px;">Period: ${marketing.period_start} to ${marketing.period_end} · ${marketing.total_customers || 0} customers (${marketing.new_customers || 0} new, ${marketing.returning_customers || 0} returning)</div>`;

  // KPI grid
  html += '<div class="kpi-grid">';
  kpis.forEach(k => {
    const valStyle = k.color ? `color:${k.color}` : '';
    html += `<div class="kpi-card">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value" style="${valStyle}">${k.val}</div>
      <div class="kpi-meta" style="font-size:0.72rem;color:var(--gray);">${k.sub}</div>
    </div>`;
  });
  html += '</div>';

  // ── Channel Performance Table ──────────────────
  html += '<h3 style="margin:24px 0 12px;font-size:1rem;">Channel Performance</h3>';
  html += '<div style="font-size:0.72rem;color:var(--gray);margin-bottom:8px;">Note: Metrics are blended across all customers (no per-channel attribution yet)</div>';
  html += '<div style="overflow-x:auto;"><table class="data-table"><thead><tr>';
  html += '<th>Channel</th><th>CAC</th><th>LTV</th><th>nCAC</th><th>Payback</th><th>Rev Contribution</th><th>ROAS</th>';
  html += '</tr></thead><tbody>';
  channels.forEach(ch => {
    html += `<tr>
      <td><strong>${ch.name}</strong></td>
      <td>${fmt(ch.cac)}</td>
      <td>${fmt(ch.ltv)}</td>
      <td>${fmt(ch.ncac)}</td>
      <td>${ch.payback_months != null ? ch.payback_months.toFixed(1) + ' mo' : '—'}</td>
      <td>${ch.revenue_contribution_pct != null ? ch.revenue_contribution_pct.toFixed(1) + '%' : '—'}</td>
      <td>${ch.roas != null ? ch.roas.toFixed(2) + 'x' : '—'}</td>
    </tr>`;
  });
  html += '</tbody></table></div>';

  // ── 90-Day Daily Table ─────────────────────────
  html += '<h3 style="margin:24px 0 12px;font-size:1rem;">Last 90 Days — Daily Breakdown</h3>';
  html += '<div style="overflow-x:auto;max-height:600px;overflow-y:auto;"><table class="data-table"><thead style="position:sticky;top:0;background:var(--card);"><tr>';
  html += '<th>Date</th><th>Ad Spend</th><th>Google Ads</th><th>Channel Rev</th><th>WC Revenue</th><th>MER</th>';
  html += '</tr></thead><tbody>';

  // Reverse so newest first
  const reversed = [...daily].reverse();
  reversed.forEach(row => {
    html += `<tr>
      <td>${row.date}</td>
      <td>${fmt(row.ad_spend)}</td>
      <td>${fmt(row.ad_spend_google)}</td>
      <td>${fmt(row.channel_revenue)}</td>
      <td>${fmt(row.wc_revenue)}</td>
      <td>${row.mer != null ? row.mer.toFixed(2) + 'x' : '—'}</td>
    </tr>`;
  });
  html += '</tbody></table></div>';
  html += '</div>';

  el.innerHTML = html;
}
```

- [ ] **Step 2: Wire up renderMarketing in the data loading callback**

Find where other render functions are called after `loadAllData()` (search for `renderMtd(data.reporting)`). Add nearby:

```javascript
renderMarketing(data.marketing);
```

- [ ] **Step 3: Commit**

```bash
git add docs/index.html
git commit -m "feat: implement Marketing tab rendering with KPIs, channel table, and 90-day daily table"
```

---

### Task 8: Verify dashboard end-to-end

- [ ] **Step 1: Open dashboard locally**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/docs"
python3 -m http.server 8080
```

Open `http://localhost:8080` in browser. Click the "Marketing" tab. Verify:
- 6 KPI cards render with values
- Channel table shows Google Ads row
- 90-day daily table scrolls and shows dates

- [ ] **Step 2: Check edge cases**

- Verify "—" displays for days with zero ad spend (MER column)
- Check that table is sorted newest-first
- Confirm KPI card styling matches existing MTD cards

- [ ] **Step 3: Final commit**

```bash
git add docs/index.html docs/data/marketing.json
git commit -m "feat: Marketing Channels Review tab complete — KPIs, channels, 90-day table"
```

---

## Summary of Files

| File | Action | Purpose |
|------|--------|---------|
| `infrastructure/dashboard/generate_data.py` | Modify | Add Google Ads helpers, WC order pull, COGS helpers, `generate_marketing()` |
| `docs/index.html` | Modify | Add Marketing tab, panel, `renderMarketing()`, wire up data loading |
| `docs/data/marketing.json` | Create (generated) | Output data file for dashboard |
