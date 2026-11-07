"""Measure the real prek staged-file workflow with prepared wheel environments.

The corpus must be a disposable, self-contained Git repository configured with
one local system hook named skilllint. Its entry must be the published entry;
PATH selects the preinstalled wheel, leaving installation outside timing.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import resource
import secrets
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.bench_paired import (
    EvaluationError,
    Outcome,
    Sample,
    capture_git_state,
    check_environments,
    compare_trees,
    controlled_environment,
    pair_order,
    probe_environment,
    reset_work,
    tree_digest,
    validate_corpus,
)


def index_state(corpus: Path, env: dict[str, str], timeout: float) -> bytes:
    """Capture index semantics, including stages, flags and cached diff bytes.

    Git may refresh stat data during stash/restore, so raw index bytes are also
    retained privately but are not the semantic equality criterion.

    Returns:
        Length-prefixed output of independent Git index inspections.
    """
    git = shutil.which("git")
    if git is None:
        raise EvaluationError("Git executable is required")
    result = bytearray()
    for args in (["ls-files", "--stage", "-z"], ["ls-files", "-v", "-z"], ["diff", "--cached", "--binary"]):
        output = subprocess.run(
            [git, *args], cwd=corpus, env=env, capture_output=True, check=True, timeout=timeout
        ).stdout
        result.extend(len(output).to_bytes(8, "big"))
        result.extend(output)
    return bytes(result)


@dataclass(frozen=True)
class Options:
    """Explicit experiment inputs, supplied by the command line."""

    baseline: Path
    candidate: Path
    prek: Path
    source: Path
    artifacts: Path
    pairs: int
    warmups: int
    timeout: float


def run_once(options: Options, *, python: Path, key: bytes, index: int, endpoint: str) -> Outcome:
    """Run the hook and independently verify index and working-tree preservation.

    Returns:
        A public sample and exact private output bytes.
    """
    corpus = reset_work(options.artifacts / "snapshot", options.artifacts / "work")
    env = controlled_environment(options.artifacts / "work")
    env["PATH"] = f"{python.parent}{os.pathsep}{os.defpath}"
    env["PREK_HOME"] = str(options.artifacts / "work" / "cache" / "prek")
    destination = options.artifacts / f"{index:03}-{endpoint}"
    destination.mkdir()
    (destination / "index-before").write_bytes(index_state(corpus, env, options.timeout))
    capture_git_state(corpus, destination / "git-before")
    result = time_hook(options, corpus=corpus, env=env, key=key, index=index, endpoint=endpoint)
    (destination / "stdout").write_bytes(result.stdout)
    (destination / "stderr").write_bytes(result.stderr)
    capture_git_state(corpus, destination / "git-after")
    (destination / "index-after").write_bytes(index_state(corpus, env, options.timeout))
    if (destination / "index-before").read_bytes() != (destination / "index-after").read_bytes():
        raise EvaluationError("Git index semantics changed")
    compare_trees(options.artifacts / "snapshot", corpus)
    return result


def time_hook(options: Options, *, corpus: Path, env: dict[str, str], key: bytes, index: int, endpoint: str) -> Outcome:
    """Time only framework execution, including its children and output capture.

    Returns:
        Measured counters and raw output; no framework-log normalization.
    """
    command = [str(options.prek), "run", "skilllint", "--stage", "pre-commit", "--color", "never"]
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    started_at = datetime.now(UTC).isoformat()
    started = time.perf_counter()
    result = subprocess.run(command, cwd=corpus, env=env, capture_output=True, check=False, timeout=options.timeout)
    wall = time.perf_counter() - started
    after_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    if endpoint not in {"baseline", "candidate"}:
        raise EvaluationError("Unknown endpoint")
    return Outcome(
        Sample(
            phase="warmup" if index < options.warmups else "measured",
            pair=index,
            endpoint="baseline" if endpoint == "baseline" else "candidate",
            started_at=started_at,
            wall_seconds=wall,
            child_user_seconds=after_usage.ru_utime - usage.ru_utime,
            child_system_seconds=after_usage.ru_stime - usage.ru_stime,
            returncode=result.returncode,
            stdout_digest=hmac.new(key, result.stdout, hashlib.sha256).hexdigest(),
            stderr_digest=hmac.new(key, result.stderr, hashlib.sha256).hexdigest(),
            tree_digest=tree_digest(corpus, key),
        ),
        result.stdout,
        result.stderr,
    )


def evaluate(options: Options) -> None:
    """Snapshot inputs, require runtime parity, and always check source integrity."""
    source, artifacts = options.source.resolve(), options.artifacts.resolve()
    if source.is_relative_to(artifacts) or artifacts.is_relative_to(source):
        raise EvaluationError("Source and artifacts must not contain one another")
    validate_corpus(options.source, options.timeout)
    options.artifacts.mkdir(mode=0o700)
    snapshot = options.artifacts / "snapshot"
    shutil.copytree(options.source, snapshot, symlinks=True)
    try:
        samples = evaluate_snapshot(options)
    finally:
        compare_trees(options.source, snapshot, include_git=True)
    write_public(options.artifacts / "public.json", samples, completed=True)


def evaluate_snapshot(options: Options) -> list[Sample]:
    """Alternate endpoints, retaining incremental allowlisted evidence.

    Returns:
        Verified samples, still incomplete until the source check succeeds.
    """
    key = secrets.token_bytes(32)
    (options.artifacts / "key").write_bytes(key)
    corpus = reset_work(options.artifacts / "snapshot", options.artifacts / "work")
    environment = controlled_environment(options.artifacts / "work")
    endpoints = {"baseline": options.baseline, "candidate": options.candidate}
    metadata = {
        label: probe_environment(python, corpus, environment, options.timeout) for label, python in endpoints.items()
    }
    check_environments(metadata["baseline"], metadata["candidate"])
    (options.artifacts / "metadata.json").write_text(
        json.dumps({label: value.model_dump() for label, value in metadata.items()}, indent=2)
    )
    canonical: tuple[int, bytes, bytes] | None = None
    samples: list[Sample] = []
    public = options.artifacts / "public.json"
    public.write_text(json.dumps({"completed": False, "samples": []}))
    for index in range(options.warmups + options.pairs):
        for endpoint in pair_order(index):
            result = run_once(options, python=endpoints[endpoint], key=key, index=index, endpoint=endpoint)
            outcome = (result.sample.returncode, result.stdout, result.stderr)
            if result.sample.returncode not in {0, 1}:
                raise EvaluationError("Hook execution failed")
            if canonical is None:
                canonical = outcome
            elif outcome != canonical:
                raise EvaluationError("Exact hook output/exit parity failed")
            samples.append(result.sample)
            write_public(public, samples, completed=False)
    for label, python in endpoints.items():
        if probe_environment(python, corpus, environment, options.timeout) != metadata[label]:
            raise EvaluationError("Endpoint metadata changed")
    return samples


def write_public(path: Path, samples: list[Sample], *, completed: bool) -> None:
    """Export only the existing paired evaluator's allowlisted sample fields."""
    path.write_text(
        json.dumps({"completed": completed, "samples": [asdict(s) for s in samples]}, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    """Parse explicit experiment parameters; never overwrite existing evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("baseline", "candidate", "prek", "source", "artifacts"):
        parser.add_argument(f"--{option}", required=True, type=Path)
    parser.add_argument("--pairs", type=int, required=True)
    parser.add_argument("--warmups", type=int, required=True)
    parser.add_argument("--timeout", type=float, required=True)
    args = parser.parse_args()
    if args.pairs < 1 or args.warmups < 0 or args.timeout <= 0:
        parser.error("Require positive pairs/timeout and nonnegative warmups")
    evaluate(
        Options(
            args.baseline.absolute(),
            args.candidate.absolute(),
            args.prek.absolute(),
            args.source.absolute(),
            args.artifacts.absolute(),
            args.pairs,
            args.warmups,
            args.timeout,
        )
    )


if __name__ == "__main__":
    main()
