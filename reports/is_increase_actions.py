#!/usr/bin/env python3
"""
IS Increase — Google Ads Account Changes
=========================================
Implements Quality Score improvements directly via Google Ads API:
  1. Restructure ad groups (move misplaced keywords)
  2. Create intent-matched RSA ads
  3. Add sitelinks + callout extensions
  4. Pause low-QS keywords that waste spend

Usage:
    python3 reports/is_increase_actions.py
"""

import json
import logging
import time
from datetime import date
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("is_increase")

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


# ── Step 0: Pull current structure ───────────────────────────────────────────

def pull_full_structure(service, customer_id):
    """Pull all ad groups, keywords, ads, and extensions for enabled campaigns."""

    # Ad groups with their campaigns
    log.info("Pulling ad groups...")
    ag_query = """
        SELECT
            campaign.id, campaign.name,
            ad_group.id, ad_group.name, ad_group.status,
            ad_group.cpc_bid_micros
        FROM ad_group
        WHERE campaign.status = 'ENABLED'
          AND ad_group.status != 'REMOVED'
    """
    ag_resp = service.search(customer_id=customer_id, query=ag_query)
    ad_groups = {}
    for row in ag_resp:
        ag_id = str(row.ad_group.id)
        ad_groups[ag_id] = {
            "id": ag_id,
            "name": row.ad_group.name,
            "status": str(row.ad_group.status).split(".")[-1],
            "campaign_id": str(row.campaign.id),
            "campaign": row.campaign.name,
            "cpc_bid_micros": row.ad_group.cpc_bid_micros,
            "keywords": [],
            "ads": [],
        }
    log.info(f"  {len(ad_groups)} ad groups")

    # Keywords
    log.info("Pulling keywords...")
    kw_query = """
        SELECT
            campaign.id, campaign.name,
            ad_group.id, ad_group.name,
            ad_group_criterion.criterion_id,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.status,
            ad_group_criterion.quality_info.quality_score,
            ad_group_criterion.quality_info.creative_quality_score,
            ad_group_criterion.quality_info.search_predicted_ctr,
            ad_group_criterion.quality_info.post_click_quality_score,
            ad_group_criterion.final_urls,
            metrics.impressions, metrics.clicks, metrics.cost_micros,
            metrics.conversions, metrics.conversions_value
        FROM keyword_view
        WHERE campaign.status = 'ENABLED'
          AND ad_group.status = 'ENABLED'
          AND segments.date DURING LAST_30_DAYS
    """
    kw_resp = service.search(customer_id=customer_id, query=kw_query)

    keywords_agg = {}
    for row in kw_resp:
        ag_id = str(row.ad_group.id)
        crit_id = str(row.ad_group_criterion.criterion_id)
        key = f"{ag_id}_{crit_id}"

        if key not in keywords_agg:
            qi = row.ad_group_criterion.quality_info
            urls = list(row.ad_group_criterion.final_urls) if row.ad_group_criterion.final_urls else []
            keywords_agg[key] = {
                "criterion_id": crit_id,
                "ad_group_id": ag_id,
                "campaign_id": str(row.campaign.id),
                "campaign": row.campaign.name,
                "ad_group": row.ad_group.name,
                "keyword": row.ad_group_criterion.keyword.text,
                "match_type": str(row.ad_group_criterion.keyword.match_type).split(".")[-1],
                "status": str(row.ad_group_criterion.status).split(".")[-1],
                "quality_score": qi.quality_score or 0,
                "ad_relevance": str(qi.creative_quality_score).split(".")[-1],
                "expected_ctr": str(qi.search_predicted_ctr).split(".")[-1],
                "landing_page_exp": str(qi.post_click_quality_score).split(".")[-1],
                "final_urls": urls,
                "impressions": 0, "clicks": 0, "spend": 0,
                "conversions": 0, "conv_value": 0,
            }
        kw = keywords_agg[key]
        kw["impressions"] += row.metrics.impressions
        kw["clicks"]      += row.metrics.clicks
        kw["spend"]       += row.metrics.cost_micros / 1_000_000
        kw["conversions"] += row.metrics.conversions
        kw["conv_value"]  += row.metrics.conversions_value

    for kw in keywords_agg.values():
        kw["spend"] = round(kw["spend"], 2)
        kw["conversions"] = round(kw["conversions"], 1)
        kw["conv_value"] = round(kw["conv_value"], 2)
        ag_id = kw["ad_group_id"]
        if ag_id in ad_groups:
            ad_groups[ag_id]["keywords"].append(kw)

    log.info(f"  {len(keywords_agg)} keywords")

    # Ads
    log.info("Pulling ads...")
    ad_query = """
        SELECT
            campaign.id, campaign.name,
            ad_group.id, ad_group.name,
            ad_group_ad.ad.id,
            ad_group_ad.ad.type,
            ad_group_ad.ad.final_urls,
            ad_group_ad.ad.responsive_search_ad.headlines,
            ad_group_ad.ad.responsive_search_ad.descriptions,
            ad_group_ad.status
        FROM ad_group_ad
        WHERE campaign.status = 'ENABLED'
          AND ad_group.status = 'ENABLED'
          AND ad_group_ad.status != 'REMOVED'
    """
    ad_resp = service.search(customer_id=customer_id, query=ad_query)

    ads_seen = set()
    for row in ad_resp:
        ad_id = str(row.ad_group_ad.ad.id)
        ag_id = str(row.ad_group.id)
        if ad_id in ads_seen:
            continue
        ads_seen.add(ad_id)

        headlines = []
        descriptions = []
        if row.ad_group_ad.ad.responsive_search_ad:
            rsa = row.ad_group_ad.ad.responsive_search_ad
            headlines = [{"text": h.text, "pinned": str(h.pinned_field).split(".")[-1] if h.pinned_field else None}
                        for h in rsa.headlines]
            descriptions = [{"text": d.text, "pinned": str(d.pinned_field).split(".")[-1] if d.pinned_field else None}
                           for d in rsa.descriptions]

        urls = list(row.ad_group_ad.ad.final_urls) if row.ad_group_ad.ad.final_urls else []

        ad_data = {
            "ad_id": ad_id,
            "ad_group_id": ag_id,
            "type": str(row.ad_group_ad.ad.type).split(".")[-1],
            "status": str(row.ad_group_ad.status).split(".")[-1],
            "final_urls": urls,
            "headlines": headlines,
            "descriptions": descriptions,
        }

        if ag_id in ad_groups:
            ad_groups[ag_id]["ads"].append(ad_data)

    log.info(f"  {len(ads_seen)} ads")

    # Extensions (asset-based in newer API)
    log.info("Pulling campaign-level assets (extensions)...")
    ext_query = """
        SELECT
            campaign.id, campaign.name, campaign.status,
            campaign_asset.asset,
            campaign_asset.field_type,
            asset.name,
            asset.type,
            asset.sitelink_asset.description1,
            asset.sitelink_asset.description2,
            asset.sitelink_asset.link_text,
            asset.callout_asset.callout_text,
            asset.structured_snippet_asset.header,
            asset.structured_snippet_asset.values
        FROM campaign_asset
        WHERE campaign.status = 'ENABLED'
    """
    try:
        ext_resp = service.search(customer_id=customer_id, query=ext_query)
        extensions = []
        for row in ext_resp:
            ext = {
                "campaign_id": str(row.campaign.id),
                "campaign": row.campaign.name,
                "field_type": str(row.campaign_asset.field_type).split(".")[-1],
                "asset_type": str(row.asset.type).split(".")[-1],
                "name": row.asset.name,
            }
            if row.asset.sitelink_asset and row.asset.sitelink_asset.link_text:
                ext["sitelink_text"] = row.asset.sitelink_asset.link_text
                ext["sitelink_desc1"] = row.asset.sitelink_asset.description1
                ext["sitelink_desc2"] = row.asset.sitelink_asset.description2
            if row.asset.callout_asset and row.asset.callout_asset.callout_text:
                ext["callout_text"] = row.asset.callout_asset.callout_text
            if row.asset.structured_snippet_asset and row.asset.structured_snippet_asset.header:
                ext["snippet_header"] = row.asset.structured_snippet_asset.header
                ext["snippet_values"] = list(row.asset.structured_snippet_asset.values)
            extensions.append(ext)
        log.info(f"  {len(extensions)} campaign assets/extensions")
    except Exception as e:
        log.warning(f"  Extensions query failed: {e}")
        extensions = []

    return ad_groups, list(keywords_agg.values()), extensions


