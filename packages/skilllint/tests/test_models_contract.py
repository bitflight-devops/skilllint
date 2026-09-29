from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

import skilllint.plugin_validator as legacy
from skilllint.models import AppliedFix, ValidationIssue, ValidationResult, Validator, YamlValue

ROOT = Path(__file__).parents[3]


def test_legacy_module_reexports_validation_contracts_by_identity() -> None:
    assert legacy.ValidationIssue is ValidationIssue
    assert legacy.ValidationResult is ValidationResult
    assert legacy.AppliedFix is AppliedFix
    assert legacy.Validator is Validator
    assert legacy.YamlValue is YamlValue


def test_validation_issue_behavior_is_preserved_after_extraction() -> None:
    issue = ValidationIssue(
        field="description",
        severity="warning",
        message="example",
        code="SK004",
        suggestion="expand it",
        docs_url="skilllint rule SK004",
    )

    rendered = issue.format()
    assert "[SK004]" in rendered
    assert "\n    → expand it" in rendered
    assert "\n    → skilllint rule SK004" in rendered

    with pytest.raises(ValidationError):
        ValidationIssue(field="x", severity="error", message="bad", code="invalid")


def test_rule_and_reporting_modules_do_not_source_shared_contracts_from_legacy_module() -> None:
    paths = [
        ROOT / "packages/skilllint/rule_registry.py",
        ROOT / "packages/skilllint/reporting.py",
        ROOT / "packages/skilllint/scan_runtime.py",
        *sorted((ROOT / "packages/skilllint/rules").glob("*.py")),
    ]
    forbidden = (
        "plugin_validator import AppliedFix",
        "plugin_validator import ValidationIssue",
        "plugin_validator import ValidationResult",
        "plugin_validator import YamlValue",
    )

    for path in paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source, f"{path.relative_to(ROOT)} still imports {token!r}"
