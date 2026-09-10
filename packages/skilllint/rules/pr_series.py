"""PR-series plugin registration rules (PR001, PR002, and PR005).

``PluginRegistrationValidator`` in ``plugin_validator.py`` packages these
results into a ``ValidationResult``.

Detection needs the plugin manifest and the filesystem, not frontmatter, so
each function takes the input it actually reads.

The validator is wired into plugin-root validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from skilllint.rule_registry import _make_issue, skilllint_rule

if TYPE_CHECKING:
    from skilllint.plugin_validator import ValidationIssue, YamlValue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------


def find_actual_capabilities(plugin_dir: Path) -> tuple[set[Path], set[Path], set[Path]]:
    """Find all actual capability files in a plugin directory.

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


def _component_paths(manifest: dict[str, YamlValue], plugin_dir: Path, field: str) -> list[Path]:
    """Parse registered capability paths from a plugin.json field.

    Args:
        manifest: Loaded plugin.json content.
        plugin_dir: Plugin directory path.
        field: Field name (skills, agents, commands).

    Returns:
        Set of registered paths relative to plugin_dir.
    """
    value = manifest.get(field)
    entries = (
        [value]
        if isinstance(value, str)
        else [item for item in value if isinstance(item, str)]
        if isinstance(value, list)
        else []
    )
    return [Path(entry.removeprefix("./")) for entry in entries]


def _registered_component_files(manifest: dict[str, YamlValue], plugin_dir: Path, field: str) -> set[Path]:
    from skilllint.plugin_validator import FRONTMATTER_EXEMPT_FILENAMES  # noqa: PLC0415

    registered: set[Path] = set()
    root = plugin_dir.resolve()
    for reference in _component_paths(manifest, plugin_dir, field):
        target = plugin_dir / reference
        resolved = target.resolve()
        if not resolved.is_relative_to(root):
            continue
        if resolved.is_dir():
            registered.update(
                file.resolve().relative_to(root)
                for file in resolved.glob("*.md")
                if file.name not in FRONTMATTER_EXEMPT_FILENAMES and file.resolve().is_relative_to(root)
            )
        else:
            registered.add(resolved.relative_to(root))
    return registered


# ---------------------------------------------------------------------------
# PR001 — Capability exists but not explicitly registered in plugin.json
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PR001",
    severity="warning",
    category="plugin-registration",
    platforms=["claude-code"],
    authority={
        "origin": "code.claude.com",
        "reference": "https://code.claude.com/docs/en/plugins-reference.md#path-behavior-rules",
    },
)
def check_pr001(manifest: dict[str, YamlValue], plugin_dir: Path) -> list[ValidationIssue]:
    """## PR001 — Capability exists but not explicitly registered

    An agent or command file was found in its default directory but is not
    listed in the corresponding array in ``plugin.json``.

    Per the vendor path-behavior rules, an explicit ``agents`` or
    ``commands`` array *replaces* default directory discovery: once either
    field is declared, Claude Code stops auto-discovering unregistered files
    under the matching default directory, so anything PR001 still finds
    there is a genuine gap.  When the field is absent, the default directory
    is auto-discovered wholesale and PR001 is suppressed.

    **Source:** ``PluginRegistrationValidator.validate`` in
    ``plugin_validator.py`` — scans the filesystem for actual capability
    files and compares them with the registered paths from ``plugin.json``.

    **Fix:** Add the unregistered capability path to the appropriate array in
    ``plugin.json``:

    ```json
    {
      "agents": ["./agents/my-agent.md"]
    }
    ```

    Args:
        manifest: Decoded ``plugin.json`` content.
        plugin_dir: Plugin directory containing ``.claude-plugin/plugin.json``.

    Returns:
        One warning per agent or command file absent from its matching
        registration array.

    <!-- examples: PR001 -->
    """
    _actual_skills, actual_agents, actual_commands = find_actual_capabilities(plugin_dir)
    registered_agents = _registered_component_files(manifest, plugin_dir, "agents")
    registered_commands = _registered_component_files(manifest, plugin_dir, "commands")

    issues: list[ValidationIssue] = []

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
    platforms=["claude-code"],
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
        for ref in _component_paths(manifest, plugin_dir, "skills")
        if not (
            ((plugin_dir / ref).is_file() and ref.name == "SKILL.md")
            or (plugin_dir / ref / "SKILL.md").is_file()
            or any((plugin_dir / ref).glob("*/SKILL.md"))
        )
    )

    issues.extend(
        _make_issue(
            field="plugin.json",
            severity="error",
            message=f"Registered agent '{ref}' does not exist",
            code="PR002",
            suggestion=f"Remove from plugin.json or create {ref}",
        )
        for ref in _component_paths(manifest, plugin_dir, "agents")
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
        for ref in _component_paths(manifest, plugin_dir, "commands")
        if not (plugin_dir / ref).exists()
    )

    return issues


# ---------------------------------------------------------------------------
# PR005 — Registered command path is a skill directory (contains SKILL.md)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PR005",
    severity="info",
    category="plugin-registration",
    platforms=["claude-code"],
    authority={
        "origin": "code.claude.com",
        "reference": "https://code.claude.com/docs/en/plugins-reference.md#component-path-fields",
    },
)
def check_pr005(manifest: dict[str, YamlValue], plugin_dir: Path) -> list[ValidationIssue]:
    """## PR005 — Registered command path is a skill directory

    A path listed in the ``commands`` array of ``plugin.json`` resolves to a
    directory that contains a ``SKILL.md`` file.  Per
    code.claude.com/docs/en/plugins-reference, ``commands`` accepts "custom
    flat .md skill files or directories", so this is valid configuration, not
    a load-blocking error.  Listing it under ``commands`` instead of
    ``skills`` does forgo skill-only features (e.g. supporting files) that
    code.claude.com/docs/en/skills gives as the reason skills are recommended
    over commands.

    **Source:** ``PluginRegistrationValidator.validate`` in
    ``plugin_validator.py`` — checks whether each registered command path is a
    directory containing a ``SKILL.md`` file.

    **Fix (recommended, not required):** Move the path from the ``commands``
    array to the ``skills`` array in ``plugin.json``:

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
        One info issue per registered command path that is a directory
        containing a ``SKILL.md``.

    <!-- examples: PR005 -->
    """
    return [
        _make_issue(
            field="plugin.json",
            severity="info",
            message=(
                f"Registered command '{ref}' is a skill directory (contains SKILL.md). "
                f"Consider listing it under 'skills' instead of 'commands' — skills support "
                f"features (e.g. supporting files) that commands do not."
            ),
            code="PR005",
            suggestion=f"Move '{ref}' from the 'commands' array to the 'skills' array in plugin.json",
        )
        for ref in _component_paths(manifest, plugin_dir, "commands")
        if (plugin_dir / ref).is_dir() and (plugin_dir / ref / "SKILL.md").exists()
    ]


__all__ = ["check_pr001", "check_pr002", "check_pr005", "find_actual_capabilities"]
