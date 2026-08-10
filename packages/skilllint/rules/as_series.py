"""AS-series rule validation for agentskills.io SKILL.md files.

Rules AS006-AS009 fire on SKILL.md files only, regardless of which platform
adapter is active. They enforce the AgentSkills specification, a cross-harness
baseline that defines SKILL.md and does not describe agent files. A check on
agent frontmatter belongs to a series that governs agent files, cited to the
harness documentation that defines them — not here.

Entry point: check_skill_md(path: Path) -> list[dict]

Each violation dict has the shape:
    {"code": str, "severity": str, "message": str}

Severities:
    "warning" — AS008, AS009
    "info"    — AS006
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from skilllint.rule_registry import RULE_REGISTRY, skilllint_rule
from skilllint.token_counter import TOKEN_ERROR_THRESHOLD, TOKEN_WARNING_THRESHOLD

if TYPE_CHECKING:
    import pathlib

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rule registry — maps code to human-readable description
# ---------------------------------------------------------------------------

AS_RULES: dict[str, str] = {
    "AS006": "No eval_queries.json found — add evaluation queries for quality assurance",
    "AS008": "MCP tool name may have incorrect casing — case is sensitive in the tools field",
    "AS009": "Nested skill will not be auto-discovered — skills must be direct children of the skills/ directory",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_skill_md(path: pathlib.Path) -> tuple[dict, list[str]]:
    """Parse a SKILL.md file into frontmatter dict and body lines.

    Frontmatter is delimited by leading '---' lines. Everything after
    the closing '---' is the body.

    Returns:
        (frontmatter, body_lines) where frontmatter is a dict of parsed YAML
        fields and body_lines is the content after the frontmatter block.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    frontmatter: dict = {}
    body_lines: list[str] = []

    if not lines or lines[0].strip() != "---":
        # No frontmatter — treat entire file as body
        return {}, lines

    # Find closing '---'
    close_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            close_idx = i
            break

    if close_idx is None:
        # Unclosed frontmatter — parse what we can, no body
        return {}, []

    # Parse frontmatter lines as simple key: value YAML
    for line in lines[1:close_idx]:
        if ":" in line:
            key, _, value = line.partition(":")
            key_stripped = key.strip()
            value_stripped = value.strip()
            frontmatter[key_stripped] = value_stripped

    body_lines = lines[close_idx + 1 :]

    return frontmatter, body_lines


def _violation(
    code: str, severity: str, message: str, fix: str | None = None, authority: dict | None = None
) -> dict[str, str | dict]:
    """Build a violation dict.

    Args:
        code: Rule code (e.g., "AS006").
        severity: Severity level ("error", "warning", "info").
        message: Human-readable message.
        fix: Optional auto-fix instruction.
        authority: Optional authority metadata dict.

    Returns:
        Violation dict with code, severity, message, and optional fix/authority.
    """
    result: dict[str, str | dict] = {"code": code, "severity": severity, "message": message}
    if fix:
        result["fix"] = fix
    if authority:
        result["authority"] = authority
    return result


def _get_rule_authority(code: str) -> dict | None:
    """Get authority metadata for a rule from the registry.

    Args:
        code: Rule ID (e.g., "AS006")

    Returns:
        Authority dict with 'origin' and optional 'reference', or None if not found.
    """
    entry = RULE_REGISTRY.get(code.upper())
    if entry and entry.authority:
        result = {"origin": entry.authority.origin}
        if entry.authority.reference:
            result["reference"] = entry.authority.reference
        return result
    return None


def _make_violation(code: str, severity: str, message: str, fix: str | None = None) -> dict:
    """Create a violation dict with authority metadata from the rule registry.

    This is a convenience wrapper around _violation that automatically
    looks up and includes authority metadata from the rule registry.

    Args:
        code: Rule ID (e.g., "AS006")
        severity: One of "error", "warning", "info"
        message: Human-readable violation message
        fix: Optional auto-fix suggestion

    Returns:
        Violation dict with code, severity, message, and optionally fix and authority.
    """
    return _violation(code, severity, message, fix=fix, authority=_get_rule_authority(code))


