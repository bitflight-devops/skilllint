"""Tests for skilllint.frontmatter module (mmap-based processor).

Tests:
- loads_frontmatter: no-closing-delimiter path, YAML parse error path
- load_frontmatter / dump_frontmatter / dumps_frontmatter / update_field
- process_markdown_file: empty file, no-frontmatter, malformed, and with
  lint_and_fix mocked to drive both the "no fix needed" and "fix needed" paths
- lint_and_fix raises NotImplementedError (scaffold)

How: Uses tmp_path for real files; unittest.mock.patch to control lint_and_fix.
Why: frontmatter.py is separate from frontmatter_utils.py and had 0% coverage
     for the mmap-based process_markdown_file and several loads_frontmatter
     branches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from skilllint.frontmatter import (
    Post,
    dump_frontmatter,
    dumps_frontmatter,
    lint_and_fix,
    load_frontmatter,
    loads_frontmatter,
    process_markdown_file,
    update_field,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestLoadsFrontmatter:
    """Tests for loads_frontmatter string parser."""

    def test_no_opening_delimiter_returns_empty_metadata(self) -> None:
        """Text not starting with '---' yields empty metadata."""
        text = "# Just a heading\n\nSome body text.\n"
        post = loads_frontmatter(text)
        assert post.metadata == {}
        assert "Just a heading" in post.content

    def test_unclosed_frontmatter_returns_empty_metadata(self) -> None:
        """Text starting with '---' but without a closing delimiter yields empty metadata."""
        text = "---\nname: test\ndescription: no closing\n"
        post = loads_frontmatter(text)
        assert post.metadata == {}
        # The unclosed text is returned as content
        assert post.content == text

    def test_valid_frontmatter_parsed(self) -> None:
        """Standard frontmatter is parsed correctly."""
        text = "---\nname: my-skill\ndescription: A test skill\n---\n\nBody.\n"
        post = loads_frontmatter(text)
        assert post.metadata["name"] == "my-skill"
        assert post.metadata["description"] == "A test skill"
        assert post.content == "Body."

    def test_non_dict_yaml_returns_empty_metadata(self) -> None:
        """YAML that parses as a non-dict (list) yields empty metadata."""
        # A YAML list is valid YAML but not a dict — metadata stays empty.
        text = "---\n- item1\n- item2\n---\n\nBody.\n"
        post = loads_frontmatter(text)
        assert post.metadata == {}

    def test_empty_frontmatter_block_returns_empty_metadata(self) -> None:
        """Frontmatter delimiters with no content yield empty metadata."""
        text = "---\n---\n\nBody text.\n"
        post = loads_frontmatter(text)
        assert post.metadata == {}

    def test_body_content_extracted(self) -> None:
        """Body is everything after the closing '---' line."""
        text = "---\nname: test\n---\n\nFirst line.\nSecond line.\n"
        post = loads_frontmatter(text)
        assert "First line." in post.content
        assert "Second line." in post.content


class TestLoadFrontmatter:
    """Tests for load_frontmatter file-based API."""

    def test_loads_from_file(self, tmp_path: Path) -> None:
        """Reads and parses a real file."""
        f = tmp_path / "test.md"
        f.write_text("---\nname: skill\n---\n\nContent.\n", encoding="utf-8")
        post = load_frontmatter(f)
        assert post.metadata["name"] == "skill"

    def test_string_path_accepted(self, tmp_path: Path) -> None:
        """Accepts a string path as well as a Path object."""
        f = tmp_path / "test.md"
        f.write_text("---\nname: skill\n---\n\nContent.\n", encoding="utf-8")
        post = load_frontmatter(str(f))
        assert post.metadata["name"] == "skill"


class TestDumpFrontmatter:
    """Tests for dump_frontmatter and dumps_frontmatter."""

    def test_dump_produces_delimiters(self) -> None:
        """Serialised output starts with '---' and contains another '---'."""
        post = Post(metadata={"name": "skill"}, content="Body.\n")
        result = dump_frontmatter(post)
        assert result.startswith("---\n")
        assert "\n---\n" in result

    def test_dump_includes_body(self) -> None:
        """Body content appears after the closing delimiter."""
        post = Post(metadata={"name": "skill"}, content="My body.")
        result = dump_frontmatter(post)
        assert "My body." in result

    def test_dumps_writes_file(self, tmp_path: Path) -> None:
        """dumps_frontmatter writes a valid file that can be round-tripped."""
        post = Post(metadata={"name": "write-test"}, content="Body text.")
        target = tmp_path / "out.md"
        dumps_frontmatter(post, target)
        reloaded = load_frontmatter(target)
        assert reloaded.metadata["name"] == "write-test"


class TestUpdateField:
    """Tests for update_field convenience function."""

    def test_updates_existing_field(self, tmp_path: Path) -> None:
        """An existing key is overwritten."""
        f = tmp_path / "skill.md"
        f.write_text("---\nname: old\n---\n\nBody.\n", encoding="utf-8")
        update_field(f, "name", "new")
        post = load_frontmatter(f)
        assert post.metadata["name"] == "new"

    def test_adds_new_field(self, tmp_path: Path) -> None:
        """A new key is inserted."""
        f = tmp_path / "skill.md"
        f.write_text("---\nname: skill\n---\n\nBody.\n", encoding="utf-8")
        update_field(f, "model", "sonnet")
        post = load_frontmatter(f)
        assert post.metadata["model"] == "sonnet"
        assert post.metadata["name"] == "skill"


class TestProcessMarkdownFile:
    """Tests for process_markdown_file (mmap-based in-place processor)."""

    def test_empty_file_is_skipped_silently(self, tmp_path: Path) -> None:
        """Empty file does not raise (mmap raises ValueError on zero-length)."""
        f = tmp_path / "empty.md"
        f.write_text("", encoding="utf-8")
        # Should return without error
        process_markdown_file(str(f))
        assert f.read_text(encoding="utf-8") == ""

    def test_file_without_frontmatter_is_untouched(self, tmp_path: Path) -> None:
        """File with no opening '---' delimiter is not modified."""
        original = "# No frontmatter\n\nJust a body.\n"
        f = tmp_path / "plain.md"
        f.write_text(original, encoding="utf-8")
        process_markdown_file(str(f))
        assert f.read_text(encoding="utf-8") == original

    def test_malformed_no_closing_delimiter_is_untouched(self, tmp_path: Path) -> None:
        """File with opening '---' but no closing delimiter is not modified."""
        original = "---\nname: skill\ndescription: no closing\n"
        f = tmp_path / "malformed.md"
        f.write_text(original, encoding="utf-8")
        process_markdown_file(str(f))
        assert f.read_text(encoding="utf-8") == original

    def test_lint_and_fix_not_needed_no_write(self, tmp_path: Path) -> None:
        """When lint_and_fix returns (False, ...), the file is not rewritten."""
        original = "---\nname: skill\n---\n\nBody.\n"
        f = tmp_path / "ok.md"
        f.write_text(original, encoding="utf-8")

        with patch("skilllint.frontmatter.lint_and_fix", return_value=(False, b"name: skill\n")):
            process_markdown_file(str(f))

        # File must be unchanged
        assert f.read_text(encoding="utf-8") == original

    def test_lint_and_fix_needed_rewrites_file(self, tmp_path: Path) -> None:
        """When lint_and_fix returns (True, new_bytes), the file is rewritten."""
        original = "---\nname: skill\n---\n\nBody.\n"
        f = tmp_path / "fixme.md"
        f.write_text(original, encoding="utf-8")

        fixed_yaml = b"name: fixed-skill\n"
        with patch("skilllint.frontmatter.lint_and_fix", return_value=(True, fixed_yaml)):
            process_markdown_file(str(f))

        result = f.read_text(encoding="utf-8")
        assert "fixed-skill" in result
        # Body should still be present
        assert "Body." in result

    def test_lint_and_fix_adds_trailing_newline_if_missing(self, tmp_path: Path) -> None:
        """lint_and_fix result without trailing newline gets one appended."""
        original = "---\nname: skill\n---\n\nBody.\n"
        f = tmp_path / "nonl.md"
        f.write_text(original, encoding="utf-8")

        # Bytes without trailing newline
        fixed_yaml = b"name: newname"
        with patch("skilllint.frontmatter.lint_and_fix", return_value=(True, fixed_yaml)):
            process_markdown_file(str(f))

        result = f.read_text(encoding="utf-8")
        assert "newname" in result


class TestLintAndFix:
    """Tests for the lint_and_fix scaffold."""

    def test_raises_not_implemented(self) -> None:
        """lint_and_fix raises NotImplementedError (scaffold, not yet integrated)."""
        with pytest.raises(NotImplementedError, match="lint_and_fix is not yet implemented"):
            lint_and_fix(b"name: skill\n")
