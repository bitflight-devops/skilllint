"""Complete emitted content across help, rule docs, diagnostics and recordings."""

from __future__ import annotations

import io
from pathlib import Path
from xml.etree import ElementTree

import pytest
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from skilllint import cli_docs, plugin_validator
from skilllint.cli_help import CompleteHelpCommand, CompleteHelpGroup
from skilllint.models import ValidationIssue, ValidationResult
from skilllint.output import print_panel, print_table
from skilllint.reporting import ConsoleReporter
from skilllint.vendor_cache import CacheResult, CacheStatus, NoCacheError

# Exceeds the former 800-column help boundary, modelling long diagnostic values.
_LONG_VALUE = "https://example.invalid/" + "path-segment/" * 100 + "?complete=yes"


def test_help_wraps_long_labels_usage_and_authored_text_without_truncation(cli_runner):
    app = typer.Typer(cls=CompleteHelpGroup, rich_markup_mode=None)
    option_name = "--" + "long-option-" * 80

    @app.command(cls=CompleteHelpCommand)
    def inspect_content(value: str = typer.Option("", option_name, help=_LONG_VALUE)) -> None:
        """Inspect complete content.

        First intentional line.
            Indented second line.
        """

    result = cli_runner.invoke(app, ["--help"], prog_name="tool-" + _LONG_VALUE)
    assert result.exit_code == 0
    flattened = " ".join(result.stdout.split())
    assert "tool-" + _LONG_VALUE in flattened
    assert option_name in flattened
    assert _LONG_VALUE in flattened
    assert "First intentional line." in flattened
    assert "Indented second line." in flattened
    assert "..." not in result.stdout


@pytest.mark.parametrize("columns", [40, 200])
def test_table_preserves_values_on_their_rows_and_in_recording(columns, tmp_path):
    console = Console(file=io.StringIO(), width=columns, height=25, record=True)
    table = Table("ID", "Description")
    table.add_row("RULE_IDENTIFIER", _LONG_VALUE)
    print_table(console, table)
    output = console.export_text(clear=False)
    assert any("RULE_IDENTIFIER" in line and _LONG_VALUE in line for line in output.splitlines())
    assert "…" not in output
    from skilllint.record_export import export_recording

    html_path = tmp_path / "rules.html"
    export_recording(console, html_path, title="rules")
    assert _LONG_VALUE in html_path.read_text()
    svg_path = tmp_path / "rules.svg"
    export_recording(console, svg_path, title="rules")
    svg = ElementTree.fromstring(svg_path.read_text())
    assert float(svg.attrib["viewBox"].split()[2]) > len(_LONG_VALUE)
    assert _LONG_VALUE in "".join(svg.itertext())
    assert console.width == columns


@pytest.mark.parametrize("columns", [40, 200])
def test_documentation_panel_preserves_long_prose_code_and_link(columns):
    buf = io.StringIO()
    console = Console(file=buf, width=columns, height=25, color_system=None)
    body = f"# Heading\n\n{_LONG_VALUE}\n\n```text\n{_LONG_VALUE}\n```\n\n[Authority]({_LONG_VALUE})"
    print_panel(console, Panel(Syntax(body, "markdown", word_wrap=False), title="Rule"))
    assert buf.getvalue().count(_LONG_VALUE) == 3
    assert console.width == columns


@pytest.mark.parametrize("body", [f"|ID|Value|\n|--|--|\n|RULE|{_LONG_VALUE}|", f"- {_LONG_VALUE}", f"> {_LONG_VALUE}"])
def test_rule_command_preserves_nested_markdown_content(cli_runner, monkeypatch, body):
    entry = plugin_validator._get_rule("FM010")
    assert entry is not None
    monkeypatch.setattr(plugin_validator, "_get_rule", lambda rule_id: entry.model_copy(update={"docstring": body}))
    monkeypatch.setenv("COLUMNS", "40")
    result = cli_runner.invoke(plugin_validator.app, ["rule", "FM010"])
    assert result.exit_code == 0
    assert _LONG_VALUE in result.stdout


def test_diagnostics_preserve_long_value_after_summary():
    buf = io.StringIO()
    console = Console(file=buf, width=40, height=25, color_system=None)
    reporter = ConsoleReporter(console=console)
    reporter.summarize(1, 0, 1, 0)
    reporter._print_issue(ValidationIssue(code="FM001", severity="error", field="field", message=_LONG_VALUE))
    assert any("FM001" in line and _LONG_VALUE in line for line in buf.getvalue().splitlines())
    assert console.width == 40


