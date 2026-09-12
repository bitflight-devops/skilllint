"""Unit tests for PluginRegistrationValidator.

Tests:
- Graceful pass when .claude-plugin/plugin.json is absent (TestNoPluginJson)
- PL002 error for malformed plugin.json (TestInvalidJson)
- PR001 warning for unregistered agent (TestUnregisteredAgent)
- PR001 warning for unregistered command (TestUnregisteredCommand)
- PR002 error when registered path does not exist (TestMissingRegisteredFile)
- PR005 info when a registered command path is a skill directory (TestCommandPathIsSkillDirectory)
- No errors when all capabilities registered and files exist (TestFullyRegistered)
- Empty plugin with no capabilities passes (TestEmptyPlugin)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec.json
import pytest

from skilllint.plugin_validator import PluginRegistrationValidator

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helper factory functions
# ---------------------------------------------------------------------------


def _make_plugin(tmp_path: Path, plugin_name: str = "test-plugin", plugin_json_content: str | None = None) -> Path:
    """Create a plugin directory with .claude-plugin/plugin.json.

    Args:
        tmp_path: Pytest temporary directory
        plugin_name: Name of the plugin directory
        plugin_json_content: Raw JSON string for plugin.json; if None, a
            minimal valid JSON is written

    Returns:
        Path to the plugin root directory
    """
    plugin_dir = tmp_path / plugin_name
    plugin_dir.mkdir()
    claude_plugin = plugin_dir / ".claude-plugin"
    claude_plugin.mkdir()

    if plugin_json_content is not None:
        (claude_plugin / "plugin.json").write_text(plugin_json_content)
    else:
        default_config = {"name": plugin_name, "skills": [], "agents": [], "commands": []}
        (claude_plugin / "plugin.json").write_text(
            msgspec.json.format(msgspec.json.encode(default_config), indent=2).decode()
        )

    return plugin_dir


def _add_skill(plugin_dir: Path, skill_name: str) -> Path:
    """Create a skill directory with SKILL.md inside the plugin.

    Args:
        plugin_dir: Plugin root directory
        skill_name: Skill directory name

    Returns:
        Path to the new SKILL.md
    """
    skill_dir = plugin_dir / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(f"---\ndescription: {skill_name}\n---\n\n# {skill_name}\n")
    return skill_md


def _add_agent(plugin_dir: Path, agent_name: str) -> Path:
    """Create an agent .md file inside the plugin.

    Args:
        plugin_dir: Plugin root directory
        agent_name: Agent file stem (without .md extension)

    Returns:
        Path to the new agent .md file
    """
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir(exist_ok=True)
    agent_md = agents_dir / f"{agent_name}.md"
    agent_md.write_text(f"---\nname: {agent_name}\ndescription: Test agent\n---\n\n# {agent_name}\n")
    return agent_md


def _add_command(plugin_dir: Path, command_name: str) -> Path:
    """Create a command .md file inside the plugin.

    Args:
        plugin_dir: Plugin root directory
        command_name: Command file stem (without .md extension)

    Returns:
        Path to the new command .md file
    """
    commands_dir = plugin_dir / "commands"
    commands_dir.mkdir(exist_ok=True)
    command_md = commands_dir / f"{command_name}.md"
    command_md.write_text(f"---\ndescription: {command_name} command\n---\n\n# {command_name}\n")
    return command_md


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestNoPluginJson:
    """Test validator passes gracefully when plugin.json is absent."""

    def test_no_plugin_json_passes(self, tmp_path: Path) -> None:
        """Test validation passes when .claude-plugin/plugin.json does not exist.

        Tests: Missing plugin.json handling
        How: Create plugin dir without plugin.json, validate
        Why: Validator skips gracefully; not all directories are plugins
        """
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        # No .claude-plugin directory or plugin.json

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_claude_plugin_dir_exists_but_no_plugin_json_passes(self, tmp_path: Path) -> None:
        """Test validation passes when .claude-plugin/ exists but plugin.json absent.

        Tests: plugin.json presence check
        How: Create .claude-plugin/ directory without plugin.json, validate
        Why: Validator checks file existence before attempting JSON load
        """
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / ".claude-plugin").mkdir()
        # plugin.json deliberately absent

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_validates_from_skill_file_path(self, tmp_path: Path) -> None:
        """Test validator can be called with a file path inside the plugin.

        Tests: _find_plugin_dir traversal from file path
        How: Pass skill file path instead of plugin dir, verify graceful result
        Why: validate(path) accepts both file and directory paths
        """
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        skill_dir = plugin_dir / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("---\ndescription: Test\n---\n\n# Test\n")
        # No plugin.json -- passes gracefully

        validator = PluginRegistrationValidator()
        result = validator.validate(skill_md)

        assert result.passed is True


class TestInvalidJson:
    """Test PL002 error for malformed plugin.json."""

    def test_invalid_json_syntax_produces_pl002(self, tmp_path: Path) -> None:
        """Test PL002 error reported for malformed JSON in plugin.json.

        Tests: JSON parse error detection (PL002)
        How: Write invalid JSON to plugin.json, validate
        Why: Malformed JSON prevents capability discovery and must be flagged
        """
        plugin_dir = _make_plugin(tmp_path, plugin_json_content='{"name": "test", INVALID}')

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is False
        pl002_errors = [e for e in result.errors if e.code == "PL002"]
        assert len(pl002_errors) >= 1

    def test_completely_empty_plugin_json_produces_pl002(self, tmp_path: Path) -> None:
        """Test PL002 error for completely empty plugin.json.

        Tests: Empty file handling (PL002)
        How: Write empty string to plugin.json, validate
        Why: Empty file is invalid JSON
        """
        plugin_dir = _make_plugin(tmp_path, plugin_json_content="")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is False
        pl002_errors = [e for e in result.errors if e.code == "PL002"]
        assert len(pl002_errors) >= 1

    def test_invalid_json_pl002_has_suggestion(self, tmp_path: Path) -> None:
        """Test PL002 error includes a suggestion for resolving the issue.

        Tests: Suggestion field populated for PL002
        How: Write invalid JSON, validate, check suggestion
        Why: Actionable suggestions help users fix validation errors
        """
        plugin_dir = _make_plugin(tmp_path, plugin_json_content="{not valid json at all")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pl002_errors = [e for e in result.errors if e.code == "PL002"]
        assert len(pl002_errors) >= 1
        assert all(e.suggestion is not None for e in pl002_errors)

    def test_can_fix_returns_false(self) -> None:
        """Test can_fix() returns False for PluginRegistrationValidator.

        Tests: Auto-fix capability
        How: Call can_fix(), assert False
        Why: Registration issues require manual plugin.json edits
        """
        validator = PluginRegistrationValidator()
        assert validator.can_fix() is False

    def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
        """Test fix() raises NotImplementedError.

        Tests: Auto-fix raises correctly
        How: Call fix() on plugin dir, expect NotImplementedError
        Why: Registration fixes require manual plugin.json edits
        """
        plugin_dir = _make_plugin(tmp_path)

        validator = PluginRegistrationValidator()
        with pytest.raises(NotImplementedError):
            validator.fix(plugin_dir)


class TestUnregisteredAgent:
    """Test PR001 warning when agent file exists but is not in plugin.json."""

    def test_unregistered_agent_produces_pr001(self, tmp_path: Path) -> None:
        """Test PR001 warning for agent existing without registration.

        Tests: Unregistered agent detection (PR001)
        How: Create agent file, leave plugin.json agents array empty, validate
        Why: Unregistered agents must be flagged for explicit registration
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent(plugin_dir, "my-agent")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) >= 1

    def test_unregistered_agent_warning_mentions_agent_name(self, tmp_path: Path) -> None:
        """Test PR001 warning message references the unregistered agent name.

        Tests: PR001 warning message for agent
        How: Create named agent, validate, check warning message
        Why: Warning must identify which agent needs registration
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent(plugin_dir, "unregistered-agent")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) >= 1
        assert any("unregistered-agent" in w.message for w in pr001_warnings)

    def test_registered_agent_no_pr001(self, tmp_path: Path) -> None:
        """Test no PR001 warning when agent is registered in plugin.json.

        Tests: Registered agent accepted without warning
        How: Create agent, register it in plugin.json, validate
        Why: Registered agents should not generate PR001 warnings
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "agents": ["./agents/my-agent.md"],
            }).decode(),
        )
        _add_agent(plugin_dir, "my-agent")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) == 0

    def test_normalized_registered_agent_directory_has_no_pr001(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "agents": ["./aliases/../agents"],
            }).decode(),
        )
        _add_agent(plugin_dir, "my-agent")

        result = PluginRegistrationValidator().validate(plugin_dir)

        assert not [warning for warning in result.warnings if warning.code == "PR001"]

    def test_pr001_keeps_distinct_in_root_symlink_aliases(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({"name": "test-plugin", "agents": ["./agents/a.md"]}).decode(),
        )
        (plugin_dir / "agents").mkdir()
        (plugin_dir / "shared").mkdir()
        (plugin_dir / "shared" / "agent.md").write_text("---\ndescription: alias target\n---\n")
        (plugin_dir / "agents" / "a.md").symlink_to("../shared/agent.md")
        (plugin_dir / "agents" / "b.md").symlink_to("../shared/agent.md")

        result = PluginRegistrationValidator().validate(plugin_dir)

        assert [warning.message for warning in result.warnings if warning.code == "PR001"] == [
            "Agent 'agents/b.md' exists but is not registered"
        ]

    def test_pr001_ignores_dangling_agent_symlink(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(
            tmp_path, plugin_json_content=msgspec.json.encode({"name": "test-plugin", "agents": []}).decode()
        )
        (plugin_dir / "agents").mkdir()
        (plugin_dir / "agents" / "ghost.md").symlink_to("missing.md")

        result = PluginRegistrationValidator().validate(plugin_dir)

        assert not [warning for warning in result.warnings if warning.code == "PR001"]

    def test_registered_directory_skips_external_symlink_child(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({"name": "test-plugin", "commands": ["./custom"]}).decode(),
        )
        external_file = tmp_path / "external.md"
        external_file.write_text("# External\n")
        custom_dir = plugin_dir / "custom"
        custom_dir.mkdir()
        (custom_dir / "external.md").symlink_to(external_file)

        result = PluginRegistrationValidator().validate(plugin_dir)

        assert result.passed is True

    def test_no_pr001_for_unregistered_agent_when_agents_field_absent(self, tmp_path: Path) -> None:
        """Test no PR001 warning for an agent when 'agents' is absent from plugin.json.

        Tests: PR001 suppression for agents when the field is undeclared
        How: plugin.json has no 'agents' key at all; an agent file exists; validate
        Why: Per the vendor path-behavior rules, an explicit 'agents' array replaces
            default discovery of ./agents/ -- only once declared. When the field is
            absent, Claude Code still auto-discovers ./agents/ wholesale, so an
            unregistered agent there is not a genuine gap and must not be flagged.
        """
        plugin_dir = _make_plugin(tmp_path, plugin_json_content=msgspec.json.encode({"name": "test-plugin"}).decode())
        _add_agent(plugin_dir, "auto-discovered-agent")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) == 0

    def test_pr001_fires_for_unregistered_agent_when_agents_field_explicitly_empty(self, tmp_path: Path) -> None:
        """Test PR001 fires for an orphan agent when 'agents' is an explicit empty array.

        Tests: PR001 for agents once the plugin has opted into explicit registration
        How: plugin.json declares 'agents': [] explicitly; an unregistered agent
            file exists; validate
        Why: Declaring 'agents' (even empty) replaces default discovery of
            ./agents/, per the vendor path-behavior rules, so any file Claude Code
            still finds there is a genuine gap that PR001 must flag.
        """
        plugin_dir = _make_plugin(
            tmp_path, plugin_json_content=msgspec.json.encode({"name": "test-plugin", "agents": []}).decode()
        )
        _add_agent(plugin_dir, "orphan-agent")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) >= 1
        assert any("orphan-agent" in w.message for w in pr001_warnings)

    def test_pr001_orders_multiple_orphans_by_component_path(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({"name": "test-plugin", "agents": [], "commands": []}).decode(),
        )
        _add_agent(plugin_dir, "zeta")
        _add_agent(plugin_dir, "alpha")
        _add_command(plugin_dir, "zeta")
        _add_command(plugin_dir, "alpha")

        result = PluginRegistrationValidator().validate(plugin_dir)

        assert [warning.message for warning in result.warnings if warning.code == "PR001"] == [
            "Agent 'agents/alpha.md' exists but is not registered",
            "Agent 'agents/zeta.md' exists but is not registered",
            "Command 'commands/alpha.md' exists but is not registered",
            "Command 'commands/zeta.md' exists but is not registered",
        ]


