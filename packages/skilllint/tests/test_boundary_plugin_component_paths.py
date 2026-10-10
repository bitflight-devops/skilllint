"""Tests for the plugin.json component-path boundary used by the ``--fix`` folder-rename guard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skilllint.boundary.plugin_level_config_ingest import (
    component_paths_from_plugin_document,
    ingest_plugin_component_paths,
)


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


def test_component_paths_load_the_requested_manifest_without_sharing_cached_content(tmp_path: Path) -> None:
    """Coexisting platform manifests retain their own registrations; the default remains Claude."""
    manifests = {
        ".claude-plugin/plugin.json": "./claude",
        "plugin.json": "./portable",
        ".codex-plugin/plugin.json": "./codex",
        ".cursor-plugin/plugin.json": "./cursor",
    }
    for manifest_path, entry in manifests.items():
        manifest = tmp_path / manifest_path
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"skills": [entry]}), encoding="utf-8")

    assert ingest_plugin_component_paths(tmp_path) == ("./claude",)
    for manifest_path, entry in manifests.items():
        assert ingest_plugin_component_paths(tmp_path, manifest_path=manifest_path) == (entry,)
    assert ingest_plugin_component_paths(tmp_path) == ("./claude",)
