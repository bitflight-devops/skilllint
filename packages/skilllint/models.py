"""Dependency-light validation contracts shared across skilllint subsystems.

The legacy ``skilllint.plugin_validator`` module re-exports these names for
compatibility while callers migrate to this owner module.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, Protocol, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class ValidationIssue(BaseModel):
    """A single validation issue."""

    model_config = ConfigDict(frozen=True)

    field: str
    severity: Literal["error", "warning", "info"]
    message: str
    code: Annotated[str, Field(pattern=r"^[A-Z]{2}\\d{3}$")]
    line: int | None = None
    suggestion: str | None = None
    docs_url: str | None = None

    def format(self) -> str:
        """Format issue for display.

        Returns:
            Formatted string with severity icon, code, field, message, and optional docs URL.
        """
        severity_icon = {"error": ":cross_mark:", "warning": ":warning:", "info": ":information:"}[self.severity]
        location = f":{self.line}" if self.line else ""
        suggestion_line = f"\\n    → {self.suggestion}" if self.suggestion else ""
        docs = f"\\n    → {self.docs_url}" if self.docs_url else ""
        return f"  {severity_icon} [{self.code}] {self.field}{location}: {self.message}{suggestion_line}{docs}"


class ValidationResult(BaseModel):
    """Result from a validation check."""

    model_config = ConfigDict(frozen=True)

    passed: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    info: list[ValidationIssue]


FileResults: TypeAlias = dict[Path, list[tuple[str, ValidationResult]]]


@dataclass(frozen=True)
class AppliedFix:
    """Record of one fix a validator applied to a file under --fix."""

    path: Path
    validator: str
    codes: tuple[str, ...]
    description: str


class Validator(Protocol):
    """Structural contract implemented by validators."""

    def validate(self, path: Path) -> ValidationResult:
        """Run validation on path."""
        ...

    def can_fix(self) -> bool:
        """Return whether this validator supports auto-fixing."""
        ...

    def fix(self, path: Path) -> list[str]:
        """Apply supported fixes and return human-readable descriptions."""
        ...


__all__ = ["AppliedFix", "FileResults", "ValidationIssue", "ValidationResult", "Validator"]
