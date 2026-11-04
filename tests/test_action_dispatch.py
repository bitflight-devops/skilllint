"""Capability dispatch must use the requested installed package, not checkout code."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).parents[1] / "scripts/action_dispatch.py"
SPEC = importlib.util.spec_from_file_location("action_dispatch", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
DISPATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DISPATCH)


def test_structured_dispatch_never_runs_legacy_shell(mocker):
    mocker.patch.object(DISPATCH.importlib.util, "find_spec", return_value=object())
    structured = mocker.patch("skilllint.action_runner.run", return_value=1)
    shell = mocker.patch.object(DISPATCH.subprocess, "run")
    assert DISPATCH.main() == 1
    structured.assert_called_once_with()
    shell.assert_not_called()


def test_historical_pin_dispatches_to_preserved_legacy_runner(mocker, capsys):
    mocker.patch.object(DISPATCH.importlib.util, "find_spec", return_value=None)
    shell = mocker.patch.object(DISPATCH.subprocess, "run", return_value=SimpleNamespace(returncode=2))
    assert DISPATCH.main() == 2
    assert Path(shell.call_args.args[0][1]) == SCRIPT.with_name("action_legacy.sh")
    assert "legacy Action compatibility" in capsys.readouterr().out
