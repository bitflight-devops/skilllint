"""Tests for the plugin.json component-path boundary used by the ``--fix`` folder-rename guard."""

from __future__ import annotations

import pytest

from skilllint.boundary.plugin_level_config_ingest import component_paths_from_plugin_document


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param({"skills": ["./a", "./b"]}, ("./a", "./b"), id="list"),
        pytest.param({"commands": "./c.md"}, ("./c.md",), id="single-string"),
        pytest.param({"agents": ["./ok.md", 3, None, "./x\x00y"]}, ("./ok.md",), id="drops-non-strings-and-nul"),
        pytest.param({"skills": {"a": 1}}, (), id="object-ignored"),
        pytest.param(["not", "an", "object"], (), id="non-object-root"),
        pytest.param(None, (), id="missing"),
    ],
)
def test_component_paths_keep_only_valid_path_strings(raw: object, expected: tuple[str, ...]) -> None:
    """Only path strings from skills, commands and agents reach the caller."""
    assert component_paths_from_plugin_document(raw) == expected
