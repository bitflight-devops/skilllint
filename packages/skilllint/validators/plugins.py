"""Plugin-tree validation and Claude CLI integration.

This module owns validators whose responsibility is the plugin as an installed
or registered unit, including LK004 copied-plugin link checks, registration
cross-checks, and optional `claude plugin validate` subprocess integration.
Rule truth remains in `rules/`; scan and ignore primitives remain in
`scan_runtime` and `policy`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import msgspec.json

from skilllint.models import ValidationIssue, ValidationResult
from skilllint.policy import IgnoreConfig, _is_suppressed, _resolve_ignore_config
from skilllint.rule_registry import rule_reference
from skilllint.rules.lk_series import check_lk004
from skilllint.rules.pl_series import (
    _check_pl004_manifest_paths,
    check_pl001,
    check_pl002,
    check_pl003,
    check_pl004,
    check_pl005,
    check_pl006,
    claude_validation_failure_issue,
)
from skilllint.rules.pr_series import check_pr001, check_pr002, check_pr005
from skilllint.scan_runtime import (
    _build_gitignore_set,
    _find_anchor_dir,
    _glob_excluding,
    _is_ignored,
    _load_ignore_patterns,
    find_marketplace_dir,
    find_plugin_dir,
)

FM002 = "FM002"
PL001 = "PL001"
PL002 = "PL002"
PL003 = "PL003"
PL004 = "PL004"
PL005 = "PL005"
PL006 = "PL006"

def _run_claude_plugin_validate(claude_path: str, plugin_dir: Path) -> subprocess.CompletedProcess[str]:
    subprocess_env = {key: value for key, value in os.environ.items() if key != "CLAUDECODE"}
    return subprocess.run(
        [claude_path, "plugin", "validate", str(plugin_dir)],
        capture_output=True,
        text=True,
        check=False,
        env=subprocess_env,
    )


def _git_bash_path() -> str | None:
    """Resolve path to bash.exe for CLAUDE_CODE_GIT_BASH_PATH.

    Claude Code on Windows requires git-bash. Tries:
    1. shutil.which("git-bash") — if found, use sibling bin/bash.exe
    2. On Windows: LOCALAPPDATA/Programs/Git — check git-bash.exe exists, use bin/bash.exe

    If resolved, sets os.environ["CLAUDE_CODE_GIT_BASH_PATH"] and returns the path.

    Returns:
        Resolved path to bash.exe, or None if not found
    """
    # Already set
    existing = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH", "").strip()
    if existing and Path(existing).is_file():
        return existing

    # Try PATH for git-bash only (not generic bash — claude requires Git Bash)
    found = shutil.which("git-bash")
    if found:
        path = Path(found).resolve()
        if path.is_file() and path.name.lower() == "git-bash.exe":
            bash_exe = path.parent / "bin" / "bash.exe"
            if bash_exe.is_file():
                resolved = str(bash_exe.resolve())
                os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = resolved
                return resolved
            # Shims may point elsewhere; if path is git-bash.exe, try parent/bin
            # Already tried above; fall through to Windows fallback if no bin/bash

    # Windows fallback: AppData\Local\Programs\Git\git-bash.exe
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA", "").strip()
        if localappdata:
            base = Path(localappdata) / "Programs" / "Git"
            git_bash_exe = base / "git-bash.exe"
            if git_bash_exe.is_file():
                bash_exe = base / "bin" / "bash.exe"
                if bash_exe.is_file():
                    resolved = str(bash_exe.resolve())
                    os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = resolved
                    return resolved

    return None


def _should_skip_claude_validate() -> bool:
    """Detect if running in a context where claude CLI validation should be skipped.

    Skips validation when either:
    - CLAUDE_CODE_REMOTE=true (cloud-hosted Claude Code sessions)
    - CLAUDECODE is set (nested Claude Code session detected by Anthropic)

    Returns:
        True if claude plugin validate should be skipped, False otherwise
    """
    # Check for remote cloud session
    if os.environ.get("CLAUDE_CODE_REMOTE", "").lower() == "true":
        return True

    # Check for nested Claude Code session (CLAUDECODE env var set by Anthropic)
    return bool(os.environ.get("CLAUDECODE"))


# ============================================================================
# PLUGIN LINK ESCAPE VALIDATOR
# ============================================================================


# Manifests that mark a plugin root whose installer copies only the plugin
# directory (LK004). Each path is a provenance-registry.json claim:
# Claude Code saves its manifest at .claude-plugin/plugin.json
# (code.claude.com/docs/en/plugins-reference.md#manifest-file); a Codex
# overlay keeps its plugin.json inside .codex-plugin/
# (developers.openai.com/codex/plugins/build.md#plugin-structure).
CLAUDE_PLUGIN_MANIFEST = ".claude-plugin/plugin.json"
CODEX_PLUGIN_MANIFEST = ".codex-plugin/plugin.json"
_LINK_SCOPE_PLUGIN_MARKERS: tuple[str, ...] = (CLAUDE_PLUGIN_MANIFEST, CODEX_PLUGIN_MANIFEST)
# Plugin directories an agent reads from the installed copy. READMEs, CLAUDE.md,
# AGENTS.md and docs/ are read in the source repository, so LK004 skips them.
LK004_SCOPE_DIRS: tuple[str, ...] = ("agents", "skills", "commands")


def find_link_scope_plugin_dir(path: Path) -> Path | None:
    """Return the nearest plugin root above *path* for LK004, or None.

    Args:
        path: Path to start searching from (file or directory).

    Returns:
        The deepest ancestor holding any of ``_LINK_SCOPE_PLUGIN_MARKERS``.
    """
    roots = [root for marker in _LINK_SCOPE_PLUGIN_MARKERS if (root := _find_anchor_dir(path, marker)) is not None]
    return max(roots, key=lambda root: len(root.parts)) if roots else None


class PluginLinkEscapeValidator:
    """Reports markdown links that may dangle once a plugin is installed (LK004).

    Detection lives in ``skilllint.rules.lk_series``; this class walks the
    ``*.md`` files under the plugin's ``agents/``, ``skills/`` and
    ``commands/`` directories (the files an agent reads from an installed
    copy) and packages the rule results into a ``ValidationResult``. The walk
    skips files excluded by ``.pluginvalidatorignore`` or git, and drops an
    observation that a path-scoped ignore config suppresses for its own
    Markdown file. The plugin root is a Claude Code
    (``.claude-plugin/plugin.json``) or Codex (``.codex-plugin/plugin.json``)
    plugin.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate every markdown file in the plugin containing *path*.

        Args:
            path: Path to the plugin directory or a file within it.

        Returns:
            ValidationResult that always passes; LK004 observations are
            ``info`` issues, and read failures are errors.
        """
        errors: list[ValidationIssue] = []
        info: list[ValidationIssue] = []
        plugin_dir = find_link_scope_plugin_dir(path)
        if plugin_dir is not None:
            md_files = sorted(
                md_file for part in LK004_SCOPE_DIRS for md_file in _glob_excluding(plugin_dir / part, "**/*.md")
            )
            ignore_patterns = _load_ignore_patterns()
            gitignored = _build_gitignore_set(md_files, plugin_dir)
            ignore_cache: dict[str, tuple[IgnoreConfig, Path | None]] = {}
            for md_file in md_files:
                if str(md_file.resolve()) in gitignored or (ignore_patterns and _is_ignored(md_file, ignore_patterns)):
                    continue
                try:
                    content = md_file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as e:
                    errors.append(
                        ValidationIssue(
                            field=md_file.relative_to(plugin_dir).as_posix(),
                            severity="error",
                            message=f"Could not read file: {e}",
                            code=FM002,
                            docs_url=rule_reference(FM002),
                        )
                    )
                    continue
                ignore_config, config_root = _resolve_ignore_config(md_file, ignore_cache)
                info.extend(
                    issue
                    for issue in check_lk004(content, md_file, plugin_dir)
                    if config_root is None or not _is_suppressed(ignore_config, md_file, config_root, str(issue.code))
                )
        return ValidationResult(passed=not errors, errors=errors, warnings=[], info=info)

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (moving a link target into the plugin is a manual decision).
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix escaping links (not supported).

        Args:
            path: Path to file or directory.

        Raises:
            NotImplementedError: Escaping links require manual fixes.
        """
        raise NotImplementedError("Links that escape the plugin root require moving the target or editing the link.")