# ---------------------------------------------------------------------------
# Individual rule checks
# ---------------------------------------------------------------------------


def _extract_tools_list(path: pathlib.Path, field: str = "allowed-tools") -> list[str]:
    """Extract tool names from a tool-declaring frontmatter field.

    Handles the YAML list form and the inline string form. Uses proper YAML
    parsing (not the simple key/value parser used by _parse_skill_md) so that
    multi-line list values are read correctly.

    The inline form is split on **both** whitespace and commas. The AgentSkills
    specification describes ``allowed-tools`` as a space-separated string
    (agentskills.io/specification.md, fetched 2026-08-22), but marks the field
    Experimental and notes support varies between implementations, and nothing
    establishes that another separator is an error. Parsing liberally is what
    lets a rule *see* the entries either way; whether a given separator is
    worth reporting is a separate question this function does not answer.

    Args:
        path: Path to the SKILL.md file.
        field: Frontmatter key to read. Defaults to ``allowed-tools``, the
            field the AgentSkills specification defines for skills.

    Returns:
        List of tool name strings. Empty list if the field is absent or
        the file cannot be parsed.
    """
    # Deferred import to break circular dependency; plugin_validator imports
    # rules modules, so we defer here rather than at module level.
    from skilllint.frontmatter_core import extract_frontmatter  # noqa: PLC0415
    from skilllint.plugin_validator import safe_load_yaml_with_colon_fix  # noqa: PLC0415

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return []

    fm_text, _start, _end = extract_frontmatter(content)
    if fm_text is None:
        return []

    parsed, _err, _colon_fields, _used = safe_load_yaml_with_colon_fix(fm_text)
    if not isinstance(parsed, dict):
        return []

    tools_value = parsed.get(field)
    if isinstance(tools_value, list):
        return [str(t) for t in tools_value if t is not None]
    if isinstance(tools_value, str):
        # Inline form, either separator: "Read Grep" or "Read, Grep".
        return [t for t in tools_value.replace(",", " ").split() if t]
    return []


def _extract_mcp_server_keys(data: dict[str, object]) -> set[str]:
    """Return the keys of the ``mcpServers`` dict inside *data*, if present.

    Args:
        data: A parsed JSON/YAML dict that may contain an ``mcpServers`` key.

    Returns:
        Set of server name strings; empty set when key is absent or not a dict.
    """
    mcp_servers = data.get("mcpServers")
    if isinstance(mcp_servers, dict):
        return {str(k) for k in mcp_servers}
    return set()


def _read_json_file(path: pathlib.Path) -> dict[str, object] | None:
    """Read and parse a JSON file, returning a dict or None on failure.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed dict, or None if the file is missing, unreadable, or not a dict.
    """
    import json  # noqa: PLC0415

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _collect_plugin_names_from_ancestry(file_path: pathlib.Path) -> dict[str, set[str]]:
    """Walk upward from *file_path* collecting plugin names from plugin.json files.

    Returns a mapping of plugin_name -> set of server names declared in that
    plugin's mcpServers, so that plugin-namespaced tool names can be resolved.

    The Claude Code plugin MCP tool naming convention is:
        mcp__plugin_{plugin-name}_{server-name}__{tool-name}

    where ``plugin-name`` is the ``name`` field from ``.claude-plugin/plugin.json``
    and ``server-name`` is a key in ``mcpServers``.

    Args:
        file_path: Path to the file being scanned.

    Returns:
        Dict mapping plugin name strings to sets of server name strings.
    """
    plugin_server_map: dict[str, set[str]] = {}
    current = file_path.parent
    visited: set[pathlib.Path] = set()
    while current not in visited:
        visited.add(current)

        plugin_json = current / ".claude-plugin" / "plugin.json"
        if plugin_json.is_file():
            data = _read_json_file(plugin_json)
            if data is not None:
                plugin_name = data.get("name")
                if isinstance(plugin_name, str) and plugin_name:
                    server_keys = _extract_mcp_server_keys(data)
                    if plugin_name not in plugin_server_map:
                        plugin_server_map[plugin_name] = set()
                    plugin_server_map[plugin_name].update(server_keys)

        parent = current.parent
        if parent == current:
            break
        current = parent
    return plugin_server_map


