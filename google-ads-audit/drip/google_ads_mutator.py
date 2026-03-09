"""
Google Ads Mutation Library — Nature's Seed Drip Automation
============================================================
All write operations for the Google Ads account.
Every function supports validate_only=True for dry-run testing.

Usage:
    from google_ads_mutator import GoogleAdsMutator
    mutator = GoogleAdsMutator()

    # Dry run (no changes)
    mutator.update_campaign_budget(campaign_id, new_budget_micros, validate_only=True)

    # Live execution
    mutator.update_campaign_budget(campaign_id, new_budget_micros, validate_only=False)
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.api_core.exceptions import GoogleAPICallError

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("google_ads_mutator")

# ── Load credentials from .env ───────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # ClaudeDataAgent-/
AUDIT_DIR = Path(__file__).resolve().parents[1]     # google-ads-audit/


def _load_env():
    """Load .env file from project root."""
    env = {}
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        raise FileNotFoundError(f".env not found at {env_file}")
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip().strip("'\"")
    return env


# ── Guardrails ───────────────────────────────────────────────────────────────
PEAK_MONTHS = {3, 4, 5, 9, 10}  # March-May, September-October
MAX_CHANGE_PCT = 0.30  # 30% max change per cycle
MAX_KEYWORDS_PAUSED_PER_CYCLE = 10
MAX_NEGATIVES_ADDED_PER_CYCLE = 20
MAX_PRODUCTS_EXCLUDED_PER_CYCLE = 15


class GuardrailViolation(Exception):
    """Raised when a proposed change violates guardrail constraints."""
    pass


def check_peak_season(action_type: str):
    """Check if current month is peak season and block structural changes."""
    month = datetime.now().month
    if month in PEAK_MONTHS:
        blocked_actions = [
            "bidding_strategy_change",
            "campaign_restructure",
            "campaign_create",
            "asset_group_create",
        ]
        if action_type in blocked_actions:
            raise GuardrailViolation(
                f"Action '{action_type}' blocked: peak season (month {month}). "
                f"Only budget adjustments, negatives, and exclusions allowed."
            )


def check_change_limit(current_value: float, new_value: float, param_name: str):
    """Ensure change doesn't exceed 30% of current value."""
    if current_value == 0:
        return
    change_pct = abs(new_value - current_value) / current_value
    if change_pct > MAX_CHANGE_PCT:
        raise GuardrailViolation(
            f"Change to {param_name} exceeds 30% limit: "
            f"current={current_value}, proposed={new_value}, change={change_pct:.1%}. "
            f"Max allowed: {current_value * (1 + MAX_CHANGE_PCT):.2f} or {current_value * (1 - MAX_CHANGE_PCT):.2f}"
        )


# ── Main Mutator Class ──────────────────────────────────────────────────────

