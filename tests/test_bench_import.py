"""Tests for scripts/bench_import.py's aggregation and validation logic."""

from __future__ import annotations

import pytest
from scripts.bench_import import _MODULES, build_gh_benchmark_array, run_benchmark


def test_run_benchmark_reports_min_mean_max_for_each_module() -> None:
    """A single-run benchmark produces min/mean/max/runs keys for every module."""
    result = run_benchmark(runs=1)

    assert result["runs"] == 1
    for label in _MODULES:
        for stat in ("min", "mean", "max"):
            key = f"{label}_{stat}_ms"
            assert key in result
            assert isinstance(result[key], float)
            assert result[key] >= 0


def test_run_benchmark_rejects_zero_runs() -> None:
    """Zero runs must fail loudly instead of crashing on an empty min()/max()."""
    with pytest.raises(ValueError, match="empty"):
        run_benchmark(runs=0)


def test_build_gh_benchmark_array_matches_customsmallerisbetter_shape() -> None:
    """Every entry has the name/value/unit keys github-action-benchmark expects."""
    result = run_benchmark(runs=1)
    entries = build_gh_benchmark_array(result)

    assert len(entries) == len(_MODULES) * 3
    for entry in entries:
        assert entry.keys() == {"name", "value", "unit"}
        assert entry["unit"] == "ms"
        assert isinstance(entry["value"], float)
