"""Verify audit-scoped config settings are readable and have sensible defaults."""

from naturesseed_pipeline.config import Settings


def test_audit_defaults_present():
    s = Settings()
    assert s.audit_llm_model == "claude-sonnet-4-6"
    assert s.audit_http_check_concurrency == 5
    assert s.audit_http_check_cache_days == 30
    assert 0.0 < s.audit_fuzzy_match_threshold <= 1.0
    assert s.audit_thin_word_count == 300
    assert isinstance(s.audit_current_shipping, str)


def test_audit_shipping_overridable_via_env(monkeypatch):
    monkeypatch.setenv("AUDIT_CURRENT_SHIPPING", "Free shipping over $99")
    s = Settings()
    assert "Free shipping over $99" in s.audit_current_shipping
