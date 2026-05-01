#!/usr/bin/env python3
"""
Nature's Seed — Google Customer Match Audience Sync

Reads customer data from Supabase, segments into audience lists,
hashes PII (SHA-256), and uploads to Google Ads via OfflineUserDataJobService.

Runs weekly (Sunday night) via GitHub Actions.

Usage:
  python3 customer_match_sync.py          # Sync all lists
  python3 customer_match_sync.py dry-run  # Show counts without uploading
"""

import hashlib
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path

import requests
from google.ads.googleads.client import GoogleAdsClient

# ══════════════════════════════════════════════════════════════
# ENV + CONFIG
# ══════════════════════════════════════════════════════════════

env_path = Path(__file__).resolve().parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

SUPABASE_URL = env_vars.get("SUPABASE_URL", "")
SUPABASE_KEY = env_vars.get("SUPABASE_SECRET_API_KEY", "")

GOOGLE_ADS_CONFIG = {
    "developer_token": env_vars["GOOGLE_ADS_DEVELOPER_TOKEN"],
    "client_id": env_vars["GOOGLE_ADS_CLIENT_ID"],
    "client_secret": env_vars["GOOGLE_ADS_CLIENT_SECRET"],
    "refresh_token": env_vars["GOOGLE_ADS_REFRESH_TOKEN"],
    "use_proto_plus": True,
}
login_cid = env_vars.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
if login_cid:
    GOOGLE_ADS_CONFIG["login_customer_id"] = login_cid
GOOGLE_ADS_CUSTOMER_ID = env_vars["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")

# ══════════════════════════════════════════════════════════════
# AUDIENCE DEFINITIONS
# ══════════════════════════════════════════════════════════════

# Each audience: name, description, filter function
# Filter receives a customer dict and today's date, returns bool
def _has_revenue(c):
    """True if customer has actual purchase revenue (not a $0 backfill record)."""
    return float(c.get("total_revenue", 0)) > 0


AUDIENCES = [
    {
        "name": "NS - All Buyers",
        "description": "All registered customers (lookalike seed + bid adjustments)",
        "filter": lambda c, today: True,  # All records in customers table are real WC buyers
    },
    {
        "name": "NS - High Value Buyers",
        "description": "Top 20% customers by total revenue (premium lookalikes)",
        "filter": "high_value",  # Special handling — needs percentile calc
    },
    {
        "name": "NS - Spring 2025 Buyers",
        "description": "Customers whose last purchase was Mar-Jun 2025 (seasonal reactivation)",
        "filter": lambda c, today: (
            c.get("last_order_date") and
            "2025-03" <= c["last_order_date"][:7] <= "2025-06"
        ),
    },
    {
        "name": "NS - Recent Buyers 90d",
        "description": "Purchased in last 90 days — exclude from acquisition",
        "filter": lambda c, today: (
            c.get("last_order_date") and
            c["last_order_date"] >= (today - timedelta(days=90)).isoformat()
        ),
    },
    {
        "name": "NS - Lapsed Buyers 180d",
        "description": "No purchase in 180+ days — win-back targeting",
        "filter": lambda c, today: (
            c.get("last_order_date") and
            c["last_order_date"] < (today - timedelta(days=180)).isoformat()
        ),
    },
]


# ══════════════════════════════════════════════════════════════
# SUPABASE
# ══════════════════════════════════════════════════════════════

