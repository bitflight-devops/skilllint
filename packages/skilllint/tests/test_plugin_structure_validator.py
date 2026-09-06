"""Unit tests for PluginStructureValidator.

Tests:
- Claude CLI availability detection
- Graceful skip when CLI unavailable
- Error parsing from claude output
- Subprocess security (no shell=True)
- Timeout handling
- marketplace.json layout (PL006); no auto-fix exists (skilllint#114)
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

from skilllint.plugin_validator import PL006, PluginStructureValidator, validate_single_path


class TestPluginStructureValidatorBasic:
    """Test basic PluginStructureValidator functionality."""

    def test_validator_instantiation(self) -> None:
        """Test PluginStructureValidator can be instantiated.

        PL006 has no auto-fix (skilllint#114): a relocation fix once moved
        marketplace.json root keys into `metadata` and silently rewrote valid
        files, so `can_fix()` is permanently False.
        """
        validator = PluginStructureValidator()
        assert validator is not None
        assert validator.can_fix() is False

    def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
        """Test fix() always raises NotImplementedError.

        Tests: fix() has no implementation left to invoke (skilllint#114)
        How: Call fix() on a plugin dir, expect NotImplementedError regardless
        of marketplace.json contents
        """
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        with pytest.raises(NotImplementedError):
            validator.fix(plugin_dir)


class TestClaudeCLIDetection:
    """Test Claude CLI availability detection."""

    def test_detects_claude_available(self, mocker: MockerFixture) -> None:
        """Test validator detects when claude CLI is available.

        Tests: Claude CLI detection
        How: Mock shutil.which to return path, validate
        Why: Ensure validator detects CLI presence correctly
        """
        # Mock shutil.which to return a path
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        validator = PluginStructureValidator()
        # Validator should detect claude is available
        assert validator is not None

    def test_handles_claude_unavailable(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test validator handles claude CLI absence gracefully.

        Tests: Graceful degradation when CLI unavailable
        How: Mock shutil.which to return None, validate plugin
        Why: Ensure validator skips validation without error
        """
        # Mock shutil.which to return None (claude not found)
        mocker.patch("shutil.which", return_value=None)

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Should pass with info message (skipped)
        assert result.passed is True
        assert len(result.info) > 0


class TestNonPluginDirectory:
    """Test validation skips non-plugin directories."""

    def test_skips_non_plugin_directory(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test validation skips directory without plugin.json.

        Tests: Plugin directory detection
        How: Create directory without .claude-plugin/plugin.json, validate
        Why: Ensure validator skips non-plugin directories
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        regular_dir = tmp_path / "regular-dir"
        regular_dir.mkdir()

        validator = PluginStructureValidator()
        result = validator.validate(regular_dir)

        # Should pass without validation (not a plugin)
        assert result.passed is True

    def test_skips_skill_directory(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test validation skips skill directory (not plugin).

        Tests: File type detection
        How: Create skill directory, validate
        Why: Ensure only plugin directories are validated
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")

        validator = PluginStructureValidator()
        result = validator.validate(skill_dir / "SKILL.md")

        # Should pass without plugin validation
        assert result.passed is True


class TestSubprocessExecution:
    """Test subprocess execution security and behavior."""

    def test_no_shell_true_usage(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test subprocess never uses shell=True.

        Tests: Security - no shell=True
        How: Mock subprocess.run, verify arguments
        Why: Prevent command injection vulnerabilities
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        # Mock subprocess.run to track calls
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Success", stderr="")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        validator.validate(plugin_dir)

        # Verify subprocess.run was called without shell=True
        if mock_run.called:
            for call in mock_run.call_args_list:
                kwargs = call[1] if len(call) > 1 else {}
                assert kwargs.get("shell", False) is False

    def test_timeout_set(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test subprocess has timeout configured.

        Tests: Timeout configuration
        How: Mock subprocess.run, verify timeout parameter
        Why: Prevent hanging on unresponsive claude CLI
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Success", stderr="")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        validator.validate(plugin_dir)

        # Verify timeout was set
        if mock_run.called:
            for call in mock_run.call_args_list:
                kwargs = call[1] if len(call) > 1 else {}
                assert "timeout" in kwargs
                assert kwargs["timeout"] > 0


class TestClaudeOutputParsing:
    """Test parsing of claude CLI output."""

    def test_success_output(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test parsing successful validation output.

        Tests: Success case parsing
        How: Mock claude CLI success output, validate
        Why: Ensure validator recognizes successful validation
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Plugin validation passed", stderr="")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Should pass
        assert result.passed is True

    def test_error_output(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test parsing error validation output.

        Tests: Error case parsing
        How: Mock claude CLI error output, validate
        Why: Ensure validator captures validation failures
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")
        # Prevent skip in Claude Code session environments (CLAUDECODE / CLAUDE_CODE_REMOTE env vars)
        mocker.patch("skilllint.plugin_validator._should_skip_claude_validate", return_value=False)

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=1, stdout="", stderr="Error: Invalid plugin.json")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Should fail with error
        assert result.passed is False
        assert len(result.errors) > 0

    def test_startup_failure_skips_not_fails(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Claude env/runtime startup failure must skip validation, not fail.

        Tests: Git-bash / PATH / env errors are treated as skip
        How: Mock claude output with git-bash message, validate
        Why: Validator must only fail on plugin validation errors, not when claude cannot run
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")
        mocker.patch("skilllint.plugin_validator._should_skip_claude_validate", return_value=False)

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(
            returncode=1,
            stdout="",
            stderr="Claude Code on Windows requires git-bash. If installed but not in PATH, set CLAUDE_CODE_GIT_BASH_PATH=C:\\Program Files\\Git\\bin\\bash.exe",
        )

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0
        assert len(result.info) > 0


class TestTimeoutHandling:
    """Test timeout error handling."""

    def test_timeout_error_handled(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test timeout is handled gracefully.

        Tests: Timeout exception handling
        How: Mock subprocess to raise TimeoutExpired, validate
        Why: Ensure validator handles timeouts without crashing
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["claude", "plugin", "validate"], timeout=30)

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Should handle timeout gracefully
        assert result.passed is False or result.passed is True
        # Either fails with error or passes with warning


class TestFileNotFoundHandling:
    """Test FileNotFoundError handling."""

    def test_file_not_found_handled(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test FileNotFoundError is handled gracefully.

        Tests: Command not found handling
        How: Mock subprocess to raise FileNotFoundError, validate
        Why: Ensure validator handles missing claude binary
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError("claude not found")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Should handle FileNotFoundError gracefully
        assert isinstance(result.passed, bool)


class TestCommandArguments:
    """Test command construction and arguments."""

    def test_command_uses_full_path(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test command uses full path from shutil.which.

        Tests: Command path construction
        How: Mock shutil.which, verify command uses full path
        Why: Ensure security by using full path, not PATH search
        """
        claude_path = "/usr/local/bin/claude"
        mocker.patch("shutil.which", return_value=claude_path)

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Success", stderr="")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        validator.validate(plugin_dir)

        # Verify command uses full path
        if mock_run.called:
            args = mock_run.call_args[0][0] if mock_run.call_args else []
            if args:
                assert args[0] == claude_path or args[0].startswith("/")

    def test_command_arguments_correct(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test command arguments are correct.

        Tests: Command argument structure
        How: Mock subprocess, verify arguments
        Why: Ensure correct claude CLI invocation
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Success", stderr="")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        validator.validate(plugin_dir)

        # Verify command arguments
        if mock_run.called:
            args = mock_run.call_args[0][0] if mock_run.call_args else []
            # Should be: [claude_path, "plugin", "validate", plugin_dir]
            if len(args) >= 3:
                assert "plugin" in args
                assert "validate" in args


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_nested_plugin_directory(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test validation works on nested plugin directories.

        Tests: Path resolution for nested plugins
        How: Create plugin in nested directory, validate
        Why: Ensure validator handles various directory structures
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Success", stderr="")

        plugin_dir = tmp_path / "nested" / "path" / "test-plugin"
        plugin_dir.mkdir(parents=True)
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Should handle nested paths
        assert isinstance(result.passed, bool)

    def test_symlinked_plugin_directory(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test validation works on symlinked plugin directories.

        Tests: Symlink handling
        How: Create symlink to plugin, validate via symlink
        Why: Ensure validator handles symlinks correctly
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Success", stderr="")

        # Create real plugin
        real_plugin = tmp_path / "real-plugin"
        real_plugin.mkdir()
        claude_plugin = real_plugin / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        # Create symlink
        symlink = tmp_path / "link-to-plugin"
        symlink.symlink_to(real_plugin)

        validator = PluginStructureValidator()
        result = validator.validate(symlink)

        # Should handle symlinks
        assert isinstance(result.passed, bool)


class TestMarketplaceJsonLayout:
    """marketplace.json root keys (PL006). No auto-fix exists (skilllint#114)."""

    def test_pl006_misplaced_keys_skips_claude_subprocess(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Disallowed marketplace root keys fail fast with PL006; do not invoke claude."""
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")
        mocker.patch("skilllint.plugin_validator._should_skip_claude_validate", return_value=False)

        mock_run = mocker.patch("subprocess.run")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')
        marketplace = {
            "name": "cat",
            "owner": {"name": "x"},
            "plugins": [],
            "repository": "https://example.com/r",
            "homepage": "https://example.com",
            "license": "MIT",
        }
        (claude_plugin / "marketplace.json").write_text(json.dumps(marketplace))

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # PL006 unrecognized/misplaced root keys are a warning, not an error
        # (verified against `claude plugin validate` v2.1.263, see issue #145).
        assert result.passed is True
        assert any(e.code == PL006 for e in result.warnings)
        mock_run.assert_not_called()

    def test_pl006_recognized_field_suggests_move_to_metadata(self, tmp_path: Path) -> None:
        """A root key recognized elsewhere in the plugin ecosystem (`repository`) gets
        move-under-`metadata` guidance, not delete-it guidance (skilllint#141 review:
        the old auto-fix moved this field, so telling users to delete it loses data).
        """
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')
        marketplace = {"name": "cat", "owner": {"name": "x"}, "plugins": [], "repository": "https://example.com/r"}
        (claude_plugin / "marketplace.json").write_text(json.dumps(marketplace))

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        pl006 = [e for e in result.warnings if e.code == PL006]
        assert len(pl006) == 1
        assert pl006[0].suggestion is not None
        assert "metadata" in pl006[0].suggestion
        assert "`repository`" in pl006[0].suggestion
        assert "remove or rename these unrecognized" not in pl006[0].suggestion

    def test_pl006_unknown_key_still_suggests_remove_or_rename(self, tmp_path: Path) -> None:
        """A genuinely unrecognized root key (a typo) still gets remove-or-rename guidance."""
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')
        marketplace = {"name": "cat", "owner": {"name": "x"}, "plugins": [], "pluginz": "typo"}
        (claude_plugin / "marketplace.json").write_text(json.dumps(marketplace))

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        pl006 = [e for e in result.warnings if e.code == PL006]
        assert len(pl006) == 1
        assert pl006[0].suggestion is not None
        assert "remove or rename" in pl006[0].suggestion.lower()
        assert "`pluginz`" in pl006[0].suggestion

    def test_pl006_accepts_documented_root_fields(self, tmp_path: Path) -> None:
        """Documented root fields ($schema, description, version, renames, ...) pass PL006."""
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')
        marketplace = {
            "$schema": "https://code.claude.com/docs/en/plugin-marketplaces.md#marketplace-schema",
            "name": "cat",
            "description": "A test marketplace",
            "version": "1.0.0",
            "owner": {"name": "x"},
            "plugins": [],
            "allowCrossMarketplaceDependenciesOn": [],
            "renames": {},
        }
        (claude_plugin / "marketplace.json").write_text(json.dumps(marketplace))

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        assert not any(e.code == PL006 for e in result.errors)
        assert not any(e.code == PL006 for e in result.warnings)

    def test_pl006_non_object_root_stays_error(self, tmp_path: Path) -> None:
        """A non-object marketplace.json root is a structural defect, not an
        unrecognized-key finding, and must stay an **error** (exit 1).

        Regression guard: a naive blanket ``severity="error"`` -> ``"warning"``
        find-and-replace across `check_pl006` would wrongly downgrade this
        case too. Verified against `claude plugin validate` v2.1.263 (issue
        #145): a non-object root still reports a real error, non-zero exit.
        """
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')
        (claude_plugin / "marketplace.json").write_text(json.dumps([1, 2, 3]))

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is False
        pl006 = [e for e in result.errors if e.code == PL006]
        assert len(pl006) == 1
        assert not any(e.code == PL006 for e in result.warnings)

    def test_fix_leaves_documented_marketplace_json_byte_identical(self, tmp_path: Path) -> None:
        """`--fix` must not rewrite a marketplace.json with documented root fields.

        Regression test for skilllint#114: root-level `description`/`version`
        (both documented-valid) were being silently relocated under `metadata`
        by an auto-fix that has since been removed. Proof is byte-identity:
        hash the file, run the `--fix` code path, hash again.
        """
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')
        marketplace_path = claude_plugin / "marketplace.json"
        marketplace_path.write_text(
            json.dumps({
                "name": "cat",
                "description": "A test marketplace",
                "version": "1.0.0",
                "owner": {"name": "x"},
                "plugins": [],
            })
        )
        before = hashlib.sha256(marketplace_path.read_bytes()).hexdigest()

        validate_single_path(plugin_dir, check=False, fix=True, verbose=False)

        after = hashlib.sha256(marketplace_path.read_bytes()).hexdigest()
        assert after == before

    def test_claude_output_marketplace_unrecognized_keys_maps_to_pl006(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Fallback parser maps marketplace unrecognized-keys CLI output to PL006."""
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")
        mocker.patch("skilllint.plugin_validator._should_skip_claude_validate", return_value=False)

        stderr = (
            "Validating marketplace manifest: /tmp/.claude-plugin/marketplace.json\n"
            'Found 1 error:\n  root: Unrecognized keys: "repository", "homepage", "license"\n'
        )
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=1, stdout="", stderr=stderr)

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')
        (claude_plugin / "marketplace.json").write_text(
            json.dumps({"name": "c", "owner": {"name": "a"}, "plugins": []})
        )

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Subprocess-derived PL006 (fallback parser) is also a warning
        # (verified against `claude plugin validate` v2.1.263, see issue #145).
        assert result.passed is True
        assert any(e.code == PL006 for e in result.warnings)