class TestUnregisteredCommand:
    """Test PR001 warning when command file exists but is not in plugin.json."""

    def test_unregistered_command_produces_pr001(self, tmp_path: Path) -> None:
        """Test PR001 warning for command existing without registration.

        Tests: Unregistered command detection (PR001)
        How: Create command file, leave plugin.json commands array empty, validate
        Why: Unregistered commands must be flagged
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_command(plugin_dir, "my-command")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) >= 1

    def test_no_pr001_for_unregistered_command_when_commands_field_absent(self, tmp_path: Path) -> None:
        """Test no PR001 warning for a command when 'commands' is absent from plugin.json.

        Tests: PR001 suppression for commands when the field is undeclared
        How: plugin.json has no 'commands' key at all; a command file exists; validate
        Why: Per the vendor path-behavior rules, an explicit 'commands' array
            replaces default discovery of ./commands/ -- only once declared. When
            the field is absent, Claude Code still auto-discovers ./commands/
            wholesale, so an unregistered command there is not a genuine gap.
        """
        plugin_dir = _make_plugin(tmp_path, plugin_json_content=msgspec.json.encode({"name": "test-plugin"}).decode())
        _add_command(plugin_dir, "auto-discovered-command")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) == 0

    def test_pr001_fires_for_unregistered_command_when_commands_field_explicitly_empty(self, tmp_path: Path) -> None:
        """Test PR001 fires for an orphan command when 'commands' is an explicit empty array.

        Tests: PR001 for commands once the plugin has opted into explicit registration
        How: plugin.json declares 'commands': [] explicitly; an unregistered command
            file exists; validate
        Why: Declaring 'commands' (even empty) replaces default discovery of
            ./commands/, per the vendor path-behavior rules, so any file Claude Code
            still finds there is a genuine gap that PR001 must flag.
        """
        plugin_dir = _make_plugin(
            tmp_path, plugin_json_content=msgspec.json.encode({"name": "test-plugin", "commands": []}).decode()
        )
        _add_command(plugin_dir, "orphan-command")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) >= 1
        assert any("orphan-command" in w.message for w in pr001_warnings)

    def test_registered_command_no_pr001(self, tmp_path: Path) -> None:
        """Test no PR001 warning when command is registered in plugin.json.

        Tests: Registered command accepted without warning
        How: Create command, register it in plugin.json, validate
        Why: Registered commands should not generate PR001 warnings
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "commands": ["./commands/my-command.md"],
            }).decode(),
        )
        _add_command(plugin_dir, "my-command")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) == 0

    def test_readme_and_claude_md_not_treated_as_commands(self, tmp_path: Path) -> None:
        """Test CLAUDE.md and README.md in commands/ are not flagged as unregistered.

        Tests: CLAUDE.md and README.md exclusion from command discovery
        How: Create CLAUDE.md and README.md in commands/ dir, validate
        Why: _find_actual_capabilities excludes these filenames explicitly
        """
        plugin_dir = _make_plugin(tmp_path)
        commands_dir = plugin_dir / "commands"
        commands_dir.mkdir()
        (commands_dir / "CLAUDE.md").write_text("# Claude instructions\n")
        (commands_dir / "README.md").write_text("# Commands readme\n")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        # CLAUDE.md and README.md must not produce PR001 warnings
        assert len(pr001_warnings) == 0


