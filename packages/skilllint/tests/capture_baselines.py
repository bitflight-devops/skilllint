"""Capture the golden files that pin the CLI's default output.

Run from the repository root::

    uv run python packages/skilllint/tests/capture_baselines.py

Goldens must be captured from the commit *before* a behaviour-changing step, never
re-captured to make a failing ``test_default_output_unchanged.py`` pass: the test
exists to prove default output did not change. The only legitimate reasons to
re-run this are adding a case, or a dependency bump (Rich, Typer) that is meant
to change rendering and is reviewed as such. ``baselines/MANIFEST.json`` records
which commit and library versions the current goldens came from; the diff of
that file shows a re-capture in review.

Every run recaptures all cases, deletes goldens of cases that no longer exist,
and rewrites the manifest.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from importlib import metadata
from pathlib import Path

from cli_probe import Endpoints, loopback_endpoints, write_golden
from default_output_cases import (
    BASELINES,
    CASES,
    NO_ENDPOINTS,
    SERVED_BODIES,
    Case,
    Variant,
    golden_path,
    record_case,
    variants_for,
)

MANIFEST = BASELINES / "MANIFEST.json"


def _capture(case: Case, variant: Variant, scratch: Path, docs_endpoints: Endpoints) -> Path:
    endpoints = docs_endpoints if case.docs else NO_ENDPOINTS
    golden = record_case(case, variant, scratch / f"{case.id}--{variant.id}", endpoints)
    target = golden_path(case, variant)
    write_golden(target, golden)
    return target


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, check=True, text=True, cwd=Path(__file__).parent
    ).stdout.strip()


def main() -> int:
    """Recapture every golden and rewrite the manifest.

    Returns:
        Process exit status.
    """
    with loopback_endpoints(SERVED_BODIES) as endpoints, tempfile.TemporaryDirectory() as scratch_name:
        scratch = Path(scratch_name)
        with ThreadPoolExecutor() as pool:
            futures = [
                pool.submit(_capture, case, variant, scratch, endpoints)
                for case in CASES
                for variant in variants_for(case)
            ]
            written = {future.result() for future in futures}
    for stale in set(BASELINES.rglob("*.json")) - written - {MANIFEST}:
        stale.unlink()
    for directory in sorted(BASELINES.iterdir()):
        if directory.is_dir() and not any(directory.iterdir()):
            shutil.rmtree(directory)
    manifest = {
        "captured_at_commit": _git_head(),
        "python": sys.version.split()[0],
        "rich": metadata.version("rich"),
        "typer": metadata.version("typer"),
        "cases": len(CASES),
        "goldens": len(written),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(f"wrote {len(written)} goldens for {len(CASES)} cases\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
