"""Plain Typer help that preserves complete fields and intentional line breaks."""

from __future__ import annotations

from collections.abc import Sequence

from typer import Context
from typer._click import Context as ClickContext
from typer._click._compat import term_len  # noqa: PLC2701 - Match the vendored formatter's visible-label measurement.
from typer._click.formatting import HelpFormatter  # noqa: PLC2701 - Typer has no public HelpFormatter export.
from typer.core import TyperCommand, TyperGroup


class CompleteHelpFormatter(HelpFormatter):
    """Align help from its content without terminal-based reflow or cropping."""

    def write_usage(self, prog: str, args: str = "", prefix: str | None = None) -> None:
        """Write the complete usage on one physical line."""
        prefix = "Usage: " if prefix is None else prefix
        self.write(f"{prefix:>{self.current_indent}}{prog} {args}\n")

    def write_text(self, text: str) -> None:
        """Preserve source line breaks and indentation in help paragraphs."""
        indent = " " * self.current_indent
        for line in text.expandtabs().splitlines():
            # Click's no-rewrap marker is formatting metadata, not visible text.
            if line.strip() != "\b":
                self.write(f"{indent}{line}\n")

    def write_dl(self, rows: Sequence[tuple[str, str]], col_max: int = 30, col_spacing: int = 2) -> None:
        """Align definition lists to their longest label without folding values."""
        # col_max/col_spacing retain Click's override signature. Unlike its
        # formatter, we do not cap labels at col_max or values at terminal width.
        first_width = max((term_len(first) for first, _ in rows), default=0)
        for first, second in rows:
            padding = " " * (first_width - term_len(first) + col_spacing)
            lines = second.splitlines() or [""]
            self.write(f"{' ' * self.current_indent}{first}{padding}{lines[0]}\n")
            for line in lines[1:]:
                self.write(f"{' ' * (self.current_indent + first_width + col_spacing)}{line}\n")


class CompleteHelpContext(Context):
    """Use the complete-content formatter for help and usage errors."""

    formatter_class = CompleteHelpFormatter


class CompleteHelpCommand(TyperCommand):
    """Typer command with complete plain help."""

    context_class = CompleteHelpContext


class CompleteHelpGroup(TyperGroup):
    """Typer group that does not shorten command summaries to console width."""

    context_class = CompleteHelpContext

    def format_commands(self, ctx: ClickContext, formatter: HelpFormatter) -> None:
        """Retain normal command summaries without width-based ellipses."""
        rows: list[tuple[str, str]] = []
        for name in self.list_commands(ctx):
            command = self.get_command(ctx, name)
            if command is not None and not command.hidden:
                # get_short_help_str still selects a summary sentence. Its
                # shortening limit comes from the full source, not the terminal.
                source = command.short_help or command.help or ""
                rows.append((name, command.get_short_help_str(limit=len(source))))
        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)
