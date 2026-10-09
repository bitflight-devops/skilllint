"""Validation result reporters.

Extracted from ``plugin_validator`` so the CLI entrypoint can delegate output
formatting to a dedicated module without changing user-facing behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeAlias

from rich.console import Console, ConsoleRenderable, RichCast
from rich.markup import escape
from rich.panel import Panel

from skilllint.output import ICON_ERROR, ICON_FIXED, ICON_INFO, ICON_PASSED, ICON_WARNING, print_panel, rendered_width

if TYPE_CHECKING:
    from skilllint.models import AppliedFix, ValidationIssue, ValidationResult

FileResults: TypeAlias = dict[Path, list[tuple[str, "ValidationResult"]]]


class Reporter(Protocol):
    """Protocol for result reporters.

    Defines interface for formatting and displaying validation results to users.
    Different implementations support various output formats (Rich terminal,
    plain text for CI, summary).
    """

    def report(self, file_results: FileResults, verbose: bool = False, *, show_progress: bool = False) -> None:
        """Display validation results grouped by file."""
        ...

    def summarize(self, total_files: int, passed: int, failed: int, warnings: int) -> None:
        """Display summary statistics."""
        ...

    def report_fixes(self, fixes: list[AppliedFix]) -> None:
        """Display fixes applied by --fix, grouped by file."""
        ...


class ConsoleReporter:
    """Rich-based terminal reporter with colored output."""

    def __init__(self, console: Console | None = None, *, no_color: bool = False) -> None:
        if console is not None:
            self.console = console
        else:
            self.console = Console(force_terminal=not no_color, no_color=no_color, soft_wrap=True, emoji=False)
        self.no_color = no_color

    @staticmethod
    def _get_rendered_width(renderable: ConsoleRenderable | RichCast | str) -> int:
        """Get actual rendered width of any Rich renderable.

        Returns:
            The maximum rendered width in characters.
        """
        return rendered_width(renderable)

    @staticmethod
    def _issue_lines(issue: ValidationIssue) -> list[str]:
        """Build complete styled diagnostic lines without rendering each separately.

        Returns:
            Issue, suggestion and documentation lines in display order.
        """
        severity_icons = {"error": ICON_ERROR, "warning": ICON_WARNING, "info": ICON_INFO}
        severity_colors = {"error": "red", "warning": "yellow", "info": "blue"}
        icon = severity_icons.get(issue.severity, "")
        color = severity_colors.get(issue.severity, "white")
        location = f":{issue.line}" if issue.line else ""
        lines = [
            f"    {icon} [{color}][{escape(issue.code)}][/{color}] {escape(issue.field)}{location}: {escape(issue.message)}"
        ]
        if issue.suggestion:
            lines.append(f"      [dim]→[/dim] {escape(issue.suggestion)}")
        if issue.docs_url:
            lines.append(f"      [dim]→[/dim] [cyan]{escape(issue.docs_url)}[/cyan]")
        return lines

    def _print_issue(self, issue: ValidationIssue) -> None:
        """Print a single validation issue with Rich formatting."""
        self.console.print(
            "\n".join(self._issue_lines(issue)),
            crop=False,
            overflow="ignore",
            soft_wrap=True,
            highlight=False,
            emoji=False,
        )

    def report(self, file_results: FileResults, verbose: bool = False, *, show_progress: bool = False) -> None:
        """Display validation results with Rich formatting, grouped by file."""
        for file_path, validator_results in file_results.items():
            all_passed = all(r.passed for _, r in validator_results)
            any_issues = any(r.errors or r.warnings or (verbose and r.info) for _, r in validator_results)
            if all_passed and not any_issues:
                if show_progress:
                    self.console.print(
                        f"{ICON_PASSED} [green]{escape(str(file_path))}[/green] - PASSED",
                        crop=False,
                        overflow="ignore",
                        soft_wrap=True,
                        highlight=False,
                        emoji=False,
                    )
                continue

            lines = [f"\n[bold]{escape(str(file_path))}[/bold]"]
            for validator_name, result in validator_results:
                issues_to_show = [*result.errors, *result.warnings]
                if verbose:
                    issues_to_show.extend(result.info)
                if not issues_to_show:
                    if show_progress:
                        lines.append(f"  {ICON_PASSED} [dim]{escape(validator_name)}:[/dim] PASSED")
                    continue
                status_icon = ICON_ERROR if not result.passed else ICON_WARNING
                lines.append(f"  {status_icon} [dim]{escape(validator_name)}:[/dim]")
                for issue in issues_to_show:
                    lines.extend(self._issue_lines(issue))
            # Render once per file. Large scans can contain tens of thousands
            # of diagnostics; per-line Rich calls dominated their runtime.
            self.console.print(
                "\n".join(lines), crop=False, overflow="ignore", soft_wrap=True, highlight=False, emoji=False
            )

    def report_fixes(self, fixes: list[AppliedFix]) -> None:
        """Display a summary of files and rules that --fix modified.

        Args:
            fixes: Fixes applied during this run, in the order they were
                recorded. Grouped by file for display, preserving the order
                each file's fixes were recorded in.
        """
        self.console.print("\n[bold]Fixes applied[/bold]", crop=False, overflow="ignore", soft_wrap=True)
        fixes_by_path: dict[Path, list[AppliedFix]] = {}
        for applied_fix in fixes:
            fixes_by_path.setdefault(applied_fix.path, []).append(applied_fix)
        for file_path, path_fixes in fixes_by_path.items():
            self.console.print(
                f"[bold]{escape(str(file_path))}[/bold]", crop=False, overflow="ignore", soft_wrap=True, emoji=False
            )
            for applied_fix in path_fixes:
                codes = ", ".join(applied_fix.codes)
                self.console.print(
                    f"  {ICON_FIXED} [magenta][{escape(codes)}][/magenta] "
                    f"[dim]{escape(applied_fix.validator)}:[/dim] {escape(applied_fix.description)}",
                    crop=False,
                    overflow="ignore",
                    soft_wrap=True,
                    emoji=False,
                )

    def summarize(self, total_files: int, passed: int, failed: int, warnings: int) -> None:
        """Display summary statistics with Rich formatting."""
        if failed == 0:
            status_icon = ICON_PASSED
            status_text = "PASSED"
            status_color = "green"
        else:
            status_icon = ICON_ERROR
            status_text = "FAILED"
            status_color = "red"

        summary_lines = [
            f"{status_icon} [bold {status_color}]{status_text}[/bold {status_color}]",
            "",
            f"Total files: {total_files}",
            f"[green]Passed: {passed}[/green]",
            f"[red]Failed: {failed}[/red]",
        ]

        if warnings > 0:
            summary_lines.append(f"[yellow]Warnings: {warnings}[/yellow]")

        summary = "\n".join(summary_lines)
        panel = Panel(summary, title="Validation Summary", border_style=status_color, expand=False)
        print_panel(self.console, panel)


class CIReporter:
    """Plain text reporter for CI environments."""

    @staticmethod
    def _print_issue(issue: ValidationIssue) -> None:
        """Print a single validation issue in plain text."""
        severity_prefixes = {"error": "✗ ERROR", "warning": "⚠ WARN", "info": "i INFO"}
        prefix = severity_prefixes.get(issue.severity, "")
        location = f":{issue.line}" if issue.line else ""

        print(f"    {prefix} [{issue.code}] {issue.field}{location}: {issue.message}")

        if issue.suggestion:
            print(f"      → {issue.suggestion}")

        if issue.docs_url:
            print(f"      → {issue.docs_url}")

    def report(self, file_results: FileResults, verbose: bool = False, *, show_progress: bool = False) -> None:
        """Display validation results in plain text, grouped by file."""
        for file_path, validator_results in file_results.items():
            all_passed = all(r.passed for _, r in validator_results)
            any_issues = False

            for _vname, result in validator_results:
                issues_to_show = [*result.errors, *result.warnings]
                if verbose:
                    issues_to_show.extend(result.info)
                if issues_to_show:
                    any_issues = True

            if all_passed and not any_issues:
                if show_progress:
                    print(f"✓ {file_path} - PASSED")
                continue

            print(f"\n{file_path}")

            for validator_name, result in validator_results:
                issues_to_show = [*result.errors, *result.warnings]
                if verbose:
                    issues_to_show.extend(result.info)

                if not issues_to_show:
                    if show_progress:
                        print(f"  ✓ {validator_name}: PASSED")
                    continue

                status_icon = "✗" if not result.passed else "⚠"
                print(f"  {status_icon} {validator_name}:")

                for issue in issues_to_show:
                    self._print_issue(issue)

    def report_fixes(self, fixes: list[AppliedFix]) -> None:
        """Display a summary of files and rules that --fix modified, plain text.

        Args:
            fixes: Fixes applied during this run, one line per fix.
        """
        for applied_fix in fixes:
            codes = ", ".join(applied_fix.codes)
            print(f"FIXED [{codes}] {applied_fix.path}: {applied_fix.description}")

    def summarize(self, total_files: int, passed: int, failed: int, warnings: int) -> None:
        """Display summary statistics in plain text."""
        status = "✓ PASSED" if failed == 0 else "✗ FAILED"

        print("\n" + "=" * 60)
        print(f"{status}")
        print(f"Total files: {total_files}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        if warnings > 0:
            print(f"Warnings: {warnings}")
        print("=" * 60)


class SummaryReporter:
    """Single-line summary reporter for quick status checks."""

    def report(self, file_results: FileResults, verbose: bool = False, *, show_progress: bool = False) -> None:
        """Display nothing (summary-only reporter)."""

    def report_fixes(self, fixes: list[AppliedFix]) -> None:
        """Display nothing (summary-only reporter)."""

    def summarize(self, total_files: int, passed: int, failed: int, warnings: int) -> None:
        """Display single-line summary."""
        if failed == 0:
            status_icon = "✓"
            status = f"{passed}/{total_files} files passed"
        else:
            status_icon = "✗"
            status = f"{failed}/{total_files} files failed"

        if warnings > 0:
            status += f" ({warnings} with warnings)"

        print(f"{status_icon} {status}")
