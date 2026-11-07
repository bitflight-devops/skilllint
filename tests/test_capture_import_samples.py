"""Tests for the raw lifecycle recorder; no real timing claims."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_capture_preserves_timer_values_order_and_restores_harness(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts"))
    recorder = importlib.import_module("capture_import_samples")
    harness = recorder.bench_import
    original_modules = harness._MODULES
    values = iter([9.0, 0.1, 0.3, 8.0, 0.2, 0.4])

    def measure(module):
        return next(values)

    monkeypatch.setattr(harness, "_run_once", measure)
    result = recorder.capture(2, 1, True)
    assert [s["module"] for s in result["samples"]] == ["skilllint.rules"] * 3 + ["skilllint"] * 3
    assert [s["role"] for s in result["samples"]] == ["warmup", "measured", "measured"] * 2
    assert [s["seconds"] for s in result["samples"]] == [9.0, 0.1, 0.3, 8.0, 0.2, 0.4]
    assert result["aggregate"]["warm_cache_import_rules_mean_ms"] == pytest.approx(200)
    assert harness._run_once is measure
    assert harness._MODULES is original_modules


def test_capture_restores_harness_after_failure(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts"))
    recorder = importlib.import_module("capture_import_samples")
    harness = recorder.bench_import
    original_modules = harness._MODULES

    def fail(module):
        raise RuntimeError(module)

    monkeypatch.setattr(harness, "_run_once", fail)
    with pytest.raises(RuntimeError, match=r"skilllint\.rules"):
        recorder.capture(1, 0, True)
    assert harness._run_once is fail
    assert harness._MODULES is original_modules


def test_capture_zero_warmups_preserves_legacy_aggregate(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts"))
    recorder = importlib.import_module("capture_import_samples")

    def measure(module):
        return 0.125

    monkeypatch.setattr(recorder.bench_import, "_run_once", measure)
    result = recorder.capture(1, 0, False)
    assert [s["module"] for s in result["samples"]] == ["skilllint", "skilllint.rules"]
    assert all(s["role"] == "measured" for s in result["samples"])
    assert result["aggregate"]["import_package_mean_ms"] == 125
    assert "warmups" not in result["aggregate"]
