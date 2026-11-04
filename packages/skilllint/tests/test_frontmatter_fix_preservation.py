"""Regression coverage for explicit edits to authored frontmatter."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from skilllint.frontmatter_core import extract_frontmatter
from skilllint.frontmatter_yaml import _safe_load_yaml
from skilllint.plugin_validator import app
from skilllint.validators.frontmatter import FrontmatterValidator

if TYPE_CHECKING:
    from pathlib import Path

    from typer.testing import CliRunner


@pytest.mark.parametrize("relative_path", ["skills/sample/SKILL.md", "agents/sample.md", "commands/sample.md"])
@pytest.mark.parametrize("description", ["|", ">-", '"Use this\\nwhen testing."'])
def test_description_fix_preserves_unrelated_authored_fields(
    tmp_path: Path, relative_path: str, description: str
) -> None:
    """A validated model is a view, never the replacement YAML document."""
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True)
    block = "\n  Use this\n  when testing." if description in {"|", ">-"} else ""
    body = "\n\n# Body\n\n```yaml\nexample: |\n  Keep this unchanged.\n```\n"
    source = (
        f"---\nname: sample\ndescription: {description}{block}\n"
        "# unrelated nulls and coercible values\n"
        "extension-mode: null # explicit extension null\n"
        "model: null # explicit schema null\n"
        "allowed-tools: 42\n"
        "user-invocable: 'false'\n"
        "maxTurns: '7'\n"
        "permission_mode: default\n"
        'extension: {nested: [null, "quoted", true]}\n'
        "notes: |-\n  Preserve this\n  multiline extension.\n"
        "skills: [null, Build]\n"
        f"---\n{body}"
    )
    path.write_text(source, encoding="utf-8")
    before_text, *_ = extract_frontmatter(source)
    assert before_text is not None
    before = _safe_load_yaml(before_text)
    assert isinstance(before, dict)

    validator = FrontmatterValidator()
    fixes = validator.fix(path)

    fixed = path.read_text(encoding="utf-8")
    after_text, *_ = extract_frontmatter(fixed)
    assert after_text is not None
    after = _safe_load_yaml(after_text)
    assert after == {**before, "description": "Use this when testing."}
    assert fixes == ["Normalized multiline description to single line"]
    assert "# unrelated nulls and coercible values" in fixed
    assert "# explicit extension null" in fixed
    assert "# explicit schema null" in fixed
    assert "user-invocable: 'false'" in fixed
    assert "maxTurns: '7'" in fixed
    assert "notes: |-\n  Preserve this\n  multiline extension." in fixed
    assert fixed.endswith(f"---\n{body}")
    assert validator.fix(path) == []
    assert path.read_text(encoding="utf-8") == fixed


def test_description_fix_preserves_alias_value_and_block_comment(tmp_path: Path) -> None:
    path = tmp_path / "agents" / "sample.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: sample\ndescription: &description | # explain this\n"
        "  Use this\n  when testing.\n"
        "extension: *description\n---\n\nBody.\n",
        encoding="utf-8",
    )

    fixes = FrontmatterValidator().fix(path)

    fixed = path.read_text(encoding="utf-8")
    text, *_ = extract_frontmatter(fixed)
    assert text is not None
    assert _safe_load_yaml(text) == {
        "name": "sample",
        "description": "Use this when testing.",
        "extension": "Use this\nwhen testing.\n",
    }
    assert fixes == ["Normalized multiline description to single line"]
    assert "# explain this" in fixed


def test_unrelated_block_scalar_is_not_a_fix(tmp_path: Path) -> None:
    path = tmp_path / "agents" / "sample.md"
    path.parent.mkdir()
    original = "---\nname: sample\ndescription: Use this when testing.\nnotes: |\n  Keep me.\n---\n\nBody.\n"
    path.write_text(original, encoding="utf-8")

    assert FrontmatterValidator().fix(path) == []
    assert path.read_text(encoding="utf-8") == original


@pytest.mark.parametrize("name", ["", "name: wrong\n", "name: null\n"])
def test_name_and_tool_fixes_preserve_unrelated_nulls_and_body(tmp_path: Path, name: str) -> None:
    path = tmp_path / "sample" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        f"---\n{name}description: Use this when testing.\n"
        "allowed-tools: [Read, Grep]\nmodel: null # keep me\nextension: null\n---\n\n\nBody.\n",
        encoding="utf-8",
    )

    fixes = FrontmatterValidator().fix(path)

    assert len(fixes) == 2
    assert "name" in fixes[0]
    assert fixes[1] == "Converted allowed-tools from YAML array to comma-separated string"
    fixed = path.read_text(encoding="utf-8")
    text, *_ = extract_frontmatter(fixed)
    assert text is not None
    assert _safe_load_yaml(text) == {
        "name": "sample",
        "description": "Use this when testing.",
        "allowed-tools": "Read, Grep",
        "model": None,
        "extension": None,
    }
    assert "# keep me" in fixed
    assert fixed.endswith("---\n\n\nBody.\n")


def test_cli_fix_reports_only_changed_fields_and_preserves_nulls(cli_runner: CliRunner, tmp_path: Path) -> None:
    path = tmp_path / "sample" / "SKILL.md"
    path.parent.mkdir()
    source = (
        "---\nname: sample\ndescription: |\n  Use this\n  when testing.\n"
        "model: null\nextension-mode: null\n---\n\n# Instructions\nDo the work.\n"
    )
    path.write_text(source, encoding="utf-8")

    result = cli_runner.invoke(app, ["check", str(path), "--fix", "--json"])

    assert result.exit_code == 0, result.output
    response = json.loads(result.stdout)
    text, *_ = extract_frontmatter(path.read_text(encoding="utf-8"))
    assert text is not None
    assert _safe_load_yaml(text) == {
        "name": "sample",
        "description": "Use this when testing.",
        "model": None,
        "extension-mode": None,
    }
    assert [fix["description"] for fix in response["fixes"]] == ["Normalized multiline description to single line"]
    assert all(fix["codes"] == ["FM004"] for fix in response["fixes"])
    first = path.read_bytes()
    second_result = cli_runner.invoke(app, ["check", str(path), "--fix", "--json"])
    assert second_result.exit_code == 0, second_result.output
    assert json.loads(second_result.stdout)["fixes"] == []
    assert path.read_bytes() == first


def test_colon_repair_reports_its_field_and_keeps_unrelated_bytes(tmp_path: Path) -> None:
    path = tmp_path / "agents" / "sample.md"
    path.parent.mkdir()
    original = (
        "---\nname: sample\ndescription: Use this when testing.\n"
        "extension: Note: this needs quoting\nmodel: null # retain me\n---\n\n\nBody.\n"
    )
    path.write_text(original, encoding="utf-8")

    fixes = FrontmatterValidator().fix(path)

    assert fixes == ["Quoted extension value containing unquoted colon"]
    fixed = path.read_text(encoding="utf-8")
    assert 'extension: "Note: this needs quoting"' in fixed
    assert "model: null # retain me" in fixed
    assert fixed.endswith("---\n\n\nBody.\n")
