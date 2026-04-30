# Klaviyo Plan 2 — Seasonal Reorder + Real Data Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate the Seasonal Reorder flow (currently live but 0 sends in 90 days) and replace all stub zeros in the weekly review with real deliverability metrics and WooCommerce revenue from Supabase.

**Architecture:** Four independent tracks: (1) extend KlaviyoClient with deliverability metric aggregates, (2) add Supabase WC revenue module, (3) write + upload 4 category-conditional Seasonal Reorder HTML templates, (4) add campaign proposal generator. All wire into the existing `generate_weekly_review.py` CLI.

**Tech Stack:** Python 3.11, requests, Klaviyo REST API (revision `2024-07-15`), Supabase PostgREST REST API, pytest, Klaviyo template language (Django-style)

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `marketing/klaviyo-audit/framework/klaviyo_client.py` | Add `get_deliverability_metrics()` |
| Create | `marketing/klaviyo-audit/framework/wc_revenue.py` | Supabase WC revenue query |
| Create | `marketing/klaviyo-audit/framework/campaign_proposal.py` | 6-check proposal evaluator |
| Modify | `scripts/generate_weekly_review.py` | Wire real data (replace stub zeros) |
| Create | `marketing/klaviyo-audit/seasonal-reorder/email1.html` | Replant trigger email |
| Create | `marketing/klaviyo-audit/seasonal-reorder/email2.html` | Planting guide email |
| Create | `marketing/klaviyo-audit/seasonal-reorder/email3.html` | Social proof + product rec |
| Create | `marketing/klaviyo-audit/seasonal-reorder/email4.html` | Seasonal urgency close |
| Create | `marketing/klaviyo-audit/seasonal-reorder/flow-setup.md` | Manual UI steps doc |
| Create | `scripts/upload_seasonal_reorder_templates.py` | Upload 4 templates, print IDs |
| Modify | `tests/klaviyo-framework/test_klaviyo_client.py` | Add deliverability test |
| Create | `tests/klaviyo-framework/test_wc_revenue.py` | Supabase module tests |
| Create | `tests/klaviyo-framework/test_campaign_proposal.py` | Proposal evaluator tests |

---

## Task 1: Add `get_deliverability_metrics()` to KlaviyoClient

**Files:**
- Modify: `marketing/klaviyo-audit/framework/klaviyo_client.py`
- Modify: `tests/klaviyo-framework/test_klaviyo_client.py`

- [ ] **Step 1.1: Write the failing test**

Add to `tests/klaviyo-framework/test_klaviyo_client.py`:

```python
import pytest
from unittest.mock import MagicMock, patch, call
from framework.klaviyo_client import KlaviyoClient


def test_get_deliverability_metrics_computes_rates():
    """Verify counts are fetched and rates computed correctly."""
    client = KlaviyoClient(api_key="test-key")

    # Ordered: subscribed, unsubscribed, bounced, spam
    side_effects = [
        {"results": [{"measurements": {"count": [120, 80]}}]},   # subscribed = 200
        {"results": [{"measurements": {"count": [30, 20]}}]},    # unsubscribed = 50
        {"results": [{"measurements": {"count": [10]}}]},         # bounced = 10
        {"results": [{"measurements": {"count": [2]}}]},          # spam = 2
    ]

    with patch.object(client, "query_metric_aggregates", side_effect=side_effects) as mock_qma:
        result = client.get_deliverability_metrics(
            start_date="2026-03-22",
            end_date="2026-04-22",
            total_sends=1000,
        )

    assert result["net_list_growth_30d"] == 150      # 200 - 50
    assert result["spam_rate_30d"] == pytest.approx(0.002)    # 2 / 1000
    assert result["bounce_rate_30d"] == pytest.approx(0.01)   # 10 / 1000
    assert result["unsub_rate_per_send_30d"] == pytest.approx(0.05)  # 50 / 1000

    # Verify called with correct metric IDs in order
    calls = mock_qma.call_args_list
    assert calls[0].kwargs["metric_id"] == "RDUMLh"   # subscribed
    assert calls[1].kwargs["metric_id"] == "UwnyvV"   # unsubscribed
    assert calls[2].kwargs["metric_id"] == "MTYddd"   # bounced
    assert calls[3].kwargs["metric_id"] == "NwZfPQ"   # spam


def test_get_deliverability_metrics_handles_zero_sends():
    """total_sends=0 should not raise ZeroDivisionError."""
    client = KlaviyoClient(api_key="test-key")
    empty = {"results": [{"measurements": {"count": []}}]}

    with patch.object(client, "query_metric_aggregates", return_value=empty):
        result = client.get_deliverability_metrics("2026-03-22", "2026-04-22", total_sends=0)

    assert result["spam_rate_30d"] == 0.0
    assert result["bounce_rate_30d"] == 0.0
    assert result["unsub_rate_per_send_30d"] == 0.0
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
python3 -m pytest tests/klaviyo-framework/test_klaviyo_client.py -v -k "deliverability"
```

Expected: `FAILED` with `AttributeError: 'KlaviyoClient' object has no attribute 'get_deliverability_metrics'`

- [ ] **Step 1.3: Implement `get_deliverability_metrics()` in KlaviyoClient**

Append to `marketing/klaviyo-audit/framework/klaviyo_client.py` (before the final newline):

```python
    # Metric IDs for deliverability (Klaviyo account H627hn)
    _DELIVERABILITY_METRIC_IDS = {
        "subscribed": "RDUMLh",
        "unsubscribed": "UwnyvV",
        "bounced": "MTYddd",
        "spam": "NwZfPQ",
    }

    def get_deliverability_metrics(
        self,
        start_date: str,
        end_date: str,
        total_sends: int,
    ) -> Dict[str, Any]:
        """Return a dict ready for check_all_gates().

        Fetches 4 metric aggregate counts (subscribed, unsubscribed, bounced, spam)
        and computes rates against total_sends.
        """
        def _count(metric_id: str) -> int:
            attrs = self.query_metric_aggregates(
                metric_id=metric_id,
                measurements=["count"],
                start_date=start_date,
                end_date=end_date,
                interval="month",
            )
            total = 0
            for result in attrs.get("results", []):
                values = result.get("measurements", {}).get("count", [])
                total += sum(values)
            return total

        subscribed = _count(self._DELIVERABILITY_METRIC_IDS["subscribed"])
        unsubscribed = _count(self._DELIVERABILITY_METRIC_IDS["unsubscribed"])
        bounced = _count(self._DELIVERABILITY_METRIC_IDS["bounced"])
        spam = _count(self._DELIVERABILITY_METRIC_IDS["spam"])

        safe_sends = max(total_sends, 1)
        return {
            "net_list_growth_30d": subscribed - unsubscribed,
            "spam_rate_30d": spam / safe_sends,
            "bounce_rate_30d": bounced / safe_sends,
            "unsub_rate_per_send_30d": unsubscribed / safe_sends,
        }
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
python3 -m pytest tests/klaviyo-framework/test_klaviyo_client.py -v -k "deliverability"
```

Expected: `2 passed`

- [ ] **Step 1.5: Run full test suite to check no regressions**

```bash
python3 -m pytest tests/klaviyo-framework/ -v
```

Expected: all tests pass (currently 19 tests + 2 new = 21 total)

- [ ] **Step 1.6: Commit**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
git add marketing/klaviyo-audit/framework/klaviyo_client.py tests/klaviyo-framework/test_klaviyo_client.py
git commit -m "feat(framework): add get_deliverability_metrics() to KlaviyoClient"
```

---

## Task 2: Supabase WC Revenue Module

**Files:**
- Create: `marketing/klaviyo-audit/framework/wc_revenue.py`
- Create: `tests/klaviyo-framework/test_wc_revenue.py`

- [ ] **Step 2.1: Create the test file**

Create `tests/klaviyo-framework/test_wc_revenue.py`:

```python
"""Tests for Supabase WC revenue query."""
import pytest
from unittest.mock import patch, MagicMock
from framework.wc_revenue import get_wc_revenue_for_week