# ── Step 1: Create new ad group for wildflower keywords ──────────────────────

def create_wildflower_ad_group(client, customer_id, pasture_campaign_id, wildflower_keywords):
    """Create a new ad group for wildflower keywords and move them there."""
    actions = []

    service = client.get_service("GoogleAdsService")
    ag_service = client.get_service("AdGroupService")
    agc_service = client.get_service("AdGroupCriterionService")
    ad_service = client.get_service("AdGroupAdService")

    # 1. Create new ad group "Wildflower Seeds"
    log.info("Creating 'Wildflower Seeds' ad group...")
    ag_operation = client.get_type("AdGroupOperation")
    ag = ag_operation.create
    ag.name = "Wildflower Seeds"
    ag.campaign = client.get_service("CampaignService").campaign_path(customer_id, pasture_campaign_id)
    ag.status = client.enums.AdGroupStatusEnum.ENABLED
    ag.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
    ag.cpc_bid_micros = 2_000_000  # $2.00 CPC bid

    try:
        ag_response = ag_service.mutate_ad_groups(customer_id=customer_id, operations=[ag_operation])
        new_ag_resource = ag_response.results[0].resource_name
        new_ag_id = new_ag_resource.split("/")[-1]
        log.info(f"  Created ad group: {new_ag_resource}")
        actions.append(f"Created ad group 'Wildflower Seeds' (ID: {new_ag_id})")
    except GoogleAdsException as e:
        log.error(f"  Failed to create ad group: {e.failure.errors[0].message}")
        return actions

    # 2. Add wildflower keywords to the new ad group
    log.info("Adding wildflower keywords to new ad group...")
    kw_operations = []
    for kw in wildflower_keywords:
        op = client.get_type("AdGroupCriterionOperation")
        criterion = op.create
        criterion.ad_group = new_ag_resource
        criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
        criterion.keyword.text = kw["keyword"]
        match_type = kw["match_type"].upper()
        if match_type == "EXACT":
            criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.EXACT
        elif match_type == "PHRASE":
            criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
        else:
            criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
        # Set landing page URL if available
        if kw.get("final_urls"):
            criterion.final_urls.append(kw["final_urls"][0])
        kw_operations.append(op)

    if kw_operations:
        try:
            kw_response = agc_service.mutate_ad_group_criteria(
                customer_id=customer_id, operations=kw_operations
            )
            log.info(f"  Added {len(kw_response.results)} keywords to Wildflower Seeds")
            actions.append(f"Added {len(kw_response.results)} wildflower keywords to new ad group")
        except GoogleAdsException as e:
            log.error(f"  Failed to add keywords: {e.failure.errors[0].message}")

    # 3. Create RSA ad for the new wildflower ad group
    log.info("Creating wildflower RSA ad...")
    ad_op = client.get_type("AdGroupAdOperation")
    ad_group_ad = ad_op.create
    ad_group_ad.ad_group = new_ag_resource
    ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

    ad = ad_group_ad.ad
    ad.final_urls.append("https://naturesseed.com/product-category/wildflower-seed/")

    # Headlines (need 3-15)
    headline_texts = [
        "Native Wildflower Seeds",
        "Premium Wildflower Seed Mix",
        "California Wildflower Seeds",
        "Shop Wildflower Seeds Online",
        "Native Wildflower Seed Blends",
        "Wildflower Seeds — Free Shipping",
        "Beautiful Wildflower Mixes",
        "Easy-to-Grow Wildflower Seeds",
        "USDA Tested Wildflower Seed",
        "Browse Wildflower Varieties",
    ]
    for i, h in enumerate(headline_texts):
        headline = client.get_type("AdTextAsset")
        headline.text = h
        ad.responsive_search_ad.headlines.append(headline)

    # Descriptions (need 2-4)
    desc_texts = [
        "Premium native wildflower seed mixes for every region. USDA-tested, fast-growing varieties. Free shipping on all orders.",
        "Create a stunning wildflower meadow with our curated seed blends. Native species for pollinators & low maintenance beauty.",
        "Shop Nature's Seed wildflower collections. California natives, Texas mixes & more. Expert growing guides included.",
        "High-purity wildflower seeds with proven germination rates. Perfect for meadows, borders & restoration projects.",
    ]
    for d_text in desc_texts:
        desc = client.get_type("AdTextAsset")
        desc.text = d_text
        ad.responsive_search_ad.descriptions.append(desc)

    try:
        ad_response = ad_service.mutate_ad_group_ads(customer_id=customer_id, operations=[ad_op])
        log.info(f"  Created wildflower RSA: {ad_response.results[0].resource_name}")
        actions.append("Created intent-matched RSA ad for Wildflower Seeds ad group")
    except GoogleAdsException as e:
        log.error(f"  Failed to create ad: {e.failure.errors[0].message}")

    # 4. Pause the wildflower keywords in the old Pasture ad group
    log.info("Pausing wildflower keywords in old Pasture ad groups...")
    pause_ops = []
    from google.api_core import protobuf_helpers
    for kw in wildflower_keywords:
        op = client.get_type("AdGroupCriterionOperation")
        criterion_resource = client.get_service("AdGroupCriterionService").ad_group_criterion_path(
            customer_id, kw["ad_group_id"], kw["criterion_id"]
        )
        op.update.resource_name = criterion_resource
        op.update.status = client.enums.AdGroupCriterionStatusEnum.PAUSED
        op.update_mask.paths.append("status")
        pause_ops.append(op)

    if pause_ops:
        try:
            pause_response = agc_service.mutate_ad_group_criteria(
                customer_id=customer_id, operations=pause_ops
            )
            log.info(f"  Paused {len(pause_response.results)} keywords in old ad groups")
            actions.append(f"Paused {len(pause_response.results)} wildflower keywords in Pasture ad groups")
        except GoogleAdsException as e:
            log.error(f"  Failed to pause keywords: {e.failure.errors[0].message}")

    return actions


