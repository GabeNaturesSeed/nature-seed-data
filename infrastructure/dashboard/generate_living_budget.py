#!/usr/bin/env python3
"""
Nature's Seed — Living Budget Data Generator
Pulls May–Dec 2026 ad spend and revenue actuals from Supabase,
computes per-month EBITDA, and writes docs/data/living-budget.json.
"""

import json
from datetime import date, datetime
from pathlib import Path
from collections import defaultdict

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "docs" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

env_path = ROOT / ".env"
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")

TODAY = date.today()


def _sb_get(path, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    p = dict(params or {})
    if "limit" not in p:
        p["limit"] = 10000
    resp = requests.get(url, headers=headers, params=p, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── Budget plan (hardcoded) ───────────────────────────────────────────────────
PLAN = {
    "2026-05": {"budget_ad": 25000, "budget_rev": 162872, "budget_ebitda": -18314, "gm_pct": 48.5, "non_ad_opex": 77684},
    "2026-06": {"budget_ad": 8000,  "budget_rev": 104608, "budget_ebitda": -17320, "gm_pct": 50.7, "non_ad_opex": 67733},
    "2026-07": {"budget_ad": 5000,  "budget_rev": 36676,  "budget_ebitda": -57522, "gm_pct": 50.8, "non_ad_opex": 76530},
    "2026-08": {"budget_ad": 15000, "budget_rev": 112188, "budget_ebitda": -32291, "gm_pct": 40.2, "non_ad_opex": 67768},
    "2026-09": {"budget_ad": 42000, "budget_rev": 252727, "budget_ebitda": 13840,  "gm_pct": 49.3, "non_ad_opex": 74131},
    "2026-10": {"budget_ad": 38000, "budget_rev": 198442, "budget_ebitda": -23524, "gm_pct": 40.2, "non_ad_opex": 70675},
    "2026-11": {"budget_ad": 3952,  "budget_rev": 51110,  "budget_ebitda": -39357, "gm_pct": 45.2, "non_ad_opex": 63884},
    "2026-12": {"budget_ad": 0,     "budget_rev": 17948,  "budget_ebitda": -65239, "gm_pct": 31.6, "non_ad_opex": 76288},
}

DEPRECIATION = 5377

MONTHS_ORDER = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"]


def fetch_actuals():
    """Fetch ad spend and revenue from Supabase for May–Dec 2026."""
    ad_by_month = defaultdict(lambda: {"spend": 0.0, "conversions_value": 0.0, "days": 0})
    rev_by_month = defaultdict(float)
    last_date = None

    try:
        rows = _sb_get("daily_ad_spend", {
            "select": "report_date,spend,conversions_value",
            "report_date": "gte.2026-05-01",
            "order": "report_date.asc",
        })
        for r in rows:
            mo = r["report_date"][:7]
            if mo in PLAN:
                ad_by_month[mo]["spend"] += float(r.get("spend") or 0)
                ad_by_month[mo]["conversions_value"] += float(r.get("conversions_value") or 0)
                ad_by_month[mo]["days"] += 1
                if last_date is None or r["report_date"] > last_date:
                    last_date = r["report_date"]
    except Exception as e:
        print(f"  [WARN] daily_ad_spend fetch failed: {e}")

    try:
        rows = _sb_get("daily_sales", {
            "select": "report_date,revenue",
            "report_date": "gte.2026-05-01",
            "channel": "eq.woocommerce",
            "order": "report_date.asc",
        })
        for r in rows:
            mo = r["report_date"][:7]
            if mo in PLAN:
                rev_by_month[mo] += float(r.get("revenue") or 0)
    except Exception as e:
        print(f"  [WARN] daily_sales fetch failed: {e}")

    return ad_by_month, rev_by_month, last_date


def compute_months(ad_by_month, rev_by_month):
    today_mo = TODAY.strftime("%Y-%m")
    results = []

    for mo in MONTHS_ORDER:
        p = PLAN[mo]
        ad_actual = ad_by_month[mo]["spend"]
        conv_value = ad_by_month[mo]["conversions_value"]
        days_data = ad_by_month[mo]["days"]
        rev_actual = rev_by_month[mo]

        if mo < today_mo:
            status = "complete"
        elif mo == today_mo:
            status = "mtd"
        else:
            status = "future"

        # EBITDA: Gross Margin − Non-Ad OPEX − Ad Spend + Depreciation
        if status != "future" and rev_actual > 0:
            gm = rev_actual * p["gm_pct"] / 100
            ebitda_actual = gm - p["non_ad_opex"] - ad_actual + DEPRECIATION
        else:
            ebitda_actual = None

        # ROAS: conversions value / ad spend
        roas_actual = (conv_value / ad_actual) if (ad_actual > 0 and status != "future") else None

        # MER: WC revenue / ad spend
        mer_actual = (rev_actual / ad_actual) if (ad_actual > 0 and status != "future") else None

        results.append({
            "month": mo,
            "status": status,
            "days_with_data": days_data,
            "budget_ad": p["budget_ad"],
            "budget_rev": p["budget_rev"],
            "budget_ebitda": p["budget_ebitda"],
            "ad_actual": round(ad_actual, 2) if status != "future" else None,
            "rev_actual": round(rev_actual, 2) if status != "future" else None,
            "ebitda_actual": round(ebitda_actual, 2) if ebitda_actual is not None else None,
            "roas_actual": round(roas_actual, 3) if roas_actual is not None else None,
            "mer_actual": round(mer_actual, 3) if mer_actual is not None else None,
        })

    return results


def main():
    print("Generating living-budget.json...")
    ad_by_month, rev_by_month, last_date = fetch_actuals()
    months = compute_months(ad_by_month, rev_by_month)

    # Current month MTD efficiency (for guardrail cards)
    today_mo = TODAY.strftime("%Y-%m")
    current = next((m for m in months if m["month"] == today_mo), None)

    out = {
        "generated_at": str(TODAY),
        "as_of": last_date or str(TODAY),
        "annual_budget": 391315,
        "spent_jan_apr": 254363,
        "remaining": 136952,
        "annual_ebitda_target": 8579,
        "q1_apr_ebitda": 248307,
        "months": months,
        "current_month": today_mo,
        "current_roas": current["roas_actual"] if current else None,
        "current_mer": current["mer_actual"] if current else None,
    }

    out_path = OUT_DIR / "living-budget.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"  Written: {out_path}")
    print(f"  Months with data: {sum(1 for m in months if m['status'] != 'future')}")


if __name__ == "__main__":
    main()
