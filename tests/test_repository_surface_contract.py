from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "docs/repository-surfaces.toml"

ALLOWED_KINDS = {
    "product",
    "project-tooling",
    "agent-runtime",
    "generated-state",
    "vendor",
    "historical-planning",
    "test-fixture",
}
ALLOWED_EVIDENCE = {"primary", "supporting", "task-only"}


def _surfaces() -> list[dict[str, str]]:
    data = tomllib.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["version"] == 1
    return data["surface"]


def _is_classified(path: str, surface_paths: set[str]) -> bool:
    return any(path == surface or path.startswith(f"{surface}/") for surface in surface_paths)


def test_all_tracked_repository_subtrees_are_classified() -> None:
    surface_paths = {entry["path"] for entry in _surfaces()}

    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    tracked_paths = {path for path in tracked if "/" in path}
    unclassified_paths = sorted(path for path in tracked_paths if not _is_classified(path, surface_paths))

    assert not unclassified_paths, f"tracked paths missing repository surface classification: {unclassified_paths}"


def test_surface_matching_is_segment_aware() -> None:
    surfaces = {"packages/skilllint"}

    assert _is_classified("packages/skilllint/models.py", surfaces)
    assert not _is_classified("packages/skilllint-extra/module.py", surfaces)
    assert not _is_classified("packages/another-product/module.py", surfaces)


def test_surface_entries_are_unique_valid_and_existing() -> None:
    surfaces = _surfaces()
    paths = [entry["path"] for entry in surfaces]

    assert len(paths) == len(set(paths))
    for entry in surfaces:
        assert entry["kind"] in ALLOWED_KINDS
        assert entry["architecture_evidence"] in ALLOWED_EVIDENCE
        assert entry["description"].strip()
        assert (ROOT / entry["path"]).exists()


def test_specific_non_product_overrides_are_task_only() -> None:
    by_path = {entry["path"]: entry for entry in _surfaces()}

    for path in (
        ".agents",
        ".claude",
        ".claude/vendor",
        ".cursor",
        ".gsd",
        ".hermes",
        "tests/fixtures",
        "packages/skilllint/tests/fixtures",
    ):
        assert by_path[path]["architecture_evidence"] == "task-only"

    assert by_path["packages/skilllint"]["kind"] == "product"
    assert by_path["packages/skilllint"]["architecture_evidence"] == "primary"
    assert by_path["docs/architecture.md"]["architecture_evidence"] == "primary"
