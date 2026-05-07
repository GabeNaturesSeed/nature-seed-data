import tempfile
from pathlib import Path
import pandas as pd
import pytest
import networkx as nx
from naturesseed_pipeline.content_map.loader import load_data
from naturesseed_pipeline.content_map.graph import build_graph, compute_metrics
from naturesseed_pipeline.content_map.coverage import build_coverage_layer
from naturesseed_pipeline.content_map.exporter import export_csvs

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def export_dir(tmp_path):
    articles, edges, taxonomy = load_data(audit_dir=FIXTURES, classifier_dir=FIXTURES)
    g = build_graph(articles, edges)
    metrics = compute_metrics(g)
    health, ghosts = build_coverage_layer(g, taxonomy)
    export_csvs(g, metrics, health, ghosts, output_dir=tmp_path)
    return tmp_path


def test_orphans_csv_created(export_dir):
    assert (export_dir / "orphans.csv").exists()


def test_orphans_contains_article_4(export_dir):
    df = pd.read_csv(export_dir / "orphans.csv")
    assert 4 in df["content_id"].values


def test_consolidation_csv_created(export_dir):
    assert (export_dir / "consolidation-candidates.csv").exists()


def test_consolidation_contains_article_3(export_dir):
    df = pd.read_csv(export_dir / "consolidation-candidates.csv")
    assert 3 in df["candidate_id"].values


def test_consolidation_survivor_is_article_2(export_dir):
    df = pd.read_csv(export_dir / "consolidation-candidates.csv")
    row = df[df["candidate_id"] == 3].iloc[0]
    assert row["survivor_id"] == 2


def test_depth_violations_csv_created(export_dir):
    assert (export_dir / "depth-violations.csv").exists()


def test_coverage_gaps_csv_created(export_dir):
    assert (export_dir / "coverage-gaps.csv").exists()


def test_coverage_gaps_has_red_rows(export_dir):
    df = pd.read_csv(export_dir / "coverage-gaps.csv")
    assert "red" in df["health"].values
