"""Track metadata-bearing result groups across accumulation and owner moves."""

from __future__ import annotations

from pathlib import Path

import pytest

from skilllint.models import AppliedFix, ValidationIssue, ValidationResult
from skilllint.scan_runtime import _clear_changed_source_spans, _located_result_sources, _rebase_collected
from skilllint.source_location import SourceLocation, SourcePosition


def _result(path: Path | None) -> ValidationResult:
    return ValidationResult(
        passed=True,
        errors=[],
        warnings=[],
        info=[
            ValidationIssue(
                field="label",
                severity="info",
                message="finding",
                code="LK004",
                source_location=SourceLocation(path=path, start=SourcePosition(line=2, column=3))
                if path is not None
                else None,
            )
        ],
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_location_index_survives_owner_collision_and_later_rewrite(tmp_path: Path, reverse: bool) -> None:
    old, new = tmp_path / "old", tmp_path / "new"
    source = old / "guide.md"
    other = tmp_path / "unrelated.md"
    entries = [
        (old, [("repeat", _result(None)), ("repeat", _result(source))]),
        (new, [("repeat", _result(other)), ("repeat", _result(None))]),
    ]
    results = dict(reversed(entries) if reverse else entries)
    index = {path: _located_result_sources(groups) for path, groups in results.items()}
    identities = {old: old, new: new, source: source, other: other}
    _rebase_collected(results, [], identities, old, new, canonical_old=old, located_results=index)
    assert list(results) == [new]
    assert index == {new: {0: frozenset({other}), 3: frozenset({new / "guide.md"})}}
    moved_source = new / "guide.md"
    fix = AppliedFix(path=moved_source, validator="frontmatter", codes=("FM004",), description="rewrite")
    _clear_changed_source_spans(results, [fix], identities, located_results=index)
    locations = [result.info[0].source_location for _name, result in results[new]]
    assert locations == [
        SourceLocation(path=other, start=SourcePosition(line=2, column=3)),
        None,
        None,
        SourceLocation(path=moved_source),
    ]
    final = tmp_path / "final"
    _rebase_collected(results, [], identities, new, final, canonical_old=new, located_results=index)
    assert index == {final: {0: frozenset({other}), 3: frozenset({final / "guide.md"})}}
    assert results[final][3][1].info[0].source_location == SourceLocation(path=final / "guide.md")


@pytest.mark.parametrize("operation", ["rename", "rewrite"])
def test_unrelated_source_groups_are_not_transformed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    from skilllint import scan_runtime

    source = tmp_path / "other.md"
    plain = _result(None)
    located = _result(source)
    results = {tmp_path: [("plain", plain), ("located", located)]}
    index = {tmp_path: _located_result_sources(results[tmp_path])}
    original = scan_runtime._map_changed_issues
    visited: list[ValidationResult] = []

    def observe(result, transform):
        visited.append(result)
        return original(result, transform)

    monkeypatch.setattr(scan_runtime, "_map_changed_issues", observe)
    old, new = tmp_path / "old", tmp_path / "new"
    if operation == "rename":
        _rebase_collected(results, [], {source: source}, old, new, canonical_old=old, located_results=index)
    else:
        fix = AppliedFix(path=old, validator="frontmatter", codes=("FM004",), description="rewrite")
        _clear_changed_source_spans(results, [fix], {source: source}, located_results=index)
    assert visited == []
    assert results[tmp_path][0][1] is plain