def _collect_servers_from_ancestry(file_path: pathlib.Path) -> set[str]:
    """Walk upward from *file_path* collecting MCP server names from config files.

    Checks each ancestor directory for ``.mcp.json`` and
    ``.claude-plugin/plugin.json``, extracting ``mcpServers`` keys from each.

    Args:
        file_path: Path to the file being scanned.

    Returns:
        Set of MCP server names found in ancestor config files.
    """
    servers: set[str] = set()
    current = file_path.parent
    visited: set[pathlib.Path] = set()
    while current not in visited:
        visited.add(current)

        mcp_json = current / ".mcp.json"
        if mcp_json.is_file():
            data = _read_json_file(mcp_json)
            if data is not None:
                servers.update(_extract_mcp_server_keys(data))

        plugin_json = current / ".claude-plugin" / "plugin.json"
        if plugin_json.is_file():
            data = _read_json_file(plugin_json)
            if data is not None:
                servers.update(_extract_mcp_server_keys(data))

        parent = current.parent
        if parent == current:
            break
        current = parent
    return servers


def _collect_servers_from_frontmatter(file_path: pathlib.Path) -> set[str]:
    """Extract MCP server names declared inline in the agent/skill frontmatter.

    Args:
        file_path: Path to the agent or skill file.

    Returns:
        Set of MCP server names from the file's own ``mcpServers`` frontmatter
        key; empty set on parse failure or when the key is absent.
    """
    from skilllint.frontmatter_core import extract_frontmatter  # noqa: PLC0415
    from skilllint.plugin_validator import safe_load_yaml_with_colon_fix  # noqa: PLC0415

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError:
        return set()

    fm_text, _start, _end = extract_frontmatter(content)
    if fm_text is None:
        return set()

    parsed, _err, _colon_fields, _used = safe_load_yaml_with_colon_fix(fm_text)
    if isinstance(parsed, dict):
        return _extract_mcp_server_keys(parsed)
    return set()


def _resolve_plugin_namespaced_server(raw_segment: str, plugin_server_map: dict[str, set[str]]) -> tuple[str, str]:
    """Resolve the actual server name from a raw mcp__ segment, handling plugin-namespaced tools.

    Claude Code registers plugin MCP servers using:
        mcp__plugin_{plugin-name}_{server-name}__{tool-name}

    When the middle segment starts with ``plugin_``, this function strips the
    ``plugin_{plugin-name}_`` prefix to recover ``{server-name}``, then validates
    that the recovered name matches a server declared in that plugin's
    ``mcpServers``.  If the plugin name cannot be identified or the server is
    not found in the matched plugin, the full raw segment is returned unchanged
    so that normal discovery fallback handles it.

    Args:
        raw_segment: The ``parts[1]`` segment from splitting the tool name on
            ``__``.  For user-level tools this is just the server name; for
            plugin-level tools it is ``plugin_{plugin-name}_{server-name}``.
        plugin_server_map: Mapping of plugin name → set of server names,
            produced by ``_collect_plugin_names_from_ancestry``.

    Returns:
        A ``(server_name, prefix)`` tuple where ``server_name`` is the resolved
        server name (stripped of the plugin prefix when applicable) and
        ``prefix`` is the ``plugin_{plugin-name}_`` prefix string that was
        removed (empty string for user-level tools).  The prefix is needed so
        callers can reconstruct the full tool name for error messages.
    """
    plugin_pfx = "plugin_"
    if not raw_segment.startswith(plugin_pfx):
        return raw_segment, ""

    # raw_segment = "plugin_{plugin-name}_{server-name}"
    # We must identify which plugin name to strip.  Try each known plugin name
    # in order of descending length to avoid prefix ambiguity (e.g. plugin "dh"
    # vs plugin "dh_backlog").
    after_plugin = raw_segment[len(plugin_pfx) :]  # "{plugin-name}_{server-name}"
    plugin_names = sorted(plugin_server_map.keys(), key=str.__len__, reverse=True)
    for plugin_name in plugin_names:
        candidate_prefix = plugin_name + "_"
        if after_plugin.startswith(candidate_prefix):
            server_name = after_plugin[len(candidate_prefix) :]
            plugin_servers: set[str] = plugin_server_map[plugin_name]
            stripped_prefix = plugin_pfx + candidate_prefix
            if server_name in plugin_servers:
                # Exact match in this plugin's mcpServers — resolved
                return server_name, stripped_prefix
            # Plugin name matched but server not in its mcpServers.
            # Still strip the prefix so case-fold lookup can find it.
            return server_name, stripped_prefix

    # Could not identify plugin name — return raw segment for fallback handling
    return raw_segment, ""


