from pathlib import Path
import pytest
import networkx as nx
import pandas as pd
from naturesseed_pipeline.content_map.loader import load_data
from naturesseed_pipeline.content_map.graph import build_graph
from naturesseed_pipeline.content_map.coverage import (
    build_coverage_layer,
    ClusterHealth,
    GhostNode,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def coverage_data():
    articles, edges, taxonomy = load_data(audit_dir=FIXTURES, classifier_dir=FIXTURES)
    g = build_graph(articles, edges)
    return build_coverage_layer(g, taxonomy)


def test_returns_health_and_ghosts(coverage_data):
    health, ghosts = coverage_data
    assert isinstance(health, dict)
    assert isinstance(ghosts, list)


def test_lawn_care_overseeding_yellow():
    # Fixture: Lawn Care/Overseeding has 1 article (word_count=2500, products=2) but only 1 article
    # → yellow (needs ≥2 supporting articles, i.e. len >= 3 total)
    articles = pd.DataFrame({
        "content_id": [1],
        "title": ["Overseeding Guide"],
        "url": ["https://naturesseed.com/?p=100"],
        "word_count": [2500],
        "products_count": [2],
        "post_id": [100],
        "primary_category": ["Lawn Care"],
        "primary_subcategory": ["Overseeding"],
    })
    edges = pd.DataFrame({"source_id": pd.Series([], dtype=int), "target_id": pd.Series([], dtype=int), "anchor_text": []})
    taxonomy = pd.DataFrame({
        "category": ["Lawn Care"],
        "subcategory": ["Overseeding"],
        "article_count": [27],
    })
    g = build_graph(articles, edges)
    health, _ = build_coverage_layer(g, taxonomy)
    assert health[("Lawn Care", "Overseeding")] == ClusterHealth.YELLOW


def test_red_cluster_for_missing_subcategory(coverage_data):
    # Pasture Management/Overseeding is in taxonomy fixture but has no articles → RED
    health, _ = coverage_data
    assert health[("Pasture Management", "Overseeding")] == ClusterHealth.RED


def test_ghost_node_for_red_cluster(coverage_data):
    _, ghosts = coverage_data
    labels = [g.label for g in ghosts]
    assert any("Pasture Management" in label for label in labels)


def test_ghost_node_has_category(coverage_data):
    _, ghosts = coverage_data
    for ghost in ghosts:
        assert ghost.category != ""
        assert ghost.subcategory != ""
