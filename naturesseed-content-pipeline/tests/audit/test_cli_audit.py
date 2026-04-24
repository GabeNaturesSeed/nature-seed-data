"""Smoke tests for the new audit CLI subcommands via typer.testing."""

from typer.testing import CliRunner

from naturesseed_pipeline.cli import app

runner = CliRunner()


def test_audit_help_lists_new_subcommands():
    result = runner.invoke(app, ["audit", "--help"])
    assert result.exit_code == 0
    for cmd in ("sync", "classify", "tag-products", "scan-links",
                "scan-decay"):
        assert cmd in result.stdout


def test_audit_classify_help_mentions_markdown_flow():
    result = runner.invoke(app, ["audit", "classify", "--help"])
    assert result.exit_code == 0
    assert "export-proposals" in result.stdout.lower()
    assert "import-approvals" in result.stdout.lower()