# ============================================================================
# PLUGIN REGISTRATION VALIDATOR
# ============================================================================


class PluginRegistrationValidator:
    """Validates capability registration against plugin.json.

    Checks that replaced default components are registered and declared paths
    exist. Detection lives in ``skilllint.rules.pr_series``.

    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate registration and metadata for the plugin containing path.

        Args:
            path: Path to a file or directory within the plugin.

        Returns:
            ValidationResult with registration and metadata issues.
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        plugin_dir = find_plugin_dir(path)
        if plugin_dir is None:
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        plugin_json_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if not plugin_json_path.exists():
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        try:
            plugin_config = msgspec.json.decode(plugin_json_path.read_bytes())
        except msgspec.DecodeError as error:
            errors.append(
                ValidationIssue(
                    field="plugin.json",
                    severity="error",
                    message=f"Invalid JSON: {error}",
                    code=PL002,
                    docs_url=rule_reference(PL002),
                    suggestion="Fix JSON syntax errors",
                )
            )
            return ValidationResult(passed=False, errors=errors, warnings=warnings, info=info)

        if not isinstance(plugin_config, dict):
            errors.append(
                ValidationIssue(
                    field="plugin.json",
                    severity="error",
                    message="Invalid JSON: plugin.json top level must be an object",
                    code=PL002,
                    docs_url=rule_reference(PL002),
                    suggestion="Use a JSON object for plugin.json",
                )
            )
            return ValidationResult(passed=False, errors=errors, warnings=warnings, info=info)

        # Registration checks — detection lives in skilllint.rules.pr_series.
        errors.extend(_check_pl004_manifest_paths(plugin_config, plugin_dir))
        warnings.extend(check_pr001(plugin_config, plugin_dir))
        errors.extend(check_pr002(plugin_config, plugin_dir))
        info.extend(check_pr005(plugin_config, plugin_dir))

        return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings, info=info)

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (registration issues require manual plugin.json edits).
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix registration issues (not supported).

        Args:
            path: Path to file or directory.

        Raises:
            NotImplementedError: Registration issues require manual fixes.
        """
        raise NotImplementedError("Plugin registration issues require manual edits to plugin.json.")


