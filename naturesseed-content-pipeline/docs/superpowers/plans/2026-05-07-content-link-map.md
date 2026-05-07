# Content Link Map — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained 3D interactive HTML visualization of Nature's Seed's 990-article internal linking structure, surfacing orphans, consolidation candidates, coverage gaps, and link-depth violations.

**Architecture:** Python module reads four existing CSVs, builds a NetworkX directed graph, computes per-node metrics (inbound count, link depth, orphan flag, consolidation candidate), then renders a Plotly 3D scatter+line figure exported as a single HTML file alongside four diagnostic CSVs.

**Tech Stack:** Python 3.11, pandas, NetworkX 3.x, Plotly 5.x, pytest, structlog, Typer (existing CLI)

---

## Key Data Relationships

```
per-article.csv          content_id (1,2,3…sequential) → join key for edges
                         url contains ?p=<WP_POST_ID>  → extract for classifications join

internal-linking.csv     source_content_id / target_content_id → match content_id above
                         blank target_content_id = external link (skip for graph edges)

classifications.csv      post_id (WP ID: 444495…)      → join via extracted WP post ID
                         one article may have multiple rows (multiple subcategory assignments)
                         use FIRST row per post_id as primary category/subcategory

taxonomy-key.csv         category, subcategory, article_count → defines ideal coverage
```

**Link depth definition:** BFS hops from any "hub" article (inbound_count ≥ 3) through
the directed link graph. Depth -1 = unreachable from any hub. Flag depth > 3 as violation.
(We cannot compute true click-depth-from-homepage without crawling live site.)

---

## File Map

### Created
| Path | Responsibility |
|---|---|
| `src/naturesseed_pipeline/content_map/__init__.py` | Module marker |
| `src/naturesseed_pipeline/content_map/loader.py` | Load & merge CSVs → articles_df, edges_df, taxonomy_df |
| `src/naturesseed_pipeline/content_map/graph.py` | Build NetworkX DiGraph, compute ArticleMetrics per node |
| `src/naturesseed_pipeline/content_map/coverage.py` | Ideal coverage analysis → cluster health + ghost nodes |
| `src/naturesseed_pipeline/content_map/renderer.py` | Plotly 3D figure + HTML export |
| `src/naturesseed_pipeline/content_map/exporter.py` | Write 4 diagnostic CSVs |
| `tests/content_map/__init__.py` | Test module marker |
| `tests/content_map/fixtures/per_article_sample.csv` | 5-row fixture |
| `tests/content_map/fixtures/internal_linking_sample.csv` | 7-row fixture |
| `tests/content_map/fixtures/classifications_sample.csv` | 5-row fixture |
| `tests/content_map/fixtures/taxonomy_key_sample.csv` | 4-row fixture |
| `tests/content_map/test_loader.py` | Loader tests |
| `tests/content_map/test_graph.py` | Graph + metrics tests |
| `tests/content_map/test_coverage.py` | Coverage analysis tests |
| `tests/content_map/test_exporter.py` | CSV export tests |

### Modified
| Path | Change |
|---|---|
| `pyproject.toml` | Add `networkx>=3.0`, `plotly>=5.0` to dependencies |
| `src/naturesseed_pipeline/cli.py` | Add `map_app` Typer group with `build` command |

### Output (generated at runtime)
```
docs/content-map/
    content-link-map.html
    consolidation-candidates.csv
    coverage-gaps.csv
    orphans.csv
    depth-violations.csv
```

---

## Task 1: Add Dependencies + Module Skeleton

**Files:**
- Modify: `pyproject.toml`
- Create: `src/naturesseed_pipeline/content_map/__init__.py`
- Create: `tests/content_map/__init__.py`

- [ ] **Step 1: Add dependencies to pyproject.toml**

Find the `[project]` dependencies list and add two entries:

```toml
"networkx>=3.0",
"plotly>=5.0",
```

- [ ] **Step 2: Install new dependencies**

```bash
cd "$(git rev-parse --show-toplevel)"
pip install "networkx>=3.0" "plotly>=5.0"
```

Expected: both packages install without error.

- [ ] **Step 3: Create module `__init__.py` files**

