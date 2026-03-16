#!/usr/bin/env python3
"""
IS Increase — Create RSA ads (fixed character limits)
======================================================
Google Ads RSA limits: Headlines ≤ 30 chars, Descriptions ≤ 90 chars
"""

import json
import logging
from datetime import date
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("rsa_fix")

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


def create_rsa(client, customer_id, ad_service, ag_resource, headlines, descriptions, url, label):
    """Create an RSA ad with validation."""
    # Validate lengths
    for i, h in enumerate(headlines):
        if len(h) > 30:
            log.warning(f"  Headline too long ({len(h)}): '{h}' — truncating")
            headlines[i] = h[:30]
    for i, d in enumerate(descriptions):
        if len(d) > 90:
            log.warning(f"  Description too long ({len(d)}): '{d[:50]}...' — truncating")
            descriptions[i] = d[:90]

    ad_op = client.get_type("AdGroupAdOperation")
    ad_group_ad = ad_op.create
    ad_group_ad.ad_group = ag_resource
    ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

    ad = ad_group_ad.ad
    ad.final_urls.append(url)

    for h in headlines:
        asset = client.get_type("AdTextAsset")
        asset.text = h
        ad.responsive_search_ad.headlines.append(asset)

    for d in descriptions:
        asset = client.get_type("AdTextAsset")
        asset.text = d
        ad.responsive_search_ad.descriptions.append(asset)

    try:
        resp = ad_service.mutate_ad_group_ads(customer_id=customer_id, operations=[ad_op])
        log.info(f"  Created RSA [{label}]: {resp.results[0].resource_name}")
        return True
    except GoogleAdsException as e:
        err = e.failure.errors[0].message if e.failure.errors else str(e)
        log.error(f"  FAILED RSA [{label}]: {err}")
        return False


