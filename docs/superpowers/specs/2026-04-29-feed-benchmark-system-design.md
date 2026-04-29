# Feed Benchmark & Platform Success System — Design Spec
_2026-04-29_

## Purpose

Build a seasonality-normalized, multi-dimensional feed health benchmark system across 8 channels (Walmart, Amazon, Google Merchant, Klaviyo, Shopper Approved, Reddit, Facebook, Pinterest). The output is an AI-agent directive system: per-platform guides + a master operating directive the agent reads monthly, executes improvements, and reports results to Gabe. No human review loop required for housekeeping tasks.

---

## Architecture

```
docs/feeds/
  guides/
    walmart.md
    amazon.md
    google_merchant.md
    klaviyo.md
    shopper_approved.md
    reddit.md
    facebook.md
    pinterest.md
  FEED_AGENT_DIRECTIVE.md     ← master monthly operating instructions

feeds/
  benchmark/
    score.py                  ← computes 3-dimension scores, appends to benchmark.json
    benchmark.json            ← committed to git (weekly snapshots, full history)

docs/data/
  seasonality.json            ← existing, read-only input

.github/workflows/
  feed-audit.yml              ← existing workflow; score.py added as a step
```

**Daily data flow:**
1. `build_feed_master.py` pulls WC catalog → `feed_master.json`
2. `run_audit.py` runs all 8 adapters → `AdapterResult` objects
3. `score.py` reads adapter results + `seasonality.json` → computes scores → appends snapshot to `benchmark.json` → injects "Feed Scorecard" section into today's digest
4. Everything committed to git by existing GH Actions step

