"""Tests for vendor drift detection, report output, and process exit behavior."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
from scripts.fetch_platform_docs import (
    DocPage,
    DocSitePlatform,
    GitDriftResult,
    GitPlatform,
    HttpDriftResult,
    HttpFileDriftResult,
    clone_or_update_repo,
    fetch_doc_site,
)

from skilllint.vendor_io import sha256_hex as _sha256

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# GitDriftResult.to_dict tests
# ---------------------------------------------------------------------------


def test_git_drift_result_to_dict_includes_type_git() -> None:
    """GitDriftResult.to_dict() includes type discriminator 'git'."""
    # Arrange
    result = GitDriftResult(
        provider="claude_code", before_sha="aaa", after_sha="bbb", diff="some diff", changelog="v2 released"
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


# ---------------------------------------------------------------------------
# HttpDriftResult.to_dict tests
# ---------------------------------------------------------------------------


def test_http_drift_result_to_dict_nested_files() -> None:
    """HttpDriftResult.to_dict() serializes nested HttpFileDriftResult list."""
    # Arrange
    file_result = HttpFileDriftResult(
        filename="rules.md", before_hash="aaa", after_hash="bbb", before_content="old", after_content="new"
    )
    result = HttpDriftResult(provider="cursor", files=[file_result], changelog="updated rules")

    # Act
    d = result.to_dict()

    # Assert
    assert len(d["files"]) == 1
    assert d["files"][0]["filename"] == "rules.md"
    assert d["changelog"] == "updated rules"
    # Full dict must be JSON-serializable
    json.dumps(d)


# ---------------------------------------------------------------------------
# fetch_doc_site snapshot/compare tests
# ---------------------------------------------------------------------------


def _make_platform(
    name: str = "testplatform", pages: list[DocPage] | None = None, releases_url: str | None = None
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


def test_fetch_doc_site_detects_content_change_returns_drift_result(tmp_path: Path) -> None:
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


def test_fetch_doc_site_fetches_releases_url_when_changes_detected(tmp_path: Path) -> None:
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


# ---------------------------------------------------------------------------
# clone_or_update_repo snapshot/compare tests
# ---------------------------------------------------------------------------


def _make_git_platform(name: str = "test_repo", url: str = "https://github.com/example/repo") -> GitPlatform:
    """Create a GitPlatform for testing.

    Args:
        name: Platform name used as the vendor subdirectory.
        url: Repository clone URL.

    Returns:
        A GitPlatform instance.
    """
    return GitPlatform(name, url)


def test_clone_or_update_repo_detects_change_returns_drift_result(tmp_path: Path, mocker: MockerFixture) -> None:
    """Return GitDriftResult with diff and changelog when SHA changes.

    Tests: clone_or_update_repo detects vendor content drift via SHA comparison.
    How: Set up a fake existing repo (.git dir present), mock _git_head_sha to
        return different SHAs before and after the pull, and mock _run_git to
        provide diff and log output.
    Why: The drift detection pipeline requires a GitDriftResult containing the
        before/after SHAs, diff of doc-relevant files, and commit changelog
        to generate actionable audit reports.
    """
    # Arrange
    vendor_dir = tmp_path / "vendor"
    platform = _make_git_platform()
    dest = vendor_dir / platform.name
    dest.mkdir(parents=True)
    (dest / ".git").mkdir()

    before_sha = "aaaa" * 10
    after_sha = "bbbb" * 10

    mocker.patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir)

    sha_call_count = 0

    def fake_git_head_sha(repo_dir: Path) -> str | None:
        nonlocal sha_call_count
        sha_call_count += 1
        if sha_call_count == 1:
            return before_sha
        return after_sha

    mocker.patch("scripts.fetch_platform_docs._git_head_sha", side_effect=fake_git_head_sha)

    def fake_run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        if args[0] == "pull":
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args[0] == "fetch" and "--unshallow" in args:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args[0] == "diff":
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="diff --git a/CLAUDE.md b/CLAUDE.md\n", stderr=""
            )
        if args[0] == "log":
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="abc1234 feat: update docs\ndef5678 fix: typo", stderr=""
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    mocker.patch("scripts.fetch_platform_docs._run_git", side_effect=fake_run_git)

    # Create .git/shallow to simulate a shallow clone
    (dest / ".git" / "shallow").touch()

    # Act
    result = clone_or_update_repo(platform, dry_run=False)

    # Assert
    assert result is not None
    assert isinstance(result, GitDriftResult)
    assert result.provider == "test_repo"
    assert result.before_sha == before_sha
    assert result.after_sha == after_sha
    assert "CLAUDE.md" in result.diff
    assert "feat: update docs" in result.changelog


def test_clone_or_update_repo_no_change_returns_none(tmp_path: Path, mocker: MockerFixture) -> None:
    """Return None when HEAD SHA is the same before and after pull.

    Tests: clone_or_update_repo correctly identifies no-change scenario.
    How: Mock _git_head_sha to return the same SHA both times (before and
        after the pull operation), mock _run_git for the pull command.
    Why: When a vendor repo has no new commits since the last fetch, no
        drift result should be generated to avoid false-positive reports.
    """
    # Arrange
    vendor_dir = tmp_path / "vendor"
    platform = _make_git_platform()
    dest = vendor_dir / platform.name
    dest.mkdir(parents=True)
    (dest / ".git").mkdir()

    same_sha = "cccc" * 10

    mocker.patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir)
    mocker.patch("scripts.fetch_platform_docs._git_head_sha", return_value=same_sha)
    mocker.patch(
        "scripts.fetch_platform_docs._run_git",
        return_value=subprocess.CompletedProcess(args=["git", "pull"], returncode=0, stdout="", stderr=""),
    )

    # Act
    result = clone_or_update_repo(platform, dry_run=False)

    # Assert
    assert result is None


def test_clone_or_update_repo_first_clone_returns_none(tmp_path: Path, mocker: MockerFixture) -> None:
    """Return None on first clone when before_sha is None.

    Tests: clone_or_update_repo handles first-time clone scenario.
    How: Set up a vendor directory where the platform subdirectory does not
        exist (no .git), so _git_head_sha returns None for the before_sha.
        Mock _run_git for the clone command and _git_head_sha to return a
        SHA only on the second call (after clone).
    Why: On first clone there is no before_sha to compare against, so no
        drift can be reported. The function must return None rather than
        creating a misleading GitDriftResult.
    """
    # Arrange
    vendor_dir = tmp_path / "vendor"
    platform = _make_git_platform()

    mocker.patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir)

    sha_call_count = 0

    def fake_git_head_sha(repo_dir: Path) -> str | None:
        nonlocal sha_call_count
        sha_call_count += 1
        if sha_call_count == 1:
            return None  # No repo before clone
        return "dddd" * 10  # After clone

    mocker.patch("scripts.fetch_platform_docs._git_head_sha", side_effect=fake_git_head_sha)

    def fake_run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        if args[0] == "clone":
            # Simulate clone by creating the .git dir
            dest = vendor_dir / platform.name
            dest.mkdir(parents=True, exist_ok=True)
            (dest / ".git").mkdir(exist_ok=True)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    mocker.patch("scripts.fetch_platform_docs._run_git", side_effect=fake_run_git)

    # Act
    result = clone_or_update_repo(platform, dry_run=False)

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# fetch command integration tests (CliRunner)
# ---------------------------------------------------------------------------


def test_fetch_command_exits_2_when_changes_detected(tmp_path: Path, mocker: MockerFixture) -> None:
    """Exit code 2 when vendor drift is detected in non-dry-run mode."""
    from scripts.fetch_platform_docs import app
    from typer.testing import CliRunner

    cli_runner = CliRunner()

    # Arrange — mock git platforms to return a drift result
    mocker.patch("scripts.fetch_platform_docs.GIT_PLATFORMS", [GitPlatform("test_repo", "https://example.com/repo")])
    mocker.patch("scripts.fetch_platform_docs.DOC_SITE_PLATFORMS", [])
    mocker.patch(
        "scripts.fetch_platform_docs.clone_or_update_repo",
        return_value=GitDriftResult(provider="test_repo", before_sha="aaa", after_sha="bbb"),
    )
    mocker.patch("scripts.fetch_platform_docs.DRIFT_FILE", tmp_path / ".drift-pending.json")

    # Act
    result = cli_runner.invoke(app)

    # Assert
    assert result.exit_code == 2


def test_fetch_command_exits_0_when_no_changes(tmp_path: Path, mocker: MockerFixture) -> None:
    """Exit code 0 when no vendor drift is detected."""
    from scripts.fetch_platform_docs import app
    from typer.testing import CliRunner

    cli_runner = CliRunner()

    # Arrange — mock all platforms to return None (no changes)
    mocker.patch("scripts.fetch_platform_docs.GIT_PLATFORMS", [GitPlatform("test_repo", "https://example.com/repo")])
    mocker.patch("scripts.fetch_platform_docs.DOC_SITE_PLATFORMS", [])
    mocker.patch("scripts.fetch_platform_docs.clone_or_update_repo", return_value=None)

    # Act
    result = cli_runner.invoke(app)

    # Assert
    assert result.exit_code == 0


def test_drift_pending_json_matches_schema(tmp_path: Path, mocker: MockerFixture) -> None:
    """Written JSON has expected keys: fetch_time, changed array with provider entries."""
    from scripts.fetch_platform_docs import app
    from typer.testing import CliRunner

    cli_runner = CliRunner()

    # Arrange
    drift_file = tmp_path / ".drift-pending.json"
    mocker.patch("scripts.fetch_platform_docs.GIT_PLATFORMS", [GitPlatform("repo_a", "https://example.com/a")])
    mocker.patch(
        "scripts.fetch_platform_docs.DOC_SITE_PLATFORMS",
        [DocSitePlatform("site_b", [DocPage("https://example.com/page", "page.md")])],
    )
    mocker.patch(
        "scripts.fetch_platform_docs.clone_or_update_repo",
        return_value=GitDriftResult(provider="repo_a", before_sha="aaa", after_sha="bbb"),
    )
    mocker.patch(
        "scripts.fetch_platform_docs.fetch_doc_site",
        return_value=HttpDriftResult(
            provider="site_b",
            files=[
                HttpFileDriftResult(
                    filename="page.md", before_hash="h1", after_hash="h2", before_content="old", after_content="new"
                )
            ],
        ),
    )
    mocker.patch("scripts.fetch_platform_docs.DRIFT_FILE", drift_file)

    # Act
    _ = cli_runner.invoke(app)

    # Assert — validate schema structure
    data = json.loads(drift_file.read_text(encoding="utf-8"))
    assert "fetch_time" in data
    assert isinstance(data["changed"], list)
    assert len(data["changed"]) == 2

    # Check git entry
    git_entry = data["changed"][0]
    assert git_entry["type"] == "git"
    assert git_entry["provider"] == "repo_a"
    assert "before_sha" in git_entry
    assert "after_sha" in git_entry

    # Check http entry
    http_entry = data["changed"][1]
    assert http_entry["type"] == "http"
    assert http_entry["provider"] == "site_b"
    assert isinstance(http_entry["files"], list)
    assert len(http_entry["files"]) == 1


# ---------------------------------------------------------------------------
# Real-process exit codes: drift and usage errors must be distinguishable
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "scripts" / "fetch_platform_docs.py"
DRIFT_EXIT_CODE = 2

# Runs the script's real process entry point with network access replaced by a
# canned drift result, so the exit status comes from a real interpreter exit.
DRIFT_DRIVER = """
import pathlib, sys, tempfile
from unittest.mock import patch
import scripts.fetch_platform_docs as script

drift_file = pathlib.Path(tempfile.mkdtemp()) / ".drift-pending.json"
result = script.GitDriftResult(provider="t", before_sha="a", after_sha="b")
with (
    patch.object(script, "GIT_PLATFORMS", [script.GitPlatform("t", "https://example.com/r")]),
    patch.object(script, "DOC_SITE_PLATFORMS", []),
    patch.object(script, "DRIFT_FILE", drift_file),
    patch.object(script, "clone_or_update_repo", return_value=result),
):
    script.main()
"""


def test_main_exits_2_when_drift_detected() -> None:
    """A drift run exits with the documented drift code, 2."""
    # Act
    completed = subprocess.run(
        [sys.executable, "-c", DRIFT_DRIVER], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )

    # Assert
    assert completed.returncode == DRIFT_EXIT_CODE, completed.stderr


def test_script_usage_error_does_not_exit_with_drift_code() -> None:
    """An unknown option must not exit with the drift code the SessionStart hook acts on."""
    # Act
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--no-such-option"], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )

    # Assert
    assert completed.returncode not in {0, DRIFT_EXIT_CODE}
    assert "No such option" in completed.stderr
    assert "Usage:" in completed.stderr