class TestMissingRegisteredFile:
    """Test PR002 error when plugin.json lists paths that do not exist."""

    def test_registered_direct_skill_file_does_not_produce_pr002(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "skills": ["./skills/example/SKILL.md"],
            }).decode(),
        )
        _add_skill(plugin_dir, "example")

        result = PluginRegistrationValidator().validate(plugin_dir)

        assert [issue for issue in result.errors if issue.code == "PR002"] == []

    def test_registered_skill_not_on_disk_produces_pr002(self, tmp_path: Path) -> None:
        """Test PR002 error when registered skill SKILL.md does not exist on disk.

        Tests: Missing registered skill detection (PR002)
        How: Register skill in plugin.json without creating SKILL.md, validate
        Why: Registered paths that do not exist are broken configurations (PR002)
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "skills": ["./skills/phantom-skill/"],
            }).decode(),
        )
        # Do NOT create the skills/phantom-skill/SKILL.md

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is False
        pr002_errors = [e for e in result.errors if e.code == "PR002"]
        assert len(pr002_errors) >= 1

    def test_registered_agent_not_on_disk_produces_pr002(self, tmp_path: Path) -> None:
        """Test PR002 error when registered agent .md does not exist on disk.

        Tests: Missing registered agent detection (PR002)
        How: Register agent path in plugin.json without creating file, validate
        Why: Registered agent paths that do not exist are broken configurations (PR002)
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "agents": ["./agents/phantom-agent.md"],
            }).decode(),
        )
        # Do NOT create agents/phantom-agent.md

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is False
        pr002_errors = [e for e in result.errors if e.code == "PR002"]
        assert len(pr002_errors) >= 1

    def test_registered_command_not_on_disk_produces_pr002(self, tmp_path: Path) -> None:
        """Test PR002 error when registered command .md does not exist on disk.

        Tests: Missing registered command detection (PR002)
        How: Register command path in plugin.json without creating file, validate
        Why: Registered command paths that do not exist are broken (PR002)
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "commands": ["./commands/phantom-cmd.md"],
            }).decode(),
        )
        # Do NOT create commands/phantom-cmd.md

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is False
        pr002_errors = [e for e in result.errors if e.code == "PR002"]
        assert len(pr002_errors) >= 1

    def test_pr002_error_has_suggestion(self, tmp_path: Path) -> None:
        """Test PR002 error includes a suggestion for resolving the issue.

        Tests: Suggestion field populated for PR002
        How: Register non-existent skill, validate, check suggestion
        Why: Actionable suggestions help users remove or create the referenced path
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "skills": ["./skills/ghost-skill/"],
            }).decode(),
        )

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr002_errors = [e for e in result.errors if e.code == "PR002"]
        assert len(pr002_errors) >= 1
        assert all(e.suggestion is not None for e in pr002_errors)