# ── Step 2: Create intent-matched RSA ads for Pasture keywords ───────────────

def create_pasture_intent_ads(client, customer_id, pasture_ad_groups, keywords):
    """Create new RSA ads with better keyword-to-ad matching for pasture ad groups."""
    actions = []
    ad_service = client.get_service("AdGroupAdService")

    # Group keywords by intent
    intent_groups = {
        "horse": {
            "keywords": ["horse", "equine", "forage"],
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
                "Premium horse-safe pasture grass seed mixes. Nutrient-rich forage varieties. USDA-tested with high germination rates. Free shipping.",
                "Build a lush, durable horse pasture with our expert seed blends. Designed for heavy grazing and fast recovery.",
                "Trusted by ranchers nationwide. High-quality equine pasture seed with proven performance. Shop Nature's Seed today.",
            ],
            "url": "https://naturesseed.com/product-category/pasture-grass-seed/",
        },
        "drought": {
            "keywords": ["drought", "dry", "arid"],
            "headlines": [
                "Drought-Tolerant Pasture Seed",
                "Dry Climate Pasture Grass",
                "Water-Wise Pasture Seed Mix",
                "Heat & Drought Pasture Seed",
                "Low-Water Pasture Grass Seed",
                "Drought-Resistant Forage Seed",
                "Arid Climate Grass Seed",
                "Save Water — Pasture Seed",
                "Hardy Drought Pasture Mix",
                "Thrives in Dry Conditions",
            ],
            "descriptions": [
                "Drought-tolerant pasture seed blends engineered for dry climates. Deep-rooting varieties that thrive with minimal water.",
                "Premium drought-resistant pasture grass seed. USDA-tested for arid conditions. Free shipping on all orders.",
                "Build a resilient, low-water pasture. Our drought-hardy seed mixes are designed for the toughest growing conditions.",
            ],
            "url": "https://naturesseed.com/product-category/pasture-grass-seed/",
        },
        "regional": {
            "keywords": ["texas", "california", "western", "southern"],
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
                "Pasture grass seed mixes specifically formulated for your climate zone. Texas, California, Western & more. Free shipping.",
                "Region-specific pasture seed blends with proven performance. USDA-tested varieties adapted to your local growing conditions.",
                "Stop guessing — get the right pasture seed for your state. Climate-adapted blends from Nature's Seed experts.",
            ],
            "url": "https://naturesseed.com/product-category/pasture-grass-seed/",
        },
    }

    # For each pasture ad group, check which keywords match and create tailored ads
    for ag_id, ag_data in pasture_ad_groups.items():
        ag_keywords = [kw for kw in keywords if kw["ad_group_id"] == ag_id and kw["status"] == "ENABLED"]
        if not ag_keywords:
            continue

        for intent_name, intent_data in intent_groups.items():
            # Check if any keywords in this ad group match this intent
            matching = [kw for kw in ag_keywords
                       if any(t in kw["keyword"].lower() for t in intent_data["keywords"])]

            if not matching:
                continue

            # Check if there's already a good ad for this intent
            existing_ads = ag_data.get("ads", [])
            has_intent_ad = False
            for ad in existing_ads:
                for h in ad.get("headlines", []):
                    if any(t in h["text"].lower() for t in intent_data["keywords"]):
                        has_intent_ad = True
                        break

            if has_intent_ad:
                log.info(f"  Ad group {ag_data['name']} already has {intent_name} intent ad — skipping")
                continue

            # Create the RSA
            log.info(f"  Creating {intent_name} RSA for ad group '{ag_data['name']}'...")
            ad_op = client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_op.create
            ag_resource = client.get_service("AdGroupService").ad_group_path(customer_id, ag_id)
            ad_group_ad.ad_group = ag_resource
            ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

            ad = ad_group_ad.ad
            ad.final_urls.append(intent_data["url"])

            for h_text in intent_data["headlines"]:
                headline = client.get_type("AdTextAsset")
                headline.text = h_text
                ad.responsive_search_ad.headlines.append(headline)

            for d_text in intent_data["descriptions"]:
                desc = client.get_type("AdTextAsset")
                desc.text = d_text
                ad.responsive_search_ad.descriptions.append(desc)

            try:
                resp = ad_service.mutate_ad_group_ads(customer_id=customer_id, operations=[ad_op])
                log.info(f"    Created: {resp.results[0].resource_name}")
                actions.append(f"Created {intent_name}-intent RSA in '{ag_data['name']}'")
            except GoogleAdsException as e:
                err_msg = e.failure.errors[0].message if e.failure.errors else str(e)
                log.error(f"    Failed: {err_msg}")
                actions.append(f"FAILED: {intent_name} RSA in '{ag_data['name']}' — {err_msg}")

    return actions


