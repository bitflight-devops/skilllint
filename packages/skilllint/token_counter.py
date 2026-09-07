"""First-class token counting module for skilllint.

Token counts are a first-class concern for loading cost visibility. Frontmatter,
body, total skill file collections, and other contexts all expose token counts
to users so they can reason about context window impact.

This module provides:
- The bundled tiktoken cl100k_base encoding (no network access required)
- Token threshold constants (re-exported from skilllint.limits)
- Low-level token counting (count_tokens)
- File-level counting (count_file_tokens)
- Skill-level structured counting (count_skill_tokens, TokenCounts)

Design note: plugin_validator imports from this module rather than token_utils
to avoid a circular import (plugin_validator imports rules.as_series, which
imports token_counter — importing from plugin_validator back would be circular).
"""

from __future__ import annotations

import base64
import functools
import re
from dataclasses import dataclass
from importlib.resources import files
from typing import TYPE_CHECKING

import tiktoken

from skilllint.limits import BODY_TOKEN_ERROR, BODY_TOKEN_WARNING

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Bundled encoding
# ---------------------------------------------------------------------------
#
# skilllint bundles the cl100k_base BPE rank file so token counting works with
# no network access (issue #224 — sandboxed/offline agents previously failed
# here because tiktoken.get_encoding() fetches from OpenAI's blob storage on
# first use, and load_tiktoken_bpe() on a local path routes through tiktoken's
# read_file_cached(), which writes a duplicate copy into TIKTOKEN_CACHE_DIR and
# raises PermissionError when that directory is unwritable — exactly the
# sandboxed scenario this bundling exists to avoid). We instead read the
# bundled bytes directly and parse tiktoken's plaintext rank format ourselves.
#
# Source: https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken
# sha256: 223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7
# — this is tiktoken 0.14.0's own `expected_hash` for cl100k_base, asserted in
# tiktoken_ext/openai_public.py::cl100k_base(); a byte-identical match proves
# the bundled file is the genuine OpenAI artifact.

_ENCODING_NAME = "cl100k_base"
_ENCODING_DATA_PATH = "data/cl100k_base.tiktoken"

# Copied verbatim from tiktoken_ext/openai_public.py::cl100k_base() (tiktoken
# 0.14.0). Do not hand-retype: a single dropped regex alternative silently
# changes token counts on most real-world text while n_vocab still looks
# correct. See TestBundledEncodingParity in
# packages/skilllint/tests/test_bundled_tiktoken.py for the guard.
_PAT_STR = (
    r"""'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?+\p{L}++|\p{N}{1,3}+"""
    r"""| ?[^\s\p{L}\p{N}]++[\r\n]*+|\s++$|\s*[\r\n]|\s+(?!\S)|\s"""
)
_SPECIAL_TOKENS = {
    "<|endoftext|>": 100257,
    "<|fim_prefix|>": 100258,
    "<|fim_middle|>": 100259,
    "<|fim_suffix|>": 100260,
    "<|endofprompt|>": 100276,
}


def _parse_mergeable_ranks(data: bytes) -> dict[bytes, int]:
    """Parse tiktoken's plaintext BPE rank format: one ``<base64-token> <rank>`` per line.

    Mirrors ``tiktoken.load.load_tiktoken_bpe``'s own parsing loop, without the
    ``read_file_cached`` wrapper it normally runs through (that wrapper writes
    a duplicate copy into ``TIKTOKEN_CACHE_DIR`` and is not needed for a file
    already bundled with this package).

    Args:
        data: Raw bytes of a ``.tiktoken`` rank file.

    Returns:
        Mapping of decoded token bytes to their merge rank.
    """
    ranks: dict[bytes, int] = {}
    for line in data.splitlines():
        if not line:
            continue
        token, rank = line.split()
        ranks[base64.b64decode(token)] = int(rank)
    return ranks


@functools.cache
def _get_encoding() -> tiktoken.Encoding:
    """Build the cl100k_base encoding from the bundled rank file.

    Cached because construction costs ~0.5s (parsing ~100k BPE merge rules);
    ``count_tokens`` is called multiple times per scanned file.

    Returns:
        The cl100k_base :class:`tiktoken.Encoding`.
    """
    data = files("skilllint").joinpath(_ENCODING_DATA_PATH).read_bytes()
    return tiktoken.Encoding(
        name=_ENCODING_NAME,
        pat_str=_PAT_STR,
        mergeable_ranks=_parse_mergeable_ranks(data),
        special_tokens=_SPECIAL_TOKENS,
    )


