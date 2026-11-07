"""Link masking preserves every character offset and newline."""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

from skilllint.rules.lk_series import _strip_code_blocks


@given(body=st.text(alphabet=st.characters(blacklist_characters="`~")))
def test_fenced_mask_preserves_unicode_offsets_and_line_endings(body: str) -> None:
    """Mask arbitrary Unicode without changing CR, LF, or surrounding text."""
    fenced = f"```text\n{body}\n```"
    expected = "".join(char if char in "\r\n" else " " for char in fenced)
    assert _strip_code_blocks(f"Before\n{fenced}\nAfter") == f"Before\n{expected}\nAfter"


@pytest.mark.parametrize("masked", ["`😀 é\t`", "<!-- 😀\r\né\rtext\n -->", "`plain`", "<!-- -->"])
def test_inline_and_comment_masks_preserve_source_offsets(masked: str) -> None:
    """Inline code and comments keep the same offset-preserving contract."""
    suffix = " [visible](./target.md)"
    expected = "".join(char if char in "\r\n" else " " for char in masked)
    assert _strip_code_blocks(masked + suffix) == expected + suffix
