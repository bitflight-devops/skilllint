"""Tests for drift detection data model and hash helpers in fetch_platform_docs."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from scripts.fetch_platform_docs import (
    DocPage,
    DocSitePlatform,
    DriftReport,
    GitDriftResult,
    HttpDriftResult,
    HttpFileDriftResult,
    _read_text_or_none,
    _sha256,
    fetch_doc_site,
)

# ---------------------------------------------------------------------------
# _sha256 tests
# ---------------------------------------------------------------------------


def test_sha256_returns_hex_digest() -> None:
    """Known SHA-256 of 'hello' matches reference value."""
    assert (
        _sha256("hello")
        == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_sha256_same_input_same_output() -> None:
    """Deterministic: same input always produces same digest."""
    assert _sha256("foo") == _sha256("foo")


def test_sha256_different_inputs_different_output() -> None:
    """Different inputs produce different digests."""
    assert _sha256("foo") != _sha256("bar")


# ---------------------------------------------------------------------------
# _read_text_or_none tests
# ---------------------------------------------------------------------------


def test_read_text_or_none_existing_file_returns_content(tmp_path: Path) -> None:
    """Existing file content is returned as string."""
    f = tmp_path / "test.txt"
    f.write_text("hello", encoding="utf-8")
    assert _read_text_or_none(f) == "hello"


def test_read_text_or_none_missing_file_returns_none(tmp_path: Path) -> None:
    """Missing file returns None instead of raising."""
    assert _read_text_or_none(tmp_path / "nonexistent.txt") is None


# ---------------------------------------------------------------------------
# GitDriftResult.to_dict tests
# ---------------------------------------------------------------------------


def test_git_drift_result_to_dict_includes_type_git() -> None:
    """GitDriftResult.to_dict() includes type discriminator 'git'."""
    # Arrange
    result = GitDriftResult(
        provider="claude_code",
        before_sha="aaa",
        after_sha="bbb",
        diff="some diff",
        changelog="v2 released",
    )

    # Act
    d = result.to_dict()

    # Assert
    assert d["type"] == "git"
    assert d["provider"] == "claude_code"
    assert d["before_sha"] == "aaa"
    assert d["after_sha"] == "bbb"
    assert d["diff"] == "some diff"
    assert d["changelog"] == "v2 released"


def test_git_drift_result_to_dict_json_serializable() -> None:
    """GitDriftResult.to_dict() output is JSON-serializable."""
    result = GitDriftResult(provider="codex", before_sha="a", after_sha="b")
    serialized = json.dumps(result.to_dict())
    assert '"type": "git"' in serialized


# ---------------------------------------------------------------------------
# HttpFileDriftResult.to_dict tests
# ---------------------------------------------------------------------------


def test_http_file_drift_result_to_dict_round_trip() -> None:
    """HttpFileDriftResult round-trips through to_dict and back."""
    # Arrange
    original = HttpFileDriftResult(
        filename="rules.md",
        before_hash="abc",
        after_hash="def",
        before_content="old",
        after_content="new",
    )

    # Act
    d = original.to_dict()
    restored = HttpFileDriftResult(**d)

    # Assert
    assert restored == original


# ---------------------------------------------------------------------------
# HttpDriftResult.to_dict tests
# ---------------------------------------------------------------------------


def test_http_drift_result_to_dict_serializes_type_field() -> None:
    """HttpDriftResult.to_dict() includes hardcoded type discriminator 'http'."""
    # Arrange
    result = HttpDriftResult(provider="cursor")

    # Act
    d = result.to_dict()

    # Assert
    assert d["type"] == "http"
    assert "type_" not in d


def test_http_drift_result_to_dict_nested_files() -> None:
    """HttpDriftResult.to_dict() serializes nested HttpFileDriftResult list."""
    # Arrange
    file_result = HttpFileDriftResult(
        filename="rules.md",
        before_hash="aaa",
        after_hash="bbb",
        before_content="old",
        after_content="new",
    )
    result = HttpDriftResult(
        provider="cursor",
        files=[file_result],
        changelog="updated rules",
    )

    # Act
    d = result.to_dict()

    # Assert
    assert len(d["files"]) == 1
    assert d["files"][0]["filename"] == "rules.md"
    assert d["changelog"] == "updated rules"
    # Full dict must be JSON-serializable
    json.dumps(d)


# ---------------------------------------------------------------------------
# DriftReport.to_dict tests
# ---------------------------------------------------------------------------


def test_drift_report_to_dict_empty_changed() -> None:
    """DriftReport with no changes serializes correctly."""
    report = DriftReport(fetch_time="2026-03-11T00:00:00+00:00", changed=[])
    d = report.to_dict()
    assert d["fetch_time"] == "2026-03-11T00:00:00+00:00"
    assert d["changed"] == []
    json.dumps(d)  # must not raise


def test_drift_report_to_dict_mixed_results() -> None:
    """DriftReport.to_dict() calls to_dict() on each item in changed."""
    # Arrange
    git_result = GitDriftResult(provider="claude_code", before_sha="a1", after_sha="b2")
    http_result = HttpDriftResult(
        provider="cursor",
        files=[
            HttpFileDriftResult(
                filename="rules.md",
                before_hash="h1",
                after_hash="h2",
                before_content="old",
                after_content="new",
            )
        ],
    )
    report = DriftReport(
        fetch_time="2026-03-11T00:00:00+00:00",
        changed=[git_result, http_result],
    )

    # Act
    d = report.to_dict()

    # Assert
    assert len(d["changed"]) == 2
    assert d["changed"][0]["type"] == "git"
    assert d["changed"][1]["type"] == "http"
    # Full round-trip through JSON
    serialized = json.dumps(d)
    deserialized = json.loads(serialized)
    assert deserialized["fetch_time"] == "2026-03-11T00:00:00+00:00"
    assert len(deserialized["changed"]) == 2


# ---------------------------------------------------------------------------
# DocSitePlatform.releases_url tests
# ---------------------------------------------------------------------------


def test_doc_site_platform_releases_url_default_none() -> None:
    """DocSitePlatform.releases_url defaults to None."""
    platform = DocSitePlatform("test", [])
    assert platform.releases_url is None


def test_doc_site_platform_releases_url_set() -> None:
    """DocSitePlatform.releases_url can be set via constructor."""
    platform = DocSitePlatform("test", [], releases_url="https://example.com/releases")
    assert platform.releases_url == "https://example.com/releases"


# ---------------------------------------------------------------------------
# fetch_doc_site snapshot/compare tests
# ---------------------------------------------------------------------------


def _make_platform(
    name: str = "testplatform",
    pages: list[DocPage] | None = None,
    releases_url: str | None = None,
) -> DocSitePlatform:
    """Create a DocSitePlatform for testing."""
    if pages is None:
        pages = [DocPage("https://example.com/docs/page.md", "page.md")]
    return DocSitePlatform(name, pages, releases_url=releases_url)


def _mock_response(text: str, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response with given text."""
    resp = MagicMock(spec=httpx.Response)
    resp.text = text
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


