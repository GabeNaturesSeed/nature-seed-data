#!/usr/bin/env python3
"""
Update Google Ads drought keyword final URLs to point to the new category page.
"""

import logging
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("update_urls")

ROOT = Path(__file__).resolve().parents[1]

NEW_DROUGHT_URL = "https://naturesseed.com/product-category/pasture-seed/drought-tolerant-pasture-seed/"

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
    login_id = ENV.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
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
    agc_service = client.get_service("AdGroupCriterionService")

    DROUGHT_TERMS = ["drought", "dry", "arid", "dryland", "water-wise", "low water"]

    # Find drought-related keywords
    kw_query = """
        SELECT
            campaign.name,
            ad_group.id, ad_group.name,
            ad_group_criterion.criterion_id,
            ad_group_criterion.keyword.text,
            ad_group_criterion.status,
            ad_group_criterion.final_urls
        FROM keyword_view
        WHERE campaign.status = 'ENABLED'
          AND ad_group.status = 'ENABLED'
          AND ad_group_criterion.status = 'ENABLED'
          AND segments.date DURING LAST_30_DAYS
    """
    resp = service.search(customer_id=customer_id, query=kw_query)

    drought_keywords = []
    seen = set()
    for row in resp:
        kw_text = row.ad_group_criterion.keyword.text
        ag_id = str(row.ad_group.id)
        crit_id = str(row.ad_group_criterion.criterion_id)
        key = f"{ag_id}_{crit_id}"

        if key in seen:
            continue
        seen.add(key)

        if any(t in kw_text.lower() for t in DROUGHT_TERMS):
            current_urls = list(row.ad_group_criterion.final_urls) if row.ad_group_criterion.final_urls else []
            drought_keywords.append({
                "ag_id": ag_id,
                "crit_id": crit_id,
                "keyword": kw_text,
                "campaign": row.campaign.name,
                "ad_group": row.ad_group.name,
                "current_urls": current_urls,
            })

    log.info(f"Found {len(drought_keywords)} drought-related keywords:")
    for dk in drought_keywords:
        log.info(f"  '{dk['keyword']}' in {dk['ad_group']} — current URLs: {dk['current_urls']}")

    # Update final URLs
    if not drought_keywords:
        log.info("No drought keywords to update")
        return

    ops = []
    for dk in drought_keywords:
        # Skip if already pointing to the right URL
        if NEW_DROUGHT_URL in dk["current_urls"]:
            log.info(f"  '{dk['keyword']}' already has correct URL — skipping")
            continue

        op = client.get_type("AdGroupCriterionOperation")
        resource = agc_service.ad_group_criterion_path(customer_id, dk["ag_id"], dk["crit_id"])
        op.update.resource_name = resource
        op.update.final_urls.append(NEW_DROUGHT_URL)
        op.update_mask.paths.append("final_urls")
        ops.append((op, dk))

    if ops:
        try:
            result = agc_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[o[0] for o in ops]
            )
            for i, r in enumerate(result.results):
                log.info(f"  Updated '{ops[i][1]['keyword']}' → {NEW_DROUGHT_URL}")
            log.info(f"\nUpdated {len(result.results)} keyword URLs")
        except GoogleAdsException as e:
            err = e.failure.errors[0].message if e.failure.errors else str(e)
            log.error(f"Failed: {err}")
    else:
        log.info("All drought keywords already have correct URLs")


if __name__ == "__main__":
    run()
