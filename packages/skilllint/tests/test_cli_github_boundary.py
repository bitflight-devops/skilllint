"""Invocation-level GitHub safety for parser diagnostics and crash tracebacks."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.main import get_group
from typer.testing import CliRunner

from skilllint import plugin_validator
from skilllint.cli_github_boundary import GitHubDiagnosticGroup

ENTRYPOINTS = [
    (sys.executable, "-m", "skilllint"),
    (sys.executable, "-m", "skilllint.plugin_validator"),
    *(
        (str(Path(sys.executable).parent / (name + (".exe" if os.name == "nt" else ""))),)
        for name in ("skilllint", "skillint", "pluginlint", "agentlint")
    ),
]


@pytest.mark.parametrize("entrypoint", ENTRYPOINTS)
@pytest.mark.parametrize("payload", ["--unknown##[error]injected", "--unknown\n::error::injected"])
def test_parser_errors_are_guarded_across_public_entrypoints(entrypoint: tuple[str, ...], payload: str) -> None:
    result = subprocess.run(
        [*entrypoint, "check", "--output-format=github", payload], capture_output=True, text=True, check=False
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "No such option" in result.stderr
    assert "##[" not in result.stderr
    assert "::error::" not in result.stderr


def _overlong_path(tmp_path: Path) -> Path:
    """Return a path whose existence probe raises on the current runtime."""
    if os.name == "nt":
        pytest.skip("This regression relies on POSIX component-length errors")
    # Exceed the filesystem's actual component limit, rather than inventing one.
    path = tmp_path / ("##[error]injected" + "x" * os.pathconf(tmp_path, "PC_NAME_MAX"))
    try:
        path.exists()
    except OSError:
        return path
    # Python 3.14 suppresses OSError from exists(); the callback test below
    # exercises uncaught tracebacks independently of these filesystem semantics.
    # https://docs.python.org/3.14/library/pathlib.html#querying-file-type-and-status
    pytest.skip("Path.exists suppresses OS errors on this runtime")


@pytest.mark.parametrize("entrypoint", ENTRYPOINTS)
def test_real_traceback_is_rendered_before_guard_ends(entrypoint: tuple[str, ...], tmp_path: Path) -> None:
    path = _overlong_path(tmp_path)
    result = subprocess.run(
        [*entrypoint, "check", str(path), "--output-format", "github"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "Traceback" in result.stderr
    assert "File name too long" in result.stderr
    assert "##%5Berror]injected" in result.stderr
    assert "##[" not in result.stderr


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["check", "--output-format", "github"], True),
        (["check", "--output-format=github"], True),
        (["--", "check", "--output-format=github"], True),
        (["--json", "check", "--output-format=github"], True),
        (["check", "--unknown", "--output-format=github"], True),
        (["check", "--output-format=concise", "--output-format", "github"], True),
        (["check", "--output-format=github", "--output-format", "concise"], False),
        (["check", "--", "--output-format=github"], False),
        (["check", "--output-format=github", "--", "--output-format=concise"], True),
        (["check", "--filter", "--output-format=github"], False),
        (["check", "--filter=--output-format=github"], False),
        (["check", "--record", "--output-format", "github"], False),
        (["check", "--filter", "--", "--output-format=github"], True),
        (["check", "--output-format=github", "--output-format"], False),
        (["docs", "fetch", "check", "--output-format=github"], False),
        ([], False),
    ],
)
def test_format_selection_follows_real_option_arity(args: list[str], expected: bool) -> None:
    command = get_group(plugin_validator.app)
    assert isinstance(command, GitHubDiagnosticGroup)
    assert command._requests_github(args) is expected


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--output-format", "concise"],
        ["--output-format=github", "--output-format=concise"],
        ["--output-format", "concise", "--filter", "--output-format=github"],
    ],
)
def test_non_github_parser_errors_remain_unchanged(args: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "skilllint", "check", *args, "--unknown##[error]injected"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "--unknown##[error]injected" in result.stderr


def test_non_github_traceback_keeps_original_rendering(tmp_path: Path) -> None:
    path = _overlong_path(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "skilllint", "check", str(path), "--output-format", "concise"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Traceback" in result.stderr
    assert "##[error]injected" in result.stderr


def test_cli_runner_and_non_standalone_callers_use_correct_exception_contract(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    failure = RuntimeError("##[error]injected")
    monkeypatch.setattr(plugin_validator, "main", Mock(side_effect=failure))
    args = ["check", "--output-format", "github", "SKILL.md"]
    result = CliRunner().invoke(plugin_validator.app, args)
    assert result.exit_code == 1
    assert "RuntimeError: ##%5Berror]injected" in result.stderr
    with pytest.raises(RuntimeError) as raised:
        plugin_validator.app(args, standalone_mode=False)
    assert raised.value is failure
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("output_format", ["github", "concise"])
def test_callback_traceback_is_guarded_independently_of_filesystem_semantics(output_format: str) -> None:
    script = """
from skilllint import plugin_validator as cli
def fail(**kwargs):
    raise RuntimeError("##[error]injected")
cli.main = fail
cli.app()
"""
    result = subprocess.run(
        [sys.executable, "-c", script, "check", "SKILL.md", "--output-format", output_format],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "Traceback" in result.stderr
    assert ("##[error]injected" in result.stderr) is (output_format != "github")
    assert ("##%5Berror]injected" in result.stderr) is (output_format == "github")
