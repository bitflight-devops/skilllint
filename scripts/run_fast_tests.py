"""Run the repository's fast iterative pytest profile."""

from __future__ import annotations

import sys

import pytest

_FAST_PROFILE = ["--no-cov", "-m", "not slow"]


def _apply_fast_profile(args: list[str]) -> list[str]:
    """Append mandatory fast-profile options before pytest's option terminator."""
    try:
        separator = args.index("--")
    except ValueError:
        return [*args, *_FAST_PROFILE]
    return [*args[:separator], *_FAST_PROFILE, *args[separator:]]


def main(args: list[str] | None = None) -> int:
    """Run pytest with the repository fast profile.

    Args:
        args: Optional pytest arguments. Defaults to command-line arguments.

    Returns:
        Pytest's process-style exit code.
    """
    forwarded = sys.argv[1:] if args is None else args
    return int(pytest.main(_apply_fast_profile(forwarded)))


if __name__ == "__main__":
    raise SystemExit(main())
