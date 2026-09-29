from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
SKILL = ROOT / "plugins/agentskills-skilllint/skills/skilllint/SKILL.md"
PLUGIN_README = ROOT / "plugins/agentskills-skilllint/README.md"
README = ROOT / "README.md"


def test_agent_skill_queries_runtime_owned_rule_and_command_metadata() -> None:
    text = SKILL.read_text(encoding="utf-8")

    for command in (
        "skilllint --help",
        "skilllint check",
        "skilllint rule <ID>",
        "skilllint rules",
        "skilllint check --fix",
        "skilllint check --check",
    ):
        assert command in text

    for stale_copy_pattern in (
        "Auto-fixable rules:",
        "Not auto-fixable:",
        "The three commands are:",
        "TOKEN_WARNING_THRESHOLD",
        "TOKEN_ERROR_THRESHOLD",
    ):
        assert stale_copy_pattern not in text


def test_plugin_readme_does_not_maintain_a_second_rule_catalog() -> None:
    text = PLUGIN_README.read_text(encoding="utf-8")

    assert "skilllint rules" in text
    assert "skilllint rule <ID>" in text
    assert "| Series | Domain |" not in text
    assert "FM001" + chr(0x2013) + "FM010" not in text


def test_root_readme_defers_volatile_catalog_and_command_inventory_to_runtime() -> None:
    text = README.read_text(encoding="utf-8")

    assert "## Runtime rule reference" in text
    assert "skilllint rules" in text
    assert "skilllint --help" in text
    assert "| Code | Category | Description |" not in text
    assert "Commands:\n  check" not in text


def test_documented_action_examples_use_explicit_release_placeholders() -> None:
    for path in (README, ROOT / "docs/usage.md"):
        text = path.read_text(encoding="utf-8")
        assert "bitflight-devops/skilllint@vX.Y.Z" in text
        assert 'version: "X.Y.Z"' in text


def test_agent_skill_routes_platform_scope_to_per_rule_command() -> None:
    paragraphs = [" ".join(p.split()) for p in SKILL.read_text(encoding="utf-8").split("\n\n")]

    # `skilllint rules` prints no platform column; `skilllint rule <ID>` does.
    assert any("per-rule output" in p and "platform scope" in p for p in paragraphs)
    assert not any("Use `skilllint rules`" in p and "platform" in p for p in paragraphs)


def test_root_readme_explains_release_placeholder_replacement() -> None:
    text = README.read_text(encoding="utf-8")

    action_section = text.split("## GitHub Action", 1)[1].split("```yaml", 1)[0]
    pre_commit_section = text.split("## Pre-commit hook", 1)[1].split("```yaml", 1)[0]
    for section in (action_section, pre_commit_section):
        assert "Replace `X.Y.Z`" in section or "replacing `X.Y.Z`" in section


def test_agent_skill_and_plugin_readme_offer_uv_pipx_and_pip_bootstrap() -> None:
    # mission.json requires uv, pipx, and pip to be supported equally.
    for path in (SKILL, PLUGIN_README):
        text = path.read_text(encoding="utf-8")
        for command in ("uvx skilllint", "pipx run skilllint", "python -m pip install skilllint"):
            assert command in text, (path.name, command)
