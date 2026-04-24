"""Test CLI entry point works."""

from typer.testing import CliRunner

from naturesseed_pipeline.cli import app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Nature's Seed Content Pipeline" in result.output


def test_db_init() -> None:
    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code == 0
    assert "Database initialized" in result.output


def test_subcommands_listed() -> None:
    result = runner.invoke(app, ["--help"])
    assert "db" in result.output
    assert "audit" in result.output
    assert "research" in result.output
    assert "write" in result.output
    assert "publish" in result.output
