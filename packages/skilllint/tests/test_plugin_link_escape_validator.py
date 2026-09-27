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

from pathlib import Path

from typer.testing import CliRunner

from skilllint.plugin_validator import PluginLinkEscapeValidator, _get_validators_for_path, app


def _make_plugin(root: Path) -> Path:
    """Create a minimal plugin at *root* and return its root."""
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text('{"name": "demo"}\n', encoding="utf-8")
    return root


def _lk004(plugin: Path) -> list[tuple[str, int | None, str]]:
    result = PluginLinkEscapeValidator().validate(plugin)
    return [(issue.field, issue.line, issue.message) for issue in result.errors if issue.code == "LK004"]


def test_relative_link_climbing_past_plugin_root_is_reported(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "plugins" / "demo")
    skill = plugin / "skills" / "one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# One\n\nSee [rules](../../../rules/x.md).\n", encoding="utf-8")
    (plugin / "docs").mkdir()
    (plugin / "docs" / "guide.md").write_text("[rules](../../rules/x.md)\n", encoding="utf-8")

    findings = _lk004(plugin)

    assert [(field, line) for field, line, _ in findings] == [("docs/guide.md", 1), ("skills/one/SKILL.md", 3)]
    assert "](../../rules/x.md)" in findings[0][2]


def test_escape_is_reported_whether_or_not_the_target_exists(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "plugins" / "demo")
    (tmp_path / "plugins" / "shared.md").write_text("shared\n", encoding="utf-8")
    (plugin / "README.md").write_text("[exists](../shared.md)\n[missing](../gone.md)\n", encoding="utf-8")

    assert [(field, line) for field, line, _ in _lk004(plugin)] == [("README.md", 1), ("README.md", 2)]


def test_root_absolute_link_is_reported(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    (plugin / "README.md").write_text("Credit: [boltons](/mahmoud/boltons)\n", encoding="utf-8")

    assert [(field, line) for field, line, _ in _lk004(plugin)] == [("README.md", 1)]


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
    (plugin / "README.md").write_text(
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
    (plugin / "README.md").write_text(
        "```markdown\n[fenced](../../rules/x.md)\n```\n\n`[inline](../outside.md)`\n", encoding="utf-8"
    )

    assert _lk004(plugin) == []


def test_line_numbers_are_real_after_code_blocks_and_for_repeated_targets(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    (plugin / "README.md").write_text(
        "# Title\n"  # 1
        "\n"  # 2
        "```\n"  # 3
        "[in code](../x.md)\n"  # 4
        "```\n"  # 5
        "\n"  # 6
        "\n"  # 7
        "First [a](../x.md) here.\n"  # 8
        "\n"  # 9
        "Again [b](../x.md) here.\n",  # 10
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


def test_every_markdown_file_in_the_plugin_is_scanned(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    files = [
        "README.md",
        "CLAUDE.md",
        "AGENTS.md",
        "docs/guide.md",
        "agents/a.md",
        "commands/c.md",
        "skills/one/SKILL.md",
        "skills/one/references/r.md",
    ]
    for rel in files:
        target = plugin / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("[out](/outside.md)\n", encoding="utf-8")
    excluded = plugin / "node_modules" / "pkg" / "README.md"
    excluded.parent.mkdir(parents=True)
    excluded.write_text("[out](/outside.md)\n", encoding="utf-8")

    assert sorted(field for field, _, _ in _lk004(plugin)) == sorted(files)


def test_file_path_inside_plugin_selects_the_same_plugin(tmp_path: Path) -> None:
    plugin = _make_plugin(tmp_path / "demo")
    (plugin / "README.md").write_text("[out](../x.md)\n", encoding="utf-8")

    result = PluginLinkEscapeValidator().validate(plugin / ".claude-plugin" / "plugin.json")

    assert [issue.field for issue in result.errors] == ["README.md"]


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
    (plugin / "README.md").write_text("# Demo\n\n[out](../../rules/x.md)\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["check", "--no-color", str(plugin)])

    assert result.exit_code == 1, result.output
    assert "[LK004] README.md:3:" in result.output
