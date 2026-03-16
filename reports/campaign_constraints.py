#!/usr/bin/env python3
"""
Campaign Constraint Analysis — Nature's Seed
=============================================
Pulls impression share + lost IS metrics per campaign to understand
what's ACTUALLY constraining each campaign (budget vs rank vs demand).

Usage:
    python3 reports/campaign_constraints.py
"""

import json
import logging
from datetime import date
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("constraints")

ROOT = Path(__file__).resolve().parents[1]

POST_START = date(2026, 2, 28)
POST_END   = date(2026, 3, 12)


def _load_env() -> dict:
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip().strip("'\"")
    return env

ENV = _load_env()


def run():
    customer_id = ENV["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
    login_id    = ENV.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")

    config = {
        "developer_token": ENV["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": ENV["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": ENV["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": ENV["GOOGLE_ADS_REFRESH_TOKEN"],
        "use_proto_plus": True,
    }
    if login_id:
        config["login_customer_id"] = login_id

    client = GoogleAdsClient.load_from_dict(config)
    service = client.get_service("GoogleAdsService")

    # Pull campaign-level metrics with impression share data
    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.advertising_channel_type,
            campaign.bidding_strategy_type,
            campaign.campaign_budget,
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value,
            metrics.search_impression_share,
            metrics.search_budget_lost_impression_share,
            metrics.search_rank_lost_impression_share,
            metrics.content_impression_share,
            metrics.content_budget_lost_impression_share,
            metrics.content_rank_lost_impression_share
        FROM campaign
        WHERE segments.date >= '{POST_START}'
          AND segments.date <= '{POST_END}'
          AND campaign.status = 'ENABLED'
          AND metrics.impressions > 0
    """
    response = service.search(customer_id=customer_id, query=query)

    campaigns = {}
    for row in response:
        cid = str(row.campaign.id)
        if cid not in campaigns:
            campaigns[cid] = {
                "id": cid,
                "name": row.campaign.name,
                "type": str(row.campaign.advertising_channel_type).replace("AdvertisingChannelType.", ""),
                "bidding": str(row.campaign.bidding_strategy_type).replace("BiddingStrategyType.", ""),
                "budget_resource": row.campaign.campaign_budget,
                "spend": 0, "impressions": 0, "clicks": 0,
                "conversions": 0, "conv_value": 0,
                # Impression share accumulators (will average later)
                "_search_is_sum": 0, "_search_budget_lost_sum": 0, "_search_rank_lost_sum": 0,
                "_content_is_sum": 0, "_content_budget_lost_sum": 0, "_content_rank_lost_sum": 0,
                "_row_count": 0,
            }
        c = campaigns[cid]
        c["spend"]       += row.metrics.cost_micros / 1_000_000
        c["impressions"] += row.metrics.impressions
        c["clicks"]      += row.metrics.clicks
        c["conversions"] += row.metrics.conversions
        c["conv_value"]  += row.metrics.conversions_value

        # Impression share metrics (these are ratios, need to average)
        c["_search_is_sum"]          += row.metrics.search_impression_share or 0
        c["_search_budget_lost_sum"] += row.metrics.search_budget_lost_impression_share or 0
        c["_search_rank_lost_sum"]   += row.metrics.search_rank_lost_impression_share or 0
        c["_content_is_sum"]         += row.metrics.content_impression_share or 0
        c["_content_budget_lost_sum"]+= row.metrics.content_budget_lost_impression_share or 0
        c["_content_rank_lost_sum"]  += row.metrics.content_rank_lost_impression_share or 0
        c["_row_count"] += 1

    # Now pull budget amounts
    budget_ids = set()
    for c in campaigns.values():
        if c["budget_resource"]:
            budget_ids.add(c["budget_resource"])

    budgets = {}
    if budget_ids:
        budget_query = f"""
            SELECT
                campaign_budget.resource_name,
                campaign_budget.amount_micros,
                campaign_budget.type
            FROM campaign_budget
            WHERE campaign_budget.resource_name IN ({','.join(f"'{b}'" for b in budget_ids)})
        """
        try:
            budget_resp = service.search(customer_id=customer_id, query=budget_query)
            for row in budget_resp:
                budgets[row.campaign_budget.resource_name] = {
                    "daily_budget": row.campaign_budget.amount_micros / 1_000_000,
                    "type": str(row.campaign_budget.type),
                }
        except Exception as e:
            log.warning(f"Budget query failed: {e}")

    # Build final results
    results = []
    for c in campaigns.values():
        n = c["_row_count"] or 1
        c["spend"]       = round(c["spend"], 2)
        c["conversions"] = round(c["conversions"], 1)
        c["conv_value"]  = round(c["conv_value"], 2)
        c["roas"]        = round(c["conv_value"] / c["spend"], 2) if c["spend"] > 0 else 0
        c["cpc"]         = round(c["spend"] / c["clicks"], 2) if c["clicks"] else 0
        c["cr"]          = round(c["conversions"] / c["clicks"] * 100, 2) if c["clicks"] else 0

        c["search_impression_share"]    = round(c["_search_is_sum"] / n * 100, 1)
        c["search_lost_budget"]         = round(c["_search_budget_lost_sum"] / n * 100, 1)
        c["search_lost_rank"]           = round(c["_search_rank_lost_sum"] / n * 100, 1)
        c["content_impression_share"]   = round(c["_content_is_sum"] / n * 100, 1)
        c["content_lost_budget"]        = round(c["_content_budget_lost_sum"] / n * 100, 1)
        c["content_lost_rank"]          = round(c["_content_rank_lost_sum"] / n * 100, 1)

        budget_info = budgets.get(c["budget_resource"], {})
        c["daily_budget"] = round(budget_info.get("daily_budget", 0), 2)
        days = (POST_END - POST_START).days + 1
        c["daily_avg_spend"] = round(c["spend"] / days, 2)
        c["budget_utilization"] = round(c["daily_avg_spend"] / c["daily_budget"] * 100, 1) if c["daily_budget"] else 0

        # Determine the real constraint
        constraints = []
        if c["search_lost_budget"] > 10:
            constraints.append(f"Losing {c['search_lost_budget']}% IS to budget")
        if c["search_lost_rank"] > 10:
            constraints.append(f"Losing {c['search_lost_rank']}% IS to rank/quality")
        if c["content_lost_budget"] > 10:
            constraints.append(f"Losing {c['content_lost_budget']}% content IS to budget")
        if c["content_lost_rank"] > 10:
            constraints.append(f"Losing {c['content_lost_rank']}% content IS to rank")
        if c["budget_utilization"] < 60:
            constraints.append(f"Only using {c['budget_utilization']}% of budget — demand-limited")
        if not constraints:
            constraints.append("Fully optimized or data unavailable")
        c["constraints"] = constraints

        # Recommended action
        if c["budget_utilization"] < 60 and c["roas"] > 3:
            c["recommendation"] = "DEMAND-LIMITED: Add keywords/audiences to capture more demand at this ROAS"
        elif c["search_lost_budget"] > 20 and c["roas"] > 2.5:
            c["recommendation"] = "BUDGET-LIMITED: Increase budget — losing impressions to budget cap"
        elif c["search_lost_rank"] > 30:
            c["recommendation"] = "RANK-LIMITED: Improve quality score (landing page, ad relevance) or increase bids"
        elif c["content_lost_budget"] > 20 and c["roas"] > 2.5:
            c["recommendation"] = "BUDGET-LIMITED (Display/PMax): Increase budget"
        elif c["roas"] < 1.5 and c["spend"] > 500:
            c["recommendation"] = "UNDERPERFORMING: Review targeting, pause low-value keywords"
        else:
            c["recommendation"] = "MONITOR: Performance is reasonable, continue optimizing"

        # Clean up internal fields
        for k in list(c.keys()):
            if k.startswith("_") or k == "budget_resource":
                del c[k]

        results.append(c)

    results.sort(key=lambda x: x["conv_value"], reverse=True)

    # Output
    out_path = ROOT / "reports" / "campaign_constraints.json"
    out_path.write_text(json.dumps(results, indent=2))
    log.info(f"Saved: {out_path}")

    print("\n" + "=" * 90)
    print(f"{'Campaign':<40s} {'ROAS':>5s} {'Spend':>8s} {'Budget':>8s} {'Util%':>5s} {'SrchIS%':>7s} {'LostBudg':>8s} {'LostRank':>8s}")
    print("=" * 90)
    for c in results:
        print(f"{c['name'][:40]:<40s} {c['roas']:>5.1f}x ${c['spend']:>7,.0f} ${c['daily_budget']:>7,.0f} {c['budget_utilization']:>5.0f}% {c['search_impression_share']:>6.1f}% {c['search_lost_budget']:>7.1f}% {c['search_lost_rank']:>7.1f}%")
        print(f"  → Constraints: {'; '.join(c['constraints'])}")
        print(f"  → Action: {c['recommendation']}")
        print()


if __name__ == "__main__":
    run()
