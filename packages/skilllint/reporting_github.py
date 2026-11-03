"""GitHub Actions workflow annotations projected from one collected scan."""

from __future__ import annotations

import sys
from collections.abc import Generator
from contextlib import contextmanager, redirect_stderr, suppress
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from skilllint.models import FileResults
    from skilllint.source_location import SourceLocation


@contextmanager
def github_diagnostics() -> Generator[None, None, None]:
    """Keep ordinary stderr diagnostics from becoming runner commands.

    Buffer complete writes so a command split across writes is neutralized too.
    This is only used by the explicit GitHub CLI format, not other formats.

    Yields:
        A scope in which diagnostics are captured before safe emission.
    """
    output = StringIO()
    destination = sys.stderr
    try:
        with redirect_stderr(output):
            yield
    finally:
        # Modern workflow commands and the older runner syntax are both active.
        text = output.getvalue().replace("::", "%3A%3A").replace("##[", "##%5B")
        safe = "".join(
            character if character == "\n" or character.isprintable() else ascii(character)[1:-1] for character in text
        )
        destination.write(safe)
        destination.flush()


def _escape_data(value: str) -> str:
    """Escape workflow data and make other terminal controls visible.

    Returns:
        Safe command data with its percent escapes preserved literally.
    """
    # Match actions/toolkit packages/core/src/command.ts: escape '%' first.
    # https://github.com/actions/toolkit/blob/main/packages/core/src/command.ts
    escaped = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return "".join(character if character.isprintable() else ascii(character)[1:-1] for character in escaped)


def workflow_command(level: Literal["error", "warning", "notice"], properties: dict[str, str], message: str) -> str:
    """Encode one annotation, with the distinct official property/data escapes.

    Returns:
        A single physical command line, without its trailing newline.
    """
    props = ",".join(
        f"{key}={_escape_data(value).replace(':', '%3A').replace(',', '%2C')}" for key, value in properties.items()
    )
    return f"::{level}{' ' + props if props else ''}::{_escape_data(message)}"


def _positions(source: SourceLocation | None) -> dict[str, str]:
    """Project known positions, translating half-open ranges to inclusive ends.

    GitHub ignores column ranges spanning multiple lines. When an exclusive
    end is at the beginning of a later line, that line is outside the range.
    No source text is reread to guess an unknown end column.

    Returns:
        Only coordinates supported by the observed source location.
    """
    if source is None or source.start is None:
        return {}
    start, end = source.start, source.end
    result = {"line": str(start.line)}
    if end is None or end == start:
        return {**result, "col": str(start.column)}
    last_line = end.line - 1 if end.column == 1 and end.line > start.line else end.line
    if last_line > start.line:
        return {**result, "endLine": str(last_line)}
    result["col"] = str(start.column)
    if end.line == start.line:
        result["endColumn"] = str(end.column - 1)
    return result


def github_lines(file_results: FileResults, *, verbose: bool = False) -> list[str]:
    """Return sorted annotations for visible findings without rescanning inputs.

    Returns:
        One command per finding, retaining duplicates. Info becomes notice only
        with verbose enabled. Unknown positions are omitted, never inferred
        from semantic fields or the legacy line number.
    """
    base = Path.cwd()
    lines: list[str] = []
    for target, validator_results in file_results.items():
        for _validator, result in validator_results:
            issues = [*result.errors, *result.warnings, *(result.info if verbose else [])]
            for issue in issues:
                source = issue.source_location
                path = source.path if source is not None else target
                with suppress(ValueError):
                    path = path.relative_to(base)
                properties = {"file": path.as_posix(), **_positions(source), "title": issue.code}
                message = f"{issue.field}: {issue.message}" if issue.field else issue.message
                if issue.suggestion:
                    message += f"\nSuggestion: {issue.suggestion}"
                if issue.docs_url:
                    message += f"\nHelp: {issue.docs_url}"
                level = "notice" if issue.severity == "info" else issue.severity
                lines.append(workflow_command(level, properties, message))
    return sorted(lines)


def emit_github(file_results: FileResults, *, verbose: bool = False) -> None:
    """Write annotations only, with no ANSI, human progress, or summary."""
    for line in github_lines(file_results, verbose=verbose):
        print(line)