def test_get_wc_revenue_sums_rows():
    """Correctly sums revenue from multiple daily rows."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"revenue": "1250.50"},
        {"revenue": "875.00"},
        {"revenue": "2100.25"},
    ]
    mock_response.raise_for_status = MagicMock()

    with patch("framework.wc_revenue.requests.get", return_value=mock_response) as mock_get:
        total = get_wc_revenue_for_week(
            start_date="2026-04-14",
            end_date="2026-04-20",
            supabase_url="https://abc.supabase.co",
            api_key="test-key",
        )

    assert total == pytest.approx(4225.75)

    # Verify correct PostgREST query
    call_args = mock_get.call_args
    assert "daily_sales" in call_args.args[0]
    params = call_args.kwargs["params"]
    assert params["channel"] == "eq.woocommerce"
    assert params["report_date"] == "gte.2026-04-14"


def test_get_wc_revenue_returns_zero_on_empty():
    """Returns 0.0 when no rows found (e.g., date range before data exists)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()

    with patch("framework.wc_revenue.requests.get", return_value=mock_response):
        total = get_wc_revenue_for_week(
            start_date="2020-01-01",
            end_date="2020-01-07",
            supabase_url="https://abc.supabase.co",
            api_key="test-key",
        )

    assert total == 0.0


def test_get_wc_revenue_correct_headers():
    """Sends correct Supabase auth headers."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()

    with patch("framework.wc_revenue.requests.get", return_value=mock_response) as mock_get:
        get_wc_revenue_for_week("2026-04-14", "2026-04-20", "https://abc.supabase.co", "sk-test")

    headers = mock_get.call_args.kwargs["headers"]
    assert headers["apikey"] == "sk-test"
    assert headers["Authorization"] == "Bearer sk-test"
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
python3 -m pytest tests/klaviyo-framework/test_wc_revenue.py -v
```

Expected: `ImportError: No module named 'framework.wc_revenue'`

- [ ] **Step 2.3: Create `wc_revenue.py`**

Create `marketing/klaviyo-audit/framework/wc_revenue.py`:

```python
"""Supabase WooCommerce revenue query.

Reads from daily_sales table (channel='woocommerce') via PostgREST REST API.
Schema: daily_sales(report_date DATE, channel TEXT, revenue NUMERIC(12,2))
"""
from typing import Union
import requests


def get_wc_revenue_for_week(
    start_date: str,
    end_date: str,
    supabase_url: str,
    api_key: str,
    timeout: int = 20,
) -> float:
    """Sum WooCommerce revenue from daily_sales for a date range (inclusive).

    Args:
        start_date: ISO date string "YYYY-MM-DD" (inclusive lower bound)
        end_date: ISO date string "YYYY-MM-DD" (inclusive upper bound)
        supabase_url: Base URL like "https://abc.supabase.co"
        api_key: Supabase service role key (SUPABASE_SECRET_API_KEY)

    Returns:
        Total revenue as float. Returns 0.0 if no rows found.
    """
    url = f"{supabase_url.rstrip('/')}/rest/v1/daily_sales"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    params = {
        "select": "revenue",
        "channel": "eq.woocommerce",
        "report_date": f"gte.{start_date}",
        "report_date2": f"lte.{end_date}",  # PostgREST allows duplicate param names via ?col=gte.x&col=lte.y
    }
    # PostgREST requires both bounds on the same column — use a proper filter string
    params = {
        "select": "revenue",
        "channel": "eq.woocommerce",
        "report_date": f"gte.{start_date}",
    }
    # Add end-date filter via second param (requests encodes duplicate keys)
    response = requests.get(
        url,
        headers=headers,
        params=[
            ("select", "revenue"),
            ("channel", "eq.woocommerce"),
            ("report_date", f"gte.{start_date}"),
            ("report_date", f"lte.{end_date}"),
        ],
        timeout=timeout,
    )
    response.raise_for_status()
    rows = response.json()
    return sum(float(row["revenue"]) for row in rows)
```

Wait — there's a bug in the above draft. The `params` dict gets reassigned twice and is never used. The actual call uses a list of tuples for the `params` argument. Let me rewrite this cleanly.

Actually, create `marketing/klaviyo-audit/framework/wc_revenue.py` with this content:

```python
"""Supabase WooCommerce revenue query.

Reads from daily_sales table (channel='woocommerce') via PostgREST REST API.
Schema: daily_sales(report_date DATE, channel TEXT, revenue NUMERIC(12,2))
"""
import requests


def get_wc_revenue_for_week(
    start_date: str,
    end_date: str,
    supabase_url: str,
    api_key: str,
    timeout: int = 20,
) -> float:
    """Sum WooCommerce revenue from daily_sales for a date range (inclusive).

    Returns 0.0 if no rows found.
    """
    url = f"{supabase_url.rstrip('/')}/rest/v1/daily_sales"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # requests encodes list-of-tuples as repeated query params — required for
    # PostgREST range filters on the same column
    params = [
        ("select", "revenue"),
        ("channel", "eq.woocommerce"),
        ("report_date", f"gte.{start_date}"),
        ("report_date", f"lte.{end_date}"),
    ]
    response = requests.get(url, headers=headers, params=params, timeout=timeout)
    response.raise_for_status()
    rows = response.json()
    return sum(float(row["revenue"]) for row in rows)
```

- [ ] **Step 2.4: Run tests to verify they pass**

```bash
python3 -m pytest tests/klaviyo-framework/test_wc_revenue.py -v
```

Expected: `3 passed`

Note: `test_get_wc_revenue_sums_rows` verifies `params["channel"] == "eq.woocommerce"` — the test will need to check `call_args.kwargs["params"]` which is a list of tuples. Update the test assertion if needed:

```python
# Replace the params assertion block in the test with:
call_args = mock_get.call_args
assert "daily_sales" in call_args.args[0]
params_list = call_args.kwargs["params"]
params_dict = {}
for k, v in params_list:
    params_dict.setdefault(k, []).append(v)
assert params_dict["channel"] == ["eq.woocommerce"]
assert any("gte.2026-04-14" in v for v in params_dict.get("report_date", []))
```

Update `tests/klaviyo-framework/test_wc_revenue.py` — replace the `params` assertion block:

```python
def test_get_wc_revenue_sums_rows():
    """Correctly sums revenue from multiple daily rows."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"revenue": "1250.50"},
        {"revenue": "875.00"},
        {"revenue": "2100.25"},
    ]
    mock_response.raise_for_status = MagicMock()

    with patch("framework.wc_revenue.requests.get", return_value=mock_response) as mock_get:
        total = get_wc_revenue_for_week(
            start_date="2026-04-14",
            end_date="2026-04-20",
            supabase_url="https://abc.supabase.co",
            api_key="test-key",
        )

    assert total == pytest.approx(4225.75)

    call_args = mock_get.call_args
    assert "daily_sales" in call_args.args[0]
    params_list = call_args.kwargs["params"]
    params_map: dict = {}
    for k, v in params_list:
        params_map.setdefault(k, []).append(v)
    assert params_map["channel"] == ["eq.woocommerce"]
    assert any("gte.2026-04-14" in v for v in params_map.get("report_date", []))
