"""AG-series rule validation for agents/*.md (Claude Code subagent) frontmatter.

Rules AG001-AG003 fire on agent files only. They enforce Claude Code's
sub-agents.md, the harness document that defines `agents/*.md` frontmatter —
the AgentSkills specification does not describe agent files at all (see
``as_series.py``'s module docstring), so a check on this frontmatter belongs
here, not in the AS family.

Entry points:
    check_ag001(frontmatter: dict) -> list[ValidationIssue]
    check_ag002(frontmatter: dict, path: Path) -> list[ValidationIssue]
    check_ag003(frontmatter: dict) -> list[ValidationIssue]

All three read the raw parsed frontmatter dict (pre-Pydantic-coercion) so a
YAML-list ``tools``/``skills`` value is inspected in its original shape.
``AgentFrontmatter`` (frontmatter_core.py) itself coerces list-valued
``tools``/``disallowedTools`` to a CSV string, which would otherwise hide the
exact violations AG001/AG002 exist to catch.

Severities:
    "error"   — AG001 (every tools entry provably resolves to nothing), AG003
                (skills is not a YAML list)
    "warning" — AG002 (default registry severity; individual findings are
                "error" for a case mismatch against a known server, "warning"
                when the server is not found in any discovered config)

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from skilllint.frontmatter_core import normalize_tools_value
from skilllint.rule_registry import rule_reference, skilllint_rule
from skilllint.rules._mcp_tool_discovery import (
    collect_plugin_names_from_ancestry,
    discover_mcp_servers,
    resolve_plugin_namespaced_server,
)

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

# .claude/vendor/sources/sub-agents-2026-08-30-0906.md
_SUBAGENTS_URL = "https://code.claude.com/docs/en/sub-agents.md"
# Line 416 of the cached doc: "Both fields accept MCP server-level patterns in
# addition to exact tool names: `mcp__<server>` or `mcp__<server>__*` grants or
# removes every tool from the named server." Line 414: "When nothing in the
# tools list resolves to a tool ... Claude Code usually refuses to launch the
# subagent and the Agent tool returns an error naming the unresolved entries."
_AVAILABLE_TOOLS_URL = f"{_SUBAGENTS_URL}#available-tools"
# Lines 532-546 of the cached doc: the `skills` field and its YAML-list example.
_PRELOAD_SKILLS_URL = f"{_SUBAGENTS_URL}#preload-skills-into-subagents"

# Source: sub-agents.md line 416 (cached doc, see _AVAILABLE_TOOLS_URL above) — the
# only documented wildcard shape that resolves is `mcp__<server>__*`, where <server>
# is a non-empty run of underscore-separated segments containing no `*`. Any other
# entry containing `*` (bare `*`, `mcp__*`, or a malformed pattern) names no server
# and, per the same page, contributes no tool.
_MCP_SERVER_GRANT_RE = re.compile(r"^mcp__[^*_]+(?:_[^*_]+)*__\*$")

# Fields sub-agents.md defines for MCP tool grants/denials on an agent file.
# Source: sub-agents.md "Supported frontmatter fields" table (cached doc lines
# 294, 296) — `tools` and `disallowedTools`.
_AGENT_TOOL_FIELD_NAMES: tuple[str, ...] = ("tools", "disallowedTools")


def _make_issue(
    *, field: str, severity: Literal["error", "warning", "info"], message: str, code: str, suggestion: str | None = None
) -> ValidationIssue:
    """Construct a ValidationIssue for an AG rule.

    Args:
        field: Frontmatter field name (``tools``, ``disallowedTools``, or ``skills``).
        severity: Issue severity.
        message: Human-readable description.
        code: Rule code (e.g. "AG001").
        suggestion: Optional repair hint.

    Returns:
        A frozen ValidationIssue instance.
    """
    # Deferred import to break the circular dependency: plugin_validator
    # imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    return ValidationIssue(
        field=field, severity=severity, message=message, code=code, docs_url=rule_reference(code), suggestion=suggestion
    )


# ---------------------------------------------------------------------------
# AG001 — `tools` field resolves to no tool
# ---------------------------------------------------------------------------


@skilllint_rule(
    "AG001",
    severity="error",
    category="agent",
    authority={"origin": "code.claude.com", "reference": _AVAILABLE_TOOLS_URL},
)
def check_ag001(frontmatter: dict) -> list[ValidationIssue]:
    """## AG001 — `tools` field resolves to no tool

    Every entry in the agent's `tools` field is an unscoped wildcard that
    names no MCP server. A *server-scoped* grant such as `mcp__Ref__*` is
    supported and NOT reported here — Claude Code resolves it to every tool
    that server exposes, identically to the bare `mcp__Ref` form. An
    *unscoped* wildcard (bare `*`, or `mcp__*` naming no server) has no
    documented meaning in this field.

    This only fires when **every** entry is provably unresolvable. A single
    unscoped wildcard alongside an ordinary tool name (`Read`, `mcp__Ref__*`)
    is not reported: skilllint has no registry of live tool names, so it
    cannot prove the sibling entry fails to resolve too.

    **Source:** sub-agents.md, "Available tools" — "When nothing in the
    `tools` list resolves to a tool ... Claude Code usually refuses to launch
    the subagent and the Agent tool returns an error naming the unresolved
    entries." Same section: "`mcp__<server>` or `mcp__<server>__*` grants ...
    every tool from the named server."

    **Fix:** Replace each wildcard with a server-scoped grant (e.g.
    `mcp__Ref__*`) or the exact tool names, or remove `tools` entirely to
    inherit the default set.

    Args:
        frontmatter: Raw parsed agent frontmatter dict (pre-Pydantic).

    Returns:
        One error issue per unscoped wildcard entry when every entry in
        `tools` is unresolvable; empty list otherwise, including when
        `tools` is absent, blank, or an empty list.

    <!-- examples: AG001 -->
    """
    tools = normalize_tools_value(frontmatter.get("tools"))
    if not tools:
        return []

    unscoped = [t for t in tools if "*" in t and not _MCP_SERVER_GRANT_RE.match(t)]
    if not unscoped or len(unscoped) != len(tools):
        # Not fatal: either no wildcard is present, or at least one entry is
        # not a provable-unresolvable wildcard and may resolve to a real tool.
        return []

    return [
        _make_issue(
            field="tools",
            severity="error",
            message=(
                f"Unscoped wildcard '{tool_name}' in the tools field names no server. Every entry in tools "
                "resolves to nothing, so Claude Code will refuse to launch this subagent."
            ),
            code="AG001",
            suggestion=(
                f"Replace '{tool_name}' with a server-scoped grant (e.g. 'mcp__Ref__*'), the exact tool "
                "names (e.g. 'mcp__Ref__ref_read_url'), or remove 'tools' to inherit the default set."
            ),
        )
        for tool_name in unscoped
    ]


# ---------------------------------------------------------------------------
# AG002 — MCP tool name references an unknown or incorrectly-cased server
# ---------------------------------------------------------------------------


@skilllint_rule(
    "AG002",
    severity="warning",
    category="agent",
    authority={"origin": "code.claude.com", "reference": _AVAILABLE_TOOLS_URL},
)
def check_ag002(frontmatter: dict, path: Path) -> list[ValidationIssue]:
    """## AG002 — MCP tool name references an unknown or incorrectly-cased server

    Discovers available MCP server names from `.mcp.json`, `plugin.json`, and
    the agent's own frontmatter, then validates each `mcp__{server}[__{tool}]`
    entry in `tools` and `disallowedTools` against the discovered set.

    Three outcomes per entry:

    - **Exact match** against a discovered server → no violation.
    - **Case-insensitive match but case differs** → ERROR: the server exists
      but is referenced with the wrong casing.
    - **No match** → WARNING: server not found in any discovered config; may
      be an external server that end users must configure.

    Unscoped wildcard entries (`mcp__*`) name no server to look up and are
    AG001's concern, not this rule's — they are skipped here.

    **Source:** sub-agents.md, "Available tools" — "`mcp__<server>` or
    `mcp__<server>__*` grants or removes every tool from the named server."
    Server names come from configured `mcpServers` keys, which are matched
    exactly as declared.

    **Fix:** Correct the server segment to match the discovered server's
    exact casing.

    Args:
        frontmatter: Raw parsed agent frontmatter dict (pre-Pydantic).
        path: Path to the agent file being validated (used to discover MCP
            server configuration in ancestor directories).

    Returns:
        List of violation dicts — one per tool entry with a case mismatch or
        unknown server.

    <!-- examples: AG002 -->
    """
    field_tools = {
        field_name: normalize_tools_value(frontmatter.get(field_name)) for field_name in _AGENT_TOOL_FIELD_NAMES
    }
    if not any(field_tools.values()):
        return []

    known_servers = discover_mcp_servers(path)
    lower_to_canonical: dict[str, str] = {s.lower(): s for s in known_servers}
    plugin_server_map = collect_plugin_names_from_ancestry(path)

    issues: list[ValidationIssue] = []
    for field_name, tools in field_tools.items():
        for tool_name in tools:
            if not tool_name.startswith("mcp__"):
                continue

            parts = tool_name.split("__", 2)
            if len(parts) < 2:  # noqa: PLR2004
                continue
            raw_segment = parts[1]
            tool_suffix = parts[2] if len(parts) > 2 else ""  # noqa: PLR2004

            if "*" in raw_segment:
                # Unscoped wildcard (mcp__*) or malformed pattern — no server
                # name to look up; AG001's territory, not this rule's.
                continue

            extracted_server, plugin_prefix = resolve_plugin_namespaced_server(raw_segment, plugin_server_map)

            if extracted_server in known_servers:
                continue

            canonical = lower_to_canonical.get(extracted_server.lower())
            if canonical is not None:
                full_prefix = f"mcp__{plugin_prefix}{extracted_server}" if plugin_prefix else f"mcp__{extracted_server}"
                correct_prefix = f"mcp__{plugin_prefix}{canonical}" if plugin_prefix else f"mcp__{canonical}"
                issues.append(
                    _make_issue(
                        field=field_name,
                        severity="error",
                        message=(
                            f"MCP tool '{tool_name}' has a case mismatch with server '{canonical}'. "
                            f"Did you mean '{correct_prefix}__{tool_suffix}'?"
                        ),
                        code="AG002",
                        suggestion=f"Replace '{full_prefix}__' with '{correct_prefix}__'.",
                    )
                )
            else:
                # Plugin-namespaced but the plugin isn't in the local ancestry
                # map — expected for externally-installed plugins, not a violation.
                if raw_segment.startswith("plugin_") and not plugin_prefix:
                    continue
                issues.append(
                    _make_issue(
                        field=field_name,
                        severity="warning",
                        message=(
                            f"MCP tool '{tool_name}' references server '{extracted_server}' which was not found "
                            "in this agent's or project's MCP configuration. If this references an external "
                            "MCP server that end users must configure, this may be expected."
                        ),
                        code="AG002",
                    )
                )

    return issues


# ---------------------------------------------------------------------------
# AG003 — `skills` field is not a YAML list
# ---------------------------------------------------------------------------


@skilllint_rule(
    "AG003",
    severity="error",
    category="agent",
    authority={"origin": "code.claude.com", "reference": _PRELOAD_SKILLS_URL},
)
def check_ag003(frontmatter: dict) -> list[ValidationIssue]:
    """## AG003 — `skills` field is not a YAML list

    The `skills` field preloads named skills into the subagent's context at
    startup. Its only documented shape is a YAML list of skill names.

    **Source:** sub-agents.md, "Preload skills into subagents" — the field's
    sole example is:

    ```yaml
    skills:
      - api-conventions
      - error-handling-patterns
    ```

    Unlike `tools`, the specification gives no inline-string form for this
    field. `AgentFrontmatter.skills` (frontmatter_core.py) declares the field
    as `list[str] | None` and does not coerce other shapes, so a malformed
    value also raises a generic Pydantic error; this rule replaces that
    generic message with one citing the field's actual authority.

    **Fix:** Rewrite `skills` as a YAML list.

    Args:
        frontmatter: Raw parsed agent frontmatter dict (pre-Pydantic).

    Returns:
        One error issue when `skills` is present and not a list; empty list
        when absent or already a list.

    <!-- examples: AG003 -->
    """
    value = frontmatter.get("skills")
    if value is None or isinstance(value, list):
        return []

    return [
        _make_issue(
            field="skills",
            severity="error",
            message="`skills` must be a YAML list of skill names to preload, not a scalar or mapping value",
            code="AG003",
            suggestion="Rewrite as a YAML list, e.g.:\nskills:\n  - api-conventions\n  - error-handling-patterns",
        )
    ]


__all__ = ["check_ag001", "check_ag002", "check_ag003"]
