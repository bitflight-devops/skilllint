"""Tests for the bundled cl100k_base tiktoken rank file (issue #224).

These tests run fully offline: they never call ``tiktoken.get_encoding`` (which
fetches ranks from OpenAI's blob storage, or requires a warm local cache) or
touch ``TIKTOKEN_CACHE_DIR`` / ``DATA_GYM_CACHE_DIR``. The parity check against
tiktoken's own network-backed encoding lives in
``TestEncodingConsistency.test_encoding_matches_cl100k_base`` in
test_token_counting.py, guarded to skip when that oracle is unreachable.
"""

from __future__ import annotations

import hashlib
from importlib.resources import files

import pytest

from skilllint.token_counter import _ENCODING_DATA_PATH, count_tokens

# tiktoken 0.14.0's own `expected_hash` for cl100k_base, asserted in
# tiktoken_ext/openai_public.py::cl100k_base() — itself OpenAI's published
# integrity hash for this file. A byte-identical match proves the bundled
# copy is the genuine artifact, independent of file mtimes or line endings.
_EXPECTED_SHA256 = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"

# Fixed strings with token counts recorded from tiktoken.get_encoding("cl100k_base")
# (tiktoken 0.14.0), independently of skilllint's own bundled loader. This is the
# offline guard against a mistyped pat_str or special_tokens table: a dropped
# regex alternative changes counts while n_vocab still looks correct, so a
# vocab-size check alone would not catch it.
_GOLDEN_COUNTS: list[tuple[str, int]] = [
    ("", 0),
    ("hello world", 2),
    ("Hello world! This is a test of token counting with various symbols: @#$%^&*()", 20),
    ("The quick brown fox jumps over the lazy dog.", 10),
    ("世界 Здравствуй مرحبا 🚀", 16),
    ("# Heading\n\nSome *markdown* body with ```code``` and a [link](https://example.com).\n", 22),
    ("1234567890 numbers 42 3.14159", 12),
    ("word " * 50, 51),
]


class TestBundledEncodingData:
    """Tests for the bundled rank file itself, independent of any parsing."""

    def test_bundled_encoding_data_matches_published_hash(self) -> None:
        """The bundled file is byte-identical to OpenAI's published cl100k_base.tiktoken."""
        raw_bytes = files("skilllint").joinpath(_ENCODING_DATA_PATH).read_bytes()
        assert hashlib.sha256(raw_bytes).hexdigest() == _EXPECTED_SHA256

    def test_bundled_encoding_readable_via_importlib_resources(self) -> None:
        """The bundled file resolves via importlib.resources, not a __file__-relative path.

        Mirrors test_bundled_schema.py's resource-loading proof: this must work
        under zipimport (an installed wheel), not just a repo checkout.
        """
        raw_bytes = files("skilllint").joinpath(_ENCODING_DATA_PATH).read_bytes()
        assert raw_bytes, "bundled cl100k_base.tiktoken must not be empty"


class TestGoldenTokenCounts:
    """Regression guard: bundled encoding must reproduce known-good counts."""

    @pytest.mark.parametrize(("text", "expected"), _GOLDEN_COUNTS)
    def test_count_tokens_matches_recorded_count(self, text: str, expected: int) -> None:
        """count_tokens(text) matches the count recorded from tiktoken's own encoding."""
        assert count_tokens(text) == expected