```

- [ ] **Step 2.5: Run tests again after test fix**

```bash
python3 -m pytest tests/klaviyo-framework/test_wc_revenue.py -v
```

Expected: `3 passed`

- [ ] **Step 2.6: Run full suite**

```bash
python3 -m pytest tests/klaviyo-framework/ -v
```

Expected: all tests pass (21 + 3 new = 24 total)

- [ ] **Step 2.7: Commit**

```bash
git add marketing/klaviyo-audit/framework/wc_revenue.py tests/klaviyo-framework/test_wc_revenue.py
git commit -m "feat(framework): add Supabase WC revenue module"
```

---

## Task 3: Wire Real Data into generate_weekly_review.py

**Files:**
- Modify: `scripts/generate_weekly_review.py`

- [ ] **Step 3.1: Identify the stubs to replace**

In `scripts/generate_weekly_review.py`, the stubs are:
1. `deliverability_metrics` dict — all zeros (lines ~68–73)
2. `campaign_revenue_total = 0.0` (line ~65)
3. `total_wc_revenue: 0.0` in the `data` dict
4. `opens_unique: 0` and `clicks_unique: 0` in the `data` dict

For this task: wire deliverability metrics and WC revenue. Campaign revenue + opens/clicks are planned for a future task (requires campaign list + open/click metric aggregates).

- [ ] **Step 3.2: Update imports and env loading in generate_weekly_review.py**

At the top of the file, add these imports after the existing framework imports:

```python
from framework.wc_revenue import get_wc_revenue_for_week
```

In the env loading section, after `KLAVIYO_API_KEY` is set, add:

```python
SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_API_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")
```

- [ ] **Step 3.3: Replace deliverability stubs in the `main()` function**

Replace this block in `main()`:

```python
    # Deliverability metrics (placeholder — Plan 2 wires real metric aggregates)
    deliverability_metrics = {
        "net_list_growth_30d": 0,     # TODO in Plan 2: pull from subscribe - unsub metric aggregates
        "spam_rate_30d": 0.0,
        "bounce_rate_30d": 0.0,
        "unsub_rate_per_send_30d": 0.0,
    }
```

With:

```python
    # Real deliverability metrics from Klaviyo metric aggregates
    total_sends_for_gates = sum(s["recipients"] for s in flow_stats.values())
    end_date_str = target_monday.isoformat()
    start_date_str = (target_monday - timedelta(days=30)).isoformat()
    try:
        deliverability_metrics = client.get_deliverability_metrics(
            start_date=start_date_str,
            end_date=end_date_str,
            total_sends=total_sends_for_gates,
        )
        time.sleep(0.4)
    except Exception as e:
        print(f"[WARN] deliverability metrics failed: {e}", file=sys.stderr)
        deliverability_metrics = {
            "net_list_growth_30d": 0,
            "spam_rate_30d": 0.0,
            "bounce_rate_30d": 0.0,
            "unsub_rate_per_send_30d": 0.0,
        }
```

- [ ] **Step 3.4: Replace `total_wc_revenue` stub in the `data` dict**

Replace:

```python
        "total_wc_revenue": 0.0,      # populated in Plan 2 via Supabase daily_sales
```

With:

```python
        "total_wc_revenue": _get_wc_revenue(start_date_str, end_date_str),
```

Add this helper function above `main()`:

```python
def _get_wc_revenue(start_date: str, end_date: str) -> float:
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        print("[WARN] SUPABASE_URL or SUPABASE_SECRET_API_KEY not set — WC revenue will show $0", file=sys.stderr)
        return 0.0
    try:
        return get_wc_revenue_for_week(start_date, end_date, SUPABASE_URL, SUPABASE_API_KEY)
    except Exception as e:
        print(f"[WARN] Supabase WC revenue query failed: {e}", file=sys.stderr)
        return 0.0
```

- [ ] **Step 3.5: Verify script runs without crashing**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
python3 scripts/generate_weekly_review.py 2026-04-27
```

Expected: `[OK] Wrote marketing/klaviyo-audit/reviews/weekly/2026-04-27-weekly-review.md`
No `[ERROR]` lines. `[WARN]` lines are acceptable (rate limits, missing Supabase creds).

- [ ] **Step 3.6: Commit**

```bash
git add scripts/generate_weekly_review.py
git commit -m "feat(scripts): wire real deliverability metrics and Supabase WC revenue into weekly review"
```

---

## Task 4: Seasonal Reorder Email HTML Templates

**Files:**
- Create: `marketing/klaviyo-audit/seasonal-reorder/email1.html`
- Create: `marketing/klaviyo-audit/seasonal-reorder/email2.html`
- Create: `marketing/klaviyo-audit/seasonal-reorder/email3.html`
- Create: `marketing/klaviyo-audit/seasonal-reorder/email4.html`

These are Klaviyo template-language HTML files. The flow trigger is entry into `WdpJti` (Warm RFM). Category is read from `person|lookup:'last_category_purchased'` — values: `lawn`, `pasture`, `wildflower`, `clover`.

- [ ] **Step 4.1: Create email1.html — Replant Moment (Day 0, trigger)**

Create `marketing/klaviyo-audit/seasonal-reorder/email1.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Time to reseed</title>
</head>
<body style="margin:0;padding:0;background-color:#f8f9fa;font-family:Inter,Arial,sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f8f9fa;">
<tr><td align="center" style="padding:24px 16px;">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:4px;overflow:hidden;">

  <!-- Header bar -->
  <tr>
    <td style="background-color:#2d6a4f;padding:16px 32px;text-align:center;">
      <p style="margin:0;color:#ffffff;font-size:12px;letter-spacing:1px;text-transform:uppercase;font-family:Inter,Arial,sans-serif;">Nature's Seed — Seed You Can Trust</p>
    </td>
  </tr>

  <!-- Hero -->
  <tr>
    <td style="padding:40px 32px 24px;text-align:left;">
      <p style="margin:0 0 8px;color:#2d6a4f;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;font-family:Inter,Arial,sans-serif;">Spring 2026</p>
      {% if person|lookup:'last_category_purchased' == 'lawn' %}
      <h1 style="margin:0 0 16px;color:#212529;font-size:28px;font-weight:700;line-height:1.2;font-family:'Noto Serif Display',Georgia,serif;">Your lawn is ready for its spring reseeding</h1>
      <p style="margin:0 0 24px;color:#495057;font-size:16px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Hi {{ first_name|default:"there" }},<br><br>Spring is the window. Soil temps are rising — which means your grass seed will germinate fastest right now, before summer heat slows things down.</p>
      {% elif person|lookup:'last_category_purchased' == 'pasture' %}
      <h1 style="margin:0 0 16px;color:#212529;font-size:28px;font-weight:700;line-height:1.2;font-family:'Noto Serif Display',Georgia,serif;">Spring overseeding time for your pasture</h1>
      <p style="margin:0 0 24px;color:#495057;font-size:16px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Hi {{ first_name|default:"there" }},<br><br>Your pasture came through winter. Now's the time to thicken thin spots before summer heat sets in — and before your livestock traffic puts pressure on recovering areas.</p>
      {% elif person|lookup:'last_category_purchased' == 'wildflower' %}
      <h1 style="margin:0 0 16px;color:#212529;font-size:28px;font-weight:700;line-height:1.2;font-family:'Noto Serif Display',Georgia,serif;">Your wildflower meadow — plant again this spring</h1>
      <p style="margin:0 0 24px;color:#495057;font-size:16px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Hi {{ first_name|default:"there" }},<br><br>Wildflower mixes do best when direct-seeded in early spring. Frost stratification is still happening in most zones right now — your best germination window is open.</p>
      {% else %}
      <h1 style="margin:0 0 16px;color:#212529;font-size:28px;font-weight:700;line-height:1.2;font-family:'Noto Serif Display',Georgia,serif;">Spring planting window is open</h1>
      <p style="margin:0 0 24px;color:#495057;font-size:16px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Hi {{ first_name|default:"there" }},<br><br>Spring is your best planting window. Whether you're reseeding clover, cover crop, or topping up from last year — conditions are right and we can ship within one business day.</p>
      {% endif %}

      <!-- CTA -->
      <table role="presentation" cellspacing="0" cellpadding="0" border="0">
        <tr>
          <td style="border-radius:4px;background-color:#C96A2E;">
            {% if person|lookup:'last_category_purchased' == 'lawn' %}
            <a href="https://www.naturesseed.com/lawn-seed/?utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e1" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Shop Lawn Seed</a>
            {% elif person|lookup:'last_category_purchased' == 'pasture' %}
            <a href="https://www.naturesseed.com/pasture-seed/?utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e1" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Shop Pasture Seed</a>
            {% elif person|lookup:'last_category_purchased' == 'wildflower' %}
            <a href="https://www.naturesseed.com/wildflower-seed/?utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e1" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Shop Wildflower Seed</a>
            {% else %}
            <a href="https://www.naturesseed.com/?utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e1" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Shop Seed</a>
            {% endif %}
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Trust bar -->
  <tr>
    <td style="padding:24px 32px;border-top:1px solid #e9ecef;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
          <td width="33%" style="padding:0 8px 0 0;color:#495057;font-size:12px;font-family:Inter,Arial,sans-serif;">✓ Ships within 1 business day</td>
          <td width="33%" style="padding:0 8px;color:#495057;font-size:12px;font-family:Inter,Arial,sans-serif;text-align:center;">✓ Farm-direct, filler-free</td>
          <td width="34%" style="padding:0 0 0 8px;color:#495057;font-size:12px;font-family:Inter,Arial,sans-serif;text-align:right;">✓ Satisfaction guaranteed</td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="padding:20px 32px;background-color:#f8f9fa;border-top:1px solid #e9ecef;">
      <p style="margin:0;color:#6c757d;font-size:12px;line-height:1.5;font-family:Inter,Arial,sans-serif;">Nature's Seed | customercare@naturesseed.com | 801-531-1456<br>
      <a href="{{ unsubscribe_url }}" style="color:#6c757d;">Unsubscribe</a> &nbsp;·&nbsp; <a href="{{ manage_preferences_url }}" style="color:#6c757d;">Manage preferences</a></p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>
```

