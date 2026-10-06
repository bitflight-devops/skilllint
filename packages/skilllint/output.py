"""Content-driven Rich layout shared by the CLI's reporting surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console, ConsoleOptions, ConsoleRenderable, RenderResult, RichCast
from rich.emoji import Emoji
from rich.measure import Measurement
from rich.panel import Panel
from rich.table import Table


def emoji_glyph(name: str) -> str:
    """Resolve a Rich emoji name to its glyph before any text is printed.

    A status icon cannot stay a ``:name:`` token inside a string that also holds
    diagnostic data: Rich replaces every ``:name:`` it finds, so a data value
    such as a line number ``100`` would print as an emoji. Resolving the icon
    here lets the print keep emoji replacement off, leaving the data literal.

    Args:
        name: Rich emoji name without the colons, for example ``cross_mark``.

    Returns:
        The glyph Rich would have drawn for ``:name:``.
    """
    return Emoji.replace(f":{name}:")


ICON_ERROR = emoji_glyph("cross_mark")
ICON_WARNING = emoji_glyph("warning")
ICON_INFO = emoji_glyph("information")
ICON_PASSED = emoji_glyph("white_check_mark")
ICON_FIXED = emoji_glyph("wrench")
# Status icons are resolved to glyphs so the lines that carry diagnostic data
# can be printed with emoji replacement off.


def rendered_width(renderable: ConsoleRenderable | RichCast | str) -> int:
    """Measure natural width on the reporter's existing generous probe surface.

    Returns:
        The content's maximum rendered width, including container decoration.
    """
    # Existing ConsoleReporter measurement bound; this is a practical probe
    # surface, not a cap imposed on the output's content-driven width.
    # Rich's dumb-terminal fallback ignores an explicit width unless height is
    # explicit too (e.g. TERM=dumb with FORCE_COLOR). Retain its detected height.
    temporary = Console(width=999999, height=Console().height)
    return Measurement.get(temporary, temporary.options, renderable).maximum


def print_table(console: Console, table: Table) -> None:
    """Print every table cell intact, keeping values on their labelled rows."""
    for column in table.columns:
        column.no_wrap = True
        column.overflow = "ignore"
    table.width = rendered_width(table)
    console.print(table, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)


def print_panel(console: Console, panel: Panel) -> None:
    """Print a panel at its natural width without changing the caller's console."""
    panel.width = rendered_width(panel)
    # Console.print(width=...) clamps to console.width. Give the container its
    # measured rendering options instead, without mutating the shared console.
    console.print(_ContentWidthPanel(panel, panel.width), crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)


@dataclass(frozen=True)
class _ContentWidthPanel:
    panel: Panel
    width: int

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:  # noqa: PLW3201 - Rich render protocol.
        """Render the panel with its measured, content-driven container width.

        Yields:
            Rich segments rendered at the panel's natural width.
        """
        yield from console.render(self.panel, options.update_width(self.width))
