#!/usr/bin/env python3
"""
Product Quality Report for Walmart Marketplace — Nature's Seed.

Scores STAGE items using only fields returned by GET /v3/items/{sku}.
Fields not available via the API (images, description, brand, bullets)
are marked as None rather than scored.

Score rubric (100 pts total):
  - Title 50-150 chars          25 pts
  - Title contains species name  20 pts
  - Price present               15 pts
  - UPC/GTIN present            15 pts
  - Shelf has 4+ levels         15 pts
  - No unpublished reasons      10 pts

Public API:
  check_fields(item)            -> dict
  calc_quality_score(item, fields) -> int
  score_item(item)              -> dict
  run_report()                  -> None  (orchestrator, live API)
"""

import json
import csv
import os
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Species keywords used for title scoring
# ---------------------------------------------------------------------------
SPECIES_KEYWORDS = [
    "bluegrass", "fescue", "bermuda", "ryegrass", "zoysia", "buffalo",
    "centipede", "bahia", "bentgrass", "st. augustine", "st augustine",
    "kentucky", "tall fescue", "fine fescue", "creeping red", "chewings",
    "perennial rye", "annual rye",
]

# ---------------------------------------------------------------------------
# check_fields
# ---------------------------------------------------------------------------

def check_fields(item: dict) -> dict:
    """
    Return a dict of field presence checks.

    Fields not available via the Walmart item API are always None.
    Fields available via the API return True/False.
    """
    # Title: productName must be non-empty
    product_name = item.get("productName", "") or ""
    title_ok = bool(product_name.strip())

    # Price: price.amount must be present and non-zero
    price_block = item.get("price") or {}
    price_ok = bool(price_block.get("amount"))

    # UPC/GTIN: at least one must be present and non-empty
    upc = item.get("upc") or ""
    gtin = item.get("gtin") or ""
    upc_ok = bool(upc.strip() or gtin.strip())

    # Shelf: must have 4+ "/" separators (5+ segments)
    shelf = item.get("shelf") or ""
    shelf_ok = shelf.count("/") >= 4

    return {
        "title": title_ok,
        "price": price_ok,
        "upc": upc_ok,
        "shelf_category": shelf_ok,
        # Not available via the Walmart item API:
        "images": None,
        "description": None,
        "brand": None,
        "bullets": None,
    }


# ---------------------------------------------------------------------------
# calc_quality_score
# ---------------------------------------------------------------------------

def calc_quality_score(item: dict, fields: dict) -> int:
    """
    Return an integer quality score 0-100 based on available API fields.

    Rubric:
      Title 50-150 chars           25 pts
      Title contains species name  20 pts
      Price present                15 pts
      UPC/GTIN present             15 pts
      Shelf has 4+ levels          15 pts
      No unpublished reasons       10 pts
    """
    score = 0
    product_name = (item.get("productName") or "").strip()

    # Title length 50-150 chars
    if 50 <= len(product_name) <= 150:
        score += 25

    # Title contains a species/grass keyword
    name_lower = product_name.lower()
    if any(kw in name_lower for kw in SPECIES_KEYWORDS):
        score += 20

    # Price present
    if fields.get("price"):
        score += 15

    # UPC/GTIN present
    if fields.get("upc"):
        score += 15

    # Shelf category depth (4+ "/" = 5+ segments)
    if fields.get("shelf_category"):
        score += 15

    # No unpublished reasons (only award if the key is present — API returned it)
    if "unpublishedReasons" in item:
        reasons = item["unpublishedReasons"]
        reason_list = reasons.get("reason", []) if isinstance(reasons, dict) else []
        if not reason_list:
            score += 10

    return min(score, 100)


# ---------------------------------------------------------------------------
# score_item
# ---------------------------------------------------------------------------

def score_item(item: dict) -> dict:
    """
    Score a single item dict and return a structured result.

    Returns:
      {
        "sku": str,
        "fields": dict,
        "quality_score": int,
        "gaps": list[str],           # fields where value is False
        "api_limitations": list[str],# fields where value is None
        "unpublished_reasons": list[str],
      }
    """
    fields = check_fields(item)
    quality_score = calc_quality_score(item, fields)

    gaps = [k for k, v in fields.items() if v is False]
    api_limitations = [k for k, v in fields.items() if v is None]

    reasons_block = item.get("unpublishedReasons", {})
    unpublished_reasons = (
        reasons_block.get("reason", []) if isinstance(reasons_block, dict) else []
    )

    return {
        "sku": item.get("sku", ""),
        "fields": fields,
        "quality_score": quality_score,
        "gaps": gaps,
        "api_limitations": api_limitations,
        "unpublished_reasons": unpublished_reasons,
    }


# ---------------------------------------------------------------------------
# run_report  (orchestrator — do NOT call during unit tests)
# ---------------------------------------------------------------------------

