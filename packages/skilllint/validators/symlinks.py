"""Symlink validation and safe target repair."""

from __future__ import annotations

import contextlib
from pathlib import Path

from skilllint.models import ValidationResult
from skilllint.rules.sl_series import check_sl001, iter_symlinks


class SymlinkTargetValidator:
    r"""Validate and repair trailing whitespace in symlink targets."""

    def validate(self, path: Path) -> ValidationResult:
        """Validate symlink targets under a file or directory.

        Args:
            path: File or directory to inspect.

        Returns:
            Result containing SL001 errors.
        """
        errors = check_sl001(path)
        return ValidationResult(passed=not errors, errors=errors, warnings=[], info=[])

    def can_fix(self) -> bool:
        """Return True; verified dirty symlink targets can be rewritten safely."""
        return True

    def fix(self, path: Path) -> list[str]:
        """Strip trailing whitespace from verified symlink targets.

        Args:
            path: File or directory whose symlinks may be repaired.

        Returns:
            Human-readable descriptions of applied repairs.
        """
        fixes: list[str] = []
        for symlink_path in iter_symlinks(path):
            try:
                raw_target = str(Path(symlink_path).readlink())
            except OSError:
                continue
            if raw_target == raw_target.rstrip():
                continue

            clean_target = raw_target.rstrip()
            resolved = (symlink_path.parent / clean_target).resolve()
            if not resolved.exists():
                continue

            try:
                Path(symlink_path).unlink()
                Path(symlink_path).symlink_to(clean_target)
                fixes.append(
                    f"Fixed symlink {symlink_path}: stripped trailing whitespace from target "
                    f"({raw_target!r} -> {clean_target!r})"
                )
            except OSError:
                with contextlib.suppress(OSError):
                    Path(symlink_path).symlink_to(raw_target)
        return fixes


__all__ = ["SymlinkTargetValidator"]
