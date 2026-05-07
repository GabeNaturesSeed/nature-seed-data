# Content Link Map — Design Spec
Date: 2026-05-07

## Purpose

Build a static 3D interactive visualization of Nature's Seed's internal linking structure across all 990 resource articles. The output is a strategic planning tool — a one-time audit that shows current link topology, topic cluster coverage, consolidation candidates, coverage gaps, and click depth violations. It is not a live dashboard.

---

## Inputs

All input files already exist under `docs/content-audit/2026-04-27/` and `docs/resource-classifier/`:

| File | Role |
|---|---|
| `per-article.csv` | 990 nodes — content_id, title, url, word_count, products_count, open_findings, critical_findings |
| `internal-linking.csv` | 1,297 edges — source_content_id, target_content_id, anchor_text, href |
| `classifications.csv` | Topic cluster per article — category, subcategory, article_count |
| `topic-map.csv` | Product connections per article — content_id, topic_slug, subtopic_slug, product_slug |
| `taxonomy-key.csv` | Full topic taxonomy — defines all categories and subcategories that should exist |

---

## Data Pipeline

1. **Load & merge** — join `per-article.csv` + `classifications.csv` on content_id to assign each article its topic cluster (category + subcategory)
2. **Build directed graph** — NetworkX DiGraph; nodes = articles, edges = internal links from `internal-linking.csv`
3. **Compute per-node metrics**
   - `inbound_count` — in-degree (drives node size)
   - `outbound_count` — out-degree
   - `click_depth` — BFS from homepage node; homepage identified by URL `naturesseed.com/`
   - `is_orphan` — inbound_count == 0
   - `consolidation_candidate` — see Consolidation Rules below
4. **3D layout** — NetworkX `spring_layout(dim=3)` with same-cluster attraction; fallback to ForceAtlas2 via `fa2` library for better cluster separation if spring layout produces poor separation
5. **Build ideal coverage layer** — from `taxonomy-key.csv`, compute missing pillar/supporting article slots as ghost nodes
6. **Render** — Plotly 3D scatter + line traces; export single self-contained `content-link-map.html`

---

## Visual Design

### Nodes

| Property | Mapping |
|---|---|
| Size | Inbound link count (min 4px orphan → max 20px top hub) |
| Color | Top-level category — one distinct color per category |
| Border | Solid = real article. Hollow/dashed = coverage gap (missing article) |
| Red outline | Consolidation candidate |
| Hover tooltip | Title, URL, category, subcategory, word count, inbound count, outbound count, click depth |

### Edges

| Property | Mapping |
|---|---|
| Color | Source node cluster color at 40% opacity |
| Thickness | Uniform 1px |
| Direction | Arrows indicating link direction |

### Layout Rules

- Force-directed 3D: same-cluster nodes attract, cross-cluster nodes repel
- Homepage node pinned at center of gravity
- Orphan nodes float to periphery naturally (no edges pulling them inward)
- Ghost/gap nodes placed at centroid of their cluster

---

## Ideal Coverage Map

Complete coverage for a subcategory = pillar article (1, 2,500+ words) + 2+ supporting articles + at least 1 article with a product link.

Cluster health colors:
- **Green** = pillar + 2+ supporting + product link present
- **Yellow** = subcategory exists but missing pillar, thin supporting count, or no product link
- **Red** = subcategory in taxonomy with zero articles (pure gap)

Ghost nodes represent specific missing article slots within yellow clusters.

---

## Consolidation Flagging Rules

A node is flagged as a consolidation candidate (red outline) when ALL of the following are true:
- Same subcategory as at least one other article
- Inbound internal links < 3
- Word count < 800
- Not the highest word-count article in that subcategory

Survivor = article in the same subcategory with the most inbound links (word count as tiebreaker).
Tooltip shows: "Consolidate into: [survivor title]"

---

## Click Depth Enforcement

- BFS from homepage node computes click depth for all reachable articles
- Articles at depth > 3 flagged with warning in tooltip
- Depth slider UI filter isolates all depth-4+ nodes

---

## UI Controls (inside the HTML output)

- Topic filter — toggle clusters on/off by top-level category
- Show orphans only — isolate zero-inbound nodes
- Show consolidation candidates — highlight red-outlined nodes
- Show coverage gaps — toggle ghost nodes on/off
- Search by title — highlight a single node and its direct connections
- Click depth slider — filter to nodes at depth N from homepage

---

## Output Files

All written to `docs/content-map/`:

| File | Description |
|---|---|
| `content-link-map.html` | Self-contained 3D interactive map |
| `consolidation-candidates.csv` | All flagged pairs: candidate_id, candidate_title, survivor_id, survivor_title, subcategory |
| `coverage-gaps.csv` | Subcategories missing pillar or supporting articles |
| `orphans.csv` | All zero-inbound articles: content_id, title, url, category, subcategory |
| `depth-violations.csv` | All articles > 3 clicks from homepage: content_id, title, url, click_depth |

---

## Script Location

`naturesseed-content-pipeline/src/content_map/build_map.py`

Single script. Run with: `python src/content_map/build_map.py`

No external data fetching required — reads only from existing CSVs.

---

## Dependencies

- `networkx`
- `plotly`
- `pandas`
- `fa2` (optional, for ForceAtlas2 layout)