def fetch_customers():
    """Fetch all customers with emails from Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/customers"
    headers = {"apikey": SUPABASE_KEY}
    params = {
        "select": "customer_id,email,total_orders,total_revenue,first_order_date,last_order_date",
        "email": "neq.",  # Exclude empty emails
        "order": "total_revenue.desc",
    }
    all_customers = []
    offset = 0
    page_size = 1000

    while True:
        params["offset"] = offset
        params["limit"] = page_size
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_customers.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    print(f"[Supabase] Fetched {len(all_customers)} customers with emails")
    return all_customers


# ══════════════════════════════════════════════════════════════
# HASHING
# ══════════════════════════════════════════════════════════════

def hash_email(email):
    """Normalize and SHA-256 hash an email per Google's spec.
    - Lowercase
    - Strip whitespace
    - SHA-256 hex digest
    """
    normalized = email.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════
# SEGMENTATION
# ══════════════════════════════════════════════════════════════

def segment_customers(customers, today):
    """Apply audience filters and return dict of {name: [hashed_emails]}."""
    # Pre-compute high-value threshold (top 20% by revenue, excluding $0 records)
    revenues = sorted(
        [float(c.get("total_revenue", 0)) for c in customers
         if float(c.get("total_revenue", 0)) > 0],
        reverse=True,
    )
    if revenues:
        cutoff_idx = max(1, len(revenues) // 5)  # Top 20%
        high_value_threshold = revenues[cutoff_idx - 1]
        print(f"  [High Value threshold] Top 20% = ${high_value_threshold:.2f}+ "
              f"({cutoff_idx} of {len(revenues)} paying customers)")
    else:
        high_value_threshold = float("inf")

    segments = {}
    for audience in AUDIENCES:
        name = audience["name"]
        matched_emails = set()

        for customer in customers:
            email = customer.get("email", "")
            if not email or "@" not in email:
                continue

            if audience["filter"] == "high_value":
                if float(customer.get("total_revenue", 0)) >= high_value_threshold:
                    matched_emails.add(hash_email(email))
            else:
                if audience["filter"](customer, today):
                    matched_emails.add(hash_email(email))

        segments[name] = {
            "hashed_emails": list(matched_emails),
            "description": audience["description"],
            "count": len(matched_emails),
        }
        print(f"  [{name}] {len(matched_emails)} emails")

    return segments


# ══════════════════════════════════════════════════════════════
# GOOGLE ADS — USER LIST MANAGEMENT
# ══════════════════════════════════════════════════════════════

def get_or_create_user_list(client, customer_id, list_name, description):
    """Find an existing user list by name, or create a new one.
    Returns the user list resource name.
    """
    ga_service = client.get_service("GoogleAdsService")

    # Search for existing list
    query = f"""
        SELECT user_list.resource_name, user_list.name, user_list.size_for_search
        FROM user_list
        WHERE user_list.name = '{list_name}'
          AND user_list.type = 'CRM_BASED'
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    for row in response:
        print(f"    Found existing list: {row.user_list.resource_name} "
              f"(search size: {row.user_list.size_for_search})")
        return row.user_list.resource_name

    # Create new list
    user_list_service = client.get_service("UserListService")
    user_list_op = client.get_type("UserListOperation")
    user_list = user_list_op.create
    user_list.name = list_name
    user_list.description = description
    user_list.membership_life_span = 90  # Days before auto-removal
    user_list.crm_based_user_list.upload_key_type = client.enums.CustomerMatchUploadKeyTypeEnum.CONTACT_INFO

    response = user_list_service.mutate_user_lists(
        customer_id=customer_id,
        operations=[user_list_op],
    )
    resource_name = response.results[0].resource_name
    print(f"    Created new list: {resource_name}")
    return resource_name


