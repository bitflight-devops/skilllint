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


def test_warmups_are_excluded_and_each_module_is_prepared(monkeypatch: pytest.MonkeyPatch) -> None:
    """Discard each module's first observation without warming the other early."""
    calls: list[str] = []
    timings = iter([99.0, 0.1, 0.3, 88.0, 0.2, 0.4])

    def measure(module: str) -> float:
        calls.append(module)
        return next(timings)

    monkeypatch.setattr("scripts.bench_import._run_once", measure)
    result = run_benchmark(runs=2, warmups=1)
    assert calls == ["skilllint"] * 3 + ["skilllint.rules"] * 3
    assert result["warm_cache_import_package_mean_ms"] == 200.0
    assert result["warm_cache_import_rules_mean_ms"] == 300.0
    assert result["warmups"] == 1
    assert "import_package_mean_ms" not in result
    entries = build_gh_benchmark_array(result)
    assert all(str(entry["name"]).startswith("warm_cache_import_") for entry in entries)


def test_legacy_default_has_no_excluded_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    """Existing callers retain the exact old invocation count and result shape."""
    calls: list[str] = []

    def measure(module: str) -> float:
        calls.append(module)
        return 0.1

    monkeypatch.setattr("scripts.bench_import._run_once", measure)
    result = run_benchmark(runs=1)
    assert calls == ["skilllint", "skilllint.rules"]
    assert "warmups" not in result
    assert result["import_package_mean_ms"] == 100.0


def test_negative_warmups_are_rejected() -> None:
    """Invalid preparation must fail before any imports execute."""
    with pytest.raises(ValueError, match="warmups"):
        run_benchmark(warmups=-1)


def test_warm_cache_real_subprocess_measurement() -> None:
    """Opt-in preparation works with actual fresh interpreter processes."""
    result = run_benchmark(runs=1, warmups=1)
    assert result["warm_cache_import_rules_mean_ms"] > 0


def test_workflow_uses_one_harness_and_immutable_pr_base() -> None:
    """Both sides opt into the same named preparation and preserved script."""
    from pathlib import Path

    workflow = (Path(__file__).parents[1] / ".github/workflows/benchmark.yml").read_text()
    job = workflow.split("  benchmark-import:\n", 1)[1].split("  post-pr-comment:\n", 1)[0]
    assert job.count(".venv/bin/python /tmp/skilllint-bench-import.py --warmups 1") == 2
    assert "cp scripts/bench_import.py /tmp/skilllint-bench-import.py" in job
    assert job.count("fetch-depth: 0") == 2
    assert "github.workflow_sha" in job
    assert job.index("cp scripts/bench_import.py") < job.index("- name: Checkout compare ref")
    assert job.count("if: github.event_name == 'pull_request' || inputs.base_ref != ''") == 5
    assert "github.event.pull_request.base.sha" in job
    assert "github.event.pull_request.base.ref" not in job
    assert "benchmark-results-import-warm-cache-compare" in job
    assert "benchmark-results-import-warm-cache-base" in job


def test_warm_cache_metrics_are_smaller_is_better(monkeypatch: pytest.MonkeyPatch) -> None:
    """New series must not invert regression arrows in the PR report."""
    import importlib
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts"))
    comment = importlib.import_module("bench_comment")
    for module in ("package", "rules"):
        for stat in ("min", "mean", "max"):
            name = f"warm_cache_import_{module}_{stat}_ms"
            assert "🔴" in comment.change_cell(name, 100.0, 150.0, 1.3)
            assert "✅" in comment.change_cell(name, 100.0, 90.0, 1.3)
