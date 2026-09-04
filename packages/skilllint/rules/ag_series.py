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

from typing import TYPE_CHECKING

from skilllint.frontmatter_core import normalize_tools_value
from skilllint.rule_registry import _make_issue, skilllint_rule
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

# Source: the "Available tools" section above states two concrete facts about
# `mcp__*`-shaped entries: (1) the only documented resolving wildcard is
# `mcp__<server>__*` with a non-empty, real server name -- `mcp__*` matches
# neither that nor the bare `mcp__<server>` grant, so it names no server; and
# (2) `mcp__*` has a *different*, defined meaning in `disallowedTools` only
# ("also removes every MCP tool from any server"), which the same paragraph
# withholds from `tools`. No other wildcard-bearing form (e.g. a bare `*`, or
# a non-mcp token like `Bash(git:*)`) is established by this page to fail;
# treating "undocumented" as "provably unresolvable" would be an invented
# constraint, so only this exact literal is treated as fatal.
_UNRESOLVABLE_WILDCARD_TOOLS: frozenset[str] = frozenset({"mcp__*"})

# Source: sub-agents.md, "Available tools" -- "The first filter removes these
# tools, even when listed in the `tools` field:" (.claude/vendor/sources/
# sub-agents-2026-08-30-1123.md:374-384). Every subagent, foreground or
# background, unconditionally loses these tool names regardless of what
# `tools` lists. Two names from that same bullet list are deliberately
# excluded because their removal is conditional, not provable from
# frontmatter alone: `Agent` is removed only when the subagent is at the
# depth limit, and `ExitPlanMode` is removed unless `permissionMode` is
# `plan` (a case AG001 cannot rule out without also inspecting that field).
_UNCONDITIONALLY_REMOVED_TOOLS: frozenset[str] = frozenset({
    "AskUserQuestion",
    "EndConversation",
    "EnterPlanMode",
    "ScheduleWakeup",
    "TaskOutput",
    "WaitForMcpServers",
    "Workflow",
})

# The full provable-zero set: an entry in `tools` is provably non-functional
# when it either names no server (an unresolvable wildcard) or is stripped by
# the first filter before the subagent ever sees it (unconditionally removed).
_PROVABLY_ZERO_TOOLS: frozenset[str] = _UNRESOLVABLE_WILDCARD_TOOLS | _UNCONDITIONALLY_REMOVED_TOOLS

# Fields the "Supported frontmatter fields" table defines for MCP tool
# grants/denials on an agent file.
_AGENT_TOOL_FIELD_NAMES: tuple[str, ...] = ("tools", "disallowedTools")


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

    Every entry in the agent's `tools` field is provably non-functional, by
    one of two documented mechanisms:

    - **Unscoped wildcard.** The literal string `mcp__*`, which names no MCP
      server. A *server-scoped* grant such as `mcp__Ref__*` is supported and
      NOT reported here — Claude Code resolves it to every tool that server
      exposes, identically to the bare `mcp__Ref` form.
    - **Unconditionally removed.** One of `AskUserQuestion`,
      `EndConversation`, `EnterPlanMode`, `ScheduleWakeup`, `TaskOutput`,
      `WaitForMcpServers`, or `Workflow` — Claude Code's first tool filter
      strips these from every subagent regardless of what `tools` lists, so
      listing one has no effect.

    Both checks are deliberately narrow. For the wildcard case: no other
    wildcard-bearing token — a bare `*`, or a non-MCP form like
    `Bash(git:*)` — is established by sub-agents.md to fail; the absence of a
    documented *resolving* meaning for a token is not proof it is *invalid*,
    and asserting otherwise would be an unsourced constraint (see the AS007
    rule #108 deleted for the same reason). For the removed-tools case: two
    names from the same documented list are deliberately excluded because
    their removal is conditional, not provable from frontmatter alone —
    `Agent` (removed only at the subagent depth limit) and `ExitPlanMode`
    (removed unless `permissionMode` is `plan`).

    This only fires when **every** entry in `tools` is provably
    non-functional. A single such entry alongside an ordinary tool name
    (`Read`, `mcp__Ref__*`) is not reported: skilllint has no registry of
    live tool names, so it cannot prove the sibling entry fails to resolve
    too.

    **Source (wildcard):** sub-agents.md, "Available tools" — "When nothing
    in the `tools` list resolves to a tool ... Claude Code usually refuses to
    launch the subagent and the Agent tool returns an error naming the
    unresolved entries." Same section, same paragraph: "`mcp__<server>` or
    `mcp__<server>__*` grants or removes every tool from the named server. In
    `disallowedTools`, `mcp__*` also removes every MCP tool from any server."
    `mcp__*` is therefore defined *only* for `disallowedTools`; in `tools` it
    matches neither documented grant pattern (a real server name is required)
    and so names no server there.

    **Source (removed tools):** sub-agents.md, "Available tools" — "The
    first filter removes these tools, even when listed in the `tools`
    field:" followed by the bullet list naming the seven tools above (plus
    the two conditional exclusions).

    **Fix:** Replace the offending entry with a server-scoped grant (e.g.
    `mcp__Ref__*`), an exact tool name that the first filter does not strip,
    or remove `tools` entirely to inherit the default set.

    Args:
        frontmatter: Raw parsed agent frontmatter dict (pre-Pydantic).

    Returns:
        One error issue per provably non-functional entry when every entry
        in `tools` is provably non-functional; empty list otherwise,
        including when `tools` is absent, blank, or an empty list.

    <!-- examples: AG001 -->
    """
    tools = normalize_tools_value(frontmatter.get("tools"))
    if not tools:
        return []

    provably_zero = [t for t in tools if t in _PROVABLY_ZERO_TOOLS]
    if not provably_zero or len(provably_zero) != len(tools):
        # Not fatal: either no provably non-functional entry is present, or
        # at least one entry is not one and may resolve to a real tool.
        return []

    issues: list[ValidationIssue] = []
    for tool_name in provably_zero:
        if tool_name in _UNRESOLVABLE_WILDCARD_TOOLS:
            message = (
                f"Unscoped wildcard '{tool_name}' in the tools field names no server. Every entry in tools "
                "resolves to nothing, so Claude Code will refuse to launch this subagent."
            )
            suggestion = (
                f"Replace '{tool_name}' with a server-scoped grant (e.g. 'mcp__Ref__*'), the exact tool "
                "names (e.g. 'mcp__Ref__ref_read_url'), or remove 'tools' entirely to inherit the default set."
            )
        else:
            message = (
                f"'{tool_name}' in the tools field is unconditionally removed by Claude Code's first tool "
                "filter. Every entry in tools resolves to nothing, so Claude Code will refuse to launch "
                "this subagent."
            )
            suggestion = f"Remove '{tool_name}' from tools, or remove 'tools' entirely to inherit the default set."
        issues.append(
            _make_issue(field="tools", severity="error", message=message, code="AG001", suggestion=suggestion)
        )
    return issues


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
            if analysis is None or analysis.status in {"exact", "unscoped"}:
                # "unscoped" (mcp__*) is AG001's diagnostic, not this rule's.
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
