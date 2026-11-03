"""GitLab's required report shape, paths, fingerprints and unsupported findings."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from skilllint.models import FileResults, ValidationIssue, ValidationResult
from skilllint.reporting_gitlab import emit_gitlab, gitlab_report
from skilllint.source_location import SourceLocation, SourcePosition


def _issue(**updates: object) -> ValidationIssue:
    return ValidationIssue.model_validate({
        "field": "name",
        "severity": "error",
        "message": "bad",
        "code": "FM010",
        **updates,
    })


def _results(*issues: ValidationIssue, path: Path = Path("SKILL.md"), validator: str = "Example") -> FileResults:
    return {
        path: [
            (
                validator,
                ValidationResult(
                    passed=not any(issue.severity == "error" for issue in issues),
                    errors=[issue for issue in issues if issue.severity == "error"],
                    warnings=[issue for issue in issues if issue.severity == "warning"],
                    info=[issue for issue in issues if issue.severity == "info"],
                ),
            )
        ]
    }


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / "SKILL.md").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub/other.md").touch()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_contract_severity_and_file_level_anchor(repository, capsys):
    issues = [_issue(severity=severity) for severity in ("error", "warning", "info")]
    emit_gitlab(_results(*issues), verbose=True)
    captured = capsys.readouterr()
    assert captured.err == ""
    assert not captured.out.startswith("\ufeff")
    findings = json.loads(captured.out)
    assert len(findings) == 3
    assert {finding["severity"] for finding in findings} == {"major", "minor", "info"}
    for finding in findings:
        assert set(finding) == {"description", "check_name", "fingerprint", "severity", "location"}
        assert finding["check_name"] == "FM010"
        assert finding["location"] == {"path": "SKILL.md", "lines": {"begin": 1}}
        assert "file-level; line 1 is a display anchor, not a source position" in finding["description"]
        assert len(finding["fingerprint"]) == 64
    assert len({finding["fingerprint"] for finding in findings}) == 3


def test_source_precedes_target_and_legacy_line_is_not_a_position(repository):
    source = SourceLocation(path=repository / "sub/other.md", start=SourcePosition(line=3, column=8))
    findings, diagnostics = gitlab_report(_results(_issue(source_location=source, line=99), path=repository))
    assert diagnostics == []
    assert findings[0].location.path == "sub/other.md"
    assert findings[0].location.lines.begin == 3
    assert "display anchor" not in findings[0].description
    file_level, _ = gitlab_report(_results(_issue(source_location=SourceLocation(path=source.path), line=99)))
    assert file_level[0].location.lines.begin == 1
    assert "display anchor" in file_level[0].description


def test_nested_cwd_worktree_marker_and_parent_paths(repository, monkeypatch):
    # A worktree uses a .git file, not a directory.
    (repository / ".git").rmdir()
    (repository / ".git").write_text("gitdir: elsewhere")
    monkeypatch.chdir(repository / "sub")
    relative, _ = gitlab_report(_results(_issue(), path=Path("../SKILL.md")))
    absolute, _ = gitlab_report(_results(_issue(), path=repository / "SKILL.md"))
    assert relative == absolute
    assert relative[0].location.path == "SKILL.md"


def test_exported_source_uses_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("skilllint.reporting_gitlab._repository_root", lambda: tmp_path)
    (tmp_path / "SKILL.md").touch()
    findings, diagnostics = gitlab_report(_results(_issue()))
    assert diagnostics == []
    assert findings[0].location.path == "SKILL.md"


def test_global_external_missing_and_source_failure_are_disclosed(repository, capsys):
    outside = repository.parent / "outside.md"
    outside.touch()
    issue = _issue(message="bad\n\x1b[31m", suggestion="fix", docs_url="https://example.test/rule")
    results = (
        _results(issue, path=repository) | _results(issue, path=outside) | _results(issue, path=Path("missing.md"))
    )
    results |= _results(_issue(source_location=SourceLocation(path=outside)), path=Path("SKILL.md"))
    emit_gitlab(results)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == []
    assert len(captured.err.splitlines()) == 4
    assert "\x1b" not in captured.err
    assert "\\n\\u001b[31m" in captured.err
    assert '"suggestion": "fix"' in captured.err
    assert '"docs_url": "https://example.test/rule"' in captured.err
    assert "source_location" in captured.err
    assert "use json-lines for a complete report" in captured.err


def test_symlink_identity_and_escape(repository):
    (repository / "alias.md").symlink_to(repository / "SKILL.md")
    findings, diagnostics = gitlab_report(_results(_issue(), path=Path("alias.md")))
    assert diagnostics == []
    assert findings[0].location.path == "alias.md"
    outside = repository.parent / "outside.md"
    outside.touch()
    (repository / "external.md").symlink_to(outside)
    findings, diagnostics = gitlab_report(_results(_issue(), path=Path("external.md")))
    assert findings == []
    assert len(diagnostics) == 1


def test_stable_fingerprints_reordering_relocation_and_line_movement(repository):
    def issue(line, **changes):
        return _issue(
            source_location=SourceLocation(path=Path("SKILL.md"), start=SourcePosition(line=line, column=1)), **changes
        )

    first, _ = gitlab_report(_results(issue(2), issue(8), issue(2)))
    reverse, _ = gitlab_report(_results(issue(2), issue(2), issue(8)))
    shifted, _ = gitlab_report(_results(issue(4), issue(10), issue(4)))
    assert first == reverse
    assert len({finding.fingerprint for finding in first}) == 3
    assert [finding.fingerprint for finding in first] == [finding.fingerprint for finding in shifted]
    relative, _ = gitlab_report(_results(_issue()))
    absolute, _ = gitlab_report(_results(_issue(), path=repository / "SKILL.md"))
    assert relative == absolute
    severity, _ = gitlab_report(_results(_issue(severity="warning", suggestion="new help")))
    assert relative[0].fingerprint == severity[0].fingerprint
    other_validator, _ = gitlab_report(_results(_issue(), validator="Other"))
    assert relative[0].fingerprint != other_validator[0].fingerprint


def test_unsupported_info_is_hidden_without_verbose_and_empty_is_array(repository, capsys):
    emit_gitlab({})
    assert capsys.readouterr().out == "[]\n"
    emit_gitlab(_results(_issue(severity="info"), path=repository))
    assert capsys.readouterr().err == ""
    emit_gitlab(_results(_issue(severity="info"), path=repository), verbose=True)
    assert "omitted" in capsys.readouterr().err


@given(st.text())
def test_message_round_trip_has_no_raw_terminal_controls(value):
    # The module itself supplies a real in-repository source independent of fixtures.
    issue = _issue(
        message=value,
        field="",
        source_location=SourceLocation(path=Path(__file__), start=SourcePosition(line=1, column=1)),
    )
    findings, diagnostics = gitlab_report(_results(issue))
    assert diagnostics == []
    raw = json.dumps([finding.model_dump() for finding in findings], ensure_ascii=True)
    assert json.loads(raw)[0]["description"] == value
    assert "\x1b" not in raw
    raw.encode("utf-8")
