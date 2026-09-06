"""
Tests for AS-series agentskills.io rule validation (AS001, AS006, AS008, AS009).

Wave 0 TDD scaffold — all tests fail RED (ImportError) until plan 02-02
creates the skilllint.rules.as_series module.

Test IDs map to VALIDATION.md task ID 2-05-01 for traceability.
"""

from __future__ import annotations

import pathlib
import textwrap

# This import fails RED until plan 02-02 creates the module.
from skilllint.rules.as_series import check_skill_md

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _violations_with_code(violations: list[dict], code: str) -> list[dict]:
    """Filter violations list by rule code."""
    return [v for v in violations if v.get("code") == code]


# ---------------------------------------------------------------------------
# AS001: SKILL.md declares a name field (syntax belongs to FM010)
# ---------------------------------------------------------------------------


def test_as001_name_format_valid(tmp_path: pathlib.Path):
    """name 'my-skill' passes AS001 (no violation produced)."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: A valid skill description.
            ---

            Body content.
        """)
    )
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS001") == [], (
        f"Expected no AS001 violations for valid name, got: {violations}"
    )


def test_as001_ignores_name_syntax(tmp_path: pathlib.Path):
    """A malformed name produces no AS001 — FM010 owns name syntax."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: My_Skill!
            description: A skill with an invalid name.
            ---

            Body content.
        """)
    )
    assert "AS001" not in {v.get("code") for v in check_skill_md(skill_md)}


def test_as001_missing_name_is_error(tmp_path: pathlib.Path):
    """Absent name field produces AS001 with severity 'error'.

    The AgentSkills spec (agentskills.io/specification) marks name as required.
    Claude Code's skills.md treats it as optional, so SkillFrontmatter declares
    it ``str | None`` and FM001 stays silent — AS001 is the only signal.
    """
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            description: A skill with no name field.
            ---

            Body content.
        """)
    )
    as001 = _violations_with_code(check_skill_md(skill_md), "AS001")
    assert as001 != [], "Expected AS001 when the name field is absent"
    assert as001[0]["severity"] == "error", f"AS001 missing-name must be an error, got: {as001[0]['severity']}"


def test_as001_block_scalar_body_collision_is_not_a_name_field(tmp_path: pathlib.Path):
    """A ``name: ...``-shaped line inside a block-scalar description is not the name field.

    Regression for the naive colon-splitter that used to back AS001: it read
    frontmatter line-by-line without YAML indentation awareness, so a line
    inside a multi-line ``description: |`` block that happened to read
    ``name: something`` was misread as a top-level ``name`` key — masking a
    SKILL.md that has no real ``name`` field at all.
    """
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            description: |
              This skill does many things.
              name: something
              It also documents its own fields inline.
            ---

            Body content.
        """)
    )
    as001 = _violations_with_code(check_skill_md(skill_md), "AS001")
    assert as001 != [], "Expected AS001: no real top-level name field, only a block-scalar body collision"
    assert as001[0]["severity"] == "error", f"AS001 missing-name must be an error, got: {as001[0]['severity']}"


def test_parse_skill_md_body_lines_excludes_closing_delimiter(tmp_path: pathlib.Path):
    """body_lines for a well-formed file must not include the closing '---'.

    Regression: _parse_skill_md delegates to plugin_validator.parse_skill_md,
    which used to slice body_lines as ``lines[end_line:]`` — off by one, so
    the closing frontmatter delimiter leaked in as the first body line.
    """
    from skilllint.rules.as_series import _parse_skill_md

    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: A valid skill description.
            ---
            Body content.
        """)
    )
    _frontmatter, body_lines = _parse_skill_md(skill_md)
    assert body_lines == ["Body content."], f"Expected the delimiter excluded from body_lines, got: {body_lines}"


def test_parse_skill_md_unclosed_frontmatter_returns_empty_body(tmp_path: pathlib.Path):
    """Unclosed frontmatter (opening '---' with no closing '---') yields no body.

    Regression: after this PR moved off the naive colon splitter,
    _parse_skill_md returned the entire raw file as body_lines for this case
    instead of the pre-existing ``[]`` behavior.
    """
    from skilllint.rules.as_series import _parse_skill_md

    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("---\nname: my-skill\ndescription: never closed\n")
    frontmatter, body_lines = _parse_skill_md(skill_md)
    assert frontmatter == {}
    assert body_lines == [], f"Expected empty body_lines for unclosed frontmatter, got: {body_lines}"


# ---------------------------------------------------------------------------
# AS002: name matches parent directory name
# ---------------------------------------------------------------------------


def test_as002_directory_match_is_retired(tmp_path: pathlib.Path):
    """A name/directory mismatch produces no AS002 — FM010 owns the match."""
    skill_dir = tmp_path / "bar"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: foo
            description: Name does not match directory name bar.
            ---

            Body content.
        """)
    )
    assert "AS002" not in {v.get("code") for v in check_skill_md(skill_md)}