`src/naturesseed_pipeline/content_map/__init__.py`:
```python
"""3D internal link map — strategic content planning tool."""
```

`tests/content_map/__init__.py`:
```python
```

- [ ] **Step 4: Verify imports work**

```bash
python -c "import networkx; import plotly; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/naturesseed_pipeline/content_map/__init__.py tests/content_map/__init__.py
git commit -m "feat: scaffold content_map module, add networkx+plotly deps"
```

---

## Task 2: Create Fixture CSV Files

**Files:**
- Create: `tests/content_map/fixtures/per_article_sample.csv`
- Create: `tests/content_map/fixtures/internal_linking_sample.csv`
- Create: `tests/content_map/fixtures/classifications_sample.csv`
- Create: `tests/content_map/fixtures/taxonomy_key_sample.csv`

These fixtures drive all unit tests. Design choices:
- Articles 1–3: Lawn Care cluster, mutually linked, article 3 is a consolidation candidate
- Articles 4–5: Wildflowers cluster, article 4 is an orphan (no inbound)

- [ ] **Step 1: Create `tests/content_map/fixtures/` directory and fixtures**

`tests/content_map/fixtures/per_article_sample.csv`:
```
content_id,title,url,post_type,status,word_count,products_count,open_findings,critical_findings
1,Overseeding Guide,https://naturesseed.com/?p=100,post,draft,2500,2,5,1
2,Tall Fescue Basics,https://naturesseed.com/?p=101,post,draft,900,1,3,0
3,Kentucky Bluegrass Care,https://naturesseed.com/?p=102,post,draft,600,0,2,0
4,Wildflower Meadow Intro,https://naturesseed.com/?p=103,post,draft,1800,1,4,0
5,Native Plant Selection,https://naturesseed.com/?p=104,post,draft,700,0,1,0
```

`tests/content_map/fixtures/internal_linking_sample.csv`:
```
source_content_id,target_content_id,anchor_text,href
1,2,tall fescue,https://naturesseed.com/?p=101
1,3,kentucky bluegrass,https://naturesseed.com/?p=102
2,1,overseeding,https://naturesseed.com/?p=100
2,3,bluegrass,https://naturesseed.com/?p=102
3,1,overseeding guide,https://naturesseed.com/?p=100
4,5,native plants,https://naturesseed.com/?p=104
1,,Nature's Seed,https://naturesseed.com/
```

`tests/content_map/fixtures/classifications_sample.csv`:
```
post_id,title,url,category,subcategory,species_mentioned,products_mentioned,has_link
100,Overseeding Guide,https://naturesseed.com/?p=100,Lawn Care,Overseeding,Tall Fescue,,
101,Tall Fescue Basics,https://naturesseed.com/?p=101,Lawn Care,Cool-Season Grasses,Tall Fescue,,
102,Kentucky Bluegrass Care,https://naturesseed.com/?p=102,Lawn Care,Cool-Season Grasses,Kentucky Bluegrass,,
103,Wildflower Meadow Intro,https://naturesseed.com/?p=103,Wildflowers,Native Species Selection,,,
104,Native Plant Selection,https://naturesseed.com/?p=104,Wildflowers,Native Species Selection,,,
```

`tests/content_map/fixtures/taxonomy_key_sample.csv`:
```
category,subcategory,article_count
Lawn Care,Overseeding,27
Lawn Care,Cool-Season Grasses,16
Wildflowers,Native Species Selection,21
Pasture Management,Overseeding,12
```

- [ ] **Step 2: Commit**

```bash
git add tests/content_map/fixtures/
git commit -m "test: add content_map fixture CSVs"
```

---

## Task 3: Data Loader

**Files:**
- Create: `src/naturesseed_pipeline/content_map/loader.py`
- Create: `tests/content_map/test_loader.py`

**Expected behavior:**
- Extracts WP post_id from `?p=<ID>` in per-article URL
- Joins per-article with classifications on WP post_id
- Returns articles_df with columns: `content_id, post_id, title, url, word_count, products_count, primary_category, primary_subcategory`
- Returns edges_df with only article-to-article edges (blank target_content_id dropped)
- Returns taxonomy_df unmodified from taxonomy-key.csv

