"""Validator protocol adapters grouped by implementation responsibility."""

from __future__ import annotations

from skilllint.validators.content import ComplexityValidator, DescriptionValidator, MarkdownTokenCounter
from skilllint.validators.hooks import HookValidator
from skilllint.validators.rule_series import (
    AsSeriesValidator,
    InternalLinkValidator,
    NamespaceReferenceValidator,
    ProgressiveDisclosureValidator,
)
from skilllint.validators.symlinks import SymlinkTargetValidator

__all__ = [
    "AsSeriesValidator",
    "ComplexityValidator",
    "DescriptionValidator",
    "HookValidator",
    "InternalLinkValidator",
    "MarkdownTokenCounter",
    "NamespaceReferenceValidator",
    "ProgressiveDisclosureValidator",
    "SymlinkTargetValidator",
]
