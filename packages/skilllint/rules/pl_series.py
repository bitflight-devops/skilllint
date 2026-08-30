"""PL-series plugin structure rules (PL001-PL006).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

PL001-PL006 detection lives here.  ``PluginStructureValidator`` in
``plugin_validator.py`` is a thin wrapper: it locates the plugin directory,
runs the ``claude plugin validate`` subprocess, calls these rule functions,
and packages the result into a ``ValidationResult``.  The auto-fix
(``_fix_marketplace_json_metadata_keys``) stays on the validator side because
it mutates files; it calls ``analyze_marketplace_root_keys`` from this module
so detection and repair cannot drift apart.

Detection sources per code — the PL family has two, and several codes use
both:

* **Direct inspection** of files under ``.claude-plugin/``:
  PL002 (``plugin.json`` syntax) and PL006 (``marketplace.json`` root keys,
  which also reports PL002 when the file itself cannot be parsed).
* **Subprocess output** — regex matches against combined stdout/stderr of
  ``claude plugin validate``: PL001, PL002, PL003, PL004, PL005, and the
  PL006 fallback in ``claude_validation_failure_issue``.  PL003, PL004 and
  PL005 have *no* direct detector at all; they exist only as patterns
  against that output.

Signatures state the input each rule actually reads rather than a uniform
frontmatter triple, which the PL family never had access to.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | PL001 | Missing plugin.json file                                  | error     |
    | PL002 | Invalid JSON syntax in plugin.json / marketplace.json     | error     |
    | PL003 | Missing required field 'name' in plugin.json              | error     |
    | PL004 | Component path does not start with './'                   | error     |
    | PL005 | Referenced component file does not exist                  | error     |
    | PL006 | marketplace.json has invalid top-level keys               | error     |
    +-------+-----------------------------------------------------------+-----------+

Import note: ValidationIssue is deferred inside ``_make_issue`` to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

import msgspec

from skilllint.rule_registry import rule_reference, skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue, YamlValue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

# Official plugin.json schema (plugin manifest)
PLUGIN_MANIFEST_SCHEMA_URL = "https://code.claude.com/docs/en/plugins-reference.md#plugin-manifest-schema"
# Claude Code marketplace.json top-level keys (not plugin-manifest fields at root)
MARKETPLACE_MANIFEST_SCHEMA_URL = "https://code.claude.com/docs/en/plugin-marketplaces.md#marketplace-schema"
MARKETPLACE_JSON_ROOT_KEYS: frozenset[str] = frozenset({"name", "owner", "plugins", "metadata"})
# Same field names as plugin.json metadata, but must live under `metadata` on marketplace.json
MARKETPLACE_METADATA_RELOCATABLE_KEYS: frozenset[str] = frozenset({
    "repository",
    "homepage",
    "license",
    "author",
    "keywords",
    "description",
    "version",
})

# Patterns matched against combined stdout/stderr of `claude plugin validate`.
# Source: PluginStructureValidator._parse_claude_errors, plugin_validator.py.
_CLAUDE_ERROR_PATTERNS: dict[str, str] = {
    "PL001": r"missing.*plugin\.json|plugin\.json.*not found",
    "PL002": r"invalid.*json|json.*syntax|parse.*error",
    "PL003": r"missing.*required.*field.*name|name.*required",
    "PL004": r"path.*must.*start.*with.*\./|invalid.*path.*format",
    "PL005": r"file.*does not exist|referenced.*file.*not found|missing.*file",
}


def _make_issue(
    *, field: str, severity: Literal["error", "warning", "info"], message: str, code: str, suggestion: str | None = None
) -> ValidationIssue:
    """Construct a ValidationIssue for a PL rule.

    Args:
        field: Manifest file the issue concerns ("plugin.json" / "marketplace.json").
        severity: Issue severity.
        message: Human-readable description.
        code: Rule code (e.g. "PL001").
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


