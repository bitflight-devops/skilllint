from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "docs/repository-surfaces.toml"

EXPECTED_TOP_LEVEL_DIRECTORIES = {
    ".agents",
    ".claude",
    ".cursor",
    ".github",
    ".gsd",
    ".hermes",
    "docs",
    "packages",
    "plugins",
    "scripts",
    "tests",
}
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


def _tracked_top_level_directories() -> set[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-d", "--name-only", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {line for line in result.stdout.splitlines() if line}


def test_all_top_level_repository_directories_are_classified() -> None:
    surfaces = _surfaces()
    classified_roots = {entry["path"].split("/", 1)[0] for entry in surfaces}

    actual = _tracked_top_level_directories()
    assert actual == EXPECTED_TOP_LEVEL_DIRECTORIES
    assert classified_roots >= EXPECTED_TOP_LEVEL_DIRECTORIES


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
    assert by_path["docs"]["architecture_evidence"] == "supporting"
    assert by_path["docs/architecture.md"]["architecture_evidence"] == "primary"
