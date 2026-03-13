#!/usr/bin/env python3
"""CLI for skilllint rule documentation.

Usage:
    skilllint-rule SK001      # Show documentation for rule SK001
    skilllint-rules           # List all rules
    skilllint-rules -p claude-code  # Filter by platform
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import rules to register them
import skilllint.rules.as_series  # noqa: F401
from skilllint.rule_registry import get_rule, list_rules

console = Console()


def show_rule(rule_id: str) -> None:
    """Show documentation for a rule ID.

    Args:
        rule_id: Rule identifier (e.g., "SK001", "FM002")
    """
    entry = get_rule(rule_id)
    if not entry:
        console.print(f"[red]Unknown rule: {rule_id}[/red]")
        console.print("\n[dim]Run [bold]skilllint-rules[/bold] to see all available rules.[/dim]")
        raise typer.Exit(1)

    # Header with severity indicator
    severity_colors = {"error": "red", "warning": "yellow", "info": "blue"}
    sev_color = severity_colors.get(entry.severity, "white")

    console.print()
    console.print(f"[bold]{entry.id}[/bold] — [{sev_color}]{entry.severity}[/{sev_color}]")
    console.print(f"[dim]Category: {entry.category} | Platforms: {', '.join(entry.platforms)}[/dim]")
    console.print()
    console.print(Panel(entry.docstring, title=entry.id, border_style="dim"))


def list_rules_cmd(
    platform: Annotated[
        str | None, typer.Option("--platform", "-p", help="Filter rules by platform (e.g., 'claude-code')")
    ] = None,
    category: Annotated[
        str | None, typer.Option("--category", "-c", help="Filter rules by category (e.g., 'skill')")
    ] = None,
    severity: Annotated[
        str | None, typer.Option("--severity", "-s", help="Filter rules by severity (error, warning, info)")
    ] = None,
) -> None:
    """List all available validation rules."""
    rules = list_rules(platform=platform, category=category, severity=severity)

    if not rules:
        console.print("[yellow]No rules found matching the specified filters.[/yellow]")
        return

    severity_colors = {"error": "red", "warning": "yellow", "info": "blue"}

    # Build table
    table = Table(title="Validation Rules", show_header=True, header_style="bold")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Severity", no_wrap=True)
    table.add_column("Category", no_wrap=True)
    table.add_column("Summary")

    for rule in rules:
        sev_color = severity_colors.get(rule.severity, "white")
        summary = rule.docstring.strip().split("\n")[0] if rule.docstring else ""

        table.add_row(rule.id, f"[{sev_color}]{rule.severity}[/{sev_color}]", rule.category, summary)

    console.print(table)
    console.print("\n[dim]Run [bold]skilllint-rule <ID>[/bold] for details on a specific rule.[/dim]")


# Create separate apps for each command
rule_app = typer.Typer(help="Show documentation for a rule ID", add_completion=False)
rule_app.command()(show_rule)

rules_app = typer.Typer(help="List all available validation rules", add_completion=False)
rules_app.command()(list_rules_cmd)
