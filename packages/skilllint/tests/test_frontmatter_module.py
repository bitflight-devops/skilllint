"""Test frontmatter parsing, serialization, and field updates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from skilllint.frontmatter import (
    Post,
    dump_frontmatter,
    dumps_frontmatter,
    load_frontmatter,
    loads_frontmatter,
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
