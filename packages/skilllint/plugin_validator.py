"""Plugin validator for Claude Code plugins.

Validates:
- Frontmatter schema (skills, agents, commands)
- Plugin structure (plugin.json)
- Skill complexity (token-based)
- Internal links
- Progressive disclosure structure
- Plugin completeness

Token-based complexity measurement replaces line counting for accurate AI cost estimation.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import stat
import subprocess
import sys
from io import TextIOWrapper

import msgspec.json

# Module-level logger for debug output
_logger = logging.getLogger(__name__)

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dataclasses import dataclass
from enum import StrEnum
from io import StringIO
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Annotated, Literal, NoReturn, Protocol, TypeAlias, cast

# YAML/JSON at the edge: dict, list, or JSON-serializable scalars. More specific than Any.
YamlValue: TypeAlias = dict[str, "YamlValue"] | list["YamlValue"] | str | int | float | bool | None

import contextlib

import typer
from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError
from git.index.fun import entry_key
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

import skilllint.rules  # ruff: ignore[unused-import] — ensures all 15 series modules register into RULE_REGISTRY
from skilllint.adapters import PlatformAdapter, load_adapters, matches_file
from skilllint.adapters.claude_code import ClaudeCodeAdapter
from skilllint.cli_docs import docs_app
from skilllint.record_export import (
    build_svg_title as _build_svg_title,
    export_recording as _export_recording,
    make_recording_console as _make_recording_console,
)
from skilllint.rule_registry import rule_authority, rule_reference
from skilllint.rules.ag_series import check_ag001, check_ag002, check_ag003
from skilllint.rules.as_series import run_as_series
from skilllint.rules.fm_series import check_fm001, check_fm004, check_fm007, check_fm010
from skilllint.rules.hk_series import (
    check_hk002,
    check_hk003,
    check_hk004,
    check_hk005,
    find_hook_plugin_dir,
    is_file_path_reference,
    iter_command_scripts,
    iter_hook_entries,
    load_hooks_object,
)
from skilllint.rules.lk_series import check_lk001
from skilllint.rules.nr_series import check_nr001, check_nr002
from skilllint.rules.pd_series import check_pd001, check_pd002, check_pd003
from skilllint.rules.pl_series import (
    check_pl001,
    check_pl002,
    check_pl003,
    check_pl004,
    check_pl005,
    check_pl006,
    claude_validation_failure_issue,
)
from skilllint.rules.pr_series import (
    check_pr001,
    check_pr002,
    check_pr003,
    check_pr004,
    check_pr005,
    find_actual_capabilities,
    parse_registered_paths,
)
from skilllint.rules.sk_series import check_sk004, check_sk005
from skilllint.rules.sl_series import check_sl001, iter_symlinks
from skilllint.rules.tc_series import check_tc001
from skilllint.scan_runtime import ScanContext
from skilllint.token_counter import TOKEN_ERROR_THRESHOLD, TOKEN_WARNING_THRESHOLD, count_tokens
from skilllint.version import __version__

from .frontmatter_core import (
    AgentFrontmatter,
    CommandFrontmatter,
    SkillFrontmatter,
    extract_frontmatter,
    fix_skill_name_field,
    get_frontmatter_model,
)
from .scan_runtime import _resolve_filter_and_expand_paths, run_validation_loop

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from pydantic_core import ErrorDetails


# Module-level ruamel.yaml safe-mode instance (replaces yaml.safe_load)
_yaml_safe = YAML(typ="safe")

# Round-trip YAML instance for dumping with format preservation
_rt_yaml = YAML(typ="rt")
_rt_yaml.preserve_quotes = False
_rt_yaml.width = 10000  # prevent line wrapping

# Platform adapter registry — loaded once at module level.
# Keys are adapter IDs (e.g. "claude_code", "cursor", "codex").
ADAPTERS: dict[str, object] = {a.id(): a for a in load_adapters()}


def _safe_load_yaml(text: str) -> YamlValue:
    """Parse a YAML string using ruamel.yaml safe loader.

    Args:
        text: YAML text to parse (frontmatter content, no --- delimiters).

    Returns:
        Parsed YAML data (dict, list, scalar, or None).
    """
    if not text or not text.strip():
        return {}
    return _yaml_safe.load(text)


def find_plugin_dir(path: Path) -> Path | None:
    """Find the plugin directory containing .claude-plugin/plugin.json.

    Walks up the directory tree from *path* (or its parent, if *path* is a
    file) looking for a ``.claude-plugin/plugin.json`` marker.

    Args:
        path: Path to start searching from.

    Returns:
        Plugin directory path, or None if not found.
    """
    search_path = path.parent if path.is_file() else path
    for parent in [search_path, *search_path.parents]:
        if (parent / ".claude-plugin" / "plugin.json").exists():
            return parent
    return None


def _dump_yaml(data: dict[str, YamlValue]) -> str:
    """Serialize a dict to YAML using the round-trip handler.

    Preserves key insertion order. Values containing ': ' are wrapped in
    double quotes so YAML parsers handle them correctly.

    Args:
        data: Dictionary to serialize.

    Returns:
        YAML string (may include trailing newline).
    """
    prepared: dict[str, YamlValue] = {}
    for key, value in data.items():
        if isinstance(value, str) and ": " in value:
            prepared[key] = DoubleQuotedScalarString(value)
        else:
            prepared[key] = value

    buf = StringIO()
    _rt_yaml.dump(prepared, buf)
    return buf.getvalue()


def _fix_unquoted_colons(frontmatter_text: str) -> tuple[str, list[str], list[str]]:
    """Quote description (and similar string) values that contain unquoted colons.

    Detects lines of the form ``key: value: more`` where the unquoted colon
    causes a YAML parse error and wraps the value in double-quotes.

    Args:
        frontmatter_text: Raw YAML frontmatter (without ``---`` delimiters).

    Returns:
        Tuple of (possibly-fixed frontmatter text, list of fix descriptions,
        list of field names that were fixed).  The field names list has one entry
        per fixed line and is used by callers to emit FM009 info issues.
    """
    fixes: list[str] = []
    fixed_fields: list[str] = []
    lines = frontmatter_text.splitlines(keepends=True)
    new_lines = []

    # Regex: key: value where value contains an unquoted colon
    # Only matches simple single-line scalar values, not block scalars or already-quoted values
    unquoted_colon_re = re.compile(r'^(\s*([\w-]+):\s+)([^\'"\[\{|>].+:.*)$')

    for line in lines:
        m = unquoted_colon_re.match(line.rstrip("\n"))
        if m:
            prefix = m.group(1)
            field_name = m.group(2)
            value = m.group(3)
            # Escape any existing double-quotes inside the value
            escaped = value.replace('"', '\\"')
            new_line = f'{prefix}"{escaped}"\n'
            fixes.append("Quoted description value containing unquoted colon")
            fixed_fields.append(field_name)
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    if fixes:
        return "".join(new_lines), fixes, fixed_fields
    return frontmatter_text, [], []


def safe_load_yaml_with_colon_fix(fm_text: str) -> tuple[dict | None, str | None, list[str], str]:
    """Parse YAML frontmatter, attempting unquoted-colon auto-fix on failure.

    Consolidates the try/except YAMLError -> _fix_unquoted_colons -> retry
    pattern used in multiple call sites.

    Args:
        fm_text: Raw YAML frontmatter text (without ``---`` delimiters).

    Returns:
        Tuple of (parsed_dict, yaml_error_msg, colon_fixed_fields, used_text).
        - parsed_dict: The parsed YAML dict, or None if parsing failed.
        - yaml_error_msg: Error message string if YAML parsing failed
          even after colon fix, or None on success.
        - colon_fixed_fields: List of field names where unquoted colons
          were detected and auto-fixed (empty if no fix was needed).
        - used_text: The frontmatter text that was successfully parsed
          (may be the colon-fixed version if auto-fix was applied).
    """
    try:
        data = _safe_load_yaml(fm_text)
    except YAMLError as exc:
        fixed_fm, colon_fixes, colon_fields = _fix_unquoted_colons(fm_text)
        if colon_fixes:
            try:
                data = _safe_load_yaml(fixed_fm)
            except YAMLError:
                pass
            else:
                parsed = dict(data) if isinstance(data, dict) else None
                return parsed, None, colon_fields, fixed_fm
        return None, str(exc), [], fm_text
    else:
        parsed = dict(data) if isinstance(data, dict) else None
        return parsed, None, [], fm_text


SKILL_FRONTMATTER_SCHEMA_URL = "https://code.claude.com/docs/en/skills.md#frontmatter-reference"
# PLUGIN_MANIFEST_SCHEMA_URL, MARKETPLACE_MANIFEST_SCHEMA_URL, MARKETPLACE_JSON_ROOT_KEYS and
# MARKETPLACE_METADATA_RELOCATABLE_KEYS are rule data and live in rules/pl_series.py.

# FILTER_TYPE_MAP and DEFAULT_SCAN_PATTERNS live in scan_runtime.py
# and are re-imported at the top of this module.

# Name format — matches agentskills.io/specification and init_skill.py convention:
# lowercase a-z/0-9/hyphen, no leading/trailing/consecutive hyphens.
NAME_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"


def _normalize_skill_name(name: str) -> str:
    """Normalize name to schema format: lowercase, hyphens only, no leading/trailing/consecutive hyphens.

    Returns:
        Normalized name string.
    """
    s = name.lower().replace("_", "-")
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


# Trigger phrase requirements — duplicated from sk_series._REQUIRED_TRIGGER_PHRASES.
# Dead code: DescriptionValidator._check_description_quality delegates to check_sk005.
# Kept only for import compatibility; consumers should import from sk_series instead.
REQUIRED_TRIGGER_PHRASES = [
    "use when",
    "use this",
    "use on",
    "used when",
    "used by",
    "when ",
    "trigger",
    "activate",
    "load this",
    "load when",
    "invoke",
]

# ============================================================================
# ERROR CODE CONSTANTS
# ============================================================================


class ErrorCode(StrEnum):
    """Validation error codes. Use as type hint for code parameters."""

    # Frontmatter (FM001-FM010)
    FM001 = "FM001"  # Missing required field (name, description)
    FM002 = "FM002"  # Invalid YAML syntax
    FM003 = "FM003"  # Frontmatter not closed with `---`
    FM004 = "FM004"  # Forbidden multiline indicator (`>-`, `|-`)
    FM005 = "FM005"  # Field type mismatch (expected string/bool)
    FM006 = "FM006"  # Invalid field value (model not in enum)
    FM007 = "FM007"  # Tools field is YAML array (not CSV string)
    FM009 = "FM009"  # Unquoted description with colons
    FM010 = "FM010"  # Name pattern invalid (not lowercase-hyphens)

    # Skill (SK004-SK009)

    SK004 = "SK004"  # Description too short (minimum 20 characters)
    SK005 = "SK005"  # Description missing trigger phrases
    SK006 = "SK006"  # Token count exceeds TOKEN_WARNING_THRESHOLD
    SK007 = "SK007"  # Token count exceeds TOKEN_ERROR_THRESHOLD (must split)
    SK008 = "SK008"  # Skill directory name violates naming convention
    SK009 = "SK009"  # Plugin uses manual skill selection (overrides auto-discovery)

    # Link (LK001)
    LK001 = "LK001"  # Broken internal link (file does not exist)

    # Progressive Disclosure (PD001-PD003)
    PD001 = "PD001"  # No `references/` directory found
    PD002 = "PD002"  # No `assets/` directory found
    PD003 = "PD003"  # No `scripts/` directory found

    # Plugin (PL001-PL006)
    PL001 = "PL001"  # Missing `plugin.json` file
    PL002 = "PL002"  # Invalid JSON syntax in `plugin.json`
    PL003 = "PL003"  # Missing required field `name` in plugin.json
    PL004 = "PL004"  # Component path does not start with `./`
    PL005 = "PL005"  # Referenced component file does not exist
    PL006 = "PL006"  # marketplace.json has invalid top-level keys (use `metadata`)

    # Command (CM001)
    CM001 = "CM001"  # Command-specific validation (reserved)

    # Hook (HK001-HK005)
    HK001 = "HK001"  # Invalid hooks.json structure
    HK002 = "HK002"  # Invalid event type in hooks.json
    HK003 = "HK003"  # Invalid hook entry structure
    HK004 = "HK004"  # Hook script referenced but not found
    HK005 = "HK005"  # Hook script exists but is not executable

    # Namespace Reference (NR001-NR002)
    NR001 = "NR001"  # Namespace reference target does not exist
    NR002 = "NR002"  # Namespace reference points outside plugin directory

    # Symlink (SL001)
    SL001 = "SL001"  # Symlink target has trailing whitespace/newlines

    # Token Count (TC001)
    TC001 = "TC001"  # Token count info (total, frontmatter, body)

    # Plugin Registration (PR001-PR005)
    PR001 = "PR001"  # Capability exists but not explicitly registered in plugin.json
    PR002 = "PR002"  # Registered capability path does not exist
    PR003 = "PR003"  # Plugin metadata fields (repository, homepage, author) not populated
    PR004 = "PR004"  # Plugin metadata repository URL mismatches git remote URL
    PR005 = "PR005"  # Registered command path is a skill directory (contains SKILL.md)

    # Plugin Agent Frontmatter (PA001)
    PA001 = "PA001"  # Plugin agent: hooks/mcpServers/permissionMode unsupported per Anthropic (ignored at load)

    # Agent frontmatter (AG001-AG003)
    AG001 = "AG001"  # Agent tools entries all resolve to nothing
    AG002 = "AG002"  # Agent MCP server reference is unknown or incorrectly cased
    AG003 = "AG003"  # Agent skills value contains runtime-ignored entries

    # Cursor adapter (CU001-CU002)
    CU001 = "CU001"  # Required field missing from .mdc frontmatter
    CU002 = "CU002"  # Unknown field in .mdc frontmatter (additionalProperties is false)

    # Codex adapter (CX001-CX002)
    CX001 = "CX001"  # AGENTS.md is empty or structurally invalid
    CX002 = "CX002"  # Unknown field in .rules prefix_rule() block


# Aliases for backward compatibility and concise usage
FM001, FM002, FM003, FM004, FM005, FM006, FM007, FM009, FM010 = (
    ErrorCode.FM001,
    ErrorCode.FM002,
    ErrorCode.FM003,
    ErrorCode.FM004,
    ErrorCode.FM005,
    ErrorCode.FM006,
    ErrorCode.FM007,
    ErrorCode.FM009,
    ErrorCode.FM010,
)
SK004, SK005, SK006, SK007, SK008, SK009 = (
    ErrorCode.SK004,
    ErrorCode.SK005,
    ErrorCode.SK006,
    ErrorCode.SK007,
    ErrorCode.SK008,
    ErrorCode.SK009,
)
LK001 = ErrorCode.LK001
PD001, PD002, PD003 = ErrorCode.PD001, ErrorCode.PD002, ErrorCode.PD003
PL001, PL002, PL003, PL004, PL005, PL006 = (
    ErrorCode.PL001,
    ErrorCode.PL002,
    ErrorCode.PL003,
    ErrorCode.PL004,
    ErrorCode.PL005,
    ErrorCode.PL006,
)
CM001 = ErrorCode.CM001
HK001, HK002, HK003, HK004, HK005 = (
    ErrorCode.HK001,
    ErrorCode.HK002,
    ErrorCode.HK003,
    ErrorCode.HK004,
    ErrorCode.HK005,
)
NR001, NR002 = ErrorCode.NR001, ErrorCode.NR002
SL001 = ErrorCode.SL001
PR001, PR002, PR003, PR004, PR005 = (
    ErrorCode.PR001,
    ErrorCode.PR002,
    ErrorCode.PR003,
    ErrorCode.PR004,
    ErrorCode.PR005,
)
PA001 = ErrorCode.PA001
AG001, AG002, AG003 = ErrorCode.AG001, ErrorCode.AG002, ErrorCode.AG003

# ============================================================================
# VALIDATOR OWNERSHIP
# ============================================================================


class ValidatorOwnership(StrEnum):
    """Ownership classification for validators.

    Used to distinguish between schema-backed validation (hard failures)
    and lint-rule validation (warnings/findings).
    """

    SCHEMA = "schema"  # Schema-backed validation (hard failures = exit code 1)
    LINT = "lint"  # Lint rules (warnings = exit code 0 with findings)


# Mapping from validator class name to ownership classification.
# This establishes the explicit boundary between schema and lint validation.
VALIDATOR_OWNERSHIP: dict[str, ValidatorOwnership] = {
    # Schema-backed validators (hard failures)
    "FrontmatterValidator": ValidatorOwnership.SCHEMA,
    "PluginStructureValidator": ValidatorOwnership.SCHEMA,
    "PluginRegistrationValidator": ValidatorOwnership.SCHEMA,
    "HookValidator": ValidatorOwnership.SCHEMA,
    "SymlinkTargetValidator": ValidatorOwnership.SCHEMA,
    # Lint validators (warnings/findings)
    "NameFormatValidator": ValidatorOwnership.LINT,
    "DescriptionValidator": ValidatorOwnership.LINT,
    "ComplexityValidator": ValidatorOwnership.LINT,
    "InternalLinkValidator": ValidatorOwnership.LINT,
    "ProgressiveDisclosureValidator": ValidatorOwnership.LINT,
    "NamespaceReferenceValidator": ValidatorOwnership.LINT,
    "MarkdownTokenCounter": ValidatorOwnership.LINT,
    "AsSeriesValidator": ValidatorOwnership.LINT,
}

# ============================================================================
# RULE TRUTH CLASSIFICATION (S04 — M002)
# ============================================================================
# Justified errors (genuine schema violations):
#   FM003 — frontmatter required (agents/skills/commands need it to function)
#   FM005 — field type mismatch (schema violation, not style preference)
# Downgraded to warning (runtime-accepted patterns):
#   FM004 — multiline YAML (|, >, |-, >-) accepted by Claude Code runtime
#   FM007 — tools field as YAML array accepted by Claude Code runtime

# Evidence: Official repos (claude-plugins-official, skills, claude-code-plugins)
#   contain these patterns and Claude Code runtime accepts them.


def get_validator_ownership(validator: Validator) -> ValidatorOwnership:
    """Get the ownership classification for a validator.

    Args:
        validator: A validator instance.

    Returns:
        ValidatorOwnership enum value (SCHEMA or LINT).

    Defaults to LINT for unknown validators (conservative assumption).
    """
    class_name = type(validator).__name__
    return VALIDATOR_OWNERSHIP.get(class_name, ValidatorOwnership.LINT)


# Mapping from validator class name to constraint scope applicability.
# Validators that are provider-specific will only run when the adapter's
# constraint_scopes() includes "provider_specific".
VALIDATOR_CONSTRAINT_SCOPES: dict[str, set[str]] = {
    # Shared validators (run for all providers)
    "FrontmatterValidator": {"shared", "provider_specific"},
    "PluginStructureValidator": {"shared", "provider_specific"},
    "PluginRegistrationValidator": {"shared", "provider_specific"},
    "HookValidator": {"shared", "provider_specific"},
    "SymlinkTargetValidator": {"shared", "provider_specific"},
    "NameFormatValidator": {"shared", "provider_specific"},
    "DescriptionValidator": {"shared", "provider_specific"},
    "ComplexityValidator": {"shared", "provider_specific"},
    "InternalLinkValidator": {"shared", "provider_specific"},
    "ProgressiveDisclosureValidator": {"shared", "provider_specific"},
    "NamespaceReferenceValidator": {"shared", "provider_specific"},
    "MarkdownTokenCounter": {"shared", "provider_specific"},
    "AsSeriesValidator": {"shared", "provider_specific"},
}


def get_validator_constraint_scopes(class_name: str) -> set[str]:
    """Get the constraint scopes a validator applies to.

    Args:
        class_name: Validator class name (e.g. "FrontmatterValidator").

    Returns:
        Set of constraint scope strings (e.g. {"shared", "provider_specific"}).
        Defaults to {"shared", "provider_specific"} for unknown validators.
    """
    return VALIDATOR_CONSTRAINT_SCOPES.get(class_name, {"shared", "provider_specific"})


def filter_validators_by_constraint_scopes(
    validators: Sequence[Validator], constraint_scopes: set[str]
) -> list[Validator]:
    """Filter validators based on provider constraint scopes.

    Validators are included if their applicable constraint scopes intersect
    with the provider's constraint_scopes().

    Args:
        validators: List of validator instances.
        constraint_scopes: Set of constraint scope strings from adapter.

    Returns:
        Filtered list of validators that match the constraint scopes.
    """
    filtered: list[Validator] = []
    for validator in validators:
        class_name = type(validator).__name__
        validator_scopes = get_validator_constraint_scopes(class_name)
        # Include validator if there's any intersection
        if validator_scopes & constraint_scopes:
            filtered.append(validator)
    return filtered


# Claude CLI timeout
CLAUDE_TIMEOUT = 3  # seconds
GIT_MODE_EXECUTABLE = 0o100755  # Git mode for executable files (100755)

# Filenames exempt from frontmatter requirement (case-sensitive)
FRONTMATTER_EXEMPT_FILENAMES: frozenset[str] = frozenset({
    "AGENT.md",
    "AGENTS.md",
    "GEMINI.md",
    "CLAUDE.md",
    "README.md",
})


def _git_bash_path() -> str | None:
    """Resolve path to bash.exe for CLAUDE_CODE_GIT_BASH_PATH.

    Claude Code on Windows requires git-bash. Tries:
    1. shutil.which("git-bash") — if found, use sibling bin/bash.exe
    2. On Windows: LOCALAPPDATA/Programs/Git — check git-bash.exe exists, use bin/bash.exe

    If resolved, sets os.environ["CLAUDE_CODE_GIT_BASH_PATH"] and returns the path.

    Returns:
        Resolved path to bash.exe, or None if not found
    """
    # Already set
    existing = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH", "").strip()
    if existing and Path(existing).is_file():
        return existing

    # Try PATH for git-bash only (not generic bash — claude requires Git Bash)
    found = shutil.which("git-bash")
    if found:
        path = Path(found).resolve()
        if path.is_file() and path.name.lower() == "git-bash.exe":
            bash_exe = path.parent / "bin" / "bash.exe"
            if bash_exe.is_file():
                resolved = str(bash_exe.resolve())
                os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = resolved
                return resolved
            # Shims may point elsewhere; if path is git-bash.exe, try parent/bin
            # Already tried above; fall through to Windows fallback if no bin/bash

    # Windows fallback: AppData\Local\Programs\Git\git-bash.exe
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA", "").strip()
        if localappdata:
            base = Path(localappdata) / "Programs" / "Git"
            git_bash_exe = base / "git-bash.exe"
            if git_bash_exe.is_file():
                bash_exe = base / "bin" / "bash.exe"
                if bash_exe.is_file():
                    resolved = str(bash_exe.resolve())
                    os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = resolved
                    return resolved

    return None


def _should_skip_claude_validate() -> bool:
    """Detect if running in a context where claude CLI validation should be skipped.

    Skips validation when either:
    - CLAUDE_CODE_REMOTE=true (cloud-hosted Claude Code sessions)
    - CLAUDECODE is set (nested Claude Code session detected by Anthropic)

    Returns:
        True if claude plugin validate should be skipped, False otherwise
    """
    # Check for remote cloud session
    if os.environ.get("CLAUDE_CODE_REMOTE", "").lower() == "true":
        return True

    # Check for nested Claude Code session (CLAUDECODE env var set by Anthropic)
    return bool(os.environ.get("CLAUDECODE"))


# ============================================================================
# IGNORE CONFIG (per-plugin .claude-plugin/validator.json)
# ============================================================================

# Type alias: maps relative path prefix → set of suppressed error codes.
IgnoreConfig: TypeAlias = dict[str, list[str]]


@dataclass(frozen=True, slots=True)
class ValidationPolicy:
    """Per-config lint policy; invalid entries are deliberately ignored."""

    thresholds: dict[str, int]
    severity: dict[str, str]
    ignore: IgnoreConfig


DEFAULT_THRESHOLDS: dict[str, int] = {"SK006": TOKEN_WARNING_THRESHOLD, "SK007": TOKEN_ERROR_THRESHOLD}
# Threshold keys must map to an implemented warning/error band.
_THRESHOLD_POLICY_RULES = frozenset({"SK006", "SK007"})
# Severity may be reconfigured for the token-band rules. AS005 shared this band
# and was listed here until it was retired into SK006/SK007.
_SEVERITY_POLICY_RULES = frozenset({"SK006", "SK007"})
_VALID_SEVERITIES = frozenset({"warning", "info"})

_SKILLLINT_CONFIG_FILENAME = ".skilllint.json"


def _load_ignore_dict(config_path: Path) -> IgnoreConfig:
    """Load an IgnoreConfig dict from a JSON file's 'ignore' key.

    Returns empty dict if the file does not exist, cannot be read, or
    does not contain a valid 'ignore' object.

    Args:
        config_path: Path to the JSON config file to read.

    Returns:
        Mapping of relative path prefixes to lists of suppressed error codes.
    """
    if not config_path.is_file():
        return {}
    try:
        raw = msgspec.json.decode(config_path.read_bytes())
    except (OSError, msgspec.DecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    ignore = raw.get("ignore", {})
    if not isinstance(ignore, dict):
        return {}
    return {str(k): [str(c) for c in v] for k, v in ignore.items() if isinstance(v, list)}


def _parse_thresholds(raw: object, config_path: Path, diagnostics: list[str]) -> dict[str, int]:
    """Parse the ``thresholds`` block, appending a diagnostic per rejected entry.

    Args:
        raw: The raw ``thresholds`` value from the decoded config.
        config_path: Config path, used only in diagnostic messages.
        diagnostics: Mutable list that rejected-entry messages are appended to.

    Returns:
        Thresholds with defaults substituted for missing or invalid entries.
    """
    thresholds = dict(DEFAULT_THRESHOLDS)
    if isinstance(raw, dict):
        for raw_code, value in raw.items():
            code = str(raw_code)
            if code not in _THRESHOLD_POLICY_RULES:
                diagnostics.append(f"{config_path}: thresholds.{code} is not a configurable threshold; ignored")
            elif not (isinstance(value, int) and not isinstance(value, bool) and value > 0):
                diagnostics.append(
                    f"{config_path}: thresholds.{code}={value!r} is not a positive integer; using default"
                )
            else:
                thresholds[code] = value
    else:
        diagnostics.append(f"{config_path}: thresholds is not an object; using defaults")
    # Warning must stay below error, or the warning band is unreachable
    # (test_limits.py asserts warning < error as the built-in invariant).
    if thresholds["SK006"] >= thresholds["SK007"]:
        diagnostics.append(
            f"{config_path}: thresholds SK006 ({thresholds['SK006']}) must be below SK007 "
            f"({thresholds['SK007']}); resetting both to defaults"
        )
        thresholds = dict(DEFAULT_THRESHOLDS)
    return thresholds


def _parse_severity(raw: object, config_path: Path, diagnostics: list[str]) -> dict[str, str]:
    """Parse the ``severity`` block, appending a diagnostic per rejected entry.

    Args:
        raw: The raw ``severity`` value from the decoded config.
        config_path: Config path, used only in diagnostic messages.
        diagnostics: Mutable list that rejected-entry messages are appended to.

    Returns:
        Mapping of rule code to a valid configured severity; invalid entries
        are dropped rather than raising.
    """
    severity: dict[str, str] = {}
    if isinstance(raw, dict):
        for raw_code, value in raw.items():
            code = str(raw_code)
            if code not in _SEVERITY_POLICY_RULES:
                diagnostics.append(f"{config_path}: severity.{code} is not a configurable rule; ignored")
            elif not (isinstance(value, str) and value in _VALID_SEVERITIES):
                diagnostics.append(
                    f"{config_path}: severity.{code}={value!r} must be one of {sorted(_VALID_SEVERITIES)}; ignored"
                )
            else:
                severity[code] = value
    else:
        diagnostics.append(f"{config_path}: severity is not an object; using defaults")
    return severity


def _load_policy(config_path: Path) -> tuple[ValidationPolicy, list[str]]:
    """Load thresholds and severity from the existing JSON config.

    Invalid entries fall back to defaults but are reported: a linter config is
    producer input, and silently swallowing a typo hides a real error
    (docs/TYPING_POLICY.md — producer errors must not be silently coerced).

    Returns:
        The policy (defaults for invalid or missing entries) and a list of
        human-readable diagnostics describing every rejected entry.
    """
    defaults = dict(DEFAULT_THRESHOLDS)
    if not config_path.is_file():
        return ValidationPolicy(defaults, {}, {}), []
    try:
        raw = msgspec.json.decode(config_path.read_bytes())
    except (OSError, msgspec.DecodeError) as exc:
        return ValidationPolicy(defaults, {}, {}), [
            f"{config_path}: unreadable or malformed JSON ({exc}); using defaults"
        ]
    if not isinstance(raw, dict):
        return ValidationPolicy(defaults, {}, {}), [f"{config_path}: top-level config is not an object; using defaults"]
    diagnostics: list[str] = []
    thresholds = _parse_thresholds(raw.get("thresholds", {}), config_path, diagnostics)
    severity = _parse_severity(raw.get("severity", {}), config_path, diagnostics)
    return ValidationPolicy(thresholds, severity, _load_ignore_dict(config_path)), diagnostics


def _load_ignore_config(plugin_root: Path) -> IgnoreConfig:
    """Load per-plugin validator ignore config from .claude-plugin/validator.json.

    Args:
        plugin_root: Directory containing .claude-plugin/plugin.json.

    Returns:
        Mapping of relative path prefixes to lists of suppressed error codes.
        Returns empty dict if config file does not exist or cannot be parsed.
    """
    return _load_ignore_dict(plugin_root / ".claude-plugin" / "validator.json")


def _load_skilllint_config(config_file: Path) -> IgnoreConfig:
    """Load ignore config from a .skilllint.json file.

    Args:
        config_file: Path to .skilllint.json.

    Returns:
        Mapping of relative path prefixes to lists of suppressed error codes.
        Returns empty dict if the file does not exist or cannot be parsed.
    """
    return _load_ignore_dict(config_file)


def _resolve_ignore_config(
    path: Path, cache: dict[str, tuple[IgnoreConfig, Path | None]]
) -> tuple[IgnoreConfig, Path | None]:
    """Resolve the ignore config for *path*, walking up the directory tree.

    Checks the cache first (keyed by resolved directory path string). If not
    cached, walks up from ``path.parent`` looking for:

    - ``.claude-plugin/plugin.json`` → loads from ``.claude-plugin/validator.json``
      via :func:`_load_ignore_config`.
    - ``.skilllint.json`` → loads the ``ignore`` dict from that file.

    The first match wins. All directories in the walked chain up to the found
    root are populated in *cache* so sibling files in the same tree do not
    re-walk.

    Args:
        path: Absolute path to the file being validated.
        cache: Mutable per-run cache mapping resolved directory path strings to
            ``(ignore_config, config_root)`` tuples.

    Returns:
        Tuple of (ignore_config, config_root). ``config_root`` is the directory
        that contained the config file, used as the base for relative-path
        prefix matching. Both values are empty / ``None`` when nothing is found.
    """
    start_dir = path.parent.resolve()
    cache_key = str(start_dir)
    if cache_key in cache:
        return cache[cache_key]

    walked: list[Path] = []
    current = start_dir
    result_config: IgnoreConfig = {}
    result_root: Path | None = None

    while True:
        walked.append(current)
        if (current / ".claude-plugin" / "plugin.json").exists():
            result_config = _load_ignore_config(current)
            result_root = current
            break
        skilllint_cfg = current / _SKILLLINT_CONFIG_FILENAME
        if skilllint_cfg.exists():
            result_config = _load_skilllint_config(skilllint_cfg)
            result_root = current
            break
        parent = current.parent
        if parent == current:
            # Filesystem root reached
            break
        current = parent

    # Populate cache for every directory in the walked chain so sibling files
    # in the same tree skip the upward walk entirely.
    result: tuple[IgnoreConfig, Path | None] = (result_config, result_root)
    for walked_dir in walked:
        dir_key = str(walked_dir)
        if dir_key not in cache:
            cache[dir_key] = result

    return result


def _resolve_policy(
    path: Path, cache: dict[str, tuple[ValidationPolicy, Path | None]]
) -> tuple[ValidationPolicy, Path | None]:
    """Resolve first-match policy using the existing discovery and cache.

    Diagnostics for invalid config are emitted once per config file: they fire
    only on a cache miss (the first file that resolves a given config), so a
    1000-file scan warns once, not once per file.

    Returns:
        The policy and its config root, or defaults and ``None``.
    """
    start_dir = path.parent.resolve()
    key = str(start_dir)
    if key in cache:
        return cache[key]
    walked: list[Path] = []
    current = start_dir
    policy = ValidationPolicy(dict(DEFAULT_THRESHOLDS), {}, {})
    root: Path | None = None
    diagnostics: list[str] = []
    while True:
        ancestor_key = str(current)
        # A sibling file already cached this ancestor: reuse it instead of
        # re-walking and re-emitting diagnostics once per sibling skill.
        if ancestor_key in cache:
            policy, root = cache[ancestor_key]
            break
        walked.append(current)
        plugin_cfg = current / ".claude-plugin" / "plugin.json"
        skilllint_cfg = current / _SKILLLINT_CONFIG_FILENAME
        if plugin_cfg.exists():
            policy, diagnostics = _load_policy(current / ".claude-plugin" / "validator.json")
            root = current
            break
        if skilllint_cfg.exists():
            policy, diagnostics = _load_policy(skilllint_cfg)
            root = current
            break
        parent = current.parent
        if parent == current:
            break
        current = parent
    for message in diagnostics:
        typer.echo(f"Warning: {message}", err=True)
    result = (policy, root)
    for directory in walked:
        cache.setdefault(str(directory), result)
    return result


def _is_suppressed(ignore_config: IgnoreConfig, file_path: Path, config_root: Path, code: str) -> bool:
    """Check whether an issue code is suppressed for a given file path.

    Matching is by prefix: a key of "skills/python3-development" suppresses the
    code for any file whose path relative to the config root starts with that prefix.

    Args:
        ignore_config: Loaded ignore config mapping prefixes to suppressed codes.
        file_path: Absolute path to the file being validated.
        config_root: Directory containing the resolved config file (plugin root
            or .skilllint.json parent). Used to compute the relative path.
        code: Error code string (e.g. "SK006") to check.

    Returns:
        True if this code is suppressed for file_path, False otherwise.
    """
    if not ignore_config:
        return False
    try:
        rel = file_path.relative_to(config_root)
    except ValueError:
        return False
    rel_str = rel.as_posix()
    for prefix, codes in ignore_config.items():
        if not prefix:
            # Empty prefix means suppress globally for all files under this root.
            if code in codes:
                return True
        elif (rel_str == prefix or rel_str.startswith(prefix.rstrip("/") + "/")) and code in codes:
            return True
    return False


def _filter_result_by_ignore(
    result: ValidationResult, file_path: Path, config_root: Path, ignore_config: IgnoreConfig
) -> ValidationResult:
    """Return a new ValidationResult with suppressed issues removed.

    Suppressed issues are dropped entirely (not downgraded to info).
    The passed flag is recomputed from the remaining errors.

    Args:
        result: Original validation result.
        file_path: Path to the file that was validated.
        config_root: Directory containing the resolved config file (plugin root
            or .skilllint.json parent). Used for relative-path prefix matching.
        ignore_config: Loaded ignore config.

    Returns:
        Filtered ValidationResult (same object if nothing was suppressed).
    """
    if not ignore_config:
        return result

    def keep(issue: ValidationIssue) -> bool:
        return not _is_suppressed(ignore_config, file_path, config_root, str(issue.code))

    errors = [i for i in result.errors if keep(i)]
    warnings = [i for i in result.warnings if keep(i)]
    info = [i for i in result.info if keep(i)]

    if errors is result.errors and warnings is result.warnings and info is result.info:
        return result

    return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings, info=info)


# ============================================================================
# DATA MODELS
# ============================================================================


class FileType(StrEnum):
    """Type of capability file."""

    SKILL = "skill"
    AGENT = "agent"
    COMMAND = "command"
    PLUGIN = "plugin"
    HOOK_CONFIG = "hook_config"
    HOOK_SCRIPT = "hook_script"
    CLAUDE_MD = "claude_md"
    REFERENCE = "reference"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"

    @staticmethod
    def _is_plugin_scoped_unknown(path: Path, plugin_root: Path) -> bool:
        """Return True if path is skill-internal and must be classified as UNKNOWN.

        In PLUGIN context, only direct children of {plugin_root}/agents/ or
        {plugin_root}/commands/ qualify. Skill-internal paths are UNKNOWN.

        Args:
            path: The file path to classify.
            plugin_root: The plugin root directory.

        Returns:
            True if the path should be classified as UNKNOWN.
        """
        if "agents" in path.parts and path.parent != plugin_root / "agents":
            return True
        return bool("commands" in path.parts and path.parent != plugin_root / "commands")

    @staticmethod
    def detect_file_type(
        path: Path, scan_context: ScanContext | None = None, plugin_root: Path | None = None
    ) -> FileType:
        """Detect file type from path structure, optionally scoped by context.

        When scan_context is PLUGIN and plugin_root is provided:
        - Only classify as AGENT if path is directly under {plugin_root}/agents/
        - Only classify as COMMAND if path is directly under {plugin_root}/commands/
        - Files under skills/*/agents/ or skills/*/commands/ within the plugin
          are classified as UNKNOWN (skill-internal, not plugin-level components)

        When scan_context is None: current behavior (backward compatible).

        Args:
            path: The file path to classify.
            scan_context: Optional scan context for scoped classification.
            plugin_root: Optional plugin root for context-aware classification.

        Returns:
            FileType enum value.
        """
        if (
            scan_context == ScanContext.PLUGIN
            and plugin_root is not None
            and FileType._is_plugin_scoped_unknown(path, plugin_root)
        ):
            return FileType.UNKNOWN

        if path.name == "SKILL.md":
            result = FileType.SKILL
        elif path.name == "plugin.json" or (path / ".claude-plugin/plugin.json").exists():
            result = FileType.PLUGIN
        elif "agents" in path.parts:
            result = FileType.AGENT
        elif "commands" in path.parts:
            result = FileType.COMMAND
        elif path.name == "hooks.json":
            result = FileType.HOOK_CONFIG
        elif "hooks" in path.parts:
            result = FileType.HOOK_SCRIPT
        elif path.name == "CLAUDE.md":
            result = FileType.CLAUDE_MD
        elif "references" in path.parts and path.suffix == ".md":
            result = FileType.REFERENCE
        elif path.suffix == ".md":
            result = FileType.MARKDOWN
        else:
            result = FileType.UNKNOWN
        return result


class ValidationIssue(BaseModel):
    """A single validation issue."""

    model_config = ConfigDict(frozen=True)

    field: str
    severity: Literal["error", "warning", "info"]
    message: str
    code: Annotated[str, Field(pattern=r"^[A-Z]{2}\d{3}$")]
    line: int | None = None
    suggestion: str | None = None
    docs_url: str | None = None

    def format(self) -> str:
        """Format issue for display.

        Returns:
            Formatted string with severity icon, code, field, message, and optional docs URL
        """
        severity_icon = {"error": ":cross_mark:", "warning": ":warning:", "info": ":information:"}[self.severity]

        location = f":{self.line}" if self.line else ""
        suggestion_line = f"\n    → {self.suggestion}" if self.suggestion else ""
        docs = f"\n    → {self.docs_url}" if self.docs_url else ""
        return f"  {severity_icon} [{self.code}] {self.field}{location}: {self.message}{suggestion_line}{docs}"


class ValidationResult(BaseModel):
    """Result from a validation check."""

    model_config = ConfigDict(frozen=True)

    passed: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    info: list[ValidationIssue]


# Type alias: maps each unique file path to a list of (validator_name, result) pairs.
# This groups validator results by file so reports count unique files, not validator
# invocations.
FileResults = dict[Path, list[tuple[str, ValidationResult]]]


@dataclass(frozen=True)
class ComplexityMetrics:
    """Token-based complexity metrics."""

    total_tokens: int
    frontmatter_tokens: int
    body_tokens: int
    encoding: str = "cl100k_base"

    @property
    def status(self) -> Literal["ok", "warning", "error"]:
        """Determine status from thresholds.

        Returns:
            Status based on TOKEN_WARNING_THRESHOLD and TOKEN_ERROR_THRESHOLD
        """
        if self.body_tokens > TOKEN_ERROR_THRESHOLD:
            return "error"
        if self.body_tokens > TOKEN_WARNING_THRESHOLD:
            return "warning"
        return "ok"

    @property
    def message(self) -> str:
        """Human-readable status message.

        Returns:
            Status message with token count and threshold
        """
        if self.status == "error":
            return f"CRITICAL: {self.body_tokens} tokens (>{TOKEN_ERROR_THRESHOLD})"
        if self.status == "warning":
            return f"WARNING: {self.body_tokens} tokens (>{TOKEN_WARNING_THRESHOLD})"
        return f"OK: {self.body_tokens} tokens"


# ============================================================================
# VALIDATOR PROTOCOL
# ============================================================================


class Validator(Protocol):
    """Protocol for all validators.

    Defines the interface that all validator classes must implement to be
    compatible with the validation framework. Validators check specific aspects
    of plugin structure and can optionally provide auto-fixing capabilities.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Run validation check on path.

        Args:
            path: Path to file or directory to validate

        Returns:
            ValidationResult with passed status and any issues found
        """
        ...

    def can_fix(self) -> bool:
        """Whether this validator supports auto-fixing.

        Returns:
            True if validator can automatically fix issues, False otherwise
        """
        ...

    def fix(self, path: Path) -> list[str]:
        """Auto-fix issues in the file or directory.

        Args:
            path: Path to file or directory to fix

        Returns:
            List of human-readable descriptions of fixes applied
        """
        ...


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def generate_docs_url(error_code: ErrorCode | str) -> str:
    """Generate documentation URL for error code.

    Args:
        error_code: Error code (ErrorCode enum or string like "FM001", "SK006").

    Returns:
        The ``skilllint rule <CODE>`` invocation that renders the rule docs.
    """
    return rule_reference(str(error_code))


# extract_frontmatter imported from frontmatter_core


def _get_pydantic_ctx_val(error: ErrorDetails, key: str, default: str = "") -> str:
    """Extract a string value from Pydantic error ctx dict.

    Returns:
        The ctx value as string, or default if not found.
    """
    ctx = error.get("ctx")
    if isinstance(ctx, dict):
        val = ctx.get(key)
        return str(val) if val is not None else default
    return default


def _pydantic_error_to_validation_issue(error: ErrorDetails) -> ValidationIssue:
    """Convert a single Pydantic ValidationError item to a ValidationIssue.

    Args:
        error: Pydantic ErrorDetails from ValidationError.errors().

    Returns:
        ValidationIssue with appropriate code and suggestion.
    """
    loc = error.get("loc", ())
    field = ".".join(str(x) for x in (loc if isinstance(loc, (list, tuple)) else (loc,)))
    msg = str(error.get("msg", ""))
    code = FM005
    suggestion: str | None = None

    if "Field required" in msg:
        code = FM001
        msg = f"Missing required field: {field}"
    elif "String should match pattern" in msg:
        code = FM010
        msg = "Must use lowercase letters, numbers, and hyphens only"
        suggestion = "Use format: lowercase-with-hyphens"
    elif "String should have at most" in msg:
        max_len = _get_pydantic_ctx_val(error, "max_length", "unknown")
        msg = f"Exceeds maximum length of {max_len} characters"
        suggestion = f"Shorten to {max_len} characters or less"
        if field == "name":
            # FM010 owns name-length validation (see check_fm010 in fm_series.py).
            # Routing here avoids a duplicate FM005+FM010 finding for the same
            # over-length name (#139); _check_name_field_format's duplicate
            # guard then suppresses the second FM010 source.
            code = FM010
    elif "Input should be" in msg and "literal" in msg.lower():
        code = FM006
        valid_values = _get_pydantic_ctx_val(error, "expected")
        msg = f"Invalid value. Must be one of: {valid_values}"
    elif isinstance(error.get("input"), list):
        if "tools" in field.lower():
            code = FM007
            msg = "Tools field is YAML array — runtime accepts this, but CSV string is preferred style"
        suggestion = "Use format: 'tool1, tool2, tool3'"
    elif "colon" in msg.lower():
        code = FM009
        suggestion = "Quote the description or remove colons"

    # FM007 (YAML array for tools) is a runtime-accepted pattern -> warning
    severity: Literal["error", "warning", "info"] = "warning" if code == FM007 else "error"

    return ValidationIssue(
        field=field, severity=severity, message=msg, code=code, docs_url=generate_docs_url(code), suggestion=suggestion
    )


def _check_list_valued_tool_fields(
    data: dict[str, YamlValue], errors: list[ValidationIssue], warnings: list[ValidationIssue]
) -> None:
    """Append warnings for list-valued tools fields that Pydantic may not catch.

    Delegates to check_fm007 from fm_series for issue construction.

    Args:
        data: Parsed frontmatter dict.
        errors: Mutable list to append error issues to (unused, kept for API compat).
        warnings: Mutable list to append warning issues to.
    """
    from pathlib import Path as _Path  # ruff: ignore[import-outside-top-level]

    sentinel_path = _Path()
    warnings.extend(check_fm007(data, sentinel_path, "skill"))


def _check_agent_tools_and_skills_fields(
    data: dict[str, YamlValue], path: Path, errors: list[ValidationIssue], warnings: list[ValidationIssue]
) -> None:
    """Append AG001-AG003 issues for agent frontmatter (tools/disallowedTools/skills).

    Only called for ``FileType.AGENT``. Reads the raw parsed dict so a
    YAML-list ``tools``/``skills`` value is inspected before
    ``AgentFrontmatter``'s own field-level CSV coercion of ``tools``/
    ``disallowedTools``.

    Args:
        data: Parsed frontmatter dict.
        path: Path to the agent file (AG002 uses it to discover MCP server config).
        errors: Mutable list to append error issues to.
        warnings: Mutable list to append warning issues to.
    """
    for issue in (*check_ag001(data), *check_ag002(data, path), *check_ag003(data)):
        (errors if issue.severity == "error" else warnings).append(issue)


def _check_name_field_format(
    data: dict[str, YamlValue],
    path: Path,
    file_type: FileType,
    errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
) -> None:
    """Emit FM010 for the ``name`` field on any frontmatter-bearing file type.

    Runs for skills, agents and commands alike. ``SkillFrontmatter`` and
    ``AgentFrontmatter`` declare ``name`` with the same pattern constraint, so
    for those types the Pydantic path usually reports FM010 first and the
    duplicate guard below suppresses a second copy. ``CommandFrontmatter``
    declares no ``name`` field (it is accepted as an extra), so this call is the
    only FM010 source for ``commands/*.md``.

    Args:
        data: Parsed frontmatter dict.
        path: Path to the file being validated.
        file_type: Detected file type.
        errors: Mutable list to append errors to.
        warnings: Mutable list to append warnings to.
    """
    if data.get("name") is None or any(issue.code == FM010 for issue in (*errors, *warnings)):
        return

    for issue in check_fm010(data, path, file_type.value):
        (errors if issue.severity == "error" else warnings).append(issue)


def _check_skill_directory_name(path: Path, file_type: FileType, errors: list[ValidationIssue]) -> None:
    """Validate the directory name that contains a SKILL.md file (SK008).

    SK008 constrains the directory layout, not the frontmatter, so it stays
    skill-only while FM010 name-format checking applies to every file type.

    Args:
        path: Path to SKILL.md file.
        file_type: Detected file type.
        errors: Mutable list to append errors to.
    """
    if file_type != FileType.SKILL or path.name != "SKILL.md":
        return

    skill_dir_name = path.parent.name

    if path.parent.parent.name == "skills":
        dir_name_issues = _validate_skill_directory_name(skill_dir_name)
        for issue_msg, issue_suggestion in dir_name_issues:
            errors.append(
                ValidationIssue(
                    field="directory",
                    severity="error",
                    message=issue_msg,
                    code=SK008,
                    docs_url=generate_docs_url(SK008),
                    suggestion=issue_suggestion,
                )
            )


# ============================================================================
# PROGRESSIVE DISCLOSURE VALIDATOR
# ============================================================================


class ProgressiveDisclosureValidator:
    """Validates presence of progressive disclosure directories.

    Checks for references/, assets/, and scripts/ directories that help
    organize additional content for on-demand exploration. Missing directories
    are reported as INFO (not errors) since they're optional organizational aids.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate progressive disclosure structure in skill directory.

        Args:
            path: Path to skill directory (should contain SKILL.md)

        Returns:
            ValidationResult with info messages for missing directories
        """
        info = check_pd001(path) + check_pd002(path) + check_pd003(path)

        # Always pass - info messages don't fail validation
        return ValidationResult(passed=True, errors=[], warnings=[], info=info)

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (creating directories requires content creation decisions)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix progressive disclosure issues (not supported).

        Args:
            path: Path to directory to fix

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Progressive disclosure validation cannot be auto-fixed
        """
        raise NotImplementedError(
            "Progressive disclosure validation cannot be auto-fixed. "
            "Creating directories requires human decisions about content organization."
        )


# ============================================================================
# INTERNAL LINK VALIDATOR
# ============================================================================


class InternalLinkValidator:
    """Validates internal markdown links in SKILL.md files.

    Checks that relative links point to existing files (LK001).

    Detection lives in ``skilllint.rules.lk_series``; this class reads the file
    and packages the rule results into a ``ValidationResult``.

    Architecture lines 1188-1256, Task T8 lines 897-982
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate internal markdown links in SKILL.md.

        Args:
            path: Path to SKILL.md file

        Returns:
            ValidationResult with errors for broken links.
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        # Only validate SKILL.md files
        if path.name != "SKILL.md":
            # Not a skill file - skip validation
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        # Read file
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                )
            )
            return ValidationResult(passed=False, errors=errors, warnings=warnings, info=info)

        errors.extend(check_lk001(content, path))

        # Pass if no errors (warnings don't fail validation)
        passed = len(errors) == 0
        return ValidationResult(passed=passed, errors=errors, warnings=warnings, info=info)

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (broken links require file creation or manual correction)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix internal link issues (not supported).

        Args:
            path: Path to file to fix

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Internal link validation cannot be auto-fixed
        """
        raise NotImplementedError(
            "Internal link validation cannot be auto-fixed. "
            "Broken links require creating missing files or correcting link paths manually."
        )


# ============================================================================
# NAMESPACE REFERENCE VALIDATOR
# ============================================================================


class NamespaceReferenceValidator:
    """Validates namespace-qualified references in plugin files.

    Checks that ``Skill()``, ``Task()``, ``@agent``, and ``/command`` references
    with namespace prefixes (``plugin:name``) resolve to actual files in the
    referenced plugin directory.

    Detects patterns such as:
    - ``Skill(command: "plugin:skill-name")``
    - ``Skill(skill="plugin:skill-name")``
    - ``Task(agent="plugin:agent-name")``
    - ``@plugin:agent-name`` (prose agent references)
    - ``/plugin:skill-name`` (slash command references)

    Detection lives in ``skilllint.rules.nr_series``; this class reads the file
    and packages the rule results into a ``ValidationResult``.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate namespace-qualified references in a plugin file.

        Extracts references from the file body (after frontmatter) and verifies
        each namespace-qualified reference resolves to an existing file in the
        referenced plugin directory.

        Args:
            path: Path to a SKILL.md, agent .md, or command .md file

        Returns:
            ValidationResult with errors for broken references
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors = [
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=NR001,
                    docs_url=generate_docs_url(NR001),
                )
            ]
            return ValidationResult(passed=False, errors=errors, warnings=[], info=[])

        errors = check_nr001(content, path) + check_nr002(content, path)
        return ValidationResult(passed=not errors, errors=errors, warnings=[], info=[])

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (namespace references require manual correction)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix namespace reference issues (not supported).

        Args:
            path: Path to file to fix

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Namespace reference validation cannot be auto-fixed
        """
        raise NotImplementedError(
            "Namespace reference validation cannot be auto-fixed. "
            "Broken references require creating missing files or correcting "
            "the namespace prefix manually."
        )


# ============================================================================
# SYMLINK TARGET VALIDATOR
# ============================================================================


class SymlinkTargetValidator:
    r"""Validates that symlinks within the validated path have clean target paths.

    Detects symlinks whose targets contain trailing whitespace or newlines
    (e.g. ``os.readlink()`` returns ``'../../python3-development/skills/uv\\n'``).
    Such symlinks cause ``Path.resolve()`` and ``is_file()``/``is_dir()`` to
    fail silently, producing false-positive errors in other validators.

    When ``path`` is a file: checks whether the file itself is a symlink with
    a dirty target.  When ``path`` is a directory: scans all symlinks found
    recursively within the directory.

    Auto-fix (SL001): strips trailing whitespace from the target, removes the
    old symlink, and recreates it pointing to the clean target.  The fix is
    only applied when the cleaned target resolves to an existing path.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Detect symlinks with trailing whitespace in their target paths.

        Args:
            path: Path to a file or directory to inspect for dirty symlinks.

        Returns:
            ValidationResult with errors for each dirty symlink found.
        """
        errors = check_sl001(path)
        return ValidationResult(passed=not errors, errors=errors, warnings=[], info=[])

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            True (trailing whitespace in symlink targets can be stripped automatically)
        """
        return True

    def fix(self, path: Path) -> list[str]:
        """Strip trailing whitespace from symlink targets and recreate affected symlinks.

        Only recreates symlinks whose cleaned target resolves to an existing path.
        Symlinks whose cleaned target does not exist are left untouched and reported
        as unfixable.

        Args:
            path: Path to a file or directory to scan for dirty symlinks.

        Returns:
            List of human-readable descriptions of fixes applied.
        """
        fixes: list[str] = []

        for symlink_path in iter_symlinks(path):
            try:
                raw_target = str(Path(symlink_path).readlink())
            except OSError:
                continue

            if raw_target == raw_target.rstrip():
                continue  # Target is already clean

            clean_target = raw_target.rstrip()

            # Resolve the cleaned target to verify it exists before recreating
            resolved = (symlink_path.parent / clean_target).resolve()
            if not resolved.exists():
                continue  # Cannot verify cleaned target — leave untouched

            try:
                Path(symlink_path).unlink()
                Path(symlink_path).symlink_to(clean_target)
                fixes.append(
                    f"Fixed symlink {symlink_path}: stripped trailing whitespace from target "
                    f"({raw_target!r} -> {clean_target!r})"
                )
            except OSError:
                # Best-effort: if remove/symlink fails, leave the original in place
                with contextlib.suppress(OSError):
                    Path(symlink_path).symlink_to(raw_target)

        return fixes


class AsSeriesValidator:
    """Runs AS001 and AS006-AS009 rules on SKILL.md files.

    AS-series rules enforce the AgentSkills specification, which is a
    cross-harness baseline for skills. It defines ``SKILL.md`` and does not
    describe agent files at all, so this validator is wired only to
    ``FileType.SKILL``. A check on agent frontmatter belongs to a series that
    governs agent files, cited to the harness documentation defining them.

    These are platform-independent, so this validator integrates into the
    default ``validate_single_path`` code path and fires without ``--platform``.
    """

    def validate(self, path: Path, policy: ValidationPolicy | None = None) -> ValidationResult:
        """Run AS-series checks on a skill file.

        Args:
            path: Path to a SKILL.md file. Default dispatch wires only
                ``FileType.SKILL`` to this validator (see the class
                docstring for why); this method itself does not check the
                file type, so tests may call it directly with other paths.
            policy: Optional resolved per-plugin policy.

        Returns:
            ValidationResult grouping AS-series issues by severity.
        """
        from skilllint.rules.as_series import run_as_series  # ruff: ignore[import-outside-top-level]

        frontmatter_data, body_lines, _yaml_err, _colon_fields = parse_skill_md(path)
        thresholds = policy.thresholds if policy is not None else DEFAULT_THRESHOLDS
        violations = run_as_series(
            path,
            frontmatter_data,
            body_lines,
            warning_threshold=thresholds.get("SK006", TOKEN_WARNING_THRESHOLD),
            error_threshold=thresholds.get("SK007", TOKEN_ERROR_THRESHOLD),
        )

        issues = [
            ValidationIssue(
                field=v.get("code", "unknown"),
                severity=(
                    v.get("severity", "error")
                    if v.get("severity", "error") in {"error", "warning", "info"}
                    else "error"
                ),
                message=v.get("message", ""),
                code=v["code"],
            )
            for v in violations
        ]
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        info = [i for i in issues if i.severity == "info"]
        return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings, info=info)

    def can_fix(self) -> bool:
        """AS-series rules do not support auto-fixing.

        Returns:
            Always False.
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """No-op — AS-series rules do not support auto-fixing.

        Args:
            path: Unused.

        Returns:
            Empty list.
        """
        return []


# SkillFrontmatter, CommandFrontmatter, AgentFrontmatter imported from frontmatter_core


_SKILL_DIR_CONVENTION_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _validate_skill_directory_name(skill_dir_name: str) -> list[tuple[str, str]]:
    """Validate skill directory name against naming conventions.

    Checks: non-empty, max ``MAX_NAME_LENGTH`` (64) chars per the
    agentskills.io specification, lowercase+digits+hyphens only, no
    leading/trailing/consecutive hyphens, no underscores.

    Source: https://agentskills.io/specification.md — the spec applies the
    same 64-character limit to both the frontmatter ``name`` field and the
    skill directory name (``_spec_constants.MAX_NAME_LENGTH``).

    Args:
        skill_dir_name: Directory name to validate.

    Returns:
        List of (message, suggestion) tuples for each violation found.
        Empty list if the name is valid.
    """
    from skilllint._spec_constants import MAX_NAME_LENGTH  # ruff: ignore[import-outside-top-level]

    if not skill_dir_name:
        return [("Skill directory name cannot be empty", "Provide a non-empty directory name")]

    results: list[tuple[str, str]] = []

    if len(skill_dir_name) > MAX_NAME_LENGTH:
        results.append((
            f"Directory name exceeds maximum length of {MAX_NAME_LENGTH} characters (got {len(skill_dir_name)})",
            f"Shorten directory name to {MAX_NAME_LENGTH} characters or less",
        ))

    if not _SKILL_DIR_CONVENTION_PATTERN.match(skill_dir_name):
        violations: list[str] = []
        if re.search(r"[A-Z]", skill_dir_name):
            violations.append("contains uppercase letters")
        if re.search(r"[^a-z0-9-]", skill_dir_name):
            violations.append("contains invalid characters (only lowercase, digits, hyphens allowed)")
        if skill_dir_name.startswith("-"):
            violations.append("starts with hyphen")
        if skill_dir_name.endswith("-"):
            violations.append("ends with hyphen")
        if "--" in skill_dir_name:
            violations.append("contains consecutive hyphens")
        if "_" in skill_dir_name:
            violations.append("contains underscores (use hyphens instead)")
        violation_msg = "; ".join(violations) if violations else "invalid format"
        results.append((f"Directory name {violation_msg}", "Use lowercase-hyphen-case (e.g., 'my-skill-name')"))

    return results


def _coerce_validation_issues(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    """Rebuild issues as this module's ``ValidationIssue`` instances.

    Deferred imports (e.g. rules calling ``ValidationIssue`` from inside helpers) can
    produce a different class object than the one bound on ``ValidationResult`` in
    edge loads (notably ``python -m skilllint.plugin_validator``). Pydantic then
    rejects nested instances with ``model_type``. Round-tripping through
    ``model_dump`` / ``model_validate`` normalizes to a single class identity.

    Args:
        issues: Issues collected during validation.

    Returns:
        Equivalent issues re-instantiated on the canonical ``ValidationIssue`` model.
    """
    return [ValidationIssue.model_validate(i.model_dump()) for i in issues]


def _build_validation_result(
    *, errors: list[ValidationIssue], warnings: list[ValidationIssue], info: list[ValidationIssue]
) -> ValidationResult:
    """Build a validation result from accumulated issue lists.

    Args:
        errors: Collected error issues.
        warnings: Collected warning issues.
        info: Collected informational issues.

    Returns:
        ValidationResult with pass/fail derived from whether errors exist.
    """
    return ValidationResult(
        passed=len(errors) == 0,
        errors=_coerce_validation_issues(errors),
        warnings=_coerce_validation_issues(warnings),
        info=_coerce_validation_issues(info),
    )


def _validation_result_with_error(
    *,
    errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
    info: list[ValidationIssue],
    issue: ValidationIssue,
) -> ValidationResult:
    """Append one error issue and return a validation result.

    Args:
        errors: Collected error issues.
        warnings: Collected warning issues.
        info: Collected informational issues.
        issue: Error issue to append before returning.

    Returns:
        ValidationResult containing the appended error.
    """
    errors.append(issue)
    return _build_validation_result(errors=errors, warnings=warnings, info=info)


def _fm009_recovery_warnings(colon_fields: list[str]) -> list[ValidationIssue]:
    """Return one FM009 warning per field that only parsed after colon recovery.

    ``safe_load_yaml_with_colon_fix`` quotes unquoted colon values in memory so
    validation can continue, and returns ``yaml_err=None``. The source file is
    unchanged and still breaks a plain YAML parse, so the recovery has to be
    reported rather than swallowed.

    Args:
        colon_fields: Field names whose values required quoting to parse.

    Returns:
        One FM009 warning per field; empty when no recovery was needed.
    """
    return [
        ValidationIssue(
            field=field_name,
            severity="warning",
            message=(
                f"Unquoted value containing a colon in field '{field_name}' breaks YAML parsing "
                "(parsed here only after quoting it)"
            ),
            code=FM009,
            docs_url=generate_docs_url(FM009),
            suggestion=f"Quote the value of '{field_name}', or run with --fix",
        )
        for field_name in colon_fields
    ]


def _validate_frontmatter_yaml(
    frontmatter_text: str,
    *,
    errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
    info: list[ValidationIssue],
) -> tuple[dict[str, YamlValue] | None, ValidationResult | None]:
    """Validate raw frontmatter YAML and return parsed mapping or failure result.

    Args:
        frontmatter_text: Extracted frontmatter text without outer delimiters.
        errors: Collected error issues.
        warnings: Collected warning issues.
        info: Collected informational issues.

    Returns:
        Tuple of parsed mapping or None, and a terminal ValidationResult when
        validation must stop.
    """
    data, yaml_err, colon_fields, _used_text = safe_load_yaml_with_colon_fix(frontmatter_text)
    # Recovery keeps validation going, but the file on disk is still invalid
    # YAML. Report it, or a check-only run reports nothing at all for a source
    # that only parsed because the colon was quoted for us.
    warnings.extend(_fm009_recovery_warnings(colon_fields))

    if yaml_err is not None:
        result = _validation_result_with_error(
            errors=errors,
            warnings=warnings,
            info=info,
            issue=ValidationIssue(
                field="(yaml)",
                severity="error",
                message=f"Invalid YAML syntax: {yaml_err}",
                code=FM002,
                docs_url=generate_docs_url(FM002),
            ),
        )
        return None, result

    if not isinstance(data, dict):
        result = _validation_result_with_error(
            errors=errors,
            warnings=warnings,
            info=info,
            issue=ValidationIssue(
                field="(yaml)",
                severity="error",
                message="Frontmatter must be a YAML mapping",
                code=FM002,
                docs_url=generate_docs_url(FM002),
            ),
        )
        return None, result

    return data, None


# ============================================================================
# FRONTMATTER VALIDATOR
# ============================================================================


class FrontmatterValidator:
    """Validates and auto-fixes YAML frontmatter in capability files.

    Implements Validator protocol for frontmatter validation of skills, agents,
    and commands. Uses shared Pydantic models from frontmatter_core.
    """

    def __init__(self) -> None:
        """Initialize frontmatter validator.

        ``_pending_fm009_info`` accumulates FM009 info issues produced by
        :meth:`fix` (via :meth:`_apply_fixes`) so that the next
        :meth:`validate` call can surface them as ``info`` entries.  This lets
        ``--verbose`` output show exactly which fields were silently repaired by
        the unquoted-colon auto-fix.
        """
        self._pending_fm009_info: list[ValidationIssue] = []

    def validate(self, path: Path) -> ValidationResult:
        """Validate frontmatter in file.

        Args:
            path: Path to file with YAML frontmatter

        Returns:
            ValidationResult with errors, warnings, and info issues

        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        # Drain any FM009 info issues queued by a preceding fix() call so that
        # --verbose output shows what was silently repaired.
        info: list[ValidationIssue] = self._pending_fm009_info
        self._pending_fm009_info = []

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            return _validation_result_with_error(
                errors=errors,
                warnings=warnings,
                info=info,
                issue=ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                ),
            )

        frontmatter_text, _start_line, _end_line = self._extract_frontmatter(content)
        if frontmatter_text is None:
            return _validation_result_with_error(
                errors=errors,
                warnings=warnings,
                info=info,
                issue=ValidationIssue(
                    field="(file)",
                    severity="error",
                    message="No YAML frontmatter found",
                    code=FM003,
                    docs_url=generate_docs_url(FM003),
                    suggestion="File must start with '---' delimiter",
                ),
            )

        file_type = FileType.detect_file_type(path)
        if file_type == FileType.UNKNOWN:
            file_type = FileType.SKILL

        data, yaml_result = _validate_frontmatter_yaml(frontmatter_text, errors=errors, warnings=warnings, info=info)
        if yaml_result is not None:
            return yaml_result

        model_class = self._get_model_class(file_type)
        if model_class is None:
            return _build_validation_result(errors=errors, warnings=warnings, info=info)

        validated_data = cast("dict[str, YamlValue]", data)
        self._validate_pydantic_model(
            model_class, validated_data, file_type, path, frontmatter_text, errors=errors, warnings=warnings
        )

        return _build_validation_result(errors=errors, warnings=warnings, info=info)

    def _validate_pydantic_model(
        self,
        model_class: type[SkillFrontmatter | CommandFrontmatter | AgentFrontmatter],
        data: dict[str, YamlValue],
        file_type: FileType,
        path: Path,
        frontmatter_text: str,
        *,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ) -> None:
        """Run Pydantic validation and post-validation checks.

        Args:
            model_class: Pydantic model class to validate against
            data: Parsed frontmatter data
            file_type: Detected file type
            path: Path to the file being validated
            frontmatter_text: Raw YAML frontmatter (between ``---`` delimiters) for FM004 source checks
            errors: Mutable list to append errors to
            warnings: Mutable list to append warnings to

        """
        try:
            model_class.model_validate(data)
            # SK004 (description length) is emitted exclusively by DescriptionValidator,
            # which calls check_sk004 directly. Emitting it here as well produced
            # duplicate warnings for over-length descriptions.
            # AS-series rules do not duplicate parser-owned findings.
        except ValidationError as e:
            for err in e.errors():
                issue = _pydantic_error_to_validation_issue(err)
                if issue.severity == "warning":
                    warnings.append(issue)
                else:
                    errors.append(issue)

        warnings.extend(check_fm004(data, path, file_type.value, frontmatter_yaml=frontmatter_text))
        _check_list_valued_tool_fields(data, errors, warnings)
        _check_name_field_format(data, path, file_type, errors, warnings)
        _check_skill_directory_name(path, file_type, errors)
        if file_type == FileType.AGENT:
            _check_agent_tools_and_skills_fields(data, path, errors, warnings)

        hooks_value = data.get("hooks")
        if isinstance(hooks_value, dict):
            HookValidator().validate_hook_script_references_in_hooks_dict(hooks_value, path.parent, errors, warnings)

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            True (frontmatter validator supports auto-fixing)
        """
        return True

    def fix(self, path: Path) -> list[str]:
        """Auto-fix frontmatter issues in file.

        Fixes FM004, FM007, FM009 only. Does not fix schema violations.

        Args:
            path: Path to file to fix

        Returns:
            List of human-readable descriptions of fixes applied
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return []

        # Detect file type
        file_type = FileType.detect_file_type(path)
        if file_type == FileType.UNKNOWN:
            file_type = FileType.SKILL

        # Apply fixes
        fixed_content, fixes = self._apply_fixes(content, file_type, path)

        if not fixes:
            return []

        # Write fixed content
        try:
            path.write_text(fixed_content, encoding="utf-8")
        except OSError:
            return []

        return fixes

    def _extract_frontmatter(self, content: str) -> tuple[str | None, int, int]:
        """Extract YAML frontmatter from content.

        Returns:
            Tuple of (frontmatter_text, start_line, end_line) or (None, 0, 0)

        Deprecated:
            Use module-level extract_frontmatter() function instead.
        """
        return extract_frontmatter(content)

    def _get_model_class(
        self, file_type: FileType
    ) -> type[SkillFrontmatter | CommandFrontmatter | AgentFrontmatter] | None:
        """Get Pydantic model class for file type.

        Delegates to frontmatter_core.get_frontmatter_model().

        Returns:
            Pydantic model class or None if unknown type.
        """
        return get_frontmatter_model(file_type.value)

    def _queue_fm009_info(self, fixed_fields: list[str]) -> None:
        """Append FM009 info issues for fields that were auto-fixed by colon quoting.

        Args:
            fixed_fields: Field names whose values were quoted.
        """
        for field_name in fixed_fields:
            self._pending_fm009_info.append(
                ValidationIssue(
                    field=field_name,
                    severity="info",
                    message=(f"Auto-fixed: unquoted value containing colon was quoted in field '{field_name}'"),
                    code=FM009,
                    docs_url=generate_docs_url(FM009),
                )
            )

    def _parse_frontmatter_with_colon_fix(
        self, frontmatter_text: str
    ) -> tuple[str, dict[str, YamlValue] | None, list[str]]:
        """Parse frontmatter, applying unquoted-colon fix if YAML parse fails.

        Returns:
            Tuple of (frontmatter_text, parsed_data, colon_fix_descriptions).
            parsed_data is None if parse failed even after colon fix.
        """
        parsed, _yaml_err, colon_fields, used_text = safe_load_yaml_with_colon_fix(frontmatter_text)
        if colon_fields:
            self._queue_fm009_info(colon_fields)
        # Build colon_fixes list (one description per fixed field) to match caller expectations
        colon_fixes = ["Quoted description value containing unquoted colon"] * len(colon_fields)
        return (used_text, cast("dict[str, YamlValue]", parsed), colon_fixes)

    def _normalize_tool_fields_and_detect_changes(
        self,
        normalized_dict: dict[str, YamlValue],
        original_data: dict[str, YamlValue],
        frontmatter_text: str,
        *,
        colon_fixes: list[str],
        file_type: FileType,
        file_path: Path | None,
    ) -> tuple[dict[str, YamlValue], list[str]]:
        """Normalize tool/skills fields and detect other changes.

        Returns:
            Tuple of (dict to dump, combined list of fix descriptions).
            The dict may be a new instance when fix_skill_name_field adds a name.
        """
        fixes = list(colon_fixes)
        if file_type == FileType.SKILL and file_path is not None:
            normalized_dict = fix_skill_name_field(normalized_dict, file_path, fixes)
        # SkillFrontmatter has no declared `skills` field (passthrough only via
        # extra="allow"); AgentFrontmatter exposes a runtime-friendly view via
        # `normalized_skills`. Either way, --fix must preserve the originally
        # authored value's parsed shape (scalar/sequence/null) untouched.
        if "skills" in original_data:
            normalized_dict["skills"] = original_data["skills"]
        tool_fields = {"tools", "disallowedTools", "allowed-tools"}
        for field_name in tool_fields:
            val = normalized_dict.get(field_name)
            if isinstance(val, list):
                normalized_dict[field_name] = ", ".join(str(x) for x in val)
                fixes.append(f"Converted {field_name} from YAML array to comma-separated string")
        for key, value in normalized_dict.items():
            if key in tool_fields:
                continue
            orig_val = original_data.get(key)
            if orig_val is not None and orig_val != value:
                if isinstance(orig_val, list) and isinstance(value, str):
                    fixes.append(f"Converted {key} from YAML array to comma-separated string")
                elif isinstance(orig_val, str) and "\n" in orig_val and "\n" not in str(value):
                    fixes.append(f"Normalized {key} to single line")
        if re.search(r":\s*[|>][-+]?", frontmatter_text):
            fixes.append("Removed YAML multiline indicators")
        return normalized_dict, fixes

    def _compute_normalized_fixes(
        self,
        original_data: dict[str, YamlValue],
        frontmatter_text: str,
        body: str,
        *,
        file_type: FileType,
        file_path: Path | None,
        colon_fixes: list[str],
    ) -> tuple[str, list[str]] | None:
        """Compute normalized frontmatter and list of fixes.

        Returns:
            Tuple of (fixed_content, fixes_list) or None if validation fails.
        """
        model_class = self._get_model_class(file_type)
        if model_class is None:
            return None
        try:
            validated = model_class.model_validate(original_data)
            normalized_dict = validated.model_dump(by_alias=True, exclude_none=True, mode="python")
        except ValidationError:
            return (f"---\n{frontmatter_text}\n---\n{body}", colon_fixes) if colon_fixes else None

        normalized_dict, fixes = self._normalize_tool_fields_and_detect_changes(
            normalized_dict,
            original_data,
            frontmatter_text,
            colon_fixes=colon_fixes,
            file_type=file_type,
            file_path=file_path,
        )
        if not fixes:
            return None
        return f"---\n{_dump_yaml(normalized_dict)}---\n{body}", fixes

    def _apply_fixes(self, content: str, file_type: FileType, file_path: Path | None = None) -> tuple[str, list[str]]:
        """Apply auto-fixes to content.

        Args:
            content: File content with frontmatter
            file_type: Type of capability file
            file_path: Optional path to file, used to derive skill name from directory

        Returns:
            Tuple of (fixed_content, list_of_fixes_applied)

        """
        result_content = content
        result_fixes: list[str] = []

        frontmatter_text, _, _ = self._extract_frontmatter(content)
        end_match = re.search(r"\n---\s*\n", content[3:]) if frontmatter_text is not None else None
        if frontmatter_text is None or end_match is None:
            return result_content, result_fixes

        body = content[end_match.end() + 3 :]
        frontmatter_text, original_data, colon_fixes = self._parse_frontmatter_with_colon_fix(frontmatter_text)

        if isinstance(original_data, dict):
            computed = self._compute_normalized_fixes(
                original_data, frontmatter_text, body, file_type=file_type, file_path=file_path, colon_fixes=colon_fixes
            )
            if computed is not None:
                result_content, result_fixes = computed

        return result_content, result_fixes


# ============================================================================
# NAME FORMAT VALIDATOR
# ============================================================================


class NameFormatValidator:
    """Repairs skill/agent/command name format (FM010).

    Delegates every check to :func:`check_fm010`, the single owner of the
    name-format rule:

    - Lowercase letters, digits and hyphens only
    - No leading/trailing hyphens and no consecutive hyphens
    - 1-64 characters
    - For SKILL.md, ``name`` matching the parent directory name

    In the CLI this validator runs from ``_get_fixers_for_path`` only, so that
    FM010 has exactly one reporter (``FrontmatterValidator``) and exactly one
    fixer (this class). ``validate()`` remains available to callers that want
    the rule in isolation.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate name format in frontmatter.

        Args:
            path: Path to file with YAML frontmatter

        Returns:
            ValidationResult with errors for invalid name format
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []
        result: ValidationResult | None = None
        frontmatter_text: str | None = None

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                )
            )
            result = ValidationResult(passed=False, errors=errors, warnings=warnings, info=info)

        if result is None:
            frontmatter_text, _start_line, _end_line = extract_frontmatter(content)
            if frontmatter_text is None:
                result = ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        if result is None and frontmatter_text is not None:
            try:
                data = _safe_load_yaml(frontmatter_text)
            except YAMLError:
                result = ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)
            else:
                if not isinstance(data, dict):
                    result = ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)
                else:
                    name = data.get("name")
                    if name is None or not isinstance(name, str):
                        result = ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)
                    else:
                        file_type = FileType.detect_file_type(path)
                        for issue in check_fm010(data, path, file_type.value):
                            (errors if issue.severity == "error" else warnings).append(issue)
                        result = ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings, info=info)

        return (
            result if result is not None else ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)
        )

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            True (name format is auto-fixable on case-sensitive filesystems)
        """
        return True

    def fix(self, path: Path) -> list[str]:
        """Auto-fix name format issues (uppercase, underscores, hyphens).

        Normalizes the frontmatter name field and, for SKILL.md in a skill
        directory, renames the directory to match. Uses a two-step rename on
        case-insensitive filesystems so Test-Skill -> test-skill works.

        Args:
            path: Path to file to fix

        Returns:
            List of fix descriptions, or empty if nothing was fixed
        """
        fixes = self._try_fix_name_format(path)
        return fixes if fixes is not None else []

    def _read_name_and_frontmatter(self, path: Path) -> tuple[str, dict[str, YamlValue], str] | None:
        """Read file, parse frontmatter, extract name.

        Returns:
            Tuple of (content, data, name) or None if any step fails.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return None
        fm_text, _start, _end = extract_frontmatter(content)
        if fm_text is None:
            return None
        try:
            data = _safe_load_yaml(fm_text)
        except YAMLError:
            return None
        if not isinstance(data, dict):
            return None
        name = data.get("name")
        if not isinstance(name, str) or not name:
            return None
        return content, data, name

    def _try_fix_name_format(self, path: Path) -> list[str] | None:
        """Attempt to fix name format.

        Returns:
            List of fix descriptions if fixes were applied, None otherwise.
        """
        parsed = self._read_name_and_frontmatter(path)
        if parsed is None:
            return None
        content, data, name = parsed

        fixed_name = _normalize_skill_name(name)
        if not fixed_name or fixed_name == name or not re.match(NAME_PATTERN, fixed_name):
            return None

        data["name"] = fixed_name
        end_match = re.search(r"\n---\s*\n", content[3:])
        body = content[end_match.end() + 3 :] if end_match else ""
        # `body` starts after the closing delimiter, so the delimiter has to be
        # written back explicitly — omitting it left the file with no closing
        # `---`, which FM003 then reported as missing frontmatter.
        new_content = f"---\n{_dump_yaml(data)}---\n{body}"
        try:
            path.write_text(new_content, encoding="utf-8")
        except OSError:
            return None

        fixes = [f"Normalized name from '{name}' to '{fixed_name}'"]
        # Rename skill directory to match (two-step on case-insensitive filesystems)
        if path.name == "SKILL.md" and path.parent.name != fixed_name:
            skill_dir = path.parent
            parent_dir = skill_dir.parent
            try:
                temp_name = f"{skill_dir.name}.fmtemp"
                skill_dir.rename(parent_dir / temp_name)
                (parent_dir / temp_name).rename(parent_dir / fixed_name)
                fixes.append(f"Renamed directory to '{fixed_name}'")
            except OSError:
                pass  # Directory rename best-effort; frontmatter fix already applied

        return fixes


# ============================================================================
# DESCRIPTION VALIDATOR
# ============================================================================


class DescriptionValidator:
    """Validates description field quality.

    Checks:
    - Minimum length (20 characters) — SKILL and AGENT files only
    - Presence of trigger phrases — SKILL files only

    Both checks produce warnings, not errors, since description quality is subjective.
    Commands have different frontmatter schemas and do not require trigger phrases.
    """

    def __init__(self, file_type: FileType = FileType.SKILL) -> None:
        """Initialize with file type to scope validation checks.

        Args:
            file_type: The type of file being validated. SK004 (too short) applies
                to SKILL and AGENT files. SK005 (missing triggers) applies to SKILL only.
        """
        self.file_type = file_type

    def validate(self, path: Path) -> ValidationResult:
        """Validate description field in frontmatter.

        Args:
            path: Path to file with YAML frontmatter

        Returns:
            ValidationResult with warnings for description quality issues

        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                )
            )
            return ValidationResult(passed=False, errors=errors, warnings=warnings, info=info)

        frontmatter_text, _start_line, _end_line = extract_frontmatter(content)
        if frontmatter_text is None:
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        try:
            data = _safe_load_yaml(frontmatter_text)
        except YAMLError:
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        if not isinstance(data, dict):
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        description = data.get("description")
        if description is None or not isinstance(description, str):
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        self._check_description_quality(data, description, warnings)
        return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings, info=info)

    def _check_description_quality(
        self, data: dict[str, YamlValue], description: str, warnings: list[ValidationIssue]
    ) -> None:
        """Append warnings for description length and trigger phrases.

        Delegates to sk_series check_sk004/check_sk005 — the series module is
        the single source of truth for SK-series rule logic.

        Args:
            data: Full parsed frontmatter dict, needed so sk_series can read
                `disable-model-invocation` and suppress both checks when a
                skill has opted out of model-driven activation.
            description: The frontmatter `description` value.
            warnings: Mutable list to append warnings to.
        """
        from pathlib import Path as _Path  # ruff: ignore[import-outside-top-level]

        frontmatter: dict[str, object] = {
            "description": description,
            "disable-model-invocation": data.get("disable-model-invocation"),
        }
        sentinel = _Path()
        file_type_str = self.file_type.value
        # Coerce through _coerce_validation_issues so that ValidationIssue
        # instances built inside sk_series are rebuilt as this module's
        # canonical class (avoids Pydantic model_type errors under
        # ``python -m skilllint.plugin_validator``).
        warnings.extend(_coerce_validation_issues(check_sk004(frontmatter, sentinel, file_type_str)))
        warnings.extend(_coerce_validation_issues(check_sk005(frontmatter, sentinel, file_type_str)))

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (description quality requires human-written content)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix description issues (not supported).

        Args:
            path: Path to file to fix

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Description quality cannot be auto-fixed
        """
        raise NotImplementedError(
            "Description validation cannot be auto-fixed. Writing quality descriptions requires human judgment."
        )


# ============================================================================
# COMPLEXITY VALIDATOR (TOKEN-BASED)
# ============================================================================


class ComplexityValidator:
    """Validates skill complexity using token counting.

    Measures skill complexity by counting tokens in body content (excluding
    frontmatter) using tiktoken. Provides more accurate complexity measurement
    than line counting since it reflects actual Claude processing cost.
    """

    def validate(self, path: Path, policy: ValidationPolicy | None = None) -> ValidationResult:
        """Validate skill complexity using token counting.

        Args:
            path: Path to SKILL.md file
            policy: Optional resolved per-plugin policy.

        Returns:
            ValidationResult with warnings/errors based on token thresholds

        Note:
            Multiple early returns are necessary to handle various skip conditions gracefully.
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        # Only validate SKILL.md files
        if path.name != "SKILL.md":
            # Not a skill file - skip validation
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        # Read file
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                )
            )
            return ValidationResult(passed=False, errors=errors, warnings=warnings, info=info)

        # Split frontmatter and body
        frontmatter_text, _start_line, _end_line = extract_frontmatter(content)

        # Calculate body content (everything after frontmatter)
        # Note: re module already imported at module level (line 27)
        if frontmatter_text is not None:
            # Find end of frontmatter
            end_match = re.search(r"\n---\s*\n", content[3:])
            body = content[end_match.end() + 3 :] if end_match else content
        else:
            # No frontmatter - entire file is body
            body = content

        # Count tokens using tiktoken
        body_tokens = count_tokens(body)

        # Check against the resolved policy, retaining quality defaults.
        thresholds = policy.thresholds if policy is not None else DEFAULT_THRESHOLDS
        warning_threshold = thresholds.get("SK006", TOKEN_WARNING_THRESHOLD)
        error_threshold = thresholds.get("SK007", TOKEN_ERROR_THRESHOLD)
        if body_tokens > error_threshold:
            # CRITICAL: Must split skill
            errors.append(
                ValidationIssue(
                    field="complexity",
                    severity="error",
                    message=f"Skill body exceeds token limit ({body_tokens} tokens > {error_threshold} threshold)",
                    code=SK007,
                    docs_url=generate_docs_url(SK007),
                    suggestion="Run /plugin-creator:refactor-skill to split into multiple smaller skills",
                )
            )
        elif body_tokens > warning_threshold:
            # WARNING: Larger than Anthropic's official skills
            warnings.append(
                ValidationIssue(
                    field="complexity",
                    severity="warning",
                    message=f"Skill body is large ({body_tokens} tokens > {warning_threshold} threshold)",
                    code=SK006,
                    docs_url=generate_docs_url(SK006),
                    suggestion="This skill is larger than Anthropic's official skills. Review whether content can be moved to references/ or if the skill covers multiple domains that could be separated",
                )
            )

        # Pass if no errors (warnings don't fail validation)
        passed = len(errors) == 0
        return ValidationResult(passed=passed, errors=errors, warnings=warnings, info=info)

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (complexity requires content restructuring)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix complexity issues (not supported).

        Args:
            path: Path to file to fix

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Complexity issues cannot be auto-fixed
        """
        raise NotImplementedError(
            "Complexity validation cannot be auto-fixed. "
            "Reducing complexity requires content restructuring and splitting skills."
        )


# ============================================================================
# MARKDOWN TOKEN COUNTER (General markdown files)
# ============================================================================


class MarkdownTokenCounter:
    """Counts tokens in general markdown files (CLAUDE.md, references, etc.).

    Unlike ComplexityValidator which only processes SKILL.md files and applies
    skill-specific threshold checks, this counter works on any markdown file.
    It reports total and body token counts as info messages without applying
    skill-specific thresholds or triggering errors/warnings.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Count tokens in a markdown file and report as info.

        Args:
            path: Path to markdown file

        Returns:
            ValidationResult with token count info (always passes)
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            error = ValidationIssue(
                field="(file)",
                severity="error",
                message=f"Could not read file: {e}",
                code=FM002,
                docs_url=generate_docs_url(FM002),
            )
            return ValidationResult(passed=False, errors=[error], warnings=[], info=[])

        return ValidationResult(passed=True, errors=[], warnings=[], info=check_tc001(content))

    def count_file_tokens(self, path: Path, *, body_only: bool = False) -> int | None:
        """Count tokens in a file for programmatic use.

        Args:
            path: Path to markdown file
            body_only: When True, strip frontmatter and count only the body.
                Matches what ComplexityValidator measures for threshold comparisons.

        Returns:
            Token count (body or total), or None if counting failed
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return None

        if body_only:
            frontmatter_text, _start, _end = extract_frontmatter(content)
            if frontmatter_text is not None:
                end_match = re.search(r"\n---\s*\n", content[3:])
                text = content[end_match.end() + 3 :] if end_match else content
            else:
                text = content
            return count_tokens(text)

        return count_tokens(content)

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (token counting is read-only)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix not supported for token counting.

        Args:
            path: Path to file

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Token counting cannot be auto-fixed
        """
        raise NotImplementedError("Token counting is read-only, no fixes to apply.")


# ============================================================================
# PLUGIN REGISTRATION VALIDATOR
# ============================================================================


def _git_file_has_execute_bit(file_path: Path) -> bool | None:
    """Check if a file has the execute bit in Git's index or HEAD.

    Uses Git's tracked mode (100755 = executable, 100644 = not) so validation
    is consistent across platforms. On Windows, os.access(X_OK) is unreliable;
    checking Git ensures plugins that pass on Windows will also pass on Linux.

    Uses GitPython (project dependency) for consistency with other scripts.

    Args:
        file_path: Absolute path to the file.

    Returns:
        True if executable in Git, False if not, None if not in a Git repo or
        file is untracked.
    """
    resolved = file_path.resolve()
    try:
        repo = Repo(resolved.parent, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError, OSError):
        return None

    if repo.working_tree_dir is None:
        return None

    try:
        rel = resolved.relative_to(Path(repo.working_tree_dir))
    except ValueError:
        return None  # file is outside the working tree

    rel_str = str(rel).replace("\\", "/")

    # Prefer index (staged/unstaged); fall back to HEAD
    entry = repo.index.entries.get(entry_key(rel_str, 0))
    if entry is not None:
        return entry.mode == GIT_MODE_EXECUTABLE

    try:
        blob = repo.head.commit.tree[rel_str]
    except KeyError:
        return None
    return blob.mode == GIT_MODE_EXECUTABLE


def _get_git_remote_url(repo_dir: Path) -> str | None:
    """Extract the remote URL for the git repository at repo_dir.

    Args:
        repo_dir: Root of a git repository (directory containing .git/).

    Returns:
        Remote URL string with .git suffix stripped, or None if unavailable.
    """
    try:
        repo = Repo(str(repo_dir))
        remote_url = repo.remotes.origin.url
    except (InvalidGitRepositoryError, NoSuchPathError, AttributeError, ValueError):
        return None

    if not remote_url:
        return None

    return remote_url.removesuffix(".git")


def _get_git_author() -> dict[str, str] | None:
    """Extract author info from git config.

    Returns:
        Dict with 'name' and optionally 'email', or None if unavailable.
    """
    try:
        repo = Repo(search_parent_directories=True)
        reader = repo.config_reader()
        name = reader.get_value("user", "name", default="")
    except (InvalidGitRepositoryError, NoSuchPathError, KeyError):
        return None

    if not name:
        return None

    try:
        email = repo.config_reader().get_value("user", "email", default="")
    except KeyError:
        email = ""

    author: dict[str, str] = {"name": str(name)}
    if email:
        author["email"] = str(email)
    return author


def _generate_plugin_metadata(plugin_dir: Path) -> dict[str, YamlValue]:
    """Generate plugin.json metadata from git and file structure.

    Args:
        plugin_dir: Path to the plugin directory.

    Returns:
        Dict with repository, homepage, and author fields populated from git.
        Empty dict if git is unavailable or not in a repo.
    """
    metadata: dict[str, YamlValue] = {}

    current = plugin_dir
    while current != current.parent:
        if (current / ".git").exists():
            repo_url = _get_git_remote_url(current)
            if repo_url:
                metadata["repository"] = repo_url
                relative_path = plugin_dir.relative_to(current)
                metadata["homepage"] = f"{repo_url}/tree/main/{relative_path}"
            break
        current = current.parent

    author = _get_git_author()
    if author:
        metadata["author"] = author

    return metadata


def _sk009_message(unlisted: set[Path]) -> str:
    """Build the SK009 info message based on unlisted disk skills.

    Args:
        unlisted: Skills present on disk but absent from the explicit skills array.

    Returns:
        Human-readable message describing the manual-selection state.
    """
    if unlisted:
        paths = ", ".join(sorted(f"./{s}" for s in unlisted))
        return (
            "Plugin uses manual skill selection — new skills added to skills/ "
            f"will not be auto-loaded. The following skills are present on disk but not listed: {paths}"
        )
    return "Plugin uses manual skill selection — all skills/ are explicitly registered."


class PluginRegistrationValidator:
    """Validates capability registration against plugin.json.

    Checks that all capability files are registered and all registered paths
    exist. Also validates plugin.json metadata against git-derived values.

    PR001-PR005 detection lives in ``skilllint.rules.pr_series``; this class
    packages those results, adds SK009, and owns the git-metadata lookup.

    Open/Closed: new capability types can be added by extending
    ``find_actual_capabilities()`` in ``rules/pr_series.py`` and adding entries
    in validate().
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate registration and metadata for the plugin containing path.

        Args:
            path: Path to a file or directory within the plugin.

        Returns:
            ValidationResult with registration and metadata issues.
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        plugin_dir = find_plugin_dir(path)
        if plugin_dir is None:
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        plugin_json_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if not plugin_json_path.exists():
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        try:
            plugin_config = msgspec.json.decode(plugin_json_path.read_bytes())
        except msgspec.DecodeError as e:
            errors.append(
                ValidationIssue(
                    field="plugin.json",
                    severity="error",
                    message=f"Invalid JSON: {e}",
                    code=PL002,
                    docs_url=generate_docs_url(PL002),
                    suggestion="Fix JSON syntax errors",
                )
            )
            return ValidationResult(passed=False, errors=errors, warnings=warnings, info=info)

        # Registration checks — detection lives in skilllint.rules.pr_series.
        warnings.extend(check_pr001(plugin_config, plugin_dir))
        errors.extend(check_pr002(plugin_config, plugin_dir))
        info.extend(check_pr005(plugin_config, plugin_dir))

        # SK009 — manual skill selection mode (informational)
        if "skills" in plugin_config:
            actual_skills, _actual_agents, _actual_commands = find_actual_capabilities(plugin_dir)
            registered_skills = parse_registered_paths(plugin_config, plugin_dir, "skills")
            info.append(
                ValidationIssue(
                    field="plugin.json",
                    severity="info",
                    message=_sk009_message(actual_skills - registered_skills),
                    code=SK009,
                    docs_url=generate_docs_url(SK009),
                    suggestion=(
                        "To switch to auto-discovery mode, remove the 'skills' field from "
                        "plugin.json. Claude Code will discover all skills under ./skills/ "
                        "automatically."
                    ),
                )
            )

        # Metadata checks — detection lives in skilllint.rules.pr_series.
        git_metadata = _generate_plugin_metadata(plugin_dir)
        info.extend(check_pr003(plugin_config, git_metadata))
        warnings.extend(check_pr004(plugin_config, git_metadata))

        return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings, info=info)

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (registration issues require manual plugin.json edits).
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix registration issues (not supported).

        Args:
            path: Path to file or directory.

        Raises:
            NotImplementedError: Registration issues require manual fixes.
        """
        raise NotImplementedError("Plugin registration issues require manual edits to plugin.json.")


# ============================================================================
# PLUGIN AGENT FRONTMATTER VALIDATOR
# ============================================================================
# Validation logic lives in skilllint.rules.pa_series (check_pa001).
# PluginAgentFrontmatterValidator is re-exported from there for pipeline compatibility.
# Import happens at module bottom (line ~5030) to avoid circular imports.


# ============================================================================
# PLUGIN STRUCTURE VALIDATOR (CLAUDE CLI INTEGRATION)
# ============================================================================


class PluginStructureValidator:
    """Validates plugin structure using claude CLI.

    Integrates with external `claude plugin validate` CLI command for
    plugin.json validation. Gracefully handles cases where claude CLI
    is not available by skipping validation.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate plugin structure using claude CLI.

        Args:
            path: Path to plugin directory or file within plugin

        Returns:
            ValidationResult with errors from claude CLI or info if skipped
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        # Find plugin directory (contains .claude-plugin/plugin.json)
        plugin_dir = find_plugin_dir(path)
        if plugin_dir is None:
            # Not a plugin directory - skip validation
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        # Validate plugin.json JSON syntax locally before delegating to claude CLI.
        # Catches encoding/line-ending issues that may cause claude to fail inconsistently.
        plugin_json_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if plugin_json_path.exists():
            json_issues = check_pl002(plugin_json_path)
            if json_issues:
                errors.extend(json_issues)
                return ValidationResult(passed=False, errors=errors, warnings=warnings, info=info)

        mp_layout = check_pl006(plugin_dir)
        if mp_layout:
            errors.extend(mp_layout)
            return ValidationResult(passed=False, errors=errors, warnings=warnings, info=info)

        # Skip claude plugin validate when running inside a Claude Code session
        # (nested CLI invocations are blocked by Anthropic safety measure).
        if _should_skip_claude_validate():
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message="Skipping claude plugin validate (nested CLI sessions not supported)",
                    code=PL001,
                    docs_url=generate_docs_url(PL001),
                )
            )
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        # Check if claude CLI is available and get full path
        claude_path = self._get_claude_path()
        if claude_path is None:
            # Claude not available - skip with info message
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message="Claude CLI not available, skipping plugin structure validation",
                    code=PL001,
                    docs_url=generate_docs_url(PL001),
                    suggestion="Install Claude Code to enable plugin validation",
                )
            )
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        # On Windows, ensure CLAUDE_CODE_GIT_BASH_PATH is set if git-bash can be found
        _git_bash_path()

        # Run claude plugin validate
        # Unset CLAUDECODE so the subprocess is not treated as a nested CLI session.
        subprocess_env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        try:
            result = subprocess.run(
                [claude_path, "plugin", "validate", str(plugin_dir)],
                capture_output=True,
                text=True,
                timeout=CLAUDE_TIMEOUT,
                check=False,
                env=subprocess_env,
            )

            # Parse output for errors
            if result.returncode != 0:
                # Validation failed - parse errors from output
                self._parse_claude_errors(result.stdout, result.stderr, errors, warnings, info)

        except subprocess.TimeoutExpired:
            errors.append(
                ValidationIssue(
                    field="(plugin-validation)",
                    severity="error",
                    message=f"Claude plugin validation timed out after {CLAUDE_TIMEOUT} seconds",
                    code=PL002,
                    docs_url=generate_docs_url(PL002),
                )
            )
        except FileNotFoundError:
            # Claude CLI not found (should be caught by _is_claude_available)
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message="Claude CLI not found in PATH",
                    code=PL001,
                    docs_url=generate_docs_url(PL001),
                    suggestion="Install Claude Code to enable plugin validation",
                )
            )
        except OSError as e:
            # Subprocess failed to run (permissions, env, etc.) — skip, do not fail
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message=f"Claude CLI could not run; skipping plugin structure validation: {e}",
                    code=PL001,
                    docs_url=generate_docs_url(PL001),
                )
            )

        # Pass if no errors (warnings/info don't fail validation)
        passed = len(errors) == 0
        return ValidationResult(passed=passed, errors=errors, warnings=warnings, info=info)

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False. A relocation auto-fix once moved marketplace.json root keys
            into ``metadata``; it silently rewrote files that already carried
            documented root-level ``description``/``version`` fields and was
            removed rather than repaired (skilllint#114).
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix marketplace.json layout issues (not supported).

        Args:
            path: Path to plugin directory or file within plugin

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: PL006 findings must be corrected by hand; see
                ``can_fix`` for why the relocation auto-fix was removed.
        """
        raise NotImplementedError(
            "marketplace.json layout issues (PL006) have no auto-fix. An earlier "
            "relocation fix silently rewrote valid files and was removed (skilllint#114)."
        )

    def _get_claude_path(self) -> str | None:
        """Get full path to claude CLI if available.

        Returns:
            Full path to claude executable, or None if not found
        """
        return shutil.which("claude")

    def _is_claude_startup_failure(self, output: str) -> bool:
        """Return True if output indicates claude failed to start (env/runtime), not validation.

        We must not fail validation when claude cannot run (e.g. git-bash not found on
        Windows). Only fail when claude ran and reported plugin structure errors.
        """
        startup_patterns = (r"requires git-bash", r"CLAUDE_CODE_GIT_BASH_PATH", r"not in PATH")
        combined = output.lower()
        return any(re.search(p, combined, re.IGNORECASE) for p in startup_patterns)

    def _parse_claude_errors(
        self,
        stdout: str,
        stderr: str,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
        info: list[ValidationIssue],
    ) -> None:
        """Parse claude CLI output for validation errors.

        Args:
            stdout: Standard output from claude CLI
            stderr: Standard error from claude CLI
            errors: List to append error issues to
            warnings: List to append warning issues to
            info: List to append info issues to
        """
        # Combine stdout and stderr for parsing
        output = stdout + "\n" + stderr

        # If claude failed to start (env/runtime), skip — do not fail validation
        if self._is_claude_startup_failure(output):
            detail = (stdout.strip() + "\n" + stderr.strip())[:300] or "(no output)"
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message="Claude CLI could not start; skipping plugin structure validation",
                    code=PL001,
                    docs_url=generate_docs_url(PL001),
                    suggestion=detail,
                )
            )
            return

        # Map claude CLI output to error codes — each rule owns its own pattern.
        errors.extend(check_pl001(output))
        errors.extend(check_pl002(claude_output=output))
        errors.extend(check_pl003(output))
        errors.extend(check_pl004(output))
        errors.extend(check_pl005(output))

        # If no specific error pattern matched but validation failed, add generic error
        # Include actual CLI output for diagnosis (truncate to avoid huge messages)
        if not errors:
            errors.append(claude_validation_failure_issue(stdout, stderr))


# ============================================================================
# HOOK VALIDATOR
# ============================================================================


class HookValidator:
    """Validates Claude Code hooks.json configuration files.

    Validates JSON structure, event types, and hook entries.
    Hook scripts themselves are language-agnostic (any executable) and validated
    by their respective language linters (oxlint, ruff, shellcheck, etc.).

    Detection lives in ``skilllint.rules.hk_series``.  This class packages rule
    output into a ValidationResult and owns the HK005 auto-fix, which mutates
    the filesystem.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate a hooks.json configuration file.

        HK001 is terminal: an unreadable file, invalid JSON, or a missing /
        non-object top-level ``hooks`` key leaves nothing for the remaining
        rules to inspect.  Otherwise HK002/HK003 check the structure and
        HK004/HK005 check the referenced scripts.  HK004 (missing script) is
        a hard error and goes to ``errors``; HK005 (non-executable script) is
        a warning and goes to ``warnings``.  ``passed`` reflects ``errors``
        only, so HK005 findings alone do not fail validation.

        Args:
            path: Path to hooks.json

        Returns:
            ValidationResult with errors/warnings for hook issues
        """
        hooks_obj, errors = load_hooks_object(path)
        if hooks_obj is None:
            return ValidationResult(passed=False, errors=errors, warnings=[], info=[])

        warnings: list[ValidationIssue] = []
        errors.extend(check_hk002(hooks_obj))
        errors.extend(check_hk003(hooks_obj))
        self.validate_hook_script_references_in_hooks_dict(hooks_obj, path.parent, errors, warnings)

        return ValidationResult(passed=not errors, errors=errors, warnings=warnings, info=[])

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            True (HK005 non-executable scripts can be fixed with chmod/git)
        """
        return True

    def fix(self, path: Path) -> list[str]:
        """Auto-fix HK005 by making non-executable hook scripts executable.

        For each command script referenced in hooks.json that exists but is not
        executable, applies ``git update-index --chmod=+x`` when the file is
        git-tracked, or ``os.chmod`` with execute bits otherwise.

        Args:
            path: Path to hooks.json file

        Returns:
            List of human-readable descriptions of fixes applied
        """
        hooks_dict, _ = load_hooks_object(path)
        if hooks_dict is None:
            return []

        fixes: list[str] = []

        for command, resolved_path in iter_command_scripts(iter_hook_entries(hooks_dict), path.parent):
            if not resolved_path.exists():
                continue
            fix_desc = self._fix_execute_bit(resolved_path, command)
            if fix_desc:
                fixes.append(fix_desc)

        return fixes

    def _fix_execute_bit(self, resolved_path: Path, command: str) -> str | None:
        git_exec = _git_file_has_execute_bit(resolved_path)
        if git_exec is True:
            return None
        if git_exec is False:
            git_bin = shutil.which("git")
            if git_bin:
                try:
                    subprocess.run(
                        [git_bin, "update-index", "--chmod=+x", str(resolved_path)], check=True, capture_output=True
                    )
                except (subprocess.CalledProcessError, OSError):
                    pass
                else:
                    return f"Made hook script executable: {command}"
            return None
        if not os.access(resolved_path, os.X_OK):
            try:
                current_mode = resolved_path.stat().st_mode
                resolved_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except OSError:
                pass
            else:
                return f"Made hook script executable: {command}"
        return None

    @staticmethod
    def _is_file_path_reference(command: str) -> bool:
        """Return True if *command* looks like a file path rather than a bare shell command.

        Args:
            command: The ``command`` value from a hook entry.

        Returns:
            True if command is a file path reference, False otherwise.
        """
        return is_file_path_reference(command)

    @staticmethod
    def _find_hook_plugin_dir(base_dir: Path) -> Path:
        """Find the hook plugin directory by checking .claude-plugin/ directory existence.

        Args:
            base_dir: Base directory to search from.

        Returns:
            Plugin directory path if .claude-plugin/ exists, otherwise base_dir.
        """
        return find_hook_plugin_dir(base_dir)

    def _validate_command_script_references(
        self,
        hook_entries: Iterable[object],
        base_dir: Path,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ) -> None:
        """Check that file-path ``command`` values in hook entries exist and are executable.

        Args:
            hook_entries: List of hook entry dicts to inspect.
            base_dir: Directory to use as the resolution base for relative paths.
            errors: List to append HK004 (error-severity) issues to.
            warnings: List to append HK005 (warning-severity) issues to.
        """
        errors.extend(check_hk004(hook_entries, base_dir))
        for issue in check_hk005(hook_entries, base_dir):
            (errors if issue.severity == "error" else warnings).append(issue)

    def validate_hook_script_references_in_hooks_dict(
        self,
        hooks_dict: Mapping[str, YamlValue],
        base_dir: Path,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ) -> None:
        """Validate command file-path references in a hooks configuration dict.

        Iterates over a hooks configuration dict (same structure as the root
        ``"hooks"`` key in ``hooks.json``) and runs HK004/HK005 against every
        hook entry found.

        Args:
            hooks_dict: Hooks configuration mapping event types to groups.
            base_dir: Directory used as base for resolving relative script paths.
            errors: List to append HK004 (error-severity) issues to.
            warnings: List to append HK005 (warning-severity) issues to.
        """
        for entry in iter_hook_entries(hooks_dict):
            self._validate_command_script_references([entry], base_dir, errors, warnings)


# ============================================================================
# INTEGRATION LAYER
# ============================================================================


def is_claude_available() -> bool:
    """Check if claude CLI is available in PATH.

    Uses shutil.which() to safely detect claude CLI without shell execution.
    This function is used by validators to determine if Claude CLI-based
    validation is possible.

    Security: Uses shutil.which() to get full command path, no shell=True.

    Returns:
        True if claude CLI found in PATH, False otherwise
    """
    return shutil.which("claude") is not None


def validate_with_claude(plugin_dir: Path) -> tuple[bool, str]:
    """Run claude plugin validate if available.

    Executes claude CLI validation on a plugin directory. Gracefully handles
    cases where claude CLI is not available by returning success with skip message.

    Security requirements:
    - NEVER uses shell=True (command injection risk)
    - Passes command as list: [cmd_path, arg1, arg2]
    - Sets timeout to prevent hanging
    - Gets full command path via shutil.which()

    Args:
        plugin_dir: Path to plugin directory containing .claude-plugin/plugin.json

    Returns:
        Tuple of (success, output):
        - If claude not available: (True, "skipped")
        - If not a plugin directory: (True, "skipped")
        - If validation passes: (True, stdout)
        - If validation fails: (False, stderr + stdout)

    Raises:
        Never raises - returns (False, error_message) on failure
    """
    # Check if claude CLI is available
    claude_path = shutil.which("claude")
    if claude_path is None:
        return True, "claude CLI not available (skipped)"

    # Check if this is a plugin directory
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    if not plugin_json.exists():
        return True, "Not a plugin directory (skipped)"

    # Run claude plugin validate with security best practices
    # Unset CLAUDECODE so the subprocess is not treated as a nested CLI session.
    subprocess_env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        result = subprocess.run(
            [claude_path, "plugin", "validate", str(plugin_dir)],
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT,
            check=False,  # Handle non-zero exit code ourselves
            env=subprocess_env,
        )
    except subprocess.TimeoutExpired:
        return (False, f"Claude plugin validation timed out after {CLAUDE_TIMEOUT} seconds")
    except (FileNotFoundError, OSError) as e:
        # FileNotFoundError: Claude CLI not found (should be caught by shutil.which)
        # OSError: Other subprocess errors (permission denied, etc.)
        is_not_found = isinstance(e, FileNotFoundError)
        message = (
            "Claude CLI not found in PATH (skipped)" if is_not_found else f"Failed to run claude plugin validate: {e}"
        )
        # Not found is a skip (success), other OS errors are failures
        return is_not_found, message
    else:
        # Return success if validation passed, failure with details otherwise
        success = result.returncode == 0
        output = result.stdout if success else result.stderr + "\n" + result.stdout
        return success, output


def get_staged_files() -> list[Path]:
    """Get list of staged files for pre-commit context.

    Uses GitPython to identify which files are staged for commit (index vs HEAD).
    Used in pre-commit hooks to validate only changed files.

    Returns:
        List of Path objects for staged files
        Empty list if not in a git repository or no staged files

    Raises:
        Never raises - returns empty list on failure
    """
    try:
        repo = Repo(search_parent_directories=True)
        # diff between index (staged) and HEAD commit gives staged files
        diffs = repo.index.diff(repo.head.commit)
        return [Path(item.a_path) for item in diffs if item.a_path]
    except (InvalidGitRepositoryError, NoSuchPathError, ValueError):
        return []
    except Exception:  # ruff: ignore[blind-except]
        return []


# ============================================================================
# REPORTER PROTOCOL
# ============================================================================


# ============================================================================
# IGNORE PATTERN SUPPORT
# ============================================================================


# _load_ignore_patterns and _is_ignored moved to scan_runtime.py


# ============================================================================
# FRONTMATTER REQUIREMENT LOGIC
# ============================================================================


class _FrontmatterRequirement(StrEnum):
    """Whether a file requires YAML frontmatter."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    EXEMPT = "exempt"


def _frontmatter_requirement(path: Path) -> _FrontmatterRequirement:
    """Determine whether frontmatter is required for a given path.

    Rules:
    - Files in FRONTMATTER_EXEMPT_FILENAMES are always exempt.
    - ``**/skills/*/SKILL.md`` (direct child of skill dir) -- required.
    - ``**/agents/*.md`` (direct child of agents dir) -- required.
    - ``**/commands/*.md`` (direct child of commands dir) -- required.
    - Deeper nested files under agents/ or commands/ -- optional.
      If the file already contains frontmatter it will be validated normally;
      if it does not, frontmatter validation is skipped entirely.

    Args:
        path: Path to the markdown file.

    Returns:
        _FrontmatterRequirement indicating the frontmatter policy for this file.
    """
    # Exempt well-known filenames regardless of location
    if path.name in FRONTMATTER_EXEMPT_FILENAMES:
        return _FrontmatterRequirement.EXEMPT

    # SKILL.md files are always required (the FileType detector already handles this)
    if path.name == "SKILL.md":
        return _FrontmatterRequirement.REQUIRED

    # Check parent directory name to distinguish direct child vs nested
    parent_name = path.parent.name

    if parent_name == "agents":
        return _FrontmatterRequirement.REQUIRED
    if parent_name == "commands":
        return _FrontmatterRequirement.REQUIRED

    # If "agents" or "commands" appears anywhere in the path parts but the
    # immediate parent is NOT that directory, this is a nested subdirectory file.
    parts = set(path.parts)
    if "agents" in parts or "commands" in parts:
        return _FrontmatterRequirement.OPTIONAL

    # Default: required (preserves existing behavior for any other case)
    return _FrontmatterRequirement.REQUIRED


def _file_has_frontmatter(path: Path) -> bool:
    """Quick check whether a file starts with a YAML frontmatter delimiter.

    Args:
        path: Path to file to check.

    Returns:
        True if the file content starts with ``---``.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return content.startswith("---")


# ============================================================================
# CLI LAYER
# ============================================================================


_NAME_BEARING_FILE_TYPES: frozenset[FileType] = frozenset({FileType.SKILL, FileType.AGENT, FileType.COMMAND})
"""File types whose frontmatter may carry a ``name`` field (FM010 applies)."""


def _get_validators_for_path(path: Path) -> list[Validator]:
    """Return validators to run for the given path based on file type.

    Args:
        path: Path to validate.

    Returns:
        List of validator instances (empty for unknown file types).
    """
    file_type = FileType.detect_file_type(path)
    validators: list[Validator] = [SymlinkTargetValidator()]

    if file_type in _NAME_BEARING_FILE_TYPES:
        fm_req = _frontmatter_requirement(path)
        if fm_req == _FrontmatterRequirement.EXEMPT:
            return [SymlinkTargetValidator()]
        if fm_req == _FrontmatterRequirement.REQUIRED or _file_has_frontmatter(path):
            validators.append(FrontmatterValidator())
        if fm_req == _FrontmatterRequirement.REQUIRED or _file_has_frontmatter(path):
            validators.append(DescriptionValidator(file_type=file_type))
        validators.append(NamespaceReferenceValidator())
        # AS-series rules enforce the AgentSkills specification, which governs
        # SKILL.md and nothing else. Agent files are a harness extension the
        # spec does not define, so running AS rules on them is a category error
        # regardless of what an individual rule happens to check.
        if file_type == FileType.SKILL:
            validators.append(AsSeriesValidator())
        if file_type == FileType.SKILL:
            validators.extend([ComplexityValidator(), InternalLinkValidator(), ProgressiveDisclosureValidator()])
    elif file_type == FileType.PLUGIN:
        validators.extend((PluginStructureValidator(), PluginAgentFrontmatterValidator()))
    elif file_type == FileType.HOOK_CONFIG:
        validators.append(HookValidator())
    elif file_type == FileType.HOOK_SCRIPT:
        pass
    elif file_type in {FileType.CLAUDE_MD, FileType.REFERENCE, FileType.MARKDOWN}:
        validators.append(MarkdownTokenCounter())
    else:
        # Unknown file type — return empty list.  The CLI entry point
        # (validate_single_path) checks for this and emits a user-facing
        # error; library callers (run_platform_checks) receive an empty
        # validator list and can proceed without exceptions.
        return []

    return validators


def _get_fixers_for_path(validators: list[Validator], path: Path) -> list[Validator]:
    """Return validators to invoke for ``--fix`` on the given path.

    A validator that reports a rule and a validator that repairs it need not be
    the same object. FM010 is reported by ``FrontmatterValidator`` so that each
    finding has exactly one owner, but ``NameFormatValidator`` holds the only
    implementation of the FM010 repair — normalising the ``name`` field and
    renaming a mismatched skill directory. It is therefore appended here as a
    fix-only participant and deliberately kept out of the reporting pipeline.

    The reporting instances are reused rather than rebuilt: ``FrontmatterValidator``
    carries FM009 info from ``fix()`` to the following ``validate()`` on
    ``_pending_fm009_info``, and a fresh instance would drop it.

    Args:
        validators: Reporting validators already built for this path.
        path: Path to fix.

    Returns:
        ``validators`` plus any fix-only validator that applies to this path.
    """
    if not validators or FileType.detect_file_type(path) not in _NAME_BEARING_FILE_TYPES:
        return validators
    if _frontmatter_requirement(path) == _FrontmatterRequirement.EXEMPT:
        return validators
    return [*validators, NameFormatValidator()]


def _collect_validator_results(
    validators: list[Validator],
    path: Path,
    *,
    config_root: Path | None,
    ignore_config: IgnoreConfig,
    policy: ValidationPolicy | None = None,
) -> list[tuple[str, ValidationResult]]:
    """Run each validator and collect results, applying ignore filtering.

    Args:
        validators: Validators to run.
        path: Path to validate.
        config_root: Directory containing the resolved config file (plugin root
            or .skilllint.json parent). Used as the base for relative-path
            prefix matching. Pass ``None`` to skip filtering.
        ignore_config: Resolved ignore configuration.
        policy: Optional resolved token/severity policy.

    Returns:
        List of (validator_class_name, result) tuples.
    """
    results: list[tuple[str, ValidationResult]] = []
    for validator in validators:
        name = type(validator).__name__
        if policy is not None and isinstance(validator, (ComplexityValidator, AsSeriesValidator)):
            result = validator.validate(path, policy)
        else:
            result = validator.validate(path)
        if policy is not None and policy.severity:

            def remap(issue: ValidationIssue) -> ValidationIssue:
                configured = policy.severity.get(str(issue.code))
                severity: Literal["error", "warning", "info"] = issue.severity
                if configured == "warning":
                    severity = "warning"
                elif configured == "info":
                    severity = "info"
                return ValidationIssue(
                    field=issue.field,
                    severity=severity,
                    message=issue.message,
                    code=issue.code,
                    line=issue.line,
                    docs_url=issue.docs_url,
                    suggestion=issue.suggestion,
                )

            issues = [remap(i) for i in [*result.errors, *result.warnings, *result.info]]
            result = ValidationResult(
                passed=not any(i.severity == "error" for i in issues),
                errors=[i for i in issues if i.severity == "error"],
                warnings=[i for i in issues if i.severity == "warning"],
                info=[i for i in issues if i.severity == "info"],
            )
        if config_root is not None:
            result = _filter_result_by_ignore(result, path, config_root, ignore_config)
        results.append((name, result))
    return results


def _normalize_skill_folder(path: Path) -> Path:
    """Map a skill folder entrypoint to its direct ``SKILL.md`` file.

    Returns:
        The direct skill file for a skill folder, otherwise the original path.
    """
    skill_file = path / "SKILL.md"
    return skill_file if path.is_dir() and skill_file.is_file() else path


def validate_single_path(
    path: Path,
    *,
    check: bool,
    fix: bool,
    verbose: bool,
    per_run_cache: dict[str, tuple[IgnoreConfig, Path | None]] | None = None,
    per_run_policy_cache: dict[str, tuple[ValidationPolicy, Path | None]] | None = None,
) -> FileResults:
    """Validate a single path and return results grouped by file.

    Args:
        path: Path to validate.
        check: Validate only, don't auto-fix.
        fix: Auto-fix issues where possible.
        verbose: Show detailed output.
        per_run_cache: Optional mutable cache for ignore-config resolution.
            When provided, directory-tree walks are cached across calls so
            sibling files share the same lookup result.  Pass the same dict
            for the lifetime of a single scan run.
        per_run_policy_cache: Optional mutable cache for policy resolution,
            with the same per-run lifetime as ``per_run_cache``.  Sharing it
            avoids re-walking and re-reading config for every sibling file.

    Returns:
        Mapping of file path to list of (validator_class_name, result) tuples.

    Raises:
        typer.Exit: If path doesn't exist or file type is unknown.

    """
    if not path.exists():
        typer.echo(f"Error: Path does not exist: {path}", err=True)
        raise typer.Exit(2) from None

    path = _normalize_skill_folder(path)

    validators = _get_validators_for_path(path)
    if not validators:
        # _get_validators_for_path returns [] for unknown file types.
        # In CLI context this is a user error — report it and exit.
        file_type = FileType.detect_file_type(path)
        if file_type == FileType.UNKNOWN:
            typer.echo(f"Error: Cannot determine file type for: {path}", err=True)
            typer.echo(
                "Expected: SKILL.md, agent .md, command .md, hooks.json, plugin directory, or markdown file", err=True
            )
            raise typer.Exit(2) from None
        return {path: []}

    cache: dict[str, tuple[IgnoreConfig, Path | None]] = per_run_cache if per_run_cache is not None else {}
    ignore_config, config_root = _resolve_ignore_config(path, cache)
    policy_cache: dict[str, tuple[ValidationPolicy, Path | None]] = (
        per_run_policy_cache if per_run_policy_cache is not None else {}
    )
    policy, _policy_root = _resolve_policy(path, policy_cache)
    policy = ValidationPolicy(policy.thresholds, policy.severity, ignore_config)

    validator_results = _collect_validator_results(
        validators, path, config_root=config_root, ignore_config=ignore_config, policy=policy
    )

    # Note: --fix still runs even for suppressed issues (ignore = suppress reporting, not fixing)
    if fix:
        # Guard: never auto-fix intentionally broken test fixtures
        if "failing-examples" in path.parts:
            _logger.debug("Skipping auto-fix for fixture file: %s", path)
        else:
            fixes_applied: list[str] = []
            for validator in _get_fixers_for_path(validators, path):
                if validator.can_fix():
                    try:
                        validator_fixes = validator.fix(path)
                        fixes_applied.extend(validator_fixes)
                    except NotImplementedError:
                        pass  # Validator doesn't support fixing

            # Re-validate after fixes
            if fixes_applied:
                validator_results = _collect_validator_results(
                    validators, path, config_root=config_root, ignore_config=ignore_config, policy=policy
                )

    return {path: validator_results}


def _handle_tokens_only(paths: list[Path], *, batch: bool = False) -> None:
    r"""Output only the integer token count for each path, then exit.

    For a single path, prints just the integer. For multiple paths (or when
    ``batch`` is True), prints one entry per line. When ``batch`` is True,
    each line is tab-separated ``<count>\\t<path>`` for machine readability.

    Token counting always uses body-only (frontmatter stripped) so that the
    numbers match what ComplexityValidator measures against thresholds.

    Args:
        paths: Paths to count tokens for
        batch: When True, emit ``<count>\\t<path>`` tab-separated output.

    Raises:
        typer.Exit: Always exits (code 0 on success, code 2 on error)
    """
    counter = MarkdownTokenCounter()
    entries: list[tuple[int, Path]] = []
    for path in paths:
        if not path.exists():
            typer.echo(f"Error: Path does not exist: {path}", err=True)
            raise typer.Exit(2) from None
        normalized_path = _normalize_skill_folder(path)
        # Always count body-only so output matches ComplexityValidator thresholds
        token_count = counter.count_file_tokens(normalized_path, body_only=True)
        if token_count is None:
            typer.echo(f"Error: Could not count tokens for: {normalized_path}", err=True)
            raise typer.Exit(2) from None
        entries.append((token_count, normalized_path))

    if batch:
        for count, path in entries:
            print(f"{count}\t{path}")
    else:
        for count, _path in entries:
            print(count)
    raise typer.Exit(0) from None


# _discover_validatable_paths, _resolve_filter_and_expand_paths,
# and _compute_summary moved to scan_runtime.py


def _show_help_and_exit(ctx: typer.Context, code: int = 0) -> NoReturn:
    """Print the help text for the current command and exit.

    Args:
        ctx: The Typer/Click context to extract help from.
        code: Exit code to use.

    Raises:
        typer.Exit: Always raised to terminate after displaying help.
    """
    typer.echo(ctx.get_help())
    raise typer.Exit(code) from None


# ---------------------------------------------------------------------------
# Platform adapter dispatch (plan 02-05)
# ---------------------------------------------------------------------------


def is_skill_md(path: Path) -> bool:
    """Return True if the path is a SKILL.md file."""
    return path.name == "SKILL.md"


def parse_skill_md(path: Path) -> tuple[dict, list[str], str | None, list[str]]:
    """Parse a SKILL.md file into frontmatter dict and body lines.

    Uses extract_frontmatter (from frontmatter_core) and _safe_load_yaml
    to avoid the namespace conflict between the ``frontmatter`` and
    ``python-frontmatter`` PyPI packages.

    When YAML parsing fails due to unquoted colons, the frontmatter is
    auto-fixed (colons quoted) and the fixed data is returned along with
    a list of fields that were fixed.

    Args:
        path: Path to the SKILL.md file.

    Returns:
        Tuple of (frontmatter dict, body lines, yaml_error_message,
        colon_fixed_fields).  yaml_error_message is None when parsing
        succeeds (or when the colon auto-fix succeeds).
        colon_fixed_fields lists field names where unquoted colons were
        detected and auto-fixed. body_lines excludes the closing '---'
        delimiter. When frontmatter opens with '---' but never closes,
        body_lines is empty — there is no recoverable body.
    """
    content = path.read_text(encoding="utf-8")
    fm_text, _start, end_line = extract_frontmatter(content)
    if fm_text is None:
        if content.startswith("---"):
            # Opening delimiter present but never closed — no recoverable body.
            return {}, [], None, []
        return {}, content.splitlines(), None, []
    parsed, yaml_err, colon_fields, _used_text = safe_load_yaml_with_colon_fix(fm_text)
    frontmatter_dict: dict = parsed if parsed is not None else {}
    body_lines = content.splitlines()[end_line + 1 :]
    return frontmatter_dict, body_lines, yaml_err, colon_fields


def _issue_to_violation(issue: ValidationIssue) -> dict:
    """Convert a ValidationIssue to the violation dict shape used by adapters.

    Attaches the rule's registry authority so that findings from the validator
    pipeline carry the same provenance as AS-series violations, which build
    theirs through ``rule_authority`` in ``rules/as_series.py``.

    Args:
        issue: Issue emitted by a validator.

    Returns:
        Violation dict with code, severity and message, plus authority when the
        rule declares one.
    """
    violation = {"code": str(issue.code), "severity": str(issue.severity), "message": str(issue.message)}
    authority = rule_authority(str(issue.code))
    if authority is not None:
        violation["authority"] = authority
    return violation


def run_platform_checks(
    path: Path, adapter: PlatformAdapter, *, policy_cache: dict[str, tuple[ValidationPolicy, Path | None]] | None = None
) -> list[dict]:
    """Run platform-specific validation for a single adapter.

    Dispatches to adapter.validate(path) for all adapter types.
    For ClaudeCodeAdapter, also routes to the existing SK/PR/HK pipeline.

    Args:
        path: File path to validate.
        adapter: PlatformAdapter instance for constraint scope filtering.
        policy_cache: Optional mutable per-run policy cache, forwarded to the
            nested Claude pipeline so a multi-file scan reads each config —
            and emits its diagnostics — once rather than once per file.

    Returns:
        List of violation dicts with keys: code, severity, message.
    """
    if isinstance(adapter, ClaudeCodeAdapter):
        # Route files through the SK/PR/HK pipeline only when the pipeline
        # has validators for the file type.  Files the pipeline does not
        # handle (e.g. test fixtures named "valid_plugin.json" rather than
        # "plugin.json") go directly to the adapter's own validate().
        sk_validators = _get_validators_for_path(path)
        # Filter validators by provider constraint scopes
        constraint_scopes = adapter.constraint_scopes()
        sk_validators = filter_validators_by_constraint_scopes(sk_validators, constraint_scopes)
        if not sk_validators:
            return list(adapter.validate(path))

        file_results = validate_single_path(
            path, check=True, fix=False, verbose=False, per_run_policy_cache=policy_cache
        )

        violations: list[dict] = []
        for validator_results in file_results.values():
            for name, vr_result in validator_results:
                # AsSeriesValidator is already run unconditionally in validate_file()
                # before run_platform_checks() is called.  Skipping it here prevents
                # duplicate AS-series violations in the output.
                if name == "AsSeriesValidator":
                    continue
                all_issues = [*vr_result.errors, *vr_result.warnings, *vr_result.info]
                violations.extend(_issue_to_violation(issue) for issue in all_issues)
        return violations

    # Cursor and Codex adapters implement validate() directly
    return list(adapter.validate(path))


def _adapter_runs_frontmatter_pipeline(matching: list[PlatformAdapter]) -> bool:
    """Report whether a selected adapter routes SKILL.md through the validator pipeline.

    Only ``ClaudeCodeAdapter`` does — Cursor validates ``.mdc`` files and Codex
    validates ``AGENTS.md``/``.rules``, so neither runs ``FrontmatterValidator``
    over a ``SKILL.md``. Callers use this to decide whether the canonical rule
    owners still need invoking directly, and whether a generic finding would be
    a duplicate.

    Args:
        matching: Adapters selected for this file.

    Returns:
        True when at least one selected adapter runs the frontmatter pipeline.
    """
    return any(isinstance(adapter, ClaudeCodeAdapter) for adapter in matching)


def _shared_skill_frontmatter_violations(path: Path, frontmatter: dict, policy: ValidationPolicy | None) -> list[dict]:
    """Return canonical SKILL.md findings for adapters that skip the pipeline.

    AS001-AS003 and AS005 used to cover name syntax, the directory match, the
    missing description and the token budget on this path. They were duplicates
    of FM010, FM001 and SK006/SK007 and were retired, so the canonical owners
    are invoked here instead. Without this a Cursor or Codex skill, or a
    ``SKILL.md`` no adapter claims, would be checked by nothing but AS006.

    Args:
        path: Path to the SKILL.md file.
        frontmatter: Parsed frontmatter mapping.
        policy: Resolved per-plugin policy, for the configured token thresholds.

    Returns:
        Violation dicts, with authority attached where the rule declares one.
    """
    # FM001 covers both `name` and `description`, but AS001 already owns name
    # presence for a SKILL.md on this same path, so only the description claim
    # (the one AS003 used to carry here) is taken.
    #
    # check_fm001 grades a skill description as a warning because skills.md calls
    # it "Recommended". This path runs only where no adapter applies the Claude
    # Code reading, and the AgentSkills specification the AS series enforces marks
    # description Required, which is why AS003 was an error here. Keep that grade
    # so an invalid file still fails the run.
    issues = [
        issue.model_copy(update={"severity": "error"})
        for issue in check_fm001(frontmatter, path, "skill")
        if issue.field == "description"
    ]
    issues.extend(check_fm010(frontmatter, path, "skill"))
    complexity = ComplexityValidator().validate(path, policy)
    issues.extend([*complexity.errors, *complexity.warnings])
    return [_issue_to_violation(issue) for issue in issues]


def _skill_md_violations(
    path: Path, *, pipeline_runs: bool, policy_cache: dict[str, tuple[ValidationPolicy, Path | None]]
) -> list[dict]:
    """Return everything ``validate_file`` reports for a SKILL.md before dispatch.

    Args:
        path: Path to the SKILL.md file.
        pipeline_runs: Whether a selected adapter runs the frontmatter pipeline,
            which decides whether the generic FM002 and the canonical rule
            owners would be duplicates here.
        policy_cache: Per-run policy cache, shared so a large scan reads each
            config once.

    Returns:
        Violation dicts with any configured severity downgrade applied.
    """
    frontmatter_data, body_lines, yaml_err, colon_fields = parse_skill_md(path)
    violations: list[dict] = []

    # Suppress the generic FM002 only when the pipeline will report it — keying
    # on whether any adapter matched silenced it for Cursor and Codex, neither
    # of which validates SKILL.md frontmatter.
    if yaml_err is not None and not pipeline_runs:
        violations.append({"code": str(FM002), "severity": "error", "message": f"Invalid YAML frontmatter: {yaml_err}"})

    # Resolve per-plugin policy so --platform validation honors the same
    # configured thresholds AND severity as the default path (PR #97 review:
    # the two paths must not lint the same skill differently).
    policy, policy_root = _resolve_policy(path, policy_cache)
    violations.extend(
        run_as_series(
            path,
            frontmatter_data,
            body_lines,
            warning_threshold=policy.thresholds.get("SK006", TOKEN_WARNING_THRESHOLD),
            error_threshold=policy.thresholds.get("SK007", TOKEN_ERROR_THRESHOLD),
        )
    )
    if not pipeline_runs:
        # FM009 has no reporter here either: parse_skill_md recovers the unquoted
        # colon in memory and returns no YAML error, and FrontmatterValidator —
        # which normally raises this — never runs for Cursor or Codex.
        violations.extend(_issue_to_violation(issue) for issue in _fm009_recovery_warnings(colon_fields))
        violations.extend(_shared_skill_frontmatter_violations(path, frontmatter_data, policy))

    # Suppression applies to every reporter, so the --platform route must honour
    # the same ignore config as the default path rather than only its thresholds.
    # _load_policy fills ValidationPolicy.ignore from the same file it reads the
    # thresholds from, and policy_root is that file's directory.
    if policy.ignore and policy_root is not None:
        violations = [v for v in violations if not _is_suppressed(policy.ignore, path, policy_root, str(v.get("code")))]

    if not policy.severity:
        return violations
    # Apply configured severity downgrades so --platform matches the
    # default-path remap.
    return [
        {**violation, "severity": configured}
        if (configured := policy.severity.get(str(violation.get("code")))) in _VALID_SEVERITIES
        else violation
        for violation in violations
    ]


def validate_file(
    path: Path,
    adapters: dict,
    platform_override: str | None = None,
    policy_cache: dict[str, tuple[ValidationPolicy, Path | None]] | None = None,
) -> list[dict]:
    """Dispatch validation for a single file using the adapter registry.

    AS-series fires ONCE per file (before per-adapter loop) — structural dedup.

    Args:
        path: File to validate.
        adapters: Dict of adapter_id -> PlatformAdapter.
        platform_override: If set, restrict to this adapter ID. The selected
            adapter's constraint_scopes() will be used to filter rules by
            provider relevance (shared vs provider_specific).
        policy_cache: Optional mutable per-run policy cache. Sharing it across
            a scan prevents re-reading config and re-emitting diagnostics once
            per file.

    Returns:
        List of violation dicts with keys: code, severity, message.
        May include 'authority' key with origin and reference when the rule
        has authority metadata.
    """
    resolved_policy_cache: dict[str, tuple[ValidationPolicy, Path | None]] = (
        policy_cache if policy_cache is not None else {}
    )
    pure = PurePath(path)
    if platform_override:
        matching = [adapters[platform_override]]
    else:
        matching = [a for a in adapters.values() if matches_file(a, pure)]

    # AS-series rules are cross-platform — they run before the adapter matching
    # guard so that a SKILL.md outside a recognised plugin structure is still
    # checked even when no platform adapter claims the file. They do not extend
    # to agent files: the AgentSkills specification defines SKILL.md only.
    violations: list[dict] = (
        _skill_md_violations(
            path, pipeline_runs=_adapter_runs_frontmatter_pipeline(matching), policy_cache=resolved_policy_cache
        )
        if is_skill_md(path)
        else []
    )

    if not matching:
        return violations

    primary_adapter = matching[0]
    _logger.debug("Validating %s with adapter %s", path, primary_adapter.id())

    for adapter in matching:
        violations.extend(run_platform_checks(path, adapter, policy_cache=resolved_policy_cache))

    return violations


def _resolve_platform_override(platform: str | None) -> str | None:
    """Validate and normalize the --platform CLI value.

    Args:
        platform: Raw CLI value (may contain hyphens).

    Returns:
        Normalized platform key (underscores) or None.

    Raises:
        typer.Exit: If the platform is not a registered adapter.
    """
    if platform is None:
        return None
    platform_key = platform.replace("-", "_")
    if platform_key not in ADAPTERS:
        typer.echo(
            f"Unknown platform: {platform!r}. Valid choices: {', '.join(k.replace('_', '-') for k in ADAPTERS)}",
            err=True,
        )
        raise typer.Exit(2) from None
    return platform_key


def violations_to_result(violations: list[dict]) -> ValidationResult:
    """Convert a list of violation dicts into a ValidationResult.

    Args:
        violations: List of dicts with keys: code, severity, message.

    Returns:
        A ValidationResult grouping issues by severity.
    """
    issues = [
        ValidationIssue(
            field=v["code"],
            severity=(
                v.get("severity", "error") if v.get("severity", "error") in {"error", "warning", "info"} else "error"
            ),
            message=v.get("message", ""),
            code=v["code"],
        )
        for v in violations
    ]
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    info = [i for i in issues if i.severity == "info"]
    return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings, info=info)


def main(
    ctx: typer.Context,
    paths: Annotated[
        list[Path] | None, typer.Argument(help="Paths to plugin, skill, agent, or command files to validate")
    ] = None,
    *,
    check: Annotated[bool, typer.Option("--check", help="Validate only, don't auto-fix")] = False,
    fix: Annotated[bool, typer.Option("--fix", help="Auto-fix issues where possible")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed validation output including info messages")
    ] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color output for CI environments")] = False,
    tokens_only: Annotated[
        bool, typer.Option("--tokens-only", help="Output only the integer token count (for programmatic use)")
    ] = False,
    show_progress: Annotated[
        bool, typer.Option("--show-progress", help="Show per-file PASSED/FAILED status for all files")
    ] = False,
    show_summary: Annotated[
        bool, typer.Option("--show-summary", help="Show validation summary panel at the end")
    ] = False,
    filter_glob: Annotated[
        str | None,
        typer.Option(
            "--filter",
            help=(
                "Glob pattern to match files within a directory "
                "(e.g. '**/skills/*/SKILL.md'). "
                "Ignored when the positional path is a file. "
                "Mutually exclusive with --filter-type."
            ),
        ),
    ] = None,
    filter_type: Annotated[
        str | None,
        typer.Option(
            "--filter-type",
            help=(
                "Shortcut for common filter patterns. "
                "Choices: skills (**/skills/*/SKILL.md), "
                "agents (**/agents/*.md), "
                "commands (**/commands/*.md). "
                "Mutually exclusive with --filter."
            ),
        ),
    ] = None,
    platform: Annotated[
        str | None,
        typer.Option(
            "--platform",
            help=(
                "Restrict validation to a specific platform adapter. "
                "Initial bundled adapters: claude-code, cursor, codex. "
                "See .claude/vendor/CLAUDE.md for all supported platforms."
            ),
        ),
    ] = None,
    record: Path | None = None,
    include_gitignore: bool = False,
) -> None:
    """Validate Claude Code plugins, skills, agents, and commands."""
    # If a subcommand was invoked, don't run validation
    if ctx.invoked_subcommand is not None:
        return

    # Show help when no arguments provided
    if not paths:
        _show_help_and_exit(ctx, code=0)

    # Validate that all provided paths exist; report non-existent ones
    bad_paths = [str(p) for p in paths if not p.exists()]
    if bad_paths:
        typer.echo(f"Path does not exist: {', '.join(bad_paths)}", err=True)
        typer.echo("", err=True)
        _show_help_and_exit(ctx, code=2)

    platform_override = _resolve_platform_override(platform)

    record_console = _make_recording_console(no_color=no_color) if record is not None else None

    def _run_validation_command() -> None:
        expanded_paths, is_batch = _resolve_filter_and_expand_paths(paths, filter_glob, filter_type)
        if platform_override is not None:
            expanded_paths = [_normalize_skill_folder(path) for path in expanded_paths]

        if tokens_only:
            _handle_tokens_only(expanded_paths, batch=is_batch)

        if check and fix:
            typer.echo("Error: Cannot use both --check and --fix flags", err=True)
            raise typer.Exit(2) from None

        # One shared cache per scan run — prevents re-walking the directory
        # tree for every file when many files share the same config root.
        per_run_cache: dict[str, tuple[IgnoreConfig, Path | None]] = {}
        per_run_policy_cache: dict[str, tuple[ValidationPolicy, Path | None]] = {}

        def _validate_with_cache(p: Path, *, check: bool, fix: bool, verbose: bool) -> FileResults:
            return validate_single_path(
                p,
                check=check,
                fix=fix,
                verbose=verbose,
                per_run_cache=per_run_cache,
                per_run_policy_cache=per_run_policy_cache,
            )

        run_validation_loop(
            expanded_paths=expanded_paths,
            check=check,
            fix=fix,
            verbose=verbose,
            no_color=no_color,
            show_progress=show_progress,
            show_summary=show_summary,
            platform_override=platform_override,
            validate_single_path=_validate_with_cache,
            validate_file=lambda p, a, o: validate_file(p, a, o, policy_cache=per_run_policy_cache),
            violations_to_result=violations_to_result,
            adapters=ADAPTERS,
            record_console=record_console,
            include_gitignore=include_gitignore,
        )

    try:
        _run_validation_command()
    except (SystemExit, typer.Exit):
        _maybe_export_recording(record_console, record)
        raise
    except KeyboardInterrupt:
        typer.echo("\nInterrupted by user", err=True)
        raise typer.Exit(130) from None


# =============================================================================
# CLI APP SETUP
# =============================================================================

# Create Typer app
app = typer.Typer(help="Validate Claude Code plugins and skills", add_completion=False)
app.add_typer(docs_app, name="docs")

# Version option handled via callback


@app.callback(invoke_without_command=True)
def _callback(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", "-V", help="Show version and exit", is_eager=True)] = False,
) -> None:
    """Validate Claude Code plugins, skills, agents, and commands."""
    if version:
        print(f"skilllint {__version__}")
        raise typer.Exit
    if ctx.invoked_subcommand is None:
        print("Use 'skilllint --help' for usage.")
        raise typer.Exit(1)


def _show_rules_list(
    platform: str | None = None, category: str | None = None, severity: str | None = None, *, console: _Console
) -> None:
    """Show list of rules (shared logic for callback and rules_cmd)."""
    rules = _list_rules(platform=platform, category=category, severity=severity)

    if not rules:
        console.print("[yellow]No rules found matching the specified filters.[/yellow]")
        return

    severity_colors = {"error": "red", "warning": "yellow", "info": "blue"}

    table = _Table(title="Validation Rules", show_header=True, header_style="bold")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Severity", no_wrap=True)
    table.add_column("Category", no_wrap=True)
    table.add_column("Fixable", no_wrap=True)
    table.add_column("Summary")

    for rule in rules:
        sev_color = severity_colors.get(rule.severity, "white")
        summary = rule.docstring.split("\n")[0].lstrip("#").strip() if rule.docstring else ""
        fixable = "[green]Yes[/green]" if rule.fixable else "No"
        table.add_row(rule.id, f"[{sev_color}]{rule.severity}[/{sev_color}]", rule.category, fixable, summary)

    console.print(table)


def _render_examples_block(rule_id: str) -> str:
    """Return a plain-text block listing fixture examples for rule_id.

    Calls discover_fixtures() to find all FixtureCase objects for the rule,
    then formats them grouped by kind (failing / passing).  Paths are shown
    relative to the tests/ directory (e.g. fixtures/providers/agentskills/…).

    Args:
        rule_id: Rule identifier to look up (e.g. "FM001").

    Returns:
        Formatted string listing fixture examples, or a "No examples yet" note
        if no fixtures exist for the rule.
    """
    cases = _discover_fixtures(rule_id)
    if not cases:
        return "No fixture examples available yet."

    # FIXTURES_ROOT is packages/skilllint/tests/fixtures/providers/
    # parent.parent is packages/skilllint/tests/ — paths shown relative to that
    tests_dir = _FIXTURES_ROOT.parent.parent

    failing = [c for c in cases if c.kind == "failing"]
    passing = [c for c in cases if c.kind == "passing"]

    lines: list[str] = ["### Examples", ""]
    if failing:
        lines.append(f"**Failing examples** (should trigger {rule_id}):")
        for case in failing:
            rel = case.path.relative_to(tests_dir)
            lines.append(f"  - {rel}/")
    if passing:
        if failing:
            lines.append("")
        lines.append(f"**Passing examples** (should not trigger {rule_id}):")
        for case in passing:
            rel = case.path.relative_to(tests_dir)
            lines.append(f"  - {rel}/")
    return "\n".join(lines)


def _resolve_example_markers(docstring: str) -> str:
    """Replace <!-- examples: RULE_ID --> markers in docstring with fixture listings.

    Args:
        docstring: Raw rule docstring that may contain example markers.

    Returns:
        Docstring with every marker replaced by the corresponding fixture block.
    """

    def _replace(match: re.Match[str]) -> str:
        return _render_examples_block(match.group(1).upper())

    return _EXAMPLES_MARKER.sub(_replace, docstring)


def _show_rule_doc(rule_id: str, *, console: _Console) -> None:
    """Show documentation for a single rule (shared logic for callback and rule_cmd)."""
    entry = _get_rule(rule_id)
    if not entry:
        console.print(f"[red]Unknown rule: {rule_id}[/red]")
        console.print("\n[dim]Run [bold]skilllint rules[/bold] to see all available rules.[/dim]")
        raise typer.Exit(1)

    severity_colors = {"error": "red", "warning": "yellow", "info": "blue"}
    sev_color = severity_colors.get(entry.severity, "white")

    console.print()
    console.print(f"[bold]{entry.id}[/bold] — [{sev_color}]{entry.severity}[/{sev_color}]")
    console.print(f"[dim]Category: {entry.category} | Platforms: {', '.join(entry.platforms)}[/dim]")
    console.print()
    resolved_doc = _resolve_example_markers(entry.docstring)
    console.print(_Panel(_Markdown(resolved_doc), title=entry.id, border_style="dim"))


# =============================================================================
# CHECK COMMAND
# =============================================================================


@app.command("check")
def check_cmd(
    ctx: typer.Context,
    paths: Annotated[list[Path] | None, typer.Argument(help="Paths to validate")] = None,
    *,
    check: Annotated[bool, typer.Option("--check", help="Validate only, don't auto-fix")] = False,
    fix: Annotated[bool, typer.Option("--fix", help="Auto-fix issues where possible")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed output")] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
    tokens_only: Annotated[bool, typer.Option("--tokens-only", help="Output token count only")] = False,
    show_progress: Annotated[bool, typer.Option("--show-progress", help="Show per-file status")] = False,
    show_summary: Annotated[bool, typer.Option("--show-summary", help="Show summary panel")] = False,
    filter_glob: Annotated[str | None, typer.Option("--filter", help="Glob pattern")] = None,
    filter_type: Annotated[str | None, typer.Option("--filter-type", help="Filter type")] = None,
    platform: Annotated[str | None, typer.Option("--platform", help="Platform adapter")] = None,
    record: Annotated[Path | None, typer.Option("--record", help="Record terminal output to SVG or HTML file")] = None,
    include_gitignore: Annotated[
        bool,
        typer.Option(
            "--include-gitignore",
            help=("Scan files that are excluded by .gitignore rules. By default, gitignored paths are skipped."),
        ),
    ] = False,
) -> None:
    """Validate Claude Code plugins, skills, agents, and commands."""
    main(
        ctx=ctx,
        paths=paths,
        check=check,
        fix=fix,
        verbose=verbose,
        no_color=no_color,
        tokens_only=tokens_only,
        show_progress=show_progress,
        show_summary=show_summary,
        filter_glob=filter_glob,
        filter_type=filter_type,
        platform=platform,
        record=record,
        include_gitignore=include_gitignore,
    )


# =============================================================================
# RULE DOCUMENTATION COMMANDS
# =============================================================================

from rich.console import Console as _Console
from rich.markdown import Markdown as _Markdown
from rich.panel import Panel as _Panel
from rich.table import Table as _Table

from skilllint.fixture_loader import FIXTURES_ROOT as _FIXTURES_ROOT, discover_fixtures as _discover_fixtures
from skilllint.rule_registry import get_rule as _get_rule, list_rules as _list_rules
from skilllint.rules._constants import RuleCategory, RulePlatform
from skilllint.rules.pa_series import PluginAgentFrontmatterValidator


def _make_rule_console(*, record: bool = False) -> _Console:
    """Return a Rich Console for rules/rule commands.

    Args:
        record: When *True*, return a recording-capable console suitable for
            export to SVG/HTML via :func:`skilllint.record_export.export_recording`.
            When *False* (default), return a plain console.

    Returns:
        A :class:`rich.console.Console` instance.
    """
    if record:
        return _make_recording_console()
    return _Console()


def _maybe_export_recording(console: _Console | None, record: Path | None) -> None:
    if record is not None and console is not None:
        _export_recording(console, record, title=_build_svg_title(sys.argv[1:]))


_EXAMPLES_MARKER = re.compile(r"<!--\s*examples:\s*(\w+)\s*-->", re.IGNORECASE)


@app.command("rule")
def rule_cmd(
    rule_id: str,
    *,
    record: Annotated[Path | None, typer.Option("--record", help="Record terminal output to SVG or HTML file")] = None,
) -> None:
    """Show documentation for a validation rule.

    Args:
        rule_id: Rule identifier (e.g., "FM002", "SK004")
        record: Optional path to write terminal output as SVG or HTML.
    """
    console = _make_rule_console(record=record is not None)
    _show_rule_doc(rule_id, console=console)
    _maybe_export_recording(console, record)


@app.command("rules")
def rules_cmd(
    platform: Annotated[RulePlatform | None, typer.Option("--platform", "-p", help="Filter rules by platform")] = None,
    category: Annotated[RuleCategory | None, typer.Option("--category", "-c", help="Filter rules by category")] = None,
    severity: Annotated[
        Literal["error", "warning", "info"] | None, typer.Option("--severity", "-s", help="Filter rules by severity")
    ] = None,
    *,
    record: Annotated[Path | None, typer.Option("--record", help="Record terminal output to SVG or HTML file")] = None,
) -> None:
    """List all available validation rules."""
    console = _make_rule_console(record=record is not None)
    _show_rules_list(platform=platform, category=category, severity=severity, console=console)
    console.print("\n[dim]Run [bold]skilllint rule [yellow]RULE_ID[/yellow][/bold] for details.[/dim]")
    _maybe_export_recording(console, record)


if __name__ == "__main__":
    # `python -m skilllint.plugin_validator` executes this file as "__main__".
    # Without this alias, the rules package's deferred
    # `from skilllint.plugin_validator import ValidationIssue` would execute the
    # file a *second* time under its real name, producing a distinct
    # ValidationIssue class that ValidationResult then rejects. Registering this
    # module under its real name keeps every issue on one class.
    sys.modules.setdefault("skilllint.plugin_validator", sys.modules["__main__"])
    app()