def analyze_marketplace_root_keys(data: dict[str, YamlValue]) -> tuple[list[str], list[str]]:
    """Classify misplaced top-level keys in marketplace.json.

    Shared with ``_fix_marketplace_json_metadata_keys`` in ``plugin_validator.py``
    so PL006 detection and its auto-fix always agree on which keys are in scope.

    Args:
        data: Parsed marketplace.json root object.

    Returns:
        (relocatable, unknown) — keys to move under ``metadata``, and keys that are not
        recognized at root and are not auto-relocated (require manual removal or rename).
    """
    misplaced = [k for k in data if k not in MARKETPLACE_JSON_ROOT_KEYS]
    relocatable = sorted(k for k in misplaced if k in MARKETPLACE_METADATA_RELOCATABLE_KEYS)
    unknown = sorted(k for k in misplaced if k not in MARKETPLACE_METADATA_RELOCATABLE_KEYS)
    return relocatable, unknown


def _claude_error_message(code: str, output: str) -> str:
    """Get human-readable error message for code.

    Args:
        code: Error code (PL001-PL006)
        output: CLI output containing error details

    Returns:
        Human-readable error message
    """
    lines = output.split("\n")
    for text_line in lines:
        stripped_line = text_line.strip()
        if (
            stripped_line
            and not stripped_line.startswith("#")
            and any(kw in stripped_line.lower() for kw in ["error", "missing", "invalid", "required", "not found"])
        ):
            return stripped_line[:200]

    fallbacks: dict[str, str] = {
        "PL001": "Missing plugin.json file in .claude-plugin/ directory",
        "PL002": "Invalid JSON syntax in plugin.json",
        "PL003": "Missing required field 'name' in plugin.json",
        "PL004": "Component path does not start with './'",
        "PL005": "Referenced component file does not exist",
        "PL006": "marketplace.json has invalid top-level keys (use metadata object)",
    }
    return fallbacks.get(str(code), "Plugin structure validation failed")


def _claude_error_suggestion(code: str) -> str:  # noqa: PLR0911
    """Get suggestion for fixing error.

    Args:
        code: Error code (PL001-PL006)

    Returns:
        Human-readable suggestion for fixing the error
    """
    match code:
        case "PL001":
            return "Create .claude-plugin/plugin.json with required fields"
        case "PL002":
            return "Validate JSON syntax: python3 -m json.tool .claude-plugin/plugin.json"
        case "PL003":
            return 'Add \'name\' field to plugin.json: {"name": "plugin-name"}'
        case "PL004":
            return "Ensure all component paths start with './' (e.g., './skills/skill-name/')"
        case "PL005":
            return "Verify all referenced files exist at specified paths"
        case "PL006":
            return (
                "Keep only name, owner, plugins, and metadata at the marketplace root; "
                f"see {MARKETPLACE_MANIFEST_SCHEMA_URL}"
            )
        case _:
            return "Run 'claude plugin validate' for detailed error information"


def _claude_output_issues(code: str, claude_output: str) -> list[ValidationIssue]:
    """Match one PL pattern against ``claude plugin validate`` output.

    Args:
        code: Rule code whose pattern to apply.
        claude_output: Combined stdout/stderr of the subprocess.

    Returns:
        A single-issue list when the pattern matches, otherwise an empty list.
    """
    if not re.search(_CLAUDE_ERROR_PATTERNS[code], claude_output, re.IGNORECASE):
        return []
    return [
        _make_issue(
            field="plugin.json",
            severity="error",
            message=_claude_error_message(code, claude_output),
            code=code,
            suggestion=_claude_error_suggestion(code),
        )
    ]


def claude_validation_failure_issue(stdout: str, stderr: str) -> ValidationIssue:
    """Build the catch-all issue for a failed ``claude plugin validate`` run.

    Used when the subprocess reported failure but no PL001-PL005 pattern
    matched.  Emits PL006 when the output names unrecognized marketplace keys,
    otherwise a generic PL002.

    Args:
        stdout: Standard output from claude CLI.
        stderr: Standard error from claude CLI.

    Returns:
        A single ValidationIssue carrying the truncated CLI output.
    """
    detail = (stdout.strip() + "\n" + stderr.strip())[:500] or "(no output)"
    low = detail.lower()
    if "marketplace" in low and "unrecognized keys" in low:
        return _make_issue(
            field="marketplace.json",
            severity="error",
            message=(
                "marketplace.json: top-level keys rejected by `claude plugin validate` "
                "(Claude Code allows only `name`, `owner`, `plugins`, and `metadata` at the catalog root)"
            ),
            code="PL006",
            suggestion=(
                "Plugin-manifest fields such as `repository`, `homepage`, and `license` belong under "
                f"`metadata`, not beside `plugins`. Reference: {MARKETPLACE_MANIFEST_SCHEMA_URL}. "
                f"Run `skilllint check --fix` to relocate known fields. CLI output: {detail}"
            ),
        )
    return _make_issue(
        field="plugin.json",
        severity="error",
        message="Plugin validation failed (see claude CLI output for details)",
        code="PL002",
        suggestion=f"Run 'claude plugin validate <plugin-dir>'. CLI output: {detail}",
    )