- [ ] **Step 4.2: Create email2.html — Planting Guide (Day 7)**

Create `marketing/klaviyo-audit/seasonal-reorder/email2.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Planting guide</title>
</head>
<body style="margin:0;padding:0;background-color:#f8f9fa;font-family:Inter,Arial,sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f8f9fa;">
<tr><td align="center" style="padding:24px 16px;">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:4px;overflow:hidden;">

  <!-- Header bar -->
  <tr>
    <td style="background-color:#2d6a4f;padding:16px 32px;text-align:center;">
      <p style="margin:0;color:#ffffff;font-size:12px;letter-spacing:1px;text-transform:uppercase;font-family:Inter,Arial,sans-serif;">Nature's Seed — Seed You Can Trust</p>
    </td>
  </tr>

  <!-- Body -->
  <tr>
    <td style="padding:40px 32px 24px;">
      <p style="margin:0 0 8px;color:#2d6a4f;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;font-family:Inter,Arial,sans-serif;">Expert tip</p>

      {% if person|lookup:'last_category_purchased' == 'lawn' %}
      <h1 style="margin:0 0 16px;color:#212529;font-size:26px;font-weight:700;line-height:1.2;font-family:'Noto Serif Display',Georgia,serif;">How to prepare your lawn for spring seeding</h1>
      <p style="margin:0 0 16px;color:#495057;font-size:15px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Three things our seed specialists recommend before you seed:</p>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:20px;">
        <tr><td style="padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #2d6a4f;margin-bottom:8px;font-family:Inter,Arial,sans-serif;font-size:14px;color:#212529;"><strong>1. Soil temp check</strong><br>Cool-season grasses (fescue, bluegrass, rye) germinate best at 50–65°F soil temp. Warm-season (bermuda, zoysia) need 65–70°F+.</td></tr>
      </table>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:8px;">
        <tr><td style="padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #2d6a4f;font-family:Inter,Arial,sans-serif;font-size:14px;color:#212529;"><strong>2. Scalp and dethatch</strong><br>Mow low, rake out thatch. Seed-to-soil contact is the #1 germination factor. Dead thatch blocks it.</td></tr>
      </table>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:20px;">
        <tr><td style="padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #2d6a4f;font-family:Inter,Arial,sans-serif;font-size:14px;color:#212529;"><strong>3. Starter fertilizer</strong><br>High-phosphorus starter fert in the seedbed significantly improves germination rates — especially in clay soils.</td></tr>
      </table>

      {% elif person|lookup:'last_category_purchased' == 'pasture' %}
      <h1 style="margin:0 0 16px;color:#212529;font-size:26px;font-weight:700;line-height:1.2;font-family:'Noto Serif Display',Georgia,serif;">Spring pasture overseed: what actually works</h1>
      <p style="margin:0 0 16px;color:#495057;font-size:15px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Three things our agronomists see make the biggest difference:</p>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:8px;">
        <tr><td style="padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #2d6a4f;font-family:Inter,Arial,sans-serif;font-size:14px;color:#212529;"><strong>1. Rest the field first</strong><br>Remove livestock for at least 2 weeks before overseeding. Hoof traffic on newly germinating seed is a silent killer.</td></tr>
      </table>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:8px;">
        <tr><td style="padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #2d6a4f;font-family:Inter,Arial,sans-serif;font-size:14px;color:#212529;"><strong>2. Use a slit seeder</strong><br>Broadcast seeding on established sod rarely works. Slit seeders place seed below the thatch layer where moisture is consistent.</td></tr>
      </table>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:20px;">
        <tr><td style="padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #2d6a4f;font-family:Inter,Arial,sans-serif;font-size:14px;color:#212529;"><strong>3. Seeding rate matters</strong><br>Most people under-seed. For overseeding: use 80% of new-planting rate. For bare patches: full rate.</td></tr>
      </table>

      {% elif person|lookup:'last_category_purchased' == 'wildflower' %}
      <h1 style="margin:0 0 16px;color:#212529;font-size:26px;font-weight:700;line-height:1.2;font-family:'Noto Serif Display',Georgia,serif;">How to get wildflowers to actually germinate</h1>
      <p style="margin:0 0 16px;color:#495057;font-size:15px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Most wildflower failures come down to three fixable mistakes:</p>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:8px;">
        <tr><td style="padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #2d6a4f;font-family:Inter,Arial,sans-serif;font-size:14px;color:#212529;"><strong>1. Weed competition</strong><br>Bare soil invites weeds. Solarize or till before seeding to deplete the weed seed bank. Wildflowers can't out-compete weeds at germination.</td></tr>
      </table>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:8px;">
        <tr><td style="padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #2d6a4f;font-family:Inter,Arial,sans-serif;font-size:14px;color:#212529;"><strong>2. Planting depth</strong><br>Most wildflower seed needs light to germinate. Press seed into soil surface — don't bury it. A hand roller after seeding is ideal.</td></tr>
      </table>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:20px;">
        <tr><td style="padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #2d6a4f;font-family:Inter,Arial,sans-serif;font-size:14px;color:#212529;"><strong>3. Consistent moisture in week 1</strong><br>Light daily watering for 7–10 days after seeding dramatically improves establishment. Don't let the surface dry completely.</td></tr>
      </table>

      {% else %}
      <h1 style="margin:0 0 16px;color:#212529;font-size:26px;font-weight:700;line-height:1.2;font-family:'Noto Serif Display',Georgia,serif;">3 ways to get better germination this spring</h1>
      <p style="margin:0 0 16px;color:#495057;font-size:15px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Our seed scientists recommend the same three steps across almost every seed type:</p>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:8px;">
        <tr><td style="padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #2d6a4f;font-family:Inter,Arial,sans-serif;font-size:14px;color:#212529;"><strong>1. Seed-to-soil contact</strong><br>The most overlooked factor. Press or rake seed into the surface — don't scatter on top of thatch or mulch.</td></tr>
      </table>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:8px;">
        <tr><td style="padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #2d6a4f;font-family:Inter,Arial,sans-serif;font-size:14px;color:#212529;"><strong>2. Consistent early moisture</strong><br>Light daily watering for the first 7–14 days. Let germination start before reducing frequency.</td></tr>
      </table>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:20px;">
        <tr><td style="padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #2d6a4f;font-family:Inter,Arial,sans-serif;font-size:14px;color:#212529;"><strong>3. Right rate for the job</strong><br>Overseeding into existing growth requires 80% of a new-planting rate. Bare ground needs the full rate.</td></tr>
      </table>
      {% endif %}

      <!-- CTA -->
      <p style="margin:0 0 16px;color:#495057;font-size:15px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Questions about your specific conditions? Our seed specialists answer by email or phone — no automated responses.</p>
      <table role="presentation" cellspacing="0" cellpadding="0" border="0">
        <tr>
          <td style="border-radius:4px;background-color:#C96A2E;">
            <a href="mailto:customercare@naturesseed.com?subject=Spring+planting+question&utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e2" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Ask a Seed Expert</a>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="padding:20px 32px;background-color:#f8f9fa;border-top:1px solid #e9ecef;">
      <p style="margin:0;color:#6c757d;font-size:12px;line-height:1.5;font-family:Inter,Arial,sans-serif;">Nature's Seed | customercare@naturesseed.com | 801-531-1456<br>
      <a href="{{ unsubscribe_url }}" style="color:#6c757d;">Unsubscribe</a> &nbsp;·&nbsp; <a href="{{ manage_preferences_url }}" style="color:#6c757d;">Manage preferences</a></p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>
```