# ---------------------------------------------------------------------------
# AS006: eval_queries.json absence info notice
# ---------------------------------------------------------------------------


def test_as006_no_eval_queries_info(tmp_path: pathlib.Path):
    """SKILL.md directory without eval_queries.json produces AS006 info."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: A skill without eval queries.
            ---

            Body content.
        """)
    )
    # No eval_queries.json in skill_dir
    violations = check_skill_md(skill_md)
    as006 = _violations_with_code(violations, "AS006")
    assert as006 != [], "Expected AS006 info when eval_queries.json is absent"
    assert as006[0].get("severity") in ("info", "information"), (
        f"Expected AS006 to be info severity, got: {as006[0].get('severity')}"
    )


def test_as006_evals_json_in_evals_dir_satisfies_check(tmp_path: pathlib.Path):
    """A skill with only evals/evals.json (no eval_queries.json) triggers no AS006.

    agentskills.io's evaluating-skills guide documents ``evals/evals.json``
    as the standard eval layout. The old file-only glob over
    ``parent.iterdir()`` never sees content inside a subdirectory, so this
    documented layout was a blind spot.
    """
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: A skill with evals/evals.json instead of eval_queries.json.
            ---

            Body content.
        """)
    )
    evals_dir = skill_dir / "evals"
    evals_dir.mkdir()
    (evals_dir / "evals.json").write_text('{"skill_name": "my-skill", "evals": []}')

    violations = check_skill_md(skill_md)
    as006 = _violations_with_code(violations, "AS006")
    assert as006 == [], f"Expected no AS006 when evals/evals.json is present, got: {as006}"


# ---------------------------------------------------------------------------
# AS008: MCP server name references in the allowed-tools field
# ---------------------------------------------------------------------------


def _make_skill_with_tools(tmp_path: pathlib.Path, tools_block: str) -> pathlib.Path:
    """Write a minimal valid SKILL.md with the given tool-field block and return its path.

    The tools_block is inserted verbatim between the description line and the
    closing '---' delimiter. It must not be indented (textwrap.dedent would
    strip indentation from the surrounding template and corrupt list items).
    """
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir(exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    content = (
        "---\n"
        "name: my-skill\n"
        "description: A skill for tools field testing.\n" + tools_block + "\n---\n\nBody content.\n"
    )
    skill_md.write_text(content)
    return skill_md


def test_as008_reads_the_spec_field_and_both_separators(tmp_path: pathlib.Path):
    """AS008 must see `allowed-tools`, in list form and either inline separator.

    `allowed-tools` is the field the AgentSkills specification defines for
    skills (agentskills.io/specification.md, fetched 2026-08-22); AS008 read
    `tools:` and was blind to it. The spec describes the inline form as
    space-separated but marks the field Experimental, and nothing establishes
    that a comma is an error — so the parser accepts both rather than picking
    one and silently missing entries written the other way.
    """
    _write_mcp_json(tmp_path, "Ref")
    forms = (
        "allowed-tools:\n  - mcp__ref__read_url\n  - Bash",  # YAML list
        "allowed-tools: mcp__ref__read_url Bash",  # space-separated (spec form)
        "allowed-tools: mcp__ref__read_url, Bash",  # comma-separated
    )
    for i, block in enumerate(forms):
        case_dir = tmp_path / f"form{i}"
        case_dir.mkdir()
        _write_mcp_json(case_dir, "Ref")
        as008 = _violations_with_code(check_skill_md(_make_skill_with_tools(case_dir, block)), "AS008")
        assert as008 != [], f"AS008 must catch the wrong-case server in form {block!r}"


def test_as008_ignores_the_agent_tools_field_on_a_skill(tmp_path: pathlib.Path):
    """`tools:` is agent frontmatter; the AgentSkills spec does not define it for skills."""
    _write_mcp_json(tmp_path, "Ref")
    skill_md = _make_skill_with_tools(tmp_path, "tools:\n  - mcp__ref__read_url")
    assert _violations_with_code(check_skill_md(skill_md), "AS008") == [], (
        "AS008 must not read `tools:` on a SKILL.md — that is not the spec's field"
    )


def _write_mcp_json(directory: pathlib.Path, *server_names: str) -> None:
    """Write a .mcp.json containing the given server names into *directory*."""
    import json

    mcp_config = {"mcpServers": {name: {} for name in server_names}}
    (directory / ".mcp.json").write_text(json.dumps(mcp_config))


def test_as008_exact_match_discovered_server_passes(tmp_path: pathlib.Path):
    """Exact server name match against .mcp.json discovery produces no AS008 violation."""
    _write_mcp_json(tmp_path, "Ref")
    skill_md = _make_skill_with_tools(tmp_path, "allowed-tools:\n  - mcp__Ref__ref_search_documentation")
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS008") == [], (
        "AS008 must not fire when server 'Ref' exactly matches .mcp.json discovery"
    )


def test_as008_case_mismatch_with_discovered_server_produces_error(tmp_path: pathlib.Path):
    """Wrong-case server name against a discovered server produces AS008 error."""
    # .mcp.json declares 'Ref'; skill uses 'ref' (lowercase) — case mismatch
    _write_mcp_json(tmp_path, "Ref")
    skill_md = _make_skill_with_tools(tmp_path, "allowed-tools:\n  - mcp__ref__ref_search_documentation")
    violations = check_skill_md(skill_md)
    as008 = _violations_with_code(violations, "AS008")
    assert as008 != [], "Expected AS008 error for case mismatch 'mcp__ref__' vs discovered 'Ref'"
    assert as008[0]["severity"] == "error"
    assert "Ref" in as008[0]["message"], "AS008 message must show the correct canonical server name"
    assert "fix" in as008[0]


def test_as008_bare_server_grant_has_suffix_safe_correction(tmp_path: pathlib.Path) -> None:
    """A bare server grant must not acquire a dangling ``__`` in its fix."""
    _write_mcp_json(tmp_path, "Ref")
    skill_md = _make_skill_with_tools(tmp_path, "allowed-tools: mcp__ref")

    as008 = _violations_with_code(check_skill_md(skill_md), "AS008")

    assert len(as008) == 1
    assert "Did you mean 'mcp__Ref'?" in as008[0]["message"]
    assert as008[0]["fix"] == "Replace 'mcp__ref' with 'mcp__Ref'."


def test_as008_unscoped_wildcard_is_reported_as_unknown_server(tmp_path: pathlib.Path) -> None:
    """``mcp__*`` on SKILL.md has no AG001 equivalent -- AS008 must still flag it.

    Regression test for PR #147 review thread PRRT_kwDORXxKvc6dgksD: the
    ``analyze_mcp_tool_reference`` extraction shared by AS008 and AG002 briefly
    silenced this case for both callers. AG002 is right to skip it (AG001 owns
    "does this wildcard resolve" for agent files), but SKILL.md's `allowed-tools`
    has no such sibling rule, so AS008 must keep reporting it exactly as it did
    before the shared extraction (see ``git show 728d7ae:.../as_series.py``).
    """
    skill_md = _make_skill_with_tools(tmp_path, "allowed-tools: mcp__*")
    as008 = _violations_with_code(check_skill_md(skill_md), "AS008")
    assert as008 != [], "AS008 must report 'mcp__*' as an unknown server on SKILL.md"
    assert as008[0]["severity"] == "warning"
    assert "*" in as008[0]["message"]


def test_as008_scoped_wildcard_still_checks_server_casing(tmp_path: pathlib.Path) -> None:
    """Only the server segment is skipped; a wildcard suffix remains valid."""
    _write_mcp_json(tmp_path, "Ref")
    skill_md = _make_skill_with_tools(tmp_path, "allowed-tools: mcp__ref__*")

    as008 = _violations_with_code(check_skill_md(skill_md), "AS008")

    assert len(as008) == 1
    assert "Did you mean 'mcp__Ref__*'?" in as008[0]["message"]
    assert as008[0]["fix"] == "Replace 'mcp__ref__' with 'mcp__Ref__'."


def test_as008_unknown_server_not_in_any_config_produces_warning(tmp_path: pathlib.Path):
    """MCP tool referencing a server absent from all config files produces AS008 warning."""
    # No .mcp.json written — server is entirely unknown
    skill_md = _make_skill_with_tools(tmp_path, "allowed-tools:\n  - mcp__someUnknownServer__some_tool")
    violations = check_skill_md(skill_md)
    as008 = _violations_with_code(violations, "AS008")
    assert as008 != [], "Expected AS008 warning for server not found in any config"
    assert as008[0]["severity"] == "warning"
    assert "someUnknownServer" in as008[0]["message"]


# ---------------------------------------------------------------------------
# AsSeriesValidator integration — agent file wiring
# ---------------------------------------------------------------------------
# These tests verify the AS family's file-type boundary and AS008 wiring
# via the default validate_single_path code path (not --platform).
# AS002 must be suppressed for agent files because agents live directly in
# agents/ — the parent directory name is always "agents", not the agent name.
# ---------------------------------------------------------------------------


def _make_agent_md(tmp_path: pathlib.Path, tools_yaml: str) -> pathlib.Path:
    """Create an agents/bad-agent.md fixture under tmp_path.

    Args:
        tmp_path: Pytest temporary directory.
        tools_yaml: Raw YAML line(s) for the tools field (e.g. "tools: mcp__Ref__*").

    Returns:
        Path to the created agent .md file.
    """
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(exist_ok=True)
    agent_md = agents_dir / "bad-agent.md"
    agent_md.write_text(
        textwrap.dedent(f"""\
            ---
            name: bad-agent
            description: Test agent for AsSeriesValidator integration.
            {tools_yaml}
            ---

            Agent body.
        """)
    )
    return agent_md


def test_as_family_does_not_run_on_agent_files(tmp_path: pathlib.Path):
    """No AS-series rule may fire on an agent file.

    The AgentSkills specification is a cross-harness baseline that defines
    SKILL.md and does not describe agent files at all. An AS rule evaluating
    agent frontmatter is a category error regardless of what it checks, so the
    boundary lives in the family wiring rather than in each rule's own guard.

    This asserts the routing in _get_validators_for_path, not a rule in
    isolation — calling AsSeriesValidator directly would bypass the boundary
    and pass even when the wiring is wrong.
    """
    from skilllint.plugin_validator import _get_validators_for_path

    agent_md = _make_agent_md(tmp_path, "allowed-tools: mcp__*, Read, Bash")
    names = [type(v).__name__ for v in _get_validators_for_path(agent_md)]
    assert "AsSeriesValidator" not in names, f"AS family must not be wired to agent files, got: {names}"


def test_as_family_still_runs_on_skill_md(tmp_path: pathlib.Path):
    """The boundary must not cost SKILL.md its AS coverage."""
    from skilllint.plugin_validator import _get_validators_for_path

    skill_md = _make_skill_with_tools(tmp_path, "allowed-tools:\n  - Read")
    names = [type(v).__name__ for v in _get_validators_for_path(skill_md)]
    assert "AsSeriesValidator" in names, f"AS family must still run on SKILL.md, got: {names}"


def test_name_check_suppressed_for_agent_files_via_validator(tmp_path: pathlib.Path):
    """AsSeriesValidator does not emit AS002 for agent files.

    AS002 compares the name field against the parent directory name. For agents
    the parent is always 'agents/', which never matches the agent name. The
    validator must suppress AS002 for non-SKILL.md files to avoid false positives.
    """
    from skilllint.plugin_validator import AsSeriesValidator

    agent_md = _make_agent_md(tmp_path, "allowed-tools: Read")
    result = AsSeriesValidator().validate(agent_md)
    codes = [i.field for i in result.errors + result.warnings + result.info]
    assert "AS002" not in codes, f"AS002 must not fire for agent files, got: {codes}"


def test_as002_directory_match_is_retired_for_skill_md(tmp_path: pathlib.Path):
    """AsSeriesValidator emits no AS002 for a SKILL.md/directory mismatch.

    FM010 owns the name/directory match; it reports the mismatch as a warning
    from ``check_fm010``. AS002 was retired to leave that claim one owner.
    """
    from skilllint.plugin_validator import AsSeriesValidator

    skill_dir = tmp_path / "wrong-dir"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: correct-name
            description: A skill whose directory name does not match.
            ---

            Body content.
        """)
    )
    result = AsSeriesValidator().validate(skill_md)
    codes = [i.field for i in result.errors + result.warnings + result.info]
    assert "AS002" not in codes