# ---------------------------------------------------------------------------
# PL001 — Missing plugin.json file
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PL001",
    severity="error",
    category="plugin",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_pl001(claude_output: str) -> list[ValidationIssue]:
    r"""## PL001 — Missing plugin.json file

    The ``.claude-plugin/plugin.json`` file is absent from the plugin
    directory.  Without ``plugin.json``, Claude Code cannot register or
    load the plugin and ``claude plugin validate`` will fail.

    Detection is **subprocess-derived only**: the combined stdout/stderr of
    ``claude plugin validate`` is matched against
    ``missing.*plugin\.json|plugin\.json.*not found``.  There is no direct
    filesystem detector — ``PluginStructureValidator`` reaches this rule only
    after ``find_plugin_dir`` has already located a directory containing
    ``.claude-plugin/plugin.json``.

    ``PL001`` is additionally reused by ``PluginStructureValidator`` as the
    code on several *informational* "validation skipped" messages (nested CLI
    session, Claude CLI absent, CLI failed to start).  Those are emitted by the
    validator, not by this function, and carry ``severity="info"``.

    **Fix:** Create a ``.claude-plugin/plugin.json`` file with the required
    fields:

    ```json
    {
      "name": "my-plugin",
      "version": "1.0.0"
    }
    ```

    Args:
        claude_output: Combined stdout/stderr from ``claude plugin validate``.

    Returns:
        One error issue when the missing-manifest pattern matches, else empty.

    <!-- examples: PL001 -->
    """
    return _claude_output_issues("PL001", claude_output)


# ---------------------------------------------------------------------------
# PL002 — Invalid JSON syntax in plugin.json or marketplace.json
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PL002",
    severity="error",
    category="plugin",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_pl002(plugin_json_path: Path | None = None, claude_output: str = "") -> list[ValidationIssue]:
    """## PL002 — Invalid JSON syntax in plugin.json or marketplace.json

    The ``plugin.json`` or ``marketplace.json`` file contains malformed JSON
    that cannot be parsed.  Claude Code and ``claude plugin validate`` both
    require syntactically valid JSON.

    PL002 has two detection sources, and this function owns both:

    - **Direct** — ``plugin_json_path`` is decoded with ``msgspec``; a
      ``DecodeError`` or ``OSError`` produces the issue.
    - **Subprocess** — ``claude_output`` is matched against
      ``invalid.*json|json.*syntax|parse.*error``.

    Two further PL002 emissions live outside this function because they are
    orchestration outcomes rather than rule detection: ``check_pl006`` reports
    PL002 when ``marketplace.json`` itself cannot be read or decoded, and
    ``PluginStructureValidator`` reports PL002 when the subprocess times out or
    when a failed run matches no pattern at all (see
    ``claude_validation_failure_issue``).

    **Fix:** Validate and repair the JSON syntax:

    ```bash
    python3 -m json.tool .claude-plugin/plugin.json
    python3 -m json.tool .claude-plugin/marketplace.json
    ```

    Args:
        plugin_json_path: ``plugin.json`` to parse, or None to skip the direct check.
        claude_output: Combined stdout/stderr from ``claude plugin validate``.

    Returns:
        One error issue per detection source that fires; empty when the
        manifest parses and the output matches no JSON-syntax pattern.

    <!-- examples: PL002 -->
    """
    issues: list[ValidationIssue] = []

    if plugin_json_path is not None:
        message: str | None = None
        try:
            msgspec.json.decode(plugin_json_path.read_bytes())
        except msgspec.DecodeError as e:
            message = f"Invalid JSON syntax in plugin.json: {e}"
        except OSError as e:
            message = f"Cannot read plugin.json: {e}"
        if message is not None:
            issues.append(
                _make_issue(
                    field="plugin.json",
                    severity="error",
                    message=message,
                    code="PL002",
                    suggestion=f"plugin.json must be valid JSON. Schema: {PLUGIN_MANIFEST_SCHEMA_URL}",
                )
            )

    if claude_output:
        issues.extend(_claude_output_issues("PL002", claude_output))

    return issues


