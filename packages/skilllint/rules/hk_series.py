"""HK-series hooks validation rules (HK001-HK005).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

HK001-HK005 detection lives here.  ``HookValidator`` in ``plugin_validator.py``
is a thin wrapper that calls these functions and packages the result; it
retains the auto-fix, which mutates the filesystem and is a validator concern
rather than a rule concern.

Detection needs a parsed ``hooks.json`` (and, for HK004/HK005, the filesystem)
rather than frontmatter, so each signature states the input the rule actually
reads instead of a uniform frontmatter triple.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | HK001 | Invalid hooks.json structure                              | error     |
    | HK002 | Invalid event type in hooks.json                          | error     |
    | HK003 | Invalid hook entry structure                               | error     |
    | HK004 | Hook script referenced but not found                      | error     |
    | HK005 | Hook script exists but is not executable                  | warning   |
    +-------+-----------------------------------------------------------+-----------+

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from skilllint.boundary.hooks_json_ingest import HooksJsonDefect, ingest_hooks_json
from skilllint.rule_registry import _make_issue, skilllint_rule

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping

    from pydantic import JsonValue

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

# Rule data for HK002: the event names Claude Code dispatches hooks for.
# Source: .claude/vendor/sources/hooks-2026-09-04-0550.md, "Hook events" (level-3
# headings). Provenance claim HK002.valid_event_types. Verified via
# scripts/refresh_claim_values.py -- PreModelSwitch and PostModelSwitch were
# added upstream between the 2026-08-28 and 2026-09-04 captures.
VALID_EVENT_TYPES: frozenset[str] = frozenset({
    "SessionStart",
    "Setup",
    "InstructionsLoaded",
    "UserPromptSubmit",
    "UserPromptExpansion",
    "PreToolUse",
    "PermissionRequest",
    "PermissionDenied",
    "PostToolUse",
    "PostToolUseFailure",
    "PostToolBatch",
    "Notification",
    "MessageDisplay",
    "SubagentStart",
    "SubagentStop",
    "Stop",
    "StopFailure",
    "TeammateIdle",
    "TaskCreated",
    "TaskCompleted",
    "ConfigChange",
    "CwdChanged",
    "DirectoryAdded",
    "FileChanged",
    "WorktreeCreate",
    "WorktreeRemove",
    "PreCompact",
    "PostCompact",
    "PreModelSwitch",
    "PostModelSwitch",
    "Elicitation",
    "ElicitationResult",
    "SessionEnd",
})

# Rule data for HK003: the accepted values of a hook entry's "type" field.
# Source: .claude/vendor/sources/hooks-2026-08-28-0408.md, "Common fields" table.
# Provenance claim HK003.valid_hook_types.
VALID_HOOK_TYPES: frozenset[str] = frozenset({"command", "http", "mcp_tool", "prompt", "agent"})

# Rule data for HK003: the companion field(s) each hook type requires.
# mcp_tool requires both "server" and "tool" (source: "MCP tool hook fields"
# section of the same doc), which a single-field mapping cannot express.
_REQUIRED_FIELDS_BY_HOOK_TYPE: dict[str, tuple[str, ...]] = {
    "command": ("command",),
    "prompt": ("prompt",),
    "http": ("url",),
    "agent": ("prompt",),
    "mcp_tool": ("server", "tool"),
}


# ---------------------------------------------------------------------------
# Shared scanning helpers
#
# Used by both detection (below) and repair (``HookValidator.fix``) so the two
# can never disagree about which hook entries and scripts are in scope.
# ---------------------------------------------------------------------------


def is_file_path_reference(command: str) -> bool:
    """Return True if *command* looks like a file path rather than a bare shell command.

    File path references start with ``./``, ``../``, ``/`` (absolute), or
    ``${CLAUDE_PLUGIN_ROOT}/``.  Bare shell commands (e.g. ``echo hello``,
    ``python3 -m pytest``) do not match.

    Args:
        command: The ``command`` value from a hook entry.

    Returns:
        True if command is a file path reference, False otherwise.
    """
    return bool(command) and (command.startswith(("./", "../", "/", "${CLAUDE_PLUGIN_ROOT}/")))


def find_hook_plugin_dir(base_dir: Path) -> Path:
    """Find the hook plugin directory by checking .claude-plugin/ directory existence.

    Unlike find_plugin_dir, this checks for the presence of the
    ``.claude-plugin/`` directory rather than ``plugin.json``.  It also returns
    *base_dir* as a fallback rather than None, because hook files may exist in a
    plugin directory even when plugin.json is absent or malformed.

    Args:
        base_dir: Base directory to search from.

    Returns:
        Plugin directory path if .claude-plugin/ exists, otherwise base_dir.
    """
    current = base_dir.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".claude-plugin").is_dir():
            return parent
    return base_dir


def iter_hook_entries(hooks_dict: Mapping[str, JsonValue]) -> Iterator[JsonValue]:
    """Yield every hook entry dict in a hooks configuration mapping.

    Walks ``{event_type: [{"hooks": [entry, ...]}, ...]}``, skipping anything
    not shaped that way.  Structural complaints about the skipped values are
    HK003's job, not this helper's.

    Args:
        hooks_dict: Hooks configuration mapping event types to hook groups.

    Yields:
        Each hook entry dict found, in document order.
    """
    for groups in hooks_dict.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            hook_entries = group.get("hooks", [])
            if not isinstance(hook_entries, list):
                continue
            for entry in hook_entries:
                if isinstance(entry, dict):
                    yield entry


def iter_command_scripts(hook_entries: Iterable[object], base_dir: Path) -> Iterator[tuple[str, Path]]:
    """Yield ``(command, resolved_path)`` for every file-path command reference.

    Entries that are not ``type: command``, or whose command is a bare shell
    command rather than a file path, are skipped.  ``${CLAUDE_PLUGIN_ROOT}`` is
    substituted with the detected plugin root and relative paths are resolved
    against *base_dir*.  Existence is not checked here — callers decide what a
    missing file means.

    Args:
        hook_entries: Hook entry objects to inspect.
        base_dir: Directory used as the resolution base for relative paths.

    Yields:
        Tuples of the original command string and its resolved filesystem path.
    """
    plugin_root = find_hook_plugin_dir(base_dir)

    for entry in hook_entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != "command":
            continue

        command = entry.get("command", "")
        if not isinstance(command, str) or not is_file_path_reference(command):
            continue

        # Substitute ${CLAUDE_PLUGIN_ROOT} with the detected plugin root
        resolved_command = command.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))

        resolved_path = Path(resolved_command)
        if not resolved_path.is_absolute():
            resolved_path = (base_dir / resolved_command).resolve()

        yield command, resolved_path


def load_hooks_object(path: Path) -> tuple[dict[str, JsonValue] | None, list[ValidationIssue]]:
    """Read *path* and return its validated top-level ``"hooks"`` object.

    Ingestion happens in :mod:`skilllint.boundary.hooks_json_ingest`, which
    validates the untrusted payload with Pydantic and returns either a concrete
    mapping or a :class:`~skilllint.boundary.hooks_json_ingest.HooksJsonDefect`.
    This function only turns a defect into the HK001 issue that reports it --
    the wording, severity and docs anchor belong to the rule, not the boundary.

    Args:
        path: Path to a hooks.json file.

    Returns:
        ``(hooks_object, [])`` when the file is structurally valid, otherwise
        ``(None, [issue])`` with the HK001 issue describing the failure.
    """
    result = ingest_hooks_json(path)
    if isinstance(result, HooksJsonDefect):
        return None, [
            _make_issue(
                field=result.field, severity="error", message=result.message, code="HK001", suggestion=result.suggestion
            )
        ]
    return result, []


# ---------------------------------------------------------------------------
# HK001 — Invalid hooks.json structure
# ---------------------------------------------------------------------------


@skilllint_rule(
    "HK001",
    severity="error",
    category="hook",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_hk001(path: Path) -> list[ValidationIssue]:
    """## HK001 — Invalid hooks.json structure

    The ``hooks.json`` file has an invalid top-level structure.  This rule
    fires when:

    - The file cannot be read (I/O error).
    - The file contains malformed JSON that cannot be parsed.
    - The parsed JSON is not an object, or does not have a top-level
      ``"hooks"`` key.
    - The value of the ``"hooks"`` key is not an object (dict).

    A valid ``hooks.json`` must have the shape:

    ```json
    {
      "hooks": {
        "EventType": [...]
      }
    }
    ```

    HK001 is terminal: when it fires there is no usable hooks object, so
    HK002-HK005 do not run against the file.

    **Fix:** Ensure ``hooks.json`` is valid JSON containing a top-level
    ``"hooks"`` key whose value is an object:

    ```json
    {
      "hooks": {
        "PreToolUse": [
          {
            "hooks": [
              {"type": "command", "command": "./hooks/pre-tool.sh"}
            ]
          }
        ]
      }
    }
    ```

    Args:
        path: Path to the hooks.json file to read and parse.

    Returns:
        A single-issue list describing the structural failure, or an empty list
        when the file parses to a valid top-level hooks object.

    <!-- examples: HK001 -->
    """
    return load_hooks_object(path)[1]


# ---------------------------------------------------------------------------
# HK002 — Invalid event type in hooks.json
# ---------------------------------------------------------------------------


@skilllint_rule(
    "HK002",
    severity="error",
    category="hook",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_hk002(hooks_config: Mapping[str, JsonValue]) -> list[ValidationIssue]:
    """## HK002 — Invalid event type in hooks.json

    A key under ``hooks`` in ``hooks.json`` is not a recognised Claude Code
    event type.  Claude Code silently ignores unknown event types, but
    ``skilllint`` flags them so misspelled or outdated event names are caught
    before deployment.

    Valid event types include: ``SessionStart``, ``Setup``,
    ``InstructionsLoaded``, ``UserPromptSubmit``, ``UserPromptExpansion``,
    ``PreToolUse``, ``PermissionRequest``, ``PermissionDenied``,
    ``PostToolUse``, ``PostToolUseFailure``, ``PostToolBatch``,
    ``Notification``, ``MessageDisplay``, ``SubagentStart``,
    ``SubagentStop``, ``Stop``, ``StopFailure``, ``TeammateIdle``,
    ``TaskCreated``, ``TaskCompleted``, ``ConfigChange``, ``CwdChanged``,
    ``DirectoryAdded``, ``FileChanged``, ``WorktreeCreate``,
    ``WorktreeRemove``, ``PreCompact``, ``PostCompact``, ``PreModelSwitch``,
    ``PostModelSwitch``, ``Elicitation``, ``ElicitationResult``,
    ``SessionEnd``.

    **Source:** the module-level ``VALID_EVENT_TYPES`` frozenset — the
    canonical set of accepted event type strings.

    **Fix:** Replace the unrecognised event type with a valid one:

    ```json
    {
      "hooks": {
        "PreToolUse": [...]
      }
    }
    ```

    Args:
        hooks_config: The parsed top-level ``"hooks"`` object.

    Returns:
        One issue per key that is not a recognised event type.

    <!-- examples: HK002 -->
    """
    return [
        _make_issue(
            field=f"hooks.{event_type}",
            severity="error",
            message=f"Invalid event type: '{event_type}'",
            code="HK002",
            suggestion=f"Valid event types: {', '.join(sorted(VALID_EVENT_TYPES))}",
        )
        for event_type in hooks_config
        if event_type not in VALID_EVENT_TYPES
    ]


# ---------------------------------------------------------------------------
# HK003 — Invalid hook entry structure
# ---------------------------------------------------------------------------


def _check_hook_entry(entry: JsonValue, field_prefix: str) -> list[ValidationIssue]:
    """Validate a single hook entry.

    Args:
        entry: The hook entry object to validate.
        field_prefix: JSON path of this entry, used to build issue fields.

    Returns:
        HK003 issues for this entry; empty when it is well formed.
    """
    if not isinstance(entry, dict):
        return [_make_issue(field=field_prefix, severity="error", message="Hook entry must be an object", code="HK003")]

    hook_type = entry.get("type")
    if not isinstance(hook_type, str) or hook_type not in VALID_HOOK_TYPES:
        return [
            _make_issue(
                field=f"{field_prefix}.type",
                severity="error",
                message=f"Invalid or missing hook type: '{hook_type}'",
                code="HK003",
                suggestion=f"Hook type must be one of: {', '.join(sorted(VALID_HOOK_TYPES))}",
            )
        ]

    return [
        _make_issue(
            field=f"{field_prefix}.{required_field}",
            severity="error",
            message=f"Hook type '{hook_type}' requires '{required_field}' field",
            code="HK003",
        )
        for required_field in _REQUIRED_FIELDS_BY_HOOK_TYPE[hook_type]
        if required_field not in entry
    ]


def _check_hook_group(group: JsonValue, event_type: str, group_idx: int) -> list[ValidationIssue]:
    """Validate a single hook group within an event type.

    Args:
        group: The hook group object to validate.
        event_type: Parent event type name.
        group_idx: Index of this group in the event type array.

    Returns:
        HK003 issues for this group and its entries.
    """
    field = f"hooks.{event_type}[{group_idx}]"

    if not isinstance(group, dict):
        return [_make_issue(field=field, severity="error", message="Hook group must be an object", code="HK003")]

    hook_entries = group.get("hooks")
    if not isinstance(hook_entries, list):
        return [
            _make_issue(
                field=field,
                severity="error",
                message="Hook group must have 'hooks' array",
                code="HK003",
                suggestion='Each hook group needs: {"hooks": [...]}',
            )
        ]

    issues: list[ValidationIssue] = []
    for entry_idx, entry in enumerate(hook_entries):
        issues.extend(_check_hook_entry(entry, f"{field}.hooks[{entry_idx}]"))
    return issues


@skilllint_rule(
    "HK003",
    severity="error",
    category="hook",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_hk003(hooks_config: Mapping[str, JsonValue]) -> list[ValidationIssue]:
    """## HK003 — Invalid hook entry structure

    A hook group or hook entry within ``hooks.json`` is structurally invalid.
    This rule fires when any of the following are true:

    - An event type value is not a list of hook groups.
    - A hook group is not an object.
    - A hook group does not contain a ``"hooks"`` key with a list value.
    - A hook entry is not an object.
    - A hook entry has an invalid or missing ``"type"`` field.  Valid types
      are ``"command"``, ``"http"``, ``"mcp_tool"``, ``"prompt"``, and
      ``"agent"``.
    - A ``"command"`` entry is missing the required ``"command"`` field.
    - A ``"prompt"`` entry is missing the required ``"prompt"`` field.
    - An ``"http"`` entry is missing the required ``"url"`` field.
    - An ``"agent"`` entry is missing the required ``"prompt"`` field.
    - An ``"mcp_tool"`` entry is missing the required ``"server"`` and/or
      ``"tool"`` fields.

    Event types that HK002 rejects are skipped: an unrecognised event name is
    reported once, and its contents are not additionally picked apart here.

    **Fix:** Ensure each hook group and entry follows the required schema:

    ```json
    {
      "hooks": {
        "PreToolUse": [
          {
            "hooks": [
              {"type": "command", "command": "./hooks/pre-tool.sh"},
              {"type": "prompt", "prompt": "Summarise changes before tool use."}
            ]
          }
        ]
      }
    }
    ```

    Args:
        hooks_config: The parsed top-level ``"hooks"`` object.

    Returns:
        One issue per structural defect found in the hook groups and entries.

    <!-- examples: HK003 -->
    """
    issues: list[ValidationIssue] = []

    for event_type, hook_groups in hooks_config.items():
        if event_type not in VALID_EVENT_TYPES:
            # Already reported by HK002; its contents are not inspected.
            continue

        if not isinstance(hook_groups, list):
            issues.append(
                _make_issue(
                    field=f"hooks.{event_type}",
                    severity="error",
                    message=f"Event type '{event_type}' value must be an array of hook groups",
                    code="HK003",
                )
            )
            continue

        for group_idx, group in enumerate(hook_groups):
            issues.extend(_check_hook_group(group, event_type, group_idx))

    return issues


# ---------------------------------------------------------------------------
# HK004 — Hook script referenced but not found
# ---------------------------------------------------------------------------


@skilllint_rule(
    "HK004",
    severity="error",
    category="hook",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_hk004(hook_entries: Iterable[object], base_dir: Path) -> list[ValidationIssue]:
    """## HK004 — Hook script referenced but not found

    A ``"command"`` hook entry points to a file path (starting with ``./``,
    ``../``, ``/``, or ``${CLAUDE_PLUGIN_ROOT}/``) that does not exist on the
    filesystem.  Claude Code will fail to execute the hook at runtime.

    Bare shell commands (e.g. ``echo hello``, ``python3 -m pytest``) are
    intentionally excluded from this check.

    **Fix:** Create the missing script at the referenced path, or update the
    path to point to an existing executable:

    ```bash
    # Create the missing hook script
    mkdir -p hooks
    cat > hooks/pre-tool.sh << 'EOF'
    #!/usr/bin/env bash
    echo "PreToolUse hook triggered"
    EOF
    git add hooks/pre-tool.sh
    git update-index --chmod=+x hooks/pre-tool.sh
    ```

    Args:
        hook_entries: Hook entry objects to inspect.
        base_dir: Directory used as the resolution base for relative paths.

    Returns:
        One issue per file-path command reference that does not exist on disk.

    <!-- examples: HK004 -->
    """
    return [
        _make_issue(
            field="command",
            severity="error",
            message=f"Hook script not found: {command}",
            code="HK004",
            suggestion=f"Create the script at {resolved_path} or fix the path",
        )
        for command, resolved_path in iter_command_scripts(hook_entries, base_dir)
        if not resolved_path.exists()
    ]


# ---------------------------------------------------------------------------
# HK005 — Hook script exists but is not executable
# ---------------------------------------------------------------------------


@skilllint_rule(
    "HK005",
    severity="warning",
    category="hook",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_hk005(hook_entries: Iterable[object], base_dir: Path) -> list[ValidationIssue]:
    """## HK005 — Hook script exists but is not executable

    A ``"command"`` hook entry references a script that exists on disk but
    does not have the execute permission bit set.  Claude Code will fail to
    run the script at hook invocation time.

    The execute bit is checked via the Git index when the file is tracked by
    Git (cross-platform reliable), falling back to ``os.access(X_OK)`` when
    the file is not tracked.

    **Fix:** Mark the script executable.  Prefer the Git method for
    portability:

    ```bash
    # Git-tracked scripts (works on Windows too)
    git update-index --chmod=+x hooks/pre-tool.sh

    # Untracked / non-git scripts
    chmod +x hooks/pre-tool.sh
    ```

    This issue is auto-fixable: run ``skilllint check --fix`` to apply the
    executable bit automatically.  The repair lives on ``HookValidator.fix``.

    Args:
        hook_entries: Hook entry objects to inspect.
        base_dir: Directory used as the resolution base for relative paths.

    Returns:
        One warning per existing script that lacks the execute bit.

    <!-- examples: HK005 -->
    """
    # Deferred import: plugin_validator imports rules/, so the Git helper it
    # owns cannot be imported here at module level.
    from skilllint.plugin_validator import _git_file_has_execute_bit  # noqa: PLC0415

    issues: list[ValidationIssue] = []

    for command, resolved_path in iter_command_scripts(hook_entries, base_dir):
        if not resolved_path.exists():
            continue

        # Use Git's tracked mode when available for cross-platform consistency.
        # On Windows, os.access(X_OK) is unreliable; Git check ensures plugins
        # that pass on Windows will also pass on Linux.
        git_exec = _git_file_has_execute_bit(resolved_path)
        if git_exec is False:
            issues.append(
                _make_issue(
                    field="command",
                    severity="warning",
                    message=f"Hook script is not executable in Git: {command}",
                    code="HK005",
                    suggestion=f"Run: git update-index --chmod=+x {resolved_path}",
                )
            )
        elif git_exec is None and not os.access(resolved_path, os.X_OK):
            # Fallback when not in Git: os.access works on Unix only
            issues.append(
                _make_issue(
                    field="command",
                    severity="warning",
                    message=f"Hook script is not executable: {command}",
                    code="HK005",
                    suggestion=f"Run: chmod +x {resolved_path}",
                )
            )

    return issues


__all__ = [
    "VALID_EVENT_TYPES",
    "VALID_HOOK_TYPES",
    "check_hk001",
    "check_hk002",
    "check_hk003",
    "check_hk004",
    "check_hk005",
    "find_hook_plugin_dir",
    "is_file_path_reference",
    "iter_command_scripts",
    "iter_hook_entries",
    "load_hooks_object",
]
