"""PR-series plugin registration rules (PR001-PR005).

PR001-PR005 detection lives here.  ``PluginRegistrationValidator`` in
``plugin_validator.py`` is a thin wrapper that calls these functions and
packages the results into a ``ValidationResult``; it retains SK009 (a
different rule family) and the git-metadata lookup, which shells out to
``git`` and is a validator concern rather than a rule concern.

Detection needs the plugin manifest and the filesystem, not frontmatter, so
each function takes the input it actually reads.

Note: ``PluginRegistrationValidator`` is not currently wired into
``_get_validators_for_path``, so PR001-PR005 do not fire during a normal
``skilllint check`` run.  The rules are nonetheless callable and unit-testable
on their own.

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
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import msgspec.json

from skilllint.rule_registry import _make_issue, skilllint_rule

if TYPE_CHECKING:
    from skilllint.plugin_validator import ValidationIssue, YamlValue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------


def find_actual_capabilities(plugin_dir: Path) -> tuple[set[Path], set[Path], set[Path]]:
    """Find all actual capability files in a plugin directory.

    Shared with ``PluginRegistrationValidator``, which needs the same disk
    inventory to build its SK009 message.

    Args:
        plugin_dir: Path to the plugin directory.

    Returns:
        Tuple of (actual_skills, actual_agents, actual_commands) as sets of
        paths relative to plugin_dir.
    """
    from skilllint.plugin_validator import FRONTMATTER_EXEMPT_FILENAMES  # noqa: PLC0415

    actual_skills: set[Path] = set()
    actual_agents: set[Path] = set()
    actual_commands: set[Path] = set()

    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        actual_skills = {
            d.relative_to(plugin_dir) for d in skills_dir.glob("*/") if d.is_dir() and (d / "SKILL.md").exists()
        }

    agents_dir = plugin_dir / "agents"
    if agents_dir.is_dir():
        actual_agents = {
            f.relative_to(plugin_dir) for f in agents_dir.glob("*.md") if f.name not in FRONTMATTER_EXEMPT_FILENAMES
        }

    commands_dir = plugin_dir / "commands"
    if commands_dir.is_dir():
        actual_commands = {
            f.relative_to(plugin_dir) for f in commands_dir.glob("*.md") if f.name not in FRONTMATTER_EXEMPT_FILENAMES
        }

    return actual_skills, actual_agents, actual_commands


def parse_registered_paths(manifest: dict[str, YamlValue], plugin_dir: Path, field: str) -> set[Path]:
    """Parse registered capability paths from a plugin.json field.

    Shared with ``PluginRegistrationValidator``, which needs the registered
    skills to build its SK009 message.

    Args:
        manifest: Loaded plugin.json content.
        plugin_dir: Plugin directory path.
        field: Field name (skills, agents, commands).

    Returns:
        Set of registered paths relative to plugin_dir.
    """
    from skilllint.plugin_validator import FRONTMATTER_EXEMPT_FILENAMES  # noqa: PLC0415

    registered: set[Path] = set()

    if field not in manifest:
        return registered

    value = manifest[field]

    if isinstance(value, str):
        value_path = plugin_dir / value.removeprefix("./")
        if value_path.is_dir():
            registered.update(
                f.relative_to(plugin_dir) for f in value_path.glob("*.md") if f.name not in FRONTMATTER_EXEMPT_FILENAMES
            )
        else:
            registered.add(Path(value.removeprefix("./")))
    elif isinstance(value, list):
        registered.update(Path(item.removeprefix("./")) for item in value if isinstance(item, str))

    return registered


# ---------------------------------------------------------------------------
# PR001 — Capability exists but not explicitly registered in plugin.json
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PR001",
    severity="warning",
    category="plugin-registration",
    platforms=["agentskills"],
    authority={
        "origin": "code.claude.com",
        "reference": "https://code.claude.com/docs/en/plugins-reference.md#path-behavior-rules",
    },
)
def check_pr001(manifest: dict[str, YamlValue], plugin_dir: Path) -> list[ValidationIssue]:
    """## PR001 — Capability exists but not explicitly registered

    A skill, agent, or command directory was found on the filesystem but is
    not listed in the corresponding array in ``plugin.json``.

    Per the vendor path-behavior rules, an explicit ``agents`` or
    ``commands`` array *replaces* default directory discovery: once either
    field is declared, Claude Code stops auto-discovering unregistered files
    under the matching default directory, so anything PR001 still finds
    there is a genuine gap.  When the field is absent, the default directory
    is auto-discovered wholesale and PR001 is suppressed.

    ``skills`` behaves differently: the default ``./skills/`` directory is
    *always* scanned, whether or not ``skills`` is declared (additive, not
    replacing).  An unregistered standard-path skill therefore always loads.
    PR001 still flags it once the plugin has opted into explicit
    registration by declaring the ``skills`` array (even empty), as a
    consistency nudge, but is suppressed while no ``skills`` array is
    declared at all.

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

    Args:
        manifest: Decoded ``plugin.json`` content.
        plugin_dir: Plugin directory containing ``.claude-plugin/plugin.json``.

    Returns:
        One warning per capability found on disk but absent from the matching
        registration array, ordered skills, agents, then commands.

    <!-- examples: PR001 -->
    """
    actual_skills, actual_agents, actual_commands = find_actual_capabilities(plugin_dir)
    registered_skills = parse_registered_paths(manifest, plugin_dir, "skills")
    registered_agents = parse_registered_paths(manifest, plugin_dir, "agents")
    registered_commands = parse_registered_paths(manifest, plugin_dir, "commands")

    issues: list[ValidationIssue] = []

    # ``skills`` is additive (path-behavior-rules): the default ./skills/
    # directory is always scanned regardless of declaration, so an
    # unregistered standard-path skill always loads.  PR001 only nudges for
    # explicit registration once the plugin has opted in by declaring the
    # array (even empty); it is suppressed while no ``skills`` array exists
    # at all.  (Mirrors the SK009 gate in plugin_validator.py.)
    issues.extend(
        _make_issue(
            field="plugin.json",
            severity="warning",
            message=f"Skill '{orphan}' exists but is not registered (relies on default discovery)",
            code="PR001",
            suggestion=f"Add './{orphan}' to the skills array in plugin.json",
        )
        for orphan in actual_skills - registered_skills
        if "skills" in manifest
    )

    # ``agents``/``commands`` replace default discovery once declared
    # (path-behavior-rules): an unregistered file under the default
    # directory is then a genuine gap.  When the field is absent, the
    # default directory is still auto-discovered wholesale, so PR001 is
    # suppressed for it.
    issues.extend(
        _make_issue(
            field="plugin.json",
            severity="warning",
            message=f"Agent '{orphan}' exists but is not registered",
            code="PR001",
            suggestion=f"Add './{orphan}' to the agents array in plugin.json",
        )
        for orphan in actual_agents - registered_agents
        if "agents" in manifest
    )

    issues.extend(
        _make_issue(
            field="plugin.json",
            severity="warning",
            message=f"Command '{orphan}' exists but is not registered",
            code="PR001",
            suggestion=f"Add './{orphan}' to the commands array in plugin.json",
        )
        for orphan in actual_commands - registered_commands
        if "commands" in manifest
    )

    return issues


# ---------------------------------------------------------------------------
# PR002 — Registered capability path does not exist
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PR002",
    severity="error",
    category="plugin-registration",
    platforms=["agentskills"],
    # No authority: no vendor doc requires validating that a registered
    # skills/agents/commands path resolves on disk before load. This
    # existence check is skilllint's own robustness check, not a claim
    # traceable to an upstream spec.
)
def check_pr002(manifest: dict[str, YamlValue], plugin_dir: Path) -> list[ValidationIssue]:
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

    Args:
        manifest: Decoded ``plugin.json`` content.
        plugin_dir: Plugin directory containing ``.claude-plugin/plugin.json``.

    Returns:
        One error per registered path that does not resolve on disk, ordered
        skills, agents, then commands.

    <!-- examples: PR002 -->
    """
    issues: list[ValidationIssue] = []

    issues.extend(
        _make_issue(
            field="plugin.json",
            severity="error",
            message=f"Registered skill '{ref}' does not exist",
            code="PR002",
            suggestion=f"Remove from plugin.json or create {ref}/SKILL.md",
        )
        for ref in parse_registered_paths(manifest, plugin_dir, "skills")
        if not (plugin_dir / ref / "SKILL.md").exists()
    )

    issues.extend(
        _make_issue(
            field="plugin.json",
            severity="error",
            message=f"Registered agent '{ref}' does not exist",
            code="PR002",
            suggestion=f"Remove from plugin.json or create {ref}",
        )
        for ref in parse_registered_paths(manifest, plugin_dir, "agents")
        if not (plugin_dir / ref).exists()
    )

    issues.extend(
        _make_issue(
            field="plugin.json",
            severity="error",
            message=f"Registered command '{ref}' does not exist",
            code="PR002",
            suggestion=f"Remove from plugin.json or create {ref}",
        )
        for ref in parse_registered_paths(manifest, plugin_dir, "commands")
        if not (plugin_dir / ref).exists()
    )

    return issues


