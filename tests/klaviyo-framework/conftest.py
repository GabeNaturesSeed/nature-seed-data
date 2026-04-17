"""Shared pytest fixtures for klaviyo-framework tests."""

import sys
from pathlib import Path
import pytest

# Make framework modules importable during tests
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "marketing" / "klaviyo-audit"))  # allow `from framework import ...`


@pytest.fixture
def sample_campaign_report():
    """Mocked Klaviyo campaign performance payload."""
    return {
        "data": {
            "attributes": {
                "recipients": 6636,
                "delivered": 6580,
                "opens_unique": 4497,
                "clicks_unique": 112,
                "conversions": 13,
                "conversion_value": 6856.40,
                "unsubscribes": 8,
                "spam_complaints": 0,
                "bounced": 56,
            }
        }
    }


@pytest.fixture
def sample_flow_report():
    """Mocked Klaviyo flow performance payload."""
    return {
        "data": {
            "attributes": {
                "recipients": 3208,
                "opens_unique": 1350,
                "clicks_unique": 138,
                "conversions": 135,
                "conversion_value": 29314.00,
                "conversion_rate": 0.042,
            }
        }
    }


@pytest.fixture
def sample_metric_aggregates():
    """Mocked Klaviyo query-metric-aggregates payload."""
    return {
        "data": {
            "attributes": {
                "dates": ["2026-03-17", "2026-03-18"],
                "data": [
                    {"measurements": {"count": [12, 15], "sum_value": [1450.0, 1820.0]}},
                ],
            }
        }
    }
