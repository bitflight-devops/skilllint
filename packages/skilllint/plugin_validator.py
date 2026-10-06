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
import re
import sys
from dataclasses import dataclass
from enum import StrEnum
from io import StringIO, TextIOWrapper
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Annotated, Literal, NoReturn

import typer
from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError

import skilllint.rules  # ruff: ignore[unused-import] — ensures all 15 series modules register into RULE_REGISTRY
from skilllint.adapters import ALL_RULE_SERIES, PlatformAdapter, load_adapters, matches_file
from skilllint.cli_docs import docs_app
from skilllint.cli_help import CompleteHelpCommand, CompleteHelpGroup
from skilllint.cli_json import JsonOption, emit_and_exit, fail_missing_argument
from skilllint.file_types import (
    NAME_BEARING_FILE_TYPES as _NAME_BEARING_FILE_TYPES,
    FileType,
    FrontmatterRequirement as _FrontmatterRequirement,
    file_has_frontmatter as _file_has_frontmatter,
    frontmatter_requirement as _frontmatter_requirement,
)
from skilllint.fixing import FIXER_TRIGGER_CODES, apply_authorized_fixes, get_fixer_trigger_codes  # noqa: F401
from skilllint.frontmatter_core import (  # noqa: F401 - compatibility re-exports
    FRONTMATTER_EXEMPT_FILENAMES,
    AgentFrontmatter,
    CommandFrontmatter,
    SkillFrontmatter,
    extract_frontmatter,
    fix_skill_name_field,
    get_frontmatter_model,
)
from skilllint.frontmatter_yaml import (  # noqa: F401 - compatibility re-exports
    _dump_tool_list_fixes,
    _dump_yaml,
    _is_losslessly_scalar_tool_list,
    _replace_list_valued_tool_fields,
    _safe_load_yaml,
    parse_skill_md,
    safe_load_yaml_with_colon_fix,
)
from skilllint.models import (
    AppliedFix,
    FileResults,
    ValidationIssue,
    ValidationResult,
    Validator,
    YamlValue,  # noqa: F401 - compatibility re-export
)
from skilllint.output import print_panel, print_table
from skilllint.policy import (  # noqa: F401 - compatibility re-exports
    DEFAULT_THRESHOLDS,
    IgnoreConfig,
    ValidationPolicy,
    _filter_result_by_ignore,
    _is_suppressed,
    _load_ignore_config,
    _load_ignore_dict,
    _load_policy,
    _load_skilllint_config,
    _parse_severity,
    _parse_thresholds,
    _resolve_ignore_config,
    _resolve_policy,
)
from skilllint.responses import (
    build_check_response,
    build_rule_response,
    build_rules_response,
    build_tokens_response,
    build_unknown_rule_response,
    build_version_response,
)
from skilllint.record_export import (
    build_svg_title as _build_svg_title,
    export_recording as _export_recording,
    make_recording_console as _make_recording_console,
)
from skilllint.rule_registry import RULE_REGISTRY, rule_authority, rule_reference
from skilllint.rules.as_series import run_as_series
from skilllint.rules.fm_series import check_fm001, check_fm010
from skilllint.rules.hk_series import _git_file_has_execute_bit  # noqa: F401 - compatibility re-export
from skilllint.scan_runtime import (
    _resolve_filter_and_expand_paths,
    find_marketplace_dir,  # noqa: F401 - compatibility re-export
    find_plugin_dir,  # noqa: F401 - compatibility re-export
    run_validation_loop,
)
from skilllint.token_counter import TOKEN_ERROR_THRESHOLD, TOKEN_WARNING_THRESHOLD
from skilllint.validators.content import ComplexityValidator, DescriptionValidator, MarkdownTokenCounter
from skilllint.validators.frontmatter import (  # noqa: F401 - compatibility re-exports
    NAME_PATTERN,
    FrontmatterValidator,
    NameFormatValidator,
    _build_validation_result,
    _check_agent_tools_and_skills_fields,
    _check_list_valued_tool_fields,
    _check_name_field_format,
    _check_skill_directory_name,
    _coerce_validation_issues,
    _fm009_recovery_warnings,
    _get_pydantic_ctx_val,
    _normalize_skill_name,
    _pydantic_error_to_validation_issue,
    _validate_frontmatter_yaml,
    _validate_skill_directory_name,
    _validation_result_with_error,
)
from skilllint.validators.hooks import HookValidator
from skilllint.validators.metadata import (  # noqa: F401 - compatibility re-exports
    VALIDATOR_CONSTRAINT_SCOPES,
    VALIDATOR_OWNERSHIP,
    ValidatorOwnership,
    filter_validators_by_constraint_scopes,
    get_validator_constraint_scopes,
    get_validator_ownership,
)
from skilllint.validators.plugins import (  # noqa: F401 - compatibility re-exports
    CLAUDE_PLUGIN_MANIFEST,
    CODEX_PLUGIN_MANIFEST,
    LK004_SCOPE_DIRS,
    PluginLinkEscapeValidator,
    PluginRegistrationValidator,
    PluginStructureValidator,
    _git_bash_path,
    _run_claude_plugin_validate,
    _should_skip_claude_validate,
    find_link_scope_plugin_dir,
    is_claude_available,
    validate_with_claude,
)
from skilllint.validators.rule_series import (
    AsSeriesValidator,
    InternalLinkValidator,
    NamespaceReferenceValidator,
    ProgressiveDisclosureValidator,
)
from skilllint.validators.symlinks import SymlinkTargetValidator
from skilllint.version import __version__

