"""Unit tests for link extraction and URL classification."""

from naturesseed_pipeline.pipelines.audit.link_extract import (
    classify_href, extract_links, ExtractedLink,
)


def test_classify_anchor():
    assert classify_href("#section-1", "naturesseed.com") == "anchor"


def test_classify_internal_product():
    assert classify_href("https://naturesseed.com/products/fescue/", "naturesseed.com") == "internal_product"
    assert classify_href("https://naturesseed.com/product/bundle/foo/", "naturesseed.com") == "internal_product"


def test_classify_internal_content():
    assert classify_href("https://naturesseed.com/resources/guide/", "naturesseed.com") == "internal_content"
    assert classify_href("/resources/guide/", "naturesseed.com") == "internal_content"


def test_classify_external():
    assert classify_href("https://example.com/page", "naturesseed.com") == "external"


def test_extract_links_returns_href_and_anchor():
    html = '<p><a href="/a/">A text</a> <a href="https://ext.com">Ext</a></p>'
    links = extract_links(html, "naturesseed.com")
    assert len(links) == 2
    assert links[0] == ExtractedLink(href="/a/", anchor_text="A text", link_type="internal_content")
    assert links[1].link_type == "external"


def test_extract_links_dedupes_same_href_in_same_doc():
    html = '<a href="/x/">first</a> <a href="/x/">second</a>'
    links = extract_links(html, "naturesseed.com")
    assert len(links) == 1
    assert links[0].anchor_text == "first"


def test_extract_links_handles_relative_urls():
    html = '<a href="/products/foo/">Foo</a>'
    links = extract_links(html, "naturesseed.com")
    assert links[0].link_type == "internal_product"