def run():
    client, customer_id = _gads_client()
    service = client.get_service("GoogleAdsService")
    ad_service = client.get_service("AdGroupAdService")

    all_actions = []

    # ── Find ad groups ───────────────────────────────────────────────────────
    ag_query = """
        SELECT campaign.id, campaign.name, ad_group.id, ad_group.name
        FROM ad_group
        WHERE campaign.status = 'ENABLED' AND ad_group.status = 'ENABLED'
    """
    ag_resp = service.search(customer_id=customer_id, query=ag_query)
    ad_groups = {}
    for row in ag_resp:
        ad_groups[str(row.ad_group.id)] = {
            "name": row.ad_group.name,
            "campaign": row.campaign.name,
            "campaign_id": str(row.campaign.id),
        }

    # ── Find which ad groups have which keywords ─────────────────────────────
    kw_query = """
        SELECT ad_group.id, ad_group_criterion.keyword.text
        FROM keyword_view
        WHERE campaign.status = 'ENABLED' AND ad_group.status = 'ENABLED'
          AND ad_group_criterion.status = 'ENABLED'
          AND segments.date DURING LAST_30_DAYS
    """
    kw_resp = service.search(customer_id=customer_id, query=kw_query)
    ag_keywords = {}
    seen = set()
    for row in kw_resp:
        ag_id = str(row.ad_group.id)
        kw = row.ad_group_criterion.keyword.text
        key = f"{ag_id}_{kw}"
        if key not in seen:
            seen.add(key)
            ag_keywords.setdefault(ag_id, []).append(kw)

    # ── RSA definitions (all within character limits) ────────────────────────
    # Headlines: max 30 chars | Descriptions: max 90 chars

    rsa_configs = {
        # Wildflower ad group (ID from previous run)
        "wildflower": {
            "match_ag_name": "Wildflower Seeds",
            "url": "https://naturesseed.com/product-category/wildflower-seed/",
            "headlines": [                          # ≤30 chars each
                "Native Wildflower Seeds",          # 23
                "Wildflower Seed Mixes",            # 21
                "California Wildflower Seed",       # 26
                "Shop Wildflower Seeds",            # 21
                "Native Seed Blends",               # 18
                "Wildflower Seed Free Ship",        # 25
                "Beautiful Wildflower Mix",          # 24
                "Easy-Grow Wildflower Seed",        # 25
                "USDA Tested Wildflower",           # 22
                "Browse Wildflower Mixes",          # 23
            ],
            "descriptions": [                       # ≤90 chars each
                "Native wildflower seed mixes for every region. USDA-tested varieties. Free shipping.",  # 82
                "Create a wildflower meadow with curated seed blends. Native species for pollinators.",  # 84
                "California natives, Texas mixes & more. Expert growing guides included with every order.",  # 89 — close!
                "High-purity wildflower seeds with proven germination. Perfect for meadows & gardens.",  # 86
            ],
        },
        # Horse intent for Pasture ad groups
        "horse": {
            "match_keywords": ["horse", "equine", "forage"],
            "match_campaign": "pasture",
            "url": "https://naturesseed.com/product-category/pasture-grass-seed/",
            "headlines": [
                "Horse Pasture Grass Seed",         # 24
                "Equine-Safe Pasture Seed",         # 24
                "Premium Horse Forage Seed",        # 25
                "Pasture Seed for Horses",          # 23
                "Horse-Safe Grass Seed Mix",        # 25
                "Shop Equine Pasture Seed",         # 24
                "Forage Grass Seed Blends",         # 24
                "Best Horse Pasture Seed",          # 23
                "USDA Tested Forage Seed",          # 23
                "Fast-Grow Horse Pasture",          # 23
            ],
            "descriptions": [
                "Horse-safe pasture grass seed mixes. Nutrient-rich forage. USDA-tested. Free shipping.",  # 85
                "Build a durable horse pasture with expert seed blends. Heavy grazing & fast recovery.",  # 84
                "Trusted by ranchers. High-quality equine pasture seed. Shop Nature's Seed today.",  # 82
            ],
        },
        # Drought intent
        "drought": {
            "match_keywords": ["drought", "dry", "arid"],
            "match_campaign": "pasture",
            "url": "https://naturesseed.com/product-category/pasture-grass-seed/",
            "headlines": [
                "Drought-Tolerant Pasture",         # 24
                "Dry Climate Pasture Grass",        # 25
                "Water-Wise Pasture Seed",          # 23
                "Heat & Drought Pasture",           # 22
                "Low-Water Pasture Grass",          # 23
                "Drought-Resistant Forage",         # 24
                "Arid Climate Grass Seed",          # 23
                "Save Water - Pasture Seed",        # 25
                "Hardy Drought Pasture Mix",        # 25
                "Thrives in Dry Conditions",        # 25
            ],
            "descriptions": [
                "Drought-tolerant pasture seed for dry climates. Deep-rooting varieties. Free shipping.",  # 86
                "Premium drought-resistant pasture grass seed. USDA-tested for arid conditions.",  # 82
                "Build a resilient low-water pasture. Drought-hardy seed mixes for tough conditions.",  # 86
            ],
        },
        # Regional intent
        "regional": {
            "match_keywords": ["texas", "california", "western", "southern"],
            "match_campaign": "pasture",
            "url": "https://naturesseed.com/product-category/pasture-grass-seed/",
            "headlines": [
                "Regional Pasture Grass Seed",      # 27
                "Texas Pasture Seed Mixes",         # 24
                "Western Pasture Grass Seed",       # 26
                "Climate-Adapted Pasture",          # 23
                "Local Pasture Seed Blends",        # 25
                "State-Specific Pasture",           # 22
                "Native Pasture Grass Seed",        # 25
                "Best Regional Pasture Mix",        # 25
                "Shop by Your Climate Zone",        # 25
                "Expert Regional Seed Mix",         # 24
            ],
            "descriptions": [
                "Pasture seed mixes for your climate zone. Texas, California, Western & more.",  # 79
                "Region-specific pasture seed with proven performance. USDA-tested. Free shipping.",  # 85
                "Get the right pasture seed for your state. Climate-adapted blends from experts.",  # 84
            ],
        },
    }

    # ── Create RSAs ──────────────────────────────────────────────────────────
    for config_name, cfg in rsa_configs.items():
        target_ag_ids = []

        if "match_ag_name" in cfg:
            # Direct name match
            for ag_id, ag_data in ad_groups.items():
                if cfg["match_ag_name"].lower() in ag_data["name"].lower():
                    target_ag_ids.append(ag_id)
        elif "match_keywords" in cfg:
            # Find ad groups with matching keywords in the right campaign
            for ag_id, ag_data in ad_groups.items():
                if cfg.get("match_campaign", "").lower() not in ag_data["campaign"].lower():
                    continue
                kws = ag_keywords.get(ag_id, [])
                if any(any(t in kw.lower() for t in cfg["match_keywords"]) for kw in kws):
                    target_ag_ids.append(ag_id)

        for ag_id in target_ag_ids:
            ag_data = ad_groups[ag_id]
            label = f"{config_name} in '{ag_data['name']}' ({ag_data['campaign']})"
            log.info(f"\nCreating RSA: {label}")
            ag_resource = f"customers/{customer_id}/adGroups/{ag_id}"

            ok = create_rsa(client, customer_id, ad_service, ag_resource,
                           cfg["headlines"][:], cfg["descriptions"][:], cfg["url"], label)
            if ok:
                all_actions.append(f"Created {config_name}-intent RSA in '{ag_data['name']}'")
            else:
                all_actions.append(f"FAILED: {label}")

    # ── Summary ──────────────────────────────────────────────────────────────
    log.info(f"\n{'='*60}")
    log.info("RSA CREATION COMPLETE")
    log.info(f"{'='*60}")
    for i, a in enumerate(all_actions, 1):
        log.info(f"  {i}. {a}")

    # Update action log
    action_log_path = ROOT / "IS-Increase" / "action_log.json"
    existing = json.loads(action_log_path.read_text()) if action_log_path.exists() else {"actions": []}
    existing["actions"].extend(all_actions)
    existing["rsa_date"] = str(date.today())
    action_log_path.write_text(json.dumps(existing, indent=2))


if __name__ == "__main__":
    run()
