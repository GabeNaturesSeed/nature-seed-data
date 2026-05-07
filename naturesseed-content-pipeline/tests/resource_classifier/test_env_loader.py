import pytest
from pathlib import Path


def test_parses_spaced_equals_and_strips_quotes(tmp_path):
    from docs.resource_classifier.env_loader import load_env
    env_file = tmp_path / ".env"
    env_file.write_text('WC_CK = "my_key"\nWC_CS = "my_secret"\n')
    result = load_env(env_file)
    assert result["WC_CK"] == "my_key"
    assert result["WC_CS"] == "my_secret"


def test_skips_blank_lines_and_comments(tmp_path):
    from docs.resource_classifier.env_loader import load_env
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\n\nWC_CK = \"key\"\n")
    result = load_env(env_file)
    assert list(result.keys()) == ["WC_CK"]


def test_handles_no_quotes(tmp_path):
    from docs.resource_classifier.env_loader import load_env
    env_file = tmp_path / ".env"
    env_file.write_text("CF_WORKER_URL = https://worker.example.com\n")
    result = load_env(env_file)
    assert result["CF_WORKER_URL"] == "https://worker.example.com"
