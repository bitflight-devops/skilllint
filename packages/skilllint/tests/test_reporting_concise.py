"""Plain one-line diagnostic rendering without guessed source positions."""

from __future__ import annotations

from pathlib import Path

import pytest

from skilllint.models import FileResults, ValidationIssue, ValidationResult
from skilllint.reporting import concise_lines, emit_concise
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


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (None, "plugin: error[FM010] name: bad"),
        (SourceLocation(path=Path("other.md")), "other.md: error[FM010] name: bad"),
        (
            SourceLocation(path=Path("café/SKILL.md"), start=SourcePosition(line=4, column=3)),
            "café/SKILL.md:4:3: error[FM010] name: bad",
        ),
    ],
)
def test_actual_source_and_known_positions_only(source: SourceLocation | None, expected: str) -> None:
    issue = _issue(source_location=source, line=90)
    assert concise_lines(_results(issue, path=Path("plugin"))) == [expected]


def test_multiline_control_and_unicode_values_remain_one_literal_line() -> None:
    value = "café 😀 [bold]\n\r\t\x00\x1b[31m\u0085\u2028\u2029\udcff"
    issue = _issue(field=value, message=value)
    lines = concise_lines(_results(issue, path=Path(value)))
    assert len(lines) == len(lines[0].splitlines()) == 1
    assert "café 😀 [bold]" in lines[0]
    assert r"\n\r\t\x00\x1b[31m\x85\u2028\u2029\udcff" in lines[0]
    assert "\x1b" not in lines[0]
    assert "\x00" not in lines[0]


def test_order_is_stable_and_duplicates_are_retained() -> None:
    issue = _issue()
    first = _results(issue, issue, path=Path("b.md")) | _results(issue, path=Path("a.md"))
    reverse = _results(issue, path=Path("a.md")) | _results(issue, issue, path=Path("b.md"))
    assert concise_lines(first) == concise_lines(reverse)
    assert concise_lines(first) == ["a.md: error[FM010] name: bad", *["b.md: error[FM010] name: bad"] * 2]


def test_paths_are_relative_without_resolving_symlinks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    path = Path("links/../café.md")
    assert concise_lines(_results(_issue(), path=path)) == concise_lines(_results(_issue(), path=tmp_path / path))
    outside = tmp_path.parent / "outside.md"
    assert concise_lines(_results(_issue(), path=outside))[0].startswith(outside.as_posix() + ": ")


def test_info_requires_verbose_and_clean_scan_is_empty(capsys: pytest.CaptureFixture[str]) -> None:
    emit_concise({})
    emit_concise(_results(_issue(severity="info")))
    assert capsys.readouterr().out == ""
    emit_concise(_results(_issue(severity="info", field="")), verbose=True)
    assert capsys.readouterr().out == "SKILL.md: info[FM010] bad\n"
