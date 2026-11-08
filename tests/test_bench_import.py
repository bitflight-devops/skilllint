"""Tests for scripts/bench_import.py's GitHub benchmark output."""

from __future__ import annotations

from scripts.bench_import import build_gh_benchmark_array, run_benchmark


def test_build_gh_benchmark_array_matches_customsmallerisbetter_shape() -> None:
    """Every entry has the name/value/unit keys github-action-benchmark expects."""
    result = run_benchmark(runs=1)
    entries = build_gh_benchmark_array(result)

    for entry in entries:
        assert entry.keys() == {"name", "value", "unit"}
        assert entry["unit"] == "ms"
        assert isinstance(entry["value"], float)
