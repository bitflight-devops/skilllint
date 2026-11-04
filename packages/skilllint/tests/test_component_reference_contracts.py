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


def test_precommit_removes_scalar_component_reference(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    manifest = tmp_path / "plugins/demo/.claude-plugin/plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"name":"demo","version":"1.0.0","agents":"./agents/missing.md"}')
    changes: sync.ComponentChanges = {
        "added": [],
        "modified": [],
        "deleted": [{"component_type": "agent", "component_path": "agents/missing.md"}],
    }
    assert sync.update_plugin_json("demo", changes) == (True, "2.0.0")
    assert json.loads(manifest.read_bytes())["agents"] == []


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


@pytest.mark.parametrize("kind", ["skills", "agents", "commands"])
def test_symlink_parent_traversal_keeps_its_real_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: ComponentKind
) -> None:
    monkeypatch.chdir(tmp_path)
    plugin = tmp_path / "plugins/demo"
    nested = plugin / "shared/nested"
    nested.mkdir(parents=True)
    alias = plugin / "alias"
    try:
        alias.symlink_to(nested, target_is_directory=True)
    except OSError:
        pytest.skip("This environment cannot create directory symlinks")
    target = plugin / "shared/foo" / ("SKILL.md" if kind == "skills" else "agent.md")
    target.parent.mkdir()
    target.write_text("---\nname: foo\ndescription: Target\n---\n")
    manifest = plugin / ".claude-plugin/plugin.json"
    manifest.parent.mkdir()
    data = {"name": "demo", "version": "1.0.0", kind: ["./alias/../foo"]}
    manifest.write_text(json.dumps(data))
    original = manifest.read_bytes()

    assert check_pr002(data, plugin) == []
    paths = _discover_validatable_paths(plugin)
    assert target in paths or (kind == "skills" and target.parent in paths)
    assert sync.reconcile(dry_run=False) == 0
    assert manifest.read_bytes() == original


@pytest.mark.parametrize("kind", ["agents", "commands"])
@pytest.mark.parametrize("scalar", [False, True])
@pytest.mark.parametrize("platform", [[], ["--platform", "claude_code"]])
def test_cli_validates_custom_agent_and_command_frontmatter(
    tmp_path: Path, kind: ComponentKind, platform: list[str], *, scalar: bool
) -> None:
    target = tmp_path / "custom/reviewer.md"
    target.parent.mkdir()
    target.write_text("---\nname: reviewer\ndescription: [oops\n---\n")
    manifest = tmp_path / ".claude-plugin/plugin.json"
    manifest.parent.mkdir()
    manifest.write_text(
        json.dumps({"name": "demo", kind: "./custom/reviewer.md" if scalar else ["./custom/reviewer.md"]})
    )
    result = CliRunner().invoke(app, ["check", str(tmp_path), "--json", *platform])
    assert result.exit_code == 1, result.output
    assert "FM002" in result.output, result.output


def test_filtered_skill_collection_excludes_vendored_children(tmp_path: Path) -> None:
    manifest = tmp_path / ".claude-plugin/plugin.json"
    manifest.parent.mkdir()
    manifest.write_text('{"name":"demo","skills":"./custom"}')
    for name in ("wanted", ".venv"):
        target = tmp_path / "custom" / name / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("---\nname: missing-description\n---\n")
    result = CliRunner().invoke(
        app, ["check", str(tmp_path), "--platform", "claude_code", "--filter-type", "skills", "--json"]
    )
    assert "custom/wanted/SKILL.md" in result.output
    assert ".venv" not in result.output


def test_reconcile_ignores_discovered_agent_symlinks_outside_plugin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside")
    plugin = tmp_path / "plugins/demo"
    agents = plugin / "agents"
    agents.mkdir(parents=True)
    try:
        (agents / "outside.md").symlink_to(outside)
    except OSError:
        pytest.skip("This environment cannot create symlinks")
    manifest = plugin / ".claude-plugin/plugin.json"
    manifest.parent.mkdir()
    manifest.write_text('{"name":"demo","version":"1.0.0","agents":[]}')
    original = manifest.read_bytes()
    assert sync.reconcile(dry_run=False) == 0
    assert sync.reconcile(dry_run=False) == 0
    assert manifest.read_bytes() == original


def test_parent_traversal_preserves_a_following_file_symlink_alias(tmp_path: Path) -> None:
    from skilllint.boundary.component_references import ComponentReference

    target = tmp_path / "target.md"
    target.write_text("# Target")
    shared = tmp_path / "shared/nested"
    shared.mkdir(parents=True)
    try:
        (tmp_path / "alias").symlink_to(shared, target_is_directory=True)
        (tmp_path / "shared/agent.md").symlink_to(target)
    except OSError:
        pytest.skip("This environment cannot create symlinks")
    resolution = ComponentReference("./alias/../agent.md").resolve(tmp_path, "agents")
    assert resolution.valid
    assert resolution.paths == (tmp_path / "shared/agent.md",)