def test_as008_hyphen_vs_underscore_unrecognized_server_produces_warning(tmp_path: pathlib.Path):
    """mcp__sequential-thinking__ is not a case-fold match for 'sequential_thinking' — produces AS008 warning."""
    # 'sequential-thinking' (hyphen) vs 'sequential_thinking' (underscore) differ by more than
    # case — case-folding won't unify them, so it falls through to "unknown server → warning".
    _write_mcp_json(tmp_path, "sequential_thinking")
    skill_md = _make_skill_with_tools(tmp_path, "allowed-tools:\n  - mcp__sequential-thinking__sequentialthinking")
    violations = check_skill_md(skill_md)
    as008 = _violations_with_code(violations, "AS008")
    assert as008 != [], "Expected AS008 warning for 'mcp__sequential-thinking__' (not a case-fold match)"
    assert as008[0]["severity"] == "warning"
    assert "sequential-thinking" in as008[0]["message"]


def test_as008_correct_server_with_discovered_context_passes(tmp_path: pathlib.Path):
    """Correct server name when that server is in .mcp.json produces no AS008 violation."""
    _write_mcp_json(tmp_path, "sequential_thinking")
    skill_md = _make_skill_with_tools(tmp_path, "allowed-tools:\n  - mcp__sequential_thinking__sequentialthinking")
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS008") == [], (
        "AS008 must not fire when server name exactly matches discovered 'sequential_thinking'"
    )


