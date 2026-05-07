import csv
import pytest
from pathlib import Path


SAMPLE_RESULTS = [
    {
        "post_id": 1,
        "title": "Overseeding Your Lawn",
        "url": "https://naturesseed.com/resources/overseeding/",
        "topics": [
            {"category": "Lawn Care", "subcategory": "Overseeding"},
            {"category": "Grass Seed", "subcategory": "Cool Season"},
        ],
        "species_mentioned": ["Kentucky Bluegrass", "Perennial Ryegrass"],
        "products_mentioned": [
            {"name": "Sun & Shade Mix", "slug_if_known": "sun-shade-mix", "has_link": True},
            {"name": "Turf Builder", "slug_if_known": None, "has_link": False},
        ],
    }
]


def test_append_classifications_creates_file_with_header(tmp_path):
    from docs.resource_classifier.writer import append_classifications
    csv_path = tmp_path / "classifications.csv"
    append_classifications(csv_path, SAMPLE_RESULTS)
    rows = list(csv.DictReader(csv_path.open()))
    assert rows[0]["post_id"] == "1"
    assert rows[0]["category"] == "Lawn Care"
    assert rows[0]["subcategory"] == "Overseeding"


def test_append_classifications_one_row_per_topic(tmp_path):
    from docs.resource_classifier.writer import append_classifications
    csv_path = tmp_path / "classifications.csv"
    append_classifications(csv_path, SAMPLE_RESULTS)
    rows = list(csv.DictReader(csv_path.open()))
    # 1 article × 2 topics = 2 rows
    assert len(rows) == 2


def test_append_classifications_products_comma_separated(tmp_path):
    from docs.resource_classifier.writer import append_classifications
    csv_path = tmp_path / "classifications.csv"
    append_classifications(csv_path, SAMPLE_RESULTS)
    rows = list(csv.DictReader(csv_path.open()))
    assert rows[0]["products_mentioned"] == "Sun & Shade Mix,Turf Builder"
    assert rows[0]["has_link"] == "true,false"


def test_append_classifications_appends_on_second_call(tmp_path):
    from docs.resource_classifier.writer import append_classifications
    csv_path = tmp_path / "classifications.csv"
    append_classifications(csv_path, SAMPLE_RESULTS)
    append_classifications(csv_path, SAMPLE_RESULTS)
    rows = list(csv.DictReader(csv_path.open()))
    assert len(rows) == 4  # 2 topics × 2 calls


def test_rebuild_taxonomy_key(tmp_path):
    from docs.resource_classifier.writer import append_classifications, rebuild_taxonomy_key
    csv_path = tmp_path / "classifications.csv"
    key_path = tmp_path / "taxonomy-key.csv"
    append_classifications(csv_path, SAMPLE_RESULTS)
    append_classifications(csv_path, SAMPLE_RESULTS)  # same data twice
    rebuild_taxonomy_key(csv_path, key_path)
    rows = list(csv.DictReader(key_path.open()))
    lawn_care = next(r for r in rows if r["category"] == "Lawn Care")
    assert lawn_care["article_count"] == "2"  # 2 appearances (same post × 2 batches)
