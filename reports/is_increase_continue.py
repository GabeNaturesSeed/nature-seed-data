#!/usr/bin/env python3
"""
IS Increase — Continue from Step 1b
====================================
The ad group 'Wildflower Seeds' (199364599372) and its keywords were already
created. This script continues:
  - Creates RSA ad for the Wildflower ad group
  - Pauses wildflower keywords in old Pasture ad groups
  - Creates intent-matched RSA ads for horse/drought/regional queries
  - Adds sitelinks + callouts to search campaigns
"""

import json
import logging
import time
from datetime import date
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("is_continue")

ROOT = Path(__file__).resolve().parents[1]


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

def _gads_client():
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
    return GoogleAdsClient.load_from_dict(config), customer_id


def run():
    client, customer_id = _gads_client()
    service = client.get_service("GoogleAdsService")
    ad_service = client.get_service("AdGroupAdService")
    agc_service = client.get_service("AdGroupCriterionService")

    all_actions = []
    WILDFLOWER_AG_ID = "199364599372"
    WILDFLOWER_AG_RESOURCE = f"customers/{customer_id}/adGroups/{WILDFLOWER_AG_ID}"

    # ── Step 1b: Create RSA ad for Wildflower ad group ───────────────────────
    log.info("STEP 1b: Creating wildflower RSA ad...")

    ad_op = client.get_type("AdGroupAdOperation")
    ad_group_ad = ad_op.create
    ad_group_ad.ad_group = WILDFLOWER_AG_RESOURCE
    ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

    ad = ad_group_ad.ad
    ad.final_urls.append("https://naturesseed.com/product-category/wildflower-seed/")

    headline_texts = [
        "Native Wildflower Seeds",
        "Premium Wildflower Seed Mix",
        "California Wildflower Seeds",
        "Shop Wildflower Seeds Online",
        "Native Wildflower Seed Blends",
        "Wildflower Seeds - Free Ship",
        "Beautiful Wildflower Mixes",
        "Easy-to-Grow Wildflower Seed",
        "USDA Tested Wildflower Seed",
        "Browse Wildflower Varieties",
    ]
    for h in headline_texts:
        headline = client.get_type("AdTextAsset")
        headline.text = h
        ad.responsive_search_ad.headlines.append(headline)

    desc_texts = [
        "Premium native wildflower seed mixes for every region. USDA-tested varieties. Free shipping on all orders.",
        "Create a stunning wildflower meadow with our curated seed blends. Native species for pollinators.",
        "Shop Nature's Seed wildflower collections. California natives, Texas mixes & more. Growing guides included.",
        "High-purity wildflower seeds with proven germination rates. Perfect for meadows & restoration projects.",
    ]
    for d in desc_texts:
        desc = client.get_type("AdTextAsset")
        desc.text = d
        ad.responsive_search_ad.descriptions.append(desc)

    try:
        resp = ad_service.mutate_ad_group_ads(customer_id=customer_id, operations=[ad_op])
        log.info(f"  Created wildflower RSA: {resp.results[0].resource_name}")
        all_actions.append("Created intent-matched RSA ad for Wildflower Seeds ad group")
    except GoogleAdsException as e:
        err = e.failure.errors[0].message if e.failure.errors else str(e)
        log.error(f"  Failed: {err}")
        all_actions.append(f"FAILED wildflower RSA: {err}")

    # ── Step 1c: Pause wildflower keywords in old Pasture ad groups ──────────
    log.info("\nSTEP 1c: Pausing wildflower keywords in old Pasture ad groups...")

    # Find wildflower keywords in Pasture campaign (not in the new ad group)
    kw_query = """
        SELECT
            campaign.name,
            ad_group.id, ad_group.name,
            ad_group_criterion.criterion_id,
            ad_group_criterion.keyword.text,
            ad_group_criterion.status
        FROM keyword_view
        WHERE campaign.status = 'ENABLED'
          AND ad_group.status = 'ENABLED'
          AND ad_group_criterion.status = 'ENABLED'
          AND segments.date DURING LAST_30_DAYS
    """
    kw_resp = service.search(customer_id=customer_id, query=kw_query)

    pause_ops = []
    seen = set()
    for row in kw_resp:
        kw_text = row.ad_group_criterion.keyword.text
        ag_id = str(row.ad_group.id)
        crit_id = str(row.ad_group_criterion.criterion_id)
        key = f"{ag_id}_{crit_id}"

        if key in seen:
            continue
        seen.add(key)

        # Only pause wildflower keywords that are in Pasture campaign but NOT in the new wildflower ad group
        if ag_id != WILDFLOWER_AG_ID and "pasture" in row.campaign.name.lower():
            if any(t in kw_text.lower() for t in ["wildflower", "wild flower"]):
                log.info(f"  Pausing '{kw_text}' in ad group '{row.ad_group.name}'")
                op = client.get_type("AdGroupCriterionOperation")
                resource = agc_service.ad_group_criterion_path(customer_id, ag_id, crit_id)
                op.update.resource_name = resource
                op.update.status = client.enums.AdGroupCriterionStatusEnum.PAUSED
                op.update_mask.paths.append("status")
                pause_ops.append(op)

    if pause_ops:
        try:
            resp = agc_service.mutate_ad_group_criteria(customer_id=customer_id, operations=pause_ops)
            log.info(f"  Paused {len(resp.results)} wildflower keywords in old groups")
            all_actions.append(f"Paused {len(resp.results)} wildflower keywords in Pasture ad groups")
        except GoogleAdsException as e:
            err = e.failure.errors[0].message if e.failure.errors else str(e)
            log.error(f"  Failed: {err}")
    else:
        log.info("  No wildflower keywords found to pause (may already be paused)")

    time.sleep(1)

    # ── Step 2: Intent-matched RSA ads for Pasture keywords ──────────────────
    log.info("\nSTEP 2: Creating intent-matched RSA ads for Pasture keywords...")

    # Find Pasture ad groups and their keywords
    ag_query = """
        SELECT
            campaign.id, campaign.name,
            ad_group.id, ad_group.name
        FROM ad_group
        WHERE campaign.status = 'ENABLED'
          AND ad_group.status = 'ENABLED'
    """
    ag_resp = service.search(customer_id=customer_id, query=ag_query)
    pasture_ad_groups = {}
    for row in ag_resp:
        if "pasture" in row.campaign.name.lower() and str(row.ad_group.id) != WILDFLOWER_AG_ID:
            pasture_ad_groups[str(row.ad_group.id)] = {
                "id": str(row.ad_group.id),
                "name": row.ad_group.name,
                "campaign_id": str(row.campaign.id),
                "campaign": row.campaign.name,
            }

    # Get keywords for pasture ad groups
    pasture_keywords = {}
    for row2 in service.search(customer_id=customer_id, query=kw_query):
        ag_id = str(row2.ad_group.id)
        if ag_id in pasture_ad_groups:
            kw_text = row2.ad_group_criterion.keyword.text
            key = f"{ag_id}_{kw_text}"
            if key not in pasture_keywords:
                pasture_keywords[key] = {
                    "ad_group_id": ag_id,
                    "keyword": kw_text,
                }

    intent_configs = {
        "horse": {
            "match_terms": ["horse", "equine", "forage"],
            "headlines": [
                "Horse Pasture Grass Seed",
                "Equine-Safe Pasture Seed",
                "Premium Horse Forage Seed",
                "Pasture Seed for Horses",
                "Horse-Safe Grass Seed Mix",
                "Shop Equine Pasture Seed",
                "Forage Grass Seed Blends",
                "Best Horse Pasture Seed",
                "USDA Tested Forage Seed",
                "Fast-Growing Horse Pasture",
            ],
            "descriptions": [
                "Premium horse-safe pasture grass seed mixes. Nutrient-rich forage varieties. USDA-tested. Free shipping.",
                "Build a lush, durable horse pasture with our expert seed blends. Designed for heavy grazing and fast recovery.",
                "Trusted by ranchers nationwide. High-quality equine pasture seed with proven performance. Shop Nature's Seed.",
            ],
            "url": "https://naturesseed.com/product-category/pasture-grass-seed/",
        },
        "drought": {
            "match_terms": ["drought", "dry", "arid"],
            "headlines": [
                "Drought-Tolerant Pasture Seed",
                "Dry Climate Pasture Grass",
                "Water-Wise Pasture Seed Mix",
                "Heat & Drought Pasture Seed",
                "Low-Water Pasture Grass Seed",
                "Drought-Resistant Forage Seed",
                "Arid Climate Grass Seed",
                "Save Water - Pasture Seed",
                "Hardy Drought Pasture Mix",
                "Thrives in Dry Conditions",
            ],
            "descriptions": [
                "Drought-tolerant pasture seed blends for dry climates. Deep-rooting varieties that thrive with minimal water.",
                "Premium drought-resistant pasture grass seed. USDA-tested for arid conditions. Free shipping on all orders.",
                "Build a resilient, low-water pasture. Our drought-hardy seed mixes handle the toughest growing conditions.",
            ],
            "url": "https://naturesseed.com/product-category/pasture-grass-seed/",
        },
        "regional": {
            "match_terms": ["texas", "california", "western", "southern"],
            "headlines": [
                "Regional Pasture Grass Seed",
                "Texas Pasture Seed Mixes",
                "Western Pasture Grass Seed",
                "Climate-Adapted Pasture Seed",
                "Local Pasture Seed Blends",
                "State-Specific Pasture Seed",
                "Native Pasture Grass Seed",
                "Best Regional Pasture Mix",
                "Shop by Your Climate Zone",
                "Expert Regional Seed Blends",
            ],
            "descriptions": [
                "Pasture grass seed mixes formulated for your climate zone. Texas, California, Western & more. Free shipping.",
                "Region-specific pasture seed blends with proven performance. USDA-tested for your local growing conditions.",
                "Get the right pasture seed for your state. Climate-adapted blends from Nature's Seed experts.",
            ],
            "url": "https://naturesseed.com/product-category/pasture-grass-seed/",
        },
    }

    for ag_id, ag_data in pasture_ad_groups.items():
        ag_kws = [pk for pk in pasture_keywords.values() if pk["ad_group_id"] == ag_id]

        for intent_name, intent_cfg in intent_configs.items():
            matching = [kw for kw in ag_kws
                       if any(t in kw["keyword"].lower() for t in intent_cfg["match_terms"])]
            if not matching:
                continue

            log.info(f"  Creating {intent_name} RSA for '{ag_data['name']}'...")

            ad_op = client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_op.create
            ag_resource = f"customers/{customer_id}/adGroups/{ag_id}"
            ad_group_ad.ad_group = ag_resource
            ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

            ad = ad_group_ad.ad
            ad.final_urls.append(intent_cfg["url"])

            for h in intent_cfg["headlines"]:
                headline = client.get_type("AdTextAsset")
                headline.text = h
                ad.responsive_search_ad.headlines.append(headline)

            for d in intent_cfg["descriptions"]:
                desc = client.get_type("AdTextAsset")
                desc.text = d
                ad.responsive_search_ad.descriptions.append(desc)

            try:
                resp = ad_service.mutate_ad_group_ads(customer_id=customer_id, operations=[ad_op])
                log.info(f"    Created: {resp.results[0].resource_name}")
                all_actions.append(f"Created {intent_name}-intent RSA in '{ag_data['name']}'")
            except GoogleAdsException as e:
                err = e.failure.errors[0].message if e.failure.errors else str(e)
                log.error(f"    Failed: {err}")
                all_actions.append(f"FAILED: {intent_name} RSA in '{ag_data['name']}' — {err}")

    time.sleep(1)

    # ── Step 3: Sitelinks + Callouts ─────────────────────────────────────────
    log.info("\nSTEP 3: Adding sitelinks + callouts to search campaigns...")

    # Find search campaign IDs
    search_campaigns = set()
    for ag in pasture_ad_groups.values():
        search_campaigns.add((ag["campaign_id"], ag["campaign"]))

    # Also find the other search campaigns
    camp_query = """
        SELECT campaign.id, campaign.name, campaign.status
        FROM campaign
        WHERE campaign.status = 'ENABLED'
    """
    camp_resp = service.search(customer_id=customer_id, query=camp_query)
    for row in camp_resp:
        if "search" in row.campaign.name.lower():
            search_campaigns.add((str(row.campaign.id), row.campaign.name))

    # Pull existing extensions
    log.info("  Pulling existing campaign extensions...")
    ext_query = """
        SELECT
            campaign.id, campaign.name, campaign.status,
            campaign_asset.field_type,
            asset.sitelink_asset.link_text,
            asset.callout_asset.callout_text
        FROM campaign_asset
        WHERE campaign.status = 'ENABLED'
    """
    existing_ext = {}
    try:
        ext_resp = service.search(customer_id=customer_id, query=ext_query)
        for row in ext_resp:
            cid = str(row.campaign.id)
            if cid not in existing_ext:
                existing_ext[cid] = {"sitelinks": [], "callouts": []}
            ft = str(row.campaign_asset.field_type).split(".")[-1]
            if "SITELINK" in ft and row.asset.sitelink_asset.link_text:
                existing_ext[cid]["sitelinks"].append(row.asset.sitelink_asset.link_text)
            if "CALLOUT" in ft and row.asset.callout_asset.callout_text:
                existing_ext[cid]["callouts"].append(row.asset.callout_asset.callout_text)
    except GoogleAdsException as e:
        log.warning(f"  Extensions query failed: {e}")

    asset_service = client.get_service("AssetService")
    ca_service = client.get_service("CampaignAssetService")

    sitelink_defs = [
        {"text": "Shop Grass Seed", "desc1": "Premium USDA-tested grass seed", "desc2": "Free shipping on all orders", "url": "https://naturesseed.com/product-category/grass-seed/"},
        {"text": "Pasture & Forage Seed", "desc1": "Horse, cattle & livestock pasture", "desc2": "Climate-adapted seed blends", "url": "https://naturesseed.com/product-category/pasture-grass-seed/"},
        {"text": "Wildflower Seeds", "desc1": "Native wildflower seed mixes", "desc2": "Beautiful low-maintenance meadows", "url": "https://naturesseed.com/product-category/wildflower-seed/"},
        {"text": "Growing Guides", "desc1": "Expert planting & care guides", "desc2": "Get the best results from seed", "url": "https://naturesseed.com/resources/"},
    ]

    callout_defs = ["Free Shipping", "USDA Tested Seed", "Since 1998", "Expert Growing Guides", "Fast Germination", "Climate-Adapted Blends"]

    for camp_id, camp_name in search_campaigns:
        log.info(f"\n  Campaign: {camp_name}")
        camp_ext = existing_ext.get(camp_id, {"sitelinks": [], "callouts": []})
        camp_resource = f"customers/{customer_id}/campaigns/{camp_id}"

        # Sitelinks
        existing_sl_texts = {t.lower() for t in camp_ext["sitelinks"]}
        for sl in sitelink_defs:
            if sl["text"].lower() in existing_sl_texts:
                log.info(f"    Sitelink '{sl['text']}' already exists — skipping")
                continue

            # Create asset
            asset_op = client.get_type("AssetOperation")
            asset = asset_op.create
            asset.sitelink_asset.link_text = sl["text"]
            asset.sitelink_asset.description1 = sl["desc1"]
            asset.sitelink_asset.description2 = sl["desc2"]
            asset.final_urls.append(sl["url"])

            try:
                asset_resp = asset_service.mutate_assets(customer_id=customer_id, operations=[asset_op])
                asset_resource = asset_resp.results[0].resource_name

                # Link to campaign
                link_op = client.get_type("CampaignAssetOperation")
                link_op.create.asset = asset_resource
                link_op.create.campaign = camp_resource
                link_op.create.field_type = client.enums.AssetFieldTypeEnum.SITELINK

                ca_service.mutate_campaign_assets(customer_id=customer_id, operations=[link_op])
                log.info(f"    Added sitelink '{sl['text']}'")
                all_actions.append(f"Added sitelink '{sl['text']}' to {camp_name}")
            except GoogleAdsException as e:
                err = e.failure.errors[0].message if e.failure.errors else str(e)
                log.warning(f"    Sitelink '{sl['text']}' failed: {err}")

        # Callouts
        existing_co_texts = {t.lower() for t in camp_ext["callouts"]}
        added_callouts = 0
        for ct in callout_defs:
            if ct.lower() in existing_co_texts:
                continue
            if added_callouts >= 4:
                break

            asset_op = client.get_type("AssetOperation")
            asset_op.create.callout_asset.callout_text = ct

            try:
                asset_resp = asset_service.mutate_assets(customer_id=customer_id, operations=[asset_op])
                asset_resource = asset_resp.results[0].resource_name

                link_op = client.get_type("CampaignAssetOperation")
                link_op.create.asset = asset_resource
                link_op.create.campaign = camp_resource
                link_op.create.field_type = client.enums.AssetFieldTypeEnum.CALLOUT

                ca_service.mutate_campaign_assets(customer_id=customer_id, operations=[link_op])
                log.info(f"    Added callout '{ct}'")
                all_actions.append(f"Added callout '{ct}' to {camp_name}")
                added_callouts += 1
            except GoogleAdsException as e:
                err = e.failure.errors[0].message if e.failure.errors else str(e)
                log.warning(f"    Callout '{ct}' failed: {err}")

    # ── Summary ──────────────────────────────────────────────────────────────
    log.info(f"\n{'='*60}")
    log.info("ALL ACTIONS COMPLETED")
    log.info(f"{'='*60}")
    for i, action in enumerate(all_actions, 1):
        log.info(f"  {i}. {action}")

    # Save action log
    action_log_path = ROOT / "IS-Increase" / "action_log.json"
    action_log_path.parent.mkdir(exist_ok=True)
    action_log_path.write_text(json.dumps({
        "date": str(date.today()),
        "actions": all_actions,
    }, indent=2))
    log.info(f"\nAction log: {action_log_path}")


if __name__ == "__main__":
    run()
