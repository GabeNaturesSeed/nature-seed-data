"""Write diagnostic CSVs from graph metrics and coverage analysis."""

from pathlib import Path

import networkx as nx
import pandas as pd

from naturesseed_pipeline.content_map.coverage import ClusterHealth, GhostNode
from naturesseed_pipeline.content_map.graph import ArticleMetrics


def export_csvs(
    g: nx.DiGraph,
    metrics: dict[int, ArticleMetrics],
    health: dict[tuple[str, str], ClusterHealth],
    ghosts: list[GhostNode],
    output_dir: Path,
) -> None:
    """Write orphans.csv, consolidation-candidates.csv, depth-violations.csv, coverage-gaps.csv."""
    output_dir.mkdir(parents=True, exist_ok=True)
    node_data = {n: g.nodes[n] for n in g.nodes()}

    # orphans.csv
    orphan_rows = [
        {
            "content_id": m.content_id,
            "title": node_data[m.content_id]["title"],
            "url": node_data[m.content_id]["url"],
            "primary_category": node_data[m.content_id]["primary_category"],
            "primary_subcategory": node_data[m.content_id]["primary_subcategory"],
        }
        for m in metrics.values()
        if m.is_orphan
    ]
    pd.DataFrame(orphan_rows).to_csv(output_dir / "orphans.csv", index=False)

    # consolidation-candidates.csv
    cand_rows = [
        {
            "candidate_id": m.content_id,
            "candidate_title": node_data[m.content_id]["title"],
            "survivor_id": m.consolidate_into_id,
            "survivor_title": node_data[m.consolidate_into_id]["title"]
            if m.consolidate_into_id is not None
            else "",
            "subcategory": node_data[m.content_id]["primary_subcategory"],
        }
        for m in metrics.values()
        if m.is_consolidation_candidate
    ]
    pd.DataFrame(cand_rows).to_csv(output_dir / "consolidation-candidates.csv", index=False)

    # depth-violations.csv — unreachable non-orphans + depth > 3
    violation_rows = [
        {
            "content_id": m.content_id,
            "title": node_data[m.content_id]["title"],
            "url": node_data[m.content_id]["url"],
            "link_depth": m.link_depth,
        }
        for m in metrics.values()
        if (m.link_depth == -1 and not m.is_orphan) or m.link_depth > 3
    ]
    pd.DataFrame(violation_rows).to_csv(output_dir / "depth-violations.csv", index=False)

    # coverage-gaps.csv
    gap_rows = [
        {
            "category": key[0],
            "subcategory": key[1],
            "health": h.value,
            "ghost_type": next(
                (gh.ghost_type for gh in ghosts if gh.category == key[0] and gh.subcategory == key[1]),
                "",
            ),
        }
        for key, h in health.items()
        if h != ClusterHealth.GREEN
    ]
    pd.DataFrame(gap_rows).to_csv(output_dir / "coverage-gaps.csv", index=False)
