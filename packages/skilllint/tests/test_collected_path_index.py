"""Indexed rename bookkeeping stays equivalent without visiting unrelated owners."""

from __future__ import annotations

import ntpath
from copy import deepcopy
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
from typing import no_type_check

import pytest
from hypothesis import given, strategies as st

from skilllint import scan_runtime
from skilllint.models import AppliedFix, ValidationIssue, ValidationResult
from skilllint.scan_runtime import _CollectedSources, _located_result_sources, _rebase_collected
from skilllint.source_location import SourceLocation, SourcePosition


def _result(*sources: Path) -> ValidationResult:
    return ValidationResult(
        passed=False,
        errors=[
            ValidationIssue(
                field="link",
                severity="error",
                message="finding",
                code="LK004",
                source_location=SourceLocation(path=source, start=SourcePosition(line=2, column=3)),
            )
            for source in sources
        ],
        warnings=[],
        info=[],
    )


def _fix(path: Path) -> AppliedFix:
    return AppliedFix(path=path, validator="frontmatter", codes=("FM010",), description="rename")


def _index(results, fixes, identities) -> _CollectedSources:
    collected = _CollectedSources(
        identities=identities, results={path: _located_result_sources(groups) for path, groups in results.items()}
    )
    for path in results:
        collected.refresh_owner(path)
    collected.add_fixes(fixes, 0)
    return collected


@given(
    order=st.permutations(range(5)),
    alias=st.sampled_from(["old/guide.md", "alias/guide.md", "old/../outside/guide.md", "other/../old/guide.md"]),
)
def test_indexed_rebases_match_full_scan_through_collisions_and_nested_moves(order, alias) -> None:
    """The unindexed transform is the oracle, including duplicate group names."""
    old, new, final = Path("old"), Path("new"), Path("final")
    source = Path(alias)
    inner = old / "inner" / "SKILL.md"
    entries = [
        (old, [("repeat", _result(source))]),
        (new, [("repeat", _result(Path("elsewhere.md")))]),
        (Path("aggregate"), [("repeat", _result(source, inner)), ("repeat", _result())]),
        (old / "inner", [("repeat", _result(inner))]),
        (Path("unrelated"), [("repeat", _result(Path("untouched.md")))]),
    ]
    results = dict(entries[index] for index in order)
    fixes = [_fix(source), _fix(inner), _fix(Path("untouched.md"))]
    identities = {path: path for path in results}
    identities.update({source: old / "guide.md", inner: inner})
    expected, expected_fixes, expected_identities = deepcopy((results, fixes, identities))
    collected = _index(results, fixes, identities)
    for before, after in [(old, new), (new / "inner", new / "nested"), (new, final)]:
        _rebase_collected(expected, expected_fixes, expected_identities, before, after, canonical_old=before)
        _rebase_collected(
            results,
            fixes,
            identities,
            before,
            after,
            canonical_old=before,
            located_results=collected.results,
            collected_sources=collected,
        )
        assert list(results) == list(expected)
        assert results == expected
        assert fixes == expected_fixes
        assert collected.results == {
            path: groups for path, values in results.items() if (groups := _located_result_sources(values))
        }


def test_new_snapshot_updates_shared_source_dependencies(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(first, target_is_directory=True)
    source = alias / "guide.md"
    results = {tmp_path / "aggregate": [("links", _result(source))]}
    collected = _CollectedSources()
    collected.add({}, results)
    alias.unlink()
    alias.symlink_to(second, target_is_directory=True)
    fresh = {tmp_path / "fresh": [("links", _result(source))]}
    collected.add(results, fresh)
    results.update(fresh)
    candidates = collected.affected_paths(second)
    assert set(collected.affected_owners(candidates)) == set(results)
    assert collected.affected_paths(first) == set()


@no_type_check  # PureWindowsPath deliberately exercises Windows equality on every host.
def test_indexed_case_only_windows_move_preserves_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scan_runtime, "os", SimpleNamespace(sep="\\", path=ntpath))
    old = PureWindowsPath("skills", "Test-Skill")
    new = PureWindowsPath("skills", "test-skill")
    source = PureWindowsPath("alias", "CLAUDE.md")
    identity = old / "CLAUDE.md"
    results = {source: [("frontmatter", _result())], old: [("other", _result())]}
    fixes = [_fix(source)]
    identities = {source: identity, old: old}
    expected, expected_fixes, expected_identities = deepcopy((results, fixes, identities))
    collected = _index(results, fixes, identities)
    _rebase_collected(expected, expected_fixes, expected_identities, old, new, canonical_old=old)
    _rebase_collected(
        results,
        fixes,
        identities,
        old,
        new,
        canonical_old=old,
        located_results=collected.results,
        collected_sources=collected,
    )
    assert [str(path) for path in results] == [str(path) for path in expected]
    assert results == expected
    assert [str(fix.path) for fix in fixes] == [str(fix.path) for fix in expected_fixes]


def test_indexed_rewrite_clears_all_shared_source_spans(tmp_path: Path) -> None:
    source = tmp_path / "rewritten.md"
    other = tmp_path / "other.md"
    results = {
        tmp_path / "aggregate": [("links", _result(source, other))],
        source: [("frontmatter", _result(source))],
        other: [("frontmatter", _result(other))],
    }
    identities = {path: path for path in results}
    collected = _index(results, [], identities)
    expected = deepcopy(results)
    fixes = [_fix(source)]
    scan_runtime._clear_changed_source_spans(expected, fixes, identities)
    scan_runtime._clear_changed_source_spans(
        results, fixes, identities, located_results=collected.results, collected_sources=collected
    )
    assert results == expected


@pytest.mark.parametrize("size", [20, 200])
def test_sibling_renames_only_visit_their_collected_dependencies(monkeypatch: pytest.MonkeyPatch, size: int) -> None:
    """Work grows with affected records rather than all previous sibling fixes."""
    results = {}
    fixes = []
    collected = _CollectedSources()
    original = scan_runtime._rebase_path_identity
    calls = 0

    def count(*args):
        nonlocal calls
        calls += 1
        return original(*args)

    monkeypatch.setattr(scan_runtime, "_rebase_path_identity", count)
    for index in range(size):
        old, new = Path(f"old-{index}"), Path(f"new-{index}")
        source = old / "SKILL.md"
        fresh = {source: [("frontmatter", _result(source))]}
        # Use explicit saved identities, independent of filesystem access.
        collected.identities[source] = source
        collected.results[source] = _located_result_sources(fresh[source])
        results.update(fresh)
        collected.refresh_owner(source)
        fixes.append(_fix(source))
        collected.add_fixes(fixes, len(fixes) - 1)
        _rebase_collected(
            results,
            fixes,
            collected.identities,
            old,
            new,
            canonical_old=old,
            located_results=collected.results,
            collected_sources=collected,
        )
    # Each move transforms its owner, source eligibility, source, and fix once.
    assert calls == 4 * size
    assert list(results) == [Path(f"new-{index}/SKILL.md") for index in range(size)]