# ── Step 3: Add sitelinks + callouts ─────────────────────────────────────────

def add_campaign_extensions(client, customer_id, campaign_id, campaign_name, existing_extensions):
    """Add sitelinks and callout extensions to a campaign if missing."""
    actions = []
    asset_service = client.get_service("AssetService")
    campaign_asset_service = client.get_service("CampaignAssetService")

    # Check what already exists
    existing_sitelinks = [e for e in existing_extensions
                         if e.get("campaign_id") == campaign_id and "SITELINK" in e.get("field_type", "")]
    existing_callouts = [e for e in existing_extensions
                        if e.get("campaign_id") == campaign_id and "CALLOUT" in e.get("field_type", "")]

    campaign_resource = client.get_service("CampaignService").campaign_path(customer_id, campaign_id)

    # Add sitelinks if fewer than 4
    if len(existing_sitelinks) < 4:
        sitelinks = [
            {
                "text": "Shop Grass Seed",
                "desc1": "Premium USDA-tested grass seed",
                "desc2": "Free shipping on all orders",
                "url": "https://naturesseed.com/product-category/grass-seed/",
            },
            {
                "text": "Pasture & Forage Seed",
                "desc1": "Horse, cattle & livestock pasture",
                "desc2": "Climate-adapted seed blends",
                "url": "https://naturesseed.com/product-category/pasture-grass-seed/",
            },
            {
                "text": "Wildflower Seeds",
                "desc1": "Native wildflower seed mixes",
                "desc2": "Beautiful low-maintenance meadows",
                "url": "https://naturesseed.com/product-category/wildflower-seed/",
            },
            {
                "text": "Growing Guides",
                "desc1": "Expert planting & care guides",
                "desc2": "Get the best results from seed",
                "url": "https://naturesseed.com/resources/",
            },
        ]

        # Skip sitelinks that already exist
        existing_texts = {e.get("sitelink_text", "").lower() for e in existing_sitelinks}
        new_sitelinks = [s for s in sitelinks if s["text"].lower() not in existing_texts]

        for sl in new_sitelinks:
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
                log.info(f"  Created sitelink asset: {sl['text']}")

                # Link to campaign
                link_op = client.get_type("CampaignAssetOperation")
                link_op.create.asset = asset_resource
                link_op.create.campaign = campaign_resource
                link_op.create.field_type = client.enums.AssetFieldTypeEnum.SITELINK

                link_resp = campaign_asset_service.mutate_campaign_assets(
                    customer_id=customer_id, operations=[link_op]
                )
                log.info(f"    Linked to {campaign_name}")
                actions.append(f"Added sitelink '{sl['text']}' to {campaign_name}")
            except GoogleAdsException as e:
                err_msg = e.failure.errors[0].message if e.failure.errors else str(e)
                log.warning(f"  Sitelink '{sl['text']}' failed: {err_msg}")

    # Add callouts if fewer than 4
    if len(existing_callouts) < 4:
        callouts = [
            "Free Shipping",
            "USDA Tested Seed",
            "Since 1998",
            "Expert Growing Guides",
            "Fast Germination",
            "Climate-Adapted Blends",
        ]

        existing_callout_texts = {e.get("callout_text", "").lower() for e in existing_callouts}
        new_callouts = [c for c in callouts if c.lower() not in existing_callout_texts][:4]

        for ct in new_callouts:
            asset_op = client.get_type("AssetOperation")
            asset_op.create.callout_asset.callout_text = ct

            try:
                asset_resp = asset_service.mutate_assets(customer_id=customer_id, operations=[asset_op])
                asset_resource = asset_resp.results[0].resource_name

                link_op = client.get_type("CampaignAssetOperation")
                link_op.create.asset = asset_resource
                link_op.create.campaign = campaign_resource
                link_op.create.field_type = client.enums.AssetFieldTypeEnum.CALLOUT

                campaign_asset_service.mutate_campaign_assets(
                    customer_id=customer_id, operations=[link_op]
                )
                log.info(f"  Added callout '{ct}' to {campaign_name}")
                actions.append(f"Added callout '{ct}' to {campaign_name}")
            except GoogleAdsException as e:
                err_msg = e.failure.errors[0].message if e.failure.errors else str(e)
                log.warning(f"  Callout '{ct}' failed: {err_msg}")

    return actions


