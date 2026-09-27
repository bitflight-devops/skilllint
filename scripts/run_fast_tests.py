"""Run the repository's fast iterative pytest profile."""

from __future__ import annotations

import sys

import pytest


def main(args: list[str] | None = None) -> int:
    """Run pytest excluding tests explicitly marked slow.

    Args:
        args: Optional pytest arguments appended after the fast-profile marker.
            Defaults to command-line arguments.

    Returns:
        Pytest's process-style exit code.
    """
    forwarded = sys.argv[1:] if args is None else args
    return int(pytest.main(["-m", "not slow", *forwarded]))


if __name__ == "__main__":
    raise SystemExit(main())
