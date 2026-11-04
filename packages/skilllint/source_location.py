"""Source identity and coordinates for diagnostic consumers.

Coordinates count Unicode code points, not UTF-8 bytes or display cells. Lines
and columns are one-based, tabs count as one character, and range ends are
exclusive. A path without a start is a file-level finding, not line one.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.json_schema import SkipJsonSchema


def source_digest(content: str) -> str:
    """Return an identity for decoded source, treating CRLF like text-mode reads."""
    return sha256(content.replace("\r\n", "\n").encode("utf-8")).hexdigest()


class SourcePosition(BaseModel):
    """A one-based position in decoded source text."""

    model_config = ConfigDict(frozen=True)

    line: Annotated[int, Field(strict=True, ge=1)]
    column: Annotated[int, Field(strict=True, ge=1)]

    @classmethod
    def from_offset(cls, content: str, offset: int) -> Self:
        """Convert a Python string offset, including EOF, into a source position.

        Returns:
            Position counting LF and CRLF as a single line ending.

        Raises:
            ValueError: If the offset falls outside the source text.
        """
        if not 0 <= offset <= len(content):
            raise ValueError("Source offset must be within the source text")
        return cls(line=content.count("\n", 0, offset) + 1, column=offset - content.rfind("\n", 0, offset))


class SourceLocation(BaseModel):
    """Actual source path with an optional point or half-open range.

    Paths retain the producer's identity. Reporters, not rules, choose how to
    display or relativize them. An unknown source has no SourceLocation at all;
    a known file with unknown coordinates has neither start nor end.
    """

    model_config = ConfigDict(frozen=True)

    path: Path
    start: SourcePosition | None = None
    end: SourcePosition | None = None
    content_digest: SkipJsonSchema[str | None] = Field(default=None, exclude=True, repr=False)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        """Reject an end without a start or a backwards range.

        Returns:
            This validated location.

        Raises:
            ValueError: If the range cannot describe a source span.
        """
        if self.end is not None:
            if self.start is None:
                raise ValueError("Source range end requires a start")
            if (self.end.line, self.end.column) < (self.start.line, self.start.column):
                raise ValueError("Source range end must not precede its start")
        return self

    @classmethod
    def from_offsets(cls, path: Path, content: str, start: int, end: int, *, digest: str | None = None) -> Self:
        """Return a location for an observed span in decoded source text."""
        return cls(
            path=path,
            start=SourcePosition.from_offset(content, start),
            end=SourcePosition.from_offset(content, end),
            content_digest=source_digest(content) if digest is None else digest,
        )