def test_as008_mixed_exact_and_case_mismatch_produces_one_error(tmp_path: pathlib.Path):
    """One case-mismatched and one correct tool produces exactly one AS008 violation."""
    _write_mcp_json(tmp_path, "Ref")
    skill_md = _make_skill_with_tools(
        tmp_path, "allowed-tools:\n  - mcp__ref__ref_read_url\n  - mcp__Ref__ref_search_documentation\n  - Bash"
    )
    violations = check_skill_md(skill_md)
    as008 = _violations_with_code(violations, "AS008")
    assert len(as008) == 1, f"Expected exactly 1 AS008 violation (the case mismatch), got: {len(as008)}"
    assert "mcp__ref__ref_read_url" in as008[0]["message"]


def test_as008_non_mcp_tools_are_ignored(tmp_path: pathlib.Path):
    """Non-MCP tool names (Bash, Read, Write) never trigger AS008."""
    skill_md = _make_skill_with_tools(tmp_path, "allowed-tools:\n  - Bash\n  - Read\n  - Write\n  - Edit")
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS008") == [], "AS008 must not fire for non-MCP tool names"


# ---------------------------------------------------------------------------
# AS009: nested skill directory depth
# ---------------------------------------------------------------------------


def _make_skill_at_depth(root: pathlib.Path, rel_path: str) -> pathlib.Path:
    """Create a minimal SKILL.md at root/rel_path."""
    skill_md = root / rel_path
    skill_md.parent.mkdir(parents=True, exist_ok=True)
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: A test skill.
            ---

            Body.
        """)
    )
    return skill_md


def test_as009_skill_at_correct_depth_passes(tmp_path: pathlib.Path):
    """skills/my-skill/SKILL.md at depth 1 produces no AS009 violation."""
    skill_md = _make_skill_at_depth(tmp_path, "skills/my-skill/SKILL.md")
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS009") == [], (
        f"Expected no AS009 violations for depth-1 skill, got: {violations}"
    )


def test_as009_skill_nested_two_levels_bare_context_warns(tmp_path: pathlib.Path):
    """skills/category/my-skill/SKILL.md at depth 2, no plugin.json, produces AS009 warning."""
    skill_md = _make_skill_at_depth(tmp_path, "skills/category/my-skill/SKILL.md")
    violations = check_skill_md(skill_md)
    as009 = _violations_with_code(violations, "AS009")
    assert as009 != [], "Expected AS009 warning for depth-2 skill in bare context"
    assert as009[0]["severity"] == "warning"
    assert "will not activate in Claude Code" in as009[0]["message"]


def test_as009_skill_nested_two_levels_plugin_context_warns(tmp_path: pathlib.Path):
    """skills/category/my-skill/SKILL.md at depth 2 inside a plugin produces AS009 plugin-variant warning."""
    plugin_json = tmp_path / ".claude-plugin" / "plugin.json"
    plugin_json.parent.mkdir(parents=True, exist_ok=True)
    plugin_json.write_text('{"name": "test-plugin"}')
    skill_md = _make_skill_at_depth(tmp_path, "skills/category/my-skill/SKILL.md")
    violations = check_skill_md(skill_md)
    as009 = _violations_with_code(violations, "AS009")
    assert as009 != [], "Expected AS009 warning for depth-2 skill in plugin context"
    assert as009[0]["severity"] == "warning"
    assert "plugin.json" in as009[0]["message"]


def test_as009_skill_not_under_skills_dir_is_ignored(tmp_path: pathlib.Path):
    """A SKILL.md not under a skills/ directory produces no AS009 violation."""
    skill_md = _make_skill_at_depth(tmp_path, "other/my-skill/SKILL.md")
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS009") == [], "AS009 must not fire when no skills/ ancestor is present"


def test_as009_commands_subdir_not_affected(tmp_path: pathlib.Path):
    """A deeply nested file under commands/ does not trigger AS009 (not a SKILL.md scenario)."""
    # AS009 only applies to SKILL.md files. Commands can be nested.
    # We simulate by placing a SKILL.md deeply under commands/ — no skills/ ancestor → no AS009.
    skill_md = _make_skill_at_depth(tmp_path, "commands/rwr/sub/SKILL.md")
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS009") == [], (
        "AS009 must not fire for files under commands/ (no skills/ ancestor)"
    )


def test_as009_depth_three_bare_context_warns(tmp_path: pathlib.Path) -> None:
    """skills/a/b/my-skill/SKILL.md at depth 3, no plugin.json, produces AS009 warning.

    Tests: AS009 fires for any depth > 1, not only exactly depth 2.
    How: Create a real three-level structure under skills/ with no plugin.json
         ancestor, then assert the bare-context variant of AS009 fires.
    Why: _count_levels_under_skills returns values > 2 for deeper nesting; the
         rule must fire for all such cases, not just the minimum two-level case.
    """
    skill_md = _make_skill_at_depth(tmp_path, "skills/a/b/my-skill/SKILL.md")
    violations = check_skill_md(skill_md)
    as009 = _violations_with_code(violations, "AS009")
    assert as009 != [], "Expected AS009 warning for depth-3 skill in bare context"
    assert as009[0]["severity"] == "warning"
    assert "will not activate in Claude Code" in as009[0]["message"]


def test_as009_plugin_context_provides_fix(tmp_path: pathlib.Path) -> None:
    """AS009 plugin-context variant includes a fix field pointing to plugin.json.

    Tests: AS009 violation dict structure for plugin context.
    How: Create a realistic plugin layout with plugin.json above skills/ and a
         nested SKILL.md, then assert the violation carries the expected fix text.
    Why: The fix field is machine-consumable; callers rely on it to suggest the
         correct remediation action for plugin-scoped skills.
    """
    plugin_json = tmp_path / ".claude-plugin" / "plugin.json"
    plugin_json.parent.mkdir(parents=True, exist_ok=True)
    plugin_json.write_text('{"name": "test-plugin"}')
    skill_md = _make_skill_at_depth(tmp_path, "skills/category/my-skill/SKILL.md")
    violations = check_skill_md(skill_md)
    as009 = _violations_with_code(violations, "AS009")
    assert as009 != [], "Expected AS009 violation in plugin context"
    assert "fix" in as009[0], "AS009 plugin-context violation must carry a fix field"
    assert "plugin.json" in as009[0]["fix"]


def test_as009_plugin_json_in_grandparent_is_found(tmp_path: pathlib.Path) -> None:
    """_find_plugin_json_in_ancestry finds plugin.json multiple hops above skills/.

    Tests: AS009 emits plugin-context variant when plugin.json is above the
           skills/ directory rather than a direct sibling.
    How: Create tmp_path/my-plugin/.claude-plugin/plugin.json, then place a
         nested SKILL.md at tmp_path/my-plugin/skills/category/nested/SKILL.md.
         The ancestry walk must traverse my-plugin/ to find .claude-plugin/.
    Why: Real plugin layouts nest skills/ inside a named plugin directory.
         The ancestry walker must traverse multiple hops, not just check the
         immediate parent of skills/.
    """
    plugin_root = tmp_path / "my-plugin"
    plugin_json = plugin_root / ".claude-plugin" / "plugin.json"
    plugin_json.parent.mkdir(parents=True, exist_ok=True)
    plugin_json.write_text('{"name": "my-plugin"}')
    skill_md = _make_skill_at_depth(plugin_root, "skills/category/nested/SKILL.md")
    violations = check_skill_md(skill_md)
    as009 = _violations_with_code(violations, "AS009")
    assert as009 != [], "Expected AS009 warning when plugin.json is in a grandparent directory"
    assert as009[0]["severity"] == "warning"
    assert "plugin.json" in as009[0]["message"]


def test_as009_dot_claude_skills_bare_context_warns(tmp_path: pathlib.Path) -> None:
    """skills/category/nested-skill/SKILL.md under .claude/ with no plugin.json warns.

    Tests: AS009 bare-context variant fires for the canonical .claude/skills/ layout.
    How: Create tmp_path/.claude/skills/category/nested-skill/SKILL.md with no
         plugin.json anywhere in the ancestry, then assert the bare-context
         warning fires.
    Why: Claude Code loads user skills from ~/.claude/skills/. A skill nested at
         .claude/skills/category/name/ will not auto-activate. This is the
         most common real-world occurrence of AS009.
    """
    dot_claude = tmp_path / ".claude"
    skill_md = _make_skill_at_depth(dot_claude, "skills/category/nested-skill/SKILL.md")
    violations = check_skill_md(skill_md)
    as009 = _violations_with_code(violations, "AS009")
    assert as009 != [], "Expected AS009 warning for .claude/skills/category/nested-skill/ layout"
    assert as009[0]["severity"] == "warning"
    assert "will not activate in Claude Code" in as009[0]["message"]


def test_as009_scoped_to_claude_code_platform() -> None:
    """AS009's registry entry declares only the Claude Code platform.

    Tests: AS009 platform scoping, distinct from its AS-series siblings.
    How: Look up the AS009 registry entry and assert its platforms list.
    Why: Unlike AS001/AS006/AS008 (agentskills.io spec rules, which apply to
         every platform), AS009 describes a Claude Code-only auto-discovery
         limitation and cites Claude Code's own docs as its authority — it
         must not be listed under `skilllint rules --platform cursor` or
         `--platform codex`, where the underlying constraint does not exist.
    """
    # Imported locally: importing rule_registry before skilllint.rules.as_series
    # at module scope trips the rule_registry <-> rules circular-import trap
    # documented in ag_series.py's module docstring.
    from skilllint.rule_registry import get_rule

    entry = get_rule("AS009")
    assert entry is not None
    assert entry.platforms == ["claude-code"], entry.platforms