# ---------------------------------------------------------------------------
# PR003 — Plugin metadata fields not populated
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PR003",
    severity="info",
    category="plugin-registration",
    platforms=["agentskills"],
    authority={
        "origin": "code.claude.com",
        "reference": "https://code.claude.com/docs/en/plugins-reference.md#metadata-fields",
    },
)
def check_pr003(manifest: dict[str, YamlValue], git_metadata: dict[str, YamlValue]) -> list[ValidationIssue]:
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

    Args:
        manifest: Decoded ``plugin.json`` content.
        git_metadata: Metadata derived from git by the caller (empty when git
            is unavailable or the plugin is not inside a repository).

    Returns:
        A single info issue naming the fields git could populate, or an empty
        list when nothing is missing or git yielded nothing.

    <!-- examples: PR003 -->
    """
    missing = [k for k in ("repository", "homepage", "author") if k not in manifest and k in git_metadata]
    if not missing:
        return []

    suggestion_json = msgspec.json.format(msgspec.json.encode({k: git_metadata[k] for k in missing}), indent=2).decode()
    return [
        _make_issue(
            field="plugin.json",
            severity="info",
            message=f"Metadata could be populated from git: {', '.join(missing)}",
            code="PR003",
            suggestion=f"Add to plugin.json:\n{suggestion_json}",
        )
    ]


# ---------------------------------------------------------------------------
# PR004 — Plugin metadata repository URL mismatches git remote URL
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PR004",
    severity="warning",
    category="plugin-registration",
    platforms=["agentskills"],
    # No authority: no vendor doc requires plugin.json's "repository" field
    # to match the git remote URL. That consistency check is skilllint's own
    # opinion, not a claim traceable to an upstream spec.
)
def check_pr004(manifest: dict[str, YamlValue], git_metadata: dict[str, YamlValue]) -> list[ValidationIssue]:
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

    Args:
        manifest: Decoded ``plugin.json`` content.
        git_metadata: Metadata derived from git by the caller (empty when git
            is unavailable or the plugin is not inside a repository).

    Returns:
        A single warning when both sides declare a repository and the two
        differ, otherwise an empty list.

    <!-- examples: PR004 -->
    """
    if (
        "repository" not in manifest
        or "repository" not in git_metadata
        or manifest["repository"] == git_metadata["repository"]
    ):
        return []

    return [
        _make_issue(
            field="plugin.json",
            severity="warning",
            message=(
                f"Repository URL mismatch: plugin.json has "
                f"'{manifest['repository']}', git has '{git_metadata['repository']}'"
            ),
            code="PR004",
            suggestion=f"Update repository to: {git_metadata['repository']}",
        )
    ]


