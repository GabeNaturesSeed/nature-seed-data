import csv
from collections import defaultdict
from pathlib import Path

CLASSIFICATIONS_HEADER = [
    "post_id", "title", "url", "category", "subcategory",
    "species_mentioned", "products_mentioned", "has_link",
]

TAXONOMY_HEADER = ["category", "subcategory", "article_count"]


def append_classifications(csv_path: Path, results: list[dict]) -> None:
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CLASSIFICATIONS_HEADER)
        if write_header:
            writer.writeheader()
        for article in results:
            products = article.get("products_mentioned") or []
            product_names = ",".join(p["name"] for p in products)
            has_links = ",".join("true" if p.get("has_link") else "false" for p in products)
            species = ",".join(article.get("species_mentioned") or [])

            topics = article.get("topics") or [{"category": "Uncategorized", "subcategory": ""}]
            for topic in topics:
                writer.writerow({
                    "post_id": article["post_id"],
                    "title": article["title"],
                    "url": article["url"],
                    "category": topic.get("category", ""),
                    "subcategory": topic.get("subcategory", ""),
                    "species_mentioned": species,
                    "products_mentioned": product_names,
                    "has_link": has_links,
                })


def rebuild_taxonomy_key(classifications_path: Path, key_path: Path) -> None:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    with classifications_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["category"], row["subcategory"])
            counts[key] += 1

    with key_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TAXONOMY_HEADER)
        writer.writeheader()
        for (cat, subcat), count in sorted(counts.items(), key=lambda x: -x[1]):
            writer.writerow({"category": cat, "subcategory": subcat, "article_count": count})
