"""Integration coverage for Claude Code agent-frontmatter AG rules.

These tests exercise the boundaries that the rule-level tests do not: CLI
reporting, scan-context discovery, plugin discovery, structured adapter output,
and rule ownership metadata.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from skilllint import plugin_validator
from skilllint.adapters.claude_code.adapter import ClaudeCodeAdapter
from skilllint.adapters.codex.adapter import CodexAdapter
from skilllint.adapters.cursor.adapter import CursorAdapter
from skilllint.plugin_validator import FileResults, ValidationIssue, validate_file, validate_single_path
from skilllint.rule_registry import RULE_REGISTRY
from skilllint.scan_runtime import _discover_validatable_paths

if TYPE_CHECKING:
    from pathlib import Path

    from typer.testing import CliRunner


_DISCARDED_SKILLS_LINE = "skills: 7"
_AG003_AUTHORITY = {
    "origin": "@anthropic-ai/claude-code",
    "reference": "https://www.npmjs.com/package/@anthropic-ai/claude-code/v/2.1.251",
}


def _write_agent(
    path: Path,
    *,
    name: str = "bad-skills",
    skills_lines: tuple[str, ...] = (_DISCARDED_SKILLS_LINE,),
    tools: str | None = None,
) -> Path:
    """Write a syntactically valid agent with caller-selected AG fields."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = [
        "---",
        f"name: {name}",
        "description: Use this agent when testing Claude Code frontmatter integration",
    ]
    if tools is not None:
        frontmatter.append(f"tools: {tools}")
    frontmatter.extend((*skills_lines, "---", "", "Follow the supplied task.", ""))
    path.write_text("\n".join(frontmatter), encoding="utf-8")
    return path


def _all_issues(file_results: FileResults) -> list[ValidationIssue]:
    """Flatten issues emitted by every validator for every checked file."""
    return [
        issue
        for validator_results in file_results.values()
        for _validator_name, result in validator_results
        for issue in (*result.errors, *result.warnings, *result.info)
    ]


def _assert_scan_discovers_one_ag003(scan_root: Path, agent_file: Path) -> None:
    """Prove scanner discovery routes an agent through AG validation once."""
    discovered = _discover_validatable_paths(scan_root)
    assert agent_file in discovered, f"{agent_file} was not discovered from {scan_root}: {discovered}"

    file_results = validate_single_path(agent_file, check=True, fix=False, verbose=False)
    ag003 = [issue for issue in _all_issues(file_results) if issue.code == "AG003"]
    assert len(ag003) == 1, f"Expected one AG003 for {agent_file}, got {ag003}"


def test_direct_agent_check_reports_ag003_warning_once(
    cli_runner: CliRunner, tmp_path: Path, no_color_env: None
) -> None:
    """A discarded agent `skills` value warns once without failing the CLI."""
    agent_file = _write_agent(tmp_path / "agents" / "bad-skills.md")

    result = cli_runner.invoke(plugin_validator.app, ["check", "--no-color", str(agent_file)])

    assert result.exit_code == 0, result.stdout
    assert result.stdout.count("WARN [AG003]") == 1, result.stdout
    assert str(agent_file) in result.stdout


def test_project_scan_recursively_discovers_dot_claude_agent(tmp_path: Path) -> None:
    """Scanning a project root recurses through project .claude/agents."""
    project_root = tmp_path / "project"
    agent_file = _write_agent(project_root / ".claude" / "agents" / "team" / "bad-skills.md")

    _assert_scan_discovers_one_ag003(project_root, agent_file)


def test_personal_style_scan_recursively_discovers_dot_claude_agent(tmp_path: Path) -> None:
    """Scanning a personal-style ~/.claude root recurses through agents."""
    personal_claude = tmp_path / "home" / ".claude"
    agent_file = _write_agent(personal_claude / "agents" / "team" / "bad-skills.md")

    _assert_scan_discovers_one_ag003(personal_claude, agent_file)


