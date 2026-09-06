"""AS-series rule validation for agentskills.io SKILL.md files.

Rules AS001 and AS006-AS009 fire on SKILL.md files only, regardless of which platform
adapter is active. They enforce the AgentSkills specification, a cross-harness
baseline that defines SKILL.md and does not describe agent files. A check on
agent frontmatter belongs to a series that governs agent files, cited to the
harness documentation that defines them — not here. That series is ``ag_series.py``.

Entry point: check_skill_md(path: Path) -> list[dict]

Each violation dict has the shape:
    {"code": str, "severity": str, "message": str}

Severities:
    "error"   — AS001
    "warning" — AS008, AS009
    "info"    — AS006
"""

from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING

from skilllint.frontmatter_core import normalize_tools_value
from skilllint.rule_registry import rule_authority, skilllint_rule
from skilllint.rules._mcp_tool_discovery import (
    analyze_mcp_tool_reference,
    collect_plugin_names_from_ancestry,
    discover_mcp_servers,
)
from skilllint.token_counter import TOKEN_ERROR_THRESHOLD, TOKEN_WARNING_THRESHOLD

if TYPE_CHECKING:
    import pathlib

_logger = logging.getLogger(__name__)

# AS006 authority: agentskills.io/specification.md has no eval-related
# section (re-verified via `skilllint docs fetch` — zero matches for
# "eval" in the full spec text). The real agentskills.io coverage of this
# concept lives on a sibling page, skill-creation/evaluating-skills.md,
# "Designing test cases" section, which states verbatim: "Store test
# cases in `evals/evals.json` inside your skill directory."
_AS006_EVALS_URL = "https://agentskills.io/skill-creation/evaluating-skills.md#designing-test-cases"

# ---------------------------------------------------------------------------
# Rule registry — maps code to human-readable description
# ---------------------------------------------------------------------------

AS_RULES: dict[str, str] = {
    "AS001": "SKILL.md must declare a name field",
    "AS006": "No eval_queries.json or evals/evals.json found — add evaluation queries for quality assurance",
    "AS008": "MCP tool name may have incorrect casing — case is sensitive in the tools field",
    "AS009": "Nested skill will not be auto-discovered — skills must be direct children of the skills/ directory",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_skill_md(path: pathlib.Path) -> tuple[dict, list[str]]:
    """Parse a SKILL.md file into frontmatter dict and body lines.

    Delegates to plugin_validator.parse_skill_md — the same real-YAML
    extract+parse+body-slice sequence AsSeriesValidator.validate already
    uses for the production AS-series entry point — instead of
    reimplementing it a third time (the other existing copy is
    _extract_tools_list, below). Real YAML parsing matters because a naive
    line-by-line colon splitter has no notion of YAML indentation or block
    scalars, so a line inside a multi-line ``description: |`` value that
    happens to read like ``name: something`` would be misread as a
    top-level ``name`` key, masking a SKILL.md with no real name field.

    Returns:
        (frontmatter, body_lines) where frontmatter is a dict of parsed YAML
        fields and body_lines is the content after the frontmatter block.
    """
    # Deferred import to break circular dependency; plugin_validator imports
    # rules modules, so we defer here rather than at module level.
    from skilllint.plugin_validator import parse_skill_md  # noqa: PLC0415

    frontmatter, body_lines, _yaml_err, _colon_fields = parse_skill_md(path)
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
    return _violation(code, severity, message, fix=fix, authority=rule_authority(code))


# ---------------------------------------------------------------------------
# Individual rule checks
# ---------------------------------------------------------------------------


@skilllint_rule(
    "AS001",
    severity="error",
    category="skill",
    authority={"origin": "agentskills.io", "reference": "/specification#skill-naming"},
)
def _check_as001(name: str | None) -> dict | None:
    """AS001 — SKILL.md declares no name field.

    agentskills.io requires ``name`` on a SKILL.md. FM001 stays silent here
    because Claude Code's own skills.md treats the field as optional and falls
    back to the directory name, so ``SkillFrontmatter.name`` is declared
    ``str | None``. AS001 is therefore the only signal that a skill is missing
    its name under the AgentSkills specification.

    Name *syntax* — casing, hyphens, length, and the directory match — is
    FM010's, not AS001's. This rule asserts presence only.

    Args:
        name: The skill name from frontmatter, or None if missing.

    Returns:
        Violation dict when the name field is absent, None otherwise.

    Fix:
        Add a ``name`` field to the frontmatter, matching the skill directory.
    """
    if name is None:
        return _make_violation("AS001", "error", "name field is missing")

    return None


def _extract_tools_list(path: pathlib.Path, field: str = "allowed-tools") -> list[str]:
    """Extract tool names from a tool-declaring frontmatter field.

    Handles the YAML list form and the inline string form. Uses proper YAML
    parsing (not the simple key/value parser used by _parse_skill_md) so that
    multi-line list values are read correctly.

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

    return normalize_tools_value(parsed.get(field))


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
        tools: List of tool name strings from the ``allowed-tools`` frontmatter field.
        path: Path to the SKILL.md being validated.

    Returns:
        List of violation dicts — one per tool with a case mismatch or unknown server.
    """
    known_servers = discover_mcp_servers(path)
    # Collect plugin-name -> server names map for plugin-namespaced tool resolution
    plugin_server_map = collect_plugin_names_from_ancestry(path)

    violations: list[dict] = []
    for tool_name in tools:
        analysis = analyze_mcp_tool_reference(tool_name, known_servers, plugin_server_map)
        if analysis is None or analysis.status == "exact":
            continue
        if analysis.status == "case-mismatch":
            # Case mismatch with a discoverable server — error
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
                violations.append(
                    _make_violation(
                        "AS008",
                        "error",
                        f"MCP tool '{tool_name}' has a case mismatch with server '{canonical}'. "
                        "The allowed-tools: field is case-sensitive. "
                        f"Did you mean '{corrected_reference}'?",
                        fix=f"Replace '{replacement_source}' with '{replacement_target}'.",
                    )
                )
        else:
            violations.append(
                _make_violation(
                    "AS008",
                    "warning",
                    f"MCP tool '{tool_name}' references server '{analysis.server_name}' which was not found "
                    "in this plugin or project's MCP configuration. "
                    "If this references an external MCP server that end users must configure, "
                    "suppress this warning.",
                )
            )

    return violations


@skilllint_rule(
    "AS006", severity="info", category="skill", authority={"origin": "agentskills.io", "reference": _AS006_EVALS_URL}
)
def _check_as006(path: pathlib.Path) -> dict | None:
    """AS006 — No evaluation queries file found.

    Recommends adding evaluation queries to the skill directory to enable
    automated quality assessment, either as a top-level ``eval_queries.json``
    (or any ``*eval*.json``/``*queries*.json`` file) or as ``evals/evals.json``
    — the layout documented by agentskills.io's evaluating-skills guide.

    Args:
        path: Path to the SKILL.md file being validated.

    Returns:
        Violation dict if no eval file found, None otherwise.

    Fix:
        Create ``eval_queries.json`` (or ``evals/evals.json``) in the skill
        directory with test queries in JSON format.

    Note:
        This is an informational message, not an error. Skills work
        without evaluation queries, but they're recommended for quality
        assurance.
    """
    parent = path.parent

    # Check for eval_queries.json exact name first
    if (parent / "eval_queries.json").exists():
        return None

    # Check for evals/evals.json — a directory, so it's invisible to the
    # file glob below (which only scans parent.iterdir(), not subdirs).
    # The doc wording ("stores ... in evals/evals.json") is about the file's
    # content, so an empty evals/ dir does not satisfy this.
    if (parent / "evals" / "evals.json").is_file():
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
        "No eval_queries.json or evals/evals.json found in skill directory — add evaluation queries to enable automated quality assessment",
    )