# ---------------------------------------------------------------------------
# PL003 — Missing required field 'name' in plugin.json
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PL003",
    severity="error",
    category="plugin",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_pl003(claude_output: str) -> list[ValidationIssue]:
    """## PL003 — Missing required field 'name' in plugin.json

    The ``plugin.json`` file does not contain the mandatory ``name`` field.
    Claude Code requires ``name`` to identify the plugin during registration
    and display.

    Detection is **subprocess-derived only**: the combined stdout/stderr of
    ``claude plugin validate`` is matched against
    ``missing.*required.*field.*name|name.*required``.  skilllint never reads
    ``plugin.json`` itself for this rule.

    **Fix:** Add the ``name`` field to ``plugin.json``:

    ```json
    {
      "name": "my-plugin"
    }
    ```

    Args:
        claude_output: Combined stdout/stderr from ``claude plugin validate``.

    Returns:
        One error issue when the name-required pattern matches, else empty.

    <!-- examples: PL003 -->
    """
    return _claude_output_issues("PL003", claude_output)


# ---------------------------------------------------------------------------
# PL004 — Component path does not start with './'
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PL004",
    severity="error",
    category="plugin",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_pl004(claude_output: str) -> list[ValidationIssue]:
    r"""## PL004 — Component path does not start with './'

    A component path listed in ``plugin.json`` (skills, agents, or commands
    array) does not start with ``./``.  Claude Code requires all component
    paths to be relative paths that begin with ``./`` to prevent accidental
    absolute-path references.

    Detection is **subprocess-derived only**: the combined stdout/stderr of
    ``claude plugin validate`` is matched against
    ``path.*must.*start.*with.*\./|invalid.*path.*format``.

    **Fix:** Prefix all component paths in ``plugin.json`` with ``./``:

    ```json
    {
      "skills": ["./skills/my-skill/"]
    }
    ```

    Args:
        claude_output: Combined stdout/stderr from ``claude plugin validate``.

    Returns:
        One error issue when the path-format pattern matches, else empty.

    <!-- examples: PL004 -->
    """
    return _claude_output_issues("PL004", claude_output)


# ---------------------------------------------------------------------------
# PL005 — Referenced component file does not exist
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PL005",
    severity="error",
    category="plugin",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_pl005(claude_output: str) -> list[ValidationIssue]:
    """## PL005 — Referenced component file does not exist

    A component path registered in ``plugin.json`` points to a file or
    directory that does not exist on the filesystem.  Claude Code will fail
    to load the referenced component at runtime.

    Detection is **subprocess-derived only**: the combined stdout/stderr of
    ``claude plugin validate`` is matched against
    ``file.*does not exist|referenced.*file.*not found|missing.*file``.
    skilllint performs no filesystem presence check of its own for this rule.

    **Fix:** Either create the missing component at the listed path, or remove
    its entry from ``plugin.json``:

    ```bash
    # Create the missing skill
    mkdir -p skills/my-skill
    touch skills/my-skill/SKILL.md

    # Or remove the broken reference from plugin.json
    ```

    Args:
        claude_output: Combined stdout/stderr from ``claude plugin validate``.

    Returns:
        One error issue when the missing-file pattern matches, else empty.

    <!-- examples: PL005 -->
    """
    return _claude_output_issues("PL005", claude_output)


