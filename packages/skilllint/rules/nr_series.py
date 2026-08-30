"""NR-series namespace reference validation rules (NR001-NR002).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

NR001 and NR002 are emitted by ``NamespaceReferenceValidator`` in
``plugin_validator.py``.  Detection requires filesystem access (reading file
content, resolving plugin directories via ``plugin.json``, and checking whether
referenced skills, agents, and commands exist on disk).  None of that
information is available from frontmatter alone, so the validator functions
registered here are **registration-only stubs** — they exist to make rule
metadata available via ``RULE_REGISTRY`` (and therefore via
``skilllint rule NRxxx``) without duplicating the detection logic that belongs
in the filesystem-owning ``NamespaceReferenceValidator`` class.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | NR001 | Namespace reference target does not exist                 | error     |
    | NR002 | Namespace reference points outside plugin directory       | error     |
    +-------+-----------------------------------------------------------+-----------+

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skilllint.rule_registry import rule_reference, skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

# NR002 authority: code.claude.com/docs/en/plugins-reference, "Path traversal
# limitations" section. Verified via `skilllint docs fetch` — the cached page
# states verbatim: "Claude Code doesn't let a plugin reference files outside
# its own directory. It rejects a component path that resolves outside the
# plugin root, such as `../shared-utils`...". The same page's "plugin init"
# reference defines `<name>` as becoming "the skill namespace and the
# directory name under `~/.claude/skills/`, so it cannot contain spaces or
# path separators" — the basis for rejecting `/` and `\` in reference
# components. (Previously this rule cited agentskills.io/specification.md,
# which says nothing about traversal, boundaries, escaping, or symlinks —
# verified via `grep -ci` returning 0 for those terms against the cached spec.)
_NR002_PATH_TRAVERSAL_URL = "https://code.claude.com/docs/en/plugins-reference.md#path-traversal-limitations"


def _docs_url(code: str) -> str:
    """Return the documentation URL for an NR rule code.

    Args:
        code: Rule code string (e.g., "NR001").

    Returns:
        Full URL with anchor for the error code documentation.
    """
    return rule_reference(code)


# ---------------------------------------------------------------------------
# NR001 — Namespace reference target does not exist
# ---------------------------------------------------------------------------


@skilllint_rule(
    "NR001",
    severity="error",
    category="namespace-reference",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_nr001(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## NR001 — Namespace reference target does not exist

    A namespace-qualified reference in the file body points to a skill, agent,
    or command that cannot be resolved on the filesystem.  This rule fires
    when any of the following patterns cannot be resolved:

    - ``Skill(command: "plugin:skill-name")``
    - ``Skill(skill="plugin:skill-name")``
    - ``Task(agent="plugin:agent-name")``
    - ``@plugin:agent-name`` (prose agent references)
    - ``/plugin:skill-name`` (slash command references)

    Resolution fails when:

    - The plugin directory corresponding to the namespace prefix does not
      exist under the plugins root (no directory whose ``plugin.json`` declares
      ``"name": "<prefix>"``).
    - The referenced skill, agent, or command file cannot be found within
      the resolved plugin directory.
    - The file cannot be read at all (I/O error).

    **Source:** ``NamespaceReferenceValidator.validate`` in
    ``plugin_validator.py`` — reads file content, resolves plugin directories
    via ``plugin.json`` name fields, and checks for matching files.

    **Fix:** Ensure the referenced target exists at the expected path.  For
    a skill reference ``plugin:my-skill``, create the skill file at one of:

    ```
    plugins / plugin / skills / my - skill / SKILL.md
    plugins / plugin / skills / {category} / my - skill / SKILL.md
    ```

    Or correct the namespace prefix to match an existing plugin directory.

    Returns:
        Always an empty list.  NR001 is emitted by
        ``NamespaceReferenceValidator`` in ``plugin_validator.py`` after
        reading file content and resolving references against the filesystem;
        this function exists for rule metadata registration only.

    <!-- examples: NR001 -->
    """
    # Detection requires reading file content and resolving plugin directories
    # and skill/agent/command paths on the filesystem.
    # Owned by NamespaceReferenceValidator in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# NR002 — Namespace reference points outside plugin directory
# ---------------------------------------------------------------------------


@skilllint_rule(
    "NR002",
    severity="error",
    category="namespace-reference",
    platforms=["agentskills"],
    authority={"origin": "code.claude.com", "reference": _NR002_PATH_TRAVERSAL_URL},
)
def check_nr002(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    r"""## NR002 — Namespace reference points outside plugin directory

    A namespace reference's plugin prefix or target name contains a
    path-traversal sequence (``..``) or a path separator (``/`` or ``\\``),
    which would cause the resolved file path to escape the plugin directory
    that owns the reference.

    **Source (`..` traversal):** ``code.claude.com/docs/en/plugins-reference``
    — "Path traversal limitations": "Claude Code doesn't let a plugin
    reference files outside its own directory. It rejects a component path
    that resolves outside the plugin root, such as `../shared-utils`...".
    See https://code.claude.com/docs/en/plugins-reference.md#path-traversal-limitations

    **Source (`/` and `\\` separators):** the same doc's ``plugin init``
    reference defines a plugin's ``<name>``: "Becomes the skill namespace
    and the directory name under `~/.claude/skills/`, so it cannot contain
    spaces or path separators." See
    https://code.claude.com/docs/en/plugins-reference.md#plugin-init

    **Source (detection):**
    ``NamespaceReferenceValidator._check_nr002_traversal`` in
    ``plugin_validator.py`` — rejects namespace prefix/target components
    containing ``..``, ``/``, or ``\\``.

    **Fix:** Remove any path-traversal segments or path separators from
    reference names.  References must resolve to files that live inside the
    plugin directory they belong to:

    ```yaml
    # Problematic (traverses outside the plugin boundary)
    # Skill(skill="plugin:../other-plugin/skill-name")

    # Correct (stays within the declared plugin)
    # Skill(skill="other-plugin:skill-name")
    ```

    Use the correct namespace prefix that maps to the plugin directory
    where the target file actually lives.

    Returns:
        Always an empty list.  NR002 is emitted by
        ``NamespaceReferenceValidator`` in ``plugin_validator.py`` after
        resolving the canonical path of a referenced file and comparing it
        against the plugin directory boundary; this function exists for rule
        metadata registration only.

    <!-- examples: NR002 -->
    """
    # Detection requires resolving canonical filesystem paths and checking
    # that the resolved path remains within the plugin directory boundary.
    # Owned by NamespaceReferenceValidator in plugin_validator.py.
    return []


__all__ = ["check_nr001", "check_nr002"]