- [ ] **Step 1: Write failing tests**

`tests/content_map/test_loader.py`:
```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd "$(git rev-parse --show-toplevel)"
pytest tests/content_map/test_loader.py -v 2>&1 | head -30
```

Expected: `ImportError` or `ModuleNotFoundError` — loader.py does not exist yet.

- [ ] **Step 3: Implement `loader.py`**

`src/naturesseed_pipeline/content_map/loader.py`:
```python
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/content_map/test_loader.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/naturesseed_pipeline/content_map/loader.py tests/content_map/test_loader.py
git commit -m "feat: content_map loader — merge per-article + classifications CSVs"
```

---

## Task 4: Graph Builder + Metrics

**Files:**
- Create: `src/naturesseed_pipeline/content_map/graph.py`
- Create: `tests/content_map/test_graph.py`

**ArticleMetrics fields:**
- `inbound_count` — in-degree
- `outbound_count` — out-degree
- `link_depth` — BFS hops from nearest hub (inbound ≥ 3); -1 = unreachable
- `is_orphan` — inbound_count == 0
- `is_consolidation_candidate` — same subcategory + inbound < 3 + word_count < 800 + not max word_count in subcategory
- `consolidate_into_id` — content_id of survivor article (or None)

**Fixture expected values:**
- Article 1: inbound=2 (from 2,3), outbound=2 (to 2,3), link_depth=0 (is a hub? No — inbound=2 < 3. So depth=-1 unless reachable from another hub. No hubs in fixture → all depth=-1)
- With no hubs in fixture, all link_depth=-1. This is intentional — tests should reflect this.
- Article 4: inbound=0, is_orphan=True
- Article 3: inbound=2, word_count=600 (<800), not max in Cool-Season Grasses (article 2 has 900) → consolidation_candidate=True, consolidate_into_id=2

- [ ] **Step 1: Write failing tests**

`tests/content_map/test_graph.py`:
```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/content_map/test_graph.py -v 2>&1 | head -20
```

Expected: `ImportError` — graph.py not yet created.

- [ ] **Step 3: Implement `graph.py`**

`src/naturesseed_pipeline/content_map/graph.py`:
```python
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/content_map/test_graph.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/naturesseed_pipeline/content_map/graph.py tests/content_map/test_graph.py
git commit -m "feat: content_map graph builder + ArticleMetrics computation"
```

---

## Task 5: Coverage Analysis

**Files:**
- Create: `src/naturesseed_pipeline/content_map/coverage.py`
- Create: `tests/content_map/test_coverage.py`

**Cluster health rules:**
- Green: ≥1 article with word_count ≥ 2500 (pillar) AND ≥2 supporting articles AND ≥1 article with products_count > 0
- Yellow: subcategory has articles but fails any green criterion
- Red: subcategory exists in taxonomy but has zero articles in our corpus

**Ghost nodes:** one ghost per red subcategory, positioned at centroid of its category cluster (or at origin if category has no articles). Also one ghost labeled "Missing pillar" per yellow subcategory that lacks a ≥2500-word article.

- [ ] **Step 1: Write failing tests**

`tests/content_map/test_coverage.py`:
```python
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
    # → yellow (needs ≥2 supporting articles)
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/content_map/test_coverage.py -v 2>&1 | head -20
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `coverage.py`**

`src/naturesseed_pipeline/content_map/coverage.py`:
```python
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/content_map/test_coverage.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/naturesseed_pipeline/content_map/coverage.py tests/content_map/test_coverage.py
git commit -m "feat: coverage analysis — cluster health + ghost nodes"
```

---

## Task 6: CSV Exporters

**Files:**
- Create: `src/naturesseed_pipeline/content_map/exporter.py`
- Create: `tests/content_map/test_exporter.py`

**Four output CSVs:**
- `orphans.csv` — content_id, title, url, primary_category, primary_subcategory
- `consolidation-candidates.csv` — candidate_id, candidate_title, survivor_id, survivor_title, subcategory
- `depth-violations.csv` — content_id, title, url, link_depth (link_depth > 3 OR link_depth == -1 AND NOT orphan)
- `coverage-gaps.csv` — category, subcategory, health, ghost_type

- [ ] **Step 1: Write failing tests**

`tests/content_map/test_exporter.py`:
```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/content_map/test_exporter.py -v 2>&1 | head -20
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `exporter.py`**