# ============================================================================
# PLUGIN STRUCTURE VALIDATOR (CLAUDE CLI INTEGRATION)
# ============================================================================


class PluginStructureValidator:
    """Validates plugin structure using claude CLI.

    Integrates with external `claude plugin validate` CLI command for
    plugin.json validation. Gracefully handles cases where claude CLI
    is not available by skipping validation.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate plugin structure using claude CLI.

        Args:
            path: Path to plugin directory or file within plugin

        Returns:
            ValidationResult with errors from claude CLI or info if skipped
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        # Find plugin directory (contains .claude-plugin/plugin.json), falling
        # back to a marketplace-only root (contains .claude-plugin/
        # marketplace.json but no plugin.json anywhere in its ancestry) so
        # PL006 is reachable there too (skilllint#118). Plugin anchor is
        # tried first: a nested plugin root must resolve to itself, not to
        # an ancestor's marketplace.json.
        plugin_dir = find_plugin_dir(path) or find_marketplace_dir(path)
        if plugin_dir is None:
            # Neither a plugin nor a marketplace directory - skip validation
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        # Validate plugin.json JSON syntax locally before delegating to claude CLI.
        # Catches encoding/line-ending issues that may cause claude to fail inconsistently.
        plugin_json_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if plugin_json_path.exists():
            json_issues = check_pl002(plugin_json_path)
            if json_issues:
                errors.extend(json_issues)
                return ValidationResult(passed=False, errors=errors, warnings=warnings, info=info)

        mp_layout = check_pl006(plugin_dir)
        if mp_layout:
            for issue in mp_layout:
                (errors if issue.severity == "error" else warnings).append(issue)
            return ValidationResult(passed=not errors, errors=errors, warnings=warnings, info=info)

        # Skip claude plugin validate when running inside a Claude Code session
        # (nested CLI invocations are blocked by Anthropic safety measure).
        if _should_skip_claude_validate():
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message="Skipping claude plugin validate (nested CLI sessions not supported)",
                    code=PL001,
                    docs_url=rule_reference(PL001),
                )
            )
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        # Check if claude CLI is available and get full path
        claude_path = self._get_claude_path()
        if claude_path is None:
            # Claude not available - skip with info message
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message="Claude CLI not available, skipping plugin structure validation",
                    code=PL001,
                    docs_url=rule_reference(PL001),
                    suggestion="Install Claude Code to enable plugin validation",
                )
            )
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        # On Windows, ensure CLAUDE_CODE_GIT_BASH_PATH is set if git-bash can be found
        _git_bash_path()

        try:
            result = _run_claude_plugin_validate(claude_path, plugin_dir)

            # Parse output for errors
            if result.returncode != 0:
                # Validation failed - parse errors from output
                self._parse_claude_errors(result.stdout, result.stderr, errors, warnings, info)

        except subprocess.TimeoutExpired as error:
            errors.append(
                ValidationIssue(
                    field="(plugin-validation)",
                    severity="error",
                    message=f"Claude plugin validation timed out after {error.timeout} seconds",
                    code=PL002,
                    docs_url=rule_reference(PL002),
                )
            )
        except FileNotFoundError:
            # Claude CLI not found (should be caught by _is_claude_available)
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message="Claude CLI not found in PATH",
                    code=PL001,
                    docs_url=rule_reference(PL001),
                    suggestion="Install Claude Code to enable plugin validation",
                )
            )
        except OSError as e:
            # Subprocess failed to run (permissions, env, etc.) — skip, do not fail
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message=f"Claude CLI could not run; skipping plugin structure validation: {e}",
                    code=PL001,
                    docs_url=rule_reference(PL001),
                )
            )

        # Pass if no errors (warnings/info don't fail validation)
        passed = len(errors) == 0
        return ValidationResult(passed=passed, errors=errors, warnings=warnings, info=info)

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False. A relocation auto-fix once moved marketplace.json root keys
            into ``metadata``; it silently rewrote files that already carried
            documented root-level ``description``/``version`` fields and was
            removed rather than repaired (skilllint#114).
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix marketplace.json layout issues (not supported).

        Args:
            path: Path to plugin directory or file within plugin

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: PL006 findings must be corrected by hand; see
                ``can_fix`` for why the relocation auto-fix was removed.
        """
        raise NotImplementedError(
            "marketplace.json layout issues (PL006) have no auto-fix. An earlier "
            "relocation fix silently rewrote valid files and was removed (skilllint#114)."
        )

    def _get_claude_path(self) -> str | None:
        """Get full path to claude CLI if available.

        Returns:
            Full path to claude executable, or None if not found
        """
        return shutil.which("claude")

    def _is_claude_startup_failure(self, output: str) -> bool:
        """Return True if output indicates claude failed to start (env/runtime), not validation.

        We must not fail validation when claude cannot run (e.g. git-bash not found on
        Windows). Only fail when claude ran and reported plugin structure errors.
        """
        startup_patterns = (r"requires git-bash", r"CLAUDE_CODE_GIT_BASH_PATH", r"not in PATH")
        combined = output.lower()
        return any(re.search(p, combined, re.IGNORECASE) for p in startup_patterns)

    def _parse_claude_errors(
        self,
        stdout: str,
        stderr: str,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
        info: list[ValidationIssue],
    ) -> None:
        """Parse claude CLI output for validation errors.

        Args:
            stdout: Standard output from claude CLI
            stderr: Standard error from claude CLI
            errors: List to append error issues to
            warnings: List to append warning issues to
            info: List to append info issues to
        """
        # Combine stdout and stderr for parsing
        output = stdout + "\n" + stderr

        # If claude failed to start (env/runtime), skip — do not fail validation
        if self._is_claude_startup_failure(output):
            detail = (stdout.strip() + "\n" + stderr.strip())[:300] or "(no output)"
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message="Claude CLI could not start; skipping plugin structure validation",
                    code=PL001,
                    docs_url=rule_reference(PL001),
                    suggestion=detail,
                )
            )
            return

        # Map claude CLI output to error codes — each rule owns its own pattern.
        errors.extend(check_pl001(output))
        errors.extend(check_pl002(claude_output=output))
        errors.extend(check_pl003(output))
        errors.extend(check_pl004(output))
        errors.extend(check_pl005(output))

        # If no specific error pattern matched but validation failed, add generic error
        # Include actual CLI output for diagnosis (truncate to avoid huge messages)
        if not errors:
            issue = claude_validation_failure_issue(stdout, stderr)
            (errors if issue.severity == "error" else warnings).append(issue)


