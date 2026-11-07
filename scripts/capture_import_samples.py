"""Record raw observations from the unchanged import benchmark timer.

This diagnostic wrapper is for the lifecycle experiment, not the CI series.
Run it with the target editable environment's Python from that checkout.
"""

# The diagnostic deliberately wraps private harness seams to preserve its bytes.
# ruff: noqa: SLF001

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import TypedDict
from unittest.mock import patch

import bench_import


class Observation(TypedDict):
    """One child import, including excluded preparation."""

    module: str
    index: int
    role: str
    seconds: float


class Capture(TypedDict):
    """Typed record from the diagnostic wrapper."""

    harness_sha256: str
    reverse_module_order: bool
    warmups: int
    aggregate: dict[str, float | int]
    samples: list[Observation]


def capture(runs: int, warmups: int, reverse: bool) -> Capture:
    """Capture excluded and measured observations without changing the timer.

    Args:
        runs: Measured samples per module.
        warmups: Excluded samples per module.
        reverse: Whether to visit rules before the package.

    Returns:
        Aggregates, raw observations, and the benchmark's byte identity.
    """
    original = bench_import._run_once
    original_modules = bench_import._MODULES
    samples: list[Observation] = []
    counts: dict[str, int] = {}

    def record(module: str) -> float:
        seconds = original(module)
        index = counts.get(module, 0)
        samples.append({
            "module": module,
            "index": index,
            "role": "warmup" if index < warmups else "measured",
            "seconds": seconds,
        })
        counts[module] = index + 1
        return seconds

    modules = dict(reversed(original_modules.items())) if reverse else original_modules
    with patch.object(bench_import, "_run_once", record), patch.object(bench_import, "_MODULES", modules):
        aggregate = bench_import.run_benchmark(runs=runs, warmups=warmups)
    return {
        "harness_sha256": hashlib.sha256(Path(bench_import.__file__).read_bytes()).hexdigest(),
        "reverse_module_order": reverse,
        "warmups": warmups,
        "aggregate": aggregate,
        "samples": samples,
    }


def main() -> None:
    """Print one capture as JSON; use shell redirection for incremental evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--warmups", type=int, choices=(0, 1), required=True)
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be >= 1")
    print(json.dumps(capture(args.runs, args.warmups, args.reverse), indent=2))


if __name__ == "__main__":
    main()
