"""Frontmatter schema validation, normalization, and name repair.

This module owns the Validator-protocol implementations and helper logic that
validate or mutate capability frontmatter. Rule detection remains in ``rules/``;
YAML syntax/round-trip primitives remain in ``frontmatter_yaml``; schema models
remain in ``frontmatter_core``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

from pydantic import ValidationError
from ruamel.yaml import YAMLError

from skilllint.file_types import FileType
from skilllint.frontmatter_core import (
    AgentFrontmatter,
    CommandFrontmatter,
    SkillFrontmatter,
    extract_frontmatter,
    fix_skill_name_field,
    get_frontmatter_model,
)
from skilllint.frontmatter_yaml import (
    _dump_tool_list_fixes,
    _dump_yaml,
    _is_losslessly_scalar_tool_list,
    _replace_list_valued_tool_fields,
    _safe_load_yaml,
    safe_load_yaml_with_colon_fix,
)
from skilllint.models import ValidationIssue, ValidationResult, YamlValue
from skilllint.rule_registry import rule_reference
from skilllint.rules.ag_series import check_ag001, check_ag002, check_ag003
from skilllint.rules.fm_series import check_fm004, check_fm007, check_fm010
from skilllint.validators.hooks import HookValidator

if TYPE_CHECKING:
    from pydantic_core import ErrorDetails

# Local rule identifiers. The legacy ErrorCode enum remains a compatibility
# surface in plugin_validator; this owner depends on the canonical rule IDs.
FM001 = "FM001"
FM002 = "FM002"
FM003 = "FM003"
FM004 = "FM004"
FM005 = "FM005"
FM006 = "FM006"
FM007 = "FM007"
FM009 = "FM009"
FM010 = "FM010"
SK008 = "SK008"

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
    elif error.get("type") == "literal_error":
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
        field=field, severity=severity, message=msg, code=code, docs_url=rule_reference(code), suggestion=suggestion
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
                    docs_url=rule_reference(SK008),
                    suggestion=issue_suggestion,
                )
            )


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
            docs_url=rule_reference(FM009),
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
                docs_url=rule_reference(FM002),
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
                docs_url=rule_reference(FM002),
            ),
        )
        return None, result

    return data, None


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
                    docs_url=rule_reference(FM002),
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
                    docs_url=rule_reference(FM003),
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
                    docs_url=rule_reference(FM009),
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
            original_value = original_data.get(field_name)
            if isinstance(original_value, list) and _is_losslessly_scalar_tool_list(original_value):
                normalized_dict[field_name] = ", ".join(str(x) for x in original_value if x is not None)
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
        content: str,
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
        for field_name in ("tools", "disallowedTools", "allowed-tools"):
            original_value = original_data.get(field_name)
            if isinstance(original_value, list) and not _is_losslessly_scalar_tool_list(original_value):
                normalized_dict[field_name] = original_value
        if not fixes:
            return None
        tool_list_fixes = {
            f"Converted {field_name} from YAML array to comma-separated string"
            for field_name in ("tools", "disallowedTools", "allowed-tools")
            if isinstance(original_data.get(field_name), list)
            and _is_losslessly_scalar_tool_list(original_data[field_name])
        }
        tool_values = {
            field_name: value
            for field_name, value in normalized_dict.items()
            if field_name in {"tools", "disallowedTools", "allowed-tools"}
            and isinstance(original_data.get(field_name), list)
            and _is_losslessly_scalar_tool_list(original_data[field_name])
            and isinstance(value, str)
        }
        if set(fixes) == tool_list_fixes:
            rewritten_frontmatter = _replace_list_valued_tool_fields(frontmatter_text, original_data)
            if rewritten_frontmatter is not None:
                return content.replace(frontmatter_text, rewritten_frontmatter, 1), fixes
        if len(tool_values) == len(fixes):
            yaml = _dump_tool_list_fixes(frontmatter_text, tool_values)
            if yaml is not None:
                return f"---\n{yaml}---\n{body}", fixes
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
                content,
                original_data,
                frontmatter_text,
                body,
                file_type=file_type,
                file_path=file_path,
                colon_fixes=colon_fixes,
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
                    docs_url=rule_reference(FM002),
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


__all__ = [
    "NAME_PATTERN",
    "FrontmatterValidator",
    "NameFormatValidator",
    "_build_validation_result",
    "_check_agent_tools_and_skills_fields",
    "_check_list_valued_tool_fields",
    "_check_name_field_format",
    "_check_skill_directory_name",
    "_coerce_validation_issues",
    "_fm009_recovery_warnings",
    "_get_pydantic_ctx_val",
    "_normalize_skill_name",
    "_pydantic_error_to_validation_issue",
    "_validate_frontmatter_yaml",
    "_validate_skill_directory_name",
    "_validation_result_with_error",
]
