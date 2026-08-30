"""Shared MCP server-name discovery for tool-declaring frontmatter fields.

Extracted from ``as_series.py`` (AS008) so the same discovery logic can back
``ag_series.py`` (AG002) without a second, independently-drifting
implementation of plugin-namespace resolution. Both rules discover MCP server
names the same way regardless of which field or file type they inspect; only
what they do with the result (violation shape, authority, message wording)
differs, and that stays in each rule module.

Entry points:
    discover_mcp_servers(file_path) -> set[str]
    analyze_mcp_tool_reference(...) -> McpReferenceAnalysis | None
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import pathlib


@dataclass(frozen=True)
class McpReferenceAnalysis:
    """Pure classification of one MCP tool/server reference.

    ``replacement_source`` and ``replacement_target`` are server prefixes for
    qualified references and complete references for bare server grants. This
    lets callers retain their own diagnostic wording without inventing a
    dangling ``__`` for ``mcp__server``.
    """

    reference: str
    server_name: str
    status: Literal["exact", "case-mismatch", "unknown", "unscoped"]
    canonical_server: str | None = None
    corrected_reference: str | None = None
    replacement_source: str | None = None
    replacement_target: str | None = None


def _read_json_file(path: pathlib.Path) -> dict[str, object] | None:
    """Read and parse a JSON file, returning a dict or None on failure.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed dict, or None if the file is missing, unreadable, or not a dict.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


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


def collect_plugin_names_from_ancestry(file_path: pathlib.Path) -> dict[str, set[str]]:
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


def _is_plugin_packaged_agent(file_path: pathlib.Path) -> bool:
    """Return True when *file_path* is a plugin's own ``agents/*.md`` file.

    Mirrors PA001's definition of a plugin-packaged agent
    (``PluginAgentFrontmatterValidator`` in ``plugin_validator.py``: a direct
    child of ``<plugin_root>/agents/``). ``pa_series.py`` documents that
    Claude Code ignores ``mcpServers`` in such a file's own frontmatter when
    loading it from a plugin, so that field must not seed server discovery.

    Args:
        file_path: Path to the agent or skill file.

    Returns:
        True if *file_path* is a direct child of a plugin's ``agents/`` directory.
    """
    from skilllint.plugin_validator import find_plugin_dir  # noqa: PLC0415

    plugin_dir = find_plugin_dir(file_path)
    if plugin_dir is None:
        return False
    return file_path.parent == plugin_dir / "agents"


def _collect_servers_from_frontmatter(file_path: pathlib.Path) -> set[str]:
    """Extract MCP server names declared inline in the agent/skill frontmatter.

    Args:
        file_path: Path to the agent or skill file.

    Returns:
        Set of MCP server names from the file's own ``mcpServers`` frontmatter
        key; empty set on parse failure, when the key is absent, or when
        *file_path* is a plugin-packaged agent (see ``_is_plugin_packaged_agent``)
        whose inline ``mcpServers`` the runtime ignores.
    """
    if _is_plugin_packaged_agent(file_path):
        return set()

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


def resolve_plugin_namespaced_server(
    raw_segment: str, plugin_server_map: dict[str, set[str]]
) -> tuple[str, str, frozenset[str] | None]:
    """Resolve the actual server name from a raw mcp__ segment, handling plugin-namespaced tools.

    Claude Code registers plugin MCP servers using:
        mcp__plugin_{plugin-name}_{server-name}__{tool-name}

    When the middle segment starts with ``plugin_``, this function strips the
    ``plugin_{plugin-name}_`` prefix to recover ``{server-name}``. If the
    plugin name cannot be identified, the full raw segment is returned
    unchanged so the caller's normal (global) discovery fallback handles it.

    Args:
        raw_segment: The ``parts[1]`` segment from splitting the tool name on
            ``__``.  For user-level tools this is just the server name; for
            plugin-level tools it is ``plugin_{plugin-name}_{server-name}``.
        plugin_server_map: Mapping of plugin name → set of server names,
            produced by ``collect_plugin_names_from_ancestry``.

    Returns:
        A ``(server_name, prefix, plugin_servers)`` tuple. ``server_name`` is
        the resolved server name (stripped of the plugin prefix when
        applicable); ``prefix`` is the ``plugin_{plugin-name}_`` prefix string
        that was removed (empty string for user-level tools, needed so
        callers can reconstruct the full tool name for error messages).
        ``plugin_servers`` is the identified plugin's *own* server set when a
        known plugin namespace was matched, or ``None`` for a user-level
        reference or an unrecognized namespace. Callers must resolve
        membership and casing against ``plugin_servers`` (when not ``None``)
        instead of the global known-servers set: a same-named server exposed
        by a *different* plugin or by project-level config must not produce a
        false accept for a namespace this plugin does not itself declare.
    """
    plugin_pfx = "plugin_"
    if not raw_segment.startswith(plugin_pfx):
        return raw_segment, "", None

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
            stripped_prefix = plugin_pfx + candidate_prefix
            # Always scoped to this plugin's own servers, matched or not: the
            # caller must never fall back to the global set for a namespace
            # this plugin claims, or a same-named server from elsewhere
            # would silently resolve it.
            return server_name, stripped_prefix, frozenset(plugin_server_map[plugin_name])

    # Could not identify plugin name — return raw segment for global fallback handling
    return raw_segment, "", None