if TYPE_CHECKING:
    from collections.abc import Iterable


# Module-level logger for debug output
_logger = logging.getLogger(__name__)

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Platform adapter registry — loaded once at module level.
# Keys are adapter IDs (e.g. "claude_code", "cursor", "codex").
ADAPTERS: dict[str, PlatformAdapter] = {a.id(): a for a in load_adapters()}


def _build_platform_cli_ids(adapter_ids: Iterable[str]) -> dict[str, str]:
    """Map unambiguous CLI display names back to registered adapter IDs.

    Underscore-only IDs retain the established hyphenated CLI spelling when it
    cannot collide with an exact registered ID. Mixed-separator and ambiguous
    IDs are displayed exactly so every advertised choice is selectable.

    Returns:
        Mapping from displayed CLI name to registered adapter ID.
    """
    registered = set(adapter_ids)
    cli_ids: dict[str, str] = {}
    for adapter_id in registered:
        alias = adapter_id.replace("_", "-")
        display = alias if "_" in adapter_id and "-" not in adapter_id and alias not in registered else adapter_id
        cli_ids[display] = adapter_id
    return cli_ids


PLATFORM_CLI_IDS = _build_platform_cli_ids(ADAPTERS)
PLATFORM_CHOICES = ", ".join(sorted(PLATFORM_CLI_IDS))


SKILL_FRONTMATTER_SCHEMA_URL = "https://code.claude.com/docs/en/skills.md#frontmatter-reference"
# PLUGIN_MANIFEST_SCHEMA_URL, MARKETPLACE_MANIFEST_SCHEMA_URL, MARKETPLACE_JSON_ROOT_KEYS and
# MARKETPLACE_METADATA_RELOCATABLE_KEYS are rule data and live in rules/pl_series.py.

# FILTER_TYPE_MAP and DEFAULT_SCAN_PATTERNS live in scan_runtime.py
# and are re-imported at the top of this module.

# Trigger phrase requirements — duplicated from sk_series._REQUIRED_TRIGGER_PHRASES.
# Dead compatibility constant: validators/content.py delegates description checks to SK-series rules.
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

    SK004 = "SK004"  # Description too short (minimum 20 characters)
    SK005 = "SK005"  # Description missing trigger phrases
    SK006 = "SK006"  # Token count exceeds TOKEN_WARNING_THRESHOLD
    SK007 = "SK007"  # Token count exceeds TOKEN_ERROR_THRESHOLD (must split)
    SK008 = "SK008"  # Skill directory name violates naming convention

    # Link (LK001, LK004)
    LK001 = "LK001"  # Broken internal link (file does not exist)
    LK004 = "LK004"  # Link may dangle at runtime when the plugin is installed (info)

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

    PR001 = "PR001"  # Capability exists but not explicitly registered in plugin.json
    PR002 = "PR002"  # Registered capability path does not exist
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
SK004, SK005, SK006, SK007, SK008 = (
    ErrorCode.SK004,
    ErrorCode.SK005,
    ErrorCode.SK006,
    ErrorCode.SK007,
    ErrorCode.SK008,
)
LK001, LK004 = ErrorCode.LK001, ErrorCode.LK004
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
PR001, PR002, PR005 = (ErrorCode.PR001, ErrorCode.PR002, ErrorCode.PR005)
PA001 = ErrorCode.PA001
AG001, AG002, AG003 = ErrorCode.AG001, ErrorCode.AG002, ErrorCode.AG003

# ============================================================================
# VALIDATOR OWNERSHIP
# ============================================================================


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


# ============================================================================
# DATA MODELS
# ============================================================================


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


# ============================================================================
# INTEGRATION LAYER
# ============================================================================


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
# FRONTMATTER REQUIREMENT LOGIC
# ============================================================================


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
        validators.extend((
            PluginStructureValidator(),
            PluginRegistrationValidator(),
            PluginAgentFrontmatterValidator(),
            PluginLinkEscapeValidator(),
        ))
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