class TestCommandPathIsSkillDirectory:
    """Test PR005 info issue when a registered command path is a skill directory.

    PR005 downgraded from error to info per issue #195: code.claude.com/docs/en/
    plugins-reference documents 'commands' as accepting directories (not just
    flat .md files), so this configuration is valid, not load-blocking -- it
    only forgoes skill-only features that code.claude.com/docs/en/skills
    describes as the reason skills are recommended over commands.
    """

    def test_command_path_that_is_skill_directory_produces_pr005_info(self, tmp_path: Path) -> None:
        """Test PR005 info issue for a command path that is a SKILL.md directory.

        Tests: PR005 detection and severity (check_pr005 in pr_series.py)
        How: Register a directory containing SKILL.md under 'commands', validate
        Why: PR005 must still detect this configuration, now as a recommendation
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "commands": ["./commands/embedded-skill/"],
            }).decode(),
        )
        skill_dir = plugin_dir / "commands" / "embedded-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: embedded-skill\n---\n\n# embedded-skill\n")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr005_info = [i for i in result.info if i.code == "PR005"]
        assert len(pr005_info) >= 1
        assert not any(i.code == "PR005" for i in result.errors)
        assert not any(i.code == "PR005" for i in result.warnings)

    def test_pr005_does_not_fail_validation(self, tmp_path: Path) -> None:
        """Test PR005 alone does not fail validation (result.passed stays True).

        Tests: PR005 severity is info, not error
        How: Register a skill directory under 'commands' with no other issues, validate
        Why: An info-severity rule must not flip result.passed to False
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "commands": ["./commands/embedded-skill/"],
            }).decode(),
        )
        skill_dir = plugin_dir / "commands" / "embedded-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: embedded-skill\n---\n\n# embedded-skill\n")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True

    def test_pr005_message_does_not_claim_it_may_prevent_loading(self, tmp_path: Path) -> None:
        """Test PR005's message no longer contains the unsourced load-blocking claim.

        Tests: PR005 message content after issue #195's rewrite
        How: Trigger PR005, inspect the message text
        Why: The prior message claimed the config "may prevent the skill from
            loading" with no vendor-doc citation backing that claim; issue #195
            required removing it, not softening it
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "commands": ["./commands/embedded-skill/"],
            }).decode(),
        )
        skill_dir = plugin_dir / "commands" / "embedded-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: embedded-skill\n---\n\n# embedded-skill\n")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr005_info = [i for i in result.info if i.code == "PR005"]
        assert len(pr005_info) >= 1
        assert not any("may prevent the skill from loading" in i.message for i in pr005_info)
        assert not any("must not be listed" in i.message for i in pr005_info)


class TestFullyRegistered:
    """Test no errors or PR001 warnings when all capabilities are registered and exist."""

    def test_fully_registered_plugin_passes(self, tmp_path: Path) -> None:
        """Test plugin with all capabilities registered passes with no errors.

        Tests: Happy path -- all capabilities registered and present
        How: Create skill, agent, command; register all in plugin.json; validate
        Why: Correctly configured plugin must produce zero errors or PR001 warnings
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "skills": ["./skills/my-skill/"],
                "agents": ["./agents/my-agent.md"],
                "commands": ["./commands/my-cmd.md"],
            }).decode(),
        )
        _add_skill(plugin_dir, "my-skill")
        _add_agent(plugin_dir, "my-agent")
        _add_command(plugin_dir, "my-cmd")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0
        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) == 0

    def test_fully_registered_plugin_from_skill_file(self, tmp_path: Path) -> None:
        """Test validation via file path inside plugin finds plugin.json.

        Tests: _find_plugin_dir traversal for file path input
        How: Call validate() with a SKILL.md path, assert passes
        Why: validate() must handle file inputs by traversing up to plugin root
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({"name": "test-plugin", "skills": ["./skills/my-skill/"]}).decode(),
        )
        skill_md = _add_skill(plugin_dir, "my-skill")

        validator = PluginRegistrationValidator()
        result = validator.validate(skill_md)

        assert result.passed is True
        assert len(result.errors) == 0
        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) == 0

    @pytest.mark.skip(reason="Superseded by additive skills contract")
    def test_mixed_registered_and_unregistered_separates_correctly(self, tmp_path: Path) -> None:
        """Test only the unregistered skill generates PR001, registered one does not.

        Tests: Partial registration -- mix of registered and unregistered
        How: Register one skill, leave another unregistered, validate
        Why: Each skill must be evaluated independently
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "skills": ["./skills/alpha-skill/"],
            }).decode(),
        )
        _add_skill(plugin_dir, "alpha-skill")
        _add_skill(plugin_dir, "beta-skill")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        # Only the unregistered skill should produce PR001
        assert len(pr001_warnings) >= 1
        assert any("beta-skill" in w.message for w in pr001_warnings)
        # The registered skill must not generate a PR001 warning
        assert not any("alpha-skill" in w.message for w in pr001_warnings)


