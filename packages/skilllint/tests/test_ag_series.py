"""Tests for the AG-series agent frontmatter rules (AG001-AG003).

AG001/AG002 port the tools-field checks that used to live in AS007/AS008
before PR #108 scoped the AS family to SKILL.md only, leaving agent `tools`
frontmatter unvalidated (issue #109). AG003 reports authored `skills` values
that Claude Code's filesystem-agent loader silently discards (issue #132).

The model tests also lock the loader's normalized list view while preserving
the scalar-versus-sequence shape authored in YAML.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from skilllint.frontmatter_core import AgentFrontmatter, extract_frontmatter
from skilllint.plugin_validator import FrontmatterValidator, safe_load_yaml_with_colon_fix
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

    def test_agent_skills_csv_string_is_runtime_accepted(self, tmp_path: Path) -> None:
        """A comma-separated scalar is accepted by the filesystem-agent loader."""
        agent_md = _write_agent(
            tmp_path,
            "scalar-skills",
            "---\nname: scalar-skills\ndescription: test agent\nskills: api-conventions, error-handling-patterns\n---\n\nBody.\n",
        )

        result = FrontmatterValidator().validate(agent_md)

        assert result.passed is True
        assert [i for i in (*result.errors, *result.warnings) if i.code == "AG003"] == []

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

    @pytest.mark.parametrize("skills_yaml", ["1", "true", "{nested: value}", "[api-conventions, 1, false]"])
    def test_runtime_ignored_skills_value_warns_once_without_fm005(self, tmp_path: Path, skills_yaml: str) -> None:
        """Unsupported scalars and mixed lists produce one non-fatal AG003."""
        agent_md = _write_agent(
            tmp_path,
            "ignored-skills",
            f"---\nname: ignored-skills\ndescription: test agent\nskills: {skills_yaml}\n---\n\nBody.\n",
        )

        result = FrontmatterValidator().validate(agent_md)

        skills_issues = [i for i in (*result.errors, *result.warnings) if i.field == "skills"]
        assert len(skills_issues) == 1, f"Expected exactly one 'skills' issue, got {skills_issues}"
        assert skills_issues[0].code == "AG003"
        assert skills_issues[0].severity == "warning"
        assert all(issue.code != "FM005" for issue in (*result.errors, *result.warnings))
        assert result.passed is True


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

    def test_bare_star_is_not_provably_fatal(self) -> None:
        """`tools: "*"` (no `mcp__` prefix) is not sourced to fail -- do not flag it.

        Corrects the PR #147 review finding (thread PRRT_kwDORXxKvc6dgksB):
        sub-agents.md establishes failure only for the literal `mcp__*`. A
        bare `*` has no stated meaning in `tools` either way, so treating its
        absence of documented meaning as proof of invalidity would be the
        same unsourced-constraint mistake #108 deleted AS007 for.
        """
        assert check_ag001({"tools": "*"}) == []

    def test_non_mcp_wildcard_form_is_not_provably_fatal(self) -> None:
        """A non-MCP wildcard-bearing token is not sourced to fail either.

        Regression test for PR #147 review thread PRRT_kwDORXxKvc6dgksB: the
        prior implementation flagged ANY entry containing `*` that wasn't the
        one documented resolving pattern (`mcp__<server>__*`), which would
        incorrectly fire on a parenthesised specifier like `Bash(git:*)` --
        explicitly called out in issue #109's own investigation as neither
        established to grant nor restrict, and "not established" is not
        "established to fail".
        """
        assert check_ag001({"tools": ["Bash(git:*)"]}) == []

    def test_mcp_star_is_fatal(self) -> None:
        """`tools: mcp__*` — the concrete case from issue #109 — is fatal.

        Sourced from sub-agents.md, "Available tools": `mcp__*` is defined
        only for `disallowedTools` ("removes every MCP tool from any
        server"); in the `tools` allow-list it matches neither documented
        grant pattern (`mcp__<server>` / `mcp__<server>__*`, both of which
        require a real server name), so it names no server there.
        """
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

    def test_unconditionally_removed_tool_is_fatal(self) -> None:
        """A single entry naming an unconditionally-removed tool is fatal.

        Sourced from sub-agents.md, "Available tools" — the first filter
        strips these tools from every subagent regardless of what `tools`
        lists (#150). `AskUserQuestion` is one of the seven unconditional
        entries (the two conditional ones, `Agent` and `ExitPlanMode`, are
        deliberately excluded — see the module-level constant comment).
        """
        issues = check_ag001({"tools": ["AskUserQuestion"]})
        assert len(issues) == 1
        assert issues[0].code == "AG001"

    def test_all_seven_unconditionally_removed_tools_are_fatal(self) -> None:
        """Every documented unconditional-removal name is individually fatal."""
        for tool_name in (
            "AskUserQuestion",
            "EndConversation",
            "EnterPlanMode",
            "ScheduleWakeup",
            "TaskOutput",
            "WaitForMcpServers",
            "Workflow",
        ):
            issues = check_ag001({"tools": [tool_name]})
            assert len(issues) == 1, f"{tool_name} should be fatal alone"
            assert issues[0].code == "AG001"

    def test_agent_is_not_provably_fatal(self) -> None:
        """`Agent` is removed only at the subagent depth limit — not statically provable."""
        assert check_ag001({"tools": ["Agent"]}) == []

    def test_exit_plan_mode_is_not_provably_fatal(self) -> None:
        """`ExitPlanMode` is removed only when `permissionMode` isn't `plan` — not statically provable."""
        assert check_ag001({"tools": ["ExitPlanMode"]}) == []

    def test_mixed_wildcard_and_removed_tool_is_fatal(self) -> None:
        """An unscoped wildcard alongside an unconditionally-removed tool: both provably fail."""
        issues = check_ag001({"tools": ["mcp__*", "AskUserQuestion"]})
        assert len(issues) == 2
        assert {issue.code for issue in issues} == {"AG001"}

    def test_removed_tool_alongside_a_real_tool_is_not_fatal(self) -> None:
        """skilllint cannot prove a sibling ordinary tool name also fails to resolve."""
        assert check_ag001({"tools": ["Read", "AskUserQuestion"]}) == []


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

    def test_bare_server_grant_has_suffix_safe_correction(self, tmp_path: Path) -> None:
        """A bare grant must not gain a dangling separator in its correction."""
        _write_mcp_json(tmp_path, "Ref")
        agent_md = tmp_path / "agents" / "a.md"
        agent_md.parent.mkdir(parents=True)

        issues = check_ag002({"tools": ["mcp__ref"]}, agent_md)

        assert len(issues) == 1
        assert "Did you mean 'mcp__Ref'?" in issues[0].message
        assert issues[0].suggestion == "Replace 'mcp__ref' with 'mcp__Ref'."

    def test_qualified_reference_retains_suffix_in_correction(self, tmp_path: Path) -> None:
        _write_mcp_json(tmp_path, "Ref")
        agent_md = tmp_path / "agents" / "a.md"
        agent_md.parent.mkdir(parents=True)

        issues = check_ag002({"tools": ["mcp__ref__search"]}, agent_md)

        assert "Did you mean 'mcp__Ref__search'?" in issues[0].message
        assert issues[0].suggestion == "Replace 'mcp__ref__' with 'mcp__Ref__'."

    def test_unknown_server_produces_warning(self, tmp_path: Path) -> None:
        agent_md = tmp_path / "agents" / "a.md"
        agent_md.parent.mkdir(parents=True)
        issues = check_ag002({"tools": ["mcp__someUnknownServer__thing"]}, agent_md)
        assert len(issues) == 1
        assert issues[0].code == "AG002"
        assert issues[0].severity == "warning"

    def test_unresolved_external_plugin_namespace_is_skipped(self, tmp_path: Path) -> None:
        agent_md = tmp_path / "agents" / "a.md"
        agent_md.parent.mkdir(parents=True)
        assert check_ag002({"tools": ["mcp__plugin_external_Ref__search"]}, agent_md) == []

    def test_configured_plugin_prefixed_server_still_checks_case(self, tmp_path: Path) -> None:
        """A real configured server may itself start with ``plugin_``."""
        _write_mcp_json(tmp_path, "plugin_external_Ref")
        agent_md = tmp_path / "agents" / "a.md"
        agent_md.parent.mkdir(parents=True)

        issues = check_ag002({"tools": ["mcp__plugin_external_ref__search"]}, agent_md)

        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "mcp__plugin_external_Ref__search" in issues[0].message

    def test_unscoped_wildcard_is_skipped_not_double_reported(self, tmp_path: Path) -> None:
        """`mcp__*` is AG001's territory; AG002 must not also warn about server '*'."""
        agent_md = tmp_path / "agents" / "a.md"
        agent_md.parent.mkdir(parents=True)
        assert check_ag002({"tools": ["mcp__*"]}, agent_md) == []

    def test_plugin_recognized_but_server_not_declared_is_unknown(self, tmp_path: Path) -> None:
        """A same-named server from a different plugin/project must not false-accept.

        Regression test for PR #147 review thread PRRT_kwDORXxKvc6dgksF: plugin
        "myplugin" is recognized (it has a plugin.json) but does not itself
        declare "ServerX" in its own mcpServers. A *different*, unrelated
        server sharing that name at project level must not let
        `mcp__plugin_myplugin_ServerX__...` resolve as exact -- resolution
        must be scoped to the matched plugin's own server set.
        """
        plugin_dir = tmp_path / "myplugin"
        (plugin_dir / ".claude-plugin").mkdir(parents=True)
        (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "myplugin", "mcpServers": {"OtherServer": {}}}), encoding="utf-8"
        )
        _write_mcp_json(tmp_path, "ServerX")
        agent_md = plugin_dir / "agents" / "a.md"
        agent_md.parent.mkdir(parents=True)
        agent_md.write_text("---\nname: a\ndescription: d\n---\n\nBody.\n", encoding="utf-8")

        issues = check_ag002({"tools": ["mcp__plugin_myplugin_ServerX__search"]}, agent_md)

        assert len(issues) == 1, f"Expected the unmatched plugin-local server to warn, got: {issues}"
        assert issues[0].code == "AG002"
        assert issues[0].severity == "warning"

    def test_plugin_agent_own_inline_mcp_servers_excluded_from_discovery(self, tmp_path: Path) -> None:
        """A plugin agent's own `mcpServers` is ignored at load -- AG002 must not trust it.

        Regression test for PR #147 review thread PRRT_kwDORXxKvc6dgksH: per
        pa_series.py's documented policy, Claude Code ignores inline
        `mcpServers` in a plugin-packaged agent's own frontmatter. An agent
        whose only declaration of a server is that ignored field must still
        be flagged as referencing an unconfigured server.
        """
        plugin_dir = tmp_path / "my-plugin"
        (plugin_dir / ".claude-plugin").mkdir(parents=True)
        (plugin_dir / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "my-plugin"}), encoding="utf-8")
        agents_dir = plugin_dir / "agents"
        agents_dir.mkdir(parents=True)
        agent_md = agents_dir / "a.md"
        agent_md.write_text(
            "---\nname: a\ndescription: d\nmcpServers:\n  Ref:\n    command: x\ntools: mcp__Ref__read\n---\n\nBody.\n",
            encoding="utf-8",
        )

        issues = check_ag002({"tools": ["mcp__Ref__read"]}, agent_md)

        assert len(issues) == 1, f"Expected the ignored inline mcpServers to not configure 'Ref', got: {issues}"
        assert issues[0].code == "AG002"
        assert issues[0].severity == "warning"

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
    """Unit tests for values the runtime accepts or silently ignores."""

    @pytest.mark.parametrize(
        "frontmatter",
        [
            {},
            {"skills": None},
            {"skills": ""},
            {"skills": "api-conventions, error-handling-patterns"},
            {"skills": []},
            {"skills": ["api-conventions", "error-handling-patterns"]},
        ],
    )
    def test_runtime_accepted_values_are_clean(self, frontmatter: dict) -> None:
        assert check_ag003(frontmatter) == []

    @pytest.mark.parametrize("value", [1, 1.5, True, False, {"name": "api"}, ["api", 1, False]])
    def test_runtime_ignored_values_produce_one_warning(self, value: object) -> None:
        issues = check_ag003({"skills": value})

        assert len(issues) == 1
        assert issues[0].code == "AG003"
        assert issues[0].severity == "warning"
        if isinstance(value, list):
            assert "string members continue through runtime normalization" in issues[0].message
        else:
            assert "preloads no skills" in issues[0].message