class GoogleAdsMutator:
    """
    Google Ads API mutation operations with built-in guardrails.
    All operations log their actions and support dry-run via validate_only.
    """

    def __init__(self):
        env = _load_env()
        credentials = {
            "developer_token": env["GOOGLE_ADS_DEVELOPER_TOKEN"],
            "client_id": env["GOOGLE_ADS_CLIENT_ID"],
            "client_secret": env["GOOGLE_ADS_CLIENT_SECRET"],
            "refresh_token": env["GOOGLE_ADS_REFRESH_TOKEN"],
            "login_customer_id": env["GOOGLE_ADS_LOGIN_CUSTOMER_ID"].replace("-", ""),
            "use_proto_plus": True,
        }
        self.client = GoogleAdsClient.load_from_dict(credentials)
        self.customer_id = env["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
        self.change_log = []

    def _log_change(self, action: str, details: dict, validate_only: bool):
        """Log every change for audit trail."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "validate_only": validate_only,
            "details": details,
        }
        self.change_log.append(entry)
        mode = "DRY RUN" if validate_only else "LIVE"
        log.info(f"[{mode}] {action}: {json.dumps(details, default=str)}")

    def get_change_log(self) -> list:
        """Return all changes made in this session."""
        return self.change_log

    def save_change_log(self, path: str = None):
        """Save change log to file."""
        if path is None:
            path = AUDIT_DIR / "drip" / f"changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.change_log, f, indent=2, default=str)
        log.info(f"Change log saved to {path}")

    # ── READ OPERATIONS ──────────────────────────────────────────────────

    def get_campaign_performance(self, days: int = 90) -> list:
        """Pull campaign performance for the last N days."""
        ga_service = self.client.get_service("GoogleAdsService")
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.impressions,
                metrics.clicks,
                metrics.search_impression_share
            FROM campaign
            WHERE campaign.status = 'ENABLED'
                AND segments.date BETWEEN '{start}' AND '{end}'
            ORDER BY metrics.cost_micros DESC
        """
        response = ga_service.search(customer_id=self.customer_id, query=query)
        campaigns = []
        for row in response:
            cost = row.metrics.cost_micros / 1_000_000
            rev = row.metrics.conversions_value
            campaigns.append({
                "id": row.campaign.id,
                "name": row.campaign.name,
                "type": row.campaign.advertising_channel_type.name,
                "budget_micros": row.campaign_budget.amount_micros,
                "budget_daily": row.campaign_budget.amount_micros / 1_000_000,
                "cost": round(cost, 2),
                "revenue": round(rev, 2),
                "roas": round(rev / cost, 2) if cost > 0 else 0,
                "conversions": round(row.metrics.conversions, 1),
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "impression_share": round(row.metrics.search_impression_share, 4) if row.metrics.search_impression_share else 0,
            })
        return campaigns

    def get_search_terms(self, days: int = 30, limit: int = 200) -> list:
        """Pull search term performance."""
        ga_service = self.client.get_service("GoogleAdsService")
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        query = f"""
            SELECT
                search_term_view.search_term,
                campaign.name,
                campaign.id,
                ad_group.id,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.clicks,
                metrics.impressions
            FROM search_term_view
            WHERE campaign.status = 'ENABLED'
                AND segments.date BETWEEN '{start}' AND '{end}'
                AND metrics.cost_micros > 0
            ORDER BY metrics.cost_micros DESC
            LIMIT {limit}
        """
        response = ga_service.search(customer_id=self.customer_id, query=query)
        terms = []
        for row in response:
            cost = row.metrics.cost_micros / 1_000_000
            rev = row.metrics.conversions_value
            terms.append({
                "term": row.search_term_view.search_term,
                "campaign_name": row.campaign.name,
                "campaign_id": row.campaign.id,
                "ad_group_id": row.ad_group.id,
                "cost": round(cost, 2),
                "revenue": round(rev, 2),
                "roas": round(rev / cost, 2) if cost > 0 else 0,
                "conversions": round(row.metrics.conversions, 1),
                "clicks": row.metrics.clicks,
            })
        return terms

    def get_shopping_products(self, days: int = 90, limit: int = 200) -> list:
        """Pull Shopping product performance."""
        ga_service = self.client.get_service("GoogleAdsService")
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        query = f"""
            SELECT
                segments.product_item_id,
                segments.product_title,
                segments.product_type_l1,
                segments.product_type_l2,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.clicks,
                metrics.impressions
            FROM shopping_performance_view
            WHERE segments.date BETWEEN '{start}' AND '{end}'
                AND metrics.cost_micros > 0
            ORDER BY metrics.cost_micros DESC
            LIMIT {limit}
        """
        response = ga_service.search(customer_id=self.customer_id, query=query)
        products = []
        for row in response:
            cost = row.metrics.cost_micros / 1_000_000
            rev = row.metrics.conversions_value
            products.append({
                "item_id": row.segments.product_item_id,
                "title": row.segments.product_title,
                "type_l1": row.segments.product_type_l1,
                "type_l2": row.segments.product_type_l2,
                "cost": round(cost, 2),
                "revenue": round(rev, 2),
                "roas": round(rev / cost, 2) if cost > 0 else 0,
                "conversions": round(row.metrics.conversions, 1),
                "clicks": row.metrics.clicks,
                "impressions": row.metrics.impressions,
            })
        return products

    def get_keywords(self, campaign_id: int = None) -> list:
        """Pull keyword performance from enabled campaigns."""
        ga_service = self.client.get_service("GoogleAdsService")
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        campaign_filter = f"AND campaign.id = {campaign_id}" if campaign_id else ""
        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group.id,
                ad_group.name,
                campaign.id,
                campaign.name,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.clicks,
                metrics.impressions
            FROM keyword_view
            WHERE campaign.status = 'ENABLED'
                AND ad_group_criterion.status = 'ENABLED'
                AND segments.date BETWEEN '{start}' AND '{end}'
                {campaign_filter}
            ORDER BY metrics.cost_micros DESC
            LIMIT 200
        """
        response = ga_service.search(customer_id=self.customer_id, query=query)
        keywords = []
        for row in response:
            cost = row.metrics.cost_micros / 1_000_000
            rev = row.metrics.conversions_value
            keywords.append({
                "criterion_id": row.ad_group_criterion.criterion_id,
                "keyword": row.ad_group_criterion.keyword.text,
                "match_type": row.ad_group_criterion.keyword.match_type.name,
                "status": row.ad_group_criterion.status.name,
                "ad_group_id": row.ad_group.id,
                "ad_group_name": row.ad_group.name,
                "campaign_id": row.campaign.id,
                "campaign_name": row.campaign.name,
                "cost": round(cost, 2),
                "revenue": round(rev, 2),
                "roas": round(rev / cost, 2) if cost > 0 else 0,
                "conversions": round(row.metrics.conversions, 1),
                "clicks": row.metrics.clicks,
            })
        return keywords

    # ── WRITE OPERATIONS ─────────────────────────────────────────────────

    def update_campaign_budget(
        self,
        campaign_id: int,
        new_budget_daily: float,
        current_budget_daily: float = None,
        validate_only: bool = True,
    ) -> dict:
        """
        Update a campaign's daily budget.

        Args:
            campaign_id: The campaign ID
            new_budget_daily: New daily budget in dollars (e.g., 500.0)
            current_budget_daily: Current budget for guardrail check (auto-fetched if None)
            validate_only: If True, validates but doesn't apply
        """
        # Fetch current budget if not provided
        if current_budget_daily is None:
            campaigns = self.get_campaign_performance(days=7)
            match = [c for c in campaigns if c["id"] == campaign_id]
            if not match:
                raise ValueError(f"Campaign {campaign_id} not found or not enabled")
            current_budget_daily = match[0]["budget_daily"]

        # Guardrail: 30% max change
        check_change_limit(current_budget_daily, new_budget_daily, "campaign_budget")

        new_budget_micros = int(new_budget_daily * 1_000_000)

        # Find the budget resource name
        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT campaign.id, campaign_budget.resource_name
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """
        response = ga_service.search(customer_id=self.customer_id, query=query)
        budget_resource = None
        for row in response:
            budget_resource = row.campaign_budget.resource_name
            break

        if not budget_resource:
            raise ValueError(f"Budget resource not found for campaign {campaign_id}")

        # Build mutation
        budget_service = self.client.get_service("CampaignBudgetService")
        budget_operation = self.client.get_type("CampaignBudgetOperation")
        budget = budget_operation.update
        budget.resource_name = budget_resource
        budget.amount_micros = new_budget_micros

        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("amount_micros")
        budget_operation.update_mask.CopyFrom(field_mask)

        details = {
            "campaign_id": campaign_id,
            "budget_resource": budget_resource,
            "current_budget": current_budget_daily,
            "new_budget": new_budget_daily,
            "change_pct": f"{(new_budget_daily - current_budget_daily) / current_budget_daily:.1%}",
        }

        self._log_change("update_campaign_budget", details, validate_only)

        response = budget_service.mutate_campaign_budgets(
            customer_id=self.customer_id,
            operations=[budget_operation],
            validate_only=validate_only,
        )

        return {
            "success": True,
            "validate_only": validate_only,
            "details": details,
            "response": str(response) if not validate_only else "validated",
        }

    def pause_keyword(
        self,
        ad_group_id: int,
        criterion_id: int,
        keyword_text: str = "",
        validate_only: bool = True,
    ) -> dict:
        """Pause a keyword in an ad group."""
        check_peak_season("keyword_pause")  # This is allowed during peak, just logging

        resource_name = self.client.get_service("AdGroupCriterionService").ad_group_criterion_path(
            self.customer_id, ad_group_id, criterion_id
        )

        operation = self.client.get_type("AdGroupCriterionOperation")
        criterion = operation.update
        criterion.resource_name = resource_name
        criterion.status = self.client.enums.AdGroupCriterionStatusEnum.PAUSED

        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("status")
        operation.update_mask.CopyFrom(field_mask)

        details = {
            "ad_group_id": ad_group_id,
            "criterion_id": criterion_id,
            "keyword": keyword_text,
            "action": "PAUSE",
        }
        self._log_change("pause_keyword", details, validate_only)

        service = self.client.get_service("AdGroupCriterionService")
        response = service.mutate_ad_group_criteria(
            customer_id=self.customer_id,
            operations=[operation],
            validate_only=validate_only,
        )

        return {"success": True, "validate_only": validate_only, "details": details}

    def add_negative_keyword_to_campaign(
        self,
        campaign_id: int,
        keyword_text: str,
        match_type: str = "EXACT",
        validate_only: bool = True,
    ) -> dict:
        """Add a negative keyword to a specific campaign."""
        service = self.client.get_service("CampaignCriterionService")
        operation = self.client.get_type("CampaignCriterionOperation")

        criterion = operation.create
        criterion.campaign = self.client.get_service("CampaignService").campaign_path(
            self.customer_id, campaign_id
        )
        criterion.negative = True
        criterion.keyword.text = keyword_text
        criterion.keyword.match_type = getattr(
            self.client.enums.KeywordMatchTypeEnum, match_type
        )

        details = {
            "campaign_id": campaign_id,
            "keyword": keyword_text,
            "match_type": match_type,
            "action": "ADD_NEGATIVE",
        }
        self._log_change("add_negative_keyword_campaign", details, validate_only)

        response = service.mutate_campaign_criteria(
            customer_id=self.customer_id,
            operations=[operation],
            validate_only=validate_only,
        )

        return {"success": True, "validate_only": validate_only, "details": details}

    def add_negative_keyword_account_level(
        self,
        keyword_text: str,
        match_type: str = "EXACT",
        validate_only: bool = True,
    ) -> dict:
        """Add a negative keyword at the account (customer) level."""
        service = self.client.get_service("CustomerNegativeCriterionService")
        operation = self.client.get_type("CustomerNegativeCriterionOperation")

        criterion = operation.create
        criterion.keyword.text = keyword_text
        criterion.keyword.match_type = getattr(
            self.client.enums.KeywordMatchTypeEnum, match_type
        )

        details = {
            "keyword": keyword_text,
            "match_type": match_type,
            "action": "ADD_NEGATIVE_ACCOUNT",
        }
        self._log_change("add_negative_keyword_account", details, validate_only)

        response = service.mutate_customer_negative_criteria(
            customer_id=self.customer_id,
            operations=[operation],
            validate_only=validate_only,
        )

        return {"success": True, "validate_only": validate_only, "details": details}

    def add_keyword_to_ad_group(
        self,
        ad_group_id: int,
        keyword_text: str,
        match_type: str = "PHRASE",
        cpc_bid_micros: int = None,
        validate_only: bool = True,
    ) -> dict:
        """Add a new keyword to an existing ad group."""
        service = self.client.get_service("AdGroupCriterionService")
        operation = self.client.get_type("AdGroupCriterionOperation")

        criterion = operation.create
        criterion.ad_group = self.client.get_service("AdGroupService").ad_group_path(
            self.customer_id, ad_group_id
        )
        criterion.status = self.client.enums.AdGroupCriterionStatusEnum.ENABLED
        criterion.keyword.text = keyword_text
        criterion.keyword.match_type = getattr(
            self.client.enums.KeywordMatchTypeEnum, match_type
        )

        if cpc_bid_micros:
            criterion.cpc_bid_micros = cpc_bid_micros

        details = {
            "ad_group_id": ad_group_id,
            "keyword": keyword_text,
            "match_type": match_type,
            "action": "ADD_KEYWORD",
        }
        self._log_change("add_keyword", details, validate_only)

        response = service.mutate_ad_group_criteria(
            customer_id=self.customer_id,
            operations=[operation],
            validate_only=validate_only,
        )

        return {"success": True, "validate_only": validate_only, "details": details}

    def create_ad_group(
        self,
        campaign_id: int,
        ad_group_name: str,
        validate_only: bool = True,
    ) -> dict:
        """Create a new ad group in a campaign."""
        check_peak_season("campaign_restructure")

        service = self.client.get_service("AdGroupService")
        operation = self.client.get_type("AdGroupOperation")

        ad_group = operation.create
        ad_group.name = ad_group_name
        ad_group.campaign = self.client.get_service("CampaignService").campaign_path(
            self.customer_id, campaign_id
        )
        ad_group.status = self.client.enums.AdGroupStatusEnum.ENABLED
        ad_group.type_ = self.client.enums.AdGroupTypeEnum.SEARCH_STANDARD

        details = {
            "campaign_id": campaign_id,
            "ad_group_name": ad_group_name,
            "action": "CREATE_AD_GROUP",
        }
        self._log_change("create_ad_group", details, validate_only)

        response = service.mutate_ad_groups(
            customer_id=self.customer_id,
            operations=[operation],
            validate_only=validate_only,
        )

        result = {"success": True, "validate_only": validate_only, "details": details}
        if not validate_only and response.results:
            result["ad_group_resource"] = response.results[0].resource_name
        return result

    # ── BATCH OPERATIONS ─────────────────────────────────────────────────

    def batch_add_negative_keywords(
        self,
        campaign_id: int,
        keywords: list,
        match_type: str = "EXACT",
        validate_only: bool = True,
    ) -> dict:
        """
        Add multiple negative keywords to a campaign in one API call.

        Args:
            campaign_id: Target campaign
            keywords: List of keyword strings
            match_type: EXACT, PHRASE, or BROAD
            validate_only: Dry-run mode
        """
        if len(keywords) > MAX_NEGATIVES_ADDED_PER_CYCLE:
            raise GuardrailViolation(
                f"Attempting to add {len(keywords)} negatives, max is {MAX_NEGATIVES_ADDED_PER_CYCLE} per cycle"
            )

        service = self.client.get_service("CampaignCriterionService")
        operations = []

        for kw in keywords:
            op = self.client.get_type("CampaignCriterionOperation")
            criterion = op.create
            criterion.campaign = self.client.get_service("CampaignService").campaign_path(
                self.customer_id, campaign_id
            )
            criterion.negative = True
            criterion.keyword.text = kw
            criterion.keyword.match_type = getattr(
                self.client.enums.KeywordMatchTypeEnum, match_type
            )
            operations.append(op)

        details = {
            "campaign_id": campaign_id,
            "keywords": keywords,
            "match_type": match_type,
            "count": len(keywords),
        }
        self._log_change("batch_add_negatives", details, validate_only)

        response = service.mutate_campaign_criteria(
            customer_id=self.customer_id,
            operations=operations,
            validate_only=validate_only,
            partial_failure=True,
        )

        return {"success": True, "validate_only": validate_only, "details": details}

    def batch_pause_keywords(
        self,
        keyword_specs: list,
        validate_only: bool = True,
    ) -> dict:
        """
        Pause multiple keywords in one API call.

        Args:
            keyword_specs: List of dicts with {ad_group_id, criterion_id, keyword_text}
            validate_only: Dry-run mode
        """
        if len(keyword_specs) > MAX_KEYWORDS_PAUSED_PER_CYCLE:
            raise GuardrailViolation(
                f"Attempting to pause {len(keyword_specs)} keywords, max is {MAX_KEYWORDS_PAUSED_PER_CYCLE} per cycle"
            )

        service = self.client.get_service("AdGroupCriterionService")
        operations = []

        for spec in keyword_specs:
            op = self.client.get_type("AdGroupCriterionOperation")
            criterion = op.update
            criterion.resource_name = service.ad_group_criterion_path(
                self.customer_id, spec["ad_group_id"], spec["criterion_id"]
            )
            criterion.status = self.client.enums.AdGroupCriterionStatusEnum.PAUSED

            field_mask = self.client.get_type("FieldMask")
            field_mask.paths.append("status")
            op.update_mask.CopyFrom(field_mask)
            operations.append(op)

        details = {
            "keywords": [s.get("keyword_text", s["criterion_id"]) for s in keyword_specs],
            "count": len(keyword_specs),
        }
        self._log_change("batch_pause_keywords", details, validate_only)

        response = service.mutate_ad_group_criteria(
            customer_id=self.customer_id,
            operations=operations,
            validate_only=validate_only,
            partial_failure=True,
        )

        return {"success": True, "validate_only": validate_only, "details": details}

    # ── ACCOUNT SNAPSHOT ─────────────────────────────────────────────────

    def get_account_snapshot(self) -> dict:
        """
        Pull a comprehensive account snapshot for the cycle plan.
        Returns campaigns, top search terms, top products, and key metrics.
        """
        log.info("Pulling account snapshot...")

        campaigns = self.get_campaign_performance(days=30)
        search_terms = self.get_search_terms(days=30, limit=100)
        products = self.get_shopping_products(days=30, limit=100)
        keywords = self.get_keywords()

        total_spend = sum(c["cost"] for c in campaigns)
        total_rev = sum(c["revenue"] for c in campaigns)

        # Identify waste
        wasted_terms = [t for t in search_terms if t["roas"] < 1.0 and t["cost"] > 10]
        wasted_term_spend = sum(t["cost"] for t in wasted_terms)

        zero_rev_products = [p for p in products if p["revenue"] == 0 and p["cost"] > 10]
        zero_rev_spend = sum(p["cost"] for p in zero_rev_products)

        losing_keywords = [k for k in keywords if k["roas"] < 1.0 and k["cost"] > 10]

        # Winners
        winner_terms = [t for t in search_terms if t["roas"] >= 5.0]
        star_products = [p for p in products if p["roas"] >= 5.0 and p["cost"] > 20]

        snapshot = {
            "date": datetime.now().isoformat(),
            "period": "last_30_days",
            "account_totals": {
                "spend": total_spend,
                "revenue": total_rev,
                "roas": round(total_rev / total_spend, 2) if total_spend > 0 else 0,
            },
            "campaigns": campaigns,
            "waste_summary": {
                "wasted_search_terms": len(wasted_terms),
                "wasted_search_spend": wasted_term_spend,
                "zero_rev_products": len(zero_rev_products),
                "zero_rev_spend": zero_rev_spend,
                "losing_keywords": len(losing_keywords),
            },
            "winners": {
                "top_search_terms": winner_terms[:10],
                "star_products": star_products[:10],
            },
            "keywords": keywords,
            "search_terms_sample": search_terms[:50],
            "products_sample": products[:50],
        }

        return snapshot


# ── Convenience Functions ────────────────────────────────────────────────────

def dollars_to_micros(dollars: float) -> int:
    """Convert dollar amount to micros (Google Ads API unit)."""
    return int(dollars * 1_000_000)


def micros_to_dollars(micros: int) -> float:
    """Convert micros to dollar amount."""
    return micros / 1_000_000


if __name__ == "__main__":
    # Quick test — pull account snapshot
    mutator = GoogleAdsMutator()
    snapshot = mutator.get_account_snapshot()
    print(f"\nAccount ROAS (30d): {snapshot['account_totals']['roas']}x")
    print(f"Spend: ${snapshot['account_totals']['spend']:,.0f}")
    print(f"Revenue: ${snapshot['account_totals']['revenue']:,.0f}")
    print(f"Waste: {snapshot['waste_summary']}")
    for c in snapshot["campaigns"]:
        print(f"  {c['name']}: ${c['budget_daily']:.0f}/day, {c['roas']}x ROAS, {c['impression_share']:.0%} IS")
