"""Validation policy, configuration discovery, and suppression contracts.

This module owns the lint policy boundary: loading/discovering config,
threshold and severity overrides, suppression matching, and policy caching.
The legacy ``skilllint.plugin_validator`` module re-exports these names for
compatibility while #283 decomposes the central validator.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

import msgspec.json

from skilllint.models import ValidationIssue, ValidationResult
from skilllint.token_counter import TOKEN_ERROR_THRESHOLD, TOKEN_WARNING_THRESHOLD

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
# Severity may be reconfigured for the token-band rules (SK006/SK007) and for
# PL006's marketplace.json root-key check (see issue #145). AS005 shared this
# band and was listed here until it was retired into SK006/SK007.
_SEVERITY_POLICY_RULES = frozenset({"PL006", "SK006", "SK007"})
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
    cached, walks up from ``path`` itself when *path* is already a directory
    (e.g. a plugin root passed directly by ``FileType.PLUGIN`` validation) or
    from ``path.parent`` when *path* is a file, looking for:

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
    start_dir = (path if path.is_dir() else path.parent).resolve()
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
    1000-file scan warns once, not once per file. Walks up from ``path``
    itself when *path* is already a directory (a plugin root passed directly
    by ``FileType.PLUGIN`` validation), or from ``path.parent`` when *path*
    is a file -- see ``_resolve_ignore_config`` for the identical rationale.

    Returns:
        The policy and its config root, or defaults and ``None``.
    """
    start_dir = (path if path.is_dir() else path.parent).resolve()
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
        print(f"Warning: {message}", file=sys.stderr)
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
        rel = file_path.resolve().relative_to(config_root.resolve())
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
