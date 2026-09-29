"""Tests for LK004 — markdown link resolves outside the plugin root.

Tests:
- Relative ``../`` and root-absolute ``/`` escapes are reported
- In-plugin links, URLs, anchors, mailto and code-block links are not
- ``${CLAUDE_PLUGIN_ROOT}`` links inside and outside the plugin
- Every Markdown file in the plugin is scanned, not only SKILL.md
- Reported line numbers are the link's own line, including repeated targets
- No plugin root means the rule does not apply
- The public ``skilllint check`` route reports LK004
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from skilllint.plugin_validator import PluginLinkEscapeValidator, _get_validators_for_path, app


def _make_plugin(root: Path) -> Path:
    """Create a minimal plugin at *root* and return its root."""
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text('{"name": "demo"}\n', encoding="utf-8")
    return root


def _doc(plugin: Path) -> Path:
    """Return ``skills/doc.md`` in *plugin*, a file LK004 scans, creating its directory."""
    (plugin / "skills").mkdir(parents=True, exist_ok=True)
    return plugin / "skills" / "doc.md"


def _lk004(plugin: Path) -> list[tuple[str, int | None, str]]:
    result = PluginLinkEscapeValidator().validate(plugin)
    return [(issue.field, issue.line, issue.message) for issue in result.info if issue.code == "LK004"]


def test_relative_link_climbing_past_plugin_root_is_reported(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "plugins" / "demo")
    skill = plugin / "skills" / "one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# One\n\nSee [rules](../../../rules/x.md).\n", encoding="utf-8")
    (plugin / "skills" / "guide.md").write_text("[rules](../../rules/x.md)\n", encoding="utf-8")

    findings = _lk004(plugin)

    assert [(field, line) for field, line, _ in findings] == [("skills/guide.md", 1), ("skills/one/SKILL.md", 3)]
    assert "](../../rules/x.md)" in findings[0][2]


def test_escape_is_reported_whether_or_not_the_target_exists(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "plugins" / "demo")
    (tmp_path / "plugins" / "shared.md").write_text("shared\n", encoding="utf-8")
    _doc(plugin).write_text("[exists](../../shared.md)\n[missing](../../gone.md)\n", encoding="utf-8")

    assert [(field, line) for field, line, _ in _lk004(plugin)] == [("skills/doc.md", 1), ("skills/doc.md", 2)]


def test_root_absolute_link_is_reported(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text("Credit: [boltons](/mahmoud/boltons)\n", encoding="utf-8")

    assert [(field, line) for field, line, _ in _lk004(plugin)] == [("skills/doc.md", 1)]


def test_links_inside_the_plugin_are_not_reported(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    skill = plugin / "skills" / "one"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "[ref](./references/a.md)\n[root readme](../../README.md)\n[missing but inside](references/none.md)\n",
        encoding="utf-8",
    )

    assert _lk004(plugin) == []


def test_urls_anchors_mailto_and_protocol_relative_links_are_ignored(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text(
        "[web](https://example.com/../x)\n"
        "[plain](http://example.com)\n"
        "[ftp](ftp://example.com/x)\n"
        "[anchor](#section)\n"
        "[mail](mailto:someone@example.com)\n"
        "[proto](//cdn.example.com/x.js)\n",
        encoding="utf-8",
    )

    assert _lk004(plugin) == []


def test_links_in_code_blocks_and_inline_code_are_ignored(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text(
        "```markdown\n[fenced](../../../rules/x.md)\n```\n\n`[inline](../../outside.md)`\n", encoding="utf-8"
    )

    assert _lk004(plugin) == []


def test_line_numbers_are_real_after_code_blocks_and_for_repeated_targets(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text(
        "# Title\n"  # 1
        "\n"  # 2
        "```\n"  # 3
        "[in code](../../x.md)\n"  # 4
        "```\n"  # 5
        "\n"  # 6
        "\n"  # 7
        "First [a](../../x.md) here.\n"  # 8
        "\n"  # 9
        "Again [b](../../x.md) here.\n",  # 10
        encoding="utf-8",
    )

    assert [line for _, line, _ in _lk004(plugin)] == [8, 10]


def test_claude_plugin_root_link_inside_plugin_is_not_reported(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    skill = plugin / "skills" / "one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("[doc](${CLAUDE_PLUGIN_ROOT}/docs/guide.md)\n", encoding="utf-8")

    assert _lk004(plugin) == []


def test_claude_plugin_root_link_climbing_out_is_reported(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    skill = plugin / "skills" / "one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("[doc](${CLAUDE_PLUGIN_ROOT}/../rules/x.md)\n", encoding="utf-8")

    assert [(field, line) for field, line, _ in _lk004(plugin)] == [("skills/one/SKILL.md", 1)]


def test_claude_skill_dir_escape_is_reported_and_unresolvable_vars_skipped(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    skill = plugin / "skills" / "one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "[in](${CLAUDE_SKILL_DIR}/references/a.md)\n"
        "[out](${CLAUDE_SKILL_DIR}/../../../x.md)\n"
        "[project](${CLAUDE_PROJECT_DIR}/../x.md)\n",
        encoding="utf-8",
    )

    assert [line for _, line, _ in _lk004(plugin)] == [2]


def test_only_agents_skills_and_commands_are_scanned(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    scanned = ["agents/a.md", "commands/c.md", "skills/one/SKILL.md", "skills/one/references/r.md"]
    skipped = ["README.md", "CLAUDE.md", "AGENTS.md", "docs/guide.md", "docs/adrs/ADR-1.md", "skills/node_modules/p.md"]
    for rel in [*scanned, *skipped]:
        target = plugin / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("[out](/outside.md)\n", encoding="utf-8")

    assert sorted(field for field, _, _ in _lk004(plugin)) == sorted(scanned)


def test_ignore_file_and_path_scoped_ignore_config_are_respected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    for rel in ("skills/keep.md", "skills/vendored/x.md", "skills/quiet.md"):
        (plugin / rel).parent.mkdir(parents=True, exist_ok=True)
        (plugin / rel).write_text("[out](/outside.md)\n", encoding="utf-8")
    (plugin / ".claude-plugin" / "validator.json").write_text(
        '{"ignore": {"skills/quiet.md": ["LK004"]}}\n', encoding="utf-8"
    )
    (tmp_path / ".pluginvalidatorignore").write_text("**/vendored/*.md\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert [field for field, _, _ in _lk004(plugin)] == ["skills/keep.md"]


def test_gitignored_files_are_skipped(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("generated/\n", encoding="utf-8")
    plugin = _make_plugin(tmp_path / "demo")
    for rel in ("skills/keep.md", "skills/generated/x.md"):
        (plugin / rel).parent.mkdir(parents=True, exist_ok=True)
        (plugin / rel).write_text("[out](/outside.md)\n", encoding="utf-8")

    assert [field for field, _, _ in _lk004(plugin)] == ["skills/keep.md"]


def test_file_path_inside_plugin_selects_the_same_plugin(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text("[out](../../x.md)\n", encoding="utf-8")

    result = PluginLinkEscapeValidator().validate(plugin / ".claude-plugin" / "plugin.json")

    assert [issue.field for issue in result.info] == ["skills/doc.md"]


def test_no_plugin_root_means_rule_does_not_apply(tmp_path: Path) -> None:
    skill = tmp_path / "standalone"
    skill.mkdir()
    (skill / "SKILL.md").write_text("[out](../../rules/x.md)\n", encoding="utf-8")

    result = PluginLinkEscapeValidator().validate(skill / "SKILL.md")

    assert result.passed is True
    assert result.errors == []
    assert not any(isinstance(v, PluginLinkEscapeValidator) for v in _get_validators_for_path(skill / "SKILL.md"))


def test_cli_check_on_plugin_directory_reports_lk004_with_file_and_line(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text("# Demo\n\n[out](../../../rules/x.md)\n", encoding="utf-8")

    quiet = CliRunner().invoke(app, ["check", "--no-color", str(plugin)])
    result = CliRunner().invoke(app, ["check", "--no-color", "--verbose", str(plugin)])

    # An observation: never fails the run, and shows only with --verbose.
    assert quiet.exit_code == 0, quiet.output
    assert "[LK004]" not in quiet.output
    assert result.exit_code == 0, result.output
    assert "[LK004] skills/doc.md:3:" in result.output
    assert "may dangle at runtime when the plugin is installed" in result.output


def test_reference_definitions_are_checked_with_titles_and_real_lines(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text(
        "# Demo\n"  # 1
        "\n"  # 2
        "See [rules][r] and [site][s].\n"  # 3
        "\n"  # 4
        "```markdown\n"  # 5
        "[fenced]: ../../../rules/x.md\n"  # 6
        "```\n"  # 7
        "\n"  # 8
        '[r]: ../../rules/x.md "Shared rules"\n'  # 9
        "[s]: https://example.com/\n"  # 10
        "[in]: ./docs/a.md 'inside'\n"  # 11
        "  [abs]: </abs path.md> (title)\n"  # 12
        "[^note]: ../../not-a-link.md\n",  # 13
        encoding="utf-8",
    )

    findings = _lk004(plugin)

    assert [line for _, line, _ in findings] == [9, 12]
    assert "[r](../../rules/x.md)" in findings[0][2]
    assert "[abs](/abs path.md)" in findings[1][2]


@pytest.mark.parametrize(
    "destination",
    [
        r"\.\./outside.md",
        "%2E%2E/outside.md",
        "&#46;&#46;/outside.md",
        "&#x2E;&#x2E;/outside.md",
        "&period;&period;/outside.md",
        r"\/abs.md",
    ],
    ids=[
        "backslash-escape",
        "percent-encoded",
        "decimal-reference",
        "hex-reference",
        "named-reference",
        "escaped-root",
    ],
)
def test_encoded_escaping_destinations_are_decoded_and_reported(tmp_path: Path, destination: str) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    # From skills/doc.md one extra ../ is needed to leave the plugin; a root-absolute form needs none.
    up = "" if destination.startswith("\\/") else "../"
    _doc(plugin).write_text(f"# Demo\n\n[x]({up}{destination})\n[r]: {up}{destination}\n", encoding="utf-8")

    assert [line for _, line, _ in _lk004(plugin)] == [3, 4]


def test_encoded_url_and_in_plugin_destinations_are_not_reported(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text(
        "[web](&#104;ttps://example.com/../x)\n[inside](docs%2Fa.md)\n[hash](a%23b.md)\n", encoding="utf-8"
    )

    assert _lk004(plugin) == []


def _make_codex_plugin(root: Path) -> Path:
    (root / ".codex-plugin").mkdir(parents=True)
    (root / ".codex-plugin" / "plugin.json").write_text('{"name": "demo"}\n', encoding="utf-8")
    return root


def test_codex_only_plugin_is_checked(tmp_path: Path) -> None:
    plugin = _make_codex_plugin(tmp_path / "demo")
    _doc(plugin).write_text("[out](../../outside.md)\n", encoding="utf-8")

    assert [(field, line) for field, line, _ in _lk004(plugin)] == [("skills/doc.md", 1)]
    result = PluginLinkEscapeValidator().validate(plugin / ".codex-plugin" / "plugin.json")
    assert [issue.field for issue in result.info] == ["skills/doc.md"]


def test_codex_only_plugin_claude_plugin_root_escape_is_reported(tmp_path: Path) -> None:
    """``${CLAUDE_PLUGIN_ROOT}`` must resolve for a Codex-only plugin root.

    Regression test: ``check_lk004`` used to resolve ``${CLAUDE_PLUGIN_ROOT}``
    via the Claude-only ``find_plugin_dir`` (only checks
    ``.claude-plugin/plugin.json``) instead of reusing the plugin root
    ``find_link_scope_plugin_dir`` already resolved (which also recognizes
    ``.codex-plugin/plugin.json``). For a Codex-only plugin, that
    re-derivation returned ``None``, so the substitution silently failed and
    the link was skipped instead of being flagged as an escape.
    """
    plugin = _make_codex_plugin(tmp_path / "demo")
    skill = plugin / "skills" / "one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("[doc](${CLAUDE_PLUGIN_ROOT}/../../x.md)\n", encoding="utf-8")

    assert [(field, line) for field, line, _ in _lk004(plugin)] == [("skills/one/SKILL.md", 1)]


def test_cli_check_on_codex_only_plugin_reports_lk004(tmp_path: Path) -> None:
    plugin = _make_codex_plugin(tmp_path / "plugins" / "demo")
    _doc(plugin).write_text("# Demo\n\n[out](../../../rules/x.md)\n", encoding="utf-8")

    for target in (plugin, tmp_path):
        result = CliRunner().invoke(app, ["check", "--no-color", "--verbose", str(target)])

        assert result.exit_code == 0, result.output
        assert result.output.count("[LK004] skills/doc.md:3:") == 1, result.output


def test_plugin_with_claude_and_codex_manifests_is_reported_once(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "plugins" / "demo")
    _make_codex_plugin(plugin)
    _doc(plugin).write_text("[out](../../../rules/x.md)\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["check", "--no-color", "--verbose", str(tmp_path)])

    assert result.output.count("[LK004]") == 1, result.output


def test_cursor_only_plugin_is_not_checked(tmp_path: Path) -> None:
    plugin = tmp_path / "demo"
    (plugin / ".cursor-plugin").mkdir(parents=True)
    (plugin / ".cursor-plugin" / "plugin.json").write_text('{"name": "demo"}\n', encoding="utf-8")
    _doc(plugin).write_text("[out](../../outside.md)\n", encoding="utf-8")

    assert _lk004(plugin) == []
    assert "[LK004]" not in CliRunner().invoke(app, ["check", "--no-color", "--verbose", str(tmp_path)]).output


def test_inline_links_with_titles_resolve_to_the_destination_only(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text(
        '[a](../../a.md "Double")\n'  # 1
        "[b](../../b.md 'Single')\n"  # 2
        "[c](../../c.md (Paren))\n"  # 3
        '[d](<../../with space.md> "Title")\n'  # 4
        '[in](./docs/a.md "Inside")\n'  # 5
        "[not a link](../../x.md bad title)\n",  # 6: invalid title, not a link
        encoding="utf-8",
    )

    findings = _lk004(plugin)

    assert [line for _, line, _ in findings] == [1, 2, 3, 4]
    assert "[d](../../with space.md)" in findings[3][2]


def test_html_href_and_src_escapes_are_reported(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text(
        '<p align="center">\n'  # 1
        '  <img alt="logo" src="../../../assets/logo.png">\n'  # 2
        "</p>\n"  # 3
        "\n"  # 4
        "Inline <a href=\"../../x.md\">x</a> and <a HREF='../&#46;&#46;/y.md'>y</a>.\n"  # 5
        "<img\n"  # 6
        "  src=../../z.png>\n"  # 7
        '<a href="https://example.com">site</a> <a href="#top">top</a> <img src="./assets/in.png">\n'  # 8
        '`<a href="../../code.md">`\n',  # 9
        encoding="utf-8",
    )

    findings = _lk004(plugin)

    assert [line for _, line, _ in findings] == [2, 5, 5, 7]
    assert "[<img src>](../../../assets/logo.png)" in findings[0][2]


def test_html_comments_are_not_links_and_keep_line_numbers(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text(
        '<!-- <img src="../../../old.png"> -->\n'  # 1
        "<!--\n"  # 2
        "[x](../../../y.md)\n"  # 3
        "-->\n"  # 4
        "[after](../../after.md)\n",  # 5
        encoding="utf-8",
    )

    assert [line for _, line, _ in _lk004(plugin)] == [5]


def test_balanced_parentheses_in_bare_destinations(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text(
        "[p](../../a(b).md)\n"  # 1: escapes, parenthesised name kept whole
        "[w](https://en.wikipedia.org/wiki/Foo_(bar)) [in](./docs/c(d).md)\n"  # 2: URL ignored, inside
        '[e](../../e\\(f.md "t")\n',  # 3: escaped parenthesis
        encoding="utf-8",
    )

    findings = _lk004(plugin)

    assert [line for _, line, _ in findings] == [1, 3]
    assert "[p](../../a(b).md)" in findings[0][2]


def test_backslash_is_a_separator_in_html_but_literal_in_markdown(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    _doc(plugin).write_text(
        '<a href="..\\..\\..\\outside.md">x</a>\n'  # 1: WHATWG reads \ as /, escapes
        '<img src="assets\\logo.png"> <a href="\\\\host\\x">h</a>\n'  # 2: inside; \\host is //host
        '<a href="..%5C..%5Cy.md">l</a>\n'  # 3: %5C is a literal backslash, not a separator
        "[b](..\\..\\outside.md) [c](x\\y/..\\z.md)\n",  # 4: Markdown keeps \ literal (renders as %5C)
        encoding="utf-8",
    )

    findings = _lk004(plugin)

    assert [line for _, line, _ in findings] == [1]
    assert f"({tmp_path.parent / 'outside.md'})" in findings[0][2]


def test_platform_codex_reports_lk004_and_lk001_on_a_codex_plugin(tmp_path: Path) -> None:
    plugin = _make_codex_plugin(tmp_path / "plugins" / "demo")
    skill = plugin / "skills" / "one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: one\ndescription: Use when checking Codex platform routing of link rules.\n---\n\n"
        "[gone](./references/missing.md)\n",
        encoding="utf-8",
    )
    _doc(plugin).write_text("[out](../../../rules/x.md)\n", encoding="utf-8")

    for args in (["--platform", "codex"], []):
        result = CliRunner().invoke(app, ["check", "--no-color", "--verbose", *args, str(tmp_path)])

        assert result.exit_code == 1, result.output  # the LK001 error; LK004 is info
        assert result.output.count("[LK004]") == 1, (args, result.output)
        assert result.output.count("[LK001]") == 1, (args, result.output)


def test_platform_cursor_runs_neutral_lk001_but_not_lk004(tmp_path: Path) -> None:
    skill = tmp_path / ".agents" / "skills" / "one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: one\ndescription: Use when checking Cursor platform routing of link rules.\n---\n\n"
        "[gone](./references/missing.md)\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["check", "--no-color", "--verbose", "--platform", "cursor", str(tmp_path)])

    assert result.output.count("[LK001]") == 1, result.output
    assert "[LK004]" not in result.output, result.output


def test_agent_file_relative_links_resolve_against_the_project_not_the_plugin(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    (plugin / "agents").mkdir()
    (plugin / "docs").mkdir()
    (plugin / "agents" / "helper.md").write_text(
        "---\nname: helper\ndescription: Helper agent.\n---\n\n"  # 1-4
        "Read [guide](../docs/guide.md) first.\n"  # 6: relative, resolves against the project cwd
        "Or [pinned](${CLAUDE_PLUGIN_ROOT}/docs/guide.md).\n"  # 7: inside the plugin, not reported
        "And [abs](/etc/x.md).\n",  # 8: root-absolute, outside the plugin
        encoding="utf-8",
    )
    (plugin / "docs" / "guide.md").write_text("[back](../agents/helper.md)\n", encoding="utf-8")

    findings = _lk004(plugin)

    assert [(field, line) for field, line, _ in findings] == [("agents/helper.md", 6), ("agents/helper.md", 8)]
    assert "resolves against the user's project root" in findings[0][2]
    assert "points outside the plugin" in findings[1][2]


def test_command_file_relative_links_resolve_against_the_project_not_the_plugin(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    (plugin / "commands").mkdir()
    (plugin / "commands" / "run.md").write_text(
        "Follow [steps](./steps.md).\nOr [pinned](${CLAUDE_PLUGIN_ROOT}/skills/x/SKILL.md).\n", encoding="utf-8"
    )

    findings = _lk004(plugin)

    assert [(field, line) for field, line, _ in findings] == [("commands/run.md", 1)]
    assert "agent or command body" in findings[0][2]


def test_same_document_anchors_are_not_links_in_agent_and_command_files(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    (plugin / "agents").mkdir()
    (plugin / "agents" / "a.md").write_text('[top](#top) <a href="#sec">s</a>\n', encoding="utf-8")

    assert _lk004(plugin) == []
