"""SL-series symlink validation rules (SL001).

SL001 detection lives here. ``SymlinkTargetValidator`` in
``plugin_validator.py`` is a thin wrapper that calls ``check_sl001`` and
packages the result; it retains the auto-fix, which mutates the filesystem
and is a validator concern rather than a rule concern.

Detection needs filesystem access, not frontmatter, so ``check_sl001`` takes
the path it inspects.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | SL001 | Symlink target has trailing whitespace/newlines           | error     |
    +-------+-----------------------------------------------------------+-----------+

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from skilllint.rule_registry import _make_issue, skilllint_rule

if TYPE_CHECKING:
    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------


def iter_symlinks(path: Path) -> list[Path]:
    """Return every symlink at or under *path*.

    When *path* is itself a symlink, returns ``[path]``. When *path* is a
    directory, returns all symlinks found by ``os.walk``, which does not
    follow symlinks by default.

    Shared with ``SymlinkTargetValidator.fix``, so detection and repair always
    agree on which symlinks are in scope.

    Args:
        path: Starting path to search for symlinks.

    Returns:
        List of symlink paths found.
    """
    symlinks: list[Path] = []

    if path.is_symlink():
        symlinks.append(path)
        return symlinks

    if path.is_dir():
        for root, dirs, files in os.walk(path, followlinks=False):
            root_path = Path(root)
            for name in dirs + files:
                candidate = root_path / name
                if candidate.is_symlink():
                    symlinks.append(candidate)

    return symlinks


# ---------------------------------------------------------------------------
# SL001 — Symlink target has trailing whitespace/newlines
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SL001",
    severity="error",
    category="symlink",
    platforms=["agentskills"],
    # No authority: no vendor doc addresses malformed symlink targets. A
    # trailing-whitespace/newline target is skilllint's own filesystem
    # robustness check, not a claim traceable to an upstream spec.
)
def check_sl001(path: Path) -> list[ValidationIssue]:
    r"""## SL001 — Symlink target has trailing whitespace or newlines

    A symlink within the validated path has a target string that contains
    trailing whitespace or newline characters.  For example,
    ``os.readlink()`` may return ``'../../python3-development/skills/uv\\n'``
    when the symlink was created with a newline-terminated target.

    Such symlinks cause ``Path.resolve()`` and ``is_file()``/``is_dir()`` to
    fail silently or raise unexpected errors, producing false-positive
    failures in other validators that depend on resolved paths.

    **Source:** ``SymlinkTargetValidator.validate`` in
    ``plugin_validator.py`` — reads symlink targets via ``Path.readlink()``,
    compares the raw target string against its ``rstrip()`` form, and emits
    this rule for any mismatch.

    **Fix:** Strip trailing whitespace from the symlink target and recreate
    the symlink.  Run ``skilllint check --fix`` to apply the fix
    automatically, or repair manually:

    ```bash
    python3 -c "
    import os
    p = 'path/to/symlink'
    t = os.readlink(p).rstrip()
    os.remove(p)
    os.symlink(t, p)
    "
    ```

    The auto-fix is only applied when the cleaned target resolves to an
    existing path.  Symlinks whose cleaned target does not exist are left
    untouched and reported as unfixable.

    Args:
        path: File or directory to inspect. A file that is itself a symlink is
            checked directly; a directory is scanned recursively.

    Returns:
        One issue per symlink whose target has trailing whitespace; empty when
        every symlink target is clean or the path contains no symlinks.

    <!-- examples: SL001 -->
    """
    issues: list[ValidationIssue] = []

    for symlink_path in iter_symlinks(path):
        try:
            raw_target = str(Path(symlink_path).readlink())
        except OSError:
            continue

        if raw_target != raw_target.rstrip():
            clean_target = raw_target.rstrip()
            issues.append(
                _make_issue(
                    field=str(symlink_path),
                    severity="error",
                    message=(
                        f"Symlink target has trailing whitespace: "
                        f"{symlink_path!s} -> {raw_target!r} "
                        f"(should be {clean_target!r})"
                    ),
                    code="SL001",
                    suggestion=(
                        "Run with --fix to strip trailing whitespace and recreate the symlink, "
                        'or run: python3 -c "'
                        f"import os; p='{symlink_path}'; t=os.readlink(p).rstrip(); "
                        'os.remove(p); os.symlink(t, p)"'
                    ),
                )
            )

    return issues


__all__ = ["check_sl001", "iter_symlinks"]
