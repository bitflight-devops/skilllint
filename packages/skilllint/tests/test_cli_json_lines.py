"""Real executable contract checks for per-finding JSONL, plus single-scan probes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from unittest.mock import Mock

import pytest
from cli_probe import CliRun, Endpoints, Sandbox
from default_output_cases import CORE_VARIANTS, Case
from json_probe_support import CheckResponse, Strict, assert_plain, parse, run_probe
from typer.testing import CliRunner

from skilllint import plugin_validator
from skilllint.models import ValidationIssue, ValidationResult
from skilllint.scan_runtime import CheckRun


class Position(Strict):
    """Independently pinned one-based coordinate shape."""

    line: int
    column: int


class Location(Strict):
    """Unknown coordinates must not materialize as line/column one."""

    path: str
    start: Position | None = None
    end: Position | None = None


class Finding(Strict):
    """Independent schema-v1 contract, not imported from the serializer."""

    schema_version: Literal[1]
    path: str
    validator: str
    code: str
    severity: Literal["error", "warning", "info"]
    message: str
    field: str
    source_location: Location | None = None
    suggestion: str | None = None
    docs_url: str | None = None


def _records(run: CliRun) -> list[Finding]:
    assert_plain(run)
    assert not run.stdout.startswith(b"\xef\xbb\xbf")
    assert not run.stdout or run.stdout.endswith(b"\n")
    lines = run.stdout.splitlines()
    assert lines == sorted(lines)
    for line in lines:
        assert line == json.dumps(json.loads(line), ensure_ascii=True, separators=(",", ":")).encode()
    return [Finding.model_validate_json(line) for line in lines]


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
    """The same visible diagnostics and run status survive the new projection."""
    _, actual = run_probe(tmp_path, Case("jsonl", ("check", *args, "--output-format", "json-lines")))
    _, legacy = run_probe(tmp_path, Case("legacy", ("check", *args, "--json")), root="legacy")
    response = parse(CheckResponse, legacy)
    records = _records(actual)
    assert actual.returncode == legacy.returncode
    expected = sorted(
        (
            file.path,
            validator.name,
            issue.code,
            issue.severity,
            issue.message,
            issue.field,
            issue.suggestion,
            issue.docs_url,
        )
        for file in response.files
        for validator in file.validators
        for issue in validator.issues
    )
    assert (
        sorted((r.path, r.validator, r.code, r.severity, r.message, r.field, r.suggestion, r.docs_url) for r in records)
        == expected
    )


def test_real_frontmatter_location_is_in_original_source(tmp_path: Path) -> None:
    """A real rule's YAML key span remains separate from its semantic label."""
    _, run = run_probe(tmp_path, Case("located", ("check", "invalid-skill/SKILL.md", "--output-format=json-lines")))
    record = next(r for r in _records(run) if r.code == "FM010")
    assert record.source_location == Location(
        path="invalid-skill/SKILL.md", start=Position(line=2, column=1), end=Position(line=2, column=5)
    )
    assert record.field == "name"


def test_clean_scan_has_no_records_even_with_progress_summary_or_recording(tmp_path: Path) -> None:
    """A clean result is an empty byte stream, including with a human sidecar."""
    sandbox, run = run_probe(
        tmp_path,
        Case(
            "clean",
            (
                "check",
                "valid_skill.md",
                "--output-format",
                "json-lines",
                "--show-progress",
                "--show-summary",
                "--record",
                "out.svg",
            ),
        ),
    )
    assert run.returncode == 0
    assert run.stdout == b""
    assert b"Validation" in (sandbox.case / "out.svg").read_bytes()


