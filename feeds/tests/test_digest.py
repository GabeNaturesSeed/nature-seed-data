import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from feeds.digest.run_audit import build_digest_markdown, run_audit

def _mock_result(channel, wc=10, ch=8, drift=1, incomplete=2, error=""):
    from feeds.adapters.base_adapter import AdapterResult, CoverageResult, DriftResult, QualityResult
    r = AdapterResult(channel=channel, error=error)
    if not error:
        r.coverage = CoverageResult(wc_total=wc, channel_total=ch, missing_skus=["SKU-A", "SKU-B"])
        r.drift = DriftResult(drifted=[{"sku": "SKU-A", "field": "price", "wc": "10.00", "channel": "12.00"}] * drift)
        r.quality = QualityResult(incomplete=[{"sku": "SKU-A", "missing_fields": ["gtin"]}] * incomplete)
    return r

def test_build_digest_markdown_contains_all_channels():
    results = [
        _mock_result("walmart"),
        _mock_result("amazon"),
        _mock_result("google_merchant", error="auth failed"),
    ]
    md = build_digest_markdown(results, date="2026-04-28")
    assert "walmart" in md
    assert "amazon" in md
    assert "google_merchant" in md
    assert "auth failed" in md
    assert "8/10" in md  # coverage display

def test_build_digest_markdown_has_action_items():
    results = [_mock_result("walmart")]
    md = build_digest_markdown(results, date="2026-04-28")
    assert "Action Items" in md
    assert "- [ ]" in md
