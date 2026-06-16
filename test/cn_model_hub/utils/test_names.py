"""Tests for name normalization helpers."""

from cn_model_hub.utils.names import normalize_name


def test_normalize_name_lowercases_and_strips_separators():
    assert normalize_name("My-Repo_Name") == "myreponame"


def test_normalize_name_preserves_other_characters():
    assert normalize_name("Model.v2") == "model.v2"