# ---------------------------------------------------------------------------
# AgentFrontmatter model — issue #132
# ---------------------------------------------------------------------------


class TestAgentFrontmatterSkillsShape:
    """AgentFrontmatter preserves raw shape and exposes the loader's list."""

    @pytest.mark.parametrize(
        "value",
        [
            "api-conventions, error-handling-patterns",
            ["api-conventions", "error-handling-patterns"],
            ["api-conventions", 1, False],
            1,
            True,
            {"nested": "value"},
            None,
        ],
    )
    def test_skills_authored_shape_round_trips(self, value: object) -> None:
        model = AgentFrontmatter.model_validate({"name": "a", "description": "d", "skills": value})
        assert model.skills == value
        assert model.model_dump()["skills"] == value

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("", []),
            (" , ", []),
            ("api-conventions, error-handling-patterns", ["api-conventions", "error-handling-patterns"]),
            (["one two", 7, "three", False], ["one", "two", "three"]),
            (["one two", "three,four"], ["one", "two", "three", "four"]),
            ("one(foo, bar) two", ["one(foo, bar)", "two"]),
            ("one\ttwo three\nfour", ["one\ttwo", "three\nfour"]),
            (["same", "same"], ["same", "same"]),
            (["one", "*", "two"], ["*"]),
            ("one,*", ["*"]),
            ("\u0085one\u0085", ["\u0085one\u0085"]),
            ("\ufeffone\ufeff", ["one"]),
            ("one,,,  two", ["one", "two"]),
            ("one(unclosed, value", ["one(unclosed, value"]),
            ("one((nested, value) tail", ["one((nested, value)", "tail"]),
            ("foo*", ["foo*"]),
            (42, []),
            (True, []),
            ({"name": "one"}, []),
            (None, []),
        ],
    )
    def test_normalized_skills_matches_filesystem_loader(self, value: object, expected: list[str]) -> None:
        model = AgentFrontmatter.model_validate({"name": "a", "description": "d", "skills": value})
        assert model.normalized_skills == expected

    def test_skills_absent_is_none(self) -> None:
        model = AgentFrontmatter.model_validate({"name": "a", "description": "d"})
        assert model.skills is None
        assert model.normalized_skills == []

    @pytest.mark.parametrize(
        ("skills_yaml", "expected_raw"),
        [
            ("skills: api-conventions, error-handling-patterns", "api-conventions, error-handling-patterns"),
            (
                "skills:\n  - api-conventions\n  - error-handling-patterns",
                ["api-conventions", "error-handling-patterns"],
            ),
            ("skills:\n  - api-conventions\n  - 1\n  - false", ["api-conventions", 1, False]),
            ("skills: null", None),
            ("skills: 7", 7),
            ("skills: {nested: value}", {"nested": "value"}),
            ("skills: []", []),
        ],
    )
    def test_fix_preserves_skills_shape_and_is_idempotent(
        self, tmp_path: Path, skills_yaml: str, expected_raw: object
    ) -> None:
        """An unrelated tools fix must not rewrite or re-fix skills."""
        agent_md = _write_agent(
            tmp_path,
            "fix-shape",
            (
                "---\nname: fix-shape\ndescription: |\n  test\n  agent\n"
                f"{skills_yaml}\n"
                "tools: Read, Grep\n---\n\nBody.\n"
            ),
        )
        validator = FrontmatterValidator()

        first_fixes = validator.fix(agent_md)
        first_content = agent_md.read_text(encoding="utf-8")
        second_fixes = validator.fix(agent_md)

        assert first_fixes != []
        frontmatter_text, _start, _end = extract_frontmatter(first_content)
        assert frontmatter_text is not None
        parsed, error, _colon_fields, _used = safe_load_yaml_with_colon_fix(frontmatter_text)
        assert error is None
        assert parsed is not None
        assert parsed["skills"] == expected_raw
        assert second_fixes == []
        assert agent_md.read_text(encoding="utf-8") == first_content
