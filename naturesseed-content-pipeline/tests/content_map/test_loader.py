from pathlib import Path
import pandas as pd
import pytest
from naturesseed_pipeline.content_map.loader import load_data

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def data():
    return load_data(audit_dir=FIXTURES, classifier_dir=FIXTURES)


def test_articles_row_count(data):
    articles, _, _ = data
    assert len(articles) == 5


def test_post_id_extracted(data):
    articles, _, _ = data
    row = articles[articles["content_id"] == 1].iloc[0]
    assert row["post_id"] == 100


def test_primary_category_joined(data):
    articles, _, _ = data
    row = articles[articles["content_id"] == 1].iloc[0]
    assert row["primary_category"] == "Lawn Care"
    assert row["primary_subcategory"] == "Overseeding"


def test_edges_drop_external_links(data):
    _, edges, _ = data
    # Row with blank target_content_id (external link) must be excluded
    assert edges["target_id"].notna().all()
    assert len(edges) == 6  # 7 rows in fixture minus 1 external link


def test_edges_columns(data):
    _, edges, _ = data
    assert set(edges.columns) >= {"source_id", "target_id", "anchor_text"}


def test_taxonomy_loaded(data):
    _, _, taxonomy = data
    assert len(taxonomy) == 4
    assert "category" in taxonomy.columns and "subcategory" in taxonomy.columns


def test_uncategorized_fallback():
    # Article with no classification row gets "Uncategorized"
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        # per-article with one article not in classifications
        (p / "per-article.csv").write_text(
            "content_id,title,url,post_type,status,word_count,products_count,open_findings,critical_findings\n"
            "99,Mystery Article,https://naturesseed.com/?p=999,post,draft,500,0,0,0\n"
        )
        (p / "internal-linking.csv").write_text(
            "source_content_id,target_content_id,anchor_text,href\n"
        )
        (p / "classifications.csv").write_text(
            "post_id,title,url,category,subcategory,species_mentioned,products_mentioned,has_link\n"
        )
        (p / "taxonomy-key.csv").write_text(
            "category,subcategory,article_count\n"
        )
        articles, _, _ = load_data(audit_dir=p, classifier_dir=p)
        row = articles.iloc[0]
        assert row["primary_category"] == "Uncategorized"
        assert row["primary_subcategory"] == "Uncategorized"
