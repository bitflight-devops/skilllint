"""Assert the composite Action's outputs and installed tool runtime."""

from __future__ import annotations

import os
import sys


def main() -> int:
    """Return zero only when the Action environment matches its expected contract."""
    checks = (
        ("result", "ACTION_RESULT", "EXPECTED_RESULT"),
        ("exit code", "ACTION_EXIT_CODE", "EXPECTED_EXIT_CODE"),
        ("inspected count", "ACTION_INSPECTED_COUNT", "EXPECTED_INSPECTED_COUNT"),
    )
    failures = [
        f"{name}: expected {os.environ[expected]!r}, got {os.environ[actual]!r}"
        for name, actual, expected in checks
        if os.environ[actual] != os.environ[expected]
    ]
    expected_finding = os.environ["EXPECTED_FINDING"]
    if expected_finding and expected_finding not in os.environ["ACTION_FINDINGS"].split():
        failures.append(f"finding: expected {expected_finding!r}, got {os.environ['ACTION_FINDINGS']!r}")
    expected_python = f"Python {os.environ['EXPECTED_PYTHON_VERSION']}"
    if not os.environ["ACTION_TOOL_PYTHON"].startswith(expected_python):
        failures.append(f"tool Python: expected {expected_python!r}, got {os.environ['ACTION_TOOL_PYTHON']!r}")
    expected_version = os.environ["EXPECTED_PACKAGE_VERSION"]
    if not os.environ["ACTION_TOOL_VERSION"].endswith(expected_version):
        failures.append(f"tool version: expected {expected_version!r}, got {os.environ['ACTION_TOOL_VERSION']!r}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"case={os.environ['CASE']} result={os.environ['ACTION_RESULT']} exit-code={os.environ['ACTION_EXIT_CODE']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
