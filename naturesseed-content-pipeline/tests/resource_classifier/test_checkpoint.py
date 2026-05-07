import json
import pytest
from pathlib import Path


def test_load_returns_empty_set_when_file_missing(tmp_path):
    from docs.resource_classifier.checkpoint import load_checkpoint, save_checkpoint
    cp_path = tmp_path / "checkpoint.json"
    assert load_checkpoint(cp_path) == set()


def test_save_and_load_roundtrip(tmp_path):
    from docs.resource_classifier.checkpoint import load_checkpoint, save_checkpoint
    cp_path = tmp_path / "checkpoint.json"
    save_checkpoint(cp_path, {0, 3, 7})
    result = load_checkpoint(cp_path)
    assert result == {0, 3, 7}


def test_save_is_idempotent(tmp_path):
    from docs.resource_classifier.checkpoint import load_checkpoint, save_checkpoint
    cp_path = tmp_path / "checkpoint.json"
    save_checkpoint(cp_path, {1, 2})
    save_checkpoint(cp_path, {1, 2, 5})
    assert load_checkpoint(cp_path) == {1, 2, 5}
