"""Build and export the Plotly 3D internal link map."""

from pathlib import Path
from typing import Any

import networkx as nx
import plotly.graph_objects as go

from naturesseed_pipeline.content_map.coverage import ClusterHealth, GhostNode
from naturesseed_pipeline.content_map.graph import ArticleMetrics

# Distinct colors for up to 12 top-level categories
_PALETTE = [
    "#2ECC71", "#3498DB", "#E67E22", "#9B59B6", "#E74C3C",
    "#1ABC9C", "#F39C12", "#2980B9", "#D35400", "#7F8C8D",
    "#27AE60", "#8E44AD",
]


def _assign_colors(categories: list[str]) -> dict[str, str]:
    unique = sorted(set(categories))
    return {cat: _PALETTE[i % len(_PALETTE)] for i, cat in enumerate(unique)}


def build_and_export(
    g: nx.DiGraph,
    metrics: dict[int, ArticleMetrics],
    health: dict[tuple[str, str], ClusterHealth],
    ghosts: list[GhostNode],
    output_path: Path,
) -> None:
    """Compute 3D layout, build Plotly figure, and write self-contained HTML."""
    import random

    # 3D spring layout — same-category nodes will cluster loosely
    pos3d = nx.spring_layout(g, dim=3, seed=42, k=0.8)

    node_ids = list(g.nodes())
    node_data = {n: g.nodes[n] for n in node_ids}
    categories = [node_data[n]["primary_category"] for n in node_ids]
    color_map = _assign_colors(categories)

    # Group nodes by category for per-category traces (legend grouping)
    cat_groups: dict[str, list[int]] = {}
    for nid in node_ids:
        cat = node_data[nid]["primary_category"]
        cat_groups.setdefault(cat, []).append(nid)

    traces: list[Any] = []

    # ── Edge trace ────────────────────────────────────────────────────────────
    ex, ey, ez = [], [], []
    for src, tgt in g.edges():
        x0, y0, z0 = pos3d[src]
        x1, y1, z1 = pos3d[tgt]
        ex += [x0, x1, None]
        ey += [y0, y1, None]
        ez += [z0, z1, None]

    traces.append(go.Scatter3d(
        x=ex, y=ey, z=ez,
        mode="lines",
        line=dict(width=1, color="rgba(180,180,180,0.25)"),
        hoverinfo="none",
        name="Links",
        showlegend=True,
    ))

    # ── Node traces (one per category) ────────────────────────────────────────
    for cat, nids in sorted(cat_groups.items()):
        x, y, z, sizes, texts = [], [], [], [], []
        for nid in nids:
            coords = pos3d[nid]
            x.append(coords[0])
            y.append(coords[1])
            z.append(coords[2])
            m = metrics[nid]
            size = max(4, min(20, 4 + m.inbound_count * 2))
            sizes.append(size)
            depth_str = str(m.link_depth) if m.link_depth >= 0 else "unreachable"
            flags = []
            if m.is_orphan:
                flags.append("ORPHAN")
            if m.is_consolidation_candidate:
                flags.append(f"CONSOLIDATE → {m.consolidate_into_id}")
            if m.link_depth > 3 or (m.link_depth == -1 and not m.is_orphan):
                flags.append("DEPTH VIOLATION")
            flag_str = " | ".join(flags) if flags else "OK"
            texts.append(
                f"<b>{node_data[nid]['title']}</b><br>"
                f"Category: {node_data[nid]['primary_category']}<br>"
                f"Subcategory: {node_data[nid]['primary_subcategory']}<br>"
                f"Words: {node_data[nid]['word_count']}<br>"
                f"Inbound: {m.inbound_count} | Outbound: {m.outbound_count}<br>"
                f"Link depth: {depth_str}<br>"
                f"Status: {flag_str}"
            )

        traces.append(go.Scatter3d(
            x=x, y=y, z=z,
            mode="markers",
            marker=dict(
                size=sizes,
                color=color_map[cat],
                opacity=0.85,
                line=dict(width=0.5, color="white"),
            ),
            text=texts,
            hovertemplate="%{text}<extra></extra>",
            name=cat,
        ))

    # ── Consolidation candidate overlay ───────────────────────────────────────
    cx, cy, cz, ctexts = [], [], [], []
    for nid in node_ids:
        if metrics[nid].is_consolidation_candidate:
            coords = pos3d[nid]
            cx.append(coords[0])
            cy.append(coords[1])
            cz.append(coords[2])
            ctexts.append(f"Consolidate: {node_data[nid]['title']}")

    traces.append(go.Scatter3d(
        x=cx, y=cy, z=cz,
        mode="markers",
        marker=dict(
            size=14,
            color="rgba(0,0,0,0)",
            line=dict(width=3, color="red"),
        ),
        text=ctexts,
        hovertemplate="%{text}<extra></extra>",
        name="Consolidation Candidates",
        visible=False,
    ))

    # ── Ghost nodes (coverage gaps) ───────────────────────────────────────────
    random.seed(1)
    cat_centroids: dict[str, tuple[float, float, float]] = {}
    for cat, nids in cat_groups.items():
        xs = [pos3d[n][0] for n in nids]
        ys = [pos3d[n][1] for n in nids]
        zs = [pos3d[n][2] for n in nids]
        cat_centroids[cat] = (sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs))

    gx, gy, gz_, gtexts, gcolors = [], [], [], [], []
    for ghost in ghosts:
        centroid = cat_centroids.get(ghost.category, (0.0, 0.0, 0.0))
        gx.append(centroid[0] + random.uniform(-0.1, 0.1))
        gy.append(centroid[1] + random.uniform(-0.1, 0.1))
        gz_.append(centroid[2] + random.uniform(-0.1, 0.1))
        gtexts.append(ghost.label)
        gcolors.append(color_map.get(ghost.category, "#999999"))

    traces.append(go.Scatter3d(
        x=gx, y=gy, z=gz_,
        mode="markers",
        marker=dict(
            size=8,
            color="rgba(0,0,0,0)",
            line=dict(width=2, color=gcolors),
            opacity=0.5,
        ),
        text=gtexts,
        hovertemplate="%{text}<extra></extra>",
        name="Coverage Gaps",
        visible=False,
    ))

    # ── Trace index map for buttons ───────────────────────────────────────────
    n_cat_traces = len(cat_groups)
    total = len(traces)
    edges_idx = 0
    node_trace_indices = list(range(1, 1 + n_cat_traces))
    cand_idx = total - 2
    ghost_idx = total - 1

    def visibility(
        show_edges: bool = True,
        show_nodes: bool = True,
        show_cands: bool = False,
        show_ghosts: bool = False,
    ) -> list[bool]:
        v = [False] * total
        if show_edges:
            v[edges_idx] = True
        if show_nodes:
            for i in node_trace_indices:
                v[i] = True
        v[cand_idx] = show_cands
        v[ghost_idx] = show_ghosts
        return v

    fig = go.Figure(data=traces)
    fig.update_layout(
        title="Nature's Seed — Internal Link Map",
        scene=dict(
            xaxis=dict(showticklabels=False, title=""),
            yaxis=dict(showticklabels=False, title=""),
            zaxis=dict(showticklabels=False, title=""),
            bgcolor="rgb(15,15,25)",
        ),
        paper_bgcolor="rgb(15,15,25)",
        font=dict(color="white"),
        legend=dict(bgcolor="rgba(0,0,0,0.4)", font=dict(size=11)),
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=0.01, y=1.08,
                showactive=True,
                buttons=[
                    dict(
                        label="All Articles",
                        method="update",
                        args=[{"visible": visibility(True, True, False, False)}],
                    ),
                    dict(
                        label="+ Consolidation Candidates",
                        method="update",
                        args=[{"visible": visibility(True, True, True, False)}],
                    ),
                    dict(
                        label="+ Coverage Gaps",
                        method="update",
                        args=[{"visible": visibility(True, True, False, True)}],
                    ),
                    dict(
                        label="All Layers",
                        method="update",
                        args=[{"visible": visibility(True, True, True, True)}],
                    ),
                ],
            )
        ],
        margin=dict(l=0, r=0, t=60, b=0),
        height=800,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path), include_plotlyjs=True)
