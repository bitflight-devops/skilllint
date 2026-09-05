"""PD-series progressive disclosure rules (PD001-PD003).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

PD001, PD002, and PD003 detection lives here.  ``ProgressiveDisclosureValidator``
in ``plugin_validator.py`` is a thin wrapper that calls the three rule functions
in order and packages their issues into a ``ValidationResult``; it retains
``can_fix``/``fix``, which are validator concerns rather than rule concerns.

Detection needs filesystem access, not frontmatter, so each rule takes only the
path it inspects.  Signatures across the rules package state the input the rule
actually reads rather than a uniform frontmatter triple.

Rule IDs and default severities:
    +-------+-----------------------------------------------+-----------+
    | ID    | Summary                                       | Severity  |
    +-------+-----------------------------------------------+-----------+
    | PD001 | No references/ directory found                | info      |
    | PD002 | No assets/ directory found                    | info      |
    | PD003 | No scripts/ directory found                   | info      |
    +-------+-----------------------------------------------+-----------+

Import note: ValidationIssue is deferred inside ``_make_issue`` to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skilllint.rule_registry import _make_issue, skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

# PD002 authority: agentskills.io/specification.md, "Progressive disclosure"
# section. Verified via `skilllint docs fetch` — the cached spec's `assets/`
# subsection states verbatim: "Contains static resources: Templates ...
# Images ... Data files ...". The spec documents `references/`, `scripts/`,
# and `assets/` as the three optional subdirectories; it never mentions an
# `examples/` directory.
_PD002_ASSETS_URL = "https://agentskills.io/specification.md#assets"


def _check_disclosure_dir(path: Path, dir_name: str, code: str) -> list[ValidationIssue]:
    """Report *code* when *dir_name* is missing from a skill directory.

    Shared by PD001-PD003 so the three rules cannot drift on how they locate
    the skill directory or decide a path is out of scope.

    Args:
        path: Skill directory, or a file inside it (a file resolves to its parent).
        dir_name: Progressive disclosure directory to look for.
        code: Rule code to emit when the directory is absent.

    Returns:
        A single info issue when the directory is missing; empty when it exists
        or when the resolved directory is not a skill directory (no SKILL.md).
    """
    skill_dir = path.parent if path.is_file() else path

    # Not a skill directory - skip validation
    if not (skill_dir / "SKILL.md").exists():
        return []

    if (skill_dir / dir_name).exists():
        # No info message needed when directory exists (only report missing directories)
        return []

    return [
        _make_issue(
            field="progressive-disclosure",
            severity="info",
            message=f"No {dir_name}/ directory found (consider adding for documentation)",
            code=code,
            suggestion=f"Create {dir_name}/ directory to organize additional content",
        )
    ]


# ---------------------------------------------------------------------------
# PD001 — No references/ directory found
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PD001",
    severity="info",
    category="progressive-disclosure",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_pd001(path: Path) -> list[ValidationIssue]:
    """## PD001 — No references/ directory found

    The skill directory does not contain a ``references/`` subdirectory.
    A ``references/`` directory provides supporting documentation, external
    links, and background material that readers can explore on demand without
    cluttering the main ``SKILL.md``.

    This is an informational notice, not an error.  Missing the directory does
    not prevent the skill from functioning; it is a recommendation for better
    content organisation.

    **Source:** ``ProgressiveDisclosureValidator`` in ``plugin_validator.py`` —
    calls this rule, which checks for the presence of ``references/`` under the skill directory.

    **Fix:** Create a ``references/`` directory and populate it with supporting
    documentation:

    ```
    my-skill/
      SKILL.md
      references/
        background.md
        external-links.md
    ```

    Args:
        path: Skill directory, or a file inside it (a file resolves to its
            parent directory).

    Returns:
        A single info issue when ``references/`` is missing; empty when it exists or
        when the resolved directory is not a skill directory.

    <!-- examples: PD001 -->
    """
    return _check_disclosure_dir(path, "references", "PD001")


# ---------------------------------------------------------------------------
# PD002 — No assets/ directory found
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PD002",
    severity="info",
    category="progressive-disclosure",
    platforms=["agentskills"],
    authority={"origin": "agentskills.io", "reference": _PD002_ASSETS_URL},
)
def check_pd002(path: Path) -> list[ValidationIssue]:
    """## PD002 — No assets/ directory found

    The skill directory does not contain an ``assets/`` subdirectory.
    An ``assets/`` directory holds static resources — templates (document
    templates, configuration templates), images (diagrams, examples), and
    data files (lookup tables, schemas) — that the skill's content can
    reference without embedding them in ``SKILL.md``.

    This is an informational notice, not an error.  Missing the directory does
    not prevent the skill from functioning; it is a recommendation for better
    content organisation.

    **Source:** `agentskills.io/specification.md` — the "Progressive
    disclosure" section documents ``assets/`` alongside ``references/`` and
    ``scripts/`` as the three optional subdirectories; verified via
    `skilllint docs fetch` against the cached spec, which describes
    ``assets/`` as containing "Templates ... Images ... Data files". See
    https://agentskills.io/specification.md#assets

    **Fix:** Create an ``assets/`` directory and populate it with static
    resources:

    ```
    my-skill/
      SKILL.md
      assets/
        template.docx
        diagram.png
    ```

    Args:
        path: Skill directory, or a file inside it (a file resolves to its
            parent directory).

    Returns:
        A single info issue when ``assets/`` is missing; empty when it exists or
        when the resolved directory is not a skill directory.

    <!-- examples: PD002 -->
    """
    return _check_disclosure_dir(path, "assets", "PD002")


# ---------------------------------------------------------------------------
# PD003 — No scripts/ directory found
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PD003",
    severity="info",
    category="progressive-disclosure",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_pd003(path: Path) -> list[ValidationIssue]:
    """## PD003 — No scripts/ directory found

    The skill directory does not contain a ``scripts/`` subdirectory.
    A ``scripts/`` directory holds helper scripts, automation utilities, and
    supporting code referenced or used by the skill.

    This is an informational notice, not an error.  Missing the directory does
    not prevent the skill from functioning; it is a recommendation for better
    content organisation.

    **Source:** ``ProgressiveDisclosureValidator`` in ``plugin_validator.py`` —
    calls this rule, which checks for the presence of ``scripts/`` under the skill directory.

    **Fix:** Create a ``scripts/`` directory and populate it with helper
    scripts:

    ```
    my-skill/
      SKILL.md
      scripts/
        setup.sh
        run-example.py
    ```

    Args:
        path: Skill directory, or a file inside it (a file resolves to its
            parent directory).

    Returns:
        A single info issue when ``scripts/`` is missing; empty when it exists or
        when the resolved directory is not a skill directory.

    <!-- examples: PD003 -->
    """
    return _check_disclosure_dir(path, "scripts", "PD003")


__all__ = ["check_pd001", "check_pd002", "check_pd003"]
