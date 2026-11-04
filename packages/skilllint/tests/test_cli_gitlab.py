"""Executable contract for GitLab reports and preserved legacy behavior."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from default_output_cases import CORE_VARIANTS, Case, workspace
from json_probe_support import CheckResponse, assert_plain, parse, run_probe
from typer.testing import CliRunner

from skilllint import plugin_validator
from skilllint.models import ValidationIssue, ValidationResult
from skilllint.scan_runtime import CheckRun


def _repository_workspace(sandbox, endpoints):
    workspace(sandbox, endpoints)
    (sandbox.case / ".git").mkdir()


@pytest.mark.parametrize(
    "args",
    [
        ("valid_skill.md",),
        ("invalid-skill/SKILL.md",),
        ("plug",),
        ("plug", "--platform", "claude-code"),
        ("invalid-skill/SKILL.md", "--verbose"),
        ("fixme/SKILL.md", "--fix"),
    ],
)
def test_findings_and_status_match_legacy_json(args: tuple[str, ...], tmp_path: Path) -> None:
    _, actual = run_probe(tmp_path, Case("gitlab", ("check", *args, "--output-format", "gitlab", "--no-color")))
    _, legacy = run_probe(tmp_path, Case("legacy", ("check", *args, "--json")), root="legacy")
    response = parse(CheckResponse, legacy)
    assert actual.returncode == legacy.returncode
    assert_plain(actual)
    findings = json.loads(actual.stdout)
    issues = [issue for file in response.files for validator in file.validators for issue in validator.issues]
    assert len(findings) + len(actual.stderr.splitlines()) == len(issues)
    for issue in issues:
        assert (
            any(
                finding["severity"] == {"error": "major", "warning": "minor", "info": "info"}[issue.severity]
                and finding["check_name"] == issue.code
                and issue.message in finding["description"]
                for finding in findings
            )
            or issue.message in actual.stderr.decode()
        )


@pytest.mark.parametrize("color_args", [(), ("--no-color",)])
def test_known_location_and_no_terminal_decoration(tmp_path: Path, color_args: tuple[str, ...]) -> None:
    args = (
        "check",
        "invalid-skill/SKILL.md",
        "--output-format",
        "gitlab",
        *color_args,
        "--show-progress",
        "--show-summary",
    )
    runs = [
        run_probe(tmp_path, Case("environment", args, setup=_repository_workspace), root=variant.id, variant=variant)[1]
        for variant in CORE_VARIANTS
    ]
    for run in runs:
        assert_plain(run)
        assert run.stdout == runs[0].stdout
        assert run.returncode == 1
        assert any(
            finding["location"] == {"path": "invalid-skill/SKILL.md", "lines": {"begin": 2}}
            for finding in json.loads(run.stdout)
        )
        assert b"PASSED" not in run.stdout
        assert b"Summary" not in run.stdout
        assert b"FrontmatterValidator" not in run.stdout


def test_clean_scan_and_human_recording(tmp_path: Path) -> None:
    sandbox, run = run_probe(
        tmp_path,
        Case(
            "clean",
            (
                "check",
                "valid_skill.md",
                "--output-format",
                "gitlab",
                "--show-summary",
                "--show-progress",
                "--record",
                "out.svg",
            ),
        ),
    )
    assert run.returncode == 0
    assert run.stdout == b"[]\n"
    assert b"Validation" in (sandbox.case / "out.svg").read_bytes()


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("missing.md",),
        ("valid_skill.md", "--json"),
        ("valid_skill.md", "--tokens-only"),
        ("valid_skill.md", "--check", "--fix"),
        ("invalid-skill/SKILL.md", "--record", "missing/out.svg"),
    ],
)
def test_usage_errors_keep_stdout_empty(args: tuple[str, ...], tmp_path: Path) -> None:
    _, run = run_probe(tmp_path, Case("usage", ("check", *args, "--output-format", "gitlab")))
    assert run.returncode == 2
    assert run.stdout == b""
    assert run.stderr
    assert_plain(run)


def test_fix_and_record_collect_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "fixme/SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: fixme\ndescription: Use when testing the gitlab output format.\ntools:\n  - Read\n  - Grep\n---\nBody.\n"
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    collect = Mock(wraps=plugin_validator.collect_validation_results)
    monkeypatch.setattr(plugin_validator, "collect_validation_results", collect)
    result = CliRunner().invoke(
        plugin_validator.app,
        ["check", str(path), "--fix", "--output-format", "gitlab", "--record", str(tmp_path / "out.svg")],
    )
    assert result.exit_code == 0
    assert collect.call_count == 1
    assert "  - Read" not in path.read_text()
    assert "FIXED" not in result.stdout
    assert "Fixes applied" not in result.stdout


def test_exit_status_does_not_depend_on_visible_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "SKILL.md"
    path.touch()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    for passed in (False, True):
        issues = [ValidationIssue(field="test", code="FM001", severity="error", message="test")] if passed else []
        outcome = CheckRun(
            results={path: [("test", ValidationResult(passed=passed, errors=issues, warnings=[], info=[]))]}, fixes=[]
        )
        monkeypatch.setattr(plugin_validator, "collect_validation_results", Mock(return_value=outcome))
        result = CliRunner().invoke(plugin_validator.app, ["check", str(path), "--output-format", "gitlab"])
        assert result.exit_code == (0 if passed else 1)
        assert bool(json.loads(result.stdout)) is passed


def test_outside_finding_is_not_silently_lost(tmp_path, monkeypatch):
    root = tmp_path / "repository"
    root.mkdir()
    (root / ".git").mkdir()
    monkeypatch.chdir(root)
    path = tmp_path / "SKILL.md"
    path.write_text("---\nname: Bad_Name\ndescription: Use when testing GitLab safely.\n---\nBody.\n")
    result = CliRunner().invoke(
        plugin_validator.app, ["check", "--platform", "claude-code", "--output-format", "gitlab", str(path)]
    )
    assert result.exit_code == 1
    assert json.loads(result.stdout) == []
    assert '"code": "FM010"' in result.stderr
    assert "omitted a finding with no repository file" in result.stderr


def test_nested_repository_cwd_reports_root_relative_source(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "skills"
    nested.mkdir()
    monkeypatch.chdir(nested)
    path = nested / "SKILL.md"
    path.write_text("---\nname: Bad_Name\ndescription: Use when testing GitLab safely.\n---\nBody.\n")
    result = CliRunner().invoke(
        plugin_validator.app, ["check", "--platform", "claude-code", "--output-format", "gitlab", "SKILL.md"]
    )
    assert result.exit_code == 1
    assert result.stderr == ""
    assert json.loads(result.stdout)[0]["location"]["path"] == "skills/SKILL.md"