def _discover_mcp_servers(file_path: pathlib.Path) -> set[str]:
    """Collect known MCP server names from project and plugin context.

    Combines results from:
    1. Ancestor ``.mcp.json`` files — keys of their ``mcpServers`` dicts.
    2. Ancestor ``.claude-plugin/plugin.json`` files — same.
    3. The scanned file's own frontmatter ``mcpServers`` key.

    Args:
        file_path: Path to the agent/skill file being scanned.

    Returns:
        Set of MCP server name strings (exact case as declared in config).
    """
    return _collect_servers_from_ancestry(file_path) | _collect_servers_from_frontmatter(file_path)


@skilllint_rule(
    "AS008",
    severity="warning",
    category="skill",
    authority={"origin": "agentskills.io", "reference": "/specification#tools-field"},
)
def _check_as008(tools: list[str], path: pathlib.Path) -> list[dict]:
    """AS008 — MCP tool name references an unknown or incorrectly-cased server.

    Discovers available MCP server names from ``.mcp.json``, ``plugin.json``,
    and agent frontmatter in the project context, then validates each
    ``mcp__{server}__{tool}`` entry against the discovered set.

    Three outcomes per tool:

    - **Exact match** against a discovered server → no violation.
    - **Case-insensitive match but case differs** (fuzzy match) → ERROR:
      the server exists but is referenced with wrong casing.
    - **No match** → WARNING: server not found in any config file; may be
      an external server that end users must configure.

    Args:
        tools: List of tool name strings from the tools: frontmatter field.
        path: Path to the SKILL.md or agent file being validated.

    Returns:
        List of violation dicts — one per tool with a case mismatch or unknown server.
    """
    known_servers = _discover_mcp_servers(path)
    # Build case-folded lookup: lowercase_name -> canonical_name
    lower_to_canonical: dict[str, str] = {s.lower(): s for s in known_servers}
    # Collect plugin-name -> server names map for plugin-namespaced tool resolution
    plugin_server_map = _collect_plugin_names_from_ancestry(path)

    violations: list[dict] = []
    for tool_name in tools:
        if not tool_name.startswith("mcp__"):
            continue

        parts = tool_name.split("__", 2)
        if len(parts) < 2:  # noqa: PLR2004
            continue
        raw_segment = parts[1]
        tool_suffix = parts[2] if len(parts) > 2 else ""  # noqa: PLR2004

        # Resolve the server name, handling the plugin-namespaced format:
        #   mcp__plugin_{plugin-name}_{server-name}__{tool}
        # In this format raw_segment = "plugin_{plugin-name}_{server-name}".
        # We must strip the "plugin_{plugin-name}_" prefix to get the actual
        # server name, then check it against that plugin's mcpServers.
        extracted_server, plugin_prefix = _resolve_plugin_namespaced_server(raw_segment, plugin_server_map)

        if extracted_server in known_servers:
            # Exact match — pass
            continue

        canonical = lower_to_canonical.get(extracted_server.lower())
        if canonical is not None:
            # Case mismatch with a discoverable server — error
            full_prefix = f"mcp__{plugin_prefix}{extracted_server}" if plugin_prefix else f"mcp__{extracted_server}"
            correct_prefix = f"mcp__{plugin_prefix}{canonical}" if plugin_prefix else f"mcp__{canonical}"
            violations.append(
                _make_violation(
                    "AS008",
                    "error",
                    f"MCP tool '{tool_name}' has a case mismatch with server '{canonical}'. "
                    "The tools: field is case-sensitive. "
                    f"Did you mean '{correct_prefix}__{tool_suffix}'?",
                    fix=f"Replace '{full_prefix}__' with '{correct_prefix}__'.",
                )
            )
        else:
            # Unknown server — warning.
            # Skip if the raw segment starts with "plugin_" but plugin_prefix is
            # empty: this means the tool is plugin-namespaced but the plugin isn't
            # in the local ancestry map.  That is expected for externally-installed
            # plugins and should not produce a violation.
            if raw_segment.startswith("plugin_") and not plugin_prefix:
                continue
            violations.append(
                _make_violation(
                    "AS008",
                    "warning",
                    f"MCP tool '{tool_name}' references server '{extracted_server}' which was not found "
                    "in this plugin or project's MCP configuration. "
                    "If this references an external MCP server that end users must configure, "
                    "suppress this warning.",
                )
            )

    return violations