`src/naturesseed_pipeline/content_map/exporter.py`:
```python
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/content_map/test_exporter.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
pytest tests/content_map/ -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/naturesseed_pipeline/content_map/exporter.py tests/content_map/test_exporter.py
git commit -m "feat: content_map CSV exporters — orphans, consolidation, gaps, violations"
```

---

## Task 7: Plotly 3D Renderer

**Files:**
- Create: `src/naturesseed_pipeline/content_map/renderer.py`

No unit tests for the renderer — testing Plotly figure internals is brittle. The integration test in Task 9 verifies the HTML output is non-empty and contains expected content.

**Design:**
- One `go.Scatter3d` trace per top-level category (so the legend shows category names)
- One `go.Scatter3d` trace for edges (all edges combined as broken line segments)
- One `go.Scatter3d` trace for consolidation candidates (red hollow circles overlay)
- One `go.Scatter3d` trace for ghost nodes (hollow, hidden by default)
- Plotly `updatemenus` buttons to toggle: orphans only, consolidation candidates, coverage gaps
- Export with `fig.write_html(path, include_plotlyjs=True)` for fully self-contained output

- [ ] **Step 1: Implement `renderer.py`**

`src/naturesseed_pipeline/content_map/renderer.py`:
```python
"""Build and export the Plotly 3D internal link map."""

from pathlib import Path

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
    import networkx as nx

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

    traces: list[go.BaseTraceType] = []

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
    # Position at mean coords of their category cluster, with small random offset
    import random
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
    # traces[0] = edges
    # traces[1..N-2] = category node traces
    # traces[-2] = consolidation overlay
    # traces[-1] = ghost nodes
    n_cat_traces = len(cat_groups)
    total = len(traces)
    edges_idx = 0
    node_trace_indices = list(range(1, 1 + n_cat_traces))
    cand_idx = total - 2
    ghost_idx = total - 1

    def visibility(show_edges=True, show_nodes=True, show_cands=False, show_ghosts=False):
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
```

- [ ] **Step 2: Verify no import errors**

```bash
python -c "from naturesseed_pipeline.content_map.renderer import build_and_export; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/naturesseed_pipeline/content_map/renderer.py
git commit -m "feat: Plotly 3D renderer — node/edge/ghost traces + filter buttons"
```

---

## Task 8: CLI Command + End-to-End Run

**Files:**
- Modify: `src/naturesseed_pipeline/cli.py`

- [ ] **Step 1: Add `map_app` Typer group to `cli.py`**

After the last `app.add_typer(...)` call and before the `if __name__ == "__main__"` block (or EOF), add:

```python
map_app = typer.Typer(help="Content link map — 3D internal linking visualization.")
app.add_typer(map_app, name="map")


@map_app.command("build")
def map_build(
    audit_dir: Path = typer.Option(
        ...,
        "--audit-dir",
        help="Directory containing per-article.csv and internal-linking.csv",
    ),
    classifier_dir: Path = typer.Option(
        ...,
        "--classifier-dir",
        help="Directory containing classifications.csv and taxonomy-key.csv",
    ),
    output_dir: Path = typer.Option(
        Path("docs/content-map"),
        "--output-dir",
        help="Directory for HTML and CSV outputs",
    ),
) -> None:
    """Build 3D internal link map from existing audit CSVs."""
    import structlog
    from naturesseed_pipeline.content_map.loader import load_data
    from naturesseed_pipeline.content_map.graph import build_graph, compute_metrics
    from naturesseed_pipeline.content_map.coverage import build_coverage_layer
    from naturesseed_pipeline.content_map.renderer import build_and_export
    from naturesseed_pipeline.content_map.exporter import export_csvs

    log = structlog.get_logger()
    log.info("loading data", audit_dir=str(audit_dir), classifier_dir=str(classifier_dir))

    articles, edges, taxonomy = load_data(audit_dir=audit_dir, classifier_dir=classifier_dir)
    log.info("data loaded", articles=len(articles), edges=len(edges))

    g = build_graph(articles, edges)
    log.info("graph built", nodes=g.number_of_nodes(), edges=g.number_of_edges())

    metrics = compute_metrics(g)
    orphan_count = sum(1 for m in metrics.values() if m.is_orphan)
    cand_count = sum(1 for m in metrics.values() if m.is_consolidation_candidate)
    log.info("metrics computed", orphans=orphan_count, consolidation_candidates=cand_count)

    health, ghosts = build_coverage_layer(g, taxonomy)
    log.info("coverage analyzed", ghosts=len(ghosts))

    export_csvs(g, metrics, health, ghosts, output_dir=output_dir)
    log.info("CSVs written", output_dir=str(output_dir))

    html_path = output_dir / "content-link-map.html"
    build_and_export(g, metrics, health, ghosts, output_path=html_path)
    log.info("HTML map written", path=str(html_path))

    console.print(f"[green]Map written to {html_path}[/green]")
    console.print(f"  Orphans: {orphan_count}")
    console.print(f"  Consolidation candidates: {cand_count}")
    console.print(f"  Coverage ghosts: {len(ghosts)}")
```