def test_arbitrary_directory_scan_discovers_agent(tmp_path: Path) -> None:
    """An explicitly scanned non-provider directory discovers agents/*.md."""
    added_directory = tmp_path / "additional-source"
    agent_file = _write_agent(added_directory / "agents" / "bad-skills.md")

    _assert_scan_discovers_one_ag003(added_directory, agent_file)


def test_plugin_scan_discovers_declared_agent(tmp_path: Path) -> None:
    """A manifest-declared plugin agent is discovered and receives AG003."""
    plugin_root = tmp_path / "fixture-plugin"
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps({"name": "fixture-plugin", "version": "1.0.0", "agents": ["./agents/bad-skills.md"]}),
        encoding="utf-8",
    )
    agent_file = _write_agent(plugin_root / "agents" / "bad-skills.md")

    _assert_scan_discovers_one_ag003(plugin_root, agent_file)


def test_skill_md_does_not_receive_ag003(tmp_path: Path) -> None:
    """The same discarded `skills` value is never judged by the agent-only rule."""
    skill_dir = tmp_path / "skills" / "example-skill"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\n"
        "name: example-skill\n"
        "description: Use this skill when testing agent-rule isolation\n"
        f"{_DISCARDED_SKILLS_LINE}\n"
        "---\n\n"
        "# Example skill\n",
        encoding="utf-8",
    )

    file_results = validate_single_path(skill_file, check=True, fix=False, verbose=False)

    assert all(issue.code != "AG003" for issue in _all_issues(file_results))


def test_warning_only_cli_prints_one_ag002_and_succeeds(
    cli_runner: CliRunner, tmp_path: Path, no_color_env: None
) -> None:
    """One unknown MCP server produces one warning, one warning-file count, and exit zero."""
    agent_file = _write_agent(
        tmp_path / "agents" / "warning-agent.md",
        name="warning-agent",
        skills_lines=("skills:", "  - api-conventions"),
        tools="mcp__Unconfigured__read",
    )
    file_results = validate_single_path(agent_file, check=True, fix=False, verbose=False)
    issues = _all_issues(file_results)
    assert [(issue.code, issue.severity) for issue in issues] == [("AG002", "warning")]

    result = cli_runner.invoke(plugin_validator.app, ["check", "--no-color", "--show-summary", str(agent_file)])

    assert result.exit_code == 0, result.stdout
    assert result.stdout.count("WARN [AG002]") == 1, result.stdout
    assert "Total files: 1" in result.stdout
    assert "Failed: 0" in result.stdout
    assert "Warnings: 1" in result.stdout


def test_structured_claude_validation_preserves_ag003_authority(tmp_path: Path) -> None:
    """Adapter-dispatched validation includes the registry authority in structured output."""
    agent_file = _write_agent(tmp_path / ".claude" / "agents" / "bad-skills.md")
    violations = validate_file(agent_file, {"claude_code": ClaudeCodeAdapter()}, platform_override="claude_code")

    ag003 = [violation for violation in violations if violation.get("code") == "AG003"]
    assert len(ag003) == 1, ag003
    assert ag003[0].get("severity") == RULE_REGISTRY["AG003"].severity
    assert ag003[0].get("authority") == _AG003_AUTHORITY


def test_all_ag_rules_are_registered_for_claude_code_only() -> None:
    """Every AG registry entry declares only the Claude Code platform."""
    ag_entries = [entry for rule_id, entry in RULE_REGISTRY.items() if rule_id.startswith("AG")]

    assert {entry.id for entry in ag_entries} >= {"AG001", "AG002", "AG003"}
    assert all(entry.platforms == ["claude-code"] for entry in ag_entries), ag_entries


def test_only_claude_adapter_owns_the_ag_rule_series() -> None:
    """AG is owned by Claude Code, not the Cursor or Codex adapters."""
    adapters = (ClaudeCodeAdapter(), CursorAdapter(), CodexAdapter())
    owners = {adapter.id() for adapter in adapters if "AG" in adapter.applicable_rules()}

    assert owners == {"claude_code"}