class TestEmptyPlugin:
    """Test plugin with no skills, agents, or commands and empty arrays passes."""

    def test_empty_plugin_passes(self, tmp_path: Path) -> None:
        """Test plugin with no capabilities and empty plugin.json arrays passes.

        Tests: Empty plugin happy path
        How: Create plugin with no skills/agents/commands directories, validate
        Why: A plugin under construction should not generate spurious errors
        """
        plugin_dir = _make_plugin(
            tmp_path,
            plugin_json_content=msgspec.json.encode({
                "name": "test-plugin",
                "skills": [],
                "agents": [],
                "commands": [],
            }).decode(),
        )
        # No skills/, agents/, or commands/ directories created

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0
        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) == 0

    def test_plugin_with_minimal_plugin_json_passes(self, tmp_path: Path) -> None:
        """Test plugin with only name field in plugin.json passes.

        Tests: Minimal plugin.json (no capability arrays)
        How: Write plugin.json with only name field, no capability arrays, validate
        Why: Capability arrays are optional; their absence should not cause errors
        """
        plugin_dir = _make_plugin(tmp_path, plugin_json_content=msgspec.json.encode({"name": "test-plugin"}).decode())
        # No directories created

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0

    @pytest.mark.parametrize(("capability_type", "file_name"), [("agents", "CLAUDE.md"), ("agents", "README.md")])
    def test_excluded_filenames_not_flagged_as_unregistered(
        self, tmp_path: Path, capability_type: str, file_name: str
    ) -> None:
        """Test CLAUDE.md and README.md in agents/ are excluded from registration checks.

        Tests: Filename exclusion in _find_actual_capabilities
        How: Create excluded filename in agents/, verify no PR001 warning
        Why: CLAUDE.md and README.md are documentation, not agent files
        """
        plugin_dir = _make_plugin(tmp_path)
        cap_dir = plugin_dir / capability_type
        cap_dir.mkdir()
        (cap_dir / file_name).write_text("# Documentation\n")

        validator = PluginRegistrationValidator()
        result = validator.validate(plugin_dir)

        pr001_warnings = [w for w in result.warnings if w.code == "PR001"]
        assert len(pr001_warnings) == 0
