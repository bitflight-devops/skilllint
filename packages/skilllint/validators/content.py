"""Read-only content quality and token validators.

These validators parse or measure individual content files and package existing
rule findings into ``ValidationResult``. They do not mutate files, scan plugin
trees, invoke external processes, or own CLI orchestration.
"""

from __future__ import annotations

import re
from pathlib import Path

from ruamel.yaml import YAMLError

from skilllint.file_types import FileType
from skilllint.frontmatter_core import extract_frontmatter
from skilllint.frontmatter_yaml import _safe_load_yaml
from skilllint.models import ValidationIssue, ValidationResult, YamlValue
from skilllint.policy import DEFAULT_THRESHOLDS, ValidationPolicy
from skilllint.rule_registry import rule_reference
from skilllint.rules.sk_series import check_sk004, check_sk005
from skilllint.rules.tc_series import check_tc001
from skilllint.token_counter import TOKEN_ERROR_THRESHOLD, TOKEN_WARNING_THRESHOLD, count_tokens


def _coerce_validation_issues(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    """Normalize issue instances to the canonical shared model class.

    Returns:
        Equivalent issues re-instantiated as ``ValidationIssue``.
    """
    return [ValidationIssue.model_validate(issue.model_dump()) for issue in issues]


class DescriptionValidator:
    """Validate description-field quality for capability frontmatter."""

    def __init__(self, file_type: FileType = FileType.SKILL) -> None:
        """Initialize with the capability file type.

        Args:
            file_type: File type used to scope SK004/SK005 checks.
        """
        self.file_type = file_type

    def validate(self, path: Path) -> ValidationResult:
        """Validate description quality.

        Args:
            path: Path to a frontmatter-bearing file.

        Returns:
            Result containing description-quality warnings or read errors.
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {exc}",
                    code="FM002",
                    docs_url=rule_reference("FM002"),
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
        return ValidationResult(passed=not errors, errors=errors, warnings=warnings, info=info)

    def _check_description_quality(
        self, data: dict[str, YamlValue], description: str, warnings: list[ValidationIssue]
    ) -> None:
        """Append SK004/SK005 warnings for the description.

        Args:
            data: Parsed frontmatter mapping.
            description: Frontmatter description value.
            warnings: Mutable warning sink.
        """
        frontmatter: dict[str, object] = {
            "description": description,
            "disable-model-invocation": data.get("disable-model-invocation"),
        }
        sentinel = Path()
        file_type_str = self.file_type.value
        warnings.extend(_coerce_validation_issues(check_sk004(frontmatter, sentinel, file_type_str)))
        warnings.extend(_coerce_validation_issues(check_sk005(frontmatter, sentinel, file_type_str)))

    def can_fix(self) -> bool:
        """Return False; description quality requires author judgement."""
        return False

    def fix(self, path: Path) -> list[str]:
        """Reject automatic description repair.

        Raises:
            NotImplementedError: Always; description writing is manual.
        """
        raise NotImplementedError(
            "Description validation cannot be auto-fixed. Writing quality descriptions requires human judgment."
        )


class ComplexityValidator:
    """Validate skill body complexity using token thresholds."""

    def validate(self, path: Path, policy: ValidationPolicy | None = None) -> ValidationResult:
        """Validate SKILL.md body complexity.

        Args:
            path: Path to SKILL.md.
            policy: Optional resolved policy for token thresholds.

        Returns:
            Result containing SK006/SK007 findings or read errors.
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        if path.name != "SKILL.md":
            return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {exc}",
                    code="FM002",
                    docs_url=rule_reference("FM002"),
                )
            )
            return ValidationResult(passed=False, errors=errors, warnings=warnings, info=info)

        frontmatter_text, _start_line, _end_line = extract_frontmatter(content)
        if frontmatter_text is not None:
            end_match = re.search(r"\n---\s*\n", content[3:])
            body = content[end_match.end() + 3 :] if end_match else content
        else:
            body = content

        body_tokens = count_tokens(body)
        thresholds = policy.thresholds if policy is not None else DEFAULT_THRESHOLDS
        warning_threshold = thresholds.get("SK006", TOKEN_WARNING_THRESHOLD)
        error_threshold = thresholds.get("SK007", TOKEN_ERROR_THRESHOLD)
        if body_tokens > error_threshold:
            errors.append(
                ValidationIssue(
                    field="complexity",
                    severity="error",
                    message=f"Skill body exceeds token limit ({body_tokens} tokens > {error_threshold} threshold)",
                    code="SK007",
                    docs_url=rule_reference("SK007"),
                    suggestion="Run /plugin-creator:refactor-skill to split into multiple smaller skills",
                )
            )
        elif body_tokens > warning_threshold:
            warnings.append(
                ValidationIssue(
                    field="complexity",
                    severity="warning",
                    message=f"Skill body is large ({body_tokens} tokens > {warning_threshold} threshold)",
                    code="SK006",
                    docs_url=rule_reference("SK006"),
                    suggestion="This skill is larger than Anthropic's official skills. Review whether content can be moved to references/ or if the skill covers multiple domains that could be separated",
                )
            )

        return ValidationResult(passed=not errors, errors=errors, warnings=warnings, info=info)

    def can_fix(self) -> bool:
        """Return False; reducing complexity requires restructuring content."""
        return False

    def fix(self, path: Path) -> list[str]:
        """Reject automatic complexity repair.

        Raises:
            NotImplementedError: Always; restructuring is manual.
        """
        raise NotImplementedError(
            "Complexity validation cannot be auto-fixed. "
            "Reducing complexity requires content restructuring and splitting skills."
        )


class MarkdownTokenCounter:
    """Count tokens for general markdown files without quality thresholds."""

    def validate(self, path: Path) -> ValidationResult:
        """Count tokens and report TC001.

        Args:
            path: Markdown path to measure.

        Returns:
            Passing TC001 result or a read error.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            error = ValidationIssue(
                field="(file)",
                severity="error",
                message=f"Could not read file: {exc}",
                code="FM002",
                docs_url=rule_reference("FM002"),
            )
            return ValidationResult(passed=False, errors=[error], warnings=[], info=[])
        return ValidationResult(passed=True, errors=[], warnings=[], info=check_tc001(content))

    def count_file_tokens(self, path: Path, *, body_only: bool = False) -> int | None:
        """Count tokens in a file for programmatic use.

        Args:
            path: Path to markdown file.
            body_only: Strip frontmatter before counting when True.

        Returns:
            Token count, or None when the file cannot be read.
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
        """Return False; token counting is read-only."""
        return False

    def fix(self, path: Path) -> list[str]:
        """Reject token-count auto-fixing.

        Raises:
            NotImplementedError: Always; token counting is read-only.
        """
        raise NotImplementedError("Token counting is read-only, no fixes to apply.")


__all__ = ["ComplexityValidator", "DescriptionValidator", "MarkdownTokenCounter"]