def upload_to_user_list(client, customer_id, user_list_resource_name, hashed_emails):
    """Upload hashed emails to a Customer Match user list via OfflineUserDataJobService.

    Uses create-add-run pattern:
    1. Create an offline user data job
    2. Add user data operations (batched)
    3. Run the job
    """
    offline_job_service = client.get_service("OfflineUserDataJobService")

    # 1. Create the job
    offline_job = client.get_type("OfflineUserDataJob")
    offline_job.type_ = client.enums.OfflineUserDataJobTypeEnum.CUSTOMER_MATCH_USER_LIST
    offline_job.customer_match_user_list_metadata.user_list = user_list_resource_name
    # Replace all existing members with fresh data
    offline_job.customer_match_user_list_metadata.consent.ad_user_data = (
        client.enums.ConsentStatusEnum.GRANTED
    )
    offline_job.customer_match_user_list_metadata.consent.ad_personalization = (
        client.enums.ConsentStatusEnum.GRANTED
    )

    create_response = offline_job_service.create_offline_user_data_job(
        customer_id=customer_id,
        job=offline_job,
    )
    job_resource_name = create_response.resource_name
    print(f"    Created job: {job_resource_name}")

    # 2. Add user data in batches of 10,000 (API limit per request)
    BATCH_SIZE = 10_000
    for i in range(0, len(hashed_emails), BATCH_SIZE):
        batch = hashed_emails[i:i + BATCH_SIZE]
        operations = []
        for email_hash in batch:
            op = client.get_type("OfflineUserDataJobOperation")
            user_identifier = client.get_type("UserIdentifier")
            user_identifier.hashed_email = email_hash
            op.create.user_identifiers.append(user_identifier)
            operations.append(op)

        request = client.get_type("AddOfflineUserDataJobOperationsRequest")
        request.resource_name = job_resource_name
        request.operations = operations
        request.enable_partial_failure = True

        response = offline_job_service.add_offline_user_data_job_operations(
            request=request,
        )

        if response.partial_failure_error:
            print(f"    [WARN] Partial failures in batch {i // BATCH_SIZE + 1}: "
                  f"{response.partial_failure_error.message[:200]}")
        else:
            print(f"    Added batch {i // BATCH_SIZE + 1}: {len(batch)} emails")

    # 3. Run the job (async — Google processes in background)
    offline_job_service.run_offline_user_data_job(
        resource_name=job_resource_name,
    )
    print(f"    Job submitted — Google will process in background (may take 24-48h)")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    dry_run = len(sys.argv) > 1 and sys.argv[1] == "dry-run"
    today = date.today()

    print("=" * 60)
    print(f"Nature's Seed — Customer Match Sync")
    print(f"Date: {today.isoformat()}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 60)

    # 1. Fetch customers from Supabase
    print("\n[1/3] Fetching customers from Supabase...")
    customers = fetch_customers()
    if not customers:
        print("[DONE] No customers found — nothing to sync")
        return

    # 2. Segment into audiences
    print(f"\n[2/3] Segmenting {len(customers)} customers into audiences...")
    segments = segment_customers(customers, today)

    # Summary
    print(f"\n{'─' * 40}")
    print("Audience Summary:")
    for name, data in segments.items():
        print(f"  {name}: {data['count']} emails")
    print(f"{'─' * 40}")

    if dry_run:
        print("\n[DRY RUN] No uploads performed. Run without 'dry-run' to upload.")
        return

    # 3. Upload to Google Ads
    print("\n[3/3] Uploading to Google Ads Customer Match...")
    client = GoogleAdsClient.load_from_dict(GOOGLE_ADS_CONFIG)

    for name, data in segments.items():
        hashed_emails = data["hashed_emails"]
        if len(hashed_emails) < 100:
            print(f"\n  [{name}] SKIP — only {len(hashed_emails)} emails "
                  f"(need 1000 matched; uploading <100 raw is unlikely to hit threshold)")
            continue

        print(f"\n  [{name}] Uploading {len(hashed_emails)} hashed emails...")
        try:
            resource_name = get_or_create_user_list(
                client, GOOGLE_ADS_CUSTOMER_ID, name, data["description"]
            )
            upload_to_user_list(client, GOOGLE_ADS_CUSTOMER_ID, resource_name, hashed_emails)
            print(f"  [{name}] ✓ Upload complete")
        except Exception as e:
            print(f"  [{name}] ✗ Error: {e}")

        time.sleep(1)  # Brief pause between lists

    print("\n[DONE] Customer Match sync complete.")
    print("Note: Google typically takes 24-48 hours to process and match uploaded data.")
    print("Lists will appear in Google Ads > Tools > Audience Manager once processing completes.")


if __name__ == "__main__":
    main()
