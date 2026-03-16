"""
Keyword Expansion — Nature's Seed Google Ads
=============================================
Part 1: Update landing page URLs for drought/horse/texas keywords
Part 2: Create Phase 1 ad groups + keywords + RSAs (Lawn, Food Plot, Clover, Cover Crop)
Part 3: Create Phase 2 ad groups + keywords + RSAs (CA Wildflower, Lawn Alt, Sports Turf, Buffalograss)

All changes target the "Search | Animal Seed (Broad) | ROAS" campaign.
"""

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.api_core.exceptions import GoogleAPICallError
from google.protobuf import field_mask_pb2

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("keyword_expansion")

# ── Load .env ───────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = Path(__file__).resolve().parent / "keyword_expansion_results.json"


def load_env():
    env = {}
    env_file = PROJECT_ROOT / ".env"
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip().strip("'\"")
    return env


def build_client():
    env = load_env()
    credentials = {
        "developer_token": env["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": env["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": env["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": env["GOOGLE_ADS_REFRESH_TOKEN"],
        "login_customer_id": env["GOOGLE_ADS_LOGIN_CUSTOMER_ID"].replace("-", ""),
        "use_proto_plus": True,
    }
    client = GoogleAdsClient.load_from_dict(credentials)
    customer_id = env["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
    return client, customer_id


# ── Helpers ─────────────────────────────────────────────────────────────────

def validate_headline(text):
    if len(text) > 30:
        raise ValueError(f"Headline too long ({len(text)} chars): '{text}'")
    return text


def validate_description(text):
    if len(text) > 90:
        raise ValueError(f"Description too long ({len(text)} chars): '{text}'")
    return text


# ── PART 1: Update Landing Page URLs ───────────────────────────────────────

LANDING_PAGE_RULES = [
    {
        "name": "Drought keywords",
        "url": "https://naturesseed.com/product-category/pasture-seed/drought-tolerant-seed/",
        "patterns": ["drought", "dry climate", "arid", "dryland", "water-wise", "low water"],
        "campaign_filter": None,  # all campaigns
    },
    {
        "name": "Horse/equine keywords",
        "url": "https://naturesseed.com/product-category/pasture-grass-seed/horse-pastures-seed/",
        "patterns": ["horse", "equine", "forage"],
        "campaign_filter": "pasture",  # only pasture campaigns
    },
    {
        "name": "Texas/regional keywords",
        "url": "https://naturesseed.com/product-category/texas-native-grass-wildflower-seed/",
        "patterns": ["texas"],
        "campaign_filter": "pasture",  # only pasture campaigns
    },
]


def part1_update_landing_pages(client, customer_id):
    """Find and update keyword final URLs based on landing page rules."""
    log.info("=" * 60)
    log.info("PART 1: Updating Landing Page URLs")
    log.info("=" * 60)

    ga_service = client.get_service("GoogleAdsService")
    criterion_service = client.get_service("AdGroupCriterionService")
    results = []

    for rule in LANDING_PAGE_RULES:
        log.info(f"\n--- {rule['name']} ---")
        log.info(f"Target URL: {rule['url']}")

        # Query all enabled keywords
        query = """
            SELECT
                ad_group_criterion.resource_name,
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.final_urls,
                ad_group.id,
                ad_group.name,
                campaign.id,
                campaign.name
            FROM keyword_view
            WHERE ad_group_criterion.status = 'ENABLED'
                AND campaign.status = 'ENABLED'
        """
        response = ga_service.search(customer_id=customer_id, query=query)

        # Collect matching keywords
        matches = []
        seen = set()
        for row in response:
            kw_text = row.ad_group_criterion.keyword.text.lower()
            resource_name = row.ad_group_criterion.resource_name
            campaign_name = row.campaign.name.lower()

            # Skip duplicates (keyword_view can return multiple rows per keyword due to date segments)
            if resource_name in seen:
                continue
            seen.add(resource_name)

            # Apply campaign filter if specified
            if rule["campaign_filter"] and rule["campaign_filter"].lower() not in campaign_name:
                continue

            # Check if keyword matches any pattern
            if any(p in kw_text for p in rule["patterns"]):
                # Check if URL already correct
                current_urls = list(row.ad_group_criterion.final_urls)
                if current_urls and current_urls[0] == rule["url"]:
                    continue  # Already correct

                matches.append({
                    "resource_name": resource_name,
                    "keyword": row.ad_group_criterion.keyword.text,
                    "campaign": row.campaign.name,
                    "ad_group": row.ad_group.name,
                    "current_urls": current_urls,
                })

        log.info(f"Found {len(matches)} keywords to update")

        if not matches:
            results.append({"rule": rule["name"], "updated": 0, "keywords": []})
            continue

        # Update final URLs in batches
        operations = []
        for m in matches:
            op = client.get_type("AdGroupCriterionOperation")
            criterion = op.update
            criterion.resource_name = m["resource_name"]
            criterion.final_urls.append(rule["url"])
            op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["final_urls"]))
            operations.append(op)

        try:
            # Send in batches of 50
            updated = 0
            for i in range(0, len(operations), 50):
                batch = operations[i:i+50]
                criterion_service.mutate_ad_group_criteria(
                    customer_id=customer_id,
                    operations=batch,
                )
                updated += len(batch)
                log.info(f"  Updated batch {i//50 + 1}: {len(batch)} keywords")
                time.sleep(0.5)

            results.append({
                "rule": rule["name"],
                "updated": updated,
                "keywords": [m["keyword"] for m in matches],
            })
            log.info(f"SUCCESS: Updated {updated} keywords for {rule['name']}")

        except GoogleAPICallError as e:
            log.error(f"FAILED: {rule['name']}: {e}")
            results.append({
                "rule": rule["name"],
                "updated": 0,
                "error": str(e),
                "keywords": [m["keyword"] for m in matches],
            })

    return results


# ── PART 2 & 3: Create Ad Groups + Keywords + RSAs ─────────────────────────

AD_GROUPS = [
    # Phase 1
    {
        "name": "Lawn Seed",
        "phase": 1,
        "keywords": [
            "lawn grass seed", "best lawn seed", "lawn seed mix",
            "cool season lawn seed", "warm season lawn seed",
            "shade tolerant lawn seed", "sun lawn grass seed",
            "kentucky bluegrass seed", "perennial ryegrass seed",
            "tall fescue lawn seed",
        ],
        "url": "https://naturesseed.com/product-category/products-grass-seed/",
        "headlines": [
            "Premium Lawn Grass Seed", "Best Lawn Seed Mixes",
            "Kentucky Bluegrass Seed", "Shop Lawn Seed Online",
            "Cool Season Lawn Seed", "Warm Season Lawn Seed",
            "Shade Tolerant Lawn Seed", "USDA Tested Lawn Seed",
            "Free Ship on Lawn Seed", "Expert Lawn Seed Blends",
        ],
        "descriptions": [
            "Premium lawn grass seed mixes for every climate. USDA-tested varieties. Free shipping.",
            "Shop cool and warm season lawn seed. Kentucky Bluegrass, Fescue, Ryegrass and more.",
            "Beautiful lawn starts with quality seed. Expert growing guides included with every order.",
        ],
    },
    {
        "name": "Food Plot Seed",
        "phase": 1,
        "keywords": [
            "food plot seed", "deer food plot seed", "wildlife food plot mix",
            "turkey food plot seed", "best food plot seed", "food plot seed mix",
            "whitetail food plot", "upland game seed mix", "deer attractant seed",
        ],
        "url": "https://naturesseed.com/product-category/specialty-seed/food-plot-seed/",
        "headlines": [
            "Deer Food Plot Seed Mix", "Wildlife Food Plot Seed",
            "Best Food Plot Seed", "Shop Food Plot Mixes",
            "Turkey Food Plot Seed", "Whitetail Deer Seed Mix",
            "Upland Game Seed Blend", "Food Plot Seed Free Ship",
            "Premium Wildlife Seed", "Expert Food Plot Blends",
        ],
        "descriptions": [
            "Deer and wildlife food plot seed mixes. Attract game with proven blends. Free shipping.",
            "Premium food plot seed for whitetail, turkey and upland game. Growing guides included.",
            "Plant the best food plots this season. USDA-tested wildlife seed mixes from Nature's Seed.",
        ],
    },
    {
        "name": "Clover Seed",
        "phase": 1,
        "keywords": [
            "clover seed", "white clover seed", "red clover seed",
            "crimson clover seed", "dutch white clover", "micro clover seed",
            "clover cover crop", "clover lawn seed", "alsike clover seed",
        ],
        "url": "https://naturesseed.com/product-category/clover-seed/",
        "headlines": [
            "Premium Clover Seed", "White Dutch Clover Seed",
            "Red Clover Seed", "Micro Clover Lawn Seed",
            "Shop Clover Seed Online", "Crimson Clover Seed",
            "Clover Cover Crop Seed", "USDA Tested Clover Seed",
            "Free Ship on Clover", "Alsike Clover Seed",
        ],
        "descriptions": [
            "Premium clover seed varieties. White Dutch, Red, Crimson and Micro Clover. Free shipping.",
            "Clover seed for lawns, cover crops and pastures. USDA-tested with expert growing guides.",
            "Build a beautiful clover lawn or boost your pasture. Shop Nature's Seed clover blends.",
        ],
    },
    {
        "name": "Cover Crop Seed",
        "phase": 1,
        "keywords": [
            "cover crop seed", "cover crop seed mix", "winter cover crop",
            "nitrogen fixing cover crop", "biofumigant seed blend",
            "green manure seed", "soil builder seed mix",
        ],
        "url": "https://naturesseed.com/product-category/specialty-seed/cover-crop-seed/",
        "headlines": [
            "Cover Crop Seed Mixes", "Winter Cover Crop Seed",
            "Nitrogen Fixing Seed", "Shop Cover Crop Seed",
            "Green Manure Seed Mix", "Soil Builder Seed Blend",
            "Premium Cover Crop Seed", "USDA Tested Cover Crop",
            "Free Ship Cover Crop", "Biofumigant Seed Blend",
        ],
        "descriptions": [
            "Cover crop seed mixes for soil health. Nitrogen fixers and biofumigants. Free shipping.",
            "Improve your soil with premium cover crop seed. Winter rye, clover and custom blends.",
            "Build soil fertility naturally. USDA-tested cover crop seed mixes from Nature's Seed.",
        ],
    },
    # Phase 2
    {
        "name": "California Wildflower Seed",
        "phase": 2,
        "keywords": [
            "california wildflower seed", "california native wildflower",
            "california poppy seed mix", "native california seed",
            "california wildflower mix",
        ],
        "url": "https://naturesseed.com/product-category/california-collection/",
        "headlines": [
            "CA Wildflower Seed Mixes", "California Native Seed",
            "California Poppy Seed Mix", "Shop CA Wildflowers",
            "Native CA Wildflower Seed", "California Seed Blends",
            "CA Native Plant Seed", "USDA Tested CA Seed",
            "Free Ship CA Wildflower", "CA Habitat Seed Mix",
        ],
        "descriptions": [
            "California native wildflower seed mixes. Poppies, lupines and more. Free shipping.",
            "Create a California wildflower meadow. Native species adapted to CA climates and soils.",
            "Shop California Collection seed mixes. USDA-tested natives for habitat and beauty.",
        ],
    },
    {
        "name": "Lawn Alternative Seed",
        "phase": 2,
        "keywords": [
            "no mow lawn seed", "low maintenance lawn", "micro clover lawn",
            "meadow lawn seed", "lawn alternative seed", "eco lawn seed",
        ],
        "url": "https://naturesseed.com/product-category/products-grass-seed/lawn-alternatives/",
        "headlines": [
            "No-Mow Lawn Seed Mix", "Low Maintenance Lawn",
            "Micro Clover Lawn Seed", "Meadow Lawn Blend",
            "Eco-Friendly Lawn Seed", "Shop Lawn Alternatives",
            "Water-Wise Lawn Seed", "Clover Lawn Seed Mix",
            "USDA Tested Eco Lawn", "Free Ship Lawn Seed",
        ],
        "descriptions": [
            "No-mow and low-maintenance lawn seed alternatives. Clover, meadow and eco-friendly blends.",
            "Replace your traditional lawn with a beautiful low-care alternative. Free shipping.",
            "Micro clover lawns and meadow blends that need less water and zero mowing. Shop now.",
        ],
    },
    {
        "name": "Sports Turf Seed",
        "phase": 2,
        "keywords": [
            "sports turf seed", "high traffic grass seed", "playground grass seed",
            "athletic field seed", "durable lawn seed", "heavy use grass seed",
        ],
        "url": "https://naturesseed.com/product-category/products-grass-seed/sports-turf-high-traffic/",
        "headlines": [
            "Sports Turf Grass Seed", "High Traffic Lawn Seed",
            "Playground Grass Seed", "Athletic Field Seed",
            "Durable Lawn Seed Mix", "Heavy Use Grass Seed",
            "Shop Sports Turf Seed", "Fast Recovery Turf Seed",
            "USDA Tested Turf Seed", "Free Ship Sports Turf",
        ],
        "descriptions": [
            "Sports turf and high-traffic grass seed mixes. Built for heavy use and fast recovery.",
            "Premium grass seed for playgrounds, athletic fields and high-traffic lawns. Free shipping.",
            "Durable turf seed that stands up to heavy foot traffic. USDA-tested blends from experts.",
        ],
    },
    {
        "name": "Buffalograss Seed",
        "phase": 2,
        "keywords": [
            "buffalograss seed", "buffalo grass lawn seed",
            "drought tolerant lawn seed", "water wise lawn seed",
            "native lawn grass seed", "low water lawn seed",
        ],
        "url": "https://naturesseed.com/product-category/products-grass-seed/",
        "headlines": [
            "Buffalograss Lawn Seed", "Drought Tolerant Lawn",
            "Water-Wise Lawn Seed", "Native Lawn Grass Seed",
            "Low Water Lawn Seed", "Shop Buffalograss Seed",
            "Save Water Lawn Seed", "Hardy Drought Lawn Mix",
            "USDA Tested Buffalo", "Free Ship Lawn Seed",
        ],
        "descriptions": [
            "Buffalograss and drought-tolerant lawn seed. Uses 75% less water than traditional lawns.",
            "Native buffalograss seed for dry climates. Low maintenance and water-wise. Free shipping.",
            "Build a beautiful drought-proof lawn with buffalograss. USDA-tested from Nature's Seed.",
        ],
    },
]


def find_campaign(client, customer_id, campaign_name_search):
    """Find campaign by name (partial match)."""
    ga_service = client.get_service("GoogleAdsService")
    query = """
        SELECT campaign.id, campaign.name, campaign.resource_name
        FROM campaign
        WHERE campaign.status = 'ENABLED'
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    for row in response:
        if campaign_name_search.lower() in row.campaign.name.lower():
            return {
                "id": row.campaign.id,
                "name": row.campaign.name,
                "resource_name": row.campaign.resource_name,
            }
    return None


def create_ad_group(client, customer_id, campaign_resource_name, ad_group_name):
    """Create an ad group and return its resource name."""
    service = client.get_service("AdGroupService")
    operation = client.get_type("AdGroupOperation")

    ad_group = operation.create
    ad_group.name = ad_group_name
    ad_group.campaign = campaign_resource_name
    ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
    ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD

    response = service.mutate_ad_groups(
        customer_id=customer_id,
        operations=[operation],
    )
    resource_name = response.results[0].resource_name
    log.info(f"  Created ad group: {ad_group_name} -> {resource_name}")
    return resource_name


def add_keywords_to_ad_group(client, customer_id, ad_group_resource_name, keywords, final_url):
    """Add BROAD match keywords with final URL to an ad group."""
    service = client.get_service("AdGroupCriterionService")
    operations = []

    for kw in keywords:
        op = client.get_type("AdGroupCriterionOperation")
        criterion = op.create
        criterion.ad_group = ad_group_resource_name
        criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
        criterion.keyword.text = kw
        criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
        criterion.final_urls.append(final_url)
        operations.append(op)

    response = service.mutate_ad_group_criteria(
        customer_id=customer_id,
        operations=operations,
    )
    log.info(f"  Added {len(response.results)} keywords")
    return len(response.results)


def create_rsa(client, customer_id, ad_group_resource_name, headlines, descriptions, final_url):
    """Create a Responsive Search Ad in the ad group."""
    service = client.get_service("AdGroupAdService")
    operation = client.get_type("AdGroupAdOperation")

    ad_group_ad = operation.create
    ad_group_ad.ad_group = ad_group_resource_name
    ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

    ad = ad_group_ad.ad
    ad.final_urls.append(final_url)

    # Add headlines
    for h_text in headlines:
        validate_headline(h_text)
        asset = client.get_type("AdTextAsset")
        asset.text = h_text
        ad.responsive_search_ad.headlines.append(asset)

    # Add descriptions
    for d_text in descriptions:
        validate_description(d_text)
        asset = client.get_type("AdTextAsset")
        asset.text = d_text
        ad.responsive_search_ad.descriptions.append(asset)

    response = service.mutate_ad_group_ads(
        customer_id=customer_id,
        operations=[operation],
    )
    resource_name = response.results[0].resource_name
    log.info(f"  Created RSA -> {resource_name}")
    return resource_name


def parts_2_and_3(client, customer_id):
    """Create Phase 1 and Phase 2 ad groups with keywords and RSAs."""
    log.info("=" * 60)
    log.info("PARTS 2 & 3: Creating Ad Groups + Keywords + RSAs")
    log.info("=" * 60)

    # Find the target campaign
    campaign = find_campaign(client, customer_id, "Search | Animal Seed (Broad) | ROAS")
    if not campaign:
        log.error("Campaign 'Search | Animal Seed (Broad) | ROAS' not found!")
        return [{"error": "Campaign not found"}]

    log.info(f"Target campaign: {campaign['name']} (ID: {campaign['id']})")
    results = []

    for ag_spec in AD_GROUPS:
        log.info(f"\n--- Phase {ag_spec['phase']}: {ag_spec['name']} ---")
        ag_result = {
            "ad_group_name": ag_spec["name"],
            "phase": ag_spec["phase"],
            "campaign": campaign["name"],
        }

        try:
            # 1. Create ad group
            ag_resource = create_ad_group(
                client, customer_id, campaign["resource_name"], ag_spec["name"]
            )
            ag_result["ad_group_resource"] = ag_resource
            time.sleep(0.5)

            # 2. Add keywords
            kw_count = add_keywords_to_ad_group(
                client, customer_id, ag_resource, ag_spec["keywords"], ag_spec["url"]
            )
            ag_result["keywords_added"] = kw_count
            ag_result["keyword_list"] = ag_spec["keywords"]
            time.sleep(0.5)

            # 3. Create RSA
            rsa_resource = create_rsa(
                client, customer_id, ag_resource,
                ag_spec["headlines"], ag_spec["descriptions"], ag_spec["url"]
            )
            ag_result["rsa_resource"] = rsa_resource
            ag_result["success"] = True
            time.sleep(0.5)

        except GoogleAPICallError as e:
            log.error(f"FAILED creating {ag_spec['name']}: {e}")
            ag_result["success"] = False
            ag_result["error"] = str(e)
        except Exception as e:
            log.error(f"UNEXPECTED ERROR for {ag_spec['name']}: {e}")
            ag_result["success"] = False
            ag_result["error"] = str(e)

        results.append(ag_result)

    return results


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    log.info("Starting Keyword Expansion script")
    client, customer_id = build_client()

    all_results = {
        "timestamp": datetime.now().isoformat(),
        "customer_id": customer_id,
    }

    # Part 1: Update landing page URLs
    try:
        part1_results = part1_update_landing_pages(client, customer_id)
        all_results["part1_landing_pages"] = part1_results
    except Exception as e:
        log.error(f"Part 1 failed: {e}")
        all_results["part1_landing_pages"] = {"error": str(e)}

    # Parts 2 & 3: Create ad groups + keywords + RSAs
    try:
        parts23_results = parts_2_and_3(client, customer_id)
        all_results["parts23_ad_groups"] = parts23_results
    except Exception as e:
        log.error(f"Parts 2/3 failed: {e}")
        all_results["parts23_ad_groups"] = {"error": str(e)}

    # Save results
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    log.info(f"\nResults saved to {RESULTS_PATH}")

    # Summary
    log.info("\n" + "=" * 60)
    log.info("SUMMARY")
    log.info("=" * 60)

    if isinstance(all_results.get("part1_landing_pages"), list):
        total_updated = sum(r.get("updated", 0) for r in all_results["part1_landing_pages"])
        log.info(f"Part 1: Updated {total_updated} keyword landing pages")
        for r in all_results["part1_landing_pages"]:
            status = f"{r.get('updated', 0)} updated" if "error" not in r else f"ERROR: {r['error']}"
            log.info(f"  {r['rule']}: {status}")

    if isinstance(all_results.get("parts23_ad_groups"), list):
        succeeded = sum(1 for r in all_results["parts23_ad_groups"] if r.get("success"))
        failed = sum(1 for r in all_results["parts23_ad_groups"] if not r.get("success"))
        log.info(f"Parts 2/3: {succeeded} ad groups created, {failed} failed")
        for r in all_results["parts23_ad_groups"]:
            status = "OK" if r.get("success") else f"FAILED: {r.get('error', 'unknown')}"
            log.info(f"  Phase {r.get('phase')}: {r['ad_group_name']}: {status}")


if __name__ == "__main__":
    main()
