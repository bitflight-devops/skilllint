"""Cursor uses the shared YAML recovery contract without hiding invalid input."""

from __future__ import annotations

from pathlib import Path

import pytest
from json_probe_support import CheckResponse
from typer.testing import CliRunner

from skilllint.adapters.cursor import CursorAdapter
from skilllint.plugin_validator import app, validate_file


@pytest.mark.parametrize(
    ("content", "code", "message"),
    [
        ("---\ndescription: [oops\n---\nBody.\n", "FM002", "Invalid YAML syntax"),
        ("---\ndescription: valid\ndescription: duplicate\n---\n", "FM002", "Invalid YAML syntax"),
        ("---\n- description\n---\n", "FM002", "must be a YAML mapping"),
        ("---\nnull\n---\n", "FM002", "must be a YAML mapping"),
        ("---\n42\n---\n", "FM002", "must be a YAML mapping"),
        ("---\ndescription: valid\n", "FM003", "not closed"),
        ("---\ndescription: valid\n---not-a-delimiter\n", "FM003", "not closed"),
    ],
)
def test_invalid_cursor_frontmatter_reports_findings(tmp_path: Path, content: str, code: str, message: str) -> None:
    """Direct adapter, library routing, and real CLI report the same failure."""
    rule = tmp_path / "bad.mdc"
    rule.write_text(content)
    adapter = CursorAdapter()
    violations = adapter.validate(rule)
    assert [issue["code"] for issue in violations] == [code]
    assert message in violations[0]["message"]
    for override in (None, "cursor"):
        assert validate_file(rule, {"cursor": adapter}, platform_override=override) == violations

    result = CliRunner().invoke(app, ["check", str(rule), "--platform", "cursor", "--json"])
    assert result.exit_code == 1, result.output
    response = CheckResponse.model_validate_json(result.stdout)
    assert response.status == "failed"
    assert [issue.code for file in response.files for validator in file.validators for issue in validator.issues] == [
        code
    ]
    assert "Traceback" not in result.output
    assert rule.read_text() == content


@pytest.mark.parametrize("ending", ["---", "---\n", "---\nBody.\n"])
def test_valid_cursor_frontmatter_at_eof(tmp_path: Path, ending: str) -> None:
    """A closing delimiter need not be followed by a newline or body."""
    rule = tmp_path / "valid.mdc"
    rule.write_text(f"---\ndescription: Valid rule\n{ending}")
    assert CursorAdapter().validate(rule) == []


@pytest.mark.parametrize(
    "content",
    [
        "# Manual rule\nBody.\n",
        "----\n# Manual rule\nBody.\n",
        "-----\n---\nBody.\n",
        "---not-a-delimiter\nBody.\n",
        "---\n---\nBody.\n",
    ],
)
def test_cursor_optional_frontmatter_remains_valid(tmp_path: Path, content: str) -> None:
    """Headerless manual rules and empty mappings retain existing behavior."""
    rule = tmp_path / "valid.mdc"
    rule.write_text(content)
    assert CursorAdapter().validate(rule) == []

    result = CliRunner().invoke(app, ["check", str(rule), "--platform", "cursor", "--json"])
    assert result.exit_code == 0, result.output
    response = CheckResponse.model_validate_json(result.stdout)
    assert response.status == "passed"
    assert response.summary.failed == 0
    assert rule.read_text() == content


def test_cursor_colon_recovery_continues_schema_validation(tmp_path: Path) -> None:
    """Recoverable syntax identifies the field and does not hide CU findings."""
    content = "---\ndescription: Use this: when needed\nunknown_field: value\n---\nBody.\n"
    rule = tmp_path / "recovered.mdc"
    rule.write_text(content)

    result = CliRunner().invoke(app, ["check", str(rule), "--platform", "cursor", "--json"])

    assert result.exit_code == 1, result.output
    response = CheckResponse.model_validate_json(result.stdout)
    issues = [issue for file in response.files for validator in file.validators for issue in validator.issues]
    assert {issue.code for issue in issues} == {"FM009", "CU002"}
    recovery = next(issue for issue in issues if issue.code == "FM009")
    assert recovery.field == "description"
    assert recovery.severity == "warning"
    assert rule.read_text() == content


@pytest.mark.parametrize("platform", [None, "claude_code", "cursor", "codex"])
@pytest.mark.parametrize(
    ("frontmatter", "code"),
    [("description: [oops\n---\n", "FM002"), ("- item\n---\n", "FM002"), ("description: valid\n", "FM003")],
)
def test_skill_yaml_failures_remain_structured_across_platforms(
    tmp_path: Path, platform: str | None, frontmatter: str, code: str
) -> None:
    """The existing skill parser still diagnoses unrecoverable input on every route."""
    skill = tmp_path / "valid-skill" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(f"---\n{frontmatter}")
    args = ["check", str(skill), "--json"]
    if platform is not None:
        args.extend(["--platform", platform])

    result = CliRunner().invoke(app, args)

    assert result.exit_code == 1, result.output
    response = CheckResponse.model_validate_json(result.stdout)
    issues = [issue for file in response.files for validator in file.validators for issue in validator.issues]
    assert code in {issue.code for issue in issues}
    assert "Traceback" not in result.output


@pytest.mark.parametrize("platform", [None, "claude_code", "cursor", "codex"])
def test_skill_colon_recovery_keeps_field_validation(tmp_path: Path, platform: str | None) -> None:
    """Recovery still allows subsequent schema validation to identify a bad field."""
    content = "---\nname: valid-skill\ndescription: Use this: when needed\ncontext: invalid\n---\nBody.\n"
    skill = tmp_path / "valid-skill" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(content)
    args = ["check", str(skill), "--json"]
    if platform is not None:
        args.extend(["--platform", platform])

    result = CliRunner().invoke(app, args)

    assert result.exit_code == 1, result.output
    response = CheckResponse.model_validate_json(result.stdout)
    issues = [issue for file in response.files for validator in file.validators for issue in validator.issues]
    assert ("FM009", "description") in {(issue.code, issue.field) for issue in issues}
    assert ("FM006", "context") in {(issue.code, issue.field) for issue in issues}
    assert skill.read_text() == content
