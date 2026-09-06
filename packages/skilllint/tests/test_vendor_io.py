"""Tests for skilllint.vendor_io — shared low-level I/O utilities.

Tests:
- Hash utilities: sha256_hex, sha256_hex_short
- File I/O: read_text_or_none, write_json, load_json_or_none
- HTTP: fetch_url_text (mocked httpx.Client)
- Sidecar: write_sidecar, load_sidecar
- Timestamp: utc_now_iso
- Directory constants: PROJECT_ROOT, VENDOR_DIR, SOURCES_DIR
- Worktree detection: _shared_checkout_root

How: Unit tests with tmp_path for file operations, mocker.patch for httpx,
     known-input/known-output checks for hash functions, real `git init` /
     `git worktree add` subprocess calls for worktree-detection tests.
Why: vendor_io is the foundation layer used by all vendor documentation scripts;
     correctness here is required for cache integrity and offline-first behaviour.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest

from skilllint.vendor_io import (
    PROJECT_ROOT,
    SOURCES_DIR,
    VENDOR_DIR,
    _shared_checkout_root,
    fetch_url_text,
    load_json_or_none,
    load_sidecar,
    read_text_or_none,
    sha256_hex,
    sha256_hex_short,
    utc_now_iso,
    write_json,
    write_sidecar,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Hash utilities
# ---------------------------------------------------------------------------


class TestSha256Hex:
    """Tests for sha256_hex — full 64-character hex digest."""

    def test_sha256_hex_known_input_returns_known_hash(self) -> None:
        """sha256_hex of b'test' produces the expected 64-char hex digest.

        Tests: sha256_hex
        How: Pass the string 'test', compare against independently computed value.
        Why: The sidecar integrity check relies on this producing a deterministic
             hash; any regression breaks drift detection across all vendor scripts.
        """
        # Arrange
        text = "test"
        expected = hashlib.sha256(b"test").hexdigest()

        # Act
        result = sha256_hex(text)

        # Assert
        assert result == expected
        assert len(result) == 64

    def test_sha256_hex_encodes_as_utf8(self) -> None:
        """sha256_hex encodes the string as UTF-8 before hashing.

        Tests: sha256_hex UTF-8 encoding
        How: Compare result for a multi-byte unicode string against manual encoding.
        Why: Consistent encoding is required for hash reproducibility across platforms.
        """
        # Arrange
        text = "héllo"
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()

        # Act
        result = sha256_hex(text)

        # Assert
        assert result == expected

    def test_sha256_hex_different_inputs_produce_different_hashes(self) -> None:
        """sha256_hex produces distinct digests for distinct inputs.

        Tests: sha256_hex collision resistance
        How: Hash two different strings, assert inequality.
        Why: Drift detection depends on hash distinctness; identical hashes for
             different content would suppress alerts.
        """
        # Arrange / Act
        hash_a = sha256_hex("content_a")
        hash_b = sha256_hex("content_b")

        # Assert
        assert hash_a != hash_b


class TestSha256HexShort:
    """Tests for sha256_hex_short — truncated digest."""

    def test_sha256_hex_short_default_length_is_12(self) -> None:
        """sha256_hex_short with no length arg returns 12 characters.

        Tests: sha256_hex_short default truncation
        How: Call with a known string, assert result length is 12.
        Why: The default length is a documented API contract used in file naming.
        """
        # Arrange
        text = "test"

        # Act
        result = sha256_hex_short(text)

        # Assert
        assert len(result) == 12

    def test_sha256_hex_short_is_prefix_of_full_hash(self) -> None:
        """sha256_hex_short result is a prefix of the full sha256_hex result.

        Tests: sha256_hex_short relationship to sha256_hex
        How: Compare short result against the first N chars of the full digest.
        Why: Short hash must be a deterministic prefix, not an independent value.
        """
        # Arrange
        text = "test"

        # Act
        full = sha256_hex(text)
        short = sha256_hex_short(text)

        # Assert
        assert full.startswith(short)

    def test_sha256_hex_short_custom_length(self) -> None:
        """sha256_hex_short respects the length keyword argument.

        Tests: sha256_hex_short with custom length
        How: Pass length=8, assert result has exactly 8 characters.
        Why: Callers choose their own digest length; the function must honour it.
        """
        # Arrange / Act
        result = sha256_hex_short("hello", length=8)

        # Assert
        assert len(result) == 8
        assert sha256_hex("hello").startswith(result)

    def test_sha256_hex_short_known_value(self) -> None:
        """sha256_hex_short of 'test' with length=12 equals first 12 chars of full hash.

        Tests: sha256_hex_short exact output
        How: Hard-code the expected prefix derived from the known full digest.
        Why: Pinning a specific value catches accidental changes to encoding or
             the truncation implementation.
        """
        # Arrange
        expected = hashlib.sha256(b"test").hexdigest()[:12]

        # Act
        result = sha256_hex_short("test", length=12)

        # Assert
        assert result == expected


# ---------------------------------------------------------------------------
# File I/O utilities
# ---------------------------------------------------------------------------


class TestReadTextOrNone:
    """Tests for read_text_or_none — safe file reader."""

    def test_read_text_or_none_existing_file_returns_content(self, tmp_path: Path) -> None:
        """read_text_or_none returns file content for an existing file.

        Tests: read_text_or_none happy path
        How: Write a known string to a tmp file, assert the return value matches.
        Why: All cache reading goes through this helper; wrong content breaks
             downstream SHA-256 comparisons.
        """
        # Arrange
        expected = "hello vendor\n"
        test_file = tmp_path / "doc.md"
        test_file.write_text(expected, encoding="utf-8")

        # Act
        result = read_text_or_none(test_file)

        # Assert
        assert result == expected

    def test_read_text_or_none_missing_file_returns_none(self, tmp_path: Path) -> None:
        """read_text_or_none returns None when the file does not exist.

        Tests: read_text_or_none missing file
        How: Pass a path to a nonexistent file, assert None is returned.
        Why: Callers use the None return to distinguish cache miss from empty content.
        """
        # Arrange
        missing = tmp_path / "nonexistent.md"

        # Act
        result = read_text_or_none(missing)

        # Assert
        assert result is None


class TestWriteJson:
    """Tests for write_json — JSON serialiser with indent=2 and trailing newline."""

    def test_write_json_creates_parent_directories(self, tmp_path: Path) -> None:
        """write_json creates missing parent directories automatically.

        Tests: write_json parent dir creation
        How: Pass a path whose parents do not exist, then assert the file was created.
        Why: Vendor scripts write into nested directories that may not exist yet.
        """
        # Arrange
        nested = tmp_path / "a" / "b" / "c" / "data.json"
        data = {"key": "value"}

        # Act
        write_json(nested, data)

        # Assert
        assert nested.exists()

    def test_write_json_uses_indent_2(self, tmp_path: Path) -> None:
        """write_json produces output formatted with 2-space indentation.

        Tests: write_json indent format
        How: Write a dict, read back the raw text, assert two-space indent is present.
        Why: Human-readable JSON with consistent indentation is the documented contract.
        """
        # Arrange
        target = tmp_path / "output.json"
        data = {"name": "test"}

        # Act
        write_json(target, data)
        raw = target.read_text(encoding="utf-8")

        # Assert
        assert '  "name"' in raw  # two-space indent

    def test_write_json_appends_trailing_newline(self, tmp_path: Path) -> None:
        """write_json appends a trailing newline after the JSON body.

        Tests: write_json trailing newline
        How: Write data, read raw text, assert it ends with newline.
        Why: POSIX text file convention; diff tools and git show cleaner output.
        """
        # Arrange
        target = tmp_path / "output.json"
        data = {"x": 1}

        # Act
        write_json(target, data)
        raw = target.read_text(encoding="utf-8")

        # Assert
        assert raw.endswith("\n")

    def test_write_json_produces_valid_json(self, tmp_path: Path) -> None:
        """write_json output is valid JSON that round-trips correctly.

        Tests: write_json JSON validity
        How: Write a dict, parse the file back with json.loads, compare to original.
        Why: The sidecar and cache files must be machine-readable; invalid JSON
             causes load_json_or_none to silently return None.
        """
        # Arrange
        target = tmp_path / "round_trip.json"
        original: dict[str, int | str] = {"count": 42, "label": "hello"}

        # Act
        write_json(target, original)
        parsed = json.loads(target.read_text(encoding="utf-8"))

        # Assert
        assert parsed == original


class TestLoadJsonOrNone:
    """Tests for load_json_or_none — safe JSON loader."""

    def test_load_json_or_none_valid_file_returns_dict(self, tmp_path: Path) -> None:
        """load_json_or_none returns parsed dict for a valid JSON file.

        Tests: load_json_or_none happy path
        How: Write valid JSON, call load_json_or_none, assert dict returned.
        Why: Sidecar loading depends on this returning the dict, not None.
        """
        # Arrange
        path = tmp_path / "valid.json"
        data = {"url": "https://example.com", "sha256": "abc123"}
        path.write_text(json.dumps(data), encoding="utf-8")

        # Act
        result = load_json_or_none(path)

        # Assert
        assert result == data

    def test_load_json_or_none_missing_file_returns_none(self, tmp_path: Path) -> None:
        """load_json_or_none returns None when file does not exist.

        Tests: load_json_or_none missing file
        How: Pass path to non-existent file, assert None.
        Why: Cache code branches on None to detect missing sidecars.
        """
        # Arrange
        missing = tmp_path / "no_such_file.json"

        # Act
        result = load_json_or_none(missing)

        # Assert
        assert result is None

    def test_load_json_or_none_corrupt_json_returns_none(self, tmp_path: Path) -> None:
        """load_json_or_none returns None for a file containing invalid JSON.

        Tests: load_json_or_none corrupt file
        How: Write non-JSON bytes to a file, assert None is returned.
        Why: A partially-written or truncated sidecar must be treated as absent,
             not raise an exception that propagates to callers.
        """
        # Arrange
        corrupt = tmp_path / "corrupt.json"
        corrupt.write_text("{ this is not json }", encoding="utf-8")

        # Act
        result = load_json_or_none(corrupt)

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# HTTP utilities
# ---------------------------------------------------------------------------


class TestFetchUrlText:
    """Tests for fetch_url_text — HTTP fetcher backed by httpx.Client."""

    def test_fetch_url_text_success_returns_response_text(self, mocker: MockerFixture) -> None:
        """fetch_url_text returns the response body text on a successful request.

        Tests: fetch_url_text happy path
        How: Mock httpx.Client context manager to return a response with known text.
        Why: All vendor page fetching goes through this; correct text passthrough
             is required for content hashing and drift detection.
        """
        # Arrange
        expected_text = "# Documentation\n\nSome content."
        mock_response = mocker.Mock()
        mock_response.text = expected_text
        mock_response.raise_for_status = mocker.Mock()

        mock_client = mocker.Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = mocker.Mock(return_value=mock_client)
        mock_client.__exit__ = mocker.Mock(return_value=False)

        mocker.patch("skilllint.vendor_io.httpx.Client", return_value=mock_client)

        # Act
        result = fetch_url_text("https://example.com/docs.md")

        # Assert
        assert result == expected_text

    def test_fetch_url_text_non_2xx_raises_http_status_error(self, mocker: MockerFixture) -> None:
        """fetch_url_text raises HTTPStatusError for non-2xx responses.

        Tests: fetch_url_text HTTP error handling
        How: Make raise_for_status raise HTTPStatusError, assert it propagates.
        Why: Callers depend on this exception to detect fetch failures and fall
             back to cached copies.
        """
        # Arrange
        mock_response = mocker.Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=mocker.Mock(), response=mocker.Mock()
        )

        mock_client = mocker.Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = mocker.Mock(return_value=mock_client)
        mock_client.__exit__ = mocker.Mock(return_value=False)

        mocker.patch("skilllint.vendor_io.httpx.Client", return_value=mock_client)

        # Act / Assert
        with pytest.raises(httpx.HTTPStatusError):
            fetch_url_text("https://example.com/missing.md")

    def test_fetch_url_text_empty_body_raises_value_error(self, mocker: MockerFixture) -> None:
        """fetch_url_text raises ValueError when the response body is empty.

        Tests: fetch_url_text empty response guard
        How: Return a response with empty text, assert ValueError is raised.
        Why: An empty response indicates a bad fetch; writing it to disk would
             corrupt the cache with zero-byte content.
        """
        # Arrange
        mock_response = mocker.Mock()
        mock_response.text = ""
        mock_response.raise_for_status = mocker.Mock()

        mock_client = mocker.Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = mocker.Mock(return_value=mock_client)
        mock_client.__exit__ = mocker.Mock(return_value=False)

        mocker.patch("skilllint.vendor_io.httpx.Client", return_value=mock_client)

        # Act / Assert
        with pytest.raises(ValueError, match="Empty response body"):
            fetch_url_text("https://example.com/empty.md")

    def test_fetch_url_text_passes_timeout_to_client(self, mocker: MockerFixture) -> None:
        """fetch_url_text constructs the httpx.Client with the given timeout.

        Tests: fetch_url_text timeout forwarding
        How: Capture the kwargs passed to httpx.Client, assert timeout matches.
        Why: Timeout control prevents vendor scripts from hanging indefinitely
             on slow or unresponsive hosts.
        """
        # Arrange
        mock_response = mocker.Mock()
        mock_response.text = "content"
        mock_response.raise_for_status = mocker.Mock()

        mock_client = mocker.Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = mocker.Mock(return_value=mock_client)
        mock_client.__exit__ = mocker.Mock(return_value=False)

        patched = mocker.patch("skilllint.vendor_io.httpx.Client", return_value=mock_client)

        # Act
        fetch_url_text("https://example.com/page.md", timeout=10.0)

        # Assert
        patched.assert_called_once_with(timeout=10.0, follow_redirects=True)


# ---------------------------------------------------------------------------
# Sidecar utilities
# ---------------------------------------------------------------------------


class TestWriteSidecar:
    """Tests for write_sidecar — .meta.json provenance recorder."""

    def test_write_sidecar_creates_meta_json_alongside_file(self, tmp_path: Path) -> None:
        """write_sidecar creates a .meta.json file next to the given path.

        Tests: write_sidecar path convention
        How: Call write_sidecar for a .md file, assert .meta.json exists.
        Why: The .meta.json convention is relied upon by load_sidecar and
             verify_integrity; a different extension would silently break both.
        """
        # Arrange
        md_path = tmp_path / "settings-2026-03-23-1400.md"
        md_path.write_text("# Settings\n", encoding="utf-8")

        # Act
        sidecar_path = write_sidecar(md_path, url="https://example.com/settings.md", content="# Settings\n")

        # Assert
        assert sidecar_path == md_path.with_suffix(".meta.json")
        assert sidecar_path.exists()

    def test_write_sidecar_contains_url(self, tmp_path: Path) -> None:
        """write_sidecar records the source URL in the sidecar.

        Tests: write_sidecar url field
        How: Write a sidecar, parse it, assert url matches what was passed.
        Why: Provenance tracking requires the exact source URL to be stored.
        """
        # Arrange
        md_path = tmp_path / "doc.md"
        url = "https://docs.example.com/page.md"

        # Act
        write_sidecar(md_path, url=url, content="content")
        sidecar = json.loads(md_path.with_suffix(".meta.json").read_text(encoding="utf-8"))

        # Assert
        assert sidecar["url"] == url

    def test_write_sidecar_contains_fetched_at(self, tmp_path: Path) -> None:
        """write_sidecar records a fetched_at ISO timestamp in the sidecar.

        Tests: write_sidecar fetched_at field
        How: Write a sidecar, parse it, assert fetched_at is an ISO string.
        Why: TTL logic in vendor_cache reads fetched_at to determine cache age.
        """
        # Arrange
        md_path = tmp_path / "doc.md"

        # Act
        write_sidecar(md_path, url="https://example.com/", content="text")
        sidecar = json.loads(md_path.with_suffix(".meta.json").read_text(encoding="utf-8"))

        # Assert
        assert "fetched_at" in sidecar
        # Must be parseable as ISO 8601
        datetime.fromisoformat(sidecar["fetched_at"])

    def test_write_sidecar_contains_sha256(self, tmp_path: Path) -> None:
        """write_sidecar records the SHA-256 digest of the content.

        Tests: write_sidecar sha256 field
        How: Write a sidecar with known content, assert sha256 matches expected.
        Why: verify_integrity compares this field against the current file hash.
        """
        # Arrange
        md_path = tmp_path / "doc.md"
        content = "# Test Content\n"
        expected_sha = sha256_hex(content)

        # Act
        write_sidecar(md_path, url="https://example.com/", content=content)
        sidecar = json.loads(md_path.with_suffix(".meta.json").read_text(encoding="utf-8"))

        # Assert
        assert sidecar["sha256"] == expected_sha

    def test_write_sidecar_contains_byte_count(self, tmp_path: Path) -> None:
        """write_sidecar records the UTF-8 byte count of the content.

        Tests: write_sidecar byte_count field
        How: Write a sidecar with known content, assert byte_count is correct.
        Why: verify_integrity uses byte_count as a secondary integrity signal.
        """
        # Arrange
        md_path = tmp_path / "doc.md"
        content = "hello"
        expected_bytes = len(content.encode("utf-8"))

        # Act
        write_sidecar(md_path, url="https://example.com/", content=content)
        sidecar = json.loads(md_path.with_suffix(".meta.json").read_text(encoding="utf-8"))

        # Assert
        assert sidecar["byte_count"] == expected_bytes


class TestLoadSidecar:
    """Tests for load_sidecar — .meta.json loader."""

    def test_load_sidecar_valid_sidecar_returns_dict(self, tmp_path: Path) -> None:
        """load_sidecar returns the parsed dict for a valid .meta.json file.

        Tests: load_sidecar happy path
        How: Write a .meta.json file, call load_sidecar for the .md path.
        Why: Cache freshness checks depend on reading back the stored fetched_at value.
        """
        # Arrange
        md_path = tmp_path / "page.md"
        sidecar_data = {
            "url": "https://example.com/",
            "fetched_at": "2026-03-23T14:00:00+00:00",
            "sha256": "abc",
            "byte_count": 3,
        }
        md_path.with_suffix(".meta.json").write_text(json.dumps(sidecar_data), encoding="utf-8")

        # Act
        result = load_sidecar(md_path)

        # Assert
        assert result == sidecar_data

    def test_load_sidecar_missing_sidecar_returns_none(self, tmp_path: Path) -> None:
        """load_sidecar returns None when no .meta.json file exists.

        Tests: load_sidecar missing file
        How: Call load_sidecar for a path with no corresponding .meta.json.
        Why: Cache code branches on None to handle the no-sidecar case.
        """
        # Arrange
        md_path = tmp_path / "page_no_sidecar.md"

        # Act
        result = load_sidecar(md_path)

        # Assert
        assert result is None

    def test_load_sidecar_corrupt_sidecar_returns_none(self, tmp_path: Path) -> None:
        """load_sidecar returns None when the .meta.json contains invalid JSON.

        Tests: load_sidecar corrupt file
        How: Write non-JSON to the .meta.json file, assert None is returned.
        Why: A corrupt sidecar is treated as absent, preventing parse errors
             from propagating to callers.
        """
        # Arrange
        md_path = tmp_path / "page.md"
        md_path.with_suffix(".meta.json").write_text("NOT JSON", encoding="utf-8")

        # Act
        result = load_sidecar(md_path)

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# UTC timestamp
# ---------------------------------------------------------------------------


class TestUtcNowIso:
    """Tests for utc_now_iso — ISO 8601 UTC timestamp generator."""

    def test_utc_now_iso_returns_parseable_string(self) -> None:
        """utc_now_iso returns a string parseable by datetime.fromisoformat.

        Tests: utc_now_iso return type and format
        How: Call the function, pass result to datetime.fromisoformat.
        Why: All sidecar fetched_at values must be parseable; an unparseable
             value causes vendor_cache to treat files as infinitely stale.
        """
        # Arrange / Act
        result = utc_now_iso()

        # Assert — no exception means parseable
        parsed = datetime.fromisoformat(result)
        assert parsed is not None

    def test_utc_now_iso_contains_timezone_info(self) -> None:
        """utc_now_iso returns a timezone-aware datetime string.

        Tests: utc_now_iso timezone awareness
        How: Parse the result, assert tzinfo is not None.
        Why: Age calculations in vendor_cache subtract an aware datetime from now(UTC);
             a naive timestamp would raise a TypeError.
        """
        # Arrange / Act
        result = utc_now_iso()
        parsed = datetime.fromisoformat(result)

        # Assert
        assert parsed.tzinfo is not None

    def test_utc_now_iso_is_utc(self) -> None:
        """utc_now_iso returns a UTC timestamp (offset +00:00).

        Tests: utc_now_iso UTC zone
        How: Parse result, check UTC offset is zero.
        Why: All TTL age comparisons use UTC; a non-UTC timestamp would cause
             incorrect age calculations for machines in other timezones.
        """
        # Arrange / Act
        result = utc_now_iso()
        parsed = datetime.fromisoformat(result)

        # Assert
        offset = parsed.utcoffset()
        assert offset is not None
        assert offset.total_seconds() == 0


# ---------------------------------------------------------------------------
# Directory constants
# ---------------------------------------------------------------------------


class TestDirectoryConstants:
    """Tests for PROJECT_ROOT, VENDOR_DIR, and SOURCES_DIR path constants."""

    def test_project_root_contains_pyproject_toml(self) -> None:
        """PROJECT_ROOT is the repository root — pyproject.toml must exist there.

        Tests: PROJECT_ROOT accuracy
        How: Assert that PROJECT_ROOT / pyproject.toml exists.
        Why: Many scripts resolve paths relative to PROJECT_ROOT; if it points
             to the wrong directory, all downstream paths are wrong.
        """
        # Arrange / Act / Assert
        assert (PROJECT_ROOT / "pyproject.toml").exists()

    def test_vendor_dir_is_shared_checkout_root_claude_vendor(self) -> None:
        """VENDOR_DIR is _shared_checkout_root(PROJECT_ROOT) / '.claude' / 'vendor'.

        Tests: VENDOR_DIR path derivation
        How: Compare VENDOR_DIR against the expected composed path, deriving the
             base via _shared_checkout_root rather than assuming PROJECT_ROOT
             directly — VENDOR_DIR is redirected to the primary checkout root
             when running inside a linked git worktree (see issue #116).
        Why: Scripts must write into .claude/vendor; an incorrect constant
             would scatter files elsewhere in the repo, or make a worktree's
             cache invisible to the primary checkout and vice versa.
        """
        # Arrange / Act / Assert
        assert _shared_checkout_root(PROJECT_ROOT) / ".claude" / "vendor" == VENDOR_DIR

    def test_sources_dir_is_under_vendor_dir(self) -> None:
        """SOURCES_DIR is VENDOR_DIR / 'sources'.

        Tests: SOURCES_DIR path derivation
        How: Compare SOURCES_DIR against the expected composed path.
        Why: Cache files must land in .claude/vendor/sources; a wrong path
             breaks all cache reads and writes.
        """
        # Arrange / Act / Assert
        assert SOURCES_DIR == VENDOR_DIR / "sources"


# ---------------------------------------------------------------------------
# Worktree detection
# ---------------------------------------------------------------------------


def _run_git(args: list[str], *, cwd: Path) -> None:
    """Run a git command, raising with captured output on failure.

    Args:
        args: Arguments to pass to ``git`` (excluding the ``git`` executable itself).
        cwd: Working directory to run the command in.

    Raises:
        subprocess.CalledProcessError: If the git command exits non-zero.
    """
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo_with_commit(repo_dir: Path) -> None:
    """Create a git repository at *repo_dir* with a single commit.

    Args:
        repo_dir: Directory to initialise as a git repository. Must already exist.
    """
    _run_git(["init", "--initial-branch=main"], cwd=repo_dir)
    _run_git(["config", "user.email", "test@example.com"], cwd=repo_dir)
    _run_git(["config", "user.name", "Test"], cwd=repo_dir)
    (repo_dir / "file.txt").write_text("content\n", encoding="utf-8")
    _run_git(["add", "."], cwd=repo_dir)
    _run_git(["commit", "-m", "initial commit"], cwd=repo_dir)


class TestSharedCheckoutRoot:
    """Tests for _shared_checkout_root — linked-worktree primary-checkout detection.

    Uses real ``git init`` / ``git worktree add`` subprocess calls rather than
    mocks, per the issue #116 fix requirement that detection be validated
    against actual git-managed filesystem shapes, not simulated behaviour.
    """

    def test_non_git_directory_returns_start_unchanged(self, tmp_path: Path) -> None:
        """A directory with no .git entry at all returns start unchanged.

        Tests: _shared_checkout_root with no repository present
        How: Pass a plain empty directory with no .git file or directory.
        Why: An installed wheel with no .git anywhere above it must resolve
             VENDOR_DIR under itself, not raise or require git.
        """
        # Arrange
        plain_dir = tmp_path / "no_repo"
        plain_dir.mkdir()

        # Act
        result = _shared_checkout_root(plain_dir)

        # Assert
        assert result == plain_dir

    def test_plain_checkout_returns_start_unchanged(self, tmp_path: Path) -> None:
        """A plain checkout (.git is a directory) returns start unchanged.

        Tests: _shared_checkout_root with a plain (non-worktree) checkout
        How: git init a real repository, assert the function returns its own root.
        Why: The overwhelming majority of clones are plain checkouts; this must
             be a complete no-op for them, preserving today's behaviour exactly.
        """
        # Arrange
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo_with_commit(repo)

        # Act
        result = _shared_checkout_root(repo)

        # Assert
        assert result == repo

    def test_linked_worktree_returns_primary_checkout_root(self, tmp_path: Path) -> None:
        """A linked worktree (git worktree add) resolves to the primary checkout root.

        Tests: _shared_checkout_root with a real linked worktree
        How: git init a repo with a commit, `git worktree add` a second working
             tree, assert _shared_checkout_root(worktree) == primary repo root.
        Why: This is the exact issue #116 scenario — a linked worktree's
             gitignored .claude/vendor/ must resolve to the primary checkout's
             cache, not its own empty directory.
        """
        # Arrange
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo_with_commit(repo)
        worktree = tmp_path / "linked-worktree"
        _run_git(["worktree", "add", str(worktree)], cwd=repo)

        # Act
        result = _shared_checkout_root(worktree)

        # Assert
        assert result == repo.resolve()

    def test_submodule_shape_returns_start_unchanged(self, tmp_path: Path) -> None:
        """A submodule's .git file (gitdir with no commondir) returns start unchanged.

        Tests: _shared_checkout_root defensive fallback for the submodule shape
        How: Construct the filesystem shape directly (a .git file pointing at a
             gitdir that lacks a commondir file) — the same shape `git submodule
             add` produces — rather than invoking `git submodule add`, whose
             exact internal layout depends on git version and requires enabling
             the file:// transport (CVE-2022-39253 mitigation) in CI.
        Why: A submodule's .git file has no commondir, so it must be treated as
             "not a linked worktree" and never redirected — confirmed as a
             distinct case during design.
        """
        # Arrange
        submodule_dir = tmp_path / "submodule"
        submodule_gitdir = tmp_path / "parent" / ".git" / "modules" / "submodule"
        submodule_gitdir.mkdir(parents=True)
        submodule_dir.mkdir()
        (submodule_dir / ".git").write_text(f"gitdir: {submodule_gitdir}\n", encoding="utf-8")
        # No commondir file under submodule_gitdir — this is what distinguishes
        # a submodule's gitdir from a linked worktree's gitdir.

        # Act
        result = _shared_checkout_root(submodule_dir)

        # Assert
        assert result == submodule_dir

    def test_bare_repo_worktree_resolves_via_commondir(self, tmp_path: Path) -> None:
        """A worktree attached to a bare repository resolves via its commondir.

        Tests: _shared_checkout_root with a bare-repo-backed worktree
        How: Create a bare repo, seed it with a commit via a throwaway clone,
             then `git --git-dir=<bare> worktree add` a real working tree.
        Why: Bare-repo worktree setups are a distinct topology from a linked
             worktree off a normal checkout; the commondir-resolution algorithm
             must handle both without special-casing.
        """
        # Arrange
        bare = tmp_path / "repo.git"
        _run_git(["init", "--bare", "--initial-branch=main", str(bare)], cwd=tmp_path)
        seed = tmp_path / "seed"
        seed.mkdir()
        _run_git(["clone", str(bare), str(seed)], cwd=tmp_path)
        _run_git(["config", "user.email", "test@example.com"], cwd=seed)
        _run_git(["config", "user.name", "Test"], cwd=seed)
        (seed / "file.txt").write_text("content\n", encoding="utf-8")
        _run_git(["add", "."], cwd=seed)
        _run_git(["commit", "-m", "initial commit"], cwd=seed)
        _run_git(["push", "origin", "main"], cwd=seed)
        bare_worktree = tmp_path / "bare-worktree"
        _run_git(["--git-dir", str(bare), "worktree", "add", str(bare_worktree), "main"], cwd=tmp_path)

        # Act
        result = _shared_checkout_root(bare_worktree)

        # Assert — the bare repo's directory has no working-tree parent of its
        # own, so the resolved commondir's parent is the bare repo's *parent*
        # directory. This is the algorithm's defined, deterministic behaviour
        # for this topology, not a meaningful "primary checkout" in the
        # linked-worktree sense.
        assert result == bare.resolve().parent

    def test_malformed_gitdir_content_returns_start_unchanged(self, tmp_path: Path) -> None:
        """A .git file with unreadable/garbage gitdir content returns start unchanged.

        Tests: _shared_checkout_root defensive fallback for malformed .git file
        How: Write a .git file with content that doesn't match the "gitdir: "
             prefix contract at all.
        Why: Must never raise on a corrupt or foreign .git file; always falls
             back to treating the directory as its own root.
        """
        # Arrange
        weird_dir = tmp_path / "weird"
        weird_dir.mkdir()
        (weird_dir / ".git").write_text("not a gitdir pointer\n", encoding="utf-8")

        # Act
        result = _shared_checkout_root(weird_dir)

        # Assert
        assert result == weird_dir

    def test_gitdir_pointing_nowhere_returns_start_unchanged(self, tmp_path: Path) -> None:
        """A .git file pointing at a nonexistent gitdir returns start unchanged.

        Tests: _shared_checkout_root defensive fallback for a dangling gitdir pointer
        How: Write a .git file whose gitdir target directory doesn't exist,
             so reading its commondir file fails.
        Why: A dangling or stale worktree registration must never raise;
             falls back to start.
        """
        # Arrange
        dangling_dir = tmp_path / "dangling"
        dangling_dir.mkdir()
        (dangling_dir / ".git").write_text(f"gitdir: {tmp_path / 'nonexistent-gitdir'}\n", encoding="utf-8")

        # Act
        result = _shared_checkout_root(dangling_dir)

        # Assert
        assert result == dangling_dir


# ---------------------------------------------------------------------------
# Regression guard: PROJECT_ROOT must stay worktree-local
# ---------------------------------------------------------------------------


class TestProjectRootStaysWorktreeLocal:
    """Regression guard for issue #116 point 1 — PROJECT_ROOT is never redirected.

    Only VENDOR_DIR (and therefore SOURCES_DIR) is redirected to the primary
    checkout root inside a linked worktree. PROJECT_ROOT itself must remain
    worktree-local because scripts/fetch_spec_schema.py uses it to write
    tracked source files (packages/skilllint/schemas/agentskills_io/ and
    packages/skilllint/_spec_constants.py); redirecting it would make a
    worktree run of that script silently overwrite generated source in a
    different working tree than the one being edited.
    """

    def test_schema_dir_resolves_under_this_checkout_not_a_shared_one(self) -> None:
        """fetch_spec_schema.SCHEMA_DIR resolves under this test's own repo root.

        Tests: PROJECT_ROOT (and everything derived from it) is not passed
               through _shared_checkout_root.
        How: Compute this test file's own repo root independently of vendor_io
             (by walking up from __file__), then assert SCHEMA_DIR and
             PROJECT_ROOT both match it exactly. This test runs for real
             inside a linked worktree in CI/dev — if PROJECT_ROOT were ever
             redirected to a primary checkout, this assertion would fail
             whenever a primary checkout with an existing cache exists
             alongside the worktree running the tests.
        Why: Guards against the exact wrong-implementation described in the
             issue #116 design — redirecting PROJECT_ROOT instead of only
             VENDOR_DIR.
        """
        # Arrange
        from scripts.fetch_spec_schema import SCHEMA_DIR

        this_checkout_root = Path(__file__).resolve().parents[3]

        # Act / Assert
        assert this_checkout_root == PROJECT_ROOT
        assert this_checkout_root / "packages" / "skilllint" / "schemas" / "agentskills_io" == SCHEMA_DIR