# ---------------------------------------------------------------------------
# Threshold constants (canonical source: skilllint.limits)
# ---------------------------------------------------------------------------

#: Body token count at which SK006 emits a warning.
TOKEN_WARNING_THRESHOLD: int = BODY_TOKEN_WARNING

#: Body token count at which SK007 emits an error.
TOKEN_ERROR_THRESHOLD: int = BODY_TOKEN_ERROR

# ---------------------------------------------------------------------------
# Low-level counting
# ---------------------------------------------------------------------------


def count_tokens(text: str) -> int:
    """Count tokens in *text* using the cl100k_base encoding.

    A SKILL.md body is free-form prose/markdown, not a prompt being replayed
    through a model, so it must never be validated against tiktoken's own
    special-token allowlist: literal text like ``<|endoftext|>`` appearing in
    a skill body (e.g. documentation describing tiktoken itself) is ordinary
    content to count, not a special token to reject. ``disallowed_special=()``
    is tiktoken's own documented way to disable that check (see the
    suggestion in ``tiktoken.core.Encoding.encode``'s ``ValueError`` message).

    Args:
        text: Text content to count tokens in.

    Returns:
        Number of tokens in *text*.
    """
    return len(_get_encoding().encode(text, disallowed_special=()))


# ---------------------------------------------------------------------------
# Structured result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TokenCounts:
    """Token counts for a skill file broken down by section.

    Attributes:
        total: Total tokens in the full file (frontmatter + body).
        frontmatter: Tokens in the frontmatter block only.
        body: Tokens in the body (everything after the closing ``---``).
    """

    total: int
    frontmatter: int
    body: int


# ---------------------------------------------------------------------------
# Frontmatter splitter (minimal, no external deps)
# ---------------------------------------------------------------------------

_FRONTMATTER_CLOSE_RE = re.compile(r"\n---\s*\n")


def _split_frontmatter_body(content: str) -> tuple[str, str]:
    """Split *content* into (frontmatter_text, body_text).

    Returns:
        A 2-tuple ``(frontmatter, body)`` where *frontmatter* is the raw text
        inside the ``---`` delimiters (empty string if none) and *body* is
        everything after the closing ``---``.
    """
    if not content.startswith("---"):
        return "", content

    match = _FRONTMATTER_CLOSE_RE.search(content[3:])
    if match is None:
        # Unclosed frontmatter — treat whole file as frontmatter, body is empty
        return content, ""

    # content[3:] offset means match positions are relative to after the opening ---
    # match.end() points to just after the closing ---\n in the shifted string
    split_pos = 3 + match.end()
    frontmatter = content[3 : 3 + match.start()]  # between opening --- and closing ---
    body = content[split_pos:]
    return frontmatter, body


# ---------------------------------------------------------------------------
# File-level counting
# ---------------------------------------------------------------------------


def count_file_tokens(path: Path, *, body_only: bool = False) -> int | None:
    """Count tokens in a file.

    Args:
        path: Path to the file to read.
        body_only: When True, strip frontmatter and count only the body.
            This matches what ComplexityValidator measures for threshold
            comparisons.

    Returns:
        Token count (body or total), or None if the file could not be read.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    if body_only:
        _, body = _split_frontmatter_body(content)
        return count_tokens(body)

    return count_tokens(content)


# ---------------------------------------------------------------------------
# Skill-level structured counting
# ---------------------------------------------------------------------------


def count_skill_tokens(content: str) -> TokenCounts:
    """Count tokens in a skill file, split by frontmatter and body.

    Args:
        content: Full text content of the skill file (SKILL.md or similar).

    Returns:
        :class:`TokenCounts` with ``total``, ``frontmatter``, and ``body`` fields.
    """
    _frontmatter_text, body_text = _split_frontmatter_body(content)
    total = count_tokens(content)
    body = count_tokens(body_text)
    frontmatter = total - body
    return TokenCounts(total=total, frontmatter=frontmatter, body=body)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "TOKEN_ERROR_THRESHOLD",
    "TOKEN_WARNING_THRESHOLD",
    "TokenCounts",
    "count_file_tokens",
    "count_skill_tokens",
    "count_tokens",
]