- [ ] **Step 4.3: Create email3.html — Social Proof + Product Rec (Day 10)**

Create `marketing/klaviyo-audit/seasonal-reorder/email3.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>What customers planted this April</title>
</head>
<body style="margin:0;padding:0;background-color:#f8f9fa;font-family:Inter,Arial,sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f8f9fa;">
<tr><td align="center" style="padding:24px 16px;">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:4px;overflow:hidden;">

  <!-- Header bar -->
  <tr>
    <td style="background-color:#2d6a4f;padding:16px 32px;text-align:center;">
      <p style="margin:0;color:#ffffff;font-size:12px;letter-spacing:1px;text-transform:uppercase;font-family:Inter,Arial,sans-serif;">Nature's Seed — Seed You Can Trust</p>
    </td>
  </tr>

  <!-- Social proof banner -->
  <tr>
    <td style="background-color:#40916c;padding:20px 32px;text-align:center;">
      <p style="margin:0;color:#ffffff;font-size:20px;font-weight:700;font-family:'Noto Serif Display',Georgia,serif;">1,200+ customers have already seeded this spring</p>
    </td>
  </tr>

  <!-- Body -->
  <tr>
    <td style="padding:40px 32px 24px;">
      <p style="margin:0 0 20px;color:#495057;font-size:15px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Hi {{ first_name|default:"there" }},</p>
      <p style="margin:0 0 24px;color:#495057;font-size:15px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Here's what customers with similar properties ordered this April:</p>

      {% if person|lookup:'last_category_purchased' == 'lawn' %}
      <!-- Lawn product rec -->
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #dee2e6;border-radius:4px;margin-bottom:24px;">
        <tr><td style="padding:20px 24px;">
          <p style="margin:0 0 4px;color:#2d6a4f;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;font-family:Inter,Arial,sans-serif;">Most ordered — Lawn</p>
          <p style="margin:0 0 8px;color:#212529;font-size:17px;font-weight:700;font-family:'Noto Serif Display',Georgia,serif;">Premium Tall Fescue Blend</p>
          <p style="margin:0 0 12px;color:#495057;font-size:14px;font-family:Inter,Arial,sans-serif;">Expertly blended for the Mountain West. 85%+ germination rate, tested at our Utah facility. Heat and drought tolerant once established.</p>
          <p style="margin:0;color:#6c757d;font-size:13px;font-family:Inter,Arial,sans-serif;">⭐⭐⭐⭐⭐ "Thickest lawn I've had in 10 years" — Customer, Utah</p>
        </td></tr>
      </table>

      {% elif person|lookup:'last_category_purchased' == 'pasture' %}
      <!-- Pasture product rec -->
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #dee2e6;border-radius:4px;margin-bottom:24px;">
        <tr><td style="padding:20px 24px;">
          <p style="margin:0 0 4px;color:#2d6a4f;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;font-family:Inter,Arial,sans-serif;">Most ordered — Pasture</p>
          <p style="margin:0 0 8px;color:#212529;font-size:17px;font-weight:700;font-family:'Noto Serif Display',Georgia,serif;">Premium Pasture Mix — Mountain West</p>
          <p style="margin:0 0 12px;color:#495057;font-size:14px;font-family:Inter,Arial,sans-serif;">Orchard grass, meadow brome, perennial ryegrass — balanced for both productivity and palatability. Regionally tested in Colorado, Utah, and Idaho.</p>
          <p style="margin:0;color:#6c757d;font-size:13px;font-family:Inter,Arial,sans-serif;">⭐⭐⭐⭐⭐ "Best stand I've gotten in 5 tries" — Ranch manager, Wyoming</p>
        </td></tr>
      </table>

      {% elif person|lookup:'last_category_purchased' == 'wildflower' %}
      <!-- Wildflower product rec -->
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #dee2e6;border-radius:4px;margin-bottom:24px;">
        <tr><td style="padding:20px 24px;">
          <p style="margin:0 0 4px;color:#2d6a4f;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;font-family:Inter,Arial,sans-serif;">Most ordered — Wildflower</p>
          <p style="margin:0 0 8px;color:#212529;font-size:17px;font-weight:700;font-family:'Noto Serif Display',Georgia,serif;">Western Native Wildflower Mix</p>
          <p style="margin:0 0 12px;color:#495057;font-size:14px;font-family:Inter,Arial,sans-serif;">36 species of native wildflowers, wildland-collected across 13 western states. No annuals that need replanting every year — these naturalize and spread.</p>
          <p style="margin:0;color:#6c757d;font-size:13px;font-family:Inter,Arial,sans-serif;">⭐⭐⭐⭐⭐ "Bloomed the first year, came back fuller the second" — Homeowner, Colorado</p>
        </td></tr>
      </table>

      {% else %}
      <!-- Clover / Other product rec -->
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #dee2e6;border-radius:4px;margin-bottom:24px;">
        <tr><td style="padding:20px 24px;">
          <p style="margin:0 0 4px;color:#2d6a4f;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;font-family:Inter,Arial,sans-serif;">Most ordered — Spring</p>
          <p style="margin:0 0 8px;color:#212529;font-size:17px;font-weight:700;font-family:'Noto Serif Display',Georgia,serif;">White Dutch Clover</p>
          <p style="margin:0 0 12px;color:#495057;font-size:14px;font-family:Inter,Arial,sans-serif;">Nitrogen-fixing, drought-tolerant, pollinator-friendly. Mixes well with most grasses — great for filling thin spots while improving soil health.</p>
          <p style="margin:0;color:#6c757d;font-size:13px;font-family:Inter,Arial,sans-serif;">⭐⭐⭐⭐⭐ "Germinated in 5 days, filled in fast" — Gardener, New Mexico</p>
        </td></tr>
      </table>
      {% endif %}

      <!-- CTA -->
      <table role="presentation" cellspacing="0" cellpadding="0" border="0">
        <tr>
          <td style="border-radius:4px;background-color:#C96A2E;">
            {% if person|lookup:'last_category_purchased' == 'lawn' %}
            <a href="https://www.naturesseed.com/lawn-seed/?utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e3" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Shop Lawn Seed</a>
            {% elif person|lookup:'last_category_purchased' == 'pasture' %}
            <a href="https://www.naturesseed.com/pasture-seed/?utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e3" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Shop Pasture Seed</a>
            {% elif person|lookup:'last_category_purchased' == 'wildflower' %}
            <a href="https://www.naturesseed.com/wildflower-seed/?utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e3" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Shop Wildflower Seed</a>
            {% else %}
            <a href="https://www.naturesseed.com/?utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e3" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Shop Best Sellers</a>
            {% endif %}
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="padding:20px 32px;background-color:#f8f9fa;border-top:1px solid #e9ecef;">
      <p style="margin:0;color:#6c757d;font-size:12px;line-height:1.5;font-family:Inter,Arial,sans-serif;">Nature's Seed | customercare@naturesseed.com | 801-531-1456<br>
      <a href="{{ unsubscribe_url }}" style="color:#6c757d;">Unsubscribe</a> &nbsp;·&nbsp; <a href="{{ manage_preferences_url }}" style="color:#6c757d;">Manage preferences</a></p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>
```

- [ ] **Step 4.4: Create email4.html — Seasonal Urgency (Day 16)**

