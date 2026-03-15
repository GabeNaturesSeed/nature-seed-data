#!/usr/bin/env python3
"""
Query Google Ads Change History for Nature's Seed account.
Shows all changes made to the account in March 2026.
"""

import os
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime

print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

try:
    from google.ads.googleads.client import GoogleAdsClient
    print("google-ads package loaded successfully")
except ImportError as e:
    print(f"ERROR: Cannot import google-ads: {e}")
    sys.exit(1)

# ── Load .env ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def load_env():
    env = {}
    env_file = PROJECT_ROOT / ".env"
    print(f"Looking for .env at: {env_file}")
    if env_file.exists():
        print(f".env file found ({env_file.stat().st_size} bytes)")
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip().strip("'\"")
        print(f"Loaded {len(env)} keys from .env: {list(env.keys())}")
    else:
        print(f".env not found at {env_file}, trying OS environment variables")

    # Fallback to OS environment variables
    for key in ["GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID",
                "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN",
                "GOOGLE_ADS_CUSTOMER_ID", "GOOGLE_ADS_LOGIN_CUSTOMER_ID"]:
        if key not in env and key in os.environ:
            env[key] = os.environ[key]
            print(f"  Got {key} from OS environment")

    return env


def main():
    try:
        env = load_env()

        required = ["GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID",
                     "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN"]
        missing = [k for k in required if not env.get(k)]
        if missing:
            print(f"ERROR: Missing required credentials: {missing}")
            print("Available keys:", list(env.keys()))
            # Print first 10 chars of each value to verify they're not empty
            for k, v in env.items():
                if "GOOGLE" in k:
                    print(f"  {k}: {'<empty>' if not v else v[:10] + '...'}")
            sys.exit(1)

        credentials = {
            "developer_token": env["GOOGLE_ADS_DEVELOPER_TOKEN"],
            "client_id": env["GOOGLE_ADS_CLIENT_ID"],
            "client_secret": env["GOOGLE_ADS_CLIENT_SECRET"],
            "refresh_token": env["GOOGLE_ADS_REFRESH_TOKEN"],
            "login_customer_id": env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "8386194588").replace("-", ""),
            "use_proto_plus": True,
        }

        print("Creating Google Ads client...")
        client = GoogleAdsClient.load_from_dict(credentials)
        customer_id = env.get("GOOGLE_ADS_CUSTOMER_ID", "5992879586").replace("-", "")
        ga_service = client.get_service("GoogleAdsService")
        print(f"Client created. Customer ID: {customer_id}")

        # ── Try change_event first ────────────────────────────────────────────
        print("=" * 80)
        print("QUERYING change_event (March 1-15, 2026)")
        print("=" * 80)

        query = """
            SELECT
                change_event.change_date_time,
                change_event.change_resource_type,
                change_event.change_resource_name,
                change_event.client_type,
                change_event.user_email,
                change_event.old_resource,
                change_event.new_resource,
                change_event.resource_change_operation,
                change_event.changed_fields
            FROM change_event
            WHERE change_event.change_date_time BETWEEN '2026-03-01 00:00:00' AND '2026-03-15 23:59:59'
            ORDER BY change_event.change_date_time DESC
            LIMIT 1000
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            count = 0
            for row in response:
                count += 1
                print(f"\n{'─' * 60}")
                print(f"Change #{count}")
                print(f"  Date/Time:          {row.change_event.change_date_time}")
                print(f"  Resource Type:      {row.change_event.change_resource_type.name}")
                print(f"  Resource Name:      {row.change_event.change_resource_name}")
                print(f"  Client Type:        {row.change_event.client_type.name}")
                print(f"  User Email:         {row.change_event.user_email}")
                print(f"  Operation:          {row.change_event.resource_change_operation.name}")
                print(f"  Changed Fields:     {row.change_event.changed_fields}")

                # Print old/new resource details
                old_res = row.change_event.old_resource
                new_res = row.change_event.new_resource
                if old_res:
                    print(f"  Old Resource:")
                    for field in ['campaign', 'campaign_budget', 'ad_group', 'ad_group_criterion',
                                  'campaign_criterion', 'ad_group_ad', 'asset', 'asset_group']:
                        attr = getattr(old_res, field, None)
                        if attr and str(attr):
                            try:
                                attr_str = str(attr)
                                if attr_str and len(attr_str) > 5:
                                    print(f"    {field}: {attr_str[:500]}")
                            except Exception:
                                pass
                if new_res:
                    print(f"  New Resource:")
                    for field in ['campaign', 'campaign_budget', 'ad_group', 'ad_group_criterion',
                                  'campaign_criterion', 'ad_group_ad', 'asset', 'asset_group']:
                        attr = getattr(new_res, field, None)
                        if attr and str(attr):
                            try:
                                attr_str = str(attr)
                                if attr_str and len(attr_str) > 5:
                                    print(f"    {field}: {attr_str[:500]}")
                            except Exception:
                                pass

            if count == 0:
                print("No change_event results found.")
            else:
                print(f"\n{'=' * 80}")
                print(f"Total change_event records: {count}")

        except Exception as e:
            print(f"change_event query failed: {e}")
            traceback.print_exc()
            print("\nFalling back to change_status...")

            # ── Fallback: change_status ───────────────────────────────────────
            print("\n" + "=" * 80)
            print("QUERYING change_status (March 1-15, 2026)")
            print("=" * 80)

            query2 = """
                SELECT
                    change_status.last_change_date_time,
                    change_status.resource_type,
                    change_status.resource_status,
                    change_status.campaign,
                    change_status.ad_group
                FROM change_status
                WHERE change_status.last_change_date_time BETWEEN '2026-03-01T00:00:00' AND '2026-03-15T23:59:59'
                ORDER BY change_status.last_change_date_time DESC
                LIMIT 500
            """

            try:
                response2 = ga_service.search(customer_id=customer_id, query=query2)
                count2 = 0
                for row in response2:
                    count2 += 1
                    print(f"\n{'─' * 60}")
                    print(f"Change #{count2}")
                    print(f"  Last Changed:   {row.change_status.last_change_date_time}")
                    print(f"  Resource Type:  {row.change_status.resource_type.name}")
                    print(f"  Status:         {row.change_status.resource_status.name if row.change_status.resource_status else 'N/A'}")
                    print(f"  Campaign:       {row.change_status.campaign}")
                    print(f"  Ad Group:       {row.change_status.ad_group}")

                if count2 == 0:
                    print("No change_status results found.")
                else:
                    print(f"\n{'=' * 80}")
                    print(f"Total change_status records: {count2}")

            except Exception as e2:
                print(f"change_status query also failed: {e2}")
                traceback.print_exc()

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
