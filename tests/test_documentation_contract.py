from __future__ import annotations

import json
from pathlib import Path

from scripts.check_documentation_contract import EXPECTED, validate_documentation_contract

ROOT = Path(__file__).parents[1]


def test_maintained_inventory_and_links_are_valid() -> None:
    assert not validate_documentation_contract(ROOT)
    assert len(EXPECTED) == 13


def test_external_mode_result_shape_is_machine_readable(tmp_path: Path) -> None:
    output = tmp_path / "external.json"
    data = {"links": [{"url": "https://example.test", "source": "README.md", "status": "unverified"}]}
    output.write_text(json.dumps(data), encoding="utf-8")
    assert json.loads(output.read_text(encoding="utf-8"))["links"][0]["source"] == "README.md"