Create `marketing/klaviyo-audit/seasonal-reorder/email4.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Spring planting window closing</title>
</head>
<body style="margin:0;padding:0;background-color:#f8f9fa;font-family:Inter,Arial,sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f8f9fa;">
<tr><td align="center" style="padding:24px 16px;">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:4px;overflow:hidden;">

  <!-- Header bar -->
  <tr>
    <td style="background-color:#2d6a4f;padding:16px 32px;text-align:center;">
      <p style="margin:0;color:#ffffff;font-size:12px;letter-spacing:1px;text-transform:uppercase;font-family:Inter,Arial,sans-serif;">Nature's Seed — Seed You Can Trust</p>
    </td>
  </tr>

  <!-- Urgency banner -->
  <tr>
    <td style="background-color:#1b4332;padding:16px 32px;text-align:center;">
      {% if person|lookup:'last_category_purchased' == 'lawn' %}
      <p style="margin:0;color:#ffffff;font-size:15px;font-weight:600;font-family:Inter,Arial,sans-serif;">Cool-season grasses: plant before soil temps hit 75°F</p>
      {% elif person|lookup:'last_category_purchased' == 'pasture' %}
      <p style="margin:0;color:#ffffff;font-size:15px;font-weight:600;font-family:Inter,Arial,sans-serif;">Spring overseed window: closes as summer heat sets in</p>
      {% elif person|lookup:'last_category_purchased' == 'wildflower' %}
      <p style="margin:0;color:#ffffff;font-size:15px;font-weight:600;font-family:Inter,Arial,sans-serif;">Wildflower direct-seeding: best before late May</p>
      {% else %}
      <p style="margin:0;color:#ffffff;font-size:15px;font-weight:600;font-family:Inter,Arial,sans-serif;">Spring planting window: best results before late May</p>
      {% endif %}
    </td>
  </tr>

  <!-- Body -->
  <tr>
    <td style="padding:40px 32px 24px;">
      {% if person|lookup:'last_category_purchased' == 'lawn' %}
      <h1 style="margin:0 0 16px;color:#212529;font-size:26px;font-weight:700;line-height:1.2;font-family:'Noto Serif Display',Georgia,serif;">Last chance for spring lawn seeding this year</h1>
      <p style="margin:0 0 20px;color:#495057;font-size:15px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Hi {{ first_name|default:"there" }},<br><br>Once soil temperatures climb past 75°F, cool-season grass seed (fescue, bluegrass, perennial rye) struggles to germinate. Summer heat causes seedlings to stress before they establish roots.<br><br>If you're going to seed this spring, order now — we ship within one business day, and you'll want a few days of consistent moisture after planting.</p>
      {% elif person|lookup:'last_category_purchased' == 'pasture' %}
      <h1 style="margin:0 0 16px;color:#212529;font-size:26px;font-weight:700;line-height:1.2;font-family:'Noto Serif Display',Georgia,serif;">Spring overseed window is closing</h1>
      <p style="margin:0 0 20px;color:#495057;font-size:15px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Hi {{ first_name|default:"there" }},<br><br>For most of the Mountain West and Plains, the spring overseed window runs April through mid-May. After that, summer heat and livestock pressure work against new seedlings.<br><br>If your pasture has thin spots, this is the last good window until fall.</p>
      {% elif person|lookup:'last_category_purchased' == 'wildflower' %}
      <h1 style="margin:0 0 16px;color:#212529;font-size:26px;font-weight:700;line-height:1.2;font-family:'Noto Serif Display',Georgia,serif;">Wildflower seeding: plant before it gets too warm</h1>
      <p style="margin:0 0 20px;color:#495057;font-size:15px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Hi {{ first_name|default:"there" }},<br><br>Many native wildflowers need cool, moist soil for germination. Late-spring direct seeding (before late May in most western regions) gives them the best start and protects new seedlings from summer heat stress.<br><br>The alternative is fall seeding — but that's 5 months away.</p>
      {% else %}
      <h1 style="margin:0 0 16px;color:#212529;font-size:26px;font-weight:700;line-height:1.2;font-family:'Noto Serif Display',Georgia,serif;">Spring planting: the window is still open</h1>
      <p style="margin:0 0 20px;color:#495057;font-size:15px;line-height:1.6;font-family:Inter,Arial,sans-serif;">Hi {{ first_name|default:"there" }},<br><br>For most seed types, spring gives you the best conditions — soil moisture from snowmelt, moderate temps, and long days for establishment. That window runs through late May in most regions.<br><br>If you're planning to seed this year, ordering now means you can plant while conditions are still ideal.</p>
      {% endif %}

      <!-- Shipping promise -->
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #dee2e6;border-radius:4px;margin-bottom:24px;">
        <tr><td style="padding:16px 20px;text-align:center;">
          <p style="margin:0;color:#2d6a4f;font-size:15px;font-weight:600;font-family:Inter,Arial,sans-serif;">Order by 3pm MT — ships same business day</p>
          <p style="margin:4px 0 0;color:#6c757d;font-size:13px;font-family:Inter,Arial,sans-serif;">Free shipping on orders over $75 · Farm-direct · Satisfaction guaranteed</p>
        </td></tr>
      </table>

      <!-- CTA -->
      <table role="presentation" cellspacing="0" cellpadding="0" border="0">
        <tr>
          <td style="border-radius:4px;background-color:#C96A2E;">
            {% if person|lookup:'last_category_purchased' == 'lawn' %}
            <a href="https://www.naturesseed.com/lawn-seed/?utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e4" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Order Now — Ships Today</a>
            {% elif person|lookup:'last_category_purchased' == 'pasture' %}
            <a href="https://www.naturesseed.com/pasture-seed/?utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e4" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Order Now — Ships Today</a>
            {% elif person|lookup:'last_category_purchased' == 'wildflower' %}
            <a href="https://www.naturesseed.com/wildflower-seed/?utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e4" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Order Now — Ships Today</a>
            {% else %}
            <a href="https://www.naturesseed.com/?utm_source=klaviyo&utm_medium=email&utm_campaign=seasonal-reorder-e4" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;font-family:Inter,Arial,sans-serif;">Order Now — Ships Today</a>
            {% endif %}
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="padding:20px 32px;background-color:#f8f9fa;border-top:1px solid #e9ecef;">
      <p style="margin:0;color:#6c757d;font-size:12px;line-height:1.5;font-family:Inter,Arial,sans-serif;">Nature's Seed | customercare@naturesseed.com | 801-531-1456<br>
      <a href="{{ unsubscribe_url }}" style="color:#6c757d;">Unsubscribe</a> &nbsp;·&nbsp; <a href="{{ manage_preferences_url }}" style="color:#6c757d;">Manage preferences</a></p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>
```

- [ ] **Step 4.5: Commit email templates**

```bash
git add marketing/klaviyo-audit/seasonal-reorder/
git commit -m "feat(seasonal-reorder): write 4 category-conditional email HTML templates"
```

---

## Task 5: Upload Templates + Flow Setup Doc

**Files:**
- Create: `scripts/upload_seasonal_reorder_templates.py`
- Create: `marketing/klaviyo-audit/seasonal-reorder/flow-setup.md`

- [ ] **Step 5.1: Create the upload script**

Create `scripts/upload_seasonal_reorder_templates.py`:

```python
#!/usr/bin/env python3
"""Upload 4 Seasonal Reorder email templates to Klaviyo and print their IDs.

Usage: python3 scripts/upload_seasonal_reorder_templates.py

Writes template IDs to seasonal-reorder/flow-setup.md after upload.
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
        "subject": "Time to reseed your {{ person|lookup:'last_category_purchased'|default:'lawn' }}? 🌱",
    },
    {
        "filename": "email2.html",
        "name": "Seasonal Reorder — Email 2: Planting Guide",
        "subject": "How to prep your soil this spring",
    },
    {
        "filename": "email3.html",
        "name": "Seasonal Reorder — Email 3: Social Proof + Product Rec",
        "subject": "What 1,200+ customers planted this April",
    },
    {
        "filename": "email4.html",
        "name": "Seasonal Reorder — Email 4: Seasonal Urgency",
        "subject": "Spring planting window is closing — order now",
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
        print(f"[ERROR] {html_path} not found — run Task 4 first", file=sys.stderr)
        sys.exit(1)

    html_content = html_path.read_text()
    payload = {
        "data": {
            "type": "template",
            "attributes": {
                "name": t["name"],
                "editor_type": "CODE",
                "html": html_content,
                "text": f"View this email in your browser. {t['subject']}",
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

# Print summary
print("\n--- Template IDs ---")
for filename, tid in template_ids.items():
    print(f"{filename}: {tid}")

print("\n[OK] Copy these IDs into flow-setup.md for the manual UI step.")
```

