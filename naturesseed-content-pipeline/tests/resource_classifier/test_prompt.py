import json


def test_build_prompt_includes_all_post_ids():
    from docs.resource_classifier.prompt import build_prompt
    batch = [
        {"post_id": 1, "title": "Article 1", "url": "https://naturesseed.com/a1/", "content_html": "<p>text</p>"},
        {"post_id": 2, "title": "Article 2", "url": "https://naturesseed.com/a2/", "content_html": "<p>more</p>"},
    ]
    prompt = build_prompt(batch)
    assert "1" in prompt
    assert "2" in prompt


def test_build_prompt_is_valid_json_instruction():
    from docs.resource_classifier.prompt import build_prompt
    batch = [
        {"post_id": 10, "title": "T", "url": "https://x.com/", "content_html": "<p>body</p>"},
    ]
    prompt = build_prompt(batch)
    # Prompt must reference the expected JSON structure
    assert "post_id" in prompt
    assert "topics" in prompt
    assert "species_mentioned" in prompt
    assert "products_mentioned" in prompt
