"""Executable contract for JUnit reports and preserved legacy behavior."""

from __future__ import annotations

import xml.etree.ElementTree as ET
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
    _, actual = run_probe(tmp_path, Case("junit", ("check", *args, "--output-format", "junit", "--no-color")))
    _, legacy = run_probe(tmp_path, Case("legacy", ("check", *args, "--json", "--show-progress")), root="legacy")
    response = parse(CheckResponse, legacy)
    assert actual.returncode == legacy.returncode
    assert_plain(actual)
    root = ET.fromstring(actual.stdout)
    validators = [validator for file in response.files for validator in file.validators]
    assert int(root.attrib["tests"]) == len(validators)
    assert int(root.attrib["failures"]) == sum(validator.status == "failed" for validator in validators)
    text = "".join(root.itertext())
    for validator in validators:
        for issue in validator.issues:
            assert issue.message in text


@pytest.mark.parametrize("color_args", [(), ("--no-color",)])
def test_known_location_and_no_terminal_decoration(tmp_path: Path, color_args: tuple[str, ...]) -> None:
    args = (
        "check",
        "invalid-skill/SKILL.md",
        "--output-format",
        "junit",
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
        root = ET.fromstring(run.stdout)
        assert "invalid-skill/SKILL.md:2:1" in "".join(root.itertext())
        assert b"PASSED" not in run.stdout
        assert b"Validation Summary" not in run.stdout


def test_clean_scan_and_human_recording(tmp_path: Path) -> None:
    sandbox, run = run_probe(
        tmp_path,
        Case(
            "clean",
            (
                "check",
                "valid_skill.md",
                "--output-format",
                "junit",
                "--show-summary",
                "--show-progress",
                "--record",
                "out.svg",
            ),
        ),
    )
    assert run.returncode == 0
    root = ET.fromstring(run.stdout)
    assert int(root.attrib["tests"]) > 0
    assert root.attrib["failures"] == "0"
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
    _, run = run_probe(tmp_path, Case("usage", ("check", *args, "--output-format", "junit")))
    assert run.returncode == 2
    assert run.stdout == b""
    assert run.stderr
    assert_plain(run)


def test_fix_and_record_collect_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "fixme/SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: fixme\ndescription: Use when testing the junit output format.\ntools:\n  - Read\n  - Grep\n---\nBody.\n"
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    collect = Mock(wraps=plugin_validator.collect_validation_results)
    monkeypatch.setattr(plugin_validator, "collect_validation_results", collect)
    result = CliRunner().invoke(
        plugin_validator.app,
        ["check", str(path), "--fix", "--output-format", "junit", "--record", str(tmp_path / "out.svg")],
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
        result = CliRunner().invoke(plugin_validator.app, ["check", str(path), "--output-format", "junit"])
        assert result.exit_code == (0 if passed else 1)
        assert ET.fromstring(result.stdout).attrib["failures"] == ("0" if passed else "1")


def test_real_warning_only_scan_remains_passing(tmp_path):
    _, run = run_probe(tmp_path, Case("warning", ("check", "fixme/SKILL.md", "--output-format", "junit")))
    assert run.returncode == 0
    root = ET.fromstring(run.stdout)
    assert root.attrib["failures"] == "0"
    assert root.find(".//failure") is None
    assert "warning[FM007]" in "".join(root.itertext())


def test_xunit_dialect_is_not_silently_aliased(tmp_path):
    _, run = run_probe(tmp_path, Case("unsupported", ("check", "valid_skill.md", "--output-format", "xunit")))
    assert run.returncode == 2
    assert run.stdout == b""
    assert b"junit" in run.stderr
