from pathlib import Path
import pytest
from naturesseed_pipeline.content_map.loader import load_data
from naturesseed_pipeline.content_map.graph import build_graph, compute_metrics

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def graph_and_metrics():
    articles, edges, _ = load_data(audit_dir=FIXTURES, classifier_dir=FIXTURES)
    g = build_graph(articles, edges)
    metrics = compute_metrics(g)
    return g, metrics


def test_node_count(graph_and_metrics):
    g, _ = graph_and_metrics
    assert g.number_of_nodes() == 5


def test_edge_count(graph_and_metrics):
    # 6 article-to-article edges in fixture
    g, _ = graph_and_metrics
    assert g.number_of_edges() == 6


def test_inbound_counts(graph_and_metrics):
    _, metrics = graph_and_metrics
    assert metrics[1].inbound_count == 2  # linked by articles 2 and 3
    assert metrics[3].inbound_count == 2  # linked by articles 1 and 2
    assert metrics[4].inbound_count == 0  # orphan


def test_outbound_counts(graph_and_metrics):
    _, metrics = graph_and_metrics
    assert metrics[1].outbound_count == 2
    assert metrics[4].outbound_count == 1


def test_orphan_detection(graph_and_metrics):
    _, metrics = graph_and_metrics
    assert metrics[4].is_orphan is True
    assert metrics[1].is_orphan is False


def test_link_depth_no_hubs(graph_and_metrics):
    # No article has inbound >= 3 in fixture, so all depths are -1
    _, metrics = graph_and_metrics
    for m in metrics.values():
        assert m.link_depth == -1


def test_link_depth_with_hub():
    # Build a minimal graph where one node qualifies as hub (inbound >= 3)
    import pandas as pd
    from naturesseed_pipeline.content_map.graph import build_graph, compute_metrics

    articles = pd.DataFrame({
        "content_id": [1, 2, 3, 4, 5],
        "title": ["Hub", "A", "B", "C", "Leaf"],
        "url": [f"https://naturesseed.com/?p={i}" for i in range(1, 6)],
        "word_count": [2000, 800, 700, 900, 500],
        "products_count": [0] * 5,
        "post_id": list(range(1, 6)),
        "primary_category": ["Lawn Care"] * 5,
        "primary_subcategory": ["Overseeding"] * 5,
    })
    # Articles 2, 3, 4 all link to article 1 → hub. Article 1 links to article 5.
    edges = pd.DataFrame({
        "source_id": [2, 3, 4, 1],
        "target_id": [1, 1, 1, 5],
        "anchor_text": ["hub"] * 4,
    })
    g = build_graph(articles, edges)
    metrics = compute_metrics(g)
    assert metrics[1].inbound_count == 3
    assert metrics[1].link_depth == 0   # hub itself
    assert metrics[5].link_depth == 1   # 1 hop from hub


def test_consolidation_candidate(graph_and_metrics):
    _, metrics = graph_and_metrics
    # Article 3: Lawn Care/Cool-Season Grasses, inbound=2, word_count=600 < 800,
    # not max word_count in subcategory (article 2 has 900)
    assert metrics[3].is_consolidation_candidate is True
    assert metrics[3].consolidate_into_id == 2  # article 2 has most inbound in subcategory


def test_non_candidate_high_wordcount(graph_and_metrics):
    _, metrics = graph_and_metrics
    # Article 2: word_count=900 >= 800, so NOT a candidate
    assert metrics[2].is_consolidation_candidate is False


def test_non_candidate_max_wordcount_in_subcat(graph_and_metrics):
    _, metrics = graph_and_metrics
    # Article 4: only Wildflowers/Native Species Selection article (along with 5),
    # but article 4 has inbound=0, word_count=1800 (max in subcat) → not candidate
    assert metrics[4].is_consolidation_candidate is False