def test_diagnostics_do_not_interpret_data_as_rich_markup():
    buf = io.StringIO()
    reporter = ConsoleReporter(console=Console(file=buf, width=40, height=25, color_system=None))
    message = "[bold]literal diagnostic[/bold] " + _LONG_VALUE
    reporter._print_issue(ValidationIssue(code="FM001", severity="error", field="field", message=message))
    assert message in buf.getvalue()


def test_content_measurement_and_svg_ignore_dumb_terminal_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("FORCE_COLOR", "1")
    console = Console(file=io.StringIO(), record=True)
    original_width = console.width
    print_panel(console, Panel(f"URL: {_LONG_VALUE}"))
    table = Table("ID", "Value")
    table.add_row("RULE", _LONG_VALUE)
    print_table(console, table)
    assert console.export_text(clear=False).count(_LONG_VALUE) == 2
    from skilllint.record_export import export_recording

    path = tmp_path / "dumb-terminal.svg"
    export_recording(console, path, title="complete output")
    svg = ElementTree.fromstring(path.read_text())
    assert float(svg.attrib["viewBox"].split()[2]) > len(_LONG_VALUE)
    assert console.width == original_width


def test_docs_fetch_error_preserves_long_url(cli_runner, monkeypatch):
    monkeypatch.setenv("COLUMNS", "40")
    monkeypatch.setattr(cli_docs, "fetch_or_cached", lambda *args, **kwargs: _no_cache())
    result = cli_runner.invoke(plugin_validator.app, ["docs", "fetch", _LONG_VALUE])
    assert result.exit_code == 1
    assert _LONG_VALUE in result.stderr


def _no_cache():
    raise NoCacheError(_LONG_VALUE, "network unavailable")


def test_docs_section_emits_exact_source_including_markup(cli_runner, monkeypatch):
    body = f"[bold]literal tags[/bold]\n{_LONG_VALUE}\n"
    monkeypatch.setattr(cli_docs, "read_section", lambda *args: body)
    result = cli_runner.invoke(plugin_validator.app, ["docs", "section", "cached.md", "Heading"])
    assert result.exit_code == 0
    assert result.stdout == body


def test_docs_authorities_emit_exact_long_path(cli_runner, monkeypatch):
    path = Path("/cache") / ("nested/" * 100) / "[bold]source.md"
    monkeypatch.setattr(cli_docs, "iter_authority_urls", lambda **kwargs: iter([_LONG_VALUE]))
    monkeypatch.setattr(
        cli_docs,
        "fetch_or_cached",
        lambda *args, **kwargs: CacheResult(path=path, status=CacheStatus.FRESH, page_name="source", url=_LONG_VALUE),
    )
    result = cli_runner.invoke(plugin_validator.app, ["docs", "fetch-authorities"])
    assert result.exit_code == 0
    assert result.stdout == f"{path}\n"


def test_rule_help_uses_cli_argument_and_option_guidance(cli_runner):
    result = cli_runner.invoke(plugin_validator.app, ["rule", "--help"])
    assert result.exit_code == 0
    assert "Rule identifier (e.g., FM002, SK004)." in result.stdout
    assert "--record" in result.stdout
    assert "Args:" not in result.stdout


def test_grouped_report_preserves_all_diagnostics_and_literal_data():
    buf = io.StringIO()
    reporter = ConsoleReporter(console=Console(file=buf, width=40, height=25, color_system=None))
    issues = [
        ValidationIssue(
            code=f"FM{index:03d}",
            severity="error",
            field="[bold]field[/bold]",
            message=f"diagnostic {index}: {_LONG_VALUE}",
            suggestion="[link]literal suggestion[/link]",
            docs_url=_LONG_VALUE,
        )
        for index in range(32)
    ]
    reporter.report({
        Path("[bold]SKILL.md[/bold]"): [
            ("[red]validator[/red]", ValidationResult(passed=False, errors=issues, warnings=[], info=[]))
        ]
    })
    output = buf.getvalue()
    assert "[bold]SKILL.md[/bold]" in output
    assert "[red]validator[/red]" in output
    assert output.count(_LONG_VALUE) == 64
    assert output.count("[link]literal suggestion[/link]") == 32
    for index in range(32):
        assert f"[FM{index:03d}] [bold]field[/bold]: diagnostic {index}: {_LONG_VALUE}" in output
