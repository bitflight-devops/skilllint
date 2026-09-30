"""Read-only adapters from rule-series detection into the Validator protocol.

These classes package existing rule functions into ``ValidationResult`` without
owning rule truth, mutation, plugin-tree scanning, subprocess execution, or CLI
orchestration. Keeping them outside ``rules/`` avoids adding policy/frontmatter
dependencies to the eagerly imported rule-registration path.
"""

from __future__ import annotations

from pathlib import Path

from skilllint.frontmatter_yaml import parse_skill_md
from skilllint.models import ValidationIssue, ValidationResult
from skilllint.policy import DEFAULT_THRESHOLDS, ValidationPolicy
from skilllint.rule_registry import rule_reference
from skilllint.rules.as_series import run_as_series
from skilllint.rules.lk_series import check_lk001
from skilllint.rules.nr_series import check_nr001, check_nr002
from skilllint.rules.pd_series import check_pd001, check_pd002, check_pd003
from skilllint.token_counter import TOKEN_ERROR_THRESHOLD, TOKEN_WARNING_THRESHOLD


class ProgressiveDisclosureValidator:
    """Adapt PD-series progressive-disclosure checks to Validator."""

    def validate(self, path: Path) -> ValidationResult:
        """Validate progressive disclosure structure in a skill directory.

        Returns:
            Passing result with PD-series informational findings.
        """
        info = check_pd001(path) + check_pd002(path) + check_pd003(path)
        return ValidationResult(passed=True, errors=[], warnings=[], info=info)

    def can_fix(self) -> bool:
        """Return False; creating content directories requires human decisions."""
        return False

    def fix(self, path: Path) -> list[str]:
        """Reject automatic progressive-disclosure repair."""
        raise NotImplementedError(
            "Progressive disclosure validation cannot be auto-fixed. "
            "Creating directories requires human decisions about content organization."
        )


class InternalLinkValidator:
    """Adapt LK001 internal-link checks to Validator."""

    def validate(self, path: Path) -> ValidationResult:
        """Validate internal markdown links in SKILL.md.

        Returns:
            Result containing LK001 errors or a passing result.
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

        errors.extend(check_lk001(content, path))
        return ValidationResult(passed=not errors, errors=errors, warnings=warnings, info=info)

    def can_fix(self) -> bool:
        """Return False; broken links require content or path decisions."""
        return False

    def fix(self, path: Path) -> list[str]:
        """Reject automatic internal-link repair."""
        raise NotImplementedError(
            "Internal link validation cannot be auto-fixed. "
            "Broken links require creating missing files or correcting link paths manually."
        )


class NamespaceReferenceValidator:
    """Adapt NR-series namespace-reference checks to Validator."""

    def validate(self, path: Path) -> ValidationResult:
        """Validate namespace-qualified references in a plugin file.

        Returns:
            Result containing NR-series errors or a passing result.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors = [
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {exc}",
                    code="NR001",
                    docs_url=rule_reference("NR001"),
                )
            ]
            return ValidationResult(passed=False, errors=errors, warnings=[], info=[])

        errors = check_nr001(content, path) + check_nr002(content, path)
        return ValidationResult(passed=not errors, errors=errors, warnings=[], info=[])

    def can_fix(self) -> bool:
        """Return False; namespace-reference repair requires author intent."""
        return False

    def fix(self, path: Path) -> list[str]:
        """Reject automatic namespace-reference repair."""
        raise NotImplementedError(
            "Namespace reference validation cannot be auto-fixed. "
            "Broken references require creating missing files or correcting "
            "the namespace prefix manually."
        )


class AsSeriesValidator:
    """Adapt AgentSkills AS-series checks to Validator."""

    def validate(self, path: Path, policy: ValidationPolicy | None = None) -> ValidationResult:
        """Run AS-series checks on a skill file using resolved token policy.

        Returns:
            Result grouping AS-series findings by severity.
        """
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
                field=violation.get("code", "unknown"),
                severity=(
                    violation.get("severity", "error")
                    if violation.get("severity", "error") in {"error", "warning", "info"}
                    else "error"
                ),
                message=violation.get("message", ""),
                code=violation["code"],
            )
            for violation in violations
        ]
        errors = [issue for issue in issues if issue.severity == "error"]
        warnings = [issue for issue in issues if issue.severity == "warning"]
        info = [issue for issue in issues if issue.severity == "info"]
        return ValidationResult(passed=not errors, errors=errors, warnings=warnings, info=info)

    def can_fix(self) -> bool:
        """Return False; AS-series adapters do not mutate source files."""
        return False

    def fix(self, path: Path) -> list[str]:
        """Return no fixes for AS-series findings."""
        return []


__all__ = [
    "AsSeriesValidator",
    "InternalLinkValidator",
    "NamespaceReferenceValidator",
    "ProgressiveDisclosureValidator",
]