@skilllint_rule(
    "AS006",
    severity="info",
    category="skill",
    authority={"origin": "agentskills.io", "reference": "/specification#evaluation-queries"},
)
def _check_as006(path: pathlib.Path) -> dict | None:
    """AS006 — No evaluation queries file found.

    Recommends adding an ``eval_queries.json`` file to the skill directory
    to enable automated quality assessment. The file should contain test
    queries that exercise the skill's functionality.

    Args:
        path: Path to the SKILL.md file being validated.

    Returns:
        Violation dict if no eval file found, None otherwise.

    Fix:
        Create ``eval_queries.json`` in the skill directory with test queries
        in JSON format.

    Note:
        This is an informational message, not an error. Skills work
        without evaluation queries, but they're recommended for quality
        assurance.
    """
    parent = path.parent

    # Check for eval_queries.json exact name first
    if (parent / "eval_queries.json").exists():
        return None

    # Check for any file matching *eval*.json or *queries*.json
    for f in parent.iterdir():
        if f.suffix == ".json":
            stem = f.stem.lower()
            if "eval" in stem or "queries" in stem:
                return None

    return _make_violation(
        "AS006",
        "info",
        "No eval_queries.json found in skill directory — add evaluation queries to enable automated quality assessment",
    )


def _find_plugin_json_in_ancestry(path: pathlib.Path) -> bool:
    """Return True if any ancestor directory contains a .claude-plugin/plugin.json file.

    Args:
        path: Path to the SKILL.md file being validated.

    Returns:
        True if a plugin.json is found in an ancestor, False otherwise.
    """
    current = path.parent
    visited: set[pathlib.Path] = set()
    while current not in visited:
        visited.add(current)
        if (current / ".claude-plugin" / "plugin.json").is_file():
            return True
        parent = current.parent
        if parent == current:
            break
        current = parent
    return False


def _count_levels_under_skills(path: pathlib.Path) -> int:
    """Count the number of directory levels between a skills/ directory and path.

    Walks up from path.parent until a directory named 'skills' is found.
    Returns the number of levels between the skills/ dir and the file.

    For ``skills/my-skill/SKILL.md`` the count is 1 (one level: my-skill/).
    For ``skills/cat/my-skill/SKILL.md`` the count is 2 (two levels: cat/my-skill/).

    Returns 0 if no ancestor named 'skills' is found.

    Args:
        path: Path to the SKILL.md file being validated.

    Returns:
        Number of directory levels between the skills/ ancestor and path.
    """
    parts = path.parts
    # Find the rightmost 'skills' directory in the path
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] == "skills":
            # levels = number of path components between skills/ and the file
            # path.parts[-1] is the filename (SKILL.md), so levels = len(parts) - i - 2
            return len(parts) - i - 2
    return 0