def _plugin_error_deduplication_key(issue: ValidationIssue) -> str | tuple[str, str]:
    code = str(issue.code)
    if code == "PL004":
        return code
    message = issue.message
    for prefix in ("Invalid JSON syntax in plugin.json:", "Invalid JSON:"):
        message = message.removeprefix(prefix).strip()
    return code, message


def _without_duplicate_plugin_errors(
    result: ValidationResult, reported_plugin_structure_counts: dict[str | tuple[str, str], int]
) -> ValidationResult:
    remaining_duplicate_counts = reported_plugin_structure_counts.copy()
    errors: list[ValidationIssue] = []
    for issue in result.errors:
        code = str(issue.code)
        duplicate_key = _plugin_error_deduplication_key(issue)
        if code in {"PL002", "PL004"} and remaining_duplicate_counts.get(duplicate_key, 0):
            remaining_duplicate_counts[duplicate_key] -= 1
            continue
        errors.append(issue)
    return ValidationResult(passed=not errors, errors=errors, warnings=result.warnings, info=result.info)


def _collect_validator_results(
    validators: list[Validator],
    path: Path,
    *,
    config_root: Path | None,
    ignore_config: IgnoreConfig,
    policy: ValidationPolicy | None = None,
    raw_codes_out: set[str] | None = None,
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
        raw_codes_out: Optional mutable out-param collecting every issue code
            found *before* ignore filtering. ``--fix`` gating reads this set:
            issue #144's fix policy is "ignore = suppress reporting, not
            fixing", so the fixer gate must see codes ignore filtering would
            otherwise remove.

    Returns:
        List of (validator_class_name, result) tuples.
    """
    results: list[tuple[str, ValidationResult]] = []
    reported_plugin_structure_counts: dict[str | tuple[str, str], int] = {}
    for validator in validators:
        name = type(validator).__name__
        if policy is not None and isinstance(validator, (ComplexityValidator, AsSeriesValidator)):
            result = validator.validate(path, policy)
        else:
            result = validator.validate(path)
        if name == "PluginRegistrationValidator":
            result = _without_duplicate_plugin_errors(result, reported_plugin_structure_counts)
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
        if raw_codes_out is not None:
            raw_codes_out.update(str(i.code) for i in (*result.errors, *result.warnings, *result.info))
        if config_root is not None:
            result = _filter_result_by_ignore(result, path, config_root, ignore_config)
        if name == "PluginStructureValidator":
            for issue in (*result.errors, *result.warnings, *result.info):
                str(issue.code)
                duplicate_key = _plugin_error_deduplication_key(issue)
                reported_plugin_structure_counts[duplicate_key] = (
                    reported_plugin_structure_counts.get(duplicate_key, 0) + 1
                )
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
    fixes_out: list[AppliedFix] | None = None,
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
        fixes_out: Optional mutable append-only out-param collecting one
            AppliedFix per fix description a fixer returned. Only appended
            to when ``fix`` is True and a fixer's declared trigger codes
            (FIXER_TRIGGER_CODES) intersect this path's findings.

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

    # raw_codes carries every issue code found before ignore filtering, so the
    # --fix gate below sees suppressed findings too (ignore = suppress
    # reporting, not fixing -- see the note in the fix loop).
    raw_codes: set[str] = set()
    validator_results = _collect_validator_results(
        validators,
        path,
        config_root=config_root,
        ignore_config=ignore_config,
        policy=policy,
        raw_codes_out=raw_codes if fix else None,
    )

    # Note: --fix still runs even for suppressed issues (ignore = suppress reporting, not fixing)
    if fix:
        # Guard: never auto-fix intentionally broken test fixtures
        if "failing-examples" in path.parts:
            _logger.debug("Skipping auto-fix for fixture file: %s", path)
        else:
            fixes_applied = apply_authorized_fixes(
                _get_fixers_for_path(validators, path), path, raw_codes=raw_codes, fixes_out=fixes_out
            )

            # Re-validate after fixes
            if fixes_applied:
                validator_results = _collect_validator_results(
                    validators, path, config_root=config_root, ignore_config=ignore_config, policy=policy
                )

    return {path: validator_results}


def _count_body_tokens(paths: list[Path]) -> list[tuple[int, Path]]:
    """Count body tokens for each path.

    Token counting always uses body-only (frontmatter stripped) so that the
    numbers match what ComplexityValidator measures against thresholds.

    Args:
        paths: Paths to count tokens for

    Returns:
        ``(token count, normalised path)`` per path, in order. A skill folder is
        normalised to its ``SKILL.md``.

    Raises:
        typer.Exit: Code 2, after a stderr line, when a path does not exist or cannot be counted.
    """
    entries = _count_body_tokens(paths)
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


RULE_SERIES_PREFIX_LENGTH = 2


def _issue_to_violation(issue: ValidationIssue) -> dict:
    """Convert a ValidationIssue to the adapter violation boundary.

    The adapter boundary remains dict-based for compatibility, but every
    diagnostic identity field carried by ValidationIssue is preserved.

    Returns:
        Compatibility violation dictionary retaining diagnostic identity.
    """
    violation = issue.model_dump(exclude_none=True)
    violation["code"] = str(issue.code)
    violation["severity"] = str(issue.severity)
    violation["message"] = str(issue.message)
    authority = rule_authority(str(issue.code))
    if authority is not None:
        violation["authority"] = authority
    return violation


def _violation_applies_to_adapter(violation: dict, adapter: PlatformAdapter) -> bool:
    """Return whether an adapter's routing contract permits a violation.

    applicable_rules() is the coarse series allow-list. Registered core rules
    are additionally narrowed by RuleEntry.platforms: "agentskills" is
    platform-neutral, while a named platform applies only to that adapter.
    Unknown third-party rules have no core metadata, so their adapter series
    declaration is sufficient.
    """
    code = str(violation.get("code", "")).upper()
    if len(code) < RULE_SERIES_PREFIX_LENGTH:
        return False

    declared_series = adapter.applicable_rules()
    if ALL_RULE_SERIES not in declared_series and code[:RULE_SERIES_PREFIX_LENGTH] not in declared_series:
        return False

    entry = RULE_REGISTRY.get(code)
    if entry is None:
        return True

    platform = adapter.id().replace("_", "-")
    return "agentskills" in entry.platforms or platform in entry.platforms


def _filter_platform_violations(violations: list[dict], adapter: PlatformAdapter) -> list[dict]:
    """Apply one authoritative routing contract to adapter and core findings.

    Returns:
        Findings permitted by the selected adapter and rule metadata.
    """
    return [violation for violation in violations if _violation_applies_to_adapter(violation, adapter)]


def run_platform_checks(
    path: Path, adapter: PlatformAdapter, *, policy_cache: dict[str, tuple[ValidationPolicy, Path | None]] | None = None
) -> list[dict]:
    """Run adapter-native and core validation through one routing contract.

    Adapter-native findings and core-pipeline findings are collected first,
    then both pass through the same applicable_rules()/rule-metadata filter.
    AS-series is skipped in the nested core result because validate_file runs
    it once per SKILL.md before adapter dispatch.

    Returns:
        Adapter-native and core findings permitted by the routing contract.
    """
    violations = list(adapter.validate(path))

    if _get_validators_for_path(path):
        file_results = validate_single_path(
            path, check=True, fix=False, verbose=False, per_run_policy_cache=policy_cache
        )
        for validator_results in file_results.values():
            for name, vr_result in validator_results:
                if name == "AsSeriesValidator":
                    continue
                all_issues = [*vr_result.errors, *vr_result.warnings, *vr_result.info]
                violations.extend(_issue_to_violation(issue) for issue in all_issues)

    return _filter_platform_violations(violations, adapter)


def _shared_skill_compatibility_violations(
    path: Path, frontmatter: dict, policy: ValidationPolicy | None
) -> list[dict]:
    """Preserve the omitted-platform no-adapter SKILL.md behavior.

    This is deliberately outside the explicit-platform routing contract.
    validate_file historically reports canonical FM/SK checks even when no
    adapter claims a directly supplied SKILL.md; retaining that library seam
    avoids changing the default/omitted route while explicit adapters consume
    the authoritative declaration-driven core pipeline.

    Returns:
        Legacy FM/SK findings for an otherwise unclaimed SKILL.md.
    """
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
    path: Path, *, compatibility_fallback: bool, policy_cache: dict[str, tuple[ValidationPolicy, Path | None]]
) -> list[dict]:
    """Return once-per-SKILL.md findings before adapter dispatch.

    Returns:
        AS findings plus the legacy no-adapter FM/SK compatibility findings
        when the omitted route has no matching adapter.
    """
    frontmatter_data, body_lines, yaml_err, colon_fields = parse_skill_md(path)
    violations: list[dict] = []

    if yaml_err is not None and compatibility_fallback:
        violations.append({"code": str(FM002), "severity": "error", "message": f"Invalid YAML frontmatter: {yaml_err}"})

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
    if compatibility_fallback:
        violations.extend(_issue_to_violation(issue) for issue in _fm009_recovery_warnings(colon_fields))
        violations.extend(_shared_skill_compatibility_violations(path, frontmatter_data, policy))

    if policy.ignore and policy_root is not None:
        violations = [v for v in violations if not _is_suppressed(policy.ignore, path, policy_root, str(v.get("code")))]

    if not policy.severity:
        return violations
    return [
        {**violation, "severity": configured}
        if (configured := policy.severity.get(str(violation.get("code")))) in {"warning", "info"}
        else violation
        for violation in violations
    ]


def validate_file(
    path: Path,
    adapters: dict,
    platform_override: str | None = None,
    policy_cache: dict[str, tuple[ValidationPolicy, Path | None]] | None = None,
) -> list[dict]:
    """Dispatch explicit-platform validation using adapter routing contracts.

    A SKILL.md runs AS once. Adapter-native and core findings then use the same
    per-adapter declaration and rule metadata, so the runtime cannot emit a
    registered series that the selected adapter does not route.

    Returns:
        Violation dictionaries produced by the selected routing mode.
    """
    resolved_policy_cache: dict[str, tuple[ValidationPolicy, Path | None]] = (
        policy_cache if policy_cache is not None else {}
    )
    pure = PurePath(path)
    if platform_override:
        matching = [adapters[platform_override]]
    else:
        matching = [adapter for adapter in adapters.values() if matches_file(adapter, pure)]

    skill_violations = (
        _skill_md_violations(
            path, compatibility_fallback=platform_override is None and not matching, policy_cache=resolved_policy_cache
        )
        if is_skill_md(path)
        else []
    )
    if not matching:
        return skill_violations

    violations = [
        violation
        for violation in skill_violations
        if any(_violation_applies_to_adapter(violation, adapter) for adapter in matching)
    ]

    for adapter in matching:
        _logger.debug("Validating %s with adapter %s", path, adapter.id())
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
    if platform in ADAPTERS:
        return platform
    platform_key = PLATFORM_CLI_IDS.get(platform)
    if platform_key is None:
        typer.echo(f"Unknown platform: {platform!r}. Valid choices: {PLATFORM_CHOICES}", err=True)
        raise typer.Exit(2) from None
    return platform_key


def violations_to_result(violations: list[dict]) -> ValidationResult:
    """Convert adapter-boundary violations without losing diagnostic identity.

    Returns:
        Structured result retaining supported diagnostic identity fields.
    """
    issues: list[ValidationIssue] = []
    for violation in violations:
        code = str(violation["code"])
        raw_severity = violation.get("severity", "error")
        if raw_severity == "warning":
            severity: Literal["error", "warning", "info"] = "warning"
        elif raw_severity == "info":
            severity = "info"
        else:
            severity = "error"
        line = violation.get("line")
        issues.append(
            ValidationIssue(
                field=str(violation.get("field", code)),
                severity=severity,
                message=str(violation.get("message", "")),
                code=code,
                line=line if isinstance(line, int) else None,
                suggestion=(str(violation["suggestion"]) if violation.get("suggestion") is not None else None),
                docs_url=(str(violation["docs_url"]) if violation.get("docs_url") is not None else None),
            )
        )
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    info = [issue for issue in issues if issue.severity == "info"]
    return ValidationResult(passed=not errors, errors=errors, warnings=warnings, info=info)


def _open_record_console(record: Path | None, *, no_color: bool, json_output: bool) -> _Console | None:
    """Return the console ``--record`` renders into, or ``None`` when no recording was asked for.

    Under ``--json`` the console writes to an in-memory buffer, so the recording is made without
    anything reaching the terminal.

    Args:
        record: The ``--record`` destination, if any.
        no_color: Whether ``--no-color`` was given.
        json_output: Whether ``--json`` was given.

    Returns:
        A recording console, or ``None``.
    """
    if record is None:
        return None
    return _make_recording_console(no_color=no_color, file=StringIO() if json_output else None)


def _export_recording_on_exit(record_console: _Console | None, record: Path | None, *, json_output: bool) -> None:
    """Write the ``--record`` file when a run ends in an exit, as the text path does.

    Args:
        record_console: The recording console, if a recording was asked for.
        record: The ``--record`` destination, if any.
        json_output: Whether ``--json`` was given. A file that cannot be written then exits 2 with
            one plain stderr line instead of a traceback.
    """
    if json_output and record is not None and record_console is not None:
        _export_recording_for_json(record_console, record)
    else:
        _maybe_export_recording(record_console, record)


def _finish_check_json(
    outcome: CheckRun | list[tuple[int, Path]],
    *,
    record: Path | None,
    record_console: _Console | None,
    verbose: bool,
    no_color: bool,
    show_progress: bool,
    show_summary: bool,
) -> NoReturn:
    """End a ``check --json`` run: record the usual rendering when asked, then print the response.

    The ``--record`` file is rendered by the same ``report_results`` the text path calls, with the
    same ``no_color`` and ``show_summary``, and is written before the response names it.

    Args:
        outcome: The scan, or the token counts of ``--tokens-only``.
        record: The ``--record`` destination, if any.
        record_console: The buffer-backed recording console, if a recording was asked for.
        verbose: Whether ``--verbose`` was given.
        no_color: Whether ``--no-color`` was given.
        show_progress: Whether ``--show-progress`` was given.
        show_summary: Whether ``--show-summary`` was given.

    Raises:
        typer.Exit: Always: 0 for a pass, 1 for a failed scan, 2 when the ``--record`` file cannot be written.
    """
    record_path = None
    if record is not None and record_console is not None:
        if isinstance(outcome, CheckRun):
            report_results(
                outcome,
                verbose=verbose,
                no_color=no_color,
                show_progress=show_progress,
                show_summary=show_summary,
                record_console=record_console,
            )
        record_path = _export_recording_for_json(record_console, record)
    if not isinstance(outcome, CheckRun):
        emit_and_exit(build_tokens_response(outcome, record_path=record_path))
    response = build_check_response(
        outcome.results, verbose=verbose, show_progress=show_progress, fixes=outcome.fixes, record_path=record_path
    )
    emit_and_exit(response, code=1 if response.status == "failed" else 0)


def _require_usable_paths(
    ctx: typer.Context, paths: list[Path] | None, *, check: bool, fix: bool, platform: str | None, json_output: bool
) -> list[Path]:
    """Reject the argument combinations ``check`` cannot run, and return the paths.

    On the text path, no paths or a path that does not exist prints the command's help on stdout.
    Under ``--json`` stdout stays empty: the same stderr lines are printed and the help is not.

    Args:
        ctx: The context of the running command.
        paths: The positional paths, if any.
        check: Whether ``--check`` was given.
        fix: Whether ``--fix`` was given.
        platform: The ``--platform`` value, if any.
        json_output: Whether ``--json`` was given.

    Returns:
        The paths, all of which exist.

    Raises:
        typer.Exit: Code 0 for no paths on the text path (after the help), 2 for any other rejection.
    """
    # Show help when no arguments provided
    if not paths:
        if json_output:
            fail_missing_argument(ctx, "paths")
        _show_help_and_exit(ctx, code=0)

    if check and fix:
        typer.echo("Error: Cannot use both --check and --fix flags", err=True)
        raise typer.Exit(2) from None

    if fix and platform:
        typer.echo("Error: Cannot use --fix with --platform", err=True)
        raise typer.Exit(2) from None

    # Validate that all provided paths exist; report non-existent ones
    bad_paths = [str(p) for p in paths if not p.exists()]
    if bad_paths:
        typer.echo(f"Path does not exist: {', '.join(bad_paths)}", err=True)
        typer.echo("", err=True)
        if json_output:
            raise typer.Exit(2) from None
        _show_help_and_exit(ctx, code=2)
    return paths


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
    json_output: bool = False,
) -> None:
    """Validate Claude Code plugins, skills, agents, and commands."""
    # If a subcommand was invoked, don't run validation
    if ctx.invoked_subcommand is not None:
        return

    paths = _require_usable_paths(ctx, paths, check=check, fix=fix, platform=platform, json_output=json_output)

    platform_override = _resolve_platform_override(platform)

    record_console = _open_record_console(record, no_color=no_color, json_output=json_output)

    def _run_validation_command() -> CheckRun | list[tuple[int, Path]] | None:
        expanded_paths, is_batch = _resolve_filter_and_expand_paths(
            paths,
            filter_glob,
            filter_type,
            platform_adapter=ADAPTERS[platform_override] if platform_override is not None else None,
            platform_adapters=tuple(ADAPTERS.values()) if platform_override is not None else None,
        )
        if platform_override is not None:
            expanded_paths = [_normalize_skill_folder(path) for path in expanded_paths]

        if tokens_only:
            if json_output:
                return _count_body_tokens(expanded_paths)
            _handle_tokens_only(expanded_paths, batch=is_batch)

        # One shared cache per scan run — prevents re-walking the directory
        # tree for every file when many files share the same config root.
        per_run_cache: dict[str, tuple[IgnoreConfig, Path | None]] = {}
        per_run_policy_cache: dict[str, tuple[ValidationPolicy, Path | None]] = {}

        def _validate_with_cache(
            p: Path, *, check: bool, fix: bool, verbose: bool, fixes_out: list[AppliedFix] | None = None
        ) -> FileResults:
            return validate_single_path(
                p,
                check=check,
                fix=fix,
                verbose=verbose,
                per_run_cache=per_run_cache,
                per_run_policy_cache=per_run_policy_cache,
                fixes_out=fixes_out,
            )

        if json_output:
            return collect_validation_results(
                expanded_paths=expanded_paths,
                check=check,
                fix=fix,
                verbose=verbose,
                platform_override=platform_override,
                validate_single_path=_validate_with_cache,
                validate_file=lambda p, a, o: validate_file(p, a, o, policy_cache=per_run_policy_cache),
                violations_to_result=violations_to_result,
                adapters=ADAPTERS,
                include_gitignore=include_gitignore,
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
        return None

    try:
        outcome = _run_validation_command()
    except (SystemExit, typer.Exit):
        _export_recording_on_exit(record_console, record, json_output=json_output)
        raise
    except KeyboardInterrupt:
        typer.echo("\nInterrupted by user", err=True)
        raise typer.Exit(130) from None

    # Only a --json run returns here; every other run ends in an exit above.
    if outcome is not None:
        _finish_check_json(
            outcome,
            record=record,
            record_console=record_console,
            verbose=verbose,
            no_color=no_color,
            show_progress=show_progress,
            show_summary=show_summary,
        )


# =============================================================================
# CLI APP SETUP
# =============================================================================

# Create Typer app
app = typer.Typer(
    help="Validate Claude Code plugins and skills",
    add_completion=False,
    cls=CompleteHelpGroup,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)
app.add_typer(docs_app, name="docs")

# Version option handled via callback


@app.callback(invoke_without_command=True)
def _callback(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", "-V", help="Show version and exit", is_eager=True)] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="With --version, print one compact JSON line instead of text.")
    ] = False,
) -> None:
    """Validate Claude Code plugins, skills, agents, and commands."""
    if version:
        if json_output:
            emit_and_exit(build_version_response(__version__))
        print(f"skilllint {__version__}")
        raise typer.Exit
    if json_output:
        # Click does not hand a root option to the subcommand, so it would be a silent no-op here.
        ctx.fail(
            "--json before a command is valid only with --version; give it after the command, e.g. skilllint check PATH --json"
        )
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
        table.add_row(
            _Text(rule.id), f"[{sev_color}]{rule.severity}[/{sev_color}]", _Text(rule.category), fixable, _Text(summary)
        )

    print_table(console, table)


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
    # Markdown's nested list/table renderers can wrap or hide link targets even
    # when the outer console disables cropping. Highlight the complete source
    # instead, retaining every authored line and URL.
    print_panel(console, _Panel(_Syntax(resolved_doc, "markdown", word_wrap=False), title=entry.id, border_style="dim"))


# =============================================================================
# CHECK COMMAND
# =============================================================================


@app.command("check", cls=CompleteHelpCommand)
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
    platform: Annotated[
        str | None, typer.Option("--platform", help=f"Platform adapter. Choices: {PLATFORM_CHOICES}")
    ] = None,
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
from rich.panel import Panel as _Panel
from rich.syntax import Syntax as _Syntax
from rich.table import Table as _Table
from rich.text import Text as _Text

from skilllint.fixture_loader import FIXTURES_ROOT as _FIXTURES_ROOT, discover_fixtures as _discover_fixtures
from skilllint.rule_registry import RuleCategory, RulePlatform, get_rule as _get_rule, list_rules as _list_rules
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
    return _Console(soft_wrap=True)


def _maybe_export_recording(console: _Console | None, record: Path | None) -> None:
    if record is not None and console is not None:
        _export_recording(console, record, title=_build_svg_title(sys.argv[1:]))


_EXAMPLES_MARKER = re.compile(r"<!--\s*examples:\s*(\w+)\s*-->", re.IGNORECASE)


def _show_rules_report(
    platform: str | None = None, category: str | None = None, severity: str | None = None, *, console: _Console
) -> None:
    """Show the rules table and the footer that points at ``skilllint rule`` (rules_cmd and its ``--json`` record)."""
    _show_rules_list(platform=platform, category=category, severity=severity, console=console)
    console.print("\n[dim]Run [bold]skilllint rule [yellow]RULE_ID[/yellow][/bold] for details.[/dim]")


def _rules_json(*, platform: str | None, category: str | None, severity: str | None, record: Path | None) -> NoReturn:
    """Finish ``rules --json``: record the usual rendering into a buffer when asked, then print the response.

    Raises:
        typer.Exit: Always, with code 0, or 2 when the ``--record`` file cannot be written.
    """
    record_path = None
    if record is not None:
        console = _make_recording_console(file=StringIO())
        _show_rules_report(platform=platform, category=category, severity=severity, console=console)
        record_path = _export_recording_for_json(console, record)
    rules = _list_rules(platform=platform, category=category, severity=severity)
    emit_and_exit(build_rules_response(rules, record_path=record_path))


def _rule_json(rule_id: str, record: Path | None) -> NoReturn:
    """Finish ``rule --json``: record the usual rendering into a buffer when asked, then print the response.

    An unknown rule writes no file, as on the text path, so its response has no ``record_path``.

    Raises:
        typer.Exit: Always, with code 0, 1 for an unknown rule, or 2 when the ``--record`` file cannot be written.
    """
    entry = _get_rule(rule_id)
    if entry is None:
        emit_and_exit(build_unknown_rule_response(rule_id), code=1)
    record_path = None
    if record is not None:
        console = _make_recording_console(file=StringIO())
        _show_rule_doc(rule_id, console=console)
        record_path = _export_recording_for_json(console, record)
    documentation = _resolve_example_markers(entry.docstring)
    emit_and_exit(build_rule_response(entry, documentation=documentation, record_path=record_path))


# =============================================================================
# CHECK COMMAND
# =============================================================================


@app.command("check", cls=CompleteHelpCommand)
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
    platform: Annotated[
        str | None, typer.Option("--platform", help=f"Platform adapter. Choices: {PLATFORM_CHOICES}")
    ] = None,
    record: Annotated[Path | None, typer.Option("--record", help="Record terminal output to SVG or HTML file")] = None,
    include_gitignore: Annotated[
        bool,
        typer.Option(
            "--include-gitignore",
            help=("Scan files that are excluded by .gitignore rules. By default, gitignored paths are skipped."),
        ),
    ] = False,
    json_output: JsonOption = False,
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
        json_output=json_output,
    )


# =============================================================================
# RULE DOCUMENTATION COMMANDS
# =============================================================================

from rich.console import Console as _Console
from rich.panel import Panel as _Panel
from rich.syntax import Syntax as _Syntax
from rich.table import Table as _Table
from rich.text import Text as _Text

from skilllint.fixture_loader import FIXTURES_ROOT as _FIXTURES_ROOT, discover_fixtures as _discover_fixtures
from skilllint.rule_registry import RuleCategory, RulePlatform, get_rule as _get_rule, list_rules as _list_rules
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
    return _Console(soft_wrap=True)


def _maybe_export_recording(console: _Console | None, record: Path | None) -> None:
    if record is not None and console is not None:
        _export_recording(console, record, title=_build_svg_title(sys.argv[1:]))


def _export_recording_for_json(console: _Console, record: Path) -> str:
    """Write the ``--record`` file for a ``--json`` run and name it.

    The file is written before any JSON is printed, so a response that names ``record_path`` never
    names a file that is missing.

    Args:
        console: The recording console the command rendered into.
        record: The destination the user gave.

    Returns:
        The absolute, resolved path of the written file.

    Raises:
        typer.Exit: With code 2 and one plain line on stderr when the file cannot be written.
    """
    try:
        _export_recording(console, record, title=_build_svg_title(sys.argv[1:]))
    except (ValueError, OSError) as exc:
        typer.echo(f"Error: Cannot write the recording to {record}: {exc}", err=True)
        raise typer.Exit(2) from None
    return str(record.resolve())


_EXAMPLES_MARKER = re.compile(r"<!--\s*examples:\s*(\w+)\s*-->", re.IGNORECASE)


@app.command("rule", cls=CompleteHelpCommand)
def rule_cmd(
    rule_id: Annotated[str, typer.Argument(help="Rule identifier (e.g., FM002, SK004).")],
    *,
    record: Annotated[Path | None, typer.Option("--record", help="Record terminal output to SVG or HTML file")] = None,
    json_output: JsonOption = False,
) -> None:
    """Show documentation for a validation rule."""
    if json_output:
        _rule_json(rule_id, record)
    console = _make_rule_console(record=record is not None)
    _show_rule_doc(rule_id, console=console)
    _maybe_export_recording(console, record)


@app.command("rules", cls=CompleteHelpCommand)
def rules_cmd(
    platform: Annotated[RulePlatform | None, typer.Option("--platform", "-p", help="Filter rules by platform")] = None,
    category: Annotated[RuleCategory | None, typer.Option("--category", "-c", help="Filter rules by category")] = None,
    severity: Annotated[
        Literal["error", "warning", "info"] | None, typer.Option("--severity", "-s", help="Filter rules by severity")
    ] = None,
    *,
    record: Annotated[Path | None, typer.Option("--record", help="Record terminal output to SVG or HTML file")] = None,
    json_output: JsonOption = False,
) -> None:
    """List all available validation rules."""
    if json_output:
        _rules_json(platform=platform, category=category, severity=severity, record=record)
    console = _make_rule_console(record=record is not None)
    _show_rules_report(platform=platform, category=category, severity=severity, console=console)
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
