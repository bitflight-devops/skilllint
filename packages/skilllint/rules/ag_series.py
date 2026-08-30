"""AG-series rule validation for agents/*.md (Claude Code subagent) frontmatter.

Rules AG001-AG003 fire on agent files only. AG001/AG002 enforce Claude Code's
subagents documentation; AG003 follows the pinned filesystem-loader contract
recorded in ``docs/runtime-contracts``. The AgentSkills specification does not
describe agent files at all (see ``as_series.py``'s module docstring), so these
checks belong here rather than in the AS family.

Entry points:
    check_ag001(frontmatter: dict) -> list[ValidationIssue]
    check_ag002(frontmatter: dict, path: Path) -> list[ValidationIssue]
    check_ag003(frontmatter: dict) -> list[ValidationIssue]

All three read the raw parsed frontmatter dict (pre-Pydantic-coercion) so
list-valued ``tools``/``skills`` fields are inspected in their original shape.
``AgentFrontmatter`` (frontmatter_core.py) itself coerces list-valued
``tools``/``disallowedTools`` to a CSV string, which would otherwise hide the
exact violations AG001/AG002 exist to catch.

Severities:
    "error"   — AG001 (every tools entry provably resolves to nothing)
    "warning" — AG002 (default registry severity; individual findings are
                "error" for a case mismatch against a known server, "warning"
                when the server is not found in any discovered config), AG003
                (Claude Code ignores a non-string skills value/member)

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
    analyze_mcp_tool_reference,
    collect_plugin_names_from_ancestry,
    discover_mcp_servers,
)

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

_SUBAGENTS_URL = "https://code.claude.com/docs/en/sub-agents"
# The "Available tools" section defines `mcp__<server>` and
# `mcp__<server>__*` server grants and describes the launch failure when no
# entry resolves.
_AVAILABLE_TOOLS_URL = f"{_SUBAGENTS_URL}#available-tools"

# Source: the "Available tools" section above. The documented wildcard shape
# is `mcp__<server>__*`, where <server> is a non-empty run of
# underscore-separated segments containing no `*`.
_MCP_SERVER_GRANT_RE = re.compile(r"^mcp__[^*_]+(?:_[^*_]+)*__\*$")

# Fields the "Supported frontmatter fields" table defines for MCP tool
# grants/denials on an agent file.
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
    platforms=["claude-code"],
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
    platforms=["claude-code"],
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
    plugin_server_map = collect_plugin_names_from_ancestry(path)

    issues: list[ValidationIssue] = []
    for field_name, tools in field_tools.items():
        for tool_name in tools:
            analysis = analyze_mcp_tool_reference(tool_name, known_servers, plugin_server_map)
            if analysis is None or analysis.status == "exact":
                continue
            if analysis.status == "case-mismatch":
                canonical = analysis.canonical_server
                corrected_reference = analysis.corrected_reference
                replacement_source = analysis.replacement_source
                replacement_target = analysis.replacement_target
                if (
                    canonical is not None
                    and corrected_reference is not None
                    and replacement_source is not None
                    and replacement_target is not None
                ):
                    issues.append(
                        _make_issue(
                            field=field_name,
                            severity="error",
                            message=(
                                f"MCP tool '{tool_name}' has a case mismatch with server '{canonical}'. "
                                f"Did you mean '{corrected_reference}'?"
                            ),
                            code="AG002",
                            suggestion=f"Replace '{replacement_source}' with '{replacement_target}'.",
                        )
                    )
            else:
                issues.append(
                    _make_issue(
                        field=field_name,
                        severity="warning",
                        message=(
                            f"MCP tool '{tool_name}' references server '{analysis.server_name}' which was not found "
                            "in this agent's or project's MCP configuration. If this references an external "
                            "MCP server that end users must configure, this may be expected."
                        ),
                        code="AG002",
                    )
                )

    return issues


# ---------------------------------------------------------------------------
# AG003 — `skills` contains a value Claude Code ignores
# ---------------------------------------------------------------------------


@skilllint_rule(
    "AG003",
    severity="warning",
    category="agent",
    platforms=["claude-code"],
    authority={
        "origin": "@anthropic-ai/claude-code",
        "reference": "https://www.npmjs.com/package/@anthropic-ai/claude-code/v/2.1.251",
    },
)
def check_ag003(frontmatter: dict) -> list[ValidationIssue]:
    """## AG003 — `skills` contains a value Claude Code ignores

    The `skills` field preloads named skills into the subagent's context at
    startup. Claude Code accepts either a scalar string or a list and exposes a
    normalized list to the agent. Non-string scalar values normalize to an
    empty list; non-string members of a list are silently discarded.

    **Sources:** The subagents documentation's "Preload skills into
    subagents" section provides the field semantics and canonical list form:

    ```yaml
    skills:
      - api-conventions
      - error-handling-patterns
    ```

    Scalar acceptance and discard behavior are verified against the published
    Claude Code 2.1.251 filesystem loader:
    ``https://www.npmjs.com/package/@anthropic-ai/claude-code/v/2.1.251``.

    **Fix:** Replace unsupported values with string skill references. This is
    intentionally advisory and is not auto-fixed because discarding or
    stringifying authored YAML could change intent.

    Args:
        frontmatter: Raw parsed agent frontmatter dict (pre-Pydantic).

    Returns:
        One warning when an unsupported scalar/mapping is present or a list
        contains at least one non-string member. Empty list for accepted
        strings, all-string lists, null, and an absent field.

    <!-- examples: AG003 -->
    """
    value = frontmatter.get("skills")
    if value is None or isinstance(value, str):
        return []
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return []

    if isinstance(value, list):
        ignored_count = sum(not isinstance(item, str) for item in value)
        message = (
            f"`skills` contains {ignored_count} non-string member(s) that Claude Code discards; "
            "string members continue through runtime normalization"
        )
        suggestion = "Remove the non-string members or replace them with the intended skill name strings"
    else:
        message = "Claude Code discards this non-string `skills` value and preloads no skills from it"
        suggestion = "Replace the value with a skill name string or a list of skill name strings"

    return [_make_issue(field="skills", severity="warning", message=message, code="AG003", suggestion=suggestion)]


__all__ = ["check_ag001", "check_ag002", "check_ag003"]
