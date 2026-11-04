"""One registration contract across scanning, diagnostics and reconciliation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, strategies as st
from typer.testing import CliRunner

from skilllint import auto_sync_manifests as sync
from skilllint.boundary.component_references import ComponentKind, component_references_from_raw
from skilllint.plugin_manifest import load_plugin_json
from skilllint.plugin_validator import app
from skilllint.rules.pr_series import check_pr002
from skilllint.scan_runtime import _discover_validatable_paths


@given(st.text().filter(lambda text: "\x00" not in text))
def test_scalar_and_list_declarations_normalize_identically(path: str) -> None:
    assert component_references_from_raw(path) == component_references_from_raw([path])


@pytest.mark.parametrize("scalar", [False, True])
@pytest.mark.parametrize(
    ("kind", "reference", "file"),
    [
        ("skills", "custom/foo", "custom/foo/SKILL.md"),
        ("skills", "custom", "custom/foo/SKILL.md"),
        ("skills", "custom/foo/SKILL.md", "custom/foo/SKILL.md"),
        ("agents", "custom", "custom/agent.md"),
        ("agents", "custom/agent.md", "custom/agent.md"),
        ("commands", "custom", "custom/command.md"),
        ("commands", "custom/command.md", "custom/command.md"),
    ],
)
def test_custom_reference_survives_reconciliation_and_is_scanned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: ComponentKind, reference: str, file: str, *, scalar: bool
) -> None:
    monkeypatch.chdir(tmp_path)
    plugin = tmp_path / "plugins/demo"
    target = plugin / file
    target.parent.mkdir(parents=True)
    target.write_text("---\nname: foo\ndescription: A skill\n---\n")
    manifest = plugin / ".claude-plugin/plugin.json"
    manifest.parent.mkdir()
    value = f"./{reference}"
    data = {"name": "demo", "version": "1.0.0", kind: value if scalar else [value]}
    manifest.write_text(json.dumps(data))
    original = manifest.read_bytes()

    assert check_pr002(data, plugin) == []
    paths = _discover_validatable_paths(plugin)
    assert target in paths or (target.name == "SKILL.md" and target.parent in paths)
    assert sync.reconcile(dry_run=False) == 0
    assert manifest.read_bytes() == original
    assert sync.reconcile(dry_run=False) == 0
    assert manifest.read_bytes() == original


@pytest.mark.parametrize(
    "platform", [[], ["--platform", "claude_code"], ["--platform", "claude_code", "--filter-type", "skills"]]
)
@pytest.mark.parametrize("scalar", [False, True])
def test_cli_reports_malformed_registered_custom_skill(tmp_path: Path, platform: list[str], *, scalar: bool) -> None:
    target = tmp_path / "custom/foo/SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("---\nname: foo\ndescription: [oops\n---\n")
    manifest = tmp_path / ".claude-plugin/plugin.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"name": "demo", "skills": "./custom/foo" if scalar else ["./custom/foo"]}))
    load_plugin_json.cache_clear()

    result = CliRunner().invoke(app, ["check", str(tmp_path), "--json", *platform])

    assert result.exit_code == 1, result.output
    assert "FM002" in result.output, result.output
    assert "custom/foo/SKILL.md" in result.output, result.output


@pytest.mark.parametrize("kind", ["skills", "agents", "commands"])
def test_missing_scalar_reconciliation_reaches_fixed_point(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: ComponentKind
) -> None:
    monkeypatch.chdir(tmp_path)
    manifest = tmp_path / "plugins/demo/.claude-plugin/plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": "demo", "version": "1.0.0", kind: "./custom/missing"}))
    before = manifest.read_bytes()

    assert sync.reconcile(dry_run=True) == 1
    assert manifest.read_bytes() == before
    assert sync.reconcile(dry_run=False) == 0
    first = manifest.read_bytes()
    assert json.loads(first)[kind] == []
    assert json.loads(first)["version"] == "1.1.0"
    assert sync.reconcile(dry_run=False) == 0
    assert manifest.read_bytes() == first


def test_precommit_removes_scalar_component_reference() -> None:
    data: dict[str, list[str] | str] = {"agents": "./agents/missing.md"}
    assert sync._remove_component_from_array(data, "agents", "agents/missing.md")
    assert data == {"agents": []}


def test_agent_directory_registration_does_not_gain_redundant_file_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    plugin = tmp_path / "plugins/demo"
    agent = plugin / "agents/reviewer.md"
    agent.parent.mkdir(parents=True)
    agent.write_text("---\nname: reviewer\ndescription: Reviewer\n---\n")
    manifest = plugin / ".claude-plugin/plugin.json"
    manifest.parent.mkdir()
    manifest.write_text('{"name":"demo","version":"1.0.0","agents":"./agents"}')
    original = manifest.read_bytes()
    assert sync.reconcile(dry_run=False) == 0
    assert manifest.read_bytes() == original


def test_skill_collection_scan_keeps_excluded_directory_policy(tmp_path: Path) -> None:
    manifest = tmp_path / ".claude-plugin/plugin.json"
    manifest.parent.mkdir()
    manifest.write_text('{"name":"demo","skills":"./custom"}')
    for name in ("wanted", ".venv"):
        target = tmp_path / "custom" / name / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("# Skill")
    paths = _discover_validatable_paths(tmp_path)
    assert tmp_path / "custom/wanted/SKILL.md" in paths
    assert tmp_path / "custom/.venv/SKILL.md" not in paths
