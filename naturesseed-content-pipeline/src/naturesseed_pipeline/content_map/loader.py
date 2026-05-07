"""Load and merge content map input CSVs into normalized DataFrames."""

from pathlib import Path

import pandas as pd


def load_data(
    audit_dir: Path,
    classifier_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and merge the four content map input CSVs.

    Returns:
        articles_df: one row per article with content_id, post_id, title, url,
                     word_count, products_count, primary_category, primary_subcategory
        edges_df:    article-to-article internal links with source_id, target_id, anchor_text
        taxonomy_df: category/subcategory/article_count from taxonomy-key.csv
    """
    articles = pd.read_csv(audit_dir / "per-article.csv")

    # Extract WP post ID from ?p=<ID> URL pattern (all drafts use this format)
    articles["post_id"] = (
        articles["url"].str.extract(r"\?p=(\d+)")[0].astype("Int64")
    )

    classifications = pd.read_csv(classifier_dir / "classifications.csv")
    classifications["post_id"] = classifications["post_id"].astype("Int64")

    # One article may appear multiple times; take first row per post_id as primary
    primary = (
        classifications.groupby("post_id", as_index=False)
        .first()[["post_id", "category", "subcategory"]]
        .rename(columns={"category": "primary_category", "subcategory": "primary_subcategory"})
    )

    articles = articles.merge(primary, on="post_id", how="left")
    articles["primary_category"] = articles["primary_category"].fillna("Uncategorized")
    articles["primary_subcategory"] = articles["primary_subcategory"].fillna("Uncategorized")

    edges = pd.read_csv(audit_dir / "internal-linking.csv")
    edges = edges.rename(
        columns={"source_content_id": "source_id", "target_content_id": "target_id"}
    )
    # Drop external links (blank target) and cast to int
    edges = edges.dropna(subset=["target_id"]).copy()
    edges["source_id"] = edges["source_id"].astype(int)
    edges["target_id"] = edges["target_id"].astype(int)

    taxonomy = pd.read_csv(classifier_dir / "taxonomy-key.csv")

    return articles, edges, taxonomy
