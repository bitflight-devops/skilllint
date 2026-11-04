"""Source-aware human diagnostics, independent of the legacy report layout."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import regex
from rich.cells import cell_len
from rich.console import Console
from rich.text import Text

from skilllint.reporting import _single_line
from skilllint.source_location import source_digest

if TYPE_CHECKING:
    from typing import TextIO

    from skilllint.models import AppliedFix, FileResults, ValidationIssue
    from skilllint.source_location import SourceLocation

ColorMode = Literal["auto", "always", "never"]
_SourceCache = dict[tuple[Path, str], list[str] | None]
_COLORS = {"error": "bold red", "warning": "bold yellow", "info": "bold blue"}


def human_console(
    *, color: ColorMode = "auto", no_color: bool = False, record: bool = False, file: TextIO | None = None
) -> Console:
    """Build a terminal-aware console; explicit no-color always wins.

    Returns:
        Console with automatic detection or the requested explicit colour mode.
    """
    if no_color:
        color = "never"
    return Console(
        file=file,
        record=record,
        force_terminal=None if color == "auto" else color == "always",
        no_color=None if color == "auto" else color == "never",
        color_system="standard" if color == "always" else "auto",
        emoji=False,
        markup=True,
        highlight=False,
    )


def _path(path: Path) -> str:
    """Return a literal display path without resolving source identities."""
    with suppress(ValueError):
        path = path.relative_to(Path.cwd())
    return _single_line(path.as_posix())


def _verified_lines(source: SourceLocation, cache: _SourceCache) -> list[str] | None:
    """Read only source whose content still matches the producer's evidence.

    Returns:
        LF-delimited source lines, or None for unavailable/untrusted spans.
    """
    if source.start is None or source.content_digest is None:
        return None
    identity = (source.path, source.content_digest)
    if identity not in cache:
        try:
            content = source.path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            cache[identity] = None
        else:
            # Coordinates count LF only, not splitlines()'s Unicode separators.
            cache[identity] = content.split("\n") if source_digest(content) == source.content_digest else None
    lines = cache[identity]
    if lines is None:
        return None
    for position in (source.start, source.end):
        if position is not None and (position.line > len(lines) or position.column > len(lines[position.line - 1]) + 1):
            return None
    return lines


def _display_tokens(line: str, start: int, end: int, *, tab_size: int) -> tuple[list[str], int, int]:
    """Expand tabs and controls without splitting Unicode grapheme clusters.

    Returns:
        Safe display clusters plus the containing start and end cluster indices.
        A coordinate inside a combining sequence highlights the whole glyph.
    """
    tokens: list[str] = []
    column = 0
    first = 0
    last = 0
    for match in regex.finditer(r"\X", line):
        cluster = match.group()
        token = " " * (tab_size - column % tab_size) if cluster == "\t" else _single_line(cluster)
        # An orphan combining mark has no own terminal cell and could attach
        # to the gutter or make its caret point at the following glyph.
        if not cell_len(token):
            token = "".join(ascii(character)[1:-1] for character in cluster)
        tokens.append(token)
        column += cell_len(token)
        if match.end() <= start:
            first += 1
        if match.start() < end:
            last += 1
    return tokens, first, last


def _excerpt_line(line: str, start: int, end: int, *, width: int, tab_size: int) -> tuple[str, int, int] | None:
    """Fit genuine source around its highlight using display-cell widths.

    Returns:
        Visible source, marker indentation/count; None if the selected character
        cannot fit. A point at EOF reserves its own cell, never the last glyph.
    """
    tokens, start, end = _display_tokens(line, start, end, tab_size=tab_size)
    widths = [cell_len(token) for token in tokens]
    before = sum(widths[:start])
    selected = max(1, sum(widths[start:end]))
    total = sum(widths)
    left = 0
    removed = 0
    # Centre the start in the available row when the original line does not fit.
    # This is a viewport calculation, not a content-length limit.
    while left < start and total - removed >= width and before - removed > width // 2:
        removed += widths[left]
        left += 1
    while True:
        prefix = "…" if left else ""
        right = left
        used = 0
        while right < len(tokens):
            # Keep a cell for either an omission marker or an EOF caret.
            if used + widths[right] + int(right + 1 < len(tokens) or start == len(tokens)) > width - cell_len(prefix):
                break
            used += widths[right]
            right += 1
        indent = cell_len(prefix) + before - removed
        if (right > start or start == len(tokens) == right) and indent < width:
            break
        if left >= start:
            return None
        removed += widths[left]
        left += 1
    visible = prefix + "".join(tokens[left:right]) + ("…" if right < len(tokens) else "")
    count = min(selected, max(1, cell_len(prefix) + used - indent))
    return visible, indent, count


class FullReporter:
    """Ruff-style issue blocks with verified excerpts and a safe file fallback."""

    def __init__(self, console: Console) -> None:
        self.console = console

    def _excerpt(self, source: SourceLocation, lines: list[str], color: str) -> None:
        """Render range boundaries with display-cell aligned caret markers."""
        start = source.start
        if start is None:
            return
        end = source.end or start
        last = end.line - 1 if end.line > start.line and end.column == 1 else end.line
        numbers = [start.line] if last == start.line else [start.line, last]
        gutter = len(str(last))
        # A gutter plus ellipses and at least one source cell must fit. On a
        # smaller terminal, keep the complete path/message but omit the excerpt.
        width = self.console.width - gutter - len(" | ")
        if width < len("…x…"):
            return
        self.console.print(Text(" " * gutter + " |", style="blue"))
        for index, number in enumerate(numbers):
            if index and number > start.line + 1:
                self.console.print(Text(" " * gutter + " | …", style="dim"))
            line = lines[number - 1]
            first_column = start.column - 1 if number == start.line else 0
            last_column = end.column - 1 if number == end.line else len(line)
            excerpt = _excerpt_line(line, first_column, last_column, width=width, tab_size=self.console.tab_size)
            if excerpt is None:
                continue
            visible, indent, count = excerpt
            row = Text(f"{number:>{gutter}} | ", style="blue")
            row.append(visible, style="default")
            self.console.print(row, soft_wrap=True)
            marker = Text(" " * gutter + " | ", style="blue")
            marker.append(" " * indent + "^" * count, style=color)
            self.console.print(marker, soft_wrap=True)
        self.console.print(Text(" " * gutter + " |", style="blue"))

    def _issue(self, target: Path, issue: ValidationIssue, sources: _SourceCache) -> None:
        """Print literal diagnostic data and only verified source highlighting."""
        color = _COLORS[issue.severity]
        title = Text(f"{issue.severity}[{issue.code}]", style=color)
        title.append(": ", style="default")
        if issue.field:
            title.append(_single_line(issue.field) + ": ", style="bold")
        title.append(_single_line(issue.message), style="default")
        self.console.print(title)
        source = issue.source_location
        lines = _verified_lines(source, sources) if source is not None else None
        location = _path(source.path if source is not None else target)
        # Unverified source is deliberately file-only: even a plausible numeric
        # position can now point at unrelated content after a concurrent edit.
        if source is not None and source.start is not None and lines is not None:
            location += f":{source.start.line}:{source.start.column}"
        self.console.print(Text(" --> " + location, style="blue"))
        if source is not None and lines is not None:
            self._excerpt(source, lines, color)
        if issue.suggestion:
            help_text = Text("help: ", style="bold cyan")
            help_text.append(_single_line(issue.suggestion), style="default")
            self.console.print(help_text)
        if issue.docs_url:
            self.console.print(Text("docs: " + _single_line(issue.docs_url), style="dim cyan"))

    def report(self, file_results: FileResults, verbose: bool = False, *, show_progress: bool = False) -> None:
        """Display findings in stable target order, retaining duplicates."""
        sources: _SourceCache = {}
        printed = False
        for target, validators in sorted(file_results.items(), key=lambda item: str(item[0])):
            for validator, result in validators:
                issues = [*result.errors, *result.warnings, *(result.info if verbose else [])]
                for issue in issues:
                    if printed:
                        self.console.print()
                    self._issue(target, issue, sources)
                    printed = True
                if not issues and (show_progress or not result.passed):
                    status = "PASSED" if result.passed else "FAILED"
                    self.console.print(Text(f"{status} {_path(target)} ({_single_line(validator)})"))
                    printed = True

    def report_fixes(self, fixes: list[AppliedFix]) -> None:
        """Show applied fixes without interpreting their data as terminal markup."""
        for fix in fixes:
            self.console.print(
                Text(
                    f"fixed {_single_line(','.join(fix.codes))}: {_path(fix.path)}: {_single_line(fix.description)}",
                    style="green",
                )
            )

    def summarize(self, total_files: int, passed: int, failed: int, warnings: int) -> None:
        """Print an optional compact scan summary with the actual scan status."""
        self.console.print(
            Text(
                f"{total_files} files checked: {passed} passed, {failed} failed, {warnings} passed files with warnings",
                style="bold red" if failed else "bold green",
            )
        )