def test_output_is_identical_in_all_terminal_environments(tmp_path: Path) -> None:
    """A pty, forced color and narrow widths cannot wrap or color JSONL."""
    case = Case("environment", ("check", "plug", "--output-format", "json-lines", "--show-progress", "--show-summary"))
    runs = [run_probe(tmp_path, case, root=variant.id, variant=variant)[1] for variant in CORE_VARIANTS]
    for run in runs:
        assert _records(run)
        assert run.stdout == runs[0].stdout
        assert run.returncode == runs[0].returncode == 1


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("missing.md",),
        ("weird.xyz",),
        ("valid_skill.md", "--json"),
        ("valid_skill.md", "--tokens-only"),
        ("valid_skill.md", "--check", "--fix"),
        ("valid_skill.md", "--platform", "bogus"),
        ("plug", "--filter-type", "bogus"),
        ("plug", "--filter", "*", "--filter-type", "skills"),
        ("invalid-skill/SKILL.md", "--record", "missing/out.svg"),
        ("invalid-skill/SKILL.md", "--record", "out.txt"),
    ],
)
def test_usage_and_record_write_errors_keep_stdout_empty(args: tuple[str, ...], tmp_path: Path) -> None:
    """Failures to invoke or export never masquerade as finding records."""
    _, run = run_probe(tmp_path, Case("invalid", ("check", *args, "--output-format", "json-lines")))
    assert run.returncode == 2
    assert run.stdout == b""
    assert run.stderr
    assert_plain(run)


def test_recording_stays_human_without_changing_findings(tmp_path: Path) -> None:
    """--record is the existing human sidecar, not JSONL disguised as a screenshot."""
    base = ("check", "invalid-skill/SKILL.md", "--output-format", "json-lines", "--no-color")
    sandbox, recorded = run_probe(tmp_path, Case("recorded", (*base, "--record", "out.html")))
    _, plain = run_probe(tmp_path, Case("plain", base), root="plain")
    assert recorded.stdout == plain.stdout
    assert recorded.returncode == plain.returncode == 1
    html = (sandbox.case / "out.html").read_text()
    assert "FrontmatterValidator" in html
    assert "FM010" in html
    assert "schema_version" not in html


def test_unknown_output_format_is_plain_usage_error(tmp_path: Path) -> None:
    """An unsupported format cannot silently select human output."""
    _, run = run_probe(tmp_path, Case("format", ("check", "valid_skill.md", "--output-format", "unsupported")))
    assert run.returncode == 2
    assert run.stdout == b""
    assert b"Invalid value" in run.stderr
    assert_plain(run)


def test_warning_only_and_info_keep_existing_exit_and_visibility(tmp_path: Path) -> None:
    """Warnings pass, and info appears only with the existing --verbose flag."""

    def setup(sandbox: Sandbox, _endpoints: Endpoints) -> None:
        path = sandbox.case / "warn/SKILL.md"
        path.parent.mkdir()
        path.write_text("---\nname: warn\ndescription: A sufficiently long description of this example.\n---\nBody.\n")

    args = ("check", "warn/SKILL.md", "--output-format", "json-lines")
    _, regular = run_probe(tmp_path, Case("warning", args, setup=setup))
    _, verbose = run_probe(tmp_path, Case("verbose", (*args, "--verbose"), setup=setup), root="verbose")
    assert regular.returncode == verbose.returncode == 0
    assert any(r.severity == "warning" for r in _records(regular))
    assert all(r.severity != "info" for r in _records(regular))
    assert any(r.severity == "info" for r in _records(verbose))


def test_fix_and_record_collect_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Recording the human view of a fix run never starts a second scan."""
    path = tmp_path / "fixme/SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: fixme\ndescription: >-\n  Use when testing. A multiline description for the fixture.\n"
        "tools:\n  - Read\n  - Grep\n---\nBody.\n"
    )
    collect = Mock(wraps=plugin_validator.collect_validation_results)
    monkeypatch.setattr(plugin_validator, "collect_validation_results", collect)
    result = CliRunner().invoke(
        plugin_validator.app,
        ["check", str(path), "--fix", "--output-format", "json-lines", "--record", str(tmp_path / "out.svg")],
    )
    assert result.exit_code == 0
    assert collect.call_count == 1
    assert "  - Read" not in path.read_text()


def test_exit_status_comes_from_results_not_visible_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed validator with no records still fails; a passing error-list result passes."""
    path = tmp_path / "SKILL.md"
    path.touch()
    args = ["check", str(path), "--output-format", "json-lines"]
    for passed in (False, True):
        issues = [ValidationIssue(field="test", code="FM001", severity="error", message="test")] if passed else []
        outcome = CheckRun(
            results={path: [("test", ValidationResult(passed=passed, errors=issues, warnings=[], info=[]))]}, fixes=[]
        )
        monkeypatch.setattr(plugin_validator, "collect_validation_results", Mock(return_value=outcome))
        result = CliRunner().invoke(plugin_validator.app, args)
        assert result.exit_code == (0 if passed else 1)
        assert bool(result.stdout) is passed