@skilllint_rule(
    "AS009",
    severity="warning",
    category="skill",
    authority={"origin": "anthropic.com", "reference": "https://docs.anthropic.com/en/docs/claude-code/skills"},
)
def _check_as009(path: pathlib.Path) -> dict | None:
    """AS009 — Nested skill will not be auto-discovered.

    Claude Code skills only support single-level namespacing. A SKILL.md must be
    a direct child of the ``skills/`` directory (e.g., ``skills/my-skill/SKILL.md``).
    If nested deeper (e.g., ``skills/category/my-skill/SKILL.md``), it will not be
    auto-discovered at runtime.

    In a plugin context (a ``plugin.json`` ancestor is present), the skill can be
    registered manually via the ``skills`` array in ``plugin.json``. In a user or
    project scope, the skill simply will not activate.

    Note: ``commands/`` subdirectories are valid for namespacing and are not affected
    by this rule.

    Args:
        path: Path to the SKILL.md file being validated.

    Returns:
        Violation dict if nested more than one level under skills/, None otherwise.

    Fix:
        Move the skill directory to ``skills/<skill-name>/SKILL.md``, or if inside
        a plugin, add the path to the ``skills`` array in ``plugin.json``.
    """
    levels = _count_levels_under_skills(path)
    if levels <= 1:
        return None

    in_plugin = _find_plugin_json_in_ancestry(path)
    if in_plugin:
        return _make_violation(
            "AS009",
            "warning",
            "Nested skill will not activate automatically — add its path to the plugin.json skills section",
            fix="Add the skill path to the 'skills' array in .claude-plugin/plugin.json",
        )
    return _make_violation(
        "AS009",
        "warning",
        "Nested skill will not activate in Claude Code",
        fix="Move the skill to skills/<skill-name>/SKILL.md (one level under skills/)",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_skill_md(path: pathlib.Path) -> list[dict]:
    """Run AS006-AS009 checks on a SKILL.md file.

    Reads and parses the file at the given path, then runs all AS-series
    rules. Returns a list of violation dicts; empty list means no issues.

    Args:
        path: Path to the SKILL.md file to validate.

    Returns:
        List of violation dicts, each with keys: code, severity, message.
        May include 'fix' key with auto-fix suggestion for AS008, AS009.
    """
    _frontmatter, _body_lines = _parse_skill_md(path)

    violations: list[dict] = []

    v = _check_as006(path)
    if v:
        violations.append(v)

    tools = _extract_tools_list(path)
    violations.extend(_check_as008(tools, path))

    v = _check_as009(path)
    if v:
        violations.append(v)

    return violations


# Alias for plan 02-02 spec compatibility (run_as_series is the plan name,
# check_skill_md is what the tests actually import).
def run_as_series(
    path: pathlib.Path,
    frontmatter: dict,
    body_lines: list[str],
    *,
    warning_threshold: int = TOKEN_WARNING_THRESHOLD,
    error_threshold: int = TOKEN_ERROR_THRESHOLD,
) -> list[dict]:
    """Run AS-series rules given pre-parsed frontmatter and body lines.

    This is a lower-level entry point for callers that have already parsed
    the frontmatter. check_skill_md() is preferred for file-based callers.

    Returns:
        List of violation dicts, each with keys: code, severity, message.
    """
    violations: list[dict] = []

    v = _check_as006(path)
    if v:
        violations.append(v)

    tools = _extract_tools_list(path)
    violations.extend(_check_as008(tools, path))

    v = _check_as009(path)
    if v:
        violations.append(v)

    return violations


__all__ = ["AS_RULES", "check_skill_md", "run_as_series"]
