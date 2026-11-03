"""GitHub workflow escaping, honest source positions, and deterministic output."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from skilllint.models import FileResults, ValidationIssue, ValidationResult
from skilllint.reporting_github import emit_github, github_lines, workflow_command
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


def test_official_property_and_data_escaping_are_distinct() -> None:
    value = "a%0A,b:c\r\n::error::injected"
    assert workflow_command("error", {"file": value, "title": value}, value) == (
        "::error file=a%250A%2Cb%3Ac%0D%0A%3A%3Aerror%3A%3Ainjected,"
        "title=a%250A%2Cb%3Ac%0D%0A%3A%3Aerror%3A%3Ainjected::"
        "a%250A,b:c%0D%0A::error::injected"
    )


@given(st.text())
def test_untrusted_text_cannot_inject_another_command(value: str) -> None:
    command = workflow_command("warning", {"file": value, "title": value}, value)
    assert len(command.splitlines()) == 1
    assert "\x1b" not in command
    command.encode("utf-8")
    properties = command.split("::", 2)[1]
    assert properties.count(",") == 1
    assert properties.count(":") == 0


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (None, "file=plugin,title=FM010"),
        (SourceLocation(path=Path("other.md")), "file=other.md,title=FM010"),
        (
            SourceLocation(path=Path("other.md"), start=SourcePosition(line=4, column=3)),
            "file=other.md,line=4,col=3,title=FM010",
        ),
        (
            SourceLocation(
                path=Path("other.md"), start=SourcePosition(line=4, column=3), end=SourcePosition(line=4, column=8)
            ),
            "file=other.md,line=4,col=3,endColumn=7,title=FM010",
        ),
        (
            SourceLocation(
                path=Path("other.md"), start=SourcePosition(line=4, column=3), end=SourcePosition(line=6, column=1)
            ),
            "file=other.md,line=4,endLine=5,title=FM010",
        ),
        (
            SourceLocation(
                path=Path("other.md"), start=SourcePosition(line=4, column=3), end=SourcePosition(line=6, column=2)
            ),
            "file=other.md,line=4,endLine=6,title=FM010",
        ),
        (
            SourceLocation(
                path=Path("other.md"), start=SourcePosition(line=4, column=3), end=SourcePosition(line=5, column=1)
            ),
            "file=other.md,line=4,col=3,title=FM010",
        ),
        (
            SourceLocation(
                path=Path("other.md"), start=SourcePosition(line=4, column=3), end=SourcePosition(line=4, column=3)
            ),
            "file=other.md,line=4,col=3,title=FM010",
        ),
    ],
)
def test_known_source_only_and_half_open_ranges(source: SourceLocation | None, expected: str) -> None:
    assert github_lines(_results(_issue(source_location=source, line=90), path=Path("plugin"))) == [
        f"::error {expected}::name: bad"
    ]


def test_hostile_filename_multiline_message_and_help_are_preserved() -> None:
    path = Path("café 😀%,:\n\r\x1b[31m\udcff/SKILL.md")
    issue = _issue(
        field="f,:", message="A < B & [red]\n::warning::bad", suggestion="fix\rit", docs_url="https://example.test/%0A"
    )
    lines = github_lines(_results(issue, path=path))
    assert len(lines) == len(lines[0].splitlines()) == 1
    assert "café 😀%25%2C%3A%0A%0D\\x1b[31m\\udcff/SKILL.md" in lines[0]
    assert "::f,:: A < B & [red]%0A::warning::bad%0ASuggestion: fix%0Dit%0AHelp: https://example.test/%250A" in lines[0]


def test_order_duplicates_and_path_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    issue = _issue()
    first = _results(issue, issue, path=Path("b.md")) | _results(issue, path=Path("a.md"))
    reverse = _results(issue, path=Path("a.md")) | _results(issue, issue, path=Path("b.md"))
    assert github_lines(first) == github_lines(reverse)
    assert len(github_lines(first)) == 3
    assert github_lines(first)[1] == github_lines(first)[2]
    path = Path("links/../café.md")
    assert github_lines(_results(issue, path=path)) == github_lines(_results(issue, path=tmp_path / path))
    outside = tmp_path.parent / "outside.md"
    assert f"file={outside.as_posix()}" in github_lines(_results(issue, path=outside))[0]


def test_info_is_notice_only_with_verbose_and_clean_is_empty(capsys: pytest.CaptureFixture[str]) -> None:
    emit_github({})
    emit_github(_results(_issue(severity="info")))
    assert capsys.readouterr().out == ""
    emit_github(_results(_issue(severity="info", field="")), verbose=True)
    assert capsys.readouterr().out == "::notice file=SKILL.md,title=FM010::bad\n"


def test_diagnostics_neutralize_split_writes_and_preserve_non_github_stream(capsys: pytest.CaptureFixture[str]) -> None:
    import sys

    from skilllint.reporting_github import github_diagnostics

    with github_diagnostics():
        sys.stderr.write(":")
        sys.stderr.write(":error::bad\ntext ##[error]other\r\x1b[31m\udcff\n")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "%3A%3Aerror%3A%3Abad\ntext ##%5Berror]other\\r\\x1b[31m\\udcff\n"
    sys.stderr.write("::unchanged::\n")
    assert capsys.readouterr().err == "::unchanged::\n"
