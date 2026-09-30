"""Hook configuration validation and execute-bit repair."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from skilllint.models import ValidationIssue, ValidationResult
from skilllint.rules.hk_series import (
    _git_file_has_execute_bit,
    check_hk002,
    check_hk003,
    check_hk004,
    check_hk005,
    find_hook_plugin_dir,
    is_file_path_reference,
    iter_command_scripts,
    iter_hook_entries,
    load_hooks_object,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from skilllint.models import YamlValue


class HookValidator:
    """Validate hooks.json and repair HK005 execute-bit findings."""

    def validate(self, path: Path) -> ValidationResult:
        """Validate hook structure and referenced scripts.

        Args:
            path: Path to hooks.json.

        Returns:
            Result containing HK001-HK005 findings.
        """
        hooks_obj, errors = load_hooks_object(path)
        if hooks_obj is None:
            return ValidationResult(passed=False, errors=errors, warnings=[], info=[])

        warnings: list[ValidationIssue] = []
        errors.extend(check_hk002(hooks_obj))
        errors.extend(check_hk003(hooks_obj))
        self.validate_hook_script_references_in_hooks_dict(hooks_obj, path.parent, errors, warnings)
        return ValidationResult(passed=not errors, errors=errors, warnings=warnings, info=[])

    def can_fix(self) -> bool:
        """Return True; HK005 can be repaired with Git mode or chmod."""
        return True

    def fix(self, path: Path) -> list[str]:
        """Make existing non-executable hook scripts executable.

        Args:
            path: Path to hooks.json.

        Returns:
            Human-readable descriptions of applied repairs.
        """
        hooks_dict, _ = load_hooks_object(path)
        if hooks_dict is None:
            return []

        fixes: list[str] = []
        for command, resolved_path in iter_command_scripts(iter_hook_entries(hooks_dict), path.parent):
            if not resolved_path.exists():
                continue
            fix_desc = self._fix_execute_bit(resolved_path, command)
            if fix_desc:
                fixes.append(fix_desc)
        return fixes

    def _fix_execute_bit(self, resolved_path: Path, command: str) -> str | None:
        git_exec = _git_file_has_execute_bit(resolved_path)
        if git_exec is True:
            return None
        if git_exec is False:
            git_bin = shutil.which("git")
            if git_bin:
                try:
                    subprocess.run(
                        [git_bin, "update-index", "--chmod=+x", str(resolved_path)],
                        check=True,
                        capture_output=True,
                    )
                except (subprocess.CalledProcessError, OSError):
                    pass
                else:
                    return f"Made hook script executable: {command}"
            return None
        if not os.access(resolved_path, os.X_OK):
            try:
                current_mode = resolved_path.stat().st_mode
                resolved_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except OSError:
                pass
            else:
                return f"Made hook script executable: {command}"
        return None

    @staticmethod
    def _is_file_path_reference(command: str) -> bool:
        """Return whether a hook command looks like a file-path reference."""
        return is_file_path_reference(command)

    @staticmethod
    def _find_hook_plugin_dir(base_dir: Path) -> Path:
        """Return the plugin root used to resolve hook paths."""
        return find_hook_plugin_dir(base_dir)

    def _validate_command_script_references(
        self,
        hook_entries: Iterable[object],
        base_dir: Path,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ) -> None:
        """Append HK004/HK005 findings for referenced scripts."""
        errors.extend(check_hk004(hook_entries, base_dir))
        for issue in check_hk005(hook_entries, base_dir):
            (errors if issue.severity == "error" else warnings).append(issue)

    def validate_hook_script_references_in_hooks_dict(
        self,
        hooks_dict: Mapping[str, YamlValue],
        base_dir: Path,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ) -> None:
        """Append referenced-script findings for every hook entry."""
        for entry in iter_hook_entries(hooks_dict):
            self._validate_command_script_references([entry], base_dir, errors, warnings)


__all__ = ["HookValidator"]
