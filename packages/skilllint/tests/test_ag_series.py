"""Tests for the AG-series agent frontmatter rules (AG001-AG003).

AG001/AG002 port the tools-field checks that used to live in AS007/AS008
before PR #108 scoped the AS family to SKILL.md only, leaving agent `tools`
frontmatter unvalidated (issue #109). AG003 gives the `skills` YAML-list
shape check (formerly FM008, deleted in #105) a home on the file type where
`skills` is a real field (issue #132).

Two integration tests are the RED-first cases named in the task:
    - test_agent_tools_mcp_star_fails_lint (AG001, `tools: mcp__*`)
    - test_agent_skills_csv_string_fails_lint (AG003, `skills` as CSV string)
Both were written and confirmed failing (ImportError: no ag_series module)
before packages/skilllint/rules/ag_series.py existed.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from skilllint.frontmatter_core import AgentFrontmatter
from skilllint.plugin_validator import FrontmatterValidator
from skilllint.rules.ag_series import check_ag001, check_ag002, check_ag003

if TYPE_CHECKING:
    from pathlib import Path


def _write_agent(tmp_path: Path, name: str, body: str) -> Path:
    """Write an agent file under an ``agents/`` directory and return its path.

    ``FileType.detect_file_type`` classifies a path as AGENT only when
    ``"agents"`` is one of its path parts, so fixtures must live under an
    ``agents/`` directory for the integration tests to exercise the real
    validator wiring.
    """
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(exist_ok=True)
    agent_md = agents_dir / f"{name}.md"
    agent_md.write_text(body, encoding="utf-8")
    return agent_md


def _write_mcp_json(directory: Path, *server_names: str) -> None:
    """Write a .mcp.json declaring the given server names into *directory*."""
    mcp_config = {"mcpServers": {name: {} for name in server_names}}
    (directory / ".mcp.json").write_text(json.dumps(mcp_config), encoding="utf-8")


# ---------------------------------------------------------------------------
# RED-first integration cases named in the task
# ---------------------------------------------------------------------------


class TestAgentToolsWildcardIntegration:
    """AG001 via the real FrontmatterValidator wiring."""

    def test_agent_tools_mcp_star_fails_lint(self, tmp_path: Path) -> None:
        """`tools: mcp__*` on an agent file must fail lint (the concrete case from #109).

        Tests: FrontmatterValidator.validate() end-to-end for an agent file
        How: Write agents/broken.md with `tools: mcp__*`; validate it.
        Why: Per sub-agents.md, an entry that resolves to no tool means the
             subagent fails to launch. Before AG001 this passed lint silently.
        """
        agent_md = _write_agent(
            tmp_path, "broken", "---\nname: broken\ndescription: test agent\ntools: mcp__*\n---\n\nBody.\n"
        )

        result = FrontmatterValidator().validate(agent_md)

        assert result.passed is False, "tools: mcp__* must fail lint — every entry resolves to nothing"
        ag001 = [i for i in result.errors if i.code == "AG001"]
        assert ag001 != [], f"Expected an AG001 error, got errors={result.errors} warnings={result.warnings}"
        assert ag001[0].severity == "error"


class TestAgentSkillsShapeIntegration:
    """AG003 via the real FrontmatterValidator wiring."""

    def test_agent_skills_csv_string_fails_lint(self, tmp_path: Path) -> None:
        """A comma-separated `skills` string on an agent file must fail lint.

        Tests: FrontmatterValidator.validate() end-to-end for an agent file
        How: Write agents/bad-skills.md with `skills: a, b` (a scalar, not a list).
        Why: sub-agents.md documents `skills` as a YAML list of names to
             preload; nothing validated this shape until AG003 (issue #132).
        """
        agent_md = _write_agent(
            tmp_path,
            "bad-skills",
            "---\nname: bad-skills\ndescription: test agent\nskills: api-conventions, error-handling-patterns\n---\n\nBody.\n",
        )

        result = FrontmatterValidator().validate(agent_md)

        assert result.passed is False, "skills as a CSV string must fail lint — the field is YAML-list-only"
        ag003 = [i for i in result.errors if i.code == "AG003"]
        assert ag003 != [], f"Expected an AG003 error, got errors={result.errors} warnings={result.warnings}"

    def test_agent_skills_yaml_list_passes(self, tmp_path: Path) -> None:
        """The documented YAML-list shape produces no AG003 violation."""
        agent_md = _write_agent(
            tmp_path,
            "good-skills",
            "---\nname: good-skills\ndescription: test agent\nskills:\n  - api-conventions\n  - error-handling-patterns\n---\n\nBody.\n",
        )

        result = FrontmatterValidator().validate(agent_md)

        assert result.passed is True
        assert [i for i in (*result.errors, *result.warnings) if i.code == "AG003"] == []

    def test_agent_skills_bad_shape_does_not_also_emit_generic_fm005(self, tmp_path: Path) -> None:
        """AG003 replaces the generic Pydantic-derived issue, it does not duplicate it.

        Tests: the `_is_pydantic_shape_error_for_field` suppression in
            plugin_validator.py's `_validate_pydantic_model`
        Why: without the suppression, a bad `skills` shape on an agent file
             would report both a generic FM005 and the AG003-specific finding
             for the same defect.
        """
        agent_md = _write_agent(
            tmp_path, "double-report", "---\nname: double-report\ndescription: test agent\nskills: a, b\n---\n\nBody.\n"
        )

        result = FrontmatterValidator().validate(agent_md)

        skills_issues = [i for i in (*result.errors, *result.warnings) if i.field == "skills"]
        assert len(skills_issues) == 1, f"Expected exactly one 'skills' issue, got {skills_issues}"
        assert skills_issues[0].code == "AG003"


# ---------------------------------------------------------------------------
# AG001 unit tests
# ---------------------------------------------------------------------------


class TestCheckAg001:
    """Unit tests for check_ag001 (tools field resolves to nothing)."""

    def test_absent_tools_field_is_clean(self) -> None:
        """No `tools` field means inherit-everything — not a violation."""
        assert check_ag001({}) == []

    def test_ordinary_tools_are_clean(self) -> None:
        """Concrete tool names never trigger AG001."""
        assert check_ag001({"tools": ["Read", "Grep", "Bash"]}) == []

    def test_bare_star_is_fatal(self) -> None:
        """`tools: "*"` names no server and is the only entry — fatal."""
        issues = check_ag001({"tools": "*"})
        assert len(issues) == 1
        assert issues[0].code == "AG001"
        assert issues[0].severity == "error"

    def test_mcp_star_is_fatal(self) -> None:
        """`tools: mcp__*` — the concrete case from issue #109 — is fatal."""
        issues = check_ag001({"tools": ["mcp__*"]})
        assert len(issues) == 1
        assert issues[0].code == "AG001"

    def test_server_scoped_wildcard_is_not_fatal(self) -> None:
        """`mcp__Ref__*` is a documented, resolving grant — not flagged."""
        assert check_ag001({"tools": ["mcp__Ref__*"]}) == []

    def test_wildcard_alongside_a_real_tool_is_not_fatal(self) -> None:
        """A stray wildcard next to an ordinary tool is not provably fatal.

        skilllint has no live tool registry, so it cannot prove `Read` fails
        to resolve — only that every entry failing to resolve is provable.
        """
        assert check_ag001({"tools": ["Read", "mcp__*"]}) == []

    def test_empty_tools_list_is_not_sourced_as_fatal(self) -> None:
        """`tools: []` has no documented consequence — not flagged (see #109 analysis)."""
        assert check_ag001({"tools": []}) == []


# ---------------------------------------------------------------------------
# AG002 unit tests
# ---------------------------------------------------------------------------


class TestCheckAg002:
    """Unit tests for check_ag002 (MCP server casing on agent tools fields)."""

    def test_no_mcp_tools_is_clean(self, tmp_path: Path) -> None:
        assert check_ag002({"tools": ["Read", "Grep"]}, tmp_path / "agents" / "a.md") == []

    def test_exact_match_discovered_server_passes(self, tmp_path: Path) -> None:
        _write_mcp_json(tmp_path, "Ref")
        agent_md = tmp_path / "agents" / "a.md"
        agent_md.parent.mkdir(parents=True)
        issues = check_ag002({"tools": ["mcp__Ref__search"]}, agent_md)
        assert issues == []

    def test_case_mismatch_produces_error(self, tmp_path: Path) -> None:
        _write_mcp_json(tmp_path, "Ref")
        agent_md = tmp_path / "agents" / "a.md"
        agent_md.parent.mkdir(parents=True)
        issues = check_ag002({"tools": ["mcp__ref__search"]}, agent_md)
        assert len(issues) == 1
        assert issues[0].code == "AG002"
        assert issues[0].severity == "error"
        assert "Ref" in issues[0].message

    def test_unknown_server_produces_warning(self, tmp_path: Path) -> None:
        agent_md = tmp_path / "agents" / "a.md"
        agent_md.parent.mkdir(parents=True)
        issues = check_ag002({"tools": ["mcp__someUnknownServer__thing"]}, agent_md)
        assert len(issues) == 1
        assert issues[0].code == "AG002"
        assert issues[0].severity == "warning"

    def test_unscoped_wildcard_is_skipped_not_double_reported(self, tmp_path: Path) -> None:
        """`mcp__*` is AG001's territory; AG002 must not also warn about server '*'."""
        agent_md = tmp_path / "agents" / "a.md"
        agent_md.parent.mkdir(parents=True)
        assert check_ag002({"tools": ["mcp__*"]}, agent_md) == []

    def test_reads_disallowed_tools_field_too(self, tmp_path: Path) -> None:
        _write_mcp_json(tmp_path, "Ref")
        agent_md = tmp_path / "agents" / "a.md"
        agent_md.parent.mkdir(parents=True)
        issues = check_ag002({"disallowedTools": ["mcp__ref__search"]}, agent_md)
        assert len(issues) == 1
        assert issues[0].field == "disallowedTools"


# ---------------------------------------------------------------------------
# AG003 unit tests
# ---------------------------------------------------------------------------


class TestCheckAg003:
    """Unit tests for check_ag003 (skills field shape)."""

    def test_absent_skills_field_is_clean(self) -> None:
        assert check_ag003({}) == []

    def test_yaml_list_is_clean(self) -> None:
        assert check_ag003({"skills": ["api-conventions"]}) == []

    def test_csv_string_is_a_violation(self) -> None:
        issues = check_ag003({"skills": "api-conventions, error-handling-patterns"})
        assert len(issues) == 1
        assert issues[0].code == "AG003"
        assert issues[0].severity == "error"

    def test_scalar_int_is_a_violation(self) -> None:
        issues = check_ag003({"skills": 1})
        assert len(issues) == 1
        assert issues[0].code == "AG003"


# ---------------------------------------------------------------------------
# AgentFrontmatter model — issue #132
# ---------------------------------------------------------------------------


class TestAgentFrontmatterSkillsShape:
    """AgentFrontmatter.skills must match the documented YAML-list shape."""

    def test_skills_yaml_list_round_trips_as_a_list(self) -> None:
        """A list input stays a list — no CSV coercion (the bug #132 reports)."""
        model = AgentFrontmatter.model_validate({
            "name": "a",
            "description": "d",
            "skills": ["api-conventions", "error-handling-patterns"],
        })
        assert model.skills == ["api-conventions", "error-handling-patterns"]

    def test_skills_absent_is_none(self) -> None:
        model = AgentFrontmatter.model_validate({"name": "a", "description": "d"})
        assert model.skills is None
