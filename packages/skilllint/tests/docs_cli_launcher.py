"""Run the real ``skilllint`` Typer app with the docs cache redirected.

``skilllint docs`` reads and writes ``skilllint.vendor_cache.SOURCES_DIR``. That
directory resolves to the *primary checkout's* ``.claude/vendor/sources`` for an
editable install, even from a linked worktree, so a docs probe that relied on its
working directory would touch the developer's real cache. This launcher is the
existing pattern from ``test_cli_docs.py`` (patch ``SOURCES_DIR``, then call the
real ``app()``) lifted into a file so it can be linted and type-checked.

It is executed as ``python -P docs_cli_launcher.py <sources-dir> [args...]``. ``-P``
keeps this directory off ``sys.path`` so test helper modules cannot shadow
anything the CLI imports.

The environment variable named by :data:`AUTHORITY_URLS_ENV` optionally replaces
the rule registry's authority URL list, one URL per line, so ``docs
fetch-authorities`` can be exercised against loopback servers instead of the
network.
"""

from __future__ import annotations

import os
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import skilllint.cli_docs as cli_docs
import skilllint.vendor_cache as vendor_cache
from skilllint.plugin_validator import app

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

AUTHORITY_URLS_ENV = "SKILLLINT_PROBE_AUTHORITY_URLS"
PROG_NAME = "skilllint"


def _fixed_authority_urls(urls: tuple[str, ...]) -> Callable[..., Iterator[str]]:
    """Return a stand-in for ``iter_authority_urls`` that yields exactly *urls*."""

    def fixed_urls(*, unique: bool = True) -> Iterator[str]:
        del unique  # the replacement list is already the exact set to fetch
        yield from urls

    return fixed_urls


def main() -> None:
    """Patch the cache location, then hand control to the real CLI."""
    vendor_cache.SOURCES_DIR = Path(sys.argv.pop(1))
    authority_urls = os.environ.get(AUTHORITY_URLS_ENV)
    replacement = None if authority_urls is None else _fixed_authority_urls(tuple(authority_urls.splitlines()))
    sys.argv[0] = PROG_NAME
    with nullcontext() if replacement is None else patch.object(cli_docs, "iter_authority_urls", replacement):
        app(prog_name=PROG_NAME)


if __name__ == "__main__":
    main()