def run_report():
    """
    Orchestrator: fetch all STAGE items, score each, write MD + CSV reports.

    Reads:
      data/stage_audit.json       (stock info, keyed by SKU)
      data/activation_results.json (optional, activation attempt history)

    Writes:
      data/product_quality_report.md
      data/product_quality_report.csv
    """
    from walmart_client import get_all_items, get_item  # noqa: PLC0415

    base_dir = Path(__file__).resolve().parent / "data"
    base_dir.mkdir(exist_ok=True)

    # Load stage audit map
    stage_audit_path = base_dir / "stage_audit.json"
    stage_audit = {}
    if stage_audit_path.exists():
        stage_audit = json.loads(stage_audit_path.read_text())

    # Load activation results map (optional)
    activation_path = base_dir / "activation_results.json"
    activation_map = {}
    if activation_path.exists():
        activation_map = json.loads(activation_path.read_text())

    # Fetch all items and filter to STAGE
    print("Fetching all Walmart items...")
    all_items = get_all_items()
    stage_items = [i for i in all_items if i.get("publishedStatus") == "STAGE"]
    print(f"Found {len(stage_items)} STAGE items.")

    rows = []
    for item in stage_items:
        sku = item.get("sku", "")
        print(f"  Fetching detail for {sku}...")
        try:
            response = get_item(sku)
            item_responses = response.get("ItemResponse", [])
            if not item_responses:
                print(f"    No ItemResponse for {sku}, skipping.")
                continue
            detail = item_responses[0]
        except Exception as exc:
            print(f"    Error fetching {sku}: {exc}")
            continue

        result = score_item(detail)
        stock_info = stage_audit.get(sku, {})
        activation_info = activation_map.get(sku, {})

        rows.append({
            "sku": sku,
            "product_name": detail.get("productName", ""),
            "quality_score": result["quality_score"],
            "gaps": ", ".join(result["gaps"]) if result["gaps"] else "none",
            "api_limitations": result["api_limitations"],
            "unpublished_reasons": "; ".join(result["unpublished_reasons"]) if result["unpublished_reasons"] else "",
            "in_stock": stock_info.get("in_stock", ""),
            "activation_attempted": bool(activation_info),
        })

    # Sort by quality score ascending (worst first)
    rows.sort(key=lambda r: r["quality_score"])

    # Write CSV
    csv_path = base_dir / "product_quality_report.csv"
    fieldnames = ["sku", "product_name", "quality_score", "gaps", "api_limitations", "unpublished_reasons", "in_stock", "activation_attempted"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row["api_limitations"] = "; ".join(row.get("api_limitations", []))
        writer.writerows(rows)
    print(f"CSV written: {csv_path}")

    # Write Markdown
    md_path = base_dir / "product_quality_report.md"
    _write_markdown(md_path, rows)
    print(f"Markdown written: {md_path}")


def _write_markdown(path: Path, rows: list) -> None:
    """Write the markdown quality report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(rows)
    if total:
        avg_score = sum(r["quality_score"] for r in rows) / total
        high = sum(1 for r in rows if r["quality_score"] >= 80)
        medium = sum(1 for r in rows if 50 <= r["quality_score"] < 80)
        low = sum(1 for r in rows if r["quality_score"] < 50)
    else:
        avg_score = high = medium = low = 0

    lines = [
        f"# Walmart Product Quality Report",
        f"",
        f"Generated: {now}  |  STAGE items scored: {total}",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Average quality score | {avg_score:.0f} / 100 |",
        f"| High (≥80) | {high} |",
        f"| Medium (50-79) | {medium} |",
        f"| Low (<50) | {low} |",
        f"",
        f"## API Limitations",
        f"",
        f"The Walmart `GET /v3/items/{{sku}}` endpoint does **not** return the following fields.",
        f"These could not be assessed programmatically — verify them manually in Walmart Seller Center:",
        f"",
        f"- **Images** — check that each item has at least 4 images with white background",
        f"- **Description** — verify the short description (shortDescription) is present and complete",
        f"- **Brand** — confirm brand name is set correctly",
        f"- **Bullet points** — confirm key features / selling points are populated",
        f"",
        f"## Score Rubric",
        f"",
        f"| Signal | Points |",
        f"|---|---|",
        f"| Title 50–150 chars | 25 |",
        f"| Title contains species name | 20 |",
        f"| Price present | 15 |",
        f"| UPC/GTIN present | 15 |",
        f"| Shelf category has 4+ levels | 15 |",
        f"| No Walmart unpublishedReasons | 10 |",
        f"",
        f"## Item Scores",
        f"",
        f"| SKU | Product Name | Score | Gaps | Unpublished Reasons |",
        f"|---|---|---|---|---|",
    ]

    for r in rows:
        name = r["product_name"][:60] + "..." if len(r["product_name"]) > 60 else r["product_name"]
        score = r["quality_score"]
        gaps = r["gaps"]
        reasons = r["unpublished_reasons"] or "—"
        lines.append(f"| {r['sku']} | {name} | {score} | {gaps} | {reasons} |")

    lines += [
        f"",
        f"---",
        f"*Report generated by `product_quality_report.py`*",
    ]

    path.write_text("\n".join(lines))


if __name__ == "__main__":
    run_report()