def test_fetch_doc_site_detects_content_change_returns_drift_result(
    tmp_path: Path,
) -> None:
    """When existing file has different content than fetched, return HttpDriftResult."""
    # Arrange
    platform = _make_platform()
    vendor_dir = tmp_path / ".claude" / "vendor"
    dest = vendor_dir / platform.name
    dest.mkdir(parents=True)
    (dest / "page.md").write_text("old content", encoding="utf-8")

    mock_resp = _mock_response("new content")

    with (
        patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir),
        patch("scripts.fetch_platform_docs.httpx.Client") as mock_client_cls,
    ):
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Act
        result = fetch_doc_site(platform, dry_run=False)

    # Assert
    assert result is not None
    assert result.provider == "testplatform"
    assert len(result.files) == 1
    assert result.files[0].filename == "page.md"
    assert result.files[0].before_content == "old content"
    assert result.files[0].after_content == "new content"
    assert result.files[0].before_hash == _sha256("old content")
    assert result.files[0].after_hash == _sha256("new content")
    assert result.files[0].before_hash != result.files[0].after_hash


def test_fetch_doc_site_no_change_returns_none(tmp_path: Path) -> None:
    """When existing file matches fetched content, return None."""
    # Arrange
    platform = _make_platform()
    vendor_dir = tmp_path / ".claude" / "vendor"
    dest = vendor_dir / platform.name
    dest.mkdir(parents=True)
    (dest / "page.md").write_text("same content", encoding="utf-8")

    mock_resp = _mock_response("same content")

    with (
        patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir),
        patch("scripts.fetch_platform_docs.httpx.Client") as mock_client_cls,
    ):
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Act
        result = fetch_doc_site(platform, dry_run=False)

    # Assert
    assert result is None


def test_fetch_doc_site_first_fetch_returns_none(tmp_path: Path) -> None:
    """When no existing file (first time fetch), return None."""
    # Arrange
    platform = _make_platform()
    vendor_dir = tmp_path / ".claude" / "vendor"

    mock_resp = _mock_response("brand new content")

    with (
        patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir),
        patch("scripts.fetch_platform_docs.httpx.Client") as mock_client_cls,
    ):
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Act
        result = fetch_doc_site(platform, dry_run=False)

    # Assert
    assert result is None
    # File should still be written on first fetch
    written = (vendor_dir / platform.name / "page.md").read_text(encoding="utf-8")
    assert written == "brand new content"


def test_fetch_doc_site_fetches_releases_url_when_changes_detected(
    tmp_path: Path,
) -> None:
    """When changes detected and releases_url set, changelog is included."""
    # Arrange
    platform = _make_platform(releases_url="https://example.com/changelog")
    vendor_dir = tmp_path / ".claude" / "vendor"
    dest = vendor_dir / platform.name
    dest.mkdir(parents=True)
    (dest / "page.md").write_text("old content", encoding="utf-8")

    page_resp = _mock_response("new content")
    changelog_resp = _mock_response("## v2.0\n- Big changes")

    def mock_get(url: str) -> MagicMock:
        if "changelog" in url:
            return changelog_resp
        return page_resp

    with (
        patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir),
        patch("scripts.fetch_platform_docs.httpx.Client") as mock_client_cls,
    ):
        mock_client = MagicMock()
        mock_client.get.side_effect = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Act
        result = fetch_doc_site(platform, dry_run=False)

    # Assert
    assert result is not None
    assert result.changelog == "## v2.0\n- Big changes"
    assert len(result.files) == 1


def test_fetch_doc_site_dry_run_returns_none() -> None:
    """Dry-run mode returns None without making HTTP requests."""
    # Arrange
    platform = _make_platform()

    # Act
    result = fetch_doc_site(platform, dry_run=True)

    # Assert
    assert result is None
