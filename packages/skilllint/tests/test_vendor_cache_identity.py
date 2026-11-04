"""Source identity must survive cache reuse, offline fallback, and migration."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING

import httpx
import pytest
from typer.testing import CliRunner

from skilllint.plugin_validator import app
from skilllint.vendor_cache import CacheStatus, NoCacheError, derive_page_name, fetch_or_cached, find_latest
from skilllint.vendor_io import load_sidecar, write_sidecar

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize("other_content", ["source A", "source B"])
@pytest.mark.parametrize(
    "other_url",
    [
        "https://b.example/docs/settings.md",
        "http://a.example/docs/settings.md",
        "https://a.example:8443/docs/settings.md",
        "https://a.example/docs/settings.md?version=2",
        "https://a.example/docs/settings.md?x=1&y=2",
        "https://user:a@a.example/docs/settings.md",
        "https://a.example/docs/Settings.md",
        "https://a.example/docs/%73ettings.md",
        "https://a.example/settings.md",
        "https://a.example/api/settings.md",
        "https://a.example/docs/settings",
    ],
)
def test_distinct_sources_never_share_content_or_provenance(
    tmp_path: Path, mocker: MockerFixture, other_url: str, other_content: str
) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    url = "https://a.example/docs/settings.md"
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", side_effect=["source A", other_content])

    first = fetch_or_cached(url)
    second = fetch_or_cached(other_url)

    assert fetch.call_count == 2
    assert first.status is second.status is CacheStatus.NEW
    assert first.path != second.path
    assert first.path.read_text() == "source A"
    assert second.path.read_text() == other_content
    assert json.loads(first.path.with_suffix(".meta.json").read_text())["url"] == url
    assert json.loads(second.path.with_suffix(".meta.json").read_text())["url"] == other_url
    assert fetch_or_cached(url).path == first.path
    assert fetch_or_cached(other_url).path == second.path
    assert fetch.call_count == 2


@pytest.mark.parametrize(
    "alias",
    [
        "HTTPS://A.EXAMPLE:443/docs/settings.md",
        "https://a.example/docs/settings.md#section",
        "https://a.example/docs/../docs/settings.md",
    ],
)
def test_http_client_normalized_aliases_share_source_cache(tmp_path: Path, mocker: MockerFixture, alias: str) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value="source A")
    first = fetch_or_cached("https://a.example/docs/settings.md")

    second = fetch_or_cached(alias)

    fetch.assert_called_once()
    assert second.status is CacheStatus.FRESH
    assert second.path == first.path
    assert second.url == alias


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize("legacy", [False, True])
def test_other_sources_are_not_offline_fallbacks(
    tmp_path: Path, mocker: MockerFixture, force: bool, legacy: bool
) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    url = "https://a.example/docs/settings.md"
    content = "source A"
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value=content)
    cached = fetch_or_cached(url).path
    if legacy:
        legacy_path = tmp_path / "settings-2026-01-01-0000.md"
        cached.rename(legacy_path)
        cached.with_suffix(".meta.json").rename(legacy_path.with_suffix(".meta.json"))
        cached = legacy_path
    write_sidecar(cached, url=url, content=content, fetched_at=datetime.now(UTC) - timedelta(days=1))
    before = cached.with_suffix(".meta.json").read_bytes()
    fetch.side_effect = httpx.ConnectError("offline")

    with pytest.raises(NoCacheError):
        fetch_or_cached("https://b.example/docs/settings.md", force=force)

    assert cached.read_text() == content
    assert cached.with_suffix(".meta.json").read_bytes() == before


@pytest.mark.parametrize("force", [False, True])
def test_legacy_lookup_skips_newer_entries_from_other_sources(
    tmp_path: Path, mocker: MockerFixture, force: bool
) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    url = "https://a.example/docs/settings.md"
    own = tmp_path / "settings-2026-01-01-0000.md"
    other = tmp_path / "settings-2026-01-02-0000.md"
    for path, source, content in [(own, url, "A"), (other, "https://b.example/docs/settings.md", "B")]:
        path.write_text(content)
        write_sidecar(path, url=source, content=content)
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", side_effect=httpx.ConnectError("offline"))

    result = fetch_or_cached(url, force=force)

    assert result.path == own
    assert result.status is (CacheStatus.STALE if force else CacheStatus.FRESH)
    assert fetch.call_count == int(force)


def test_legacy_refresh_migrates_without_overwriting_either_source(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    url = "https://a.example/docs/settings.md"
    now = datetime.now(UTC)
    clock = mocker.patch("skilllint.vendor_cache.datetime", wraps=datetime)
    clock.now.return_value = now
    legacy = tmp_path / f"settings-{now:%Y-%m-%d-%H%M}.md"
    legacy.write_text("old A")
    write_sidecar(legacy, url=url, content="old A")
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value="new A")

    result = fetch_or_cached(url, force=True)

    assert result.status is CacheStatus.REFRESHED
    assert result.path != legacy
    assert result.path.read_text() == "new A"
    assert legacy.read_text() == "old A"
    assert fetch_or_cached(url).path == result.path
    assert find_latest("settings", sources_dir=tmp_path) == result.path
    fetch.assert_called_once_with(url)


@pytest.mark.parametrize("sidecar_content", [None, "[]", "{}", "not JSON"])
def test_unidentifiable_legacy_entries_are_never_served_offline(
    tmp_path: Path, mocker: MockerFixture, sidecar_content: str | None
) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    path = tmp_path / "settings-2026-01-01-0000.md"
    path.write_text("unknown source")
    if sidecar_content is not None:
        path.with_suffix(".meta.json").write_text(sidecar_content)
    mocker.patch("skilllint.vendor_cache.fetch_url_text", side_effect=httpx.ConnectError("offline"))

    with pytest.raises(NoCacheError):
        fetch_or_cached("https://a.example/docs/settings.md")


@pytest.mark.parametrize("force", [False, True])
def test_source_hash_alone_is_not_accepted_as_provenance(tmp_path: Path, mocker: MockerFixture, force: bool) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    url = "https://a.example/docs/settings.md"
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value="A")
    cached = fetch_or_cached(url).path
    write_sidecar(cached, url="https://b.example/docs/settings.md", content="A")
    fetch.side_effect = httpx.ConnectError("offline")

    with pytest.raises(NoCacheError):
        fetch_or_cached(url, force=force)

    sidecar = load_sidecar(cached)
    assert sidecar is not None
    assert sidecar.url == "https://b.example/docs/settings.md"


def test_legacy_source_with_invalid_port_is_a_cache_miss(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    url = "https://a.example/docs/settings.md"
    legacy = tmp_path / "settings-2026-01-01-0000.md"
    legacy.write_text("untrusted")
    write_sidecar(legacy, url="https://a.example:invalid/docs/settings.md", content="untrusted")
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value="verified")

    result = fetch_or_cached(url)

    assert result.status is CacheStatus.NEW
    assert result.path.read_text() == "verified"
    assert legacy.read_text() == "untrusted"
    fetch.assert_called_once_with(url)


def test_legacy_source_accepts_normalized_aliases(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    legacy = tmp_path / "settings-2026-01-01-0000.md"
    legacy.write_text("A")
    write_sidecar(legacy, url="HTTPS://A.EXAMPLE:443/docs/settings.md#first", content="A")
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text")

    result = fetch_or_cached("https://a.example/docs/settings.md#second")

    assert result.path == legacy
    assert result.status is CacheStatus.FRESH
    fetch.assert_not_called()


def test_legacy_alias_migration_selects_latest_timestamp_not_display_slug(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    alias = "https://a.example/z/../docs/settings.md"
    legacy = tmp_path / "z--docs--settings-2026-01-01-0000.md"
    legacy.write_text("old")
    write_sidecar(legacy, url=alias, content="old")
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value="new")

    result = fetch_or_cached(alias, force=True)

    assert result.status is CacheStatus.REFRESHED
    assert result.path.read_text() == "new"
    assert fetch_or_cached(alias).path == result.path
    assert fetch_or_cached("https://a.example/docs/settings.md").path == result.path
    assert legacy.read_text() == "old"
    fetch.assert_called_once_with(alias)


def test_cli_keeps_real_http_sources_on_different_ports_separate(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            source = self.headers["Host"]
            requests.append(source)
            body = f"# Source {source}\n".encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    servers = [ThreadingHTTPServer(("127.0.0.1", 0), Handler) for _ in range(2)]
    threads = [Thread(target=server.serve_forever) for server in servers]
    for thread in threads:
        thread.start()
    runner = CliRunner()
    urls = [f"http://127.0.0.1:{server.server_port}/settings.md" for server in servers]
    try:
        results = [runner.invoke(app, ["docs", "fetch", url]) for url in urls]
        assert all(result.exit_code == 0 for result in results)
        paths = [Path(result.stdout.strip()) for result in results]
        assert paths[0] != paths[1]
        for url, path in zip(urls, paths, strict=True):
            assert path.read_text() == f"# Source {httpx.URL(url).netloc.decode()}\n"
            assert runner.invoke(app, ["docs", "fetch", url]).stdout.strip() == str(path)
        assert len(requests) == 2
    finally:
        for server, thread in zip(servers, threads, strict=True):
            server.shutdown()
            thread.join()
            server.server_close()


@pytest.mark.parametrize("query", ["?x=2&y=2", "?y=2&x=1"])
def test_query_values_and_order_are_not_discarded(tmp_path: Path, mocker: MockerFixture, query: str) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value="same body")
    base = "https://a.example/docs/settings.md"

    first = fetch_or_cached(f"{base}?x=1&y=2")
    second = fetch_or_cached(f"{base}{query}")

    assert first.path != second.path
    assert first.status is second.status is CacheStatus.NEW
    assert fetch.call_count == 2


@pytest.mark.parametrize("mode", ["new", "fresh", "stale"])
def test_unrelated_invalid_utf8_sidecar_does_not_block_lookup(tmp_path: Path, mocker: MockerFixture, mode: str) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    url = "https://a.example/docs/settings.md"
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value="valid source")
    existing = None if mode == "new" else fetch_or_cached(url).path
    unrelated = tmp_path / "unrelated-2099-01-01-0000.md"
    unrelated.write_text("unrelated")
    unrelated.with_suffix(".meta.json").write_bytes(b"\xff")
    if mode == "stale":
        fetch.side_effect = httpx.ConnectError("offline")

    result = fetch_or_cached(url, force=mode == "stale")

    assert result.status.value == mode
    assert result.path.read_text() == "valid source"
    if existing is not None:
        assert result.path == existing


def test_long_display_names_do_not_overflow_filenames_or_merge_sources(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    # This prefix fitted the legacy filename but overflowed after adding a hash.
    page_name = "long-page-" * 19
    first_url = f"https://a.example/docs/{page_name}.md"
    second_name = f"{page_name}other"
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", side_effect=["A", "B"])
    legacy = tmp_path / f"{page_name}-2026-01-01-0000.md"
    legacy.write_text("old A")
    write_sidecar(legacy, url=first_url, content="old A")

    first = fetch_or_cached(first_url, force=True)
    second = fetch_or_cached(f"https://a.example/docs/{second_name}.md")

    assert first.page_name == page_name
    assert second.page_name == second_name
    assert first.path != second.path
    assert first.path.read_text() == "A"
    assert second.path.read_text() == "B"
    assert first.path.with_suffix(".meta.json").is_file()
    assert second.path.with_suffix(".meta.json").is_file()
    assert find_latest(page_name, sources_dir=tmp_path) == first.path
    assert find_latest(second_name, sources_dir=tmp_path) == second.path
    assert fetch_or_cached(first_url).path == first.path
    assert fetch.call_count == 2


@pytest.mark.parametrize(
    "url",
    [
        "https://a.example/docs/café.md",
        "https://a.example/docs/%73ettings.md",
        "https://a.example/z/../docs/settings.md",
    ],
)
def test_display_name_contract_is_independent_of_source_normalization(
    tmp_path: Path, mocker: MockerFixture, url: str
) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value="content")

    result = fetch_or_cached(url)

    assert result.page_name == derive_page_name(url)
    assert find_latest(result.page_name, sources_dir=tmp_path) == result.path


def test_unchanged_alias_refresh_preserves_long_display_name_lookup(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    path = "/".join(["x"] * 60 + [".."] * 60 + ["docs", "settings.md"])
    original_url = f"https://a.example/{path}"
    mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value="unchanged")
    first = fetch_or_cached(original_url)

    second = fetch_or_cached("https://a.example/docs/settings.md", force=True)

    assert second.status is CacheStatus.UNCHANGED
    assert second.path == first.path
    assert find_latest(derive_page_name(original_url), sources_dir=tmp_path) == first.path
    sidecar = load_sidecar(first.path)
    assert sidecar is not None
    assert sidecar.url == original_url


def test_changed_alias_refresh_cannot_select_older_slug_in_same_minute(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    clock = mocker.patch("skilllint.vendor_cache.datetime", wraps=datetime)
    clock.now.return_value = datetime(2026, 11, 4, 11, 37, tzinfo=UTC)
    alias = "https://a.example/z/../docs/settings.md"
    canonical = "https://a.example/docs/settings.md"
    fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", side_effect=["old", "new"])
    fetch_or_cached(alias)

    refreshed = fetch_or_cached(canonical, force=True)
    cached = fetch_or_cached(canonical)

    assert refreshed.status is CacheStatus.REFRESHED
    assert cached.status is CacheStatus.FRESH
    assert cached.path == refreshed.path
    assert cached.path.read_text() == "new"
    assert find_latest(derive_page_name(alias), sources_dir=tmp_path) == refreshed.path
    fetch.assert_has_calls([mocker.call(alias), mocker.call(canonical)])
    assert fetch.call_count == 2


def test_complete_short_label_does_not_match_truncated_long_label(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
    mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value="content")
    long_name = "a" * 200
    long_result = fetch_or_cached(f"https://a.example/docs/{long_name}.md")
    # Derive the actual shortened prefix without coupling the test to its budget.
    short_name = long_result.path.name.split("-", 1)[0]

    assert find_latest(short_name, sources_dir=tmp_path) is None
    short_result = fetch_or_cached(f"https://a.example/docs/{short_name}.md")

    assert find_latest(short_name, sources_dir=tmp_path) == short_result.path
    assert find_latest(long_name, sources_dir=tmp_path) == long_result.path
