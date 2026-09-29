"""Tests for the ``python -m skilllint`` entry point."""

from __future__ import annotations

import re
import subprocess
import sys

from skilllint.version import __version__

# GitHub Actions sets FORCE_COLOR=1, so Rich emits ANSI codes even into a pipe
# (same pattern as conftest._ANSI_ESCAPE).
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[mGKHFJA-Z]")


def _run_module(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, "-m", "skilllint", *args], capture_output=True, check=False, text=True)
    result.stdout = _ANSI_ESCAPE.sub("", result.stdout)
    return result


def test_python_dash_m_skilllint_shows_cli_help_under_the_skilllint_name() -> None:
    result = _run_module("--help")

    assert result.returncode == 0, result.stderr
    assert "Usage: skilllint" in result.stdout


def test_python_dash_m_skilllint_reports_the_package_version() -> None:
    result = _run_module("--version")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"skilllint {__version__}"
