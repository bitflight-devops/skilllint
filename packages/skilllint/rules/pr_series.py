"""PR-series plugin registration rules (PR001-PR005).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

PR001-PR005 are emitted by ``PluginRegistrationValidator`` in
``plugin_validator.py``.  Detection requires filesystem access (scanning
the plugin directory, reading ``plugin.json``, checking path existence, and
querying git metadata).  None of that information is available from
frontmatter alone, so the validator functions registered here are
**registration-only stubs** — they exist to make rule metadata available via
``RULE_REGISTRY`` (and therefore via ``skilllint rule PR00N``) without
duplicating the detection logic that belongs in the filesystem-owning
``PluginRegistrationValidator`` class.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | PR001 | Capability exists but not explicitly registered           | warning   |
    | PR002 | Registered capability path does not exist                 | error     |
    | PR003 | Plugin metadata fields not populated                      | info      |
    | PR004 | Plugin metadata repository URL mismatches git remote URL  | warning   |
    | PR005 | Registered command path is a skill directory              | error     |
    +-------+-----------------------------------------------------------+-----------+

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skilllint.rule_registry import skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

_PR_DOCS_BASE = "https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md"


def _docs_url(code: str) -> str:
    """Return the documentation URL for a PR rule code.

    Args:
        code: Rule code string (e.g., "PR001").

    Returns:
        Full URL with anchor for the error code documentation.
    """
    return f"{_PR_DOCS_BASE}#{code.lower()}"


# ---------------------------------------------------------------------------
# PR001 — Capability exists but not explicitly registered in plugin.json
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PR001",
    severity="warning",
    category="plugin-registration",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PR_DOCS_BASE},
)
def check_pr001(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## PR001 — Capability exists but not explicitly registered

    A skill, agent, or command directory was found on the filesystem but is
    not listed in the corresponding array in ``plugin.json``.  When
    ``plugin.json`` contains an explicit ``skills``, ``agents``, or
    ``commands`` array, Claude Code uses only the listed paths and will not
    auto-discover unregistered capabilities.

    Note: when the ``skills`` field is absent from ``plugin.json`` entirely,
    standard-path skills (under ``./skills/``) are auto-discovered by Claude
    Code and PR001 is suppressed for them.  PR001 is only emitted when the
    plugin has opted into explicit registration by declaring the array.

    **Source:** ``PluginRegistrationValidator.validate`` in
    ``plugin_validator.py`` — scans the filesystem for actual capability
    directories and compares against the registered paths from
    ``plugin.json``.

    **Fix:** Add the unregistered capability path to the appropriate array in
    ``plugin.json``:

    ```json
    {
      "skills": ["./skills/my-skill"]
    }
    ```

    Returns:
        Always an empty list.  PR001 is emitted by ``PluginRegistrationValidator``
        in ``plugin_validator.py`` after scanning the filesystem and comparing
        against ``plugin.json``; this function exists for rule metadata
        registration only.

    <!-- examples: PR001 -->
    """
    # Detection requires filesystem scanning (plugin directory) and reading
    # plugin.json registration arrays.
    # Owned by PluginRegistrationValidator in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# PR002 — Registered capability path does not exist
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PR002",
    severity="error",
    category="plugin-registration",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PR_DOCS_BASE},
)
def check_pr002(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## PR002 — Registered capability path does not exist

    A path listed in ``plugin.json`` under ``skills``, ``agents``, or
    ``commands`` does not correspond to an existing directory or file on the
    filesystem.  Claude Code will fail to load the capability at runtime.

    **Source:** ``PluginRegistrationValidator.validate`` in
    ``plugin_validator.py`` — checks whether each registered path resolves to
    an existing ``SKILL.md`` (for skills) or an existing path (for agents and
    commands) within the plugin directory.

    **Fix:** Either remove the stale entry from ``plugin.json``, or create the
    missing capability at the expected path:

    ```bash
    # Remove the stale reference
    # Edit plugin.json and delete the entry under "skills"

    # Or create the missing skill
    mkdir -p skills/my-skill && touch skills/my-skill/SKILL.md
    ```

    Returns:
        Always an empty list.  PR002 is emitted by ``PluginRegistrationValidator``
        in ``plugin_validator.py`` after verifying registered paths against the
        filesystem; this function exists for rule metadata registration only.

    <!-- examples: PR002 -->
    """
    # Detection requires checking path existence on the filesystem for each
    # registered capability in plugin.json.
    # Owned by PluginRegistrationValidator in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# PR003 — Plugin metadata fields not populated
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PR003",
    severity="info",
    category="plugin-registration",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PR_DOCS_BASE},
)
def check_pr003(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## PR003 — Plugin metadata fields not populated

    One or more recommended metadata fields (``repository``, ``homepage``,
    ``author``) are absent from ``plugin.json``.  These fields are not
    required but improve discoverability and attribution.  When git metadata
    is available, the validator suggests values that could be copied from the
    remote URL.

    **Source:** ``PluginRegistrationValidator.validate`` in
    ``plugin_validator.py`` — reads ``plugin.json``, determines which metadata
    fields are missing, queries git for repository metadata, and emits an
    informational message with suggested values.

    **Fix:** Populate the missing fields in ``plugin.json``:

    ```json
    {
      "repository": "https://github.com/owner/plugin-repo",
      "homepage": "https://owner.github.io/plugin-repo",
      "author": "Owner Name"
    }
    ```

    Returns:
        Always an empty list.  PR003 is emitted by ``PluginRegistrationValidator``
        in ``plugin_validator.py`` after reading ``plugin.json`` and querying
        git metadata; this function exists for rule metadata registration only.

    <!-- examples: PR003 -->
    """
    # Detection requires reading plugin.json and querying git metadata via
    # subprocess calls.
    # Owned by PluginRegistrationValidator in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# PR004 — Plugin metadata repository URL mismatches git remote URL
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PR004",
    severity="warning",
    category="plugin-registration",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PR_DOCS_BASE},
)
def check_pr004(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## PR004 — Plugin metadata repository URL mismatches git remote URL

    The ``repository`` field in ``plugin.json`` does not match the URL
    reported by ``git remote get-url origin``.  This mismatch usually
    indicates the ``plugin.json`` was copied from another project and not
    updated, or the repository was moved/renamed.

    **Source:** ``PluginRegistrationValidator.validate`` in
    ``plugin_validator.py`` — compares ``plugin_config["repository"]`` against
    the URL returned by git for the ``origin`` remote.

    **Fix:** Update the ``repository`` field in ``plugin.json`` to match the
    git remote URL:

    ```json
    {
      "repository": "https://github.com/owner/correct-repo"
    }
    ```

    Returns:
        Always an empty list.  PR004 is emitted by ``PluginRegistrationValidator``
        in ``plugin_validator.py`` after querying git metadata and comparing
        against ``plugin.json``; this function exists for rule metadata
        registration only.

    <!-- examples: PR004 -->
    """
    # Detection requires reading plugin.json and querying the git remote URL
    # via subprocess.
    # Owned by PluginRegistrationValidator in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# PR005 — Registered command path is a skill directory (contains SKILL.md)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PR005",
    severity="error",
    category="plugin-registration",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PR_DOCS_BASE},
)
def check_pr005(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## PR005 — Registered command path is a skill directory

    A path listed in the ``commands`` array of ``plugin.json`` resolves to a
    directory that contains a ``SKILL.md`` file.  Skill directories must be
    listed under ``skills``, not ``commands``.  Listing a skill directory as a
    command causes incorrect runtime behaviour and may prevent the skill from
    loading.

    **Source:** ``PluginRegistrationValidator.validate`` in
    ``plugin_validator.py`` — checks whether each registered command path is a
    directory containing a ``SKILL.md`` file.

    **Fix:** Move the path from the ``commands`` array to the ``skills`` array
    in ``plugin.json``:

    ```json
    {
      "skills": ["./skills/my-skill"],
      "commands": []
    }
    ```

    Returns:
        Always an empty list.  PR005 is emitted by ``PluginRegistrationValidator``
        in ``plugin_validator.py`` after checking the filesystem structure of
        registered command paths; this function exists for rule metadata
        registration only.

    <!-- examples: PR005 -->
    """
    # Detection requires checking whether each registered command path contains
    # a SKILL.md file on the filesystem.
    # Owned by PluginRegistrationValidator in plugin_validator.py.
    return []


__all__ = ["check_pr001", "check_pr002", "check_pr003", "check_pr004", "check_pr005"]
