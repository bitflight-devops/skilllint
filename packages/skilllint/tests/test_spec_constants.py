"""Tests for skilllint._spec_constants module.

Tests:
- Constant values are correct per the agentskills.io specification
- Constants are importable and accessible

How: Direct attribute inspection.
Why: Constant values drive validation rules; regressions here cause silent
     mis-validation without test coverage to catch them.
"""

from __future__ import annotations

from skilllint._spec_constants import (
    MAX_COMPATIBILITY_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    MIN_DESCRIPTION_LENGTH,
)


class TestSpecConstants:
    """Tests for the auto-generated spec constants."""

    def test_max_name_length(self) -> None:
        """MAX_NAME_LENGTH matches agentskills.io spec value of 64."""
        assert MAX_NAME_LENGTH == 64

    def test_max_description_length(self) -> None:
        """MAX_DESCRIPTION_LENGTH matches agentskills.io spec value of 1024."""
        assert MAX_DESCRIPTION_LENGTH == 1024

    def test_min_description_length(self) -> None:
        """MIN_DESCRIPTION_LENGTH matches agentskills.io spec value of 1."""
        assert MIN_DESCRIPTION_LENGTH == 1

    def test_max_compatibility_length(self) -> None:
        """MAX_COMPATIBILITY_LENGTH matches agentskills.io spec value of 500."""
        assert MAX_COMPATIBILITY_LENGTH == 500

    def test_constants_are_integers(self) -> None:
        """All spec constants are integer values."""
        assert isinstance(MAX_NAME_LENGTH, int)
        assert isinstance(MAX_DESCRIPTION_LENGTH, int)
        assert isinstance(MIN_DESCRIPTION_LENGTH, int)
        assert isinstance(MAX_COMPATIBILITY_LENGTH, int)

    def test_description_range_is_sane(self) -> None:
        """MIN_DESCRIPTION_LENGTH < MAX_DESCRIPTION_LENGTH."""
        assert MIN_DESCRIPTION_LENGTH < MAX_DESCRIPTION_LENGTH
