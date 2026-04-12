"""PL-series plugin structure rules (PL001-PL006).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

PL001 through PL006 are emitted by ``PluginStructureValidator`` (and its
helpers ``_validate_marketplace_json_layout`` / ``_validate_plugin_json_syntax``)
in ``plugin_validator.py``.  Detection requires filesystem access (checking
whether ``.claude-plugin/plugin.json`` and ``marketplace.json`` exist),
JSON parsing of those files, and in some cases spawning the ``claude plugin
validate`` subprocess.  None of that information is available from frontmatter
alone, so the validator functions registered here are **registration-only
stubs** — they exist to make rule metadata available via ``RULE_REGISTRY``
(and therefore via ``skilllint rule PLxxx``) without duplicating the
detection logic that belongs in the filesystem/subprocess-owning validator
class.

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

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skilllint.rule_registry import skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

_PL_DOCS_BASE = "https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md"


def _docs_url(code: str) -> str:
    """Return the documentation URL for a PL rule code.

    Args:
        code: Rule code string (e.g., "PL001").

    Returns:
        Full URL with anchor for the error code documentation.
    """
    return f"{_PL_DOCS_BASE}#{code.lower()}"


# ---------------------------------------------------------------------------
# PL001 — Missing plugin.json file
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PL001",
    severity="error",
    category="plugin",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PL_DOCS_BASE},
)
def check_pl001(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    r"""## PL001 — Missing plugin.json file

    The ``.claude-plugin/plugin.json`` file is absent from the plugin
    directory.  Without ``plugin.json``, Claude Code cannot register or
    load the plugin and ``claude plugin validate`` will fail.

    This rule is detected by ``PluginStructureValidator`` in
    ``plugin_validator.py`` when the filesystem path
    ``.claude-plugin/plugin.json`` does not exist, or when
    ``claude plugin validate`` reports a missing-manifest error.

    **Source:** ``PluginStructureValidator`` in ``plugin_validator.py`` —
    checks for the existence of ``.claude-plugin/plugin.json`` under the
    plugin directory, and maps ``claude plugin validate`` output patterns
    matching ``missing.*plugin\\.json`` to this code.

    **Fix:** Create a ``.claude-plugin/plugin.json`` file with the required
    fields:

    ```json
    {
      "name": "my-plugin",
      "version": "1.0.0"
    }
    ```

    Returns:
        Always an empty list.  PL001 is emitted by ``PluginStructureValidator``
        in ``plugin_validator.py`` after checking filesystem path existence
        and parsing ``claude plugin validate`` output; this function exists for
        rule metadata registration only.

    <!-- examples: PL001 -->
    """
    # Detection requires filesystem path checks and subprocess output parsing.
    # Owned by PluginStructureValidator in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# PL002 — Invalid JSON syntax in plugin.json or marketplace.json
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PL002",
    severity="error",
    category="plugin",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PL_DOCS_BASE},
)
def check_pl002(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## PL002 — Invalid JSON syntax in plugin.json or marketplace.json

    The ``plugin.json`` or ``marketplace.json`` file contains malformed JSON
    that cannot be parsed.  Claude Code and ``claude plugin validate`` both
    require syntactically valid JSON.

    This rule fires when:
    - ``plugin.json`` fails to parse (``_validate_plugin_json_syntax`` in
      ``plugin_validator.py`` catches ``msgspec.DecodeError``).
    - ``marketplace.json`` fails to parse (``_validate_marketplace_json_layout``
      catches ``msgspec.DecodeError`` or ``OSError``).
    - ``claude plugin validate`` output matches ``invalid.*json|json.*syntax|parse.*error``.
    - ``claude plugin validate`` times out.

    **Source:** ``PluginStructureValidator._validate_plugin_json_syntax`` and
    ``_validate_marketplace_json_layout`` in ``plugin_validator.py``.

    **Fix:** Validate and repair the JSON syntax:

    ```bash
    python3 -m json.tool .claude-plugin/plugin.json
    python3 -m json.tool .claude-plugin/marketplace.json
    ```

    Returns:
        Always an empty list.  PL002 is emitted by ``PluginStructureValidator``
        in ``plugin_validator.py`` after attempting to parse the JSON files;
        this function exists for rule metadata registration only.

    <!-- examples: PL002 -->
    """
    # Detection requires JSON parsing of filesystem files and subprocess output.
    # Owned by PluginStructureValidator in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# PL003 — Missing required field 'name' in plugin.json
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PL003",
    severity="error",
    category="plugin",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PL_DOCS_BASE},
)
def check_pl003(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## PL003 — Missing required field 'name' in plugin.json

    The ``plugin.json`` file does not contain the mandatory ``name`` field.
    Claude Code requires ``name`` to identify the plugin during registration
    and display.

    This rule is detected when ``claude plugin validate`` reports an error
    matching ``missing.*required.*field.*name|name.*required``.

    **Source:** ``PluginStructureValidator._parse_claude_errors`` in
    ``plugin_validator.py`` — maps ``claude plugin validate`` output to PL003
    when the name-required pattern is matched.

    **Fix:** Add the ``name`` field to ``plugin.json``:

    ```json
    {
      "name": "my-plugin"
    }
    ```

    Returns:
        Always an empty list.  PL003 is emitted by ``PluginStructureValidator``
        in ``plugin_validator.py`` by parsing ``claude plugin validate``
        subprocess output; this function exists for rule metadata registration
        only.

    <!-- examples: PL003 -->
    """
    # Detection requires subprocess output parsing from claude plugin validate.
    # Owned by PluginStructureValidator in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# PL004 — Component path does not start with './'
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PL004",
    severity="error",
    category="plugin",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PL_DOCS_BASE},
)
def check_pl004(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    r"""## PL004 — Component path does not start with './'

    A component path listed in ``plugin.json`` (skills, agents, or commands
    array) does not start with ``./``.  Claude Code requires all component
    paths to be relative paths that begin with ``./`` to prevent accidental
    absolute-path references.

    This rule is detected when ``claude plugin validate`` reports an error
    matching ``path.*must.*start.*with.*\\./|invalid.*path.*format``.

    **Source:** ``PluginStructureValidator._parse_claude_errors`` in
    ``plugin_validator.py`` — maps ``claude plugin validate`` output to PL004
    when the path-format pattern is matched.

    **Fix:** Prefix all component paths in ``plugin.json`` with ``./``:

    ```json
    {
      "skills": ["./skills/my-skill/"]
    }
    ```

    Returns:
        Always an empty list.  PL004 is emitted by ``PluginStructureValidator``
        in ``plugin_validator.py`` by parsing ``claude plugin validate``
        subprocess output; this function exists for rule metadata registration
        only.

    <!-- examples: PL004 -->
    """
    # Detection requires subprocess output parsing from claude plugin validate.
    # Owned by PluginStructureValidator in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# PL005 — Referenced component file does not exist
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PL005",
    severity="error",
    category="plugin",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PL_DOCS_BASE},
)
def check_pl005(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## PL005 — Referenced component file does not exist

    A component path registered in ``plugin.json`` points to a file or
    directory that does not exist on the filesystem.  Claude Code will fail
    to load the referenced component at runtime.

    This rule is detected when ``claude plugin validate`` reports an error
    matching ``file.*does not exist|referenced.*file.*not found|missing.*file``.

    **Source:** ``PluginStructureValidator._parse_claude_errors`` in
    ``plugin_validator.py`` — maps ``claude plugin validate`` output to PL005
    when the missing-file pattern is matched.

    **Fix:** Either create the missing component at the listed path, or remove
    its entry from ``plugin.json``:

    ```bash
    # Create the missing skill
    mkdir -p skills/my-skill
    touch skills/my-skill/SKILL.md

    # Or remove the broken reference from plugin.json
    ```

    Returns:
        Always an empty list.  PL005 is emitted by ``PluginStructureValidator``
        in ``plugin_validator.py`` by parsing ``claude plugin validate``
        subprocess output; this function exists for rule metadata registration
        only.

    <!-- examples: PL005 -->
    """
    # Detection requires filesystem presence checks via subprocess output parsing.
    # Owned by PluginStructureValidator in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# PL006 — marketplace.json has invalid top-level keys
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PL006",
    severity="error",
    category="plugin",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PL_DOCS_BASE},
)
def check_pl006(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## PL006 — marketplace.json has invalid top-level keys

    The ``marketplace.json`` file contains plugin-manifest fields (such as
    ``repository``, ``homepage``, or ``license``) at the catalog root.  The
    Claude Code marketplace schema allows only ``name``, ``owner``,
    ``plugins``, and ``metadata`` at the top level.  All other fields must
    be nested under ``metadata``.

    This rule is detected by:
    - ``_validate_marketplace_json_layout`` in ``plugin_validator.py`` when
      the parsed JSON object contains keys not in
      ``MARKETPLACE_JSON_ROOT_KEYS``.
    - ``PluginStructureValidator._parse_claude_errors`` when
      ``claude plugin validate`` reports unrecognized top-level marketplace
      keys.

    **Source:** ``_validate_marketplace_json_layout`` and
    ``PluginStructureValidator._parse_claude_errors`` in ``plugin_validator.py``.

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
      "plugins": [...],
      "metadata": {
        "repository": "https://github.com/my-org/my-plugin",
        "homepage": "https://my-org.github.io/my-plugin",
        "license": "MIT"
      }
    }
    ```

    Returns:
        Always an empty list.  PL006 is emitted by
        ``_validate_marketplace_json_layout`` and
        ``PluginStructureValidator._parse_claude_errors`` in
        ``plugin_validator.py`` after reading and parsing the filesystem file;
        this function exists for rule metadata registration only.

    <!-- examples: PL006 -->
    """
    # Detection requires reading and parsing marketplace.json from the filesystem,
    # and/or parsing claude plugin validate subprocess output.
    # Owned by _validate_marketplace_json_layout and PluginStructureValidator
    # in plugin_validator.py.
    return []


__all__ = ["check_pl001", "check_pl002", "check_pl003", "check_pl004", "check_pl005", "check_pl006"]
