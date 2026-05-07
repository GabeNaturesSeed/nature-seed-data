def test_strip_html_removes_tags():
    from docs.resource_classifier.fetcher import strip_html
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_empty_string():
    from docs.resource_classifier.fetcher import strip_html
    assert strip_html("") == ""
