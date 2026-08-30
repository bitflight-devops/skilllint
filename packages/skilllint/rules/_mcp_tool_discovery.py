"""Shared MCP server-name discovery for tool-declaring frontmatter fields.

Extracted from ``as_series.py`` (AS008) so the same discovery logic can back
``ag_series.py`` (AG002) without a second, independently-drifting
implementation of plugin-namespace resolution. Both rules discover MCP server
names the same way regardless of which field or file type they inspect; only
what they do with the result (violation shape, authority, message wording)
differs, and that stays in each rule module.

Entry point: discover_mcp_servers(file_path) -> set[str]
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib


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


def resolve_plugin_namespaced_server(raw_segment: str, plugin_server_map: dict[str, set[str]]) -> tuple[str, str]:
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
            produced by ``collect_plugin_names_from_ancestry``.

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


__all__ = ["collect_plugin_names_from_ancestry", "discover_mcp_servers", "resolve_plugin_namespaced_server"]
