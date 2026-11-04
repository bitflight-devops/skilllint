"""Versioned, one-finding-per-line output for agent consumers.

This projection reads collected results only. It does not run validators, infer
source positions from legacy field labels, or change the legacy JSON response.
"""

from __future__ import annotations

import json
import os
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from skilllint.source_location import SourcePosition

if TYPE_CHECKING:
    from skilllint.models import FileResults


class JsonLinesLocation(BaseModel):
    """Actual source identity with portable paths and optional original positions."""

    model_config = ConfigDict(frozen=True)

    path: str
    start: SourcePosition | None = None
    end: SourcePosition | None = None


class JsonLinesFinding(BaseModel):
    """Schema version 1 of a standalone finding record.

    ``path`` identifies the checked target. An optional ``source_location``
    identifies the actual source, which can differ for aggregate validators.
    Absolute paths beneath the invocation directory are made relative to it.
    Other spellings retain their identity, including symlinks and ``..``.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: Literal[1] = 1
    path: str
    validator: str
    code: str
    severity: Literal["error", "warning", "info"]
    message: str
    field: str
    source_location: JsonLinesLocation | None = None
    suggestion: str | None = None
    docs_url: str | None = None


def _relative_path(path: Path, base: Path) -> str:
    """Return a portable spelling without resolving symlinks or requiring existence."""
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        # Preserve already-relative paths and absolute paths outside the cwd.
        # Normalizing '..' could change the source identity across a symlink.
        return path.as_posix()


def json_lines_records(file_results: FileResults, *, verbose: bool = False) -> list[str]:
    """Project visible findings into deterministically ordered JSON lines.

    Optional metadata is omitted, not guessed. Escaping non-ASCII code points
    also escapes Unicode line separators so every record occupies one physical
    line even in viewers that recognize more separators than LF.

    Returns:
        Compact JSON records, without their trailing LF. Identical findings
        remain separate records; this function does not deduplicate findings.
    """
    base = Path.cwd()
    records: list[str] = []
    for path, validator_results in file_results.items():
        for validator, result in validator_results:
            issues = [*result.errors, *result.warnings, *(result.info if verbose else [])]
            for issue in issues:
                source = issue.source_location
                location = (
                    JsonLinesLocation(path=_relative_path(source.path, base), start=source.start, end=source.end)
                    if source is not None
                    else None
                )
                finding = JsonLinesFinding(
                    path=_relative_path(path, base),
                    validator=validator,
                    code=issue.code,
                    severity=issue.severity,
                    message=issue.message,
                    field=issue.field,
                    source_location=location,
                    suggestion=issue.suggestion,
                    docs_url=issue.docs_url,
                )
                # The stdlib preserves lone surrogates from POSIX filenames;
                # Pydantic's direct JSON encoder rejects them even in ASCII mode.
                records.append(
                    json.dumps(finding.model_dump(exclude_none=True), ensure_ascii=True, separators=(",", ":"))
                )
    return sorted(records)


def emit_json_lines(file_results: FileResults, *, verbose: bool = False) -> None:
    """Write UTF-8 findings, retaining native newlines and text-only redirects."""
    records = json_lines_records(file_results, verbose=verbose)
    stream = sys.stdout
    if isinstance(stream, TextIOWrapper):
        # Bypass arbitrary text encodings without reconfiguring the caller's
        # stream. Flush any existing text before writing its binary buffer.
        stream.flush()
        for record in records:
            stream.buffer.write((record + os.linesep).encode("utf-8"))
        stream.buffer.flush()
    else:
        # StringIO and other text-only redirects have no byte encoding.
        for record in records:
            stream.write(record + "\n")
        stream.flush()