**Monthly agent flow:**
1. Agent reads `FEED_AGENT_DIRECTIVE.md`
2. Pulls latest `benchmark.json` + all platform guides
3. For each Red/Amber dimension, executes top item from that channel's improvement checklist
4. Commits changes, sends Gabe a summary (what ran, what moved, what's still open)
5. Updates directive if results warrant a pivot

---

## Scoring Model

Three dimensions tracked independently per channel. No single composite is the primary signal — dimensions are read separately.

### 1. Coverage Score (0–100) — seasonality-adjusted

```python
raw_ratio = channel_total / wc_total
expected_ratio = channel_baseline_coverage × seasonality_index
score = min(100, (raw_ratio / expected_ratio) × 100)
```

- `channel_baseline_coverage`: learned from first 4 weeks of data per channel, then stable
- `seasonality_index`: `weekly_baselines[iso_week].revenue_mean / max(revenue_mean across all weeks)`
- Rationale: missing SKUs in off-season may be intentional (stage items, seasonal listings); same gap at peak is revenue at risk

**Thresholds:** ≥90 Green | 70–89 Amber | <70 Red

### 2. Quality Score (0–100) — seasonality-flat

```python
score = (1 - incomplete_count / channel_total) × 100
```

- No seasonal adjustment. A missing GTIN or image is always a problem regardless of week.
- `incomplete_count` = products failing `get_required_fields()` check per adapter
- Discovery channels (Reddit, Facebook, Pinterest, Shopper Approved): quality = feed completeness only

**Thresholds:** ≥95 Green | 80–94 Amber | <80 Red

### 3. Drift Score (0–100) — seasonality-adjusted tolerance

```python
weighted_drift = sum(
    drift_count_price × 2.0 +
    drift_count_stock × 1.5
) / channel_total × 100

score = max(0, 100 - weighted_drift)
```

- Price drift weight 2.0: wrong prices cost money and erode buy box
- Stock drift weight 1.5: overselling/underselling hurts fulfillment metrics
- During peak (index > 0.85): digest flags "tighten sync cadence"
- During off-season (index < 0.5): digest notes "acceptable lag — review monthly"
- Discovery channels (no price/stock): drift score = 100 (N/A, not penalized)

**Thresholds:** ≥90 Green | 75–89 Amber | <75 Red

### Composite (trend tracking only)

```python
composite = coverage × 0.40 + quality × 0.35 + drift × 0.25
```

Used only for week-over-week trend lines in `benchmark.json`. Not the primary decision signal.

---

## Seasonality Normalization

```python
import json
from datetime import date

with open("docs/data/seasonality.json") as f:
    idx = json.load(f)

iso_week = str(date.today().isocalendar()[1])
baselines = idx["weekly_baselines"]
max_revenue = max(b["revenue_mean"] for b in baselines.values())
current_revenue_mean = baselines[iso_week]["revenue_mean"]
seasonality_index = current_revenue_mean / max_revenue  # 0.0–1.0

season_label = idx["index"]["label"]  # "Deep Off-Season", "Peak Season", etc.
```

The `seasonality.json` is updated by the existing `seasonality_hit_report.py` — no new data pipeline needed.

---

## benchmark.json Schema

```json
{
  "meta": {
    "schema_version": 1,
    "channel_baselines": {
      "walmart": {"coverage": 0.45},
      "amazon": {"coverage": 0.90},
      "google_merchant": {"coverage": 0.70},
      "klaviyo": {"coverage": 0.95},
      "shopper_approved": {"coverage": 0.99},
      "reddit": {"coverage": 1.0},
      "facebook": {"coverage": 0.85},
      "pinterest": {"coverage": 1.0}
    }
  },
  "snapshots": [
    {
      "date": "2026-04-29",
      "iso_week": 18,
      "seasonality_index": 0.537,
      "season_label": "Deep Off-Season",
      "channels": {
        "walmart": {
          "coverage_score": 85,
          "quality_score": 72,
          "drift_score": 68,
          "composite": 76,
          "raw": {
            "channel_total": 200,
            "wc_total": 478,
            "incomplete_count": 55,
            "drift_price": 8,
            "drift_stock": 192
          }
        }
      }
    }
  ]
}
```

History accumulates indefinitely — one snapshot per day. Git history provides the change log.

---

## Digest Integration

After the existing Summary table and Action Items, `score.py` appends a **Feed Scorecard** section:

```markdown
## Feed Scorecard — Week 18 (Deep Off-Season, index 0.54)

| Channel         | Coverage | Quality | Drift | Trend |
|----------------|----------|---------|-------|-------|
| walmart        | 85 🟡    | 72 🔴   | 68 🔴 | ↓     |
| amazon         | —        | —       | —     | ERROR |
| google_merchant | 94 🟢   | 97 🟢   | 100 🟢| →     |
| klaviyo        | —        | —       | —     | ERROR |
| shopper_approved| 100 🟢  | 100 🟢  | 85 🟡 | →     |
| reddit         | —        | —       | —     | ERROR |
| facebook       | 91 🟢    | 88 🟡   | 100 🟢| ↑ NEW |
| pinterest      | —        | —       | —     | STUB  |

_Seasonality note: off-season coverage expectations relaxed. Quality scores held to full standard._
```

Trend arrow = composite vs 4-week rolling average (↑ improving, → stable, ↓ declining).

---

## Per-Platform Guide Structure

Each `docs/feeds/guides/{channel}.md` follows this template:

```markdown
# {Channel} — Feed Success Guide
_Last updated: YYYY-MM-DD_

## What Success Looks Like
[Platform-specific definition. For commerce channels: coverage %, conversion signals.
For discovery channels: coverage % + field completeness only.]

## Required Fields & Why They Matter
[Per-field explanation of what happens when it's missing on this platform.]

## Known Failure Modes
[Common errors, with diagnosis and fix for each.]

## Seasonal Behavior
[How this channel's algorithm/visibility responds to planting season demand shifts.]

## Improvement Checklist (ordered by impact)
- [ ] Item 1 — highest ROI fix
- [ ] Item 2
...

## How to Measure Progress
[What metric moves when this channel improves. What to watch in benchmark.json.]
```

Content is researched via Opus 4.7 (platform best practices + algorithm behavior) merged with current feed data (actual gaps, SKU counts, field failure rates).

Guides are living docs. Agent appends "Last updated" timestamp and a change note whenever it pivots strategy based on observed results.

---

## Master Agent Directive

`docs/feeds/FEED_AGENT_DIRECTIVE.md` — the agent's monthly operating instructions:

```markdown
# Feed Agent — Monthly Operating Directive
_Last updated: YYYY-MM-DD | Next review: YYYY-MM-DD_

## Mission
Maintain feed health across all active channels. Execute improvement tasks autonomously.
Report results to Gabe. Pivot this document when results warrant.

## Monthly Workflow
1. Pull latest benchmark.json — identify all Red/Amber dimensions
2. For each Red dimension: execute top unchecked item from that channel's guide checklist
3. For each Amber dimension: log it, execute if < 2 items already in progress
4. Commit all changes
5. Send Gabe a report: [channel] [dimension] [score before → after] [what was done]
6. If a tactic produced no improvement after 2 cycles, mark it stale and try next item

## Priority Order (update as needed)
1. Walmart quality (GTINs, short descriptions)
2. Walmart drift (192 stock mismatches)
3. Amazon — resolve auth error
4. Klaviyo — resolve auth error
5. Facebook quality (image URLs, descriptions)
6. GMC GTINs (16 remaining)

## Standing Rules
- Never auto-push price changes without dry-run log committed first
- Coverage gaps below the seasonality-adjusted threshold: log only, do not alert Gabe
- Quality gaps: always act regardless of season
- If an adapter errors 3 days in a row: alert Gabe immediately
```

---

## Platforms In Scope for Research

| Channel | Research Focus | Performance Signal |
|---------|---------------|-------------------|
| Walmart | Listing quality score, buy box factors, content requirements | Coverage + Quality + Drift |
| Amazon | SP-API catalog completeness, ASIN matching, suppressed listings | Coverage + Quality + Drift |
| Google Merchant | Feed spec compliance, disapprovals, supplemental feeds | Coverage + Quality + Drift |
| Klaviyo | Catalog sync health, product block rendering, browse abandonment | Coverage + Quality |
| Shopper Approved | Review collection completeness, widget health | Quality only |
| Reddit | Dynamic product ads feed spec, catalog approval requirements | Quality only (feed completeness) |
| Facebook | Meta catalog spec, disapprovals, dynamic ad eligibility | Quality only |
| Pinterest | Catalog spec, product pin eligibility, rich pin requirements | Quality only |

---

## Implementation Notes

- `run_audit.py` must also write `feeds/digest/latest_results.json` (structured adapter results) so `score.py` can consume them without re-running adapters
- `score.py` must handle adapter errors gracefully — erroring channels get `null` scores, not 0
- Baseline coverage per channel: seeded from current audit data on first run (`walmart: 0.42, amazon: 0.90, google_merchant: 0.67, klaviyo: 0.95, shopper_approved: 0.99, reddit: 1.0, facebook: 0.59, pinterest: 1.0`), written to `benchmark.json` meta, never auto-updated (prevents drift from masking real problems)
- `benchmark.json` has no size limit concern — 365 snapshots × 8 channels × ~200 bytes = ~580KB/year
- GH Actions step order: `build_feed_master` → `run_audit` → `score` → `commit`
- The Opus 4.7 research phase runs once to produce guide content; guides are then maintained by the monthly agent, not by re-running deep research

---

## Out of Scope

- Auto-pushing content changes to channels (price/stock sync already handled by `sync_prices.py`)
- Pinterest API integration (stub only, no timeline)
- Reddit catalog upload automation (external agent dependency)
- Meta Catalog API (sheet-based approach sufficient until ad spend warrants direct API)
