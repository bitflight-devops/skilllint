# Paired CLI evaluation

`scripts/bench_paired.py` compares two installed Skilllint endpoints using fresh
`python -I -m skilllint` processes. It is separate from `bench_io.py`, which
measures one executable from PATH and does not enforce paired output parity.
This harness creates new evidence. It does not reconstruct historical samples.

## Run

Use a POSIX host with Python 3.11+ and the project's Pydantic dependency for the
runner, plus Git when the corpus contains Git configuration. Prepare both endpoint environments before starting. Install the two
Skilllint revisions with the same interpreter build and matching distribution
names/versions for **every other installed distribution**, including tooling.
Only the `skilllint` distribution may differ. Install from known artifacts and
retain wheel hashes/revision identities separately when stronger provenance is
needed: matching package versions do not prove matching installed bytes.

```sh
uv run python -m scripts.bench_paired \
  --baseline-python /path/to/baseline/bin/python \
  --candidate-python /path/to/candidate/bin/python \
  --corpus /path/to/corpus \
  --artifacts /path/to/new-private-results \
  --warmups 2 --pairs 10 --timeout 120 \
  -- check --fix .
```

The paths above are placeholders, not a bundled corpus or published dataset.
Run `check .` without `--fix` for a scan. Other CLI arguments follow `--` and
must use targets relative to the disposable corpus. Absolute targets and `..`
path components are rejected, including `--option=path` values. Interpreter
symlinks are not resolved, preserving virtualenv selection.

`--timeout` is required and applies separately to every subprocess. The defaults
of two warmup pairs and ten measured pairs are experiment parameters, not a
statistical confidence claim. Choose counts before observing results and report
them. An existing artifact directory is rejected rather than overwritten.

## What is controlled

- The source is copied once, including a self-contained `.git` directory, into
  private evidence. The original is never passed to a CLI invocation or fixed.
- Every invocation receives a fresh copy at the **same absolute disposable cwd**.
  Copy/reset, metadata queries, parity checks, and evidence capture are outside
  the timer. This avoids differing output paths and prevents one fix from
  cleaning the next invocation's input.
- Warmup and measured pairs alternate AB, BA, AB, BA continuously. Warmups run
  the same workload and parity checks but are separately labeled. Every call
  starts a new interpreter; warmups do not create an in-process Python cache.
- The environment is constructed, not inherited. Both endpoints use `PATH`
  from `os.defpath`, fresh disposable HOME/XDG/cache/TMPDIR directories,
  `C.UTF-8`, UTC, `TERM=dumb`, `COLUMNS=80`, `LINES=24`, and disabled color.
  Tiktoken's cache location is also disposable. This evaluates Skilllint's
  bundled token-rank construction, not a separately warmed Python encoding.
- Global and system Git config are disabled; optional Git locks are disabled.
  Local Git data is copied exactly. This is a controlled Git context, **not** a
  reproduction of the user's complete Git configuration.
- Relative symlinks must resolve inside the corpus; Git-internal links must
  resolve within their own `.git` directory. Gitfiles/linked worktrees,
  external Git storage, special files, Git includes, and core path overrides or
  active hooks/fsmonitor configuration are unsupported and rejected. Supply a
  self-contained copy first. An existing cache-dependent or network-dependent
  workload requires a separately specified experiment rather than silently
  inheriting a host cache.

The runner is not a security sandbox. Use trusted executables and corpus
configuration, and do not run commands that intentionally access outside paths.
Keep source and endpoint environments unchanged during the experiment. Source
bytes, symlink targets, file types, permissions, and Git data are checked against
the snapshot at the end, including after an execution failure; detected changes
are reported, never repaired. Access times and modification timestamps are not
part of the source equality claim.

## Parity and failure

The first invocation is the canonical result. Every subsequent invocation,
including warmups and later pairs, must match its exit code, stdout bytes,
stderr bytes, and final corpus file bytes/types/permissions/symlink targets.
There is no path, whitespace, line-ending, ANSI, or diagnostic normalization.
The corpus comparison excludes `.git`, whose full tree is captured privately
before and after **each** invocation and required to remain unchanged. This
includes config, index, HEAD, refs, objects, excludes, and shallow boundaries.
Even an otherwise harmless Git metadata write fails this strict experiment.

Only exit codes 0 and 1 are accepted as normal Skilllint outcomes. Timeouts,
other exit codes, output drift, differing fixes, changed Git inputs, changed
source, differing unrelated distribution versions, or changed endpoint metadata
fail the experiment. Do not report a speedup from an incomplete result.
End-of-run metadata equality detects version/path changes, not edits that keep
identical package versions and paths. Byte provenance remains a separate check.

## Evidence and privacy

The artifact root is created with mode 0700. Treat **everything except the
allowlisted export** as private: corpus snapshots, commands, interpreter paths,
package metadata, controlled environment, raw stdout/stderr, Git snapshots,
error details, and the digest key. Keep these artifacts out of the repository.

`public.json` contains only fixed schema/endpoint/phase labels, completion state,
pair indices, UTC start timestamps, wall seconds, child user/system CPU seconds,
return codes, and opaque keyed digests. It omits CLI arguments, host paths,
filenames, diagnostics, corpus contents, and raw environment/dependency metadata.
The metadata digest binds the private record without disclosing its strings.
HMAC-SHA256 uses a private random key per experiment; do not publish that key or
compare digests across experiments. Exact parity uses bytes, not hash equality.
Review even the allowlisted export before sharing: timing, timestamps, and
sample counts can themselves reveal experiment details.

Wall time surrounds the subprocess invocation and output capture, including
process startup and teardown. Child CPU comes from the change in POSIX
`RUSAGE_CHILDREN` user/system counters in this single-threaded runner. These
counters require no unrelated children to run inside the runner process. Raw
outputs are captured as bytes through pipes, then saved privately outside timing. Timings do not include tree
copying, hashing, metadata inspection, or parity verification.

## Interpreting results

Reserve a quiet CPU window and avoid overlapping tests, installations, builds,
or other experiments. Fresh-process runs are **not** cold-machine runs: OS page
caches remain warm and copying the corpus itself warms its pages. The harness
does not flush caches, pin CPUs, disable turbo, control thermal state, or measure
network-independent performance for arbitrary custom workloads. Record those
conditions separately and repeat noisy experiments rather than selecting a
favorable sample.

Keep pair identity when analyzing the measured phase. Report baseline and
candidate distributions, paired ratios/differences, sample counts, and spread;
do not combine different CLI workloads into a single unqualified speedup.
Separate import diagnostics from end-to-end CLI measurements. A passing parity
check establishes equivalence only for the supplied corpus, arguments, and
controlled environment, not every supported input.
