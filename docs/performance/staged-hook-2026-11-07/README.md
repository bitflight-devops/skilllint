# Actual staged hook workflow

This is a separate session, not pooled with earlier explicit-file CLI samples.
Baseline product: `85813670fbaf8755cc81698497b992cb0a1d2b60`.
Candidate product: `41a53b7a7b00e236f2f2f8fc076dbaa965bf2ac8`.
Measured local harness: `1e8278d68a54e757c0cdc8a742d97cf703cf54f5`.
The retrievable [published harness](https://github.com/bitflight-devops/skilllint/blob/9211bba1609a982f337a24b35ba831bc51c9612a/scripts/bench_staged.py)
is at `9211bba1609a982f337a24b35ba831bc51c9612a`; its script and shared paired
helpers have identical Git blob IDs, recorded in provenance. The original
measurement identity and immutable repeat declaration are retained.

## Workload and execution boundary

The source is the complete tracked working tree of
[alirezarezvani/claude-skills at 8f082544](https://github.com/alirezarezvani/claude-skills/tree/8f082544116fc0d014188e521ca40304cdfc86b0),
copied with internal symlinks into an independent local Git history. All 5,344
upstream tracked paths remain on disk. The initial unforced staging respects
the upstream ignore rules: 14 originally tracked paths are not in the new
index. With three experiment-added paths, the index has 5,333 entries. This is
a prepared Git projection, not a faithful copy of upstream history/index.
The ten lexicographically first regular `SKILL.md` paths receive a harmless
staged HTML comment. Additional controls are a staged invalid file under
`failing-examples/`, a staged nonmatching text file, and an ignored untracked
`SKILL.md`. The ignore rule is itself staged. These are experiment changes,
not modifications to the pinned upstream source.

Each sample runs `prek run skilllint --stage pre-commit --color never`, with no
explicit filename arguments. The local system hook uses the published
manifest's entry, file regex, exclusion regex and pass_filenames setting.
PATH selects the preinstalled baseline or candidate wheel. This measures real
framework startup, Git staged discovery and CLI execution. It does not time
remote Python-hook provisioning or the surrounding Git commit command.
Fresh framework caches, output capture and child processes are included;
snapshot copies, Git/index comparisons and artifact writes are outside timing.

The initial A/B and A/A sessions have two warmup pairs and ten measured pairs, alternating
AB/BA continuously. A/A uses the baseline executable for both roles. The
sample worktree is restored from the same snapshot at the same absolute path
before every invocation. Only disposable experiment directories are restored;
the source corpus and development worktree are not reset.

## Parity and controls

All timed observations return zero, with exact raw stdout/stderr parity and
unchanged worktree paths, bytes, modes and symlink targets. Git index stages,
object IDs, flags and cached binary diff are unchanged. Full before/after Git
captures remain private; raw index stat-cache bytes are not the equality
criterion. Source snapshots, including their Git metadata, remain unchanged.

An untimed instrumented hook confirms the framework passed exactly the ten
expected paths, with bytes equal to their staged blobs. Excluded, nonmatching
and ignored controls are absent. A partially staged companion confirms the
unstaged bytes were hidden from the hook and restored exactly, with index
semantics preserved. Baseline/candidate stdout and exit match exactly.
Their raw stderr differs because prek reports unique stash patch filenames;
both logs are retained, and each stash/restore pair names the same patch.
No stderr normalization or partial-stage timing claim is made.

## Results

| Session | Baseline median ms | Candidate median ms | Median paired ratio | Ratio IQR | Candidate wins |
| --- | ---: | ---: | ---: | --- | ---: |
| Local-system staged A/B | 2061.83 | 2234.22 | 1.05224 | 0.99869–1.20699 | 3/10 |
| Same-executable staged A/A | 1953.85 | 2084.23 | 0.98720 | 0.92332–1.12381 | 5/10 |
| Separate staged A/B repeat | 2993.17 | 2762.24 | 0.97182 | 0.81549–1.06514 | 19/30 |

The A/B paired median is about 5.2% slower, with only 3/10 candidate wins.
Its wide spread and the substantial A/A variation do not establish a stable
regression magnitude. They also do not support a staged-hook speedup or
performance equivalence. This unfavorable observation remains visible; it is
not pooled with earlier explicit-file measurements or replaced by the control.

A separate repeat was declared before execution: two warmup pairs and thirty
measured alternating A/B pairs, with unchanged corpus/index projection,
endpoints, framework executable and harness. Its plan binds the original
exports by SHA256; those exports remain unchanged. No samples are pooled.
The repeat paired median is about 2.8% faster, so the original slowdown did not
recur directionally. However, its IQR still crosses one and its ratio range is
0.452–2.294, including a 10.07-second baseline observation. All observations
remain in the report. The large variation, including changed absolute timing
levels between sessions, does not support a stable hook-speedup magnitude or
performance equivalence.

Quartiles use the inclusive method. Marginal medians and median paired ratios
are different statistics. All raw timing observations, CPU distributions,
paired differences, order splits and half-session splits are retained in the
adjacent JSON files. No sample was removed from either completed session.

## Provenance and limits

CPython, framework, wheel and installed product provenance are recorded in
`provenance.json`. Both wheels were built from the pinned Git archives with
the same explicit `0.0.0` version override. Runtime-only environments have
identical dependency versions and matching installed non-product payload
files, excluding bytecode and RECORD files containing environment-specific
console-script hashes. Other dependency bin scripts were not compared.
These are newly prepared environments, not the earlier primary/secondary
session environments; their dependency versions may differ.

Initial pilots using copied development environments failed because installed
hatchling caused Skilllint's wheel version helper to require a source
pyproject.toml. Those incomplete pilots and their diagnostics were retained,
then fresh runtime-only environments were built. They contribute no timing
claim. The completed sessions use the fresh runtime environments exclusively.

An untimed smoke test also installed each pinned revision through its unmodified
published `language: python` hook manifest, using local Git repository URLs.
Both completed with exit zero, identical stdout, empty stderr, unchanged
worktrees and equal index semantics. Their dependency versions matched the
timed runtime environments. Initial offline provisioning lacked build
dependencies in prek's separate cache; reusing the existing trusted uv cache
resolved that setup issue. This is functional provisioning evidence, not an
installation-time or end-to-end remote-install performance claim.

Owned heavy jobs were paused during capture. OS caches are warm/uncontrolled;
CPU frequency, affinity, thermal state and external host activity are not
controlled. Python processes are fresh but endpoint bytecode caches persist.
This clean ten-file subset does not establish performance for other staged
sizes, lint failures, fix hooks, other framework versions, or repository-wide
scans. No significance, equivalence, universal-speedup or workload-frequency
claim is made. Source contents, selected filenames and raw findings are not
republished.
