"""Ideal coverage analysis: cluster health and ghost nodes for missing content."""

from dataclasses import dataclass
from enum import Enum

import networkx as nx
import pandas as pd


class ClusterHealth(str, Enum):
    GREEN = "green"    # pillar + ≥2 supporting + product link
    YELLOW = "yellow"  # present but incomplete
    RED = "red"        # in taxonomy, zero articles


@dataclass
class GhostNode:
    label: str         # e.g. "Gap: Pasture Management / Overseeding"
    category: str
    subcategory: str
    ghost_type: str    # "missing_subcategory" | "missing_pillar"


def build_coverage_layer(
    g: nx.DiGraph,
    taxonomy: pd.DataFrame,
) -> tuple[dict[tuple[str, str], ClusterHealth], list[GhostNode]]:
    """Compute cluster health and ghost nodes from graph + taxonomy.

    Returns:
        health: {(category, subcategory): ClusterHealth}
        ghosts: list of GhostNode for red clusters and yellow clusters missing a pillar
    """
    # Group articles by subcategory
    subcat_articles: dict[tuple[str, str], list[dict]] = {}
    for node, data in g.nodes(data=True):
        key = (data["primary_category"], data["primary_subcategory"])
        subcat_articles.setdefault(key, []).append(data)

    health: dict[tuple[str, str], ClusterHealth] = {}
    ghosts: list[GhostNode] = []

    for _, row in taxonomy.iterrows():
        key = (str(row["category"]), str(row["subcategory"]))
        articles = subcat_articles.get(key, [])

        if not articles:
            health[key] = ClusterHealth.RED
            ghosts.append(
                GhostNode(
                    label=f"Gap: {key[0]} / {key[1]}",
                    category=key[0],
                    subcategory=key[1],
                    ghost_type="missing_subcategory",
                )
            )
            continue

        has_pillar = any(a["word_count"] >= 2500 for a in articles)
        has_supporting = len(articles) >= 3  # pillar + ≥2 supporting
        has_product_link = any(g.nodes[n].get("products_count", 0) > 0
                               for n in g.nodes()
                               if g.nodes[n].get("primary_subcategory") == key[1]
                               and g.nodes[n].get("primary_category") == key[0])

        if has_pillar and has_supporting and has_product_link:
            health[key] = ClusterHealth.GREEN
        else:
            health[key] = ClusterHealth.YELLOW
            if not has_pillar:
                ghosts.append(
                    GhostNode(
                        label=f"Missing pillar: {key[0]} / {key[1]}",
                        category=key[0],
                        subcategory=key[1],
                        ghost_type="missing_pillar",
                    )
                )

    return health, ghosts
