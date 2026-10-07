"""Plain Typer help that wraps to terminal width without truncating content."""

from __future__ import annotations

from typer import Context
from typer._click import Context as ClickContext
from textwrap import TextWrapper

from typer._click.formatting import HelpFormatter  # noqa: PLC2701 - Typer has no public HelpFormatter export.
from typer.core import TyperCommand, TyperGroup


class CompleteHelpFormatter(HelpFormatter):
    """Wrap help at terminal width without splitting authored tokens such as URLs."""

    def write_text(self, text: str) -> None:
        """Write prose at the available width without breaking authored tokens."""
        text_width = max(self.width - self.current_indent, 11)
        wrapper = TextWrapper(width=text_width, break_long_words=False, break_on_hyphens=False)
        paragraphs = text.split("\n\n")
        rendered = "\n\n".join(wrapper.fill(" ".join(paragraph.split())) for paragraph in paragraphs)
        self.write(rendered)
        self.write("\n")


class CompleteHelpContext(Context):
    """Use width-aware plain help for help and usage errors."""

    formatter_class = CompleteHelpFormatter


class CompleteHelpCommand(TyperCommand):
    """Typer command with complete, width-aware plain help."""

    context_class = CompleteHelpContext


class CompleteHelpGroup(TyperGroup):
    """Typer group that wraps complete command summaries instead of ellipsizing them."""

    context_class = CompleteHelpContext

    def format_commands(self, ctx: ClickContext, formatter: HelpFormatter) -> None:
        """Keep complete command summaries and let the formatter wrap them to width."""
        rows: list[tuple[str, str]] = []
        for name in self.list_commands(ctx):
            command = self.get_command(ctx, name)
            if command is not None and not command.hidden:
                source = command.short_help or command.help or ""
                rows.append((name, command.get_short_help_str(limit=len(source))))
        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)