# ponytail: global process-lifetime cache; fine for a linter CLI invocation.
# Ancestor plugin.json is never touched by --fix (which only rewrites the
# file being checked), so a stale-cache read is not possible for a
# same-path re-validation pass within one process.
@functools.cache
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
    platforms=["claude-code"],
    authority={"origin": "anthropic.com", "reference": "https://docs.anthropic.com/en/docs/claude-code/skills"},
)
def _check_as009(path: pathlib.Path) -> dict | None:
    """AS009 — Nested skill will not be auto-discovered.

    Unlike its AS-series siblings (AS001, AS006, AS008), this rule is not
    sourced from the agentskills.io specification — its ``authority`` above
    cites Claude Code's own docs, and it describes a Claude Code auto-discovery
    limitation. It is scoped to ``platforms=["claude-code"]`` instead of the
    AS-series default of "applies to every platform" for that reason.

    Scope of ``platforms=`` here: it affects only rule *listing* — it is what
    makes ``skilllint rules --platform cursor``/``codex`` correctly omit
    AS009. It has no effect on *enforcement*: ``skilllint check --platform
    <any>`` still runs this check unconditionally on every SKILL.md, because
    validator dispatch (``_get_validators_for_path`` in plugin_validator.py)
    selects ``AsSeriesValidator`` by file type alone, never by platform. That
    dispatch is pre-existing, deliberate architecture — unrelated to and
    unchanged by this fix.

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
    """Run AS001 and AS006-AS009 checks on a SKILL.md file.

    Reads and parses the file at the given path, then runs all AS-series
    rules. Returns a list of violation dicts; empty list means no issues.

    Args:
        path: Path to the SKILL.md file to validate.

    Returns:
        List of violation dicts, each with keys: code, severity, message.
        May include 'fix' key with auto-fix suggestion for AS008, AS009.
    """
    frontmatter, _body_lines = _parse_skill_md(path)

    violations: list[dict] = []

    v = _check_as001(frontmatter.get("name") or None)
    if v:
        violations.append(v)

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

    v = _check_as001(frontmatter.get("name") or None)
    if v:
        violations.append(v)

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
