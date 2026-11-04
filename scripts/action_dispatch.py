"""Select structured Action support from the installed tool, or its legacy contract."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path


def main() -> int:
    """Run the installed tool, preserving historical version pins.

    Returns:
        The selected runner exit code.
    """
    if importlib.util.find_spec("skilllint.action_runner") is not None:
        from skilllint.action_runner import run  # noqa: PLC0415 - absent in historical releases

        return run()
    legacy = Path(__file__).with_name("action_legacy.sh")
    print("Using legacy Action compatibility: structured annotations require a newer skilllint release.", flush=True)
    return subprocess.run([shutil.which("bash") or "/bin/bash", str(legacy)], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
