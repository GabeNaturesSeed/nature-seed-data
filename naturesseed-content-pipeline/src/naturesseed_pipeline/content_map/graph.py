"""Build directed link graph and compute per-article metrics."""

from dataclasses import dataclass

import networkx as nx
import pandas as pd


@dataclass
class ArticleMetrics:
    content_id: int
    inbound_count: int
    outbound_count: int
    link_depth: int  # BFS hops from nearest hub; -1 = unreachable
    is_orphan: bool
    is_consolidation_candidate: bool
    consolidate_into_id: int | None


def build_graph(articles: pd.DataFrame, edges: pd.DataFrame) -> nx.DiGraph:
    """Build a directed graph: nodes = articles, edges = internal links."""
    g = nx.DiGraph()
    for _, row in articles.iterrows():
        g.add_node(
            int(row["content_id"]),
            title=str(row["title"]),
            url=str(row["url"]),
            word_count=int(row["word_count"]),
            products_count=int(row["products_count"]),
            primary_category=str(row["primary_category"]),
            primary_subcategory=str(row["primary_subcategory"]),
        )
    valid = set(g.nodes())
    for _, row in edges.iterrows():
        src, tgt = int(row["source_id"]), int(row["target_id"])
        if src in valid and tgt in valid:
            g.add_edge(src, tgt, anchor_text=str(row.get("anchor_text", "")))
    return g


def compute_metrics(g: nx.DiGraph) -> dict[int, ArticleMetrics]:
    """Compute inbound/outbound counts, link depth, orphan flag, and consolidation candidates."""
    in_deg = dict(g.in_degree())
    out_deg = dict(g.out_degree())

    # Link depth: BFS from hub articles (inbound >= 3) through original directed graph
    hubs = [n for n, d in in_deg.items() if d >= 3]
    depths: dict[int, int] = {}
    for hub in hubs:
        for node, dist in nx.single_source_shortest_path_length(g, hub).items():
            if node not in depths or dist < depths[node]:
                depths[node] = dist

    # Consolidation candidates: group by subcategory
    subcat_groups: dict[str, list[tuple[int, int]]] = {}  # subcat → [(word_count, content_id)]
    for node, data in g.nodes(data=True):
        subcat = data["primary_subcategory"]
        subcat_groups.setdefault(subcat, []).append((data["word_count"], node))

    candidates: dict[int, int] = {}  # candidate_id → survivor_id
    for subcat, group in subcat_groups.items():
        if len(group) < 2:
            continue
        max_wc = max(wc for wc, _ in group)
        for wc, node_id in group:
            if in_deg[node_id] < 3 and wc < 800 and wc < max_wc:
                # Survivor: highest inbound in same subcat (word_count as tiebreaker), excluding self
                others = [(in_deg[nid], wc2, nid) for wc2, nid in group if nid != node_id]
                if others:
                    candidates[node_id] = max(others)[2]

    return {
        node: ArticleMetrics(
            content_id=node,
            inbound_count=in_deg[node],
            outbound_count=out_deg[node],
            link_depth=depths.get(node, -1),
            is_orphan=in_deg[node] == 0,
            is_consolidation_candidate=node in candidates,
            consolidate_into_id=candidates.get(node),
        )
        for node in g.nodes()
    }
