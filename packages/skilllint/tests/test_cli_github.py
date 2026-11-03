"""Executable contract for GitHub annotations and preserved legacy behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest
from default_output_cases import CORE_VARIANTS, Case
from json_probe_support import CheckResponse, assert_plain, parse, run_probe
from typer.testing import CliRunner

from skilllint import plugin_validator
from skilllint.models import ValidationIssue, ValidationResult
from skilllint.scan_runtime import CheckRun


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
    _, actual = run_probe(tmp_path, Case("github", ("check", *args, "--output-format", "github", "--no-color")))
    _, legacy = run_probe(tmp_path, Case("legacy", ("check", *args, "--json")), root="legacy")
    response = parse(CheckResponse, legacy)
    assert actual.returncode == legacy.returncode
    assert_plain(actual)
    lines = actual.stdout.decode().splitlines()
    issues = [issue for file in response.files for validator in file.validators for issue in validator.issues]
    assert len(lines) == len(issues)
    assert lines == sorted(lines)
    for issue in issues:
        assert any(
            f"::{'notice' if issue.severity == 'info' else issue.severity} " in line
            and f"title={issue.code}::" in line
            and issue.message in line
            for line in lines
        )


@pytest.mark.parametrize("color_args", [(), ("--no-color",)])
def test_known_location_and_no_terminal_decoration(tmp_path: Path, color_args: tuple[str, ...]) -> None:
    args = (
        "check",
        "invalid-skill/SKILL.md",
        "--output-format",
        "github",
        *color_args,
        "--show-progress",
        "--show-summary",
    )
    runs = [
        run_probe(tmp_path, Case("environment", args), root=variant.id, variant=variant)[1] for variant in CORE_VARIANTS
    ]
    for run in runs:
        assert_plain(run)
        assert run.stdout == runs[0].stdout
        assert run.returncode == 1
        assert b"file=invalid-skill/SKILL.md,line=2,col=1" in run.stdout
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
                "github",
                "--show-summary",
                "--show-progress",
                "--record",
                "out.svg",
            ),
        ),
    )
    assert run.returncode == 0
    assert run.stdout == b""
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
    _, run = run_probe(tmp_path, Case("usage", ("check", *args, "--output-format", "github")))
    assert run.returncode == 2
    assert run.stdout == b""
    assert run.stderr
    assert_plain(run)


def test_fix_and_record_collect_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "fixme/SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: fixme\ndescription: Use when testing the github output format.\ntools:\n  - Read\n  - Grep\n---\nBody.\n"
    )
    collect = Mock(wraps=plugin_validator.collect_validation_results)
    monkeypatch.setattr(plugin_validator, "collect_validation_results", collect)
    result = CliRunner().invoke(
        plugin_validator.app,
        ["check", str(path), "--fix", "--output-format", "github", "--record", str(tmp_path / "out.svg")],
    )
    assert result.exit_code == 0
    assert collect.call_count == 1
    assert "  - Read" not in path.read_text()
    assert "FIXED" not in result.stdout
    assert "Fixes applied" not in result.stdout


def test_exit_status_does_not_depend_on_visible_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "SKILL.md"
    path.touch()
    for passed in (False, True):
        issues = [ValidationIssue(field="test", code="FM001", severity="error", message="test")] if passed else []
        outcome = CheckRun(
            results={path: [("test", ValidationResult(passed=passed, errors=issues, warnings=[], info=[]))]}, fixes=[]
        )
        monkeypatch.setattr(plugin_validator, "collect_validation_results", Mock(return_value=outcome))
        result = CliRunner().invoke(plugin_validator.app, ["check", str(path), "--output-format", "github"])
        assert result.exit_code == (0 if passed else 1)
        assert bool(result.stdout) is passed


def test_actual_hostile_filename_is_one_escaped_annotation(tmp_path: Path) -> None:
    import os

    if os.name == "nt":
        pytest.skip("Windows disallows colons and line breaks in filenames")
    directory = tmp_path / "café%,:\n::warning::injected"
    directory.mkdir()
    path = directory / "SKILL.md"
    path.write_text(
        "---\nname: Bad_Name\ndescription: Use when testing GitHub annotations safely.\n---\n# Demo\nBody.\n"
    )
    result = CliRunner().invoke(
        plugin_validator.app, ["check", "--platform", "claude-code", "--output-format", "github", str(path)]
    )
    assert result.exit_code == 1
    assert result.stderr == ""
    lines = result.stdout.splitlines()
    assert len(lines) == 1
    assert "café%25%2C%3A%0A%3A%3Awarning%3A%3Ainjected/SKILL.md" in lines[0]
    assert ",line=2,col=1,endColumn=4,title=FM010::" in lines[0]


@pytest.mark.parametrize("payload", ["missing\n::error::injected", "missing##[error]injected"])
def test_usage_diagnostics_cannot_inject_runner_commands(payload: str, tmp_path: Path) -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "skilllint", "check", str(tmp_path / payload), "--output-format", "github"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Path does not exist:" in result.stderr
    assert "::" not in result.stderr
    assert "##[" not in result.stderr
