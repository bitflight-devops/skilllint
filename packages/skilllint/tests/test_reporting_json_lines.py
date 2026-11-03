"""The standalone finding schema preserves diagnostics without guessing locations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skilllint.models import FileResults, ValidationIssue, ValidationResult
from skilllint.reporting_json_lines import emit_json_lines, json_lines_records
from skilllint.source_location import SourceLocation, SourcePosition


def _issue(**updates: object) -> ValidationIssue:
    return ValidationIssue.model_validate({
        "field": "name",
        "severity": "error",
        "message": "bad",
        "code": "FM010",
        **updates,
    })


def _results(*issues: ValidationIssue, path: Path = Path("SKILL.md")) -> FileResults:
    return {
        path: [
            (
                "ExampleValidator",
                ValidationResult(
                    passed=not any(issue.severity == "error" for issue in issues),
                    errors=[issue for issue in issues if issue.severity == "error"],
                    warnings=[issue for issue in issues if issue.severity == "warning"],
                    info=[issue for issue in issues if issue.severity == "info"],
                ),
            )
        ]
    }


def test_unknown_source_does_not_guess_from_legacy_field_or_line() -> None:
    """Semantic labels and legacy line values are not actual source metadata."""
    record = json.loads(json_lines_records(_results(_issue(field="nested.md:90", line=90)))[0])
    assert record == {
        "schema_version": 1,
        "path": "SKILL.md",
        "validator": "ExampleValidator",
        "code": "FM010",
        "severity": "error",
        "message": "bad",
        "field": "nested.md:90",
    }


def test_actual_source_is_separate_from_checked_aggregate_target() -> None:
    """The source path and half-open span survive a plugin-level aggregation."""
    location = SourceLocation(
        path=Path("plugin/skills/café/SKILL.md"),
        start=SourcePosition(line=4, column=3),
        end=SourcePosition(line=5, column=1),
    )
    issue = _issue(source_location=location, suggestion="Use café", docs_url="skilllint rule FM010")
    record = json.loads(json_lines_records(_results(issue, path=Path("plugin")))[0])
    assert record["path"] == "plugin"
    assert record["source_location"] == {
        "path": "plugin/skills/café/SKILL.md",
        "start": {"line": 4, "column": 3},
        "end": {"line": 5, "column": 1},
    }
    assert record["suggestion"] == "Use café"
    assert record["docs_url"] == "skilllint rule FM010"


def test_file_only_and_point_locations_do_not_invent_positions() -> None:
    """Known files differ from unknown sources, and points need no range end."""
    file_location = SourceLocation(path=Path("elsewhere.md"))
    point = SourceLocation(path=Path("elsewhere.md"), start=SourcePosition(line=2, column=5))
    file_record = json.loads(json_lines_records(_results(_issue(source_location=file_location)))[0])
    point_record = json.loads(json_lines_records(_results(_issue(source_location=point)))[0])
    assert file_record["source_location"] == {"path": "elsewhere.md"}
    assert point_record["source_location"] == {"path": "elsewhere.md", "start": {"line": 2, "column": 5}}


def test_json_escaping_is_lossless_and_always_one_physical_line() -> None:
    """Quotes, Unicode, separators, CR/LF, terminal controls and markup are data."""
    unusual = 'café 😀 "quote" \\ slash\n\r\t\x00\x1b[31m\u0085\u2028\u2029[bold]'
    issue = _issue(message=unusual, field=unusual, suggestion=unusual, docs_url=unusual)
    line = json_lines_records(_results(issue, path=Path('space " , : café.md')))[0]
    assert line.isascii()
    assert len(line.splitlines()) == 1
    assert "\x1b" not in line
    assert "\x00" not in line
    record = json.loads(line)
    assert all(record[field] == unusual for field in ("message", "field", "suggestion", "docs_url"))
    assert record["path"] == 'space " , : café.md'


def test_order_is_deterministic_and_duplicate_findings_are_preserved() -> None:
    """Input traversal order cannot reorder output or erase repeated diagnostics."""
    issue = _issue()
    differing = _issue(message="different")
    forward = _results(issue, differing, issue, path=Path("b.md")) | _results(issue, path=Path("a.md"))
    reverse = _results(issue, path=Path("a.md")) | _results(differing, issue, issue, path=Path("b.md"))
    records = json_lines_records(forward)
    assert records == json_lines_records(reverse) == sorted(records)
    assert len(records) == 4
    assert records.count(json_lines_records(_results(issue, path=Path("b.md")))[0]) == 2


def test_surrogateescape_names_remain_distinct_and_reversible() -> None:
    """Filesystem bytes that are not UTF-8 are escaped, never replaced or rejected."""
    paths = [Path("bad-\udcff.md"), Path("bad-\udcfe.md")]
    results: FileResults = {}
    for path in paths:
        results.update(_results(_issue(source_location=SourceLocation(path=path)), path=path))
    records = [json.loads(line) for line in json_lines_records(results)]
    assert {record["path"] for record in records} == {str(path) for path in paths}
    assert all(record["source_location"]["path"] == record["path"] for record in records)


def test_paths_are_relative_without_resolving_symlinks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Equivalent absolute/relative inputs have portable, cwd-relative records."""
    monkeypatch.chdir(tmp_path)
    relative = Path("links/../missing café.md")
    absolute = tmp_path / relative
    a = _issue(source_location=SourceLocation(path=absolute))
    b = _issue(source_location=SourceLocation(path=relative))
    assert json_lines_records(_results(a, path=absolute)) == json_lines_records(_results(b, path=relative))
    assert json.loads(json_lines_records(_results(a, path=absolute))[0])["path"] == "links/../missing café.md"


def test_external_absolute_paths_keep_their_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An absolute source outside cwd remains absolute rather than changing its route."""
    working = tmp_path / "working"
    working.mkdir()
    monkeypatch.chdir(working)
    path = tmp_path / "outside.md"
    record = json.loads(json_lines_records(_results(_issue(source_location=SourceLocation(path=path)), path=path))[0])
    assert record["path"] == record["source_location"]["path"] == path.as_posix()


def test_information_requires_verbose_and_empty_output_is_truly_empty(capsys: pytest.CaptureFixture[str]) -> None:
    """Clean and info-only default scans do not emit a blank line or summary."""
    results = _results(_issue(severity="info"))
    emit_json_lines(results)
    emit_json_lines({})
    assert capsys.readouterr().out == ""
    emit_json_lines(results, verbose=True)
    output = capsys.readouterr().out
    assert output.endswith("\n")
    assert output.count("\n") == 1
    assert json.loads(output)["severity"] == "info"