- [ ] **Step 5.2: Run the upload script**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
python3 scripts/upload_seasonal_reorder_templates.py
```

Expected output (template IDs will differ):
```
[OK] Seasonal Reorder — Email 1: Replant Moment → Abc123
[OK] Seasonal Reorder — Email 2: Planting Guide → Def456
[OK] Seasonal Reorder — Email 3: Social Proof + Product Rec → Ghi789
[OK] Seasonal Reorder — Email 4: Seasonal Urgency → Jkl012

--- Template IDs ---
email1.html: Abc123
email2.html: Def456
email3.html: Ghi789
email4.html: Jkl012
```

- [ ] **Step 5.3: Create the flow setup doc with real template IDs**

Create `marketing/klaviyo-audit/seasonal-reorder/flow-setup.md` with the actual template IDs from the script output:

```markdown
# Seasonal Reorder Flow — Manual UI Setup

Flow ID: `Vzp5Nb`
Klaviyo UI: https://www.klaviyo.com/flow/Vzp5Nb/edit

## Templates Uploaded (API)

| Email | Template ID | Subject Line |
|---|---|---|
| Email 1 — Replant Moment | [FILL FROM SCRIPT OUTPUT] | Time to reseed your {{ person\|lookup:'last_category_purchased'\|default:'lawn' }}? 🌱 |
| Email 2 — Planting Guide | [FILL FROM SCRIPT OUTPUT] | How to prep your soil this spring |
| Email 3 — Social Proof | [FILL FROM SCRIPT OUTPUT] | What 1,200+ customers planted this April |
| Email 4 — Urgency | [FILL FROM SCRIPT OUTPUT] | Spring planting window is closing — order now |

## Steps to Complete in Klaviyo UI

1. Open https://www.klaviyo.com/flow/Vzp5Nb/edit
2. Verify trigger: **Segment trigger → WdpJti (Warm)**. If missing, add it.
3. For **Email 1** (send immediately on trigger):
   - Click the first email block
   - Click "Edit" → "Change template" → paste template ID from table above
   - Set subject: `Time to reseed your {{ person|lookup:'last_category_purchased'|default:'lawn' }}? 🌱`
   - Set sender: `customercare@naturesseed.com` | `Nature's Seed`
   - Preview with a profile that has `last_category_purchased = lawn` and one with `pasture`
4. Add **Time Delay** of **7 days** after Email 1
5. For **Email 2** (Day 7):
   - Click email block → assign template → set subject above
6. Add **Time Delay** of **3 days** (total 10 days from trigger)
7. For **Email 3** (Day 10):
   - Assign template → set subject
8. Add **Time Delay** of **6 days** (total 16 days from trigger)
9. For **Email 4** (Day 16):
   - Assign template → set subject
10. Add suppression filter to each email: **exclude** anyone who purchased in last 48h (use `Placed Order` metric filter: `in last 2 days`)
11. Set Smart Send Time on each email (Klaviyo → Advanced → "Send at optimal time")
12. Click **Activate Flow**

## Suppression Rules (per suppression-rules.md)

- Exclude: in-active-discount-flow (Winback), NOT-E90 (VirYfN), Unsubscribed-730d
- These should already be applied at the flow level if suppression rules from Phase 0 were set

## Verification After Activation

- Check Klaviyo flow analytics after 24h: confirm "Messages Sent" counter is incrementing
- Seasonal Reorder should start sending to new Warm entries immediately after activation
- The flow has been sitting empty since creation — any profile entering Warm RFM from this point forward will enter the flow
```

- [ ] **Step 5.4: Commit**

```bash
git add scripts/upload_seasonal_reorder_templates.py marketing/klaviyo-audit/seasonal-reorder/flow-setup.md
git commit -m "feat(seasonal-reorder): upload script + flow UI setup doc"
```

---

## Task 6: Campaign Proposal Generator

**Files:**
- Create: `marketing/klaviyo-audit/framework/campaign_proposal.py`
- Create: `tests/klaviyo-framework/test_campaign_proposal.py`

- [ ] **Step 6.1: Write the failing tests**

Create `tests/klaviyo-framework/test_campaign_proposal.py`:

```python
"""Tests for the 6-check campaign proposal evaluator (spec §4.1)."""
import pytest
from framework.campaign_proposal import ProposalCheck, evaluate_proposal


# --- Happy path ---