# ---------------------------------------------------------------------------
# PL006 — marketplace.json has invalid top-level keys
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PL006",
    severity="error",
    category="plugin",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_pl006(plugin_dir: Path) -> list[ValidationIssue]:
    """## PL006 — marketplace.json has invalid top-level keys

    The ``marketplace.json`` file contains plugin-manifest fields (such as
    ``repository``, ``homepage``, or ``license``) at the catalog root.  The
    Claude Code marketplace schema allows only ``name``, ``owner``,
    ``plugins``, and ``metadata`` at the top level.  All other fields must
    be nested under ``metadata``.

    Detection is **direct**: ``.claude-plugin/marketplace.json`` is read and
    decoded, then its root keys are classified by
    ``analyze_marketplace_root_keys``.  Because the file must be parsed before
    its keys can be judged, this function also emits **PL002** when the file
    cannot be read or decoded.

    A second, **subprocess-derived** PL006 lives in
    ``claude_validation_failure_issue``: a failed ``claude plugin validate``
    run whose output mentions a marketplace with "unrecognized keys" and that
    matched no PL001-PL005 pattern.

    Missing ``marketplace.json`` is not an issue — most plugins have none.

    **Fix:** Move the offending fields under a ``metadata`` object, or run
    the auto-fix:

    ```bash
    skilllint check --fix <plugin-dir>
    ```

    Manual correction:

    ```json
    {
      "name": "my-catalog",
      "owner": "my-org",
      "plugins": [],
      "metadata": {
        "repository": "https://github.com/my-org/my-plugin",
        "homepage": "https://my-org.github.io/my-plugin",
        "license": "MIT"
      }
    }
    ```

    Args:
        plugin_dir: Plugin root directory containing ``.claude-plugin/``.

    Returns:
        Issues describing an unparseable (PL002) or schema-violating (PL006)
        ``marketplace.json``; empty when the file is absent or conforming.

    <!-- examples: PL006 -->
    """
    mp_path = plugin_dir / ".claude-plugin" / "marketplace.json"
    if not mp_path.exists():
        return []
    try:
        raw = msgspec.json.decode(mp_path.read_bytes())
    except msgspec.DecodeError as e:
        return [
            _make_issue(
                field="marketplace.json",
                severity="error",
                message=f"Invalid JSON syntax in marketplace.json: {e}",
                code="PL002",
                suggestion=f"marketplace.json must be valid JSON. Schema: {MARKETPLACE_MANIFEST_SCHEMA_URL}",
            )
        ]
    except OSError as e:
        return [
            _make_issue(
                field="marketplace.json", severity="error", message=f"Cannot read marketplace.json: {e}", code="PL002"
            )
        ]
    if not isinstance(raw, dict):
        return [
            _make_issue(
                field="marketplace.json",
                severity="error",
                message="marketplace.json must be a JSON object at the root",
                code="PL006",
                suggestion=f"See: {MARKETPLACE_MANIFEST_SCHEMA_URL}",
            )
        ]
    relocatable, unknown = analyze_marketplace_root_keys(raw)
    if not relocatable and not unknown:
        return []
    parts: list[str] = []
    if relocatable:
        parts.append("move these fields under a `metadata` object: " + ", ".join(f"`{k}`" for k in relocatable))
    if unknown:
        parts.append("remove or rename unrecognized top-level keys: " + ", ".join(f"`{k}`" for k in unknown))
    detail = "; ".join(parts)
    suggestion = (
        "Claude Code marketplace manifests only allow top-level `name`, `owner`, `plugins`, "
        f"and optional `metadata`. {detail.capitalize()}. "
        f"Reference: {MARKETPLACE_MANIFEST_SCHEMA_URL}"
    )
    if relocatable and not unknown:
        suggestion += " Run `skilllint check --fix` on the plugin directory to move them automatically."
    return [
        _make_issue(
            field="marketplace.json",
            severity="error",
            message=(
                f"marketplace.json violates the Claude Code marketplace schema: {detail}. "
                "Plugin-manifest fields must not appear beside `plugins` at the catalog root."
            ),
            code="PL006",
            suggestion=suggestion,
        )
    ]


__all__ = [
    "MARKETPLACE_JSON_ROOT_KEYS",
    "MARKETPLACE_MANIFEST_SCHEMA_URL",
    "MARKETPLACE_METADATA_RELOCATABLE_KEYS",
    "PLUGIN_MANIFEST_SCHEMA_URL",
    "analyze_marketplace_root_keys",
    "check_pl001",
    "check_pl002",
    "check_pl003",
    "check_pl004",
    "check_pl005",
    "check_pl006",
    "claude_validation_failure_issue",
]
