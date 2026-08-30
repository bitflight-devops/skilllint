"""Expected one-owner findings for consolidated rule properties."""

from __future__ import annotations

from pathlib import Path

import pytest

from skilllint.adapters import load_adapters
from skilllint.plugin_validator import validate_file
from skilllint.token_counter import TOKEN_ERROR_THRESHOLD, TOKEN_WARNING_THRESHOLD


@pytest.fixture
def adapters() -> dict:
    """Return the registered adapters for the integration validation path."""
    return {adapter.id(): adapter for adapter in load_adapters()}


def _codes(path: Path, adapters: dict) -> list[str]:
    """Return emitted rule codes in validator order."""
    return [violation["code"] for violation in validate_file(path, adapters, platform_override="claude_code")]


def test_invalid_skill_name_has_one_fm010_finding(tmp_path: Path, adapters: dict) -> None:
    """Malformed skill names have FM010 as their sole syntax finding."""
    skill_dir = tmp_path / "bad-name"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("---\nname: Bad_Name!\ndescription: Use this skill when testing names\n---\n\nBody.\n")

    name_codes = set(_codes(skill_md, adapters)) & {"AS001", "FM010", "SK001", "SK002", "SK003"}
    assert name_codes == {"FM010"}
    assert _codes(skill_md, adapters).count("FM010") == 1


def test_valid_name_in_wrong_directory_has_only_directory_finding(tmp_path: Path, adapters: dict) -> None:
    """A valid name in a mismatched directory has no syntax duplicate."""
    skill_dir = tmp_path / "wrong-directory"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("---\nname: right-name\ndescription: Use this skill when testing directories\n---\n\nBody.\n")

    name_codes = set(_codes(skill_md, adapters)) & {"AS001", "AS002", "FM010", "SK001", "SK002", "SK003"}
    assert name_codes == {"FM010"}


def test_missing_description_has_only_fm001_finding(tmp_path: Path, adapters: dict) -> None:
    """A missing description is reported only by FM001."""
    skill_dir = tmp_path / "missing-description"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("---\nname: missing-description\n---\n\nBody.\n")

    description_codes = set(_codes(skill_md, adapters)) & {"FM001", "SK004", "SK005"}
    assert description_codes == {"FM001"}


@pytest.mark.parametrize("threshold", [TOKEN_WARNING_THRESHOLD + 100, TOKEN_ERROR_THRESHOLD + 100])
def test_over_threshold_body_has_one_complexity_finding(tmp_path: Path, adapters: dict, threshold: int) -> None:
    """An oversized body has one SK006/SK007 finding and no AS005."""
    skill_dir = tmp_path / "large-body"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        "---\nname: large-body\ndescription: Use this skill when testing body limits\n---\n\n" + ("word " * threshold)
    )

    emitted = set(_codes(skill_md, adapters))
    complexity_codes = emitted & {"SK006", "SK007"}
    assert len(complexity_codes) == 1
    assert "AS005" not in emitted, f"AS005 was retired into SK006/SK007, got: {sorted(emitted)}"


def test_parser_failure_has_only_fm002_finding(tmp_path: Path, adapters: dict) -> None:
    """Malformed YAML is owned by FM002."""
    skill_dir = tmp_path / "parser-failure"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("---\ndescription: [unclosed bracket\n---\n\nBody.\n")

    parser_codes = set(_codes(skill_md, adapters))
    assert "AS004" not in parser_codes
    assert "FM002" in parser_codes
    assert _codes(skill_md, adapters).count("FM002") == 1
    # AS001 is expected here and is not a duplicate: unparseable YAML yields an
    # empty frontmatter dict, so the skill genuinely declares no name. FM002
    # reports the syntax error; AS001 reports the absent field.
    assert "AS001" in parser_codes


__all__ = []


def test_colon_recovery_is_reported_without_fix(tmp_path: Path, adapters: dict) -> None:
    """An unquoted colon is reported on a check-only run.

    ``safe_load_yaml_with_colon_fix`` quotes the value in memory and reports no
    YAML error, so without a diagnostic the unchanged invalid source produces
    nothing at all. FM009 owns the claim; AS004 used to duplicate it.
    """
    skill_dir = tmp_path / "colon-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("---\nname: colon-skill\ndescription: Use this: when testing colons\n---\n\nBody.\n")

    codes = _codes(skill_md, adapters)
    assert "AS004" not in codes
    assert codes.count("FM009") == 1, f"Expected one FM009 finding, got: {codes}"


def test_plugin_agent_colon_recovery_is_reported(tmp_path: Path) -> None:
    """The PA001 ingestion path reports colon recovery under FM009."""
    from skilllint.plugin_validator import PluginAgentFrontmatterValidator

    plugin_dir = tmp_path / "probe-plugin"
    (plugin_dir / ".claude-plugin").mkdir(parents=True)
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        '{"name": "probe-plugin", "version": "0.0.1", "description": "Probe plugin for colon recovery"}'
    )
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "probe-agent.md").write_text(
        "---\nname: probe-agent\ndescription: Use this: when testing colons\n---\n\nBody.\n"
    )

    result = PluginAgentFrontmatterValidator().validate(plugin_dir)
    codes = [issue.code for issue in result.errors + result.warnings + result.info]

    assert "FM009" in codes, f"Expected FM009 for the recovered colon, got: {codes}"
    assert "AS004" not in codes