# ── Main ─────────────────────────────────────────────────────────────────────

def run():
    client, customer_id = _gads_client()
    service = client.get_service("GoogleAdsService")

    all_actions = []

    # Step 0: Pull current structure
    ad_groups, keywords, extensions = pull_full_structure(service, customer_id)

    # Save structure for reference
    structure_path = ROOT / "reports" / "ads_structure.json"
    structure_path.write_text(json.dumps({
        "ad_groups": {k: {**v, "keywords": v["keywords"], "ads": v["ads"]} for k, v in ad_groups.items()},
        "extensions": extensions,
    }, indent=2, default=str))
    log.info(f"Saved structure to {structure_path}")

    # Identify Pasture campaign and wildflower keywords
    pasture_campaign_id = None
    pasture_ad_groups = {}
    wildflower_keywords = []

    for ag_id, ag in ad_groups.items():
        if "pasture" in ag["campaign"].lower():
            pasture_campaign_id = ag["campaign_id"]
            pasture_ad_groups[ag_id] = ag
            for kw in ag["keywords"]:
                if any(t in kw["keyword"].lower() for t in ["wildflower", "wild flower"]):
                    wildflower_keywords.append(kw)

    # Step 1: Move wildflower keywords to new ad group
    if wildflower_keywords and pasture_campaign_id:
        log.info(f"\n{'='*60}")
        log.info(f"STEP 1: Moving {len(wildflower_keywords)} wildflower keywords")
        log.info(f"{'='*60}")
        for wk in wildflower_keywords:
            log.info(f"  '{wk['keyword']}' (QS: {wk['quality_score']}, spend: ${wk['spend']})")
        step1_actions = create_wildflower_ad_group(client, customer_id, pasture_campaign_id, wildflower_keywords)
        all_actions.extend(step1_actions)
    else:
        log.info("No wildflower keywords found in Pasture campaign — skipping Step 1")

    time.sleep(1)

    # Step 2: Create intent-matched RSA ads for remaining pasture keywords
    log.info(f"\n{'='*60}")
    log.info("STEP 2: Creating intent-matched RSA ads")
    log.info(f"{'='*60}")
    step2_actions = create_pasture_intent_ads(client, customer_id, pasture_ad_groups, keywords)
    all_actions.extend(step2_actions)

    time.sleep(1)

    # Step 3: Add sitelinks + callouts to search campaigns missing them
    log.info(f"\n{'='*60}")
    log.info("STEP 3: Adding sitelinks + callouts")
    log.info(f"{'='*60}")
    search_campaigns = set()
    for ag in ad_groups.values():
        if "search" in ag["campaign"].lower() or "pasture" in ag["campaign"].lower():
            search_campaigns.add((ag["campaign_id"], ag["campaign"]))

    for camp_id, camp_name in search_campaigns:
        log.info(f"\nCampaign: {camp_name}")
        step3_actions = add_campaign_extensions(client, customer_id, camp_id, camp_name, extensions)
        all_actions.extend(step3_actions)

    # Summary
    log.info(f"\n{'='*60}")
    log.info("ACTIONS COMPLETED")
    log.info(f"{'='*60}")
    for i, action in enumerate(all_actions, 1):
        log.info(f"  {i}. {action}")

    # Save action log
    action_log_path = ROOT / "IS-Increase" / "action_log.json"
    action_log_path.parent.mkdir(exist_ok=True)
    action_log_path.write_text(json.dumps({
        "date": str(date.today()),
        "actions": all_actions,
        "wildflower_keywords_moved": [kw["keyword"] for kw in wildflower_keywords],
        "campaigns_updated": [c[1] for c in search_campaigns],
    }, indent=2))
    log.info(f"\nAction log saved: {action_log_path}")


if __name__ == "__main__":
    run()
