"""Claude JSON kinds share the core manifest and hook validation owners."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

import pytest
from hypothesis import given, strategies as st
from pydantic import JsonValue

from skilllint.adapters.claude_code import ClaudeCodeAdapter
from skilllint.boundary.plugin_manifest_ingest import PluginManifestDefect, ingest_plugin_manifest
from skilllint.plugin_validator import app, validate_file
from skilllint.rules.pl_series import check_pl002, check_pl003

if TYPE_CHECKING:
    from typer.testing import CliRunner


@pytest.mark.parametrize("platform", [[], ["--platform", "claude_code"]], ids=["default", "claude"])
@pytest.mark.parametrize("layout", ["standalone", "manifest", "plugin-root"])
@pytest.mark.parametrize("payload", ['"name"', "null", "42", "true", "[]", '["name"]', '{"name":'])
def test_invalid_manifest_produces_json_report(
    tmp_path: Path, cli_runner: CliRunner, payload: str, layout: str, platform: list[str]
) -> None:
    """Every public manifest route reports invalid roots rather than crashing."""
    parent = tmp_path if layout == "standalone" else tmp_path / ".claude-plugin"
    parent.mkdir(exist_ok=True)
    manifest = parent / "plugin.json"
    manifest.write_text(payload, encoding="utf-8")
    target = tmp_path if layout == "plugin-root" else manifest

    result = cli_runner.invoke(app, ["check", str(target), *platform, "--json"])

    assert result.exit_code == 1, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "failed"
    issues = [issue for file in report["files"] for validator in file["validators"] for issue in validator["issues"]]
    assert [issue["code"] for issue in issues if issue["severity"] == "error"] == ["PL002"]
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("platform", [[], ["--platform", "claude_code"]], ids=["default", "claude"])
@pytest.mark.parametrize(("payload", "code"), [('{"hooks": {}}', None), ('{"hooks": []}', "HK001"), ("null", "HK001")])
def test_hooks_use_hook_rules(
    tmp_path: Path, cli_runner: CliRunner, payload: str, code: str | None, platform: list[str]
) -> None:
    """Hooks retain HK findings without plugin name or root-shape findings."""
    path = tmp_path / "hooks.json"
    path.write_text(payload, encoding="utf-8")

    result = cli_runner.invoke(app, ["check", str(path), *platform, "--json"])

    assert result.exit_code == (1 if code else 0), result.output
    report = json.loads(result.stdout)
    issues = [issue for file in report["files"] for validator in file["validators"] for issue in validator["issues"]]
    assert [issue["code"] for issue in issues] == ([code] if code else [])


@pytest.mark.parametrize(("payload", "expected"), [("{}", ["PL003"]), ('{"name": "example"}', [])])
def test_standalone_manifest_uses_shared_required_field_rule(tmp_path: Path, payload: str, expected: list[str]) -> None:
    """Fallback manifests now use the PL rule owner instead of adapter schema logic."""
    path = tmp_path / "plugin.json"
    path.write_text(payload, encoding="utf-8")
    adapter = ClaudeCodeAdapter()

    violations = validate_file(path, {adapter.id(): adapter}, platform_override=adapter.id())

    assert [issue["code"] for issue in violations] == expected


def test_unrelated_json_is_not_a_plugin_manifest(tmp_path: Path) -> None:
    """An explicit platform does not turn arbitrary JSON into plugin.json."""
    path = tmp_path / "settings.json"
    path.write_text("null", encoding="utf-8")
    adapter = ClaudeCodeAdapter()

    assert validate_file(path, {adapter.id(): adapter}, platform_override=adapter.id()) == []


def test_manifest_boundary_reports_missing_file(tmp_path: Path) -> None:
    """Read failures remain PL002 findings at the shared boundary."""
    path = tmp_path / "plugin.json"

    result = ingest_plugin_manifest(path)

    assert isinstance(result, PluginManifestDefect)
    assert result.kind == "read"
    assert [issue.code for issue in check_pl002(path)] == ["PL002"]


def test_required_name_field_rule_retains_subprocess_contract() -> None:
    """Adding direct detection does not change existing Claude output detection."""
    assert [issue.code for issue in check_pl003("missing required field name")] == ["PL003"]
    assert [issue.code for issue in check_pl003(manifest={})] == ["PL003"]
    assert check_pl003(manifest={"name": "example"}) == []


_JSON_VALUES = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False, allow_infinity=False) | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
)


@given(payload=_JSON_VALUES)
def test_manifest_boundary_accepts_only_objects(payload: JsonValue) -> None:
    """Arbitrary JSON roots are either preserved objects or structured defects."""
    with TemporaryDirectory() as directory:
        path = Path(directory) / "plugin.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        result = ingest_plugin_manifest(path)

    if isinstance(payload, dict):
        assert result == payload
    else:
        assert result == PluginManifestDefect("shape")
