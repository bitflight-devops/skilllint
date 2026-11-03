"""Run the composite Action against one structured scan, preserving human output."""

from __future__ import annotations

import os
import platform
import traceback
from pathlib import Path
from uuid import uuid4

import typer
from typer.main import get_group

from skilllint import __version__
from skilllint.plugin_validator import app, main as check
from skilllint.reporting_github import emit_github
from skilllint.scan_runtime import CheckRun


def _check_context() -> typer.Context:
    """Build the same command context used by ``skilllint check``.

    Returns:
        The check command context, with its normal parent help scope.

    Raises:
        RuntimeError: If the installed CLI no longer exposes its check command.
    """
    group = get_group(app)
    root = typer.Context(group, info_name="skilllint")
    command = group.get_command(root, "check")
    if command is None:
        raise RuntimeError("skilllint check command is unavailable")
    return typer.Context(command, info_name="check", parent=root)


def run() -> int:
    """Read Action inputs and publish outputs.

    Returns:
        The validation or usage exit code.
    """
    inspected = ""
    scan: CheckRun | None = None
    codes: set[str] = set()
    verbose = os.environ.get("INPUT_VERBOSE") == "true"

    def report(outcome: CheckRun | list[tuple[int, Path]]) -> None:
        nonlocal inspected, scan
        if not isinstance(outcome, CheckRun):
            inspected = str(len(outcome))
            return
        scan = outcome
        inspected = str(len(outcome.results))
        for validators in outcome.results.values():
            for _, result in validators:
                issues = [*result.errors, *result.warnings, *(result.info if verbose else [])]
                codes.update(issue.code for issue in issues)
        for fix in outcome.fixes:
            codes.update(fix.codes)

    exit_code = 0
    # Untrusted filenames and finding text must not become workflow commands in human logs.
    command_token = uuid4().hex
    typer.echo(f"::stop-commands::{command_token}")
    try:
        check(
            ctx=_check_context(),
            paths=[Path(path) for path in os.environ.get("INPUT_PATHS", ".").split()],
            check=os.environ.get("INPUT_CHECK_ONLY") == "true",
            fix=os.environ.get("INPUT_FIX") == "true",
            verbose=verbose,
            no_color=os.environ.get("INPUT_NO_COLOR", "true") == "true",
            tokens_only=os.environ.get("INPUT_TOKENS_ONLY") == "true",
            show_progress=os.environ.get("INPUT_SHOW_PROGRESS") == "true",
            show_summary=os.environ.get("INPUT_SHOW_SUMMARY", "true") == "true",
            platform=os.environ.get("INPUT_PLATFORM") or None,
            filter_glob=os.environ.get("INPUT_FILTER") or None,
            filter_type=os.environ.get("INPUT_FILTER_TYPE") or None,
            action_report=report,
        )
    except (typer.Exit, SystemExit) as exc:
        exit_code = exc.exit_code if isinstance(exc, typer.Exit) else int(exc.code or 0)
    except Exception:  # noqa: BLE001 - preserve Action outputs and suspend commands for crash tracebacks
        traceback.print_exc()
        exit_code = 1
        inspected = ""
        codes.clear()
        scan = None
    finally:
        typer.echo(f"::{command_token}::")
    if scan is not None:
        emit_github(scan.results, verbose=verbose)
    outputs = {
        "exit-code": str(exit_code),
        "inspected-count": inspected,
        "findings": " ".join(sorted(codes)),
        "tool-python": f"{'Python' if platform.python_implementation() == 'CPython' else platform.python_implementation()} {platform.python_version()}",
        "tool-version": f"skilllint {__version__}",
        "result": "passed" if exit_code == 0 else "failed",
    }
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
        for name, value in outputs.items():
            if "\n" in value or "\r" in value:
                delimiter = uuid4().hex
                while delimiter in value.splitlines():
                    delimiter = uuid4().hex
                stream.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
            else:
                stream.write(f"{name}={value}\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(run())
