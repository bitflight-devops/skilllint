"""Tests for skilllint.token_utils backward-compatibility shim.

Tests:
- Re-exported symbols are the same objects as in token_counter
- All three public names are importable from token_utils

How: Direct import and identity checks.
Why: token_utils is a shim for existing callers; if re-exports break,
     downstream code silently uses wrong thresholds or functions.
"""

from __future__ import annotations

from skilllint import token_counter, token_utils


class TestTokenUtilsReexports:
    """Tests that token_utils correctly re-exports token_counter symbols."""

    def test_count_tokens_is_same_object(self) -> None:
        """token_utils.count_tokens is the same callable as token_counter.count_tokens."""
        assert token_utils.count_tokens is token_counter.count_tokens

    def test_token_warning_threshold_matches(self) -> None:
        """TOKEN_WARNING_THRESHOLD has the same value as token_counter's."""
        assert token_utils.TOKEN_WARNING_THRESHOLD == token_counter.TOKEN_WARNING_THRESHOLD

    def test_token_error_threshold_matches(self) -> None:
        """TOKEN_ERROR_THRESHOLD has the same value as token_counter's."""
        assert token_utils.TOKEN_ERROR_THRESHOLD == token_counter.TOKEN_ERROR_THRESHOLD

    def test_all_public_names_in_all(self) -> None:
        """__all__ declares the three public re-exports."""
        assert "count_tokens" in token_utils.__all__
        assert "TOKEN_WARNING_THRESHOLD" in token_utils.__all__
        assert "TOKEN_ERROR_THRESHOLD" in token_utils.__all__

    def test_count_tokens_callable(self) -> None:
        """count_tokens imported via token_utils produces correct results."""
        result = token_utils.count_tokens("hello world")
        assert isinstance(result, int)
        assert result > 0