# ---------------------------------------------------------------------------
# PR005 — Registered command path is a skill directory (contains SKILL.md)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PR005",
    severity="error",
    category="plugin-registration",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_pr005(manifest: dict[str, YamlValue], plugin_dir: Path) -> list[ValidationIssue]:
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

    Args:
        manifest: Decoded ``plugin.json`` content.
        plugin_dir: Plugin directory containing ``.claude-plugin/plugin.json``.

    Returns:
        One error per registered command path that is a directory containing a
        ``SKILL.md``.

    <!-- examples: PR005 -->
    """
    return [
        _make_issue(
            field="plugin.json",
            severity="error",
            message=(
                f"Registered command '{ref}' is a skill directory (contains SKILL.md). "
                f"Skill directories must not be listed under 'commands'."
            ),
            code="PR005",
            suggestion=f"Move '{ref}' from the 'commands' array to the 'skills' array in plugin.json",
        )
        for ref in parse_registered_paths(manifest, plugin_dir, "commands")
        if (plugin_dir / ref).is_dir() and (plugin_dir / ref / "SKILL.md").exists()
    ]


__all__ = [
    "check_pr001",
    "check_pr002",
    "check_pr003",
    "check_pr004",
    "check_pr005",
    "find_actual_capabilities",
    "parse_registered_paths",
]
