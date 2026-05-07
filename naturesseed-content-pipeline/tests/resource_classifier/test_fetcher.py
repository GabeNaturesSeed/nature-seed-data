import pytest
from unittest.mock import patch, MagicMock


def _make_post(n: int) -> dict:
    return {
        "id": n,
        "title": {"rendered": f"Article {n}"},
        "link": f"https://naturesseed.com/resources/article-{n}/",
        "content": {"rendered": f"<p>Body {n}</p>"},
    }


def test_parse_post_extracts_fields():
    from docs.resource_classifier.fetcher import parse_post
    raw = _make_post(42)
    result = parse_post(raw)
    assert result["post_id"] == 42
    assert result["title"] == "Article 42"
    assert result["url"] == "https://naturesseed.com/resources/article-42/"
    assert "<p>Body 42</p>" in result["content_html"]


def test_strip_html_removes_tags():
    from docs.resource_classifier.fetcher import strip_html
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_empty_string():
    from docs.resource_classifier.fetcher import strip_html
    assert strip_html("") == ""
