"""Property and unit tests for the ``hooks.json`` boundary ingest.

Covers the four structural failures HK001 owns plus the strictness required by
``docs/TYPING_POLICY.md`` 8.2: a producer that emits the wrong JSON type where an
object is declared must be rejected, not coerced.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from hypothesis import given, strategies as st

from skilllint.boundary.hooks_json_ingest import HooksJsonDefect, ingest_hooks_json


def _write(directory: Path, text: str) -> Path:
    """Write *text* to a ``hooks.json`` inside *directory*.

    Args:
        directory: Directory to write into.
        text: Raw file content.

    Returns:
        Path to the written file.
    """
    path = directory / "hooks.json"
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_document_returns_hooks_mapping(tmp_path: Path) -> None:
    entry = {"type": "command", "command": "echo hi"}
    path = _write(tmp_path, json.dumps({"hooks": {"PreToolUse": [{"hooks": [entry]}]}}))

    assert ingest_hooks_json(path) == {"PreToolUse": [{"hooks": [entry]}]}


def test_nested_structure_is_not_validated(tmp_path: Path) -> None:
    """HK002/HK003 report on nested shape, so the boundary must let it through."""
    path = _write(tmp_path, json.dumps({"hooks": {"NotAnEvent": "not even a list"}}))

    assert ingest_hooks_json(path) == {"NotAnEvent": "not even a list"}


def test_missing_file_is_a_read_defect(tmp_path: Path) -> None:
    result = ingest_hooks_json(tmp_path / "absent.json")

    assert isinstance(result, HooksJsonDefect)
    assert result.field == "(file)"


def test_malformed_json_is_a_syntax_defect(tmp_path: Path) -> None:
    result = ingest_hooks_json(_write(tmp_path, "{not valid json}"))

    assert isinstance(result, HooksJsonDefect)
    assert result.field == "(json)"
    assert result.message.startswith("Invalid JSON syntax")


def test_missing_hooks_key_is_a_defect(tmp_path: Path) -> None:
    result = ingest_hooks_json(_write(tmp_path, json.dumps({"other": {}})))

    assert isinstance(result, HooksJsonDefect)
    assert result.message == "Missing required top-level 'hooks' key"


def test_non_object_root_is_a_defect(tmp_path: Path) -> None:
    result = ingest_hooks_json(_write(tmp_path, json.dumps([{"hooks": {}}])))

    assert isinstance(result, HooksJsonDefect)
    assert result.message == "Missing required top-level 'hooks' key"


def test_non_object_hooks_value_is_a_defect(tmp_path: Path) -> None:
    result = ingest_hooks_json(_write(tmp_path, json.dumps({"hooks": ["PreToolUse"]})))

    assert isinstance(result, HooksJsonDefect)
    assert result.message == "'hooks' value must be an object"


def test_hooks_value_string_is_not_coerced(tmp_path: Path) -> None:
    """Strict mode: a JSON string where an object is declared is a producer error."""
    result = ingest_hooks_json(_write(tmp_path, json.dumps({"hooks": '{"PreToolUse": []}'})))

    assert isinstance(result, HooksJsonDefect)
    assert result.message == "'hooks' value must be an object"


@given(st.dictionaries(st.text(), st.integers()))
def test_arbitrary_hooks_mapping_round_trips(mapping: dict[str, int]) -> None:
    """Any JSON object under ``hooks`` is returned unchanged, never raising.

    The strategies are unbounded: the boundary imposes no size limit of its own, so capping
    the generated mapping would be an invented constraint and would narrow the coverage this
    property claims. Hypothesis's own default sizing governs instead.

    Uses ``tempfile`` rather than the ``tmp_path`` fixture because Hypothesis
    rejects function-scoped fixtures inside ``@given``.
    """
    with tempfile.TemporaryDirectory() as tmp:
        assert ingest_hooks_json(_write(Path(tmp), json.dumps({"hooks": mapping}))) == mapping
