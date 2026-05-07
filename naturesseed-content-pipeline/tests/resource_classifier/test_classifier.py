import json
import pytest
from unittest.mock import patch, MagicMock


VALID_RESPONSE = json.dumps([
    {
        "post_id": 1,
        "topics": [{"category": "Lawn Care", "subcategory": "Overseeding"}],
        "species_mentioned": ["Kentucky Bluegrass"],
        "products_mentioned": [{"name": "Sun & Shade Mix", "slug_if_known": "sun-shade-mix", "has_link": True}],
    }
])


def test_parse_response_valid():
    from docs.resource_classifier.classifier import parse_response
    result = parse_response(VALID_RESPONSE)
    assert len(result) == 1
    assert result[0]["post_id"] == 1
    assert result[0]["topics"][0]["category"] == "Lawn Care"


def test_parse_response_strips_markdown_fences():
    from docs.resource_classifier.classifier import parse_response
    fenced = f"```json\n{VALID_RESPONSE}\n```"
    result = parse_response(fenced)
    assert len(result) == 1


def test_parse_response_raises_on_invalid_json():
    from docs.resource_classifier.classifier import parse_response, ClassifierError
    with pytest.raises(ClassifierError):
        parse_response("not json at all")


def test_parse_response_raises_when_not_array():
    from docs.resource_classifier.classifier import parse_response, ClassifierError
    with pytest.raises(ClassifierError):
        parse_response('{"error": "bad"}')


def test_call_claude_returns_parsed(monkeypatch):
    from docs.resource_classifier.classifier import call_claude

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = VALID_RESPONSE
    mock_result.stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)

    batch = [{"post_id": 1, "title": "T", "url": "u", "content_html": "<p>x</p>"}]
    result = call_claude(batch)
    assert result[0]["post_id"] == 1


def test_call_claude_raises_on_nonzero_exit(monkeypatch):
    from docs.resource_classifier.classifier import call_claude, ClassifierError

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "claude error"

    monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)

    with pytest.raises(ClassifierError):
        call_claude([{"post_id": 1, "title": "T", "url": "u", "content_html": "x"}])