def is_claude_available() -> bool:
    """Check if claude CLI is available in PATH.

    Uses shutil.which() to safely detect claude CLI without shell execution.
    This function is used by validators to determine if Claude CLI-based
    validation is possible.

    Security: Uses shutil.which() to get full command path, no shell=True.

    Returns:
        True if claude CLI found in PATH, False otherwise
    """
    return shutil.which("claude") is not None


def validate_with_claude(plugin_dir: Path) -> tuple[bool, str]:
    """Run claude plugin validate if available.

    Executes claude CLI validation on a plugin directory. Gracefully handles
    cases where claude CLI is not available by returning success with skip message.

    Security requirements:
    - NEVER uses shell=True (command injection risk)
    - Passes command as list: [cmd_path, arg1, arg2]
    - Gets full command path via shutil.which()

    Args:
        plugin_dir: Path to plugin directory containing .claude-plugin/plugin.json

    Returns:
        Tuple of (success, output):
        - If claude not available: (True, "skipped")
        - If not a plugin directory: (True, "skipped")
        - If validation passes: (True, stdout)
        - If validation fails: (False, stderr + stdout)

    Raises:
        Never raises - returns (False, error_message) on failure
    """
    # Check if claude CLI is available
    claude_path = shutil.which("claude")
    if claude_path is None:
        return True, "claude CLI not available (skipped)"

    # Check if this is a plugin directory
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    if not plugin_json.exists():
        return True, "Not a plugin directory (skipped)"

    try:
        result = _run_claude_plugin_validate(claude_path, plugin_dir)
    except subprocess.TimeoutExpired as error:
        return (False, f"Claude plugin validation timed out after {error.timeout} seconds")
    except (FileNotFoundError, OSError) as e:
        # FileNotFoundError: Claude CLI not found (should be caught by shutil.which)
        # OSError: Other subprocess errors (permission denied, etc.)
        is_not_found = isinstance(e, FileNotFoundError)
        message = (
            "Claude CLI not found in PATH (skipped)" if is_not_found else f"Failed to run claude plugin validate: {e}"
        )
        # Not found is a skip (success), other OS errors are failures
        return is_not_found, message
    else:
        # Return success if validation passed, failure with details otherwise
        success = result.returncode == 0
        output = result.stdout if success else result.stderr + "\n" + result.stdout
        return success, output

__all__ = [
    "CLAUDE_PLUGIN_MANIFEST",
    "CODEX_PLUGIN_MANIFEST",
    "LK004_SCOPE_DIRS",
    "PluginLinkEscapeValidator",
    "PluginRegistrationValidator",
    "PluginStructureValidator",
    "_git_bash_path",
    "_run_claude_plugin_validate",
    "_should_skip_claude_validate",
    "find_link_scope_plugin_dir",
    "is_claude_available",
    "validate_with_claude",
]