Also add `from pathlib import Path` to the imports at the top of `cli.py` if not already present.

- [ ] **Step 2: Run the full test suite**

```bash
pytest tests/content_map/ -v
```

Expected: all tests PASS.

- [ ] **Step 3: Run end-to-end build against real data**

```bash
BASE="/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/naturesseed-content-pipeline"
python -m naturesseed_pipeline.cli map build \
  --audit-dir "$BASE/docs/content-audit/2026-04-27" \
  --classifier-dir "$BASE/docs/resource-classifier" \
  --output-dir "$BASE/docs/content-map"
```

Expected output (approximate):
```
Map written to docs/content-map/content-link-map.html
  Orphans: <N>
  Consolidation candidates: <N>
  Coverage ghosts: <N>
```

- [ ] **Step 4: Open and inspect the HTML**

```bash
open "$BASE/docs/content-map/content-link-map.html"
```

Verify:
- 3D graph renders with colored clusters
- Hover tooltips show title, category, inbound count, link depth
- Button toggles work: "All Articles", "+ Consolidation Candidates", "+ Coverage Gaps", "All Layers"
- Node sizes vary (large hubs visible, small orphans visible)

- [ ] **Step 5: Spot-check a diagnostic CSV**

```bash
head -10 "$BASE/docs/content-map/orphans.csv"
head -10 "$BASE/docs/content-map/consolidation-candidates.csv"
```

Verify columns match spec and data looks reasonable.

- [ ] **Step 6: Commit**

```bash
git add src/naturesseed_pipeline/cli.py
git commit -m "feat: add 'nspipe map build' CLI command for 3D content link map"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Data pipeline (loader.py: per-article + classifications + edges + taxonomy)
- ✅ 3D force-directed graph (renderer.py: spring_layout dim=3)
- ✅ Node size = inbound links (renderer.py: size = 4 + inbound * 2)
- ✅ Node color = topic cluster (renderer.py: color_map by primary_category)
- ✅ Hover tooltip (renderer.py: title, category, subcategory, words, inbound, outbound, depth, status)
- ✅ Edges with direction (rendered as lines; Plotly 3D lines don't support arrows natively — cones would require separate trace, acceptable omission for MVP)
- ✅ Ghost nodes for coverage gaps (renderer.py: hollow markers, visible=False by default)
- ✅ Consolidation candidates overlay (renderer.py: red hollow circles, visible=False by default)
- ✅ UI filter buttons (renderer.py: updatemenus with 4 states)
- ✅ Click depth computation (graph.py: BFS from hubs)
- ✅ Four diagnostic CSVs (exporter.py)
- ✅ CLI command (cli.py: `nspipe map build`)
- ⚠️ Edge arrows: Plotly 3D lines don't natively support arrowheads. Accepted limitation — direction is implicit from the force layout clustering. Can be added as cone traces in a future iteration.
- ⚠️ Search by title / depth slider: deferred — requires injecting custom JS into Plotly HTML. The button toggles cover the primary use cases. Add in a future iteration.