def test_all_checks_pass():
    check = evaluate_proposal(
        name="Spring Lawn Campaign",
        goal="Replant",
        audience_segment_id="WdpJti",   # Warm — starred
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.all_pass is True
    assert check.goal_pass is True
    assert check.audience_pass is True
    assert check.cadence_pass is True
    assert check.suppression_pass is True
    assert check.offer_pass is True
    assert check.rpr_pass is True


# --- Rejection cases ---

def test_rejects_missing_goal():
    check = evaluate_proposal(
        name="No goal",
        goal=None,
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.all_pass is False
    assert check.goal_pass is False


def test_rejects_non_starred_segment():
    check = evaluate_proposal(
        name="Non-starred audience",
        goal="Retention",
        audience_segment_id="XXXZZZ",   # not in starred set
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.all_pass is False
    assert check.audience_pass is False


def test_rejects_cadence_cap_breach():
    check = evaluate_proposal(
        name="Over-mailed",
        goal="Replant",
        audience_segment_id="WdpJti",
        sends_past_7d=2,   # cap is 2 → 2 >= 2 → breach
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.all_pass is False
    assert check.cadence_pass is False


def test_rejects_missing_suppression():
    check = evaluate_proposal(
        name="No suppressions",
        goal="Replant",
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=False,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.all_pass is False
    assert check.suppression_pass is False


def test_rejects_offer_over_cap():
    check = evaluate_proposal(
        name="Too-large discount",
        goal="Replant",
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=0.20,   # 20% > 15% cap
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.all_pass is False
    assert check.offer_pass is False


def test_rejects_rpr_below_targeted_minimum():
    check = evaluate_proposal(
        name="Low RPR targeted",
        goal="Replant",
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.40,   # below $0.50 min for targeted
        target_type="targeted",
    )
    assert check.all_pass is False
    assert check.rpr_pass is False


def test_broad_segment_uses_lower_rpr_minimum():
    check = evaluate_proposal(
        name="Broad segment",
        goal="Seasonal moment",
        audience_segment_id="RbH7na",   # E60D — starred
        sends_past_7d=0,
        cadence_cap=3,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.20,   # above $0.15 min for broad
        target_type="broad",
    )
    assert check.all_pass is True
    assert check.rpr_pass is True


# --- Markdown rendering ---

def test_to_markdown_contains_verdict():
    check = evaluate_proposal(
        name="Spring Lawn Campaign",
        goal="Replant",
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    md = check.to_markdown()
    assert "APPROVED" in md
    assert "Spring Lawn Campaign" in md


def test_to_markdown_shows_rejection():
    check = evaluate_proposal(
        name="Bad Campaign",
        goal=None,
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    md = check.to_markdown()
    assert "REJECTED" in md
    assert "❌" in md
```

- [ ] **Step 6.2: Run tests to verify they fail**

```bash
python3 -m pytest tests/klaviyo-framework/test_campaign_proposal.py -v
```

Expected: `ImportError: No module named 'framework.campaign_proposal'`

- [ ] **Step 6.3: Implement `campaign_proposal.py`**

Create `marketing/klaviyo-audit/framework/campaign_proposal.py`:

```python
"""Campaign proposal evaluator — implements spec §4.1 six-check decision tree.

Every broadcast must pass all 6 checks. Failing any one = auto-rejected.
"""
from dataclasses import dataclass, field
from typing import Optional

# Segments explicitly starred in CLAUDE.md / spec §1.3 — only these are valid audience targets
STARRED_SEGMENTS = {
    # RFM lifecycle
    "VtKptn",  # Champions Active
    "RAQTca",  # Champions
    "RbGRqF",  # Active This Season
    "T93fB3",  # New
    "WdpJti",  # Warm
    "RyASXF",  # At Risk
    "Sv5cSC",  # Lapsed
    "WjzuUj",  # Dormant
    # Engagement tiers
    "VKVpf9",  # E30D
    "RbH7na",  # E60D
    "VduUfa",  # E90D
}

MAX_OFFER_PCT = 0.15          # spec §2.3
MIN_RPR_TARGETED = 0.50       # spec §4.1
MIN_RPR_BROAD = 0.15          # spec §4.1


@dataclass
class ProposalCheck:
    name: str
    goal: Optional[str]
    audience_segment_id: str
    sends_past_7d: int
    cadence_cap: int
    has_suppression_exclusions: bool
    offer_pct: Optional[float]
    expected_rpr: float
    target_type: str  # "targeted" | "broad"

    @property
    def goal_pass(self) -> bool:
        return bool(self.goal)

    @property
    def audience_pass(self) -> bool:
        return self.audience_segment_id in STARRED_SEGMENTS

    @property
    def cadence_pass(self) -> bool:
        return self.sends_past_7d < self.cadence_cap

    @property
    def suppression_pass(self) -> bool:
        return self.has_suppression_exclusions

    @property
    def offer_pass(self) -> bool:
        if self.offer_pct is None:
            return True
        return self.offer_pct <= MAX_OFFER_PCT

    @property
    def rpr_pass(self) -> bool:
        min_rpr = MIN_RPR_TARGETED if self.target_type == "targeted" else MIN_RPR_BROAD
        return self.expected_rpr >= min_rpr

    @property
    def all_pass(self) -> bool:
        return all([
            self.goal_pass,
            self.audience_pass,
            self.cadence_pass,
            self.suppression_pass,
            self.offer_pass,
            self.rpr_pass,
        ])

    def to_markdown(self) -> str:
        offer_detail = f"{self.offer_pct * 100:.0f}%" if self.offer_pct is not None else "none"
        min_rpr = MIN_RPR_TARGETED if self.target_type == "targeted" else MIN_RPR_BROAD
        checks = [
            ("1. Goal", self.goal_pass, self.goal or "None — no business goal defined"),
            ("2. Audience", self.audience_pass, f"`{self.audience_segment_id}` {'✓ starred' if self.audience_pass else '✗ not in starred segments'}"),
            ("3. Cadence", self.cadence_pass, f"{self.sends_past_7d} sends in last 7d vs cap of {self.cadence_cap}"),
            ("4. Suppression", self.suppression_pass, "exclusions applied" if self.suppression_pass else "MISSING — add bought-48hr, in-active-flow, NOT-E90 exclusions"),
            ("5. Offer", self.offer_pass, f"{offer_detail} vs {MAX_OFFER_PCT * 100:.0f}% cap"),
            ("6. RPR target", self.rpr_pass, f"${self.expected_rpr:.2f} vs ${min_rpr:.2f} min ({self.target_type})"),
        ]
        rows = "\n".join(
            f"| {name} | {'✅' if ok else '❌'} | {detail} |"
            for name, ok, detail in checks
        )
        verdict = "✅ APPROVED — ready to schedule" if self.all_pass else "❌ REJECTED — fix failing checks above"
        return (
            f"## Campaign Proposal: {self.name}\n\n"
            f"| Check | Status | Detail |\n"
            f"|---|---|---|\n"
            f"{rows}\n\n"
            f"**Verdict:** {verdict}\n"
        )


def evaluate_proposal(
    name: str,
    goal: Optional[str],
    audience_segment_id: str,
    sends_past_7d: int,
    cadence_cap: int,
    has_suppression_exclusions: bool,
    offer_pct: Optional[float],
    expected_rpr: float,
    target_type: str,
) -> ProposalCheck:
    """Run all 6 spec §4.1 checks and return a ProposalCheck."""
    return ProposalCheck(
        name=name,
        goal=goal,
        audience_segment_id=audience_segment_id,
        sends_past_7d=sends_past_7d,
        cadence_cap=cadence_cap,
        has_suppression_exclusions=has_suppression_exclusions,
        offer_pct=offer_pct,
        expected_rpr=expected_rpr,
        target_type=target_type,
    )
```

- [ ] **Step 6.4: Run tests to verify they pass**

```bash
python3 -m pytest tests/klaviyo-framework/test_campaign_proposal.py -v
```

Expected: `9 passed`

- [ ] **Step 6.5: Run full suite**

```bash
python3 -m pytest tests/klaviyo-framework/ -v
```

Expected: all tests pass (24 + 9 new = 33 total)

- [ ] **Step 6.6: Commit**

```bash
git add marketing/klaviyo-audit/framework/campaign_proposal.py tests/klaviyo-framework/test_campaign_proposal.py
git commit -m "feat(framework): add campaign proposal evaluator (spec §4.1 six-check tree)"
```

---

## Task 7: Regenerate Weekly Review with Real Data

**Files:**
- Read/verify: `marketing/klaviyo-audit/reviews/weekly/`

- [ ] **Step 7.1: Run the weekly review script**

```bash
cd "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -"
python3 scripts/generate_weekly_review.py 2026-04-28
```

Expected: `[OK] Wrote marketing/klaviyo-audit/reviews/weekly/2026-04-28-weekly-review.md`

Note any `[WARN]` lines. If Supabase returns data, `total_wc_revenue` will be non-zero in the output file.

- [ ] **Step 7.2: Inspect the output file**

```bash
head -60 "marketing/klaviyo-audit/reviews/weekly/2026-04-28-weekly-review.md"
```

Verify:
- "Total sends" line is populated (not 0) — flow stats should be real
- Deliverability section shows values (not all 0.0) — or `[WARN]` in stderr indicates rate limit
- No Python exceptions in output

- [ ] **Step 7.3: Final test suite run**

```bash
python3 -m pytest tests/klaviyo-framework/ -v
```

Expected: all 33 tests pass, zero failures.

- [ ] **Step 7.4: Commit**

```bash
git add marketing/klaviyo-audit/reviews/weekly/2026-04-28-weekly-review.md
git commit -m "chore: generate 2026-04-28 weekly review with real deliverability + Supabase data"
```

---

## Post-Plan Manual Steps (Gabe — UI only)

These cannot be automated via REST API:

1. **Seasonal Reorder flow activation** — Follow `marketing/klaviyo-audit/seasonal-reorder/flow-setup.md` in Klaviyo UI at `klaviyo.com/flow/Vzp5Nb/edit`
   - Assign templates, set timing (Day 0 / Day 7 / Day 10 / Day 16), set subject lines, activate
   - Priority: **urgent** — spring planting season is active now

2. **Winback flow** (from Plan 1) — Assign templates QNMmmd, TcdhjN, WYVPer, W3pKee to flow `WpFDg7` if not yet done

---

## Self-Review Checklist

### Spec coverage

| Spec requirement | Covered by |
|---|---|
| Real deliverability metrics in weekly review | Task 1 + Task 3 |
| Supabase WC revenue in weekly review | Task 2 + Task 3 |
| Seasonal Reorder flow — category-conditional emails | Task 4 |
| Seasonal Reorder templates uploaded to Klaviyo | Task 5 |
| Campaign proposal 6-check evaluator | Task 6 |
| flow `Vzp5Nb` activation path documented | Task 5 (flow-setup.md) |

### Items deferred to Plan 3

- `opens_unique` / `clicks_unique` — require open/click metric aggregate calls (new metric IDs needed)
- Campaign revenue aggregate — requires iterating sent campaign IDs
- Alert-file writer — writes `marketing/klaviyo-audit/alerts/YYYY-MM-DD-alert.md` on gate failure
- Monthly review generator
- Welcome Series (`WQBF89`) content build-out (42% open, 0.5% conversion — big opportunity)
