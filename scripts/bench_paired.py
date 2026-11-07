"""Paired fresh-process CLI evaluation with private evidence and opaque exports.

See docs/paired-cli-evaluation.md for the experiment contract and limitations.
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
import stat
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from scripts.bench_paired_ingest import EnvironmentMetadata, Options, validate_git_config

Endpoint = Literal["baseline", "candidate"]
Phase = Literal["warmup", "measured"]

# Probe only metadata, not CLI initialization. Versions describe distributions,
# not byte-for-byte equality of their installed files.
_METADATA_PROBE = """
import importlib.metadata, importlib.util, json, platform, re, sys
packages = {}
for dist in importlib.metadata.distributions():
    name = re.sub(r"[-_.]+", "-", dist.metadata["Name"]).lower()
    packages.setdefault(name, []).append(dist.version)
for versions in packages.values():
    versions.sort()
spec = importlib.util.find_spec("skilllint")
print(json.dumps({
    "python_version": sys.version,
    "implementation": platform.python_implementation(),
    "platform": platform.platform(),
    "machine": platform.machine(),
    "executable": sys.executable,
    "module_origin": spec.origin if spec is not None else "",
    "distributions": packages,
}))
"""


class EvaluationError(RuntimeError):
    """The experiment cannot establish comparable, equivalent executions."""


@dataclass(frozen=True)
class Sample:
    """The public allowlist; never add command, output, or filesystem strings."""

    phase: Phase
    pair: int
    endpoint: Endpoint
    started_at: str
    wall_seconds: float
    child_user_seconds: float
    child_system_seconds: float
    returncode: int
    stdout_digest: str
    stderr_digest: str
    tree_digest: str


@dataclass(frozen=True)
class Outcome:
    """Private execution result used for exact byte parity."""

    sample: Sample
    stdout: bytes
    stderr: bytes


def pair_order(index: int) -> tuple[Endpoint, Endpoint]:
    """Alternate AB/BA continuously across warmup and measured pairs.

    Returns:
        The endpoint order for the zero-based pair index.
    """
    return ("baseline", "candidate") if index % 2 == 0 else ("candidate", "baseline")


def controlled_environment(work: Path) -> dict[str, str]:
    """Build a shared, minimal environment rather than inherit user settings.

    Returns:
        Fixed terminal, locale, Git, and disposable home/cache settings.
    """
    return {
        "PATH": os.defpath,
        "HOME": str(work / "home"),
        "XDG_CONFIG_HOME": str(work / "home" / ".config"),
        "XDG_CACHE_HOME": str(work / "cache"),
        "TMPDIR": str(work / "tmp"),
        "TIKTOKEN_CACHE_DIR": str(work / "cache" / "tiktoken"),
        "COLUMNS": "80",
        "LINES": "24",
        "TERM": "dumb",
        "NO_COLOR": "1",
        "FORCE_COLOR": "0",
        "CLICOLOR": "0",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_OPTIONAL_LOCKS": "0",
    }


def tree_entries(root: Path, *, include_git: bool = False) -> Iterator[Path]:
    """Walk deterministically without following directory symlinks.

    Yields:
        Relative paths, optionally including Git metadata.
    """
    for directory, names, files in os.walk(root, followlinks=False):
        names.sort()
        if not include_git:
            names[:] = [name for name in names if name != ".git"]
        for name in sorted([*names, *files]):
            if include_git or name != ".git":
                yield (Path(directory) / name).relative_to(root)


def validate_corpus(root: Path, timeout: float) -> None:
    """Reject indirect source writes and non-copyable or external Git context."""
    if not root.is_dir():
        raise EvaluationError("Corpus must be a directory")
    for relative in tree_entries(root, include_git=True):
        path = root / relative
        mode = path.lstat().st_mode
        if path.is_symlink():
            target = path.readlink()
            try:
                within_root = path.resolve().is_relative_to(root)
            except RuntimeError as error:
                raise EvaluationError("Corpus contains a symlink cycle") from error
            if target.is_absolute() or not within_root:
                raise EvaluationError("Corpus symlinks must resolve within the corpus using relative targets")
            if ".git" in relative.parts:
                git_root = root.joinpath(*relative.parts[: relative.parts.index(".git") + 1])
                if not path.resolve().is_relative_to(git_root):
                    raise EvaluationError("Git symlinks must resolve within their own Git directory")
        elif not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise EvaluationError("Corpus contains a special file that cannot be safely reset")
        if path.name == ".git" and (path.is_symlink() or not path.is_dir()):
            raise EvaluationError("Git files/linked worktrees are unsupported; supply a self-contained Git directory")
        if ".git" in relative.parts and path.name in {"commondir", "alternates"}:
            raise EvaluationError("External Git storage is unsupported; supply a self-contained Git directory")
        if path.name in {"config", "config.worktree"} and path.parent.name == ".git":
            validate_git_config(path.read_text(encoding="utf-8"), timeout)


def reset_work(snapshot: Path, work: Path) -> Path:
    """Restore the same disposable path before every invocation, outside timing.

    Returns:
        The fresh corpus working directory.
    """
    if work.exists():
        shutil.rmtree(work)
    for name in ("home", "cache", "tmp"):
        (work / name).mkdir(parents=True)
    corpus = work / "corpus"
    shutil.copytree(snapshot, corpus, symlinks=True)
    return corpus


def tree_digest(root: Path, key: bytes) -> str:
    """Create a keyed, unambiguous digest without exporting names or contents.

    Returns:
        HMAC-SHA256 of paths, types, permission bits, bytes, and symlink targets.
    """
    digest = hmac.new(key, digestmod=hashlib.sha256)
    for relative in tree_entries(root):
        path = root / relative
        mode = path.lstat().st_mode
        values = [os.fsencode(relative), str(stat.S_IFMT(mode)).encode(), str(stat.S_IMODE(mode)).encode()]
        if path.is_symlink():
            values.append(os.fsencode(path.readlink()))
        elif path.is_file():
            values.append(path.read_bytes())
        for value in values:
            digest.update(len(value).to_bytes(8, "big"))
            digest.update(value)
    return digest.hexdigest()


def compare_trees(first: Path, second: Path, *, include_git: bool = False) -> None:
    """Check actual bytes, types, permissions, and link text, not just digests."""
    paths = list(tree_entries(first, include_git=include_git))
    if paths != list(tree_entries(second, include_git=include_git)):
        raise EvaluationError("Final corpus path parity failed")
    for relative in paths:
        left, right = first / relative, second / relative
        if left.lstat().st_mode != right.lstat().st_mode:
            raise EvaluationError("Final corpus type/permission parity failed")
        if left.is_symlink():
            if left.readlink() != right.readlink():
                raise EvaluationError("Final corpus symlink parity failed")
        elif left.is_file() and left.read_bytes() != right.read_bytes():
            raise EvaluationError("Final corpus file content parity failed")


def capture_git_state(corpus: Path, destination: Path) -> None:
    """Save all Git context privately and separately from the corpus digest.

    This includes config, index, HEAD, refs, objects, local excludes, and shallow
    boundaries. With optional locks disabled, supported CLI workloads must leave
    Git context unchanged; even metadata-only writes invalidate the experiment.
    """
    destination.mkdir()
    for directory, names, files in os.walk(corpus, followlinks=False):
        if ".git" in names or ".git" in files:
            source = Path(directory) / ".git"
            target = destination / source.relative_to(corpus)
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_symlink() or source.is_file():
                shutil.copy2(source, target, follow_symlinks=False)
            else:
                shutil.copytree(source, target, symlinks=True)
            if ".git" in names:
                names.remove(".git")


def probe_environment(python: Path, cwd: Path, env: dict[str, str], timeout: float) -> EnvironmentMetadata:
    """Read and validate endpoint metadata outside the measured interval.

    Returns:
        Strictly validated private interpreter and distribution metadata.
    """
    result = subprocess.run(
        [str(python), "-I", "-c", _METADATA_PROBE], cwd=cwd, env=env, capture_output=True, check=True, timeout=timeout
    )
    return EnvironmentMetadata.model_validate_json(result.stdout)


def check_environments(baseline: EnvironmentMetadata, candidate: EnvironmentMetadata) -> None:
    """Refuse Python/platform drift or any distribution drift except skilllint."""
    for field in ("python_version", "implementation", "platform", "machine"):
        if getattr(baseline, field) != getattr(candidate, field):
            raise EvaluationError("Endpoint Python/platform metadata differs")
    for metadata in (baseline, candidate):
        if not metadata.module_origin or len(metadata.distributions.get("skilllint", [])) != 1:
            raise EvaluationError("Each endpoint must have exactly one installed skilllint distribution")
        if any(len(versions) != 1 for versions in metadata.distributions.values()):
            raise EvaluationError("Ambiguous duplicate installed distributions")
    first = {name: versions for name, versions in baseline.distributions.items() if name != "skilllint"}
    second = {name: versions for name, versions in candidate.distributions.items() if name != "skilllint"}
    if first != second:
        raise EvaluationError("Unrelated installed distribution names/versions differ")


def run_once(
    python: Path,
    options: Options,
    corpus: Path,
    env: dict[str, str],
    *,
    destination: Path,
    key: bytes,
    phase: Phase,
    pair: int,
    endpoint: Endpoint,
) -> Outcome:
    """Time only one fresh isolated CLI subprocess and retain its raw output.

    Returns:
        Exact private output and the allowlisted public timing sample.
    """
    destination.mkdir()
    capture_git_state(corpus, destination / "git-before")
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started_at = datetime.now(UTC).isoformat()
    start = time.perf_counter_ns()
    try:
        result = subprocess.run(
            [str(python), "-I", "-m", "skilllint", *options.cli_args],
            cwd=corpus,
            env=env,
            capture_output=True,
            check=False,
            timeout=options.timeout,
        )
    except subprocess.TimeoutExpired as error:
        (destination / "stdout").write_bytes(error.stdout or b"")
        (destination / "stderr").write_bytes(error.stderr or b"")
        capture_git_state(corpus, destination / "git-after")
        raise
    elapsed = (time.perf_counter_ns() - start) / 1_000_000_000
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    stdout_bytes, stderr_bytes = result.stdout, result.stderr
    (destination / "stdout").write_bytes(stdout_bytes)
    (destination / "stderr").write_bytes(stderr_bytes)
    capture_git_state(corpus, destination / "git-after")
    compare_trees(destination / "git-before", destination / "git-after", include_git=True)
    sample = Sample(
        phase=phase,
        pair=pair,
        endpoint=endpoint,
        started_at=started_at,
        wall_seconds=elapsed,
        child_user_seconds=usage_after.ru_utime - usage_before.ru_utime,
        child_system_seconds=usage_after.ru_stime - usage_before.ru_stime,
        returncode=result.returncode,
        stdout_digest=hmac.digest(key, stdout_bytes, "sha256").hex(),
        stderr_digest=hmac.digest(key, stderr_bytes, "sha256").hex(),
        tree_digest=tree_digest(corpus, key),
    )
    return Outcome(sample, stdout_bytes, stderr_bytes)


def compare_outputs(first: Outcome, second: Outcome) -> None:
    """Require exact return code and stdout/stderr byte equality."""
    if first.sample.returncode != second.sample.returncode:
        raise EvaluationError("Exit status parity failed")
    if first.stdout != second.stdout:
        raise EvaluationError("stdout byte parity failed")
    if first.stderr != second.stderr:
        raise EvaluationError("stderr byte parity failed")
    if first.sample.returncode not in {0, 1}:
        raise EvaluationError("Unexpected CLI exit status")


def export_public(path: Path, samples: list[Sample], key: bytes, metadata: bytes, *, complete: bool) -> None:
    """Write only fixed schema fields and keyed opaque digests, never raw inputs."""
    report = {
        "schema_version": 1,
        "complete": complete,
        "metadata_digest": hmac.digest(key, metadata, "sha256").hex(),
        "samples": [asdict(sample) for sample in samples],
    }
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def run_pairs(options: Options, artifacts: Path, snapshot: Path, key: bytes, metadata: bytes) -> list[Sample]:
    """Run alternating pairs, aborting on drift within or between pairs.

    Returns:
        Samples that still need final source and environment verification.
    """
    samples: list[Sample] = []
    work = artifacts / "work"
    env = controlled_environment(work)
    reference = artifacts / "reference"
    canonical: Outcome | None = None
    try:
        for index in range(options.warmups + options.pairs):
            phase: Phase = "warmup" if index < options.warmups else "measured"
            pair = index if phase == "warmup" else index - options.warmups
            for endpoint in pair_order(index):
                corpus = reset_work(snapshot, work)
                python = options.baseline_python if endpoint == "baseline" else options.candidate_python
                destination = artifacts / f"{phase}-{pair:04d}-{endpoint}"
                outcome = run_once(
                    python,
                    options,
                    corpus,
                    env,
                    destination=destination,
                    key=key,
                    phase=phase,
                    pair=pair,
                    endpoint=endpoint,
                )
                samples.append(outcome.sample)
                if canonical is None:
                    canonical = outcome
                    shutil.copytree(corpus, reference, symlinks=True)
                compare_outputs(canonical, outcome)
                compare_trees(reference, corpus)
        return samples
    finally:
        export_public(artifacts / "public.json", samples, key, metadata, complete=False)


def evaluate(options: Options) -> None:
    """Prepare private evidence, verify comparable endpoints, and run pairs."""
    source = options.corpus.resolve()
    artifacts = options.artifacts.resolve()
    if artifacts.is_relative_to(source) or source.is_relative_to(artifacts):
        raise EvaluationError("Artifact and corpus directories must not contain one another")
    validate_corpus(source, options.timeout)
    artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    snapshot = artifacts / "source"
    shutil.copytree(source, snapshot, symlinks=True)
    try:
        evaluate_snapshot(options, artifacts, snapshot)
    except (EvaluationError, ValidationError, OSError, ValueError, subprocess.SubprocessError) as error:
        (artifacts / "failure.txt").write_text(str(error), encoding="utf-8")
        raise


def evaluate_snapshot(options: Options, artifacts: Path, snapshot: Path) -> None:
    """Verify source/environment on success and preserve incomplete evidence on failure."""
    key = secrets.token_bytes(32)  # SHA256 key length; private to prevent content-guessing attacks.
    (artifacts / "digest-key").write_bytes(key)
    work = artifacts / "work"
    corpus = reset_work(snapshot, work)
    env = controlled_environment(work)
    metadata = b""
    samples: list[Sample] = []
    export_public(artifacts / "public.json", samples, key, metadata, complete=False)
    try:
        baseline = probe_environment(options.baseline_python, corpus, env, options.timeout)
        candidate = probe_environment(options.candidate_python, corpus, env, options.timeout)
        metadata = json.dumps(
            {
                "options": options.model_dump(mode="json"),
                "environment": env,
                "baseline": baseline.model_dump(),
                "candidate": candidate.model_dump(),
            },
            indent=2,
        ).encode()
        (artifacts / "metadata.json").write_bytes(metadata)
        export_public(artifacts / "public.json", samples, key, metadata, complete=False)
        check_environments(baseline, candidate)
        samples = run_pairs(options, artifacts, snapshot, key, metadata)
        for python, before in ((options.baseline_python, baseline), (options.candidate_python, candidate)):
            if probe_environment(python, corpus, env, options.timeout) != before:
                raise EvaluationError("Endpoint metadata changed during evaluation")
    finally:
        # Check on failure too. This is detection, not a sandbox for an untrusted
        # executable or malicious configuration. Never modify or restore source.
        compare_trees(snapshot, options.corpus.resolve(), include_git=True)
    export_public(artifacts / "public.json", samples, key, metadata, complete=True)


def parse_options(argv: list[str] | None = None) -> Options:
    """Validate command-line configuration before touching the source.

    Returns:
        Concrete experiment options with absolute interpreter paths.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-python", type=Path, required=True)
    parser.add_argument("--candidate-python", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True, help="New private directory; must not already exist")
    parser.add_argument("--warmups", type=int, default=2, help="Warmup pairs (experiment default: 2)")
    parser.add_argument("--pairs", type=int, default=10, help="Measured pairs (experiment default: 10)")
    parser.add_argument("--timeout", type=float, required=True, help="Per-process timeout in seconds")
    parser.add_argument("cli_args", nargs=argparse.REMAINDER)
    options = Options.model_validate(vars(parser.parse_args(argv)))
    # Do not resolve interpreter symlinks: that would discard virtualenv identity.
    options.baseline_python = options.baseline_python.absolute()
    options.candidate_python = options.candidate_python.absolute()
    return options


def main(argv: list[str] | None = None) -> int:
    """Run the evaluator without printing potentially private exception details.

    Returns:
        Zero on verified parity, two on invalid or failed evaluation.
    """
    try:
        options = parse_options(argv)
        evaluate(options)
    except (EvaluationError, ValidationError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Paired evaluation failed ({type(error).__name__}); no valid performance conclusion.", file=sys.stderr)
        return 2
    print(
        "Paired evaluation completed with exact output and corpus parity. public.json is an allowlisted export; review before sharing."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
