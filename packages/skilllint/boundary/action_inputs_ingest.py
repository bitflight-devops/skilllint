"""Validate composite Action environment inputs before orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter

_STRING = TypeAdapter(str, config=ConfigDict(strict=True))


def _boolean(value: object) -> bool:
    """Preserve the Action's exact, case-sensitive boolean convention.

    Returns:
        Whether the external string is exactly ``true``.
    """
    return _STRING.validate_python(value) == "true"


def _paths(value: object) -> list[Path]:
    """Preserve whitespace splitting without shell expansion or quoting.

    Returns:
        Paths selected by the external whitespace-separated string.
    """
    return [Path(path) for path in _STRING.validate_python(value).split()]


def _optional_string(value: object) -> str | None:
    """Preserve empty strings as absent options without trimming content.

    Returns:
        The supplied string, or None when it is empty.
    """
    return _STRING.validate_python(value) or None


class ActionInputs(BaseModel):
    """Concrete check inputs with defaults matching the composite Action."""

    model_config = ConfigDict(strict=True, frozen=True)

    paths: Annotated[list[Path], BeforeValidator(_paths)] = Field(default_factory=lambda: [Path()], alias="INPUT_PATHS")
    check_only: Annotated[bool, BeforeValidator(_boolean)] = Field(default=False, alias="INPUT_CHECK_ONLY")
    fix: Annotated[bool, BeforeValidator(_boolean)] = Field(default=False, alias="INPUT_FIX")
    verbose: Annotated[bool, BeforeValidator(_boolean)] = Field(default=False, alias="INPUT_VERBOSE")
    no_color: Annotated[bool, BeforeValidator(_boolean)] = Field(default=True, alias="INPUT_NO_COLOR")
    tokens_only: Annotated[bool, BeforeValidator(_boolean)] = Field(default=False, alias="INPUT_TOKENS_ONLY")
    show_progress: Annotated[bool, BeforeValidator(_boolean)] = Field(default=False, alias="INPUT_SHOW_PROGRESS")
    show_summary: Annotated[bool, BeforeValidator(_boolean)] = Field(default=True, alias="INPUT_SHOW_SUMMARY")
    platform: Annotated[str | None, BeforeValidator(_optional_string)] = Field(default=None, alias="INPUT_PLATFORM")
    filter_glob: Annotated[str | None, BeforeValidator(_optional_string)] = Field(default=None, alias="INPUT_FILTER")
    filter_type: Annotated[str | None, BeforeValidator(_optional_string)] = Field(
        default=None, alias="INPUT_FILTER_TYPE"
    )


def parse_action_inputs(environment: Mapping[str, str]) -> ActionInputs:
    """Validate the Action environment and ignore unrelated environment keys.

    Returns:
        Typed inputs ready for check orchestration.
    """
    return ActionInputs.model_validate(dict(environment))
