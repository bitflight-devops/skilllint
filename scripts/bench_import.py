#!/usr/bin/env python3
"""Import-time benchmark for the ``skilllint`` package and its rule registry.

Measures the wall-clock cost of ``import skilllint.rules`` in a fresh
subprocess. A subprocess is required because Python caches imports after the
first import in a process, so the cost cannot be measured in-process after
warmup.

``import skilllint.rules`` is what ``packages/skilllint/plugin_validator.py``
does eagerly at module load (see the ``import skilllint.rules`` line there)
so that all 51 ``@skilllint_rule(...)`` decorator calls register into
``RULE_REGISTRY``. Each call constructs a Pydantic ``RuleEntry`` (and, for
most rules, a nested ``RuleAuthority``), so this import triggers 51 Pydantic
validation passes on every ``skilllint`` CLI cold start.

For context/comparison, this script also measures ``import skilllint`` alone.
``packages/skilllint/__init__.py`` only imports ``skilllint.schemas`` and
``skilllint.version`` — it does not import ``plugin_validator`` or
``skilllint.rules`` — so this is a genuinely separate, lighter import path,
not an artificial split of the same work.

Usage::

    python scripts/bench_import.py
    python scripts/bench_import.py --output scripts/results/bench_import_gh.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_MODULES: dict[str, str] = {"import_package": "skilllint", "import_rules": "skilllint.rules"}


def _run_once(module: str) -> float:
    """Import *module* in a fresh subprocess and return wall-clock seconds.

    Args:
        module: Fully-qualified module name to import (e.g. ``"skilllint.rules"``).

    Returns:
        Elapsed wall-clock time in seconds, as reported by the subprocess.

    Raises:
        subprocess.CalledProcessError: If the subprocess exits non-zero.
        ValueError: If the subprocess did not print a parseable float.
    """
    code = f"import time; t = time.perf_counter(); import {module}; print(time.perf_counter() - t)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True, timeout=30)
    # Only the last line is the timing print; anything printed earlier during
    # import (e.g. a future warning) must not break parsing.
    return float(result.stdout.strip().splitlines()[-1])


def run_benchmark(runs: int = 3) -> dict[str, float | int]:
    """Run the import-time benchmark and return aggregated timing data.

    Args:
        runs: Number of measurement repetitions per module.

    Returns:
        Dictionary with ``{label}_min_ms``, ``{label}_mean_ms``, and
        ``{label}_max_ms`` keys for each module in :data:`_MODULES`, plus
        ``runs``.
    """
    result: dict[str, float | int] = {"runs": runs}
    for label, module in _MODULES.items():
        timings = [_run_once(module) * 1000.0 for _ in range(runs)]
        result[f"{label}_min_ms"] = round(min(timings), 3)
        result[f"{label}_mean_ms"] = round(sum(timings) / len(timings), 3)
        result[f"{label}_max_ms"] = round(max(timings), 3)
    return result


def build_gh_benchmark_array(result: dict[str, float | int]) -> list[dict[str, float | str]]:
    """Build a ``customSmallerIsBetter`` JSON array for github-action-benchmark.

    Args:
        result: Aggregated timing data returned by :func:`run_benchmark`.

    Returns:
        List of benchmark entry dicts, each with ``name``, ``value``, and
        ``unit`` keys, suitable for the ``customSmallerIsBetter`` tool format.
    """
    entries: list[dict[str, float | str]] = []
    for label in _MODULES:
        for stat in ("min", "mean", "max"):
            key = f"{label}_{stat}_ms"
            entries.append({"name": key, "value": float(result[key]), "unit": "ms"})
    return entries


def main() -> None:
    """Entry point: parse CLI args, run benchmark, print JSON to stdout.

    When ``--output`` is provided, also write the ``customSmallerIsBetter``
    JSON array to the given file path.
    """
    parser = argparse.ArgumentParser(description="Import-time benchmark for skilllint and skilllint.rules")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write customSmallerIsBetter JSON array to this file path",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        metavar="N",
        help="Number of subprocess measurement repetitions per module (default: 3)",
    )
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be >= 1")
    output_path: Path | None = args.output

    result = run_benchmark(runs=args.runs)
    print(json.dumps(result, indent=2))

    if output_path is not None:
        gh_array = build_gh_benchmark_array(result)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(gh_array, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
