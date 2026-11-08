from __future__ import annotations

from pathlib import Path

from scripts.check_documentation_contract import EXPECTED, _validate_links, validate_documentation_contract

ROOT = Path(__file__).parents[1]


def test_maintained_inventory_and_links_are_valid() -> None:
    assert not validate_documentation_contract(ROOT)
    assert "docs/output-formats.md" in EXPECTED


def test_extensionless_local_links_are_validated(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("[License](LICENSE)\n", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("license\n", encoding="utf-8")

    assert _validate_links("README.md", "[License](LICENSE)", tmp_path) == []
    assert _validate_links("README.md", "[Missing](CONTRIBUTING)", tmp_path)


def test_fragment_only_links_resolve_against_current_document(tmp_path: Path) -> None:
    document = tmp_path / "README.md"
    document.write_text("# Usage\n\n[Usage](#usage)\n", encoding="utf-8")

    assert _validate_links("README.md", "[Usage](#usage)", tmp_path) == []
    assert _validate_links("README.md", "[Missing](#missing)", tmp_path)
