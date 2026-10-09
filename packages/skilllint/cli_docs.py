"""Typer sub-app for the ``skilllint docs`` subcommand group.

Provides ``fetch``, ``latest``, ``sections``, ``section``, and ``verify``
commands that wrap :mod:`skilllint.vendor_cache`.  All business logic lives in
that module — this file is a pure CLI adapter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from skilllint.cli_help import CompleteHelpCommand, CompleteHelpGroup
from skilllint.cli_json import JsonOption, emit_and_exit
from skilllint.output import ICON_ERROR, ICON_PASSED, ICON_WARNING, print_panel
from skilllint.responses import (
    AuthorityResult,
    authority_failed,
    authority_fetched,
    build_authorities_response,
    build_fetch_no_cache_response,
    build_fetch_response,
    build_latest_response,
    build_section_response,
    build_sections_response,
    build_verify_response,
)
from skilllint.rule_registry import iter_authority_urls
from skilllint.vendor_cache import (
    CacheStatus,
    IntegrityStatus,
    NoCacheError,
    fetch_or_cached,
    find_latest,
    find_section,
    format_section_index,
    list_sections,
    read_section,
    verify_integrity,
)

# ---------------------------------------------------------------------------
# Consoles
# ---------------------------------------------------------------------------

console = Console(soft_wrap=True, emoji=False)  # stdout — file paths and data output
err_console = Console(stderr=True, soft_wrap=True, emoji=False)  # stderr — status, warnings, errors

# ---------------------------------------------------------------------------
# Typer sub-app
# ---------------------------------------------------------------------------

docs_app = typer.Typer(
    help="Fetch, query, and verify cached vendor documentation.",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode=None,
    cls=CompleteHelpGroup,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_status_label(status: CacheStatus) -> str:
    """Return the uppercased display label for a cache status.

    Args:
        status: The :class:`CacheStatus` value to format.

    Returns:
        Uppercase string of the status enum value (e.g. ``"REFRESHED"``).
    """
    return status.value.upper()


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------


@docs_app.command(cls=CompleteHelpCommand)
def fetch(
    url: Annotated[str, typer.Argument(help="Documentation URL to fetch or serve from cache.")],
    ttl: Annotated[
        float, typer.Option("--ttl", help="Cache time-to-live in hours before a refresh is attempted.")
    ] = 4.0,
    force: Annotated[
        bool, typer.Option("--force", help="Skip the freshness check and always attempt a network fetch.")
    ] = False,
    json_output: JsonOption = False,
) -> None:
    """Fetch a documentation page or return a cached copy.

    Prints the cached file path to stdout so agents can capture it.
    Status information is written to stderr.

    Exit status:
        1 when no cache exists and network is unavailable.
    """
    try:
        result = fetch_or_cached(url, ttl_hours=ttl, force=force)
    except NoCacheError as exc:
        if json_output:
            emit_and_exit(build_fetch_no_cache_response(exc), code=1)
        print_panel(
            err_console,
            Panel(
                f"[bold]URL:[/bold] {escape(str(exc.url))}\n[bold]Reason:[/bold] {escape(str(exc.reason))}",
                title=f"{ICON_ERROR} No Cache Available",
                border_style="red",
            ),
        )
        raise typer.Exit(code=1) from exc

    if json_output:
        emit_and_exit(build_fetch_response(result))

    if result.status is CacheStatus.STALE:
        err_console.print(f"{ICON_WARNING} [yellow]Serving stale cache — network unavailable[/yellow]")
    else:
        status_label = _format_status_label(result.status)
        err_console.print(f"{ICON_PASSED} [green]{status_label}[/green] {escape(str(result.page_name))}")

    typer.echo(str(result.path))


# ---------------------------------------------------------------------------
# fetch-authorities
# ---------------------------------------------------------------------------


def _fetch_authority_results(urls: list[str], *, ttl: float, force: bool) -> list[AuthorityResult]:
    """Attempt every URL and describe each outcome, for ``--json``.

    Follows the same collect-and-continue contract as the text path: a URL that fails never stops the
    ones after it.

    Args:
        urls: The registry URLs, in registry order.
        ttl: Cache time-to-live in hours.
        force: Skip the freshness check and always attempt a network fetch.

    Returns:
        One outcome per URL, in the same order.
    """
    results: list[AuthorityResult] = []
    for url in urls:
        try:
            results.append(authority_fetched(url, fetch_or_cached(url, ttl_hours=ttl, force=force)))
        except NoCacheError as exc:
            results.append(authority_failed(str(exc.url), str(exc.reason)))
        except Exception as exc:  # noqa: BLE001 — collect-and-continue contract: all URLs must be attempted
            results.append(authority_failed(str(url), str(exc)))
    return results


@docs_app.command("fetch-authorities", cls=CompleteHelpCommand)
def fetch_authorities(
    ttl: Annotated[
        float, typer.Option("--ttl", help="Cache time-to-live in hours before a refresh is attempted.")
    ] = 4.0,
    force: Annotated[
        bool, typer.Option("--force", help="Skip the freshness check and always attempt a network fetch.")
    ] = False,
    json_output: JsonOption = False,
) -> None:
    """Fetch cached documentation for all normalized rule authority URLs.

    Prints one cached file path per successfully fetched authority URL.

    Exit status:
        1 when one or more authority URLs cannot be fetched
            and no stale cache can be served.
    """
    authority_urls = list(iter_authority_urls(unique=True))
    if json_output:
        results = _fetch_authority_results(authority_urls, ttl=ttl, force=force)
        response = build_authorities_response(results)
        emit_and_exit(response, code=1 if response.status == "failed" else 0)
    if not authority_urls:
        err_console.print(f"{ICON_WARNING} [yellow]No authority URLs found in the rule registry[/yellow]")
        return

    had_failure = False
    for url in authority_urls:
        try:
            result = fetch_or_cached(url, ttl_hours=ttl, force=force)
        except NoCacheError as exc:
            had_failure = True
            err_console.print(f"{ICON_ERROR} [red]FAILED[/red] {escape(str(exc.url))} ({escape(str(exc.reason))})")
            continue
        except Exception as exc:  # noqa: BLE001 — collect-and-continue contract: all URLs must be attempted
            had_failure = True
            err_console.print(f"{ICON_ERROR} [red]FAILED[/red] {escape(str(url))} ({escape(str(exc))})")
            continue

        if result.status is CacheStatus.STALE:
            err_console.print(f"{ICON_WARNING} [yellow]STALE[/yellow] {escape(str(url))} — serving stale cache")
        else:
            status_label = _format_status_label(result.status)
            err_console.print(f"{ICON_PASSED} [green]{status_label}[/green] {escape(str(url))}")

        typer.echo(str(result.path))

    if had_failure:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# latest
# ---------------------------------------------------------------------------


@docs_app.command(cls=CompleteHelpCommand)
def latest(
    page_name: Annotated[
        str, typer.Argument(help="Filesystem-safe page name to look up (e.g. 'claude-code--settings').")
    ],
    json_output: JsonOption = False,
) -> None:
    """Find the most recent cached file for a page name.

    Prints the file path to stdout when found.

    Exit status:
        1 when no cached file exists for the given page name.
    """
    path = find_latest(page_name)
    if json_output:
        emit_and_exit(build_latest_response(page_name, path), code=0 if path is not None else 1)
    if path is None:
        err_console.print(f"{ICON_ERROR} [red]No cached file found for page name:[/red] {escape(str(page_name))}")
        raise typer.Exit(code=1)

    typer.echo(str(path))


# ---------------------------------------------------------------------------
# sections
# ---------------------------------------------------------------------------


@docs_app.command(cls=CompleteHelpCommand)
def sections(
    file_path: Annotated[Path, typer.Argument(help="Path to the cached markdown file to index.")],
    json_output: JsonOption = False,
) -> None:
    """Print a table of sections in a cached markdown file.

    Output is written to stdout.
    """
    if file_path.exists() and not file_path.is_file():
        typer.echo(f"Expected a file path: {file_path}", err=True)
        raise typer.Exit(code=2) from None
    if json_output:
        file_exists = file_path.exists()
        emit_and_exit(build_sections_response(file_path, list_sections(file_path), file_exists=file_exists))
    table = format_section_index(file_path)
    typer.echo(table)


# ---------------------------------------------------------------------------
# section
# ---------------------------------------------------------------------------


@docs_app.command(cls=CompleteHelpCommand)
def section(
    file_path: Annotated[Path, typer.Argument(help="Path to the cached markdown file.")],
    heading: Annotated[str, typer.Argument(help="Heading text to locate (case-insensitive, leading # optional).")],
    json_output: JsonOption = False,
) -> None:
    """Print the text of a named section from a cached markdown file.

    Output is written to stdout.

    Exit status:
        1 when the heading is not found.
    """
    if file_path.exists() and not file_path.is_file():
        typer.echo(f"Expected a file path: {file_path}", err=True)
        raise typer.Exit(code=2) from None
    if json_output:
        file_exists = file_path.exists()
        found = find_section(file_path, heading)
        emit_and_exit(
            build_section_response(file_path, heading, found, file_exists=file_exists),
            code=0 if found is not None else 1,
        )
    text = read_section(file_path, heading)
    if text is None:
        err_console.print(
            f"{ICON_ERROR} [red]Section not found:[/red] {escape(repr(heading))} in {escape(str(file_path))}"
        )
        raise typer.Exit(code=1)

    typer.echo(text, nl=False)


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


@docs_app.command(cls=CompleteHelpCommand)
def verify(
    file_path: Annotated[Path, typer.Argument(help="Path to the cached markdown file to verify against its sidecar.")],
    json_output: JsonOption = False,
) -> None:
    """Verify a cached file against its .meta.json sidecar.

    Exits 0 when the file is intact, 1 otherwise.

    Exit status:
        1 when MODIFIED or UNVERIFIABLE.
    """
    if file_path.exists() and not file_path.is_file():
        typer.echo(f"Expected a file path: {file_path}", err=True)
        raise typer.Exit(code=2) from None
    if json_output:
        file_exists = file_path.exists()
        outcome = verify_integrity(file_path)
        emit_and_exit(
            build_verify_response(outcome, file_exists=file_exists),
            code=0 if outcome.status is IntegrityStatus.INTACT else 1,
        )
    result = verify_integrity(file_path)

    match result.status:
        case IntegrityStatus.INTACT:
            console.print(
                f"{ICON_PASSED} [green]INTACT[/green] {escape(str(file_path))}\n"
                f"  sha256: {escape(str(result.computed_sha256))}\n"
                f"  bytes:  {result.computed_bytes}"
            )

        case IntegrityStatus.MODIFIED:
            print_panel(
                err_console,
                Panel(
                    f"[bold]File:[/bold] {escape(str(file_path))}\n"
                    f"[bold]Computed sha256:[/bold]  {escape(str(result.computed_sha256))}\n"
                    f"[bold]Expected sha256:[/bold]  {escape(str(result.expected_sha256))}\n"
                    f"[bold]Computed bytes:[/bold]   {result.computed_bytes}\n"
                    f"[bold]Expected bytes:[/bold]   {result.expected_bytes}",
                    title=f"{ICON_WARNING} MODIFIED — file differs from sidecar",
                    border_style="yellow",
                ),
            )
            raise typer.Exit(code=1)

        case IntegrityStatus.UNVERIFIABLE:
            print_panel(
                err_console,
                Panel(
                    f"[bold]File:[/bold] {escape(str(file_path))}\nNo .meta.json sidecar found — cannot verify this file.",
                    title=f"{ICON_WARNING} UNVERIFIABLE — no sidecar",
                    border_style="yellow",
                ),
            )
            raise typer.Exit(code=1)
