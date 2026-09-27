"""Run the repository's fast iterative pytest profile."""

from __future__ import annotations

import sys

import pytest


def _reject_marker_override(args: list[str]) -> None:
    """Reject caller marker selection that could override the fast profile."""
    for arg in args:
        if arg in {"-m", "--markexpr"} or (arg.startswith("-m") and arg != "-m") or arg.startswith("--markexpr="):
            raise ValueError("the fast test profile owns pytest marker selection; do not pass -m/--markexpr")


def main(args: list[str] | None = None) -> int:
    """Run pytest excluding tests explicitly marked slow.

    Args:
        args: Optional pytest arguments appended after the fast-profile marker.
            Defaults to command-line arguments.

    Returns:
        Pytest's process-style exit code.
    """
    forwarded = sys.argv[1:] if args is None else args
    _reject_marker_override(forwarded)
    return int(pytest.main(["-m", "not slow", *forwarded]))


if __name__ == "__main__":
    raise SystemExit(main())
