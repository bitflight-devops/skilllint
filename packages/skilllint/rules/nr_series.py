"""NR-series namespace reference validation rules (NR001-NR002).

NR001 and NR002 detection lives here.  ``NamespaceReferenceValidator`` in
``plugin_validator.py`` is a thin wrapper that reads the file and packages the
results into a ``ValidationResult``; it retains only the unreadable-file case
(an I/O failure, not a namespace-reference finding) and the ``can_fix`` /
``fix`` pair.

Detection needs the markdown body plus filesystem access, not frontmatter, so
both rules take ``(content, path)``.

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

import re
from pathlib import Path
from typing import TYPE_CHECKING

import msgspec

from skilllint.rule_registry import _make_issue, skilllint_rule

if TYPE_CHECKING:
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


# ---------------------------------------------------------------------------
# Reference extraction
# ---------------------------------------------------------------------------

# Regex patterns for extracting namespace-qualified references
SKILL_COMMAND_PATTERN = r'Skill\(command:\s*"([^"]+):([^"]+)"'
SKILL_SKILL_PATTERN = r'Skill\(skill="([^"]+):([^"]+)"'
TASK_AGENT_PATTERN = r'Task\(agent[=:]\s*"([^"]+):([^"]+)"'
AT_AGENT_PATTERN = r"@([a-z0-9-]+):([a-z0-9-]+)"
SLASH_COMMAND_PATTERN = r"(?<!\w)/([a-z0-9-]+):([a-z0-9-]+)"


def _extract_body(content: str) -> str:
    """Extract file body content after YAML frontmatter.

    Args:
        content: Full file content

    Returns:
        Body text after the closing ``---`` delimiter, or the full content
        if no frontmatter is present
    """
    if not content.startswith("---"):
        return content

    # Find closing delimiter
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return content

    # Return everything after the closing ---
    return content[3 + end_match.end() :]


def _find_plugins_root(path: Path) -> Path | None:
    """Find the repository-level ``plugins/`` directory from a file path.

    Walks up from the file path looking for a directory named ``plugins``
    that appears in the path's parents.

    Args:
        path: Path to a file inside a plugin

    Returns:
        Path to the ``plugins/`` directory, or None if not found
    """
    resolved = path.resolve()
    parts = resolved.parts
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] == "plugins":
            candidate = Path(*parts[: i + 1])
            if candidate.is_dir():
                return candidate
    return None


def _strip_urls_and_code(body: str) -> str:
    """Remove URLs, fenced code blocks, and inline code spans from body.

    Strips content that may contain slash-colon patterns that are not
    real namespace references (e.g. ``http://localhost:8080``).

    Args:
        body: Markdown body content

    Returns:
        Body with URLs, fenced code blocks, and inline code spans removed
    """
    # Strip fenced code blocks (``` or ~~~ delimited)
    stripped = re.sub(r"^(`{3,}|~{3,})[^\n]*\n.*?\n\1\s*$", "", body, flags=re.MULTILINE | re.DOTALL)
    # Strip inline code spans
    stripped = re.sub(r"(`+)(?!`)(.+?)(?<!`)\1(?!`)", "", stripped)
    # Strip URLs (http:// and https:// through end of URL)
    return re.sub(r"https?://[^\s)\]>\"']+", "", stripped)


def _extract_references(body: str) -> list[tuple[str, str, str, str]]:
    """Extract all namespace-qualified references from file body.

    Args:
        body: File body content (after frontmatter)

    Returns:
        List of (label, plugin, name, ref_type) tuples where ref_type is
        one of 'skill', 'agent', or 'command'
    """
    references: list[tuple[str, str, str, str]] = []

    # Skill(command: "plugin:name")
    for match in re.finditer(SKILL_COMMAND_PATTERN, body):
        plugin, name = match.group(1), match.group(2)
        label = f'Skill(command: "{plugin}:{name}")'
        references.append((label, plugin, name, "skill"))

    # Skill(skill="plugin:name")
    for match in re.finditer(SKILL_SKILL_PATTERN, body):
        plugin, name = match.group(1), match.group(2)
        label = f'Skill(skill="{plugin}:{name}")'
        references.append((label, plugin, name, "skill"))

    # Task(agent="plugin:name")
    for match in re.finditer(TASK_AGENT_PATTERN, body):
        plugin, name = match.group(1), match.group(2)
        label = f'Task(agent="{plugin}:{name}")'
        references.append((label, plugin, name, "agent"))

    # @plugin:agent-name
    for match in re.finditer(AT_AGENT_PATTERN, body):
        plugin, name = match.group(1), match.group(2)
        label = f"@{plugin}:{name}"
        references.append((label, plugin, name, "agent"))

    # /plugin:skill-name -- use stripped body to avoid URL false positives
    stripped_body = _strip_urls_and_code(body)
    for match in re.finditer(SLASH_COMMAND_PATTERN, stripped_body):
        plugin, name = match.group(1), match.group(2)
        label = f"/{plugin}:{name}"
        references.append((label, plugin, name, "command"))

    return references


def _scoped_references(content: str, path: Path) -> tuple[list[tuple[str, str, str, str]], Path] | None:
    """Extract references plus the plugins root, or None when out of scope.

    Both NR rules only apply to files that have a body and live inside a
    ``plugins/`` tree; this shared gate keeps that condition identical for
    both.

    Args:
        content: Full file content.
        path: Path to the file being validated.

    Returns:
        ``(references, plugins_root)`` or None when the file has no body or
        is not inside a plugins directory structure.
    """
    # Only check the body (after frontmatter)
    body = _extract_body(content)
    if not body:
        return None

    # Find the plugins root directory
    plugins_root = _find_plugins_root(path)
    if plugins_root is None:
        # Not inside a plugins directory structure -- skip validation
        return None

    return _extract_references(body), plugins_root


def _is_skipped(plugin: str, name: str) -> bool:
    """Return True when a reference is a template placeholder, exempt from both NR rules.

    Args:
        plugin: Namespace prefix component.
        name: Target name component.

    Returns:
        True for template placeholders (containing ``{`` or ``}``).
    """
    return "{" in plugin or "}" in plugin or "{" in name or "}" in name


# ---------------------------------------------------------------------------
# Reference resolution
# ---------------------------------------------------------------------------


def _resolve_to_directory(path: Path) -> Path | None:
    """Resolve path to directory, following symlinks and Git pointer files (Windows).

    On Windows, Git may store symlinks as regular files whose content is the
    target path. This allows validation to work cross-platform.

    Args:
        path: Path that may be a directory, symlink, or pointer file

    Returns:
        Resolved directory path, or None if resolution fails
    """
    result: Path | None = None
    if path.is_dir():
        result = path.resolve()
    elif path.is_symlink():
        resolved = path.resolve()
        result = resolved if resolved.is_dir() else None
    elif path.is_file():
        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError:
            pass
        else:
            if content and "\n" not in content:
                try:
                    target = (path.parent / content).resolve()
                    result = target if target.is_dir() else None
                except (OSError, RuntimeError):
                    pass
    return result


def _build_plugin_name_map(plugins_root: Path) -> dict[str, Path]:
    """Build a mapping from plugin declared name to plugin directory path.

    Scans each subdirectory of ``plugins_root`` and reads the ``"name"``
    field from ``.claude-plugin/plugin.json`` (falling back to the
    directory name when the file is absent or unparseable).  This ensures
    that namespace references are resolved against the plugin's declared
    name rather than its on-disk directory name.

    Args:
        plugins_root: Path to the ``plugins/`` directory

    Returns:
        Mapping of ``{declared_name: plugin_dir_path}`` for every plugin
        directory found under ``plugins_root``
    """
    name_to_dir: dict[str, Path] = {}
    if not plugins_root.is_dir():
        return name_to_dir

    for entry in plugins_root.iterdir():
        if not entry.is_dir():
            continue
        # Attempt to read the declared name from plugin.json
        plugin_json = entry / ".claude-plugin" / "plugin.json"
        declared_name: str | None = None
        if plugin_json.is_file():
            try:
                data = msgspec.json.decode(plugin_json.read_bytes())
                if isinstance(data, dict) and isinstance(data.get("name"), str):
                    declared_name = data["name"]
            except (OSError, msgspec.DecodeError):
                pass
        # Fall back to directory name when plugin.json is absent/invalid
        name_to_dir[declared_name or entry.name] = entry

    return name_to_dir


def _resolve_skill_reference(plugin_dir: Path, name: str) -> bool:
    """Check if a skill reference resolves to an existing file.

    Checks direct path and nested (category) paths. Resolves symlinks and
    Git pointer files (Windows) before existence checks.

    Args:
        plugin_dir: Path to the resolved plugin directory
        name: Skill name

    Returns:
        True if the skill SKILL.md exists at any valid location
    """
    # Direct: {plugin_dir}/skills/{name}/SKILL.md
    skill_dir = plugin_dir / "skills" / name
    resolved_dir = _resolve_to_directory(skill_dir)
    if resolved_dir is not None and (resolved_dir / "SKILL.md").is_file():
        return True

    # Also check direct path (real symlinks resolve via resolve())
    direct = plugin_dir / "skills" / name / "SKILL.md"
    if direct.is_file():
        return True

    # Nested: {plugin_dir}/skills/*/{name}/SKILL.md
    nested_pattern = plugin_dir / "skills"
    if nested_pattern.is_dir():
        for category_dir in nested_pattern.iterdir():
            resolved_cat = _resolve_to_directory(category_dir)
            if resolved_cat is not None:
                nested = resolved_cat / name / "SKILL.md"
                if nested.is_file():
                    return True
                # Pointer/symlink: category_dir may resolve to skill dir itself
                if category_dir.name == name and (resolved_cat / "SKILL.md").is_file():
                    return True

    return False


def _resolve_agent_reference(plugin_dir: Path, name: str) -> bool:
    """Check if an agent reference resolves to an existing file.

    Args:
        plugin_dir: Path to the resolved plugin directory
        name: Agent name

    Returns:
        True if the agent .md file exists
    """
    agent_path = plugin_dir / "agents" / f"{name}.md"
    return agent_path.is_file()


def _resolve_command_reference(plugin_dir: Path, name: str) -> bool:
    """Check if a command/slash-command reference resolves to an existing file.

    Slash command references can resolve to skills or commands.

    Args:
        plugin_dir: Path to the resolved plugin directory
        name: Command or skill name

    Returns:
        True if the target exists as a skill or command
    """
    # Check as skill first (most common)
    if _resolve_skill_reference(plugin_dir, name):
        return True

    # Check as command: {plugin_dir}/commands/{name}.md
    command_path = plugin_dir / "commands" / f"{name}.md"
    return command_path.is_file()


def _resolve_ref_or_error(
    *, label: str, plugin: str, name: str, ref_type: str, plugin_dir: Path
) -> ValidationIssue | None:
    """Resolve a reference against a plugin directory, returning NR001 if missing.

    Args:
        label: Reference label for error messages.
        plugin: Namespace prefix.
        name: Target name.
        ref_type: ``"skill"``, ``"agent"``, or ``"command"``.
        plugin_dir: Resolved plugin directory path.

    Returns:
        An NR001 ValidationIssue if the target cannot be resolved, or
        None if the reference is valid (or the ref_type is unknown).
    """
    match ref_type:
        case "skill":
            found = _resolve_skill_reference(plugin_dir, name)
            expected = (
                f"plugins/{plugin}/skills/{name}/SKILL.md or plugins/{plugin}/skills/{{category}}/{name}/SKILL.md"
            )
        case "agent":
            found = _resolve_agent_reference(plugin_dir, name)
            expected = f"plugins/{plugin}/agents/{name}.md"
        case "command":
            found = _resolve_command_reference(plugin_dir, name)
            expected = (
                f"plugins/{plugin}/skills/{name}/SKILL.md, "
                f"plugins/{plugin}/skills/{{category}}/{name}/SKILL.md, "
                f"or plugins/{plugin}/commands/{name}.md"
            )
        case _:
            return None

    if found:
        return None

    return _make_issue(
        field="namespace-reference",
        severity="error",
        message=(f"Namespace reference target does not exist: {label}"),
        code="NR001",
        suggestion=f"Expected file at: {expected}",
    )


def _has_path_traversal(component: str) -> bool:
    r"""Check if a namespace reference component contains path-traversal.

    A well-formed namespace reference component is a plain identifier
    (lowercase letters, digits, hyphens).  Any path separator or
    parent-directory sequence indicates an attempt to escape the plugin
    directory boundary and should emit NR002.

    Args:
        component: A plugin prefix or target name extracted from a
            namespace reference.

    Returns:
        True if the component contains ``..``, ``/``, or ``\\``.
    """
    return ".." in component or "/" in component or "\\" in component


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
def check_nr001(content: str, path: Path) -> list[ValidationIssue]:
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

    References carrying a path-traversal sequence are owned by NR002 and are
    skipped here, so a single reference never emits both codes.  The
    unreadable-file case is emitted by ``NamespaceReferenceValidator`` because
    it is an I/O failure rather than a reference finding.

    **Fix:** Ensure the referenced target exists at the expected path.  For
    a skill reference ``plugin:my-skill``, create the skill file at one of:

    ```
    plugins / plugin / skills / my - skill / SKILL.md
    plugins / plugin / skills / {category} / my - skill / SKILL.md
    ```

    Or correct the namespace prefix to match an existing plugin directory.

    Args:
        content: Full file content, including any YAML frontmatter.
        path: Path to the file being validated; used to locate the enclosing
            ``plugins/`` root and resolve reference targets.

    Returns:
        One issue per unresolvable namespace reference; empty when every
        reference resolves or the file is outside a plugins tree.

    <!-- examples: NR001 -->
    """
    scoped = _scoped_references(content, path)
    if scoped is None:
        return []
    references, plugins_root = scoped

    # Build name→dir mapping once: reads plugin.json "name" from each plugin dir
    # so that namespace resolution uses the declared name, not the directory name.
    name_to_dir = _build_plugin_name_map(plugins_root)

    issues: list[ValidationIssue] = []
    for label, plugin, name, ref_type in references:
        if _is_skipped(plugin, name):
            continue

        # References with traversal sequences are reported as NR002 instead;
        # they never reach resolution.
        if _has_path_traversal(plugin) or _has_path_traversal(name):
            continue

        # Resolve the plugin directory via plugin.json name mapping
        plugin_dir = name_to_dir.get(plugin)
        if plugin_dir is None:
            issues.append(
                _make_issue(
                    field="namespace-reference",
                    severity="error",
                    message=(
                        f"Namespace reference target does not exist: {label} -- plugin directory '{plugin}' not found"
                    ),
                    code="NR001",
                    suggestion=(
                        f"Expected plugin directory at: {plugins_root / plugin}. "
                        f"Create the plugin or fix the namespace prefix."
                    ),
                )
            )
            continue

        issue = _resolve_ref_or_error(label=label, plugin=plugin, name=name, ref_type=ref_type, plugin_dir=plugin_dir)
        if issue is not None:
            issues.append(issue)

    return issues


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
def check_nr002(content: str, path: Path) -> list[ValidationIssue]:
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

    The permissive ``Skill(...)`` / ``Task(...)`` regex patterns match
    any quoted string (``[^"]+``), so the plugin and name components
    can contain ``..``, ``/``, or ``\\`` even though those would never
    appear in a well-formed namespace reference.  When either component
    contains such a sequence, the reference is treated as escaping the
    plugin boundary and NR002 is emitted.

    Such references are considered invalid because the plugin boundary is a
    security and portability constraint: each plugin is a self-contained unit
    and should only reference files within its own directory tree.

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

    Args:
        content: Full file content, including any YAML frontmatter.
        path: Path to the file being validated; used to confirm the file
            lives inside a ``plugins/`` tree.

    Returns:
        One issue per reference containing a path-traversal sequence; empty
        when every reference is well-formed or the file is outside a plugins
        tree.

    <!-- examples: NR002 -->
    """
    scoped = _scoped_references(content, path)
    if scoped is None:
        return []
    references, _plugins_root = scoped

    issues: list[ValidationIssue] = []
    for label, plugin, name, _ref_type in references:
        if _is_skipped(plugin, name):
            continue

        if not (_has_path_traversal(plugin) or _has_path_traversal(name)):
            continue

        issues.append(
            _make_issue(
                field="namespace-reference",
                severity="error",
                message=(
                    f"Namespace reference points outside plugin directory: {label} -- contains path-traversal sequence"
                ),
                code="NR002",
                suggestion=(
                    "Remove '..', '/', and '\\\\' from the reference. "
                    "Use 'other-plugin:skill-name' with a correct "
                    "namespace prefix instead of relative paths."
                ),
            )
        )

    return issues


__all__ = ["check_nr001", "check_nr002"]
