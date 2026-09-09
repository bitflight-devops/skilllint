from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from scripts import refresh_claim_values as refresh

from skilllint.vendor_cache import CacheResult, CacheStatus, NoCacheError

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).parent.parent
AUTHORITY_URL = "https://example.test/hooks.md"


def _registry() -> dict[str, object]:
    return {
        "claims": {
            "HK002.valid_event_types": {
                "authority": {"authority_url": AUTHORITY_URL},
                "expected_value": ["SessionStart"],
                "x-audited": {"date": "2026-01-01", "source": "old.md"},
            },
            "HK003.valid_hook_types": {
                "authority": {"authority_url": AUTHORITY_URL},
                "expected_value": ["command"],
                "x-audited": {"date": "2026-01-01", "source": "old.md"},
            },
        }
    }


def _configure_updater(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    section: Callable[[Path, str], str | None],
    *,
    status: CacheStatus = CacheStatus.REFRESHED,
) -> tuple[Path, list[str]]:
    registry_path = tmp_path / "packages" / "skilllint" / "schemas" / "provenance-registry.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps(_registry(), indent=2) + "\n", encoding="utf-8")
    cache_path = tmp_path / ".claude" / "vendor" / "sources" / "hooks.md"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text("fixture", encoding="utf-8")
    calls: list[str] = []

    def fetch(url: str, *, force: bool) -> CacheResult:
        calls.append(url)
        assert force is True
        return CacheResult(cache_path, status, "hooks", url)

    monkeypatch.setattr(refresh, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(refresh, "REGISTRY_PATH", registry_path)
    monkeypatch.setattr(refresh, "fetch_or_cached", fetch)
    monkeypatch.setattr(refresh, "read_section", section)
    return registry_path, calls


def test_refresh_returns_zero_when_authority_is_unchanged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    registry_path, calls = _configure_updater(
        monkeypatch,
        tmp_path,
        lambda _path, heading: "### SessionStart\n" if heading == "Hook events" else '| `type` | `"command"` |',
    )
    before = registry_path.read_bytes()

    result = refresh.main()

    assert result == 0
    assert calls == [AUTHORITY_URL]
    assert registry_path.read_bytes() == before


def test_refresh_writes_only_drifted_claim(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    registry_path, calls = _configure_updater(
        monkeypatch,
        tmp_path,
        lambda _path, heading: "### NewEvent\n" if heading == "Hook events" else '| `type` | `"command"` |',
    )

    result = refresh.main()

    saved = json.loads(registry_path.read_text(encoding="utf-8"))
    claims = saved["claims"]
    assert result == 1
    assert calls == [AUTHORITY_URL]
    assert claims["HK002.valid_event_types"]["expected_value"] == ["NewEvent"]
    assert claims["HK003.valid_hook_types"]["expected_value"] == ["command"]


def test_refresh_accepts_usable_stale_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    registry_path, _calls = _configure_updater(
        monkeypatch,
        tmp_path,
        lambda _path, heading: "### SessionStart\n" if heading == "Hook events" else '| `type` | `"command"` |',
        status=CacheStatus.STALE,
    )
    before = registry_path.read_bytes()

    result = refresh.main()

    assert result == 0
    assert registry_path.read_bytes() == before


@pytest.mark.parametrize("section", [lambda _path, _heading: None, lambda _path, _heading: ""])
def test_refresh_rejects_unusable_authority_without_writing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, section: Callable[[Path, str], str | None]
) -> None:
    registry_path, _calls = _configure_updater(monkeypatch, tmp_path, section)
    before = registry_path.read_bytes()

    with pytest.raises(SystemExit) as raised:
        refresh.main()

    assert raised.value.code == 2
    assert registry_path.read_bytes() == before


def test_refresh_exits_two_when_no_cache_exists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    registry_path, _calls = _configure_updater(monkeypatch, tmp_path, lambda _path, _heading: None)
    before = registry_path.read_bytes()

    def no_cache(url: str, *, force: bool) -> CacheResult:
        raise NoCacheError(url, "offline")

    monkeypatch.setattr(refresh, "fetch_or_cached", no_cache)
    with pytest.raises(SystemExit) as raised:
        refresh.main()

    assert raised.value.code == 2
    assert registry_path.read_bytes() == before


def test_script_exits_three_for_unexpected_exception() -> None:
    command = "import runpy\nfrom unittest.mock import patch\nwith patch('skilllint.vendor_cache.fetch_or_cached', side_effect=RuntimeError('boom')):\n    runpy.run_path('scripts/refresh_claim_values.py', run_name='__main__')"

    result = subprocess.run([sys.executable, "-c", command], cwd=REPO_ROOT, capture_output=True, text=True, check=False)

    assert result.returncode == 3
    assert "RuntimeError: boom" in result.stderr


@pytest.mark.parametrize("exit_code", [0, 1, 2, 3])
def test_wrapper_propagates_refresh_exit_code(tmp_path: Path, exit_code: int) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_uv = bin_dir / "uv"
    fake_uv.write_text(f"#!/usr/bin/env bash\nexit {exit_code}\n", encoding="utf-8")
    fake_uv.chmod(0o755)
    output = tmp_path / "github-output"

    result = subprocess.run(
        ["bash", "scripts/run_claim_refresh.sh"],
        cwd=REPO_ROOT,
        env={**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "GITHUB_OUTPUT": str(output)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output.read_text(encoding="utf-8") == f"exit_code={exit_code}\n"