def _split_mcp_reference(reference: str) -> tuple[str, str | None] | None:
    """Split an MCP tool reference into its server segment and optional suffix.

    Args:
        reference: Authored tool or bare server-grant name.

    Returns:
        ``(raw_segment, suffix)`` for a well-formed ``mcp__<segment>[__<suffix>]``
        reference, or ``None`` when *reference* is not an MCP name or its
        server segment is empty.
    """
    if not reference.startswith("mcp__"):
        return None
    parts = reference.split("__", 2)
    raw_segment = parts[1]
    if not raw_segment:
        return None
    suffix = parts[2] if len(parts) > 2 else None  # noqa: PLR2004
    return raw_segment, suffix


def analyze_mcp_tool_reference(
    reference: str, known_servers: set[str], plugin_server_map: dict[str, set[str]]
) -> McpReferenceAnalysis | None:
    """Classify a tool reference against discovered MCP server names.

    Non-MCP names, empty server segments, and references to
    externally-installed plugin namespaces are outside the casing rules'
    scope and return ``None``. An unscoped wildcard server segment
    (``mcp__*``) is classified as ``"unscoped"`` rather than skipped here:
    whether that is worth reporting is a per-caller decision. AS008
    (``SKILL.md``) has no separate "resolves to nothing" rule and must still
    flag it, as it did before this module existed; AG002 (agent files) skips
    it, because AG001 already owns that diagnostic there. All other MCP
    references are classified as an exact match, case mismatch, or unknown
    server.

    Args:
        reference: Authored tool or bare server-grant name.
        known_servers: Exact server names discovered from applicable config.
        plugin_server_map: Plugin-name to MCP-server mapping used to remove a
            locally resolvable ``plugin_{name}_`` namespace.

    Returns:
        Immutable analysis data, or ``None`` when casing rules should skip the
        reference.
    """
    split = _split_mcp_reference(reference)
    if split is None:
        return None
    raw_segment, suffix = split

    if "*" in raw_segment:
        return McpReferenceAnalysis(reference=reference, server_name=raw_segment, status="unscoped")

    server_name, plugin_prefix, plugin_servers = resolve_plugin_namespaced_server(raw_segment, plugin_server_map)
    original_prefix = f"mcp__{plugin_prefix}{server_name}"
    # A recognized plugin namespace is scoped to that plugin's own servers
    # only -- never the global set, or a same-named server exposed by a
    # different plugin or by project config would false-accept this reference.
    scope = plugin_servers if plugin_servers is not None else known_servers
    if server_name in scope:
        return McpReferenceAnalysis(reference=reference, server_name=server_name, status="exact")

    lower_to_canonical = {known.lower(): known for known in scope}
    canonical_server = lower_to_canonical.get(server_name.lower())
    if canonical_server is None:
        if raw_segment.startswith("plugin_") and not plugin_prefix:
            # The plugin is not installed in the local ancestry. Claude Code
            # may resolve it externally, so there is no local casing claim.
            return None
        return McpReferenceAnalysis(reference=reference, server_name=server_name, status="unknown")

    corrected_prefix = f"mcp__{plugin_prefix}{canonical_server}"
    if suffix is None:
        corrected_reference = corrected_prefix
        replacement_source = original_prefix
        replacement_target = corrected_prefix
    else:
        corrected_reference = f"{corrected_prefix}__{suffix}"
        replacement_source = f"{original_prefix}__"
        replacement_target = f"{corrected_prefix}__"

    return McpReferenceAnalysis(
        reference=reference,
        server_name=server_name,
        status="case-mismatch",
        canonical_server=canonical_server,
        corrected_reference=corrected_reference,
        replacement_source=replacement_source,
        replacement_target=replacement_target,
    )


def discover_mcp_servers(file_path: pathlib.Path) -> set[str]:
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


__all__ = [
    "McpReferenceAnalysis",
    "analyze_mcp_tool_reference",
    "collect_plugin_names_from_ancestry",
    "discover_mcp_servers",
    "resolve_plugin_namespaced_server",
]
