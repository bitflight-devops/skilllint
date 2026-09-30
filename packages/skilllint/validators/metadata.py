"""Dependency-light validator ownership and applicability metadata."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from skilllint.models import Validator


class ValidatorOwnership(StrEnum):
    """Ownership classification for validators."""

    SCHEMA = "schema"
    LINT = "lint"


VALIDATOR_OWNERSHIP: dict[str, ValidatorOwnership] = {
    "FrontmatterValidator": ValidatorOwnership.SCHEMA,
    "PluginStructureValidator": ValidatorOwnership.SCHEMA,
    "PluginRegistrationValidator": ValidatorOwnership.SCHEMA,
    "HookValidator": ValidatorOwnership.SCHEMA,
    "SymlinkTargetValidator": ValidatorOwnership.SCHEMA,
    "NameFormatValidator": ValidatorOwnership.LINT,
    "DescriptionValidator": ValidatorOwnership.LINT,
    "ComplexityValidator": ValidatorOwnership.LINT,
    "InternalLinkValidator": ValidatorOwnership.LINT,
    "ProgressiveDisclosureValidator": ValidatorOwnership.LINT,
    "NamespaceReferenceValidator": ValidatorOwnership.LINT,
    "MarkdownTokenCounter": ValidatorOwnership.LINT,
    "AsSeriesValidator": ValidatorOwnership.LINT,
}

VALIDATOR_CONSTRAINT_SCOPES: dict[str, set[str]] = {
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


def get_validator_ownership(validator: Validator) -> ValidatorOwnership:
    """Return schema/lint ownership for a validator, defaulting to lint."""
    return VALIDATOR_OWNERSHIP.get(type(validator).__name__, ValidatorOwnership.LINT)


def get_validator_constraint_scopes(class_name: str) -> set[str]:
    """Return provider constraint scopes for a validator class name."""
    return VALIDATOR_CONSTRAINT_SCOPES.get(class_name, {"shared", "provider_specific"})


def filter_validators_by_constraint_scopes(
    validators: Sequence[Validator], constraint_scopes: set[str]
) -> list[Validator]:
    """Return validators whose declared scopes intersect the provider scopes."""
    filtered: list[Validator] = []
    for validator in validators:
        validator_scopes = get_validator_constraint_scopes(type(validator).__name__)
        if validator_scopes & constraint_scopes:
            filtered.append(validator)
    return filtered


__all__ = [
    "VALIDATOR_CONSTRAINT_SCOPES",
    "VALIDATOR_OWNERSHIP",
    "ValidatorOwnership",
    "filter_validators_by_constraint_scopes",
    "get_validator_constraint_scopes",
    "get_validator_ownership",
]
